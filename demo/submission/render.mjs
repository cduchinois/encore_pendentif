// Render demo/submission/slides.html to PNGs with headless Chromium.
// Usage: node render.mjs <slides.html> <outdir>
// Needs playwright-core (npm i playwright-core) and a Chromium binary,
// either autodetected via PLAYWRIGHT_BROWSERS_PATH or set with CHROMIUM_PATH.
import { chromium } from 'playwright-core';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const [htmlPath, outDir] = process.argv.slice(2);
if (!htmlPath || !outDir) { console.error('usage: node render.mjs <slides.html> <outdir>'); process.exit(1); }
fs.mkdirSync(outDir, { recursive: true });

const exe = process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const browser = await chromium.launch({ executablePath: exe });
const page = await browser.newPage({ viewport: { width: 2000, height: 1200 } });
await page.goto(pathToFileURL(path.resolve(htmlPath)).href, { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);

const n = await page.locator('.slide').count();
for (let i = 0; i < n; i++) {
  await page.locator('.slide').nth(i).screenshot({ path: path.join(outDir, `slide${i + 1}.png`) });
}

// Clean variant: no explanation text, phone centered.
await page.addStyleTag({ content: `
  .copy{display:none!important}
  .phone-wrap{right:50%!important;transform:translate(50%,-50%)!important}
  .brand{left:50%!important;transform:translateX(-50%)!important}
`});
for (let i = 0; i < n; i++) {
  await page.locator('.slide').nth(i).screenshot({ path: path.join(outDir, `slide${i + 1}_notext.png`) });
}

await browser.close();
console.log(`rendered ${n} slides x2 variants -> ${outDir}`);
