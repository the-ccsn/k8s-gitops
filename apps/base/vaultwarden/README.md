# Vaultwarden rolling updates

Vaultwarden keeps one steady-state replica. Updates use Kubernetes' default
rolling update limits and ten seconds of readiness before replacing the old Pod. The
old container waits ten seconds before graceful shutdown to allow endpoint
changes to propagate. The chart's startup/readiness probes remain enabled.

Both Pods use external PostgreSQL and the same Longhorn RWX `/data` volume,
including the existing RSA keys and any attachments or Sends. This avoids
cross-node RWO attachment conflicts and generating a different signing key.
WebSocket state is process-local: notifications and device approval can be
affected during the overlap, and clients may need to reconnect. This is not
a guarantee of transparent failover or compatibility across database migrations.

The chart-managed old RWO PVC stays in the Helm release, with a keep annotation.
The standalone RWX PVC is excluded from Flux pruning. Neither is removed by
this change. The new Pod cannot start Vaultwarden until a migration completion
marker and both existing RSA key files are present.

## One-time migration before merging

1. Use the kubevirt cluster and verify a recoverable PostgreSQL backup and an
   independent Longhorn backup of the existing data volume.
2. Create `vaultwarden-vaultwarden-data-rwx` in `prod` from the PVC document in
   `helm-release.yaml`. Verify it is Bound, NFS clients are available on all
   application nodes, and its backup job group is retained.
3. Quiesce attachment uploads, file Sends, admin configuration changes and other
   `/data` mutations for the final copy. A maintenance window may be needed for
   this first migration; the rolling update configuration does not itself
   guarantee a zero-downtime storage migration. Password data remains in the
   existing PostgreSQL cluster.
4. Create the following migration Job. Pod affinity places it alongside the old
   Vaultwarden Pod, allowing the source RWO volume to remain attached. The source
   is mounted read-only. The destination must not serve application writes yet.
   On a failed partial copy, correct the cause and rerun with a new Job name while
   writes remain quiesced. Do not write the marker by hand.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: vaultwarden-copy-rwx
  namespace: prod
spec:
  backoffLimit: 1
  template:
    metadata:
      labels:
        app.kubernetes.io/name: vaultwarden-data-migration
        istio.io/dataplane-mode: none
    spec:
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      affinity:
        podAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app.kubernetes.io/name: vaultwarden
                  app.kubernetes.io/instance: vaultwarden
              topologyKey: kubernetes.io/hostname
      containers:
        - name: copy
          image: docker.io/library/python:3.14-alpine@sha256:dd4d2bd5b53d9b25a51da13addf2be586beebd5387e289e798e4083d94ca837a
          command: [python3, -c]
          args:
            - |
              import filecmp
              import pathlib
              import shutil
              import sys

              source, target = pathlib.Path('/source'), pathlib.Path('/target')
              marker = target / '.rwx-migration-complete'
              if marker.exists():
                  if all(filecmp.cmp(source / key, target / key, shallow=False)
                         for key in ('rsa_key.pem', 'rsa_key.pub.pem')):
                      print('Migration already complete; existing signing keys match')
                      sys.exit(0)
                  raise SystemExit('Signing keys differ; refusing to overwrite a migrated destination')
              for key in ('rsa_key.pem', 'rsa_key.pub.pem'):
                  if not (source / key).is_file() or not (source / key).stat().st_size:
                      raise SystemExit('Existing RSA key is missing; refusing migration')
              # Caches and temporary uploads are regenerated; durable files are copied.
              skipped = {'lost+found', 'icon_cache', 'tmp', '.rwx-migration-complete'}
              for entry in source.iterdir():
                  if entry.name in skipped:
                      continue
                  destination = target / entry.name
                  if entry.is_dir():
                      shutil.copytree(entry, destination, dirs_exist_ok=True)
                  else:
                      shutil.copy2(entry, destination)
              for entry in source.rglob('*'):
                  if entry.relative_to(source).parts[0] in skipped:
                      continue
                  if entry.is_file() and not filecmp.cmp(entry, target / entry.relative_to(source), shallow=False):
                      raise SystemExit('Copy verification failed; keep writes quiesced and retry')
              marker.write_text('verified\n')
              print('Durable files and existing RSA keys copied and verified')
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
          resources:
            requests:
              cpu: 50m
              memory: 32Mi
            limits:
              cpu: 500m
              memory: 128Mi
          volumeMounts:
            - name: source
              mountPath: /source
              readOnly: true
            - name: target
              mountPath: /target
      volumes:
        - name: source
          persistentVolumeClaim:
            claimName: vaultwarden-vaultwarden-data
        - name: target
          persistentVolumeClaim:
            claimName: vaultwarden-vaultwarden-data-rwx
```

5. Confirm Job completion and compare the signing keys and durable files without
   printing their contents. Keep file mutations quiesced until the cutover finishes.
6. Merge and reconcile the reviewed PR. Observe the replacement Pod passing its
   migration guard and becoming Ready while the old Pod is still serving. Verify
   login, vault access, attachment/Sends access and client reconnects before
   resuming file mutations. Afterward, test an ordinary rollout and check for
   failed requests throughout the update.

For rollback before any RWX writes, restore the Deployment's old claim reference.
After RWX has accepted writes, first quiesce and reconcile those durable files
back to the old volume; switching claims alone would lose the new files. Do not
roll back across an incompatible PostgreSQL schema migration.

References: [Vaultwarden multi-instance discussion](https://github.com/dani-garcia/vaultwarden/discussions/2691),
[device approval limitation](https://github.com/dani-garcia/vaultwarden/discussions/5796),
[Longhorn RWX](https://longhorn.io/docs/1.11.1/nodes-and-volumes/volumes/rwx-volumes/).
