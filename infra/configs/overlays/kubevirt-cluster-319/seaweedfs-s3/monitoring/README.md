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

Volume disk totals sum native `normal` and `ec` bytes. `deleted_bytes` is already
part of a normal data file, so it remains visible in the type breakdown but is
not added again to totals. These metrics cover SeaweedFS data files/shards, not
complete filesystem, index or metadata usage.

`scrape-config.yaml` declares ten authenticated HTTPS paths: master, filer,
ordinary S3, direct S3 and six volume servers. The target names use internal DNS,
with no fixed IP or site-alias hostname. `instance` combines target address and
metrics path so the six volume servers on one host cannot overwrite each other.
The client Secret supplies CA trust, certificate and key; normal DNS-name
verification remains enabled. The direct S3 HTTPS transport probe stays separate.
S3 latency quantiles are empty without requests in the selected time window,
and bucket traffic metrics depend on producer support.

The [Portainer Stacks](../portainer/README.md) prepare loopback-only native
listeners and a common mTLS policy in both network namespaces. Dedicated
cert-manager resources and read access to only the server leaf Secret are
included here. This version requires those Stacks to be deployed; publishing it
does not update OMV. Complete the documented certificate/OMV barrier before
publishing these HTTPS collection changes. The preparation commit keeps the old
three-target HTTP configuration until that barrier is satisfied.

Alerts cover failed targets, disappearance of any of the five component families
and fewer than six volume targets remaining in discovery. A failed but discovered
volume still counts toward that inventory and triggers the failed-target alert
instead. Volume I/O/read/write failures retain the affected `instance`; S3 latency
retains both gateway identity and request type. Bucket gauges remain deduplicated.

When updating, verify the pinned source, preserve the UID, reapply the
host/component bindings, and validate active queries and bucket deduplication.
