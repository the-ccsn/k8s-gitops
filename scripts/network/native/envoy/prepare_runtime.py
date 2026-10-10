#!/usr/bin/env python3
"""Generate plugin mounts from the pinned Istio chart; no cluster writes."""

import argparse
import hashlib
from pathlib import Path
import struct

import yaml

REPO = Path(__file__).resolve().parents[4]
VERSION = "1.31.1"
PROXY = "docker.io/istio/proxyv2:1.31.1-distroless@sha256:15e6087b4033bc6cfbcddc4b47d93cb0c2ec6f1a4730c349ee1f3308108e4acf"
LOADER = "docker.io/library/busybox:1.37.0@sha256:bdf57e528e45e4433820e045b29b4597825a1c9e38353532d90a01445013f82e"
MODULES = {
    "amd64": (62, "49e1d724a195e987be4f887ed0a816db5c82fae7c776ad48dff60d1dbb1d174c"),
    "arm64": (183, "87d6dbdd647880faf27eac0950695c6b0f85609c5a143351dd8c00a05023d2b7"),
}
RUNTIME_ID = "49e1d724-87d6dbdd"
NODE_MODULE = f"/var/lib/istio/server-timing/{RUNTIME_ID}/server-timing.so"
SCRIPT = """case "$(uname -m)" in
  x86_64) timing_arch=amd64; timing_digest=49e1d724a195e987be4f887ed0a816db5c82fae7c776ad48dff60d1dbb1d174c ;;
  aarch64) timing_arch=arm64; timing_digest=87d6dbdd647880faf27eac0950695c6b0f85609c5a143351dd8c00a05023d2b7 ;;
  *) echo "Unsupported Envoy plugin architecture" >&2; exit 1 ;;
esac
if [ ! -e /runtime/server-timing.so ]; then
  cp "/binaries/server-timing-$timing_arch.so" /runtime/server-timing.next
  printf '%s  %s\\n' "$timing_digest" /runtime/server-timing.next | sha256sum -c -
  chmod 0444 /runtime/server-timing.next
  mv /runtime/server-timing.next /runtime/server-timing.so
fi
printf '%s  %s\\n' "$timing_digest" /runtime/server-timing.so | sha256sum -c -
"""


class LiteralDumper(yaml.SafeDumper):
    pass


def represent_string(dumper, value):
    return dumper.represent_scalar("tag:yaml.org,2002:str", value,
                                   style="|" if "\n" in value else None)


LiteralDumper.add_representer(str, represent_string)


def insert_once(text, marker, replacement):
    if text.count(marker) != 1:
        raise ValueError(f"Pinned template changed: {marker!r}")
    return text.replace(marker, replacement, 1)


def generate(chart, module_dir):
    if yaml.safe_load((chart / "Chart.yaml").read_text())["version"] != VERSION:
        raise ValueError("Plugin templates require the pinned Istio chart")
    for arch, (machine, expected) in MODULES.items():
        blob = (module_dir / f"server-timing-{arch}.module").read_bytes()
        if (blob[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", blob, 18)[0] != machine
                or hashlib.sha256(blob).hexdigest() != expected):
            raise ValueError(f"Unverified {arch} plugin")
    templates = {}
    for name, filename, depth in [
        ("sidecar", "injection-template.yaml", 2),
        ("gateway", "gateway-injection-template.yaml", 2),
        ("kube-gateway", "kube-gateway.yaml", 6),
        ("waypoint", "waypoint.yaml", 6),
    ]:
        template = (chart / "files" / filename).read_text()
        prefix = " " * depth
        marker = prefix + "  volumeMounts:\n"
        mount = (prefix + "  - name: ccsn-server-timing\n" + prefix
                 + "    mountPath: /etc/istio/server-timing/server-timing.so\n"
                 + prefix + "    readOnly: true\n")
        template = insert_once(template, marker, marker + mount)
        proxy_marker = prefix + "- name: istio-proxy\n"
        if template.count(proxy_marker) != 1:
            raise ValueError("Pinned template must contain exactly one proxy")
        before, proxy = template.split(proxy_marker, 1)
        marker = prefix + "  env:\n"
        proxy = insert_once(proxy, marker,
                            marker + prefix + "  - name: ISTIO_META_CCSN_SERVER_TIMING\n"
                            + prefix + f"    value: {RUNTIME_ID}\n")
        template = before + proxy_marker + proxy
        marker = prefix + "volumes:\n"
        template = insert_once(template, marker,
                               marker + prefix + "- name: ccsn-server-timing\n"
                               + prefix + "  hostPath:\n" + prefix + f"    path: {NODE_MODULE}\n"
                               + prefix + "    type: File\n")
        templates[name] = template
    return {
        "global": {"proxy": {"image": PROXY}},
        "sidecarInjectorWebhook": {"templates": templates},
    }


def loader_manifest():
    security = {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True,
                "capabilities": {"drop": ["ALL"]}}
    return {
        "apiVersion": "apps/v1", "kind": "DaemonSet",
        "metadata": {"name": "istio-server-timing", "namespace": "istio-system"},
        "spec": {
            "selector": {"matchLabels": {"app": "istio-server-timing"}},
            "template": {
                "metadata": {"labels": {"app": "istio-server-timing"},
                             "annotations": {"sidecar.istio.io/inject": "false"}},
                "spec": {
                    "automountServiceAccountToken": False,
                    "nodeSelector": {"kubernetes.io/os": "linux"},
                    "tolerations": [{"operator": "Exists"}],
                    "initContainers": [{
                        "name": "install", "image": LOADER,
                        "command": ["sh", "-eu", "-c"], "args": [SCRIPT],
                        "securityContext": {**security, "runAsUser": 0},
                        "resources": {"requests": {"cpu": "1m", "memory": "8Mi"},
                                      "limits": {"memory": "32Mi"}},
                        "volumeMounts": [
                            {"name": "binaries", "mountPath": "/binaries", "readOnly": True},
                            {"name": "runtime", "mountPath": "/runtime"}],
                    }],
                    "containers": [{
                        "name": "ready", "image": LOADER,
                        "command": ["sleep", "infinity"],
                        "securityContext": {**security, "runAsNonRoot": True, "runAsUser": 65534},
                        "resources": {"requests": {"cpu": "1m", "memory": "2Mi"},
                                      "limits": {"memory": "8Mi"}},
                    }],
                    "volumes": [
                        {"name": "binaries", "configMap": {"name": "istio-server-timing-binaries"}},
                        {"name": "runtime", "hostPath": {
                            "path": str(Path(NODE_MODULE).parent), "type": "DirectoryOrCreate"}},
                    ],
                },
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chart", required=True, type=Path)
    parser.add_argument("--module-dir", type=Path,
                        default=REPO / "infra/controllers/networking/base/istio")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--loader-output", type=Path)
    args = parser.parse_args()
    values = generate(args.chart, args.module_dir)
    serialized = yaml.dump(values, Dumper=LiteralDumper, sort_keys=False)
    if args.loader_output:
        args.loader_output.write_text(yaml.dump(loader_manifest(), Dumper=LiteralDumper, sort_keys=False))
    if args.output.exists() and args.output.read_text() == serialized:
        print(f"Runtime values already match: {args.output}")
        return
    args.output.write_text(serialized)
    print(f"Generated four native plugin templates: {args.output}")


if __name__ == "__main__":
    main()
