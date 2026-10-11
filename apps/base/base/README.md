# Base

Base at `https://base.ccsn.dev`, with a dedicated
Helm release, Logto application, API resource, credential, roles and network policy.

Role scopes: `base:admin`, `base:general`, `base:guest`. Verified
access-token claims drive the native CEL role mapping; initial usernames use
`'oidc:' + claims.sub`, while account binding uses issuer and subject.

Base permits anonymous browsing and downloads using the native guest account,
with uploads and file management disabled. The Helm bootstrap enforces guest
access to `/buctbase` with permission `0`, keeping other mounts private. Existing authenticated accounts retain their
BasePath and Permission values.

S3 API traffic uses the internal gateway; signed downloads keep the public S3
domain. OIDC uses the shared native bootstrap component in `../../components/openlist`.
