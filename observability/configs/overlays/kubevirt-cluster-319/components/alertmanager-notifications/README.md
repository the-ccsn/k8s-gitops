# Alertmanager notifications

This optional package sends every selected alert to both Telegram and an
Enterprise WeChat group robot. Alertmanager's native Telegram receiver is used
directly. Alertmanager v0.32+'s native custom webhook payload renders the nested
JSON required by the Enterprise WeChat group robot; no adapter is deployed.

The package is referenced by the active cluster overlay. Its Telegram target is
the forum topic identified by `chatID: -1001896823188` and
`messageThreadID: 1`. Telegram and WeCom are separate receivers with separate
least-privilege Secrets, stored only after SOPS encryption. The root route fans
every alert out to both child routes; `continue: true` on Telegram allows WeCom
to be evaluated as well.

## Credentials and rollout

Both encrypted Secrets are already referenced by this component. Preserve their
names and keys when rotating credentials through the existing SOPS workflow.
Never stage plaintext credentials. Flux reconciles the package after the
monitoring controllers; verify actual firing and resolved delivery after rollout.

Prometheus Operator manages the Alertmanager runtime independently from the
VictoriaMetrics metrics backend. Its matcher strategy is `None` so this
centrally-operated `AlertmanagerConfig` receives node and cross-namespace
alerts. Application-owned
notification routes may still be added as Prometheus `AlertmanagerConfig`
objects, but they must use explicit matchers to avoid becoming another global
receiver.

The installed Prometheus Operator CRD chart serves `AlertmanagerConfig` as
`monitoring.coreos.com/v1alpha1`. The WeCom payload field requires Prometheus
Operator v0.92+ and Alertmanager v0.32+.
