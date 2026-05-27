CNAO hardcoded cri socket path to /run/crio/crio.sock,
but for k3s, the cri socket path is /run/k3s/containerd/containerd.sock,
so we need to patch the dynamic-networks-controller-ds to change the cri socket path.

Since the dynamic-networks-controller-ds is managed by cluster-network-addons-operator,
we cannot directly patch the ds, so manually instll the multus-dynamic-networks-controller,
and then patch the ds to change the cri socket path.

https://github.com/kubevirt/cluster-network-addons-operator/issues/1846

Without the patch, the dynamic-networks-controller failed to start with the error:
```
~: kubectl describe pod dynamic-networks-controller-ds-gnn42 -n cluster-network-addons
Name:             dynamic-networks-controller-ds-gnn42
Namespace:        cluster-network-addons
Priority:         0
Service Account:  dynamic-networks-controller
Node:             whitefox/192.168.1.101
Start Time:       Tue, 17 Feb 2026 03:42:41 +0800
Labels:           app=dynamic-networks-controller
                  app.kubernetes.io/component=network
                  app.kubernetes.io/managed-by=cnao-operator
                  controller-revision-hash=59c856cd8d
                  name=dynamic-networks-controller
                  pod-template-generation=2
                  prometheus.cnao.io=true
                  tier=node
Annotations:      <none>
Status:           Pending
IP:
IPs:              <none>
Controlled By:    DaemonSet/dynamic-networks-controller-ds
Containers:
  dynamic-networks-controller:
    Container ID:
    Image:         ghcr.io/k8snetworkplumbingwg/multus-dynamic-networks-controller@sha256:2a2bb32c0ea8b232b3dbe81c0323a107e8b05f8cad06704fca2efd0d993a87be
    Image ID:
    Port:          <none>
    Host Port:     <none>
    Command:
      /dynamic-networks-controller
    Args:
      -config=/etc/dynamic-networks-controller/dynamic-networks-config.json
      -v=5
    State:          Waiting
      Reason:       ContainerCreating
    Ready:          False
    Restart Count:  0
    Requests:
      cpu:      100m
      memory:   50Mi
    Liveness:   exec [curl --fail --unix-socket /host/run/multus/multus.sock localhost/healthz] delay=15s timeout=1s period=5s #success=1 #failure=3
    Readiness:  exec [curl --fail --unix-socket /host/run/multus/multus.sock localhost/healthz] delay=15s timeout=1s period=5s #success=1 #failure=3
    Environment:
      NODE_NAME:   (v1:spec.nodeName)
    Mounts:
      /etc/dynamic-networks-controller/ from dynamic-networks-controller-config-dir (ro)
      /host/run/crio/crio.sock from cri-socket (rw)
      /host/run/multus/multus.sock from multus-server-socket (rw)
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-xjpnh (ro)
Conditions:
  Type                        Status
  PodReadyToStartContainers   False
  Initialized                 True
  Ready                       False
  ContainersReady             False
  PodScheduled                True
Volumes:
  dynamic-networks-controller-config-dir:
    Type:      ConfigMap (a volume populated by a ConfigMap)
    Name:      dynamic-networks-controller-config
    Optional:  false
  multus-server-socket:
    Type:          HostPath (bare host directory volume)
    Path:          /run/multus/multus.sock
    HostPathType:  Socket
  cri-socket:
    Type:          HostPath (bare host directory volume)
    Path:          /run/crio/crio.sock
    HostPathType:  Socket
  kube-api-access-xjpnh:
    Type:                    Projected (a volume that contains injected data from multiple sources)
    TokenExpirationSeconds:  3607
    ConfigMapName:           kube-root-ca.crt
    Optional:                false
    DownwardAPI:             true
QoS Class:                   Burstable
Node-Selectors:              <none>
Tolerations:                 node.kubernetes.io/disk-pressure:NoSchedule op=Exists
                             node.kubernetes.io/memory-pressure:NoSchedule op=Exists
                             node.kubernetes.io/not-ready:NoExecute op=Exists
                             node.kubernetes.io/pid-pressure:NoSchedule op=Exists
                             node.kubernetes.io/unreachable:NoExecute op=Exists
                             node.kubernetes.io/unschedulable:NoSchedule op=Exists
Events:
  Type     Reason       Age                From               Message
  ----     ------       ----               ----               -------
  Normal   Scheduled    10m                default-scheduler  Successfully assigned cluster-network-addons/dynamic-networks-controller-ds-gnn42 to whitefox
  Warning  FailedMount  8s (x13 over 10m)  kubelet            MountVolume.SetUp failed for volume "cri-socket" : hostPath type check failed: /run/crio/crio.sock is not a socket file
```