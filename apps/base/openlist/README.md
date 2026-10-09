# OpenList

Two Helm-managed OpenList v4.2.6 instances replace the OMV web frontends.

| Instance | Hostname | Storage and access |
| --- | --- | --- |
| Private | alist.ccsn.dev | Authenticated access; `/buctbase` and `/share` use SeaweedFS S3. Existing accounts and path permissions are retained. |
| Public | share.ccsn.dev | SeaweedFS `share` bucket at `/`; anonymous read access. The S3 credential permits only read/list on this bucket. |

S3 uses `https://s3.ccsn.dev`, path-style addressing, region `us-east-1`, and one-hour presigned download URLs. Uploads pass through the private instance. Secrets are SOPS-encrypted; bootstrap copies the migrated SQLite database only into an empty PVC and injects the generated Logto credentials. Existing databases are preserved on redeploy.

Both applications use native Logto OIDC with stable `sub` identifiers. The existing administrator is bound to the owner's Logto subject. Private automatic registration is disabled; existing users can bind their identities through their profile. Public automatic registration creates read-only users. Interactive owner login still requires user verification; authorization redirects and callback URLs have been checked.

The private `/host/srv/mergerfs/share` mount uses the AList V3 driver to reach the existing OMV AList instance with a dedicated path-scoped bridge account. Keep this legacy container running until the remaining NAS data has moved. Its web frontend is no longer the domain backend. The old public AList can be stopped after cutover verification; retain its data for recovery.

The existing public share maps exactly to the SeaweedFS `share` bucket contents. Original NAS files are retained.

## Operational checks

Verify both HelmReleases and pods in namespace `prod`, route backend references, authenticated private listing/upload, anonymous private denial, public read access and write denial, and both OIDC authorization redirects.

Native S3 correctly honors Range requests, including a 1 GiB object. At migration time Cloudflare returned a full HTTP 200 for that object's presigned Range request, while smaller objects returned 206. Further diagnosis needs Cache Rules permission: enable Origin Range Requests while preserving caching. The owner explicitly requests Cloudflare cache utilization; do not add bypass rules. Current automation credentials cannot edit Cache Rules. Do not treat successful bounded byte reads as proof of public range support.

`public-dns.yaml` preserves the public share CNAME through external-dns. An old explicit record pointed at the legacy OMV tunnel and bypassed the Kubernetes gateway; migration updates it to `prod.ingress.ccsn.dev`. The private hostname uses the existing production wildcard.
