# Grafana dashboard

`dashboard.json` uses the official Grafana mixin's generated overview from
[Monitoring Mixins](https://github.com/monitoring-mixins/website/blob/7b1f6de899ffdbdf59c807a32cd8a9a514231915/assets/grafana/dashboards/grafana-overview.json),
pinned to website commit `7b1f6de899ffdbdf59c807a32cd8a9a514231915`.
Its SHA-256 is
`c91a84f8d193ee322d274c9fa7d9ac598056224720854612365b1ae6aa3faef6`.
The catalog identifies
[`grafana/grafana/grafana-mixin`](https://github.com/grafana/grafana/tree/a100054f212653d1f15ae4fc80e98c9548c77f86/grafana-mixin)
as the source. `LICENSE.dashboard` preserves its AGPL 3.0 license from Grafana
v13.0.1 commit `a100054f212653d1f15ae4fc80e98c9548c77f86`.

The five upstream panels retain their layout and native visualizations. Local
bindings update UID `grafana` in place, use `victoriametrics`, and add a
`k8s_cluster_name` selector to every metric query. Job/instance options are scoped
to that cluster, and the instance options also follow the chosen job. Saved
upstream selections are cleared.
The refresh interval stays at 30 seconds.

The firing-alert panel queries the current `grafana_alerting_alerts{state="alerting"}`
gauge, rather than the old evaluation-result counter. No metric aliases or
fallback queries are retained. The remaining panels show the dashboard count,
build information, request rates and latency.

This imports only a dashboard; Grafana login, role synchronization, alert rules
and data source permissions are unchanged. When updating, verify the source hash,
reapply these bindings and validate the variables and queries against current
Grafana metrics.

## Kubernetes overview

`kubernetes-overview.json` uses dotdc's
[`k8s-views-global.json`](https://github.com/dotdc/grafana-dashboards-kubernetes/blob/e4faf59e017a18e1b06fa64f11623bef15ce7507/dashboards/k8s-views-global.json),
pinned to commit `e4faf59e017a18e1b06fa64f11623bef15ce7507`.
Upstream SHA-256:
`89b52678c34b978b621feac39eaa9fce73fbe5df3049d4472bd12db91a61958f`.
`LICENSE.kubernetes-dashboard` preserves its Apache 2.0 license separately from
the Grafana dashboard's AGPL license.

The dashboard retains UID `kubernetes-overview`, upstream layout and
`victoriametrics`, with `k8s_cluster_name` on every metric selector and dependent
variable. Native namespace labels continue to refer to workloads. The resource
count uses current `kube_endpointslice_info` and
`kube_horizontalpodautoscaler_info` metrics; the EndpointSlice legend matches
that resource rather than the retired Endpoints API. Job filters support the
upstream multi-selection. Namespace, Deployment, StatefulSet, DaemonSet and
NetworkPolicy counts use their native creation metrics instead of optional
`*_labels` series; timestamps are counted, not summed.
Not Ready Pods is retained as a final panel, alongside
the upstream namespace CPU/memory and container restart views.
It sums `1 - readiness` to count unhealthy Pods rather than summing zero values.

Saved demo selections and unused Terraform/OnCall annotations are removed.
Unconfigured resource types and hardware-specific throttling counters may have
no series. Updating this file requires source/hash verification, preserving the
UID, and checking all variable and panel queries against current native metrics.
