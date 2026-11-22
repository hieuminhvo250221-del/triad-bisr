"""Exact allocation by enumerating column sets (polynomial for a fixed number S of spare columns).

For a fixed set Y of replaced columns the best choice of spare words is forced: every word that
still has two or more faults must be replaced; the remaining spare words can only be spent on
words with exactly one fault, one word each.  Trying all O(W^S) column sets is therefore exact.
This is the second golden model (and a candidate for a search-free hardware allocator).
"""
from __future__ import annotations

from itertools import combinations
from typing import Optional

from .core import FaultMap, Policy, Resources, Solution, col_mask


def solve_by_columns(faults: FaultMap, res: Resources, policy: Policy = Policy.RELIABILITY_FIRST) -> Optional[Solution]:
    union = 0
    for m in faults.values():
        union |= m
    columns = [c for c in range(union.bit_length()) if union >> c & 1]
    best: Optional[Solution] = None
    for n in range(min(res.cols, len(columns)) + 1):
        for ys in combinations(columns, n):
            keep = ~col_mask(ys)
            multi, single = [], []
            for w in sorted(faults):
                m = faults[w] & keep
                if m & (m - 1):
                    multi.append(w)
                elif m:
                    single.append(w)
            spare = res.rows - len(multi)
            if spare < 0:
                continue
            if policy is Policy.RELIABILITY_FIRST:
                bought = min(len(single), spare)
            else:
                bought = max(0, len(single) - res.ecc_budget)
                if bought > spare:
                    continue
            ecc = len(single) - bought
            if ecc > res.ecc_budget:
                continue
            cand = Solution(frozenset(multi + single[:bought]), frozenset(ys), ecc)
            if best is None or cand.objective(policy) < best.objective(policy):
                best = cand
    return best
