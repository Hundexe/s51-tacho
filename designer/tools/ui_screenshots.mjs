// Bildschirmfotos der Oberfläche für die Doku (docs/bilder/designer/).
//
// Startet nichts selbst: zuerst den Designer ohne Fenster starten,
//   python -m s51design --kein-fenster --port 8765
// dann mit der ausgegebenen Adresse:
//   node tools/ui_screenshots.mjs "<Adresse>" ../docs/bilder/designer
//
// Braucht das npm-Paket playwright-core und Chrome oder Chromium. Pfad zum
// Browser über die Umgebungsvariable CHROME (Standard: /usr/bin/google-chrome).
// Meldet Fehler aus der Seite und endet dann mit Code 1.

import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
let pw;
try { pw = require("playwright-core"); } catch (e) { pw = require("playwright"); }

const [url, out = "screenshots"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const browser = await pw.chromium.launch({ executablePath: process.env.CHROME || "/usr/bin/google-chrome" });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.stack || e.message));
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });

const shot = async (name) => {
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${out}/${name}.png` });
  console.log(`${out}/${name}.png`);
};
const clickDisplay = async (x, y) => {
  const box = await page.locator("#overlay").boundingBox();
  const z = box.width / 480;
  await page.mouse.click(box.x + x * z, box.y + y * z);
};

await page.goto(url);
await page.waitForTimeout(1500);
await shot("designer-start");

await clickDisplay(230, 150);
await shot("designer-eigenschaften");

await page.keyboard.press("Escape");
await page.locator(".page", { hasText: "Startbild" }).click();
await clickDisplay(240, 100);
await shot("designer-bild");

// Musikseite von „Klar“ mit ausgewählter Taste
await page.keyboard.press("Escape");
await page.locator("#page-list > .page", { hasText: "Musik" }).click();
await clickDisplay(240, 260);
await shot("designer-taste");

await page.keyboard.press("Control+n");
await page.waitForTimeout(800);
await shot("designer-vorlagen");
await page.locator(".card", { hasText: "Rennsport" }).click();
await page.waitForTimeout(500);
await page.locator(".page", { hasText: "Schräglage" }).click();
await clickDisplay(110, 130);
await shot("designer-schraeglage");

await page.locator('#toolbar button[data-tip="Tacho-Einstellungen"]').click();
await shot("designer-einstellungen");
await page.keyboard.press("Escape");

await page.locator('.toggle[data-tip^="Vorschau"]').click();
await shot("designer-vorschau");

// Weitere Bedienschritte ohne Bild: kopieren und einfügen, Seiten, Ebenen, Demo
await page.locator('.toggle[data-tip^="Vorschau"]').click();
await clickDisplay(240, 150);
await page.keyboard.press("Control+c");
await page.keyboard.press("PageUp");
await page.keyboard.press("Control+v");
await page.keyboard.press("Control+z");
await page.locator('#page-tools button[data-tip="Neue Seite"]').click();
await page.locator(".segctl button", { hasText: "Nacht" }).click();
await page.locator(".layer-list .layer").first().waitFor({ state: "attached" }).catch(() => {});
await page.locator('.tile', { hasText: "Text" }).click();
await page.locator('.layer .icon-btn[data-tip="Am Tacho ausblenden"]').first().click();
await page.locator('.toggle[data-tip^="Demo"]').click();
await page.waitForTimeout(600);
await page.keyboard.press("Control+z");
await page.keyboard.press("Control+y");
await shot("designer-bedienung");

await browser.close();
if (errors.length) {
  console.error("Fehler in der Seite:\n" + errors.join("\n"));
  process.exit(1);
}
