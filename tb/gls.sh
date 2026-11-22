#!/usr/bin/env bash
# Gate-level simulation of the routed netlist for OpenLane run <tag>: functional (no SDF), Icarus,
# sky130_fd_sc_hd cell models from the PDK and the fault-injectable macro model (sram_fault_model.v
# is added by tb/run.sh).  Usage:  bash tb/gls.sh <tag>
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
tag="${1:?usage: tb/gls.sh <run tag>}"
nl="../flow/openlane/triad_bisr_top/runs/$tag/results/final/verilog/gl/triad_bisr_top.nl.v"
sc="$PDK_ROOT/$PDK/libs.ref/sky130_fd_sc_hd/verilog"
[ -f "$nl" ] || { echo "no routed netlist at $nl" >&2; exit 1; }
[ -f "$sc/sky130_fd_sc_hd.v" ] || { echo "no cell models at $sc" >&2; exit 1; }
export EXTRA_COMPILE_ARGS="-DFUNCTIONAL -I$sc"
bash run.sh gls_tb test_gls "$nl" "$sc/primitives.v" "$sc/sky130_fd_sc_hd.v" gls_tb.v
