# Blackbox investigation dashboards

Network, HTTP, ICMP, DNS and TLS views adapt the community
[`adinhodovic/blackbox-exporter-mixin`](https://github.com/adinhodovic/blackbox-exporter-mixin/blob/7d2b9263d7adae3ec937c8ae0cb6003492616710/dashboards_out/blackbox-exporter.json),
commit `7d2b9263d7adae3ec937c8ae0cb6003492616710`.
Unmodified source SHA-256:
`51794de3f7ca5b619a5e071bcdb61b5f442558f061f1be55123bdd65aa502227`.
`LICENSE.dashboard` preserves the MIT notice. Existing dashboard UIDs and
`victoriametrics` are retained.

| View | Existing UID | Native job-option family |
| --- | --- | --- |
| All probes | `network-availability` | `probe_success` |
| HTTP | `http-availability` | `probe_http_status_code` |
| ICMP | `icmp-availability` | `probe_icmp_duration_seconds` |
| DNS | `dns-availability` | `probe_dns_query_succeeded` |
| TLS | `tls-certificates` | `probe_ssl_earliest_cert_expiry` |

The overview keeps recorded results, failed probes/scrapes, success history and
probe duration visible. Protocol details are collapsed, preserving applicable
upstream charts and relative layout. DNS replaces HTTP/ICMP phases with native
DNS phases and retains answer counts. ICMP omits HTTP/TLS-only charts. TLS retains
its certificate, version and HTTP detail views. A separate observed IP protocol
stat distinguishes the actual IPv4/IPv6 result from the configured family policy.

Selectors use `k8s_cluster_name`, path, IP-family policy, job and target. Per-probe
aggregations preserve job, target, `probe_path` and `ip_family`; phase or TLS
version is added where relevant. A successful family/path cannot conceal another
family's failure. Path/family All is deliberately `.*` so unlabelled probes remain
visible. Job/target All expands actual options instead of matching arbitrary
jobs. Links retain the cluster, time and relevant selectors.

Probe tiles open the clicked job, target, path and family with the current time
range. Links back to All probes retain job and target; the TLS-to-HTTP link also
retains those compatible selections. Switching to an unrelated protocol view
resets job and target so incompatible options cannot hide its targets.

Path and family selectors include a native **Not set** option with an empty
value. It selects probes without that label and remains selected when variable
options refresh. **All** continues to include labelled and unlabelled probes.

A failed probe (`probe_success=0`) is distinct from a scrape failure (`up=0`).
The failure list gives scrape failure precedence when both exist for the same
identity. Result tiles show the last recorded probe result; missing samples are
not proof of health. Selected-range uptime describes successful recorded samples,
limited by retention, rather than a fixed 30-day claim. Current-status queries
are instant; histories remain range queries. ICMP/SNMP views can remain empty
until their targets are configured. This import does not install device agents,
change credentials or create targets.
Plain HTTP targets report a zero SSL share; absent HTTP samples remain no data.

## Host and SNMP bandwidth

`network-bandwidth.json` uses the network section of
[dotdc's pinned node dashboard](https://github.com/dotdc/grafana-dashboards-kubernetes/blob/e4faf59e017a18e1b06fa64f11623bef15ce7507/dashboards/k8s-views-nodes.json),
commit `e4faf59e017a18e1b06fa64f11623bef15ce7507`.
Unmodified source SHA-256:
`4a11656116232acc2b1fdf77261e7c814af88c52a5559039db56e84b88772be7`.
`LICENSE.network-dashboard` preserves Apache 2.0.

The existing UID is retained. Four native upstream traffic/error/drop charts
preserve their relative layout, with two optional existing SNMP directions.
Host selection uses native `nodename`, so external node exporters do not need
a Kubernetes `node` label. An endpoint and interface selector retain native
identities. Host traffic is bytes/second, packets are packets/second; mirrored
transmit series retain the upstream negative plotting convention. SNMP octet
counters are converted to bits/second and retain `device_id` / `ifName`.
The collecting Kubernetes cluster is not a claim that an external device is a
cluster member.
Query intervals use the datasource default instead of an undefined resolution
variable.

For updates, verify source hashes and preserve UIDs, scopes and probe identities.
Test same-URL paths/families, scrape versus probe failure, unlabelled probes,
expired certificates, actual IP protocol and native units. No recording-rule
aliases or additional runtime components are needed.
