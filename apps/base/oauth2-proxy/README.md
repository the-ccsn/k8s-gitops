# Shared OAuth2 Gateway

The production overlay installs this release and its monitoring resources in
`prod`.

## Native metrics

Chart 10.6.0 / OAuth2 Proxy 7.15.2 exposes a separate HTTP metrics listener on
port `44180`. The HelmRelease makes that existing default explicit and leaves
the chart's ServiceMonitor disabled. Owner-local monitoring declares one
ServiceMonitor; VictoriaMetrics Operator converts it for the existing vmagent.
The target uses `job="oauth2-proxy"`, native `namespace` / `pod` / `instance`
labels and the global `k8s_cluster_name` label.

Production already uses Istio ambient. The workload AuthorizationPolicy permits
the vmagent ServiceAccount to reach the metrics port and leaves other ports
under their existing policy. Collection uses the mesh identity, without adding
credentials, an external metrics route or a separate proxy.

Native application metrics are:

- `oauth2_proxy_requests_total{code}`: requests by HTTP status.
- `oauth2_proxy_requests_in_flight`: concurrent requests.
- `oauth2_proxy_response_duration_seconds_*{method}`: request latency in seconds.

These families have no user, token, URL or request-ID labels. Go/process metrics
describe the proxy process; `promhttp_*` describes the metrics handler. Health
requests handled before application instrumentation are excluded. Redirects and
authorization denials are normal traffic; HTTP status counts do not establish
login success, active sessions or downstream application availability.

The existing `VMAgentScrapeErrors` alert covers scrape failures. This integration
adds no notification route or duplicate scrape-failure rule.

Use the VictoriaMetrics datasource in Explore for these scoped queries:

```promql
sum by (code) (rate(oauth2_proxy_requests_total{k8s_cluster_name="kubevirt-cluster-319",namespace="prod",job="oauth2-proxy"}[5m]))

histogram_quantile(0.95, sum by (le, method) (rate(oauth2_proxy_response_duration_seconds_bucket{k8s_cluster_name="kubevirt-cluster-319",namespace="prod",job="oauth2-proxy"}[5m])))

sum(oauth2_proxy_requests_in_flight{k8s_cluster_name="kubevirt-cluster-319",namespace="prod",job="oauth2-proxy"})
```

No dedicated dashboard is provisioned by this integration. Existing
**Application Logs** provides the log view; select workload namespace `prod`.

## Traces and logs

The pinned official binary has no configurable native OTLP producer. Istio's
HTTP-visible proxy spans and the existing container-log pipeline remain the
available signals. Native request IDs are separate from trace IDs and do not
correlate an entire login redirect sequence. This integration does not alter
logging formats, identity claims, login/session settings or authentication rules.

The metric contract follows the pinned
[producer definitions](https://github.com/oauth2-proxy/oauth2-proxy/blob/v7.15.2/pkg/middleware/metrics.go)
and [chart defaults](https://github.com/oauth2-proxy/manifests/blob/oauth2-proxy-10.6.0/helm/oauth2-proxy/values.yaml).
