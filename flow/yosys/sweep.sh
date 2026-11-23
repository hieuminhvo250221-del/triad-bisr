#!/usr/bin/env bash
# Synthesis sweep: PBITS x R grid through flow/yosys/synth.sh, collected into one CSV.
#   bash flow/yosys/sweep.sh [out.csv]
# Columns: pbits,r,module,area_um2,cells,ffs
#   module = base module name (the $paramod$HASH\ suffix yosys adds is stripped)
#   TOTAL  = the "=== design hierarchy ===" chip-area line, i.e. the HIERARCHICAL total:
#            every instance counted, so it is not the plain sum of the per-module-type rows
#            (e.g. word_class is instantiated once per spare-word slot).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
out_csv="${1:-$TRIAD_BUILD/export/ppa/synth_sweep.csv}"
mkdir -p "$(dirname "$out_csv")"
echo "pbits,r,module,area_um2,cells,ffs" > "$out_csv"
for pbits in 1 2 3 4; do
    for r in 1 2 4; do
        bash flow/yosys/synth.sh "$pbits" "$r" >/dev/null
        python3 - "$out_csv" "$pbits" "$r" "$TRIAD_BUILD/yosys/p${pbits}_r${r}/area.rpt" <<'PY'
import re, sys
csv_path, pbits, r, rpt = sys.argv[1:5]
blocks = re.split(r"\n=== (.+?) ===\n", open(rpt).read())
out = open(csv_path, "a")
for nm, body in zip(blocks[1::2], blocks[2::2]):
    area = re.search(r"Chip area for (?:module|top module) '[^']*':\s*([0-9.]+)", body)
    cells = re.search(r"^\s*(\d+)\s+[\d.E+-]*\s*cells$", body, re.M) or re.search(r"Number of cells:\s*(\d+)", body)
    ffs = sum(int(n) for n, c in re.findall(r"^\s*(\d+)\s+[\d.E+-]*\s*(\S+)$", body, re.M) if "__df" in c)
    base = re.sub(r"^\$paramod\$[0-9a-f]+\\", "", nm.strip())
    if nm.strip() == "design hierarchy":
        base = "TOTAL"
    out.write(f"{pbits},{r},{base},{float(area.group(1)):.0f},{cells.group(1) if cells else 0},{ffs}\n")
out.close()
PY
        echo "done PBITS=$pbits R=$r"
    done
done
echo "wrote $out_csv"
