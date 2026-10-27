# Flux dashboards

These dashboards use the official
[`fluxcd/flux2-monitoring-example`](https://github.com/fluxcd/flux2-monitoring-example/tree/7ab65dc8b90f7a6751d88f18bbb4e1bee33bf334/monitoring/configs/dashboards)
at commit `7ab65dc8b90f7a6751d88f18bbb4e1bee33bf334`.
`LICENSE.dashboard` preserves its Apache 2.0 license.

| Local file / UID | Upstream file | Upstream SHA-256 |
| --- | --- | --- |
| `dashboard.json` / `flux` | `cluster.json` | `2a52d416ca7fee166c7703524332d3c8e586808c21ff5679a259c9dd744ed309` |
| `control-plane-dashboard.json` / `flux-control-plane` | `control-plane.json` | `604dd55eadc2fc66ee6933d339d51ed475595699fc11c6fec26b91f6831a8e27` |

Panel design and layout remain upstream. Both use `victoriametrics` and explicitly
scope metrics to `k8s_cluster_name`. The cluster dashboard updates UID `flux` in
place; the control-plane dashboard adds a separate view of the controllers.

Queries use the current Flux Operator `flux_resource_info` directly, with native
`kind` and `suspended="True"` labels. The old kube-state-metrics
`gotk_resource_info` producer is not deployed and is not recreated. Tables and
filters distinguish controller `namespace` from `flux_resource_namespace_name`.
Per-object latency legends and aggregations retain the resource namespace so
objects with equal names remain distinct.

The control-plane dashboard scopes every query to the selected controller
namespace and `.*-controller-.*` Pods, including upstream queries that omitted
these filters. Process/controller queries and namespace options use the existing
`monitoring/flux-controllers` scrape job; container memory comes from cAdvisor.
Built-in Grafana event annotations remain Grafana queries, not Prometheus queries.
Saved upstream selections are cleared. No aliases, extra collectors or recording
rules are introduced.

When updating, verify the pinned sources, reapply the datasource/label bindings,
and check the variables, readiness tables and controller queries against current
metrics. Sources with no Bucket resources and healthy-only failure selections may
have no series; they must not include unrelated controllers or another cluster.

## Native event tracing

The shared [flux-event-tracing Component](../../../../../observability/components/flux-event-tracing/)
connects notification-controller's native `otel` Provider to the existing
Collector's OTLP HTTP `/v1/traces` endpoint. Each enrolled namespace has one
`tempo` Provider and one `gitops-events` Alert, owned by its existing Flux path.
The Alert omits source namespaces, so it selects only local resources.
Wildcard names cover new objects without updating a central inventory.

The template includes every event-source kind supported by notification-controller
1.8.4 except HelmRepository, which its native exporter skips. It does not install
additional controllers. Success and error events are both forwarded; no
user-notification receiver is involved.

To enroll a namespace, include the Component once in the existing Kustomization
that sets that namespace. If the parent also manages resources in other
namespaces, use a small child Kustomization so namespace transformation applies
only to the Provider and Alert:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: my-app
components:
  - <relative-path>/observability/components/flux-event-tracing/
```

Reference that child from its parent's `resources`. Do not add the Component to
every application in a shared namespace: one existing owner is sufficient for
all local Flux resources. New namespaces require this one-time inclusion; Flux
does not discover and enroll arbitrary namespaces automatically.

In Grafana Explore, choose Tempo and search:

```traceql
{ resource.service.name = "flux-system/gitops-events" && span.flux.resource.kind = "Kustomization" }
```

For a release investigation, keep its namespace and name together:

```traceql
{ resource.service.name = "harbor/gitops-events" && span.flux.resource.kind = "HelmRelease" && span.flux.resource.namespace = "harbor" && span.flux.resource.name = "harbor" }
```

The native service name is `<alert-namespace>/gitops-events`, and resource
`service.namespace` is the Alert's namespace. Resource `k8s.namespace.name`
still identifies the emitting controller Pod in `flux-system`, not the managed
application. The Collector maps native `object.*` span fields to
`flux.resource.*` to distinguish the managed object. Native event metadata,
including `revision`, remains on spans and is not promoted to resource
attributes or metric dimensions.

These are event-derived spans, not controller-internal SDK traces. The native
exporter correlates the Alert UID and revision. Separate namespace Alerts have
separate UIDs and trace groups; different Git/chart revisions also produce
separate groups. These spans do not form a complete deployment dependency graph.
Within one Alert, missing revisions share an `unknown` revision. Span start is
the event timestamp and span end is export time: latency represents event age,
not reconciliation duration or application latency. Use the existing Flux
metrics dashboards for reconciliation duration.

Events are exported without probabilistic filtering, subject to the controller's
event filtering/deduplication; this does not change HTTP/mesh sampling. No
historical events are replayed. Delivery is best effort: 1.8.4 does not return
span-export errors through `Post`, so the presence of Provider/Alert resources or
a successful dispatch log is insufficient acceptance. After merge, verify new
revision/object spans in Tempo, namespace separation and Collector queues/export
failures. Event traces do not automatically share trace IDs with controller logs
or application traces.

Contract: [pinned exporter implementation](https://github.com/fluxcd/notification-controller/blob/v1.8.4/internal/notifier/otel.go),
[Provider documentation](https://fluxcd.io/flux/components/notification/providers/#otel).
