# Proxy replicas and cache storage

The Deployment runs two replicas with RollingUpdate, Kubernetes default rollout
limits, a minimum readiness period and a PodDisruptionBudget. Preferred node
anti-affinity spreads replicas when capacity allows. Existing proxy ports and
clients continue to use `proxy-svc`.

`nodes-cache-rwx` is a new 1Gi Longhorn RWX claim shared by subscription init
containers. Writers use bounded POSIX locks and atomic file replacement. A failed
subscription fetch reads the last successful shared configuration without
republishing it. Each Pod receives a private startup snapshot in `config-temp`;
a peer publishing new subscriptions cannot change a running Pod's configuration.
The daily restarter rolls replicas to refresh their startup configuration.

`work-cache` is a private 100Mi emptyDir for each Pod. UI downloads and mutable
sing-box state cannot be shared safely by concurrent instances. UI assets are
redownloaded on Pod replacement. The old RWO `nodes-cache` and
`proxy-engine-work-cache` claims remain declared and excluded from pruning for
rollback; neither is mounted by the new Deployment.

The admin HTTPRoute uses a separate `proxy-admin-svc` and an Istio session cookie
for best-effort affinity. Runtime selections, counters and connection lists are
per instance. UI selection changes do not fan out to every replica; use the
existing Secret's `NODE_SELECTIONS` and a rollout for consistent startup choices.
Endpoint changes may remap sessions. The original TCP proxy Service has no cookie
policy.

## Before merge and cutover

1. Create the new claim from `nodes-cache-pvc.yaml` and verify it is Bound.
   Verify NFS clients and cross-node mount/lock behavior on the application nodes.
2. Confirm subscription fetching works. An empty cache can bootstrap directly;
   the new claim initially has no fallback when subscriptions are unavailable.
   To preserve fallback before cutover, run a one-time copy Pod on the node of the
   existing proxy Pod, mounting the old claim read-only and the new claim writable.
   Parse and validate `nodes-last-good.json` as a JSON object with a nonempty
   `outbounds` list, then publish it atomically as both `nodes-last-good.json` and
   `nodes.json` under the same `.nodes-cache.lock` used by the init script. Do not
   print subscription credentials or JSON contents. Do not copy sing-box work state.
3. Merge and reconcile the reviewed change. Verify both replicas become Ready,
   preferably on different nodes, and that both pass proxy requests. Test the
   admin cookie, refresh behavior, subscription-failure fallback and an ordinary
   rollout while continuously requesting the proxy. Long-lived TCP connections
   can disconnect when their owning Pod terminates.

Rollback before merging uses the retained RWO claims. After cutover, revert the
Deployment and route configuration together. Stop overlapping proxy Pods before
restoring the single-instance RWO mounts. The new RWX claim remains retained.

References: [Longhorn RWX](https://longhorn.io/docs/1.11.1/nodes-and-volumes/volumes/rwx-volumes/),
[Istio cookie affinity](https://istio.io/latest/docs/reference/config/networking/destination-rule/#LoadBalancerSettings-ConsistentHashLB-HTTPCookie).
