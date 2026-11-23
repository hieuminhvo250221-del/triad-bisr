import random
from math import comb

import pytest

from triad import ecc
from triad.reliability import fit, fit_unprotected, lam_per_bit_hour, triple_error_outcomes


def test_triple_outcomes_match_random_codewords():
    frac = triple_error_outcomes()
    assert abs(sum(frac.values()) - 1) < 1e-12
    rng = random.Random(3)
    seen = {"sdc": 0, "due": 0, "benign": 0}
    for _ in range(20000):
        data = rng.getrandbits(24)
        code = ecc.encode(data)
        for b in rng.sample(range(30), 3):
            code ^= 1 << b
        got, _, ue = ecc.decode(code)
        seen["due" if ue else "sdc" if got != data else "benign"] += 1
    for k in frac:
        assert abs(seen[k] / 20000 - frac[k]) < 0.015


def test_fit_limits():
    lam = lam_per_bit_hour(1000)
    assert lam == pytest.approx(1e-12)
    clean = fit(0, 256, 1000, 1000)
    assert clean["sdc"] == 0
    assert clean["due"] == pytest.approx(256 * comb(30, 2) * lam ** 2 * 1000 * 1e9)
    one = fit(1, 256, 1000, 0, activation=1.0)       # no accumulation: only the single-upset term
    assert one["due"] == pytest.approx(29 * lam * 1e9) and one["sdc"] == 0
    assert fit(8, 256, 1000, 1000)["due"] == pytest.approx(8 * 0.5 * 29e-3, rel=1e-3)
    assert fit_unprotected(256, 24, 1000) == pytest.approx(6.144)


def test_fit_is_monotone_in_consumed_words():
    vals = [fit(e, 256, 1000, 8760)["due"] for e in range(0, 17)]
    assert vals == sorted(vals) and vals[0] < vals[1]
