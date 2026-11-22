"""Exploration: is a partition table worth more than the same flip-flops spent on spare words?

Area proxy (flip-flops only, no muxes/comparators): spare word = 39 FF (30 data + 8 address +
valid); partition table = P * S * 6 FF (5-bit select + valid per partition and spare column).

    PYTHONPATH=model:model/analysis python model/analysis/equal_area.py [trials]
"""
from __future__ import annotations

import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor

from partitioned_steering import GEOM, min_ecc
from triad.defects import MIXES, Geometry, sample

# kang_dl: low-density mix used by the Yonsei (Kang) group: 80.4 % single cell, 9.7 % row, 9.7 % column
MIX = dict(MIXES, kang_dl={"cell": 0.804, "row": 0.098, "col": 0.098})
SETTINGS = [(1, 2, 2), (1, 7, 2), (4, 6, 2), (8, 4, 2), (16, 2, 2), (16, 4, 2), (1, 9, 2)]  # (P, R, S)
BUDGETS = (0, 2, 8)


def run(task: tuple) -> tuple:
    mix, n, trials = task
    rng = random.Random(f"eq/{mix}/{n}")
    geom = Geometry(*GEOM)
    acc = {(s, k): 0 for s in SETTINGS for k in BUDGETS}
    for _ in range(trials):
        f = sample(rng, geom, n, MIX[mix])
        for s in SETTINGS:
            e = min_ecc(f, *s)
            for k in BUDGETS:
                acc[(s, k)] += e <= k
    return mix, n, {key: v / trials for key, v in acc.items()}


def main() -> None:
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    tasks = [(m, n, trials) for m in ("cells", "mixed", "kang_dl") for n in range(1, 41)]
    with ProcessPoolExecutor(os.cpu_count()) as pool:
        out = list(pool.map(run, tasks))

    def n90(mix: str, key: tuple) -> float:
        pts = [(0, 1.0)] + sorted((n, r[key]) for m, n, r in out if m == mix)
        for (n0, y0), (n1, y1) in zip(pts, pts[1:]):
            if y1 < 0.9 <= y0:
                return n0 + (y0 - 0.9) / (y0 - y1) * (n1 - n0)
        return float("inf")

    print("defects per memory tolerated at 90 % repair rate (256x30, S=2 spare columns)")
    print(f"{'setting':22s} {'FFs':>4s} | " + " | ".join(f"{m:>7s} K={k}" for m in ("cells", "mixed", "kang_dl") for k in BUDGETS))
    for p, r, s in SETTINGS:
        ffs = 39 * r + (p * s * 6 if p > 1 else 0)
        print(f"P={p:<2d} R={r} spare words   {ffs:4d} | "
              + " | ".join(f"{n90(m, ((p, r, s), k)):11.1f}" for m in ("cells", "mixed", "kang_dl") for k in BUDGETS))


if __name__ == "__main__":
    main()
