#!/usr/bin/env bash
# Full simulation regression (run inside WSL from the mirror, after `source tools/env.sh`).
#   bash tb/regress.sh [maps per configuration]
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
RTL="../rtl/ecc30_24.v ../rtl/triad_datapath.v ../rtl/mbist_march.v ../rtl/alloc_enum.v ../rtl/alloc_dp.v ../rtl/bisr_ctrl.v ../rtl/triad_bisr_top.v"
maps="${1:-24}"
rc=0
echo "== datapath unit tests =="
bash tb/run.sh dp_tb_top test_datapath ../rtl/ecc30_24.v ../rtl/triad_datapath.v dp_tb_top.v | tail -1 || rc=1
for cfg in "4 2 7" "2 1 11" "3 4 13"; do
  set -- $cfg
  echo "== system tests: PBITS=$1 R=$2 seed=$3, $maps random maps =="
  TB_PBITS=$1 TB_R=$2 TB_SEED=$3 TB_MAPS=$maps EXTRA_COMPILE_ARGS="-Ptop_tb.PBITS=$1 -Ptop_tb.R=$2" \
    bash tb/run.sh top_tb test_top $RTL top_tb.v | tail -1 || rc=1
  grep -h "random maps:" build/sim/top_tb.log | sed 's/.*random maps:/   random maps:/' || true
done
exit $rc
