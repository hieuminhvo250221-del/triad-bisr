import random

import pytest

from triad.baselines import ALGORITHMS, esp
from triad.core import Policy, Resources, brute_force, evaluate, is_valid
from triad.defects import MIXES, Geometry, sample
from triad.solver import cam_bound, kernelize, solve

CASES = [(r, s, k) for r in range(4) for s in range(4) for k in (0, 1, 2, 3, 99)]


def random_map(rng: random.Random, words: int, bits: int, density: float) -> dict[int, int]:
    faults = {}
    for w in range(words):
        m = sum(1 << b for b in range(bits) if rng.random() < density)
        if m:
            faults[w] = m
    return faults


@pytest.mark.parametrize("policy", list(Policy))
def test_matches_brute_force_on_dense_maps(policy):
    rng = random.Random(1234)
    repaired = 0
    for _ in range(3000):
        faults = random_map(rng, rng.randint(1, 6), rng.randint(1, 5), rng.choice((0.1, 0.25, 0.45)))
        res = Resources(*rng.choice(CASES))
        ref = brute_force(faults, res, policy)
        got = solve(faults, res, policy)
        assert (ref is None) == (got is None), (faults, res)
        if got is not None:
            assert is_valid(faults, res, got), (faults, res, got)
            assert got.objective(policy) == ref.objective(policy), (faults, res, got, ref)
            repaired += 1
    assert repaired > 500


@pytest.mark.parametrize("policy", list(Policy))
def test_matches_brute_force_on_physical_defects(policy):
    rng = random.Random(99)
    geom = Geometry(16, 8, 2)
    repaired = unrepairable = 0
    for _ in range(1500):
        mix = MIXES[rng.choice(("cells", "mixed", "lines"))]
        faults = sample(rng, geom, rng.randint(1, 7), mix)
        res = Resources(rng.randint(0, 2), rng.randint(0, 2), rng.choice((0, 1, 2, 4, 99)))
        ref = brute_force(faults, res, policy)
        got = solve(faults, res, policy)
        assert (ref is None) == (got is None), (faults, res)
        if got is None:
            unrepairable += 1
        else:
            assert is_valid(faults, res, got)
            assert got.objective(policy) == ref.objective(policy), (faults, res, got, ref)
            repaired += 1
    assert repaired > 300 and unrepairable > 100


def test_fault_store_bound_holds_for_every_repairable_map():
    rng = random.Random(7)
    geom = Geometry(64, 12, 2)
    checked = 0
    for _ in range(4000):
        res = Resources(rng.randint(0, 3), rng.randint(0, 2), rng.choice((0, 1, 2, 4)))
        faults = sample(rng, geom, rng.randint(1, 14), MIXES[rng.choice(("cells", "mixed"))])
        if solve(faults, res) is None:
            continue
        kernel = kernelize(faults, res)
        assert kernel is not None
        assert len(kernel.faults) <= cam_bound(res.rows, res.cols, res.ecc_budget)
        checked += 1
    assert checked > 500


def test_triad_dominates_every_ecc_first_scheme():
    rng = random.Random(21)
    geom = Geometry(64, 12, 2)
    compared = 0
    for _ in range(3000):
        res = Resources(rng.randint(0, 3), rng.randint(0, 2), rng.choice((1, 2, 4, 8)))
        faults = sample(rng, geom, rng.randint(1, 12), MIXES["mixed"])
        triad = solve(faults, res, Policy.RELIABILITY_FIRST)
        for name in ("greedy_joint", "ef_exact_bb", "ef_exact", "ef_esp"):
            other = ALGORITHMS[name](faults, res)
            if other is not None:
                assert is_valid(faults, res, other), (name, faults, res, other)
                assert triad is not None and triad.ecc_words <= other.ecc_words
                compared += 1
    assert compared > 1000


def test_esp_cover_is_valid_and_never_beats_exact():
    rng = random.Random(5)
    geom = Geometry(32, 8, 2)
    for _ in range(2000):
        rows, cols = rng.randint(0, 3), rng.randint(0, 3)
        faults = sample(rng, geom, rng.randint(1, 6), MIXES["mixed"])
        sol = esp(faults, rows, cols)
        if sol is not None:
            assert len(sol.rows) <= rows and len(sol.cols) <= cols
            assert evaluate(faults, sol.rows, sol.cols) == 0
            assert solve(faults, Resources(rows, cols, 0)) is not None


def test_policies_trade_spares_for_ecc_words():
    rng = random.Random(3)
    geom = Geometry(64, 12, 2)
    for _ in range(1500):
        res = Resources(rng.randint(0, 3), rng.randint(0, 2), rng.choice((1, 2, 4, 8)))
        faults = sample(rng, geom, rng.randint(1, 10), MIXES["mixed"])
        rel = solve(faults, res, Policy.RELIABILITY_FIRST)
        sav = solve(faults, res, Policy.SPARE_SAVING)
        assert (rel is None) == (sav is None)
        if rel is not None:
            assert rel.ecc_words <= sav.ecc_words and sav.spares <= rel.spares


def test_defect_geometry():
    geom = Geometry(words=16, bits=4, wpr=2)
    assert (geom.phys_rows, geom.phys_cols) == (8, 8)
    assert geom.cell(3, 5) == (7, 2)
    row = sample(random.Random(0), geom, 1, {"row": 1.0})
    assert len(row) == 2 and all(m == 0b1111 for m in row.values())
    col = sample(random.Random(0), geom, 1, {"col": 1.0})
    assert len(col) == 8 and len(set(col.values())) == 1 and all(m.bit_count() == 1 for m in col.values())
    for seed in range(50):
        pair = sample(random.Random(seed), geom, 1, {"pair_h": 1.0})
        assert all(m.bit_count() == 1 for m in pair.values())
