# OMV SeaweedFS metrics

These complete Portainer Stacks prepare authenticated metrics for SeaweedFS
4.48. They are external-host configuration, not Kustomize resources. Both keep
startup commands and NGINX configuration inline; no new startup script or custom
image is required. Existing data mounts, disk guards and S3 authentication-file
references come from the reviewed OMV configuration on 2026-10-31.

| Stack | Metrics listener | Native backends |
| --- | --- | --- |
| `seaweedfs.yaml` | `openmediavault.local:9443` | master, filer, ordinary S3 and six volume servers |
| `seaweedfs-s3-exposure.yaml` | current `lan0` IPv4 address, port 9443; queried as `s3.ccsn.dev` | direct S3 |

The existing gateways use different network namespaces. Each therefore has one
NGINX frontend; the direct frontend shares the S3 service's namespace. Native
metrics bind only to `127.0.0.1` in their respective namespaces. The public S3
HTTP/HTTPS listeners and their dual-stack configuration remain independent.
Both frontends require the dedicated CA and exact client subject
`CN=vmagent-seaweedfs-metrics`. Only GET requests to the enumerated metrics paths
are proxied; arbitrary targets, query strings and application endpoints are not
exposed. Client headers and bodies are not forwarded. Each new frontend has a
0.25 CPU / 128 MiB hard limit and a 16 MiB temporary filesystem.

## Certificates and renewal

`../monitoring/metrics-certificates.yaml` provisions a dedicated namespaced CA,
a 90-day server certificate for `openmediavault.local` and `s3.ccsn.dev`, and a
90-day client certificate. Leaf renewal starts 15 days before expiry. The CA key
and client key stay in `monitoring`; OMV's existing `prod/omv-s3-cert-reader`
identity receives only `get` on `monitoring/seaweedfs-metrics-server-tls`.

The exposure Stack's existing controller runs an inline certificate worker next
to its existing network/DNS/certificate supervision. It reads the existing
`cert-reader.json` at runtime, verifies the API TLS certificate, and fetches only
the server Secret. It verifies the key pair, CA chain, both DNS names and at
least one day of validity before replacing the live PEM. The private server
bundle is mode 0640 in a mode-0750 directory; its CA file is public trust data.
Only the two exactly owned metrics containers receive NGINX test/reload calls.
Client-certificate Secret updates use the native monitoring Operator path.

The controller also detects a network-namespace change after an in-place S3
restart and restarts only the direct metrics frontend to rejoin it. Replacing
the S3 container must update its dependent metrics service in the same Compose
operation; `depends_on.restart` covers Compose-managed changes. An in-place
`lan0` address change requires restarting the metrics service to regenerate its
listener. No runtime code restarts a master, filer, volume or S3 data service for
metrics recovery.

The bootstrap CA lasts ten years and retains its key on routine renewal.
Rekeying that CA is a separate trust-bundle rollover: retain overlapping trust
until both leaf certificates and OMV have adopted the replacement. Do not delete
its Secret to attempt automatic rotation.

## Release order

1. Publish only the certificate resources, narrowly scoped Role/RoleBinding and
   these Stack sources first. Keep the existing ScrapeConfig until the OMV
   endpoints are ready. Wait for both leaf Certificates to become Ready and
   verify the existing identity can get the server Secret but cannot get the
   client or CA Secret. Do not print Secret data.
2. Wait for the independently owned EC/volume maintenance to finish. Recompare
   these Stacks with the then-current OMV service configuration; do not overwrite
   maintenance changes. Stage the controller update, verify certificate sync,
   then update data services one at a time in the maintenance window. Each
   native `metricsIp` change requires that service to restart. Confirm readiness
   before proceeding to the next volume. Update direct S3 and its dependent
   metrics service together. A full-stack redeploy can recreate all changed
   volumes together and is unsuitable for this sequence.
3. Before switching collection, verify all ten authenticated routes, rejection
   without a client certificate, rejection of a different subject and closure of
   the old LAN metrics ports. Then publish the HTTPS ScrapeConfig and its alert
   changes separately. No suspension fields are required.
4. Accept ten `up == 1` targets, effective TLS configuration, per-volume disk/QPS
   and latency panels, distinct S3 instances, alert evaluation and a leaf renewal.
   Direct requests must use the internal DNS answer for `s3.ccsn.dev`; no fixed
   address or `s3.319.ccsn.dev` target is needed.

```sh
docker compose -f seaweedfs.yaml config --quiet
docker compose -f seaweedfs-s3-exposure.yaml config --quiet
```

Compose's `configs.content` requires version 2.23.1 or newer. `$$` preserves
container-shell and NGINX variables through Compose interpolation; runtime
`envsubst` expands only the listener address. The existing custom network
controller image and its credentials remain external dependencies, not included
as image layers or literal credentials in these files.

References: [Compose inline configs](https://docs.docker.com/reference/compose-file/configs/),
[NGINX client verification](https://nginx.org/en/docs/http/ngx_http_ssl_module.html#ssl_verify_client),
[cert-manager CA lifecycle](https://cert-manager.io/docs/configuration/ca/).
