/* 破曉網站冒煙測試（2026-10-12）：中文／英文 × 桌面／手機，每一版都要能渲染、不能有 JS 錯誤、不能有「模組載入失敗」、不能橫向捲動。
   用法：先在倉庫根目錄起靜態伺服器（python3 -m http.server 8765），再執行 node tests/smoke.js。PW 環境變數可指定 playwright 模組路徑。 */
const { chromium } = require(process.env.PW || 'playwright');
const BASE = process.env.BASE || 'http://localhost:8765/';
(async () => {
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}); let fail = 0;
  for (const lang of ['zh', 'en']) for (const w of [1280, 390]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
    await ctx.addInitScript(l => { localStorage.setItem('daybreak.lang', l); }, lang);
    await ctx.route(/fonts\.(googleapis|gstatic)\.com|country\.is|geojs\.io/, r => r.abort());   // 測試不依賴外部字型與 IP 查詢
    const p = await ctx.newPage(); const errs = [];
    p.on('pageerror', e => errs.push(e.message));
    await p.goto(BASE); await p.waitForFunction(() => document.querySelector('#view .pg'), null, { timeout: 30000 }); await p.waitForTimeout(1500);
    const ids = await p.$$eval('#view .pg', s => s.map(x => x.id));
    for (const id of ids) {
      await p.evaluate(i => { location.hash = i.replace('pg-', ''); }, id); await p.waitForTimeout(1200);
      const sw = await p.evaluate(() => document.documentElement.scrollWidth);
      if (sw > w + 1) { console.log(`✗ ${lang} ${w}px ${id}: 橫向溢出 ${sw}px`); fail++; }
    }
    const bad = await p.$$eval('#view .err', es => es.map(e => e.textContent.slice(0, 80)));
    bad.forEach(t => { console.log(`✗ ${lang} ${w}px：${t}`); fail++; });
    errs.forEach(e => { console.log(`✗ ${lang} ${w}px JS 錯誤：${e}`); fail++; });
    console.log(`${lang} ${w}px：${ids.length} 個版面，錯誤 ${bad.length + errs.length}`);
    await ctx.close();
  }
  await b.close(); if (fail) { console.log(`共 ${fail} 個問題`); process.exit(1); } console.log('全部通過');
})().catch(e => { console.error(e); process.exit(1); });
