import en from "./en";
import vi from "./vi";

export type Lang = "en" | "vi";
const dicts = { en, vi };

let current: Lang = "en";
export function setLang(l: Lang) {
  current = l;
}
export function getLang(): Lang {
  return current;
}
export function t(key: keyof typeof en): string {
  const v: unknown = dicts[current][key];
  return typeof v === "string" ? v : `?${String(key)}`;
}
export function dict(l: Lang = current): typeof en {
  return dicts[l] as typeof en;
}

/** Locale-aware number formatting; `digits` = fraction digits. */
export function fmt(v: number, digits = 0, lang: Lang = current): string {
  return new Intl.NumberFormat(lang === "vi" ? "vi-VN" : "en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(v);
}
