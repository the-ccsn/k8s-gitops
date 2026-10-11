# Cloudreve

Cloudreve is available at `https://cloud.ccsn.dev`, using the pinned community
OIDC image and the TrueCharts Helm chart. Uploads use the independent private
SeaweedFS S3 bucket `cloudreve`.

Logto users can register through OIDC as ordinary users in group 2, with an
initial 1 GiB quota. Administrators are assigned separately. Local public
registration is disabled. OIDC group mapping applies at registration.

The local recovery administrator is `cloudreve-recovery@ccsn.dev`. Its initial
password is in Secret `prod/cloudreve-bootstrap`, key `adminPassword`. Bootstrap
leaves an existing administrator password unchanged. Crossplane supplies OIDC
credentials; tracked credentials are SOPS encrypted. Master settings are
injected through the managed environment at startup.

Chart-managed PostgreSQL and Valkey are disabled. Independent CRs configure
the application database and cache:

- `cloudreve-pg-cluster`: two PostgreSQL 18 instances from
  `postgresql-minimal-trixie`, with 5 GiB Longhorn data volumes, continuous WAL
  archiving and daily backups. Backups use the `cloudreve/` prefix in the R2
  bucket `vaultwarden-pg-backup`, with 14-day retention.
- `cloudreve-dragonfly`: one operator-managed Dragonfly instance with
  authenticated access, 512 MB maximum data memory and a 1 GiB Longhorn
  snapshot volume. Snapshots run every five minutes.

Cloudreve connects to `cloudreve-pg-cluster-rw:5432` and
`cloudreve-dragonfly:6379`. Database and cache passwords are Secret references.
The startup init container uses `valkey-cli` for authenticated cache readiness.
