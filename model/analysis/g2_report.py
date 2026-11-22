"""G2 gate: does joint (TRIAD) allocation beat ECC-first schemes?  Reads the Monte Carlo CSVs.

    python model/analysis/g2_report.py build/g2/macro.csv build/g2/large.csv --out build/export/g2

Decision criteria, fixed before the experiment was run:

  (a) yield: Poisson-averaged yield of TRIAD exceeds the strongest ECC-first heuristic
      (ef_exact_bb = exact 2-D analysis of multi-fault words + greedy buy-back) by at least
      1 percentage point at some defect density where the TRIAD yield is between 50 % and 99 %;
  (b) reliability: on the memories both repair, TRIAD leaves at least 10 % fewer ECC-consumed words.

If neither holds, the exact joint search buys little over "ECC first + greedy buy-back" and the
contribution has to rest on the guarantee (bound, exactness, programmable budget) and on PPA.
The comparison with ef_esp (the EBISR recipe) and with 2-D-only repair is reported separately,
because those are the published baselines.
"""
from __future__ import annotations

import argparse
from math import exp
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

KEYS = ["words", "bits", "wpr", "mix", "R", "S", "K"]
LABEL = {
    "triad_rel": "TRIAD (joint, exact)",
    "greedy_joint": "Greedy joint (no backtracking)",
    "ef_exact_bb": "ECC-first exact + buy-back",
    "ef_exact": "ECC-first exact",
    "ef_esp": "ECC-first ESP (EBISR-like)",
    "exact_2d": "2-D exact, no ECC",
    "esp_2d": "ESP, no ECC",
}
STYLE = {"triad_rel": "k-", "greedy_joint": "C5-", "ef_exact_bb": "C0--", "ef_exact": "C1-.", "ef_esp": "C3:", "exact_2d": "C2-", "esp_2d": "C4:"}


def poisson_weights(lam: float, n_max: int) -> np.ndarray:
    w = np.empty(n_max + 1)
    w[0] = exp(-lam)
    for n in range(1, n_max + 1):
        w[n] = w[n - 1] * lam / n
    return w


def per_defect(group: pd.DataFrame, column: str, n_max: int) -> np.ndarray:
    """Value of `column` per trial for n = 0..n_max defects (linear interpolation between samples)."""
    g = group.sort_values("defects")
    return np.interp(np.arange(n_max + 1), g["defects"], g[column] / g["trials"], left=np.nan)


def curves(df: pd.DataFrame) -> pd.DataFrame:
    """Poisson-averaged yield and mean ECC-consumed words for every setting, algorithm and density."""
    out = []
    for key, grp in df.groupby(KEYS):
        n_max = int(grp["defects"].max())
        lams = np.linspace(0.25, n_max / 2.0, 2 * int(n_max / 2.0 / 0.25) // 2)
        for algo, g in grp.groupby("algo"):
            rep = per_defect(g, "repaired", n_max)
            ecc = per_defect(g, "sum_ecc", n_max)
            ecc_t = per_defect(g, "sum_ecc_triad", n_max)
            rep[0], ecc[0], ecc_t[0] = 1.0, 0.0, 0.0  # no defect: good memory, nothing to repair
            rep, ecc, ecc_t = (np.nan_to_num(a, nan=1.0 if a is rep else 0.0) for a in (rep, ecc, ecc_t))
            for lam in lams:
                w = poisson_weights(lam, n_max)
                y = float(w @ rep)
                out.append(dict(zip(KEYS, key), algo=algo, lam=lam, tail=1.0 - float(w.sum()), yield_=y,
                                mean_ecc=float(w @ ecc) / y if y else np.nan,
                                mean_ecc_triad=float(w @ ecc_t) / y if y else np.nan))
    return pd.DataFrame(out)


def gate_table(cv: pd.DataFrame) -> pd.DataFrame:
    rows = []
    piv = cv.pivot_table(index=KEYS + ["lam"], columns="algo", values=["yield_", "mean_ecc", "mean_ecc_triad", "tail"])
    for key, g in piv.groupby(level=KEYS):
        ok = g[(g[("yield_", "triad_rel")] >= 0.5) & (g[("yield_", "triad_rel")] <= 0.99) & (g[("tail", "triad_rel")] < 0.01)]
        if ok.empty:
            continue
        row = dict(zip(KEYS, key))
        ref = (ok[("yield_", "triad_rel")] - 0.90).abs().idxmin()  # density where TRIAD yield is nearest 90 %
        row["lam90"] = ref[-1]
        row["yield90_triad"] = 100 * ok.loc[ref, ("yield_", "triad_rel")]
        for algo in ("greedy_joint", "ef_exact_bb", "ef_exact", "ef_esp", "exact_2d", "esp_2d"):
            gain = ok[("yield_", "triad_rel")] - ok[("yield_", algo)]
            row[f"gain90_pp_{algo}"] = 100 * gain.loc[ref]
            row[f"gainmax_pp_{algo}"] = 100 * gain.max()
            base, ours = ok.loc[ref, ("mean_ecc", algo)], ok.loc[ref, ("mean_ecc_triad", algo)]
            row[f"ecc90_{algo}"] = base
            row[f"ecc90_triad_vs_{algo}"] = ours
            row[f"ecc_cut90_pct_{algo}"] = 100 * (1 - ours / base) if base > 0 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def plot_setting(df: pd.DataFrame, cv: pd.DataFrame, key: tuple, out: Path) -> None:
    sel = dict(zip(KEYS, key))
    d = df[(df[KEYS] == pd.Series(sel)).all(axis=1)]
    c = cv[(cv[KEYS] == pd.Series(sel)).all(axis=1)]
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    for algo in LABEL:
        g = d[d["algo"] == algo].sort_values("defects")
        ax[0].plot(g["defects"], 100 * g["repaired"] / g["trials"], STYLE[algo], label=LABEL[algo])
        h = c[c["algo"] == algo].sort_values("lam")
        ax[1].plot(h["lam"], 100 * h["yield_"], STYLE[algo], label=LABEL[algo])
        if algo.startswith(("triad", "ef_", "greedy")):
            ok = g[g["repaired"] > 0]
            ax[2].plot(ok["defects"], ok["sum_ecc"] / ok["repaired"], STYLE[algo], label=LABEL[algo])
    ax[0].set(xlabel="defects per memory", ylabel="repair rate (%)", title="Repair rate")
    ax[1].set(xlabel="mean defects per memory (Poisson)", ylabel="yield (%)", title="Yield")
    ax[2].set(xlabel="defects per memory", ylabel="ECC-consumed words (mean over repaired)", title="Soft-error exposure")
    for a in ax:
        a.grid(alpha=0.3)
    ax[0].legend(fontsize=8)
    fig.suptitle("{words}x{bits} (mux {wpr}), mix '{mix}', R={R} spare words, S={S} spare columns, K={K}".format(**sel))
    fig.tight_layout()
    fig.savefig(out / "g2_{words}x{bits}_{mix}_R{R}_S{S}_K{K}.png".format(**sel), dpi=130)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    df = pd.concat([pd.read_csv(p) for p in args.csv], ignore_index=True)
    cv = curves(df)
    cv.to_csv(args.out / "g2_yield_curves.csv", index=False, float_format="%.5f")
    gate = gate_table(cv)
    gate.to_csv(args.out / "g2_gate.csv", index=False, float_format="%.3f")
    search = df[df["algo"] == "triad_rel"].groupby(KEYS).agg(max_nodes=("max_nodes", "max"),
                                                              max_kernel_words=("max_kernel_words", "max")).reset_index()
    search["store_bound"] = search["R"] + search["S"] * (search["R"] + search["K"]) + search["K"]
    search.to_csv(args.out / "g2_search_effort.csv", index=False)
    for key in df[KEYS].drop_duplicates().itertuples(index=False):
        if key.K in (8, 16, 32) and key.mix in ("cells", "mixed"):
            plot_setting(df, cv, tuple(key), args.out)
    pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 200)
    cols = KEYS + ["lam90", "yield90_triad"] + [c for c in gate.columns if c.startswith(("gain90", "gainmax", "ecc_cut90"))]
    print(gate[cols].round(2).to_string(index=False))
    print()
    print(search.to_string(index=False))


if __name__ == "__main__":
    main()
