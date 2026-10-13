# Cloudreve

Cloudreve is available at `https://cloud.ccsn.dev`, using the pinned community
OIDC image and the TrueCharts Helm chart. Uploads use the independent private
SeaweedFS S3 bucket `cloudreve`.

Logto users can register through OIDC as ordinary users in group 2, with an
initial 1 GiB quota. Administrators are assigned separately. Local public
registration is disabled. OIDC group mapping applies at registration.

Storage policies, user groups, quotas and administrator accounts are managed
manually in the Cloudreve administration interface. Existing database settings
and accounts are retained; no SQL bootstrap job manages them.

Crossplane supplies OIDC credentials; tracked credentials are SOPS encrypted.
The startup init container writes `conf.ini` and injects the site URL, local
registration setting, signing secret and OIDC provider through environment
variables. Database and cache connections remain managed by Helm.

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

Full-text search uses private Meilisearch and Apache Tika services. Meilisearch
stores its index on a 20 GiB Longhorn volume. The minimal Tika image extracts
text without an OCR installation. Ambient mTLS and AuthorizationPolicy restrict access to Cloudreve’s dedicated
service account; NetworkPolicy permits mesh ingress.
Search connections, document extensions, the 50 MiB extraction limit and the
search switch are supplied through `CR_SETTING_*` environment variables. The
Meilisearch authentication key comes from the SOPS-encrypted `cloudreve-search`
Secret. Vector search is disabled. Cloudreve uses warning-level logging to avoid
printing the search credential through its generic environment override logger.
