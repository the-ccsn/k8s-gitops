# k8s-as-code

Repository for my personal kubernetes clusters.

## Prerequisites

All my Kubernetes Clusters are deployed via
[isning/nix-config/hosts/k8s](https://github.com/isning/nix-config/tree/main/hosts/k8s).

```bash
nix shell nixpkgs#fluxcd
```

My personal container images:

- Dockerfile & CI: <https://github.com/isning/containers>
- Docker Hub: <https://hub.docker.com/r/isning>

## Bootstrap

Bootstrap is now driven by Terraform in the `bootstrap/` directory.

1. Add a new folder in `clusters/` with the name of the cluster.
1. Add the Flux entrypoint files into the new cluster folder.
1. Prepare `bootstrap/terraform.tfvars` from `bootstrap/terraform.tfvars.example`.
1. Run Terraform to install Flux and the initial cluster resources.

See [bootstrap/README.md](bootstrap/README.md) for the current end-to-end flow.

### Bootstrap Flow (Recommended)

Use the staged Terraform bootstrap flow and keep dependency breakers in the flow
itself (no hard cut-over until dependencies are healthy):

1. Bootstrap Flux and the initial cluster resources from `bootstrap/`.
2. Verify Flux source/controller health and the `sops-age` secret.
3. Reconcile `infra-namespaces` first.
4. Reconcile `infra-pre-controllers` (networking/storage foundations).
5. Reconcile `infra-controllers` (operators and Harbor HelmRelease).
6. Reconcile `infra-configs`, but apply in this order:
   - 6.1 Networking and ingress routes first (Gateway/HTTPRoute/DNS paths).
   - 6.2 Harbor runtime mirror configs only in non-enforcing mode first.
   - 6.3 Logto/OIDC providers and clients after ingress is confirmed reachable.
7. Validate service readiness before hard dependencies:
   - Harbor core/registry healthy and serving API.
   - Logto issuer URL reachable from cluster and admin workstation.
8. Initialize Harbor proxy-cache projects (`tofu-controller` + Terraform at `infra/configs/base/harbor/tf`).
9. Switch node mirror config to Harbor-first only after step 7-8 pass, and keep
   a break-glass upstream fallback during first rollout.
10. Enable OIDC-dependent login paths (API server OIDC login flow and related client
    settings) only after Logto is healthy and reachable.
11. Reconcile `apps` and `vms`.
12. Perform all items listed in the Manual Steps Index.

Suggested verification commands:

```bash
flux get ks
flux get all -A
flux events
```

### Manual Steps Index (Post-Bootstrap)

The following items currently require manual operation and are not fully automated by
GitOps manifests. Review them after a fresh bootstrap:

1. Harbor initial login and OIDC manual setup:
   - `infra/controllers/base/harbor/README.md`
2. Harbor node mirror templates and credential rotation notes:
   - `scripts/templates/README-harbor-mirror.md`
3. Astrbot Bay and OneBot adapter manual setup:
   - `apps/base/astrbot/README.md`
4. API server OIDC login helper (kubectl oidc-login):
   - `infra/configs/base/apiserver-oidc/README.md`
5. KubeVirt dynamic-networks-controller manual workaround notes:
   - `infra/controllers/base/kubevirt/README.md`

## Usage

Add your configs into those directories, fluxcd will take care of the rest:

```bash
› tree
.
├── apps             # app-specific configs
├── clusters         # cluster-wide configs
│   └── k3s-test-1   # cluster name
├── infra            # cluster-wide infra files(monitoring, networking, certificates, etc.)
```

CLI usage:

> NOTE: kustomization, helmrelease and other resources are defined as k8s's CRDs, so you
> can use `kubectl get ks` or `k9s` to check the status of the resources too. use
> `flux get all -A` to get all resources' status is not the only way.

```bash
# show stats
flux stats

# show stats for a specific resource, such as kustomization
flux get ks

# show k8s events (reconcile, build, deploy, etc)
flux events

# reconcile a specific git repo
flux reconcile source git flux-system

# get all other resources' status
flux get all -A

# show image automation status
flux get images all -A
# reconcile a specific image automation
flux reconcile image update <image-automation-name>

# retry a failed kustomization, such as infra-controllers
flux reconcile ks infra-controllers

# show more details
flux --help

# suspend and resume a kustomization's sync
flux suspend ks vms
flux resume ks vms
```

## Image Lock

This repo uses `gen-image-lock` to generate `clusters/<name>/images.lock.nix` for
airgapped/archived images.

How it works:

- `flux-local get cluster` extracts image sources from Kustomizations/HelmReleases.
- `flux-local build all` renders manifests to discover image targets.
- The script resolves image digests and builds archive hashes via Nix.
- The Nix archive builder uses `skopeo` to copy by digest, preserve digests, and
  handle multi-arch manifest lists based on detected media types.

Rationale (why `skopeo` and mediaType branching): these constraints are the reason
the script looks strict about digests and schema types.

- `skopeo` can copy by digest (`name@sha256:...`) while preserving the original
  manifest digest. Docker/OCI tooling often rewrites manifests during conversion,
  which breaks digest pinning.
- Registries return different schema/media types (OCI index, Docker manifest list,
  v2/v1 manifests). The script inspects the mediaType first and picks a compatible
  output format to avoid accidental conversion and keep multi-arch manifests intact.
- The copy uses `--multi-arch all` so the OCI archive contains the full manifest
  list, not just the local platform. This is required for true airgapped imports.
- `--preserve-digests` keeps the descriptor digests stable; without it, the copied
  manifest can be re-signed or re-encoded and no longer match the pinned digest.
- Format selection is intentional and follows mediaType to minimize schema churn:
  OCI index/manifest -> `oci` then `v2s2` then `v2s1`; Docker manifest list/v2
  -> `v2s2` then `oci` then `v2s1`; Docker v1 -> `v2s1` to avoid silent upgrades.
- The script inspects mediaType with `skopeo inspect --raw` and only falls back to
  `skopeo inspect` if needed, because some registries omit mediaType in the
  standard output.

```bash
# single cluster
nix run .#gen-image-lock -- --cluster kubevirt-cluster-319

# all clusters
nix run .#gen-image-lock-all
```

### Extra images via annotation

When an image is not referenced in manifests, attach it to the owning
HelmRelease/Kustomization with a comma-separated annotation:

```yaml
metadata:
   annotations:
      image-lock/extra-images: "longhornio/longhorn-manager:v1.11.2, longhornio/longhorn-ui:v1.11.2"
```

Optional alternatives:

- Use `--extra-images` for ad-hoc comma/space separated images.
- Use `--extra-images-file` for a file list (json/yaml array or one per line).
- Override the annotation key with `--extra-images-annotation`.

## Secrets Management

> https://fluxcd.io/flux/guides/mozilla-sops/#encrypting-secrets-using-age

We use sops & age to manage secrets, so prerequisites:

```bash
nix shell nixpkgs#sops nixpkgs#age
```

### 1. Generate & add the age key to the cluster

> Generally one age key for one git repository is enough, so you need to generate the age
> key only once.

Generate a new age key first, add the age key into the cluster:

```bash
# generate a new age key
age-keygen -o k8s-gitops.agekey

# add the age key to the cluster
cat k8s-gitops.agekey |
kubectl create secret generic sops-age \
--namespace=flux-system \
--from-file=age.agekey=/dev/stdin
```

> NOTE: You may want to backup the age key in a secure place, as it's the only way to
> decrypt the secrets.

After that, you need to reference the age key in the kustomization config, e.g:

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: test
  namespace: flux-system
spec:
  sourceRef:
    kind: GitRepository
    name: flux-system
  path: ./infra/xxx
  # Add the following decryption config
  # https://fluxcd.io/flux/components/kustomize/kustomizations/#decryption
  decryption:
    provider: sops
    # reference the secret we created before
    secretRef:
      name: sops-age
```

Now, you can encrypt the secrets in the yaml files located in the `infra/xxx` directory,
and fluxcd will decrypt them automatically.

### 2. Encrypt secrets

> https://github.com/getsops/sops?tab=readme-ov-file#49encrypting-only-parts-of-a-file

To encrypt specific values in a yaml file using age's putlic key:

> NOTE: private keyfile is not needed here, it's only used for decryption in cluster.

```bash
# This is the age recipient public key, it's printed when you generate the age key
export AGE_RECIPIENT=age1td0htsklm8xpsvcync3ulwxs82w5a9a03eeq9wwg8pm2mx3t99fqtgyhhs

# Encrypting only specific values in a yaml file
sops --encrypt --age=${AGE_RECIPIENT} \
  --encrypted-regex '^(data|stringData)$' --in-place /path/to/secrets.yaml

# Decrypting the encrypted values
sops --decrypt /path/to/secrets.yaml
```

Examples:

- TODO


### 3. Decrypt secrets

> https://github.com/getsops/sops?tab=readme-ov-file#22encrypting-using-age

Generally, you won't need to decrypt the secrets localy. To decrypt the secrets locally,
you can just replace the encrypted values with the plaintext values, and then encrypt them
again.

If you really need to decrypt the secrets locally, you can use the following command:

```bash
# Specify the private key file path
export SOPS_AGE_KEY_FILE=./k8s-gitops.agekey

# Decrypting the encrypted values
sops --decrypt /path/to/secrets.yaml
```

## TODO

- [ ] Add alert-manager config for fluxcd itself.
- [ ] Web UI for monitoring fluxcd and cluster's status.

## FAQ

See [FAQ](./FAQ.md).

## Cluster Security & Stability

To prevent damage to the cluster, we have to follow some rules:

1. **Do not use `kubectl apply` to apply changes to the cluster.** FluxCD will take care
   of the changes, and it will revert the changes if you apply them manually.
1. **Do not allow push to the `main` branch directly(except flux itself, or more
   accurately, flux's deploy key).** All changes should be made via PRs, and the PRs
   should be reviewed by at least one person.
   - NOTE: if you're using gitlab, the creator of the deploy key will gains the same
     access as the deploy key! So, **please create the deploy key with a separate
     account**.
1. **Do not enable flux's `prune` on critical resources, such as namespaces.** Prune will
   delete the resources that are not defined in the Git repository, which may cause damage
   to the cluster.
1. **Deploy resources that contains finalizers carefully.** Deleting resources with
   finalizers may cause the namespace stuck in `Terminating` status.
1. **Use `dependsOn` in `kustomization.yaml` to control the order of deployment and
   deletion.**
   1. For CRDs provided by operators, you have to delete the CRs first, and then delete
      the operators and namespace, otherwise the namespace will stuck in `Terminating`
      status.
   1. For PV/PVC with `kubernetes.io/pv-protection` finalizer, you have to make sure the
      PV/PVC is not needed anymore, and then delete the finalizer manually.
   1. For operators that adds its admission webhook to the CRs, you have to delete ther CR
      & admission webhook first, and then delete the operator and namespace. Otherwise,
      the CRs will fail to be deleted, and the namespace will stuck in `Terminating`
      status.
1. CI for PRs:
   [fluxcd/flux2-kustomize-helm-example/workflows](https://github.com/fluxcd/flux2-kustomize-helm-example/tree/main/.github/workflows)
1. Be especially careful when using flux to deploy **network plugins**, as network
   failures may prevent flux from accessing the git repositories or pulling the helm
   charts.
1. For the corporate environment, consider spliting gitops repositories & k8s clusters by
   categories. Use multiple git repos & k8s clusters may increase the management overhead,
   but it can also reduce the damage caused by accidents.

## References

- Flux Official Example:
  [fluxcd/flux2-kustomize-helm-example](https://github.com/fluxcd/flux2-kustomize-helm-example)
- [Kustomize Tutorial: Comprehensive Guide For Beginners](https://devopscube.com/kustomize-tutorial/):
  A comprehensive guide for beginners to understand and use Kustomize for Kubernetes
  deployments, but it do not cover all the features of Kustomize.
- [Kustomize Official Examples](https://github.com/kubernetes-sigs/kustomize/blob/master/examples/README.md)
- [Kustomize Official Docs](https://kubectl.docs.kubernetes.io/references/kustomize/)
- [JSON Patch - Docs](https://jsonpatch.com/)
- [Kustomization API - FluxCD](https://fluxcd.io/flux/components/kustomize/kustomizations/)

## LICENSE

[MIT](LICENSE)
