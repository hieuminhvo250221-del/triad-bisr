"""cocotb system tests: the RTL self-repair must agree with the hardware-faithful golden model."""
import os
import random

import cocotb
from cocotb.triggers import FallingEdge, RisingEdge, with_timeout

from triad.defects import MIXES, Geometry, sample
from triad.hwmodel import HwConfig, allocate, check, effective

PBITS = int(os.environ.get("TB_PBITS", "4"))
R = int(os.environ.get("TB_R", "2"))
CFG = HwConfig(pbits=PBITS, rows=R)
GEOM = Geometry(256, 32, 2)  # all 32 physical bits, so the spare columns can be faulty too


async def bist(dut, raw, budget, rng):
    """Inject `raw` as stuck-at faults (random polarity), run self-repair, return the status."""
    for a in range(256):
        m = raw.get(a, 0)
        pol = rng.getrandbits(32)
        dut.dut.u_sram.sa0[a].value = m & pol
        dut.dut.u_sram.sa1[a].value = m & ~pol
    for name in ("bist_start", "req_en", "req_we", "req_addr", "req_wdata"):
        getattr(dut, name).value = 0
    dut.cfg_k.value = budget
    dut.rst_n.value = 0
    for _ in range(3):
        await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)
    dut.bist_start.value = 1
    await FallingEdge(dut.clk)
    dut.bist_start.value = 0
    await with_timeout(RisingEdge(dut.bist_done), 40, "ms")
    await FallingEdge(dut.clk)
    return dict(passed=int(dut.bist_pass.value), code=int(dut.stat_fail_code.value),
                ecc=int(dut.stat_ecc_words.value), spares=int(dut.stat_spare_words.value))


def repair_state(dut):
    s0, s1 = int(dut.dut.u_dpath.sel0_flat.value), int(dut.dut.u_dpath.sel1_flat.value)
    dec = lambda v: (v & 31) if v & 32 else None
    steer = tuple((dec(s0 >> 6 * p & 63), dec(s1 >> 6 * p & 63)) for p in range(CFG.parts))
    valid, addr = int(dut.dut.u_dpath.sw_valid.value), int(dut.dut.u_dpath.sw_addr.value)
    words = frozenset(addr >> 8 * i & 255 for i in range(R) if valid >> i & 1)
    return steer, words


async def user_check(dut, rng, ecc_words):
    """Every word must store random data, no uncorrectable error, and ECC is used only on `ecc_words`."""
    data = [rng.getrandbits(24) for _ in range(256)]
    for a in range(256):
        dut.req_en.value, dut.req_we.value, dut.req_addr.value, dut.req_wdata.value = 1, 1, a, data[a]
        await FallingEdge(dut.clk)
    dut.req_we.value = 0
    bad = 0
    for a in range(256):
        dut.req_en.value, dut.req_addr.value = 1, a
        await FallingEdge(dut.clk)
        dut.req_en.value = 0
        await FallingEdge(dut.clk)
        assert dut.rvalid.value == 1
        bad += int(dut.rdata.value) != data[a] or int(dut.rd_ue.value)
        bad += int(dut.rd_ce.value) and a not in ecc_words
    return bad


async def compare(dut, raw, budget, rng):
    ref = allocate(raw, CFG, budget)
    assert check(raw, CFG, budget, ref)
    got = await bist(dut, raw, budget, rng)
    tag = f"faulty words={len(raw)} K={budget} model={ref.repairable}/{ref.ecc_words} rtl={got}"
    if not raw:
        assert got["passed"] == 1 and got["code"] == 0, tag
    elif ref.repairable:
        assert got["passed"] == 1 and got["code"] == 0, tag
        assert got["ecc"] == ref.ecc_words and got["spares"] == len(ref.spare_words), tag
        assert repair_state(dut) == (ref.steer, ref.spare_words), tag
    else:
        assert got["passed"] == 0 and got["code"] == 1, tag
    if got["passed"]:
        ecc_words = {w for w, m in raw.items() if w not in ref.spare_words
                     and effective(m, ref.steer[w // CFG.win], CFG.code_bits)}
        assert await user_check(dut, rng, ecc_words) == 0, tag
    return ref.repairable


@cocotb.test()
async def directed_cases(dut):
    rng = random.Random(1)
    assert await compare(dut, {}, 0, rng)
    assert await compare(dut, {37: 1 << 5}, 0, rng)                       # one cell: steered away, no ECC needed
    assert await compare(dut, {37: 1 << 31, 38: 1 << 30}, 0, rng)          # faults only in the spare columns
    assert await compare(dut, {100: 0x3FFFFFFF, 101: 0x3FFFFFFF}, 0, rng) == (R >= 2)  # dead word line: two spare words
    assert await compare(dut, {a: 1 << 12 for a in range(0, 256, 2)}, 0, rng)  # dead bit line in every partition
    assert await compare(dut, {37: 1 << 31 | 1 << 5}, 0, rng)              # spare column 1 is bad where it is needed
    both = {37: 1 << 30 | 1 << 5, 38: 1 << 31 | 1 << 5}                    # each spare column bad on one of the words
    assert await compare(dut, both, 0, rng) == (R >= 1)
    assert await compare(dut, both, 1, rng)
    three = {5: 1 << 1, 6: 1 << 2, 7: 1 << 3}                              # three columns in one partition
    assert await compare(dut, three, 1 if R == 0 else 0, rng) == (R >= 1)
    over = {16 + i: 1 << (i + 1) for i in range(R + 3)}                    # one single fault more than the spares can hide
    assert not await compare(dut, over, 0, rng)                            # ... exceeds a budget of 0
    assert await compare(dut, over, 1, rng)                                # ... fits a budget of 1
    dead = {a: 0x3FFFFFFF for a in range(8, 8 + R + 1)}                    # one dead word too many
    assert not await compare(dut, dead, 31, rng)


@cocotb.test()
async def random_defect_maps(dut):
    rng = random.Random(int(os.environ.get("TB_SEED", "7")))
    n = int(os.environ.get("TB_MAPS", "24"))
    repaired = 0
    for _ in range(n):
        raw = sample(rng, GEOM, rng.randint(1, 24), MIXES[rng.choice(("cells", "mixed", "kang_dl"))])
        repaired += await compare(dut, raw, rng.choice((0, 2, 8)), rng)
    dut._log.info("random maps: %d repairable, %d not", repaired, n - repaired)
    assert 0 < repaired < n
