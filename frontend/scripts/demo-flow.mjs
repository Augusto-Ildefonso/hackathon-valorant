// End-to-end demo flow (the pitch storyline) clicked through like a user, with screenshots for the slides.
// Usage (make dev running):  npm run demo-flow [out-dir=demo-shots]
import { mkdirSync } from "node:fs";
import { chromium } from "playwright";

const WEB = process.env.WEB ?? "http://localhost:5173";
const out = process.argv[2] ?? "demo-shots";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
page.on("console", (m) => m.type() === "error" && errors.push(`console: ${m.text()}`));
const steps = [];
const step = async (name, fn) => {
  try { await fn(); steps.push(`ok   ${name}`); } catch (e) { steps.push(`FAIL ${name}: ${String(e.message).split("\n")[0]}`); }
};
const shot = (n) => page.screenshot({ path: `${out}/${n}.png`, fullPage: true });
const see = (text, timeout = 60000) => page.getByText(text).first().waitFor({ timeout });

await step("1 Home: KPIs and leaderboards", async () => {
  await page.goto(WEB, { waitUntil: "domcontentloaded" });
  await see("VAVÁGYM");
  await page.waitForLoadState("networkidle");
  await shot("1-home");
});

await step("2 Search a player and open the profile", async () => {
  await page.getByPlaceholder("Buscar jogador, time ou mapa…").fill("chadu");
  await page.getByRole("link", { name: /chadu/i }).first().click();
  await see("Pontos fortes");
  await page.waitForLoadState("networkidle");
  await shot("2-player");
});

await step("3 Player -> team profile", async () => {
  await page.locator("a[href^='/time/']").first().click();
  await see("Pontos fortes");
  await page.waitForLoadState("networkidle");
  await shot("3-team");
});

await step("4 Map profile: blind-spot layers toggle", async () => {
  await page.goto(`${WEB}/mapa/Haven`, { waitUntil: "domcontentloaded" });
  await see("Pontos cegos");
  await page.waitForLoadState("networkidle");
  const chips = page.getByRole("button").filter({ hasText: /perigosa|descoberta|zona/i });
  if (await chips.count()) await chips.first().click();
  await shot("4-map");
});

await step("5 Match report: pick a round, kill replay follows", async () => {
  await page.goto(`${WEB}/partidas`, { waitUntil: "domcontentloaded" });
  await page.getByText("Ver relatório").first().click();
  await see("Replay de abates");
  await page.waitForLoadState("networkidle");
  await page.locator("button").filter({ hasText: /^7/ }).first().click();
  await page.waitForTimeout(1200);
  await shot("5-match");
});

await step("6 Action Plan: round-by-round detail", async () => {
  await page.goto(`${WEB}/plano?teamA=UFMT%20Turuna&teamB=Azure%20Bears%20Black&map=Haven`, { waitUntil: "domcontentloaded" });
  await see("Linha do tempo da partida", 120000);
  await page.waitForLoadState("networkidle");
  await shot("6-plan");
  await page.getByRole("button", { name: /^R5\b/ }).first().click();
  await page.waitForTimeout(1200);
  await see("Movimento provável do adversário");
  await shot("6-plan-round");
});

await browser.close();
console.log(steps.join("\n"));
console.log(errors.length ? `\nERRORS:\n${errors.join("\n")}` : "\nno console errors");
process.exit(steps.some((s) => s.startsWith("FAIL")) || errors.length ? 1 : 0);
