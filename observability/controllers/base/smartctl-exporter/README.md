# Kubernetes node SMART

The official [smartctl-exporter 0.14.0](https://github.com/prometheus-community/smartctl_exporter/tree/v0.14.0)
runs once per Linux amd64 node labeled
`observability.ccsn.dev/smartctl-exporter=true`. The existing NixOS K3s module
declares this label on all three physical nodes; there is no Kubernetes host
list or fixed target address. Native node-exporter remains the resource,
filesystem and I/O collector.

## Device visibility and privileges

Native `smartctl --scan --device=by-id` discovers devices. The exporter keeps
ATA IDs, physical NAA-5 SCSI IDs and MegaRAID member IDs. This excludes the
current Longhorn iSCSI devices and PERC logical volumes. Stable ATA/SCSI IDs
avoid `/dev/sdX` ordering; MegaRAID labels retain the bus and member ID.
Other WWN formats and NVMe devices require a reviewed filter extension.

Read-only inspection on 2026-11-13 identified ten distinct physical disks:
three on `kubevirt-dl160`, two on `kubevirt-dl380`, and five on `kubevirt-t410`
(including its three PERC members). These are observations, not hardcoded
scrape targets or universal expected counts. All ten returned health readings.
Unsupported optional SMART commands can still set exit flags independently of
failed disk health. Do not suppress or reinterpret native command flags.

As with the [upstream Kubernetes chart](https://github.com/prometheus-community/helm-charts/blob/prometheus-smartctl-exporter-0.19.2/charts/prometheus-smartctl-exporter/templates/daemonset.yaml),
the container uses root and privileged device access for block-device and RAID
ioctls. Only host `/dev` is mounted, read-only. There is no host network, host
PID namespace, host root mount, Kubernetes RBAC grant or mounted API token.
The mount does not make privileged ioctls read-only: trust the pinned official
image and its native read-only smartctl arguments. No self-tests or disk-setting
commands are configured. Each Pod requests 10m CPU/32 MiB and is limited to
250m CPU/128 MiB.

## Collection and alerts

Pods join the existing ambient mesh. A selector-scoped strict PeerAuthentication
and L4 AuthorizationPolicy permit only
`monitoring/vmagent-victoriametrics-vmks` on port 9633. The PodMonitor discovers
each Pod directly; no Service, host port, gateway or additional certificate
controller is needed. Scheme HTTP describes the application listener; ztunnel
provides mTLS between the collector and exporter workloads.
The existing runtime Flux owner waits for networking-core as well as the
monitoring API gate, so Istio security APIs precede these resources.

Scrapes run every 60 seconds with a 15-second timeout and 5000-sample limit.
The native job is `smartctl`, `node` comes from Pod discovery, and `instance`
retains the individual Pod endpoint. The existing shared **SMART / Physical
Disks** dashboard and `SMART*` health rules therefore cover these hosts without
duplicated models or metric aliases. Kube-state-metrics exposes the opt-in
node label for disappearance detection.

`SMARTNodeMetricsMissing` detects an opted-in node with no discovered target;
the existing `ScrapeTargetDown` covers unreachable targets. A reachable exporter
with zero selected physical disks or missing health readings triggers
`SMARTNodeDeviceCoverageIncomplete`. If scanning itself loses a disk, its
selected count can also decrease; these rules do not establish a fixed physical
inventory. Cached last-good readings have no native per-device freshness
timestamp. SMART does not establish RAID controller, battery or enclosure health.

After GitOps rollout, verify one Ready Pod and one successful target per opted-in
node, ten distinct physical disk readings against the current inventory, the
shared dashboard Host selections, and rejection of non-vmagent metrics traffic.
The source and offline tests alone do not establish deployed mesh enforcement.
