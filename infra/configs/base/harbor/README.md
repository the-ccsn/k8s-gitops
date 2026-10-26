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
