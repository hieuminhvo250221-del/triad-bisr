"""autoMBIST's on-chip repair analyzers on the fault maps of the evaluation protocol.

    PYTHONPATH=model python model/analysis/automb_compare.py <autoMBIST checkout>/src build/export/automb [trials]

autoMBIST (github.com/ranaumarnadeem/autoMBIST, Apache-2.0, commit 032deb05) ships a decision-for-decision
Python model of its two on-chip 2-D analyzers (`autombist.yieldsim.onchip_model`: "greedy", one pass, and
"deferred", two passes) and an exact solver that runs on the tester (`autombist.repair.bira.analyze`).
Their code is imported from the checkout, not copied.  The fault maps are the ones `triad.mc` draws for
the same (seed, geometry, mix, defect count), so the TRIAD columns equal the protocol results.

Two readings of the same spare budget (R rows, S columns):
  word  - a spare row replaces one word, a spare column one bit lane (words_per_row = 1): the same
          resources as TRIAD without ECC;
  phys  - autoMBIST's native model of a column-muxed macro (words_per_row = 2): a spare row replaces a
          physical row (two words), a spare column one physical column (one bit of every second word).
Stuck values are drawn at random; they only set the order in which the march reports the faults.
"""
from __future__ import annotations

import csv
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from triad.core import Policy, Resources
from triad.defects import MIXES, Geometry, sample
from triad.partitioned import solve_partitioned
from triad.solver import solve

GEOM = (256, 30, 2)
R, S = 2, 2
SEED = 20261122          # the seed of triad.mc
MIX_NAMES = ("kang_dl", "kang_dh", "date06", "mixed")
DEFECTS = range(1, 21)
COLS = ["amb_greedy_word", "amb_deferred_word", "amb_exact_word", "amb_greedy_phys", "amb_deferred_phys",
        "amb_exact_phys", "exact_2d", "triad_k8", "triad_p16_k0", "triad_p16_k8"]


def run(task):
    amb_src, mix, n, trials = task
    sys.path.insert(0, amb_src)
    from autombist.repair.bira import analyze
    from autombist.repair.types import RepairSolution, SpareGeometry
    from autombist.yieldsim.onchip_model import deferred, greedy, march_c_events

    geom = Geometry(*GEOM)
    wpr = geom.wpr
    sg_word = SpareGeometry(geom.words, geom.bits, R, S, 1)
    sg_phys = SpareGeometry(geom.words, geom.bits, R, S, wpr)
    rng = random.Random(f"{SEED}/{GEOM}/{mix}/{n}")
    pol = random.Random(f"polarity/{SEED}/{mix}/{n}")
    acc = dict.fromkeys(COLS, 0)
    for _ in range(trials):
        faults = sample(rng, geom, n, MIXES[mix])
        cells = {(w, b) for w, m in faults.items() for b in range(geom.bits) if m >> b & 1}
        stuck = {c: pol.getrandbits(1) for c in sorted(cells)}
        events = march_c_events(stuck, geom.words)
        folded = [(a // wpr, sum(1 << (b * wpr + a % wpr) for b in range(geom.bits) if m >> b & 1)) for a, m in events]
        pcells = {(w // wpr, b * wpr + w % wpr) for w, b in cells}
        for name, fn in (("greedy", greedy), ("deferred", deferred)):
            rows, cols = fn(events, R, S)
            acc[f"amb_{name}_word"] += all(w in rows or b in cols for w, b in cells)
            rows, cols = fn(folded, R, S)
            acc[f"amb_{name}_phys"] += all(r in rows or c in cols for r, c in pcells)
        ours = solve(faults, Resources(R, S, 0), Policy.SPARE_SAVING) is not None
        theirs = isinstance(analyze(set(cells), sg_word), RepairSolution)
        assert ours == theirs, f"exact solvers disagree on {faults}"
        acc["exact_2d"] += ours
        acc["amb_exact_word"] += theirs
        acc["amb_exact_phys"] += isinstance(analyze(set(cells), sg_phys), RepairSolution)
        acc["triad_k8"] += solve(faults, Resources(R, S, 8), Policy.RELIABILITY_FIRST) is not None
        acc["triad_p16_k0"] += solve_partitioned(faults, Resources(R, S, 0), geom.words, 16) is not None
        acc["triad_p16_k8"] += solve_partitioned(faults, Resources(R, S, 8), geom.words, 16) is not None
    return dict(mix=mix, defects=n, trials=trials, R=R, S=S, **acc)


def main() -> None:
    amb_src, out = str(Path(sys.argv[1]).resolve()), Path(sys.argv[2])
    trials = int(sys.argv[3]) if len(sys.argv) > 3 else 10000
    jobs = int(sys.argv[4]) if len(sys.argv) > 4 else None
    out.mkdir(parents=True, exist_ok=True)
    tasks = [(amb_src, mix, n, trials) for mix in MIX_NAMES for n in DEFECTS]
    with ProcessPoolExecutor(jobs) as pool:
        rows = list(pool.map(run, tasks))
    with open(out / "automb_compare.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for mix in MIX_NAMES:
        print(f"-- {mix}: repair rate (%), R={R} S={S}, {trials} maps per point")
        print("   n  " + " ".join(f"{c[:14]:>14s}" for c in COLS))
        for r in rows:
            if r["mix"] == mix and r["defects"] in (2, 4, 6, 8, 12):
                print(f"  {r['defects']:2d}  " + " ".join(f"{100 * r[c] / trials:14.1f}" for c in COLS))


if __name__ == "__main__":
    main()
