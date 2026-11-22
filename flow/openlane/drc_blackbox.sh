#!/usr/bin/env bash
# Magic DRC on the final GDS with the OpenRAM macro kept as an abstract view (pre-verified hard IP):
# everything else (standard cells, routing, power grid) is checked at full detail.
#   flow/openlane/drc_blackbox.sh <tag>
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
tag="$1"
run="$TRIAD_ROOT/flow/openlane/triad_bisr_top/runs/$tag"
out="$TRIAD_BUILD/export/asic/$tag"; mkdir -p "$out"
cat > "$run/drc_blackbox.tcl" <<EOF
drc off
load $SRAM_MACRO_DIR/maglef/sky130_sram_1kbyte_1rw1r_32x256_8.mag
gds noduplicates true
gds read $run/results/final/gds/triad_bisr_top.gds
load triad_bisr_top
select top cell
expand
drc style drc(full)
drc euclidean on
drc check
drc catchup
set res [drc listall why]
set total 0
foreach {rule boxes} \$res { incr total [llength \$boxes] }
set fh [open $out/drc_blackbox.rpt w]
puts \$fh "Magic DRC, final GDS, SRAM macro as abstract view"
puts \$fh "total: \$total"
foreach {rule boxes} \$res { puts \$fh "[llength \$boxes]  \$rule" }
close \$fh
puts "DRC_BLACKBOX_TOTAL \$total"
quit -noprompt
EOF
cd "$run"
ol-exec magic -dnull -noconsole -rcfile "$PDK_ROOT/$PDK/libs.tech/magic/$PDK.magicrc" "$run/drc_blackbox.tcl" > "$run/drc_blackbox.log" 2>&1 || true
grep -E 'DRC_BLACKBOX_TOTAL' "$run/drc_blackbox.log" || echo "DRC_BLACKBOX: no result, see $run/drc_blackbox.log"
head -12 "$out/drc_blackbox.rpt" 2>/dev/null
