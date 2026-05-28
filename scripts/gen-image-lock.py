#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pyyaml",
#     "flux-local~=8.2.0",
# ]
# ///
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import yaml

ARCHIVE_HASH_FORMAT_VERSION = "v2"

def log(msg):
    print(msg, file=sys.stderr)


def ensure_commands_exist(commands):
    missing = [cmd for cmd in commands if shutil.which(cmd) is None]
    if not missing:
        return

    log("[gen-image-lock] missing required command(s): " + ", ".join(missing))
    log("[gen-image-lock] please install them and make sure they are available in PATH")
    sys.exit(1)

def run_cmd(cmd, input_data=None, retries=1, check=True):
    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(
                cmd,
                input=input_data.encode('utf-8') if input_data else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=check
            )
            return result.stdout.decode('utf-8')
        except subprocess.CalledProcessError as e:
            if attempt == retries:
                log(f"Command failed: {' '.join(cmd)}")
                log(f"Error output: {e.stderr.decode('utf-8')}")
                if check:
                    sys.exit(1)
                return None
            time.sleep(attempt * 2)


def nix_escape_string(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'

def split_image_name(image_name):
    parts = image_name.split("/")
    first = parts[0] if parts else ""
    has_explicit_registry = "." in first or ":" in first or first == "localhost"
    if has_explicit_registry:
        registry = first
        repo = "/".join(parts[1:])
    else:
        registry = "docker.io"
        repo = image_name
    return registry, repo

def map_image_source(image_name, registry_mirrors):
    registry, repo = split_image_name(image_name)
    mapped_registry = registry_mirrors.get(registry, registry)
    return f"{mapped_registry}/{repo}"

def normalize_mirror_value(mirror_value):
    if isinstance(mirror_value, list):
        return [it for it in mirror_value if isinstance(it, str) and it]
    if isinstance(mirror_value, str) and mirror_value:
        return [mirror_value]
    return []

def map_image_sources(image_name, registry_mirrors):
    registry, repo = split_image_name(image_name)
    mirror_value = registry_mirrors.get(registry, [])
    mirror_registries = normalize_mirror_value(mirror_value)
    sources = [f"{mirror_registry}/{repo}" for mirror_registry in mirror_registries]
    sources.append(image_name)
    unique_sources = []
    seen = set()
    for source in sources:
        if source not in seen:
            seen.add(source)
            unique_sources.append(source)
    return unique_sources

def canonical_image_name(image_name):
    registry, repo = split_image_name(image_name)
    if registry == "docker.io" and "/" not in repo:
        repo = f"library/{repo}"
    return f"{registry}/{repo}"

def parse_nix_blocks(content):
    """Extract complete block text for exact metadata diffing"""
    blocks = {}
    if not content:
        return blocks
    
    parts = content.split('  {\n    imageName = "')
    for part in parts[1:]:
        chunk = '  {\n    imageName = "' + part
        end_idx = chunk.rfind('\n  }')
        if end_idx != -1:
            block_str = chunk[:end_idx + 4]
        else:
            block_str = chunk
            
        name_match = re.search(r'imageName\s*=\s*"([^"]*)"', block_str)
        tag_match = re.search(r'finalImageTag\s*=\s*"([^"]*)"', block_str)
        hash_match = re.search(r'archiveHash\s*=\s*"([^"]*)"', block_str)
        
        if name_match and tag_match and hash_match:
            name = name_match.group(1)
            tag = tag_match.group(1) or "latest"
            uid = f"{name}:{tag}"
            blocks[uid] = {
                "archiveHash": hash_match.group(1),
                "block": block_str.strip()
            }
    return blocks

def parse_metadata_from_block(block_str):
    """Extract sources, sourceChains and targets sets from rendered Nix Block for Diffing"""
    def extract_section(name):
        pattern = fr"{name}\s*=\s*\[(.*?)\];"
        match = re.search(pattern, block_str, re.DOTALL)
        return match.group(1) if match else ""

    sources_raw = extract_section("sources")
    chains_raw = extract_section("sourceChains")
    targets_raw = extract_section("targets")

    def parse_items(raw):
        return set([f"{m[0]}:{m[1]}/{m[2]}" for m in re.findall(r'kind\s*=\s*"([^"]+)";\s*namespace\s*=\s*"([^"]+)";\s*name\s*=\s*"([^"]+)";', raw)])

    def parse_chains(raw):
        chains = []
        for chain_block in re.findall(r'\[(.*?)\]', raw, re.DOTALL):
            items = [f"{m[0]}:{m[1]}/{m[2]}" for m in re.findall(r'kind\s*=\s*"([^"]+)";\s*namespace\s*=\s*"([^"]+)";\s*name\s*=\s*"([^"]+)";', chain_block)]
            if items:
                chains.append(" -> ".join(items))
        return set(chains)

    return {
        "sources": parse_items(sources_raw),
        "sourceChains": parse_chains(chains_raw),
        "targets": parse_items(targets_raw)
    }

def generate_meta_diff(old_meta, new_meta):
    """Calculate metadata diff and return formatted text list"""
    lines = []
    for key in ["sources", "sourceChains", "targets"]:
        old_set = old_meta.get(key, set())
        new_set = new_meta.get(key, set())
        added = new_set - old_set
        removed = old_set - new_set
        if added or removed:
            lines.append(f"        {key}:")
            for r in sorted(removed): lines.append(f"            - {r}")
            for a in sorted(added): lines.append(f"            + {a}")
    return lines

def format_image_diff(uid, old_hash, new_hash, old_meta, new_meta, action, intro_map):
    """Generate hierarchical change report for a single image"""
    lines = []
    intro = intro_map.get(uid, "")
    
    if action == "Added":
        lines.append(f"• Added image '{uid}'{intro}:")
        lines.append(f"    archiveHash: '{new_hash}'")
    elif action == "Updated":
        lines.append(f"• Updated image '{uid}':")
        lines.append(f"    archiveHash:")
        lines.append(f"      - '{old_hash}'")
        lines.append(f"      + '{new_hash}'")
    elif action == "MetaUpdated":
        lines.append(f"• Updated metadata for '{uid}':")
    elif action == "Removed":
        lines.append(f"• Removed image '{uid}'")
        return lines

    if action in ["Added", "Updated", "MetaUpdated"]:
        meta_diff_lines = generate_meta_diff(old_meta, new_meta)
        if meta_diff_lines:
            lines.append("    metadata:")
            lines.extend(meta_diff_lines)
            
    return lines

class ImageLockGenerator:
    def __init__(self, args):
        self.args = args
        self.flux_root = Path(args.root) / "clusters" / args.cluster
        self.out_lock_file = self.flux_root / "images.lock.nix"
        self.image_map = {}
        self.total_images = 0
        self.results_nix_blocks = []
        self.new_hashes = {}
        self.intro_map = {}
        self.changes_detected = False
        self.final_nix = ""
        self.summary_output = ""
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_writes = 0
        self.cache_skips = 0
        self.nix_build_count = 0
        self.nix_build_paths = []
        self.registry_mirrors = json.loads(args.registry_mirror_map) if args.registry_mirror_map else {}
        self.mirror_retries = max(args.mirror_retries, 1)
        self.repo_root = Path(args.root).resolve()

    def vlog(self, msg):
        if self.args.verbose:
            log(msg)
        
        if not self.flux_root.is_dir():
            log(f"Cluster path does not exist: {self.flux_root}")
            sys.exit(1)

    def run(self):
        log(f"[gen-image-lock] cluster={self.args.cluster} root={self.flux_root}")
        self.check_dependencies()
        cluster_meta = self.fetch_cluster_metadata()
        manifests = self.render_manifests()
        
        self.process_cluster_sources(cluster_meta)
        self.process_manifest_targets(manifests)
        self.filter_by_namespace()
        self.sort_and_deduplicate()
        
        if not self.image_map:
            log("Generated empty lock file (no images found)")
            self.out_lock_file.write_text("[\n]\n", encoding='utf-8')
            sys.exit(0)
            
        self.total_images = len(self.image_map)
        log(f"[gen-image-lock] render complete: {self.total_images} images found")
        
        self.resolve_digests_and_archive_hash()
        self.generate_diff()
        self.generate_report()
        self.write_commit_msg()
        self.auto_commit()
        log("Execution finished successfully.")

    def check_dependencies(self):
        required_commands = [
            "flux-local",
            "flux",
            "kustomize",
            "crane",
            "nix",
        ]
        ensure_commands_exist(required_commands)

    def prefetch_archive_hash_via_nix(self, source_images, image_name, tag, digest):
        source_images_json = json.dumps(source_images)
        expr = (
            "let\n"
            f"  flake = builtins.getFlake {nix_escape_string(str(self.repo_root))};\n"
            "  pkgs = import flake.inputs.nixpkgs { system = builtins.currentSystem; };\n"
            "in flake.lib.mkMultiArchImageArchive {\n"
            "  inherit pkgs;\n"
            f"  sourceImages = builtins.fromJSON ''{source_images_json}'';\n"
            f"  finalImageName = {nix_escape_string(image_name)};\n"
            f"  finalImageTag = {nix_escape_string(tag)};\n"
            f"  imageDigest = {nix_escape_string(digest)};\n"
            "  archiveHash = \"sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\";\n"
            f"  mirrorRetries = {self.mirror_retries};\n"
            "}"
        )
        result = subprocess.run([
            "nix",
            "build",
            "--impure",
            "--no-link",
            "--print-out-paths",
            "--expr",
            expr,
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.nix_build_count += 1

        output = (result.stdout or "") + "\n" + (result.stderr or "")
        got_match = re.search(r"got:\s*(sha256-[A-Za-z0-9+/=]+)", output)
        if got_match:
            archive_hash = got_match.group(1)
            self.nix_build_paths.append(f"prefetch:{image_name}:{tag}@{digest} -> {archive_hash}")
            return archive_hash

        if result.returncode == 0:
            out_path = (result.stdout or "").strip()
            if out_path:
                hash_val = run_cmd(["nix", "hash", "file", "--sri", out_path], retries=2).strip()
                if hash_val:
                    self.nix_build_paths.append(f"build:{out_path} -> {hash_val}")
                    return hash_val

        log(f"Command failed: {' '.join(result.args)}")
        log(f"Error output: {result.stderr}")
        raise Exception("Failed to prefetch archive hash via FOD placeholder")

    def fetch_cluster_metadata(self):
        log("[gen-image-lock] step 1: fetch cluster metadata (sources)")
        cluster_cmd = [
            "flux-local", "get", "cluster", "--path", str(self.flux_root), "--enable-images", "-o", "json"
        ]
        cluster_json = run_cmd(cluster_cmd, retries=4)
        return json.loads(cluster_json)

    def render_manifests(self):
        log("[gen-image-lock] step 2: render manifests (targets)")
        build_cmd = [
            "flux-local", "build", "all", "--enable-helm", str(self.flux_root)
        ]
        rendered_yaml = run_cmd(build_cmd, retries=4)
        try:
            return list(yaml.safe_load_all(rendered_yaml))
        except yaml.YAMLError as exc:
            log(f"Failed to parse YAML output: {exc}")
            sys.exit(1)

    def add_to_map(self, img_ref, section, item):
        if not img_ref or not isinstance(img_ref, str): return
        img_ref = img_ref.strip()
        if not img_ref: return
        if img_ref not in self.image_map:
            self.image_map[img_ref] = {"sources": [], "sourceChains": [], "targets": []}
        self.image_map[img_ref][section].append(item)

    def process_cluster_sources(self, cluster_meta):
        for cluster in cluster_meta.get("clusters", []):
            kustomizations = cluster.get("kustomizations", [])
            for k in kustomizations:
                k_ns = k.get("namespace") or "unknown ns"
                if not k.get("namespace"):
                    log(f"Warning: Namespace missing for Kustomization {k.get('name', '')}, marking as 'unknown ns'")
                    
                k_path = k.get("path", "")
                parents_with_path = []
                for other_k in kustomizations:
                    if other_k.get("path") != k_path and k_path.startswith(other_k.get("path", "") + "/"):
                        p_ns = other_k.get("namespace") or "unknown ns"
                        parents_with_path.append({
                            "kind": "Kustomization", 
                            "namespace": p_ns, 
                            "name": other_k.get("name", ""),
                            "path": other_k.get("path", "")
                        })
                parents_with_path.sort(key=lambda x: len(x.get("path", "")), reverse=True)
                parents = [{"kind": p["kind"], "namespace": p["namespace"], "name": p["name"]} for p in parents_with_path]

                k_source = {"kind": "Kustomization", "namespace": k_ns, "name": k.get("name", "")}
                k_chain = [k_source] + parents

                for img in k.get("images", []):
                    self.add_to_map(img, "sources", k_source)
                    self.add_to_map(img, "sourceChains", k_chain)

                for hr in k.get("helm_releases", []):
                    hr_ns = hr.get("namespace")
                    if not hr_ns:
                        hr_ns = k_ns if k_ns != "unknown ns" else "unknown ns"
                        if not hr.get("namespace"):
                            log(f"Warning: Namespace missing for HelmRelease {hr.get('name', '')}, marking as 'unknown ns'")
                            
                    hr_source = {"kind": "HelmRelease", "namespace": hr_ns, "name": hr.get("name", "")}
                    hr_chain = [hr_source] + k_chain
                    for img in hr.get("images", []):
                        self.add_to_map(img, "sources", hr_source)
                        self.add_to_map(img, "sourceChains", hr_chain)

    def process_manifest_targets(self, manifests):
        target_kinds = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "Pod", "ReplicaSet", "ReplicationController"}
        for obj in manifests:
            if not obj or not isinstance(obj, dict): continue
            kind = obj.get("kind")
            if kind not in target_kinds: continue
            
            meta = obj.get("metadata", {})
            ns = meta.get("namespace")
            name = meta.get("name", "")
            if not ns:
                log(f"Warning: Namespace missing for Target {kind}/{name}, marking as 'unknown ns'")
                ns = "unknown ns"
            
            target = {"kind": kind, "namespace": ns, "name": name}
            
            def extract_from_containers(containers):
                if isinstance(containers, list):
                    for c in containers:
                        img = c.get("image")
                        if img: self.add_to_map(img, "targets", target)

            spec = obj.get("spec", {})
            extract_from_containers(spec.get("containers"))
            extract_from_containers(spec.get("initContainers"))
            extract_from_containers(spec.get("ephemeralContainers"))
            
            template_spec = spec.get("template", {}).get("spec", {})
            extract_from_containers(template_spec.get("containers"))
            extract_from_containers(template_spec.get("initContainers"))
            extract_from_containers(template_spec.get("ephemeralContainers"))
            
            job_spec = spec.get("jobTemplate", {}).get("spec", {}).get("template", {}).get("spec", {})
            extract_from_containers(job_spec.get("containers"))
            extract_from_containers(job_spec.get("initContainers"))
            extract_from_containers(job_spec.get("ephemeralContainers"))

    def filter_by_namespace(self):
        allowed_ns = set(self.args.namespaces.split()) if self.args.namespaces else set()
        if not allowed_ns: return
            
        filtered_image_map = {}
        for img_ref, data in self.image_map.items():
            in_allowed_ns = False
            for src in data["sources"]:
                if src.get("namespace") in allowed_ns:
                    in_allowed_ns = True
                    break
            if not in_allowed_ns:
                for tgt in data["targets"]:
                    if tgt.get("namespace") in allowed_ns:
                        in_allowed_ns = True
                        break
            if in_allowed_ns:
                filtered_image_map[img_ref] = data
        self.image_map = filtered_image_map

    def sort_and_deduplicate(self):
        def get_sort_key(item):
            return (item.get('kind', ''), item.get('namespace', ''), item.get('name', ''))

        def get_chain_sort_key(chain):
            return tuple(get_sort_key(c) for c in chain)

        for img_ref, data in self.image_map.items():
            for key, get_key in [("sources", get_sort_key), ("targets", get_sort_key), ("sourceChains", get_chain_sort_key)]:
                seen = []
                for item in data[key]:
                    if item not in seen: seen.append(item)
                seen.sort(key=get_key)
                data[key] = seen

    def format_list(self, items):
        if not items: return "[]"
        lines = []
        for item in items:
            if isinstance(item, list): 
                lines.append("      [")
                for sub in item:
                    lines.append(f"        {{ kind = \"{sub['kind']}\"; namespace = \"{sub['namespace']}\"; name = \"{sub['name']}\"; }}")
                lines.append("      ]")
            else:
                lines.append(f"      {{ kind = \"{item['kind']}\"; namespace = \"{item['namespace']}\"; name = \"{item['name']}\"; }}")
        return "[\n" + "\n".join(lines) + "\n    ]"

    def resolve_digests_and_archive_hash(self):
        cache_dir = Path.home() / f".cache/nixos-image-lock/{self.args.arch}-{self.args.os}"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.vlog(f"[gen-image-lock] cache dir: {cache_dir}")

        def process_image(img_ref, data, index):
            log(f"[gen-image-lock] [{index}/{self.total_images}] resolve digest: {img_ref}")
            image_name = img_ref
            tag = "latest"
            if "@sha256:" in img_ref:
                image_name = img_ref.split("@sha256:")[0]
            if ":" in image_name:
                tag = image_name.split(":")[-1]
                image_name = image_name.rsplit(":", 1)[0]

            uid = f"{image_name}:{tag}"
            digest = run_cmd(["crane", "digest", img_ref], retries=4).strip()
            
            safe_digest = digest.replace(":", "-")
            safe_name = re.sub(r'[/:]', '_', image_name)
            safe_tag = re.sub(r'[^a-zA-Z0-9._-]', '_', tag)
            cache_file = cache_dir / (
                f"{safe_name}-{safe_tag}-{safe_digest}-"
                f"{hashlib.sha256(json.dumps(source_images := map_image_sources(image_name, self.registry_mirrors), sort_keys=True).encode('utf-8')).hexdigest()[:16]}-"
                f"{ARCHIVE_HASH_FORMAT_VERSION}.txt"
            )

            
            hash_val = cache_file.read_text('utf-8').strip() if cache_file.exists() else ""
            if self.args.ignore_cache:
                self.cache_skips += 1
                hash_val = ""
                self.vlog(f"[gen-image-lock] [{index}/{self.total_images}] cache bypass enabled")
            if not hash_val:
                self.cache_misses += 1
                self.vlog(f"[gen-image-lock] [{index}/{self.total_images}] cache miss: {cache_file.name}")
                self.vlog(f"[gen-image-lock] [{index}/{self.total_images}] digest={digest} sources={len(source_images)}")
                log(f"[gen-image-lock] [{index}/{self.total_images}] prefetching archive hash via nix lib...")
                hash_val = self.prefetch_archive_hash_via_nix(source_images, image_name, tag, digest)
                if not hash_val:
                    raise Exception(f"Failed to calculate archive hash for: {img_ref}")
                tmp_cache_file = cache_file.with_suffix(cache_file.suffix + f".{os.getpid()}.tmp")
                tmp_cache_file.write_text(hash_val, encoding='utf-8')
                tmp_cache_file.replace(cache_file)
                self.cache_writes += 1
                log(f"[gen-image-lock] [{index}/{self.total_images}] archive hash ok: {hash_val}")
            else:
                self.cache_hits += 1
                self.vlog(f"[gen-image-lock] [{index}/{self.total_images}] cache hit: {cache_file.name}")
                self.vlog(f"[gen-image-lock] [{index}/{self.total_images}] archive hash cached: {hash_val}")

            block = (
                f"  {{\n"
                f"    imageName = \"{image_name}\";\n"
                f"    imageDigest = \"{digest}\";\n"
                f"    finalImageName = \"{canonical_image_name(image_name)}\";\n"
                f"    finalImageTag = \"{tag}\";\n"
                f"    archiveHash = \"{hash_val}\";\n"
                f"    os = \"{self.args.os}\";\n"
                f"    arch = \"{self.args.arch}\";\n"
                f"    sources = {self.format_list(data['sources'])};\n"
                f"    sourceChains = {self.format_list(data['sourceChains'])};\n"
                f"    targets = {self.format_list(data['targets'])};\n"
                f"  }}"
            )
            intro_names = sorted(list(set([s.get("name") for s in data["sources"] if s.get("name")])))
            intro_str = f" (introduced by {', '.join(intro_names)})" if intro_names else ""
            return img_ref, uid, hash_val, block, intro_str

        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = {executor.submit(process_image, img, data, i+1): img for i, (img, data) in enumerate(self.image_map.items())}
            for future in as_completed(futures):
                try:
                    img_ref, uid, hash_val, block, intro_str = future.result()
                    self.results_nix_blocks.append((img_ref, block))
                    self.new_hashes[uid] = {"archiveHash": hash_val, "block": block.strip()}
                    self.intro_map[uid] = intro_str
                except BaseException as e:
                    log(f"Job failed: {e}")
                    sys.exit(1)

        self.results_nix_blocks.sort(key=lambda x: x[0])
        self.final_nix = "[\n" + "\n".join([block for _, block in self.results_nix_blocks]) + "\n]\n"
        self.vlog(
            "[gen-image-lock] cache summary: "
            f"hits={self.cache_hits} misses={self.cache_misses} writes={self.cache_writes} "
            f"nix-builds={self.nix_build_count}"
        )

    def generate_diff(self):
        old_content = self.out_lock_file.read_text('utf-8') if self.out_lock_file.exists() else ""
        self.changes_detected = (self.final_nix != old_content)
        
        self.out_lock_file.write_text(self.final_nix, encoding='utf-8')
        log(f"[gen-image-lock] wrote {self.out_lock_file}")

        summary_lines = []
        if self.changes_detected:
            if not old_content:
                summary_lines.append(f"• Created initial lock file for {self.total_images} images.")
            else:
                old_hashes = parse_nix_blocks(old_content)
                stats = {"updated": 0, "meta_updated": 0, "added": 0, "removed": 0}
                
                for uid, new_data in self.new_hashes.items():
                    new_meta = parse_metadata_from_block(new_data['block'])
                    if uid in old_hashes:
                        old_data = old_hashes[uid]
                        old_meta = parse_metadata_from_block(old_data['block'])
                        
                        if old_data['archiveHash'] != new_data['archiveHash']:
                            diff_lines = format_image_diff(uid, old_data['archiveHash'], new_data['archiveHash'], old_meta, new_meta, "Updated", self.intro_map)
                            summary_lines.extend(diff_lines)
                            stats["updated"] += 1
                        elif old_data['block'] != new_data['block']:
                            diff_lines = format_image_diff(uid, old_data['archiveHash'], new_data['archiveHash'], old_meta, new_meta, "MetaUpdated", self.intro_map)
                            summary_lines.extend(diff_lines)
                            stats["meta_updated"] += 1
                    else:
                        diff_lines = format_image_diff(uid, None, new_data['archiveHash'], {}, new_meta, "Added", self.intro_map)
                        summary_lines.extend(diff_lines)
                        stats["added"] += 1
                        
                for uid in old_hashes:
                    if uid not in self.new_hashes:
                        diff_lines = format_image_diff(uid, None, None, {}, {}, "Removed", self.intro_map)
                        summary_lines.extend(diff_lines)
                        stats["removed"] += 1
                        
                if any(stats.values()):
                    summary_lines.extend(["", "-" * 40])
                    if stats["updated"]: summary_lines.append(f"{stats['updated']} image(s) updated in total.")
                    if stats["meta_updated"]: summary_lines.append(f"{stats['meta_updated']} image(s) metadata updated in total.")
                    if stats["added"]: summary_lines.append(f"{stats['added']} image(s) added in total.")
                    if stats["removed"]: summary_lines.append(f"{stats['removed']} image(s) removed in total.")
                else:
                    summary_lines.append("• Lock file structure modified, but core image archive hashes remain unchanged.")
                    
        self.summary_output = "\n".join(summary_lines).strip()

    def generate_report(self):
        if not self.args.report_file: return
            
        report_path = Path(self.args.report_file)
        report_content = [
            "## 🚀 Flux Image Lock Report",
            f"- **Cluster:** `{self.args.cluster}`",
            f"- **Images Processed:** {self.total_images}",
            f"- **Verbose Mode:** {self.args.verbose}",
            f"- **Cache Hits:** {self.cache_hits}",
            f"- **Cache Misses:** {self.cache_misses}",
            f"- **Cache Writes:** {self.cache_writes}",
            f"- **Cache Bypassed:** {self.cache_skips}",
            f"- **Nix Builds:** {self.nix_build_count}",
            ""
        ]

        if self.nix_build_paths:
            report_content.extend([
                "### 🧱 Nix Build Outputs",
                "```text",
                "\n".join(self.nix_build_paths),
                "```",
            ])
        
        if self.changes_detected:
            report_content.extend(["### 🔄 Image lock file updates\n", f"```text\n{self.summary_output}\n```"])
        else:
            report_content.extend(["### ✅ No Changes", "All image digests and metadata are up to date."])
            
        report_path.write_text("\n".join(report_content), encoding='utf-8')
        log(f"[gen-image-lock] generated report file at {report_path}")

    def write_commit_msg(self):
        if not self.changes_detected or not self.args.commit_msg_file:
            return
        
        commit_msg = f"chore(lock): update image lock for cluster {self.args.cluster}\n\nImage lock file updates:\n{self.summary_output or '• Structural or metadata changes only.'}"
        Path(self.args.commit_msg_file).write_text(commit_msg, encoding='utf-8')
        log(f"[gen-image-lock] wrote commit message to {self.args.commit_msg_file}")

    def auto_commit(self):
        if not self.args.auto_commit or not self.changes_detected:
            return

        log("[gen-image-lock] auto-committing...")
        commit_msg = f"chore(lock): update image lock for cluster {self.args.cluster}\n\nImage lock file updates:\n{self.summary_output or '• Structural or metadata changes only.'}"
        if shutil.which("git"):
            run_cmd(["git", "add", str(self.out_lock_file)])
            diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
            if diff_check.returncode != 0:
                run_cmd(["git", "commit", "-m", commit_msg])
                log("[gen-image-lock] commit successful")
            else:
                log("[gen-image-lock] no staged changes found for git")
        else:
            log("[gen-image-lock] git command not found, skipping auto-commit")


def main():
    parser = argparse.ArgumentParser(description="Generate Nix image lock file for Flux CD")
    parser.add_argument("--root", default=".", help="Root directory of the repository")
    parser.add_argument("--cluster", required=True, help="Cluster name")
    parser.add_argument("--arch", default="amd64", help="Target architecture")
    parser.add_argument("--os", default="linux", help="Target OS")
    parser.add_argument("--auto-commit", action="store_true", help="Enable auto commit")
    parser.add_argument("--report-file", default="", help="Path to generate markdown report")
    parser.add_argument("--commit-msg-file", default="", help="Path to save the generated commit message")
    parser.add_argument("--registry-mirror-map", default="", help="JSON object mapping source registry to mirror registry")
    parser.add_argument("--mirror-retries", type=int, default=3, help="Retry attempts per mirror source")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging for cache/build details")
    parser.add_argument("--ignore-cache", action="store_true", help="Ignore local cache and force rebuild archive hashes")
    
    parser.add_argument("--namespaces", default="", help="Space separated namespaces to filter")
    
    args = parser.parse_args()
    
    generator = ImageLockGenerator(args)
    generator.run()

if __name__ == "__main__":
    main()
