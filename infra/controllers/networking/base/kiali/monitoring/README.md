# Kiali internal-metrics dashboard

The seven charts are rendered from Kiali **2.24.0**'s official built-in
[`kiali` dashboard definition](https://github.com/kiali/kiali/blob/52141136c5ebf53bd9f9fee4a356e80e662f42d9/config/dashboards/dashboards.go),
commit `52141136c5ebf53bd9f9fee4a356e80e662f42d9`.
Full unmodified source SHA-256: `0d88fe24b3f903717dbfad991dbce3c978cb643f0d9864f9e44042e22413b81c`.
`LICENSE.dashboard` preserves Apache 2.0. This is a native Grafana rendering of
the upstream MonitoringDashboard definition, not an upstream Grafana JSON file.

UID `kiali` is retained. The existing scrape-health chart plus seven upstream
charts give eight charts: API hit rate, API duration/failures, graph duration,
cache hits/misses and tracing processing duration. Chart order, relative widths,
metric names/types, units and grouping come from that definition. Histograms
show p50/p95/p99 in seconds; raw counters retain their cumulative meaning.
API routes remain `route`, rather than a nonexistent HTTP status label.

Cluster, Kiali server namespace and job come from native Kiali metrics. Shared
metric families therefore do not select another application's process. A counter
or histogram can be absent until used; absence is not replaced by invented data.
This changes the Grafana dashboard only. Kiali login, Kubernetes permissions and
its server/Operator configuration are outside this component.

For updates, verify the source hash and built-in definition, preserve the UID,
and check the deployed producer's groups, units, native queries and datasource.
