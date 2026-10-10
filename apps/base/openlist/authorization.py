"""Authorize OpenList sessions by app role and expose configuration read-only."""
import base64
import hashlib
import http.client
import json
import os
import re
import sqlite3
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CONFIG_READS = {
    '/api/admin/' + group + '/' + operation
    for group, operations in {
        'setting': ['get', 'list'], 'storage': ['get', 'list'],
        'driver': ['list', 'names', 'info'], 'meta': ['get', 'list'],
        'user': ['get', 'list', 'sshkey/list'],
        'index': ['progress'], 'scan': ['progress'],
    }.items() for operation in operations
}
HOP_HEADERS = {'connection', 'keep-alive', 'proxy-authenticate',
               'proxy-authorization', 'te', 'trailer', 'transfer-encoding', 'upgrade'}
SECRET_NAMES = re.compile(r'secret|password|pwd|token|cookie|access.?key|api.?key|private.?key|authorization', re.I)


def redact(value):
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            if isinstance(decoded, (dict, list)):
                return json.dumps(redact(decoded))
        except ValueError:
            pass
        if value.startswith(('http://', 'https://')):
            parsed = urllib.parse.urlsplit(value)
            if parsed.username is not None:
                return urllib.parse.urlunsplit(parsed._replace(netloc='[redacted]@' + parsed.netloc.rsplit('@', 1)[1]))
        return value
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if SECRET_NAMES.search(key):
            result[key] = '[redacted]' if item else item
        elif key == 'value' and SECRET_NAMES.search(str(value.get('key', ''))):
            result[key] = '[redacted]' if item else item
        elif key == 'addition' and isinstance(item, str):
            try:
                result[key] = json.dumps(redact(json.loads(item)))
            except ValueError:
                result[key] = '[redacted]'
        else:
            result[key] = redact(item)
    return result


def canonical_path(target):
    path = urllib.parse.unquote(urllib.parse.urlsplit(target).path)
    if '\\' in path or '\x00' in path or '//' in path or any(p in ['.', '..'] for p in path.split('/')):
        raise ValueError('Invalid request path')
    return path


class AccessDenied(Exception):
    pass


class RoleAuthority:
    def __init__(self, credentials, endpoint, required_role):
        self.credentials = credentials
        self.endpoint = urllib.parse.urlsplit(endpoint)
        self.required_role = required_role
        self.lock = threading.RLock()
        self.token = None
        self.token_expiry = 0
        self.users = {}

    def request(self, method, path, body=None, authorization=None):
        connection = http.client.HTTPConnection(self.endpoint.hostname, self.endpoint.port or 80, timeout=10)
        headers = {'Host': self.credentials['hostname'], 'Content-Type': 'application/x-www-form-urlencoded' if path == '/oidc/token' else 'application/json'}
        if authorization:
            headers['Authorization'] = 'Bearer ' + authorization
        try:
            connection.request(method, path, body, headers)
            response = connection.getresponse()
            data = response.read(2**20)
            if response.status != 200:
                raise AccessDenied('Identity authorization unavailable')
            return json.loads(data)
        finally:
            connection.close()

    def allows(self, subject):
        if not subject:
            return False
        with self.lock:
            now = time.monotonic()
            cached = self.users.get(subject)
            if cached and cached[0] > now:
                return cached[1]
            if now >= self.token_expiry:
                data = urllib.parse.urlencode({
                    'grant_type': 'client_credentials', 'client_id': self.credentials['application_id'],
                    'client_secret': self.credentials['application_secret'],
                    'resource': self.credentials['resource'], 'scope': 'all',
                }).encode()
                result = self.request('POST', '/oidc/token', data)
                self.token = result['access_token']
                self.token_expiry = now + max(0, int(result['expires_in']) - 30)
            roles = self.request('GET', '/api/users/' + urllib.parse.quote(subject, safe='') + '/roles', authorization=self.token)
            allowed = any(role['name'] == self.required_role for role in roles)
            # Never use stale positive decisions after an identity-provider failure.
            if len(self.users) >= 4096:
                self.users.clear()
            self.users[subject] = (now + 30, allowed)
            return allowed


class Gate:
    def __init__(self, native_host, native_port, authority, database, site_url):
        self.native_host, self.native_port = native_host, native_port
        self.authority, self.database = authority, database
        self.site_host = urllib.parse.urlsplit(site_url).netloc
        self.cache = {}
        self.lock = threading.Lock()

    def admin_token(self):
        with sqlite3.connect('file:' + str(self.database) + '?mode=ro', uri=True) as connection:
            row = connection.execute("select value from x_setting_items where key='token'").fetchone()
        if not row or not row[0]:
            raise AccessDenied('Configuration reader unavailable')
        return row[0]

    def actor(self, authorization):
        if not authorization:
            return None
        if authorization.startswith('Bearer '):
            authorization = authorization[7:]
        if authorization.startswith('Basic '):
            try:
                username = base64.b64decode(authorization[6:], validate=True).decode().split(':', 1)[0]
                with sqlite3.connect('file:' + str(self.database) + '?mode=ro', uri=True) as connection:
                    connection.row_factory = sqlite3.Row
                    row = connection.execute('select username,sso_id,role,disabled from x_users where username=?', (username,)).fetchone()
                if not row or row['disabled']:
                    raise AccessDenied('Invalid session')
                # Native WebDAV still validates the actual password and path permissions.
                return dict(row)
            except (ValueError, UnicodeError):
                raise AccessDenied('Invalid session') from None
        digest = hashlib.sha256(authorization.encode()).digest()
        with self.lock:
            cached = self.cache.get(digest)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        connection = http.client.HTTPConnection(self.native_host, self.native_port, timeout=10)
        try:
            connection.request('GET', '/api/me', headers={'Authorization': authorization, 'Host': self.site_host})
            response = connection.getresponse()
            result = json.loads(response.read(2**20))
            if response.status != 200 or result.get('code') != 200:
                raise AccessDenied('Invalid session')
            actor = result['data']
        finally:
            connection.close()
        with self.lock:
            if len(self.cache) >= 4096:
                self.cache.clear()
            self.cache[digest] = (time.monotonic() + 5, actor)
        return actor

    def authorized_actor(self, authorization):
        actor = self.actor(authorization)
        if actor and actor.get('sso_id') and not self.authority.allows(actor['sso_id']):
            raise AccessDenied('Required application role is missing')
        return actor


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *_):
        # URLs may contain OIDC codes, download signatures or credentials.
        pass

    def json_response(self, status, message):
        body = json.dumps({'code': status, 'message': message, 'data': None}).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)
        self.close_connection = True

    def handle_request(self):
        connection = None
        try:
            path = canonical_path(self.path)
            gate = self.server.gate
            if path == '/healthz':
                return self.json_response(200, 'ready')
            configuration = path == '/api/admin' or path.startswith('/api/admin/')
            if configuration and (self.command != 'GET' or path not in CONFIG_READS):
                return self.json_response(403, 'Configuration is read-only and managed by Helm')
            auth = self.headers.get('Authorization', '')
            if auth.startswith('Basic ') and path.startswith('/api/'):
                raise AccessDenied('API requests require a valid OpenList session')
            actor = gate.authorized_actor(auth)
            manager = bool(actor and actor.get('sso_id') and gate.authority.allows(actor['sso_id']))
            if configuration and not manager:
                raise AccessDenied('Required application role is missing')
            headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_HEADERS}
            headers['Host'] = gate.site_host
            headers['Connection'] = 'close'
            if auth.startswith('Bearer '):
                headers['Authorization'] = auth[7:]
            if configuration or (manager and path == '/api/fs/link'):
                headers['Authorization'] = gate.admin_token()
            length = self.headers.get('Content-Length')
            transfer = self.headers.get('Transfer-Encoding')
            if (length and transfer) or (transfer and transfer.lower() != 'chunked'):
                return self.json_response(400, 'Invalid request framing')
            if len(self.headers.get_all('Content-Length', [])) > 1 or len(self.headers.get_all('Transfer-Encoding', [])) > 1:
                return self.json_response(400, 'Invalid request framing')
            payload = None
            if path == '/api/me/update' and actor and actor.get('sso_id'):
                if transfer or not length or not 0 <= int(length) <= 2**20:
                    return self.json_response(400, 'Invalid profile update')
                profile = json.loads(self.rfile.read(int(length)))
                if any(key.lower() == 'sso_id' and key != 'sso_id' for key in profile):
                    return self.json_response(400, 'Invalid profile field')
                if profile.get('sso_id') != actor['sso_id']:
                    return self.json_response(403, 'SSO identity is managed by the identity provider')
                payload = json.dumps(profile).encode()
                headers['Content-Length'] = str(len(payload))
            connection = http.client.HTTPConnection(gate.native_host, gate.native_port, timeout=300)
            connection.putrequest(self.command, self.path, skip_host=True, skip_accept_encoding=True)
            if transfer:
                headers['Transfer-Encoding'] = 'chunked'
            # JSON responses that are filtered must use an uncompressed representation.
            filtered = configuration or path == '/api/me' or path.startswith('/api/auth')
            if filtered:
                headers['Accept-Encoding'] = 'identity'
            for name, value in headers.items():
                connection.putheader(name, value)
            connection.endheaders()
            if payload is not None:
                connection.send(payload)
            elif transfer:
                while True:
                    line = self.rfile.readline(8193)
                    if len(line) > 8192 or not line.endswith(b'\r\n'):
                        raise ValueError('Invalid chunk')
                    size = int(line.strip().split(b';')[0], 16)
                    if size < 0:
                        raise ValueError('Invalid chunk')
                    if size == 0:
                        total = 0
                        while True:
                            trailer = self.rfile.readline(8193)
                            total += len(trailer)
                            if not trailer or total > 65536:
                                raise ValueError('Invalid trailer')
                            if trailer == b'\r\n':
                                break
                        connection.send(b'0\r\n\r\n')
                        break
                    connection.send(('%x\r\n' % size).encode())
                    remaining = size
                    while remaining:
                        block = self.rfile.read(min(65536, remaining))
                        if not block:
                            raise ValueError('Incomplete body')
                        connection.send(block)
                        remaining -= len(block)
                    if self.rfile.read(2) != b'\r\n':
                        raise ValueError('Invalid chunk terminator')
                    connection.send(b'\r\n')
            elif length:
                remaining = int(length)
                if remaining < 0:
                    raise ValueError('Invalid length')
                while remaining:
                    block = self.rfile.read(min(65536, remaining))
                    if not block:
                        raise ValueError('Incomplete body')
                    connection.send(block)
                    remaining -= len(block)
            response = connection.getresponse()
            body = None
            if filtered:
                body = response.read(8*2**20+1)
                if len(body) > 8*2**20:
                    raise AccessDenied('Configuration response too large')
                if configuration:
                    body = json.dumps(redact(json.loads(body))).encode()
                elif path == '/api/me':
                    result = json.loads(body)
                    if result.get('code') == 200:
                        result['data']['role'] = 2 if manager else (1 if result['data'].get('role') == 1 else 0)
                    body = json.dumps(result).encode()
                elif path.startswith('/api/auth'):
                    content_type = response.getheader('Content-Type', '')
                    if 'json' in content_type:
                        result = json.loads(body)
                        token = (result.get('data') or {}).get('token') if isinstance(result.get('data'), dict) else None
                        if token:
                            gate.authorized_actor(token)
                    else:
                        text = body.decode('utf-8')
                        match = re.search(r'"token"\s*:\s*"([^"]+)"', text)
                        if match:
                            gate.authorized_actor(match.group(1))
                        binding = re.search(r'"sso_id"\s*:\s*"([^"]+)"', text)
                        if binding:
                            # This proof comes directly from the trusted native callback,
                            # after native OIDC signature, issuer, audience and state validation.
                            part = binding.group(1).split('.')[1]
                            claims = json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4)))
                            if not gate.authority.allows(claims['sso_id']):
                                raise AccessDenied('Required application role is missing')
            self.send_response(response.status)
            for name, value in response.getheaders():
                if name.lower() in HOP_HEADERS or name.lower() == 'content-length' and body is not None:
                    continue
                if filtered and name.lower() in ['cache-control', 'etag', 'content-encoding']:
                    continue
                self.send_header(name, value)
            if body is not None:
                self.send_header('Content-Length', str(len(body)))
            if filtered:
                self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            if self.command != 'HEAD':
                if body is not None:
                    self.wfile.write(body)
                else:
                    while True:
                        block = response.read(65536)
                        if not block:
                            break
                        self.wfile.write(block)
            self.close_connection = True
        except AccessDenied as error:
            self.json_response(403, str(error))
        except (ValueError, KeyError, IndexError):
            self.json_response(400, 'Invalid request or upstream response')
        except (OSError, http.client.HTTPException, sqlite3.Error):
            self.json_response(503, 'Authorization or upstream unavailable')
        finally:
            if connection:
                connection.close()

    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = handle_request
    do_PROPFIND = do_PROPPATCH = do_MKCOL = do_MOVE = do_COPY = do_LOCK = do_UNLOCK = handle_request


def main():
    credentials = json.loads(Path('/logto/credentials').read_text())
    authority = RoleAuthority(credentials, 'http://logto-core.prod.svc.cluster.local:3001', os.environ['REQUIRED_ROLE'])
    server = ThreadingHTTPServer(('0.0.0.0', 5246), Handler)
    server.daemon_threads = True
    server.gate = Gate('127.0.0.1', 5244, authority, Path('/data/data.db'), os.environ['SITE_URL'])
    print('OpenList role authorization and read-only configuration gateway ready', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
