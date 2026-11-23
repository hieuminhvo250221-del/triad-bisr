// Full-coverage screenshots + checks: hero, arch diagram, stepper states,
// automb table, chip3d presets, console errors, 390px overflow, img dims, weight.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const BASE = process.env.SITE_URL || "http://localhost:4321/triad-bisr";
const OUT = fileURLToPath(new URL("../.screens/", import.meta.url));
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const errors = [];

function newPage(w, h) {
  return browser.newPage({ viewport: { width: w, height: h } }).then((p) => {
    p.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
    p.on("console", (m) => {
      if (m.type() === "error") errors.push(`console.error: ${m.text()}`);
    });
    return p;
  });
}
async function scrollPaint(page) {
  await page.evaluate(async () => {
    const step = innerHeight * 0.8;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 50));
    }
    scrollTo(0, 0);
  });
  await page.waitForFunction(() =>
    [...document.images].every((i) => i.complete && i.naturalWidth > 0));
}

// ---- hero crop (desktop, top of page) ----
{
  const p = await newPage(1440, 900);
  await p.goto(BASE + "/", { waitUntil: "networkidle" });
  await p.waitForFunction(() =>
    [...document.images].every((i) => i.complete && i.naturalWidth > 0));
  await p.screenshot({ path: `${OUT}hero.png` });
  console.log("wrote hero.png");
  await p.close();
}

async function unstickHeader(p) {
  await p.addStyleTag({ content: ".site-header{position:static!important}" });
}

// ---- arch diagram desktop + mobile ----
for (const [name, w, h] of [["arch-desktop", 1440, 900], ["arch-mobile", 390, 844]]) {
  const p = await newPage(w, h);
  await p.goto(BASE + "/#architecture", { waitUntil: "networkidle" });
  await unstickHeader(p);
  const el = p.locator(".diagramwrap").first();
  await el.scrollIntoViewIfNeeded();
  await el.screenshot({ path: `${OUT}${name}.png` });
  console.log(`wrote ${name}.png`);
  await p.close();
}

// ---- stepper: mixed steps 0-4 ----
{
  const p = await newPage(1440, 1500);
  await p.goto(BASE + "/", { waitUntil: "networkidle" });
  await unstickHeader(p);
  const stepper = p.locator("[data-stepper]").first();
  await stepper.scrollIntoViewIfNeeded();
  const sel = stepper.locator(".sc-sel");
  await sel.selectOption("mixed");
  await p.waitForTimeout(100);
  const next = stepper.locator(".snext");
  for (let i = 0; i < 5; i++) {
    await stepper.screenshot({ path: `${OUT}step-mixed-${i}.png` });
    console.log(`wrote step-mixed-${i}.png`);
    if (i < 4) { await next.click(); await p.waitForTimeout(120); }
  }
  // unrepairable verdict
  await sel.selectOption("unrepairable");
  await p.waitForTimeout(100);
  await next.click();
  await p.waitForTimeout(120);
  await stepper.screenshot({ path: `${OUT}step-unrepairable-verdict.png` });
  console.log("wrote step-unrepairable-verdict.png");
  await p.close();
}

// ---- automb table desktop + mobile ----
for (const [name, w, h] of [["automb-desktop", 1440, 900], ["automb-mobile", 390, 844]]) {
  const p = await newPage(w, h);
  await p.goto(BASE + "/#automb", { waitUntil: "networkidle" });
  await unstickHeader(p);
  const el = p.locator("#automb .tablewrap").first();
  await el.scrollIntoViewIfNeeded();
  await el.screenshot({ path: `${OUT}${name}.png` });
  console.log(`wrote ${name}.png`);
  await p.close();
}

// ---- weight + overflow + img-dimension checks (before 3-D click) ----
{
  const p = await newPage(1440, 900);
  await p.goto(BASE + "/", { waitUntil: "networkidle" });
  const weight = await p.evaluate(() => {
    let total = new XMLSerializer().serializeToString(document).length;
    for (const r of performance.getEntriesByType("resource"))
      total += r.transferSize || r.encodedBodySize || 0;
    return total;
  });
  console.log(`page weight before 3-D click: ${(weight / 1024).toFixed(1)} KB`);
  const imgs = await p.evaluate(() =>
    [...document.images].map((i) => ({ src: i.src.split("/").pop(), w: i.getAttribute("width"), h: i.getAttribute("height") })));
  const noDim = imgs.filter((i) => !i.w || !i.h);
  console.log(`images missing width/height: ${noDim.length}`, JSON.stringify(noDim));
  await p.close();
}
{
  const p = await newPage(390, 844);
  await p.goto(BASE + "/", { waitUntil: "networkidle" });
  await scrollPaint(p);
  const over = await p.evaluate(() => ({
    docW: document.documentElement.scrollWidth, win: innerWidth,
    bodyW: document.body.scrollWidth,
  }));
  console.log(`390px overflow check: ${JSON.stringify(over)} ${over.docW > over.win ? "FAIL" : "PASS"}`);
  await p.close();
}

// ---- chip3d viewer: load + 4 desktop presets + 1 mobile ----
{
  const p = await newPage(1440, 900);
  await p.goto(BASE + "/", { waitUntil: "networkidle" });
  const chip = p.locator("[data-chip3d]").first();
  await chip.scrollIntoViewIfNeeded();
  await chip.locator("[data-load]").click();
  await p.waitForSelector(".chip3d-canvas", { timeout: 120000 });
  await p.waitForFunction(
    () => document.querySelector("[data-readout]")?.textContent?.includes("drawn items"),
    undefined, { timeout: 120000 });
  await p.waitForTimeout(500);
  for (const preset of ["die", "macro", "rows", "route"]) {
    await chip.locator(`[data-preset="${preset}"]`).click();
    await p.waitForTimeout(600);
    await chip.screenshot({ path: `${OUT}chip3d-${preset}.png` });
    console.log(`wrote chip3d-${preset}.png`);
  }
  await p.close();
}
{
  const p = await newPage(390, 844);
  await p.goto(BASE + "/", { waitUntil: "networkidle" });
  const chip = p.locator("[data-chip3d]").first();
  await chip.scrollIntoViewIfNeeded();
  await chip.locator("[data-load]").click();
  await p.waitForSelector(".chip3d-canvas", { timeout: 120000 });
  await p.waitForFunction(
    () => document.querySelector("[data-readout]")?.textContent?.includes("drawn items"),
    undefined, { timeout: 120000 });
  await p.waitForTimeout(500);
  await chip.screenshot({ path: `${OUT}chip3d-mobile.png` });
  console.log("wrote chip3d-mobile.png");
  await p.close();
}

console.log(errors.length ? `CONSOLE ERRORS:\n${errors.join("\n")}` : "no console errors");
await browser.close();
