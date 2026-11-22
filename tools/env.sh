#!/usr/bin/env bash
# Project environment for WSL (Ubuntu 22.04).  Usage:  source tools/env.sh
# Everything is user-level; nothing outside $HOME/work is modified.

export TRIAD_ROOT="${TRIAD_ROOT:-$HOME/work/triad_bisr}"   # WSL-native mirror of the repo (path without spaces)
export EDA_TOOLS="${EDA_TOOLS:-$HOME/work/eda-tools}"       # user-level tool installs
export TRIAD_BUILD="${TRIAD_BUILD:-$TRIAD_ROOT/build}"      # every generated file goes here

# PDK installed with ciel (open_pdks 0fe599b = the version pinned by OpenLane 1.0.2)
export PDK_ROOT="${PDK_ROOT:-$HOME/.ciel}"
export PDK="${PDK:-sky130A}"
export STD_CELL_LIBRARY="${STD_CELL_LIBRARY:-sky130_fd_sc_hd}"
export SRAM_MACRO_DIR="$PDK_ROOT/$PDK/libs.ref/sky130_sram_macros"

# OpenLane 1 in Docker. Tag = upstream commit that ~/OpenLane (v1.0.2) is based on.
export OPENLANE_ROOT="${OPENLANE_ROOT:-$HOME/OpenLane}"
export OPENLANE_IMAGE_NAME="${OPENLANE_IMAGE_NAME:-ghcr.io/the-openroad-project/openlane:ff5509f65b17bfa4068d5336495ab1718987ff69}"
export OPENLANE_IMAGE="${OPENLANE_IMAGE:-${OPENLANE_IMAGE_NAME}-amd64}"

# OpenROAD-flow-scripts (native): OpenROAD 26Q2 binary + Yosys from OSS CAD Suite
export ORFS_ROOT="${ORFS_ROOT:-$EDA_TOOLS/OpenROAD-flow-scripts}"
export FLOW_HOME="$ORFS_ROOT/flow"
export OPENROAD_EXE="${OPENROAD_EXE:-$HOME/.local/bin/openroad}"
export OPENSTA_EXE="${OPENSTA_EXE:-$HOME/.local/opt/openroad-26Q2-1164-g08f67ee5ec/usr/bin/sta}"
export YOSYS_EXE="${YOSYS_EXE:-$EDA_TOOLS/oss-cad-suite/bin/yosys}"

export MAMBA_ROOT_PREFIX="$EDA_TOOLS/mamba"

_triad_prepend() { [ -d "$1" ] || return 0; case ":$PATH:" in *":$1:"*) ;; *) PATH="$1:$PATH" ;; esac; }
_triad_prepend "$EDA_TOOLS/oss-cad-suite/bin"   # yosys, iverilog, verilator, sby, gtkwave (newer than apt)
_triad_prepend "$EDA_TOOLS/bin"                 # micromamba, tectonic, ngspice/magic/netgen launchers
_triad_prepend "$TRIAD_ROOT/tools/bin"          # project wrappers (ol-exec, ol-flow, ...)
if [ -d "$EDA_TOOLS/venv" ]; then
  export VIRTUAL_ENV="$EDA_TOOLS/venv"
  _triad_prepend "$VIRTUAL_ENV/bin"
fi
export PATH
unset -f _triad_prepend
