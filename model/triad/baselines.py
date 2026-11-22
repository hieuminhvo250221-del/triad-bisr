"""Baseline allocators used for comparison with TRIAD.

* `esp`        - Essential Spare Pivoting (2-D redundancy, no ECC), as commonly described after
                 Huang et al., IEEE Trans. Reliability 2003.  To be re-checked against the paper.
* `ecc_first`  - "ECC first, spares for the rest" (the EBISR idea, Lu et al., TVLSI 2016): words
                 with a single faulty bit are left to ECC; every fault of a multi-fault word must be
                 covered by a spare.  `ra` selects the 2-D analyser for those words ("esp" as in
                 EBISR, or "exact" = the best any ECC-first scheme can do).  `buyback=True` adds a
                 greedy pass that spends left-over spares on single-fault words: the strongest
                 simple heuristic we compare against.
* `greedy_joint` - a one-pass heuristic for the joint problem: must-repair, then repeatedly replace
                 the line holding most faults of the words that still have two or more faults
                 (repair-most without backtracking), then the same buy-back.  The gap between it
                 and TRIAD is what the exact search itself is worth.
"""
from __future__ import annotations

from typing import Callable, Optional

from .core import FaultMap, Policy, Resources, Solution, col_mask
from .solver import complete, kernelize, solve


def esp(faults: FaultMap, rows: int, cols: int) -> Optional[Solution]:
    pivots: list[list] = []  # [word, column, row_essential, col_essential]
    for w in sorted(faults):
        m = faults[w]
        while m:
            low = m & -m
            c = low.bit_length() - 1
            m ^= low
            hit = next((p for p in pivots if p[0] == w), None)
            if hit is not None:
                hit[2] = True
                continue
            hit = next((p for p in pivots if p[1] == c), None)
            if hit is not None:
                hit[3] = True
                continue
            if len(pivots) == rows + cols:
                return None
            pivots.append([w, c, False, False])
    xs = {p[0] for p in pivots if p[2]}
    ys = {p[1] for p in pivots if p[3]}
    if len(xs) > rows or len(ys) > cols:
        return None
    for p in pivots:
        if p[2] or p[3]:
            continue
        if len(xs) < rows:
            xs.add(p[0])
        elif len(ys) < cols:
            ys.add(p[1])
        else:
            return None
    return Solution(frozenset(xs), frozenset(ys), 0)


def ecc_first(faults: FaultMap, res: Resources, ra: str = "exact", buyback: bool = False) -> Optional[Solution]:
    singles = {w: m for w, m in faults.items() if m and not m & (m - 1)}
    multi = {w: m for w, m in faults.items() if m & (m - 1)}
    if ra == "esp":
        sol = esp(multi, res.rows, res.cols)
    else:
        sol = solve(multi, Resources(res.rows, res.cols, 0), Policy.SPARE_SAVING)
    if sol is None:
        return None
    rows, ymask = sol.rows, col_mask(sol.cols)
    if buyback:
        done = complete(singles, rows, ymask, res.rows - len(rows), res.cols - len(sol.cols),
                        res.ecc_budget, Policy.RELIABILITY_FIRST)
        if done is None:
            return None
        rows, ymask, ecc = done
    else:
        ecc = sum(1 for m in singles.values() if m & ~ymask)
        if ecc > res.ecc_budget:
            return None
    return Solution(frozenset(rows), frozenset(c for c in range(ymask.bit_length()) if ymask >> c & 1), ecc)


def greedy_joint(faults: FaultMap, res: Resources) -> Optional[Solution]:
    kernel = kernelize(faults, res)
    if kernel is None:
        return None
    kf = kernel.faults
    rows: set[int] = set()
    ymask = 0
    rows_left, cols_left = kernel.rows_left, kernel.cols_left
    while True:
        per_col: dict[int, int] = {}
        worst_word, worst_n = -1, 0
        for w in sorted(kf):
            if w in rows:
                continue
            m = kf[w] & ~ymask
            if not m & (m - 1):
                continue
            if m.bit_count() > worst_n:
                worst_word, worst_n = w, m.bit_count()
            while m:
                low = m & -m
                per_col[low] = per_col.get(low, 0) + 1
                m ^= low
        if worst_n == 0:
            break
        col_bit, col_n = max(per_col.items(), key=lambda kv: (kv[1], -kv[0]))
        if cols_left and (rows_left == 0 or col_n >= worst_n):
            ymask |= col_bit
            cols_left -= 1
        elif rows_left:
            rows.add(worst_word)
            rows_left -= 1
        else:
            return None
    done = complete(kf, frozenset(rows), ymask, rows_left, cols_left, res.ecc_budget, Policy.RELIABILITY_FIRST)
    if done is None:
        return None
    new_rows, new_mask, ecc = done
    cols = frozenset(c for c in range(new_mask.bit_length()) if new_mask >> c & 1)
    return Solution(kernel.must_rows | new_rows, kernel.must_cols | cols, ecc)


Allocator = Callable[[FaultMap, Resources], Optional[Solution]]

ALGORITHMS: dict[str, Allocator] = {
    "triad_rel": lambda f, r: solve(f, r, Policy.RELIABILITY_FIRST),
    "triad_spare": lambda f, r: solve(f, r, Policy.SPARE_SAVING),
    "greedy_joint": greedy_joint,
    "ef_exact_bb": lambda f, r: ecc_first(f, r, "exact", True),
    "ef_exact": lambda f, r: ecc_first(f, r, "exact", False),
    "ef_esp": lambda f, r: ecc_first(f, r, "esp", False),
    "exact_2d": lambda f, r: solve(f, Resources(r.rows, r.cols, 0), Policy.SPARE_SAVING),
    "esp_2d": lambda f, r: esp(f, r.rows, r.cols),
}
