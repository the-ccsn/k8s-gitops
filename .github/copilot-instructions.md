# Copilot Instructions

## Repository Overview

This is a **GitOps repository** for personal Kubernetes clusters managed by
[FluxCD](https://fluxcd.io/). All cluster state is declared here as YAML; FluxCD
continuously reconciles the cluster to match what is committed.

The active cluster is **`kubevirt-cluster-319`** (a KubeVirt-based homelab). Clusters are
provisioned separately via
[isning/nix-config](https://github.com/isning/nix-config/tree/main/hosts/k8s).

---

## Directory Layout

```
.
├── clusters/               # Per-cluster FluxCD entry points
│   └── kubevirt-cluster-319/     # Kustomizations that wire infra → apps → vms together
├── infra/                  # Cluster-wide infrastructure
│   ├── namespaces/         # Namespace definitions (prune: false — never auto-delete)
│   ├── pre-controllers/    # Bootstrap-level controllers (Cilium CNI, Flux itself, storage)
│   ├── controllers/        # Operators & Helm releases (cert-manager, kubevirt, istio, …)
│   └── configs/            # CRs that depend on controllers (gateways, issuers, tunnels, …)
├── apps/                   # Application workloads
│   ├── base/               # Reusable base manifests
│   └── overlays/           # Per-cluster overlays (prod / staging environments)
├── vms/                    # KubeVirt VirtualMachine definitions
│   ├── instancetypes/
│   ├── preferences/
│   ├── nixos/
│   ├── windows/
│   └── k8s/
├── scripts/validate.sh     # CI validation script (kustomize build + kubeconform)
├── Justfile                # Developer shortcuts (requires Nushell)
└── gen_kustomization.nu    # Nushell script to auto-generate kustomization.yaml files
```

### Deployment order (via `dependsOn`)

`infra-namespaces` → `infra-pre-controllers` → `infra-controllers` → `infra-configs` →
`apps` (and `vms` in parallel with apps)

---

## Key Conventions

### Kustomize base / overlay pattern

- **`base/`** – reusable, cluster-agnostic manifests.
- **`overlays/<cluster>/`** – cluster-specific patches and composition. Always reference
  bases with relative paths (e.g., `../../base/podinfo/`).
- Every directory that contains YAML resources **must** have a `kustomization.yaml`.
- Auto-generate `kustomization.yaml` files with `just genks` (runs `gen_kustomization.nu`
  via Nushell). Do not maintain them manually when the script can do it.

### FluxCD Kustomizations (`clusters/`)

Files in `clusters/<name>/` are pure FluxCD `Kustomization` CRs. When adding a new
layer, follow the existing pattern: set `interval`, `retryInterval`, `timeout`,
`sourceRef`, `path`, `prune`, and `dependsOn` as appropriate. For critical infra
(`pre-controllers`, namespaces) always set `prune: false`.

### Secrets — SOPS + age encryption

**Never commit plaintext secrets.** All Kubernetes `Secret` resources must be
SOPS-encrypted before committing.

```bash
# AGE_RECIPIENT is the public key printed during initial cluster bootstrap
export AGE_RECIPIENT=age167wn2qepdh87r0fqks69s0em09fkve4nrpuuxdrvgdr0dfmqpf2q08uzxn

# Encrypt only data/stringData fields in-place
sops --encrypt --age=${AGE_RECIPIENT} \
  --encrypted-regex '^(data|stringData)$' --in-place path/to/secret.yaml
```

An encrypted secret looks like:

```yaml
stringData:
  apiToken: ENC[AES256_GCM,data:...,type:str]
sops:
  age:
    - recipient: age167wn2qepdh87r0fqks69s0em09fkve4nrpuuxdrvgdr0dfmqpf2q08uzxn
      enc: |
        -----BEGIN AGE ENCRYPTED FILE-----
        ...
        -----END AGE ENCRYPTED FILE-----
  encrypted_regex: ^(data|stringData)$
  version: 3.11.0
```

The FluxCD Kustomization that consumes the secret must declare:

```yaml
decryption:
  provider: sops
  secretRef:
    name: sops-age
```

### Helm releases

Helm controllers and their repos live under `infra/controllers/base/<name>/`. A typical
entry contains `helm-repo.yaml` (HelmRepository) + `helm-release.yaml` (HelmRelease) +
`kustomization.yaml`. OCI chart URLs must not have a `v` prefix in tags (Flux limitation
— see FAQ).

### Namespaces

Defined once in `infra/namespaces/` and **never pruned**. Available namespace labels:

- `apps.yaml` → `prod`, `staging`
- `controllers.yaml` → controller/operator namespaces
- `vms.yaml` → VM namespaces

---

## CI / Validation

The GitHub Actions workflow (`.github/workflows/test.yaml`) runs on every push:

1. **yq** – validates all YAML files are well-formed.
2. **kustomize build** – builds every overlay.
3. **kubeconform** – validates manifests against Flux CRD schemas (Secrets are skipped
   because SOPS fields fail schema validation).

Run locally with:

```bash
./scripts/validate.sh
```

Prerequisites: `yq` v4.34+, `kustomize` v5.3+, `kubeconform` v0.6+.

---

## Developer Tooling

| Tool | Purpose |
|------|---------|
| `flux` CLI | Check reconciliation status, suspend/resume, reconcile manually |
| `kubectl` / `k9s` | Inspect cluster state (read-only; do **not** `kubectl apply` manually) |
| `sops` + `age` | Encrypt / decrypt secrets |
| `just` (Nushell) | `just genks` — regenerate all `kustomization.yaml` files |
| `prettier` | YAML/Markdown formatting (`.prettierrc.yaml`: 90-col, no semi, no single-quotes) |

Useful Flux commands:

```bash
flux get ks          # list Kustomization status
flux get all -A      # all resource status
flux events          # recent reconcile events
flux reconcile ks infra-controllers   # force re-sync a kustomization
flux suspend ks vms && flux resume ks vms
```

---

## Safety Rules (Do Not Violate)

1. **Never `kubectl apply` directly** — Flux will revert manual changes.
2. **Never push to `main` directly** — all changes go through PRs.
3. **Never enable `prune: true` on namespaces** — it will delete live resources.
4. **Always add `dependsOn`** when a resource depends on a CRD provided by an operator;
   Flux deletes in reverse dependency order, preventing stuck `Terminating` namespaces.
5. **Encrypt secrets before committing** — use `sops` as described above.
6. **Be careful with network plugins** (Cilium) — misconfiguration can cut off Flux from
   Git/Helm sources.

---

## Common Pitfalls & Workarounds

- **OCI Helm chart 401**: URL path is likely wrong; OCI prefix must be separate from the
  image name.
- **`unable to locate any tags`**: Remove `v` prefix from OCI image tags (Flux does not
  support it).
- **Namespace stuck in `Terminating`**: CRs must be deleted before their operator. Use
  `dependsOn` in FluxCD Kustomizations. See `FAQ.md` for KubeVirt-specific workarounds
  (delete stale apiservice entries).
- **`kustomize.toolkit.fluxcd.io/ssa: Merge`**: Add to resources whose fields you need
  to change manually without Flux reverting them (e.g., `spec.replicas`).
- **Force-recreate a resource**: Add annotation
  `kustomize.toolkit.fluxcd.io/force: "Enabled"` to the resource or via a
  `kustomization.yaml` patch.

---

## Adding a New Application

1. Create `apps/base/<app-name>/` with manifests + `kustomization.yaml`.
2. Reference it from the appropriate overlay:
   `apps/overlays/kubevirt-cluster-319/{prod,staging}/kustomization.yaml`.
3. If the app needs its own namespace, declare it in `infra/namespaces/apps.yaml`.
4. If the app requires secrets, encrypt them with `sops` before committing.
5. Run `./scripts/validate.sh` locally before opening a PR.

## Adding a New Controller / Operator

1. Create `infra/controllers/base/<name>/` with `helm-repo.yaml`, `helm-release.yaml`,
   `kustomization.yaml`.
2. Add it to `infra/controllers/overlays/kubevirt-cluster-319/kustomization.yaml`.
3. If the operator provides CRDs, place the corresponding CRs in `infra/configs/` (not
   `infra/controllers/`) so `dependsOn` ordering is respected.
