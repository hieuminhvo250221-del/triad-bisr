#!/usr/bin/env bash
# Smoke test of the native ORFS flow (OpenROAD 26Q2 + Yosys from OSS CAD Suite + KLayout): gcd on sky130hd.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../env.sh"
W="$TRIAD_BUILD/smoke/orfs"; mkdir -p "$W"
cd "$FLOW_HOME"
make DESIGN_CONFIG=designs/sky130hd/gcd/config.mk WORK_HOME="$W" "$@" </dev/null
echo "== smoke summary =="
ls -la "$W"/results/sky130hd/gcd/base/6_final.gds
python3 - "$W/logs/sky130hd/gcd/base/6_report.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for k in ("finish__design__instance__count", "finish__design__instance__area", "finish__timing__setup__ws",
          "finish__timing__hold__ws", "finish__power__total", "finish__timing__drv__setup_violation_count"):
    print(f"{k:45s} {d.get(k)}")
PY
grep -h -E "Total number of DRC|violation" "$W"/logs/sky130hd/gcd/base/5_2_route.log | tail -2
