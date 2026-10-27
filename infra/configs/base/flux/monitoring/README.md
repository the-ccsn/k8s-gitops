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
