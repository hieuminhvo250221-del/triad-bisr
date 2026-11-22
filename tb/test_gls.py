"""cocotb gate-level test: the routed netlist (tb/gls.sh <tag>) must self-repair like the golden
model.  Internals are flattened, so the repair state is checked through the signature port:
export the chain, decode with from_signature, compare with the model."""
import os
import random

import cocotb
from cocotb.triggers import FallingEdge, RisingEdge, with_timeout

from triad.defects import MIXES, Geometry, sample
from triad.hwmodel import HwConfig, allocate, check, effective, from_signature

CFG = HwConfig(pbits=4, rows=2)  # PBITS=4, R=2 are fixed in the routed netlist
GEOM = Geometry(256, 32, 2)
SIG_LEN = 12 * CFG.parts + 9 * CFG.rows


async def bist(dut, raw, budget, rng):
    """Inject `raw` as stuck-at faults (random polarity), run self-repair, return the status."""
    for a in range(256):
        m = raw.get(a, 0)
        pol = rng.getrandbits(32)
        dut.dut.u_sram.sa0[a].value = m & pol
        dut.dut.u_sram.sa1[a].value = m & ~pol
    for name in ("bist_start", "req_en", "req_we", "req_addr", "req_wdata", "sig_shift", "sig_in"):
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


async def export_signature(dut):
    """Rotate the chain L times feeding sig_out back into sig_in; return the L-bit signature."""
    val = 0
    dut.sig_shift.value = 1
    for _ in range(SIG_LEN):
        bit = int(dut.sig_out.value)
        dut.sig_in.value = bit
        val = (val << 1) | bit
        await FallingEdge(dut.clk)
    dut.sig_shift.value = 0
    dut.sig_in.value = 0
    await FallingEdge(dut.clk)
    return val


async def check_map(dut, raw, budget, rng, name):
    ref = allocate(raw, CFG, budget)
    assert check(raw, CFG, budget, ref)
    got = await bist(dut, raw, budget, rng)
    tag = f"{name}: model={ref.repairable}/{ref.ecc_words} rtl={got}"
    if ref.repairable:
        assert got["passed"] == 1 and got["code"] == 0, tag
        assert got["ecc"] == ref.ecc_words and got["spares"] == len(ref.spare_words), tag
        bits = await export_signature(dut)
        assert from_signature(bits, CFG) == (ref.steer, ref.spare_words), tag
        ecc_words = {w for w, m in raw.items() if w not in ref.spare_words
                     and effective(m, ref.steer[w // CFG.win], CFG.code_bits)}
        assert await user_check(dut, rng, ecc_words) == 0, tag
    else:
        assert got["passed"] == 0 and got["code"] == 1, tag
    dut._log.info("%s: pass=%d code=%d ecc=%d spares=%d (model %s)",
                  name, got["passed"], got["code"], got["ecc"], got["spares"], ref.repairable)
    return ref.repairable


@cocotb.test()
async def gls_cases(dut):
    rng = random.Random(7)
    R = CFG.rows
    assert await check_map(dut, {}, 0, rng, "fault_free")
    assert await check_map(dut, {37: 1 << 5}, 0, rng, "one_cell")
    assert await check_map(dut, {100: 0x3FFFFFFF, 101: 0x3FFFFFFF}, 0, rng, "dead_word_x2")
    assert await check_map(dut, {a: 1 << 12 for a in range(0, 256, 2)}, 0, rng,
                           "dead_bitline_all_partitions")
    assert not await check_map(dut, {a: 0x3FFFFFFF for a in range(8, 8 + R + 1)}, 0, rng,
                               "unrepairable")
    if os.environ.get("GLS_RANDOM", "1") != "0":
        for i in range(3):
            raw = sample(rng, GEOM, rng.randint(1, 24),
                         MIXES[rng.choice(("cells", "mixed", "kang_dl"))])
            await check_map(dut, raw, rng.choice((0, 2, 8)), rng, f"random_{i}")
