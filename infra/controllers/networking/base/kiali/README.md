# Native server tracing

Kiali 2.24.0 exports its own server traces through the existing Collector's
OTLP/gRPC listener on port 4317. This is independent of
`external_services.tracing`, which lets Kiali query Tempo for mesh/application
traces. No new tracing component or image is required.

The native parent-based sampler preserves a parent's sampling decision; new root
traces use the configured one-percent rate. Kiali supplies
`service.name=kiali.kiali-operator` and `service.namespace=kiali-operator`.
The Collector adds Kubernetes workload metadata and the existing cluster/site
defaults. These are sampled Kiali operations, not total traffic or instrumentation
inside every application that Kiali displays. No contextual Trace ID is assumed
in every Kiali log, and this pin does not propagate W3C context to its downstream
Prometheus/Tempo clients.

The Collector removes raw PromQL, selectors and `jsonPatch` attributes from
Kiali's native manual spans: workload changes can contain literal environment
credentials. Its HTTP scope also drops raw I/O-error and panic-event messages.
These rules match Kiali's resource identity and the two native instrumentation
scopes. Operation names, timing, object identity, request IDs, HTTP status and
exception type remain available. The native HTTP middleware records URL paths
without query strings and does not collect request bodies or authentication
headers. This does not sanitize preexisting log bodies or arbitrary producer
attributes.

The native implementation and settings are documented in
[Kiali 2.24's debugging guide](https://v2-24.kiali.io/docs/configuration/debugging-kiali/#tracing)
and its pinned
[tracer implementation](https://github.com/kiali/kiali/blob/52141136c5ebf53bd9f9fee4a356e80e662f42d9/observability/tracing.go).
Kiali login, Kubernetes permissions and external-service credentials remain
independent of this exporter.

Enable this producer only after the
[Collector payload filters](../../../../../observability/controllers/base/otel-collector/README.md#kiali-native-trace-payloads)
are deployed and all Collector Pods have adopted them. The filter preparation
and producer enablement are separate reviewed releases.
