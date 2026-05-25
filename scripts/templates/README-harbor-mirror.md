# Harbor Mirror Templates

This folder contains node-level mirror templates for Harbor proxy-cache.

Files:

- `k3s-registries.harbor.example.yaml`
  - target path: `/etc/rancher/k3s/registries.yaml`
- `containerd-hosts.harbor.example.toml`
  - target path: `/etc/containerd/certs.d/<upstream-registry>/hosts.toml`

Supported upstream registries and Harbor projects:

- `docker.io` -> `dockerhub`
- `ghcr.io` -> `ghcr` (Harbor native provider: `github-ghcr`, upstream `https://ghcr.io`)
- `quay.io` -> `quay`
- `registry.k8s.io` -> `registry-k8s`
- `gcr.io` -> `gcr`
- `k8s.gcr.io` -> `gcr`
- `mcr.microsoft.com` -> `mcr`

## How To Test

Test the mirror by pulling the upstream image name on a node that has the mirror
config installed. Do **not** use the Harbor project path as the image reference for
the primary test.

Examples:

```bash
sudo crictl pull ghcr.io/speaches-ai/speaches:latest-cpu
sudo crictl pull docker.io/library/busybox:latest
```

These pulls should be rewritten by the node runtime to Harbor automatically.
If you pull `harbor.319.ccsn.dev/ghcr/...` directly, you are bypassing the mirror
rewrite path and testing Harbor project resolution instead.

## Initialize Proxy Cache Projects

Proxy-cache registries/projects are managed by `tofu-controller` + Terraform:

- Controller install: `infra/pre-controllers/base/tofu-controller`
- Terraform CR: `infra/configs/base/harbor/tofu-terraform.yaml`
- Terraform code: `infra/configs/base/harbor/tf`

Terraform runs in namespace `harbor` and reuses Harbor's existing admin password secret.

- `harbor_username` is set to `admin` via `spec.vars` in `Terraform` CR
- `harbor_password` is read from secret `harbor-admin-auth` via `spec.varsFrom`
- `robot_account_k8s_secret` is read from secret `harbor-k8s-robot-account-auth` via `spec.varsFrom`

If you need upstream registry credentials, add them via `spec.varsFrom` (recommended) or `spec.vars` in the `Terraform` CR.

## k3s

1. Copy template:

```bash
sudo cp scripts/templates/k3s-registries.harbor.example.yaml /etc/rancher/k3s/registries.yaml
```

2. Replace credentials placeholders:

- `__HARBOR_USERNAME__`
- `__HARBOR_PASSWORD__`

3. Restart k3s:

```bash
sudo systemctl restart k3s
```

## containerd

1. Create one `hosts.toml` per upstream registry:

```bash
sudo mkdir -p /etc/containerd/certs.d/docker.io
sudo cp scripts/templates/containerd-hosts.harbor.example.toml /etc/containerd/certs.d/docker.io/hosts.toml
```

2. For each upstream registry, replace:

- `__SERVER__` (example: `https://registry-1.docker.io`)
- `__HARBOR_PROJECT__` (example: `dockerhub`)
- `__BASE64_HARBOR_CREDENTIALS__` (`base64(username:password)`)

3. Restart containerd:

```bash
sudo systemctl restart containerd
```

## Operational Notes

- Use Harbor robot account with pull-only permission.
- Keep proxy-cache projects private if your egress bandwidth is limited.
- Plan yearly manual token rotation if you do not need high-frequency rotate.
- If Harbor uses private CA, install CA cert on nodes and keep `skip_verify = false`.
