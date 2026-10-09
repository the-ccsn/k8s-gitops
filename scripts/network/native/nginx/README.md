# Native Nginx Server-Timing candidate

This dynamic module reads this request's upstream states and appends its own
metrics to an existing opaque `Server-Timing` field. Configuration-owned cached
templates avoid repeated description formatting. Longer durations, retries,
and partial intervals use the general path. Configuration reloads retain no
pointers into a previous configuration. `ccsn_server_timing on;` enables the
module in an HTTP, server, or location configuration.

The source corresponds to the locally tested O3 candidate for the pinned
Nginx 1.29.8 image. Ten integration checks passed, including configuration
reload, opaque upstream fields, retries, local replies, streaming, and all
production locations. The guarded 14-round peak-throughput comparison lost
4.03%; its one-sided 95% upper loss was 4.46%, passing the independent 5% gate.
The disabled peak range was 3.33%. Raw-source and harness identities and
complete curves are recorded in `../../benchmarks/server-timing-native-probes-2026-10-09.json`.

This remains a candidate: the production manifests still use maps and njs.
No module binary is included or deployed. Build the dynamic module against the
pinned image's Nginx version and compatible configure flags; the Nginx addon
entrypoint is `config`. Use `--add-dynamic-module=<this directory>` and the
`make -f objs/Makefile modules` target to build the module alone. Verify the
result against the intended image and architecture before packaging it.
