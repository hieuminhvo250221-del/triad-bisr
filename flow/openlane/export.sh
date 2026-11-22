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
