# Alert coverage and response

Rules stay with their component owners and use the existing VictoriaMetrics,
Loki and Alertmanager path. No new alert engine, exporter or restart controller
is introduced. Warning and critical notifications go to Telegram and WeCom;
info remains queryable without chat delivery. Do not silence a problem instead
of checking the underlying expression and telemetry freshness.

## Sources and local adaptations

- Host rules follow the [node_exporter 1.10.2 mixin](https://github.com/prometheus/node_exporter/blob/v1.10.2/docs/node-mixin/alerts/alerts.libsonnet).
  Local adaptations use `k8s_cluster_name`/`node`, deduplicate filesystem bind
  mounts by device, and exclude Longhorn `VIRTUAL-DISK` devices from physical
  disk latency/queue checks. The filesystem warning/critical free-space
  thresholds are 15%/5%; the 24-hour forecast uses six hours of history and
  requires less than 40% free. This includes root and Longhorn data filesystems.
  NixOS tmpfs root is included explicitly; other ephemeral tmpfs mounts are excluded.
- Workload rules follow the [kubernetes-mixin](https://github.com/kubernetes-monitoring/kubernetes-mixin).
  Terminal Job failure is distinct from a retried Pod; a later successful run
  of the same CronJob suppresses its old failed Job history. Suspended CronJobs are
  excluded from overdue alerts. CPU throttling requires both more than 25%
  throttled periods and more than 80% CPU-limit utilization for 15 minutes.
- Longhorn metrics follow [1.11.2 producer definitions](https://longhorn.io/docs/1.11.2/monitoring/metrics/).
  Backup state 4 is an error; state 2 is in progress. Volume states are one-hot
  series and require a value of 1. Disk capacity and schedulability are distinct
  from free space inside a PVC. The 75% disk utilization warning corresponds to
  the deployed 25% minimum-free scheduling policy; reassess together if that
  policy changes. Backup age applies only to PVs using `longhorn-backup` that
  are older than 48 hours, matching their daily recurring backup group.
- PostgreSQL rules adapt [CNPG's native examples](https://github.com/cloudnative-pg/cloudnative-pg/blob/main/docs/src/samples/monitoring/alerts.yaml).
  They retain `cnpg_cluster_name`, aggregate connection state before comparing
  to max_connections, and use increases rather than lifetime deadlock counts.
  The native backup timestamp exporter is zero with the deployed plugin despite
  successful Backup resources. The existing kube-state-metrics therefore reads
  Backup/ScheduledBackup metadata and status with list/watch RBAC. Longhorn
  Backup metadata supplies the timestamp needed to suppress stale failures. Its
  [native CR-state implementation](https://github.com/kubernetes/kube-state-metrics/blob/v2.18.0/docs/metrics/extend/customresourcestate-metrics.md)
  parses RFC3339 times. No credentials or backup content become metrics.
  CRD discovery caches the full schemas, so kube-state-metrics requests 256 MiB
  and is limited to 512 MiB. The former 128 MiB limit was insufficient with the
  deployed CRDs and caused repeated OOM kills.
- Dragonfly 1.40.1 exposes native `dragonfly_*` metrics on admin port 9999.
  One PodMonitor discovers labeled instances across namespaces. Root-namespace
  policy rejects unauthenticated admin access. Owner-local policies permit only
  vmagent, the native Operator and the instance's dedicated peer ServiceAccount.
  NetworkPolicies admit their HBONE transport; other application ports retain
  their existing policy. The Operator Pod is enrolled in ambient for its native
  admin calls. Dedicated instance identities require a rolling update of all
  three single-replica caches, which can briefly interrupt Redis connections.
  Production is namespace-enrolled; Harbor's cache is explicitly Pod-enrolled.
- SeaweedFS 4.48 metrics follow the [pinned producer](https://github.com/seaweedfs/seaweedfs/blob/530be3e37337488ecc34d58441e0bc476e121c93/weed/stats/metrics.go).
  Bucket read-only gauges use max, avoiding duplicate component reports. S3
  latency uses only the S3-gateway histogram and preserves request type.
- Loki/Tempo query alerts use the deployed HTTP histogram and counter labels.
  Query 5xx needs more than 5% errors and at least three errors per five-minute
  window, sustained for five minutes. Query p95 above ten seconds for 15 minutes
  and Tempo storage queue utilization above 80% for five minutes are separate
  signals. No traffic yields no latency/error alert; target absence is covered
  independently.

## Node storage

Use the node and device in the alert to inspect filesystem capacity, inode use,
mounts and kernel errors. A device-level alert intentionally combines NixOS
bind/subvolume aliases. Read-only alerts require all selected aliases of a
filesystem device to be read-only, avoiding intentional read-only bind mounts.
Check logs, images, snapshots and volume ownership before choosing cleanup.
This runbook does not authorize deleting data.

High throughput alone is not a fault. Check average read/write latency,
weighted I/O time (outstanding work), and full I/O pressure together. Latency
requires more than one operation per second and sustained averages above
50 ms; physical queue saturation requires more than ten outstanding operations
for 15 minutes. Keep HDD and SSD behavior in mind. Virtual Longhorn device
statistics remain available but do not generate duplicate physical-disk alerts.

Dragonfly uses its native epoll backend. Its io_uring network waits can be
[accounted as I/O wait](https://github.com/dragonflydb/dragonfly/issues/7375)
while disks are nearly idle. This produced near-100% container I/O pressure and
a node alert in this cluster. The backend choice preserves the pressure alert
and its threshold; it does not exclude Dragonfly from monitoring. It gives up
io_uring-specific optimizations; recheck application latency after rollout.

## Node resources

Compare MemAvailable, CPU modes, load per CPU and workload limits. Non-idle CPU
includes I/O wait; increasing a CPU limit does not fix slow disks. Clock offsets
and synchronization failures can affect TLS and distributed request timing.

## Hardware

Use the sensor's own critical threshold for temperature. Corrected memory
errors warn on repeated events; uncorrectable errors are critical. Longhorn
native disk-health metrics cover only disks for which it reports health. Standard
ATA pending/uncorrectable sector IDs 197/198 and increases of
Reallocated_Sector_Ct (ID 5) are monitored only when native Longhorn attributes
are available. Vendor-specific raw values are not interpreted as these counters.
A healthy RAID virtual disk does not prove its member disks are healthy.

Standalone SMART/NVMe attributes, RAID controller/battery status, fans, PSU and
UPS are not comprehensively collected. OMV has SeaweedFS metrics and transport
probing, but no active node-exporter/SMART metrics were found during this audit.
Adding empty metric selectors would not fill these gaps. Device-side exporter
and hardware visibility must be confirmed before claiming that coverage.

## Longhorn

Check disk Ready/schedulable conditions, actual free bytes, reservations, tags
and volume state. A nearly empty PVC can still fail replica scheduling when
its backing disk's budget is exhausted. Detached unused volumes are normal;
only sustained attaching state alerts. Inspect backup state and latest success
before a retry; never remove a Backup or Volume CR to make an alert disappear.
A later completed CNPG backup clears its earlier failure alert. Longhorn backup
failure alerts compare Backup creation time to the current volume's last
successful backup; old errors for removed volumes do not alert.

## Workloads

Restart and OOM alerts use VictoriaMetrics' `increase_prometheus` so a newly
discovered kube-state-metrics target does not count historical restarts as new
events. Real counter increases remain alertable; thresholds are unchanged.

Inspect scheduling events, image-pull/config errors and PVC conditions. Job
alerts use the terminal failed condition. Retained failed history for a CronJob
clears after a newer successful run; standalone failed Jobs remain visible.
CronJob overdue alerts allow an hour
past next_schedule_time, then require another 15 minutes; suspended schedules
are excluded. The cluster overlay sets kube-state-metrics TZ=Asia/Shanghai to
match all three K3s nodes/controllers for CronJobs without spec.timeZone.
Explicit per-CronJob timezones still take precedence; no workload schedule is
changed. An intentionally long-running workload may need a component
policy; do not add a global exclusion to suppress one workload.

## PostgreSQL

Inspect the identified namespace/cluster/Pod, active connections, transaction
age, locks, WAL archiving and standby streaming. Backups warn when an enabled
schedule has no completed Backup in 36 hours; new schedules receive the same
initial grace. A failed attempt alerts only until a later success exists.
Unfinished Backup resources older than two hours alert separately. Backup
metrics need both the Kubernetes watch and kube-state-metrics scrape to work.

These checks do not prove restores. They do not require a backup for clusters
without an enabled ScheduledBackup, and do not reinterpret the generic `cluster`
label as PostgreSQL cluster identity.

## Network

Inspect interface error ratios, traffic, conntrack capacity, CoreDNS SERVFAIL
and latency. Expected NXDOMAIN answers are not server failures. Avoid restarting
network components before identifying routing, DNS or upstream issues. API
latency excludes long-lived WATCH/CONNECT requests.

## Control plane

API server errors and latency complement existing target-down rules. K3s API
server etcd-client metrics are not equivalent to independent etcd server
health. Raft quorum, backend quota and server WAL/fsync alerts remain pending
secure access to actual etcd server metrics. No guessed endpoint is added.

## Dragonfly

Check Pod exec readiness (authenticated Redis PING), native metric scrape,
maxmemory, connected clients and snapshot failures. Metrics availability alone
does not prove Redis commands work. Logto cache-mode eviction may be expected;
there is no blanket eviction alarm. Memory warnings compare to native maxmemory,
not the container's RSS limit. The metric port shares the admin listener, so
keep its mesh identity restriction, native Operator/peer exceptions and HBONE
NetworkPolicy admission together. Instance ServiceAccounts have no Kubernetes
RBAC grant and do not automount API tokens. The namespace ambient setup alone
is not a substitute for the per-instance admin identity policy.
Harbor's namespace is not enrolled in ambient; its Dragonfly Pod must carry
`istio.io/dataplane-mode: ambient` to use the authenticated metrics path.
The cache NetworkPolicy must also admit same-namespace clients on HBONE port
15008; allowing only the original Redis port 6379 blocks mesh clients. This
transport permission does not grant access to the identity-restricted admin
port 9999 or remove native Redis authentication.

## Egress

The previously inactive fetch-nodes rules now use PrometheusRule plus the
existing Loki rule ConfigMap mechanism. Init restarts warn; zero Ready proxy
replicas are critical. A fallback-cache message warns while cached proxy
service may still work. Inspect upstream retrieval without logging subscription
URLs or credentials. These alerts do not prove every external destination works;
no synthetic CONNECT request, fake trace or new proxy is introduced.

## SeaweedFS

Check bucket read-only state, storage I/O/read/write failures and latency by
request type alongside allocation and replication alerts. Existing component
listeners can report overlapping counters; a positive I/O-error alert identifies
the host rather than claiming an exact failed-operation count. S3 transport
probing accepts a private-root 403; it does not prove signed bucket permissions,
object retention, backup or recovery.

## Telemetry

For query errors, inspect the exact route/status, storage read failures and
query queues before raising concurrency. For Tempo's block fan-out, pending
queue capacity is separate from worker concurrency. The queue alert is a
saturation warning, not a guarantee every large admission batch fits. Distinguish
failed queries from stopped collection and failed persistence.

## Triage

1. Confirm the alert's cluster/resource labels and fresh source samples.
2. Inspect the linked component dashboard and corresponding rule expression.
3. Distinguish a producer failure, a discovery/scrape failure, and an evaluator
   failure. Discrete reload, listener-accept and storage I/O errors use a one-minute
   hold within their five-minute counter window. Several counters are created
   only after activity; their absence is
   not a proven healthy state.
4. Verify recovery in the underlying signal and evaluator, not just chat.

Critical-over-warning inhibition includes device, disk, filesystem type,
volume, bucket and backup identities so one failing resource does not hide a
warning on another. This change does not create silences or send test alerts.
Independent off-cluster dead-man monitoring remains outside this batch.
