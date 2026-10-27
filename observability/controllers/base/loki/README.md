# Loki operational dashboard

`dashboard.json` uses Grafana's official Loki **3.6.7** operational dashboard,
matching the deployed binary. Source:
[`production/loki-mixin-compiled/dashboards/loki-operational.json`](https://github.com/grafana/loki/blob/7e1daf3a36f68639a5d06c1ac057a2fcbf0dce40/production/loki-mixin-compiled/dashboards/loki-operational.json),
commit `7e1daf3a36f68639a5d06c1ac057a2fcbf0dce40`.
Unmodified upstream SHA-256:
`cc0f23ff9c573d8db7108602106e09126b4808e257155f24e093b1df226a54ce`.
`LICENSE.dashboard` preserves its AGPL 3.0 license.

The dashboard updates UID `loki` in place and uses `victoriametrics`. Backend
metrics use the selected `k8s_cluster_name`, namespace, native job and Pod from
`loki_build_info`. The namespace is the Loki workload's namespace, not the
namespace of applications whose logs it stores. The source's separate component
job expressions are bound to the actual single-binary job. Server-wide latency is
labelled accordingly; route-specific read/write queries retain their route filters.

Upstream types and positions are retained for applicable sections: main traffic,
ingestion limits, distributor/ingester internals, streams, chunks, queries and S3.
The existing ingested-byte view is retained. Disabled Memcached, Consul, Bigtable,
DynamoDB, GCS, Azure and BoltDB Shipper sections are omitted. Component-separated
log panels are also omitted: one Loki process cannot supply separate component
job identities. The existing Application Logs dashboard and Grafana log tools
remain the views for log content.

CPU reads the selected Pod's `loki` container through native cAdvisor collection;
CPU and Go heap memory each have one process view rather than three component
views of the same process. Restart
counts use the same Pod with kube-state-metrics. Those resource queries retain
the same cluster/namespace scope and their own collector jobs. Unconfigured
Promtail custom bad-word metrics are omitted.

The two upstream histogram recording expressions are expanded directly into
`sum by (...) (rate(loki_request_duration_seconds_bucket[...]))`, with the
original grouping and route filters. No recording-rule aliases or new runtime
rules are installed. The rule definitions are in the same pinned source's
[`production/loki-mixin/recording_rules.libsonnet`](https://github.com/grafana/loki/blob/7e1daf3a36f68639a5d06c1ac057a2fcbf0dce40/production/loki-mixin/recording_rules.libsonnet).
The main Query Latency panel uses seconds, matching its unscaled histogram;
panels that multiply by 1000 retain milliseconds. Ingested bytes use bytes/second.

Internal RPC, inactive error counters and idle request histograms can have no
series in a single-binary deployment. Empty charts do not justify enabling a
service, changing collection or inventing aliases. These bindings change no Loki
storage, ingestion, retention, authentication or application log queries.
When updating, verify the source hash, preserve the UID, reapply topology/scopes,
and check native metrics, histogram units and every query.
