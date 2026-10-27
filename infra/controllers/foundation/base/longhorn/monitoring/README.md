# Longhorn dashboard

`dashboard.json` adapts ONZACK's community
[Longhorn Monitoring & Backups dashboard](https://github.com/onzack/grafana-dashboards/blob/ecfade2a8d983684e34213a47af05d4ac2cb908a/grafana/longhorn/onzack-longhorn-monitoring.json),
pinned to commit `ecfade2a8d983684e34213a47af05d4ac2cb908a`.
Upstream SHA-256:
`4f304a1abcf9d3f093263cdf866cf2acc6f326db34388c87ff44419e252904e0`.
`LICENSE.dashboard` preserves its Apache 2.0 license.

The dashboard updates UID `longhorn` in place, binds `victoriametrics`, and scopes
every metric selector to `k8s_cluster_name`. PVC namespace, claim and volume
selection remain separate from the emitting controller namespace. Source panels
and layout are retained with these adaptations for Longhorn 1.11.2:

- Volume health and attachment counts use `state="..."` with value `1`.
  Older integer-enum and alternate robustness-label branches are removed.
- Capacity, used space and usage percentage share `(pvc_namespace, pvc, volume)`.
  Kubelet usage is joined through native `kube_persistentvolumeclaim_info` to
  obtain the volume name. Equal claim names in different namespaces stay distinct.
- The backup population is labelled **PVC Volumes**: a PVC alone does not prove
  that a backup policy is required. Backup states and recurring-job labels use the
  native producer; no synthetic compatibility labels are added.
- The alert slot uses a native Prometheus table for firing `Longhorn.*` alerts
  from `ALERTS`. Grafana's alert-list panel would show Grafana-managed rules rather
  than our VMAlert rules.
- The existing Replica Count view is retained as a final panel, using native
  `longhorn_replica_info` and the same volume selection.

Saved source selections are cleared. The existing persistent-volume dashboard,
alerts, scrape and access policies are unchanged. A count of zero failing alerts
or backup jobs is normal; absence of a backup is displayed rather than repaired
or assigned a policy by this dashboard.

For updates, verify the pinned source, reapply these bindings, and validate state
counts, PVC joins, units and the active Kustomize output. Preserve the UID and
namespace meanings; do not restore old metric aliases.

## Persistent-volume dashboard

`persistent-volumes.json` uses the Kubernetes mixin dashboard distributed by
[kube-prometheus](https://github.com/prometheus-operator/kube-prometheus/blob/174e45d20337d6cdfd5d8bfd042acdf479a38424/manifests/grafana-dashboardDefinitions.yaml),
pinned to commit `174e45d20337d6cdfd5d8bfd042acdf479a38424`.
Source key: `grafana-dashboard-persistentvolumesusage` /
`persistentvolumesusage.json`. The extracted unmodified JSON has SHA-256
`4b44b315ea2696595136ac2d3e5fa08a1f93f4cbba25085f61ef112cbfa07815`.
`LICENSE.kube-prometheus` preserves its Apache 2.0 license.

UID `persistent-volumes`, native space/inode visualizations and datasource
`victoriametrics` are retained. Every selector is scoped by `k8s_cluster_name`,
PVC namespace and claim, preserving the native kubelet labels. Namespace/claim
options use `kube_persistentvolumeclaim_info` so Pending PVCs can also be selected.
The existing Pending PVCs panel is retained and shows only active Pending state.
Space/inode panels require the selected claim to be mounted and reported by CSI;
they can be empty for a Pending or unmounted claim. No kubelet, CSI, storage or
retention settings change with this import.
