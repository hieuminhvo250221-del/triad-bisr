import random
from itertools import combinations

from triad.ecc import CODE_BITS, COLUMNS, DATA_BITS, decode, encode


def test_columns_are_distinct_and_odd():
    assert len(set(COLUMNS)) == DATA_BITS
    assert all(c.bit_count() % 2 == 1 and c.bit_count() >= 3 for c in COLUMNS)


def test_single_errors_are_corrected_and_double_errors_detected():
    rng = random.Random(1)
    for _ in range(300):
        data = rng.getrandbits(DATA_BITS)
        code = encode(data)
        assert decode(code) == (data, False, False)
        for i in range(CODE_BITS):
            assert decode(code ^ 1 << i) == (data, True, False)
        for i, j in combinations(range(CODE_BITS), 2):
            _, ce, ue = decode(code ^ 1 << i ^ 1 << j)
            assert ue and not ce
