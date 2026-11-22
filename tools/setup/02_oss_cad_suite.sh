#!/usr/bin/env bash
# OSS CAD Suite (YosysHQ): recent Yosys, Icarus Verilog, Verilator, SymbiYosys, GTKWave.  User-level.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../env.sh"
DATE="${OSS_CAD_DATE:-2026-11-14}"
TGZ="oss-cad-suite-linux-x64-${DATE//-/}.tgz"
URL="https://github.com/YosysHQ/oss-cad-suite-build/releases/download/$DATE/$TGZ"
DEST="$EDA_TOOLS/oss-cad-suite-${DATE//-/}"
mkdir -p "$EDA_TOOLS/dl"
if [ ! -x "$DEST/bin/yosys" ]; then
  [ -f "$EDA_TOOLS/dl/$TGZ" ] || curl -fsSL --retry 3 -m 3000 -o "$EDA_TOOLS/dl/$TGZ.part" "$URL"
  [ -f "$EDA_TOOLS/dl/$TGZ" ] || mv "$EDA_TOOLS/dl/$TGZ.part" "$EDA_TOOLS/dl/$TGZ"
  sha256sum "$EDA_TOOLS/dl/$TGZ"
  rm -rf "$DEST.tmp" && mkdir -p "$DEST.tmp"
  tar -xzf "$EDA_TOOLS/dl/$TGZ" -C "$DEST.tmp" --strip-components=1
  mv "$DEST.tmp" "$DEST"
fi
ln -sfn "$DEST" "$EDA_TOOLS/oss-cad-suite"
"$EDA_TOOLS/oss-cad-suite/bin/yosys" -V
