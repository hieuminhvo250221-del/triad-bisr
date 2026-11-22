#!/usr/bin/env bash
# Fresh, sparse OpenROAD-flow-scripts checkout (the old ~/OpenROAD-flow-scripts is left untouched).
# No compilation: it uses the OpenROAD 26Q2 binary in ~/.local and Yosys from OSS CAD Suite.
# sky130hs is checked out too because sky130hd/rcx_patterns.rules is a symlink into it.
# Tag 26Q2 = newest ORFS tag whose OpenROAD submodule (2026-04-06) is older than the binary (2026-05-12).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../env.sh"
TAG="${ORFS_TAG:-26Q2}"
if [ ! -d "$ORFS_ROOT/.git" ]; then
  git clone --filter=blob:none --no-checkout --depth 1 --branch "$TAG" \
    https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts.git "$ORFS_ROOT" </dev/null
  git -C "$ORFS_ROOT" sparse-checkout init --cone
  git -C "$ORFS_ROOT" sparse-checkout set flow/scripts flow/util flow/platforms/common \
    flow/platforms/sky130hd flow/platforms/sky130hs flow/platforms/sky130ram \
    flow/designs/sky130hd/gcd flow/designs/src/gcd flow/designs/sky130hd/chameleon flow/designs/src/chameleon
  git -C "$ORFS_ROOT" checkout -q "$TAG" </dev/null
fi
git -C "$ORFS_ROOT" log -1 --format='ORFS %h %ad %s' --date=short
du -sh "$ORFS_ROOT" | cut -f1
