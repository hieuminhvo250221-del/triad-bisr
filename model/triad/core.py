"""Problem definition, solution checker and brute-force reference.

Model
-----
A memory has N words of W physical bits.  A *fault map* maps a word address to the bitmask of its
faulty bit columns.  Three resources can hide faults:

* R spare words ("rows"): a spare word replaces one whole word,
* S spare bit columns: a spare column replaces one bit position in every word,
* SEC-DED ECC: tolerates at most one remaining faulty bit in a word.  A word that relies on ECC
  for a hard fault is *ECC-consumed* (a single soft error there becomes uncorrectable), so at most
  K such words are allowed (the ECC budget).

(X, Y) with |X| <= R, |Y| <= S is a repair iff every word outside X has at most one faulty bit
outside Y and the number E of words with exactly one such bit is <= K.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from typing import Iterable, Mapping, Optional

FaultMap = Mapping[int, int]  # word address -> bitmask of faulty bit columns


class Policy(str, Enum):
    RELIABILITY_FIRST = "reliability_first"  # minimise (ecc_words, spares)
    SPARE_SAVING = "spare_saving"  # minimise (spares, ecc_words)


@dataclass(frozen=True)
class Resources:
    rows: int  # R: spare words
    cols: int  # S: spare bit columns
    ecc_budget: int  # K: maximum number of ECC-consumed words (0 = ECC not used for hard faults)


@dataclass(frozen=True)
class Solution:
    rows: frozenset[int]
    cols: frozenset[int]
    ecc_words: int

    @property
    def spares(self) -> int:
        return len(self.rows) + len(self.cols)

    def objective(self, policy: Policy) -> tuple[int, int]:
        if policy is Policy.RELIABILITY_FIRST:
            return (self.ecc_words, self.spares)
        return (self.spares, self.ecc_words)


def col_mask(cols: Iterable[int]) -> int:
    mask = 0
    for c in cols:
        mask |= 1 << c
    return mask


def evaluate(faults: FaultMap, rows: Iterable[int], cols: Iterable[int]) -> Optional[int]:
    """Number of ECC-consumed words left by (rows, cols), or None if some word keeps >= 2 faults."""
    rows = set(rows)
    keep = ~col_mask(cols)
    ecc = 0
    for word, mask in faults.items():
        if word in rows:
            continue
        mask &= keep
        if mask == 0:
            continue
        if mask & (mask - 1):
            return None
        ecc += 1
    return ecc


def is_valid(faults: FaultMap, res: Resources, sol: Solution) -> bool:
    """Independent check of a claimed repair (used on RTL results as well)."""
    if len(sol.rows) > res.rows or len(sol.cols) > res.cols:
        return False
    ecc = evaluate(faults, sol.rows, sol.cols)
    return ecc is not None and ecc == sol.ecc_words and ecc <= res.ecc_budget


def brute_force(faults: FaultMap, res: Resources, policy: Policy) -> Optional[Solution]:
    """Optimal repair by exhaustive enumeration (reference for small instances only)."""
    words = sorted(w for w, m in faults.items() if m)
    union = 0
    for w in words:
        union |= faults[w]
    columns = [c for c in range(union.bit_length()) if union >> c & 1]
    best: Optional[Solution] = None
    for nr in range(min(res.rows, len(words)) + 1):
        for xs in combinations(words, nr):
            for ns in range(min(res.cols, len(columns)) + 1):
                for ys in combinations(columns, ns):
                    ecc = evaluate(faults, xs, ys)
                    if ecc is None or ecc > res.ecc_budget:
                        continue
                    cand = Solution(frozenset(xs), frozenset(ys), ecc)
                    if best is None or cand.objective(policy) < best.objective(policy):
                        best = cand
    return best
