"""Ensure capacity experiments cannot accept incomplete timing responses."""
import importlib.util
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location(
    "benchmark_server_timing", Path(__file__).resolve().parents[1] / "benchmark_server_timing.py"
)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)

# The fixture has one TLS Envoy, one plaintext Envoy, Nginx, and an application.
CHAIN_TIMING = ",".join([
    "app;dur=1",
    'envoy_headers;dur=0;desc="inner"',
    'envoy_upstream_tcp;dur=0;desc="inner"',
    'envoy_upstream_tls;dur=0;desc="inner"',
    'envoy_upstream_headers;dur=0;desc="inner"',
    'envoy_upstream_pool;dur=0;desc="inner"',
    'envoy_request_receive;dur=0;desc="inner"',
    'envoy_headers;dur=0;desc="outer"',
    'envoy_upstream_tcp;dur=0;desc="outer"',
    'envoy_upstream_headers;dur=0;desc="outer"',
    'envoy_upstream_pool;dur=0;desc="outer"',
    'envoy_request_receive;dur=0;desc="outer"',
    'nginx_headers;dur=0001;desc="edge"',
    'nginx_upstream_connect;dur=0000;desc="edge attempt 1"',
    'nginx_upstream_headers;dur=0001;desc="edge attempt 1"',
])


class BenchmarkTimingValidationTest(unittest.TestCase):
    def test_accepts_real_zeros_and_omits_plaintext_tls(self):
        benchmark.validate_timing("chain", "on", [("Server-Timing", CHAIN_TIMING)])

    def test_rejects_empty_duration_from_failed_conversion(self):
        malformed = CHAIN_TIMING + ',envoy_upstream_tls;dur=;desc="outer"'
        with self.assertRaisesRegex(ValueError, "Invalid benchmark timing"):
            benchmark.validate_timing("chain", "on", [("Server-Timing", malformed)])

    def test_rejects_dropped_upstream_metric(self):
        incomplete = CHAIN_TIMING.replace(',envoy_upstream_headers;dur=0;desc="outer"', "")
        with self.assertRaisesRegex(ValueError, "metrics differ"):
            benchmark.validate_timing("chain", "on", [("Server-Timing", incomplete)])

    def test_rejects_private_helper_leak(self):
        with self.assertRaisesRegex(ValueError, "helper leaked"):
            benchmark.validate_timing("chain", "on", [
                ("Server-Timing", CHAIN_TIMING), ("x-ccsn-envoy-timing", "private")
            ])


class BenchmarkEnvironmentValidationTest(unittest.TestCase):
    def test_detects_builds_without_blocking_normal_apps(self):
        with patch.object(benchmark, "command", return_value="chrome\nsoong_build\nrustc\nclang-21\n"):
            self.assertEqual(benchmark.active_builds(), ["clang-21", "rustc", "soong_build"])

    def test_build_interference_persists_invalidation_and_prevents_report(self):
        run = benchmark.Benchmark.__new__(benchmark.Benchmark)
        run.args = SimpleNamespace(require_idle_builds=True)
        run.state = {"samples": []}
        run.persist = Mock()
        with patch.object(benchmark, "active_builds", return_value=["soong_build"]):
            with self.assertRaisesRegex(RuntimeError, "invalidated by build"):
                run.require_idle()
        run.persist.assert_called_once()
        with self.assertRaisesRegex(RuntimeError, "cannot be used for acceptance"):
            run.report()

    def test_manual_invalidation_marker_prevents_report(self):
        run = benchmark.Benchmark.__new__(benchmark.Benchmark)
        run.state = {"samples": []}
        with tempfile.TemporaryDirectory(dir=benchmark.ROOT.parent / "task-logs") as directory:
            run.output = Path(directory)
            (run.output / "invalid.json").write_text('{"reason":"Concurrent compilation"}')
            with self.assertRaisesRegex(RuntimeError, "cannot be used for acceptance"):
                run.report()


if __name__ == "__main__":
    unittest.main()
