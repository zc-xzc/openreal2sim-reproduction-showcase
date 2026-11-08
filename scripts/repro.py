#!/usr/bin/env python3
"""Offline-first OpenReal2Sim orchestration and structural acceptance checks.

No third-party imports, model downloads, pickle loads or upstream execution at import.
This is an engineering harness, not evidence of a successful GPU reproduction.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import pickle
import re
import shutil
import struct
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parents[1]
PIN = "8f69a19e5dfdfe0aad906fdacad0decf862a7adf"
STAGES = {
    "preprocess": ["openreal2sim/preprocess/preprocess_manager.py", "--key_name"],
    "annotate": ["openreal2sim/reconstruction/tools/segmentation_annotator.py"],
    "reconstruct": ["openreal2sim/reconstruction/recon_agent.py", "--key"],
    "motion": ["openreal2sim/motion/motion_manager.py", "--key"],
    "usd": ["openreal2sim/simulation/isaaclab/demo/sim_utils_demo/usd_conversion.py", "--key"],
    "rollout": ["openreal2sim/simulation/isaaclab/demo/sim_heuristic_manip.py", "--key"],
    "randomize": ["openreal2sim/simulation/isaaclab/demo/sim_randomize_rollout.py", "--key"],
}
PACKAGES = ("numpy", "torch", "torchvision", "PyYAML", "pandas", "gradio",
            "open3d", "transformers", "diffusers", "huggingface-hub", "onnx",
            "onnxruntime-gpu", "protobuf", "trimesh", "pymeshlab", "moge")


class CheckError(Exception):
    pass


def key_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value):
        raise CheckError("key must contain 1-80 letters, digits, underscores or hyphens")
    return value


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def confined(root, relative):
    root = Path(root).resolve()
    p = (root / relative).resolve()
    if not p.is_relative_to(root):
        raise CheckError("path escapes the selected root")
    return p


def emit(value, output=None):
    text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if output:
        p = Path(output)
        if p.exists():
            raise CheckError("report already exists; choose a new output path")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(text, end="")


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if result.returncode:
        raise CheckError("git check failed; verify checkout and submodule access")
    return result.stdout.strip()


def source_check(root, require_patch=True, require_submodules=True):
    root = Path(root).resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise CheckError("upstream HEAD differs from locked commit")
    locks = json.loads((HERE / "locks/source-lock.json").read_text())
    if require_submodules:
        for item in locks["submodules"]:
            path = confined(root, item["path"])
            if git(path, "rev-parse", "HEAD") != item["commit"]:
                raise CheckError("submodule mismatch: " + item["path"])
            if git(path, "status", "--porcelain", "--untracked-files=no"):
                raise CheckError("modified submodule: " + item["path"])
        status = git(root, "submodule", "status", "--recursive")
        if any(line.startswith(("-", "+", "U")) for line in status.splitlines()):
            raise CheckError("recursive submodule is missing or differs from its gitlink")
    patched = locks.get("patched_files", {})
    if not isinstance(patched, dict) or (require_patch and not patched):
        raise CheckError("source lock lacks patched_files SHA256 mapping")
    allowed = {"config/config.yaml"} | set(patched)
    changed = git(root, "diff", "HEAD", "--name-only").splitlines()
    if set(changed) - allowed:
        raise CheckError("unexpected tracked source changes")
    if require_patch:
        for relative, expected in patched.items():
            if not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise CheckError("invalid patched source SHA256")
            if sha256(confined(root, relative)) != expected:
                raise CheckError("patched source checksum mismatch: " + relative)
        patch = HERE / "patches/0001-safe-cli.patch"
        result = subprocess.run(["git", "-C", str(root), "apply", "--reverse", "--check", str(patch)],
                                capture_output=True, text=True)
        if result.returncode:
            raise CheckError("required safety patch is missing or modified")
    return {"source_commit": PIN, "submodules_checked": require_submodules,
            "safety_patch_checked": require_patch}


def capture():
    versions = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name")
        if name:
            versions[name] = dist.version
    return {"schema_version": 1, "kind": "observed_environment_not_validated",
            "python": ".".join(map(str, sys.version_info[:3])),
            "platform": sys.platform, "packages": dict(sorted(versions.items(), key=lambda p: p[0].lower())),
            "contains_secrets_or_environment_variables": False}


def preflight(root):
    facts = capture()
    packages = {k.lower().replace("_", "-"): v for k, v in facts["packages"].items()}
    checks = [{"name": "python_3_10", "pass": sys.version_info[:2] == (3, 10)},
              {"name": "linux", "pass": sys.platform == "linux"},
              {"name": "nvidia_smi_available", "pass": shutil.which("nvidia-smi") is not None},
              {"name": "ffmpeg_available", "pass": shutil.which("ffmpeg") is not None}]
    for package in PACKAGES:
        version = packages.get(package.lower().replace("_", "-"))
        checks.append({"name": package, "pass": version is not None, "version": version})
    try:
        source_check(root)
        checks.append({"name": "source_and_patch", "pass": True})
    except CheckError as exc:
        checks.append({"name": "source_and_patch", "pass": False, "reason": str(exc)})
    return {"kind": "preflight_only", "checks": checks,
            "pass": all(c["pass"] for c in checks),
            "warning": "Presence checks do not prove ABI compatibility, model availability or GPU success."}


def verify_asset_lock(root, manifest):
    data = json.loads(Path(manifest).read_text())
    entries = data.get("files", [])
    if not entries:
        raise CheckError("asset lock is empty; locally acquire licensed models and inventory them first")
    for entry in entries:
        if not re.fullmatch(r"[0-9a-f]{64}", entry.get("sha256", "")):
            raise CheckError("asset lock contains an invalid SHA256")
        p = confined(root, entry["path"])
        if not p.is_file() or sha256(p) != entry["sha256"]:
            raise CheckError("asset missing or checksum mismatch: " + entry["path"])
    return {"files_verified": len(entries), "warning": "Hashes identify local bytes, not license or model suitability."}


def inventory(root, paths):
    files = {}
    for selected in paths:
        p = confined(root, selected)
        candidates = sorted(p.rglob("*")) if p.is_dir() else [p]
        for candidate in candidates:
            # Resolve symlinks for reading, but retain the requested relative name.
            real = confined(root, candidate)
            if real.is_file():
                relative = str(candidate.relative_to(Path(root).resolve()))
                files[relative] = {"path": relative, "bytes": real.stat().st_size, "sha256": sha256(real)}
    if not files:
        raise CheckError("no files found under explicitly selected paths")
    return {"schema_version": 1, "kind": "local_byte_inventory", "files": list(files.values())}


def nonempty(path):
    if not path.is_file() or path.stat().st_size == 0:
        raise CheckError("missing or empty artifact: " + path.name)


def check_glb(path):
    nonempty(path)
    with path.open("rb") as f:
        header = f.read(12)
        if len(header) != 12:
            raise CheckError("truncated GLB header")
        magic, version, length = struct.unpack("<4sII", header)
        if magic != b"glTF" or version != 2 or length != path.stat().st_size:
            raise CheckError("invalid GLB header or length")
        chunks = 0
        while f.tell() < length:
            chunk_header = f.read(8)
            if len(chunk_header) != 8:
                raise CheckError("truncated GLB chunk")
            size, kind = struct.unpack("<I4s", chunk_header)
            if size % 4 or size == 0 or size > length - f.tell():
                raise CheckError("invalid GLB chunk size")
            payload = f.read(size)
            if chunks == 0:
                if kind != b"JSON":
                    raise CheckError("GLB first chunk must be JSON")
                try:
                    data = json.loads(payload)
                except (ValueError, UnicodeError) as exc:
                    raise CheckError("invalid GLB JSON") from exc
                if not isinstance(data, dict) or data.get("asset", {}).get("version") != "2.0":
                    raise CheckError("missing glTF 2.0 asset metadata")
            elif chunks != 1 or kind != b"BIN\x00":
                raise CheckError("unsupported GLB chunk order")
            chunks += 1
        if not chunks:
            raise CheckError("GLB has no JSON chunk")


def check_masks(root, key, trust=False):
    if not trust:
        raise CheckError("pickle can execute code; only use --trust-local-pickle for your own generated scene.pkl")
    path = confined(root, f"outputs/{key_name(key)}/scene/scene.pkl")
    nonempty(path)
    with path.open("rb") as f:
        scene = pickle.load(f)  # Explicitly gated trusted-local operation, never used by default.
    masks = scene.get("mask") if isinstance(scene, dict) else None
    if not isinstance(masks, (dict, list)) or not masks:
        raise CheckError("scene has no saved mask collection")
    images = scene.get("images")
    shape = getattr(images, "shape", ())
    if len(shape) != 4 or shape[-1] != 3 or shape[0] < 1:
        raise CheckError("scene images must have shape [N,H,W,3]")
    objects = masks.get(0) if isinstance(masks, dict) else masks[0]
    if not isinstance(objects, dict) or not objects:
        raise CheckError("frame 0 has no saved masks")
    names = []
    for oid, item in objects.items():
        if not isinstance(oid, int) or isinstance(oid, bool) or oid < 1:
            raise CheckError("mask object ID must be a positive integer")
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise CheckError("invalid saved mask object")
        name = item["name"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", name):
            raise CheckError("mask object name is unsafe for asset filenames")
        mask = item.get("mask")
        if getattr(mask, "shape", None) != tuple(shape[1:3]) or getattr(mask, "dtype", None) != bool or not bool(mask.any()):
            raise CheckError("mask must be a nonempty boolean array matching image H,W")
        box = item.get("bbox")
        if box is None or len(box) != 4:
            raise CheckError("mask bbox must have four coordinates")
        try:
            x1, y1, x2, y2 = map(float, box)
            if not (0 <= x1 <= x2 <= shape[2] and 0 <= y1 <= y2 <= shape[1]):
                raise CheckError("mask bbox outside image")
        except (ValueError, TypeError) as exc:
            raise CheckError("invalid mask bbox") from exc
        names.append(name)
    if "ground" not in names or not any(n not in {"ground", "hand", "robot"} for n in names):
        raise CheckError("frame 0 requires ground and a reconstructable object")
    return {"kind": "annotation_seed_structure", "pass": True,
            "warning": "Mask quality and video coverage require visual review."}


def check_artifacts(root, key, stage):
    base = confined(root, f"outputs/{key_name(key)}")
    if stage == "preprocess":
        nonempty(confined(base, "scene/scene.pkl"))
        frames = list(confined(base, "images").glob("*.jpg")) + list(confined(base, "images").glob("*.png"))
        if not frames:
            raise CheckError("no extracted image frames")
        for frame in frames:
            nonempty(confined(base, frame))
        return {"kind": "preprocess_file_structure", "frame_count": len(frames), "pass": True,
                "warning": "No pickle deserialization; depth/camera content is not validated."}
    sim = confined(base, "simulation")
    scene_path = confined(sim, "scene.json")
    nonempty(scene_path)
    data = json.loads(scene_path.read_text())
    refs = [data.get("background_image"), data.get("background", {}).get("registered"),
            data.get("scene_mesh", {}).get("optimized")]
    objects = data.get("objects")
    if not isinstance(objects, dict) or not objects:
        raise CheckError("scene.json has no objects")
    for obj in objects.values():
        if not isinstance(obj, dict):
            raise CheckError("invalid object record")
        refs.extend(obj.get(field) for field in ("optimized", "fdpose_trajs", "simple_trajs", "hybrid_trajs"))
    for ref in refs:
        if not isinstance(ref, str) or not ref:
            raise CheckError("scene.json is missing a full-pipeline asset reference")
        p = Path(ref)
        # Upstream writes absolute paths. Relative portable paths resolve against scene.json.
        p = confined(sim, p if p.is_absolute() else ref)
        nonempty(p)
        if p.suffix.lower() == ".glb":
            check_glb(p)
    return {"kind": "full_reconstruction_file_structure", "pass": True, "objects": len(objects),
            "references_checked": len(refs),
            "warning": "This is not mesh quality, physics, trajectory semantics or simulator acceptance."}


def command(stage, key, python=sys.executable):
    key_name(key)
    args = STAGES[stage]
    if stage == "annotate":
        return [python, *args, "--key", key, "--server-name", "127.0.0.1"]
    return [python, *args, key]


def run(args):
    root = args.root.resolve()
    cmd = command(args.stage, args.key)
    if not args.execute:
        emit({"kind": "plan_not_execution", "argv": cmd, "cwd": "<upstream-checkout>",
              "network": "HF offline flags only; use container network isolation", "annotation_key_to_enter": args.key if args.stage == "annotate" else None})
        return 0
    if not args.trust_local_code:
        raise CheckError("inspect upstream/submodules and use --trust-local-code before execution")
    if args.stage in {"annotate", "reconstruct", "motion"} and not args.trust_local_pickle:
        raise CheckError("this upstream stage reads pickle; use --trust-local-pickle only for your own generated artifacts")
    if args.report is None:
        raise CheckError("--report is required for real runs")
    if args.report.exists():
        raise CheckError("report already exists; choose a new output path")
    source_check(root)
    output_dir = confined(root, f"outputs/{args.key}")
    resume = getattr(args, "resume", False)
    if args.stage == "preprocess" and output_dir.exists() and not resume:
        raise CheckError("output already exists; choose a new key or explicitly --resume")
    inputs = {}
    for suffix in (".jpg", ".png", ".mp4", ".r3d", "_depth.png"):
        candidate = confined(root, f"data/{args.key}{suffix}")
        if candidate.is_file():
            inputs[candidate.name] = sha256(candidate)
    rgb_inputs = [name for name in inputs if not name.endswith("_depth.png")]
    if args.stage == "preprocess" and len(rgb_inputs) != 1:
        raise CheckError("preprocess requires exactly one RGB image, video or R3D input for the key")
    try:
        import yaml
    except ImportError as exc:
        raise CheckError("PyYAML is required in the target environment") from exc
    config = yaml.safe_load(confined(root, "config/config.yaml").read_text())
    if args.key not in config.get("keys", []):
        raise CheckError("key is absent from config/config.yaml")
    if args.assets_lock is None:
        raise CheckError("--assets-lock is required; empty model inventory is not a runnable environment")
    verify_asset_lock(root, args.assets_lock)
    if args.stage in {"annotate", "reconstruct"}:
        check_artifacts(root, args.key, "preprocess")
    if args.stage == "reconstruct":
        check_masks(root, args.key, args.trust_local_pickle)
    if args.stage in {"motion", "usd", "rollout", "randomize"}:
        check_artifacts(root, args.key, "reconstruct")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root), str(root / "openreal2sim/preprocess")])
    env["GRADIO_ANALYTICS_ENABLED"] = "False"
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    started = time.monotonic()
    record = {"schema_version": 1, "key": args.key, "stage": args.stage, "source_commit": PIN,
              "resume": resume, "input_sha256": inputs,
              "config_sha256": sha256(confined(root, "config/config.yaml")),
              "asset_manifest_sha256": sha256(args.assets_lock),
              "patch_sha256": sha256(HERE / "patches/0001-safe-cli.patch"),
              "status": "running", "upstream_exit_code": None, "artifact_acceptance": "not_checked",
              "environment": capture(), "privacy": "Inspect upstream terminal logs before sharing; they may contain paths."}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(record, indent=2) + "\n")
    try:
        result = subprocess.run(cmd, cwd=root, env=env, check=False)
        record["upstream_exit_code"] = result.returncode
        record["status"] = "process_passed" if result.returncode == 0 else "process_failed"
        if result.returncode == 0 and args.stage in {"preprocess", "reconstruct"}:
            record["artifact_acceptance"] = check_artifacts(root, args.key, args.stage)
        elif result.returncode == 0:
            record["artifact_acceptance"] = "manual_acceptance_required"
    except (CheckError, OSError, ValueError, TypeError, KeyError, EOFError, AttributeError, KeyboardInterrupt) as exc:
        record["status"] = "failed_or_interrupted"
        record["error_type"] = type(exc).__name__
    finally:
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        args.report.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "process_passed" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("source-check", "preflight"):
        p = sub.add_parser(name)
        p.add_argument("--root", required=True, type=Path)
    p = sub.add_parser("capture-env")
    p.add_argument("--output", type=Path)
    p = sub.add_parser("inventory")
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--paths", nargs="+", required=True)
    p.add_argument("--output", required=True, type=Path)
    p = sub.add_parser("verify-assets")
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    p = sub.add_parser("check")
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--key", required=True)
    p.add_argument("--stage", choices=["preprocess", "masks", "reconstruct"], required=True)
    p.add_argument("--trust-local-pickle", action="store_true")
    p = sub.add_parser("run")
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--key", required=True)
    p.add_argument("--stage", choices=list(STAGES), required=True)
    p.add_argument("--execute", action="store_true")
    p.add_argument("--resume", action="store_true", help="Explicitly reuse existing output; does not prove prior-run identity")
    p.add_argument("--trust-local-code", action="store_true")
    p.add_argument("--trust-local-pickle", action="store_true")
    p.add_argument("--assets-lock", type=Path)
    p.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "run":
            return run(args)
        if args.cmd == "source-check":
            result = source_check(args.root)
        elif args.cmd == "preflight":
            result = preflight(args.root)
        elif args.cmd == "capture-env":
            result = capture()
        elif args.cmd == "inventory":
            result = inventory(args.root.resolve(), args.paths)
        elif args.cmd == "verify-assets":
            result = verify_asset_lock(args.root, args.manifest)
        elif args.stage == "masks":
            result = check_masks(args.root, args.key, args.trust_local_pickle)
        else:
            result = check_artifacts(args.root, args.key, args.stage)
        emit(result, getattr(args, "output", None))
        return 0 if result.get("pass", True) else 1
    except (CheckError, OSError, ValueError, TypeError, KeyError, pickle.UnpicklingError, EOFError, AttributeError) as exc:
        # Do not expose raw exception messages from third-party parsers or private absolute paths.
        message = str(exc) if isinstance(exc, CheckError) else type(exc).__name__
        print(json.dumps({"pass": False, "error": message}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
