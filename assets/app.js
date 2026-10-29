/* 破曉 Daybreak — 前端（無外部套件）。讀 data/latest.json（每日資料管線）與 data/notes.json（每日結論）。 */
(window.DAYBREAK_BOOT || Promise.resolve()).then(function () {
  'use strict';
  var D = null, N = null, H = [], ZH_ONLY = false;
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

  /* ---------------- Chart kit ---------------- */
  var mounted = [];
  function mount(el, draw) { if (!el) return; el._draw = draw; mounted.push(el); draw(el); }
  var ro = window.ResizeObserver ? new ResizeObserver(function (es) {
    es.forEach(function (e) { var el = e.target; if (el._w !== el.clientWidth && el._draw) { el._w = el.clientWidth; el._draw(el); } });
  }) : null;
  function observe(el) { if (ro && el) { el._w = el.clientWidth; ro.observe(el); } }

  function niceStep(span, n) { var r = span / n, p = Math.pow(10, Math.floor(Math.log10(r))), m = r / p; return (m < 1.5 ? 1 : m < 3.5 ? 2 : m < 7.5 ? 5 : 10) * p; }
  function svgEl(W, Ht, inner, label) { return '<svg viewBox="0 0 ' + W + ' ' + Ht + '" width="' + W + '" height="' + Ht + '" role="img" aria-label="' + esc(label || '') + '">' + inner + '</svg>'; }
  function bisect(a, x) { var lo = 0, hi = a.length - 1; while (hi - lo > 1) { var m = (lo + hi) >> 1; if (a[m][0] < x) lo = m; else hi = m; } return Math.abs(a[lo][0] - x) <= Math.abs(a[hi][0] - x) ? lo : hi; }
  function animateLines(el) {
    if (reduced || el._drawn) return; el._drawn = true;
    // 2026-10-14：虛線（推測、還沒發生的部分）不套描線動畫，動畫的 stroke-dasharray 會蓋掉虛線樣式、讓它變成實線
    el.querySelectorAll('path.ln:not([stroke-dasharray])').forEach(function (p) { try { var L = p.getTotalLength(); p.style.setProperty('--len', L); p.classList.add('draw'); } catch (e) {} });
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
  function lineChart(el, cfg) {
    var W = Math.max(280, el.clientWidth), Ht = cfg.h || (W < 520 ? 210 : 260);
    var ML = cfg.ml || 8, MR = cfg.mr || 58, MT = 14, MB = 24, pw = W - ML - MR, ph = Ht - MT - MB;
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
    if (all2.length) { var T2 = function (v) { return cfg.log2 ? Math.log10(v) : v; }, v2 = all2.map(function (p) { return T2(p[1]); }), l2 = Math.min.apply(null, v2), h2 = Math.max.apply(null, v2), p2 = (h2 - l2) * 0.08 || 1; l2 -= p2; h2 += p2; Y2 = function (v) { return MT + (1 - (T2(v) - l2) / (h2 - l2)) * ph; }; }
    var s = '', yf = cfg.yFmt || function (v) { return fmt.k(v); };
    // y grid
    var ticks = [];
    if (lg) { [0.1, 0.2, 0.3, 0.5, 1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1e3, 2e3, 5e3, 1e4, 2e4, 5e4, 1e5, 2e5, 5e5, 1e6].forEach(function (t) { if (T(t) >= tl && T(t) <= th) ticks.push(t); }); if (ticks.length > 7) ticks = ticks.filter(function (t, i) { return i % 2 === 0; }); }
    else { var st = niceStep(th - tl, W < 520 ? 3 : 4); for (var t = Math.ceil(tl / st) * st; t <= th + 1e-9; t += st) ticks.push(+t.toFixed(10)); }
    ticks.forEach(function (t) { var y = Y(t); s += '<line class="gl" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (y + 3.5).toFixed(1) + '">' + yf(t) + '</text>'; });
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
    } else (cfg.xticks || []).forEach(function (t) { s += '<text class="ax" x="' + X(t[0]).toFixed(1) + '" y="' + (Ht - 6) + '" text-anchor="middle">' + esc(t[1]) + '</text>'; });
    // vertical bands & lines
    (cfg.vbands || []).forEach(function (b) { var a = Math.max(ML, X(b.x0)), z = Math.min(ML + pw, X(b.x1)); if (z > a) s += '<rect x="' + a.toFixed(1) + '" y="' + MT + '" width="' + (z - a).toFixed(1) + '" height="' + ph + '" fill="' + (b.color || 'var(--flare-dim)') + '"/>' + (b.label ? '<text class="ax" x="' + (a + 6).toFixed(1) + '" y="' + (MT + 12) + '">' + esc(b.label) + '</text>' : ''); });
    (cfg.vlines || []).concat(sigV(el)).forEach(function (v) { var xx = X(v.x); if (xx < ML || xx > ML + pw) return; s += '<line x1="' + xx.toFixed(1) + '" x2="' + xx.toFixed(1) + '" y1="' + MT + '" y2="' + (MT + ph) + '" stroke="var(--ink-3)" stroke-dasharray="2 4" stroke-width="1"/>' + (v.label ? '<text class="ax" x="' + (xx > ML + pw - 70 ? xx - 5 : xx + 5).toFixed(1) + '" y="' + (MT + ph - 6) + '"' + (xx > ML + pw - 70 ? ' text-anchor="end"' : '') + '>' + esc(v.label) + '</text>' : ''); });
    (cfg.hbands || []).forEach(function (b) { var a = Math.max(MT, Y(b.y1)), z = Math.min(MT + ph, Y(b.y0)); if (z <= a) return; s += '<rect x="' + ML + '" y="' + a.toFixed(1) + '" width="' + pw + '" height="' + Math.max(1, z - a).toFixed(1) + '" fill="' + b.color + '"/>'; });
    // refs
    (cfg.refs || []).forEach(function (r) { var y = Y(r.y); if (y < MT - 2 || y > MT + ph + 2) return; s += '<line class="ref" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '" stroke="' + r.color + '"/>'; if (r.label) s += '<text class="reflab" x="' + (ML + 6) + '" y="' + (y + (r.below ? 13 : -5)).toFixed(1) + '" fill="' + r.color + '">' + esc(r.label) + '</text>'; });
    // series
    var defs = '';
    cfg.series.forEach(function (sr, si) {
      var pts = sr.data.filter(function (p) { return p[1] != null; }); if (pts.length < 2) return;
      var Yf = sr.y2 ? Y2 : Y, dpath = sr.smooth ? smoothPath(pts.map(function (p) { return [X(p[0]), Yf(p[1])]; })) : pts.map(function (p, i) { return (i ? 'L' : 'M') + X(p[0]).toFixed(1) + ',' + Yf(p[1]).toFixed(1); }).join('');
      if (sr.area) { var gid = 'g' + Math.random().toString(36).slice(2, 8); defs += '<linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + sr.color + '" stop-opacity=".28"/><stop offset="1" stop-color="' + sr.color + '" stop-opacity="0"/></linearGradient>'; s += '<path d="' + dpath + 'L' + X(pts[pts.length - 1][0]).toFixed(1) + ',' + (MT + ph) + 'L' + X(pts[0][0]).toFixed(1) + ',' + (MT + ph) + 'Z" fill="url(#' + gid + ')"/>'; }
      s += '<path class="ln" d="' + dpath + '" stroke="' + sr.color + '" stroke-width="' + (sr.w || 2) + '"' + (sr.dash ? ' stroke-dasharray="' + sr.dash + '"' : '') + ' style="animation-delay:' + (si * 0.12) + 's"/>';
      if (sr.end !== false) { var lp = pts[pts.length - 1]; s += '<circle cx="' + X(lp[0]).toFixed(1) + '" cy="' + Yf(lp[1]).toFixed(1) + '" r="4" fill="' + sr.color + '" stroke="var(--deck)" stroke-width="2"/>'; }
    });
    (cfg.marks || []).forEach(function (m) { var xx = X(m.x), yy = Y(m.y); s += '<circle cx="' + xx.toFixed(1) + '" cy="' + yy.toFixed(1) + '" r="4.5" fill="var(--deck)" stroke="' + (m.color || 'var(--flare)') + '" stroke-width="2"/>' + (m.label ? '<text class="reflab" x="' + (xx + (m.left ? -8 : 8)).toFixed(1) + '" y="' + (yy + (m.below ? 15 : -8)).toFixed(1) + '" fill="' + (m.color || 'var(--flare)') + '"' + (m.left ? ' text-anchor="end"' : '') + '>' + esc(m.label) + '</text>' : ''); });
    s += '<line class="xh" x1="0" x2="0" y1="' + MT + '" y2="' + (MT + ph) + '" visibility="hidden"/><g class="hdots"></g><rect class="hit" x="' + ML + '" y="' + MT + '" width="' + pw + '" height="' + ph + '"/>';
    el.innerHTML = svgEl(W, Ht, '<defs>' + defs + '</defs>' + s, cfg.aria);
    animateLines(el);
    var svg = el.querySelector('svg'), xh = svg.querySelector('.xh'), dots = svg.querySelector('.hdots'), hit = svg.querySelector('.hit');
    function move(ev) {
      var r = svg.getBoundingClientRect(), mx = (ev.clientX - r.left) * W / r.width, xv = x0 + (mx - ML) / pw * (x1 - x0), rows = [], g = '', xs = null;
      cfg.series.forEach(function (sr) {
        var pts = sr.data.filter(function (p) { return p[1] != null; }); if (!pts.length || sr.tip === false) return;
        var i = bisect(pts, xv), p = pts[i]; if (xs == null) xs = p[0];
        if (Math.abs(p[0] - xv) > (cfg.tipGap || 1e9)) return;   // 這條線在游標附近沒有資料（例如外推線）就不列
        g += '<circle cx="' + X(p[0]).toFixed(1) + '" cy="' + (sr.y2 ? Y2 : Y)(p[1]).toFixed(1) + '" r="4" fill="' + sr.color + '" stroke="var(--deck)" stroke-width="2"/>';
        rows.push('<div class="r"><i style="background:' + sr.color + '"></i><span>' + esc(sr.name) + '</span><b>' + (sr.fmt || cfg.tipFmt || yf)(p[1]) + '</b></div>');
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
      s += '<g class="cd" data-i="' + i + '"><rect x="' + (ML + i * bw) + '" y="' + MT + '" width="' + bw + '" height="' + ph + '" fill="transparent"/><line x1="' + x.toFixed(1) + '" x2="' + x.toFixed(1) + '" y1="' + Y(r[2]).toFixed(1) + '" y2="' + Y(r[3]).toFixed(1) + '" stroke="' + col + '" stroke-width="1.4"/>' +
        '<rect x="' + (x - w / 2).toFixed(1) + '" y="' + Y(Math.max(r[1], r[4])).toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + Math.max(1.5, Math.abs(Y(r[1]) - Y(r[4]))).toFixed(1) + '" rx="1.5" fill="' + col + '"/></g>';
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
  function panel(cls, title, src, body, extra) { return '<section class="panel ' + cls + '"><div class="panel-h"><h2>' + title + '</h2>' + (extra || '') + (src ? '<span class="src">' + src + '</span>' : '') + '</div>' + body + '</section>'; }
  function readBar(key, bare) {
    var m = N && N.modules && N.modules[key]; if (!m) return '';
    if (ZH_ONLY) return '<div class="read' + (bare ? ' bare' : '') + '" data-k="' + key + '">' + (bare ? '' : '<span class="tag">TODAY’S READ</span>') + '<div><p class="note">The written commentary for this edition is available in Chinese only. All numbers and the readings under them are in English.</p></div></div>';
    return '<div class="read' + (bare ? ' bare' : '') + '" data-k="' + key + '">' + (bare ? '' : _t('<span class="tag">今日判讀<small>TODAY’S READ</small></span>')) + '<div><p>' + esc(m.lead) + '</p><ul>' + (m.points || []).map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul></div></div>';
  }
  function kpi(k, v, n, bar, cls) { return '<div class="kpi"><span class="k">' + k + '</span><span class="v' + (cls ? ' ' + cls : '') + '">' + v + '</span>' + (n ? '<span class="n">' + n + '</span>' : '') + (bar != null ? '<span class="bar"><i style="width:' + Math.max(2, Math.min(100, bar)).toFixed(1) + '%"></i></span>' : '') + '</div>'; }
  function legend(items) { return '<div class="legend">' + items.map(function (it) { return '<span style="color:' + it[1] + '"><i class="' + (it[2] || '') + '"></i><b style="color:var(--ink-2);font-weight:400">' + esc(it[0]) + '</b></span>'; }).join('') + '</div>'; }
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

  function runwaySvg() { /* 收盤到各出場線的距離（對數刻度） */
    var c = D.price.bar.c, S = D.exit.status, F = D.exit.framework, lo = 55000, hi = 240000, W = 1000, Ht = 150, ML = 20, MR = 20, pw = W - ML - MR, y = 78;
    var X = function (v) { return ML + (Math.log(v) - Math.log(lo)) / (Math.log(hi) - Math.log(lo)) * pw; }, s = '';
    s += '<defs><linearGradient id="rw" x1="0" x2="1"><stop offset="0" stop-color="var(--orbit)"/><stop offset="1" stop-color="var(--flare)"/></linearGradient></defs>';
    s += '<line x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y + '" y2="' + y + '" stroke="var(--line-2)" stroke-width="2"/>';
    [60000, 80000, 100000, 150000, 200000].forEach(function (t) { s += '<text class="ax" x="' + X(t).toFixed(1) + '" y="' + (Ht - 6) + '" text-anchor="middle" style="font-family:var(--f-mono);font-size:11px" fill="var(--ink-3)">' + fmt.k(t) + '</text>'; });
    s += '<rect x="' + X(S.sma200).toFixed(1) + '" y="' + (y - 3) + '" width="' + (X(c) - X(S.sma200)).toFixed(1) + '" height="6" rx="3" fill="var(--orbit)" opacity=".5"/>';
    s += '<rect x="' + X(c).toFixed(1) + '" y="' + (y - 3) + '" width="' + (X(F.ladder[0]) - X(c)).toFixed(1) + '" height="6" rx="3" fill="url(#rw)" opacity=".35"/>';
    F.ladder.forEach(function (v, i) { s += '<rect x="' + (X(v) - 2).toFixed(1) + '" y="' + (y - 14) + '" width="4" height="28" rx="2" fill="var(--flare)" opacity="' + (1 - i * .08).toFixed(2) + _t('"><title>出場第 ') + (i + 1) + _t(' 階 ') + fmt.usd(v) + '</title></rect>'; });
    s += '<text x="' + X(F.ladder[0]).toFixed(1) + '" y="' + (y - 24) + _t('" style="font-size:12px" fill="var(--flare)">出場階梯 125K–215K（8 階）</text>');
    var mk = function (v, lab, col, up) { var xx = X(v); return '<line x1="' + xx.toFixed(1) + '" x2="' + xx.toFixed(1) + '" y1="' + (y - 12) + '" y2="' + (y + 12) + '" stroke="' + col + '" stroke-width="2"/><text x="' + xx.toFixed(1) + '" y="' + (up ? y - 22 : y + 30) + '" text-anchor="middle" style="font-size:12px" fill="' + col + '">' + lab + '</text>'; };
    s += mk(S.sma200, _t('避險線 ') + fmt.k(S.sma200) + _t('（') + fmt.pct((S.sma200 / c - 1) * 100, 0) + _t('）'), 'var(--orbit)', true);
    s += mk(S.k075_price, 'MVRV 0.75 ' + fmt.k(S.k075_price) + _t('（') + fmt.pct((S.k075_price / c - 1) * 100, 0) + _t('）'), 'var(--rose)', false);
    s += '<circle cx="' + X(c).toFixed(1) + '" cy="' + y + '" r="14" fill="var(--flare)" opacity=".18"><animate attributeName="r" values="11;18;11" dur="3s" repeatCount="indefinite"/></circle><circle cx="' + X(c).toFixed(1) + '" cy="' + y + '" r="7" fill="var(--ink)" stroke="var(--deck)" stroke-width="2.5"/><text x="' + X(c).toFixed(1) + '" y="' + (y + 32) + _t('" text-anchor="middle" style="font-family:var(--f-mono);font-size:13px" fill="var(--ink)">收盤 ') + fmt.k(c) + '</text>';
    return '<svg viewBox="0 0 ' + W + ' ' + Ht + _t('" role="img" aria-label="收盤到避險線與出場階梯的距離">') + s + '</svg>';
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
    mount(m, function () { var cw = m.clientWidth - parseFloat(getComputedStyle(m).paddingLeft) * 2; big.style.fontSize = ''; var cur = big.textContent; big.textContent = fin; var fs = parseFloat(getComputedStyle(big).fontSize), w = big.offsetWidth; big.textContent = cur; if (w > 0) big.style.fontSize = Math.min(fs * cw / w * 0.97, 560) + 'px'; });
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
        return '<tr><td><span class="mk-s' + (e.ok ? ' ok' : '') + '">' + (e.ok ? '✓' : '×') + '</span><b>' + esc(_T(e.label, (EV_EN[e.id] || [])[0] || e.label)) + '</b></td><td class="num">' + v + '</td><td>' + esc(_T(e.cond, (EV_EN[e.id] || [])[1] || e.cond)) + '</td><td class="num">' + fmt.md(e.date) + '</td></tr>';
      }).join('') + '</tbody></table></div>' : '') + evCharts(ev) +
      '<div class="rules">' + lines.map(function (l) { return '<div class="rule"><span class="t"><span class="mk-s">' + l[0] + '</span>' + l[1] + '</span><span class="d">' + l[2] + '</span><span></span></div>'; }).join('') + '</div>' +
      _t('<p class="note">判定規則：轉換期＝燈號一（投降）✓ 且收盤在上升的 200 日均線之上（上升＝高於 30 天前）；牛市＝燈號一 ✓ 且收盤連 30 日在上升的 200 日均線之上，成立後單向鎖定；退回熊市＝轉換期中連 5 日收在 200 日均線下，牛市則需連 30 日在下降的 200 日均線下。佐證燈號只顯示證據強弱，不參與判定。</p>') +
      _t('<p class="note">限制：2014 年起只有 3–4 輪週期可回測。這條價格規則在候選標準中假訊號最少，但 2019 年中一樣誤判為牛市，之後跌了近五成；沒有任何規則能同時又快又少假訊號。交易所供給 90 日轉負原為必要條件，回測顯示換視窗長度就失效、地址歸屬會事後修正（有前視偏差），且 2025 年 99% 的日子成立，2026-10-09 起降為佐證。牛市條件在頂部附近也會亮，不是賣出訊號；市場階段只是標籤，不連動出場框架。</p>');
  }
  // 以下三塊由每日結論任務寫進 notes.json；不是當天的就標「上一期」
  /* 資料管線寫進 latest.json 的中文標籤，英文版在這裡對照 */
  var EV_EN = { mom12: ['12-month momentum', 'Close above its level a year ago'], mvrv1y: ['MVRV vs 1-year mean', 'MVRV above its own 1-year average'],
    rcgrowth: ['Capital inflow', 'Realized cap 30-day growth is positive'], xs90: ['Exchange supply', '90-day change is negative'], sth: ['Short-term holder cost', 'Close above short-term holder cost (bitcoin-data)'],
    tmm: ['STH cost vs true market mean', 'Short-term holder cost above the true market mean (bitcoin-data, ~7 days late)'] };
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
    return '<div class="evcharts">' + EV_ORDER.filter(function (id) { return by[id]; }).map(function (id) {
      var e = by[id], PX = [_T('BTC 價格', 'BTC price'), 'var(--ink-3)'], PX2 = [_T('BTC 價格（另一刻度）', 'BTC price (own scale)'), 'var(--ink-3)'], STH = [_T('短期持有者成本', 'STH cost'), 'var(--s2)'];
      var lg = { tmm: [STH, [_T('真實市場均價', 'True market mean'), 'var(--s3)'], PX, [_T('近 30 日速度外推', 'Extrapolated at 30-day pace'), 'var(--ink-3)', 'dash']], sth: [STH, PX],
        mom12: [PX, [_T('一年前的價格', 'Price a year earlier'), 'var(--s2)'], [_T('未來要比的價格（已知）', 'Year-ago price ahead (known)'), 'var(--s2)', 'dash']],
        mvrv1y: [['MVRV', 'var(--s1)'], [_T('一年均值', '1-year mean'), 'var(--s3)'], PX2], rcgrowth: [[_T('實現市值 30 日變化', 'Realized cap, 30-day change'), 'var(--s4)'], PX2], xs90: [[_T('交易所供給 90 日變化', 'Exchange supply, 90-day change'), 'var(--s2)'], PX2] }[id];
      var seg = id === 'tmm' ? '<div class="seg" id="ev-tmm-seg"><button aria-pressed="true" data-v="1">' + _T('近 1 年', '1 year') + '</button><button aria-pressed="false" data-v="3">' + _T('3 年', '3 years') + '</button></div>' : '';
      return '<div class="evc' + (id === 'tmm' ? ' wide' : '') + '"><div class="panel-h"><h3><span class="mk-s' + (e.ok ? ' ok' : '') + '">' + (e.ok ? '✓' : '×') + '</span>' + esc(_T(e.label, (EV_EN[id] || [])[0] || e.label)) + '</h3>' + seg + '</div><p class="note">' + esc(evSay(e, sv)) + '</p>' + legend(lg) + '<div class="chart" id="c-ev-' + id + '"></div></div>';
    }).join('') + '</div>' + _T('<p class="note">走勢圖近 3 年、每 3 天一點；灰線是 BTC 價格（CoinMetrics；不同刻度的圖只看方向）。外推與「價格不動」都只是讀值，不是預測。</p>', '<p class="note">Charts cover 3 years, one point every 3 days; the grey line is the BTC price (CoinMetrics; where it has its own scale, read only its direction). Extrapolations and “if price stays flat” are readings, not forecasts.</p>');
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
  function sigOn(chart) { return ((D.signals || {}).items || []).filter(function (s) { return s.chart && s.chart === chart; }); }
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
    var fuH = fu.length ? '<div class="fu"><h4>' + _T('上期發現的後續', 'Follow-ups') + '</h4><ul class="deltas">' + fu.map(function (f) { var st = FU_ST[f.status] || FU_ST.open; return '<li><span class="ar ' + st[3] + '">' + st[0] + '</span><div><h3>' + esc(f.title) + ' <span class="chip">' + _T(st[1], st[2]) + '</span></h3>' + (f.since ? '<div class="fig num">' + _T('自 ', 'since ') + fmt.md(f.since) + '</div>' : '') + '<p>' + esc(f.say || '') + '</p></div></li>'; }).join('') + '</ul></div>' : '';
    var sgH = sg.length ? '<details class="sigs"' + (fs.length ? '' : ' open') + '><summary>' + _T('自動偵測的異動 ', 'Detected signals ') + sg.length + (D.signals.n > sg.length ? ' / ' + D.signals.n : '') + '</summary><ul>' + sg.map(function (x) {
        var k = SIG_K[x.kind] || ['', ''];
        return '<li><span class="chip ' + (x.dir === 'up' ? 'up' : x.dir === 'down' ? 'down' : '') + '">' + _T(k[0], k[1]) + '</span>' + (x.new ? '<span class="new">' + _T('新', 'New') + '</span>' : '<span class="days">' + _T('第 ' + x.days + ' 天', 'day ' + x.days) + '</span>') +
          '<div><b>' + esc(lt(x.title)) + '</b> ' + jumpA(x.page, x.chart, '→') + '<span class="fig num">' + esc(lt(x.fig)) + '</span>' + [x.ctx, x.decomp, x.caveat].filter(Boolean).map(function (t) { return '<span class="note">' + esc(lt(t)) + '</span>'; }).join('') + '</div></li>';
      }).join('') + '</ul><p class="note">' + _T('資料管線每天依寫死的規則偵測：一年最極端的 2%、7 日急變、狀態翻轉、關鍵價位 ±3%、連續、跨指標組合。上面的發現才是判讀；這裡只作讀值。', 'Detected daily by fixed rules: the most extreme 2% of the past year, sharp 7-day moves, state flips, key levels within ±3%, streaks, cross-indicator combos. The findings above are the interpretation; these are readings only.') + '</p></details>' : '';
    // 整體多空（2026-10-23 使用者要求）：依各則 lean 計數，偏多多於偏空＝整體偏多，反之偏空，相同＝多空互見
    var cnt = { bull: 0, bear: 0, neutral: 0 }; fs.forEach(function (f) { if (cnt[f.lean] != null) cnt[f.lean]++; });
    var ov = cnt.bull > cnt.bear ? 'bull' : cnt.bear > cnt.bull ? 'bear' : 'neutral', nl = cnt.bull + cnt.bear + cnt.neutral;
    var sum = nl ? '<p class="find-sum"><span class="imp ' + ov + '">' + (ov === 'bull' ? _T('整體偏多', 'Leaning bullish') : ov === 'bear' ? _T('整體偏空', 'Leaning bearish') : cnt.bull ? _T('多空互見', 'Mixed') : _T('整體中性', 'Neutral overall')) + '</span><span>' +
      _T('偏多 ' + cnt.bull + ' · 偏空 ' + cnt.bear + ' · 中性 ' + cnt.neutral, cnt.bull + ' bullish · ' + cnt.bear + ' bearish · ' + cnt.neutral + ' neutral') + '</span><span class="note">' + _T('描述這些發現對價格的一般含意，不是預測', 'what these findings usually mean for price; not a forecast') + '</span></p>' : '';
    var empty = has ? _T('本期沒有值得特別注意的異動。', 'Nothing unusual enough to call out today.') : _T('本期判讀還沒有寫發現；下面是自動偵測的異動。', 'Today\'s commentary has no findings yet; detected signals are below.');
    return _T('<div class="sec-h"><h2>今日發現</h2><span class="en">The Findings</span><hr></div>', '<div class="sec-h"><h2>Today\'s findings</h2><span class="en">The Findings</span><hr></div>') +
      sum + '<div class="finds">' + (cards || '<p class="note">' + empty + '</p>') + '</div>' + fuH + sgH;
  }
  /* 有異動的圖：圖上方標一行（哪一項、數字），圖上標日期線（lineChart 的 sigV） */
  function markSignals(root) {
    var by = {}; ((D.signals || {}).items || []).forEach(function (s) { if (s.chart) (by[s.chart] = by[s.chart] || []).push(s); });
    Object.keys(by).forEach(function (ch) {
      var el = (root || document).querySelector('#c-' + ch); if (!el || (el.previousElementSibling && el.previousElementSibling.classList.contains('sig-flag'))) return;
      el.insertAdjacentHTML('beforebegin', '<p class="sig-flag"><span class="chip flare"><i></i>' + _T('異動', 'Signal') + '</span>' + by[ch].map(function (s) { return '<span><b>' + esc(lt(s.title)) + '</b> ' + esc(lt(s.fig)) + '</span>'; }).join('') + '</p>');
    });
  }
  function researchHtml() {
    var r = N && N.research || {}, rows = r.items || [];
    if (!rows.length) return '<p class="note">' + esc(r.summary || _t('本期沒有新的機構研報。')) + '</p>';
    return (r.summary ? '<p class="say">' + esc(r.summary) + '</p>' : '') + _t('<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:20%"><col style="width:44%"><col style="width:36%"></colgroup><thead><tr><th>來源</th><th>重點</th><th>對本站判斷的意義</th></tr></thead><tbody>') +
      rows.map(function (x) { var src = x.url ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(x.source) + '</a>' : esc(x.source); return '<tr><td><b>' + src + '</b><br><span class="note">' + esc(x.title || '') + (x.date ? _t('，') + fmt.md(x.date) : '') + (x.access === 'title_only' ? _t('・只取得標題') : '') + '</span></td><td>' + esc(x.points) + '</td><td>' + esc(x.meaning) + '</td></tr>'; }).join('') +
      _t('</tbody></table></div><p class="note">研報只作文字對照，不改變任何規則；只取得標題的不作判斷依據。</p>');
  }
  function newsItem(n, lead, ix) {
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
  function interpHtml(items) {
    items = items.filter(function (x) { return x && x[2]; });
    return items.length ? '<div class="interp">' + items.map(function (x) { return '<div class="it"><span class="k">' + esc(x[0]) + '</span><span class="v num">' + x[1] + '</span>' + tnHtml(x[3]) + '<span class="d">' + esc(x[2]) + '</span></div>'; }).join('') + '</div>' : '';
  }
  function interpPanel(items, src) { var h = interpHtml(items); return h ? panel('span-12', _t('這些數字代表什麼'), src || _t('依當日數值套固定門檻自動產生 · 非投資建議'), h) : ''; }
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
      if (v.chg30_pct > 30) s += _t('；30 日上升 ') + fmt.n(v.chg30_pct, 0) + _t('%，老手獲利了結增加');
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

  /* 週期與出場（頭版、週期版、出場框架版共用） */
  function p20Read() { var cm = D.cycle.cm, r = cm.mvrv_vs_prior, c = D.price.bar.c, k = cm.k075_price;
    if (r == null) return null;
    return [r >= 0.75 ? _t('已站上 0.75 賣出線，連 5 天即觸發第一個鏈上賣點（現在 ') + (cm.p20_run_ge075 || 0) + _t('/5 天）。') : _t('離 0.75 賣出線還很遠：價格約要到 ') + fmt.usd(k) + _t('（比收盤高 ') + fmt.pct((k / c - 1) * 100, 0) + _t('）才會碰到；2025 頂部時是 0.78。'), r >= 0.75 ? 'neg' : r >= 0.7 ? 'warn' : 'neu']; }
  function plRead() { var pl = D.cycle.powerlaw || {}, r = pl.ratio, bb = pl.bottom_band || [0.24, 0.48];
    if (r == null) return null;
    return [_T('價格是冪律合理價（' + fmt.usd(pl.fair) + '）的 ' + fmt.n(r * 100, 0) + '%：', 'Price is ' + fmt.n(r * 100, 0) + '% of the power-law fair value (' + fmt.usd(pl.fair) + '): ') + (r <= bb[1] ? _t('落在歷史底部帶（') + bb[0] + '–' + bb[1] + _t(' 倍），長期看很便宜。') : r < 1 ? _t('低於合理價、高於歷史底部帶（') + bb[1] + _t(' 倍），長期看偏便宜。') : r < 1.12 ? _t('高於合理價，但還低於 2025 頂部的 1.12 倍。') : _t('已超過 2025 頂部的 1.12 倍，偏貴。')), r <= bb[1] ? 'pos' : r < 1 ? 'neu' : r < 1.12 ? 'warn' : 'neg']; }
  function tmRead() { var tm = D.cycle.tidemark || {}, t = (tm.top || {}).signal, b = (tm.bottom || {}).signal, ct = tm.cycle_test || {};
    if (t == null && b == null) return null;
    return [_t('頂部訊號 ') + fmt.n(t, 0) + _t('（') + (t >= 70 ? _t('高度警戒') : t >= 50 ? _t('進入頂部窗口') : _t('低於 50，沒有頂部跡象')) + _t('）、底部訊號 ') + fmt.n(b, 0) + _t('（') + (b >= 70 ? _t('強烈底部') : b >= 50 ? _t('進入底部區') : _t('低於 50，不在底部區')) + _t('）') + (t < 50 && b < 50 ? _t('：模型認為現在既不是頂也不是底，在週期中段。') : _t('。')) + (ct.status === 'testing' && ct.decisive_date ? _t('本輪低點假說驗證到 ') + ct.decisive_date + _t('。') : ''), t >= 50 ? 'neg' : b >= 50 ? 'pos' : 'neu']; }
  function p6Read() { var p6 = D.cycle.p6 || {}, nm = { mvrv_z: 'MVRV Z', nupl: 'NUPL', puell: 'Puell' }, hit = Object.keys(nm).filter(function (k) { return p6[k] >= 80; });
    if (p6.mvrv_z == null) return null;
    return [hit.length + _t(' 項到 80') + (hit.length ? _t('（') + hit.map(function (k) { return nm[k]; }).join(_t('、')) + _t('）') : '') + _t('；') + (hit.length >= 2 ? _t('已進入頂部區，出場框架的加速規則開始適用。') : _t('任兩項到 80 才進入頂部區，現在還差') + (hit.length ? _t('一') : _t('兩')) + _t('項。')), hit.length >= 2 ? 'neg' : hit.length ? 'warn' : 'neu']; }
  function ladderRead() { var ex = D.exit.status, n = (ex.steps_hit || []).length;
    if (!ex.next_step) return [_t('價格階梯 8 階都已觸發。'), 'neg'];
    return [_t('收盤要再漲 ') + fmt.n(ex.next_step_dist_pct, 0) + _t('% 到 ') + fmt.usd(ex.next_step) + _t(' 才賣') + (n ? _t('第 ') + (n + 1) + _t(' 階') : _t('第一階')) + _t('（每階 12.5%）') + (n ? _t('；已觸發 ') + n + _t(' 階。') : _t('；目前一階都還沒觸發，價格階梯沒有任何賣出動作。')), ex.next_step_dist_pct < 10 ? 'warn' : 'neu']; }
  function hedgeRead() { var c = D.price.bar.c, s = D.exit.status, sma = s.sma200, run = s.below_sma200_run || 0;
    if (!sma) return null;
    return [c < sma ? _t('收盤在 200 日均線（') + fmt.usd(sma) + _t('）之下，第 ') + run + _t('/5 天；連 5 天就減 20%。') : _t('收盤高於 200 日均線（') + fmt.usd(sma) + _t('），高出 ') + fmt.n((c / sma - 1) * 100, 0) + _t('%；要跌到線下並連 5 日收在下方才會減 20%。'), c < sma ? 'neg' : c / sma - 1 < 0.05 ? 'warn' : 'pos']; }
  function rd2(label, val, r) { return r ? [label, val, r[0], r[1]] : null; }
  function ovInterp() {
    var cm = D.cycle.cm, pl = D.cycle.powerlaw || {}, tm = D.cycle.tidemark || {}, p6 = D.cycle.p6 || {}, ex = D.exit.status;
    return [rd2(_t('MVRV ÷ 前一輪高點'), fmt.n(cm.mvrv_vs_prior, 3), p20Read()), rd2(_t('冪律倍數'), fmt.n(pl.ratio, 2) + '×', plRead()), rd2(_t('Tidemark 頂 / 底'), fmt.n((tm.top || {}).signal, 0) + ' / ' + fmt.n((tm.bottom || {}).signal, 0), tmRead()),
      rd2(_t('頂部三指標'), ['mvrv_z', 'nupl', 'puell'].map(function (k) { return fmt.n(p6[k], 0); }).join(' / '), p6Read()), rd2(_t('離出場第一階'), fmt.pct(ex.next_step_dist_pct, 0), ladderRead()), rd2(_t('200 日均線避險'), fmt.k(ex.sma200), hedgeRead())];
  }

  /* 價格版 */
  function mkInterp() {
    var p = D.price, b = p.bar, c = b.c, a = p.atr || {}, v = p.vol || {}, my = (p.mayer || {}).mayer, pi = p.pi_cycle, it = [];
    if (b.close_pos_pct != null) it.push([_t('收盤'), fmt.pct(b.chg_pct, 2), _t('收在當日高低區間的 ') + fmt.n(b.close_pos_pct, 0) + _t('% 位置（') + (b.close_pos_pct >= 70 ? _t('收在高檔，買方較強') : b.close_pos_pct <= 30 ? _t('收在低檔，賣方較強') : _t('收在中段，多空互有攻守')) + _t('）') + (b.vol_vs_20dma != null ? _t('；成交量是 20 日均量的 ') + fmt.n(b.vol_vs_20dma, 2) + _t(' 倍') + (b.vol_vs_20dma < 0.6 ? _t('，量縮，這根 K 線的訊號力道弱。') : b.vol_vs_20dma > 1.5 ? _t('，放量，訊號較可信。') : _t('。')) : _t('。')), b.close_pos_pct >= 70 ? 'pos' : b.close_pos_pct <= 30 ? 'neg' : 'neu']);
    if (a.atr14) it.push(['ATR14', fmt.usd(a.atr14), _t('一天的正常波動約 ±') + fmt.usd(a.atr14) + _t('（') + fmt.n(a.atr14 / c * 100, 1) + _t('%）：這個範圍內的漲跌屬日常雜訊；掛單或停損的距離小於它，很容易被正常波動掃到。'), 'neu']);
    if (v.rv30 != null) it.push([_t('實際波動 RV30'), fmt.n(v.rv30, 1) + '%', band(v.rv30, [30, 50, 70], [_t('年化 30% 以下，低波動'), _t('年化 30–50%，一般水準'), _t('年化 50–70%，偏高'), _t('年化 70% 以上，劇烈')]) + (v.rv7_rv30 < 0.75 ? _t('；近 7 天明顯比近 30 天平靜（RV7 只有 RV30 的 ') + fmt.n(v.rv7_rv30 * 100, 0) + _t('%），價格在收斂盤整，之後常出現方向性突破。') : v.rv7_rv30 > 1.3 ? _t('；近 7 天波動明顯放大（RV7 是 RV30 的 ') + fmt.n(v.rv7_rv30, 2) + _t(' 倍）。') : _t('。')), 'neu']);
    if (my != null) it.push([_t('Mayer 倍數'), fmt.n(my, 2), band(my, [0.8, 1, 1.5, 2.4], [_t('0.8 以下：歷史便宜區'), _t('0.8–1：價格低於 200 日均線，偏弱但不算便宜'), _t('1–1.5：價格高於 200 日均線、還沒過熱'), _t('1.5–2.4：偏熱'), _t('2.4 以上：歷史過熱區')]) + _t('。'), my < 0.8 ? 'pos' : my >= 2.4 ? 'neg' : my >= 1.5 ? 'warn' : 'neu']);
    if (pi != null) it.push(['Pi Cycle', fmt.n(pi, 2), pi >= 1 ? _t('已到 1：歷史頂部訊號觸發。') : pi >= 0.9 ? _t('接近 1，頂部訊號逼近。') : _t('只有 ') + fmt.n(pi, 2) + _t('，離觸發（1）很遠，沒有頂部跡象。'), pi >= 1 ? 'neg' : pi >= 0.9 ? 'warn' : 'neu']);
    return it;
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
  function concSay(k, dvol) {
    var a = concAgo(7), h = (D.chips || {}).conc_hist || [];
    var wk = a ? _T('，7 天前 ' + fmt.n(a[2], 1) + '%', '; ' + fmt.n(a[2], 1) + '% a week ago') : '';
    var lowIv = dvol && dvol.pct_1y != null && dvol.pct_1y < 30;
    return _T('現價 ±5%（' + fmt.k(k.lo) + '–' + fmt.k(k.hi) + '）內有 ' + fmt.n(k.btc / 1e4, 0) + ' 萬顆，佔流通 ' + fmt.n(k.pct, 1) + '%' + wk + '。籌碼越集中，價格離開這一帶時越容易引發一起停損或一起解套，波動容易放大；它不指方向。' + (lowIv ? '目前 DVOL 也在一年偏低處：籌碼擠在現價附近、選擇權又不貴。' : '') + '本站從 2026-10-01 才開始記錄（' + h.length + ' 天），還不足以判斷高低。',
      'Within ±5% of price (' + fmt.k(k.lo) + '–' + fmt.k(k.hi) + ') sit ' + (k.btc / 1e6).toFixed(2) + 'M BTC, ' + fmt.n(k.pct, 1) + '% of circulating supply' + wk + '. The more supply crowds here, the more likely a move out of this band sets off stop-losses or break-even selling together, so volatility tends to expand; it says nothing about direction.' + (lowIv ? ' DVOL is also low for the year: supply is crowded near price and options are cheap.' : '') + ' We have only tracked it since 2026-10-01 (' + h.length + ' days), too short to call it high or low.');
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
    if (big) it.push([_t('最大到期'), big.expiry, _t('佔全部未平倉 ') + fmt.n(big.share, 0) + _t('%，賣權／買權 ') + fmt.n(big.pc, 2) + (big.pc < 0.7 ? _t('（買權明顯較多，偏多佈局）') : big.pc > 1 ? _t('（賣權較多，偏避險）') : _t('（大致平衡）')) + _t('；Max Pain ') + fmt.k(big.maxpain) + _t('，') + (big.maxpain < c ? _t('低於收盤 ') : _t('高於收盤 ')) + fmt.n(Math.abs(big.maxpain / c - 1) * 100, 0) + _t('%。到期前價格有時被拉向 Max Pain，但這個效應的證據薄弱，只作參考。'), big.pc < 0.7 ? 'pos' : big.pc > 1 ? 'neg' : 'neu']);
    return it;
  }
  function basisSay(cv) {
    if (!cv || !cv.length) return '';
    var ys = cv.map(function (p) { return p[1]; }), lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys), sl = ys[ys.length - 1] - ys[0];
    return _t('<p class="say">各期限年化 <b>') + fmt.n(lo, 1) + '–' + fmt.n(hi, 1) + _t('%</b>，') + (sl > 0.5 ? _t('遠月較高（正常的正價差）') : sl < -0.5 ? _t('近月較高，短期做多需求較強') : _t('曲線平坦')) + _t('；') + (hi > 15 ? _t('水準偏高，槓桿偏熱。') : lo < 3 ? _t('水準很低，做多需求冷淡。') : _t('水準中性（3–15% 屬常態）。')) + '</p>';
  }
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
      it.push([_t('短期持有者成本'), fmt.usd(sv.sth_cost), (d >= 0 ? _T('收盤高於短期持有者（持有不到 155 天）的平均成本 ' + fmt.n(d, 1) + '%：新進場的資金整體在賺錢，是多頭結構；跌回這條線時常有回本或停損賣壓。', 'Close is ' + fmt.n(d, 1) + '% above the average cost of short-term holders (held under 155 days): recent buyers are in profit overall, a bullish structure; a drop back to this line often meets break-even or stop-loss selling. ') : _T('收盤低於短期持有者的平均成本 ' + fmt.n(-d, 1) + '%：新進場的資金整體虧損，反彈到成本線附近容易遇到解套賣壓。', 'Close is ' + fmt.n(-d, 1) + '% below the average cost of short-term holders: recent buyers are underwater, and rallies toward that cost line tend to meet selling from holders getting back to even. ')) +
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
     短週期：收盤價 15% 反轉才算新的一段（collect.py G1c）。鯨魚：BitInfoCharts 依地址餘額分層的持幣量（G1d）。只作讀值，不連動任何規則。 */
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
    var s = _T('30 日 ' + cK(x.chg30, true) + ' 顆（' + lvl + '；30 日變化落在 2021 年以來第 ' + fmt.n(p, 0) + ' 百分位）', '30-day ' + cK(x.chg30, true) + ' BTC (' + lvl + '; the 30-day change is at the ' + ord(p) + ' percentile since 2021)') +
      (flip ? _T('，但最近 7 天轉為' + (x.chg7 > 0 ? '增持 ' : '減持 ') + cK(x.chg7, true), ', but the last 7 days flipped to ' + cK(x.chg7, true)) : '') + _T('；90 日 ' + cK(x.chg90, true) + '。', '; 90-day ' + cK(x.chg90, true) + '. ');
    if (x.key === 'ge10k') s += _T('這一層多是交易所冷錢包與 ETF 託管，增減常是錢包整理或客戶進出，不能直接當成大戶買賣。', 'This tier is mostly exchange cold wallets and ETF custodians; changes are often wallet reshuffles or client flows, not big-holder buying or selling.');
    if (x.key === 'lt1') s += _T('散戶持幣變化小、影響有限，主要看方向是否與大戶相反。', 'Retail holdings move little; what matters is whether they move opposite to big holders.');
    var big = x.key === '100_1k' || x.key === '1k_10k';
    return [s, big && !flip ? (up && p >= 60 ? 'pos' : !up && p <= 40 ? 'neg' : 'neu') : 'neu'];
  }
  var MQ560 = window.matchMedia('(max-width: 560px)');   // 手機隱藏 7d／90d 兩欄，解讀列的 colspan 跟著改
  /* 鏈上指標走勢（2026-10-14）：表格與頂部雷達每一項近 3 年，配 BTC 價格線（另一刻度）。只作讀值 */
  var OCV = [['mvrv-zscore', 'MVRV Z', 'MVRV Z', 2], ['nupl', 'NUPL', 'NUPL', 3], ['puell-multiple', 'Puell', 'Puell', 2],
    ['asopr', 'aSOPR（7 日均）', 'aSOPR (7-day avg)', 4], ['sth-sopr', 'STH-SOPR（7 日均）', 'STH-SOPR (7-day avg)', 4], ['lth-sopr', 'LTH-SOPR（7 日均）', 'LTH-SOPR (7-day avg)', 3],
    ['illiquid-supply', '非流動性供給', 'Illiquid supply', 'M'], ['highly-liquid-supply', '高流動性供給', 'Highly liquid supply', 'M'],
    ['lth-mvrv-zscore', 'LTH MVRV Z', 'LTH MVRV Z', 2], ['supply-in-profit-pct', '獲利供給 %', 'Supply in profit %', 1], ['lth-net-position-change-30d-btc', '長期持有者 30 日淨部位', 'LTH 30-day net position', 'K']];
  function ocFmt(v, f) { if (v == null) return '—'; if (f === 'M') return fmt.n(v / 1e6, 2) + 'M'; if (f === 'K') return (v > 0 ? '+' : v < 0 ? '−' : '') + fmt.n(Math.abs(v) / 1e3, 0) + 'K'; return fmt.n(v, f); }
  function ocDelta(v, f) { if (v == null) return '—'; var s = v > 0 ? '+' : v < 0 ? '−' : ''; return s + ocFmt(Math.abs(v), f === 'K' ? 'K' : f).replace(/^[+−]/, ''); }
  var OC_REF = { p80: ['四年 80 百分位（頂部區門檻）', '4-year 80th percentile (top-zone line)'], top2025: ['2025 頂部附近的極值', 'Extreme near the 2025 top'], one: ['1.0＝賣在成本', '1.0 = selling at cost'] };
  function ocPanel() {
    var V_ = (D.onchain || {}).viz; if (!V_ || !(D.cycle.stage || {}).viz) return '';
    var cells = OCV.filter(function (o) { return V_[o[0]]; }).map(function (o) {
      var x = V_[o[0]], r = x.ref, f = o[3];
      var say = _T('現在 ', 'Now ') + ocFmt(x.last, f) + _T('（' + fmt.md(x.date) + '）· 30 日 ', ' (' + fmt.md(x.date) + ') · 30d ') + ocDelta(x.chg30, f) + _T(' · 90 日 ', ' · 90d ') + ocDelta(x.chg90, f) +
        (r ? _T(' · ' + OC_REF[r.kind][0] + ' ', ' · ' + OC_REF[r.kind][1] + ' ') + ocFmt(r.y, f) : '');
      return '<div class="evc"><div class="panel-h"><h3>' + esc(_T(o[1], o[2])) + '</h3></div><p class="note">' + esc(say) + '</p><div class="chart" id="c-oc-' + o[0] + '"></div></div>';
    }).join('');
    return panel('span-12', _T('鏈上指標走勢', 'On-chain indicators over time'), _T('近 3 年 · 灰線是 BTC 價格（另一刻度）', '3 years · grey line is the BTC price (own scale)'),
      legend([[_T('指標', 'Indicator'), 'var(--s1)'], [_T('參考線', 'Reference line'), 'var(--down)'], [_T('BTC 價格（另一刻度）', 'BTC price (own scale)'), 'var(--ink-3)']]) + '<div class="evcharts">' + cells + '</div>');
  }
  function drawOc() {
    var V_ = (D.onchain || {}).viz, px = ((D.cycle.stage || {}).viz || {}).px || []; if (!V_) return;
    OCV.forEach(function (o) {
      var x = V_[o[0]], el = $('#c-oc-' + o[0]); if (!x || !el) return;
      var f = o[3], x0 = x.rows.length ? x.rows[0][0] : 0, yf = function (v) { return f === 'M' ? (v / 1e6).toFixed(1) + 'M' : f === 'K' ? Math.round(v / 1e3) + 'K' : v.toFixed(typeof f === 'number' ? Math.min(f, 2) : 2); };
      mount(el, function (e) { lineChart(e, { h: 180, log2: true, robust: /sopr/.test(o[0]) ? 0.01 : 0, series: [{ name: _T('BTC 價格', 'BTC price'), data: px.filter(function (r) { return r[0] >= x0; }), color: 'var(--ink-3)', w: 1.1, end: false, y2: true, fmt: fmt.usd }, { name: _T(o[1], o[2]), data: x.rows, color: 'var(--s1)', w: 1.7 }],
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
      'conc': { h: h('現價 ±5% 內的籌碼（最後一次移動在這個價格帶的 BTC）佔流通量的比例；灰線是 BTC 價格。', 'Share of circulating supply whose last move was within ±5% of the current price; the grey line is the BTC price.', '比例上升＝越多人的成本擠在現價附近；價格離開這一帶時，買在這裡的人容易一起停損或一起解套，波動常放大。', 'A rising share means more holders\' cost basis is crowded near price; when price leaves the band they tend to cut or sell at break-even together, and volatility often expands.', '只說波動可能變大，不說方向。URPD 以 2,000 美元一格估算、晚約 1 天；本站從 2026-10-01 才有紀錄，樣本太短，不設門檻。', 'It flags bigger moves, not direction. URPD uses $2,000 buckets and lags about a day; our record starts 2026-10-01, too short to set any threshold.'),
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
      'cbp': { h: h('Coinbase（美國現貨、機構與 ETF 常用）相對 Binance 的價差；淡線是 7 日平均。', 'Coinbase (US spot, used by institutions and ETFs) price vs Binance; the faint line is the 7-day average.', '正溢價＝美國買盤較強；長時間負溢價＝美國需求偏弱。', 'A positive premium means stronger US buying; a persistent discount means weak US demand.', '單日雜訊大，看 7 日平均；USDT 偏離 1 美元也會影響。', 'Single days are noisy, use the 7-day average; USDT drifting from $1 also distorts it.'),
        now: function () { var p = D.flows.cb_premium || {}; return _T('今天 ' + fmt.n(p.pct, 3) + '%、7 日均 ' + fmt.n(p.avg7, 3) + '%、30 日均 ' + fmt.n(p.avg30, 3) + '%：' + (p.avg7 > 0 ? '美國買盤偏強。' : '美國買盤偏弱。'), 'Today ' + fmt.n(p.pct, 3) + '%, 7-day ' + fmt.n(p.avg7, 3) + '%, 30-day ' + fmt.n(p.avg30, 3) + '%: ' + (p.avg7 > 0 ? 'US buying is stronger.' : 'US buying is weaker.')); } },
      'cost': { h: h('短期持有者成本（155 天內換手的幣的平均成本）、真實市場均價（活躍投資人的成本）；橫線是收盤。', 'Short-term holder cost (average cost of coins moved within 155 days) and the true market mean (active investors\' cost); the horizontal line is the close.', '價格在短期持有者成本之上＝新買家整體賺錢，回檔常在這條線獲得支撐；短期持有者成本高於真實市場均價＝新資金願意用更高價買。', 'Price above the STH cost means recent buyers are in profit, and pullbacks often find support there; STH cost above the true market mean means new money is paying up.', 'bitcoin-data 晚約 7 天。', 'bitcoin-data runs about 7 days late.'),
        now: function () { var f = (D.chips.flow || {}).sth_vs_tmm || {}; return _T('收盤比短期持有者成本 ' + pc(c(), f.sth_cost) + '；短期持有者成本比真實市場均價 ' + fmt.pct(f.sth_vs_tmm_pct, 1) + '（' + ymd(f.date) + '）。', 'Close vs STH cost: ' + pc(c(), f.sth_cost) + '; STH cost vs true market mean: ' + fmt.pct(f.sth_vs_tmm_pct, 1) + ' (' + ymd(f.date) + ').'); } },
      'profit': { h: h('短期持有者中處於獲利的比例。', 'Share of short-term holder supply in profit.', '長時間 > 90%＝過熱、容易回檔；跌到 50% 以下＝短期持有者普遍套牢，回調中常接近階段低點。', 'Long stretches above 90% mean overheating and pullback risk; below 50% means most recent buyers are underwater, often near a local low in a correction.', '同一個數字在牛市回調和熊市裡意義不同。', 'The same reading means different things in a bull correction and a bear market.'),
        now: function () { var p = (D.chips.flow || {}).sth_in_profit_pct || {}; return _T(fmt.n(p.value, 1) + '%（7 天前 ' + fmt.n(p.d7, 1) + '%），30 日最低 ' + fmt.n(p.min30, 1) + '%（' + ymd(p.min30_date) + '）。', fmt.n(p.value, 1) + '% (' + fmt.n(p.d7, 1) + '% a week ago); 30-day low ' + fmt.n(p.min30, 1) + '% (' + ymd(p.min30_date) + ').'); } },
      'urpd': { h: h('每 2,000 美元一格：有多少顆 BTC 最後一次移動是在這個價位；橘格是現價，淡框是 7 天前。', '$2,000 buckets: how many BTC last moved at each price; the orange bucket is the current price, faint outlines are 7 days ago.', '籌碼厚的價位常成支撐或壓力（買在那裡的人會防守或解套賣出）；籌碼薄的區間價格走得快。', 'Thick buckets often act as support or resistance (holders defend or sell to break even); price moves fast through thin zones.', '交易所內部轉帳也會重設成本。', 'Exchange-internal transfers also reset the cost basis.') },
      'npl': { h: h('上層：BTC 價格與每天的淨實現損益氣泡（綠＝當天整體獲利賣出、紅＝認賠賣出，越大金額越大，粗外圈＝在之前一年最極端的 2%）；下層：同一數字的每日柱。切到「30 日累計」看週期級別：下層是 30 日累計佔市值的比例，紅線是之前 4 年最極端的 3%，橘圈是首次跌破。', 'Top: BTC price with a bubble for each day\'s net realized profit/loss (green = net profit selling, red = net loss selling, bigger = larger, thick ring = most extreme 2% of the prior year); bottom: the same numbers as daily bars. Switch to “30-day total” for the cycle view: the bottom pane is the 30-day total as % of market cap, the red line the most extreme 3% of the prior 4 years, and orange rings the first breaches.', '大綠泡集中在急漲與高點那幾天＝獲利了結；綠泡變小＝想在現價賣的人變少。回檔時出現大紅泡＝認賠出清，但不代表已經見底。', 'Big green bubbles cluster on rallies and highs: profit taking; shrinking green bubbles mean fewer holders want to sell at this price. Big red bubbles on pullbacks are loss capitulation, which does not mean the low is in.', '只有淨值（獲利減認賠），看不到兩邊各有多少；交易所內部轉帳也會實現損益。2015 起只用當天已知資料回測：認賠高峰之後的表現和平常差不多，不是買點；獲利高峰之後反而多半續漲（一輪比一輪弱），不是賣點。30 日累計跌破紅線過去 5 次（2015–2022）1 年後都上漲，但其中 3 次之後還再跌 17–44%，而且 2025 頂部之後這一輪沒有觸發。ETF 時代這個訊號可能變鈍：ETF 持有人在股市互相買賣不會移動鏈上的幣，只有淨贖回才會；2025-10 到 2026-06 的下跌中 ETF 只淨贖回約 13 萬顆（約一成八），這一輪按跌幅換算的認賠也只有前幾輪的一半。過去 5 次觸發都在 ETF 上市（2024-01）之前。', 'Net only (profit minus loss), so the two sides are not visible separately; exchange-internal transfers also realize P/L. In tests since 2015 using only data known on the day, loss spikes were followed by ordinary returns (not a buy signal), and profit spikes were more often followed by further gains, weaker each cycle (not a sell signal). The 5 breaches of the 30-day red line (2015–2022) were all higher a year later, but 3 fell another 17–44% first, and it has not triggered since the 2025 top. The signal may be blunter in the ETF era: ETF shares changing hands on the stock market do not move coins on-chain, only net redemptions do; in the Oct 2025–Jun 2026 decline ETFs net-redeemed only about 134K BTC (roughly 18% of their holdings), and loss realization per point of drawdown was about half that of past cycles. All 5 past triggers came before spot ETFs launched (Jan 2024).'),
        now: function () { var n = D.onchain.npl; if (!n) return ''; return _T('近 7 日合計 ' + nplB(n.sum7_usd_m) + '，前 7 日 ' + nplB(n.sum7_prev_usd_m) + '；最新一天 ' + nplB(n.usd_m) + '（近一年第 ' + fmt.n(n.rank_1y, 0) + ' 百分位）。', 'Past 7 days ' + nplB(n.sum7_usd_m) + ', prior 7 days ' + nplB(n.sum7_prev_usd_m) + '; latest day ' + nplB(n.usd_m) + ' (1-year percentile ' + fmt.n(n.rank_1y, 0) + ').'); } },
      'cohort': { h: h('每 2,000 美元一格：左邊是持有不到 155 天的短期持有者（STH），右邊是長期持有者（LTH），橫線是收盤；灰底是過去 155 天價格走過的區間。切到「STH 變化／LTH 變化」看和約 30 天前比：灰條是當時，彩條是現在。', '$2,000 buckets: short-term holders (held under 155 days) on the left, long-term holders on the right, the line is the close; the shaded band is the range price covered in the past 155 days. Switch to “STH change / LTH change” to compare with about 30 days ago: grey is then, colour is now.',
          '短期持有者堆在收盤上方＝那批人帳面虧損，價格回到成本時容易解套賣出；堆在下方＝跌回去之前他們還在獲利，是第一道承接。長期持有者的堆動得慢，變少的格子代表那個成本的老手在賣。', 'Short-term holders piled above the close are underwater and tend to sell when price returns to their cost; piled below, they stay in profit until price falls back, the first layer of support. Long-term holder piles move slowly; a shrinking bucket means veterans with that cost are selling.',
          '「現在」是 CheckOnChain 依實際幣齡算的（取不到時退回推算）；「變化」是推算。都是逐筆 UTXO、不是實體調整，交易所整理錢包會被當成賣出再買進（單日大量又集中的搬家已放回原本的成本）；灰底區間外只有長期持有者。', '“Now” is CheckOnChain\'s actual coin-age data (falls back to the estimate if unavailable); “changes” are estimated. Both are per-UTXO, not entity-adjusted, so exchange wallet reshuffles look like selling and rebuying (large, concentrated one-day moves are put back at their original cost). Outside the shaded band there are only long-term holders.'),
        now: function () { var co = D.chips.cohort; if (!co) return ''; var ex = co.src === 'checkonchain'; return _T('短期持有者 ' + coins(co.tot.sth) + '、平均成本 ' + fmt.usd(co.tot.sth_cost) + '；長期持有者 ' + coins(co.tot.lth) + '（' + (ex ? 'CheckOnChain ' + ymd(co.now_date) + '，已扣搬家日' : 'URPD ' + ymd(co.date) + '，推算') + '）。', 'Short-term holders ' + coins(co.tot.sth) + ', average cost ' + fmt.usd(co.tot.sth_cost) + '; long-term holders ' + coins(co.tot.lth) + ' (' + (ex ? 'CheckOnChain ' + ymd(co.now_date) + ', transfer days removed' : 'URPD ' + ymd(co.date) + ', estimated') + ').'); } },
      'lthc': { h: h('BTC 價格（對數刻度），線的顏色是長期持有者（持有 ≥155 天）過去 30 天的淨增減：紅＝淨減、灰＝持平、藍＝淨增，±40 萬顆最深。', 'BTC price on a log scale, coloured by long-term holders\' (held 155+ days) net change over 30 days: red = net cut, grey = flat, blue = net add, deepest at ±400K BTC.',
          '高價區出現紅色＝老手趁高出貨（2024/3、2024 年底、2025/9–11 都是）；下跌後轉藍＝老手不賣、籌碼沉澱。價格在漲、線卻是紅的，代表上漲一路有人供貨。', 'Red at high prices means veterans selling into strength (as in Mar 2024, late 2024 and Sep–Nov 2025); turning blue after a drop means veterans are holding and supply is settling. Price rising on a red line means the rally is being met with supply.',
          '藍色不等於有人在買：幣放滿 155 天就自動算成長期持有者。這是依幣齡分組，不排除交易所；Glassnode 的吸籌趨勢評分以實體計，是不同指標。', 'Blue is not buying: coins become long-term automatically at 155 days. Grouped by coin age with exchanges included; Glassnode\'s Accumulation Trend Score is entity-based and a different metric.') },
      'whale': { h: h('依地址餘額分層的 30 日淨變化（顆）。', '30-day net change by address-balance tier (BTC).', '鯊魚（100–1K）與鯨魚（1K–10K）同向增加＝大戶在累積；≥ 10K 多是交易所與託管，不算大戶買賣。', 'Sharks (100–1K) and whales (1K–10K) rising together means big holders are accumulating; ≥10K is mostly exchanges and custodians.', '一個地址不等於一個人，錢包整理會讓幣在分層之間移動。', 'One address is not one person; wallet reshuffles move coins between tiers.') },
      'sopr': { h: h('STH-SOPR＝短期持有者當天賣出的幣「賣價 ÷ 買價」；灰線是價格，標記是每一次認賠的最低點。', 'STH-SOPR = sale price ÷ purchase price for coins short-term holders sold that day; the grey line is price, markers are the low of each loss-selling episode.', '低於 1＝短期持有者賠錢賣（停損或恐慌）。價格回到前一次認賠的低點附近，SOPR 卻沒跌得更深＝願意認賠的人變少、賣壓遞減，常是階段性止跌的特徵；跌得更深＝賣壓加重。', 'Below 1 means short-term holders are selling at a loss. When price revisits a previous loss-selling low but SOPR doesn\'t dip as deep, fewer holders are willing to sell at a loss — a common sign of a local bottom forming; a deeper dip means selling is getting heavier.', '日線（CheckOnChain，晚約 1 天）：盤中的集中認賠會被同一天其他人的獲利賣出平均掉，單日下殺不一定跌破 1；隔幾天內的兩次下殺可能算成同一次。只是讀值，不是買點。', 'Daily data (CheckOnChain, about 1 day late): intraday loss bursts get averaged out by the same day\'s profit-taking, so a sharp drop may not push it below 1, and two drops a few days apart may merge into one episode. A reading, not a buy signal.') },
      'sthpnl': { h: h('短期持有者當天賣出時實現的獲利與虧損（顆，已平滑），分開兩條；灰線是價格。', 'Profit and loss short-term holders realized on coins sold (BTC, smoothed), as two separate lines; the grey line is price.', 'STH-SOPR 只是兩者合起來的比例，這張圖看是哪一邊在動：獲利線上升＝獲利了結變多，虧損線下降＝認賠變少；虧損線衝高＝集中認賠。', 'STH-SOPR only shows the two combined as a ratio; this chart shows which side moved: profit rising means more profit taking, loss falling means less loss selling, a loss spike means capitulation.', '數值是 CheckOnChain 平滑過的，單日大額轉帳也會被算進去，要看幾天才算數。只是讀值，不是買點。', 'Values are smoothed by CheckOnChain and a single large transfer can show up as a spike; wait a few days before reading much into it. A reading, not a buy signal.') },
      'p20': { h: h('MVRV 除以前一輪週期高點（只用當時已知的資料）；紅線 0.75／0.80 是出場框架的鏈上賣點。', 'MVRV divided by the previous cycle\'s peak (using only data known at the time); red lines at 0.75/0.80 are the exit framework\'s on-chain sell points.', '比值越高越接近上一輪的狂熱程度；連 5 天站上 0.75 啟動第一個鏈上賣出。', 'The higher the ratio, the closer to last cycle\'s euphoria; 5 straight days above 0.75 trigger the first on-chain sale.', '每輪頂部的 MVRV 越來越低，所以用相對前一輪的比例。', 'MVRV peaks lower each cycle, hence the ratio to the previous peak.') },
      'path': { h: h('四種長期走法（虛線，本站的預測）與已實現價格（實線）；橘色帶是頂部模型的 80% 區間。', 'Four long-term paths (dashed, our forecasts) and the realized price (solid); the orange band is the top model\'s 80% range.', '看實線貼近哪一條；權重每月底依實際走勢重估。', 'See which path the solid line is tracking; weights are re-estimated at each month end.', '2028 年以後只供量級參考。', 'Beyond 2028, treat it as order-of-magnitude only.') },
      'pl': { h: h('價格除以冪律合理價（對數刻度）；藍帶是歷史底部區，橘點頂、藍點底。', 'Price divided by the power-law fair value (log scale); the blue band is the historical bottom zone, orange dots tops, blue dots bottoms.', '倍數越高越貴；歷輪頂部倍數一輪比一輪小。', 'Higher multiples mean more expensive; each cycle\'s top multiple has been smaller than the last.', '冪律是擬合出來的；每天只用當天以前的資料。', 'The power law is a fit; each day uses only data up to that day.') },
      'ev-tmm': { h: h('短期持有者成本、真實市場均價與價格；虛線是用近 30 日速度外推。', 'STH cost, true market mean and price; dashed lines extrapolate the last 30 days\' pace.', '短期持有者成本上穿真實市場均價＝新資金用更高價進場，過去三次（2016、2019、2023）之後都走入牛市段。', 'STH cost crossing above the true market mean means new money is paying up; the last three crosses (2016, 2019, 2023) were followed by bull phases.', '落後指標；2019 年上穿後仍跌近六成。', 'A lagging signal; after the 2019 cross price still fell about 60%.') },
      'ev-sth': { h: h('價格與短期持有者成本。', 'Price and short-term holder cost.', '價格在成本之上＝新買家整體獲利，牛市回檔常在這條線止跌。', 'Price above cost means recent buyers are in profit; bull-market pullbacks often stop here.', 'bitcoin-data 晚約 7 天。', 'bitcoin-data runs about 7 days late.') },
      'ev-mom12': { h: h('價格與一年前的價格；虛線是未來每一天要比的那個價格（已知）。', 'Price and the price a year earlier; the dashed line is the year-ago price each future day will be compared with (already known).', '價格在一年前之上＝12 個月動能為正；虛線往下走，代表接下來的門檻在降低。', 'Price above its year-ago level means positive 12-month momentum; a falling dashed line means the bar is getting lower.', '門檻已知，但價格未知；「價格不動」只是假設。', 'The bar is known, the price isn\'t; "if price stays flat" is an assumption.') },
      'ev-mvrv1y': { h: h('MVRV 與自己的一年均值；灰線是價格（另一刻度）。', 'MVRV and its own 1-year average; grey line is price (own scale).', 'MVRV 在均值之上＝估值相對一年來在擴張。', 'MVRV above its average means valuation is expanding relative to the past year.', '均值線移動慢，盤整時容易來回穿越。', 'The average moves slowly, so sideways markets cause back-and-forth crosses.') },
      'ev-rcgrowth': { h: h('實現市值 30 日變化；灰線是價格（另一刻度）。', 'Realized cap 30-day change; grey line is price (own scale).', '> 0＝資金在流入。', 'Above zero means money is flowing in.', '不是買賣訊號。', 'Not a trade signal.') },
      'ev-xs90': { h: h('交易所供給 90 日變化；灰線是價格（另一刻度）。', 'Exchange supply 90-day change; grey line is price (own scale).', '< 0＝幣在離開交易所，賣壓供給減少。', 'Below zero means coins are leaving exchanges, shrinking sell-side supply.', 'CoinMetrics 的地址歸屬會事後修正。', 'CoinMetrics address tags get revised later.') },
      'oc-mvrv-zscore': { h: h('MVRV Z：市值減實現市值，再除以市值的歷史標準差；紅線是四年 80 百分位。', 'MVRV Z: market cap minus realized cap, over the historical standard deviation; the red line is the 4-year 80th percentile.', '越高越貴；頂部三指標任兩項到 80 百分位進入頂部區。', 'Higher means more expensive; any two of the top-3 at the 80th percentile put us in the top zone.', '每輪頂部讀數遞減。', 'Peak readings decline each cycle.') },
      'oc-nupl': { h: h('NUPL：帳面未實現獲利占市值的比例。', 'NUPL: unrealized profit as a share of market cap.', '> 0.5 常是狂熱期，< 0 是投降期。', 'Above 0.5 is typically euphoria, below 0 capitulation.', '同上，頂部讀數一輪比一輪低。', 'As above, peak readings fall each cycle.') },
      'oc-puell-multiple': { h: h('Puell：礦工每日收入 ÷ 一年平均。', 'Puell: daily miner revenue ÷ its 1-year average.', '高＝礦工收入暴增、賣壓可能增加；低（< 0.5）常在底部。', 'High means a revenue spike and possible miner selling; low (below 0.5) often marks bottoms.', '減半會讓它一次性下台階。', 'Halvings knock it down a step.') },
      'oc-asopr': { h: h('aSOPR 7 日均：所有賣出的幣「賣價 ÷ 買價」，排除一小時內轉手。', 'aSOPR 7-day average: sale price ÷ purchase price for all coins sold, excluding those moved within an hour.', '> 1＝市場平均賣在獲利；牛市中跌回 1 常獲支撐，熊市中漲到 1 常遇壓。', 'Above 1 means coins sell at a profit on average; in bull markets dips to 1 tend to hold, in bear markets rallies to 1 tend to fail.', '日值雜訊大，所以畫 7 日均。', 'Daily values are noisy, hence the 7-day average.') },
      'oc-sth-sopr': { h: h('STH-SOPR 7 日均：短期持有者的賣價 ÷ 買價。', 'STH-SOPR 7-day average: short-term holders\' sale price ÷ purchase price.', '低於 1＝新買家在認賠；配合上方「認賠賣壓」圖看深度是否遞減。', 'Below 1 means recent buyers are selling at a loss; see the loss-selling chart above for whether the dips are getting shallower.', 'CheckOnChain，晚約 1 天；和 bitcoin-data 是不同資料商，數值不互相比較。', 'CheckOnChain, about 1 day late; a different vendor from bitcoin-data, so values aren\'t compared across them.') },
      'oc-lth-sopr': { h: h('LTH-SOPR 7 日均：長期持有者的賣價 ÷ 買價。', 'LTH-SOPR 7-day average: long-term holders\' sale price ÷ purchase price.', '大幅升高＝老手在高價獲利了結，常見於牛市後段；跌破 1 極少見，多在深熊。', 'A big rise means veterans are taking profits, common late in bull markets; below 1 is rare and usually deep bear.', '單日大筆移動會讓它跳動。', 'Single large moves make it jumpy.') },
      'oc-illiquid-supply': { h: h('非流動性供給：長期不動的錢包持有的幣（百萬顆）。', 'Illiquid supply: coins in wallets that rarely spend (millions of BTC).', '持續增加＝囤幣、浮動籌碼減少；下降＝老幣回到市場。', 'Rising means hoarding and less float; falling means old coins returning to the market.', '分類依錢包行為估算，會事後修正。', 'Classified by wallet behavior and revised later.') },
      'oc-highly-liquid-supply': { h: h('高流動性供給：常在交易的錢包持有的幣（百萬顆）。', 'Highly liquid supply: coins in frequently trading wallets (millions of BTC).', '增加＝可交易的浮動籌碼變多，常伴隨派發或投機升溫。', 'Rising means more tradable float, often with distribution or speculation.', '同上，會事後修正。', 'As above, revised later.') },
      'oc-lth-mvrv-zscore': { h: h('長期持有者的 MVRV Z；紅線是 2025 頂部附近的最高值。', 'Long-term holder MVRV Z; the red line is its peak near the 2025 top.', '越接近紅線，長期持有者的帳面獲利越接近上次頂部的程度。', 'The closer to the line, the closer long-term holders\' paper profits are to last top\'s level.', '一個樣本的頂部值不是門檻。', 'One top\'s reading is not a threshold.') },
      'oc-supply-in-profit-pct': { h: h('處於獲利狀態的供給比例；紅線是 2025 頂部附近的最高值。', 'Share of supply in profit; the red line is its peak near the 2025 top.', '接近 100%＝幾乎所有人都賺錢，常在頂部附近；跌破 50% 多在熊市底部區。', 'Near 100% means almost everyone is in profit, typical near tops; below 50% is usually bear-market bottom territory.', '新高時一定接近 100%，單看它判斷不了頂。', 'At new highs it is always near 100%, so it can\'t call a top alone.') },
      'oc-lth-net-position-change-30d-btc': { h: h('長期持有者 30 日淨部位變化（顆）；紅線是 2025 頂部附近的最大賣出量。', 'Long-term holders\' 30-day net position change (BTC); the red line is their biggest selling near the 2025 top.', '大幅為負＝老手在派發，常見於牛市高點；轉正＝重新囤積。', 'Deeply negative means veterans are distributing, typical near bull highs; turning positive means accumulation again.', '幣從短期「熟成」成長期也會讓它變正，不全是買入。', 'Coins aging from short- to long-term also push it up; not all of it is buying.') }
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
    return panel('span-12', _T('短期持有者認賠賣壓（STH-SOPR）', 'Short-term holder loss selling (STH-SOPR)'), _T('CheckOnChain · 晚約 1 天 · 近 1 年', 'CheckOnChain · ~1 day late · 1 year'),
      '<p class="say">' + esc(soprSay(v)) + '</p>' + legend([['STH-SOPR', 'var(--s1)'], [_T('BTC 價格（另一刻度）', 'BTC price (own scale)'), 'var(--ink-3)'], [_T('賣壓遞減', 'Easing'), 'var(--up)'], [_T('賣壓加重', 'Heavier'), 'var(--down)']]) + '<div class="chart" id="c-sopr"></div>' + _T('<p class="note">資料：<a href="https://charts.checkonchain.com/btconchain/realised/sthsopr_indicator/sthsopr_indicator_light.html" target="_blank" rel="noopener">CheckOnChain STH-SOPR</a>（公開圖表，晚約 1 天）。</p>', '<p class="note">Data: <a href="https://charts.checkonchain.com/btconchain/realised/sthsopr_indicator/sthsopr_indicator_light.html" target="_blank" rel="noopener">CheckOnChain STH-SOPR</a> (public chart, about 1 day late).</p>'));
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
    return panel('span-12', _T('短期持有者實現獲利與虧損', 'Short-term holder realized profit and loss'), _T('CheckOnChain · 晚約 1 天 · 近 1 年', 'CheckOnChain · ~1 day late · 1 year'),
      '<p class="say">' + esc(sthPnlSay(v)) + '</p>' + legend([[_T('實現獲利', 'Realized profit'), 'var(--up)'], [_T('實現虧損', 'Realized loss'), 'var(--down)'], [_T('BTC 價格（另一刻度）', 'BTC price (own scale)'), 'var(--ink-3)']]) + '<div class="chart" id="c-sthpnl"></div>' +
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
    if (nplMode === 'cum') {
      var c = n.cum30 || {}, tg = (c.trig || [])[(c.trig || []).length - 1], mn = c.min_since_top;
      return _T('30 日累計 ' + nplB(c.usd_m) + '（市值的 ' + nplPct(c.pct_mcap) + '，4 年第 ' + fmt.n(c.pct_4y, 0) + ' 百分位）；觸發線（之前 4 年最極端的 3%）在 ' + nplPct(c.thr_pct_mcap) + '。' + (tg ? '上一次觸發是 ' + ymd(tg.date) + '（' + fmt.usd(tg.price) + '）。' : '') + (mn ? ymd(mn.top) + ' 週期頂部之後最深只到第 ' + fmt.n(mn.pct_4y, 1) + ' 百分位（' + fmt.date(mn.x) + '，' + fmt.usd(mn.price) + '）' + (mn.pct_4y > 3 ? '，本輪沒有觸發。' : '。') : ''),
        '30-day total ' + nplB(c.usd_m) + ' (' + nplPct(c.pct_mcap) + ' of market cap, 4-year percentile ' + fmt.n(c.pct_4y, 0) + '); the trigger line (most extreme 3% of the prior 4 years) is at ' + nplPct(c.thr_pct_mcap) + '.' + (tg ? ' The last trigger was ' + ymd(tg.date) + ' (' + fmt.usd(tg.price) + ').' : '') + (mn ? ' Since the ' + ymd(mn.top) + ' cycle top the deepest reading was only percentile ' + fmt.n(mn.pct_4y, 1) + ' (' + fmt.date(mn.x) + ', ' + fmt.usd(mn.price) + ')' + (mn.pct_4y > 3 ? '; it has not triggered this cycle.' : '.') : ''));
    }
    var s7 = n.sum7_usd_m, p7 = n.sum7_prev_usd_m, ls = n.loss_spike_last;
    var tr = s7 < 0 ? ['近一週整體轉為認賠賣出', 'the past week turned to net loss selling'] : p7 <= 0 ? ['前一週以認賠為主，這週轉為獲利賣出', 'the prior week was net loss selling; this week is net profit'] : s7 < p7 * 0.6 ? ['獲利了結明顯降溫', 'profit taking has clearly cooled'] : s7 > p7 * 1.4 ? ['獲利了結增溫', 'profit taking is heating up'] : ['獲利了結大致持平', 'profit taking is roughly flat'];
    return _T('最新 ' + ymd(n.date) + ' ' + nplB(n.usd_m) + '（近一年第 ' + fmt.n(n.rank_1y, 0) + ' 百分位）。近 7 日合計 ' + nplB(s7) + '，前 7 日 ' + nplB(p7) + '：' + tr[0] + '。' + (ls ? '最近一次明顯認賠（近一年最極端的 2%）是 ' + ymd(ls.date) + ' ' + nplB(ls.usd_m) + '。' : ''),
      'Latest ' + ymd(n.date) + ' ' + nplB(n.usd_m) + ' (1-year percentile ' + fmt.n(n.rank_1y, 0) + '). Past 7 days ' + nplB(s7) + ', prior 7 days ' + nplB(p7) + ': ' + tr[1] + '.' + (ls ? ' The last clear loss spike (most extreme 2% of the past year) was ' + ymd(ls.date) + ' ' + nplB(ls.usd_m) + '.' : ''));
  }
  function nplLegend() {
    return nplMode === 'cum' ? legend([[_T('BTC 價格（對數）', 'BTC price (log)'), 'var(--ink)'], [_T('30 日累計淨獲利', '30-day net profit'), 'var(--up)'], [_T('30 日累計淨認賠', '30-day net loss'), 'var(--down)'], [_T('觸發線：4 年第 3 百分位', 'Trigger: 4-year 3rd percentile'), 'var(--down)'], [_T('首次觸發', 'First trigger'), 'var(--s2)']])
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
      _T('<p class="note">算法：實現市值（市值 ÷ MVRV）當日變化減去當天新挖出的幣，等於當天移動的幣「賣價 − 上次移動價」的淨和；和 Glassnode 的 Net Realized Profit/Loss 對照，方向與大小相符。只有淨值；每日模式的粗外圈＝在之前一年最極端的 2%；30 日累計模式以市值百分比顯示，紅線是之前 4 年第 3 百分位（逐日計算，只用當時已知資料）。只作讀值。</p>',
         '<p class="note">Method: the daily change in realized cap (market cap ÷ MVRV) minus newly mined coins equals the net of “sale price − last-moved price” for coins moved that day; it matches Glassnode\'s Net Realized Profit/Loss in direction and size. Net only; in daily mode a thick ring marks the most extreme 2% of the prior year; the 30-day mode is shown as % of market cap, and the red line is the prior 4 years\' 3rd percentile (computed day by day from data known at the time). Reading only.</p>'),
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
    var note = '<p class="note">' + _T('資料：BitInfoCharts 依地址餘額分層的每日持幣量（2021-05 起）。限制：一個地址不等於一個人，交易所與 ETF 託管用少數大地址集中保管客戶的幣，錢包整理也會讓幣在分層之間移動，所以單日的大跳動常是整理而非買賣；看 30 日以上的方向比較可靠。「本段以來」＝自價格版「短週期」目前這一段的起點（' + (W.leg_start || '—') + '）。只作讀值，不連動出場規則。',
      'Data: BitInfoCharts daily holdings by address-balance tier (since 2021-05). Limits: one address is not one person; exchanges and ETF custodians hold client coins in a few large addresses, and wallet reshuffles move coins between tiers, so single-day jumps are often housekeeping, not trading — the direction over 30+ days is more reliable. “This leg” = since the start of the current short-cycle leg on the Price page (' + (W.leg_start || '—') + '). Readings only; not linked to the exit rules.') + '</p>';
    return panel('span-12', _T('鯨魚與大戶動向', 'Whale and big-holder activity'), 'BitInfoCharts · ' + fmt.md(W.date), say + tb + '<div class="panel-h" style="margin-top:14px"><h2>' + _T('30 日淨變化（顆）', '30-day net change (BTC)') + '</h2>' + legend([[_T('鯊魚 100–1K', 'Sharks 100–1K'), 'var(--s4)'], [_T('鯨魚 1K–10K', 'Whales 1K–10K'), 'var(--s1)'], [_T('≥10K', '≥10K'), 'var(--s3)']]) + '</div><div class="chart" id="c-whale"></div>' + note);
  }
  function drawWhale(el) {
    var r = (D.onchain.whales || {}).rows || [], f = function (i) { return r.map(function (x) { return [x[0], x[i] == null ? null : x[i] / 1e3]; }); };
    lineChart(el, { h: 220, series: [{ name: _T('鯊魚 100–1K', 'Sharks 100–1K'), data: f(1), color: 'var(--s4)' }, { name: _T('鯨魚 1K–10K', 'Whales 1K–10K'), data: f(2), color: 'var(--s1)' }, { name: '≥10K', data: f(3), color: 'var(--s3)', w: 1.4 }], refs: [{ y: 0, color: 'var(--ink-3)' }], yFmt: function (x) { return x + 'K'; }, tipFmt: function (x) { return (x > 0 ? '+' : '') + x.toFixed(1) + 'K BTC'; }, aria: _T('大戶 30 日淨變化', 'Big-holder 30-day net change') });
  }

  /* 資料健康（2026-10-12）：管線錯誤（meta.errors）與各來源資料日期。超過預期延遲的標 ⚠；全部正常時只顯示一行 */
  function healthHtml() {
    var bd = D.meta.bar_date, age = function (d) { return d ? dnOf(bd) - dnOf(String(d).slice(0, 10)) : null; };
    var oc = D.onchain.metrics || {}, etf = (D.flows.etf || []).filter(function (r) { return !r.partial; }), tm = D.cycle.tidemark || {}, fl = (D.chips || {}).flow || {};
    var src = [   // [名稱, 資料日期, 可接受的最大延遲（天）]
      [_T('價格（Kraken）', 'Price (Kraken)'), bd, 0],
      [_T('頂部三指標（CoinMetrics）', 'Top-3 indicators (CoinMetrics)'), D.cycle.p6_date, 2],
      [_T('持有者成本（bitcoin-data）', 'Holder cost basis (bitcoin-data)'), (oc['sth-realized-price'] || {}).date, 7],
      [_T('短期持有者獲利（bitcoin-data）', 'STH in profit (bitcoin-data)'), (fl.sth_in_profit_pct || {}).date, 3],
      [_T('流動性供給（bitcoin-data）', 'Liquid supply (bitcoin-data)'), (oc['illiquid-supply'] || {}).date, 3],
      [_T('ETF 流量（The Block）', 'ETF flows (The Block)'), (etf[etf.length - 1] || {}).d, 4],
      ['Tidemark', tm.price_date, 2],
      // 2026-10-21：補上 10/14 之後新增、原本沒列的來源
      [_T('短期持有者 SOPR（CheckOnChain）', 'STH-SOPR (CheckOnChain)'), (((D.chips || {}).viz || {}).sopr || {}).date, 2],
      [_T('淨實現損益（CoinMetrics）', 'Net realized P/L (CoinMetrics)'), (D.onchain.npl || {}).date, 2],
      [_T('籌碼分布 URPD（bitcoin-data）', 'URPD (bitcoin-data)'), ((D.chips || {}).urpd || {}).date, 2],
      [_T('美債殖利率（FRED）', 'Treasury yields (FRED)'), (((D.flows.fred || {}).DGS10) || {}).last_date, 4]
    ];
    if (D.onchain.whales) src.push([_T('鯨魚分層（BitInfoCharts）', 'Whale tiers (BitInfoCharts)'), D.onchain.whales.date, 2]);   // 2026-10-21 起暫停，沒有資料就不列
    if (D.flows.stables) src.push([_T('穩定幣（DefiLlama）', 'Stablecoins (DefiLlama)'), D.flows.stables.date, 2]);
    if ((D.chips || {}).cohort) src.push([_T('長短期持有者籌碼（CheckOnChain／推算）', 'LTH/STH supply split (CheckOnChain / estimate)'), D.chips.cohort.now_date || D.chips.cohort.date, 3]);   // 2026-10-27 起
    if (D.onchain.sth_pnl) src.push([_T('短期持有者實現損益（CheckOnChain）', 'STH realized P/L (CheckOnChain)'), D.onchain.sth_pnl.date, 2]);   // 2026-10-23 起；第一次跑管線前沒有資料就不列
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
    if (cp) it.push([_T('Coinbase 溢價', 'Coinbase premium'), fmt.pct(cp.avg7, 3), _T('Coinbase（美元）比 Binance（USDT）貴 ' + fmt.pct(cp.avg7, 3) + '（7 日平均；30 日平均 ' + fmt.pct(cp.avg30, 3) + '）：', 'Coinbase (USD) vs. Binance (USDT): ' + fmt.pct(cp.avg7, 3) + ' (7-day avg; 30-day avg ' + fmt.pct(cp.avg30, 3) + '): ') +
      (cp.avg7 > 0.05 ? _T('美國買盤較強，常見於機構或 ETF 需求升溫。', 'US demand is stronger, often a sign of rising institutional or ETF demand.') : cp.avg7 < -0.05 ? _T('美國買盤偏弱，賣壓多來自美國。', 'US demand is weaker; selling is coming more from the US.') : _T('兩邊差不多，美國與海外買盤平衡。', 'roughly even — US and offshore demand are balanced.')) + _T('USDT 偏離 1 美元時會有誤差。', ' Deviations of USDT from $1 add noise.'), cp.avg7 > 0.05 ? 'pos' : cp.avg7 < -0.05 ? 'neg' : 'neu']);
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
    return (sc ? panel('span-6', _T('穩定幣總供給', 'Total stablecoin supply'), 'DefiLlama · ' + _T('近 2 年 · 十億美元', 'last 2 years · USD billions'), '<div class="chart" id="c-stab"></div>') : '') +
      (cp ? panel('span-6', _T('Coinbase 溢價', 'Coinbase premium'), _T('Coinbase ÷ Binance 收盤 − 1 · 近 300 天', 'Coinbase ÷ Binance close − 1 · last 300 days'), legend([[_T('每日', 'Daily'), 'var(--ink-3)'], [_T('7 日平均', '7-day avg'), 'var(--s1)']]) + '<div class="chart" id="c-cbp"></div>') : '');
  }
  function drawFlowCharts() {
    var sc = D.flows.stables, cp = D.flows.cb_premium;
    if (sc) mount($('#c-stab'), function (el) { lineChart(el, { h: 200, series: [{ name: _T('穩定幣', 'Stablecoins'), data: sc.rows, color: 'var(--s4)', area: true }], yFmt: function (x) { return '$' + x.toFixed(0) + 'B'; }, tipFmt: function (x) { return '$' + x.toFixed(1) + 'B'; }, aria: _T('穩定幣總供給', 'Total stablecoin supply') }); });
    if (cp) mount($('#c-cbp'), function (el) { var r = cp.rows, ma = r.map(function (x, i) { if (i < 6) return [x[0], null]; var s = 0; for (var k = i - 6; k <= i; k++) s += r[k][1]; return [x[0], s / 7]; });
      lineChart(el, { h: 200, series: [{ name: _T('每日', 'Daily'), data: r, color: 'var(--ink-3)', w: 1, end: false }, { name: _T('7 日平均', '7-day avg'), data: ma, color: 'var(--s1)' }], refs: [{ y: 0, color: 'var(--ink-3)' }], yFmt: function (x) { return x.toFixed(2) + '%'; }, tipFmt: function (x) { return (x > 0 ? '+' : '') + x.toFixed(3) + '%'; }, aria: _T('Coinbase 溢價', 'Coinbase premium') }); });
  }

  /* ---------------- Views ---------------- */
  var V = {};
  var ROUTES = [
    ['overview', _t('頭版'), _t('今天的比特幣'), 'M4 5h16v14H4zM8 9h8M8 13h5', 'FRONT PAGE'],
    ['news', _t('消息'), _t('新聞與解讀'), 'M5 4h11l3 3v13H5zM9 9h6M9 13h6M9 17h4', 'THE BRIEF'],
    ['cycle', _t('週期'), _t('離頂部還多遠'), 'M12 3a9 9 0 1 0 9 9M12 7a5 5 0 1 0 5 5M12 12h9', 'CYCLE'],
    ['market', _t('價格'), _t('日線與關鍵價位'), 'M4 19V9m5 10V5m5 14v-7m5 7V8', 'PRICE'],
    ['deriv', _t('衍生品'), _t('波動率與選擇權'), 'M3 17c3-8 6-8 9 0s6 8 9 0', 'DERIVATIVES'],
    ['flows', _t('資金'), _t('ETF 與宏觀'), 'M4 7h16M4 12h10M4 17h6', 'FLOWS · MACRO'],
    ['onchain', _t('鏈上'), _t('持有者與籌碼'), 'M7 7h4v4H7zM13 13h4v4h-4zM11 9h4M9 11v4', 'ON-CHAIN'],
    ['exit', _t('出場框架'), _t('何時分批賣'), 'M4 20h4v-4h4v-4h4V8h4V4', 'EXIT PLAN'],
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
    var newsBlock = news.length ? _t('<div class="sec-h"><h2>今日要聞</h2><span class="en">The Brief</span><hr><a href="#news">全部 ') + news.length + _t(' 則 →</a></div><div class="news-front">') + newsItem(news[0], true) + '<div class="news-side">' + news.slice(1, 4).map(function (n, i) { return newsItem(n); }).join('') + '</div></div>' : '';
    var kp = '<div class="kpis">' +
      kpi(_t('MVRV ÷ 前一輪高點'), fmt.n(cm.mvrv_vs_prior, 3), _t('賣出線 0.75 · 2025 頂 0.78'), cm.mvrv_vs_prior / 0.75 * 100) +
      kpi(_t('冪律倍數'), fmt.n(pl.ratio, 2) + '×', _t('合理價 ') + fmt.usd(pl.fair), (pl.ratio || 0) / 1.2 * 100) +
      kpi(_t('Tidemark 頂 / 底'), fmt.n((tm.top || {}).signal, 0) + ' / ' + fmt.n((tm.bottom || {}).signal, 0), _t('門檻 50 · ') + fmt.md(tm.price_date) + _t(' 資料')) +
      kpi(_t('頂部三指標百分位'), ['mvrv_z', 'nupl', 'puell'].map(function (k) { return fmt.n(p6[k], 0); }).join(' / '), _t('任兩項到 80 進入頂部區'), ((p6.mvrv_z || 0) + (p6.nupl || 0) + (p6.puell || 0)) / 3 / 0.8) +
      kpi(_t('離出場第一階'), fmt.pct(ex.next_step_dist_pct, 0), fmt.usd(ex.next_step) + _t(' 起每階 12.5%'), 100 - Math.min(100, ex.next_step_dist_pct)) + '</div>';
    var ev = (N && N.events || []).map(function (e) { var dd = dnOf(e.date) - dnOf(D.meta.bar_date); return '<div class="event"><span class="d">' + e.date.slice(5).replace('-', '/') + '</span><span>' + esc(e.label) + '</span><span class="in' + (dd === 1 ? ' now' : '') + '">' + (dd > 1 ? dd - 1 + _t(' 天後') : dd === 1 ? _t('今天') : _t('已過')) + '</span></div>'; }).join('');
    var plan = _t('<div class="sec-h"><h2>今天該做什麼</h2><span class="en">The Plan</span><hr>') + staleTag() + '</div><div class="grid">' +
      panel('span-7', _t('今天該做什麼、盯什麼'), _t('依出場框架 · 非投資建議'), actionsHtml()) + panel('span-5', _t('今天變了什麼'), _t('相對上一期'), changesHtml()) + '</div>';
    var zhNote = ZH_ONLY ? '<p class="note" style="margin:0">The English edition of today’s written commentary (headline, news and plan) is not published yet, so those parts are shown in Chinese. All data and readings are in English.</p>' : '';
    return zhNote + front + tapeHtml() + healthHtml() + findingsHtml() + newsBlock + plan +
      _t('<div class="sec-h"><h2>今日數據</h2><span class="en">The Numbers</span><hr></div>') + kp +
      '<div class="grid">' + interpPanel(ovInterp()) + panel('span-12', _t('離出場線還多遠'), _t('以 ') + fmt.md(D.meta.bar_date) + _t(' 收盤計 · 對數刻度'), '<div class="runway">' + runwaySvg() + '</div>') +
      panel('span-7', _t('價格近一年'), _t('CoinMetrics 每 7 天'), '<div class="chart" id="c-ov-px"></div>') +
      panel('span-5', _t('接下來的日期'), '', '<div class="events">' + ev + '</div>') + '</div>';
  };
  V.overview.after = function () {
    bindMega();
    var hist = D.price.history || [], cut = hist[hist.length - 1][0] - 400;
    mount($('#c-ov-px'), function (el) { lineChart(el, { h: 250, series: [{ name: _t('價格'), data: hist.filter(function (p) { return p[0] >= cut; }), color: 'var(--s1)', area: true }], refs: [{ y: D.price.ma.sma200, color: 'var(--ink-3)', label: _t('200 日均線 ') + fmt.k(D.price.ma.sma200), below: true }], tipFmt: fmt.usd, aria: _t('近一年價格') }); });
  };

  V.news = function () {
    var news = (N && N.news || []);
    var rs = '<div class="grid" style="margin-top:28px">' + panel('span-12', _t('權威研報怎麼看'), _t('Glassnode · The Block · K33 · Coinbase Institutional 等'), researchHtml(), staleTag()) + '</div>';
    if (!news.length) return _t('<p class="err">今天還沒有整理好的消息。</p>') + rs;
    var cats = ['*'].concat(news.map(function (n) { return n.cat; }).filter(function (c, i, a) { return a.indexOf(c) === i; }));
    var cnt = function (k) { return news.filter(function (n) { return n.impact === k; }).length; };
    return _t('<div class="news-sum"><div><span class="note">偏多</span><b style="color:var(--up)">') + ('0' + cnt('bull')).slice(-2) + _t('</b></div><div><span class="note">偏空</span><b style="color:var(--down)">') + ('0' + cnt('bear')).slice(-2) + _t('</b></div><div><span class="note">中性</span><b>') + ('0' + cnt('neutral')).slice(-2) + '</b></div></div>' +
      _t('<div class="filters" id="nf" role="group" aria-label="分類">') + cats.map(function (c, i) { return '<button type="button" aria-pressed="' + (i === 0) + '" data-c="' + esc(c) + '">' + esc(c === '*' ? _t('全部') : catT(c)) + '</button>'; }).join('') + '</div>' +
      _t('<div class="news-grid" id="ng"></div><p class="note">每則消息都查證過發布日期；「解讀」說明它對比特幣的意義，並對照本站的數據。消息只作參考，不改變任何出場規則。</p>') + rs;
  };
  V.news.after = function () {
    var news = (N && N.news || []).slice().sort(function (a, b) { return (b.weight || 0) - (a.weight || 0) || (b.time > a.time ? 1 : -1); });
    function draw(cat) { $('#ng').innerHTML = news.filter(function (n) { return cat === '*' || n.cat === cat; }).map(function (n, i) { return '<article class="news-card"><div class="news-meta"><span class="cat">' + esc(catT(n.cat)) + '</span>' + impChip(n.impact) + '<span>' + esc(n.time.slice(5).replace('-', '/')) + '</span></div><h3>' + esc(n.title) + _t('</h3><div class="read-box"><b class="lbl">解讀</b>') + esc(n.read) + _t('</div><div class="src-link">來源：<a href="') + esc(n.url) + '" target="_blank" rel="noopener">' + esc(n.source) + '</a></div>' + (n.module ? '<a class="go" href="#' + n.module + _t('">看相關數據 →</a>') : '') + '</article>'; }).join(''); }
    draw('*');
    $('#nf').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; this.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); draw(b.getAttribute('data-c')); });
  };

  V.cycle = function () {
    var cm = D.cycle.cm, pl = D.cycle.powerlaw || {}, tm = D.cycle.tidemark || {}, p6 = D.cycle.p6 || {}, st = D.cycle.stage || {}, M = D.cycle.model;
    var w = M.weights;
    return readBar('cycle') + '<div class="grid">' +
      panel('span-12', _t('市場階段：') + (STAGE[st.stage] || ['—'])[0], _t('P23 · 熊市 → 轉換期 → 牛市'), stageHtml()) +
      panel('span-12', _t('長期路徑：四種走法'), _t('每月底重估 · 下次 ') + M.next_review, legend([[_t('直接修復 ') + w['直接修復'] + '%', 'var(--s4)', 'dash'], [_t('淺回檔 ') + w['淺回檔'] + '%', 'var(--s1)', 'dash'], [_t('基準雙底 ') + w['基準雙底'] + '%', 'var(--s2)', 'dash'], [_t('延後新低 ') + w['延後新低'] + '%', 'var(--s3)', 'dash'], [_t('已實現'), 'var(--ink)'], [_t('頂部 80% 區間'), 'var(--flare)', 'box']]) + _t('<div class="chart" id="c-path"></div><p class="note">頂部模型：中位 ') + fmt.usd(M.top_model.median) + _t('，80% 區間 ') + fmt.k(M.top_model.p10) + '–' + fmt.k(M.top_model.p90) + _t('，時間 ') + esc(tx(M.top_model, 'timing')) + _t('。路徑是本站的預測，2028 年以後只供量級參考。</p>')) +
      panel('span-7', _t('MVRV ÷ 前一輪高點'), _t('CoinMetrics · 2021 起'), _t('<p class="say">現在 <b>') + fmt.n(cm.mvrv_vs_prior, 3) + _t('</b>；連 5 天站上 0.75 是出場框架的第一個鏈上賣點。') + esc((p20Read() || [''])[0]) + '</p><div class="chart" id="c-p20"></div>') +
      panel('span-5', _t('頂部三指標'), fmt.md(D.cycle.p6_date) + _t(' · 四年百分位'), '<p class="say">' + esc((p6Read() || [''])[0]) + '</p><div class="meters">' + meter('MVRV Z', _t('<0 底 · >3.5 頂'), p6.mvrv_z, fmt.n(p6.mvrv_z, 0), _t('百分位'), [80, 85, 90]) + meter('NUPL', _t('淨未實現損益'), p6.nupl, fmt.n(p6.nupl, 0), _t('百分位'), [80, 85, 90]) + meter('Puell', _t('礦工收入倍數'), p6.puell, fmt.n(p6.puell, 0), _t('百分位'), [80, 85, 90]) + _t('</div><p class="note">任兩項到 80 進入頂部區；到 85 連 5 天多賣兩階；到 90 在 10 個交易日內賣完。</p>') ) +
      panel('span-7', _t('冪律：價格 ÷ 合理價'), _t('每天只用當天以前資料擬合'), _t('<p class="say">現在 <b>') + fmt.n(pl.ratio, 2) + _t(' 倍</b>（合理價 ') + fmt.usd(pl.fair) + _t('）。頂部倍數每輪縮小，照這個速度，下一輪頂部約在合理價的 ') + fmt.n((pl.next_top_ratio || [])[0], 2) + '–' + fmt.n((pl.next_top_ratio || [])[1], 2) + _t(' 倍。') + esc((plRead() || [''])[0]) + '</p><div class="chart" id="c-pl"></div>', _t('<div class="seg" id="pl-seg"><button aria-pressed="false" data-v="all">2012 起</button><button aria-pressed="true" data-v="2020">2020 起</button></div>')) +
      panel('span-5', _t('Tidemark 綜合訊號'), _t('第三方模型 · ') + fmt.md(tm.price_date) + _t(' 資料'), '<p class="say">' + esc((tmRead() || [''])[0]) + '</p><div class="meters">' + meter(_t('頂部訊號'), _t('≥50 窗口 · ≥70 警戒'), (tm.top || {}).signal || 0, fmt.n((tm.top || {}).signal, 1), (tm.top || {}).level || '—', [50, 70]) + meter(_t('熱度'), _t('五類加權'), (tm.top || {}).heat || 0, fmt.n((tm.top || {}).heat, 1), (tm.top || {}).zone || '', [40, 65]) + meter(_t('底部訊號'), _t('≥50 底部區'), (tm.bottom || {}).signal || 0, fmt.n((tm.bottom || {}).signal, 1), (tm.bottom || {}).level || '—', [50, 70]) + meter(_t('冷度'), _t('估值・礦工・價格結構'), (tm.bottom || {}).cold || 0, fmt.n((tm.bottom || {}).cold, 1), '', []) + '</div>' +
        '<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:62%"><col style="width:38%"></colgroup><tbody>' + (tm.cats || []).map(function (x) { return '<tr><td>' + esc(_T(x[0], TM_CAT_EN[x[0]] || x[0])) + (x[2] === 'partial' ? _t('＊') : '') + '</td><td><div class="pct"><i><b class="' + ((x[1] || 0) >= 80 ? 'hot' : '') + '" style="width:' + (x[1] || 0) + '%"></b></i><span class="num">' + (x[1] == null ? '—' : fmt.n(x[1], 0)) + '</span></div></td></tr>'; }).join('') + '</tbody></table></div><p class="note">' + esc(tmVerdict(tm.cycle_test)) + '</p>') +
      '</div>';
  };
  V.cycle.after = function () {
    drawEv();
    var M = D.cycle.model, cols = { '直接修復': 'var(--s4)', '淺回檔': 'var(--s1)', '基準雙底': 'var(--s2)', '延後新低': 'var(--s3)' };
    var md = function (y, m) { return Math.round(Date.UTC(y, m - 1, 15) / 864e5); };
    var series = Object.keys(M.nodes).map(function (k) { return { name: _t(k), data: M.nodes[k].map(function (p) { return [md(p[0], p[1]), p[2]]; }), color: cols[k], dash: '5 5', w: 1.8, end: false, smooth: true }; });
    var real = M.realized.map(function (p) { return [md(p[0], p[1]), p[2]]; }); real.push([dnOf(D.meta.bar_date), D.price.bar.c]);
    series.push({ name: _t('已實現'), data: real, color: 'var(--ink)', w: 2.6, smooth: true });
    mount($('#c-path'), function (el) { lineChart(el, { h: el.clientWidth < 520 ? 260 : 340, log: true, series: series, hbands: [{ y0: M.top_model.p10, y1: M.top_model.p90, color: 'var(--flare-dim)' }], refs: [{ y: M.top_model.median, color: 'var(--flare)', label: _t('頂部中位 ') + fmt.k(M.top_model.median) }], vlines: [{ x: dnOf(D.cycle.next_halving_est), label: _t('2028/04 減半') }], tipFmt: fmt.usd, aria: _t('四條長期路徑') }); });
    var p20 = D.cycle.p20 || {};
    mount($('#c-p20'), function (el) { var top = dnOf('2025-10-06'), tv = (p20.rows || []).filter(function (r) { return Math.abs(r[0] - top) <= 2; })[0]; lineChart(el, { series: [{ name: _t('比值'), data: p20.rows || [], color: 'var(--s1)', area: true }], refs: [{ y: 0.75, color: 'var(--down)', label: _t('0.75 第一階 ≈ ') + fmt.k(p20.k075) }, { y: 0.8, color: 'var(--down)', label: _t('0.80 第二階'), below: false }], marks: tv ? [{ x: tv[0], y: tv[1], label: _t('2025 頂 ') + tv[1].toFixed(2), left: true }] : [], yFmt: function (v) { return v.toFixed(1); }, tipFmt: function (v) { return v.toFixed(3); }, aria: _t('MVRV 除以前一輪高點') }); });
    var pl = D.cycle.powerlaw || {}, rng = '2020';
    function drawPl(el) {
      var rows = (pl.rows || []).map(function (r) { return [r[0], Math.pow(10, r[1])]; }); if (rng === '2020') rows = rows.filter(function (r) { return r[0] >= dnOf('2020-01-01'); });
      var mk = (pl.tops || []).concat(pl.bottoms || []).map(function (t) { var x = dnOf(t[0]); return rows.length && x >= rows[0][0] ? { x: x, y: t[1], label: t[1].toFixed(2), color: t[1] >= 1 ? 'var(--flare)' : 'var(--orbit)', below: t[1] < 1 } : null; }).filter(Boolean);
      lineChart(el, { log: true, series: [{ name: _t('倍數'), data: rows, color: 'var(--s3)' }], hbands: [{ y0: (pl.bottom_band || [0.24, 0.48])[0], y1: (pl.bottom_band || [0.24, 0.48])[1], color: 'var(--orbit-dim)' }], refs: [{ y: 1, color: 'var(--ink-3)', label: _t('1.0 合理價') }], marks: mk, yFmt: function (v) { return v >= 1 ? v.toFixed(v >= 10 ? 0 : 1) : v.toFixed(2); }, tipFmt: function (v) { return v.toFixed(2) + '×'; }, aria: _t('價格除以冪律合理價') });
    }
    mount($('#c-pl'), drawPl);
    $('#pl-seg').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; rng = b.getAttribute('data-v'); this.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); drawPl($('#c-pl')); });
  };

  V.market = function () {
    var p = D.price, ma = p.ma, c = p.bar.c, vp = p.volprofile || {};
    var lv = [[D.exit.framework.ladder[0], _t('出場第一階')], [D.cycle.cm.k080_price, _t('MVRV 0.80 線')], [D.cycle.cm.k075_price, _t('MVRV 0.75 線')], [D.cycle.cm.price_ath_close, _t('歷史收盤新高')], [vp.va_high_outer, _t('近 20 日價值區上緣')], [vp.poc, _t('近 20 日成交最密集價')], [ma.sma20, _t('20 日均線')], [vp.va_low, _t('近 20 日價值區下緣')], [ma.sma50, _t('50 日均線')], [ma.sma200, _t('200 日均線（避險線）')], [D.cycle.cm.realized_price, _t('全網平均成本（實現價）')]].filter(function (x) { return x[0]; }).sort(function (a, b) { return b[0] - a[0]; });
    var tbl = _t('<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:30%"><col style="width:24%"><col style="width:46%"></colgroup><thead><tr><th>價位</th><th class="num">距收盤</th><th>是什麼</th></tr></thead><tbody>') + lv.map(function (x) { var d = (x[0] / c - 1) * 100; return '<tr><td class="num" style="text-align:left">' + fmt.usd(x[0]) + '</td><td class="num" style="color:' + (d >= 0 ? 'var(--up)' : 'var(--down)') + '">' + fmt.pct(d) + '</td><td>' + x[1] + '</td></tr>'; }).join('') + '</tbody></table></div>';
    var ma2 = [[_t('5 日'), ma.sma5], [_t('20 日'), ma.sma20], [_t('50 日'), ma.sma50], [_t('111 日'), ma.sma111], [_t('200 日'), ma.sma200], [_t('350 日'), ma.sma350]];
    var mat = '<div class="meters">' + ma2.map(function (m) { var d = (c / m[1] - 1) * 100; return meter(m[0] + _t('均線'), fmt.usd(m[1]), 50 + Math.max(-50, Math.min(50, d * 2)), fmt.pct(d), d >= 0 ? _t('價格在上方') : _t('價格在下方'), [50]); }).join('') + _t('</div><p class="note">中線＝均線位置；圓點越往右，價格越高於該均線。</p>');
    return readBar('market') + '<div class="kpis">' + kpi(_t('收盤'), fmt.usd(c), fmt.pct(p.bar.chg_pct, 2) + _t(' · 當日區間位置 ') + fmt.n(p.bar.close_pos_pct, 0) + '%') + kpi(_t('ATR14（簡單平均）'), fmt.usd(p.atr.atr14), _t('約 ') + fmt.n(p.atr.atr14 / c * 100, 1) + _t('% / 日')) + kpi(_t('實際波動 RV30'), fmt.n(p.vol.rv30, 1) + '%', 'RV7 ' + fmt.n(p.vol.rv7, 1) + '% · RV90 ' + fmt.n(p.vol.rv90, 1) + '%') + kpi(_t('Mayer 倍數'), fmt.n(p.mayer.mayer, 2), _t('價格 ÷ 200 日均線')) + kpi('Pi Cycle', fmt.n(p.pi_cycle, 2), _t('111 日 ÷ 2×350 日；≥1 為歷史頂部訊號'), p.pi_cycle * 100) + '</div><div class="grid">' + interpPanel(mkInterp()) + swingPanel() +
      panel('span-8', _t('近 20 天 K 線'), _t('Kraken 日線 · UTC'), '<div class="chart" id="c-cd"></div>') +
      panel('span-4', _t('關鍵價位'), '', levelsSay(lv, c) + tbl) +
      panel('span-6', _t('價格與均線'), '', maSay(ma, c) + mat) +
      panel('span-6', _t('價格長期走勢'), _t('CoinMetrics · 對數刻度'), '<div class="chart" id="c-long"></div>', _t('<div class="seg" id="lg-seg"><button aria-pressed="false" data-v="all">2012 起</button><button aria-pressed="true" data-v="4y">近 4 年</button></div>')) + '</div>';
  };
  V.market.after = function () {
    var p = D.price, H = p.history || [], rng = '4y';
    mount($('#c-cd'), function (el) { candleChart(el, p.rows20 || [], [{ v: p.ma.sma20, label: _t('20 日 ') + fmt.k(p.ma.sma20), color: 'var(--s1)' }, { v: (p.volprofile || {}).va_high_outer, label: _t('價值區上緣'), color: 'var(--flare)' }, { v: (p.volprofile || {}).poc, label: 'POC', color: 'var(--ink-3)' }]); });
    function drawLong(el) {
      var rows = rng === '4y' ? H.filter(function (r) { return r[0] >= H[H.length - 1][0] - 1461; }) : H;
      var mk = D.cycle.tops.concat(D.cycle.bottoms).map(function (t) { var x = dnOf(t[0]); return rows.length && x >= rows[0][0] ? { x: x, y: t[1], label: fmt.k(t[1]), color: t[1] > 50000 || D.cycle.tops.some(function (q) { return q[0] === t[0]; }) ? 'var(--flare)' : 'var(--orbit)', below: !D.cycle.tops.some(function (q) { return q[0] === t[0]; }), left: true } : null; }).filter(Boolean);
      lineChart(el, { log: true, series: [{ name: _t('價格'), data: rows, color: 'var(--s1)', area: true }], marks: mk, vlines: D.cycle.halvings.map(function (h) { return { x: dnOf(h), label: '' }; }), tipFmt: fmt.usd, aria: _t('長期價格') });
    }
    mount($('#c-long'), drawLong);
    $('#lg-seg').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; rng = b.getAttribute('data-v'); this.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); drawLong($('#c-long')); });
  };

  V.deriv = function () {
    var dv = D.deriv, d = dv.deriv || {}, r = dv.rr25 || {}, o = dv.options || {};
    var big = (o.expiries || []).slice().sort(function (a, b) { return b.oi - a.oi; })[0] || {};
    return readBar('deriv') + '<div class="kpis">' + kpi('DVOL', fmt.n((dv.dvol || {}).value, 1), _t('一年第 ') + fmt.n((dv.dvol || {}).pct_1y, 0) + _t(' 百分位'), (dv.dvol || {}).pct_1y) + (concNow() ? kpi(_T('籌碼集中度 ±5%', 'Supply within ±5%'), fmt.n(concNow().pct, 1) + '%', _T('URPD ' + fmt.md(concNow().urpd_date) + ' · 只作讀值', 'URPD ' + fmt.md(concNow().urpd_date) + ' · reading only')) : '') + kpi(_t('IV − RV30（同源）'), fmt.n((dv.samesource || {}).iv_minus_rv30, 2), _t('負值＝隱含波動比實際便宜')) + kpi(_t('永續資金費率'), fmt.pct(fundNow(), 1), _T('年化 · 多家加權 · 基差中位 ', 'annualized · multi-venue weighted · basis ') + fmt.n(d.basis_median, 1) + '%') + kpi(_t('25Δ 風險逆轉'), fmt.n(r.rr, 2), r.expiry ? r.expiry + ' · ATM ' + fmt.n(r.atm_iv, 1) + '%' : _t('本日沒有可計算的合約')) + kpi(_t('選擇權未平倉'), fmt.n(o.total_oi) + _t(' 顆'), _t('最大到期 ') + (big.expiry || '—') + _t('（') + fmt.n(big.share, 0) + _t('%）')) + '</div><div class="grid">' + interpPanel(dvInterp()) +
      panel('span-8', _t('隱含波動 vs 實際波動'), _t('Deribit DVOL · Kraken RV30 · 近一年'), legend([['DVOL', 'var(--s1)'], ['RV30', 'var(--s2)']]) + '<div class="chart" id="c-vol"></div>') +
      panel('span-4', _t('期貨基差曲線'), _t('年化 % · 排除 7 天內到期'), basisSay(d.basis_curve) + _t('<div class="chart" id="c-basis"></div><p class="note">資金費率年化 ') + fmt.pct(fundNow(), 1) + _t('；永續 OI ') + fmt.usd(d.perp_oi_usd_m) + _t('M。</p><div class="src-link">外部：<a href="https://www.coinglass.com/pro/futures/LiquidationHeatMap" target="_blank" rel="noopener">CoinGlass 爆倉熱力圖 ↗</a>（以 OI 與假設槓桿推估，非實際倉位）</div>')) +
      (concNow() ? panel('span-12', _T('籌碼集中度（現價 ±5%）', 'Supply concentration (±5% of price)'), _T('URPD ÷ 流通量 · 2026-10-01 起 · 只作讀值', 'URPD ÷ circulating supply · since 2026-10-01 · reading only'), legend([[_T('集中度', 'Concentration'), 'var(--s1)'], [_T('BTC 價格（另一刻度）', 'BTC price (own scale)'), 'var(--ink-3)']]) + '<div class="chart" id="c-conc"></div>') : '') +
      panel('span-6', _t('各到期未平倉'), _t('買權 / 賣權（顆）'), legend([[_t('買權'), 'var(--s4)'], [_t('賣權'), 'var(--s3)']]) + '<div class="chart" id="c-oi"></div>') +
      panel('span-6', _t('最大到期的履約價分布'), ((dv.viz || {}).options || {}).strikes ? dv.viz.options.strikes.expiry + ' · Max Pain ' + fmt.k(dv.viz.options.strikes.maxpain) : '', strikeSay((o.expiries || []).filter(function (e) { return e.expiry === (((dv.viz || {}).options || {}).strikes || {}).expiry; })[0] || big) + '<div id="c-strike"></div>') + bookCard() + '</div>';
  };
  V.deriv.after = function () {
    drawBook();
    var v = D.deriv.viz || {};
    mount($('#c-vol'), function (el) { var rows = (v.vol || {}).rows || []; lineChart(el, { series: [{ name: 'DVOL', data: rows.map(function (r) { return [r[0], r[1]]; }), color: 'var(--s1)' }, { name: 'RV30', data: rows.map(function (r) { return [r[0], r[2]]; }), color: 'var(--s2)' }], yFmt: function (x) { return x.toFixed(0); }, tipFmt: function (x) { return x.toFixed(1) + '%'; }, aria: _t('波動率') }); });
    mount($('#c-conc'), function (el) { var h = (D.chips || {}).conc_hist || []; lineChart(el, { h: 200, series: [{ name: _T('BTC 價格', 'BTC price'), data: h.map(function (r) { return [r[0], r[1]]; }), color: 'var(--ink-3)', w: 1.1, end: false, y2: true, fmt: fmt.usd }, { name: _T('集中度', 'Concentration'), data: h.map(function (r) { return [r[0], r[2]]; }), color: 'var(--s1)' }], yFmt: function (x) { return x.toFixed(1) + '%'; }, tipFmt: function (x) { return x.toFixed(2) + '%'; }, aria: _T('籌碼集中度', 'Supply concentration') }); });
    mount($('#c-basis'), function (el) { var cv = (v.basis || {}).curve || []; lineChart(el, { h: 200, xType: 'num', series: [{ name: _t('年化基差'), data: cv, color: 'var(--s4)', area: true }], xticks: cv.filter(function (p, i) { return i % 2 === 0; }).map(function (p) { return [p[0], Math.round(p[0]) + 'd']; }), xTipFmt: function (x) { return Math.round(x) + _t(' 天到期'); }, yFmt: function (x) { return x.toFixed(1) + '%'; }, tipFmt: function (x) { return x.toFixed(2) + '%'; }, y0: 0, aria: _t('基差曲線') }); });
    mount($('#c-oi'), function (el) {
      var ex = ((v.options || {}).expiries || []), W = Math.max(280, el.clientWidth), Ht = 230, ML = 8, MR = 52, MT = 10, MB = 26, pw = W - ML - MR, ph = Ht - MT - MB;
      var mx = Math.max.apply(null, ex.map(function (e) { return e[2] + e[3]; })) || 1, st = niceStep(mx, 4), top = Math.ceil(mx / st) * st, bw = pw / ex.length, s = '';
      var Y = function (q) { return MT + (1 - q / top) * ph; };
      for (var t = 0; t <= top; t += st) s += '<line class="' + (t ? 'gl' : 'base') + '" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + Y(t).toFixed(1) + '" y2="' + Y(t).toFixed(1) + '"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (Y(t) + 3.5).toFixed(1) + '">' + fmt.k(t) + '</text>';
      ex.forEach(function (e, i) { var x = ML + i * bw + 3, w = bw - 6, yc = Y(e[2]), yp = Y(e[2] + e[3]); s += '<g class="oi" data-i="' + i + '"><rect x="' + x.toFixed(1) + '" y="' + yc.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + (MT + ph - yc).toFixed(1) + '" rx="3" fill="var(--s4)"/><rect x="' + x.toFixed(1) + '" y="' + yp.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + Math.max(0, yc - yp - 2).toFixed(1) + '" rx="3" fill="var(--s3)"/></g><text class="ax" x="' + (x + w / 2).toFixed(1) + '" y="' + (Ht - 8) + '" text-anchor="middle">' + fmt.md(e[0]) + '</text>'; });
      el.innerHTML = svgEl(W, Ht, s, _t('各到期未平倉'));
      el.querySelectorAll('.oi').forEach(function (g) { var e = ex[+g.getAttribute('data-i')]; g.addEventListener('pointermove', function (ev) { showTip(ev.clientX, ev.clientY, '<div class="t">' + e[0] + ' · ' + e[1] + _t(' 天</div><div class="r"><i style="background:var(--s4)"></i><span>買權</span><b>') + fmt.n(e[2]) + _t('</b></div><div class="r"><i style="background:var(--s3)"></i><span>賣權</span><b>') + fmt.n(e[3]) + '</b></div><div class="r"><i></i><span>Max Pain</span><b>' + fmt.k(e[4]) + '</b></div>'); }); g.addEventListener('pointerleave', hideTip); });
    });
    var sk0 = ((v.options || {}).strikes || {}).rows || [], el = $('#c-strike'), cc = D.price.bar.c, bk = {};
    /* 只看收盤 ±30%，依數量自動分箱到 26 列以內，避免出現捲軸 */
    sk0 = sk0.filter(function (r) { return r[0] >= cc * 0.7 && r[0] <= cc * 1.3; });
    var bs = 1000; while (sk0.length && (sk0[sk0.length - 1][0] - sk0[0][0]) / bs > 26) bs = bs === 1000 ? 2500 : bs * 2;
    sk0.forEach(function (r) { var k = Math.floor(r[0] / bs) * bs; if (!bk[k]) bk[k] = [k, 0, 0]; bk[k][1] += r[1]; bk[k][2] += r[2]; });
    var sk = Object.keys(bk).map(function (k) { return bk[k]; }).sort(function (a, b) { return a[0] - b[0]; });
    if (el) { var mx = Math.max.apply(null, sk.map(function (r) { return Math.max(r[1], r[2]); })) || 1, c = D.price.bar.c;
      el.innerHTML = '<div class="ladder dense">' + sk.slice().reverse().map(function (r) { var near = c >= r[0] && c < r[0] + bs; return '<div class="row' + (near ? ' cur' : '') + '" style="grid-template-columns:minmax(0,1fr) 64px minmax(0,1fr)"><span class="b" style="direction:rtl"><i style="width:' + (r[2] / mx * 100).toFixed(1) + '%;background:var(--s3);left:auto;right:0"></i></span><span class="p" style="text-align:center">' + fmt.k(r[0]) + '</span><span class="b"><i style="width:' + (r[1] / mx * 100).toFixed(1) + '%;background:var(--s4)"></i></span></div>'; }).join('') + _t('</div><div class="legend" style="margin-top:8px;justify-content:space-between"><span style="color:var(--s3)"><i></i><b style="color:var(--ink-2);font-weight:400">← 賣權</b></span><span style="color:var(--s4)"><b style="color:var(--ink-2);font-weight:400">買權 →</b><i></i></span></div>'); }
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
  V.flows = function () {
    var fr = D.flows.fred || {}, etf = D.flows.etf || [], full = etf.filter(function (r) { return !r.partial; });
    var last = full[full.length - 1] || {}, s7 = full.slice(-7).reduce(function (a, r) { return a + r.musd; }, 0), p7 = full.slice(-14, -7).reduce(function (a, r) { return a + r.musd; }, 0);
    var nq = fr.NASDAQCOM || {}, dx = fr.DTWEXBGS || {}, tn = fr.DGS10 || {}, rr = D.flows.dfii10 || {}, rc = D.flows.rc_liq || {};
    return readBar('flows') + '<div class="kpis">' + kpi(_t('最近完整日 ETF'), (last.musd >= 0 ? '+' : '') + fmt.n(last.musd, 1) + 'M', fmt.md(last.d) + _t(' · 美元')) + kpi(_t('近 7 個完整日'), (s7 >= 0 ? '+' : '') + fmt.n(s7, 0) + 'M', _t('前 7 日 ') + (p7 >= 0 ? '+' : '') + fmt.n(p7, 0) + 'M') + kpi(_t('BTC–那斯達克 30 日相關'), fmt.n(nq.corr30, 2), fmt.md(nq.last_date) + _t(' · 高於 0.5 代表同漲同跌'), (nq.corr30 + 1) * 50) + kpi(_t('BTC–美元 30 日相關'), fmt.n(dx.corr30, 2), _t('FRED 廣義美元指數'), (dx.corr30 + 1) * 50) + kpi(_t('10 年期實質利率'), fmt.n(rr.value, 2) + '%', _t('20 日 ') + (rr.chg_20obs_bp >= 0 ? '+' : '') + rr.chg_20obs_bp + _t('bp · 名目 ') + fmt.n(tn.last, 2) + '%') + (D.flows.stables ? kpi(_T('穩定幣供給', 'Stablecoin supply'), '$' + fmt.n(D.flows.stables.usd_b, 0) + 'B', _T('30 日 ', '30-day ') + fmt.pct(D.flows.stables.chg30_pct, 2)) : '') + (D.flows.cb_premium ? kpi(_T('Coinbase 溢價', 'Coinbase premium'), fmt.pct(D.flows.cb_premium.avg7, 3), _T('7 日平均 · 30 日 ', '7-day avg · 30-day ') + fmt.pct(D.flows.cb_premium.avg30, 3)) : '') + (rc.chg30_pct != null ? kpi(_t('實現市值 30 日'), fmt.pct(rc.chg30_pct, 2), (rc.zero_now ? _t('≤0 已 ') : _t('>0 已 ')) + rc.state_run_days + _t(' 天 · 90 日 ') + fmt.pct(rc.chg90_pct, 2)) : '') + '</div><div class="grid">' + interpPanel(flInterp(last, s7, p7).concat(flInterp2(s7))) +
      panel('span-12', _t('現貨 ETF 每日淨流量'), _t('The Block（與 Farside 同口徑）· 百萬美元 · 淡色＝暫定或尚未完整'), '<div class="chart" id="c-etf"></div>') + flowCharts() + rcPanel(rc) + '</div>';
  };
  V.flows.after = function () {
    drawFlowCharts();
    var etf = D.flows.etf || [];
    var rc = D.flows.rc_liq || {};
    mount($('#c-rcliq'), function (el) { var r = rc.rows || [], x0 = r.length ? r[0][0] : 0; lineChart(el, { h: 220, series: [{ name: _t('30 日變化'), data: r, color: 'var(--s1)' }], vbands: (rc.episodes || []).filter(function (e) { return dnOf(e.end) >= x0; }).map(function (e) { return { x0: Math.max(x0, dnOf(e.start)), x1: dnOf(e.end) + 1, color: 'var(--down-dim)' }; }), refs: [{ y: 0, color: 'var(--ink-3)', label: _t('0＝流入停滯'), below: true }], yFmt: function (x) { return x + '%'; }, tipFmt: function (x) { return fmt.pct(x, 2); }, aria: _t('實現市值 30 日變化') }); });
    mount($('#c-etf'), function (el) { barChart(el, { h: 260, data: etf.map(function (r) { return [fmt.md(r.d), r.musd, '<div class="t">' + r.d + (r.partial ? (r.src ? _t('（暫定）') : _t('（部分回報）')) : '') + '</div><div class="r"><i style="background:' + (r.musd >= 0 ? 'var(--up)' : 'var(--down)') + _t('"></i><span>淨流量</span><b>') + (r.musd >= 0 ? '+' : '') + fmt.n(r.musd, 1) + 'M</b></div>' + (r.src ? '<div class="t" style="font-weight:400;max-width:240px;white-space:normal">' + esc(r.src) + '</div>' : ''), r.partial]; }), yFmt: function (v) { return v + 'M'; }, aria: _t('ETF 淨流量') }); });
  };

  /* 長短期持有者籌碼（2026-10-27 使用者要求，Murphy〈跌破 $80K 的 BTC，潛在拋壓有多大？〉的拆法）：bitcoin-data 的 URPD 依持有時間拆成
     LTH／STH，推算（pipeline/cohort_urpd.py：URPD × 幣齡分布 × 每日價格區間），不是實體調整，只作讀值。
     三種看法：現在（左 STH、右 LTH）、STH 和約 30 天前比、LTH 和約 30 天前比 */
  var cohMode = 'now';
  function cohLo() { var co = D.chips.cohort; return Math.floor(Math.min(co.window.lo, co.price * 0.7) / co.width) * co.width; }
  function cohRange(lo, hi) { return function (r) { return r[0] + D.chips.cohort.width > lo && r[0] < hi; }; }
  function cohTop(rows, k, n) { return rows.slice().sort(function (a, b) { return b[k] - a[k]; }).slice(0, n || 1); }
  function cohB(r) { return fmt.k(r[0]) + '–' + fmt.k(r[0] + D.chips.cohort.width); }
  function cohCoins(x) { return coins(x, Math.abs(x) < 1e5 ? 1 : 0); }
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
        it.push([_T(fmt.k(mf.lo) + ' 以上的套牢盤', 'Trapped supply above ' + fmt.k(mf.lo)), fmt.pct(ch, 1), _T('這一段全部是長期持有者，而且價格 ' + f.days + ' 天內沒碰過，變化就是賣出、不靠模型：從 ' + cohCoins(mf.before) + ' 到 ' + cohCoins(mf.after) + '。' + (ch < -5 ? '高位套牢的老手還在陸續出清，上方的潛在解套賣壓在變少。' : '高位套牢盤沒什麼動，價格回到那裡時仍可能遇到解套賣壓。') + (tf ? '其中約 ' + cohCoins(tf) + '是疑似內部轉帳搬走的，不一定是賣出。' : ''),
          'All long-term holders, and price has not touched this range in ' + f.days + ' days, so any change is selling, no model involved: ' + cohCoins(mf.before) + ' to ' + cohCoins(mf.after) + '. ' + (ch < -5 ? 'Holders trapped at the highs keep selling out, so there is less overhead supply waiting to break even.' : 'Little has moved, so price may still meet break-even selling up there.') + (tf ? ' About ' + cohCoins(tf) + ' of it left in a likely internal transfer, which is not necessarily selling.' : '')), ch < -5 ? 'pos' : 'neu']); }
    }
    (co.transfers || []).forEach(function (m) {   // 2026-10-27：疑似同一實體內部轉帳（cohort_urpd.transfers），已放回原本的成本與幣齡
      var bk = function (a) { return a.map(function (x) { return fmt.k(x[0]) + '–' + fmt.k(x[0] + w); }).join(_T('、', ', ')); };
      var rr = (co.raw || {}).rows || [], diff = 0; m.dst.forEach(function (x) { var a = rr.filter(function (r) { return r[0] === x[0]; })[0], b = co.rows.filter(function (r) { return r[0] === x[0]; })[0]; if (a && b) diff += a[1] - b[1]; });
      it.push([_T('疑似內部轉帳', 'Likely internal transfer'), cohCoins(m.btc), _T(fmt.md(m.date) + ' 有約 ' + cohCoins(m.btc) + '從 ' + bk(m.src) + ' 一天內搬到 ' + bk(m.dst) + '，平常遠離現價的格子一天只流出幾萬顆以下。逐筆 UTXO 會把它算成賣出再買進；量這麼大又集中，多半是同一實體整併錢包。上面的數字已把這批幣放回原本的成本與幣齡' + (co.raw ? '（不修正的話，短期持有者是 ' + cohCoins(co.raw.sth) + '，' + bk(m.dst) + ' 多出約 ' + cohCoins(diff) + '）' : '') + '。',
        fmt.md(m.date) + ': about ' + cohCoins(m.btc) + ' moved from ' + bk(m.src) + ' to ' + bk(m.dst) + ' in one day; buckets far from the price normally lose only a few tens of thousands of BTC a day at most. Per-UTXO data reads this as selling and rebuying; something this large and concentrated is most likely one entity consolidating wallets. The figures above put these coins back at their original cost and age' + (co.raw ? ' (uncorrected, short-term holders would be ' + cohCoins(co.raw.sth) + ', with about ' + cohCoins(diff) + ' more at ' + bk(m.dst) + ')' : '') + '.'), 'warn']);
    });
    if (co.vs) it.push([_T('推算 vs 實際', 'Estimate vs actual'), fmt.pct(co.vs.sth_diff_pct, 1), _T('推算模型的短期持有者 ' + cohCoins(co.vs.sth_model) + '，CheckOnChain 依實際幣齡算 ' + cohCoins(co.vs.sth_exact) + '；各格合計約 ' + fmt.n(co.vs.misplaced_pct, 0) + '% 分到了別的價位。「STH 變化／LTH 變化」用的是推算（CheckOnChain 只有當下的快照，2026-10-28 起每天存檔，存滿 30 天後改用實際）。',
      'The model puts short-term holders at ' + cohCoins(co.vs.sth_model) + '; CheckOnChain, using actual coin age, has ' + cohCoins(co.vs.sth_exact) + '; about ' + fmt.n(co.vs.misplaced_pct, 0) + '% sits in a different bucket. “STH change / LTH change” still use the estimate (CheckOnChain only has the current snapshot; archived daily from 2026-10-28, the actual data takes over after 30 days).'), Math.abs(co.vs.sth_diff_pct) <= 5 ? 'neu' : 'warn']);
    if (co.val) it.push([_T('驗證', 'Check'), fmt.pct(co.val.diff_pct, 2), _T('推算的短期持有者成本 ' + fmt.usd(co.val.ours) + '，bitcoin-data 公布 ' + fmt.usd(co.val.bd) + '（' + fmt.md(co.val.date) + '）。這個數字沒有拿去校正，差距小代表拆分可信。',
      'Estimated STH cost ' + fmt.usd(co.val.ours) + ' vs ' + fmt.usd(co.val.bd) + ' published by bitcoin-data (' + fmt.md(co.val.date) + '). It is not used in the fit, so a small gap means the split holds up.'), Math.abs(co.val.diff_pct) <= 1 ? 'neu' : 'warn']);
    return it;
  }
  function cohLegend() {
    var f = (D.chips.cohort || {}).flow;
    if (cohMode === 'now') return legend([[_T('短期持有者 STH（< 155 天）', 'Short-term holders (< 155 days)'), 'var(--s2)'], [_T('長期持有者 LTH', 'Long-term holders'), 'var(--s1)'], [_T('收盤', 'Close'), 'var(--ink)']]);
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
    return panel('span-12', _T('長短期持有者籌碼', 'Long- vs short-term holder supply'), (cohExact() ? _T('現在：CheckOnChain 實際幣齡 ' + fmt.md(co.now_date) + ' · 變化：推算', 'Now: CheckOnChain actual coin age ' + fmt.md(co.now_date) + ' · changes: estimate') : _T('推算 · bitcoin-data URPD × 幣齡分布 · ' + fmt.md(co.date), 'Estimate · bitcoin-data URPD × coin age · ' + fmt.md(co.date))),
      interpHtml(cohSay()) + '<div id="coh-lg" style="margin-top:10px">' + cohLegend() + '</div><div class="chart" id="c-cohort"></div>' + tbl +
      '<p class="note">' + (cohExact() ? _T('「現在」來自 CheckOnChain 的公開圖表（Bitcoin Research Kit 依每顆幣的實際幣齡算），併成每 2,000 美元一格。', '“Now” comes from CheckOnChain\'s public chart (Bitcoin Research Kit, using each coin\'s actual age), regrouped into $2,000 buckets. ') : '') + _T('變化的做法：每天新產生的幣放進當天價格區間所在的格子，再讓各幣齡帶與各價格格的總量同時對上 bitcoin-data 的幣齡分布與 URPD；持有不到 155 天算短期持有者。過去 155 天價格走過 ' + fmt.k(co.window.lo) + '–' + fmt.k(co.window.hi) + '，這個區間外只有長期持有者，不靠模型；區間內的拆分是推算。逐筆 UTXO、不是 Glassnode 的實體調整：交易所與託管整理錢包會被當成賣出再買進，換手量偏高；單日大量從遠離現價的格子搬到現價的（疑似同一實體內部轉帳），會放回原本的成本與幣齡。',
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
      if (wlo >= 0) s += tx_(4, top + wlo * rh + 10, _T('155 天內價格走過的區間', 'Range price covered in 155 days'), 'start');
    } else {
      var k = cohMode === 'sth' ? 1 : 2, f = co.flow, cmp = {}; co.cmp.rows.forEach(function (r) { cmp[r[0]] = r; });
      rows = (co.model_rows || co.rows).filter(k === 1 ? cohRange(Math.floor(co.window.lo / w) * w, co.window.hi) : cohRange(cohLo(), 1e9)).slice().reverse();
      var lab = 44, right = 64, top2 = 6, mx2 = Math.max.apply(null, rows.map(function (r) { return Math.max(r[k], (cmp[r[0]] || [])[k] || 0); })) || 1, sx2 = function (v) { return v / mx2 * (W - lab - right); }, yb2 = top2 + rows.length * (rh + 2), Ht2 = yb2 + 6;
      var big = rows.map(function (r) { return Math.abs(r[k] - ((cmp[r[0]] || [])[k] || 0)); }).sort(function (a, b) { return b - a; })[3] || 0;
      if (k === 2 && f.model_free_above) { var j = rows.findIndex(function (r) { return r[0] < f.model_free_above.lo; }); if (j > 0) s += '<rect x="' + lab + '" y="' + top2 + '" width="' + (W - lab) + '" height="' + j * (rh + 2) + '" fill="var(--deck-2)"/>' + tx_(W - 2, top2 + 11, _T('價格沒碰過：變化就是賣出，不靠模型', 'Untouched by price: changes are selling, no model'), 'end'); }
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
     紅＝淨減、灰＝持平、藍＝淨增，±40 萬顆最深。不是 Glassnode 的評分（那個以實體計、排除交易所）。只作讀值 */
  function lcLv(v, clip) { return Math.max(0, Math.min(8, Math.round(v / clip * 4) + 4)); }
  function lcCoins(v) { return (v > 0 ? '+' : v < 0 ? '−' : '') + cohCoins(Math.abs(v)); }
  function lcSay() {
    var x = D.onchain.lth_color, r = x.run, it = [], up = r.price_chg_pct > 5, dn_ = r.price_chg_pct < -5, sell = r.sign < 0;
    var since = _T('從 ' + fmt.md(r.start) + ' 起連續 ' + r.days + ' 天淨' + (sell ? '減' : '增') + '（最多 ' + lcCoins(r.extreme) + '），同期價格 ' + fmt.pct(r.price_chg_pct, 0) + '（' + fmt.usd(r.price0) + ' → ' + fmt.usd(r.price) + '）。',
      'Net ' + (sell ? 'reducing' : 'adding') + ' for ' + r.days + ' straight days since ' + fmt.md(r.start) + ' (peak ' + lcCoins(r.extreme) + '), while price moved ' + fmt.pct(r.price_chg_pct, 0) + ' (' + fmt.usd(r.price0) + ' → ' + fmt.usd(r.price) + '): ');
    var why = sell ? (up ? _T('價格漲、老手減：老手趁反彈出貨，上方一直有人供貨。', 'price up while veterans cut, so long-term holders are selling into the rally and supplying the market above.') :
      dn_ ? _T('價格跌、老手也減：賣壓有一部分來自持有很久的人。', 'price down and veterans cutting too, so part of the selling comes from long-held coins.') :
      _T('價格沒什麼動、老手在減：老手在這個價位出貨，有人接得住。', 'price flat while veterans cut, so they are distributing at this level and buyers are absorbing it.')) :
      (dn_ ? _T('價格跌、老手淨增：持有的人沒賣；增加的部分也包括幣放滿 155 天自動轉成長期。', 'price down yet veterans grow, so holders are not selling; part of the rise is coins simply aging past 155 days.') :
      up ? _T('價格漲、老手淨增：上漲中老手沒有出貨。', 'price up and veterans still growing, so long-term holders are not selling into the rise.') :
      _T('價格沒什麼動、老手淨增：籌碼在沉澱。', 'price flat and veterans growing, so supply is settling into stronger hands.'));
    it.push([_T('長期持有者 30 日淨部位', 'LTH 30-day net position'), lcCoins(x.last), since + why, sell ? 'warn' : 'pos']);
    var p = x.prev_same;
    it.push([_T('四年位置', '4-year rank'), fmt.n(x.pct_4y, 0) + _T(' 百分位', 'th pct'), _T('0＝四年來淨減最多的一天、100＝淨增最多。', '0 = the heaviest net reduction in four years, 100 = the heaviest net addition. ') +
      (p ? _T('這段之前，上一次淨' + (x.last < 0 ? '減' : '增') + '這麼多是 ' + p.date.replace(/-/g, '/') + '（' + lcCoins(p.value) + '，價格 ' + fmt.usd(p.price) + '）。', 'Before this run, the last time it was this ' + (x.last < 0 ? 'negative' : 'positive') + ' was ' + p.date.replace(/-/g, '/') + ' (' + lcCoins(p.value) + ', price ' + fmt.usd(p.price) + '). ') : '') +
      (x.vs_hi1y_pct > -2 ? _T('價格就在一年高點 ' + fmt.usd(x.hi1y) + ' 附近。', 'Price is at the one-year high of ' + fmt.usd(x.hi1y) + '.') : _T('價格比一年高點 ' + fmt.usd(x.hi1y) + ' 低 ' + fmt.n(-x.vs_hi1y_pct, 0) + '%。', 'Price is ' + fmt.n(-x.vs_hi1y_pct, 0) + '% below the one-year high of ' + fmt.usd(x.hi1y) + '.')), 'neu']);
    return it;
  }
  function lthColorPanel() {
    var x = (D.onchain || {}).lth_color; if (!x || !x.rows) return '';
    var k = x.clip / (LANG === 'en' ? 1e3 : 1e4) + _T(' 萬', 'K');
    return panel('span-12', _T('價格 × 長期持有者動向', 'Price × long-term holder flow'), _T('bitcoin-data · 長期持有者 30 日淨部位 · ' + fmt.md(x.date), 'bitcoin-data · LTH 30-day net position · ' + fmt.md(x.date)),
      interpHtml(lcSay()) + '<div class="legend" style="margin-top:10px"><span><b style="color:var(--ink-2);font-weight:400">' + _T('淨減 ≥' + k, 'Net cut ≥' + k) + '</b><i class="lc-bar"></i><b style="color:var(--ink-2);font-weight:400">' + _T('淨增 ≥' + k, 'Net add ≥' + k) + '</b></span><span><b style="color:var(--ink-2);font-weight:400">' + _T('中間灰色＝持平（±5 萬內）', 'grey middle = flat (within ±50K)') + '</b></span></div><div class="chart" id="c-lthc"></div>' +
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

  V.onchain = function () {
    var oc = D.onchain, m = oc.metrics || {}, tr = oc.top_radar || {}, ch = D.chips, fl = ch.flow || {}, u = ch.urpd || {}, mi = oc.mining || {}, ex = oc.exchange || {};
    var rows = [
      ['MVRV Z', 'mvrv-zscore', _t('估值：市值與實現市值的差距')], ['NUPL', 'nupl', _t('淨未實現損益：帳面獲利佔市值比例')], ['Puell', 'puell-multiple', _t('礦工收入 ÷ 一年平均')],
      ['aSOPR', 'asopr', _T('賣出時的獲利倍數（排除一小時內轉手），>1 平均獲利', 'Profit multiple on coins sold (excluding coins moved within an hour); >1 = sold at a profit on average')], ['STH-SOPR', 'sth-sopr', _t('短期持有者的 SOPR')], ['LTH-SOPR', 'lth-sopr', _t('長期持有者的 SOPR')],
      [_t('非流動性供給'), 'illiquid-supply', _t('長期不動的幣')], [_t('高流動性供給'), 'highly-liquid-supply', _t('浮動籌碼')]
    ].map(function (r) { return [r[0], m[r[1]], r[2], r[1]]; }).filter(function (r) { return r[1]; });
    var t = _t('<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:46%"><col style="width:20%"><col style="width:34%"></colgroup><thead><tr><th>指標</th><th class="num">讀值</th><th>四年百分位</th></tr></thead><tbody>') + rows.map(function (r) { var v = r[1], big = Math.abs(v.value) > 1e5, rd = OC_READ[r[3]] ? OC_READ[r[3]](v) : null; return '<tr' + (rd ? ' class="has-rd"' : '') + '><td><b>' + r[0] + '</b><div class="note">' + esc(r[2]) + ' · ' + fmt.md(v.date) + '</div></td><td class="num">' + (big ? fmt.n(v.value / 1e6, 2) + 'M' : fmt.n(v.value, 3)) + '</td><td>' + (v.pct_4y == null ? '—' : '<div class="pct"><i><b class="' + (v.pct_4y >= 80 ? 'hot' : '') + '" style="width:' + v.pct_4y + '%"></b></i><span class="num">' + fmt.n(v.pct_4y, 0) + '</span></div>') + '</td></tr>' + rdRow(rd, 3); }).join('') + '</tbody></table></div>';
    var radar = [['LTH MVRV Z', tr['lth-mvrv-zscore'], 2, 'lth-mvrv-zscore'], [_t('獲利供給 %'), tr['supply-in-profit-pct'], 1, 'supply-in-profit-pct'], [_t('LTH 30 日淨部位'), tr['lth-net-position-change-30d-btc'], 0, 'lth-net-position-change-30d-btc']].filter(function (r) { return r[1]; });
    var rt = _t('<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:34%"><col style="width:22%"><col style="width:22%"><col style="width:22%"></colgroup><thead><tr><th>頂部雷達</th><th class="num">現在</th><th class="num">2025 頂部</th><th>本輪位置</th></tr></thead><tbody>') + radar.map(function (r) { var v = r[1], rd = RADAR_READ[r[3]](v); return '<tr class="has-rd"><td><b>' + r[0] + '</b></td><td class="num">' + fmt.n(v.value, r[2]) + '</td><td class="num">' + fmt.n(v.extreme_near_2025_top, r[2]) + '</td><td><div class="pct"><i><b style="width:' + v.pct_since_2022_11 + '%"></b></i><span class="num">' + fmt.n(v.pct_since_2022_11, 0) + '</span></div></td></tr>' + rdRow(rd, 4); }).join('') + '</tbody></table></div>';
    return readBar('onchain') + '<div class="kpis">' + kpi(_t('短期持有者獲利比例'), fmt.n((fl.sth_in_profit_pct || {}).value, 1) + '%', _t('7 天前 ') + fmt.n((fl.sth_in_profit_pct || {}).d7, 1) + '%', (fl.sth_in_profit_pct || {}).value) + kpi(_t('短期持有者成本'), fmt.usd((fl.sth_vs_tmm || {}).sth_cost), _t('真實市場均價 ') + fmt.usd((fl.sth_vs_tmm || {}).tmm)) + kpi(_t('交易所供給'), fmt.n(ex.exchange_supply_share_pct, 2) + '%', _t('7 日 ') + fmt.pct(ex.exchange_supply_chg7_pct, 2) + _t(' · 90 日 ') + fmt.pct(ex.exchange_supply_chg90_pct, 2)) + kpi(_t('算力 7 日均'), fmt.n(mi.hash7, 0) + ' EH/s', _t('週 ') + fmt.pct(mi.wk_chg_pct, 1) + ' · hashprice $' + fmt.n(mi.hashprice, 1)) + kpi(_t('下次難度調整'), fmt.pct(mi.diff_next_pct, 1), fmt.md(mi.retarget) + _t(' · 進度 ') + fmt.n(mi.diff_progress, 0) + '%', mi.diff_progress) + '</div><div class="grid">' + interpPanel(ocInterp()) +
      panel('span-5', _t('籌碼分布（URPD）'), fmt.md(u.date) + _t(' · 每 2,000 美元一格'), urpdSay(u) + '<div id="c-urpd"></div>') +
      panel('span-7', _t('短期持有者：成本 vs 價格'), _t('bitcoin-data · 近 2 年'), legend([[_t('短期持有者成本'), 'var(--s2)'], [_t('真實市場均價'), 'var(--s3)']]) + '<div class="chart" id="c-cost"></div>' + _t('<div class="panel-h" style="margin-top:6px"><h2>短期持有者獲利比例</h2><span class="src">2025 頂部 ') + fmt.n((ch.viz || {}).top_vals ? ch.viz.top_vals.profit : null, 1) + '%</span></div><div class="chart" id="c-profit"></div>') +
      cohortPanel() + lthColorPanel() + soprPanel() + sthPnlPanel() + nplPanel() + whalePanel() + panel('span-7', _t('鏈上指標'), _T('MVRV Z／NUPL／Puell：CoinMetrics · STH-SOPR：CheckOnChain · 其他：bitcoin-data', 'MVRV Z / NUPL / Puell: CoinMetrics · STH-SOPR: CheckOnChain · others: bitcoin-data'), t) + panel('span-5', _t('頂部雷達'), _t('2022/11 起本輪百分位'), rt) + ocPanel() + '</div>';
  };
  V.onchain.after = function () {
    mount($('#c-whale'), drawWhale); drawSopr(); drawSthPnl(); drawOc(); mount($('#c-npl'), drawNpl); cohortAfter(); mount($('#c-lthc'), drawLthColor);
    var ns = $('#npl-segs'); if (ns) ns.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; var m = b.getAttribute('data-m'); if (m) { if (m === nplMode) return; nplMode = m; nplRng = m === 'cum' ? 1460 : 180; } else nplRng = +b.getAttribute('data-v'); nplSync(); });
    var v = D.chips.viz || {}, u = v.urpd || {}, c = D.price.bar.c, el = $('#c-urpd');
    if (el && u.band) {
      var pv = {}; ((u.prev7 || {}).band || []).forEach(function (b) { pv[b[0]] = b[1]; });
      var rows = u.band.filter(function (b) { return b[0] >= c * 0.62 && b[0] <= c * 1.4; }).slice().reverse().map(function (b) { var cur = c >= b[0] && c < b[0] + (u.width || 2000); return { label: fmt.k(b[0]), v: b[1], color: cur ? 'var(--flare)' : 'var(--s1)', cls: cur ? 'cur' : '', right: _T(fmt.n(b[1] / 1e4, 1) + '萬', fmt.n(b[1] / 1e3, 0) + 'K'), prev: pv[b[0]], tip: '<div class="t">' + fmt.usd(b[0]) + '–' + fmt.usd(b[0] + (u.width || 2000)) + _t('</div><div class="r"><i style="background:var(--s1)"></i><span>籌碼</span><b>') + fmt.n(b[1]) + _t(' 顆</b></div>') + (pv[b[0]] != null ? _t('<div class="r"><i></i><span>7 天前</span><b>') + fmt.n(pv[b[0]]) + '</b></div>' : '') }; });
      el.innerHTML = ladderHtml(rows, { dense: true }); bindLadder(el, rows);
    }
    mount($('#c-cost'), function (el) { var r = v.cost || []; lineChart(el, { h: 220, series: [{ name: _t('短期持有者成本'), data: r.map(function (x) { return [x[0], x[2]]; }), color: 'var(--s2)' }, { name: _t('真實市場均價'), data: r.map(function (x) { return [x[0], x[3]]; }), color: 'var(--s3)' }], refs: [{ y: c, color: 'var(--ink-3)', label: _t('收盤 ') + fmt.k(c), below: true }], tipFmt: fmt.usd, aria: _t('成本線') }); });
    mount($('#c-profit'), function (el) { lineChart(el, { h: 170, series: [{ name: _t('獲利比例'), data: v.profit || [], color: 'var(--s4)', area: true }], y0: 0, y1: 100, yFmt: function (x) { return x + '%'; }, tipFmt: function (x) { return x.toFixed(1) + '%'; }, aria: _t('短期持有者獲利比例') }); });
  };

  /* 掛單簿摘要（2026-10-12 由獨立版面縮成衍生品版的一張卡）：快照在 UTC 00:05、掛單隨時可撤，只留買賣比與最大的牆 */
  function bookCard() {
    var o = D.orderbook; if (!o) return '';
    var w = o.walls || {}, t = o.totals || {}, rd = o.rounds || {};
    var walls = function (arr, col) { return (arr || []).slice(0, 5).map(function (x) { return '<div class="event"><span class="d">' + fmt.k(x[0]) + '–' + fmt.k(x[0] + 1000) + '</span><span style="color:var(--ink-2)">' + esc(venue(x[2])) + '</span><span class="num" style="color:' + col + '">$' + fmt.n(x[1], 1) + 'M</span></div>'; }).join(''); };
    return panel('span-12', _T('掛單簿', 'Order book'), _T('13 個交易所 · ±15% · 快照 ', '13 exchanges · ±15% · snapshot ') + (o.ts || '').replace('T', ' ').slice(5, 16) + ' UTC',
      interpHtml(bkInterp(o)) + '<div class="grid" style="margin-top:8px">' +
      (o.wide ? '<div class="span-8"><div class="panel-h"><h2>' + _T('全景：每 1,000 美元一格', 'Full view: $1,000 buckets') + '</h2><span class="src">' + _T('7 個整本可得的場所 · ±15%', '7 venues with full books · ±15%') + '</span></div>' + legend([[_t('買單'), 'var(--up)'], [_t('賣單'), 'var(--down)']]) + '<div id="c-book"></div></div>' : '') +
      '<div class="' + (o.wide ? 'span-4' : 'span-12') + '"><div class="panel-h"><h2 style="color:var(--down)">' + _T('上方賣牆', 'Ask walls above') + '</h2><span class="src">' + _T('賣單合計 ', 'total asks ') + '$' + fmt.n(t.wide_ask, 0) + 'M</span></div><div class="events">' + walls(w.ask, 'var(--down)') + '</div>' +
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
    return readBar('exit') + '<div class="grid">' + panel('span-12', _t('現在離每條出場規則多遠'), _t('依當日數值自動產生 · 非投資建議'), interpHtml([rd2(_t('價格階梯'), fmt.k(S.next_step), ladderRead()), rd2(_t('MVRV ÷ 前一輪高點'), fmt.n(S.p20_ratio, 3), p20Read()), rd2(_t('頂部三指標'), ['mvrv_z', 'nupl', 'puell'].map(function (k) { return fmt.n((S.p6 || {})[k], 0); }).join(' / '), p6Read()), rd2(_t('200 日均線避險'), fmt.k(S.sma200), hedgeRead()), [_t('時間停損'), '2029/10', _t('2029/10–2030/03 才適用，現在不作用。'), 'neu']])) +
      panel('span-12', _t('出場模擬器'), esc(tx(F, 'unit')), _t('<div class="sim"><div class="sim-ctrl"><label for="sim-px">拖動看看：如果收盤到這個價位，框架會賣出多少？</label><span class="big" id="sim-v">') + fmt.usd(c) + '</span><input type="range" id="sim-px" min="60000" max="240000" step="1000" value="' + Math.round(c / 1000) * 1000 + '"><div class="legend"><span>60K</span><span style="margin-left:auto">240K</span></div><div class="stair" id="sim-stair"></div></div><div class="donut-wrap" id="sim-donut"></div></div>') +
      panel('span-6', _t('鏈上觸發'), _t('MVRV ÷ 前一輪高點'), '<div class="rules">' + F.onchain.map(function (r) { var run = r.id === 'p20a' ? S.p20_run_075 : r.id === 'p20b' ? S.p20_run_080 : null; return '<div class="rule"><span class="t">' + (r.k ? _t('比值 ≥ ') + r.k : _t('新高背離')) + '</span><span class="d">' + esc(tx(r, 'rule')) + '</span><span class="chip">' + (run != null ? run + _t(' / 5 天') : _t('未啟用')) + '</span></div>'; }).join('') + _t('</div><p class="note">現在比值 ') + fmt.n(S.p20_ratio, 3) + _t('；0.75 約對應 ') + fmt.usd(S.k075_price) + _t('、0.80 約 ') + fmt.usd(S.k080_price) + _t('（隨實現價每天移動）。</p>')) +
      panel('span-6', _t('其他規則'), '', _t('<div class="rules"><div class="rule"><span class="t">200 日均線避險</span><span class="d">') + esc(tx(F.hedge, 'rule')) + '</span><span class="chip">' + S.below_sma200_run + _t(' / 5 天</span></div><div class="rule"><span class="t">訊號加速</span><span class="d">') + esc(tx(F, 'accelerate')) + '</span><span class="chip">' + ['mvrv_z', 'nupl', 'puell'].map(function (k) { return fmt.n((S.p6 || {})[k], 0); }).join(_t('／')) + _t('</span></div><div class="rule"><span class="t">時間停損</span><span class="d">') + esc(tx(F, 'time_stop')) + _t('</span><span class="chip">2029/10 起</span></div></div><p class="note">框架是本站對「週期頂部分批出場」的建議做法，只是參考，不是投資建議；每個人的部位與需求不同。</p>')) + '</div>';
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

  V.method = function () {
    return '<div class="grid">' + panel('span-7', _t('這是什麼'), '', _t('<div class="prose"><p>破曉（Daybreak）是每天清晨的第一份比特幣簡報：先告訴你今天發生了什麼、為什麼重要，再用數據說明市場在週期裡的位置，以及離分批出場還有多遠。</p><p>每天兩段更新：台北 08:20（UTC 00:20）資料管線自動抓取 Kraken、Deribit、CoinMetrics、bitcoin-data、mempool.space、FRED、13 個交易所掛單簿與 Tidemark，算出所有指標；之後由 Claude 查證當天新聞、讀數據，寫成頭條、今日要聞解讀與各版的「今日判讀」。數字全部來自管線，判讀只解釋數字，不改數字。</p>') +
      _t('<h3>原則</h3><p>先給結論再給證據。各版「這些數字代表什麼」與表格下方的解讀，是用當日數值套固定門檻自動產生（門檻寫在句子裡），標籤「偏多／偏空／留意／中性」只描述該數字對價格的一般含意，不是預測，也不連動出場規則。寧可標示「本日未取得」，也不推估或沿用舊數字。不同資料商的數字不相減。分數一律附樣本數，樣本少於 30 不下結論。</p><h3>限制</h3><p>週期模型只有 3–4 輪歷史，所有「遞減」推論都假設趨勢延續。冪律擬合線會隨新資料下修。掛單隨時可撤。短線預測不連動出場規則。bitcoin-data 的部分序列本身晚 5–6 天，頁首「資料狀態」列出每個來源的資料日期與落後天數。</p>') +
      _t('<h3>免責聲明</h3><p>本站內容僅供研究與教育參考，不構成投資建議。加密資產波動極大，請依自身情況判斷並自負風險。</p></div>')) +
      panel('span-5', _t('資料來源'), '', '<div class="events">' + [[_t('價格、均線、ATR'), _t('Kraken 日線（UTC）')], [_t('波動率、基差、選擇權'), _t('Deribit 公開 API')], [_T('MVRV、頂部三指標、交易所供給、冪律', 'MVRV, top-3 indicators, exchange supply, power law'), 'CoinMetrics Community'], [_T('SOPR、持有者成本、籌碼', 'SOPR, holder cost basis, supply distribution'), 'bitcoin-data.com'], ['STH-SOPR', 'CheckOnChain'], [_t('算力、難度'), 'mempool.space'], [_t('相關係數、利率'), 'FRED'], [_t('ETF 流量'), _t('The Block（與 Farside 同口徑）')], [_t('掛單簿'), _t('Coinbase、Bitstamp、Gemini、Bitfinex、Kraken、Binance、OKX、Gate、MEXC、Deribit、Hyperliquid')], [_t('綜合訊號'), _t('Tidemark（north7.github.io）')]].concat(D.onchain.whales ? [[_T('鯨魚分層持幣', 'Holdings by balance tier (whales)'), 'BitInfoCharts']] : []).map(function (r) { return '<div class="event" style="grid-template-columns:minmax(0,1fr) minmax(0,1.2fr)"><span>' + r[0] + '</span><span style="color:var(--ink-2)">' + r[1] + '</span></div>'; }).join('') + _t('</div><p class="note">資料日 ') + D.meta.bar_date + _t(' · 管線產出 ') + (D.meta.generated_utc || '').replace('T', ' ').slice(0, 16) + _t(' UTC · 結論 ') + (N ? (N.written_utc || '').replace('T', ' ').slice(0, 16) + ' UTC' : '—') + '</p>') + '</div>';
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
    ROUTES.forEach(function (r) { try { if (V[r[0]].after) V[r[0]].after(); } catch (e) { console.error(e); } });
    try { attachReads(v); } catch (e) { console.error(e); }
    try { markSignals(v); } catch (e) { console.error(e); }
    mounted.forEach(observe); settleMeters(v);
    void v.offsetWidth; v.classList.add('view-enter');
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
    document.querySelectorAll('.nav button').forEach(function (b) { b.setAttribute('aria-current', b.getAttribute('data-r') === id ? 'page' : 'false'); });
    var nv = $('#nav'), nb = nv.querySelector('[aria-current="page"]');   // 行動版頂部導航可橫向捲動：把目前版面捲到中間
    if (nb && nv.scrollWidth > nv.clientWidth) nv.scrollTo({ left: nb.offsetLeft - nv.offsetLeft - (nv.clientWidth - nb.offsetWidth) / 2, behavior: reduced ? 'auto' : 'smooth' });
    $('#crumb-k').textContent = r[2]; $('#crumb-t').textContent = r[1];
    document.title = (id === 'overview' ? _t('破曉 Daybreak') : r[1] + _t('｜破曉 Daybreak'));
    if (location.hash.slice(1) !== id) { try { history.replaceState(null, '', '#' + id); } catch (e) {} }
    if (!seen[id]) { seen[id] = 1; decodeNums($('#pg-' + id)); }
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
    requestAnimationFrame(function () { de.style.overflow = b.style.overflow = ''; window.scrollTo(0, 0); });
    [80, 250, 500].forEach(function (t) { setTimeout(function () { if (MQ.matches && window.scrollY > 0) window.scrollTo(0, 0); }, t); });
  }
  function go(id) {
    if (id === 'book') id = 'deriv';   // 2026-10-12 掛單簿版面併入衍生品版，舊連結導過去
    var sec = $('#pg-' + id); if (!sec) return;
    if (MQ.matches) { activate(id); toTop(); return; }
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
    var ft = document.querySelectorAll('.foot span'); ['© Daybreak', 'For research only — not investment advice', 'Press 1–9 to switch sections', 'Swipe left/right to switch sections'].forEach(function (x, i) { if (ft[i]) ft[i].textContent = x; });
    var fr = $('#follow-rail .k'); if (fr) fr.textContent = 'FOLLOW';
    var ff = $('#follow-foot'); if (ff) ff.innerHTML = 'Daily at 08:30 Taipei · follow <b>@songpu717</b> on X ↗';
    document.title = 'Daybreak';
    var md = document.querySelector('meta[name="description"]'); if (md) md.setAttribute('content', 'Daybreak: the first Bitcoin brief of the morning — news with analysis, market data, cycle position and a staged exit framework.');
  }
  function shell() {
    $('#nav').innerHTML = ROUTES.map(function (r, i) { return '<button type="button" data-r="' + r[0] + '"><span class="i">' + ('0' + (i + 1)).slice(-2) + '</span><span>' + r[1] + '</span></button>'; }).join('');
    $('#nav').addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) go(b.getAttribute('data-r')); });
    document.addEventListener('keydown', function (e) { if ((e.target.closest && e.target.closest('input,textarea')) || e.metaKey || e.ctrlKey || e.altKey) return; var n = e.key === '0' ? 10 : +e.key; if (n >= 1 && n <= ROUTES.length) go(ROUTES[n - 1][0]); });
    // 跨過 860px（旋轉、縮放視窗）時切換顯示方式，停在同一版
    var onMode = function () { if (MQ.matches) window.scrollTo(0, 0); else go(cur); };
    if (MQ.addEventListener) MQ.addEventListener('change', onMode); else if (MQ.addListener) MQ.addListener(onMode);
    window.addEventListener('hashchange', function () { var h = location.hash.slice(1); if (h !== cur) go(h); });
    // 2026-10-23：「看圖 →」連結：換到那一版後捲到那張圖並閃一下
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a.jump'); if (!a) return; var ch = a.getAttribute('data-chart'); if (!ch) return;
      e.preventDefault(); go(a.getAttribute('href').slice(1));
      setTimeout(function () { var el = $('#c-' + ch); if (!el) return; el.scrollIntoView({ block: 'center', behavior: reduced ? 'auto' : 'smooth' }); el.classList.add('flash'); setTimeout(function () { el.classList.remove('flash'); }, 1800); }, MQ.matches ? 350 : 500);
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
    window.addEventListener('scroll', function () { if (ticking) return; ticking = true; requestAnimationFrame(function () { ticking = false; spy(); }); }, { passive: true });
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
      if (i >= 0 && i < ROUTES.length) go(ROUTES[i][0]);
    }, { passive: true });
    // 日刊／夜刊：桌面在側欄、行動版在頂部列右上；語言：選了就記住（daybreak.lang），重新載入套用
    var tt = $('#theme'), mt = $('#m-theme'), SUN = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>', MOON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>';
    function setTheme(v) {
      if (v === 'dark') document.documentElement.setAttribute('data-theme', 'dark'); else document.documentElement.removeAttribute('data-theme');
      tt.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x.getAttribute('data-t') === v); });
      if (mt) { mt.innerHTML = v === 'dark' ? MOON : SUN; mt.setAttribute('data-v', v); }
    }
    function pickTheme(v) { setTheme(v); try { localStorage.setItem('daybreak.theme', v); } catch (er) {} mounted.forEach(function (el) { el._draw && el._draw(el); }); }
    tt.addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) pickTheme(b.getAttribute('data-t')); });
    if (mt) mt.addEventListener('click', function () { pickTheme(mt.getAttribute('data-v') === 'dark' ? 'light' : 'dark'); });
    try { setTheme(localStorage.getItem('daybreak.theme') === 'dark' ? 'dark' : 'light'); } catch (e) { setTheme('light'); }
    function pickLang(l) { if (l === LANG) return; try { localStorage.setItem('daybreak.lang', l); } catch (er) {} location.reload(); }
    $('#lang').querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x.getAttribute('data-l') === LANG); });
    $('#lang').addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) pickLang(b.getAttribute('data-l')); });
    var ml = $('#m-lang'); if (ml) { ml.textContent = LANG === 'en' ? '中文' : 'EN'; ml.addEventListener('click', function () { pickLang(LANG === 'en' ? 'zh' : 'en'); }); }
    staticText();
    var pad = function (x) { return ('0' + x).slice(-2); };
    function tick() { var t = new Date(); var nx = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate(), 0, 30)); if (nx <= t) nx = new Date(+nx + 864e5); var d = Math.floor((nx - t) / 1000); $('#nxt').textContent = 'T−' + pad(Math.floor(d / 3600)) + ':' + pad(Math.floor(d % 3600 / 60)) + ':' + pad(d % 60); }
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
  // 英文版讀 data/notes.en.json（每日任務與中文同時寫）；沒有或日期比中文舊時，退回中文並標示
  Promise.all([load('data/latest.json'), load('data/notes.json').catch(function () { return null; }), LANG === 'en' ? load('data/notes.en.json').catch(function () { return null; }) : null]).then(function (a) {
    var nz = a[1], ne = a[2], nn = LANG === 'en' && ne && (!nz || ne.date >= nz.date) ? ne : nz;
    ZH_ONLY = LANG === 'en' && !!nn && nn === nz;
    D = a[0]; N = nn && nn.date === D.meta.bar_date ? nn : (nn ? Object.assign({}, nn, { stale: true }) : null);
    shell();
    renderAll();
    var start = location.hash.slice(1);
    if (start && start !== 'overview' && $('#pg-' + start)) {
      go(start);   // 字型載入後版面會變高，載完再對齊一次（使用者已自行捲動就不動）
      var y0 = window.scrollY; if (document.fonts) document.fonts.ready.then(function () { if (Math.abs(window.scrollY - y0) < 2) go(start); });
    } else { window.scrollTo(0, 0); activate(ROUTES[0][0]); }
  }).catch(function (e) { $('#view').innerHTML = _t('<p class="err">資料載入失敗：') + esc(e.message) + _t('。請稍後重新整理。</p>'); });
});
