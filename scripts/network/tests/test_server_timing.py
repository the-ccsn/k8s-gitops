"""Local proxy integration checks; no cluster writes.

Run with: uv run --with pyyaml python scripts/network/tests/test_server_timing.py
Requires Podman and OpenSSL. Containers are stopped, retained for inspection.
"""
from __future__ import annotations

import copy
import http.client
import json
import re
import socket
import ssl
import subprocess
import threading
import time
import unittest
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
NGINX_DIR = ROOT / "infra/configs/base/i319-reroute"
ENVOY_POLICY = ROOT / "infra/configs/base/gateway/server-timing.yaml"
ENVOY_IMAGE = "registry.istio.io/release/proxyv2:1.30.0-rc.0-distroless"


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Backend(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        # Make upstream waiting distinguishable from connect/handshake time.
        time.sleep(0.08)
        self.send_response(503 if self.path == "/error" else 200)
        self.send_header("Server-Timing", 'app;dur=7;desc="query, render"')
        self.send_header("Server-Timing", "opaque_layer;dur=9")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"o")
        self.wfile.flush()
        if self.path == "/stream":
            time.sleep(1.5)
        self.wfile.write(b"k")

    def log_message(self, *_args: object) -> None:
        pass


class ServerTimingIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.containers: list[str] = []
        cls.servers: list[ThreadingHTTPServer] = []
        cls.addClassCleanup(cls.cleanup)
        cls.run_id = str(time.time_ns())
        cls.artifacts = ROOT.parent / "task-logs/server-timing" / cls.run_id
        cls.artifacts.mkdir(parents=True)
        run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(cls.artifacts / "tls.key"), "-out", str(cls.artifacts / "tls.crt"),
            "-days", "1", "-subj", "/CN=localhost")
        backend = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
        tls_backend = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cls.artifacts / "tls.crt", cls.artifacts / "tls.key")
        tls_backend.socket = context.wrap_socket(tls_backend.socket, server_side=True)
        cls.servers.extend([backend, tls_backend])
        for server in cls.servers:
            threading.Thread(target=server.serve_forever, daemon=True).start()
        cls.inner_port, cls.outer_port, cls.nginx_port, cls.tls_port = free_port(), free_port(), free_port(), free_port()
        policies = yaml.safe_load(ENVOY_POLICY.read_text())["items"]
        cls.patches = policies[0]["spec"]["configPatches"]
        assert policies[1]["spec"]["configPatches"] == cls.patches
        cls.start_envoy("inner", cls.inner_port, tls_backend.server_port, tls=True)
        cls.start_envoy("outer", cls.outer_port, cls.inner_port)
        cls.start_nginx(backend.server_port)
        for port in [cls.inner_port, cls.outer_port, cls.nginx_port, cls.tls_port]:
            deadline = time.monotonic() + 15
            while True:
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError(f"Proxy failed to listen on {port}; see {cls.artifacts}")
                    time.sleep(0.1)

    @classmethod
    def container(cls, role: str, image: str, entrypoint: str, args: list[str], mounts: list[str] | None = None) -> None:
        name = f"ccsn-server-timing-{role}-{cls.run_id}"
        command = ["podman", "run", "--detach", "--name", name, "--hostname", f"timing-{role}",
                   "--user", "0", "--network", "host", "--entrypoint", entrypoint,
                   "--volume", f"{cls.artifacts}:/test:ro"]
        for mount in mounts or []:
            command.extend(["--volume", mount])
        run(*command, image, *args)
        cls.containers.append(name)

    @classmethod
    def start_envoy(cls, role: str, port: int, upstream: int, tls: bool = False) -> None:
        route = {"name": "test", "virtual_hosts": [{"name": "test", "domains": ["*"], "routes": [
            {"match": {"path": "/local"}, "direct_response": {"status": 403}},
            {"match": {"prefix": "/"}, "route": {"cluster": "backend"}},
        ]}]}
        route.update(copy.deepcopy(cls.patches[0]["patch"]["value"]))
        filters = [copy.deepcopy(cls.patches[1]["patch"]["value"]), {
            "name": "test.local_reply",
            "typed_config": {
                "@type": "type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua",
                "default_source_code": {"inline_string": """
function envoy_on_request(handle)
  if handle:headers():get(":path") == "/deny" then
    handle:respond({[":status"] = "401"}, "denied")
  end
end
"""},
            },
        }, *(copy.deepcopy(patch["patch"]["value"]) for patch in cls.patches[2:]), {
            "name": "envoy.filters.http.router",
            "typed_config": {"@type": "type.googleapis.com/envoy.extensions.filters.http.router.v3.Router"},
        }]
        cluster = {"name": "backend", "connect_timeout": "1s", "type": "STATIC", "load_assignment": {
            "cluster_name": "backend", "endpoints": [{"lb_endpoints": [{"endpoint": {
                "address": {"socket_address": {"address": "127.0.0.1", "port_value": upstream}},
            }}]}],
        }}
        if tls:
            cluster["transport_socket"] = {"name": "envoy.transport_sockets.tls", "typed_config": {
                "@type": "type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.UpstreamTlsContext",
                "common_tls_context": {"validation_context": {"trusted_ca": {"filename": "/test/tls.crt"}}},
            }}
        bootstrap = {"static_resources": {"clusters": [cluster], "listeners": [{
            "name": "http", "address": {"socket_address": {"address": "127.0.0.1", "port_value": port}},
            "filter_chains": [{"filters": [{"name": "envoy.filters.network.http_connection_manager", "typed_config": {
                "@type": "type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager",
                "stat_prefix": "test", "route_config": route, "http_filters": filters,
            }}]}],
        }]}}
        if tls:
            listener = copy.deepcopy(bootstrap["static_resources"]["listeners"][0])
            listener["name"] = "https"
            listener["address"]["socket_address"]["port_value"] = cls.tls_port
            listener["filter_chains"][0]["transport_socket"] = {
                "name": "envoy.transport_sockets.tls", "typed_config": {
                    "@type": "type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext",
                    "common_tls_context": {"tls_certificates": [{
                        "certificate_chain": {"filename": "/test/tls.crt"},
                        "private_key": {"filename": "/test/tls.key"},
                    }]},
                },
            }
            bootstrap["static_resources"]["listeners"].append(listener)
        (cls.artifacts / f"{role}.yaml").write_text(yaml.safe_dump(bootstrap))
        cls.container(role, ENVOY_IMAGE, "/usr/local/bin/envoy", ["-c", f"/test/{role}.yaml",
                      "--disable-hot-restart", "--concurrency", "1", "-l", "error"])

    @classmethod
    def start_nginx(cls, backend_port: int) -> None:
        cls.nginx_image = yaml.safe_load((NGINX_DIR / "deployment.yaml").read_text())["spec"]["template"]["spec"]["containers"][0]["image"]
        main = yaml.safe_load((NGINX_DIR / "nginx-config.yaml").read_text())["data"]["nginx.conf"]
        (cls.artifacts / "nginx.conf").write_text(main)
        (cls.artifacts / "nginx-servers").mkdir()
        # Reuse the production module/import and location handler, change only listeners/backends.
        (cls.artifacts / "nginx-servers/test.conf").write_text(f"""
upstream test_retry {{
    server 127.0.0.1:{free_port()};
    server 127.0.0.1:{backend_port} backup;
}}
server {{
    listen 127.0.0.1:{cls.nginx_port};
    add_header Alt-Svc 'h3=":443"; ma=86400';
    location / {{
        include /etc/nginx/server-timing/server-timing-headers.conf;
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_pass http://127.0.0.1:{cls.outer_port};
    }}
    location /standalone {{
        include /etc/nginx/server-timing/server-timing-headers.conf;
        proxy_pass http://127.0.0.1:{backend_port}/;
    }}
    location /nginx-local {{
        include /etc/nginx/server-timing/server-timing-headers.conf;
        return 503;
    }}
    location /retry {{
        include /etc/nginx/server-timing/server-timing-headers.conf;
        proxy_pass http://test_retry/;
    }}
}}
""")
        cls.container("nginx", cls.nginx_image, "nginx", ["-c", "/test/nginx.conf", "-g", "daemon off;"], [
            f"{NGINX_DIR}:/etc/nginx/server-timing:ro",
            f"{cls.artifacts / 'nginx-servers'}:/etc/nginx/conf.d:ro",
        ])

    @classmethod
    def cleanup(cls) -> None:
        for name in reversed(cls.containers):
            try:
                run("podman", "stop", "--time", "2", name)
                (cls.artifacts / f"{name}.log").write_text(run("podman", "logs", name))
            except subprocess.CalledProcessError as error:
                print(error.output)
        for server in cls.servers:
            server.shutdown()
            server.server_close()

    def fetch(self, port: int, path: str = "/") -> tuple[int, str]:
        with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=5)) as conn:
            conn.request("GET", path, headers={"x-ccsn-envoy-timing": "forged=999999", "x-ccsn-envoy-timing-hop": "forged"})
            response = conn.getresponse()
            headers = response.getheaders()
            self.assertFalse(any(key.lower().startswith("x-ccsn-envoy-timing") for key, _ in headers))
            self.assertFalse(any(key.lower() == "timing-allow-origin" for key, _ in headers))
            self.assertNotIn("__end", response.getheader("Server-Timing", ""))
            self.assertEqual(response.getheader("Alt-Svc"), 'h3=":443"; ma=86400' if port == self.nginx_port and response.status == 200 else None)
            response.read()
            return response.status, ", ".join(value for key, value in headers if key.lower() == "server-timing")

    def test_each_proxy_works_independently(self) -> None:
        _, nginx = self.fetch(self.nginx_port, "/standalone")
        self.assertIn("nginx_upstream_headers", nginx)
        # The fallback formats decimals; integer milliseconds demonstrate that
        # the normal response used the native map instead of creating njs state.
        self.assertRegex(nginx, r"nginx_headers;dur=[0-9]+;")
        self.assertRegex(nginx, r"nginx_upstream_headers;dur=[0-9]+;")
        self.assertNotIn("envoy_", nginx)
        _, envoy = self.fetch(self.inner_port)
        self.assertIn("envoy_upstream_headers", envoy)
        self.assertNotIn("nginx_", envoy)

    def test_chain_preserves_all_hops_and_tls(self) -> None:
        _, timing = self.fetch(self.nginx_port)
        for metric in ['app;dur=7;desc="query, render"', "opaque_layer;dur=9", "nginx_upstream_connect", "nginx_upstream_headers",
                       "envoy_upstream_tcp", "envoy_upstream_tls", "envoy_upstream_headers", "envoy_headers"]:
            self.assertIn(metric, timing)
        self.assertEqual(timing.count("envoy_upstream_headers;"), 2)
        self.assertIn('desc="timing-inner"', timing)
        self.assertIn('desc="timing-outer"', timing)
        self.assertNotIn("forged", timing)
        self.assertNotIn('envoy_upstream_tls;dur=;desc="timing-outer"', timing)
        self.assertNotRegex(timing, r'envoy_upstream_tls;[^,]*desc="timing-outer"')
        self.assertNotIn("dur=-", timing)
        self.assertNotIn("dur=;", timing)
        # Both native total durations and seconds-to-milliseconds maps must
        # reflect the 80 ms backend wait, rather than completion-only zeros.
        for metric in ["nginx_headers", "nginx_upstream_headers", "envoy_headers", "envoy_upstream_headers"]:
            durations = re.findall(metric + r";dur=([0-9.]+)", timing)
            self.assertTrue(durations)
            self.assertTrue(all(70 <= float(value) < 1000 for value in durations), durations)
        (self.artifacts / "response-timing.json").write_text(json.dumps({"server-timing": timing}, indent=2))

    def test_errors_and_local_responses(self) -> None:
        for path, status in [("/error", 503), ("/local", 403), ("/deny", 401), ("/nginx-local", 503)]:
            actual, timing = self.fetch(self.nginx_port, path)
            self.assertEqual(actual, status)
            self.assertIn("nginx_headers", timing)
            if path != "/nginx-local":
                self.assertIn("envoy_headers", timing)

    def test_all_production_nginx_locations_validate(self) -> None:
        configs = yaml.safe_load((NGINX_DIR / "nginx-subconfig.yaml").read_text())["data"]
        overlay = ROOT / "infra/configs/overlays/kubevirt-cluster-319/i319-reroute/nginx-subconfig-infra-patch.yaml"
        configs.update(yaml.safe_load(overlay.read_text())["data"])
        directory = self.artifacts / "production-servers"
        directory.mkdir(exist_ok=True)
        hosts = set()
        for filename, text in configs.items():
            self.assertEqual(text.count("location / {"), text.count("include /etc/nginx/server-timing/server-timing-headers.conf;"))
            (directory / filename).write_text(text)
            hosts.update(re.findall(r"server ([a-z0-9.-]+):\d+;", text))
        name = f"ccsn-server-timing-nginx-config-{self.run_id}"
        command = ["podman", "run", "--name", name, "--user", "0", "--entrypoint", "nginx"]
        for host in sorted(hosts):
            command.extend(["--add-host", f"{host}:127.0.0.1"])
        command.extend([
            "--volume", f"{self.artifacts}:/test:ro",
            "--volume", f"{NGINX_DIR}:/etc/nginx/server-timing:ro",
            "--volume", f"{directory}:/etc/nginx/conf.d:ro",
            "--volume", f"{self.artifacts}:/etc/nginx/certs:ro",
            self.nginx_image, "-t", "-c", "/test/nginx.conf",
        ])
        self.containers.append(name)
        output = run(*command)
        self.assertIn("test is successful", output)

    def test_nginx_retry_records_successful_attempt(self) -> None:
        status, timing = self.fetch(self.nginx_port, "/retry")
        self.assertEqual(status, 200)
        self.assertIn('nginx_upstream_headers;', timing)
        self.assertIn('desc="timing-nginx attempt 2"', timing)
        self.assertNotIn("dur=-", timing)

    def test_upstream_tls_and_connection_reuse(self) -> None:
        context = ssl.create_default_context(cafile=str(self.artifacts / "tls.crt"))
        with closing(http.client.HTTPSConnection("localhost", self.tls_port, context=context, timeout=5)) as conn:
            for _ in range(2):
                conn.request("GET", "/")
                response = conn.getresponse()
                timing = response.getheader("Server-Timing")
                self.assertEqual(response.status, 200)
                self.assertIn("envoy_upstream_pool;", timing)
                self.assertIn("envoy_upstream_tls;", timing)
                response.read()

    def test_local_reply_before_request_body_omits_all_unavailable_timings(self) -> None:
        with closing(http.client.HTTPConnection("127.0.0.1", self.inner_port, timeout=5)) as conn:
            conn.putrequest("POST", "/local")
            conn.putheader("Content-Length", "1000")
            conn.endheaders()
            # No request body has arrived: neither upstream nor complete request
            # receive intervals exist. The converter must omit all five metrics.
            response = conn.getresponse()
            self.assertEqual(response.status, 403)
            timing = response.getheader("Server-Timing")
            self.assertIn("envoy_headers;", timing)
            self.assertEqual(timing.count("envoy_"), 1)
            self.assertNotIn("__end", timing)
            self.assertNotIn("dur=;", timing)
            self.assertFalse(any(key.lower().startswith("x-ccsn-envoy-timing") for key, _ in response.getheaders()))
            response.read()

    def test_stream_headers_do_not_wait_for_body(self) -> None:
        with closing(http.client.HTTPConnection("127.0.0.1", self.nginx_port, timeout=5)) as conn:
            start = time.monotonic()
            conn.request("GET", "/stream")
            response = conn.getresponse()
            self.assertLess(time.monotonic() - start, 1)
            self.assertIn("nginx_headers", response.getheader("Server-Timing"))
            self.assertEqual(response.read(), b"ok")


if __name__ == "__main__":
    unittest.main()
