// Full-page screenshot of a route for visual comparison with Figma. Usage:
//   node scripts/shot.mjs <route> <out.png> [width=1440]   (dev server must be running: make dev)
import { chromium } from "playwright";

const [route = "/", out = "shot.png", width = "1440"] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: Number(width), height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
page.on("console", (m) => m.type() === "error" && errors.push(`console: ${m.text()}`));
await page.goto(`http://localhost:5173${route}`, { waitUntil: "networkidle" });
await page.waitForTimeout(500);
await page.screenshot({ path: out, fullPage: true });
await browser.close();
console.log(errors.length ? `ERRORS:\n${errors.join("\n")}` : "no console errors");
