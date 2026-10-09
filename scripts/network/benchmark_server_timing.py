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
from collections import Counter
from contextlib import closing
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
NGINX_DIR = ROOT / "infra/configs/base/i319-reroute"
ENVOY_IMAGE = "registry.istio.io/release/proxyv2:1.30.0-rc.0-distroless"


def validate_timing(scenario: str, mode: str, headers: list[tuple[str, str]]) -> None:
    """Reject candidates that gain capacity by omitting or corrupting metrics."""
    if any(key.lower() == "x-ccsn-envoy-timing" for key, _ in headers):
        raise ValueError("Private timing helper leaked into a benchmark response")
    timing = ",".join(value for key, value in headers if key.lower() == "server-timing")
    # This fixture's descriptions are DNS hostnames; its backend emits app;dur=1.
    names = []
    for metric in timing.split(","):
        match = re.fullmatch(r'\s*([a-z_]+);dur=([0-9]+(?:\.[0-9]+)?)(?:;desc="[^"]*")?\s*', metric)
        if match is None:
            raise ValueError(f"Invalid benchmark timing metric: {metric!r}")
        names.append(match[1])
    expected = Counter({"app": 1})
    if mode != "off":
        if scenario in {"nginx", "chain"}:
            expected.update(["nginx_headers", "nginx_upstream_connect", "nginx_upstream_headers"])
        if scenario in {"envoy", "chain"}:
            hops = 2 if scenario == "chain" else 1
            expected.update({name: hops for name in ["envoy_headers", "envoy_upstream_tcp",
                            "envoy_upstream_headers", "envoy_upstream_pool", "envoy_request_receive"]})
            expected["envoy_upstream_tls"] = 1
    if Counter(names) != expected:
        raise ValueError(f"Benchmark timing metrics differ: expected {dict(expected)}, got {dict(Counter(names))}")


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
        self.timing_dir = args.nginx_timing_dir.resolve()
        if not self.timing_dir.is_relative_to(ROOT.parent):
            raise ValueError("Candidate Nginx sources must remain inside the workspace")
        self.state.setdefault("role_cpus", {})
        self.reference_dir = (args.reference_nginx_timing_dir or self.timing_dir).resolve()
        reference_policy = (args.reference_envoy_policy or args.envoy_policy).resolve()
        if not self.reference_dir.is_relative_to(ROOT.parent) or not reference_policy.is_relative_to(ROOT.parent):
            raise ValueError("Reference sources must remain inside the workspace")
        selected_cpus = args.cpus or physical_cpus()
        if not set(selected_cpus).issubset(os.sched_getaffinity(0)):
            raise ValueError("Selected CPUs must be available to this process")
        cores = [tuple((Path(f"/sys/devices/system/cpu/cpu{cpu}/topology") / name).read_text().strip()
                       for name in ["physical_package_id", "core_id"]) for cpu in selected_cpus]
        if len(set(cores)) != 6:
            raise ValueError("Select six distinct physical cores")
        config = {"rounds": args.rounds, "duration": args.duration, "rate": args.rate, "cpus": selected_cpus,
                  "scenarios": args.scenarios, "connections": args.connections, "modes": args.modes}
        if "config" in self.state and self.state["config"] != config:
            raise ValueError("Existing run parameters differ; select another output directory")
        self.state["config"] = config
        policy = args.envoy_policy.resolve()
        if not policy.is_relative_to(ROOT.parent):
            raise ValueError("Candidate policy must remain inside the workspace")
        sources = [policy, *sorted(p for p in self.timing_dir.iterdir()
                   if p.name.startswith("server-timing") or p.name == "module-load.conf")]
        if "reference" in args.modes:
            sources += [reference_policy, *sorted(p for p in self.reference_dir.iterdir()
                        if p.name.startswith("server-timing") or p.name == "module-load.conf")]
        source_hash = hashlib.sha256(b"".join(str(p.relative_to(ROOT.parent)).encode() + b"\0" + p.read_bytes() for p in sources)).hexdigest()
        if self.state.get("source_sha256", source_hash) != source_hash:
            raise ValueError("Timing implementation changed; select another output directory")
        self.state["source_sha256"] = source_hash
        self.cpus = config["cpus"]
        self.client_cpus = ",".join(map(str, self.cpus[4:6]))
        self.nginx_image = yaml.safe_load((NGINX_DIR / "deployment.yaml").read_text())["spec"]["template"]["spec"]["containers"][0]["image"]
        self.patches = yaml.safe_load(policy.read_text())["items"][0]["spec"]["configPatches"]
        self.reference_patches = yaml.safe_load(reference_policy.read_text())["items"][0]["spec"]["configPatches"]
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
        command("podman", "run", "--detach", "--name", name, "--hostname", f"benchmark-{role.replace('_reference', '_on')}",
                "--user", "0", "--network", "host",
                "--entrypoint", entrypoint, "--volume", f"{self.output}:/bench:ro",
                "--volume", f"{self.timing_dir}:/module:ro", "--volume", f"{self.reference_dir}:/reference:ro", image, *args)
        self.state["containers"][role] = name
        self.persist()
        return role

    def nginx(self, role: str, listen: int, upstream: int, mode: str, cpu: int) -> str:
        enabled = mode in {"on", "reference"}
        directory, mount = (self.reference_dir, "/reference") if mode == "reference" else (self.timing_dir, "/module")
        module = f"include {mount}/module-load.conf;" if (directory / "module-load.conf").exists() else "load_module /usr/lib/nginx/modules/ngx_http_js_module.so;"
        imports = f"include {mount}/server-timing-http.conf;" if (directory / "server-timing-http.conf").exists() else f"js_import server_timing from {mount}/server-timing.js; include {mount}/server-timing-maps.conf;"
        if mode == "static":
            hop = f"benchmark-{role.replace('_static', '_on')}"
            metrics = f'nginx_headers;dur=0000;desc="{hop}", nginx_upstream_connect;dur=0000;desc="{hop} attempt 1", nginx_upstream_headers;dur=0000;desc="{hop} attempt 1"'
            headers = f"add_header Server-Timing '{metrics}' always;"
        else:
            headers = f"include {mount}/server-timing-headers.conf;" if enabled else ""
        text = f"""
{module if enabled else ''}
pcre_jit on;
user root;
worker_processes 1;
events {{ worker_connections 8192; }}
http {{
    access_log off;
    error_log /dev/stderr warn;
    keepalive_requests 1000000;
    {imports if enabled else ''}
    upstream backend {{ server 127.0.0.1:{upstream}; keepalive 128; }}
    server {{
        listen 127.0.0.1:{listen};
        location / {{
            {headers}
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

    def envoy(self, role: str, listen: int, upstream: int, mode: str, cpu: int, tls: bool = False) -> str:
        route = {"name": "benchmark", "virtual_hosts": [{"name": "backend", "domains": ["*"], "routes": [{
            "match": {"prefix": "/"}, "route": {"cluster": "backend"},
        }]}]}
        filters = []
        patches = self.reference_patches if mode == "reference" else self.patches
        if mode in {"on", "reference"}:
            for patch in patches:
                if patch["applyTo"] == "ROUTE_CONFIGURATION":
                    route.update(copy.deepcopy(patch["patch"]["value"]))
                elif patch["applyTo"] == "HTTP_FILTER":
                    filters.append(copy.deepcopy(patch["patch"]["value"]))
        elif mode == "static":
            hop = f"benchmark-{role.replace('_static', '_on')}"
            names = ["upstream_tcp", *(["upstream_tls"] if tls else []), "upstream_headers", "upstream_pool", "request_receive"]
            values = [f'envoy_headers;dur=0;desc="{hop}"', ",".join(f'envoy_{name};dur=0;desc="{hop}"' for name in names)]
            route["response_headers_to_add"] = [{"header": {"key": "server-timing", "value": value},
                                                 "append_action": "APPEND_IF_EXISTS_OR_ADD"} for value in values]
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
        if mode in {"on", "reference"}:
            hcm = bootstrap["static_resources"]["listeners"][0]["filter_chains"][0]["filters"][0]["typed_config"]
            for patch in patches:
                if patch["applyTo"] == "NETWORK_FILTER":
                    hcm.update(copy.deepcopy(patch["patch"]["value"]["typed_config"]))
        (self.output / f"{role}.yaml").write_text(yaml.safe_dump(bootstrap))
        return self.container(role, cpu, ENVOY_IMAGE, "/usr/local/bin/envoy", ["-c", f"/bench/{role}.yaml",
                              "--disable-hot-restart", "--concurrency", "1", "-l", "error"])

    def prepare(self) -> None:
        self.state.setdefault("run_id", str(time.time_ns()))
        keys = ["backend", "backend_tls", *(f"{role}_{mode}" for mode in self.args.modes for role in ["nginx", "envoy", "outer", "chain"])]
        ports = self.state.setdefault("ports", {key: port() for key in keys})
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
        for mode in self.args.modes:
            inner = self.envoy(f"envoy_{mode}", ports[f"envoy_{mode}"], ports["backend_tls"], mode, self.cpus[2], tls=True)
            outer = self.envoy(f"outer_{mode}", ports[f"outer_{mode}"], ports[f"envoy_{mode}"], mode, self.cpus[1])
            nginx = self.nginx(f"nginx_{mode}", ports[f"nginx_{mode}"], ports["backend"], mode, self.cpus[0])
            chain = self.nginx(f"chain_{mode}", ports[f"chain_{mode}"], ports[f"outer_{mode}"], mode, self.cpus[0])
            for scenario, roles, endpoint in [("nginx", [nginx], f"nginx_{mode}"), ("envoy", [inner], f"envoy_{mode}"),
                                               ("chain", [chain, outer, inner], f"chain_{mode}")]:
                self.state["endpoints"][f"{scenario}_{mode}"] = {"url": f"http://127.0.0.1:{ports[endpoint]}/", "roles": roles}
        self.persist()
        for key, endpoint in self.state["endpoints"].items():
            endpoint_port = int(endpoint["url"].split(":")[2].split("/")[0])
            deadline = time.monotonic() + 15
            while True:
                try:
                    with closing(http.client.HTTPConnection("127.0.0.1", endpoint_port, timeout=1)) as conn:
                        conn.request("GET", "/")
                        response = conn.getresponse()
                        assert response.status == 200 and len(response.read()) == 256
                        scenario, mode = key.rsplit("_", 1)
                        validate_timing(scenario, mode, response.getheaders())
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
            frequency = Path(f"/sys/devices/system/cpu/cpu{self.state['role_cpus'][role]}/cpufreq/scaling_cur_freq")
            if frequency.exists():
                result[role]["frequency_khz"] = int(frequency.read_text())
        return result

    def sample(self, scenario: str, mode: str, stage: str, round_number: int, connections: int = 64) -> None:
        key = f"{stage}_{scenario}_{mode}_{round_number}_c{connections}"
        if any(item["key"] == key for item in self.state["samples"]):
            return
        endpoint = self.state["endpoints"][f"{scenario}_{mode}"]
        prefix = self.output / key
        command("taskset", "-c", self.client_cpus, "wrk", "-t2", f"-c{connections}", "-d2s", endpoint["url"])
        roles = endpoint["roles"] + ["backend"]
        if stage == "capacity":
            args = ["taskset", "-c", self.client_cpus, "wrk", "-t2", f"-c{connections}", f"-d{self.args.duration}s", "--latency", endpoint["url"]]
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
            frequencies = [item[role]["frequency_khz"] for item in memory_samples if "frequency_khz" in item[role]]
            if frequencies:
                per_role[role]["frequency_khz_median"] = statistics.median(frequencies)
                per_role[role]["frequency_khz_range"] = [min(frequencies), max(frequencies)]
        result.update({"key": key, "scenario": scenario, "mode": mode, "stage": stage, "round": round_number,
                       "connections": connections, "elapsed_s": elapsed, "load_after": Path("/proc/loadavg").read_text().strip(), "roles": per_role,
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
                for connections in (self.args.connections if stage == "capacity" else [64]):
                    modes = self.args.modes if round_number % 2 == 0 else list(reversed(self.args.modes))
                    for mode in modes:
                        self.sample(scenario, mode, stage, round_number, connections)

    def report(self) -> None:
        summary = {"environment": self.state["environment"], "config": self.state["config"], "source_sha256": self.state.get("source_sha256"), "results": {}}
        for scenario in self.state["config"].get("scenarios", ["nginx", "envoy", "chain"]):
            entry = {}
            for stage in ["capacity", "latency"]:
                for mode in self.state["config"].get("modes", ["off", "on"]):
                    samples = [s for s in self.state["samples"] if (s["scenario"], s["stage"], s["mode"]) == (scenario, stage, mode)]
                    if not samples:
                        continue
                    curves = {}
                    if stage == "capacity":
                        for connections in sorted({s.get("connections", 64) for s in samples}):
                            group = [s for s in samples if s.get("connections", 64) == connections]
                            curves[str(connections)] = {"rps": statistics.median(s["rps"] for s in group),
                                                        "rps_range": [min(s["rps"] for s in group), max(s["rps"] for s in group)],
                                                        "samples": len(group)}
                        peak = max(curves, key=lambda c: curves[c]["rps"])
                        samples = [s for s in samples if s.get("connections", 64) == int(peak)]
                    metrics = ["rps", "proxy_cpu_us_per_request", "proxy_anon_mib", "client_cpu_cores"]
                    if stage == "latency":
                        metrics += ["p50_ms", "p95_ms", "p99_ms"]
                    entry[f"{stage}_{mode}"] = {name: statistics.median(s[name] for s in samples) for name in metrics}
                    entry[f"{stage}_{mode}"]["rps_range"] = [min(s["rps"] for s in samples), max(s["rps"] for s in samples)]
                    entry[f"{stage}_{mode}"]["samples"] = len(samples)
                    if curves:
                        entry[f"{stage}_{mode}"]["connections"] = int(peak)
                        entry[f"{stage}_{mode}"]["curve"] = curves
            for stage in ["capacity", "latency"]:
                if f"{stage}_on" in entry and f"{stage}_off" in entry:
                    entry[f"{stage}_change_percent"] = {key: (entry[f"{stage}_on"][key] / value - 1) * 100
                                                         for key, value in entry[f"{stage}_off"].items()
                                                         if isinstance(value, (int, float)) and value != 0 and key not in {"samples", "connections"}}
            if "capacity_static" in entry and "capacity_off" in entry:
                entry["static_throughput_change_percent"] = (entry["capacity_static"]["rps"] / entry["capacity_off"]["rps"] - 1) * 100
            if "capacity_reference" in entry and "capacity_on" in entry:
                entry["throughput_change_from_reference_percent"] = (entry["capacity_on"]["rps"] / entry["capacity_reference"]["rps"] - 1) * 100
            if "capacity_change_percent" in entry:
                throughput_drop = -entry["capacity_change_percent"]["rps"]
                baseline = entry["capacity_off"]
                spread = (baseline["rps_range"][1] - baseline["rps_range"][0]) / baseline["rps"] * 100
                entry["acceptance"] = {
                    "threshold_percent": 1,
                    "metric": "peak_throughput",
                    "throughput_point_estimate_pass": throughput_drop <= 1,
                    "baseline_throughput_spread_percent": spread,
                    # A point estimate on a noisy workstation cannot establish a 1% limit.
                    "status": "failed" if throughput_drop > 1 else "inconclusive",
                }
            if "on" in self.state["config"].get("modes", ["off", "on"]) and "off" in self.state["config"].get("modes", ["off", "on"]):
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
    parser.add_argument("--nginx-timing-dir", type=Path, default=NGINX_DIR)
    parser.add_argument("--reference-envoy-policy", type=Path, help="Previous implementation for reference mode")
    parser.add_argument("--reference-nginx-timing-dir", type=Path, help="Previous Nginx implementation for reference mode")
    parser.add_argument("--stage", choices=["all", "capacity", "latency", "report"], default="all")
    parser.add_argument("--scenarios", choices=["nginx", "envoy", "chain"], nargs="+", default=["nginx", "envoy", "chain"])
    parser.add_argument("--connections", type=int, nargs="+", default=[16, 64, 256, 1024], help="Capacity connection-count sweep")
    parser.add_argument("--cpus", type=int, nargs=6, help="Distinct physical cores: Nginx, outer Envoy, inner Envoy, backend, two clients")
    parser.add_argument("--modes", choices=["off", "on", "static", "reference"], nargs="+", default=["off", "on"], help="Static uses constant metrics; reference runs the previous implementation")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--duration", type=int, default=12)
    parser.add_argument("--rate", type=int, default=2000)
    args = parser.parse_args()
    if min(args.rounds, args.duration, args.rate, *args.connections) <= 0 or min(args.connections) < 2:
        parser.error("rounds, duration, and rate must be positive; connections must be at least two")
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
