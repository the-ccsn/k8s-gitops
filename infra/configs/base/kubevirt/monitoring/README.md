# KubeVirt dashboard

`dashboard.json` adapts the official [KubeVirt monitoring dashboard](https://github.com/kubevirt/monitoring/blob/06ffe455bb0de1eb4366ddfc2c6d401038afcf37/dashboards/grafana/kubevirt-control-plane.json),
commit `06ffe455bb0de1eb4366ddfc2c6d401038afcf37`.
Unmodified upstream SHA-256: `1130b5c292b62181d4fbddfec9b7dca1eb4eea85bfd329ba6211a84c2d051337`.
`LICENSE.dashboard` preserves its Apache 2.0 license. UID `kubevirt` and
`victoriametrics` are retained. The view contains 25 charts.

The upstream Graph panels are converted to native Grafana timeseries panels for
Grafana 13. Applicable positions, units, series colors, stacking and legends are
preserved. Kubernetes-wide API, etcd and storage sections remain in their own
component views. KubeVirt API-client and work-queue charts use native
`kubevirt_rest_client_*` and `kubevirt_workqueue_*` metrics from the deployed
KubeVirt 1.8 release. Open file descriptors use the gauge directly.

The cluster, KubeVirt component namespace, job and endpoint select the producer.
VMI namespace is the separate `kubevirt_resource_namespace_name`, followed by
VMI name. VMI filters constrain the current phase inventory and VMI resources;
phase-transition histograms and component queues have their own native labels
and do not acquire a fictitious per-VMI identity. Queue `name` is a queue name,
not the selected VMI name.

The source's recent-transition approximation is replaced with current
`kubevirt_vmi_info`, deduplicated by cluster, VMI namespace, name and phase.
The existing VMI CPU, memory and network views remain. CPU uses the native total
VMI CPU counter, which includes guest vCPU and hypervisor CPU, in cores; memory
is bytes and network is bytes/second. Component and guest namespaces are never
interchanged. The metric definitions are in the pinned [KubeVirt 1.8.1 metrics
reference](https://github.com/kubevirt/kubevirt/blob/v1.8.1/docs/observability/metrics.md).

Phase histograms can have no series until lifecycle events are observed.
Empty charts do not create VMs or trigger lifecycle operations. For updates,
verify the source hash, reapply the native visualization and metric bindings,
then verify scope, inventory deduplication, gauges, histogram units and queries.
