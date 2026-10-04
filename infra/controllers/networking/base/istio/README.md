# Istio Service Mesh

Helm Charts:

- https://github.com/istio/istio/tree/1.28.3/manifests/charts

## NOTES

1. All
   [Platform-Specific Prerequisites - Istio Ambient Mode Docs](https://istio.io/latest/docs/ambient/install/platform-prerequisites/)
   should be met before installing Istio. so you have to install the prerequisites in
   `/infra/pre-controllers/`!

## Recovering stale ambient enrollment

After a node or Pod sandbox restarts, an `ambient.istio.io/redirection=enabled`
annotation can outlive its network rules and ztunnel listeners. Check the Pod's
network namespace for TCP 15008 and confirm a successful gateway-to-Pod request;
application readiness alone does not verify mesh enrollment.

For an affected Pod, temporarily set `istio.io/dataplane-mode=none`, wait for the
redirection annotation to disappear, then restore its original label value
(remove the temporary label if it was originally absent). This makes the CNI
controller find the current network namespace and register it again. Verify the
annotation, listeners, and actual traffic afterwards. Recover one Pod at a time.

Ambient detection retry prevents CNI ADD from silently continuing after an API
detection error. It does not repair an already stale enrollment annotation.
