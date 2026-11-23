"""Monte Carlo comparison of allocators on random physical defect maps.

    PYTHONPATH=model python -m triad.mc --preset macro --trials 5000 --out build/g2/macro.csv

For every (geometry, defect mix, number of defects) the same fault maps are given to every
allocator and every resource setting (common random numbers), so differences between allocators
are not sampling noise.
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .baselines import ALGORITHMS
from .core import Policy, Resources
from .defects import MIXES, Geometry, sample
from .partitioned import solve_partitioned
from .solver import solve

PRESETS = {
    # the project memory: sky130 OpenRAM 32x256 macro, 30 code bits (24 data + 6 check), mux 2
    "macro": dict(geom=(256, 30, 2), defects=range(1, 25), rs=[(2, 2), (4, 2), (2, 1)], ks=[0, 2, 4, 8, 16, 256]),
    # a larger embedded SRAM: 4096 x 39 (32 data + 7 check), mux 8
    "large": dict(geom=(4096, 39, 8), defects=range(2, 41, 2), rs=[(8, 2), (8, 4)], ks=[0, 8, 32, 4096]),
    # evaluation protocol for the paper: project memory, plain and address-partitioned steering
    "protocol": dict(geom=(256, 30, 2), defects=range(1, 31), rs=[(2, 2), (4, 2)], ks=[0, 2, 8], parts=(4, 16)),
    # the same protocol on the larger memory
    "protocol_large": dict(geom=(4096, 39, 8), defects=range(2, 61, 2), rs=[(8, 2), (8, 4)], ks=[0, 8, 32],
                           parts=(16, 64)),
}
FIELDS = ["words", "bits", "wpr", "mix", "defects", "trials", "R", "S", "K", "algo", "repaired", "sum_ecc",
          "sum_spares", "sum_ecc_triad", "sum_spares_triad", "max_nodes", "sum_nodes", "max_kernel_words"]


def run_task(task: tuple) -> list[dict]:
    geom_t, mix_name, n_defects, trials, seed, settings, part_list = task
    geom = Geometry(*geom_t)
    rng = random.Random(f"{seed}/{geom_t}/{mix_name}/{n_defects}")
    acc: dict[tuple[Resources, str], list[int]] = {}
    search: dict[Resources, list[int]] = {}
    for _ in range(trials):
        faults = sample(rng, geom, n_defects, MIXES[mix_name])
        two_d: dict[tuple[str, int, int], object] = {}
        for res in settings:
            st: dict = {}
            triad = solve(faults, res, Policy.RELIABILITY_FIRST, st)
            s = search.setdefault(res, [0, 0, 0])
            s[0] = max(s[0], st["nodes"])
            s[1] += st["nodes"]
            s[2] = max(s[2], st["kernel_words"])
            for name, algo in ALGORITHMS.items():
                if name == "triad_rel":
                    sol = triad
                elif name.endswith("_2d"):  # independent of the ECC budget
                    key = (name, res.rows, res.cols)
                    if key not in two_d:
                        two_d[key] = algo(faults, res)
                    sol = two_d[key]
                else:
                    sol = algo(faults, res)
                a = acc.setdefault((res, name), [0, 0, 0, 0, 0])
                if sol is not None:
                    assert triad is not None, "TRIAD must repair whatever a baseline repairs"
                    a[0] += 1
                    a[1] += sol.ecc_words
                    a[2] += sol.spares
                    a[3] += triad.ecc_words
                    a[4] += triad.spares
            for parts in part_list:  # address-partitioned steering (dominates the plain scheme)
                psol = solve_partitioned(faults, res, geom.words, parts)
                a = acc.setdefault((res, f"triad_p{parts}"), [0, 0, 0, 0, 0])
                if psol is not None:
                    a[0] += 1
                    a[1] += psol.ecc_words
                    a[2] += psol.spares
    rows = []
    for (res, name), a in acc.items():
        s = search[res]
        rows.append(dict(zip(FIELDS, [*geom_t, mix_name, n_defects, trials, res.rows, res.cols, res.ecc_budget,
                                      name, *a, *s])))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", choices=PRESETS, required=True)
    ap.add_argument("--mixes", nargs="+", default=list(MIXES), choices=list(MIXES))
    ap.add_argument("--trials", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20261122)
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    p = PRESETS[args.preset]
    settings = [Resources(r, s, k) for r, s in p["rs"] for k in p["ks"]]
    tasks = [(p["geom"], mix, n, args.trials, args.seed, settings, tuple(p.get("parts", ())))
             for mix in args.mixes for n in p["defects"]]
    tasks.sort(key=lambda t: -t[2])  # longest first
    t0 = time.time()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(args.jobs) as pool, open(args.out, "w", newline="") as fh:
        writer = csv.DictWriter(fh, FIELDS)
        writer.writeheader()
        for i, rows in enumerate(pool.map(run_task, tasks), 1):
            writer.writerows(rows)
            fh.flush()
            print(f"[{i}/{len(tasks)}] {time.time() - t0:.0f}s", flush=True)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
