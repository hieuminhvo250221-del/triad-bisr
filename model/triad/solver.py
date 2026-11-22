"""TRIAD exact solver: must-repair kernel, bounded 3-way search, greedy ECC buy-back.

This is the golden model of the hardware allocator.  Three facts make it exact:

1. Must-repair.  A column with more than R_left + K faulty words must be replaced (words can only
   escape it through a spare word or the ECC budget).  A word with more than S_left + [K > 0]
   faulty bits must be replaced (columns can remove S_left of them, ECC one more).
2. Branching.  If a word outside X keeps two faulty bits b1, b2 outside Y, every repair contains
   that word, column b1 or column b2 (ECC can absorb only one of the two).  The search depth is at
   most R + S, so at most 3^(R+S) branches.
3. Buy-back.  When no word keeps two faults, each remaining faulty word has exactly one fault, so
   the sets of words covered by different columns are disjoint and a spare word covers one word.
   Taking the largest gains first is therefore optimal, both for "cover as much as possible" and
   for "reach the budget with the fewest spares".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .core import FaultMap, Policy, Resources, Solution


@dataclass(frozen=True)
class Kernel:
    must_rows: frozenset[int]
    must_cols: frozenset[int]
    faults: dict[int, int]  # remaining fault map (must rows removed, must columns masked)
    rows_left: int
    cols_left: int


def cam_bound(rows: int, cols: int, ecc_budget: int) -> int:
    """Number of distinct faulty words a repairable kernel can contain: R + S(R+K) + K."""
    return rows + cols * (rows + ecc_budget) + ecc_budget


def kernelize(faults: FaultMap, res: Resources) -> Optional[Kernel]:
    """Must-repair fixed point.  None means provably unrepairable."""
    ecc_slack = 1 if res.ecc_budget > 0 else 0
    must_rows: set[int] = set()
    must_mask = 0
    live = {w: m for w, m in faults.items() if m}
    changed = True
    while changed:
        changed = False
        cols_left = res.cols - must_mask.bit_count()
        if cols_left < 0:
            return None
        for w in [w for w, m in live.items() if m.bit_count() > cols_left + ecc_slack]:
            must_rows.add(w)
            del live[w]
            changed = True
        rows_left = res.rows - len(must_rows)
        if rows_left < 0:
            return None
        count: dict[int, int] = {}
        for m in live.values():
            while m:
                low = m & -m
                count[low] = count.get(low, 0) + 1
                m ^= low
        new_mask = 0
        for bit, n in count.items():
            if n > rows_left + res.ecc_budget:
                new_mask |= bit
        if new_mask:
            must_mask |= new_mask
            live = {w: m & ~new_mask for w, m in live.items() if m & ~new_mask}
            changed = True
    rows_left = res.rows - len(must_rows)
    cols_left = res.cols - must_mask.bit_count()
    if rows_left < 0 or cols_left < 0:
        return None
    if len(live) > cam_bound(rows_left, cols_left, res.ecc_budget):
        return None  # more faulty words than any repair of the kernel can absorb
    must_cols = frozenset(c for c in range(must_mask.bit_length()) if must_mask >> c & 1)
    return Kernel(frozenset(must_rows), must_cols, live, rows_left, cols_left)


def complete(faults: FaultMap, rows: frozenset[int], ymask: int, rows_left: int, cols_left: int,
             budget: int, policy: Policy) -> Optional[tuple[frozenset[int], int, int]]:
    """Buy-back at a conflict-free node.

    Every faulty word outside `rows` has exactly one fault outside `ymask`.  Spend the remaining
    spares largest-gain-first (a column gains the number of such words in it, a spare word gains
    one) until the target is met.  Returns (rows, column mask, ecc_words), or None if the budget
    cannot be met.
    """
    by_col: dict[int, list[int]] = {}
    total = 0
    for w in sorted(faults):
        if w in rows:
            continue
        m = faults[w] & ~ymask
        if m:
            by_col.setdefault(m.bit_length() - 1, []).append(w)
            total += 1
    target = total if policy is Policy.RELIABILITY_FIRST else max(0, total - budget)
    col_order = sorted(by_col, key=lambda c: (-len(by_col[c]), c))[:cols_left]
    covered = 0
    add_cols: list[int] = []
    add_rows = 0
    i = 0
    while covered < target:
        gain = len(by_col[col_order[i]]) if i < len(col_order) else 0
        if gain > 1 or (gain == 1 and add_rows >= rows_left):
            add_cols.append(col_order[i])
            covered += gain
            i += 1
        elif add_rows < rows_left:
            add_rows += 1
            covered += 1
        else:
            break
    ecc = total - min(covered, total)
    if ecc > budget:
        return None
    chosen = set(add_cols)
    uncovered = sorted(w for c, ws in by_col.items() if c not in chosen for w in ws)
    new_mask = ymask
    for c in add_cols:
        new_mask |= 1 << c
    return rows | frozenset(uncovered[:add_rows]), new_mask, ecc


def solve(faults: FaultMap, res: Resources, policy: Policy = Policy.RELIABILITY_FIRST,
          stats: Optional[dict] = None) -> Optional[Solution]:
    """Optimal repair under `policy`, or None if the memory is unrepairable within the budget."""
    kernel = kernelize(faults, res)
    if stats is not None:
        stats.update(nodes=0, leaves=0, kernel_words=len(kernel.faults) if kernel else -1)
    if kernel is None:
        return None
    kf = kernel.faults
    words = sorted(kf)
    base_spares = len(kernel.must_rows) + len(kernel.must_cols)
    best: Optional[tuple[tuple[int, int], frozenset[int], int, int]] = None
    seen: set[tuple[frozenset[int], int]] = set()

    def visit(rows: frozenset[int], ymask: int, rows_left: int, cols_left: int) -> None:
        nonlocal best
        if (rows, ymask) in seen:
            return
        seen.add((rows, ymask))
        if stats is not None:
            stats["nodes"] += 1
        for w in words:
            if w in rows:
                continue
            m = kf[w] & ~ymask
            if m & (m - 1):  # conflict word: two or more faults left
                if rows_left:
                    visit(rows | {w}, ymask, rows_left - 1, cols_left)
                if cols_left:
                    b1 = m & -m
                    rest = m ^ b1
                    b2 = rest & -rest
                    visit(rows, ymask | b1, rows_left, cols_left - 1)
                    visit(rows, ymask | b2, rows_left, cols_left - 1)
                return
        if stats is not None:
            stats["leaves"] += 1
        done = complete(kf, rows, ymask, rows_left, cols_left, res.ecc_budget, policy)
        if done is None:
            return
        new_rows, new_mask, ecc = done
        spares = base_spares + len(new_rows) + new_mask.bit_count()
        key = (ecc, spares) if policy is Policy.RELIABILITY_FIRST else (spares, ecc)
        if best is None or key < best[0]:
            best = (key, new_rows, new_mask, ecc)

    visit(frozenset(), 0, kernel.rows_left, kernel.cols_left)
    if best is None:
        return None
    _, rows, ymask, ecc = best
    cols = frozenset(c for c in range(ymask.bit_length()) if ymask >> c & 1)
    return Solution(kernel.must_rows | rows, kernel.must_cols | cols, ecc)
