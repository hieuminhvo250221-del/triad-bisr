"""Reliability cost of repairing with ECC, from the evaluation-protocol Monte Carlo results.

    PYTHONPATH=model python model/analysis/fit_report.py build/proto build/export/reliability

For every allocator: repair rate, mean number of ECC-consumed words over the dies it repairs, and the
resulting DUE/SDC FIT (triad.reliability).  `paired_triad_ecc` is the plain TRIAD allocator's mean on
exactly the dies the baseline repaired, so that column pair compares like with like.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from triad.reliability import fit, fit_unprotected, triple_error_outcomes

FIT_PER_MBIT = 1000.0   # assumed raw soft-error rate; no measurement exists for this macro
LIFETIME_H = 8760.0     # data lifetime between rewrites (one year, no scrubbing)
ACTIVATION = 0.5
ALGOS = ["triad_rel", "triad_p4", "triad_p16", "greedy_joint", "ef_exact_bb", "ef_exact"]
BASELINES = {"greedy_joint", "ef_exact_bb", "ef_exact"}


def main(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    out = []
    for path in sorted(src.glob("protocol_*.csv")):
        for r in csv.DictReader(open(path)):
            if r["algo"] not in ALGOS or int(r["repaired"]) == 0:
                continue
            rep, words = int(r["repaired"]), int(r["words"])
            mean_e = int(r["sum_ecc"]) / rep
            f = fit(mean_e, words, FIT_PER_MBIT, LIFETIME_H, ACTIVATION, int(r["bits"]))
            out.append(dict(mix=r["mix"], R=r["R"], S=r["S"], K=r["K"], defects=r["defects"], algo=r["algo"],
                            trials=r["trials"], repair_rate=f"{rep / int(r['trials']):.4f}",
                            mean_ecc_words=f"{mean_e:.4f}",
                            paired_triad_ecc=f"{int(r['sum_ecc_triad']) / rep:.4f}" if r["algo"] in BASELINES else "",
                            fit_due=f"{f['due']:.5f}", fit_sdc=f"{f['sdc']:.3e}"))
    out.sort(key=lambda d: (d["mix"], int(d["R"]), int(d["K"]), int(d["defects"]), ALGOS.index(d["algo"])))
    with open(dst / "fit_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, list(out[0]))
        w.writeheader()
        w.writerows(out)
    clean = fit(0, 256, FIT_PER_MBIT, LIFETIME_H, ACTIVATION)
    one = fit(1, 256, FIT_PER_MBIT, LIFETIME_H, ACTIVATION)
    with open(dst / "fit_constants.txt", "w", newline="\n") as fh:
        fh.write(f"assumptions: {FIT_PER_MBIT:g} FIT/Mbit, lifetime {LIFETIME_H:g} h, activation {ACTIVATION}\n")
        fh.write(f"triple-error outcomes of the (30,24) decoder: {triple_error_outcomes()}\n")
        fh.write(f"256x30 memory, no consumed word: DUE {clean['due']:.3e} FIT, SDC {clean['sdc']:.3e} FIT\n")
        fh.write(f"each consumed word adds: DUE {one['due'] - clean['due']:.5f} FIT, SDC {one['sdc']:.3e} FIT\n")
        fh.write(f"256x24 memory without ECC: SDC {fit_unprotected(256, 24, FIT_PER_MBIT):.3f} FIT\n")
    print(open(dst / "fit_constants.txt").read())
    for mix in sorted({d["mix"] for d in out}):
        for k in ("2", "8"):
            print(f"-- {mix} R=2 S=2 K={k}:  defects algo repair_rate mean_E paired_TRIAD_E FIT_DUE")
            for d in out:
                if (d["mix"], d["R"], d["K"]) == (mix, "2", k) and d["defects"] in ("4", "8", "12"):
                    print(f"   {d['defects']:>2} {d['algo']:13s} {d['repair_rate']} {d['mean_ecc_words']:>7} "
                          f"{d['paired_triad_ecc']:>7} {d['fit_due']}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
