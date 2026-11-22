#!/usr/bin/env bash
# RTL-to-GDS with OpenLane 1 (inside WSL, from the mirror):  flow/openlane/run.sh <tag>
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
tag="${1:-run1}"
design="$TRIAD_ROOT/flow/openlane/triad_bisr_top"
ol-flow -design "$design" -tag "$tag" -overwrite > "$TRIAD_BUILD/openlane_$tag.log" 2>&1 || true
grep -E '^\[(ERROR|SUCCESS)\]|Flow complete|violations|\[STEP' "$TRIAD_BUILD/openlane_$tag.log" | tail -12
run="$design/runs/$tag"
[ -f "$run/reports/metrics.csv" ] && python3 - "$run/reports/metrics.csv" <<'PY'
import csv, sys
row = next(csv.DictReader(open(sys.argv[1])))
for k in ("flow_status", "total_runtime", "DIEAREA_mm^2", "CoreArea_um^2", "synth_cell_count", "tritonRoute_violations",
          "Magic_violations", "lvs_total_errors", "pin_antenna_violations", "wns", "spef_wns", "spef_tns", "suggested_clock_period",
          "suggested_clock_frequency", "wire_length", "vias", "power_slowest_internal_uW", "power_typical_internal_uW"):
    print(f"{k:28s} {row.get(k)}")
PY
