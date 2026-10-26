# Metrics runtime

The pinned stack chart `0.79.1` runs VMSingle, VMAgent and VMAlert. Operator
chart `0.63.1` packages binary `v0.70.1`. Scrape and rule policy uses neutral
Prometheus Operator resources under `observability/configs` and component-local
`monitoring/` directories; chart-generated VM scrapes and rules stay disabled.

- VMSingle: seven-day retention, 20Gi Longhorn PVC; query/write endpoint
  `http://vmsingle-victoriametrics-vmks.monitoring.svc.cluster.local:8428`.
- VMAgent: one StatefulSet replica, 2Gi Longhorn PVC, 1Gi remote-write queue.
  Its target/debug UI is on port 8429.
- VMAlert: evaluates rules and notifies the separately managed native
  Alertmanager through the existing notifier Secret.

The shared API gate owns the HelmRelease; dashboards and monitors are selected
after that gate. Existing deployments require storage/version inspection before
reconciliation. Switching VMAgent from Deployment to StatefulSet requires a
controller/Service migration; the old ephemeral queue is not transferred.

Use the existing manifest and flux-local CI checks before merging changes.

Scraped metrics use qualified infrastructure metadata such as `k8s_cluster_name`;
component-specific identities follow the [shared naming contract](../../../README.md).
Keep the standard `job`, `instance` and Kubernetes metric labels used by upstream
dashboards and Headlamp. Renaming a label changes series identity; historical
samples retain their previous keys until retention expires.

The VMSingle Service uses the shared observability waypoint. Its API policy
allows Grafana, Kiali and Headlamp to query; VMAlert can also query and remote
write; VMAgent and Tempo can remote write. Blackbox can only check health.
Other API paths, including GET-based deletion, are denied through the Service.

The workload policy prevents those clients from bypassing the waypoint through
Pod addresses. VMAgent retains direct Pod access for metrics scraping and must
remain trusted with the whole backend port. These controls do not isolate
metrics by namespace or change Grafana/Kiali login roles.

The three component dashboards use unmodified official JSON from the deployed
`v1.143.0` release, pinned by commit and recorded SHA-256. Grafana Operator
binds `${ds}` references to the `victoriametrics` datasource UID; the upstream
`$ds` variable refreshes from Prometheus-compatible datasources on load.
VMSingle stays in Database; vmagent and vmalert are in Platform. The separate
Observability Platform overview remains specific to this installation.

VMSingle now uses upstream dashboard UID `wNf0q_kZk`; existing bookmarks using
`victoriametrics` must be updated. The pinned operator handles the UID change
through its normal dashboard reconciliation. vmagent and vmalert use upstream
UIDs `G7Z9GzMGz` and `LzldHAVnz`.
