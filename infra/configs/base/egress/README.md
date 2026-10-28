# Egress observability

The existing Collector, Loki, VictoriaMetrics and Tempo handle this namespace.
The proxy topology, TLS passthrough, CONNECT routing and authorization stay under
their existing owners. No additional exporter or proxy is required.

## Coverage

| Layer | Available signal | Boundary |
| --- | --- | --- |
| Instrumented application HTTP client | Native application spans in Tempo | Requires the application's SDK; encrypted forwarding preserves its bytes but adds no proxy spans |
| Egress waypoint | TCP connection logs and native Istio/Envoy metrics; HTTP spans when HTTP is visible | HTTPS, SSH and explicit CONNECT listeners remain opaque TCP |
| sing-box | Native connection-context logs in Loki | Version 1.13.12 has no OTLP exporter or distributed trace-context integration |
| Proxy management UI | Existing ingress HTTP tracing | The headless Clash API bypasses the waypoint; UI traces do not describe forwarded Internet requests |

The ServiceEntry-attached routes use `egress-system/waypoint`. The separately
declared `https-egress-gateway` currently has no authored route attachments;
it is covered by the same logging policy, without adding traffic to it.
Explicit or non-mesh clients are not guaranteed to traverse the waypoint.

The scoped Telemetry selects `egress-json` with an unconditional logging filter.
The mesh's HTTP error/sampled-header predicate cannot retain ordinary TCP
sessions. Other namespaces retain their existing logging policies. Genuine
HTTP spans inherit the existing OpenTelemetry provider and one-percent sampling,
with `istio.proxy.role=egress`; TCP logs have no trace/span context.

Connection records contain start time, duration, byte counts, response flags,
socket addresses, upstream cluster, optional SNI and transport failure details.
Default TCP records arrive at connection close; a long-lived or multiplexed
tunnel is not one HTTP request. Its duration is not application request latency.
The configured formatter excludes HTTP query strings, headers and payloads.
Addresses can describe a proxy or HBONE hop rather than the ultimate endpoint.

## Follow a proxy connection

From **Observability Platform**, open **Egress logs** or **Egress connections**.
Both links retain the cluster and time range. The log link resets unrelated
request, Ray, trace and text filters. **Application Logs** also links to the
egress waypoint's existing Gateway API view.

In **Application Logs**, select `egress-system`, a Pod and a narrow time range,
then inspect the structured metadata. In Explore, for example:

```logql
{k8s_namespace_name="egress-system", k8s_container_name="sing-box", k8s_pod_name="proxy-engine-0"}
  | singbox_connection_id="1234567890"
```

`singbox.connection.id` is the native random uint32 context ID, retained as a
string; zero is valid. Scope it to Pod/container lifetime and time. IDs can
collide, and HTTP keep-alive requests can share one context. The separate Clash
connection UUID and Envoy connection ID are unrelated. None is an OTLP Trace ID.

`singbox.connection.age_text` preserves the native formatted context age. It is
not a completed connection duration. This version prints hundredths without
zero padding: `1.5s` can mean 1.05 seconds. Do not convert it into a latency
metric. DNS messages share an ID only when they retain that context; background
work can lack one. The current INFO level does not log every successful close.

The CLI disables ANSI colors for stable parsing. Ordinary log bodies and levels
remain intact. The Collector removes known HTTP authentication-error tails and
full schemed HTTP/WebSocket/SOCKS URLs from sing-box bodies before Loki export:
the native producer can include supplied credentials or URL queries there.
This scoped treatment does not sanitize previously stored logs or the original
container files, and it is not a claim that arbitrary future log formats are safe.
Connection IDs remain structured metadata, without new metric or index labels.

For waypoint records, use:

```logql
{k8s_namespace_name="egress-system", k8s_container_name="istio-proxy"}
  | istio_proxy_role="egress"
```

`envoy.connection.id` is scoped to the emitting proxy. Compare the actual
adjacent socket endpoints, SNI and overlapping time windows with sing-box logs.
NAT, HBONE, retries and connection reuse prevent a universal exact join. A
nearby connection is diagnostic evidence, not a verified child span.

In **Gateway API** select namespace `egress-system` and gateway `waypoint` for
the existing TCP traffic and Envoy metrics. HTTP panels can be empty. Avoid
adding together source, destination and waypoint observations of the same flow.
The existing PodMonitors already cover these proxies; no duplicate scrape is
needed.

For genuine HTTP-visible egress spans, search Tempo with:

```traceql
{ resource.k8s.namespace.name = "egress-system" && span.istio.proxy.role = "egress" }
```

This search does not discover encrypted requests inside a TCP tunnel. Follow an
instrumented application's client span for that request, then inspect transport
logs over the same time range. Flux event traces describe reconciliation events,
not the source-controller's HTTP transport. No synthetic spans or compatibility
aliases bridge these distinct signals.

## Source contracts

- [sing-box 1.13.12 log context](https://github.com/SagerNet/sing-box/blob/1086ab2563320e0da0c23b3a491d8dfa0939dff4/log/id.go)
  and [text formatter](https://github.com/SagerNet/sing-box/blob/1086ab2563320e0da0c23b3a491d8dfa0939dff4/log/format.go).
- [Pinned HTTP proxy authentication and CONNECT handling](https://github.com/SagerNet/sing/blob/9404d4d2a252db5bb5dae1bbacaa55bb2bf08ed4/protocol/http/handshake.go).
- [Istio 1.31.1 TCP proxy and CONNECT configuration](https://github.com/istio/istio/blob/190ae921b848ec010b8be4457533837ed8fce258/pilot/pkg/networking/core/networkfilter.go).
- [Envoy tracing prerequisites](https://www.envoyproxy.io/docs/envoy/v1.38.0/intro/arch_overview/observability/tracing).
