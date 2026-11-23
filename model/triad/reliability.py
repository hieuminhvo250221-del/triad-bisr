"""Soft-error reliability of a SEC-DED protected memory in which some words spend their
correction capability on a hard fault ("ECC-consumed" words).

Model (single-bit upsets only, independent, rate lam per bit-hour; multi-bit upsets are not modelled):
  * clean word, n code bits: fails only if two upsets accumulate within the data lifetime T
    (time between rewrites or scrubs):  rate = C(n,2) * lam^2 * T   -> detected (DUE)
  * consumed word: its hard fault is an error only when the stored bit differs from the stuck value
    (activation probability a; 1/2 for a stuck-at cell and random data).  While active, any one
    upset in the other n-1 bits gives a double error:  rate = a * (n-1) * lam   -> detected (DUE)
    and two upsets within T give a triple error:  rate = a * C(n-1,2) * lam^2 * T, of which the
    fraction `triple_error_outcomes()["sdc"]` is miscorrected by the code   -> silent (SDC)
Rates are returned in FIT (failures per 1e9 device-hours).
"""
from __future__ import annotations

from itertools import combinations
from math import comb

from . import ecc


def lam_per_bit_hour(fit_per_mbit: float) -> float:
    return fit_per_mbit * 1e-9 / 1e6


def triple_error_outcomes() -> dict[str, float]:
    """Exact outcome fractions of the (30,24) decoder over all 4060 three-bit error patterns."""
    count = {"sdc": 0, "due": 0, "benign": 0}
    for bits in combinations(range(ecc.CODE_BITS), 3):
        err = sum(1 << b for b in bits)
        data, _, ue = ecc.decode(err)  # linear code: decode the error pattern on the all-zero word
        count["due" if ue else "sdc" if data else "benign"] += 1
    total = sum(count.values())
    return {k: v / total for k, v in count.items()}


def fit(consumed: float, words: int, fit_per_mbit: float, lifetime_h: float, activation: float = 0.5,
        code_bits: int = ecc.CODE_BITS) -> dict[str, float]:
    """FIT of the whole memory with `consumed` ECC-consumed words (may be a mean, hence float)."""
    lam = lam_per_bit_hour(fit_per_mbit)
    n = code_bits
    clean_pair = comb(n, 2) * lam ** 2 * lifetime_h
    used_single = activation * (n - 1) * lam
    used_pair = activation * comb(n - 1, 2) * lam ** 2 * lifetime_h
    idle = (1 - activation) * comb(n - 1, 2) * lam ** 2 * lifetime_h  # hard fault masked by the data
    p_sdc = triple_error_outcomes()["sdc"]
    due = consumed * (used_single + used_pair * (1 - p_sdc) + idle) + (words - consumed) * clean_pair
    sdc = consumed * used_pair * p_sdc
    return {"due": due * 1e9, "sdc": sdc * 1e9}


def fit_unprotected(words: int, data_bits: int, fit_per_mbit: float) -> float:
    """SDC FIT of the same memory without ECC: every upset of a data bit is silent."""
    return words * data_bits * lam_per_bit_hour(fit_per_mbit) * 1e9
