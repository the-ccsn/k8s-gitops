# Native Envoy Server-Timing plugin

The three C/C++ files use the stock dynamic-module filter loader and pinned public
StreamInfo interfaces. There is no Go runtime and no Envoy rebuild. The ELF
build-ID guard rejects incompatible proxies before accessing C++ interfaces.

The pinned Istio 1.31.1 package passed the 10% throughput gate: HTTP loss
4.88% (95% upper bound 5.07%) and upstream TLS loss 4.37% (upper 4.75%).
Both AMD64 and ARM64 passed 13 two-worker integration checks; ARM64 uses QEMU
for functionality only. Raw samples and package hashes are in the benchmark catalog.

`build.py --external SDK_SOURCES --generated SDK_PROTO_HEADERS --output OUTPUT`
compiles only three translation units. Use Clang 21 with libc++ headers;
`--flags` accepts explicit cross-compiler and linker flags. `--stage verify`
checks the output independently. The SDK must match the pinned Envoy revision
`ae1505b84c97a618838ea3d22b8f5a6f872826f9`; the script never runs a proxy build.

`prepare_runtime.py --chart PINNED_ISTIOD_CHART --output VALUES --loader-output LOADER`
verifies module identities and generates the four stock injection templates.
A node DaemonSet installs an immutable versioned module once. Proxies mount it
read-only; the filter matches their module-version metadata. Existing proxies
join after their next rollout. No registry publication or request scripts are required.
