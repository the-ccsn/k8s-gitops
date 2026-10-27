# Dashboard catalogue and investigation

The active overlays declare 41 GrafanaDashboard resources: 38 use pinned
upstream dashboards or official component definitions, and three combine this
installation's signals. Component owners keep source commits, hashes, licenses
and local metric bindings beside their dashboards. Helm- or Operator-generated
dashboards are managed by their own charts and are outside this count.

| Area | Views | Owner and source notes |
| --- | --- | --- |
| Kubernetes | Cluster, namespace, node, Pod, control plane, Deployment | [ONZACK, dotdc and Kubernetes mixin](configs/base/victoria-metrics/README.md) |
| Kubernetes overview / Grafana | Kubernetes overview, Grafana | [Grafana monitoring mixins](configs/base/grafana/) |
| KubeVirt | KubeVirt components and VMIs | [Official KubeVirt monitoring](../infra/configs/base/kubevirt/monitoring/README.md) |
| Istio | Mesh, service, workload, control plane, ztunnel, Gateway API | [Official Istio dashboards](../infra/configs/base/istio/monitoring/README.md) |
| Kiali | Server internal metrics | [Official Kiali definition rendered for Grafana](../infra/controllers/networking/base/kiali/monitoring/README.md) |
| PostgreSQL | CloudNativePG | [Official CNPG monitoring](../infra/controllers/general/base/cloudnative-pg/monitoring/README.md) |
| Storage | Longhorn, persistent volumes | [Longhorn and Kubernetes storage sources](../infra/controllers/foundation/base/longhorn/monitoring/README.md) |
| Certificates | cert-manager | [cert-manager mixin](../infra/configs/base/cert-manager/monitoring/README.md) |
| GitOps | Flux, Flux control plane | [Official Flux dashboards](../infra/configs/base/flux/monitoring/README.md) |
| Registry | Harbor | [Official Harbor dashboard](../infra/configs/base/harbor/monitoring/dashboard.yaml) |
| Metrics | VictoriaMetrics, vmagent, vmalert | [Official VictoriaMetrics dashboards](controllers/base/victoria-metrics/README.md) |
| Alerting | Alertmanager | [Prometheus Alertmanager mixin](controllers/base/prometheus-alertmanager/README.md) |
| Logs / traces | Loki operations, Tempo operations | [Loki](controllers/base/loki/README.md), [Tempo](controllers/base/tempo/README.md) |
| Collection | OTel Collector | [OpenTelemetry Collector source](controllers/base/otel-collector/README.md) |
| External availability / network | All probes, HTTP, ICMP, DNS, TLS, bandwidth | [Blackbox mixin and dotdc node network section](controllers/base/blackbox-exporter/README.md) |
| Cloudflare | Tunnel connectors | [Official cloudflared dashboard](../infra/configs/overlays/kubevirt-cluster-319/cloudflare-operator/monitoring/README.md) |
| Object storage | SeaweedFS | [Official SeaweedFS dashboard](../infra/configs/overlays/kubevirt-cluster-319/seaweedfs-s3/monitoring/README.md) |
| Installation-specific | Application Logs, Ingress Requests, Observability Platform | [Log investigation](controllers/base/loki/README.md), [ingress correlation](../infra/configs/base/istio/monitoring/README.md), [metrics runtime](controllers/base/victoria-metrics/README.md) |

## Follow an ingress request

Open **Ingress Requests**, select the cluster, time range and entrypoint, then
paste a full Request ID or CF-Ray. Matching logs and sampled ingress traces are
side by side. Expand slow/error traces for focused investigation, or follow a
native TraceID link to the complete distributed trace. **Traces Drilldown** opens
Grafana's installed trace-analysis app. **Open trace ID** uses the optional
Trace ID field directly.

The metric cards remain cluster traffic trends; ID filters narrow logs and
traces. Ingress HTTP metrics select gateway source reports, excluding waypoint
copies. Cloudflare connector metrics describe the tunnel, not Cloudflare's edge
request logs. An ID cannot recover a request that was not collected or sampled.
Application propagation determines whether one trace spans multiple services.
Only the three targeted ingress Gateways supply the Istio ingress marker;
internal waypoint-only traffic remains in application/mesh views. Gateway access
logs include successful unsampled requests and local authorization redirects.
A valid trace ID in a log does not imply that sampling retained the trace.

## Find application logs

Open **Application Logs**, choose the cluster, workload namespace, service and
Pod, then use severity, literal text or an ID. Empty ID fields keep all records.
The default view shows counts, trends and up to 200 matching records; errors and
cross-service trace lookup are folded below. Expand a record for structured
metadata and its native TraceID link. Counts describe collected logs, not
application health.

Log text and workload filters apply to logs. Request ID / CF-Ray trace lookup
uses exact full IDs across services, so it does not truncate a trace at a
namespace boundary. The optional Trace ID field filters logs and enables direct
trace lookup. Tempo search returns the first matches in range, not necessarily
the newest; reduce the time range when searching a busy system.

Open a span in the native trace view to follow its metrics links: sampled span
rate by kind/status and p50/p95 latency. Links use the span's available cluster,
namespace and service attributes and open a five-minute margin around the span.
These are sampled-span trends, not total request traffic; client/server kinds
remain separate. New namespace-qualified metric samples are required after
rollout. See [Tempo's bindings](controllers/base/tempo/README.md#trace-to-metric-navigation).

[Harbor](../infra/configs/base/harbor/README.md#native-application-tracing) and
[Grafana](../apps/base/grafana/README.md) also export native application spans.
Keep their workload namespace selected when following span metrics. Their
contextual logs can link by trace ID; this does not make every application log
or request part of a stored trace. See each component's sampling and coverage
limits before interpreting missing spans.

For GitOps investigations, [Flux event tracing](../infra/configs/base/flux/monitoring/README.md#native-event-tracing)
adds revision/object searches in Tempo. Its event-age spans are separate from
application requests; use Flux's metrics dashboards for reconciliation duration.

## Investigate a probe

Start with **Network Availability**, then open the HTTP, DNS, TLS or ICMP view.
Choose the cluster, path, IP-family policy, job and target. The observed IP
protocol shows what was actually probed; it can differ from a dual-stack policy.
The failure table distinguishes a failed target probe from a scrape failure.
History shows the last recorded results and selected-range sample success,
rather than treating missing samples as successful probes. Expand protocol
details for phase timings, HTTP status, DNS answers or TLS expiry.

**Network Bandwidth** has separate native host/interface and SNMP selections.
Unconfigured ICMP or SNMP targets stay empty. Importing dashboards does not
install exporters, probes or application instrumentation. Component namespace,
managed-object namespace and cluster selectors retain their separate meanings;
they do not implement user-access isolation.

## Maintain the catalogue

Keep existing UIDs and owner-local ConfigMaps, bind the installed datasource
UIDs, and preserve native metric meanings and units. Expand needed upstream
recording expressions directly when their rules are not installed. Do not add
compatibility aliases or collectors just to populate optional panels. Verify
active-overlay rendering, source hashes, variable options, cluster/namespace
scope, joins and native queries before updating a source. Verify authenticated
rendering and navigation after the reviewed change is reconciled.
