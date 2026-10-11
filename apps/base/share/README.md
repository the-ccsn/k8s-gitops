# Share

Share at `https://share.ccsn.dev`, with a dedicated
Helm release, Logto application, API resource, credential, roles and network policy.

Role scopes: `share:admin`, `share:general`, `share:guest`. Verified
access-token claims drive the native CEL role mapping; initial usernames use
`'oidc:' + claims.sub`, while account binding uses issuer and subject.

Share permits anonymous read access using the native guest restrictions.

S3 API traffic uses the internal gateway; signed downloads keep the public S3
domain. OIDC uses the shared native bootstrap component in `../../components/openlist`.
