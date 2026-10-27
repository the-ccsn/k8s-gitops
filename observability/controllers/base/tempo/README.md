# Tempo operational dashboard

`dashboard.json` uses Grafana's official Tempo **2.9.0** operational dashboard,
matching the deployed binary. Source:
[`operations/tempo-mixin-compiled/dashboards/tempo-operational.json`](https://github.com/grafana/tempo/blob/607c7fb69662262bbb4462da1e2d91067dab6785/operations/tempo-mixin-compiled/dashboards/tempo-operational.json),
commit `607c7fb69662262bbb4462da1e2d91067dab6785`.
Unmodified upstream SHA-256:
`3fa24bcd0f6183776d4eb3c06e38a61aeeff4d646817c32eae0b4deebf2a8e87`.
`LICENSE.dashboard` preserves its AGPL 3.0 license.

UID `tempo`, the tracing folder and `victoriametrics` are retained. Backend metrics
use `k8s_cluster_name`, namespace, native job and Pod from `tempo_build_info`.
The namespace identifies the Tempo workload, not the
namespaces of traced applications. Separate distributor, ingester, querier,
frontend, compactor and generator job selectors bind to the single Tempo process.
Their native metric names and route filters remain distinct.

Applicable upstream types and panel positions are retained, covering process
resources, maintenance, reads, writes, metrics generation, backend and compaction.
The unused Cortex gateway, Memcached, Vulture and distributed ring/memberlist
sections are omitted. Histograms use the current classic `_bucket` metrics;
the native-histogram alternatives and format switch are removed. No compatibility
series or recording rules are added. Unconfigured log-diff annotations are removed.

Resource panels use cAdvisor's actual collector job and selected Pod. CPU/memory
exclude empty aggregate and pause containers; network uses the Pod counters.
Restart counts use kube-state-metrics. The PVC selector follows that Pod's native
volume metadata, and free space reads the selected claim's kubelet statistics.
All resource queries retain cluster/namespace scope. Promtail custom bad-word
metrics are omitted because the cluster collects logs with OpenTelemetry.

Existing discarded spans and live traces remain as final panels. The old generic
p95 panel is accurately labelled Server Request Latency: its histogram includes
all server requests, while upstream's read panels select their specific routes.
Internal RPCs invoked in-process, lazy error counters and features without recent
requests may leave charts empty. This import changes no sampling, Collector,
metrics generator, storage, authentication or trace-query policy.
When updating, verify the source hash, preserve the UID, reapply topology/scopes,
and check exact metric names, histogram format and every query.

## Trace-to-metric navigation

The Tempo datasource supplies native span links to VictoriaMetrics: sampled span
rate by kind/status and p50/p95 latency in seconds. Each link uses the span's
available Kubernetes cluster, workload namespace and service attributes, with a
five-minute margin before and after the span. Workload namespaces, native jobs
and client/server kinds remain separate in query results rather than adding
both observations of a request together. Grafana omits mappings missing from a
span, so unenriched external SDK spans can open a broader selection; the
namespace grouping still keeps their metric series distinct. These links do
not implement user-access isolation.

The generator explicitly adds `k8s.namespace.name` as the metric label
`k8s_namespace_name`; the native `service`, `span_kind` and `status_code` labels
remain unchanged. The namespace is the traced workload's namespace, not Tempo's
namespace. Only new samples carry this dimension; no historical fallback or
metric alias is installed. Rates need fresh samples after rollout.

These metrics describe collected, sampled spans. They do not estimate total
traffic, and span status is not an HTTP error-rate calculation. Use Istio's
traffic metrics for request totals. Application SDK instrumentation and header
propagation still determine application-level trace coverage.

The link configuration follows Grafana's pinned
[native trace-to-metrics settings](https://github.com/grafana/grafana/blob/v13.0.1/docs/sources/datasources/tempo/configure-tempo-data-source/configure-trace-to-metrics.md)
and Tempo's pinned
[span-metrics processor](https://github.com/grafana/tempo/blob/v2.9.0/modules/generator/processor/spanmetrics/config.go).
