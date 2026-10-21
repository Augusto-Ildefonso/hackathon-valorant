// Round clicks must bring the round's section into view, never jump to the top. Usage (make dev running):
//   node scripts/test-round-click.mjs
import { chromium } from "playwright";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
page.on("console", (m) => m.type() === "error" && errors.push(`console: ${m.text()}`));
const top = (sel) => page.evaluate((s) => Math.round(document.querySelector(s).getBoundingClientRect().top), sel);
const settle = () => page.waitForTimeout(1500);

// ---- Action Plan
await page.goto("http://localhost:5173/plano?teamA=UFMT%20Turuna", { waitUntil: "networkidle" });
await page.getByText("Linha do tempo da partida").first().waitFor({ timeout: 120000 });
const chip = page.getByRole("button", { name: /^R5\b/ }).first();
await chip.click();
await settle();
console.log("plan, timeline chip R5 -> scrollY", await page.evaluate(() => Math.round(scrollY)), "| detail top in viewport", await top("#plano-round-detalhe"),
  "| title:", (await page.locator("#plano-round-detalhe").innerText()).split("\n")[0]);
await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
await page.waitForTimeout(500);
await page.locator("div.cursor-pointer.border-b").nth(3).scrollIntoViewIfNeeded();
await page.locator("div.cursor-pointer.border-b").nth(3).click();   // table row for round 4
await settle();
console.log("plan, table row 4 -> scrollY", await page.evaluate(() => Math.round(scrollY)), "| detail top in viewport", await top("#plano-round-detalhe"),
  "| title:", (await page.locator("#plano-round-detalhe").innerText()).split("\n")[0]);

// ---- Match report
const mid = process.env.MATCH ?? "9050596f-5a36-4554-a002-d7bbe68fccac";
await page.goto(`http://localhost:5173/partida/${mid}`, { waitUntil: "networkidle" });
await page.getByText("Replay de abates").first().waitFor({ timeout: 120000 });
await page.evaluate(() => window.scrollTo(0, 0));
const rb = page.locator("button", { hasText: /^R?7$|^7$/ }).first();
const timelineChip = page.locator("button").filter({ hasText: /^7/ }).first();
await timelineChip.click();
await settle();
console.log("match, timeline round 7 -> scrollY", await page.evaluate(() => Math.round(scrollY)), "| replay top in viewport", await top("#partida-replay"));
console.log(errors.length ? `ERRORS:\n${errors.join("\n")}` : "no console errors");
await browser.close();
