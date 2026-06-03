// Headless-browser screenshot capture for the MetricLens dashboard.
//
// Drives a running instance of the frontend (default http://localhost:4173,
// i.e. `vite preview`) with Playwright/Chromium and writes PNGs to
// ./docs/screenshots/. The dashboard falls back to deterministic demo data when
// no backend is configured, so captures are reproducible in CI.
//
// Usage:
//   SCREENSHOT_URL=http://localhost:4173 node scripts/capture_screenshots.js

import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { mkdirSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = join(__dirname, '..', 'docs', 'screenshots');
const BASE_URL = process.env.SCREENSHOT_URL || 'http://localhost:4173';

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  // Allow the ECharts canvases to finish their first paint.
  await page.waitForSelector('canvas');
  await page.waitForTimeout(800);

  await page.screenshot({ path: join(OUT_DIR, 'dashboard_overview.png'), fullPage: true });

  // Per-host views to exercise the selector and the recommendation card.
  const tabs = await page.$$('.host-tabs .tab');
  for (let i = 0; i < tabs.length; i += 1) {
    await tabs[i].click();
    await page.waitForTimeout(600);
    await page.screenshot({
      path: join(OUT_DIR, `dashboard_host_${i + 1}.png`),
      fullPage: true,
    });
  }

  await browser.close();
  console.log(`Captured ${tabs.length + 1} screenshots to ${OUT_DIR}`);
}

main().catch((err) => {
  console.error('Screenshot capture failed:', err);
  process.exit(1);
});
