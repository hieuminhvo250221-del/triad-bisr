#!/usr/bin/env bash
# Quick synthesis for area exploration (not the sign-off flow):  flow/yosys/synth.sh <PBITS> <R> [NBG]
# Prints the cell area of the wrapper logic per module, mapped to sky130_fd_sc_hd (tt, 1.8 V, 25 C).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
pbits="${1:-4}"; r="${2:-2}"; nbg="${3:-6}"
lib="$PDK_ROOT/$PDK/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
out="$TRIAD_BUILD/yosys/p${pbits}_r${r}"; mkdir -p "$out"
cd "$TRIAD_ROOT"
cat > "$out/synth.ys" <<EOF
read_verilog flow/common/sram_blackbox.v
read_verilog rtl/ecc30_24.v rtl/triad_datapath.v rtl/mbist_march.v rtl/alloc_enum.v rtl/alloc_dp.v rtl/bisr_ctrl.v rtl/triad_bisr_top.v
chparam -set PBITS $pbits -set R $r -set NBG $nbg triad_bisr_top
hierarchy -check -top triad_bisr_top
synth -top triad_bisr_top
dfflibmap -liberty $lib
abc -liberty $lib
opt_clean -purge
tee -o $out/area.rpt stat -liberty $lib
write_verilog -noattr $out/netlist.v
EOF
yosys -q -l "$out/yosys.log" "$out/synth.ys" </dev/null
python3 - "$out/area.rpt" "$pbits" "$r" <<'PY'
import re, sys
text = open(sys.argv[1]).read()
blocks = re.split(r"\n=== (.+?) ===\n", text)
rows = {}
for name, body in zip(blocks[1::2], blocks[2::2]):
    area = re.search(r"Chip area for (?:module|top module) '[^']*':\s*([0-9.]+)", body)
    cells = re.search(r"^\s*(\d+)\s+[\d.E+-]*\s*cells$", body, re.M) or re.search(r"Number of cells:\s*(\d+)", body)
    ffs = sum(int(n) for n, c in re.findall(r"^\s*(\d+)\s+[\d.E+-]*\s*(\S+)$", body, re.M) if "__df" in c)
    if area:
        rows[name.strip()] = (float(area.group(1)), int(cells.group(1)) if cells else 0, ffs)
print(f"PBITS={sys.argv[2]} R={sys.argv[3]}  (area in um^2 of standard cells, before place and route)")
for name, (a, c, f) in rows.items():
    print(f"  {name[:60]:60s} area={a:10.0f} cells={c:6d} ffs={f:5d}")
PY
