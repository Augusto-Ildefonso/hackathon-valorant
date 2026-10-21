// Drives the "Análise por IA" button on a page: scrolls to the mode bar, clicks, checks the page does not jump or collapse,
// waits for the AI insights and screenshots the bar + insight panels before and after. Usage (make dev running, key in .env):
//   node scripts/test-ai-insights.mjs <route> <out-prefix> [maxWaitSeconds=300]
import { chromium } from "playwright";

const [route, outPrefix = "ai", maxWait = "300"] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
page.on("console", (m) => m.type() === "error" && errors.push(`console: ${m.text()}`));
await page.goto(`http://localhost:5173${route}`, { waitUntil: "networkidle" });
const bar = page.getByText("Insights por", { exact: true });
await bar.waitFor({ timeout: 120000 });
await bar.scrollIntoViewIfNeeded();
await page.waitForTimeout(600);
const region = async (name) => {
  const box = await bar.evaluate((el) => {
    const r = el.getBoundingClientRect();
    return { x: 0, y: r.y + window.scrollY - 8, width: 1440, height: Math.min(document.body.scrollHeight - (r.y + window.scrollY) + 8, 620) };
  });
  await page.screenshot({ path: `${outPrefix}-${name}.png`, fullPage: true, clip: box });
};
const metrics = async () => page.evaluate(() => ({ y: Math.round(window.scrollY), h: document.body.scrollHeight, ia: document.body.innerText.split("\n").filter((l) => l.trim() === "IA").length }));
console.log("before:", await metrics());
await region("rules");
const button = page.getByRole("button", { name: /Análise por IA/ });
console.log("button disabled:", await button.isDisabled());
await button.click();
await page.waitForTimeout(1500);
console.log("1.5 s after click:", await metrics(), "| loading msg:", (await page.getByText("Gerando a análise por IA").count()) > 0);
const t0 = Date.now();
let state = "timeout";
while (Date.now() - t0 < Number(maxWait) * 1000) {
  if (await page.getByText("Análise por IA a partir dos fatos calculados").count()) { state = "ai"; break; }
  if (await page.getByText("não ficou disponível agora").count()) { state = "fallback-to-rules"; break; }
  await page.waitForTimeout(2000);
}
console.log("result:", state, "after", Math.round((Date.now() - t0) / 1000), "s", await metrics());
await region("ai");
// back to the rules
await page.getByRole("button", { name: /^Regras$/ }).click();
await page.waitForTimeout(800);
console.log("back to rules:", await metrics());
console.log(errors.length ? `ERRORS:\n${errors.join("\n")}` : "no console errors");
await browser.close();
