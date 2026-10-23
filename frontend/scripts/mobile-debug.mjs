// Prints the widest elements of one route at phone width: node scripts/mobile-debug.mjs <route> [width=390]
import { chromium } from "playwright";

const WEB = process.env.WEB ?? "http://localhost:5173";
const route = process.argv[2] ?? "/";
const width = Number(process.argv[3] ?? 390);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height: 800 }, isMobile: true });
await page.goto(WEB + route, { waitUntil: "domcontentloaded" });
await page.waitForLoadState("networkidle", { timeout: 120000 }).catch(() => {});
await page.waitForTimeout(1500);
const rows = await page.evaluate((w) => {
  const out = [];
  for (const el of document.body.querySelectorAll("*")) {
    const b = el.getBoundingClientRect();
    if (b.width && b.right > w + 1 && (!el.closest("[data-scroll-x]") || el.hasAttribute("data-scroll-x"))) out.push({ tag: el.tagName.toLowerCase(), cls: String(el.className).slice(0, 80), right: Math.round(b.right), text: (el.textContent ?? "").slice(0, 30) });
  }
  for (const el of document.body.querySelectorAll("*")) {  // content wider than its own box (text/children spilling out)
    if (el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0 && !el.closest("[data-scroll-x]")) out.push({ tag: el.tagName.toLowerCase(), cls: String(el.className).slice(0, 80), right: el.scrollWidth, text: "SPILL " + (el.textContent ?? "").slice(0, 30) });
  }
  return out.sort((a, b) => b.right - a.right).slice(0, 8);
}, width);
console.log(rows);
await browser.close();
