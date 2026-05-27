# harbor

Harbor is deployed by HelmRelease in this directory.

## Initial login

- Username: `admin`
- Password: `Harbor123`

After first login, change the admin password immediately.

## OIDC

OIDC baseline config is managed by `helm-release.yaml` via `valuesFrom -> core.configureUserSettings`.

Secret `harbor-oidc` (namespace `harbor`) provides a single key:

- `configure-user-settings-json`

The value is a JSON object containing Harbor OIDC settings (including `oidc_client_id` and `oidc_client_secret`).
