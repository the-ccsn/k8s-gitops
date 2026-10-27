# Harbor

Harbor is deployed by the HelmRelease in this directory. Its administrator password
comes from the SOPS-encrypted `harbor-admin-auth` Secret; do not assume a default
password. OAuth configuration reads the Logto-generated connection Secret through
`core.extraEnvVars` and `CONFIG_OVERWRITE_JSON`.

Project creation is restricted to system administrators. Crossplane uses its
dedicated management credentials to create and configure projects; normal OIDC
logins have no system-administrator group mapping. The non-default Logto role
`harbor:maintainer` grants Maintainer access to the seven proxy-cache projects
through the native MemberGroup declarations in `managed-resources/project-access.yaml`.
The same file declares the shared OIDC Group; memberships retry until it exists.
Keep the stable group name explicit and resolve only the project ID: the current
reference resolver otherwise alternates ownership of the two resolved fields.
Assign this role explicitly in Logto and sign in to Harbor again to refresh claims.
Maintainers can push, scan and delete images and manage tag policies, but cannot
edit project configuration, manage members or delete projects. Proxy-cache projects
retain Harbor's native restriction against manual pushes. New projects need an
explicit membership declaration. The local administrator remains available for
GitOps management and recovery; existing administrator grants must not be used for
daily access because Harbor combines permissions from all memberships.

Metrics for core, registry, jobservice and exporter are enabled on port 8001.
Their pods join Istio ambient; only vmagent can access that listener. The
access policy is installed by `infra-configs` before metrics are enabled. The
remaining owner-local `monitoring/` resources are included by `observability-configs`
after the shared monitoring APIs. They provide the Harbor dashboard, backend health
and finite-quota alerts, plus internal and public health probes. The public probe
checks transport availability; `harbor_health` reports backend health separately.
The dashboard imports Harbor's official v2.15.4 example from a fixed release commit;
its source SHA-256 is recorded on the resource. The native datasource mapping uses
the `victoriametrics` UID because the upstream placeholder occupies UID fields.

## Native application tracing

Harbor core, jobservice and registryctl export OTLP HTTP/protobuf to the existing
Collector on port 4318 at `/v1/traces`, then to Tempo. The endpoint is a host:port,
without a scheme or path. HTTP is carried inside Istio ambient mTLS; no public
ingestion endpoint or additional credentials are introduced. The existing
`.cluster.local` proxy exclusion keeps this traffic inside the cluster.

Native service names remain `harbor-core`, `harbor-jobservice` and
`harbor-registryctl`, with `service.namespace=harbor` and
`k8s.namespace.name=harbor`. The registry Pod's resource annotation also changes
its template: chart 1.19.4 does not checksum the registryctl trace ConfigMap,
so changing that ConfigMap alone would leave existing registryctl processes
unchanged. Core and jobservice already checksum their trace configuration.

`sample_rate: 1` records all Harbor spans. Harbor 2.15.4 uses a bare
`TraceIDRatioBased` sampler rather than `ParentBased`; 100% retains application
spans for ingress-selected traces. Istio still samples new traces at 1%, so
Harbor can also store traces with no recorded ingress span. Current core traffic
is approximately 0.37 requests/second; verify actual exported span rate, Collector
queues and Tempo resource use after rollout before changing this policy.

Harbor supports W3C Trace Context. Its core request-context text logs contain
`traceID`, which the Collector promotes to the LogRecord context for the existing
Loki-to-Tempo link. These records have no native span ID. Global logger calls and
separate job loggers are not universally correlated. Harbor's `X-Request-ID`
attribute retains its native meaning; it is not the campus correlation header.
The Collector removes query strings from confirmed Harbor HTTP-client `url.full`
attributes, leaving server paths and unrelated SDK spans unchanged.

In Grafana, select namespace `harbor` in the application logs and trace views,
then use the existing trace-to-logs and trace-to-metrics links. Core contextual
logs and sampled spans can be correlated by trace ID across ingress and Harbor.
The separate distribution-registry container is not an OTLP producer. Queued
jobs start independent traces, and some outgoing requests do not propagate the
caller context; this does not promise complete DB, Redis, storage or job tracing.
See the [pinned Harbor implementation](https://github.com/goharbor/harbor/blob/0a6bf30d54e779962ad5b862fc67e3e9f6b010d8/src/lib/trace/trace.go)
and [official tracing guide](https://goharbor.io/docs/main/administration/distributed-tracing/).

## Proxy-cache and robot management

Crossplane is the only writer for the seven proxy-cache registries/projects and
the system robot account. `managed-resources/proxy-caches.yaml` declares the pairs.
The namespaced `ProxyCache` composition creates the Registry first, waits for its
observed positive ID, and then sets the Project's `registryId`. The composition
uses the observed registry ID and does not depend on IDs from an old database.
The upstream Harbor provider currently exposes no `registryIdRef` on Project.

The definition and composition stay in this Harbor directory. The existing
`identity-providers` Flux phase installs them and the Go templating function before
`infra-configs` creates the composites. The function package is digest-pinned.
A composite is Ready only when both resources are Ready and the project reports
its association with the observed registry. The provider treats `registryId` as
immutable: changing the registry of an existing project requires an explicit
project migration. The no-Delete policy prevents an automatic destructive
replacement; the empty-database bootstrap creates the correct association first.

Robot permissions resolve project names on every reconcile. The robot password
is read from `harbor-k8s-robot-credential`; it remains the same value used by the
existing node configuration. The Harbor provider reads `harbor-management` JSON
credentials. Both input Secrets are SOPS-encrypted; keep the administrator
credentials aligned with Harbor's actual administrator account on an empty database.
No custom database bootstrap or runtime Terraform controller is required.

```bash
kubectl --context snc -n harbor get proxycaches.harbor.ccsn.dev
kubectl --context snc -n harbor get registries.harbor.m.crossplane.io,projects.harbor.m.crossplane.io,accounts.robot.harbor.m.crossplane.io
```

## Adopt an existing Harbor installation

An empty database needs no external IDs: apply the declarations after Harbor is
reachable and let Crossplane create them. An existing installation requires a
one-time adoption before enabling creation:

1. Suspend the legacy Harbor Terraform resource through the existing deployment
   workflow and confirm `spec.destroyResourcesOnDeletion` is false or unset.
   Retain its state backup. Removing a Terraform CR must not destroy Harbor data.
2. Before reconciling the new declarations, set each ProxyCache's
   `spec.resourceManagementPolicies` to `[Observe]`, and the robot Account's
   `spec.managementPolicies` to `[Observe]` in the tracked Git configuration.
3. Import each existing Registry, Project and robot Account by setting
   `crossplane.io/external-name` on its live managed resource. Use Harbor's actual
   `/registries/<id>`, `/projects/<id>` and `/robots/<id>` API paths, not IDs from
   another database. The composed managed resources keep the declared registry
   names and project names; the robot managed resource is named `k8s`.
   Missing IDs leave resources pending without creating duplicates.
4. Verify the observed registry/project associations, robot permissions and
   password agree with the existing installation. Then restore the declared
   `[Observe, Create, Update]` policies through Git. External IDs stay in the live
   resources and are not committed to Git.
5. Remove the suspended Terraform resource and its dedicated source/controller
   after confirming Crossplane is the only writer. The pre-controller Flux phase
   has `prune: false`, so removing manifests alone will not uninstall an already
   deployed tofu-controller HelmRelease. Clean up that legacy release explicitly
   through the cluster deployment workflow after adoption. No Terraform or runner
   manifests remain in this repository.

The managed resources do not allow `Delete`; deleting a CR does not authorize
removing its external Harbor resource. Node mirrors must remain usable throughout
adoption. See [mirror configuration](../../../../scripts/templates/README-harbor-mirror.md)
and the [Kubernetes bootstrap procedure](../../../../bootstrap/README.md).
