#!/usr/bin/env bash
# Are the system tests able to see bugs?  Each mutant of the RTL must make the directed test fail.
# Run inside WSL from the mirror:  bash tb/mutation_check.sh
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
RTL="../rtl/ecc30_24.v ../rtl/triad_datapath.v ../rtl/mbist_march.v ../rtl/alloc_enum.v ../rtl/alloc_dp.v ../rtl/bisr_ctrl.v ../rtl/triad_bisr_top.v"
keep=build/tmp/rtl_orig; rm -rf "$keep"; mkdir -p build/tmp; cp -r rtl "$keep"
missed=0
mutate() {  # <name> <file> <sed expression> [testcase]
  if [ -n "${ONLY:-}" ] && [[ "$1" != *"$ONLY"* ]]; then return; fi
  cp "$keep"/*.v rtl/
  sed -i "$3" "rtl/$2"
  if cmp -s "rtl/$2" "$keep/$2"; then echo "NOT APPLIED  $1"; missed=$((missed + 1)); return; fi
  if TESTCASE="${4:-directed_cases}" bash tb/run.sh top_tb test_top $RTL top_tb.v >/dev/null 2>&1; then
    echo "MISSED       $1"; missed=$((missed + 1))
  else
    echo "detected     $1"
  fi
}
mutate "read path takes the wrong spare column"    triad_datapath.v 's/r_code\[r_s0\[4:0\]\] = m_dout\[30\];/r_code[r_s0[4:0]] = m_dout[31];/'
mutate "write path does not drive spare column 1"  triad_datapath.v 's/wire \[31:0\] w_rep = {w_s1\[5\] \& w_pad\[w_s1\[4:0\]\],/wire [31:0] w_rep = {1'"'"'b0,/'
mutate "spare word is not written"                 triad_datapath.v 's/sw_data\[30\*k +: 30\] <= w_code;/sw_data[30*k +: 30] <= sw_data[30*k +: 30];/'
mutate "enumeration ignores a faulty spare column" alloc_enum.v     's/if (o0\[5\]) v\[o0\[4:0\]\] = row\[30\];/if (o0[5]) v[o0[4:0]] = 1'"'"'b0;/'
mutate "enumeration never tries spare column 1"    alloc_enum.v     's/if (i1 != 5'"'"'d30) i1 <= i1 + 5'"'"'d1;/if (1'"'"'b0) i1 <= i1 + 5'"'"'d1;/'
mutate "dynamic programme ignores the window cost" alloc_dp.v       's/+ {1'"'"'b0, e_flat\[6\*q +: 6\]};/+ 7'"'"'d0;/'
mutate "budget comparison off by one"              bisr_ctrl.v      's/else if (best_total > {1'"'"'b0, cfg_k}) begin/else if (best_total > {1'"'"'b0, cfg_k} + 6'"'"'d1) begin/'
mutate "spare words only for conflict words"       bisr_ctrl.v      's/| ((state == P2_SCAN_S) \& c_single \& (need != 7'"'"'d0));/;/'
mutate "March expects the wrong value in element 4" mbist_march.v   's/wire e_rval  = (elem == 3'"'"'d2) | (elem == 3'"'"'d4);/wire e_rval  = (elem == 3'"'"'d2);/'
mutate "bitmap overwrites instead of accumulating" alloc_enum.v     's/<= bm\[32\*f_idx +: 32\] | f_diff;/<= f_diff;/'
mutate "verification result ignored"               bisr_ctrl.v      's/pass <= ~m_fail;/pass <= 1'"'"'b1;/' verify_failure
mutate "signature chain shifts the wrong way"      triad_datapath.v 's/{sig_val\[L-2:0\], sig_in}/{sig_in, sig_val[L-2:0]}/' signature_roundtrip
mutate "cfg_clear does not clear sw_valid"         triad_datapath.v 's/; sw_valid <= {R{1'"'"'b0}};/; sw_valid <= sw_valid;/' restart_without_reset
cp "$keep"/*.v rtl/; rm -rf "$keep"
echo "mutants not detected: $missed"
exit "$missed"
