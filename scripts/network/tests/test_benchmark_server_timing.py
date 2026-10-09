"""Ensure capacity experiments cannot accept incomplete timing responses."""
import importlib.util
import json
import socket
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
    def test_fixture_ports_are_distinct_and_reservations_are_released(self):
        keys = [f"role_{i}" for i in range(256)]
        ports = benchmark.allocate_ports(keys)
        self.assertEqual(set(ports), set(keys))
        self.assertEqual(len(set(ports.values())), len(keys))
        for number in ports.values():
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", number))

    def test_resume_rejects_missing_or_changed_harness_identity(self):
        with tempfile.TemporaryDirectory(dir=benchmark.ROOT.parent / "task-logs") as directory:
            output = Path(directory)
            for identity in [None, "another-harness"]:
                state = {"samples": [{"key": "existing-sample"}], "containers": {}}
                if identity is not None:
                    state["harness_sha256"] = identity
                (output / "state.json").write_text(json.dumps(state))
                with self.subTest(identity=identity):
                    with self.assertRaisesRegex(ValueError, "harness changed or was not recorded"):
                        benchmark.Benchmark(SimpleNamespace(output=output, stage="capacity"))

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


class BenchmarkThroughputBudgetTest(unittest.TestCase):
    def test_component_budgets_apply_independently(self):
        baseline = {"rps": 1000, "rps_range": [995, 1005]}
        config = {"throughput_budgets_percent": {"nginx": 5, "envoy": 10}}
        for scenario, loss, expected in [("nginx", 4, True), ("nginx", 6, False),
                                         ("envoy", 9, True), ("envoy", 11, False)]:
            with self.subTest(scenario=scenario, loss=loss):
                result = benchmark.throughput_acceptance(scenario, loss, baseline, config)
                self.assertEqual(result["throughput_point_estimate_pass"], expected)
                self.assertNotEqual(result["status"], "passed")

    def test_historical_runs_retain_original_gate(self):
        result = benchmark.throughput_acceptance("nginx", 4, {"rps": 1000, "rps_range": [1000, 1000]}, {})
        self.assertEqual(result["threshold_percent"], 1)
        self.assertEqual(result["status"], "failed")

    def test_chain_has_no_invented_combined_gate(self):
        result = benchmark.throughput_acceptance("chain", 20, {"rps": 1000, "rps_range": [1000, 1000]},
                                                 {"throughput_budgets_percent": {"nginx": 5, "envoy": 10}})
        self.assertEqual(result["status"], "diagnostic")
        self.assertNotIn("threshold_percent", result)


class BenchmarkCapacityConfidenceTest(unittest.TestCase):
    def setUp(self):
        self.config = {"rounds": 7, "connections": [16, 64], "require_idle_builds": True,
                       "confidence_method": "paired_round_bootstrap_95pct",
                       "throughput_budgets_percent": {"nginx": 5, "envoy": 10}}
        self.baseline = {"rps": 1000, "rps_range": [1000, 1000]}

    def samples(self, on):
        return [{"stage": "capacity", "scenario": "nginx", "mode": mode,
                 "round": r, "connections": c, "rps": value}
                for r in range(7) for mode, c, value in [
                    ("off", 16, 1000), ("off", 64, 500),
                    ("on", 16, 900), ("on", 64, on[r])]]

    def test_peak_is_reselected_and_stable_complete_sweep_can_pass(self):
        confidence = benchmark.capacity_confidence(self.samples([960] * 7), "nginx", self.config)
        self.assertAlmostEqual(confidence["upper_loss_percent"], 4)
        result = benchmark.throughput_acceptance("nginx", 4, self.baseline, self.config, confidence)
        self.assertEqual(result["status"], "passed")

    def test_uncertainty_prevents_passing_a_good_point_estimate(self):
        confidence = benchmark.capacity_confidence(self.samples([960] * 4 + [900] * 3), "nginx", self.config)
        self.assertGreater(confidence["upper_loss_percent"], 5)
        result = benchmark.throughput_acceptance("nginx", 4, self.baseline, self.config, confidence)
        self.assertTrue(result["throughput_point_estimate_pass"])
        self.assertEqual(result["status"], "inconclusive")

    def test_partial_or_short_sweeps_have_no_confidence_claim(self):
        samples = self.samples([960] * 7)
        self.assertIsNone(benchmark.capacity_confidence(samples[:-1], "nginx", self.config))
        self.assertIsNone(benchmark.capacity_confidence(samples, "nginx", {**self.config, "rounds": 5}))

    def test_uncontrolled_noisy_or_diagnostic_runs_cannot_pass(self):
        confidence = {"upper_loss_percent": 4}
        for config, baseline, diagnostic in [
                ({**self.config, "require_idle_builds": False}, self.baseline, False),
                (self.config, {"rps": 1000, "rps_range": [900, 1100]}, False),
                (self.config, self.baseline, True)]:
            with self.subTest(config=config, baseline=baseline, diagnostic=diagnostic):
                result = benchmark.throughput_acceptance("nginx", 4, baseline, config, confidence, diagnostic)
                self.assertNotEqual(result["status"], "passed")


class BenchmarkNativeReferenceTest(unittest.TestCase):
    def test_native_reference_loads_its_own_binary(self):
        with tempfile.TemporaryDirectory(dir=benchmark.ROOT.parent / "task-logs") as directory:
            output = Path(directory)
            run = benchmark.Benchmark.__new__(benchmark.Benchmark)
            run.output = output
            run.timing_dir = output / "candidate"
            run.reference_dir = output / "previous"
            run.nginx_image = "nginx:test"
            run.container = Mock()
            for source in [run.timing_dir, run.reference_dir]:
                source.mkdir()
                (source / "module-load.conf").write_text("load_module /module/server-timing.so;\n")
            run.nginx("nginx_reference", 18080, 19090, "reference", 16)
            run.nginx("nginx_on", 18081, 19090, "on", 16)
            self.assertIn("load_module /reference/server-timing.so;", (output / "nginx_reference.conf").read_text())
            self.assertIn("load_module /module/server-timing.so;", (output / "nginx_on.conf").read_text())


if __name__ == "__main__":
    unittest.main()
