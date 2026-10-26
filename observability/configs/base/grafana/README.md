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
