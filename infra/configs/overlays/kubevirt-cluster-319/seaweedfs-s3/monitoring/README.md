# SeaweedFS dashboard

`dashboard.json` uses the official SeaweedFS **4.48** chart dashboard,
matching the verified OMV producer version. Source:
[`k8s/charts/seaweedfs/dashboards/seaweedfs-grafana-dashboard.json`](https://github.com/seaweedfs/seaweedfs/blob/530be3e37337488ecc34d58441e0bc476e121c93/k8s/charts/seaweedfs/dashboards/seaweedfs-grafana-dashboard.json),
commit `530be3e37337488ecc34d58441e0bc476e121c93`.
Upstream SHA-256:
`09a4af4e950aa9c42a8560d47c773bede30dbaa4ebe6065d85b7a76337bb74a7`.
`LICENSE.dashboard` preserves the Apache 2.0 license.

The official panel layout is retained. Local bindings update UID `seaweedfs` in
place and use `victoriametrics`. Every selector has `k8s_cluster_name` and the
existing `job="seaweedfs"`. The upstream Kubernetes namespace selector becomes a
SeaweedFS host selector using our existing `node` label. Pod legends/aggregations
likewise use the external host, without inventing Kubernetes identity for OMV.
Per-process panels use the native scrape `instance` label: these endpoints are
scraped directly and do not supply Pushgateway's `exported_instance` label.
Volume-server disk use and request latency therefore remain separate on one host;
the S3 per-instance latency panel likewise keeps each gateway distinct.
Master/filer job filters use the existing `component` labels. Bucket size/object
gauges retain upstream `max by(bucket)` to avoid counting copies from multiple
components. The refresh interval defaults to 30 seconds.

Volume disk totals sum native `normal` and `ec` bytes. `deleted_bytes` is already
part of a normal data file, so it remains visible in the type breakdown but is
not added again to totals. These metrics cover SeaweedFS data files/shards, not
complete filesystem, index or metadata usage.

`scrape-config.yaml` declares ten authenticated HTTPS paths: master, filer,
ordinary S3, direct S3 and six volume servers. The target names use internal DNS,
with no fixed IP or site-alias hostname. `instance` combines target address and
metrics path so the six volume servers on one host cannot overwrite each other.
The client Secret supplies CA trust, certificate and key; normal DNS-name
verification remains enabled. The direct S3 HTTPS transport probe stays separate.
S3 latency quantiles are empty without requests in the selected time window,
and bucket traffic metrics depend on producer support.

The [Portainer Stacks](../portainer/README.md) define loopback-only native
listeners and a common mTLS policy in both network namespaces. During ongoing
volume maintenance, the frontends can use existing listeners without restarting
the data services; persistent OMV firewall rules then restrict native metrics to
local access after HTTPS collection is adopted. Dedicated
cert-manager resources and read access to only the server leaf Secret are
included here. This version requires those Stacks to be deployed; publishing it
does not update OMV. Complete the documented certificate/OMV barrier before
publishing these HTTPS collection changes. The preparation commit keeps the old
three-target HTTP configuration until that barrier is satisfied.

Alerts cover failed targets, disappearance of any of the five component families
and fewer than six volume targets remaining in discovery. A failed but discovered
volume still counts toward that inventory and triggers the failed-target alert
instead. Volume I/O/read/write failures retain the affected `instance`; S3 latency
retains both gateway identity and request type. Bucket gauges remain deduplicated.

When updating, verify the pinned source, preserve the UID, reapply the
host/component bindings, and validate active queries and bucket deduplication.

## OMV host metrics

`host-scrape-config.yaml` collects the official node-exporter through
`https://openmediavault.local:9443/node/metrics`, using the existing mTLS client
Secret and hostname verification. It retains native `node_*` metrics with
`job="node-exporter"`, `node="openmediavault-1"` and the collecting cluster's
`k8s_cluster_name`. OMV is not a Kubernetes node. The exporter and frontend must
pass the [Stack acceptance steps](../portainer/README.md#host-telemetry-addition)
before publishing this target. Collection runs every 30 seconds with a
10-second timeout and a 10,000-sample limit.

The shared node rules cover filesystem space/inodes/read-only state, disk
latency/queues, I/O pressure, memory, CPU/load, swap, OOM and network counters
when their native metrics exist. `ScrapeTargetDown` covers failed requests.
`OMVHostMetricsMissing` separately detects removal of this known host while
other node exporters remain healthy. `OMVHostCollectorFailed` checks only the
six expected core collectors on a reachable endpoint; absent optional hardware
subsystems do not trigger it. Check exporter logs and mounts before changing
permissions or disabling a core collector.

**Infrastructure → OMV / Node Exporter Full** uses rfmoz's Apache 2.0 community
[Node Exporter Full dashboard](https://github.com/rfmoz/grafana-dashboards/blob/b07d8a90d8fadd112e9ac841b777ee863cda850b/prometheus/node-exporter-full.json),
commit `b07d8a90d8fadd112e9ac841b777ee863cda850b`.
Upstream SHA-256:
`c2e79a5ead15537e0ebe276a2878c95d6286ca1ab8db2cd7f69d4ba8c079de7e`.
`LICENSE.host-dashboard` preserves the license. The upstream layout, panels,
units and calculations remain intact. Local bindings use UID `omv-host`,
datasource `victoriametrics`, a collection-cluster selector and exact OMV host
matchers in every query. The upstream `node` dashboard variable selects a scrape
`instance`; the metric's `node` label still identifies OMV. Saved demo selections
are cleared. No recording rules, aliases or extra collectors are installed.

Optional systemd, process, interrupt and TCP-state collectors are not enabled
just for this dashboard. Timex is intentionally disabled, and unsupported
hardware panels can be empty. Disk I/O and filesystem counters do not establish
SMART, RAID-member, controller/battery or physical temperature health. The
separate SMART addition below covers verified physical disks. Cluster/host selectors organize
queries and do not provide Grafana user-access isolation.

## OMV physical-disk SMART

`smart-scrape-config.yaml` adds native smartctl-exporter metrics through
`https://openmediavault.local:9443/smart/metrics`, using the existing mTLS client
and hostname verification. Its native job is `smartctl`, host label is
`node="openmediavault-1"`, and `k8s_cluster_name` identifies the collecting cluster.
It runs every 60 seconds with a ten-second timeout and a 5,000-sample limit.
Publish these resources only after the
[external Stack acceptance barrier](../portainer/README.md#physical-disk-smart-addition).
They do not install an exporter on OMV.

Read-only checks on 2026-11-09 matched three ATA and four SAS direct physical
disks to their MegaRAID member identities. Stable native by-id labels distinguish
them without duplicate controller paths or virtual QEMU disks. Disk replacement
therefore creates a new identity rather than inheriting the previous disk's
history. The expected minimum is seven health-reporting disks; revise that count
only after an intentional inventory change.

Two OMV-specific rules cover missing discovery and incomplete seven-disk health
coverage. Seven shared rules cover every `job="smartctl"` target: failed
SMART health, approaching/reached native temperature limits, ATA pending or
uncorrectable sectors, increasing standard reallocated-sector counts, increasing
SAS grown-defect/uncorrected read/write counts, and active prefailure thresholds.
The existing `ScrapeTargetDown` covers a reachable-in-discovery but failed target.
Temperature warnings use native `drive_trip - 5 C`, falling back to 55 C only
when no trip threshold exists; critical temperature alerts require a reported
native threshold. Vendor operating limits remain authoritative. ATA IDs 197/198
are raw pending/uncorrectable counts; ID 5 additionally requires the standard
`Reallocated_Sector_Ct` name. Vendor-specific wear attributes are not reinterpreted.
Native SAS gauges use `delta`, not counter `rate`; corrected ECC totals alone
are not treated as failures. Historical nonzero error logs do not page forever.

The command exit status is a bitmask, not a Boolean health result. Mask 16 denotes
an active prefailure threshold. An unsupported optional error-log command can
produce status 4 while health and attributes remain valid, as observed on this
host's SATA SSD and the verified DL160/DL380 SSDs; that value alone is not a
failed disk. Inspect the original flags and attributes before scheduling tests
or replacement. No alert performs
recovery, disk writes or self-tests.

The pinned official exporter always includes `--log=error` in its native
[read command](https://github.com/prometheus-community/smartctl_exporter/blob/ef5c03de02cb793e6a1540bef943fe6a167de635/readjson.go#L67).
It has no native per-device option to omit that request. Keep the official
image and original exit flags rather than rewriting results or adding a command
wrapper. The diagnostic table identifies each affected host/disk and displays
the numeric mask with single-bit meanings. Value 4 remains a command/checksum
warning; only the original device output establishes an unsupported error log.
Combined masks remain numeric and must be interpreted bit by bit. The table
shows current nonzero readings; an empty table alone does not establish healthy
collection. The summary card counts disks with nonzero flags per host instead
of taking the numeric maximum of bitmasks. Health and sector alerts remain
independent.

Native exporter limits matter: failed reads can leave cached last-good results
with no per-disk freshness timestamp. Startup missing-health and rescan removal
are detectable, but this configuration cannot prove every cached value was just
read. Keep exporter logs and direct read-only `smartctl` verification in the
runbook. Controller/battery/array health is not supplied by SMART; neither are
PSU/fan sensors. The four SAS drives do not expose ATA attributes, and this
official version does not export their verify-error totals.

**Infrastructure → SMART / Physical Disks** retains the 18 panel/row entries
from the Apache 2.0 community smartctl mixin proposed in upstream PR #369:
[`mixin/output/smartctl-overview.json`](https://github.com/clementduveau/smartctl_exporter/blob/3d67aa1dff9cc57a322fe73795b7435030023018/mixin/output/smartctl-overview.json),
commit `3d67aa1dff9cc57a322fe73795b7435030023018`.
Upstream SHA-256:
`daf5d288a1ece45629e0d6d6750d93a06943ca215312441989bf5f465e1f14f9`.
`LICENSE.smart-dashboard` preserves the license. This is a pinned community
proposal, not a released official mixin. Only its dashboard is imported;
upstream generic alerts are not installed.

Local bindings use UID `smart-disks`, GrafanaDashboard `smart-disks`, ConfigMap
`smart-disks-dashboard`, tags `smartctl`, `storage`, `hardware`, datasource
`victoriametrics`, and collection
cluster/instance matchers on every native selector. Two query
corrections preserve no-data behavior: command flags no longer invent success
when metrics are absent, and failed-disk count handles all-failed inputs. The
command-flags card is explicitly diagnostic, not a failed-health indicator.
The decorative header is replaced by a native per-disk command-diagnostics
table; the other panel positions, native metric names and units are retained.
Command cards use the latest reading rather than a maximum over the dashboard
time range. NVMe/wear panels without
a matching producer remain empty. SAS errors are available through native
Explore queries and alerts; the inherited overview has no dedicated SAS error
panel. The host dashboard remains the capacity/I/O view. Neither dashboard
provides Grafana user-access isolation.

The new address is `/d/smart-disks`. Flux owns the resource rename and the
Grafana Operator's native finalizer removes the old dashboard by its stored UID.
No old UID alias or duplicate dashboard is retained.

### Additional SMART hosts

The shared dashboard discovers `job="smartctl"` targets from `up` in the selected
collection cluster. Its **Host** selector supports one, several, or all instances.
Grafana's native named capture groups display the target's `node` name while
retaining its native `instance` endpoint as the selection value. The options
query does not depend on its own selection. A failed scrape remains selectable.

Each new physical host needs its own authorized exporter and owner-local
ServiceMonitor or ScrapeConfig. Set `job="smartctl"`, a unique readable `node`
host name, and a distinct native `instance`; VMAgent supplies the existing global
collection labels. Keep the host's metrics authentication and transport policy.
Do not attach a host name globally to a multi-target scrape job: labels must
identify the individual target. The OMV Stack and mTLS endpoint remain specific
to OMV; this dashboard change does not install exporters on other machines.

Kubernetes nodes use the [owner-local SMART DaemonSet](../../../../../../observability/controllers/base/smartctl-exporter/README.md).
It selects the existing opt-in node label and joins ambient for authenticated
Pod metrics collection, preserving this dashboard's native target contract.

Plots retain host and instance identity when aggregating identical disk names.
Legends use **host / disk**; tables show the host name instead of repeating the
metrics address. Command flags and failed-disk counts are separate per host.
The shared health rules apply automatically to new SMART targets. Discovery
absence and expected disk counts require that host's actual inventory; the
OMV-specific seven-disk check must not be copied as a universal expectation.
