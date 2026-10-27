# Cloudflared dashboard

`cloudflared-dashboard.json` adapts the community DockFlare dashboard at
[`examples/dashboard.json`](https://github.com/ChrispyBacon-dev/DockFlare/blob/9c7bed826f76b2005a544b260ac457c81b3515d9/examples/dashboard.json),
commit `9c7bed826f76b2005a544b260ac457c81b3515d9`.
Unmodified source SHA-256:
`72554a9adc76f4eb9297a1bcb177180d2004333d40ce9e7b62a4f66887d33e43`.
This adaptation was modified on 2026-10-27 and is distributed under GPL-3.0;
`LICENSE.dashboard` preserves the upstream license. The dashboard description
also identifies the source, license and modifications.

The existing `cloudflared-tunnel` UID is retained, with 14 charts using
`victoriametrics`. Cluster, namespace, job and Pod options come from native
`cloudflared_tunnel_ha_connections`, keeping generic process metrics scoped to
tunnel Pods rather than the Cloudflare Operator. Pod All expands actual options.
No target address, Pod name or credential is embedded.

Applicable upstream layouts and panel types are retained, with these corrections:

- Latency uses `cloudflared_proxy_connect_latency_bucket`, measured in
  milliseconds. Titles identify TCP/stream origin connection establishment time;
  ordinary HTTP traffic need not populate this histogram. An unobserved histogram
  has no percentile data. This is not end-to-end HTTP latency.
- Concurrency uses `cloudflared_tunnel_concurrent_requests_per_tunnel`.
- Edge locations use active `cloudflared_tunnel_server_locations == 1`, grouped
  by `edge_location`, excluding stale zero-valued location entries.
- The unsupported per-protocol request metric is omitted. Go memory is labelled
  as heap allocation, and process views retain the selected tunnel job.
- Total requests and HTTP-code counts evaluate the selected-range increase once
  through instant queries, instead of summing overlapping range-query results.
  Error percentage divides by the actual request rate, including below one
  request per second; no-traffic intervals are not presented as proven success.
- Total HA connections are complemented by the existing per-Pod HA and scrape
  health views, so a healthy replica does not hide a failed one.

This dashboard covers the cloudflared connector. It does not provide Cloudflare
edge HTTP analytics, WAF events or request logs. Those require separate sources.
No exporters, recording-rule aliases, collection settings or tunnel workloads
are added. When updating, verify the source hash, preserve the UID, reapply the
native metric corrections and scopes, and check units and failure cases.
