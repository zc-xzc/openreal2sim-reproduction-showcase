#!/usr/bin/env python3
"""Check a distribution's shared files, optionally against its local peer.

This is a local, read-only byte comparison. It never reads original archives,
connects to GitHub, or certifies inference, licenses, or absence of private data.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

CONTRACT = "reports/distribution-contract.json"


def safe_file(root, relative):
    if not isinstance(relative, str):
        raise ValueError("contract path must be a string")
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or any(x in {".", ".."} for x in relative.split("/")) or "\\" in relative:
        raise ValueError("unsafe contract path")
    target = root / relative
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlink is not allowed: " + relative)
    if not target.is_file():
        raise ValueError("missing file: " + relative)
    return target


def load_contract(root):
    data = json.loads(safe_file(root, CONTRACT).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("unsupported distribution contract")
    shared = data.get("shared_paths")
    variants = data.get("variant_paths")
    if not isinstance(shared, list) or not shared or not isinstance(variants, list):
        raise ValueError("invalid shared or variant path list")
    for paths in (shared, variants):
        if any(not isinstance(p, str) for p in paths) or len(paths) != len(set(paths)):
            raise ValueError("invalid or duplicate contract paths")
    if set(shared) & set(variants):
        raise ValueError("shared and variant paths overlap")
    for relative in shared + variants:
        safe_file(root, relative)
    return data


def verify(root, peer=None):
    root = Path(root).resolve()
    errors = []
    compared = 0
    try:
        contract = load_contract(root)
        if peer is not None:
            peer = Path(peer).resolve()
            if peer == root:
                raise ValueError("peer must be a different directory")
            other = load_contract(peer)
            if other != contract:
                raise ValueError("peer distribution contract differs")
            for relative in contract["shared_paths"]:
                local_hash = hashlib.sha256(safe_file(root, relative).read_bytes()).digest()
                peer_hash = hashlib.sha256(safe_file(peer, relative).read_bytes()).digest()
                compared += 1
                if local_hash != peer_hash:
                    errors.append("shared content differs: " + relative)
        count = len(contract["shared_paths"])
    except (OSError, ValueError, TypeError) as exc:
        # Avoid printing raw paths, archive identifiers, or exception text.
        errors.append(str(exc) if isinstance(exc, ValueError) and not isinstance(exc, json.JSONDecodeError) else "unable to read a valid local distribution")
        count = 0
    return {"kind": "local_distribution_coverage_only", "pass": not errors,
            "shared_files": count, "peer_files_compared": compared,
            "peer_checked": peer is not None, "errors": errors,
            "not_verified": ["original preservation bytes", "remote state", "privacy clearance", "GPU reproduction"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--peer", type=Path, help="Optional local checkout of the other distribution")
    args = parser.parse_args()
    result = verify(Path(__file__).resolve().parents[1], args.peer)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
