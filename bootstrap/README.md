# Bootstrap

This directory contains the Terraform bootstrap flow for a new cluster.

## Prerequisites

- A working kubeconfig for the target cluster.
- The SOPS age private key in `k8s-gitops.agekey`.
- Terraform installed with access to the configured providers.

## Files

- `main.tf` installs Flux and the initial GitOps resources.
- `variables.tf` defines the required inputs.
- `terraform.tfvars.example` is the template for local bootstrap values.

## Bootstrap Flow

1. Copy the example variables file and fill in the real values:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```
2. Set `kubeconfig`, `cluster_name`, and `sops_age_key` in `terraform.tfvars`.
3. Initialize Terraform:
   ```bash
   terraform init
   ```
4. Apply the bootstrap configuration:
   ```bash
   terraform apply -var-file=terraform.tfvars
   ```
5. Verify Flux and the cluster resources after the apply completes.

## Notes

- `bootstrap_revision` should usually match the branch or tag you want Flux to track.
- Keep the age private key out of version control.

For campus ingress, configure OpenWrt port forwarding to `172.30.0.201` and
complete the [OpenWrt DDNS setup](../infra/configs/base/i319-reroute/README.md#dns-and-openwrt-ddns).
The router writes `ingress.319.ccsn.dev` A from its campus-facing IPv4;
ExternalDNS writes AAAA from the Service IPv6. Set up the entry A before
switching existing campus wildcard records to the declared CNAMEs.

TODO: Add bootstrap image and flux controllers image to airgap image lock
