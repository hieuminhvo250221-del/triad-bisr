#!/usr/bin/env bash
# Tectonic: self-contained LaTeX engine (fetches TeX Live packages on demand).  User-level.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../env.sh"
VER="${TECTONIC_VER:-0.17.0+20260731}"
TGZ="tectonic-${VER}-x86_64-unknown-linux-musl.tar.gz"
URL="https://github.com/tectonic-typesetting/tectonic/releases/download/continuous/${TGZ//+/%2B}"
mkdir -p "$EDA_TOOLS/bin" "$EDA_TOOLS/dl"
if [ ! -x "$EDA_TOOLS/bin/tectonic" ]; then
  curl -fsSL --retry 3 -m 600 -o "$EDA_TOOLS/dl/$TGZ" "$URL"
  sha256sum "$EDA_TOOLS/dl/$TGZ"
  tar -xzf "$EDA_TOOLS/dl/$TGZ" -C "$EDA_TOOLS/bin" tectonic
fi
"$EDA_TOOLS/bin/tectonic" --version
