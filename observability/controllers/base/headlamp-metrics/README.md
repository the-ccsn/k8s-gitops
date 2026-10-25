# Headlamp query boundary

This Kustomization defines an internal query-only endpoint for Headlamp's
builtin Prometheus plugin, selected by the independent metrics runtime overlay.

Existing administrators can enable **Enable Metrics** in the Prometheus plugin
and use autodetection or `monitoring/headlamp-metrics:8080` with an empty subpath.

The pinned regular Nginx Alpine image includes njs. The container runs as UID/GID
10001 with a read-only root filesystem, dropped capabilities, no API token and
only `/tmp` writable. Kustomize hashes its generated configuration so config
changes roll the Deployment.

Only GET requests to the exact original paths `/api/v1/query`,
`/api/v1/query_range` and `/-/healthy` reach the fixed VMSingle backend. Request
bodies, other methods, normalized/encoded path variants, redirects, admin,
delete, write, metadata and debug routes are denied. Responses are buffered and
capped at 8MiB; client credentials and upstream control headers are not relayed.
Readiness checks VMSingle health; liveness only checks the local TCP listener.

This boundary grants no Kubernetes RBAC and does not enforce namespace
isolation. Do not bind ordinary users or expose this Service through a Gateway
under an assumption that query-only means namespace-scoped.
