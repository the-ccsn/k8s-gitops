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
No module binary is included or deployed. The `config` addon entrypoint was
independently rebuilt against the pinned Nginx 1.29.8 source and passed all ten
integration checks. Its executable section matches the accepted candidate.

Build the module alone using the pinned source and flake inputs:

```sh
nix build .#nginx-server-timing-module --out-link ./nginx-timing-result
```

The output is `nginx-timing-result/lib/nginx/modules/ngx_http_ccsn_server_timing_module.so`.
The package builds only the dynamic module target with O3 and compatibility
enabled; it rejects a runtime library dependency. It retains Nix compiler
hardening, so its executable section differs from the accepted candidate.
Ten package integration checks passed; a separate guarded fourteen-round
throughput comparison is pending. Acceptance is not transferred between binaries.
Native builds are exposed for x86_64 Linux and aarch64 Linux. Both packages
built successfully and passed ten integration checks each on their pinned
stock images. ARM64 validation used local QEMU and does not establish ARM64
throughput acceptance. Flake evaluation passed for both systems. Verify the
package against the intended image and architecture before packaging it.
