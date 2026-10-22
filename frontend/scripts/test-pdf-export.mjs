// "Exportar PDF" on the Action Plan must download a real PDF (text-first dossier), not open the print dialog. Usage (make dev running):
//   node scripts/test-pdf-export.mjs [out.pdf]
import { statSync } from "node:fs";
import { chromium } from "playwright";

const out = process.argv[2] ?? "plano.pdf";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
const errors = [];
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
page.on("console", (m) => m.type() === "error" && errors.push(`console: ${m.text()}`));
await page.goto("http://localhost:5173/plano?teamA=UFMT%20Turuna", { waitUntil: "domcontentloaded" });
await page.getByText("Linha do tempo da partida").first().waitFor({ timeout: 120000 });
await page.getByRole("button", { name: "Exportar PDF" }).scrollIntoViewIfNeeded();
await page.waitForTimeout(300);
const scrollBefore = await page.evaluate(() => Math.round(scrollY));
const [download] = await Promise.all([page.waitForEvent("download", { timeout: 300000 }), page.getByRole("button", { name: "Exportar PDF" }).click()]);
console.log("busy label shown:", await page.getByRole("button", { name: /Gerando PDF/ }).count() > 0 || "(already finished)");
await download.saveAs(out);
await page.waitForTimeout(500);
console.log("downloaded:", download.suggestedFilename(), statSync(out).size, "bytes | scroll kept:", scrollBefore === (await page.evaluate(() => Math.round(scrollY))));
console.log("button back to normal:", await page.getByRole("button", { name: "Exportar PDF" }).count() === 1);
console.log(errors.length ? `ERRORS:\n${errors.join("\n")}` : "no console errors");
await browser.close();
