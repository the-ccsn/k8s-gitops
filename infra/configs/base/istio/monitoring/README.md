# Istio dashboards

The six JSON dashboards come from the official Istio **1.31.1** release,
commit `190ae921b848ec010b8be4457533837ed8fce258`, matching our Istio version.
Sources are under
[`manifests/addons/dashboards`](https://github.com/istio/istio/tree/190ae921b848ec010b8be4457533837ed8fce258/manifests/addons/dashboards).
`LICENSE.dashboard` preserves the upstream Apache 2.0 license.

| Local file | Upstream file | Upstream SHA-256 |
| --- | --- | --- |
| `istio-mesh.json` | `istio-mesh-dashboard.gen.json` | `d1f8f1f0c61722ffebada80b4ea50a17d99e5dfd62efd658d0f79635437afc74` |
| `istio-service.json` | `istio-service-dashboard.json` | `d2c3881bd82f44965bd124ef5aade6e81b41e05355758a41c6d4d7465e98d3fc` |
| `istio-workload.json` | `istio-workload-dashboard.json` | `0a9b4c2cec355b85fe941db9215467b0ca0bfd85c44598c99fbfe91eb539a1de` |
| `istio-control-plane.json` | `pilot-dashboard.gen.json` | `5a03f45efa32b975ac1dba1b12877c586fb63bbb1da06516dfa56256caa1acc0` |
| `istio-ztunnel.json` | `ztunnel-dashboard.gen.json` | `66b6b15099eb9b497cba8655835f4e8cc485fd0ef61ee8e4ed545ee26553cfe8` |
| `gateway-api.json` | Outbound section of `istio-workload-dashboard.json` | `0a9b4c2cec355b85fe941db9215467b0ca0bfd85c44598c99fbfe91eb539a1de` |

The upstream panels, visualization types and layout are retained. Local bindings:

- Use the existing `victoriametrics` datasource and a `k8s_cluster_name` selector
  in every metric query. Native `source_cluster` and `destination_cluster` retain
  their Istio meanings.
- Replace the existing mesh dashboard at UID `istio-mesh`; keep its title and
  destination `namespace` filter for Kiali links. The additional UIDs match their
  local filenames. Mesh navigation links point to the installed service/workload
  UIDs, rather than upstream tag searches.
- Use the current millisecond latency histogram directly, removing the alternate
  seconds metric branch. Service/workload panels convert milliseconds to seconds
  where their upstream units require it.
- Default the service/workload reporter selector to `source|waypoint`, as used by
  the official mesh dashboard. The destination view remains available. Reporter
  directions are not summed together indiscriminately.
- Identify control-plane/ztunnel processes by their existing `pod` labels rather
  than requiring an additional scrape-time `app` label. Clear saved upstream
  selections and bind explicit query reference IDs.

`gateway-api.json` derives the seven outbound charts from the same pinned
workload source, retaining their types, layout and millisecond-to-second latency
conversion. Its producer scope is the exact selected Gateway API namespace/name;
source/waypoint reporters are selected without destination copies. The four
existing gateway summary charts remain, with the same scope and native units.
Destination options include both HTTP and TCP metrics. The view covers ingress
gateways and ambient waypoints.

`ingress-requests` is a project-specific correlation page for NGINX, Istio,
Cloudflare and Tempo. Its HTTP metric cards select the source reporter on gateway
Pods, excluding waypoint copies from that ingress summary. IDs narrow logs and
sampled ingress spans; metrics remain cluster-level trends. Matching logs/traces
are side by side, while slow/error spans and connector trends are collapsed.
Complete traces open through native Tempo links and the installed Traces Drilldown.
No collection, routing, tracing or access policy changes are introduced here.

Ambient workloads without a waypoint expose L4 telemetry. Their HTTP charts can
be empty, and destination-side HTTP charts require a destination L7 reporter.
Do not synthesize metrics or enable sidecars merely to populate a chart.

To update, fetch the pinned upstream files, verify their hashes, reapply these
bindings and validate the active Kustomize output, variables, units and panel
queries. Preserve UIDs and the Kiali namespace filter.
