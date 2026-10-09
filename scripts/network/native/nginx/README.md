# Native Nginx Server-Timing module

This dynamic module reads the current request's upstream states and appends its
own metrics to an existing opaque `Server-Timing` field. It reports elapsed
header time and available upstream connect/header intervals, preserving zero.
Cached descriptions and templates avoid repeated formatting. Longer durations,
retries, and missing intervals use a separate general formatter. Single-attempt
responses retain the hostname; retries include their attempt numbers. Reloads
retain no pointers into a previous configuration.

The hardened x86_64 Nix package for the pinned stock Nginx 1.29.8 image passed
eleven integration checks and a guarded fourteen-round peak-throughput sweep
with 12-second samples at concurrency 16, 64, and 256. Peak loss was 0.74%; the
one-sided 95% upper loss was 1.99%, passing the independent 5% gate. Baseline
peak range was 3.80%. The accepted binary is 15,248 bytes with SHA-256
`3238f9d78c26426215a4c5266b9223a7c6c9961658ada858d13aefe03b57c522`.
Complete curves and frozen input identities are recorded in
`../../benchmarks/server-timing-native-probes-2026-10-09.json`.

Both architecture packages passed eleven functional checks each. The actual
startup selection and read-only runtime path also passed eleven checks per
architecture, including reload and 212 fast or changing-delay responses each.
Repeated rendering is identical; verification rejects changed binaries and
writable module mounts. ARM64 validation used QEMU and does not establish
native ARM64 throughput acceptance. Acceptance is not transferred to different
binaries. Production manifests still use maps and njs; the verified runtime
bundle remains unshipped.

Build only the module with the pinned source and flake inputs:

```sh
nix build .#nginx-server-timing-module --out-link ./nginx-timing-result
nix build .#packages.aarch64-linux.nginx-server-timing-module \
  --out-link ./nginx-timing-arm64-result
```

The output is `lib/nginx/modules/ngx_http_ccsn_server_timing_module.so`.
The addon builds the dynamic-module target with O3 and compatibility enabled,
retains compiler hardening, and rejects runtime library dependencies.
`ccsn_server_timing on;` enables timing in HTTP, server, or location scope.

Prepare a separate runtime bundle using both verified packages:

```sh
uv run --with pyyaml python scripts/network/native/nginx/prepare_runtime.py \
  --stage prepare --output ./nginx-timing-runtime \
  --amd64 ./nginx-timing-result/lib/nginx/modules/ngx_http_ccsn_server_timing_module.so \
  --arm64 ./nginx-timing-arm64-result/lib/nginx/modules/ngx_http_ccsn_server_timing_module.so
nix run nixpkgs#kustomize -- build ./nginx-timing-runtime > ./nginx-timing-runtime.yaml
uv run --with pyyaml python scripts/network/native/nginx/prepare_runtime.py \
  --stage verify --output ./nginx-timing-runtime --rendered ./nginx-timing-runtime.yaml
```

The preparer checks the accepted source, package hashes and ELF architectures,
preserves base files, and resumes only with identical inputs. A hash-named
ConfigMap holds both modules. An init container using the pinned stock image
selects the architecture and copies its module into an emptyDir; Nginx loads it
from a read-only mount. No registry publication is required. Verification
checks rendered binary hashes, rollout references, image, selection command,
mounts and timing configuration before the bundle is used.
