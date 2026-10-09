# Native Nginx Server-Timing module

This dynamic module reads the current request's upstream states and appends a
separate `Server-Timing` field without inspecting or changing upstream fields. It reports elapsed
header time and available upstream connect/header intervals, preserving zero.
Cached descriptions and templates avoid repeated formatting. Longer durations,
retries, and missing intervals use a separate general formatter. Single-attempt
responses retain the hostname; retries include their attempt numbers. Reloads
retain no pointers into a previous configuration.

Both architecture packages passed thirteen production integration checks,
including physical-field preservation. This revision passed the 5% throughput
gate: peak loss 4.38%, one-sided 95% upper bound 4.81%. ARM64 uses QEMU
for functionality only.

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
