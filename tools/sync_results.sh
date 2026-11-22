#!/usr/bin/env bash
# Copy curated artifacts (build/export/**) from the WSL mirror back into results/ of the repo.
# Run inside WSL from anywhere:  bash ~/work/triad_bisr/tools/sync_results.sh
set -euo pipefail
DST_MIRROR="${TRIAD_ROOT:-$HOME/work/triad_bisr}"
SRC_REPO="$(cat "$DST_MIRROR/build/.src_path")"
[ -d "$DST_MIRROR/build/export" ] || { echo "nothing to export"; exit 0; }
mkdir -p "$SRC_REPO/results"
rsync -rlt --chmod=D755,F644 "$DST_MIRROR/build/export"/ "$SRC_REPO/results"/
echo "exported: $DST_MIRROR/build/export -> $SRC_REPO/results"
