import random

import pytest

from triad.core import Policy, Resources
from triad.defects import MIXES, Geometry, sample
from triad.partitioned import brute_force_part, is_valid_part, solve_partitioned
from triad.solver import solve


def random_map(rng: random.Random, words: int, bits: int, density: float) -> dict[int, int]:
    faults = {}
    for w in range(words):
        m = sum(1 << b for b in range(bits) if rng.random() < density)
        if m:
            faults[w] = m
    return faults


@pytest.mark.parametrize("policy", list(Policy))
def test_one_partition_is_the_plain_problem(policy):
    rng = random.Random(11)
    geom = Geometry(64, 12, 2)
    repaired = 0
    for _ in range(1500):
        res = Resources(rng.randint(0, 3), rng.randint(0, 2), rng.choice((0, 1, 2, 4, 99)))
        faults = sample(rng, geom, rng.randint(1, 10), MIXES[rng.choice(("cells", "mixed"))])
        plain = solve(faults, res, policy)
        part = solve_partitioned(faults, res, geom.words, 1, policy)
        assert (plain is None) == (part is None), (faults, res)
        if part is not None:
            assert is_valid_part(faults, geom.words, 1, res, part)
            assert part.objective(policy) == plain.objective(policy), (faults, res, part, plain)
            repaired += 1
    assert repaired > 300


@pytest.mark.parametrize("policy", list(Policy))
@pytest.mark.parametrize("parts", [2, 4])
def test_matches_brute_force(policy, parts):
    rng = random.Random(100 + parts)
    repaired = unrepairable = 0
    for _ in range(1200):
        faults = random_map(rng, 8, rng.randint(2, 4), rng.choice((0.1, 0.25, 0.4)))
        res = Resources(rng.randint(0, 2), rng.randint(0, 2), rng.choice((0, 1, 2, 99)))
        ref = brute_force_part(faults, res, 8, parts, policy)
        got = solve_partitioned(faults, res, 8, parts, policy)
        assert (ref is None) == (got is None), (faults, res)
        if got is None:
            unrepairable += 1
        else:
            assert is_valid_part(faults, 8, parts, res, got), (faults, res, got)
            assert got.objective(policy) == ref.objective(policy), (faults, res, got, ref)
            repaired += 1
    assert repaired > 300 and unrepairable > 30


def test_finer_partitions_never_leave_more_ecc_words():
    rng = random.Random(5)
    geom = Geometry(64, 12, 2)
    compared = 0
    for _ in range(1500):
        res = Resources(rng.randint(0, 2), rng.randint(1, 2), rng.choice((0, 2, 4, 99)))
        faults = sample(rng, geom, rng.randint(1, 12), MIXES[rng.choice(("cells", "mixed"))])
        prev = None
        for parts in (1, 2, 4, 8, 16):
            sol = solve_partitioned(faults, res, geom.words, parts)
            if prev is not None:
                assert sol is not None and sol.ecc_words <= prev.ecc_words, (faults, res, parts)
                compared += 1
            prev = sol if sol is not None else prev
    assert compared > 1000
