#!/usr/bin/env python3
"""tools/site_chip3d.py <tag> — emit 3-D viewer data for the routed layout.

Run inside WSL from the mirror (the DEF only exists there):

    source tools/env.sh
    python3 tools/site_chip3d.py try15
    bash tools/sync_results.sh

Reads the final DEF plus the PDK tech/cell/macro LEFs and the magic tech file
(layer heights), writes $TRIAD_ROOT/build/export/chip3d/<tag>/ containing:

  index.json            die box, units, layer stack, macro pins, counts, sources, sha256
  comps.i32.gz          little-endian Int32 x,y,w,h,class per placed component
  wire_<layer>.i32.gz   signal-net segment boxes x0,y0,x1,y1 per routing layer
  swire_<layer>.i32.gz  special-net (power) segment boxes, same layout
  via_<cut>.i32.gz      x,y points per cut layer (dropped first if payload is too big)
"""
import gzip
import hashlib
import json
import os
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

TRIAD_ROOT = Path(os.environ.get("TRIAD_ROOT", Path.home() / "work" / "triad_bisr"))
PDK_ROOT = Path(os.environ["PDK_ROOT"])
PDK = os.environ.get("PDK", "sky130A")
SC = os.environ.get("STD_CELL_LIBRARY", "sky130_fd_sc_hd")

ROUTING = ["li1", "met1", "met2", "met3", "met4", "met5"]
# magic-tech height-layer names -> our layer names
HEIGHT_MAP = {
    "allli": "li1", "mcon": "mcon", "allm1": "met1", "allm2": "met2",
    "allm3": "met3", "allm4": "met4", "allm5": "met5",
    "v1": "via", "v2": "via2", "v3": "via3", "v4": "via4",
}
# via-cell name -> cut layer for the fixed names nets use
VIA_CUT = {"L1M1_PR": "mcon", "M1M2_PR": "via", "M2M3_PR": "via2",
           "M3M4_PR": "via3", "M4M5_PR": "via4"}
CLS = {"logic": 0, "ff": 1, "diode": 2, "clk": 3, "fill": 4, "macro": 5}


def cell_class(name: str) -> int:
    n = name.lower()
    if "sram" in n:
        return CLS["macro"]
    if "diode" in n:
        return CLS["diode"]
    if any(k in n for k in ("clkbuf", "clkinv", "clkdlybuf")):
        return CLS["clk"]
    if "df" in n:
        return CLS["ff"]
    if any(k in n for k in ("fill", "decap", "tap")):
        return CLS["fill"]
    return CLS["logic"]


def parse_lef_sizes(path: Path) -> dict:
    """MACRO name -> (w_um, h_um); for the macro LEF also return pins."""
    sizes, pins, macro_name = {}, [], None
    cur = pin = None
    for line in path.read_text(errors="replace").splitlines():
        m = re.match(r"\s*MACRO\s+(\S+)", line)
        if m:
            cur = m.group(1)
            macro_name = cur
            continue
        m = re.match(r"\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", line)
        if m and cur:
            sizes[cur] = (float(m.group(1)), float(m.group(2)))
            continue
        m = re.match(r"\s*PIN\s+(\S+)", line)
        if m:
            pin = {"name": m.group(1), "layer": None, "rects": []}
            pins.append(pin)
            continue
        if pin is not None:
            m = re.search(r"LAYER\s+(\S+)", line)
            if m and pin["layer"] is None:
                pin["layer"] = m.group(1)
            m = re.search(r"RECT\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)", line)
            if m:
                pin["rects"].append([float(m.group(i)) for i in range(1, 5)])
            if re.match(r"\s*END\s+" + re.escape(pin["name"]), line):
                pin = None
    return sizes, pins, macro_name


def parse_techlef_widths(path: Path) -> tuple[dict, dict]:
    """routing/cut LAYER blocks: name -> {type, width_um, thickness_um}."""
    layers, cur = {}, None
    for line in path.read_text(errors="replace").splitlines():
        m = re.match(r"\s*LAYER\s+(\w+)", line)
        if m:
            cur = m.group(1)
            layers.setdefault(cur, {})
            continue
        if cur:
            m = re.match(r"\s*TYPE\s+(\w+)", line)
            if m:
                layers[cur]["type"] = m.group(1)
                continue
            m = re.match(r"\s*WIDTH\s+([\d.]+)", line)
            if m:
                layers[cur].setdefault("width_um", float(m.group(1)))
                continue
            m = re.match(r"\s*THICKNESS\s+([\d.]+)", line)
            if m:
                layers[cur]["thickness_um"] = float(m.group(1))
                continue
            if re.match(r"\s*END\s+" + re.escape(cur), line):
                cur = None
    return layers


def parse_magic_heights(path: Path) -> dict:
    """'height <layer> <base> <thickness>' lines -> {layer: (base_um, thickness_um)}."""
    out = {}
    for line in path.read_text(errors="replace").splitlines():
        m = re.match(r"\s*height\s+(\S+)\s+(-?[\d.]+)\s+(-?[\d.]+)", line)
        if m and m.group(1) in HEIGHT_MAP:
            out[HEIGHT_MAP[m.group(1)]] = (float(m.group(2)), float(m.group(3)))
    return out


def parse_def_vias(text: str) -> dict:
    """DEF VIAS section: via name -> middle (cut) layer."""
    out = {}
    m = re.search(r"^VIAS .*?^END VIAS", text, re.M | re.S)
    if m:
        for vm in re.finditer(r"-\s+(\S+).*?\+ LAYERS\s+(\w+)\s+(\w+)\s+(\w+)", m.group(0)):
            out[vm.group(1)] = vm.group(3)
    return out


POINT = re.compile(r"\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s*\)")
# start of a wire fragment: "+ ROUTED <layer> [width]" or "NEW <layer> [width]"
WIRE_START = re.compile(r"(?:\+\s*ROUTED|(?<![\w])NEW)\s+(\w+)\s*(?:(\d+)\s*)?")
# token inside a wire body: point, "+ KEYWORD value", or bare word (via name)
TOK = re.compile(r"\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s*\)|\+\s*(\w+)|([A-Za-z_][\w.\[\]/]*)|(\d+)")


def parse_wires(text: str, via_map: dict, defw: dict, units: int):
    """Parse all wire fragments in one NET body; returns segment boxes and via points."""
    wires: dict = defaultdict(list)   # layer -> (x0,y0,x1,y1) boxes, dbu
    vias: dict = defaultdict(list)    # cut layer -> (x,y), dbu
    last = [0, 0]                     # '*' inherits the previous point across the whole net
    starts = list(WIRE_START.finditer(text))
    for i, m in enumerate(starts):
        layer, width_tok = m.group(1), m.group(2)
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        body = text[m.end():end]
        if layer not in ROUTING:
            continue
        w_dbu = int(width_tok) if width_tok else int(round(defw.get(layer, 0.0) * units))
        pts = []
        skip_val = False
        for tm in TOK.finditer(body):
            if tm.group(3):                       # "+ KEYWORD": skip its single argument
                skip_val = True
                continue
            if tm.group(1) is not None:           # point
                if tm.group(1) != "*":
                    last[0] = int(tm.group(1))
                if tm.group(2) != "*":
                    last[1] = int(tm.group(2))
                pts.append((last[0], last[1]))
                continue
            word = tm.group(4) or tm.group(5)
            if word is None:
                continue
            if skip_val:                          # the keyword's argument — not a via name
                skip_val = False
                continue
            cut = via_map.get(word)               # bare word after a point = via cell
            if cut and pts:
                vias[cut].append(pts[-1])
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            x0, x1 = min(ax, bx), max(ax, bx)
            y0, y1 = min(ay, by), max(ay, by)
            hw = w_dbu // 2
            if x0 == x1:
                x0, x1 = x0 - hw, x1 + hw
            else:
                y0, y1 = y0 - hw, y1 + hw
            wires[layer].append((x0, y0, x1, y1))
    return wires, vias


def i32gz(path: Path, ints) -> int:
    data = struct.pack(f"<{len(ints)}i", *ints)
    path.write_bytes(gzip.compress(data, compresslevel=9))
    return path.stat().st_size


def main() -> None:
    tag = sys.argv[1] if len(sys.argv) > 1 else "try15"
    def_path = TRIAD_ROOT / "flow" / "openlane" / "triad_bisr_top" / "runs" / tag \
        / "results" / "final" / "def" / "triad_bisr_top.def"
    libdir = PDK_ROOT / PDK / "libs.ref"
    techlef = libdir / SC / "techlef" / f"{SC}__nom.tlef"
    cell_lefs = [libdir / SC / "lef" / f"{SC}.lef", libdir / SC / "lef" / "sky130_ef_sc_hd.lef"]
    macro_lef = libdir / "sky130_sram_macros" / "lef" / "sky130_sram_1kbyte_1rw1r_32x256_8.lef"
    magic_tech = PDK_ROOT / PDK / "libs.tech" / "magic" / f"{PDK}.tech"
    for p in [def_path, techlef, *cell_lefs, macro_lef, magic_tech]:
        if not p.is_file():
            raise SystemExit(f"chip3d: missing {p}")

    sizes, _, _ = {}, [], None
    cell_sizes = {}
    pin_data, macro_name = [], None
    for lf in cell_lefs:
        s, _, _ = parse_lef_sizes(lf)
        cell_sizes.update(s)
    msize, pin_data, macro_name = parse_lef_sizes(macro_lef)
    cell_sizes.update(msize)

    tlayers = parse_techlef_widths(techlef)
    defw_um = {l: tlayers.get(l, {}).get("width_um", 0.0) for l in ROUTING}
    heights = parse_magic_heights(magic_tech)
    missing = [l for l in ["li1", "mcon", "met1", "via", "met2", "via2", "met3", "via3",
                           "met4", "via4", "met5"] if l not in heights]
    if missing:
        raise SystemExit(f"chip3d: no height for {missing} in {magic_tech}")
    cell_heights = Counter(h for _, h in cell_sizes.values())
    cell_h_um = cell_heights.most_common(1)[0][0]

    text = def_path.read_text(errors="replace")
    units = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", text).group(1))
    die = [int(v) for v in re.search(r"DIEAREA \( (\d+) (\d+) \) \( (\d+) (\d+) \)", text).groups()]
    via_map = dict(VIA_CUT)
    via_map.update(parse_def_vias(text))

    # components (single-line entries)
    comps: list[int] = []
    counts = Counter()
    macro_origin = None
    comp_sec = re.search(r"^COMPONENTS .*?^END COMPONENTS", text, re.M | re.S).group(0)
    cre = re.compile(r"-\s+(\S+)\s+(\S+).*?\+\s*(?:PLACED|FIXED|COVER|UNPLACED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)")
    for m in cre.finditer(comp_sec):
        inst, cell, x, y = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        cls = cell_class(cell)
        w_um, h_um = cell_sizes.get(cell, (0.0, cell_h_um))
        w, h = int(round(w_um * units)), int(round(h_um * units))
        comps += [x, y, w, h, cls]
        counts[f"comp_{cls}"] += 1
        if cls == CLS["macro"] and macro_origin is None:
            macro_origin = (x, y)

    # nets + special nets
    segmap, swiremap = defaultdict(list), defaultdict(list)
    vpoint = defaultdict(list)
    for sec_name, dest in (("NETS", segmap), ("SPECIALNETS", swiremap)):
        sec = re.search(rf"^{sec_name} .*?^END {sec_name}", text, re.M | re.S)
        if not sec:
            continue
        for nm in re.finditer(r"-\s+\S+.*?(?=\n\s*-|\Z)", sec.group(0), re.S):
            w, v = parse_wires(nm.group(0), via_map, defw_um, units)
            for l, segs in w.items():
                dest[l] += segs
            for l, ps in v.items():
                vpoint[l] += ps

    out = TRIAD_ROOT / "build" / "export" / "chip3d" / tag
    out.mkdir(parents=True, exist_ok=True)
    files = []
    files.append({"name": "comps.i32.gz", "bytes": i32gz(out / "comps.i32.gz", comps)})
    for l in ROUTING:
        ints = [v for seg in segmap[l] for v in seg]
        files.append({"name": f"wire_{l}.i32.gz", "bytes": i32gz(out / f"wire_{l}.i32.gz", ints)})
        counts[f"wires_{l}"] = len(segmap[l])
    for l in ROUTING:
        ints = [v for seg in swiremap[l] for v in seg]
        if ints:
            files.append({"name": f"swire_{l}.i32.gz", "bytes": i32gz(out / f"swire_{l}.i32.gz", ints)})
        counts[f"swires_{l}"] = len(swiremap[l])
    total = sum(f["bytes"] for f in files)
    if total <= 12 * 1024 * 1024:
        for cut, ps in vpoint.items():
            if ps:
                ints = [v for p in ps for v in p]
                files.append({"name": f"via_{cut}.i32.gz", "bytes": i32gz(out / f"via_{cut}.i32.gz", ints)})
                counts[f"vias_{cut}"] = len(ps)

    index = {
        "tag": tag,
        "def_sha256": hashlib.sha256(def_path.read_bytes()).hexdigest(),
        "units_per_um": units,
        "die_area_dbu": die,
        "sources": {
            "def": str(def_path),
            "techlef": str(techlef),
            "cell_lefs": [str(p) for p in cell_lefs],
            "macro_lef": str(macro_lef),
            "stack_source": f"{magic_tech} (height section)",
        },
        "stack": {l: {"base_um": b, "thickness_um": t}
                  for l, (b, t) in heights.items() if l in
                  ["li1", "mcon", "met1", "via", "met2", "via2", "met3", "via3", "met4", "via4", "met5"]},
        "default_widths_um": defw_um,
        "cell_height_um": cell_h_um,
        "macro": {
            "name": macro_name,
            "origin_dbu": list(macro_origin) if macro_origin else None,
            "size_um": list(msize[macro_name]) if macro_name in msize else None,
            "pins": pin_data,
        },
        "counts": dict(counts),
        "files": files,
    }
    (out / "index.json").write_text(json.dumps(index, indent=1))
    print(f"chip3d: wrote {out} ({len(files)} payload files)")
    for f in files:
        print(f"  {f['name']:24s} {f['bytes']:>9,d} B")
    print(f"  payload total              {total:,} B")
    print(f"  stack source               {magic_tech}")
    for l in ["li1", "met1", "met2", "met3", "met4", "met5"]:
        print(f"    {l:5s} base {heights[l][0]:8.4f} um  thick {heights[l][1]:.3f} um")


if __name__ == "__main__":
    main()
