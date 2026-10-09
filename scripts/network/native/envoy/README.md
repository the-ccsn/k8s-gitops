# Native Envoy Server-Timing candidate

This policy uses the stock HeaderMutation filter and builtin CEL formatter.
Native route formatters provide one helper containing the available upstream
TCP/TLS/header/pool and request-receive intervals. The response mutation runs
late in the encoder chain and measures elapsed time with `%DURATION%`.
Complete TLS intervals are copied directly. Missing intervals are filtered by
a regex fallback; real zero remains present. The private helper is removed and
existing upstream Server-Timing fields remain opaque. The proxy does not
buffer streaming bodies or inspect another proxy's metrics.

The root and waypoint attachments share the same patches. Eleven two-worker
checks and nine strict fixture preflights passed on the pinned stock Istio
proxy, covering TLS/plaintext, local responses, 2,000 fast replies, changed
durations, later response-filter waiting, and streaming. No proxy compilation
or separately compiled plugin is required. This directory is not referenced
by the production kustomization. Throughput acceptance is pending.

The policy removes the second helper used by the earlier CEL experiment,
avoiding duplicated native interval and hostname formatting. Run the guarded
comparison after local compilation stops:

```sh
nix shell nixpkgs#wrk nixpkgs#vegeta -c uv run --with pyyaml python \
  scripts/network/benchmark_server_timing.py --stage capacity \
  --output ../task-logs/server-timing-native-cel-capacity \
  --envoy-policy scripts/network/native/envoy/policy.yaml \
  --reference-envoy-policy infra/configs/base/gateway/server-timing.yaml \
  --scenarios envoy --modes off reference on --connections 16 64 256 \
  --rounds 7 --duration 6 --require-idle-builds \
  --nginx-throughput-budget 5 --envoy-throughput-budget 10
```

Use a fresh output directory for changed inputs. Complete curves, frozen
identities, and historical experiments are recorded in
`../../benchmarks/server-timing-native-probes-2026-10-09.json`.
