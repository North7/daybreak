/* 破曉 Daybreak — 前端（無外部套件）。讀 data/site.json（每日資料管線；和 latest.json 內容相同、較小，見 unpack()）與 data/notes.json（每日結論）。 */
(window.DAYBREAK_BOOT || Promise.resolve()).then(function () {
  'use strict';
  var D = null, N = null, H = [], ZH_ONLY = false, HELD = null;   // HELD：新數字已到、判讀還沒寫好，暫時整期顯示上一份（2026-11-06）
  /* 語言（2026-10-12）：index.html 的開機腳本先決定語言（使用者選過→沿用；沒選過→依 IP 國家，華語地區用中文；查不到看瀏覽器語言），
     英文時載入 assets/i18n-en.js（中文原句 → 英文）。_t：字典翻譯，缺字回傳中文；_T：直接給兩種語言；tx：資料欄位的 *_en 版本 */
  var LANG = window.DAYBREAK_LANG === 'en' ? 'en' : 'zh', EN = window.DAYBREAK_EN || {};
  function _t(s) { return LANG === 'en' && EN[s] != null ? EN[s] : s; }
  function _T(zh, en) { return LANG === 'en' ? en : zh; }
  function tx(o, k) { return !o ? '' : LANG === 'en' && o[k + '_en'] ? o[k + '_en'] : o[k]; }
  function ord(n) { n = Math.round(n); var v = n % 100; return n + ((v > 10 && v < 14) ? 'th' : ['th', 'st', 'nd', 'rd'][n % 10] || 'th'); }
  /* 顆數：中文以「萬顆」、英文以「K BTC」 */
  function venue(s) { return LANG === 'en' ? String(s || '').replace(' 永續', ' perp') : s; }   // 掛單簿場所名（管線寫「永續」）
  function coins(x, d) { return LANG === 'en' ? fmt.n(x / 1e3, d == null ? 0 : d) + 'K BTC' : fmt.n(x / 1e4, d == null ? 0 : d) + ' 萬顆'; }
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var fmt = {
    n: function (v, d) { return v == null || isNaN(v) ? '—' : (+v).toLocaleString('en-US', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); },
    usd: function (v) { return v == null ? '—' : '$' + fmt.n(v); },
    k: function (v) { return v == null ? '—' : (Math.abs(v) >= 1000 ? (v / 1000).toFixed(v % 1000 ? 1 : 0) + 'K' : fmt.n(v)); },
    pct: function (v, d) { return v == null ? '—' : (v > 0 ? '+' : '') + (+v).toFixed(d == null ? 1 : d) + '%'; },
    date: function (dn) { var t = new Date(dn * 864e5); return t.getUTCFullYear() + '/' + ('0' + (t.getUTCMonth() + 1)).slice(-2) + '/' + ('0' + t.getUTCDate()).slice(-2); },
    md: function (s) { return s ? (+s.slice(5, 7)) + '/' + (+s.slice(8, 10)) : '—'; }
  };
  var dnOf = function (s) { return Math.round(Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)) / 864e5); };
  var css = function (v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); };
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var MQ = window.matchMedia('(max-width: 860px)');   // 行動版：導航橫排
  try { history.scrollRestoration = 'manual'; } catch (e) {}   // 由網址決定開在哪一版，不沿用瀏覽器記住的捲動位置

  /* ---------------- Tooltip ---------------- */
  var tip = null;
  function showTip(x, y, html) {
    if (!tip) tip = $('#tip');
    tip.innerHTML = html; tip.hidden = false;
    var w = tip.offsetWidth, h = tip.offsetHeight, vw = innerWidth, vh = innerHeight;
    var left = x + 16, top = y + 14;
    if (left + w > vw - 8) left = x - w - 16;
    if (top + h > vh - 8) top = y - h - 14;
    tip.style.left = Math.max(8, left) + 'px'; tip.style.top = Math.max(8, top) + 'px';
  }
  function hideTip() { if (tip) tip.hidden = true; }
  /* 2026-11-09：手機上點了圖、提示框出現後一捲動就卡在畫面上（只有離開圖表才收）。捲動、觸控被瀏覽器接手（pointercancel）、
     點到圖表以外的地方時收起；桌面滑鼠移回圖上會再出現 */
  window.addEventListener('scroll', function () { if (tip && !tip.hidden) hideTip(); }, { passive: true });
  document.addEventListener('pointercancel', hideTip, true);
  document.addEventListener('pointerdown', function (e) { if (e.pointerType !== 'mouse' && !(e.target.closest && e.target.closest('svg, canvas, a.term'))) hideTip(); }, true);

  /* ---------------- Chart kit ---------------- */
  var mounted = [];
  var langInHook = null;   // 2026-11-09 換語言轉場的進場（shell() 裡定義，資料畫好後呼叫）
  /* 2026-11-04 自我檢查：一張圖出錯只影響自己——原本同一版的圖依序畫，前面一張丟錯，後面全部空白。
     出錯的那一張顯示說明（class 帶 err，冒煙測試會抓到），其他照畫 */
  function chartErr(el, e) { console.error(e); if (el) el.innerHTML = '<p class="err chart-err">' + _T('這張圖今天畫不出來（資料格式異常），其他圖不受影響。', 'This chart could not be drawn today (unexpected data); other charts are unaffected.') + '</p>'; }
  // 2026-11-05：最新一點的心跳只在圖進到畫面時才跑（全站約 35 張圖同時跳會讓整頁一直重畫，手機捲動明顯變卡）
  var scT; window.addEventListener('scroll', function () { document.documentElement.classList.add('scrolling'); clearTimeout(scT); scT = setTimeout(function () { document.documentElement.classList.remove('scrolling'); }, 250); }, { passive: true });   // 捲動中先停心跳（發光線＋動畫一起重畫很貴），停下來再跳
  var pulseIO = 'IntersectionObserver' in window ? new IntersectionObserver(function (es) { es.forEach(function (e) { e.target.classList.toggle('inview', e.isIntersecting); }); }) : null;
  function mount(el, draw) { if (!el) return; el._draw = function (e) { try { draw(e); } catch (er) { chartErr(e, er); } try { lgAfter(e); } catch (er) {} }; mounted.push(el); if (pulseIO && !el._io) { el._io = 1; pulseIO.observe(el); } el._draw(el); }
  /* 不經 mount 的繪圖（自己找元素、綁按鈕）：個別包起來，出錯只記錄、不中斷同一版其他圖 */
  function safe() { for (var i = 0; i < arguments.length; i++) { try { arguments[i](); } catch (e) { console.error(e); } } }
  var ro = window.ResizeObserver ? new ResizeObserver(function (es) {
    es.forEach(function (e) { var el = e.target; if (el._w !== el.clientWidth && el._draw) { el._w = el.clientWidth; el._draw(el); } });
  }) : null;
  /* 2026-11-04：換到解析度不同的螢幕（devicePixelRatio 變了）時，canvas 圖重畫，不然會糊；寬度沒變 ResizeObserver 不會觸發 */
  (function watchDpr() {
    if (!window.matchMedia) return; var mq = window.matchMedia('(resolution: ' + (window.devicePixelRatio || 1) + 'dppx)');
    var f = function () { mounted.forEach(function (el) { if (el._draw && el.querySelector('canvas')) el._draw(el); }); watchDpr(); };
    if (mq.addEventListener) mq.addEventListener('change', f, { once: true });
  })();
  function observe(el) { if (ro && el) { el._w = el.clientWidth; ro.observe(el); } }

  function niceStep(span, n) { var r = span / n, p = Math.pow(10, Math.floor(Math.log10(r))), m = r / p; return (m < 1.5 ? 1 : m < 3.5 ? 2 : m < 7.5 ? 5 : 10) * p; }
  /* 圖上標註文字的大約寬度（reflab 11px：中日韓字約 11px、其他約 6.3px），用來避免重疊 */
  /* 2026-11-04 → 2026/11/04（原本五個讀值函式各寫一份） */
  function ymdS(d) { return String(d).replace(/-/g, '/'); }
  /* 圖上的軸文字（原本各圖各寫一個區域 tx，蓋過模組層的 tx(o, k)） */
  function axText(xx, y, t, a, cls) { return '<text class="' + (cls || 'ax') + '" x="' + xx.toFixed(1) + '" y="' + y.toFixed(1) + '"' + (a ? ' text-anchor="' + a + '"' : '') + '>' + esc(t) + '</text>'; }
  function lblW(t) { var w = 0; String(t).replace(/[\s\S]/g, function (c) { w += /[\u2e80-\uffef]/.test(c) ? 11 : 6.3; }); return w; }
  function svgEl(W, Ht, inner, label) { return '<svg viewBox="0 0 ' + W + ' ' + Ht + '" width="' + W + '" height="' + Ht + '" role="img" aria-label="' + esc(label || '') + '">' + inner + '</svg>'; }
  function bisect(a, x) { var lo = 0, hi = a.length - 1; while (hi - lo > 1) { var m = (lo + hi) >> 1; if (a[m][0] < x) lo = m; else hi = m; } return Math.abs(a[lo][0] - x) <= Math.abs(a[hi][0] - x) ? lo : hi; }
  function animateLines(el) {
    // 2026-11-05：畫的時候圖還藏著（例如手機上收在「展開其餘」後面的小圖）就不套描線動畫：
    //   藏著時動畫不會跑，線會停在看不見的狀態，只剩最後一點（截圖工具直接截這種圖時就是空的）
    if (reduced || el._drawn || el.offsetParent === null) return; el._drawn = true;
    // 2026-10-14：虛線（推測、還沒發生的部分）不套描線動畫，動畫的 stroke-dasharray 會蓋掉虛線樣式、讓它變成實線
    // 2026-11-05：描線跑完就拿掉 draw class。否則圖之後被藏起來再顯示（截圖工具 captureBeyondViewport 會暫時改視窗大小、
    //   視窗跨過 860px 再拉回）動畫會從頭重播，桌面版「展開其餘」那幾張小圖在截圖裡只剩最後一點
    el.querySelectorAll('path.ln:not([stroke-dasharray])').forEach(function (p) { try { var L = p.getTotalLength(); p.style.setProperty('--len', L); p.classList.add('draw'); p.addEventListener('animationend', function () { p.classList.remove('draw'); p.style.removeProperty('--len'); }, { once: true }); } catch (e) {} });
  }

  /* 折線／面積圖：x 為日期序號（天）或數值；可對數 y；參考線、區段、標記；十字線 tooltip */
  // 2026-10-23：單調三次曲線（Fritsch–Carlson），通過每個節點、不會衝過節點（頂部不會被畫得比預測高）
  function smoothPath(xy) {
    var n = xy.length, dx = [], m = [], t = [];
    for (var i = 0; i < n - 1; i++) { dx.push(xy[i + 1][0] - xy[i][0]); m.push((xy[i + 1][1] - xy[i][1]) / (dx[i] || 1)); }
    t[0] = m[0]; t[n - 1] = m[n - 2];
    for (i = 1; i < n - 1; i++) t[i] = m[i - 1] * m[i] <= 0 ? 0 : 3 * (dx[i - 1] + dx[i]) / ((2 * dx[i] + dx[i - 1]) / m[i - 1] + (dx[i] + 2 * dx[i - 1]) / m[i]);
    var d = 'M' + xy[0][0].toFixed(1) + ',' + xy[0][1].toFixed(1);
    for (i = 0; i < n - 1; i++) { var h = dx[i] / 3; d += 'C' + (xy[i][0] + h).toFixed(1) + ',' + (xy[i][1] + t[i] * h).toFixed(1) + ' ' + (xy[i + 1][0] - h).toFixed(1) + ',' + (xy[i + 1][1] - t[i + 1] * h).toFixed(1) + ' ' + xy[i + 1][0].toFixed(1) + ',' + xy[i + 1][1].toFixed(1); }
    return d;
  }
  /* 時間範圍切換（2026-11-04 整體審查）：歷史超過約兩年的日期折線圖，右上角一律有「1 年／3 年／全部」，預設全部（維持原本的樣子）。
     圖本身已經有自己的切換（.seg）、寬度不到 420px 或 x 不是日期的不加。選擇記在元素上，重畫時沿用 */
  var RNG = [[365, '1 年', '1Y'], [1095, '3 年', '3Y'], [0, '全部', 'All']];
  function rangeOf(el, cfg, W) {
    if (cfg.xType === 'num' || cfg.noRange || W < 420 || (cfg.h && cfg.h < 190)) return null;   // 小圖（鏈上指標走勢的小格）不加，太擠
    var host = el.closest('.evc, .panel'); if (host && [].some.call(host.querySelectorAll('.seg'), function (g) { return !g.classList.contains('rng') && !g.classList.contains('tm-mode') && !g.classList.contains('lg-view'); })) return null;
    var xs = []; cfg.series.forEach(function (s) { s.data.forEach(function (p) { if (p[1] != null) xs.push(p[0]); }); }); if (xs.length < 2) return null;
    var lo = Math.min.apply(null, xs), hi = Math.max.apply(null, xs), span = hi - lo; if (span < 700) return null;
    var opts = RNG.filter(function (o) { return !o[0] || o[0] < span * 0.8; }), sel = el._rng || 0;
    if (opts.every(function (o) { return o[0] !== sel; })) sel = 0;
    var html = '<div class="seg rng" role="group" aria-label="' + _T('時間範圍', 'Time range') + '">' + opts.map(function (o) { return '<button type="button" data-d="' + o[0] + '" aria-pressed="' + (o[0] === sel) + '">' + _T(o[1], o[2]) + '</button>'; }).join('') + '</div>';
    return { html: html, x0: sel ? hi - sel : null };
  }
  function bindRng(el, rg) { if (rg) el.querySelector('.rng').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; el._rng = +b.getAttribute('data-d'); if (el._draw) el._draw(el); }); }
  function lineChart(el, cfg) {
    var W = Math.max(280, el.clientWidth), Ht = cfg.h || (W < 520 ? 210 : 260);
    var rg = rangeOf(el, cfg, W);
    if (rg && rg.x0 != null) { var rx0 = rg.x0; cfg = Object.assign({}, cfg, { x0: cfg.x0 != null ? Math.max(cfg.x0, rx0) : rx0, series: cfg.series.map(function (q) { return Object.assign({}, q, { data: q.data.filter(function (p) { return p[0] >= rx0; }) }); }), marks: (cfg.marks || []).filter(function (m) { return m.x >= rx0; }) }); }
    var ML = cfg.ml || 8, MR = cfg.mr || 58, MT = 14, MB = 24, pw = W - ML - MR, ph = Ht - MT - MB;
    /* 2026-11-04 整體審查：BTC 價格「另一刻度」不再疊在同一格（兩條線的交叉沒有意義），改成上下兩格：上格價格（有自己的刻度）、下格指標，共用時間軸 */
    var stack = cfg.stack !== false && cfg.series.some(function (s) { return s.y2; }), MT0 = MT, topH = 0;
    if (stack) { topH = Math.round(Math.max(70, ph * 0.5)); Ht += topH + 20; MT = MT0 + topH + 20; }
    var all = [], all2 = [], xa = []; cfg.series.forEach(function (s) { s.data.forEach(function (p) { if (p[1] != null) { (s.y2 ? all2 : all).push(p); xa.push(p[0]); } }); });
    if (all.length < 2) { el.innerHTML = _t('<p class="note">本日未取得資料。</p>'); return; }
    var x0 = cfg.x0 != null ? cfg.x0 : Math.min.apply(null, xa);
    var x1 = cfg.x1 != null ? cfg.x1 : Math.max.apply(null, xa);
    var ys = all.map(function (p) { return p[1]; }); (cfg.refs || []).forEach(function (r) { if (r.inRange !== false) ys.push(r.y); });
    var lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys);
    if (cfg.robust) { var srt = all.map(function (p) { return p[1]; }).sort(function (a, b) { return a - b; }), q = Math.ceil(srt.length * cfg.robust); lo = Math.min(lo, srt[q]); hi = srt[srt.length - 1 - q]; lo = Math.max(lo, srt[q]); (cfg.refs || []).forEach(function (r) { if (r.inRange !== false) { lo = Math.min(lo, r.y); hi = Math.max(hi, r.y); } }); }   // 2026-10-14：排除資料商的離群值（例如 STH-SOPR 2025-10-20 的 1.69），超出的點畫在邊緣
    if (cfg.y0 != null) lo = Math.min(lo, cfg.y0); if (cfg.y1 != null) hi = Math.max(hi, cfg.y1);
    var lg = !!cfg.log, T = function (v) { return lg ? Math.log10(v) : v; };
    var tl = T(lo), th = T(hi), pad = (th - tl) * 0.08 || 1; tl -= pad; th += pad;
    var X = function (x) { return ML + (x - x0) / (x1 - x0 || 1) * pw; };
    var Y = function (v) { var y = MT + (1 - (T(v) - tl) / (th - tl)) * ph; return cfg.robust ? Math.max(MT, Math.min(MT + ph, y)) : y; };
    // 第二 y 軸（2026-10-14）：series 帶 y2 的用自己的刻度（例如佐證燈號圖上的價格線），不畫刻度、tooltip 照列
    var Y2 = Y;
    if (all2.length) { var T2 = function (v) { return cfg.log2 ? Math.log10(v) : v; }, v2 = all2.map(function (p) { return T2(p[1]); }), l2 = Math.min.apply(null, v2), h2 = Math.max.apply(null, v2), p2 = (h2 - l2) * 0.08 || 1; l2 -= p2; h2 += p2; Y2 = stack ? function (v) { return MT0 + (1 - (T2(v) - l2) / (h2 - l2)) * topH; } : function (v) { return MT + (1 - (T2(v) - l2) / (h2 - l2)) * ph; }; }
    var s = '', yf = cfg.yFmt || function (v) { return fmt.k(v); };
    // y grid
    var ticks = [];
    if (lg) { [0.1, 0.2, 0.3, 0.5, 1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1e3, 2e3, 5e3, 1e4, 2e4, 5e4, 1e5, 2e5, 5e5, 1e6].forEach(function (t) { if (T(t) >= tl && T(t) <= th) ticks.push(t); }); if (ticks.length > 7) ticks = ticks.filter(function (t, i) { return i % 2 === 0; }); }
    else { var st = niceStep(th - tl, W < 520 ? 3 : 4); for (var t = Math.ceil(tl / st) * st; t <= th + 1e-9; t += st) ticks.push(+t.toFixed(10)); }
    ticks.forEach(function (t) { var y = Y(t); s += '<line class="gl" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (y + 3.5).toFixed(1) + '">' + yf(t) + '</text>'; });
    if (stack && all2.length) {   // 上格（價格）的刻度與標題
      var t2s = [], y2n = cfg.series.filter(function (q) { return q.y2; })[0], y1n = cfg.series.filter(function (q) { return !q.y2; })[0];
      if (cfg.log2) [100, 1e3, 2e3, 5e3, 1e4, 2e4, 5e4, 1e5, 2e5].forEach(function (t) { var v = Math.log10(t); if (v >= l2 && v <= h2) t2s.push(t); });
      else { var st2 = niceStep(h2 - l2, 2); for (var t2 = Math.ceil(l2 / st2) * st2; t2 <= h2 + 1e-9; t2 += st2) t2s.push(+t2.toFixed(10)); }
      if (t2s.length > 4) t2s = t2s.filter(function (t, i) { return i % 2 === (t2s.length - 1) % 2; });
      t2s.forEach(function (t) { var y = Y2(t); s += '<line class="gl" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (y + 3.5).toFixed(1) + '">' + (t >= 1000 ? fmt.k(t) : fmt.n(t)) + '</text>'; });
      s += axText(ML, MT0 - 3, y2n.name) + (y1n ? axText(ML, MT - 6, y1n.name) : '');
    }
    // x ticks
    if (cfg.xType !== 'num') {
      var span = x1 - x0, step = span > 2500 ? 24 : span > 1100 ? 12 : span > 500 ? 6 : span > 150 ? 2 : 1, d = new Date(x0 * 864e5), lastX = -99;
      d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + 1);
      while (d.getTime() / 864e5 <= x1) {
        var mo = d.getUTCMonth();
        if ((step >= 12 ? mo === 0 && (step === 12 || d.getUTCFullYear() % 2 === 0) : mo % step === 0)) {
          var xx = X(d.getTime() / 864e5);
          if (xx - lastX > 46) { s += '<text class="ax" x="' + xx.toFixed(1) + '" y="' + (Ht - 6) + '" text-anchor="middle">' + (step >= 12 || mo === 0 ? d.getUTCFullYear() : (String(d.getUTCFullYear()).slice(2) + '/' + (mo + 1))) + '</text>'; lastX = xx; }
        }
        d.setUTCMonth(d.getUTCMonth() + 1);
      }
    } else { var lxt = -99; (cfg.xticks || []).forEach(function (t) { var xx = X(t[0]), w = lblW(t[1]) * 10 / 10.5; if (xx - w / 2 < lxt + 6) return; lxt = xx + w / 2; s += '<text class="ax" x="' + xx.toFixed(1) + '" y="' + (Ht - 6) + '" text-anchor="middle">' + esc(t[1]) + '</text>'; }); }   // 2026-11-04：太近的刻度略過（基差曲線 9d／23d 疊在一起）
    // vertical bands & lines
    (cfg.vbands || []).forEach(function (b) { var a = Math.max(ML, X(b.x0)), z = Math.min(ML + pw, X(b.x1)); if (z > a) s += '<rect x="' + a.toFixed(1) + '" y="' + MT + '" width="' + (z - a).toFixed(1) + '" height="' + ph + '" fill="' + (b.color || 'var(--flare-dim)') + '"/>' + (b.label ? '<text class="ax" x="' + (a + 6).toFixed(1) + '" y="' + (MT + 12) + '">' + esc(b.label) + '</text>' : ''); });
    (cfg.vlines || []).concat(sigV(el)).forEach(function (v) { var xx = X(v.x); if (xx < ML || xx > ML + pw) return; s += '<line x1="' + xx.toFixed(1) + '" x2="' + xx.toFixed(1) + '" y1="' + MT + '" y2="' + (MT + ph) + '" stroke="var(--ink-3)" stroke-dasharray="2 4" stroke-width="1"/>' + (v.label ? '<text class="ax" x="' + (xx > ML + pw - 70 ? xx - 5 : xx + 5).toFixed(1) + '" y="' + (MT + ph - 6) + '"' + (xx > ML + pw - 70 ? ' text-anchor="end"' : '') + '>' + esc(v.label) + '</text>' : ''); });
    (cfg.hbands || []).forEach(function (b) { var a = Math.max(MT, Y(b.y1)), z = Math.min(MT + ph, Y(b.y0)); if (z <= a) return; s += '<rect x="' + ML + '" y="' + a.toFixed(1) + '" width="' + pw + '" height="' + Math.max(1, z - a).toFixed(1) + '" fill="' + b.color + '"/>'; });
    // refs
    (cfg.refs || []).forEach(function (r) { var y = Y(r.y); if (y < MT - 2 || y > MT + ph + 2) return; s += '<line class="ref" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '" stroke="' + r.color + '"/>'; if (r.label) s += '<text class="reflab" x="' + (ML + 6) + '" y="' + (y + (r.below ? 13 : -5)).toFixed(1) + '" fill="' + r.color + '">' + esc(r.label) + '</text>'; });
    // series
    var defs = '';
    var nowDone = false;   // 2026-11-05 全站圖表升級：第一條彩色實線的最新一點加 now-dot（心跳動畫，見 app.css）
    cfg.series.forEach(function (sr, si) {
      var pts = sr.data.filter(function (p) { return p[1] != null; }); if (pts.length < 2) return;
      var Yf = sr.y2 ? Y2 : Y, dpath = sr.smooth ? smoothPath(pts.map(function (p) { return [X(p[0]), Yf(p[1])]; })) : pts.map(function (p, i) { return (i ? 'L' : 'M') + X(p[0]).toFixed(1) + ',' + Yf(p[1]).toFixed(1); }).join('');
      if (sr.area) { var gid = 'g' + Math.random().toString(36).slice(2, 8); defs += '<linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + sr.color + '" stop-opacity=".5"/><stop offset=".6" stop-color="' + sr.color + '" stop-opacity=".14"/><stop offset="1" stop-color="' + sr.color + '" stop-opacity="0"/></linearGradient>'; s += '<path d="' + dpath + 'L' + X(pts[pts.length - 1][0]).toFixed(1) + ',' + (MT + ph) + 'L' + X(pts[0][0]).toFixed(1) + ',' + (MT + ph) + 'Z" fill="url(#' + gid + ')"/>'; }
      s += '<path class="ln" d="' + dpath + '" stroke="' + sr.color + '" stroke-width="' + (sr.w || 2) + '"' + (sr.dash ? ' stroke-dasharray="' + sr.dash + '"' : '') + ' style="animation-delay:' + (si * 0.12) + 's"/>';
      if (sr.end !== false) { var lp = pts[pts.length - 1], nd = !nowDone && !sr.dash && String(sr.color).indexOf('ink') < 0; if (nd) nowDone = true; s += '<circle' + (nd ? ' class="now-dot"' : '') + ' cx="' + X(lp[0]).toFixed(1) + '" cy="' + Yf(lp[1]).toFixed(1) + '" r="4" fill="' + (sr.endColor || sr.color) + '" stroke="var(--deck)" stroke-width="2"/>'; }
    });
    // 2026-11-04 自我檢查：標註文字不再互相重疊——由最新一個往回放，撞到已放的字（含參考線標籤）就換到另一側，兩側都撞就只畫點不寫字；超出右緣改成向左寫
    var placed = (cfg.refs || []).filter(function (r) { return r.label; }).map(function (r) { var y = Y(r.y) + (r.below ? 13 : -5); return [ML + 6, ML + 6 + lblW(r.label), y - 10, y + 2]; }), mk = '';
    (cfg.marks || []).slice().reverse().forEach(function (m) {
      var xx = X(m.x), yy = Y(m.y), col = m.color || 'var(--flare)', lab = '';
      if (m.label) {
        var w = lblW(m.label), left = (m.left || xx + 8 + w > ML + pw) && xx - 8 - w >= 0, x0 = left ? xx - 8 - w : xx + 8;   // 往左寫會超出左緣就改往右
        [m.below, !m.below].some(function (bl) {
          var ty = yy + (bl ? 15 : -8), bx = [x0, x0 + w, ty - 10, ty + 2];
          if (placed.some(function (p) { return bx[0] < p[1] && bx[1] > p[0] && bx[2] < p[3] && bx[3] > p[2]; })) return false;
          placed.push(bx); lab = '<text class="reflab" x="' + (xx + (left ? -8 : 8)).toFixed(1) + '" y="' + ty.toFixed(1) + '" fill="' + col + '"' + (left ? ' text-anchor="end"' : '') + '>' + esc(m.label) + '</text>'; return true;
        });
      }
      mk = '<circle cx="' + xx.toFixed(1) + '" cy="' + yy.toFixed(1) + '" r="4.5" fill="var(--deck)" stroke="' + col + '" stroke-width="2"/>' + lab + mk;
    });
    s += mk;
    var HT0 = stack ? MT0 : MT;   // 上下兩格時十字線與滑過區涵蓋兩格
    s += '<line class="xh" x1="0" x2="0" y1="' + HT0 + '" y2="' + (MT + ph) + '" visibility="hidden"/><g class="hdots"></g><rect class="hit" x="' + ML + '" y="' + HT0 + '" width="' + pw + '" height="' + (MT + ph - HT0) + '"/>';
    el.innerHTML = (rg ? rg.html : '') + svgEl(W, Ht, '<defs>' + defs + '</defs>' + s, cfg.aria);
    bindRng(el, rg);
    animateLines(el);
    var svg = el.querySelector('svg'), xh = svg.querySelector('.xh'), dots = svg.querySelector('.hdots'), hit = svg.querySelector('.hit');
    function move(ev) {
      var r = svg.getBoundingClientRect(), mx = (ev.clientX - r.left) * W / r.width, xv = x0 + (mx - ML) / pw * (x1 - x0), rows = [], g = '', xs = null;
      cfg.series.forEach(function (sr) {
        var pts = sr.data.filter(function (p) { return p[1] != null; }); if (!pts.length || sr.tip === false) return;
        var i = bisect(pts, xv), p = pts[i]; if (xs == null) xs = p[0];
        if (Math.abs(p[0] - xv) > (cfg.tipGap || 1e9)) return;   // 這條線在游標附近沒有資料（例如外推線）就不列
        g += '<circle cx="' + X(p[0]).toFixed(1) + '" cy="' + (sr.y2 ? Y2 : Y)(p[1]).toFixed(1) + '" r="4" fill="' + sr.color + '" stroke="var(--deck)" stroke-width="2"/>';
        rows.push('<div class="r"><i style="background:' + (sr.tipColor ? sr.tipColor(p[1]) : sr.color) + '"></i><span>' + esc(sr.name) + '</span><b>' + (sr.fmt || cfg.tipFmt || yf)(p[1]) + '</b></div>');
      });
      if (xs == null) return;
      xh.setAttribute('x1', X(xs)); xh.setAttribute('x2', X(xs)); xh.setAttribute('visibility', 'visible'); dots.innerHTML = g;
      showTip(ev.clientX, ev.clientY, '<div class="t">' + (cfg.xType === 'num' ? (cfg.xTipFmt ? cfg.xTipFmt(xs) : xs) : fmt.date(xs)) + '</div>' + rows.join(''));
    }
    hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', function () { xh.setAttribute('visibility', 'hidden'); dots.innerHTML = ''; hideTip(); });
  }

  /* 長條圖：data [[label, value, tipHtml]]，正負配色 */
  function barChart(el, cfg) {
    var W = Math.max(280, el.clientWidth), Ht = cfg.h || 220, ML = 8, MR = 52, MT = 12, MB = cfg.mb || 24, pw = W - ML - MR, ph = Ht - MT - MB;
    var d = cfg.data; if (!d || !d.length) { el.innerHTML = _t('<p class="note">本日未取得資料。</p>'); return; }
    var vals = d.map(function (r) { return r[1]; }), lo = Math.min(0, Math.min.apply(null, vals)), hi = Math.max(0, Math.max.apply(null, vals));
    var st = niceStep(hi - lo || 1, 4); lo = Math.floor(lo / st) * st; hi = Math.ceil(hi / st) * st;
    var Y = function (v) { return MT + (1 - (v - lo) / (hi - lo || 1)) * ph; }, bw = pw / d.length, gap = Math.min(6, bw * 0.28), s = '';
    for (var t = lo; t <= hi + 1e-9; t += st) { var y = Y(t); s += '<line class="' + (Math.abs(t) < 1e-9 ? 'base' : 'gl') + '" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (y + 3.5).toFixed(1) + '">' + (cfg.yFmt || fmt.k)(t) + '</text>'; }
    var every = Math.ceil(d.length / Math.max(1, Math.floor(pw / 46)));
    d.forEach(function (r, i) {
      var x = ML + i * bw + gap / 2, w = Math.max(1, bw - gap), y0 = Y(0), y = Y(r[1]), top = Math.min(y, y0), h = Math.max(1, Math.abs(y - y0));
      var col = cfg.color ? cfg.color(r, i) : (r[1] >= 0 ? 'var(--up)' : 'var(--down)');
      var rad = Math.min(4, w / 2);
      s += '<rect class="bar" data-i="' + i + '" x="' + x.toFixed(1) + '" y="' + top.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + h.toFixed(1) + '" rx="' + rad + '" fill="' + col + '"' + (r[3] ? ' opacity=".45"' : '') + '><animate attributeName="height" from="0" to="' + h.toFixed(1) + '" dur="' + (reduced ? '0.01' : '0.7') + 's" fill="freeze"/></rect>';
      if (i % every === 0 || i === d.length - 1) s += '<text class="ax" x="' + (x + w / 2).toFixed(1) + '" y="' + (Ht - 6) + '" text-anchor="middle">' + esc(r[0]) + '</text>';
    });
    el.innerHTML = svgEl(W, Ht, s, cfg.aria);
    el.querySelectorAll('.bar').forEach(function (b) {
      var r = d[+b.getAttribute('data-i')];
      b.addEventListener('pointermove', function (ev) { showTip(ev.clientX, ev.clientY, r[2] || ('<div class="t">' + esc(r[0]) + _t('</div><div class="r"><i style="background:currentColor"></i><span>值</span><b>') + fmt.n(r[1], 1) + '</b></div>')); });
      b.addEventListener('pointerleave', hideTip);
    });
  }

  /* K 線 */
  /* 一根 K 線：影線＋實體（2026-11-04 抽出，近 20 天 K 線、清算熱力圖、短期持有者獲利比例的週 K 共用）。y 是已換算的像素 */
  function candleMark(cx, w, yo, yh, yl, yc, col, o) { o = o || {};
    return '<line x1="' + cx.toFixed(1) + '" x2="' + cx.toFixed(1) + '" y1="' + yh.toFixed(1) + '" y2="' + yl.toFixed(1) + '" stroke="' + col + '" stroke-width="' + (o.sw || 1) + '"/><rect x="' + (cx - w / 2).toFixed(1) + '" y="' + Math.min(yo, yc).toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + Math.max(o.minH || 1, Math.abs(yo - yc)).toFixed(1) + '"' + (o.rx ? ' rx="' + o.rx + '"' : '') + ' fill="' + col + '"/>'; }
  function candleChart(el, rows, lines) {
    var W = Math.max(280, el.clientWidth), Ht = W < 520 ? 240 : 300, ML = 8, MR = 62, MT = 12, MB = 24, pw = W - ML - MR, ph = Ht - MT - MB;
    var lo = Math.min.apply(null, rows.map(function (r) { return r[3]; })), hi = Math.max.apply(null, rows.map(function (r) { return r[2]; }));
    lines.forEach(function (l) { if (l.v > lo * 0.97 && l.v < hi * 1.03) { lo = Math.min(lo, l.v); hi = Math.max(hi, l.v); } });
    var pad = (hi - lo) * 0.06; lo -= pad; hi += pad;
    var Y = function (v) { return MT + (1 - (v - lo) / (hi - lo)) * ph; }, bw = pw / rows.length, s = '', st = niceStep(hi - lo, 5);
    for (var t = Math.ceil(lo / st) * st; t <= hi; t += st) { var y = Y(t); s += '<line class="gl" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (y + 3.5).toFixed(1) + '">' + fmt.k(t) + '</text>'; }
    var used = []; lines.filter(function (l) { return l.v >= lo && l.v <= hi; }).sort(function (a, b) { return b.v - a.v; }).forEach(function (l) { var y = Y(l.v), ty = y - 4; while (used.some(function (u) { return Math.abs(u - ty) < 12; })) ty += 13; used.push(ty); s += '<line class="ref" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '" stroke="' + l.color + '"/><text class="reflab" x="' + (ML + 4) + '" y="' + ty.toFixed(1) + '" fill="' + l.color + '">' + esc(l.label) + '</text>'; });
    rows.forEach(function (r, i) {
      var x = ML + i * bw + bw / 2, up = r[4] >= r[1], col = up ? 'var(--up)' : 'var(--down)', w = Math.max(3, bw * 0.56);
      s += '<g class="cd" data-i="' + i + '"><rect x="' + (ML + i * bw) + '" y="' + MT + '" width="' + bw + '" height="' + ph + '" fill="transparent"/>' + candleMark(x, w, Y(r[1]), Y(r[2]), Y(r[3]), Y(r[4]), col, { sw: 1.4, minH: 1.5, rx: 1.5 }) + '</g>';
      var ev = Math.ceil(rows.length / Math.max(1, Math.floor(pw / 52))); if ((i % ev === 0 && rows.length - 1 - i >= ev) || i === rows.length - 1) s += '<text class="ax" x="' + x.toFixed(1) + '" y="' + (Ht - 6) + '" text-anchor="middle">' + r[0] + '</text>';
    });
    el.innerHTML = svgEl(W, Ht, s, _t('近 20 日 K 線'));
    el.querySelectorAll('.cd').forEach(function (g) {
      var r = rows[+g.getAttribute('data-i')];
      g.addEventListener('pointermove', function (ev) { showTip(ev.clientX, ev.clientY, '<div class="t">' + r[0] + '</div>' + [[_t('開'), r[1]], [_t('高'), r[2]], [_t('低'), r[3]], [_t('收'), r[4]]].map(function (p) { return '<div class="r"><i style="background:' + (r[4] >= r[1] ? 'var(--up)' : 'var(--down)') + '"></i><span>' + p[0] + '</span><b>' + fmt.n(p[1]) + '</b></div>'; }).join('') + _t('<div class="r"><i></i><span>漲跌</span><b>') + fmt.pct((r[4] / r[1] - 1) * 100, 2) + '</b></div>'); });
      g.addEventListener('pointerleave', hideTip);
    });
  }

  /* 水平階梯（掛單簿、籌碼分布） */
  function ladderHtml(rows, opt) {
    var mx = Math.max.apply(null, rows.map(function (r) { return r.v; })) || 1;
    return '<div class="ladder' + (opt && opt.dense ? ' dense' : '') + '">' + rows.map(function (r, i) {
      return '<div class="row' + (r.cls ? ' ' + r.cls : '') + '" data-i="' + i + '"><span class="p">' + esc(r.label) + '</span><span class="b"><i style="width:' + (r.v / mx * 100).toFixed(1) + '%;background:' + r.color + ';animation-delay:' + (i * 0.015).toFixed(2) + 's"></i>' + (r.prev != null ? '<u style="position:absolute;top:-2px;bottom:-2px;left:' + (r.prev / mx * 100).toFixed(1) + '%;width:2px;background:var(--ink-2)"></u>' : '') + '</span><span class="m">' + esc(r.right) + '</span></div>';
    }).join('') + '</div>';
  }
  function bindLadder(el, rows) {
    el.querySelectorAll('.ladder .row').forEach(function (n) { var r = rows[+n.getAttribute('data-i')]; if (!r.tip) return; n.addEventListener('pointermove', function (ev) { showTip(ev.clientX, ev.clientY, r.tip); }); n.addEventListener('pointerleave', hideTip); });
  }

  /* ---------------- Shared bits ---------------- */
  function panel(cls, title, src, body, extra, id) { return '<section class="panel ' + cls + '"' + (id ? ' id="pn-' + id + '"' : '') + '><div class="panel-h"><h2>' + title + '</h2>' + (extra || '') + (src ? '<span class="src">' + src + '</span>' : '') + '</div>' + body + '</section>'; }
  function readBar(key, bare) {
    var m = N && N.modules && N.modules[key]; if (!m) return '';
    if (ZH_ONLY) return '<div class="read' + (bare ? ' bare' : '') + '" data-k="' + key + '">' + (bare ? '' : '<span class="tag">TODAY’S READ</span>') + '<div><p class="note">The written commentary for this edition is available in Chinese only. All numbers and the readings under them are in English.</p></div></div>';
    if (N.stale && !bare) return '<div class="read old" data-k="' + key + '"><span class="tag">' + _T('上一期判讀', 'Previous read') + '<b>' + fmt.md(N.date) + '</b></span><div><p>' + esc(m.lead) + '</p><ul>' + (m.points || []).map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul></div></div>';   // 2026-11-06：判讀還是上一期（任務晚了或失敗）
    return '<div class="read' + (bare ? ' bare' : '') + '" data-k="' + key + '">' + (bare ? '' : _t('<span class="tag">今日判讀<small>TODAY’S READ</small></span>')) + '<div><p>' + esc(m.lead) + '</p><ul>' + (m.points || []).map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul></div></div>';
  }
  function kpi(k, v, n, bar, cls) { return '<div class="kpi"><span class="k">' + k + '</span><span class="v' + (cls ? ' ' + cls : '') + '">' + v + '</span>' + (n ? '<span class="n">' + n + '</span>' : '') + (bar != null ? '<span class="bar"><i style="width:' + Math.max(2, Math.min(100, bar)).toFixed(1) + '%"></i></span>' : '') + '</div>'; }
  function legend(items) { return '<div class="legend">' + items.map(function (it) { return '<span style="color:' + it[1] + '"><i class="' + (it[2] || '') + '"></i><b style="color:var(--ink-2);font-weight:400">' + esc(it[0]) + '</b></span>'; }).join('') + '</div>'; }

  /* 2026-11-09 使用者：「值得搬過來的那4個」（Tidemark 歷史圖的互動）搬到全站。圖例在圖前面的都會自動套：
     ① 圖例可以點：依顏色對應到圖上的線、面積、柱與標記，點一下藏起來、再點一下回來（重畫後保留）；
     ② 圖例旁顯示數字：沒滑過時是最新一天，滑過圖時是游標那一天（數字取自提示框，顏色對上的才顯示）；
     ③ 圖例同時有「頂」和「底」的項目時，加「全部／頂部／底部」切換，一次藏起另一邊。
     Tidemark 歷史圖有自己的圖例與讀數列，不套這一套 */
  var lgSim = 0;
  function lgCol(sp) { var m = /(?:^|;)\s*color:\s*([^;]+)/.exec(sp.getAttribute('style') || ''); return m ? m[1].trim() : null; }
  function lgOf(el) { for (var n = el.previousElementSibling, k = 0; n && k < 4; n = n.previousElementSibling, k++) { if (n.classList.contains('chart')) return null; if (n.classList.contains('legend')) return n.classList.contains('tmh-chips') ? null : n; } return null; }
  function lgItems(lg) { return [].filter.call(lg.children, function (n) { return n.tagName === 'SPAN' && !n.classList.contains('lg-d'); }); }
  function lgNodes(svg, col) {
    var ids = [].filter.call(svg.querySelectorAll('linearGradient'), function (g) { var st = g.querySelector('stop'); return st && st.getAttribute('stop-color') === col; }).map(function (g) { return g.id; });
    var sel = '[stroke="' + col + '"], [fill="' + col + '"], [style*="fill:' + col + '"]' + ids.map(function (id) { return ', [fill="url(#' + id + ')"]'; }).join('');
    return [].filter.call(svg.querySelectorAll(sel), function (n) { return !n.closest('defs') && !n.classList.contains('hit'); });
  }
  function lgApply(el) {
    var svg = el.querySelector('svg'); if (!svg) return; var H = el._lgHide || {};
    [].forEach.call(svg.querySelectorAll('.lg-off'), function (n) { n.classList.remove('lg-off'); });
    Object.keys(H).forEach(function (c) { if (H[c]) lgNodes(svg, c).forEach(function (n) { n.classList.add('lg-off'); }); });
  }
  function lgSync(el, lg) { lgItems(lg).forEach(function (sp) { if (sp.classList.contains('lg-tg')) sp.setAttribute('aria-pressed', !el._lgHide[lgCol(sp)]); }); lgApply(el); }
  function lgTip() {
    var T = $('#tip'); if (!T || T.hidden) return null;
    var t = T.querySelector('.t'), rows = [].map.call(T.querySelectorAll('.r'), function (r) { var i = r.querySelector('i'), b = r.querySelector('b'), n = r.querySelector('span'), m = /background:\s*([^;]+)/.exec((i && i.getAttribute('style')) || ''); return [m ? m[1].trim() : '', b ? b.textContent : '', n ? n.textContent.trim() : '']; });
    return { t: t ? t.textContent : '', rows: rows };
  }
  function lgFill(lg, q) {
    var hit = 0, used = {}, its = lgItems(lg), nm = function (x) { return String(x || '').replace(/[\s（）()：:]/g, '').toLowerCase(); };
    its.forEach(function (sp) {
      var c = lgCol(sp), em = sp.querySelector('.lg-v'), r = null;
      if (q && c) {
        var cand = q.rows.filter(function (x, k) { return x[0] === c && !used[k]; }), name = nm((sp.querySelector('b') || sp).textContent);
        var same = its.filter(function (o) { return lgCol(o) === c; }).length, all = q.rows.filter(function (x) { return x[0] === c; }).length;
        r = cand.filter(function (x) { var a = nm(x[2]); return a && (a === name || a.indexOf(name) === 0 || name.indexOf(a) === 0); })[0] || null;   // 先比名稱
        if (!r && (same === 1 || all === same)) r = cand[0] || null;   // 同色只有一項，或同色的列數和圖例項數一樣（照順序一對一）
        if (r) used[q.rows.indexOf(r)] = 1;
      }
      if (r && r[1]) { hit = 1; if (!em) { em = document.createElement('em'); em.className = 'lg-v'; sp.appendChild(em); } em.textContent = r[1]; } else if (em) em.textContent = '';
    });
    var d = lg.querySelector('.lg-d'); if (hit && !d) { d = document.createElement('span'); d.className = 'lg-d'; lg.insertBefore(d, lg.firstChild); }
    if (d) d.textContent = hit ? q.t : '';
  }
  function lgLatest(el, lg) {   // 模擬游標放在圖的右緣外，取最後一筆（手機上一個像素可能涵蓋十幾天，放在右緣內會取到前一筆）
    var hs = el.querySelectorAll('.hit'); if (!hs.length) return; var h = hs[hs.length - 1], r = h.getBoundingClientRect(), T = $('#tip');
    if (!r.width || (T && !T.hidden)) return;
    lgSim = 1;
    try { h.dispatchEvent(new PointerEvent('pointermove', { clientX: hs.length > 1 ? r.left + r.width / 2 : r.right + 40, clientY: r.top + r.height / 2, bubbles: true })); el._lgLast = lgTip(); h.dispatchEvent(new PointerEvent('pointerleave')); } catch (e) {}
    hideTip(); lgSim = 0;
    if (el._lgLast) lgFill(lg, el._lgLast);
  }
  function lgView(el, lg) {
    var its = lgItems(lg).filter(function (sp) { return sp.classList.contains('lg-tg'); }), tx = function (sp) { return sp.textContent; };
    var TP = /頂部|頂背離|週期頂|歷次頂|cycle top|bearish div/i, BT = /底部|底背離|熊市底|歷次底|bottom|bullish div/i;
    var top = its.filter(function (sp) { return TP.test(tx(sp)) && !BT.test(tx(sp)); }), bot = its.filter(function (sp) { return BT.test(tx(sp)) && !TP.test(tx(sp)); });
    var sg = lg.querySelector('.lg-view'); if (!top.length || !bot.length) { if (sg) sg.remove(); return; } if (sg) return;
    lg.insertAdjacentHTML('beforeend', '<div class="seg lg-view" role="group" aria-label="' + _T('看哪一邊', 'Which side') + '"><button type="button" data-v="all" aria-pressed="true">' + _T('全部', 'All') + '</button><button type="button" data-v="top" aria-pressed="false">' + _T('頂部', 'Tops') + '</button><button type="button" data-v="bot" aria-pressed="false">' + _T('底部', 'Bottoms') + '</button></div>');
    sg = lg.querySelector('.lg-view');
    sg.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return; e.stopPropagation(); var v = b.getAttribute('data-v');
      [].forEach.call(sg.querySelectorAll('button'), function (q) { q.setAttribute('aria-pressed', q === b); });
      top.forEach(function (sp) { el._lgHide[lgCol(sp)] = v === 'bot'; }); bot.forEach(function (sp) { el._lgHide[lgCol(sp)] = v === 'top'; });
      lgSync(el, lg);
    });
  }
  function lgAfter(el) {
    var lg = el && lgOf(el), svg = el && el.querySelector('svg'); if (!lg || !svg) return;
    el._lgHide = el._lgHide || {};
    lgItems(lg).forEach(function (sp) { var c = lgCol(sp), on = c && lgNodes(svg, c).length; sp.classList.toggle('lg-tg', !!on); if (on) { sp.setAttribute('role', 'button'); sp.tabIndex = 0; } });
    if (!lg._lgEl) {
      var tg = function (e) { var sp = e.target.closest('.lg-tg'); if (!sp || (e.type === 'keydown' && e.key !== 'Enter' && e.key !== ' ')) return; e.preventDefault(); var c = lgCol(sp), E = lg._lgEl; E._lgHide[c] = !E._lgHide[c]; lgSync(E, lg); };
      lg.addEventListener('click', tg); lg.addEventListener('keydown', tg);
    }
    lg._lgEl = el;
    lgView(el, lg); lgSync(el, lg); lgLatest(el, lg);
  }
  document.addEventListener('pointermove', function (e) { if (lgSim) return; var h = e.target.closest && e.target.closest('.chart .hit'); if (!h) return; var el = h.closest('.chart'), lg = el && lgOf(el); if (lg) lgFill(lg, lgTip()); });
  document.addEventListener('pointerout', function (e) {
    if (lgSim) return; var h = e.target.closest && e.target.closest('.chart .hit'); if (!h) return; var el = h.closest('.chart'); if (e.relatedTarget && el.contains(e.relatedTarget) && e.relatedTarget.closest('.hit')) return;
    var lg = lgOf(el); if (!lg) return; if (el._lgLast) lgFill(lg, el._lgLast); else lgLatest(el, lg);
  });
  function meter(lab, sub, pos, val, valSub, ticks) {
    return '<div class="meter"><span class="lab"><b>' + lab + '</b><span>' + sub + '</span></span><span class="track">' + (ticks || []).map(function (t) { return '<u style="left:' + t + '%"></u>'; }).join('') + '<em data-pos="' + Math.max(0, Math.min(100, pos)).toFixed(1) + '" style="left:0%"></em></span><span class="val">' + val + (valSub ? '<small>' + valSub + '</small>' : '') + '</span></div>';
  }
  function settleMeters(root) { requestAnimationFrame(function () { root.querySelectorAll('.meter em').forEach(function (e) { e.style.left = e.getAttribute('data-pos') + '%'; }); }); }

  /* ---------------- 破曉：日出插畫、數據帶、跑道 ---------------- */
  function tapeItems() {
    var p = D.price, dv = D.deriv, fr = D.flows.fred || {}, etf = (D.flows.etf || []).filter(function (r) { return !r.partial; }), le = etf[etf.length - 1] || {}, cm = D.cycle.cm, tm = D.cycle.tidemark || {}, mi = D.onchain.mining || {}, pl = D.cycle.powerlaw || {};
    var it = [[_t('BTC 收盤'), fmt.usd(p.bar.c), fmt.pct(p.bar.chg_pct, 2), p.bar.chg_pct >= 0], [_t('200 日均線'), fmt.usd(p.ma.sma200), fmt.pct((p.bar.c / p.ma.sma200 - 1) * 100), true], ['DVOL', fmt.n((dv.dvol || {}).value, 1), _t('一年第 ') + fmt.n((dv.dvol || {}).pct_1y, 0) + _t(' 百分位')], [_t('資金費率'), fmt.pct(fundNow(), 1), _t('年化')], ['ETF ' + fmt.md(le.d), (le.musd >= 0 ? '+' : '') + fmt.n(le.musd, 1) + 'M', '', le.musd >= 0], [_t('10 年期殖利率'), fmt.n((fr.DGS10 || {}).last, 2) + '%', fmt.md((fr.DGS10 || {}).last_date)], [_t('BTC–那斯達克'), fmt.n((fr.NASDAQCOM || {}).corr30, 2), _t('30 日相關')], [_t('MVRV ÷ 前高'), fmt.n(cm.mvrv_vs_prior, 3), _t('賣出線 0.75')], [_t('冪律倍數'), fmt.n(pl.ratio, 2) + '×', _t('合理價 ') + fmt.k(pl.fair)], ['Tidemark', fmt.n((tm.top || {}).signal, 0) + ' / ' + fmt.n((tm.bottom || {}).signal, 0), _t('頂 / 底')], [_t('算力'), fmt.n(mi.hash7, 0) + ' EH/s', fmt.pct(mi.wk_chg_pct, 1), mi.wk_chg_pct >= 0], [_t('下次難度'), fmt.pct(mi.diff_next_pct, 1), fmt.md(mi.retarget)]];
    return it.map(function (x) { return '<span class="tape-item">' + x[0] + ' <b>' + x[1] + '</b>' + (x[2] ? '<i class="' + (x[3] === true ? 'up' : x[3] === false ? 'down' : '') + '">' + x[2] + '</i>' : '') + '</span>'; }).join('');
  }

  /* 收盤到各出場線的距離（對數刻度）。2026-11-04 自我檢查：原本固定 1000 寬的 viewBox 等比縮放，手機上字只剩約 4px；
     改成依實際寬度畫（字維持 11–13px），窄螢幕把標籤分到上下兩排、靠邊的改成往內寫 */
  function runwaySvg(W) {
    var c = D.price.bar.c, S = D.exit.status, F = D.exit.framework, lo = 55000, hi = 240000, nar = W < 560, ML = 12, MR = 12, pw = W - ML - MR, y = 50, Ht = nar ? 138 : 112;
    var X = function (v) { return ML + (Math.log(v) - Math.log(lo)) / (Math.log(hi) - Math.log(lo)) * pw; }, s = '';
    // 文字：置中，但碰到左右邊緣就往內收
    var lab = function (xx, ty, txt, col, size, mono) {
      var w = lblW(txt) * size / 10.5, a = 'middle';
      if (xx - w / 2 < 2) { xx = Math.max(2, xx - 10); a = 'start'; } else if (xx + w / 2 > W - 2) { xx = Math.min(W - 2, xx + 10); a = 'end'; }
      return '<text x="' + xx.toFixed(1) + '" y="' + ty + '" text-anchor="' + a + '" style="font-size:' + size + 'px' + (mono ? ';font-family:var(--f-mono)' : '') + '" fill="' + col + '">' + esc(txt) + '</text>';
    };
    s += '<defs><linearGradient id="rw" x1="0" x2="1"><stop offset="0" stop-color="var(--orbit)"/><stop offset="1" stop-color="var(--flare)"/></linearGradient></defs>';
    s += '<line x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y + '" y2="' + y + '" stroke="var(--line-2)" stroke-width="2"/>';
    (nar ? [60000, 100000, 200000] : [60000, 80000, 100000, 150000, 200000]).forEach(function (t) { s += '<text class="ax" x="' + X(t).toFixed(1) + '" y="' + (Ht - 4) + '" text-anchor="middle" style="font-family:var(--f-mono);font-size:11px" fill="var(--ink-3)">' + fmt.k(t) + '</text>'; });
    s += '<rect x="' + Math.min(X(S.sma200), X(c)).toFixed(1) + '" y="' + (y - 3) + '" width="' + Math.abs(X(c) - X(S.sma200)).toFixed(1) + '" height="6" rx="3" fill="var(--orbit)" opacity=".5"/>';
    s += '<rect x="' + X(c).toFixed(1) + '" y="' + (y - 3) + '" width="' + Math.max(0, X(F.ladder[0]) - X(c)).toFixed(1) + '" height="6" rx="3" fill="url(#rw)" opacity=".35"/>';
    F.ladder.forEach(function (v, i) { s += '<rect x="' + (X(v) - 2).toFixed(1) + '" y="' + (y - 14) + '" width="4" height="28" rx="2" fill="var(--flare)" opacity="' + (1 - i * .08).toFixed(2) + '"><title>' + _T('出場第 ' + (i + 1) + ' 階 ', 'Exit step ' + (i + 1) + ' ') + fmt.usd(v) + '</title></rect>'; });
    var lad = _T('出場階梯 ' + fmt.k(F.ladder[0]) + '–' + fmt.k(F.ladder[F.ladder.length - 1]) + '（' + F.ladder.length + ' 階）', 'Exit ladder ' + fmt.k(F.ladder[0]) + '–' + fmt.k(F.ladder[F.ladder.length - 1]) + ' (' + F.ladder.length + ' steps)');
    var ladX = X(F.ladder[0]), ladW = lblW(lad) * 12 / 10.5;
    s += '<text x="' + (ladX + ladW > W - 2 ? W - 2 : ladX).toFixed(1) + '" y="' + (y - 22) + '" text-anchor="' + (ladX + ladW > W - 2 ? 'end' : 'start') + '" style="font-size:12px" fill="var(--flare)">' + esc(lad) + '</text>';
    var tick = function (v, col) { var xx = X(v).toFixed(1); return '<line x1="' + xx + '" x2="' + xx + '" y1="' + (y - 12) + '" y2="' + (y + 12) + '" stroke="' + col + '" stroke-width="2"/>'; };
    var pc = function (v) { return _T('（', ' (') + fmt.pct((v / c - 1) * 100, 0) + _T('）', ')'); };
    s += tick(S.sma200, 'var(--orbit)') + tick(S.k075_price, 'var(--rose)');
    // 寬螢幕：避險線、階梯在上，MVRV 與收盤在下同一排；窄螢幕只有階梯在上，下方依序收盤、避險線、MVRV 各一排
    s += lab(X(S.sma200), nar ? y + 48 : y - 22, _T('避險線 ', 'Hedge line ') + fmt.k(S.sma200) + pc(S.sma200), 'var(--orbit)', 12);
    s += lab(X(S.k075_price), y + (nar ? 66 : 30), 'MVRV 0.75 ' + fmt.k(S.k075_price) + pc(S.k075_price), 'var(--rose)', 12);
    s += '<circle cx="' + X(c).toFixed(1) + '" cy="' + y + '" r="14" fill="var(--flare)" opacity=".18"><animate attributeName="r" values="11;18;11" dur="3s" repeatCount="indefinite"/></circle><circle cx="' + X(c).toFixed(1) + '" cy="' + y + '" r="7" fill="var(--ink)" stroke="var(--deck)" stroke-width="2.5"/>';
    s += lab(X(c), y + 30, _T('收盤 ', 'Close ') + fmt.k(c), 'var(--ink)', 13, true);
    return svgEl(W, Ht, s, _T('收盤到避險線與出場階梯的距離', 'Distance from the close to the hedge line and the exit ladder'));
  }
  /* 巨型收盤價：數字本身是主視覺，近 20 日收盤線疊在數字上；滑過可逐日回看 */
  function megaHtml(c) {
    var rows = D.price.rows20 || [], cl = rows.map(function (r) { return r[4]; }), lo = Math.min.apply(null, cl), hi = Math.max.apply(null, cl), n = cl.length;
    var Y = function (v) { return 90 - (v - lo) / (hi - lo || 1) * 80; }, pts = cl.map(function (v, i) { return [(i / (n - 1) * 1000).toFixed(1), Y(v).toFixed(2)]; });
    var d = pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0] + ',' + p[1]; }).join('');
    var sma = D.price.ma.sma200;
    return '<div class="mega" id="mega">' +
      _t('<div class="hud tl"><span>BTC / USD · 收盤</span><b id="h-d">') + D.meta.bar_date.replace(/-/g, '.') + ' UTC</b></div>' +
      _t('<div class="hud tr"><span>日漲跌</span><b id="h-c" class="') + (c.chg_pct >= 0 ? 'up' : 'down') + '">' + fmt.pct(c.chg_pct, 2) + '</b></div>' +

      '<b class="big" id="mega-n" data-t="' + fmt.n(c.c) + '">' + fmt.n(c.c) + '</b>' +
      '<div class="spark" aria-hidden="true"><svg viewBox="0 0 1000 100" preserveAspectRatio="none"><path class="line" d="' + d + '"/></svg><span class="scrub" id="m-scrub"></span><span class="dot" id="m-dot" style="left:100%;top:' + Y(cl[n - 1]).toFixed(2) + '%"></span></div>' +
      _t('<p class="mega-hint">滑過數字，逐日回看近 20 天</p>') +
      '</div>';
  }
  function bindMega() {
    var m = $('#mega'); if (!m) return;
    var rows = D.price.rows20 || [], n = rows.length, cl = rows.map(function (r) { return r[4]; }), lo = Math.min.apply(null, cl), hi = Math.max.apply(null, cl);
    var big = $('#mega-n'), fin = fmt.n(D.price.bar.c), dot = $('#m-dot'), sc = $('#m-scrub'), sp = m.querySelector('.spark'), c = D.price.bar, last = n - 1, yr = D.meta.bar_date.slice(0, 4);
    function show(i) {
      if (i === last) return; last = i; var r = rows[i], prev = rows[i - 1], ch = prev ? (r[4] / prev[4] - 1) * 100 : null, Y = 90 - (r[4] - lo) / (hi - lo || 1) * 80;
      big.textContent = fmt.n(r[4]); big.setAttribute('data-t', fmt.n(r[4]));
      dot.style.left = (i / (n - 1) * 100) + '%'; dot.style.top = Y + '%'; sc.style.left = dot.style.left;
      $('#h-d').textContent = yr + '.' + r[0].replace('/', '.') + ' UTC';
      var hc = $('#h-c'); hc.textContent = ch == null ? '—' : fmt.pct(ch, 2); hc.className = ch == null ? '' : ch >= 0 ? 'up' : 'down';
    }
    m.addEventListener('pointermove', function (ev) { var b = sp.getBoundingClientRect(); var i = Math.round(Math.max(0, Math.min(1, (ev.clientX - b.left) / b.width)) * (n - 1)); m.classList.add('scrubbing'); show(i); });
    m.addEventListener('pointerleave', function () { m.classList.remove('scrubbing'); show(n - 1); $('#h-d').textContent = D.meta.bar_date.replace(/-/g, '.') + ' UTC'; var hc = $('#h-c'); hc.textContent = fmt.pct(c.chg_pct, 2); hc.className = c.chg_pct >= 0 ? 'up' : 'down'; });
    mount(m, function () { var cw = m.clientWidth - parseFloat(getComputedStyle(m).paddingLeft) * 2; big.style.fontSize = ''; var cur = big.textContent; big.textContent = fin; var fs = parseFloat(getComputedStyle(big).fontSize), w = big.offsetWidth; big.textContent = cur; if (w > 0) big.style.fontSize = Math.min(fs * cw / w * 0.97, 560, MQ.matches ? 560 : Math.max(180, innerHeight * 0.26)) + 'px'; });   // 2026-11-04：桌面限高（約視窗 26%），讓立場與三個價位進到第一屏
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { m._draw && m._draw(m); });
    countUp(big, c.c);
  }
  function countUp(el, v, dec) {
    if (reduced || !el) return; var t0 = performance.now(), from = v * 0.82, dur = 1100;
    (function step(t) { var k = Math.max(0, Math.min(1, (t - t0) / dur)), e = 1 - Math.pow(1 - k, 4); el.textContent = fmt.n(from + (v - from) * e, dec || 0); if (k < 1) requestAnimationFrame(step); })(t0);
  }
  function tapeHtml() { var one = tapeItems(); return _t('<div class="tape" aria-label="今日數據帶"><div class="tape-track">') + one + one + '</div></div>'; }
  /* 數字解碼：每個數字先亂跳，再由左到右依序定格 */
  function decodeNums(root) {
    if (reduced || !root) return;
    root.querySelectorAll('.kpi .v, .watch .v, .news-sum b, .mod-h .idx').forEach(function (el, k) {
      var txt = el.textContent, f = 0, tot = 18 + k * 2;
      (function step() { f++; el.textContent = txt.replace(/\d/g, function (d, i) { return f / tot * txt.length > i ? d : String((Math.random() * 10) | 0); }); if (f < tot) setTimeout(step, 32); else el.textContent = txt; })();
    });
  }
  function impChip(i) { return '<span class="imp ' + i + '">' + ({ bull: _t('偏多'), bear: _t('偏空'), neutral: _t('中性') })[i] + '</span>'; }

  // 市場階段 P23：資料管線依寫死規則計算（data/latest.json cycle.stage），不連動出場規則
  var STAGE = { '熊市': [_t('熊市'), 'down'], '轉換期': [_t('熊牛轉換期'), 'orbit'], '牛市': [_t('牛市'), 'up'] };
  function stageChip() { var s = STAGE[(D.cycle.stage || {}).stage]; return s ? '<span class="chip ' + s[1] + '">' + s[0] + '</span>' : ''; }
  function stageHtml() {
    var st = D.cycle.stage || {}, s = STAGE[st.stage], c = D.price.bar.c;
    if (!s) return _t('<p class="err">本日未取得市場階段。</p>');
    var need = (st.bull_need || {}).run || 30, run = st.above_rising_run || 0, sma = st.sma200, ev = st.evidence || {}, gap = [];
    if (run < need) gap.push(_t('再站穩 ') + (need - run) + _t(' 天'));
    var lines = st.stage === '牛市' ? [['✓', _t('牛市（單向鎖定）'), fmt.md(st.since) + _t(' 起成立；之後不因短線跌破而改判。')], ['↩', _t('什麼會退回熊市'), _t('收盤連 30 日在下降的 200 日均線之下；現在 ') + (st.below_falling_run || 0) + _t(' 天。')]]
      : st.stage === '轉換期' ? [['✓', _t('不是熊市了'), _t('收盤連 ') + run + _t(' 天站在上升的 200 日均線（') + fmt.usd(sma) + _t('）之上，高出 ') + fmt.pct((c / sma - 1) * 100, 1) + _t('。')],
          ['△', _t('還不是牛市'), gap.length ? _t('差 ') + gap.join(_t('、')) + _t('。') : _t('條件已齊，下一次收盤確認。')],
          ['↩', _t('什麼會退回熊市'), _t('收盤連 5 日在 200 日均線（') + fmt.usd(sma) + _t('，') + fmt.pct((sma / c - 1) * 100, 1) + _t('）之下；現在 ') + (st.below_run || 0) + _t('/5。')]]
      : [['×', _t('仍是熊市'), _t('收盤') + (run ? _t('在上升的 200 日均線之上 ') + run + _t(' 天') : _t('不在上升的 200 日均線之上')) + _t('。')], ['↗', _t('什麼會轉為轉換期'), st.capitulation_seen ? _t('收盤站上上升中的 200 日均線。') : _t('燈號一（投降）重新出現，且收盤站上上升中的 200 日均線。')]];
    var light = function (ok, name, val, cond) { return '<div class="light' + (ok ? ' on' : '') + '"><span class="mk">' + (ok ? '✓' : '·') + '</span><b>' + name + '</b><span class="v num">' + val + '</span><span class="note">' + cond + '</span></div>'; };
    return _t('<p class="say">現在是 <b>') + s[0] + _t('</b>（') + fmt.md(st.since) + _t(' 起）') + (st.stale ? _t('；本日缺資料，沿用前一日判定') : '') + _t('。</p>') +
      '<div class="lights">' + light(st.capitulation_seen, _t('燈號一：投降'), st.capitulation_seen ? _t('已出現過') : _t('未出現'), _t('過去式；一個週期只看一次')) +
        light(run >= need, _t('上升 200 日線上'), run + ' / ' + need + _t(' 天'), _t('線 ') + fmt.usd(sma) + (st.sma200_rising ? _t('，上升中') : _t('，下降中'))) +
        light(ev.n && ev.ok * 2 > ev.n, _t('佐證燈號'), ev.n ? ev.ok + ' / ' + ev.n : '—', _t('只顯示、不參與判定；過半亮起才打勾')) + '</div>' +
      (ev.items ? '<div class="tbl-wrap"><table class="tbl evid"><tbody>' + ev.items.map(function (e) {
        var v = e.id === 'mvrv1y' ? fmt.n(e.value, 3) + _t('（均值 ') + fmt.n(e.ref, 3) + _t('）') : e.id === 'sth' ? fmt.usd(e.value) : fmt.pct(e.value, e.id === 'rcgrowth' ? 2 : 1);
        return '<tr><td><span class="mk-s' + (e.ok ? ' ok' : '') + '">' + (e.ok ? '✓' : '×') + '</span><b>' + esc(_T(e.label, (EV_EN[e.id] || [])[0] || e.label)) + '</b></td><td class="num">' + v + '</td><td>' + esc(_T(e.cond, evCondEn(e))) + '</td><td class="num">' + fmt.md(e.date) + '</td></tr>';
      }).join('') + '</tbody></table></div>' : '') + evCharts(ev) +
      '<div class="rules">' + lines.map(function (l) { return '<div class="rule"><span class="t"><span class="mk-s">' + l[0] + '</span>' + l[1] + '</span><span class="d">' + l[2] + '</span><span></span></div>'; }).join('') + '</div>' +
      _t('<p class="note">判定規則：轉換期＝燈號一（投降）✓ 且收盤在上升的 200 日均線之上（上升＝高於 30 天前）；牛市＝燈號一 ✓ 且收盤連 30 日在上升的 200 日均線之上，成立後單向鎖定；退回熊市＝轉換期中連 5 日收在 200 日均線下，牛市則需連 30 日在下降的 200 日均線下。佐證燈號只顯示證據強弱，不參與判定。</p>') +
      _t('<p class="note">限制：2014 年起只有 3–4 輪週期可回測。這條價格規則在候選標準中假訊號最少，但 2019 年中一樣誤判為牛市，之後跌了近五成；沒有任何規則能同時又快又少假訊號。交易所供給 90 日轉負原為必要條件，回測顯示換視窗長度就失效、地址歸屬會事後修正（有前視偏差），且 2025 年 99% 的日子成立，2026-10-09 起降為佐證。牛市條件在頂部附近也會亮，不是賣出訊號；市場階段只是標籤，不連動出場框架。</p>');
  }
  // 以下三塊由每日結論任務寫進 notes.json；不是當天的就標「上一期」
  /* 資料管線寫進 latest.json 的中文標籤，英文版在這裡對照 */
  var EV_EN = { mom12: ['12-month momentum', 'Close above its level a year ago'], mvrv1y: ['MVRV vs 1-year mean', 'MVRV above its own 1-year average'],
    rcgrowth: ['Capital inflow', 'Realized cap 30-day growth is positive'], xs90: ['Exchange supply', '90-day change is negative'], sth: ['Short-term holder cost', 'Close above short-term holder cost ({src})'],
    tmm: ['STH cost vs true market mean', 'Short-term holder cost above the true market mean ({src})'] };
  // 2026-11-04：短期持有者成本與真實市場均價改用 Bitview（失敗時退回 bitcoin-data），英文條件依資料來源帶入
  function evCondEn(e) { var t = (EV_EN[e.id] || [])[1]; return t ? t.replace('{src}', e.src === 'Bitview' ? 'Bitview' : e.id === 'tmm' ? 'bitcoin-data, ~7 days late' : 'bitcoin-data') : e.cond; }
  /* 佐證燈號走勢圖（2026-10-14）：每盞燈一張、配 BTC 價格線；上方一句「離翻轉多遠、大概何時」。只作讀值，外推不是預測 */
  var EV_ORDER = ['tmm', 'sth', 'mom12', 'mvrv1y', 'rcgrowth', 'xs90'];
  function evSay(e, sv) {
    var c = D.price.bar.c, m = sv.mom12 || {}, t = (sv.tmm || {}).est || e.est || {}, ymd = function (d) { return d ? d.replace(/-/g, '/') : '—'; }, sgn = function (v) { return (v >= 0 ? '+' : '−') + fmt.n(Math.abs(v), 0); };
    switch (e.id) {
      case 'mom12':
        var f = m.flat_flip, s1 = _T('現價比一年前 ', 'Price vs a year ago: ') + fmt.pct(e.value, 1) + _T('。', '. ');
        if (m.hi30) s1 += _T('未來 30 天要比的一年前價格最高 ' + fmt.usd(m.hi30.price) + '（' + ymd(m.hi30.date) + '）。', 'The year-ago price to beat peaks at ' + fmt.usd(m.hi30.price) + ' (' + ymd(m.hi30.date) + ') over the next 30 days. ');
        if (f) s1 += _T('價格不動的話，' + ymd(f.date) + ' 前後燈號' + (e.ok ? '熄滅' : '亮起') + '（一年前價格' + (e.ok ? '升到 ' : '降到 ') + fmt.usd(f.price) + '）。', 'If price stays flat, the light turns ' + (e.ok ? 'off' : 'on') + ' around ' + ymd(f.date) + ' (the year-ago price ' + (e.ok ? 'rises to ' : 'falls to ') + fmt.usd(f.price) + ').');
        return s1;
      case 'mvrv1y': return _T('MVRV ', 'MVRV ') + fmt.n(e.value, 3) + _T('，一年均值 ', ', 1-year mean ') + fmt.n(e.ref, 3) + _T('，差 ', ', gap ') + fmt.pct((e.value / e.ref - 1) * 100, 1) + _T('；均值線移動慢，看 MVRV 何時穿過它。', '; the mean moves slowly, so watch where MVRV crosses it.');
      case 'rcgrowth': return _T('實現市值 30 日 ', 'Realized cap, 30 days: ') + fmt.pct(e.value, 2) + _T('；轉負燈號就熄。', '; the light goes off if it turns negative.');
      case 'xs90': return _T('交易所供給 90 日 ', 'Exchange supply, 90 days: ') + fmt.pct(e.value, 2) + _T('；轉正燈號就熄（CoinMetrics 地址歸屬會事後修正）。', '; the light goes off if it turns positive (CoinMetrics address tags get revised).');
      case 'sth': return _T('收盤比短期持有者成本 ', 'Close vs short-term holder cost: ') + fmt.pct((c / e.value - 1) * 100, 1) + _T('（成本 ' + fmt.usd(e.value) + '，' + ymd(e.date) + '）。', ' (cost ' + fmt.usd(e.value) + ', ' + ymd(e.date) + ').');
      case 'tmm':
        var up = t.direction === 'up', s2 = _T('差距 ', 'Gap ') + fmt.pct(e.value, 2) + _T('（' + ymd(e.date) + '）。', ' (' + ymd(e.date) + '). ');
        s2 += t.days ? _T('以近 30 日速度（短期持有者成本每天 ' + sgn(t.sth_per_day) + '、真實市場均價 ' + sgn(t.tmm_per_day) + ' 美元），約 ' + t.days + ' 天後、' + ymd(t.date) + ' 前後' + (up ? '上穿' : '下穿') + '（約 ' + fmt.usd(t.sth_at) + '）。',
                                'At the last 30 days\' pace (STH cost ' + sgn(t.sth_per_day) + '/day, true market mean ' + sgn(t.tmm_per_day) + '/day), they cross ' + (up ? 'up' : 'down') + ' in about ' + t.days + ' days, around ' + ymd(t.date) + ' (near ' + fmt.usd(t.sth_at) + '). ')
                     : _T('以近 30 日速度不會交叉。', 'At the last 30 days\' pace they do not cross. ');
        return s2 + _T('只是線性外推：價格跌破短期持有者成本時，成本線就不再上升。', 'Linear extrapolation only: if price falls below the STH cost, that line stops rising.');
    }
    return '';
  }
  function evCharts(ev) {
    var sv = (D.cycle.stage || {}).viz; if (!sv || !ev.items) return '';
    var by = {}; ev.items.forEach(function (e) { by[e.id] = e; });
    // 2026-11-04 整體審查：6 張佐證圖（約 1,800px）預設收起，上面的燈號表已列出哪幾盞亮；點開或從別處連過來（#cycle/ev-tmm）才展開
    var nEv = EV_ORDER.filter(function (id) { return by[id]; }).length;
    return '<div class="evfold fold"><button type="button" class="ev-open">' + _T('展開 ' + nEv + ' 張佐證圖（每盞燈的走勢與離翻轉多遠）', 'Show the ' + nEv + ' evidence charts (each light\'s trend and how far from flipping)') + '</button><div class="evcharts">' + EV_ORDER.filter(function (id) { return by[id]; }).map(function (id) {
      var e = by[id], PX = [_T('BTC 價格', 'BTC price'), 'var(--ink-3)'], PX2 = [_T('BTC 價格（上格）', 'BTC price (top pane)'), 'var(--ink-3)'], STH = [_T('短期持有者成本', 'STH cost'), 'var(--s2)'];
      var lg = { tmm: [STH, [_T('真實市場均價', 'True market mean'), 'var(--s3)'], PX, [_T('近 30 日速度外推', 'Extrapolated at 30-day pace'), 'var(--ink-3)', 'dash']], sth: [STH, PX],
        mom12: [PX, [_T('一年前的價格', 'Price a year earlier'), 'var(--s2)'], [_T('未來要比的價格（已知）', 'Year-ago price ahead (known)'), 'var(--s2)', 'dash']],
        mvrv1y: [['MVRV', 'var(--s1)'], [_T('一年均值', '1-year mean'), 'var(--s3)'], PX2], rcgrowth: [[_T('實現市值 30 日變化', 'Realized cap, 30-day change'), 'var(--s4)'], PX2], xs90: [[_T('交易所供給 90 日變化', 'Exchange supply, 90-day change'), 'var(--s2)'], PX2] }[id];
      var seg = id === 'tmm' ? '<div class="seg" id="ev-tmm-seg"><button aria-pressed="true" data-v="1">' + _T('近 1 年', '1 year') + '</button><button aria-pressed="false" data-v="3">' + _T('3 年', '3 years') + '</button></div>' : '';
      return '<div class="evc' + (id === 'tmm' ? ' wide' : '') + '"><div class="panel-h"><h3><span class="mk-s' + (e.ok ? ' ok' : '') + '">' + (e.ok ? '✓' : '×') + '</span>' + esc(_T(e.label, (EV_EN[id] || [])[0] || e.label)) + '</h3>' + seg + '</div><p class="note">' + esc(evSay(e, sv)) + '</p>' + legend(lg) + '<div class="chart" id="c-ev-' + id + '"></div></div>';
    }).join('') + '</div>' + _T('<p class="note">走勢圖近 3 年、每 3 天一點；BTC 價格（CoinMetrics）是灰線，或畫在上格。外推與「價格不動」都只是讀值，不是預測。</p>', '<p class="note">Charts cover 3 years, one point every 3 days; the BTC price (CoinMetrics) is the grey line or the top pane. Extrapolations and “if price stays flat” are readings, not forecasts.</p>') + '</div>';
  }
  var evTmmYears = 1;
  function drawEv() {
    var sv = (D.cycle.stage || {}).viz; if (!sv) return;
    var px = sv.px || [], today = dnOf(D.meta.bar_date), PXn = _T('BTC 價格', 'BTC price');
    var px2 = { name: PXn, data: px, color: 'var(--ink-3)', w: 1.2, end: false, y2: true, fmt: fmt.usd };
    var pxS = { name: PXn, data: px, color: 'var(--ink-3)', w: 1.4, end: false };
    var pctf = function (d) { return function (v) { return (v > 0 ? '+' : '') + v.toFixed(d) + '%'; }; };
    var C = {
      mom12: function (el) { var a = (sv.mom12 || {}).ago || [], af = (sv.mom12 || {}).ahead_from; lineChart(el, { h: 200, log: true, series: [pxS, { name: _T('一年前的價格', 'Price a year earlier'), data: a.filter(function (r) { return r[0] <= af; }), color: 'var(--s2)', w: 1.6, end: false }, { name: _T('未來要比的價格', 'Year-ago price ahead'), data: a.filter(function (r) { return r[0] >= af; }), color: 'var(--s2)', dash: '4 4', w: 1.6, end: false }], vlines: [{ x: today, label: _T('今天', 'today') }], tipFmt: fmt.usd, aria: _T('12 個月動能', '12-month momentum') }); },
      mvrv1y: function (el) { var v = sv.mvrv1y || {}; lineChart(el, { h: 200, log2: true, series: [px2, { name: 'MVRV', data: v.v || [], color: 'var(--s1)', w: 1.8 }, { name: _T('一年均值', '1-year mean'), data: v.ma || [], color: 'var(--s3)', w: 1.6, end: false }], yFmt: function (x) { return x.toFixed(1); }, tipFmt: function (x) { return x.toFixed(3); }, aria: _T('MVRV 對一年均值', 'MVRV vs 1-year mean') }); },
      rcgrowth: function (el) { lineChart(el, { h: 200, log2: true, series: [px2, { name: _T('30 日變化', '30-day change'), data: (sv.rcgrowth || {}).v || [], color: 'var(--s4)', area: true }], refs: [{ y: 0, color: 'var(--ink-3)' }], yFmt: pctf(0), tipFmt: pctf(2), aria: _T('資金流入', 'Capital inflow') }); },
      xs90: function (el) { lineChart(el, { h: 200, log2: true, series: [px2, { name: _T('90 日變化', '90-day change'), data: (sv.xs90 || {}).v || [], color: 'var(--s2)', area: true }], refs: [{ y: 0, color: 'var(--ink-3)' }], yFmt: pctf(0), tipFmt: pctf(2), aria: _T('交易所供給', 'Exchange supply') }); },
      sth: function (el) { lineChart(el, { h: 200, log: true, series: [pxS, { name: _T('短期持有者成本', 'STH cost'), data: (sv.sth || {}).v || [], color: 'var(--s2)', w: 1.8 }], tipFmt: fmt.usd, aria: _T('短期持有者成本', 'STH cost') }); },
      tmm: function (el) {
        var t = sv.tmm || {}, pj = t.proj || {}, est = t.est || {}, sth = (sv.sth || {}).v || [], x0 = t.tmm && t.tmm.length ? t.tmm[0][0] : null;
        if (evTmmYears === 1) x0 = Math.max(x0 || 0, today - 365);
        t = Object.assign({}, t, { tmm: (t.tmm || []).filter(function (r) { return r[0] >= x0; }), crosses: (t.crosses || []).filter(function (c) { return c[0] >= x0; }) });
        var mk = (t.crosses || []).map(function (c) {   // 歷史交叉點：標在真實市場均價線上
          var r = (t.tmm || []).filter(function (q) { return q[0] >= c[0]; })[0], d = new Date(c[0] * 864e5); if (!r) return null;
          return { x: c[0], y: r[1], label: (c[1] === 'up' ? '↑ ' : '↓ ') + d.getUTCFullYear() + '/' + (d.getUTCMonth() + 1), color: c[1] === 'up' ? 'var(--up)' : 'var(--down)', below: c[1] === 'down' };
        }).filter(Boolean);
        lineChart(el, { series: [{ name: PXn, data: px.filter(function (r) { return x0 == null || r[0] >= x0; }), color: 'var(--ink-3)', w: 1.2, end: false }, { name: _T('短期持有者成本', 'STH cost'), data: sth.filter(function (r) { return x0 == null || r[0] >= x0; }), color: 'var(--s2)', w: 2 }, { name: _T('真實市場均價', 'True market mean'), data: t.tmm || [], color: 'var(--s3)', w: 2 },
          { name: _T('外推', 'Extrapolated'), data: pj.sth || [], color: 'var(--s2)', dash: '4 4', w: 1.6, end: false, tip: false }, { name: _T('外推', 'Extrapolated'), data: pj.tmm || [], color: 'var(--s3)', dash: '4 4', w: 1.6, end: false, tip: false }],
          h: evTmmYears === 1 ? 240 : 220, marks: mk, vlines: est.days ? [{ x: dnOf(est.date), label: _T('外推交叉 ', 'cross ') + est.date.slice(5).replace('-', '/') }] : [], tipFmt: fmt.usd, aria: _T('短期持有者成本 vs 真實市場均價', 'STH cost vs true market mean') });
      }
    };
    EV_ORDER.forEach(function (id) { var el = $('#c-ev-' + id); if (el && C[id]) mount(el, C[id]); });
    var sg = $('#ev-tmm-seg'); if (sg) sg.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; evTmmYears = +b.getAttribute('data-v'); this.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); C.tmm($('#c-ev-tmm')); });
  }
  var TM_CAT_EN = { '鏈上估值': 'On-chain valuation', '持有者行為': 'Holder behavior', '資金流與機構': 'Flows & institutions', '槓桿與衍生品': 'Leverage & derivatives', '情緒': 'Sentiment' };
  function tmVerdict(ct) {
    if (!ct || !ct.verdict) return '';
    if (LANG !== 'en') return ct.verdict;
    return ct.status === 'testing' && ct.low_price ? 'Testing: if price holds above the candidate low of ' + fmt.usd(ct.low_price) + ' (' + ct.low_date + ') through ' + ct.decisive_date + ', it supports “this low was the cycle bottom; bear markets are shallower in the ETF era”. A break below rejects the hypothesis.' : '';
  }
  function staleTag() { return N && N.stale ? _t('<span class="chip">上一期 ') + fmt.md(N.date) + '</span>' : ''; }
  function actionsHtml() {
    var a = N && N.actions || [], L = { do: _t('可以做'), dont: _t('不要做'), watch: _t('要盯'), flip: _t('會推翻') };
    if (!a.length) return _t('<p class="note">本期沒有寫。</p>');
    return '<ul class="acts">' + a.map(function (x) { return '<li><span class="b ' + esc(x.kind) + '">' + (L[x.kind] || esc(x.kind)) + '</span><span><b>' + esc(x.head) + '</b>' + esc(x.text || '') + '</span></li>'; }).join('') + '</ul>';
  }
  function changesHtml() {
    var a = N && N.changes || [], AR = { up: ['▲', 'u'], down: ['▼', 'd'], flat: ['■', ''] };
    if (!a.length) return _t('<p class="note">本期沒有寫。</p>');
    return '<ul class="deltas">' + a.map(function (x) { var r = AR[x.dir] || AR.flat; return '<li><span class="ar ' + r[1] + '">' + r[0] + '</span><div><h3>' + esc(x.title) + '</h3>' + (x.fig ? '<div class="fig num">' + esc(x.fig) + '</div>' : '') + '<p>' + esc(x.say || '') + '</p></div></li>'; }).join('') + '</ul>';
  }
  /* 今日發現（2026-10-23）：每日任務寫的 findings（拆解、交叉比對、其他解釋、追蹤條件）、上期發現的後續，以及資料管線自動偵測的異動（pipeline/signals.py） */
  var CONF = { high: ['可信度高', 'High confidence', 'up'], medium: ['可信度中', 'Medium confidence', ''], low: ['可信度低', 'Low confidence', 'down'] };
  var FU_ST = { confirmed: ['✓', '確認', 'Confirmed', 'u'], refuted: ['✗', '推翻', 'Refuted', 'd'], expired: ['–', '到期結案', 'Expired', ''], open: ['…', '追蹤中', 'Watching', ''] };
  var SIG_K = { extreme: ['極端值', 'Extreme'], jump: ['急變', 'Sharp move'], cross: ['翻轉', 'Flip'], level: ['關鍵價位', 'Key level'], streak: ['連續', 'Streak'], combo: ['組合', 'Combo'] };
  function lt(o) { return !o ? '' : typeof o === 'string' ? o : (LANG === 'en' && o.en) || o.zh || ''; }
  function jumpA(page, chart, label) { return page ? '<a class="jump" href="#' + esc(page) + '" data-chart="' + esc(chart || '') + '">' + label + '</a>' : ''; }
  function chartKey(ch) { return ALIAS[ch] ? ALIAS[ch][1] : ch; }   // 併掉的圖：異動標記改標在保留的那一張
  function sigOn(chart) { return ((D.signals || {}).items || []).filter(function (s) { return s.chart && chartKey(s.chart) === chart; }); }
  function sigV(el) { return el && el.id ? sigOn(el.id.replace(/^c-/, '')).filter(function (s) { return s.x != null; }).map(function (s) { return { x: s.x, label: _T('異動', 'Signal') }; }) : []; }
  function findingsHtml() {
    var has = N && N.findings, fs = (N && N.findings) || [], fu = (N && N.followups) || [], sg = (D.signals || {}).items || [];
    if (!has && !sg.length) return '';
    var row = function (v, z, e) { return v ? '<div><dt>' + _T(z, e) + '</dt><dd>' + esc(v) + '</dd></div>' : ''; };
    var cards = fs.map(function (f, i) {
      var c = CONF[f.confidence] || CONF.medium, cks = Array.isArray(f.check) ? f.check : f.check ? [f.check] : [];
      var ck = cks.length ? '<div><dt>' + _T('追蹤條件', 'Checks') + '</dt><dd>' + cks.map(function (k) { return esc(k.label || (k.path + ' ' + k.op + ' ' + k.value)) + _T('（成立＝' + (k.means === 'refute' ? '推翻' : '確認') + '，期限 ' + fmt.md(k.by) + '）', ' (' + (k.means === 'refute' ? 'refutes' : 'confirms') + ' if met, by ' + fmt.md(k.by) + ')'); }).join('<br>') + '</dd></div>' : '';
      return '<article class="find"><div class="find-h"><span class="idx">' + ('0' + (i + 1)).slice(-2) + '</span><span class="chip ' + c[2] + '">' + _T(c[0], c[1]) + '</span>' + jumpA(f.module, f.chart, _T('看圖 →', 'See chart →')) + '</div>' +
        '<h3>' + esc(f.title) + '</h3>' + (f.lean ? '<p class="lean">' + impChip(f.lean) + (f.lean_why ? '<span>' + esc(f.lean_why.replace(/^(偏多|偏空|中性)[：:]\s*|^(Bullish|Bearish|Neutral):\s*/, '')) + '</span>' : '') + '</p>' : '') + '<p class="what">' + esc(f.what || '') + '</p>' +
        '<details><summary>' + _T('拆解、其他解釋與追蹤條件', 'Breakdown, alternatives and checks') + '</summary><dl>' + row(f.why, '拆解', 'Breakdown') + row(f.alt, '其他解釋', 'Alternatives') + row(f.history, '過去', 'History') + row(f.so, '所以呢', 'So what') + row(f.next, '接下來看', 'Watch next') + ck + '</dl></details></article>';
    }).join('');
    // 2026-11-04 頭版重排：今天結案的（確認／推翻／到期）照常列出；仍在追蹤的收成一行，點開才看（原本 12 則「追蹤中」把新發現壓到下面）
    var fuLi = function (f) { var st = FU_ST[f.status] || FU_ST.open; return '<li><span class="ar ' + st[3] + '">' + st[0] + '</span><div><h3>' + esc(f.title) + ' <span class="chip">' + _T(st[1], st[2]) + '</span></h3>' + (f.since ? '<div class="fig num">' + _T('自 ', 'since ') + fmt.md(f.since) + '</div>' : '') + '<p>' + esc(f.say || '') + '</p></div></li>'; };
    var fuDone = fu.filter(function (f) { return f.status && f.status !== 'open' && FU_ST[f.status]; }), fuOpen = fu.filter(function (f) { return fuDone.indexOf(f) < 0; });
    var fuCnt = ['confirmed', 'refuted', 'expired', 'open'].map(function (k) { var n = (k === 'open' ? fuOpen : fuDone.filter(function (f) { return f.status === k; })).length; return n ? _T(FU_ST[k][1] + ' ' + n, n + ' ' + FU_ST[k][2].toLowerCase()) : ''; }).filter(Boolean).join(' · ');
    var fuH = fu.length ? '<div class="fu"><h4>' + _T('上期發現的後續', 'Follow-ups') + '<span class="note">' + (fuDone.length ? '' : _T('今天沒有結案 · ', 'none resolved today · ')) + fuCnt + '</span></h4>' +
      (fuDone.length ? '<ul class="deltas">' + fuDone.map(fuLi).join('') + '</ul>' : '') +
      (fuOpen.length ? '<details class="fu-open"><summary>' + _T('看追蹤中的 ' + fuOpen.length + ' 則（條件還沒成立，期限內每天檢查）', 'Show the ' + fuOpen.length + ' being tracked (conditions not met yet; checked daily until the deadline)') + '</summary><ul class="deltas">' + fuOpen.map(fuLi).join('') + '</ul></details>' : '') + '</div>' : '';
    var sgH = sg.length ? '<details class="sigs"' + (fs.length ? '' : ' open') + '><summary>' + _T('自動偵測的異動 ', 'Detected signals ') + sg.length + (D.signals.n > sg.length ? ' / ' + D.signals.n : '') + '</summary><ul>' + sg.map(function (x) {
        var k = SIG_K[x.kind] || ['', ''];
        return '<li><span class="chip ' + (x.dir === 'up' ? 'up' : x.dir === 'down' ? 'down' : '') + '">' + _T(k[0], k[1]) + '</span>' + (x.new ? '<span class="new">' + _T('新', 'New') + '</span>' : '<span class="days">' + _T('第 ' + x.days + ' 天', 'day ' + x.days) + '</span>') +
          '<div><b>' + esc(lt(x.title)) + '</b> ' + jumpA(x.page, x.chart, '→') + '<span class="fig num">' + esc(lt(x.fig)) + '</span>' + (x.means ? '<span class="means">' + esc(lt(x.means)) + '</span>' : '') +
          '<details class="sig-more"><summary>' + _T('規則、數字與過去同樣情況', 'Rule, numbers and past cases') + '</summary>' + sigDetail(x, true) + '</details></div></li>';
      }).join('') + '</ul><p class="note">' + _T('資料管線每天依寫死的規則偵測：一年最極端的 2%、7 日急變、狀態翻轉、關鍵價位 ±3%、連續、跨指標組合。上面的發現才是判讀；這裡只作讀值。', 'Detected daily by fixed rules: the most extreme 2% of the past year, sharp 7-day moves, state flips, key levels within ±3%, streaks, cross-indicator combos. The findings above are the interpretation; these are readings only.') + '</p></details>' : '';
    // 整體多空（2026-10-23 使用者要求）：依各則 lean 計數，偏多多於偏空＝整體偏多，反之偏空，相同＝多空互見
    var cnt = { bull: 0, bear: 0, neutral: 0 }; fs.forEach(function (f) { if (cnt[f.lean] != null) cnt[f.lean]++; });
    var ov = cnt.bull > cnt.bear ? 'bull' : cnt.bear > cnt.bull ? 'bear' : 'neutral', nl = cnt.bull + cnt.bear + cnt.neutral;
    var sum = nl ? '<p class="find-sum"><span class="imp ' + ov + '">' + (ov === 'bull' ? _T('整體偏多', 'Leaning bullish') : ov === 'bear' ? _T('整體偏空', 'Leaning bearish') : cnt.bull ? _T('多空互見', 'Mixed') : _T('整體中性', 'Neutral overall')) + '</span><span>' +
      _T('偏多 ' + cnt.bull + ' · 偏空 ' + cnt.bear + ' · 中性 ' + cnt.neutral, cnt.bull + ' bullish · ' + cnt.bear + ' bearish · ' + cnt.neutral + ' neutral') + '</span><span class="note">' + _T('描述這些發現對價格的一般含意，不是預測', 'what these findings usually mean for price; not a forecast') + '</span></p>' : '';
    var empty = has ? _T('本期沒有值得特別注意的異動。', 'Nothing unusual enough to call out today.') : _T('本期判讀還沒有寫發現；下面是自動偵測的異動。', 'Today\'s commentary has no findings yet; detected signals are below.');
    return _T('<div class="sec-h" id="pn-findings"><h2>今日發現</h2><span class="en">The Findings</span><hr></div>', '<div class="sec-h" id="pn-findings"><h2>Today\'s findings</h2><span class="en">The Findings</span><hr></div>') +
      sum + '<div class="finds">' + (cards || '<p class="note">' + empty + '</p>') + '</div>' + fuH + sgH;
  }
  /* 2026-11-06 使用者要求（「不知道在哪裡可以看怎樣的異動，異動哪裡了，說明什麼，意味著什麼」）：每則異動的完整說明——
     觸發的規則、從哪天開始、數字變化、一般含意、過去同樣情況之後 30 天價格。rule／means／hist 由 pipeline/signal_means.py 產生 */
  function sigHist(h) {
    if (!h) return '';
    var pc = function (v) { return v == null ? _T('未滿 30 天', 'n/a yet') : fmt.pct(v, 1); };
    if (!h.n) return '<p>' + _T('資料期間（' + ymdD(h.since) + ' 起）裡，過去沒有同樣的情況。', 'No earlier case in the data (since ' + ymdD(h.since) + ').') + '</p>';
    return '<p>' + _T(ymdD(h.since) + ' 起出現過 ' + h.n + ' 次（不含這次）' + (h.fwd30_med != null ? '，之後 30 天價格的中位數 <b>' + fmt.pct(h.fwd30_med, 1) + '</b>' : '') + (h.base30_med != null ? '；同一段期間任選一天，之後 30 天的中位數是 ' + fmt.pct(h.base30_med, 1) : '') + '。',
        h.n + ' earlier case' + (h.n > 1 ? 's' : '') + ' since ' + ymdD(h.since) + (h.fwd30_med != null ? '; median price change over the next 30 days <b>' + fmt.pct(h.fwd30_med, 1) + '</b>' : '') + (h.base30_med != null ? ', versus ' + fmt.pct(h.base30_med, 1) + ' for any day in the same period' : '') + '.') + '</p>' +
      '<ul class="sig-h">' + (h.last || []).slice().reverse().map(function (p) { return '<li><span class="num">' + ymdD(p.d) + '</span><span class="num ' + (p.fwd30 == null ? '' : p.fwd30 >= 0 ? 'up' : 'dn') + '">' + pc(p.fwd30) + '</span></li>'; }).join('') + '</ul>' +
      '<p class="note">' + _T(((h.last || []).length < h.n ? '列出最近 ' + h.last.length + ' 次；' : '') + '右邊是那次之後 30 天的價格變化；' + (h.n < 10 ? '只有 ' + h.n + ' 次，樣本很少，只當背景參考。' : '過去不代表這次。'), ((h.last || []).length < h.n ? 'The latest ' + h.last.length + ' are listed. ' : '') + 'Right: price change over the following 30 days. ' + (h.n < 10 ? 'Only ' + h.n + ' cases — background only.' : 'The past does not decide this time.')) + '</p>';
  }
  function sigDetail(x, inList) {
    var k = SIG_K[x.kind] || ['', ''], row = function (h, b) { return b ? '<div class="sd-r"><span class="sd-k">' + h + '</span><div class="sd-v">' + b + '</div></div>' : ''; };
    var when = _T('資料日期 ' + ymdD(x.date) + '；' + (x.new ? '今天第一次出現' : ymdD(x.first_seen) + ' 起連續出現，今天第 ' + x.days + ' 天') + '。', 'Data date ' + ymdD(x.date) + '; ' + (x.new ? 'first seen today' : 'seen every day since ' + ymdD(x.first_seen) + ', day ' + x.days) + '.') +
      (x.x != null && !inList ? _T('圖上橘色直線「異動」標的就是這一天。', ' The orange "Signal" line on the chart marks this day.') : '');
    var num = [x.ctx, x.decomp].filter(Boolean).map(function (t) { return esc(lt(t)); }).join('；') + (x.caveat ? '<span class="note">' + _T('注意：', 'Note: ') + esc(lt(x.caveat)) + '</span>' : '');
    return '<div class="sig-d">' +
      row(_T('哪種異動', 'What fired'), '<span class="chip">' + _T(k[0], k[1]) + '</span> ' + esc(lt(x.rule) || '')) +
      row(_T('什麼時候', 'When'), when) +
      row(_T('背景', 'Context'), num) +
      row(_T('代表什麼', 'What it usually means'), x.means ? esc(lt(x.means)) : '') +
      row(_T(x.hist && x.hist.what === 'cross' ? '過去同樣翻轉' : '過去同樣情況', 'Past cases'), sigHist(x.hist)) +
      (inList ? '' : '<p class="note">' + _T('自動偵測、規則寫死，只作讀值，不是買賣訊號。當天的判讀看頭版「今日發現」', 'Detected automatically by fixed rules; a reading, not a trade signal. For the day\'s interpretation see Today\'s findings on the front page ') + jumpA('overview', 'findings', '→') + '</p>') + '</div>';
  }
  /* 有異動的圖：圖上方一行（哪一項、數字），點開看完整說明；圖上標日期線（lineChart 的 sigV） */
  function markSignals(root) {
    var by = {}; ((D.signals || {}).items || []).forEach(function (s) { if (s.chart) { var k = chartKey(s.chart); (by[k] = by[k] || []).push(s); } });
    Object.keys(by).forEach(function (ch) {
      var el = (root || document).querySelector('#c-' + ch); if (!el || (el.previousElementSibling && el.previousElementSibling.classList.contains('sig-flag'))) return;
      el.insertAdjacentHTML('beforebegin', '<div class="sig-flag">' + by[ch].map(function (s) { return '<details><summary><span class="chip flare"><i></i>' + _T('異動', 'Signal') + '</span><b>' + esc(lt(s.title)) + '</b> <span class="fig">' + esc(lt(s.fig)) + '</span><span class="more">' + _T('看說明', 'Details') + '</span></summary>' + sigDetail(s) + '</details>'; }).join('') + '</div>');
    });
  }
  function researchHtml() {
    var r = N && N.research || {}, rows = r.items || [];
    if (!rows.length) return '<p class="note">' + esc(r.summary || _t('本期沒有新的機構研報。')) + '</p>';
    return (r.summary ? '<p class="say">' + esc(r.summary) + '</p>' : '') + _t('<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:20%"><col style="width:44%"><col style="width:36%"></colgroup><thead><tr><th>來源</th><th>重點</th><th>對本站判斷的意義</th></tr></thead><tbody>') +
      rows.map(function (x) { var src = x.url ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(x.source) + '</a>' : esc(x.source); return '<tr><td><b>' + src + '</b><br><span class="note">' + esc(x.title || '') + (x.date ? _t('，') + fmt.md(x.date) : '') + (x.access === 'title_only' ? _t('・只取得標題') : '') + '</span></td><td>' + esc(x.points) + '</td><td>' + esc(x.meaning) + '</td></tr>'; }).join('') +
      _t('</tbody></table></div><p class="note">研報只作文字對照，不改變任何規則；只取得標題的不作判斷依據。</p>');
  }
  function newsItem(n, lead, ix, brief) {   // brief：頭版側欄只列標題（2026-11-04；完整解讀在消息版，原本頭版與消息版各印一次）
    if (brief) return '<article class="news-item brief"><div class="news-meta"><span class="cat">' + esc(catT(n.cat)) + '</span>' + impChip(n.impact) + '<span>' + esc(n.time.slice(5).replace('-', '/')) + '</span></div><h3><a href="#news">' + esc(n.title) + '</a></h3></article>';
    return '<article class="' + (lead ? 'news-lead' : 'news-item') + '">' + (ix ? '<span class="idx">' + ('0' + ix).slice(-2) + '</span>' : '') + '<div class="news-meta"><span class="cat">' + esc(catT(n.cat)) + '</span>' + impChip(n.impact) + '<span>' + esc(n.time.slice(5).replace('-', '/')) + '</span></div><h3>' + esc(n.title) + _t('</h3><div class="read-box"><b class="lbl">解讀</b>') + esc(n.read) + _t('</div><div class="src-link">來源：<a href="') + esc(n.url) + '" target="_blank" rel="noopener">' + esc(n.source) + '</a>' + (n.module ? ' · <a href="#' + n.module + _t('">看相關數據 →</a>') : '') + '</div></article>';
  }

  /* ---------------- 數字解讀（2026-10-12 使用者要求：每個數字都說明「現在代表什麼」） ----------------
     由當日數值套固定門檻自動產生（門檻寫在句子裡），不是預測，也不連動出場規則。
     tone：pos 偏多（對價格有利）、neg 偏空（對價格不利）、warn 留意（偏熱或接近門檻）、neu 中性 */
  var TONE = { pos: [_t('偏多'), 'up'], neg: [_t('偏空'), 'down'], warn: [_t('留意'), 'warn'], neu: [_t('中性'), ''] };
  function band(v, cuts, words) { for (var i = 0; i < cuts.length; i++) if (v < cuts[i]) return words[i]; return words[cuts.length]; }
  function pctWord(p, lab) {
    if (p == null) return '';
    var w = band(p, [20, 40, 60, 80], [_t('低檔'), _t('偏低'), _t('中間'), _t('偏高'), _t('高檔')]);
    return _T((lab || '四年') + '第 ' + fmt.n(p, 0) + ' 百分位（' + w + '）', ord(p) + ' percentile ' + (lab === '本輪' ? 'this cycle' : 'over 4 years') + ' (' + w + ')');
  }
  function tnHtml(t) { t = TONE[t] || TONE.neu; return '<span class="tn ' + t[1] + '">' + t[0] + '</span>'; }
  /* items：[名稱, 數值 HTML, 解讀文字, tone]；解讀為空的整列略過 */
  /* 2026-11-06 版面整理：「我們的看法」排第一列（原本在最後，要往下滑才看得到）；圖表面板的細項讀值超過 3 列時，其餘收進「更多讀值」，
     讓圖往上移。keep＝不收（「這些數字代表什麼」、出場規則這類本身就是重點的列表） */
  var RD_SHOW = 3;
  function interpHtml(items, keep) {
    items = items.filter(function (x) { return x && x[2]; });
    if (!items.length) return '';
    var vw = items.filter(function (x) { return x[4]; }), rest = items.filter(function (x) { return !x[4]; });
    var one = function (x) { return '<div class="it' + (x[4] ? ' view' : '') + '"><span class="k">' + esc(x[0]) + '</span><span class="v num">' + x[1] + '</span>' + tnHtml(x[3]) + '<span class="d">' + (x[4] && x[5] != null ? esc(x[5]) + (x[6] ? '<span class="chg"><b>' + _T('會改變看法', 'What would change it') + '</b>' + esc(x[6]) + '</span>' : '') : esc(x[2])) + '</span></div>'; };
    var cut = keep || rest.length <= RD_SHOW + 1 ? rest.length : RD_SHOW;
    return '<div class="interp' + (vw.length ? ' has-view' : '') + '">' + vw.concat(rest.slice(0, cut)).map(one).join('') +
      (cut < rest.length ? '<details class="rd-more"><summary>' + _T('更多讀值（' + (rest.length - cut) + '）', 'More readings (' + (rest.length - cut) + ')') + '</summary>' + rest.slice(cut).map(one).join('') + '</details>' : '') + '</div>';
  }
  /* 2026-11-05 使用者要求：不只說數據，要基於數據給出具體觀點。每個面板最後一列「我們的看法」：傾向＋理由（可引用其他面板互相印證）＋會改變看法的條件。
     由當天資料自動判斷；不寫目標價、不標買賣區、不連動任何倉位 */
  function viewRow(stance, text, change, tone) { return [_T('我們的看法', 'Our read'), stance, text + (change ? _T('會改變看法：', ' What would change it: ') + change : ''), tone || 'neu', 1, text, change]; }
  function lvOf(k) { var L = ((D.cycle || {}).levels || {}).levels || []; for (var i = 0; i < L.length; i++) if (L[i].key === k) return L[i].value; return null; }
  /* 2026-11-06 版面整理：長的版面分組，組名同時出現在版內目錄 */
  function grpH(key, zh, en, note) { return '<div class="sec-h grp-h span-12" id="grp-' + key + '"><h2>' + _T(zh, en) + '</h2><hr>' + (note ? '<span class="src">' + note + '</span>' : '') + '</div>'; }
  function interpPanel(items, src) { var h = interpHtml(items, true); return h ? panel('span-12', _t('這些數字代表什麼'), src || _t('依當日數值套固定門檻自動產生 · 非投資建議'), h) : ''; }
  function rdRow(rd, cols) { return rd && rd[0] ? '<tr class="rd"><td colspan="' + cols + '">' + tnHtml(rd[1]) + esc(rd[0]) + '</td></tr>' : ''; }
  function top3Line(p, key) {   // 頂部三指標共用的提醒
    if (p == null) return '';
    return p >= 80 ? _t('這是頂部三指標之一，四年百分位已過 80；三項中任兩項到 80 才進入頂部區。') : _t('這是頂部三指標之一，四年百分位到 80 才算到線，現在還差 ') + fmt.n(80 - p, 0) + _t(' 個百分位。');
  }
  function chgLine(v) { return v.chg30_pct == null ? '' : _t('30 日 ') + fmt.pct(v.chg30_pct, 1) + _t('。'); }

  /* 鏈上指標表（bitcoin-data） */
  var OC_READ = {
    'mvrv-zscore': function (v) { var x = v.value;
      return [band(x, [0, 1, 2.5, 3.5], [_t('低於 0：市值低於全體持有者的總成本，歷來是週期底部區'), _t('0–1：偏低估'), _t('1–2.5：估值中性，不便宜也不貴'), _t('2.5–3.5：偏熱'), _t('3.5 以上：歷史頂部區')]) + _t('；') + pctWord(v.pct_4y) + _t('。') + top3Line(v.pct_4y), x < 1 ? 'pos' : x < 2.5 ? 'neu' : x < 3.5 ? 'warn' : 'neg']; },
    'nupl': function (v) { var x = v.value;
      return [band(x, [0, 0.25, 0.5, 0.75], [_t('低於 0（投降區）：整體帳面虧損'), _t('0–0.25（希望／恐懼區）'), _t('0.25–0.5（樂觀／焦慮區）'), _t('0.5–0.75（信念區）：牛市中後段常見'), _t('0.75 以上（狂熱區）：歷史頂部')]) + _t('，市值中約 ') + fmt.n(x * 100, 0) + _t('% 是還沒實現的帳面獲利；') + pctWord(v.pct_4y) + _t('。') + top3Line(v.pct_4y), x < 0.25 ? 'pos' : x < 0.5 ? 'neu' : x < 0.75 ? 'warn' : 'neg']; },
    'puell-multiple': function (v) { var x = v.value, p = v.pct_4y;
      var s = band(x, [0.5, 1, 2, 4], [_t('低於 0.5：礦工收入極低，歷來對應底部'), _t('0.5–1：礦工收入低於一年平均'), _t('1–2：礦工收入略高於一年平均，屬正常'), _t('2–4：礦工收入明顯偏高'), _t('4 以上：歷史頂部區')]);
      if (p >= 80 && x < 2) s += _t('。絕對值不高，但過去四年多數時間比現在更低，所以百分位已過 80');
      return [s + _t('；') + pctWord(p) + _t('，') + chgLine(v) + top3Line(p), p >= 80 || x >= 2 ? 'warn' : x < 0.5 ? 'pos' : 'neu']; },
    'asopr': function (v) { return [soprLine(v.value, _t('排除一小時內轉手後，賣出的幣')), 'neu']; },
    'sth-sopr': function (v) { var x = v.value, d = (x - 1) * 100;
      return [Math.abs(d) <= 0.5 ? _t('短期持有者幾乎在成本價賣出（') + fmt.pct(d, 1) + _t('），多空正在成本線拉鋸；牛市裡回到 1 附近又彈起常是支撐，持續低於 1 代表短線資金在停損。')
        : d < 0 ? _t('短期持有者平均虧損 ') + fmt.n(-d, 1) + _t('% 賣出：新進場的人在停損，短線賣壓偏重。') : _t('短期持有者平均獲利 ') + fmt.n(d, 1) + _t('% 賣出：新進場的人有賺錢可以了結，短線結構健康。'), d < -0.5 ? 'neg' : d > 0.5 ? 'pos' : 'neu']; },
    'lth-sopr': function (v) { var x = v.value, s = x >= 1 ? _t('長期持有者賣出時平均獲利 ') + fmt.n((x - 1) * 100, 0) + '%' : _t('長期持有者在虧損賣出（少見，常出現在深熊）');
      if (v.ma7 && Math.abs(x / v.ma7 - 1) > 0.2) s += _t('；單日值跳動大，7 日均 ') + fmt.n(v.ma7, 2) + _t(' 比較能代表趨勢');
      if (v.chg30_pct > 30) s += _t('；30 日上升 ') + fmt.n(v.chg30_pct, 0) + _t('%，長期持有者獲利了結增加');
      return [s + _t('。'), x >= 3 ? 'warn' : 'neu']; },
    'illiquid-supply': function (v) { var p = v.pct_4y;
      return [_t('長期不動的幣有 ') + fmt.n(v.value / 1e6, 2) + _t('M 顆，') + pctWord(p) + _t('，') + chgLine(v) + (p >= 80 ? _t('囤幣量在高檔，籌碼鎖得緊，市場上可賣的幣少。') : p < 20 ? _t('囤幣量在四年低檔，長期持有的幣在被釋出，供給偏鬆。') : _t('囤幣量中性。')), p >= 80 ? 'pos' : p < 20 ? 'neg' : 'neu']; },
    'highly-liquid-supply': function (v) { var p = v.pct_4y;
      return [_t('隨時可交易的幣有 ') + fmt.n(v.value / 1e6, 2) + _t('M 顆，') + pctWord(p) + _t('，') + chgLine(v) + (p >= 80 ? _t('浮動籌碼在高檔，可賣的幣多，潛在賣壓較大（也可能是交易熱度回升）。') : p < 20 ? _t('浮動籌碼少，賣壓來源有限。') : _t('浮動籌碼中性。')), p >= 80 ? 'neg' : p < 20 ? 'pos' : 'neu']; }
  };
  function soprLine(x, who) { var d = (x - 1) * 100;
    return d < -2 ? who + _t('平均虧損 ') + fmt.n(-d, 1) + _t('% 賣出，常見於恐慌拋售。') : d < 0 ? who + _t('平均小虧 ') + fmt.n(-d, 1) + _t('% 賣出，有人在認賠。') : d <= 2 ? who + _t('平均小賺 ') + fmt.n(d, 1) + _t('% 賣出，獲利了結溫和。') : who + _t('平均獲利 ') + fmt.n(d, 1) + _t('% 賣出，獲利了結明顯。'); }

  /* 頂部雷達（本輪 2022/11 起百分位） */
  var RADAR_READ = {
    'lth-mvrv-zscore': function (v) { var p = v.pct_since_2022_11, tp = v.extreme_near_2025_top;
      return [_t('長期持有者的帳面獲利約是 2025 頂部時的 ') + fmt.n(v.value / tp * 100, 0) + _t('%；') + pctWord(p, '本輪') + (p >= 90 ? _t('，接近本輪高點，頂部風險升高。') : _t('。')), p >= 90 ? 'neg' : 'neu']; },
    'supply-in-profit-pct': function (v) { var x = v.value;
      return [_t('約 ') + fmt.n(100 - x, 0) + _t('% 的幣處於虧損；2025 頂部時 ') + fmt.n(v.extreme_near_2025_top, 1) + _t('% 的幣在獲利。') + (x >= 95 ? _t('幾乎人人獲利，歷來是頂部特徵。') : x <= 50 ? _t('一半以上的幣虧損，歷來是底部特徵。') : _t('介於頂部（95% 以上）與底部（50% 以下）之間。')), x >= 95 ? 'neg' : x <= 50 ? 'pos' : 'neu']; },
    'lth-net-position-change-30d-btc': function (v) { var x = v.value, tp = v.extreme_near_2025_top;
      return [x < 0 ? _T('長期持有者 30 日淨減少 ', 'Long-term holders shed a net ') + coins(-x, 1) + _T('，正在賣出（分配）', ' over 30 days — they are distributing') + (tp < 0 ? _T('，但規模只有 2025 頂部時（' + coins(-tp, 1) + '）的 ' + fmt.n(x / tp * 100, 0) + '%。', ', but that is only ' + fmt.n(x / tp * 100, 0) + '% of the 2025-top pace (' + coins(-tp, 1) + ').') : _t('。'))
        : _T('長期持有者 30 日淨增加 ' + coins(x, 1) + '，正在累積，籌碼被鎖住。', 'Long-term holders added a net ' + coins(x, 1) + ' over 30 days — accumulating and locking up supply.'), x > 0 ? 'pos' : x <= v.p10_since_2022_11 ? 'neg' : 'neu']; }
  };

  /* 訊號總表（2026-11-04 整體審查）：原本 8 個綜合讀數散在頭版、週期、鏈上三版，彼此關係沒交代。這裡分三組排在一起：
     方向（現在偏多還是偏空）、離頂部多近、離出場多遠。後兩組的條一律是「離觸發多近」：100% ＝碰到觸發線（或本輪極值），
     讀法一致；方向組用自己的刻度（階段三格、多空分數 −6～+6）。每列連到該指標的詳細圖。只作讀值，不新增任何判定 */
  /* 2026-11-06 版面整理：頭版彙整 7 張圖的「我們的看法」——從長線到短線排；每列：面板、傾向、會改變看法的條件，點了跳到那張圖。
     看法本身仍在各面板（同一份判斷，不重寫） */
  var VIEWS = [
    ['cycle', 'cyccmp', ['和前幾輪比', 'Versus past cycles'], function () { return ccSay(); }],
    ['onchain', 'lthrl', ['長期持有者已實現虧損', 'LTH realized loss'], function () { return rlSay(); }],
    ['market', 'levels', ['成本線與均線', 'Cost bases and averages'], function () { return lvSay(); }],
    ['onchain', 'sthband', ['短期持有者成本帶', 'STH cost bands'], function () { return sbSay(); }],
    ['onchain', 'agecost', ['1 週–1 個月持有者成本', '1w–1m holder cost'], function () { return acSay1m(); }],
    ['flows', 'ad', ['表觀需求', 'Apparent demand'], function () { return adSay(); }],   // 2026-11-08 搬到資金版
    ['onchain', 'lthc', ['長期持有者動向', 'Long-term holder moves'], function () { return lcSay(); }]
  ];
  function viewsHtml() {
    var rows = VIEWS.map(function (v) { var it = null; try { it = (v[3]() || []).filter(function (x) { return x && x[4]; })[0]; } catch (e) { console.error(e); } return it ? [v, it] : null; }).filter(Boolean);
    if (rows.length < 3) return '';
    var cnt = { pos: 0, neg: 0 }; rows.forEach(function (r) { var t = r[1][3]; if (t === 'pos') cnt.pos++; else if (t === 'neg' || t === 'warn') cnt.neg++; });
    return _T('<div class="sec-h"><h2>我們的看法</h2><span class="en">Our Read</span><hr>', '<div class="sec-h"><h2>Our read</h2><span class="en">Our Read</span><hr>') + '<span class="src">' +
      _T(rows.length + ' 張圖 · 偏多 ' + cnt.pos + '、偏弱 ' + cnt.neg + '、中性 ' + (rows.length - cnt.pos - cnt.neg) + ' · 依當日資料自動判斷 · 非投資建議', rows.length + ' charts · ' + cnt.pos + ' positive, ' + cnt.neg + ' soft, ' + (rows.length - cnt.pos - cnt.neg) + ' neutral · set by each day\'s data · not investment advice') + '</span></div>' +
      '<div class="views">' + rows.map(function (r) { var v = r[0], x = r[1];
        return '<div class="vw-r"><span class="k">' + esc(_T(v[2][0], v[2][1])) + '</span><span class="v">' + x[1] + '</span>' + tnHtml(x[3]) + jumpA(v[0], v[1], '→') +
          (x[6] ? '<p class="d"><b>' + _T('會改變看法', 'What would change it') + '</b>' + esc(x[6]) + '</p>' : '') + '</div>'; }).join('') + '</div>';
  }
  /* 晨昏指數（2026-11-08 使用者要求「用現在所有數據做一個更準確的週期圖，新的我們自己取名」，和週線多空分數並列；見 pipeline/dawn.py）：
     熱度 0–100＝五項估值和過去 4 年比的百分位平均；方向＝四項趨勢（連續 4 週才翻）；把一輪週期當成一天分五段。只用當天以前的資料，只作讀值 */
  var DW_STG = [['深夜', 'Deep night', '底部區', 'bottom zone'], ['入夜', 'Nightfall', '下跌', 'falling'], ['破曉', 'Daybreak', '初升', 'early rise'], ['白晝', 'Daylight', '上升', 'rising'], ['黃昏', 'Dusk', '過熱', 'overheated']];
  var DW_HL = { lnupl: ['長期持有者 NUPL', 'LTH NUPL'], rup: ['未實現獲利 ÷ 市值', 'Unrealized profit ÷ market cap'], pl: ['冪律殘差', 'Power-law residual'], rr: ['儲備風險', 'Reserve risk'], mvz: ['MVRV-Z', 'MVRV-Z'],
    d200: ['價格 ÷ 200 日均線', 'Price ÷ 200-day MA'], sth: ['價格 ÷ 短期持有者成本', 'Price ÷ STH cost basis'], asopr: ['aSOPR 30 日', 'aSOPR, 30-day'], rpl: ['實現獲利 ÷ 虧損 90 日', 'Realized profit ÷ loss, 90-day'] };
  function dwName(k, full) { var n = DW_STG[k] || ['—', '—', '', '']; return full ? _T(n[0] + '（' + n[2] + '）', n[1] + ' (' + n[3] + ')') : _T(n[0], n[1]); }
  function dwTr(c) { if (c.raw == null) return '—'; return c.key === 'asopr' ? fmt.n(1 + c.raw, 3) : c.key === 'rpl' ? fmt.n(Math.pow(10, c.raw), 2) : fmt.pct(c.raw * 100, 1); }
  function dwSay() {
    var x = D.cycle.dawn, it = [], th = x.th, k = x.stage, s = (x.stats || [])[k] || {}, y1 = s.y1 || {}, b = x.base || {};
    var why = k === 4 ? _T('熱度 ≥ ' + th.hot + '，估值和過去 4 年比已經很高。', 'Heat ≥ ' + th.hot + ': valuations are high against the past 4 years.')
      : k === 0 ? _T('熱度 ≤ ' + th.cold + '，估值和過去 4 年比已經很低。', 'Heat ≤ ' + th.cold + ': valuations are low against the past 4 years.')
      : k === 1 ? _T('熱度在 ' + th.cold + '–' + th.hot + ' 之間、方向空方。', 'Heat between ' + th.cold + ' and ' + th.hot + ' with a bearish trend.')
      : _T('方向多方、熱度' + (k === 2 ? '低於 ' : '在 ') + th.mid + (k === 2 ? '' : '–' + th.hot) + '。', 'Bullish trend with heat ' + (k === 2 ? 'below ' + th.mid : 'between ' + th.mid + ' and ' + th.hot) + '.');
    it.push([_T('現在', 'Now'), dwName(k), why + _T('這個階段已經 ' + x.stage_weeks + ' 週。', ' In this stage for ' + x.stage_weeks + ' weeks.') + (y1.n ? _T(oxYm('2013-01') + ' 以來' + dwName(k) + '共 ' + s.weeks + ' 週，之後一年中位數 ' + fmt.pct(y1.med, 0) + '、' + y1.up + '% 上漲（全部的週：' + fmt.pct(b.med, 0) + '、' + b.up + '%）。',
      ' Since ' + oxYm('2013-01') + ', ' + s.weeks + ' weeks of ' + dwName(k) + ', with a median ' + fmt.pct(y1.med, 0) + ' and ' + y1.up + '% up a year later (all weeks: ' + fmt.pct(b.med, 0) + ', ' + b.up + '%).') : ''), k === 4 ? 'warn' : k === 2 || k === 0 ? 'pos' : 'neu']);
    it.push([_T('熱度', 'Heat'), fmt.n(x.heat, 0) + ' / 100',
      _T('4 週前 ' + fmt.n(x.heat4, 0) + '、13 週前 ' + fmt.n(x.heat13, 0) + '。五項估值各自和過去 4 年比的百分位：', '4 weeks ago ' + fmt.n(x.heat4, 0) + ', 13 weeks ago ' + fmt.n(x.heat13, 0) + '. Each valuation input\'s percentile against the past 4 years: ') +
      x.heat_c.map(function (c) { return _T(DW_HL[c.key][0] + ' 第 ' + (c.pct == null ? '—' : c.pct), DW_HL[c.key][1] + ' ' + (c.pct == null ? '—' : ord(c.pct))); }).join(_T('、', ', ')) + _T('。0 是過去 4 年最便宜、100 是最貴。', '. 0 = cheapest of the past 4 years, 100 = most expensive.'), 'neu']);
    it.push([_T('方向', 'Trend'), x.regime > 0 ? _T('多方', 'Bullish') : _T('空方', 'Bearish'),
      x.trend_c.map(function (c) { return _T(DW_HL[c.key][0] + ' ' + dwTr(c), DW_HL[c.key][1] + ' ' + dwTr(c)); }).join(_T('、', ', ')) + _T('，合起來 ' + (x.trend >= 0 ? '+' : '') + fmt.n(x.trend, 2) + '；' + (x.since ? ymdS(x.since) + ' 翻' + (x.regime > 0 ? '多' : '空') + '，第 ' + (x.weeks + 1) + ' 週' : '') + '（連續 4 週在另一邊才算翻轉）。',
        '; combined ' + (x.trend >= 0 ? '+' : '') + fmt.n(x.trend, 2) + (x.since ? '; turned ' + (x.regime > 0 ? 'bullish' : 'bearish') + ' on ' + ymdS(x.since) + ', week ' + (x.weeks + 1) : '') + ' (a flip needs 4 straight weeks on the other side).'), x.regime > 0 ? 'pos' : 'neu']);
    var tp = (x.marks || []).filter(function (m) { return m.kind === 'top'; }), bt = (x.marks || []).filter(function (m) { return m.kind === 'bottom'; });
    it.push([_T('歷次頂底', 'Past tops and bottoms'), _T('頂 ', 'Tops ') + tp.map(function (m) { return m.heat; }).join('/'),
      _T('頂部前後 4 週內的最高熱度：' + tp.map(function (m) { return m.date.slice(0, 7).replace('-', '/') + ' ' + m.heat; }).join('、') + '；底部前後的最低熱度：' + bt.map(function (m) { return m.date.slice(0, 7).replace('-', '/') + ' ' + m.heat; }).join('、') + '。近兩輪鏈上估值都比價格先見頂，黃昏常提早出現（例如 2024/12、2025/07），價格最高那幾週反而只有 80 上下。',
        'Highest heat within 4 weeks of each top: ' + tp.map(function (m) { return m.date.slice(0, 7).replace('-', '/') + ' ' + m.heat; }).join(', ') + '; lowest around each bottom: ' + bt.map(function (m) { return m.date.slice(0, 7).replace('-', '/') + ' ' + m.heat; }).join(', ') + '. In the last two cycles on-chain valuations peaked before price, so Dusk tends to come early (e.g. 2024/12, 2025/07) and the top weeks themselves sit around 80.'), 'neu']);
    return it;
  }
  function dwTable() {
    var x = D.cycle.dawn, c = function (o) { return o && o.n ? '<span style="color:var(--' + (o.med >= 0 ? 'up' : 'down') + ')">' + fmt.pct(o.med, 0) + '</span> <span class="note">' + o.up + '%</span>' : '—'; };
    return '<div class="tbl-wrap" style="margin-top:12px"><table class="tbl"><thead><tr><th>' + _T('階段', 'Stage') + '</th><th class="num">' + _T('週數', 'Weeks') + '</th><th class="num">' + _T('半年後（中位 · 上漲）', '6 months later (median · up)') + '</th><th class="num">' + _T('一年後（中位 · 上漲）', '1 year later (median · up)') + '</th></tr></thead><tbody>' +
      (x.stats || []).slice().reverse().map(function (s) { return '<tr' + (s.stage === x.stage ? ' style="font-weight:700"' : '') + '><td><i style="display:inline-block;width:10px;height:10px;background:' + dwStgCol(s.stage) + ';margin-right:6px;border-radius:2px"></i>' + dwName(s.stage, true) + '</td><td class="num">' + s.weeks + '</td><td class="num">' + c(s.m6) + '</td><td class="num">' + c(s.y1) + '</td></tr>'; }).join('') +
      '<tr><td>' + _T('全部的週', 'All weeks') + '</td><td class="num">' + ((x.base || {}).n || '—') + '</td><td class="num">—</td><td class="num">' + c(x.base) + '</td></tr></tbody></table></div>';
  }
  function dwPanel() {
    var x = (D.cycle || {}).dawn; if (!x || !x.rows) return '';
    return panel('span-12', _T('晨昏指數', 'Dawn–Dusk Index'), _T('週期熱度 0–100 · 五項估值＋四項趨勢 · 2013 起 · 每週 · ' + fmt.md(x.date), 'Cycle heat 0–100 · five valuation + four trend inputs · since 2013 · weekly · ' + fmt.md(x.date)),
      '<div class="cf-hero">' + oxCard(dwCol(x.heat), _T('週期熱度', 'Cycle heat'), fmt.n(x.heat, 0), _T('0 冷 · 100 熱；4 週前 ' + fmt.n(x.heat4, 0), '0 cold · 100 hot; ' + fmt.n(x.heat4, 0) + ' 4 weeks ago'), oxArrow(x.heat, x.heat4, _T(' 點', ' pts'), 0)) +
      oxCard(dwStgCol(x.stage), _T('階段', 'Stage'), dwName(x.stage), _T((DW_STG[x.stage] || [])[2] + '；方向' + (x.regime > 0 ? '多方' : '空方'), (DW_STG[x.stage] || [])[3] + '; trend ' + (x.regime > 0 ? 'bullish' : 'bearish'))) + '</div>' +
      interpHtml(dwSay()) + '<div class="legend" style="margin-top:10px"><span><b style="color:var(--ink-2);font-weight:400">' + _T('冷（底）', 'Cold (bottom)') + '</b><i class="liq-bar" style="background:' + dwLegend() + '"></i><b style="color:var(--ink-2);font-weight:400">' + _T('熱（頂）', 'Hot (top)') + '</b></span><span><b style="color:var(--ink-2);font-weight:400">' + _T('熱度高於 50 往上長、低於 50 往下長；網點越密越靠中線', 'heat above 50 grows up, below 50 grows down; dots get denser toward the midline') + '</b></span></div><div class="chart" id="c-dawn"></div>' + dwTable() +
      '<p class="note">' + _T('把一輪週期當成一天：深夜（底部區）→ 破曉（初升）→ 白晝（上升）→ 黃昏（過熱）→ 入夜（下跌）。熱度＝長期持有者 NUPL、未實現獲利 ÷ 市值、冪律殘差、儲備風險、MVRV-Z 五項，各自和過去 4 年比的百分位平均；方向＝價格 ÷ 200 日均線、價格 ÷ 短期持有者成本、aSOPR 30 日、實現獲利 ÷ 虧損 90 日四項，連續 4 週在另一邊才翻。階段：熱度 ≥ ' + x.th.hot + ' 黃昏、≤ ' + x.th.cold + ' 深夜；其餘空方是入夜，多方熱度 < ' + x.th.mid + ' 破曉、其餘白晝。每一週都只用當時已有的資料算（不偷看未來）。研究時和事後週期位置的等級相關 0.82（週線多空分數 0.49）。資料 Bitview、CoinMetrics、CheckOnChain。只有三輪多完整週期，表裡是歷史描述，不是買賣訊號。',
        'A cycle seen as a day: Deep night (bottom zone) → Daybreak (early rise) → Daylight (rising) → Dusk (overheated) → Nightfall (falling). Heat = the average percentile, against the past 4 years, of LTH NUPL, unrealized profit ÷ market cap, the power-law residual, reserve risk and MVRV-Z; trend = price ÷ 200-day MA, price ÷ STH cost basis, 30-day aSOPR and the 90-day realized profit ÷ loss, flipping after 4 straight weeks. Stages: heat ≥ ' + x.th.hot + ' Dusk, ≤ ' + x.th.cold + ' Deep night; otherwise bearish = Nightfall, bullish with heat < ' + x.th.mid + ' = Daybreak, else Daylight. Every week uses only data available then (no look-ahead). In research its rank correlation with the hindsight cycle position was 0.82 (weekly regime score: 0.49). Data: Bitview, CoinMetrics, CheckOnChain. Only three-plus full cycles; the table describes history and is not a trading signal.') + '</p>', '', 'dawn');
  }
  /* 晨昏指數的畫法（2026-11-08 使用者從 Pinterest 挑的「Daily activity timeline」網點圖，最後選「上下模式」；前兩版：紅藍面積、五組配色、五種海報都沒選）：
     ・熱度以 50 為中線：熱往上長成暖色的山、冷往下長成冷色的谷
     ・錯位網點：越靠中線越大（最深處重疊成色塊），越往外越小，輪廓外散開幾顆小點
     ・色票從參考圖的點心取色（深青 → 青 → 黃綠 → 芥末黃 → 琥珀 → 珊瑚 → 洋紅 → 紫）；形狀看 σ≈5 週平滑的熱度、顏色看 σ≈11 週（色區大片、慢慢過渡）
     ・圖自帶淺灰藍底（夜刊深藍黑）；頂從上方標籤往下指、底從下方往上指。樣稿與研究：本機 .claude/research/dawn/ */
  /* 2026-11-09 使用者：「晨昏指數顏色也統一一下」→ 改用全站的週期階段五色（--stg0 深藍 → --stg1 淺藍 → --stg2 綠 → --stg3 琥珀 → --stg4 品牌橘紅），
     和週線多空分數同一套：熱度 0–100 照 DW_POS 的位置在五色之間漸變；五個階段各取一色（深夜 stg0、入夜 stg1、破曉 stg2、白晝 stg3、黃昏 stg4）。
     原本的參考圖色票（深青→黃綠→琥珀→珊瑚→洋紅紫）不再使用 */
  var DW_POS = [0, 20, 45, 70, 90], DW_C = {};
  function dwHex(h) { h = String(h).trim(); var m = /^rgba?\((\d+),\s*(\d+),\s*(\d+)/.exec(h); return m ? [+m[1], +m[2], +m[3]] : [1, 3, 5].map(function (i) { return parseInt(h.substr(i, 2), 16); }); }
  function dwDark() { return document.documentElement.getAttribute('data-theme') === 'dark'; }
  function dwStops() {   // 從 CSS 讀當下主題的階段色（一個主題只讀一次）
    var k = dwDark() ? 'd' : 'l'; if (DW_C[k]) return DW_C[k];
    var cs = getComputedStyle(document.documentElement), c = DW_POS.map(function (_, i) { return cs.getPropertyValue('--stg' + i).trim(); });
    if (c.some(function (x) { return !x; })) return [[0, '#3C5CDD'], [100, '#CC2827']];
    return (DW_C[k] = DW_POS.map(function (p, i) { return [p, c[i]]; }).concat([[100, c[4]]]));
  }
  function dwCol(v) {
    var S = dwStops(); v = Math.max(0, Math.min(100, v));
    for (var i = 0; i < S.length - 1; i++) if (v <= S[i + 1][0]) {
      var A = dwHex(S[i][1]), B = dwHex(S[i + 1][1]), f = (v - S[i][0]) / (S[i + 1][0] - S[i][0] || 1);
      return 'rgb(' + A.map(function (q, j) { return Math.round(q + (B[j] - q) * f); }).join(',') + ')';
    }
    return S[S.length - 1][1];
  }
  function dwLegend() { return 'linear-gradient(90deg,' + dwStops().map(function (q) { return q[1] + ' ' + q[0] + '%'; }).join(',') + ')'; }
  function dwStgCol(k) { return 'var(--stg' + (k >= 0 && k <= 4 ? k : 2) + ')'; }
  function dwGs(v, sg) { var K = Math.ceil(sg * 3); return v.map(function (_, i) { var a = 0, w = 0; for (var k = -K; k <= K; k++) { var j = i + k; if (j < 0 || j >= v.length) continue; var q = Math.exp(-k * k / (2 * sg * sg)); a += v[j] * q; w += q; } return a / w; }); }
  /* 2026-11-08 使用者：「這個圖要配合 K 線一起」「圖底色需要與網站一致，不需要額外底色」→ 上格月 K（Bitview 每日開高低收合成），下格網點熱度，共用時間軸；不畫自己的底色。
     K 線顏色＝當月熱度色（和網點同一組色票：週期階段五色，頂部品牌橘紅、底部深藍）；漲的月空心、跌的月實心（單色 K 線慣例）。頂部標籤拉細線指到那一輪最高的那根 K 線 */
  function drawDawn(el) {
    var x = (D.cycle || {}).dawn; if (!x || !el) return;
    var R_ = x.rows, n = R_.length, t0 = R_[0][0], t1 = R_[n - 1][0], hv = R_.map(function (r) { return r[1]; }), hS = dwGs(hv, 5), hC = dwGs(hv, 11);
    var W = Math.max(300, el.clientWidth), sm = W < 520, L = sm ? 4 : 8, MR = sm ? 34 : 46, pw = W - L - MR;
    var CK = x.candles || [], hasK = CK.length > 12;
    var topY = 14, pT = 30, pH = hasK ? (sm ? 120 : 196) : 0, amp = sm ? 92 : 132, mid = (hasK ? pT + pH + (sm ? 16 : 22) : 26) + amp;
    var botY = mid + amp + (sm ? 26 : 30), yrY = botY + (sm ? 22 : 26), H = yrY + 8;
    var step = Math.max(4, Math.min(6.4, W / 120)), vs = step * 0.88, rMax = step * 0.62, band = 3.5;
    var X = function (d) { return L + (d - t0) / (t1 - t0) * pw; }, Dx = function (xv) { return t0 + (xv - L) / pw * (t1 - t0); };
    var at = function (arr, d) { var f = Math.max(0, Math.min(n - 1, (d - t0) / 7)), i = Math.min(n - 2, Math.floor(f)); return arr[i] + (arr[i + 1] - arr[i]) * (f - i); };
    var A = function (d) { return (at(hS, d) - 50) / 50 * amp; };   // 正＝往上（熱）、負＝往下（冷）
    var seed = 11, rnd = function () { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    var s = '', k, xv, i;
    // ── 上格：月 K（手機上每 2 個月併一根，不然太細）
    var Yp = null, KK = [];
    if (hasK) {
      var g = sm ? 2 : 1;
      for (i = 0; i < CK.length; i += g) { var grp = CK.slice(i, i + g); KK.push([grp[0][0], grp[0][1], Math.max.apply(null, grp.map(function (q) { return q[2]; })), Math.min.apply(null, grp.map(function (q) { return q[3]; })), grp[grp.length - 1][4], (grp[grp.length - 1][0] + 30 * g) ]); }
      var lo = Math.log(Math.min.apply(null, KK.map(function (q) { return q[3]; }))), hi = Math.log(Math.max.apply(null, KK.map(function (q) { return q[2]; }))), pd = (hi - lo) * 0.04;
      Yp = function (v) { return pT + (1 - (Math.log(v) - lo + pd) / (hi - lo + 2 * pd)) * pH; };
      [1, 10, 100, 1e3, 1e4, 1e5].forEach(function (t) { var y = Yp(t); if (y < pT - 1 || y > pT + pH + 1) return; s += '<line x1="' + L + '" x2="' + (L + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '" stroke="var(--line)" stroke-width=".6" stroke-dasharray="1 3"/>' + axText(L + pw + 6, y + 3.5, t >= 1000 ? fmt.k(t) : '$' + t); });
      var bwK = Math.max(1, (pw / KK.length) * 0.62);
      KK.forEach(function (q) {
        var d0 = q[0], d1 = Math.min(q[5], t1), cx = (X(d0) + X(d1)) / 2, c = dwCol(at(hC, Math.min(t1, Math.max(t0, (d0 + d1) / 2)))), up = q[4] >= q[1];
        var yo = Yp(q[1]), yc = Yp(q[4]), yt = Math.min(yo, yc), bh = Math.max(0.8, Math.abs(yc - yo));
        s += '<line x1="' + cx.toFixed(1) + '" x2="' + cx.toFixed(1) + '" y1="' + Yp(q[2]).toFixed(1) + '" y2="' + Yp(q[3]).toFixed(1) + '" stroke="' + c + '" stroke-width="1"/>' +
          '<rect x="' + (cx - bwK / 2).toFixed(1) + '" y="' + yt.toFixed(1) + '" width="' + bwK.toFixed(1) + '" height="' + bh.toFixed(1) + '"' + (up && bwK > 2.2 ? ' fill="var(--deck)" stroke="' + c + '" stroke-width="1"' : ' fill="' + c + '"') + '/>';
      });
    }
    // ── 下格：網點熱度
    var kmax = Math.ceil((amp + 12) / vs);
    for (k = 0; k <= kmax; k++) [1, -1].forEach(function (dir) {
      if (k === 0 && dir < 0) return;
      var y = mid - dir * k * vs, dist = k * vs;
      for (xv = L + ((k % 2) ? step / 2 : 0); xv <= L + pw + 0.1; xv += step) {
        var d = Dx(xv), ext = Math.max(band, A(d) * dir), r;
        if (dist <= ext) r = rMax * Math.max(0.12, Math.pow(Math.min(1, (1 - dist / (ext + 2)) * 1.22), 0.8));
        else { if (dist > ext + 10 || rnd() > 0.3 - (dist - ext) * 0.025) continue; r = 0.55; }
        s += '<circle cx="' + xv.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="' + r.toFixed(2) + '" fill="' + dwCol(at(hC, d)) + '"/>';
      }
    });
    if (hasK) s += axText(L, mid - amp - 6, _T('週期熱度：往上熱、往下冷', 'Cycle heat: up hot, down cold'));
    [[100, mid - amp], [50, mid], [0, mid + amp]].forEach(function (q) { s += axText(L + pw + 6, q[1] + 3.5, String(q[0])); });
    // ── 頂：最上面的標籤拉細線到那一輪最高的 K 線（沒有 K 線時指到熱度山頂）；底：下方標籤往上指到谷底
    (x.marks || []).forEach(function (m) {
      var d = dnOf(m.date); if (d < t0 || d > t1) return;
      var tp = m.kind === 'top', a = A(d), lab = m.date.slice(0, 4) + (tp ? _T(' 頂', ' top') : _T(' 底', ' bottom')), cx = X(d), yEnd;
      if (tp && hasK) { var best = KK.filter(function (q) { return Math.abs(q[0] - d) < 120; }).sort(function (p_, q) { return q[2] - p_[2]; })[0]; if (best) { cx = (X(best[0]) + X(Math.min(best[5], t1))) / 2; yEnd = Yp(best[2]) - 4; } }
      if (yEnd == null) yEnd = tp ? mid - Math.max(band, a) - 9 : 0;
      var an = cx > W - MR - 26 ? 'end' : cx < 30 ? 'start' : 'middle';
      if (tp) s += '<line x1="' + cx.toFixed(1) + '" x2="' + cx.toFixed(1) + '" y1="' + (topY + 5) + '" y2="' + Math.max(topY + 6, yEnd).toFixed(1) + '" stroke="var(--ink)" stroke-opacity=".7" stroke-width="1"/>' + axText(cx, topY, lab, an, 'ax dw-lab');
      else s += '<line x1="' + cx.toFixed(1) + '" x2="' + cx.toFixed(1) + '" y1="' + (mid + Math.max(band, -a) + 9).toFixed(1) + '" y2="' + (botY - 12) + '" stroke="var(--ink)" stroke-opacity=".7" stroke-width="1"/>' + axText(cx, botY, lab, an, 'ax dw-lab');
    });
    for (var yy = new Date(t0 * 864e5).getUTCFullYear() + 1; yy <= new Date(t1 * 864e5).getUTCFullYear(); yy++) { if (yy % (sm ? 4 : 2)) continue; var yx = X(Date.UTC(yy, 0, 1) / 864e5); if (yx > L + 12 && yx < L + pw - 12) s += axText(yx, yrY, String(yy), 'middle'); }
    var na = A(t1), ny = mid - (na >= 0 ? Math.max(band, na) + 8 : -(Math.max(band, -na) + 8));
    s += '<circle cx="' + (X(t1) - 1).toFixed(1) + '" cy="' + ny.toFixed(1) + '" r="3.2" fill="var(--ink)"/>';
    s += '<line class="xh" x1="0" x2="0" y1="' + (hasK ? pT : topY + 6) + '" y2="' + (botY - 12) + '" visibility="hidden"/><rect class="hit" x="' + L + '" y="0" width="' + pw + '" height="' + H + '"/>';
    el.innerHTML = svgEl(W, H, s, _T('晨昏指數：上格 BTC 月 K，下格每週的週期熱度（熱往上、冷往下）', 'Dawn–Dusk Index: BTC monthly candles on top, weekly cycle heat below (hot up, cold down)'));
    var svg = el.querySelector('svg'), xh = svg.querySelector('.xh'), hit = svg.querySelector('.hit');
    function move(ev) {
      var r = svg.getBoundingClientRect(), mx = (ev.clientX - r.left) * W / r.width, i_ = Math.max(0, Math.min(n - 1, Math.round((Dx(mx) - t0) / 7))), p = R_[i_], cx = X(p[0]);
      var kq = KK.filter(function (q) { return q[0] <= p[0] && p[0] < q[5]; })[0];
      xh.setAttribute('x1', cx); xh.setAttribute('x2', cx); xh.setAttribute('visibility', 'visible');
      showTip(ev.clientX, ev.clientY, '<div class="t">' + _T('週至 ', 'Week to ') + fmt.date(p[0]) + '</div>' + tipRow1(dwCol(p[1]), _T('熱度（' + dwName(p[3]) + '）', 'Heat (' + dwName(p[3]) + ')'), fmt.n(p[1], 0)) +
        tipRow1('var(--ink-3)', _T('方向', 'Trend'), p[4] < 0 ? _T('空方', 'Bearish') : _T('多方', 'Bullish')) + tipRow1('var(--ink-2)', _T('BTC 週收盤', 'BTC weekly close'), fmt.usd(p[2])) +
        (kq ? tipRow1('var(--ink-3)', _T('當月 高／低', 'Month high / low'), fmt.usd(kq[2]) + ' / ' + fmt.usd(kq[3])) : ''));
    }
    hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', function () { xh.setAttribute('visibility', 'hidden'); hideTip(); });
  }
  function boardHtml() {
    var cm = D.cycle.cm || {}, p6 = D.cycle.p6 || {}, tm = D.cycle.tidemark || {}, pl = D.cycle.powerlaw || {}, st = D.cycle.stage || {}, rg = D.cycle.regime || {}, dw = D.cycle.dawn || {}, ex = D.exit.status || {}, c = D.price.bar.c, tr = D.onchain.top_radar || {};
    var sg = function (v) { return (v > 0 ? '+' : v < 0 ? '−' : '') + fmt.n(Math.abs(v), 2); };
    var gauge = function (p, lab) { if (p == null || !isFinite(p)) return '<span class="gauge none"></span>'; var w = Math.max(0, Math.min(100, p)); return '<span class="gauge' + (p >= 100 ? ' hit' : p >= 85 ? ' near' : '') + '"><i style="width:' + w.toFixed(1) + '%"></i><b>' + (lab || fmt.n(p, 0) + '%') + '</b></span>'; };
    var row = function (o) { return '<div class="bd-r"><span class="k">' + o.k + (o.sub ? '<small>' + o.sub + '</small>' : '') + '</span><span class="v num">' + o.v + '</span>' + (o.viz || gauge(o.p, o.pl)) + tnHtml(o.r ? o.r[1] : 'neu') + jumpA(o.to[0], o.to[1], '→') + (o.r && o.r[0] ? '<p class="d">' + esc(o.r[0]) + '</p>' : '') + '</div>'; };
    var grp = function (h, note, rows) { rows = rows.filter(Boolean); return rows.length ? '<div class="bd-g"><h3>' + h + (note ? '<small>' + note + '</small>' : '') + '</h3>' + rows.map(row).join('') + '</div>' : ''; };
    // 方向
    var S3 = Object.keys(STAGE), si = S3.indexOf(st.stage), ev = st.evidence || {};
    var stageViz = '<span class="steps">' + S3.map(function (s, i) { return '<i class="' + (i === si ? 'on ' + (STAGE[s] || [])[1] : i < si ? 'past' : '') + '">' + (STAGE[s] || [s])[0] + '</i>'; }).join('') + '</span>';
    var stageR = si < 0 ? null : [_T((STAGE[st.stage] || [''])[0] + '（' + fmt.md(st.since) + ' 起）' + (ev.n ? '；佐證燈 ' + ev.ok + ' / ' + ev.n + ' 亮（只顯示、不參與判定）' : '') + '。', (STAGE[st.stage] || [''])[0] + ' since ' + fmt.md(st.since) + (ev.n ? '; ' + ev.ok + ' of ' + ev.n + ' supporting lights on (shown only, not used in the call)' : '') + '.'), si === 2 ? 'pos' : si === 0 ? 'neg' : 'neu'];
    var rv = rg.value, rgViz = rv == null ? null : '<span class="dvg"><i style="' + (rv >= 0 ? 'left:50%;width:' : 'right:50%;width:') + Math.min(50, Math.abs(rv) / 6 * 50).toFixed(1) + '%" class="' + (rv >= 0 ? 'up' : 'down') + '"></i><b>−6 · 0 · +6</b></span>';
    var rgR = rv == null ? null : [_T((rg.regime > 0 ? '多方' : '空方') + (rg.since ? '第 ' + ((rg.weeks || 0) + 1) + ' 週' : '') + '；一週前 ' + sg(rg.prev) + '。絕對值小於 1 屬於弱勢，方向容易反覆。', (rg.regime > 0 ? 'Bullish' : 'Bearish') + (rg.since ? ', week ' + ((rg.weeks || 0) + 1) : '') + '; ' + sg(rg.prev) + ' a week ago. Below 1 in size is weak and prone to flip.'), rv >= 1 ? 'pos' : rv <= -1 ? 'neg' : 'neu'];
    var fs = (N && N.findings) || [], cnt = { bull: 0, bear: 0, neutral: 0 }; fs.forEach(function (f) { if (cnt[f.lean] != null) cnt[f.lean]++; });
    var dirRows = [
      si < 0 ? null : { k: _T('市場階段', 'Market stage'), sub: 'P23', v: (STAGE[st.stage] || ['—'])[0], viz: stageViz, r: stageR, to: ['cycle', ''] },
      rv == null ? null : { k: _T('週線多空分數', 'Weekly regime score'), sub: _T('六項合成', 'six inputs'), v: sg(rv), viz: rgViz, r: rgR, to: ['cycle', 'regime'] },
      dw.heat == null ? null : { k: _T('晨昏指數', 'Dawn–Dusk Index'), sub: _T('週期熱度', 'cycle heat'), v: fmt.n(dw.heat, 0) + ' · ' + dwName(dw.stage), p: dw.heat, pl: fmt.n(dw.heat, 0) + ' / 100', r: [_T(dwName(dw.stage, true) + '；4 週前 ' + fmt.n(dw.heat4, 0) + '、方向' + (dw.regime > 0 ? '多方' : '空方') + '。0 是過去 4 年估值最低、100 最高。', dwName(dw.stage, true) + '; ' + fmt.n(dw.heat4, 0) + ' 4 weeks ago, trend ' + (dw.regime > 0 ? 'bullish' : 'bearish') + '. 0 = cheapest valuations of the past 4 years, 100 = richest.'), dw.stage === 4 ? 'warn' : dw.stage === 2 || dw.stage === 0 ? 'pos' : 'neu'], to: ['cycle', 'dawn'] },
      fs.length ? { k: _T('今日發現', "Today's findings"), sub: _T('每日判讀', 'daily read'), v: _T('多 ' + cnt.bull + ' · 空 ' + cnt.bear, cnt.bull + ' bull · ' + cnt.bear + ' bear'), viz: '<span class="gauge none"></span>', r: [_T('今天 ' + fs.length + ' 則發現：偏多 ' + cnt.bull + '、偏空 ' + cnt.bear + '、中性 ' + cnt.neutral + '。描述一般含意，不是預測。', fs.length + ' findings today: ' + cnt.bull + ' bullish, ' + cnt.bear + ' bearish, ' + cnt.neutral + ' neutral. What they usually mean, not a forecast.'), cnt.bull > cnt.bear ? 'pos' : cnt.bear > cnt.bull ? 'neg' : 'neu'], to: ['overview', 'findings'] } : null
    ];
    // 離頂部多近
    var p6v = ['mvrv_z', 'nupl', 'puell'].map(function (k) { return p6[k]; }).filter(function (v) { return v != null; }).sort(function (a, b) { return b - a; });
    var rk = Object.keys(tr).filter(function (k) { return tr[k] && tr[k].pct_since_2022_11 != null && RADAR_READ[k]; }).sort(function (a, b) { return tr[b].pct_since_2022_11 - tr[a].pct_since_2022_11; })[0];
    var RN = { 'lth-mvrv-zscore': 'LTH MVRV Z', 'supply-in-profit-pct': _T('獲利供給 %', 'Supply in profit'), 'lth-net-position-change-30d-btc': _T('LTH 30 日淨部位', 'LTH 30d net position') };
    var topRows = [
      cm.mvrv_vs_prior == null ? null : { k: _T('MVRV ÷ 前一輪高點', 'MVRV ÷ prior peak'), sub: _T('第一個鏈上賣點 0.75', 'first on-chain sell 0.75'), v: fmt.n(cm.mvrv_vs_prior, 3), p: cm.mvrv_vs_prior / 0.75 * 100, r: p20Read(), to: ['cycle', 'p20'] },
      p6v.length < 2 ? null : { k: _T('頂部三指標', 'Top-3 indicators'), sub: _T('第二高的到 80 進頂部區', '2nd-highest to 80 = top zone'), v: ['mvrv_z', 'nupl', 'puell'].map(function (k) { return fmt.n(p6[k], 0); }).join(' / '), p: p6v[1] / 80 * 100, r: p6Read(), to: ['cycle', 'p6'] },
      (tm.top || {}).signal == null ? null : { k: _T('Tidemark 頂部訊號', 'Tidemark top signal'), sub: _T('第三方 · 50 進窗口', 'third-party · 50 = window'), v: fmt.n(tm.top.signal, 0) + ' / ' + fmt.n((tm.bottom || {}).signal, 0), p: tm.top.signal / 50 * 100, r: tmRead(), to: ['cycle', 'tm'] },
      !rk ? null : { k: _T('頂部雷達', 'Top radar'), sub: _T('三項中最高：', 'highest of 3: ') + RN[rk], v: fmt.n(tr[rk].pct_since_2022_11, 0), p: tr[rk].pct_since_2022_11, pl: _T('本輪第 ' + fmt.n(tr[rk].pct_since_2022_11, 0) + ' 百分位', fmt.n(tr[rk].pct_since_2022_11, 0) + 'th pct this cycle'), r: RADAR_READ[rk](tr[rk]), to: ['cycle', 'radar'] },
      pl.ratio == null ? null : { k: _T('冪律倍數', 'Power-law multiple'), sub: _T('價格 ÷ 合理價', 'price ÷ fair value'), v: fmt.n(pl.ratio, 2) + '×', viz: '<span class="gauge none"></span>', r: plRead(), to: ['cycle', 'pl'] }
    ];
    // 離出場多遠
    var exRows = [
      { k: _T('價格階梯第一階', 'Price ladder, next step'), sub: ex.next_step ? fmt.usd(ex.next_step) : '', v: ex.next_step ? fmt.pct(ex.next_step_dist_pct, 0) : '—', p: ex.next_step ? c / ex.next_step * 100 : 100, r: ladderRead(), to: ['exit', 'sim'] },
      ex.sma200 ? { k: _T('200 日均線避險', '200-day MA hedge'), sub: fmt.usd(ex.sma200), v: fmt.pct((c / ex.sma200 - 1) * 100, 1), p: c > ex.sma200 ? ex.sma200 / c * 100 : 100, pl: c > ex.sma200 ? fmt.n(ex.sma200 / c * 100, 0) + '%' : _T('跌破 ' + (ex.below_sma200_run || 0) + ' / 5 天', 'below ' + (ex.below_sma200_run || 0) + ' / 5 days'), r: hedgeRead(), to: ['exit', ''] } : null
    ];
    var body = grp(_T('方向：現在偏多還是偏空', 'Direction: bullish or bearish now'), '', dirRows) +
      grp(_T('離頂部多近', 'How close to a top'), _T('條＝離觸發多近，100% ＝碰到觸發線（頂部雷達是本輪極值）', 'bar = how close to its trigger; 100% = at the trigger (top radar: this cycle\'s extreme)'), topRows) +
      grp(_T('離出場多遠', 'How far from the exit rules'), _T('100% ＝規則觸發', '100% = rule fires'), exRows);
    return body ? '<div class="board">' + body + '</div>' : '';
  }

  /* 頂部三指標的原始讀值（2026-11-04：鏈上版的指標表不再重複這三列，原始值改附在週期版這裡） */
  function p6Raw() {
    var m = D.onchain.metrics || {}, it = [['MVRV Z', 'mvrv-zscore', 3], ['NUPL', 'nupl', 3], ['Puell', 'puell-multiple', 3]].filter(function (r) { return m[r[1]] && m[r[1]].value != null; });
    return it.length ? '<p class="note">' + _T('原始讀值：', 'Raw values: ') + it.map(function (r) { return r[0] + ' ' + fmt.n(m[r[1]].value, r[2]); }).join(' · ') + ' · ' + fmt.md(m[it[0][1]].date) + '</p>' : '';
  }
  /* 週期與出場（頭版、週期版、出場框架版共用） */
  function p20Read() { var cm = D.cycle.cm, r = cm.mvrv_vs_prior, c = D.price.bar.c, k = cm.k075_price;
    if (r == null) return null;
    return [r >= 0.75 ? _t('已站上 0.75 賣出線，連 5 天即觸發第一個鏈上賣點（現在 ') + (cm.p20_run_ge075 || 0) + _t('/5 天）。') : _t('離 0.75 賣出線還很遠：價格約要到 ') + fmt.usd(k) + _t('（比收盤高 ') + fmt.pct((k / c - 1) * 100, 0) + _t('）才會碰到；2025 頂部時是 0.78。'), r >= 0.75 ? 'neg' : r >= 0.7 ? 'warn' : 'neu']; }
  // 2026-11-04：倍數旁加白話「低於趨勢 X%」（一般讀者比較好懂）
  // 2026-11-04 使用者要求（已實現波動率年低）：RV30 在近一年裡的百分位；第 10 百分位以下註明「低波動後常有大波動，方向不一定」
  function rvYear(v) {
    if (v.rv30_pct1y == null) return '';
    var lo = v.rv30_pct1y <= 10, md = fmt.md(v.rv30_min1y_date);
    return _T('；近一年第 ' + fmt.n(v.rv30_pct1y, 0) + ' 百分位（一年最低 ' + fmt.n(v.rv30_min1y, 1) + '%，' + md + '）' + (lo ? '，接近一年低點：低波動之後常接著大波動，但方向不一定' : ''),
      '; ' + fmt.n(v.rv30_pct1y, 0) + 'th percentile of the past year (low ' + fmt.n(v.rv30_min1y, 1) + '% on ' + md + ')' + (lo ? ', near a one-year low: quiet spells are often followed by big moves, in either direction' : ''));
  }
  function plGap(r) { var g = fmt.n(Math.abs(1 - r) * 100, 0); return r < 1 ? _T('低於趨勢 ' + g + '%', g + '% below trend') : _T('高於趨勢 ' + g + '%', g + '% above trend'); }
  /* 2026-11-05 冪律通道位置（對照「冪律衰減通道震盪」）：倍數取對數後，0%＝歷次底部的連線、100%＝歷次頂部的連線（頂部一輪比一輪低，所以上緣逐輪下降）；
     兩條線各用 4 個頂／底在 log(倍數)–log(天數) 上直線擬合，超出 0–100% 的截在邊上。頂底含之後才知道的點，歷史段是事後畫的；只作讀值 */
  var PL_STG = [[15, '底部區', 'Bottom zone'], [35, '偏低', 'Low'], [55, '中段', 'Middle'], [75, '偏高', 'High'], [1e9, '頂部區', 'Top zone']];
  function plStage(v) { for (var i = 0; i < PL_STG.length; i++) if (v < PL_STG[i][0]) return i; return 4; }
  function plChan() {
    var pl = D.cycle.powerlaw || {}, T = pl.tops || [], B = pl.bottoms || [], g = dnOf('2009-01-03');
    if (T.length < 2 || B.length < 2 || !(pl.rows || []).length) return null;
    var fit = function (P) {
      var xs = P.map(function (q) { return Math.log10(dnOf(q[0]) - g); }), ys = P.map(function (q) { return Math.log10(q[1]); }), n = xs.length;
      var mx = xs.reduce(function (a, b) { return a + b; }, 0) / n, my = ys.reduce(function (a, b) { return a + b; }, 0) / n, sxy = 0, sxx = 0;
      xs.forEach(function (x, i) { sxy += (x - mx) * (ys[i] - my); sxx += (x - mx) * (x - mx); });
      var b = sxy / sxx; return [my - b * mx, b];
    };
    var U = fit(T), L = fit(B), pos = function (t, lr) { var x = Math.log10(t - g), up = U[0] + U[1] * x, lo = L[0] + L[1] * x; return (lr - lo) / (up - lo) * 100; };
    var rows = pl.rows.map(function (r) { return [r[0], Math.max(0, Math.min(100, pos(r[0], r[1])))]; });
    var at = function (P) { return P.map(function (q) { return Math.round(pos(dnOf(q[0]), Math.log10(q[1]))); }); };
    return { rows: rows, now: rows[rows.length - 1][1], tops: at(T), bottoms: at(B) };
  }
  function plChanSay() {
    var c = plChan(); if (!c) return '';
    var k = plStage(c.now), tp = c.tops.map(function (v) { return Math.min(100, v); }), bt = c.bottoms.map(function (v) { return Math.max(0, v); });
    return _T('通道位置 ' + fmt.n(c.now, 0) + '%（' + PL_STG[k][1] + '）：0%＝歷次底部的連線、100%＝逐輪下降的頂部連線；歷次頂部在 ' + Math.min.apply(null, tp) + '–' + Math.max.apply(null, tp) + '%，底部在 ' + Math.min.apply(null, bt) + '–' + Math.max.apply(null, bt) + '%。',
      'Channel position ' + fmt.n(c.now, 0) + '% (' + PL_STG[k][2] + '): 0% is the line through past bottoms, 100% the falling line through past tops; past tops sat at ' + Math.min.apply(null, tp) + '–' + Math.max.apply(null, tp) + '%, bottoms at ' + Math.min.apply(null, bt) + '–' + Math.max.apply(null, bt) + '%. ');
  }
  function plLegend(m) {
    return m === 'chan' ? legend(stgItems(PL_STG.map(function (x) { return [x[1], x[2]]; })))
      : legend([[_T('價格 ÷ 合理價', 'Price ÷ fair value'), 'var(--s2)'], [_T('歷次頂部', 'Past tops'), 'var(--flare)', 'dot'], [_T('歷次底部', 'Past bottoms'), 'var(--orbit)', 'dot'], [_T('歷史底部帶', 'Historical bottom band'), 'var(--orbit-dim)', 'box']]);
  }
  function plRead() { var pl = D.cycle.powerlaw || {}, r = pl.ratio, bb = pl.bottom_band || [0.24, 0.48];
    if (r == null) return null;
    return [_T('價格是冪律合理價（' + fmt.usd(pl.fair) + '）的 ' + fmt.n(r * 100, 0) + '%，' + plGap(r) + '：', 'Price is ' + fmt.n(r * 100, 0) + '% of the power-law fair value (' + fmt.usd(pl.fair) + '), ' + plGap(r) + ': ') + (r <= bb[1] ? _t('落在歷史底部帶（') + bb[0] + '–' + bb[1] + _t(' 倍），長期看很便宜。') : r < 1 ? _t('低於合理價、高於歷史底部帶（') + bb[1] + _t(' 倍），長期看偏便宜。') : r < 1.12 ? _t('高於合理價，但還低於 2025 頂部的 1.12 倍。') : _t('已超過 2025 頂部的 1.12 倍，偏貴。')), r <= bb[1] ? 'pos' : r < 1 ? 'neu' : r < 1.12 ? 'warn' : 'neg']; }
  function tmRead() { var tm = D.cycle.tidemark || {}, t = (tm.top || {}).signal, b = (tm.bottom || {}).signal, ct = tm.cycle_test || {};
    if (t == null && b == null) return null;
    return [_t('頂部訊號 ') + fmt.n(t, 0) + _t('（') + (t >= 70 ? _t('高度警戒') : t >= 50 ? _t('進入頂部窗口') : _t('低於 50，沒有頂部跡象')) + _t('）、底部訊號 ') + fmt.n(b, 0) + _t('（') + (b >= 70 ? _t('強烈底部') : b >= 50 ? _t('進入底部區') : _t('低於 50，不在底部區')) + _t('）') + (t < 50 && b < 50 ? _t('：模型認為現在既不是頂也不是底，在週期中段。') : _t('。')) + (ct.status === 'testing' && ct.decisive_date ? _t('本輪低點假說驗證到 ') + ct.decisive_date + _t('。') : ''), t >= 50 ? 'neg' : b >= 50 ? 'pos' : 'neu']; }
  function p6Read() { var p6 = D.cycle.p6 || {}, nm = { mvrv_z: 'MVRV Z', nupl: 'NUPL', puell: 'Puell' }, hit = Object.keys(nm).filter(function (k) { return p6[k] >= 80; });
    if (p6.mvrv_z == null) return null;
    return [hit.length + _t(' 項到 80') + (hit.length ? _t('（') + hit.map(function (k) { return nm[k]; }).join(_t('、')) + _t('）') : '') + _t('；') + (hit.length >= 2 ? _t('已進入頂部區（只作讀值，不連動賣出）。') : _t('任兩項到 80 才進入頂部區，現在還差') + (hit.length ? _t('一') : _t('兩')) + _t('項。')), hit.length >= 2 ? 'neg' : hit.length ? 'warn' : 'neu']; }
  function ladderRead() { var ex = D.exit.status, n = (ex.steps_hit || []).length;
    if (!ex.next_step) return [_t('價格階梯 8 階都已觸發。'), 'neg'];
    return [_t('收盤要再漲 ') + fmt.n(ex.next_step_dist_pct, 0) + _t('% 到 ') + fmt.usd(ex.next_step) + _t(' 才賣') + (n ? _t('第 ') + (n + 1) + _t(' 階') : _t('第一階')) + _t('（每階 12.5%）') + (n ? _t('；已觸發 ') + n + _t(' 階。') : _t('；目前一階都還沒觸發，價格階梯沒有任何賣出動作。')), ex.next_step_dist_pct < 10 ? 'warn' : 'neu']; }
  function hedgeRead() { var c = D.price.bar.c, s = D.exit.status, sma = s.sma200, run = s.below_sma200_run || 0;
    if (!sma) return null;
    return [c < sma ? _t('收盤在 200 日均線（') + fmt.usd(sma) + _t('）之下，第 ') + run + _t('/5 天；連 5 天就減 20%。') : _t('收盤高於 200 日均線（') + fmt.usd(sma) + _t('），高出 ') + fmt.n((c / sma - 1) * 100, 0) + _t('%；要跌到線下並連 5 日收在下方才會減 20%。'), c < sma ? 'neg' : c / sma - 1 < 0.05 ? 'warn' : 'pos']; }
  function rd2(label, val, r) { return r ? [label, val, r[0], r[1]] : null; }

  /* 價格版 */
  function mkInterp() {
    var p = D.price, b = p.bar, c = b.c, a = p.atr || {}, v = p.vol || {}, my = (p.mayer || {}).mayer, pi = p.pi_cycle, it = [];
    if (b.close_pos_pct != null) it.push([_t('收盤'), fmt.pct(b.chg_pct, 2), _t('收在當日高低區間的 ') + fmt.n(b.close_pos_pct, 0) + _t('% 位置（') + (b.close_pos_pct >= 70 ? _t('收在高檔，買方較強') : b.close_pos_pct <= 30 ? _t('收在低檔，賣方較強') : _t('收在中段，多空互有攻守')) + _t('）') + (b.vol_vs_20dma != null ? _t('；成交量是 20 日均量的 ') + fmt.n(b.vol_vs_20dma, 2) + _t(' 倍') + (b.vol_vs_20dma < 0.6 ? _t('，量縮，這根 K 線的訊號力道弱。') : b.vol_vs_20dma > 1.5 ? _t('，放量，訊號較可信。') : _t('。')) : _t('。')), b.close_pos_pct >= 70 ? 'pos' : b.close_pos_pct <= 30 ? 'neg' : 'neu']);
    if (a.atr14) it.push(['ATR14', fmt.usd(a.atr14), _t('一天的正常波動約 ±') + fmt.usd(a.atr14) + _t('（') + fmt.n(a.atr14 / c * 100, 1) + _t('%）：這個範圍內的漲跌屬日常雜訊；掛單或停損的距離小於它，很容易被正常波動掃到。'), 'neu']);
    if (v.rv30 != null) it.push([_t('實際波動 RV30'), fmt.n(v.rv30, 1) + '%', band(v.rv30, [30, 50, 70], [_t('年化 30% 以下，低波動'), _t('年化 30–50%，一般水準'), _t('年化 50–70%，偏高'), _t('年化 70% 以上，劇烈')]) + rvYear(v) + (v.rv7_rv30 < 0.75 ? _t('；近 7 天明顯比近 30 天平靜（RV7 只有 RV30 的 ') + fmt.n(v.rv7_rv30 * 100, 0) + _t('%），價格在收斂盤整，之後常出現方向性突破。') : v.rv7_rv30 > 1.3 ? _t('；近 7 天波動明顯放大（RV7 是 RV30 的 ') + fmt.n(v.rv7_rv30, 2) + _t(' 倍）。') : _t('。')), 'neu']);
    if (my != null) it.push([_t('Mayer 倍數'), fmt.n(my, 2), band(my, [0.8, 1, 1.5, 2.4], [_t('0.8 以下：歷史便宜區'), _t('0.8–1：價格低於 200 日均線，偏弱但不算便宜'), _t('1–1.5：價格高於 200 日均線、還沒過熱'), _t('1.5–2.4：偏熱'), _t('2.4 以上：歷史過熱區')]) + _t('。'), my < 0.8 ? 'pos' : my >= 2.4 ? 'neg' : my >= 1.5 ? 'warn' : 'neu']);
    var w5 = w50Row(); if (w5) it.push(w5);
    var qy = p.q365;   // 2026-11-09 使用者要求（365 日分位帶）：收盤在近 365 天收盤裡的位置；只用價格，和 Mayer 倍數是同一件事
    if (qy && qy.pct != null) it.push([_T('近一年位置', '1-year position'), _T('第 ' + fmt.n(qy.pct, 0) + ' 百分位', ord(qy.pct) + ' pct'),
      (c < qy.q10 ? _T('過去一年最弱的一成：收盤跌破 10% 線 ' + fmt.k(qy.q10) + '。前三輪的週期低點都落在這種期間，但每段持續 3–7 個月。', 'Weakest tenth of the past year: the close is below the 10% line at ' + fmt.k(qy.q10) + '. The past three cycle lows all came inside such stretches, each lasting 3–7 months.')
        : c < qy.q50 ? _T('偏弱的一半，不在極端：收盤低於過去一年中位數 ' + fmt.k(qy.q50) + '，10% 線在 ' + fmt.k(qy.q10) + '。', 'Weaker half, not extreme: the close is below the past year\'s median of ' + fmt.k(qy.q50) + '; the 10% line is at ' + fmt.k(qy.q10) + '.')
        : c <= qy.q90 ? _T('偏強的一半，不在極端：收盤高於過去一年中位數 ' + fmt.k(qy.q50) + '，90% 線在 ' + fmt.k(qy.q90) + '。', 'Stronger half, not extreme: the close is above the past year\'s median of ' + fmt.k(qy.q50) + '; the 90% line is at ' + fmt.k(qy.q90) + '.')
        : _T('過去一年最強的一成：收盤站上 90% 線 ' + fmt.k(qy.q90) + '，常見於上升段。', 'Strongest tenth of the past year: the close is above the 90% line at ' + fmt.k(qy.q90) + ', typical of an uptrend.'))
      + _T('它只用價格算，和 Mayer 倍數是同一件事，不要算成兩個訊號。', ' Built from price alone, it says the same thing as the Mayer multiple; don\'t count them as two signals.'),
      c < qy.q10 ? 'neg' : c > qy.q90 ? 'pos' : 'neu']);
    if (pi != null) it.push(['Pi Cycle', fmt.n(pi, 2), pi >= 1 ? _t('已到 1：歷史頂部訊號觸發。') : pi >= 0.9 ? _t('接近 1，頂部訊號逼近。') : _t('只有 ') + fmt.n(pi, 2) + _t('，離觸發（1）很遠，沒有頂部跡象。'), pi >= 1 ? 'neg' : pi >= 0.9 ? 'warn' : 'neu']);
    return it;
  }
  /* 2026-11-09 使用者要求（國外 X 多用 50 週均線看牛熊，本站用 200 日）：50 週均線的週收盤讀值。週收盤＝週日的日收盤；
     列出最近一根週 K 在上／下、連幾週、和 200 日均線是否同調，以及 2013 年起每次週收盤跌破後多久收回。只作讀值 */
  function w50Row() {
    var w = ((D.cycle || {}).levels || {}).w50; if (!w) return null;
    var B = (w.breaks || []).filter(function (b) { return b.weeks != null; }), q = function (f) { return B.filter(f); };
    var fast = q(function (b) { return b.weeks <= 2; }), mid = q(function (b) { return b.weeks > 2 && b.weeks < 26; }), slow = q(function (b) { return b.weeks >= 26; });
    var rng = function (A) { var v = A.map(function (b) { return b.weeks; }), lo = Math.min.apply(null, v), hi = Math.max.apply(null, v); return lo === hi ? '' + lo : lo + '–' + hi; };
    var yrs = slow.map(function (b) { return b.date.slice(0, 4); }), y0 = (w.since || '').slice(0, 4), cr = w.cross, fresh = cr && cr.date === w.date, ab = w.above, a2 = w.above200, L = w.live;
    var t = _T(fmt.md(w.date) + ' 週收盤 ' + fmt.usd(w.close) + (ab ? '，高於' : '，低於') + ' 50 週均線 ' + fmt.usd(w.ma) + '（' + fmt.pct(w.dist_pct, 1) + '）',
      'The ' + fmt.md(w.date) + ' weekly close of ' + fmt.usd(w.close) + ' is ' + fmt.n(Math.abs(w.dist_pct), 1) + '% ' + (ab ? 'above' : 'below') + ' the 50-week MA at ' + fmt.usd(w.ma));
    t += fresh ? _T('，是連 ' + cr.prev_run + ' 週在' + (ab ? '下方之後第一次收回上方。' : '上方之後第一次收在下方。'), ', the first close ' + (ab ? 'back above' : 'below') + ' it after ' + cr.prev_run + ' weeks ' + (ab ? 'below.' : 'above.'))
      : _T('，已連 ' + w.run + ' 週在' + (ab ? '上方' : '下方') + (cr ? '（' + ymdD(cr.date) + (cr.up ? ' 站回）' : ' 跌破）') : '') + '。', ', ' + w.run + ' weeks ' + (ab ? 'above' : 'below') + ' in a row' + (cr ? ' (' + (cr.up ? 'reclaimed ' : 'lost ') + ymdD(cr.date) + ')' : '') + '.');
    if (a2 != null && w.sma200) t += a2 !== ab
      ? _T('但收盤仍在 200 日均線 ' + fmt.usd(w.sma200) + (a2 ? ' 之上' : ' 之下') + '，兩條線目前不同調：50 週偏' + (ab ? '多' : '空') + '、200 日偏' + (a2 ? '多。' : '空。'),
        ' Yet the close is still ' + (a2 ? 'above' : 'below') + ' the 200-day MA at ' + fmt.usd(w.sma200) + ', so the two lines disagree: the 50-week reads ' + (ab ? 'bullish' : 'bearish') + ', the 200-day ' + (a2 ? 'bullish.' : 'bearish.'))
      : _T('收盤也在 200 日均線 ' + fmt.usd(w.sma200) + (a2 ? ' 之上' : ' 之下') + '，兩條線同調。', ' The close is also ' + (a2 ? 'above' : 'below') + ' the 200-day MA at ' + fmt.usd(w.sma200) + '; the two lines agree.');
    if (B.length) t += _T(y0 + ' 年起週收盤跌破 ' + B.length + ' 次：' + [fast.length ? fast.length + ' 次兩週內就收回' : '', mid.length ? mid.length + ' 次 ' + rng(mid) + ' 週後收回' : '', slow.length ? slow.length + ' 次在下方待了 ' + rng(slow) + ' 週（' + yrs.join('、') + ' 年，都是熊市）' : ''].filter(Boolean).join('，') + '。',
      ' Since ' + y0 + ' the weekly close has broken below it ' + B.length + ' times: ' + [fast.length ? fast.length + ' reclaimed it within two weeks' : '', mid.length ? mid.length + ' after ' + rng(mid) + ' weeks' : '', slow.length ? slow.length + ' stayed below for ' + rng(slow) + ' weeks (' + yrs.join(', ') + ', all bear markets)' : ''].filter(Boolean).join(', ') + '.');
    if (L) t += _T('本週還沒收，用 ' + fmt.md(L.date) + ' 收盤 ' + fmt.usd(L.price) + ' 代入，在 50 週均線 ' + fmt.usd(L.ma) + (L.above ? ' 之上' : ' 之下') + '（' + fmt.pct(L.dist_pct, 1) + '）。',
      ' This week has not closed; with the ' + fmt.md(L.date) + ' close of ' + fmt.usd(L.price) + ' it sits ' + fmt.n(Math.abs(L.dist_pct), 1) + '% ' + (L.above ? 'above' : 'below') + ' the 50-week MA at ' + fmt.usd(L.ma) + '.');
    t += _T('看的是週日的收盤，週中跌破不算。', ' Only the Sunday close counts; breaks during the week do not.');
    return [_T('50 週均線', '50-week MA'), _T('週收盤 ', 'Weekly ') + fmt.pct(w.dist_pct, 1), t, ab ? 'pos' : w.run >= 2 ? 'neg' : 'warn'];
  }
  function levelsSay(lv, c) {
    var up = lv.filter(function (x) { return x[0] > c; }).pop(), dn = lv.filter(function (x) { return x[0] <= c; })[0];
    return _t('<p class="say">上方最近：<b>') + (up ? up[1] + ' ' + fmt.k(up[0]) : '—') + '</b>' + (up ? _t('（') + fmt.pct((up[0] / c - 1) * 100) + _t('）') : '') + _t('；下方最近：<b>') + (dn ? dn[1] + ' ' + fmt.k(dn[0]) : '—') + '</b>' + (dn ? _t('（') + fmt.pct((dn[0] / c - 1) * 100) + _t('）') : '') + _t('。價格常在這些位置停頓或反轉，但沒有一條是必守的。</p>');
  }
  function maSay(ma, c) {
    var s = function (v) { return c >= v; }, L = s(ma.sma200), M = s(ma.sma50), S = s(ma.sma20);
    var w = L && M && S ? _t('長、中、短線都在均線之上，多頭排列') : L && M ? _t('長線、中線仍是多頭，短線（20 日）跌到均線下方在整理') : L ? _t('長線（200 日）仍是多頭，但中短線轉弱') : !M && !S ? _t('長、中、短線都在均線之下，空頭排列') : _t('長線（200 日）在均線之下，中短線反彈中');
    return '<p class="say">' + w + _t('。</p>');
  }

  /* 籌碼集中度（2026-10-15）：現價 ±5% 內的 URPD 籌碼佔流通量，只作讀值、不設門檻 */
  function concNow() { return ((D.chips || {}).flow || {}).conc5 || null; }
  function concAgo(days) { var h = (D.chips || {}).conc_hist || [], t = h.length ? h[h.length - 1][0] - days : 0, r = null; h.forEach(function (x) { if (x[0] <= t) r = x; }); return r; }
  /* 2026-11-05 使用者要求「籌碼結構＋集中度」（BRS 是 Glassnode 付費專有指標、算法不公開，使用者決定不放替代分數）：
     上格價格＋右緣當天的長短期持有者籌碼分布、現價 ±5% 區間；下格 2018 起的集中度（Bitview），標出前 10% 的高水位。只作讀值 */
  function concCohortSay() {
    var co = (D.chips || {}).cohort || {}, R_ = co.rows || [], c = D.price.bar.c, w = co.width || 2000; if (!R_.length) return null;
    var side = function (lo, hi) { var b = R_.filter(function (r) { return r[0] + w > lo && r[0] < hi; }).sort(function (a, b) { return (b[1] + b[2]) - (a[1] + a[2]); })[0]; return b && b[1] + b[2] > 0 ? b : null; };
    var dn_ = side(c * 0.9, c), up_ = side(c, c * 1.1), f = function (b) { var t = b[1] + b[2]; return fmt.k(b[0]) + '–' + fmt.k(b[0] + w) + _T('（' + fmt.n(t / 1e4, 0) + ' 萬顆，短期持有者佔 ' + fmt.n(b[1] / t * 100, 0) + '%）', ' (' + fmt.n(t / 1e3, 0) + 'K BTC, ' + fmt.n(b[1] / t * 100, 0) + '% short-term holders)'); };
    return [_T('籌碼結構', 'Supply structure'), dn_ && up_ ? fmt.k(dn_[0]) + ' / ' + fmt.k(up_[0]) : '—',
      _T('現價下方 10% 內最厚的一格：' + (dn_ ? f(dn_) : '沒有') + '；上方 10% 內最厚：' + (up_ ? f(up_) : '沒有') + '。短期持有者多的格子是近 155 天買進的，價格回到這裡時比較容易出現解套賣壓或防守買盤。籌碼分布是 ' + fmt.md(co.now_date || co.date) + ' 的（CheckOnChain，逐筆 UTXO）。',
        'Thickest bucket within 10% below: ' + (dn_ ? f(dn_) : 'none') + '; within 10% above: ' + (up_ ? f(up_) : 'none') + '. Buckets heavy in short-term holders were bought in the last 155 days, so price returning there tends to meet break-even selling or defensive buying. Distribution as of ' + fmt.md(co.now_date || co.date) + ' (CheckOnChain, per UTXO).'), 'neu'];
  }
  function concItems() {
    var k = concNow(), cs = (D.chips || {}).conc_stats || {}, a = concAgo(7), it = []; if (!k) return it;
    var hiN = (cs.episodes || []).filter(function (e) { return e[2] != null; }), up = hiN.filter(function (e) { return e[2] > 0; }).length, ex = function (e) { return fmt.date(dnOf(e[0])).slice(0, 7) + ' ' + fmt.pct(e[2], 0); };
    var big = hiN.slice().sort(function (x, y) { return Math.abs(y[2]) - Math.abs(x[2]); }).slice(0, 2).sort(function (x, y) { return x[0] < y[0] ? -1 : 1; });
    it.push([_T('現價 ±5% 籌碼', 'Within ±5% of price'), fmt.n(k.pct, 1) + '%', _T('現價 ±5%（' + fmt.k(k.lo) + '–' + fmt.k(k.hi) + '）內有 ' + fmt.n(k.btc / 1e4, 0) + ' 萬顆，佔全部供給 ' + fmt.n(k.pct, 1) + '%' + (a ? '，7 天前 ' + fmt.n(a[2], 1) + '%' : '') + '；' + (cs.since ? cs.since.slice(0, 4) + ' 年以來第 ' + fmt.n(cs.pct_now, 0) + ' 百分位（最高 ' + fmt.n(cs.max, 1) + '%）' : '') + '。籌碼越集中，價格離開這一帶時越容易一起停損或一起解套，波動容易放大；它不指方向。',
      'Within ±5% of price (' + fmt.k(k.lo) + '–' + fmt.k(k.hi) + ') sit ' + (k.btc / 1e6).toFixed(2) + 'M BTC, ' + fmt.n(k.pct, 1) + '% of supply' + (a ? ' (' + fmt.n(a[2], 1) + '% a week ago)' : '') + (cs.since ? '; ' + fmt.n(cs.pct_now, 0) + 'th percentile since ' + cs.since.slice(0, 4) + ' (record ' + fmt.n(cs.max, 1) + '%)' : '') + '. The more crowded, the more a move out of this band triggers stops or break-even selling together, so volatility tends to expand; it says nothing about direction.'), k.pct >= (cs.p90 || 99) ? 'warn' : 'neu']);
    if (cs.hi_med30 != null) it.push([_T('高集中之後', 'After high concentration'), fmt.n(cs.hi_med30, 0) + '% / ' + fmt.n(cs.lo_med30, 0) + '%',
      _T('集中度在前 10%（≥ ' + fmt.n(cs.p90, 1) + '%）的日子，之後 30 天最大波動的中位數 ' + fmt.n(cs.hi_med30, 1) + '%、超過 15% 的佔 ' + cs.hi_gt15 + '%；其他日子 ' + fmt.n(cs.lo_med30, 1) + '%、' + cs.lo_gt15 + '%。方向不定：' + cs.since.slice(0, 4) + ' 年以來首次衝上前 10% 的 ' + hiN.length + ' 次，30 天後 ' + up + ' 次漲、' + (hiN.length - up) + ' 次跌' + (big.length ? '（例如 ' + big.map(ex).join('、') + '）' : '') + '。',
        'Days in the top 10% (≥ ' + fmt.n(cs.p90, 1) + '%) saw a median 30-day maximum move of ' + fmt.n(cs.hi_med30, 1) + '%, with ' + cs.hi_gt15 + '% above 15%; other days ' + fmt.n(cs.lo_med30, 1) + '% and ' + cs.lo_gt15 + '%. No direction: of ' + hiN.length + ' first entries into the top 10% since ' + cs.since.slice(0, 4) + ', ' + up + ' were higher 30 days later and ' + (hiN.length - up) + ' lower' + (big.length ? ' (e.g. ' + big.map(ex).join(', ') + ')' : '') + '.'), 'neu']);
    var cc = concCohortSay(); if (cc) it.push(cc);
    return it;
  }
  function concPanel() {
    var k = concNow(), cs = (D.chips || {}).conc_stats || {}; if (!k) return '';
    return panel('span-12', _T('籌碼結構與集中度', 'Supply structure and concentration'), _T('Bitview · ' + (cs.since || '').slice(0, 4) + ' 起 · 只作讀值', 'Bitview · since ' + (cs.since || '').slice(0, 4) + ' · reading only'),
      interpHtml(concItems()) + legend([[_T('BTC 價格（上格）', 'BTC price (top)'), 'var(--ink-2)'], [_T('長期持有者籌碼', 'Long-term holder supply'), 'var(--s1)', 'box'], [_T('短期持有者籌碼', 'Short-term holder supply'), 'var(--s2)', 'box'], [_T('現價 ±5% 區間', '±5% of price'), 'var(--s3)', 'box'], [_T('集中度（下格）', 'Concentration (bottom)'), 'var(--s3)'], [_T('前 10% 高水位', 'Top-10% line'), 'var(--warn)', 'dash']]) + '<div class="chart" id="c-conc"></div>');
  }
  function drawConc(el) {
    var h = ((D.chips || {}).conc_hist || []).filter(function (r) { return r[1] && r[2] != null; }), cs = (D.chips || {}).conc_stats || {}, co = (D.chips || {}).cohort || {}, k = concNow(); if (h.length < 30 || !el) return;
    var mx = Math.max(10, Math.ceil(Math.max.apply(null, h.map(function (r) { return r[2]; })) / 5) * 5), p90 = cs.p90;
    if (el._rng == null) el._rng = 365;   // 預設近 1 年：全部（2018 起、價格 3K–120K）時右緣的籌碼分布會被壓得很扁
    if (el.clientWidth < 420) h = h.filter(function (r) { return r[0] >= h[h.length - 1][0] - 365; });   // 手機沒有時間範圍按鈕，直接只畫近 1 年
    twoPane(el, { rows: h, pi: 1, hp: [150, 210], hs: [130, 170], label: _T('集中度：現價 ±5% 內的籌碼佔全部供給（%）', 'Concentration: supply within ±5% of price (%)'), aria: _T('BTC 價格、籌碼分布與集中度', 'BTC price, supply distribution and concentration'),
      scale: function (C) { return function (v) { return C.ys0 + (1 - v / mx) * C.hs; }; },
      body: function (C) {
        var s = '';
        for (var g = 0; g <= mx; g += 5) s += C.gl(C.Ys(g), g + '%', g ? 'gl' : 'base');
        if (p90) { var yp = C.Ys(p90); s += '<rect x="' + C.ML + '" y="' + C.Ys(mx).toFixed(1) + '" width="' + C.pw + '" height="' + (yp - C.Ys(mx)).toFixed(1) + '" fill="color-mix(in srgb, var(--warn) 9%, transparent)"/><line x1="' + C.ML + '" x2="' + (C.ML + C.pw) + '" y1="' + yp.toFixed(1) + '" y2="' + yp.toFixed(1) + '" stroke="var(--warn)" stroke-dasharray="4 4" stroke-width="1"/>' + C.tx(C.ML + 6, yp - 5, _T('前 10%（' + fmt.n(p90, 1) + '%）', 'top 10% (' + fmt.n(p90, 1) + '%)')).replace('class="ax"', 'class="ax" fill="var(--warn)"'); }
        var pts = C.rows.map(function (r) { return C.X(r[0]).toFixed(1) + ',' + C.Ys(r[2]).toFixed(1); });
        s += '<path d="M' + C.X(C.rows[0][0]).toFixed(1) + ',' + C.yb.toFixed(1) + 'L' + pts.join('L') + 'L' + C.X(C.rows[C.rows.length - 1][0]).toFixed(1) + ',' + C.yb.toFixed(1) + 'Z" fill="color-mix(in srgb, var(--s3) 16%, transparent)"/>';
        s += '<path class="ln" d="M' + pts.join('L') + '" stroke="var(--s3)" stroke-width="1.6"/>';
        return s;
      },
      over: function (C) {
        var s = '', R_ = co.rows || [], w = co.width || 2000, ps = C.rows.map(function (r) { return r[1]; }), lo = Math.min.apply(null, ps), hi = Math.max.apply(null, ps);
        var vis = R_.filter(function (r) { var yt = C.Yp(r[0] + w), yb = C.Yp(r[0]); return yt >= C.MT && yb <= C.MT + C.hp && r[1] + r[2] > 0; }), m = Math.max.apply(null, vis.map(function (r) { return r[1] + r[2]; }).concat([1])), L = C.pw * 0.24, xr = C.ML + C.pw;
        if (k) { var y1 = C.Yp(k.hi), y0 = C.Yp(k.lo), bx = xr - L - 14; s += '<rect x="' + bx.toFixed(1) + '" y="' + y1.toFixed(1) + '" width="' + (xr - bx).toFixed(1) + '" height="' + (y0 - y1).toFixed(1) + '" fill="color-mix(in srgb, var(--s3) 18%, transparent)" stroke="var(--s3)" stroke-opacity=".5" stroke-dasharray="3 3"/>'; }   // 現價 ±5%：只畫在右緣分布旁邊
        vis.forEach(function (r) {   // 右緣籌碼分布：長期持有者（紫）貼右邊、短期持有者（橙）接在左邊；長度按顆數
          var yt = C.Yp(r[0] + w), yb = C.Yp(r[0]), hh = Math.max(1, yb - yt - 1), ll = r[2] / m * L, sl = r[1] / m * L;
          if (yt < C.MT || yb > C.MT + C.hp) return;   // 只畫在上格的價格範圍內
          if (ll > 0.3) s += '<rect x="' + (xr - ll).toFixed(1) + '" y="' + (yt + 0.5).toFixed(1) + '" width="' + ll.toFixed(1) + '" height="' + hh.toFixed(1) + '" fill="var(--s1)" opacity=".5"/>';
          if (sl > 0.3) s += '<rect x="' + (xr - ll - sl).toFixed(1) + '" y="' + (yt + 0.5).toFixed(1) + '" width="' + sl.toFixed(1) + '" height="' + hh.toFixed(1) + '" fill="var(--s2)" opacity=".6"/>';
        });
        (cs.episodes || []).forEach(function (e) { var t = dnOf(e[0]); if (t < C.rows[0][0]) return; s += '<circle cx="' + C.X(t).toFixed(1) + '" cy="' + C.Ys(e[1]).toFixed(1) + '" r="3.5" fill="var(--deck)" stroke="var(--warn)" stroke-width="1.8"/>'; });
        var lr = C.rows[C.rows.length - 1]; s += '<circle cx="' + C.X(lr[0]).toFixed(1) + '" cy="' + C.Ys(lr[2]).toFixed(1) + '" r="4" fill="var(--s3)" stroke="var(--deck)" stroke-width="2"/>';
        return s;
      },
      tip: function (p, C) { return { dots: '<circle cx="' + C.X(p[0]).toFixed(1) + '" cy="' + C.Ys(p[2]).toFixed(1) + '" r="3.5" fill="var(--s3)" stroke="var(--deck)" stroke-width="1.5"/>', rows: tipRow1('var(--s3)', _T('集中度', 'Concentration'), fmt.n(p[2], 2) + '%') + tipRow1('var(--ink-2)', _T('收盤', 'Close'), fmt.usd(p[1])) }; } });
  }
  function concSay(k, dvol) {
    var a = concAgo(7), h = (D.chips || {}).conc_hist || [];
    var wk = a ? _T('，7 天前 ' + fmt.n(a[2], 1) + '%', '; ' + fmt.n(a[2], 1) + '% a week ago') : '';
    var lowIv = dvol && dvol.pct_1y != null && dvol.pct_1y < 30;
    return _T('現價 ±5%（' + fmt.k(k.lo) + '–' + fmt.k(k.hi) + '）內有 ' + fmt.n(k.btc / 1e4, 0) + ' 萬顆，佔流通 ' + fmt.n(k.pct, 1) + '%' + wk + '。籌碼越集中，價格離開這一帶時越容易引發一起停損或一起解套，波動容易放大；它不指方向。' + (lowIv ? '目前 DVOL 也在一年偏低處：籌碼擠在現價附近、選擇權又不貴。' : '') + '本站從 2026-10-01 才開始記錄（' + h.length + ' 天），還不足以判斷高低。',
      'Within ±5% of price (' + fmt.k(k.lo) + '–' + fmt.k(k.hi) + ') sit ' + (k.btc / 1e6).toFixed(2) + 'M BTC, ' + fmt.n(k.pct, 1) + '% of circulating supply' + wk + '. The more supply crowds here, the more likely a move out of this band sets off stop-losses or break-even selling together, so volatility tends to expand; it says nothing about direction.' + (lowIv ? ' DVOL is also low for the year: supply is crowded near price and options are cheap.' : '') + ' We have only tracked it since 2026-10-01 (' + h.length + ' days), too short to call it high or low.');
  }

  /* 2026-11-07 指標擴充：賣壓累積（0–100）與動能品質（0–1），本站自製、只用每日收盤（取代 11/05 的短期壓力分數）。只作讀值 */
  var SX_K = { bottom: ['warn', '底部組合成立', 'Bottom combo on', 'Combo on'], near: ['warn', '接近底部組合', 'Near the bottom combo', 'Near combo'], build: ['neu', '賣壓累積中', 'Pressure building', 'Building'],
    strong: ['neu', '強勢動能', 'Strong momentum', 'Strong'], calm: ['neu', '沒有累積', 'No build-up', 'Calm'] };   // 第 4 欄：英文狀態卡用的短字（大字放不下長句）
  function sxX() { return (D.chips || {}).stress || null; }
  function sxDl(a, b, dg, upBad) { if (a == null || b == null) return ''; var d = a - b; return '<em class="' + ((d >= 0) !== upBad ? 'up' : 'dn') + '">' + (d >= 0 ? '▲ ' : '▼ ') + fmt.n(Math.abs(d), dg) + _T(' / 7 天', ' / 7d') + '</em>'; }   // 賣壓上升是壞事，顏色和一般箭頭相反
  function sxSay() {
    var x = sxX(); if (!x || x.r == null) return [];
    var it = [], K = SX_K[x.state] || SX_K.calm, sf = function (v) { return fmt.n(v, 2); }, now;
    var rz = x.rise_from ? _T('，' + fmt.md(x.rise_from) + ' 起從 0 升上來', '; rising from 0 since ' + fmt.md(x.rise_from)) : '';
    var head = _T('賣壓累積 ' + x.r + '（7 天前 ' + x.r7 + rz + '），動能品質 ' + sf(x.s) + '（7 天前 ' + sf(x.s7) + '）。', 'pressure ' + x.r + ' (' + x.r7 + ' a week ago' + rz + '), momentum quality ' + sf(x.s) + ' (' + sf(x.s7) + ' a week ago). ');
    if (x.state === 'bottom') now = _T('兩個條件同時成立：賣壓到 100（已連 ' + (x.at100 + 1) + ' 天）、動能低於 0.3。弱勢已經拖了一段時間，而且還在跌得又快又穩，過去這種時候常在一段下跌的後段，但短期常常還有一跌。', 'Both conditions hold: pressure at 100 (' + (x.at100 + 1) + ' days) and momentum below 0.3. Weakness has dragged on and the drop is still fast and steady; in the past this often came late in a decline, though another leg down was common first.');
    else if (x.state === 'near' && x.s >= 0.3 && x.r < 100) now = _T('兩個條件都差一點：賣壓還差 ' + (100 - x.r) + ' 分到 100，動能 ' + sf(x.s) + ' 還沒低於 0.3。', 'Both conditions are close: pressure is ' + (100 - x.r) + ' points short of 100 and momentum ' + sf(x.s) + ' is not yet below 0.3.');
    else if (x.state === 'near') now = x.s < 0.3 ? _T('動能已經低於 0.3，賣壓還差 ' + (100 - x.r) + ' 分到 100；再弱幾天，底部組合就成立。', 'Momentum is already below 0.3; pressure is ' + (100 - x.r) + ' points short of 100. A few more weak days would complete the bottom combo.') : _T('賣壓已經到 100，動能 ' + sf(x.s) + ' 還在 0.3 之上；跌勢要更快更穩，底部組合才成立。', 'Pressure is at 100 but momentum ' + sf(x.s) + ' is still above 0.3; the drop would need to get faster and steadier to complete the combo.');
    else if (x.state === 'build') now = _T('動能一直在 0.45 以下，弱勢拖得越久分數越高；一段又快又穩的上漲（動能到 0.7）會直接歸零。', 'Momentum has stayed under 0.45, and the longer weakness drags on the higher it climbs; a fast, steady rally (momentum 0.7) resets it to zero.');
    else if (x.state === 'strong') now = _T('賣壓 0、動能高於 0.85：近 21 天漲得又快又穩。', 'Pressure 0 and momentum above 0.85: the last 21 days rose fast and steadily.');
    else now = _T('賣壓 0：最近沒有拖著的弱勢。', 'Pressure 0: no lingering weakness lately.');
    it.push([_T('現在', 'Now'), x.r + ' · ' + sf(x.s), _T(K[1] + '：', K[2] + ': ') + head + now, K[0]]);
    if (x.f90 && x.f90.n) it.push([_T('底部組合之後', 'After the bottom combo'), x.f90.up + '/' + x.f90.n,
      _T(x.since.slice(0, 4) + ' 年起 ' + x.f90.n + ' 次（和上一次相隔 60 天以上才算新的一次）。30 天後：', 'Since ' + x.since.slice(0, 4) + ', ' + x.f90.n + ' times (60+ days apart). 30 days later: ') + oxStat(x.f30, x.base30) + _T('；90 天後：', '; 90 days later: ') + oxStat(x.f90, x.base90) + _T('。短期常常還有一跌，拉長到 3 個月才比平常好。', '. Another leg down was common in the short run; only over three months did it beat a random day.'), 'neu']);
    var ex = x.ex || {}, bad = (x.ev || []).filter(function (e) { return e.ret != null; }).sort(function (a, b) { return a.ret - b.ret; }).slice(0, 4), op = (x.ev || []).filter(function (e) { return e.ret == null; })[0];
    if (ex.n) it.push([_T('等賣壓歸零再出場', 'Exit when pressure resets'), ex.win + '/' + ex.n,
      _T('底部組合出現時買進、賣壓回到 0 時賣出：' + ex.n + ' 次中 ' + ex.win + ' 次獲利，報酬中位數 ' + fmt.pct(ex.med, 1) + '、持有中位數 ' + ex.days + ' 天，中途最深再跌的中位數 ' + fmt.pct(ex.dip, 1) + '。分年代：' + (x.era || []).map(function (e) { return e.lo + '–' + e.hi.slice(2) + ' 年 ' + e.win + '/' + e.n; }).join('、') + '。虧最多的幾次多在熊市初期：' + bad.map(function (e) { return oxYm(e.date) + ' ' + fmt.pct(e.ret, 0); }).join('、') + '。' + (op ? '最近一次 ' + ymdS(op.date) + ' 還沒歸零。' : ''),
        'Buy when the combo appears, sell when pressure returns to 0: ' + ex.win + ' of ' + ex.n + ' won, median ' + fmt.pct(ex.med, 1) + ' over a median ' + ex.days + ' days, with a median further dip of ' + fmt.pct(ex.dip, 1) + ' along the way. By era: ' + (x.era || []).map(function (e) { return e.lo + '–' + e.hi.slice(2) + ' ' + e.win + '/' + e.n; }).join(', ') + '. The worst ones mostly came early in bear markets: ' + bad.map(function (e) { return oxYm(e.date) + ' ' + fmt.pct(e.ret, 0); }).join(', ') + '.' + (op ? ' The latest, ' + ymdS(op.date) + ', has not reset yet.' : '')), 'neu']);
    var tp = (x.top || {}).f90; if (tp && tp.n) it.push([_T('強勢動能不是頂部', 'Strong momentum is not a top'), tp.up + '/' + tp.n,
      _T('賣壓 0 且動能高於 0.85（漲得又快又穩）的 ' + tp.n + ' 次，90 天後 ' + tp.up + ' 次上漲、中位數 ' + fmt.pct(tp.med, 1) + '：多半是行情延續；只有熊市裡的反彈才常在這時見局部高點。',
        'Of ' + tp.n + ' times with pressure 0 and momentum above 0.85 (a fast, steady rise), ' + tp.up + ' were higher 90 days later, median ' + fmt.pct(tp.med, 1) + ': usually continuation; only bear-market rallies tended to peak here.'), 'neu']);
    return it;
  }
  function sxPanel() {
    var x = sxX(); if (!x || !x.rows || x.r == null) return '';
    var K = SX_K[x.state] || SX_K.calm, sub = x.at100 ? _T('已連 ' + (x.at100 + 1) + ' 天在 100', (x.at100 + 1) + ' days at 100') : x.rise_from ? _T(fmt.md(x.rise_from) + ' 起從 0 升上來', 'up from 0 since ' + fmt.md(x.rise_from)) : _T('目前沒有累積', 'nothing built up');
    return panel('span-12', _T('賣壓累積與動能品質', 'Selling pressure and momentum quality'), _T('本站自製 · 每日收盤 · ' + fmt.md(x.date), 'Ours · daily closes · ' + fmt.md(x.date)),
      '<div class="cf-hero">' + oxCard('var(--down)', _T('賣壓累積', 'Selling pressure'), x.r + ' / 100', sub, sxDl(x.r, x.r7, 0, true)) +
        oxCard('var(--s3)', _T('動能品質', 'Momentum quality'), fmt.n(x.s, 2), x.s < 0.3 ? _T('低於 0.3：跌得又快又穩', 'below 0.3: falling fast and steadily') : x.s > 0.85 ? _T('高於 0.85：漲得又快又穩', 'above 0.85: rising fast and steadily') : _T('0–1，0.5 是不漲不跌', '0–1; 0.5 is flat'), sxDl(x.s, x.s7, 2, false)) +
        oxCard('var(--ink-2)', _T('狀態', 'State'), _T(K[1], K[3]), _T('底部組合：賣壓 100 且動能 < 0.3', 'Bottom combo: pressure 100 and momentum < 0.3')) + '</div>' +
      interpHtml(sxSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('賣壓累積（0–100）', 'Selling pressure (0–100)'), 'var(--down)'], [_T('動能品質（0–1）', 'Momentum quality (0–1)'), 'var(--s3)'], [_T('動能 0.3 線', 'Momentum 0.3 line'), 'var(--s3)', 'dash'], [_T('底部組合到賣壓歸零', 'Bottom combo until pressure resets'), 'var(--s3)', 'box']]) +
      '<div class="chart cf-chart" id="c-sx"></div><p class="note">' + _T('本站自製，只用每日收盤。動能品質＝近 21 天日報酬的平均 ÷ 標準差 × √21，用常態分布換成 0–1：漲得又快又穩接近 1、跌得又快又穩接近 0。賣壓累積＝動能低於 0.45 時每天往上加（離 0.45 越遠加越多）、高於 0.45 時往下減，動能一到 0.7 直接歸零，夾在 0–100。底部組合＝賣壓 100 且動能低於 0.3。回測只有二十幾次，換一個收盤價來源或參數稍微調一下，次數和勝率就會變幾次。只作讀值，不是買賣訊號。',
        'Ours, from daily closes only. Momentum quality = mean ÷ standard deviation of the last 21 daily returns × √21, mapped to 0–1 with the normal distribution: near 1 for a fast, steady rise, near 0 for a fast, steady fall. Selling pressure adds up each day momentum sits below 0.45 (more the further below), drains when it is above, and resets to zero once momentum reaches 0.7, capped at 0–100. Bottom combo = pressure 100 and momentum below 0.3. The backtest has only twenty-odd cases; a different close source or a small parameter change shifts the counts by a few. Reading only, not a trade signal.') + '</p>', '', 'sx');
  }
  function drawSx(el) {
    var x = sxX(); if (!x || !el) return;
    var rows = x.rows.map(function (r) { return [r[0], r[1], r[2], r[3] == null ? null : r[3] * 100]; });
    if (el.clientWidth < 420) rows = rows.filter(function (r) { return r[0] >= rows[rows.length - 1][0] - 365; });   // 手機沒有時間範圍按鈕，只畫近 1 年
    oxPane(el, { rows: rows, rng: 365, y0: 0, y1: 100, ticks: [0, 25, 50, 75, 100], fmt: function (v) { return fmt.n(v, 0); },
      label: _T('賣壓累積 0–100；動能品質 0–1 畫在同一高度（0.3 對到 30）', 'Pressure 0–100; momentum 0–1 on the same height (0.3 at 30)'), aria: _T('BTC 價格、賣壓累積與動能品質', 'BTC price, selling pressure and momentum quality'),
      refs: [{ y: 30, col: 'var(--s3)', lab: _T('動能 0.3', 'momentum 0.3') }],
      vbands: (x.ev || []).map(function (e) { return { x0: dnOf(e.date), x1: e.exit ? dnOf(e.exit) : rows[rows.length - 1][0], col: 'var(--s3)', op: 0.12 }; }),
      lines: [{ i: 3, col: 'var(--s3)', w: 1.4, name: _T('動能品質', 'Momentum quality'), tfmt: function (v) { return fmt.n(v / 100, 2); } },
        { i: 2, col: 'var(--down)', w: 1.9, name: _T('賣壓累積', 'Selling pressure'), tfmt: function (v) { return fmt.n(v, 0) + ' / 100'; } }],
      marks: (x.ev || []).map(function (e) { return { x: dnOf(e.date), y: 100, t: e.f90 == null ? _T('底部組合', 'combo') : _T('90 天 ', '90d ') + fmt.pct(e.f90, 0), col: e.f90 == null ? 'var(--s3)' : e.f90 >= 0 ? 'var(--up)' : 'var(--down)', up: false }; }),
      now: { i: 2, col: 'var(--down)', lab: String(x.r) } });
  }

  /* 2026-11-08 指標擴充：隱含波動率期限結構（Deribit 各到期日的 ATM 標記隱含波動）。Deribit 沒有免費的歷史曲線，每天收盤後快照一次，2026-11-07 起累積。只作讀值 */
  var IVT_K = { inv: ['warn', '倒掛：近月較貴', 'Inverted: near term pricier', 'Inverted'], flat: ['neu', '大致持平', 'Roughly flat', 'Flat'], norm: ['neu', '正常：遠月較貴', 'Normal: longer dated pricier', 'Normal'] };   // 第 4 欄：英文狀態卡用的短字
  function ivtX() { return (D.deriv || {}).ivterm || null; }
  function ivtSg(v) { return v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + fmt.n(Math.abs(v), 1); }
  function ivtDl(a, b) { if (a == null || b == null) return ''; var d = a - b; return '<em>' + (d >= 0 ? '▲ ' : '▼ ') + fmt.n(Math.abs(d), 1) + _T(' 點 / 7 天', ' pt / 7d') + '</em>'; }   // 波動高低沒有好壞，不上綠紅
  function ivtSay() {
    var x = ivtX(); if (!x || !x.t) return [];
    var it = [], t = x.t, K = IVT_K[x.state] || IVT_K.flat, p = x.prev7, v = function (k) { return t[k] == null ? '—' : fmt.n(t[k], 1) + '%'; };
    var shape = x.state === 'inv' ? _T('近月比遠月貴：市場覺得眼前幾天的風險比較大，常見於急跌、清算潮或大事件前後。', 'Near-dated options cost more than longer-dated ones: the market sees more risk in the next few days, as is common around sharp drops, liquidation waves or big events.')
      : x.state === 'norm' ? _T('遠月比近月貴：時間越長、不確定越多，市場平靜時通常是這個形狀。', 'Longer-dated options cost more: more time means more uncertainty, the usual shape in calm markets.')
      : _T('近月和遠月相差不到 1 點：市場對眼前幾天和幾個月後的波動看法差不多。', 'Near and far differ by less than a point: the market expects about the same volatility now as months out.');
    it.push([_T('現在', 'Now'), ivtSg(x.slope), _T(K[1] + '。7 天 ' + v(7) + '、30 天 ' + v(30) + '、90 天 ' + v(90) + '、180 天 ' + v(180) + '，7 天減 90 天 ' + ivtSg(x.slope) + ' 點。', K[2] + '. 7 days ' + v(7) + ', 30 days ' + v(30) + ', 90 days ' + v(90) + ', 180 days ' + v(180) + '; 7 days minus 90 days is ' + ivtSg(x.slope) + ' points. ') + shape, K[0]]);
    if (p && p.slope != null && p.t) {
      var d7 = t[7] - p.t[7], d90 = t[90] - p.t[90], mv = function (d) { return _T((d >= 0 ? '升 ' : '降 ') + fmt.n(Math.abs(d), 1) + ' 點', (d >= 0 ? 'up ' : 'down ') + fmt.n(Math.abs(d), 1) + ' pt'); };
      it.push([_T('和 7 天前比', 'Versus a week ago'), ivtSg(p.slope) + ' → ' + ivtSg(x.slope), _T(fmt.md(p.date) + ' 以來 7 天' + mv(d7) + '、90 天' + mv(d90) + '：' + (Math.abs(d7) > Math.abs(d90) + 1 ? '主要是近月在動。' : Math.abs(d90) > Math.abs(d7) + 1 ? '主要是遠月在動。' : '近月和遠月差不多一起動。'),
        'Since ' + fmt.md(p.date) + ', 7 days is ' + mv(d7) + ' and 90 days ' + mv(d90) + ': ' + (Math.abs(d7) > Math.abs(d90) + 1 ? 'mostly the near end moving.' : Math.abs(d90) > Math.abs(d7) + 1 ? 'mostly the far end moving.' : 'near and far moving about together.')), 'neu']);
    } else it.push([_T('歷史', 'History'), x.n + _T(' 天', x.n === 1 ? ' day' : ' days'),_T('Deribit 沒有免費的歷史曲線，本站每天收盤後存一條（目前 ' + x.n + ' 條）：滿 7 天後疊上 7 天前的曲線，滿 30 天後畫出斜率走勢。', 'Deribit offers no free history of the curve, so the site saves one after each daily close (' + x.n + ' so far): the curve from a week ago appears after 7 days, the slope history after 30.'), 'neu']);
    return it;
  }
  function ivtPanel() {
    var x = ivtX(); if (!x || !x.curve || !x.t) return '';
    var t = x.t, p = x.prev7 || {}, pt = p.t || {}, K = IVT_K[x.state] || IVT_K.flat, nh = (x.rows || []).filter(function (r) { return r[2] != null; }).length;
    var lg = [[_T('今天', 'Today'), 'var(--s4)']].concat(x.prev7 ? [[_T('7 天前', 'A week ago'), 'var(--ink-2)', 'dash']] : [], x.prev30 ? [[_T('30 天前', '30 days ago'), 'var(--ink-3)', 'dash']] : [], x.state === 'inv' ? [[_T('近月高於 90 天', 'Near term above 90 days'), 'var(--warn)', 'box']] : []);
    return panel('span-12', _T('隱含波動率期限結構', 'Implied volatility term structure'), _T('Deribit 標記隱含波動 · 價平 · 快照 ' + x.ts + ' UTC', 'Deribit mark IV · at the money · snapshot ' + x.ts + ' UTC'),
      '<div class="cf-hero">' + oxCard('var(--s4)', _T('近月 7 天', 'Near: 7 days'), fmt.n(t[7], 1) + '%', _T('30 天 ', '30 days ') + fmt.n(t[30], 1) + '%', ivtDl(t[7], pt[7])) +
        oxCard('var(--s4)', _T('遠月 90 天', 'Far: 90 days'), fmt.n(t[90], 1) + '%', _T('180 天 ', '180 days ') + fmt.n(t[180], 1) + '%', ivtDl(t[90], pt[90])) +
        oxCard(x.state === 'inv' ? 'var(--warn)' : 'var(--ink-2)', _T('7 天 − 90 天', '7d − 90d'), ivtSg(x.slope) + _T(' 點', ' pt'), _T(K[1], K[3]), ivtDl(x.slope, p.slope)) + '</div>' +
      interpHtml(ivtSay()) + legend(lg) + '<div class="chart cf-chart" id="c-ivt"></div>' + (nh >= 30 ? '<div class="chart cf-chart" id="c-ivts"></div>' : '') +
      '<p class="note">' + _T('每個到期日取遠期價兩側最近的價外選擇權，用 Deribit 的標記隱含波動內插出價平（ATM）的隱含波動；7／30／90／180 天是固定期限，用總變異數內插。排除 3 天內到期（週末和快到期時失真）。隱含波動是從選擇權價格反推的預期波動幅度，不分漲跌。Deribit 沒有免費的歷史曲線，本站從 2026/11/07 起每天存一條。只作讀值。',
        'For each expiry, the at-the-money implied volatility is interpolated from Deribit mark IVs of the nearest out-of-the-money options on either side of the forward; 7/30/90/180 days are constant maturities interpolated in total variance. Expiries within 3 days are left out (weekends and the last days before expiry distort them). Implied volatility is the expected size of moves backed out of option prices, not their direction. Deribit offers no free history of the curve, so the site has saved one daily since 2026/11/07. Reading only.') + '</p>', '', 'ivt');
  }
  function drawIvt(el) {
    var x = ivtX(); if (!x || !el) return;
    var sq = Math.sqrt, ser = function (cv) { return (cv || []).map(function (q) { return [sq(q[0]), q[1]]; }); };   // 橫軸用天數的平方根：近月不擠在一起
    var S = [{ name: _T('今天', 'Today'), data: ser(x.curve), color: 'var(--s4)', area: true, w: 2, end: false }];
    if (x.prev7) S.push({ name: _T('7 天前', 'A week ago'), data: ser(x.prev7.curve), color: 'var(--ink-2)', dash: '5 4', w: 1.4, end: false });
    if (x.prev30) S.push({ name: _T('30 天前', '30 days ago'), data: ser(x.prev30.curve), color: 'var(--ink-3)', dash: '2 3', w: 1.3, end: false });
    var all = [], xm = 0; S.forEach(function (s) { s.data.forEach(function (q) { all.push(q[1]); xm = Math.max(xm, q[0]); }); });
    var xt = [[7, _T('7 天', '7d')], [30, _T('30 天', '30d')], [90, _T('90 天', '90d')], [180, _T('180 天', '180d')], [365, _T('1 年', '1y')]].filter(function (q) { return sq(q[0]) <= xm; }).map(function (q) { return [sq(q[0]), q[1]]; });
    var mk = [7, 90].filter(function (k) { return x.t[k] != null; }).map(function (k) { return { x: sq(k), y: x.t[k], label: _T(k + ' 天 ', k + 'd ') + fmt.n(x.t[k], 1) + '%', color: 'var(--s4)' }; });
    var vb = [];
    if (x.state === 'inv') { var hi = x.curve.filter(function (q) { return q[0] < 90 && q[1] > x.t[90]; }); if (hi.length) vb.push({ x0: sq(x.curve[0][0]), x1: sq(hi[hi.length - 1][0]), color: 'var(--warn-dim)' }); }
    lineChart(el, { xType: 'num', h: el.clientWidth < 520 ? 220 : 270, series: S, xticks: xt, marks: mk, vbands: vb,
      y0: Math.floor(Math.min.apply(null, all) - 4), y1: Math.ceil(Math.max.apply(null, all) + 2),   // 留一點空間，1–2 點的差別不要被放大成懸崖
      xTipFmt: function (v) { return _T(Math.round(v * v) + ' 天後到期', Math.round(v * v) + ' days to expiry'); }, yFmt: function (v) { return v.toFixed(0) + '%'; }, tipFmt: function (v) { return v.toFixed(1) + '%'; },
      aria: _T('各到期日的價平隱含波動', 'At-the-money implied volatility by expiry') });
  }
  function drawIvtS(el) {
    var x = ivtX(); if (!x || !el) return;
    var rows = x.rows.filter(function (r) { return r[2] != null; });
    oxPane(el, { rows: rows, rng: 365, zero: true, fmt: function (v) { return fmt.n(v, 0); },
      label: _T('7 天減 90 天（點）：正＝倒掛', '7 days minus 90 days (pt): positive = inverted'), aria: _T('BTC 價格與期限結構斜率', 'BTC price and term-structure slope'),
      zones: [{ y0: 1, y1: 1e3, col: 'var(--warn)', op: 0.1 }],   // 倒掛區（≥ 1 點）淡底；日刊的 --warn 和 --s4 同色，所以線不分正負上色
      lines: [{ i: 2, col: 'var(--s4)', area: true, w: 1.8, name: _T('7 天 − 90 天', '7d − 90d'), tfmt: function (v) { return ivtSg(v) + _T(' 點', ' pt'); } }],
      now: { i: 2, col: 'var(--s4)', lab: ivtSg(x.slope) } });
  }

  /* 2026-11-08 指標擴充：月度報酬熱力表（2013 年起，每月最後一天收盤；本月到最新收盤為止）。只描述過去，不是預測 */
  var MON_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function monX() { return (D.price || {}).monthly || null; }
  function monSay() {
    var x = monX(); if (!x || x.mtd == null) return [];
    var c = x.cur || {}, m = c.m, it = [], y1 = +x.date.slice(0, 4) - 1;
    it.push([_T('現在', 'Now'), fmt.pct(x.mtd, 1), _T(m + ' 月至今 ' + fmt.pct(x.mtd, 1) + '（從上月底收盤 ' + fmt.usd(x.base) + ' 到 ' + fmt.md(x.date) + '），今年至今 ' + fmt.pct(x.ytd, 1) + '。月底前還會變。',
      MON_EN[m - 1] + ' so far ' + fmt.pct(x.mtd, 1) + ' (from the ' + fmt.usd(x.base) + ' close at last month-end to ' + fmt.md(x.date) + '), year to date ' + fmt.pct(x.ytd, 1) + '. It will change before the month ends.'), 'neu']);   // 月中的漲跌只是讀數，不標偏多偏空
    if (c.n) it.push([_T('過去的 ' + m + ' 月', 'Past ' + MON_EN[m - 1] + 's'), c.up + '/' + c.n,
      _T(x.since + '–' + y1 + ' 年的 ' + c.n + ' 次 ' + m + ' 月，上漲 ' + c.up + ' 次、中位數 ' + fmt.pct(c.med, 1) + '；最好 ' + c.best_y + ' 年 ' + fmt.pct(c.best, 0) + '，最差 ' + c.worst_y + ' 年 ' + fmt.pct(c.worst, 0) + '。只有 ' + c.n + ' 個樣本，只描述過去，不代表今年會照走。',
        'Of ' + c.n + ' ' + MON_EN[m - 1] + 's from ' + x.since + ' to ' + y1 + ', ' + c.up + ' rose, median ' + fmt.pct(c.med, 1) + '; best ' + c.best_y + ' ' + fmt.pct(c.best, 0) + ', worst ' + c.worst_y + ' ' + fmt.pct(c.worst, 0) + '. Only ' + c.n + ' cases: this describes the past, not what this year will do.'), 'neu']);
    return it;
  }
  function monPanel() {
    var x = monX(); if (!x || !x.rows || x.mtd == null) return '';
    var c = x.cur || {}, m = c.m;
    return panel('span-12', _T('月度報酬熱力表', 'Monthly returns heatmap'), _T('每月最後一天收盤 · ' + x.since + ' 年起 · 到 ' + fmt.md(x.date), 'Month-end closes · since ' + x.since + ' · to ' + fmt.md(x.date)),
      '<div class="cf-hero">' + oxCard(x.mtd >= 0 ? 'var(--up)' : 'var(--down)', _T(m + ' 月至今', MON_EN[m - 1] + ' so far'), fmt.pct(x.mtd, 1), _T('從上月底 ' + fmt.usd(x.base) + ' 算起', 'from ' + fmt.usd(x.base) + ' at last month-end')) +
        oxCard('var(--ink-2)', _T('過去的 ' + m + ' 月', 'Past ' + MON_EN[m - 1] + 's'), c.up + ' / ' + c.n, _T('次上漲 · 中位數 ', 'rose · median ') + fmt.pct(c.med, 1)) +
        oxCard(x.ytd >= 0 ? 'var(--up)' : 'var(--down)', _T('今年至今', 'Year to date'), fmt.pct(x.ytd, 1), _T(x.date.slice(0, 4) + ' 年', x.date.slice(0, 4))) + '</div>' +
      interpHtml(monSay()) + '<div class="chart cf-chart" id="c-mon"></div><p class="note">' + _T('每格是上個月最後一天收盤到這個月最後一天收盤的漲跌（%，四捨五入到整數）；綠漲紅跌，顏色越深幅度越大（月份 ±30% 以上同色、全年 ±100% 以上同色）。框起來的是本月，到最新收盤為止。最下面兩列是各月的中位數和上漲比例，' + x.since + ' 年起、不含本月。窄螢幕只畫近 8 年、不畫全年欄（統計仍用全部年份）。每個月只有十幾個樣本，只作讀值，不是預測。',
        'Each cell is the change from the last close of the previous month to the last close of the month (%, rounded); green up, red down, darker for bigger moves (months saturate at ±30%, years at ±100%). The outlined cell is this month, up to the latest close. The bottom two rows are each month’s median and share of up months since ' + x.since + ', excluding this month. Narrow screens show the last 8 years without the yearly column (the stats still use every year). Each month has only a dozen or so cases. Reading only, not a forecast.') + '</p>', '', 'mon');
  }
  function drawMon(el) {
    var x = monX(); if (!x || !el) return;
    var W = Math.max(280, el.clientWidth), sm = W < 520, rows = sm ? x.rows.slice(-8) : x.rows, yc = !sm, nc = 12 + (yc ? 1 : 0);
    var lab = [_T(sm ? '中位' : '中位數', sm ? 'Med' : 'Median'), _T(sm ? '上漲' : '上漲比例', sm ? 'Up' : 'Up share')];
    var mh = MON_EN.map(function (e, j) { return _T(sm ? String(j + 1) : (j + 1) + ' 月', e); });
    var ML = Math.ceil(Math.max(lblW('2026'), lblW(lab[0]), lblW(lab[1]))) + 10, MR = 2, MT = 20, ch = sm ? 22 : 24, sep = 12, cw = (W - ML - MR) / nc;
    var cy = +x.month.slice(0, 4), cm = +x.month.slice(5), ys = MT + rows.length * ch + sep, H = ys + 2 * ch + 4, fs = sm ? 10 : 11, s = '';
    var sgn = function (v) { var r = Math.round(v); return (r > 0 ? '+' : r < 0 ? '−' : '') + fmt.n(Math.abs(r), 0); };
    function cell(cx, y, v, sc, txt, ttl, now) {   // v：決定顏色的數字（正綠負紅），sc：滿色的幅度
      var op = (0.08 + 0.5 * Math.min(1, Math.abs(v) / sc)).toFixed(2), w = cw - 2, h = ch - 2;
      return '<g><title>' + esc(ttl) + '</title><rect x="' + (cx + 1).toFixed(1) + '" y="' + (y + 1) + '" width="' + w.toFixed(1) + '" height="' + h + '" rx="3" fill="' + (v >= 0 ? 'var(--up)' : 'var(--down)') + '" fill-opacity="' + op + '"/>' +
        '<text x="' + (cx + cw / 2).toFixed(1) + '" y="' + (y + ch / 2 + fs * 0.36 + 1).toFixed(1) + '" text-anchor="middle" style="fill:var(--ink);font-size:' + fs + 'px;font-variant-numeric:tabular-nums">' + esc(txt) + '</text>' +
        (now ? '<rect x="' + (cx + 1).toFixed(1) + '" y="' + (y + 1) + '" width="' + w.toFixed(1) + '" height="' + h + '" rx="3" fill="none" stroke="var(--ink)" stroke-width="1.6"/><circle class="cf-pulse" cx="' + (cx + cw - 5).toFixed(1) + '" cy="' + (y + 5) + '" r="2.6" fill="' + (v >= 0 ? 'var(--up)' : 'var(--down)') + '"/>' : '') + '</g>';
    }
    mh.forEach(function (t, j) { s += axText(ML + (j + 0.5) * cw, MT - 7, t, 'middle'); });
    if (yc) s += axText(ML + 12.5 * cw, MT - 7, _T('全年', 'Year'), 'middle');
    rows.forEach(function (r, i) {
      var y = MT + i * ch; s += axText(ML - 8, y + ch / 2 + 4, String(r[0]), 'end');
      r[1].forEach(function (v, j) { if (v == null) return; var now = r[0] === cy && j + 1 === cm; s += cell(ML + j * cw, y, v, 30, sgn(v), _T(r[0] + ' 年 ' + (j + 1) + ' 月' + (now ? '（至今）' : '') + '：', MON_EN[j] + ' ' + r[0] + (now ? ' (so far)' : '') + ': ') + fmt.pct(v, 1), now); });
      if (yc && r[2] != null) s += cell(ML + 12 * cw, y, r[2], 100, sgn(r[2]), _T(r[0] + ' 年全年' + (r[0] === cy ? '（至今）' : '') + '：', r[0] + (r[0] === cy ? ' so far' : ' full year') + ': ') + fmt.pct(r[2], 1));
    });
    s += '<line class="gl" x1="' + ML + '" x2="' + (W - MR) + '" y1="' + (ys - sep / 2) + '" y2="' + (ys - sep / 2) + '"/>' + axText(ML - 8, ys + ch / 2 + 4, lab[0], 'end') + axText(ML - 8, ys + ch * 1.5 + 4, lab[1], 'end');
    x.stats.concat(yc ? [x.ystat] : []).forEach(function (st, j) {
      if (!st || !st.n) return; var nm = j < 12 ? _T((j + 1) + ' 月', MON_EN[j]) : _T('全年', 'Full year'), sh = st.up / st.n * 100;
      s += cell(ML + j * cw, ys, st.med, j < 12 ? 30 : 100, sgn(st.med), _T(nm + '中位數 ' + fmt.pct(st.med, 1) + '（' + st.n + ' 次）', nm + ' median ' + fmt.pct(st.med, 1) + ' (' + st.n + ' cases)')) +
        cell(ML + j * cw, ys + ch, sh - 50, 40, Math.round(sh) + '%', _T(nm + '上漲 ' + st.up + ' / ' + st.n + ' 次', nm + ' rose ' + st.up + ' of ' + st.n));
    });
    el.innerHTML = svgEl(W, H, s, _T('每月漲跌熱力表', 'Monthly returns heatmap'));
  }

  /* 衍生品版 */
  function dvInterp() {
    var dv = D.deriv, d = dv.deriv || {}, r = dv.rr25 || {}, o = dv.options || {}, c = D.price.bar.c, it = [], dvol = dv.dvol || {}, x = (dv.samesource || {}).iv_minus_rv30;
    var big = (o.expiries || []).slice().sort(function (a, b) { return b.oi - a.oi; })[0];
    if (dvol.value != null) it.push(['DVOL', fmt.n(dvol.value, 1), _t('一年第 ') + fmt.n(dvol.pct_1y, 0) + _t(' 百分位：') + band(dvol.pct_1y, [20, 50, 80], [_t('在一年低檔，選擇權市場預期平靜，買保護很便宜；長時間低波動之後常接大波動，但不指方向。'), _t('偏低，市場預期平靜。'), _t('偏高，市場預期波動放大。'), _t('在一年高檔，市場緊張或有大事件，買保護很貴。')]), dvol.pct_1y >= 80 ? 'warn' : 'neu']);
    var k5 = concNow(); if (k5) it.push([_T('籌碼集中度 ±5%', 'Supply within ±5%'), fmt.n(k5.pct, 1) + '%', concSay(k5, dvol), 'neu']);
    if (x != null) it.push(['IV − RV30', fmt.n(x, 2), Math.abs(x) < 3 ? _t('隱含波動和實際波動相差不到 3 點：選擇權定價大致公允，沒有恐慌溢價。') : x < 0 ? _t('隱含波動比實際低 ') + fmt.n(-x, 1) + _t(' 點：選擇權相對便宜，市場可能低估了波動。') : _t('隱含波動比實際高 ') + fmt.n(x, 1) + _t(' 點：市場在為未來波動付溢價（避險需求或事件前）。'), 'neu']);
    var fa = fundNow(); if (fa != null) it.push([_t('永續資金費率'), fmt.pct(fa, 1), fundVenues() + band(fa, [0, 10, 20, 40], [_t('低於 0：空頭付費給多頭，空單擁擠，容易出現軋空'), _t('0–10%：中性，多頭槓桿不擁擠'), _t('10–20%：偏熱，多頭願意付較高成本'), _t('20–40%：槓桿過熱，回檔時容易連環爆倉'), _t('40% 以上：極端過熱')]) + _t('；期貨基差中位 ') + fmt.n(d.basis_median, 1) + _t('%。'), fa < 0 ? 'pos' : fa < 10 ? 'neu' : fa < 20 ? 'warn' : 'neg']);
    if (r.rr != null) it.push([_t('25Δ 風險逆轉'), fmt.n(r.rr, 2), r.rr > 2 ? _t('買權比賣權貴 ') + fmt.n(r.rr, 1) + _t(' 點：選擇權市場偏向押漲。') : r.rr < -2 ? _t('賣權比買權貴 ') + fmt.n(-r.rr, 1) + _t(' 點：市場在買下跌保護，偏防守。') : _t('接近 0：押漲和押跌的需求大致平衡。'), r.rr > 2 ? 'pos' : r.rr < -2 ? 'neg' : 'neu']);
    else it.push([_t('25Δ 風險逆轉'), '—', _t('本日沒有符合條件（20–45 天到期）的合約可計算。'), 'neu']);
    var pcr = (D.deriv || {}).pcr;   // 2026-11-09 看跌／看漲比：Deribit 沒有歷史，從 11/9 起每天累積（coc_cache/opt_daily.json）
    if (pcr && pcr.oi_pcr != null) it.push([_T('看跌／看漲比', 'Put/call ratio'), fmt.n(pcr.oi_pcr, 2),
      _T('Deribit 全部到期：看跌未平倉是看漲的 ' + fmt.n(pcr.oi_pcr, 2) + ' 倍（24 小時成交 ' + fmt.n(pcr.vol_pcr, 2) + ' 倍）。大於 1＝買看跌（避險或看空）的部位比看漲多；' + (pcr.oi_pcr >= 1 ? '現在偏防守。' : pcr.oi_pcr <= 0.6 ? '現在看漲部位明顯較多。' : '現在看漲部位較多，但不極端。') + (pcr.n < 60 ? '從 ' + ymdS(pcr.first) + ' 開始每天累積，滿幾個月後再畫歷史圖。' : ''),
        'Deribit, all expiries: put open interest is ' + fmt.n(pcr.oi_pcr, 2) + '× call open interest (24h volume ' + fmt.n(pcr.vol_pcr, 2) + '×). Above 1 means more put (hedging or bearish) positions than calls; ' + (pcr.oi_pcr >= 1 ? 'positioning is defensive now.' : pcr.oi_pcr <= 0.6 ? 'calls clearly dominate now.' : 'calls lead, but not to an extreme.') + (pcr.n < 60 ? ' Collected daily since ' + ymdS(pcr.first) + '; a history chart will follow once a few months have built up.' : '')),
      pcr.oi_pcr >= 1 ? 'warn' : 'neu']);
    if (big) it.push([_t('最大到期'), big.expiry, _t('佔全部未平倉 ') + fmt.n(big.share, 0) + _t('%，賣權／買權 ') + fmt.n(big.pc, 2) + (big.pc < 0.7 ? _t('（買權明顯較多，偏多佈局）') : big.pc > 1 ? _t('（賣權較多，偏避險）') : _t('（大致平衡）')) + _t('；Max Pain ') + fmt.k(big.maxpain) + _t('，') + (big.maxpain < c ? _t('低於收盤 ') : _t('高於收盤 ')) + fmt.n(Math.abs(big.maxpain / c - 1) * 100, 0) + _t('%。到期前價格有時被拉向 Max Pain，但這個效應的證據薄弱，只作參考。'), big.pc < 0.7 ? 'pos' : big.pc > 1 ? 'neg' : 'neu']);
    return it;
  }
  function basisSay(cv) {
    if (!cv || !cv.length) return '';
    var ys = cv.map(function (p) { return p[1]; }), lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys), sl = ys[ys.length - 1] - ys[0];
    return _t('<p class="say">各期限年化 <b>') + fmt.n(lo, 1) + '–' + fmt.n(hi, 1) + _t('%</b>，') + (sl > 0.5 ? _t('遠月較高（正常的正價差）') : sl < -0.5 ? _t('近月較高，短期做多需求較強') : _t('曲線平坦')) + _t('；') + (hi > 15 ? _t('水準偏高，槓桿偏熱。') : lo < 3 ? _t('水準很低，做多需求冷淡。') : _t('水準中性（3–15% 屬常態）。')) + '</p>';
  }
  // 2026-11-04 使用者要求（Glassnode 週報的兩大到期對照）：未平倉最大的兩個到期可以切換；標題列給全部到期的買權／賣權合計
  var skSel = 0;
  function skList() { var o = (D.deriv.viz || {}).options || {}; return [o.strikes, o.strikes2].filter(Boolean); }
  function skObj() { var L = skList(); return L[Math.min(skSel, L.length - 1)] || null; }
  function skRow() { var k = skObj(); return k ? ((D.deriv.options || {}).expiries || []).filter(function (e) { return e.expiry === k.expiry; })[0] : null; }
  function skSegs() { var L = skList(); if (L.length < 2) return ''; return '<span class="seg" id="sk-segs">' + L.map(function (k, i) { return '<button aria-pressed="' + (i === skSel) + '" data-i="' + i + '">' + fmt.md(k.expiry) + '</button>'; }).join('') + '</span>'; }
  function skTotals() { var t = ((D.deriv.viz || {}).options || {}).totals, k = skObj(); return (k ? fmt.md(k.expiry) + ' · Max Pain ' + fmt.k(k.maxpain) : '') + (t ? _T(' · 全部到期：買權 ' + fmt.n(t.call_usd_b, 1) + 'B／賣權 ' + fmt.n(t.put_usd_b, 1) + 'B 美元', ' · all expiries: calls $' + fmt.n(t.call_usd_b, 1) + 'B / puts $' + fmt.n(t.put_usd_b, 1) + 'B') : ''); }
  function strikeSay(big) {
    if (!big || !big.top_calls) return '';
    var k = function (a) { return a.map(function (x) { return fmt.k(x[0]); }).join(_t('、')); };
    return _t('<p class="say">買權集中在 <b>') + k(big.top_calls) + _t('</b>，賣權保護集中在 <b>') + k(big.top_puts) + _t('</b>：大戶押注的上檔目標和下檔防線大致在這些價位。</p>');
  }

  /* 資金版 */
  function flInterp(last, s7, p7) {
    var fr = D.flows.fred || {}, nq = fr.NASDAQCOM || {}, dx = fr.DTWEXBGS || {}, rr = D.flows.dfii10 || {}, rc = D.flows.rc_liq || {}, it = [];
    if (last.musd != null) it.push([_t('最近完整日 ETF'), (last.musd >= 0 ? '+' : '') + fmt.n(last.musd, 1) + 'M', fmt.md(last.d) + (last.musd >= 0 ? _t(' 淨流入') : _t(' 淨流出')) + (Math.abs(last.musd) >= 300 ? _t('，屬大額。') : Math.abs(last.musd) < 100 ? _t('，金額不大，單日意義有限。') : _t('。')), last.musd >= 0 ? 'pos' : 'neg']);
    it.push([_t('近 7 個完整日'), (s7 >= 0 ? '+' : '') + fmt.n(s7, 0) + 'M', (s7 >= 0 ? _t('淨流入') : _t('淨流出')) + (s7 * p7 > 0 ? _t('，前 7 日也是') + (p7 >= 0 ? _t('流入，機構買盤延續。') : _t('流出，機構需求連兩週偏弱。')) : _t('，與前 7 日方向相反，還不算趨勢。')), s7 >= 0 ? 'pos' : 'neg']);
    if (nq.corr30 != null) it.push([_t('BTC–那斯達克'), fmt.n(nq.corr30, 2), nq.corr30 >= 0.5 ? _t('高度同步：BTC 目前跟美股科技股同漲同跌，美股大跌時 BTC 很難獨善其身。') : nq.corr30 >= 0.2 ? _t('有些同步，但不緊密。') : nq.corr30 > -0.2 ? _t('幾乎無關，BTC 走自己的路。') : _t('反向，少見。'), nq.corr30 >= 0.5 ? 'warn' : 'neu']);
    if (dx.corr30 != null) it.push([_t('BTC–美元'), fmt.n(dx.corr30, 2), dx.corr30 <= -0.3 ? _t('明顯反向：美元走強時 BTC 通常受壓。') : dx.corr30 >= 0.3 ? _t('同向，少見。') : _t('關係不明顯，美元不是現在的主要驅動。'), 'neu']);
    if (rr.value != null) it.push([_t('10 年期實質利率'), fmt.n(rr.value, 2) + '%', band(rr.value, [0, 1, 2], [_t('低於 0：實質利率為負，對無息資產有利'), _t('0–1%：寬鬆'), _t('1–2%：中性偏緊'), _t('2% 以上：偏緊，持有不生息資產（如 BTC）的機會成本高')]) + (rr.chg_20obs_bp >= 20 ? _t('；近 20 個交易日上升 ') + rr.chg_20obs_bp + _t('bp，緊縮壓力增加，對 BTC 不利。') : rr.chg_20obs_bp <= -20 ? _t('；近 20 個交易日下降 ') + (-rr.chg_20obs_bp) + _t('bp，壓力減輕。') : _t('；近 20 日變化不大。')), rr.chg_20obs_bp >= 20 ? 'neg' : rr.chg_20obs_bp <= -20 ? 'pos' : 'neu']);
    if (rc.chg30_pct != null) it.push([_t('實現市值 30 日'), fmt.pct(rc.chg30_pct, 2), (rc.zero_now ? _t('小於等於 0：新資金停止流入，已 ') : _t('大於 0：仍有新資金流入，已持續 ')) + rc.state_run_days + _t(' 天。只是資金背景，不是買賣訊號（見下方說明）。'), rc.zero_now ? 'neg' : 'pos']);
    return it;
  }

  /* 鏈上版 */
  function ocInterp() {
    var fl = D.chips.flow || {}, sp = fl.sth_in_profit_pct || {}, sv = fl.sth_vs_tmm || {}, ex = D.onchain.exchange || {}, mi = D.onchain.mining || {}, c = D.price.bar.c, it = [];
    if (sp.value != null) it.push([_t('短期持有者獲利比例'), fmt.n(sp.value, 1) + '%', band(sp.value, [20, 50, 90], [_t('低於 20%：短期持有者幾乎全數虧損，歷來是短線恐慌底部'), _t('20–50%：多數短期持有者虧損，停損賣壓仍在'), _t('50–90%：多數短期持有者獲利，結構健康'), _t('90% 以上：短期持有者幾乎全數獲利，短線過熱，容易出現獲利了結')]) + (sp.d7 != null && Math.abs(sp.value - sp.d7) >= 10 ? _t('；7 天前 ') + fmt.n(sp.d7, 1) + _t('%，一週內') + (sp.value < sp.d7 ? _t('下降 ') : _t('上升 ')) + fmt.n(Math.abs(sp.value - sp.d7), 0) + _t(' 個百分點。') : _t('。')), sp.value < 20 ? 'pos' : sp.value < 50 ? 'neg' : sp.value < 90 ? 'pos' : 'warn']);
    if (sv.sth_cost) { var d = (c / sv.sth_cost - 1) * 100;
      it.push([_t('短期持有者成本'), fmt.usd(sv.sth_cost), (d >= 0 ? _T('收盤高於短期持有者（持有不到 155 天）的平均成本 ' + fmt.n(d, 1) + '%：新進場的資金整體在賺錢，是多頭結構；跌回這條線時常有回本或停損賣壓。', 'Close is ' + fmt.n(d, 1) + '% above the average cost of short-term holders (held under 155 days): short-term holders are in profit overall, a bullish structure; a drop back to this line often meets break-even or stop-loss selling. ') : _T('收盤低於短期持有者的平均成本 ' + fmt.n(-d, 1) + '%：新進場的資金整體虧損，反彈到成本線附近容易遇到解套賣壓。', 'Close is ' + fmt.n(-d, 1) + '% below the average cost of short-term holders: short-term holders are underwater, and rallies toward that cost line tend to meet selling from holders getting back to even. ')) +
        (sv.tmm ? (sv.sth_cost < sv.tmm ? _t('短期成本仍低於真實市場均價（') + fmt.usd(sv.tmm) + _t('）') + (sv.last_cross_down ? _t('，自 ') + sv.last_cross_down + _t(' 下穿後還沒收復') : '') + _t('；籌碼流向框架把「短期成本上穿真實市場均價」視為多頭結構確認，現在還沒有。') : _t('短期成本已高於真實市場均價（') + fmt.usd(sv.tmm) + _t('），多頭結構確認。')) : ''), d >= 0 ? 'pos' : 'neg']); }
    if (ex.exchange_supply_chg30_pct != null) { var a = ex.exchange_supply_chg30_pct, b = ex.exchange_supply_chg90_pct;
      it.push([_t('交易所供給'), fmt.n(ex.exchange_supply_share_pct, 2) + '%', _t('30 日 ') + fmt.pct(a, 2) + (a < 0 ? _t('（幣在離開交易所，可賣的現貨變少，偏多）') : _t('（幣在流入交易所，潛在賣壓增加）')) + _t('；90 日 ') + fmt.pct(b, 2) + (a * b < 0 ? _t('，與 30 日方向相反，趨勢還不明確。') : _t('，方向一致。')) + _t('地址歸屬會事後修正，看方向不看小數。'), a < 0 && b < 0 ? 'pos' : a > 0 && b > 0 ? 'neg' : 'neu']); }
    if (mi.hash7 != null) { var be = mi.breakeven || {}, up = [], dn = [];
      Object.keys(be).forEach(function (k) { var m = k.match(/(\d+)J@([\d.]+)/), lab = m ? m[1] + _t(' J/TH（電價 $') + m[2] + _t('）') : k; (c >= be[k] ? up : dn).push(lab + ' ' + fmt.k(be[k])); });
      it.push([_t('算力'), fmt.n(mi.hash7, 0) + ' EH/s', (mi.wk_chg_pct >= 0 ? _t('週 ') + fmt.pct(mi.wk_chg_pct, 1) + _t('，礦工持續投入，沒有投降跡象') : _t('週 ') + fmt.pct(mi.wk_chg_pct, 1) + (mi.wk_chg_pct < -5 ? _t('，明顯下降，留意礦工投降（歷來接近底部）') : _t('，小幅下降'))) + _t('。') + (up.length ? _t('收盤高於 ') + up.join(_t('、')) + _t(' 的電費損益兩平價') : '') + (dn.length ? (up.length ? _t('，') : '') + _t('低於 ') + dn.join(_t('、')) + _t('（這類礦機在虧電費）') : '') + _t('。'), mi.wk_chg_pct < -5 ? 'warn' : 'neu']); }
    var hrb = hashRibRead(); if (hrb) it.push(hrb);
    if (mi.diff_next_pct != null) it.push([_t('下次難度調整'), fmt.pct(mi.diff_next_pct, 1), _t('目前平均 ') + fmt.n(mi.block_time_s / 60, 1) + _t(' 分鐘出一個塊（目標 10 分鐘），') + fmt.md(mi.retarget) + _t(' 預計') + (mi.diff_next_pct >= 0 ? _t('上調：礦工競爭加劇、成本上升。') : _t('下調：礦工壓力減輕。')), 'neu']);
    return it;
  }
  function urpdSay(u) {
    if (!u.cur_btc) return '';
    var ab = u.above_cluster, bl = u.below_cluster, r = function (x) { return fmt.k(x.range[0]) + '–' + fmt.k(x.range[1]); };
    return _t('<p class="say">現價這一格（') + r({ range: u.cur_bucket }) + _t('）堆了 <b>') + coins(u.cur_btc) + _t('</b>（') + fmt.n(u.cur_pct, 1) + _t('%）。') +
      (ab ? _t('上方最近的大堆在 <b>') + r(ab) + _t('</b>（') + coins(ab.btc) + _t('）：價格回到那裡時，在那裡買的人剛好回本，常出現解套賣壓；站穩之後則轉為支撐。') : '') +
      (bl ? _t('下方最近的大堆在 <b>') + r(bl) + _t('</b>（') + coins(bl.btc) + _t('），是第一道籌碼支撐。') : '') + '</p>';
  }

  /* 掛單簿 */
  function bkInterp(o) {
    var t = o.totals || {}, w = o.walls || {}, r = t.wide_bid / t.wide_ask, it = [];
    if (isFinite(r)) it.push([_t('買賣比'), fmt.n(r, 2), band(r, [0.8, 1.2], [_t('低於 0.8：上方賣單明顯比下方買單厚，上漲阻力較大。'), _t('0.8–1.2：上下掛單大致平衡。'), _t('高於 1.2：下方承接明顯較厚，下跌有緩衝。')]), r < 0.8 ? 'neg' : r > 1.2 ? 'pos' : 'neu']);
    var a = (w.ask || [])[0], b = (w.bid || [])[0], c = o.mid;
    var wl = function (x, side) {   // 牆是每 1,000 美元一格；現價落在格內就說「就在現價這一格」
      var lo = x[0], hi = x[0] + 1000, inside = c >= lo && c < hi, d = side === 'a' ? (lo / c - 1) * 100 : (1 - hi / c) * 100;
      return [fmt.k(lo) + '–' + fmt.k(hi), _T(venue(x[2]) + ' 在這一格掛了 $' + fmt.n(x[1], 1) + 'M，' + (inside ? '就在現價這一格' : '距中間價約 ' + fmt.n(Math.abs(d), 1) + '%') + (side === 'a' ? '：價格接近時可能先被擋住；但掛單隨時可撤，假牆很常見。' : '：可能是下檔第一道承接，同樣可以隨時撤。'),
        venue(x[2]) + ' has $' + fmt.n(x[1], 1) + 'M in this bucket, ' + (inside ? 'right at the current price' : 'about ' + fmt.n(Math.abs(d), 1) + '% from mid') + (side === 'a' ? ': price may stall as it gets close — but orders can be pulled at any time and fake walls are common.' : ': possibly the first support below — also cancellable at any time.'))];
    };
    if (a) { var wa = wl(a, 'a'); it.push([_t('最大賣牆'), wa[0], wa[1], 'neu']); }
    if (b) { var wb = wl(b, 'b'); it.push([_t('最大買牆'), wb[0], wb[1], 'neu']); }
    return it;
  }

  /* ---------------- 短週期與鯨魚（2026-10-12 使用者要求） ----------------
     短週期：收盤價 15% 反轉才算新的一段（collect.py G1c）。鯨魚：Bitview 依地址餘額分層的持幣量（G1d，2026-11-04 起）。只作讀值，不連動任何規則。 */
  function cK(x, signed) {   // 顆數簡寫：中文「萬」、英文「K」
    if (x == null) return '—';
    var s = signed ? (x > 0 ? '+' : x < 0 ? '−' : '') : '', a = signed ? Math.abs(x) : x;
    if (a < (LANG === 'en' ? 1e3 : 1e4)) return s + fmt.n(a, 0);   // 小於一萬（英文一千）就寫完整數字
    return s + (LANG === 'en' ? fmt.n(a / 1e3, a >= 1e5 ? 0 : 1) + 'K' : fmt.n(a / 1e4, a >= 1e6 ? 0 : 1) + '萬');
  }
  function swingPanel() {
    var sw = D.price.swing; if (!sw || !sw.current) return '';
    var c = sw.current, up = c.dir === 'up', W = D.onchain.whales || {}, co = {}, legs = (sw.legs || []).slice(-6).reverse(), med = up ? sw.up_median_pct : sw.down_median_pct, medD = up ? sw.up_median_days : sw.down_median_days, nSame = up ? sw.n_up : sw.n_down;
    (W.cohorts || []).forEach(function (x) { co[x.key] = x; });
    var dirZ = up ? '上漲段' : '下跌段', dirE = up ? 'up-leg' : 'down-leg';
    var say = '<p class="say">' + _T('目前是<b>' + dirZ + '</b>：從 ' + fmt.md(c.start) + ' 的 ' + fmt.k(c.p0) + (up ? ' 起漲 ' : ' 起跌 ') + c.days + ' 天、<b>' + fmt.pct(c.pct, 1) + '</b>（本段' + (up ? '最高 ' : '最低 ') + fmt.k(c.ext) + '，' + fmt.md(c.ext_date) + '），現在離本段' + (up ? '高點 ' : '低點 ') + fmt.pct(c.from_ext_pct, 1) + '。',
      'We are in an <b>' + dirE + '</b>: ' + c.days + ' days from the ' + fmt.md(c.start) + ' ' + (up ? 'low' : 'high') + ' of ' + fmt.k(c.p0) + ', <b>' + fmt.pct(c.pct, 1) + '</b> (leg ' + (up ? 'high ' : 'low ') + fmt.k(c.ext) + ' on ' + fmt.md(c.ext_date) + '); price is now ' + fmt.pct(c.from_ext_pct, 1) + ' from that ' + (up ? 'high' : 'low') + '.') + '</p>';
    var it = [];
    if (med != null) it.push([_T('幅度', 'Size'), fmt.pct(c.ext_pct, 1), _T('本段最大' + (up ? '漲' : '跌') + '幅 ' + fmt.pct(c.ext_pct, 1) + '，大於本輪（2022/11 起）' + nSame + ' 段' + dirZ + '中的 ' + sw.size_rank_pct + '%；中位數 ' + fmt.pct(med, 1) + '。' + (sw.size_rank_pct >= 80 ? '已是偏大的一段，延伸空間通常有限。' : sw.size_rank_pct <= 30 ? '幅度還小，屬早段。' : '屬一般大小。'),
      'The leg’s largest move so far is ' + fmt.pct(c.ext_pct, 1) + ', bigger than ' + sw.size_rank_pct + '% of the ' + nSame + ' ' + dirE + 's this cycle (since 2022/11); the median is ' + fmt.pct(med, 1) + '. ' + (sw.size_rank_pct >= 80 ? 'Already a large leg; further extension is usually limited.' : sw.size_rank_pct <= 30 ? 'Still small — early in the leg.' : 'A typical size.')), sw.size_rank_pct >= 80 ? 'warn' : 'neu']);
    if (medD != null) it.push([_T('時間', 'Duration'), c.days + _T(' 天', 'd'), _T('已走 ' + c.days + ' 天，比 ' + sw.days_rank_pct + '% 的' + dirZ + '長（中位數 ' + medD + ' 天）。' + (sw.days_rank_pct >= 70 ? (up ? '漲得慢、拉得長，量能與動能要跟上才走得遠。' : '跌得久，賣壓在時間上消化。') : sw.days_rank_pct <= 30 ? '時間還短。' : '時間屬一般。'),
      c.days + ' days so far, longer than ' + sw.days_rank_pct + '% of ' + dirE + 's (median ' + medD + ' days). ' + (sw.days_rank_pct >= 70 ? (up ? 'A slow, drawn-out rise; it needs volume and momentum to go much further.' : 'A long decline; selling is being worked off over time.') : sw.days_rank_pct <= 30 ? 'Still young.' : 'A typical length.')), 'neu']);
    var dEnd = (c.end_level / c.close - 1) * 100;
    it.push([_T('本段結束線', 'Leg-end line'), fmt.k(c.end_level), _T('收盤' + (up ? '跌到 ' : '漲到 ') + fmt.usd(c.end_level) + '（距今 ' + fmt.pct(dEnd, 1) + '）才算本段結束、轉為' + (up ? '下跌段' : '上漲段') + '；在那之前的' + (up ? '回檔' : '反彈') + '都算本段內的整理。',
      'Only a close ' + (up ? 'below ' : 'above ') + fmt.usd(c.end_level) + ' (' + fmt.pct(dEnd, 1) + ' from here) would end this leg and start a ' + (up ? 'down-leg' : 'up-leg') + '; ' + (up ? 'pullbacks' : 'bounces') + ' before that are consolidation within the leg.'), Math.abs(dEnd) < 5 ? 'warn' : up ? 'pos' : 'neg']);
    var w1 = co['1k_10k'], w2 = co['100_1k'];
    if (w1 && w2 && w1.since_leg != null && w2.since_leg != null) { var tot = w1.since_leg + w2.since_leg;
      it.push([_T('大戶在本段', 'Big holders this leg'), cK(tot, true), _T('本段以來，鯨魚（1K–10K BTC 地址）' + cK(w1.since_leg, true) + ' 顆、鯊魚（100–1K）' + cK(w2.since_leg, true) + ' 顆，合計' + (tot >= 0 ? '增持' : '減持') + '。' + (w1.since_leg * w2.since_leg < 0 ? '兩者方向相反，籌碼在大戶之間換手，不是單向進出。' : tot >= 0 ? '大戶整體在這一段' + (up ? '跟著買' : '逢低買') + '。' : '大戶整體在這一段' + (up ? '趁漲賣出' : '跟著賣') + '。'),
        'Since this leg began, whales (1K–10K BTC addresses) ' + cK(w1.since_leg, true) + ' BTC and sharks (100–1K) ' + cK(w2.since_leg, true) + ' BTC — net ' + (tot >= 0 ? 'accumulation' : 'distribution') + '. ' + (w1.since_leg * w2.since_leg < 0 ? 'They moved in opposite directions, so coins are rotating between big holders rather than flowing one way.' : tot >= 0 ? 'Big holders have been buying ' + (up ? 'into the rise.' : 'the dip.') : 'Big holders have been selling ' + (up ? 'into the rise.' : 'along with the decline.'))), tot >= 0 ? 'pos' : 'neg']); }
    var pl = (sw.legs || [])[sw.legs.length - 1];
    if (pl) it.push([_T('前一段', 'Previous leg'), fmt.pct(pl.pct, 1), _T('前一段是' + (pl.pct > 0 ? '上漲段' : '下跌段') + '：' + fmt.md(pl.start) + ' → ' + fmt.md(pl.end) + '，' + fmt.pct(pl.pct, 1) + '、' + pl.days + ' 天。', 'The previous leg was ' + (pl.pct > 0 ? 'an up-leg' : 'a down-leg') + ': ' + fmt.md(pl.start) + ' → ' + fmt.md(pl.end) + ', ' + fmt.pct(pl.pct, 1) + ' over ' + pl.days + ' days.'), 'neu']);
    var tb = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>' + _T('最近的段落', 'Recent legs') + '</th><th class="num">' + _T('幅度', 'Move') + '</th><th class="num">' + _T('天數', 'Days') + '</th></tr></thead><tbody>' + legs.map(function (g) { return '<tr><td style="white-space:nowrap">' + g.start.slice(2) + ' → ' + g.end.slice(2) + '<div class="note">' + fmt.k(g.p0) + ' → ' + fmt.k(g.p1) + '</div></td><td class="num" style="color:var(--' + (g.pct >= 0 ? 'up' : 'down') + ')">' + fmt.pct(g.pct, 1) + '</td><td class="num">' + g.days + '</td></tr>'; }).join('') + '</tbody></table></div>';
    var note = '<p class="note">' + _T('怎麼算：用每日收盤價，從高點跌 15% 或從低點漲 15% 才算換成新的一段（還沒反轉前，新高或新低都算同一段延伸）。「本輪」＝2022-11-21 低點以來已完成的段落，樣本 ' + (sw.n_up + sw.n_down) + ' 段。只描述目前走到哪裡，不預測、不連動出場規則。',
      'Method: using daily closes, a new leg starts only after a 15% drop from a high or a 15% rise from a low (until then, new highs or lows extend the same leg). “This cycle” = completed legs since the 2022-11-21 low, ' + (sw.n_up + sw.n_down) + ' legs. This describes where we are; it is not a forecast and does not drive the exit rules.') + '</p>';
    return panel('span-12', _T('短週期：目前這一段行情', 'Short cycle: the current leg'), _T('收盤價 15% 反轉 · ', '15% reversal on closes · ') + fmt.md(sw.date), say + '<div class="grid" style="margin-top:6px"><div class="span-8">' + interpHtml(it) + '</div><div class="span-4">' + tb + '</div></div>' + note);
  }

  var COH = { lt1: ['散戶 <1 BTC', 'Shrimp <1 BTC'], '1_10': ['1–10 BTC', 'Crabs 1–10 BTC'], '10_100': ['10–100 BTC', 'Fish 10–100 BTC'], '100_1k': ['鯊魚 100–1K', 'Sharks 100–1K'], '1k_10k': ['鯨魚 1K–10K', 'Whales 1K–10K'], ge10k: ['≥10K', '≥10K'] };
  function cohRead(x) {
    if (x.chg30 == null) return null;
    var p = x.pct30, up = x.chg30 > 0, flip = x.chg7 != null && x.chg7 * x.chg30 < 0 && Math.abs(x.chg7) > Math.abs(x.chg30) * 0.25;
    var lvl = p >= 80 ? _T(up ? '明顯增持' : '減持', up ? 'clear accumulation' : 'distribution') : p <= 20 ? _T(up ? '小幅增持' : '明顯減持', up ? 'slight accumulation' : 'clear distribution') : _T(up ? '小幅增持' : '小幅減持', up ? 'slight accumulation' : 'slight distribution');
    var s = _T('30 日 ' + cK(x.chg30, true) + ' 顆（' + lvl + '；30 日變化落在' + ((D.onchain.whales || {}).src === 'Bitview' ? '近 4 年' : ' 2021 年以來') + '第 ' + fmt.n(p, 0) + ' 百分位）', '30-day ' + cK(x.chg30, true) + ' BTC (' + lvl + '; the 30-day change is at the ' + ord(p) + ' percentile ' + ((D.onchain.whales || {}).src === 'Bitview' ? 'of the last 4 years' : 'since 2021') + ')') +
      (flip ? _T('，但最近 7 天轉為' + (x.chg7 > 0 ? '增持 ' : '減持 ') + cK(x.chg7, true), ', but the last 7 days flipped to ' + cK(x.chg7, true)) : '') + _T('；90 日 ' + cK(x.chg90, true) + '。', '; 90-day ' + cK(x.chg90, true) + '. ');
    if (x.key === 'ge10k') s += _T('這一層多是交易所冷錢包與 ETF 託管，增減常是錢包整理或客戶進出，不能直接當成大戶買賣。', 'This tier is mostly exchange cold wallets and ETF custodians; changes are often wallet reshuffles or client flows, not big-holder buying or selling.');
    if (x.key === 'lt1') s += _T('散戶持幣變化小、影響有限，主要看方向是否與大戶相反。', 'Retail holdings move little; what matters is whether they move opposite to big holders.');
    var big = x.key === '100_1k' || x.key === '1k_10k';
    return [s, big && !flip ? (up && p >= 60 ? 'pos' : !up && p <= 40 ? 'neg' : 'neu') : 'neu'];
  }
  var MQ560 = window.matchMedia('(max-width: 560px)');   // 手機隱藏 7d／90d 兩欄，解讀列的 colspan 跟著改
  /* 鏈上指標走勢（2026-10-14）：表格與頂部雷達每一項近 3 年，上格是 BTC 價格。只作讀值。
     2026-11-04 每個指標一個家：頂部三指標與頂部雷達的 6 張移到週期版（和它們的讀值放在一起），STH-SOPR 小圖拿掉（鏈上版已有完整的 STH-SOPR 圖） */
  var OCV = [['mvrv-zscore', 'MVRV Z', 'MVRV Z', 2], ['nupl', 'NUPL', 'NUPL', 3], ['puell-multiple', 'Puell', 'Puell', 2],
    ['asopr', 'aSOPR（7 日均）', 'aSOPR (7-day avg)', 4], ['lth-sopr', 'LTH-SOPR（7 日均）', 'LTH-SOPR (7-day avg)', 3],
    ['illiquid-supply', '非流動性供給', 'Illiquid supply', 'M'], ['highly-liquid-supply', '高流動性供給', 'Highly liquid supply', 'M'],
    ['lth-mvrv-zscore', 'LTH MVRV Z', 'LTH MVRV Z', 2], ['supply-in-profit-pct', '獲利供給 %', 'Supply in profit %', 1], ['lth-net-position-change-30d-btc', '長期持有者 30 日淨部位', 'LTH 30-day net position', 'K']];
  function ocFmt(v, f) { if (v == null) return '—'; if (f === 'M') return fmt.n(v / 1e6, 2) + 'M'; if (f === 'K') return (v > 0 ? '+' : v < 0 ? '−' : '') + fmt.n(Math.abs(v) / 1e3, 0) + 'K'; return fmt.n(v, f); }
  function ocDelta(v, f) { if (v == null) return '—'; var s = v > 0 ? '+' : v < 0 ? '−' : ''; return s + ocFmt(Math.abs(v), f === 'K' ? 'K' : f).replace(/^[+−]/, ''); }
  var OC_REF = { p80: ['四年 80 百分位（頂部區門檻）', '4-year 80th percentile (top-zone line)'], top2025: ['2025 頂部附近的極值', 'Extreme near the 2025 top'], one: ['1.0＝賣在成本', '1.0 = selling at cost'] };
  // 2026-11-05 使用者決定：主色按指標類型分（全站一致）：成本與價位＝橙 s2、獲利與情緒＝紫 s1、籌碼與供給＝青綠 s3、資金與衍生品＝金 s4（見 docs/chart-style.md）
  var OC_KIND = { 'illiquid-supply': 's3', 'highly-liquid-supply': 's3', 'supply-in-profit-pct': 's3', 'lth-net-position-change-30d-btc': 's3', 'puell-multiple': 's4' };
  function ocCol(k) { return 'var(--' + (OC_KIND[k] || 's1') + ')'; }
  var OC_TOP = ['mvrv-zscore', 'nupl', 'puell-multiple', 'lth-mvrv-zscore', 'supply-in-profit-pct', 'lth-net-position-change-30d-btc'];   // 週期版
  function ocKeys(top) { return OCV.filter(function (o) { return (OC_TOP.indexOf(o[0]) >= 0) === !!top; }); }
  function ocPanel(top) {
    var V_ = (D.onchain || {}).viz; if (!V_ || !(D.cycle.stage || {}).viz) return '';
    // 2026-11-04 自我檢查：手機上鏈上版約 22 個螢幕高，這 11 張小圖佔了一半。手機只先顯示前 3 張與有「異動」的，其餘收在按鈕後面（桌面照舊全部顯示）
    var sigd = {}, nShow = 0, nMore = 0; ((D.signals || {}).items || []).forEach(function (x) { if (x.chart) sigd[x.chart] = 1; });
    var cells = ocKeys(top).filter(function (o) { return V_[o[0]]; }).map(function (o) {
      var more = nShow >= 3 && !sigd['oc-' + o[0]]; if (more) nMore++; else nShow++;
      var x = V_[o[0]], r = x.ref, f = o[3];
      var say = _T('現在 ', 'Now ') + ocFmt(x.last, f) + _T('（' + fmt.md(x.date) + '）· 30 日 ', ' (' + fmt.md(x.date) + ') · 30d ') + ocDelta(x.chg30, f) + _T(' · 90 日 ', ' · 90d ') + ocDelta(x.chg90, f) +
        (r ? _T(' · ' + OC_REF[r.kind][0] + ' ', ' · ' + OC_REF[r.kind][1] + ' ') + ocFmt(r.y, f) : '');
      return '<div class="evc' + (more ? ' more' : '') + '"><div class="panel-h"><h3>' + esc(_T(o[1], o[2])) + '</h3></div><p class="note">' + esc(say) + '</p><div class="chart" id="c-oc-' + o[0] + '"></div></div>';
    }).join('') + (nMore ? '<button type="button" class="oc-more">' + _T('展開其餘 ' + nMore + ' 張圖', 'Show ' + nMore + ' more charts') + '</button>' : '');
    if (!cells) return '';
    return panel('span-12', top ? _T('頂部三指標與頂部雷達走勢', 'Top-3 indicators and top radar over time') : _T('鏈上指標走勢', 'On-chain indicators over time'), _T('近 3 年 · 上格是 BTC 價格', '3 years · top pane is the BTC price'),
      legend([[_T('獲利與情緒', 'Profit & sentiment'), 'var(--s1)'], [_T('籌碼與供給', 'Supply'), 'var(--s3)'], [_T('礦工收入', 'Miner revenue'), 'var(--s4)']].filter(function (k) { return ocKeys(top).some(function (o) { return V_[o[0]] && ocCol(o[0]) === k[1]; }); }).concat([[_T('參考線', 'Reference line'), 'var(--down)'], [_T('BTC 價格（上格）', 'BTC price (top pane)'), 'var(--ink-3)']])) + '<div class="evcharts fold">' + cells + '</div>');
  }
  function drawOc(top) {
    var V_ = (D.onchain || {}).viz, px = ((D.cycle.stage || {}).viz || {}).px || []; if (!V_) return;
    ocKeys(top).forEach(function (o) {
      var x = V_[o[0]], el = $('#c-oc-' + o[0]); if (!x || !el) return;
      var f = o[3], x0 = x.rows.length ? x.rows[0][0] : 0, yf = function (v) { return f === 'M' ? (v / 1e6).toFixed(1) + 'M' : f === 'K' ? Math.round(v / 1e3) + 'K' : v.toFixed(typeof f === 'number' ? Math.min(f, 2) : 2); };
      mount(el, function (e) { lineChart(e, { h: 180, log2: true, robust: /sopr/.test(o[0]) ? 0.01 : 0, series: [{ name: _T('BTC 價格', 'BTC price'), data: px.filter(function (r) { return r[0] >= x0; }), color: 'var(--ink-3)', w: 1.1, end: false, y2: true, fmt: fmt.usd }, { name: _T(o[1], o[2]), data: x.rows, color: ocCol(o[0]), w: 1.7 }],
        refs: x.ref ? [{ y: x.ref.y, color: 'var(--down)' }] : [], yFmt: yf, tipFmt: function (v) { return ocFmt(v, f); }, aria: _T(o[1], o[2]) }); });
    });
  }

  /* 讀圖（2026-10-14）：每張圖下方「現在」一句（依當日資料自動產生）＋「怎麼讀這張圖」三點（圖上／怎麼看／小心），中英雙語。
     由 renderAll 在各版畫完後插到圖的後面，不改各版原本的字串。只作讀值、非投資建議 */
  var RD = (function () {
    var c = function () { return D.price.bar.c; }, ymd = function (d) { return d ? d.replace(/-/g, '/') : '—'; }, pc = function (a, b) { return fmt.pct((a / b - 1) * 100, 1); };
    var h = function (a, b, cz, ce, dz, de) { return [[a, b], [cz, ce], [dz, de]]; };
    return {
      'ov-px': { h: h('近一年每日收盤與 200 日均線（橫線）。', 'Daily closes for the past year and the 200-day average (horizontal line).', '收盤在 200 日均線之上、均線往上＝長期趨勢向上；出場框架的避險線就是這條（連 5 日收在其下才動）。', 'Closes above a rising 200-day average mean the long-term trend is up; it is also the exit framework\'s hedge line (5 straight closes below it).', '盤中刺破不算，只看收盤與連續天數。', 'Intraday breaks don\'t count; only closes and consecutive days do.'),
        now: function () { var t0 = dnOf(D.meta.bar_date) - 365, H = (D.price.history || []).filter(function (r) { return r[0] >= t0; }), v = H.map(function (r) { return r[1]; }), hi = Math.max.apply(null, v), lo = Math.min.apply(null, v), s = D.price.ma.sma200; return _T('收盤比 200 日均線 ' + pc(c(), s) + '；近一年高 ' + fmt.usd(hi) + '、低 ' + fmt.usd(lo) + '，現在位於這段區間的 ' + fmt.n((c() - lo) / (hi - lo) * 100, 0) + '%。', 'Close vs the 200-day average: ' + pc(c(), s) + '. One-year high ' + fmt.usd(hi) + ', low ' + fmt.usd(lo) + '; price sits at ' + fmt.n((c() - lo) / (hi - lo) * 100, 0) + '% of that range.'); } },
      'long': { h: h('全部歷史收盤（對數刻度）；橘點是週期頂、藍點是週期底，虛直線是減半日。', 'All closes on a log scale; orange dots are cycle tops, blue dots cycle bottoms, dashed verticals the halvings.', '對數刻度下同樣高度＝同樣的漲跌比例；過去幾輪頂部大約在減半後 12–18 個月，底部約在頂部後一年。', 'On a log scale equal heights are equal percentage moves; past tops came roughly 12–18 months after a halving, and bottoms about a year after the top.', '只有 3–4 輪樣本，時間規律不保證重演。', 'Only 3–4 cycles of history; the timing pattern may not repeat.'),
        now: function () { var t = D.cycle.tops[D.cycle.tops.length - 1], hv = D.cycle.halvings[D.cycle.halvings.length - 1], days = dnOf(D.meta.bar_date) - dnOf(hv); return _T('比上一輪頂（' + ymd(t[0]) + ' ' + fmt.usd(t[1]) + '）' + pc(c(), t[1]) + '；距上次減半 ' + days + ' 天。', 'vs the last top (' + ymd(t[0]) + ', ' + fmt.usd(t[1]) + '): ' + pc(c(), t[1]) + '; ' + days + ' days since the last halving.'); } },
      'vol': { h: h('DVOL＝Deribit 選擇權隱含的未來 30 天年化波動；RV30＝過去 30 天實際波動。', 'DVOL = implied 30-day annualized volatility from Deribit options; RV30 = realized volatility over the past 30 days.', 'DVOL 高於 RV30＝市場花錢買保護、預期波動變大；兩者都在低檔＝波動壓縮，常在大行情之前。', 'DVOL above RV30 means traders pay up for protection and expect bigger moves; both low means compressed volatility, which often precedes a big move.', '波動率不告訴你方向。', 'Volatility says nothing about direction.'),
        now: function () { var dv = D.deriv.dvol || {}, rv = (D.deriv.samesource || {}).rv30; return _T('DVOL ' + fmt.n(dv.value, 1) + '（一年百分位 ' + fmt.n(dv.pct_1y, 0) + '）、RV30 ' + fmt.n(rv, 1) + '：' + (dv.value > rv ? '隱含高於實際，市場在預期波動放大。' : '隱含不高於實際，選擇權不貴、市場不預期大波動。'), 'DVOL ' + fmt.n(dv.value, 1) + ' (1-year percentile ' + fmt.n(dv.pct_1y, 0) + '), RV30 ' + fmt.n(rv, 1) + ': ' + (dv.value > rv ? 'implied above realized; the market expects bigger moves.' : 'implied not above realized; options are cheap and no big move is priced in.')); } },
      'conc': { h: h('上格是 BTC 價格，右緣是當天的籌碼分布（每 2,000 美元一格，紫＝長期持有者、橙＝短期持有者，越長越多），青綠色帶是現價 ±5%。下格是集中度：最後一次移動在當天收盤 ±5% 內的幣佔全部供給的比例（Bitview，2018 起），黃虛線以上是歷史前 10%，黃圈是每次首次衝上前 10%。', 'Top: BTC price, with the day\'s supply distribution on the right edge ($2,000 buckets; purple long-term holders, orange short-term holders; longer = more) and the ±5% band in teal. Bottom: concentration, the share of supply last moved within ±5% of that day\'s close (Bitview, since 2018); above the yellow dashed line is the historical top 10%, yellow rings mark each first entry.', '比例上升＝越多人的成本擠在現價附近；價格離開這一帶時，買在這裡的人容易一起停損或一起解套，波動常放大。', 'A rising share means more holders\' cost basis is crowded near price; when price leaves the band they tend to cut or sell at break-even together, and volatility often expands.', '只說波動可能變大，不說方向。URPD 以 2,000 美元一格估算、晚約 1 天；本站從 2026-10-01 才有紀錄，樣本太短，不設門檻。', 'It flags bigger moves, not direction. URPD uses $2,000 buckets and lags about a day; our record starts 2026-10-01, too short to set any threshold.'),
        now: function () { var k = concNow(), a = concAgo(7); if (!k) return ''; return _T(fmt.n(k.pct, 1) + '%（URPD ' + ymd(k.urpd_date) + '，價格帶 ' + fmt.k(k.lo) + '–' + fmt.k(k.hi) + '）' + (a ? '，7 天前 ' + fmt.n(a[2], 1) + '%' : '') + '。', fmt.n(k.pct, 1) + '% (URPD ' + ymd(k.urpd_date) + ', band ' + fmt.k(k.lo) + '–' + fmt.k(k.hi) + ')' + (a ? '; ' + fmt.n(a[2], 1) + '% a week ago' : '') + '.'); } },
      'basis': { h: h('橫軸是到期天數，縱軸是期貨相對現貨的年化溢價。', 'X axis: days to expiry; Y axis: annualized futures premium over spot.', '正常是遠月高於近月；整體 >10% 代表槓桿多頭擁擠，接近 0 或近月高於遠月（倒掛）代表恐慌或去槓桿。', 'Normally longer expiries pay more; above 10% means crowded leveraged longs, near zero or inverted means fear or deleveraging.', '7 天內到期的合約雜訊大，已排除。', 'Contracts within 7 days of expiry are noisy and excluded.'),
        now: function () { var b = D.deriv.deriv || {}, cv = b.basis_curve || [], a = cv[0], z = cv[cv.length - 1], m = b.basis_median; if (!a) return ''; var lv = m > 10 ? ['偏熱', 'hot'] : m >= 5 ? ['正常', 'normal'] : ['偏冷', 'cool']; return _T('中位 ' + fmt.n(m, 2) + '%（' + lv[0] + '），近月 ' + fmt.n(a[1], 2) + '% → 最遠 ' + fmt.n(z[1], 2) + '%：' + (z[1] > a[1] + 0.3 ? '正價差。' : z[1] < a[1] - 0.3 ? '倒掛。' : '幾乎平。'), 'Median ' + fmt.n(m, 2) + '% (' + lv[1] + '), front ' + fmt.n(a[1], 2) + '% → far ' + fmt.n(z[1], 2) + '%: ' + (z[1] > a[1] + 0.3 ? 'upward sloping.' : z[1] < a[1] - 0.3 ? 'inverted.' : 'nearly flat.')); } },
      'oi': { h: h('每個到期日的買權與賣權未平倉（顆）。', 'Call and put open interest by expiry (BTC).', '未平倉最大的到期日接近時，價格常被吸向最大痛點；賣權多於買權（P/C > 1）＝避險需求高。', 'As the largest expiry nears, price often gravitates to max pain; more puts than calls (P/C > 1) means heavy hedging.', '「最大痛點磁吸」只在大到期前幾天、價格本來就靠近時才明顯。', 'The max-pain pull only shows in the last few days before a big expiry, and only when price is already near.'),
        now: function () { var e = (D.deriv.options || {}).expiries || []; if (!e.length) return ''; var b = e.reduce(function (a, x) { return x.share > a.share ? x : a; }); return _T('最大的到期是 ' + ymd(b.expiry) + '（占 ' + fmt.n(b.share, 1) + '%、P/C ' + fmt.n(b.pc, 2) + '），最大痛點 ' + fmt.usd(b.maxpain) + '，在現價 ' + pc(b.maxpain, c()) + '。', 'The largest expiry is ' + ymd(b.expiry) + ' (' + fmt.n(b.share, 1) + '% of OI, P/C ' + fmt.n(b.pc, 2) + '); max pain ' + fmt.usd(b.maxpain) + ', ' + pc(b.maxpain, c()) + ' from price.'); } },
      'strike': { h: h('最大一次到期的每個履約價上，買權與賣權未平倉。', 'Call and put open interest at each strike for the largest expiry.', '買權堆積的價位常成上方壓力或目標，賣權堆積是下方保護；最大痛點＝到期時讓買方損失最大的價位。', 'Call clusters often act as resistance or targets, put clusters as downside protection; max pain is where option buyers lose the most at expiry.', '未平倉看不出是買方還是賣方的部位。', 'Open interest doesn\'t tell you who is long or short.'),
        now: function () { var s = (((D.deriv.viz || {}).options || {}).strikes) || {}, r = s.rows || []; if (!r.length) return ''; var ca = r.reduce(function (a, x) { return x[1] > a[1] ? x : a; }), pu = r.reduce(function (a, x) { return x[2] > a[2] ? x : a; }); return _T(ymd(s.expiry) + ' 到期：買權最多在 ' + fmt.usd(ca[0]) + '、賣權最多在 ' + fmt.usd(pu[0]) + '，最大痛點 ' + fmt.usd(s.maxpain) + '（現價 ' + pc(s.maxpain, c()) + '）。', ymd(s.expiry) + ' expiry: most calls at ' + fmt.usd(ca[0]) + ', most puts at ' + fmt.usd(pu[0]) + '; max pain ' + fmt.usd(s.maxpain) + ' (' + pc(s.maxpain, c()) + ' from price).'); } },
      'book': { h: h('7 個可讀整本的交易所，±15% 內每 1,000 美元的買單與賣單。', 'Bids and asks in $1,000 buckets within ±15%, across 7 venues with full books.', '大買牆可能成支撐、大賣牆成壓力；買賣比的變化看哪一邊在退。', 'Big bid walls can act as support and ask walls as resistance; watch which side is pulling orders.', '掛單隨時可撤（假牆常見），而且只是 UTC 00:05 的快照。', 'Orders can be pulled any time (spoof walls are common), and this is only a 00:05 UTC snapshot.') },
      'etf': { h: h('美國現貨 BTC ETF 每日淨流量（百萬美元）；淡色是暫定或未完整。', 'Daily net flows into US spot BTC ETFs ($M); faded bars are provisional or incomplete.', '看連續方向與 5–7 日合計，比單日重要；連續流入代表傳統資金在買。', 'Streaks and 5–7 day totals matter more than single days; sustained inflows mean traditional money is buying.', 'The Block 晚 1–2 個交易日；單日大筆常是個別基金調倉。', 'The Block lags 1–2 trading days; single big days are often one fund rebalancing.'),
        now: function () { var e = (D.flows.etf || []).filter(function (r) { return !r.partial; }); if (!e.length) return ''; var l5 = e.slice(-5), s5 = l5.reduce(function (a, r) { return a + r.musd; }, 0), dir = e[e.length - 1].musd >= 0, n = 0; for (var i = e.length - 1; i >= 0 && (e[i].musd >= 0) === dir; i--) n++; return _T('最近 5 個完整交易日合計 ' + (s5 >= 0 ? '+' : '−') + fmt.n(Math.abs(s5), 0) + 'M，已連續 ' + n + ' 天' + (dir ? '流入' : '流出') + '（到 ' + ymd(e[e.length - 1].d) + '）。', 'Last 5 complete days: ' + (s5 >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(s5), 0) + 'M; ' + n + ' straight days of ' + (dir ? 'inflows' : 'outflows') + ' (through ' + ymd(e[e.length - 1].d) + ').'); } },
      'cd': { h: h('近 20 天日 K；橫線是 20 日均線、價值區上緣、POC（成交最密集的價位）。', 'Daily candles for 20 days; lines mark the 20-day average, the value-area top and the POC (busiest price).', '價格在價值區內＝區間整理；突破上緣並站穩＝轉強；POC 常是磁吸點與支撐壓力。', 'Inside the value area means range trading; a hold above its top means strength; the POC often acts as a magnet and as support or resistance.', '價值區由日線估算，不是逐筆成交。', 'The value area is estimated from daily bars, not tick data.'),
        now: function () { var vp = D.price.volprofile || {}, s20 = D.price.ma.sma20, x = c(), pos = x > vp.va_high_outer ? ['在價值區上方', 'above the value area'] : x >= vp.va_low ? ['在價值區內', 'inside the value area'] : ['在價值區下方', 'below the value area']; return _T('收盤 ' + fmt.usd(x) + pos[0] + '（' + fmt.k(vp.va_low) + '–' + fmt.k(vp.va_high_outer) + '），比 POC ' + pc(x, vp.poc) + '、比 20 日均線 ' + pc(x, s20) + '。', 'Close ' + fmt.usd(x) + ' is ' + pos[1] + ' (' + fmt.k(vp.va_low) + '–' + fmt.k(vp.va_high_outer) + '), ' + pc(x, vp.poc) + ' vs the POC and ' + pc(x, s20) + ' vs the 20-day average.'); } },
      'rcliq': { h: h('實現市值（每顆幣以最後一次移動的價格計的總成本）30 日變化；紅色區段是 ≤ 0 的期間。', '30-day change in realized cap (every coin valued at the price it last moved); red spans are periods at or below zero.', '> 0 代表新資金用更高的價格進場；跌到 0 以下＝資金流入停滯，多出現在熊市或深度回調。', 'Above zero means new money is coming in at higher prices; below zero means inflows have stalled, typical of bear markets or deep corrections.', '不是買賣訊號：2018、2021-06、2022-01 歸零之後仍大跌。', 'Not a trade signal: price kept falling after the 2018, 2021-06 and 2022-01 zero crossings.'),
        now: function () { var r = D.flows.rc_liq || {}, e = r.last_episode; return _T('30 日 ' + fmt.pct(r.chg30_pct, 2) + '，已連續 ' + r.state_run_days + ' 天' + (r.zero_now ? '≤ 0' : '為正') + (e ? '；上一次 ≤ 0 是 ' + ymd(e.start) + '–' + ymd(e.end) + '（' + e.days + ' 天）。' : '。'), '30-day ' + fmt.pct(r.chg30_pct, 2) + ', ' + r.state_run_days + ' days ' + (r.zero_now ? 'at or below zero' : 'positive') + (e ? '; the last stretch at or below zero was ' + ymd(e.start) + '–' + ymd(e.end) + ' (' + e.days + ' days).' : '.')); } },
      'stab': { h: h('全部美元穩定幣的流通量（十億美元）。', 'Total circulating USD stablecoins ($B).', '持續增加＝場內可用的購買力在增加，常是多頭的燃料；減少＝資金撤離。', 'Steady growth means more buying power on-chain, often fuel for rallies; shrinking means money leaving.', '很多穩定幣用在交易所與 DeFi 以外，不等於一定會買 BTC。', 'Much of it is used outside exchanges and DeFi; it won\'t necessarily buy BTC.'),
        now: function () { var s = D.flows.stables || {}; return _T(fmt.n(s.usd_b, 1) + 'B，30 日 ' + fmt.pct(s.chg30_pct, 2) + '（' + (s.chg30_usd_b >= 0 ? '+' : '−') + fmt.n(Math.abs(s.chg30_usd_b), 1) + 'B）、7 日 ' + fmt.pct(s.chg7_pct, 2) + '。', '$' + fmt.n(s.usd_b, 1) + 'B; 30 days ' + fmt.pct(s.chg30_pct, 2) + ' (' + (s.chg30_usd_b >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(s.chg30_usd_b), 1) + 'B), 7 days ' + fmt.pct(s.chg7_pct, 2) + '.'); } },
      'fng': { h: h('上格 BTC 價格，下格 alternative.me 恐懼貪婪指數（0–100）；紅底是極度恐懼（≤ 20）、綠底是極度貪婪（≥ 80）。', 'Top: BTC price; bottom: the alternative.me Fear & Greed Index (0–100). The red band is extreme fear (≤ 20), the green band extreme greed (≥ 80).',
          '情緒是反向參考：長時間極度貪婪常在過熱段，極度恐懼常在急跌中。2018 年以來第一次掉進極度恐懼之後的 30 天，多數還沒止跌。', 'Sentiment is a contrarian reference: long stretches of extreme greed tend to come in overheated phases, extreme fear in sharp sell-offs. Since 2018, the 30 days after first dropping into extreme fear mostly had not bottomed yet.',
          '指數由波動、成交量、社群、市值占比、搜尋熱度等合成，權重由 alternative.me 決定、可能調整；它反映的是已經發生的價格與情緒，不是預測。', 'The index blends volatility, volume, social activity, dominance and search trends with weights set (and possibly changed) by alternative.me; it reflects price and mood that already happened, not a forecast.'),
        now: function () { var x = D.flows.fng_hist || {}; return x.value == null ? '' : _T(x.value + '（' + fgLab(x.label) + '），一週前 ' + x.d7 + '、30 日平均 ' + fmt.n(x.avg30, 0) + '。', x.value + ' (' + fgLab(x.label) + '), ' + x.d7 + ' a week ago, 30-day average ' + fmt.n(x.avg30, 0) + '.'); } },
      'wiki': { h: h('上格 BTC 價格，下格英文維基百科「Bitcoin」條目的 7 日平均瀏覽量 ÷ 自己過去一年的中位數（對數刻度）；紅底是暴增（≥ 2.5 倍）。', 'Top: BTC price; bottom: 7-day average views of the English Wikipedia "Bitcoin" article ÷ its own past-year median (log scale). The red band marks spikes (≥ 2.5×).',
          '倍數突然衝高＝新手大量湧入在查資料，2017 年底、2020 年底到 2021 年都是；長時間在 1 倍附近或以下，代表散戶還沒回來。', 'A sudden jump means newcomers flooding in to look things up, as in late 2017 and late 2020 into 2021; hovering around 1× or below means retail has not come back.',
          '只代表關注度，不分買賣：暴跌也會帶來暴增。只算英文版；中文圈、X、YouTube 的熱度看不到。', 'Attention only, not direction: crashes bring spikes too. English Wikipedia only; Chinese-language, X and YouTube attention are not captured.'),
        now: function () { var x = D.flows.wiki || {}; return x.ratio == null ? '' : _T('×' + fmt.n(x.ratio, 2) + '（每天約 ' + fmt.n(x.v7) + ' 次，一年中位數 ' + fmt.n(x.med) + '）。', '×' + fmt.n(x.ratio, 2) + ' (about ' + fmt.n(x.v7) + ' a day; past-year median ' + fmt.n(x.med) + ').'); } },
      'cot': { h: h('上格 BTC 價格，下格 CME 比特幣期貨的淨部位（多單 − 空單，換算成顆）：紫線是槓桿基金、綠線是資產管理機構。每週一點（週二持倉）。', 'Top: BTC price; bottom: net positions in CME bitcoin futures (longs − shorts, in BTC): purple is leveraged funds, green is asset managers. One point per week (Tuesday positions).',
          '資產管理機構淨多增加，比較接近機構真的看多；槓桿基金淨空擴大多半是基差交易（ETF 買現貨、CME 放空），套利資金越多空單越大。兩條線一起往零靠近，常是套利價差變小、機構在 CME 的部位整體縮小。', 'A rising asset-manager net long is closer to genuine institutional bullishness; a widening leveraged-fund net short is mostly basis trading (long spot via ETFs, short CME), growing with arbitrage money. Both lines drifting toward zero often means the basis has narrowed and institutions hold less on CME overall.',
          '只看 CME，不含幣安等加密交易所的期貨；持倉晚 3–10 天公布。', 'CME only, not crypto-exchange futures such as Binance; positions are published 3–10 days late.'),
        now: function () { var x = D.flows.cot || {}; return x.lev == null ? '' : _T('槓桿基金 ' + fmt.n(x.lev) + ' 顆、資產管理機構 ' + fmt.n(x.am) + ' 顆（' + fmt.md(x.date) + ' 持倉）。', 'Leveraged funds ' + fmt.n(x.lev) + ' BTC, asset managers ' + fmt.n(x.am) + ' BTC (as of ' + fmt.md(x.date) + ').'); } },
      'conf': { h: h('上格：BTC 價格、短期持有者這 7 天賣出的幣的平均成本（紫）、還在持有的人的成本（橘）。下格：兩條成本線的差距 ÷ 收盤；綠＝≥ +0.05、紅＝≤ −0.05、黃底是轉換帶。', 'Top: BTC price, the average cost of coins short-term holders sold over 7 days (purple) and the cost of those still holding (orange). Bottom: the gap between the two ÷ close; green ≥ +0.05, red ≤ −0.05, the yellow band is the transition zone.',
          '綠色連續出現＝最近才進場的人沒急著賣、市場還接得住，常見於多頭主升段；紅色＝成本低的人也在賣，常見於急跌與熊市。由紅轉綠是信心回來的跡象，由綠轉黃常是動能變弱。', 'Sustained green means recent buyers are not rushing out and the market keeps absorbing supply, typical of the main leg of a bull run; red means even low-cost coins are selling, typical of crashes and bear markets. Red turning green signals returning confidence; green fading to yellow often means momentum is cooling.',
          '7 日平均、逐筆 UTXO、未做實體調整：交易所整理錢包或大額內部轉帳會讓單週跳一下。±0.05 是原作者自己說任意訂的轉換帶，不是精確門檻；轉負之後常是洗盤，不一定續跌。', '7-day average, UTXO-level, not entity-adjusted: exchange wallet shuffles or large internal transfers can make a single week jump. ±0.05 is a band the original author calls arbitrary, not a precise trigger; a turn negative is often a shake-out rather than a continued fall.'),
        now: function () { var x = D.onchain.sthconf || {}; return x.value == null ? '' : _T((x.value > 0 ? '+' : '') + fmt.n(x.value, 3) + '（' + confWord(x.band) + '，' + ymd(x.since) + ' 起）；賣出成本 ' + fmt.usd(x.spend) + '、持有成本 ' + fmt.usd(x.hold) + '。', (x.value > 0 ? '+' : '') + fmt.n(x.value, 3) + ' (' + confWord(x.band) + ' since ' + ymd(x.since) + '); sellers\' cost ' + fmt.usd(x.spend) + ', holders\' cost ' + fmt.usd(x.hold) + '.'); } },
      'profit': { h: h('短期持有者中處於獲利的比例。', 'Share of short-term holder supply in profit.', '長時間 > 90%＝過熱、容易回檔；跌到 50% 以下＝短期持有者普遍套牢，回調中常接近階段低點。', 'Long stretches above 90% mean overheating and pullback risk; below 50% means most short-term holders are underwater, often near a local low in a correction.', '同一個數字在牛市回調和熊市裡意義不同。', 'The same reading means different things in a bull correction and a bear market.'),
        now: function () { var p = (D.chips.flow || {}).sth_in_profit_pct || {}; return _T(fmt.n(p.value, 1) + '%（7 天前 ' + fmt.n(p.d7, 1) + '%），30 日最低 ' + fmt.n(p.min30, 1) + '%（' + ymd(p.min30_date) + '）。', fmt.n(p.value, 1) + '% (' + fmt.n(p.d7, 1) + '% a week ago); 30-day low ' + fmt.n(p.min30, 1) + '% (' + ymd(p.min30_date) + ').'); } },
      'urpd': { h: h('每 2,000 美元一格：有多少顆 BTC 最後一次移動是在這個價位；橘格是現價，淡框是 7 天前。', '$2,000 buckets: how many BTC last moved at each price; the orange bucket is the current price, faint outlines are 7 days ago.', '籌碼厚的價位常成支撐或壓力（買在那裡的人會防守或解套賣出）；籌碼薄的區間價格走得快。', 'Thick buckets often act as support or resistance (holders defend or sell to break even); price moves fast through thin zones.', '交易所內部轉帳也會重設成本。', 'Exchange-internal transfers also reset the cost basis.') },
      'npl': { h: h('上層：BTC 價格與每天的淨實現損益氣泡（綠＝當天整體獲利賣出、紅＝認賠賣出，越大金額越大，粗外圈＝在之前一年最極端的 2%）；下層：同一數字的每日柱。切到「30 日累計」看週期級別：下層是 30 日累計佔市值的比例，紅線是之前 4 年最大 30 日淨獲利的 1/4（取負），橘圈是首次跌破。', 'Top: BTC price with a bubble for each day\'s net realized profit/loss (green = net profit selling, red = net loss selling, bigger = larger, thick ring = most extreme 2% of the prior year); bottom: the same numbers as daily bars. Switch to “30-day total” for the cycle view: the bottom pane is the 30-day total as % of market cap, the red line minus a quarter of the prior 4 years\' largest 30-day net profit, and orange rings the first breaches.', '大綠泡集中在急漲與高點那幾天＝獲利了結；綠泡變小＝想在現價賣的人變少。回檔時出現大紅泡＝認賠出清，但不代表已經見底。', 'Big green bubbles cluster on rallies and highs: profit taking; shrinking green bubbles mean fewer holders want to sell at this price. Big red bubbles on pullbacks are loss capitulation, which does not mean the low is in.', '只有淨值（獲利減認賠），看不到兩邊各有多少；交易所內部轉帳也會實現損益。2015 起只用當天已知資料回測：認賠高峰之後的表現和平常差不多，不是買點；獲利高峰之後反而多半續漲（一輪比一輪弱），不是賣點。30 日累計首次跌破紅線（2015 起）：2015/01、2018/11、2020/03、2022/05、2022/11、2026/02、2026/06；2023 年以前的 5 次有 4 次 1 年後上漲（2022/05 那次 −7%），而且 2018/11、2022/05 之後還再跌 26%、46%。2026-11-04 起才改成這條線，是看過這一輪結果才定的，樣本只有 3–4 輪；舊規則（4 年第 3 百分位）沒有 2026 兩次，2022 年那次是 6/16。2028 年 3 月以後 2024/3 的獲利高點移出 4 年視窗，紅線會變淺到約 −1%。ETF 時代這個訊號可能變鈍：ETF 持有人在股市互相買賣不會移動鏈上的幣，只有淨贖回才會；這一輪最深的認賠只有同輪最大獲利的 3–4 成，前兩輪約 7 成。', 'Net only (profit minus loss), so the two sides are not visible separately; exchange-internal transfers also realize P/L. In tests since 2015 using only data known on the day, loss spikes were followed by ordinary returns (not a buy signal), and profit spikes were more often followed by further gains, weaker each cycle (not a sell signal). First breaches of the 30-day red line since 2015: 2015/01, 2018/11, 2020/03, 2022/05, 2022/11, 2026/02, 2026/06; 4 of the 5 before 2023 were higher a year later (2022/05 was −7%), and after 2018/11 and 2022/05 price still fell another 26% and 46%. The line was changed on 2026-11-04 after seeing this cycle, with only 3–4 cycles of history; the old rule (4-year 3rd percentile) missed both 2026 breaches and triggered 2022 on 6/16. After March 2028 the 2024/3 profit peak leaves the 4-year window and the line will rise to about −1%. The signal may be blunter in the ETF era: ETF shares changing hands on the stock market do not move coins on-chain, only net redemptions do; this cycle\'s deepest loss was only 30–40% of its largest profit, versus about 70% in the previous two.'),
        now: function () { var n = D.onchain.npl; if (!n) return ''; return _T('近 7 日合計 ' + nplB(n.sum7_usd_m) + '，前 7 日 ' + nplB(n.sum7_prev_usd_m) + '；最新一天 ' + nplB(n.usd_m) + '（近一年第 ' + fmt.n(n.rank_1y, 0) + ' 百分位）。', 'Past 7 days ' + nplB(n.sum7_usd_m) + ', prior 7 days ' + nplB(n.sum7_prev_usd_m) + '; latest day ' + nplB(n.usd_m) + ' (1-year percentile ' + fmt.n(n.rank_1y, 0) + ').'); } },
      'cohort': { h: h('每 2,000 美元一格：左邊是持有不到 155 天的短期持有者（STH），右邊是長期持有者（LTH），橫線是收盤；灰底是過去 155 天價格走過的區間。切到「STH 變化／LTH 變化」看和約 30 天前比：灰條是當時，彩條是現在。', '$2,000 buckets: short-term holders (held under 155 days) on the left, long-term holders on the right, the line is the close; the shaded band is the range price covered in the past 155 days. Switch to “STH change / LTH change” to compare with about 30 days ago: grey is then, colour is now.',
          '短期持有者堆在收盤上方＝那批人帳面虧損，價格回到成本時容易解套賣出；堆在下方＝跌回去之前他們還在獲利，是第一道承接。長期持有者的堆動得慢，變少的格子代表那個成本的長期持有者在賣。', 'Short-term holders piled above the close are underwater and tend to sell when price returns to their cost; piled below, they stay in profit until price falls back, the first layer of support. Long-term holder piles move slowly; a shrinking bucket means long-term holders with that cost are selling.',
          '「現在」是 CheckOnChain 依實際幣齡算的（取不到時退回推算）；「變化」是推算。都是逐筆 UTXO、不是實體調整，交易所整理錢包會被當成賣出再買進（單日大量又集中的搬家已放回原本的成本）；灰底區間外只有長期持有者。', '“Now” is CheckOnChain\'s actual coin-age data (falls back to the estimate if unavailable); “changes” are estimated. Both are per-UTXO, not entity-adjusted, so exchange wallet reshuffles look like selling and rebuying (large, concentrated one-day moves are put back at their original cost). Outside the shaded band there are only long-term holders.'),
        now: function () { var co = D.chips.cohort; if (!co) return ''; var ex = co.src === 'checkonchain'; return _T('短期持有者 ' + coins(co.tot.sth) + '、平均成本 ' + fmt.usd(co.tot.sth_cost) + '；長期持有者 ' + coins(co.tot.lth) + '（' + (ex ? 'CheckOnChain ' + ymd(co.now_date) + '，已扣搬家日' : 'URPD ' + ymd(co.date) + '，推算') + '）。', 'Short-term holders ' + coins(co.tot.sth) + ', average cost ' + fmt.usd(co.tot.sth_cost) + '; long-term holders ' + coins(co.tot.lth) + ' (' + (ex ? 'CheckOnChain ' + ymd(co.now_date) + ', transfer days removed' : 'URPD ' + ymd(co.date) + ', estimated') + ').'); } },
      'liq': { h: h('每一格是某個小時、某個價位推算還沒被清算的槓桿倉位量，越亮越多；疊的是小時 K 線（「2 年」是每天一欄、日 K 線），虛線是最後收盤。收盤下方是多單的清算價、上方是空單的。', 'Each cell is the estimated leveraged position size still awaiting liquidation at that hour and price; brighter means more. Hourly candles on top (“2Y” uses one column and one candle per day), the dashed line is the last close. Long liquidation prices sit below the close, shorts above.',
          '亮帶＝槓桿倉位堆積的價位。價格走到那裡會觸發強制平倉：多單強平是市價賣、空單強平是市價買，常讓行情在那一段走得更快；價格走過之後那一帶會變暗（被清掉）。', 'Bright bands are where leverage is stacked. Price reaching them triggers forced closes: longs are market-sold, shorts market-bought, which often speeds up the move through that zone; once price passes, the band goes dark (cleared).',
          '推算：Coinalyze 彙整的多家交易所未平倉量（取不到時只有 OKX），槓桿分布是假設，亮帶位置會隨假設移動；每天快照一次，不是即時；清算量多不代表價格會往那裡走。', 'An estimate: multi-exchange open interest compiled by Coinalyze (OKX only when unavailable), with an assumed leverage mix that moves the bands; a daily snapshot, not real time; more liquidations on one side does not mean price will go there.') },
      'tmh': { h: h('上格 BTC 價格（對數）；下格是 Tidemark 的 0–100 訊號，2011 起每週、近一年每日。頂部視角：紅＝頂部訊號（粗線）、琥珀＝熱度、灰虛線＝時機，直虛線是歷次週期頂部；底部視角：綠＝底部訊號、藍＝冷度，直虛線是歷次週期底部、綠點線是本輪候選低點。點圖例可以開關每條線，滑過圖時上方那一行跟著顯示當天數字。', 'Price on top (log); below, Tidemark\'s 0–100 signals, weekly since 2011 and daily for the past year. Top view: red = top signal (thick), amber = heat, grey dashed = timing, with vertical dashes at past cycle tops. Bottom view: green = bottom signal, blue = cold, vertical dashes at past cycle bottoms and a green dotted line at this cycle\'s candidate low. Click a legend item to hide or show a line; hovering updates the readout row above.',
          '頂部訊號 ≥50 進入窗口、≥70 警戒；底部訊號 ≥50 進入底部區。看過去幾次頂部、底部前後訊號升到多高、提前多久亮，再對照現在的位置。', 'A top signal of 50 or more opens the window and 70 is the alert; a bottom signal of 50 or more is the bottom zone. See how high the signals rose around past tops and bottoms, and how early, then compare with now.',
          '第三方模型，規則與權重由 Tidemark 決定、可能改版；歷史是用目前的規則回算的，不是當時的即時讀數；部分指標 2012 年底以後才有，之前只有熱度。只作讀值。', 'A third-party model whose rules and weights Tidemark sets and may change; the history is back-calculated under today\'s rules, not live readings at the time; some inputs start in late 2012, before which only heat exists. Reading only.'),
        now: function () { var x = ((D.cycle || {}).tidemark || {}).hist; if (!x) return ''; var p = x.rows[x.rows.length - 1]; return _T('頂部訊號 ' + fmt.n(p[2], 0) + '、熱度 ' + fmt.n(p[3], 0) + '；底部訊號 ' + fmt.n(p[5], 0) + '、冷度 ' + fmt.n(p[6], 0) + '（' + fmt.md(x.to) + '）。', 'Top signal ' + fmt.n(p[2], 0) + ', heat ' + fmt.n(p[3], 0) + '; bottom signal ' + fmt.n(p[5], 0) + ', cold ' + fmt.n(p[6], 0) + ' (' + fmt.md(x.to) + ').'); } },
      'fh': { h: h('上格價格；下格是多家永續以未平倉加權的資金費率，年化 % 的 7 日平均。綠＝正（多方付費給空方）、紅＝負（空方付費），虛線是 30%。', 'Price on top; below, the open-interest-weighted funding rate across perpetuals, 7-day average, annualized. Green = positive (longs pay shorts), red = negative (shorts pay); the dashed line is 30%.',
          '費率越高＝做多的人越願意付錢，槓桿多單越擁擠；轉負＝空方擁擠或多單已被洗掉。極端值比方向更有參考價值。', 'Higher funding = longs willing to pay more, leveraged longs more crowded; negative = shorts crowded or longs already flushed. Extremes say more than the direction.',
          '每日值是當天費率的（開＋高＋低＋收）÷ 4，和「永續資金費率」的即時快照不同；Hyperliquid 2024-10 起才有。統計只是歷史描述，不是訊號。', 'Daily values use (open + high + low + close) ÷ 4, so they differ from the live "Perpetual funding" snapshot; Hyperliquid joins in 2024-10. The stats describe history, not a signal.'),
        now: function () { var x = (D.deriv || {}).fund_hist; return x ? _T('7 日平均 ' + fmt.pct(x.value, 1) + '（' + oxYm(x.from_) + ' 以來第 ' + x.pct + ' 百分位）。', '7-day average ' + fmt.pct(x.value, 1) + ' (' + ord(x.pct) + ' percentile since ' + oxYm(x.from_) + ').') : ''; } },
      'oih': { h: h('上格價格；下格是 11 個 BTC 永續合約的未平倉量合計（顆）。', 'Price on top; below, total open interest across 11 BTC perpetual contracts (BTC).',
          '和價格一起看：價格跌、未平倉增＝逆勢開新倉，槓桿在堆；價格跌、未平倉減＝多單被清掉，槓桿在退。未平倉越高，之後清算時的波動通常越大。', 'Read it with price: price down with open interest up = new positions against the move, leverage building; price down with open interest down = longs cleared, leverage unwinding. Higher open interest usually means bigger swings when liquidations hit.',
          '以顆計：價格漲時同樣的美元會變少顆。合約陸續上線，長期增加有一部分是新合約。', 'In BTC: the same dollars mean fewer coins when price rises. Contracts were added over time, so part of the long-run rise is new contracts.'),
        now: function () { var x = (D.deriv || {}).oi_hist; return x ? _T('合計約 ' + fmt.n(x.btc) + ' 顆，30 天 ' + fmt.pct(x.chg30, 1) + '（同期價格 ' + fmt.pct(x.px30, 1) + '）。', 'About ' + fmt.n(x.btc) + ' BTC, ' + fmt.pct(x.chg30, 1) + ' over 30 days (price ' + fmt.pct(x.px30, 1) + ').') : ''; } },
      'lsa': { h: h('上格價格；下格是 Binance、Bybit 的 BTCUSDT 永續上持多單的帳戶占比（%）。紅色帶是 Binance 歷史前 10%、綠色帶是後 10%。', 'Price on top; below, the share of accounts long on Binance and Bybit BTCUSDT perpetuals (%). The red band is Binance\'s top 10%, the green band its bottom 10%.',
          '常被當反向指標：大部分帳戶都做多時，價格容易往下洗；多數帳戶做空時，容易往上軋。讀值裡的統計檢查這個說法在這段期間成不成立。', 'Often read as a contrarian gauge: when most accounts are long, price tends to flush them; when most are short, squeezes follow. The stats in the reading check how well that held in this period.',
          '算帳戶數、不是部位大小，比較像散戶情緒；只有 Binance、Bybit。', 'It counts accounts, not size, so it is closer to retail sentiment; Binance and Bybit only.'),
        now: function () { var x = (D.deriv || {}).ls_acct; return x ? _T('Binance ' + fmt.n(x.binance, 1) + '% 的帳戶做多（第 ' + x.pct + ' 百分位）、Bybit ' + fmt.n(x.bybit, 1) + '%。', 'Binance ' + fmt.n(x.binance, 1) + '% of accounts long (' + ord(x.pct) + ' percentile), Bybit ' + fmt.n(x.bybit, 1) + '%.') : ''; } },
      'tk': { h: h('上格價格；下格是主動買 − 主動賣的 30 天加總（顆）：紫＝現貨（Binance、Coinbase、Bybit），橘＝永續（Binance、Bybit、OKX）。虛線是各自的中位數（常態）。', 'Price on top; below, the 30-day sum of taker buys − sells (BTC): purple = spot (Binance, Coinbase, Bybit), orange = perpetuals (Binance, Bybit, OKX). Dashed lines are each series\' median (typical level).',
          '在常態線上方＝比平常多買、下方＝比平常多賣。現貨偏買、永續偏賣＝真錢在買、槓桿在空；反過來＝槓桿在推、現貨沒跟。', 'Above its typical line = more buying than usual, below = more selling. Spot buying while perps sell = real money buying and leverage shorting; the reverse = leverage pushing without spot.',
          '只算吃單方向，不含掛單；永續的主動賣長期偏多，所以要和常態線比，不看正負。', 'Aggressor side only, no makers; perpetual taker selling runs high over time, so compare with the typical line, not zero.'),
        now: function () { var x = (D.deriv || {}).taker; return x ? _T('30 天：現貨 ' + btcS(x.spot.d30) + ' 顆（常態 ' + btcS(x.spot.med) + '）、永續 ' + btcS(x.perp.d30) + ' 顆（常態 ' + btcS(x.perp.med) + '）。', '30 days: spot ' + btcS(x.spot.d30) + ' BTC (typical ' + btcS(x.spot.med) + '), perpetuals ' + btcS(x.perp.d30) + ' BTC (typical ' + btcS(x.perp.med) + ').') : ''; } },
      'lqv': { h: h('每天實際被強制平倉的 BTC 永續：往上是空單、往下是多單（美元，平方根壓縮刻度），上格是價格。', 'BTC perpetual positions actually force-closed each day: shorts up, longs down (USD, square-root scale), price on top.',
          '多單清算集中＝下跌時槓桿多單被迫賣出，常出現在急跌；空單清算集中＝上漲時被迫買回，常出現在軋空。看近 30 天哪一邊多，比單日更穩。', 'Clusters of long liquidations = leveraged longs forced to sell into a drop; short clusters = forced buying into a squeeze. The 30-day balance is steadier than any single day.',
          '交易所公開的清算資料會少報（Binance 每秒只推一筆；Hyperliquid 沒有、Deribit 停在 2023 年），總額只是下限；比例比總額可靠。', 'Exchange liquidation feeds under-report (Binance one per second; nothing from Hyperliquid, Deribit stopped in 2023), so totals are a floor; the long/short balance is more reliable than the size.'),
        now: function () { var x = (D.deriv || {}).liq_vol; return x ? _T('近 30 天多單占 ' + fmt.n(x.d30.share, 0) + '%（多單 ' + lqvM(x.d30.long) + '、空單 ' + lqvM(x.d30.short) + '）。', 'Past 30 days: longs ' + fmt.n(x.d30.share, 0) + '% (longs ' + lqvM(x.d30.long) + ', shorts ' + lqvM(x.d30.short) + ').') : ''; } },
      'pr-us': { h: h('上格是 BTC 價格；下格是 Coinbase 溢價：Coinbase BTC-USD 收盤比 Binance BTC-USDT 貴多少（%）。柱子是每日值（和 TradingView 的 CB-BN basis 同一種算法），金線是 7 日平均，紅虛線是 −0.15% 深度折價線，紅圈是歷次跌破、旁邊寫 30 天後漲跌；最右邊的空心點是打開網頁時的即時值。', 'Top: BTC price; bottom: the Coinbase premium, how much Coinbase BTC-USD closes above Binance BTC-USDT (%). Bars are daily values (the same calculation as TradingView\'s CB-BN basis), the gold line the 7-day average, the red dashed line the −0.15% deep-discount line; red rings mark past breaks with the 30-day change; the hollow dot at the right edge is the live value when the page opens.',
          '正＝美國現貨（機構、ETF 相關）買得比海外積極；長時間停在 0 以下＝美國買盤缺席。牛市主升段多半維持正值。', 'Positive means US spot buyers (institutions, ETF-related) are keener than offshore; staying below 0 for long means US demand is absent. Bull-market advances usually run positive.',
          '以 USDT 計價，USDT 偏離 1 美元時會有誤差；看方向和持續多久，不看單日。', 'Priced against USDT, so a USDT depeg distorts it; read the direction and how long it lasts, not single days.'),
        now: function () { var cp = D.flows.cb_premium || {}, r = cp.rows || []; if (cp.avg7 == null) return ''; var a7 = ma7r(r).map(function (x) { return x[1]; }), n = 0;
          for (var i = a7.length - 1; i >= 0 && a7[i] != null && (a7[i] < 0) === (cp.avg7 < 0); i--) n++;
          return _T('每日 ' + fmt.pct(cp.pct, 3) + '，7 日平均 ' + fmt.pct(cp.avg7, 3) + '；7 日平均已連續 ' + n + ' 天在 0 ' + (cp.avg7 < 0 ? '以下' : '以上') + '。' + (cp.avg7 < 0 ? '美國現貨買盤比海外弱。' : '美國現貨買盤比海外積極。'), 'Daily ' + fmt.pct(cp.pct, 3) + ', 7-day average ' + fmt.pct(cp.avg7, 3) + '; the 7-day average has been ' + (cp.avg7 < 0 ? 'below' : 'above') + ' 0 for ' + n + ' straight days. ' + (cp.avg7 < 0 ? 'US spot demand is weaker than offshore.' : 'US spot demand is keener than offshore.')); } },
      'pr-asia': { h: h('OKX 場外 USDT 兌人民幣的中間價，比美元兌人民幣匯率高或低多少（%）；每天 00:06 UTC 記一個快照，標在剛收盤的那一天。', 'OKX OTC USDT/CNY mid price vs the USD/CNY rate (%); one snapshot a day at 00:06 UTC, dated to the day that just closed.',
          '正（溢價）＝有人搶著用人民幣換 USDT 進場；負（折價）＝換回人民幣的人多，亞洲資金偏離場。過去牛市常見溢價，熊市或監管收緊時常見折價。', 'Positive (premium) means buyers are rushing to swap CNY into USDT; negative (discount) means more are cashing out to CNY and Asian money is leaning out. Premiums are common in bull markets, discounts in bear markets or crackdowns.',
          '場外報價受人民幣管制、商家與付款方式影響，±0.3% 內視為持平；歷史從 2026/11/02 才開始累積，不到 30 天不談百分位。', 'OTC quotes depend on capital controls, merchants and payment methods; treat ±0.3% as flat. The record only starts 2026-11-02, so no percentiles before 30 days.'),
        now: function () { var p3 = D.flows.premium3 || {}, u = p3.usdt, h = p3.usdt_hist || []; if (!u) return ''; var a = h.length > 7 ? h[h.length - 8][1] : null;
          return _T('場外 USDT 約 ' + fmt.n(u.mid, 3) + ' 人民幣、匯率 ' + fmt.n(u.fx, 3) + '，' + fmt.pct(u.pct, 2) + '：' + (u.pct > 0.3 ? '溢價，亞洲有人搶著進場。' : u.pct < -0.3 ? '折價，亞洲資金偏離場。' : '接近匯率，買賣大致平衡。') + (a != null ? '一週前 ' + fmt.pct(a, 2) + '。' : '目前累積 ' + h.length + ' 天。'),
            'OTC USDT at about ' + fmt.n(u.mid, 3) + ' CNY vs a ' + fmt.n(u.fx, 3) + ' FX rate, ' + fmt.pct(u.pct, 2) + ': ' + (u.pct > 0.3 ? 'a premium; Asian buyers are rushing in.' : u.pct < -0.3 ? 'a discount; Asian money is leaning out.' : 'near the FX rate; flows roughly balanced.') + (a != null ? ' A week ago ' + fmt.pct(a, 2) + '.' : ' ' + h.length + ' day(s) recorded so far.')); } },
      'pr-perp': { h: h('OKX BTC 永續合約比現貨貴或便宜多少（%）的 7 日平均；虛線是 0。', '7-day average of how far OKX BTC perpetuals trade above or below spot (%); the dashed line is 0.',
          '永續平常就比現貨低一點（這一年平均約 −0.04%），所以和它自己的歷史比：比平常高＝多單願意付錢追價，比平常低＝槓桿偏空或在避險。', 'Perps usually sit slightly below spot (about −0.04% on average this year), so compare with its own history: higher than usual means longs pay up to chase; lower means leverage leans short or is hedging.',
          '只有 OKX 一家，價差只有百分之零點零幾；要搭配資金費率一起看。', 'OKX only, and the gap is only a few hundredths of a percent; read it with funding rates.'),
        now: function () { var pp = (D.flows.premium3 || {}).perp, fw = (D.deriv.funding_multi || {}).weighted_now; if (!pp) return '';
          return _T('7 日平均 ' + fmt.pct(pp.avg7, 3) + '，平常（30 日）' + fmt.pct(pp.avg30, 3) + '，在近 ' + pp.n + ' 天第 ' + fmt.n(pp.avg7_pct_own, 0) + ' 百分位' + (fw != null ? '；資金費率年化 ' + fmt.n(fw, 1) + '%' : '') + '。' + (pp.avg7_pct_own == null ? '' : pp.avg7_pct_own >= 70 ? '比平常貴，多單在付錢追價。' : pp.avg7_pct_own <= 30 ? '比平常便宜，槓桿偏空。' : '和平常差不多。'),
            '7-day average ' + fmt.pct(pp.avg7, 3) + ', usually (30-day) ' + fmt.pct(pp.avg30, 3) + ', ' + fmt.n(pp.avg7_pct_own, 0) + 'th percentile of ' + pp.n + ' days' + (fw != null ? '; funding ' + fmt.n(fw, 1) + '% a year' : '') + '. ' + (pp.avg7_pct_own == null ? '' : pp.avg7_pct_own >= 70 ? 'Richer than usual: longs pay up to chase.' : pp.avg7_pct_own <= 30 ? 'Cheaper than usual: leverage leans short.' : 'About usual.')); } },
      'dawn': { h: h('每週的週期熱度（0–100），以 50 為中線：熱度高於 50 往上長成暖色的山（琥珀 → 越接近頂越紅），低於 50 往下長成冷色的谷（淺藍 → 越接近底越深藍）；顏色和週線多空分數的階段色同一套。網點越靠中線越大越密。上方細線指的是歷次頂，下方指的是歷次底。熱度 ≥ 80 黃昏、≤ 10 深夜；滑過去看那一週的熱度、方向與價格。', 'Weekly cycle heat (0–100) around a midline at 50: above 50 it grows up into warm hills (amber, turning red near tops), below 50 down into cool valleys (light blue, turning deep blue near bottoms); the colours are the same stage colours as the weekly regime score. Dots get larger and denser toward the midline. Lines above point to past tops, lines below to past bottoms. Heat ≥ 80 is Dusk, ≤ 10 Deep night; hover for that week\'s heat, trend and price.',
          '熱度是估值，回答「離頂部、底部多遠」；方向是趨勢，回答「現在往哪走」。熱度低又翻多（破曉）歷史上之後一年最好；熱度高（黃昏）之後一年大約持平、下跌機率接近一半。', 'Heat is valuation, answering "how far from a top or bottom"; trend answers "which way now". Low heat with a bullish flip (Daybreak) has had the best year ahead; high heat (Dusk) has been roughly flat a year later, with close to even odds of a fall.',
          '近兩輪鏈上估值都比價格先見頂，黃昏常提早出現；只有三輪多完整週期，統計只是歷史描述，不是訊號。', 'In the last two cycles valuations peaked before price, so Dusk tends to come early; with only three-plus full cycles the stats describe history and are not a signal.'),
        now: function () { var x = (D.cycle || {}).dawn; return x ? _T('熱度 ' + fmt.n(x.heat, 0) + '，' + dwName(x.stage, true) + '，方向' + (x.regime > 0 ? '多方' : '空方') + '。', 'Heat ' + fmt.n(x.heat, 0) + ', ' + dwName(x.stage, true) + ', trend ' + (x.regime > 0 ? 'bullish' : 'bearish') + '.') : ''; } },
      'regime': { h: h('上格是 BTC 價格，下格是每週的多空分數（−6 到 +6），柱子按階段上色：≥ +4 過熱（紅）、熊市後轉正的頭 26 週初牛（綠）、其餘正值牛（琥珀）、負值熊（淺藍）、≤ −4 極熊（深藍）。', 'Top: BTC price; bottom: the weekly regime score (−6 to +6), bars coloured by stage: ≥ +4 overheated (red), the first 26 positive weeks after a real bear early bull (green), other positive bull (amber), negative bear (light blue), ≤ −4 extreme bear (deep blue).',
          '把六個看趨勢、估值、資金和獲利了結的訊號合成一個數字：正值對應牛市、負值對應熊市；柱子越長，六項越一致。分數在零軸附近（絕對值小於 1）代表訊號互相矛盾。', 'Six trend, valuation, capital-flow and profit-taking signals combined into one number: positive stretches match bull markets, negative ones bear markets; longer bars mean the six agree more. Near zero (under 1 in size) the signals conflict.',
          '是本站自己的合成方法，不是任何不公開指標的複製。翻轉要連續 4 週才算，所以會晚幾週；2014/6、2021/8 的翻多一年後價格反而較低。', 'Our own composite, not a copy of any unpublished indicator. A flip needs 4 straight weeks, so it lags; the bullish flips of Jun 2014 and Aug 2021 saw lower prices a year later.') },
      'ad': { h: h('上格是 BTC 價格，下格是 30 天的表觀需求（顆）：綠＝正、紅＝負，虛線是它的 30 日平均，琥珀色點虛線是疑似搬家日。', 'Top: BTC price; bottom: 30-day apparent demand (BTC), green positive and red negative, the dashed line its 30-day average, amber markers likely transfer days.',
          '正＝舊幣醒來被市場接走，需求夠；負＝滿一年沒動的幣增加得比新挖出的快，換手少、需求偏弱。跌到自己的 30 日平均之下＝需求在轉弱；大段紅色常出現在下跌或盤整期。', 'Positive means old coins wake and get absorbed: enough demand. Negative means coins reaching one year unmoved outpace issuance: little turnover, soft demand. Dropping below its own 30-day average means demand is weakening; long red stretches tend to come with declines or chop.',
          '會受一年前換手量影響（那批幣滿一年時把它拉低）；交易所整理錢包會造成尖峰，一年後還有回音。逐筆計算、不是實體調整，和 CryptoQuant 的數值不完全相同。', 'It echoes turnover from a year earlier (those coins drag it down when they turn one); exchange wallet reshuffles cause spikes with an echo a year later. Per-UTXO, not entity-adjusted, so it differs somewhat from CryptoQuant\'s numbers.'),
        now: function () { var x = (D.onchain || {}).ad; if (!x) return ''; return _T(adK(x.value) + '（' + fmt.md(x.date) + '），30 日平均 ' + adK(x.sma30) + (x.value < x.sma30 ? '，在平均之下。' : '，在平均之上。'), adK(x.value) + ' (' + fmt.md(x.date) + '), 30-day average ' + adK(x.sma30) + (x.value < x.sma30 ? ', below the average.' : ', above the average.')); } },
      'rpl': { h: h('上格是 BTC 價格，下格是全網實現獲利 ÷ 實現虧損的 90 天平均（都是對數刻度）；1 以上綠、以下紅，紅底是低於 1 的期間。', 'Top: BTC price; bottom: network-wide realized profit ÷ realized loss, 90-day average (both log scale). Green above 1, red below; red bands mark the stretches below 1.',
          '低於 1＝賣出的人整體在認賠，大段紅色都出現在熊市；回到 1 以上代表賣出的人又開始賺錢。歷史上大段紅色結束後，多半到週期頂部都沒再跌回 1 以下。', 'Below 1 means sellers as a whole are realizing losses; long red stretches all came in bear markets. Moving back above 1 means sellers are taking profits again; historically, after a long red stretch it mostly stayed above 1 until the cycle top.',
          '不是保證：2019/5 回到 1 以上後，2019/12–2020/1 又跌回 37 天。90 天平均反應慢，要搭配最近 7 天的每日比值看。', 'Not a guarantee: after returning above 1 in May 2019 it fell back below for 37 days in Dec 2019–Jan 2020. The 90-day average is slow; read it with the last 7 daily values.') },
      'lthloss': { h: h('上格是 BTC 價格，下格是長期持有者（持有 ≥155 天）帳面虧損的比例；紅圈是歷輪熊市底部的高點，紅底是 42–48% 區，虛線是這輪高點。', 'Top: BTC price; bottom: the share of long-term holder (155+ days) supply at a loss. Red circles mark peaks at past bear-market bottoms, the red band is 42–48%, the dashed line this cycle\'s peak.',
          '熊市底部時比例衝到高點（2019、2022、2026 都在 42–48%）；脫離底部後，之前幾輪都沒有再創新高，回升（價格回調）時常是牛初的加碼段。跌破虛線那一天，等於這個規律被打破。', 'It peaks at bear-market bottoms (2019, 2022 and 2026 all at 42–48%); after leaving the bottom, earlier cycles never made a new high, and its rebounds (price pullbacks) were often early-bull buying windows. A move above the dashed line would break that pattern.',
          '不只受價格影響：最近高價買進的短期持有者滿 155 天後會被算成長期持有者，價格不漲也會把比例推高。只有 3–4 輪樣本，是事後看出的規律。', 'Not price alone: recent high-priced buyers become long-term holders after 155 days, which lifts the share even if price stalls. Only 3–4 cycles, and a pattern seen in hindsight.'),
        now: function () { var x = (D.onchain || {}).lthloss; if (!x) return ''; var c = x.cohort; return _T(fmt.n(x.value, 1) + '%（' + fmt.md(x.date) + '）' + (c && c.break_price ? '；跌破約 ' + fmt.usd(c.break_price) + ' 會超過這輪高點。' : '。'), fmt.n(x.value, 1) + '% (' + fmt.md(x.date) + ')' + (c && c.break_price ? '; below about ' + fmt.usd(c.break_price) + ' it would top this cycle\'s peak.' : '.')); } },
      'levels': { h: h('BTC 價格和七條線：200 日、365 日、50 週均線，短期持有者成本、真實市場均價、實現價、長期持有者成本。', 'BTC price and seven lines: the 200-day, 365-day and 50-week averages, the short-term holder cost basis, true market mean, realized price and long-term holder cost basis.',
          '價格在線上＝這批買家或這段趨勢整體獲利；好幾條線擠在一起的價位，常被當成支撐或壓力來看。價格跌破一條線，代表那一批人轉為虧損。', 'Price above a line means that group of buyers, or that trend, is in profit; where several lines bunch up is often read as support or resistance. A break below a line means that group turns to a loss.',
          '線會隨時間移動；「支撐」是常見的讀法，不保證守得住。均線和成本線來自不同資料（統一收盤與 Bitview）。', 'The lines move over time; “support” is a common reading, not a guarantee. Moving averages and cost bases come from different data (standard close and Bitview).'),
        now: function () { var x = (D.cycle || {}).levels; if (!x) return ''; var nr = x.near; return nr ? _T('收盤下方 ' + nr.pct + '% 內有 ' + nr.keys.length + ' 條線，在 ' + fmt.usd(nr.lo) + '–' + fmt.usd(nr.hi) + '（' + fmt.md(x.date) + '）。', nr.keys.length + ' lines within ' + nr.pct + '% below the close, at ' + fmt.usd(nr.lo) + '–' + fmt.usd(nr.hi) + ' (' + fmt.md(x.date) + ').') : ''; } },
      'stkrel': { h: h('BTC、S&P 500、那斯達克、黃金（PAXG）近兩個月的漲跌，起點都是 0。', 'Change over two months for BTC, the S&P 500, the Nasdaq and gold (PAXG), all starting at 0.', '看 BTC 在回檔中是不是比傳統資產跌得更多；跌得差不多代表只是跟著大盤走。', 'Shows whether BTC fell more than traditional assets in the pullback; falling about the same means it simply moved with the market.', '起點不同，結論會不同；只看兩個月。', 'A different start date gives a different picture; two months only.'),
        now: function () { var x = D.flows.btc_vs_stocks; if (!x) return ''; var L = x.rel.last, f = function (v) { return v == null ? '—' : fmt.pct(v, 1); }; return 'BTC ' + f(L.btc) + ' · S&P 500 ' + f(L.spx) + ' · ' + _T('那斯達克 ', 'Nasdaq ') + f(L.ndq) + ' · ' + _T('黃金 ', 'gold ') + f(L.gold); } },
      'stkwin': { h: h('近 90 個美股交易日裡，BTC 當天漲幅大於 S&P 500 的比例（灰線 50%）。', 'Share of the last 90 US sessions in which BTC rose more than the S&P 500 (grey line: 50%).', '高於 50% 且維持住＝BTC 相對股市轉強；長期低於 50% 代表一直落後。', 'Holding above 50% means BTC is gaining strength against stocks; staying below means it keeps lagging.', '只看贏的次數、不看贏多少（另看每日平均超額）；BTC 和美股收盤時間差約 3 小時。', 'It counts wins, not their size (see the average daily excess); BTC and US closes are about 3 hours apart.'),
        now: function () { var x = D.flows.btc_vs_stocks; if (!x) return ''; return _T(fmt.n(x.win90, 0) + '%，每日平均超額 ' + fmt.n(x.excess90, 2) + ' 個百分點（' + fmt.md(x.date) + '）。', fmt.n(x.win90, 0) + '%, average daily excess ' + fmt.n(x.excess90, 2) + ' points (' + fmt.md(x.date) + ').'); } },
      'capflow': { h: h('上格是 BTC 價格；下格是全體實現市值裡，最近一個月換手的幣（橘）和一到兩年沒動的幣（紫）各佔多少；黃底是週期頂部、青綠底是熊市底部。', 'Top: BTC price. Bottom: the share of realized cap held in coins moved within the last month (orange) and coins unmoved for one to two years (violet); amber bands mark cycle tops, teal bands bear-market bottoms.',
          '橘色衝高＝大量新錢在高價追進，過去兩輪頂部都超過 50%；紫色升高＝一年前進場的人沒賣，熊底附近最大。兩塊一起看：橘低、紫升代表籌碼在沉澱。', 'A surge in orange means lots of new money chasing at high prices — above 50% at the last two tops; a rising violet share means last year\'s buyers have not sold, largest near bottoms. Read together: low orange and rising violet mean supply is settling.',
          '按實現市值加權，高價買進的幣權重大；紫色升高部分是時間推移（高價的幣滿一年），不全是信心。逐筆 UTXO，交易所整理錢包會讓幣齡歸零。', 'Weighted by realized cap, so coins bought high weigh more; part of the violet rise is just time passing (high-priced coins turning one). Per-UTXO: exchange wallet reshuffles reset coin age.'),
        now: function () { var x = (D.onchain || {}).capflow; if (!x) return ''; return _T('1–2 年沒動 ' + cfPct(x.y12) + '、1 個月內換手 ' + cfPct(x.m1) + '（' + fmt.md(x.date) + '）。', 'Unmoved 1–2y ' + cfPct(x.y12) + ', moved < 1 month ' + cfPct(x.m1) + ' (' + fmt.md(x.date) + ').'); } },
      'sthband': { h: h('BTC 價格、短期持有者成本（橘）和上下各兩條標準差帶（對數刻度）。', 'BTC price, short-term holder cost (orange) and two standard-deviation bands on each side (log scale).',
          '價格在 +1 標準差以上＝短期持有者獲利豐厚，過去常在這附近遇到賣壓（例如 2023 年 1–9 月：碰到 +1 標準差後，回踩到成本線或 −1 標準差）；跌到 −1 標準差以下＝短期持有者普遍套牢，多半是急跌後的恐慌區。', 'Above +1σ short-term holders sit on big gains and selling has often shown up nearby (e.g. Jan–Sep 2023: each touch of +1σ was followed by a pullback to the cost line or −1σ); below −1σ short-term holders are broadly under water, usually after a sharp drop.',
          '帶寬用近 4 年的價格起伏算，會隨時間改變；碰到帶不代表一定反轉。只有一家資料（Bitview），和 Glassnode 原版的數字會有小差距。', 'The band width comes from the last 4 years of price swings and changes over time; touching a band does not mean a reversal. One data source (Bitview), so small differences from Glassnode\'s original are expected.'),
        now: function () { var x = (D.onchain || {}).sth_bands; if (!x) return ''; var n = x.now; return _T('收盤在 ' + sbZ(n.z) + ' 標準差（' + fmt.md(x.date) + '）；+1 標準差 ' + fmt.usd(n.bands['1']) + '、−1 標準差 ' + fmt.usd(n.bands['-1']) + '。', 'Close at ' + sbZ(n.z) + 'σ (' + fmt.md(x.date) + '); +1σ ' + fmt.usd(n.bands['1']) + ', −1σ ' + fmt.usd(n.bands['-1']) + '.'); } },
      'agecost': { h: h('可以切換兩種看法（對數刻度）：3–6 個月持幣成本（橘）配價格，綠點是熊市後第一次站回、灰點是其他站回；6–12 個月（橘）與 12–18 個月（紫）持幣成本，紅點死叉、綠點金叉。', 'Two views (log scale): the 3–6 month holder cost (orange) with price, green dots marking the first cross back above after a bear market and grey dots other crosses; and the cost of coins aged 6–12 months (orange) and 12–18 months (purple), red dots death crosses, green dots golden crosses.',
          '6–12 個月線跌破 12–18 個月線＝近一年買的人比更早一批便宜，過去大致在熊底附近；重新升過＝新進場的成本拉高，過去在主升段前後。從死叉到金叉：2019 約 11 個月、2023 約 12 個月。', 'The 6–12 month line dropping below the 12–18 month line means last year\'s buyers paid less than the earlier group, historically near bear-market bottoms; crossing back above means new money is paying up, historically around the main bull leg. Death to golden took about 11 months in 2019 and 12 in 2023.',
          '兩條線比價格落後半年以上，交叉時價格往往已經走了一段；樣本只有 3–4 輪，2020 年有一次疫情後的短暫交叉。', 'Both lines lag price by six months or more, so price has usually moved a lot by the cross; only 3–4 cycles, plus a brief post-pandemic cross in 2020.'),
        now: function () { var x = (D.cycle || {}).age_cost; if (!x) return ''; var lx = x.last_cross || {}, c = x.c36; return _T((c ? '3–6 個月 ' + fmt.usd(c.cost) + '（收盤' + (c.above ? '高 ' : '低 ') + fmt.n(Math.abs(c.gap_pct), 1) + '%' + (c.since ? '，上穿 ' + c.since.days + ' 天' : '') + '）；' : '') + '6–12 個月 ' + fmt.usd(x.c612) + '、12–18 個月 ' + fmt.usd(x.c1218) + '（' + fmt.md(x.date) + '），' + (lx.kind === 'death' ? '死叉' : '金叉') + '至今 ' + x.days_since + ' 天。', (c ? '3–6 months ' + fmt.usd(c.cost) + ' (close ' + fmt.n(Math.abs(c.gap_pct), 1) + '% ' + (c.above ? 'above' : 'below') + (c.since ? ', crossed ' + c.since.days + ' days ago' : '') + '); ' : '') + '6–12 months ' + fmt.usd(x.c612) + ', 12–18 months ' + fmt.usd(x.c1218) + ' (' + fmt.md(x.date) + '), ' + x.days_since + ' days since the ' + (lx.kind === 'death' ? 'death' : 'golden') + ' cross.'); } },
      'sec': { h: h('上格是 BTC 價格，下格是賣方衰竭常數（都是對數刻度）；紅底是極端區（低於 0.13），紅圈是每次跌破後 90 天內的最低點。', 'Top: BTC price; bottom: the seller exhaustion constant (both log scale). The red band is the extreme zone (below 0.13); red circles mark the lowest point within 90 days of each break.',
          '常數很低＝價格很平靜、同時很多人在虧損，想賣的人大多已經賣了，過去多出現在熊市底部或大跌後的整理期。跌破之後再出現、但沒有更低的低點，有人當成第二個訊號點。', 'A very low reading means calm prices while many holders are underwater, so most would-be sellers have sold; historically it shows up near bear-market bottoms or in post-crash consolidations. A later low that does not undercut the first is read by some as a second signal.',
          '不是精準的底：2018/11 跌破後價格又先跌了 50%；也不只出現在週期底部（2023/8 在牛市中段）。刻度和 Glassnode 版不同，0.01 的門檻不能套。', 'Not a precise bottom: after the Nov 2018 break price fell another 50% first; nor only at cycle bottoms (Aug 2023 was mid-bull). The scale differs from Glassnode\'s, so the 0.01 line does not apply.') },
      'lthc': { h: h('BTC 價格（對數刻度），線的顏色是長期持有者（持有 ≥155 天）過去 30 天的淨增減：紅＝淨減、灰＝持平、綠＝淨增，±40 萬顆最深。', 'BTC price on a log scale, coloured by long-term holders\' (held 155+ days) net change over 30 days: red = net cut, grey = flat, green = net add, deepest at ±400K BTC.',
          '高價區出現紅色＝長期持有者趁高出貨（2024/3、2024 年底、2025/9–11 都是）；下跌後轉綠＝長期持有者不賣、籌碼沉澱。價格在漲、線卻是紅的，代表上漲一路有人供貨。', 'Red at high prices means long-term holders selling into strength (as in Mar 2024, late 2024 and Sep–Nov 2025); turning green after a drop means long-term holders are holding and supply is settling. Price rising on a red line means the rally is being met with supply.',
          '綠色不等於有人在買：幣放滿 155 天就自動算成長期持有者。這是依幣齡分組，不排除交易所；Glassnode 的吸籌趨勢評分以實體計，是不同指標。', 'Green is not buying: coins become long-term automatically at 155 days. Grouped by coin age with exchanges included; Glassnode\'s Accumulation Trend Score is entity-based and a different metric.') },
      'whale': { h: h('依地址餘額分層的 30 日淨變化（顆）。', '30-day net change by address-balance tier (BTC).', '鯊魚（100–1K）與鯨魚（1K–10K）同向增加＝大戶在累積；≥ 10K 多是交易所與託管，不算大戶買賣。', 'Sharks (100–1K) and whales (1K–10K) rising together means big holders are accumulating; ≥10K is mostly exchanges and custodians.', '一個地址不等於一個人，錢包整理會讓幣在分層之間移動。', 'One address is not one person; wallet reshuffles move coins between tiers.') },
      'sopr': { h: h('STH-SOPR＝短期持有者當天賣出的幣「賣價 ÷ 買價」；灰線是價格，標記是每一次認賠的最低點。', 'STH-SOPR = sale price ÷ purchase price for coins short-term holders sold that day; the grey line is price, markers are the low of each loss-selling episode.', '低於 1＝短期持有者賠錢賣（停損或恐慌）。價格回到前一次認賠的低點附近，SOPR 卻沒跌得更深＝願意認賠的人變少、賣壓遞減，常是階段性止跌的特徵；跌得更深＝賣壓加重。', 'Below 1 means short-term holders are selling at a loss. When price revisits a previous loss-selling low but SOPR doesn\'t dip as deep, fewer holders are willing to sell at a loss — a common sign of a local bottom forming; a deeper dip means selling is getting heavier.', '日線（CheckOnChain，晚約 1 天）：盤中的集中認賠會被同一天其他人的獲利賣出平均掉，單日下殺不一定跌破 1；隔幾天內的兩次下殺可能算成同一次。只是讀值，不是買點。', 'Daily data (CheckOnChain, about 1 day late): intraday loss bursts get averaged out by the same day\'s profit-taking, so a sharp drop may not push it below 1, and two drops a few days apart may merge into one episode. A reading, not a buy signal.') },
      'sthpnl': { h: h('短期持有者當天賣出時實現的獲利與虧損（顆，已平滑），分開兩條；灰線是價格。', 'Profit and loss short-term holders realized on coins sold (BTC, smoothed), as two separate lines; the grey line is price.', 'STH-SOPR 只是兩者合起來的比例，這張圖看是哪一邊在動：獲利線上升＝獲利了結變多，虧損線下降＝認賠變少；虧損線衝高＝集中認賠。', 'STH-SOPR only shows the two combined as a ratio; this chart shows which side moved: profit rising means more profit taking, loss falling means less loss selling, a loss spike means capitulation.', '數值是 CheckOnChain 平滑過的，單日大額轉帳也會被算進去，要看幾天才算數。只是讀值，不是買點。', 'Values are smoothed by CheckOnChain and a single large transfer can show up as a spike; wait a few days before reading much into it. A reading, not a buy signal.') },
      'p20': { h: h('MVRV 除以前一輪週期高點（只用當時已知的資料）；紅線 0.75／0.80 是出場框架的鏈上賣點。', 'MVRV divided by the previous cycle\'s peak (using only data known at the time); red lines at 0.75/0.80 are the exit framework\'s on-chain sell points.', '比值越高越接近上一輪的狂熱程度；連 5 天站上 0.75 啟動第一個鏈上賣出。', 'The higher the ratio, the closer to last cycle\'s euphoria; 5 straight days above 0.75 trigger the first on-chain sale.', '每輪頂部的 MVRV 越來越低，所以用相對前一輪的比例。', 'MVRV peaks lower each cycle, hence the ratio to the previous peak.') },
      'path': { h: h('四種長期走法（虛線，本站的預測）與已實現價格（實線）；橘色帶是頂部模型的 80% 區間。', 'Four long-term paths (dashed, our forecasts) and the realized price (solid); the orange band is the top model\'s 80% range.', '看實線貼近哪一條。每月底自動重估：起點換成月底收盤，權重依收盤離各路徑多遠做貝氏更新；收盤連 10 天超出四條路徑上下 12% 才重畫形狀。', 'See which path the solid line is tracking. Re-estimated automatically each month end: the start moves to the month-end close and weights get a Bayesian update from how far the close is from each path; shapes are re-drawn only after 10 straight closes more than 12% outside all four.', '2028 年以後只供量級參考。', 'Beyond 2028, treat it as order-of-magnitude only.') },
      'pl': { h: h('兩種看法。通道位置：0%＝歷次底部的連線、100%＝歷次頂部的連線（頂部一輪比一輪低，上緣逐輪下降），線的顏色按位置分五段：底部區 < 15%、偏低、中段、偏高、頂部區 ≥ 75%。倍數：價格除以冪律合理價（對數刻度），藍帶是歷史底部區，紅點頂、藍點底。', 'Two views. Channel: 0% is the line through past bottoms, 100% the line through past tops (falling each cycle); the line is coloured in five stages: bottom zone < 15%, low, middle, high, top zone ≥ 75%. Multiple: price divided by the power-law fair value (log scale); the blue band is the historical bottom zone, red dots tops, blue dots bottoms.', '通道位置把「每輪頂部越來越低」算進去：歷次頂部都在 75% 以上、底部都在 15% 以下。倍數越高越貴。', 'The channel builds in the shrinking tops: every past top sat above 75% and every bottom below 15%. Higher multiples mean more expensive.', '冪律每天只用當天以前的資料擬合；但通道的上下緣是用全部 4 個頂／底擬合的，歷史段是事後畫的，樣本也只有 4 輪。只作讀值。', 'The power law uses only data up to each day, but the channel edges are fitted through all four tops and bottoms, so the history is drawn after the fact, from only four cycles. Read-only.') },
      'ev-tmm': { h: h('短期持有者成本、真實市場均價與價格；虛線是用近 30 日速度外推。', 'STH cost, true market mean and price; dashed lines extrapolate the last 30 days\' pace.', '短期持有者成本上穿真實市場均價＝新資金用更高價進場，過去三次（2016、2019、2023）之後都走入牛市段。', 'STH cost crossing above the true market mean means new money is paying up; the last three crosses (2016, 2019, 2023) were followed by bull phases.', '落後指標；2019 年上穿後仍跌近六成。2026-11-04 起兩條線改用 Bitview（真實市場均價和 CheckOnChain 幾乎一致）；之前用的 bitcoin-data 真實市場均價偏高約 1.5%，下穿日記成 4/26，Bitview 是 5/18。', 'A lagging signal; after the 2019 cross price still fell about 60%. Since 2026-11-04 both lines come from Bitview (its true market mean matches CheckOnChain almost exactly); the bitcoin-data version used before runs about 1.5% higher and dated the down-cross 4/26, Bitview 5/18.') },
      'ev-sth': { h: h('價格與短期持有者成本。', 'Price and short-term holder cost.', '價格在成本之上＝短期持有者整體獲利，牛市回檔常在這條線止跌。', 'Price above cost means short-term holders are in profit; bull-market pullbacks often stop here.', '2026-11-04 起用 Bitview，晚 1 天（之前用 bitcoin-data，晚約 7 天）。', 'From 2026-11-04 the data is Bitview, 1 day late (previously bitcoin-data, about 7 days late).') },
      'ev-mom12': { h: h('價格與一年前的價格；虛線是未來每一天要比的那個價格（已知）。', 'Price and the price a year earlier; the dashed line is the year-ago price each future day will be compared with (already known).', '價格在一年前之上＝12 個月動能為正；虛線往下走，代表接下來的門檻在降低。', 'Price above its year-ago level means positive 12-month momentum; a falling dashed line means the bar is getting lower.', '門檻已知，但價格未知；「價格不動」只是假設。', 'The bar is known, the price isn\'t; "if price stays flat" is an assumption.') },
      'ev-mvrv1y': { h: h('MVRV 與自己的一年均值；上格是價格。', 'MVRV and its own 1-year average; the top pane is price.', 'MVRV 在均值之上＝估值相對一年來在擴張。', 'MVRV above its average means valuation is expanding relative to the past year.', '均值線移動慢，盤整時容易來回穿越。', 'The average moves slowly, so sideways markets cause back-and-forth crosses.') },
      'ev-rcgrowth': { h: h('實現市值 30 日變化；上格是價格。', 'Realized cap 30-day change; the top pane is price.', '> 0＝資金在流入。', 'Above zero means money is flowing in.', '不是買賣訊號。', 'Not a trade signal.') },
      'ev-xs90': { h: h('交易所供給 90 日變化；上格是價格。', 'Exchange supply 90-day change; the top pane is price.', '< 0＝幣在離開交易所，賣壓供給減少。', 'Below zero means coins are leaving exchanges, shrinking sell-side supply.', 'CoinMetrics 的地址歸屬會事後修正。', 'CoinMetrics address tags get revised later.') },
      'oc-mvrv-zscore': { h: h('MVRV Z：市值減實現市值，再除以市值的歷史標準差；紅線是四年 80 百分位。', 'MVRV Z: market cap minus realized cap, over the historical standard deviation; the red line is the 4-year 80th percentile.', '越高越貴；頂部三指標任兩項到 80 百分位進入頂部區。', 'Higher means more expensive; any two of the top-3 at the 80th percentile put us in the top zone.', '每輪頂部讀數遞減。', 'Peak readings decline each cycle.') },
      'oc-nupl': { h: h('NUPL：帳面未實現獲利占市值的比例。', 'NUPL: unrealized profit as a share of market cap.', '> 0.5 常是狂熱期，< 0 是投降期。', 'Above 0.5 is typically euphoria, below 0 capitulation.', '同上，頂部讀數一輪比一輪低。', 'As above, peak readings fall each cycle.') },
      'oc-puell-multiple': { h: h('Puell：礦工每日收入 ÷ 一年平均。', 'Puell: daily miner revenue ÷ its 1-year average.', '高＝礦工收入暴增、賣壓可能增加；低（< 0.5）常在底部。', 'High means a revenue spike and possible miner selling; low (below 0.5) often marks bottoms.', '減半會讓它一次性下台階。', 'Halvings knock it down a step.') },
      'oc-asopr': { h: h('aSOPR 7 日均：所有賣出的幣「賣價 ÷ 買價」，排除一小時內轉手。', 'aSOPR 7-day average: sale price ÷ purchase price for all coins sold, excluding those moved within an hour.', '> 1＝市場平均賣在獲利；牛市中跌回 1 常獲支撐，熊市中漲到 1 常遇壓。', 'Above 1 means coins sell at a profit on average; in bull markets dips to 1 tend to hold, in bear markets rallies to 1 tend to fail.', '日值雜訊大，所以畫 7 日均。', 'Daily values are noisy, hence the 7-day average.') },
      'oc-sth-sopr': { h: h('STH-SOPR 7 日均：短期持有者的賣價 ÷ 買價。', 'STH-SOPR 7-day average: short-term holders\' sale price ÷ purchase price.', '低於 1＝短期持有者在認賠；配合上方「認賠賣壓」圖看深度是否遞減。', 'Below 1 means short-term holders are selling at a loss; see the loss-selling chart above for whether the dips are getting shallower.', 'CheckOnChain，晚約 1 天；和 bitcoin-data 是不同資料商，數值不互相比較。', 'CheckOnChain, about 1 day late; a different vendor from bitcoin-data, so values aren\'t compared across them.') },
      'oc-lth-sopr': { h: h('LTH-SOPR 7 日均：長期持有者的賣價 ÷ 買價。', 'LTH-SOPR 7-day average: long-term holders\' sale price ÷ purchase price.', '大幅升高＝長期持有者在高價獲利了結，常見於牛市後段；跌破 1 極少見，多在深熊。', 'A big rise means long-term holders are taking profits, common late in bull markets; below 1 is rare and usually deep bear.', '單日大筆移動會讓它跳動。', 'Single large moves make it jumpy.') },
      'oc-illiquid-supply': { h: h('非流動性供給：長期不動的錢包持有的幣（百萬顆）。', 'Illiquid supply: coins in wallets that rarely spend (millions of BTC).', '持續增加＝囤幣、浮動籌碼減少；下降＝老幣回到市場。', 'Rising means hoarding and less float; falling means old coins returning to the market.', '分類依錢包行為估算，會事後修正。', 'Classified by wallet behavior and revised later.') },
      'oc-highly-liquid-supply': { h: h('高流動性供給：常在交易的錢包持有的幣（百萬顆）。', 'Highly liquid supply: coins in frequently trading wallets (millions of BTC).', '增加＝可交易的浮動籌碼變多，常伴隨派發或投機升溫。', 'Rising means more tradable float, often with distribution or speculation.', '同上，會事後修正。', 'As above, revised later.') },
      'oc-lth-mvrv-zscore': { h: h('長期持有者的 MVRV Z；紅線是 2025 頂部附近的最高值。', 'Long-term holder MVRV Z; the red line is its peak near the 2025 top.', '越接近紅線，長期持有者的帳面獲利越接近上次頂部的程度。', 'The closer to the line, the closer long-term holders\' paper profits are to last top\'s level.', '一個樣本的頂部值不是門檻。', 'One top\'s reading is not a threshold.') },
      'oc-supply-in-profit-pct': { h: h('處於獲利狀態的供給比例；紅線是 2025 頂部附近的最高值。', 'Share of supply in profit; the red line is its peak near the 2025 top.', '接近 100%＝幾乎所有人都賺錢，常在頂部附近；跌破 50% 多在熊市底部區。', 'Near 100% means almost everyone is in profit, typical near tops; below 50% is usually bear-market bottom territory.', '新高時一定接近 100%，單看它判斷不了頂。', 'At new highs it is always near 100%, so it can\'t call a top alone.') },
      'oc-lth-net-position-change-30d-btc': { h: h('長期持有者 30 日淨部位變化（顆）；紅線是 2025 頂部附近的最大賣出量。', 'Long-term holders\' 30-day net position change (BTC); the red line is their biggest selling near the 2025 top.', '大幅為負＝長期持有者在派發，常見於牛市高點；轉正＝重新囤積。', 'Deeply negative means long-term holders are distributing, typical near bull highs; turning positive means accumulation again.', '幣從短期「熟成」成長期也會讓它變正，不全是買入。', 'Coins aging from short- to long-term also push it up; not all of it is buying.') }
    };
  })();
  function rdHtml(id) {
    var r = RD[id]; if (!r) return '';
    var n = ''; try { n = r.now ? r.now() : ''; } catch (e) { n = ''; }
    var L = [_T('圖上', 'What'), _T('怎麼看', 'Reading'), _T('小心', 'Caveat')];
    return '<div class="rd">' + (n ? '<p class="rd-now"><b>' + _T('現在', 'Now') + '</b>' + esc(n) + '</p>' : '') +
      '<details class="rd-how"><summary>' + _T('怎麼讀這張圖', 'How to read this chart') + '</summary><ul>' + r.h.map(function (x, i) { return '<li><b>' + L[i] + '</b>' + esc(_T(x[0], x[1])) + '</li>'; }).join('') + '</ul></details></div>';
  }
  function attachReads(root) {
    Object.keys(RD).forEach(function (id) {
      var el = (root || document).querySelector('#c-' + id); if (!el) return;
      var nx = el.nextElementSibling; if (nx && nx.classList.contains('rd')) return;
      el.insertAdjacentHTML('afterend', rdHtml(id));
    });
  }

  /* 短期持有者認賠賣壓（2026-10-14）：STH-SOPR 低於 1＝短期持有者在賠錢賣；價格回到前次認賠低點附近時比較深度（只作讀值） */
  var SOPR_K = { easing: ['var(--up)', '賣壓遞減', 'easing'], heavier: ['var(--down)', '賣壓加重', 'heavier'], flat: ['var(--ink-3)', '持平', 'flat'] };
  function soprSay(v) {
    if (!v) return '';
    var ds = v.dips || [], last = ds[ds.length - 1], ymd = function (d) { return d.replace(/-/g, '/'); };
    var s = _T('最新 ' + fmt.n(v.value, 4) + '（' + ymd(v.date) + '）' + (v.value < 1 ? '，短期持有者正在賠錢賣，已連續 ' + v.below_run + ' 天。' : '，短期持有者整體賣在成本之上。'),
               'Latest ' + fmt.n(v.value, 4) + ' (' + ymd(v.date) + ')' + (v.value < 1 ? '; short-term holders are selling at a loss, ' + v.below_run + (v.below_run === 1 ? ' day' : ' days in a row') + '. ' : '; short-term holders are selling above cost overall. '));
    if (last) s += _T('最近一次認賠 ' + ymd(last.d) + '，最低 ' + fmt.n(last.sopr, 4) + '（價格 ' + fmt.usd(last.price) + '）' + (last.vs ? '，價格回到 ' + ymd(last.vs.d) + ' 那次附近，深度' + (last.kind === 'easing' ? '比上次淺：賣壓遞減。' : last.kind === 'heavier' ? '比上次深：賣壓加重。' : '和上次相同。') : '。'),
                      'Last loss-selling episode ' + ymd(last.d) + ', low ' + fmt.n(last.sopr, 4) + ' (price ' + fmt.usd(last.price) + ')' + (last.vs ? '; price was back near the ' + ymd(last.vs.d) + ' episode and the dip was ' + (last.kind === 'easing' ? 'shallower: selling pressure is easing.' : last.kind === 'heavier' ? 'deeper: selling pressure is heavier.' : 'the same depth.') : '.'));
    return s;
  }
  function soprPanel() {
    var v = (D.chips.viz || {}).sopr; if (!v) return '';
    return panel('span-6', _T('短期持有者認賠賣壓（STH-SOPR）', 'Short-term holder loss selling (STH-SOPR)'), _T('CheckOnChain · 晚約 1 天 · 近 1 年', 'CheckOnChain · ~1 day late · 1 year'),
      '<p class="say">' + esc(soprSay(v)) + '</p>' + legend([['STH-SOPR', 'var(--s1)'], [_T('BTC 價格（上格）', 'BTC price (top pane)'), 'var(--ink-3)'], [_T('賣壓遞減', 'Easing'), 'var(--up)'], [_T('賣壓加重', 'Heavier'), 'var(--down)']]) + '<div class="chart" id="c-sopr"></div>' + _T('<p class="note">資料：<a href="https://charts.checkonchain.com/btconchain/realised/sthsopr_indicator/sthsopr_indicator_light.html" target="_blank" rel="noopener">CheckOnChain STH-SOPR</a>（公開圖表，晚約 1 天）。</p>', '<p class="note">Data: <a href="https://charts.checkonchain.com/btconchain/realised/sthsopr_indicator/sthsopr_indicator_light.html" target="_blank" rel="noopener">CheckOnChain STH-SOPR</a> (public chart, about 1 day late).</p>'));
  }
  function drawSopr() {
    var v = (D.chips.viz || {}).sopr; if (!v) return;
    mount($('#c-sopr'), function (el) {
      var mk = (v.dips || []).map(function (d) { var k = SOPR_K[d.kind]; return { x: d.x, y: d.sopr, color: k ? k[0] : 'var(--ink-3)', label: k ? _T(k[1], k[2]) : '', below: true }; });
      var keep = el.clientWidth < 520 ? 4 : 8; mk.forEach(function (m, i) { if (i < mk.length - keep) m.label = ''; });   // 只有最近幾次寫字，避免疊在一起
      lineChart(el, { h: 240, log2: true, series: [{ name: _T('BTC 價格', 'BTC price'), data: (v.rows || []).map(function (r) { return [r[0], r[2]]; }), color: 'var(--ink-3)', w: 1.2, end: false, y2: true, fmt: fmt.usd },
        { name: 'STH-SOPR', data: (v.rows || []).map(function (r) { return [r[0], r[1]]; }), color: 'var(--s1)', w: 1.6 }],
        robust: 0.01, hbands: [{ y0: 0.9, y1: 1, color: 'var(--down-dim)' }], refs: [{ y: 1, color: 'var(--ink-3)', label: _T('1.0＝賣在成本', '1.0 = selling at cost') }], marks: mk,
        yFmt: function (x) { return x.toFixed(2); }, tipFmt: function (x) { return x.toFixed(4); }, aria: _T('短期持有者 SOPR', 'Short-term holder SOPR') });
    });
  }
  /* 短期持有者實現獲利與虧損（2026-10-23）：CheckOnChain 兩條分開的序列（BTC，已平滑），分辨 SOPR 升降是獲利了結變多還是認賠變少（只作讀值） */
  function sthPnlSay(v) {
    if (!v) return '';
    var ymd = function (d) { return d.replace(/-/g, '/'); }, sg = function (x) { return (x >= 0 ? '+' : '−') + fmt.n(Math.abs(x), 1) + '%'; }, w = v.d7;
    var s = _T('最新 ' + ymd(v.date) + '：實現獲利 ' + fmt.n(v.profit, 0) + ' 顆、實現虧損 ' + fmt.n(v.loss, 0) + ' 顆，獲利是虧損的 ' + fmt.n(v.ratio, 2) + ' 倍',
               'Latest ' + ymd(v.date) + ': realized profit ' + fmt.n(v.profit, 0) + ' BTC, realized loss ' + fmt.n(v.loss, 0) + ' BTC; profit is ' + fmt.n(v.ratio, 2) + '× loss');
    if (!w) return s + _T('。', '.');
    var up = v.ratio >= w.ratio, k = w.drive === 'profit' ? (up ? ['主要是獲利了結變多', 'mainly more profit taking'] : ['主要是獲利了結變少', 'mainly less profit taking']) : (up ? ['主要是認賠變少', 'mainly less loss selling'] : ['主要是認賠變多', 'mainly more loss selling']);
    return s + _T('（7 天前 ' + fmt.n(w.ratio, 2) + ' 倍）。和 7 天前比，獲利 ' + sg(w.profit_chg_pct) + '、虧損 ' + sg(w.loss_chg_pct) + '：' + k[0] + '。',
                  ' (' + fmt.n(w.ratio, 2) + '× 7 days ago). Versus 7 days ago, profit ' + sg(w.profit_chg_pct) + ', loss ' + sg(w.loss_chg_pct) + ': ' + k[1] + '.');
  }
  function sthPnlPanel() {
    var v = D.onchain.sth_pnl; if (!v) return '';
    return panel('span-6', _T('短期持有者實現獲利與虧損', 'Short-term holder realized profit and loss'), _T('CheckOnChain · 晚約 1 天 · 近 1 年', 'CheckOnChain · ~1 day late · 1 year'),
      '<p class="say">' + esc(sthPnlSay(v)) + '</p>' + legend([[_T('實現獲利', 'Realized profit'), 'var(--up)'], [_T('實現虧損', 'Realized loss'), 'var(--down)'], [_T('BTC 價格（上格）', 'BTC price (top pane)'), 'var(--ink-3)']]) + '<div class="chart" id="c-sthpnl"></div>' +
      _T('<p class="note">資料：<a href="https://charts.checkonchain.com/btconchain/realised/realisedpnl_bycohort_2/realisedpnl_bycohort_2_light.html" target="_blank" rel="noopener">CheckOnChain Realised Value [BTC]</a>（公開圖表，晚約 1 天）。單位是顆，數值已經 CheckOnChain 平滑（圖上沒標明視窗）；對數刻度。</p>',
         '<p class="note">Data: <a href="https://charts.checkonchain.com/btconchain/realised/realisedpnl_bycohort_2/realisedpnl_bycohort_2_light.html" target="_blank" rel="noopener">CheckOnChain Realised Value [BTC]</a> (public chart, about 1 day late). In BTC, already smoothed by CheckOnChain (window not stated); log scale.</p>'));
  }
  function drawSthPnl() {
    var v = D.onchain.sth_pnl; if (!v) return;
    mount($('#c-sthpnl'), function (el) {
      var r = v.rows || [], bt = function (x) { return fmt.n(x, 0) + ' BTC'; };
      lineChart(el, { h: 240, log: true, log2: true, series: [{ name: _T('BTC 價格', 'BTC price'), data: r.map(function (x) { return [x[0], x[3]]; }), color: 'var(--ink-3)', w: 1.2, end: false, y2: true, fmt: fmt.usd },
        { name: _T('實現獲利', 'Realized profit'), data: r.map(function (x) { return [x[0], x[1]]; }), color: 'var(--up)', w: 1.6, fmt: bt },
        { name: _T('實現虧損', 'Realized loss'), data: r.map(function (x) { return [x[0], x[2]]; }), color: 'var(--down)', w: 1.6, fmt: bt }],
        yFmt: fmt.k, tipFmt: bt, aria: _T('短期持有者實現獲利與虧損', 'Short-term holder realized profit and loss') });
    });
  }
  /* 每日淨實現損益（2026-10-18）：仿 Glassnode「Net Realized Profit/Loss」——上層價格線＋氣泡（面積＝淨值大小，綠＝淨獲利、紅＝淨認賠，粗外圈＝之前一年的 ≤2／≥98 百分位），
     下層每日柱。另有「30 日累計」模式：30 日累計 ÷ 市值，紅線＝之前 4 年第 3 百分位（週期級別的認賠），紅圈＝首次跌破。
     資料為 CoinMetrics 實現市值日變化 − 新發行，只有淨值。只作讀值，不是買賣訊號 */
  var nplMode = 'day', nplRng = 180;
  var NPL_RNG = { day: [[90, '近 3 個月', '3M'], [180, '近半年', '6M'], [365, '近 1 年', '1Y']], cum: [[365, '近 1 年', '1Y'], [1460, '近 4 年', '4Y'], [0, '2015 起', 'Since 2015']] };
  function nplB(m) { return (m >= 0 ? '+' : '−') + '$' + (Math.abs(m) >= 1000 ? fmt.n(Math.abs(m) / 1e3, 2) + 'B' : fmt.n(Math.abs(m), 0) + 'M'); }
  function nplPct(v) { return (v >= 0 ? '+' : '−') + fmt.n(Math.abs(v), 2) + '%'; }
  function nplSay(n) {
    if (!n) return '';
    var ymd = function (d) { return d.replace(/-/g, '/'); };
    if (nplMode === 'cum') {   // 2026-11-04：觸發線改成「之前 4 年最大 30 日淨獲利 × −1/4」（舊規則 4 年第 3 百分位的觸發在 trig_old）
      var c = n.cum30 || {}, T = c.trig || [], g = c.green_max, mn = c.min_since_top, tx = mn ? dnOf(mn.top) : null, cyc = T.filter(function (t) { return tx != null && t.x >= tx; }), tg = T[T.length - 1];
      var ge = g ? ' (' + ymd(g.date) + ', ' + nplPct(g.pct_mcap) + ')' : '';
      return _T('30 日累計 ' + nplB(c.usd_m) + '（市值的 ' + nplPct(c.pct_mcap) + '，4 年第 ' + fmt.n(c.pct_4y, 0) + ' 百分位）；觸發線＝之前 4 年最大 30 日淨獲利' + (g ? '（' + ymd(g.date) + '，' + nplPct(g.pct_mcap) + '）' : '') + '的 1/4，取負，在 ' + nplPct(c.thr_pct_mcap) + '。' + (cyc.length ? ymd(mn.top) + ' 週期頂部之後觸發 ' + cyc.length + ' 次：' + cyc.map(function (t) { return ymd(t.date) + '（' + fmt.usd(t.price) + '）'; }).join('、') + '。' : (tg ? '上一次觸發是 ' + ymd(tg.date) + '（' + fmt.usd(tg.price) + '）。' : '') + (mn ? ymd(mn.top) + ' 週期頂部之後還沒有觸發。' : '')),
        '30-day total ' + nplB(c.usd_m) + ' (' + nplPct(c.pct_mcap) + ' of market cap, 4-year percentile ' + fmt.n(c.pct_4y, 0) + '); the trigger line is minus a quarter of the largest 30-day net profit of the prior 4 years' + ge + ', at ' + nplPct(c.thr_pct_mcap) + '.' + (cyc.length ? ' Since the ' + ymd(mn.top) + ' cycle top it has triggered ' + cyc.length + ' time' + (cyc.length > 1 ? 's' : '') + ': ' + cyc.map(function (t) { return ymd(t.date) + ' (' + fmt.usd(t.price) + ')'; }).join(', ') + '.' : (tg ? ' The last trigger was ' + ymd(tg.date) + ' (' + fmt.usd(tg.price) + ').' : '') + (mn ? ' It has not triggered since the ' + ymd(mn.top) + ' cycle top.' : '')));
    }
    var s7 = n.sum7_usd_m, p7 = n.sum7_prev_usd_m, ls = n.loss_spike_last;
    var tr = s7 < 0 ? ['近一週整體轉為認賠賣出', 'the past week turned to net loss selling'] : p7 <= 0 ? ['前一週以認賠為主，這週轉為獲利賣出', 'the prior week was net loss selling; this week is net profit'] : s7 < p7 * 0.6 ? ['獲利了結明顯降溫', 'profit taking has clearly cooled'] : s7 > p7 * 1.4 ? ['獲利了結增溫', 'profit taking is heating up'] : ['獲利了結大致持平', 'profit taking is roughly flat'];
    return _T('最新 ' + ymd(n.date) + ' ' + nplB(n.usd_m) + '（近一年第 ' + fmt.n(n.rank_1y, 0) + ' 百分位）。近 7 日合計 ' + nplB(s7) + '，前 7 日 ' + nplB(p7) + '：' + tr[0] + '。' + (ls ? '最近一次明顯認賠（近一年最極端的 2%）是 ' + ymd(ls.date) + ' ' + nplB(ls.usd_m) + '。' : ''),
      'Latest ' + ymd(n.date) + ' ' + nplB(n.usd_m) + ' (1-year percentile ' + fmt.n(n.rank_1y, 0) + '). Past 7 days ' + nplB(s7) + ', prior 7 days ' + nplB(p7) + ': ' + tr[1] + '.' + (ls ? ' The last clear loss spike (most extreme 2% of the past year) was ' + ymd(ls.date) + ' ' + nplB(ls.usd_m) + '.' : ''));
  }
  function nplLegend() {
    return nplMode === 'cum' ? legend([[_T('BTC 價格（對數）', 'BTC price (log)'), 'var(--ink)'], [_T('30 日累計淨獲利', '30-day net profit'), 'var(--up)'], [_T('30 日累計淨認賠', '30-day net loss'), 'var(--down)'], [_T('觸發線：4 年最大獲利 × −1/4', 'Trigger: −¼ × 4-year max profit'), 'var(--down)'], [_T('首次觸發', 'First trigger'), 'var(--s2)']])
      : legend([[_T('BTC 價格', 'BTC price'), 'var(--ink)'], [_T('淨獲利', 'Net profit'), 'var(--up)'], [_T('淨認賠', 'Net loss'), 'var(--down)']]);
  }
  function nplSegs() {
    var b = function (attr, v, on, z, e) { return '<button aria-pressed="' + on + '" data-' + attr + '="' + v + '">' + _T(z, e) + '</button>'; };
    return '<span style="display:inline-flex;gap:8px;flex-wrap:wrap;margin-left:auto"><span class="seg">' + b('m', 'day', nplMode === 'day', '每日', 'Daily') + b('m', 'cum', nplMode === 'cum', '30 日累計', '30-day total') + '</span><span class="seg">' +
      NPL_RNG[nplMode].map(function (o) { return b('v', o[0], o[0] === nplRng, o[1], o[2]); }).join('') + '</span></span>';
  }
  function nplPanel() {
    var n = D.onchain.npl; if (!n || !n.rows) return '';
    return panel('span-12', _T('每日淨實現損益', 'Daily net realized profit/loss'), _T('CoinMetrics 推算 · 晚約 1 天', 'Derived from CoinMetrics · ~1 day late'),
      '<p class="say" id="npl-say">' + esc(nplSay(n)) + '</p><div id="npl-lg">' + nplLegend() + '</div><div class="chart" id="c-npl"></div>' +
      _T('<p class="note">算法：實現市值（市值 ÷ MVRV）當日變化減去當天新挖出的幣，等於當天移動的幣「賣價 − 上次移動價」的淨和；和 Glassnode 的 Net Realized Profit/Loss 對照，方向與大小相符。只有淨值；每日模式的粗外圈＝在之前一年最極端的 2%；30 日累計模式以市值百分比顯示，紅線是之前 4 年最大 30 日淨獲利的 1/4（取負；逐日計算，只用當時已知資料）。2026-11-04 起改用這條線：獲利與認賠的幅度每輪都變小（最大獲利約 15% → 10% → 5.75%），舊的「之前 4 年第 3 百分位」拿上一輪熊市的大認賠當標準，這一輪兩次低點都沒觸發。新規則是看過這一輪結果才定的，代價是 2022 年那次由 6/16 提早到 5/20，之後還再跌約 40%。只作讀值。</p>',
         '<p class="note">Method: the daily change in realized cap (market cap ÷ MVRV) minus newly mined coins equals the net of “sale price − last-moved price” for coins moved that day; it matches Glassnode\'s Net Realized Profit/Loss in direction and size. Net only; in daily mode a thick ring marks the most extreme 2% of the prior year; the 30-day mode is shown as % of market cap, and the red line is minus a quarter of the largest 30-day net profit of the prior 4 years (computed day by day from data known at the time). This line replaced the prior-4-year 3rd percentile on 2026-11-04: both profit and loss swings shrink every cycle (largest profit about 15% → 10% → 5.75%), so the old line measured against the previous bear market\'s heavy losses and missed both lows of this cycle. The new rule was chosen after seeing this cycle; the cost is that 2022\'s trigger moves from 6/16 to 5/20, after which price still fell about 40%. Reading only.</p>'),
      '<span id="npl-segs" style="display:contents">' + nplSegs() + '</span>');
  }
  function nplSync() { var n = D.onchain.npl; $('#npl-say').textContent = nplSay(n); $('#npl-lg').innerHTML = nplLegend(); $('#npl-segs').innerHTML = nplSegs(); drawNpl($('#c-npl')); }
  function drawNpl(el) {
    var n = D.onchain.npl; if (!n || !n.rows || !el) return;
    var cum = nplMode === 'cum', src = cum ? ((n.cum30 || {}).rows || []) : n.rows; if (src.length < 2) return;
    var xl = src[src.length - 1][0], r = nplRng ? src.filter(function (x) { return x[0] > xl - nplRng; }) : src;
    var W = Math.max(280, el.clientWidth), sm = W < 520;
    var ML = 8, MR = 58, MT = 12, H1 = sm ? 190 : 250, G = 18, H2 = sm ? 84 : 112, MB = 22, Ht = MT + H1 + G + H2 + MB, pw = W - ML - MR;
    var x0 = r[0][0], x1 = r[r.length - 1][0], X = function (d) { return ML + (d - x0) / Math.max(1, x1 - x0) * pw; };
    var lg = cum && (x1 - x0) > 500, Tf = function (v) { return lg ? Math.log10(v) : v; };
    var ps = r.map(function (x) { return Tf(x[1]); }), plo = Math.min.apply(null, ps), phi = Math.max.apply(null, ps), pd = (phi - plo) * 0.14 || 1; plo -= pd; phi += pd;
    var YP = function (v) { return MT + (1 - (Tf(v) - plo) / (phi - plo)) * H1; };
    var val = function (x) { return x[2]; }, vals = r.map(val).concat(cum ? r.map(function (x) { return x[3]; }) : []);
    var mx = Math.max.apply(null, vals.map(Math.abs)) || 1, st2 = niceStep(mx, 2), top2 = Math.ceil(mx / st2) * st2;
    var yc = MT + H1 + G + H2 / 2, YB = function (v) { return yc - v / top2 * (H2 / 2); }, rmax = sm ? 11 : 18;
    var col = function (v) { return v >= 0 ? 'var(--up)' : 'var(--down)'; }, s = '', q;
    if (lg) { for (q = Math.ceil(plo); q <= phi; q++) [1, 3].forEach(function (m) { var v = m * Math.pow(10, q - (m === 3 ? 1 : 0)); if (Tf(v) < plo || Tf(v) > phi) return; s += '<line class="gl" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + YP(v).toFixed(1) + '" y2="' + YP(v).toFixed(1) + '"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (YP(v) + 3.5).toFixed(1) + '">' + fmt.k(v) + '</text>'; }); }
    else { var pst = niceStep(phi - plo, 4); for (q = Math.ceil(plo / pst) * pst; q <= phi; q += pst) s += '<line class="gl" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + YP(q).toFixed(1) + '" y2="' + YP(q).toFixed(1) + '"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (YP(q) + 3.5).toFixed(1) + '">' + fmt.k(q) + '</text>'; }
    var axl = function (v) { return cum ? (v > 0 ? '+' : '−') + +Math.abs(v).toFixed(1) + '%' : (v > 0 ? '+' : '−') + (Math.abs(v) >= 1000 ? +(Math.abs(v) / 1e3).toFixed(1) + 'B' : Math.round(Math.abs(v)) + 'M'); };
    for (q = -top2; q <= top2 + 1e-9; q += st2) s += '<line class="' + (Math.abs(q) < 1e-9 ? 'base' : 'gl') + '" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + YB(q).toFixed(1) + '" y2="' + YB(q).toFixed(1) + '"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (YB(q) + 3.5).toFixed(1) + '">' + (Math.abs(q) < 1e-9 ? '0' : axl(q)) + '</text>';
    if (!cum) r.map(function (x, i) { return i; }).sort(function (a, b) { return Math.abs(r[b][2]) - Math.abs(r[a][2]); }).forEach(function (i) {   // 大泡先畫，小泡疊在上面
      var x = r[i], ex = x[3] != null && (x[3] <= 2 || x[3] >= 98);
      s += '<circle cx="' + X(x[0]).toFixed(1) + '" cy="' + YP(x[1]).toFixed(1) + '" r="' + Math.max(1.5, Math.sqrt(Math.abs(x[2]) / mx) * rmax).toFixed(1) + '" fill="' + col(x[2]) + '" fill-opacity=".26" stroke="' + col(x[2]) + '" stroke-opacity="' + (ex ? '.95' : '.4') + '" stroke-width="' + (ex ? 1.8 : 0.8) + '"/>';
    });
    s += '<path d="' + r.map(function (x, i) { return (i ? 'L' : 'M') + X(x[0]).toFixed(1) + ' ' + YP(x[1]).toFixed(1); }).join('') + '" fill="none" stroke="var(--ink)" stroke-width="1.3" stroke-linejoin="round"/>';
    var bw = Math.max(cum ? 0.6 : 1, pw / r.length * (cum ? 0.9 : 0.72));
    r.forEach(function (x) { var y = YB(Math.max(0, x[2])), h = Math.max(0.6, Math.abs(YB(x[2]) - YB(0))); s += '<rect x="' + (X(x[0]) - bw / 2).toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + h.toFixed(1) + '" fill="' + col(x[2]) + '" opacity="' + (cum ? '.7' : '.8') + '"/>'; });
    if (cum) {
      s += '<path d="' + r.map(function (x, i) { return (i ? 'L' : 'M') + X(x[0]).toFixed(1) + ' ' + YB(x[3]).toFixed(1); }).join('') + '" fill="none" stroke="var(--down)" stroke-width="1.2"/>';
      ((n.cum30 || {}).trig || []).filter(function (t) { return t.x >= x0 - 3 && t.x <= x1; }).forEach(function (t, k) {   // 標籤上下交錯，貼邊時改靠左／靠右，避免重疊或被切掉
        var cx = X(t.x), an = cx < ML + 24 ? 'start' : cx > ML + pw - 24 ? 'end' : 'middle', ty = YP(t.price) + (k % 2 ? -10 : 17);
        s += '<circle cx="' + cx.toFixed(1) + '" cy="' + YP(t.price).toFixed(1) + '" r="5" fill="none" stroke="var(--s2)" stroke-width="2"/><text class="ax" x="' + cx.toFixed(1) + '" y="' + ty.toFixed(1) + '" text-anchor="' + an + '" style="fill:var(--s2)">' + t.date.slice(0, 7) + '</text>';
      });
    }
    var ticks = [], yrs = (x1 - x0) > 500;
    r.forEach(function (x) { var t = new Date(x[0] * 864e5), prev = ticks.length ? ticks[ticks.length - 1] : null; var key = yrs ? t.getUTCFullYear() : t.getUTCFullYear() * 12 + t.getUTCMonth(); if (!prev || prev.k !== key) ticks.push({ k: key, x: x[0], t: t }); });
    ticks = ticks.slice(1); var every = Math.ceil(ticks.length / (sm ? 4 : 8));
    ticks.forEach(function (o, i) { if (i % every) return; var t = o.t; s += '<text class="ax" x="' + X(o.x).toFixed(1) + '" y="' + (Ht - 6) + '" text-anchor="middle">' + (yrs ? t.getUTCFullYear() : _T((t.getUTCMonth() + 1) + ' 月', ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][t.getUTCMonth()])) + '</text>'; });
    s += '<line id="npl-x" x1="0" x2="0" y1="' + MT + '" y2="' + (Ht - MB) + '" stroke="var(--ink-3)" stroke-dasharray="2 3" visibility="hidden"/>';
    el.innerHTML = '<svg width="' + W + '" height="' + Ht + '" viewBox="0 0 ' + W + ' ' + Ht + '" role="img" aria-label="' + esc(_T('每日淨實現損益', 'Daily net realized profit/loss')) + '">' + s + '</svg>';
    var sv = el.querySelector('svg'), vl = el.querySelector('#npl-x');
    sv.addEventListener('pointermove', function (ev) {
      var bx = ev.clientX - sv.getBoundingClientRect().left, d = x0 + (bx - ML) / pw * (x1 - x0), i = 0;
      r.forEach(function (x, j) { if (Math.abs(x[0] - d) < Math.abs(r[i][0] - d)) i = j; });
      var x = r[i], px = X(x[0]).toFixed(1); vl.setAttribute('x1', px); vl.setAttribute('x2', px); vl.setAttribute('visibility', 'visible');
      var row = function (c, k, v) { return '<div class="r"><i style="background:' + c + '"></i><span>' + k + '</span><b>' + v + '</b></div>'; };
      showTip(ev.clientX, ev.clientY, '<div class="t">' + fmt.date(x[0]) + '</div>' + row('var(--ink)', _T('BTC 價格', 'BTC price'), fmt.usd(x[1])) +
        (cum ? row(col(x[2]), _T('30 日累計', '30-day total'), nplB(x[4]) + ' · ' + nplPct(x[2])) + row('var(--down)', _T('觸發線', 'Trigger line'), nplPct(x[3])) + row('', _T('4 年百分位', '4-year percentile'), fmt.n(x[5], 1))
             : row(col(x[2]), _T('淨實現損益', 'Net realized P/L'), nplB(x[2])) + (x[3] != null ? row('', _T('近一年百分位', '1-year percentile'), fmt.n(x[3], 0)) : '')));
    });
    sv.addEventListener('pointerleave', function () { vl.setAttribute('visibility', 'hidden'); hideTip(); });
  }
  function whalePanel() {
    var W = D.onchain.whales; if (!W || !W.cohorts) return '';
    var co = {}; W.cohorts.forEach(function (x) { co[x.key] = x; });
    var big30 = (co['100_1k'] || {}).chg30 + (co['1k_10k'] || {}).chg30, big7 = (co['100_1k'] || {}).chg7 + (co['1k_10k'] || {}).chg7;
    var say = '<p class="say">' + _T('大戶（100–10K BTC 地址）30 日合計 <b>' + cK(big30, true) + ' 顆</b>、7 日 ' + cK(big7, true) + ' 顆：' + (big30 > 0 && big7 >= 0 ? '這個月在累積，最近一週也沒有停。' : big30 > 0 ? '這個月在累積，但最近一週轉為賣出，留意是否反轉。' : big7 > 0 ? '這個月在減持，最近一週開始買回。' : '這個月在減持，最近一週仍在賣。'),
      'Big holders (100–10K BTC addresses) <b>' + cK(big30, true) + ' BTC</b> over 30 days and ' + cK(big7, true) + ' BTC over 7 days: ' + (big30 > 0 && big7 >= 0 ? 'accumulating this month, and still at it this week.' : big30 > 0 ? 'accumulating this month, but they turned sellers this week — watch for a reversal.' : big7 > 0 ? 'distributing this month, but buying back this week.' : 'distributing this month and still selling this week.')) + '</p>';
    var tb = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>' + _T('地址餘額分層', 'Balance tier') + '</th><th class="num">' + _T('持幣', 'Holdings') + '</th><th class="num mh">7d</th><th class="num">30d</th><th class="num mh">90d</th><th class="num">' + _T('本段以來', 'This leg') + '</th></tr></thead><tbody>' +
      W.cohorts.slice().reverse().map(function (x) { var rd = cohRead(x), col = function (v, h) { return '<td class="num' + (h ? ' mh' : '') + '" style="color:var(--' + (v > 0 ? 'up' : v < 0 ? 'down' : 'ink-3') + ')">' + cK(v, true) + '</td>'; };
        return '<tr class="has-rd"><td><b>' + esc(_T(COH[x.key][0], COH[x.key][1])) + '</b></td><td class="num">' + (LANG === 'en' ? fmt.n(x.btc / 1e6, 2) + 'M' : fmt.n(x.btc / 1e4, 0) + '萬') + '</td>' + col(x.chg7, 1) + col(x.chg30) + col(x.chg90, 1) + col(x.since_leg) + '</tr>' + rdRow(rd, MQ560.matches ? 4 : 6); }).join('') + '</tbody></table></div>';
    var note = '<p class="note">' + _T('資料：Bitview（Bitcoin Research Kit）依地址餘額分層的每日持幣量（2011 起；百分位用近 4 年）。2026-11-04 起取代被 Cloudflare 擋下的 BitInfoCharts。限制：一個地址不等於一個人，交易所與 ETF 託管用少數大地址集中保管客戶的幣，錢包整理也會讓幣在分層之間移動，所以單日的大跳動常是整理而非買賣（例如交易所大量提幣，幣從大地址分散到小地址，看起來像大戶在賣、散戶在買）；看 30 日以上的方向比較可靠。「本段以來」＝自價格版「短週期」目前這一段的起點（' + (W.leg_start || '—') + '）。只作讀值，不連動出場規則。',
      'Data: Bitview (Bitcoin Research Kit) daily holdings by address-balance tier (since 2011; percentiles use the last 4 years), replacing BitInfoCharts, which now blocks automated access, from 2026-11-04. Limits: one address is not one person; exchanges and ETF custodians hold client coins in a few large addresses, and wallet reshuffles move coins between tiers, so single-day jumps are often housekeeping, not trading (a wave of exchange withdrawals, for example, spreads coins from big addresses to small ones and looks like whales selling to retail) — the direction over 30+ days is more reliable. “This leg” = since the start of the current short-cycle leg on the Price page (' + (W.leg_start || '—') + '). Readings only; not linked to the exit rules.') + '</p>';
    return panel('span-12', _T('鯨魚與大戶動向', 'Whale and big-holder activity'), (W.src || 'BitInfoCharts') + ' · ' + fmt.md(W.date), say + tb + '<div class="panel-h" style="margin-top:14px"><h2>' + _T('30 日淨變化（顆）', '30-day net change (BTC)') + '</h2>' + legend([[_T('鯊魚 100–1K', 'Sharks 100–1K'), 'var(--s4)'], [_T('鯨魚 1K–10K', 'Whales 1K–10K'), 'var(--s1)'], [_T('≥10K', '≥10K'), 'var(--s3)']]) + '</div><div class="chart" id="c-whale"></div>' + note);
  }
  function drawWhale(el) {
    var r = (D.onchain.whales || {}).rows || [], f = function (i) { return r.map(function (x) { return [x[0], x[i] == null ? null : x[i] / 1e3]; }); };
    lineChart(el, { h: 220, series: [{ name: _T('鯊魚 100–1K', 'Sharks 100–1K'), data: f(1), color: 'var(--s4)' }, { name: _T('鯨魚 1K–10K', 'Whales 1K–10K'), data: f(2), color: 'var(--s1)' }, { name: '≥10K', data: f(3), color: 'var(--s3)', w: 1.4 }], refs: [{ y: 0, color: 'var(--ink-3)' }], yFmt: function (x) { return x + 'K'; }, tipFmt: function (x) { return (x > 0 ? '+' : '') + x.toFixed(1) + 'K BTC'; }, aria: _T('大戶 30 日淨變化', 'Big-holder 30-day net change') });
  }

  /* 資料健康（2026-10-12）：管線錯誤（meta.errors）與各來源資料日期。超過預期延遲的標 ⚠；全部正常時只顯示一行 */
  function healthHtml() {
    var bd = D.meta.bar_date, age = function (d) { return d ? Math.max(0, dnOf(bd) - dnOf(String(d).slice(0, 10))) : null; };   // 快照（場外 USDT、清算熱力圖）在收盤後隔天 00:06 UTC 拍，不算負的落後
    var oc = D.onchain.metrics || {}, etf = (D.flows.etf || []).filter(function (r) { return !r.partial; }), tm = D.cycle.tidemark || {}, fl = (D.chips || {}).flow || {};
    var src = [   // [名稱, 資料日期, 可接受的最大延遲（天）]
      [_T('價格（Kraken）', 'Price (Kraken)'), bd, 0],
      [_T('頂部三指標（CoinMetrics）', 'Top-3 indicators (CoinMetrics)'), D.cycle.p6_date, 2],
      [_T('持有者成本（' + ((oc['sth-realized-price'] || {}).source || 'bitcoin-data') + '）', 'Holder cost basis (' + ((oc['sth-realized-price'] || {}).source || 'bitcoin-data') + ')'), (oc['sth-realized-price'] || {}).date, (oc['sth-realized-price'] || {}).source === 'Bitview' ? 2 : 7],
      [_T('短期成本與真實市場均價（' + (fl.sth_vs_tmm || {}).source + '）', 'STH cost and true market mean (' + (fl.sth_vs_tmm || {}).source + ')'), (fl.sth_vs_tmm || {}).date, (fl.sth_vs_tmm || {}).source === 'Bitview' ? 2 : 7],
      [_T('短期持有者獲利（' + ((fl.sth_in_profit_pct || {}).source || 'bitcoin-data') + '）', 'STH in profit (' + ((fl.sth_in_profit_pct || {}).source || 'bitcoin-data') + ')'), (fl.sth_in_profit_pct || {}).date, 3],
      [_T('流動性供給（bitcoin-data）', 'Liquid supply (bitcoin-data)'), (oc['illiquid-supply'] || {}).date, 3],
      [_T('ETF 流量（The Block）', 'ETF flows (The Block)'), (etf[etf.length - 1] || {}).d, 4],
      ['Tidemark', tm.price_date, 2],
      // 2026-10-21：補上 10/14 之後新增、原本沒列的來源
      [_T('短期持有者 SOPR（CheckOnChain）', 'STH-SOPR (CheckOnChain)'), (((D.chips || {}).viz || {}).sopr || {}).date, 2],
      [_T('淨實現損益（CoinMetrics）', 'Net realized P/L (CoinMetrics)'), (D.onchain.npl || {}).date, 2],
      [_T('籌碼分布 URPD（bitcoin-data）', 'URPD (bitcoin-data)'), ((D.chips || {}).urpd || {}).date, 2],
      [_T('美債殖利率（FRED）', 'Treasury yields (FRED)'), (((D.flows.fred || {}).DGS10) || {}).last_date, 4]
    ];
    if (D.onchain.whales) src.push([_T('鯨魚分層（' + (D.onchain.whales.src || 'BitInfoCharts') + '）', 'Whale tiers (' + (D.onchain.whales.src || 'BitInfoCharts') + ')'), D.onchain.whales.date, 2]);   // 2026-10-21 起暫停，沒有資料就不列
    if (D.flows.stables) src.push([_T('穩定幣（DefiLlama）', 'Stablecoins (DefiLlama)'), D.flows.stables.date, 2]);
    if ((D.chips || {}).cohort) src.push([_T('長短期持有者籌碼（CheckOnChain／推算）', 'LTH/STH supply split (CheckOnChain / estimate)'), D.chips.cohort.now_date || D.chips.cohort.date, 3]);   // 2026-10-27 起
    if (D.onchain.sth_pnl) src.push([_T('短期持有者實現損益（CheckOnChain）', 'STH realized P/L (CheckOnChain)'), D.onchain.sth_pnl.date, 2]);   // 2026-10-23 起；第一次跑管線前沒有資料就不列
    // 2026-11-04 自我檢查：10/27 之後新增的圖表也列進來（原本只有管線錯誤那一行會提示）。欄位整個沒有＝本日未取得，同樣標 ⚠
    var p3 = D.flows.premium3 || {};
    [[_T('賣方衰竭常數（CheckOnChain）', 'Seller exhaustion (CheckOnChain)'), D.onchain.sec, 2],
     [_T('實現獲利 ÷ 虧損（CheckOnChain）', 'Realized profit ÷ loss (CheckOnChain)'), D.onchain.rpl, 2],
     [_T('表觀需求（CheckOnChain HODL Waves）', 'Apparent demand (CheckOnChain HODL Waves)'), D.onchain.ad, 2],
     [_T('長期持有者已實現虧損（Bitview）', 'LTH realized loss (Bitview)'), D.onchain.lthrl, 2],
     [_T('價格 × 長期持有者（bitcoin-data）', 'Price × LTH (bitcoin-data)'), D.onchain.lth_color, 7],
     [_T('週線多空分數', 'Weekly bull/bear score'), D.cycle.regime, 8],
     [_T('晨昏指數', 'Dawn–Dusk Index'), D.cycle.dawn, 8],
     [_T('永續對現貨（OKX）', 'Perp vs spot (OKX)'), p3.perp, 1],
     // 2026-11-09 市場情緒：CFTC 是週二持倉、週五公布，最晚約晚 10 天；維基百科瀏覽量晚 1–2 天
     [_T('對趨勢的信心（Bitview）', 'Confidence in the trend (Bitview)'), D.onchain.sthconf, 2],
     [_T('恐懼貪婪（alternative.me）', 'Fear & Greed (alternative.me)'), D.flows.fng_hist, 1],
     [_T('維基百科瀏覽量（Wikimedia）', 'Wikipedia page views (Wikimedia)'), D.flows.wiki, 3],
     [_T('CME 持倉（CFTC）', 'CME positioning (CFTC)'), D.flows.cot, 11],
     [_T('看跌／看漲比（Deribit）', 'Put/call ratio (Deribit)'), D.deriv.pcr, 1]
    ].forEach(function (x) { src.push([x[0], (x[1] || {}).date, x[2]]); });
    src.push([_T('場外 USDT 溢價（OKX）', 'OTC USDT premium (OKX)'), (p3.usdt || {}).ts, 1]);
    src.push([_T('清算熱力圖（推算）', 'Liquidation heatmap (estimate)'), (D.deriv.liq_heat || {}).asof, 1]);
    src.push([_T('每日多空清算量（Coinalyze）', 'Daily liquidations (Coinalyze)'), (D.deriv.liq_vol || {}).date, 2]);
    var rows = src.map(function (x) { var a = age(x[1]); return { name: x[0], date: x[1], age: a, bad: x[1] == null || a > x[2], max: x[2] }; });
    var errs = D.meta.errors || [], bad = rows.filter(function (r) { return r.bad; }), notesOld = N && N.stale;
    var n = bad.length + errs.length + (notesOld ? 1 : 0);
    var head = n ? '⚠ ' + _T('資料狀態：' + n + ' 項需要留意', 'Data status: ' + n + ' item(s) need attention') : '✓ ' + _T('資料狀態：各來源都在預期時間內', 'Data status: every source is within its expected delay');
    var body = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>' + _T('來源', 'Source') + '</th><th class="num">' + _T('資料日期', 'Data date') + '</th><th class="num">' + _T('落後', 'Lag') + '</th></tr></thead><tbody>' +
      rows.map(function (r) { return '<tr><td>' + (r.bad ? '⚠ ' : '') + esc(r.name) + '</td><td class="num">' + (r.date ? fmt.md(String(r.date).slice(0, 10)) : _T('未取得', 'missing')) + '</td><td class="num"' + (r.bad ? ' style="color:var(--warn)"' : '') + '>' + (r.age == null ? '—' : r.age + _T(' 天', 'd')) + _T('（上限 ' + r.max + '）', ' (max ' + r.max + ')') + '</td></tr>'; }).join('') + '</tbody></table></div>' +
      (notesOld ? '<p class="note">⚠ ' + _T('今天的判讀還沒更新，顯示的是 ' + fmt.md(N.date) + ' 那一期。', 'Today’s commentary has not been updated yet; showing the ' + fmt.md(N.date) + ' edition.') + '</p>' : '') +
      (errs.length ? '<p class="note">' + _T('管線錯誤（該項在頁面上顯示「本日未取得」）：', 'Pipeline errors (those items show as “not available today”):') + '</p><ul class="note">' + errs.map(function (e) { return '<li>' + esc(e) + '</li>'; }).join('') + '</ul>' : '') +
      '<p class="note">' + _T('「落後」＝資料日期比收盤日早幾天。bitcoin-data 部分序列本身就晚 5–6 天，所以上限較寬。', '“Lag” = days between the data date and the close date. Some bitcoin-data series are themselves 5–6 days behind, hence the wider limit.') + '</p>';
    return '<details class="health' + (n ? ' warn' : '') + '"><summary>' + head + '</summary>' + body + '</details>';
  }

  /* 多家永續資金費率（2026-10-12）：以未平倉加權；缺時退回 Deribit */
  function fundNow() { var fm = D.deriv.funding_multi || {}; return fm.weighted_now != null ? fm.weighted_now : (D.deriv.deriv || {}).funding_ann; }
  function fundVenues() {
    var v = (D.deriv.funding_multi || {}).venues; if (!v) return _t('年化 ');
    return _T('以未平倉加權（', 'Open-interest weighted (') + Object.keys(v).map(function (k) { return k + ' ' + fmt.pct(v[k].now, 1) + (v[k].avg7 != null ? _T('，7 日均 ', ', 7d avg ') + fmt.pct(v[k].avg7, 1) : ''); }).join(_T('；', '; ')) + _T('）。年化 ', '). ');
  }
  /* 金額（十億美元）：中文「億美元」、英文「$…B」 */
  function usdB(x, signed) { if (x == null) return '—'; var s = signed ? (x > 0 ? '+' : x < 0 ? '−' : '') : '', a = signed ? Math.abs(x) : x; return s + (LANG === 'en' ? '$' + fmt.n(a, a >= 100 ? 0 : 1) + 'B' : fmt.n(a * 10, 0) + ' 億美元'); }
  /* 資金版新增讀值：穩定幣、Coinbase 溢價、ETF 換算 BTC、恐懼貪婪 */
  function flInterp2(s7) {
    var it = [], sc = D.flows.stables, cp = D.flows.cb_premium, fg = D.flows.fear_greed, c = D.price.bar.c, mi = D.onchain.mining || {}, etf = (D.flows.etf || []).filter(function (r) { return !r.partial; }).slice(-7);
    if (sc && sc.chg30_pct != null) it.push([_T('穩定幣供給', 'Stablecoin supply'), usdB(sc.usd_b), _T('30 日 ' + usdB(sc.chg30_usd_b, true) + '（' + fmt.pct(sc.chg30_pct, 2) + '，落在 2021 年以來第 ' + fmt.n(sc.pct30, 0) + ' 百分位）：', '30-day ' + usdB(sc.chg30_usd_b, true) + ' (' + fmt.pct(sc.chg30_pct, 2) + ', ' + ord(sc.pct30) + ' percentile since 2021): ') +
      (sc.pct30 >= 80 ? _T('場外美元快速增加，潛在買盤充沛。', 'dollars on the sidelines are growing fast — plenty of potential buying power.') : sc.pct30 <= 20 ? _T('場外美元在萎縮，潛在買盤減少。', 'sidelined dollars are shrinking — less potential buying power.') : _T('場外美元溫和變化，不是現在的主要推力。', 'sidelined dollars are changing modestly; not a main driver right now.')) + _T('穩定幣是加密市場裡等待進場的資金。', ' Stablecoins are the cash waiting to be deployed in crypto.'), sc.pct30 >= 80 ? 'pos' : sc.pct30 <= 20 ? 'neg' : 'neu']);
    // 2026-11-04：Coinbase 溢價的讀值只留在「三地溢價」（premSay），這裡不再重複一列
    if (etf.length >= 5 && mi.btc_day) {
      var span = dnOf(etf[etf.length - 1].d) - dnOf(etf[0].d) + 1, btc = s7 * 1e6 / c, mined = mi.btc_day * span, r = btc / mined;
      it.push([_T('ETF 換算 BTC', 'ETF flows in BTC'), cK(btc, true), _T('近 7 個完整交易日淨' + (btc >= 0 ? '買進' : '賣出') + '約 ' + cK(Math.abs(btc)) + ' 顆（以今天收盤換算），同期（' + span + ' 天）礦工新挖約 ' + cK(mined) + ' 顆，', 'Over the last 7 full trading days ETFs net ' + (btc >= 0 ? 'bought' : 'sold') + ' about ' + cK(Math.abs(btc)) + ' BTC (at today’s close), while miners produced about ' + cK(mined) + ' BTC over the same ' + span + ' days, ') +
        (btc >= 0 ? _T('是新產出的 ' + fmt.n(r, 1) + ' 倍' + (r >= 1 ? '：ETF 吸收的量超過新供給。' : '：還不足以吃掉新供給。'), fmt.n(r, 1) + '× new supply' + (r >= 1 ? ' — ETFs are absorbing more than is being mined.' : ' — not enough to absorb new supply.')) : _T('等於額外多了 ' + fmt.n(-r, 1) + ' 倍新產出的賣壓。', 'adding selling pressure equal to ' + fmt.n(-r, 1) + '× new supply.')), btc >= mined ? 'pos' : btc < 0 ? 'neg' : 'neu']);
    }
    if (fg) it.push([_T('恐懼貪婪指數', 'Fear & Greed'), fg.value, band(fg.value, [25, 45, 55, 75], [_T('25 以下：極度恐懼，歷來常是中短期低點附近', 'Below 25: extreme fear, historically often near short- to mid-term lows'), _T('25–45：恐懼', '25–45: fear'), _T('45–55：中性', '45–55: neutral'), _T('55–75：貪婪', '55–75: greed'), _T('75 以上：極度貪婪，追高風險升高', '75+: extreme greed, chasing gets riskier')]) +
      _T('；7 天前 ' + fg.d7 + '、30 日平均 ' + fmt.n(fg.avg30, 0) + '，近一年第 ' + fmt.n(fg.pct_1y, 0) + ' 百分位。情緒是反向參考，不是買賣訊號。', '; ' + fg.d7 + ' a week ago, 30-day avg ' + fmt.n(fg.avg30, 0) + ', ' + ord(fg.pct_1y) + ' percentile of the past year. Sentiment is a contrarian reference, not a trading signal.'), fg.value < 25 ? 'pos' : fg.value > 75 ? 'warn' : 'neu']);
    return it;
  }
  function hashRibRead() {
    var h = D.onchain.hash_ribbons; if (!h) return null;
    return [_T('算力帶', 'Hash Ribbons'), fmt.n(h.ratio, 3), h.capitulation ? _T('30 日均算力低於 60 日均（已 ' + h.state_days + ' 天）：礦工投降期，歷來多出現在底部附近；等它回到 1 以上，才是傳統上的「恢復」訊號。', 'The 30-day hashrate average is below the 60-day (' + h.state_days + ' days): miner capitulation, historically common near bottoms; the classic signal comes when it recovers above 1.')
      : _T('30 日均算力高於 60 日均 ' + fmt.pct((h.ratio - 1) * 100, 1) + '（已 ' + h.state_days + ' 天）：礦工狀態健康。上次由投降期恢復在 ' + fmt.md(h.last_cross) + '；這類恢復歷來常在底部附近，但不是每次都準。', 'The 30-day hashrate average is ' + fmt.pct((h.ratio - 1) * 100, 1) + ' above the 60-day (' + h.state_days + ' days): miners are healthy. The last recovery from capitulation was on ' + fmt.md(h.last_cross) + '; such recoveries have often come near bottoms, but not every time.'), h.capitulation ? 'warn' : 'neu'];
  }
  function flowCharts() {
    var sc = D.flows.stables, cp = D.flows.cb_premium; if (!sc && !cp) return '';
    // 2026-11-04 每個指標只有一個家：獨立的 Coinbase 溢價圖併進「三地溢價」的美國現貨（舊連結 #flows/cbp 由 ALIAS 導過去）
    return sc ? panel('span-12', _T('穩定幣總供給', 'Total stablecoin supply'), 'DefiLlama · ' + _T('近 2 年 · 十億美元', 'last 2 years · USD billions'), '<div class="chart" id="c-stab"></div>') : '';
  }
  function drawFlowCharts() {
    var sc = D.flows.stables, cp = D.flows.cb_premium;
    if (sc) mount($('#c-stab'), function (el) { lineChart(el, { h: 200, series: [{ name: _T('穩定幣', 'Stablecoins'), data: sc.rows, color: 'var(--s4)', area: true }], yFmt: function (x) { return '$' + x.toFixed(0) + 'B'; }, tipFmt: function (x) { return '$' + x.toFixed(1) + 'B'; }, aria: _T('穩定幣總供給', 'Total stablecoin supply') }); });

  }

  /* ---------------- Views ---------------- */
  var V = {};
  // 2026-11-05 使用者要求：鏈上是重點，移到第 3（頭版、消息之後）；出場框架離現在還遠，移到第 8（往期之前）。資金排在衍生品前面
  var ROUTES = [
    ['overview', _t('頭版'), _t('今天的比特幣'), 'M4 5h16v14H4zM8 9h8M8 13h5', 'FRONT PAGE'],
    ['news', _t('消息'), _t('新聞與解讀'), 'M5 4h11l3 3v13H5zM9 9h6M9 13h6M9 17h4', 'THE BRIEF'],
    ['cycle', _t('週期'), _t('離頂部還多遠'), 'M12 3a9 9 0 1 0 9 9M12 7a5 5 0 1 0 5 5M12 12h9', 'CYCLE'],   // 2026-11-06 使用者要求：週期放在鏈上前面
    ['onchain', _t('鏈上'), _t('持有者與籌碼'), 'M7 7h4v4H7zM13 13h4v4h-4zM11 9h4M9 11v4', 'ON-CHAIN'],
    ['market', _t('價格'), _T('行情、均線與季節性', 'Price action, averages and seasonality'), 'M4 19V9m5 10V5m5 14v-7m5 7V8', 'PRICE'],
    ['flows', _t('資金'), _T('ETF、需求與宏觀', 'ETFs, demand and macro'), 'M4 7h16M4 12h10M4 17h6', 'FLOWS · MACRO'],
    ['deriv', _t('衍生品'), _T('波動率、槓桿與選擇權', 'Volatility, leverage and options'), 'M3 17c3-8 6-8 9 0s6 8 9 0', 'DERIVATIVES'],
    ['exit', _t('出場框架'), _t('何時分批賣'), 'M4 20h4v-4h4v-4h4V8h4V4', 'EXIT PLAN'],
    ['archive', _t('往期'), _t('過去的判讀與戰績'), 'M4 6h16M4 12h16M4 18h10', 'ARCHIVE'],
    ['method', _t('方法'), _t('資料與限制'), 'M12 3v18M3 12h18M6 6l12 12', 'METHOD']
  ];

  V.overview = function () {
    var c = D.price.bar, ex = D.exit.status, cm = D.cycle.cm, pl = D.cycle.powerlaw || {}, tm = D.cycle.tidemark || {}, p6 = D.cycle.p6 || {};
    var news = (N && N.news || []).slice().sort(function (a, b) { return (b.weight || 0) - (a.weight || 0); });
    var wd = (LANG === 'en' ? ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'] : ['日', '一', '二', '三', '四', '五', '六'])[new Date(D.meta.bar_date + 'T12:00:00Z').getUTCDay()];
    // 標題裡的數字（連同緊接的單位：%、億、萬、倍、基點、K 等）一律用號外紅
    var hl = esc(N ? N.headline : '').replace(/(\d{1,2}\/\d{1,2}(?!\d)|[+\-−]?\d[\d,.]*(?:\s?(?:%|億|萬|千|兆|倍|個基點|基點|bp|K|M|B)(?![A-Za-z]))?)/g, '<em>$1</em>');
    var watch = (N && N.watch || []).map(function (w) { var dd = (w.value / c.c - 1) * 100; return '<div><span class="k">' + esc(w.label) + '</span><span class="v ' + (dd >= 0 ? 'up' : 'dn') + '">' + fmt.pct(dd, 1) + '</span><span class="px">' + fmt.usd(w.value) + '</span><span class="n">' + esc(w.note) + '</span></div>'; }).join('');
    var front = _t('<section class="front" id="front"><div class="dateline"><b>號外</b><span>DAYBREAK No.') + ('00' + (N ? N.edition : 0)).slice(-3) + '</span><hr><span>' + D.meta.bar_date.replace(/-/g, '.') + _t('（') + wd + _t('）收盤版</span></div>') +
      '<h2 class="reveal">' + hl + '</h2>' + megaHtml(c) +
      '<div class="front-foot"><div class="dek"><div class="stamp"><span class="chip flare"><i></i>' + esc(N ? N.stance.label : '—') + '</span><span class="chip">' + (N ? esc(N.stance.short) : '') + '</span>' + stageChip() + '</div><p>' + esc(N ? N.summary : '') + '</p></div><div class="watch">' + watch + '</div></div></section>';
    var newsBlock = news.length ? _t('<div class="sec-h"><h2>今日要聞</h2><span class="en">The Brief</span><hr><a href="#news">全部 ') + news.length + _t(' 則 →</a></div><div class="news-front">') + newsItem(news[0], true) + '<div class="news-side">' + news.slice(1, 4).map(function (n, i) { return newsItem(n, false, 0, true); }).join('') + '</div></div>' : '';
    var ev = (N && N.events || []).map(function (e) { var dd = dnOf(e.date) - dnOf(D.meta.bar_date); return '<div class="event"><span class="d">' + e.date.slice(5).replace('-', '/') + '</span><span>' + esc(e.label) + '</span><span class="in' + (dd === 1 ? ' now' : '') + '">' + (dd > 1 ? dd - 1 + _t(' 天後') : dd === 1 ? _t('今天') : _t('已過')) + '</span></div>'; }).join('');
    var plan = _t('<div class="sec-h"><h2>今天該做什麼</h2><span class="en">The Plan</span><hr>') + staleTag() + '</div><div class="grid">' +
      panel('span-7', _t('行動與要盯的價位'), _t('依出場框架 · 非投資建議'), actionsHtml()) + panel('span-5', _t('今天變了什麼'), _t('相對上一期'), changesHtml()) + '</div>';
    var zhNote = ZH_ONLY ? '<p class="note" style="margin:0">The English edition of today’s written commentary (headline, news and plan) is not published yet, so those parts are shown in Chinese. All data and readings are in English.</p>' : '';
    // 2026-11-04 頭版重排：結論（號外＋立場）→ 今天該做什麼／變了什麼 → 今日發現 → 要聞 → 數據（原本行動清單排在發現與要聞之後，約第 4–5 屏）
    // 2026-11-04 訊號總表取代「今日數據」6 張卡：同樣的數字加上市場階段、週線多空、頂部雷達，分組排在一起
    var board = boardHtml();
    return zhNote + front + tapeHtml() + healthHtml() + plan + viewsHtml() +
      (board ? _T('<div class="sec-h"><h2>訊號總表</h2><span class="en">The Board</span><hr>', '<div class="sec-h"><h2>Signal board</h2><span class="en">The Board</span><hr>') + '<span class="src">' + _t('依當日數值套固定門檻自動產生 · 非投資建議') + '</span></div>' + board : '') +
      findingsHtml() + newsBlock +
      '<div class="grid">' + panel('span-12', _t('離出場線還多遠'), _t('以 ') + fmt.md(D.meta.bar_date) + _t(' 收盤計 · 對數刻度'), '<div class="runway" id="c-runway"></div>') +
      panel('span-7', _t('價格近一年'), _t('CoinMetrics 每 7 天'), '<div class="chart" id="c-ov-px"></div>') +
      panel('span-5', _t('接下來的日期'), '', '<div class="events">' + ev + '</div>') + '</div>';
  };
  V.overview.after = function () {
    bindMega();
    mount($('#c-runway'), function (el) { el.innerHTML = runwaySvg(Math.max(280, el.clientWidth)); });
    var hist = D.price.history || [], cut = hist[hist.length - 1][0] - 400;
    mount($('#c-ov-px'), function (el) { lineChart(el, { h: 250, series: [{ name: _t('價格'), data: hist.filter(function (p) { return p[0] >= cut; }), color: 'var(--s2)', area: true }], refs: [{ y: D.price.ma.sma200, color: 'var(--ink-3)', label: _t('200 日均線 ') + fmt.k(D.price.ma.sma200), below: true }], tipFmt: fmt.usd, aria: _t('近一年價格') }); });
  };

  V.news = function () {
    var news = (N && N.news || []);
    var rs = '<div class="grid" style="margin-top:28px">' + panel('span-12', _t('權威研報怎麼看'), _t('Glassnode · The Block · K33 · Coinbase Institutional 等'), researchHtml(), staleTag()) + '</div>';
    if (!news.length) return _t('<p class="err">今天還沒有整理好的消息。</p>') + rs;
    var cats = ['*'].concat(news.map(function (n) { return n.cat; }).filter(function (c, i, a) { return a.indexOf(c) === i; }));
    var cnt = function (k) { return news.filter(function (n) { return n.impact === k; }).length; };
    return _t('<div class="news-sum"><div><span class="note">偏多</span><b style="color:var(--up)">') + ('0' + cnt('bull')).slice(-2) + _t('</b></div><div><span class="note">偏空</span><b style="color:var(--down-ink)">') + ('0' + cnt('bear')).slice(-2) + _t('</b></div><div><span class="note">中性</span><b>') + ('0' + cnt('neutral')).slice(-2) + '</b></div></div>' +
      _t('<div class="filters" id="nf" role="group" aria-label="分類">') + cats.map(function (c, i) { return '<button type="button" aria-pressed="' + (i === 0) + '" data-c="' + esc(c) + '">' + esc(c === '*' ? _t('全部') : catT(c)) + '</button>'; }).join('') + '</div>' +
      _t('<div class="news-grid" id="ng"></div><p class="note">每則消息都查證過發布日期；「解讀」說明它對比特幣的意義，並對照本站的數據。消息只作參考，不改變任何出場規則。</p>') + rs;
  };
  V.news.after = function () {
    var news = (N && N.news || []).slice().sort(function (a, b) { return (b.weight || 0) - (a.weight || 0) || (b.time > a.time ? 1 : -1); });
    function draw(cat) { $('#ng').innerHTML = news.filter(function (n) { return cat === '*' || n.cat === cat; }).map(function (n, i) { return '<article class="news-card"><div class="news-meta"><span class="cat">' + esc(catT(n.cat)) + '</span>' + impChip(n.impact) + '<span>' + esc(n.time.slice(5).replace('-', '/')) + '</span></div><h3>' + esc(n.title) + _t('</h3><div class="read-box"><b class="lbl">解讀</b>') + esc(n.read) + _t('</div><div class="src-link">來源：<a href="') + esc(n.url) + '" target="_blank" rel="noopener">' + esc(n.source) + '</a></div>' + (n.module ? '<a class="go" href="#' + n.module + _t('">看相關數據 →</a>') : '') + '</article>'; }).join(''); }
    draw('*');
    $('#nf').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; this.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); draw(b.getAttribute('data-c')); });
  };

  /* 上下兩格：上＝BTC 價格（對數刻度）、下＝指標，共用時間軸與十字線，不疊成雙 y 軸。
     2026-11-04 自我檢查：週線多空分數、賣方衰竭常數、實現獲利 ÷ 虧損、表觀需求原本各寫一份約 20 行的同樣骨架，抽成這一個。
     o.rows：[[日, …]]；o.pi：價格在第幾欄；o.hp／o.hs：[手機, 桌面] 上下兩格高度；o.scale(C) 回傳下格的 Y 函式；
     o.body(C) 畫下格（格線、柱、線）；o.over(C) 畫在最上層（標記點）；o.tip(p, C) 回傳 { t: 標題, rows: 指標列, dots: 下格的點 } */
  function twoPane(el, o) {
    var W = Math.max(280, el.clientWidth), rg = rangeOf(el, { series: [{ data: o.rows.map(function (r) { return [r[0], 1]; }) }] }, W), R_ = rg && rg.x0 != null ? o.rows.filter(function (r) { return r[0] >= rg.x0; }) : o.rows, sm = W < 520, ML = 8, MR = 58, MT = 16, gap = 28, MB = 24, hp = o.hp[sm ? 0 : 1], hs = o.hs[sm ? 0 : 1], LR = o.lr ? o.lr(sm) : 0;
    var Ht = MT + hp + gap + hs + LR + MB, pw = W - ML - MR, ys0 = MT + hp + gap, L = Math.log10;
    var x0 = R_[0][0], x1 = R_[R_.length - 1][0], X = function (t) { return ML + (t - x0) / (x1 - x0 || 1) * pw; };
    var pv = R_.map(function (r) { return r[o.pi]; }), pl = L(Math.min.apply(null, pv)), ph = L(Math.max.apply(null, pv)), pp = (ph - pl) * 0.05 || 0.1; pl -= pp; ph += pp;
    var Yp = function (v) { return MT + (1 - (L(v) - pl) / (ph - pl)) * hp; };
    var C = { W: W, sm: sm, ML: ML, pw: pw, MT: MT, hp: hp, hs: hs, ys0: ys0, yb: ys0 + hs, Ht: Ht, X: X, Yp: Yp, L: L, tx: axText, rows: R_ };
    C.gl = function (y, lab, cls, col) { return '<line class="' + (cls || 'gl') + '" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/>' + (lab == null ? '' : axText(ML + pw + 8, y + 3.5, lab).replace('class="ax"', 'class="ax"' + (col ? ' fill="' + col + '"' : ''))); };
    C.Ys = o.scale(C);
    var s = '';
    [1, 10, 100, 1e3, 2e3, 5e3, 1e4, 2e4, 5e4, 1e5, 2e5].forEach(function (t) {
      if (L(t) < pl || L(t) > ph) return;
      if ((t === 2e3 || t === 5e3 || t === 2e4 || t === 5e4 || t === 2e5) && ph - pl > 2.2) return;   // 跨好幾個數量級時只標 10 的次方
      s += C.gl(Yp(t), t >= 1000 ? fmt.k(t) : '$' + t);
    });
    var cid = 'cp' + Math.random().toString(36).slice(2, 8), clip = '<defs><clipPath id="' + cid + '"><rect x="' + ML + '" y="0" width="' + pw + '" height="' + Ht + '"/></clipPath></defs>';   // 選了 1 年／3 年時，下格用的是完整資料，超出左緣的部分剪掉
    s += clip + '<g clip-path="url(#' + cid + ')">' + o.body(C) + '</g>';
    s += axText(ML, MT - 5, _T('BTC 價格（對數刻度）', 'BTC price (log scale)')) + axText(ML, ys0 - 9, o.label);
    var ya = new Date(x0 * 864e5).getUTCFullYear() + 1, yz = new Date(x1 * 864e5).getUTCFullYear(), every = Math.max(1, Math.ceil(46 * (yz - ya + 1) / pw));   // 年份標籤至少隔 46px
    for (var y = ya; y <= yz; y++) { var xx = X(Date.UTC(y, 0, 1) / 864e5); if ((yz - y) % every === 0 && xx > ML + 14 && xx < ML + pw - 14) s += axText(xx, Ht - 6, String(y), 'middle'); }
    s += '<path class="ln" d="M' + R_.map(function (r) { return X(r[0]).toFixed(1) + ',' + Yp(r[o.pi]).toFixed(1); }).join('L') + '" stroke="var(--ink-2)" stroke-width="1.3"/>';
    var pdot = function (r) { return '<circle cx="' + X(r[0]).toFixed(1) + '" cy="' + Yp(r[o.pi]).toFixed(1) + '" r="3.5" fill="var(--ink-2)" stroke="var(--deck)" stroke-width="2"/>'; };
    s += (o.over ? '<g class="now-g" clip-path="url(#' + cid + ')">' + o.over(C) + '</g>' : '') + pdot(R_[R_.length - 1]);
    s += '<line class="xh" x1="0" x2="0" y1="' + MT + '" y2="' + C.yb + '" visibility="hidden"/><g class="hdots"></g><rect class="hit" x="' + ML + '" y="' + MT + '" width="' + pw + '" height="' + (C.yb - MT) + '"/>';
    el.innerHTML = (rg ? rg.html : '') + svgEl(W, Ht, s, o.aria);
    bindRng(el, rg);
    animateLines(el);
    var svg = el.querySelector('svg'), xh = svg.querySelector('.xh'), dots = svg.querySelector('.hdots'), hit = svg.querySelector('.hit');
    function move(ev) {
      var r = svg.getBoundingClientRect(), xv = x0 + ((ev.clientX - r.left) * W / r.width - ML) / pw * (x1 - x0), p = R_[bisect(R_, xv)], q = o.tip(p, C);
      xh.setAttribute('x1', X(p[0])); xh.setAttribute('x2', X(p[0])); xh.setAttribute('visibility', 'visible');
      dots.innerHTML = (q.dots || '') + pdot(p);
      showTip(ev.clientX, ev.clientY, '<div class="t">' + (q.t || fmt.date(p[0])) + '</div>' + q.rows + '<div class="r"><i style="background:var(--ink-2)"></i><span>' + _T('BTC 價格', 'BTC price') + '</span><b>' + fmt.usd(p[o.pi]) + '</b></div>' + (q.after || ''));
    }
    hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', function () { xh.setAttribute('visibility', 'hidden'); dots.innerHTML = ''; hideTip(); });
  }
  function tipRow1(col, name, val) { return '<div class="r"><i style="background:' + col + '"></i><span>' + name + '</span><b>' + val + '</b></div>'; }
  function dot1(x, y, col) { return '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="4" fill="' + col + '" stroke="var(--deck)" stroke-width="2"/>'; }

  /* 週線多空分數（2026-11-03 使用者要求；參考的指標不公開，這是我們自己的版本）：
     六項已有訊號各除以自己的歷史中位數取 tanh、平均後 ×6（−6 到 +6）；連續 4 週在另一邊才算翻轉。上下兩格共用時間軸。只作讀值 */
  var REG_LAB = { d200: ['200 日均線位置', 'Price vs 200-day MA'], mom12: ['12 個月動能', '12-month momentum'], mvrv1y: ['MVRV 對一年均值', 'MVRV vs its 1-year mean'], rc30: ['實現市值 30 日', 'Realized cap, 30 days'], xs90: ['交易所供給 90 日', 'Exchange supply, 90 days'], rpl: ['實現獲利 ÷ 虧損（90 天）', 'Realized profit ÷ loss (90d)'] };
  function regRaw(c) {
    if (c.raw == null) return '—';
    if (c.key === 'mom12') return fmt.pct((Math.exp(c.raw) - 1) * 100, 0);
    if (c.key === 'xs90') return fmt.pct(-c.raw * 100, 2);
    if (c.key === 'rpl') return fmt.n(Math.pow(10, c.raw), 2);
    return fmt.pct(c.raw * 100, c.key === 'rc30' ? 2 : 1);
  }
  /* 2026-11-05 使用者要求：同樣是牛／熊，要看得出到了哪個階段（參考 CryptoQuant 牛熊週期圖、冪律衰減通道震盪的分段配色）。
     五段冷→熱共用一組顏色 --stg0..4（app.css，已驗色）；門檻用本站自己的歷史定，只作讀值、不連動倉位 */
  var STG_C = ['var(--stg0)', 'var(--stg1)', 'var(--stg2)', 'var(--stg3)', 'var(--stg4)'];
  var REG_STG = [['極熊', 'Extreme bear'], ['熊', 'Bear'], ['初牛', 'Early bull'], ['牛', 'Bull'], ['過熱', 'Overheated']];
  var REG_HOT = 4, REG_EARLY = 26;   // ≥ +4 過熱（歷輪頂部 3.6–4.9）、≤ −4 極熊（2015、2018 底 −5.4、−5.5）；初牛＝空方滿 26 週後翻多的頭 26 週（含還沒確認翻轉、但分數已轉正的週）
  function regSegs() {
    var x = D.cycle.regime, seg = [{ t: -1e9, dir: x.rows[0][1] >= 0 ? 1 : -1, prev: 0 }];
    (x.flips || []).forEach(function (f) { var p = seg[seg.length - 1], t = dnOf(f.date); seg.push({ t: t, dir: f.dir, prev: p.t < 0 ? 0 : Math.round((t - p.t) / 7) }); });
    return seg;
  }
  function regStages() {
    var x = D.cycle.regime, seg = regSegs(), j = 0;
    return x.rows.map(function (r) {
      while (j + 1 < seg.length && seg[j + 1].t <= r[0]) j++;
      var g = seg[j], v = r[1], w = (r[0] - g.t) / 7;
      if (v >= REG_HOT) return 4; if (v <= -REG_HOT) return 0; if (v < 0) return 1;
      if (g.dir > 0) return w < REG_EARLY && g.prev >= REG_EARLY ? 2 : 3;
      return w >= REG_EARLY ? 2 : 3;
    });
  }
  function stgItems(names) { return names.map(function (n, i) { return [_T(n[0], n[1]), STG_C[i], 'box']; }); }
  function regStageItem() {
    var x = D.cycle.regime, st = regStages(), k = st[st.length - 1], seg = regSegs(), g = seg[seg.length - 1], n = REG_STG[k];
    var why = k === 2 ? _T('分數轉正，' + (g.dir > 0 ? '翻多第 ' + (x.weeks + 1) + ' 週，前一段空方持續 ' + g.prev + ' 週（滿 26 週才算熊市後的初牛）' : '空方已持續 ' + Math.round((dnOf(x.date) - g.t) / 7) + ' 週、還沒確認翻多') + '。', 'Score positive; ' + (g.dir > 0 ? 'week ' + (x.weeks + 1) + ' of the bull regime, after ' + g.prev + ' bearish weeks (26+ makes it an early bull after a real bear)' : 'bearish for ' + Math.round((dnOf(x.date) - g.t) / 7) + ' weeks, flip not yet confirmed') + '.')
      : k === 4 ? _T('分數 ≥ +' + REG_HOT + '：六項幾乎全面偏多，歷輪頂部前後都到過這裡（也會停留好幾個月）。', 'Score ≥ +' + REG_HOT + ': nearly all six inputs bullish; every past top passed through here (often for months).')
      : k === 3 ? _T('分數為正，多方已超過 26 週，或是短暫回檔後再翻多。', 'Score positive, past the first 26 bull weeks or resuming after a short dip.')
      : k === 0 ? _T('分數 ≤ −' + REG_HOT + '：六項幾乎全面偏空，2015、2018 年的底部都在這一段。', 'Score ≤ −' + REG_HOT + ': nearly all inputs bearish; the 2015 and 2018 bottoms sat here.')
      : _T('分數為負。', 'Score negative.');
    return [_T('目前階段', 'Stage now'), _T(n[0], n[1]), why + _T('顏色：≥ +4 過熱、熊市後轉正的頭 26 週初牛、其餘正值牛、負值熊、≤ −4 極熊。', ' Colours: ≥ +4 overheated, first 26 positive weeks after a real bear early bull, other positive bull, negative bear, ≤ −4 extreme bear.'), k >= 4 ? 'warn' : k === 2 ? 'pos' : 'neu'];
  }
  function regSay() {
    var x = D.cycle.regime, it = [], F = x.flips || [], ymd = ymdS, sg = function (v) { return (v > 0 ? '+' : v < 0 ? '−' : '') + fmt.n(Math.abs(v), 2); };
    var side = x.regime > 0 ? _T('多方', 'bullish') : _T('空方', 'bearish');
    it.push(regStageItem());
    it.push([_T('多空分數', 'Regime score'), sg(x.value),
      _T(side + '（' + (x.since ? ymd(x.since) + ' 起，第 ' + (x.weeks + 1) + ' 週' : '') + '）；一週前 ' + sg(x.prev) + '、四週前 ' + sg(x.prev4) + '。範圍 −6 到 +6，絕對值小於 1 屬於弱勢，方向容易反覆。' + (x.pending ? '最近 ' + x.pending + ' 週已在另一邊，再 ' + (4 - x.pending) + ' 週就算翻轉。' : ''),
        'Regime ' + side + (x.since ? ' since ' + ymd(x.since) + ' (week ' + (x.weeks + 1) + ')' : '') + '; ' + sg(x.prev) + ' a week ago, ' + sg(x.prev4) + ' four weeks ago. Range −6 to +6; below 1 in size is weak and prone to flip.' + (x.pending ? ' The last ' + x.pending + ' week(s) sit on the other side; ' + (4 - x.pending) + ' more and it flips.' : '')), 'neu']);
    var C = x.comps || [], pos = C.filter(function (c) { return c.val != null && c.val >= 0.15; }), neg = C.filter(function (c) { return c.val != null && c.val <= -0.15; }), flat = C.filter(function (c) { return c.val != null && Math.abs(c.val) < 0.15; });
    var lst = function (a) { return a.map(function (c) { var L = REG_LAB[c.key] || [c.key, c.key]; return _T(L[0], L[1]) + ' ' + regRaw(c); }).join(_T('、', ', ')); };   // 2026-11-04：管線多一項時不讓整個週期版壞掉
    it.push([_T('六項拆解', 'Six inputs'), pos.length + ' / ' + neg.length,
      _T((pos.length ? '偏多：' + lst(pos) + '。' : '') + (neg.length ? '偏空：' + lst(neg) + '。' : '') + (flat.length ? '持平：' + lst(flat) + '。' : ''),
        (pos.length ? 'Bullish: ' + lst(pos) + '. ' : '') + (neg.length ? 'Bearish: ' + lst(neg) + '. ' : '') + (flat.length ? 'Flat: ' + lst(flat) + '.' : '')), 'neu']);
    var up = F.filter(function (f) { return f.dir > 0 && f.r52 != null; }), ok = up.filter(function (f) { return f.r52 > 0; }), bad = up.filter(function (f) { return f.r52 <= 0; }), short = F.filter(function (f) { return f.dir > 0 && f.weeks != null && f.weeks < 12; });
    if (up.length) it.push([_T('過去翻多之後', 'After past bullish flips'), ok.length + ' / ' + up.length,
      _T('2013 年以來翻多、已滿 52 週的 ' + up.length + ' 次中，' + ok.length + ' 次一年後價格較高' + (bad.length ? '；' + bad.map(function (f) { return secYm(f.date) + ' ' + fmt.pct(f.r52, 0); }).join('、') + ' 是錯的' : '') + (short.length ? '；' + short.length + ' 次不到 12 週就翻回空方（' + short.map(function (f) { return secYm(f.date); }).join('、') + '）' : '') + '。只代表過去。',
        'Of ' + up.length + ' bullish flips since 2013 with a full year since, ' + ok.length + ' saw a higher price a year later' + (bad.length ? '; wrong: ' + bad.map(function (f) { return secYm(f.date) + ' ' + fmt.pct(f.r52, 0); }).join(', ') : '') + (short.length ? '; ' + short.length + ' turned back bearish within 12 weeks (' + short.map(function (f) { return secYm(f.date); }).join(', ') + ')' : '') + '. The past only.'), 'neu']);
    return it;
  }
  function regTable() {
    var F = (D.cycle.regime.flips || []).slice().reverse(), c = function (v) { return v == null ? '<span class="note">' + _T('未滿', 'n/a') + '</span>' : '<span style="color:var(--' + (v >= 0 ? 'up' : 'down') + ')">' + fmt.pct(v, 0) + '</span>'; };
    return '<div class="tbl-wrap" style="margin-top:12px"><table class="tbl"><thead><tr><th>' + _T('翻轉', 'Flip') + '</th><th>' + _T('方向', 'To') + '</th><th class="num hide-sm">' + _T('價格', 'Price') + '</th><th class="num">' + _T('持續', 'Lasted') + '</th><th class="num hide-sm">26 ' + _T('週後', 'w later') + '</th><th class="num">52 ' + _T('週後', 'w later') + '</th></tr></thead><tbody>' +
      F.map(function (f) { return '<tr><td><span class="num">' + f.date.replace(/-/g, '/') + '</span></td><td><span style="color:var(--' + (f.dir > 0 ? 'up' : 'down') + ')">' + (f.dir > 0 ? _T('翻多', 'Bull') : _T('翻空', 'Bear')) + '</span></td><td class="num hide-sm">' + fmt.usd(f.price) + '</td><td class="num">' + (f.weeks != null ? f.weeks + _T(' 週', 'w') : _T('進行中', 'ongoing')) + '</td><td class="num hide-sm">' + c(f.r26) + '</td><td class="num">' + c(f.r52) + '</td></tr>'; }).join('') + '</tbody></table></div>';
  }
  function regPanel() {
    var x = (D.cycle || {}).regime; if (!x || !x.rows) return '';
    return panel('span-12', _T('週線多空分數', 'Weekly regime score'), _T('六項合成 · 2013 起 · 每週 · ' + fmt.md(x.date), 'Six inputs · since 2013 · weekly · ' + fmt.md(x.date)),
      interpHtml(regSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)']].concat(stgItems(REG_STG))) + '<div class="chart" id="c-regime"></div>' + regTable() +
      '<p class="note">' + _T('六項：200 日均線位置、12 個月動能、MVRV 對一年均值、實現市值 30 日變化、交易所供給 90 日變化（減少算多）、實現獲利 ÷ 虧損 90 天平均。每項除以自己 2013 年起的典型大小（中位數）再壓到 −1 到 +1，平均後乘 6。連續 4 週在零軸另一邊才算翻轉。都是網站已有的資料，不另外抓。',
        'Inputs: price vs the 200-day MA, 12-month momentum, MVRV vs its 1-year mean, 30-day realized-cap change, 90-day exchange-supply change (falling counts as bullish), and the 90-day realized profit ÷ loss. Each is divided by its typical size since 2013 (median), squashed to −1…+1, averaged and multiplied by 6. A flip needs 4 straight weeks on the other side of zero. All inputs are already on the site.') + '</p>');
  }
  function drawRegime(el) {
    var x = (D.cycle || {}).regime; if (!x || !el) return;
    var R_ = x.rows, mx = Math.max(3, Math.ceil(Math.max.apply(null, R_.map(function (r) { return Math.abs(r[1]); })))), st = regStages(), sk = {};
    R_.forEach(function (r, i) { sk[r[0]] = st[i]; });
    var col = function (r) { return STG_C[sk[r[0]] != null ? sk[r[0]] : (r[1] >= 0 ? 3 : 1)]; };
    twoPane(el, { rows: R_, pi: 2, hp: [110, 150], hs: [140, 180], label: _T('多空分數（每週）', 'Regime score (weekly)'), aria: _T('BTC 價格與週線多空分數', 'BTC price and weekly regime score'),
      scale: function (C) { return function (v) { return C.ys0 + (1 - (v + mx) / (2 * mx)) * C.hs; }; },
      body: function (C) {
        var s = '';
        for (var g = -mx; g <= mx; g += mx > 4 ? 2 : 1) s += C.gl(C.Ys(g), (g > 0 ? '+' : '') + g, g ? 'gl' : 'base');
        var bw = Math.max(1, C.pw / C.rows.length * 0.8), z0 = C.Ys(0);   // C.rows＝目前時間範圍內的列
        R_.forEach(function (r) { var cx = C.X(r[0]), yv = C.Ys(r[1]); s += '<rect x="' + (cx - bw / 2).toFixed(1) + '" y="' + Math.min(z0, yv).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(0.5, Math.abs(yv - z0)).toFixed(1) + '" fill="' + col(r) + '"/>'; });
        return s;
      },
      tip: function (p) { var n = REG_STG[sk[p[0]]] || ['', '']; return { t: _T('週至 ', 'Week to ') + fmt.date(p[0]), rows: tipRow1(col(p), _T('多空分數', 'Regime score') + (n[0] ? _T('（' + n[0] + '）', ' (' + n[1] + ')') : ''), (p[1] > 0 ? '+' : '') + fmt.n(p[1], 2)) }; } });
  }


  /* 長期路徑的每月重估紀錄（2026-11-03 起自動，pipeline/path_review.py）：公開最近一次的計算過程與包絡檢查。規則沿用舊日報 P3／P4／P26 (a) */
  var PATH_EN = { '直接修復': 'Direct recovery', '淺回檔': 'Shallow pullback', '基準雙底': 'Base-case double bottom', '延後新低': 'Delayed new low' };
  function pathReviewHtml() {
    var M = D.cycle.model, R = (M.reviews || []).filter(function (r) { return r.kind === 'monthly'; }), r = R[R.length - 1], f = M.fan || {}, ks = Object.keys(M.weights), ym = function (s) { return s.slice(0, 7).replace('-', '/'); };
    var fanTxt = f.run != null ? _T('包絡檢查：收盤目前連續 ' + f.run + ' 天超出四條路徑上下 12%（今天的範圍 ' + fmt.k(f.lo) + '–' + fmt.k(f.hi) + '），滿 ' + f.need + ' 天才需要重畫路徑形狀' + (f.reshape_needed ? '——<b>已滿，需要重估形狀</b>' : '') + '。',
      'Envelope check: the close has been more than 12% outside all four paths for ' + f.run + ' straight day(s) (today\'s range ' + fmt.k(f.lo) + '–' + fmt.k(f.hi) + '); the path shapes are re-drawn only after ' + f.need + (f.reshape_needed ? ' — <b>reached: shapes need review</b>' : '') + '.') : '';
    if (!r) return fanTxt ? '<p class="note">' + fanTxt + '</p>' : '';
    var tbl = '<div class="tbl-wrap"><table class="tbl"><thead><tr><th>' + _T('路徑', 'Path') + '</th><th class="num">' + _T(ym(r.month) + ' 路徑值', ym(r.month) + ' path value') + '</th><th class="num">' + _T('似然', 'Likelihood') + '</th><th class="num">' + _T('權重', 'Weight') + '</th></tr></thead><tbody>' +
      ks.map(function (k) { var a = r.before[k], b = r.after[k]; return '<tr><td>' + esc(_T(k, PATH_EN[k] || k)) + '</td><td class="num">' + fmt.usd(r.m[k]) + '</td><td class="num">' + fmt.n(r.L[k], 2) + '</td><td class="num">' + a + '% → <b>' + b + '%</b>' + (b !== a ? ' <span style="color:var(--' + (b > a ? 'up' : 'down') + ')">' + (b > a ? '+' : '−') + Math.abs(b - a) + '</span>' : '') + '</td></tr>'; }).join('') + '</tbody></table></div>';
    return '<details class="rd-how" style="margin-top:10px"><summary>' + _T(ym(r.month) + ' 重估：月底收 ' + fmt.usd(r.close) + '，權重 ' + ks.map(function (k) { return r.before[k]; }).join('/') + ' → ' + ks.map(function (k) { return r.after[k]; }).join('/'), ym(r.month) + ' review: month-end close ' + fmt.usd(r.close) + ', weights ' + ks.map(function (k) { return r.before[k]; }).join('/') + ' → ' + ks.map(function (k) { return r.after[k]; }).join('/')) + '</summary>' + tbl +
      '<p class="note">' + _T('每月底自動做：起點換成月底收盤、已實現線補上這個月；權重用月底收盤和各路徑當月值的距離做貝氏更新（似然 = exp(−(ln 收盤 − ln 路徑值)² ÷ (2 × 0.12²))，新權重 = 舊權重與更新後的平均）；收盤跌破 61,000 時「直接修復」歸零。這個月' + (r.fan_run ? '有 ' + r.fan_run + ' 天' : '沒有一天') + '超出包絡上下 12%，路徑形狀不變。',
        'Done automatically at each month end: the start moves to the month-end close and the realized line gains the month; weights get a Bayesian update from the gap between the close and each path\'s value for the month (likelihood = exp(−(ln close − ln path)² ÷ (2 × 0.12²)); new weight = average of old and updated); “Direct recovery” drops to zero on a close below 61,000. This month ' + (r.fan_run ? r.fan_run + ' day(s) were' : 'no day was') + ' more than 12% outside the envelope, so the shapes stay.') + ' ' + fanTxt + '</p></details>';
  }

  /* 頂部雷達（2026-11-04 由鏈上版搬到週期版：週期版集中「離頂部多遠」的所有讀數） */
  function radarPanel() {
    var tr = D.onchain.top_radar || {};
    var radar = [['LTH MVRV Z', tr['lth-mvrv-zscore'], 2, 'lth-mvrv-zscore'], [_t('獲利供給 %'), tr['supply-in-profit-pct'], 1, 'supply-in-profit-pct'], [_t('LTH 30 日淨部位'), tr['lth-net-position-change-30d-btc'], 0, 'lth-net-position-change-30d-btc']].filter(function (r) { return r[1]; });
    var rt = _t('<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:34%"><col style="width:22%"><col style="width:22%"><col style="width:22%"></colgroup><thead><tr><th>頂部雷達</th><th class="num">現在</th><th class="num">2025 頂部</th><th>本輪位置</th></tr></thead><tbody>') + radar.map(function (r) { var v = r[1], rd = RADAR_READ[r[3]](v); return '<tr class="has-rd"><td><b>' + r[0] + '</b></td><td class="num">' + fmt.n(v.value, r[2]) + '</td><td class="num">' + fmt.n(v.extreme_near_2025_top, r[2]) + '</td><td><div class="pct"><i><b style="width:' + v.pct_since_2022_11 + '%"></b></i><span class="num">' + fmt.n(v.pct_since_2022_11, 0) + '</span></div></td></tr>' + rdRow(rd, 4); }).join('') + '</tbody></table></div>';
    return radar.length ? panel('span-12', _t('頂部雷達'), _t('2022/11 起本輪百分位'), rt, '', 'radar') : '';
  }
  V.cycle = function () {
    var cm = D.cycle.cm, pl = D.cycle.powerlaw || {}, tm = D.cycle.tidemark || {}, p6 = D.cycle.p6 || {}, st = D.cycle.stage || {}, M = D.cycle.model;
    var w = M.weights;
    return readBar('cycle') + '<div class="grid">' +
      grpH('cy-now', '現在的階段', 'Where we are') +
      panel('span-12', _t('市場階段：') + (STAGE[st.stage] || ['—'])[0], _t('P23 · 熊市 → 轉換期 → 牛市'), stageHtml()) +
      regPanel() + dwPanel() + rupPanel() + lnPanel() +   // 2026-11-08 晨昏指數和週線多空分數並列
      grpH('cy-top', '離頂部多近', 'How close to a top', _T('出場框架用到的鏈上指標', 'The on-chain gauges the exit plan uses')) +
      panel('span-7', _t('MVRV ÷ 前一輪高點'), _t('CoinMetrics · 2021 起'), _t('<p class="say">現在 <b>') + fmt.n(cm.mvrv_vs_prior, 3) + _t('</b>；連 5 天站上 0.75 是出場框架的第一個鏈上賣點。') + esc((p20Read() || [''])[0]) + '</p><div class="chart" id="c-p20"></div>') +
      panel('span-5', _t('頂部三指標'), fmt.md(D.cycle.p6_date) + _t(' · 四年百分位'), '<p class="say">' + esc((p6Read() || [''])[0]) + '</p><div class="meters">' + meter('MVRV Z', _t('<0 底 · >3.5 頂'), p6.mvrv_z, fmt.n(p6.mvrv_z, 0), _t('百分位'), [80]) + meter('NUPL', _t('淨未實現損益'), p6.nupl, fmt.n(p6.nupl, 0), _t('百分位'), [80]) + meter('Puell', _t('礦工收入倍數'), p6.puell, fmt.n(p6.puell, 0), _t('百分位'), [80]) + _t('</div><p class="note">任兩項到 80 標為頂部區；只作讀值，不連動賣出。舊的 85／90 加速規則已取消：過去四輪都在週期中段就先到。</p>') + p6Raw(), '', 'p6') +
      avPanel() + rrPanel() + radarPanel() + ocPanel(true) +
      grpH('cy-hist', '和歷史與模型比', 'Against history and models') +
      ccPanel() + cePanel() +
      panel('span-7', _t('冪律：價格 ÷ 合理價'), _t('每天只用當天以前資料擬合'), _t('<p class="say">現在 <b>') + fmt.n(pl.ratio, 2) + _t(' 倍</b>（合理價 ') + fmt.usd(pl.fair) + _T('，', ', ') + plGap(pl.ratio) + _t('）。頂部倍數每輪縮小，照這個速度，下一輪頂部約在合理價的 ') + fmt.n((pl.next_top_ratio || [])[0], 2) + '–' + fmt.n((pl.next_top_ratio || [])[1], 2) + _t(' 倍。') + esc((plRead() || [''])[0]) + esc(plChanSay()) + '</p><div id="pl-lg">' + plLegend(plChan() ? 'chan' : 'ratio') + '</div><div class="chart" id="c-pl"></div>', (plChan() ? '<div class="seg" id="pl-mode"><button aria-pressed="true" data-m="chan">' + _T('通道位置', 'Channel') + '</button><button aria-pressed="false" data-m="ratio">' + _T('倍數', 'Multiple') + '</button></div>' : '') + _t('<div class="seg" id="pl-seg"><button aria-pressed="false" data-v="all">2012 起</button><button aria-pressed="true" data-v="2020">2020 起</button></div>')) +
      panel('span-5', _t('Tidemark 綜合訊號'), _t('第三方模型 · ') + fmt.md(tm.price_date) + _t(' 資料'), '<p class="say">' + esc((tmRead() || [''])[0]) + '</p><div class="meters">' + meter(_t('頂部訊號'), _t('≥50 窗口 · ≥70 警戒'), (tm.top || {}).signal || 0, fmt.n((tm.top || {}).signal, 1), (tm.top || {}).level || '—', [50, 70]) + meter(_t('熱度'), _t('五類加權'), (tm.top || {}).heat || 0, fmt.n((tm.top || {}).heat, 1), (tm.top || {}).zone || '', [40, 65]) + meter(_t('底部訊號'), _t('≥50 底部區'), (tm.bottom || {}).signal || 0, fmt.n((tm.bottom || {}).signal, 1), (tm.bottom || {}).level || '—', [50, 70]) + meter(_t('冷度'), _t('估值・礦工・價格結構'), (tm.bottom || {}).cold || 0, fmt.n((tm.bottom || {}).cold, 1), '', []) + '</div>' +
        '<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:62%"><col style="width:38%"></colgroup><tbody>' + (tm.cats || []).map(function (x) { return '<tr><td>' + esc(_T(x[0], TM_CAT_EN[x[0]] || x[0])) + (x[2] === 'partial' ? _t('＊') : '') + '</td><td><div class="pct"><i><b class="' + ((x[1] || 0) >= 80 ? 'hot' : '') + '" style="width:' + (x[1] || 0) + '%"></b></i><span class="num">' + (x[1] == null ? '—' : fmt.n(x[1], 0)) + '</span></div></td></tr>'; }).join('') + '</tbody></table></div><p class="note">' + esc(tmVerdict(tm.cycle_test)) + '</p>', '', 'tm') +
      tmhPanel() +
      panel('span-12', _t('長期路徑：四種走法'), _t('每月底重估 · 下次 ') + M.next_review, legend([[_t('直接修復 ') + w['直接修復'] + '%', 'var(--s4)', 'dash'], [_t('淺回檔 ') + w['淺回檔'] + '%', 'var(--s1)', 'dash'], [_t('基準雙底 ') + w['基準雙底'] + '%', 'var(--s2)', 'dash'], [_t('延後新低 ') + w['延後新低'] + '%', 'var(--s3)', 'dash'], [_t('已實現'), 'var(--ink)'], [_t('頂部 80% 區間'), 'var(--flare)', 'box']]) + _t('<div class="chart" id="c-path"></div><p class="note">頂部模型：中位 ') + fmt.usd(M.top_model.median) + _t('，80% 區間 ') + fmt.k(M.top_model.p10) + '–' + fmt.k(M.top_model.p90) + _t('，時間 ') + esc(tx(M.top_model, 'timing')) + _t('。路徑是本站的預測，2028 年以後只供量級參考。</p>') + pathReviewHtml()) +
      '</div>';
  };
  V.cycle.after = function () {
    safe(drawEv, function () { drawOc(true); }); tmhBind(); mount($('#c-regime'), drawRegime); mount($('#c-dawn'), drawDawn); mount($('#c-rup'), drawRup); mount($('#c-hnupl'), drawLn); mount($('#c-aviv'), drawAv); mount($('#c-rrisk'), drawRr); mount($('#c-cyccmp'), drawCycCmp);
    var M = D.cycle.model, cols = { '直接修復': 'var(--s4)', '淺回檔': 'var(--s1)', '基準雙底': 'var(--s2)', '延後新低': 'var(--s3)' };
    var md = function (y, m) { return Math.round(Date.UTC(y, m - 1, 15) / 864e5); };
    var series = Object.keys(M.nodes).map(function (k) { return { name: _t(k), data: M.nodes[k].map(function (p) { return [md(p[0], p[1]), p[2]]; }), color: cols[k], dash: '5 5', w: 1.8, end: false, smooth: true }; });
    var real = M.realized.map(function (p) { return [md(p[0], p[1]), p[2]]; }); real.push([dnOf(D.meta.bar_date), D.price.bar.c]);
    series.push({ name: _t('已實現'), data: real, color: 'var(--ink)', w: 2.6, smooth: true });
    mount($('#c-path'), function (el) { lineChart(el, { h: el.clientWidth < 520 ? 260 : 340, log: true, series: series, hbands: [{ y0: M.top_model.p10, y1: M.top_model.p90, color: 'var(--flare-dim)' }], refs: [{ y: M.top_model.median, color: 'var(--flare)', label: _t('頂部中位 ') + fmt.k(M.top_model.median) }], vlines: [{ x: dnOf(D.cycle.next_halving_est), label: _t('2028/04 減半') }], tipFmt: fmt.usd, aria: _t('四條長期路徑') }); });
    var p20 = D.cycle.p20 || {};
    mount($('#c-p20'), function (el) { var top = dnOf('2025-10-06'), tv = (p20.rows || []).filter(function (r) { return Math.abs(r[0] - top) <= 2; })[0]; lineChart(el, { series: [{ name: _t('比值'), data: p20.rows || [], color: 'var(--s1)', area: true }], refs: [{ y: 0.75, color: 'var(--down)', label: _t('0.75 第一階 ≈ ') + fmt.k(p20.k075) }, { y: 0.8, color: 'var(--down)', label: _t('0.80 第二階'), below: false }], marks: tv ? [{ x: tv[0], y: tv[1], label: _t('2025 頂 ') + tv[1].toFixed(2), left: true }] : [], yFmt: function (v) { return v.toFixed(1); }, tipFmt: function (v) { return v.toFixed(3); }, aria: _t('MVRV 除以前一輪高點') }); });
    var pl = D.cycle.powerlaw || {}, rng = '2020', plMode = plChan() ? 'chan' : 'ratio';
    function drawPlChan(el) {   // 通道位置：線的顏色按五段分（垂直漸層、硬切），各段底色淡淡標出
      var c = plChan(), H = 240, rows = c.rows; if (rng === '2020') rows = rows.filter(function (r) { return r[0] >= dnOf('2020-01-01'); });
      var cut = [0, 15, 35, 55, 75, 100], gid = 'plg-' + el.id;
      lineChart(el, { h: H, y0: 0, y1: 100, series: [{ name: _T('通道位置', 'Channel position'), data: rows, color: 'url(#' + gid + ')', w: 2, endColor: STG_C[plStage(c.now)], tipColor: function (v) { return STG_C[plStage(v)]; } }],
        hbands: cut.slice(0, 5).map(function (y0, i) { return { y0: y0, y1: cut[i + 1], color: 'color-mix(in srgb, ' + STG_C[i] + ' 9%, transparent)' }; }),
        yFmt: function (v) { return v.toFixed(0) + '%'; }, tipFmt: function (v) { var k = plStage(v); return fmt.n(v, 0) + '%' + _T('（' + PL_STG[k][1] + '）', ' (' + PL_STG[k][2] + ')'); }, aria: _T('冪律通道位置', 'Power-law channel position') });
      // lineChart 的 y 軸：上下各留 8%、上邊界 14px、下邊界 24px（見 lineChart），所以 0–100% 在畫面上的位置可以直接算
      var ph = H - 38, py = function (v) { return 14 + (1 - (v + 8) / 116) * ph; }, st = '';
      for (var i = 4; i >= 0; i--) st += '<stop offset="' + (py(cut[i + 1]) / H).toFixed(4) + '" stop-color="' + STG_C[i] + '"/><stop offset="' + (py(cut[i]) / H).toFixed(4) + '" stop-color="' + STG_C[i] + '"/>';
      el.insertAdjacentHTML('beforeend', '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs><linearGradient id="' + gid + '" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="' + H + '">' + st + '</linearGradient></defs></svg>');
    }
    function drawPl(el) {
      if (plMode === 'chan') return drawPlChan(el);
      var rows = (pl.rows || []).map(function (r) { return [r[0], Math.pow(10, r[1])]; }); if (rng === '2020') rows = rows.filter(function (r) { return r[0] >= dnOf('2020-01-01'); });
      var mk = (pl.tops || []).concat(pl.bottoms || []).map(function (t) { var x = dnOf(t[0]); return rows.length && x >= rows[0][0] ? { x: x, y: t[1], label: t[1].toFixed(2), color: t[1] >= 1 ? 'var(--flare)' : 'var(--orbit)', below: t[1] < 1 } : null; }).filter(Boolean);
      lineChart(el, { log: true, series: [{ name: _t('倍數'), data: rows, color: 'var(--s2)' }], hbands: [{ y0: (pl.bottom_band || [0.24, 0.48])[0], y1: (pl.bottom_band || [0.24, 0.48])[1], color: 'var(--orbit-dim)' }], refs: [{ y: 1, color: 'var(--ink-3)', label: _t('1.0 合理價') }], marks: mk, yFmt: function (v) { return v >= 1 ? v.toFixed(v >= 10 ? 0 : 1) : v.toFixed(2); }, tipFmt: function (v) { return v.toFixed(2) + '×'; }, aria: _t('價格除以冪律合理價') });
    }
    mount($('#c-pl'), drawPl);
    $('#pl-seg').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; rng = b.getAttribute('data-v'); this.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); drawPl($('#c-pl')); });
    var pm = $('#pl-mode'); if (pm) pm.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; plMode = b.getAttribute('data-m'); this.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); var lg = $('#pl-lg'); if (lg) lg.innerHTML = plLegend(plMode); drawPl($('#c-pl')); });
  };

  V.market = function () {
    var p = D.price, ma = p.ma, c = p.bar.c, vp = p.volprofile || {};
    var lv = [[D.exit.framework.ladder[0], _t('出場第一階')], [D.cycle.cm.k080_price, _t('MVRV 0.80 線')], [D.cycle.cm.k075_price, _t('MVRV 0.75 線')], [D.cycle.cm.price_ath_close, _t('歷史收盤新高')], [vp.va_high_outer, _t('近 20 日價值區上緣')], [vp.poc, _t('近 20 日成交最密集價')], [ma.sma20, _t('20 日均線')], [vp.va_low, _t('近 20 日價值區下緣')], [ma.sma50, _t('50 日均線')], [ma.sma200, _t('200 日均線（避險線）')], [D.cycle.cm.realized_price, _t('全網平均成本（實現價）')]].filter(function (x) { return x[0]; }).sort(function (a, b) { return b[0] - a[0]; });
    var tbl = _t('<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:30%"><col style="width:24%"><col style="width:46%"></colgroup><thead><tr><th>價位</th><th class="num">距收盤</th><th>是什麼</th></tr></thead><tbody>') + lv.map(function (x) { var d = (x[0] / c - 1) * 100; return '<tr><td class="num" style="text-align:left">' + fmt.usd(x[0]) + '</td><td class="num" style="color:' + (d >= 0 ? 'var(--up)' : 'var(--down)') + '">' + fmt.pct(d) + '</td><td>' + x[1] + '</td></tr>'; }).join('') + '</tbody></table></div>';
    var ma2 = [[_t('5 日'), ma.sma5], [_t('20 日'), ma.sma20], [_t('50 日'), ma.sma50], [_t('111 日'), ma.sma111], [_t('200 日'), ma.sma200], [_t('350 日'), ma.sma350]];
    var mat = '<div class="meters">' + ma2.map(function (m) { var d = (c / m[1] - 1) * 100; return meter(m[0] + _t('均線'), fmt.usd(m[1]), 50 + Math.max(-50, Math.min(50, d * 2)), fmt.pct(d), d >= 0 ? _t('價格在上方') : _t('價格在下方'), [50]); }).join('') + _t('</div><p class="note">中線＝均線位置；圓點越往右，價格越高於該均線。</p>');
    return readBar('market') + '<div class="kpis">' + kpi(_t('收盤'), fmt.usd(c), fmt.pct(p.bar.chg_pct, 2) + _t(' · 當日區間位置 ') + fmt.n(p.bar.close_pos_pct, 0) + '%') + kpi(_t('ATR14（簡單平均）'), fmt.usd(p.atr.atr14), _t('約 ') + fmt.n(p.atr.atr14 / c * 100, 1) + _t('% / 日')) + kpi(_t('實際波動 RV30'), fmt.n(p.vol.rv30, 1) + '%', 'RV7 ' + fmt.n(p.vol.rv7, 1) + '% · RV90 ' + fmt.n(p.vol.rv90, 1) + '%' + (p.vol.rv30_pct1y != null ? _T(' · 一年第 ' + fmt.n(p.vol.rv30_pct1y, 0) + ' 百分位', ' · ' + fmt.n(p.vol.rv30_pct1y, 0) + 'th pct (1y)') : '')) + kpi(_t('Mayer 倍數'), fmt.n(p.mayer.mayer, 2), _t('價格 ÷ 200 日均線')) + kpi('Pi Cycle', fmt.n(p.pi_cycle, 2), _t('111 日 ÷ 2×350 日；≥1 為歷史頂部訊號'), p.pi_cycle * 100) + '</div><div class="grid">' + interpPanel(mkInterp()) +
      grpH('mk-leg', '這一段行情', 'This leg', _T('這一段走了多遠、近幾天的價位、跌勢拖了多久', 'How far this leg has run, the nearby levels, and how long weakness has dragged on')) +   // 2026-11-08 內容重組：價格版分三組
      swingPanel() +
      panel('span-8', _t('近 20 天 K 線'), _t('Kraken 日線 · UTC'), '<div class="chart" id="c-cd"></div>') +
      panel('span-4', _t('關鍵價位'), '', levelsSay(lv, c) + tbl) +
      sxPanel() +   // 2026-11-08 從衍生品版搬來：只用每日收盤，屬於價格動能
      grpH('mk-ma', '均線與成本線', 'Moving averages and cost lines', _T('上下各有哪幾條線、離多遠', 'Which lines sit above and below, and how far away')) +
      lvPanel() +
      panel('span-12', _t('價格與均線'), '', maSay(ma, c) + mat) +
      grpH('mk-long', '長期與季節性', 'Long run and seasonality', _T('放到十幾年來看，這個月算不算特別', 'Over a decade and more, and whether this month is unusual')) +
      panel('span-12', _t('價格長期走勢'), _t('CoinMetrics · 對數刻度'), '<div class="chart" id="c-long"></div>', _t('<div class="seg" id="lg-seg"><button aria-pressed="false" data-v="all">2012 起</button><button aria-pressed="true" data-v="4y">近 4 年</button></div>')) +
      monPanel() + '</div>';   // 2026-11-08 月度報酬熱力表
  };
  V.market.after = function () {
    mount($('#c-levels'), drawLevels);
    mount($('#c-mon'), drawMon);   // 2026-11-08 月度報酬熱力表
    mount($('#c-sx'), drawSx);   // 2026-11-08 從衍生品版搬來
    var p = D.price, H = p.history || [], rng = '4y';
    mount($('#c-cd'), function (el) { candleChart(el, p.rows20 || [], [{ v: p.ma.sma20, label: _t('20 日 ') + fmt.k(p.ma.sma20), color: 'var(--s2)' }, { v: (p.volprofile || {}).va_high_outer, label: _t('價值區上緣'), color: 'var(--flare)' }, { v: (p.volprofile || {}).poc, label: 'POC', color: 'var(--ink-3)' }]); });
    function drawLong(el) {
      var rows = rng === '4y' ? H.filter(function (r) { return r[0] >= H[H.length - 1][0] - 1461; }) : H;
      var mk = D.cycle.tops.concat(D.cycle.bottoms).map(function (t) { var x = dnOf(t[0]); return rows.length && x >= rows[0][0] ? { x: x, y: t[1], label: fmt.k(t[1]), color: t[1] > 50000 || D.cycle.tops.some(function (q) { return q[0] === t[0]; }) ? 'var(--flare)' : 'var(--orbit)', below: !D.cycle.tops.some(function (q) { return q[0] === t[0]; }), left: true } : null; }).filter(Boolean);
      lineChart(el, { log: true, series: [{ name: _t('價格'), data: rows, color: 'var(--s2)', area: true }], marks: mk, vlines: D.cycle.halvings.map(function (h) { return { x: dnOf(h), label: '' }; }), tipFmt: fmt.usd, aria: _t('長期價格') });
    }
    mount($('#c-long'), drawLong);
    $('#lg-seg').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; rng = b.getAttribute('data-v'); this.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); drawLong($('#c-long')); });
  };

  /* 清算熱力圖（推算；2026-11-02 使用者要求，參考 CoinGlass 爆倉熱力圖）：永續未平倉量＋假設槓桿 5–100 倍，見 pipeline/liq_heat.py。
     2026-11-08 起用 Coinalyze 彙整的多家交易所（取不到時退回 OKX），並加「2 年」範圍（data/liq_long.json，點了才載入，每天一欄）。
     畫布畫熱力（越亮＝推算的待清算量越多），SVG 疊 K 線與十字線。不是實際倉位，只作讀值 */
  var liqDays = 3, liqBytes = null, liqTop_ = null, liqL = null, liqLBytes = null, liqLTop = null, liqLErr = false;
  /* 熱力圖底色永遠是深色的 viridis（淺色主題也一樣），K 線與收盤線用深色主題的亮色才看得清楚，所以這三個色不跟主題變（2026-11-04 註明，刻意的） */
  var LIQ_UP = '#2FD08A', LIQ_DN = '#FF4A2E', LIQ_INK = '#F2F0EA', LIQ_HL = '#FFFFFF';   // LIQ_HL：Hyperliquid 實際清算價的橫條（2026-11-05），白色和 viridis、K 線的紅綠都分得開
  /* 2026-11-04 自我檢查：色階上限用整份快照算一次（原本每次依畫面內的格子重算，切換 3／7 天同一格會變色，縮放視窗也重排序一次） */
  function liqTopOf(u) { var v = []; for (var i = 0; i < u.length; i++) if (u[i]) v.push(u[i]); v.sort(function (a, b) { return a - b; }); return v.length ? Math.max(1, v[Math.floor(v.length * 0.998)]) : 255; }
  function liqTop() { if (liqTop_ == null) liqTop_ = liqTopOf(liqBytes); return liqTop_; }
  function liqB64(b64) { var b = atob(b64), u = new Uint8Array(b.length); for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u; }
  /* 第 i 根 K 線的時間：管線有給 hr（距 t0 的小時數）就用它，漏掉的小時不會讓後面整段錯位 */
  function liqT(x, i) { return x.t0 + (x.hr ? x.hr[i] : i) * 36e5; }
  var VIR = [[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]];
  function liqCol(v) { v = Math.max(0, Math.min(1, v)); var s = v * 4, i = Math.min(3, Math.floor(s)), f = s - i; return VIR[i].map(function (a, k) { return Math.round(a + (VIR[i + 1][k] - a) * f); }); }
  function liqData() {
    var x = (D.deriv || {}).liq_heat; if (!x || !x.heat) return null;
    if (!liqBytes) liqBytes = liqB64(x.heat);
    return x;
  }
  function liqCz() { var m = ((D.deriv || {}).liq_heat || {}).model || {}; return m.src === 'Coinalyze' ? m : null; }
  /* 「2 年」：data/liq_long.json 點了才載入（約 200 KB），用 latest.json 記的時間避開舊快取 */
  function liqLong(cb) {
    var m = ((D.deriv || {}).liq_heat || {}).long; if (!m) return;
    fetch('data/liq_long.json?v=' + encodeURIComponent(m.asof)).then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (j) { liqL = j; liqLBytes = liqB64(j.heat); liqLTop = liqTopOf(liqLBytes); cb(); }).catch(function () { liqLErr = true; cb(); });
  }
  function liqBand(b) { return fmt.k(b.lo) + '–' + fmt.k(b.hi); }
  function liqBtc(v) { return _T('約 ' + fmt.n(v) + ' 顆', '~' + fmt.n(v) + ' BTC'); }
  function liqHour(ms) { var t = new Date(ms); return (t.getUTCMonth() + 1) + '/' + t.getUTCDate() + ' ' + ('0' + t.getUTCHours()).slice(-2) + ':00'; }
  function hlBandSay() {   // 2026-11-05：熱力圖右緣的 Hyperliquid 白條（實際清算價，每格至少 5 個帳戶、最大一個不超過一半）
    var hb = hlBands(); if (!hb) return '';
    var L = hlSide(hb, 'long'), S = hlSide(hb, 'short'), h = hb.hidden || {}, k = function (b) { return fmt.k(b.lo) + '–' + fmt.k(b.hi); };
    var hs = function (g, L) { g = g || {}; return g.btc != null ? _T((L ? '多單 ' : '空單 ') + g.n + ' 個帳戶 ' + fmt.n(g.btc) + ' 顆', (L ? 'longs ' : 'shorts ') + g.n + ' accounts, ' + fmt.n(g.btc) + ' BTC') : _T((L ? '多單 ' : '空單 ') + (g.n || 0) + ' 個帳戶', (L ? 'longs ' : 'shorts ') + (g.n || 0) + ' account(s)'); };
    if (!hb.rows.length) return _T('清算價在收盤 ±' + hb.pct + '% 內的有' + (h.long ? '下方' + hs(h.long, 1) + '、上方' + hs(h.short, 0) : ' ' + (h.n || 0) + ' 個帳戶') + '，分散在各價位：沒有任何 ' + fmt.n(hb.w) + ' 美元的價位聚了 ' + hb.min_n + ' 個以上帳戶（大戶清算價大多離現價很遠），所以熱力圖上沒有 Hyperliquid 白條；聚集時會自動畫出來。',
      'Within ±' + hb.pct + '% of the close: ' + (h.long ? hs(h.long, 1) + ' below, ' + hs(h.short, 0) + ' above' : (h.n || 0) + ' accounts') + ', scattered: no $' + fmt.n(hb.w) + ' bucket holds ' + hb.min_n + '+ accounts (big accounts mostly sit far from the price), so no Hyperliquid bars are drawn; they appear automatically when positions cluster. ');
    return _T('熱力圖右緣的白條是清算價在收盤 ±' + hb.pct + '% 內、每 ' + fmt.n(hb.w) + ' 美元一格至少 ' + hb.min_n + ' 個帳戶的價位：' + (L.cells ? '下方多單 ' + L.n + ' 個帳戶 ' + fmt.n(L.btc) + ' 顆（最多在 ' + k(L.top) + '）' : '下方沒有') + '、' + (S.cells ? '上方空單 ' + S.n + ' 個帳戶 ' + fmt.n(S.btc) + ' 顆（最多在 ' + k(S.top) + '）' : '上方沒有') + '；其餘 ' + (h.n || 0) + ' 個帳戶太分散、不畫。',
      'White bars on the heatmap\'s right edge mark liquidation prices within ±' + hb.pct + '% where a $' + fmt.n(hb.w) + ' bucket holds at least ' + hb.min_n + ' accounts: ' + (L.cells ? 'longs below, ' + L.n + ' accounts and ' + fmt.n(L.btc) + ' BTC (most at ' + k(L.top) + ')' : 'none below') + '; ' + (S.cells ? 'shorts above, ' + S.n + ' accounts and ' + fmt.n(S.btc) + ' BTC (most at ' + k(S.top) + ')' : 'none above') + '; the other ' + (h.n || 0) + ' accounts are too scattered to draw. ');
  }
  function liqSay() {
    var x = D.deriv.liq_heat, it = [], b = (x.below || [])[0], a = (x.above || [])[0], w = x.within5 || {};
    if (b) it.push([_T('下方最亮（多單）', 'Brightest below (longs)'), liqBand(b), _T('推算' + liqBtc(b.btc) + '，在收盤下方 ' + fmt.n(-b.dist_pct, 1) + '%。跌到這裡會觸發這批多單強制平倉；強平是市價賣出，可能讓下跌加速。',
      'Estimated ' + liqBtc(b.btc) + ', ' + fmt.n(-b.dist_pct, 1) + '% below the close. A drop there would force-close these longs; forced closes are market sells and can speed up a decline.'), 'neu']);
    if (a) it.push([_T('上方最亮（空單）', 'Brightest above (shorts)'), liqBand(a), _T('推算' + liqBtc(a.btc) + '，在收盤上方 ' + fmt.n(a.dist_pct, 1) + '%。漲到這裡會觸發空單強制平倉；強平是市價買進，可能讓上漲加速。',
      'Estimated ' + liqBtc(a.btc) + ', ' + fmt.n(a.dist_pct, 1) + '% above the close. A rise there would force-close these shorts; forced closes are market buys and can speed up a rally.'), 'neu']);
    if (w.above != null && w.below != null) {
      var r = w.below / (w.above || 1), side = r >= 1.2 ? _T('下方較多（約 ' + fmt.n(r, 1) + ' 倍）', 'more below (about ' + fmt.n(r, 1) + 'x)') : r <= 1 / 1.2 ? _T('上方較多（約 ' + fmt.n(1 / r, 1) + ' 倍）', 'more above (about ' + fmt.n(1 / r, 1) + 'x)') : _T('兩邊差不多', 'roughly balanced');
      it.push([_T('收盤下／上 5% 內', 'Below / above, within 5%'), fmt.n(w.below) + ' / ' + fmt.n(w.above),
        _T('推算的待清算量：下方多單 ' + fmt.n(w.below) + ' 顆、上方空單 ' + fmt.n(w.above) + ' 顆，' + side + '。只代表哪一側堆了較多槓桿，不代表價格會往那裡走。', 'Estimated BTC awaiting liquidation: ' + fmt.n(w.below) + ' in longs below, ' + fmt.n(w.above) + ' in shorts above, ' + side + '. It shows where leverage is stacked, not where price will go.'), 'neu']);
    }
    var fr = x.far || {}, fb = fr.below, fa = fr.above, since = (x.model || {}).since;   // 2026-11-04：畫面（收盤 ±7%）外、±25% 內最亮的一塊
    if (fb || fa) it.push([_T('畫面外（±25% 內）', 'Off-screen (within ±25%)'), (fb ? fmt.k(fb.lo) + '–' + fmt.k(fb.hi) : '—') + ' / ' + (fa ? fmt.k(fa.lo) + '–' + fmt.k(fa.hi) : '—'),
      _T((fb ? '下方 ' + fmt.k(fb.lo) + '–' + fmt.k(fb.hi) + ' 推算' + liqBtc(fb.btc) + '（低 ' + fmt.n(-fb.dist_pct, 1) + '%）' : '') + (fb && fa ? '；' : '') + (fa ? '上方 ' + fmt.k(fa.lo) + '–' + fmt.k(fa.hi) + ' 推算' + liqBtc(fa.btc) + '（高 ' + fmt.n(fa.dist_pct, 1) + '%）' : '') + '。' + (since ? '較早的部分用 4 小時線補到 ' + ymdD(since) + '，算進更早累積、還沒被清掉的槓桿。' : ''),
        (fb ? 'Below ' + fmt.k(fb.lo) + '–' + fmt.k(fb.hi) + ': an estimated ' + liqBtc(fb.btc) + ' (' + fmt.n(-fb.dist_pct, 1) + '% down)' : '') + (fb && fa ? '; ' : '') + (fa ? 'above ' + fmt.k(fa.lo) + '–' + fmt.k(fa.hi) + ': an estimated ' + liqBtc(fa.btc) + ' (' + fmt.n(fa.dist_pct, 1) + '% up)' : '') + '.' + (since ? ' Older history is filled in with 4-hour bars back to ' + ymdD(since) + ', so older leverage that has not been cleared is included.' : '')), 'neu']);
    var hw = D.deriv.hl_whales;   // 2026-11-04：Hyperliquid 大戶的 BTC 部位彙總（實際部位，不是推算；不列個別帳戶）
    if (hw && hw.long && hw.short) {
      var gq = function (g, L) { return g.btc != null ? _T((L ? '多單 ' : '空單 ') + fmt.n(g.btc) + ' 顆（' + g.n + ' 個帳戶）', (L ? 'longs ' : 'shorts ') + fmt.n(g.btc) + ' BTC (' + g.n + ' accounts)') : _T((L ? '多單 ' : '空單 ') + g.n + ' 個帳戶', (L ? 'longs ' : 'shorts ') + g.n + ' account' + (g.n === 1 ? '' : 's')); };
      var lq = gq(hw.long, 1), sq = gq(hw.short, 0), nl = gq(hw.near.long, 1), ns = gq(hw.near.short, 0);
      var net = hw.long.btc != null && hw.short.btc != null ? hw.long.btc - hw.short.btc : null;
      it.push([_T('Hyperliquid 大戶', 'Hyperliquid big accounts'), net != null ? (net >= 0 ? _T('淨多 ', 'Net long ') : _T('淨空 ', 'Net short ')) + fmt.n(Math.abs(net)) : hw.with_btc + _T(' 個帳戶', ' accounts'),
        _T('帳戶淨值前 ' + hw.scanned + ' 名（≥ ' + fmt.n(hw.floor_usd_m, hw.floor_usd_m < 10 ? 1 : 0) + ' 百萬美元）裡 ' + hw.with_btc + ' 個有 BTC 部位：' + lq + '、' + sq + '；清算價在收盤 ±' + hw.near.pct + '% 內：' + nl + '、' + ns + '。' + hlBandSay() + '實際部位，不是推算；只有 Hyperliquid 一家，大帳戶可能是做市或避險，空單多不一定代表看空。',
          hw.with_btc + ' of the top ' + hw.scanned + ' accounts by equity (≥ $' + fmt.n(hw.floor_usd_m, hw.floor_usd_m < 10 ? 1 : 0) + 'M) hold BTC: ' + lq + ', ' + sq + '; liquidation prices within ±' + hw.near.pct + '% of the close: ' + nl + ', ' + ns + '. ' + hlBandSay() + 'Actual positions, not an estimate; Hyperliquid only, and big accounts may be market makers or hedgers, so more shorts does not necessarily mean bearish.'), 'neu']);
    }
    return it;
  }
  function hlBands() { var hb = (D.deriv.hl_whales || {}).bands; return hb && hb.rows ? hb : null; }
  function hlSide(hb, side) { var r = hb.rows.filter(function (b) { return b.side === side; }); return { n: r.reduce(function (a, b) { return a + b.n; }, 0), btc: r.reduce(function (a, b) { return a + b.btc; }, 0), cells: r.length, top: r.slice().sort(function (a, b) { return b.btc - a.btc; })[0] }; }
  function liqSegs() { var b = function (d, l) { return '<button aria-pressed="' + (liqDays === d) + '" data-d="' + d + '">' + (l || _T(d + ' 天', d + 'D')) + '</button>'; }; return '<span class="seg">' + b(3) + b(7) + (((D.deriv || {}).liq_heat || {}).long ? b(730, _T('2 年', '2Y')) : '') + '</span>'; }
  function liqPanel() {
    var x = liqData(); if (!x) return '';
    var cz = liqCz(), snap = liqHour(Date.parse(x.asof));
    return panel('span-12', _T('清算熱力圖（推算）', 'Liquidation heatmap (estimate)'), cz ? _T('Coinalyze · ' + cz.exch.length + ' 家交易所永續 · 快照 ' + snap + ' UTC', 'Coinalyze · perpetuals on ' + cz.exch.length + ' exchanges · snapshot ' + snap + ' UTC') : _T('OKX 永續 · 快照 ' + snap + ' UTC', 'OKX perpetuals · snapshot ' + snap + ' UTC'),
      interpHtml(liqSay()) + '<div class="legend" style="margin-top:10px"><span><b style="color:var(--ink-2);font-weight:400">' + _T('少', 'Less') + '</b><i class="liq-bar" style="background:linear-gradient(90deg,' + VIR.map(function (c) { return 'rgb(' + c.join(',') + ')'; }).join(',') + ')"></i><b style="color:var(--ink-2);font-weight:400">' + _T('多', 'More') + '</b></span><span><b style="color:var(--ink-2);font-weight:400">' + _T('推算的待清算量；收盤下方是多單、上方是空單', 'estimated BTC awaiting liquidation; longs below the close, shorts above') + '</b></span>' + (hlBands() && hlBands().rows.length ? '<span><i class="liq-hl"></i><b style="color:var(--ink-2);font-weight:400">' + _T('Hyperliquid 大戶實際清算價（右緣，越長越多）', 'Hyperliquid big accounts\' actual liquidation prices (right edge; longer = more)') + '</b></span>' : '') + '</div><div class="chart" id="c-liq"></div>' +
      '<p class="note">' + (cz ? _T('做法：Coinalyze 彙整的 ' + cz.exch.join('、') + ' 共 ' + cz.n + ' 個 BTC 永續合約（USDT、USDC、幣本位；目前合計未平倉約 ' + fmt.n(cz.oi_btc) + ' 顆；Coinalyze 沒有 Bitget、Gate）。每根 K 線各合約的未平倉量增加當成新開倉、一多一空各記一份，減少的按比例減；槓桿假設 5–100 倍、進場價攤在那根 K 線的高低之間，算出清算價；價格走過就算清算掉。最近約 84 天用 1 小時線，更早用 4 小時線；「2 年」用 12 小時線、每天一欄。槓桿分布是假設，亮帶位置會隨假設移動；每天快照一次，不是即時；不是 CoinGlass 的數字。',
        'Method: ' + cz.n + ' BTC perpetual contracts on ' + cz.exch.join(', ') + ' as compiled by Coinalyze (USDT-, USDC- and coin-margined; about ' + fmt.n(cz.oi_btc) + ' BTC of open interest now; Coinalyze has no Bitget or Gate). Each bar\'s rise in a contract\'s open interest counts as new positions, one long and one short, and falls scale existing positions down; leverage is assumed between 5x and 100x with entries spread across the bar\'s range, giving liquidation prices; levels are cleared once price trades through them. Hourly bars for the last ~84 days, 4-hour bars before that; “2Y” uses 12-hour bars with one column per day. The leverage mix is an assumption and moves the bands; a daily snapshot, not real time; not CoinGlass\'s numbers.')
        : _T('做法：OKX BTC 永續（USDT＋幣本位）每小時未平倉量增加當成新開倉，一多一空各記一份；槓桿假設 5–100 倍、進場價攤在那一小時的高低之間，算出清算價；價格走過就算清算掉，未平倉量減少時按比例減。這次多家交易所的資料（Coinalyze）取不到，暫時只有 OKX；槓桿分布是假設，亮帶位置會隨假設移動；每天快照一次，不是即時；不是 CoinGlass 的數字。',
        'Method: each hour\'s rise in OKX BTC perpetual open interest (USDT- and coin-margined) counts as new positions, one long and one short; leverage is assumed between 5x and 100x with entries spread across the hour\'s range, giving liquidation prices; levels are cleared once price trades through them, and scaled down when open interest falls. Multi-exchange data (Coinalyze) was unavailable this time, so OKX only; the leverage mix is an assumption and moves the bands; a daily snapshot, not real time; not CoinGlass\'s numbers.')) +
      (cz ? ' <a href="https://coinalyze.net" target="_blank" rel="noopener">' + _T('資料：Coinalyze ↗', 'Data: Coinalyze ↗') + '</a>' : '') +
      ' <a href="https://www.coinglass.com/pro/futures/LiquidationHeatMap" target="_blank" rel="noopener">' + _T('對照 CoinGlass ↗', 'Compare with CoinGlass ↗') + '</a></p>',
      '<span id="liq-segs" style="display:contents">' + liqSegs() + '</span>');
  }
  function drawLiq(el) {
    var x = liqData(); if (!x || !el) return;
    if (liqDays > 7) {   // 「2 年」：第一次點才載入
      if (!liqL && !liqLErr) { el.innerHTML = '<p class="note">' + _T('載入 2 年資料…', 'Loading 2 years of data…') + '</p>'; liqLong(function () { if (liqDays > 7) drawLiq(el); }); return; }
      if (!liqL) { el.innerHTML = '<p class="note">' + _T('2 年資料載入失敗，請稍後再點一次。', 'Could not load the 2-year data; please try again later.') + '</p>'; return; }
      return liqPaint(el, { x: liqL, u: liqLBytes, top: liqLTop, n0: 0, n: liqL.days, K: liqL.candles, t: function (i) { return liqL.t0 + liqL.dd[i] * 864e5; }, day: true });
    }
    var nh = Math.min(x.hours, liqDays * 24), h0 = x.hours - nh;
    liqPaint(el, { x: x, u: liqBytes, top: liqTop(), n0: h0, n: nh, K: x.candles.slice(h0), t: function (i) { return liqT(x, h0 + i); } });
  }
  /* v：{x 資料, u 熱力位元組, top 色階上限, n0 從第幾欄, n 欄數, K K 線, t(i) 第 i 欄的時間, day 每欄一天（「2 年」）} */
  function liqPaint(el, v) {
    var x = v.x, nb = x.nb, nh = v.n, h0 = v.n0, K = v.K, U = v.u, DY = !!v.day, i, j;
    var plo = Math.min.apply(null, K.map(function (k) { return k[2]; })) * 0.95, phi = Math.max.apply(null, K.map(function (k) { return k[1]; })) * 1.05;
    if (!DY) { (x.below || []).slice(0, 1).forEach(function (b) { plo = Math.min(plo, b.lo - 500); }); (x.above || []).slice(0, 1).forEach(function (b) { phi = Math.max(phi, b.hi + 500); }); }   // 讀值提到的最亮帶一定在圖內
    var b0 = Math.max(0, Math.floor((plo - x.lo) / x.step)), b1 = Math.min(nb, Math.ceil((phi - x.lo) / x.step)), rows = b1 - b0, pLo = x.lo + b0 * x.step, pHi = x.lo + b1 * x.step;
    var top = v.top, gam = function (v) { return Math.pow(Math.min(1, v), 1.6); };   // 色階偏向突顯最亮的帶（越亮越多，不是等距）
    var W = Math.max(280, el.clientWidth), Ht = W < 520 ? 300 : 420, ML = 8, MR = 58, MT = 8, MB = 24, pw = W - ML - MR, ph = Ht - MT - MB, dpr = window.devicePixelRatio || 1;
    var X = function (k) { return ML + (k + 0.5) * pw / nh; }, Y = function (p) { return MT + (1 - (p - pLo) / (pHi - pLo)) * ph; }, s = '';
    var st = niceStep(pHi - pLo, W < 520 ? 4 : 6);
    for (var p = Math.ceil(pLo / st) * st; p <= pHi; p += st) s += '<line x1="' + (ML + pw) + '" x2="' + (ML + pw + 4) + '" y1="' + Y(p).toFixed(1) + '" y2="' + Y(p).toFixed(1) + '" stroke="var(--ink-3)"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (Y(p) + 3.5).toFixed(1) + '">' + fmt.k(p) + '</text>';
    var MON = ['Jan', 'Apr', 'Jul', 'Oct'], pm = null;
    for (i = 0; i < nh; i++) {
      var t = new Date(v.t(i)), lx = X(i), lab = null;
      if (!DY) { if (t.getUTCHours() === 0) lab = (t.getUTCMonth() + 1) + '/' + t.getUTCDate(); }
      else { var mo = t.getUTCMonth(); if (pm != null && mo !== pm && mo % 3 === 0 && (W >= 520 || mo % 6 === 0)) lab = mo === 0 ? String(t.getUTCFullYear()) : _T((mo + 1) + '月', MON[mo / 3]); pm = mo; }   // 「2 年」：每季標一次（窄螢幕每半年）
      if (lab && lx > ML + 16 && lx < ML + pw - 16) s += '<text class="ax" x="' + lx.toFixed(1) + '" y="' + (Ht - 6) + '" text-anchor="middle">' + lab + '</text>';
    }
    var bw = Math.max(1, pw / nh * 0.6);
    K.forEach(function (k, i) { var c = k[3] >= k[0] ? LIQ_UP : LIQ_DN, cx = X(i); s += candleMark(cx, bw, Y(k[0]), Y(k[1]), Y(k[2]), Y(k[3]), c); });
    var lc = K[K.length - 1][3]; s += '<line x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + Y(lc).toFixed(1) + '" y2="' + Y(lc).toFixed(1) + '" stroke="' + LIQ_INK + '" stroke-dasharray="2 4" stroke-width="1" opacity=".6"/>';
    var hb = DY ? null : hlBands(), hg = [];   // Hyperliquid 實際清算價是今天的快照，只疊在 3／7 天   // Hyperliquid 實際清算價：右緣往左的橫條，長度按顆數（最長約畫面寬的 22%）
    var hlTip = function (mx, my) { var g = hg.filter(function (q) { return mx >= q.x0 - 2 && my >= q.yt && my <= q.yb; })[0]; if (!g) return ''; return '<div class="r"><i style="background:' + LIQ_HL + '"></i><span>' + _T('Hyperliquid 實際清算（快照）', 'Hyperliquid actual (snapshot)') + ' ' + fmt.k(g.b.lo) + '–' + fmt.k(g.b.hi) + '</span><b>' + _T(g.b.n + ' 個帳戶 · ' + fmt.n(g.b.btc) + ' 顆', g.b.n + ' accts · ' + fmt.n(g.b.btc) + ' BTC') + '</b></div>'; };
    if (hb && hb.rows.length) {
      var hm = Math.max.apply(null, hb.rows.map(function (b) { return b.btc; }));
      hb.rows.forEach(function (b) {
        if (b.hi <= pLo || b.lo >= pHi) return;
        var yt = Y(Math.min(b.hi, pHi)), yb = Y(Math.max(b.lo, pLo)), len = Math.max(8, b.btc / hm * pw * 0.22), x0 = ML + pw - len;
        hg.push({ b: b, x0: x0, yt: yt, yb: yb });
        s += '<rect x="' + x0.toFixed(1) + '" y="' + (yt + 0.5).toFixed(1) + '" width="' + len.toFixed(1) + '" height="' + Math.max(2, yb - yt - 1).toFixed(1) + '" rx="1.5" fill="' + LIQ_HL + '" fill-opacity=".72" stroke="#0C0C0D" stroke-opacity=".55" stroke-width="1"/>';
      });
      var big = hg.slice().sort(function (a, c) { return c.b.btc - a.b.btc; })[0];
      if (big) s += '<text class="ax" x="' + (big.x0 - 4).toFixed(1) + '" y="' + ((big.yt + big.yb) / 2 + 3.5).toFixed(1) + '" text-anchor="end" style="fill:' + LIQ_HL + ';paint-order:stroke;stroke:#0C0C0D;stroke-width:3px">HL ' + fmt.n(big.b.btc) + _T(' 顆', ' BTC') + '</text>';
    }
    s += '<line class="xh" x1="0" x2="0" y1="' + MT + '" y2="' + (MT + ph) + '" visibility="hidden"/><line class="xh yh" x1="' + ML + '" x2="' + (ML + pw) + '" y1="0" y2="0" visibility="hidden"/><rect class="hit" x="' + ML + '" y="' + MT + '" width="' + pw + '" height="' + ph + '"/>';
    el.innerHTML = '<canvas width="' + Math.round(pw * dpr) + '" height="' + Math.round(ph * dpr) + '" style="position:absolute;left:' + (ML / W * 100).toFixed(3) + '%;top:' + (MT / Ht * 100).toFixed(3) + '%;width:' + (pw / W * 100).toFixed(3) + '%;height:' + (ph / Ht * 100).toFixed(3) + '%"></canvas>' + svgEl(W, Ht, s, _T('清算熱力圖（推算）', 'Liquidation heatmap (estimate)'));
    var svg = el.querySelector('svg'); svg.style.position = 'relative';
    var oc = document.createElement('canvas'); oc.width = nh; oc.height = rows; var ox = oc.getContext('2d'), im = ox.createImageData(nh, rows);
    for (i = 0; i < nh; i++) for (j = 0; j < rows; j++) { var cc = liqCol(gam(U[(h0 + i) * nb + b0 + j] / top)), q = ((rows - 1 - j) * nh + i) * 4; im.data[q] = cc[0]; im.data[q + 1] = cc[1]; im.data[q + 2] = cc[2]; im.data[q + 3] = 255; }
    ox.putImageData(im, 0, 0);
    var cv = el.querySelector('canvas').getContext('2d'); cv.imageSmoothingEnabled = false; cv.drawImage(oc, 0, 0, Math.round(pw * dpr), Math.round(ph * dpr));
    var xh = svg.querySelector('.xh'), yh = svg.querySelector('.yh'), hit = svg.querySelector('.hit');
    function move(ev) {
      var r = svg.getBoundingClientRect(), mx = (ev.clientX - r.left) * W / r.width, my = (ev.clientY - r.top) * Ht / r.height;
      var i = Math.max(0, Math.min(nh - 1, Math.floor((mx - ML) / pw * nh))), j = Math.max(0, Math.min(rows - 1, Math.floor((1 - (my - MT) / ph) * rows))), k = K[i], lo = pLo + j * x.step;
      xh.setAttribute('x1', X(i)); xh.setAttribute('x2', X(i)); xh.setAttribute('visibility', 'visible'); yh.setAttribute('y1', my); yh.setAttribute('y2', my); yh.setAttribute('visibility', 'visible');
      var q = U[(h0 + i) * nb + b0 + j] / 255 * x.cap, side = lo >= k[3] ? _T('空單', 'shorts') : _T('多單', 'longs'), ti = v.t(i);
      showTip(ev.clientX, ev.clientY, '<div class="t">' + (DY ? ymdS(new Date(ti).toISOString().slice(0, 10)) : liqHour(ti) + ' UTC') + '</div><div class="r"><i style="background:rgb(' + liqCol(gam(q / x.cap * 255 / top)).join(',') + ')"></i><span>' + fmt.usd(lo) + '–' + fmt.n(lo + x.step) + ' ' + side + '</span><b>' + (q >= 0.5 ? liqBtc(Math.round(q)) : '—') + '</b></div><div class="r"><i style="background:' + (k[3] >= k[0] ? LIQ_UP : LIQ_DN) + '"></i><span>' + (DY ? _T('當天收盤', 'Day close') : _T('這小時收盤', 'Hour close')) + '</span><b>' + fmt.usd(k[3]) + '</b></div>' + hlTip(mx, my));
    }
    hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', function () { xh.setAttribute('visibility', 'hidden'); yh.setAttribute('visibility', 'hidden'); hideTip(); });
  }
  function liqAfter() {
    mount($('#c-liq'), drawLiq);
    mount($('#c-lqv'), drawLqv);   // 2026-11-08 每日多空清算量
    mount($('#c-fh'), drawFh); mount($('#c-oih'), drawOih); mount($('#c-lsa'), drawLsa); mount($('#c-tk'), drawTk);   // 2026-11-08 Coinalyze 日線四張圖
    var sg = $('#liq-segs'); if (sg) sg.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b || +b.getAttribute('data-d') === liqDays) return; liqDays = +b.getAttribute('data-d'); liqLErr = false; sg.innerHTML = liqSegs(); drawLiq($('#c-liq')); });
  }

  /* 每日多空清算量（2026-11-08 使用者要求，X 上清算圖的「30 天多單清算比較多」）：Coinalyze 彙整的交易所實際強制平倉紀錄（美元），不是推算。
     交易所公開的清算資料會少報（Binance 每秒只推一筆），所以看多空比例、不看總額。見 pipeline/liq_heat.py build_vol */
  function lqvM(v) { return v == null ? '—' : Math.abs(v) >= 1000 ? '$' + fmt.n(v / 1000, 2) + 'B' : '$' + fmt.n(v, 0) + 'M'; }
  var LQ_T = function (v) { return (v >= 0 ? 1 : -1) * Math.sqrt(Math.abs(v)); };   // 平方根壓縮：大清算日不會把平常的日子壓扁
  function lqvSay() {
    var x = D.deriv.liq_vol, it = [], d30 = x.d30, hl = x.hi_long || {}, st = hl.st || {}, ev = (hl.ev || [])[(hl.ev || []).length - 1];
    it.push([_T('近 30 天', 'Past 30 days'), _T('多單占 ', 'Longs ') + fmt.n(d30.share, 0) + '%',
      _T('多單被清算 ' + lqvM(d30.long) + '、空單 ' + lqvM(d30.short) + '，多單占 ' + fmt.n(d30.share, 1) + '%，高於 ' + oxYm(x.from_) + ' 以來 ' + x.share_pct + '% 的 30 天期間。近 7 天多單占 ' + fmt.n(x.d7.share, 0) + '%、近 90 天 ' + fmt.n(x.d90.share, 0) + '%。多單被清算多＝下跌時被迫賣出的多；空單多＝上漲時被迫買回的多。',
        'Longs liquidated ' + lqvM(d30.long) + ', shorts ' + lqvM(d30.short) + ': longs are ' + fmt.n(d30.share, 1) + '%, higher than ' + x.share_pct + '% of 30-day periods since ' + oxYm(x.from_) + '. Past 7 days ' + fmt.n(x.d7.share, 0) + '% longs, past 90 days ' + fmt.n(x.d90.share, 0) + '%. More long liquidations = more forced selling on the way down; more short liquidations = more forced buying on the way up.'), 'neu']);
    it.push([_T('30 天總量', '30-day total'), lqvM(d30.long + d30.short),
      _T('比 ' + oxYm(x.from_) + ' 以來 ' + x.tot30_pct + '% 的 30 天期間多。最近一天（' + ymdS(x.date) + '）多單 ' + lqvM(x.day.long) + '、空單 ' + lqvM(x.day.short) + '。',
        'More than ' + x.tot30_pct + '% of 30-day periods since ' + oxYm(x.from_) + '. Latest day (' + ymdS(x.date) + '): longs ' + lqvM(x.day.long) + ', shorts ' + lqvM(x.day.short) + '.'), 'neu']);
    if (st.n) it.push([_T('多單占比 ≥ ' + hl.th + '% 之後', 'After long share ≥ ' + hl.th + '%'), st.n + _T(' 次', ' times'),
      _T('30 天多單占比升到 ' + hl.th + '% 以上（相隔 30 天以上算新的一次）之後 90 天：', 'After the 30-day long share rose to ' + hl.th + '%+ (30+ days apart), 90 days later: ') + oxStat(st, x.base) +
      _T('。' + (ev ? '最近一次 ' + ymdS(ev.date) + '，90 天後 ' + fmt.pct(ev.r90, 1) + '。' : '') + (d30.share >= hl.th ? '現在就在這個區間。' : '現在 ' + fmt.n(d30.share, 0) + '%，還沒到。') + '資料只從 ' + oxYm(x.from_) + ' 開始、樣本少，不是買賣訊號。',
        '.' + (ev ? ' Latest ' + ymdS(ev.date) + ', ' + fmt.pct(ev.r90, 1) + ' 90 days later.' : '') + (d30.share >= hl.th ? ' It is in that zone now.' : ' Now ' + fmt.n(d30.share, 0) + '%, not there yet.') + ' Data only since ' + oxYm(x.from_) + ' and few cases; not a trading signal.'), 'neu']);
    it.push([_T('資料範圍', 'Coverage'), x.exch.length + _T(' 家交易所', ' exchanges'),
      _T(x.exch.join('、') + ' 的 BTC 永續。' + (x.missing && x.missing.length ? x.missing.join('、') + ' 沒有近期的清算紀錄，不計入。' : '') + 'Hyperliquid 的清算量很大（大清算日可能比其他幾家加起來還多），但沒有公開、持續更新又分多空的資料；Binance 公開的清算資料每秒只推一筆，也少報很多。所以總額只是下限：適合比多空，不適合看總額。',
        'BTC perpetuals on ' + x.exch.join(', ') + '.' + (x.missing && x.missing.length ? ' ' + x.missing.join(' and ') + ' have no recent liquidation records and are left out.' : '') + ' Hyperliquid liquidations are large (on big days possibly more than the others combined) but have no public, up-to-date long/short data, and Binance publishes at most one liquidation per second. Totals are a floor: compare longs with shorts, not the totals.'), 'neu']);
    return it;
  }
  function lqvPanel() {
    var x = (D.deriv || {}).liq_vol; if (!x || !x.rows) return '';
    return panel('span-12', _T('每日多空清算量', 'Daily long and short liquidations'), 'Coinalyze · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard('var(--down)', _T('30 天多單被清算', 'Longs liquidated, 30d'), lqvM(x.d30.long), _T('占 ' + fmt.n(x.d30.share, 0) + '%', fmt.n(x.d30.share, 0) + '% of the total')) +
      oxCard('var(--up)', _T('30 天空單被清算', 'Shorts liquidated, 30d'), lqvM(x.d30.short), _T('占 ' + fmt.n(100 - x.d30.share, 0) + '%', fmt.n(100 - x.d30.share, 0) + '% of the total')) + '</div>' +
      interpHtml(lqvSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('空單被清算（往上）', 'Shorts liquidated (up)'), 'var(--up)', 'box'], [_T('多單被清算（往下）', 'Longs liquidated (down)'), 'var(--down)', 'box']]) +
      '<div class="chart cf-chart" id="c-lqv"></div><p class="note">' + _T('每天被強制平倉的 BTC 永續多單、空單（美元，UTC 日），Coinalyze 彙整的交易所實際清算紀錄，不是推算。刻度壓縮過（平方根），大清算日不會把平常的日子壓扁。膠囊是 ' + oxYm(x.from_) + ' 以來清算最多的幾天。只作讀值。',
        'BTC perpetual longs and shorts force-closed each day (USD, UTC days), from exchange liquidation records compiled by Coinalyze; not an estimate. The scale is compressed (square root) so the biggest days do not flatten the rest. Capsules mark the largest days since ' + oxYm(x.from_) + '. Reading only.') +
      ' <a href="' + (x.link || 'https://coinalyze.net') + '" target="_blank" rel="noopener">' + _T('資料：Coinalyze ↗', 'Data: Coinalyze ↗') + '</a></p>', '', 'lqv');
  }
  function drawLqv(el) {
    var x = (D.deriv || {}).liq_vol; if (!x || !el) return;
    var mk = (x.top || []).map(function (t) { var L = t.long >= t.short; return { x: dnOf(t.date), y: L ? -t.long : t.short, t: ymdS(t.date).slice(2) + ' ' + lqvM(L ? t.long : t.short), col: L ? 'var(--down)' : 'var(--up)', up: !L }; });
    oxPane(el, { rows: x.rows, rng: 365, zero: true, tf: LQ_T,   // 不用 fit：手機不分範圍、畫全部，縱軸要包含全部（平方根刻度下差別很小）
      ticks: [-1000, -300, -100, -20, 0, 20, 100, 300, 1000], fmt: function (t) { var a = Math.abs(t); return !t ? '0' : a >= 1000 ? '$' + a / 1000 + 'B' : '$' + a + 'M'; },
      label: _T('每日清算量（美元，壓縮刻度）', 'Daily liquidations (USD, compressed scale)'), aria: _T('BTC 價格與每日多空清算量', 'BTC price and daily long and short liquidations'),
      bars: [{ i: 2, pos: 'var(--up)', neg: 'var(--up)', op: 0.85, name: _T('空單被清算', 'Shorts liquidated'), tfmt: function (v) { return lqvM(v); } },
        { i: 3, pos: 'var(--down)', neg: 'var(--down)', op: 0.85, name: _T('多單被清算', 'Longs liquidated'), tfmt: function (v) { return lqvM(-v); } }],
      marks: mk });
  }

  /* 2026-11-08 使用者要求（「四項都做」）：Coinalyze 日線的四張圖，資料見 pipeline/cz_viz.py。統計只是歷史描述，不是買賣訊號 */
  function czSrc(x) { return ' <a href="' + (x.link || 'https://coinalyze.net') + '" target="_blank" rel="noopener">' + _T('資料：Coinalyze ↗', 'Data: Coinalyze ↗') + '</a>'; }
  function czEv(e) { return e ? _T('最近一次 ' + ymdS(e.date) + '（' + fmt.usd(e.price) + '）' + (e.r90 != null ? '，90 天後 ' + fmt.pct(e.r90, 1) : '，還不到 90 天') + '。', ' Latest ' + ymdS(e.date) + ' (' + fmt.usd(e.price) + ')' + (e.r90 != null ? ', ' + fmt.pct(e.r90, 1) + ' 90 days later.' : ', under 90 days ago.')) : ''; }
  function czLast(g) { var e = (g || {}).ev || []; return e[e.length - 1]; }
  function btcS(v) { return v == null ? '—' : (v > 0 ? '+' : '') + fmt.n(v, 0); }

  /* ① 資金費率歷史 */
  function fhSay() {
    var x = D.deriv.fund_hist, it = [], ng = x.neg || {}, ht = x.hot || {};
    it.push([_T('7 日平均', '7-day average'), fmt.pct(x.value, 1),
      _T('多家永續以未平倉加權的資金費率，7 日平均年化 ' + fmt.pct(x.value, 1) + '（30 天前 ' + fmt.pct(x.v30, 1) + '），高於 ' + oxYm(x.from_) + ' 以來 ' + x.pct + '% 的日子；已連續 ' + x.run + ' 天' + (x.value >= 0 ? '為正（多方付費給空方）' : '為負（空方付費給多方）') + '。' + oxYm(x.from_) + ' 以來最高是 ' + ymdS(x.hi.date) + ' 的 ' + fmt.pct(x.hi.value, 0) + '。',
        'Open-interest-weighted funding across perpetuals, 7-day average ' + fmt.pct(x.value, 1) + ' annualized (' + fmt.pct(x.v30, 1) + ' 30 days ago), higher than ' + x.pct + '% of days since ' + oxYm(x.from_) + '; ' + (x.value >= 0 ? 'positive (longs pay shorts)' : 'negative (shorts pay longs)') + ' for ' + x.run + ' days. The high since ' + oxYm(x.from_) + ' was ' + fmt.pct(x.hi.value, 0) + ' on ' + ymdS(x.hi.date) + '.'), x.value >= (ht.th || 30) ? 'warn' : 'neu']);
    if (ng.st && ng.st.n) it.push([_T('轉負之後', 'After turning negative'), ng.st.n + _T(' 次', ' times'),
      _T('7 日平均由正轉負（相隔 30 天以上算新的一次）之後 90 天：', 'After the 7-day average turned negative (30+ days apart), 90 days later: ') + oxStat(ng.st, x.base) + _T('。', '.') + czEv(czLast(ng)) + _T('空方付費代表槓桿偏空、多單已經被洗掉，過去多半出現在低點附近，但次數不多。', ' Shorts paying means leverage leans short and longs have been flushed; historically this came near lows, but the sample is small.'), 'neu']);
    if (ht.st && ht.st.n) it.push([_T('升到 ' + ht.th + '% 以上之後', 'After rising above ' + ht.th + '%'), ht.st.n + _T(' 次', ' times'),
      _T('7 日平均升到 ' + ht.th + '% 以上之後 90 天：', 'After the 7-day average rose above ' + ht.th + '%, 90 days later: ') + oxStat(ht.st, x.base) + _T('。', '.') + czEv(czLast(ht)) + _T('多方付很高的費用＝槓桿多單擁擠，之後常有一次清洗，但牛市裡也可能撐很久。', ' Longs paying a lot = crowded leveraged longs, often followed by a flush, though in bull markets it can last.'), 'neu']);
    it.push([_T('怎麼算', 'Method'), x.venues.length + _T(' 家', ' venues'),
      _T(x.venues.join('、') + ' 的 BTC 永續（Hyperliquid 2024-10 起才有）。每日值＝當天費率的（開＋高＋低＋收）÷ 4，換成年化後以未平倉加權。和上面「永續資金費率」的即時快照不同，這是每日平均，兩個數字會差一點。',
        'BTC perpetuals on ' + x.venues.join(', ') + ' (Hyperliquid only from 2024-10). Each day\'s value = (open + high + low + close) ÷ 4 of that day\'s rate, annualized and weighted by open interest. This is a daily average, not the live snapshot shown in "Perpetual funding" above, so the two differ a little.'), 'neu']);
    return it;
  }
  /* 2026-11-09 使用者要求「借鑑 Tidemark 的歷史圖」：Tidemark（第三方模型）頂部／底部訊號 2011 起的歷史（2025-11 起每日）。
     借：頂部／底部兩個視角、可點的圖例（開關每條線）、滑過時更新的讀數列；不借：極光底色、發光線、價格疊在右軸（本站一張圖一個 y 軸）。
     顏色照紅綠規則：頂部訊號紅、底部訊號綠；熱度琥珀、冷度藍、時機灰虛線。只作讀值 */
  var TMH = {   // [欄位, rows 第幾欄, 顏色, 中文, 英文, 主線]
    top: { lines: [['sig', 2, 'var(--down)', '頂部訊號', 'Top signal', 1], ['heat', 3, 'var(--warn)', '熱度', 'Heat', 0], ['tim', 4, 'var(--ink-3)', '時機', 'Timing', 0]],
      refs: [[50, '50 窗口', '50 window'], [70, '70 警戒', '70 alert']], marks: 'tops', mk: ['歷次週期頂部', 'Past cycle tops'], tag: [' 頂', ' top'] },
    bottom: { lines: [['bsig', 5, 'var(--up)', '底部訊號', 'Bottom signal', 1], ['cold', 6, 'var(--orbit)', '冷度', 'Cold', 0]],
      refs: [[50, '50 底部區', '50 bottom zone']], marks: 'bottoms', mk: ['歷次週期底部', 'Past cycle bottoms'], tag: [' 底', ' bottom'] }
  };
  function tmhMode(el) { return (el && el._mode) || 'top'; }
  function tmhPanel() {
    var x = ((D.cycle || {}).tidemark || {}).hist; if (!x || !x.rows) return '';
    var seg = '<div class="seg tm-mode" role="group" aria-label="' + _T('視角', 'View') + '"><button type="button" data-m="top" aria-pressed="true">' + _T('頂部視角', 'Top view') + '</button><button type="button" data-m="bottom" aria-pressed="false">' + _T('底部視角', 'Bottom view') + '</button></div>';
    return panel('span-12', _T('Tidemark 歷史：頂部與底部訊號', 'Tidemark history: top and bottom signals'),
      _T('第三方模型 · ' + x.from_.slice(0, 4) + ' 起每週、近一年每日 · ' + fmt.md(x.to) + (x.stale ? ' · 沿用上一份' : ''), 'third-party model · weekly since ' + x.from_.slice(0, 4) + ', daily for the past year · ' + fmt.md(x.to) + (x.stale ? ' · previous copy' : '')),
      '<div class="tmh-top">' + seg + '<p class="tmh-read mono"></p></div><div class="legend tmh-chips"></div><div class="chart" id="c-tmh"></div>' +
      '<p class="note">' + _T('Tidemark 是第三方公開模型（north7.github.io/tidemark），頂部訊號＝熱度（估值、資金、衍生品、情緒等五類加權）× 時機（離上一個低點與減半的天數）；底部訊號＝冷度（估值、礦工、價格結構）× 時機。歷史是 Tidemark 用目前的規則回算的，部分指標 2012 年底以後才有。本站只轉錄、不改數字；只作讀值，不連動倉位。',
        'Tidemark is a public third-party model (north7.github.io/tidemark): top signal = heat (valuation, flows, derivatives, sentiment and more, weighted) × timing (days since the last low and the halving); bottom signal = cold (valuation, miners, price structure) × timing. The history is back-calculated by Tidemark under its current rules, and some inputs start only in late 2012. We copy the numbers without changing them; reading only, not tied to positions.') + '</p>', '', 'tmh');
  }
  function tmhRead(el, p) {
    var x = D.cycle.tidemark.hist, R_ = x.rows, M = TMH[tmhMode(el)], pn = el.closest('.panel'), box = pn && pn.querySelector('.tmh-read'); if (!box) return;
    if (!p) p = R_[R_.length - 1];
    box.innerHTML = '<b>' + fmt.date(p[0]) + '</b><span>' + fmt.usd(p[1]) + '</span>' + M.lines.map(function (l) { return '<span><i style="background:' + l[2] + '"></i>' + _T(l[3], l[4]) + ' <b>' + (p[l[1]] == null ? '—' : fmt.n(p[l[1]], 0)) + '</b></span>'; }).join('');
  }
  function tmhChips(el) {
    var x = D.cycle.tidemark.hist, m = tmhMode(el), M = TMH[m], hide = el._hide || {}, pn = el.closest('.panel'), box = pn && pn.querySelector('.tmh-chips'); if (!box) return;
    var st = function (col, cls, t) { return '<span style="color:' + col + '"><i class="' + cls + '"></i><b style="color:var(--ink-2);font-weight:400">' + t + '</b></span>'; };
    box.innerHTML = st('var(--ink-2)', '', _T('BTC 價格（上格）', 'BTC price (top pane)')) +
      M.lines.map(function (l) { return '<button type="button" class="tmh-chip" data-k="' + l[0] + '" aria-pressed="' + !hide[l[0]] + '" style="color:' + l[2] + '"><i class="' + (l[0] === 'tim' ? 'dash' : '') + '"></i><b>' + _T(l[3], l[4]) + '</b></button>'; }).join('') +
      st('var(--ink-3)', 'dash', _T(M.mk[0], M.mk[1])) + (m === 'bottom' && x.low && x.low.date ? st('var(--up)', 'dots', _T('本輪低點（待驗證）', 'This cycle\'s low (being tested)')) : '');
  }
  function drawTmh(el) {
    var x = ((D.cycle || {}).tidemark || {}).hist; if (!x || !x.rows || !el) return;
    var m = tmhMode(el), M = TMH[m], hide = el._hide || (el._hide = {}), main = M.lines[0], mk = x[M.marks] || [];
    oxPane(el, { rows: x.rows, y0: 0, y1: 100, ticks: [0, 25, 50, 75, 100], fmt: function (t) { return String(t); },
      label: _T('Tidemark ' + (m === 'top' ? '頂部' : '底部') + '視角（0–100）', 'Tidemark ' + m + ' view (0–100)'), aria: _T('BTC 價格與 Tidemark 頂部、底部訊號的歷史', 'BTC price and the history of Tidemark\'s top and bottom signals'),
      refs: M.refs.map(function (r) { return { y: r[0], col: 'var(--ink-3)', lab: _T(r[1], r[2]) }; }),
      lines: M.lines.filter(function (l) { return !hide[l[0]]; }).map(function (l) { return { i: l[1], col: l[2], w: l[5] ? 2.2 : 1.3, area: !!l[5], dash: l[0] === 'tim' ? '4 3' : null, name: _T(l[3], l[4]), tfmt: function (v) { return fmt.n(v, 1); } }; }),
      over: function (C) {
        var s = '', a = C.rows[0][0], b = C.rows[C.rows.length - 1][0];
        var vl = function (d, col, dash, lab) { var cx = C.X(d).toFixed(1); var rt = +cx > C.ML + C.pw - 90; return '<line x1="' + cx + '" x2="' + cx + '" y1="' + C.MT + '" y2="' + C.yb + '" stroke="' + col + '" stroke-width="1" stroke-dasharray="' + dash + '"/>' + (lab && !C.sm ? axText(+cx + (rt ? -4 : 4), C.ys0 + 11, lab, rt ? 'end' : 'start') : ''); };
        mk.forEach(function (t) { var d = dnOf(t); if (d >= a && d <= b) s += vl(d, 'var(--ink-3)', '3 3', t.slice(0, 4) + _T(M.tag[0], M.tag[1])); });
        if (m === 'bottom' && x.low && x.low.date) { var d = dnOf(x.low.date); if (d >= a && d <= b) s += vl(d, 'var(--up)', '1 3', _T('本輪低點 ', 'Low ') + fmt.k(x.low.price)); }
        return s;
      },
      now: hide[main[0]] ? null : { i: main[1], col: main[2], lab: '' },
      tipExtra: function (p) { tmhRead(el, p); return ''; } });
    var hit = el.querySelector('.hit'); if (hit) hit.addEventListener('pointerleave', function () { tmhRead(el); });
    tmhRead(el); tmhChips(el);
  }
  function tmhBind() {
    var el = $('#c-tmh'); if (!el) return; mount(el, drawTmh);
    var pn = el.closest('.panel'), sg = pn.querySelector('.tm-mode'), ch = pn.querySelector('.tmh-chips');
    sg.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; el._mode = b.getAttribute('data-m'); [].forEach.call(sg.querySelectorAll('button'), function (q) { q.setAttribute('aria-pressed', q === b); }); el._draw(el); });
    ch.addEventListener('click', function (e) { var b = e.target.closest('.tmh-chip'); if (!b) return; var k = b.getAttribute('data-k'); el._hide = el._hide || {}; el._hide[k] = !el._hide[k]; el._draw(el); });
  }
  /* 2026-11-09 紅綠規則（使用者）：有正負方向的圖一律綠＝正、品牌橘紅＝負；資金費率、鏈上勢能、韓國溢價從類型色改過來 */
  function fhPanel() {
    var x = (D.deriv || {}).fund_hist; if (!x || !x.rows) return '';
    return panel('span-12', _T('資金費率歷史', 'Funding rate history'), 'Coinalyze · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard(x.value >= 0 ? 'var(--up)' : 'var(--down)', _T('7 日平均（年化）', '7-day average (annualized)'), fmt.pct(x.value, 1), _T(oxYm(x.from_) + ' 以來第 ' + x.pct + ' 百分位', ord(x.pct) + ' percentile since ' + oxYm(x.from_)), oxArrow(x.value, x.v30, _T(' 點', ' pts'))) +
      oxCard('var(--ink-3)', _T('最近一天', 'Latest day'), fmt.pct(x.day, 1), _T('當天平均', 'daily average')) + '</div>' +
      interpHtml(fhSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('正：多方付費', 'Positive: longs pay'), 'var(--up)'], [_T('負：空方付費', 'Negative: shorts pay'), 'var(--down)'], [_T('虛線：' + (x.hot || {}).th + '%', 'Dashed: ' + (x.hot || {}).th + '%'), 'var(--warn)']]) +
      '<div class="chart cf-chart" id="c-fh"></div><p class="note">' + _T('資金費率是永續合約每 8 小時（Hyperliquid 每小時）多空之間互付的費用，正＝多方付給空方。這裡是多家以未平倉加權、換成年化的 7 日平均，每 2 天畫一點。只作讀值。',
        'Funding is what longs and shorts pay each other on perpetuals every 8 hours (hourly on Hyperliquid); positive = longs pay shorts. Shown as an open-interest-weighted, annualized 7-day average across venues, plotted every 2 days. Reading only.') + czSrc(x) + '</p>', '', 'fh');
  }
  function drawFh(el) {
    var x = (D.deriv || {}).fund_hist; if (!x || !el) return;
    oxPane(el, { rows: x.rows, rng: 365, fit: true, zero: true, fmt: function (t) { return fmt.n(t, 0) + '%'; },
      label: _T('資金費率 7 日平均（年化 %）', 'Funding, 7-day average (annualized %)'), aria: _T('BTC 價格與資金費率 7 日平均', 'BTC price and the 7-day average funding rate'),
      refs: [{ y: (x.hot || {}).th || 30, col: 'var(--warn)', lab: (x.hot || {}).th + '%' }],
      lines: [{ i: 2, split: ['var(--up)', 'var(--down)'], w: 1.4, name: _T('7 日平均', '7-day average'), tfmt: function (v) { return fmt.pct(v, 1); } }],
      now: { i: 2, col: x.value >= 0 ? 'var(--up)' : 'var(--down)', lab: '' } });
  }

  /* ② 全市場未平倉量 */
  function oihSay() {
    var x = D.deriv.oi_hist, it = [], up = x.chg30 >= 0, pu = x.px30 >= 0;
    it.push([_T('合計', 'Total'), cqKb(x.btc / 1e3).replace('+', '') + _T(' 顆', ' BTC'),
      _T(x.n + ' 個 BTC 永續合約合計約 ' + fmt.n(x.btc) + ' 顆（約 ' + usdB(x.usd_b) + '），高於 ' + oxYm(x.from_) + ' 以來 ' + x.pct + '% 的日子；以顆計的最高是 ' + ymdS(x.hi.date) + ' 的 ' + fmt.n(x.hi.btc) + ' 顆。7 天 ' + fmt.pct(x.chg7, 1) + '、90 天 ' + fmt.pct(x.chg90, 1) + '。',
        x.n + ' BTC perpetual contracts hold about ' + fmt.n(x.btc) + ' BTC (' + usdB(x.usd_b) + '), more than on ' + x.pct + '% of days since ' + oxYm(x.from_) + '; the high in BTC terms was ' + fmt.n(x.hi.btc) + ' on ' + ymdS(x.hi.date) + '. 7 days ' + fmt.pct(x.chg7, 1) + ', 90 days ' + fmt.pct(x.chg90, 1) + '.'), 'neu']);
    var K = { 'dn-up': ['價格跌、未平倉增：逆勢開新倉（新空單或抄底的多單），槓桿在堆，之後容易有一邊被清算。', 'Price down, open interest up: new positions against the move (fresh shorts or dip-buying longs); leverage is building and one side tends to get liquidated later.'],
      'up-up': ['價格漲、未平倉增：新資金用槓桿追，漲勢有一部分靠槓桿撐。', 'Price up, open interest up: new money chasing with leverage; part of the rally rests on leverage.'],
      'dn-dn': ['價格跌、未平倉減：多單在平倉或被清算，槓桿在退。', 'Price down, open interest down: longs closing or being liquidated; leverage is unwinding.'],
      'up-dn': ['價格漲、未平倉減：空單回補推動，槓桿在退。', 'Price up, open interest down: short covering drives it; leverage is unwinding.'] }[(pu ? 'up' : 'dn') + '-' + (up ? 'up' : 'dn')];
    it.push([_T('30 天：價格 vs 未平倉', '30 days: price vs open interest'), fmt.pct(x.px30, 1) + ' / ' + fmt.pct(x.chg30, 1), _T('價格 ' + fmt.pct(x.px30, 1) + '、未平倉 ' + fmt.pct(x.chg30, 1) + '。' + K[0], 'Price ' + fmt.pct(x.px30, 1) + ', open interest ' + fmt.pct(x.chg30, 1) + '. ' + K[1]), !pu && up ? 'warn' : 'neu']);
    it.push([_T('幣本位占比', 'Coin-margined share'), fmt.n(x.coin_share, 1) + '%',
      _T('用 BTC 當保證金的幣本位合約占 ' + fmt.n(x.coin_share, 1) + '%（一年前 ' + fmt.n(x.coin_share_1y, 1) + '%）。幣本位多單在價格跌時保證金也一起縮水，比較容易連環清算；占比越低，這種放大效果越小。',
        'Coin-margined contracts (BTC as collateral) are ' + fmt.n(x.coin_share, 1) + '% (' + fmt.n(x.coin_share_1y, 1) + '% a year ago). Their longs lose collateral value as price falls, which makes cascades likelier; a lower share means less of that amplification.'), 'neu']);
    return it;
  }
  function oihPanel() {
    var x = (D.deriv || {}).oi_hist; if (!x || !x.rows) return '';
    return panel('span-12', _T('全市場未平倉量', 'Total open interest'), 'Coinalyze · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard('var(--s4)', _T('永續未平倉合計', 'Perpetual open interest'), cqKb(x.btc / 1e3).replace('+', ''), _T('顆 · 約 ', 'BTC · about ') + usdB(x.usd_b), oxArrow(x.chg30, 0, '%')) +
      oxCard(x.px30 >= 0 ? 'var(--up)' : 'var(--down)', _T('同期價格（30 天）', 'Price, same 30 days'), fmt.pct(x.px30, 1), _T('未平倉 30 天 ', 'open interest 30d ') + fmt.pct(x.chg30, 1)) + '</div>' +
      interpHtml(oihSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('未平倉（顆）', 'Open interest (BTC)'), 'var(--s4)']]) +
      '<div class="chart cf-chart" id="c-oih"></div><p class="note">' + _T('Coinalyze 彙整的 ' + x.exch.join('、') + ' 共 ' + x.n + ' 個 BTC 永續合約，每日收盤的未平倉量；幣本位合約以美元計，÷ 收盤價換成顆。以顆計，價格漲時同樣的美元會變少顆。合約陸續上線（Binance USDC 2024-01、Hyperliquid 2024），長期增加有一部分是新合約。每 2 天畫一點。只作讀值。',
        'Daily closing open interest of ' + x.n + ' BTC perpetual contracts on ' + x.exch.join(', ') + ' as compiled by Coinalyze; coin-margined contracts are in USD and divided by the close. Measured in BTC, the same dollars mean fewer coins when price rises. Contracts were added over time (Binance USDC 2024-01, Hyperliquid 2024), so part of the long-run rise is new contracts. Plotted every 2 days. Reading only.') + czSrc(x) + '</p>', '', 'oih');
  }
  function drawOih(el) {
    var x = (D.deriv || {}).oi_hist; if (!x || !el) return;
    oxPane(el, { rows: x.rows, rng: 365, fit: true, fmt: cqKt, label: _T('永續未平倉（顆）', 'Perpetual open interest (BTC)'), aria: _T('BTC 價格與全市場未平倉量', 'BTC price and total open interest'),
      lines: [{ i: 2, col: 'var(--s4)', area: true, w: 1.5, name: _T('未平倉', 'Open interest'), tfmt: function (v) { return cqKb(v).replace('+', '') + _T(' 顆', ' BTC'); } }],
      now: { i: 2, col: 'var(--s4)', lab: '' } });
  }

  /* ③ 多空帳戶比 */
  function lsaSay() {
    var x = D.deriv.ls_acct, it = [], hi = x.hi || {}, lo = x.lo || {};
    it.push([_T('現在', 'Now'), 'Binance ' + fmt.n(x.binance, 1) + '%',
      _T('Binance 有 ' + fmt.n(x.binance, 1) + '% 的帳戶持多單（30 天前 ' + fmt.n(x.b30, 1) + '%），高於 ' + oxYm(x.from_) + ' 以來 ' + x.pct + '% 的日子（中位數 ' + fmt.n(x.med, 1) + '%）；Bybit ' + fmt.n(x.bybit, 1) + '%。',
        fmt.n(x.binance, 1) + '% of Binance accounts are long (' + fmt.n(x.b30, 1) + '% 30 days ago), higher than on ' + x.pct + '% of days since ' + oxYm(x.from_) + ' (median ' + fmt.n(x.med, 1) + '%); Bybit ' + fmt.n(x.bybit, 1) + '%.'), x.binance >= x.p90 ? 'warn' : 'neu']);
    if (hi.st && hi.st.n) it.push([_T('偏多帳戶 ≥ ' + fmt.n(x.p90, 1) + '% 之後', 'After long accounts ≥ ' + fmt.n(x.p90, 1) + '%'), hi.st.n + _T(' 次', ' times'),
      _T('Binance 升到 ' + oxYm(x.from_) + ' 以來前 10%（' + fmt.n(x.p90, 1) + '%）之後 90 天：', 'After Binance rose into its top 10% since ' + oxYm(x.from_) + ' (' + fmt.n(x.p90, 1) + '%), 90 days later: ') + oxStat(hi.st, x.base) + _T('。', '.') + czEv(czLast(hi)), 'neu']);
    if (lo.st && lo.st.n) it.push([_T('偏多帳戶 ≤ ' + fmt.n(x.p10, 1) + '% 之後', 'After long accounts ≤ ' + fmt.n(x.p10, 1) + '%'), lo.st.n + _T(' 次', ' times'),
      _T('降到後 10%（' + fmt.n(x.p10, 1) + '%）之後 90 天：', 'After it fell into the bottom 10% (' + fmt.n(x.p10, 1) + '%), 90 days later: ') + oxStat(lo.st, x.base) + _T('。', '.') + czEv(czLast(lo)), 'neu']);
    it.push([_T('怎麼看', 'How to read'), _T('帳戶數', 'Accounts'),
      _T('算的是帳戶數，不是部位大小：一個大戶和一個小散戶都算一個，所以比較像散戶情緒。常被當反向指標（大家都做多時容易往下洗），上面的統計可以看這個說法在這段期間成不成立。只有 Binance、Bybit。',
        'It counts accounts, not position size: a whale and a small trader count once each, so it reads more like retail sentiment. Often used as a contrarian gauge (when everyone is long, price tends to flush them); the stats above show how well that held in this period. Binance and Bybit only.'), 'neu']);
    return it;
  }
  function lsaPanel() {
    var x = (D.deriv || {}).ls_acct; if (!x || !x.rows) return '';
    return panel('span-12', _T('多空帳戶比', 'Long/short account ratio'), 'Coinalyze · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard('var(--s1)', _T('Binance 多單帳戶', 'Binance long accounts'), fmt.n(x.binance, 1) + '%', _T('30 天前 ' + fmt.n(x.b30, 1) + '%', fmt.n(x.b30, 1) + '% 30 days ago'), oxArrow(x.binance, x.b30, _T(' 點', ' pts'))) +
      oxCard('var(--s4)', _T('Bybit 多單帳戶', 'Bybit long accounts'), x.bybit == null ? '—' : fmt.n(x.bybit, 1) + '%', _T('持多單的帳戶占比', 'share of accounts long')) + '</div>' +
      interpHtml(lsaSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], ['Binance', 'var(--s1)'], ['Bybit', 'var(--s4)'], [_T('色帶：Binance 前 10%／後 10%', 'Bands: Binance top / bottom 10%'), 'var(--ink-3)', 'box']]) +
      '<div class="chart cf-chart" id="c-lsa"></div><p class="note">' + _T('BTCUSDT 永續上持多單的帳戶占全部有部位帳戶的比例（%），Coinalyze 彙整，OKX 沒有。紅色帶是 Binance ' + oxYm(x.from_) + ' 以來的前 10%、綠色帶是後 10%。每 2 天畫一點。只作讀值。',
        'Share of accounts holding longs among all accounts with a BTCUSDT perpetual position (%), compiled by Coinalyze; OKX is not available. The red band is Binance\'s top 10% since ' + oxYm(x.from_) + ', the green band its bottom 10%. Plotted every 2 days. Reading only.') + czSrc(x) + '</p>', '', 'lsa');
  }
  function drawLsa(el) {
    var x = (D.deriv || {}).ls_acct; if (!x || !el) return;
    oxPane(el, { rows: x.rows, rng: 365, fit: true, fmt: function (t) { return fmt.n(t, 0) + '%'; }, label: _T('持多單的帳戶占比（%）', 'Accounts long (%)'), aria: _T('BTC 價格與多空帳戶比', 'BTC price and the long/short account ratio'),
      refs: [{ y: 50, col: 'var(--ink-3)', lab: '50%' }], zones: [{ y0: x.p90, y1: 100, col: 'var(--down)', op: 0.08 }, { y0: 0, y1: x.p10, col: 'var(--up)', op: 0.08 }],
      lines: [{ i: 2, col: 'var(--s1)', w: 1.5, name: 'Binance', tfmt: function (v) { return fmt.n(v, 1) + '%'; } }, { i: 3, col: 'var(--s4)', w: 1.2, name: 'Bybit', tfmt: function (v) { return fmt.n(v, 1) + '%'; } }],
      now: { i: 2, col: 'var(--s1)', lab: '' } });
  }

  /* ④ 多交易所主動買賣 */
  function tkSay() {
    var x = D.deriv.taker, it = [], S = x.spot, P = x.perp, C = x.cb;
    var rel = function (g) { return g.d30 >= g.med ? _T('比常態多買', 'more buying than usual') : _T('比常態多賣', 'more selling than usual'); };
    it.push([_T('現貨 30 天', 'Spot, 30 days'), btcS(S.d30),
      _T(x.spot_venues.join('＋') + ' 現貨主動買 − 主動賣 ' + btcS(S.d30) + ' 顆（常態 ' + btcS(S.med) + '，' + oxYm(x.from_) + ' 以來第 ' + S.pct + ' 百分位）：' + rel(S) + '。近 7 天 ' + btcS(S.d7) + ' 顆。',
        'Spot taker buys − sells on ' + x.spot_venues.join(' + ') + ': ' + btcS(S.d30) + ' BTC (typical ' + btcS(S.med) + ', ' + ord(S.pct) + ' percentile since ' + oxYm(x.from_) + '): ' + rel(S) + '. Past 7 days ' + btcS(S.d7) + ' BTC.'), 'neu']);
    it.push([_T('永續 30 天', 'Perpetuals, 30 days'), btcS(P.d30),
      _T(x.perp_venues.join('、') + ' USDT 永續 ' + btcS(P.d30) + ' 顆（常態 ' + btcS(P.med) + '，第 ' + P.pct + ' 百分位）：' + rel(P) + '。永續的主動賣長期就比主動買多，所以要和常態線比，不是看正負。',
        x.perp_venues.join(', ') + ' USDT perpetuals: ' + btcS(P.d30) + ' BTC (typical ' + btcS(P.med) + ', ' + ord(P.pct) + ' percentile): ' + rel(P) + '. Perpetual taker selling runs above taker buying over time, so compare with the typical line, not with zero.'), 'neu']);
    it.push([_T('Coinbase 現貨', 'Coinbase spot'), btcS(C.d30),
      _T('美國現貨的代表：30 天 ' + btcS(C.d30) + ' 顆（常態 ' + btcS(C.med) + '，第 ' + C.pct + ' 百分位），近 7 天 ' + btcS(C.d7) + ' 顆。' + (C.pct <= 10 ? '賣得比平常重很多，和 Coinbase 溢價偏負是同一件事。' : C.pct >= 90 ? '買得比平常多很多，和 Coinbase 溢價偏正是同一件事。' : ''),
        'The US spot proxy: ' + btcS(C.d30) + ' BTC over 30 days (typical ' + btcS(C.med) + ', ' + ord(C.pct) + ' percentile), ' + btcS(C.d7) + ' BTC in the past 7 days.' + (C.pct <= 10 ? ' Selling is much heavier than usual, the same story as a negative Coinbase premium.' : C.pct >= 90 ? ' Buying is much heavier than usual, the same story as a positive Coinbase premium.' : '')), C.pct <= 10 ? 'warn' : 'neu']);
    var sR = S.d30 - S.med, pR = P.d30 - P.med;
    it.push([_T('誰在推', 'Who is pushing'), sR >= 0 && pR < 0 ? _T('現貨', 'Spot') : pR >= 0 && sR < 0 ? _T('永續', 'Perps') : sR >= 0 ? _T('兩邊都買', 'Both buying') : _T('兩邊都賣', 'Both selling'),
      _T('和各自的常態比：現貨' + (sR >= 0 ? '偏買' : '偏賣') + ' ' + fmt.n(Math.abs(sR), 0) + ' 顆、永續' + (pR >= 0 ? '偏買' : '偏賣') + ' ' + fmt.n(Math.abs(pR), 0) + ' 顆。現貨主導的走勢通常比永續（槓桿）主導的走得穩。',
        'Against their typical levels: spot leans ' + (sR >= 0 ? 'buy' : 'sell') + ' by ' + fmt.n(Math.abs(sR), 0) + ' BTC, perpetuals lean ' + (pR >= 0 ? 'buy' : 'sell') + ' by ' + fmt.n(Math.abs(pR), 0) + ' BTC. Moves led by spot usually hold better than ones led by perpetuals (leverage).'), 'neu']);
    return it;
  }
  function tkPanel() {
    var x = (D.deriv || {}).taker; if (!x || !x.rows) return '';
    return panel('span-12', _T('現貨與永續的主動買賣（多交易所）', 'Spot vs perpetual taker flow (multi-exchange)'), 'Coinalyze · Binance · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard(x.spot.d30 >= x.spot.med ? 'var(--up)' : 'var(--down)', _T('現貨 30 天', 'Spot, 30 days'), btcS(x.spot.d30), _T('顆 · 常態 ' + btcS(x.spot.med), 'BTC · typical ' + btcS(x.spot.med))) +
      oxCard(x.perp.d30 >= x.perp.med ? 'var(--up)' : 'var(--down)', _T('永續 30 天', 'Perpetuals, 30 days'), btcS(x.perp.d30), _T('顆 · 常態 ' + btcS(x.perp.med), 'BTC · typical ' + btcS(x.perp.med))) + '</div>' +
      interpHtml(tkSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('現貨 30 天', 'Spot, 30 days'), 'var(--s1)'], [_T('永續 30 天', 'Perpetuals, 30 days'), 'var(--s2)'], [_T('虛線：各自的常態（中位數）', 'Dashed: each one\'s typical level (median)'), 'var(--ink-3)']]) +
      '<div class="chart cf-chart" id="c-tk"></div><p class="note">' + _T('主動買 − 主動賣（吃單方向，不含掛單）的 30 天加總，單位顆。現貨：Binance BTCUSDT（Binance 公開資料）＋Coinbase＋Bybit；永續：Binance、Bybit、OKX 的 USDT 永續（Coinalyze；Binance 現貨和 OKX 現貨不在 Coinalyze 裡）。永續長期主動賣偏多，虛線是各自的中位數。每 2 天畫一點。只作讀值。',
        '30-day sum of taker buys − taker sells (aggressor side, excluding makers), in BTC. Spot: Binance BTCUSDT (Binance public data) + Coinbase + Bybit; perpetuals: USDT perpetuals on Binance, Bybit and OKX (Coinalyze, which lacks Binance and OKX spot). Perpetual taker selling runs high over time; the dashed lines are each series\' median. Plotted every 2 days. Reading only.') + czSrc(x) + '</p>', '', 'tk');
  }
  function drawTk(el) {
    var x = (D.deriv || {}).taker; if (!x || !el) return;
    oxPane(el, { rows: x.rows, rng: 365, fit: true, zero: true, fmt: cqKt, label: _T('主動買 − 賣，30 天加總（顆）', 'Taker buy − sell, 30-day sum (BTC)'), aria: _T('BTC 價格與現貨、永續主動買賣', 'BTC price with spot and perpetual taker flow'),
      refs: [{ y: x.spot.med / 1e3, col: 'var(--s1)' }, { y: x.perp.med / 1e3, col: 'var(--s2)' }],
      lines: [{ i: 2, col: 'var(--s1)', w: 1.5, name: _T('現貨', 'Spot'), tfmt: function (v) { return btcS(v * 1e3) + _T(' 顆', ' BTC'); } }, { i: 3, col: 'var(--s2)', w: 1.5, name: _T('永續', 'Perpetuals'), tfmt: function (v) { return btcS(v * 1e3) + _T(' 顆', ' BTC'); } }] });
  }

  V.deriv = function () {
    var dv = D.deriv, d = dv.deriv || {}, r = dv.rr25 || {}, o = dv.options || {};
    var big = (o.expiries || []).slice().sort(function (a, b) { return b.oi - a.oi; })[0] || {};
    return readBar('deriv') + '<div class="kpis">' + kpi('DVOL', fmt.n((dv.dvol || {}).value, 1), _t('一年第 ') + fmt.n((dv.dvol || {}).pct_1y, 0) + _t(' 百分位'), (dv.dvol || {}).pct_1y) + (concNow() ? kpi(_T('籌碼集中度 ±5%', 'Supply within ±5%'), fmt.n(concNow().pct, 1) + '%', _T('URPD ' + fmt.md(concNow().urpd_date) + ' · 只作讀值', 'URPD ' + fmt.md(concNow().urpd_date) + ' · reading only')) : '') + kpi(_t('IV − RV30（同源）'), fmt.n((dv.samesource || {}).iv_minus_rv30, 2), _t('負值＝隱含波動比實際便宜')) + kpi(_t('永續資金費率'), fmt.pct(fundNow(), 1), _T('年化 · 多家加權 · 基差中位 ', 'annualized · multi-venue weighted · basis ') + fmt.n(d.basis_median, 1) + '%') + kpi(_t('25Δ 風險逆轉'), fmt.n(r.rr, 2), r.expiry ? r.expiry + ' · ATM ' + fmt.n(r.atm_iv, 1) + '%' : _t('本日沒有可計算的合約')) + kpi(_t('選擇權未平倉'), fmt.n(o.total_oi) + _t(' 顆'), _t('最大到期 ') + (big.expiry || '—') + _t('（') + fmt.n(big.share, 0) + _t('%）')) + '</div><div class="grid">' + interpPanel(dvInterp()) +
      grpH('dv-vol', '波動率', 'Volatility', _T('選擇權預期接下來會動多大', 'How big a move options are pricing')) +   // 2026-11-08 內容重組：衍生品版分四組
      panel('span-12', _t('隱含波動 vs 實際波動'), _t('Deribit DVOL · Kraken RV30 · 近一年'), legend([['DVOL', 'var(--s4)'], ['RV30', 'var(--s1)']]) + '<div class="chart" id="c-vol"></div>') +
      ivtPanel() +   // 2026-11-08 隱含波動率期限結構
      grpH('dv-lev', '槓桿與清算', 'Leverage and liquidations', _T('槓桿有多擠、哪裡會被清算', 'How crowded leverage is and where liquidations sit')) +
      panel('span-12', _t('期貨基差曲線'), _t('年化 % · 排除 7 天內到期'), basisSay(d.basis_curve) + _t('<div class="chart" id="c-basis"></div><p class="note">資金費率年化 ') + fmt.pct(fundNow(), 1) + _t('；永續 OI ') + fmt.usd(d.perp_oi_usd_m) + _t('M。</p><div class="src-link">外部：<a href="https://www.coinglass.com/pro/futures/LiquidationHeatMap" target="_blank" rel="noopener">CoinGlass 爆倉熱力圖 ↗</a>（以 OI 與假設槓桿推估，非實際倉位）</div>')) +
      fhPanel() + oihPanel() + lsaPanel() + liqPanel() + lqvPanel() +   // 2026-11-08 資金費率歷史、全市場未平倉、多空帳戶比（Coinalyze）
      grpH('dv-opt', '選擇權部位', 'Options positioning', _T('未平倉堆在哪、做市商怎麼避險、錢押哪一邊', 'Where open interest sits, how dealers hedge, which side money pays for')) +
      panel('span-6', _t('各到期未平倉'), _t('買權 / 賣權（顆）'), legend([[_t('買權'), 'var(--up)'], [_t('賣權'), 'var(--down)']]) + '<div class="chart" id="c-oi"></div>') +
      panel('span-6', _T('主要到期的履約價分布', 'Open interest by strike, main expiries'), skTotals(), '<div id="sk-say">' + strikeSay(skRow() || big) + '</div><div id="c-strike"></div>', skSegs()) + gxPanel() + prPanel() +
      grpH('dv-spot', '現貨訂單流', 'Spot order flow', _T('誰在主動買賣、掛單牆在哪', 'Who is hitting the market and where the walls are')) +
      svPanel() + tkPanel() + bookCard() + '</div>';   // 籌碼結構與集中度搬到鏈上版、賣壓累積與動能品質搬到價格版（2026-11-08）
  };
  V.deriv.after = function () {
    drawBook(); liqAfter();
    mount($('#c-gex'), drawGex); mount($('#c-prem'), drawPr); mount($('#c-svd'), drawSv); mount($('#c-svdh'), drawSvH);   // 2026-11-06 指標擴充
    var gs = $('#gx-seg'); if (gs) gs.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b || b.getAttribute('data-m') === gxMode) return; gxMode = b.getAttribute('data-m'); gs.querySelectorAll('button').forEach(function (q) { q.setAttribute('aria-pressed', q === b); }); drawGex($('#c-gex')); });
    var v = D.deriv.viz || {};
    mount($('#c-vol'), function (el) { var rows = (v.vol || {}).rows || []; lineChart(el, { series: [{ name: 'DVOL', data: rows.map(function (r) { return [r[0], r[1]]; }), color: 'var(--s4)' }, { name: 'RV30', data: rows.map(function (r) { return [r[0], r[2]]; }), color: 'var(--s1)' }], yFmt: function (x) { return x.toFixed(0); }, tipFmt: function (x) { return x.toFixed(1) + '%'; }, aria: _t('波動率') }); });
    mount($('#c-ivt'), drawIvt); mount($('#c-ivts'), drawIvtS);   // 2026-11-08 隱含波動率期限結構
    mount($('#c-basis'), function (el) { var cv = (v.basis || {}).curve || []; lineChart(el, { h: 200, xType: 'num', series: [{ name: _t('年化基差'), data: cv, color: 'var(--s4)', area: true }], xticks: cv.filter(function (p, i) { return i % 2 === 0; }).map(function (p) { return [p[0], Math.round(p[0]) + 'd']; }), xTipFmt: function (x) { return Math.round(x) + _t(' 天到期'); }, yFmt: function (x) { return x.toFixed(1) + '%'; }, tipFmt: function (x) { return x.toFixed(2) + '%'; }, y0: 0, aria: _t('基差曲線') }); });
    mount($('#c-oi'), function (el) {
      var ex = ((v.options || {}).expiries || []), W = Math.max(280, el.clientWidth), Ht = 230, ML = 8, MR = 52, MT = 10, MB = 26, pw = W - ML - MR, ph = Ht - MT - MB;
      var mx = Math.max.apply(null, ex.map(function (e) { return e[2] + e[3]; })) || 1, st = niceStep(mx, 4), top = Math.ceil(mx / st) * st, bw = pw / ex.length, s = '';
      var lbEvery = Math.max(1, Math.ceil(40 / bw));   // 2026-11-04：日期標籤約 36px 寬，手機上柱子太窄時隔幾根標一次（原本每根都標、全部疊在一起）
      var Y = function (q) { return MT + (1 - q / top) * ph; };
      for (var t = 0; t <= top; t += st) s += '<line class="' + (t ? 'gl' : 'base') + '" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + Y(t).toFixed(1) + '" y2="' + Y(t).toFixed(1) + '"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (Y(t) + 3.5).toFixed(1) + '">' + fmt.k(t) + '</text>';
      ex.forEach(function (e, i) { var x = ML + i * bw + 3, w = bw - 6, yc = Y(e[2]), yp = Y(e[2] + e[3]); s += '<g class="oi" data-i="' + i + '"><rect x="' + x.toFixed(1) + '" y="' + yc.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + (MT + ph - yc).toFixed(1) + '" rx="3" fill="var(--up)"/><rect x="' + x.toFixed(1) + '" y="' + yp.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + Math.max(0, yc - yp - 2).toFixed(1) + '" rx="3" fill="var(--down)"/></g>' + (i % lbEvery === 0 || i === ex.length - 1 && i % lbEvery >= lbEvery / 2 ? '<text class="ax" x="' + (x + w / 2).toFixed(1) + '" y="' + (Ht - 8) + '" text-anchor="middle">' + fmt.md(e[0]) + '</text>' : ''); });
      el.innerHTML = svgEl(W, Ht, s, _t('各到期未平倉'));
      el.querySelectorAll('.oi').forEach(function (g) { var e = ex[+g.getAttribute('data-i')]; g.addEventListener('pointermove', function (ev) { showTip(ev.clientX, ev.clientY, '<div class="t">' + e[0] + ' · ' + e[1] + _t(' 天</div><div class="r"><i style="background:var(--up)"></i><span>買權</span><b>') + fmt.n(e[2]) + _t('</b></div><div class="r"><i style="background:var(--down)"></i><span>賣權</span><b>') + fmt.n(e[3]) + '</b></div><div class="r"><i></i><span>Max Pain</span><b>' + fmt.k(e[4]) + '</b></div>'); }); g.addEventListener('pointerleave', hideTip); });
    });
    skDraw();
    var sg = $('#sk-segs'); if (sg) sg.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; skSel = +b.getAttribute('data-i'); sg.querySelectorAll('button').forEach(function (q) { q.setAttribute('aria-pressed', q === b); }); var h = sg.closest('.panel-h') && sg.closest('.panel-h').querySelector('.src'); if (h) h.textContent = skTotals(); $('#sk-say').innerHTML = strikeSay(skRow() || {}); skDraw(); });
  };
  function skDraw() {
    var sk0 = (skObj() || {}).rows || [], el = $('#c-strike'), cc = D.price.bar.c, bk = {};
    /* 只看收盤 ±30%，依數量自動分箱到 26 列以內，避免出現捲軸 */
    sk0 = sk0.filter(function (r) { return r[0] >= cc * 0.7 && r[0] <= cc * 1.3; });
    var bs = 1000; while (sk0.length && (sk0[sk0.length - 1][0] - sk0[0][0]) / bs > 26) bs = bs === 1000 ? 2500 : bs * 2;
    sk0.forEach(function (r) { var k = Math.floor(r[0] / bs) * bs; if (!bk[k]) bk[k] = [k, 0, 0]; bk[k][1] += r[1]; bk[k][2] += r[2]; });
    var sk = Object.keys(bk).map(function (k) { return bk[k]; }).sort(function (a, b) { return a[0] - b[0]; });
    if (el) { var mx = Math.max.apply(null, sk.map(function (r) { return Math.max(r[1], r[2]); })) || 1, c = D.price.bar.c;
      el.innerHTML = '<div class="ladder dense">' + sk.slice().reverse().map(function (r) { var near = c >= r[0] && c < r[0] + bs; return '<div class="row' + (near ? ' cur' : '') + '" style="grid-template-columns:minmax(0,1fr) 64px minmax(0,1fr)"><span class="b" style="direction:rtl"><i style="width:' + (r[2] / mx * 100).toFixed(1) + '%;background:var(--down);left:auto;right:0"></i></span><span class="p" style="text-align:center">' + fmt.k(r[0]) + '</span><span class="b"><i style="width:' + (r[1] / mx * 100).toFixed(1) + '%;background:var(--up)"></i></span></div>'; }).join('') + _t('</div><div class="legend" style="margin-top:8px;justify-content:space-between"><span style="color:var(--down)"><i></i><b style="color:var(--ink-2);font-weight:400">← 賣權</b></span><span style="color:var(--up)"><b style="color:var(--ink-2);font-weight:400">買權 →</b><i></i></span></div>'); }
  };

  /* 實現市值 30 日變化（2026-10-12 使用者要求）：只作資金背景讀值，附歷次 ≤0 期間與之後的價格表現，避免被當成加倉訊號 */
  function rcPanel(rc) {
    if (rc.chg30_pct == null) return '';
    var eps = (rc.episodes || []).slice().reverse(), f = function (v) { return v == null ? _t('<span class="note">未到</span>') : '<span style="color:var(--' + (v >= 0 ? 'up' : 'down') + ')">' + fmt.pct(v, 0) + '</span>'; };
    var tb = _t('<div class="tbl-wrap"><table class="tbl"><thead><tr><th>≤0 期間</th><th class="num">天數</th><th class="num">期間價格</th><th class="num">之後 180 天</th><th class="num">之後 365 天</th></tr></thead><tbody>') + eps.map(function (e) { return '<tr><td style="white-space:nowrap">' + e.start.slice(2) + '<br>→ ' + (e.ongoing ? _t('進行中') : e.end.slice(2)) + '</td><td class="num">' + e.days + '</td><td class="num">' + fmt.k(e.px_start) + '<br>→ ' + fmt.k(e.px_end) + '</td><td class="num">' + f(e.fwd180) + '</td><td class="num">' + f(e.fwd365) + '</td></tr>'; }).join('') + '</tbody></table></div>';
    var say = _t('<p class="say">現在 <b>') + fmt.pct(rc.chg30_pct, 2) + _t('</b>（') + (rc.zero_now ? _t('≤0，資金流入停滯') : _t('>0，仍有資金流入')) + _t('，已持續 ') + rc.state_run_days + _t(' 天）；實現市值 ') + fmt.n(rc.realized_cap_usd_b / 1000, 3) + _t(' 兆美元，90 日 ') + fmt.pct(rc.chg90_pct, 2) + _t('、180 日 ') + fmt.pct(rc.chg180_pct, 2) + _t('。</p>');
    var note = _t('<div class="note" style="margin-top:10px;line-height:1.7"><p><b>這是什麼：</b>實現市值＝每顆幣以「最後一次在鏈上移動時的價格」計價後加總，可看成全體持有者的總成本。30 日變化 &gt;0，代表有幣以高於上次成本的價格換手，新資金在進場；≤0（圖中紅底）代表新資金停止流入，或換手以虧損賣出為主。</p>') +
      _t('<p><b>社群的用法：</b>Checkonchain 的「Realised Cap Liquidity Cycle」以同一數字為核心，常見說法是「熊市底部之後，30 日流動性歸零是加倉的好時機，每輪會出現 2–3 次」。</p>') +
      _t('<p><b>本站的看法：</b>上表列出 2014 年以來每一次 ≤0 的期間。2015、2019 底、2020-03、2023 的歸零之後確實大漲；但 2014-04、2018-02 到 09 月的四次、2021-06、2022-01 同樣歸零，之後半年仍跌 29%–55%。「已經離開底部」只有事後才能確認，所以這裡只作資金背景讀值：不作買賣訊號、不連動出場框架。週期版「佐證燈號」的「資金流入」就是同一數字是否 &gt;0。</p>') +
      _t('<p><b>口徑：</b>CoinMetrics 社群版「市值 ÷ MVRV」推得，與 Checkonchain、bitcoin-data 的數值可能略有差異；期間至少連續 7 天才列入；「結束後」報酬以期間最後一天收盤計。</p></div>');
    return panel('span-12', _t('資金流入：實現市值 30 日變化'), 'CoinMetrics · ' + fmt.md(rc.date) + _t(' · 2019 起 · 紅底＝≤0'), say + '<div class="chart" id="c-rcliq"></div>' + note + _t('<details style="margin-top:10px"><summary class="note" style="cursor:pointer">歷次 ≤0 期間與之後的價格表現（') + eps.length + _t(' 次）</summary>') + tb + '</details>');
  }
  /* 三地溢價（2026-11-03 使用者要求；參考的「期現差價加權 USDT 溢價率」權重不公開，改成三條分開看）：
     美國現貨＝Coinbase 溢價、亞洲＝OKX 場外 USDT/CNY 對匯率的溢價（只有快照，從 2026-11-03 起每日累積）、槓桿＝OKX 永續對現貨。只作讀值 */
  /* 2026-11-05 使用者：「Coinbase 溢價在 TradingView 已經收斂，你的圖還在底部」「運營回覆時用到溢價圖，沒什麼說服力」。
     原因是圖畫 7 日平均（還含上週的低點）；資料和 TradingView 的 CB-BN basis 同一種算法。改成：每日值＋7 日平均、上格價格、約 4 年歷史、
     過去深度折價之後的走勢（樣本照實寫），以及瀏覽器打開時直接向 Coinbase、Binance 取最新一小時（不經本站伺服器）。只作讀值 */
  var CB_DEEP = -0.15, CB_REARM = -0.05, CB_LIVE = null;
  function cbA7(r) { return ma7r(r.map(function (x) { return [x[0], x[1]]; })).map(function (x) { return x[1]; }); }
  function cbStats() {
    var cp = D.flows.cb_premium || {}, r = cp.rows || []; if (r.length < 60 || r[0].length < 3) return null;
    var a7 = cbA7(r), at = function (i, n) { var t = r[i][0] + n; for (var k = i; k < r.length; k++) if (r[k][0] >= t) return (r[k][2] / r[i][2] - 1) * 100; return null; };
    var ev = [], armed = true, cv = [];
    for (var i = 0; i < r.length; i++) { var a = a7[i]; if (a == null) continue;
      if (armed && a < CB_DEEP) { ev.push({ i: i, t: r[i][0], a: a, f30: at(i, 30) }); armed = false; } else if (!armed && a > CB_REARM) armed = true;
      if (i > 0 && a7[i - 1] != null && a7[i - 1] <= 0 && a > 0) { var mn = Infinity; for (var k = Math.max(0, i - 30); k < i; k++) if (a7[k] != null) mn = Math.min(mn, a7[k]); if (mn < -0.1) cv.push({ t: r[i][0], f30: at(i, 30) }); } }
    var all = []; for (i = 0; i < r.length; i++) { var f = at(i, 30); if (f != null) all.push(f); }
    var done = ev.filter(function (e) { return e.f30 != null; }), cdone = cv.filter(function (e) { return e.f30 != null; });
    // 最近 14 天每日最低（看是不是已經從低點收斂）
    var lo = null; for (i = Math.max(0, r.length - 14); i < r.length; i++) if (!lo || r[i][1] < lo[1]) lo = r[i];
    return { a7: a7, ev: ev, done: done, up: done.filter(function (e) { return e.f30 > 0; }).length, cv: cdone, cup: cdone.filter(function (e) { return e.f30 > 0; }).length,
      base: all.length ? all.filter(function (x) { return x > 0; }).length / all.length * 100 : null, lo14: lo, since: r[0][0] };
  }
  function cbLive(cb) {   // 瀏覽器直接取 Coinbase 與 Binance 的 1 小時 K 線（兩邊都允許跨網域讀取）；失敗就不顯示，不影響其他內容
    if (CB_LIVE !== null) { if (CB_LIVE) cb(); return; } CB_LIVE = false;
    var j = function (u) { return fetch(u).then(function (x) { if (!x.ok) throw 0; return x.json(); }); };
    Promise.all([j('https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600'), j('https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=48')]).then(function (a) {
      var c = {}; a[0].forEach(function (k) { c[k[0]] = k[4]; });
      var m = a[1].map(function (k) { var t = Math.round(k[0] / 1000); return c[t] ? [t, (c[t] / +k[4] - 1) * 100] : null; }).filter(Boolean);
      if (m.length < 6) return;
      var last = m[m.length - 1], d24 = m.slice(-24);
      CB_LIVE = { t: last[0], v: last[1], a24: d24.reduce(function (s_, x) { return s_ + x[1]; }, 0) / d24.length, n: d24.length }; cb();
    }).catch(function () {});
  }
  function cbLiveTxt() {
    if (!CB_LIVE) return '';
    var d = new Date(CB_LIVE.t * 1000), hm = ('0' + d.getUTCHours()).slice(-2) + ':00', pc = function (v) { return (v > 0 ? '+' : '') + fmt.n(v, 3) + '%'; };
    return _T('即時（' + (d.getUTCMonth() + 1) + '/' + d.getUTCDate() + ' ' + hm + ' UTC 那一小時）' + pc(CB_LIVE.v) + '，近 24 小時平均 ' + pc(CB_LIVE.a24) + '；打開網頁時直接向 Coinbase、Binance 取得',
      'Live (hour of ' + (d.getUTCMonth() + 1) + '/' + d.getUTCDate() + ' ' + hm + ' UTC) ' + pc(CB_LIVE.v) + ', 24-hour average ' + pc(CB_LIVE.a24) + '; fetched from Coinbase and Binance when the page opens');
  }
  function premSay() {
    var cp = D.flows.cb_premium || {}, p3 = D.flows.premium3 || {}, u = p3.usdt, pp = p3.perp, it = [], sgn = [], nm = [], fw = (D.deriv.funding_multi || {}).weighted_now;
    var pc = function (v, d) { return (v > 0 ? '+' : '') + fmt.n(v, d) + '%'; };
    if (cp.avg7 != null) { sgn.push(cp.avg7 > 0.02 ? 1 : cp.avg7 < -0.02 ? -1 : 0); nm.push(_T('美國現貨', 'US spot'));
      var cs = cbStats(), lo14 = cs && cs.lo14, conv = lo14 && cp.pct != null && cp.pct - lo14[1] >= 0.08 && lo14[0] < dnOf(cp.date);
      it.push([_T('美國現貨（Coinbase）', 'US spot (Coinbase)'), _T('每日 ', 'Daily ') + pc(cp.pct, 3), _T('每日 ' + pc(cp.pct, 3) + '（' + fmt.md(cp.date) + '），7 日平均 ' + pc(cp.avg7, 3) + '、30 日平均 ' + pc(cp.avg30, 3) + '。' + (conv ? '每日值已從 ' + fmt.date(lo14[0]).slice(5) + ' 的 ' + pc(lo14[1], 3) + ' 收斂回來；7 日平均還含前幾天的低點，所以看起來還在底部。' : '') + (cp.avg7 > 0.02 ? '美國買盤比海外積極。' : cp.avg7 < -0.02 ? '美國現貨比海外便宜，美國買盤（含 ETF 相關）偏弱。' : '和海外差不多。'),
        'Daily ' + pc(cp.pct, 3) + ' (' + fmt.md(cp.date) + '); 7-day average ' + pc(cp.avg7, 3) + ', 30-day ' + pc(cp.avg30, 3) + '. ' + (conv ? 'The daily value has recovered from ' + pc(lo14[1], 3) + ' on ' + fmt.date(lo14[0]).slice(5) + '; the 7-day average still holds the recent lows, so it looks stuck at the bottom. ' : '') + (cp.avg7 > 0.02 ? 'US buyers are more eager than offshore.' : cp.avg7 < -0.02 ? 'US spot trades below offshore; US demand (incl. ETF-related) is soft.' : 'In line with offshore.')), 'neu']);
      if (cs && cs.done.length) { var rr = cs.done.map(function (e) { return fmt.date(e.t).slice(0, 7) + ' ' + fmt.pct(e.f30, 0); }).join(_T('、', ', ')), cur = cs.ev.filter(function (e) { return e.f30 == null; })[0];
        it.push([_T('過去的深度折價', 'Past deep discounts'), cs.up + ' / ' + cs.done.length,
          _T(fmt.date(cs.since).slice(0, 4) + ' 年以來 7 日平均跌破 ' + CB_DEEP + '% 共 ' + cs.ev.length + ' 次' + (cur ? '（最近一次是 ' + fmt.md(fmt.date(cur.t).replace(/\//g, '-')) + '，還沒滿 30 天）' : '') + '；之前 ' + cs.done.length + ' 次，30 天後價格 ' + cs.up + ' 次較高（' + rr + '），都在當時的階段低點附近。樣本只有 ' + cs.done.length + ' 次。另外，7 日平均「收斂回 0 以上」本身沒有額外資訊：過去 ' + cs.cv.length + ' 次 30 天後 ' + cs.cup + ' 次較高，和隨便一天（' + fmt.n(cs.base, 0) + '%）差不多。',
            'Since ' + fmt.date(cs.since).slice(0, 4) + ' the 7-day average has fallen below ' + CB_DEEP + '% ' + cs.ev.length + ' times' + (cur ? ' (latest ' + fmt.date(cur.t).slice(5) + ', under 30 days ago)' : '') + '; after the earlier ' + cs.done.length + ', price was higher 30 days later ' + cs.up + ' times (' + rr + '), each near a local low at the time. Only ' + cs.done.length + ' cases. Separately, the 7-day average turning back above 0 carries no extra information: of ' + cs.cv.length + ' cases, ' + cs.cup + ' were higher 30 days later, about the same as any day (' + fmt.n(cs.base, 0) + '%).'), 'neu']); }
    }
    if (u) { sgn.push(u.pct > 0.3 ? 1 : u.pct < -0.3 ? -1 : 0); nm.push(_T('亞洲 USDT', 'Asian USDT')); var h = p3.usdt_hist || [], h0 = h.length ? fmt.date(h[0][0]) : '';
      it.push([_T('亞洲（USDT 場外）', 'Asia (USDT OTC)'), pc(u.pct, 2), _T('OKX 場外 USDT 約 ' + fmt.n(u.mid, 3) + ' 人民幣，匯率 ' + fmt.n(u.fx, 3) + '。' + (u.pct > 0.3 ? '溢價：有人搶著用人民幣換 USDT 進場。' : u.pct < -0.3 ? '折價：換回人民幣的人比較多，亞洲資金偏離場。' : '接近匯率，亞洲買賣大致平衡。') + (h.length < 30 ? '這條只有每日快照（這次 ' + u.ts.slice(5, 10).replace('-', '/') + ' ' + u.ts.slice(11, 16) + ' UTC），紀錄從 ' + h0 + ' 開始累積（目前 ' + h.length + ' 天）。' : ''),
        'OKX OTC USDT at about ' + fmt.n(u.mid, 3) + ' CNY vs a ' + fmt.n(u.fx, 3) + ' FX rate. ' + (u.pct > 0.3 ? 'Premium: buyers are swapping CNY into USDT to enter.' : u.pct < -0.3 ? 'Discount: more people are cashing USDT back into CNY; Asian money is leaning out.' : 'Near the FX rate; Asian flows roughly balanced.') + (h.length < 30 ? ' Daily snapshot only (this one ' + u.ts.slice(0, 16).replace('T', ' ') + ' UTC); the record starts ' + h0 + ' (' + h.length + ' day(s) so far).' : '')), 'neu']); }
    if (pp) { var pk = pp.avg7_pct_own, hi = pk != null && pk >= 70, lo = pk != null && pk <= 30; if (pk != null) { sgn.push(hi ? 1 : lo ? -1 : 0); nm.push(_T('槓桿', 'leverage')); }   // 2026-11-04：百分位缺時不當成「比平常便宜」   // 永續平常就略低於現貨，所以和自己的歷史比，不看正負號
      it.push([_T('槓桿（永續對現貨）', 'Leverage (perp vs spot)'), pc(pp.avg7, 3), _T('OKX 永續對現貨 7 日平均；平常（30 日平均）是 ' + pc(pp.avg30, 3) + '，現在在近 ' + pp.n + ' 天第 ' + fmt.n(pp.avg7_pct_own, 0) + ' 百分位' + (fw != null ? '；加權資金費率年化 ' + fmt.n(fw, 1) + '%' : '') + '。' + (hi ? '比平常貴：多單願意付溢價追價。' : lo ? '比平常便宜：槓桿偏空或在避險。' : '和平常差不多，槓桿沒有明顯偏向。'),
        'OKX perp vs spot, 7-day average; usually (30-day avg) ' + pc(pp.avg30, 3) + ', now at the ' + fmt.n(pp.avg7_pct_own, 0) + 'th percentile of ' + pp.n + ' days' + (fw != null ? '; weighted funding ' + fmt.n(fw, 1) + '% a year' : '') + '. ' + (hi ? 'Richer than usual: longs pay up to chase.' : lo ? 'Cheaper than usual: leverage leans short or is hedging.' : 'About usual; no clear leverage tilt.')), 'neu']); }
    if (sgn.length >= 2) { var P_ = nm.filter(function (n, i) { return sgn[i] > 0; }), N_ = nm.filter(function (n, i) { return sgn[i] < 0; }), Z_ = nm.filter(function (n, i) { return !sgn[i]; }), j_ = function (a) { return a.join(_T('、', ', ')); };
      var spotOut = N_.length && N_.indexOf(_T('槓桿', 'leverage')) < 0 && P_.indexOf(_T('槓桿', 'leverage')) >= 0;
      it.push([_T('合起來', 'Together'), P_.length + ' / ' + N_.length, _T((P_.length ? '在推：' + j_(P_) + '。' : '') + (N_.length ? '缺席：' + j_(N_) + '。' : '') + (Z_.length ? '持平：' + j_(Z_) + '。' : '') + (spotOut ? '現貨買盤缺席、只有槓桿在撐，這種行情比較脆弱。' : N_.length > P_.length ? '買盤大多缺席。' : P_.length > N_.length ? '多數地方有買盤在推。' : ''),
        (P_.length ? 'Pushing: ' + j_(P_) + '. ' : '') + (N_.length ? 'Absent: ' + j_(N_) + '. ' : '') + (Z_.length ? 'Flat: ' + j_(Z_) + '. ' : '') + (spotOut ? 'Spot buyers are absent and only leverage is holding up; that makes the market fragile.' : N_.length > P_.length ? 'Buyers are mostly absent.' : P_.length > N_.length ? 'Buyers are pushing in most places.' : '')), N_.length > P_.length || spotOut ? 'warn' : 'neu']); }
    return it;
  }
  function premPanel() {
    var p3 = D.flows.premium3; if (!p3 || (!p3.usdt && !p3.perp)) return '';
    return panel('span-12', _T('三地溢價：買盤從哪裡來', 'Three premiums: where the buying comes from'), _T('Coinbase · OKX 場外 · OKX 永續', 'Coinbase · OKX OTC · OKX perps'),
      interpHtml(premSay()) + '<div class="panel-h" style="margin-top:14px"><h3>' + _T('美國現貨：Coinbase 溢價（每日與 7 日平均）', 'US spot: Coinbase premium (daily and 7-day average)') + '</h3></div><p class="note" id="cb-live"></p>' +
      legend([[_T('BTC 價格（上格）', 'BTC price (top)'), 'var(--ink-2)'], [_T('每日 ≥ 0', 'Daily ≥ 0'), 'var(--up)', 'box'], [_T('每日 < 0', 'Daily < 0'), 'var(--down)', 'box'], [_T('7 日平均', '7-day average'), 'var(--s4)'], [_T('深度折價線 ' + CB_DEEP + '%', 'Deep-discount line ' + CB_DEEP + '%'), 'var(--down)', 'dash'], [_T('即時（最新一小時）', 'Live (latest hour)'), 'var(--s4)', 'dot']]) + '<div class="chart" id="c-pr-us"></div>' +
      '<div class="evcharts">' + [['c-pr-asia', _T('亞洲：USDT 場外溢價（每日快照）', 'Asia: USDT OTC premium (daily snapshot)')], ['c-pr-perp', _T('槓桿：永續對現貨（7 日平均）', 'Leverage: perp vs spot (7-day avg)')]].map(function (c) { return '<div class="evc"><div class="panel-h"><h3>' + c[1] + '</h3></div><div class="chart" id="' + c[0] + '"></div></div>'; }).join('') + '</div>' +
      '<p class="note">' + _T('三條都是「和基準差多少 %」：Coinbase ÷ Binance、場外 USDT ÷ 美元兌人民幣匯率、永續 ÷ 現貨，大於 0＝那一邊的買方比較積極；永續平常就略低於現貨，所以槓桿這條和自己的歷史比。不合成一個數字（權重沒有客觀答案），分開看誰在推、誰在缺席。場外報價只有當下快照，歷史從上線那天開始累積。',
        'All three are “% away from a benchmark”: Coinbase ÷ Binance, OTC USDT ÷ the USD/CNY rate, and perp ÷ spot; above 0 means buyers on that side are keener; perps usually sit slightly below spot, so the leverage line is judged against its own history. They are not merged into one number (no objective weights); read them side by side to see who pushes and who is absent. The OTC quote is a snapshot, so its history builds from launch.') + '</p>');
  }
  /* [[日, 值]] 的 7 日平均（前 6 天為 null）；三地溢價圖與「現在」讀值共用（2026-11-04） */
  function ma7r(r) { return r.map(function (x, i) { if (i < 6) return [x[0], null]; var s = 0; for (var k = i - 6; k <= i; k++) s += r[k][1]; return [x[0], s / 7]; }); }
  function drawCbPrem(el) {
    var cp = D.flows.cb_premium || {}, R_ = (cp.rows || []).filter(function (r) { return r[2] != null; }); if (R_.length < 60 || !el) return;
    var cs = cbStats(), a7 = {}; R_.forEach(function (r, i) { a7[r[0]] = cs.a7[i]; });
    var vs = R_.map(function (r) { return r[1]; }).slice().sort(function (a, b) { return a - b; }), q = function (p) { return vs[Math.floor((vs.length - 1) * p)]; };
    var lo = Math.min(-0.3, q(0.005) * 1.1), hi = Math.max(0.2, q(0.995) * 1.1), pf = function (v) { return (v > 0 ? '+' : '') + v.toFixed(2) + '%'; };
    twoPane(el, { rows: R_, pi: 2, hp: [110, 150], hs: [150, 200], label: _T('Coinbase 溢價（%）', 'Coinbase premium (%)'), aria: _T('BTC 價格與 Coinbase 溢價', 'BTC price and Coinbase premium'),
      scale: function (C) { return function (v) { return C.ys0 + (1 - (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * C.hs; }; },
      body: function (C) {
        var s = '', z = C.Ys(0), yd = C.Ys(CB_DEEP), st = hi - lo > 0.6 ? 0.2 : 0.1;
        for (var g = Math.ceil(lo / st) * st; g <= hi + 1e-9; g += st) { if (Math.abs(g) < 1e-9) continue; var gy = C.Ys(g); s += C.gl(gy, Math.abs(gy - yd) < 11 ? null : pf(+g.toFixed(2))); }
        s += C.gl(z, '0', 'base');
        s += '<rect x="' + C.ML + '" y="' + yd.toFixed(1) + '" width="' + C.pw + '" height="' + (C.yb - yd).toFixed(1) + '" fill="var(--down-dim)"/><line x1="' + C.ML + '" x2="' + (C.ML + C.pw) + '" y1="' + yd.toFixed(1) + '" y2="' + yd.toFixed(1) + '" stroke="var(--down)" stroke-dasharray="3 4" stroke-width="1"/>' + C.tx(C.ML + C.pw + 8, yd + 3.5, CB_DEEP + '%').replace('class="ax"', 'class="ax" fill="var(--down-ink)"');
        var bw = Math.max(0.8, C.pw / C.rows.length * 0.7);
        C.rows.forEach(function (r) { var y = C.Ys(r[1]); s += '<rect x="' + (C.X(r[0]) - bw / 2).toFixed(1) + '" y="' + Math.min(y, z).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(0.5, Math.abs(y - z)).toFixed(1) + '" fill="var(--' + (r[1] >= 0 ? 'up' : 'down') + ')" opacity=".42"/>'; });
        var pts = C.rows.filter(function (r) { return a7[r[0]] != null; });
        s += '<path class="ln" d="M' + pts.map(function (r) { return C.X(r[0]).toFixed(1) + ',' + C.Ys(a7[r[0]]).toFixed(1); }).join('L') + '" stroke="var(--s4)" stroke-width="1.8"/>';
        return s;
      },
      over: function (C) {
        var s = '', x0 = C.rows[0][0], lx = -Infinity;
        cs.ev.forEach(function (e) { if (e.t < x0) return; var xx = C.X(e.t), yy = C.Ys(e.a); s += '<circle cx="' + xx.toFixed(1) + '" cy="' + yy.toFixed(1) + '" r="4.5" fill="var(--deck)" stroke="var(--down)" stroke-width="2"/>';
          if (e.f30 != null && xx - lx > (C.sm ? 30 : 44)) { var tx_ = Math.max(C.ML + (C.sm ? 14 : 26), Math.min(C.ML + C.pw - 26, xx)); s += '<text class="ax hi" x="' + tx_.toFixed(1) + '" y="' + (yy + 16).toFixed(1) + '" text-anchor="middle">' + (C.sm ? '' : _T('30 天 ', '30d ')) + fmt.pct(e.f30, 0) + '</text>'; lx = xx; } });
        var lr = C.rows[C.rows.length - 1], la = a7[lr[0]];
        if (la != null) s += '<circle cx="' + C.X(lr[0]).toFixed(1) + '" cy="' + C.Ys(la).toFixed(1) + '" r="4" fill="var(--s4)" stroke="var(--deck)" stroke-width="2"/>';
        if (CB_LIVE) { var lx2 = C.ML + C.pw, ly = C.Ys(CB_LIVE.v); s += '<circle cx="' + lx2.toFixed(1) + '" cy="' + ly.toFixed(1) + '" r="5" fill="var(--deck)" stroke="var(--s4)" stroke-width="2.5"/><text class="ax hi" x="' + (lx2 - 8).toFixed(1) + '" y="' + (ly - 9).toFixed(1) + '" text-anchor="end">' + _T('即時 ', 'Live ') + pf(CB_LIVE.v) + '</text>'; }
        return s;
      },
      tip: function (p, C) { var a = a7[p[0]]; return { dots: '<circle cx="' + C.X(p[0]).toFixed(1) + '" cy="' + C.Ys(p[1]).toFixed(1) + '" r="3.5" fill="var(--' + (p[1] >= 0 ? 'up' : 'down') + ')" stroke="var(--deck)" stroke-width="1.5"/>',
        rows: tipRow1('var(--' + (p[1] >= 0 ? 'up' : 'down') + ')', _T('每日', 'Daily'), (p[1] > 0 ? '+' : '') + fmt.n(p[1], 3) + '%') + (a != null ? tipRow1('var(--s4)', _T('7 日平均', '7-day avg'), (a > 0 ? '+' : '') + fmt.n(a, 3) + '%') : '') }; } });
  }
  function drawPrem() {
    var cp = D.flows.cb_premium || {}, p3 = D.flows.premium3 || {}, ma7 = ma7r;
    var X1 = dnOf(D.meta.bar_date), X0 = X1 - 300, pf = function (d) { return function (v) { return (v > 0 ? '+' : '') + v.toFixed(d) + '%'; }; };
    var one = function (id, data, d, color, title) { mount($('#' + id), function (el) { var pts = (data || []).filter(function (p) { return p[1] != null && p[0] >= X0; });
      // 2026-11-04：歷史還很短（場外 USDT 從 11/02 才開始）時，x 軸從第一點往前留同樣長度，不要擠在 300 天軸的最右邊 1px
      var x0 = pts.length && X1 - pts[0][0] < 150 ? pts[0][0] - Math.max(14, X1 - pts[0][0]) : X0;
      if (pts.length < 2) {   // 2026-11-03：只有一天時畫一個點和零軸（場外 USDT 溢價從 11/02 才開始累積），不留空白
        if (!pts.length) { el.innerHTML = '<p class="note">' + _T('本日未取得資料。', 'No data today.') + '</p>'; return; }
        var W = Math.max(280, el.clientWidth), Ht = 150, ML = 8, MR = 58, MT = 14, MB = 24, pw = W - ML - MR, ph = Ht - MT - MB, v0 = pts[0][1], lo = Math.min(-1.5, v0 - 0.5), hi = Math.max(1.5, v0 + 0.5);
        var Y = function (v) { return MT + (1 - (v - lo) / (hi - lo)) * ph; }, X = function (t) { return ML + (t - x0) / (X1 - x0) * pw; }, sv = '';
        [lo, 0, hi].forEach(function (g) { var gy = Y(g); sv += '<line class="' + (g ? 'gl' : 'base') + '" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + gy.toFixed(1) + '" y2="' + gy.toFixed(1) + '"' + (g ? '' : ' stroke-dasharray="4 4"') + '/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (gy + 3.5).toFixed(1) + '">' + pf(1)(+g.toFixed(1)) + '</text>'; });
        var px_ = X(pts[0][0]), py_ = Y(v0);
        sv += '<circle cx="' + px_.toFixed(1) + '" cy="' + py_.toFixed(1) + '" r="4.5" fill="' + color + '" stroke="var(--deck)" stroke-width="2"/><text class="ax hi" x="' + (px_ - 8).toFixed(1) + '" y="' + (py_ - 9).toFixed(1) + '" text-anchor="end">' + fmt.md(fmt.date(pts[0][0]).replace(/\//g, '-')) + ' ' + pf(d)(v0) + '</text>' +
          '<text class="ax" x="' + (ML + pw / 2).toFixed(1) + '" y="' + (Ht - 6) + '" text-anchor="middle">' + _T('紀錄從這天開始，每天累積一點，兩天後連成線', 'Record starts here; one point a day') + '</text>';
        el.innerHTML = svgEl(W, Ht, sv, title); return;
      }
      lineChart(el, { h: 150, x0: x0, x1: X1, series: [{ name: _T('溢價', 'Premium'), data: pts, color: color }], refs: [{ y: 0, color: 'var(--ink-3)' }], yFmt: pf(d > 2 ? 2 : d), tipFmt: pf(d), aria: title }); }); };
    mount($('#c-pr-us'), drawCbPrem); cbLive(function () { var e = $('#cb-live'); if (e) e.textContent = cbLiveTxt(); var c = $('#c-pr-us'); if (c && c._draw) c._draw(c); });
    one('c-pr-asia', p3.usdt_hist || [], 2, 'var(--s4)', _T('場外 USDT 溢價', 'OTC USDT premium'));
    one('c-pr-perp', ma7((p3.perp || {}).rows || []), 3, 'var(--s4)', _T('永續對現貨（7 日平均）', 'Perp vs spot (7-day avg)'));
  }

  V.flows = function () {
    var fr = D.flows.fred || {}, etf = D.flows.etf || [], full = etf.filter(function (r) { return !r.partial; });
    var last = full[full.length - 1] || {}, s7 = full.slice(-7).reduce(function (a, r) { return a + r.musd; }, 0), p7 = full.slice(-14, -7).reduce(function (a, r) { return a + r.musd; }, 0);
    var nq = fr.NASDAQCOM || {}, dx = fr.DTWEXBGS || {}, tn = fr.DGS10 || {}, rr = D.flows.dfii10 || {}, rc = D.flows.rc_liq || {};
    return readBar('flows') + '<div class="kpis">' + kpi(_t('最近完整日 ETF'), (last.musd >= 0 ? '+' : '') + fmt.n(last.musd, 1) + 'M', fmt.md(last.d) + _t(' · 美元')) + kpi(_t('近 7 個完整日'), (s7 >= 0 ? '+' : '') + fmt.n(s7, 0) + 'M', _t('前 7 日 ') + (p7 >= 0 ? '+' : '') + fmt.n(p7, 0) + 'M') + kpi(_t('BTC–那斯達克 30 日相關'), fmt.n(nq.corr30, 2), fmt.md(nq.last_date) + _t(' · 高於 0.5 代表同漲同跌'), (nq.corr30 + 1) * 50) + kpi(_t('BTC–美元 30 日相關'), fmt.n(dx.corr30, 2), _t('FRED 廣義美元指數'), (dx.corr30 + 1) * 50) + kpi(_t('10 年期實質利率'), fmt.n(rr.value, 2) + '%', _t('20 日 ') + (rr.chg_20obs_bp >= 0 ? '+' : '') + rr.chg_20obs_bp + _t('bp · 名目 ') + fmt.n(tn.last, 2) + '%') + (D.flows.stables ? kpi(_T('穩定幣供給', 'Stablecoin supply'), '$' + fmt.n(D.flows.stables.usd_b, 0) + 'B', _T('30 日 ', '30-day ') + fmt.pct(D.flows.stables.chg30_pct, 2)) : '') + (D.flows.cb_premium ? kpi(_T('Coinbase 溢價', 'Coinbase premium'), fmt.pct(D.flows.cb_premium.avg7, 3), _T('7 日平均 · 30 日 ', '7-day avg · 30-day ') + fmt.pct(D.flows.cb_premium.avg30, 3)) : '') + (rc.chg30_pct != null ? kpi(_t('實現市值 30 日'), fmt.pct(rc.chg30_pct, 2), (rc.zero_now ? _t('≤0 已 ') : _t('>0 已 ')) + rc.state_run_days + _t(' 天 · 90 日 ') + fmt.pct(rc.chg90_pct, 2)) : '') + '</div><div class="grid">' + interpPanel(flInterp(last, s7, p7).concat(flInterp2(s7))) +
      grpH('fl-etf', 'ETF 與機構', 'ETFs and institutions', _T('機構的錢是進還是出、平均成本在哪', 'Is institutional money coming in or going out, and at what average cost')) +   // 2026-11-08 內容重組：資金版分四組
      panel('span-12', _t('現貨 ETF 每日淨流量'), _t('The Block（與 Farside 同口徑）· 百萬美元 · 淡色＝暫定或尚未完整'), '<div class="chart" id="c-etf"></div>') + etfcPanel() +
      grpH('fl-buy', '買盤從哪裡來', 'Where the buying comes from', _T('美國、亞洲、韓國哪邊在買，幣往交易所進還是出', 'Which region is buying, and whether coins are moving onto or off exchanges')) +
      premPanel() + kpPanel() + exfPanel() +
      grpH('fl-dmd', '鏈上需求', 'On-chain demand', _T('新的需求接不接得住供給', 'Is new demand absorbing supply')) +   // 從鏈上版搬來
      adPanel() + dmdPanel() + cfPanel() + grPanel() +
      grpH('fl-liq', '流動性與宏觀', 'Liquidity and macro', _T('場外的錢、美股和利率怎麼走', 'Where outside money, stocks and rates are heading')) +
      flowCharts() + rcPanel(rc) + stkPanel() +
      grpH('fl-sent', '情緒與關注', 'Sentiment and attention', _T('整體市場、散戶和機構現在是什麼態度', 'How the market as a whole, retail and institutions feel right now')) +   // 2026-11-09 使用者要求（市場情緒）
      fngPanel() + wikiPanel() + cotPanel() + '</div>';
  };
  V.flows.after = function () {
    safe(drawStk);
    drawFlowCharts(); drawPrem();
    mount($('#c-etfcost'), drawEtfc); mount($('#c-exflow'), drawExf); mount($('#c-kp'), drawKp);   // 2026-11-06 指標擴充
    mount($('#c-fng'), drawFng); mount($('#c-wiki'), drawWiki); mount($('#c-cot'), drawCot);   // 2026-11-09 市場情緒
    mount($('#c-ad'), drawAd); mount($('#c-dmd'), drawDmd); mount($('#c-capflow'), drawCapflow); mount($('#c-grad'), drawGr);   // 2026-11-08 鏈上需求四張從鏈上版搬來
    var etf = D.flows.etf || [];
    var rc = D.flows.rc_liq || {};
    mount($('#c-rcliq'), function (el) { var r = rc.rows || [], x0 = r.length ? r[0][0] : 0; lineChart(el, { h: 220, series: [{ name: _t('30 日變化'), data: r, color: 'var(--s4)' }], vbands: (rc.episodes || []).filter(function (e) { return dnOf(e.end) >= x0; }).map(function (e) { return { x0: Math.max(x0, dnOf(e.start)), x1: dnOf(e.end) + 1, color: 'var(--down-dim)' }; }), refs: [{ y: 0, color: 'var(--ink-3)', label: _t('0＝流入停滯'), below: true }], yFmt: function (x) { return x + '%'; }, tipFmt: function (x) { return fmt.pct(x, 2); }, aria: _t('實現市值 30 日變化') }); });
    mount($('#c-etf'), function (el) { barChart(el, { h: 260, data: etf.map(function (r) { return [fmt.md(r.d), r.musd, '<div class="t">' + r.d + (r.partial ? (r.src ? _t('（暫定）') : _t('（部分回報）')) : '') + '</div><div class="r"><i style="background:' + (r.musd >= 0 ? 'var(--up)' : 'var(--down)') + _t('"></i><span>淨流量</span><b>') + (r.musd >= 0 ? '+' : '') + fmt.n(r.musd, 1) + 'M</b></div>' + (r.src ? '<div class="t" style="font-weight:400;max-width:240px;white-space:normal">' + esc(r.src) + '</div>' : ''), r.partial]; }), yFmt: function (v) { return v + 'M'; }, aria: _t('ETF 淨流量') }); });
  };

  /* 長短期持有者籌碼（2026-10-27 使用者要求，「跌破 $80K 的潛在拋壓」的拆法）：bitcoin-data 的 URPD 依持有時間拆成
     LTH／STH，推算（pipeline/cohort_urpd.py：URPD × 幣齡分布 × 每日價格區間），不是實體調整，只作讀值。
     三種看法：現在（左 STH、右 LTH）、STH 和約 30 天前比、LTH 和約 30 天前比 */
  var cohMode = 'now';
  function cohLo() { var co = D.chips.cohort; return Math.floor(Math.min(co.window.lo, co.price * 0.7) / co.width) * co.width; }
  function cohRange(lo, hi) { return function (r) { return r[0] + D.chips.cohort.width > lo && r[0] < hi; }; }
  function cohTop(rows, k, n) { return rows.slice().sort(function (a, b) { return b[k] - a[k]; }).slice(0, n || 1); }
  function cohB(r) { return fmt.k(r[0]) + '–' + fmt.k(r[0] + D.chips.cohort.width); }
  function cohCoins(x) { return coins(x, Math.abs(x) < 1e5 ? 1 : 0); }
  function cohValSrc() { return ((D.onchain.metrics || {})['sth-realized-price'] || {}).source || 'bitcoin-data'; }   // 2026-11-04：短期持有者成本改用 Bitview
  function cohCmpExact() { var co = D.chips.cohort; return !!(co && co.cmp && co.cmp.src === 'bitview'); }   // 2026-11-04：30 天前也是實際值
  function cohExact() { var co = D.chips.cohort; return co.src === 'checkonchain'; }   // 2026-10-28：「現在」用 CheckOnChain 依實際幣齡算的分布；變化仍是推算
  function cohSrc() { var co = D.chips.cohort; return cohExact() ? _T('CheckOnChain 實際幣齡，' + fmt.md(co.now_date), 'CheckOnChain actual coin age, ' + fmt.md(co.now_date)) : _T('推算', 'estimated'); }
  function cohSay() {
    var co = D.chips.cohort, c = co.price, w = co.width, it = [], T = co.tot;
    var big = cohTop(co.rows, 1)[0], inB = c >= big[0] && c < big[0] + w;
    it.push([_T('短期持有者', 'Short-term holders'), cohCoins(T.sth), _T('平均成本 ' + fmt.usd(T.sth_cost) + '（' + cohSrc() + '），收盤比它 ' + fmt.pct((c / T.sth_cost - 1) * 100, 1) + '。最厚的一格在 ' + cohB(big) + '（' + cohCoins(big[1]) + '）' +
      (inB ? '，就是現價這一格：這批買家在成本附近，往下就轉虧，最容易出現停損賣壓。' : big[0] > c ? '，在現價上方：這批買家已經帳面虧損，價格回到那裡時容易遇到解套賣壓。' : '，在現價下方：跌回那裡之前大多數短期持有者還在獲利，是第一道承接。'),
      'Average cost ' + fmt.usd(T.sth_cost) + ' (' + cohSrc() + '); the close is ' + fmt.pct((c / T.sth_cost - 1) * 100, 1) + ' from it. The thickest bucket is ' + cohB(big) + ' (' + cohCoins(big[1]) + ')' +
      (inB ? ', right at the current price: these buyers are at cost and turn to a loss on any drop, the most likely source of stop-loss selling.' : big[0] > c ? ', above the price: these buyers are underwater and may sell to break even when price returns there.' : ', below the price: most short-term holders stay in profit until price falls back there, the first layer of support.')),
      inB || big[0] > c ? 'warn' : 'pos']);
    var L = co.loss || [];
    if (L.length > 2) {
      var l0 = L[0], l2 = L[2], p = function (x) { return fmt.n(x / T.sth * 100, 0) + '%'; }, inc = 0, at = null;
      for (var i = 1; i < L.length; i++) { var d = L[i][1] - L[i - 1][1]; if (d > inc) { inc = d; at = L[i][0]; } }
      it.push([_T('跌到哪裡誰套牢', 'Who is underwater where'), p(l0[1]), _T('成本在 ' + fmt.k(l0[0]) + ' 以上的短期持有者有 ' + cohCoins(l0[1]) + '（' + p(l0[1]) + '），價格在這之下就是帳面虧損；跌到 ' + fmt.k(l2[0]) + ' 增加到 ' + cohCoins(l2[1]) + '（' + p(l2[1]) + '）。' + (at != null ? '往下 25% 內，新增虧損最多的一層在 ' + fmt.k(at) + '–' + fmt.k(at + w) + '（' + cohCoins(inc) + '）。' : '') + '虧損不等於會賣，要搭配 STH-SOPR 與實現虧損看。',
        'Short-term holders with a cost at or above ' + fmt.k(l0[0]) + ': ' + cohCoins(l0[1]) + ' (' + p(l0[1]) + '), underwater below that price; at ' + fmt.k(l2[0]) + ' this rises to ' + cohCoins(l2[1]) + ' (' + p(l2[1]) + ').' + (at != null ? ' Within 25% below, the layer that adds the most is ' + fmt.k(at) + '–' + fmt.k(at + w) + ' (' + cohCoins(inc) + ').' : '') + ' Underwater does not mean selling; read it with STH-SOPR and realized loss.'),
        l0[1] / T.sth >= 0.5 ? 'warn' : 'neu']);
    }
    var f = co.flow;
    if (f) {
      var fr = f.rows, sp = cohTop(fr, 1, 2), nw = cohTop(fr, 3, 2), rng = function (a) { var lo = Math.min(a[0][0], a[1][0]), hi = Math.max(a[0][0], a[1][0]) + w; return fmt.k(lo) + '–' + fmt.k(hi); };
      it.push([_T('近 ' + f.days + ' 天誰在賣', 'Who sold in the last ' + f.days + ' days'), cohCoins(f.sth_spent + f.lth_spent), _T('推算：' + fmt.md(f.start) + ' 的短期持有者動了 ' + cohCoins(f.sth_spent) + '（當時共 ' + cohCoins(f.sth0) + '，主要成本在 ' + rng(sp) + '）；長期持有者動了 ' + cohCoins(f.lth_spent) + '（' + fmt.n(f.lth_spent / f.lth0 * 100, 1) + '%）。之後買進、到現在還沒動的有 ' + cohCoins(f.new) + '，集中在 ' + rng(nw) + '。',
        'Estimated: short-term holders as of ' + fmt.md(f.start) + ' moved ' + cohCoins(f.sth_spent) + ' (out of ' + cohCoins(f.sth0) + ', mostly with a cost of ' + rng(sp) + '); long-term holders moved ' + cohCoins(f.lth_spent) + ' (' + fmt.n(f.lth_spent / f.lth0 * 100, 1) + '%). Coins bought since and still unmoved: ' + cohCoins(f.new) + ', concentrated at ' + rng(nw) + '.'), 'neu']);
      var mf = f.model_free_above;
      if (mf && mf.before) { var ch = (mf.after / mf.before - 1) * 100, tf = 0; (co.transfers || []).forEach(function (m) { if (m.date > f.start) m.src.forEach(function (x) { if (x[0] >= mf.lo) tf += x[1]; }); });
        it.push([_T(fmt.k(mf.lo) + ' 以上的套牢盤', 'Trapped supply above ' + fmt.k(mf.lo)), fmt.pct(ch, 1), _T('這一段全部是長期持有者，而且價格 ' + f.days + ' 天內沒碰過，變化就是賣出、不靠模型：從 ' + cohCoins(mf.before) + ' 到 ' + cohCoins(mf.after) + '。' + (ch < -5 ? '高位套牢的長期持有者還在陸續出清，上方的潛在解套賣壓在變少。' : '高位套牢盤沒什麼動，價格回到那裡時仍可能遇到解套賣壓。') + (tf ? '其中約 ' + cohCoins(tf) + '是疑似內部轉帳搬走的，不一定是賣出。' : ''),
          'All long-term holders, and price has not touched this range in ' + f.days + ' days, so any change is selling, no model involved: ' + cohCoins(mf.before) + ' to ' + cohCoins(mf.after) + '. ' + (ch < -5 ? 'Holders trapped at the highs keep selling out, so there is less overhead supply waiting to break even.' : 'Little has moved, so price may still meet break-even selling up there.') + (tf ? ' About ' + cohCoins(tf) + ' of it left in a likely internal transfer, which is not necessarily selling.' : '')), ch < -5 ? 'pos' : 'neu']); }
    }
    (co.transfers || []).forEach(function (m) {   // 2026-10-27：疑似同一實體內部轉帳（cohort_urpd.transfers），已放回原本的成本與幣齡
      var bk = function (a) { return a.map(function (x) { return fmt.k(x[0]) + '–' + fmt.k(x[0] + w); }).join(_T('、', ', ')); };
      var rr = (co.raw || {}).rows || [], diff = 0; m.dst.forEach(function (x) { var a = rr.filter(function (r) { return r[0] === x[0]; })[0], b = co.rows.filter(function (r) { return r[0] === x[0]; })[0]; if (a && b) diff += a[1] - b[1]; });
      it.push([_T('疑似內部轉帳', 'Likely internal transfer'), cohCoins(m.btc), _T(fmt.md(m.date) + ' 有約 ' + cohCoins(m.btc) + '從 ' + bk(m.src) + ' 一天內搬到 ' + bk(m.dst) + '，平常遠離現價的格子一天只流出幾萬顆以下。逐筆 UTXO 會把它算成賣出再買進；量這麼大又集中，多半是同一實體整併錢包。上面的數字已把這批幣放回原本的成本與幣齡' + (co.raw ? '（不修正的話，短期持有者是 ' + cohCoins(co.raw.sth) + '，' + bk(m.dst) + ' 多出約 ' + cohCoins(diff) + '）' : '') + '。',
        fmt.md(m.date) + ': about ' + cohCoins(m.btc) + ' moved from ' + bk(m.src) + ' to ' + bk(m.dst) + ' in one day; buckets far from the price normally lose only a few tens of thousands of BTC a day at most. Per-UTXO data reads this as selling and rebuying; something this large and concentrated is most likely one entity consolidating wallets. The figures above put these coins back at their original cost and age' + (co.raw ? ' (uncorrected, short-term holders would be ' + cohCoins(co.raw.sth) + ', with about ' + cohCoins(diff) + ' more at ' + bk(m.dst) + ')' : '') + '.'), 'warn']);
    });
    if (co.vs) it.push([_T('推算 vs 實際', 'Estimate vs actual'), fmt.pct(co.vs.sth_diff_pct, 1), _T('推算模型的短期持有者 ' + cohCoins(co.vs.sth_model) + '，CheckOnChain 依實際幣齡算 ' + cohCoins(co.vs.sth_exact) + '；各格合計約 ' + fmt.n(co.vs.misplaced_pct, 0) + '% 分到了別的價位。' + (cohCmpExact() && co.cmp_model ? '「STH 變化／LTH 變化」已改用實際：' + fmt.md(co.cmp.date) + ' 的短期持有者實際 ' + cohCoins(co.cmp.tot.sth) + '（Bitview），推算是 ' + cohCoins(co.cmp_model.tot.sth) + '。' : '「STH 變化／LTH 變化」用的是推算（CheckOnChain 只有當下的快照）。'),
      'The model puts short-term holders at ' + cohCoins(co.vs.sth_model) + '; CheckOnChain, using actual coin age, has ' + cohCoins(co.vs.sth_exact) + '; about ' + fmt.n(co.vs.misplaced_pct, 0) + '% sits in a different bucket. ' + (cohCmpExact() && co.cmp_model ? '“STH change / LTH change” now use actual data: short-term holders on ' + fmt.md(co.cmp.date) + ' were ' + cohCoins(co.cmp.tot.sth) + ' (Bitview) versus an estimate of ' + cohCoins(co.cmp_model.tot.sth) + '.' : '“STH change / LTH change” use the estimate (CheckOnChain only has the current snapshot).')), Math.abs(co.vs.sth_diff_pct) <= 5 ? 'neu' : 'warn']);
    if (co.val) it.push([_T('驗證', 'Check'), fmt.pct(co.val.diff_pct, 2), _T('推算的短期持有者成本 ' + fmt.usd(co.val.ours) + '，' + cohValSrc() + ' 公布 ' + fmt.usd(co.val.bd) + '（' + fmt.md(co.val.date) + '）。這個數字沒有拿去校正，差距小代表拆分可信。',
      'Estimated STH cost ' + fmt.usd(co.val.ours) + ' vs ' + fmt.usd(co.val.bd) + ' published by ' + cohValSrc() + ' (' + fmt.md(co.val.date) + '). It is not used in the fit, so a small gap means the split holds up.'), Math.abs(co.val.diff_pct) <= 1 ? 'neu' : 'warn']);
    return it;
  }
  function cohLegend() {
    var f = (D.chips.cohort || {}).flow;
    if (cohMode === 'now') return legend([[_T('短期持有者 STH（< 155 天）', 'Short-term holders (< 155 days)'), 'var(--s2)'], [_T('長期持有者 LTH', 'Long-term holders'), 'var(--s1)'], [_T('收盤', 'Close'), 'var(--ink)']]);
    var co = D.chips.cohort; if (cohCmpExact()) return legend([[fmt.md(co.cmp.date) + _T('（Bitview 實際）', ' (Bitview, actual)'), 'var(--ink-3)'], [fmt.md(co.now_date) + _T('（CheckOnChain 實際）', ' (CheckOnChain, actual)'), cohMode === 'sth' ? 'var(--s2)' : 'var(--s1)']]);
    return legend([[fmt.md(f.start) + _T('（推算）', ' (estimate)'), 'var(--ink-3)'], [fmt.md(f.end) + _T('（推算）', ' (estimate)'), cohMode === 'sth' ? 'var(--s2)' : 'var(--s1)']]);
  }
  function cohSegs() {
    var b = function (v, z, e) { return '<button aria-pressed="' + (cohMode === v) + '" data-c="' + v + '">' + _T(z, e) + '</button>'; };
    return '<span class="seg">' + b('now', '現在', 'Now') + ((D.chips.cohort || {}).flow ? b('sth', 'STH 變化', 'STH change') + b('lth', 'LTH 變化', 'LTH change') : '') + '</span>';
  }
  function cohortPanel() {
    var co = (D.chips || {}).cohort; if (!co || !co.rows) return '';
    var L = (co.loss || []).slice(0, 8);
    var tbl = L.length ? '<div class="tbl-wrap" style="margin-top:12px"><table class="tbl"><thead><tr><th>' + _T('收盤跌到', 'If price falls to') + '</th><th class="num">' + _T('STH 帳面虧損', 'STH underwater') + '</th><th class="num">' + _T('佔 STH', 'Share of STH') + '</th><th class="num">' + _T('LTH 帳面虧損', 'LTH underwater') + '</th></tr></thead><tbody>' +
      L.map(function (r) { return '<tr><td><span class="num">' + fmt.usd(r[0]) + '</span></td><td class="num">' + cohCoins(r[1]) + '</td><td class="num">' + fmt.n(r[1] / co.tot.sth * 100, 0) + '%</td><td class="num">' + cohCoins(r[2]) + '</td></tr>'; }).join('') + '</tbody></table></div>' : '';
    return panel('span-12', _T('長短期持有者籌碼', 'Long- vs short-term holder supply'), (cohExact() ? (cohCmpExact() ? _T('現在：CheckOnChain ' + fmt.md(co.now_date) + ' · 30 天前：Bitview ' + fmt.md(co.cmp.date) + ' · 誰賣了：推算', 'Now: CheckOnChain ' + fmt.md(co.now_date) + ' · 30 days ago: Bitview ' + fmt.md(co.cmp.date) + ' · who sold: estimate') : _T('現在：CheckOnChain 實際幣齡 ' + fmt.md(co.now_date) + ' · 變化：推算', 'Now: CheckOnChain actual coin age ' + fmt.md(co.now_date) + ' · changes: estimate')) : _T('推算 · bitcoin-data URPD × 幣齡分布 · ' + fmt.md(co.date), 'Estimate · bitcoin-data URPD × coin age · ' + fmt.md(co.date))),
      interpHtml(cohSay()) + '<div id="coh-lg" style="margin-top:10px">' + cohLegend() + '</div><div class="chart" id="c-cohort"></div>' + tbl +
      '<p class="note">' + (cohExact() ? _T('「現在」來自 CheckOnChain 的公開圖表（Bitcoin Research Kit 依每顆幣的實際幣齡算），併成每 2,000 美元一格。' + (cohCmpExact() ? '「30 天前」來自 Bitview（同一套 Bitcoin Research Kit 的公開 API），套用同樣的搬家修正，所以「STH 變化／LTH 變化」是實際對實際；只有誰賣了、誰滿 155 天轉成長期（下面的流向）還是推算。' : ''), '“Now” comes from CheckOnChain\'s public chart (Bitcoin Research Kit, using each coin\'s actual age), regrouped into $2,000 buckets. ' + (cohCmpExact() ? '“30 days ago” comes from Bitview (the public API of the same Bitcoin Research Kit) with the same transfer correction, so the STH/LTH change views compare actual with actual; only who sold and who aged into long-term (the flows below) is still estimated. ' : '')) : '') + _T('變化的做法：每天新產生的幣放進當天價格區間所在的格子，再讓各幣齡帶與各價格格的總量同時對上 bitcoin-data 的幣齡分布與 URPD；持有不到 155 天算短期持有者。過去 155 天價格走過 ' + fmt.k(co.window.lo) + '–' + fmt.k(co.window.hi) + '，這個區間外只有長期持有者，不靠模型；區間內的拆分是推算。逐筆 UTXO、不是 Glassnode 的實體調整：交易所與託管整理錢包會被當成賣出再買進，換手量偏高；單日大量從遠離現價的格子搬到現價的（疑似同一實體內部轉帳），會放回原本的成本與幣齡。',
        'How changes are estimated: coins created each day go into the buckets that day\'s price range covered; then age-band and price-bucket totals are matched to bitcoin-data\'s HODL waves and URPD at the same time. Held under 155 days = short-term holder. Price covered ' + fmt.k(co.window.lo) + '–' + fmt.k(co.window.hi) + ' in the past 155 days; outside that range there are only long-term holders, no model involved; inside it the split is an estimate. Per-UTXO, not entity-adjusted like Glassnode: exchange and custodian wallet reshuffles look like selling and rebuying, so turnover reads high; large one-day moves from buckets far from the price into the current price (likely one entity moving its own coins) are put back at their original cost and age.') + '</p>',
      '<span id="coh-segs" style="display:contents">' + cohSegs() + '</span>');
  }
  function drawCohort(el) {
    var co = (D.chips || {}).cohort; if (!co || !el) return;
    var w = co.width, c = co.price, W = Math.max(300, el.clientWidth), cs = { sth: 'var(--s2)', lth: 'var(--s1)' }, s = '', rows, rh = W < 520 ? 13 : 14;
    var pxRow = function (rws, top) { for (var i = 0; i < rws.length; i++) if (c >= rws[i][0] && c < rws[i][0] + w) return top + i * rh + rh * (1 - (c - rws[i][0]) / w); return null; };
    var bar = function (x0, x1, y, h, col) { var L_ = Math.abs(x1 - x0); if (L_ < 0.5) return ''; var r = Math.min(3, L_, h / 2), d = x1 >= x0 ? 1 : -1;
      return '<path fill="' + col + '" d="M' + x0.toFixed(1) + ',' + y + 'H' + (x1 - d * r).toFixed(1) + 'Q' + x1.toFixed(1) + ',' + y + ' ' + x1.toFixed(1) + ',' + (y + r) + 'V' + (y + h - r) + 'Q' + x1.toFixed(1) + ',' + (y + h) + ' ' + (x1 - d * r).toFixed(1) + ',' + (y + h) + 'H' + x0.toFixed(1) + 'Z"/>'; };
    var tx_ = function (x, y, t, a, cls) { return '<text x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '"' + (a ? ' text-anchor="' + a + '"' : '') + ' class="' + (cls || 'ax') + '">' + esc(t) + '</text>'; };
    var unit = _T('萬顆', 'K BTC'), u = function (v) { return LANG === 'en' ? fmt.n(v / 1e3, 0) : fmt.n(v / 1e4, 0); };
    var tipRow = function (lab, items) { return '<div class="t">' + lab + '</div>' + items.map(function (x) { return '<div class="r"><i style="background:' + x[1] + '"></i><span>' + x[0] + '</span><b>' + cohCoins(x[2]) + '</b></div>'; }).join(''); }, tips = [];
    if (cohMode === 'now') {
      rows = co.rows.filter(cohRange(cohLo(), 1e9)).slice().reverse();
      var top = 18, mid = 46, pad = W < 520 ? 52 : 60, side = (W - mid) / 2, mx = Math.max.apply(null, rows.map(function (r) { return Math.max(r[1], r[2]); })) || 1, sx = function (v) { return v / mx * (side - pad); };
      var x0 = side, x1 = side + mid, yb = top + rows.length * rh, Ht = yb + 20, st = niceStep(mx, 3);
      var wlo = rows.findIndex(function (r) { return r[0] < co.window.hi; }), whi = rows.findIndex(function (r) { return r[0] + w <= co.window.lo; });
      if (wlo >= 0) s += '<rect x="0" y="' + (top + wlo * rh) + '" width="' + x0 + '" height="' + ((whi < 0 ? rows.length : whi) - wlo) * rh + '" fill="var(--deck-2)"/>';
      for (var g = st; g < mx; g += st) [x0 - sx(g), x1 + sx(g)].forEach(function (x) { s += '<line x1="' + x.toFixed(1) + '" x2="' + x.toFixed(1) + '" y1="' + (top - 2) + '" y2="' + yb + '" stroke="var(--grid)"/>' + tx_(x, yb + 13, u(g), 'middle'); });
      s += tx_(0, yb + 13, unit) + tx_(W, yb + 13, unit, 'end') + tx_(x0 - 4, 11, _T('← 短期持有者', '← Short-term'), 'end') + tx_(x1 + 4, 11, _T('長期持有者 →', 'Long-term →'));
      rows.forEach(function (r, i) {
        var y = top + i * rh, cur = c >= r[0] && c < r[0] + w;
        s += '<g class="hit" data-i="' + i + '"><rect x="0" y="' + y + '" width="' + W + '" height="' + rh + '" fill="transparent"/>' + bar(x0, x0 - sx(r[1]), y + 2, rh - 4, cs.sth) + bar(x1, x1 + sx(r[2]), y + 2, rh - 4, cs.lth) + tx_(x0 + mid / 2, y + rh - 3, fmt.k(r[0]), 'middle', cur ? 'ax hi' : 'ax') + '</g>';
        tips.push(tipRow(fmt.usd(r[0]) + '–' + fmt.usd(r[0] + w), [[_T('短期持有者', 'Short-term'), cs.sth, r[1]], [_T('長期持有者', 'Long-term'), cs.lth, r[2]]]));
      });
      var bs = cohTop(rows, 1)[0], bl = cohTop(rows.filter(function (r) { return r[0] >= c; }), 2)[0];
      [[bs, 1, -1], [bl, 2, 1]].forEach(function (q) { if (!q[0]) return; var i = rows.indexOf(q[0]), y = top + i * rh + rh - 3; s += q[2] < 0 ? tx_(x0 - sx(q[0][1]) - 4, y, cohCoins(q[0][1]), 'end', 'ax hi') : tx_(x1 + sx(q[0][2]) + 4, y, cohCoins(q[0][2]), 'start', 'ax hi'); });
      var yp = pxRow(rows, top); if (yp != null) s += '<line x1="0" x2="' + W + '" y1="' + yp.toFixed(1) + '" y2="' + yp.toFixed(1) + '" stroke="var(--ink)" stroke-width="1"/>' + tx_(W, yp - 3, _T('收盤 ', 'Close ') + fmt.usd(c), 'end', 'ax hi');
      if (wlo >= 0) s += tx_(4, top + wlo * rh + 10, (W < 520 ? _T('155 天內價格走過', 'Traded within 155d') : _T('155 天內價格走過的區間', 'Range price covered in 155 days'))   /* 2026-11-04：手機用短句，英文原句會撞到中間的價位欄 */, 'start');
    } else {
      var k = cohMode === 'sth' ? 1 : 2, f = co.flow, cmp = {}; co.cmp.rows.forEach(function (r) { cmp[r[0]] = r; });
      rows = (cohCmpExact() ? co.rows : (co.model_rows || co.rows)).filter(k === 1 ? cohRange(Math.floor(co.window.lo / w) * w, co.window.hi) : cohRange(cohLo(), 1e9)).slice().reverse();
      var lab = 44, right = 64, top2 = 6, mx2 = Math.max.apply(null, rows.map(function (r) { return Math.max(r[k], (cmp[r[0]] || [])[k] || 0); })) || 1, sx2 = function (v) { return v / mx2 * (W - lab - right); }, yb2 = top2 + rows.length * (rh + 2), Ht2 = yb2 + 6;
      var big = rows.map(function (r) { return Math.abs(r[k] - ((cmp[r[0]] || [])[k] || 0)); }).sort(function (a, b) { return b - a; })[3] || 0;
      if (k === 2 && f.model_free_above) { var j = rows.findIndex(function (r) { return r[0] < f.model_free_above.lo; }); if (j > 0) s += '<rect x="' + lab + '" y="' + top2 + '" width="' + (W - lab) + '" height="' + j * (rh + 2) + '" fill="var(--deck-2)"/>' + tx_(W - 2, top2 + 11, (W < 520 ? _T('價格沒碰過：變化就是賣出', 'Untouched: changes = selling') : _T('價格沒碰過：變化就是賣出，不靠模型', 'Untouched by price: changes are selling, no model')), 'end'); }
      rows.forEach(function (r, i) {
        var y = top2 + i * (rh + 2), a = (cmp[r[0]] || [])[k] || 0, d = r[k] - a, cur = c >= r[0] && c < r[0] + w;
        s += '<g class="hit" data-i="' + i + '"><rect x="0" y="' + y + '" width="' + W + '" height="' + (rh + 2) + '" fill="transparent"/>' + bar(lab, lab + sx2(a), y + 2, 4, 'var(--ink-3)') + bar(lab, lab + sx2(r[k]), y + 7, rh - 6, k === 1 ? cs.sth : cs.lth) + tx_(lab - 6, y + rh - 1, fmt.k(r[0]), 'end', cur ? 'ax hi' : 'ax') +
          (Math.abs(d) >= big && Math.abs(d) > 0 ? tx_(lab + sx2(Math.max(a, r[k])) + 5, y + rh - 1, (d > 0 ? '+' : '−') + cohCoins(Math.abs(d)), 'start', 'ax hi') : '') + '</g>';
        tips.push('<div class="t">' + fmt.usd(r[0]) + '–' + fmt.usd(r[0] + w) + '</div><div class="r"><i style="background:var(--ink-3)"></i><span>' + fmt.md(f.start) + '</span><b>' + cohCoins(a) + '</b></div><div class="r"><i style="background:' + (k === 1 ? cs.sth : cs.lth) + '"></i><span>' + fmt.md(f.end) + '</span><b>' + cohCoins(r[k]) + '</b></div><div class="r"><i></i><span>' + _T('變化', 'Change') + '</span><b>' + (d >= 0 ? '+' : '−') + cohCoins(Math.abs(d)) + '</b></div>');
      });
      s += '<line x1="' + lab + '" x2="' + lab + '" y1="' + top2 + '" y2="' + yb2 + '" stroke="var(--line)"/>';
      Ht = Ht2;
    }
    el.innerHTML = svgEl(W, Ht, s, _T('長短期持有者籌碼分布', 'Supply by long- and short-term holders'));
    el.querySelectorAll('g.hit').forEach(function (n) { var i = +n.getAttribute('data-i'); n.addEventListener('pointermove', function (ev) { showTip(ev.clientX, ev.clientY, tips[i]); }); n.addEventListener('pointerleave', hideTip); });
  }
  function cohortAfter() {
    mount($('#c-cohort'), drawCohort);
    var sg = $('#coh-segs'); if (sg) sg.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b || b.getAttribute('data-c') === cohMode) return; cohMode = b.getAttribute('data-c'); sg.innerHTML = cohSegs(); $('#coh-lg').innerHTML = cohLegend(); drawCohort($('#c-cohort')); });
  }

  /* 價格 × 長期持有者 30 日淨部位（2026-10-29 使用者要求，參考 Glassnode「吸籌趨勢評分」的畫法）：價格線依淨部位上色，
     品牌橘紅＝淨減、灰＝持平、綠＝淨增（2026-11-09 照紅綠規則，原本紅／藍），±40 萬顆最深。不是 Glassnode 的評分（那個以實體計、排除交易所）。只作讀值 */
  /* 9 階：|淨部位| < clip ÷ 8 是中間的灰（持平）；圖例的「持平」範圍也由 clip 算，改 LC_CLIP 不會對不上（2026-11-04） */
  function lcLv(v, clip) { return Math.max(0, Math.min(8, Math.round(v / clip * 4) + 4)); }
  function lcCoins(v) { return (v > 0 ? '+' : v < 0 ? '−' : '') + cohCoins(Math.abs(v)); }
  function lcSay() {
    var x = D.onchain.lth_color, r = x.run, it = [], up = r.price_chg_pct > 5, dn_ = r.price_chg_pct < -5, sell = r.sign < 0, ls = (D.onchain || {}).lsr;
    var since = _T('從 ' + fmt.md(r.start) + ' 起連續 ' + r.days + ' 天淨' + (sell ? '減' : '增') + '（最多 ' + lcCoins(r.extreme) + '），同期價格 ' + fmt.pct(r.price_chg_pct, 0) + '（' + fmt.usd(r.price0) + ' → ' + fmt.usd(r.price) + '）。',
      'Net ' + (sell ? 'reducing' : 'adding') + ' for ' + r.days + ' straight days since ' + fmt.md(r.start) + ' (peak ' + lcCoins(r.extreme) + '), while price moved ' + fmt.pct(r.price_chg_pct, 0) + ' (' + fmt.usd(r.price0) + ' → ' + fmt.usd(r.price) + '): ');
    var why = sell ? (up ? _T('價格漲、長期持有者減：長期持有者趁反彈出貨，上方一直有人供貨。', 'price up while long-term holders cut, so they are selling into the rally and supplying the market above.') :
      dn_ ? _T('價格跌、長期持有者也減：賣壓有一部分來自持有很久的人。', 'price down and long-term holders cutting too, so part of the selling comes from long-held coins.') :
      _T('價格沒什麼動、長期持有者在減：長期持有者在這個價位出貨，有人接得住。', 'price flat while long-term holders cut, so they are distributing at this level and buyers are absorbing it.')) :
      (dn_ ? _T('價格跌、長期持有者淨增：持有的人沒賣；增加的部分也包括幣放滿 155 天自動轉成長期。', 'price down yet long-term holders grow, so holders are not selling; part of the rise is coins simply aging past 155 days.') :
      up ? _T('價格漲、長期持有者淨增：上漲時長期持有者沒有出貨。', 'price up and long-term holders still growing, so they are not selling into the rise.') :
      _T('價格沒什麼動、長期持有者淨增：籌碼在沉澱。', 'price flat and long-term holders growing, so supply is settling into stronger hands.'));
    it.push([_T('長期持有者 30 日淨部位', 'LTH 30-day net position'), lcCoins(x.last), since + why, sell ? 'warn' : 'pos']);
    var p = x.prev_same;
    var md_ = function (s) { return s.replace(/-/g, '/'); };   // 2026-11-05 長短期持有者供給比（Bitview）
    if (ls) it.push([_T('長短期持有者供給比', 'LTH ÷ STH supply'), fmt.n(ls.value, 2),
      _T('長期持有者 ' + cohCoins(ls.lth) + ' ÷ 短期持有者 ' + cohCoins(ls.sth) + '（Bitview，' + fmt.md(ls.date) + '）。30 天前 ' + fmt.n(ls.d30, 2) + '（' + fmt.pct(ls.chg30_pct, 1) + '）' + (ls.d365 != null ? '、一年前 ' + fmt.n(ls.d365, 2) : '') + '；一年內最高 ' + fmt.n(ls.hi1y.value, 2) + '（' + md_(ls.hi1y.date) + '）、最低 ' + fmt.n(ls.lo1y.value, 2) + '（' + md_(ls.lo1y.date) + '）；2015 年以來第 ' + fmt.n(ls.pct, 0) + ' 百分位。下降＝短期籌碼變多（長期持有者分發或短期持有者進場），上升＝籌碼沉澱（也包括幣放滿 155 天自動轉成長期）。',
        'Long-term ' + cohCoins(ls.lth) + ' ÷ short-term ' + cohCoins(ls.sth) + ' (Bitview, ' + fmt.md(ls.date) + '). 30 days ago ' + fmt.n(ls.d30, 2) + ' (' + fmt.pct(ls.chg30_pct, 1) + ')' + (ls.d365 != null ? ', a year ago ' + fmt.n(ls.d365, 2) : '') + '; 1-year high ' + fmt.n(ls.hi1y.value, 2) + ' (' + md_(ls.hi1y.date) + '), low ' + fmt.n(ls.lo1y.value, 2) + ' (' + md_(ls.lo1y.date) + '); ' + fmt.n(ls.pct, 0) + 'th percentile since 2015. Falling = more short-term supply (long-term holders distributing or short-term holders arriving); rising = supply settling (including coins simply aging past 155 days).'), 'neu']);
    var lcView = sell && !dn_ ? viewRow(_T('換手中', 'Handover under way'),
        _T('長期持有者從 ' + fmt.md(r.start) + ' 起淨減 ' + r.days + ' 天，同期價格 ' + fmt.pct(r.price_chg_pct, 0) + (ls && ls.chg30_pct < 0 ? '，長短期持有者供給比從一年內高點 ' + fmt.n(ls.hi1y.value, 2) + ' 降到 ' + fmt.n(ls.value, 2) : '') + '：籌碼正從長期持有者轉到短期持有者手上，而且有人接得住（價格沒跌）。從真實市場均價走到新高，前幾輪都要經過這種換手，而且都花了很久；我們看這是中段的消化，不是頂部出貨。',
          'Long-term holders have been net sellers for ' + r.days + ' days since ' + fmt.md(r.start) + ' while price moved ' + fmt.pct(r.price_chg_pct, 0) + (ls && ls.chg30_pct < 0 ? ', and the LTH ÷ STH supply ratio fell from a 1-year high of ' + fmt.n(ls.hi1y.value, 2) + ' to ' + fmt.n(ls.value, 2) : '') + ': supply is passing from long-term holders to short-term holders, and it is being absorbed (price has not fallen). Every past climb from the true market mean to a new high needed this handover, and it always took a while; we read it as mid-cycle digestion, not top distribution. '),
        _T('長期持有者繼續減、價格開始跌（派發接不住）。', 'long-term holders keep selling while price starts falling (distribution not absorbed).'), 'neu')
      : sell ? viewRow(_T('派發', 'Distribution'),
        _T('長期持有者在減、價格也在跌：賣壓有一部分來自持有很久的人，接盤不夠。我們看偏弱。', 'Long-term holders selling into a falling price: part of the selling comes from long-held coins and buyers are not absorbing it. Soft. '),
        _T('長期持有者轉為淨增，或價格止跌。', 'long-term holders turning net buyers, or price stabilising.'), 'warn')
      : viewRow(_T('籌碼沉澱', 'Supply settling'),
        _T('長期持有者淨增：持有的人沒在賣（也包括幣放滿 155 天自動轉成長期）。供給在變少，我們看結構偏多。', 'Long-term holders net adding: holders are not selling (coins ageing past 155 days also count). Supply is thinning; structurally constructive. '),
        _T('長期持有者轉為淨減。', 'long-term holders turning net sellers.'), 'pos');
    it.push([_T('四年位置', '4-year rank'), fmt.n(x.pct_4y, 0) + _T(' 百分位', 'th pct'), _T('0＝四年來淨減最多的一天、100＝淨增最多。', '0 = the heaviest net reduction in four years, 100 = the heaviest net addition. ') +
      (p ? _T('這段之前，上一次淨' + (x.last < 0 ? '減' : '增') + '這麼多是 ' + p.date.replace(/-/g, '/') + '（' + lcCoins(p.value) + '，價格 ' + fmt.usd(p.price) + '）。', 'Before this run, the last time it was this ' + (x.last < 0 ? 'negative' : 'positive') + ' was ' + p.date.replace(/-/g, '/') + ' (' + lcCoins(p.value) + ', price ' + fmt.usd(p.price) + '). ') : '') +
      (x.vs_hi1y_pct > -2 ? _T('價格就在一年高點 ' + fmt.usd(x.hi1y) + ' 附近。', 'Price is at the one-year high of ' + fmt.usd(x.hi1y) + '.') : _T('價格比一年高點 ' + fmt.usd(x.hi1y) + ' 低 ' + fmt.n(-x.vs_hi1y_pct, 0) + '%。', 'Price is ' + fmt.n(-x.vs_hi1y_pct, 0) + '% below the one-year high of ' + fmt.usd(x.hi1y) + '.')), 'neu']);
    it.push(lcView);
    return it;
  }
  function lthColorPanel() {
    var x = (D.onchain || {}).lth_color; if (!x || !x.rows) return '';
    var k = x.clip / (LANG === 'en' ? 1e3 : 1e4) + _T(' 萬', 'K');
    return panel('span-12', _T('價格 × 長期持有者動向', 'Price × long-term holder flow'), _T('bitcoin-data · 長期持有者 30 日淨部位 · ' + fmt.md(x.date), 'bitcoin-data · LTH 30-day net position · ' + fmt.md(x.date)),
      interpHtml(lcSay()) + '<div class="legend" style="margin-top:10px"><span><b style="color:var(--ink-2);font-weight:400">' + _T('淨減 ≥' + k, 'Net cut ≥' + k) + '</b><i class="lc-bar"></i><b style="color:var(--ink-2);font-weight:400">' + _T('淨增 ≥' + k, 'Net add ≥' + k) + '</b></span><span><b style="color:var(--ink-2);font-weight:400">' + _T('中間灰色＝持平（±' + fmt.n(x.clip / 8 / 1e4, 0) + ' 萬內）', 'grey middle = flat (within ±' + fmt.n(x.clip / 8 / 1e3, 0) + 'K)') + '</b></span></div><div class="chart" id="c-lthc"></div>' +
      '<p class="note">' + _T('長期持有者＝持有 155 天以上。淨部位上升不全是買入：幣放滿 155 天就自動算成長期持有者。這不是 Glassnode 的吸籌趨勢評分（那個先把地址歸成實體、排除交易所，屬付費資料）；bitcoin-data 同名的指標和這條線是同一個數字換算。',
        'Long-term holder = held 155 days or more. A rising net position is not all buying: coins become “long-term” automatically once they reach 155 days. This is not Glassnode\'s Accumulation Trend Score (entity-based, exchanges excluded, paid data); bitcoin-data\'s indicator of that name is a rescaling of this same series.') + '</p>');
  }
  function drawLthColor(el) {
    var x = (D.onchain || {}).lth_color; if (!x || !el) return;
    var R_ = x.rows, W = Math.max(280, el.clientWidth), Ht = W < 520 ? 230 : 300, ML = 8, MR = 58, MT = 14, MB = 24, pw = W - ML - MR, ph = Ht - MT - MB;
    var x0 = R_[0][0], x1 = R_[R_.length - 1][0], lp = R_.map(function (r) { return Math.log10(r[1]); }), tl = Math.min.apply(null, lp), th = Math.max.apply(null, lp), pad = (th - tl) * 0.06; tl -= pad; th += pad;
    var X = function (v) { return ML + (v - x0) / (x1 - x0 || 1) * pw; }, Y = function (v) { return MT + (1 - (Math.log10(v) - tl) / (th - tl)) * ph; }, s = '';
    [1e4, 2e4, 3e4, 5e4, 8e4, 12e4, 2e5].forEach(function (t) { var l = Math.log10(t); if (l < tl || l > th) return; var y = Y(t); s += '<line class="gl" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (y + 3.5).toFixed(1) + '">' + fmt.k(t) + '</text>'; });
    var y0 = new Date(x0 * 864e5).getUTCFullYear() + 1, yr = new Date(x1 * 864e5).getUTCFullYear();
    for (var y = y0; y <= yr; y++) { var xx = X(Date.UTC(y, 0, 1) / 864e5); if (xx > ML + 16 && xx < ML + pw - 16) s += '<line class="gl" x1="' + xx.toFixed(1) + '" x2="' + xx.toFixed(1) + '" y1="' + (MT + ph) + '" y2="' + (MT + ph + 4) + '"/><text class="ax" x="' + xx.toFixed(1) + '" y="' + (Ht - 6) + '" text-anchor="middle">' + y + '</text>'; }
    // 同一階的相鄰線段併成一條 path（每段的顏色取終點那天的淨部位）
    var cur = -1, d = '';
    var flush = function () { if (d) s += '<path d="' + d + '" fill="none" stroke="var(--lc' + cur + ')" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'; };
    for (var i = 1; i < R_.length; i++) {
      var lv = lcLv(R_[i][2], x.clip), a = X(R_[i - 1][0]).toFixed(1) + ',' + Y(R_[i - 1][1]).toFixed(1), b = X(R_[i][0]).toFixed(1) + ',' + Y(R_[i][1]).toFixed(1);
      if (lv !== cur) { flush(); cur = lv; d = 'M' + a + 'L' + b; } else d += 'L' + b;
    }
    flush();
    var z = R_[R_.length - 1]; s += '<circle cx="' + X(z[0]).toFixed(1) + '" cy="' + Y(z[1]).toFixed(1) + '" r="4" fill="var(--lc' + lcLv(z[2], x.clip) + ')" stroke="var(--deck)" stroke-width="2"/>';
    s += '<line class="xh" x1="0" x2="0" y1="' + MT + '" y2="' + (MT + ph) + '" visibility="hidden"/><g class="hdots"></g><rect class="hit" x="' + ML + '" y="' + MT + '" width="' + pw + '" height="' + ph + '"/>';
    el.innerHTML = svgEl(W, Ht, s, _T('價格 × 長期持有者 30 日淨部位', 'Price × long-term holder 30-day net position'));
    var svg = el.querySelector('svg'), xh = svg.querySelector('.xh'), dots = svg.querySelector('.hdots'), hit = svg.querySelector('.hit');
    function move(ev) {
      var r = svg.getBoundingClientRect(), xv = x0 + ((ev.clientX - r.left) * W / r.width - ML) / pw * (x1 - x0), p = R_[bisect(R_, xv)], c = 'var(--lc' + lcLv(p[2], x.clip) + ')';
      xh.setAttribute('x1', X(p[0])); xh.setAttribute('x2', X(p[0])); xh.setAttribute('visibility', 'visible');
      dots.innerHTML = '<circle cx="' + X(p[0]).toFixed(1) + '" cy="' + Y(p[1]).toFixed(1) + '" r="4" fill="' + c + '" stroke="var(--deck)" stroke-width="2"/>';
      showTip(ev.clientX, ev.clientY, '<div class="t">' + fmt.date(p[0]) + '</div><div class="r"><i style="background:var(--ink-3)"></i><span>' + _T('BTC 價格', 'BTC price') + '</span><b>' + fmt.usd(p[1]) + '</b></div><div class="r"><i style="background:' + c + '"></i><span>' + _T('長期持有者 30 日淨部位', 'LTH 30-day net position') + '</span><b>' + lcCoins(p[2]) + '</b></div>');
    }
    hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', function () { xh.setAttribute('visibility', 'hidden'); dots.innerHTML = ''; hideTip(); });
  }

  /* 短期持有者獲利比例 ＋ BTC 週 K（2026-10-31 使用者要求：對照價格）：上下兩格共用時間軸與十字線，不疊成雙 y 軸。
     週 K 是 Kraken 週線（週四起算）；沒有 kw 時退回只畫獲利比例 */
  function drawProfitK(el) {
    var v = D.chips.viz || {}, P = (v.profit || []).filter(function (p) { return p[1] != null; }), K = v.kw || [];
    if (P.length < 2) { el.innerHTML = _t('<p class="note">本日未取得資料。</p>'); return; }
    var W = Math.max(280, el.clientWidth), sm = W < 520, ML = 8, MR = 58, MT = 16, hk = K.length ? (sm ? 120 : 150) : 0, gap = K.length ? 28 : 0, hp = sm ? 110 : 130, MB = 24, Ht = MT + hk + gap + hp + MB, pw = W - ML - MR;
    var x0 = Math.min(P[0][0], K.length ? K[0][0] : Infinity), x1 = Math.max(P[P.length - 1][0], K.length ? K[K.length - 1][0] + 6 : -Infinity);
    var X = function (t) { return ML + (t - x0) / (x1 - x0 || 1) * pw; }, s = '', yp0 = MT + hk + gap;
    var Yp = function (q) { return yp0 + (1 - q / 100) * hp; };
    if (K.length) {
      var lo = Math.log10(Math.min.apply(null, K.map(function (k) { return k[3]; }))), hi = Math.log10(Math.max.apply(null, K.map(function (k) { return k[2]; }))), pd = (hi - lo) * 0.05; lo -= pd; hi += pd;
      var Yk = function (q) { return MT + (1 - (Math.log10(q) - lo) / (hi - lo)) * hk; }, bw = Math.max(1, (X(7) - X(0)) * 0.62);
      [1e4, 2e4, 3e4, 5e4, 8e4, 12e4, 2e5].forEach(function (t) { var l = Math.log10(t); if (l < lo || l > hi) return; var y = Yk(t); s += '<line class="gl" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/>' + axText(ML + pw + 8, y + 3.5, fmt.k(t)); });
      K.forEach(function (k) {
        var cx = X(k[0] + 3.5), up = k[4] >= k[1], col = up ? 'var(--up)' : 'var(--down)', yo = Yk(k[1]), yc = Yk(k[4]);
        s += candleMark(cx, bw, yo, Yk(k[2]), Yk(k[3]), yc, col);
      });
      s += axText(ML, MT - 5, _T('BTC 週 K（對數刻度）', 'BTC weekly candles (log scale)'));
    }
    [0, 50, 100].forEach(function (q) { var y = Yp(q); s += '<line class="' + (q ? 'gl' : 'base') + '" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"' + (q === 50 ? ' stroke-dasharray="4 3"' : '') + '/>' + axText(ML + pw + 8, y + 3.5, q + '%'); });
    // 2026-11-04：97.5% 賣出線（幾乎每個短期持有者都有獲利可以了結）與 50% 線（短期持有者整體回到獲利）
    s += '<rect x="' + ML + '" y="' + Yp(100).toFixed(1) + '" width="' + pw + '" height="' + (Yp(97.5) - Yp(100)).toFixed(1) + '" fill="var(--down-dim)"/><line x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + Yp(97.5).toFixed(1) + '" y2="' + Yp(97.5).toFixed(1) + '" stroke="var(--down)" stroke-dasharray="4 3" stroke-width="1"/>';
    s += axText(ML, yp0 - 9, _T('短期持有者獲利比例（紅虛線 97.5% 賣出線、灰虛線 50%）', 'STH supply in profit (red dashed: 97.5% sell line; grey dashed: 50%)'));
    var pts = P.map(function (p) { return X(p[0]).toFixed(1) + ',' + Yp(p[1]).toFixed(1); }), line = 'M' + pts.join('L');
    s += '<defs><linearGradient id="gpk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--s3)" stop-opacity=".5"/><stop offset="1" stop-color="var(--s3)" stop-opacity="0"/></linearGradient></defs>' +
      '<path d="' + line + 'L' + X(P[P.length - 1][0]).toFixed(1) + ',' + Yp(0).toFixed(1) + 'L' + X(P[0][0]).toFixed(1) + ',' + Yp(0).toFixed(1) + 'Z" fill="url(#gpk)"/><path class="ln" d="' + line + '" stroke="var(--s3)"/>';
    var lp = P[P.length - 1]; s += '<circle cx="' + X(lp[0]).toFixed(1) + '" cy="' + Yp(lp[1]).toFixed(1) + '" r="4" fill="var(--s3)" stroke="var(--deck)" stroke-width="2"/>';
    // 年份刻度與異動標記（貫穿上下兩格）
    for (var y = new Date(x0 * 864e5).getUTCFullYear() + 1; y <= new Date(x1 * 864e5).getUTCFullYear(); y++) { var xx = X(Date.UTC(y, 0, 1) / 864e5); if (xx > ML + 16 && xx < ML + pw - 16) s += axText(xx, Ht - 6, String(y), 'middle'); }
    sigV(el).forEach(function (g) { var xx = X(g.x); if (xx < ML || xx > ML + pw) return; s += '<line x1="' + xx.toFixed(1) + '" x2="' + xx.toFixed(1) + '" y1="' + MT + '" y2="' + (yp0 + hp) + '" stroke="var(--ink-3)" stroke-dasharray="2 4" stroke-width="1"/>' + axText(xx > ML + pw - 70 ? xx - 5 : xx + 5, yp0 + hp - 6, g.label, xx > ML + pw - 70 ? 'end' : ''); });
    s += '<line class="xh" x1="0" x2="0" y1="' + MT + '" y2="' + (yp0 + hp) + '" visibility="hidden"/><g class="hdots"></g><rect class="hit" x="' + ML + '" y="' + MT + '" width="' + pw + '" height="' + (yp0 + hp - MT) + '"/>';
    el.innerHTML = svgEl(W, Ht, s, _T('BTC 週 K 與短期持有者獲利比例', 'BTC weekly candles and STH supply in profit'));
    animateLines(el);
    var svg = el.querySelector('svg'), xh = svg.querySelector('.xh'), dots = svg.querySelector('.hdots'), hit = svg.querySelector('.hit');
    function move(ev) {
      var r = svg.getBoundingClientRect(), xv = x0 + ((ev.clientX - r.left) * W / r.width - ML) / pw * (x1 - x0), p = P[bisect(P, xv)], k = null;
      for (var i = K.length - 1; i >= 0; i--) if (K[i][0] <= p[0]) { k = p[0] - K[i][0] < 7 ? K[i] : null; break; }
      xh.setAttribute('x1', X(p[0])); xh.setAttribute('x2', X(p[0])); xh.setAttribute('visibility', 'visible');
      dots.innerHTML = '<circle cx="' + X(p[0]).toFixed(1) + '" cy="' + Yp(p[1]).toFixed(1) + '" r="4" fill="var(--s3)" stroke="var(--deck)" stroke-width="2"/>';
      var kc = k ? (k[4] >= k[1] ? 'var(--up)' : 'var(--down)') : '';
      showTip(ev.clientX, ev.clientY, '<div class="t">' + fmt.date(p[0]) + '</div><div class="r"><i style="background:var(--s3)"></i><span>' + _T('獲利比例', 'In profit') + '</span><b>' + p[1].toFixed(1) + '%</b></div>' +
        (k ? '<div class="r"><i style="background:' + kc + '"></i><span>' + _T('週收（' + fmt.md(fmt.date(k[0]).replace(/\//g, '-')) + ' 起）', 'Week from ' + fmt.md(fmt.date(k[0]).replace(/\//g, '-')) + ', close') + '</span><b>' + fmt.usd(k[4]) + '</b></div><div class="r"><i></i><span>' + _T('開／高／低', 'O / H / L') + '</span><b>' + fmt.k(k[1]) + ' / ' + fmt.k(k[2]) + ' / ' + fmt.k(k[3]) + '</b></div>' : ''));
    }
    hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', function () { xh.setAttribute('visibility', 'hidden'); dots.innerHTML = ''; hideTip(); });
  }

  /* 賣方衰竭常數（2026-11-02 使用者要求，賣方衰竭指數；資料取自 CheckOnChain）：獲利供給比例 × 30 天價格波動。
     刻度和 Glassnode 版不同，極端區用本身的歷史分布（低於 0.13 約是 2011 年起最低 1% 的日子）。上下兩格共用時間軸，不疊成雙 y 軸。只作讀值 */
  function secYm(s) { return s.slice(0, 7).replace('-', '/'); }
  function secSay() {
    var x = D.onchain.sec, it = [], H = x.hits || [], last = H[H.length - 1], rl = x.recent_low;
    var done = H.filter(function (h) { return h.done; }), up = done.filter(function (h) { return h.r365 > 0; }), deep = done.filter(function (h) { return h.dd365 <= -10; });
    var days = last ? dnOf(x.date) - dnOf(last.date) : null, ymd = ymdS;
    it.push([_T('賣方衰竭常數', 'Seller exhaustion constant'), fmt.n(x.value, 3),
      _T('2011 年起第 ' + fmt.n(x.pct, 0) + ' 百分位（越低＝價格越平靜、虧損的人越多）；低於 ' + x.th + ' 的日子只佔 ' + fmt.n(x.th_share, 1) + '%。' + (x.value < x.th ? '現在就在極端區內。' : last ? '上次跌破是 ' + ymd(last.date) + '（' + days + ' 天前），之後最低 ' + fmt.n(last.low, 3) + '（' + ymd(last.low_date) + '，價格 ' + fmt.usd(last.low_price) + '）。' : ''),
        fmt.n(x.pct, 0) + 'th percentile since 2011 (lower = calmer price and more holders at a loss); only ' + fmt.n(x.th_share, 1) + '% of days were below ' + x.th + '. ' + (x.value < x.th ? 'It is inside the extreme zone now.' : last ? 'Last break: ' + ymd(last.date) + ' (' + days + ' days ago), bottoming at ' + fmt.n(last.low, 3) + ' (' + ymd(last.low_date) + ', price ' + fmt.usd(last.low_price) + ').' : '')), 'neu']);
    if (rl && last && rl.date > last.low_date) {
      var now = rl.date === x.date, hl = rl.value > last.low, ph = rl.price > last.low_price;
      it.push([_T('近 30 天低點', 'Low of the past 30 days'), fmt.n(rl.value, 3) + ' · ' + fmt.md(rl.date),
        now ? _T('近 30 天最低就是最新一天，還在往下，低點還沒出現。', 'The 30-day low is the latest day; it is still falling, so no low has formed yet.') :
        _T('比 ' + ymd(last.low_date) + ' 的 ' + fmt.n(last.low, 3) + (hl ? ' 高' : ' 更低') + '，當天價格 ' + fmt.usd(rl.price) + (ph ? '，也比當時的 ' + fmt.usd(last.low_price) + ' 高' : '，比當時的 ' + fmt.usd(last.low_price) + ' 低') + '。' + (rl.value < x.th ? '這次也進了極端區。' : '這次沒有回到 ' + x.th + ' 以下。') + (hl ? '跌破之後再出現、但沒有更低的低點，有人當成第二個訊號點；這只是形狀上的比對。' : ''),
          (hl ? 'Higher' : 'Lower') + ' than ' + fmt.n(last.low, 3) + ' on ' + ymd(last.low_date) + '; price that day was ' + fmt.usd(rl.price) + (ph ? ', also above the ' + fmt.usd(last.low_price) + ' of then' : ', below the ' + fmt.usd(last.low_price) + ' of then') + '. ' + (rl.value < x.th ? 'It re-entered the extreme zone.' : 'It did not return below ' + x.th + '.') + (hl ? ' A later low that does not undercut the first is read by some as a second signal; this is only a shape comparison.' : '')), 'neu']);
    }
    if (done.length) {
      var mn = Math.min.apply(null, done.map(function (h) { return h.r365; }));
      it.push([_T('歷次跌破之後', 'After past breaks'), up.length + ' / ' + done.length,
        _T('2011 年起跌破 ' + x.th + ' 共 ' + H.length + ' 次（隔 90 天以上算新的一次）；已滿一年的 ' + done.length + ' 次中，' + up.length + ' 次一年後價格較高（最少 ' + fmt.pct(mn, 0) + '）' + (deep.length ? '，但 ' + deep.length + ' 次在一年內先跌超過 10%（' + deep.map(function (h) { return secYm(h.date) + ' ' + fmt.pct(h.dd365, 0); }).join('、') + '）' : '') + '。次數少，只代表過去，不是買進訊號。',
          'Since 2011 it broke below ' + x.th + ' ' + H.length + ' times (90+ days apart counts as new); of the ' + done.length + ' with a full year since, ' + up.length + ' saw a higher price a year later (smallest ' + fmt.pct(mn, 0) + ')' + (deep.length ? ', but ' + deep.length + ' first fell more than 10% within the year (' + deep.map(function (h) { return secYm(h.date) + ' ' + fmt.pct(h.dd365, 0); }).join(', ') + ')' : '') + '. A small sample of the past, not a buy signal.'), 'neu']);
    }
    return it;
  }
  function secTable() {
    var x = D.onchain.sec, H = (x.hits || []).slice().reverse(), c = function (v) { return v == null ? '<span class="note">' + _T('未滿', 'n/a') + '</span>' : '<span style="color:var(--' + (v >= 0 ? 'up' : 'down') + ')">' + fmt.pct(v, 0) + '</span>'; };
    return '<div class="tbl-wrap" style="margin-top:12px"><table class="tbl"><thead><tr><th>' + _T('跌破日', 'Break date') + '</th><th class="num hide-sm">' + _T('價格', 'Price') + '</th><th class="num hide-sm">' + _T('90 天內最低', 'Low within 90d') + '</th><th class="num hide-sm">90 ' + _T('天', 'd') + '</th><th class="num">180 ' + _T('天', 'd') + '</th><th class="num">365 ' + _T('天', 'd') + '</th><th class="num">' + _T('一年內最大回撤', 'Max drawdown in 1y') + '</th></tr></thead><tbody>' +
      H.map(function (h) { return '<tr><td><span class="num">' + h.date.replace(/-/g, '/') + '</span></td><td class="num hide-sm">' + fmt.usd(h.price) + '</td><td class="num hide-sm">' + fmt.n(h.low, 3) + '</td><td class="num hide-sm">' + c(h.r90) + '</td><td class="num">' + c(h.r180) + '</td><td class="num">' + c(h.r365) + '</td><td class="num">' + (h.done ? c(h.dd365) : c(h.dd365) + '*') + '</td></tr>'; }).join('') + '</tbody></table></div>' + (H.some(function (h) { return !h.done; }) ? '<p class="note">' + _T('* 還不滿一年，算到最新一天。', '* Less than a year so far; measured to the latest day.') + '</p>' : '');
  }
  function secPanel() {
    var x = (D.onchain || {}).sec; if (!x || !x.rows) return '';
    return panel('span-12', _T('賣方衰竭常數', 'Seller exhaustion constant'), _T('CheckOnChain · ' + fmt.md(x.date), 'CheckOnChain · ' + fmt.md(x.date)),
      interpHtml(secSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('賣方衰竭常數', 'Seller exhaustion constant'), 'var(--s1)'], [_T('極端區（低於 ' + x.th + '）', 'Extreme zone (below ' + x.th + ')'), 'var(--down)', 'box']]) + '<div class="chart" id="c-sec"></div>' + secTable() +
      '<p class="note">' + _T('賣方衰竭常數＝獲利供給比例 × 30 天價格波動：價格很平靜、同時很多人在虧損時會很低，代表想賣的人大多已經賣了。資料取自 CheckOnChain 的公開圖表（晚約 1 天）。刻度和 Glassnode 版不同，網路上常見的 0.01 門檻不能套用；這裡的極端區用它自己的歷史分布。',
        'Seller exhaustion constant = percent supply in profit × 30-day price volatility: it is very low when price is calm while many holders are at a loss, a sign that most would-be sellers have already sold. Data from CheckOnChain\'s public chart (about a day behind). Its scale differs from Glassnode\'s, so the 0.01 line often quoted online does not apply; the extreme zone here comes from its own history.') +
      ' <a href="' + 'https://charts.checkonchain.com/btconchain/unrealised/seller_exhaustion_constant_supply/seller_exhaustion_constant_supply_light.html' + '" target="_blank" rel="noopener">' + _T('原圖 ↗', 'Source chart ↗') + '</a></p>');
  }
  function drawSec(el) {
    var x = (D.onchain || {}).sec; if (!x || !el) return;
    var R_ = x.rows, H = x.hits || [], L = Math.log10;
    var sl = L(Math.min(x.th, Math.min.apply(null, R_.map(function (r) { return r[1]; }))) * 0.9), sh = L(Math.max.apply(null, R_.map(function (r) { return r[1]; })) * 1.1);
    twoPane(el, { rows: R_, pi: 2, hp: [110, 140], hs: [150, 200], lr: function (sm) { return sm ? 0 : 16; }, label: _T('賣方衰竭常數（對數刻度）', 'Seller exhaustion constant (log scale)'), aria: _T('BTC 價格與賣方衰竭常數', 'BTC price and seller exhaustion constant'),
      scale: function (C) { return function (v) { return C.ys0 + (1 - (L(v) - sl) / (sh - sl)) * C.hs; }; },
      body: function (C) {
        var yt = C.Ys(x.th), s = '<rect x="' + C.ML + '" y="' + yt.toFixed(1) + '" width="' + C.pw + '" height="' + (C.yb - yt).toFixed(1) + '" fill="var(--down-dim)"/><line x1="' + C.ML + '" x2="' + (C.ML + C.pw) + '" y1="' + yt.toFixed(1) + '" y2="' + yt.toFixed(1) + '" stroke="var(--down)" stroke-dasharray="3 4" stroke-width="1"/>';
        // 2026-11-04：和門檻 0.13 的標籤距離不到 11px 的刻度只畫線不寫字（原本 0.1 和 0.13 疊在一起）
        [0.1, 0.2, 0.5, 1, 2].forEach(function (t) { if (L(t) < sl || L(t) > sh) return; var y = C.Ys(t); s += C.gl(y, Math.abs(y - yt) < 11 ? null : String(t)); });
        s += C.tx(C.ML + C.pw + 8, yt + 3.5, String(x.th)).replace('class="ax"', 'class="ax" fill="var(--down-ink)"');
        s += '<path class="ln" d="M' + R_.map(function (r) { return C.X(r[0]).toFixed(1) + ',' + C.Ys(r[1]).toFixed(1); }).join('L') + '" stroke="var(--s1)" stroke-width="1.5"/>';
        return s;
      },
      over: function (C) {
        var s = '', lx = Infinity;   // 由新到舊標日期，和右邊已標的距離不到 56px 就略過
        H.slice().reverse().forEach(function (h) { var xx = C.X(dnOf(h.low_date)), yy = C.Ys(h.low); s += '<circle cx="' + xx.toFixed(1) + '" cy="' + yy.toFixed(1) + '" r="4" fill="var(--deck)" stroke="var(--down)" stroke-width="2"/>';
          if (!C.sm && lx - xx >= 56) { s += C.tx(Math.min(xx, C.ML + C.pw - 22), C.yb + 13, secYm(h.low_date), 'middle'); lx = xx; } });
        var z = R_[R_.length - 1]; return s + dot1(C.X(z[0]), C.Ys(z[1]), 'var(--s1)');
      },
      tip: function (p, C) { return { dots: dot1(C.X(p[0]), C.Ys(p[1]), 'var(--s1)'), rows: tipRow1('var(--s1)', _T('賣方衰竭常數', 'Seller exhaustion'), fmt.n(p[1], 3)) }; } });
  }


  /* 市場情緒三張（2026-11-09 使用者要求，見 pipeline/sentiment.py）：恐懼貪婪指數全部歷史、散戶關注度（維基百科瀏覽量）、CME 機構持倉（CFTC）。
     都附回測與樣本數；只作讀值、不是買賣訊號 */
  function fgLab(l) { return l === 'Extreme Fear' ? _T('極度恐懼', l) : l === 'Fear' ? _T('恐懼', l) : l === 'Neutral' ? _T('中性', l) : l === 'Greed' ? _T('貪婪', l) : l === 'Extreme Greed' ? _T('極度貪婪', l) : l; }   // alternative.me 的分類
  function epStat(a, b) { return a.n ? a.up + ' / ' + a.n + _T(' 次上漲、中位數 ', ' rose, median ') + fmt.pct(a.med, 1) + _T('（同期任一天 ' + b.up + '% 上漲、中位數 ' + fmt.pct(b.med, 1) + '）', ' (any day: ' + b.up + '% rose, median ' + fmt.pct(b.med, 1) + ')') : '—'; }
  function fngSay() {
    var x = D.flows.fng_hist, it = [];
    it.push([_T('恐懼貪婪指數', 'Fear & Greed'), x.value + ' · ' + fgLab(x.label),
      _T('一週前 ' + x.d7 + '、一個月前 ' + x.d30 + '，30 日平均 ' + fmt.n(x.avg30, 0) + '；落在 ' + ymdS(x.since_first) + ' 以來第 ' + fmt.n(x.pct, 0) + ' 百分位。極度恐懼（≤ ' + x.lo + '）的日子佔 ' + fmt.n(x.share_xf, 0) + '%、極度貪婪（≥ ' + x.hi + '）佔 ' + fmt.n(x.share_xg, 0) + '%。',
        x.d7 + ' a week ago and ' + x.d30 + ' a month ago; 30-day average ' + fmt.n(x.avg30, 0) + '; ' + ord(x.pct) + ' percentile since ' + ymdS(x.since_first) + '. Extreme fear (≤ ' + x.lo + ') covered ' + fmt.n(x.share_xf, 0) + '% of days, extreme greed (≥ ' + x.hi + ') ' + fmt.n(x.share_xg, 0) + '%.'),
      x.zone === 'xf' ? 'warn' : x.zone === 'xg' ? 'warn' : 'neu']);
    if (x.fear.length) it.push([_T('過去極度恐懼之後', 'After past extreme fear'), x.f30.up + ' / ' + x.f30.n,
      _T('跌到 ' + x.lo + ' 以下共 ' + x.fear.length + ' 段（隔 30 天以上算新的一段，最近 ' + ymdS(x.fear[x.fear.length - 1].date) + '）。30 天後：' + epStat(x.f30, x.base30) + '；90 天後：' + epStat(x.f90, x.base90) + '。極度恐懼常出現在急跌的開頭，第一次掉進去不一定是底；樣本少於 30，只當背景。',
        'It fell to ' + x.lo + ' or below in ' + x.fear.length + ' separate stretches (30+ days apart; latest ' + ymdS(x.fear[x.fear.length - 1].date) + '). 30 days later: ' + epStat(x.f30, x.base30) + '; 90 days later: ' + epStat(x.f90, x.base90) + '. Extreme fear often arrives early in a sell-off, so the first dip into it is not necessarily the low; fewer than 30 cases, background only.'), 'neu']);
    if (x.greed.length) it.push([_T('過去極度貪婪之後', 'After past extreme greed'), x.g30.up + ' / ' + x.g30.n,
      _T('升到 ' + x.hi + ' 以上共 ' + x.greed.length + ' 段（最近 ' + ymdS(x.greed[x.greed.length - 1].date) + '）。30 天後：' + epStat(x.g30, x.base30) + '；90 天後：' + epStat(x.g90, x.base90) + '。樣本很少，只當背景。',
        'It rose to ' + x.hi + ' or above in ' + x.greed.length + ' stretches (latest ' + ymdS(x.greed[x.greed.length - 1].date) + '). 30 days later: ' + epStat(x.g30, x.base30) + '; 90 days later: ' + epStat(x.g90, x.base90) + '. Very few cases, background only.'), 'neu']);
    return it;
  }
  function fngPanel() {
    var x = (D.flows || {}).fng_hist; if (!x || !x.rows) return '';
    return panel('span-12', _T('恐懼貪婪指數', 'Fear & Greed Index'), 'alternative.me · ' + _T(x.since_first.slice(0, 4) + ' 起 · ', 'since ' + x.since_first.slice(0, 4) + ' · ') + fmt.md(x.date),
      interpHtml(fngSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('恐懼貪婪指數', 'Fear & Greed'), 'var(--s4)'], [_T('極度恐懼（≤ ' + x.lo + '）', 'Extreme fear (≤ ' + x.lo + ')'), 'var(--down)', 'box'], [_T('極度貪婪（≥ ' + x.hi + '）', 'Extreme greed (≥ ' + x.hi + ')'), 'var(--up)', 'box']]) +
      '<div class="chart" id="c-fng"></div><p class="note">' + _T('alternative.me 的恐懼貪婪指數（0 極度恐懼、100 極度貪婪），由波動、成交量、社群、市值占比、搜尋熱度等合成。情緒是反向參考：過去極度恐懼之後的 30 天，往往還沒止跌。只作讀值。', 'The alternative.me Fear & Greed Index (0 extreme fear, 100 extreme greed), built from volatility, volume, social activity, dominance and search trends. Sentiment is a contrarian reference: in the past, the 30 days after extreme fear often had not yet bottomed. A reading only.') + '</p>');
  }
  function drawFng(el) {
    var x = (D.flows || {}).fng_hist; if (!x || !el) return;
    twoPane(el, { rows: x.rows, pi: 1, hp: [110, 150], hs: [130, 170], label: _T('恐懼貪婪指數', 'Fear & Greed'), aria: _T('BTC 價格與恐懼貪婪指數', 'BTC price and the Fear & Greed Index'),
      scale: function (C) { return function (v) { return C.ys0 + (1 - v / 100) * C.hs; }; },
      body: function (C) {
        var s = '', yl = C.Ys(x.lo), yh = C.Ys(x.hi);
        s += '<rect x="' + C.ML + '" y="' + yl.toFixed(1) + '" width="' + C.pw + '" height="' + (C.yb - yl).toFixed(1) + '" fill="var(--down-dim)"/><rect x="' + C.ML + '" y="' + C.ys0.toFixed(1) + '" width="' + C.pw + '" height="' + (yh - C.ys0).toFixed(1) + '" fill="var(--up-dim)"/>';
        [0, x.lo, 50, x.hi, 100].forEach(function (g) { s += C.gl(C.Ys(g), String(g), g === 50 ? 'base' : 'gl'); });
        return s + '<path class="ln" d="M' + C.rows.map(function (r) { return C.X(r[0]).toFixed(1) + ',' + C.Ys(r[2]).toFixed(1); }).join('L') + '" stroke="var(--s4)" stroke-width="1.3" fill="none"/>';
      },
      over: function (C) { var z = C.rows[C.rows.length - 1]; return dot1(C.X(z[0]), C.Ys(z[2]), 'var(--s4)'); },
      tip: function (p, C) { return { dots: dot1(C.X(p[0]), C.Ys(p[2]), 'var(--s4)'), rows: tipRow1('var(--s4)', _T('恐懼貪婪指數', 'Fear & Greed'), String(p[2])) }; } });
  }
  function wikiSay() {
    var x = D.flows.wiki, it = [], pk = x.peak;
    it.push([_T('散戶關注度（7 日平均）', 'Retail attention (7-day avg)'), '×' + fmt.n(x.ratio, 2),
      _T('英文維基百科「Bitcoin」條目每天約 ' + fmt.n(x.v7) + ' 次瀏覽，是過去一年中位數（' + fmt.n(x.med) + '）的 ' + fmt.n(x.ratio, 2) + ' 倍；一個月前 ' + fmt.n(x.r30, 2) + ' 倍。絕對量落在 2016 年以來第 ' + fmt.n(x.pct, 0) + ' 百分位，只有 ' + ymdS(pk.date) + ' 高峰（每天 ' + fmt.n(pk.v7) + ' 次）的 ' + fmt.n(x.v7 / pk.v7 * 100, 1) + '%。',
        'The English Wikipedia "Bitcoin" article gets about ' + fmt.n(x.v7) + ' views a day, ' + fmt.n(x.ratio, 2) + '× its past-year median (' + fmt.n(x.med) + '); ' + fmt.n(x.r30, 2) + '× a month ago. In absolute terms that is the ' + ord(x.pct) + ' percentile since 2016, only ' + fmt.n(x.v7 / pk.v7 * 100, 1) + '% of the ' + ymdS(pk.date) + ' peak (' + fmt.n(pk.v7) + ' a day).'),
      x.ratio >= x.spike ? 'warn' : 'neu']);
    if (x.spikes.length) it.push([_T('過去暴增之後', 'After past spikes'), x.s30.up + ' / ' + x.s30.n,
      _T('7 日平均到過去一年中位數的 ' + x.spike + ' 倍以上共 ' + x.spikes.length + ' 次（' + x.spikes.map(function (e) { return ymdS(e.date).slice(0, 7) + ' 最高 ×' + fmt.n(e.peak, 1); }).join('、') + '）。30 天後：' + epStat(x.s30, x.base30) + '；90 天後：' + epStat(x.s90, x.base90) + '。新手湧入時暴增，頂部和急跌都會；只有 ' + x.spikes.length + ' 次，只當背景。',
        'The 7-day average reached ' + x.spike + '× its past-year median ' + x.spikes.length + ' times (' + x.spikes.map(function (e) { return ymdS(e.date).slice(0, 7) + ' peak ×' + fmt.n(e.peak, 1); }).join(', ') + '). 30 days later: ' + epStat(x.s30, x.base30) + '; 90 days later: ' + epStat(x.s90, x.base90) + '. It spikes when newcomers pour in, at tops and in crashes alike; only ' + x.spikes.length + ' cases, background only.'), 'neu']);
    return it;
  }
  function wikiPanel() {
    var x = (D.flows || {}).wiki; if (!x || !x.rows) return '';
    return panel('span-12', _T('散戶關注度：維基百科瀏覽量', 'Retail attention: Wikipedia page views'), _T('Wikimedia · 英文版 · ' + fmt.md(x.date), 'Wikimedia · English · ' + fmt.md(x.date)),
      interpHtml(wikiSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('7 日平均 ÷ 過去一年中位數', '7-day avg ÷ past-year median'), 'var(--s1)'], [_T('暴增（≥ ' + x.spike + ' 倍）', 'Spike (≥ ' + x.spike + '×)'), 'var(--down)', 'box']]) +
      '<div class="chart" id="c-wiki"></div><p class="note">' + _T('英文維基百科「Bitcoin」條目每天的瀏覽量（只算真人、不含爬蟲），7 日平均除以自己過去一年的中位數，看關注度是不是突然升溫。大量新手湧入時會暴增（2017 年底、2021 年都是），但只代表有人在查，不分買賣。只作讀值。', 'Daily views of the English Wikipedia "Bitcoin" article (people only, no crawlers), as a 7-day average divided by its own past-year median, to see whether attention is suddenly heating up. It spikes when newcomers flood in (late 2017, 2021), but it only shows people looking things up, not whether they buy or sell. A reading only.') + '</p>');
  }
  function drawWiki(el) {
    var x = (D.flows || {}).wiki; if (!x || !el) return;
    var L = Math.log10;
    twoPane(el, { rows: x.rows, pi: 1, hp: [110, 150], hs: [130, 170], label: _T('7 日平均 ÷ 過去一年中位數（對數刻度）', '7-day avg ÷ past-year median (log scale)'), aria: _T('BTC 價格與維基百科瀏覽量', 'BTC price and Wikipedia page views'),
      scale: function (C) { var v = C.rows.map(function (r) { return r[3]; }), lo = L(Math.min(0.5, Math.min.apply(null, v)) * 0.9), hi = L(Math.max(x.spike * 1.2, Math.max.apply(null, v)) * 1.1); return function (y) { return C.ys0 + (1 - (L(y) - lo) / (hi - lo)) * C.hs; }; },
      body: function (C) {
        var s = '', ys = C.Ys(x.spike);
        s += '<rect x="' + C.ML + '" y="' + C.ys0.toFixed(1) + '" width="' + C.pw + '" height="' + (ys - C.ys0).toFixed(1) + '" fill="var(--down-dim)"/>';
        [0.5, 1, 2, x.spike, 5].forEach(function (g) { var y = C.Ys(g); if (y < C.ys0 - 1 || y > C.yb + 1) return; s += C.gl(y, '×' + g, g === 1 ? 'base' : 'gl'); });
        return s + '<path class="ln" d="M' + C.rows.map(function (r) { return C.X(r[0]).toFixed(1) + ',' + C.Ys(r[3]).toFixed(1); }).join('L') + '" stroke="var(--s1)" stroke-width="1.3" fill="none"/>';
      },
      over: function (C) { var z = C.rows[C.rows.length - 1]; return dot1(C.X(z[0]), C.Ys(z[3]), 'var(--s1)'); },
      tip: function (p, C) { return { dots: dot1(C.X(p[0]), C.Ys(p[3]), 'var(--s1)'), rows: tipRow1('var(--s1)', _T('倍數', 'Multiple'), '×' + fmt.n(p[3], 2)) + tipRow1('var(--ink-3)', _T('每日瀏覽（7 日平均）', 'Daily views (7-day avg)'), fmt.n(p[2])) }; } });
  }
  function cotSay() {
    var x = D.flows.cot, it = [], k = function (v) { return (v > 0 ? '+' : v < 0 ? '−' : '') + fmt.n(Math.abs(v)) + _T(' 顆', ' BTC'); };
    it.push([_T('槓桿基金淨部位', 'Leveraged funds, net'), k(x.lev),
      _T((x.lev < 0 ? '淨空 ' : '淨多 ') + fmt.n(Math.abs(x.lev)) + ' 顆（' + fmt.md(x.date) + ' 持倉），4 週前比 ' + k(x.lev4) + '；空單佔全部未平倉 ' + fmt.n(x.lev_short_share, 0) + '%。槓桿基金的空單多半是基差交易（買現貨或 ETF、放空期貨賺價差），淨空擴大常代表套利資金進場，不等於看空；淨空縮小則可能是套利資金撤出。2018 年以來最空是 ' + ymdS(x.lev_min.date) + '（' + k(x.lev_min.v) + '）。',
        (x.lev < 0 ? 'Net short ' : 'Net long ') + fmt.n(Math.abs(x.lev)) + ' BTC (positions as of ' + fmt.md(x.date) + '), ' + k(x.lev4) + ' versus four weeks earlier; their shorts are ' + fmt.n(x.lev_short_share, 0) + '% of all open interest. Much of the leveraged-fund short is basis trading (long spot or ETFs, short futures for the spread), so a bigger net short often means arbitrage money coming in rather than a bearish bet, and a smaller one may mean it is leaving. The most short since 2018 was ' + ymdS(x.lev_min.date) + ' (' + k(x.lev_min.v) + ').'), 'neu']);
    it.push([_T('資產管理機構淨部位', 'Asset managers, net'), k(x.am),
      _T((x.am >= 0 ? '淨多 ' : '淨空 ') + fmt.n(Math.abs(x.am)) + ' 顆，4 週前比 ' + k(x.am4) + '；2018 年以來第 ' + fmt.n(x.am_pct, 0) + ' 百分位，最多是 ' + ymdS(x.am_max.date) + '（' + k(x.am_max.v) + '）。資產管理機構（基金、退休金、ETF 發行商）較少做套利，淨多比較接近真的看多。',
        (x.am >= 0 ? 'Net long ' : 'Net short ') + fmt.n(Math.abs(x.am)) + ' BTC, ' + k(x.am4) + ' versus four weeks earlier; ' + ord(x.am_pct) + ' percentile since 2018, peaking on ' + ymdS(x.am_max.date) + ' (' + k(x.am_max.v) + '). Asset managers (funds, pensions, ETF issuers) do less arbitrage, so their net long is closer to a genuine bullish position.'), 'neu']);   // 淨多但 4 週減少時掛「偏空」容易誤會，增減交給文字
    it.push([_T('CME 未平倉', 'CME open interest'), fmt.n(x.oi) + _T(' 顆', ' BTC'),
      _T('一年前比 ' + fmt.pct(x.oi52, 0) + '。未平倉縮小代表機構在 CME 的部位整體變少（套利價差變小時常見）。', fmt.pct(x.oi52, 0) + ' versus a year ago. Shrinking open interest means institutions hold less on CME overall (common when the basis narrows).'), 'neu']);
    return it;
  }
  function cotPanel() {
    var x = (D.flows || {}).cot; if (!x || !x.rows) return '';
    return panel('span-12', _T('CME 機構持倉', 'CME institutional positioning'), _T('CFTC · 每週 · ' + fmt.md(x.date) + ' 持倉', 'CFTC · weekly · positions as of ' + fmt.md(x.date)),
      interpHtml(cotSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('槓桿基金淨部位', 'Leveraged funds, net'), 'var(--s1)'], [_T('資產管理機構淨部位', 'Asset managers, net'), 'var(--s3)']]) +
      '<div class="chart" id="c-cot"></div><p class="note">' + _T('CFTC 每週的金融期貨交易者持倉報告（Traders in Financial Futures），CME 比特幣期貨（每口 5 顆）。淨部位＝多單 − 空單，換算成顆。週二的持倉、週五公布，所以最新一筆通常晚 3–10 天。槓桿基金的空單很大一部分是基差交易，不能直接當成看空。只作讀值。', 'CFTC\'s weekly Traders in Financial Futures report for CME bitcoin futures (5 BTC per contract). Net position = longs − shorts, in BTC. Positions are as of Tuesday and published on Friday, so the latest point is usually 3–10 days old. Much of the leveraged-fund short is basis trading and should not be read as bearish on its own. A reading only.') + '</p>');
  }
  function drawCot(el) {
    var x = (D.flows || {}).cot; if (!x || !el) return;
    var R0 = x.rows.filter(function (r) { return r[1]; });
    twoPane(el, { rows: R0, pi: 1, hp: [110, 150], hs: [140, 180], label: _T('淨部位（顆）', 'Net position (BTC)'), aria: _T('BTC 價格與 CME 機構淨部位', 'BTC price and CME institutional net positions'),
      scale: function (C) { var v = []; C.rows.forEach(function (r) { v.push(r[2], r[3]); }); var lo = Math.min(0, Math.min.apply(null, v)), hi = Math.max(0, Math.max.apply(null, v)), pd = (hi - lo) * 0.08 || 1; lo -= pd; hi += pd; C.cLo = lo; C.cHi = hi; return function (y) { return C.ys0 + (1 - (y - lo) / (hi - lo)) * C.hs; }; },
      body: function (C) {
        var s = '', st = niceStep(C.cHi - C.cLo, C.sm ? 3 : 4);
        for (var g = Math.ceil(C.cLo / st) * st; g <= C.cHi + 1e-9; g += st) s += C.gl(C.Ys(g), (g > 0 ? '+' : '') + fmt.k(g), Math.abs(g) < 1e-9 ? 'base' : 'gl');
        var ln = function (k, c) { return '<path class="ln" d="M' + C.rows.map(function (r) { return C.X(r[0]).toFixed(1) + ',' + C.Ys(r[k]).toFixed(1); }).join('L') + '" stroke="' + c + '" stroke-width="1.5" fill="none"/>'; };
        return s + ln(2, 'var(--s1)') + ln(3, 'var(--s3)');
      },
      over: function (C) { var z = C.rows[C.rows.length - 1]; return dot1(C.X(z[0]), C.Ys(z[2]), 'var(--s1)') + dot1(C.X(z[0]), C.Ys(z[3]), 'var(--s3)'); },
      tip: function (p, C) { return { t: _T('週二 ', 'Tuesday ') + fmt.date(p[0]), dots: dot1(C.X(p[0]), C.Ys(p[2]), 'var(--s1)') + dot1(C.X(p[0]), C.Ys(p[3]), 'var(--s3)'),
        rows: tipRow1('var(--s1)', _T('槓桿基金', 'Leveraged funds'), (p[2] > 0 ? '+' : '') + fmt.n(p[2])) + tipRow1('var(--s3)', _T('資產管理機構', 'Asset managers'), (p[3] > 0 ? '+' : '') + fmt.n(p[3])) + tipRow1('var(--ink-3)', _T('未平倉', 'Open interest'), fmt.n(p[4])) }; } });
  }

  /* 對趨勢的信心（2026-11-09 使用者要求；做法參考 Glassnode 週報 2023 第 38 週，資料 Bitview，見 pipeline/bv_extra.conf_viz）：
     （短期持有者賣出的幣的 7 日平均成本 − 短期持有者成本）÷ 收盤。≥ +0.05 綠（賣的人成本比持有者高：新買家在高位也願意接、願意抱）、
     ≤ −0.05 紅（成本低的人也在賣：認賠、恐慌），中間是轉換期。上格價格加兩條成本線，下格指標。只作讀值；產品內不寫付費指標的名字 */
  function confWord(b) { return b === 'pos' ? _T('偏有信心', 'confident') : b === 'neg' ? _T('信心不足', 'lacking confidence') : _T('轉換期', 'in transition'); }
  function confSay() {
    var x = D.onchain.sthconf, it = [], sg = function (v) { return (v > 0 ? '+' : v < 0 ? '−' : '') + fmt.n(Math.abs(v), 3); }, ymd = ymdS;
    var gap = fmt.pct((x.spend / x.hold - 1) * 100, 1);
    it.push([_T('對趨勢的信心', 'Confidence in the trend'), sg(x.value),
      _T(confWord(x.band) + '（' + ymd(x.since) + ' 起，第 ' + x.days + ' 天）；一週前 ' + sg(x.d7) + '。短期持有者這 7 天賣出的幣平均成本 ' + fmt.usd(x.spend) + '，比還在持有的人的成本 ' + fmt.usd(x.hold) + ' ' + (x.spend >= x.hold ? '高 ' : '低 ') + gap.replace(/^[+-]/, '') + '。±' + x.nb + ' 之間是轉換期，方向還不明確。',
        'Currently ' + confWord(x.band) + ' (since ' + ymd(x.since) + ', day ' + x.days + '); ' + sg(x.d7) + ' a week ago. Coins short-term holders sold over 7 days cost ' + fmt.usd(x.spend) + ' on average, ' + gap.replace(/^[+-]/, '') + (x.spend >= x.hold ? ' above' : ' below') + ' the ' + fmt.usd(x.hold) + ' cost of those still holding. Between ±' + x.nb + ' is a transition zone with no clear direction.'),
      x.band === 'pos' ? 'pos' : x.band === 'neg' ? 'neg' : 'neu']);
    var st = function (a, b) { return a.n ? a.up + ' / ' + a.n + _T(' 次上漲、中位數 ', ' rose, median ') + fmt.pct(a.med, 1) + _T('（同期任一天 ' + b.up + '% 上漲、中位數 ' + fmt.pct(b.med, 1) + '）', ' (any day: ' + b.up + '% rose, median ' + fmt.pct(b.med, 1) + ')') : '—'; };
    if (x.ups && x.ups.length) it.push([_T('過去轉正之後', 'After past turns positive'), x.up90.up + ' / ' + x.up90.n,
      _T('由 −' + x.nb + ' 以下轉到 +' + x.nb + ' 以上共 ' + x.ups.length + ' 次（最近 ' + ymd(x.ups[x.ups.length - 1].date) + '）。30 天後：' + st(x.up30, x.base30) + '；90 天後：' + st(x.up90, x.base90) + '。樣本少於 30，只當背景。',
        'It went from below −' + x.nb + ' to above +' + x.nb + ' ' + x.ups.length + ' times (latest ' + ymd(x.ups[x.ups.length - 1].date) + '). 30 days later: ' + st(x.up30, x.base30) + '; 90 days later: ' + st(x.up90, x.base90) + '. Fewer than 30 cases, so background only.'), 'neu']);
    if (x.downs && x.downs.length) it.push([_T('過去轉負之後', 'After past turns negative'), x.dn90.up + ' / ' + x.dn90.n,
      _T('由 +' + x.nb + ' 以上轉到 −' + x.nb + ' 以下共 ' + x.downs.length + ' 次（最近 ' + ymd(x.downs[x.downs.length - 1].date) + '）。30 天後：' + st(x.dn30, x.base30) + '；90 天後：' + st(x.dn90, x.base90) + '。轉負之後不一定續跌，常是大跌後的洗盤。',
        'It went from above +' + x.nb + ' to below −' + x.nb + ' ' + x.downs.length + ' times (latest ' + ymd(x.downs[x.downs.length - 1].date) + '). 30 days later: ' + st(x.dn30, x.base30) + '; 90 days later: ' + st(x.dn90, x.base90) + '. A turn negative does not reliably mean further falls; it often marks a shake-out after a drop.'), 'neu']);
    return it;
  }
  function confPanel() {
    var x = (D.onchain || {}).sthconf; if (!x || !x.rows) return '';
    return panel('span-12', _T('對趨勢的信心（短期持有者）', 'Confidence in the trend (short-term holders)'), _T('Bitview · 7 日平均 · ' + fmt.md(x.date), 'Bitview · 7-day average · ' + fmt.md(x.date)),
      interpHtml(confSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('賣出的人的成本', 'Cost of coins sold'), 'var(--s1)'], [_T('還在持有的人的成本', 'Cost of coins still held'), 'var(--s2)'],
        [_T('偏有信心（≥ +' + x.nb + '）', 'Confident (≥ +' + x.nb + ')'), 'var(--up)', 'box'], [_T('信心不足（≤ −' + x.nb + '）', 'Lacking confidence (≤ −' + x.nb + ')'), 'var(--down)', 'box'], [_T('轉換期', 'Transition'), 'var(--warn)', 'box']]) +
      '<div class="chart" id="c-conf"></div><p class="note">' + _T('對趨勢的信心＝（短期持有者這 7 天賣出的幣的平均成本 − 短期持有者成本）÷ 收盤。賣的人成本比還在持有的人高，代表最近才在高位買進的人沒有急著賣、賣出的多是成本更高的籌碼，市場還願意接；反過來，成本低的人也開始賣，就是認賠或恐慌。做法參考 Glassnode 週報（2023 年第 38 週，±0.05 的轉換帶沿用原文、原文也說是任意訂的），資料取自 Bitview（逐筆 UTXO、晚 1 天、未做實體調整）。只作讀值，不是買賣訊號。',
        'Confidence in the trend = (average cost of coins short-term holders sold over 7 days − short-term holder cost) ÷ close. When sellers\' cost is above holders\', recent high buyers are not rushing out and the market is still absorbing supply; when low-cost coins start selling too, it is loss-taking or panic. Method after Glassnode\'s weekly report (2023 week 38; the ±0.05 transition band is from the original, which calls it arbitrary); data from Bitview (UTXO-level, one day behind, not entity-adjusted). A reading, not a trade signal.') + '</p>');
  }
  function drawConf(el) {
    var x = (D.onchain || {}).sthconf; if (!x || !el) return;
    var nb = x.nb, col = function (v) { return v >= nb ? 'var(--up)' : v <= -nb ? 'var(--down)' : 'var(--warn)'; };
    twoPane(el, { rows: x.rows, pi: 1, hp: [120, 160], hs: [130, 170], label: _T('對趨勢的信心（7 日）', 'Confidence in the trend (7-day)'), aria: _T('BTC 價格、短期持有者賣出與持有成本、對趨勢的信心', 'BTC price, cost of coins short-term holders sold and held, and confidence in the trend'),
      scale: function (C) {
        var v = C.rows.map(function (r) { return r[4]; }), lo = Math.min(-0.15, Math.min.apply(null, v)), hi = Math.max(0.15, Math.max.apply(null, v)), pd = (hi - lo) * 0.06; lo -= pd; hi += pd;
        C.cLo = lo; C.cHi = hi; return function (y) { return C.ys0 + (1 - (y - lo) / (hi - lo)) * C.hs; };
      },
      body: function (C) {
        var s = '', st = niceStep(C.cHi - C.cLo, C.sm ? 3 : 4), z0 = C.Ys(0);
        for (var g = Math.ceil(C.cLo / st) * st; g <= C.cHi + 1e-9; g += st) { var gv = +g.toFixed(6); s += C.gl(C.Ys(gv), (gv > 0 ? '+' : '') + fmt.n(gv, 2), gv ? 'gl' : 'base'); }
        var ya = C.Ys(nb), yb = C.Ys(-nb); s += '<rect x="' + C.ML + '" y="' + ya.toFixed(1) + '" width="' + C.pw + '" height="' + (yb - ya).toFixed(1) + '" fill="var(--warn-dim)"/>';
        var R_ = C.rows, bw = Math.max(1, C.pw / R_.length + 0.4);
        R_.forEach(function (r) { var cx = C.X(r[0]), yv = C.Ys(r[4]); s += '<rect x="' + (cx - bw / 2).toFixed(1) + '" y="' + Math.min(z0, yv).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(0.5, Math.abs(yv - z0)).toFixed(1) + '" fill="' + col(r[4]) + '"/>'; });
        return s;
      },
      over: function (C) {   // 上格兩條成本線（價格的對數刻度）
        var ln = function (k, c) { return '<path class="ln" d="M' + C.rows.filter(function (r) { return r[k] > 0; }).map(function (r) { return C.X(r[0]).toFixed(1) + ',' + C.Yp(r[k]).toFixed(1); }).join('L') + '" stroke="' + c + '" stroke-width="1.4" fill="none"/>'; };
        var z = C.rows[C.rows.length - 1];
        return ln(2, 'var(--s1)') + ln(3, 'var(--s2)') + dot1(C.X(z[0]), C.Ys(z[4]), col(z[4]));
      },
      tip: function (p, C) {
        return { dots: dot1(C.X(p[0]), C.Ys(p[4]), col(p[4])) + dot1(C.X(p[0]), C.Yp(p[2]), 'var(--s1)') + dot1(C.X(p[0]), C.Yp(p[3]), 'var(--s2)'),
          rows: tipRow1(col(p[4]), _T('對趨勢的信心', 'Confidence'), (p[4] > 0 ? '+' : '') + fmt.n(p[4], 3)) +   // 狀態看顏色（圖例旁也會顯示這個數字，不再重複寫「轉換期」）
            tipRow1('var(--s1)', _T('賣出的人的成本', 'Cost of coins sold'), fmt.usd(p[2])) + tipRow1('var(--s2)', _T('還在持有的人的成本', 'Cost of coins still held'), fmt.usd(p[3])) };
      } });
  }

  /* 實現獲利 ÷ 實現虧損（90 天平均；2026-11-02 使用者要求，Realized P/L 比率；資料取自 CheckOnChain）：
     1 以上綠、以下紅。上下兩格共用時間軸，不疊成雙 y 軸。只作讀值 */
  function rplSay() {
    var x = D.onchain.rpl, it = [], R = x.reds || [], ymd = ymdS;
    var maj = R.filter(function (y) { return y.major; }), lastMaj = maj[maj.length - 1];
    it.push([_T('90 天平均', '90-day average'), fmt.n(x.value, 2),
      x.above ? _T('獲利了結多於認賠。' + ymd(x.since) + ' 回到 1 以上（' + x.since_days + ' 天前）' + (x.first2 ? '，' + ymd(x.first2) + ' 超過 2' : '') + '。' + (lastMaj && !lastMaj.open ? '上一段紅色是 ' + ymd(lastMaj.start) + '–' + ymd(lastMaj.end) + '（' + lastMaj.days + ' 天，最低 ' + fmt.n(lastMaj.low, 2) + '）。' : ''),
        'Profit-taking outweighs loss-taking. Back above 1 on ' + ymd(x.since) + ' (' + x.since_days + ' days ago)' + (x.first2 ? ', above 2 since ' + ymd(x.first2) : '') + '. ' + (lastMaj && !lastMaj.open ? 'The last red stretch ran ' + ymd(lastMaj.start) + '–' + ymd(lastMaj.end) + ' (' + lastMaj.days + ' days, low ' + fmt.n(lastMaj.low, 2) + ').' : '')) :
        _T('認賠多於獲利（紅色），' + ymd(x.since) + ' 起已 ' + x.since_days + ' 天。', 'Loss-taking outweighs profit-taking (red) for ' + x.since_days + ' days since ' + ymd(x.since) + '.'), 'neu']);
    var p = x.proj;
    it.push([_T('最近 7 天（每日）', 'Last 7 days (daily)'), fmt.n(x.last7, 2),
      _T('每日比值 7 天平均 ' + fmt.n(x.last7, 2) + '：' + (x.last7 >= 1 ? '獲利了結仍多於認賠' : '認賠多於獲利') + '。90 天平均反應慢，' + (p ? '如果之後每天都維持這個水準，約 ' + ymd(p.date) + '（' + p.days + ' 天後）會' + (x.above ? '跌回 1 以下' : '回到 1 以上') + '；' : '維持這個水準不會' + (x.above ? '跌回 1 以下' : '回到 1 以上') + '；') + '每日比值是早一步的訊號。',
        'Daily ratio averages ' + fmt.n(x.last7, 2) + ' over 7 days: ' + (x.last7 >= 1 ? 'profit-taking still leads' : 'loss-taking leads') + '. The 90-day average is slow; ' + (p ? 'if daily values stay here it would ' + (x.above ? 'drop below' : 'rise above') + ' 1 around ' + ymd(p.date) + ' (in ' + p.days + ' days)' : 'at this level it would not ' + (x.above ? 'drop below' : 'rise above') + ' 1') + '; the daily ratio is the earlier warning.'), x.last7 >= 1 ? 'neu' : 'warn']);
    var done = maj.filter(function (y) { return y.relapse && (y !== lastMaj || x.since_days >= 365); });
    if (done.length) {
      var clean = done.filter(function (y) { return !y.relapse.length; });
      it.push([_T('紅色結束之後', 'After red stretches'), _T(clean.length + ' / ' + done.length + ' 沒再跌破', clean.length + ' / ' + done.length + ' held'),
        _T('2011 年起 60 天以上的紅色期間結束後一年內：' + done.map(function (y) { return secYm(y.end) + (y.relapse.length ? ' 之後 ' + y.relapse.map(function (z) { return secYm(z.start) + ' 又跌回 ' + z.days + ' 天（最低 ' + fmt.n(z.low, 2) + '）'; }).join('、') : ' 之後沒再跌破'); }).join('；') + '。' + (lastMaj && !lastMaj.open && x.since_days < 365 ? '這次（' + secYm(lastMaj.end) + ' 結束）還在觀察期。' : '') + '只代表過去。',
          'Within a year after each red stretch of 60+ days since 2011: ' + done.map(function (y) { return secYm(y.end) + (y.relapse.length ? ' was followed by ' + y.relapse.map(function (z) { return secYm(z.start) + ' back below for ' + z.days + ' days (low ' + fmt.n(z.low, 2) + ')'; }).join(', ') : ' held above'); }).join('; ') + '. ' + (lastMaj && !lastMaj.open && x.since_days < 365 ? 'The latest (ended ' + secYm(lastMaj.end) + ') is still within that year. ' : '') + 'The past only.'), 'neu']);
    }
    return it;
  }
  function rplTable() {
    var x = D.onchain.rpl, R = (x.reds || []).slice().reverse(), ymd = ymdS;
    return '<div class="tbl-wrap" style="margin-top:12px"><table class="tbl"><thead><tr><th>' + _T('低於 1 的期間', 'Below 1') + '</th><th class="num">' + _T('天數', 'Days') + '</th><th class="num">' + _T('最低', 'Low') + '</th><th class="num hide-sm">' + _T('最低時價格', 'Price at low') + '</th><th class="num">' + _T('結束後一年', '1y after end') + '</th></tr></thead><tbody>' +
      R.map(function (y) { var v = y.r365; return '<tr><td><span class="num">' + secYm(y.start) + '–' + (y.open ? _T('至今', 'now') : secYm(y.end).slice(2)) + '</span>' + (y.major ? '' : ' <span class="note">' + _T('短', 'brief') + '</span>') + '</td><td class="num">' + y.days + '</td><td class="num">' + fmt.n(y.low, 2) + '</td><td class="num hide-sm">' + fmt.usd(y.low_price) + '</td><td class="num">' + (v == null ? '<span class="note">' + _T('未滿', 'n/a') + '</span>' : '<span style="color:var(--' + (v >= 0 ? 'up' : 'down') + ')">' + fmt.pct(v, 0) + '</span>') + '</td></tr>'; }).join('') + '</tbody></table></div>';
  }
  function rplPanel() {
    var x = (D.onchain || {}).rpl; if (!x || !x.rows) return '';
    return panel('span-12', _T('實現獲利 ÷ 實現虧損（90 天平均）', 'Realized profit ÷ realized loss (90-day avg)'), _T('CheckOnChain · ' + fmt.md(x.date), 'CheckOnChain · ' + fmt.md(x.date)),
      interpHtml(rplSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('1 以上（獲利了結較多）', 'Above 1 (more profit-taking)'), 'var(--up)'], [_T('1 以下（認賠較多）', 'Below 1 (more loss-taking)'), 'var(--down)']]) + '<div class="chart" id="c-rpl"></div>' + rplTable() +
      '<p class="note">' + _T('全網每天賣出的幣，賺錢的那部分加起來 ÷ 賠錢的那部分加起來，再取 90 天平均（和網路上常見的 Glassnode 圖同做法，數值接近但不完全相同）。資料取自 CheckOnChain 的公開圖表（晚約 1 天）。',
        'Each day, the total profit realized by coins sold at a gain ÷ the total loss realized by coins sold at a loss, averaged over 90 days (the same method as the Glassnode chart often shared online; values are close but not identical). Data from CheckOnChain\'s public chart (about a day behind).') +
      ' <a href="https://charts.checkonchain.com/btconchain/realised/realisedpnl_ratio_all/realisedpnl_ratio_all_light.html" target="_blank" rel="noopener">' + _T('原圖 ↗', 'Source chart ↗') + '</a></p>');
  }
  function drawRpl(el) {
    var x = (D.onchain || {}).rpl; if (!x || !el) return;
    var R_ = x.rows, L = Math.log10, col = function (v) { return 'var(--' + (v >= 1 ? 'up' : 'down') + ')'; };
    var sl = L(Math.min.apply(null, R_.map(function (r) { return r[1]; })) * 0.85), sh = L(Math.max.apply(null, R_.map(function (r) { return r[1]; })) * 1.15);
    twoPane(el, { rows: R_, pi: 2, hp: [110, 140], hs: [150, 200], label: _T('實現獲利 ÷ 實現虧損，90 天平均（對數刻度）', 'Realized profit ÷ loss, 90-day avg (log scale)'), aria: _T('BTC 價格與實現獲利 ÷ 實現虧損', 'BTC price and realized profit ÷ loss'),
      scale: function (C) { return function (v) { return C.ys0 + (1 - (L(v) - sl) / (sh - sl)) * C.hs; }; },
      body: function (C) {
        var s = '', y1 = C.Ys(1);
        (x.reds || []).forEach(function (y) { var a = Math.max(C.ML, C.X(dnOf(y.start))), b = C.X(dnOf(y.end)); if (b < C.ML) return; s += '<rect x="' + a.toFixed(1) + '" y="' + y1.toFixed(1) + '" width="' + Math.max(1, b - a).toFixed(1) + '" height="' + (C.yb - y1).toFixed(1) + '" fill="var(--down-dim)"/>'; });
        [0.2, 0.5, 2, 5, 10, 20, 50].forEach(function (t) { if (L(t) < sl || L(t) > sh) return; s += C.gl(C.Ys(t), String(t)); });
        s += '<line x1="' + C.ML + '" x2="' + (C.ML + C.pw) + '" y1="' + y1.toFixed(1) + '" y2="' + y1.toFixed(1) + '" stroke="var(--ink-2)" stroke-width="1"/>' + C.tx(C.ML + C.pw + 8, y1 + 3.5, '1');
        var cur = null, pts = [];   // 1 以上綠、以下紅：顏色一換就斷開，換色點兩段共用
        var flush = function () { if (pts.length > 1) s += '<path d="M' + pts.join('L') + '" fill="none" stroke="' + col(cur ? 1 : 0) + '" stroke-width="1.6" stroke-linejoin="round"/>'; };
        R_.forEach(function (r) { var up = r[1] >= 1, pt = C.X(r[0]).toFixed(1) + ',' + C.Ys(r[1]).toFixed(1); if (up !== cur) { flush(); pts = pts.length ? [pts[pts.length - 1]] : []; cur = up; } pts.push(pt); });
        flush();
        return s;
      },
      over: function (C) { var z = R_[R_.length - 1]; return dot1(C.X(z[0]), C.Ys(z[1]), col(z[1])); },
      tip: function (p, C) { return { dots: dot1(C.X(p[0]), C.Ys(p[1]), col(p[1])), rows: tipRow1(col(p[1]), _T('獲利 ÷ 虧損（90 天）', 'Profit ÷ loss (90d)'), fmt.n(p[1], 2)) }; } });
  }


  /* 表觀需求（2026-11-03 使用者要求，CryptoQuant 的 Apparent Demand）：30 天新挖出的幣 − 30 天內 1 年以上未動供給的變化。
     資料取自 CheckOnChain HODL Waves（逐筆 UTXO）；單日大量舊幣搬動標「疑似搬家」，一年後的回音預先提醒。上下兩格共用時間軸。只作讀值 */
  function adK(v) { var a = Math.abs(v); return (v > 0 ? '+' : v < 0 ? '−' : '') + (a < 1e4 ? _T(fmt.n(a) + ' 顆', fmt.n(a) + ' BTC') : cohCoins(a)); }
  function adSay() {
    var x = D.onchain.ad, it = [], ymd = ymdS, below = x.value < x.sma30, M = x.moves || [];
    it.push([_T('表觀需求（30 天）', 'Apparent demand (30d)'), adK(x.value),
      _T((x.value >= 0 ? '正：' : '負：') + '30 天新挖出 ' + cohCoins(x.issued30) + '，1 年以上沒動的幣卻' + (x.inact_chg30 >= 0 ? '多了 ' : '少了 ') + cohCoins(Math.abs(x.inact_chg30)) + '。' + (below ? '低於自己的 30 日平均（' + adK(x.sma30) + '）' : '高於自己的 30 日平均（' + adK(x.sma30) + '）') + (x.d7 != null ? '，一週前 ' + adK(x.d7) : '') + '；2020 年以來第 ' + fmt.n(x.pct, 0) + ' 百分位。',
        (x.value >= 0 ? 'Positive: ' : 'Negative: ') + cohCoins(x.issued30) + ' mined in 30 days while coins unmoved for 1y+ ' + (x.inact_chg30 >= 0 ? 'grew by ' : 'fell by ') + cohCoins(Math.abs(x.inact_chg30)) + '. ' + (below ? 'Below' : 'Above') + ' its 30-day average (' + adK(x.sma30) + ')' + (x.d7 != null ? '; a week ago ' + adK(x.d7) : '') + '; ' + fmt.n(x.pct, 0) + 'th percentile since 2020.'), x.value < 0 && below ? 'warn' : 'neu']);
    it.push([_T('怎麼變負的', 'Why negative'), _T('一年前換手', 'Aging'),
      _T('這個數字扣掉的是「滿一年還沒動的幣」：一年前大量換手的籌碼只要沒再動，滿一年時就會把它拉低，不全是今天的買盤變弱。現在扣掉的是一年前（' + ymd(ds_(dnOf(x.date) - 395)) + '–' + ymd(ds_(dnOf(x.date) - 365)) + '）換手、到現在還沒動的幣。',
        'It subtracts coins reaching one year unmoved: heavy turnover a year ago drags it down as those coins age, so it is not all weaker buying today. Right now it is subtracting coins that changed hands ' + ymd(ds_(dnOf(x.date) - 395)) + '–' + ymd(ds_(dnOf(x.date) - 365)) + ' and have not moved since.'), 'neu']);
    var y = x.y1;   // 2026-11-05 1 年版（365 天合計）
    if (y) {
      var cb = y.combo || {}, now2 = x.value < 0 && y.value > 0, cmp = cb.up90_pct == null ? '' : cb.up90_pct < cb.all_up90_pct - 3 ? _T('比所有日子（', 'worse than all days (') : cb.up90_pct > cb.all_up90_pct + 3 ? _T('比所有日子（', 'better than all days (') : _T('和所有日子（', 'about the same as all days (');
      var cmpEnd = cb.up90_pct == null ? '' : cb.up90_pct < cb.all_up90_pct - 3 ? _T('）差', ')') : cb.up90_pct > cb.all_up90_pct + 3 ? _T('）好', ')') : _T('）差不多', ')');
      it.push([_T('表觀需求（1 年）', 'Apparent demand (1y)'), adK(y.value),
        _T('365 天新挖出 ' + cohCoins(y.issued) + '，1 年以上沒動的幣' + (y.inact_chg >= 0 ? '多了 ' : '少了 ') + cohCoins(Math.abs(y.inact_chg)) + '；2020 年以來第 ' + fmt.n(y.pct, 0) + ' 百分位。' +
          (cb.days ? (now2 ? '現在是「30 天負、1 年正」，常被說成牛市中的回調；' : '「30 天負、1 年正」常被說成牛市中的回調（現在不是：30 天' + (x.value >= 0 ? '正' : '負') + '、1 年' + (y.value >= 0 ? '正' : '負') + '）；') +
            '2016 年以來這種組合 ' + cb.days + ' 天，之後 90 天上漲的占 ' + cb.up90_pct + '%（中位 ' + fmt.pct(cb.med90, 1) + '），' + cmp + cb.all_up90_pct + '%、中位 ' + fmt.pct(cb.all_med90, 1) + cmpEnd + '。' : ''),
          cohCoins(y.issued) + ' mined in 365 days while coins unmoved for 1y+ ' + (y.inact_chg >= 0 ? 'grew by ' : 'fell by ') + cohCoins(Math.abs(y.inact_chg)) + '; ' + fmt.n(y.pct, 0) + 'th percentile since 2020. ' +
          (cb.days ? (now2 ? 'Right now 30d is negative and 1y positive, often read as a bull-market pullback; ' : '“30d negative, 1y positive” is often read as a bull-market pullback (not now: 30d ' + (x.value >= 0 ? 'positive' : 'negative') + ', 1y ' + (y.value >= 0 ? 'positive' : 'negative') + '); ') +
            'since 2016 that combination lasted ' + cb.days + ' days and price was higher 90 days later ' + cb.up90_pct + '% of the time (median ' + fmt.pct(cb.med90, 1) + '), ' + cmp + cb.all_up90_pct + '%, median ' + fmt.pct(cb.all_med90, 1) + cmpEnd + '.' : '')), 'neu']);
    }
    var vy = (x.y1 || {}).value, adView = null;
    if (vy != null) {
      if (x.value < 0 && vy < 0) adView = viewRow(_T('需求偏弱', 'Weak demand'),
        _T('30 天和 1 年都是負的：舊幣醒來被市場接走的量，追不上滿一年沒動的幣增加的速度——換手少、新買盤不積極。30 天版有一部分是一年前頂部附近換手的回音，可能誇大了弱勢；但 1 年版也是負的，所以需求偏弱不只是回音。',
          'Both the 30-day and 1-year readings are negative: old coins waking up and being absorbed do not keep pace with coins ageing past one year, so there is little turnover and new buying is not aggressive. Part of the 30-day figure is an echo of heavy turnover near last year\'s top and may overstate the weakness, but the 1-year reading is negative too, so it is not only an echo. '),
        _T('30 天版回到正值，或回到自己的 30 日平均之上。', 'the 30-day reading turning positive, or back above its own 30-day average.'), 'warn');
      else if (x.value > 0 && vy > 0) adView = viewRow(_T('需求在吸收供給', 'Demand absorbing supply'),
        _T('30 天和 1 年都是正的：舊幣醒來被市場接走，需求追得上供給。',
          'Both readings are positive: old coins are waking and being absorbed, and demand keeps up with supply. '),
        _T('30 天版轉負。', 'the 30-day reading turning negative.'), 'pos');
      else adView = viewRow(_T('分歧', 'Mixed'),
        _T('30 天' + (x.value >= 0 ? '正' : '負') + '、1 年' + (vy >= 0 ? '正' : '負') + '：短期和長期方向不一致。常聽到「30 天負、1 年正＝牛市回調」，但 2016 年以來這種組合之後 90 天的表現比平均差，所以我們不把它當成看多的理由。',
          '30-day ' + (x.value >= 0 ? 'positive' : 'negative') + ', 1-year ' + (vy >= 0 ? 'positive' : 'negative') + ': short and long run disagree. “30d negative, 1y positive” is often called a bull-market pullback, but since 2016 that mix was followed by worse-than-average 90-day returns, so we do not treat it as a bullish sign. '),
        _T('兩者同向。', 'both pointing the same way.'), 'neu');
    }
    var soon = (x.echo_soon || [])[0], seen = M.filter(function (m) { return m.echo_rise != null; }), hit = seen.filter(function (m) { return m.echo_rise >= m.btc * 0.5; });
    if (soon || M.length) it.push([_T('疑似搬家', 'Likely transfers'), soon ? ymd(soon.echo).slice(5) : String(M.length),
      _T((soon ? ymd(soon.start) + (soon.end !== soon.start ? '–' + ymd(soon.end).slice(5) : '') + ' 一天搬動 ' + cohCoins(soon.btc) + ' 1 年以上的舊幣（疑似交易所或託管整理錢包），這批幣若一直沒動，會在 ' + ymd(soon.echo) + ' 前後滿一年，把這條線拉低同樣的量——那是搬家的回音，不是需求崩掉。' : '') + (seen.length ? '過去 ' + seen.length + ' 次中 ' + hit.length + ' 次一年後真的出現回音（其他幾次那批幣又被動過）。' : ''),
        (soon ? ymd(soon.start) + ' moved ' + cohCoins(soon.btc) + ' of 1y+ coins in a day (likely an exchange or custodian reshuffle). If they stay put they turn one year old around ' + ymd(soon.echo) + ' and drag this line down by the same amount — an echo of the transfer, not collapsing demand. ' : '') + (seen.length ? 'Of ' + seen.length + ' past cases, ' + hit.length + ' produced the echo a year later (the rest moved again).' : '')), 'neu']);
    if (adView) it.push(adView);
    return it;
  }
  var AD_Y = 30 / 365;   // 1 年版畫在 30 天的刻度上
  function ds_(n) { var t = new Date(n * 864e5); return t.toISOString().slice(0, 10); }
  function adPanel() {
    var x = (D.onchain || {}).ad; if (!x || !x.rows) return '';
    return panel('span-12', _T('表觀需求（30 天與 1 年）', 'Apparent demand (30 days and 1 year)'), _T('CheckOnChain HODL Waves · ' + fmt.md(x.date), 'CheckOnChain HODL waves · ' + fmt.md(x.date)),
      interpHtml(adSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('表觀需求 ≥ 0', 'Demand ≥ 0'), 'var(--up)', 'box'], [_T('表觀需求 < 0', 'Demand < 0'), 'var(--down)', 'box'], [_T('它的 30 日平均', 'Its 30-day average'), 'var(--ink-2)', 'dash']].concat(x.y1 ? [[_T('1 年版（換算成每 30 天）', '1-year version (per 30 days)'), 'var(--s3)']] : []).concat([[_T('疑似搬家', 'Likely transfer'), 'var(--warn)']])) + '<div class="chart" id="c-ad"></div>' +
      '<p class="note">' + _T('CryptoQuant 的定義：30 天新挖出的幣 − 30 天內「1 年以上沒動過的供給」的變化。舊幣醒來、被市場接走時為正；滿一年還沒動的幣增加得比新挖出的快時為負，代表換手少、需求偏弱。1 年以上供給取自 CheckOnChain 的 HODL Waves（逐筆計算、不是實體調整，所以交易所整理錢包會出現尖峰，CryptoQuant 的版本看不到）；新挖出的幣照減半時程估。1 年版是同樣算法的 365 天合計，圖上除以 365 再乘 30，和 30 天版放在同一個刻度（提示框是原始的 1 年合計）。數字照實顯示、不修改。',
        'CryptoQuant\'s definition: coins mined in 30 days − the 30-day change in supply unmoved for a year or more. Positive when old coins wake and are absorbed; negative when coins reaching one year unmoved outpace issuance — little turnover, soft demand. The 1y+ supply comes from CheckOnChain\'s HODL waves (per-UTXO, not entity-adjusted, so exchange wallet reshuffles show up as spikes that CryptoQuant\'s version filters out); issuance follows the halving schedule. The 1-year version is the same sum over 365 days, drawn ×30/365 to share the 30-day scale (the tooltip shows the raw 1-year sum). Numbers are shown as they are.') + '</p>');
  }
  function drawAd(el) {
    var x = (D.onchain || {}).ad; if (!x || !el) return;
    var R_ = x.rows, lo, hi, col = function (v) { return 'var(--' + (v >= 0 ? 'up' : 'down') + ')'; }, kf = function (v) { return (v > 0 ? '+' : '') + fmt.k(v); };
    twoPane(el, { rows: R_, pi: 3, hp: [100, 130], hs: [160, 210], label: _T('表觀需求（30 天合計，顆）', 'Apparent demand (30-day sum, BTC)'), aria: _T('BTC 價格與表觀需求', 'BTC price and apparent demand'),
      scale: function (C) {
        var vs = R_.map(function (r) { return r[1]; }).concat(R_.filter(function (r) { return r[2] != null; }).map(function (r) { return r[2]; })).concat(R_.filter(function (r) { return r[4] != null; }).map(function (r) { return r[4] * AD_Y; })), st = niceStep(Math.max.apply(null, vs) - Math.min.apply(null, vs) || 1, C.sm ? 4 : 6);
        lo = Math.floor(Math.min.apply(null, vs) / st) * st; hi = Math.ceil(Math.max.apply(null, vs) / st) * st; C.st = st;
        return function (v) { return C.ys0 + (1 - (v - lo) / (hi - lo || 1)) * C.hs; };
      },
      body: function (C) {
        var s = '';
        for (var g = lo; g <= hi + 1; g += C.st) s += C.gl(C.Ys(g), kf(g), g ? 'gl' : 'base');
        var bw = Math.max(1, C.pw / C.rows.length + 0.3), z0 = C.Ys(0);
        R_.forEach(function (r) { var cx = C.X(r[0]), yv = C.Ys(r[1]); s += '<rect x="' + (cx - bw / 2).toFixed(1) + '" y="' + Math.min(z0, yv).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(0.5, Math.abs(yv - z0)).toFixed(1) + '" fill="' + col(r[1]) + '" opacity=".55"/>'; });
        s += '<path class="ln" d="M' + R_.filter(function (r) { return r[2] != null; }).map(function (r) { return C.X(r[0]).toFixed(1) + ',' + C.Ys(r[2]).toFixed(1); }).join('L') + '" stroke="var(--ink-2)" stroke-width="1.3" stroke-dasharray="4 3"/>';
        var y1r = R_.filter(function (r) { return r[4] != null; });
        if (y1r.length) s += '<path class="ln" d="M' + y1r.map(function (r) { return C.X(r[0]).toFixed(1) + ',' + C.Ys(r[4] * AD_Y).toFixed(1); }).join('L') + '" stroke="var(--s3)" stroke-width="1.6"/>';
        (x.moves || []).forEach(function (m) { var xm = C.X(dnOf(m.start)); if (xm < C.ML || xm > C.ML + C.pw) return; s += '<line x1="' + xm.toFixed(1) + '" x2="' + xm.toFixed(1) + '" y1="' + C.ys0 + '" y2="' + C.yb + '" stroke="var(--warn)" stroke-dasharray="2 4" stroke-width="1"/><circle cx="' + xm.toFixed(1) + '" cy="' + (C.ys0 + 4) + '" r="3" fill="var(--warn)"/>'; });
        return s;
      },
      over: function (C) { var z = R_[R_.length - 1]; return dot1(C.X(z[0]), C.Ys(z[1]), col(z[1])); },
      tip: function (p, C) {
        var mv = (x.moves || []).filter(function (m) { return Math.abs(dnOf(m.start) - p[0]) <= 3; })[0];
        return { dots: dot1(C.X(p[0]), C.Ys(p[1]), col(p[1])), rows: tipRow1(col(p[1]), _T('表觀需求（30 天）', 'Apparent demand (30d)'), adK(p[1])) + (p[2] != null ? tipRow1('var(--ink-2)', _T('30 日平均', '30-day avg'), adK(p[2])) : '') + (p[4] != null ? tipRow1('var(--s3)', _T('1 年合計', '1-year sum'), adK(p[4])) : ''),
          after: mv ? tipRow1('var(--warn)', _T('疑似搬家', 'Likely transfer'), cohCoins(mv.btc)) : '' };
      } });
  }


  /* 長期持有者虧損比例（2026-11-04 使用者要求，Supply In Loss % - LTH；資料 CheckOnChain）：
     標出歷輪熊市底部的高點與「這輪高點」線；打破「脫離底部後不再創新高」的價位用長期持有者籌碼分布每天重算。上下兩格共用時間軸。只作讀值 */
  function llSay() {
    var x = D.onchain.lthloss, it = [], P = x.peaks || [], lp = P[P.length - 1], pm = x.post_min, c = x.cohort, ymd = function (s) { return s.replace(/-/g, '/'); };
    it.push([_T('長期持有者虧損比例', 'LTH supply in loss'), fmt.n(x.value, 1) + '%',
      _T('持有 155 天以上的幣，有 ' + fmt.n(x.value, 1) + '% 成本在現價之上。' + (lp ? '這輪高點 ' + fmt.n(lp.value, 1) + '%（' + ymd(lp.date) + '，價格 ' + fmt.usd(lp.price) + '）' : '') + (pm ? '，之後最低 ' + fmt.n(pm.value, 1) + '%（' + ymd(pm.date) + '），現在' + (x.value >= pm.value ? '回升 ' : '再降 ') + fmt.n(Math.abs(x.value - pm.value), 1) + ' 個百分點。' : '。'),
        fmt.n(x.value, 1) + '% of coins held 155+ days cost more than today\'s price. ' + (lp ? 'This cycle\'s peak was ' + fmt.n(lp.value, 1) + '% (' + ymd(lp.date) + ', price ' + fmt.usd(lp.price) + ')' : '') + (pm ? ', the low since ' + fmt.n(pm.value, 1) + '% (' + ymd(pm.date) + '); now ' + (x.value >= pm.value ? 'up ' : 'down ') + fmt.n(Math.abs(x.value - pm.value), 1) + ' points.' : '.')), 'neu']);
    if (c && c.break_price && lp) {
      var t70 = (c.table || []).filter(function (r) { return r[0] <= 70000; })[0];
      it.push([_T('規律的分界', 'Where the pattern breaks'), '≈ ' + fmt.k(c.break_price),
        _T('照現在的長期持有者籌碼（CheckOnChain，' + fmt.md(c.date) + '）推算，價格跌到約 ' + fmt.usd(c.break_price) + ' 時虧損比例會超過這輪高點 ' + fmt.n(lp.value, 1) + '%，等於打破「脫離底部後不再創新高」' + (t70 ? '；跌到 ' + fmt.k(t70[0]) + ' 約 ' + fmt.n(t70[1], 0) + '%' : '') + '。最近在高價買進的短期持有者滿 155 天後會轉成長期持有者，價格不漲時這條線會慢慢上移，所以每天重算。',
          'From today\'s long-term holder supply map (CheckOnChain, ' + fmt.md(c.date) + '), a drop to about ' + fmt.usd(c.break_price) + ' would push the share above this cycle\'s ' + fmt.n(lp.value, 1) + '% peak, breaking the “no new high after the bottom” pattern' + (t70 ? '; at ' + fmt.k(t70[0]) + ' it would be about ' + fmt.n(t70[1], 0) + '%' : '') + '. Recent high-priced buyers turn long-term after 155 days, so the line drifts up if price stalls; it is recomputed daily.'), 'neu']);
    }
    var past = P.filter(function (p) { return p.after_max; });
    if (past.length) it.push([_T('歷輪底部', 'Past cycle bottoms'), P.length + _T(' 輪', ' cycles'),
      _T('熊市底部的高點：' + P.map(function (p) { return p.date.slice(0, 7).replace('-', '/') + ' ' + fmt.n(p.value, 1) + '%'; }).join('、') + '。之前幾輪脫離底部後都沒有再創新高：' + past.map(function (p) { return p.date.slice(0, 4) + ' 之後最高 ' + fmt.n(p.after_max.value, 1) + '%（' + p.after_max.date.slice(0, 7).replace('-', '/') + '）'; }).join('、') + '。樣本只有 3–4 輪，2015 年那輪高點 53% 也比後來高。',
        'Peaks at bear-market bottoms: ' + P.map(function (p) { return p.date.slice(0, 7).replace('-', '/') + ' ' + fmt.n(p.value, 1) + '%'; }).join(', ') + '. In earlier cycles it never made a new high after leaving the bottom: ' + past.map(function (p) { return 'after ' + p.date.slice(0, 4) + ' the max was ' + fmt.n(p.after_max.value, 1) + '% (' + p.after_max.date.slice(0, 7).replace('-', '/') + ')'; }).join(', ') + '. Only 3–4 cycles; 2015\'s 53% peak was also higher than later ones.'), 'neu']);
    return it;
  }
  /* 長期持有者已實現虧損（2026-11-05 使用者要求，補充指標 PDF；資料 Bitview，美元，不是實體調整）：7 日合計 ÷ 市值。
     歷史上不是「新低但虧損變小＝賣壓衰竭」：前三次熊市都是底部那次低點虧損最大，所以照實列出本輪各低點與歷輪對照。只作讀值 */
  function rlUsd(m) { return LANG === 'en' ? '$' + fmt.n(m / 1000, 1) + 'B' : fmt.n(m / 100, 0) + ' 億美元'; }
  function rlSay() {
    var x = D.onchain.lthrl, it = [], L = x.lows_now || [], B = (x.bears || []).filter(function (b) { return b.lows.length > 1; }), ym = function (s) { return s.slice(0, 7).replace('-', '/'); };
    var past = B.filter(function (b) { return !L.length || b.bottom < L[0].date; });   // 本輪的低點另外列，這裡只放之前的熊市
    it.push([_T('長期持有者已實現虧損', 'LTH realized loss'), fmt.n(x.rel, 2) + '%',
      _T('近 7 天長期持有者賣在成本以下、實現的虧損約 ' + rlUsd(x.usd7_m) + '，是市值的 ' + fmt.n(x.rel, 2) + '%（' + fmt.md(x.date) + '）；2015 年以來第 ' + fmt.n(x.pct, 0) + ' 百分位。',
        'Over the past 7 days long-term holders realized about ' + rlUsd(x.usd7_m) + ' of losses selling below cost, ' + fmt.n(x.rel, 2) + '% of market cap (' + fmt.md(x.date) + '); ' + fmt.n(x.pct, 0) + 'th percentile since 2015.'), 'neu']);
    if (L.length) it.push([_T('本輪各低點', 'This cycle\'s lows'), L.length + _T(' 次', ''),
      _T(L.map(function (l) { return ym(l.date) + ' ' + fmt.usd(l.price) + '：' + fmt.n(l.rel, 2) + '%'; }).join('、') + '（低點前後 7 天的最大值）。',
        L.map(function (l) { return ym(l.date) + ' ' + fmt.usd(l.price) + ': ' + fmt.n(l.rel, 2) + '%'; }).join(', ') + ' (max within 7 days of each low).'), 'neu']);
    if (past.length) {
      var all = past.every(function (b) { return b.last_is_max; });
      it.push([_T('歷輪熊市', 'Past bear markets'), past.length + _T(' 輪', ''),
        _T((all ? '前 ' + past.length + ' 次熊市都是底部那次低點的虧損最大：' : '前幾次熊市最大的一次：') + past.map(function (b) { return ym(b.max.date) + ' ' + fmt.n(b.max.rel, 2) + '%'; }).join('、') + '。2018 年 6→8→10 月虧損一度縮小，之後還有最大的一次投降，所以「價格新低但虧損變小」不能單獨當成賣壓衰竭。',
          (all ? 'In each of the past ' + past.length + ' bear markets the bottom brought the largest loss: ' : 'Largest in past bear markets: ') + past.map(function (b) { return ym(b.max.date) + ' ' + fmt.n(b.max.rel, 2) + '%'; }).join(', ') + '. In 2018 the loss shrank from June to August to October and the biggest capitulation still came after, so “a new low with a smaller loss” is not on its own a sign of seller exhaustion.'), 'neu']);
    }
    var mx = L.length ? L.reduce(function (a, b) { return b.rel > a.rel ? b : a; }) : null, pmin = past.length ? Math.min.apply(null, past.map(function (b) { return b.max.rel; })) : null;
    var cc = (D.cycle || {}).cycle_cmp, cur = cc ? (cc.cycles || []).filter(function (c) { return c.now; })[0] : null, ll = (D.onchain || {}).lthloss, lp = ll && ll.peaks ? ll.peaks[ll.peaks.length - 1] : null;
    if (mx && pmin) it.push(viewRow(_T('這輪沒有大投降', 'No big capitulation this cycle'),
      _T('這輪長期持有者認賠最多只有 ' + fmt.n(mx.rel, 2) + '%（' + ym(mx.date) + '），前幾次熊市底部至少 ' + fmt.n(pmin, 2) + '%。兩種讀法：這輪本來跌得淺' + (cur ? '（最深 ' + fmt.pct(cur.low.pct, 0) + '，前幾輪 −77%～−85%）' : '') + '，不需要大規模投降；或真正的投降還沒來。我們偏向前者' + (lp ? '——長期持有者虧損比例 ' + ym(lp.date) + ' 的高點 ' + fmt.n(lp.value, 1) + '% 已經落在歷輪底部的 42–48% 區間' : '') + '，和「這輪低點已經出現」一致。近 7 天 ' + fmt.n(x.rel, 2) + '%（第 ' + fmt.n(x.pct, 0) + ' 百分位），代表長期持有者在現價附近仍有人認賠，賣壓還沒清乾淨。',
        'This cycle\'s largest long-term holder capitulation was only ' + fmt.n(mx.rel, 2) + '% (' + ym(mx.date) + '); past bear-market bottoms reached at least ' + fmt.n(pmin, 2) + '%. Two readings: this cycle fell less' + (cur ? ' (deepest ' + fmt.pct(cur.low.pct, 0) + ' vs −77% to −85% before)' : '') + ' and never needed a mass capitulation, or the real one is still ahead. We lean to the first' + (lp ? ': long-term holders\' share in loss peaked at ' + fmt.n(lp.value, 1) + '% in ' + ym(lp.date) + ', inside the 42–48% band of past bottoms' : '') + ', consistent with this cycle\'s low already being in. The last 7 days at ' + fmt.n(x.rel, 2) + '% (' + fmt.n(x.pct, 0) + 'th percentile) show some long-term holders still selling at a loss near current prices, so the overhang is not fully cleared. '),
      _T('出現 ' + fmt.n(pmin, 2) + '% 以上的尖峰（那才是過去底部那種投降）。', 'a spike above ' + fmt.n(pmin, 2) + '% (the kind of capitulation past bottoms had).'), 'neu'));
    return it;
  }
  function drawLthRl(el) {
    var x = (D.onchain || {}).lthrl; if (!x || !el) return;
    var R_ = x.rows;
    lineChart(el, { h: el.clientWidth < 520 ? 200 : 240, log2: true, series: [{ name: _T('BTC 價格', 'BTC price'), data: R_.map(function (r) { return [r[0], r[2]]; }), color: 'var(--ink-3)', w: 1.1, end: false, y2: true, fmt: fmt.usd },
      { name: _T('長期持有者已實現虧損（7 日 ÷ 市值）', 'LTH realized loss (7d ÷ market cap)'), data: R_.map(function (r) { return [r[0], r[1]]; }), color: 'var(--s1)', w: 1.5 }],
      yFmt: function (v) { return v.toFixed(1) + '%'; }, tipFmt: function (v) { return fmt.n(v, 2) + '%'; }, aria: _T('BTC 價格與長期持有者已實現虧損', 'BTC price and long-term holder realized loss') });
  }
  function lthLossPanel() {
    var x = (D.onchain || {}).lthloss; if (!x || !x.rows) return '';
    return panel('span-12', _T('長期持有者虧損比例', 'Long-term holder supply in loss'), _T('CheckOnChain · ' + fmt.md(x.date), 'CheckOnChain · ' + fmt.md(x.date)),
      interpHtml(llSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('長期持有者虧損比例', 'LTH supply in loss'), 'var(--s3)'], [_T('這輪高點', 'This cycle\'s peak'), 'var(--down)', 'dash'], [_T('歷輪底部區 42–48%', 'Past bottoms 42–48%'), 'var(--down)', 'box']]) + '<div class="chart" id="c-lthloss"></div>' +
      '<p class="note">' + _T('持有 155 天以上（長期持有者）的幣裡，成本高於現價、帳面虧損的比例。熊市底部時大量長期持有者被套，這個比例衝到高點；之後隨價格回升下降。資料取自 CheckOnChain（Bitcoin Research Kit，依每顆幣的實際幣齡算）。', 'The share of coins held 155+ days (long-term holders) whose cost is above the current price. At bear-market bottoms many long-term holders are underwater and it peaks; it falls as price recovers. Data from CheckOnChain (Bitcoin Research Kit, by each coin\'s actual age).') +
      ' <a href="https://charts.checkonchain.com/btconchain/unrealised/topheavy_supplyinloss_lth/topheavy_supplyinloss_lth_light.html" target="_blank" rel="noopener">' + _T('原圖 ↗', 'Source chart ↗') + '</a></p>' +
      (((D.onchain || {}).lthrl || {}).rows ? '<div class="panel-h" style="margin-top:14px"><h3>' + _T('長期持有者已實現虧損（7 日合計 ÷ 市值）', 'Long-term holder realized loss (7-day sum ÷ market cap)') + '</h3></div>' + interpHtml(rlSay()) +
        legend([[_T('BTC 價格（上格）', 'BTC price (top)'), 'var(--ink-3)'], [_T('已實現虧損 ÷ 市值', 'Realized loss ÷ market cap'), 'var(--s1)']]) + '<div class="chart" id="c-lthrl"></div>' +
        '<p class="note">' + _T('長期持有者（持有 155 天以上）賣在自己的成本以下時實現的虧損，7 天合計後除以市值，不同年份才能比。資料 Bitview（逐筆計算，不是 Glassnode 的實體調整版，同一個人自己搬幣也可能算進去）。擺動低點＝收盤是前後 30 天最低、且比之前 180 天最高跌 20% 以上。',
          'Losses long-term holders (155+ days) realize when selling below their own cost, summed over 7 days and divided by market cap so years compare. Data from Bitview (per UTXO, not Glassnode\'s entity-adjusted version, so self-transfers can count). A swing low is a close that is the lowest within 30 days either side and 20%+ below the prior 180-day high.') + '</p>' : ''));
  }
  function drawLthLoss(el) {
    var x = (D.onchain || {}).lthloss; if (!x || !el) return;
    var R_ = x.rows, P = x.peaks || [], lp = P[P.length - 1], W = Math.max(280, el.clientWidth), sm = W < 520, ML = 8, MR = 58, MT = 16, hp = sm ? 100 : 130, gap = 28, hs = sm ? 150 : 190, MB = 24, Ht = MT + hp + gap + hs + MB, pw = W - ML - MR, ys0 = MT + hp + gap;
    var x0 = R_[0][0], x1 = R_[R_.length - 1][0], X = function (t) { return ML + (t - x0) / (x1 - x0 || 1) * pw; }, s = '', L = Math.log10;
    var pl = L(Math.min.apply(null, R_.map(function (r) { return r[2]; }))), ph = L(Math.max.apply(null, R_.map(function (r) { return r[2]; }))), pp = (ph - pl) * 0.05; pl -= pp; ph += pp;
    var top = Math.max(60, Math.ceil(Math.max.apply(null, R_.map(function (r) { return r[1]; })) / 10) * 10);
    var Yp = function (v) { return MT + (1 - (L(v) - pl) / (ph - pl)) * hp; }, Ys = function (v) { return ys0 + (1 - v / top) * hs; };
    var tx = function (xx, y, t, a, cls) { return '<text class="' + (cls || 'ax') + '" x="' + xx.toFixed(1) + '" y="' + y.toFixed(1) + '"' + (a ? ' text-anchor="' + a + '"' : '') + '>' + esc(t) + '</text>'; };
    [10, 100, 1e3, 1e4, 1e5].forEach(function (t) { if (L(t) < pl || L(t) > ph) return; var y = Yp(t); s += '<line class="gl" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/>' + tx(ML + pw + 8, y + 3.5, t >= 1000 ? fmt.k(t) : '$' + t); });
    s += '<rect x="' + ML + '" y="' + Ys(48).toFixed(1) + '" width="' + pw + '" height="' + (Ys(42) - Ys(48)).toFixed(1) + '" fill="var(--down-dim)"/>';
    for (var g = 0; g <= top; g += 10) { var yg = Ys(g); s += '<line class="' + (g ? 'gl' : 'base') + '" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + yg.toFixed(1) + '" y2="' + yg.toFixed(1) + '"/>' + tx(ML + pw + 8, yg + 3.5, g + '%'); }
    if (lp) s += '<line x1="' + X(dnOf(lp.date)).toFixed(1) + '" x2="' + (ML + pw) + '" y1="' + Ys(lp.value).toFixed(1) + '" y2="' + Ys(lp.value).toFixed(1) + '" stroke="var(--down)" stroke-dasharray="4 4" stroke-width="1"/>';
    s += tx(ML, MT - 5, _T('BTC 價格（對數刻度）', 'BTC price (log scale)')) + tx(ML, ys0 - 9, _T('長期持有者虧損比例', 'LTH supply in loss'));
    var y0 = new Date(x0 * 864e5).getUTCFullYear() + 1, y1 = new Date(x1 * 864e5).getUTCFullYear(), every = sm ? 3 : W < 900 ? 2 : 1;
    for (var y = y0; y <= y1; y++) { var xx = X(Date.UTC(y, 0, 1) / 864e5); if ((y - y0) % every === 0 && xx > ML + 14 && xx < ML + pw - 14) s += tx(xx, Ht - 6, String(y), 'middle'); }
    s += '<path class="ln" d="M' + R_.map(function (r) { return X(r[0]).toFixed(1) + ',' + Yp(r[2]).toFixed(1); }).join('L') + '" stroke="var(--ink-2)" stroke-width="1.3"/>';
    s += '<path class="ln" d="M' + R_.map(function (r) { return X(r[0]).toFixed(1) + ',' + Ys(r[1]).toFixed(1); }).join('L') + '" stroke="var(--s3)" stroke-width="1.5"/>';
    P.forEach(function (p) { var xp = X(dnOf(p.date)), yp = Ys(p.value); if (xp < ML) return; s += '<circle cx="' + xp.toFixed(1) + '" cy="' + yp.toFixed(1) + '" r="4" fill="var(--deck)" stroke="var(--down)" stroke-width="2"/>' + (sm ? '' : tx(xp > ML + pw - 90 ? xp - 8 : xp, yp - 9, p.date.slice(0, 7).replace('-', '/') + ' ' + fmt.n(p.value, 1) + '%', xp > ML + pw - 90 ? 'end' : 'middle', 'ax hi')); });
    var zz = R_[R_.length - 1]; s += '<circle cx="' + X(zz[0]).toFixed(1) + '" cy="' + Ys(zz[1]).toFixed(1) + '" r="4" fill="var(--s3)" stroke="var(--deck)" stroke-width="2"/>';
    s += '<line class="xh" x1="0" x2="0" y1="' + MT + '" y2="' + (ys0 + hs) + '" visibility="hidden"/><g class="hdots"></g><rect class="hit" x="' + ML + '" y="' + MT + '" width="' + pw + '" height="' + (ys0 + hs - MT) + '"/>';
    el.innerHTML = svgEl(W, Ht, s, _T('BTC 價格與長期持有者虧損比例', 'BTC price and long-term holder supply in loss'));
    animateLines(el);
    var svg = el.querySelector('svg'), xh = svg.querySelector('.xh'), dots = svg.querySelector('.hdots'), hit = svg.querySelector('.hit');
    function move(ev) {
      var r = svg.getBoundingClientRect(), xv = x0 + ((ev.clientX - r.left) * W / r.width - ML) / pw * (x1 - x0), p = R_[bisect(R_, xv)];
      xh.setAttribute('x1', X(p[0])); xh.setAttribute('x2', X(p[0])); xh.setAttribute('visibility', 'visible');
      dots.innerHTML = '<circle cx="' + X(p[0]).toFixed(1) + '" cy="' + Ys(p[1]).toFixed(1) + '" r="4" fill="var(--s3)" stroke="var(--deck)" stroke-width="2"/><circle cx="' + X(p[0]).toFixed(1) + '" cy="' + Yp(p[2]).toFixed(1) + '" r="3.5" fill="var(--ink-2)" stroke="var(--deck)" stroke-width="2"/>';
      showTip(ev.clientX, ev.clientY, '<div class="t">' + fmt.date(p[0]) + '</div><div class="r"><i style="background:var(--s3)"></i><span>' + _T('長期持有者虧損比例', 'LTH supply in loss') + '</span><b>' + fmt.n(p[1], 1) + '%</b></div><div class="r"><i style="background:var(--ink-2)"></i><span>' + _T('BTC 價格', 'BTC price') + '</span><b>' + fmt.usd(p[2]) + '</b></div>');
    }
    hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', function () { xh.setAttribute('visibility', 'hidden'); dots.innerHTML = ''; hideTip(); });
  }

  /* 短期持有者成本帶（2026-11-04 使用者要求，Glassnode 的 STH cost basis ±1/±2 標準差；資料 Bitview）：
     帶＝短期持有者成本 ×（近 4 年「價格 ÷ 成本」的平均 ± k 個標準差），帶的中心不是成本線，所以上下不對稱。只作讀值 */
  // 2026-11-05 加 ±0.5 標準差（點線、較細）：離現價最近的上下兩條。第 4 欄是線寬
  var SB_K = [[2, 'var(--s1)', '5 4'], [1, 'var(--s4)', ''], [0.5, 'var(--s4)', '2 3', 0.9], [-0.5, 'var(--s3)', '2 3', 0.9], [-1, 'var(--s3)', ''], [-2, 'var(--down)', '5 4']];
  function sbLab(k) { return (k > 0 ? '+' : '−') + Math.abs(k) + _T(' 標準差', 'σ'); }
  function sbZ(z) { return (z >= 0 ? '+' : '−') + fmt.n(Math.abs(z), 1); }
  function ymdD(s) { return s ? s.replace(/-/g, '/') : '—'; }
  function sbSay() {
    var x = D.onchain.sth_bands, n = x.now, st = x.stats || {}, b = n.bands, it = [], gp = fmt.n(Math.abs(n.px / n.sth - 1) * 100, 1), mx = st.max120, fell = mx && mx.z >= 0.8 && n.z < mx.z - 0.5;
    it.push([_T('現在位置', 'Where price sits'), sbZ(n.z) + _T(' 標準差', 'σ'),
      _T('收盤 ' + fmt.usd(n.px) + '，在短期持有者成本 ' + fmt.usd(n.sth) + (n.px >= n.sth ? ' 上方 ' : ' 下方 ') + gp + '%。帶的中心（近 4 年平均）是成本 ×' + fmt.n(n.mu, 3) + '＝' + fmt.usd(n.center) + '，現在在中心' + (n.z >= 0 ? '上方' : '下方') + '。',
        'Close ' + fmt.usd(n.px) + ', ' + gp + '% ' + (n.px >= n.sth ? 'above' : 'below') + ' the short-term holder cost of ' + fmt.usd(n.sth) + '. The centre of the bands (4-year average) is cost ×' + fmt.n(n.mu, 3) + ' = ' + fmt.usd(n.center) + '; price is ' + (n.z >= 0 ? 'above' : 'below') + ' it.'), Math.abs(n.z) >= 1 ? 'warn' : 'neu']);
    var h5 = b['0.5'] != null, l5 = b['-0.5'] != null;
    it.push([_T('上緣', 'Upper bands'), (h5 ? fmt.k(b['0.5']) + ' / ' : '') + fmt.k(b['1']) + ' / ' + fmt.k(b['2']),
      _T((h5 ? '+0.5 標準差 ' + fmt.usd(b['0.5']) + '、' : '') + '+1 標準差 ' + fmt.usd(b['1']) + '、+2 標準差 ' + fmt.usd(b['2']) + '。近 4 年只有 ' + fmt.n(st.above1_pct, 0) + '% 的日子收在 +1 標準差以上' + (fell ? '；近 120 天最高到 ' + sbZ(mx.z) + ' 標準差（' + ymdD(mx.date) + '）後回落' : '') + '。',
        (h5 ? '+0.5σ ' + fmt.usd(b['0.5']) + ', ' : '') + '+1σ ' + fmt.usd(b['1']) + ', +2σ ' + fmt.usd(b['2']) + '. Only ' + fmt.n(st.above1_pct, 0) + '% of days in the past 4 years closed above +1σ' + (fell ? '; the last 120 days peaked at ' + sbZ(mx.z) + 'σ (' + ymdD(mx.date) + ') and fell back' : '') + '.'), 'neu']);
    it.push([_T('下緣', 'Lower bands'), (l5 ? fmt.k(b['-0.5']) + ' / ' : '') + fmt.k(b['-1']) + ' / ' + fmt.k(b['-2']),
      _T((l5 ? '−0.5 標準差 ' + fmt.usd(b['-0.5']) + '、' : '') + '−1 標準差 ' + fmt.usd(b['-1']) + '、−2 標準差 ' + fmt.usd(b['-2']) + '。近 4 年 ' + fmt.n(st.below1_pct, 0) + '% 的日子收在 −1 標準差以下' + (st.last_below1 ? '，上一次是 ' + ymdD(st.last_below1) : '') + '。',
        (l5 ? '−0.5σ ' + fmt.usd(b['-0.5']) + ', ' : '') + '−1σ ' + fmt.usd(b['-1']) + ', −2σ ' + fmt.usd(b['-2']) + '. ' + fmt.n(st.below1_pct, 0) + '% of days in the past 4 years closed below −1σ' + (st.last_below1 ? '; the last was ' + ymdD(st.last_below1) : '') + '.'), 'neu']);
    var act = ((D.cycle || {}).levels || {}).act, z = n.z, ov = act && b['0.5'] && Math.abs(act.value / b['0.5'] - 1) < 0.03;
    if (z >= 1) it.push(viewRow(_T('過熱', 'Stretched'),
      _T('收盤在 +' + fmt.n(z, 1) + ' 標準差：近 4 年只有 ' + fmt.n(st.above1_pct, 0) + '% 的日子在 +1 標準差以上，短期持有者帳面獲利很厚，獲利了結的壓力大。我們看漲勢延續的空間有限。',
        'The close is at +' + fmt.n(z, 1) + 'σ: only ' + fmt.n(st.above1_pct, 0) + '% of days in four years sat above +1σ, so short-term holders sit on fat paper gains and profit-taking pressure is high. Limited room to keep running. '),
      _T('收回 +1 標準差 ' + fmt.usd(b['1']) + ' 下方。', 'a close back below +1σ at ' + fmt.usd(b['1']) + '.'), 'warn'));
    else if (z >= 0) it.push(viewRow(_T('健康但不強', 'Healthy, not strong'),
      _T('收盤在成本上方 ' + fmt.n((n.px / n.sth - 1) * 100, 1) + '%、+' + fmt.n(z, 1) + ' 標準差：短期持有者整體小賺，這是上漲中正常的回測區。' + (ov ? '上方 +0.5 標準差 ' + fmt.usd(b['0.5']) + ' 和活躍投資人成本 ' + fmt.usd(act.value) + ' 幾乎重疊，兩個角度都指向同一個壓力帶。' : '上方先看 +0.5 標準差 ' + fmt.usd(b['0.5']) + '。'),
        'The close is ' + fmt.n((n.px / n.sth - 1) * 100, 1) + '% above cost, at +' + fmt.n(z, 1) + 'σ: short-term holders are slightly in profit, a normal retest zone in an uptrend. ' + (ov ? 'Above, +0.5σ at ' + fmt.usd(b['0.5']) + ' nearly coincides with the active investor price of ' + fmt.usd(act.value) + ', so two separate measures point at the same resistance. ' : 'The first level above is +0.5σ at ' + fmt.usd(b['0.5']) + '. ')),
      _T('收破短期持有者成本 ' + fmt.usd(n.sth) + '（短期持有者整體轉虧）。', 'a close below the short-term holder cost of ' + fmt.usd(n.sth) + ' (short-term holders turn to a loss).'), 'neu'));
    else if (z > -1) it.push(viewRow(_T('偏弱', 'Soft'),
      _T('收盤在成本下方：短期持有者整體虧損，反彈到成本線 ' + fmt.usd(n.sth) + ' 附近會遇到回本賣壓。',
        'The close is below cost: short-term holders are under water as a group, and rallies toward the cost line at ' + fmt.usd(n.sth) + ' meet break-even selling. '),
      _T('收回 ' + fmt.usd(n.sth) + ' 上方。', 'a close back above ' + fmt.usd(n.sth) + '.'), 'warn'));
    else it.push(viewRow(_T('壓力極大', 'Deep stress'),
      _T('收盤在 −' + fmt.n(-z, 1) + ' 標準差：近 4 年只有 ' + fmt.n(st.below1_pct, 0) + '% 的日子這麼低，短期持有者大面積認賠。這是恐慌區，賣壓多半已經集中釋放。',
        'The close is at −' + fmt.n(-z, 1) + 'σ, a level seen on only ' + fmt.n(st.below1_pct, 0) + '% of days in four years: short-term holders are capitulating broadly. This is panic territory, where much of the selling has usually already happened. '),
      _T('再跌破 −2 標準差 ' + fmt.usd(b['-2']) + '。', 'a further break below −2σ at ' + fmt.usd(b['-2']) + '.'), 'neg'));
    return it;
  }
  function sbPanel() {
    var x = (D.onchain || {}).sth_bands; if (!x || !x.rows) return '';
    return panel('span-12', _T('短期持有者成本帶', 'Short-term holder cost bands'), 'Bitview · ' + fmt.md(x.date),
      interpHtml(sbSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('短期持有者成本', 'STH cost'), 'var(--s2)']].concat(SB_K.map(function (k) { return [sbLab(k[0]), k[1], k[2] ? (k[3] ? 'dots' : 'dash') : '']; }))) + '<div class="chart" id="c-sthband"></div>' +
      '<p class="note">' + _T('短期持有者＝持有不到 155 天的幣，成本是它們的平均買價。帶的算法和 Glassnode 的「短期持有者成本基礎模型」相同：成本 ×（近 4 年「價格 ÷ 成本」的平均 ± 0.5、1、2 個標準差，±0.5 是較細的點線）；帶的中心不是成本線，所以上下不對稱。2026-11-04 驗算：−1 標準差算出 68,991，和用 Glassnode 資料算出的公開數字（約 68,900）差不到 0.2%。資料 Bitview（Bitcoin Research Kit 的公開 API），價格用本站統一收盤。',
        'Short-term holders = coins held under 155 days; their cost is the average purchase price. The bands follow Glassnode\'s short-term holder cost basis model: cost × (the 4-year average of price ÷ cost ± 0.5, 1 and 2 standard deviations; ±0.5 are the thinner dotted lines); the centre is not the cost line, so the bands are asymmetric. Checked on 2026-11-04: −1σ comes out at 68,991, within 0.2% of a published figure based on Glassnode data (about 68,900). Data from Bitview (Bitcoin Research Kit\'s public API); price is the site\'s standard close.') + '</p>');
  }
  function drawSthBand(el) {
    var x = (D.onchain || {}).sth_bands; if (!x || !el) return;
    var R_ = x.rows, ser = [{ name: _T('BTC 價格', 'BTC price'), data: R_.map(function (r) { return [r[0], r[1]]; }), color: 'var(--ink-2)', w: 1.3 }];
    SB_K.forEach(function (k) { var q = { name: sbLab(k[0]), data: R_.map(function (r) { return [r[0], Math.round(r[2] * (r[3] + k[0] * r[4]))]; }), color: k[1], w: k[3] || 1.2 }; if (k[2]) q.dash = k[2]; ser.push(q); });
    ser.splice(1 + SB_K.filter(function (k) { return k[0] > 0; }).length, 0, { name: _T('短期持有者成本', 'STH cost'), data: R_.map(function (r) { return [r[0], r[2]]; }), color: 'var(--s2)', w: 2 });
    lineChart(el, { log: true, h: el.clientWidth < 520 ? 260 : 340, series: ser, tipFmt: fmt.usd, aria: _T('BTC 價格與短期持有者成本帶', 'BTC price and short-term holder cost bands') });
  }


  /* 6–12 與 12–18 個月持幣成本（2026-11-04 使用者要求，6M–12M 與 12M–18M 成本線；資料 Bitview）。
     6–12 個月線跌破 12–18 個月線（死叉）大致在熊底附近，重新升過（金叉）在主升段前後；交叉日與間隔照實列出。只作讀值 */
  function acSay() {
    var x = D.cycle.age_cost, lx = x.last_cross, X = x.crosses || [], it = [], d0 = dnOf(x.date);
    var ym = function (s) { return s.slice(0, 7).replace('-', '/'); }, ago = function (k) { return ym(ds_(d0 - k)); };
    var pairs = X.filter(function (c, i) { return c.kind === 'death' && X[i + 1]; }).map(function (c) { return [c.date, X[X.indexOf(c) + 1].date, c.days_to_next]; });
    var where = x.price < Math.min(x.c612, x.c1218) ? ['兩條線都在收盤上方：這兩批買家都還在虧損。', 'Both lines sit above the close: both groups of buyers are under water.'] : x.price < Math.max(x.c612, x.c1218) ? ['收盤在兩條線之間。', 'The close sits between the two lines.'] : ['收盤在兩條線上方。', 'The close sits above both lines.'];
    it.push([_T('兩條成本線', 'The two cost lines'), fmt.k(x.c612) + ' / ' + fmt.k(x.c1218),
      _T(ago(365) + '–' + ago(182) + ' 買進、到現在沒動的幣，平均成本 ' + fmt.usd(x.c612) + '；再早半年（' + ago(548) + '–' + ago(365) + '）買進的是 ' + fmt.usd(x.c1218) + '，前者' + (x.gap_pct < 0 ? '低 ' : '高 ') + fmt.n(Math.abs(x.gap_pct), 1) + '%。收盤 ' + fmt.usd(x.price) + '，' + where[0],
        'Coins bought ' + ago(365) + '–' + ago(182) + ' and unmoved since cost ' + fmt.usd(x.c612) + ' on average; those from ' + ago(548) + '–' + ago(365) + ' cost ' + fmt.usd(x.c1218) + ', so the first group is ' + fmt.n(Math.abs(x.gap_pct), 1) + '% ' + (x.gap_pct < 0 ? 'lower' : 'higher') + '. Close ' + fmt.usd(x.price) + '. ' + where[1]), x.gap_pct < 0 ? 'neg' : 'pos']);
    if (lx) it.push([_T('上次交叉', 'Last cross'), (lx.kind === 'death' ? _T('死叉 ', 'Death ') : _T('金叉 ', 'Golden ')) + fmt.md(lx.date),
      _T('6–12 個月線在 ' + ymdD(lx.date) + (lx.kind === 'death' ? ' 跌破' : ' 升過') + ' 12–18 個月線，至今 ' + x.days_since + ' 天。過去從死叉到重新金叉：' + pairs.map(function (p) { return ym(p[0]) + '→' + ym(p[1]) + '（' + p[2] + ' 天）'; }).join('、') + '；2020/09→2021/02 那次在疫情急跌之後，一般視為例外。',
        'The 6–12 month line ' + (lx.kind === 'death' ? 'fell below' : 'rose above') + ' the 12–18 month line on ' + ymdD(lx.date) + ', ' + x.days_since + ' days ago. Past death-to-golden gaps: ' + pairs.map(function (p) { return ym(p[0]) + '→' + ym(p[1]) + ' (' + p[2] + ' days)'; }).join(', ') + '; the 2020/09→2021/02 one came after the pandemic crash and is usually treated as an exception.'), 'neu']);
    it.push([_T('怎麼看', 'How to read it'), _T('落後', 'Lagging'),
      _T('兩條線是半年到一年半前的平均買價，比價格落後很多。半年後，12–18 個月這一段會由現在 6–12 個月的這批幣（成本 ' + fmt.usd(x.c612) + '）遞補，只要它們不動，12–18 個月線就會往這個水準移；重新金叉要等那時 6–12 個月段（也就是這半年買進的幣）的成本高過它。',
        'Both lines are average purchase prices from six to eighteen months ago, so they lag price a lot. In six months the 12–18 month band will be filled by today\'s 6–12 month coins (cost ' + fmt.usd(x.c612) + '); if they stay put, the 12–18 month line moves toward that level, and a golden cross needs the coins bought in these six months to cost more than that.'), 'neu']);
    return it;
  }
  // 2026-11-04 使用者要求：加 3–6 個月持幣成本（價格上穿後的天數），和 6–12／12–18 個月放在同一張圖切換
  var acMode = '612';   // 2026-11-06 使用者要求：預設顯示長週期（6–12 vs 12–18 個月）；按鈕由長到短排。頭版「我們的看法」的短期持有者成本不受影響（直接用 acSay1m）
  function acSegs() { var b = function (v, z, e) { return '<button aria-pressed="' + (acMode === v) + '" data-a="' + v + '">' + _T(z, e) + '</button>'; }; return '<span class="seg" id="ac-segs">' + b('612', '6–12 vs 12–18 個月', '6–12 vs 12–18 months') + b('36', '3–6 個月', '3–6 months') + ((D.cycle.age_cost || {}).c1m ? b('1m', '1 週–1 個月', '1w–1m') : '') + '</span>'; }
  function acSay36() {
    var x = D.cycle.age_cost, c = x.c36, it = [], d0 = dnOf(x.date), ym = function (k) { return ds_(d0 - k).slice(0, 7).replace('-', '/'); };
    var U = c.ups || [], bear = U.filter(function (u) { return u.bear; }), cur = bear.length && !bear[bear.length - 1].done ? bear[bear.length - 1] : null, past = bear.filter(function (u) { return u.done; });
    it.push([_T('3–6 個月成本', '3–6 month cost'), fmt.k(c.cost),
      _T(ym(182) + '–' + ym(91) + ' 買進、到現在沒動的幣，平均成本 ' + fmt.usd(c.cost) + '；收盤 ' + fmt.usd(c.price) + '，' + (c.above ? '高 ' : '低 ') + fmt.n(Math.abs(c.gap_pct), 1) + '%。' + (c.chg30 != null ? '這條線 30 天' + (c.chg30 < 0 ? '下降 ' : '上升 ') + fmt.usd(Math.abs(c.chg30)) + (c.chg30 < 0 ? '：價格較低時買進的幣正在進入 3–6 個月這一段。' : '。') : ''),
        'Coins bought ' + ym(182) + '–' + ym(91) + ' and unmoved since cost ' + fmt.usd(c.cost) + ' on average; the close of ' + fmt.usd(c.price) + ' is ' + fmt.n(Math.abs(c.gap_pct), 1) + '% ' + (c.above ? 'above' : 'below') + ' it.' + (c.chg30 != null ? ' The line ' + (c.chg30 < 0 ? 'fell ' : 'rose ') + fmt.usd(Math.abs(c.chg30)) + ' in 30 days' + (c.chg30 < 0 ? ': coins bought at lower prices are moving into the 3–6 month band.' : '.') : '')), c.above ? 'pos' : 'neg']);
    if (c.since) it.push([_T('上穿至今', 'Since the cross'), c.since.days + _T(' 天', ' days'),
      _T('價格 ' + ymdD(c.since.date) + ' 由下往上穿越' + (cur && cur.date === c.since.date ? '（之前在線下 ' + cur.below + ' 天，熊市後的第一次）' : '') + '，至今 ' + c.since.days + ' 天' + (cur ? '；之後最高收盤 ' + fmt.usd(cur.hi.price) + '（' + ymdD(cur.hi.date) + '，第 ' + cur.hi.days + ' 天）。' : '。'),
        'Price crossed above on ' + ymdD(c.since.date) + (cur && cur.date === c.since.date ? ' (after ' + cur.below + ' days below, the first time after the bear market)' : '') + ', ' + c.since.days + ' days ago' + (cur ? '; the highest close since was ' + fmt.usd(cur.hi.price) + ' (' + ymdD(cur.hi.date) + ', day ' + cur.hi.days + ').' : '.')), 'neu']);
    if (past.length) it.push([_T('熊市後的第一次', 'First cross after a bear market'), past.length + _T(' 次', ''),
      _T('之前在線下 250 天以上、第一次站回這條線：' + past.map(function (u) { return ymdD(u.date) + '，半年內最高在第 ' + u.hi.days + ' 天'; }).join('；') + '。常聽到的「上穿後約 80 天到頂」只有 2019 年吻合，2015、2023 年的半年高點都在 170 天以後；其他回到線上的 ' + (U.length - bear.length) + ' 次（線下不到 250 天）是牛市中的回檔結束。',
        'Back above the line after 250+ days below: ' + past.map(function (u) { return ymdD(u.date) + ', six-month high on day ' + u.hi.days; }).join('; ') + '. The oft-cited “about 80 days to the top” only fits 2019; in 2015 and 2023 the six-month high came after day 170. The other ' + (U.length - bear.length) + ' returns above the line (under 250 days below) ended bull-market pullbacks.'), 'neu']);
    return it;
  }
  // 2026-11-05 使用者要求（X 帳號掃描：短期持有者成本）：1 週–1 個月持幣成本
  function acSay1m() {
    var c = D.cycle.age_cost.c1m, it = [];
    it.push([_T('1 週–1 個月成本', '1w–1m cost'), fmt.k(c.cost),
      _T('最近 1 週到 1 個月進場、到現在沒動的人，平均買價 ' + fmt.usd(c.cost) + '；收盤 ' + fmt.usd(c.price) + '，' + (c.above ? '高 ' : '低 ') + fmt.n(Math.abs(c.gap_pct), 1) + '%，從 ' + ymdD(c.since) + ' 起連續 ' + c.days + ' 天在線' + (c.above ? '上' : '下') + '。' + (c.chg30 != null ? '這條線 30 天' + (c.chg30 < 0 ? '下降 ' : '上升 ') + fmt.usd(Math.abs(c.chg30)) + '。' : ''),
        'People who bought 1 week to 1 month ago and still hold paid ' + fmt.usd(c.cost) + ' on average; the close of ' + fmt.usd(c.price) + ' is ' + fmt.n(Math.abs(c.gap_pct), 1) + '% ' + (c.above ? 'above' : 'below') + ' it, for ' + c.days + ' straight days since ' + ymdD(c.since) + '.' + (c.chg30 != null ? ' The line ' + (c.chg30 < 0 ? 'fell ' : 'rose ') + fmt.usd(Math.abs(c.chg30)) + ' in 30 days.' : '')), c.above ? 'pos' : 'neg']);
    if (c.sth) it.push([_T('和短期持有者成本比', 'Vs STH cost'), fmt.pct(c.vs_sth_pct, 1),
      _T('短期持有者（持有不到 155 天的全部）成本是 ' + fmt.usd(c.sth) + '；最近一個月的買家' + (c.vs_sth_pct >= 0 ? '買得比較貴，價格回到短期持有者成本時，他們平均帳面虧損約 ' + fmt.n(Math.abs((c.sth / c.cost - 1) * 100), 1) + '%。' : '買得比較便宜。'),
        'Short-term holders overall (under 155 days) paid ' + fmt.usd(c.sth) + '; the last month\'s buyers ' + (c.vs_sth_pct >= 0 ? 'paid more, so if price returns to the STH cost they would be about ' + fmt.n(Math.abs((c.sth / c.cost - 1) * 100), 1) + '% under water on average.' : 'paid less.')), 'neu']);
    if (!c.above) it.push(viewRow(_T('1 週–1 個月持有者套牢', '1w–1m holders under water'),
      _T('最近一個月進場的人平均虧 ' + fmt.n(Math.abs(c.gap_pct), 1) + '%，已經 ' + c.days + ' 天在線下。反彈到 ' + fmt.usd(c.cost) + ' 附近，這批人回本就想走，賣壓會先出現；在站回去之前，短線偏弱。',
        'The last month\'s buyers are ' + fmt.n(Math.abs(c.gap_pct), 1) + '% under water and have been for ' + c.days + ' days. A bounce to about ' + fmt.usd(c.cost) + ' lets them exit at break-even, so selling shows up there first; short-term soft until that level is reclaimed. '),
      _T('收盤站回 ' + fmt.usd(c.cost) + ' 上方。', 'a close back above ' + fmt.usd(c.cost) + '.'), 'warn'));
    else it.push(viewRow(_T('1 週–1 個月持有者獲利', '1w–1m holders in profit'),
      _T('最近一個月進場的人平均賺 ' + fmt.n(c.gap_pct, 1) + '%：新資金還撐得住，回測 ' + fmt.usd(c.cost) + ' 時這批人通常會守住自己的成本。',
        'The last month\'s buyers are ' + fmt.n(c.gap_pct, 1) + '% in profit: new money is holding up, and on a retest of ' + fmt.usd(c.cost) + ' they tend to defend their cost. '),
      _T('收破 ' + fmt.usd(c.cost) + '。', 'a close below ' + fmt.usd(c.cost) + '.'), 'pos'));
    return it;
  }
  function acSayNow() { return acMode === '1m' ? acSay1m() : acMode === '36' ? acSay36() : acSay(); }
  function acLegend() {
    if (acMode === '1m') return legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('1 週–1 個月成本', '1w–1m cost'), 'var(--s2)']]);
    return acMode === '36' ? legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('3–6 個月成本', '3–6 month cost'), 'var(--s2)'], [_T('↑ 熊市後第一次上穿', '↑ First cross after a bear market'), 'var(--up)', 'dot'], [_T('其他上穿', 'Other crosses'), 'var(--ink-3)', 'dot']])
      : legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('6–12 個月成本', '6–12 month cost'), 'var(--s2)'], [_T('12–18 個月成本', '12–18 month cost'), 'var(--s1)'], [_T('↓ 死叉', '↓ Death cross'), 'var(--down)', 'dot'], [_T('↑ 金叉', '↑ Golden cross'), 'var(--up)', 'dot']]);
  }
  /* 和前幾輪比（2026-11-05 使用者要求，X 帳號掃描）：各輪週期頂部之後每天收盤 ÷ 頂部收盤，畫在同一個「頂部後第幾天」的橫軸上（對數）。只作讀值 */
  var CC_COL = ['var(--ink-3)', 'var(--s1)', 'var(--s3)', 'var(--s2)'];
  function ccSay() {
    var x = D.cycle.cycle_cmp, C = x.cycles || [], cur = C.filter(function (c) { return c.now; })[0], past = C.filter(function (c) { return !c.now; }), it = [], y = function (c) { return c.top.slice(0, 4); };
    if (!cur) return it;
    it.push([_T('頂部後第 ' + x.day_now + ' 天', 'Day ' + x.day_now + ' after the top'), fmt.pct(cur.at.pct, 1),
      _T('這輪頂部 ' + ymdD(cur.top) + ' 收盤 ' + fmt.usd(cur.top_price) + '，今天收盤在它的 ' + fmt.pct(cur.at.pct, 1) + '。前幾輪同一天：' + past.map(function (c) { return y(c) + ' ' + fmt.pct(c.at.pct, 0); }).join('、') + '。',
        'This cycle\'s top closed at ' + fmt.usd(cur.top_price) + ' on ' + ymdD(cur.top) + '; today\'s close is ' + fmt.pct(cur.at.pct, 1) + ' from it. Past cycles on the same day: ' + past.map(function (c) { return y(c) + ' ' + fmt.pct(c.at.pct, 0); }).join(', ') + '.'), 'neu']);
    it.push([_T('最低點', 'Deepest point'), fmt.pct(cur.low.pct, 1),
      _T('這輪到目前最低 ' + fmt.pct(cur.low.pct, 1) + '（第 ' + cur.low.day + ' 天，' + ymdD(cur.low.date) + '）。前幾輪：' + past.map(function (c) { return y(c) + ' ' + fmt.pct(c.low.pct, 1) + '（第 ' + c.low.day + ' 天）'; }).join('、') + '。',
        'This cycle\'s low so far is ' + fmt.pct(cur.low.pct, 1) + ' (day ' + cur.low.day + ', ' + ymdD(cur.low.date) + '). Past cycles: ' + past.map(function (c) { return y(c) + ' ' + fmt.pct(c.low.pct, 1) + ' (day ' + c.low.day + ')'; }).join(', ') + '.'), 'neu']);
    var bk = past.filter(function (c) { return c.back_day; });
    if (bk.length) it.push([_T('回到頂部價', 'Back to the top'), bk.map(function (c) { return c.back_day; }).join(' / ') + _T(' 天', 'd'),
      _T('前幾輪從頂部到重新收上頂部價：' + bk.map(function (c) { return y(c) + ' ' + fmt.n(c.back_day) + ' 天（最低點後 ' + fmt.n(c.back_after_low) + ' 天）'; }).join('、') + '，從最低點回來都比跌下去花得久。這輪還沒回到。只有三輪樣本，這輪的回撤也淺得多，前幾輪的時間不代表這輪會照著走。',
        'Past cycles took this long from the top to close above it again: ' + bk.map(function (c) { return y(c) + ' ' + fmt.n(c.back_day) + ' days (' + fmt.n(c.back_after_low) + ' after the low)'; }).join(', ') + '; the climb back always took longer than the fall. This cycle has not got back yet. Only three past cycles, and this drawdown is much shallower, so their timing is no guide to this one.'), 'neu']);
    var pl = Math.max.apply(null, past.map(function (c) { return c.low.pct; })), lowPx = cur.low.price || Math.round(cur.top_price * (1 + cur.low.pct / 100));
    if (cur.low.pct > pl + 15) it.push(viewRow(_T('不是典型深熊', 'Not a classic deep bear'),
      _T('同一天前幾輪都還在 ' + past.map(function (c) { return fmt.pct(c.at.pct, 0); }).join('、') + '，這輪 ' + fmt.pct(cur.at.pct, 0) + '，最深也只到 ' + fmt.pct(cur.low.pct, 0) + '。四年週期的深熊這輪沒有出現，所以前幾輪「跌一年、爬兩年」的時間表不適合直接套用；我們看這輪更像 ETF 時代的淺週期。',
        'On the same day past cycles were still at ' + past.map(function (c) { return fmt.pct(c.at.pct, 0); }).join(', ') + '; this one is at ' + fmt.pct(cur.at.pct, 0) + ' and never went deeper than ' + fmt.pct(cur.low.pct, 0) + '. The deep four-year-cycle bear did not show up, so the old “a year down, two years back” timetable does not transfer; we read this as a shallower, ETF-era cycle. '),
      _T('收破這輪低點 ' + fmt.usd(lowPx) + '（' + fmt.pct(cur.low.pct, 0) + '），走勢才開始像前幾輪。', 'a close below this cycle\'s low of ' + fmt.usd(lowPx) + ' (' + fmt.pct(cur.low.pct, 0) + '), which is when it would start to look like past cycles.'), 'neu'));
    else it.push(viewRow(_T('和前幾輪相近', 'Tracking past cycles'),
      _T('這輪的回撤已經接近前幾輪（最深 ' + fmt.pct(cur.low.pct, 0) + '，前幾輪 ' + past.map(function (c) { return fmt.pct(c.low.pct, 0); }).join('、') + '），前幾輪的時間表有參考價值，但樣本只有三輪。',
        'This drawdown is close to past cycles (deepest ' + fmt.pct(cur.low.pct, 0) + ' vs ' + past.map(function (c) { return fmt.pct(c.low.pct, 0); }).join(', ') + '), so their timing is a useful reference, though there are only three. '),
      '', 'neu'));
    return it;
  }
  function ccPanel() {
    var x = (D.cycle || {}).cycle_cmp; if (!x || !x.cycles) return '';
    return panel('span-12', _T('和前幾輪比：頂部之後', 'Versus past cycles: after the top'), _T('統一收盤 · ' + fmt.md(x.date), 'standard close · ' + fmt.md(x.date)),
      interpHtml(ccSay()) + legend(x.cycles.map(function (c, i) { return [c.top.slice(0, 4) + (c.now ? _T(' 頂部（這輪）', ' top (this cycle)') : _T(' 頂部', ' top')), CC_COL[(i + CC_COL.length - x.cycles.length) % CC_COL.length]]; }).concat([[_T('頂部價', 'Top price'), 'var(--ink-3)', 'dash']])) + '<div class="chart" id="c-cyccmp"></div>' +
      '<p class="note">' + _T('各輪週期頂部的收盤設為 0%，之後每天收盤相對頂部的位置，畫在同一個「頂部後第幾天」的橫軸上（對數刻度，同樣高度＝同樣的漲跌比例）。頂部日期取自本站的週期頂部表，價格用本站統一收盤。只作讀值，前幾輪的時間不代表這輪會照著走。',
        'Each cycle top\'s close is set to 0%, and every later close is drawn by its distance from that top on a shared “days after the top” axis (log scale, so equal heights are equal percentage moves). Top dates come from the site\'s cycle-top table; prices are the site\'s standard close. A reading only; past timing is no guide to this cycle.') + '</p>');
  }
  function drawCycCmp(el) {
    var x = (D.cycle || {}).cycle_cmp; if (!x || !el) return;
    var n = x.cycles.length, pf = function (v) { var p = (v - 1) * 100; return (p > 0 ? '+' : '') + p.toFixed(0) + '%'; };
    var ser = x.cycles.map(function (c, i) { return { name: c.top.slice(0, 4), data: c.rows, color: CC_COL[(i + CC_COL.length - n) % CC_COL.length], w: c.now ? 2.4 : 1.4, end: c.now }; });
    lineChart(el, { log: true, xType: 'num', h: el.clientWidth < 520 ? 260 : 320, series: ser, refs: [{ y: 1, color: 'var(--ink-3)' }],
      xticks: [[0, _T('頂部', 'top')], [365, _T('1 年', '1y')], [730, _T('2 年', '2y')], [1095, _T('3 年', '3y')]], vlines: [{ x: x.day_now, label: _T('今天', 'today') }],
      xTipFmt: function (d) { return _T('頂部後第 ' + Math.round(d) + ' 天', 'Day ' + Math.round(d) + ' after the top'); }, yFmt: pf, tipFmt: pf, aria: _T('各輪頂部之後的價格對照', 'Price after each cycle top, compared') });
  }
  function acPanel() {
    var x = (D.cycle || {}).age_cost; if (!x || !x.rows) return '';
    if (!x.c36 && acMode === '36' || !x.c1m && acMode === '1m') acMode = '612';
    return panel('span-12', _T('依持有時間的持幣成本', 'Holder cost by coin age'), 'Bitview · ' + fmt.md(x.date),
      '<div id="ac-say">' + interpHtml(acSayNow()) + '</div><div id="ac-lg">' + acLegend() + '</div><div class="chart" id="c-agecost"></div>' +
      '<p class="note">' + _T('持有時間（幣齡）在某一段的幣，各自的平均買價（實現價格）。1 週–1 個月：最近一個月進場者的成本，價格在它下方＝他們整體在虧損。3–6 個月：價格站回這條線＝3–6 個月前進場、到現在沒動的人整體回到獲利。6–12 vs 12–18 個月：常見的讀法是 6–12 個月線跌破 12–18 個月線大致在熊底附近，重新升過在主升段前後。資料 Bitview（Bitcoin Research Kit；6–12 個月由 6–9、9–12 個月合併，3–6 個月由 3–4、4–5、5–6 個月合併），價格用本站統一收盤。',
        'Average purchase price (realized price) of coins in each age band. 1 week–1 month: the cost of the last month\'s entrants; price below it means they are under water as a group. 3–6 months: price back above this line means people who bought 3–6 months ago and still hold are in profit again. 6–12 vs 12–18 months: the usual reading is that the 6–12 month line dropping below the 12–18 month line comes near bear-market bottoms, and crossing back above around the start of the main bull leg. Data from Bitview (Bitcoin Research Kit; 6–12 months combines the 6–9 and 9–12 month bands, 3–6 months the 3–4, 4–5 and 5–6 month bands); price is the site\'s standard close.') + '</p>', x.c36 ? acSegs() : '');
  }
  function drawAgeCost(el) {
    var x = (D.cycle || {}).age_cost; if (!x || !el) return;
    var R_ = x.rows, col = function (r, i) { return R_.map(function (q) { return [q[0], q[i]]; }).filter(function (p) { return p[1] != null; }); }, sm = el.clientWidth < 520, mk;
    if (acMode === '1m') {
      lineChart(el, { log: true, h: sm ? 260 : 340, tipFmt: fmt.usd, aria: _T('BTC 價格與 1 週–1 個月持幣成本', 'BTC price and 1-week–1-month holder cost'),
        series: [{ name: _T('BTC 價格', 'BTC price'), data: col(R_, 1), color: 'var(--ink-2)', w: 1.2 }, { name: _T('1 週–1 個月成本', '1w–1m cost'), data: col(R_, 5), color: 'var(--s2)', w: 2 }] });
      return;
    }
    if (acMode === '36') {
      var U = (x.c36 || {}).ups || [], nb = U.filter(function (u) { return u.bear; }).length, kb = 0;
      mk = U.map(function (u) { var b = u.bear, lab = b ? (++kb, sm && kb < nb ? '' : '↑ ' + u.date.slice(2, 7).replace('-', '/').replace('/0', '/')) : ''; return { x: dnOf(u.date), y: u.cost, label: lab, color: b ? 'var(--up)' : 'var(--ink-3)' }; });
      lineChart(el, { log: true, h: sm ? 260 : 340, marks: mk, tipFmt: fmt.usd, aria: _T('BTC 價格與 3–6 個月持幣成本', 'BTC price and 3–6 month holder cost'),
        series: [{ name: _T('BTC 價格', 'BTC price'), data: col(R_, 1), color: 'var(--ink-2)', w: 1.2 }, { name: _T('3–6 個月成本', '3–6 month cost'), data: col(R_, 4), color: 'var(--s2)', w: 2 }] });
      return;
    }
    var XC = x.crosses || [];   // 手機只標最近一次的日期，其他只畫點（游標看日期）
    mk = XC.map(function (c, i) { var g = c.kind === 'golden'; return { x: dnOf(c.date), y: c.cost, label: sm && i < XC.length - 1 ? '' : (g ? '↑ ' : '↓ ') + c.date.slice(2, 7).replace('-', '/').replace('/0', '/'), color: g ? 'var(--up)' : 'var(--down)', below: !g }; });
    lineChart(el, { log: true, h: sm ? 260 : 340, marks: mk, tipFmt: fmt.usd, aria: _T('BTC 價格與 6–12、12–18 個月持幣成本', 'BTC price and 6–12 / 12–18 month holder cost'),
      series: [{ name: _T('BTC 價格', 'BTC price'), data: col(R_, 1), color: 'var(--ink-2)', w: 1.2 }, { name: _T('6–12 個月成本', '6–12 month cost'), data: col(R_, 2), color: 'var(--s2)', w: 2 }, { name: _T('12–18 個月成本', '12–18 month cost'), data: col(R_, 3), color: 'var(--s1)', w: 2 }] });
  }


  /* 成本線與均線（2026-11-04 使用者要求，Glassnode 週報〈Retesting the Breakout〉）：價格和 200／365 日、50 週均線、短期持有者成本、
     真實市場均價、實現價、長期持有者成本放在同一張圖；均線用統一收盤，成本線用 Bitview。只作讀值 */
  var LV_NAME = { sma200: ['200 日均線', '200-day MA'], sma365: ['365 日均線', '365-day MA'], w50: ['50 週均線', '50-week MA'], sth: ['短期持有者成本', 'STH cost basis'], tmm: ['真實市場均價', 'True market mean'], rp: ['實現價', 'Realized price'], lth: ['長期持有者成本', 'LTH cost basis'], act: ['活躍投資人成本', 'Active investor price'] };
  var LV_COL = { sma200: ['var(--s1)', ''], sma365: ['var(--s4)', ''], w50: ['var(--ink-2)', '5 4'], sth: ['var(--s2)', ''], tmm: ['var(--s3)', ''], rp: ['var(--ink-3)', '5 4'], lth: ['var(--ink-3)', '2 3'], act: ['var(--s2)', '5 4'] };   // 2026-11-05 活躍投資人成本：成本類用橙色，虛線和短期持有者成本區分
  var LV_IDX = { sma200: 2, sma365: 3, w50: 4, sth: 5, tmm: 6, rp: 7, lth: 8, act: 9 };
  function lvName(k) { var n = LV_NAME[k] || LV_NAME[{ sma350: 'w50' }[k]]; return n ? _T(n[0], n[1]) : k; }   // 2026-11-09 前的資料（上一份數字）叫 sma350
  function lvSay() {
    var x = D.cycle.levels, it = [], up = x.levels.filter(function (l) { return l.value > x.price; }), dn = x.levels.filter(function (l) { return l.value <= x.price; }), nr = x.near;
    var li = function (L) { return L.map(function (l) { return lvName(l.key) + ' ' + fmt.usd(l.value) + '（' + fmt.pct(l.dist_pct, 1) + '）'; }).join(_T('、', ', ')); };
    if (up.length) it.push([_T('收盤上方', 'Above the close'), up.length + _T(' 條', ''), _T('收盤 ' + fmt.usd(x.price) + '（' + fmt.md(x.date) + '）上方：' + li(up) + '。', 'Above the ' + fmt.usd(x.price) + ' close (' + fmt.md(x.date) + '): ' + li(up) + '.'), 'neu']);
    if (nr) it.push([_T('下方 ' + nr.pct + '% 內', 'Within ' + nr.pct + '% below'), fmt.k(nr.lo) + '–' + fmt.k(nr.hi), _T('收盤下方 ' + nr.pct + '% 內有 ' + nr.keys.length + ' 條線擠在 ' + fmt.usd(nr.lo) + '–' + fmt.usd(nr.hi) + '：' + nr.keys.map(lvName).join('、') + '。這幾條線是不同買家的平均成本或長期趨勢，重疊的地方常被拿來當支撐看；只是讀值，不代表一定守得住。', nr.keys.length + ' lines sit within ' + nr.pct + '% below the close, between ' + fmt.usd(nr.lo) + ' and ' + fmt.usd(nr.hi) + ': ' + nr.keys.map(lvName).join(', ') + '. They are the average costs of different groups of buyers or long-term trends, and where they overlap is often read as support; a reading only, not a promise it holds.'), 'neu']);
    var far = dn.filter(function (l) { return !nr || nr.keys.indexOf(l.key) < 0; });
    if (far.length) it.push([_T('更下方', 'Further below'), far.length + _T(' 條', ''), _T(li(far) + '。', li(far) + '.'), 'neu']);
    var a = x.act;   // 2026-11-05 活躍投資人成本（Cointime Active Price，Bitview）
    if (a) it.push([lvName('act'), fmt.k(a.value),
      _T('以「幣有多活躍」加權的平均成本，長期不動的幣幾乎不算進去。收盤' + (a.above ? '在它上方 ' : '在它下方 ') + fmt.n(Math.abs(a.dist_pct), 1) + '%；今年 ' + a.ytd_days + ' 天裡收在它上方的有 ' + a.ytd_above + ' 天' + (a.last_above ? '，最近一次是 ' + ymdD(a.last_above) : '') + (a.last_cross ? '；' + ymdD(a.last_cross.date) + (a.last_cross.up ? ' 站上' : ' 跌回下方') : '') + '。',
        'Average cost weighted by how active coins are, so long-dormant coins barely count. The close is ' + fmt.n(Math.abs(a.dist_pct), 1) + '% ' + (a.above ? 'above' : 'below') + ' it; this year ' + a.ytd_above + ' of ' + a.ytd_days + ' days closed above it' + (a.last_above ? ', most recently ' + ymdD(a.last_above) : '') + (a.last_cross ? '; it ' + (a.last_cross.up ? 'moved above' : 'fell back below') + ' on ' + ymdD(a.last_cross.date) : '') + '.'), a.above ? 'pos' : 'neu']);
    var T = lvOf('tmm'), S = lvOf('sth'), c = x.price;
    if (a && T) {
      if (c > a.value) it.push(viewRow(_T('偏多', 'Constructive'),
        _T('收盤站上活躍投資人成本 ' + fmt.usd(a.value) + '：最活躍的那群人整體回到獲利，所有成本線都在下方。今年 ' + a.ytd_days + ' 天只有 ' + a.ytd_above + ' 天做到，這是結構轉強的位置。',
          'The close is above the active investor price of ' + fmt.usd(a.value) + ': the most active holders are back in profit and every cost line sits below. Only ' + a.ytd_above + ' of ' + a.ytd_days + ' days this year managed that, so the structure is turning stronger. '),
        _T('收回 ' + fmt.usd(a.value) + ' 下方。', 'a close back below ' + fmt.usd(a.value) + '.'), 'pos'));
      else if (c > T) it.push(viewRow(_T('區間整理', 'Range'),
        _T('收盤夾在真實市場均價 ' + fmt.usd(T) + '（多空分界）和活躍投資人成本 ' + fmt.usd(a.value) + ' 之間。下方 ' + fmt.k(Math.min(S || T, T)) + '–' + fmt.k(T) + ' 是短期持有者成本和真實市場均價，跌到這裡這兩群人回到成本、通常有人守；上方 ' + fmt.k(a.value) + ' 是今年的天花板（' + a.ytd_days + ' 天只有 ' + a.ytd_above + ' 天站上）。多頭結構還在，但這是區間整理，還不是新一段上漲。',
          'The close sits between the true market mean of ' + fmt.usd(T) + ' (the bull/bear line) and the active investor price of ' + fmt.usd(a.value) + '. Below, ' + fmt.k(Math.min(S || T, T)) + '–' + fmt.k(T) + ' holds the short-term holder cost and the true market mean, where those buyers break even and which usually gets defended; above, ' + fmt.k(a.value) + ' has been this year\'s ceiling (only ' + a.ytd_above + ' of ' + a.ytd_days + ' days closed above). The bull structure holds, but this is a range, not a new leg up. '),
        _T('收盤站上 ' + fmt.usd(a.value) + ' 轉偏多；收破 ' + fmt.usd(T) + ' 轉偏空。', 'a close above ' + fmt.usd(a.value) + ' turns it constructive; a close below ' + fmt.usd(T) + ' turns it bearish.'), 'neu'));
      else it.push(viewRow(_T('偏空', 'Bearish'),
        _T('收盤跌破真實市場均價 ' + fmt.usd(T) + '：活躍投資人整體轉為虧損，這條線歷來是多空分界。站回去之前，我們看偏空。',
          'The close is below the true market mean of ' + fmt.usd(T) + ': active investors as a group are under water, and this line has long separated bull and bear phases. Bearish until it is reclaimed. '),
        _T('收回 ' + fmt.usd(T) + ' 上方。', 'a close back above ' + fmt.usd(T) + '.'), 'neg'));
    }
    return it;
  }
  function lvPanel() {
    var x = (D.cycle || {}).levels; if (!x || !x.rows) return '';
    return panel('span-12', _T('成本線與均線', 'Cost bases and moving averages'), _T('均線：統一收盤 · 成本線：Bitview · ' + fmt.md(x.date), 'MAs: standard close · cost bases: Bitview · ' + fmt.md(x.date)),
      interpHtml(lvSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink)']].concat(Object.keys(LV_NAME).map(function (k) { return [lvName(k), LV_COL[k][0], LV_COL[k][1] ? 'dash' : '']; }))) + '<div class="chart" id="c-levels"></div>' +
      '<p class="note">' + _T('均線用本站統一收盤；50 週均線照週線圖的算法：週日的收盤是週收盤，最近 49 根週 K 的收盤加上當天收盤再平均，週日那天就是正式的週線值。短期持有者成本（持有不到 155 天的幣的平均買價）、真實市場均價（排除長期不動的幣後活躍投資人的平均成本）、實現價（全體持有者的平均成本）、長期持有者成本、活躍投資人成本（Cointime 的 Active Price：依幣的活躍程度加權，長期不動的幣幾乎不算）都來自 Bitview。',
        'Moving averages use the site\'s standard close; the 50-week MA follows the weekly chart: Sunday\'s close is the weekly close, and each day averages the last 49 weekly closes with that day\'s close, so on Sundays it is the official weekly value. The short-term holder cost basis (average purchase price of coins held under 155 days), true market mean (average cost of active investors, excluding long-dormant coins), realized price (average cost of all holders), long-term holder cost basis and active investor price (Cointime Active Price: weighted by how active coins are, so dormant coins barely count) come from Bitview.') + '</p>');
  }
  function drawLevels(el) {
    var x = (D.cycle || {}).levels; if (!x || !el) return;
    var R_ = x.rows, ser = [{ name: _T('BTC 價格', 'BTC price'), data: R_.map(function (r) { return [r[0], r[1]]; }), color: 'var(--ink)', w: 1.4 }];
    Object.keys(LV_NAME).forEach(function (k) { var q = { name: lvName(k), data: R_.map(function (r) { return [r[0], r[LV_IDX[k]]]; }).filter(function (p) { return p[1] != null; }), color: LV_COL[k][0], w: k === 'sth' || k === 'tmm' ? 1.8 : 1.3 }; if (LV_COL[k][1]) q.dash = LV_COL[k][1]; ser.push(q); });
    lineChart(el, { h: el.clientWidth < 520 ? 280 : 360, series: ser, tipFmt: fmt.usd, aria: _T('BTC 價格與成本線、均線', 'BTC price with cost bases and moving averages') });
  }

  /* BTC 對美股（2026-11-04 使用者要求，Glassnode 週報）：近 90 個美股交易日的勝率與每日平均超額；近兩個月和 S&P 500、那斯達克、黃金的相對表現。只作讀值 */
  function stkSay() {
    var x = D.flows.btc_vs_stocks, L = x.rel.last, it = [];
    it.push([_T('90 日勝率', '90-session win rate'), fmt.n(x.win90, 0) + '%', _T('近 90 個美股交易日，BTC 漲幅大於 S&P 500 的有 ' + fmt.n(x.win90, 0) + '%，每天平均' + (x.excess90 >= 0 ? '多 ' : '少 ') + fmt.n(Math.abs(x.excess90), 2) + ' 個百分點。' + (x.win90 > 50 ? '' : x.last_above50 ? '上一次高於 50% 是 ' + ymdD(x.last_above50) + '。' : ''),
      'Over the last 90 US sessions BTC beat the S&P 500 in ' + fmt.n(x.win90, 0) + '% of them, by ' + (x.excess90 >= 0 ? '+' : '−') + fmt.n(Math.abs(x.excess90), 2) + ' points a day on average.' + (x.win90 > 50 ? '' : x.last_above50 ? ' It was last above 50% on ' + ymdD(x.last_above50) + '.' : '')), x.win90 > 50 ? 'pos' : 'neu']);
    var f = function (v) { return v == null ? '—' : fmt.pct(v, 1); };
    it.push([_T('近兩個月', 'Last two months'), f(L.btc), _T('自 ' + ymdD(x.rel.start) + '：BTC ' + f(L.btc) + '、S&P 500 ' + f(L.spx) + '、那斯達克 ' + f(L.ndq) + '、黃金 ' + f(L.gold) + '（PAXG 代替）。', 'Since ' + ymdD(x.rel.start) + ': BTC ' + f(L.btc) + ', S&P 500 ' + f(L.spx) + ', Nasdaq ' + f(L.ndq) + ', gold ' + f(L.gold) + ' (PAXG as a proxy).'), 'neu']);
    return it;
  }
  function stkPanel() {
    var x = D.flows.btc_vs_stocks; if (!x || !x.rows) return '';
    return panel('span-12', _T('BTC 對美股', 'BTC vs stocks'), 'FRED · Kraken · ' + fmt.md(x.date), interpHtml(stkSay()) +
      '<div class="panel-h" style="margin-top:10px"><h2>' + _T('近兩個月漲跌', 'Change over two months') + '</h2>' + legend([['BTC', 'var(--s2)'], ['S&P 500', 'var(--ink)'], [_T('那斯達克', 'Nasdaq'), 'var(--s1)'], [_T('黃金（PAXG）', 'Gold (PAXG)'), 'var(--s4)']]) + '</div><div class="chart" id="c-stkrel"></div>' +
      '<div class="panel-h" style="margin-top:14px"><h2>' + _T('BTC 贏過 S&P 500 的比例（近 90 個交易日）', 'Share of sessions BTC beat the S&P 500 (90 sessions)') + '</h2></div><div class="chart" id="c-stkwin"></div>' +
      '<p class="note">' + _T('勝率＝近 90 個美股交易日裡，BTC 當天漲幅大於 S&P 500 的比例；BTC 用 UTC 日收盤、美股用紐約收盤，兩者差約 3 小時。黃金用 Kraken 的 PAXG（一枚代表一盎司黃金的代幣）代替金價。歐股沒有免費的每日資料，沒有列入。',
        'Win rate = share of the last 90 US sessions in which BTC rose more than the S&P 500; BTC uses the UTC daily close and stocks the New York close, about 3 hours apart. Gold uses Kraken\'s PAXG (a token backed by one ounce of gold) as a proxy. European stocks are left out for lack of free daily data.') + '</p>');
  }
  function drawStk() {
    var x = D.flows.btc_vs_stocks; if (!x) return;
    var R_ = x.rel.rows, col = function (i) { return R_.map(function (r) { return [r[0], r[i]]; }).filter(function (p) { return p[1] != null; }); }, pf = function (v) { return fmt.pct(v, 1); };
    mount($('#c-stkrel'), function (el) { lineChart(el, { h: 220, series: [{ name: 'BTC', data: col(1), color: 'var(--s2)', w: 1.8 }, { name: 'S&P 500', data: col(2), color: 'var(--ink)', w: 1.4 }, { name: _T('那斯達克', 'Nasdaq'), data: col(3), color: 'var(--s1)', w: 1.4 }, { name: _T('黃金（PAXG）', 'Gold (PAXG)'), data: col(4), color: 'var(--s4)', w: 1.4 }], refs: [{ y: 0, color: 'var(--ink-3)' }], yFmt: function (v) { return fmt.pct(v, 0); }, tipFmt: pf, aria: _T('近兩個月漲跌', 'Change over two months') }); });
    mount($('#c-stkwin'), function (el) { lineChart(el, { h: 200, series: [{ name: _T('90 日勝率', '90-session win rate'), data: x.rows.map(function (r) { return [r[0], r[1]]; }), color: 'var(--s4)', w: 1.6, area: true }], refs: [{ y: 50, color: 'var(--ink-3)', label: '50%' }], yFmt: function (v) { return fmt.n(v, 0) + '%'; }, tipFmt: function (v) { return fmt.n(v, 1) + '%'; }, aria: _T('BTC 贏過 S&P 500 的比例', 'Share of sessions BTC beat the S&P 500') }); });
  }

  /* 循環資金流（2026-11-05 使用者要求，Look Into Bitcoin〈Bitcoin Cycle Capital Flows〉；資料 Bitview）。
     第一張照「對外展示、抓眼球」新規則做的圖（docs/chart-style.md）：大字讀數、漸層面積、發光線、頂部／熊底底色、峰值標籤、現在的脈動點。只作讀值 */
  var CF_M1 = 'var(--s2)', CF_Y12 = 'var(--s1)';
  function cfPct(v) { return v == null ? '—' : fmt.n(v, 1) + '%'; }
  function cfSay() {
    var x = D.onchain.capflow, it = [], pm = x.peaks_m1 || [], py = (x.peaks_y12 || []).filter(function (p) { return p[0] !== x.date; });
    var yr = function (p) { return p[0].slice(0, 7).replace('-', '/') + ' ' + fmt.n(p[1], 0) + '%'; };
    it.push([_T('1–2 年沒動', 'Unmoved 1–2 years'), cfPct(x.y12), _T('一年前到兩年前買進、到現在沒動的幣，佔全體實現市值 ' + cfPct(x.y12) + '（一年前 ' + cfPct(x.y12_1y) + '、30 天前 ' + cfPct(x.y12_30) + '）。這一塊在熊底附近最大：' + py.map(yr).join('、') + '。現在升高，主要是 2024–25 年高價買進的幣放滿一年還沒賣，是時間推移，不全代表信心。',
      'Coins bought one to two years ago and unmoved since make up ' + cfPct(x.y12) + ' of realized cap (' + cfPct(x.y12_1y) + ' a year ago, ' + cfPct(x.y12_30) + ' 30 days ago). This share peaks near bear-market bottoms: ' + py.map(yr).join(', ') + '. The rise now mostly reflects coins bought at high prices in 2024–25 turning one year old unsold; it is partly the passage of time, not pure conviction.'), x.y12 >= 25 ? 'pos' : 'neu']);
    it.push([_T('1 個月內換手', 'Moved within a month'), cfPct(x.m1), _T('最近一個月換手的幣佔 ' + cfPct(x.m1) + '（一年前 ' + cfPct(x.m1_1y) + '）。過去週期頂部這一塊衝得很高：' + pm.filter(function (p) { return p[1] >= 40; }).map(yr).join('、') + '；這一輪最高只到 ' + yr(pm[pm.length - 1]) + '，2025 年頂部沒有出現前兩輪那種投機狂熱。',
      'Coins that changed hands in the last month make up ' + cfPct(x.m1) + ' (' + cfPct(x.m1_1y) + ' a year ago). At past cycle tops this share spiked: ' + pm.filter(function (p) { return p[1] >= 40; }).map(yr).join(', ') + '; this cycle it only reached ' + yr(pm[pm.length - 1]) + ' — the 2025 top had none of the earlier speculative frenzy.'), x.m1 >= 40 ? 'warn' : 'neu']);
    return it;
  }
  function cfPanel() {
    var x = (D.onchain || {}).capflow; if (!x || !x.rows) return '';
    var card = function (col, k, v, sub, dlt) { return '<div class="cf-card" style="--c:' + col + '"><span class="k"><i></i>' + k + '</span><b>' + v + '</b><span class="d">' + dlt + '</span><span class="s">' + sub + '</span></div>'; };
    var arrow = function (a, b) { if (a == null || b == null) return ''; var d = a - b; return '<em class="' + (d >= 0 ? 'up' : 'dn') + '">' + (d >= 0 ? '▲ ' : '▼ ') + fmt.n(Math.abs(d), 1) + _T(' 個百分點 / 30 天', ' pts / 30d') + '</em>'; };
    var py = (x.peaks_y12 || []).filter(function (p) { return p[0] !== x.date && p[1] >= 40; }).map(function (p) { return p[1]; }), pm = (x.peaks_m1 || []).filter(function (p) { return p[1] >= 40; });
    var rng = py.length ? fmt.n(Math.min.apply(null, py), 0) + '–' + fmt.n(Math.max.apply(null, py), 0) + '%' : '—', pms = pm.map(function (p) { return p[0].slice(0, 4) + ' ' + fmt.n(p[1], 0) + '%'; }).join(_T('、', ', '));
    var hero = '<div class="cf-hero">' + card(CF_Y12, _T('1–2 年沒動（長線）', 'Unmoved 1–2y (conviction)'), cfPct(x.y12), _T('過去熊底附近最高 ' + rng, 'Past bottoms peaked at ' + rng), arrow(x.y12, x.y12_30)) +
      card(CF_M1, _T('1 個月內換手（投機）', 'Moved < 1 month (speculation)'), cfPct(x.m1), _T('過去頂部 ' + pms, 'Past tops: ' + pms), arrow(x.m1, x.m1_30)) + '</div>';
    return panel('span-12', _T('循環資金流：投機 vs 長線', 'Cycle capital flows: speculation vs conviction'), 'Bitview · ' + fmt.md(x.date),
      hero + interpHtml(cfSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink)'], [_T('1 個月內換手', 'Moved < 1 month'), CF_M1, 'box'], [_T('1–2 年沒動', 'Unmoved 1–2 years'), CF_Y12, 'box'], [_T('週期頂部', 'Cycle top'), 'var(--warn)', 'box'], [_T('熊市底部', 'Bear-market bottom'), 'var(--s3)', 'box']]) +
      '<div class="chart cf-chart" id="c-capflow"></div>' +
      '<p class="note">' + _T('按實現市值（每顆幣的買進成本）算各持有時間佔的比例，不是按顆數：高價買進的幣權重較大。紅橘＝最近一個月換手的幣（投機、新錢），藍紫＝一到兩年沒動的幣（循環投資人）。資料 Bitview，和原圖（Look Into Bitcoin）的數字一致。',
        'Shares by realized cap (each coin weighted by its purchase cost), not by coin count, so coins bought at high prices weigh more. Orange = coins moved in the last month (speculation, new money); violet = coins unmoved for one to two years (cycle investors). Data from Bitview; the numbers match the original chart (Look Into Bitcoin).') + '</p>');
  }
  function drawCapflow(el) {
    var x = (D.onchain || {}).capflow; if (!x || !el) return;
    var R_ = x.rows, W = Math.max(280, el.clientWidth), sm = W < 520, ML = 8, MR = 52, MT = 18, hp = sm ? 92 : 120, gap = 24, hs = sm ? 200 : 270, MB = 24, Ht = MT + hp + gap + hs + MB, pw = W - ML - MR, ys0 = MT + hp + gap;
    var x0 = R_[0][0], x1 = R_[R_.length - 1][0], X = function (t) { return ML + (t - x0) / (x1 - x0 || 1) * pw; }, L = Math.log10, s = '', uid = 'cf' + Math.random().toString(36).slice(2, 7);
    var pv = R_.filter(function (r) { return r[1]; }), pl = L(Math.min.apply(null, pv.map(function (r) { return r[1]; }))), ph = L(Math.max.apply(null, pv.map(function (r) { return r[1]; }))), pp = (ph - pl) * 0.06; pl -= pp; ph += pp;
    var Yp = function (v) { return MT + (1 - (L(v) - pl) / (ph - pl)) * hp; }, top = 70, Ys = function (v) { return ys0 + (1 - v / top) * hs; };
    var tx = function (xx, y, t, a, cls, st) { return '<text class="' + (cls || 'ax') + '" x="' + xx.toFixed(1) + '" y="' + y.toFixed(1) + '"' + (a ? ' text-anchor="' + a + '"' : '') + (st ? ' style="' + st + '"' : '') + '>' + esc(t) + '</text>'; };
    // 漸層與發光
    s += '<defs><linearGradient id="' + uid + 'a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + CF_M1 + '" stop-opacity=".7"/><stop offset="1" stop-color="' + CF_M1 + '" stop-opacity=".04"/></linearGradient>' +
      '<linearGradient id="' + uid + 'b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + CF_Y12 + '" stop-opacity=".6"/><stop offset="1" stop-color="' + CF_Y12 + '" stop-opacity=".05"/></linearGradient>' +
      '<filter id="' + uid + 'g" x="-5%" y="-20%" width="110%" height="140%"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>';
    // 週期頂部／熊底的底色帶（各 ±45 天）
    var band = function (d, col, lab) { var c0 = X(dnOf(d) - 45), c1 = X(dnOf(d) + 45); if (c1 < ML || c0 > ML + pw) return ''; c0 = Math.max(ML, c0); c1 = Math.min(ML + pw, c1); return '<rect x="' + c0.toFixed(1) + '" y="' + MT + '" width="' + (c1 - c0).toFixed(1) + '" height="' + (ys0 + hs - MT) + '" fill="' + col + '" opacity=".13"/>' + (sm ? '' : tx((c0 + c1) / 2, MT - 6, lab, 'middle', 'ax', 'fill:' + col)); };
    (D.cycle.tops || []).forEach(function (t) { s += band(t[0], 'var(--warn)', _T('頂', 'Top')); });
    (D.cycle.bottoms || []).forEach(function (b) { s += band(b[0], 'var(--s3)', _T('底', 'Low')); });
    [10, 100, 1e3, 1e4, 1e5].forEach(function (t) { if (L(t) < pl || L(t) > ph) return; var y = Yp(t); s += '<line class="gl" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/>' + tx(ML + pw + 8, y + 3.5, t >= 1000 ? fmt.k(t) : '$' + t); });
    for (var g = 0; g <= top; g += sm ? 35 : 10) { var yg = Ys(g); s += '<line class="' + (g ? 'gl' : 'base') + '" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + yg.toFixed(1) + '" y2="' + yg.toFixed(1) + '"/>' + tx(ML + pw + 8, yg + 3.5, g + '%'); }
    var area = function (i, fill) { var pts = R_.map(function (r) { return X(r[0]).toFixed(1) + ',' + Ys(r[i]).toFixed(1); }); return '<path d="M' + X(x0).toFixed(1) + ',' + Ys(0).toFixed(1) + 'L' + pts.join('L') + 'L' + X(x1).toFixed(1) + ',' + Ys(0).toFixed(1) + 'Z" fill="url(#' + fill + ')"/>'; };
    var line = function (i, col, w, Y) { return '<path class="ln" d="M' + R_.filter(function (r) { return r[i] != null; }).map(function (r) { return X(r[0]).toFixed(1) + ',' + (Y || Ys)(r[i]).toFixed(1); }).join('L') + '" stroke="' + col + '" stroke-width="' + w + '" filter="url(#' + uid + 'g)"/>'; };
    s += area(3, uid + 'b') + area(2, uid + 'a') + line(3, CF_Y12, 2) + line(2, CF_M1, 2);
    s += '<path class="ln" d="M' + pv.map(function (r) { return X(r[0]).toFixed(1) + ',' + Yp(r[1]).toFixed(1); }).join('L') + '" stroke="var(--ink)" stroke-width="1.4"/>';
    s += tx(ML, MT - 6 + (sm ? 0 : 0), '', '', 'ax') + tx(ML, ys0 - 8, _T('佔全體實現市值', 'Share of realized cap'));
    // 峰值標籤（膠囊）
    var pill = function (d, v, col, up) { var cx = X(dnOf(d)), cy = Ys(v), t = d.slice(0, 4) + ' ' + fmt.n(v, 0) + '%', w = t.length * 6.4 + 12, by = up ? cy - 26 : cy + 10, bx = Math.min(Math.max(cx - w / 2, ML), ML + pw - w);
      return '<line x1="' + cx.toFixed(1) + '" x2="' + cx.toFixed(1) + '" y1="' + cy.toFixed(1) + '" y2="' + (up ? by + 18 : by).toFixed(1) + '" stroke="' + col + '" stroke-width="1"/><rect x="' + bx.toFixed(1) + '" y="' + by.toFixed(1) + '" width="' + w.toFixed(1) + '" height="18" rx="9" fill="' + col + '"/>' + tx(bx + w / 2, by + 12.5, t, 'middle', 'cf-pill') + '<circle cx="' + cx.toFixed(1) + '" cy="' + cy.toFixed(1) + '" r="3.5" fill="' + col + '" stroke="var(--deck)" stroke-width="1.5"/>'; };
    if (!sm) { (x.peaks_m1 || []).filter(function (p) { return p[1] >= 30; }).forEach(function (p) { s += pill(p[0], p[1], CF_M1, true); }); (x.peaks_y12 || []).filter(function (p) { return p[0] !== x.date && p[1] >= 40; }).forEach(function (p) { s += pill(p[0], p[1], CF_Y12, true); }); }
    // 現在：脈動點＋數值
    var lx = X(x1), lr = R_[R_.length - 1];
    s += '<circle class="cf-pulse" cx="' + lx.toFixed(1) + '" cy="' + Ys(lr[3]).toFixed(1) + '" r="5" fill="' + CF_Y12 + '"/><circle cx="' + lx.toFixed(1) + '" cy="' + Ys(lr[3]).toFixed(1) + '" r="4.5" fill="' + CF_Y12 + '" stroke="var(--deck)" stroke-width="2"/>' +
      '<circle cx="' + lx.toFixed(1) + '" cy="' + Ys(lr[2]).toFixed(1) + '" r="4" fill="' + CF_M1 + '" stroke="var(--deck)" stroke-width="2"/>' + tx(lx - 8, Ys(lr[3]) - 9, _T('現在 ', 'Now ') + fmt.n(lr[3], 1) + '%', 'end', 'cf-now', 'fill:' + CF_Y12);
    var y0 = new Date(x0 * 864e5).getUTCFullYear() + 1, y1 = new Date(x1 * 864e5).getUTCFullYear(), every = sm ? 3 : W < 900 ? 2 : 1;
    for (var y = y0; y <= y1; y++) { var xx = X(Date.UTC(y, 0, 1) / 864e5); if ((y - y0) % every === 0 && xx > ML + 14 && xx < ML + pw - 14) s += tx(xx, Ht - 6, String(y), 'middle'); }
    s += '<line class="xh" x1="0" x2="0" y1="' + MT + '" y2="' + (ys0 + hs) + '" visibility="hidden"/><g class="hdots"></g><rect class="hit" x="' + ML + '" y="' + MT + '" width="' + pw + '" height="' + (ys0 + hs - MT) + '"/>';
    el.innerHTML = svgEl(W, Ht, s, _T('BTC 價格與循環資金流', 'BTC price and cycle capital flows'));
    animateLines(el);
    var svg = el.querySelector('svg'), xh = svg.querySelector('.xh'), dots = svg.querySelector('.hdots'), hit = svg.querySelector('.hit');
    function move(ev) {
      var r = svg.getBoundingClientRect(), xv = x0 + ((ev.clientX - r.left) * W / r.width - ML) / pw * (x1 - x0), p = R_[bisect(R_, xv)], cx = X(p[0]).toFixed(1);
      xh.setAttribute('x1', cx); xh.setAttribute('x2', cx); xh.setAttribute('visibility', 'visible');
      dots.innerHTML = '<circle cx="' + cx + '" cy="' + Ys(p[3]).toFixed(1) + '" r="4" fill="' + CF_Y12 + '" stroke="var(--deck)" stroke-width="2"/><circle cx="' + cx + '" cy="' + Ys(p[2]).toFixed(1) + '" r="4" fill="' + CF_M1 + '" stroke="var(--deck)" stroke-width="2"/>' + (p[1] ? '<circle cx="' + cx + '" cy="' + Yp(p[1]).toFixed(1) + '" r="3.5" fill="var(--ink)" stroke="var(--deck)" stroke-width="2"/>' : '');
      showTip(ev.clientX, ev.clientY, '<div class="t">' + fmt.date(p[0]) + '</div>' + tipRow1(CF_Y12, _T('1–2 年沒動', 'Unmoved 1–2y'), cfPct(p[3])) + tipRow1(CF_M1, _T('1 個月內換手', 'Moved < 1 month'), cfPct(p[2])) + (p[1] ? tipRow1('var(--ink)', _T('BTC 價格', 'BTC price'), fmt.usd(p[1])) : ''));
    }
    hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', function () { xh.setAttribute('visibility', 'hidden'); dots.innerHTML = ''; hideTip(); });
  }

  /* ===== 2026-11-06 使用者要求：指標擴充（用本站自己的資料，pipeline/oc_extra.py、opt_flow.py）。
     第一批：供給分位成本線、短期持有者虧損比例的歷次（併進「短期持有者獲利比例」）、相對未實現獲利的地板（週期版）、實現虧損峰值背離、長短期供給比 30 日變化。
     第二批：資金與價格增量梯度、鏈上勢能、籌碼缺口與雙錨（併進籌碼分布）、回調壓力清單。第三批（衍生品版）：Gamma 曝險、選擇權買方權利金差、OKX 現貨主動買賣差。
     圖照 docs/chart-style.md：大字讀數卡、漸層面積＋發光線、歷史膠囊、現在的脈動點；上格價格、下格指標。全部只作讀值、不是買賣訊號 ===== */
  function oxTicks(lo, hi, n) { var st = niceStep(hi - lo, n || 4), a = []; for (var t = Math.ceil(lo / st) * st; t <= hi + 1e-9; t += st) a.push(+t.toFixed(8)); return a; }
  function oxSeg(R_, i, X, Y) { var d = '', on = false; R_.forEach(function (r) { if (r[i] == null) { on = false; return; } d += (on ? 'L' : 'M') + X(r[0]).toFixed(1) + ',' + Y(r[i]).toFixed(1); on = true; }); return d; }
  function oxPill(cx, cy, t, col, up, ML, pw) {
    var w = t.length * 6.3 + 12, by = up ? cy - 26 : cy + 8, bx = Math.min(Math.max(cx - w / 2, ML), ML + pw - w);
    return '<line x1="' + cx.toFixed(1) + '" x2="' + cx.toFixed(1) + '" y1="' + cy.toFixed(1) + '" y2="' + (up ? by + 18 : by).toFixed(1) + '" stroke="' + col + '" stroke-width="1"/><rect x="' + bx.toFixed(1) + '" y="' + by.toFixed(1) + '" width="' + w.toFixed(1) + '" height="18" rx="9" fill="' + col + '"/>' + axText(bx + w / 2, by + 12.5, t, 'middle', 'cf-pill') + '<circle cx="' + cx.toFixed(1) + '" cy="' + cy.toFixed(1) + '" r="3.5" fill="' + col + '" stroke="var(--deck)" stroke-width="1.5"/>';
  }
  function oxNow(cx, cy, col, lab) { return '<circle class="cf-pulse" cx="' + cx.toFixed(1) + '" cy="' + cy.toFixed(1) + '" r="5" fill="' + col + '"/><circle cx="' + cx.toFixed(1) + '" cy="' + cy.toFixed(1) + '" r="4.5" fill="' + col + '" stroke="var(--deck)" stroke-width="2"/>' + (lab ? axText(cx - 9, cy - 9, lab, 'end', 'cf-now').replace('<text', '<text style="fill:' + col + '"') : ''); }
  function oxCard(col, k, v, sub, dlt) { return '<div class="cf-card" style="--c:' + col + '"><span class="k"><i></i>' + k + '</span><b>' + v + '</b><span class="d">' + (dlt || '') + '</span><span class="s">' + (sub || '') + '</span></div>'; }
  function oxArrow(a, b, unit, dg) { if (a == null || b == null) return ''; var d = a - b; return '<em class="' + (d >= 0 ? 'up' : 'dn') + '">' + (d >= 0 ? '▲ ' : '▼ ') + fmt.n(Math.abs(d), dg == null ? 1 : dg) + (unit || '') + '</em>'; }
  function oxP0(v) { return v == null ? '—' : fmt.pct(Math.abs(v) < 0.5 ? 0 : v, 0); }
  function oxUsd(v) { return v == null ? '—' : Math.abs(v) >= 1e9 ? '$' + fmt.n(v / 1e9, 2) + 'B' : '$' + fmt.n(v / 1e6, 0) + 'M'; }
  function oxYm(d) { return d ? d.slice(0, 7).replace('-', '/') : '—'; }
  function oxStat(s, base) { return s && s.n ? _T(s.up + '/' + s.n + ' 次上漲、中位數 ' + fmt.pct(s.med, 1) + (base ? '（同期任一天 ' + base.up + '% 上漲、中位數 ' + fmt.pct(base.med, 1) + '）' : ''), s.up + ' of ' + s.n + ' rose, median ' + fmt.pct(s.med, 1) + (base ? ' (any day: ' + base.up + '% rose, median ' + fmt.pct(base.med, 1) + ')' : '')) : _T('樣本不足', 'too few cases'); }
  /* 上格價格、下格指標（共用 twoPane）。lines：[{i, col, w, name, area, split:[正色, 負色], dash}]；bars：{i, pos, neg, name, col(r)}；
     refs：[{y, col, lab}]；zones：[{y0, y1, col, op}]；marks：[{x, y, col, t, up}]；now：{i, col, lab}；tf：刻度轉換（給大範圍的指標，ticks 用原值） */
  function oxPane(el, o) {
    var R_ = o.rows; if (!R_ || R_.length < 2) { el.innerHTML = '<p class="note">' + _T('本日未取得資料。', 'No data today.') + '</p>'; return; }
    if (o.rng && el._rng == null) el._rng = o.rng;   // 預設時間範圍（天）；使用者點了別的就照點的
    var rg0 = o.fit ? rangeOf(el, { series: [{ data: R_.map(function (r) { return [r[0], 1]; }) }] }, Math.max(280, el.clientWidth)) : null;
    var tf = o.tf || function (v) { return v; }, vals = [], VR = rg0 && rg0.x0 != null ? R_.filter(function (r) { return r[0] >= rg0.x0; }) : R_;   // fit：縱軸只看目前畫出來的範圍（2026-11-06；11-08 改成和 twoPane 同一個判斷：手機沒有範圍切換、畫全部時縱軸也看全部）
    (o.lines || []).forEach(function (l) { VR.forEach(function (r) { if (r[l.i] != null) vals.push(tf(r[l.i])); }); });
    var BS = [].concat(o.bars || []);   // 2026-11-08：bars 可以是陣列（每日多空清算量：空單往上、多單往下）
    BS.forEach(function (b) { VR.forEach(function (r) { if (r[b.i] != null) vals.push(tf(r[b.i])); }); });
    (o.refs || []).forEach(function (f) { vals.push(tf(f.y)); });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    if (o.zero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
    var pad = (hi - lo) * 0.07 || 1; lo = o.y0 != null ? tf(o.y0) : lo - pad; hi = o.y1 != null ? tf(o.y1) : hi + pad;
    var uid = 'ox' + Math.random().toString(36).slice(2, 7), nm = function (l) { return l.name || ''; };
    twoPane(el, { rows: R_, pi: 1, hp: o.hp || [96, 124], hs: o.hs || [150, 200], label: o.label, aria: o.aria,
      scale: function (C) { return function (v) { return C.ys0 + (1 - (tf(v) - lo) / (hi - lo)) * C.hs; }; },
      body: function (C) {
        var s = '<defs>';   // 2026-11-06 使用者：「淺色背景下發光很油、有點髒」→ 不再自加模糊濾鏡，發光只用全站 CSS（夜刊才有）
        (o.lines || []).forEach(function (l, k) {
          (l.split || [l.col]).forEach(function (c, j) { s += '<linearGradient id="' + uid + 'a' + k + j + '" x1="0" y1="' + (j ? 1 : 0) + '" x2="0" y2="' + (j ? 0 : 1) + '"><stop offset="0" stop-color="' + c + '" stop-opacity=".62"/><stop offset="1" stop-color="' + c + '" stop-opacity=".05"/></linearGradient>'; });
        });
        var y0 = C.Ys(0), yt = C.ys0, yb = C.yb;
        s += '<clipPath id="' + uid + 'cu"><rect x="0" y="' + yt + '" width="' + C.W + '" height="' + Math.max(0, Math.min(yb, y0) - yt).toFixed(1) + '"/></clipPath><clipPath id="' + uid + 'cd"><rect x="0" y="' + Math.max(yt, y0).toFixed(1) + '" width="' + C.W + '" height="' + Math.max(0, yb - Math.max(yt, y0)).toFixed(1) + '"/></clipPath></defs>';
        (o.zones || []).forEach(function (z) { var a = C.Ys(z.y1), b = C.Ys(z.y0), t1 = Math.max(yt, Math.min(a, b)), t2 = Math.min(yb, Math.max(a, b)); if (t2 > t1) s += '<rect x="' + C.ML + '" y="' + t1.toFixed(1) + '" width="' + C.pw + '" height="' + (t2 - t1).toFixed(1) + '" fill="' + z.col + '" opacity="' + (z.op || 0.14) + '"/>'; });
        (o.vbands || []).forEach(function (b) { var a = Math.max(C.ML, C.X(b.x0)), c = Math.min(C.ML + C.pw, C.X(b.x1)); if (c > a) s += '<rect x="' + a.toFixed(1) + '" y="' + C.MT + '" width="' + Math.max(1.5, c - a).toFixed(1) + '" height="' + (yb - C.MT) + '" fill="' + b.col + '" opacity="' + (b.op || 0.13) + '"/>'; });
        (o.ticks || oxTicks(lo, hi)).forEach(function (t) { var y = C.Ys(t); if (y < yt - 1 || y > yb + 1) return; s += C.gl(y, o.fmt ? o.fmt(t) : fmt.n(t, Math.abs(t) < 10 && t % 1 ? 1 : 0), t === 0 ? 'base' : 'gl'); });
        (o.refs || []).forEach(function (f) { var y = C.Ys(f.y); s += '<line x1="' + C.ML + '" x2="' + (C.ML + C.pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '" stroke="' + f.col + '" stroke-dasharray="4 3" stroke-width="1.2"/>' + (f.lab && !C.sm ? axText(C.ML + 4, y - 4, f.lab).replace('class="ax"', 'class="ax" style="fill:' + f.col + '"') : ''); });
        BS.forEach(function (b) {   // 柱寬按目前看得到的根數算（選 1 年時不會因為全部資料很長而變細），只畫看得到的
          var bw = Math.max(1, C.pw / C.rows.length * 0.72);
          C.rows.forEach(function (r) { var v = r[b.i]; if (v == null) return; var y = C.Ys(v), col = b.col ? b.col(r) : (v >= 0 ? b.pos : b.neg); s += '<rect x="' + (C.X(r[0]) - bw / 2).toFixed(1) + '" y="' + Math.min(y, y0).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(0.6, Math.abs(y - y0)).toFixed(1) + '" fill="' + col + '"' + (b.op ? ' opacity="' + b.op + '"' : '') + '/>'; });
        });
        (o.lines || []).forEach(function (l, k) {
          var d = oxSeg(R_, l.i, C.X, C.Ys); if (!d) return;
          if (l.area || l.split) {
            var pts = R_.filter(function (r) { return r[l.i] != null; }), base = l.split ? y0 : yb;
            var ar = 'M' + C.X(pts[0][0]).toFixed(1) + ',' + base.toFixed(1) + 'L' + pts.map(function (r) { return C.X(r[0]).toFixed(1) + ',' + C.Ys(r[l.i]).toFixed(1); }).join('L') + 'L' + C.X(pts[pts.length - 1][0]).toFixed(1) + ',' + base.toFixed(1) + 'Z';
            if (l.split) s += '<path d="' + ar + '" fill="url(#' + uid + 'a' + k + '0)" clip-path="url(#' + uid + 'cu)"/><path d="' + ar + '" fill="url(#' + uid + 'a' + k + '1)" clip-path="url(#' + uid + 'cd)"/>';
            else s += '<path d="' + ar + '" fill="url(#' + uid + 'a' + k + '0)"/>';
          }
          if (l.split) s += '<path class="ln" d="' + d + '" stroke="' + l.split[0] + '" stroke-width="' + (l.w || 1.6) + '" clip-path="url(#' + uid + 'cu)"/><path class="ln" d="' + d + '" stroke="' + l.split[1] + '" stroke-width="' + (l.w || 1.6) + '" clip-path="url(#' + uid + 'cd)"/>';
          else s += '<path class="ln" d="' + d + '" stroke="' + l.col + '" stroke-width="' + (l.w || 1.8) + '"' + (l.op ? ' stroke-opacity="' + l.op + '"' : '') + (l.dash ? ' stroke-dasharray="' + l.dash + '"' : '') + '/>';
        });
        (o.plines || []).forEach(function (l) { var d = oxSeg(R_, l.i, C.X, C.Yp); if (d) s += '<path class="ln" d="' + d + '" stroke="' + l.col + '" stroke-width="' + (l.w || 1.6) + '"' + (l.dash ? ' stroke-dasharray="' + l.dash + '"' : '') + '/>'; });
        return s + (o.body ? o.body(C) : '');
      },
      over: function (C) {
        var s = '';
        var kept = [];   // 由新到舊放膠囊，和已放的同側膠囊重疊就略過
        if (!C.sm) (o.marks || []).slice().sort(function (a, b) { return b.x - a.x; }).forEach(function (m) { if (m.x < C.rows[0][0]) return; var cx = C.X(m.x), w = m.t.length * 6.3 + 12, up = m.up !== false; if (kept.some(function (k) { return k[2] === up && Math.abs(k[0] - cx) < (k[1] + w) / 2 + 4; })) return; kept.push([cx, w, up]); s += oxPill(cx, m.price ? C.Yp(m.y) : C.Ys(m.y), m.t, m.col, up, C.ML, C.pw); });
        (o.links || []).forEach(function (k) {   // 背離輔助線：{x0, y0, x1, y1, col, price, dash, lab}
          if (k.x1 < C.rows[0][0]) return; var Y = k.price ? C.Yp : C.Ys, ax = C.X(Math.max(k.x0, C.rows[0][0])), ay = Y(k.y0), bx = C.X(k.x1), by = Y(k.y1);
          s += '<line x1="' + ax.toFixed(1) + '" y1="' + ay.toFixed(1) + '" x2="' + bx.toFixed(1) + '" y2="' + by.toFixed(1) + '" stroke="' + k.col + '" stroke-width="' + (k.w || 1.6) + '"' + (k.dash ? ' stroke-dasharray="' + k.dash + '"' : '') + ' stroke-linecap="round"/>' +
            '<circle cx="' + ax.toFixed(1) + '" cy="' + ay.toFixed(1) + '" r="2.6" fill="' + k.col + '"/><circle cx="' + bx.toFixed(1) + '" cy="' + by.toFixed(1) + '" r="2.6" fill="' + k.col + '"/>' +
            (k.lab && !C.sm ? axText((ax + bx) / 2, Math.min(ay, by) - 6, k.lab, 'middle').replace('class="ax"', 'class="ax" style="fill:' + k.col + ';font-weight:700"') : '');
        });
        if (o.now) { var z = C.rows[C.rows.length - 1]; if (z[o.now.i] != null) s += oxNow(C.X(z[0]), C.Ys(z[o.now.i]), o.now.col, o.now.lab); }
        return s + (o.over ? o.over(C) : '');
      },
      tip: function (p, C) {
        var dots = '', rows = '';
        (o.lines || []).forEach(function (l) { if (p[l.i] == null) return; var c = l.split ? (p[l.i] >= 0 ? l.split[0] : l.split[1]) : l.col; dots += dot1(C.X(p[0]), C.Ys(p[l.i]), c); rows += tipRow1(c, nm(l), l.tfmt ? l.tfmt(p[l.i], p) : fmt.n(p[l.i], 2)); });
        (o.plines || []).forEach(function (l) { if (p[l.i] == null) return; dots += dot1(C.X(p[0]), C.Yp(p[l.i]), l.col); rows += tipRow1(l.col, nm(l), l.tfmt ? l.tfmt(p[l.i], p) : fmt.usd(p[l.i])); });   // 2026-11-06 上格（價格格）的線
        BS.forEach(function (b) { if (p[b.i] == null) return; var v = p[b.i], c2 = b.col ? b.col(p) : (v >= 0 ? b.pos : b.neg); rows += tipRow1(c2, b.name, b.tfmt ? b.tfmt(v, p) : fmt.n(v, 1)); });
        return { dots: dots, rows: rows + (o.tipExtra ? o.tipExtra(p) : '') };
      } });
  }

  /* ① 供給分位成本線：全體供給依最後一次移動的價格排序後的第 q 百分位。價格等於 q 線時，獲利供給約 q%（所以「獲利供給回到 65%」的價格＝0.65 線）。
     上方的線是解套賣壓、下方是成本密集的承接區；線會隨換手移動。單格對數價格圖 */
  var QX = [[45, 'var(--stg0)'], [50, 'var(--stg1)'], [55, 'var(--s3)'], [60, 'var(--stg2)'], [65, 'var(--s4)'], [75, 'var(--stg3)'], [85, 'var(--stg4)']];
  function qSay() {
    var x = D.onchain.quant, c = x.cur, it = [], b = x.below.length ? x.below[x.below.length - 1] : null, a = x.above.length ? x.above[0] : null;
    var qv = function (q) { return fmt.usd(c[q]); }, ch = function (q) { return x.chg30[q] == null ? '' : _T('（30 天 ' + fmt.pct(x.chg30[q], 1) + '）', ' (30d ' + fmt.pct(x.chg30[q], 1) + ')'); };
    it.push([_T('位置', 'Position'), (b ? '0.' + b : '—') + '–' + (a ? '0.' + a : '—'),
      _T('收盤 ' + fmt.usd(x.price) + (b ? ' 在 0.' + b + ' 分位 ' + qv(b) + ' 之上' : '') + (a ? '、0.' + a + ' 分位 ' + qv(a) + ' 之下' : '') + '。獲利供給 ' + fmt.n(x.psip, 1) + '%（30 天前 ' + fmt.n(x.psip30, 1) + '%）。',
        'Close ' + fmt.usd(x.price) + (b ? ' sits above the 0.' + b + ' line ' + qv(b) : '') + (a ? ' and below the 0.' + a + ' line ' + qv(a) : '') + '. Supply in profit ' + fmt.n(x.psip, 1) + '% (' + fmt.n(x.psip30, 1) + '% 30 days ago).'), 'neu']);
    it.push([_T('獲利供給回到幾 % 的價格', 'Price where supply in profit would be'), '65% ' + fmt.k(c['65']),
      _T('回到 65%：約 ' + qv('65') + ch('65') + '；60%：約 ' + qv('60') + ch('60') + '；55%：約 ' + qv('55') + ch('55') + '；50%：約 ' + qv('50') + '。分位線跟著換手移動，換手越多、線越往現價靠。',
        '65%: about ' + qv('65') + ch('65') + '; 60%: about ' + qv('60') + ch('60') + '; 55%: about ' + qv('55') + ch('55') + '; 50%: about ' + qv('50') + '. The lines move with turnover and drift toward price as coins change hands.'), 'neu']);
    var u = (x.ups75 || []).filter(function (e) { return e.r90 != null; });
    it.push([_T('0.75 分位（上方賣壓）', 'The 0.75 line (overhead supply)'), qv('75'),
      (x.below75_days ? _T('最後一次收在上方是 ' + ymdS(x.last_above75) + '，已連 ' + x.below75_days + ' 天在下方。', 'Last close above it was ' + ymdS(x.last_above75) + '; ' + x.below75_days + ' days below since. ') : _T('收在線上。', 'Closing above it. ')) +
      _T('價格在線下壓了 90 天以上之後重新站上，2015 年起有：' + u.map(function (e) { return oxYm(e.date) + '（之前 ' + e.below_days + ' 天，90 天後 ' + fmt.pct(e.r90, 0) + '）'; }).join('、') + '。2023 年 3 月第一次站上後又回到線下，10 月第二次才站穩。',
        'Reclaims after 90+ days below, since 2015: ' + u.map(function (e) { return oxYm(e.date) + ' (' + e.below_days + ' days below, 90d later ' + fmt.pct(e.r90, 0) + ')'; }).join(', ') + '. In 2023 the first reclaim in March failed; the second in October held.'), x.below75_days ? 'warn' : 'neu']);
    var bb = x.bear50 || [];
    if (bb.length) it.push([_T('熊底的獲利供給', 'Supply in profit at bear bottoms'), bb.map(function (e) { return e.days; }).join(' / '),
      _T('底部前後一年內獲利供給低於 50% 的天數：' + bb.map(function (e) { return e.bottom.slice(0, 4) + ' 年 ' + e.days + ' 天（最低 ' + fmt.n(e.min, 1) + '%）'; }).join('、') + '。每輪在 50% 以下的時間越來越短：低成本的老幣和遺失的幣越來越多，同樣的跌幅下獲利比例會比以前高。',
        'Days below 50% within a year of each bottom: ' + bb.map(function (e) { return e.bottom.slice(0, 4) + ' ' + e.days + ' days (low ' + fmt.n(e.min, 1) + '%)'; }).join(', ') + '. Each cycle spends less time below 50%: more old low-cost and lost coins keep the share higher for the same drawdown.'), 'neu']);
    var pl = (x.pulls || []).slice(-6);
    if (pl.length) it.push([_T('過渡期回調回到多低', 'How low transition pullbacks went'), pl.map(function (e) { return fmt.n(e.low, 0); }).join(' / ') + '%',
      _T('獲利供給先到 75% 以上、再跌到 65% 以下的回調，最低點：' + pl.map(function (e) { return oxYm(e.low_date) + ' ' + fmt.n(e.low, 1) + '%' + (e.r90 != null ? '（之後 90 天 ' + fmt.pct(e.r90, 0) + '）' : ''); }).join('、') + '。只代表過去，不是預測。',
        'Pullbacks after supply in profit had been above 75% and fell below 65%, at their lows: ' + pl.map(function (e) { return oxYm(e.low_date) + ' ' + fmt.n(e.low, 1) + '%' + (e.r90 != null ? ' (next 90d ' + fmt.pct(e.r90, 0) + ')' : ''); }).join(', ') + '. Past only, not a forecast.'), 'neu']);
    return it;
  }
  function qPanel() {
    var x = (D.onchain || {}).quant; if (!x || !x.rows) return '';
    var c = x.cur, b = x.below.length ? x.below[x.below.length - 1] : null, a = x.above.length ? x.above[0] : null;
    var hero = '<div class="cf-hero">' + oxCard('var(--s3)', _T('獲利供給', 'Supply in profit'), fmt.n(x.psip, 1) + '%', _T('價格在 0.' + b + '–0.' + a + ' 分位之間', 'Price between the 0.' + b + ' and 0.' + a + ' lines'), oxArrow(x.psip, x.psip30, _T(' 個百分點 / 30 天', ' pts / 30d'))) +
      oxCard('var(--stg3)', _T('上方：0.' + a + ' 分位', 'Above: 0.' + a + ' line'), fmt.k(c[a]), _T('0.75 分位 ' + fmt.usd(c['75']), '0.75 line ' + fmt.usd(c['75'])), _T('高出現價 ' + fmt.n(Math.abs(c[a] / x.price - 1) * 100, 1) + '%', fmt.n(Math.abs(c[a] / x.price - 1) * 100, 1) + '% above price')) +
      oxCard('var(--stg1)', _T('下方：0.' + b + ' 分位', 'Below: 0.' + b + ' line'), fmt.k(c[b]), _T('0.50 分位 ' + fmt.usd(c['50']), '0.50 line ' + fmt.usd(c['50'])), _T('低於現價 ' + fmt.n(Math.abs(c[b] / x.price - 1) * 100, 1) + '%', fmt.n(Math.abs(c[b] / x.price - 1) * 100, 1) + '% below price')) + '</div>';
    return panel('span-12', _T('供給分位成本線', 'Supply cost-basis quantiles'), 'Bitview · ' + fmt.md(x.date), hero + interpHtml(qSay()) +
      legend([[_T('BTC 價格', 'BTC price'), 'var(--ink)']].concat(QX.map(function (q) { return ['0.' + q[0], q[1]]; }))) + '<div class="chart cf-chart" id="c-quant"></div>' +
      '<p class="note">' + _T('全體供給依「最後一次移動時的價格」排序，第 q 百分位的價格。價格等於 0.65 線時，約 65% 的幣在獲利。逐筆 UTXO、不是實體調整；線每天隨換手移動。只作讀值。',
        'All coins ranked by the price at which they last moved; each line is the q-th percentile. When price sits on the 0.65 line, about 65% of coins are in profit. Per-UTXO, not entity-adjusted; the lines shift daily with turnover. Reading only.') + '</p>', '', 'quant');
  }
  function drawQuant(el) {
    var x = (D.onchain || {}).quant; if (!x || !el) return;
    var W = Math.max(280, el.clientWidth), rg = rangeOf(el, { series: [{ data: x.rows.map(function (r) { return [r[0], 1]; }) }] }, W), R_ = rg && rg.x0 != null ? x.rows.filter(function (r) { return r[0] >= rg.x0; }) : x.rows;
    var sm = W < 520, ML = 8, MR = sm ? 58 : 112, MT = 16, MB = 24, H = sm ? 300 : 400, pw = W - ML - MR, L = Math.log10;   // 桌面右側留 136px：刻度＋各分位線的數值
    var x0 = R_[0][0], x1 = R_[R_.length - 1][0], X = function (t) { return ML + (t - x0) / (x1 - x0 || 1) * pw; };
    var all = []; R_.forEach(function (r) { all.push(r[1], r[2], r[8]); });
    var lo = L(Math.min.apply(null, all)), hi = L(Math.max.apply(null, all)), pd = (hi - lo) * 0.05; lo -= pd; hi += pd;
    var Y = function (v) { return MT + (1 - (L(v) - lo) / (hi - lo)) * (H - MT - MB); }, s = '';
    [5e3, 1e4, 2e4, 3e4, 5e4, 7e4, 1e5, 1.5e5].forEach(function (t) { if (L(t) < lo || L(t) > hi) return; var y = Y(t); s += '<line class="gl" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/>' + (sm ? axText(ML + pw + 8, y + 3.5, fmt.k(t)) : y < MT + 18 ? '' : axText(ML + 4, y - 3, fmt.k(t))); });   // 桌面：價格刻度放左側圖內，右側邊欄留給分位數值
    var col = { 45: 2, 50: 3, 55: 4, 60: 5, 65: 6, 75: 7, 85: 8 };
    // 0.60–0.65 之間淡色帶（過渡期回調的常見區）、0.75 線以上淡紅（解套賣壓）
    var band = function (i, j, c, op) { var up = R_.map(function (r) { return X(r[0]).toFixed(1) + ',' + Y(r[i]).toFixed(1); }), dw = R_.slice().reverse().map(function (r) { return X(r[0]).toFixed(1) + ',' + Y(r[j]).toFixed(1); }); return '<path d="M' + up.join('L') + 'L' + dw.join('L') + 'Z" fill="' + c + '" opacity="' + op + '"/>'; };
    s += band(col[65], col[55], 'var(--s3)', 0.10) + band(col[85], col[75], 'var(--stg3)', 0.08);
    QX.forEach(function (q) { s += '<path class="ln" d="' + oxSeg(R_, col[q[0]], X, Y) + '" stroke="' + q[1] + '" stroke-width="' + (q[0] === 65 || q[0] === 75 ? 2 : 1.4) + '"/>'; });
    s += '<path class="ln" d="' + oxSeg(R_, 1, X, Y) + '" stroke="var(--ink)" stroke-width="1.5"/>';
    var z = R_[R_.length - 1], lab = [];
    QX.forEach(function (q) { lab.push([Y(z[col[q[0]]]), '0.' + q[0] + ' ' + fmt.k(z[col[q[0]]]), q[1]]); });
    lab.forEach(function (l) { l.push(l[0]); });   // l[3]＝線尾真正的高度（引線起點）
    lab.sort(function (a, b) { return a[0] - b[0]; }); for (var i = 1; i < lab.length; i++) if (lab[i][0] - lab[i - 1][0] < 13) lab[i][0] = lab[i - 1][0] + 13;
    var lx = ML + pw + 22;   // 右側邊欄只放分位數值（價格刻度在左側）
    if (!sm) lab.forEach(function (l) { s += '<path d="M' + (X(z[0]) + 2).toFixed(1) + ',' + l[3].toFixed(1) + 'L' + (ML + pw + 4).toFixed(1) + ',' + l[3].toFixed(1) + 'L' + (lx - 4).toFixed(1) + ',' + l[0].toFixed(1) + '" fill="none" stroke="' + l[2] + '" stroke-width="1" opacity=".55"/>' + axText(lx, l[0] + 3.5, l[1]).replace('class="ax"', 'class="ax" style="fill:' + l[2] + ';font-weight:700"'); });
    s += dot1(X(z[0]), Y(z[1]), 'var(--ink)');
    var ya = new Date(x0 * 864e5).getUTCFullYear() + 1, yz = new Date(x1 * 864e5).getUTCFullYear();
    for (var y = ya; y <= yz; y++) { var xx = X(Date.UTC(y, 0, 1) / 864e5); if (xx > ML + 14 && xx < ML + pw - 14) s += axText(xx, H - 6, String(y), 'middle'); }
    s += axText(ML, MT - 5, _T('BTC 價格與供給分位成本線（對數刻度）', 'BTC price and supply quantile lines (log scale)'));
    s += '<line class="xh" x1="0" x2="0" y1="' + MT + '" y2="' + (H - MB) + '" visibility="hidden"/><g class="hdots"></g><rect class="hit" x="' + ML + '" y="' + MT + '" width="' + pw + '" height="' + (H - MT - MB) + '"/>';
    el.innerHTML = (rg ? rg.html : '') + svgEl(W, H, s, _T('BTC 價格與供給分位成本線', 'BTC price and supply quantile lines'));
    bindRng(el, rg); animateLines(el);
    var svg = el.querySelector('svg'), xh = svg.querySelector('.xh'), dots = svg.querySelector('.hdots'), hit = svg.querySelector('.hit');
    function move(ev) {
      var r = svg.getBoundingClientRect(), xv = x0 + ((ev.clientX - r.left) * W / r.width - ML) / pw * (x1 - x0), p = R_[bisect(R_, xv)], cx = X(p[0]);
      xh.setAttribute('x1', cx); xh.setAttribute('x2', cx); xh.setAttribute('visibility', 'visible');
      dots.innerHTML = QX.map(function (q) { return dot1(cx, Y(p[col[q[0]]]), q[1]); }).join('') + dot1(cx, Y(p[1]), 'var(--ink)');
      showTip(ev.clientX, ev.clientY, '<div class="t">' + fmt.date(p[0]) + '</div>' + tipRow1('var(--ink)', _T('BTC 價格', 'BTC price'), fmt.usd(p[1])) + QX.slice().reverse().map(function (q) { return tipRow1(q[1], '0.' + q[0], fmt.usd(p[col[q[0]]])); }).join(''));
    }
    hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', function () { xh.setAttribute('visibility', 'hidden'); dots.innerHTML = ''; hideTip(); });
  }

  /* ② 短期持有者虧損比例（＝100 − 獲利比例）：讀值併進「短期持有者獲利比例」面板（同一個指標一個家） */
  function sthlSay() {
    var x = (D.onchain || {}).sthl; if (!x) return [];
    var E = (x.eps || []).filter(function (e) { return e.r30 != null; }).slice(-6);
    return [[_T('短期持有者虧損比例', 'STH supply in loss'), fmt.n(x.value, 1) + '%',
      _T('一半以上的短期持有者在虧損' + (x.value >= 50 ? '（已連 ' + x.run50 + ' 天高於 50%）' : '') + '。2015 年起平均 ' + fmt.n(x.mean_all, 1) + '%、2021 年起 ' + fmt.n(x.mean21, 1) + '%，高於 50% 的日子佔 ' + fmt.n(x.share50, 0) + '%。',
        (x.value >= 50 ? 'More than half of short-term holders are underwater (above 50% for ' + x.run50 + ' days). ' : '') + 'Average since 2015 ' + fmt.n(x.mean_all, 1) + '%, since 2021 ' + fmt.n(x.mean21, 1) + '%; it is above 50% on ' + fmt.n(x.share50, 0) + '% of days.'), x.value >= 60 ? 'warn' : 'neu'],
      [_T('升到 60% 以上之後', 'After rising above 60%'), x.stat30.up + ' / ' + x.stat30.n,
        _T('2015 年起升到 60% 以上 ' + x.eps.length + ' 次（隔 60 天算新的一次），30 天後 ' + oxStat(x.stat30, x.base30) + '；90 天後 ' + oxStat(x.stat90, x.base90) + '。最近幾次：' + E.map(function (e) { return oxYm(e.date) + ' 最高 ' + fmt.n(e.peak, 0) + '%（30 天 ' + fmt.pct(e.r30, 0) + '）'; }).join('、') + '。熊市裡會一路升到 90% 以上，單看這一項沒有優勢。',
          'Since 2015 it rose above 60% ' + x.eps.length + ' times (60+ days apart). 30 days later: ' + oxStat(x.stat30, x.base30) + '; 90 days later: ' + oxStat(x.stat90, x.base90) + '. Recent: ' + E.map(function (e) { return oxYm(e.date) + ' peak ' + fmt.n(e.peak, 0) + '% (30d ' + fmt.pct(e.r30, 0) + ')'; }).join(', ') + '. In bear markets it climbs past 90%, so on its own it gives no edge.'), 'neu']];
  }

  /* ③ 相對未實現獲利（未實現獲利 ÷ 市值）的地板：2012 年起只有週期底部附近掉到 35% 以下。週期版 */
  function rupSay() {
    var x = D.onchain.rup || {}, E = x.eps || [], it = [];
    it.push([_T('離地板', 'Distance to floor'), (x.gap >= 0 ? '+' : '') + fmt.n(x.gap, 1) + _T(' 個百分點', ' pts'),
      _T('相對未實現獲利 ' + fmt.n(x.value, 1) + '%（30 天前 ' + fmt.n(x.d30, 1) + '%），地板 ' + x.floor + '%。一年最低 ' + fmt.n(x.lo1y.value, 1) + '%（' + ymdS(x.lo1y.date) + '）。',
        'Relative unrealized profit ' + fmt.n(x.value, 1) + '% (' + fmt.n(x.d30, 1) + '% 30 days ago); the floor is ' + x.floor + '%. One-year low ' + fmt.n(x.lo1y.value, 1) + '% (' + ymdS(x.lo1y.date) + ').'), x.gap <= 0 ? 'pos' : x.gap <= 3 ? 'warn' : 'neu']);
    it.push([_T('歷次地板區', 'Past floor episodes'), E.length + _T(' 段', ''),
      _T(E.map(function (e) { return ymdS(e.start) + '–' + ymdS(e.end) + '（' + e.days + ' 天，最低 ' + fmt.n(e.min, 1) + '%' + (e.r365 != null ? '，一年後 ' + fmt.pct(e.r365, 0) : '') + '）'; }).join('、') + '。在地板的天數一輪比一輪短，本輪只有 ' + (E.length ? E[E.length - 1].days : 0) + ' 天：波動被壓縮後，跌到地板的機會變小。',
        E.map(function (e) { return ymdS(e.start) + '–' + ymdS(e.end) + ' (' + e.days + ' days, low ' + fmt.n(e.min, 1) + '%' + (e.r365 != null ? ', 1y later ' + fmt.pct(e.r365, 0) : '') + ')'; }).join('; ') + '. Each cycle spends fewer days on the floor — this one only ' + (E.length ? E[E.length - 1].days : 0) + ' — as volatility compresses.'), 'neu']);
    return it;
  }
  /* 2026-11-06 使用者要求：「相對未實現獲利：地板」要寫出底層邏輯、白話反映什麼、35% 地板的意思、怎麼用。數字都由資料產生（oc_extra.rup_viz） */
  function rupExplain() {
    var x = D.onchain.rup, E = x.eps || [], T = x.tops || [], z = E[E.length - 1] || {}, bt = (D.cycle.bottoms || []).slice(-1)[0];
    var sec = function (t, body) { return '<div class="ox-x"><h3>' + t + '</h3>' + body + '</div>'; }, p = function (t) { return '<p>' + esc(t) + '</p>'; };
    var tops = T.map(function (t) { return t.top.slice(0, 4) + ' ' + fmt.n(t.value, 0) + '%'; }).join(_T('、', ', '));
    var eps = E.map(function (e) { return ymdS(e.start) + '–' + ymdS(e.end) + _T('（' + e.days + ' 天）', ' (' + e.days + ' days)'); }).join(_T('、', ', '));
    var mins = E.map(function (e) { return e.start.slice(0, 4) + ' ' + fmt.n(e.min, 1) + '%'; }).join(' → ');
    var dd = E.filter(function (e) { return e.dd180 != null; }).map(function (e) { return e.start.slice(0, 4) + ' ' + oxP0(e.dd180); }).join(_T('、', ', '));
    var yr = E.filter(function (e) { return e.r365 != null; }), yrUp = yr.filter(function (e) { return e.r365 > 0; }).length, r1 = yr.map(function (e) { return e.r365; });
    var isLow = bt && z.min_date === bt[0], lo = x.other_lo || {};
    return '<div class="ox-xs">' +
      sec(_T('底層邏輯', 'How it is calculated'),
        p(_T('每一顆比特幣都記得自己最後一次移動時的價格，可以當成持有人的成本。現價高於成本的幣，差額就是帳面獲利；還沒賣，所以叫「未實現」。把所有幣的帳面獲利加起來，再除以市值（現價 × 流通量），就是相對未實現獲利。',
          'Every bitcoin carries the price at which it last moved, which serves as its holder\'s cost. For coins now worth more than that cost, the difference is a paper gain — "unrealized" because it has not been sold. Add up the paper gains of all coins and divide by market cap (price × supply) to get relative unrealized profit.')) +
        '<p class="ox-f">' + _T('相對未實現獲利 ＝ Σ（現價 − 成本）× 顆數 ÷ 市值　（只算現價高於成本的幣）', 'Relative unrealized profit = Σ (price − cost) × coins ÷ market cap   (coins above their cost only)') + '</p>' +
        p(_T('資料是 Bitview 從區塊鏈逐筆 UTXO 算的；不是實體調整，交易所內部搬幣會把那批幣的成本改成搬動當天的價格。',
          'Data: Bitview, computed per UTXO from the blockchain. It is not entity-adjusted, so an exchange moving coins internally resets their cost to that day\'s price.'))) +
      sec(_T('反映什麼', 'What it reflects'),   /* 2026-11-06 使用者：「白話」是要求用白話寫，不是標題 */
        p(_T('市值每 100 美元裡，有多少是持有人「還沒賣掉的賺頭」。現在 ' + fmt.n(x.value, 1) + '%，就是每 100 美元裡有 ' + fmt.n(x.value, 1) + ' 美元是帳面獲利。',
          'Of every $100 of market value, how much is holders\' gain not yet cashed in. Now ' + fmt.n(x.value, 1) + '%: $' + fmt.n(x.value, 1) + ' of every $100 is paper profit.')) +
        p(_T('數字高＝大家都賺很多，想獲利了結的人多，週期頂部附近最高（' + tops + '，一輪比一輪低）。數字低＝帳面獲利被擠乾了：高價買的人已經套牢或認賠離場，剩下的獲利多半在很早以前低價買、幾乎不動的老幣身上。2012 年起的中位數是 ' + fmt.n(x.med, 1) + '%。',
          'High means everyone is well in profit and many want to take it; it peaks near cycle tops (' + tops + ', lower each cycle). Low means paper profit has been squeezed out: high-price buyers are underwater or have sold at a loss, and what profit remains sits mostly with old, low-cost coins that rarely move. The median since 2012 is ' + fmt.n(x.med, 1) + '%.'))) +
      sec(_T('35% 地板是什麼意思', 'What the 35% floor means'),
        p(_T('有一大塊幾乎不會賣的老幣（早期挖出、多年沒動、遺失的幣），成本極低。價格再怎麼跌，它們的帳面獲利都還在，所以這個比例跌不到 0，會在某個水準附近止住，這就是「地板」。',
          'A large block of coins almost never sells — early-mined, untouched for years, or lost — and their cost is tiny. However far price falls, their paper profit remains, so the ratio cannot reach zero and stalls around some level: the floor.')) +
        p(_T('2012 年起只有 ' + fmt.n(x.share_below, 1) + '% 的日子在 ' + x.floor + '% 以下，而且全都集中在週期底部附近：' + eps + '。其他年份的最低只到 ' + fmt.n(lo.value, 1) + '%（' + lo.year + ' 年）。跌到 35% 以下，代表帳面獲利已經被擠到只剩老幣的程度，過去只在週期底部發生。',
          'Since 2012 only ' + fmt.n(x.share_below, 1) + '% of days were at or below ' + x.floor + '%, all near cycle bottoms: ' + eps + '. In other years the low only reached ' + fmt.n(lo.value, 1) + '% (' + lo.year + '). Below 35%, paper profit has been squeezed down to the old coins alone — historically only at cycle bottoms.')) +
        (z.start ? p(_T('本輪 ' + ymdS(z.start) + '–' + ymdS(z.end) + ' 共 ' + z.days + ' 天在地板以下，最低 ' + fmt.n(z.min, 1) + '% 在 ' + ymdS(z.min_date) + '（收盤 ' + fmt.usd(z.low_price) + (isLow ? '，正是本輪的最低價' : '') + '）。35% 是本站看 2012 年以來的歷史畫的線，不是理論上的常數。',
          'This cycle spent ' + z.days + ' days below the floor between ' + ymdS(z.start) + ' and ' + ymdS(z.end) + ', with the low of ' + fmt.n(z.min, 1) + '% on ' + ymdS(z.min_date) + ' (close ' + fmt.usd(z.low_price) + (isLow ? ', the cycle\'s lowest price' : '') + '). The 35% line is drawn from history since 2012, not a theoretical constant.')) : '')) +
      sec(_T('怎麼用', 'How to use it'),
        '<ol>' +
        '<li>' + esc(_T('看離地板多遠：越近，越接近過去週期底部的狀態；回到中位數 ' + fmt.n(x.med, 0) + '% 以上，代表已經離開底部區。現在 ' + fmt.n(x.value, 1) + '%，離地板 ' + fmt.n(x.gap, 1) + ' 個百分點。',
          'Watch the distance to the floor: the closer, the more it resembles past cycle bottoms; back above the ' + fmt.n(x.med, 0) + '% median means the bottom zone is behind. Now ' + fmt.n(x.value, 1) + '%, ' + fmt.n(x.gap, 1) + ' points above the floor.')) + '</li>' +
        '<li>' + esc(_T('當作「底部區」的確認，不是精準的買點：進入地板之後 180 天內，價格還可能再跌（' + dd + '）；走完一年的 ' + yr.length + ' 次中，' + yrUp + ' 次一年後比進入時高（' + (r1.length ? fmt.pct(Math.min.apply(null, r1), 0) + ' 到 ' + fmt.pct(Math.max.apply(null, r1), 0) : '—') + '）。',
          'Treat it as confirmation of a bottom zone, not a precise entry: within 180 days of entering the floor price still fell further (' + dd + '); of the ' + yr.length + ' episodes with a full year since, ' + yrUp + ' were higher a year later (' + (r1.length ? fmt.pct(Math.min.apply(null, r1), 0) + ' to ' + fmt.pct(Math.max.apply(null, r1), 0) : '—') + ').')) + '</li>' +
        '<li>' + esc(_T('和其他底部指標一起看：獲利供給（低於 50%）、長期持有者虧損比例、賣方衰竭常數。幾項同時在底部區，可信度才高。',
          'Read it with other bottom gauges — supply in profit (below 50%), long-term holder supply in loss, the seller exhaustion constant. Confidence comes when several sit in their bottom zones together.')) + '</li>' +
        '<li>' + esc(_T('要小心：樣本只有 ' + E.length + ' 次。每段的最低點大致一輪比一輪高（' + mins + '），頂部一輪比一輪低，35% 這條線之後可能要往上調。ETF 時代波動被壓縮，本輪只碰了 ' + (z.days || 0) + ' 天，之後也可能不跌到地板就反轉。只作讀值，不是買賣訊號。',
          'Caveats: only ' + E.length + ' episodes. The lows have broadly risen each cycle (' + mins + ') while tops have fallen, so the 35% line may need raising. With volatility compressed in the ETF era this cycle touched it for only ' + (z.days || 0) + ' days, and future turns may come without reaching it. Reading only, not a trading signal.')) + '</li>' +
        '</ol>') +
      '</div>';
  }
  /* 新圖的「怎麼讀這張圖」（圖上／怎麼看／小心）與「現在」一句；接到既有的讀圖機制（RD、attachReads） */
  (function () {
    var hh = function (a, b, cz, ce, dz, de) { return [[a, b], [cz, ce], [dz, de]]; }, o = function (k) { return (D.onchain || {})[k] || {}; }, dv = function (k) { return (D.deriv || {})[k] || {}; };
    Object.assign(RD, {
      'quant': { h: hh('黑線是價格，彩色線是 0.45–0.85 分位成本線（對數刻度）：全部的幣依最後一次移動的價格排隊，第 q% 那顆的價格。青綠帶是 0.55–0.65，琥珀帶是 0.75–0.85；右側是每條線現在的數值。', 'Black is price; coloured lines are the 0.45–0.85 cost quantiles (log scale): line up every coin by the price it last moved at and take the coin at q%. The teal band spans 0.55–0.65, the amber band 0.75–0.85; current values sit on the right.',
          '價格剛好在某條 q 線上＝約 q% 的幣在獲利。上方的線是套牢者回本想賣的地方（壓力），下方的線是很多人的成本（承接）。站上 0.75 之後常要一段時間消化，2023 年在線下壓了半年。', 'Price on a q line means about q% of coins are in profit. Lines above mark where trapped holders break even and may sell (resistance); lines below are where many paid (support). Clearing the 0.75 line usually takes time — in 2023 it capped price for half a year.',
          '逐筆 UTXO、不是實體調整，交易所內部搬幣會讓線跳一下；線每天隨換手移動，不是固定價位。', 'Per-UTXO and not entity-adjusted, so internal exchange moves make the lines jump; they shift daily with turnover and are not fixed levels.'),
        now: function () { var x = o('quant'); if (!x.cur) return ''; var b = x.below[x.below.length - 1], a = x.above[0]; return _T('收盤在 0.' + b + '（' + fmt.k(x.cur[b]) + '）和 0.' + a + '（' + fmt.k(x.cur[a]) + '）之間；獲利供給 ' + fmt.n(x.psip, 1) + '%。', 'Close between the 0.' + b + ' (' + fmt.k(x.cur[b]) + ') and 0.' + a + ' (' + fmt.k(x.cur[a]) + ') lines; supply in profit ' + fmt.n(x.psip, 1) + '%.'); } },
      'rloss': { h: hh('上格是價格：青綠圈是擺動低點，虛線連前後兩個低點（青綠＝背離、紅＝背離被打破、琥珀＝認賠放大）。下格是每天賣在虧損的總金額（百萬美元），灰柱是搬家日。', 'Top: price — teal circles are swing lows, dashed lines join consecutive lows (teal = divergence, red = divergence broken, amber = loss grows). Bottom: total loss realized each day ($M); grey bars are internal-transfer days.',
          '價格破底、認賠卻變少＝願意賠錢賣的人變少，恐慌在退；價格破底、認賠更大＝恐慌在放大。', 'A lower low with less loss-taking means fewer holders willing to sell at a loss — fear is fading; a lower low with more loss-taking means panic is growing.',
          '不是實體調整；擺動低點要等前後 7 天才確認，所以最近一週的判定是暫定的。', 'Not entity-adjusted; a swing low is confirmed only after 7 days, so the latest week is provisional.'),
        now: function () { var x = o('rloss'); return x.usd_m == null ? '' : _T('今日 ' + oxUsd(x.usd_m * 1e6) + '，7 天合計 ' + oxUsd(x.usd7_m * 1e6) + '。', 'Today ' + oxUsd(x.usd_m * 1e6) + ', 7-day total ' + oxUsd(x.usd7_m * 1e6) + '.'); } },
      'lsrchg': { h: hh('長期持有者供給 ÷ 短期持有者供給的 30 日變化：橘（負）＝長期持有者的幣流向短期持有者，青綠（正）＝籌碼沉澱。淡黃底是各輪週期頂部之前那一年（主升段），淡藍底是各輪熊市底部之後那一年（過渡期）；上方讀值的比例就是這兩種區間裡為負的天數。', '30-day change of long- ÷ short-term holder supply: orange (negative) = long-term holder coins passing to short-term holders, teal (positive) = supply settling. Pale amber shading is the year before each cycle top (the main up-leg), pale blue the year after each bear-market bottom (the transition); the shares in the readings above count negative days inside these windows.',
          '主升段大多為負：長期持有者在賣、新需求接得住；過渡期負值多＝需求強，接近一半一半時價格走得較平。', 'Main up-legs are mostly negative — long-term holders sell and new demand absorbs it; many negative days in a transition mean strong demand, an even split goes with flatter prices.',
          '幣放滿 155 天會自動從短期轉成長期，沒有人交易時比值也會慢慢上升。', 'Coins turn long-term automatically at 155 days, so the ratio drifts up even with no trading.'),
        now: function () { var x = o('lsrchg'); return x.value == null ? '' : _T('30 日 ' + fmt.pct(x.value, 1) + '，連 ' + x.days + ' 天為' + (x.neg ? '負' : '正') + '。', '30-day ' + fmt.pct(x.value, 1) + ', ' + (x.neg ? 'negative' : 'positive') + ' for ' + x.days + ' days.'); } },
      'grad': { h: hh('金色是 120 日（大級別），淡橘是 30 日（小級別）。0 以上＝價格漲得比資金流入快；0 以下＝價格跌得比資金撤出快。膠囊是 120 日的背離。', 'Gold is the 120-day gauge (long frame), pale orange the 30-day (short frame). Above 0 = price rising faster than money flows in; below 0 = price falling faster than money leaves. Capsules mark 120-day divergences.',
          '價格新低而梯度沒有新低（底背離）＝資金撤得比價格跌得慢，大級別在築底；價格新高而梯度沒有新高（頂背離）＝靠情緒推升、新資金沒跟上，之後常先回調。', 'A lower price low without a lower gauge low (bullish divergence) means money leaves more slowly than price falls — a long-frame base; a higher price high without a higher gauge high (bearish) means the rise runs on sentiment, and a pullback often comes first.',
          '本站自己的算法；30 日容易被消息打破；背離要等擺動點確認（30 日約 10 天、120 日約 20 天）。', 'Our own construction; the 30-day frame is easily broken by news; divergences confirm only after the swing (about 10 days for 30-day, 20 for 120-day).'),
        now: function () { var x = o('grad'); return x.z120 == null ? '' : _T('120 日 ' + fmt.n(x.z120, 2) + '、30 日 ' + fmt.n(x.z30, 2) + '（標準差）。', '120-day ' + fmt.n(x.z120, 2) + ', 30-day ' + fmt.n(x.z30, 2) + ' (SD).'); } },
      'mom': { h: hh('（SOPR − 1）× 每日銷毀幣天數的 14 日平均：綠（正）＝獲利了結的力道，紅（負）＝認賠。刻度壓縮過（大的數字被縮小）。膠囊是頂背離與之後 60 天內的最大跌幅。', '14-day average of (SOPR − 1) × coin days destroyed: green (positive) = profit-taking force, red (negative) = loss-taking. The scale is compressed. Capsules mark bearish divergences and the max drawdown over the next 60 days.',
          '價格新高、綠色峰值卻變低＝推升的力量在衰減；2015 年起之後 60 天內最大跌幅中位數約 −21%，任一天約 −9%。', 'A higher price with a lower green peak means the push is fading; since 2015 the median max drawdown within 60 days afterwards is about −21% versus about −9% for any day.',
          '老錢包或交易所整理一次搬動大量老幣，單日銷毀幣天數會暴增，峰值要看整體形態，不看單日。', 'When old wallets or exchanges move large blocks of old coins, a single day\'s coin days destroyed spikes; read the overall shape, not one day.'),
        now: function () { var x = o('mom'); return x.value == null ? '' : _T('現在 ' + fmt.n(x.value, 0) + '（' + (x.value >= 0 ? '獲利了結為主' : '認賠為主') + '）。', 'Now ' + fmt.n(x.value, 0) + ' (' + (x.value >= 0 ? 'profit-taking leads' : 'loss-taking leads') + ').'); } },
      'gex': { h: hh('每個履約價的 Gamma 曝險（百萬美元／價格變動 1%）：綠＝正（做市商逆勢對沖，吸住價格），紅＝負（順勢對沖，放大波動）。下方灰柱是籌碼分布，紅虛線是現價。', 'Gamma exposure per strike ($M per 1% move): green = positive (dealers hedge against the move, pinning price), red = negative (they hedge with it, amplifying moves). Grey bars below are the supply distribution; the red dashed line is spot.',
          '現價附近正 Gamma 多＝價格容易被釘住；跌破正 Gamma 區、進入負 Gamma 區，波動容易放大；正 Gamma 剛好落在籌碼峰上＝衍生品和鏈上的支撐（或壓力）在同一個價位。', 'Lots of positive gamma near spot pins price; breaking out of a positive zone into a negative one lets volatility grow; positive gamma on a supply cluster means derivatives and on-chain support (or resistance) coincide.',
          '做市商的方向是用逐筆成交推算的，正負號可能和付費資料不同；到期日一過，那部分就消失。', 'The dealer side is inferred from trades, so signs may differ from paid data; each expiry\'s part disappears once it settles.'),
        now: function () { var x = dv('gex'); return x.spot == null ? '' : _T('45 天內：現價上方 ' + (x.above >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.above), 0) + 'M、下方 ' + (x.below >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.below), 0) + 'M；主要到期 ' + fmt.md(x.main) + '。', 'Within 45 days: ' + (x.above >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.above), 0) + 'M above spot, ' + (x.below >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.below), 0) + 'M below; main expiry ' + fmt.md(x.main) + '.'); } },
      'prem': { h: hh('每天主動買進買權付的權利金 − 主動買進賣權付的權利金：綠＝買權多，紅＝賣權多；金線是 7 日平均。', 'Premium paid by takers buying calls minus puts each day: green = calls lead, red = puts lead; the gold line is the 7-day average.',
          '長時間為正＝錢在押上漲；轉負＝搶買下跌保護，恐慌時常見，事後看常在相對低點附近（只代表過去）。', 'Persistently positive means money is betting on upside; turning negative means a rush for downside protection, common in fear and often near relative lows in hindsight (past only).',
          '資料只有一年；只算主動買方；只有 Deribit。', 'Only a year of data; aggressive buyers only; Deribit only.'),
        now: function () { var x = dv('prem'); return x.a7 == null ? '' : _T('7 日平均 ' + (x.a7 >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.a7), 1) + 'M，連 ' + x.run + ' 天' + (x.a7 >= 0 ? '偏買權' : '偏賣權') + '。', '7-day average ' + (x.a7 >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.a7), 1) + 'M, leaning ' + (x.a7 >= 0 ? 'calls' : 'puts') + ' for ' + x.run + ' days.'); } },
      'svdh': { h: hh('上圖：OKX 現貨每天主動買 − 主動賣（顆），綠＝買方主動、紅＝賣方主動。下圖：近 7 天每小時。', 'Top chart: OKX spot taker buy − taker sell per day (BTC), green = buyers aggressive, red = sellers aggressive. Bottom chart: hourly for the last 7 days.',
          '下跌時紅柱縮小、轉綠＝殺跌的人變少、有人主動接；只在跌時放量賣、反彈時沒有主動買＝買方多半是被動掛單。', 'In a drop, red bars shrinking and turning green means fewer sellers dumping and someone buying actively; heavy selling on drops with no active buying on bounces means buyers are mostly passive bids.',
          '只有 OKX 一家；日線是 UTC+8 的日界。', 'OKX only; daily bars use UTC+8 days.'),
        now: function () { var x = dv('svd'); return x.sum7 == null ? '' : _T('7 天合計 ' + (x.sum7 >= 0 ? '+' : '') + fmt.n(x.sum7, 0) + ' 顆；近 24 小時 ' + (x.h24 >= 0 ? '+' : '') + fmt.n(x.h24, 0) + ' 顆。', '7-day total ' + (x.sum7 >= 0 ? '+' : '') + fmt.n(x.sum7, 0) + ' BTC; last 24 hours ' + (x.h24 >= 0 ? '+' : '') + fmt.n(x.h24, 0) + ' BTC.'); } }
    });
  })();
  function rupPanel() {
    var x = (D.onchain || {}).rup; if (!x || !x.rows) return '';
    return panel('span-12', _T('相對未實現獲利：地板', 'Relative unrealized profit: the floor'), 'Bitview · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard('var(--s1)', _T('相對未實現獲利', 'Relative unrealized profit'), fmt.n(x.value, 1) + '%', _T('地板 ' + x.floor + '%（過去只在週期底部附近跌破）', 'Floor ' + x.floor + '% (broken only near past cycle bottoms)'), oxArrow(x.value, x.d30, _T(' 個百分點 / 30 天', ' pts / 30d'))) + oxCard('var(--s3)', _T('一年最低', 'One-year low'), fmt.n(x.lo1y.value, 1) + '%', ymdS(x.lo1y.date) + (x.lo1y.value <= x.floor ? _T('，在地板以下', ', below the floor') : '')) + '</div>' +
      interpHtml(rupSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('相對未實現獲利', 'Relative unrealized profit'), 'var(--s1)'], [_T('地板區（≤ 35%）', 'Floor zone (≤ 35%)'), 'var(--s3)', 'box']]) +
      '<div class="chart cf-chart" id="c-rup"></div>' + rupExplain(), '', 'rup');
  }
  function drawRup(el) {
    var x = (D.onchain || {}).rup; if (!x || !el) return;
    oxPane(el, { rows: x.rows, label: _T('相對未實現獲利（%）', 'Relative unrealized profit (%)'), aria: _T('BTC 價格與相對未實現獲利', 'BTC price and relative unrealized profit'),
      lines: [{ i: 2, col: 'var(--s1)', area: true, w: 1.8, name: _T('相對未實現獲利', 'Relative unrealized profit'), tfmt: function (v) { return fmt.n(v, 1) + '%'; } }],
      zones: [{ y0: 0, y1: x.floor, col: 'var(--s3)', op: 0.16 }], refs: [{ y: x.floor, col: 'var(--s3)', lab: _T('地板 ', 'Floor ') + x.floor + '%' }], fmt: function (t) { return t + '%'; },
      vbands: (x.eps || []).map(function (e) { return { x0: dnOf(e.start), x1: dnOf(e.end), col: 'var(--s3)', op: 0.18 }; }),
      marks: (x.eps || []).map(function (e) { return { x: dnOf(e.min_date), y: e.min, col: 'var(--s3)', t: e.min_date.slice(0, 4) + ' ' + fmt.n(e.min, 1) + '%', up: false }; }),
      now: { i: 2, col: 'var(--s1)', lab: _T('現在 ', 'Now ') + fmt.n(x.value, 1) + '%' } });
  }

  /* ④ 全網實現虧損：峰值背離。價格擺動低點更低、但當時的認賠峰值小 20% 以上＝背離（想賣的人變少）；更大＝投降 */
  var RL_KIND = { div: ['背離', 'divergence'], cap: ['投降', 'capitulation'], flat: ['差不多', 'similar'] };
  var CH_KIND = { div: ['背離', 'divergence', 'var(--s3)'], 'break': ['背離被打破', 'divergence broken', 'var(--down)'], cap: ['認賠放大', 'loss grows', 'var(--warn)'], flat: ['差不多', 'similar', 'var(--ink-3)'], reset: ['價格回升，重新比', 'price higher, restart', 'var(--ink-3)'] };
  function chStep(c) { return c.kind === 'div' && c.step >= 2 ? _T(['', '', '二次', '三次', '四次'][c.step] || c.step + ' 次', ['', '', '2nd', '3rd', '4th'][c.step] || c.step + 'th') : ''; }
  function chLab(c) { return c.kind === 'div' ? (c.step >= 2 ? _T(chStep(c) + '背離', chStep(c) + ' divergence') : _T('背離', 'Divergence')) : c.kind === 'break' ? _T('打破', 'Broken') : c.kind === 'cap' ? _T('放大', 'Grows') : ''; }
  function chState() {
    var x = D.onchain.rloss, L = (x.chain || []).filter(function (c) { return c.kind !== 'flat'; }), z = L[L.length - 1];
    if (!z) return null;
    var t = z.kind === 'div' ? _T((z.step >= 2 ? chStep(z) + '背離' : '背離') + '進行中', (z.step >= 2 ? chStep(z) + ' divergence' : 'Divergence') + ' in progress') : z.kind === 'break' ? _T('背離被打破', 'Divergence broken') : z.kind === 'cap' ? _T('認賠放大', 'Loss-taking growing') : _T('價格回升，重新比', 'Price higher, comparison restarts');
    return { c: z, t: t + (z.conf ? '' : _T('（暫定）', ' (provisional)')) };
  }
  /* 2026-11-09 改名（原本也叫 rlSay，蓋掉了「長期持有者已實現虧損」的 rlSay，那張圖與頭版看法表 11/06 起顯示成這張的解讀） */
  function rlossSay() {
    var x = D.onchain.rloss, it = [], cur = x.cur, b = x.back || {};
    it.push([_T('今日認賠', 'Loss realized today'), '$' + fmt.n(x.usd_m, 0) + 'M',
      _T('全網每日實現虧損 ' + oxUsd(x.usd_m * 1e6) + '（市值的萬分之 ' + fmt.n(x.bp, 1) + '），7 天合計 ' + oxUsd(x.usd7_m * 1e6) + '。' + ((x.skip || []).length ? (x.skip.map(ymdS).join('、') + ' 是搬家日（同一實體內部轉帳），那天的虧損不算峰值。') : ''),
        'Network realized loss ' + oxUsd(x.usd_m * 1e6) + ' today (' + fmt.n(x.bp, 1) + ' bp of market cap), ' + oxUsd(x.usd7_m * 1e6) + ' over 7 days. ' + ((x.skip || []).length ? (x.skip.map(ymdS).join(', ') + ' was an internal-transfer day; its loss is not counted as a peak.') : '')), 'neu']);
    var cs = chState(), CL = (x.chain || []).filter(function (c) { return c.kind !== 'flat'; }).slice(-4), cb = x.chain_back || {};
    if (cs) it.push([_T('認賠峰值的背離', 'Loss-peak divergence'), cs.t,
      _T(CL.map(function (c) { return fmt.md(c.a) + ' ' + oxUsd(c.ua * 1e6) + '（' + fmt.k(c.pa) + '）→ ' + fmt.md(c.b) + ' ' + oxUsd(c.ub * 1e6) + '（' + fmt.k(c.pb) + '）：' + _T(CH_KIND[c.kind][0], CH_KIND[c.kind][1]) + (c.step >= 2 ? '（' + chStep(c) + '）' : ''); }).join('；') + '。規則：價格沒有比前一個峰值高 2% 以上時才比；認賠少 1 成以上＝背離，連續就是二次、三次背離；背離之後認賠反而多 1 成以上＝背離被打破；價格回升超過 2%＝重新開始比。',
        CL.map(function (c) { return fmt.md(c.a) + ' ' + oxUsd(c.ua * 1e6) + ' (' + fmt.k(c.pa) + ') → ' + fmt.md(c.b) + ' ' + oxUsd(c.ub * 1e6) + ' (' + fmt.k(c.pb) + '): ' + CH_KIND[c.kind][1]; }).join('; ') + '. Rule: peaks are compared only when price is not more than 2% above the previous peak; 10%+ less loss = divergence (repeats make a 2nd, 3rd divergence); 10%+ more loss after a divergence = divergence broken; price more than 2% higher = the comparison restarts.'), cs.c.kind === 'div' ? 'pos' : cs.c.kind === 'break' || cs.c.kind === 'cap' ? 'warn' : 'neu']);
    if (cb.n) it.push([_T('二次背離之後', 'After a 2nd divergence'), cb.r30.up + ' / ' + cb.r30.n,
      _T('2013 年起認賠峰值背離連到第二次以上 ' + cb.n + ' 次：30 天後 ' + oxStat(cb.r30, x.base30) + '；90 天後 ' + oxStat(cb.r90, x.base90) + '。其中 ' + cb.broken30 + '/' + cb.done + ' 次在之後 30 天內被打破（又出現更大的認賠）。',
        'Since 2013 the loss-peak divergence reached a 2nd step or more ' + cb.n + ' times: 30 days later ' + oxStat(cb.r30, x.base30) + '; 90 days later ' + oxStat(cb.r90, x.base90) + '. In ' + cb.broken30 + ' of ' + cb.done + ' it was broken within 30 days (a bigger loss peak followed).'), 'neu']);
    it.push([_T('最近一對低點', 'Latest pair of lows'), cur ? _T(RL_KIND[cur.kind][0], RL_KIND[cur.kind][1]) : '—',
      cur ? _T(ymdS(cur.prev) + ' ' + fmt.usd(cur.prev_price) + ' → ' + ymdS(cur.date) + ' ' + fmt.usd(cur.price) + '：價格更低，認賠峰值 ' + fmt.n(cur.prev_bp, 1) + ' → ' + fmt.n(cur.bp, 1) + ' bp' + (cur.confirmed ? '' : '（低點還沒確認，前後 7 天才算）') + '。',
        ymdS(cur.prev) + ' ' + fmt.usd(cur.prev_price) + ' → ' + ymdS(cur.date) + ' ' + fmt.usd(cur.price) + ': lower price, loss peak ' + fmt.n(cur.prev_bp, 1) + ' → ' + fmt.n(cur.bp, 1) + ' bp' + (cur.confirmed ? '' : ' (low not confirmed until 7 days pass)') + '.')
        : _T('近 30 天沒有比前一個擺動低點更低的低點（擺動低點＝前後 7 天最低、比之前 30 天最高跌 6% 以上）。', 'No lower swing low in the last 30 days (a swing low is the lowest close within 7 days either side, at least 6% below the prior 30-day high).'), cur && cur.kind === 'div' ? 'pos' : cur && cur.kind === 'cap' ? 'warn' : 'neu']);
    it.push([_T('過去的背離', 'Past divergences'), (b.div ? b.div.r30.up + ' / ' + b.div.r30.n : '—'),
      _T('2013 年起背離 ' + x.n_div + ' 次：30 天後 ' + oxStat((b.div || {}).r30, x.base30) + '；90 天後 ' + oxStat((b.div || {}).r90, x.base90) + '。投降 ' + x.n_cap + ' 次：30 天後 ' + oxStat((b.cap || {}).r30) + '。背離有一點優勢、但 2022/05 背離之後還跌了 26%；不是實體調整，交易所內部搬幣也算進虧損。',
        'Since 2013, ' + x.n_div + ' divergences: 30 days later ' + oxStat((b.div || {}).r30, x.base30) + '; 90 days later ' + oxStat((b.div || {}).r90, x.base90) + '. ' + x.n_cap + ' capitulations: 30 days later ' + oxStat((b.cap || {}).r30) + '. A slight edge, but May 2022 fell another 26% after a divergence; not entity-adjusted, so exchange-internal moves count as losses.'), 'neu']);
    return it;
  }
  function rlPanel() {
    var x = (D.onchain || {}).rloss; if (!x || !x.rows) return '';
    var P = (x.pairs || []).slice(-6).reverse();
    var tb = '<div class="tbl-wrap" style="margin-top:12px"><table class="tbl"><thead><tr><th>' + _T('前一個低點', 'Previous low') + '</th><th>' + _T('這一個低點', 'This low') + '</th><th class="num">' + _T('認賠峰值（bp）', 'Loss peak (bp)') + '</th><th>' + _T('判定', 'Call') + '</th><th class="num">30 ' + _T('天後', 'd later') + '</th></tr></thead><tbody>' +
      P.map(function (p) { return '<tr><td class="num">' + ymdS(p.prev) + ' ' + fmt.k(p.prev_price) + '</td><td class="num">' + ymdS(p.date) + ' ' + fmt.k(p.price) + '</td><td class="num">' + fmt.n(p.prev_bp, 1) + ' → ' + fmt.n(p.bp, 1) + '</td><td>' + _T(RL_KIND[p.kind][0], RL_KIND[p.kind][1]) + '</td><td class="num">' + (p.r30 == null ? '—' : '<span style="color:var(--' + (p.r30 >= 0 ? 'up' : 'down') + ')">' + fmt.pct(p.r30, 0) + '</span>') + '</td></tr>'; }).join('') + '</tbody></table></div>';
    return panel('span-12', _T('實現虧損：峰值背離', 'Realized loss: peak divergence'), 'Bitview · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard('var(--down)', _T('今日認賠', 'Loss realized today'), '$' + fmt.n(x.usd_m, 0) + 'M', _T('7 天合計 ' + oxUsd(x.usd7_m * 1e6), '7-day total ' + oxUsd(x.usd7_m * 1e6))) +
      (function () { var cs = chState(); return cs ? oxCard(CH_KIND[cs.c.kind][2], _T('認賠峰值的背離', 'Loss-peak divergence'), '<span style="font-size:.62em">' + cs.t + '</span>', fmt.md(cs.c.a) + ' ' + oxUsd(cs.c.ua * 1e6) + ' → ' + fmt.md(cs.c.b) + ' ' + oxUsd(cs.c.ub * 1e6)) : ''; })() + '</div>' +
      interpHtml(rlossSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('每日實現虧損（百萬美元）', 'Daily realized loss ($M)'), 'var(--down)', 'box'], [_T('搬家日', 'Internal-transfer day'), 'var(--ink-3)', 'box'], [_T('背離', 'Divergence'), 'var(--s3)'], [_T('背離被打破', 'Divergence broken'), 'var(--down)'], [_T('認賠放大', 'Loss grows'), 'var(--warn)']]) +
      '<div class="chart cf-chart" id="c-rloss"></div>' + tb +
      '<p class="note">' + _T('長期圖：每日實現虧損 ÷ 市值（萬分之，跨年份才能比），每 4 天取最大，刻度壓縮過；輔助線只畫二次以上的背離與背離被打破。', 'Long view: daily realized loss ÷ market cap (basis points, comparable across years), the largest of every 4 days, on a compressed scale; helper lines show only 2nd-or-later divergences and broken divergences.') + ' ' + _T('全網每日實現虧損（賣出價低於最後移動價格的部分，Bitview 逐筆 UTXO、不是實體調整）。擺動低點＝前後 7 天最低、比之前 30 天最高跌 6% 以上，取前後 3 天內最大的認賠；和 75 天內前一個低點比，小 20% 以上算背離、大 25% 以上算投降。只作讀值。',
        'Network realized loss per day (sold below the last-moved price; Bitview per-UTXO, not entity-adjusted). A swing low is the lowest close within 7 days either side and 6%+ below the prior 30-day high; its loss peak is the largest within 3 days. Against the previous low within 75 days, 20%+ smaller counts as divergence and 25%+ larger as capitulation. Reading only.') + '</p>',
      (x.hist ? '<div class="seg" id="rl-seg"><button aria-pressed="' + (rlMode === 'near') + '" data-m="near">' + _T('近 150 天', 'Last 150 days') + '</button><button aria-pressed="' + (rlMode === 'all') + '" data-m="all">' + _T('全部歷史', 'Full history') + '</button></div>' : ''), 'rloss');
  }
  var rlMode = 'near';   // 2026-11-06 使用者：「只有短期的？沒有長期的圖？」→ 近 150 天／全部歷史切換
  var RL_T = function (v) { return Math.sqrt(Math.max(0, v)); };
  function drawRl(el) {
    var x = (D.onchain || {}).rloss; if (!x || !el) return;
    if (rlMode === 'all' && x.hist) {
      var HL = x.hlinks || [], lk2 = [];
      HL.forEach(function (c) { var col = CH_KIND[c.kind][2], d = c.kind === 'div' ? null : '5 4'; lk2.push({ x0: dnOf(c.a), y0: c.pa, x1: dnOf(c.b), y1: c.pb, col: col, price: true, dash: d }, { x0: dnOf(c.a), y0: c.ra, x1: dnOf(c.b), y1: c.rb, col: col, dash: d, w: 1.8 }); });
      oxPane(el, { rows: x.hist, label: _T('每日實現虧損 ÷ 市值（萬分之，壓縮刻度）', 'Daily realized loss ÷ market cap (bp, compressed scale)'), aria: _T('BTC 價格與實現虧損（全部歷史）', 'BTC price and realized loss (full history)'), y0: 0, tf: RL_T,
        ticks: [0, 5, 25, 100, 400], fmt: function (t) { return t + ' bp'; }, links: lk2,
        lines: [{ i: 2, col: 'var(--down)', area: true, w: 1.1, name: _T('實現虧損 ÷ 市值', 'Realized loss ÷ market cap'), tfmt: function (v) { return fmt.n(v, 1) + ' bp'; } }] });
      return;
    }
    var CH = (x.chain || []).filter(function (c) { return c.kind === 'div' || c.kind === 'break' || c.kind === 'cap'; }), lk = [];
    var labN = CH.filter(function (c) { return c.kind !== 'cap'; }).slice(-3);   // 線上文字只標最近三段的背離／打破，避免擠在一起
    CH.forEach(function (c) { var col = CH_KIND[c.kind][2], d = c.kind === 'div' ? null : '5 4';   // 上格連兩個峰值當天的價格、下格連兩個認賠峰值
      lk.push({ x0: dnOf(c.a), y0: c.pa, x1: dnOf(c.b), y1: c.pb, col: col, price: true, dash: d }, { x0: dnOf(c.a), y0: c.ua, x1: dnOf(c.b), y1: c.ub, col: col, dash: d, w: 2, lab: labN.indexOf(c) >= 0 ? chLab(c) + (c.conf ? '' : _T('（暫定）', '?')) : '' }); });
    oxPane(el, { rows: x.rows, label: _T('每日實現虧損（百萬美元）', 'Daily realized loss ($M)'), aria: _T('BTC 價格與每日實現虧損', 'BTC price and daily realized loss'), y0: 0, links: lk,
      bars: { i: 2, name: _T('實現虧損', 'Realized loss'), col: function (r) { return r[4] ? 'var(--ink-3)' : 'var(--down)'; }, op: 0.85, tfmt: function (v, p) { return fmt.usd(v * 1e6) + (p[4] ? _T('（搬家日）', ' (transfer day)') : ''); } },
      fmt: function (t) { return t >= 1000 ? fmt.n(t / 1000, 1) + 'B' : t + 'M'; },
      over: null });
  }

  /* ⑤ 長短期持有者供給比的 30 日變化：負＝老幣被花掉、由短期持有者接走（需求在吸收供給）；正＝籌碼沉澱 */
  /* 2026-11-09 改名（原本也叫 lcSay，蓋掉了「價格 × 長期持有者動向」的 lcSay，那張圖 11/06 起顯示成這張的解讀） */
  function lrSay() {
    var x = D.onchain.lsrchg, it = [];
    it.push([_T('30 日變化', '30-day change'), fmt.pct(x.value, 1),
      _T('長短期持有者供給比 ' + fmt.n(x.ratio, 2) + '，30 天' + fmt.pct(x.value, 1) + '；' + ymdS(x.since) + ' 起連 ' + x.days + ' 天' + (x.neg ? '為負：長期持有者的幣在流向短期持有者。' : '為正：籌碼在沉澱（也包括幣放滿 155 天自動轉成長期）。'),
        'LTH/STH supply ratio ' + fmt.n(x.ratio, 2) + ', ' + fmt.pct(x.value, 1) + ' over 30 days; ' + (x.neg ? 'negative' : 'positive') + ' for ' + x.days + ' days since ' + ymdS(x.since) + (x.neg ? ': long-term holders\' coins are passing to short-term holders.' : ': supply is settling (including coins aging past 155 days).')), 'neu']);
    it.push([_T('主升段與過渡期', 'Main up-waves and transitions'), x.all_neg + _T('% 為負', '% negative'),
      _T('週期頂部前一年為負的天數：' + (x.up || []).map(function (u) { return u.top.slice(0, 4) + ' ' + u.neg + '%'; }).join('、') + '；熊底後一年：' + (x.trans || []).map(function (t) { return t.bottom.slice(0, 4) + ' ' + t.neg + '%' + (t.open ? '（未滿一年）' : ''); }).join('、') + '（全部日子 ' + x.all_neg + '%）。負值多＝需求接得住長期持有者的賣出；2023 年過渡期接近一半一半，價格走得較平。',
        'Share of negative days in the year before each cycle top: ' + (x.up || []).map(function (u) { return u.top.slice(0, 4) + ' ' + u.neg + '%'; }).join(', ') + '; in the year after each bear bottom: ' + (x.trans || []).map(function (t) { return t.bottom.slice(0, 4) + ' ' + t.neg + '%' + (t.open ? ' (under a year)' : ''); }).join(', ') + ' (all days ' + x.all_neg + '%). More negative days = demand absorbing long-term holders\' selling; the 2023 transition was close to even and price moved more flatly.'), 'neu']);
    return it;
  }
  function lcPanel() {
    var x = (D.onchain || {}).lsrchg; if (!x || !x.rows) return '';
    return panel('span-12', _T('長短期持有者供給比：30 日變化', 'LTH/STH supply ratio: 30-day change'), 'Bitview · ' + fmt.md(x.date),
      interpHtml(lrSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('為負：長期持有者的幣流向短期持有者', 'Negative: long-term holder coins passing to short-term holders'), 'var(--s2)', 'box'], [_T('為正：籌碼沉澱', 'Positive: supply settling'), 'var(--s3)', 'box'], [_T('淡黃底：週期頂部前一年（主升段）', 'Pale amber: the year before each cycle top (main up-leg)'), 'var(--warn)', 'box'], [_T('淡藍底：熊底後一年（過渡期）', 'Pale blue: the year after each bear bottom (transition)'), 'var(--stg1)', 'box']]) +
      '<div class="chart cf-chart" id="c-lsrchg"></div><p class="note">' + _T('長期持有者供給 ÷ 短期持有者供給（Bitview，155 天分界）的 30 日變化。幣放滿 155 天會自動從短期轉成長期，所以沒有人交易時比值也會慢慢上升。只作讀值。',
        '30-day change of LTH supply ÷ STH supply (Bitview, 155-day split). Coins move from short- to long-term automatically after 155 days, so the ratio drifts up even with no trading. Reading only.') + '</p>', '', 'lsrchg');
  }
  function drawLc(el) {
    var x = (D.onchain || {}).lsrchg; if (!x || !el) return;
    oxPane(el, { rows: x.rows, label: _T('供給比 30 日變化（%）', 'Supply ratio, 30-day change (%)'), aria: _T('BTC 價格與長短期持有者供給比 30 日變化', 'BTC price and LTH/STH supply ratio change'), zero: true,
      lines: [{ i: 2, split: ['var(--s3)', 'var(--s2)'], w: 1.4, name: _T('30 日變化', '30-day change'), tfmt: function (v) { return fmt.pct(v, 1); } }], fmt: function (t) { return t + '%'; },
      vbands: (D.cycle.tops || []).map(function (t) { return { x0: dnOf(t[0]) - 365, x1: dnOf(t[0]), col: 'var(--warn)', op: 0.09 }; })   // 2026-11-06 使用者：「這三個陰影部分什麼意思，沒有寫出來」→ 圖例寫明，並補畫熊底後一年
        .concat((D.cycle.bottoms || []).map(function (b) { return { x0: dnOf(b[0]), x1: Math.min(dnOf(b[0]) + 365, dnOf(x.date)), col: 'var(--stg1)', op: 0.12 }; })),
      now: { i: 2, col: x.neg ? 'var(--s2)' : 'var(--s3)', lab: _T('現在 ', 'Now ') + fmt.pct(x.value, 1) } });
  }

  /* ⑥ 資金與價格增量梯度：價格 N 天漲跌 − 實現價格（全體平均成本）N 天漲跌，除以自己的 4 年標準差。正＝價格跑得比資金快 */
  var DV_KIND = { top: ['頂背離', 'bearish divergence'], bot: ['底背離', 'bullish divergence'] };
  function grSay() {
    var x = D.onchain.grad, it = [], last = function (L) { return (L || []).slice(-1)[0]; };
    var a = last(x.div120), b = last(x.div30);
    it.push([_T('大級別（120 日）', 'Long frame (120d)'), (x.z120 >= 0 ? '+' : '') + fmt.n(x.z120, 2),
      _T(x.z120 >= 0 ? '近 120 天價格漲得比資金流入快（' + fmt.n(x.z120, 2) + ' 個標準差）：價格靠情緒多過靠新資金。' : '近 120 天價格跌得比資金撤出快（' + fmt.n(x.z120, 2) + ' 個標準差）。',
        x.z120 >= 0 ? 'Over 120 days price has run ahead of capital inflow (' + fmt.n(x.z120, 2) + ' SD): more sentiment than new money.' : 'Over 120 days price has fallen faster than capital left (' + fmt.n(x.z120, 2) + ' SD).') +
      (a ? _T('最近一次：' + ymdS(a.date) + ' ' + DV_KIND[a.kind][0] + '（' + fmt.n(a.za, 2) + ' → ' + fmt.n(a.zb, 2) + '）。', ' Latest: ' + ymdS(a.date) + ' ' + DV_KIND[a.kind][1] + ' (' + fmt.n(a.za, 2) + ' → ' + fmt.n(a.zb, 2) + ').') : ''), x.z120 >= 1.5 ? 'warn' : 'neu']);
    it.push([_T('小級別（30 日）', 'Short frame (30d)'), (x.z30 >= 0 ? '+' : '') + fmt.n(x.z30, 2),
      _T('近 30 天' + (x.z30 >= 0 ? '價格跑得比資金快。' : '價格跌得比資金撤得快。'), 'Over 30 days price ' + (x.z30 >= 0 ? 'has run ahead of capital.' : 'has fallen faster than capital left.')) +
      (b ? _T('最近一次：' + ymdS(b.date) + ' ' + DV_KIND[b.kind][0] + (b.r30 != null ? '（30 天後 ' + fmt.pct(b.r30, 0) + '）' : '') + '。小級別容易被消息打破。', ' Latest: ' + ymdS(b.date) + ' ' + DV_KIND[b.kind][1] + (b.r30 != null ? ' (30d later ' + fmt.pct(b.r30, 0) + ')' : '') + '. The short frame is easily broken by news.') : ''), 'neu']);
    var k = x.back120 || {}, s = x.back30 || {};
    it.push([_T('過去的背離', 'Past divergences'), (k.bot || {}).n + ' / ' + (k.top || {}).n,
      _T('2015 年起，120 日底背離 ' + (k.bot || {}).n + ' 次：90 天後 ' + oxStat((k.bot || {}).r90, x.base90) + '；頂背離 ' + (k.top || {}).n + ' 次：90 天後 ' + oxStat((k.top || {}).r90) + '，60 天內最大跌幅中位數 ' + fmt.pct((k.top || {}).dd60_med, 1) + '。30 日頂背離 ' + (s.top || {}).n + ' 次：30 天後 ' + oxStat((s.top || {}).r30, x.base30) + '。',
        'Since 2015: ' + (k.bot || {}).n + ' 120-day bullish divergences, 90 days later ' + oxStat((k.bot || {}).r90, x.base90) + '; ' + (k.top || {}).n + ' bearish, 90 days later ' + oxStat((k.top || {}).r90) + ', median max drawdown within 60 days ' + fmt.pct((k.top || {}).dd60_med, 1) + '. ' + (s.top || {}).n + ' 30-day bearish divergences: 30 days later ' + oxStat((s.top || {}).r30, x.base30) + '.'), 'neu']);
    return it;
  }
  function grPanel() {
    var x = (D.onchain || {}).grad; if (!x || !x.rows) return '';
    return panel('span-12', _T('資金與價格增量梯度', 'Capital vs price momentum'), 'Bitview · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard('var(--s4)', _T('大級別（120 日）', 'Long frame (120d)'), (x.z120 >= 0 ? '+' : '') + fmt.n(x.z120, 2), _T('標準差；正＝價格跑得比資金快', 'SD; positive = price ahead of capital')) + oxCard('var(--s2)', _T('小級別（30 日）', 'Short frame (30d)'), (x.z30 >= 0 ? '+' : '') + fmt.n(x.z30, 2), _T('標準差；比較敏感', 'SD; more sensitive')) + '</div>' +
      interpHtml(grSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], ['120 ' + _T('日', 'day'), 'var(--s4)'], ['30 ' + _T('日', 'day'), 'var(--s2)'], [_T('底背離', 'Bullish divergence'), 'var(--s3)'], [_T('頂背離', 'Bearish divergence'), 'var(--warn)']]) +
      '<div class="chart cf-chart" id="c-grad"></div><p class="note">' + _T('（價格 N 天的對數漲跌 − 實現價格 N 天的對數漲跌）÷ 自己過去 4 年的標準差，沒有前視。實現價格＝全體幣的平均買進成本，代表真正進出的資金。背離＝價格擺動新高（新低）而梯度沒有。本站自己的算法，只作讀值。',
        '(N-day log change of price − N-day log change of realized price) ÷ its own 4-year standard deviation, no look-ahead. Realized price = the average cost of all coins, i.e. the money that actually moved in or out. Divergence = price makes a new swing high (low) and the gauge does not. Our own construction; reading only.') + '</p>', '', 'grad');
  }
  function drawGr(el) {
    var x = (D.onchain || {}).grad; if (!x || !el) return;
    var mk = function (L, y) { return (L || []).map(function (d) { return { x: dnOf(d.date), y: d.zb, col: d.kind === 'top' ? 'var(--warn)' : 'var(--s3)', t: _T(DV_KIND[d.kind][0], d.kind === 'top' ? 'Bear div' : 'Bull div') + ' ' + fmt.md(d.date), up: d.kind === 'top' }; }); };
    oxPane(el, { rows: x.rows, label: _T('梯度（標準差）', 'Gauge (SD)'), aria: _T('BTC 價格與資金價格梯度', 'BTC price and capital-price gauge'), zero: true,
      lines: [{ i: 2, col: 'var(--s2)', w: 1, op: 0.55, name: '30 ' + _T('日', 'day'), glow: false, tfmt: function (v) { return fmt.n(v, 2); } }, { i: 3, split: ['var(--s4)', 'var(--s4)'], w: 2, name: '120 ' + _T('日', 'day'), tfmt: function (v) { return fmt.n(v, 2); } }],
      links: (x.div120 || []).reduce(function (a, d) { var c = d.kind === 'top' ? 'var(--warn)' : 'var(--s3)'; return a.concat([{ x0: dnOf(d.prev), y0: d.prev_price, x1: dnOf(d.date), y1: d.price, col: c, price: true, dash: '5 4' }, { x0: dnOf(d.prev), y0: d.za, x1: dnOf(d.date), y1: d.zb, col: c, dash: '5 4', w: 1.8 }]); }, []),
      marks: mk((x.div120 || []).slice(-3)), now: { i: 3, col: 'var(--s4)', lab: _T('現在 ', 'Now ') + fmt.n(x.z120, 2) } });
  }

  /* ⑦ 鏈上勢能：（SOPR − 1）× 每日銷毀幣天數，14 日平均。正＝賣出的幣在獲利而且老幣在動（獲利了結的力道）；頂背離＝價格新高但正值峰值更低 */
  var MO_T = function (v) { return (v >= 0 ? 1 : -1) * Math.log10(1 + Math.abs(v) / 20); };
  function moSay() {
    var x = D.onchain.mom, it = [], dv = (x.divs || []).slice(-1)[0];
    it.push([_T('現在', 'Now'), fmt.n(x.value, 0),
      x.value >= 0 ? _T('正值：賣出的幣整體在獲利' + (x.hump ? '，這一段從 ' + ymdS(x.hump.start) + ' 開始，峰值 ' + fmt.n(x.hump.peak_v, 0) + '（' + ymdS(x.hump.peak) + '）' : '') + '。', 'Positive: coins sold are in profit overall' + (x.hump ? '; this stretch began ' + ymdS(x.hump.start) + ', peaking at ' + fmt.n(x.hump.peak_v, 0) + ' (' + ymdS(x.hump.peak) + ')' : '') + '.')
        : _T('負值：賣出的幣整體在認賠，獲利了結的推力暫時消失。', 'Negative: coins sold are at a loss overall; the push from profit-taking has faded for now.'), x.value >= 0 ? 'neu' : 'warn']);
    it.push([_T('頂背離之後', 'After bearish divergences'), fmt.pct(x.dd60_med, 0),
      _T('2015 年起頂背離 ' + x.n + ' 次（價格擺動新高、正值峰值較低），之後 60 天內最大跌幅中位數 ' + fmt.pct(x.dd60_med, 1) + (x.dd60_q ? '（一半在 ' + fmt.pct(x.dd60_q[1], 0) + ' 到 ' + fmt.pct(x.dd60_q[0], 0) + '）' : '') + '，同期任一天 ' + fmt.pct(x.base_dd60, 1) + '；30 天後 ' + oxStat(x.r30, x.base30) + '。' + (dv ? '最近一次 ' + ymdS(dv.date) + (dv.dd60 != null ? '，之後 60 天最多跌 ' + fmt.pct(dv.dd60, 0) : (dv.r30 != null ? '，30 天後 ' + fmt.pct(dv.r30, 0) : '')) + '。' : ''),
        'Since 2015, ' + x.n + ' bearish divergences (price at a higher swing high, positive peak lower): median max drawdown within 60 days ' + fmt.pct(x.dd60_med, 1) + (x.dd60_q ? ' (middle half ' + fmt.pct(x.dd60_q[1], 0) + ' to ' + fmt.pct(x.dd60_q[0], 0) + ')' : '') + ' vs ' + fmt.pct(x.base_dd60, 1) + ' for any day; 30 days later ' + oxStat(x.r30, x.base30) + '.' + (dv ? ' Latest ' + ymdS(dv.date) + (dv.dd60 != null ? ', max drawdown within 60 days ' + fmt.pct(dv.dd60, 0) : (dv.r30 != null ? ', 30 days later ' + fmt.pct(dv.r30, 0) : '')) + '.' : '')), 'neu']);
    return it;
  }
  function moPanel() {
    var x = (D.onchain || {}).mom; if (!x || !x.rows) return '';
    return panel('span-12', _T('鏈上勢能（SOPR × 銷毀幣天數）', 'On-chain momentum (SOPR × coin days destroyed)'), 'Bitview · ' + fmt.md(x.date),
      interpHtml(moSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('獲利了結（正）', 'Profit-taking (positive)'), 'var(--up)', 'box'], [_T('認賠（負）', 'Loss-taking (negative)'), 'var(--down)', 'box'], [_T('頂背離（虛線連兩個高點，2017 年起全部）', 'Bearish divergence (dashed, joining the two highs; all since 2017)'), 'var(--warn)']]) +
      '<div class="chart cf-chart" id="c-mom"></div><p class="note">' + _T('（全網 SOPR − 1）× 每日銷毀幣天數（千），14 日指數平均；刻度壓縮過（大的數字被縮小），看方向和峰值高低。頂背離＝價格擺動新高、正值峰值比前一次低。本站自己的組合，只作讀值。',
        '(Network SOPR − 1) × coin days destroyed per day (thousands), 14-day exponential average; the scale is compressed (large values shrunk) — read direction and relative peaks. Bearish divergence = price at a higher swing high with a lower positive peak. Our own construction; reading only.') + '</p>', '', 'mom');
  }
  function drawMo(el) {
    var x = (D.onchain || {}).mom; if (!x || !el) return;
    oxPane(el, { rows: x.rows, label: _T('鏈上勢能（壓縮刻度）', 'On-chain momentum (compressed scale)'), aria: _T('BTC 價格與鏈上勢能', 'BTC price and on-chain momentum'), zero: true, tf: MO_T,
      ticks: [-1000, -100, 0, 100, 1000, 5000], fmt: function (t) { return Math.abs(t) >= 1000 ? (t / 1000) + 'K' : String(t); },
      lines: [{ i: 2, split: ['var(--up)', 'var(--down)'], w: 1.3, name: _T('鏈上勢能', 'Momentum'), tfmt: function (v) { return fmt.n(v, 0); } }],
      links: (x.divs || []).reduce(function (a, d) { return a.concat([{ x0: dnOf(d.prev), y0: d.prev_price, x1: dnOf(d.date), y1: d.price, col: 'var(--warn)', price: true, dash: '5 4' }, { x0: dnOf(d.prev), y0: d.za, x1: dnOf(d.date), y1: d.zb, col: 'var(--warn)', dash: '5 4', w: 1.8 }]); }, []),
      marks: (x.divs || []).slice(-3).map(function (d) { return { x: dnOf(d.date), y: d.zb, col: 'var(--warn)', t: _T('頂背離 ', 'Bear div ') + fmt.md(d.date) + (d.dd60 != null ? ' ' + fmt.pct(d.dd60, 0) : '') }; }),
      now: { i: 2, col: x.value >= 0 ? 'var(--up)' : 'var(--down)', lab: _T('現在 ', 'Now ') + fmt.n(x.value, 0) } });
  }

  /* ⑧ 籌碼缺口與雙錨：現價 ±30% 內最大的兩個籌碼峰（雙錨）、中間籌碼很薄的價位（缺口，上次通過時沒有充分換手）、近 7 天換手最多的價位。讀值併進「籌碼分布」 */
  function urpdGaps() {
    var v = (D.chips || {}).viz || {}, u = v.urpd || {}, c = D.price.bar.c, W = u.width || 2000;
    var B = (u.band || []).filter(function (b) { return b[0] >= c * 0.7 && b[0] <= c * 1.3; }); if (B.length < 8) return null;
    var best = null;   // 雙錨：中間至少有一格籌碼不到兩邊較小那個的 1/4（缺口），兩邊都越厚越好
    for (var i = 0; i < B.length; i++) for (var j = i + 3; j < B.length; j++) {
      var m = Math.min(B[i][1], B[j][1]), thin = B.slice(i + 1, j).filter(function (b) { return b[1] < 0.25 * m; }).length;
      if (thin && B.slice(i + 1, j).every(function (b) { return b[1] <= m; }) && (!best || m > best[2])) best = [B[i], B[j], m];
    }
    if (!best) return null;
    var a1 = best[0], a2 = best[1], lo = a1[0], hi = a2[0], th = 0.25 * best[2], gaps = [], g = null;
    B.forEach(function (b) { if (b[0] > lo && b[0] < hi && b[1] < th) { if (g && b[0] === g[1] + W) g[1] = b[0]; else { g = [b[0], b[0]]; gaps.push(g); } } else g = null; });
    var pv = {}; ((u.prev7 || {}).band || []).forEach(function (b) { pv[b[0]] = b[1]; });
    var gr = B.filter(function (b) { return pv[b[0]] != null; }).map(function (b) { return [b[0], b[1] - pv[b[0]]]; }).sort(function (a, b) { return b[1] - a[1]; });
    return { a: [a1, a2].sort(function (p, q) { return p[0] - q[0]; }), gaps: gaps, grow: gr.slice(0, 2), W: W, prevDate: (u.prev7 || {}).date };
  }
  function urpdGapSay() {
    var g = urpdGaps(); if (!g) return '';
    var rng = function (a, b) { return fmt.k(a) + '–' + fmt.k(b + g.W); }, wan = function (v) { return _T(fmt.n(v / 1e4, 1) + ' 萬顆', fmt.n(v / 1e3, 0) + 'K BTC'); };
    return '<p class="say">' + _T('雙錨：' + rng(g.a[0][0], g.a[0][0]) + '（' + wan(g.a[0][1]) + '）與 ' + rng(g.a[1][0], g.a[1][0]) + '（' + wan(g.a[1][1]) + '）。', 'Two anchors: ' + rng(g.a[0][0], g.a[0][0]) + ' (' + wan(g.a[0][1]) + ') and ' + rng(g.a[1][0], g.a[1][0]) + ' (' + wan(g.a[1][1]) + '). ') +
      (g.gaps.length ? _T('中間的缺口：' + g.gaps.map(function (x) { return rng(x[0], x[1]); }).join('、') + '（上次通過時沒有充分換手，價格回來常會停留補量）。', 'Gaps between them: ' + g.gaps.map(function (x) { return rng(x[0], x[1]); }).join(', ') + ' (little turnover when price last passed; price often lingers there to fill them). ') : _T('兩錨之間沒有明顯缺口。', 'No clear gap between them. ')) +
      (g.grow.length && g.grow[0][1] > 0 ? _T('近 7 天換手最多：' + g.grow.filter(function (x) { return x[1] > 0; }).map(function (x) { return rng(x[0], x[0]) + ' +' + wan(x[1]); }).join('、') + '。', 'Most turnover in 7 days: ' + g.grow.filter(function (x) { return x[1] > 0; }).map(function (x) { return rng(x[0], x[0]) + ' +' + wan(x[1]); }).join(', ') + '.') : '') + '</p>';
  }

  /* ⑨ 回調壓力清單：過去熊牛過渡期回調的後段常同時出現的條件。只作讀值，不是買點 */
  var PB_LAB = { sth: ['① 價格回到短期持有者成本', '① Price back at STH cost'], psip: ['② 獲利供給 ≤ 65%', '② Supply in profit ≤ 65%'], sthl: ['③ 短期持有者虧損 ≥ 50%', '③ STH in loss ≥ 50%'], sec: ['④ 賣方衰竭進極端區', '④ Seller exhaustion in extreme zone'], rloss: ['⑤ 實現虧損峰值背離', '⑤ Realized-loss peak divergence'] };
  function pbPanel() {
    var x = (D.onchain || {}).pullback; if (!x || !x.items) return '';
    var val = function (it) { return it.id === 'sth' ? fmt.pct(it.v, 1) : it.id === 'sec' ? fmt.n(it.v, 3) : it.id === 'rloss' ? (it.v ? _T(RL_KIND[it.v][0], RL_KIND[it.v][1]) : '—') : fmt.n(it.v, 1) + '%'; };
    var cond = function (it) { return it.id === 'sth' ? _T('收盤在成本 ' + fmt.usd(it.ref) + ' 的 3% 以內或以下', 'Close within 3% of, or below, the ' + fmt.usd(it.ref) + ' cost') : it.id === 'sec' ? _T('低於 ' + it.ref + '（輔助，見賣方衰竭）', 'Below ' + it.ref + ' (auxiliary; see seller exhaustion)') : it.id === 'rloss' ? _T('近 30 天的一對低點（輔助）', 'Pair of lows in 30 days (auxiliary)') : it.id === 'psip' ? _T('全體供給有多少在獲利', 'Share of all coins in profit') : _T('短期持有者有多少在虧損', 'Share of short-term holders underwater'); };
    var L = '<div class="lights pb">' + x.items.map(function (it) { return '<div class="light' + (it.ok ? ' on' : '') + '"><span class="mk">' + (it.ok ? '✓' : '·') + '</span><b>' + _T(PB_LAB[it.id][0], PB_LAB[it.id][1]) + '</b><span class="v num">' + val(it) + '</span><span class="note">' + cond(it) + '</span></div>'; }).join('') + '</div>';
    var E = (x.eps || []).filter(function (e) { return e.r30 != null; }).slice(-5);
    var say = [[_T('現在', 'Now'), x.n_ok + ' / ' + x.n, _T('五項中 ' + x.n_ok + ' 項成立。①–③ 每天可回測，④⑤ 只看現在。', x.n_ok + ' of 5 hold. ①–③ can be back-tested daily; ④–⑤ are current only.'), 'neu'],
      [_T('①–③ 同時成立之後', 'After ①–③ all held'), x.r30.up + ' / ' + x.r30.n,
        _T('2015 年起三項同時成立 ' + x.n_eps + ' 段（共 ' + x.days + ' 天），30 天後 ' + oxStat(x.r30, x.base30) + '；90 天後 ' + oxStat(x.r90, x.base90) + '。熊市中段也常三項同時成立（2018、2022 年），所以這張清單描述的是「回調的壓力釋放到哪裡」，不是買點。最近幾段：' + E.map(function (e) { return ymdS(e.start) + '（' + e.days + ' 天，30 天後 ' + oxP0(e.r30) + '）'; }).join('、') + '。',
          'Since 2015 all three held in ' + x.n_eps + ' stretches (' + x.days + ' days). 30 days later: ' + oxStat(x.r30, x.base30) + '; 90 days later: ' + oxStat(x.r90, x.base90) + '. They also line up in the middle of bear markets (2018, 2022), so this list shows how far pullback pressure has been released — not a buy signal. Recent: ' + E.map(function (e) { return ymdS(e.start) + ' (' + e.days + ' days, 30d ' + oxP0(e.r30) + ')'; }).join(', ') + '.'), 'neu']];
    return panel('span-12', _T('回調壓力清單', 'Pullback pressure checklist'), 'Bitview · CheckOnChain · ' + fmt.md(x.date), L + interpHtml(say, true), '', 'pullback');
  }

  /* ⑪ 選擇權 Gamma 曝險（依履約價）：做市商部位用逐筆成交推算。正 Gamma＝逆勢對沖（吸住價格），負＝順勢對沖（放大波動）。下方淡色＝籌碼分布 */
  var gxMode = 'all';
  function gxSay() {
    var x = D.deriv.gex, it = [], k = function (r) { return fmt.k(r[0]) + ' ' + (r[2] >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(r[2]), 0) + 'M'; };
    it.push([_T('現價附近', 'Around spot'), fmt.k(x.spot),
      _T('45 天內到期的合約合計：現價上方 ' + (x.above >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.above), 0) + 'M、下方 ' + (x.below >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.below), 0) + 'M（價格每動 1% 做市商要對沖的金額，正＝漲賣跌買、負＝追漲殺跌）。正 Gamma 最大：' + x.pos.map(k).join('、') + '；負 Gamma 最大：' + x.neg.map(k).join('、') + '。',
        'Expiries within 45 days: ' + (x.above >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.above), 0) + 'M above spot and ' + (x.below >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.below), 0) + 'M below (what dealers must hedge per 1% move; positive = sell rallies and buy dips, negative = chase the move). Largest positive: ' + x.pos.map(k).join(', ') + '; largest negative: ' + x.neg.map(k).join(', ') + '.'), 'neu']);
    if ((x.overlap || []).length) it.push([_T('和籌碼峰重疊', 'Overlap with supply clusters'), x.overlap.map(function (o) { return fmt.k(o.strike); }).join(' / '),
      _T(x.overlap.map(function (o) { return fmt.k(o.strike) + '（正 Gamma $' + fmt.n(o.gex, 0) + 'M，籌碼 ' + fmt.n(o.btc / 1e4, 1) + ' 萬顆）'; }).join('、') + '：衍生品的對沖買盤和鏈上的成本密集區在同一個價位。',
        x.overlap.map(function (o) { return fmt.k(o.strike) + ' (positive gamma $' + fmt.n(o.gex, 0) + 'M, ' + fmt.n(o.btc / 1e3, 0) + 'K BTC of supply)'; }).join(', ') + ': dealer hedging and an on-chain cost cluster sit at the same price.'), 'neu']);
    it.push([_T('主要到期日', 'Main expiry'), fmt.md(x.main), _T(ymdS(x.main) + ' 佔 45 天內未平倉的 ' + fmt.n(x.main_share, 0) + '%。正 Gamma 的吸附在到期前兩三天最強，到期後缓衝消失、波動常會放大。推算覆蓋率 ' + x.coverage + '%（有逐筆成交可推算做市商方向的未平倉比例）。',
      ymdS(x.main) + ' holds ' + fmt.n(x.main_share, 0) + '% of open interest within 45 days. Positive-gamma pinning is strongest in the last two or three days; after expiry the cushion goes and volatility often picks up. Coverage ' + x.coverage + '% (share of open interest whose dealer side could be inferred from trades).'), 'neu']);
    return it;
  }
  function gxPanel() {
    var x = (D.deriv || {}).gex; if (!x || !x.rows) return '';
    var segs = '<div class="seg" id="gx-seg"><button aria-pressed="' + (gxMode === 'all') + '" data-m="all">' + _T('45 天內', 'Within 45d') + '</button><button aria-pressed="' + (gxMode === 'main') + '" data-m="main">' + fmt.md(x.main) + '</button></div>';
    return panel('span-12', _T('選擇權 Gamma 曝險（推算）', 'Options gamma exposure (estimated)'), 'Deribit · ' + x.ts.slice(5, 16).replace('T', ' ') + ' UTC',
      interpHtml(gxSay()) + legend([[_T('正 Gamma（吸住價格）', 'Positive gamma (pins price)'), 'var(--up)', 'box'], [_T('負 Gamma（放大波動）', 'Negative gamma (amplifies moves)'), 'var(--down)', 'box'], [_T('籌碼分布', 'Supply distribution'), 'var(--ink-3)', 'box'], [_T('現價', 'Spot'), 'var(--flare)']]) +
      '<div class="chart cf-chart" id="c-gex"></div><p class="note">' + _T('每個合約：未平倉 × Black-Scholes gamma × 價格² × 1%，乘上推算的做市商部位方向（Deribit 逐筆成交裡主動買進＝做市商賣出，累計後限制在未平倉以內）。正負號是推算，Glassnode 等付費資料的做法可能不同；只作讀值。',
        'Per contract: open interest × Black-Scholes gamma × price² × 1%, signed by the inferred dealer side (in Deribit trades a taker buy is a dealer sale; summed and capped at open interest). The sign is an estimate and paid data vendors may differ; reading only.') + '</p>', segs, 'gex');
  }
  /* 2026-11-09 使用者：買權／賣權也照紅綠規則（買權＝多＝綠、賣權＝空＝品牌橘紅），各到期未平倉、履約價分布、Gamma 提示框一致 */
  function drawGex(el) {
    var x = (D.deriv || {}).gex; if (!x || !el) return;
    var R_ = x.rows, j = gxMode === 'main' ? 1 : 2, W = Math.max(280, el.clientWidth), sm = W < 520, ML = 8, MR = 58, MT = 16, MB = 26, hg = sm ? 190 : 250, hu = sm ? 50 : 64, gap = 18, H = MT + hg + gap + hu + MB, pw = W - ML - MR;
    var k0 = R_[0][0] - 500, k1 = R_[R_.length - 1][0] + 500, X = function (k) { return ML + (k - k0) / (k1 - k0) * pw; };
    var mx = Math.max.apply(null, R_.map(function (r) { return Math.abs(r[j]); })) || 1, Y = function (v) { return MT + hg / 2 - v / mx * (hg / 2 - 6); }, bw = Math.max(2, pw / (R_.length + 2) * 0.7), s = '';
    var st = niceStep(mx, 2); for (var t = -Math.floor(mx / st) * st; t <= mx; t += st) { var y = Y(t); s += '<line class="' + (t ? 'gl' : 'base') + '" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/>' + axText(ML + pw + 8, y + 3.5, (t < 0 ? '−' : '') + '$' + fmt.n(Math.abs(t), 0) + 'M'); }
    R_.forEach(function (r) { var v = r[j], y = Y(v), y0 = Y(0); s += '<rect x="' + (X(r[0]) - bw / 2).toFixed(1) + '" y="' + Math.min(y, y0).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + Math.max(0.6, Math.abs(y - y0)).toFixed(1) + '" rx="1.5" fill="' + (v >= 0 ? 'var(--up)' : 'var(--down)') + '"/>'; });
    // 下格：籌碼分布（每 2,000 美元一格）
    var U = (((D.chips || {}).viz || {}).urpd || {}).band || [], uw = (((D.chips || {}).viz || {}).urpd || {}).width || 2000, ub = MT + hg + gap + hu, um = Math.max.apply(null, U.filter(function (b) { return b[0] + uw > k0 && b[0] < k1; }).map(function (b) { return b[1]; }).concat([1]));
    U.forEach(function (b) { if (b[0] + uw <= k0 || b[0] >= k1) return; var a = Math.max(ML, X(b[0])), c = Math.min(ML + pw, X(b[0] + uw)), h = b[1] / um * (hu - 4); s += '<rect x="' + (a + 0.5).toFixed(1) + '" y="' + (ub - h).toFixed(1) + '" width="' + Math.max(0.5, c - a - 1).toFixed(1) + '" height="' + h.toFixed(1) + '" fill="var(--ink-3)" opacity=".45"/>'; });
    s += axText(ML, MT + hg + gap - 4, _T('籌碼分布', 'Supply distribution'));
    var sx = X(x.spot); s += '<line x1="' + sx.toFixed(1) + '" x2="' + sx.toFixed(1) + '" y1="' + MT + '" y2="' + ub + '" stroke="var(--flare)" stroke-width="1.5" stroke-dasharray="4 3"/>' + axText(sx + 4, MT + hg - 6, _T('現價 ', 'Spot ') + fmt.k(x.spot)).replace('class="ax"', 'class="ax" style="fill:var(--flare);font-weight:700"');
    var srt = R_.slice().sort(function (a, b) { return b[j] - a[j]; }), lab = srt.slice(0, 3).filter(function (r) { return r[j] > 0; }).concat(srt.slice(-3).filter(function (r) { return r[j] < 0; }));   // 依目前的檢視挑正負各前三
    if (!sm) lab.forEach(function (r) { var v = r[j]; if (Math.abs(v) < 0.5) return; s += axText(X(r[0]), v >= 0 ? Y(v) - 5 : Y(v) + 13, (v >= 0 ? '+' : '−') + fmt.n(Math.abs(v), 0), 'middle').replace('class="ax"', 'class="ax" style="font-weight:700;fill:' + (v >= 0 ? 'var(--up)' : 'var(--down)') + '"'); });
    var every = Math.max(1, Math.ceil(R_.length / (pw / 44)));
    R_.forEach(function (r, i) { if (i % every === 0) s += axText(X(r[0]), H - 8, fmt.k(r[0]), 'middle'); });
    s += axText(ML, MT - 5, _T('Gamma 曝險（百萬美元／價格變動 1%）', 'Gamma exposure ($M per 1% move)'));
    s += '<line class="xh" x1="0" x2="0" y1="' + MT + '" y2="' + ub + '" visibility="hidden"/><rect class="hit" x="' + ML + '" y="' + MT + '" width="' + pw + '" height="' + (ub - MT) + '"/>';
    el.innerHTML = svgEl(W, H, s, _T('依履約價的 Gamma 曝險', 'Gamma exposure by strike'));
    var svg = el.querySelector('svg'), xh = svg.querySelector('.xh'), hit = svg.querySelector('.hit');
    function move(ev) {
      var r = svg.getBoundingClientRect(), kv = k0 + ((ev.clientX - r.left) * W / r.width - ML) / pw * (k1 - k0), p = R_.reduce(function (a, b) { return Math.abs(b[0] - kv) < Math.abs(a[0] - kv) ? b : a; }), cx = X(p[0]);
      xh.setAttribute('x1', cx); xh.setAttribute('x2', cx); xh.setAttribute('visibility', 'visible');
      var ubk = U.filter(function (b) { return b[0] <= p[0] && p[0] < b[0] + uw; })[0];
      showTip(ev.clientX, ev.clientY, '<div class="t">' + _T('履約價 ', 'Strike ') + fmt.usd(p[0]) + '</div>' + tipRow1(p[j] >= 0 ? 'var(--up)' : 'var(--down)', 'Gamma', (p[j] >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(p[j]), 1) + 'M') + tipRow1('var(--up)', _T('買權未平倉（' + fmt.md(x.main) + '）', 'Call OI (' + fmt.md(x.main) + ')'), fmt.n(p[3]) + _T(' 顆', ' BTC')) + tipRow1('var(--down)', _T('賣權未平倉（' + fmt.md(x.main) + '）', 'Put OI (' + fmt.md(x.main) + ')'), fmt.n(p[4]) + _T(' 顆', ' BTC')) + (ubk ? tipRow1('var(--ink-3)', _T('籌碼', 'Supply'), fmt.n(ubk[1]) + _T(' 顆', ' BTC')) : ''));
    }
    hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move);
    hit.addEventListener('pointerleave', function () { xh.setAttribute('visibility', 'hidden'); hideTip(); });
  }

  /* ⑫ 選擇權買方權利金差：每天主動買進買權的權利金 − 主動買進賣權的權利金（Deribit 逐筆成交） */
  function prSay() {
    var x = D.deriv.prem, it = [];
    it.push([_T('7 日平均', '7-day average'), (x.a7 >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.a7), 1) + 'M',
      _T('最近一天買方花在買權 ' + oxUsd(x.call * 1e6) + '、賣權 ' + oxUsd(x.put * 1e6) + '；7 日平均' + (x.a7 >= 0 ? '偏向押上漲' : '偏向買下跌保護') + '，已連 ' + x.run + ' 天。',
        'On the latest day buyers spent ' + oxUsd(x.call * 1e6) + ' on calls and ' + oxUsd(x.put * 1e6) + ' on puts; the 7-day average leans ' + (x.a7 >= 0 ? 'toward upside bets' : 'toward downside protection') + ' for ' + x.run + ' days.'), x.a7 >= 0 ? 'neu' : 'warn']);
    it.push([_T('轉負之後', 'After turning negative'), x.r30.n ? x.r30.up + ' / ' + x.r30.n : '—',
      _T(ymdS(x.since) + ' 起，7 日平均轉負 ' + x.n_flips + ' 次（隔 30 天算新的一次），30 天後' + (x.r30.n ? ' ' + x.r30.up + '/' + x.r30.n + ' 次上漲、中位數 ' + fmt.pct(x.r30.med, 1) : '樣本不足') + '：' + (x.flips || []).map(function (f) { return fmt.md(f.date) + (f.r30 != null ? ' ' + fmt.pct(f.r30, 0) : ''); }).join('、') + '。資料只有一年，樣本很少；在熊牛過渡期，恐慌時買保護的人多，事後看常是相對低點，但不是規則。',
        'Since ' + ymdS(x.since) + ' the 7-day average turned negative ' + x.n_flips + ' times (30+ days apart); 30 days later ' + (x.r30.n ? x.r30.up + ' of ' + x.r30.n + ' rose, median ' + fmt.pct(x.r30.med, 1) : 'too few cases') + ': ' + (x.flips || []).map(function (f) { return fmt.md(f.date) + (f.r30 != null ? ' ' + fmt.pct(f.r30, 0) : ''); }).join(', ') + '. Only one year of data; in transitions, panic protection-buying often marked relative lows in hindsight, but it is not a rule.'), 'neu']);
    return it;
  }
  function prPanel() {
    var x = (D.deriv || {}).prem; if (!x || !x.rows) return '';
    return panel('span-12', _T('選擇權買方權利金差', 'Options buyer premium: calls − puts'), 'Deribit · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard(x.a7 >= 0 ? 'var(--up)' : 'var(--down)', _T('7 日平均', '7-day average'), (x.a7 >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.a7), 1) + 'M', _T('正＝錢押上漲、負＝買下跌保護', 'Positive = betting up, negative = buying protection')) + '</div>' +
      interpHtml(prSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('每日（買權多）', 'Daily (calls lead)'), 'var(--up)', 'box'], [_T('每日（賣權多）', 'Daily (puts lead)'), 'var(--down)', 'box'], [_T('7 日平均', '7-day average'), 'var(--s4)']]) +
      '<div class="chart cf-chart" id="c-prem"></div><p class="note">' + _T('每天（UTC）主動買進買權付出的權利金 − 主動買進賣權付出的權利金，Deribit 逐筆成交、換算美元。只算主動買進的一方（願意付錢的人），不含賣出。只作讀值。',
        'Each UTC day: premium paid by takers buying calls − premium paid by takers buying puts, from Deribit trades in USD. Only the aggressive buyer (who chose to pay) is counted; sales are excluded. Reading only.') + '</p>', '', 'prem');
  }
  function drawPr(el) {
    var x = (D.deriv || {}).prem; if (!x || !el) return;
    oxPane(el, { rows: x.rows.filter(function (r) { return r[1]; }), label: _T('買權 − 賣權權利金（百萬美元）', 'Calls − puts premium ($M)'), aria: _T('BTC 價格與選擇權買方權利金差', 'BTC price and options buyer premium'), zero: true,
      bars: { i: 2, pos: 'var(--up)', neg: 'var(--down)', op: 0.55, name: _T('每日', 'Daily'), tfmt: function (v) { return (v >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(v), 1) + 'M'; } },
      lines: [{ i: 3, col: 'var(--s4)', w: 2, name: _T('7 日平均', '7-day average'), tfmt: function (v) { return (v >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(v), 1) + 'M'; } }], fmt: function (t) { return (t < 0 ? '−' : '') + '$' + fmt.n(Math.abs(t), 0) + 'M'; },
      now: { i: 3, col: 'var(--s4)', lab: _T('現在 ', 'Now ') + (x.a7 >= 0 ? '+' : '−') + '$' + fmt.n(Math.abs(x.a7), 1) + 'M' } });
  }

  /* ⑬ OKX 現貨主動買賣差（SVD）：主動買進量 − 主動賣出量（BTC）。只有 OKX，不是全市場 */
  function svSay() {
    var x = D.deriv.svd, it = [];
    it.push([_T('最近一天', 'Latest day'), (x.delta >= 0 ? '+' : '') + fmt.n(x.delta, 0) + _T(' 顆', ' BTC'),
      _T(ymdS(x.date) + '（UTC+8）主動' + (x.delta >= 0 ? '買' : '賣') + '多 ' + fmt.n(Math.abs(x.delta), 0) + ' 顆；7 天合計 ' + (x.sum7 >= 0 ? '+' : '') + fmt.n(x.sum7, 0) + ' 顆，7 天裡 ' + x.neg7 + ' 天賣方主導' + (x.neg_run > 1 ? '，已連 ' + x.neg_run + ' 天' : '') + '。' + (x.h24 != null ? '近 24 小時 ' + (x.h24 >= 0 ? '+' : '') + fmt.n(x.h24, 0) + ' 顆。' : ''),
        ymdS(x.date) + ' (UTC+8): takers ' + (x.delta >= 0 ? 'bought' : 'sold') + ' ' + fmt.n(Math.abs(x.delta), 0) + ' BTC more; 7-day total ' + (x.sum7 >= 0 ? '+' : '') + fmt.n(x.sum7, 0) + ' BTC, sellers led on ' + x.neg7 + ' of 7 days' + (x.neg_run > 1 ? ', ' + x.neg_run + ' in a row' : '') + '. ' + (x.h24 != null ? 'Last 24 hours ' + (x.h24 >= 0 ? '+' : '') + fmt.n(x.h24, 0) + ' BTC.' : '')), x.sum7 < 0 ? 'warn' : 'neu']);
    it.push([_T('怎麼看', 'How to read'), '—', _T('下跌時主動賣出由深紅慢慢收斂、轉綠，代表殺跌的人變少、開始有人主動接；只在跌的時候放量賣、反彈時不放量買，代表買方多半是掛單被動承接。單一交易所、只作讀值。',
      'During a drop, taker selling that fades from deep red and turns green means fewer people are dumping and someone has started buying actively; heavy selling on drops with no buying on bounces means buyers are mostly passive bids. Single venue; reading only.'), 'neu']);
    return it;
  }
  function svPanel() {
    var x = (D.deriv || {}).svd; if (!x || !x.rows) return '';
    return panel('span-12', _T('現貨主動買賣差（OKX）', 'Spot taker buy − sell (OKX)'), 'OKX · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard(x.sum7 >= 0 ? 'var(--up)' : 'var(--down)', _T('7 天合計', '7-day total'), (x.sum7 >= 0 ? '+' : '') + fmt.n(x.sum7, 0), _T('顆 BTC；' + x.neg7 + ' / 7 天賣方主導', 'BTC; sellers led ' + x.neg7 + ' of 7 days')) + (x.h24 != null ? oxCard(x.h24 >= 0 ? 'var(--up)' : 'var(--down)', _T('近 24 小時', 'Last 24 hours'), (x.h24 >= 0 ? '+' : '') + fmt.n(x.h24, 0), _T('顆 BTC', 'BTC')) : '') + '</div>' +
      interpHtml(svSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('主動買多', 'Takers net buying'), 'var(--up)', 'box'], [_T('主動賣多', 'Takers net selling'), 'var(--down)', 'box']]) +
      '<div class="chart cf-chart" id="c-svd"></div><div class="chart cf-chart" id="c-svdh"></div><p class="note">' + _T('OKX 現貨 BTC 的主動買進量 − 主動賣出量（rubik 公開統計）。日線是 UTC+8 的日界，上方價格用 UTC 收盤；小時圖是近 7 天。這張只有 OKX 現貨（有逐小時），多家交易所的日線見下一張「現貨與永續的主動買賣」。只作讀值。',
        'OKX spot BTC taker buy volume − taker sell volume (rubik public stats). Daily bars use UTC+8 days while the price uses UTC closes; the hourly chart covers 7 days. This one is OKX spot only (it has hourly data); the multi-exchange daily view is the next chart, "Spot vs perpetual taker flow". Reading only.') + '</p>', '', 'svd');
  }
  function drawSv(el) {
    var x = (D.deriv || {}).svd; if (!x || !el) return;
    oxPane(el, { rows: x.rows.filter(function (r) { return r[1]; }), label: _T('每日主動買 − 主動賣（顆）', 'Daily taker buy − sell (BTC)'), aria: _T('BTC 價格與 OKX 現貨主動買賣差', 'BTC price and OKX spot taker delta'), zero: true,
      bars: { i: 2, pos: 'var(--up)', neg: 'var(--down)', op: 0.8, name: _T('主動買 − 賣', 'Taker buy − sell'), tfmt: function (v) { return (v >= 0 ? '+' : '') + fmt.n(v, 0) + _T(' 顆', ' BTC'); } }, fmt: function (t) { return fmt.n(t, 0); } });
  }
  function drawSvH(el) {
    var x = (D.deriv || {}).svd; if (!x || !el || !(x.hours || []).length) return;
    var R_ = x.hours.filter(function (h) { return h[2]; }).map(function (h) { return [h[0] / 24, h[2], h[1]]; });
    oxPane(el, { rows: R_, hp: [70, 90], hs: [100, 130], label: _T('近 7 天每小時（顆）', 'Hourly, last 7 days (BTC)'), aria: _T('OKX 每小時主動買賣差', 'OKX hourly taker delta'), zero: true,
      bars: { i: 2, pos: 'var(--up)', neg: 'var(--down)', op: 0.85, name: _T('主動買 − 賣', 'Taker buy − sell'), tfmt: function (v) { return (v >= 0 ? '+' : '') + fmt.n(v, 0) + _T(' 顆', ' BTC'); } }, fmt: function (t) { return fmt.n(t, 0); },
      tipExtra: function (p) { var t = new Date(p[0] * 864e5); return '<div class="r"><span>' + t.toISOString().slice(5, 13).replace('T', ' ') + ':00 UTC</span></div>'; } });
  }

  /* ===== 2026-11-06 使用者要求（「Bitview 還有什麼圖表可以搬過來的」→「推薦的都做」）：pipeline/bv_extra.py。
     鏈上版：賣方風險比、依持有時間的實現損益、Dormancy／Liveliness；週期版：長短期持有者 NUPL、AVIV、儲備風險。只作讀值 ===== */
  var LOG10 = function (v) { return Math.log10(Math.max(v, 1e-9)); };
  function cyList(L, dg, unit) { return (L || []).map(function (t) { return t.date.slice(0, 4) + ' ' + fmt.n(t.value, dg) + (unit || ''); }).join(_T('、', ', ')); }

  /* ① 賣方風險比 */
  function ssrSay() {
    var x = D.onchain.ssr, it = [], E = (x.eps || []).filter(function (e) { return e.r365 != null; }).slice(-5);
    it.push([_T('全網（7 天）', 'Network (7d)'), fmt.n(x.all * 100, 2) + '%',
      _T('7 天實現的獲利＋虧損是實現市值的 ' + fmt.n(x.all * 100, 2) + '%，在近 4 年的第 ' + fmt.n(x.pct4, 0) + ' 百分位（全部歷史第 ' + fmt.n(x.pct, 0) + '；30 天前 ' + fmt.n(x.all30 * 100, 2) + '%）。短期持有者 ' + fmt.n(x.sth * 100, 2) + '%（第 ' + fmt.n(x.pct_s, 0) + ' 百分位）、長期持有者 ' + fmt.n(x.lth * 100, 2) + '%（第 ' + fmt.n(x.pct_l, 0) + ' 百分位）。' + (x.run ? '已連 ' + x.run + ' 天在低檔區。' : '低檔區（近 4 年最低 10%）現在要到 ' + fmt.n(x.lo4 * 100, 2) + '% 以下。'),
        'Profit plus loss realized over 7 days equals ' + fmt.n(x.all * 100, 2) + '% of realized cap, the ' + fmt.n(x.pct4, 0) + 'th percentile of the last 4 years (' + fmt.n(x.pct, 0) + 'th of all history; ' + fmt.n(x.all30 * 100, 2) + '% 30 days ago). Short-term holders ' + fmt.n(x.sth * 100, 2) + '% (' + fmt.n(x.pct_s, 0) + 'th), long-term holders ' + fmt.n(x.lth * 100, 2) + '% (' + fmt.n(x.pct_l, 0) + 'th). ' + (x.run ? 'In the low zone for ' + x.run + ' days.' : 'The low zone (bottom 10% of 4 years) now starts below ' + fmt.n(x.lo4 * 100, 2) + '%.')), x.run ? 'pos' : 'neu']);
    it.push([_T('進入低檔區之後', 'After entering the low zone'), (x.r365 || {}).n ? x.r365.up + ' / ' + x.r365.n : '—',
      _T('近 4 年百分位 ≤ 10 的段落 ' + x.n_eps + ' 段（' + x.n_recent + ' 段在 2022 年之後），一年後 ' + oxStat(x.r365, x.base365) + '；90 天後 ' + oxStat(x.r90, x.base90) + '。最近幾段：' + E.map(function (e) { return ymdS(e.start) + '（' + e.days + ' 天，一年後 ' + oxP0(e.r365) + '）'; }).join('、') + '。低檔區代表賣的人少、賣價接近成本，常在盤整末端；不是精準買點。',
        'Stretches at or below the 10th percentile of 4 years: ' + x.n_eps + ' (' + x.n_recent + ' since 2022); a year later ' + oxStat(x.r365, x.base365) + '; 90 days later ' + oxStat(x.r90, x.base90) + '. Recent: ' + E.map(function (e) { return ymdS(e.start) + ' (' + e.days + ' days, 1y ' + oxP0(e.r365) + ')'; }).join(', ') + '. The low zone means few sellers selling near cost, often late in a consolidation; not a precise entry.'), 'neu']);
    it.push([_T('頂部的讀數', 'Readings at tops'), (x.tops || []).length + _T(' 輪', ' cycles'),
      _T('全網在週期頂部的最高值：' + (x.tops || []).map(function (t) { return t.date.slice(0, 4) + ' ' + fmt.n(t.value * 100, 1) + '%'; }).join('、') + '，一輪比一輪低，所以用近 4 年的滾動百分位，不用全部歷史、也不套固定門檻。', 'Network peaks at cycle tops: ' + (x.tops || []).map(function (t) { return t.date.slice(0, 4) + ' ' + fmt.n(t.value * 100, 1) + '%'; }).join(', ') + ' — lower each cycle, so read relative position, not a fixed line.'), 'neu']);
    return it;
  }
  function ssrPanel() {
    var x = (D.onchain || {}).ssr; if (!x || !x.rows) return '';
    return panel('span-12', _T('賣方風險比', 'Sell-side risk ratio'), 'Bitview · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard('var(--s4)', _T('全網（7 天）', 'Network (7d)'), fmt.n(x.all * 100, 2) + '%', _T('近 4 年第 ' + fmt.n(x.pct4, 0) + ' 百分位', fmt.n(x.pct4, 0) + 'th percentile of 4 years'), oxArrow(x.all * 100, x.all30 * 100, _T(' 個百分點 / 30 天', ' pts / 30d'), 2)) +
      oxCard('var(--s2)', 'STH', fmt.n(x.sth * 100, 2) + '%', _T('第 ' + fmt.n(x.pct_s, 0) + ' 百分位', fmt.n(x.pct_s, 0) + 'th percentile')) + oxCard('var(--s1)', 'LTH', fmt.n(x.lth * 100, 2) + '%', _T('第 ' + fmt.n(x.pct_l, 0) + ' 百分位', fmt.n(x.pct_l, 0) + 'th percentile')) + '</div>' +
      interpHtml(ssrSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('全網', 'Network'), 'var(--s4)'], ['STH', 'var(--s2)'], ['LTH', 'var(--s1)'], [_T('近 4 年最低 10% 線', '4-year bottom-10% line'), 'var(--s3)'], [_T('在低檔區的期間', 'Time in the low zone'), 'var(--s3)', 'box']]) +
      '<div class="chart cf-chart" id="c-ssr"></div><p class="note">' + _T('7 天實現的獲利＋虧損 ÷ 實現市值（Bitview，逐筆 UTXO）：賣出的人一共兌現了多少帳面損益。對數刻度。頂部一輪比一輪低，所以低檔區用全網近 4 年的滾動百分位（≤ 10）判定。只作讀值。', 'Profit plus loss realized over 7 days ÷ realized cap (Bitview, per UTXO): how much paper gain or loss sellers cashed in. Log scale. Tops fall each cycle, so the low zone uses the network value\'s rolling 4-year percentile (≤ 10). Reading only.') + '</p>', '', 'ssr');
  }
  function drawSsr(el) {
    var x = (D.onchain || {}).ssr; if (!x || !el) return;
    var pc = function (v) { return fmt.n(v * 100, v < 0.01 ? 2 : 1) + '%'; };
    oxPane(el, { rows: x.rows, label: _T('賣方風險比（對數刻度）', 'Sell-side risk ratio (log scale)'), aria: _T('BTC 價格與賣方風險比', 'BTC price and sell-side risk ratio'), tf: LOG10,
      ticks: [0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.3, 1], fmt: pc, y1: 1.4, y0: 0.0015,
      vbands: (x.eps || []).map(function (e) { return { x0: dnOf(e.start), x1: dnOf(e.end) + 3, col: 'var(--s3)', op: 0.18 }; }),
      lines: [{ i: 5, col: 'var(--s3)', w: 1, dash: '4 3', glow: false, name: _T('近 4 年最低 10%', '4y bottom 10%'), tfmt: pc }, { i: 4, col: 'var(--s1)', w: 1, op: 0.6, name: 'LTH', tfmt: pc }, { i: 3, col: 'var(--s2)', w: 1, op: 0.6, name: 'STH', tfmt: pc }, { i: 2, col: 'var(--s4)', w: 1.8, name: _T('全網', 'Network'), tfmt: pc }],
      now: { i: 2, col: 'var(--s4)', lab: _T('現在 ', 'Now ') + pc(x.all) } });
  }

  /* ② 依持有時間的實現獲利／虧損 */
  var AGE_COL = ['var(--stg4)', 'var(--stg3)', 'var(--stg2)', 'var(--s3)', 'var(--stg1)', 'var(--stg0)'], AGE_NM = [['1 個月內', '< 1 month'], ['1–6 個月', '1–6 months'], ['6–12 個月', '6–12 months'], ['1–2 年', '1–2 years'], ['2–5 年', '2–5 years'], ['5 年以上', '5+ years']];
  var agMode = 'p';
  function agSay() {
    var x = D.onchain.agepl, it = [], nm = function (i) { return _T(AGE_NM[i][0], AGE_NM[i][1]); };
    var top = function (a) { return a.map(function (v, i) { return [v, i]; }).sort(function (p, q) { return q[0] - p[0]; }).slice(0, 2); };
    var tp = top(x.prof), tl = top(x.loss);
    it.push([_T('誰在獲利了結', 'Who is taking profit'), nm(tp[0][1]) + ' ' + fmt.n(tp[0][0], 0) + '%',
      _T('30 天實現獲利 ' + oxUsd(x.prof_m * 1e6) + '，最多來自持有 ' + nm(tp[0][1]) + '（' + fmt.n(tp[0][0], 0) + '%）和 ' + nm(tp[1][1]) + '（' + fmt.n(tp[1][0], 0) + '%）。持有 6 個月以上的佔 ' + fmt.n(x.lth_prof, 0) + '%（30 天前 ' + fmt.n(x.lth_prof30, 0) + '%）。',
        'Profit realized over 30 days: ' + oxUsd(x.prof_m * 1e6) + ', mostly from coins held ' + nm(tp[0][1]) + ' (' + fmt.n(tp[0][0], 0) + '%) and ' + nm(tp[1][1]) + ' (' + fmt.n(tp[1][0], 0) + '%). Coins held 6+ months make up ' + fmt.n(x.lth_prof, 0) + '% (' + fmt.n(x.lth_prof30, 0) + '% 30 days ago).'), x.lth_prof >= 50 ? 'warn' : 'neu']);
    it.push([_T('誰在認賠', 'Who is selling at a loss'), nm(tl[0][1]) + ' ' + fmt.n(tl[0][0], 0) + '%',
      _T('30 天實現虧損 ' + oxUsd(x.loss_m * 1e6) + '，最多來自持有 ' + nm(tl[0][1]) + '（' + fmt.n(tl[0][0], 0) + '%）和 ' + nm(tl[1][1]) + '（' + fmt.n(tl[1][0], 0) + '%）。持有 6 個月以上的佔 ' + fmt.n(x.lth_loss, 0) + '%：' + (x.lth_loss >= 40 ? '去年高價買進、放了半年以上的人也開始認賠。' : '認賠主要還是近期進場的人。'),
        'Loss realized over 30 days: ' + oxUsd(x.loss_m * 1e6) + ', mostly from coins held ' + nm(tl[0][1]) + ' (' + fmt.n(tl[0][0], 0) + '%) and ' + nm(tl[1][1]) + ' (' + fmt.n(tl[1][0], 0) + '%). Coins held 6+ months make up ' + fmt.n(x.lth_loss, 0) + '%: ' + (x.lth_loss >= 40 ? 'holders who bought high last year and held over six months are now selling at a loss too.' : 'loss-selling still comes mainly from recent buyers.')), x.lth_loss >= 40 ? 'warn' : 'neu']);
    return it;
  }
  function agePanel() {
    var x = (D.onchain || {}).agepl; if (!x || !x.rows) return '';
    var segs = '<div class="seg" id="ag-seg"><button aria-pressed="' + (agMode === 'p') + '" data-m="p">' + _T('實現獲利', 'Realized profit') + '</button><button aria-pressed="' + (agMode === 'l') + '" data-m="l">' + _T('實現虧損', 'Realized loss') + '</button></div>';
    return panel('span-12', _T('依持有時間的實現獲利／虧損', 'Realized profit and loss by holding time'), 'Bitview · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard('var(--stg1)', _T('6 個月以上佔實現獲利', '6m+ share of profit'), fmt.n(x.lth_prof, 0) + '%', _T('30 天合計 ' + oxUsd(x.prof_m * 1e6), '30-day total ' + oxUsd(x.prof_m * 1e6)), oxArrow(x.lth_prof, x.lth_prof30, _T(' 個百分點 / 30 天', ' pts / 30d'), 0)) +
      oxCard('var(--stg3)', _T('6 個月以上佔實現虧損', '6m+ share of loss'), fmt.n(x.lth_loss, 0) + '%', _T('30 天合計 ' + oxUsd(x.loss_m * 1e6), '30-day total ' + oxUsd(x.loss_m * 1e6))) + '</div>' +
      interpHtml(agSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)']].concat(AGE_NM.map(function (n, i) { return [_T(n[0], n[1]), AGE_COL[i], 'box']; }))) +
      '<div class="chart cf-chart" id="c-agepl"></div><p class="note">' + _T('每天賣出的幣依「持有多久」分 6 組，下格是各組在 30 天合計裡的佔比（加起來 100%）；可切換看實現獲利或實現虧損。Bitview 逐筆 UTXO、不是實體調整：交易所內部搬幣會被算成一筆賣出。只作讀值。', 'Coins sold each day are grouped by how long they were held; the lower pane shows each group\'s share of the 30-day total (summing to 100%), for realized profit or realized loss. Bitview per UTXO, not entity-adjusted: an exchange moving coins internally counts as a sale. Reading only.') + '</p>', segs, 'agepl');
  }
  function drawAge(el) {
    var x = (D.onchain || {}).agepl; if (!x || !el) return;
    var k = agMode === 'p' ? 2 : 3, R_ = x.rows;
    twoPane(el, { rows: R_, pi: 1, hp: [90, 120], hs: [170, 220], label: _T(agMode === 'p' ? '30 天實現獲利的組成（%）' : '30 天實現虧損的組成（%）', agMode === 'p' ? '30-day realized profit by holding time (%)' : '30-day realized loss by holding time (%)'), aria: _T('依持有時間的實現損益', 'Realized P/L by holding time'),
      scale: function (C) { return function (v) { return C.ys0 + (1 - v / 100) * C.hs; }; },
      body: function (C) {
        var s = '', cum = R_.map(function () { return 0; });
        for (var g = 5; g >= 0; g--) {   // 由老到新往上疊：最老的在最下面
          var lo = cum.slice(), hi = R_.map(function (r, j) { return cum[j] + (r[k][g] || 0); });
          s += '<path d="M' + R_.map(function (r, j) { return C.X(r[0]).toFixed(1) + ',' + C.Ys(hi[j]).toFixed(1); }).join('L') + 'L' + R_.slice().reverse().map(function (r, jj) { var j = R_.length - 1 - jj; return C.X(r[0]).toFixed(1) + ',' + C.Ys(lo[j]).toFixed(1); }).join('L') + 'Z" fill="' + AGE_COL[g] + '" opacity=".78"/>';
          cum = hi;
        }
        [0, 50, 100].forEach(function (t) { s += C.gl(C.Ys(t), t + '%', t === 0 ? 'base' : 'gl'); });
        return s;
      },
      tip: function (p) { var rows = ''; for (var g = 0; g < 6; g++) rows += tipRow1(AGE_COL[g], _T(AGE_NM[g][0], AGE_NM[g][1]), fmt.n(p[k][g], 0) + '%'); return { rows: rows + tipRow1('var(--ink-3)', _T('30 天合計', '30-day total'), oxUsd((agMode === 'p' ? p[4] : p[5]) * 1e6)) }; } });
  }

  /* ③ Dormancy 與 Liveliness */
  function dmSay() {
    var x = D.onchain.dorm, it = [];
    it.push([_T('Dormancy（7 天）', 'Dormancy (7d)'), fmt.n(x.dorm, 1) + _T(' 天', ' days'),
      _T('最近 7 天賣出的幣平均放了 ' + fmt.n(x.dorm, 1) + ' 天，30 天平均 ' + fmt.n(x.dorm30, 1) + ' 天（近 4 年第 ' + fmt.n(x.a30_pct4, 0) + ' 百分位，全部歷史第 ' + fmt.n(x.a30_pct, 0) + '）：' + (x.a30_pct4 >= 80 ? '老幣動得比近幾年平常多，長期持有者在賣或搬幣。' : x.a30_pct4 <= 30 ? '賣出的多半是新幣，老幣很安靜。' : '老幣的動靜在近幾年的平常範圍。') + '週期頂部附近：' + cyList(x.tops, 1, _T(' 天', 'd')) + '；底部附近：' + cyList(x.bottoms, 1, _T(' 天', 'd')) + '。',
        'Coins spent over the last 7 days had been held ' + fmt.n(x.dorm, 1) + ' days on average; the 30-day average is ' + fmt.n(x.dorm30, 1) + ' days (' + fmt.n(x.a30_pct4, 0) + 'th percentile of 4 years, ' + fmt.n(x.a30_pct, 0) + 'th of all history): ' + (x.a30_pct4 >= 80 ? 'old coins are moving more than in recent years — long-term holders selling or moving coins.' : x.a30_pct4 <= 30 ? 'what sells is mostly young coins; old coins are quiet.' : 'old-coin activity is within its recent normal range.') + ' Near cycle tops: ' + cyList(x.tops, 1, 'd') + '; near bottoms: ' + cyList(x.bottoms, 1, 'd') + '.'), x.a30_pct4 >= 80 ? 'warn' : 'neu']);
    it.push([_T('Liveliness（90 天變化）', 'Liveliness (90-day change)'), (x.live90 >= 0 ? '+' : '') + fmt.n(x.live90, 2) + '‰',
      _T('Liveliness ' + fmt.n(x.live, 4) + '，90 天' + (x.live90 >= 0 ? '上升' : '下降') + ' ' + fmt.n(Math.abs(x.live90), 2) + ' 個千分點（' + ymdS(x.live_since) + ' 起同方向）：' + (x.live90 >= 0 ? '花掉的持有時間比新累積的多，長期持有者在花費。' : '新累積的持有時間比花掉的多，大家在囤。') + '它長期往上漂，看方向不看絕對值。',
        'Liveliness ' + fmt.n(x.live, 4) + ', ' + (x.live90 >= 0 ? 'up' : 'down') + ' ' + fmt.n(Math.abs(x.live90), 2) + ' per mille over 90 days (same direction since ' + ymdS(x.live_since) + '): ' + (x.live90 >= 0 ? 'more holding time is being spent than built up — long-term holders are spending.' : 'more holding time is building up than being spent — holders are hoarding.') + ' It drifts up over the years, so read the direction, not the level.'), 'neu']);
    return it;
  }
  function dmPanel() {
    var x = (D.onchain || {}).dorm; if (!x || !x.rows) return '';
    return panel('span-12', _T('Dormancy 與 Liveliness：老幣在不在動', 'Dormancy and liveliness: are old coins moving'), 'Bitview · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard('var(--s1)', _T('Dormancy（30 天平均）', 'Dormancy (30-day avg)'), fmt.n(x.dorm30, 1) + _T(' 天', ' d'), _T('近 4 年第 ' + fmt.n(x.a30_pct4, 0) + ' 百分位', fmt.n(x.a30_pct4, 0) + 'th percentile of 4 years')) +
      oxCard('var(--s3)', _T('Liveliness（90 天）', 'Liveliness (90d)'), (x.live90 >= 0 ? '+' : '') + fmt.n(x.live90, 2) + '‰', x.live90 >= 0 ? _T('上升：長期持有者在花費', 'Rising: long-term holders spending') : _T('下降：大家在囤', 'Falling: holders hoarding')) + '</div>' +
      interpHtml(dmSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('Dormancy（7 天）', 'Dormancy (7d)'), 'var(--s1)'], [_T('30 天平均', '30-day average'), 'var(--s2)']]) +
      '<div class="chart cf-chart" id="c-dorm"></div><p class="note">' + _T('Dormancy＝賣出的幣平均放了幾天（銷毀幣天數 ÷ 賣出量），對數刻度；Liveliness＝全部持有時間裡已經花掉的比例（Cointime）。資料 Bitview。只作讀值。', 'Dormancy = average days held of coins spent (coin days destroyed ÷ volume), log scale; liveliness = share of all holding time already spent (Cointime). Data: Bitview. Reading only.') + '</p>', '', 'dorm');
  }
  function drawDorm(el) {
    var x = (D.onchain || {}).dorm; if (!x || !el) return;
    oxPane(el, { rows: x.rows, label: _T('Dormancy（天，對數刻度）', 'Dormancy (days, log scale)'), aria: _T('BTC 價格與 Dormancy', 'BTC price and dormancy'), tf: LOG10, ticks: [2, 5, 10, 20, 50, 100], fmt: function (t) { return t + _T(' 天', 'd'); },
      lines: [{ i: 2, col: 'var(--s1)', w: 0.9, op: 0.5, name: _T('7 天', '7-day'), tfmt: function (v) { return fmt.n(v, 1) + _T(' 天', ' d'); } }, { i: 3, col: 'var(--s2)', w: 1.8, name: _T('30 天平均', '30-day average'), tfmt: function (v) { return fmt.n(v, 1) + _T(' 天', ' d'); } }],
      marks: (x.tops || []).map(function (t) { return { x: dnOf(t.date), y: t.value, col: 'var(--warn)', t: _T('頂 ', 'Top ') + t.date.slice(0, 4) + ' ' + fmt.n(t.value, 0) + _T(' 天', 'd') }; }),
      now: { i: 3, col: 'var(--s2)', lab: _T('現在 ', 'Now ') + fmt.n(x.dorm30, 1) + _T(' 天', ' d') } });
  }

  /* ④ 長短期持有者 NUPL（週期版） */
  var LN_NM = { cap: ['投降', 'Capitulation', 'var(--stg0)'], hope: ['希望／恐懼', 'Hope / fear', 'var(--stg1)'], opt: ['樂觀／焦慮', 'Optimism / anxiety', 'var(--stg2)'], belief: ['信念／否認', 'Belief / denial', 'var(--stg3)'], euph: ['狂熱／貪婪', 'Euphoria / greed', 'var(--stg4)'] };
  function lnSay() {
    var x = D.onchain.hnupl, it = [], st = LN_NM[x.stage];
    it.push([_T('LTH 階段', 'LTH stage'), _T(st[0], st[1]),
      _T('長期持有者 NUPL ' + fmt.n(x.lth, 3) + '（30 天前 ' + fmt.n(x.lth30, 3) + '），' + ymdS(x.since) + ' 起在「' + st[0] + '」（0.25–0.5）。頂部：' + cyList(x.tops, 2) + '，一輪比一輪低；底部：' + cyList(x.bottoms, 2) + '，這一輪長期持有者整體一直沒有跌到虧損（前三輪都到 −0.3 以下）。',
        'Long-term holder NUPL ' + fmt.n(x.lth, 3) + ' (' + fmt.n(x.lth30, 3) + ' 30 days ago), in "' + st[1] + '" since ' + ymdS(x.since) + '. Tops: ' + cyList(x.tops, 2) + ', lower each cycle; bottoms: ' + cyList(x.bottoms, 2) + ' — this cycle long-term holders never went underwater as a group (the last three reached −0.3 or lower).'), 'neu']);
    var c = x.cross || {};
    it.push([_T('STH-NUPL', 'STH-NUPL'), fmt.n(x.sth, 3),
      _T('短期持有者 NUPL ' + fmt.n(x.sth, 3) + '：' + (x.sth >= 0 ? '新進場的人整體還在獲利' : '新進場的人整體轉為虧損') + (c.date ? '（' + ymdS(c.date) + (c.up ? ' 回到 0 以上' : ' 跌破 0') + '）' : '') + '。2012 年起由負轉正 ' + x.n_ups + ' 次（隔 60 天以上算新的一次），30 天後 ' + oxStat(x.r30, x.base30) + '；90 天後 ' + oxStat(x.r90, x.base90) + '。',
        'Short-term holder NUPL ' + fmt.n(x.sth, 3) + ': ' + (x.sth >= 0 ? 'recent buyers are still in profit as a group' : 'recent buyers have turned to a loss as a group') + (c.date ? ' (' + (c.up ? 'back above 0' : 'below 0') + ' on ' + ymdS(c.date) + ')' : '') + '. Since 2012 it turned from negative to positive ' + x.n_ups + ' times (60+ days apart): 30 days later ' + oxStat(x.r30, x.base30) + '; 90 days later ' + oxStat(x.r90, x.base90) + '.'), x.sth >= 0 ? 'neu' : 'warn']);
    return it;
  }
  function lnPanel() {
    var x = (D.onchain || {}).hnupl; if (!x || !x.rows) return '';
    var st = LN_NM[x.stage];
    return panel('span-12', _T('長短期持有者 NUPL', 'Long- and short-term holder NUPL'), 'Bitview · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard(st[2], _T('LTH-NUPL', 'LTH-NUPL'), fmt.n(x.lth, 3), _T('階段：' + st[0], 'Stage: ' + st[1]), oxArrow(x.lth, x.lth30, _T(' / 30 天', ' / 30d'), 3)) + oxCard('var(--s2)', 'STH-NUPL', fmt.n(x.sth, 3), x.sth >= 0 ? _T('短期持有者整體獲利', 'STH in profit as a group') : _T('短期持有者整體虧損', 'STH at a loss as a group'), oxArrow(x.sth, x.sth30, _T(' / 30 天', ' / 30d'), 3)) + '</div>' +
      interpHtml(lnSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], ['LTH-NUPL', 'var(--s1)'], ['STH-NUPL', 'var(--s2)']].concat(['cap', 'hope', 'opt', 'belief', 'euph'].map(function (k) { return [_T(LN_NM[k][0], LN_NM[k][1]), LN_NM[k][2], 'box']; }))) +
      '<div class="chart cf-chart" id="c-hnupl"></div><p class="note">' + _T('NUPL＝（帳面獲利 − 帳面虧損）÷ 市值。底色是長期持有者的五個階段（常見的分法）：0 以下投降、0–0.25 希望／恐懼、0.25–0.5 樂觀／焦慮、0.5–0.75 信念／否認、0.75 以上狂熱／貪婪。短期持有者看 0 上下。資料 Bitview。只作讀值。', 'NUPL = (paper gains − paper losses) ÷ market cap. The shading marks the five long-term holder stages in common use: below 0 capitulation, 0–0.25 hope/fear, 0.25–0.5 optimism/anxiety, 0.5–0.75 belief/denial, above 0.75 euphoria/greed. For short-term holders, read above or below 0. Data: Bitview. Reading only.') + '</p>', '', 'hnupl');
  }
  function drawLn(el) {
    var x = (D.onchain || {}).hnupl; if (!x || !el) return;
    oxPane(el, { rows: x.rows, label: 'NUPL', aria: _T('BTC 價格與長短期持有者 NUPL', 'BTC price and holder NUPL'), y0: -1, y1: 1, ticks: [-0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75], fmt: function (t) { return fmt.n(t, 2); },
      zones: [{ y0: -1, y1: 0, col: 'var(--stg0)', op: 0.10 }, { y0: 0, y1: 0.25, col: 'var(--stg1)', op: 0.10 }, { y0: 0.25, y1: 0.5, col: 'var(--stg2)', op: 0.10 }, { y0: 0.5, y1: 0.75, col: 'var(--stg3)', op: 0.10 }, { y0: 0.75, y1: 1, col: 'var(--stg4)', op: 0.10 }],
      lines: [{ i: 3, col: 'var(--s2)', w: 1, op: 0.7, name: 'STH-NUPL', tfmt: function (v) { return fmt.n(v, 3); } }, { i: 2, col: 'var(--s1)', w: 1.9, name: 'LTH-NUPL', tfmt: function (v) { return fmt.n(v, 3); } }],
      marks: (x.tops || []).map(function (t) { return { x: dnOf(t.date), y: t.value, col: 'var(--stg4)', t: t.date.slice(0, 4) + ' ' + fmt.n(t.value, 2) }; }).concat((x.bottoms || []).map(function (t) { return { x: dnOf(t.date), y: t.value, col: 'var(--stg0)', t: t.date.slice(0, 4) + ' ' + fmt.n(t.value, 2), up: false }; })),
      now: { i: 2, col: 'var(--s1)', lab: _T('現在 ', 'Now ') + fmt.n(x.lth, 2) } });
  }

  /* ⑤ AVIV（週期版） */
  function avSay() {
    var x = D.onchain.aviv, it = [], E = (x.eps || []).filter(function (e) { return e.r365 != null; }).slice(-5);
    it.push([_T('現在', 'Now'), fmt.n(x.value, 3),
      _T('價格是真實市場均價（' + fmt.usd(x.tmm) + '）的 ' + fmt.n(x.value, 3) + ' 倍：' + (x.below ? '活躍投資人整體在虧損，已連 ' + x.run + ' 天低於 1。' : '活躍投資人整體在獲利，已連 ' + x.run + ' 天高於 1。') + '近 4 年第 ' + fmt.n(x.pct4, 0) + ' 百分位（全部歷史第 ' + fmt.n(x.pct, 0) + '；頂部一輪比一輪低，全部歷史的百分位會偏向近年）。頂部：' + cyList(x.tops, 2) + '，一輪比一輪低；底部：' + cyList(x.bottoms, 2) + '，一輪比一輪高。',
        'Price is ' + fmt.n(x.value, 3) + '× the true market mean (' + fmt.usd(x.tmm) + '): ' + (x.below ? 'active investors are at a loss as a group, below 1 for ' + x.run + ' days.' : 'active investors are in profit as a group, above 1 for ' + x.run + ' days.') + ' ' + fmt.n(x.pct4, 0) + 'th percentile of 4 years (' + fmt.n(x.pct, 0) + 'th of all history; tops fall each cycle, so all-history percentiles lean recent). Tops: ' + cyList(x.tops, 2) + ', lower each cycle; bottoms: ' + cyList(x.bottoms, 2) + ', higher each cycle.'), x.below ? 'warn' : 'neu']);
    it.push([_T('跌破 1 之後', 'After dropping below 1'), (x.r365 || {}).n ? x.r365.up + ' / ' + x.r365.n : '—',
      _T('2012 年起低於 1 達 10 天以上的段落，一年後 ' + oxStat(x.r365, x.base365) + '。最近幾段：' + E.map(function (e) { return ymdS(e.start) + '–' + ymdS(e.end) + '（' + e.days + ' 天，一年後 ' + oxP0(e.r365) + '）'; }).join('、') + '。在熊市裡會長時間待在 1 以下（2014–16、2018–19、2022–23），所以低於 1 本身不是買點。',
        'Since 2012, stretches below 1 lasting 10+ days: a year later ' + oxStat(x.r365, x.base365) + '. Recent: ' + E.map(function (e) { return ymdS(e.start) + '–' + ymdS(e.end) + ' (' + e.days + ' days, 1y ' + oxP0(e.r365) + ')'; }).join(', ') + '. In bear markets it stays below 1 for long stretches (2014–16, 2018–19, 2022–23), so being below 1 is not a buy signal by itself.'), 'neu']);
    return it;
  }
  function avPanel() {
    var x = (D.onchain || {}).aviv; if (!x || !x.rows) return '';
    return panel('span-12', _T('AVIV：價格 ÷ 真實市場均價', 'AVIV: price ÷ true market mean'), 'Bitview · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard(x.below ? 'var(--warn)' : 'var(--s2)', 'AVIV', fmt.n(x.value, 3), x.below ? _T('低於 1：活躍投資人整體虧損', 'Below 1: active investors at a loss') : _T('高於 1：活躍投資人整體獲利', 'Above 1: active investors in profit')) + '</div>' +
      interpHtml(avSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], ['AVIV', 'var(--s2)'], [_T('1 以下', 'Below 1'), 'var(--s3)', 'box']]) +
      '<div class="chart cf-chart" id="c-aviv"></div><p class="note">' + _T('AVIV＝價格 ÷ 真實市場均價（只算還在交易的活躍資本的平均成本，排除長期不動、遺失的幣；Cointime，Bitview）。等於 1＝價格剛好在活躍投資人的平均成本。對數刻度。只作讀值。', 'AVIV = price ÷ the true market mean (the average cost of active capital only, excluding long-dormant and lost coins; Cointime, via Bitview). At 1, price sits exactly at active investors\' average cost. Log scale. Reading only.') + '</p>', '', 'aviv');
  }
  function drawAv(el) {
    var x = (D.onchain || {}).aviv; if (!x || !el) return;
    oxPane(el, { rows: x.rows, label: _T('AVIV（對數刻度）', 'AVIV (log scale)'), aria: _T('BTC 價格與 AVIV', 'BTC price and AVIV'), tf: LOG10, ticks: [0.5, 0.75, 1, 1.5, 2, 3], fmt: function (t) { return fmt.n(t, 2); },
      zones: [{ y0: 0.3, y1: 1, col: 'var(--s3)', op: 0.12 }], refs: [{ y: 1, col: 'var(--s3)', lab: '1.0' }],
      lines: [{ i: 2, col: 'var(--s2)', w: 1.8, name: 'AVIV', tfmt: function (v) { return fmt.n(v, 3); } }],
      marks: (x.tops || []).map(function (t) { return { x: dnOf(t.date), y: t.value, col: 'var(--warn)', t: t.date.slice(0, 4) + ' ' + fmt.n(t.value, 2) }; }).concat((x.bottoms || []).map(function (t) { return { x: dnOf(t.date), y: t.value, col: 'var(--s3)', t: t.date.slice(0, 4) + ' ' + fmt.n(t.value, 2), up: false }; })),
      now: { i: 2, col: 'var(--s2)', lab: _T('現在 ', 'Now ') + fmt.n(x.value, 2) } });
  }

  /* ⑥ 儲備風險（週期版） */
  function rrSay() {   /* 2026-11-06 使用者（經長文 session）：「看起來儲備風險的峰值在逐漸降低中」→ 低檔區改用近 4 年滾動百分位 */
    var x = D.onchain.rrisk, it = [], E = (x.eps || []).filter(function (e) { return e.r365 != null; }), f = function (v) { return fmt.n(v * 1000, 2) + '‰'; };
    it.push([_T('現在', 'Now'), _T('近 4 年第 ' + fmt.n(x.pct4, 0), fmt.n(x.pct4, 0) + 'th (4y)'),
      _T('儲備風險 ' + f(x.value) + '，在近 4 年的第 ' + fmt.n(x.pct4, 0) + ' 百分位（全部歷史第 ' + fmt.n(x.pct, 0) + '）' + (x.run ? '，已連 ' + x.run + ' 天在低檔區' : '；低檔區（近 4 年最低 10%）現在要到 ' + f(x.lo4) + ' 以下') + '。頂部一輪比一輪低：' + (x.tops || []).map(function (t) { return t.date.slice(0, 4) + ' ' + f(t.value); }).join('、') + '，底部一直在 0.8–1.6‰，整條線被壓扁了，所以全部歷史的百分位會偏向近年，這裡用近 4 年比。',
        'Reserve risk ' + f(x.value) + ', the ' + fmt.n(x.pct4, 0) + 'th percentile of the last 4 years (' + fmt.n(x.pct, 0) + 'th of all history)' + (x.run ? '; in the low zone for ' + x.run + ' days' : '; the low zone (bottom 10% of 4 years) now starts below ' + f(x.lo4)) + '. Tops fall each cycle — ' + (x.tops || []).map(function (t) { return t.date.slice(0, 4) + ' ' + f(t.value); }).join(', ') + ' — while bottoms stay around 0.8–1.6‰, flattening the series, so an all-history percentile leans toward recent years; this uses the last 4 years.'), x.run ? 'pos' : 'neu']);
    it.push([_T('歷次底部的位置', 'Past bottoms'), (x.bp4 || []).map(function (b) { return fmt.n(b.pct4, 0); }).join(' / '),
      _T('各輪熊市底部在當時近 4 年的百分位：' + (x.bp4 || []).map(function (b) { return b.date.slice(0, 7).replace('-', '/') + ' 第 ' + fmt.n(b.pct4, 0); }).join('、') + '。2018 年底的底部只到第 26，所以單看這一項會漏掉底部。',
        'Each bear-market bottom against its own previous 4 years: ' + (x.bp4 || []).map(function (b) { return b.date.slice(0, 7).replace('-', '/') + ' ' + fmt.n(b.pct4, 0) + 'th'; }).join(', ') + '. The late-2018 bottom only reached the 26th, so this gauge alone can miss a bottom.'), 'neu']);
    it.push([_T('進入低檔區之後', 'After entering the low zone'), (x.r365 || {}).n ? x.r365.up + ' / ' + x.r365.n : '—',
      _T('近 4 年百分位 ≤ 10 的段落共 ' + x.n_eps + ' 段（' + x.n_recent + ' 段在 2022 年之後），走完一年的 ' + x.r365.n + ' 段中 ' + x.r365.up + ' 段一年後上漲：' + E.map(function (e) { return ymdS(e.start) + '（' + e.days + ' 天，一年後 ' + oxP0(e.r365) + '）'; }).join('、') + '。樣本少、結果不一致，只作讀值。',
        'Stretches at or below the 10th percentile of 4 years: ' + x.n_eps + ' (' + x.n_recent + ' since 2022); of the ' + x.r365.n + ' with a full year since, ' + x.r365.up + ' were higher a year later: ' + E.map(function (e) { return ymdS(e.start) + ' (' + e.days + ' days, 1y ' + oxP0(e.r365) + ')'; }).join(', ') + '. Few cases with mixed results; reading only.'), 'neu']);
    return it;
  }
  function rrPanel() {
    var x = (D.onchain || {}).rrisk; if (!x || !x.rows) return '';
    return panel('span-12', _T('儲備風險', 'Reserve risk'), 'Bitview · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard(x.run ? 'var(--s3)' : 'var(--s1)', _T('儲備風險', 'Reserve risk'), fmt.n(x.value * 1000, 2) + '‰', _T('近 4 年第 ' + fmt.n(x.pct4, 0) + ' 百分位', fmt.n(x.pct4, 0) + 'th percentile of 4 years') + (x.run ? _T('・在低檔區', ' · low zone') : '')) + '</div>' +
      interpHtml(rrSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('儲備風險', 'Reserve risk'), 'var(--s1)'], [_T('近 4 年最低 10% 線', '4-year bottom-10% line'), 'var(--s3)'], [_T('近 4 年最高 10% 線', '4-year top-10% line'), 'var(--warn)'], [_T('在低檔區的期間', 'Time in the low zone'), 'var(--s3)', 'box']]) +
      '<div class="chart cf-chart" id="c-rrisk"></div><p class="note">' + _T('儲備風險＝價格 ÷ 長期持有者的信心（他們放著不賣所累積的持有時間）。低＝價格相對長期持有者的信心便宜、風險報酬好；高＝頂部區。對數刻度，單位千分之。資料 Bitview。只作讀值。', 'Reserve risk = price ÷ long-term holder conviction (the holding time they built up by not selling). Low = price is cheap relative to that conviction, good risk/reward; high = top zone. Log scale, in per mille. Data: Bitview. Reading only.') + '</p>', '', 'rrisk');
  }
  function drawRr(el) {
    var x = (D.onchain || {}).rrisk; if (!x || !el) return;
    var f = function (v) { return fmt.n(v * 1000, v < 0.01 ? 2 : 1) + '‰'; };
    oxPane(el, { rows: x.rows, label: _T('儲備風險（對數刻度）', 'Reserve risk (log scale)'), aria: _T('BTC 價格與儲備風險', 'BTC price and reserve risk'), tf: LOG10, ticks: [0.001, 0.002, 0.005, 0.01, 0.02, 0.05], fmt: f, y0: 0.0006, y1: 0.06,
      vbands: (x.eps || []).map(function (e) { return { x0: dnOf(e.start), x1: dnOf(e.end) + 3, col: 'var(--s3)', op: 0.18 }; }),
      lines: [{ i: 3, col: 'var(--s3)', w: 1, dash: '4 3', glow: false, name: _T('近 4 年最低 10%', '4y bottom 10%'), tfmt: f }, { i: 4, col: 'var(--warn)', w: 1, dash: '4 3', glow: false, name: _T('近 4 年最高 10%', '4y top 10%'), tfmt: f }, { i: 2, col: 'var(--s1)', w: 1.8, name: _T('儲備風險', 'Reserve risk'), tfmt: f }],
      now: { i: 2, col: 'var(--s1)', lab: _T('現在 ', 'Now ') + f(x.value) } });
  }

  (function () {   /* 新圖的「怎麼讀這張圖」 */
    var hh = function (a, b, cz, ce, dz, de) { return [[a, b], [cz, ce], [dz, de]]; }, o = function (k) { return (D.onchain || {})[k] || {}; };
    Object.assign(RD, {
      'ssr': { h: hh('金線是全網賣方風險比，橘是短期持有者、紫是長期持有者（對數刻度）。青綠虛線是全網近 4 年最低 10% 的門檻（逐日變動），青綠底是落在低檔區的期間。', 'Gold is the network sell-side risk ratio, orange short-term holders, purple long-term holders (log scale). The teal dashed line is the rolling 4-year bottom-10% threshold; teal shading marks time in the low zone.',
          '很低＝賣的人少、賣價接近成本，市場在找新的平衡，常在盤整末端與底部區；很高＝大量獲利了結或恐慌認賠。長期持有者那條衝高，多半是老手在頂部出貨。', 'Very low = few sellers selling near cost, the market looking for a new balance, often late in consolidations and near bottoms; very high = heavy profit-taking or panic selling. A spike in the long-term holder line usually means seasoned holders distributing near a top.',
          '頂部的高點一輪比一輪低，固定門檻會失準，看的是在自己歷史裡的相對位置；逐筆 UTXO、不是實體調整。', 'Top readings fall each cycle, so fixed lines go stale — read the position against its own history; per UTXO, not entity-adjusted.'),
        now: function () { var x = o('ssr'); return x.all == null ? '' : _T('全網 ' + fmt.n(x.all * 100, 2) + '%（近 4 年第 ' + fmt.n(x.pct4, 0) + ' 百分位）。', 'Network ' + fmt.n(x.all * 100, 2) + '% (' + fmt.n(x.pct4, 0) + 'th percentile of 4 years).'); } },
      'agepl': { h: hh('上格價格；下格是 30 天實現獲利（或虧損）裡，各持有時間組佔多少（加起來 100%）：越上面越新的幣（紅、琥珀），越下面越老的幣（藍）。', 'Top: price. Bottom: each holding-time group\'s share of 30-day realized profit (or loss), summing to 100% — younger coins on top (red, amber), older below (blue).',
          '獲利了結裡老幣（藍）變多＝長期持有者在賣，常在高點；認賠裡 6 個月以上的變多＝去年高價買進的人也撐不住了。', 'More old coins (blue) in profit-taking = long-term holders selling, typical near highs; more 6m+ coins in loss-taking = last year\'s high-price buyers giving up.',
          '交易所內部搬幣會被算成賣出，單日的大搬家會讓某一組突然變大。', 'Internal exchange moves count as sales, so one big transfer can make a group jump.'),
        now: function () { var x = o('agepl'); return x.lth_prof == null ? '' : _T('6 個月以上：佔實現獲利 ' + fmt.n(x.lth_prof, 0) + '%、實現虧損 ' + fmt.n(x.lth_loss, 0) + '%。', '6m+: ' + fmt.n(x.lth_prof, 0) + '% of realized profit, ' + fmt.n(x.lth_loss, 0) + '% of realized loss.'); } },
      'dorm': { h: hh('紫是 7 天 Dormancy、橘是 30 天平均（對數刻度），膠囊是週期頂部附近的最高值。', 'Purple is 7-day dormancy, orange the 30-day average (log scale); capsules mark the highs near cycle tops.',
          '數字高＝賣出的幣放得很久，老幣在動；長時間偏低＝賣的都是新幣、老幣很安靜，常在底部區。', 'High = coins spent had been held a long time, old coins moving; low for a long stretch = only young coins selling, old coins quiet, often near bottoms.',
          '交易所或託管機構整理老錢包時會一次搬很多老幣，造成單週尖峰；看 30 天平均比較穩。', 'When exchanges or custodians reorganize old wallets, many old coins move at once and spike a week; the 30-day average is steadier.'),
        now: function () { var x = o('dorm'); return x.dorm30 == null ? '' : _T('30 天平均 ' + fmt.n(x.dorm30, 1) + ' 天（近 4 年第 ' + fmt.n(x.a30_pct4, 0) + ' 百分位）；Liveliness 90 天 ' + (x.live90 >= 0 ? '+' : '') + fmt.n(x.live90, 2) + '‰。', '30-day average ' + fmt.n(x.dorm30, 1) + ' days (' + fmt.n(x.a30_pct4, 0) + 'th percentile of 4 years); liveliness 90d ' + (x.live90 >= 0 ? '+' : '') + fmt.n(x.live90, 2) + '‰.'); } },
      'hnupl': { h: hh('紫是長期持有者 NUPL、橘是短期持有者 NUPL；底色是長期持有者的五個階段（藍＝投降，往上依序到紅＝狂熱）。膠囊是歷次頂部、底部的讀數。', 'Purple is long-term holder NUPL, orange short-term holder NUPL; the shading marks the five long-term holder stages (blue = capitulation up to red = euphoria). Capsules show readings at past tops and bottoms.',
          '長期持有者進到信念、狂熱（0.5 以上）是週期後段；跌回希望或投降是熊市。短期持有者在 0 附近上下，代表新進場的人在成本附近拉鋸。', 'Long-term holders in belief or euphoria (above 0.5) is late cycle; falling back to hope or capitulation is a bear market. Short-term holders hovering around 0 means recent buyers are fighting at cost.',
          '頂部讀數一輪比一輪低、這一輪底部長期持有者沒有跌到虧損，階段門檻是常見分法、不是這一輪的定律。', 'Top readings fall each cycle and this cycle\'s long-term holders never went underwater at the bottom; the stage lines are a convention, not a law for this cycle.'),
        now: function () { var x = o('hnupl'); return x.lth == null ? '' : _T('LTH ' + fmt.n(x.lth, 3) + '（' + LN_NM[x.stage][0] + '）、STH ' + fmt.n(x.sth, 3) + '。', 'LTH ' + fmt.n(x.lth, 3) + ' (' + LN_NM[x.stage][1] + '), STH ' + fmt.n(x.sth, 3) + '.'); } },
      'aviv': { h: hh('AVIV＝價格 ÷ 真實市場均價（對數刻度）；青綠底是 1 以下，膠囊是歷次頂部與底部。', 'AVIV = price ÷ the true market mean (log scale); teal shading is below 1, capsules the past tops and bottoms.',
          '高於 1＝活躍投資人整體獲利，越高越接近過熱；低於 1＝活躍投資人整體虧損，熊市大多待在這裡。頂部一輪比一輪低、底部一輪比一輪高。', 'Above 1 = active investors in profit, higher means closer to overheating; below 1 = active investors at a loss, where bear markets mostly sit. Tops fall and bottoms rise each cycle.',
          '真實市場均價是推算的活躍資本成本（Cointime 模型），和一般的實現價格不同。', 'The true market mean is a modelled cost of active capital (Cointime), different from the ordinary realized price.'),
        now: function () { var x = o('aviv'); return x.value == null ? '' : _T('AVIV ' + fmt.n(x.value, 3) + '（' + (x.below ? '低於 1，連 ' : '高於 1，連 ') + x.run + ' 天）。', 'AVIV ' + fmt.n(x.value, 3) + ' (' + (x.below ? 'below' : 'above') + ' 1 for ' + x.run + ' days).'); } },
      'rrisk': { h: hh('儲備風險（對數刻度，千分之）；青綠虛線是近 4 年最低 10% 的門檻（逐日變動）、琥珀色虛線是最高 10%，青綠底是落在低檔區的期間。', 'Reserve risk (log scale, per mille); the teal dashed line is the rolling 4-year bottom-10% threshold, the amber one the top 10%; teal shading marks time in the low zone.',
          '低＝價格相對長期持有者的信心便宜，過去都在熊市底部附近；高＝價格跑在信心前面，頂部區。', 'Low = price is cheap relative to long-term holder conviction, historically near bear-market bottoms; high = price running ahead of conviction, the top zone.',
          '頂部一輪比一輪低、整條線被壓扁，所以用近 4 年比，不用全部歷史；2018 年底的熊市底部也只到近 4 年第 26 百分位，單看這一項會漏掉底部。', 'Tops fall each cycle and flatten the series, so it is compared with the last 4 years, not all history; the late-2018 bottom only reached the 26th percentile, so this gauge alone can miss a bottom.'),
        now: function () { var x = o('rrisk'); return x.value == null ? '' : _T(fmt.n(x.value * 1000, 2) + '‰（近 4 年第 ' + fmt.n(x.pct4, 0) + ' 百分位）' + (x.run ? '，在低檔區。' : '。'), fmt.n(x.value * 1000, 2) + '‰ (' + fmt.n(x.pct4, 0) + 'th percentile of 4 years)' + (x.run ? ', in the low zone.' : '.')); } }
    });
  })();

  /* 2026-11-06 指標擴充（六項，資料見 pipeline/cq_extra.py）：交易所淨流量、現貨 vs 永續需求、ETF 持有者成本、一年累計淨實現損益（顆）、韓國溢價、每輪資金效率。
     都附歷史對照或回測，只作讀值、不是買賣訊號 */
  function cqBtc(v) { return v == null ? '—' : (v > 0 ? '+' : '') + fmt.n(v, 0); }
  function cqKb(v) {   // 千顆 → 中文「萬」、英文 K／M
    if (v == null) return '—'; var g = v > 0 ? '+' : v < 0 ? '-' : '', a = Math.abs(v);
    return g + _T(fmt.n(a / 10, a >= 1000 ? 0 : 1) + ' 萬', a >= 1000 ? fmt.n(a / 1000, 2) + 'M' : fmt.n(a, 0) + 'K');
  }
  function cqKt(v) { if (!v) return '0'; return _T(fmt.n(v / 10, 0) + '萬', Math.abs(v) >= 1000 ? fmt.n(v / 1000, v % 1000 ? 1 : 0) + 'M' : fmt.n(v, 0) + 'K'); }   // 刻度用（千顆）
  function cqB(v) {   // 十億美元
    if (v == null) return '—'; var g = v > 0 ? '+' : v < 0 ? '-' : '', a = Math.abs(v);
    return g + (a >= 1000 ? '$' + fmt.n(a / 1000, 2) + 'T' : a >= 1 ? '$' + fmt.n(a, a >= 100 ? 0 : a >= 10 ? 1 : 2) + 'B' : '$' + fmt.n(a * 1000, 0) + 'M');
  }
  function cqCmp(s, b) { if (!s || !s.n || !b || s.med == null) return ''; var d = s.med - b.med; return d > 3 ? _T('比同期任一天好', 'better than an average day') : d < -3 ? _T('比同期任一天差', 'worse than an average day') : _T('和同期任一天差不多', 'about the same as an average day'); }

  /* ① 交易所淨流量 */
  function exfSay() {
    var x = (D.flows || {}).exflow; if (!x) return [];
    var it = [], lo = (x.out_last || [])[(x.out_last || []).length - 1];
    it.push([_T('30 天淨流量', '30-day netflow'), cqBtc(x.s30) + _T(' 顆', ' BTC'),
      _T((x.out ? '幣在離開交易所' : '幣在流向交易所') + '：30 天合計 ' + cqBtc(x.s30) + ' 顆，已連續 ' + x.run + ' 天' + (x.out ? '淨流出' : '淨流入') + '，近 4 年第 ' + fmt.n(x.pct4, 0) + ' 百分位' + (x.s30_30 != null ? '（30 天前 ' + cqBtc(x.s30_30) + ' 顆）' : '') + '。',
        (x.out ? 'Coins are leaving exchanges' : 'Coins are flowing to exchanges') + ': ' + cqBtc(x.s30) + ' BTC over 30 days, net ' + (x.out ? 'outflow' : 'inflow') + ' for ' + x.run + ' days running, ' + fmt.n(x.pct4, 0) + 'th percentile of 4 years' + (x.s30_30 != null ? ' (' + cqBtc(x.s30_30) + ' BTC 30 days ago)' : '') + '.'), 'neu']);
    it.push([_T('強流出之後', 'After strong outflows'), x.n_out + _T(' 段', ' stretches'),
      _T('30 天合計落到近 4 年最低 10%（強流出）共 ' + x.n_out + ' 段，進入後 90 天：', 'The 30-day sum fell into the 4-year bottom 10% (strong outflow) ' + x.n_out + ' times; 90 days later: ') + oxStat(x.out_r90, x.base90) + _T('，' + cqCmp(x.out_r90, x.base90) + '。', ', ' + cqCmp(x.out_r90, x.base90) + '.') +
      (lo ? _T('最近一段 ' + ymdS(lo.start) + ' 起（' + fmt.usd(lo.price) + '）' + (lo.r90 != null ? '，90 天後 ' + fmt.pct(lo.r90, 1) : '，還不到 90 天') + '。', ' Latest from ' + ymdS(lo.start) + ' (' + fmt.usd(lo.price) + ')' + (lo.r90 != null ? ', ' + fmt.pct(lo.r90, 1) + ' 90 days later' : ', under 90 days ago') + '.') : ''), 'neu']);
    it.push([_T('強流入之後', 'After strong inflows'), x.n_in + _T(' 段', ' stretches'),
      _T('落到近 4 年最高 10%（強流入）共 ' + x.n_in + ' 段，進入後 90 天：', 'The 4-year top 10% (strong inflow) ' + x.n_in + ' times; 90 days later: ') + oxStat(x.in_r90, x.base90) + _T('，' + cqCmp(x.in_r90, x.base90) + '。流量本身分不出方向，要和價格、其他賣壓一起看。', ', ' + cqCmp(x.in_r90, x.base90) + '. Flows alone do not tell direction; read them with price and other selling gauges.'), 'neu']);
    return it;
  }
  function exfPanel() {
    var x = (D.flows || {}).exflow; if (!x || !x.rows) return '';
    return panel('span-12', _T('交易所淨流量', 'Exchange netflow'), 'CoinMetrics · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard(x.out ? 'var(--up)' : 'var(--down)', _T('30 天合計', '30-day sum'), cqBtc(x.s30), _T('顆；近 4 年第 ' + fmt.n(x.pct4, 0) + ' 百分位', 'BTC; ' + fmt.n(x.pct4, 0) + 'th percentile of 4 years')) +
        oxCard(x.net <= 0 ? 'var(--up)' : 'var(--down)', _T('最新一天', 'Latest day'), cqBtc(x.net), _T('顆 · ' + fmt.md(x.date), 'BTC · ' + fmt.md(x.date))) + '</div>' +
      interpHtml(exfSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('30 天淨流出', '30-day net outflow'), 'var(--up)'], [_T('30 天淨流入', '30-day net inflow'), 'var(--down)'], [_T('強流出（近 4 年最低 10%）', 'Strong outflow (4-year bottom 10%)'), 'var(--up)', 'box'], [_T('強流入（近 4 年最高 10%）', 'Strong inflow (4-year top 10%)'), 'var(--down)', 'box']]) +
      '<div class="chart cf-chart" id="c-exflow"></div><p class="note">' + _T('流入交易所的幣 − 流出的幣（顆），30 天合計。交易所地址由 CoinMetrics 歸屬，會事後修正，新交易所或新錢包加入時整條線會跳。流入不一定是要賣（交易所整理錢包、託管機構搬幣也算），流出也不一定是買。只作讀值。',
        'Coins flowing into exchanges − coins flowing out (BTC), summed over 30 days. Exchange addresses are attributed by CoinMetrics and revised later; the line jumps when new exchanges or wallets are added. Inflows are not always selling (exchange wallet reshuffles and custodian moves count), and outflows are not always buying. Reading only.') + '</p>', '', 'exflow');
  }
  function drawExf(el) {
    var x = (D.flows || {}).exflow; if (!x || !el) return;
    var f = function (v) { return cqBtc(v) + _T(' 顆', ' BTC'); }, kf = function (v) { return (v > 0 ? '+' : '') + fmt.k(v); };
    var vb = function (L, col) { return (L || []).map(function (e) { return { x0: dnOf(e.start), x1: dnOf(e.end) + 2, col: col, op: 0.14 }; }); };
    oxPane(el, { rows: x.rows, rng: 1095, fit: true, zero: true, fmt: kf, label: _T('交易所淨流量（30 天合計，顆）', 'Exchange netflow (30-day sum, BTC)'), aria: _T('BTC 價格與交易所淨流量', 'BTC price and exchange netflow'),
      vbands: vb(x.out_eps, 'var(--up)').concat(vb(x.in_eps, 'var(--down)')),
      lines: [{ i: 3, split: ['var(--down)', 'var(--up)'], w: 1.6, name: _T('30 天合計', '30-day sum'), tfmt: f }],
      tipExtra: function (p) { return tipRow1('var(--ink-3)', _T('當天', 'That day'), f(p[2])); },
      now: { i: 3, col: x.out ? 'var(--up)' : 'var(--down)', lab: _T('現在 ', 'Now ') + kf(x.s30) } });
  }

  /* ② 現貨 vs 永續需求 */
  var DMD_K = { pp: ['pos', '現貨與永續一起買', 'Spot and perps both buying', '兩邊都有新買盤。', 'Both sides are adding.'],
    pn: ['pos', '現貨在買、槓桿在退', 'Spot buying, leverage stepping back', '現貨在接、槓桿在退，比較扎實的上漲常是這樣。', 'Spot absorbing while leverage steps back — the sturdier kind of rally usually looks like this.'],
    np: ['warn', '槓桿在撐、現貨沒跟', 'Leverage carrying it, spot not following', '買盤靠槓桿、現貨沒有接，比較容易回吐。', 'Buying comes from leverage without spot behind it, which gives back more easily.'],
    nn: ['neg', '現貨與永續都在減', 'Spot and perps both pulling back', '現貨與槓桿兩邊都沒有新買盤。', 'Neither spot nor leverage is adding.'] };
  function dmdSay() {
    var x = (D.onchain || {}).dmd; if (!x) return [];
    var it = [], k = (x.spot_pos ? 'p' : 'n') + (x.perp_pos == null ? '' : x.perp_pos ? 'p' : 'n'), K = DMD_K[k], lf = (x.flips || [])[(x.flips || []).length - 1];
    if (!K) it.push([_T('現在', 'Now'), cqBtc(x.spot) + _T(' 顆', ' BTC'), _T('現貨需求（表觀需求 30 天）' + cqBtc(x.spot) + ' 顆；今天沒有永續的資料。', 'Spot demand (30-day apparent demand) ' + cqBtc(x.spot) + ' BTC; no perpetual data today.'), x.spot_pos ? 'pos' : 'neg']);
    if (K) it.push([_T('現在', 'Now'), cqBtc(x.spot) + _T(' 顆', ' BTC'), _T(K[1] + '：現貨需求（表觀需求 30 天）' + cqBtc(x.spot) + ' 顆；OKX 永續 30 天主動買 − 主動賣 ' + cqB(x.perp / 1000) + '。' + K[3], K[2] + ': spot demand (30-day apparent demand) ' + cqBtc(x.spot) + ' BTC; OKX perps 30-day taker buy − sell ' + cqB(x.perp / 1000) + '. ' + K[4]), K[0]]);   // 數值欄不換行，手機上長標籤會撐出版面（CI 390px 抓到），標籤放進文字
    if (x.r60 && x.r60.n) it.push([_T('現貨需求轉正之後', 'After spot demand turns positive'), x.r60.n + _T(' 次', ' times'),
      _T('2020 起，現貨需求 30 天合計由負轉正（相隔 60 天以上才算新的一次）' + x.r60.n + ' 次，之後 60 天 ' + x.r60.up + ' 次上漲、中位數 ' + fmt.pct(x.r60.med, 1) + '（同期任一天 ' + x.base60.up + '% 上漲、中位數 ' + fmt.pct(x.base60.med, 1) + '）。',
        'Since 2020 the 30-day spot demand turned from negative to positive ' + x.r60.n + ' times (60+ days apart); 60 days later ' + x.r60.up + ' rose, median ' + fmt.pct(x.r60.med, 1) + ' (any day: ' + x.base60.up + '% rose, median ' + fmt.pct(x.base60.med, 1) + ').') +
      (lf ? _T('最近一次 ' + ymdS(lf.date) + '（' + fmt.usd(lf.price) + '）' + (lf.r60 != null ? '，60 天後 ' + fmt.pct(lf.r60, 1) : '，還不到 60 天') + '。', ' Latest ' + ymdS(lf.date) + ' (' + fmt.usd(lf.price) + ')' + (lf.r60 != null ? ', ' + fmt.pct(lf.r60, 1) + ' 60 days later' : ', under 60 days ago') + '.') : ''), 'neu']);
    return it;
  }
  function dmdPanel() {
    var x = (D.onchain || {}).dmd; if (!x || !x.rows) return '';
    return panel('span-12', _T('現貨 vs 永續需求', 'Spot vs perpetual demand'), _T('表觀需求 · OKX · ' + fmt.md(x.date), 'Apparent demand · OKX · ' + fmt.md(x.date)),
      '<div class="cf-hero">' + oxCard(x.spot_pos ? 'var(--up)' : 'var(--down)', _T('現貨需求 30 天', 'Spot demand, 30 days'), cqBtc(x.spot), _T('顆（表觀需求）', 'BTC (apparent demand)')) +
        (x.perp != null ? oxCard(x.perp_pos ? 'var(--up)' : 'var(--down)', _T('永續淨主動買 30 天', 'Perp net taker buying, 30 days'), cqB(x.perp / 1000), _T('OKX 合約', 'OKX contracts')) : '') + '</div>' +
      interpHtml(dmdSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('現貨（表觀需求 30 天）', 'Spot (30-day apparent demand)'), 'var(--s3)'], [_T('永續（OKX 30 天主動買 − 賣）', 'Perps (OKX 30-day taker buy − sell)'), 'var(--s2)'], [_T('現貨轉正，膠囊是之後 60 天漲跌', 'Spot turns positive; capsules show the next 60 days'), 'var(--s3)', 'box']]) +
      '<div class="chart cf-chart" id="c-dmd"></div><p class="note">' + _T('現貨＝表觀需求（30 天新挖出的幣 − 1 年以上沒動過的供給的變化，顆）；永續＝OKX 合約 30 天主動買進 − 主動賣出（美元，日界 UTC+8）。兩者單位不同，圖上各除以自己近一年絕對值的最大值（−1 到 1），只比方向與相對強弱；提示框是原始數字。永續只有 OKX 一家，資料從 ' + ymdS(x.perp_since || '') + ' 起（公開 API 最多回 180 天，之後逐日累積）。只作讀值。',
        'Spot = apparent demand (coins mined in 30 days − the change in supply unmoved for 1y+, BTC); perps = OKX contracts 30-day taker buys − taker sells (USD, UTC+8 days). The units differ, so each is divided by its own largest absolute value over the past year (−1 to 1) to compare direction and relative strength; the tooltip shows raw numbers. Perps are OKX only, from ' + ymdS(x.perp_since || '') + ' (the public API returns 180 days at most; it accumulates daily from here). Reading only.') + '</p>', '', 'dmd');
  }
  function drawDmd(el) {
    var x = (D.onchain || {}).dmd; if (!x || !el) return;
    oxPane(el, { rows: x.rows, rng: 365, fit: true, zero: true, fmt: function (v) { return fmt.n(v, 1); }, label: _T('需求（各除以近一年最大值）', 'Demand (each ÷ its 1-year max)'), aria: _T('BTC 價格、現貨需求與永續需求', 'BTC price, spot demand and perpetual demand'),
      lines: [{ i: 3, col: 'var(--s2)', w: 1.5, name: _T('永續 30 天', 'Perps, 30 days'), tfmt: function (v, p) { return p && p[5] != null ? cqB(p[5] / 1000) : fmt.n(v, 2); } },
        { i: 2, col: 'var(--s3)', w: 1.9, name: _T('現貨 30 天', 'Spot, 30 days'), tfmt: function (v, p) { return p && p[4] != null ? cqBtc(p[4]) + _T(' 顆', ' BTC') : fmt.n(v, 2); } }],
      marks: (x.flips || []).map(function (f) { return { x: dnOf(f.date), y: 0, t: f.r60 == null ? _T('轉正', 'turns +') : _T('60 天 ', '60d ') + fmt.pct(f.r60, 0), col: 'var(--s3)', up: true }; }),
      now: { i: 2, col: 'var(--s3)', lab: '' } });
  }

  /* ③ ETF 持有者成本 */
  function etfcSay() {
    var x = (D.flows || {}).etfcost; if (!x) return [];
    var it = [], f30 = x.flow30 / 1000;
    it.push([_T('現價 vs 成本', 'Price vs cost'), fmt.pct(x.gap_now, 1),
      _T('最新收盤 ' + fmt.usd(x.px_now) + '（' + fmt.md(x.px_date) + '）' + (x.below ? '低於' : '高於') + ' ETF 持有者平均成本 ' + fmt.usd(x.cost) + '（' + fmt.md(x.date) + '）' + fmt.pct(x.gap_now, 1) + '：平均來說 ETF 買家帳面' + (x.below ? '虧損。' : '獲利。'),
        'The latest close ' + fmt.usd(x.px_now) + ' (' + fmt.md(x.px_date) + ') is ' + fmt.pct(x.gap_now, 1) + ' ' + (x.below ? 'below' : 'above') + ' the average ETF holder cost of ' + fmt.usd(x.cost) + ' (' + fmt.md(x.date) + '): on average ETF buyers are ' + (x.below ? 'underwater.' : 'in profit.')), x.below ? 'warn' : 'neu']);
    it.push([_T('上市以來', 'Since launch'), x.days_below + ' / ' + x.n_days + _T(' 天', ' days'),
      _T(ymdS(x.since).slice(0, 7) + ' 上市以來，價格在成本下方 ' + x.days_below + ' 天（共 ' + x.n_days + ' 天），最深 ' + fmt.pct(x.min_gap, 1) + '（' + ymdS(x.min_date) + '）；穿越成本線 ' + x.n_cross + ' 次。',
        'Since launch in ' + ymdS(x.since).slice(0, 7) + ', price spent ' + x.days_below + ' of ' + x.n_days + ' days below cost, deepest ' + fmt.pct(x.min_gap, 1) + ' (' + ymdS(x.min_date) + '); it crossed the cost line ' + x.n_cross + ' times.'), 'neu']);
    it.push([_T('近 30 天流量', 'Flows, last 30 days'), cqB(f30),
      _T('不含 GBTC 淨' + (f30 >= 0 ? '流入 ' : '流出 ') + cqB(Math.abs(f30)).replace('+', '') + '（含 GBTC ' + cqB(x.flow30_all / 1000) + '）' + (x.below ? (f30 < 0 ? '；價格在成本之下還在流出，帳面虧損的人在退場。' : '；價格在成本之下仍有流入，有人在成本下方加碼。') : '。'),
        'Net ' + (f30 >= 0 ? 'inflow ' : 'outflow ') + cqB(Math.abs(f30)).replace('+', '') + ' excluding GBTC (' + cqB(x.flow30_all / 1000) + ' including it)' + (x.below ? (f30 < 0 ? '; still leaving below cost — underwater holders are exiting.' : '; still arriving below cost — some are adding under water.') : '.')), f30 >= 0 ? 'pos' : 'neg']);
    return it;
  }
  function etfcPanel() {
    var x = (D.flows || {}).etfcost; if (!x || !x.rows) return '';
    return panel('span-12', _T('ETF 持有者成本', 'ETF holder cost basis'), _T('The Block · 不含 GBTC · ' + fmt.md(x.date), 'The Block · ex-GBTC · ' + fmt.md(x.date)),
      '<div class="cf-hero">' + oxCard('var(--s1)', _T('平均成本', 'Average cost'), fmt.usd(x.cost), _T('推算持有 ' + fmt.n(x.held / 1e4, 1) + ' 萬顆', 'about ' + fmt.n(x.held / 1e3, 0) + 'K BTC held')) +
        oxCard(x.below ? 'var(--down)' : 'var(--up)', _T('現價相對成本', 'Price vs cost'), fmt.pct(x.gap_now, 1), _T('收盤 ' + fmt.usd(x.px_now), 'close ' + fmt.usd(x.px_now))) + '</div>' +
      interpHtml(etfcSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('ETF 持有者成本', 'ETF holder cost'), 'var(--s1)'], [_T('價格高於成本', 'Price above cost'), 'var(--up)'], [_T('價格低於成本', 'Price below cost'), 'var(--down)']]) +
      '<div class="chart cf-chart" id="c-etfcost"></div><p class="note">' + _T('推算：每檔現貨 ETF 每天的淨流量 ÷ 當天收盤＝買進（或賣出）的顆數，用平均成本法累計（流出時依當時的平均成本移出）。不含 GBTC：它在轉成 ETF 前就持有約 62 萬顆，成本不是靠流量買出來的。實際買進價在當天高低之間，和託管地址收到幣的時間也不一定同一天，所以和看鏈上地址的做法會有差距。只作讀值。',
        'Estimated: each spot ETF\'s daily net flow ÷ that day\'s close = coins bought (or sold), accumulated at average cost (outflows remove coins at the running average). GBTC is excluded: it held about 620K BTC before converting, so its cost was not built from flows. Actual fills land anywhere in the day\'s range and custody wallets may receive coins on another day, so on-chain methods give a different number. Reading only.') + '</p>', '', 'etfcost');
  }
  function drawEtfc(el) {
    var x = (D.flows || {}).etfcost; if (!x || !el) return;
    oxPane(el, { rows: x.rows, zero: true, fmt: function (v) { return fmt.pct(v, 0); }, label: _T('價格相對 ETF 成本（%）', 'Price vs ETF cost (%)'), aria: _T('BTC 價格與 ETF 持有者成本', 'BTC price and ETF holder cost'),
      plines: [{ i: 2, col: 'var(--s1)', w: 1.8, name: _T('ETF 持有者成本', 'ETF holder cost') }],
      lines: [{ i: 4, split: ['var(--up)', 'var(--down)'], w: 1.6, name: _T('相對成本', 'Vs cost'), tfmt: function (v) { return fmt.pct(v, 1); } }],
      tipExtra: function (p) { return tipRow1('var(--ink-3)', _T('推算持有', 'Estimated holdings'), _T(fmt.n(p[3] / 10, 1) + ' 萬顆', fmt.n(p[3], 0) + 'K BTC')); },
      now: { i: 4, col: x.gap >= 0 ? 'var(--up)' : 'var(--down)', lab: '' } });
  }

  /* ④ 一年累計淨實現損益（顆） */
  function n365Say() {
    var x = (D.onchain || {}).npl365; if (!x) return [];
    var it = [], bt = x.bottoms || [], cur = bt[bt.length - 1], past = bt.slice(0, -1), tp = x.tops || [];
    var yr = function (b) { return b.date.slice(0, 4) + ' ' + cqKb(b.value); };
    it.push([_T('近一年合計', 'Past-year total'), cqKb(x.value) + _T('顆', ' BTC'),
      _T('近 365 天的淨實現損益換成顆數合計 ' + cqKb(x.value) + ' 顆' + (x.value < 0 && x.neg_since ? '（' + ymdS(x.neg_since) + ' 起轉負）' : '') + '，30 天前 ' + cqKb(x.v30) + ' 顆：' + (x.value < 0 ? (x.value < x.v30 ? '一年來整體在認賠賣出，而且還在加深。' : '一年來整體在認賠賣出，但在收斂。') : '一年來整體是獲利了結。'),
        'Net realized profit/loss over the past 365 days, converted to coins: ' + cqKb(x.value) + ' BTC' + (x.value < 0 && x.neg_since ? ' (negative since ' + ymdS(x.neg_since) + ')' : '') + ', vs ' + cqKb(x.v30) + ' 30 days ago: ' + (x.value < 0 ? (x.value < x.v30 ? 'the market has been selling at a loss over the year, and it is deepening.' : 'the market has been selling at a loss over the year, but it is easing.') : 'the market has been taking profit over the year.')), x.value < 0 ? 'warn' : 'neu']);
    if (cur && past.length) {
      var pv = past[past.length - 1];
      it.push([_T('和熊市底部比', 'Against bear-market bottoms'), cqKb(cur.value),
        _T('前幾輪熊市最深：' + past.map(yr).join('、') + ' 顆；這一輪到目前最深 ' + cqKb(cur.value) + ' 顆（' + ymdS(cur.date) + '），約上一輪的 ' + fmt.n(cur.value / pv.value * 100, 0) + '%。兩種可能：持有結構改變（ETF、長期持有者沒有跟著賣）讓認賠變少，或認賠還沒走完；單看這一項分不出來。',
          'Deepest in past bear markets: ' + past.map(yr).join(', ') + ' BTC; this cycle so far ' + cqKb(cur.value) + ' BTC (' + ymdS(cur.date) + '), about ' + fmt.n(cur.value / pv.value * 100, 0) + '% of the last one. Either the holder base changed (ETFs, long-term holders not selling) so less loss gets realized, or the loss-taking is not finished; this gauge alone cannot tell.'), 'neu']);
    }
    if (tp.length) {
      var lowest = tp.every(function (t) { return tp[tp.length - 1].value <= t.value; });
      it.push([_T('頂部前後', 'Around tops'), cqKb(tp[tp.length - 1].value),
        _T('頂部前後半年的最高：' + tp.map(yr).join('、') + ' 顆' + (lowest ? '；最近一輪是歷來最少的一次。' : '。'), 'Highest within six months of each top: ' + tp.map(yr).join(', ') + ' BTC' + (lowest ? '; the latest cycle was the smallest yet.' : '.')), 'neu']);
    }
    return it;
  }
  function n365Panel() {
    var x = (D.onchain || {}).npl365; if (!x || !x.rows) return '';
    return panel('span-12', _T('一年累計淨實現損益（顆）', 'One-year net realized P/L (BTC)'), 'CoinMetrics · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard(x.value < 0 ? 'var(--down)' : 'var(--up)', _T('近 365 天', 'Last 365 days'), cqKb(x.value), _T('顆', 'BTC'), _T(oxArrow(x.value / 10, x.v30 / 10, ' 萬', 1), oxArrow(x.value, x.v30, 'K', 0))) + '</div>' +
      interpHtml(n365Say()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('一年累計：獲利了結', 'One-year sum: profit-taking'), 'var(--up)'], [_T('一年累計：認賠', 'One-year sum: loss-taking'), 'var(--down)']]) +
      '<div class="chart cf-chart" id="c-npl365"></div><p class="note">' + _T('每天的淨實現損益（實現市值的變化減新發行，美元）除以當天價格換成顆數，再加總 365 天。換成顆數之後，不同價格時代的認賠可以直接比；負得越深＝一年內有越多幣在賠錢賣。資料 CoinMetrics，逐筆 UTXO、不是實體調整。只作讀值。',
        'Each day\'s net realized profit/loss (change in realized cap minus new issuance, USD) divided by that day\'s price to get coins, summed over 365 days. In coins, loss-taking from different price eras compares directly; deeper negative = more coins sold at a loss within the year. Data: CoinMetrics, per UTXO, not entity-adjusted. Reading only.') + '</p>', '', 'npl365');
  }
  function drawN365(el) {
    var x = (D.onchain || {}).npl365; if (!x || !el) return;
    var mk = (x.bottoms || []).map(function (b) { return { x: dnOf(b.date), y: b.value, t: b.date.slice(0, 4) + ' ' + cqKb(b.value), col: 'var(--down)', up: false }; })
      .concat((x.tops || []).map(function (t) { return { x: dnOf(t.date), y: t.value, t: t.date.slice(0, 4) + ' ' + cqKb(t.value), col: 'var(--up)', up: true }; }));
    oxPane(el, { rows: x.rows, zero: true, fmt: cqKt, label: _T('一年累計淨實現損益（顆）', 'One-year net realized P/L (BTC)'), aria: _T('BTC 價格與一年累計淨實現損益', 'BTC price and one-year net realized profit/loss'),
      lines: [{ i: 2, split: ['var(--up)', 'var(--down)'], w: 1.6, area: false, name: _T('一年累計', 'One-year sum'), tfmt: function (v) { return cqKb(v) + _T('顆', ' BTC'); } }],
      marks: mk, now: { i: 2, col: x.value < 0 ? 'var(--down)' : 'var(--up)', lab: '' } });
  }

  /* 短期持有者供給 90 天變化（2026-11-08 使用者要求，X 上 Alphractal 清算圖的下格）：Bitview sth_supply 今天 − 90 天前，顆。只作讀值 */
  function sthdSay() {
    var x = (D.onchain || {}).sthd; if (!x) return [];
    var it = [], v = x.value / 1e3, pos = x.sign > 0, pk = x.peak, kb = function (n) { return cqKb(n / 1e3); };
    it.push([_T('90 天變化', '90-day change'), kb(x.value) + _T(' 顆', ' BTC'),
      _T('短期持有者供給 ' + cqKb(x.sth / 1e3).replace('+', '') + ' 顆，90 天前 ' + cqKb(x.sth90 / 1e3).replace('+', '') + ' 顆。' + ymdS(x.since) + ' 起' + (pos ? '轉正' : '轉負') + '，這一段' + (pos ? '最高' : '最低') + '是 ' + ymdS(pk.date) + ' 的 ' + kb(pk.value) + ' 顆' + (Math.abs(x.off_peak) >= 1e4 ? '，之後' + (pos ? '回落 ' : '回升 ') + cqKb(Math.abs(x.off_peak) / 1e3).replace('+', '') + ' 顆' : '') + '；30 天前是 ' + kb(x.v30) + ' 顆。',
        'Short-term holder supply is ' + cqKb(x.sth / 1e3).replace('+', '') + ' BTC versus ' + cqKb(x.sth90 / 1e3).replace('+', '') + ' 90 days ago. ' + (pos ? 'Positive' : 'Negative') + ' since ' + ymdS(x.since) + '; this run\'s ' + (pos ? 'high' : 'low') + ' was ' + kb(pk.value) + ' on ' + ymdS(pk.date) + (Math.abs(x.off_peak) >= 1e4 ? ', ' + cqKb(Math.abs(x.off_peak) / 1e3).replace('+', '') + (pos ? ' lower' : ' higher') + ' since' : '') + '; 30 days ago it was ' + kb(x.v30) + '.'), 'neu']);
    it.push([_T('怎麼讀', 'How to read it'), pos ? _T('舊幣在換手', 'Old coins changing hands') : _T('幣在沉澱', 'Coins settling'),
      _T('正值＝90 天內被移動過、算成短期持有的幣，比放滿 155 天轉成長期的多：長期持有者在賣給新買家，交易所或託管搬幣也會算進來。負值＝幣放著不動、陸續轉成長期。量的是幣有沒有被移動，不直接等於短期持有者在買或在賣。',
        'Positive = more coins were moved in the past 90 days (and so count as short-term) than aged past 155 days into long-term: long-term holders selling to new buyers, plus exchange or custody wallet moves. Negative = coins sitting still and aging into long-term. It measures whether coins move, not directly whether short-term holders are buying or selling.'), 'neu']);
    if (x.tops && x.tops.length) it.push([_T('頂部附近的規模', 'Size around tops'), _T('上一輪 ', 'Last cycle ') + cqKb(x.tops[x.tops.length - 1].value / 1e3),
      _T('每輪頂部前後半年內的最大值：' + x.tops.map(function (t) { return oxYm(t.date) + ' ' + kb(t.value) + ' 顆'; }).join('、') + '。現在 ' + kb(x.value) + ' 顆。2021 年那輪特別小，大量換手發生在頂部之前更早的 2020 年底到 2021 年初。',
        'The largest reading within six months of each top: ' + x.tops.map(function (t) { return oxYm(t.date) + ' ' + kb(t.value); }).join(', ') + '. Now ' + kb(x.value) + '. The 2021 cycle is unusually small because its big turnover came earlier, in late 2020 to early 2021.'), 'neu']);
    if (x.up && x.up.n) it.push([_T('轉正、轉負之後', 'After it flips'), x.up.up + '/' + x.up.n,
      _T('2015 年起轉正 ' + x.up.n + ' 次，90 天後 ' + oxStat(x.up, x.base) + '；轉負 ' + x.down.n + ' 次，' + x.down.up + ' 次上漲、中位數 ' + fmt.pct(x.down.med, 1) + '。翻正翻負本身不是買賣訊號。',
        'Since 2015 it turned positive ' + x.up.n + ' times; 90 days later ' + oxStat(x.up, x.base) + '. It turned negative ' + x.down.n + ' times; ' + x.down.up + ' rose, median ' + fmt.pct(x.down.med, 1) + '. A flip on its own is not a buy or sell signal.'), 'neu']);
    return it;
  }
  function sthdPanel() {
    var x = (D.onchain || {}).sthd; if (!x || !x.rows) return '';
    var pos = x.sign > 0;
    return panel('span-12', _T('短期持有者供給 90 天變化', 'Short-term holder supply, 90-day change'), 'Bitview · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard(pos ? 'var(--s2)' : 'var(--s3)', _T('90 天變化', '90-day change'), cqKb(x.value / 1e3), _T('顆', 'BTC'), _T(oxArrow(x.value / 1e4, x.v30 / 1e4, ' 萬', 1), oxArrow(x.value / 1e3, x.v30 / 1e3, 'K', 0))) +
      oxCard('var(--ink-3)', _T('短期持有者供給', 'Short-term holder supply'), cqKb(x.sth / 1e3).replace('+', ''), _T('持有未滿 155 天', 'held under 155 days')) + '</div>' +
      interpHtml(sthdSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('增加：舊幣換手', 'Rising: old coins changing hands'), 'var(--s2)'], [_T('減少：幣在沉澱', 'Falling: coins settling'), 'var(--s3)']]) +
      '<div class="chart cf-chart" id="c-sthd"></div><p class="note">' + _T('短期持有者＝持有未滿 155 天（以幣最後一次移動算，逐筆 UTXO、不是實體調整）。數值＝今天的短期持有者供給 − 90 天前，資料 Bitview，每 3 天畫一點。交易所、託管整理錢包也會讓幣「變年輕」，所以單日跳動不一定是買賣。只作讀值。',
        'Short-term holders = coins held under 155 days (since their last move; per UTXO, not entity-adjusted). Value = today\'s short-term holder supply minus 90 days earlier, from Bitview, plotted every 3 days. Exchange and custody wallet reshuffles also make coins "younger", so a jump is not necessarily trading. Reading only.') + '</p>', '', 'sthd');
  }
  function drawSthd(el) {
    var x = (D.onchain || {}).sthd; if (!x || !el) return;
    var mk = (x.tops || []).map(function (t) { return { x: dnOf(t.date), y: t.value / 1e3, t: t.date.slice(0, 4) + ' ' + cqKb(t.value / 1e3), col: 'var(--s2)', up: true }; });
    oxPane(el, { rows: x.rows, rng: 1095, fit: true, zero: true, fmt: cqKt, label: _T('短期持有者供給 90 天變化（顆）', 'STH supply 90-day change (BTC)'), aria: _T('BTC 價格與短期持有者供給 90 天變化', 'BTC price and the 90-day change in short-term holder supply'),
      lines: [{ i: 2, split: ['var(--s2)', 'var(--s3)'], w: 1.5, name: _T('90 天變化', '90-day change'), tfmt: function (v) { return cqKb(v) + _T(' 顆', ' BTC'); } }],
      marks: mk, now: { i: 2, col: x.sign > 0 ? 'var(--s2)' : 'var(--s3)', lab: '' } });
  }

  /* ⑤ 韓國溢價 */
  function kpSay() {
    var x = (D.flows || {}).kp; if (!x) return [];
    var it = [], a = x.a7, lv = a >= 5 ? 'hot' : a <= -1 ? 'cold' : 'mid', hl = (x.hot || [])[(x.hot || []).length - 1];
    var LV = { hot: ['韓國散戶在追價，偏熱。', 'Korean retail is chasing — running hot.'], cold: ['折價，韓國買盤冷。', 'A discount — Korean demand is cold.'], mid: ['在常態範圍內，韓國散戶沒有明顯追價。', 'Within the normal range; no obvious chasing by Korean retail.'] };
    it.push([_T('7 日平均', '7-day average'), fmt.pct(a, 2),
      _T('Upbit 的韓元價格換成美元後' + (a >= 0 ? '貴 ' : '便宜 ') + fmt.n(Math.abs(a), 2) + '%（最新一天 ' + fmt.pct(x.value, 2) + '、30 日 ' + fmt.pct(x.a30, 2) + '，近 4 年第 ' + fmt.n(x.pct4, 0) + ' 百分位；全期中位數 ' + fmt.pct(x.med, 2) + '）：' + LV[lv][0],
        'Upbit\'s KRW price converted to USD is ' + fmt.n(Math.abs(a), 2) + '% ' + (a >= 0 ? 'higher' : 'lower') + ' (latest day ' + fmt.pct(x.value, 2) + ', 30-day ' + fmt.pct(x.a30, 2) + ', ' + fmt.n(x.pct4, 0) + 'th percentile of 4 years; all-time median ' + fmt.pct(x.med, 2) + '): ' + LV[lv][1]), lv === 'hot' ? 'warn' : 'neu']);
    if (x.hot90 && x.hot90.n) it.push([_T('衝上 5% 之後', 'After spikes above 5%'), x.hot90.n + _T(' 次', ' times'),
      _T('7 日平均衝上 5%（相隔 30 天以上算新的一次）之後 90 天：', 'After the 7-day average rose above 5% (30+ days apart), 90 days later: ') + oxStat(x.hot90, x.base90) + _T('，' + cqCmp(x.hot90, x.base90) + '。', ', ' + cqCmp(x.hot90, x.base90) + '.') +
      (hl ? _T('最近一次 ' + ymdS(hl.start) + '（' + fmt.usd(hl.price) + '）' + (hl.r90 != null ? '，90 天後 ' + fmt.pct(hl.r90, 1) : '') + '。', ' Latest ' + ymdS(hl.start) + ' (' + fmt.usd(hl.price) + ')' + (hl.r90 != null ? ', ' + fmt.pct(hl.r90, 1) + ' 90 days later' : '') + '.') : ''), 'neu']);
    var ys = (x.years || []).filter(function (y) { return y.max >= 5; });
    if (ys.length) it.push([_T('歷年高點', 'Yearly highs'), fmt.pct(ys[ys.length - 1].max, 1),
      _T('7 日平均到 5% 以上的年份：' + ys.map(function (y) { return ymdS(y.max_date).slice(0, 7) + ' ' + fmt.pct(y.max, 1); }).join('、') + '。', 'Years when the 7-day average topped 5%: ' + ys.map(function (y) { return ymdS(y.max_date).slice(0, 7) + ' ' + fmt.pct(y.max, 1); }).join(', ') + '.'), 'neu']);
    return it;
  }
  function kpPanel() {
    var x = (D.flows || {}).kp; if (!x || !x.rows) return '';
    return panel('span-12', _T('韓國溢價', 'Korea premium'), 'Upbit · ' + fmt.md(x.date),
      '<div class="cf-hero">' + oxCard(x.a7 >= 0 ? 'var(--up)' : 'var(--down)', _T('7 日平均', '7-day average'), fmt.pct(x.a7, 2), _T('近 4 年第 ' + fmt.n(x.pct4, 0) + ' 百分位', fmt.n(x.pct4, 0) + 'th percentile of 4 years')) + oxCard('var(--ink-3)', _T('最新一天', 'Latest day'), fmt.pct(x.value, 2), fmt.md(x.date)) + '</div>' +
      interpHtml(kpSay()) + legend([[_T('BTC 價格', 'BTC price'), 'var(--ink-2)'], [_T('7 日平均：溢價', '7-day average: premium'), 'var(--up)'], [_T('7 日平均：折價', '7-day average: discount'), 'var(--down)'], [_T('每日', 'Daily'), 'var(--ink-3)'], [_T('5%：偏熱', '5%: running hot'), 'var(--warn)', 'dash']]) +
      '<div class="chart cf-chart" id="c-kp"></div><p class="note">' + _T('Upbit KRW-BTC 日收盤（UTC）÷（美元收盤 × 美元兌韓元）− 1；匯率用歐洲央行參考匯率，週末沿用前一個工作日。韓國有資本管制，套利不容易，所以溢價可以長期存在；只看 Upbit 一家。縱軸是壓縮刻度（2018 年初曾到 50%）。只作讀值。',
        'Upbit KRW-BTC daily close (UTC) ÷ (USD close × USD/KRW) − 1, using ECB reference rates (weekends carry the previous business day). Capital controls make arbitrage hard, so a premium can persist; Upbit only. The vertical axis is compressed (it reached 50% in early 2018). Reading only.') + '</p>', '', 'kp');
  }
  var KPT = function (v) { return v >= 0 ? Math.log10(1 + v) : -Math.log10(1 - v); };
  function drawKp(el) {
    var x = (D.flows || {}).kp; if (!x || !el) return;
    var f = function (v) { return fmt.pct(v, 2); };
    oxPane(el, { rows: x.rows, rng: 1095, fit: true, tf: KPT, ticks: [-5, -2, 0, 2, 5, 10, 20, 50], fmt: function (v) { return fmt.pct(v, 0); }, label: _T('韓國溢價（%，壓縮刻度）', 'Korea premium (%, compressed scale)'), aria: _T('BTC 價格與韓國溢價', 'BTC price and Korea premium'),
      refs: [{ y: 5, col: 'var(--warn)' }],
      lines: [{ i: 2, col: 'var(--ink-3)', w: 1, op: 0.45, name: _T('每日', 'Daily'), tfmt: f }, { i: 3, split: ['var(--up)', 'var(--down)'], w: 1.8, name: _T('7 日平均', '7-day average'), tfmt: f }],
      now: { i: 3, col: x.a7 >= 0 ? 'var(--up)' : 'var(--down)', lab: _T('現在 ', 'Now ') + fmt.pct(x.a7, 1) } });
  }

  /* ⑥ 每輪資金效率（表格，沒有走勢圖） */
  function ceSay() {
    var x = (D.onchain || {}).capeff; if (!x || !x.cycles || !x.cycles.length) return [];
    var cy = x.cycles, c = x.cur, it = [], sep = _T(' → ', ' → ');
    var upA = cy.every(function (r, i) { return !i || r.add_b > cy[i - 1].add_b; }), dnM = cy.every(function (r, i) { return !i || r.mult < cy[i - 1].mult; });
    var mf = function (m) { return fmt.n(m, m < 10 ? 1 : 0) + '×'; };
    it.push([_T('一輪比一輪', 'Cycle by cycle'), mf(cy[cy.length - 1].mult),
      _T('每輪從熊市底部到頂部，流入的資金：' + cy.map(function (r) { return cqB(r.add_b).replace('+', ''); }).join(sep) + '；價格倍數：' + cy.map(function (r) { return mf(r.mult); }).join(sep) + '。' + (upA && dnM ? '流入一輪比一輪多、漲幅一輪比一輪小：市場越大，同樣的漲幅要越多錢。' : ''),
        'From each bear-market bottom to the top, money in: ' + cy.map(function (r) { return cqB(r.add_b).replace('+', ''); }).join(sep) + '; price multiple: ' + cy.map(function (r) { return mf(r.mult); }).join(sep) + '. ' + (upA && dnM ? 'More money each cycle, smaller gains each cycle: the bigger the market, the more money the same gain takes.' : '')), 'neu']);
    if (c) {
      var sm = cy.filter(function (r) { return r.same; }), more = sm.length && sm.every(function (r) { return c.add_b > r.same.add_b; }), less = sm.length && sm.every(function (r) { return c.mult < r.same.mult; });
      it.push([_T('這一輪到現在', 'This cycle so far'), cqB(c.add_b) + ' · ' + fmt.n(c.mult, 2) + '×',
        _T('從 ' + ymdS(c.bottom) + ' 的底部起 ' + c.days + ' 天：流入 ' + cqB(c.add_b) + '、價格 ' + fmt.n(c.mult, 2) + ' 倍。前幾輪走到同一天：' + sm.map(function (r) { return r.bottom.slice(0, 4) + ' 那輪流入 ' + cqB(r.same.add_b) + '、' + fmt.n(r.same.mult, 2) + ' 倍'; }).join('；') + '。' + (more && less ? '這一輪同期流入比較多、漲得卻比較少。' : ''),
          c.days + ' days from the ' + ymdS(c.bottom) + ' bottom: ' + cqB(c.add_b) + ' in, price ' + fmt.n(c.mult, 2) + '×. Past cycles on the same day: ' + sm.map(function (r) { return 'the ' + r.bottom.slice(0, 4) + ' cycle ' + cqB(r.same.add_b) + ', ' + fmt.n(r.same.mult, 2) + '×'; }).join('; ') + '.' + (more && less ? ' More money in than past cycles at this point, yet a smaller gain.' : '')), 'neu']);
    }
    it.push([_T('每 1 美元帶動市值', 'Market cap per $1 in'), '$' + fmt.n(cy[cy.length - 1].lev, 1),
      _T('到頂部時，每流入 1 美元，市值增加 ' + cy.map(function (r) { return '$' + fmt.n(r.lev, 1); }).join(sep) + '。這一輪剛起步、流入的錢還少，這個比值要到週期後段才有比較的意義。', 'By the top, each $1 of inflow added ' + cy.map(function (r) { return '$' + fmt.n(r.lev, 1); }).join(sep) + ' of market cap. This cycle is young and inflows are small, so the ratio only means something later in the cycle.'), 'neu']);
    return it;
  }
  function ceHtml(x) {
    var cy = x.cycles || [], c = x.cur, all = cy.concat(c ? [c] : []);
    var ma = Math.log10(1 + Math.max.apply(null, all.map(function (r) { return Math.max(0, r.add_b); }))), mm = Math.log10(Math.max.apply(null, all.map(function (r) { return r.mult; })));
    var bar = function (w, col, lab) { return '<div class="ce-bar"><span class="tr"><i style="width:' + Math.max(1.5, Math.min(100, w * 100)).toFixed(1) + '%;background:' + col + '"></i></span><span class="num">' + lab + '</span></div>'; };
    var row = function (r, now) { return '<tr' + (now ? ' class="ce-now"' : '') + '><td><b>' + oxYm(r.bottom) + ' → ' + (now ? _T('現在', 'now') : oxYm(r.top)) + '</b><div class="note">' + fmt.n(r.days, 0) + _T(' 天', ' days') + '</div></td><td>' + bar(Math.log10(1 + Math.max(0, r.add_b)) / ma, 'var(--s3)', cqB(r.add_b).replace('+', '')) + '</td><td>' + bar(Math.log10(Math.max(1, r.mult)) / mm, 'var(--s4)', fmt.n(r.mult, r.mult < 10 ? 2 : 0) + '×') + '</td><td class="num">' + (now || r.lev == null ? '—' : '$' + fmt.n(r.lev, 1)) + '</td></tr>'; };
    return '<div class="tbl-wrap"><table class="tbl ce-tbl"><colgroup><col style="width:22%"><col style="width:31%"><col style="width:31%"><col style="width:16%"></colgroup><thead><tr><th>' + _T('底部 → 頂部', 'Bottom → top') + '</th><th>' + _T('流入資金（實現市值增加）', 'Money in (realized cap added)') + '</th><th>' + _T('價格倍數', 'Price multiple') + '</th><th class="num">' + _T('每 1 美元帶動市值', 'Market cap per $1 in') + '</th></tr></thead><tbody>' +
      cy.map(function (r) { return row(r); }).join('') + (c ? row(c, true) : '') + '</tbody></table></div>';
  }
  function cePanel() {
    var x = (D.onchain || {}).capeff; if (!x || !x.cycles || !x.cycles.length) return '';
    return panel('span-12', _T('每輪資金效率', 'Capital efficiency by cycle'), 'CoinMetrics · ' + fmt.md(x.date),
      interpHtml(ceSay()) + '<div id="c-capeff">' + ceHtml(x) + '</div><p class="note">' + _T('實現市值＝每顆幣以最後一次移動時的價格計價的總和，它的增加就是真正流進來的資金（市值 ÷ MVRV，CoinMetrics）。每一輪從熊市底部算到週期頂部；長條是對數長度。「每 1 美元帶動市值」＝市值增加 ÷ 實現市值增加。底部與頂部日期沿用本站週期模型。只作讀值。',
        'Realized cap = every coin valued at the price it last moved; its increase is the money that actually came in (market cap ÷ MVRV, CoinMetrics). Each cycle runs from the bear-market bottom to the cycle top; bar lengths are logarithmic. "Market cap per $1 in" = market cap added ÷ realized cap added. Bottom and top dates follow this site\'s cycle model. Reading only.') + '</p>', '', 'capeff');
  }

  (function () {   /* 六項新圖的「怎麼讀這張圖」 */
    var hh = function (a, b, cz, ce, dz, de) { return [[a, b], [cz, ce], [dz, de]]; }, fl = function (k) { return (D.flows || {})[k] || {}; }, oc = function (k) { return (D.onchain || {})[k] || {}; };
    Object.assign(RD, {
      'exflow': { h: hh('下格是交易所淨流量的 30 天合計：綠＝淨流出（幣離開交易所）、紅＝淨流入。綠底是強流出（近 4 年最低 10%），紅底是強流入（最高 10%）。', 'Bottom: 30-day exchange netflow, green = net outflow (coins leaving exchanges), red = net inflow. Green shading marks strong outflows (4-year bottom 10%), red shading strong inflows (top 10%).',
          '長時間淨流出＝買了提走、放進冷錢包的人多，可賣的籌碼變少；大量淨流入＝有人把幣送上交易所，可能準備賣。但回測看，單靠流量的方向分不出之後漲跌。', 'Sustained outflows = more coins being withdrawn to cold storage, less supply on hand to sell; big inflows = coins sent to exchanges, possibly to sell. Backtests show flow direction alone does not separate what comes next.',
          '交易所地址是推算的、會事後修正；ETF 託管、交易所內部整理錢包都會造成大筆流動，單日尖峰常不是買賣。', 'Exchange addresses are estimated and revised; ETF custody and exchange wallet reshuffles cause big moves, so one-day spikes are often not trades.'),
        now: function () { var x = fl('exflow'); return x.s30 == null ? '' : _T('30 天合計 ' + cqBtc(x.s30) + ' 顆（近 4 年第 ' + fmt.n(x.pct4, 0) + ' 百分位）。', '30-day sum ' + cqBtc(x.s30) + ' BTC (' + fmt.n(x.pct4, 0) + 'th percentile of 4 years).'); } },
      'dmd': { h: hh('下格兩條線：青綠是現貨需求（表觀需求 30 天）、橘是永續需求（OKX 合約 30 天主動買 − 賣），各自除以近一年最大值，0 以上＝在買、以下＝在減。膠囊是現貨需求轉正的日子與之後 60 天的漲跌。', 'Two lines below: teal is spot demand (30-day apparent demand), orange perpetual demand (OKX contracts 30-day taker buy − sell), each divided by its own 1-year max; above 0 = buying, below = pulling back. Capsules mark days spot demand turned positive and the next 60 days.',
          '兩條一起在 0 以上最扎實；現貨在 0 以上、永續在 0 以下，是現貨在接、槓桿在退；永續在上、現貨在下，是槓桿推的行情，比較容易回吐。', 'Both above 0 is the sturdiest; spot above and perps below means spot absorbing while leverage retreats; perps above with spot below is a leverage-driven move that gives back more easily.',
          '現貨是推算的鏈上需求（逐筆 UTXO），永續只有 OKX 一家、而且只有半年多的資料，比較的是方向，不是誰大誰小。', 'Spot is an estimated on-chain demand (per UTXO) and perps are OKX only with about half a year of data; compare direction, not size.'),
        now: function () { var x = oc('dmd'); return x.spot == null ? '' : _T('現貨 ' + cqBtc(x.spot) + ' 顆、永續 ' + cqB((x.perp || 0) / 1000) + '。', 'Spot ' + cqBtc(x.spot) + ' BTC, perps ' + cqB((x.perp || 0) / 1000) + '.'); } },
      'etfcost': { h: hh('上格紫線是 ETF 持有者的平均成本（推算，不含 GBTC）；下格是價格相對這條成本的百分比，綠＝價格在成本之上、紅＝之下。', 'Top: the purple line is the estimated average ETF holder cost (ex-GBTC). Bottom: price versus that cost in percent, green = above cost, red = below.',
          '價格跌破成本＝ETF 買家平均帳面虧損，這時候還在流出代表有人認賠離場；能在成本附近止跌、流量轉正，代表這群買家守得住。', 'Price below cost = ETF buyers are underwater on average; continued outflows then mean some are cutting losses. Holding near cost with flows turning positive means this group is holding the line.',
          '成本是用每天流量和收盤推算的，不是實際成交價；GBTC 不算在內，ETF 只是現貨需求的一部分。', 'The cost is estimated from daily flows and closes, not actual fills; GBTC is excluded, and ETFs are only part of spot demand.'),
        now: function () { var x = fl('etfcost'); return x.cost == null ? '' : _T('成本 ' + fmt.usd(x.cost) + '，現價' + fmt.pct(x.gap_now, 1) + '。', 'Cost ' + fmt.usd(x.cost) + ', price ' + fmt.pct(x.gap_now, 1) + '.'); } },
      'npl365': { h: hh('下格是近 365 天淨實現損益的合計，換成顆數：綠＝一年內整體獲利了結、紅＝整體認賠。膠囊是歷次頂部前後的最高與熊市底部前後的最深。', 'Bottom: the past 365 days of net realized profit/loss in coins, green = net profit-taking over the year, red = net loss-taking. Capsules mark the highs around tops and the lows around bear-market bottoms.',
          '過去熊市底部都出現在這條線很深的負值附近：一年裡大量的幣被賠錢賣出、籌碼換到新買家手上。翻回正值，通常代表最難熬的認賠期結束。', 'Past bear-market bottoms came near deep negative readings: a year of heavy loss-selling that moved coins to new hands. Turning back positive usually marks the end of the hardest loss-taking.',
          '這一輪的負值比前幾輪淺很多，可能是持有結構改變，也可能是還沒走完；以顆計可跨時代比，但交易所整理錢包也會被算成實現損益。', 'This cycle\'s reading is far shallower than past ones — a changed holder base, or not finished yet. Counting in coins compares across eras, but exchange wallet reshuffles also register as realized P/L.'),
        now: function () { var x = oc('npl365'); return x.value == null ? '' : _T('近一年 ' + cqKb(x.value) + ' 顆。', 'Past year ' + cqKb(x.value) + ' BTC.'); } },
      'sthd': { h: hh('下格是短期持有者供給和 90 天前的差，橘＝增加（90 天內被移動、變成短期持有的幣比轉成長期的多）、青綠＝減少（幣在沉澱）。膠囊是每輪頂部前後的最大值。', 'Bottom: short-term holder supply minus its level 90 days earlier; orange = rising (more coins moved into short-term hands than aged into long-term), teal = falling (coins settling). Capsules mark the largest reading around each top.',
          '大幅為正＝大量舊幣換手，常見於牛市後段長期持有者分發、或恐慌時舊幣被賣出；轉負＝新買的幣放著不動，籌碼在沉澱。', 'Strongly positive = heavy turnover of old coins, typical of late-bull distribution by long-term holders or of old coins sold in a panic; turning negative = newly bought coins sitting still as supply settles.',
          '量的是幣有沒有被移動，不是誰在買；交易所和託管整理錢包也會算進去。翻正翻負後 90 天的漲跌和任一天差不多，不是買賣訊號。', 'It counts coin movement, not who is buying; exchange and custody reshuffles are included. Returns 90 days after a flip look like any other day, so a flip is not a trading signal.'),
        now: function () { var x = oc('sthd'); return x.value == null ? '' : _T('90 天 ' + cqKb(x.value / 1e3) + ' 顆。', '90-day ' + cqKb(x.value / 1e3) + ' BTC.'); } },
      'kp': { h: hh('下格是韓國溢價：粗線是 7 日平均（綠＝溢價、紅＝折價），細灰線是每日；琥珀色虛線是 5%。縱軸壓縮過，小數值看得清楚、大數值不會頂出去。', 'Bottom: the Korea premium; the thick line is the 7-day average (green = premium, red = discount), the thin grey line daily; the amber dashed line is 5%. The axis is compressed so small values stay legible and big spikes stay in frame.',
          '溢價衝高＝韓國散戶搶著買、願意付更多韓元，過去常在局部高點附近；折價＝韓國買盤冷，常在恐慌或熊市。', 'A spiking premium = Korean retail scrambling to buy and paying up in won, historically near local highs; a discount = cold Korean demand, often in panics or bear markets.',
          '只看 Upbit 一家；韓國有資本管制，溢價會長期存在，1–2% 的常態溢價不代表過熱。', 'Upbit only; capital controls let a premium persist, so a steady 1–2% does not mean overheating.'),
        now: function () { var x = fl('kp'); return x.a7 == null ? '' : _T('7 日平均 ' + fmt.pct(x.a7, 2) + '。', '7-day average ' + fmt.pct(x.a7, 2) + '.'); } },
      'capeff': { h: hh('每一列是一輪週期，從熊市底部到頂部：青綠是流進來的資金（實現市值增加）、金色是價格倍數，長條用對數長度；最後一列是這一輪到現在。', 'Each row is one cycle from bear-market bottom to top: teal is the money that came in (realized cap added), gold the price multiple, with logarithmic bar lengths; the last row is this cycle so far.',
          '比特幣越大，推動同樣的漲幅要越多錢：流入一輪比一輪多，倍數一輪比一輪小。拿這一輪和前幾輪同一天比，可以看資金進來的速度與價格的反應。', 'The bigger bitcoin gets, the more money the same gain needs: inflows grow each cycle while multiples shrink. Comparing this cycle with past ones on the same day shows how fast money arrives and how price responds.',
          '底部與頂部日期沿用本站的週期模型；實現市值逐筆 UTXO 計算，交易所整理錢包、遺失的幣都會影響，看的是數量級。', 'Bottom and top dates follow this site\'s cycle model; realized cap is per UTXO and affected by exchange reshuffles and lost coins, so read it for orders of magnitude.'),
        now: function () { var c = oc('capeff').cur; return !c ? '' : _T('這一輪 ' + c.days + ' 天：流入 ' + cqB(c.add_b) + '、' + fmt.n(c.mult, 2) + ' 倍。', 'This cycle, ' + c.days + ' days: ' + cqB(c.add_b) + ' in, ' + fmt.n(c.mult, 2) + '×.'); } }
    });
  })();
  Object.assign(RD, {   /* 2026-11-08 隱含波動率期限結構、月度報酬熱力表 */
    'ivt': { h: [['每條線是一天收盤後的快照：橫軸是距離到期的天數（越往右越遠，刻度前密後疏），縱軸是那個到期日的價平隱含波動。金線是今天，虛線是 7 天前、點線是 30 天前（存夠天數才會出現）。', 'Each line is a snapshot after a daily close: across is days to expiry (further right is further out, spaced tighter at the far end), up is the at-the-money implied volatility for that expiry. Gold is today; dashed is a week ago and dotted 30 days ago (they appear once enough days are saved).'],
        ['正常是往右上升（遠月較貴）。左端翹起、近月比遠月貴就是倒掛（淡色底），代表市場覺得眼前幾天的風險比較大，常見於急跌、清算潮或大事件前後。', 'Normally the line rises to the right (longer dated costs more). When the left end lifts above the far end it is inverted (shaded): the market sees more risk in the next few days, as is common around sharp drops, liquidation waves or big events.'],
        ['隱含波動是從選擇權價格反推的預期波動幅度，不分漲跌。Deribit 沒有免費的歷史曲線，本站 2026/11/07 起每天存一條。只作讀值。', 'Implied volatility is the expected size of moves backed out of option prices, not their direction. Deribit offers no free history of the curve, so the site has saved one daily since 2026/11/07. Reading only.']],
      now: function () { var x = ivtX(); return !x || !x.t ? '' : _T('7 天 ' + fmt.n(x.t[7], 1) + '%、90 天 ' + fmt.n(x.t[90], 1) + '%，相差 ' + ivtSg(x.slope) + ' 點（' + (IVT_K[x.state] || IVT_K.flat)[1] + '）。', '7 days ' + fmt.n(x.t[7], 1) + '%, 90 days ' + fmt.n(x.t[90], 1) + '%, a gap of ' + ivtSg(x.slope) + ' pt (' + (IVT_K[x.state] || IVT_K.flat)[3].toLowerCase() + ').'); } },
    'mon': { h: [['每格是一個月的漲跌：上個月最後一天收盤到這個月最後一天收盤。綠漲紅跌，顏色越深幅度越大；框起來的是本月，到最新收盤為止。', 'Each cell is one month: from the last close of the previous month to the last close of this one. Green up, red down, darker for bigger moves; the outlined cell is this month, up to the latest close.'],
        ['最下面兩列是各月的中位數和上漲比例（2013 年起、不含本月）。用中位數是因為 2013 年 3 月、11 月都漲超過一倍，會把平均拉得很高。', 'The bottom two rows are each month’s median and share of up months (since 2013, excluding this month). Medians, because March and November 2013 each more than doubled and would drag an average far up.'],
        ['每個月只有十幾個樣本，季節性只描述過去，不代表今年會照走；拿來看「這個月目前算不算特別」比拿來預測合適。只作讀值。', 'Each month has only a dozen or so cases. Seasonality describes the past, not what this year will do; it is better for judging whether this month is unusual so far than for forecasting. Reading only.']],
      now: function () { var x = monX(); if (!x || x.mtd == null) return ''; var c = x.cur || {}; return _T(c.m + ' 月至今 ' + fmt.pct(x.mtd, 1) + '；過去 ' + c.n + ' 次 ' + c.m + ' 月上漲 ' + c.up + ' 次、中位數 ' + fmt.pct(c.med, 1) + '。', MON_EN[c.m - 1] + ' so far ' + fmt.pct(x.mtd, 1) + '; of the past ' + c.n + ' ' + MON_EN[c.m - 1] + 's, ' + c.up + ' rose, median ' + fmt.pct(c.med, 1) + '.'); } }
  });
  Object.assign(RD, {   /* 2026-11-07 賣壓累積與動能品質 */
    'sx': { h: [['下格紅線是賣壓累積（0–100），青綠線是動能品質（0–1，畫在同一高度，0.3 對到 30）。青綠底是「底部組合」出現到賣壓回到 0 的那一段，膠囊是組合出現後 90 天的漲跌。', 'Bottom: the red line is selling pressure (0–100), the teal line momentum quality (0–1, drawn on the same height, 0.3 at 30). Teal shading runs from each bottom combo to when pressure returns to 0; capsules show the next 90 days.'],
        ['動能品質看近 21 天漲跌是不是又快又穩；賣壓累積看弱勢拖了多久：急跌一兩天不會馬上到 100，要弱勢拖一段時間才會累積上去，一段又快又穩的上漲就清空。兩個一起到極端（賣壓 100、動能 < 0.3）時，過去常在一段下跌的後段，但短期常常還有一跌。', 'Momentum quality asks whether the last 21 days moved fast and steadily; selling pressure asks how long weakness has dragged on. A one- or two-day drop does not push it to 100 — weakness has to linger — and a fast, steady rally clears it. When both hit extremes (pressure 100, momentum < 0.3), it has tended to come late in a decline, though often with another leg down first.'],
        ['只用價格，不看鏈上；回測二十幾次，熊市初期多次失靈。動能高不是頂部訊號：過去多半是行情延續。', 'Price only, no on-chain data; about twenty cases, and it failed repeatedly early in bear markets. High momentum is not a top signal: it usually meant continuation.']],
      now: function () { var x = sxX(); return !x || x.r == null ? '' : _T('賣壓 ' + x.r + '、動能 ' + fmt.n(x.s, 2) + '。', 'Pressure ' + x.r + ', momentum ' + fmt.n(x.s, 2) + '.'); } }
  });

  V.onchain = function () {
    var oc = D.onchain, m = oc.metrics || {}, tr = oc.top_radar || {}, ch = D.chips, fl = ch.flow || {}, u = ch.urpd || {}, mi = oc.mining || {}, ex = oc.exchange || {};
    var rows = [
      // 2026-11-04：MVRV Z／NUPL／Puell 只在週期版「頂部三指標」（同一份 CoinMetrics 資料），這張表不再重複
      ['aSOPR', 'asopr', _T('賣出時的獲利倍數（排除一小時內轉手），>1 平均獲利', 'Profit multiple on coins sold (excluding coins moved within an hour); >1 = sold at a profit on average')], ['STH-SOPR', 'sth-sopr', _t('短期持有者的 SOPR')], ['LTH-SOPR', 'lth-sopr', _t('長期持有者的 SOPR')],
      [_t('非流動性供給'), 'illiquid-supply', _t('長期不動的幣')], [_t('高流動性供給'), 'highly-liquid-supply', _t('浮動籌碼')]
    ].map(function (r) { return [r[0], m[r[1]], r[2], r[1]]; }).filter(function (r) { return r[1]; });
    var t = _t('<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:46%"><col style="width:20%"><col style="width:34%"></colgroup><thead><tr><th>指標</th><th class="num">讀值</th><th>四年百分位</th></tr></thead><tbody>') + rows.map(function (r) { var v = r[1], big = Math.abs(v.value) > 1e5, rd = OC_READ[r[3]] ? OC_READ[r[3]](v) : null; return '<tr' + (rd ? ' class="has-rd"' : '') + '><td><b>' + r[0] + '</b><div class="note">' + esc(r[2]) + ' · ' + fmt.md(v.date) + '</div></td><td class="num">' + (big ? fmt.n(v.value / 1e6, 2) + 'M' : fmt.n(v.value, 3)) + '</td><td>' + (v.pct_4y == null ? '—' : '<div class="pct"><i><b class="' + (v.pct_4y >= 80 ? 'hot' : '') + '" style="width:' + v.pct_4y + '%"></b></i><span class="num">' + fmt.n(v.pct_4y, 0) + '</span></div>') + '</td></tr>' + rdRow(rd, 3); }).join('') + '</tbody></table></div>';
    return readBar('onchain') + '<div class="kpis">' + kpi(_t('短期持有者獲利比例'), fmt.n((fl.sth_in_profit_pct || {}).value, 1) + '%', _t('7 天前 ') + fmt.n((fl.sth_in_profit_pct || {}).d7, 1) + '%', (fl.sth_in_profit_pct || {}).value) + kpi(_t('短期持有者成本'), fmt.usd((fl.sth_vs_tmm || {}).sth_cost), _t('真實市場均價 ') + fmt.usd((fl.sth_vs_tmm || {}).tmm)) + kpi(_t('交易所供給'), fmt.n(ex.exchange_supply_share_pct, 2) + '%', _t('7 日 ') + fmt.pct(ex.exchange_supply_chg7_pct, 2) + _t(' · 90 日 ') + fmt.pct(ex.exchange_supply_chg90_pct, 2)) + kpi(_t('算力 7 日均'), fmt.n(mi.hash7, 0) + ' EH/s', _t('週 ') + fmt.pct(mi.wk_chg_pct, 1) + ' · hashprice $' + fmt.n(mi.hashprice, 1)) + kpi(_t('下次難度調整'), fmt.pct(mi.diff_next_pct, 1), fmt.md(mi.retarget) + _t(' · 進度 ') + fmt.n(mi.diff_progress, 0) + '%', mi.diff_progress) + '</div><div class="grid">' + interpPanel(ocInterp()) +
      grpH('oc-cost', '成本與位置', 'Cost and position', _T('價格相對各群人的成本在哪裡', 'Where price sits against each group\'s cost')) +
      pbPanel() + qPanel() +
      panel('span-5', _t('籌碼分布（URPD）'), fmt.md(u.date) + _t(' · 每 2,000 美元一格'), urpdSay(u) + urpdGapSay() + '<div id="c-urpd"></div>') +
      panel('span-7', _t('短期持有者獲利比例'), _t('2025 頂部 ') + fmt.n((ch.viz || {}).top_vals ? ch.viz.top_vals.profit : null, 1) + '%', interpHtml(sthlSay()) + '<div class="chart" id="c-profit"></div><p class="note">' + _T('短期持有者成本與真實市場均價的走勢在週期版「市場階段」的佐證圖 ', 'Short-term holder cost vs the true market mean is charted with the market-stage evidence on the Cycle page ') + jumpA('cycle', 'ev-tmm', _T('看圖 →', 'See chart →')) + '</p>') +
      sbPanel() + acPanel() + concPanel() +   // 2026-11-08 內容重組：籌碼集中度從衍生品版搬來；需求四張搬到資金版
      grpH('oc-pnl', '賣出的人賺還是賠', 'Are sellers in profit or at a loss', _T('短期持有者和全市場賣出時是獲利還是認賠', 'Whether short-term holders, and the market as a whole, sell at a profit or a loss')) +
      soprPanel() + confPanel() + sthPnlPanel() + nplPanel() + n365Panel() +
      grpH('oc-sell', '賣壓強弱與衰竭', 'Selling pressure and exhaustion', _T('賣壓在加大還是快耗盡', 'Is selling building up or running dry')) +
      rplPanel() + rlPanel() + ssrPanel() + secPanel() + moPanel() +
      grpH('oc-lth', '長期持有者與大戶', 'Long-term holders and whales', _T('長期持有者和大戶在加碼、出貨還是認賠', 'Are long-term holders and whales adding, distributing or selling at a loss')) +
      cohortPanel() + lthColorPanel() + lcPanel() + sthdPanel() + agePanel() + dmPanel() + lthLossPanel() + whalePanel() +
      grpH('oc-all', '指標總表', 'All metrics') + panel('span-12', _t('鏈上指標'), _T('STH-SOPR：CheckOnChain · 長短期成本、aSOPR、LTH-SOPR：Bitview · 其他：bitcoin-data', 'STH-SOPR: CheckOnChain · holder costs, aSOPR, LTH-SOPR: Bitview · others: bitcoin-data'), t + '<p class="note">' + _T('MVRV Z、NUPL、Puell 在週期版「頂部三指標」', 'MVRV Z, NUPL and Puell are on the Cycle page under the top-3 indicators ') + jumpA('cycle', 'p6', '→') + '</p>') + ocPanel() + '</div>';
  };
  V.onchain.after = function () {
    mount($('#c-agecost'), drawAgeCost); var acs = $('#ac-segs'); if (acs) acs.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b || b.getAttribute('data-a') === acMode) return; acMode = b.getAttribute('data-a'); acs.querySelectorAll('button').forEach(function (q) { q.setAttribute('aria-pressed', q === b); }); $('#ac-say').innerHTML = interpHtml(acSayNow()); $('#ac-lg').innerHTML = acLegend(); drawAgeCost($('#c-agecost')); });   // 2026-11-06 持幣成本從週期版搬來
    mount($('#c-conc'), drawConc);   // 2026-11-08 從衍生品版搬來
    mount($('#c-whale'), drawWhale); safe(drawSopr, drawSthPnl, function () { drawOc(false); }); mount($('#c-npl'), drawNpl); mount($('#c-conf'), drawConf); safe(cohortAfter); mount($('#c-lthc'), drawLthColor); mount($('#c-lthloss'), drawLthLoss); mount($('#c-lthrl'), drawLthRl); mount($('#c-sthband'), drawSthBand); mount($('#c-quant'), drawQuant); mount($('#c-rloss'), drawRl); mount($('#c-lsrchg'), drawLc); mount($('#c-mom'), drawMo); mount($('#c-ssr'), drawSsr); mount($('#c-agepl'), drawAge); mount($('#c-dorm'), drawDorm); mount($('#c-sec'), drawSec); mount($('#c-rpl'), drawRpl); mount($('#c-npl365'), drawN365); mount($('#c-sthd'), drawSthd);   /* 2026-11-06 指標擴充的 mount 接在前面；註解只能放行尾（之前插在行中把後面三張圖註解掉了） */
    var ags = $('#ag-seg'); if (ags) ags.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b || b.getAttribute('data-m') === agMode) return; agMode = b.getAttribute('data-m'); ags.querySelectorAll('button').forEach(function (q) { q.setAttribute('aria-pressed', q === b); }); drawAge($('#c-agepl')); });   /* 2026-11-06 實現獲利／虧損切換 */
    var rs = $('#rl-seg'); if (rs) rs.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b || b.getAttribute('data-m') === rlMode) return; rlMode = b.getAttribute('data-m'); rs.querySelectorAll('button').forEach(function (q) { q.setAttribute('aria-pressed', q === b); }); drawRl($('#c-rloss')); });   /* 2026-11-06 實現虧損 近 150 天／全部歷史 */
    var ns = $('#npl-segs'); if (ns) ns.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; var m = b.getAttribute('data-m'); if (m) { if (m === nplMode) return; nplMode = m; nplRng = m === 'cum' ? 1460 : 180; } else nplRng = +b.getAttribute('data-v'); nplSync(); });
    var v = D.chips.viz || {}, u = v.urpd || {}, c = D.price.bar.c, el = $('#c-urpd');
    if (el && u.band) {
      var pv = {}; ((u.prev7 || {}).band || []).forEach(function (b) { pv[b[0]] = b[1]; });
      var rows = u.band.filter(function (b) { return b[0] >= c * 0.62 && b[0] <= c * 1.4; }).slice().reverse().map(function (b) { var cur = c >= b[0] && c < b[0] + (u.width || 2000); return { label: fmt.k(b[0]), v: b[1], color: cur ? 'var(--flare)' : 'var(--s1)', cls: cur ? 'cur' : '', right: _T(fmt.n(b[1] / 1e4, 1) + '萬', fmt.n(b[1] / 1e3, 0) + 'K'), prev: pv[b[0]], tip: '<div class="t">' + fmt.usd(b[0]) + '–' + fmt.usd(b[0] + (u.width || 2000)) + _t('</div><div class="r"><i style="background:var(--s1)"></i><span>籌碼</span><b>') + fmt.n(b[1]) + _t(' 顆</b></div>') + (pv[b[0]] != null ? _t('<div class="r"><i></i><span>7 天前</span><b>') + fmt.n(pv[b[0]]) + '</b></div>' : '') }; });
      el.innerHTML = ladderHtml(rows, { dense: true }); bindLadder(el, rows);
    }
    mount($('#c-profit'), drawProfitK);
  };

  /* 掛單簿摘要（2026-10-12 由獨立版面縮成衍生品版的一張卡）：快照在 UTC 00:05、掛單隨時可撤，只留買賣比與最大的牆 */
  function bookCard() {
    var o = D.orderbook; if (!o) return '';
    var w = o.walls || {}, t = o.totals || {}, rd = o.rounds || {};
    var walls = function (arr, col) { return (arr || []).slice(0, 5).map(function (x) { return '<div class="event"><span class="d">' + fmt.k(x[0]) + '–' + fmt.k(x[0] + 1000) + '</span><span style="color:var(--ink-2)">' + esc(venue(x[2])) + '</span><span class="num" style="color:' + col + '">$' + fmt.n(x[1], 1) + 'M</span></div>'; }).join(''); };
    return panel('span-12', _T('掛單簿', 'Order book'), _T('13 個交易所 · ±15% · 快照 ', '13 exchanges · ±15% · snapshot ') + (o.ts || '').replace('T', ' ').slice(5, 16) + ' UTC',
      interpHtml(bkInterp(o)) + '<div class="grid" style="margin-top:8px">' +
      (o.wide ? '<div class="span-8"><div class="panel-h"><h2>' + _T('全景：每 1,000 美元一格', 'Full view: $1,000 buckets') + '</h2><span class="src">' + _T('7 個整本可得的場所 · ±15%', '7 venues with full books · ±15%') + '</span></div>' + legend([[_t('買單'), 'var(--up)'], [_t('賣單'), 'var(--down)']]) + '<div id="c-book"></div></div>' : '') +
      '<div class="' + (o.wide ? 'span-4' : 'span-12') + '"><div class="panel-h"><h2 style="color:var(--down-ink)">' + _T('上方賣牆', 'Ask walls above') + '</h2><span class="src">' + _T('賣單合計 ', 'total asks ') + '$' + fmt.n(t.wide_ask, 0) + 'M</span></div><div class="events">' + walls(w.ask, 'var(--down)') + '</div>' +
      '<div class="panel-h" style="margin-top:8px"><h2 style="color:var(--up)">' + _T('下方買牆', 'Bid walls below') + '</h2><span class="src">' + _T('買單合計 ', 'total bids ') + '$' + fmt.n(t.wide_bid, 0) + 'M</span></div><div class="events">' + walls(w.bid, 'var(--up)') + '</div>' +
      _t('<div class="panel-h" style="margin-top:8px"><h2>整數關卡</h2></div><div class="events">') + Object.keys(rd).sort().reverse().map(function (k) { var r = rd[k]; return '<div class="event"><span class="d">' + fmt.usd(+k) + '</span><span style="color:var(--ink-2)">' + (r.side === 'a' ? _t('賣') : _t('買')) + _t('方第 ') + r.rank + _t('／') + r.of + _t(' 名</span><span class="num">$') + fmt.n(r.musd, 1) + 'M</span></div>'; }).join('') + '</div></div></div>' +
      '<p class="note">' + _T('快照時間是 UTC ' + (o.ts || '').slice(11, 16) + '，讀的時候可能已過好幾個小時；掛單隨時可撤，假牆常見。Binance 期貨與 Bybit 讀不到，永續部分偏低估。', 'The snapshot was taken at ' + (o.ts || '').slice(11, 16) + ' UTC and may be hours old by the time you read it; orders can be pulled at any time and fake walls are common. Binance futures and Bybit are not readable, so perpetual depth is understated.') + '</p>');
  }
  function drawBook() {   // 2026-10-12 使用者要求保留原本的掛單簿柱狀圖（每 1,000 美元一格，滑過看各交易所）
    var o = D.orderbook, el = $('#c-book'); if (!o || !el) return;
    var ven = o.wide.venues, lab = function (k) { return venue((o.meta[k] || {}).label || k); };
    var rows = o.wide.rows.map(function (r) { var tot = r[2].reduce(function (a, b) { return a + b; }, 0); return { label: fmt.k(r[0]) + (r[1] === 'a' ? ' ▲' : ' ▼'), v: tot, color: r[1] === 'a' ? 'var(--down)' : 'var(--up)', cls: r[0] === Math.floor(o.mid / 1000) * 1000 ? 'mid' : '', right: '$' + fmt.n(tot, 1) + 'M', tip: '<div class="t">' + fmt.usd(r[0]) + ' · ' + (r[1] === 'a' ? _t('賣單') : _t('買單')) + '</div>' + r[2].map(function (v, i) { return v >= 0.5 ? '<div class="r"><i style="background:' + (r[1] === 'a' ? 'var(--down)' : 'var(--up)') + '"></i><span>' + esc(lab(ven[i])) + '</span><b>$' + fmt.n(v, 1) + 'M</b></div>' : ''; }).join('') }; });
    el.innerHTML = ladderHtml(rows, { dense: true }); bindLadder(el, rows);
  }


  V.exit = function () {
    var F = D.exit.framework, S = D.exit.status, c = S.close;
    return readBar('exit') + '<div class="grid">' + panel('span-12', _t('現在離每條出場規則多遠'), _t('依當日數值自動產生 · 非投資建議'), interpHtml([rd2(_t('價格階梯'), fmt.k(S.next_step), ladderRead()), rd2(_t('MVRV ÷ 前一輪高點'), fmt.n(S.p20_ratio, 3), p20Read()), rd2(_t('頂部三指標'), ['mvrv_z', 'nupl', 'puell'].map(function (k) { return fmt.n((S.p6 || {})[k], 0); }).join(' / '), p6Read()), rd2(_t('200 日均線避險'), fmt.k(S.sma200), hedgeRead()), [_t('時間停損'), '2029/10', _t('2029/10–2030/03 才適用，現在不作用。'), 'neu']], true)) +
      panel('span-12', _t('出場模擬器'), esc(tx(F, 'unit')), _t('<div class="sim"><div class="sim-ctrl"><label for="sim-px">拖動看看：如果收盤到這個價位，框架會賣出多少？</label><span class="big" id="sim-v">') + fmt.usd(c) + '</span><input type="range" id="sim-px" min="60000" max="240000" step="1000" value="' + Math.round(c / 1000) * 1000 + '"><div class="legend"><span>60K</span><span style="margin-left:auto">240K</span></div><div class="stair" id="sim-stair"></div></div><div class="donut-wrap" id="sim-donut"></div></div>', '', 'sim') +
      panel('span-6', _t('鏈上觸發'), _t('MVRV ÷ 前一輪高點'), '<div class="rules">' + F.onchain.map(function (r) { var run = r.id === 'p20a' ? S.p20_run_075 : r.id === 'p20b' ? S.p20_run_080 : null; return '<div class="rule"><span class="t">' + (r.k ? _t('比值 ≥ ') + r.k : _t('新高背離')) + '</span><span class="d">' + esc(tx(r, 'rule')) + '</span><span class="chip">' + (run != null ? run + _t(' / 5 天') : _t('未啟用')) + '</span></div>'; }).join('') + _t('</div><p class="note">現在比值 ') + fmt.n(S.p20_ratio, 3) + _t('；0.75 約對應 ') + fmt.usd(S.k075_price) + _t('、0.80 約 ') + fmt.usd(S.k080_price) + _t('（隨實現價每天移動）。</p>')) +
      panel('span-6', _t('其他規則'), '', _t('<div class="rules"><div class="rule"><span class="t">200 日均線避險</span><span class="d">') + esc(tx(F.hedge, 'rule')) + '</span><span class="chip">' + S.below_sma200_run + _t(' / 5 天</span></div><div class="rule"><span class="t">頂部三指標（讀值）</span><span class="d">') + esc(tx(F, 'top3')) + '</span><span class="chip">' + ['mvrv_z', 'nupl', 'puell'].map(function (k) { return fmt.n((S.p6 || {})[k], 0); }).join(_t('／')) + _t('</span></div><div class="rule"><span class="t">時間停損</span><span class="d">') + esc(tx(F, 'time_stop')) + _t('</span><span class="chip">2029/10 起</span></div></div><p class="note">框架是本站對「週期頂部分批出場」的建議做法，只是參考，不是投資建議；每個人的部位與需求不同。</p>')) + '</div>';
  };
  V.exit.after = function () {
    var F = D.exit.framework, inp = $('#sim-px'), S = D.exit.status;
    function upd() {
      var px = +inp.value, hit = F.ladder.filter(function (x) { return px >= x; }).length, sold = hit * F.per_step_pct;
      $('#sim-v').textContent = fmt.usd(px);
      $('#sim-stair').innerHTML = F.ladder.slice().reverse().map(function (x, i) { var on = px >= x; return '<div class="step' + (on ? ' on' : '') + '"><span class="dot"></span><span class="p">' + fmt.usd(x) + _t('</span><span class="d">第 ') + (F.ladder.length - i) + _t(' 階 · 距今 ') + fmt.pct((x / S.close - 1) * 100, 0) + '</span><span class="q">' + (on ? _t('賣 ') : '') + F.per_step_pct + '%</span></div>'; }).join('');
      var R = 78, C = 2 * Math.PI * R, frac = sold / 100;
      $('#sim-donut').innerHTML = _t('<svg viewBox="0 0 200 200" role="img" aria-label="已賣出比例"><circle cx="100" cy="100" r="') + R + '" fill="none" stroke="var(--deck-3)" stroke-width="16"/><circle cx="100" cy="100" r="' + R + '" fill="none" stroke="var(--flare)" stroke-width="16" stroke-dasharray="' + (C * frac).toFixed(1) + ' ' + C.toFixed(1) + '" transform="rotate(-90 100 100)" style="transition:stroke-dasharray .4s var(--ease)"/><text x="100" y="98" text-anchor="middle" style="font-family:var(--f-mono);font-size:34px" fill="var(--ink)">' + sold + _t('%</text><text x="100" y="124" text-anchor="middle" style="font-size:12px" fill="var(--ink-3)">已分批賣出</text></svg><span class="note">價格階梯單獨計算；鏈上觸發會提前賣出、從最高的階往下註銷，總量不變。</span>');
    }
    inp.addEventListener('input', upd); upd();
  };

  /* 往期與戰績（2026-11-04 整體審查）：data/archive/index.json 每天都有封存，網站上一直沒有入口（2026-10-12 決定之後再設計）。
     發現戰績：每則發現的最終狀態取最後一次出現的後續（確認／推翻／到期／追蹤中）；今天這期的後續最新。
     結案少於 30 則時不算命中率（本站原則：樣本少於 30 不下結論）。往期列表：頭條、立場、當天收盤、到現在的漲跌。
     要捲到這一版附近才讀檔（英文版另讀各期的 .en.json 取英文標題） */
  var AR = null;
  function arLoad() {
    if (AR) return AR;
    AR = load('data/archive/index.json').then(function (ix) {
      var E = (ix.editions || []).slice().sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; });
      var wf = E.filter(function (e) { return (e.findings || []).length; });
      var en = LANG === 'en' ? Promise.all(wf.map(function (e) { return load('data/archive/' + e.date + '.en.json').catch(function () { return null; }); })) : Promise.resolve([]);
      return en.then(function (ns) { var T = {}; ns.forEach(function (n) { ((n && n.findings) || []).forEach(function (f) { T[f.id] = f.title; }); }); return { E: E, T: T, asof: ix.as_of }; });
    });
    return AR;
  }
  function arRender() {
    var rec = $('#ar-rec'), lst = $('#ar-list'); if (!rec || rec._done) return; rec._done = 1;
    arLoad().then(function (a) {
      var E = a.E, st = {}, all = [];
      E.forEach(function (e) { (e.findings || []).forEach(function (f) { all.push(Object.assign({ date: e.date }, f)); }); (e.followups || []).forEach(function (f) { if (f.status) st[f.id] = f.status; }); });
      ((N && N.followups) || []).forEach(function (f) { if (f.status) st[f.id] = f.status; });
      var K = ['confirmed', 'refuted', 'expired', 'open'], cnt = { confirmed: 0, refuted: 0, expired: 0, open: 0 };
      all.forEach(function (f) { f.st = FU_ST[st[f.id]] ? st[f.id] : 'open'; cnt[f.st]++; });
      var done = cnt.confirmed + cnt.refuted + cnt.expired, ttl = function (f) { return esc((LANG === 'en' && a.T[f.id]) || f.title || f.id); };
      var stChip = function (k) { var x = FU_ST[k]; return '<span class="chip ' + (k === 'confirmed' ? 'up' : k === 'refuted' ? 'down' : '') + '">' + x[0] + ' ' + _T(x[1], x[2]) + '</span>'; };
      var row = function (f) { var c = CONF[f.confidence] || CONF.medium; return '<tr><td class="ar-d">' + fmt.md(f.date) + '</td><td>' + ttl(f) + '</td><td class="hide-sm">' + _T(c[0], c[1]) + '</td><td class="hide-sm">' + (f.lean ? impChip(f.lean) : '') + '</td><td>' + stChip(f.st) + '</td></tr>'; };
      var head = '<colgroup><col style="width:9%"><col style="width:53%"><col class="hide-sm" style="width:13%"><col class="hide-sm" style="width:11%"><col style="width:14%"></colgroup><thead><tr><th>' + _T('日期', 'Date') + '</th><th>' + _T('發現', 'Finding') + '</th><th class="hide-sm">' + _T('可信度', 'Confidence') + '</th><th class="hide-sm">' + _T('當時判讀', 'Lean') + '</th><th>' + _T('結果', 'Outcome') + '</th></tr></thead>';
      var closed = all.filter(function (f) { return f.st !== 'open'; }).reverse(), open = all.filter(function (f) { return f.st === 'open'; }).reverse();
      rec.innerHTML = !all.length ? '<p class="note">' + _T('還沒有封存的發現。', 'No archived findings yet.') + '</p>' :
        '<div class="ar-sum">' + [[_T('發現', 'Findings'), all.length, '']].concat(K.map(function (k) { return [_T(FU_ST[k][1], FU_ST[k][2]), cnt[k], k]; })).map(function (x) { return '<div><span class="k">' + x[0] + '</span><b class="num ' + (x[2] === 'confirmed' ? 'up' : x[2] === 'refuted' ? 'down' : '') + '">' + x[1] + '</b></div>'; }).join('') + '</div>' +
        '<p class="note">' + (done >= 30 ? _T('已結案 ' + done + ' 則：確認 ' + fmt.n(cnt.confirmed / done * 100, 0) + '%、推翻 ' + fmt.n(cnt.refuted / done * 100, 0) + '%、到期沒有結果 ' + fmt.n(cnt.expired / done * 100, 0) + '%。', done + ' resolved: ' + fmt.n(cnt.confirmed / done * 100, 0) + '% confirmed, ' + fmt.n(cnt.refuted / done * 100, 0) + '% refuted, ' + fmt.n(cnt.expired / done * 100, 0) + '% expired without an outcome.')
          : _T('已結案 ' + done + ' 則，還不到 30 則，先不算命中率（本站原則：樣本少於 30 不下結論）。', done + ' resolved so far — fewer than 30, so no hit rate yet (site rule: no conclusions from fewer than 30 samples).')) +
          _T('每則發現寫下會確認或推翻它的條件與期限，之後每天由資料管線檢查。', ' Each finding states the conditions and deadline that would confirm or refute it; the pipeline checks them daily.') + '</p>' +
        (closed.length ? '<div class="tbl-wrap"><table class="tbl">' + head + '<tbody>' + closed.map(row).join('') + '</tbody></table></div>' : '') +
        (open.length ? '<details class="fu-open"><summary>' + _T('看追蹤中的 ' + open.length + ' 則', 'Show the ' + open.length + ' still being tracked') + '</summary><div class="tbl-wrap"><table class="tbl">' + head + '<tbody>' + open.map(row).join('') + '</tbody></table></div></details>' : '');
      var c = D.price.bar.c;
      lst.innerHTML = '<div class="tbl-wrap"><table class="tbl ar-ed"><colgroup><col style="width:9%"><col style="width:57%"><col class="hide-sm" style="width:15%"><col class="hide-sm" style="width:10%"><col style="width:9%"></colgroup><thead><tr><th>' + _T('日期', 'Date') + '</th><th>' + _T('頭條', 'Headline') + '</th><th class="hide-sm">' + _T('立場', 'Stance') + '</th><th class="num hide-sm">' + _T('當天收盤', 'Close') + '</th><th class="num">' + _T('到今天', 'Since') + '</th></tr></thead><tbody>' +
        E.slice().reverse().map(function (e) { var ch = e.close ? (c / e.close - 1) * 100 : e.chg_since_pct; return '<tr><td class="ar-d">' + e.date.slice(5).replace('-', '/') + '<br><span class="note">No.' + ('00' + e.edition).slice(-3) + '</span></td><td>' + esc((LANG === 'en' && e.headline_en) || e.headline || '') + '</td><td class="hide-sm">' + esc((LANG === 'en' && e.stance_en) || e.stance || '') + '</td><td class="num hide-sm">' + fmt.usd(e.close) + '</td><td class="num"><span style="color:var(--' + (ch >= 0 ? 'up' : 'down') + ')">' + fmt.pct(ch, 1) + '</span></td></tr>'; }).join('') + '</tbody></table></div>' +
        '<p class="note">' + _T('「到今天」＝今天收盤 ' + fmt.usd(c) + ' 相對那一期收盤的漲跌。各期完整內容封存在 data/archive/。', '“Since” = today\'s close of ' + fmt.usd(c) + ' vs that edition\'s close. Full editions are archived in data/archive/.') + '</p>';
    }).catch(function () { rec.innerHTML = '<p class="note">' + _T('往期資料本日未取得。', 'The archive could not be loaded today.') + '</p>'; lst.innerHTML = ''; });
  }
  V.archive = function () {
    return '<div class="grid">' + panel('span-12', _T('發現戰績', 'Findings track record'), _T('2026/10/23 起 · 每期的發現與後續', 'since 2026/10/23 · each edition\'s findings and follow-ups'), '<div id="ar-rec"><p class="note">' + _T('載入中…', 'Loading…') + '</p></div>', '', 'record') +
      panel('span-12', _T('往期', 'Past editions'), _T('每天台北 08:30 一期', 'one edition a day at 08:30 Taipei'), '<div id="ar-list"></div>', '', 'editions') + '</div>';
  };
  V.archive.after = function () {
    var sec = $('#pg-archive'); if (!sec) return;
    if (!window.IntersectionObserver) return arRender();
    var io = new IntersectionObserver(function (es) { if (es.some(function (e) { return e.isIntersecting; })) { io.disconnect(); arRender(); } }, { rootMargin: '800px 0px' });
    io.observe(sec);
  };

  V.method = function () {
    return '<div class="grid">' + panel('span-7', _t('這是什麼'), '', _t('<div class="prose"><p>破曉（Daybreak）是每天清晨的第一份比特幣簡報：先告訴你今天發生了什麼、為什麼重要，再用數據說明市場在週期裡的位置，以及離分批出場還有多遠。</p><p>每天兩段更新：台北 08:20（UTC 00:20）資料管線自動抓取 Kraken、Deribit、CoinMetrics、bitcoin-data、mempool.space、FRED、13 個交易所掛單簿與 Tidemark，算出所有指標；之後由 Claude 查證當天新聞、讀數據，寫成頭條、今日要聞解讀與各版的「今日判讀」。數字全部來自管線，判讀只解釋數字，不改數字。</p>') +
      _t('<h3>原則</h3><p>先給結論再給證據。各版「這些數字代表什麼」與表格下方的解讀，是用當日數值套固定門檻自動產生（門檻寫在句子裡），標籤「偏多／偏空／留意／中性」只描述該數字對價格的一般含意，不是預測，也不連動出場規則。寧可標示「本日未取得」，也不推估或沿用舊數字。不同資料商的數字不相減。分數一律附樣本數，樣本少於 30 不下結論。</p><h3>限制</h3><p>週期模型只有 3–4 輪歷史，所有「遞減」推論都假設趨勢延續。冪律擬合線會隨新資料下修。掛單隨時可撤。短線預測不連動出場規則。bitcoin-data 的部分序列本身晚 5–6 天，頁首「資料狀態」列出每個來源的資料日期與落後天數。</p>') +
      _t('<h3>免責聲明</h3><p>本站內容僅供研究與教育參考，不構成投資建議。加密資產波動極大，請依自身情況判斷並自負風險。</p></div>')) +
      panel('span-5', _t('資料來源'), '', '<div class="events">' + [[_t('價格、均線、ATR'), _t('Kraken 日線（UTC）')], [_t('波動率、基差、選擇權'), _t('Deribit 公開 API')], [_T('MVRV、頂部三指標、交易所供給、冪律', 'MVRV, top-3 indicators, exchange supply, power law'), 'CoinMetrics Community'], [_T('籌碼分布、流動性供給、頂部雷達', 'Supply distribution, liquid supply, top radar'), 'bitcoin-data.com'], ['STH-SOPR', 'CheckOnChain'], [_T('長短期持有者成本、aSOPR、LTH-SOPR、真實市場均價、成本帶、年齡層成本、地址分層、供給分位成本線、相對未實現獲利、全網實現虧損、鏈上勢能', 'Holder costs, aSOPR, LTH-SOPR, true market mean, cost bands, age-band cost, balance tiers, supply quantiles, relative unrealized profit, realized loss, on-chain momentum'), _T('Bitview（Bitcoin Research Kit）', 'Bitview (Bitcoin Research Kit)')], [_T('選擇權逐筆成交（Gamma 曝險推算、買方權利金差）', 'Option trades (gamma exposure estimate, buyer premium)'), _T('Deribit history API', 'Deribit history API')], [_T('現貨主動買賣量', 'Spot taker buy/sell volume'), 'OKX rubik'], [_t('算力、難度'), 'mempool.space'], [_t('相關係數、利率'), 'FRED'], [_t('ETF 流量'), _t('The Block（與 Farside 同口徑）')], [_t('掛單簿'), _t('Coinbase、Bitstamp、Gemini、Bitfinex、Kraken、Binance、OKX、Gate、MEXC、Deribit、Hyperliquid')], [_t('綜合訊號'), _t('Tidemark（north7.github.io）')]].concat(D.onchain.whales ? [[_T('鯨魚分層持幣', 'Holdings by balance tier (whales)'), (D.onchain.whales.src || 'BitInfoCharts')]] : []).map(function (r) { return '<div class="event" style="grid-template-columns:minmax(0,1fr) minmax(0,1.2fr)"><span>' + r[0] + '</span><span style="color:var(--ink-2)">' + r[1] + '</span></div>'; }).join('') + _t('</div><p class="note">資料日 ') + D.meta.bar_date + _t(' · 管線產出 ') + (D.meta.generated_utc || '').replace('T', ' ').slice(0, 16) + _t(' UTC · 結論 ') + (N ? (N.written_utc || '').replace('T', ' ').slice(0, 16) + ' UTC' : '—') + '</p>') + '</div>';
  };

  /* ---------------- 版面 ----------------
     桌面（導航直排）：十個版面依序疊成一頁，只靠捲動就能從頭版看到方法、再捲回來；捲過版面交界時導航、標題與網址跟著切換，
     掃一道換頁線（往下一版由下往上、往上一版由上往下），點導航或按數字鍵跳到該版開頭。
     行動版（導航橫排）：一次只顯示一版（.pg.cur），左右滑或點導航換版，換頁線往下一版由右往左、往上一版由左往右。 */
  var cur = null, seen = {};
  function ids0() { return ROUTES.map(function (r) { return r[0]; }); }
  function stickyH() { var el = MQ.matches ? document.querySelector('.rail') : document.querySelector('.top'); return el ? el.offsetHeight : 0; }
  var GAP = 16;   // 跳轉與換頁頓點時，版面標題上方留白
  function renderAll() {
    var v = $('#view');
    v.innerHTML = ROUTES.map(function (r, i) {
      var mh = r[0] === 'overview' ? '' : '<header class="mod-h"><span class="idx">' + ('0' + (i + 1)).slice(-2) + '</span><h1>' + r[1] + '</h1><p>' + r[2] + ' · ' + fmt.md(D.meta.bar_date) + _t(' 收盤版</p></header>');
      var body; try { body = V[r[0]](); } catch (e) { body = _t('<p class="err">這個模組載入失敗：') + esc(e.message) + '</p>'; console.error(e); }
      return '<section class="pg" id="pg-' + r[0] + '" data-r="' + r[0] + '" aria-label="' + r[1] + '">' + mh + body + '</section>';
    }).join('');
    // 2026-11-04 自我檢查：手機一次只顯示一版，其他版是 display:none——原本載入時 9 版約 50 張圖全畫（寬度 0 先畫成 280px，切過去再重畫一次）。
    //   改成手機只畫目前這一版，切換時才畫，閒置時順手畫左右兩版。
    // 2026-11-09 桌面也延後畫：量到產生 10 版 HTML 共約 80ms，把 10 版的圖畫完約 2 秒（鏈上約 630ms），開頁卡住的是畫圖。
    //   改成開頁只畫到網址指定的那一版（含它上面的版，位置才不會跑）；其餘見 drawUpTo／drawAhead／drawIdle
    try { buildToc(); } catch (e) { console.error(e); }
    try { grpCounts(); buildSubnav(); buildFind(); } catch (e) { console.error(e); }   // 2026-11-08 組圖數、側欄子目錄、搜尋索引
    try { foldGroups(); } catch (e) { console.error(e); }   // 2026-11-09 手機版長頁收合
    if (!MQ.matches) { var h0 = location.hash.slice(1).split('/')[0]; drawUpTo(/^[\w-]+$/.test(h0) && $('#pg-' + h0) ? h0 : ROUTES[0][0]); setTimeout(drawIdle, 1500); }
    void v.offsetWidth; v.classList.add('view-enter');
  }
  /* 2026-11-04 整體審查：長版面加版內目錄（5 個區塊以上的版面，頂端一排可點的區塊名）；每張有圖的區塊標題列加「複製連結」。
     錨點：區塊沒有 id 的，用第一張（沒收起的）圖命名 pn-圖，沒有圖就用 pn-版面-序號 */
  /* 2026-11-06 版面整理：圖表面板裡，圖後面的表格（歷次紀錄、情境表）收成「展開表格」；長的說明只露前兩行，點了展開。
     圖、判讀、看法都不收。頭版、消息、出場、往期、方法版不動 */
  var TIDY_SKIP = { overview: 1, news: 1, exit: 1, archive: 1, method: 1 };
  function tidyPanel(pn) {
    var kids = [].slice.call(pn.children), last = -1;
    kids.forEach(function (el, i) { if (/^c-/.test(el.id) || el.querySelector('[id^="c-"]') && !el.classList.contains('fold')) last = i; });
    if (last < 0) return;
    kids.forEach(function (el, i) {
      if (i > last && el.classList.contains('tbl-wrap')) {
        var n = el.querySelectorAll('tbody tr').length, d = document.createElement('details'); d.className = 'tbl-more';
        d.innerHTML = '<summary>' + _T('展開表格' + (n ? '（' + n + ' 列）' : ''), 'Show table' + (n ? ' (' + n + ' rows)' : '')) + '</summary>';
        el.parentNode.insertBefore(d, el); d.appendChild(el);
      } else if (el.tagName === 'P' && el.classList.contains('note') && el.textContent.length > (LANG === 'en' ? 260 : 120)) {
        el.classList.add('clamp'); el.insertAdjacentHTML('afterend', '<button type="button" class="note-tg" aria-expanded="false">' + _T('展開說明', 'More') + '</button>');
      }
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.note-tg'); if (!b) return;
    var p = b.previousElementSibling, open = !p.classList.contains('open'); p.classList.toggle('open', open);
    b.setAttribute('aria-expanded', open); b.textContent = open ? _T('收起說明', 'Less') : _T('展開說明', 'More');
  });
  function buildToc() {
    document.querySelectorAll('#view .pg').forEach(function (sec) {
      var page = sec.getAttribute('data-r'), pns = [].slice.call(sec.querySelectorAll(':scope > .grid > .panel'));
      if (!TIDY_SKIP[page]) pns.forEach(function (pn) { try { tidyPanel(pn); } catch (e) { console.error(e); } });
      pns.forEach(function (pn, i) {
        var c = [].slice.call(pn.querySelectorAll('[id^="c-"]')).filter(function (e) { return !e.closest('.fold'); })[0], key = c ? c.id.slice(2) : null;
        if (!pn.id) pn.id = 'pn-' + (key && !$('#pn-' + key) ? key : page + '-' + (i + 1));
        var h = pn.querySelector(':scope > .panel-h');
        if (h && (key || pn.id.indexOf('pn-' + page + '-') !== 0) && page !== 'overview') h.insertAdjacentHTML('beforeend', '<button type="button" class="cp-link" data-u="' + page + '/' + (key || pn.id.slice(3)) + '" aria-label="' + _T('複製這一格的連結', 'Copy a link to this section') + '" title="' + _T('複製這一格的連結', 'Copy a link to this section') + '">#</button>');
      });
      if (pns.length < 5 || page === 'overview' || page === 'method') return;
      var link = function (pn) { var t = pn.querySelector(':scope > .panel-h h2'); return t ? '<a href="#' + page + '/' + pn.id.slice(3) + '" data-pn="' + pn.id + '">' + esc(t.textContent.replace(/[（(].*$/, '').trim()) + '</a>' : ''; };
      var gs = [{ h: null, p: [] }];   // 2026-11-06 有分組（.grp-h）的版面：目錄一組一行，組名在前
      sec.querySelectorAll(':scope > .grid > .panel, :scope > .grid > .grp-h').forEach(function (el) { if (el.classList.contains('grp-h')) gs.push({ h: el, p: [] }); else gs[gs.length - 1].p.push(el); });
      var toc = '<nav class="toc' + (gs.length > 1 ? ' grouped' : '') + '" aria-label="' + _T('這一版的區塊', 'Sections on this page') + '">' + gs.map(function (g) {
        if (!g.p.length) return ''; var body = g.p.map(link).join('');
        return gs.length > 1 ? '<div class="toc-g">' + (g.h ? '<a class="g" href="#' + page + '" data-pn="' + g.h.id + '">' + esc(g.h.querySelector('h2').textContent) + '</a>' : '') + body + '</div>' : body; }).join('') + '</nav>';
      var after = sec.querySelector(':scope > .mod-h'); if (after) after.insertAdjacentHTML('afterend', toc);
    });
  }
  /* 2026-11-08 內容重組（使用者：「內容很多，要更合理、更有邏輯、易讀、易定位、易查找，交互更好」）：
     ① 全站搜尋：⌘K／Ctrl+K／「/」或頂部列的搜尋鈕。找圖名、組名、版面名與指標別名（SOPR、ETF、清算、funding…），
        結果寫出在哪一版、哪一組，有「現在」讀值的一併列出；Enter 或點了直接跳到那張圖。沒輸入時列出目前這一版的組與圖（手機的「目錄」鈕也開這個）。
     ② 側欄子目錄（桌面）：目前版面底下列出它的組，捲動時標出現在在哪一組，點了跳過去。
     ③ 頂部列小標跟著捲動顯示目前的組名（手機也是）。④ 組標題加圖數；組也有網址（#版面/組代號）。 */
  var FIND = [], fdAct = -1;
  var FKW = {   // 指標別名：圖代號 → [中文別名, 英文別名]（不顯示，中英都拿來搜）。產品內不寫任何付費指標的名字
    fng: ['恐懼 貪婪 情緒 恐慌', 'fear greed sentiment index'], wiki: ['散戶 關注 熱度 維基 搜尋 瀏覽', 'retail attention wikipedia page views interest'], cot: ['CME 機構 期貨 持倉 CFTC 槓桿基金 資產管理 基差', 'CME institutional futures positioning CFTC COT leveraged funds asset managers basis'],
    conf: ['信心 趨勢 情緒 賣出成本 持有成本 短期持有者 新買家', 'confidence trend sentiment spent cost basis holders spenders short-term new investors'],
    vol: ['隱含波動 實際波動', 'DVOL IV RV implied realized volatility'], basis: ['基差 期貨 資金費率', 'basis futures funding'], ivt: ['期限結構 倒掛', 'IV term structure backwardation contango'],
    liq: ['清算 爆倉 槓桿 熱力圖', 'liquidation heatmap leverage'], lqv: ['每日 多空 清算量 爆倉 多單 空單', 'daily long short liquidations volume'], dawn: ['晨昏 週期 熱度 深夜 破曉 白晝 黃昏 入夜 階段', 'dawn dusk cycle heat stage night daybreak daylight'], fh: ['資金費率 歷史 年化 多方付費', 'funding rate history annualized'], tmh: ['Tidemark 歷史 頂部訊號 底部訊號 熱度 冷度 時機 潮汐', 'Tidemark history top signal bottom signal heat cold timing tide'], oih: ['未平倉 合約 槓桿 OI', 'open interest OI leverage'], lsa: ['多空比 帳戶 散戶 情緒', 'long short ratio accounts retail sentiment'], tk: ['主動買 主動賣 現貨 永續 CVD Coinbase', 'taker buy sell spot perpetual CVD Coinbase'], gex: ['做市商', 'gamma GEX dealer'], prem: ['權利金 買權 賣權 期權', 'premium put call options'], svd: ['主動買 主動賣', 'taker CVD OKX'],
    oi: ['未平倉 到期 期權', 'open interest expiry max pain'], strike: ['履約價 期權', 'strike open interest'], book: ['掛單 買牆 賣牆', 'order book walls'],
    etf: ['流入 流出 貝萊德', 'ETF IBIT inflow outflow'], etfcost: ['成本', 'ETF cost basis'], stab: ['穩定幣', 'stablecoin USDT USDC'], 'pr-us': ['溢價 三地', 'Coinbase premium Asia'],
    kp: ['韓國 泡菜', 'Kimchi Korea Upbit premium'], exflow: ['交易所 流入 流出', 'exchange netflow reserves'], stk: ['美股 那斯達克 黃金', 'Nasdaq S&P gold stocks'], rcliq: ['實現市值', 'realized cap'],
    ad: ['表觀需求', 'apparent demand'], dmd: ['現貨 永續 需求', 'spot perp demand'], capflow: ['投機 長線', 'rotation speculative'], grad: ['梯度', 'gradient'],
    sopr: ['短期持有者', 'STH-SOPR SOPR short-term holder'], sthpnl: ['實現損益', 'realized profit loss STH'], npl: ['淨實現損益', 'net realized profit loss'], sec: ['賣方衰竭', 'seller exhaustion'],
    mom: ['鏈上勢能 銷毀幣天數', 'momentum CDD coin days destroyed'], ssr: ['賣方風險', 'sell-side risk'], rloss: ['實現虧損', 'realized loss divergence'], rpl: ['實現獲利', 'profit loss ratio'],
    cohort: ['長期持有者 短期持有者 籌碼', 'LTH STH long-term short-term holder'], urpd: ['籌碼分布', 'URPD supply distribution'], conc: ['籌碼集中度', 'concentration supply'],
    sthband: ['成本帶', 'STH cost basis bands'], agecost: ['持幣成本', 'cost basis by age'], whale: ['鯨魚 大戶', 'whale'], dorm: ['老幣', 'dormancy liveliness'], lthloss: ['虧損', 'LTH supply in loss'],
    lthc: ['長期持有者 淨部位', 'LTH net position'], sthd: ['短期持有者 供給 90 天 變化 STH 換手', 'STH short-term holder supply 90-day change delta'], sx: ['賣壓 動能', 'momentum selling pressure'], mon: ['月度 季節性 熱力表', 'monthly returns seasonality heatmap'], long: ['長期', 'long-term log price'],
    levels: ['成本線 均線', 'moving average cost basis MA'], cd: ['線 日線', 'candles daily K'], regime: ['多空', 'regime weekly'], pl: ['冪律', 'power law'], aviv: ['真實市場均價', 'AVIV true market mean'],
    rrisk: ['儲備風險', 'reserve risk'], tm: ['', 'Tidemark'], hnupl: ['', 'NUPL'], p20: ['前一輪高點', 'MVRV prior peak'], p6: ['頂部三指標', 'MVRV Z NUPL Puell top']
  };
  function fdTxt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function buildFind() {
    FIND = [];
    document.querySelectorAll('#view .pg').forEach(function (sec) {
      var page = sec.getAttribute('data-r'), r = ROUTES.filter(function (x) { return x[0] === page; })[0] || [page, page, '', '', ''], g = null, n = 0;
      FIND.push({ kind: 'page', t: r[1], sub: r[2], pg: page, pl: r[1], to: page, s: (r[1] + ' ' + r[2] + ' ' + r[4]).toLowerCase() });
      sec.querySelectorAll(':scope > .grid > .panel, :scope > .grid > .grp-h, :scope > .sec-h, :scope > .grid > .sec-h').forEach(function (el) {
        if (el.classList.contains('grp-h')) { g = { t: fdTxt(el.querySelector('h2')), q: fdTxt(el.querySelector('.src')) }; FIND.push({ kind: 'group', t: g.t, sub: g.q, pg: page, pl: r[1], to: page + '/' + el.id.slice(4), s: (g.t + ' ' + g.q).toLowerCase() }); return; }
        if (el.classList.contains('sec-h')) {   // 頭版的大標（我們的看法、訊號總表…）：沒有 id 的補一個
          var st = fdTxt(el.querySelector('h2')); if (!st) return; if (!el.id) el.id = 'sh-' + page + '-' + (++n);
          FIND.push({ kind: 'sec', t: st, pg: page, pl: r[1], to: page + '/' + el.id, s: st.toLowerCase() }); return;
        }
        var h2 = el.querySelector(':scope > .panel-h h2'); if (!h2 || !el.id) return;
        var key = el.id.slice(3), t = fdTxt(h2), c = el.querySelector('[id^="c-"]'), ck = c ? c.id.slice(2) : key;
        FIND.push({ kind: 'panel', t: t, pg: page, pl: r[1], g: g && g.t, to: page + '/' + key, rd: RD[ck] ? ck : RD[key] ? key : null, s: (t + ' ' + (FKW[ck] || FKW[key] || []).join(' ') + ' ' + (g ? g.t : '')).toLowerCase() });
      });
    });
    TERMS.forEach(function (t) { if (!t[2]) return; var e = FIND.filter(function (x) { return x.kind === 'panel' && (x.to.split('/')[1] === t[2] || x.rd === t[2]); })[0]; if (e) e.s += ' ' + (t[0] + ' ' + (t[5] || '')).toLowerCase(); });
  }
  function fdNow(e) { if (!e.rd) return ''; try { return RD[e.rd].now ? RD[e.rd].now() : ''; } catch (er) { return ''; } }
  function fdRank(q) {
    var toks = q.toLowerCase().split(/\s+/).filter(Boolean), out = [];
    FIND.forEach(function (e, i) {
      var sc = 0, tl = e.t.toLowerCase();
      for (var k = 0; k < toks.length; k++) { var w = toks[k], a = tl.indexOf(w); if (a === 0) sc += 30; else if (a > 0) sc += 20; else if (e.s.indexOf(w) >= 0) sc += 8; else return; }
      out.push([sc + (e.kind === 'page' ? 6 : e.kind === 'group' ? 4 : 0), i]);
    });
    return out.sort(function (a, b) { return b[0] - a[0] || a[1] - b[1]; }).slice(0, 40).map(function (x) { return FIND[x[1]]; });
  }
  var FD_K = { page: ['版面', 'Page'], group: ['組', 'Group'], sec: ['區塊', 'Section'], panel: ['圖', 'Chart'] };
  function fdRow(e, i, withNow) {
    var path = e.kind === 'page' ? e.sub : e.pl + (e.g ? ' › ' + e.g : e.kind === 'group' && e.sub ? ' · ' + e.sub : ''), n = withNow ? fdNow(e) : '';
    return '<a class="fd-r k-' + e.kind + '" role="option" id="fd-o' + i + '" href="#' + e.to + '" data-to="' + esc(e.to) + '"><span class="fd-k">' + _T(FD_K[e.kind][0], FD_K[e.kind][1]) + '</span>' +
      '<span class="fd-t">' + esc(e.t) + '</span><span class="fd-p">' + esc(path) + '</span>' + (n ? '<span class="fd-n">' + esc(n) + '</span>' : '') + '</a>';
  }
  function fdRender() {
    var q = $('#fd-q').value.trim(), box = $('#fd-res'), h = '', i = 0;
    if (q) {
      var R = fdRank(q);
      h = R.length ? R.map(function (e, k) { return fdRow(e, i++, k < 12); }).join('') : '<p class="fd-none">' + _T('找不到「' + esc(q) + '」。試試指標名（例如 SOPR、ETF、清算、期限結構）或版面名。', 'Nothing for "' + esc(q) + '". Try an indicator (SOPR, ETF, liquidation, term structure) or a page name.') + '</p>';
    } else {   // 沒輸入：目前這一版的組與圖，再列其他版面
      var mine = FIND.filter(function (e) { return e.pg === cur && e.kind !== 'page'; }), on = (grpNow() || {}).id;
      h = '<div class="fd-h">' + _T('這一版：', 'This page: ') + esc((ROUTES.filter(function (r) { return r[0] === cur; })[0] || [])[1] || '') + '</div>' +
        mine.map(function (e) { return fdRow(e, i++, false).replace('class="fd-r', 'class="fd-r' + (on && e.to === cur + '/' + on.slice(4) ? ' here' : '')); }).join('') +
        '<div class="fd-h">' + _T('所有版面', 'All pages') + '</div>' + FIND.filter(function (e) { return e.kind === 'page' && e.pg !== cur; }).map(function (e) { return fdRow(e, i++, false); }).join('');
    }
    box.innerHTML = h; box.classList.toggle('browse', !q); fdAct = -1; fdMove(q ? 1 : 0, true);
    var here = !q && box.querySelector('.here'); if (here) box.scrollTop = Math.max(0, here.offsetTop - 48); else box.scrollTop = 0;   // 目錄模式：直接捲到目前那一組
  }
  function fdMove(d, reset) {
    var rs = $('#fd-res').querySelectorAll('.fd-r'); if (!rs.length) return;
    if (reset) fdAct = d ? 0 : -1; else fdAct = Math.max(0, Math.min(rs.length - 1, fdAct + d));
    rs.forEach(function (r, i) { r.classList.toggle('act', i === fdAct); r.setAttribute('aria-selected', i === fdAct); });
    if (fdAct >= 0) { rs[fdAct].scrollIntoView({ block: 'nearest' }); $('#fd-q').setAttribute('aria-activedescendant', rs[fdAct].id); }
  }
  var fdBack = null;
  function fdOpen() {
    if (!FIND.length) try { buildFind(); } catch (e) { console.error(e); }
    var fd = $('#fd'); fdBack = document.activeElement; fd.hidden = false; document.documentElement.classList.add('fd-on'); hideTip();
    var q = $('#fd-q'); q.value = ''; fdRender(); setTimeout(function () { q.focus(); }, 30);
  }
  function fdClose() { var fd = $('#fd'); if (!fd || fd.hidden) return; fd.hidden = true; document.documentElement.classList.remove('fd-on'); if (fdBack && fdBack.focus) try { fdBack.focus({ preventScroll: true }); } catch (e) {} }
  function fdGo(to) { fdClose(); if (to) userNav(to, function () { go(to); }); }
  function findShell() {
    var MAG = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/></svg>', mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
    document.body.insertAdjacentHTML('beforeend', '<div class="fd" id="fd" hidden><div class="fd-bg" data-x="1"></div><div class="fd-box" role="dialog" aria-modal="true" aria-label="' + _T('搜尋圖表與指標', 'Search charts and indicators') + '">' +
      '<div class="fd-in">' + MAG + '<input id="fd-q" type="search" autocomplete="off" spellcheck="false" role="combobox" aria-expanded="true" aria-controls="fd-res" placeholder="' + _T('搜尋圖表或指標：SOPR、ETF、清算…', 'Search charts or indicators: SOPR, ETF, liquidation…') + '"><button type="button" class="fd-x" data-x="1" aria-label="' + _T('關閉', 'Close') + '"><span class="kb">Esc</span><span class="tp" aria-hidden="true">✕</span></button></div>' +
      '<div class="fd-res" id="fd-res" role="listbox"></div><div class="fd-ft">' + _T('↑↓ 選擇 · Enter 前往 · Esc 關閉', '↑↓ select · Enter go · Esc close') + '</div></div></div>' +
      '<button type="button" class="fd-fab" id="fd-fab" aria-label="' + _T('這一版的目錄與搜尋', 'Contents and search') + '"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h10"/></svg><span>' + _T('目錄', 'Contents') + '</span></button>');
    var tk = $('.ticker'), fs = $('#fs');
    if (tk) { var b = document.createElement('button'); b.type = 'button'; b.className = 'fs-btn fd-btn'; b.id = 'fd-btn'; b.setAttribute('aria-label', _T('搜尋圖表與指標', 'Search charts and indicators')); b.innerHTML = MAG + _T('搜尋', 'Search') + '<kbd>' + (mac ? '⌘K' : 'Ctrl K') + '</kbd>'; tk.insertBefore(b, fs && fs.parentNode === tk ? fs : null); }
    var mp = $('#m-prefs'); if (mp) mp.insertAdjacentHTML('afterbegin', '<button type="button" id="m-find" aria-label="' + _T('搜尋圖表與指標', 'Search charts and indicators') + '">' + MAG + '</button>');
    document.addEventListener('click', function (e) {
      var t = e.target.closest && e.target.closest('#fd-btn, #m-find, #fd-fab'); if (t) { e.preventDefault(); fdOpen(); return; }
      if (e.target.closest && e.target.closest('[data-x]')) { fdClose(); return; }
      var a = e.target.closest && e.target.closest('.fd-r'); if (a) { e.preventDefault(); fdGo(a.getAttribute('data-to')); }
    });
    $('#fd-res').addEventListener('pointermove', function (e) { var a = e.target.closest('.fd-r'); if (!a) return; var rs = [].slice.call(this.querySelectorAll('.fd-r')), i = rs.indexOf(a); if (i !== fdAct) { fdAct = i - 0; rs.forEach(function (r, k) { r.classList.toggle('act', k === i); }); } });
    $('#fd-q').addEventListener('input', fdRender);
    document.addEventListener('keydown', function (e) {
      var fd = $('#fd'), k = e.key;
      if ((k === 'k' || k === 'K') && (e.metaKey || e.ctrlKey) && !e.altKey) { e.preventDefault(); if (fd.hidden) fdOpen(); else fdClose(); return; }
      if (fd.hidden) { if (k === '/' && !e.metaKey && !e.ctrlKey && !(e.target.closest && e.target.closest('input, textarea, select, [contenteditable]'))) { e.preventDefault(); fdOpen(); } return; }
      if (k === 'Escape') { e.preventDefault(); fdClose(); }
      else if (k === 'ArrowDown' || k === 'ArrowUp') { e.preventDefault(); fdMove(k === 'ArrowDown' ? 1 : -1); }
      else if (k === 'Enter') { var a = $('#fd-res').querySelectorAll('.fd-r')[fdAct]; if (a) { e.preventDefault(); fdGo(a.getAttribute('data-to')); } }
      else if (k === 'Tab') { e.preventDefault(); $('#fd-q').focus(); }   // 焦點留在對話框裡
    }, true);
  }
  // 側欄子目錄：每個有分組的版面，在它的導航鈕下面列組名；只有目前版面展開
  function buildSubnav() {
    var nav = $('#nav'); if (!nav) return;
    nav.querySelectorAll('.nav-sub').forEach(function (s) { s.remove(); });
    document.querySelectorAll('#view .pg').forEach(function (sec) {
      var gs = sec.querySelectorAll(':scope > .grid > .grp-h'), page = sec.getAttribute('data-r'), b = nav.querySelector('button[data-r="' + page + '"]');
      if (gs.length < 2 || !b) return;
      b.insertAdjacentHTML('afterend', '<div class="nav-sub' + (page === cur ? ' open' : '') + '" data-r="' + page + '">' + [].map.call(gs, function (g) { return '<a href="#' + page + '/' + g.id.slice(4) + '" data-g="' + g.id + '">' + esc(fdTxt(g.querySelector('h2'))) + '</a>'; }).join('') + '</div>');
    });
    nav.addEventListener('click', function (e) { var a = e.target.closest('.nav-sub a'); if (!a) return; e.preventDefault(); var el = document.getElementById(a.getAttribute('data-g')); if (el) userNav(a.getAttribute('href').slice(1), function () { toHead(el); }); });
  }
  function toHead(el, smooth) {   // 標題對齊頂部列下緣（scrollIntoView 不管黏住的頂部列）
    var far = Math.abs(el.getBoundingClientRect().top) > innerHeight * 2;
    window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - stickyH() - GAP, behavior: reduced || far || smooth === false ? 'auto' : 'smooth' });
  }
  // 目前所在的組：目前版面裡，標題已經捲過頂部列下方 30% 高度的最後一組
  function grpNow() {
    var sec = $('#pg-' + cur); if (!sec) return null;
    var line = stickyH() + (window.innerHeight - stickyH()) * 0.3, pick = null;
    sec.querySelectorAll(':scope > .grid > .grp-h').forEach(function (g) { if (g.getBoundingClientRect().top <= line) pick = g; });
    return pick;
  }
  var grpLast;
  function grpSpy() {
    var g = grpNow(), id = g ? g.id : '', key = cur + '|' + id;
    if (key === grpLast) return; grpLast = key;
    var r = ROUTES.filter(function (x) { return x[0] === cur; })[0], ck = $('#crumb-k'); if (ck && r) ck.textContent = g ? fdTxt(g.querySelector('h2')) : r[2];
    document.querySelectorAll('.nav-sub').forEach(function (s) { s.classList.toggle('open', s.getAttribute('data-r') === cur); s.querySelectorAll('a').forEach(function (a) { a.classList.toggle('on', a.getAttribute('data-g') === id); }); });
    var fab = $('#fd-fab'), fs = fab && fab.querySelector('span'); if (fs) fs.textContent = g ? fdTxt(g.querySelector('h2')) : _T('目錄', 'Contents');   // 手機頂部列不黏，目前的組寫在目錄鈕上
  }
  // 組標題加圖數
  function grpCounts() {
    document.querySelectorAll('#view .grp-h').forEach(function (g) {
      if (g.querySelector('.grp-n')) return; var n = 0;
      for (var el = g.nextElementSibling; el && !el.classList.contains('grp-h'); el = el.nextElementSibling) if (el.classList.contains('panel')) n++;
      if (n) g.querySelector('h2').insertAdjacentHTML('afterend', '<span class="grp-n">' + _T(n + ' 張', n + (n === 1 ? ' chart' : ' charts')) + '</span>');
    });
  }
  function copyText(t) {   // 剪貼簿 API 被拒（沒有焦點、舊瀏覽器）時改用 textarea＋execCommand
    var old = function () { var ta = document.createElement('textarea'); ta.value = t; ta.style.position = 'fixed'; ta.style.opacity = '0'; document.body.appendChild(ta); ta.select(); try { document.execCommand('copy'); } catch (e) {} document.body.removeChild(ta); };
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(t).catch(old);
    old(); return Promise.resolve();
  }
  /* 指標名可點（2026-11-04）：每日判讀、發現、摘要、行動、變化、新聞解讀裡第一次出現的指標名，連到它的圖，滑過顯示一句解釋 */
  var TERMS = [
    ['STH-SOPR', 'onchain', 'sopr', '短期持有者（持有不到 155 天）賣出時的平均獲利倍數；大於 1＝平均賺錢賣，小於 1＝認賠賣。', 'Profit multiple on coins sold by short-term holders (held under 155 days); above 1 = sold at a profit on average, below 1 = at a loss.'],
    ['LTH-SOPR', 'onchain', 'oc-lth-sopr', '長期持有者（持有 155 天以上）賣出時的平均獲利倍數。', 'Profit multiple on coins sold by long-term holders (held 155+ days).'],
    ['aSOPR', 'onchain', 'oc-asopr', '所有賣出的幣的平均獲利倍數（排除一小時內轉手）。', 'Average profit multiple on all coins sold (excluding coins moved within an hour).'],
    ['MVRV Z', 'cycle', 'p6', '市值減實現市值，再除以歷史標準差；越高代表整體帳面獲利越大、越接近過熱。頂部三指標之一。', 'Market cap minus realized cap, divided by its historical standard deviation; higher = bigger paper profits, closer to overheating. One of the top-3 indicators.'],
    ['MVRV', 'cycle', 'p20', '市值 ÷ 實現市值（每顆幣最後一次移動時的價格加總）；大於 1 代表整體帳面獲利。', 'Market cap ÷ realized cap (every coin valued at the price it last moved); above 1 = the market is in profit overall.'],
    ['NUPL', 'cycle', 'p6', '淨未實現損益：帳面獲利佔市值的比例。頂部三指標之一。', 'Net unrealized profit/loss: paper profit as a share of market cap. One of the top-3 indicators.'],
    ['Puell', 'cycle', 'p6', '礦工每日收入 ÷ 一年平均。頂部三指標之一。', 'Daily miner revenue ÷ its 1-year average. One of the top-3 indicators.'],
    ['URPD', 'onchain', 'urpd', '籌碼分布：每個價格區間有多少幣最後一次在那裡換手。', 'Supply distribution: how many coins last moved in each price band.'],
    ['真實市場均價', 'cycle', 'ev-tmm', '排除長期不動的幣之後，活躍投資人的平均成本（True Market Mean）。', 'Average cost basis of active investors, excluding long-dormant coins (True Market Mean).', 'true market mean'],
    ['短期持有者', 'onchain', 'cohort', '持有不到 155 天的幣（STH），通常是新進場的買家。', 'Coins held for under 155 days (STH), usually short-term holders.', 'short-term holder'],
    ['長期持有者', 'onchain', 'cohort', '持有 155 天以上的幣（LTH），通常是長期持有者。', 'Coins held for 155 days or more (LTH), usually long-term holders.', 'long-term holder'],
    ['Coinbase 溢價', 'flows', 'pr-us', 'Coinbase（美元）比 Binance（USDT）貴多少；大於 0＝美國買盤比較積極。', 'How much pricier Coinbase (USD) is than Binance (USDT); above 0 = US buyers are keener.', 'Coinbase premium'],
    ['資金費率', 'deriv', '', '永續合約多空雙方定期互付的費用；正值＝做多的人付錢，槓桿偏多。', 'The periodic fee between longs and shorts on perpetual futures; positive = longs pay, leverage leans long.', 'funding'],
    ['DVOL', 'deriv', 'vol', 'Deribit 的比特幣 30 天隱含波動率指數。', 'Deribit\'s 30-day implied volatility index for bitcoin.'],
    ['Tidemark', 'cycle', 'tm', '第三方的頂部／底部綜合模型，本站只作讀值。', 'A third-party top/bottom composite model; shown as a reading only.'],
    ['賣方衰竭', 'onchain', 'sec', '獲利供給 × 波動的乘積；跌到很低代表賣壓與波動同時枯竭。', 'Supply in profit × volatility; very low readings mean selling and volatility have both dried up.', 'seller exhaustion'],
    ['表觀需求', 'flows', 'ad', '新挖出的幣減去一年以上未動供給的變化，粗估市場吸收了多少。', 'New issuance minus the change in coins unmoved for a year — a rough gauge of how much the market absorbed.', 'apparent demand'],
    ['週線多空分數', 'cycle', 'regime', '六項已有訊號合成的週線分數，−6 到 +6。', 'A weekly score built from six existing signals, −6 to +6.', 'regime score'],
    ['頂部三指標', 'cycle', 'p6', 'MVRV Z、NUPL、Puell 的四年百分位；任兩項到 80 進入頂部區。', 'Four-year percentiles of MVRV Z, NUPL and Puell; any two at 80 = top zone.', 'top-3 indicators']
  ];
  function termify(root) {
    var boxes = root.querySelectorAll('.read, .find .what, .dek p, .acts li > span, .deltas p, .read-box');
    var list = TERMS.map(function (t) { var w = LANG === 'en' && t[5] ? t[5] : t[0]; return { w: w, lw: w.toLowerCase(), t: t }; }).sort(function (a, b) { return b.w.length - a.w.length; });
    var ascii = function (c) { return c && /[A-Za-z0-9-]/.test(c); };
    [].forEach.call(boxes, function (box) {
      list.forEach(function (it) {
        var walk = document.createTreeWalker(box, NodeFilter.SHOW_TEXT, null), n;
        while ((n = walk.nextNode())) {
          if (n.parentNode.closest('a')) continue;
          var tx = n.nodeValue, i = (LANG === 'en' ? tx.toLowerCase() : tx).indexOf(LANG === 'en' ? it.lw : it.w);
          if (i < 0) continue;
          if (/^[\x00-\x7f]+$/.test(it.w) && (ascii(tx[i - 1]) || ascii(tx[i + it.w.length]))) continue;   // 英數詞要整詞相符（STH 不吃到 STH-SOPR 的一部分）
          var t = it.t, a = document.createElement('a'); a.className = 'term' + (t[2] ? ' jump' : ''); a.href = '#' + t[1]; if (t[2]) a.setAttribute('data-chart', t[2]);
          a.setAttribute('data-def', _T(t[3], t[4])); a.textContent = tx.substr(i, it.w.length);
          var rest = n.splitText(i); rest.nodeValue = rest.nodeValue.slice(it.w.length); n.parentNode.insertBefore(a, rest);
          break;   // 每個區塊只連第一次出現
        }
      });
    });
  }
  var drawn = {};
  function drawPage(id) {
    if (drawn[id] || !V[id]) return; drawn[id] = 1;
    var sec = $('#pg-' + id); if (!sec) return;
    try { if (V[id].after) V[id].after(); } catch (e) { console.error(e); }
    try { attachReads(sec); } catch (e) { console.error(e); }
    try { markSignals(sec); } catch (e) { console.error(e); }
    try { termify(sec); } catch (e) { console.error(e); }
    mounted.forEach(observe); settleMeters(sec);
  }
  function drawAllPages() { ROUTES.forEach(function (r) { drawPage(r[0]); }); }
  /* 桌面延後畫圖（2026-11-09）：版面是一整頁往下疊，某一版的圖還沒畫時比較矮。為了不讓畫面跳：
     - 要跳到某一版（導覽、連結、返回、開頁網址）之前，先把它和上面所有版畫好（drawUpTo），再算位置；
     - 往下捲到離還沒畫的版不到三個畫面高時，先把它畫好（drawAhead）——長高的部分都在畫面下方；
     - 開頁 1.5 秒後，在瀏覽器閒置時由上往下一版一版補畫（drawIdle）。所以畫面上方的版一定已經畫好 */
  function drawUpTo(id) { if (id === 'book') id = 'deriv'; var ids = ids0(), k = ids.indexOf(id); for (var i = 0; i <= k; i++) drawPage(ids[i]); }
  function drawAhead() {
    if (MQ.matches) return; var lim = window.scrollY + window.innerHeight * 3;
    document.querySelectorAll('#view .pg').forEach(function (sec) { var id = sec.getAttribute('data-r'); if (!drawn[id] && docTop(sec) < lim) drawUpTo(id); });
  }
  function drawIdle() {
    if (MQ.matches) return; var next = ids0().filter(function (i) { return !drawn[i]; })[0]; if (!next) return;
    var idle = window.requestIdleCallback || function (f) { return setTimeout(f, 400); };
    idle(function () { if (!MQ.matches) { drawPage(next); drawIdle(); } }, { timeout: 4000 });
  }
  function drawNear(id) {   // 閒置時先畫左右兩版，滑過去不用等
    var ids = ids0(), k = ids.indexOf(id), idle = window.requestIdleCallback || function (f) { return setTimeout(f, 200); };
    [ids[k + 1], ids[k - 1]].forEach(function (n) { if (n && !drawn[n]) idle(function () { drawPage(n); }); });
  }
  function activate(id) {
    if (id === cur) return;
    var r = ROUTES.filter(function (x) { return x[0] === id; })[0], ids = ids0();
    if (cur && !reduced) {
      var fwd = ids.indexOf(id) > ids.indexOf(cur), w = $('#wipe');
      w.className = 'wipe ' + (MQ.matches ? (fwd ? 'rtl' : 'ltr') : 'v ' + (fwd ? 'up' : 'down')); void w.offsetWidth; w.classList.add('on');
    }
    cur = id; hideTip();
    document.querySelectorAll('#view .pg').forEach(function (sec) { sec.classList.toggle('cur', sec.getAttribute('data-r') === id); });
    drawPage(id); if (MQ.matches) drawNear(id);
    if (id === 'archive') arRender();   // 往期：成為目前版面時一定讀（IntersectionObserver 在背景分頁可能不觸發）
    document.querySelectorAll('.nav button').forEach(function (b) { b.setAttribute('aria-current', b.getAttribute('data-r') === id ? 'page' : 'false'); });
    var nv = $('#nav'), nb = nv.querySelector('[aria-current="page"]');   // 行動版頂部導航可橫向捲動：把目前版面捲到中間
    if (nb && nv.scrollWidth > nv.clientWidth) nv.scrollTo({ left: nb.offsetLeft - nv.offsetLeft - (nv.clientWidth - nb.offsetWidth) / 2, behavior: reduced ? 'auto' : 'smooth' });
    else if (nb && nv.scrollHeight > nv.clientHeight + 1) nv.scrollTop = Math.max(0, nb.offsetTop - nv.offsetTop - 60);   // 2026-11-08 桌面視窗矮、子目錄展開時，側欄導航捲到目前版面
    $('#crumb-k').textContent = r[2]; $('#crumb-t').textContent = r[1];
    document.title = (id === 'overview' ? _t('破曉 Daybreak') : r[1] + _t('｜破曉 Daybreak'));
    if (location.hash.slice(1) !== id) { try { history.replaceState(history.state, '', '#' + id); } catch (e) {} }   // 捲動換版只改網址，保留這一筆記住的位置
    if (!seen[id]) { seen[id] = 1; decodeNums($('#pg-' + id)); }
    grpLast = null; grpSpy();   // 2026-11-08 側欄子目錄與頂部小標跟著換版
  }
  // 目前版面＝開頭已經捲過畫面 40% 高度的最後一個版面
  function spy() {
    if (MQ.matches) return;   // 行動版分頁顯示，不跟捲動切換
    var line = stickyH() + (window.innerHeight - stickyH()) * 0.4, pick = ROUTES[0][0];
    document.querySelectorAll('#view .pg').forEach(function (sec) { if (sec.getBoundingClientRect().top <= line) pick = sec.getAttribute('data-r'); });
    activate(pick);
  }
  function docTop(sec) { var y = 0; for (var el = sec; el; el = el.offsetParent) y += el.offsetTop; return y; }   // 用 offsetTop 計算，不受進場動畫的位移影響
  // 行動版換版後回到頂部：手指左右滑常帶一點上下動作，手機會在換版後繼續慣性捲動、把回頂蓋掉；
  // 先短暫鎖住捲動讓慣性停下，再回頂，之後幾個時間點再確認一次
  function toTop() {
    var de = document.documentElement, b = document.body;
    de.style.overflow = b.style.overflow = 'hidden';
    window.scrollTo(0, 0); de.scrollTop = b.scrollTop = 0;
    var unlock = function () { if (de.style.overflow !== 'hidden') return; de.style.overflow = b.style.overflow = ''; window.scrollTo(0, 0); };
    requestAnimationFrame(unlock); setTimeout(unlock, 120);   // 2026-11-08：背景分頁不跑 requestAnimationFrame，捲動會一直被鎖住；加計時器備援
    [80, 250, 500].forEach(function (t) { setTimeout(function () { if (!jumping && MQ.matches && window.scrollY > 0) window.scrollTo(0, 0); }, t); });
  }
  var jumping = 0;   // 2026-11-08 修：跳到某張圖時，換版回頂部的最後一次檢查（500ms）會把跳轉蓋掉，手機上一直停在版面頂端
  /* 2026-11-04 每張圖都有網址：#版面/圖（例如 #onchain/sopr）。錨點依序找 #c-圖、#pn-面板；
     併掉的圖用 ALIAS 導到保留的那一張（舊的 notes、異動偵測、分享出去的連結都還能用） */
  var ALIAS = { cbp: ['flows', 'pr-us'], cost: ['cycle', 'ev-tmm'], 'oc-sth-sopr': ['onchain', 'sopr'] };
  function anchorEl(ch) { return ch ? $('#c-' + ch) || $('#pn-' + ch) || $('#grp-' + ch) || document.getElementById(ch) : null; }   // 2026-11-08 加組（#版面/組代號）與頭版大標
  /* 展開收起的區塊：收起時畫的圖寬度是 0（先畫成 280px），展開後直接重畫，不靠 ResizeObserver（有些瀏覽器在背景分頁不觸發） */
  function unfold(box) { if (!box) return; box.classList.remove('fold'); box.querySelectorAll('[id^="c-"]').forEach(function (e) { if (e._draw) { e._w = e.clientWidth; e._draw(e); } }); }
  /* 手機版長頁收合（2026-11-09 整體審查）：手機上鏈上版約 38 屏、週期與衍生品約 22 屏。4 張以上的組只露前 2 張（各組的排序本來就是
     重要的在前），其餘收在「展開這組其餘 N 張」後面，按鈕上列出收起來的圖名。只在手機生效（CSS），桌面不變；搜尋、目錄、
     連結、返回鍵要去的圖被收起時先展開那一組。展開過的組記在這次瀏覽（sessionStorage），換語言或重新整理後仍展開，接回的位置才準 */
  var GOPEN = (function () { try { return JSON.parse(sessionStorage.getItem('daybreak.gopen') || '[]'); } catch (e) { return []; } })();
  function foldGroups() {
    document.querySelectorAll('#view .pg > .grid').forEach(function (grid) {
      var gid = null, list = [];
      var flush = function () {
        if (gid && list.length >= 4 && GOPEN.indexOf(gid) < 0) {
          var more = list.slice(2), names = more.map(function (p) { return fdTxt(p.querySelector(':scope > .panel-h h2')); }).filter(Boolean);
          more.forEach(function (p) { p.classList.add('gmore'); p.setAttribute('data-gm', gid); });
          list[1].insertAdjacentHTML('afterend', '<button type="button" class="gmore-btn" data-gm="' + gid + '"><b>' + _T('展開這組其餘 ' + more.length + ' 張', 'Show ' + more.length + ' more in this group') + '</b><span>' + esc(names.slice(0, 4).join(_T('、', ', ')) + (names.length > 4 ? _T('…', '…') : '')) + '</span></button>');
        }
        list = [];
      };
      [].forEach.call(grid.children, function (k) { if (k.classList.contains('grp-h')) { flush(); gid = k.id; } else if (k.classList.contains('panel')) list.push(k); });
      flush();
    });
  }
  function openGroup(gid) {
    var ps = document.querySelectorAll('.panel.gmore[data-gm="' + gid + '"]'); if (!ps.length) return;
    ps.forEach(function (p) { p.classList.remove('gmore'); });
    var b = document.querySelector('.gmore-btn[data-gm="' + gid + '"]'); if (b) b.remove();
    if (GOPEN.indexOf(gid) < 0) { GOPEN.push(gid); try { sessionStorage.setItem('daybreak.gopen', JSON.stringify(GOPEN)); } catch (e) {} }
    ps.forEach(function (p) { p.querySelectorAll('[id^="c-"]').forEach(function (e) { if (e._draw) { e._w = e.clientWidth; e._draw(e); } }); });   // 收起時畫成 280px，展開後依實際寬度重畫
  }
  function openFor(el) { var p = el && el.closest && el.closest('.panel.gmore'); if (p) openGroup(p.getAttribute('data-gm')); }
  /* 返回鍵（2026-11-09 整體審查）：原本換版一律 replaceState，手機按返回直接離開網站、跳到別版的圖之後也回不去。
     使用者主動換位置（導覽、數字鍵、左右滑、看圖連結、搜尋、子目錄、版內目錄、頁內 # 連結）時，先把目前的版面與捲動位置
     記在這一筆紀錄（mark），再新增一筆（userNav）；捲動造成的自動換版仍只改網址。按返回時回到記住的版面與位置 */
  var popAt = 0;
  function mark() { try { history.replaceState({ y: Math.round(window.scrollY), p: cur }, '', location.href); } catch (e) {} }
  function userNav(hash, fn) { mark(); try { history.pushState(null, '', '#' + hash); } catch (e) {} fn(); }
  function restore(s) {
    popAt = Date.now(); hideTip();
    if (s.p && s.p !== cur) { if (MQ.matches) activate(s.p); }
    if (!MQ.matches) drawUpTo(s.p && $('#pg-' + s.p) ? s.p : cur);   // 桌面延後畫圖：重新整理後再按返回，要回去的版可能還沒畫
    var put = function () { window.scrollTo(0, s.y); if (!MQ.matches) spy(); };
    put(); [60, 300].forEach(function (t) { setTimeout(put, t); });   // 圖畫完版面會長高一點，再對一次
  }
  function jumpTo(page, ch) {
    if (ALIAS[ch]) { page = ALIAS[ch][0]; ch = ALIAS[ch][1]; }
    var at = anchorEl(ch), pg = at && at.closest('.pg'); if (pg) page = pg.getAttribute('data-r'); openFor(at);   // 圖搬過版面時跟著圖走（例如 oc-puell-multiple 現在在週期版）
    var same = page === cur && !!ch;   // 同一版裡跳：不先回到版面頂端再捲下去
    if (!same) go(page);
    if (!ch) return;
    jumping++; setTimeout(function () { jumping = Math.max(0, jumping - 1); }, 1200);
    setTimeout(function () { var el = anchorEl(ch); if (!el) return; unfold(el.closest('.fold')); var dt = el.closest('details'); if (dt) dt.open = true;
      var far = Math.abs(el.getBoundingClientRect().top) > innerHeight * 2;   // 遠的直接跳，近的才平滑捲
      if (el.classList.contains('grp-h') || el.classList.contains('sec-h')) toHead(el); else el.scrollIntoView({ block: el.offsetHeight > innerHeight * 0.7 ? 'start' : 'center', behavior: reduced || far ? 'auto' : 'smooth' }); el.classList.add('flash'); setTimeout(function () { el.classList.remove('flash'); }, 1800); setTimeout(function () { grpLast = null; grpSpy(); }, 450); }, same ? 30 : MQ.matches ? 350 : 500);
  }
  function go(id) {
    if (id && id.indexOf('/') > 0) { var pr = id.split('/'); jumpTo(pr[0], pr[1]); return; }
    if (id === 'book') id = 'deriv';   // 2026-10-12 掛單簿版面併入衍生品版，舊連結導過去
    var sec = $('#pg-' + id); if (!sec) return;
    if (MQ.matches) { activate(id); toTop(); return; }
    drawUpTo(id);   // 桌面：先畫好目標版與上面的版，算出來的位置才準
    window.scrollTo(0, id === ROUTES[0][0] ? 0 : docTop(sec) - stickyH() - GAP);
    spy();
  }
  /* index.html 裡寫死的中文，英文版在這裡換掉 */
  function staticText() {
    if (LANG !== 'en') return;
    var set = function (sel, txt, attr) { var el = $(sel); if (!el) return; if (attr) el.setAttribute(attr, txt); else el.textContent = txt; };
    set('.brand', 'Daybreak front page', 'aria-label'); set('.wordmark span', 'BTC BRIEF'); set('#nav', 'Sections', 'aria-label');
    set('.edition .k', 'EDITION'); set('#theme', 'Edition style', 'aria-label');
    var tb = document.querySelectorAll('#theme button'); if (tb[0]) tb[0].textContent = 'Day'; if (tb[1]) tb[1].textContent = 'Night';
    set('#m-theme', 'Toggle light / dark', 'aria-label');
    var ck = $('.clock'); if (ck && ck.firstChild && ck.firstChild.nodeType === 3) ck.firstChild.nodeValue = 'Next ';
    var fs = $('#fs'); if (fs) { fs.setAttribute('aria-label', 'Full screen'); fs.lastChild.nodeValue = 'Full screen'; }
    var ft = document.querySelectorAll('.foot span'); ['© Daybreak', 'For research only — not investment advice', 'Press 1–9, 0 to switch sections; / to search', 'Swipe left/right to switch sections'].forEach(function (x, i) { if (ft[i]) ft[i].textContent = x; });
    var fr = $('#follow-rail .k'); if (fr) fr.textContent = 'FOLLOW';
    var ff = $('#follow-foot'); if (ff) ff.innerHTML = 'Daily at 08:30 Taipei · follow <b>@songpu717</b> on X ↗';
    document.title = 'Daybreak';
    var md = document.querySelector('meta[name="description"]'); if (md) md.setAttribute('content', 'Daybreak: the first Bitcoin brief of the morning — news with analysis, market data, cycle position and a staged exit framework.');
  }
  function shell() {
    try { findShell(); } catch (e) { console.error(e); }   // 2026-11-08 全站搜尋
    $('#nav').innerHTML = ROUTES.map(function (r, i) { return '<button type="button" data-r="' + r[0] + '"><span class="i">' + ('0' + (i + 1)).slice(-2) + '</span><span>' + r[1] + '</span></button>'; }).join('');
    $('#nav').addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) { var r = b.getAttribute('data-r'); userNav(r, function () { go(r); }); } });
    document.addEventListener('keydown', function (e) { if ((e.target.closest && e.target.closest('input,textarea')) || e.metaKey || e.ctrlKey || e.altKey) return; var n = e.key === '0' ? 10 : +e.key; if (n >= 1 && n <= ROUTES.length) { var r = ROUTES[n - 1][0]; userNav(r, function () { go(r); }); } });
    // 跨過 860px（旋轉、縮放視窗）時切換顯示方式，停在同一版
    var onMode = function () { if (MQ.matches) window.scrollTo(0, 0); else { drawAllPages(); go(cur); } };   // 換成桌面版：沒畫過的版一次補齊
    if (MQ.addEventListener) MQ.addEventListener('change', onMode); else if (MQ.addListener) MQ.addListener(onMode);
    window.addEventListener('popstate', function (e) { var st = e.state; if (st && st.y != null) restore(st); });
    window.addEventListener('hashchange', function () { if (Date.now() - popAt < 400) return; var h = location.hash.slice(1); if (h !== cur) go(h); });   // 返回時已由 popstate 處理就略過
    document.addEventListener('click', function (e) { var a = e.target.closest && e.target.closest('a[href^="#"]'); if (a && !e.defaultPrevented) mark(); }, true);   // 頁內一般 # 連結：瀏覽器自己新增紀錄，先記住現在的位置
    // 2026-10-23：「看圖 →」連結：換到那一版後捲到那張圖並閃一下
    document.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('.ev-open, .oc-more'); if (b) unfold(b.closest('.fold')); var gb = e.target.closest && e.target.closest('.gmore-btn'); if (gb) openGroup(gb.getAttribute('data-gm')); });
    document.addEventListener('click', function (e) {
      var t = e.target.closest && e.target.closest('.toc a'); if (t) { e.preventDefault(); var pn = document.getElementById(t.getAttribute('data-pn')); if (pn) { openFor(pn); mark(); try { history.pushState(null, '', t.getAttribute('href')); } catch (er) {} var far = Math.abs(pn.getBoundingClientRect().top) > innerHeight * 2; window.scrollTo({ top: pn.getBoundingClientRect().top + scrollY - stickyH() - GAP, behavior: reduced || far ? 'auto' : 'smooth' }); } return; }
      var cp = e.target.closest && e.target.closest('.cp-link'); if (cp) { copyText(location.origin + location.pathname + '#' + cp.getAttribute('data-u')).then(function () { cp.textContent = _T('已複製', 'Copied'); cp.classList.add('ok'); setTimeout(function () { cp.textContent = '#'; cp.classList.remove('ok'); }, 1500); }); }
    });
    document.addEventListener('pointerover', function (e) { var a = e.target.closest && e.target.closest('a.term'); if (a && e.pointerType !== 'touch') showTip(e.clientX, e.clientY, '<div class="t">' + esc(a.textContent) + '</div><div class="term-def">' + esc(a.getAttribute('data-def')) + '</div>'); });
    document.addEventListener('pointerout', function (e) { if (e.target.closest && e.target.closest('a.term')) hideTip(); });
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a.jump'); if (!a) return; var ch = a.getAttribute('data-chart'); if (!ch) return;
      e.preventDefault(); var pg = a.getAttribute('href').slice(1); userNav(pg + '/' + ch, function () { jumpTo(pg, ch); });
    });
    // 桌面換頁頓點：滾輪捲過版面開頭時，先停在「該版標題貼齊頂部列」的位置，頓 HOLD 毫秒（期間的滾輪與慣性吃掉），之後照常捲動
    var hold = 0, HOLD = 260;
    window.addEventListener('wheel', function (e) {
      if (MQ.matches || e.ctrlKey || !e.deltaY || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
      var now = Date.now();
      if (now < hold) { e.preventDefault(); return; }
      var dy = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? window.innerHeight : 1), doc = document.documentElement;
      for (var el = e.target; el && el.nodeType === 1 && el !== doc; el = el.parentElement)   // 內層可捲動區還沒捲完就交給它
        if (el.scrollHeight > el.clientHeight + 1 && /auto|scroll/.test(getComputedStyle(el).overflowY) && (dy > 0 ? el.scrollTop + el.clientHeight < el.scrollHeight - 1 : el.scrollTop > 0)) return;
      var y = window.scrollY, to = y + dy, sh = stickyH(), secs = document.querySelectorAll('#view .pg');
      for (var i = 1; i < secs.length; i++) {
        var b = docTop(secs[i]) - sh - GAP;
        if ((dy > 0 && y < b - 1 && to >= b) || (dy < 0 && y > b + 1 && to <= b)) { e.preventDefault(); window.scrollTo(0, b); hold = now + HOLD; return; }
      }
    }, { passive: false });
    var ticking = false;
    window.addEventListener('scroll', function () { if (ticking) return; ticking = true; requestAnimationFrame(function () { ticking = false; drawAhead(); spy(); grpSpy(); var fab = $('#fd-fab'); if (fab) fab.classList.toggle('show', MQ.matches && window.scrollY > window.innerHeight * 1.2); }); }, { passive: true });
    // 行動版：在內容區左右滑動切換到相鄰版面。圖表、表格、滑桿等本身要橫向操作的區域，以及螢幕邊緣（瀏覽器返回手勢）不觸發
    var sw = null, view = $('#view');
    view.addEventListener('touchstart', function (e) {
      sw = null;
      var p = e.touches[0];
      if (e.touches.length !== 1 || !MQ.matches || p.clientX < 16 || p.clientX > window.innerWidth - 16) return;
      if (e.target.closest('input, textarea, select')) return;   // 滑桿要自己用橫向手勢
      for (var el = e.target; el && el !== view; el = el.parentElement) if (el.scrollWidth > el.clientWidth + 1 && /auto|scroll/.test(getComputedStyle(el).overflowX)) return;
      sw = { x: p.clientX, y: p.clientY, t: Date.now() };
    }, { passive: true });
    view.addEventListener('touchcancel', function () { sw = null; }, { passive: true });
    view.addEventListener('touchend', function (e) {
      if (!sw) return;
      var p = e.changedTouches[0], dx = p.clientX - sw.x, dy = p.clientY - sw.y, dt = Date.now() - sw.t; sw = null;
      if (Math.abs(dx) < 50 || Math.abs(dx) < Math.abs(dy) * 1.2 || dt > 1000) return;
      var i = ROUTES.map(function (r) { return r[0]; }).indexOf(cur) + (dx < 0 ? 1 : -1);
      if (i >= 0 && i < ROUTES.length) { var r = ROUTES[i][0]; userNav(r, function () { go(r); }); }
    }, { passive: true });
    // 日刊／夜刊：桌面在側欄、行動版在頂部列右上；語言：選了就記住（daybreak.lang），重新載入套用
    var tt = $('#theme'), mt = $('#m-theme');   // 2026-11-09 日月圖示改由 ttIconSvg 產生（地平線日月，隨中間狀態變形）
    function setTheme(v) {
      if (v === 'dark') document.documentElement.setAttribute('data-theme', 'dark'); else document.documentElement.removeAttribute('data-theme');
      tt.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x.getAttribute('data-t') === v); });
      if (mt) mt.setAttribute('data-v', v);
      if (!TV) { tt.style.setProperty('--tt-k', v === 'dark' ? 1 : 0); ttIcoAll(v === 'dark' ? 1 : 0); }   // 換刊過渡中滑塊和圖示由 ttGo 的逐格迴圈帶
    }
    // 2026-11-09 換刊的中間狀態（使用者看了一支深淺色切換的範例影片：「重點是會有中間狀態效果」「用黃昏色調」「按鈕用 icon、動畫同步改變」「按鈕本身也需要配合動效」）
    // 同日第三版（使用者看了第二支範例：「還是沒有很絲滑」「整體的氛圍感還不夠」）：原本整頁一起變暗、中段蓋一層灰霧再換刊，中間會變成一片灰；
    // 改成「晨昏線」：新的一刊從切換鈕那裡像天色一樣往外漫開，交界是一圈暮色光帶（入夜：外側琥珀夕照→品牌橘紅→內側靛藍；破曉反過來，外側紫→玫瑰→內側金），
    // 還沒漫到的舊版面跟著慢慢偏暖變暗（夕照）或微微轉亮（黎明前），剛破曉的日刊先帶一點金色再褪回原色。
    // 用瀏覽器的 View Transition：舊版面是一張靜態快照、新版面是即時畫面；換刊（整頁重算約 60 毫秒）在動畫開始前做完，
    // 過程中只動快照的圓形裁切、濾鏡和一張半解析度的光帶畫布，不重算整頁，所以中途不會卡一下。
    // 桌面拖曳側欄切換鈕可停在任何位置看晨昏線，放開吸到較近的一端；點一下（含手機日月鈕）播完整段（約 1 秒）。滑塊、日月圖示、按鈕天色照舊跟著走。
    // 兩端完全等於原本的日刊與夜刊（淺色底色不變）；系統設了「減少動態效果」或瀏覽器不支援 View Transition 就照舊瞬間切換。
    var TTX = { t: 0, s: 1, lt: 0, ln: 0 };
    function ttLin(c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
    function ttDelin(c) { c = c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055; return Math.round(Math.max(0, Math.min(1, c)) * 255); }
    function ttLab(q) { var r = ttLin(q[0]), g = ttLin(q[1]), b = ttLin(q[2]), l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b), m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b), s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b); return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s, q[3]]; }
    function ttFromLab(L) { var l = L[0] + 0.3963377774 * L[1] + 0.2158037573 * L[2], m = L[0] - 0.1055613458 * L[1] - 0.0638541728 * L[2], s = L[0] - 0.0894841775 * L[1] - 1.2914855480 * L[2]; l = l * l * l; m = m * m * m; s = s * s * s; return [ttDelin(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s), ttDelin(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s), ttDelin(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s), L[3]]; }
    function ttMix(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t]; }
    function ttClamp(x) { return Math.max(0, Math.min(1, x)); }
    function ttEase(p) { return p < .5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2; }
    function ttOut(p) { return 1 - (1 - p) * (1 - p); }
    function ttBez(x1, y1, x2, y2) {   // CSS cubic-bezier()，給晨昏線推進用
      return function (x) { if (x <= 0) return 0; if (x >= 1) return 1; var lo = 0, hi = 1, t = x; for (var i = 0; i < 22; i++) { t = (lo + hi) / 2; if (3 * x1 * t * (1 - t) * (1 - t) + 3 * x2 * t * t * (1 - t) + t * t * t < x) lo = t; else hi = t; } return 3 * y1 * t * (1 - t) * (1 - t) + 3 * y2 * t * t * (1 - t) + t * t * t; };
    }
    var ttSweep = ttBez(.5, .08, .5, 1);   // 晨昏線推進：起步輕、中段勻速掃過版面、尾端光帶出畫面時放慢
    var AMB = ttLab([242, 160, 61, 1]), SUNSET = ttLab([255, 74, 46, 1]), NIGHTB = ttLab([88, 98, 214, 1]);
    function ttStr(q) { return 'rgba(' + q[0] + ',' + q[1] + ',' + q[2] + ',' + (+q[3].toFixed(3)) + ')'; }
    function ttCur() { return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'; }
    // 圖示：24×24，地平線 y=19；太陽圓心 (12,11) 往下落到看不見，月亮從地平線下升到 (12,11)
    var ttN = 0;
    function ttIconSvg(live) {
      var id = 'ttc' + (++ttN);
      return '<svg class="tt-ico' + (live ? ' live' : '') + '" viewBox="0 0 24 24" aria-hidden="true"><defs><clipPath id="' + id + '"><rect x="-4" y="-6" width="32" height="23.9"/></clipPath></defs>' +
        '<g clip-path="url(#' + id + ')"><g class="sun"><circle cx="12" cy="11" r="4"/><g class="rays"><path d="M12 2.6v2M12 17.4v2M3.6 11h2M18.4 11h2M6.1 5.1l1.4 1.4M16.5 15.5l1.4 1.4M6.1 16.9l1.4-1.4M16.5 6.5l1.4-1.4"/></g></g>' +
        '<g class="moon"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" vector-effect="non-scaling-stroke"/></g></g><path class="hz" d="M2.5 19h19"/></svg>';
    }
    function ttIco(svg, t) {
      // 太陽 0–45% 沉到地平線下（約 30% 時剩半圓，就是品牌標誌的樣子），光芒在前 24% 收起並轉動；月亮 45% 起快速冒出、到 100% 升到原位
      var e = ttEase(ttClamp(t / 0.45)), k = 1 - ttEase(ttClamp(t / 0.24)), p = ttClamp((t - 0.45) / 0.55), em = 1 - (1 - p) * (1 - p);
      svg.querySelector('.sun').setAttribute('transform', 'translate(0 ' + (13 * e).toFixed(2) + ')');
      var ry = svg.querySelector('.rays'); ry.setAttribute('transform', 'translate(12 11) rotate(' + (60 * t).toFixed(1) + ') scale(' + (0.62 + 0.38 * k).toFixed(3) + ') translate(-12 -11)'); ry.setAttribute('opacity', k.toFixed(3));   // 光芒往圓邊收、同時淡出，不會縮進圓裡
      svg.querySelector('.moon').setAttribute('transform', 'translate(12.6 ' + (t < 0.45 ? 30 : 23.5 - 12.5 * em).toFixed(2) + ') rotate(' + (-30 * (1 - em)).toFixed(1) + ') scale(.6) translate(-12 -12)');
    }
    function ttIcoAll(t) { document.querySelectorAll('.tt-ico.live').forEach(function (s) { ttIco(s, t); }); }
    function ttIcons() {
      var bs = tt.querySelectorAll('button');
      bs.forEach(function (b, i) { var lab = b.textContent.trim(); if (lab) { b.setAttribute('aria-label', lab); b.setAttribute('title', lab); } b.innerHTML = ttIconSvg(false); ttIco(b.firstChild, i); });
      if (!tt.querySelector('.tt-knob')) { var sky = document.createElement('span'); sky.className = 'tt-sky'; sky.setAttribute('aria-hidden', 'true'); tt.insertBefore(sky, tt.firstChild); var kn = document.createElement('span'); kn.className = 'tt-knob'; kn.setAttribute('aria-hidden', 'true'); kn.innerHTML = ttIconSvg(true); tt.appendChild(kn); }
      if (mt) mt.innerHTML = ttIconSvg(true);
      tt.classList.add('tt-icons');
      ttIcoAll(ttCur() === 'dark' ? 1 : 0);
    }
    // 按鈕裡的天色：傍晚琥珀 → 日落品牌橘紅 → 入夜靛藍，強度在中段最高
    function ttSky(t) {
      var c = t < .3 ? AMB : t < .5 ? ttMix(AMB, SUNSET, (t - .3) / .2) : t < .72 ? ttMix(SUNSET, NIGHTB, (t - .5) / .22) : NIGHTB;
      return [ttFromLab(c), Math.sin(Math.PI * t)];
    }
    var ttPh = null;
    function ttPhase(from) {   // 切換鈕旁的小字「黃昏／破曉」
      if (!ttPh) { ttPh = document.createElement('div'); ttPh.className = 'tt-phase'; document.body.appendChild(ttPh); }
      var src = (mt && mt.offsetParent) ? mt : tt, r = src.getBoundingClientRect(), mob = src === mt;
      ttPh.style.left = (mob ? r.left - 40 : r.left) + 'px'; ttPh.style.top = (mob ? r.bottom + 6 : r.top - 22) + 'px'; ttPh.style.width = (mob ? r.width + 80 : r.width) + 'px';
      ttPh.textContent = from === 'dark' ? (LANG === 'en' ? 'Daybreak' : '破曉') : (LANG === 'en' ? 'Dusk' : '黃昏');
    }
    // 滑塊、圖示、按鈕天色跟著 t（0 日刊～1 夜刊）；滑塊移動越快拉得越長（最多 1.3 倍），慢下來就收回
    function ttKnob(t, ph) {
      var now = performance.now(), vel = Math.abs(t - TTX.lt) / Math.max(8, now - TTX.ln) * 1000, tgt = 1 + Math.min(0.3, vel * 0.16);
      TTX.s = TTX.s + (tgt - TTX.s) * 0.35; TTX.lt = t; TTX.ln = now; TTX.t = t;
      tt.style.setProperty('--tt-k', t); tt.style.setProperty('--tt-s', TTX.s.toFixed(3));
      var sk = ttSky(t), skc = ttStr([sk[0][0], sk[0][1], sk[0][2], 1]);
      [tt, mt].forEach(function (el) { if (el) { el.style.setProperty('--tt-sky', skc); el.style.setProperty('--tt-glow', sk[1].toFixed(3)); } });
      ttIcoAll(t);
      if (ttPh) ttPh.style.opacity = Math.min(1, ph * 3);
    }
    function ttSettle(el) { if (!el) return; el.classList.remove('tt-settle'); void el.offsetWidth; el.classList.add('tt-settle'); }
    // 換刊後重畫圖表（程式算色的圖要跟著換）：一次重畫全部 87 張要 0.5 秒以上；
    // 先同步畫畫面上看得到的（在過渡開始前、被快照蓋著時畫），其餘等過渡結束後每格最多畫 8 毫秒分批補完。再換一次刊就重新排隊
    var ttRq = 0;
    function ttCharts() {
      var vis = [], rest = [], H = innerHeight;
      mounted.forEach(function (el) { if (!el._draw || !el.isConnected) return; var r = el.getBoundingClientRect(); (r.width && r.bottom > -300 && r.top < H + 300 ? vis : rest).push(el); });
      vis.forEach(function (el) { el._draw(el); });
      return rest;
    }
    function ttDrawRest(rest) {
      var id = ++ttRq;
      (function step() { if (id !== ttRq) return; var t0 = performance.now(); while (rest.length && performance.now() - t0 < 8) { var el = rest.shift(); if (el.isConnected) el._draw(el); } if (rest.length) setTimeout(step, 16); })();
    }
    function ttRedraw() { ttDrawRest(ttCharts()); }
    // 晨昏線光帶：以切換鈕為圓心、半徑 r 的一圈漸層（半解析度畫布）；stops 是相對交界的距離（光帶寬 F 的倍數）和顏色
    var TT_BAND = {
      dark: [[-1.5, [70, 58, 170, 0]], [-0.75, [72, 60, 176, .30]], [-0.22, [205, 58, 96, .30]], [0.12, [255, 104, 46, .36]], [0.7, [255, 166, 68, .2]], [2.6, [255, 190, 110, 0]]],
      light: [[-1.5, [255, 200, 120, 0]], [-0.75, [255, 186, 96, .30]], [-0.22, [255, 116, 88, .30]], [0.12, [214, 78, 150, .28]], [0.7, [104, 84, 214, .24]], [2.6, [70, 60, 180, 0]]]
    };
    function ttBand(V) {
      var c = V.cx, q = V.q, W = V.cv.width, H = V.cv.height, x = V.x * q, y = V.y * q, r = V.R * V.sp * q, F = V.F * q, st = TT_BAND[V.to];
      c.clearRect(0, 0, W, H);
      var a = ttClamp(V.sp / 0.05); if (!a || V.sp >= 1) return;
      var r0 = Math.max(0, r + st[0][0] * F), r1 = r + st[st.length - 1][0] * F, g = c.createRadialGradient(x, y, r0, x, y, r1);
      st.forEach(function (s) { var d = r + s[0] * F; g.addColorStop(ttClamp((d - r0) / (r1 - r0)), 'rgba(' + s[1][0] + ',' + s[1][1] + ',' + s[1][2] + ',' + (s[1][3] * a).toFixed(3) + ')'); });
      c.fillStyle = g; c.fillRect(0, 0, W, H);
    }
    // 2026-11-09 使用者：「按鈕一圈可以有動態光圈嗎」，選「只在切換時繞一圈」；之後：「可以直接在邊框上嗎？速度再慢一點，要有發光感」。
    // 換刊時一道光沿著切換鈕的邊框繞一圈後淡出（約 1.9 秒，自己計時，換刊結束後繼續繞完）；往夜刊順時針、往日刊逆時針，和滑塊同方向；
    // 顏色取新的一刊：日刊品牌橘紅、夜刊暖金。四層：光頭一團柔光、沿線模糊的光暈、邊框上的亮線、光頭的白芯。光暈只用在這顆鈕（使用者 11/09 指定要發光感，淺色主題其他地方仍不加光暈）。
    // 退回原刊時 0.22 秒淡掉。換刊過渡中光線有自己的 view-transition-name，疊在光帶上面、不被圓形裁切遮住
    var TT_RING = [[34, .2, .14], [16, .55, .4], [5, 1, .8]], TT_RING_MS = 1900, TT_RG = null;   // 光尾到光頭：長度（一圈＝100）、亮線不透明度、光暈不透明度
    function ttRing(src, b, to) {
      var G = 12, w = b.width + G * 2, h = b.height + G * 2, br = parseFloat(getComputedStyle(src).borderTopLeftRadius) || 0, r = Math.max(0, Math.min(br, b.height / 2, b.width / 2) - 0.5);
      var x0 = G + 0.5, y0 = G + 0.5, x1 = w - G - 0.5, y1 = h - G - 0.5, A = function (x, y) { return r ? 'A' + r + ' ' + r + ' 0 0 1 ' + x + ' ' + y : 'L' + x + ' ' + y; };
      var d = 'M' + w / 2 + ' ' + y0 + 'H' + (x1 - r) + A(x1, y0 + r) + 'V' + (y1 - r) + A(x1 - r, y1) + 'H' + (x0 + r) + A(x0, y1 - r) + 'V' + (y0 + r) + A(x0 + r, y0) + 'Z';
      var P = function (cls, op) { return '<path class="' + cls + '" pathLength="100" d="' + d + '" opacity="' + op + '"/>'; };
      var el = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      el.setAttribute('class', 'tt-ring' + (to === 'dark' ? ' to-dark' : '')); el.setAttribute('aria-hidden', 'true'); el.setAttribute('width', w); el.setAttribute('height', h); el.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
      el.style.left = (b.left - G) + 'px'; el.style.top = (b.top - G) + 'px';
      el.innerHTML = '<defs><filter id="tt-ring-blur" filterUnits="userSpaceOnUse" x="0" y="0" width="' + w + '" height="' + h + '"><feGaussianBlur stdDeviation="3"/></filter><filter id="tt-ring-bloom" filterUnits="userSpaceOnUse" x="0" y="0" width="' + w + '" height="' + h + '"><feGaussianBlur stdDeviation="5"/></filter></defs><g' + (to === 'light' ? ' transform="matrix(-1 0 0 1 ' + w + ' 0)"' : '') + '>' +
        '<g class="bloom" filter="url(#tt-ring-bloom)">' + P('', .55) + '</g><g class="glow" filter="url(#tt-ring-blur)">' + TT_RING.map(function (x) { return P('', x[2]); }).join('') + '</g>' + TT_RING.map(function (x) { return P('ln', x[1]); }).join('') + P('core', .9) + '</g>';
      var ps = [].slice.call(el.querySelectorAll('path'));
      return { el: el, bl: ps[0], gl: ps.slice(1, 4), ln: ps.slice(4, 7), core: ps[7] };
    }
    function ttRingDash(p, L, hd) { p.setAttribute('stroke-dasharray', L.toFixed(2) + ' ' + (100 - L).toFixed(2)); p.setAttribute('stroke-dashoffset', (L - hd).toFixed(2)); }
    function ttRingOff(now) { var g = TT_RG; if (!g) return; if (!now) { if (!g.cut) g.cut = performance.now(); return; } cancelAnimationFrame(g.raf); if (g.el.parentNode) g.el.parentNode.removeChild(g.el); TT_RG = null; }
    function ttRingRun(g, V) {
      TT_RG = g;
      (function f(now) {
        if (TT_RG !== g) return;
        if (!g.t0) { if (!V.ready) { g.raf = requestAnimationFrame(f); return; } g.t0 = now; }
        if (V.back && !g.cut) g.cut = now;
        var u = Math.min(1, (now - g.t0) / TT_RING_MS), hd = 104 * (1 - Math.cos(Math.PI * u)) / 2, a = ttClamp(u / 0.06) * (1 - ttClamp((u - 0.8) / 0.2));
        if (g.cut) a *= 1 - ttClamp((now - g.cut) / 220);
        g.el.style.opacity = a.toFixed(3);
        TT_RING.forEach(function (x, i) { var L = Math.min(x[0], hd); ttRingDash(g.gl[i], L, hd); ttRingDash(g.ln[i], L, hd); });
        ttRingDash(g.core, Math.min(3, hd), hd); ttRingDash(g.bl, Math.min(9, hd), hd);
        if (u >= 1 || (g.cut && now - g.cut >= 220)) return ttRingOff(true);
        g.raf = requestAnimationFrame(f);
      })(performance.now());
    }
    var TV = null;   // 進行中的換刊：sp＝晨昏線推進（0 原刊～1 新刊）、kp＝滑塊往新刊走了多少
    function ttGo(to) {
      if (TV) return TV;
      var src = (mt && mt.offsetParent) ? mt : tt, b = src.getBoundingClientRect(), x = b.left + b.width / 2, y = b.top + b.height / 2, W = innerWidth, H = innerHeight;
      var R = Math.max(Math.hypot(x, y), Math.hypot(W - x, y), Math.hypot(x, H - y), Math.hypot(W - x, H - y)), F = Math.max(70, Math.min(190, R * 0.12));
      var V = TV = { from: ttCur(), to: to, x: x, y: y, F: F, R: R + F * 1.6, sp: 0, kp: 0, tw: null, an: [], raf: 0, back: false };
      var cv = V.cv = document.createElement('canvas'); cv.className = 'tt-dusk'; cv.setAttribute('aria-hidden', 'true');
      V.q = 0.5; cv.width = Math.ceil(W * V.q); cv.height = Math.ceil(H * V.q); V.cx = cv.getContext('2d'); ttRingOff(true); V.rg = ttRing(src, b, to);
      document.documentElement.classList.add('tt-vt'); ttPhase(V.from);
      V.vt = document.startViewTransition(function () { setTheme(to); document.body.appendChild(cv); document.body.appendChild(V.rg.el); V.rest = ttCharts(); });
      V.vt.ready.then(function () {
        var root = document.documentElement, at = ' at ' + x.toFixed(1) + 'px ' + y.toFixed(1) + 'px)', o = { duration: 1000, easing: 'linear', fill: 'both' };
        function an(k, pe) { var a = root.animate(k, Object.assign({ pseudoElement: pe }, o)); a.pause(); a.currentTime = V.sp * 1000; V.an.push(a); }
        an({ clipPath: ['circle(0px' + at, 'circle(' + V.R.toFixed(1) + 'px' + at] }, '::view-transition-new(root)');
        if (to === 'dark') an({ filter: ['none', 'sepia(.32) saturate(1.3) brightness(.86)'] }, '::view-transition-old(root)');   // 夕照：還沒入夜的日刊偏暖變暗
        else { an({ filter: ['none', 'brightness(1.6) saturate(1.3)'] }, '::view-transition-old(root)'); an({ filter: ['sepia(.4) saturate(1.25) brightness(.95)', 'sepia(.14) saturate(1.08) brightness(.99)', 'none'] }, '::view-transition-new(root)'); }   // 破曉：夜刊微亮、日刊先帶金色
        V.ready = true;
      }, function () {});
      V.vt.finished.then(function () { ttDone(V); }, function () { ttDone(V); });
      (function f(now) {
        if (V.done || V.fin) return;
        var w = V.tw, p = 1;
        if (w) { if (!V.ready) w.t0 = now; p = Math.min(1, (now - w.t0) / w.ms); V.sp = w.a + (w.b - w.a) * w.ez(p); V.kp = w.ka + (w.kb - w.ka) * w.kz(p); if (w.b && V.sp > 0.995 && V.kp > 0.995) { V.sp = V.kp = p = 1; } }   // 光帶已出畫面就收尾，不空等緩出的尾巴
        if (V.ready) V.an.forEach(function (a) { a.currentTime = V.sp * 1000; });
        ttBand(V); ttKnob(to === 'dark' ? V.kp : 1 - V.kp, Math.sin(Math.PI * V.sp));
        if (w && p >= 1 && (V.sp <= 0 || V.sp >= 1)) return ttFinish(V);
        V.raf = requestAnimationFrame(f);
      })(performance.now());
      ttRingRun(V.rg, V);
      return V;
    }
    function ttTw(V, b, ms, ez, kz) { V.back = !b; V.tw = { t0: performance.now(), ms: Math.max(1, ms), a: V.sp, b: b, ez: ez, ka: V.kp, kb: b, kz: kz || ez }; }
    function ttFinish(V) {
      V.fin = true; cancelAnimationFrame(V.raf); V.cx.clearRect(0, 0, V.cv.width, V.cv.height);
      function end() { if (V.ready) V.an.forEach(function (a) { a.finish(); }); else V.vt.skipTransition(); }
      if (!V.back) return end();
      setTheme(V.from); ttCharts();   // 退回原刊：即時畫面先換回來（這時被原刊快照蓋著看不到），隔兩格再結束過渡，不會閃
      requestAnimationFrame(function () { requestAnimationFrame(end); });
    }
    function ttDone(V) {
      if (V.done) return; V.done = true; V.fin = true; cancelAnimationFrame(V.raf);
      var fin = V.back ? V.from : V.to;
      if (ttCur() !== fin) { setTheme(fin); ttCharts(); }
      if (V.cv.parentNode) V.cv.parentNode.removeChild(V.cv);
      if (TT_RG === V.rg) { if (!V.rg.t0) ttRingOff(true); else if (fin === V.from) ttRingOff(false); }
      document.documentElement.classList.remove('tt-vt');
      if (TV === V) TV = null;
      TTX.s = 1; tt.style.setProperty('--tt-s', 1); [tt, mt].forEach(function (el) { if (el) { el.style.removeProperty('--tt-sky'); el.style.removeProperty('--tt-glow'); } });
      if (ttPh) ttPh.style.opacity = 0;
      setTheme(fin);
      if (fin !== V.from) { try { localStorage.setItem('daybreak.theme', fin); } catch (er) {} ttSettle(tt.querySelector('.tt-knob')); ttSettle(mt && mt.offsetParent ? mt : null); ttDrawRest(V.rest || []); }
    }
    function ttKz(p) { return ttEase(Math.min(1, p / 0.55)); }   // 點一下：滑塊在前半段就到位，晨昏線繼續往外漫
    function pickTheme(v) {
      if (TV) { if (!TV.fin) { var b = v === TV.to ? 1 : 0; ttTw(TV, b, 1150 * Math.abs(b - TV.sp) + 120, ttEase, ttEase); } return; }
      if (v === ttCur()) return;
      if (!document.startViewTransition || matchMedia('(prefers-reduced-motion: reduce)').matches) { setTheme(v); try { localStorage.setItem('daybreak.theme', v); } catch (er) {} ttRedraw(); return; }
      ttTw(ttGo(v), 1, 1000, ttSweep, ttKz);
    }
    var ttDrag = null, ttSkip = false;
    tt.style.touchAction = 'none';
    tt.addEventListener('pointerdown', function (e) { if (e.button) return; ttDrag = { x: e.clientX, w: tt.offsetWidth, id: e.pointerId, on: false }; tt.classList.add('tt-press'); });
    tt.addEventListener('pointermove', function (e) {
      if (!ttDrag) return; var dx = e.clientX - ttDrag.x;
      if (!ttDrag.on) {
        if (Math.abs(dx) < 4) return;
        if (!TV && (!document.startViewTransition || matchMedia('(prefers-reduced-motion: reduce)').matches)) { ttDrag = null; tt.classList.remove('tt-press'); return; }
        if (TV && TV.fin) return;
        ttDrag.on = true; try { tt.setPointerCapture(ttDrag.id); } catch (er) {}
        var V = TV || ttGo(ttCur() === 'dark' ? 'light' : 'dark'); V.tw = null; ttDrag.t0 = TTX.t;
      }
      if (!TV || TV.fin) return;
      var t = ttClamp(ttDrag.t0 + dx / (ttDrag.w / 2)), p = TV.to === 'dark' ? t : 1 - t; TV.tw = null; TV.sp = TV.kp = p;
    });
    function ttEnd() {
      tt.classList.remove('tt-press'); var d = ttDrag; ttDrag = null; if (!d || !d.on) return; ttSkip = true; setTimeout(function () { ttSkip = false; }, 0);
      if (!TV || TV.fin) return; var b = TV.sp >= 0.5 ? 1 : 0; ttTw(TV, b, 160 + 620 * Math.abs(b - TV.sp), ttOut);
    }
    tt.addEventListener('pointerup', ttEnd); tt.addEventListener('pointercancel', ttEnd);
    tt.addEventListener('click', function (e) { if (ttSkip) return; var b = e.target.closest('button'); if (b) pickTheme(b.getAttribute('data-t')); });
    if (mt) mt.addEventListener('click', function () { pickTheme(mt.getAttribute('data-v') === 'dark' ? 'light' : 'dark'); });
    try { setTheme(localStorage.getItem('daybreak.theme') === 'dark' ? 'dark' : 'light'); } catch (e) { setTheme('light'); }
    // 2026-11-09 換語言的轉場（使用者：「語言切換可以做類似的概念嗎」，延續日刊／夜刊的中間狀態）。
    // 語言要重新載入整頁，中英文不會同時存在，所以中間態用「轉譯中」的亂碼：
    // 離開：滑塊跟著走（拉長、到位），畫面上看得到的字逐漸亂碼，同底色的暮色淡入，約 0.52 秒後重新載入；
    // 進入：開機就先蓋著暮色（index.html 開機腳本），新語言畫好、字型載入後，暮色淡出、字從亂碼解碼成新語言，捲動位置接回原處。
    // 亂碼只換同類字（中文換中文、英文換英文、數字換數字），版面寬度不跳；別的程式改過的字（例如數字解碼、倒數）就不再碰
    var LFX = { busy: false }, LFX_POOL = { c: '\u6bd4\u7279\u5e63\u50f9\u683c\u9031\u671f\u93c8\u4e0a\u8cc7\u91d1\u884d\u751f\u54c1\u51fa\u5834\u6846\u67b6\u5f80\u671f\u65b9\u6cd5\u5e02\u5834\u591a\u7a7a\u9802\u5e95\u71b1\u5ea6\u6210\u672c\u7372\u5229\u7c4c\u78bc\u4f9b\u7d66\u77ed\u9577\u6301\u6709\u8005\u6d41\u5165\u6de8\u8b8a\u5316\u7387\u6307\u6578\u8a0a\u865f\u98a8\u96aa\u6ce2\u52d5\u672a\u5be6\u73fe\u9078\u64c7\u6b0a\u5230\u671f\u5c65\u7d04\u4eca\u5929\u65b0\u4e00\u671f\u5224\u8b80\u7d50\u8ad6', n: 'fijlrtI', w: 'mwMW', u: 'ABCDEFGHJKLNOPQRSTUVXYZ', l: 'abcdeghknopqsuvxyz', d: '0123456789' };
    // 英文字母依寬度分組，只換成同一組的字（窄換窄、寬換寬）：亂碼時一行的寬度幾乎不變，段落不會多折一行把版面推下去（使用者 11/09 iPhone 錄影可以看到換語言時版面跳）
    function lfxKind(ch) { var c = ch.charCodeAt(0); if (c >= 0x3400 && c <= 0x9FFF) return 'c'; if (/[0-9]/.test(ch)) return 'd'; if (!/[A-Za-z]/.test(ch)) return ''; return /[fijlrtI]/.test(ch) ? 'n' : /[mwMW]/.test(ch) ? 'w' : ch < 'a' ? 'u' : 'l'; }
    function lfxRand(k) { var p = LFX_POOL[k]; return p.charAt((Math.random() * p.length) | 0); }
    function lfxNodes(max) {
      var out = [], H = innerHeight, W = innerWidth, w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null), n, rg = document.createRange();
      while ((n = w.nextNode()) && out.length < max) {
        var s = n.nodeValue; if (!s || !/\S/.test(s)) continue;
        var p = n.parentElement; if (!p || /^(SCRIPT|STYLE|NOSCRIPT|TITLE|OPTION)$/.test(p.tagName) || p.closest('#lang, #m-lang, .clock, .lfx-skip')) continue;
        rg.selectNodeContents(n); var r = rg.getBoundingClientRect(); if (!r.width || r.bottom < 0 || r.top > H || r.right < 0 || r.left > W) continue;
        var a = Array.from(s); out.push({ n: n, s: s, a: a, k: a.map(lfxKind), last: s });
      }
      return out;
    }
    function lfxPaint(items, scr) {   // scr(it, i) → 這個字現在要不要亂碼
      items.forEach(function (it) {
        if (it.gone || it.n.nodeValue !== it.last) { it.gone = true; return; }
        var o = ''; for (var i = 0; i < it.a.length; i++) o += it.k[i] && scr(it, i) ? lfxRand(it.k[i]) : it.a[i];
        it.n.nodeValue = o; it.last = o;
      });
    }
    function lfxLabel(from, to, p) {   // 按鈕上的字：前段亂碼、後段收斂成新字
      var a = Array.from(p < .5 ? from : to); return a.map(function (ch, i) { var k = lfxKind(ch); return k && Math.random() > Math.max(0, (p - .35) / .5) ? lfxRand(k) : ch; }).join('');
    }
    // 2026-11-09 使用者：「中間空白的時間太長，能不能沒有空白時間，直接亂碼到另一個語言」→ 不再用暮色蓋住重新載入：
    // 按下時先存一份「看得到的畫面」快照（畫面外的區塊只留空殼和高度，畫布轉成圖），新頁面一開頭就把這份快照擺在 shadow DOM 裡、字持續亂碼（index.html），
    // 新語言畫好後直接換成新頁面（也是亂碼）再解碼，整段畫面一直都是跳動的字，沒有空白。shadow DOM 和頁面隔開，不會被搜尋索引、目錄等全頁查詢抓到
    function lfxSnap(l) {
      var app = $('.app'); if (!app) return '';
      var H = innerHeight, c = app.cloneNode(true);
      (function walk(o, k) {
        var oc = o.children, kc = k.children;
        for (var i = oc.length - 1; i >= 0; i--) {
          var oe = oc[i], ke = kc[i]; if (!ke) continue;
          var tag = oe.tagName.toUpperCase();
          if (tag === 'SCRIPT' || tag === 'NOSCRIPT' || tag === 'TEMPLATE') { ke.remove(); continue; }
          var cs = getComputedStyle(oe); if (cs.display === 'none') { ke.remove(); continue; }
          var r = oe.getBoundingClientRect();
          if (cs.position !== 'fixed' && cs.position !== 'sticky' && (r.bottom < -80 || r.top > H + 80)) { ke.innerHTML = ''; ke.style.cssText += ';height:' + r.height + 'px;min-height:0;max-height:none;box-sizing:border-box;overflow:hidden'; continue; }
          if (tag === 'CANVAS') { try { var im = document.createElement('img'); im.src = oe.toDataURL('image/jpeg', 0.7); im.className = oe.className; im.style.cssText = 'display:block;width:' + r.width + 'px;height:' + r.height + 'px'; ke.replaceWith(im); } catch (e) {} continue; }
          if (/^(block|list-item|flex|grid|flow-root|table-cell)$/.test(cs.display) && r.height && Array.prototype.some.call(oe.childNodes, function (x) { return x.nodeType === 3 && /\S/.test(x.nodeValue); })) ke.style.cssText += ';height:' + r.height + 'px;min-height:0;max-height:none;box-sizing:border-box;overflow:hidden;overflow:clip';   // 直接含字的區塊鎖住高度：亂碼後折行不同也不會把下面推動（用 clip 不用 hidden：hidden 會讓彈性排版的項目可以縮到 0，頂部導航的字會被擠成一個字）
          if (tag !== 'SVG') walk(oe, ke);
        }
      })(app, c);
      c.querySelectorAll('#lang button').forEach(function (x) { x.setAttribute('aria-pressed', x.getAttribute('data-l') === l); });
      var ml = c.querySelector('#m-lang'); if (ml) ml.textContent = l === 'en' ? '中文' : 'EN';
      return c.outerHTML;
    }
    function pickLang(l) {
      if (l === LANG || LFX.busy) return;
      try { localStorage.setItem('daybreak.lang', l); } catch (er) {}
      if (reduced) { location.reload(); return; }
      LFX.busy = true;
      var lk = function (sel) { var e = document.querySelector(sel); return e ? e.href : ''; };
      var fx = { t: Date.now(), y: window.scrollY, w: document.documentElement.clientWidth, lang: l, theme: document.documentElement.getAttribute('data-theme') || '', bc: document.body.className, css: lk('link[rel=stylesheet][href*="app.css"]'), fonts: lk('link[rel=stylesheet][href*="fonts.googleapis"]') };
      var h = ''; try { h = lfxSnap(l); } catch (e) {}
      var save = function () { try { sessionStorage.setItem('daybreak.lfx', JSON.stringify(Object.assign({ h: h.length < 2.5e6 ? h : '' }, fx))); } catch (e) { try { sessionStorage.setItem('daybreak.lfx', JSON.stringify(fx)); } catch (e2) {} } };
      var lg = $('#lang'), ml = $('#m-lang'), mlFrom = ml ? ml.textContent : '', mlTo = l === 'en' ? '中文' : 'EN';
      if (lg) { lg.classList.add('lfx-go'); lg.classList.toggle('to-zh', l === 'zh'); setTimeout(function () { lg.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x.getAttribute('data-l') === l); }); }, 150); }
      var items = lfxNodes(800), t0 = performance.now(), D = 300, fr = 0;
      (function f(now) {
        var p = Math.min(1, (now - t0) / D), q = Math.min(.85, p * 1.2);
        if (fr++ % 2 === 0) lfxPaint(items, function () { return Math.random() < q; });   // 每兩格換一次，亂碼不會閃得太躁
        if (ml) ml.textContent = lfxLabel(mlFrom, mlTo, p);
        if (p < 1) requestAnimationFrame(f); else { save(); location.reload(); }
      })(t0);
    }
    langInHook = langIn;
    function langIn() {
      var d = document.documentElement, g = window.DAYBREAK_LFX_GHOST; if (!d.classList.contains('lfx-in') && !g) return;
      var unghost = function () { if (g) { g.remove(); g = window.DAYBREAK_LFX_GHOST = null; d.classList.remove('lfx-in', 'lfx-lift'); return true; } return false; };
      var fx = null; try { fx = JSON.parse(sessionStorage.getItem('daybreak.lfx') || 'null'); sessionStorage.removeItem('daybreak.lfx'); } catch (e) {}
      var done = false, lift = function () { d.classList.add('lfx-lift'); setTimeout(function () { d.classList.remove('lfx-in', 'lfx-lift'); }, 700); };
      var run = function () {
        if (done) return; done = true;
        if (fx && fx.y) window.scrollTo(0, fx.y);
        var items = lfxNodes(800), t0 = performance.now(), D = 820;
        items.forEach(function (it) { var L = Math.max(1, it.a.length); it.r = it.a.map(function (_, i) { return 0.12 + 0.35 * (i / L) + Math.random() * 0.5; }); });   // 每個字各自在 0.12～0.97 之間解開，大致由左到右
        lfxPaint(items, function () { return true; });
        [$('#lang'), $('#m-lang')].forEach(function (el) { if (el) { el.classList.remove('lfx-land'); void el.offsetWidth; el.classList.add('lfx-land'); } });
        if (!unghost()) requestAnimationFrame(lift);
        setTimeout(function () { d.classList.remove('lfx-came'); }, 4000);   // 有快照：同一格拿掉快照、換成已經亂碼的新頁面，直接接著解碼；沒有快照才用暮色淡出
        var fr = 0;
        (function f(now) {
          var p = Math.min(1, (now - t0) / D);
          if (fr++ % 2 === 0 || p >= 1) lfxPaint(items, function (it, i) { return p < it.r[i]; });
          if (p < 1) requestAnimationFrame(f);
        })(t0);
      };
      (document.fonts ? document.fonts.ready : Promise.resolve()).then(function () { requestAnimationFrame(function () { requestAnimationFrame(run); }); });
      setTimeout(function () { if (!done) { done = true; if (fx && fx.y) window.scrollTo(0, fx.y); if (!unghost()) lift(); setTimeout(function () { d.classList.remove('lfx-came'); }, 4000); } }, 3500);   // 保險：字型一直沒載完也不要一直蓋著（照樣接回捲動位置）
    }
    $('#lang').querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x.getAttribute('data-l') === LANG); });
    $('#lang').addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) pickLang(b.getAttribute('data-l')); });
    var ml = $('#m-lang'); if (ml) { ml.textContent = LANG === 'en' ? '中文' : 'EN'; ml.addEventListener('click', function () { pickLang(LANG === 'en' ? 'zh' : 'en'); }); }
    staticText(); ttIcons();
    var pad = function (x) { return ('0' + x).slice(-2); };
    function tick() { var t = new Date(); var nx = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate(), 0, 15));   /* 2026-11-06 日報任務改 UTC 00:15 開始 */ if (nx <= t) nx = new Date(+nx + 864e5); var d = Math.floor((nx - t) / 1000); $('#nxt').textContent = 'T−' + pad(Math.floor(d / 3600)) + ':' + pad(Math.floor(d % 3600 / 60)) + ':' + pad(d % 60); }
    tick(); setInterval(tick, 1000);
    var fs = $('#fs'); fs.addEventListener('click', function () { var d = document; try { if (d.fullscreenElement) d.exitFullscreen(); else d.documentElement.requestFullscreen().catch(function () {}); } catch (e) {} });
    var c = D.price.bar;
    $('#tk-px').textContent = fmt.usd(c.c);
    $('#tk-chg').textContent = fmt.pct(c.chg_pct, 2); $('#tk-chg').className = 'chip ' + (c.chg_pct >= 0 ? 'up' : 'down');
    $('#tk-stance').innerHTML = '<i></i>' + esc(N ? N.stance.label : '—');
    $('#tk-asof').textContent = fmt.md(D.meta.bar_date) + _t(' 收盤 · UTC');
    $('#ed-date').textContent = D.meta.bar_date + (N ? _t(' · 第 ') + N.edition + _t(' 期') : '');
    $('#ed-gen').textContent = _t('資料 ') + (D.meta.generated_utc || '').slice(11, 16) + _t(' UTC 產出');
  }

  // 新聞分類：notes 裡固定用中文分類（篩選用），英文版只在顯示時換字
  var CAT_EN = { '宏觀': 'Macro', '資金': 'Flows', '衍生品': 'Derivatives', '鏈上': 'On-chain', '監管': 'Regulation', '產業': 'Industry', '機構': 'Institutions', '地緣': 'Geopolitics' };
  function catT(c) { return LANG === 'en' && CAT_EN[c] || c; }
  function load(u) { return fetch(u, { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); }); }
  /* 2026-11-09 載入速度：網站讀 data/site.json（內容和 latest.json 相同，數字表改成按欄存放，gzip 約小 30%；見 pipeline/site_data.py）。
     下載後還原成原本的 [[日, 值…], …]，其他程式不用改。還原規則和 site_data.py 的 unpack() 相同（改一邊要改另一邊）。
     site.json 讀不到或格式不對就退回 latest.json */
  function unpack(o) {
    if (Array.isArray(o)) { for (var i = 0; i < o.length; i++) o[i] = unpack(o[i]); return o; }
    if (o && typeof o === 'object') {
      var r = o['$r'];
      if (r && o.c) { var n = o.c[0].length, out = new Array(n), x = r[0]; for (var j = 0; j < n; j++) { if (j) x += r.length > 1 ? r[1] : o.dx[j - 1]; var row = [x]; for (var k = 0; k < o.c.length; k++) row.push(o.c[k][j]); out[j] = row; } return out; }
      for (var key in o) if (Object.prototype.hasOwnProperty.call(o, key)) o[key] = unpack(o[key]);
    }
    return o;
  }
  function loadData(site, full) { return load(site).then(function (d) { d = unpack(d); if (!d || !d.meta || !d.meta.bar_date) throw new Error(site); return d; }).catch(function () { return load(full); }); }
  // 英文版讀 data/notes.en.json（每日任務與中文同時寫）；沒有或日期比中文舊時，退回中文並標示
  /* 2026-11-06 使用者要求：整期一起換。新數字（latest.json）比判讀（notes.json）新、而且數字產出不到 3 小時：
     先讀 latest.prev.json（上一份數字，和判讀同一天），整期顯示上一期，頂端說明新數字已到、判讀撰寫中，可以點「先看新數字」。
     判讀寫好後每 2 分鐘檢查一次，出現「新一期已出」。超過 3 小時判讀還沒好（任務失敗）就直接顯示新數字，每段判讀標「上一期」 */
  var HOLD_H = 3, SEE_NEW = 'daybreak.seenew';
  function ss(k, v) { try { if (v === undefined) return sessionStorage.getItem(k); sessionStorage.setItem(k, v); } catch (e) { return null; } }
  function holdPrev(d, nn) {
    var noHold = false; try { noHold = localStorage.getItem('daybreak.nohold') === '1'; } catch (e) {}   // 截圖工具（ops/post/site_shot.py、ops/replies/site_cards.py）一律看最新數字
    if (noHold || !d || !nn || nn.date >= d.meta.bar_date || ss(SEE_NEW) === d.meta.bar_date) return Promise.resolve(null);
    var age = (Date.now() - Date.parse(d.meta.generated_utc || '')) / 36e5;
    if (!(age >= 0 && age < HOLD_H)) return Promise.resolve(null);
    return loadData('data/site.prev.json', 'data/latest.prev.json').then(function (p) { return p && p.meta && p.meta.bar_date === nn.date ? p : null; }).catch(function () { return null; });
  }
  function heldBar() {
    var stale = !HELD && N && N.stale;
    if (!HELD && !stale) return '';
    var nd = HELD ? HELD.date : D.meta.bar_date, od = N.date;
    return '<div class="held" id="held" role="status"><span class="chip flare"><i></i>' + (HELD ? _T('判讀撰寫中', 'Commentary in progress') : _T('判讀還沒更新', 'Commentary not updated')) + '</span><span>' +
      (HELD ? _T(fmt.md(nd) + ' 收盤的新數字已經到了，判讀還在寫（通常 15 分鐘內完成）。為了數字和判讀對得上，現在整期顯示 ' + fmt.md(od) + ' 這一期。', 'The ' + fmt.md(nd) + ' close is in, but the commentary is still being written (usually within 15 minutes). So numbers and commentary match, the whole ' + fmt.md(od) + ' edition is shown for now.')
        : _T('數字是 ' + fmt.md(nd) + ' 收盤，判讀還是 ' + fmt.md(od) + ' 那一期；標「上一期」的文字請對照當天的數字看。', 'Numbers are from the ' + fmt.md(nd) + ' close, but the commentary is still the ' + fmt.md(od) + ' edition; text marked “previous edition” refers to that day.')) +
      '</span>' + (HELD ? '<button type="button" id="see-new">' + _T('先看新數字', 'Show new numbers') + '</button>' : '') + '</div>';
  }
  function watchNotes() {   // 判讀寫好就提示換成新一期
    var t = setInterval(function () {
      load('data/notes.json').then(function (n) {
        if (!n || n.date !== HELD.date) return; clearInterval(t);
        var h = $('#held'); if (h) h.innerHTML = '<span class="chip up"><i></i>' + _T('新一期已出', 'New edition is out') + '</span><span>' + _T(fmt.md(HELD.date) + ' 的判讀寫好了。', 'The ' + fmt.md(HELD.date) + ' commentary is ready.') + '</span><button type="button" id="see-new">' + _T('更新', 'Refresh') + '</button>';
      }).catch(function () {});
    }, 120000);
  }
  document.addEventListener('click', function (e) { if (e.target && e.target.id === 'see-new') { if (HELD) ss(SEE_NEW, HELD.date); location.reload(); } });
  Promise.all([loadData('data/site.json', 'data/latest.json'), load('data/notes.json').catch(function () { return null; }), LANG === 'en' ? load('data/notes.en.json').catch(function () { return null; }) : null]).then(function (a) {
    var nz = a[1], ne = a[2], nn = LANG === 'en' && ne && (!nz || ne.date >= nz.date) ? ne : nz;
    return holdPrev(a[0], nn).then(function (p) { if (p) { HELD = { date: a[0].meta.bar_date }; a[0] = p; } return a; });
  }).then(function (a) {
    var nz = a[1], ne = a[2], nn = LANG === 'en' && ne && (!nz || ne.date >= nz.date) ? ne : nz;
    ZH_ONLY = LANG === 'en' && !!nn && nn === nz;
    D = a[0]; N = nn && nn.date === D.meta.bar_date ? nn : (nn ? Object.assign({}, nn, { stale: true }) : null);
    var hb = heldBar(); if (hb) $('#view').insertAdjacentHTML('beforebegin', hb);
    if (HELD) watchNotes();
    shell();
    renderAll();
    var start = location.hash.slice(1);
    // 2026-11-09 修：從換語言進來（開機腳本加了 lfx-came）時，捲動位置由 langIn 接回原處，這裡只切到那一版、不回頂也不對齊。
    // 原本手機版換版會「回頂」（toTop 鎖住捲動、80／250／500 毫秒後再拉回頂端），和 langIn 接回的位置互相拉扯：
    // 使用者看到畫面先停在原位、頂部列不見，接著又被拉回頂端、整頁跳一下
    var came = document.documentElement.classList.contains('lfx-came');
    if (start && start !== 'overview' && (/^\w+\/[\w-]+$/.test(start) || (/^[\w-]+$/.test(start) && $('#pg-' + start)))) {
      if (came) { var pg0 = start.split('/')[0]; if ($('#pg-' + pg0)) activate(pg0); }
      else {
        go(start);   // 字型載入後版面會變高，載完再對齊一次（使用者已自行捲動就不動）
        var y0 = window.scrollY; if (document.fonts) document.fonts.ready.then(function () { if (Math.abs(window.scrollY - y0) < 2) go(start); });
      }
    } else { if (!came) window.scrollTo(0, 0); activate(ROUTES[0][0]); }
    if (langInHook) langInHook();
  }).catch(function (e) { $('#view').innerHTML = _t('<p class="err">資料載入失敗：') + esc(e.message) + _t('。請稍後重新整理。</p>'); });
});
