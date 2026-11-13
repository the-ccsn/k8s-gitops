# OMV metrics

These complete Portainer Stacks prepare authenticated metrics for SeaweedFS
4.48, node-exporter 1.10.2 host telemetry and smartctl-exporter 0.14.0 disk health. They are external-host configuration,
not Kustomize resources. Both keep startup commands and NGINX configuration
inline; no new startup script or custom image is required. Existing data mounts, disk guards and S3 authentication-file
references come from the reviewed OMV configuration on 2026-10-31.

| Stack | Metrics listener | Native backends |
| --- | --- | --- |
| `seaweedfs.yaml` | current management-interface IPv4 address, port 9443; queried as `openmediavault.local` | master, filer, ordinary S3, six volume servers, node-exporter and smartctl-exporter |
| `seaweedfs-s3-exposure.yaml` | current `lan0` IPv4 address, port 9443; queried as `s3.ccsn.dev` | direct S3 |

The existing gateways use different network namespaces. Each therefore has one
NGINX frontend; the direct frontend shares the S3 service's namespace. The
desired native listeners bind only to `127.0.0.1` in their respective namespaces.
Existing processes can use the maintenance-safe rollout below. The public S3
HTTP/HTTPS listeners and their dual-stack configuration remain independent.
The core frontend reads the current address of `METRICS_INTERFACE` (`enp6s18`),
OMV's existing management interface. It does not bind addresses returned by the
host's own-name resolver, which can include unscoped IPv6 link-local addresses.
Both frontends require the dedicated CA and exact client subject
`CN=vmagent-seaweedfs-metrics`. Only GET requests to the enumerated metrics paths
are proxied; arbitrary targets, query strings and application endpoints are not
exposed. Client headers and bodies are not forwarded. Each new frontend has a
0.25 CPU / 128 MiB hard limit and a 16 MiB temporary filesystem.

## Host telemetry addition

`node-exporter` uses the official digest-pinned image, a read-only host root
mounted at `/host`, and the host PID/network namespaces. It runs as nobody with
all capabilities dropped, a read-only container root and a 0.25 CPU / 128 MiB
hard limit. The native HTTP listener binds only to `127.0.0.1:9100`; the existing
authenticated frontend exposes exactly `/node/metrics`. It does not expose the
exporter's landing page or add a public port. No additional certificate or
startup script is needed.

Default native collectors provide CPU, memory, filesystem capacity/inodes,
disk I/O, pressure and network metrics. Disk properties use the host's udev data
under `/host/run/udev/data`. Collectors for absent subsystems can report no data;
this does not establish a failure of the core host metrics. `timex` is disabled
to avoid requesting the host-clock capability, so this addition does not provide timex-based NTP
synchronization alerts. SMART and physical RAID-member health come from the
separate exporter below, not from node-exporter's filesystem or I/O counters.

The Stack does not itself create a Kubernetes scrape target. Publish the
[host collection resources](../monitoring/README.md#omv-host-metrics) only after
the external endpoint passes acceptance. Use this order after reviewing the
current maintenance Stack:

1. Validate the complete Stack with `docker compose -f seaweedfs.yaml config --quiet`.
   Preserve the other task's data-service definitions and record their IDs/start
   times before making any named-service change.
2. Start only `node-exporter` and refresh only the core `metrics` frontend with
   `docker compose -f seaweedfs.yaml up -d --no-deps node-exporter metrics`.
   This change requires no master, filer, S3 or volume restart. Avoid a whole-Stack
   update while independent volume maintenance is running.
3. Verify `/node/metrics` with the existing vmagent client identity, rejection
   without that identity, and continued operation of all ten SeaweedFS routes.
   Confirm the native host metrics describe OMV and its real filesystems, and
   that port 9100 cannot be reached off-host.
4. Only then publish the host ScrapeConfig using `job="node-exporter"` and
   `node="omv"`, with the existing native node alerts and the
   **OMV / Node Exporter Full** dashboard. The Kubernetes node dashboard is not
   an OMV host view. Include target-absence coverage for this known external
   host; the other three exporters must not hide its loss.

The container flags and mount arrangement follow the pinned
[upstream deployment guide](https://github.com/prometheus/node_exporter/blob/v1.10.2/README.md#docker).

## Physical-disk SMART addition

This addition is prepared for a separate external-host rollout. It starts only
`smartctl-exporter` and refreshes only `metrics`; it does not update any
SeaweedFS data service. Keep all commands in this complete Stack. No startup
script, custom image, new certificate or firewall change is required.

On 2026-11-09, read-only `smartctl` checks confirmed seven unique physical disks
behind OMV's passed-through MegaRAID controller: three ATA and four SAS devices.
Their direct by-id identities match the seven controller-member serials. Native
automatic `by-id` discovery and an ATA/physical-SCSI filter select them once,
excluding the two QEMU disks and duplicate `/dev/bus/*` controller paths. This
does not depend on `/dev/sdX` ordering or a manually maintained serial list.
Rescanning runs every ten minutes and SMART reads every minute. Standby checks
avoid waking ATA disks for routine reads; hardware/controller behavior still
needs deployment verification. No self-test or SMART-setting command is used.

The official image is pinned to 0.14.0 and its multi-platform digest. Replaying
the seven native disk results through official 0.15.0 reproduced HTTP 500 from
missing SAS metric descriptors; 0.14.0 returned HTTP 200 with all seven health
series and four SAS grown-defect/read/write error series. See upstream
[descriptor fix #397](https://github.com/prometheus-community/smartctl_exporter/pull/397).
Use a later official release only after the same SAS fixture passes; no local
patch is carried.

The exporter uses root with only `SYS_RAWIO`, a read-only `/dev` mount, and a
device-cgroup read rule for Linux SCSI/SATA block major 8. It is not privileged
and receives no controller character-device, NVMe, host-PID or Docker-socket
access. The mount is read-only, but `SYS_RAWIO` permits storage ioctls: this is a
trusted host-monitoring process, not a security boundary against malicious disk
commands. Its official smartctl arguments perform reads only. Host and actual
container reads passed with all other capabilities removed. Its hard budget is
0.25 CPU / 128 MiB, without swap. The image's native `wget` health-check binary
is `/usr/bin/wget`.

Native HTTP binds only to `127.0.0.1:9633`. The existing mTLS frontend exposes
exactly `/smart/metrics`, using the existing authorized vmagent identity and
normal hostname validation. All existing frontend restrictions still apply.

The external-host barrier passed on 2026-11-10: seven unique healthy disks,
four SAS defect/read/write series, 471 samples, authenticated HTTPS success for
the new route and all eleven existing SeaweedFS/host routes, and rejection of
missing client certificates, extra paths, query strings and off-host port 9633.
Both monitoring containers are healthy. Data-service container identities and
start times were preserved. Acceptance used a temporary native vmagent process
with all samples dropped; it did not activate continuous SMART collection or
publish Kubernetes resources. Those remain a separate GitOps change.

Roll out in two phases, keeping source publication separate from activation:

1. Publish the Stack preparation independently of the new Kubernetes SMART
   resources. Compare with the currently maintained OMV Stack and preserve
   every data-service definition. Validate Compose, pull only the pinned
   `smartctl-exporter` image, then use
   `docker compose -f seaweedfs.yaml up -d --no-deps smartctl-exporter metrics`.
   Do not run a whole-Stack update. Record and compare data-service container
   IDs/start times before and after; independent EC maintenance must continue.
2. Verify seven unique native health series and four SAS error/defect series,
   all within the scrape sample limit; check current temperatures, permissions,
   memory and exporter logs. Verify authenticated HTTPS success, rejection
   without the client identity, all eleven pre-existing SeaweedFS/host targets,
   and off-host rejection on port 9633. Only after this barrier publish
   `smart-scrape-config.yaml`, `smart-rules.yaml`, `smart-dashboard.yaml`, its JSON
   and license, and the monitoring Kustomization changes. Then accept the new
   target, rules and dashboard. No suspension flags are needed.

Changing device families or adding another SCSI block major needs a reviewed
discovery/permission change. This configuration does not collect RAID-array,
controller/battery, PSU or fan health. See the
[SMART runbook and native cache limits](../monitoring/README.md#omv-physical-disk-smart).

## Certificates and renewal

`../monitoring/metrics-certificates.yaml` provisions a dedicated namespaced CA,
a 90-day server certificate for `openmediavault.local` and `s3.ccsn.dev`, and a
90-day client certificate. Leaf renewal starts 15 days before expiry. The CA key
and client key stay in `monitoring`; OMV's existing `prod/omv-s3-cert-reader`
identity receives only `get` on `monitoring/seaweedfs-metrics-server-tls`.

The exposure Stack's existing controller runs an inline certificate worker next
to its existing network/DNS/certificate supervision. It reads the existing
`cert-reader.json` at runtime, verifies the API TLS certificate, and fetches only
the server Secret. It verifies the key pair, CA chain, both DNS names and at
least one day of validity before replacing the live PEM. The private server
bundle is mode 0640 in a mode-0750 directory; its CA file is public trust data.
Only the two exactly owned metrics containers receive NGINX test/reload calls.
Client-certificate Secret updates use the native monitoring Operator path.

The controller also detects a network-namespace change after an in-place S3
restart and restarts only the direct metrics frontend to rejoin it. Replacing
the S3 container must update its dependent metrics service in the same Compose
operation; `depends_on.restart` covers Compose-managed changes. An in-place
`lan0` address change requires restarting the metrics service to regenerate its
listener. No runtime code restarts a master, filer, volume or S3 data service for
metrics recovery.

The bootstrap CA lasts ten years and retains its key on routine renewal.
Rekeying that CA is a separate trust-bundle rollover: retain overlapping trust
until both leaf certificates and OMV have adopted the replacement. Do not delete
its Secret to attempt automatic rotation.

## Release order

1. Publish only the certificate resources, narrowly scoped Role/RoleBinding and
   these Stack sources first. Keep the existing ScrapeConfig until the OMV
   endpoints are ready. Wait for both leaf Certificates to become Ready and
   verify the existing identity can get the server Secret but cannot get the
   client or CA Secret. Do not print Secret data.
2. Recompare these Stacks with the current OMV configuration; do not overwrite
   another task's changes. Record container IDs, start times and health for
   master, filer, ordinary S3 and all six volume servers. Update only exposure
   `controller` with `--no-deps`, verify certificate sync, and start only core
   `metrics` with `--no-deps`. Recheck direct S3's start time after the controller
   update: its existing supervision can also restart the gateway. Count such a
   restart against any approved budget before scheduling its metrics update.
   Existing wildcard native listeners also accept
   loopback connections, so these nine routes need no data-service restart.
   Update exposure `s3` and its dependent `metrics` together; the new direct-S3
   metrics port requires that gateway to restart and can briefly interrupt
   direct S3 requests. Do not restart master, filer, ordinary S3 or any volume.
   A full-stack Portainer update can recreate them and is unsuitable while
   maintenance is running. Keep the original maintenance Stack source intact;
   named-service updates may use separate copies of these complete Stack YAMLs.
3. Verify all ten authenticated routes and rejection without a client certificate
   or with a different subject. Publish the HTTPS ScrapeConfig and alert changes
   separately, then verify ten `up == 1` targets and effective client TLS assets.
   Keep the existing HTTP targets working until HTTPS collection has been
   adopted. No suspension fields are required.
4. Close the native-metrics bypass using the persistent OMV rules below. Verify
   rejection from outside OMV and successful local access, and recheck that the
   recorded data-service container IDs/start times are unchanged. Future planned
   service updates use the desired loopback settings; this release does not
   require waiting for the independently owned EC/volume maintenance to end.
5. Accept per-volume disk/QPS and latency panels, distinct S3 instances, alert
   evaluation and a leaf renewal. Direct requests must use the internal DNS
   answer for `s3.ccsn.dev`; no fixed address or `s3.319.ccsn.dev` target is needed.

## Native metrics access during maintenance

The mTLS frontend alone does not protect native ports that still listen on the
LAN. Persist two matching rules through OMV's existing firewall configuration,
one for each IP family:

| Field | Value |
| --- | --- |
| Family | `inet` / `inet6` |
| Chain / action / protocol | `INPUT` / `REJECT` / `tcp` |
| Source, destination, source port, destination port | Empty |
| Extra options | `! -i lo -m multiport --dports 9327,9328,9329,9401,9402,9403,9404,9405,9406 --reject-with tcp-reset` |
| Comment | `SeaweedFS native metrics: loopback only` |

Apply only these two rules to the running firewall after HTTPS collection works.
Place them before broader allow rules; preserve every unrelated rule. The
installed OMV firewall template flushes INPUT/OUTPUT during a full reload, so
do not restart the firewall or run its whole deployment during maintenance.
Persist the configuration and generate only its managed script without invoking
the service restart. Neither this restriction nor the loopback settings affect
the mTLS port `9443`, application ports, volume data, or EC maintenance ports.
Check both IPv4 and IPv6, including a Docker bridge source, and verify that the
rules survive a subsequent scheduled firewall refresh or host reboot.

## Stack validation

```sh
docker compose -f seaweedfs.yaml config --quiet
docker compose -f seaweedfs-s3-exposure.yaml config --quiet
```

Each metrics service writes its inline NGINX template to its bounded `/tmp`
filesystem. This works with a read-only root filesystem; Compose's inline
`configs.content` delivery does not support these read-only services. `$$`
preserves container-shell and NGINX variables through Compose interpolation;
runtime `envsubst` expands only the listener address. The existing custom network
controller image and its credentials remain external dependencies, not included
as image layers or literal credentials in these files.

References: [Compose inline configs](https://docs.docker.com/reference/compose-file/configs/),
[NGINX client verification](https://nginx.org/en/docs/http/ngx_http_ssl_module.html#ssl_verify_client),
[cert-manager CA lifecycle](https://cert-manager.io/docs/configuration/ca/).
