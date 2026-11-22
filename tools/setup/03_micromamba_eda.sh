#!/usr/bin/env bash
# Native ngspice / Magic / Netgen (LVS) without sudo, via micromamba.  The sign-off flow still uses
# the versions inside the OpenLane image; these are for interactive work and SPICE simulation.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../env.sh"
MM_VER=2.10.0-0
MM_SHA=701f39c06f8e6a670a0e186c8479b9e5c0502a2f0cda6cef65d83bdd2875e8bd
MM="$EDA_TOOLS/bin/micromamba"
mkdir -p "$EDA_TOOLS/bin" "$EDA_TOOLS/dl"
if [ ! -x "$MM" ]; then
  curl -fsSL -m 300 -o "$EDA_TOOLS/dl/micromamba-linux-64" \
    "https://github.com/mamba-org/micromamba-releases/releases/download/$MM_VER/micromamba-linux-64"
  echo "$MM_SHA  $EDA_TOOLS/dl/micromamba-linux-64" | sha256sum -c -
  install -m 755 "$EDA_TOOLS/dl/micromamba-linux-64" "$MM"
fi
# conda-forge: ngspice + magic (VLSI layout).  litex-hub: netgen (LVS) -- conda-forge "netgen" is a mesher.
[ -d "$MAMBA_ROOT_PREFIX/envs/eda" ] || "$MM" create -y -q -n eda --override-channels -c conda-forge \
  "ngspice=${NGSPICE_VER:-41}" "magic=${MAGIC_VER:-8.3.678}" </dev/null
[ -d "$MAMBA_ROOT_PREFIX/envs/netgen" ] || "$MM" create -y -q -n netgen --override-channels -c litex-hub -c conda-forge \
  "litex-hub::netgen=${NETGEN_VER:-1.5.272_0_g178af5f}" </dev/null
launcher() {  # launcher <name> <env> <binary>
  printf '#!/usr/bin/env bash\nexec "%s" run -r "%s" -n %s %s "$@"\n' "$MM" "$MAMBA_ROOT_PREFIX" "$2" "$3" > "$EDA_TOOLS/bin/$1"
  chmod +x "$EDA_TOOLS/bin/$1"
}
launcher ngspice eda ngspice
launcher magic eda magic
launcher netgen netgen netgen
launcher netgen-lvs netgen netgen
