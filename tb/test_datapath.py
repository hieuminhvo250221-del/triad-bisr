"""cocotb unit tests of the repair datapath (ECC, partitioned bit steering, spare words)."""
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from triad.ecc import encode

PERIOD_NS = 40


async def reset(dut):
    cocotb.start_soon(Clock(dut.clk, PERIOD_NS, units="ns").start())
    for name in ("en", "we", "raw", "addr", "wdata", "cfg_clear", "steer_we", "steer_part", "steer_sel0",
                 "steer_sel1", "spare_we", "spare_addr"):
        getattr(dut, name).value = 0
    for a in range(256):  # faults injected by an earlier test must not leak into this one
        stick(dut, a)
    dut.rst_n.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def access(dut, addr, we=0, wdata=0, raw=0):
    dut.en.value, dut.we.value, dut.raw.value, dut.addr.value, dut.wdata.value = 1, we, raw, addr, wdata
    await RisingEdge(dut.clk)
    dut.en.value, dut.we.value = 0, 0


async def write(dut, addr, data, raw=0):
    await access(dut, addr, 1, data, raw)


async def read(dut, addr, raw=0):
    """Returns (data, corrected, uncorrectable, raw 32 bits); two clock edges after the request."""
    await access(dut, addr, 0, 0, raw)
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")
    assert dut.rvalid.value == 1
    return int(dut.rdata.value), int(dut.rd_ce.value), int(dut.rd_ue.value), int(dut.rraw.value)


async def pulse(dut, **signals):
    for name, value in signals.items():
        getattr(dut, name).value = value
    await RisingEdge(dut.clk)
    for name in signals:
        if name.endswith("_we") or name == "cfg_clear":
            getattr(dut, name).value = 0


def stick(dut, addr, sa0=0, sa1=0):
    dut.u_ram.sa0[addr].value = sa0
    dut.u_ram.sa1[addr].value = sa1


@cocotb.test()
async def fault_free_memory_stores_every_word(dut):
    await reset(dut)
    rng = random.Random(1)
    data = [rng.getrandbits(24) for _ in range(256)]
    for a in range(256):
        await write(dut, a, data[a])
    for a in rng.sample(range(256), 256):
        assert await read(dut, a) == (data[a], 0, 0, encode(data[a])), a


@cocotb.test()
async def raw_mode_reaches_all_32_physical_bits(dut):
    await reset(dut)
    stick(dut, 7, sa0=0x8000_0001, sa1=0x0000_0100)
    await write(dut, 7, 0xFFFF_FFFF, raw=1)
    assert (await read(dut, 7, raw=1))[3] == 0x7FFF_FFFE
    await write(dut, 7, 0, raw=1)
    assert (await read(dut, 7, raw=1))[3] == 0x0000_0100


@cocotb.test()
async def ecc_corrects_one_stuck_bit_and_flags_two(dut):
    await reset(dut)
    rng = random.Random(2)
    for bit in range(30):
        a, d = rng.randrange(256), rng.getrandbits(24)
        code = encode(d)
        stick(dut, a, sa1=1 << bit)
        await write(dut, a, d)
        assert await read(dut, a) == (d, 1 - (code >> bit & 1), 0, code | 1 << bit), (a, bit)
        stick(dut, a)
    d = 0x5A5A5A
    code = encode(d)
    b0, b1 = 3, 28
    flips = 1 << b0 | 1 << b1  # invert two stored bits: stuck-at-0 where the code has 1, stuck-at-1 where it has 0
    stick(dut, 200, sa0=code & flips, sa1=~code & flips)
    await write(dut, 200, d)
    _, ce, ue, _ = await read(dut, 200)
    assert (ce, ue) == (0, 1)


@cocotb.test()
async def steering_is_per_partition_and_hides_a_bad_column(dut):
    await reset(dut)
    rng = random.Random(3)
    plan = {2: (5, None), 9: (27, 0), 15: (None, 13)}  # partition -> columns replaced by spare 0 / spare 1
    for part, cols in plan.items():
        for a in range(part * 16, part * 16 + 16):
            stick(dut, a, sa1=sum(1 << c for c in cols if c is not None))
        sel = [0x20 | c if c is not None else 0 for c in cols]
        await pulse(dut, steer_we=1, steer_part=part, steer_sel0=sel[0], steer_sel1=sel[1])
    data = [rng.getrandbits(24) for _ in range(256)]
    for a in range(256):
        await write(dut, a, data[a])
    for a in range(256):
        d, ce, ue, _ = await read(dut, a)
        assert (d, ce, ue) == (data[a], 0, 0), a
    # without the table the same faults are visible to the ECC again
    await pulse(dut, cfg_clear=1)
    seen = 0
    for a in range(9 * 16, 9 * 16 + 16):
        d, ce, ue, _ = await read(dut, a)
        seen += ce | ue
    assert seen > 0


@cocotb.test()
async def spare_words_replace_dead_words(dut):
    await reset(dut)
    dead = [17, 250]
    for a in dead:
        stick(dut, a, sa0=0x3FFF_FFFF)
    await write(dut, 17, 0xABCDEF)
    assert (await read(dut, 17))[0] != 0xABCDEF
    for n, a in enumerate(dead):
        await pulse(dut, spare_we=1, spare_addr=a)
        await Timer(1, units="ns")
        assert dut.spare_count.value == n + 1
    await pulse(dut, spare_we=1, spare_addr=99)  # no spare word left: ignored
    await Timer(1, units="ns")
    assert dut.spare_count.value == 2
    rng = random.Random(4)
    data = {a: rng.getrandbits(24) for a in (16, 17, 18, 249, 250, 251)}
    for a, d in data.items():
        await write(dut, a, d)
    for a, d in data.items():
        assert (await read(dut, a))[:3] == (d, 0, 0), a
