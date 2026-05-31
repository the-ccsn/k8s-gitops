This should cooperate with https://github.com/isning/nix-config/commit/438ed686e10ff3641cd977296b5d58f343c7daa9

For login: 
```sh
kubectl oidc-login setup --oidc-issuer-url=https://login.ccsn.dev/oidc --oidc-client-id=h465htc5ewe0zshhg3ynn --oidc-extra-scope profile,roles
```

Reference: https://kubernetes.io/docs/reference/access-authn-authz/authentication/#using-authentication-configuration
