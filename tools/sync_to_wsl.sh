#!/usr/bin/env bash
# Mirror the repo (which lives on a Windows drive, path with spaces) into a WSL-native
# directory so EDA tools can run on it.  Run inside WSL:
#   bash "/mnt/d/MBIST-BISR-BIRA SRAM ASIC PROJECT/tools/sync_to_wsl.sh"
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST="${TRIAD_ROOT:-$HOME/work/triad_bisr}"
case "$SRC" in "$DST"|"$DST"/*) echo "sync_to_wsl: already inside the mirror, nothing to do"; exit 0 ;; esac
mkdir -p "$DST/build"
rsync -rlt --delete --chmod=D755,F644 \
  --exclude '.git/' --exclude 'build/' --exclude '__pycache__/' --exclude '.pytest_cache/' --exclude 'sim_build/' \
  "$SRC"/ "$DST"/
chmod +x "$DST"/tools/*.sh "$DST"/tools/bin/* "$DST"/tools/setup/*.sh 2>/dev/null || true
printf '%s\n' "$SRC" > "$DST/build/.src_path"
echo "synced: $SRC -> $DST"
