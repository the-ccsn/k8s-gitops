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

## Shared Registry and Jobservice storage

Registry and Jobservice each run two replicas with RollingUpdate, Kubernetes
rollout defaults, a readiness period, a PodDisruptionBudget and preferred node
spread. They use new, independently provisioned Longhorn RWX claims:

| Workload | Existing source claim | New claim | Size |
| --- | --- | --- | --- |
| Registry | `harbor-registry` | `harbor-registry-rwx` | 100Gi |
| Jobservice logs | `harbor-jobservice` | `harbor-jobservice-rwx` | 5Gi |

Both new claims use `longhorn-backup` and are excluded from Flux pruning. The old
Helm-managed claims already have `helm.sh/resource-policy: keep` and stay available
for rollback. Changing a claim's name creates a new volume; changing a Bound RWO
claim's access mode in place does not perform this migration. PostgreSQL retains
its independent RWO volumes. This change does not make the remaining single
instance components or Dragonfly highly available.

## One-time migration before merge

1. Verify recoverable Longhorn backups of both source volumes and a PostgreSQL
   backup. Verify old claims carry the Helm keep annotation before the upgrade.
2. Create the two new PVCs from `helm-release.yaml`. Verify Bound status, NFS
   clients, cross-node RWX access and the backup recurring-job group.
3. Record the current Registry and Jobservice Pod nodes separately. The source
   claims may be attached to different nodes; do not use an old PVC selected-node
   annotation. Plan sufficient free storage for the retained and new volumes.
4. Enter maintenance: pause new pushes, proxy-cache population, replication,
   garbage collection and other Registry mutations; finish outstanding jobs.
   Suspend reconciliation of Harbor during maintenance, stop both source
   Deployments, and confirm no process can write their volumes. The first storage
   migration needs a maintenance window. Later ordinary rollouts can overlap
   replicas, subject to application/database upgrade compatibility.
5. Run the copy Job below once per table row, substituting its Job name,
   `SOURCE_NODE`, source claim and target claim. Place each Job on its recorded
   source node to avoid moving the source RWO attachment. Source mounts are
   read-only; destination volumes must not serve application writes yet.
   Keep writers stopped through verification and cutover. Do not create the
   completion marker by hand.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: harbor-registry-copy-rwx
  namespace: harbor
spec:
  backoffLimit: 1
  template:
    metadata:
      labels:
        istio.io/dataplane-mode: none
    spec:
      restartPolicy: Never
      nodeSelector:
        kubernetes.io/hostname: SOURCE_NODE
      securityContext:
        runAsNonRoot: true
        runAsUser: 10000
        runAsGroup: 10000
        fsGroup: 10000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: copy
          image: docker.io/library/python:3.14-alpine@sha256:dd4d2bd5b53d9b25a51da13addf2be586beebd5387e289e798e4083d94ca837a
          command: [python3, -c]
          args:
            - |
              import filecmp
              import os
              import pathlib
              import shutil
              import sys

              source, target = pathlib.Path('/source'), pathlib.Path('/target')
              marker = target / '.rwx-migration-complete'
              if marker.exists():
                  print('Already migrated; refusing to overwrite destination data')
                  sys.exit(0)
              skipped = {'lost+found', '.rwx-migration-complete'}
              def inventory(root):
                  return {entry.relative_to(root) for entry in root.rglob('*')
                          if entry.relative_to(root).parts[0] not in skipped}
              for relative in sorted(inventory(source), key=lambda path: (len(path.parts), str(path))):
                  entry, destination = source / relative, target / relative
                  if entry.is_symlink():
                      if not destination.exists() and not destination.is_symlink():
                          destination.symlink_to(os.readlink(entry))
                      elif not destination.is_symlink() or os.readlink(entry) != os.readlink(destination):
                          raise SystemExit('Destination symlink differs; refusing overwrite')
                  elif entry.is_dir():
                      if destination.is_symlink():
                          raise SystemExit('Unexpected destination symlink')
                      destination.mkdir(exist_ok=True)
                      shutil.copystat(entry, destination)
                  else:
                      if destination.is_symlink():
                          raise SystemExit('Unexpected destination symlink')
                      shutil.copy2(entry, destination)
              entries = inventory(source)
              if entries != inventory(target):
                  raise SystemExit('Inventory differs; marker withheld')
              for relative in entries:
                  original, copied = source / relative, target / relative
                  if original.is_symlink():
                      valid = copied.is_symlink() and os.readlink(original) == os.readlink(copied)
                  elif original.is_dir():
                      valid = copied.is_dir() and not copied.is_symlink()
                  else:
                      valid = copied.is_file() and not copied.is_symlink() and filecmp.cmp(original, copied, shallow=False)
                  if not valid:
                      raise SystemExit('Copy verification failed; keep writers stopped')
              with marker.open('w') as output:
                  output.write('verified\n')
                  output.flush()
                  os.fsync(output.fileno())
              print('All copied entries verified; migration complete')
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
          resources:
            requests:
              cpu: 100m
              memory: 64Mi
            limits:
              cpu: 1000m
              memory: 256Mi
          volumeMounts:
            - name: source
              mountPath: /source
              readOnly: true
            - name: target
              mountPath: /target
      volumes:
        - name: source
          persistentVolumeClaim:
            claimName: harbor-registry
        - name: target
          persistentVolumeClaim:
            claimName: harbor-registry-rwx
```

6. Both Jobs must complete before cutover. The new Registry and Jobservice Pods
   block in their migration init container until their own volume has a marker.
   Merge and reconcile the reviewed change, resume Harbor reconciliation, and
   verify both replicas of each workload become Ready. Test existing image pulls,
   authenticated pushes and job-log access before ending maintenance. Validate
   an ordinary rollout and node drain separately. A PDB protects voluntary
   eviction only; it does not protect against every node/storage failure.

A failed partial copy can be retried with a new Job name while writers stay
stopped. A completed target is never overwritten by a rerun. For rollback before
new writes, restore the old claim references and single-replica Recreate strategy.
After new writes, first stop writers and reconcile changed data back to the old
volumes; switching claims alone would lose new blobs or logs. Do not roll back
across an incompatible database schema migration.

Reference: [Harbor Helm high availability guide](https://github.com/goharbor/harbor-helm/blob/main/docs/High%20Availability.md).
