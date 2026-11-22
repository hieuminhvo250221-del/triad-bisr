"""Exploration: does the open sky130 PDK support mismatch Monte Carlo of the OpenRAM bitcell?

Builds two ngspice decks per supply voltage with 200 instances of sky130_fd_bd_sram__openram_dp_cell
(extracted from the macro netlist) in the `tt_mm` corner (local mismatch on, 25 C):
  read  - cell holds 0, word line pulsed 5 ns with both bit lines held at VDD (worst-case disturb);
  write - cell holds 1, a 0 is written through port 0 with ideal bit-line drivers, 5 ns pulse.
It is a feasibility probe, not a characterisation: ideal drivers, no periphery, one temperature.

    source tools/env.sh && python model/analysis/bitcell_probe.py build/explore/spice
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

PDK = Path(os.environ["PDK_ROOT"]) / os.environ["PDK"]
LIB = PDK / "libs.tech/ngspice/sky130.lib.spice"
MACRO = Path(os.environ["SRAM_MACRO_DIR"]) / "spice/sky130_sram_1kbyte_1rw1r_32x256_8.spice"
CELL = "sky130_fd_bd_sram__openram_dp_cell"
N = 200


def deck(kind: str, vdd: float) -> str:
    q0, qb0, bl = (0, vdd, "{vdd}") if kind == "read" else (vdd, 0, "0")
    lines = [f"* {kind} probe", f'.lib "{LIB}" tt_mm', ".include bitcell.spice", ".option seed=7",
             f".param vdd={vdd}", ".temp 25", "Vdd vdd 0 {vdd}",
             "Vwl wl0 0 pwl(0 0 1n 0 1.2n {vdd} 6n {vdd} 6.2n 0)", "Vwl1 wl1 0 0",
             f"Vbl bl0 0 {bl}", "Vbr br0 0 {vdd}", "Vbl1 bl1 0 {vdd}", "Vbr1 br1 0 {vdd}"]
    lines += [f"Xc{i} bl0 br0 bl1 br1 wl0 wl1 vdd 0 {CELL}" for i in range(N)]
    lines += [".ic " + " ".join(f"v(xc{i}.q)={q0} v(xc{i}.q_bar)={qb0}" for i in range(N)), ".tran 0.02n 10n uic"]
    lines += [f".meas tran q{i} find v(xc{i}.q) at=9.5n" for i in range(N)]
    return "\n".join(lines + [".end"]) + "\n"


def main() -> None:
    work = Path(sys.argv[1])
    work.mkdir(parents=True, exist_ok=True)
    text = MACRO.read_text()
    start = text.index(f".SUBCKT {CELL} BL0")
    (work / "bitcell.spice").write_text(text[start:text.index(".ENDS", start) + 6])
    for kind in ("read", "write"):
        for vdd in (1.8, 1.2, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5):
            name = f"{kind}_{vdd}"
            (work / f"{name}.spice").write_text(deck(kind, vdd))
            log = subprocess.run(["ngspice", "-b", f"{name}.spice"], cwd=work, capture_output=True, text=True,
                                 stdin=subprocess.DEVNULL).stdout
            q = [float(x) for x in re.findall(r"^q\d+\s*=\s*([-+0-9.eE]+)", log, re.M)]
            wrong = sum(x > vdd / 2 for x in q)  # read: flipped to 1; write: still 1
            print(f"{kind:5s} VDD={vdd:<4} cells={len(q)} failures={wrong}")


if __name__ == "__main__":
    main()
