# OpenList

Two Helm-managed OpenList v4.2.6 instances replace the OMV web frontends.

| Instance | Hostname | Storage and access |
| --- | --- | --- |
| Private | alist.ccsn.dev | Authenticated access; `/buctbase` and `/share` use SeaweedFS S3. Existing accounts and path permissions are retained. |
| Public | share.ccsn.dev | SeaweedFS `share` bucket at `/`; anonymous read access. The S3 credential permits only read/list on this bucket. |

Server-side S3 metadata, listing and uploads use the existing internal gateway `http://192.168.1.22:8333`. Download links use the separate signed custom host `https://s3.ccsn.dev`, path-style addressing, region `us-east-1`, and one-hour presigned URLs. This preserves public CDN caching while avoiding Cloudflare HEAD handling that caused S3 signature verification to return 403. Bootstrap also updates these managed SeaweedFS mount endpoints on existing PVCs; unrelated storage is preserved. Uploads pass through the private instance. Secrets are SOPS-encrypted; bootstrap copies the migrated SQLite database only into an empty PVC and injects the generated Logto credentials. Existing databases are preserved on redeploy.

Both applications use native Logto OIDC with stable `sub` identifiers. The existing administrator is bound to the owner's Logto subject. The Helm-managed authorization sidecar verifies every authenticated SSO session against current Logto roles: `base:admin` grants access only to the private app, and `share:admin` only to the public app. Neither role is assigned by default. Assign the exact role to an external user in Logto before granting private access. Role decisions expire after 30 seconds; identity-provider failures do not reuse expired positive decisions. Existing scoped local accounts retain their file permissions, while public anonymous access remains read-only.

Role holders can view storage mounts, settings, metadata and users through the management UI. Secret values are redacted, and all configuration mutations under `/api/admin` are rejected by the server, including requests by the original administrator. Configuration changes belong in this Helm/GitOps directory. Native admin privileges remain internal to the configuration reader; newly registered SSO users receive file-management permissions without a native admin role. Public S3 remains read-only at the bucket credential. Existing S3 download URLs can remain usable until their one-hour signature expires.

Both apps permit native SSO registration, but the sidecar checks the required app role before releasing a login token. Registered sessions without that role cannot access authenticated endpoints. Bound users cannot remove their SSO binding to bypass future role revocation. The Service routes HTTP to sidecar port 5246. NetworkPolicy and Istio AuthorizationPolicy block direct access to native ports 5244/5245. Kubernetes operators with pod-exec or port-forward privileges remain trusted infrastructure administrators. The native UI can still display edit controls; attempted saves receive HTTP 403.

The private `/host/srv/mergerfs/share` mount uses the AList V3 driver to reach the existing OMV AList instance with a dedicated path-scoped bridge account. Keep this legacy container running until the remaining NAS data has moved. Its web frontend is no longer the domain backend. The old public AList can be stopped after cutover verification; retain its data for recovery.

The existing public share maps exactly to the SeaweedFS `share` bucket contents. Original NAS files are retained.

## Operational checks

Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s apps/base/openlist -p 'test_authorization.py' -v` for the gateway integration checks. After editing `authorization.py`, update the ConfigMap copy and both HelmRelease `ccsn.dev/authorization-sha256` annotations so reconciliation restarts the sidecars.

Roll out the ConfigMap and HelmRelease changes first, wait for both two-container pods to become ready, then enforce the native-port policies. Verify configuration reads redact credentials, configuration writes return 403, unrelated app roles fail authorization, existing local path restrictions remain intact, public anonymous listing still works, and direct native-port requests are denied.

Native S3 correctly honors Range requests, including a 1 GiB object. At migration time Cloudflare returned a full HTTP 200 for that object's presigned Range request, while smaller objects returned 206. Further diagnosis needs Cache Rules permission: enable Origin Range Requests while preserving caching. The owner explicitly requests Cloudflare cache utilization; do not add bypass rules. Current automation credentials cannot edit Cache Rules. Do not treat successful bounded byte reads as proof of public range support.

`public-dns.yaml` preserves the public share CNAME through external-dns. An old explicit record pointed at the legacy OMV tunnel and bypassed the Kubernetes gateway; migration updates it to `prod.ingress.ccsn.dev`. The private hostname uses the existing production wildcard.
