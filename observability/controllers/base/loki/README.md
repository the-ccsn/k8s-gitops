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

## Application log investigation

UID `application-logs` is intentionally project-specific: it follows the installed
OTel resource labels, severity metadata and cross-service correlation fields.
Cluster selection precedes workload namespace, service and Pod; severity and
literal text narrow the recorded logs. Request ID, CF-Ray and Trace ID are
optional, with empty fields retaining all records. Record counts and error share
are based on the selected collected records, not assertions about service health.
No-traffic error share stays undefined rather than being forced healthy.

Severity selection ignores case while retaining the source text. Native
`WARNING`, `ERR` and `CRITICAL` values remain selectable; error views include
`error`, `err`, `critical` and `fatal`, consistent with the existing log rules.
The service count uses workload namespace and service name together, so equal
names in different namespaces remain distinct.

The default one-hour view presents a small overview, severity/service trends and
up to 200 matching records. Error records and cross-service trace lookup are
collapsed. Log details retain metadata and the existing native TraceID link.
Trace lookup applies Request ID / CF-Ray exactly across services; namespace,
service, severity and text constrain logs rather than the whole distributed trace.
The optional Trace ID field filters logs and supplies direct lookup in Explore.
Traces Drilldown supplies the official full trace-analysis interface.

Tempo targets use Grafana 13's native `traceqlSearch` filters with scalar values.
The datasource omits empty filters before constructing TraceQL; no conditional
query-string workaround or custom query service is installed. `tableType: traces`
retains native TraceID links and trace-to-log navigation. Tests of the pinned
frontend query builder cover empty/request/Ray/both combinations. Search returns
first matches in range, not necessarily the newest traces. Missing traces can be
caused by sampling. Source references: Grafana [query interpolation](https://github.com/grafana/grafana/blob/v13.0.1/public/app/plugins/datasource/tempo/SearchTraceQLEditor/utils.ts)
and [filter generation](https://github.com/grafana/grafana/blob/v13.0.1/public/app/plugins/datasource/tempo/language_provider.ts).

## Log-alert evaluation health

`LokiRuleEvaluationErrors` monitors the native
`loki_prometheus_rule_evaluation_failures_total` counter by cluster, namespace
and rule group. Sustained failures are warnings even if the failing log rule
emits no alert. Inspect query syntax, timeouts, ingestion freshness and ruler
logs before interpreting an empty log-alert result as application health.
Cloudflared's owner-local rule ConfigMap uses the existing `loki_rule=1`
sidecar selection in `monitoring`; no additional ruler is deployed.
