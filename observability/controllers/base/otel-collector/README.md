# OpenTelemetry Collector dashboard

`dashboard.json` is rendered from Grafana's
[OpenTelemetry Collector mixin](https://github.com/grafana/jsonnet-libs/tree/620b8b415f64286bf6ff8fe28590c81549155044/opentelemetry-collector-mixin),
pinned to commit `620b8b415f64286bf6ff8fe28590c81549155044`.
Rendering uses Jsonnet 0.21.0 and Grafonnet commit
`8de2f3c83a38f68085c239df979f57d8dfdb7588` (the Grafana 13 schema).
The unmodified rendered JSON has SHA-256
`d523de5bbb54c7914a2f97af2c84528ac45a3a970b20a35ef9a31263633962aa`.
`LICENSE.dashboard` includes the upstream copyright notice and Apache 2.0 license.

To reproduce the source, place the two pinned repositories on Jsonnet's library
path, with `common-lib` resolving to `jsonnet-libs/common-lib`, then evaluate
`(import 'opentelemetry-collector-mixin/mixin.libsonnet').grafanaDashboards['collector.json']`.
Only the rendered JSON is required at runtime.

The upstream layout and visualizations are preserved. Local bindings retain UID
`otel-collector`, use `victoriametrics`, and separately select Kubernetes cluster,
Collector namespace, job and Pod. Pod names replace endpoint addresses in the
instance selector and legends. Every selector has the chosen cluster/namespace.

Queries use Collector 0.152.0's exact current metric names. The source's optional
`_total`, `_bytes` and `_seconds_total` suffix matching is removed. CPU rate uses a
per-core percentage unit, heap allocation uses
`otelcol_process_runtime_heap_alloc_bytes`, and the persistent sending queue uses
bytes, matching our configured queue sizer. An unset source refresh interval is
bound to 30 seconds. The source's gRPC duration histograms are in milliseconds;
their panel unit is milliseconds, while HTTP duration panels retain seconds.

Metrics-pipeline, batch-processor and detailed HTTP/gRPC telemetry panels remain
part of the upstream design. They can have no series in our logs/traces-only
configuration without batching or detailed internal telemetry. Failure counters
can also be absent until their first event. Do not enable pipelines or synthesize
series merely to populate these panels.

This changes no Collector configuration, queue capacity, persistence or alert
rules. For updates, verify both source commits and the rendered hash, reapply the
bindings, and validate selectors, metric names, memory/queue units and queries.
