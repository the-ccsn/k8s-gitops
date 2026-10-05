# Kubernetes Bootstrap

This is the Kubernetes half of bootstrap for `kubevirt-cluster-319`. Complete the
[NixOS bootstrap](https://github.com/the-ccsn/nix-config/tree/main/hosts/k8s/kubevirt-cluster-319)
first: this procedure starts with a reachable K3s API, the expected joined nodes,
a certificate-based administrator kubeconfig with context `snc`, and working
bootstrap image access. Nodes may still be `NotReady` until Cilium is installed.
NixOS installation, host networking and K3s initialization are documented there.

Terraform establishes Cilium, Flux and its initial resources. Flux then installs
the remaining infrastructure, identity configuration, applications and VMs.
Commands below run from this repository's root unless a step says otherwise.

```bash
kubectl --context snc get --raw=/readyz
kubectl --context snc get nodes -o wide
```

## 1. Prepare the GitOps configuration and secrets

Install the local tools if needed:

```bash
nix shell nixpkgs#terraform nixpkgs#kubectl nixpkgs#fluxcd nixpkgs#sops nixpkgs#age
```

Review `clusters/kubevirt-cluster-319/` and its selected infra, app and VM overlays.
Set the FluxInstance's Git URL, `sync.ref` and `sync.path` in
[flux.yaml](../clusters/kubevirt-cluster-319/flux.yaml) to the intended repository,
revision and cluster directory. The tracked default is `refs/heads/main`.
The configuration must be available at that Git revision before Flux can use it;
local uncommitted files are not a Flux source. Arrange Git authentication if the
source is private. Terraform's `bootstrap_revision` is a separate input for the
bootstrap module's resources; it does not replace the FluxInstance's `sync.ref`.

Update the environment-specific manifests before running Terraform or allowing
Flux to reconcile. Use the target cluster's overlays where they exist; some current
values are still in shared bases and must also be reviewed.

| Configuration | Source to review and update |
| --- | --- |
| Cluster name, Git source and enabled resources | [cluster entrypoints](../clusters/kubevirt-cluster-319/), their `spec.path` values, and the selected overlay `kustomization.yaml` files; `TF_VAR_cluster_name` selects paths, it does not rename every manifest |
| Cilium API endpoint, interfaces and Pod IPAM ranges | [Cilium values](../infra/pre-controllers/overlays/kubevirt-cluster-319/cilium/values.yaml): `k8s.apiServerURLs`, `devices`, `clusterPool*PodCIDRList` and native-routing CIDRs. The API endpoint must reach an already-started server during bootstrap |
| API VIP and interface | [kube-vip DaemonSet](../infra/pre-controllers/overlays/kubevirt-cluster-319/kubevip/daemonset.yaml): `address`, `vip_interface`, subnet; match the NixOS VIP and API SANs. Update [gen-config.sh](../infra/pre-controllers/overlays/kubevirt-cluster-319/kubevip/gen-config.sh) too if using that helper |
| Load-balancer pools and BGP | [IP pools](../infra/pre-controllers/overlays/kubevirt-cluster-319/cilium/cilium-ip-pools.yaml), [BGP configuration](../infra/pre-controllers/overlays/kubevirt-cluster-319/cilium/cilium-bgp-eip-lb.yaml), its SOPS auth Secret and [router notes](../infra/pre-controllers/overlays/kubevirt-cluster-319/cilium/README.md): CIDRs, peer addresses, ASNs, source interface and selected gateway nodes |
| DNS, ingress and certificates | [gateway bases](../infra/configs/base/gateway/), [cluster gateway patches](../infra/configs/overlays/kubevirt-cluster-319/), [certificate issuers](../infra/configs/base/cert-manager/), [ExternalDNS](../infra/controllers/foundation/base/external-dns/) and app HTTPRoutes: domains, DNS zones, certificate names and Cloudflare credentials/tunnel configuration |
| Storage and node-specific scheduling | [Longhorn nodes](../infra/controllers/foundation/overlays/kubevirt-cluster-319/longhorn-hdd-nodes.yaml), [HDD StorageClass](../infra/controllers/foundation/overlays/kubevirt-cluster-319/longhorn-hdd-storageclass.yaml) and workload node selectors: node names and disk paths must match NixOS |
| Identity endpoints and application/VM configuration | Logto/Harbor HelmReleases, provider credential hostnames, application CR redirect URIs, issuer URLs, [app overlays](../apps/overlays/kubevirt-cluster-319/) and [VM definitions](../vms/): domains, network attachments, addresses, storage and externally supplied credentials |

Changing an IP or domain in one file is insufficient. Check references in both
repositories, including split DNS, OAuth redirect URIs and certificate SANs. Current
Cilium uses its own cluster-pool Pod ranges, which differ from K3s Node PodCIDRs;
keep Cilium native-routing CIDRs aligned with Cilium's allocated ranges rather than
blindly copying the K3s CIDRs. The BGP-selected nodes must carry the declared
`node-role.kubernetes.io/lb-gateway` label. Review these values before the first
reconcile; do not substitute guessed addresses into a live deployment.

Restore the matching GitOps age private key to the ignored `k8s-gitops.agekey`
file. Generating a different key will not decrypt the existing manifests. Review
SOPS-encrypted external credentials, including DNS, SMTP, GitHub and Harbor, for
validity in the target environment. Edit them with SOPS using the restored key;
do not put plaintext credentials in Git.

## 2. Bootstrap Cilium, Flux and SOPS with Terraform

Terraform uses the kubeconfig's current context, so select `snc` explicitly.
The following commands use environment inputs instead of a plaintext tfvars file:

```bash
kubectl config use-context snc
export TF_VAR_kubeconfig="$HOME/.kube/config"
export TF_VAR_cluster_name=kubevirt-cluster-319
export TF_VAR_bootstrap_revision=main
export TF_VAR_sops_age_key="$(cat k8s-gitops.agekey)"
terraform -chdir=bootstrap init
terraform -chdir=bootstrap plan
terraform -chdir=bootstrap apply
unset TF_VAR_sops_age_key
```

Use the actual kubeconfig path if it differs. Keep Terraform's state securely:
it contains the SOPS private key even though the input is marked sensitive. Local
state and tfvars are ignored by Git; retain state to manage or retry this bootstrap.

[main.tf](main.tf) installs the initial Cilium chart, Flux Operator and
FluxInstance, `flux-system/sops-age`, and the runtime configuration. Its bootstrap
Job uses host networking and tolerates NotReady nodes to establish networking.
Do not run a second `flux bootstrap` or manually install another Cilium release.

```bash
kubectl --context snc wait node --all --for=condition=Ready --timeout=10m
kubectl --context snc -n flux-system get fluxinstance,gitrepository,kustomization
kubectl --context snc -n flux-system get secret sops-age
flux --context snc get all -A
```

## 3. Let Flux establish infrastructure and Logto

Flux follows the declared dependencies automatically; there is no manual sequence
of `kubectl apply` commands. The important milestones are:

1. Namespaces and pre-controllers establish Cilium configuration, API VIP, local
   storage, Crossplane and supporting controllers.
2. Identity providers publish their CRDs. Foundation, core networking, monitoring
   and general controllers establish storage, certificates, ingress and operators.
3. `infra-configs` applies routes, database configuration, ProviderConfigs, Harbor
   and the Kubernetes Application CR. It can apply CRs whose external services are
   still starting.
4. The `logto` phase starts Logto and its database using the chart's official schema
   initialization. It waits for the Kubernetes Application and its connection
   Secret before releasing Kiali and the remaining application phases.

Verify storage, gateway addresses, DNS and certificates, then access
`https://login-dash.ccsn.dev` and the issuer
`https://login.ccsn.dev/oidc/.well-known/openid-configuration` from the workstation
and cluster network. Also check the API VIP works before making it the permanent
administrator kubeconfig endpoint.

For campus ingress, configure OpenWrt port forwarding to `172.30.0.201` and
complete the [OpenWrt DDNS setup](../infra/configs/base/i319-reroute/README.md#dns-and-openwrt-ddns).
The router writes `ingress.319.ccsn.dev` A from its campus-facing IPv4;
ExternalDNS writes AAAA from the Service IPv6. Set up the entry A before
switching existing campus wildcard records to the declared CNAMEs.

On a fresh Logto database, `logto` will remain pending until step 4 establishes its
Management API connection. Inspect its HelmRelease separately to distinguish a
healthy Logto deployment from an Application waiting for credentials.

```bash
flux --context snc get kustomizations
flux --context snc get helmreleases -A
kubectl --context snc -n prod get helmrelease logto
```

## 4. Connect Crossplane to Logto

For an empty database, complete the initial administrator setup in Logto Console.
Create a Machine-to-machine application for Crossplane and assign an M2M role with
the built-in Logto Management API `all` permission. The Management API itself is
built in; do not create another API resource or modify the database directly.

Edit [management-credentials.yaml](../apps/base/logto/management-credentials.yaml):

```bash
SOPS_AGE_KEY_FILE="$PWD/k8s-gitops.agekey" sops apps/base/logto/management-credentials.yaml
```

Its `stringData.credentials` JSON contains:

```json
{
  "hostname": "login.ccsn.dev",
  "resource": "https://default.logto.app/api",
  "application_id": "<new M2M application ID>",
  "application_secret": "<new M2M application secret>"
}
```

Save the encrypted manifest and deliver that change through the tracked Git branch.
Flux updates `prod/logto-management`; the
[ClusterProviderConfig](../infra/configs/base/crossplane/logto-provider-config.yaml)
then authenticates and reconciles the identity CRs. No custom database Job or SQL
bootstrap is involved. This manual connection is required once per empty Logto
database. When restoring the database, retain its matching M2M credential instead.

For an existing database, adopt existing identities using `Observe` and live
external names before enabling `Create`/`Update`; otherwise applications with new
IDs may be created. The empty-database procedure does not perform this adoption.

## 5. Finish Kubernetes OIDC and registry setup

Read the generated Kubernetes client ID:

```bash
kubectl --context snc -n flux-system get applications.application.logto.m.crossplane.io kubernetes-cluster \
  -o jsonpath='{.metadata.annotations.crossplane\.io/external-name}{"\n"}'
```

Use this generated ID to complete the
[NixOS node integration](https://github.com/the-ccsn/nix-config/tree/main/hosts/k8s/kubevirt-cluster-319#4-complete-node-integration-after-kubernetes-bootstrap),
then update the local kubeconfig's OIDC client ID. Follow the
[OIDC login instructions](../infra/configs/base/apiserver-oidc/README.md).
Headlamp and Kiali read `flux-system/kubernetes-oidc` automatically through Flux.
Application IDs are generated by Logto and are not pinned in Git.

Create users and assign their roles manually in Logto. GitOps manages the declared
application, connector and role definitions, but does not store users or their
role memberships. Verify a user with the intended roles can access Kubernetes and
the corresponding applications before relying on OIDC for administration.

Verify Harbor is healthy and its seven `ProxyCache` composites and robot Account
are Ready. Crossplane creates registries first and passes their observed IDs to the
proxy-cache projects; no Harbor IDs are pinned in Git. The managed resources use
`Observe`, `Create` and `Update`, without permission to delete external resources.
See the [Harbor adoption notes](../infra/configs/base/harbor/README.md) before
reconciling against an existing installation.
This is the handoff condition for the NixOS procedure's Harbor-first node mirror
configuration; keep bootstrap image access independent of Harbor until then.
Harbor OIDC client credentials are supplied by its generated connection Secret.

## 6. Verify the complete cluster

After the identity gate passes, Flux deploys Kiali, the remaining apps and VMs.
Verify all expected enabled resources, not just the Flux controllers:

```bash
flux --context snc get all -A
kubectl --context snc get nodes -o wide
kubectl --context snc get pvc -A
kubectl --context snc get gateway,httproute -A
kubectl --context snc get pods -A
kubectl --context snc get virtualmachines.kubevirt.io,virtualmachineinstances.kubevirt.io -A
```

Bootstrap is complete when Flux sources and enabled Kustomizations/HelmReleases
are Ready, required volumes are bound, routes have working DNS/TLS, OAuth login
works with the intended permissions, and the enabled VMs and application health
checks pass. Check VM network attachment and the
[KubeVirt socket compatibility notes](../infra/controllers/general/base/kubevirt/README.md)
if dynamic network attachment fails. Configure any application-specific settings
that remain outside GitOps before handing over the cluster.

If a stage stalls, inspect the first failing dependency and its events with
`flux --context snc events`. Fix its configuration or external prerequisite and
let Flux retry; do not bypass the dependency gates to start downstream consumers.
