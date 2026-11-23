"""Build slides/triad_bisr.pptx — 16:9, 16 slides. All numbers copied from paper/triad.tex.

Run with python-pptx installed, from anywhere: paths are resolved relative to
this file's location (slides/), i.e. the repo root is its parent.
"""
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_CONNECTOR
from pptx.oxml.ns import qn
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "triad_bisr.pptx"

# ---- palette / type ----
BG = RGBColor(0xFB, 0xFA, 0xF6)
INK = RGBColor(0x18, 0x18, 0x1A)
MUTED = RGBColor(0x5C, 0x5B, 0x57)
LINE = RGBColor(0xDE, 0xDB, 0xD1)
ACCENT = RGBColor(0x0F, 0x5C, 0x5A)
WARN = RGBColor(0x9A, 0x5B, 0x13)  # used only for the open sign-off items

TITLE_F, BODY_F, MONO_F = "Georgia", "Calibri", "Consolas"
SW, SH = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.6)

prs = Presentation()
prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]


def _noline(shape):
    shape.line.fill.background()


def line(shapes, x, y, w, color=LINE, weight=Pt(0.75)):
    c = shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x, y, x + w, y)
    c.line.color.rgb = color
    c.line.width = weight
    return c


def text(slide, x, y, w, h, runs, size=19, font=BODY_F, color=INK,
         align=PP_ALIGN.LEFT, space_after=Pt(8), anchor=MSO_ANCHOR.TOP,
         bold=False, wrap=True):
    """runs: list of paragraphs; each paragraph is a str or list of
    (str, dict) run tuples where dict may set font/size/color/bold."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = space_after
        if isinstance(para, str):
            para = [(para, {})]
        for s, st in para:
            r = p.add_run()
            r.text = s
            f = r.font
            f.size = Pt(st.get("size", size))
            f.name = st.get("font", font)
            f.color.rgb = st.get("color", color)
            f.bold = st.get("bold", bold)
    return tb


def new_slide(title, num):
    slide = prs.slides.add_slide(BLANK)
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = BG
    if title:
        text(slide, MARGIN, Inches(0.42), SW - 2 * MARGIN, Inches(0.55),
             [title], font=TITLE_F, size=30)
        line(slide.shapes, MARGIN, Inches(1.12), SW - 2 * MARGIN)
    # footer
    text(slide, MARGIN, SH - Inches(0.34), Inches(2), Inches(0.25),
         ["TRIAD-BISR"], size=10, color=MUTED, font=MONO_F, space_after=Pt(0))
    text(slide, SW - MARGIN - Inches(1), SH - Inches(0.34), Inches(1), Inches(0.25),
         [str(num)], size=10, color=MUTED, font=MONO_F, align=PP_ALIGN.RIGHT,
         space_after=Pt(0))
    return slide


def notes(slide, s):
    slide.notes_slide.notes_text_frame.text = s


def bullets(slide, x, y, w, items, size=19, h=Inches(4.5)):
    """items: str | (str, style) where style in {'muted','accent','mono','small','ind'}"""
    paras = []
    for it in items:
        s, st = (it, "") if isinstance(it, str) else it
        d = {"size": size}
        if "muted" in st:
            d["color"] = MUTED
        if "accent" in st:
            d["color"] = ACCENT
            d["bold"] = True
        if "warn" in st:
            d["color"] = WARN
        if "mono" in st:
            d["font"] = MONO_F
            d["size"] = size - 1
        if "small" in st:
            d["size"] = size - 3
        paras.append([(s, d)])
    return text(slide, x, y, w, h, paras)


def table(slide, x, y, widths, header, rows, aligns=None, row_h=Inches(0.34),
          size=14, head_size=12, mono_cols=()):
    """Booktabs-style table: hairline rules only, muted bold header,
    numeric columns right-aligned. widths in inches."""
    total_w = sum(widths)
    aligns = aligns or [PP_ALIGN.LEFT] * len(widths)
    n = len(rows) + 1
    # rules: top, under header, bottom
    line(slide.shapes, x, y, Inches(total_w))
    line(slide.shapes, x, y + row_h, Inches(total_w))
    line(slide.shapes, x, y + row_h * n, Inches(total_w))
    for ri, row in enumerate([header, *rows]):
        cx = x
        is_head = ri == 0
        for ci, cell in enumerate(row):
            st = {
                "size": head_size if is_head else size,
                "color": MUTED if is_head else INK,
                "bold": is_head,
            }
            if ci in mono_cols and not is_head:
                st["font"] = MONO_F
                st["size"] = size - 1
            # warn/accent cell marking via tuple (text, color)
            if isinstance(cell, tuple):
                cell, cname = cell
                if cname == "accent":
                    st["color"] = ACCENT
                elif cname == "warn":
                    st["color"] = WARN
            text(slide, cx + Inches(0.04), y + row_h * ri + Inches(0.045),
                 Inches(widths[ci]) - Inches(0.08), row_h - Inches(0.06),
                 [[(cell, st)]], align=aligns[ci], space_after=Pt(0),
                 anchor=MSO_ANCHOR.TOP, wrap=False)
            cx += Inches(widths[ci])
    return y + row_h * n


def pic(slide, path, x, y, max_w, max_h):
    """Add picture fit inside the box, aspect preserved; returns the shape."""
    with Image.open(path) as im:
        ar = im.width / im.height
    w, h = max_w, int(max_w / ar)
    if h > max_h:
        h, w = max_h, int(max_h * ar)
    px = x + int((max_w - w) / 2)
    py = y + int((max_h - h) / 2)
    return slide.shapes.add_picture(str(path), px, py, w, h)


ASSETS = Path(__file__).resolve().parent / "assets"
PROTO = ROOT / "results" / "protocol" / "protocol_mixed_R2_S2_K8.png"
LAYOUT = ROOT / "results" / "asic" / "try15" / "layout.png"
BODY_TOP = Inches(1.45)
CONTENT_W = SW - 2 * MARGIN

# ============================ 1: title ============================
s = new_slide(None, 1)
line(s.shapes, MARGIN, Inches(2.05), CONTENT_W)
text(s, MARGIN, Inches(2.25), CONTENT_W, Inches(0.8),
     [[("TRIAD-BISR", {"font": TITLE_F, "size": 30, "bold": True})]])
text(s, MARGIN, Inches(2.95), CONTENT_W, Inches(0.5),
     ["Self-test and self-repair for an embedded SRAM with a budgeted use of ECC"],
     size=21)
text(s, MARGIN, Inches(3.5), CONTENT_W, Inches(0.4),
     ["SkyWater sky130 · OpenRAM macro · open-source RTL to GDS"], size=16, color=MUTED)
text(s, MARGIN, Inches(4.6), CONTENT_W, Inches(0.35),
     ["Author names to be added"], size=15, color=MUTED)
text(s, MARGIN, Inches(5.0), CONTENT_W, Inches(0.6),
     [[("github.com/hieuminhvo250221-del/triad-bisr", {"font": MONO_F, "size": 13})],
      [("hieuminhvo250221-del.github.io/triad-bisr", {"font": MONO_F, "size": 13})]])
notes(s, "The work is a self-test and self-repair wrapper for an embedded SRAM that treats "
      "spare words, spare columns and ECC as one allocation problem with a cap on ECC use. "
      "It is implemented around an unmodified OpenRAM macro in SkyWater 130 nm and taken "
      "from RTL to GDS with open-source tools. Author details are placeholders.")

# ============================ 2: the problem ============================
s = new_slide("The problem", 2)
bullets(s, MARGIN, BODY_TOP, CONTENT_W, [
    "Embedded memories are repaired with spare rows and columns; many also carry SEC-DED ECC for soft errors.",
    "Letting ECC absorb a hard fault raises yield — but that word has no protection left.",
    ("How should spares and ECC be allocated together, on chip, with a cap on ECC use?", "accent"),
], size=21)
notes(s, "MBIST finds the faulty cells, BIRA chooses the spares, BISR applies the choice, and "
      "choosing rows and columns is already NP-complete. SEC-DED ECC can also hide a hard fault, "
      "but a word that spends its correction on a hard fault has none left for a soft error. "
      "The question is how to allocate spares and ECC jointly, on the chip itself, under a cap "
      "on how many words may rely on ECC.")

# ============================ 3: what exists ============================
s = new_slide("What exists, what is added", 3)
table(s, MARGIN, BODY_TOP + Inches(0.1), [3.6, 4.6, 3.9],
      ["Approach", "Prior work", "This work"],
      [
       ["ECC + spares analysis", "Lv 2021, Han 2021: on the tester", "exact, on chip, budget K"],
       ["On-chip ECC repair", "EBISR 2016, Sun 2011: ECC first", "joint allocation"],
       ["Partitioned column steering", "Rab, Bawa, Touba 2009: in the array, fuses", "soft table in the wrapper"],
       ["Wrapper repair of spare-less macros", "commercial tools, autoMBIST", "not claimed; used as setting and baseline"],
      ],
      row_h=Inches(0.62), size=15, head_size=13)
text(s, MARGIN, Inches(6.0), CONTENT_W, Inches(0.35),
     ["Based on the surveyed literature; some full texts were not available."],
     size=13, color=MUTED)
notes(s, "Neither ECC repair nor spare allocation is new and we claim neither: the novel part is "
      "the combination, implemented and measured. Lv and Han analyse ECC plus spares on the tester; "
      "EBISR and Sun apply ECC first on chip; Rab, Bawa and Touba steer columns per partition "
      "inside the array with fuses, while we keep a soft table in the wrapper. The full texts of "
      "three cited works were not available, so we do not claim no earlier work overlaps.")

# ============================ 4: formulation ============================
s = new_slide("Formulation", 4)
bullets(s, MARGIN, BODY_TOP, CONTENT_W, [
    "Fault map: words × bit columns; (w, c) marks a faulty bit.",
    "Choose at most R words to replace and at most S columns to steer.",
    "Every other word may keep at most one faulty bit — SEC-DED absorbs it.",
    ("At most K words may keep exactly one — the ECC budget.", "accent"),
    "K = 0 is classical spare allocation.",
], size=20)
notes(s, "A repair is a set of at most R replaced words and at most S replaced columns such that "
      "every remaining word has at most one faulty bit — the single error SEC-DED can absorb — "
      "and at most K words rely on that correction. With K = 0 this reduces to the classical "
      "constrained bipartite vertex cover of spare allocation. K is programmable, so the designer "
      "chooses how much soft-error margin repair may spend.")

# ============================ 5: what can be proved ============================
s = new_slide("What can be proved", 5)
bullets(s, MARGIN, BODY_TOP, CONTENT_W, [
    "NP-complete for every fixed K.",
    "Must-repair rules: a column with more than R′ + K faulty words; a word with more than S′ + ε bits.",
    "Fault-store bound R + S(R + K) + K faulty words — attained.",
    "Exact by enumeration for fixed S: 466 column sets at W = 30, S = 2.",
    "Partitions decouple: a dynamic programme over partitions is exact.",
], size=19)
text(s, MARGIN, Inches(6.4), CONTENT_W, Inches(0.35),
     ["Checked against exhaustive search; proofs not yet independently reviewed."],
     size=13, color=MUTED)
notes(s, "The problem stays NP-complete for every fixed K, so ECC does not make allocation easy. "
      "Must-repair rules cut the instance, after which a repairable one holds at most "
      "R + S(R + K) + K faulty words, and the bound is attained. For fixed S enumeration is "
      "polynomial — 466 column sets for 30 bits and S = 2 — and since partitions share neither "
      "words nor column choices, a dynamic programme over partitions is exact. All statements are "
      "exercised by tests against exhaustive search; the proofs are not independently reviewed.")

# ============================ 6: architecture ============================
s = new_slide("Architecture", 6)
pic(s, ASSETS / "arch.png", MARGIN, BODY_TOP, CONTENT_W, Inches(4.6))
text(s, MARGIN, Inches(6.35), CONTENT_W, Inches(0.4),
     ["Self-test and self-repair wrapper around the macro; the macro is unmodified."],
     size=14, color=MUTED)
notes(s, "The memory is the OpenRAM macro sky130_sram_1kbyte_1rw1r_32x256_8, used unchanged: bits "
      "0–29 hold a Hsiao (30,24) codeword and bits 30–31 are the two spare columns. The two spare "
      "words are flip-flop registers in the wrapper. A steering table per partition names which "
      "code bit each spare column replaces; steering table, spare words and the 210-bit signature "
      "chain are registers of the datapath.")

# ============================ 7: three passes ============================
s = new_slide("Three passes", 7)
bullets(s, MARGIN, BODY_TOP, Inches(6.4), [
    ("Analyse", "accent"),
    "March C- per partition, six data backgrounds; build the fault bitmap; try column pairs; update the dynamic programme.",
    ("Allocate", "accent"),
    "Program the steering table and the spare-word registers.",
    ("Verify", "accent"),
    "March C- on the whole memory through the repaired datapath.",
], size=18)
pic(s, ASSETS / "stepper.png", MARGIN + Inches(6.8), BODY_TOP, SW - MARGIN - (MARGIN + Inches(6.8)), Inches(5.4))
notes(s, "In the first pass March C- runs per partition on the raw 32 bits, the enumerator tries "
      "the column pairs among columns that have faults, and the dynamic programme is updated. The "
      "second pass revisits the partitions, programs the steering table and assigns spare words. "
      "The third pass runs March C- on the whole memory through the repaired datapath; a mismatch "
      "or an uncorrectable error fails the repair. The picture shows the interactive walkthrough "
      "on the project site.")

# ============================ 8: why partitions ============================
s = new_slide("Why partitions", 8)
bullets(s, MARGIN, BODY_TOP, CONTENT_W, [
    "Each spare column replaces a different bit in each of 16 address partitions.",
    "The fault store is one partition's bitmap, so more partitions make the logic smaller.",
], size=19)
table(s, MARGIN, Inches(3.3), [3.2, 3.0],
      ["Partitions", "Wrapper cell area (µm²)"],
      [["2", "477 367"], ["4", "252 252"], ["8", "143 429"],
       [("16", "accent"), ("94 427", "accent")]],
      aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT], row_h=Inches(0.42),
      size=16, head_size=13, mono_cols=(1,))
text(s, MARGIN, Inches(5.6), CONTENT_W, Inches(0.35),
     ["The cost is test time — each partition is marched separately."], size=15, color=MUTED)
notes(s, "Steering lets each spare column stand in for a different code bit in each of the sixteen "
      "partitions, and the fault store only has to cover one partition's bitmap, so the analyser "
      "shrinks as partitions increase: 477 367 µm² of cells at two partitions down to 94 427 at "
      "sixteen. The price is test time, because partitions are marched one at a time. The wrapper "
      "totals 94 427 µm² and 1 070 flip-flops at sixteen partitions.")

# ============================ 9: evaluation setup ============================
s = new_slide("Evaluation setup", 9)
bullets(s, MARGIN, BODY_TOP, CONTENT_W, [
    "10 000 identical fault maps per point; 1–30 defects; 256 × 30 array; S = 2.",
    "Defects are cells, pairs, 2×2 clusters, word lines and bit lines, in four mixes:",
    ("date06 — 40 % cells, 40 % pairs, 20 % clusters", "ind mono"),
    ("kang-dl — 80 % cells, 10 % rows, 10 % columns", "ind mono"),
    ("kang-dh — 45 % cells, 28 % rows, 27 % columns", "ind mono"),
    ("mixed — 70 % cells, 14 % pairs, 6 % clusters, 5 % rows, 5 % columns", "ind mono"),
    "Spares are fault-free; the mixes are assumptions.",
], size=18)
notes(s, "All allocators receive the same fault maps — 10 000 per point for one to thirty defects "
      "on a 256 by 30 array with a column multiplexing factor of two. The first three mixes follow "
      "mixes reported in the repair-analysis literature; the fourth is our own set. Spares are "
      "fault-free in the study, and the mixes are assumptions, which is why results are reported "
      "per mix.")

# ============================ 10: repair rate ============================
s = new_slide("Repair rate", 10)
table(s, MARGIN, BODY_TOP + Inches(0.05), [1.15, 0.55, 0.72, 0.72, 0.72, 0.85, 0.72],
      ["Mix", "K", "P16", "P4", "P1", "EF+BB", "2-D"],
      [
       ["date06", "0", "8.3", "4.4", "2.5", "2.5", "2.5"],
       ["date06", "8", "21.5", "11.5", "7.0", "7.0", "2.5"],
       ["mixed", "0", "5.5", "4.4", "3.2", "3.1", "3.2"],
       ["mixed", "8", ("9.3", "accent"), "9.2", "8.2", "5.4", "3.2"],
       ["kang-dl", "0", "4.4", "4.1", "3.3", "3.3", "3.3"],
       ["kang-dl", "8", "5.4", "5.4", "5.4", "4.3", "3.3"],
       ["kang-dh", "0", "2.2", "2.2", "2.2", "2.2", "2.2"],
       ["kang-dh", "8", "2.2", "2.2", "2.2", "2.2", "2.2"],
      ],
      aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT,
              PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
      row_h=Inches(0.36), size=13, head_size=12, mono_cols=(2, 3, 4, 5, 6))
text(s, MARGIN, BODY_TOP + Inches(0.05) + Inches(0.36) * 9 + Inches(0.15), Inches(6.0), Inches(0.7),
     ["P16/P4/P1: this work with 16/4/1 partitions. EF+BB: ECC first, exact 2-D, spare buy-back. 2-D: exact repair without ECC."],
     size=11, color=MUTED)
pic(s, PROTO, MARGIN + Inches(6.3), BODY_TOP + Inches(0.05), SW - MARGIN - (MARGIN + Inches(6.3)), Inches(4.3))
text(s, MARGIN, Inches(6.5), CONTENT_W, Inches(0.5),
     [[("3.2 → 9.3 defects at 90 % repair (mixed, K = 8, 16 partitions); no gain when line defects dominate.",
        {"color": ACCENT, "bold": True, "size": 17})]])
notes(s, "Partitioned steering helps most when cells and clusters dominate — date06 goes from 2.5 "
      "to 8.3 already at K = 0 — and not at all when line defects dominate, where the two spare "
      "words are the limit. An ECC budget raises tolerance further, and with K = 0 and one "
      "partition the allocator coincides with exact two-dimensional repair, as it must. Joint "
      "allocation also beats ECC-first with buy-back when lines are present.")

# ============================ 11: autoMBIST ============================
s = new_slide("Against autoMBIST", 11)
table(s, MARGIN, BODY_TOP + Inches(0.05), [1.4, 0.7, 1.5, 1.5, 1.5, 1.5, 1.7],
      ["Mix", "n", "1-pass", "2-pass", "exact", "K = 8", "P16, K = 8"],
      [
       ["mixed", "4", "35.0", "65.6", "65.9", "98.6", "98.6"],
       ["mixed", "6", "0.3", "2.0", "2.1", "96.5", "96.5"],
       ["mixed", "8", "0.0", "0.1", "0.1", "91.4", "93.0"],
       ["kang-dl", "4", "45.6", "68.9", "69.6", "94.9", "94.9"],
       ["kang-dl", "6", "0.3", "3.5", "3.7", "87.8", "87.8"],
       ["kang-dh", "4", "6.1", "26.2", "27.6", "63.3", "63.3"],
      ],
      aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT,
              PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
      row_h=Inches(0.42), size=15, head_size=13, mono_cols=(1, 2, 3, 4, 5, 6))
text(s, MARGIN, Inches(4.75), CONTENT_W, Inches(1.0),
     ["autoMBIST columns: on-chip 1-pass and 2-pass analysers, exact tester solver (its model, commit 032deb05, on our fault maps).",
      "Repair rate (%) on identical fault maps, 10 000 maps per point, 2 spare words and 2 spare columns."],
     size=12, color=MUTED)
text(s, MARGIN, Inches(6.15), CONTENT_W, Inches(0.8),
     [[("Its two-pass on-chip analyser is close to exact 2-D; the gap to TRIAD is ECC and partitions, "
        "which cost check bits and a steering table. No area comparison made.",
        {"color": ACCENT, "bold": True, "size": 16})]])
notes(s, "autoMBIST solves the two-dimensional problem exactly on the tester and ships a one-pass "
      "and a two-pass on-chip heuristic, documented as approximations. We ran its decision model "
      "unchanged on our fault maps; its exact solver and ours agreed on all 800 000 maps. The "
      "two-pass heuristic is close to exact, so the gap is the gap between repair with and without "
      "ECC and partitions. No area comparison is made, since we did not build its hardware.")

# ============================ 12: reliability cost ============================
s = new_slide("Reliability cost", 12)
bullets(s, MARGIN, BODY_TOP, CONTENT_W, [
    "A word that spends ECC on a hard fault has none left for soft errors.",
    ("Each ECC-reliant word adds 0.0145 FIT of DUE (assumed 1000 FIT/Mbit, single-bit upsets).", "accent"),
    "The budget caps the cost at 0.0145 · K FIT; without ECC the memory would see 6.1 FIT of silent errors.",
], size=18)
table(s, MARGIN, Inches(3.9), [4.2, 2.6, 2.6],
      ["Allocator (mixed, K = 8)", "mean ECC words, n = 4", "mean ECC words, n = 8"],
      [
       ["TRIAD, 16 partitions", "0.03", "0.53"],
       ["TRIAD, 1 partition", "0.44", "4.47"],
       ["ECC-first, no buy-back", "4.63", "—"],
       ["TRIAD on the dies ECC-first repaired", "0.41", "—"],
      ],
      aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
      row_h=Inches(0.42), size=15, head_size=13, mono_cols=(1, 2))
notes(s, "Counting single-bit upsets at an assumed 1000 FIT per megabit and a one-year data "
      "lifetime, the memory has 10^-6 FIT of detected uncorrectable errors with no ECC-reliant "
      "word, and each such word adds 0.0145 FIT; the budget K is therefore a ceiling of "
      "0.0145·K. Joint allocation also keeps far fewer words on ECC than ECC-first: 0.03 against "
      "4.63 at four defects. These ECC-first baselines follow the published outline of EBISR and "
      "were not checked against the full paper.")

# ============================ 13: verification ============================
s = new_slide("Verification", 13)
table(s, MARGIN, BODY_TOP, [7.0, 3.4, 1.4],
      ["Gate", "Result", "Status"],
      [
       ["Python golden-model and theory tests", "92 passed", "pass"],
       ["Datapath unit tests (cocotb + Icarus)", "5 of 5", "pass"],
       ["System tests vs golden model, 3 parameter sets", "7 of 7 in each", "pass"],
       ["Mutation check: injected RTL bugs detected", "13 of 13", "pass"],
       ["Verilator lint -Wall", "0 warnings", "pass"],
       ["Formal: SEC-DED corrects 1, detects 2", "proved by k-induction", "pass"],
       ["Formal: steered columns never reach output", "bounded, depth 11", ("open", "warn")],
       ["Post-route gate-level simulation, no SDF", "8 of 8 cases match", ("open", "warn")],
      ],
      row_h=Inches(0.44), size=14, head_size=13, mono_cols=(2,))
notes(s, "The RTL is compared with a Python model that follows the hardware algorithm, itself "
      "checked against exhaustive search; all thirteen seeded RTL bugs are detected. The SEC-DED "
      "code is proved by k-induction, while the steering datapath is proved only to a bound of "
      "eleven cycles and the gate-level simulation carries no timing — those two are the open "
      "items. Results are from the last full regression at commit fe7bf79.")

# ============================ 14: physical design ============================
s = new_slide("Physical design", 14)
pic(s, LAYOUT, MARGIN, BODY_TOP, Inches(6.9), Inches(4.9))
tx = MARGIN + Inches(7.15)
table(s, tx, BODY_TOP + Inches(0.05), [3.3, 1.65],
      ["Check", "Result"],
      [
       ["Detailed-routing violations", "0"],
       ["LVS errors", "0"],
       ["Worst setup / hold slack", "1.95 / 0.10 ns"],
       ["DRC of final GDS (macro abstract)", "0"],
       ["Antenna violations", ("1", "warn")],
       ["Max-slew violations (worst 1.33 / 0.75 ns)", ("200 pins", "warn")],
       ["Max-fanout violations (limit 10)", ("1705", "warn")],
      ],
      aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT], row_h=Inches(0.42),
      size=13, head_size=12, mono_cols=(1,))
text(s, tx, Inches(6.35), SW - MARGIN - tx, Inches(0.5),
     [[("Not sign-off clean.", {"color": WARN, "bold": True, "size": 17})]])
text(s, MARGIN, Inches(6.5), Inches(6.9), Inches(0.4),
     ["Routed layout, 1.30 × 0.72 mm die · OpenLane 1.0.2 · 40 ns clock · macro left."],
     size=12, color=MUTED)
notes(s, "The wrapper is routed with OpenLane 1.0.2 at a 40 ns clock on a 0.936 mm² die. Routing, "
      "LVS, timing and the DRC of the final GDS pass; one antenna violation, 200 maximum-slew "
      "violations and 1705 maximum-fanout violations remain open — the slew violations sit on "
      "nets that received antenna diodes late in the flow. The macro is treated as verified IP "
      "and its single-corner timing model means the clock mainly reflects the wrapper.")

# ============================ 15: limitations ============================
s = new_slide("Limitations", 15)
bullets(s, MARGIN, BODY_TOP, CONTENT_W, [
    "There is no silicon.",
    "The memory is small (8 kbit); defect mixes and the soft-error rate are assumptions.",
    "Spares are fault-free in the Monte Carlo study (hardware handles faulty spare columns).",
    "Multi-bit upsets are not modelled.",
    "ECC-first baselines were built from published descriptions.",
    "The proofs have not been reviewed by a second person.",
], size=19)
notes(s, "The results are simulations on assumed defect mixes, not silicon measurements, and the "
      "memory is only 8 kbit. Spares are fault-free in the study even though the hardware can "
      "steer around a faulty spare column, and multi-bit upsets fall outside the reliability "
      "model. The ECC-first baselines were reconstructed from published descriptions, and the "
      "proofs await independent review.")

# ============================ 16: conclusion ============================
s = new_slide("Conclusion", 16)
bullets(s, MARGIN, BODY_TOP, CONTENT_W, [
    "Built: an exact on-chip allocator for spare words, partition-steered spare columns and a budgeted ECC, wrapped around an unmodified OpenRAM macro, RTL to GDS in sky130.",
    "Numbers: 3.2 → 9.3 defects at 90 % repair (mixed, K = 8, 16 partitions); the benefit depends on the defect mix — large for cells and clusters, absent for lines.",
    ("github.com/hieuminhvo250221-del/triad-bisr", "mono"),
    ("hieuminhvo250221-del.github.io/triad-bisr", "mono"),
], size=18)
notes(s, "Treating ECC as a budgeted repair resource and steering spare columns per partition lets "
      "a small on-chip allocator stay exact, and lets the designer cap the soft-error cost of "
      "repair. The benefit depends on the defect mix: large for cell and cluster defects, absent "
      "for line defects. The complete design, models, results and this deck's sources are in the "
      "repository and on the project site.")

prs.save(OUT)
print(f"wrote {OUT}")
