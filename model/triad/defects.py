"""Physical defect model -> logical fault map.

The array has `words // wpr` physical rows and `bits * wpr` physical columns (column mux of `wpr`
words per row, bit-interleaved as OpenRAM does: physical column = bit * wpr + mux index).  Because
of the interleaving, horizontally adjacent cells belong to different words, a word-line defect
kills `wpr` complete words and a bit-line defect puts one faulty bit in `words // wpr` words.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Geometry:
    words: int
    bits: int
    wpr: int = 1  # words per physical row (column-mux ratio)

    @property
    def phys_rows(self) -> int:
        return self.words // self.wpr

    @property
    def phys_cols(self) -> int:
        return self.bits * self.wpr

    def cell(self, prow: int, pcol: int) -> tuple[int, int]:
        """(word address, bit) of a physical cell."""
        return prow * self.wpr + pcol % self.wpr, pcol // self.wpr


# Relative frequency of defect kinds.  These mixes are assumptions (the literature uses a range of
# them); results are reported per mix so the sensitivity is visible.
MIXES: dict[str, dict[str, float]] = {
    "cells": {"cell": 1.0},
    "mixed": {"cell": 0.70, "pair_h": 0.07, "pair_v": 0.07, "cluster": 0.06, "row": 0.05, "col": 0.05},
    "lines": {"cell": 0.50, "row": 0.25, "col": 0.25},
    # Mixes used in published BIRA evaluations, as reported by a secondary literature search
    # (docs/03_stronger_contribution.md); to be checked against the original papers before the paper is written.
    "kang_dl": {"cell": 0.804, "row": 0.097, "col": 0.097},  # Yonsei group, low line-fault density
    "kang_dh": {"cell": 0.448, "row": 0.278, "col": 0.274},  # Yonsei group, high line-fault density
    "date06": {"cell": 0.40, "pair_h": 0.20, "pair_v": 0.20, "cluster": 0.20},  # Tseng/Li, DATE 2006
}


def sample(rng: random.Random, geom: Geometry, n_defects: int, mix: dict[str, float]) -> dict[int, int]:
    faults: dict[int, int] = {}
    rows, cols = geom.phys_rows, geom.phys_cols

    def hit(pr: int, pc: int) -> None:
        if 0 <= pr < rows and 0 <= pc < cols:
            word, bit = geom.cell(pr, pc)
            faults[word] = faults.get(word, 0) | 1 << bit

    kinds = list(mix)
    for kind in rng.choices(kinds, [mix[k] for k in kinds], k=n_defects):
        pr, pc = rng.randrange(rows), rng.randrange(cols)
        if kind == "cell":
            hit(pr, pc)
        elif kind == "pair_h":
            hit(pr, pc), hit(pr, pc + 1)
        elif kind == "pair_v":
            hit(pr, pc), hit(pr + 1, pc)
        elif kind == "cluster":
            for dr in (0, 1):
                for dc in (0, 1):
                    hit(pr + dr, pc + dc)
        elif kind == "row":
            for c in range(cols):
                hit(pr, c)
        elif kind == "col":
            for r in range(rows):
                hit(r, pc)
        else:
            raise ValueError(f"unknown defect kind {kind!r}")
    return faults
