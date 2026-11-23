#!/usr/bin/env bash
# Copy the reports of an OpenLane run that belong in the repository to build/export/asic/<tag>/
# and render the final layout to a PNG.   flow/openlane/export.sh <tag>
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
tag="$1"
run="$TRIAD_ROOT/flow/openlane/triad_bisr_top/runs/$tag"
out="$TRIAD_BUILD/export/asic/$tag"; mkdir -p "$out"
cp "$run/reports/metrics.csv" "$run/reports/manufacturability.rpt" "$out/"
for f in "$run"/reports/signoff/*rcx_sta.summary.rpt "$run"/reports/signoff/*rcx_sta.power.rpt \
         "$run"/reports/signoff/*.lvs.rpt "$run"/reports/signoff/*antenna_violators.rpt; do
  [ -f "$f" ] && cp "$f" "$out/$(basename "$f" | sed 's/^[0-9]*-//')"
done
head -c 200000 "$run/reports/signoff/drc.rpt" > "$out/drc.rpt"
cp "$TRIAD_ROOT/flow/openlane/triad_bisr_top/config.json" "$out/config.json"

# sta_checks_summary.csv: typical-corner check results for the site. Each report_check_types
# section (max slew/fanout/cap) lists violating pins sorted by slack; the first (VIOLATED) line
# carries the limit (field 2) and the worst metric (field 3).
checks="$run/reports/signoff/36-rcx_sta.checks.rpt"
echo "check,violations,limit,worst" > "$out/sta_checks_summary.csv"
awk '
    /^max slew$/    { sec="slew";   next }
    /^max fanout$/  { sec="fanout"; next }
    /^max cap$/     { sec="cap";    next }
    sec != "" && /\(VIOLATED\)/ {
        cnt[sec]++
        if (!(sec in seen)) { seen[sec]=1; lim[sec]=$2; worst[sec]=$3 }
    }
    END {
        printf "max_slew,%d,%s,%s\n",   cnt["slew"],   lim["slew"],   worst["slew"]
        printf "max_fanout,%d,%s,%s\n", cnt["fanout"], lim["fanout"], worst["fanout"]
        printf "max_cap,%d,%s,%s\n",    cnt["cap"],    lim["cap"],    worst["cap"]
    }' "$checks" >> "$out/sta_checks_summary.csv"

# timing_corners.csv: worst setup/hold slack per RC corner from the multi-corner STA summaries
# (setup = "worst slack" after report_worst_slack -max, hold after -min).
echo "corner,setup_slack_ns,hold_slack_ns" > "$out/timing_corners.csv"
for c in min nom max; do
    f="$run/reports/signoff/"*"-mca/rcx_${c}_sta.summary.rpt"
    awk -v c="$c" '
        /report_worst_slack -max/ { mode="s" }
        /report_worst_slack -min/ { mode="h" }
        /^worst slack /           { if (mode=="s") s=$3; else if (mode=="h") h=$3 }
        END { printf "%s,%s,%s\n", c, s, h }' $f >> "$out/timing_corners.csv"
done
gds="$run/results/final/gds/triad_bisr_top.gds"
if [ -f "$gds" ]; then
  sha256sum "$gds" | sed "s|$run/||" > "$out/gds.sha256"
  cat > "$TRIAD_BUILD/tmp/shot.py" <<'PY'
import pya, os
view = pya.LayoutView()
view.load_layout(os.environ["GDS"], True)
view.max_hier()
view.set_config("background-color", "#ffffff")
view.save_image(os.environ["PNG"], 1800, 1000)
PY
  GDS="$gds" PNG="$out/layout.png" QT_QPA_PLATFORM=offscreen klayout -zz -r "$TRIAD_BUILD/tmp/shot.py" </dev/null >/dev/null 2>&1 \
    || echo "layout image not rendered"
fi
ls -la "$out" | awk 'NR>3{print $5, $9}'
