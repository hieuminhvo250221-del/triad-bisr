import type traces from "../data/generated/traces.json";

export type Scenario = (typeof traces.scenarios)[number];
export type Cfg = typeof traces.cfg;

/* 4×4 grid of partition tiles; each tile = 32 cols × 16 rows of square cells. */
const CS = 6.6;            // cell size px
const GAP = 5;             // gap before spare columns (px)
const TCAP = 15;           // tile caption height
const TW = 32 * CS + GAP;  // tile inner width (30 code + gap + 2 spare)
const TH = 16 * CS;        // tile inner height
const GX = 26, GY = 34;    // tile gaps
const ML = 8, MT = 26;     // margins (top leaves room for column header)
export const SVG_W = ML * 2 + 4 * TW + 3 * GX;
export const SVG_H = MT + 4 * (TH + TCAP) + 3 * GY + 30;

export function tileXY(p: number) {
  return { x: ML + (p % 4) * (TW + GX), y: MT + Math.floor(p / 4) * (TH + TCAP + GY) };
}
export function cellX(b: number, cfg: Cfg) { return b < cfg.code_bits ? b * CS : b * CS + GAP; }
export function cellY(r: number) { return TCAP + r * CS; }

export interface StepText {
  scode: string; sspare: string; words: string;
  cap0: string; cap1: string; cap2: string; cap3: string;
  capOk: string; capBad: string;
  capVerdictOk: string; capVerdictBad: string;
  legFault: string; legSteered: string; legSpare: string;
  legEcc: string; legCol: string;
}

const fill = (t: string, m: Record<string, number | string>) =>
  Object.entries(m).reduce((s, [k, v]) => s.replaceAll(`{${k}}`, String(v)), t);

export function stepIds(sc: Scenario): number[] {
  return sc.repairable ? [0, 1, 2, 3, 4] : [0, 4];
}

export function stepCaption(sc: Scenario, step: number, S: StepText): string {
  const nSteer = (sc.steer as (number | null)[][]).flat().filter((x) => x != null).length;
  switch (step) {
    case 0: return fill(S.cap0, { n: sc.faults.length });
    case 1: return fill(S.cap1, { s: nSteer });
    case 2: return fill(S.cap2, { r: sc.spare_words.length, R: sc.R });
    case 3: return fill(S.cap3, { e: sc.ecc_words, k: sc.K });
    case 4:
      return sc.repairable
        ? `${S.capOk}: ${fill(S.capVerdictOk, { e: sc.ecc_words, k: sc.K, r: sc.spare_words.length, R: sc.R })}`
        : `${S.capBad}: ${fill(S.capVerdictBad, { e: sc.ecc_words, k: sc.K })}`;
    default: return "";
  }
}

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");

/** Full inner SVG markup for a scenario at a step: 4×4 tile grid. */
export function traceSVG(sc: Scenario, cfg: Cfg, step: number, S: StepText): string {
  const o: string[] = [];
  const rect = (x: number, y: number, w: number, h: number, cls: string) =>
    o.push(`<rect class="${cls}" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}"/>`);
  const txt = (x: number, y: number, s: string, cls = "tlab", anchor?: string) =>
    o.push(`<text class="${cls}" x="${x.toFixed(1)}" y="${y.toFixed(1)}"${anchor ? ` text-anchor="${anchor}"` : ""}>${esc(s)}</text>`);

  // column header strip over the first tile row
  txt(ML, MT - 10, `${S.scode} 0–${cfg.code_bits - 1}`);
  txt(ML + cellX(cfg.spare_cols[0]!, cfg) + 4, MT - 10, `${S.sspare} ${cfg.spare_cols.join(",")}`);

  // fault lookup
  const faultSet = new Set(sc.faults.map(([w, b]) => `${w},${b}`));
  const steeredBit = (w: number, b: number) => {
    const st = sc.steer[Math.floor(w / cfg.win)];
    return !!st && st.some((x) => x === b);
  };

  for (let p = 0; p < cfg.parts; p++) {
    const { x: tx, y: ty } = tileXY(p);
    txt(tx, ty + 10, `P${p} · ${S.words} ${p * cfg.win}–${p * cfg.win + cfg.win - 1}`, "tlab");
    // cell grid (light lines)
    for (let r = 0; r <= cfg.win; r++) rect(tx, ty + TCAP + r * CS - 0.5, TW, 0.5, "tgrid");
    for (let c = 0; c <= cfg.code_bits + 2; c++) {
      const cx = c <= cfg.code_bits ? c * CS : c * CS + GAP;
      rect(tx + cx - 0.25, ty + TCAP, 0.5, TH, "tgrid");
    }
    // steered columns: accent outline + tick on spare col + tag
    const st = sc.steer[p];
    if (step >= 1 && st) {
      st.forEach((b, i) => {
        if (b == null) return;
        rect(tx + cellX(b, cfg) - 0.7, ty + TCAP - 1, CS + 1.4, TH + 2, "tsteer");
        const spx = tx + cellX(cfg.spare_cols[i]!, cfg);
        rect(spx + CS / 2 - 2.5, ty + TCAP - 8, 5, 5, "ttick");
        txt(tx + cellX(b, cfg) + CS / 2, ty + TCAP + TH + 10 + i * 11, `→ s${i}`, "ttag", "middle");
      });
    }
    // spare-word rows: raised tint + bracket + hollow faults
    for (const w of sc.spare_words as number[]) {
      if (Math.floor(w / cfg.win) !== p) continue;
      const r = w % cfg.win, y = ty + cellY(r);
      rect(tx, y, TW, CS, "tspare");
      o.push(`<path class="tbracket" d="M${(tx - 3).toFixed(1)} ${y.toFixed(1)} l3 0 l0 ${CS.toFixed(1)} l-3 0"/>`);
    }
    // faults
    for (const [w, b] of sc.faults) {
      if (Math.floor(w! / cfg.win) !== p) continue;
      const r = w! % cfg.win;
      const removed = (step >= 1 && steeredBit(w!, b!)) || (step >= 2 && (sc.spare_words as number[]).includes(w!));
      rect(tx + cellX(b!, cfg) + 0.5, ty + cellY(r) + 0.5, CS - 1, CS - 1, removed ? "tfault-h" : "tfault");
    }
    // ECC-reliant words: warn outline on remaining fault cells + E tag
    if (step >= 3) {
      for (const w of sc.ecc_reliant as number[]) {
        if (Math.floor(w / cfg.win) !== p) continue;
        const r = w % cfg.win, y = ty + cellY(r);
        for (let b = 0; b < cfg.code_bits + 2; b++) {
          if (faultSet.has(`${w},${b}`))
            rect(tx + cellX(b, cfg) - 0.4, y - 0.4, CS + 0.8, CS + 0.8, "tecc");
        }
        txt(tx + TW + 3, y + CS - 1.5, "E", "ttag");
      }
    }
  }

  // legend under the grid: sample glyph + text for each mark
  const ly = SVG_H - 16;
  const items: [string, string][] = [
    ["tfault", S.legFault],
    ["tfault-h", S.legSteered],
    ["tspare", S.legSpare],
    ["tecc", S.legEcc],
    ["tsteer", S.legCol],
  ];
  let lx = ML;
  for (const [cls, label] of items) {
    o.push(`<rect class="${cls}" x="${lx.toFixed(1)}" y="${(ly - 7).toFixed(1)}" width="7" height="7"/>`);
    o.push(`<text class="tlab" x="${(lx + 11).toFixed(1)}" y="${ly.toFixed(1)}">${esc(label)}</text>`);
    lx += 11 + label.length * 6.2 + 18;
  }
  return o.join("");
}
