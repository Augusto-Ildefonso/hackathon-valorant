// Mobile check: every route at phone widths. Reports page-level horizontal overflow and the elements that stick out of the
// viewport, and saves a screenshot per route. Usage (make dev running):  node scripts/mobile-check.mjs [out-dir=mobile-shots] [width=390]
import { mkdirSync } from "node:fs";
import { chromium } from "playwright";

const WEB = process.env.WEB ?? "http://localhost:5173";
const API = process.env.API ?? "http://localhost:8000";
const out = process.argv[2] ?? "mobile-shots";
const width = Number(process.argv[3] ?? 390);
mkdirSync(out, { recursive: true });
const get = async (p) => (await fetch(`${API}${p}`)).json();

const lb = await get("/api/leaderboards");
const matches = (await get("/api/matches?limit=5")).items;
const player = lb.players.kd[0].player.puuid;
const team = matches[0].team_a.team.name;
const rival = matches[0].team_b.team.name;
const map = matches[0].map.name;
const enc = encodeURIComponent;
const routes = [
  ["/", "chat"], ["/campeonatos", "campeonatos"], ["/jogadores", "jogadores"], ["/times", "times"], ["/mapas", "mapas"], ["/partidas", "partidas"],
  [`/jogador/${enc(player)}`, "jogador"], [`/time/${enc(team)}`, "time"], [`/mapa/${enc(map)}`, "mapa"], [`/partida/${matches[0].match_id}`, "partida"],
  [`/plano?teamA=${enc(team)}&teamB=${enc(rival)}&map=${enc(map)}`, "plano"],
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height: 800 }, isMobile: true, hasTouch: true });
let bad = 0;
for (const [route, name] of routes) {
  await page.goto(WEB + route, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 120000 }).catch(() => {});
  await page.waitForTimeout(1500);
  const r = await page.evaluate((w) => {
    const doc = document.documentElement;
    const offenders = [];
    for (const el of document.body.querySelectorAll("*")) {
      const b = el.getBoundingClientRect();
      if (b.width === 0 || b.height === 0) continue;
      if (b.right > w + 1 && !el.closest("[data-scroll-x]") && !el.closest("svg")) {
        // ignore elements whose own scrolling ancestor clips them
        let p = el.parentElement, clipped = false;
        while (p && p !== document.body) {
          const cs = getComputedStyle(p);
          if (/(auto|scroll|hidden)/.test(cs.overflowX) && p.getBoundingClientRect().right <= w + 1) { clipped = true; break; }
          p = p.parentElement;
        }
        if (!clipped) offenders.push(`${el.tagName.toLowerCase()}.${String(el.className).split(" ").slice(0, 3).join(".")} right=${Math.round(b.right)}`);
      }
    }
    return { scrollW: doc.scrollWidth, offenders: offenders.slice(0, 6) };
  }, width);
  const over = r.scrollW > width + 1;
  if (over || r.offenders.length) bad++;
  console.log(`${over || r.offenders.length ? "BAD " : "ok  "} ${name.padEnd(12)} scrollWidth=${r.scrollW}${r.offenders.length ? "\n      " + r.offenders.join("\n      ") : ""}`);
  await page.screenshot({ path: `${out}/${name}.png`, fullPage: true });
}
// the drawer menu: closed by default, opens from the button, navigates and closes itself
await page.goto(WEB + "/", { waitUntil: "domcontentloaded" });
const nav = page.getByRole("navigation", { name: "Menu principal" });
let drawerOk = true;
try {
  if (await nav.isVisible()) throw new Error("menu is open on load");
  await page.getByRole("button", { name: "Abrir menu" }).click();
  await nav.waitFor({ state: "visible", timeout: 5000 });
  await nav.getByRole("link", { name: "Times" }).click();
  await page.waitForURL(/\/times$/);
  await nav.waitFor({ state: "hidden", timeout: 5000 });
  await page.getByRole("button", { name: "Abrir menu" }).click();
  await page.keyboard.press("Escape");
  await nav.waitFor({ state: "hidden", timeout: 5000 });
} catch (e) {
  drawerOk = false;
  console.log("BAD  drawer menu:", String(e.message).split("\n")[0]);
}
if (drawerOk) console.log("ok   drawer menu opens, navigates and closes");
else bad++;
await browser.close();
console.log(bad ? `\n${bad} route(s) overflow at ${width}px` : `\nall routes fit at ${width}px`);
process.exit(bad ? 1 : 0);
