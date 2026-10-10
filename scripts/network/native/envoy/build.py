#!/usr/bin/env python3
"""Compile only the three plugin translation units against a pinned header SDK."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = Path(__file__).resolve().parent
HEADERS = {
    "source/extensions/dynamic_modules/abi/abi.h": "77378e7911100ad7302f3d8adce0e5f6826cb2f8227ec001b98c5a733fd9f633",
    "source/extensions/filters/http/dynamic_modules/filter.h": "12a013cbf35d7be45d1ffa9683976e7039ccf8a87a3d54c73d4c52c74be740a2",
    "source/extensions/filters/http/dynamic_modules/filter_config.h": "4ddabb4c9edd89d1a1da8516f854c8ab4f444e2578cade119d458fcd2e3bb81d",
    "envoy/stream_info/stream_info.h": "9d2345ce27dac3ba4522df8ea26323ad2e48bff60d04972b01439ce87d994efd",
    "envoy/http/filter.h": "06a77b3826cf75a9c59d4e2e2366fce7ef85c0f7fbd271cd8e68a1d785183c56",
    "envoy/event/dispatcher.h": "c624b849044c63ce01e0e8b9ce3220fb728b1320984b4c2503fbaf550e2b28e9",
    "envoy/common/time.h": "667190d8688bc643775b020d19d1d6bb87d009a55cad4aef70fbbd93b5d3ab23"
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command):
    subprocess.run([str(arg) for arg in command], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["build", "verify"], default="build")
    parser.add_argument("--external", type=Path, required=True,
                        help="Pinned SDK source dependencies, including envoy and abseil-cpp")
    parser.add_argument("--generated", type=Path, required=True,
                        help="SDK generated protobuf include roots; no proxy build is invoked")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cc", default="clang")
    parser.add_argument("--cxx", default="clang++")
    parser.add_argument("--flags", type=Path, help="Optional JSON: c, cxx flags and linker command")
    parser.add_argument("--expected-sha256", help="Require the exact accepted module")
    args = parser.parse_args()
    ext, generated, out = args.external.resolve(), args.generated.resolve(), args.output.resolve()
    flags = json.loads(args.flags.read_text()) if args.flags else {}
    identities = {}
    for name, expected in HEADERS.items():
        actual = digest(ext / "envoy" / name)
        if actual != expected:
            raise ValueError(f"Unsupported SDK interface: {name}")
        identities[name] = actual
    identities.update({name: digest(SOURCE / name) for name in ["plugin.c", "bridge.cc", "abi_guard.c"]})
    out.mkdir(parents=True, exist_ok=True)
    manifest = out / "build.json"
    if args.stage == "build":
        alias = out / "sdk-includes/source/common/common/logger_impl.h"
        alias.parent.mkdir(parents=True, exist_ok=True)
        alias.write_text('#include "source/common/common/standard/logger_impl.h"\n')
        includes = [out / "sdk-includes", ext / "envoy", ext / "envoy_api", ext / "abseil-cpp",
                    ext / "com_envoyproxy_protoc_gen_validate",
                    ext / "spdlog/include", ext / "fmt/include", ext / "com_google_protobuf/src",
                    ext / "com_google_protobuf/third_party/utf8_range", ext / "proto-converter/src",
                    ext / "xxhash", ext / "boringssl/include"]
        includes.extend(sorted(path for path in generated.iterdir() if path.is_dir()))
        cxx = [args.cxx, *flags.get("cxx", []), "-std=c++20", "-O3", "-DNDEBUG", "-fPIC",
               "-fno-exceptions", "-DSPDLOG_FMT_EXTERNAL", "-DSPDLOG_NO_EXCEPTIONS",
               "-DENVOY_ENABLE_FULL_PROTOS", "-Wno-deprecated-declarations"]
        for path in includes:
            cxx.extend(["-I", str(path)])
        c = [args.cc, *flags.get("c", []), "-std=c11", "-O3", "-DNDEBUG", "-D_DEFAULT_SOURCE",
             "-fPIC", "-I", str(ext / "envoy")]
        commands = [
            [*c, "-c", SOURCE / "plugin.c", "-o", out / "plugin.o"],
            [*cxx, "-c", SOURCE / "bridge.cc", "-o", out / "bridge.o"],
            [*c, "-c", SOURCE / "abi_guard.c", "-o", out / "abi_guard.o"],
            [*flags.get("linker", [args.cc, "-shared"]), out / "plugin.o", out / "bridge.o",
             out / "abi_guard.o", "-o", out / "server-timing.so"],
        ]
        state = {"identities": identities, "commands": [[str(arg) for arg in cmd] for cmd in commands],
                 "completed": 0}
        if manifest.exists():
            previous = json.loads(manifest.read_text())
            if previous["identities"] != identities or previous["commands"] != state["commands"]:
                raise ValueError("Changed build inputs: use a fresh output directory")
        for index, command in enumerate(commands):
            run(command)
            state["completed"] = index + 1
            manifest.write_text(json.dumps(state, indent=2) + "\n")
    state = json.loads(manifest.read_text())
    if state["completed"] != 4 or state["identities"] != identities:
        raise ValueError("Incomplete or outdated build")
    if subprocess.check_output(["nm", "-u", str(out / "bridge.o")], text=True).strip():
        raise ValueError("The native bridge unexpectedly requires linked Envoy or C++ libraries")
    actual = digest(out / "server-timing.so")
    if args.expected_sha256 and actual != args.expected_sha256:
        raise ValueError(f"The rebuilt module differs from acceptance: {actual}")
    state["module_sha256"] = actual
    state["verified"] = True
    manifest.write_text(json.dumps(state, indent=2) + "\n")
    print(f"Verified plugin-only build: {actual}")


if __name__ == "__main__":
    main()
