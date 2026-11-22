#!/usr/bin/env bash
# Smoke test of the OpenLane 1 flow: harden the bundled `spm` design (RTL -> GDS, DRC, LVS).
# The design is copied out of the image; nothing is written under ~/OpenLane.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../env.sh"
W="$TRIAD_BUILD/smoke/openlane"
mkdir -p "$W" && cd "$W"
[ -d spm ] || docker run --rm "$OPENLANE_IMAGE" tar -C /openlane/designs -cf - spm </dev/null | tar -xf -
ol-flow -design "$W/spm" -tag smoke -overwrite
R="$W/spm/runs/smoke"
echo "== smoke summary =="
ls -la "$R/results/final/gds/" 2>/dev/null || echo "NO FINAL GDS"
python3 - "$R/reports/metrics.csv" <<'PY'
import csv, sys
row = next(csv.DictReader(open(sys.argv[1])))
for k in ("flow_status", "total_runtime", "DIEAREA_mm^2", "synth_cell_count", "tritonRoute_violations",
          "Magic_violations", "lvs_total_errors", "pin_antenna_violations", "wns", "spef_wns", "suggested_clock_period"):
    print(f"{k:28s} {row.get(k)}")
PY
