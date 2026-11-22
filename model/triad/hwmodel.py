"""Hardware-faithful golden model of the TRIAD-P allocator (docs/05_architecture.md, section 2).

Works on RAW fault maps: word address -> bitmask over all physical bits, where bits
[code_bits-1:0] hold the codeword and bits code_bits, code_bits+1 are the two spare columns.
A steering option (c0, c1) routes code bit c0 to spare column 0 and code bit c1 to spare column 1
(None = spare unused), so a fault of the spare column itself shows up at the steered position.

The RTL must reproduce `repairable`, `ecc_words` and the per-partition decisions of this model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

SAT = 63  # saturation value of the 6-bit ECC-word counters (any value above the budget is infeasible)


@dataclass(frozen=True)
class HwConfig:
    words: int = 256
    code_bits: int = 30
    pbits: int = 4  # P = 2**pbits partitions
    rows: int = 2  # R spare words

    @property
    def parts(self) -> int:
        return 1 << self.pbits

    @property
    def win(self) -> int:
        return self.words >> self.pbits


@dataclass(frozen=True)
class HwResult:
    repairable: bool
    ecc_words: int
    steer: tuple[tuple[Optional[int], Optional[int]], ...]  # per partition (c0, c1)
    spare_words: frozenset[int]


def effective(mask: int, opt: tuple[Optional[int], Optional[int]], code_bits: int) -> int:
    """Fault vector of the codeword as seen through steering option `opt`."""
    v = mask & (1 << code_bits) - 1
    for spare, col in enumerate(opt):
        if col is not None:
            v = v & ~(1 << col) | (mask >> (code_bits + spare) & 1) << col
    return v


def options(window: dict[int, int], code_bits: int):
    """Steering options in hardware order: c0 outer, c1 inner, None first then ascending columns."""
    union = 0
    for m in window.values():
        union |= m
    cols = [None] + [c for c in range(code_bits) if union >> c & 1]
    for c0 in cols:
        for c1 in cols:
            if c0 is None or c0 != c1:
                yield (c0, c1)


def classify(window: dict[int, int], opt, code_bits: int) -> tuple[list[int], list[int]]:
    multi, single = [], []
    for w in sorted(window):
        v = effective(window[w], opt, code_bits)
        if v & (v - 1):
            multi.append(w)
        elif v:
            single.append(w)
    return multi, single


def analyse_window(window: dict[int, int], cfg: HwConfig) -> tuple[list[int], list]:
    """e[q] = minimum ECC words with q spare words (SAT if impossible) and the option reaching it."""
    e = [SAT] * (cfg.rows + 1)
    best_opt: list = [(None, None)] * (cfg.rows + 1)
    for opt in options(window, cfg.code_bits):
        multi, single = classify(window, opt, cfg.code_bits)
        for q in range(len(multi), cfg.rows + 1):
            val = min(SAT, max(0, len(single) - (q - len(multi))))
            if val < e[q]:
                e[q], best_opt[q] = val, opt
    return e, best_opt


def allocate(raw: dict[int, int], cfg: HwConfig, budget: int) -> HwResult:
    windows = [{w: m for w, m in raw.items() if w // cfg.win == p and m} for p in range(cfg.parts)]
    best = [0] * (cfg.rows + 1)
    choice = []
    for window in windows:  # pass 1: analyse, dynamic programme over the shared spare words
        e, _ = analyse_window(window, cfg)
        new, pick = [], []
        for r in range(cfg.rows + 1):
            val, arg = SAT, 0
            for q in range(r + 1):
                cand = min(SAT, best[r - q] + e[q])
                if cand < val:
                    val, arg = cand, q
            new.append(val)
            pick.append(arg)
        best = new
        choice.append(pick)
    empty = tuple((None, None) for _ in windows)
    if best[cfg.rows] > budget:
        return HwResult(False, best[cfg.rows], empty, frozenset())
    steer: list = [None] * cfg.parts
    spare: set[int] = set()
    r = cfg.rows
    for p in range(cfg.parts - 1, -1, -1):  # pass 2: allocate
        q = choice[p][r]
        r -= q
        _, best_opt = analyse_window(windows[p], cfg)
        steer[p] = best_opt[q]
        multi, single = classify(windows[p], steer[p], cfg.code_bits)
        spare.update(multi + single[:q - len(multi)])
    return HwResult(True, best[cfg.rows], tuple(steer), frozenset(spare))


def signature(alloc: HwResult, cfg: HwConfig) -> int:
    """Repair state packed into the serial signature S (docs/05_architecture.md section 7).

    S = {sw_addr, sw_valid, sel1_flat, sel0_flat}, length 12*P + 9*R bits:
    S[6*p +: 6] = sel0 entry of partition p, S[6*P + 6*p +: 6] = sel1 of p (an invalid entry
    packs as 0), S[12*P + i] = sw_valid[i], S[12*P + R + 8*i +: 8] = address of spare word i
    (spare words in ascending address order for packing).  Bit L-1 leaves the chain first.
    """
    sel0_flat = sel1_flat = 0
    for p, (c0, c1) in enumerate(alloc.steer):
        if c0 is not None:
            sel0_flat |= (32 | c0) << 6 * p
        if c1 is not None:
            sel1_flat |= (32 | c1) << 6 * p
    words = sorted(alloc.spare_words)[: cfg.rows]
    valid = sum(1 << i for i in range(len(words)))
    addr = sum(w << 8 * i for i, w in enumerate(words))
    return (addr << (12 * cfg.parts + cfg.rows)) | (valid << 12 * cfg.parts) | \
        (sel1_flat << 6 * cfg.parts) | sel0_flat


def from_signature(value: int, cfg: HwConfig) -> tuple[tuple, frozenset]:
    """Unpack the serial signature into (steer, spare_words); the inverse of `signature`."""
    dec = lambda e: (e & 31) if e & 32 else None
    steer = tuple(
        (dec(value >> 6 * p & 63), dec(value >> (6 * cfg.parts + 6 * p) & 63))
        for p in range(cfg.parts))
    valid = value >> 12 * cfg.parts & (2 ** cfg.rows - 1)
    addr = value >> (12 * cfg.parts + cfg.rows)
    words = frozenset(addr >> 8 * i & 255 for i in range(cfg.rows) if valid >> i & 1)
    return steer, words


def check(raw: dict[int, int], cfg: HwConfig, budget: int, res: HwResult) -> bool:
    """Independent validation of a claimed repair."""
    if not res.repairable:
        return True
    if len(res.spare_words) > cfg.rows:
        return False
    ecc = 0
    for w, m in raw.items():
        if w in res.spare_words:
            continue
        v = effective(m, res.steer[w // cfg.win], cfg.code_bits)
        if v & (v - 1):
            return False
        ecc += v != 0
    return ecc == res.ecc_words and ecc <= budget
