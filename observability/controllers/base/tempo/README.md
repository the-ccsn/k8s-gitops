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

## Kubernetes namespace trace search

In Grafana Explore, select the Tempo datasource and **Search**. Its default
fields include resource attributes `k8s.namespace.name` (the traced workload's
namespace) and `k8s.cluster.name`, alongside the native Service Name and Span
Name fields. The native Status and Duration fields remain available. Select
namespace and cluster values to scope trace discovery; for example, in TraceQL:

```traceql
{ resource.k8s.cluster.name = "kubevirt-cluster-319" && resource.k8s.namespace.name = "harbor" && resource.service.name = "harbor-core" }
```

These fields start empty and are optional. An empty field adds no predicate;
spans without an attribute cannot match a selected value for it. The namespace
is not Tempo's own namespace or the logical `service.namespace` attribute.
TraceQL selects matching spans and their traces; opening a trace can show spans
from other namespaces. These defaults do not enforce a namespace filter or
provide user-access isolation, and do not separate same-name services in the
aggregate service graph.

The configuration follows Grafana 13.0.1's native
[`search.filters` defaults](https://github.com/grafana/grafana/blob/v13.0.1/public/app/plugins/datasource/tempo/datasource.ts#L129-L150)
and [filter contract](https://github.com/grafana/grafana/blob/v13.0.1/public/app/plugins/datasource/tempo/dataquery.gen.ts#L127-L156).
Configured filters replace the default list, so the native service/span IDs and
scopes are retained. This source-based configuration does not establish browser
acceptance or live trace-attribute coverage.

## Logical namespaces in service graphs

Use **Service graph (logical namespaces)** in **Observability Platform**, or
follow the link from **Application Logs**. The stock Grafana node graph uses
the selected Kubernetes cluster and time range. Log namespace, service and ID
filters do not truncate a graph that crosses services or namespaces.

Tempo emits `client_service_namespace` and `server_service_namespace` using
`service_graphs.dimensions: [service.namespace]` and
`enable_client_server_prefix: true`. The native query explicitly sets
`serviceMapIncludeNamespace: true`; Grafana uses logical `namespace/service`
node identities and carries that identity into metric and trace navigation.
Those built-in node links do not retain the graph's cluster matcher; inspect
their query when working across clusters. The service names and metric names
retain their native values.

Istio proxy spans receive a default logical namespace from their enriched
workload namespace when the producer omitted it. Explicit SDK namespaces stay
unchanged. Logical `service.namespace` and workload `k8s.namespace.name` remain
different concepts; callers, external peers and unenriched producers can have
an empty logical namespace. Those nodes remain unqualified. This provides no
user-access isolation or universal Kubernetes-namespace separation.

Use the authored panel: generic service-map queries without the namespace flag
still aggregate bare names. Grafana 13.0.1 has no datasource-wide namespace
switch. Older stored graph metrics keep their old labels until retention; this
change writes new series without historical aliases or backfill. Allow fresh
samples after rollout and narrow the time range when inspecting the transition.
Adding the proxy namespace also lets Tempo's native span-metrics `job` acquire
its namespace prefix; service-name and workload-namespace selectors remain valid.

The contract follows Tempo 2.9.0's
[service-graph dimensions](https://github.com/grafana/tempo/blob/607c7fb69662262bbb4462da1e2d91067dab6785/modules/generator/processor/servicegraphs/config.go)
and Grafana 13.0.1's
[native namespace-aware query](https://github.com/grafana/grafana/blob/v13.0.1/public/app/plugins/datasource/tempo/datasource.ts#L1287-L1328).

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
