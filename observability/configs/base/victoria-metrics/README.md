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

## Node, Pod and control-plane views

`kubernetes-node.json`, `kubernetes-pod.json` and
`kubernetes-control-plane.json` use
[dotdc's Kubernetes dashboards](https://github.com/dotdc/grafana-dashboards-kubernetes/tree/e4faf59e017a18e1b06fa64f11623bef15ce7507/dashboards),
pinned to commit `e4faf59e017a18e1b06fa64f11623bef15ce7507`.
`LICENSE.dotdc` preserves their Apache 2.0 license.

| Local file / existing UID | Upstream file | Upstream SHA-256 |
| --- | --- | --- |
| `kubernetes-node.json` / `kubernetes-node` | `k8s-views-nodes.json` | `4a11656116232acc2b1fdf77261e7c814af88c52a5559039db56e84b88772be7` |
| `kubernetes-pod.json` / `kubernetes-pod` | `k8s-views-pods.json` | `e1282688933864c649c78a91352b434843b4e863c744128adc11d4d2b10b6bfd` |
| `kubernetes-control-plane.json` / `kubernetes-control-plane` | `k8s-system-api-server.json` | `f2a7970729eb906fae2e79f38454103f6ac6ee3e62eb00910781c90dee507d72` |

Layouts and visualizations are retained. Each query uses `victoriametrics` and
`k8s_cluster_name`; the upstream `cluster` selector is replaced throughout,
including variable queries and Node/Pod links. Saved demo values and unused
Terraform/OnCall annotations are removed. No recording rules or metric aliases
are introduced.

The node view uses the native `node_uname_info.node` identity to find its exporter.
Pod and PVC series retain namespace in their grouping and legends, so equal names
in different namespaces do not merge. Disk I/O in progress reads the native gauge
rather than applying `rate`. The existing readiness, allocatable capacity and Pod
capacity panels remain as a final row.

The Pod view selects one workload namespace and Pod. Information, error and
unscheduled-Pod panels follow that same selection; it cannot accidentally show
another namespace's failures. Existing Pod readiness remains visible.
The Not Ready value is `1 - readiness`, so an unhealthy Pod displays one rather
than the producer's zero-valued readiness gauge.
The control-plane view scopes all panels to its selected API-server job, including
p99 latency, scheduler attempts and per-queue depth retained from the old view.
K3s exposes those scheduler/queue metrics through the API-server target.

Hardware-specific node metrics, missing container termination history and zero
active faults may leave panels empty. Namespace and cluster selectors organize
queries; they do not implement Grafana user authorization.
