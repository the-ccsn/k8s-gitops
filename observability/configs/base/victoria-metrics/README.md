# Kubernetes dashboards

The cluster and namespace JSON files use ONZACK's community dashboards without
recording-rule dependencies, pinned to commit
`ecfade2a8d983684e34213a47af05d4ac2cb908a`.
Sources are under
[`grafana/kubernetes/without-recording-rules`](https://github.com/onzack/grafana-dashboards/tree/ecfade2a8d983684e34213a47af05d4ac2cb908a/grafana/kubernetes/without-recording-rules).
`LICENSE.dashboard` preserves the Apache 2.0 license.

| Local file / existing UID | Upstream file | Upstream SHA-256 |
| --- | --- | --- |
| `kubernetes-cluster.json` / `kubernetes-cluster` | `onzack-cluster-monitoring.json` | `f9ea15b8bb8454f356723f413e424cc09abeca274a067a1b390e934cc6e6cf8e` |
| `kubernetes-namespace.json` / `kubernetes-namespace` | `onzack-namespace-monitoring.json` | `d3f36a4ed9072390a194f10a9c49ef361664d04d9a40bbd68e759d919bcac615` |

The upstream panels, types and layout are preserved. Bindings use the existing
`victoriametrics` datasource, retain the dashboard UIDs, and add
`k8s_cluster_name` to every metric selector and dependent variable query.
Native kube-state-metrics, cAdvisor and node-exporter labels remain unchanged.
No recording rules or additional metrics collectors are required.

The cluster dashboard uses the selected real node role in its capacity overview
instead of assuming that the cluster has `role="worker"` nodes. Its role selector
remains single-valued to avoid counting nodes once per assigned role. The upstream
spare-node factor is a selectable capacity-planning assumption, not a change to
Kubernetes scheduling or Longhorn reservations.

The namespace selector refers to the workload namespace, not an exporter or
operator namespace. Queries distinguish same-named Pods through their namespace
and Kubernetes cluster. Quota and VPA panels are empty when those optional
resources are not configured; importing a dashboard does not deploy them.

Saved upstream demo selections are cleared. The dedicated deployment, Pod, node,
control-plane, PVC and application dashboards remain distinct existing views.
To update, verify source hashes, preserve UIDs, reapply scopes, and check joins,
variable options and every panel query against the current collected metrics.
