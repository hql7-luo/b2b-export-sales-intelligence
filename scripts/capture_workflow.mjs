/** Capture the current UI against a disposable, seeded fictional database.
 * Start Streamlit as described in docs/visuals/README.md before running this.
 */
import { mkdir, writeFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(root, 'docs/visuals/sources');
await mkdir(output, { recursive: true });
const baseURL = process.env.B2B_CAPTURE_URL || 'http://127.0.0.1:8514';
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, deviceScaleFactor: 1 });
const page = await context.newPage();
const captures = [];

async function settled() {
  await page.locator('[data-testid="stApp"] [data-testid="stSpinner"]').waitFor({ state: 'hidden' });
  await page.waitForTimeout(700); // Let Streamlit finish laying out charts and dataframes.
  const errors = page.locator('[data-testid="stException"]');
  if (await errors.count()) throw new Error(await errors.first().innerText());
}

async function section(name, anchor, height) {
  await anchor.evaluate((element) => {
    element.scrollIntoView({ block: 'start' });
    const scrollArea = element.closest('[data-testid="stMain"]');
    if (scrollArea) scrollArea.scrollTop = Math.max(0, scrollArea.scrollTop - 90);
  });
  await settled();
  const bounds = await anchor.boundingBox();
  const main = await page.locator('[data-testid="stMainBlockContainer"]').boundingBox();
  if (!bounds || !main) throw new Error(`Missing section: ${name}`);
  const top = Math.max(0, bounds.y - 8);
  const clip = { x: main.x, y: top, width: main.width, height: Math.min(height, 1048 - top) };
  await page.screenshot({ path: path.join(output, `${name}.png`), clip });
  captures.push({ file: `sources/${name}.png`, urlPath: new URL(page.url()).pathname, clip });
}

try {
  await page.goto(baseURL, { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: 'Analyze Inquiry', exact: true }).waitFor();
  await settled();

  // Capture aggregate analytics before adding a walkthrough inquiry/quotation.
  await page.getByRole('link', { name: 'Analytics', exact: true }).click();
  await page.getByRole('heading', { name: 'Analytics', exact: true }).waitFor();
  await page.locator('.js-plotly-plot').first().waitFor();
  await settled();
  await section('analytics', page.getByRole('heading', { name: 'Analytics', exact: true }), 870);

  await page.getByRole('link', { name: 'Analyze Inquiry', exact: true }).click();
  await page.getByRole('button', { name: 'Load fictional demo inquiry', exact: true }).click();
  await page.getByRole('textbox', { name: 'English inquiry or RFQ *', exact: true }).waitFor();
  await settled();
  await section('inquiry', page.locator('[data-testid="stTextArea"]').first(), 285);
  await page.getByRole('button', { name: 'Analyze requirements', exact: true }).click();
  await page.getByRole('heading', { name: 'Request summary', exact: true }).waitFor();
  await settled();
  await section('analysis', page.getByRole('heading', { name: 'Request summary', exact: true }), 410);

  await page.getByRole('heading', { name: 'Customer record', exact: true }).waitFor();
  await section('customer', page.getByRole('heading', { name: 'Customer record', exact: true }), 290);
  await page.getByRole('button', { name: 'Save inquiry', exact: true }).click();
  await page.getByRole('button', { name: 'Prepare quotation', exact: true }).click();
  await page.getByRole('heading', { name: 'Inherited quotation context', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Calculate quotation', exact: true }).click();
  await page.getByRole('heading', { name: 'Quotation result · Gross Margin', exact: true }).waitFor();
  await settled();
  await section('quotation', page.getByRole('heading', { name: 'Quotation result · Gross Margin', exact: true }), 410);
  await page.getByRole('button', { name: 'Save quotation', exact: true }).click();
  await page.getByRole('button', { name: 'Add follow-up', exact: true }).click();
  await page.getByRole('tab', { name: 'Record follow-up', exact: true }).click();
  await page.getByRole('heading', { name: 'Inherited follow-up context', exact: true }).waitFor();
  await settled();
  await section('followup', page.getByRole('heading', { name: 'Inherited follow-up context', exact: true }), 445);

  await writeFile(path.join(root, 'docs/visuals/capture-manifest.json'), JSON.stringify({
    sourceCommit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
    capturedAt: new Date().toISOString(),
    viewport: { width: 1440, height: 1050 },
    data: 'Fictional bundled seed data plus the built-in fictional inquiry; no API key. Analytics was captured before walkthrough writes.',
    processing: 'Unaltered UI crops; the montage only scales and lays out these images.',
    captures,
  }, null, 2) + '\n');
} finally {
  await context.close();
  await browser.close();
}
