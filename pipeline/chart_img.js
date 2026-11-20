/* 每張圖的靜態小圖（2026-11-20 GEO，使用者：「加靜態小圖」）。
   用網站自己的分享模式（/app/?share&k=…，16:9、字級放大、頁尾有網站名、資料來源和日期）截每張圖，中英各一張，
   給 charts/<k>/ 這些單頁放在表態下面，也當那一頁的 og:image（分享出去有圖）。
   用法：先在倉庫根目錄起靜態伺服器（python3 -m http.server 8765），再
        python3 pipeline/next/pages.py --img-list > list.json
        node pipeline/chart_img.js list.json <輸出資料夾>        → <輸出>/zh/<k>.jpg、<輸出>/en/<k>.jpg、<輸出>/sizes.json（每張的寬高）
   每天日報上線後由 chart-img.yml 跑，打包放在 Release「chart-img」，部署時（cloudflare.yml）下載回 charts-img/，不進程式庫。
   截不出來的圖印出來略過（那一頁就沒有小圖），超過一半失敗才算整批失敗。 */
const fs = require('fs'), path = require('path');
const { chromium } = require(process.env.PW || 'playwright');
const ROOT = process.env.ROOT || 'http://localhost:8765/app/';
const [, , listFile, outDir] = process.argv;
const KS = JSON.parse(fs.readFileSync(listFile, 'utf8'));
const W = 1600, H = 900, DPR = 0.75;   // 分享模式固定 1600×900；輸出 1200×675，頁面上最寬 760px，手機 2 倍螢幕也夠清楚
const CONC = 4;

(async () => {
  const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
  let ok = 0, bad = 0; const t0 = Date.now(), sizes = {};
  for (const lang of ['zh', 'en']) {
    fs.mkdirSync(path.join(outDir, lang), { recursive: true });
    const ctx = await b.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: DPR, reducedMotion: 'reduce' });
    await ctx.addInitScript(l => { try { localStorage.setItem('daybreak.lang', l); } catch (e) {} }, lang);
    await ctx.route(/country\.is|geojs\.io/, r => r.abort());   // 不查 IP（語言已經指定）
    const queue = KS.slice();
    const worker = async () => {
      const p = await ctx.newPage();
      for (let k; (k = queue.shift());) {
        try {
          await p.goto(ROOT + '?share&k=' + encodeURIComponent(k) + '&lang=' + lang, { waitUntil: 'load', timeout: 45000 });
          const q = '#oc-fx.on #oc-olF[data-ck="' + k + '"]';
          await p.waitForFunction(q => { const e = document.querySelector(q); return !!(e && e.querySelector('svg,canvas,.rl') && (!document.fonts || document.fonts.status === 'loaded')); }, q, { timeout: 30000 });
          await p.waitForTimeout(1200);   // 動畫已關，等最後一輪排版和字型
          // 清單型的卡（Pi Cycle、頂部雷達這種幾條長條）內容只佔上半，下面整片空白：照頁尾（網站名那一行）的位置往下裁
          const bot = await p.evaluate(q => { const e = document.querySelector(q + ' .ol-brand'); return e ? e.getBoundingClientRect().bottom : 0; }, q);
          const ch = bot && bot < H - 80 ? Math.ceil(bot + 22) : H;
          await p.screenshot({ path: path.join(outDir, lang, k + '.jpg'), type: 'jpeg', quality: 80, clip: { x: 0, y: 0, width: W, height: ch } });
          sizes[lang + '/' + k] = [Math.round(W * DPR), Math.round(ch * DPR)];
          ok++;
        } catch (e) { bad++; console.log(`✗ ${lang} ${k}: ${String(e.message || e).split('\n')[0]}`); }
      }
      await p.close();
    };
    await Promise.all(Array.from({ length: CONC }, worker));
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync(path.join(outDir, 'sizes.json'), JSON.stringify(sizes));   // pages.py 用來寫 <img> 的寬高
  console.log(`chart images: ${ok} ok, ${bad} failed, ${Math.round((Date.now() - t0) / 1000)} s`);
  process.exit(bad > ok ? 1 : 0);
})();
