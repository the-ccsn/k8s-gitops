#!/usr/bin/env python3
"""Prepare and verify a reviewable Nginx module bundle without changing the base."""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct

import yaml

REPO = Path(__file__).resolve().parents[4]
BASE = REPO / "infra/configs/base/i319-reroute"
CATALOG = REPO / "scripts/network/benchmarks/server-timing-native-probes-2026-10-09.json"
IMAGE = "nginx:mainline-alpine@sha256:5616878291a2eed594aee8db4dade5878cf7edcb475e59193904b198d9b830de"
MODULE = "ngx_http_ccsn_server_timing_module.so"
INIT_SCRIPT = """case "$(uname -m)" in
  x86_64) timing_arch=amd64 ;;
  aarch64) timing_arch=arm64 ;;
  *) echo "Unsupported Nginx module architecture" >&2; exit 1 ;;
esac
cp "/binaries/nginx-timing-$timing_arch.so" /selected/ngx_http_ccsn_server_timing_module.so
"""


class LiteralDumper(yaml.SafeDumper):
    pass


def literal_string(dumper, value):
    return dumper.represent_scalar("tag:yaml.org,2002:str", value,
                                   style="|" if "\n" in value else None)


LiteralDumper.add_representer(str, literal_string)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def prepare(args):
    proof = json.loads(CATALOG.read_text())["next_candidates"]["native_nginx_compact_single_attempt"]
    require(proof["throughput"]["acceptance"]["status"] == "passed",
            "The recorded package must pass its independent throughput gate")
    source = Path(__file__).with_name("ngx_http_ccsn_server_timing_module.c")
    if digest(source.read_bytes()) != proof["source_sha256"]:
        raise ValueError("Module source differs from the recorded package")
    blobs = {}
    for arch, machine, expected, path in (
        ("amd64", 62, proof["module_sha256"], args.amd64),
        ("arm64", 183, proof["arm64_package"]["module_sha256"], args.arm64),
    ):
        if path is None:
            raise ValueError("Both --amd64 and --arm64 package files are required")
        blob = path.read_bytes()
        if blob[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", blob, 18)[0] != machine:
            raise ValueError(f"Incorrect ELF architecture for {arch}")
        if digest(blob) != expected:
            raise ValueError(f"The {arch} module differs from the verified package")
        blobs[f"nginx-timing-{arch}.so"] = blob
    files = ["kustomization.yaml", "nginx-config.yaml", "nginx-subconfig.yaml",
             "deployment.yaml", "service.yaml", "cert.yaml", "server-timing-headers.conf"]
    inputs = {name: digest((BASE / name).read_bytes()) for name in files}
    inputs.update({name: digest(blob) for name, blob in blobs.items()})
    inputs["prepare_runtime.py"] = digest(Path(__file__).read_bytes())
    inputs["ngx_http_ccsn_server_timing_module.c"] = digest(source.read_bytes())
    fingerprint = digest(json.dumps(inputs, sort_keys=True).encode())
    state_path = args.output / "manifest-sources.json"
    if args.output.exists() and any(args.output.iterdir()):
        if not state_path.exists() or json.loads(state_path.read_text())["fingerprint"] != fingerprint:
            raise ValueError("Use a new output directory for different or unowned inputs")
    args.output.mkdir(parents=True, exist_ok=True)
    state = {"fingerprint": fingerprint, "inputs": inputs, "stage": "preparing"}
    save(state_path, state)
    for name in files:
        (args.output / name).write_bytes((BASE / name).read_bytes())
    for name, blob in blobs.items():
        (args.output / name).write_bytes(blob)

    deployment = yaml.safe_load((BASE / "deployment.yaml").read_text())
    pod = deployment["spec"]["template"]["spec"]
    nginx = pod["containers"][0]
    if nginx["image"] != IMAGE:
        raise ValueError("The Nginx image changed; verify and record new compatible packages first")
    pod["initContainers"] = [{
        "name": "server-timing-module", "image": IMAGE,
        "command": ["sh", "-eu", "-c"], "args": [INIT_SCRIPT],
        "volumeMounts": [
            {"name": "server-timing-binaries", "mountPath": "/binaries", "readOnly": True},
            {"name": "server-timing-module", "mountPath": "/selected"},
        ],
    }]
    pod["volumes"].extend([
        {"name": "server-timing-binaries", "configMap": {"name": "i319-reroute-server-timing-module"}},
        {"name": "server-timing-module", "emptyDir": {}},
    ])
    nginx["volumeMounts"].append({"name": "server-timing-module",
                                  "mountPath": "/etc/nginx/native-modules", "readOnly": True})
    config = yaml.safe_load((BASE / "nginx-config.yaml").read_text())
    main = config["data"]["nginx.conf"]
    main = main.replace("load_module /usr/lib/nginx/modules/ngx_http_js_module.so;",
                        f"load_module /etc/nginx/native-modules/{MODULE};")
    main = main.replace("js_import server_timing from /etc/nginx/server-timing/server-timing.js;\n"
                        "    include /etc/nginx/server-timing/server-timing-maps.conf;",
                        "ccsn_server_timing on;")
    if "js_import" in main or "server-timing-maps.conf" in main:
        raise ValueError("The base timing configuration changed; update the preparation step")
    config["data"]["nginx.conf"] = main
    kustomization = yaml.safe_load((BASE / "kustomization.yaml").read_text())
    generator = next(item for item in kustomization["configMapGenerator"]
                     if item["name"] == "i319-reroute-server-timing")
    generator["files"] = ["server-timing-headers.conf"]
    kustomization["configMapGenerator"].append({
        "name": "i319-reroute-server-timing-module", "files": list(blobs),
    })
    for name, value in (("deployment.yaml", deployment), ("nginx-config.yaml", config),
                        ("kustomization.yaml", kustomization)):
        (args.output / name).write_text(yaml.dump(value, Dumper=LiteralDumper, sort_keys=False))
    (args.output / "server-timing-headers.conf").write_text(
        "add_header_inherit merge;\nccsn_server_timing on;\n")
    state["stage"] = "prepared"
    save(state_path, state)
    print(f"Prepared runtime bundle: {args.output}")


def verify(args):
    state = json.loads((args.output / "manifest-sources.json").read_text())
    require(state["stage"] in ("prepared", "verified"), "Runtime preparation is incomplete")
    require(state["inputs"].get("prepare_runtime.py") == digest(Path(__file__).read_bytes()),
            "The preparation implementation changed; use a fresh bundle")
    resources = list(yaml.safe_load_all(args.rendered.read_text()))
    module_map = next(item for item in resources if item["kind"] == "ConfigMap"
                      and set(item.get("binaryData", {})) == {"nginx-timing-amd64.so", "nginx-timing-arm64.so"})
    for name, value in module_map["binaryData"].items():
        encoded = "".join(value.split())
        if digest(base64.b64decode(encoded, validate=True)) != state["inputs"][name]:
            raise ValueError(f"Rendered binary differs from the verified {name}")
    deployment = next(item for item in resources if item["kind"] == "Deployment")
    pod = deployment["spec"]["template"]["spec"]
    init = pod["initContainers"][0]
    require(init["image"] == pod["containers"][0]["image"] == IMAGE, "Init and proxy images differ")
    require(init["command"] == ["sh", "-eu", "-c"] and init["args"] == [INIT_SCRIPT],
            "The architecture selection command changed")
    volume = next(item for item in pod["volumes"] if item["name"] == "server-timing-binaries")
    require(volume["configMap"]["name"] == module_map["metadata"]["name"], "Wrong module ConfigMap reference")
    require(module_map["metadata"]["name"] != "i319-reroute-server-timing-module", "Missing rollout hash")
    selected = next(item for item in pod["volumes"] if item["name"] == "server-timing-module")
    require(selected.get("emptyDir") == {}, "Selected module must use the startup copy")
    proxy_mount = next(item for item in pod["containers"][0]["volumeMounts"]
                       if item["name"] == "server-timing-module")
    require(proxy_mount["mountPath"] == "/etc/nginx/native-modules" and proxy_mount["readOnly"],
            "Proxy module mount changed")
    init_mounts = {item["name"]: item for item in init["volumeMounts"]}
    require(init_mounts["server-timing-binaries"]["mountPath"] == "/binaries"
            and init_mounts["server-timing-binaries"]["readOnly"]
            and init_mounts["server-timing-module"]["mountPath"] == "/selected",
            "Init module mounts changed")
    config = next(item for item in resources if item["kind"] == "ConfigMap"
                  and "nginx.conf" in item.get("data", {}))["data"]["nginx.conf"]
    require(f"load_module /etc/nginx/native-modules/{MODULE};" in config, "Module is not loaded")
    require("ccsn_server_timing on;" in config and "js_import" not in config, "Native timing is not enabled")
    state["stage"] = "verified"
    save(args.output / "manifest-sources.json", state)
    print("Verified both binary hashes, generated rollout reference, init image, and native timing configuration")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("prepare", "verify"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--amd64", type=Path)
    parser.add_argument("--arm64", type=Path)
    parser.add_argument("--rendered", type=Path)
    args = parser.parse_args()
    if args.stage == "verify" and args.rendered is None:
        parser.error("--rendered is required for independent verification")
    (prepare if args.stage == "prepare" else verify)(args)
