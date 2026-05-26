# Cilium BGP LB

This directory implements a LoadBalancer setup based on the Cilium BGP Control Plane.

It is split into three layers: Cilium allocates VIPs for Services, FRR advertises those VIPs to the upstream router, and OpenWrt fills in the IPv6 NDP proxy part.

The goals are straightforward:

1. Keep Service LoadBalancerIPs independent of cloud providers or external LBs.
2. Advertise only the VIPs that should be exposed to the upstream network.
3. Make IPv6 VIPs resolvable and forwardable on the router side.

The exact address pools and peer addresses depend on the cluster deployment, so the examples below use placeholders instead of fixed values.

## How it works

### VIP allocation

[cilium-ip-pools.yaml](cilium-ip-pools.yaml) defines two address pools:

- IPv4 pool: <LB_IPV4_POOL>
- IPv6 pool: <LB_IPV6_POOL>

Cilium assigns addresses for LoadBalancer Services from these pools. This stage only decides which VIP a Service gets, not whether that VIP is reachable externally.

### BGP advertisement

[cilium-bgp-auth.yaml](cilium-bgp-auth.yaml) provides the BGP peer authentication secret, and [cilium-bgp-eip-lb.yaml](cilium-bgp-eip-lb.yaml) defines the BGP behavior:

- Only nodes with the node-role.kubernetes.io/lb-gateway label participate in advertisements.
- Nodes establish BGP sessions from the ovsbr1 layer-3 uplink interface.
- Each node peers with the main router over both IPv4 and IPv6.
- Only Service advertisements labeled advertise: bgp are published.

This keeps VIP allocation and VIP advertisement as two independent controls.

### Upstream routing

The upstream FRR router only accepts routes within the configured prefix ranges:

- IPv4 only allows prefixes inside <LB_IPV4_POOL>
- IPv6 only allows prefixes inside <LB_IPV6_POOL>

This prevents accidental cluster-side misconfiguration from injecting unrelated networks into the core network.

### IPv6 NDP proxy

For IPv4, BGP routing is enough. For IPv6, the router also needs to answer NDP correctly. The OpenWrt script watches IPv6 route changes learned from FRR and automatically adds or removes the corresponding proxy neighbor entries.

In short: BGP tells the router that the address lives here, and NDP proxy makes the router able to send packets there.

## 流量路径

The typical traffic path is:

1. A user accesses the VIP of a LoadBalancer Service.
2. The upstream router uses the BGP route learned from FRR and sends the traffic to the cluster edge.
3. Cilium on the matched node receives the VIP traffic and forwards it to the backend Pod.
4. For IPv6 traffic, the router also relies on NDP proxy to find a reachable next hop.

## Notes

In this setup, Kubernetes only declares intent; network reachability is completed by BGP and NDP proxy.

If you only look at the Cilium config, it looks like a normal LoadBalancer address pool. Once you include FRR and OpenWrt, you can see how those VIPs are carried to the upstream router.

## Router setup

The following is the reference upstream router configuration. It limits the accepted prefixes and establishes BGP peering with the Cilium nodes.

```
ip prefix-list K8S-CLUSTER-VIP seq 10 permit <LB_IPV4_POOL> le 32
!
ipv6 prefix-list K8S-CLUSTER-VIP6 seq 10 permit <LB_IPV6_POOL> le 128
!
route-map K8S-CLUSTER-IN-V4 permit 10
 match ip address prefix-list K8S-CLUSTER-VIP
exit
!
route-map K8S-CLUSTER-IN-V4 deny 100
exit
!
route-map K8S-CLUSTER-IN-V6 permit 10
 match ipv6 address prefix-list K8S-CLUSTER-VIP6
exit
!
route-map K8S-CLUSTER-IN-V6 deny 100
exit
!
password zebra
!
router bgp 65000
 bgp router-id <ROUTER_ID>
 neighbor K8S-CLUSTER peer-group
 neighbor K8S-CLUSTER remote-as <CILIUM_NODE_ASN>
 neighbor K8S-CLUSTER password <BGP_PASSWORD>
 bgp listen range <ROUTER_IPV4_LISTEN_RANGE> peer-group K8S-CLUSTER
 bgp listen range <ROUTER_IPV6_LISTEN_RANGE> peer-group K8S-CLUSTER
 !
 address-family ipv4 unicast
  neighbor K8S-CLUSTER route-map K8S-CLUSTER-IN-V4 in
 exit-address-family
 !
 address-family ipv6 unicast
  neighbor K8S-CLUSTER activate
  neighbor K8S-CLUSTER route-map K8S-CLUSTER-IN-V6 in
 exit-address-family
exit
```

## OpenWrt NDP proxy

The following two files are the router-side helpers that automatically convert FRR-learned IPv6 VIPs into proxy NDP state.

`/etc/init.d/frr-ndp-sync` runs the script as a long-lived procd service.

```sh
#!/bin/sh /etc/rc.common
START=99
STOP=10
USE_PROCD=1

PROG="/usr/bin/frr-ndp-sync.sh"

start_service() {
    echo "Starting FRR-NDP Sync Script..."
    procd_open_instance
    procd_set_param command "$PROG"

    procd_set_param respawn 3600 5 0

    procd_set_param stdout 1
    procd_set_param stderr 1

    procd_close_instance
}

stop_service() {
    echo "Stopping FRR-NDP Sync Script..."
}
```

`/usr/bin/frr-ndp-sync.sh` watches route changes, runs `ip -6 neigh add proxy ...` when a new VIP appears, and removes the proxy entry when the route is withdrawn.

```sh
#!/bin/sh

EXT_IF="wan"
VIP_PREFIX="<LB_IPV6_POOL_PREFIX>"

echo "[$(date)] OpenWrt FRR-NDP auto proxying starting..."

ip -6 monitor route | grep "$VIP_PREFIX" | grep -E "proto zebra|proto 186|proto bgp" | while read -r line; do

    if echo "$line" | grep -q "Deleted"; then
        ACTION="del"
        TARGET_IP=$(echo "$line" | awk '{print $2}')
    else
        ACTION="add"
        TARGET_IP=$(echo "$line" | awk '{print $1}')
    fi

    TARGET_IP=$(echo "$TARGET_IP" | cut -d'/' -f1)

    echo "[$(date)] Route change detected, ($ACTION) NDP proxy $TARGET_IP"
    ip -6 neigh "$ACTION" proxy "$TARGET_IP" dev "$EXT_IF" 2>/dev/null
done
```

The key idea is to sync neighbor entries from BGP route changes. That way VIPs can be advertised to the upstream router without proxying the entire IP block with `ndppd`.
