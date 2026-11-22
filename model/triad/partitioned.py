"""Address-partitioned bit steering: exact allocation.

The N words are split into P equal partitions by their upper address bits.  A spare column may
replace a different bit position in every partition, so each partition chooses its own set of at
most S columns.  Spare words (R) and the ECC budget (K) are shared by all partitions.

Because column choices of different partitions do not interact, the problem decomposes: for every
partition and every allowance (r spare words, c columns) the single-partition solver gives the
minimum number of ECC-consumed words; a dynamic programme over the partitions then distributes the
shared spare words and the shared budget.  P = 1 is the plain problem of `solver.solve`.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from typing import Optional

from .core import FaultMap, Policy, Resources, col_mask
from .solver import solve

UNLIMITED = 1 << 30


@dataclass(frozen=True)
class PartSolution:
    rows: frozenset[int]
    cols: tuple[frozenset[int], ...]  # one column set per partition
    ecc_words: int

    @property
    def spares(self) -> int:
        return len(self.rows) + sum(len(c) for c in self.cols)

    def objective(self, policy: Policy) -> tuple[int, int]:
        if policy is Policy.RELIABILITY_FIRST:
            return (self.ecc_words, self.spares)
        return (self.spares, self.ecc_words)


def split(faults: FaultMap, n_words: int, parts: int) -> list[dict[int, int]]:
    size = n_words // parts
    subs: list[dict[int, int]] = [{} for _ in range(parts)]
    for w, m in faults.items():
        if m:
            subs[w // size][w] = m
    return subs


def evaluate_part(faults: FaultMap, n_words: int, parts: int, rows, cols) -> Optional[int]:
    """ECC-consumed words left by (rows, per-partition cols); None if a word keeps >= 2 faults."""
    size = n_words // parts
    keep = [~col_mask(c) for c in cols]
    rows = set(rows)
    ecc = 0
    for w, m in faults.items():
        if w in rows:
            continue
        m &= keep[w // size]
        if m & (m - 1):
            return None
        ecc += m != 0
    return ecc


def is_valid_part(faults: FaultMap, n_words: int, parts: int, res: Resources, sol: PartSolution) -> bool:
    if len(sol.rows) > res.rows or len(sol.cols) != parts or any(len(c) > res.cols for c in sol.cols):
        return False
    ecc = evaluate_part(faults, n_words, parts, sol.rows, sol.cols)
    return ecc is not None and ecc == sol.ecc_words and ecc <= res.ecc_budget


def solve_partitioned(faults: FaultMap, res: Resources, n_words: int, parts: int,
                      policy: Policy = Policy.RELIABILITY_FIRST) -> Optional[PartSolution]:
    # table[(spare words used, ECC words)] = (column segments used, per-partition solutions)
    table: dict[tuple[int, int], tuple[int, list]] = {(0, 0): (0, [])}
    for sub in split(faults, n_words, parts):
        options = {}
        for r in range(res.rows + 1):
            for c in range(res.cols + 1):
                sol = solve(sub, Resources(r, c, UNLIMITED), Policy.RELIABILITY_FIRST)
                if sol is not None and sol.ecc_words <= res.ecc_budget:
                    options[(len(sol.rows), len(sol.cols), sol.ecc_words)] = sol
        new: dict[tuple[int, int], tuple[int, list]] = {}
        for (r0, e0), (c0, chosen) in table.items():
            for (r1, c1, e1), sol in options.items():
                key = (r0 + r1, e0 + e1)
                if key[0] > res.rows or key[1] > res.ecc_budget:
                    continue
                if key not in new or c0 + c1 < new[key][0]:
                    new[key] = (c0 + c1, chosen + [sol])
        table = new
        if not table:
            return None

    def rank(item):
        (r, e), (c, _) = item
        return (e, r + c) if policy is Policy.RELIABILITY_FIRST else (r + c, e)

    (_, ecc), (_, chosen) = min(table.items(), key=rank)
    rows = frozenset(w for sol in chosen for w in sol.rows)
    return PartSolution(rows, tuple(sol.cols for sol in chosen), ecc)


def brute_force_part(faults: FaultMap, res: Resources, n_words: int, parts: int,
                     policy: Policy) -> Optional[PartSolution]:
    """Exhaustive reference for tiny instances."""
    subs = split(faults, n_words, parts)
    words = sorted(w for sub in subs for w in sub)
    col_choices = []
    for sub in subs:
        union = 0
        for m in sub.values():
            union |= m
        columns = [c for c in range(union.bit_length()) if union >> c & 1]
        col_choices.append([frozenset(ys) for n in range(min(res.cols, len(columns)) + 1)
                            for ys in combinations(columns, n)])
    best: Optional[PartSolution] = None
    for nr in range(min(res.rows, len(words)) + 1):
        for xs in combinations(words, nr):
            for cols in product(*col_choices):
                ecc = evaluate_part(faults, n_words, parts, xs, cols)
                if ecc is None or ecc > res.ecc_budget:
                    continue
                cand = PartSolution(frozenset(xs), tuple(cols), ecc)
                if best is None or cand.objective(policy) < best.objective(policy):
                    best = cand
    return best
