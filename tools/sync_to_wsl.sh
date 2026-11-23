#!/usr/bin/env bash
# Mirror the repo (which lives on a Windows drive, path with spaces) into a WSL-native
# directory so EDA tools can run on it.  Run inside WSL:
#   bash "/mnt/d/MBIST-BISR-BIRA SRAM ASIC PROJECT/tools/sync_to_wsl.sh"
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST="${TRIAD_ROOT:-$HOME/work/triad_bisr}"
case "$SRC" in "$DST"|"$DST"/*) echo "sync_to_wsl: already inside the mirror, nothing to do"; exit 0 ;; esac
mkdir -p "$DST/build"
# Files written from Windows tools may arrive with CRLF; the repository is LF-only (.gitattributes).
(grep -rlI --exclude-dir=.git --exclude-dir=results $'\r' "$SRC" 2>/dev/null || true) | while IFS= read -r f; do
  sed -i 's/\r$//' "$f" && echo "normalised line endings: $f"
done
rsync -rlt --delete --chmod=D755,F644 \
  --exclude '.git/' --exclude 'build/' --exclude 'runs/' --exclude '__pycache__/' --exclude '.pytest_cache/' --exclude 'sim_build/' \
  --exclude 'site/node_modules/' --exclude 'site/dist/' --exclude 'site/.astro/' --exclude 'site/.screens/' \
  "$SRC"/ "$DST"/
chmod +x "$DST"/tools/*.sh "$DST"/tools/bin/* "$DST"/tools/setup/*.sh 2>/dev/null || true
printf '%s\n' "$SRC" > "$DST/build/.src_path"
echo "synced: $SRC -> $DST"
