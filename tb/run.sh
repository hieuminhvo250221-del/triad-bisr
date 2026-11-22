#!/usr/bin/env bash
# Run one cocotb test module and fail if any test failed.
#   tb/run.sh <toplevel> <python module> <verilog sources relative to tb/ ...>
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
top="$1"; mod="$2"; shift 2
out="../build/sim/$top"
rm -rf "$out"; mkdir -p "$out"
make TOPLEVEL="$top" MODULE="$mod" SRC="$*" > "$out.log" 2>&1 </dev/null || { tail -30 "$out.log"; exit 1; }
grep -E 'TESTS=|PASS|FAIL' "$out.log" | grep -v -E '^\s*$' | tail -12
[ -f "$out/results.xml" ] && ! grep -q -E '<(failure|error)' "$out/results.xml"
