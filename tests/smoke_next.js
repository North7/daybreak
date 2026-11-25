/* 首頁冒煙測試（2026-11-11 首頁 index.html 換成新版；舊版 classic.html 和它的 tests/smoke.js 2026-11-17 已刪除）。
   中文／英文 × 桌面／手機：首頁要載得出來、七頁都切得過去而且每頁有卡片、不能有 JS 錯誤、不能橫向捲動；
   另外檢查舊網址（#onchain/sthsig 這種）會轉到新版對應的圖（2026-11-16 起，規則 ㉝），以及分享模式（?share&k=oih）。
   2026-11-25 加簡體（hans）：每一頁畫完後畫面上不能留常見的繁體字（assets/hans.js 沒轉到的），切回繁體要換得回來；介紹頁（根目錄）也開一次簡體。
   用法：先在倉庫根目錄起靜態伺服器（python3 -m http.server 8765），再執行 node tests/smoke_next.js。 */
const { chromium } = require(process.env.PW || 'playwright');
const ROOT = process.env.ROOT || 'http://localhost:8765/app/';   // 2026-11-20 數據頁搬到 /app/
(async () => {
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {}); let fail = 0;
  const bad = m => { console.log('✗ ' + m); fail++; };
  /* 畫面上（不含語言鈕、給爬蟲的文字版）有幾段字含常見的繁體字／簡體字 */
  const TR = '們這說來為與個對時會後過還麼點買賣價圖頁週鏈線資數據從開關體單幣讀維訊號', SM = '们这说来为与个对时会后过还么点买卖价图页周链线资数据从开关体单币读维讯号';
  const count = (p, chars) => p.evaluate(cs => { const re = new RegExp('[' + cs + ']'), w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT), out = []; let n; while ((n = w.nextNode())) { const pe = n.parentElement; if (!pe || pe.closest('script,style,[data-nohans],#oc-static,#seo-static,#lgs,#oc-lg')) continue; if (re.test(n.nodeValue)) out.push(n.nodeValue.slice(0, 40)); } return out; }, chars);
  for (const lang of ['zh', 'en', 'hans']) for (const w of [1280, 390]) {
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
      const st = await p.evaluate(() => ({ front: (document.querySelector('#oc-st .os.front') || {}).dataset?.k, fc: document.querySelectorAll('#oc-secs .fc, #oc-secs .fr').length,   /* ㉞ 手機上收成清單列的圖也算 */ sw: document.documentElement.scrollWidth }));
      if (String(st.front) !== String(i)) bad(`${lang} ${w}px 第 ${i} 頁：前面那張是 ${st.front}`);
      if (!st.fc) bad(`${lang} ${w}px 第 ${i} 頁：沒有卡片`);
      if (st.sw > w + 1) bad(`${lang} ${w}px 第 ${i} 頁：橫向溢出 ${st.sw}px`);
      if (lang === 'hans') { const left = await count(p, TR); if (left.length) bad(`hans ${w}px 第 ${i} 頁：還有 ${left.length} 段繁體字，例如「${left[0]}」`); }
      cards += st.fc;
    }
    errs.forEach(e => bad(`${lang} ${w}px JS 錯誤：${e}`));
    console.log(`${lang} ${w}px：${n} 頁、${cards} 張卡，錯誤 ${errs.length}`);
    if (lang === 'hans' && w === 1280) {   // 簡體 → 繁體：被轉過的字要換回來
      await p.evaluate(() => document.querySelector('#oc-lg [data-l="zh"]').click()); await p.waitForTimeout(1500);
      const left = await count(p, SM.replace(/[讯号]/g, ''));
      if (left.length) bad(`簡體切回繁體後還有 ${left.length} 段簡體字，例如「${left[0]}」`);
      if (await p.evaluate(() => document.documentElement.lang) !== 'zh-Hant') bad('簡體切回繁體後 <html lang> 不是 zh-Hant');
      const e0 = errs.length; await p.goto(ROOT.replace(/app\/$/, '') + '?intro&lang=hans');   // 介紹頁
      await p.waitForFunction(() => document.getElementById('lgs') && document.getElementById('lgs').dataset.i === '1', null, { timeout: 30000 }).catch(() => bad('介紹頁 ?lang=hans 沒有切到简'));
      const il = await count(p, TR); if (il.length) bad(`介紹頁簡體還有 ${il.length} 段繁體字，例如「${il[0]}」`);
      errs.slice(e0).forEach(e => bad(`介紹頁簡體 JS 錯誤：${e}`));
      console.log('簡體切回繁體、介紹頁簡體：' + (left.length + il.length ? '有問題' : '通過'));
    }
    if (lang === 'zh' && w === 1280) {
      await p.goto(ROOT + '?from=post#onchain/sthsig');   // 從貼文點進來是整頁載入（只換 # 的話是同一頁裡跳，另由 hashchange 處理）
      // 2026-11-16 舊版對外下線（規則 ㉝）：舊網址轉到新版對應的那張圖（?k=sthsig），原本的參數（from）保留、# 拿掉，那張圖的放大檢視要打開
      await p.waitForFunction(() => /[?&]k=sthsig\b/.test(location.search) && /[?&]from=post\b/.test(location.search) && !location.hash && document.querySelector('#oc-fx.on #oc-olF[data-ck="sthsig"]'), null, { timeout: 30000 }).catch(() => bad('舊網址 #onchain/sthsig 沒有轉到新版的 sthsig'));
      console.log('舊網址轉到：' + await p.evaluate(() => location.pathname + location.search + location.hash));
      // 分享模式（2026-11-11）：?share&k=圖代號 直接打開那張圖，頁尾要看得到，座標函式要能用
      const e0 = errs.length;
      await p.goto(ROOT + '?share&k=oih');
      await p.waitForFunction(() => !document.getElementById('oc-fx').hidden && document.querySelector('#oc-olF .ol-c svg'), null, { timeout: 30000 }).catch(() => bad('分享模式沒有打開 oih'));
      const sh = await p.evaluate(() => { const b = document.querySelector('#oc-olF .ol-brand'), r = b && b.getBoundingClientRect(), xy = window.daybreakXY && window.daybreakXY('oih'); return { brand: !!(r && r.height > 0 && r.bottom <= innerHeight + 1), xy: !!(xy && xy.x > 0 && xy.ticks && xy.ticks.length >= 3), view: !!document.querySelector('#oc-olF .sy-view:not([hidden])') && getComputedStyle(document.querySelector('#oc-olF .sy-view') || document.body).display !== 'none' }; });
      if (!sh.brand) bad('分享模式：頁尾（網站名、資料來源、日期）不在畫面內');
      if (!sh.xy) bad('分享模式：daybreakXY 沒有回傳座標或刻度');
      if (sh.view) bad('分享模式：「我們的看法」沒有藏起來');
      if (await p.$$eval('.fc[data-k]', a => a.length) === 0 && await p.$$eval('#oc-olF[data-ck="oih"]', a => a.length) === 0) bad('卡片上沒有圖代號');
      errs.slice(e0).forEach(e => bad(`分享模式 JS 錯誤：${e}`));
      console.log('分享模式：' + JSON.stringify(sh));
    }
    await ctx.close();
  }
  await b.close(); if (fail) { console.log(`共 ${fail} 個問題`); process.exit(1); } console.log('全部通過');
})().catch(e => { console.error(e); process.exit(1); });
