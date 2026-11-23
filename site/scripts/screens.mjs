// Playwright screenshots: / and /vi/ at desktop + mobile, plus focus and chart states.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const BASE = process.env.SITE_URL || "http://localhost:4321/triad-bisr";
const OUT = fileURLToPath(new URL("../.screens/", import.meta.url));
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const shots = [
  ["en-desktop", "/", 1440, 900],
  ["vi-desktop", "/vi/", 1440, 900],
  ["en-mobile", "/", 390, 844],
  ["vi-mobile", "/vi/", 390, 844],
];
for (const [name, path, w, h] of shots) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await page.goto(BASE + path, { waitUntil: "networkidle" });
  // scroll through once so below-the-fold content paints before the full-page capture
  await page.evaluate(async () => {
    const step = innerHeight * 0.8;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 60));
    }
    scrollTo(0, 0);
  });
  await page.waitForFunction(() => [...document.images].every((i) => i.complete && i.naturalWidth > 0));
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}${name}.png`, fullPage: true });
  await page.close();
  console.log(`wrote .screens/${name}.png`);
}
// keyboard focus on nav
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(BASE + "/", { waitUntil: "networkidle" });
  await page.keyboard.press("Tab"); // skip link
  await page.keyboard.press("Tab"); // brand
  await page.keyboard.press("Tab"); // first nav link
  await page.screenshot({ path: `${OUT}focus-nav.png` });
  console.log("wrote .screens/focus-nav.png");
  await page.close();
}
// chart with non-default selection
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(BASE + "/#signoff-status?mix=kang_dh&r=4&k=0", { waitUntil: "networkidle" });
  const sel = page.locator("#repair-rate-mix");
  await sel.selectOption("kang_dh");
  await page.locator("#repair-rate-r").selectOption("4");
  await page.locator("#repair-rate-k").selectOption("0");
  await page.locator("#repair-rate").scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${OUT}chart-nondefault.png` });
  console.log("wrote .screens/chart-nondefault.png");
  await page.close();
}
await browser.close();
