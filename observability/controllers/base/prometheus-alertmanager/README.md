# Alertmanager dashboard

`dashboard.json` uses the official Alertmanager mixin's generated overview from
[Monitoring Mixins](https://github.com/monitoring-mixins/website/blob/7b1f6de899ffdbdf59c807a32cd8a9a514231915/assets/alertmanager/dashboards/alertmanager-overview.json),
pinned to website commit `7b1f6de899ffdbdf59c807a32cd8a9a514231915`.
Its SHA-256 is
`da57c5f4edbeceffa6d4bae8a7b46215088482a99aec6dcb3ffb69c6099655fd`.
The catalog identifies
[`prometheus/alertmanager/doc/alertmanager-mixin`](https://github.com/prometheus/alertmanager/tree/8768aa6f65f1a888b5aa5fbf877cf20ad45d1f61/doc/alertmanager-mixin)
as the source. `LICENSE.dashboard` preserves its Apache 2.0 license from
Alertmanager v0.32.1 commit `8768aa6f65f1a888b5aa5fbf877cf20ad45d1f61`.

The overview retains the upstream panels and integration row repetition: alerts,
received/invalid alerts, sent/failed notifications and delivery latency. Local
bindings preserve UID `alertmanager`, use `victoriametrics`, and scope all panel
and dependent variable queries to the chosen Kubernetes cluster and job. This
replaces the previous dashboard in place. Saved source selections are cleared.
The refresh interval stays at 30 seconds.

No notification routes, credentials or access policies change. Select `telegram`
and `webhook` for our Telegram and WeCom paths. Counters can include integrations
that Alertmanager initializes but does not use; selecting them does not enable
delivery. Latency has no value without observations in the chosen window.

For an update, verify the source hash and recheck the upstream panel queries and
variables against the deployed Alertmanager metrics.
