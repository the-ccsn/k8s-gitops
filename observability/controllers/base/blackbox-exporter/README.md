# Blackbox dashboards

The network, HTTP and ICMP dashboard JSON files adapt the community
[`adinhodovic/blackbox-exporter-mixin`](https://github.com/adinhodovic/blackbox-exporter-mixin/blob/7d2b9263d7adae3ec937c8ae0cb6003492616710/dashboards_out/blackbox-exporter.json),
commit `7d2b9263d7adae3ec937c8ae0cb6003492616710`.
Unmodified source SHA-256:
`51794de3f7ca5b619a5e071bcdb61b5f442558f061f1be55123bdd65aa502227`.
`LICENSE.dashboard` preserves the upstream MIT notice.

The existing UIDs `network-availability`, `http-availability` and
`icmp-availability` are updated in place, using `victoriametrics`. Applicable
upstream panel types, positions, value mappings and drilldown links are retained.
The network and HTTP views each contain 18 charts; ICMP contains 11 and omits
HTTP/TLS-only charts and HTTP phase queries. DNS, TLS and bandwidth dashboards
in `availability-dashboards.yaml` are unchanged.

Queries use `k8s_cluster_name`. Per-probe aggregations preserve job, instance,
`probe_path` and `ip_family`, with phase or TLS version where relevant. Two
paths or IP families for the same URL therefore remain separate series, even
when one fails. Automatic series names retain the available identity labels;
drilldown links select the cluster, job and target and show its path/family
variants together. Current-status panels use instant queries. The selected-range
uptime is the fraction of successful recorded samples, bounded by retention;
missing samples do not represent proven availability. The source's fixed 30-day
claim is removed because the backend retains seven days.

Each view derives job options from its native metric family: `probe_success`,
`probe_http_status_code` or `probe_icmp_duration_seconds`. All expands those
actual job options; it deliberately has no `.*` override. Jobs are the probe
collection boundary, so HTTP and ICMP views do not include arbitrary other
probe jobs. Failed HTTP probes with status zero remain selectable. ICMP charts
remain empty until ICMP probes are configured and collected; this dashboard
does not create targets or change network-device access.

When updating, verify the pinned source hash, preserve UIDs, reapply scope and
identity grouping, and validate every query and relevant failure cases. No
recording-rule aliases, collector changes or extra runtime components are needed.
