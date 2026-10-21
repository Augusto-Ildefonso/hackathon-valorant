// Drives "Gerar narrativa": scrolls down, clicks, and reports the scroll position before / during / after the request.
//   node scripts/test-narrative.mjs [maxWaitSeconds=240]   (make dev must be running, key in .env)
import { chromium } from "playwright";

const maxWait = Number(process.argv[2] ?? 240) * 1000;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
page.on("console", (m) => m.type() === "error" && errors.push(`console: ${m.text()}`));
const team = encodeURIComponent(process.env.TEAM ?? "UFMT Turuna");
await page.goto(`http://localhost:5173/plano?teamA=${team}`, { waitUntil: "networkidle" });
const button = page.getByRole("button", { name: /Gerar narrativa/ });
await button.waitFor({ timeout: 120000 });
await button.scrollIntoViewIfNeeded();
await page.waitForTimeout(500);
const before = await page.evaluate(() => window.scrollY);
console.log("button disabled:", await button.isDisabled(), "| scrollY before click:", before);
await button.click();
await page.waitForTimeout(1500);
const during = await page.evaluate(() => ({ y: window.scrollY, h: document.body.scrollHeight, text: document.body.innerText.includes("Narrativa de treinador") }));
console.log("1.5 s after click:", during);
console.log("progress message visible:", (await page.getByText("Escrevendo a narrativa com IA").count()) > 0, "| button label:", await page.getByRole("button", { name: /Gerar narrativa|Escrevendo/ }).innerText());
const t0 = Date.now();
let done = false;
while (Date.now() - t0 < maxWait) {
  if (await page.getByText("reescrito por IA").count()) { done = true; break; }
  if (await page.getByText("Narrativa por IA").count()) { done = true; break; }
  await page.waitForTimeout(2000);
}
const after = await page.evaluate(() => ({ y: window.scrollY, h: document.body.scrollHeight }));
console.log("finished:", done, "after", Math.round((Date.now() - t0) / 1000), "s", after);
console.log("caption:", await page.locator("text=/reescrito por IA|gerado por regras/").first().innerText().catch(() => "?"));
console.log("narrative paragraph:", (await page.locator("p.whitespace-pre-line").first().innerText().catch(() => "none")).slice(0, 160));
console.log(errors.length ? `ERRORS:\n${errors.join("\n")}` : "no console errors");
await browser.close();
