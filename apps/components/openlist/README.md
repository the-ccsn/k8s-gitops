# Shared OpenList configuration

The `base` and `share` applications use this HelmRepository and native OIDC
bootstrap ConfigMap. Each application has a dedicated Helm release, Logto App,
credential, API audience, role scopes and network policy in its own directory.

The BFF keeps provider tokens on the server and reevaluates role mappings using
verified access-token claims when refreshing. Native account identities use
issuer and subject; initial usernames use `'oidc:' + claims.sub`. General users
keep their own BasePath and Permission. Guest access uses native guest policy.

Credentials and bootstrap databases are SOPS encrypted. S3 API requests use the
internal gateway, while signed downloads use `https://s3.ccsn.dev`.
