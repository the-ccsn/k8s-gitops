# Grafana application telemetry

Grafana exports its native OTLP/gRPC spans to the existing Collector on port
4317, then to Tempo. W3C Trace Context joins sampled ingress requests to Grafana
operations and supported datasource HTTP clients. This does not enable browser
instrumentation or tracing inside every datasource backend.

The native OTLP provider wraps the 1% root sampler in `ParentBased`: sampled
parents remain sampled, unsampled parents remain unsampled, and new root traces
are sampled at 1%. This differs from Harbor's standalone ratio sampler. Service
name remains `grafana`; both `service.namespace` and `k8s.namespace.name` use the
Pod's downward-API namespace. Collector enrichment adds the existing cluster and
workload metadata. Ambient provides transport mTLS around plaintext gRPC.

Native console JSON logs preserve Grafana's contextual `traceID`. The Collector
promotes it to OTLP log context for the existing Loki-to-Tempo link, preserving
the JSON body and severity. Grafana does not attach a contextual span ID here.
An unsampled request can still have a trace ID in logs without a stored trace.
Existing OAuth log filtering and Collector token-warning suppression remain in
effect. The `/api/health` and native static-asset exceptions are not traced.

Grafana server and datasource-client spans can contain query strings in
`http.url`, including OAuth callback parameters and datasource queries. The
Collector strips those queries from Grafana spans before export. It leaves
other SDKs unchanged. Database query instrumentation remains disabled by its
native default; this change does not enable SQL statements or query logging.

Use **Application Logs** with the Grafana workload namespace, and the native
trace view's existing log and metric links. Ingress lookup finds gateway spans;
opening the complete trace also exposes Grafana application spans. This changes
no login, role mapping, datasource permissions or dashboard definitions. Updating
the Grafana configuration rolls its single Pod using the existing `Recreate`
strategy, causing a brief UI interruption after the reviewed GitOps merge.

These bindings follow Grafana 13.0.1's
[OTLP provider and sampler](https://github.com/grafana/grafana/blob/v13.0.1/pkg/infra/tracing/tracing.go),
[request middleware](https://github.com/grafana/grafana/blob/v13.0.1/pkg/middleware/request_tracing.go)
and [datasource HTTP middleware](https://github.com/grafana/grafana/blob/v13.0.1/pkg/infra/httpclient/httpclientprovider/tracing_middleware.go).
