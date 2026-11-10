/* 新版首頁冒煙測試（2026-11-11，首頁 index.html 換成新版；舊版的測試是 tests/smoke.js，跑 classic.html）。
   中文／英文 × 桌面／手機：首頁要載得出來、七頁都切得過去而且每頁有卡片、不能有 JS 錯誤、不能橫向捲動；
   另外檢查舊網址（#onchain/sthsig 這種）會轉到 classic.html。
   用法：先在倉庫根目錄起靜態伺服器（python3 -m http.server 8765），再執行 node tests/smoke_next.js。 */
const { chromium } = require(process.env.PW || 'playwright');
const ROOT = process.env.ROOT || 'http://localhost:8765/';
(async () => {
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}); let fail = 0;
  const bad = m => { console.log('✗ ' + m); fail++; };
  for (const lang of ['zh', 'en']) for (const w of [1280, 390]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 }, reducedMotion: 'reduce' });
    await ctx.addInitScript(l => { localStorage.setItem('daybreak.lang', l); }, lang);
    await ctx.route(/fonts\.(googleapis|gstatic)\.com|country\.is|geojs\.io/, r => r.abort());   // 測試不依賴外部字型與 IP 查詢
    const p = await ctx.newPage(); const errs = [];
    p.on('pageerror', e => errs.push(e.message));
    await p.goto(ROOT);
    await p.waitForFunction(() => document.querySelector('#oc-st .os.front') && document.querySelectorAll('#oc-secs .fc').length > 0, null, { timeout: 30000 });
    const got = await p.evaluate(() => (document.querySelector('#oc-lg [aria-pressed="true"]') || {}).dataset.l);
    if (got !== lang) bad(`${lang} ${w}px：語言按鈕停在 ${got}`);
    const nav = w >= 701 ? '#oc-crumb' : '#oc-tab', n = await p.$$eval(nav + ' [data-ch]', s => s.length); let cards = 0;
    for (let i = 0; i < n; i++) {
      await p.evaluate(([s, k]) => document.querySelector(s + ' [data-ch="' + k + '"]').click(), [nav, i]); await p.waitForTimeout(900);
      const st = await p.evaluate(() => ({ front: (document.querySelector('#oc-st .os.front') || {}).dataset?.k, fc: document.querySelectorAll('#oc-secs .fc').length, sw: document.documentElement.scrollWidth }));
      if (String(st.front) !== String(i)) bad(`${lang} ${w}px 第 ${i} 頁：前面那張是 ${st.front}`);
      if (!st.fc) bad(`${lang} ${w}px 第 ${i} 頁：沒有卡片`);
      if (st.sw > w + 1) bad(`${lang} ${w}px 第 ${i} 頁：橫向溢出 ${st.sw}px`);
      cards += st.fc;
    }
    errs.forEach(e => bad(`${lang} ${w}px JS 錯誤：${e}`));
    console.log(`${lang} ${w}px：${n} 頁、${cards} 張卡，錯誤 ${errs.length}`);
    if (lang === 'zh' && w === 1280) {
      await p.goto(ROOT + '#onchain/sthsig');
      await p.waitForFunction(() => location.pathname.indexOf('classic.html') >= 0 && document.querySelector('#view .pg'), null, { timeout: 30000 }).catch(() => bad('舊網址 #onchain/sthsig 沒有轉到 classic.html'));
      console.log('舊網址轉到：' + await p.evaluate(() => location.pathname + location.hash));
    }
    await ctx.close();
  }
  await b.close(); if (fail) { console.log(`共 ${fail} 個問題`); process.exit(1); } console.log('全部通過');
})().catch(e => { console.error(e); process.exit(1); });
