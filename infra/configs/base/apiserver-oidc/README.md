This should cooperate with https://github.com/isning/nix-config/commit/438ed686e10ff3641cd977296b5d58f343c7daa9

For login: 
```sh
OIDC_CLIENT_ID=$(kubectl --context snc -n flux-system get applications.application.logto.m.crossplane.io kubernetes-cluster -o jsonpath='{.metadata.annotations.crossplane\.io/external-name}')
kubectl oidc-login setup --oidc-issuer-url=https://login.ccsn.dev/oidc --oidc-client-id="$OIDC_CLIENT_ID" --oidc-extra-scope profile,roles
```

Use the generated client ID in the API server's OIDC configuration as well.
See [cluster bootstrap](../../../../bootstrap/README.md) for the initialization
and manual Kubernetes configuration steps. Headlamp and Kiali consume this ID
automatically through Flux.

Reference: https://kubernetes.io/docs/reference/access-authn-authz/authentication/#using-authentication-configuration
