#!/usr/bin/env python3
"""Verify tracked delivery bytes, local Markdown links, JSON and Python syntax.

This checks the engineering package only, not OpenReal2Sim inference.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {".git", "__pycache__", ".pytest_cache"}


def files():
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and not any(part in EXCLUDE for part in p.parts))


def main():
    errors = []
    manifest = ROOT / "SHA256SUMS"
    expected = {}
    for line in manifest.read_text().splitlines():
        digest, relative = line.split("  ", 1)
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append("invalid digest: " + relative)
        p = (ROOT / relative).resolve()
        if not p.is_relative_to(ROOT) or not p.is_file():
            errors.append("missing or unsafe manifest path: " + relative)
            continue
        expected[relative] = digest
        if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            errors.append("checksum mismatch: " + relative)
    actual = {str(p.relative_to(ROOT)) for p in files() if p.name != "SHA256SUMS"}
    if actual != set(expected):
        errors.append("manifest does not exactly cover deliverable files")
    for p in files():
        try:
            if p.suffix == ".json":
                json.loads(p.read_text())
            if p.suffix == ".py":
                ast.parse(p.read_text())
            if p.suffix == ".md":
                for link in re.findall(r"\]\(([^ )]+)", p.read_text()):
                    if "://" in link or link.startswith(("#", "mailto:")):
                        continue
                    if not (p.parent / link.split("#", 1)[0]).exists():
                        errors.append("broken local link in " + str(p.relative_to(ROOT)) + ": " + link)
        except (ValueError, SyntaxError, UnicodeDecodeError) as exc:
            errors.append(str(p.relative_to(ROOT)) + ": " + type(exc).__name__)
    print(json.dumps({"kind": "repository_integrity_only", "pass": not errors,
                      "files": len(actual), "errors": errors}, indent=2))
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
