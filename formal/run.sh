#!/usr/bin/env bash
# Run the SymbiYosys checks: ecc.sby (prove) and steer.sby (BMC). Workdirs and logs go under
# build/formal/ so the repo directory stays clean. [files] paths in the .sby files resolve
# relative to this directory (formal/).
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
mkdir -p ../build/formal
fail=0
for f in ecc steer; do
    if sby -f -d "../build/formal/$f" "$f.sby" > "../build/formal/$f.log" 2>&1 \
        && grep -q "DONE (PASS" "../build/formal/$f.log"; then
        grep "DONE (PASS" "../build/formal/$f.log" | sed "s/^/$f.sby: /"
    else
        echo "$f.sby: FAIL"
        tail -25 "../build/formal/$f.log"
        fail=1
    fi
done
exit "$fail"
