// Smoke test: visits every route, asserts no console/page errors, no failed API calls, a key element on screen,
// no horizontal overflow and basic accessibility (images with alt, buttons/links with a name, one h1).
// Usage (make dev running):  npm run smoke            real backend (ids are discovered through the API)
//                            WEB=http://localhost:5174 npm run smoke   against another dev server (e.g. make dev-mock)
import { chromium } from "playwright";

const WEB = process.env.WEB ?? "http://localhost:5173";
const API = process.env.API ?? "http://localhost:8000";
const get = async (p) => (await fetch(`${API}${p}`)).json();

const lb = await get("/api/leaderboards");
const matches = (await get("/api/matches?limit=5")).items;
const player = lb.players.kd[0].player.puuid;
const team = matches[0].team_a.team.name;
const rival = matches[0].team_b.team.name;
const map = matches[0].map.name;

// [route, text that must be visible, timeout ms]
const routes = [
  ["/", "Pergunte ao VaváGym", 30000],
  ["/campeonatos", "Partidas recentes", 30000],
  ["/jogadores", "Jogadores", 30000],
  ["/times", "Times", 30000],
  ["/mapas", "Mapas", 30000],
  ["/partidas", "Partidas", 30000],
  [`/jogador/${encodeURIComponent(player)}`, "Pontos fortes", 60000],
  [`/time/${encodeURIComponent(team)}`, "Pontos fortes", 60000],
  [`/mapa/${encodeURIComponent(map)}`, "Pontos cegos", 60000],
  [`/partida/${matches[0].match_id}`, "Replay de abates", 60000],
  [`/plano?teamA=${encodeURIComponent(team)}&teamB=${encodeURIComponent(rival)}&map=${encodeURIComponent(map)}`, "Linha do tempo da partida", 120000],
];

const browser = await chromium.launch();
const failures = [];
for (const width of [1440, 1024]) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => m.type() === "error" && errors.push(`console: ${m.text()}`));
  page.on("response", (r) => r.url().includes("/api/") && r.status() >= 400 && errors.push(`http ${r.status()}: ${r.url()}`));
  for (const [route, text, timeout] of routes) {
    errors.length = 0;
    const problems = [];
    try {
      await page.goto(WEB + route, { waitUntil: "domcontentloaded" });
      await page.getByText(text, { exact: false }).first().waitFor({ timeout });
      await page.waitForLoadState("networkidle", { timeout: 20000 }).catch(() => {});
      const audit = await page.evaluate(() => {
        const name = (el) => (el.getAttribute("aria-label") || el.textContent || el.getAttribute("title") || "").trim();
        return {
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          noAlt: [...document.querySelectorAll("img")].filter((i) => !i.hasAttribute("alt")).length,
          unnamed: [...document.querySelectorAll("button,a[href]")].filter((e) => !name(e) && !e.querySelector("img[alt]:not([alt=''])")).length,
          h1: document.querySelectorAll("h1").length,
        };
      });
      if (audit.overflow > 1) problems.push(`horizontal overflow ${audit.overflow}px`);
      if (audit.noAlt) problems.push(`${audit.noAlt} <img> without alt`);
      if (audit.unnamed) problems.push(`${audit.unnamed} buttons/links without an accessible name`);
      if (audit.h1 !== 1) problems.push(`${audit.h1} <h1> (want 1)`);
    } catch (e) {
      problems.push(`not rendered: ${String(e.message).split("\n")[0]}`);
    }
    problems.push(...errors);
    const label = `${String(width).padEnd(4)} ${route.slice(0, 60)}`;
    console.log(problems.length ? `FAIL ${label}\n     - ${problems.join("\n     - ")}` : `ok   ${label}`);
    if (problems.length) failures.push(label);
  }
  await page.close();
}
await browser.close();
console.log(failures.length ? `\n${failures.length} route(s) with problems` : "\nall routes ok");
process.exit(failures.length ? 1 : 0);
