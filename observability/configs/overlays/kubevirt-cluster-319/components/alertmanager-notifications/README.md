# Alertmanager notifications

This optional package sends actionable selected alerts to both Telegram and an
Enterprise WeChat group robot. Alertmanager's native Telegram receiver is used
directly. Alertmanager v0.32+'s native custom webhook payload renders the nested
JSON required by the Enterprise WeChat group robot; no adapter is deployed.

The package is referenced by the active cluster overlay. Its Telegram bot is
[@ccsn_up_bot](https://t.me/ccsn_up_bot), targeting the
[General topic](https://t.me/c/1896823188/1) in `chatID: -1001896823188`.
General is selected by omitting `messageThreadID`; explicitly sending `1` is
rejected by Telegram. Telegram and WeCom are separate receivers with separate
least-privilege Secrets, stored only after SOPS encryption. The root route fans
warning and critical alerts out to both channels; `continue: true` on Telegram
allows WeCom to be evaluated as well. Alerts without a recognized severity still
use the warning delivery defaults.

Messages include the group count and up to five shortened summaries to stay
within chat message limits. Query Alertmanager for the complete alert list;
Grafana provides the related metrics, logs and investigation views.

## Notification policy

| Severity | Delivery | First group wait | Group updates | Unchanged reminders |
| --- | --- | --- | --- | --- |
| `critical` | Telegram and WeCom | 30 seconds | 5 minutes | 4 hours |
| `warning` or unspecified | Telegram and WeCom | 1 minute | 10 minutes | 12 hours |
| `info` | No chat notification; the alert remains queryable | — | — | — |

Groups retain the alert name, Kubernetes cluster, workload namespace and severity.
Log alerts use their native `k8s_namespace_name`; messages display it when the
native metric namespace label is absent. No namespace alias is added to alerts.
The channels continue to send resolved notifications.

Two native inhibition rules remove duplicate notifications. A critical alert
suppresses the warning version of the same alert on the same resource, including
the PVC or Collector exporter identity. A component-specific target-down alert
suppresses `ScrapeTargetDown` only for the same cluster, scrape job and instance.
Other resources and unrelated alerts remain independent.

Resource-limit violations remain warnings. Fix the owning controller or workload
configuration rather than excluding infrastructure containers from the rule.
Ordinary error logs are handled by the sustained error-rate rule; only explicit
fatal/critical/panic severity or runtime panic signatures trigger critical log
alerts. Unstructured panic detection requires a Go/Rust runtime signature at the
start of the record. Keyword mentions in queries or documentation do not match.

These GitOps changes do not create, extend or remove Alertmanager silences.
Before an existing broad maintenance silence expires, inspect current alerts and
verify that unresolved resource-limit or component-health findings have owners.

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

## Existing-alert remediation (2026-10-28)

Keep the current global silence until its existing expiry; merging rule changes
does not authorize notifications or workload restarts.

| Finding | Source correction | Remaining runtime work |
| --- | --- | --- |
| Missing limits in Longhorn, CNAO and K3s system Pods | Existing namespace LimitRanges already supply CPU/memory limits and preserve explicit requests | Completed: all active regular/init containers have both limits; both alert expressions are zero. Changing a LimitRange alone does not update existing Pods |
| generic-device-plugin CPU saturation | Raise request/limit to 100m/500m; memory to 32Mi/64Mi | Observe CPU use and throttling after the declarative DaemonSet rollout |
| Six incomplete local-path profiles | Declare actual RWO/filesystem/copy capabilities in CDI profiles | Verify complete=true; node-local storage remains unsuitable for VM live migration |
| CDI default storage degraded | Prefer the existing longhorn-vm class for virtualization, with RWX filesystem/snapshot profile | Verify native status, then a new-volume clone and VM migration; existing PVCs are unchanged |
| Cloudflared request errors | Use scoped Loki error logs instead of an undifferentiated request-error counter | Keep incoming-cancellation diagnostics visible; verify the new rule in Loki and continue investigating other errors |
| Retired default/ubuntu-desktop-demo VMI | No configuration exclusion from resource-limit alerts | Completed separately: VM/VMI/runtime Pod removed; two DataVolumes and four PVCs preserved |

Acceptance must examine live limits, Ready replicas, volume health, metrics
freshness and the corresponding alert expression. A silenced alert disappearing
from notifications is not evidence of a fix. No automatic restart Job, cleanup
script or workload suspension is introduced.

See [the container-limit maintenance runbook](../../../../../runbooks/container-limits.md) for all affected owners, including init containers and the retired VM.
