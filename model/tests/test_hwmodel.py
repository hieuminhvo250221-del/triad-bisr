import random
from itertools import combinations

from triad.core import Resources
from triad.defects import MIXES, Geometry, sample
from triad.hwmodel import HwConfig, HwResult, allocate, check, effective, from_signature, signature
from triad.partitioned import solve_partitioned


def test_matches_exact_partitioned_solver_when_spares_are_fault_free():
    rng = random.Random(2)
    geom = Geometry(256, 30, 2)
    repaired = failed = 0
    for _ in range(1500):
        cfg = HwConfig(pbits=rng.choice((2, 3, 4)), rows=rng.choice((1, 2, 4)))
        budget = rng.choice((0, 2, 8, 31))
        faults = sample(rng, geom, rng.randint(1, 30), MIXES[rng.choice(("cells", "mixed", "kang_dl"))])
        ref = solve_partitioned(faults, Resources(cfg.rows, 2, budget), geom.words, cfg.parts)
        got = allocate(faults, cfg, budget)
        assert got.repairable == (ref is not None), (faults, cfg, budget)
        assert check(faults, cfg, budget, got)
        if got.repairable:
            assert got.ecc_words == ref.ecc_words, (faults, cfg, budget, got, ref)
            repaired += 1
        else:
            failed += 1
    assert repaired > 400 and failed > 200


def reference(raw, cfg, budget):
    """Exhaustive optimum (minimum ECC words) with possibly faulty spare columns, for tiny memories."""
    cols = [None] + list(range(cfg.code_bits))
    opts = [(a, b) for a in cols for b in cols if a is None or a != b]
    words = sorted(raw)
    best = None
    for n in range(min(cfg.rows, len(words)) + 1):
        for xs in map(set, combinations(words, n)):
            total = 0
            for p in range(cfg.parts):
                part_best = None
                for opt in opts:
                    ecc = 0
                    for w in words:
                        if w // cfg.win != p or w in xs:
                            continue
                        v = effective(raw[w], opt, cfg.code_bits)
                        if v & (v - 1):
                            ecc = None
                            break
                        ecc += v != 0
                    if ecc is not None and (part_best is None or ecc < part_best):
                        part_best = ecc
                if part_best is None:
                    total = None
                    break
                total += part_best
            if total is not None and (best is None or total < best):
                best = total
    return best if best is not None and best <= budget else None


def test_matches_exhaustive_search_with_faulty_spare_columns():
    rng = random.Random(9)
    repaired = failed = 0
    for _ in range(1200):
        cfg = HwConfig(words=8, code_bits=4, pbits=rng.choice((0, 1, 2)), rows=rng.choice((0, 1, 2)))
        budget = rng.choice((0, 1, 2, 8))
        density = rng.choice((0.08, 0.2, 0.35))
        raw = {}
        for w in range(cfg.words):
            m = sum(1 << b for b in range(cfg.code_bits + 2) if rng.random() < density)
            if m:
                raw[w] = m
        ref = reference(raw, cfg, budget)
        got = allocate(raw, cfg, budget)
        assert got.repairable == (ref is not None), (raw, cfg, budget, got, ref)
        assert check(raw, cfg, budget, got)
        if got.repairable:
            assert got.ecc_words == ref, (raw, cfg, budget, got, ref)
            repaired += 1
        else:
            failed += 1
    assert repaired > 300 and failed > 100


def test_signature_round_trip():
    rng = random.Random(5)
    for _ in range(300):
        cfg = HwConfig(pbits=rng.choice((1, 2, 4)), rows=rng.choice((1, 2, 4)))
        cols = (None,) + tuple(range(cfg.code_bits))
        steer = tuple((rng.choice(cols), rng.choice(cols)) for _ in range(cfg.parts))
        words = frozenset(rng.sample(range(cfg.words), rng.randint(0, cfg.rows)))
        value = signature(HwResult(True, 0, steer, words), cfg)
        assert value.bit_length() <= 12 * cfg.parts + 9 * cfg.rows
        assert from_signature(value, cfg) == (steer, words)
