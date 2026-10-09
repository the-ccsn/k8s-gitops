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
Ten package integration checks passed. Its separate guarded fourteen-round
comparison lost 1.31%, with a one-sided 95% upper loss of 5.62%; this is
inconclusive for the 5% gate. Acceptance is not transferred between binaries.
Native builds are exposed for x86_64 Linux and aarch64 Linux. Both packages
built successfully and passed ten integration checks each on their pinned
stock images. ARM64 validation used local QEMU and does not establish ARM64
throughput acceptance. Flake evaluation passed for both systems. Verify the
package against the intended image and architecture before packaging it.

Prepare a separate runtime bundle for review, using both verified packages:

```sh
uv run --with pyyaml python scripts/network/native/nginx/prepare_runtime.py \
  --stage prepare --output ./nginx-timing-runtime \
  --amd64 ./nginx-timing-result/lib/nginx/modules/ngx_http_ccsn_server_timing_module.so \
  --arm64 ./nginx-timing-arm64-result/lib/nginx/modules/ngx_http_ccsn_server_timing_module.so
nix run nixpkgs#kustomize -- build ./nginx-timing-runtime > ./nginx-timing-runtime.yaml
uv run --with pyyaml python scripts/network/native/nginx/prepare_runtime.py \
  --stage verify --output ./nginx-timing-runtime --rendered ./nginx-timing-runtime.yaml
```

Build the second package with
`nix build .#packages.aarch64-linux.nginx-server-timing-module --out-link ./nginx-timing-arm64-result`.
The preparer verifies recorded binary hashes and ELF architectures, preserves
the base manifests, and resumes only with identical inputs. A hash-named
ConfigMap contains both modules. An init container using the same pinned stock
image selects the node architecture and copies its module into an emptyDir;
Nginx loads that module from a read-only mount. No registry publication is
required. Only the header include remains in the timing configuration.

The actual init selection and new mount passed eleven integration checks per
architecture, including reload and 212 fast or changing-delay responses.
Repeated preparation rendered identical manifests; independent verification
rejected a changed binary and a writable module mount. These are functional
checks, and the runtime bundle remains unshipped while throughput acceptance
is unresolved.
