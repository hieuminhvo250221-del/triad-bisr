"""Exploration: address-partitioned bit steering.

A spare column normally replaces the same bit position in every word.  If the steering select is
looked up per address partition (P partitions, upper address bits), each partition can replace up
to S bit positions of its own.  Spare words (R) and the ECC budget (K) stay global.

Exact evaluation: for every partition and every number r of spare words given to it, the TRIAD
solver returns the minimum number of ECC-consumed words with S columns; a small dynamic programme
then distributes the R spare words over the partitions.  P = 1 is the plain scheme.

    PYTHONPATH=model python model/analysis/partitioned_steering.py --out build/export/explore
"""
from __future__ import annotations

import argparse
import csv
import os
import random
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from triad.core import Policy, Resources
from triad.defects import MIXES, Geometry, sample
from triad.solver import solve

GEOM = (256, 30, 2)
BIG = 10 ** 6


def min_ecc(faults: dict[int, int], parts: int, rows: int, cols: int) -> int:
    """Minimum number of ECC-consumed words with P partitions (BIG if conflicts cannot be removed)."""
    size = GEOM[0] // parts
    by_part: dict[int, dict[int, int]] = {}
    for w, m in faults.items():
        by_part.setdefault(w // size, {})[w] = m
    best = [0] + [BIG] * rows  # best[r] = min ECC words using exactly r spare words so far
    for sub in by_part.values():
        cost = []
        for r in range(rows + 1):
            sol = solve(sub, Resources(r, cols, BIG), Policy.RELIABILITY_FIRST)
            cost.append(BIG if sol is None else sol.ecc_words)
        best = [min(best[r - q] + cost[q] for q in range(r + 1)) for r in range(rows + 1)]
    return min(min(best), BIG)


def run(task: tuple) -> list[dict]:
    mix, n, trials, seed, settings, budgets = task
    geom = Geometry(*GEOM)
    rng = random.Random(f"{seed}/{mix}/{n}")
    acc = {(s, k): [0, 0] for s in settings for k in budgets}
    for _ in range(trials):
        faults = sample(rng, geom, n, MIXES[mix])
        for s in settings:
            e = min_ecc(faults, *s)
            for k in budgets:
                if e <= k:
                    acc[(s, k)][0] += 1
                    acc[(s, k)][1] += e
    return [dict(mix=mix, defects=n, trials=trials, P=s[0], R=s[1], S=s[2], K=k, repaired=a[0], sum_ecc=a[1])
            for (s, k), a in acc.items()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=2000)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    settings = [(p, r, s) for r, s in ((2, 2), (2, 1)) for p in (1, 4, 16, 64)]
    budgets = [0, 2, 4, 8]
    tasks = [(mix, n, args.trials, 7, settings, budgets) for mix in ("cells", "mixed") for n in range(1, 41)]
    args.out.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    with ProcessPoolExecutor(os.cpu_count()) as pool:
        for part in pool.map(run, sorted(tasks, key=lambda t: -t[1])):
            rows += part
    with open(args.out / "partitioned_steering.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    # defects tolerated at 90 % repair rate (linear interpolation), per setting
    print(f"{'mix':6s} {'R':>2s} {'S':>2s} {'K':>2s} " + " ".join(f"P={p:<3d}" for p in (1, 4, 16, 64)) + "   (defects per memory at 90 % repair rate)")
    for mix in ("cells", "mixed"):
        for r, s in ((2, 2), (2, 1)):
            for k in budgets:
                cells = []
                for p in (1, 4, 16, 64):
                    pts = sorted((x["defects"], x["repaired"] / x["trials"]) for x in rows
                                 if (x["mix"], x["P"], x["R"], x["S"], x["K"]) == (mix, p, r, s, k))
                    n90 = 0.0
                    for (n0, y0), (n1, y1) in zip([(0, 1.0)] + pts, pts):
                        if y1 < 0.9 <= y0:
                            n90 = n0 + (y0 - 0.9) / (y0 - y1) * (n1 - n0)
                            break
                    else:
                        n90 = float("inf")
                    cells.append(f"{n90:5.1f}")
                print(f"{mix:6s} {r:2d} {s:2d} {k:2d} " + " ".join(cells))


if __name__ == "__main__":
    main()
