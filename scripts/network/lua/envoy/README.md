# Envoy LuaJIT Server-Timing candidate

This candidate uses the builtin Lua filter in the pinned stock Istio proxy.
It requires no Envoy rebuild or separately compiled plugin. Native route and
local-reply formatters supply this proxy's request start and upstream intervals.
One response callback reads the current clock through LuaJIT FFI, measures
elapsed time after later response filters, and appends its own field. Existing
upstream fields remain opaque. Unavailable durations are omitted and zero is
retained. The private helper is removed before response headers are sent.

Each worker caches only hostname descriptions and two formatting templates.
The FFI scratch buffers are worker-local; the callback never yields and copies
the completed output to a Lua string before returning. Measurements themselves
are read afresh on every response. Slow or partial responses use general
formatting. Streaming bodies are not buffered.

`filter.lua` is the readable source embedded in `policy.yaml`; the root and
waypoint policies share the same patches. This directory is not referenced by
the production kustomization. Eleven two-worker checks and nine strict
benchmark fixture preflights passed on
`registry.istio.io/release/proxyv2:1.30.0-rc.0-distroless`, covering TLS/plaintext,
local responses, repeated opaque upstream fields, changing durations, streaming,
and later response-filter waiting. The complete seven-round guarded comparison lost 17.37% throughput, with a
17.80% one-sided 95% upper loss, failing the independent 10% gate. This remains
an unshipped experiment.
The independent Envoy gate is a loss of at most 10%, including its one-sided
95% confidence bound. Diagnostic profiling is not an acceptance result.

Run the guarded comparison from the repository root after local builds stop:

```sh
nix shell nixpkgs#wrk nixpkgs#vegeta -c uv run --with pyyaml python \
  scripts/network/benchmark_server_timing.py --stage capacity \
  --output ../task-logs/server-timing-luajit-capacity \
  --envoy-policy scripts/network/lua/envoy/policy.yaml \
  --reference-envoy-policy infra/configs/base/gateway/server-timing.yaml \
  --scenarios envoy --modes off reference on --connections 16 64 256 \
  --rounds 7 --duration 6 --require-idle-builds \
  --nginx-throughput-budget 5 --envoy-throughput-budget 10
```

Use a fresh output directory for new inputs. The benchmark verifies complete
per-hop metrics before load, freezes input identities, and discards the whole
invocation if compilation resumes. Recorded evidence is in
`../../benchmarks/server-timing-native-probes-2026-10-09.json`.
