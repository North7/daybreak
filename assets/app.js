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
    el.querySelectorAll('path.ln').forEach(function (p) { try { var L = p.getTotalLength(); p.style.setProperty('--len', L); p.classList.add('draw'); } catch (e) {} });
  }

  /* 折線／面積圖：x 為日期序號（天）或數值；可對數 y；參考線、區段、標記；十字線 tooltip */
  function lineChart(el, cfg) {
    var W = Math.max(280, el.clientWidth), Ht = cfg.h || (W < 520 ? 210 : 260);
    var ML = cfg.ml || 8, MR = cfg.mr || 58, MT = 14, MB = 24, pw = W - ML - MR, ph = Ht - MT - MB;
    var all = []; cfg.series.forEach(function (s) { s.data.forEach(function (p) { if (p[1] != null) all.push(p); }); });
    if (all.length < 2) { el.innerHTML = _t('<p class="note">本日未取得資料。</p>'); return; }
    var x0 = cfg.x0 != null ? cfg.x0 : Math.min.apply(null, all.map(function (p) { return p[0]; }));
    var x1 = cfg.x1 != null ? cfg.x1 : Math.max.apply(null, all.map(function (p) { return p[0]; }));
    var ys = all.map(function (p) { return p[1]; }); (cfg.refs || []).forEach(function (r) { if (r.inRange !== false) ys.push(r.y); });
    var lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys);
    if (cfg.y0 != null) lo = Math.min(lo, cfg.y0); if (cfg.y1 != null) hi = Math.max(hi, cfg.y1);
    var lg = !!cfg.log, T = function (v) { return lg ? Math.log10(v) : v; };
    var tl = T(lo), th = T(hi), pad = (th - tl) * 0.08 || 1; tl -= pad; th += pad;
    var X = function (x) { return ML + (x - x0) / (x1 - x0 || 1) * pw; };
    var Y = function (v) { return MT + (1 - (T(v) - tl) / (th - tl)) * ph; };
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
    (cfg.vlines || []).forEach(function (v) { var xx = X(v.x); if (xx < ML || xx > ML + pw) return; s += '<line x1="' + xx.toFixed(1) + '" x2="' + xx.toFixed(1) + '" y1="' + MT + '" y2="' + (MT + ph) + '" stroke="var(--ink-3)" stroke-dasharray="2 4" stroke-width="1"/>' + (v.label ? '<text class="ax" x="' + (xx + 5).toFixed(1) + '" y="' + (MT + ph - 6) + '">' + esc(v.label) + '</text>' : ''); });
    (cfg.hbands || []).forEach(function (b) { var a = Math.max(MT, Y(b.y1)), z = Math.min(MT + ph, Y(b.y0)); if (z <= a) return; s += '<rect x="' + ML + '" y="' + a.toFixed(1) + '" width="' + pw + '" height="' + Math.max(1, z - a).toFixed(1) + '" fill="' + b.color + '"/>'; });
    // refs
    (cfg.refs || []).forEach(function (r) { var y = Y(r.y); if (y < MT - 2 || y > MT + ph + 2) return; s += '<line class="ref" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '" stroke="' + r.color + '"/>'; if (r.label) s += '<text class="reflab" x="' + (ML + 6) + '" y="' + (y + (r.below ? 13 : -5)).toFixed(1) + '" fill="' + r.color + '">' + esc(r.label) + '</text>'; });
    // series
    var defs = '';
    cfg.series.forEach(function (sr, si) {
      var pts = sr.data.filter(function (p) { return p[1] != null; }); if (pts.length < 2) return;
      var dpath = pts.map(function (p, i) { return (i ? 'L' : 'M') + X(p[0]).toFixed(1) + ',' + Y(p[1]).toFixed(1); }).join('');
      if (sr.area) { var gid = 'g' + Math.random().toString(36).slice(2, 8); defs += '<linearGradient id="' + gid + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + sr.color + '" stop-opacity=".28"/><stop offset="1" stop-color="' + sr.color + '" stop-opacity="0"/></linearGradient>'; s += '<path d="' + dpath + 'L' + X(pts[pts.length - 1][0]).toFixed(1) + ',' + (MT + ph) + 'L' + X(pts[0][0]).toFixed(1) + ',' + (MT + ph) + 'Z" fill="url(#' + gid + ')"/>'; }
      s += '<path class="ln" d="' + dpath + '" stroke="' + sr.color + '" stroke-width="' + (sr.w || 2) + '"' + (sr.dash ? ' stroke-dasharray="' + sr.dash + '"' : '') + ' style="animation-delay:' + (si * 0.12) + 's"/>';
      if (sr.end !== false) { var lp = pts[pts.length - 1]; s += '<circle cx="' + X(lp[0]).toFixed(1) + '" cy="' + Y(lp[1]).toFixed(1) + '" r="4" fill="' + sr.color + '" stroke="var(--deck)" stroke-width="2"/>'; }
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
        g += '<circle cx="' + X(p[0]).toFixed(1) + '" cy="' + Y(p[1]).toFixed(1) + '" r="4" fill="' + sr.color + '" stroke="var(--deck)" stroke-width="2"/>';
        rows.push('<div class="r"><i style="background:' + sr.color + '"></i><span>' + esc(sr.name) + '</span><b>' + (cfg.tipFmt || yf)(p[1]) + '</b></div>');
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
    var it = [[_t('BTC 收盤'), fmt.usd(p.bar.c), fmt.pct(p.bar.chg_pct, 2), p.bar.chg_pct >= 0], [_t('200 日均線'), fmt.usd(p.ma.sma200), fmt.pct((p.bar.c / p.ma.sma200 - 1) * 100), true], ['DVOL', fmt.n((dv.dvol || {}).value, 1), _t('一年第 ') + fmt.n((dv.dvol || {}).pct_1y, 0) + _t(' 百分位')], [_t('資金費率'), fmt.pct((dv.deriv || {}).funding_ann, 1), _t('年化')], ['ETF ' + fmt.md(le.d), (le.musd >= 0 ? '+' : '') + fmt.n(le.musd, 1) + 'M', '', le.musd >= 0], [_t('10 年期殖利率'), fmt.n((fr.DGS10 || {}).last, 2) + '%', fmt.md((fr.DGS10 || {}).last_date)], [_t('BTC–那斯達克'), fmt.n((fr.NASDAQCOM || {}).corr30, 2), _t('30 日相關')], [_t('MVRV ÷ 前高'), fmt.n(cm.mvrv_vs_prior, 3), _t('賣出線 0.75')], [_t('冪律倍數'), fmt.n(pl.ratio, 2) + '×', _t('合理價 ') + fmt.k(pl.fair)], ['Tidemark', fmt.n((tm.top || {}).signal, 0) + ' / ' + fmt.n((tm.bottom || {}).signal, 0), _t('頂 / 底')], [_t('算力'), fmt.n(mi.hash7, 0) + ' EH/s', fmt.pct(mi.wk_chg_pct, 1), mi.wk_chg_pct >= 0], [_t('下次難度'), fmt.pct(mi.diff_next_pct, 1), fmt.md(mi.retarget)]];
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
      }).join('') + '</tbody></table></div>' : '') +
      '<div class="rules">' + lines.map(function (l) { return '<div class="rule"><span class="t"><span class="mk-s">' + l[0] + '</span>' + l[1] + '</span><span class="d">' + l[2] + '</span><span></span></div>'; }).join('') + '</div>' +
      _t('<p class="note">判定規則：轉換期＝燈號一（投降）✓ 且收盤在上升的 200 日均線之上（上升＝高於 30 天前）；牛市＝燈號一 ✓ 且收盤連 30 日在上升的 200 日均線之上，成立後單向鎖定；退回熊市＝轉換期中連 5 日收在 200 日均線下，牛市則需連 30 日在下降的 200 日均線下。佐證燈號只顯示證據強弱，不參與判定。</p>') +
      _t('<p class="note">限制：2014 年起只有 3–4 輪週期可回測。這條價格規則在候選標準中假訊號最少，但 2019 年中一樣誤判為牛市，之後跌了近五成；沒有任何規則能同時又快又少假訊號。交易所供給 90 日轉負原為必要條件，回測顯示換視窗長度就失效、地址歸屬會事後修正（有前視偏差），且 2025 年 99% 的日子成立，2026-10-09 起降為佐證。牛市條件在頂部附近也會亮，不是賣出訊號；市場階段只是標籤，不連動出場框架。</p>');
  }
  // 以下三塊由每日結論任務寫進 notes.json；不是當天的就標「上一期」
  /* 資料管線寫進 latest.json 的中文標籤，英文版在這裡對照 */
  var EV_EN = { mom12: ['12-month momentum', 'Close above its level a year ago'], mvrv1y: ['MVRV vs 1-year mean', 'MVRV above its own 1-year average'],
    rcgrowth: ['Capital inflow', 'Realized cap 30-day growth is positive'], xs90: ['Exchange supply', '90-day change is negative'], sth: ['Short-term holder cost', 'Close above short-term holder cost (bitcoin-data)'] };
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
  function researchHtml() {
    var r = N && N.research || {}, rows = r.items || [];
    if (!rows.length) return '<p class="note">' + esc(r.summary || _t('本期沒有新的機構研報。')) + '</p>';
    return (r.summary ? '<p class="say">' + esc(r.summary) + '</p>' : '') + _t('<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:20%"><col style="width:44%"><col style="width:36%"></colgroup><thead><tr><th>來源</th><th>重點</th><th>對本站判斷的意義</th></tr></thead><tbody>') +
      rows.map(function (x) { var src = x.url ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(x.source) + '</a>' : esc(x.source); return '<tr><td><b>' + src + '</b><br><span class="note">' + esc(x.title || '') + (x.date ? _t('，') + fmt.md(x.date) : '') + (x.access === 'title_only' ? _t('・只取得標題') : '') + '</span></td><td>' + esc(x.points) + '</td><td>' + esc(x.meaning) + '</td></tr>'; }).join('') +
      _t('</tbody></table></div><p class="note">研報只作文字對照，不改變任何規則；只取得標題的不作判斷依據。</p>');
  }
  function newsItem(n, lead, ix) {
    return '<article class="' + (lead ? 'news-lead' : 'news-item') + '">' + (ix ? '<span class="idx">' + ('0' + ix).slice(-2) + '</span>' : '') + '<div class="news-meta"><span class="cat">' + esc(n.cat) + '</span>' + impChip(n.impact) + '<span>' + esc(n.time.slice(5).replace('-', '/')) + '</span></div><h3>' + esc(n.title) + _t('</h3><div class="read-box"><b class="lbl">解讀</b>') + esc(n.read) + _t('</div><div class="src-link">來源：<a href="') + esc(n.url) + '" target="_blank" rel="noopener">' + esc(n.source) + '</a>' + (n.module ? ' · <a href="#' + n.module + _t('">看相關數據 →</a>') : '') + '</div></article>';
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
    'sopr': function (v) { return [soprLine(v.value, _t('賣出的幣')), 'neu']; },
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
    'realized-cap-growth-rate': function (v) { var p = v.pct_since_2022_11;
      return [pctWord(p, '本輪') + (v.value <= 0 ? _t('；小於等於 0，實現市值沒有成長，代表沒有新資金淨流入。') : p >= 90 ? _t('；資金流入接近本輪最快，2025 頂部時是 ') + fmt.n(v.extreme_near_2025_top, 1) + _t('。') : _t('；有資金流入但不快。')) + _t('（bitcoin-data 口徑，與資金版 CoinMetrics 的 30 日變化在日期與算法上不同，數字會有差異）'), v.value <= 0 ? 'neg' : p >= 90 ? 'warn' : 'pos']; },
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

  /* 衍生品版 */
  function dvInterp() {
    var dv = D.deriv, d = dv.deriv || {}, r = dv.rr25 || {}, o = dv.options || {}, c = D.price.bar.c, it = [], dvol = dv.dvol || {}, x = (dv.samesource || {}).iv_minus_rv30;
    var big = (o.expiries || []).slice().sort(function (a, b) { return b.oi - a.oi; })[0];
    if (dvol.value != null) it.push(['DVOL', fmt.n(dvol.value, 1), _t('一年第 ') + fmt.n(dvol.pct_1y, 0) + _t(' 百分位：') + band(dvol.pct_1y, [20, 50, 80], [_t('在一年低檔，選擇權市場預期平靜，買保護很便宜；長時間低波動之後常接大波動，但不指方向。'), _t('偏低，市場預期平靜。'), _t('偏高，市場預期波動放大。'), _t('在一年高檔，市場緊張或有大事件，買保護很貴。')]), dvol.pct_1y >= 80 ? 'warn' : 'neu']);
    if (x != null) it.push(['IV − RV30', fmt.n(x, 2), Math.abs(x) < 3 ? _t('隱含波動和實際波動相差不到 3 點：選擇權定價大致公允，沒有恐慌溢價。') : x < 0 ? _t('隱含波動比實際低 ') + fmt.n(-x, 1) + _t(' 點：選擇權相對便宜，市場可能低估了波動。') : _t('隱含波動比實際高 ') + fmt.n(x, 1) + _t(' 點：市場在為未來波動付溢價（避險需求或事件前）。'), 'neu']);
    if (d.funding_ann != null) it.push([_t('永續資金費率'), fmt.pct(d.funding_ann, 1), _t('年化 ') + band(d.funding_ann, [0, 10, 20, 40], [_t('低於 0：空頭付費給多頭，空單擁擠，容易出現軋空'), _t('0–10%：中性，多頭槓桿不擁擠'), _t('10–20%：偏熱，多頭願意付較高成本'), _t('20–40%：槓桿過熱，回檔時容易連環爆倉'), _t('40% 以上：極端過熱')]) + _t('；期貨基差中位 ') + fmt.n(d.basis_median, 1) + _t('%。'), d.funding_ann < 0 ? 'pos' : d.funding_ann < 10 ? 'neu' : d.funding_ann < 20 ? 'warn' : 'neg']);
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
    if (a) it.push([_t('最大賣牆'), fmt.k(a[0]), venue(a[2]) + _t(' 掛了 $') + fmt.n(a[1], 1) + _t('M，在中間價上方 ') + fmt.n((a[0] / c - 1) * 100, 1) + _t('%：價格接近時可能先被擋住；但掛單隨時可撤，假牆很常見。'), 'neu']);
    if (b) it.push([_t('最大買牆'), fmt.k(b[0]), venue(b[2]) + _t(' 掛了 $') + fmt.n(b[1], 1) + _t('M，在中間價下方 ') + fmt.n((1 - b[0] / c) * 100, 1) + _t('%：可能是下檔第一道承接，同樣可以隨時撤。'), 'neu']);
    return it;
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
    ['book', _t('掛單簿'), _t('13 個交易所'), 'M5 4v16M5 7h9M5 11h13M5 15h7M5 19h11', 'ORDER BOOK'],
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
    return zhNote + front + tapeHtml() + newsBlock + plan +
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
    var cats = ['全部'].concat(news.map(function (n) { return n.cat; }).filter(function (c, i, a) { return a.indexOf(c) === i; }));
    var cnt = function (k) { return news.filter(function (n) { return n.impact === k; }).length; };
    return _t('<div class="news-sum"><div><span class="note">偏多</span><b style="color:var(--up)">') + ('0' + cnt('bull')).slice(-2) + _t('</b></div><div><span class="note">偏空</span><b style="color:var(--down)">') + ('0' + cnt('bear')).slice(-2) + _t('</b></div><div><span class="note">中性</span><b>') + ('0' + cnt('neutral')).slice(-2) + '</b></div></div>' +
      _t('<div class="filters" id="nf" role="group" aria-label="分類">') + cats.map(function (c, i) { return '<button type="button" aria-pressed="' + (i === 0) + '" data-c="' + esc(c) + '">' + esc(c) + '</button>'; }).join('') + '</div>' +
      _t('<div class="news-grid" id="ng"></div><p class="note">每則消息都查證過發布日期；「解讀」說明它對比特幣的意義，並對照本站的數據。消息只作參考，不改變任何出場規則。</p>') + rs;
  };
  V.news.after = function () {
    var news = (N && N.news || []).slice().sort(function (a, b) { return (b.weight || 0) - (a.weight || 0) || (b.time > a.time ? 1 : -1); });
    function draw(cat) { $('#ng').innerHTML = news.filter(function (n) { return cat === '全部' || n.cat === cat; }).map(function (n, i) { return '<article class="news-card"><div class="news-meta"><span class="cat">' + esc(n.cat) + '</span>' + impChip(n.impact) + '<span>' + esc(n.time.slice(5).replace('-', '/')) + '</span></div><h3>' + esc(n.title) + _t('</h3><div class="read-box"><b class="lbl">解讀</b>') + esc(n.read) + _t('</div><div class="src-link">來源：<a href="') + esc(n.url) + '" target="_blank" rel="noopener">' + esc(n.source) + '</a></div>' + (n.module ? '<a class="go" href="#' + n.module + _t('">看相關數據 →</a>') : '') + '</article>'; }).join(''); }
    draw(_t('全部'));
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
    var M = D.cycle.model, cols = { '直接修復': 'var(--s4)', '淺回檔': 'var(--s1)', '基準雙底': 'var(--s2)', '延後新低': 'var(--s3)' };
    var md = function (y, m) { return Math.round(Date.UTC(y, m - 1, 15) / 864e5); };
    var series = Object.keys(M.nodes).map(function (k) { return { name: _t(k), data: M.nodes[k].map(function (p) { return [md(p[0], p[1]), p[2]]; }), color: cols[k], dash: '5 5', w: 1.8, end: false }; });
    var real = M.realized.map(function (p) { return [md(p[0], p[1]), p[2]]; }); real.push([dnOf(D.meta.bar_date), D.price.bar.c]);
    series.push({ name: _t('已實現'), data: real, color: 'var(--ink)', w: 2.6 });
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
    return readBar('market') + '<div class="kpis">' + kpi(_t('收盤'), fmt.usd(c), fmt.pct(p.bar.chg_pct, 2) + _t(' · 當日區間位置 ') + fmt.n(p.bar.close_pos_pct, 0) + '%') + kpi(_t('ATR14（簡單平均）'), fmt.usd(p.atr.atr14), _t('約 ') + fmt.n(p.atr.atr14 / c * 100, 1) + _t('% / 日')) + kpi(_t('實際波動 RV30'), fmt.n(p.vol.rv30, 1) + '%', 'RV7 ' + fmt.n(p.vol.rv7, 1) + '% · RV90 ' + fmt.n(p.vol.rv90, 1) + '%') + kpi(_t('Mayer 倍數'), fmt.n(p.mayer.mayer, 2), _t('價格 ÷ 200 日均線')) + kpi('Pi Cycle', fmt.n(p.pi_cycle, 2), _t('111 日 ÷ 2×350 日；≥1 為歷史頂部訊號'), p.pi_cycle * 100) + '</div><div class="grid">' + interpPanel(mkInterp()) +
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
    return readBar('deriv') + '<div class="kpis">' + kpi('DVOL', fmt.n((dv.dvol || {}).value, 1), _t('一年第 ') + fmt.n((dv.dvol || {}).pct_1y, 0) + _t(' 百分位'), (dv.dvol || {}).pct_1y) + kpi(_t('IV − RV30（同源）'), fmt.n((dv.samesource || {}).iv_minus_rv30, 2), _t('負值＝隱含波動比實際便宜')) + kpi(_t('永續資金費率'), fmt.pct(d.funding_ann, 1), _t('年化 · 期貨基差中位 ') + fmt.n(d.basis_median, 1) + '%') + kpi(_t('25Δ 風險逆轉'), fmt.n(r.rr, 2), r.expiry ? r.expiry + ' · ATM ' + fmt.n(r.atm_iv, 1) + '%' : _t('本日沒有可計算的合約')) + kpi(_t('選擇權未平倉'), fmt.n(o.total_oi) + _t(' 顆'), _t('最大到期 ') + (big.expiry || '—') + _t('（') + fmt.n(big.share, 0) + _t('%）')) + '</div><div class="grid">' + interpPanel(dvInterp()) +
      panel('span-8', _t('隱含波動 vs 實際波動'), _t('Deribit DVOL · Kraken RV30 · 近一年'), legend([['DVOL', 'var(--s1)'], ['RV30', 'var(--s2)']]) + '<div class="chart" id="c-vol"></div>') +
      panel('span-4', _t('期貨基差曲線'), _t('年化 % · 排除 7 天內到期'), basisSay(d.basis_curve) + _t('<div class="chart" id="c-basis"></div><p class="note">資金費率年化 ') + fmt.pct(d.funding_ann, 1) + _t('；永續 OI ') + fmt.usd(d.perp_oi_usd_m) + _t('M。</p><div class="src-link">外部：<a href="https://www.coinglass.com/pro/futures/LiquidationHeatMap" target="_blank" rel="noopener">CoinGlass 爆倉熱力圖 ↗</a>（以 OI 與假設槓桿推估，非實際倉位）</div>')) +
      panel('span-6', _t('各到期未平倉'), _t('買權 / 賣權（顆）'), legend([[_t('買權'), 'var(--s4)'], [_t('賣權'), 'var(--s3)']]) + '<div class="chart" id="c-oi"></div>') +
      panel('span-6', _t('最大到期的履約價分布'), ((dv.viz || {}).options || {}).strikes ? dv.viz.options.strikes.expiry + ' · Max Pain ' + fmt.k(dv.viz.options.strikes.maxpain) : '', strikeSay((o.expiries || []).filter(function (e) { return e.expiry === (((dv.viz || {}).options || {}).strikes || {}).expiry; })[0] || big) + '<div id="c-strike"></div>') + '</div>';
  };
  V.deriv.after = function () {
    var v = D.deriv.viz || {};
    mount($('#c-vol'), function (el) { var rows = (v.vol || {}).rows || []; lineChart(el, { series: [{ name: 'DVOL', data: rows.map(function (r) { return [r[0], r[1]]; }), color: 'var(--s1)' }, { name: 'RV30', data: rows.map(function (r) { return [r[0], r[2]]; }), color: 'var(--s2)' }], yFmt: function (x) { return x.toFixed(0); }, tipFmt: function (x) { return x.toFixed(1) + '%'; }, aria: _t('波動率') }); });
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
    return readBar('flows') + '<div class="kpis">' + kpi(_t('最近完整日 ETF'), (last.musd >= 0 ? '+' : '') + fmt.n(last.musd, 1) + 'M', fmt.md(last.d) + _t(' · 美元')) + kpi(_t('近 7 個完整日'), (s7 >= 0 ? '+' : '') + fmt.n(s7, 0) + 'M', _t('前 7 日 ') + (p7 >= 0 ? '+' : '') + fmt.n(p7, 0) + 'M') + kpi(_t('BTC–那斯達克 30 日相關'), fmt.n(nq.corr30, 2), fmt.md(nq.last_date) + _t(' · 高於 0.5 代表同漲同跌'), (nq.corr30 + 1) * 50) + kpi(_t('BTC–美元 30 日相關'), fmt.n(dx.corr30, 2), _t('FRED 廣義美元指數'), (dx.corr30 + 1) * 50) + kpi(_t('10 年期實質利率'), fmt.n(rr.value, 2) + '%', _t('20 日 ') + (rr.chg_20obs_bp >= 0 ? '+' : '') + rr.chg_20obs_bp + _t('bp · 名目 ') + fmt.n(tn.last, 2) + '%') + (rc.chg30_pct != null ? kpi(_t('實現市值 30 日'), fmt.pct(rc.chg30_pct, 2), (rc.zero_now ? _t('≤0 已 ') : _t('>0 已 ')) + rc.state_run_days + _t(' 天 · 90 日 ') + fmt.pct(rc.chg90_pct, 2)) : '') + '</div><div class="grid">' + interpPanel(flInterp(last, s7, p7)) +
      panel('span-12', _t('現貨 ETF 每日淨流量'), _t('The Block（與 Farside 同口徑）· 百萬美元 · 淡色＝暫定或尚未完整'), '<div class="chart" id="c-etf"></div>') + rcPanel(rc) + '</div>';
  };
  V.flows.after = function () {
    var etf = D.flows.etf || [];
    var rc = D.flows.rc_liq || {};
    mount($('#c-rcliq'), function (el) { var r = rc.rows || [], x0 = r.length ? r[0][0] : 0; lineChart(el, { h: 220, series: [{ name: _t('30 日變化'), data: r, color: 'var(--s1)' }], vbands: (rc.episodes || []).filter(function (e) { return dnOf(e.end) >= x0; }).map(function (e) { return { x0: Math.max(x0, dnOf(e.start)), x1: dnOf(e.end) + 1, color: 'var(--down-dim)' }; }), refs: [{ y: 0, color: 'var(--ink-3)', label: _t('0＝流入停滯'), below: true }], yFmt: function (x) { return x + '%'; }, tipFmt: function (x) { return fmt.pct(x, 2); }, aria: _t('實現市值 30 日變化') }); });
    mount($('#c-etf'), function (el) { barChart(el, { h: 260, data: etf.map(function (r) { return [fmt.md(r.d), r.musd, '<div class="t">' + r.d + (r.partial ? (r.src ? _t('（暫定）') : _t('（部分回報）')) : '') + '</div><div class="r"><i style="background:' + (r.musd >= 0 ? 'var(--up)' : 'var(--down)') + _t('"></i><span>淨流量</span><b>') + (r.musd >= 0 ? '+' : '') + fmt.n(r.musd, 1) + 'M</b></div>' + (r.src ? '<div class="t" style="font-weight:400;max-width:240px;white-space:normal">' + esc(r.src) + '</div>' : ''), r.partial]; }), yFmt: function (v) { return v + 'M'; }, aria: _t('ETF 淨流量') }); });
  };

  V.onchain = function () {
    var oc = D.onchain, m = oc.metrics || {}, tr = oc.top_radar || {}, ch = D.chips, fl = ch.flow || {}, u = ch.urpd || {}, mi = oc.mining || {}, ex = oc.exchange || {};
    var rows = [
      ['MVRV Z', 'mvrv-zscore', _t('估值：市值與實現市值的差距')], ['NUPL', 'nupl', _t('淨未實現損益：帳面獲利佔市值比例')], ['Puell', 'puell-multiple', _t('礦工收入 ÷ 一年平均')],
      ['SOPR', 'sopr', _t('賣出時的獲利倍數，>1 平均獲利')], ['aSOPR', 'asopr', _t('SOPR 排除一小時內轉手')], ['STH-SOPR', 'sth-sopr', _t('短期持有者的 SOPR')], ['LTH-SOPR', 'lth-sopr', _t('長期持有者的 SOPR')],
      [_t('非流動性供給'), 'illiquid-supply', _t('長期不動的幣')], [_t('高流動性供給'), 'highly-liquid-supply', _t('浮動籌碼')]
    ].map(function (r) { return [r[0], m[r[1]], r[2], r[1]]; }).filter(function (r) { return r[1]; });
    var t = _t('<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:46%"><col style="width:20%"><col style="width:34%"></colgroup><thead><tr><th>指標</th><th class="num">讀值</th><th>四年百分位</th></tr></thead><tbody>') + rows.map(function (r) { var v = r[1], big = Math.abs(v.value) > 1e5, rd = OC_READ[r[3]] ? OC_READ[r[3]](v) : null; return '<tr' + (rd ? ' class="has-rd"' : '') + '><td><b>' + r[0] + '</b><div class="note">' + esc(r[2]) + ' · ' + fmt.md(v.date) + '</div></td><td class="num">' + (big ? fmt.n(v.value / 1e6, 2) + 'M' : fmt.n(v.value, 3)) + '</td><td>' + (v.pct_4y == null ? '—' : '<div class="pct"><i><b class="' + (v.pct_4y >= 80 ? 'hot' : '') + '" style="width:' + v.pct_4y + '%"></b></i><span class="num">' + fmt.n(v.pct_4y, 0) + '</span></div>') + '</td></tr>' + rdRow(rd, 3); }).join('') + '</tbody></table></div>';
    var radar = [['LTH MVRV Z', tr['lth-mvrv-zscore'], 2, 'lth-mvrv-zscore'], [_t('獲利供給 %'), tr['supply-in-profit-pct'], 1, 'supply-in-profit-pct'], [_t('實現市值成長率'), tr['realized-cap-growth-rate'], 2, 'realized-cap-growth-rate'], [_t('LTH 30 日淨部位'), tr['lth-net-position-change-30d-btc'], 0, 'lth-net-position-change-30d-btc']].filter(function (r) { return r[1]; });
    var rt = _t('<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:34%"><col style="width:22%"><col style="width:22%"><col style="width:22%"></colgroup><thead><tr><th>頂部雷達</th><th class="num">現在</th><th class="num">2025 頂部</th><th>本輪位置</th></tr></thead><tbody>') + radar.map(function (r) { var v = r[1], rd = RADAR_READ[r[3]](v); return '<tr class="has-rd"><td><b>' + r[0] + '</b></td><td class="num">' + fmt.n(v.value, r[2]) + '</td><td class="num">' + fmt.n(v.extreme_near_2025_top, r[2]) + '</td><td><div class="pct"><i><b style="width:' + v.pct_since_2022_11 + '%"></b></i><span class="num">' + fmt.n(v.pct_since_2022_11, 0) + '</span></div></td></tr>' + rdRow(rd, 4); }).join('') + '</tbody></table></div>';
    return readBar('onchain') + '<div class="kpis">' + kpi(_t('短期持有者獲利比例'), fmt.n((fl.sth_in_profit_pct || {}).value, 1) + '%', _t('7 天前 ') + fmt.n((fl.sth_in_profit_pct || {}).d7, 1) + '%', (fl.sth_in_profit_pct || {}).value) + kpi(_t('短期持有者成本'), fmt.usd((fl.sth_vs_tmm || {}).sth_cost), _t('真實市場均價 ') + fmt.usd((fl.sth_vs_tmm || {}).tmm)) + kpi(_t('交易所供給'), fmt.n(ex.exchange_supply_share_pct, 2) + '%', _t('7 日 ') + fmt.pct(ex.exchange_supply_chg7_pct, 2) + _t(' · 90 日 ') + fmt.pct(ex.exchange_supply_chg90_pct, 2)) + kpi(_t('算力 7 日均'), fmt.n(mi.hash7, 0) + ' EH/s', _t('週 ') + fmt.pct(mi.wk_chg_pct, 1) + ' · hashprice $' + fmt.n(mi.hashprice, 1)) + kpi(_t('下次難度調整'), fmt.pct(mi.diff_next_pct, 1), fmt.md(mi.retarget) + _t(' · 進度 ') + fmt.n(mi.diff_progress, 0) + '%', mi.diff_progress) + '</div><div class="grid">' + interpPanel(ocInterp()) +
      panel('span-5', _t('籌碼分布（URPD）'), fmt.md(u.date) + _t(' · 每 2,000 美元一格'), urpdSay(u) + '<div id="c-urpd"></div>') +
      panel('span-7', _t('短期持有者：成本 vs 價格'), _t('bitcoin-data · 近 2 年'), legend([[_t('短期持有者成本'), 'var(--s2)'], [_t('真實市場均價'), 'var(--s3)']]) + '<div class="chart" id="c-cost"></div>' + _t('<div class="panel-h" style="margin-top:6px"><h2>短期持有者獲利比例</h2><span class="src">2025 頂部 ') + fmt.n((ch.viz || {}).top_vals ? ch.viz.top_vals.profit : null, 1) + '%</span></div><div class="chart" id="c-profit"></div>') +
      panel('span-7', _t('鏈上指標'), 'bitcoin-data.com', t) + panel('span-5', _t('頂部雷達'), _t('2022/11 起本輪百分位'), rt) + '</div>';
  };
  V.onchain.after = function () {
    var v = D.chips.viz || {}, u = v.urpd || {}, c = D.price.bar.c, el = $('#c-urpd');
    if (el && u.band) {
      var pv = {}; ((u.prev7 || {}).band || []).forEach(function (b) { pv[b[0]] = b[1]; });
      var rows = u.band.filter(function (b) { return b[0] >= c * 0.62 && b[0] <= c * 1.4; }).slice().reverse().map(function (b) { var cur = c >= b[0] && c < b[0] + (u.width || 2000); return { label: fmt.k(b[0]), v: b[1], color: cur ? 'var(--flare)' : 'var(--s1)', cls: cur ? 'cur' : '', right: _T(fmt.n(b[1] / 1e4, 1) + '萬', fmt.n(b[1] / 1e3, 0) + 'K'), prev: pv[b[0]], tip: '<div class="t">' + fmt.usd(b[0]) + '–' + fmt.usd(b[0] + (u.width || 2000)) + _t('</div><div class="r"><i style="background:var(--s1)"></i><span>籌碼</span><b>') + fmt.n(b[1]) + _t(' 顆</b></div>') + (pv[b[0]] != null ? _t('<div class="r"><i></i><span>7 天前</span><b>') + fmt.n(pv[b[0]]) + '</b></div>' : '') }; });
      el.innerHTML = ladderHtml(rows, { dense: true }); bindLadder(el, rows);
    }
    mount($('#c-cost'), function (el) { var r = v.cost || []; lineChart(el, { h: 220, series: [{ name: _t('短期持有者成本'), data: r.map(function (x) { return [x[0], x[2]]; }), color: 'var(--s2)' }, { name: _t('真實市場均價'), data: r.map(function (x) { return [x[0], x[3]]; }), color: 'var(--s3)' }], refs: [{ y: c, color: 'var(--ink-3)', label: _t('收盤 ') + fmt.k(c), below: true }], tipFmt: fmt.usd, aria: _t('成本線') }); });
    mount($('#c-profit'), function (el) { lineChart(el, { h: 170, series: [{ name: _t('獲利比例'), data: v.profit || [], color: 'var(--s4)', area: true }], y0: 0, y1: 100, yFmt: function (x) { return x + '%'; }, tipFmt: function (x) { return x.toFixed(1) + '%'; }, aria: _t('短期持有者獲利比例') }); });
  };

  V.book = function () {
    var o = D.orderbook; if (!o) return _t('<p class="err">本日未取得掛單簿資料。</p>');
    var w = o.walls || {}, rd = o.rounds || {}, t = o.totals || {};
    var walls = function (arr, col) { return (arr || []).slice(0, 5).map(function (x) { return '<div class="event"><span class="d">' + fmt.usd(x[0]) + '</span><span style="color:var(--ink-2)">' + esc(venue(x[2])) + _t(' 最多</span><span class="num" style="color:') + col + '">$' + fmt.n(x[1], 1) + 'M</span></div>'; }).join(''); };
    return readBar('book') + '<div class="kpis">' + kpi(_t('快照中間價'), fmt.usd(o.mid), (o.ts || '').replace('T', ' ').replace('+00:00', ' UTC')) + kpi(_t('±15% 買單合計'), '$' + fmt.n(t.wide_bid, 0) + 'M', _t('現貨 $') + fmt.n(t.wide_bid_spot, 0) + 'M') + kpi(_t('±15% 賣單合計'), '$' + fmt.n(t.wide_ask, 0) + 'M', _t('現貨 $') + fmt.n(t.wide_ask_spot, 0) + 'M') + kpi(_t('買賣比'), fmt.n(t.wide_bid / t.wide_ask, 2), _t('>1 下方承接較厚')) + '</div><div class="grid">' + interpPanel(bkInterp(o), _t('依快照當下的掛單自動產生 · 掛單可隨時撤')) +
      panel('span-8', _t('全景：每 1,000 美元一格'), _t('7 個整本可得的場所 · ±15%'), legend([[_t('買單'), 'var(--up)'], [_t('賣單'), 'var(--down)']]) + '<div id="c-book"></div>') +
      panel('span-4', _t('最大的牆'), '', _t('<div class="panel-h"><h2 style="color:var(--down)">上方賣牆</h2></div><div class="events">') + walls(w.ask, 'var(--down)') + _t('</div><div class="panel-h" style="margin-top:8px"><h2 style="color:var(--up)">下方買牆</h2></div><div class="events">') + walls(w.bid, 'var(--up)') + '</div>' +
        _t('<div class="panel-h" style="margin-top:8px"><h2>整數關卡</h2></div><div class="events">') + Object.keys(rd).sort().reverse().map(function (k) { var r = rd[k]; return '<div class="event"><span class="d">' + fmt.usd(+k) + '</span><span style="color:var(--ink-2)">' + (r.side === 'a' ? _t('賣') : _t('買')) + _t('方第 ') + r.rank + _t('／') + r.of + _t(' 名</span><span class="num">$') + fmt.n(r.musd, 1) + 'M</span></div>'; }).join('') + _t('</div><p class="note">掛單可隨時撤；Binance 期貨與 Bybit 讀不到，永續部分偏低估。</p>')) + '</div>';
  };
  V.book.after = function () {
    var o = D.orderbook, el = $('#c-book'); if (!o || !el) return;
    var ven = o.wide.venues, lab = function (k) { return venue((o.meta[k] || {}).label || k); };
    var rows = o.wide.rows.map(function (r) { var tot = r[2].reduce(function (a, b) { return a + b; }, 0); return { label: fmt.k(r[0]) + (r[1] === 'a' ? ' ▲' : ' ▼'), v: tot, color: r[1] === 'a' ? 'var(--down)' : 'var(--up)', cls: r[0] === Math.floor(o.mid / 1000) * 1000 ? 'mid' : '', right: '$' + fmt.n(tot, 1) + 'M', tip: '<div class="t">' + fmt.usd(r[0]) + ' · ' + (r[1] === 'a' ? _t('賣單') : _t('買單')) + '</div>' + r[2].map(function (v, i) { return v >= 0.5 ? '<div class="r"><i style="background:' + (r[1] === 'a' ? 'var(--down)' : 'var(--up)') + '"></i><span>' + esc(lab(ven[i])) + '</span><b>$' + fmt.n(v, 1) + 'M</b></div>' : ''; }).join('') }; });
    el.innerHTML = ladderHtml(rows, { dense: true }); bindLadder(el, rows);
  };

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
      _t('<h3>原則</h3><p>先給結論再給證據。各版「這些數字代表什麼」與表格下方的解讀，是用當日數值套固定門檻自動產生（門檻寫在句子裡），標籤「偏多／偏空／留意／中性」只描述該數字對價格的一般含意，不是預測，也不連動出場規則。寧可標示「本日未取得」，也不推估或沿用舊數字。不同資料商的數字不相減。分數一律附樣本數，樣本少於 30 不下結論。</p><h3>限制</h3><p>週期模型只有 3–4 輪歷史，所有「遞減」推論都假設趨勢延續。冪律擬合線會隨新資料下修。掛單隨時可撤。短線預測不連動出場規則。bitcoin-data 免費額度有限，部分變化較慢的鏈上指標每 2 天更新一次，以資料日期標示。</p>') +
      _t('<h3>免責聲明</h3><p>本站內容僅供研究與教育參考，不構成投資建議。加密資產波動極大，請依自身情況判斷並自負風險。</p></div>')) +
      panel('span-5', _t('資料來源'), '', '<div class="events">' + [[_t('價格、均線、ATR'), _t('Kraken 日線（UTC）')], [_t('波動率、基差、選擇權'), _t('Deribit 公開 API')], [_t('MVRV、交易所供給、冪律'), 'CoinMetrics Community'], [_t('SOPR、NUPL、籌碼'), 'bitcoin-data.com'], [_t('算力、難度'), 'mempool.space'], [_t('相關係數、利率'), 'FRED'], [_t('ETF 流量'), _t('The Block（與 Farside 同口徑）')], [_t('掛單簿'), _t('Coinbase、Bitstamp、Gemini、Bitfinex、Kraken、Binance、OKX、Gate、MEXC、Deribit、Hyperliquid')], [_t('綜合訊號'), _t('Tidemark（north7.github.io）')]].map(function (r) { return '<div class="event" style="grid-template-columns:minmax(0,1fr) minmax(0,1.2fr)"><span>' + r[0] + '</span><span style="color:var(--ink-2)">' + r[1] + '</span></div>'; }).join('') + _t('</div><p class="note">資料日 ') + D.meta.bar_date + _t(' · 管線產出 ') + (D.meta.generated_utc || '').replace('T', ' ').slice(0, 16) + _t(' UTC · 結論 ') + (N ? (N.written_utc || '').replace('T', ' ').slice(0, 16) + ' UTC' : '—') + '</p>') + '</div>';
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
    var ft = document.querySelectorAll('.foot span'); ['© Daybreak', 'For research only — not investment advice', 'Press 1–9, 0 to switch sections', 'Swipe left/right to switch sections'].forEach(function (x, i) { if (ft[i]) ft[i].textContent = x; });
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
