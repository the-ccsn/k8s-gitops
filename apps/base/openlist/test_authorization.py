"""Exercise the actual HTTP gateway with synthetic native and identity services."""
import http.client
import importlib.util
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

spec = importlib.util.spec_from_file_location('authorization', Path(__file__).with_name('authorization.py'))
authorization = importlib.util.module_from_spec(spec)
spec.loader.exec_module(authorization)


class Native(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def handle_request(self):
        body = b''
        if self.headers.get('Transfer-Encoding') == 'chunked':
            while True:
                size = int(self.rfile.readline().strip(), 16)
                if not size:
                    self.rfile.readline()
                    break
                body += self.rfile.read(size)
                self.rfile.read(2)
        elif self.headers.get('Content-Length'):
            body = self.rfile.read(int(self.headers['Content-Length']))
        if len(self.headers.get_all('Host', [])) != 1:
            self.send_error(400, 'Multiple Host headers')
            return
        self.server.calls.append((self.command, self.path, self.headers.get('Authorization'), body))
        if self.path == '/api/me':
            actor = self.server.actors.get(self.headers.get('Authorization'))
            result = {'code': 200, 'data': actor} if actor else {'code': 401, 'data': None}
        elif self.path.startswith('/api/admin/storage/'):
            result = {'code': 200, 'data': {'addition': json.dumps({'bucket': 'share', 'secret_access_key': 'synthetic-storage-secret', 'endpoint': 'http://native'})}}
        elif self.path.startswith('/api/admin/setting/'):
            result = {'code': 200, 'data': [{'key': 'token', 'value': 'synthetic-admin-token'}, {'key': 'site_url', 'value': 'https://share.example'}]}
        elif self.path.startswith('/api/auth/sso_callback'):
            token = self.path.split('token=', 1)[1]
            output = ('<script>window.opener.postMessage({"token":"' + token + '"},"*")</script>').encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(output)))
            self.end_headers()
            self.wfile.write(output)
            return
        elif self.path.startswith('/api/auth/login'):
            result = {'code': 200, 'data': {'token': json.loads(body)['fixture_token']}}
        else:
            result = {'code': 200, 'data': {'received_bytes': len(body)}}
        output = json.dumps(result).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(output)))
        self.end_headers()
        self.wfile.write(output)

    do_GET = do_POST = do_PUT = handle_request


class Identity(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers['Content-Length']))
        if self.headers.get('Content-Type') != 'application/x-www-form-urlencoded':
            self.send_error(400)
            return
        self.reply({'access_token': 'synthetic-management-token', 'expires_in': 300})

    def do_GET(self):
        if self.server.failed:
            self.send_error(503)
            return
        subject = self.path.split('/')[3]
        self.reply([{'name': r} for r in self.server.roles.get(subject, [])])

    def reply(self, result):
        output = json.dumps(result).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(output)))
        self.end_headers()
        self.wfile.write(output)


def start(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class GatewayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = start(ThreadingHTTPServer(('127.0.0.1', 0), Native))
        cls.native.calls = []
        cls.native.actors = {
            'base-session': {'sso_id': 'base-user', 'role': 0, 'username': 'base-user'},
            'share-session': {'sso_id': 'share-user', 'role': 0, 'username': 'share-user'},
            'external-session': {'sso_id': 'external-user', 'role': 0, 'username': 'external-user'},
            'local-session': {'sso_id': '', 'role': 0, 'username': 'local-user'},
        }
        cls.identity = start(ThreadingHTTPServer(('127.0.0.1', 0), Identity))
        cls.identity.roles = {'base-user': ['base:admin'], 'share-user': ['share:admin']}
        cls.identity.failed = False
        credentials = {'hostname': 'identity.example', 'application_id': 'fixture',
                       'application_secret': 'synthetic-client-secret', 'resource': 'fixture-api'}
        cls.authority = authorization.RoleAuthority(credentials, 'http://127.0.0.1:' + str(cls.identity.server_port), 'base:admin')
        cls.gate = authorization.Gate('127.0.0.1', cls.native.server_port, cls.authority, Path('/unused'), 'https://base.example')
        cls.gate.admin_token = lambda: 'synthetic-admin-token'
        cls.proxy = start(ThreadingHTTPServer(('127.0.0.1', 0), authorization.Handler))
        cls.proxy.gate = cls.gate

    @classmethod
    def tearDownClass(cls):
        for server in [cls.proxy, cls.native, cls.identity]:
            server.shutdown()
            server.server_close()

    def request(self, method, path, token=None, body=None, chunked=False, extra_headers=None):
        c = http.client.HTTPConnection('127.0.0.1', self.proxy.server_port, timeout=5)
        headers = {'Authorization': token} if token else {}
        headers.update(extra_headers or {})
        if body is not None and not isinstance(body, (bytes, list)):
            body = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        c.request(method, path, body, headers, encode_chunked=chunked)
        r = c.getresponse()
        result = r.status, r.read(), dict(r.getheaders())
        c.close()
        return result

    def test_role_separation_and_external_denial(self):
        for token in ['share-session', 'external-session']:
            self.assertEqual(self.request('POST', '/api/fs/list', token, {})[0], 403)
        self.assertEqual(self.request('POST', '/api/fs/list', 'base-session', {})[0], 200)
        self.assertEqual(self.request('POST', '/api/fs/list', 'local-session', {})[0], 200)
        self.assertEqual(self.request('POST', '/api/fs/list', body={})[0], 200)

    def test_read_only_configuration_and_secret_redaction(self):
        status, body, headers = self.request('GET', '/api/admin/storage/list', 'base-session')
        self.assertEqual(status, 200)
        self.assertNotIn(b'synthetic-storage-secret', body)
        self.assertEqual(json.loads(json.loads(body)['data']['addition'])['bucket'], 'share')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        status, body, _ = self.request('GET', '/api/admin/setting/list', 'base-session')
        self.assertEqual(status, 200)
        self.assertNotIn(b'synthetic-admin-token', body)
        self.assertEqual(self.request('GET', '/api/admin/setting/list', 'local-session')[0], 403)
        self.assertEqual(self.request('GET', '/api/admin/setting/list', 'Basic YmFzZS11c2VyOndyb25n')[0], 403)

    def test_mutations_are_blocked_before_the_native_service(self):
        before = len(self.native.calls)
        for path in ['/api/admin/setting/save', '/api/admin/storage/update', '/api/admin/user/update',
                     '/api/admin/meta/create', '/api/admin/storage/load_all', '/api/admin/setting/reset_token',
                     '/api/%61dmin/setting/save', '/api/admin/setting/save?unused=true']:
            for method in ['POST', 'GET', 'PUT', 'DELETE']:
                self.assertEqual(self.request(method, path, 'base-session', {})[0], 403)
        self.assertEqual(len(self.native.calls), before)

    def test_oidc_and_password_tokens_do_not_escape_without_the_role(self):
        for token in ['share-session', 'external-session']:
            status, body, _ = self.request('GET', '/api/auth/sso_callback?token=' + token)
            self.assertEqual(status, 403)
            self.assertNotIn(token.encode(), body)
            self.assertEqual(self.request('POST', '/api/auth/login', body={'fixture_token': token})[0], 403)
        self.assertEqual(self.request('GET', '/api/auth/sso_callback?token=base-session')[0], 200)

    def test_role_gives_a_configuration_view_without_changing_native_user_role(self):
        status, body, _ = self.request('GET', '/api/me', 'base-session')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['data']['role'], 2)
        self.assertEqual(self.native.actors['base-session']['role'], 0)

    def test_sso_binding_cannot_be_cleared_to_bypass_later_revocation(self):
        self.assertEqual(self.request('POST', '/api/me/update', 'base-session', {'sso_id': ''})[0], 403)
        self.assertEqual(self.request('POST', '/api/me/update', 'base-session', {'sso_id': 'base-user', 'SSO_ID': ''})[0], 400)
        self.assertEqual(self.request('POST', '/api/me/update', 'base-session', {'sso_id': 'base-user'})[0], 200)

    def test_lowercase_ingress_headers_are_overridden_without_duplicates(self):
        status, body, _ = self.request('GET', '/api/admin/storage/list', 'base-session',
                                     extra_headers={'host': 'base.example', 'accept-encoding': 'gzip'})
        self.assertEqual(status, 200)
        self.assertNotIn(b'synthetic-storage-secret', body)

    def test_fixed_length_and_chunked_upload_bodies_are_streamed(self):
        payload = b'synthetic upload' * 10000
        status, body, _ = self.request('PUT', '/api/fs/put', 'base-session', payload)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['data']['received_bytes'], len(payload))
        status, body, _ = self.request('PUT', '/api/fs/put', 'base-session', [payload[:500], payload[500:]], chunked=True)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['data']['received_bytes'], len(payload))

    def test_identity_failure_and_role_revocation_fail_closed(self):
        self.assertTrue(self.authority.allows('base-user'))
        self.authority.users.clear()
        self.identity.failed = True
        try:
            self.assertEqual(self.request('POST', '/api/fs/list', 'base-session', {})[0], 403)
        finally:
            self.identity.failed = False
        previous = self.identity.roles['base-user']
        self.identity.roles['base-user'] = []
        self.authority.users.clear()
        try:
            self.assertEqual(self.request('POST', '/api/fs/list', 'base-session', {})[0], 403)
        finally:
            self.identity.roles['base-user'] = previous
            self.authority.users.clear()


if __name__ == '__main__':
    unittest.main()
