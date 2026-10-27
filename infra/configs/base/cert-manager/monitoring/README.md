# cert-manager dashboard

`dashboard.json` uses the community [cert-manager mixin](https://github.com/imusmanmalik/cert-manager-mixin)
published by [Monitoring Mixins](https://monitoring.mixins.dev/cert-manager/).
The generated source is pinned to website commit
`7b1f6de899ffdbdf59c807a32cd8a9a514231915`:

- [Upstream JSON](https://github.com/monitoring-mixins/website/blob/7b1f6de899ffdbdf59c807a32cd8a9a514231915/assets/cert-manager/dashboards/cert-manager-overview.json)
- SHA-256: `733b08670ce7c93d6ea9efcc04c1c0a86bdd53ad2ceaf33d414200886916d582`
- Apache 2.0 license: `LICENSE.dashboard`, from mixin source commit
  `a5f74ad04be4ee8fc007a10a918b3c48154c7e55`.

The ten upstream panels retain their layout and visualization types. Local
adaptations bind them to the existing `victoriametrics` datasource and the
`cert-manager` UID, updating the existing dashboard in place. Selectors separately
identify the Kubernetes cluster, controller namespace and certificate namespace.
There is no additional datasource or parallel dashboard.

Queries use `k8s_cluster_name` and
`cert_manager_certificate_namespace_name`, as defined by the shared naming
contract. Table fields explicitly distinguish the controller namespace from the
certificate namespace. Their join key uses `/`, which cannot occur in Kubernetes
names, to keep certificates with similar names in different namespaces distinct.

The dashboard queries current metrics directly:

- Certificate validity uses `certmanager_certificate_not_after_timestamp_seconds`.
- Resource limits and requests use `kube_pod_container_resource_limits` and
  `kube_pod_container_resource_requests`, with explicit `resource` and `unit`.
- CPU, memory and network use the existing cAdvisor metrics.

No deprecated metric aliases, fallback queries or new recording rules are added.
The existing certificate alerts and metrics access policy continue to apply.
ACME request rates may be zero when no issuance or renewal is in progress. Mean
ACME latency has no value when there are no requests in the selected window.

When updating, verify the pinned source hash, preserve its panel design, reapply
these bindings and naming changes, and validate every variable and panel query
against the collected metrics. Keep the dashboard UID and namespace meanings.
