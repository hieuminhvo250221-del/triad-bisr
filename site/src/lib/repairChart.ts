/** Shared repair-rate chart: pure SVG-markup builder, run at build time and again client-side
 *  when the controls change. Output is identical both ways so the default view works without JS. */

export interface Sel {
  mix: string;
  r: number;
  k: number;
}

export interface SeriesSpec {
  algo: string;
  label: string;
  color: string;
  width: number;
  dash?: string;
}

export const MIXES = ["date06", "kang_dl", "kang_dh", "mixed"] as const;
export const RS = [2, 4] as const;
export const KS = [0, 2, 8] as const;
export const S_FIXED = 2;

export const SERIES: SeriesSpec[] = [
  { algo: "triad_p16",   label: "TRIAD-P, 16 partitions",        color: "#0f5c5a", width: 2.4 },
  { algo: "triad_p4",    label: "TRIAD-P, 4 partitions",         color: "#0f5c5a", width: 2.0, dash: "7 3" },
  { algo: "triad_rel",   label: "TRIAD, no partitions (exact)",  color: "#18181a", width: 2.0 },
  { algo: "greedy_joint",label: "Greedy joint",                  color: "#5c5b57", width: 1.7 },
  { algo: "ef_exact_bb", label: "ECC-first + buy-back",          color: "#8a897f", width: 1.7, dash: "2 3" },
  { algo: "ef_esp",      label: "ECC-first ESP (EBISR-like)",    color: "#8a897f", width: 1.7, dash: "8 2 2 2" },
  { algo: "exact_2d",    label: "2-D exact, no ECC",             color: "#b9b6aa", width: 1.7 },
];

export const DEFAULT_SEL: Sel = { mix: "mixed", r: 2, k: 8 };

const W = 740;
const H = 400;
const ML = 52; // left margin
const MR = 196; // right margin for end labels
const MT = 18;
const MB = 42;
const X0 = 1;
const X1 = 30;

function sx(d: number): number {
  return ML + ((d - X0) / (X1 - X0)) * (W - ML - MR);
}
function sy(p: number): number {
  return MT + (1 - p / 100) * (H - MT - MB);
}

export type ProtocolData = {
  defect_range: number[];
  // rate may be a percent array aligned to defect_range, or a 0..1 dict keyed by defects
  series: Record<string, { trials: number; rate: Record<string, number> | number[] }>;
};

function rateAt(p: ProtocolData, sel: Sel, algo: string, d: number): number | null {
  const s = p.series[`${sel.mix},${sel.r},${S_FIXED},${sel.k},${algo}`];
  if (!s) return null;
  if (Array.isArray(s.rate)) {
    const i = p.defect_range.indexOf(d);
    const v = i >= 0 ? s.rate[i] : undefined;
    return v === undefined ? null : v;
  }
  const v = s.rate[String(d)];
  return v === undefined ? null : v * 100;
}

/** Chart inner SVG (axes, grid, series, end labels) for a given selection. */
export function chartSvg(p: ProtocolData, sel: Sel, strings: { title: string; x: string; y: string; guide: string }): string {
  const out: string[] = [];
  // gridlines at 0/25/50/75/100
  for (const gy of [0, 25, 50, 75, 100]) {
    out.push(
      `<line x1="${ML}" y1="${sy(gy)}" x2="${W - MR}" y2="${sy(gy)}" stroke="#dedbd1" stroke-width="1"/>`,
      `<text x="${ML - 8}" y="${sy(gy) + 4}" text-anchor="end" class="chart-axis">${gy}</text>`,
    );
  }
  for (const gx of [1, 5, 10, 15, 20, 25, 30]) {
    out.push(`<text x="${sx(gx)}" y="${H - MB + 20}" text-anchor="middle" class="chart-axis">${gx}</text>`);
  }
  out.push(
    `<line x1="${ML}" y1="${MT}" x2="${ML}" y2="${H - MB}" stroke="#18181a" stroke-width="1"/>`,
    `<line x1="${ML}" y1="${H - MB}" x2="${W - MR}" y2="${H - MB}" stroke="#18181a" stroke-width="1"/>`,
    `<text x="${(ML + W - MR) / 2}" y="${H - 6}" text-anchor="middle" class="chart-axistitle">${strings.x}</text>`,
    `<text x="14" y="${MT + (H - MT - MB) / 2}" text-anchor="middle" transform="rotate(-90 14 ${MT + (H - MT - MB) / 2})" class="chart-axistitle">${strings.y}</text>`,
  );
  // 90 % guide
  out.push(
    `<line x1="${ML}" y1="${sy(90)}" x2="${W - MR}" y2="${sy(90)}" stroke="#9a5b00" stroke-width="1" stroke-dasharray="6 4"/>`,
    `<text x="${W - MR + 6}" y="${sy(90) - 4}" class="chart-axis">${strings.guide}</text>`,
  );
  // series
  const ends: { y: number; ey: number; label: string; color: string }[] = [];
  for (const s of SERIES) {
    const pts: string[] = [];
    for (const d of p.defect_range) {
      const v = rateAt(p, sel, s.algo, d);
      if (v === null) continue;
      pts.push(`${sx(d).toFixed(1)},${sy(v).toFixed(1)}`);
    }
    if (!pts.length) continue;
    out.push(
      `<polyline points="${pts.join(" ")}" fill="none" stroke="${s.color}" stroke-width="${s.width}"` +
        (s.dash ? ` stroke-dasharray="${s.dash}"` : "") + ` stroke-linejoin="round" stroke-linecap="round"/>`,
    );
    const last = pts[pts.length - 1]!;
    const ly = parseFloat(last.split(",")[1]!);
    ends.push({ y: ly, ey: ly, label: s.label, color: s.color });
  }
  // end labels: sort by y, push apart with a minimum gap, then clamp inside the plot
  ends.sort((a, b) => a.y - b.y);
  const GAP = 13;
  for (let i = 1; i < ends.length; i++) {
    const cur = ends[i]!;
    const prev = ends[i - 1]!;
    if (cur.y - prev.y < GAP) cur.y = prev.y + GAP;
  }
  const yTop = MT + 4;
  const yBot = H - MB - 4;
  if (ends.length && ends[ends.length - 1]!.y > yBot) {
    const shift = ends[ends.length - 1]!.y - yBot;
    for (const e of ends) e.y -= shift;
    for (let i = ends.length - 2; i >= 0; i--) {
      const nxt = ends[i + 1]!;
      if (nxt.y - ends[i]!.y < GAP) ends[i]!.y = nxt.y - GAP;
    }
    if (ends[0]!.y < yTop) {
      const lift = yTop - ends[0]!.y;
      for (const e of ends) e.y += lift;
    }
  }
  for (const e of ends) {
    // leader line from the series end point to its (possibly displaced) label
    out.push(
      `<polyline points="${(W - MR).toFixed(1)},${e.ey.toFixed(1)} ${(W - MR + 3).toFixed(1)},${e.y.toFixed(1)}" ` +
        `fill="none" stroke="${e.color}" stroke-width="0.75" opacity="0.6"/>`,
      `<text x="${W - MR + 6}" y="${e.y + 4}" class="chart-label">${e.label}</text>`,
    );
  }
  return out.join("\n    ");
}

/** Data table rows (for the <details> fallback): series × defect → rate %. */
export function chartRows(p: ProtocolData, sel: Sel): { algo: string; cells: (number | null)[] }[] {
  return SERIES.map((s) => ({
    algo: s.label,
    cells: p.defect_range.map((d) => rateAt(p, sel, s.algo, d)),
  }));
}
