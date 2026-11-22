"""Evaluation protocol report: repair rate, normalised repair rate and yield per defect mix.

    python model/analysis/protocol_report.py build/proto/protocol_*.csv --out build/export/protocol

For every mix and resource setting:
  n90   = defects per memory at which the repair rate falls to 90 % (linear interpolation);
  NRR   = normalised repair rate at n90 of TRIAD = repaired / repaired by the exact plain allocator
          (TRIAD is optimal for unpartitioned steering, so it is the "repairable" reference);
  Y_P   = Poisson yield at a mean of n90(TRIAD) defects;  Y_NB = negative-binomial yield, alpha = 2.
"""
from __future__ import annotations

import argparse
from math import exp, lgamma, log
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ALGOS = ["triad_p16", "triad_p4", "triad_rel", "greedy_joint", "ef_exact_bb", "ef_esp", "exact_2d", "esp_2d"]
LABEL = {"triad_p16": "TRIAD-P, 16 partitions", "triad_p4": "TRIAD-P, 4 partitions", "triad_rel": "TRIAD, exact",
         "greedy_joint": "greedy joint", "ef_exact_bb": "ECC-first exact + buy-back", "ef_esp": "ECC-first ESP (EBISR-like)",
         "exact_2d": "2-D exact, no ECC", "esp_2d": "ESP, no ECC"}
STYLE = {"triad_p16": "C3-", "triad_p4": "C1-", "triad_rel": "k-", "greedy_joint": "C5:", "ef_exact_bb": "C0--",
         "ef_esp": "C6:", "exact_2d": "C2-", "esp_2d": "C4:"}


def rate(g: pd.DataFrame) -> np.ndarray:
    g = g.sort_values("defects")
    n_max = int(g["defects"].max())
    r = np.interp(np.arange(n_max + 1), g["defects"], g["repaired"] / g["trials"])
    r[0] = 1.0
    return r


def n90(r: np.ndarray) -> float:
    below = np.nonzero(r < 0.9)[0]
    if len(below) == 0:
        return float("inf")
    i = int(below[0])
    return i - 1 + (r[i - 1] - 0.9) / (r[i - 1] - r[i])


def weights(lam: float, n_max: int, alpha: float | None) -> np.ndarray:
    n = np.arange(n_max + 1)
    if alpha is None:
        logw = -lam + n * log(lam) - np.array([lgamma(k + 1) for k in n])
    else:  # negative binomial with mean lam and clustering parameter alpha
        p = alpha / (alpha + lam)
        logw = np.array([lgamma(k + alpha) - lgamma(alpha) - lgamma(k + 1) for k in n]) + alpha * log(p) + n * log(1 - p)
    return np.exp(logw)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    df = pd.concat([pd.read_csv(p) for p in args.csv], ignore_index=True)
    rows = []
    for (mix, R, S, K), grp in df.groupby(["mix", "R", "S", "K"]):
        curves = {a: rate(g) for a, g in grp.groupby("algo")}
        ref = curves["triad_rel"]
        lam = n90(ref)
        lam = min(lam, len(ref) / 2.0)
        i = min(int(round(lam)), len(ref) - 1)
        for a in ALGOS:
            r = curves[a]
            rows.append(dict(mix=mix, R=R, S=S, K=K, algo=a, n90=n90(r), rr_at=i, rr=r[i], nrr=r[i] / ref[i] if ref[i] else np.nan,
                             y_poisson=float(weights(lam, len(r) - 1, None) @ r), y_nb2=float(weights(lam, len(r) - 1, 2.0) @ r)))
        if K in (0, 8) and R == 2:
            fig, ax = plt.subplots(figsize=(6.2, 3.8))
            for a in ALGOS:
                ax.plot(np.arange(len(curves[a])), 100 * curves[a], STYLE[a], label=LABEL[a])
            ax.set(xlabel="defects per memory", ylabel="repair rate (%)", title=f"mix '{mix}', R={R}, S={S}, K={K}")
            ax.grid(alpha=0.3)
            ax.legend(fontsize=7)
            fig.tight_layout()
            fig.savefig(args.out / f"protocol_{mix}_R{R}_S{S}_K{K}.png", dpi=130)
            plt.close(fig)
    out = pd.DataFrame(rows)
    out.to_csv(args.out / "protocol_summary.csv", index=False, float_format="%.4f")
    piv = out.pivot_table(index=["mix", "R", "K"], columns="algo", values="n90")[ALGOS]
    pd.set_option("display.width", 220, "display.max_rows", 200)
    print("defects per memory tolerated at a 90 % repair rate (S = 2 spare columns, 10 000 maps per point)")
    print(piv.round(1).to_string())
    print()
    print("normalised repair rate at n90 of TRIAD (1.0 = repairs everything the plain exact allocator can)")
    print(out.pivot_table(index=["mix", "R", "K"], columns="algo", values="nrr")[ALGOS].round(3).to_string())


if __name__ == "__main__":
    main()
