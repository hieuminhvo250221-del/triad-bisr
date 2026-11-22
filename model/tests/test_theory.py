"""Machine checks of the statements in docs/04_theory.md."""
import random
from itertools import combinations

import pytest

from triad.colenum import solve_by_columns
from triad.core import Policy, Resources, brute_force, is_valid
from triad.defects import MIXES, Geometry, sample
from triad.solver import cam_bound, kernelize, solve

BIG = 10 ** 6


def random_graph(rng: random.Random, words: int, cols: int, density: float) -> dict[int, int]:
    g = {}
    for w in range(words):
        m = sum(1 << c for c in range(cols) if rng.random() < density)
        if m:
            g[w] = m
    return g


def has_cover(g: dict[int, int], rows: int, cols: int) -> bool:
    """Constrained bipartite vertex cover (the classical spare allocation problem)."""
    return brute_force(g, Resources(rows, cols, 0), Policy.SPARE_SAVING) is not None


@pytest.mark.parametrize("budget", [1, 2, 3])
def test_hardness_reduction_for_fixed_budget(budget):
    """CBVC(G, R, S) is a yes-instance  <=>  G plus `budget` isolated faults is repairable with (R, S, K)."""
    rng = random.Random(40 + budget)
    yes = no = 0
    for _ in range(1500):
        words, cols = rng.randint(1, 5), rng.randint(1, 5)
        g = random_graph(rng, words, cols, rng.choice((0.2, 0.4, 0.6)))
        rows, scols = rng.randint(0, 3), rng.randint(0, 3)
        padded = dict(g)
        for i in range(budget):  # gadget: new word with one fault in a new private column
            padded[words + i] = 1 << (cols + i)
        expected = has_cover(g, rows, scols)
        assert (solve(padded, Resources(rows, scols, budget)) is not None) == expected, (g, rows, scols)
        yes, no = yes + expected, no + (not expected)
    assert yes > 200 and no > 200


def test_hardness_reduction_for_unlimited_ecc():
    """CBVC(G, R, S)  <=>  G with a private pendant fault on every word is repairable with unlimited ECC."""
    rng = random.Random(77)
    yes = no = 0
    for _ in range(1500):
        words, cols = rng.randint(1, 5), rng.randint(1, 5)
        g = random_graph(rng, words, cols, rng.choice((0.2, 0.4, 0.6)))
        rows, scols = rng.randint(0, 3), rng.randint(0, 3)
        pend = {w: g.get(w, 0) | 1 << (cols + w) for w in range(words)}
        expected = has_cover(g, rows, scols)
        assert (solve(pend, Resources(rows, scols, BIG)) is not None) == expected, (g, rows, scols)
        yes, no = yes + expected, no + (not expected)
    assert yes > 200 and no > 200


def test_columns_plus_ecc_is_vertex_cover():
    """R = 0, unlimited ECC, every word has two faults: repairable with S columns <=> vertex cover of size S."""
    rng = random.Random(3)
    yes = no = 0
    for _ in range(800):
        n = rng.randint(2, 7)
        edges = [e for e in combinations(range(n), 2) if rng.random() < 0.4]
        if not edges:
            continue
        size = rng.randint(0, n - 1)
        expected = any(all(a in vc or b in vc for a, b in edges) for vc in map(set, combinations(range(n), size)))
        faults = {i: 1 << a | 1 << b for i, (a, b) in enumerate(edges)}
        assert (solve(faults, Resources(0, size, BIG)) is not None) == expected, (edges, size)
        yes, no = yes + expected, no + (not expected)
    assert yes > 100 and no > 100


@pytest.mark.parametrize("rows", [0, 1, 2, 4])
@pytest.mark.parametrize("cols", [0, 1, 2, 3])
@pytest.mark.parametrize("budget", [0, 1, 3, 8])
def test_fault_store_bound_is_tight(rows, cols, budget):
    """A repairable instance on which no must-repair rule fires and that has exactly bound(R, S, K) faulty words
    (for S >= 1 or K >= 1)."""
    faults, word, col = {}, 0, 0
    for _ in range(cols):  # S columns, each with R + K single-fault words
        for _ in range(rows + budget):
            faults[word] = 1 << col
            word += 1
        col += 1
    for _ in range(budget):  # K isolated single faults
        faults[word] = 1 << col
        word, col = word + 1, col + 1
    heavy = 2 if (cols >= 1 and budget >= 1) or cols >= 2 else 1  # faults per word that needs a spare word
    for _ in range(rows):
        faults[word] = sum(1 << (col + i) for i in range(heavy))
        word, col = word + 1, col + heavy
    res = Resources(rows, cols, budget)
    bound = cam_bound(rows, cols, budget)
    assert len(faults) == bound
    kernel = kernelize(faults, res)
    assert kernel is not None
    if cols == 0 and budget == 0:
        # degenerate case: without columns and without ECC every faulty word is must-repair, the kernel is empty
        assert kernel.must_rows == frozenset(faults) and not kernel.faults
        return
    assert not kernel.must_rows and not kernel.must_cols and len(kernel.faults) == bound
    assert solve(faults, res) is not None
    assert solve_by_columns(faults, res) is not None


@pytest.mark.parametrize("policy", list(Policy))
def test_column_enumeration_is_exact(policy):
    rng = random.Random(8)
    geom = Geometry(64, 12, 2)
    repaired = 0
    for _ in range(2500):
        res = Resources(rng.randint(0, 3), rng.randint(0, 2), rng.choice((0, 1, 2, 4, 99)))
        faults = sample(rng, geom, rng.randint(1, 12), MIXES[rng.choice(("cells", "mixed", "lines"))])
        a, b = solve(faults, res, policy), solve_by_columns(faults, res, policy)
        assert (a is None) == (b is None), (faults, res)
        if a is not None:
            assert is_valid(faults, res, b) and a.objective(policy) == b.objective(policy), (faults, res, a, b)
            repaired += 1
    assert repaired > 500
