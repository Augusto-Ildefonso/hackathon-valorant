// Screenshot of the Action Plan "Mapa tático do round" panel for a given round chip. Usage:
//   node scripts/shot-map.mjs <round> <out.png>   (dev server must be running: make dev)
import { chromium } from "playwright";

const [round = "3", out = "map.png"] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
page.on("console", (m) => m.type() === "error" && errors.push(`console: ${m.text()}`));
await page.goto("http://localhost:5173/plano?teamA=UFMT%20Turuna", { waitUntil: "networkidle" });
await page.getByText("Mapa tático do round").first().waitFor({ timeout: 120000 });
await page.getByRole("button", { name: new RegExp(`^R${round}\\b`) }).first().click();
await page.waitForTimeout(800);
const box = await page.getByText("Mapa tático do round", { exact: true }).evaluate((el) => {
  let p = el;
  while (p && (p.offsetWidth < 1000 || p.offsetHeight < 400)) p = p.parentElement;
  const r = p.getBoundingClientRect();
  return { x: r.x, y: r.y + window.scrollY, width: r.width, height: r.height };
});
await page.screenshot({ path: out, fullPage: true, clip: box });
await browser.close();
console.log(errors.length ? `ERRORS:\n${errors.join("\n")}` : "no console errors");
