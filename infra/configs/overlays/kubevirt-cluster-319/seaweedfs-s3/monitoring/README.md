# SeaweedFS dashboard

`dashboard.json` uses the official SeaweedFS **4.48** chart dashboard,
matching the verified OMV producer version. Source:
[`k8s/charts/seaweedfs/dashboards/seaweedfs-grafana-dashboard.json`](https://github.com/seaweedfs/seaweedfs/blob/530be3e37337488ecc34d58441e0bc476e121c93/k8s/charts/seaweedfs/dashboards/seaweedfs-grafana-dashboard.json),
commit `530be3e37337488ecc34d58441e0bc476e121c93`.
Upstream SHA-256:
`09a4af4e950aa9c42a8560d47c773bede30dbaa4ebe6065d85b7a76337bb74a7`.
`LICENSE.dashboard` preserves the Apache 2.0 license.

The official panel layout is retained. Local bindings update UID `seaweedfs` in
place and use `victoriametrics`. Every selector has `k8s_cluster_name` and the
existing `job="seaweedfs"`. The upstream Kubernetes namespace selector becomes a
SeaweedFS host selector using our existing `node` label. Pod legends/aggregations
likewise use the external host, without inventing Kubernetes identity for OMV.
Per-process panels use the native scrape `instance` label: these endpoints are
scraped directly and do not supply Pushgateway's `exported_instance` label.
Volume-server disk use and request latency therefore remain separate on one host;
the S3 per-instance latency panel likewise keeps each gateway distinct.
Master/filer job filters use the existing `component` labels. Bucket size/object
gauges retain upstream `max by(bucket)` to avoid counting copies from multiple
components. The refresh interval defaults to 30 seconds.

These are the existing master, filer and S3-gateway listeners from
`scrape-config.yaml`. The direct S3 HTTPS probe remains separate. The volume
servers already expose metrics on OMV, but those listeners are not yet included
in this ScrapeConfig. The direct/campus gateway has no enabled metrics listener.
Their charts can be empty until collection is configured. Existing OMV metrics
listeners are private HTTP without authentication; this does not provide the
identity protection used for in-cluster metrics. S3 latency quantiles are also empty without requests
in the selected time window, and bucket traffic metrics depend on producer support.

The [Portainer Stacks](../portainer/README.md) prepare loopback-only native
listeners and a common mTLS policy in both network namespaces. Dedicated
cert-manager resources and read access to only the server leaf Secret are
included here. Their publication does not deploy the external Stacks or switch
the existing scrape targets. Complete the documented certificate/OMV barrier
before publishing the HTTPS collection changes.

When updating, verify the pinned source, preserve the UID, reapply the
host/component bindings, and validate active queries and bucket deduplication.
