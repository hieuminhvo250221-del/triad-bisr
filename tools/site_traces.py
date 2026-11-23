#!/usr/bin/env python3
"""tools/site_traces.py — repair walkthrough traces for the website stepper.

Run with PYTHONPATH=model (site_data.py does that itself). For each fixed scenario it runs the
golden model (triad.hwmodel) exactly as tb/test_top.py::compare does — allocate + check — and
stores the fault map, the allocator's decisions and the derived ECC-reliant words as JSON so the
page only renders, never allocates.

    PYTHONPATH=model python tools/site_traces.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))

from triad.hwmodel import HwConfig, allocate, check, effective  # noqa: E402

OUT = ROOT / "site" / "src" / "data" / "generated" / "traces.json"

CFG = HwConfig(pbits=4, rows=2)

SCENARIOS = [
    ("cells", 0, {37: 1 << 5, 90: 1 << 17, 91: 1 << 3, 200: 1 << 22}),
    ("bitline", 0, {a: 1 << 12 for a in range(0, 256, 2)}),
    ("mixed", 1, {100: 0x3FFFFFFF, 101: 0x3FFFFFFF, 5: 1 << 1, 6: 1 << 2, 7: 1 << 3}),
    ("bad-spare", 0, {37: (1 << 31) | (1 << 5)}),
    ("unrepairable", 31, {a: 0x3FFFFFFF for a in range(8, 11)}),
]


def main() -> None:
    scenarios = []
    for sid, K, raw in SCENARIOS:
        res = allocate(raw, CFG, K)
        assert check(raw, CFG, K, res), f"{sid}: check() failed"
        ecc_reliant = sorted(
            w for w, m in raw.items()
            if w not in res.spare_words
            and effective(m, res.steer[w // CFG.win], CFG.code_bits)
        )
        faults = sorted((w, b) for w, m in raw.items() for b in range(32) if m >> b & 1)
        scenarios.append({
            "id": sid,
            "K": K,
            "R": CFG.rows,
            "faults": faults,
            "repairable": res.repairable,
            "ecc_words": res.ecc_words,
            "steer": [list(p) for p in res.steer],
            "spare_words": sorted(res.spare_words),
            "ecc_reliant": ecc_reliant,
        })
        print(
            f"{sid:13s} K={K:2d}  repairable={str(res.repairable):5s} "
            f"ecc_words={res.ecc_words}  spare_words={sorted(res.spare_words)}  "
            f"faults={len(faults)}"
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "cfg": {
            "words": CFG.words, "code_bits": CFG.code_bits,
            "parts": CFG.parts, "win": CFG.win, "R": CFG.rows,
            "spare_cols": [CFG.code_bits, CFG.code_bits + 1],
        },
        "scenarios": scenarios,
    }, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
