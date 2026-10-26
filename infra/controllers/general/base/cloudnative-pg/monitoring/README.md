# CloudNativePG monitoring

`dashboard.json` is the official [CloudNativePG Cluster dashboard](https://github.com/cloudnative-pg/grafana-dashboards/blob/47e4c51219fdbb3c7ef2c4d91a2d8855e9ca1880/charts/cluster/grafana-dashboard.json),
pinned at commit `47e4c51219fdbb3c7ef2c4d91a2d8855e9ca1880`.
The unmodified source SHA-256 is
`89290731e516104f57673746fff65916ba2e749c4b942144a03eb53ff9dae7a8`.
Its Apache 2.0 license is included in `LICENSE.dashboard`.

The local copy keeps the upstream panels and UID. The required adaptations are:

- Bind Prometheus and expression references to the existing `victoriametrics`
  and `__expr__` datasource UIDs; remove the interactive import inputs.
- Replace the datasource selector with a Kubernetes cluster selector, and scope
  all metric queries to its `k8s_cluster_name` value.
- Read CNPG cluster choices from `cnpg_cluster_name` and label that selector
  `CNPG Cluster`. The shared `namespace` label retains its Kubernetes meaning.
- Select the declared Helm release's `cnpg-cloudnative-pg-*` operator Pods for
  readiness, using the actual workload name instead of other installation names.

The existing `cloudnative-pg` dashboard is updated in place. There is no second
dashboard, old-label alias, or runtime conversion. When updating the pin, fetch
the source, verify its hash, reapply these adaptations, and check every variable
and panel query against the collected metrics. Preserve the UID and panel design.

Both database and operator scraping use owner-local PodMonitors. The operator
opts into ambient at Pod level; its metrics port 8080 accepts only the vmagent
identity through ztunnel. Other ports retain their existing access policy.

The standard container CPU recording rule is owned by
`observability/configs/base/victoria-metrics/kubernetes-recording-rules.yaml`.
It retains `k8s_cluster_name` in the result. Kube-state-metrics exports only the
node zone label required by the upstream instance table; a node without a zone
has no zone value. Backup, replication, extension and configuration panels show
the metrics available for the selected PostgreSQL instances and features.
