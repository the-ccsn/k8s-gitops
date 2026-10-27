# Observability naming contract

See the [dashboard catalogue and investigation guide](dashboards.md) for active
views, upstream sources and log/trace/Blackbox navigation.

This contract applies to every active collector, component monitor, rule,
dashboard and correlation link. Metrics remain in VictoriaMetrics single-node;
logs and traces remain in Loki and Tempo. Naming separates meanings within these
backends; it does not provide tenant or user-access isolation.

## Names and ownership

- Keep upstream metric names and shared library namespaces: `cnpg_*`, `harbor_*`,
  `istio_*`, `process_*`, `go_*` and `controller_runtime_*`, for example. Do not
  prepend the emitting application's name to every shared metric.
- Use existing OpenTelemetry semantic attributes first. Dots separate namespaces;
  each multiword segment uses `snake_case`. Custom concepts use a clearly owned
  namespace, such as `cnpg.*` or `ccsn.*`.
- Use underscores for our Prometheus label keys. A metric name's colon is reserved
  for recording rules such as `level:metric:operations`; `cnpg:cluster` is not our
  label format. Modern UTF-8 label support does not make it a portable choice for
  the whole collection and dashboard toolchain.
- Preserve native Prometheus integration labels such as `job`, `instance`,
  `namespace`, `pod`, `container` and `node`. Their documented source remains
  important: an exporter's namespace is different from its managed object's
  namespace. Give the latter an explicit component key when they collide.
- Preserve native HTTP, database and service semantic attributes. `service.name`
  describes the producer; `service.namespace` is its logical service namespace.
  `db.namespace` is a database namespace, not a CNPG Cluster or Kubernetes namespace.
- Keep Kubernetes API labels, resource names, RBAC subjects, DNS names and raw
  application payloads intact. This policy is not a text replacement of every
  occurrence of `cluster`, `namespace`, `name` or `instance`.

These rules follow [OTel naming conventions](https://opentelemetry.io/docs/specs/semconv/general/naming/),
[Prometheus naming](https://prometheus.io/docs/practices/naming/), its
[data model](https://prometheus.io/docs/concepts/data_model/) and
[recording-rule conventions](https://prometheus.io/docs/practices/rules/).

## Resource and component identities

| Meaning | OTLP resource attribute | Prometheus label / Loki-normalized key |
| --- | --- | --- |
| Kubernetes cluster / metric collection origin | `k8s.cluster.name` | `k8s_cluster_name` |
| Kubernetes namespace | `k8s.namespace.name` | Native metrics keep `namespace`; Loki uses `k8s_namespace_name` |
| Pod / container / node | `k8s.pod.name` / `k8s.container.name` / `k8s.node.name` | Native metrics keep `pod` / `container` / `node`; Loki uses the underscored OTel names |
| Logical service | `service.name` / `service.namespace` | Loki uses `service_name` / `service_namespace`; native metric identity remains `job` / `instance` |
| Deployment environment | `deployment.environment.name` | `deployment_environment_name` |
| Installation site | `ccsn.site.name` (custom) | `ccsn_site_name` |
| CNPG Cluster | `cnpg.cluster.name` (custom) | `cnpg_cluster_name` |
| Certificate's namespace | No trace attribute synthesized | `cert_manager_certificate_namespace_name` |
| KubeVirt object's namespace | No trace attribute synthesized | `kubevirt_resource_namespace_name` |
| Flux object's namespace | No trace attribute synthesized | `flux_resource_namespace_name` |

`cnpg.cluster.name` is our custom attribute, not a published OTel convention.
The Collector extracts it from a producer Pod's `cnpg.io/cluster` label. It is
not assigned to an operator managing several clusters or inferred for a client
span merely because that client talks to PostgreSQL. A CNPG object is identified
by Kubernetes cluster, namespace and CNPG cluster name together.

The CNPG PodMonitor sets `cnpg_cluster_name` from the same Pod label before
scraping, so exporter health and backup metrics also carry it. It drops the
exporter's redundant bare `cluster`; global metadata adds `k8s_cluster_name`.
There is no collision between the database and Kubernetes identities.

For example:

```promql
cnpg_collector_up{
  k8s_cluster_name="kubevirt-cluster-319",
  namespace="harbor",
  cnpg_cluster_name="harbor-pg-cluster"
}
```

The source-object namespace mappings are endpoint-local. With our pinned vmagent
and default `honor_labels: false`, source labels that conflict with target labels
arrive at metric relabeling as `exported_namespace`. The monitors immediately
rename this to the appropriate key above; dashboards and alerts do not depend on
the fallback name. The common `namespace` still identifies the scrape target.
Do not enable `honor_labels` as a substitute for this mapping.

VMAgent adds `k8s_cluster_name`, `deployment_environment_name`, `ccsn_site_name`
and custom `ccsn_platform_name` to its scraped metrics. For external scrape
targets, the cluster label identifies the collecting Kubernetes cluster, not
Kubernetes membership of the target. Tempo's metrics generator
uses the same Kubernetes-cluster and environment keys for its direct remote
write. The Collector supplies the dotted cluster, environment and site resource
attributes to logs and traces as defaults, preserving explicit producer values.

OTLP resource attributes are not automatically labels on every metric. Our
native metrics use explicit scrape relabeling. Loki normalizes the configured
dotted resource attributes to underscore keys; new resource metadata is not
automatically promoted to an index label. Grafana explicitly maps
`k8s.cluster.name` to `k8s_cluster_name` for trace-to-log links.

## Ingress correlation

| Meaning | Log/span attribute | Loki structured-metadata key |
| --- | --- | --- |
| Ingress layer (`campus` or `istio`) | `ccsn.ingress.entrypoint` | `ccsn_ingress_entrypoint` |
| Istio proxy role (`mesh` or `ingress`) | `istio.proxy.role` | `istio_proxy_role` |
| Stable request correlation | `ccsn.request.id` | `ccsn_request_id` |
| Cloudflare Ray ID | `cloudflare.ray.id` | `cloudflare_ray_id` |

These are custom fields, not claims that OTel defines these attributes. They are
shared by NGINX and Istio where they describe the same request. Istio's temporary
`istio.proxy.request_id` supplies the direct-Gateway fallback and is removed
before export. W3C trace/span IDs keep their protocol-defined identity, and
`X-Request-ID`, `X-CCSN-Request-ID` and `CF-Ray` headers retain their wire names.

Proxy request-ID fallback, HTTP URL redaction and access-log severity use proxy
identity independently of ingress classification. Istio container logs and its
native request-ID span tag identify the proxy; campus records retain their
explicit source marker. Application SDK spans and unrelated application status
fields are outside that proxy normalization.

Only targeted ingress Gateways emit the Istio ingress marker. Mesh-only proxies
retain their role and correlation fields without appearing in ingress searches.
The ingress Gateways retain every HTTP access record, including local replies
and unsampled requests; a log's trace ID does not guarantee a stored trace.
Mesh logging stays selective and new traces remain sampled at one percent.

Producers and consumers use only these canonical names. Do not introduce old-key
aliases or transitional conversions. The Collector leaves unrelated application
attributes alone. Query-string redaction and nil/empty request-ID fallback apply
to recognized ingress spans.
Ingress HTTP status sets both OTLP severity number and text consistently; Loki
rules and the log-volume panel use `severity_text`, not a payload's `level`.

## Coverage and consumers

The following table defines the naming policy for each component family when
enabled; it does not enable targets or assert that live collection has passed.

| Component family | Contract applied |
| --- | --- |
| Kubernetes, node, SMART, OpenWrt, SNMP and blackbox targets | Keep native metric/MIB names and shared labels; apply qualified global infrastructure metadata and probe labels |
| CNPG and Barman | Explicit `cnpg_cluster_name`; namespace/Pod scope retained in the dashboard and alerts |
| cert-manager, KubeVirt and Flux | Qualified managed-object namespace; update the owner-local monitors, dashboard legends and alert annotations |
| Istio, Envoy, NGINX and Cloudflare Tunnel | Keep native metric namespaces; use qualified cluster filters and the ingress attributes above |
| VictoriaMetrics, Loki, Tempo, Collector and Alertmanager | Keep native metrics; update global metadata, log indexes, log rules, trace-derived metrics and notification grouping |
| Harbor, Redis, Logto, Cloudreve, Vaultwarden, SeaweedFS, Grafana, Kiali and other application targets | Preserve native component/library metrics; use the same collection contract; update authored probes and Kiali's metric filter |

Official/community dashboards retain their upstream names and shared-label
contracts. A component-specific mapping requires a small, documented consumer
adaptation rather than a private reimplementation of the dashboard. Headlamp's
queries continue to use the native Kubernetes metric and label names.

## Rollout and history

This is a forward schema change. Existing metrics, log streams and spans keep
their old labels/attributes until their existing retention expires. This change
does not delete, rewrite or backfill history. New dashboard filters use the new
keys; older time ranges require the prior field names in Explore. Rates need
fresh samples after the change, and current-range queries can briefly encounter
both generations of a series during independent Flux reconciliations.
The one-day dev-log retention selector uses only `k8s_namespace_name`.

Merge producer and consumer configuration together. Check VMAgent reload,
nonempty qualified labels, object-namespace alert annotations, sampled ingress
span/log request-ID equality and Grafana trace-to-log navigation after Flux has
applied it. No runtime compatibility layer or historical-data migration is
maintained. Existing PVCs, S3 buckets, tenant settings and login roles are unchanged.

When adding a component, review its native metric prefixes and label meanings,
normalize real collisions in its own monitor, and check dashboard variables,
rules and cross-signal mappings. Resource attributes and payload fields must not
be promoted wholesale into metric dimensions or log index labels.
