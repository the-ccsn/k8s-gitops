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

## New KubeVirt VMs

The completion above is a dated snapshot. New VMs still need their own resource
policy; check the generated `compute` container as well as the VM definition.

KubeVirt 1.8.1 rejects explicit domain CPU/memory requests or limits when the VM
also references an instance type. Use the native instance-type expansion before
adding explicit domain budgets, preserving its guest CPU, memory, device and
preference settings. Do not edit a shared instance type to repair one VM.
See the pinned [CPU](https://github.com/kubevirt/kubevirt/blob/v1.8.1/pkg/instancetype/apply/cpu.go#L103-L113)
and [memory](https://github.com/kubevirt/kubevirt/blob/v1.8.1/pkg/instancetype/apply/memory.go#L67-L87)
conflict checks.

Keep requests explicit when setting limits: the pinned renderer can otherwise
use a memory limit as the memory request. Account for guest hotplug bounds and
let KubeVirt add its calculated memory overhead. Verify the resulting launcher
Pod's resources; guest memory alone is not its full memory footprint.
See the pinned [resource renderer](https://github.com/kubevirt/kubevirt/blob/v1.8.1/pkg/virt-controller/services/renderresources.go#L235-L275).

Updating a VM template does not establish that an existing launcher acquired
limits. Run a server-side dry-run first, then arrange the native rollout and
verify both missing-limit expressions after the replacement Pod is Ready.

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
