"""Local proxy integration checks; no cluster writes.

Run with: uv run --with pyyaml python scripts/network/tests/test_server_timing.py
Requires Podman and OpenSSL. Containers are stopped, retained for inspection.
"""
from __future__ import annotations

import copy
import http.client
import json
import os
import platform
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
MODULE_DIR = ROOT / "infra/controllers/networking/base/istio"
ENVOY_POLICY = ROOT / "infra/configs/base/gateway/server-timing.yaml"
ENVOY_IMAGES = {
    "amd64": "mirror.gcr.io/istio/proxyv2:1.31.1-distroless@sha256:bdf5cb574340307f60438d5ebc3ba71a785e0b53bc3b7c5d02af9f0f975d04d4",
    "arm64": "mirror.gcr.io/istio/proxyv2:1.31.1-distroless@sha256:cd6b1a2f3a96aac17a1cf3faa5efd4ea51aae88231e2fabc7c84c019a3994ddb",
}
ENVOY_IMAGE = os.environ.get("TIMING_TEST_ENVOY_IMAGE") or ENVOY_IMAGES[
    os.environ.get("TIMING_TEST_ENVOY_ARCH") or
    {"x86_64": "amd64", "aarch64": "arm64"}[platform.machine()]]


def run(*args: str) -> str:
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as error:
        print(error.output)
        raise


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Backend(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    response_wait_started = threading.Event()

    def setup(self) -> None:
        super().setup()
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def do_GET(self) -> None:
        if self.path == "/delay":
            self.response_wait_started.set()
        delay = int(self.headers.get("x-test-delay", "0"))
        if delay: time.sleep(delay / 1000)
        # Fast responses exercise the cached formatting path.
        if self.path != "/fast":
            time.sleep(0.08)
        self.send_response(503 if self.path == "/error" else 200)
        self.send_header("Server-Timing", 'app;dur=7;desc="query, render"')
        self.send_header("Server-Timing", "opaque_layer;dur=9")
        self.send_header("Content-Length", "2")
        self.send_header("x-test-upstream-connection", str(self.client_address[1]))
        self.end_headers()
        if self.path == "/fast":
            self.wfile.write(b"ok")
            return
        self.wfile.write(b"o")
        self.wfile.flush()
        if self.path == "/stream":
            time.sleep(1.5)
        self.wfile.write(b"k")
        if self.path == "/response-delay":
            self.rfile.read(int(self.headers.get("Content-Length", "0")))

    def log_message(self, *_args: object) -> None:
        pass


class ServerTimingIntegrationTest(unittest.TestCase):
    def test_request_receive_becomes_available_during_response_delay(self):
        Backend.response_wait_started.clear()
        with closing(http.client.HTTPConnection("127.0.0.1", self.inner_port, timeout=2)) as connection:
            connection.putrequest("GET", "/response-delay")
            connection.putheader("Content-Length", "2")
            connection.endheaders(b"x")
            self.assertTrue(Backend.response_wait_started.wait(1), "Late response filter never started")
            connection.send(b"k")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(), b"ok")
            timing = response.getheader("Server-Timing")
            received = re.search(r"e_rx;dur=([0-9.]+)", timing)
            self.assertIsNotNone(received, timing)
            self.assertGreaterEqual(float(received.group(1)), 50, timing)
            self.assertIsNone(response.getheader("x-ccsn-envoy-timing"))


    def test_sustained_fast_responses_preserve_all_metrics(self):
        for port in [self.inner_port, self.outer_port]:
            with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=2)) as connection:
                for _ in range(1000):
                    connection.request("GET", "/fast")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.read(), b"ok")
                    timing = response.getheader("Server-Timing")
                    for metric in ["e_hdr", "e_tcp", "e_ttfb", "e_pool", "e_rx"]:
                        self.assertEqual(timing.count(metric + ";"), 1 if port == self.inner_port else 2)
                    self.assertEqual(timing.count("e_tls;"), 1)
                    self.assertNotIn(";dur=;", timing)
                    self.assertIsNone(response.getheader("x-ccsn-envoy-timing"))

    def test_changed_intervals_are_measured_on_each_response(self):
        with closing(http.client.HTTPConnection("127.0.0.1", self.inner_port, timeout=2)) as connection:
            for delay in [0, 2, 17, 31, 1, 0, 12, 8]:
                connection.request("GET", "/fast", headers={"x-test-delay": str(delay)})
                response = connection.getresponse()
                self.assertEqual(response.read(), b"ok")
                timing = response.getheader("Server-Timing")
                duration = float(re.search(r"e_ttfb;dur=([0-9.]+)", timing).group(1))
                self.assertGreaterEqual(duration, max(delay - 2, 0), timing)
                self.assertEqual(timing.count("e_ttfb;"), 1)
                self.assertIsNone(response.getheader("x-ccsn-envoy-timing"))

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
        if role.startswith("nginx") and os.environ.get("TIMING_TEST_NGINX_ARCH"):
            command.extend(["--arch", os.environ["TIMING_TEST_NGINX_ARCH"]])
        if image == ENVOY_IMAGE:
            architecture = os.environ.get("TIMING_TEST_ENVOY_ARCH") or {"x86_64": "amd64", "aarch64": "arm64"}[platform.machine()]
            command.extend(["--arch", architecture, "--volume",
                            f"{MODULE_DIR / ('server-timing-' + architecture + '.module')}:/etc/istio/server-timing/server-timing.so:ro"])
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
        for patch in cls.patches:
            if patch["applyTo"] == "ROUTE_CONFIGURATION":
                route.update(copy.deepcopy(patch["patch"]["value"]))
        filters = [*(copy.deepcopy(patch["patch"]["value"]) for patch in cls.patches if patch["applyTo"] == "HTTP_FILTER"), {
            "name": "test.local_reply",
            "typed_config": {
                "@type": "type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua",
                "default_source_code": {"inline_string": """
function envoy_on_request(handle)
  if handle:headers():get(":path") == "/response-delay" then
    handle:streamInfo():dynamicMetadata():set("test", "response_delay", true)
  end
  if handle:headers():get(":path") == "/deny" then
    handle:respond({[":status"] = "401"}, "denied")
  end
end
function envoy_on_response(handle)
  local metadata = handle:streamInfo():dynamicMetadata():get("test")
  if metadata and metadata.response_delay then
    handle:httpCall("backend", {[":method"] = "GET", [":path"] = "/delay", [":authority"] = "localhost"}, "", 1000)
  end
end
"""},
            },
        }, {
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
        hcm = bootstrap["static_resources"]["listeners"][0]["filter_chains"][0]["filters"][0]["typed_config"]
        for patch in cls.patches:
            if patch["applyTo"] == "NETWORK_FILTER":
                hcm.update(copy.deepcopy(patch["patch"]["value"]["typed_config"]))
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
                      "--disable-hot-restart", "--concurrency", os.environ.get("TIMING_TEST_WORKERS", "1"), "-l", "error"])

    @classmethod
    def start_nginx(cls, backend_port: int) -> None:
        cls.nginx_image = yaml.safe_load((NGINX_DIR / "deployment.yaml").read_text())["spec"]["template"]["spec"]["containers"][0]["image"]
        if os.environ.get("TIMING_TEST_NGINX_ARCH") == "arm64":
            cls.nginx_image = "nginx:mainline-alpine@sha256:7dd09a6c4f8cab9a2d2cb98fb39790f220e8bc2ea106b2cebde64b90405e0be8"
        main = yaml.safe_load((NGINX_DIR / "nginx-config.yaml").read_text())["data"]["nginx.conf"]
        (cls.artifacts / "nginx.conf").write_text(main)
        (cls.artifacts / "nginx-servers").mkdir()
        architecture = os.environ.get("TIMING_TEST_NGINX_ARCH") or {
            "x86_64": "amd64", "aarch64": "arm64",
        }[platform.machine()]
        module = NGINX_DIR / f"server-timing-{architecture}.module"
        cls.native_mounts = [f"{module}:/etc/nginx/native-modules/ngx_http_ccsn_server_timing_module.so:ro"]
        # Reuse the production module and location handler; change listeners/backends.
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
            *cls.native_mounts,
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
            timing = ", ".join(value for key, value in headers if key.lower() == "server-timing")
            self.assertFalse(timing.rstrip().endswith(","), timing)
            return response.status, timing

    def test_each_proxy_works_independently(self) -> None:
        _, nginx = self.fetch(self.nginx_port, "/standalone")
        self.assertIn("nginx_upstream_headers", nginx)
        self.assertRegex(nginx, r"nginx_headers;dur=[0-9]+;")
        self.assertRegex(nginx, r"nginx_upstream_headers;dur=[0-9]+;")
        self.assertNotIn("e_hdr;", nginx)
        _, envoy = self.fetch(self.inner_port)
        self.assertIn("e_ttfb", envoy)
        self.assertNotIn("nginx_", envoy)

    def test_chain_preserves_all_hops_and_tls(self) -> None:
        _, timing = self.fetch(self.nginx_port)
        for metric in ['app;dur=7;desc="query, render"', "opaque_layer;dur=9", "nginx_upstream_connect", "nginx_upstream_headers",
                       "e_tcp", "e_tls", "e_ttfb", "e_hdr"]:
            self.assertIn(metric, timing)
        self.assertEqual(timing.count("e_ttfb;"), 2)
        self.assertIn('desc=timing-inner', timing)
        self.assertIn('desc=timing-outer', timing)
        self.assertNotIn("forged", timing)
        self.assertNotIn('e_tls;dur=;desc=timing-outer', timing)
        self.assertNotRegex(timing, r'e_tls;[^,]*desc=timing-outer')
        self.assertNotIn("dur=-", timing)
        self.assertNotIn("dur=;", timing)
        # Both native total durations and seconds-to-milliseconds maps must
        # reflect the 80 ms backend wait, rather than completion-only zeros.
        for metric in ["nginx_headers", "nginx_upstream_headers", "e_hdr", "e_ttfb"]:
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
                self.assertIn("e_hdr", timing)

    def test_elapsed_headers_include_response_filter_wait(self) -> None:
        status, timing = self.fetch(self.inner_port, "/response-delay")
        self.assertEqual(status, 200)
        elapsed = float(re.search(r"e_hdr;dur=([0-9.]+)", timing).group(1))
        upstream = float(re.search(r"e_ttfb;dur=([0-9.]+)", timing).group(1))
        self.assertGreaterEqual(elapsed, 140, timing)
        self.assertGreaterEqual(upstream, 70, timing)
        self.assertGreaterEqual(elapsed - upstream, 60, timing)

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
        if os.environ.get("TIMING_TEST_NGINX_ARCH"):
            command.extend(["--arch", os.environ["TIMING_TEST_NGINX_ARCH"]])
        for mount in self.native_mounts:
            command.extend(["--volume", mount])
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
        identities = []
        with closing(http.client.HTTPSConnection("localhost", self.tls_port, context=context, timeout=5)) as conn:
            for _ in range(2):
                conn.request("GET", "/")
                response = conn.getresponse()
                timing = response.getheader("Server-Timing")
                self.assertEqual(response.status, 200)
                self.assertIn("e_pool;", timing)
                self.assertIn("e_tls;", timing)
                identities.append(response.getheader("x-test-upstream-connection"))
                response.read()
        self.assertIsNotNone(identities[0])
        self.assertEqual(identities[0], identities[1], "Upstream TLS connection was not reused")

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
            self.assertIn("e_hdr;", timing)
            self.assertEqual(timing.count("e_"), 1)
            self.assertNotIn("__end", timing)
            self.assertNotIn("dur=;", timing)
            self.assertFalse(timing.rstrip().endswith(","), timing)
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


original_backend_get = Backend.do_GET
peer_timing = 'e_tls;dur=;desc="peer-layer"'
opaque_timing = 'alien_layer;dur=;desc="comma, opaque"'
def with_opaque_peer(self):
    if self.path != "/opaque-peer": return original_backend_get(self)
    self.send_response(200)
    self.send_header("Server-Timing", peer_timing)
    self.send_header("Server-Timing", opaque_timing)
    self.send_header("Content-Length", "2")
    self.end_headers()
    self.wfile.write(b"ok")
Backend.do_GET = with_opaque_peer

def test_opaque_peer_fields_are_not_repaired(self):
    for port in [self.inner_port, self.outer_port, self.nginx_port]:
        with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=2)) as connection:
            connection.request("GET", "/opaque-peer")
            response = connection.getresponse()
            self.assertEqual(response.read(), b"ok")
            values = [v for k, v in response.getheaders() if k.lower() == "server-timing"]
            self.assertIn(peer_timing, values)
            self.assertIn(opaque_timing, values)
            self.assertNotIn('e_tls;dur=;desc=timing-outer', ",".join(values))
ServerTimingIntegrationTest.test_opaque_peer_fields_are_not_repaired = test_opaque_peer_fields_are_not_repaired

if __name__ == "__main__":
    unittest.main()
