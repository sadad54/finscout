import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(20000);
  await mkdir('screenshots', { recursive: true });
  let fail = false;
  await page.route('http://localhost:8000/**', async route => {
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers: {
      'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST, GET, OPTIONS',
      'access-control-allow-headers': 'content-type',
    }});
    if (route.request().url().endsWith('/health')) return route.fulfill({json:{status:'ok'}});
    const events = fail ? [{type:'error', detail:'Fixture provider unavailable'}] : [
      {type:'stage',stage:'news',status:'done',result:[]},
      {type:'final',markdown:'# Fixture demo report\n\nNo live market data. Filing evidence unavailable; no claims inferred.'},
    ];
    await route.fulfill({ contentType: 'text/event-stream', headers: {'access-control-allow-origin':'*'},
      body: events.map(e => `data: ${JSON.stringify(e)}\n\n`).join('') });
  });
  await page.goto('http://localhost:3000/research');
  await page.getByPlaceholder('Ticker, e.g. AAPL').fill('AAPL');
  await page.getByPlaceholder('Company, e.g. Apple Inc.').fill('Apple');
  await page.getByRole('button', {name:'Generate',exact:true}).click();
  await page.getByText('Fixture demo report', {exact:true}).waitFor();
  await page.screenshot({path:'screenshots/fixture-report.png',fullPage:true});
  fail = true;
  await page.getByRole('button', {name:'Generate',exact:true}).click();
  await page.getByText('Fixture provider unavailable', {exact:true}).waitFor();
  await page.screenshot({path:'screenshots/fixture-error.png',fullPage:true});
  console.log('Fixture research and error rendering passed; no live providers called');
} finally { await browser.close(); }
