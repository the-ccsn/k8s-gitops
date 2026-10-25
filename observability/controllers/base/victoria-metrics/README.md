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
