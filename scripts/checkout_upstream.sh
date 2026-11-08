#!/usr/bin/env bash
# Fetch pinned source only. Does not install packages, run upstream code or download model weights.
set -euo pipefail
if [[ $# != 1 ]]; then
  echo 'Usage: bash scripts/checkout_upstream.sh /absolute/new/OpenReal2Sim' >&2
  exit 2
fi
DEST="$1"
case "$DEST" in /*) ;; *) echo 'Destination must be absolute.' >&2; exit 2 ;; esac
if [[ -e "$DEST" ]]; then
  echo 'Destination already exists. Refusing to overwrite it.' >&2
  exit 1
fi
NOTES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIN=8f69a19e5dfdfe0aad906fdacad0decf862a7adf
git clone --no-checkout https://github.com/PointsCoder/OpenReal2Sim.git "$DEST"
git -C "$DEST" checkout --detach "$PIN"
# Rewrite GitHub SSH transport for this command only, not global user settings.
git -C "$DEST" -c url.https://github.com/.insteadOf=git@github.com: submodule update --init --recursive
git -C "$DEST" apply --check "$NOTES_DIR/patches/0001-safe-cli.patch"
git -C "$DEST" apply "$NOTES_DIR/patches/0001-safe-cli.patch"
python3 "$NOTES_DIR/scripts/repro.py" source-check --root "$DEST"
echo 'Pinned source prepared. Models, native builds and GPU validation are still required.'
