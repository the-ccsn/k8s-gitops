# Missing container limits

Both CPU and memory limits are required for regular and init containers. Keep
`ContainerCpuLimitMissing` and `ContainerMemoryLimitMissing` enabled until the
actual active Pods are bounded. A namespace LimitRange applies at admission;
updating it does not change an existing Pod. A limit is a per-container ceiling,
not reserved capacity or a namespace-wide quota.

## Verified completion (2026-10-28)

All active regular and init containers have CPU and memory limits. Both
missing-limit alert expressions returned zero after maintenance. The retired
`default/ubuntu-desktop-demo` VM and its runtime objects were removed separately;
its two DataVolumes and four PVCs were preserved.

Namespace admission defaults cover K3s system workloads, CNAO network components
and Longhorn-generated Pods. Explicit component budgets take precedence. The
Longhorn fallback must not be lowered below existing explicit requests; it is
not a recommended budget for every storage sidecar.

## Apply existing defaults to old Pods

Keep this as an operator-led maintenance sequence, not a restart Job or a patch
that competes with the owning operator:

1. Reconcile and verify the namespace LimitRanges before refreshing workloads.
2. Refresh CoreDNS and metrics-server separately. Verify DNS/API metrics and
   readiness before proceeding; each currently has only one replica.
3. Refresh each CNAO DaemonSet separately, verifying node network health between
   owners. Both Multus and OVS init containers must receive the defaults.
4. Refresh Longhorn CSI controller Deployments separately, then its CSI node
   plugin using the existing one-node-at-a-time update strategy. Verify mounted
   volumes and replica health throughout.
5. Schedule engine-image, instance-manager and share-manager maintenance using
   Longhorn's native procedures. Inspect dependencies and active I/O per node or
   volume first. The current engine-image DaemonSet permits 100% unavailability;
   a blanket rollout restart is therefore unsuitable. Do not stop all instance
   managers or share managers together, or delete their owning CRs.

Existing Pods may be resized only after checking Kubernetes support, resize
policy and operator behavior; this runbook does not authorize live mutations,
VM shutdown, deletion or volume disruption.

For future VMs, declare CPU/memory limits in the VM/instancetype workflow.
KubeVirt's native automatic CPU limits and quota-driven automatic memory limits
are options, but namespace-wide ResourceQuota totals are a separate capacity
choice. No arbitrary quota or global VM memory ceiling is introduced here.

## Acceptance

Inspect actual `spec.containers` and `spec.initContainers` limits, not only the
controller template. Preserve explicit requests and device allocations. Require
Ready replicas, healthy DNS/network/storage, fresh scrapes and no unexpected
OOM/restart/throttling increase before the next maintenance step.

Re-evaluate both missing-limit expressions after fresh kube-state-metrics
samples and the five-minute alert duration. The desired result is zero matching
active containers. Silence and
inhibition are not evidence that a missing limit has been fixed.
