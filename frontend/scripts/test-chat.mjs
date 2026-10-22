// Chat flow: ask by typing, ask by clicking an (optional) suggestion, open the dashboard from the answer, deep-link the plan.
// Usage (make dev running):  node scripts/test-chat.mjs [out-dir=chat-shots]
import { mkdirSync } from "node:fs";
import { chromium } from "playwright";

const WEB = process.env.WEB ?? "http://localhost:5173";
const out = process.argv[2] ?? "chat-shots";
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
const ask = async (q) => {
  await page.getByLabel("Pergunta").fill(q);
  await page.getByRole("button", { name: "Enviar" }).click();
};

const meta = await (await fetch(`${process.env.API ?? "http://localhost:8000"}/api/matches?limit=1`)).json();
const m = meta.items[0];
const teamA = m.team_a.team.name, teamB = m.team_b.team.name, map = m.map.name;

await step("chat is the first page and the old home lives at /campeonatos", async () => {
  await page.goto(WEB, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Pergunte ao VaváGym" }).waitFor({ timeout: 30000 });
  await page.goto(`${WEB}/campeonatos`, { waitUntil: "domcontentloaded" });
  await page.getByText("Partidas recentes").first().waitFor({ timeout: 30000 });
});

await step("typing a team question answers with stats and a dashboard button", async () => {
  await page.goto(WEB, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => sessionStorage.clear());
  await ask(`como está o time ${teamA}?`);
  await page.getByText("Pontos fortes").first().waitFor({ timeout: 60000 });
  await page.screenshot({ path: `${out}/team.png`, fullPage: true });
  await page.getByRole("link", { name: /Ver no dashboard/ }).click();
  await page.waitForURL(/\/time\//);
  await page.getByText("Pontos fortes").first().waitFor({ timeout: 60000 });
});

await step("a plan question opens the plan page already generated", async () => {
  await page.goto(WEB, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => sessionStorage.clear());
  await page.reload({ waitUntil: "domcontentloaded" });
  await ask(`plano do ${teamA} contra o ${teamB} no mapa ${map}`);
  await page.getByText("Rounds-chave do plano").waitFor({ timeout: 120000 });
  await page.screenshot({ path: `${out}/plan.png`, fullPage: true });
  await page.getByRole("link", { name: /Ver no dashboard/ }).click();
  await page.waitForURL(/\/plano\?/);
  await page.getByText("Linha do tempo da partida").waitFor({ timeout: 120000 });
});

await step("the conversation survives going to another page and back", async () => {
  await page.goBack();
  await page.getByText("Rounds-chave do plano").waitFor({ timeout: 10000 });
});

await step("a suggestion chip is optional and works when clicked", async () => {
  await page.getByRole("button", { name: "Nova conversa" }).click();
  await page.getByRole("button", { name: /^Resumo do campeonato$/ }).click();
  await page.getByRole("link", { name: /Ver campeonatos|Ver no dashboard/ }).waitFor({ timeout: 60000 });
});

await step("an unknown name gets an explanation, not silence", async () => {
  await ask("jogador xyzabcq");
  await page.getByText(/Não encontrei/).waitFor({ timeout: 30000 });
});

await step("no console errors", async () => { if (errors.length) throw new Error(errors.join(" | ")); });

await browser.close();
console.log(steps.join("\n"));
process.exit(steps.some((s) => s.startsWith("FAIL")) ? 1 : 0);
