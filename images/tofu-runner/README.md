# Custom tofu-runner image

This image is built for `tofu-controller` runner pods and pre-bundles required Terraform/OpenTofu providers.

## Why

- Avoid downloading provider binaries at runtime.
- Reduce dependency on outbound network during reconciliation.
- Keep provider installation behavior stable and reproducible.

## What's inside

- Base runner: `ghcr.io/flux-iac/tf-runner:v0.16.3`
- Pre-mirrored provider: `goharbor/harbor` (`~> 3.10`)
- CLI config: `/etc/tofu.rc`
- Runtime env in image: `TF_CLI_CONFIG_FILE=/etc/tofu.rc`

## Build and publish

Use GitHub Actions workflow:

- `.github/workflows/build-tofu-runner.yaml`

Target image:

- `ghcr.io/the-ccsn/k8s-gitops/tf-runner`

Published tags:

- `v0.16.3-custom-YYYYMMDD`
- `sha-<gitsha12>`

Use minute-granularity timestamps for dated tags, e.g. `v0.16.3-custom-YYYYMMDDHHmm`.

`tofu-controller` should pin to a dated tag, and Renovate updates it when a newer dated tag is available.

## Upgrade notes

When bumping runner/provider versions:

1. Update `images/tofu-runner/Dockerfile` base image and/or tofu version source.
2. Update provider constraints in `tf/versions.tf`.
3. Build and push a new image tag via workflow.
4. Update `infra/pre-controllers/base/tofu-controller/helm-release.yaml` runner tag.
5. Refresh image lock files.
