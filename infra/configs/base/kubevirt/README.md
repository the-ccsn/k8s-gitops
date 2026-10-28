# Virtualization storage defaults

CDI owns StorageProfile status; GitOps declares only supported capabilities in
spec. The six local-path classes use node-local hostPath directories and support
ReadWriteOnce/Filesystem with host-assisted copying. They cannot provide RWX,
snapshots or live migration; completing their profiles does not add those features.

`longhorn-vm` is the virtualization default, separate from the Kubernetes default
`longhorn-backup`. Its StorageProfile prefers ReadWriteMany/Filesystem and
snapshot cloning through the existing Longhorn VolumeSnapshotClass. Shared
filesystem access permits KubeVirt disk access during live migration, subject
to the VM's other migration constraints. This uses Longhorn's NFS share-manager,
not its separate migratable Block-volume mode. Nodes must support NFSv4.1.
`longhorn-vm-state` retains its separate existing profile.

Defaults apply to new DataVolumes/PVCs that omit the corresponding fields.
Explicit storage classes, modes and existing volumes are not rewritten. Verify
StorageProfile status and `kubevirt_cdi_storageprofile_info` after reconciliation:
all local-path profiles should become complete; `longhorn-vm` should report
`virtdefault="true"`, `rwx="true"`, `smartclone="true"`, `degraded="false"`.
A new-volume import/clone and a migratable VM are needed to validate actual I/O;
configuration acceptance alone does not prove either operation.

References: [CDI 1.65 StorageProfiles](https://github.com/kubevirt/containerized-data-importer/blob/v1.65.0/doc/storageprofile.md),
[Longhorn 1.11.2 RWX volumes](https://longhorn.io/docs/1.11.2/nodes-and-volumes/volumes/rwx-volumes/).
