# Cloudflare Access

The `cloudflare-access` Application is a third-party Traditional Web client with
the callback `https://the-ccsn.cloudflareaccess.com/cdn-cgi/access/callback`.
Its `UserConsentScopes` resource grants `profile` and `email`; `openid` is implicit.
Users still approve these permissions on the consent screen.

## Provider rollout

`UserConsentScopes` requires `provider-upjet-logto` v0.2.0 or later. The signed
v0.2.0 index digest is pinned in
`infra/pre-controllers/base/crossplane/providers/providers.yaml`. Keep that digest
update in a commit before this SSO configuration, and complete the provider
rollout before deploying these manifests:

1. Verify the published index and both platform signatures against the signed
   release workflow identity.
2. Deploy the verified provider package digest through GitOps.
3. Wait for the provider to become healthy and the
   `userconsentscopes.application.logto.m.crossplane.io` CRD to be Established.
4. Reconcile the `logto` Flux Kustomization and check the Application,
   UserConsentScopes and credential resources are Ready.

Publishing and live reconciliation are separate from local manifest generation.
Do not invent a package digest or deploy the new kind against the old provider.

## Cloudflare setup

After reconciliation, `prod/cloudflare-access-oidc` contains `clientId` and
`clientSecret`. Supply those values to Cloudflare's Generic OIDC identity provider
with scopes `openid email profile`. The discovery URL is
`https://login.ccsn.dev/oidc/.well-known/openid-configuration`.
The Logto application and its allowed user profile scopes are managed by GitOps.
