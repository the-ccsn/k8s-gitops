"""Resumable local A/B benchmark; does not write to a cluster.

nix shell nixpkgs#wrk nixpkgs#vegeta -c uv run --with pyyaml python \
  scripts/network/benchmark_server_timing.py --output ../task-logs/server-timing-benchmark

Each proxy has one worker pinned to its own physical core. Containers are
stopped after each invocation and retained for inspection. Results/configs
are persisted after each sample. --stage selects capacity, latency, or report.
"""
from __future__ import annotations

import argparse
import copy
import http.client
import hashlib
import json
import os
import re
import resource
import signal
import socket
import statistics
import subprocess
import time
from contextlib import closing
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
NGINX_DIR = ROOT / "infra/configs/base/i319-reroute"
ENVOY_IMAGE = "registry.istio.io/release/proxyv2:1.30.0-rc.0-distroless"


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def save(path: Path, value: object) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def physical_cpus() -> list[int]:
    found = {}
    for cpu in sorted(os.sched_getaffinity(0)):
        topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        key = ((topology / "physical_package_id").read_text(), (topology / "core_id").read_text())
        found.setdefault(key, cpu)
    if len(found) < 6:
        raise RuntimeError("At least six available physical cores are required")
    return list(found.values())[:6]


class Benchmark:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.output = args.output.resolve()
        if not self.output.is_relative_to(ROOT.parent):
            raise ValueError("Artifacts must remain inside the workspace")
        self.output.mkdir(parents=True, exist_ok=True)
        self.path = self.output / "state.json"
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {"samples": [], "containers": {}}
        if args.stage == "report":
            return
        self.state.setdefault("role_cpus", {})
        config = {"rounds": args.rounds, "duration": args.duration, "rate": args.rate, "cpus": physical_cpus(), "scenarios": args.scenarios}
        if "config" in self.state and self.state["config"] != config:
            raise ValueError("Existing run parameters differ; select another output directory")
        self.state["config"] = config
        sources = [args.envoy_policy.resolve(), *sorted(NGINX_DIR.glob("server-timing*"))]
        source_hash = hashlib.sha256(b"".join(str(p.relative_to(ROOT.parent)).encode() + b"\0" + p.read_bytes() for p in sources)).hexdigest()
        if self.state.get("source_sha256", source_hash) != source_hash:
            raise ValueError("Timing implementation changed; select another output directory")
        self.state["source_sha256"] = source_hash
        self.cpus = config["cpus"]
        self.client_cpus = ",".join(map(str, self.cpus[4:6]))
        self.nginx_image = yaml.safe_load((NGINX_DIR / "deployment.yaml").read_text())["spec"]["template"]["spec"]["containers"][0]["image"]
        policy = args.envoy_policy.resolve()
        if not policy.is_relative_to(ROOT.parent):
            raise ValueError("Candidate policy must remain inside the workspace")
        self.patches = yaml.safe_load(policy.read_text())["items"][0]["spec"]["configPatches"]
        self.state.setdefault("environment", {
            "nginx_image": self.nginx_image, "envoy_image": ENVOY_IMAGE,
            "cpu_model": next(line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name")),
            "initial_load": Path("/proc/loadavg").read_text().strip(),
            "commit": command("git", "-C", str(ROOT), "rev-parse", "HEAD").strip(),
            "wrk": subprocess.run(["wrk", "--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.splitlines()[0],
            "vegeta": command("vegeta", "-version").strip(),
        })
        self.persist()

    def persist(self) -> None:
        save(self.path, self.state)

    def container(self, role: str, cpu: int, image: str, entrypoint: str, args: list[str]) -> str:
        self.state["role_cpus"][role] = cpu
        if role in self.state["containers"]:
            name = self.state["containers"][role]
            if command("podman", "inspect", "--format", "{{.State.Running}}", name).strip() != "true":
                command("podman", "start", name)
            return role
        name = f"ccsn-timing-bench-{role}-{self.state['run_id']}"
        command("podman", "run", "--detach", "--name", name, "--hostname", f"benchmark-{role}",
                "--user", "0", "--network", "host",
                "--entrypoint", entrypoint, "--volume", f"{self.output}:/bench:ro",
                "--volume", f"{NGINX_DIR}:/module:ro", image, *args)
        self.state["containers"][role] = name
        self.persist()
        return role

    def nginx(self, role: str, listen: int, upstream: int, enabled: bool, cpu: int) -> str:
        text = f"""
{'load_module /usr/lib/nginx/modules/ngx_http_js_module.so;' if enabled else ''}
pcre_jit on;
user root;
worker_processes 1;
events {{ worker_connections 8192; }}
http {{
    access_log off;
    error_log /dev/stderr warn;
    keepalive_requests 1000000;
    {'js_import server_timing from /module/server-timing.js; include /module/server-timing-maps.conf;' if enabled else ''}
    upstream backend {{ server 127.0.0.1:{upstream}; keepalive 128; }}
    server {{
        listen 127.0.0.1:{listen};
        location / {{
            {'include /module/server-timing-headers.conf;' if enabled else ''}
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_buffering off;
            proxy_request_buffering off;
            proxy_pass http://backend;
        }}
    }}
}}
"""
        (self.output / f"{role}.conf").write_text(text)
        return self.container(role, cpu, self.nginx_image, "nginx", ["-c", f"/bench/{role}.conf", "-g", "daemon off;"])

    def envoy(self, role: str, listen: int, upstream: int, enabled: bool, cpu: int, tls: bool = False) -> str:
        route = {"name": "benchmark", "virtual_hosts": [{"name": "backend", "domains": ["*"], "routes": [{
            "match": {"prefix": "/"}, "route": {"cluster": "backend"},
        }]}]}
        filters = []
        if enabled:
            route.update(copy.deepcopy(self.patches[0]["patch"]["value"]))
            filters.extend(copy.deepcopy(patch["patch"]["value"]) for patch in self.patches[1:])
        filters.append({"name": "envoy.filters.http.router", "typed_config": {
            "@type": "type.googleapis.com/envoy.extensions.filters.http.router.v3.Router",
        }})
        cluster = {"name": "backend", "connect_timeout": "1s", "type": "STATIC", "load_assignment": {
            "cluster_name": "backend", "endpoints": [{"lb_endpoints": [{"endpoint": {
                "address": {"socket_address": {"address": "127.0.0.1", "port_value": upstream}},
            }}]}],
        }}
        if tls:
            cluster["transport_socket"] = {"name": "envoy.transport_sockets.tls", "typed_config": {
                "@type": "type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.UpstreamTlsContext",
                "common_tls_context": {"validation_context": {"trusted_ca": {"filename": "/bench/tls.crt"}}},
            }}
        bootstrap = {"static_resources": {"clusters": [cluster], "listeners": [{
            "name": "http", "address": {"socket_address": {"address": "127.0.0.1", "port_value": listen}},
            "filter_chains": [{"filters": [{"name": "envoy.filters.network.http_connection_manager", "typed_config": {
                "@type": "type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager",
                "stat_prefix": "benchmark", "route_config": route, "http_filters": filters,
            }}]}],
        }]}}
        (self.output / f"{role}.yaml").write_text(yaml.safe_dump(bootstrap))
        return self.container(role, cpu, ENVOY_IMAGE, "/usr/local/bin/envoy", ["-c", f"/bench/{role}.yaml",
                              "--disable-hot-restart", "--concurrency", "1", "-l", "error"])

    def prepare(self) -> None:
        self.state.setdefault("run_id", str(time.time_ns()))
        ports = self.state.setdefault("ports", {key: port() for key in ["backend", "backend_tls", "nginx_off", "nginx_on", "envoy_off", "envoy_on", "outer_off", "outer_on", "chain_off", "chain_on"]})
        if not (self.output / "tls.crt").exists():
            command("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(self.output / "tls.key"),
                    "-out", str(self.output / "tls.crt"), "-days", "1", "-subj", "/CN=localhost")
        (self.output / "backend.conf").write_text(f"""
pcre_jit on;
user root;
worker_processes 1;
events {{ worker_connections 8192; }}
http {{
    access_log off;
    error_log /dev/stderr warn;
    keepalive_requests 1000000;
    server {{
        listen 127.0.0.1:{ports['backend']};
        listen 127.0.0.1:{ports['backend_tls']} ssl;
        ssl_certificate /bench/tls.crt;
        ssl_certificate_key /bench/tls.key;
        add_header Server-Timing 'app;dur=1';
        location / {{ return 200 '{'x' * 256}'; }}
    }}
}}
""")
        self.container("backend", self.cpus[3], self.nginx_image, "nginx", ["-c", "/bench/backend.conf", "-g", "daemon off;"])
        self.state["endpoints"] = {}
        for enabled in [False, True]:
            mode = "on" if enabled else "off"
            inner = self.envoy(f"envoy_{mode}", ports[f"envoy_{mode}"], ports["backend_tls"], enabled, self.cpus[2], tls=True)
            outer = self.envoy(f"outer_{mode}", ports[f"outer_{mode}"], ports[f"envoy_{mode}"], enabled, self.cpus[1])
            nginx = self.nginx(f"nginx_{mode}", ports[f"nginx_{mode}"], ports["backend"], enabled, self.cpus[0])
            chain = self.nginx(f"chain_{mode}", ports[f"chain_{mode}"], ports[f"outer_{mode}"], enabled, self.cpus[0])
            for scenario, roles, endpoint in [("nginx", [nginx], f"nginx_{mode}"), ("envoy", [inner], f"envoy_{mode}"),
                                               ("chain", [chain, outer, inner], f"chain_{mode}")]:
                self.state["endpoints"][f"{scenario}_{mode}"] = {"url": f"http://127.0.0.1:{ports[endpoint]}/", "roles": roles}
        self.persist()
        for endpoint in self.state["endpoints"].values():
            endpoint_port = int(endpoint["url"].split(":")[2].split("/")[0])
            deadline = time.monotonic() + 15
            while True:
                try:
                    with closing(http.client.HTTPConnection("127.0.0.1", endpoint_port, timeout=1)) as conn:
                        conn.request("GET", "/")
                        response = conn.getresponse()
                        assert response.status == 200 and len(response.read()) == 256
                        endpoint["header_bytes"] = sum(len(k.encode()) + len(v.encode()) + 4 for k, v in response.getheaders())
                        endpoint["server_timing"] = response.getheader("Server-Timing")
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.1)
        self.cgroups = {}
        for role, name in self.state["containers"].items():
            pid = command("podman", "inspect", "--format", "{{.State.Pid}}", name).strip()
            relative = Path(f"/proc/{pid}/cgroup").read_text().strip().split("::", 1)[1]
            self.cgroups[role] = Path("/sys/fs/cgroup") / relative.lstrip("/")
            assert (self.cgroups[role] / "cpu.stat").exists()
            # The OCI runtime resets inherited affinity. Pin every existing
            # process/thread explicitly; future threads inherit this affinity.
            for process in (self.cgroups[role] / "cgroup.procs").read_text().split():
                for task in Path(f"/proc/{process}/task").iterdir():
                    os.sched_setaffinity(int(task.name), {self.state["role_cpus"][role]})
                    assert os.sched_getaffinity(int(task.name)) == {self.state["role_cpus"][role]}
        self.persist()
        print(f"Prepared {len(self.state['containers'])} containers; CPUs {self.cpus}", flush=True)

    def counters(self, roles: list[str]) -> dict:
        result = {}
        for role in roles:
            group = self.cgroups[role]
            cpu = dict(line.split() for line in (group / "cpu.stat").read_text().splitlines())
            memory = dict(line.split() for line in (group / "memory.stat").read_text().splitlines())
            result[role] = {"cpu_us": int(cpu["usage_usec"]), "anon_bytes": int(memory["anon"]),
                            "throttled_us": int(cpu.get("throttled_usec", 0))}
        return result

    def sample(self, scenario: str, mode: str, stage: str, round_number: int) -> None:
        key = f"{stage}_{scenario}_{mode}_{round_number}"
        if any(item["key"] == key for item in self.state["samples"]):
            return
        endpoint = self.state["endpoints"][f"{scenario}_{mode}"]
        prefix = self.output / key
        command("taskset", "-c", self.client_cpus, "wrk", "-t2", "-c64", "-d2s", endpoint["url"])
        roles = endpoint["roles"] + ["backend"]
        if stage == "capacity":
            args = ["taskset", "-c", self.client_cpus, "wrk", "-t2", "-c64", f"-d{self.args.duration}s", "--latency", endpoint["url"]]
        else:
            targets = self.output / "targets.txt"
            targets.write_text(f"GET {endpoint['url']}\n")
            args = ["taskset", "-c", self.client_cpus, "vegeta", "-cpus", "2", "attack", "-targets", str(targets),
                    "-rate", str(self.args.rate), "-duration", f"{self.args.duration}s", "-workers", "16", "-max-workers", "256",
                    "-connections", "64", "-max-connections", "64", "-http2=false", "-timeout", "2s", "-output", str(prefix) + ".bin"]
        before = self.counters(roles)
        usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
        memory_samples = []
        started = time.monotonic()
        with prefix.with_suffix(".log").open("wb") as logfile:
            process = subprocess.Popen(args, stdout=logfile, stderr=subprocess.STDOUT)
            try:
                while process.poll() is None:
                    memory_samples.append(self.counters(roles))
                    time.sleep(0.2)
            except BaseException:
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait()
                raise
            if process.returncode:
                raise RuntimeError(f"Load generator failed; inspect {prefix}.log")
        elapsed = time.monotonic() - started
        after = self.counters(roles)
        usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        log = prefix.with_suffix(".log").read_text()
        if stage == "capacity":
            requests = int(re.search(r"(\d+) requests in", log)[1])
            rps = float(re.search(r"Requests/sec:\s+([0-9.]+)", log)[1])
            if "Socket errors:" in log or "Non-2xx or 3xx responses:" in log:
                raise RuntimeError(f"Invalid capacity sample; inspect {prefix}.log")
            result = {"requests": requests, "rps": rps}
        else:
            report = json.loads(command("vegeta", "report", "-type=json", str(prefix) + ".bin"))
            save(prefix.with_suffix(".report.json"), report)
            if report["success"] != 1 or report["errors"]:
                raise RuntimeError(f"Invalid latency sample; inspect {prefix}.report.json")
            result = {"requests": report["requests"], "rps": report["throughput"],
                      "p50_ms": report["latencies"]["50th"] / 1e6,
                      "p95_ms": report["latencies"]["95th"] / 1e6,
                      "p99_ms": report["latencies"]["99th"] / 1e6}
        per_role = {}
        for role in roles:
            cpu_us = after[role]["cpu_us"] - before[role]["cpu_us"]
            per_role[role] = {"cpu_us_per_request": cpu_us / result["requests"], "cpu_cores": cpu_us / elapsed / 1e6,
                              "anon_mib": statistics.median(item[role]["anon_bytes"] for item in memory_samples) / 2**20,
                              "peak_anon_mib": max(item[role]["anon_bytes"] for item in memory_samples) / 2**20,
                              "throttled_us": after[role]["throttled_us"] - before[role]["throttled_us"]}
        result.update({"key": key, "scenario": scenario, "mode": mode, "stage": stage, "round": round_number,
                       "elapsed_s": elapsed, "load_after": Path("/proc/loadavg").read_text().strip(), "roles": per_role,
                       "proxy_cpu_us_per_request": sum(per_role[role]["cpu_us_per_request"] for role in endpoint["roles"]),
                       "proxy_anon_mib": sum(per_role[role]["anon_mib"] for role in endpoint["roles"]),
                       "client_cpu_cores": ((usage_after.ru_utime + usage_after.ru_stime) - (usage_before.ru_utime + usage_before.ru_stime)) / elapsed})
        self.state["samples"].append(result)
        self.persist()
        print(f"{key}: {result['rps']:.0f} req/s, proxy CPU {result['proxy_cpu_us_per_request']:.2f} us/req" +
              (f", p99 {result['p99_ms']:.3f} ms" if stage == "latency" else ""), flush=True)

    def measure(self, stage: str) -> None:
        for round_number in range(self.args.rounds):
            for scenario in self.state["config"].get("scenarios", ["nginx", "envoy", "chain"]):
                for mode in (["off", "on"] if round_number % 2 == 0 else ["on", "off"]):
                    self.sample(scenario, mode, stage, round_number)

    def report(self) -> None:
        summary = {"environment": self.state["environment"], "config": self.state["config"], "source_sha256": self.state.get("source_sha256"), "results": {}}
        for scenario in self.state["config"].get("scenarios", ["nginx", "envoy", "chain"]):
            entry = {}
            for stage in ["capacity", "latency"]:
                for mode in ["off", "on"]:
                    samples = [s for s in self.state["samples"] if (s["scenario"], s["stage"], s["mode"]) == (scenario, stage, mode)]
                    if not samples:
                        continue
                    metrics = ["rps", "proxy_cpu_us_per_request", "proxy_anon_mib", "client_cpu_cores"]
                    if stage == "latency":
                        metrics += ["p50_ms", "p95_ms", "p99_ms"]
                    entry[f"{stage}_{mode}"] = {name: statistics.median(s[name] for s in samples) for name in metrics}
                    entry[f"{stage}_{mode}"]["rps_range"] = [min(s["rps"] for s in samples), max(s["rps"] for s in samples)]
                    entry[f"{stage}_{mode}"]["samples"] = len(samples)
            for stage in ["capacity", "latency"]:
                if f"{stage}_on" in entry and f"{stage}_off" in entry:
                    entry[f"{stage}_change_percent"] = {key: (entry[f"{stage}_on"][key] / value - 1) * 100
                                                         for key, value in entry[f"{stage}_off"].items()
                                                         if isinstance(value, (int, float)) and value != 0 and key != "samples"}
            if "capacity_change_percent" in entry and "latency_change_percent" in entry:
                throughput_drop = -entry["capacity_change_percent"]["rps"]
                cpu_increase = entry["latency_change_percent"]["proxy_cpu_us_per_request"]
                baseline = entry["capacity_off"]
                spread = (baseline["rps_range"][1] - baseline["rps_range"][0]) / baseline["rps"] * 100
                entry["acceptance"] = {
                    "threshold_percent": 1,
                    "cpu_per_request_point_estimate_pass": cpu_increase <= 1,
                    "throughput_point_estimate_pass": throughput_drop <= 1,
                    "baseline_throughput_spread_percent": spread,
                    # A point estimate on a noisy workstation cannot establish a 1% limit.
                    "status": "failed" if cpu_increase > 1 or throughput_drop > 1 else "inconclusive",
                }
            entry["extra_header_bytes"] = self.state["endpoints"][f"{scenario}_on"]["header_bytes"] - self.state["endpoints"][f"{scenario}_off"]["header_bytes"]
            summary["results"][scenario] = entry
        save(self.output / "summary.json", summary)
        print(json.dumps(summary, indent=2), flush=True)

    def stop(self) -> None:
        for role, name in reversed(list(self.state["containers"].items())):
            try:
                command("podman", "stop", "--time", "2", name)
                (self.output / f"{role}.container.log").write_text(command("podman", "logs", name))
            except subprocess.CalledProcessError as error:
                print(error.output, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--envoy-policy", type=Path, default=ROOT / "infra/configs/base/gateway/server-timing.yaml",
                        help="Optional candidate policy inside the workspace")
    parser.add_argument("--stage", choices=["all", "capacity", "latency", "report"], default="all")
    parser.add_argument("--scenarios", choices=["nginx", "envoy", "chain"], nargs="+", default=["nginx", "envoy", "chain"])
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--duration", type=int, default=12)
    parser.add_argument("--rate", type=int, default=2000)
    args = parser.parse_args()
    if min(args.rounds, args.duration, args.rate) <= 0:
        parser.error("rounds, duration, and rate must be positive")
    benchmark = Benchmark(args)
    if args.stage == "report":
        benchmark.report()
        return
    try:
        benchmark.prepare()
        for stage in (["capacity", "latency"] if args.stage == "all" else [args.stage]):
            benchmark.measure(stage)
        benchmark.report()
    finally:
        benchmark.stop()


if __name__ == "__main__":
    main()
