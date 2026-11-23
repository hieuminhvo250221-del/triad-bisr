#!/usr/bin/env python3
"""tools/site_data.py — build the JSON files the website reads from the numbers in results/.

Nothing on the site may be typed by hand: every figure comes through site/src/data/generated/*.json.
A missing *required* key or file fails with a clear message; a missing *optional* input yields
{"available": false} so the section can render a "pending" note instead.

    python tools/site_data.py            # write site/src/data/generated/*.json
    python tools/site_data.py --check    # print the try15 values for eyeballing, write nothing
"""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
OUT = ROOT / "site" / "src" / "data" / "generated"

ASIC_KEYS = [
    "DIEAREA_mm^2", "CoreArea_um^2", "synth_cell_count", "tritonRoute_violations",
    "Magic_violations", "lvs_total_errors", "pin_antenna_violations", "wire_length",
    "vias", "suggested_clock_period", "suggested_clock_frequency", "OpenDP_Util",
    "critical_path_ns",
]
DEFECT_RANGE = range(1, 31)


def die(msg: str) -> "NoReturn":
    raise SystemExit(f"site_data: {msg}")


def num(s: str):
    s = s.strip()
    if s in ("", "-1", "-"):
        return None if s == "" else s
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        die(f"missing required file {path.relative_to(ROOT)}")
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def need(path: Path, what: str) -> Path:
    if not path.is_file():
        die(f"missing required {what}: {path.relative_to(ROOT)}")
    return path


def asic_json() -> dict:
    cur = need(RESULTS / "asic" / "CURRENT", "asic/CURRENT tag file")
    tag = cur.read_text().strip()
    if not tag:
        die("results/asic/CURRENT is empty")
    d = RESULTS / "asic" / tag
    if not d.is_dir():
        die(f"results/asic/CURRENT names {tag!r} but {d.relative_to(ROOT)} does not exist")

    rows = read_csv(need(d / "metrics.csv", f"metrics.csv for {tag}"))
    metrics = rows[0]
    out: dict = {"tag": tag}
    for k in ASIC_KEYS:
        if k not in metrics:
            die(f"metrics.csv for {tag} has no column {k!r}")
        out[k] = num(metrics[k])

    drc = need(d / "drc_blackbox.rpt", f"drc_blackbox.rpt for {tag}").read_text()
    m = re.search(r"total:\s*(\d+)", drc)
    if not m:
        die(f"no 'total: N' line in {d.relative_to(ROOT)}/drc_blackbox.rpt")
    out["drc_gds_total"] = int(m.group(1))

    power = need(d / "rcx_sta.power.rpt", f"rcx_sta.power.rpt for {tag}").read_text()
    m = re.search(r"^Total\s+((?:\S+\s+){3}\S+)\s+\S+%\s*$", power, re.M)
    if not m:
        die(f"no Total row in {d.relative_to(ROOT)}/rcx_sta.power.rpt")
    out["power_total_w"] = float(m.group(1).split()[-1])

    out["sta_checks"] = [
        {k: (num(v) if v != "" else None) for k, v in r.items()}
        for r in read_csv(need(d / "sta_checks_summary.csv", f"sta_checks_summary.csv for {tag}"))
    ]
    out["timing_corners"] = [
        {"corner": r["corner"], "setup_slack_ns": float(r["setup_slack_ns"]),
         "hold_slack_ns": float(r["hold_slack_ns"])}
        for r in read_csv(need(d / "timing_corners.csv", f"timing_corners.csv for {tag}"))
    ]
    out["gds_sha256"] = need(d / "gds.sha256", f"gds.sha256 for {tag}").read_text().split()[0]
    return out


def verification_json() -> dict:
    p = need(RESULTS / "verification" / "summary.yaml", "verification summary")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "gates" not in data:
        die("results/verification/summary.yaml has no 'gates' list")
    return data


def ppa_json() -> dict:
    rows = read_csv(RESULTS / "ppa" / "synth_sweep.csv")
    for col in ("pbits", "r", "area_um2", "cells", "ffs"):
        for r in rows:
            if r.get(col) in (None, ""):
                die(f"results/ppa/synth_sweep.csv: missing {col}")
            r[col] = int(r[col])
    return {"rows": rows}


def protocol_json() -> dict:
    raw_dir = RESULTS / "protocol" / "raw"
    if not raw_dir.is_dir():
        die("results/protocol/raw/ is missing — copy the Monte Carlo CSVs there first")
    series: dict[str, dict] = {}
    for f in sorted(raw_dir.glob("protocol_*.csv")):
        for r in read_csv(f):
            key = f"{r['mix']},{r['R']},{r['S']},{r['K']},{r['algo']}"
            s = series.setdefault(key, {"trials": int(r["trials"]), "rate": {}})
            s["rate"][int(r["defects"])] = round(int(r["repaired"]) / int(r["trials"]), 6)
    for key, s in series.items():
        missing = [d for d in DEFECT_RANGE if d not in s["rate"]]
        if missing:
            die(f"protocol series {key}: no rate for defects {missing[:5]}…")
    summary = [
        {k: num(v) for k, v in r.items()}
        for r in read_csv(RESULTS / "protocol" / "protocol_summary.csv")
    ]
    return {"defect_range": list(DEFECT_RANGE), "series": series, "summary": summary}


def reliability_json() -> dict:
    rows = [
        {k: num(v) for k, v in r.items()}
        for r in read_csv(RESULTS / "reliability" / "fit_summary.csv")
    ]
    txt = need(RESULTS / "reliability" / "fit_constants.txt", "fit_constants.txt")
    lines = txt.read_text(encoding="utf-8").splitlines()
    const = {"assumptions": None, "memory_due_fit": None,
             "per_word_due_fit": None, "no_ecc_sdc_fit": None}
    for line in lines:
        if line.startswith("assumptions:"):
            const["assumptions"] = line.split(":", 1)[1].strip()
        m = re.search(r"no consumed word: DUE ([\deE.+-]+) FIT", line)
        if m:
            const["memory_due_fit"] = float(m.group(1))
        m = re.search(r"each consumed word adds: DUE ([\deE.+-]+) FIT", line)
        if m:
            const["per_word_due_fit"] = float(m.group(1))
        m = re.search(r"without ECC: SDC ([\deE.+-]+) FIT", line)
        if m:
            const["no_ecc_sdc_fit"] = float(m.group(1))
    missing = [k for k, v in const.items() if v is None]
    if missing:
        die(f"fit_constants.txt: could not parse {missing}")
    return {"rows": rows, "constants": lines, "fit_constants": const}


def automb_json() -> dict:
    p = RESULTS / "automb" / "automb_compare.csv"
    if not p.is_file():
        return {"available": False}
    rows = read_csv(p)
    per: dict[str, dict] = {}
    for r in rows:
        key = f"{r['mix']},{r['defects']}"
        cell = per.setdefault(key, {"trials": int(r["trials"])})
        for col, v in r.items():
            if col in ("mix", "defects", "trials"):
                continue
            try:
                cell[col] = round(float(v) / int(r["trials"]), 6)
            except (ValueError, ZeroDivisionError):
                cell[col] = v
    return {"available": True, "rows": per}


def n90_interp(rate: dict[int, float], max_n: int):
    """First sampled n where rate < 0.9, linearly interpolated; '> max' if never below.

    rate(0) is defined as 1.0. Returns a float, or a string "> n" when the rate
    never drops below 0.9 over the sampled range.
    """
    prev_n, prev_r = 0, 1.0
    for n in sorted(rate):
        r = rate[n]
        if r < 0.9:
            if n == prev_n:
                return float(n)
            # interpolate between (prev_n, prev_r) and (n, r)
            t = (0.9 - prev_r) / (r - prev_r)
            return prev_n + t * (n - prev_n)
        prev_n, prev_r = n, r
    return f"> {max_n}"


def protocol_large_json() -> dict:
    d = RESULTS / "protocol_large"
    files = sorted(d.glob("protocol_large_*.csv")) if d.is_dir() else []
    if not files:
        return {"available": False}
    # series key: R,S,K,algo -> trials + defects -> repaired/trials
    series: dict[str, dict] = {}
    for f in files:
        for r in read_csv(f):
            key = f"{r['R']},{r['S']},{r['K']},{r['algo']}"
            s = series.setdefault(key, {"trials": int(r["trials"]), "rate": {}})
            s["rate"][int(r["defects"])] = int(r["repaired"]) / int(r["trials"])
    for key, s in series.items():
        s["n90"] = n90_interp(s["rate"], max(s["rate"]))
        s["rate"] = {str(k): v for k, v in s["rate"].items()}
    return {"available": True, "series": series}


def chip3d_json() -> dict:
    cur = need(RESULTS / "asic" / "CURRENT", "asic/CURRENT tag file")
    tag = cur.read_text().strip()
    src = RESULTS / "chip3d" / tag
    idx = src / "index.json"
    if not idx.is_file():
        return {"available": False}
    meta = json.loads(idx.read_text())
    dst = ROOT / "site" / "public" / "chip3d" / tag
    dst.mkdir(parents=True, exist_ok=True)
    payload = 0
    for f in src.iterdir():
        shutil.copy2(f, dst / f.name)
        payload += f.stat().st_size
    return {"available": True, "tag": tag, "payload_bytes": payload,
            "segments": sum(v for k, v in meta.get("counts", {}).items()
                            if k.startswith(("wires_", "swires_")))}


def static_json() -> dict:
    p = ROOT / "site" / "src" / "content" / "tables" / "static.yaml"
    if not p.is_file():
        return {"available": False}
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        die("tables/static.yaml is not a mapping")
    cmds = data.get("commands", [])
    tables = {k: v for k, v in data.items() if k != "commands"}
    return {"available": True, "tables": tables, "commands": cmds}


def main() -> None:
    gen = {
        "asic": asic_json,
        "verification": verification_json,
        "ppa": ppa_json,
        "protocol": protocol_json,
        "reliability": reliability_json,
        "automb": automb_json,
        "protocol_large": protocol_large_json,
        "chip3d": chip3d_json,
        "static": static_json,
    }
    if "--check" in sys.argv:
        a = gen["asic"]()
        print("asic:", json.dumps(a, indent=1))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    # the stepper traces come from the golden model in a subprocess (needs PYTHONPATH=model)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "model")
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "site_traces.py")],
        env=env, capture_output=True, text=True,
    )
    sys.stdout.write(r.stdout)
    if r.returncode:
        sys.stderr.write(r.stderr)
        die("site_traces.py failed")
    for name, fn in gen.items():
        data = fn()
        (OUT / f"{name}.json").write_text(json.dumps(data, indent=1) + "\n")
        print(f"wrote {OUT.relative_to(ROOT)}/{name}.json")
    # site assets that come from the data (layout render of the current tag)
    assets = ROOT / "site" / "public" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    png = RESULTS / "asic" / gen["asic"]()["tag"] / "layout.png"
    if png.is_file():
        shutil.copy2(png, assets / "layout.png")
        print(f"copied {png.relative_to(ROOT)} -> site/public/assets/layout.png")


if __name__ == "__main__":
    main()
