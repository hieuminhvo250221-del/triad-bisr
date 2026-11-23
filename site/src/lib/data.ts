import asic from "../data/generated/asic.json";
import verification from "../data/generated/verification.json";
import ppa from "../data/generated/ppa.json";
import protocol from "../data/generated/protocol.json";
import reliability from "../data/generated/reliability.json";
import automb from "../data/generated/automb.json";
import protocol_large from "../data/generated/protocol_large.json";
import chip3d from "../data/generated/chip3d.json";
import traces from "../data/generated/traces.json";
import staticTables from "../data/generated/static.json";

export const data = {
  asic, verification, ppa, protocol, reliability, automb,
  protocol_large, chip3d, traces, static: staticTables,
};

type Files = keyof typeof data;

/** Look up a generated-data key ("asic.DIEAREA_mm^2"); throws on a miss so the build fails loudly. */
export function get(path: string): unknown {
  const dot = path.indexOf(".");
  const file = (dot < 0 ? path : path.slice(0, dot)) as Files;
  const obj = data[file];
  if (obj === undefined) throw new Error(`site data: unknown file "${file}" in "${path}"`);
  if (dot < 0) return obj;
  const rest = path.slice(dot + 1);
  let v: unknown = obj;
  for (const part of rest.split(".")) {
    v = (v as Record<string, unknown>)?.[part];
    if (v === undefined) {
      // flat keys may themselves contain dots — try the joined remainder progressively
      for (let i = rest.split(".").length - 1; i > 0; i--) {
        const head = rest.split(".").slice(0, i).join(".");
        if ((obj as Record<string, unknown>)[head] !== undefined) {
          v = (obj as Record<string, unknown>)[head];
          let tail: unknown = v;
          for (const p of rest.split(".").slice(i)) {
            tail = (tail as Record<string, unknown>)?.[p];
          }
          if (tail !== undefined) return tail;
        }
      }
      throw new Error(`site data: missing key "${path}"`);
    }
  }
  return v;
}

export function num(path: string): number {
  const v = get(path);
  if (typeof v !== "number") throw new Error(`site data: "${path}" is ${JSON.stringify(v)}, not a number`);
  return v;
}

export function gateResult(id: string): string {
  const g = verification.gates.find((x) => x.id === id);
  if (!g) throw new Error(`site data: no verification gate "${id}"`);
  return g.result;
}
