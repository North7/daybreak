/* 破曉 Daybreak — 前端（無外部套件）。讀 data/latest.json（每日資料管線）與 data/notes.json（每日結論）。 */
(function () {
  'use strict';
  var D = null, N = null, H = [];
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
    if (all.length < 2) { el.innerHTML = '<p class="note">本日未取得資料。</p>'; return; }
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
    var d = cfg.data; if (!d || !d.length) { el.innerHTML = '<p class="note">本日未取得資料。</p>'; return; }
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
      b.addEventListener('pointermove', function (ev) { showTip(ev.clientX, ev.clientY, r[2] || ('<div class="t">' + esc(r[0]) + '</div><div class="r"><i style="background:currentColor"></i><span>值</span><b>' + fmt.n(r[1], 1) + '</b></div>')); });
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
    el.innerHTML = svgEl(W, Ht, s, '近 20 日 K 線');
    el.querySelectorAll('.cd').forEach(function (g) {
      var r = rows[+g.getAttribute('data-i')];
      g.addEventListener('pointermove', function (ev) { showTip(ev.clientX, ev.clientY, '<div class="t">' + r[0] + '</div>' + [['開', r[1]], ['高', r[2]], ['低', r[3]], ['收', r[4]]].map(function (p) { return '<div class="r"><i style="background:' + (r[4] >= r[1] ? 'var(--up)' : 'var(--down)') + '"></i><span>' + p[0] + '</span><b>' + fmt.n(p[1]) + '</b></div>'; }).join('') + '<div class="r"><i></i><span>漲跌</span><b>' + fmt.pct((r[4] / r[1] - 1) * 100, 2) + '</b></div>'); });
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
    return '<div class="read' + (bare ? ' bare' : '') + '" data-k="' + key + '">' + (bare ? '' : '<span class="tag">今日判讀<small>TODAY’S READ</small></span>') + '<div><p>' + esc(m.lead) + '</p><ul>' + (m.points || []).map(function (p) { return '<li>' + esc(p) + '</li>'; }).join('') + '</ul></div></div>';
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
    var it = [['BTC 收盤', fmt.usd(p.bar.c), fmt.pct(p.bar.chg_pct, 2), p.bar.chg_pct >= 0], ['200 日均線', fmt.usd(p.ma.sma200), fmt.pct((p.bar.c / p.ma.sma200 - 1) * 100), true], ['DVOL', fmt.n((dv.dvol || {}).value, 1), '一年第 ' + fmt.n((dv.dvol || {}).pct_1y, 0) + ' 百分位'], ['資金費率', fmt.pct((dv.deriv || {}).funding_ann, 1), '年化'], ['ETF ' + fmt.md(le.d), (le.musd >= 0 ? '+' : '') + fmt.n(le.musd, 1) + 'M', '', le.musd >= 0], ['10 年期殖利率', fmt.n((fr.DGS10 || {}).last, 2) + '%', fmt.md((fr.DGS10 || {}).last_date)], ['BTC–那斯達克', fmt.n((fr.NASDAQCOM || {}).corr30, 2), '30 日相關'], ['MVRV ÷ 前高', fmt.n(cm.mvrv_vs_prior, 3), '賣出線 0.75'], ['冪律倍數', fmt.n(pl.ratio, 2) + '×', '合理價 ' + fmt.k(pl.fair)], ['Tidemark', fmt.n((tm.top || {}).signal, 0) + ' / ' + fmt.n((tm.bottom || {}).signal, 0), '頂 / 底'], ['算力', fmt.n(mi.hash7, 0) + ' EH/s', fmt.pct(mi.wk_chg_pct, 1), mi.wk_chg_pct >= 0], ['下次難度', fmt.pct(mi.diff_next_pct, 1), fmt.md(mi.retarget)]];
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
    F.ladder.forEach(function (v, i) { s += '<rect x="' + (X(v) - 2).toFixed(1) + '" y="' + (y - 14) + '" width="4" height="28" rx="2" fill="var(--flare)" opacity="' + (1 - i * .08).toFixed(2) + '"><title>出場第 ' + (i + 1) + ' 階 ' + fmt.usd(v) + '</title></rect>'; });
    s += '<text x="' + X(F.ladder[0]).toFixed(1) + '" y="' + (y - 24) + '" style="font-size:12px" fill="var(--flare)">出場階梯 125K–215K（8 階）</text>';
    var mk = function (v, lab, col, up) { var xx = X(v); return '<line x1="' + xx.toFixed(1) + '" x2="' + xx.toFixed(1) + '" y1="' + (y - 12) + '" y2="' + (y + 12) + '" stroke="' + col + '" stroke-width="2"/><text x="' + xx.toFixed(1) + '" y="' + (up ? y - 22 : y + 30) + '" text-anchor="middle" style="font-size:12px" fill="' + col + '">' + lab + '</text>'; };
    s += mk(S.sma200, '避險線 ' + fmt.k(S.sma200) + '（' + fmt.pct((S.sma200 / c - 1) * 100, 0) + '）', 'var(--orbit)', true);
    s += mk(S.k075_price, 'MVRV 0.75 ' + fmt.k(S.k075_price) + '（' + fmt.pct((S.k075_price / c - 1) * 100, 0) + '）', 'var(--rose)', false);
    s += '<circle cx="' + X(c).toFixed(1) + '" cy="' + y + '" r="14" fill="var(--flare)" opacity=".18"><animate attributeName="r" values="11;18;11" dur="3s" repeatCount="indefinite"/></circle><circle cx="' + X(c).toFixed(1) + '" cy="' + y + '" r="7" fill="var(--ink)" stroke="var(--deck)" stroke-width="2.5"/><text x="' + X(c).toFixed(1) + '" y="' + (y + 32) + '" text-anchor="middle" style="font-family:var(--f-mono);font-size:13px" fill="var(--ink)">收盤 ' + fmt.k(c) + '</text>';
    return '<svg viewBox="0 0 ' + W + ' ' + Ht + '" role="img" aria-label="收盤到避險線與出場階梯的距離">' + s + '</svg>';
  }
  /* 巨型收盤價：數字本身是主視覺，近 20 日收盤線疊在數字上；滑過可逐日回看 */
  function megaHtml(c) {
    var rows = D.price.rows20 || [], cl = rows.map(function (r) { return r[4]; }), lo = Math.min.apply(null, cl), hi = Math.max.apply(null, cl), n = cl.length;
    var Y = function (v) { return 90 - (v - lo) / (hi - lo || 1) * 80; }, pts = cl.map(function (v, i) { return [(i / (n - 1) * 1000).toFixed(1), Y(v).toFixed(2)]; });
    var d = pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0] + ',' + p[1]; }).join('');
    var sma = D.price.ma.sma200;
    return '<div class="mega" id="mega">' +
      '<div class="hud tl"><span>BTC / USD · 收盤</span><b id="h-d">' + D.meta.bar_date.replace(/-/g, '.') + ' UTC</b></div>' +
      '<div class="hud tr"><span>日漲跌</span><b id="h-c" class="' + (c.chg_pct >= 0 ? 'up' : 'down') + '">' + fmt.pct(c.chg_pct, 2) + '</b></div>' +

      '<b class="big" id="mega-n" data-t="' + fmt.n(c.c) + '">' + fmt.n(c.c) + '</b>' +
      '<div class="spark" aria-hidden="true"><svg viewBox="0 0 1000 100" preserveAspectRatio="none"><path class="line" d="' + d + '"/></svg><span class="scrub" id="m-scrub"></span><span class="dot" id="m-dot" style="left:100%;top:' + Y(cl[n - 1]).toFixed(2) + '%"></span></div>' +
      '<p class="mega-hint">滑過數字，逐日回看近 20 天</p>' +
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
  function tapeHtml() { var one = tapeItems(); return '<div class="tape" aria-label="今日數據帶"><div class="tape-track">' + one + one + '</div></div>'; }
  /* 數字解碼：每個數字先亂跳，再由左到右依序定格 */
  function decodeNums(root) {
    if (reduced || !root) return;
    root.querySelectorAll('.kpi .v, .watch .v, .news-sum b, .mod-h .idx').forEach(function (el, k) {
      var txt = el.textContent, f = 0, tot = 18 + k * 2;
      (function step() { f++; el.textContent = txt.replace(/\d/g, function (d, i) { return f / tot * txt.length > i ? d : String((Math.random() * 10) | 0); }); if (f < tot) setTimeout(step, 32); else el.textContent = txt; })();
    });
  }
  function impChip(i) { return '<span class="imp ' + i + '">' + ({ bull: '偏多', bear: '偏空', neutral: '中性' })[i] + '</span>'; }

  // 市場階段 P23：資料管線依寫死規則計算（data/latest.json cycle.stage），不連動出場規則
  var STAGE = { '熊市': ['熊市', 'down'], '轉換期': ['熊牛轉換期', 'orbit'], '牛市': ['牛市', 'up'] };
  function stageChip() { var s = STAGE[(D.cycle.stage || {}).stage]; return s ? '<span class="chip ' + s[1] + '">' + s[0] + '</span>' : ''; }
  function stageHtml() {
    var st = D.cycle.stage || {}, s = STAGE[st.stage], c = D.price.bar.c;
    if (!s) return '<p class="err">本日未取得市場階段。</p>';
    var need = (st.bull_need || {}).run || 30, run = st.above_rising_run || 0, sma = st.sma200, ev = st.evidence || {}, gap = [];
    if (run < need) gap.push('再站穩 ' + (need - run) + ' 天');
    var lines = st.stage === '牛市' ? [['✓', '牛市（單向鎖定）', fmt.md(st.since) + ' 起成立；之後不因短線跌破而改判。'], ['↩', '什麼會退回熊市', '收盤連 30 日在下降的 200 日均線之下；現在 ' + (st.below_falling_run || 0) + ' 天。']]
      : st.stage === '轉換期' ? [['✓', '不是熊市了', '收盤連 ' + run + ' 天站在上升的 200 日均線（' + fmt.usd(sma) + '）之上，高出 ' + fmt.pct((c / sma - 1) * 100, 1) + '。'],
          ['△', '還不是牛市', gap.length ? '差 ' + gap.join('、') + '。' : '條件已齊，下一次收盤確認。'],
          ['↩', '什麼會退回熊市', '收盤連 5 日在 200 日均線（' + fmt.usd(sma) + '，' + fmt.pct((sma / c - 1) * 100, 1) + '）之下；現在 ' + (st.below_run || 0) + '/5。']]
      : [['×', '仍是熊市', '收盤' + (run ? '在上升的 200 日均線之上 ' + run + ' 天' : '不在上升的 200 日均線之上') + '。'], ['↗', '什麼會轉為轉換期', st.capitulation_seen ? '收盤站上上升中的 200 日均線。' : '燈號一（投降）重新出現，且收盤站上上升中的 200 日均線。']];
    var light = function (ok, name, val, cond) { return '<div class="light' + (ok ? ' on' : '') + '"><span class="mk">' + (ok ? '✓' : '·') + '</span><b>' + name + '</b><span class="v num">' + val + '</span><span class="note">' + cond + '</span></div>'; };
    return '<p class="say">現在是 <b>' + s[0] + '</b>（' + fmt.md(st.since) + ' 起）' + (st.stale ? '；本日缺資料，沿用前一日判定' : '') + '。</p>' +
      '<div class="lights">' + light(st.capitulation_seen, '燈號一：投降', st.capitulation_seen ? '已出現過' : '未出現', '過去式；一個週期只看一次') +
        light(run >= need, '上升 200 日線上', run + ' / ' + need + ' 天', '線 ' + fmt.usd(sma) + (st.sma200_rising ? '，上升中' : '，下降中')) +
        light(ev.n && ev.ok * 2 > ev.n, '佐證燈號', ev.n ? ev.ok + ' / ' + ev.n : '—', '只顯示、不參與判定；過半亮起才打勾') + '</div>' +
      (ev.items ? '<div class="tbl-wrap"><table class="tbl evid"><tbody>' + ev.items.map(function (e) {
        var v = e.id === 'mvrv1y' ? fmt.n(e.value, 3) + '（均值 ' + fmt.n(e.ref, 3) + '）' : e.id === 'sth' ? fmt.usd(e.value) : fmt.pct(e.value, e.id === 'rcgrowth' ? 2 : 1);
        return '<tr><td><span class="mk-s' + (e.ok ? ' ok' : '') + '">' + (e.ok ? '✓' : '×') + '</span><b>' + esc(e.label) + '</b></td><td class="num">' + v + '</td><td>' + esc(e.cond) + '</td><td class="num">' + fmt.md(e.date) + '</td></tr>';
      }).join('') + '</tbody></table></div>' : '') +
      '<div class="rules">' + lines.map(function (l) { return '<div class="rule"><span class="t"><span class="mk-s">' + l[0] + '</span>' + l[1] + '</span><span class="d">' + l[2] + '</span><span></span></div>'; }).join('') + '</div>' +
      '<p class="note">判定規則：轉換期＝燈號一（投降）✓ 且收盤在上升的 200 日均線之上（上升＝高於 30 天前）；牛市＝燈號一 ✓ 且收盤連 30 日在上升的 200 日均線之上，成立後單向鎖定；退回熊市＝轉換期中連 5 日收在 200 日均線下，牛市則需連 30 日在下降的 200 日均線下。佐證燈號只顯示證據強弱，不參與判定。</p>' +
      '<p class="note">限制：2014 年起只有 3–4 輪週期可回測。這條價格規則在候選標準中假訊號最少，但 2019 年中一樣誤判為牛市，之後跌了近五成；沒有任何規則能同時又快又少假訊號。交易所供給 90 日轉負原為必要條件，回測顯示換視窗長度就失效、地址歸屬會事後修正（有前視偏差），且 2025 年 99% 的日子成立，2026-10-09 起降為佐證。牛市條件在頂部附近也會亮，不是賣出訊號；市場階段只是標籤，不連動出場框架。</p>';
  }
  // 以下三塊由每日結論任務寫進 notes.json；不是當天的就標「上一期」
  function staleTag() { return N && N.stale ? '<span class="chip">上一期 ' + fmt.md(N.date) + '</span>' : ''; }
  function actionsHtml() {
    var a = N && N.actions || [], L = { do: '可以做', dont: '不要做', watch: '要盯', flip: '會推翻' };
    if (!a.length) return '<p class="note">本期沒有寫。</p>';
    return '<ul class="acts">' + a.map(function (x) { return '<li><span class="b ' + esc(x.kind) + '">' + (L[x.kind] || esc(x.kind)) + '</span><span><b>' + esc(x.head) + '</b>' + esc(x.text || '') + '</span></li>'; }).join('') + '</ul>';
  }
  function changesHtml() {
    var a = N && N.changes || [], AR = { up: ['▲', 'u'], down: ['▼', 'd'], flat: ['■', ''] };
    if (!a.length) return '<p class="note">本期沒有寫。</p>';
    return '<ul class="deltas">' + a.map(function (x) { var r = AR[x.dir] || AR.flat; return '<li><span class="ar ' + r[1] + '">' + r[0] + '</span><div><h3>' + esc(x.title) + '</h3>' + (x.fig ? '<div class="fig num">' + esc(x.fig) + '</div>' : '') + '<p>' + esc(x.say || '') + '</p></div></li>'; }).join('') + '</ul>';
  }
  function researchHtml() {
    var r = N && N.research || {}, rows = r.items || [];
    if (!rows.length) return '<p class="note">' + esc(r.summary || '本期沒有新的機構研報。') + '</p>';
    return (r.summary ? '<p class="say">' + esc(r.summary) + '</p>' : '') + '<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:20%"><col style="width:44%"><col style="width:36%"></colgroup><thead><tr><th>來源</th><th>重點</th><th>對本站判斷的意義</th></tr></thead><tbody>' +
      rows.map(function (x) { var src = x.url ? '<a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(x.source) + '</a>' : esc(x.source); return '<tr><td><b>' + src + '</b><br><span class="note">' + esc(x.title || '') + (x.date ? '，' + fmt.md(x.date) : '') + (x.access === 'title_only' ? '・只取得標題' : '') + '</span></td><td>' + esc(x.points) + '</td><td>' + esc(x.meaning) + '</td></tr>'; }).join('') +
      '</tbody></table></div><p class="note">研報只作文字對照，不改變任何規則；只取得標題的不作判斷依據。</p>';
  }
  function newsItem(n, lead, ix) {
    return '<article class="' + (lead ? 'news-lead' : 'news-item') + '">' + (ix ? '<span class="idx">' + ('0' + ix).slice(-2) + '</span>' : '') + '<div class="news-meta"><span class="cat">' + esc(n.cat) + '</span>' + impChip(n.impact) + '<span>' + esc(n.time.slice(5).replace('-', '/')) + '</span></div><h3>' + esc(n.title) + '</h3><div class="read-box"><b class="lbl">解讀</b>' + esc(n.read) + '</div><div class="src-link">來源：<a href="' + esc(n.url) + '" target="_blank" rel="noopener">' + esc(n.source) + '</a>' + (n.module ? ' · <a href="#' + n.module + '">看相關數據 →</a>' : '') + '</div></article>';
  }

  /* ---------------- Views ---------------- */
  var V = {};
  var ROUTES = [
    ['overview', '頭版', '今天的比特幣', 'M4 5h16v14H4zM8 9h8M8 13h5', 'FRONT PAGE'],
    ['news', '消息', '新聞與解讀', 'M5 4h11l3 3v13H5zM9 9h6M9 13h6M9 17h4', 'THE BRIEF'],
    ['cycle', '週期', '離頂部還多遠', 'M12 3a9 9 0 1 0 9 9M12 7a5 5 0 1 0 5 5M12 12h9', 'CYCLE'],
    ['market', '價格', '日線與關鍵價位', 'M4 19V9m5 10V5m5 14v-7m5 7V8', 'PRICE'],
    ['deriv', '衍生品', '波動率與選擇權', 'M3 17c3-8 6-8 9 0s6 8 9 0', 'DERIVATIVES'],
    ['flows', '資金', 'ETF 與宏觀', 'M4 7h16M4 12h10M4 17h6', 'FLOWS · MACRO'],
    ['onchain', '鏈上', '持有者與籌碼', 'M7 7h4v4H7zM13 13h4v4h-4zM11 9h4M9 11v4', 'ON-CHAIN'],
    ['book', '掛單簿', '13 個交易所', 'M5 4v16M5 7h9M5 11h13M5 15h7M5 19h11', 'ORDER BOOK'],
    ['exit', '出場框架', '何時分批賣', 'M4 20h4v-4h4v-4h4V8h4V4', 'EXIT PLAN'],
    ['method', '方法', '資料與限制', 'M12 3v18M3 12h18M6 6l12 12', 'METHOD']
  ];

  V.overview = function () {
    var c = D.price.bar, ex = D.exit.status, cm = D.cycle.cm, pl = D.cycle.powerlaw || {}, tm = D.cycle.tidemark || {}, p6 = D.cycle.p6 || {};
    var news = (N && N.news || []).slice().sort(function (a, b) { return (b.weight || 0) - (a.weight || 0); });
    var wd = ['日', '一', '二', '三', '四', '五', '六'][new Date(D.meta.bar_date + 'T12:00:00Z').getUTCDay()];
    // 標題裡的數字（連同緊接的單位：%、億、萬、倍、基點、K 等）一律用號外紅
    var hl = esc(N ? N.headline : '').replace(/(\d{1,2}\/\d{1,2}(?!\d)|[+\-−]?\d[\d,.]*(?:\s?(?:%|億|萬|千|兆|倍|個基點|基點|bp|K|M|B)(?![A-Za-z]))?)/g, '<em>$1</em>');
    var watch = (N && N.watch || []).map(function (w) { var dd = (w.value / c.c - 1) * 100; return '<div><span class="k">' + esc(w.label) + '</span><span class="v ' + (dd >= 0 ? 'up' : 'dn') + '">' + fmt.pct(dd, 1) + '</span><span class="px">' + fmt.usd(w.value) + '</span><span class="n">' + esc(w.note) + '</span></div>'; }).join('');
    var front = '<section class="front" id="front"><div class="dateline"><b>號外</b><span>DAYBREAK No.' + ('00' + (N ? N.edition : 0)).slice(-3) + '</span><hr><span>' + D.meta.bar_date.replace(/-/g, '.') + '（' + wd + '）收盤版</span></div>' +
      '<h2 class="reveal">' + hl + '</h2>' + megaHtml(c) +
      '<div class="front-foot"><div class="dek"><div class="stamp"><span class="chip flare"><i></i>' + esc(N ? N.stance.label : '—') + '</span><span class="chip">' + (N ? esc(N.stance.short) : '') + '</span>' + stageChip() + '</div><p>' + esc(N ? N.summary : '') + '</p></div><div class="watch">' + watch + '</div></div></section>';
    var newsBlock = news.length ? '<div class="sec-h"><h2>今日要聞</h2><span class="en">The Brief</span><hr><a href="#news">全部 ' + news.length + ' 則 →</a></div><div class="news-front">' + newsItem(news[0], true) + '<div class="news-side">' + news.slice(1, 4).map(function (n, i) { return newsItem(n); }).join('') + '</div></div>' : '';
    var kp = '<div class="kpis">' +
      kpi('MVRV ÷ 前一輪高點', fmt.n(cm.mvrv_vs_prior, 3), '賣出線 0.75 · 2025 頂 0.78', cm.mvrv_vs_prior / 0.75 * 100) +
      kpi('冪律倍數', fmt.n(pl.ratio, 2) + '×', '合理價 ' + fmt.usd(pl.fair), (pl.ratio || 0) / 1.2 * 100) +
      kpi('Tidemark 頂 / 底', fmt.n((tm.top || {}).signal, 0) + ' / ' + fmt.n((tm.bottom || {}).signal, 0), '門檻 50 · ' + fmt.md(tm.price_date) + ' 資料') +
      kpi('頂部三指標百分位', ['mvrv_z', 'nupl', 'puell'].map(function (k) { return fmt.n(p6[k], 0); }).join(' / '), '任兩項到 80 進入頂部區', ((p6.mvrv_z || 0) + (p6.nupl || 0) + (p6.puell || 0)) / 3 / 0.8) +
      kpi('離出場第一階', fmt.pct(ex.next_step_dist_pct, 0), fmt.usd(ex.next_step) + ' 起每階 12.5%', 100 - Math.min(100, ex.next_step_dist_pct)) + '</div>';
    var ev = (N && N.events || []).map(function (e) { var dd = dnOf(e.date) - dnOf(D.meta.bar_date); return '<div class="event"><span class="d">' + e.date.slice(5).replace('-', '/') + '</span><span>' + esc(e.label) + '</span><span class="in' + (dd === 1 ? ' now' : '') + '">' + (dd > 1 ? dd - 1 + ' 天後' : dd === 1 ? '今天' : '已過') + '</span></div>'; }).join('');
    var plan = '<div class="sec-h"><h2>今天該做什麼</h2><span class="en">The Plan</span><hr>' + staleTag() + '</div><div class="grid">' +
      panel('span-7', '今天該做什麼、盯什麼', '依出場框架 · 非投資建議', actionsHtml()) + panel('span-5', '今天變了什麼', '相對上一期', changesHtml()) + '</div>';
    return front + tapeHtml() + newsBlock + plan +
      '<div class="sec-h"><h2>今日數據</h2><span class="en">The Numbers</span><hr></div>' + kp +
      '<div class="grid">' + panel('span-12', '離出場線還多遠', '以 ' + fmt.md(D.meta.bar_date) + ' 收盤計 · 對數刻度', '<div class="runway">' + runwaySvg() + '</div>') +
      panel('span-7', '價格近一年', 'CoinMetrics 每 7 天', '<div class="chart" id="c-ov-px"></div>') +
      panel('span-5', '接下來的日期', '', '<div class="events">' + ev + '</div>') + '</div>';
  };
  V.overview.after = function () {
    bindMega();
    var hist = D.price.history || [], cut = hist[hist.length - 1][0] - 400;
    mount($('#c-ov-px'), function (el) { lineChart(el, { h: 250, series: [{ name: '價格', data: hist.filter(function (p) { return p[0] >= cut; }), color: 'var(--s1)', area: true }], refs: [{ y: D.price.ma.sma200, color: 'var(--ink-3)', label: '200 日均線 ' + fmt.k(D.price.ma.sma200), below: true }], tipFmt: fmt.usd, aria: '近一年價格' }); });
  };

  V.news = function () {
    var news = (N && N.news || []);
    var rs = '<div class="grid" style="margin-top:28px">' + panel('span-12', '權威研報怎麼看', 'Glassnode · The Block · K33 · Coinbase Institutional 等', researchHtml(), staleTag()) + '</div>';
    if (!news.length) return '<p class="err">今天還沒有整理好的消息。</p>' + rs;
    var cats = ['全部'].concat(news.map(function (n) { return n.cat; }).filter(function (c, i, a) { return a.indexOf(c) === i; }));
    var cnt = function (k) { return news.filter(function (n) { return n.impact === k; }).length; };
    return '<div class="news-sum"><div><span class="note">偏多</span><b style="color:var(--up)">' + ('0' + cnt('bull')).slice(-2) + '</b></div><div><span class="note">偏空</span><b style="color:var(--down)">' + ('0' + cnt('bear')).slice(-2) + '</b></div><div><span class="note">中性</span><b>' + ('0' + cnt('neutral')).slice(-2) + '</b></div></div>' +
      '<div class="filters" id="nf" role="group" aria-label="分類">' + cats.map(function (c, i) { return '<button type="button" aria-pressed="' + (i === 0) + '" data-c="' + esc(c) + '">' + esc(c) + '</button>'; }).join('') + '</div>' +
      '<div class="news-grid" id="ng"></div><p class="note">每則消息都查證過發布日期；「解讀」說明它對比特幣的意義，並對照本站的數據。消息只作參考，不改變任何出場規則。</p>' + rs;
  };
  V.news.after = function () {
    var news = (N && N.news || []).slice().sort(function (a, b) { return (b.weight || 0) - (a.weight || 0) || (b.time > a.time ? 1 : -1); });
    function draw(cat) { $('#ng').innerHTML = news.filter(function (n) { return cat === '全部' || n.cat === cat; }).map(function (n, i) { return '<article class="news-card"><div class="news-meta"><span class="cat">' + esc(n.cat) + '</span>' + impChip(n.impact) + '<span>' + esc(n.time.slice(5).replace('-', '/')) + '</span></div><h3>' + esc(n.title) + '</h3><div class="read-box"><b class="lbl">解讀</b>' + esc(n.read) + '</div><div class="src-link">來源：<a href="' + esc(n.url) + '" target="_blank" rel="noopener">' + esc(n.source) + '</a></div>' + (n.module ? '<a class="go" href="#' + n.module + '">看相關數據 →</a>' : '') + '</article>'; }).join(''); }
    draw('全部');
    $('#nf').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; this.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); draw(b.getAttribute('data-c')); });
  };

  V.cycle = function () {
    var cm = D.cycle.cm, pl = D.cycle.powerlaw || {}, tm = D.cycle.tidemark || {}, p6 = D.cycle.p6 || {}, st = D.cycle.stage || {}, M = D.cycle.model;
    var w = M.weights;
    return readBar('cycle') + '<div class="grid">' +
      panel('span-12', '市場階段：' + (STAGE[st.stage] || ['—'])[0], 'P23 · 熊市 → 轉換期 → 牛市', stageHtml()) +
      panel('span-12', '長期路徑：四種走法', '每月底重估 · 下次 ' + M.next_review, legend([['直接修復 ' + w['直接修復'] + '%', 'var(--s4)', 'dash'], ['淺回檔 ' + w['淺回檔'] + '%', 'var(--s1)', 'dash'], ['基準雙底 ' + w['基準雙底'] + '%', 'var(--s2)', 'dash'], ['延後新低 ' + w['延後新低'] + '%', 'var(--s3)', 'dash'], ['已實現', 'var(--ink)'], ['頂部 80% 區間', 'var(--flare)', 'box']]) + '<div class="chart" id="c-path"></div><p class="note">頂部模型：中位 ' + fmt.usd(M.top_model.median) + '，80% 區間 ' + fmt.k(M.top_model.p10) + '–' + fmt.k(M.top_model.p90) + '，時間 ' + esc(M.top_model.timing) + '。路徑是本站的預測，2028 年以後只供量級參考。</p>') +
      panel('span-7', 'MVRV ÷ 前一輪高點', 'CoinMetrics · 2021 起', '<p class="say">現在 <b>' + fmt.n(cm.mvrv_vs_prior, 3) + '</b>；連 5 天站上 0.75（約 ' + fmt.usd(cm.k075_price) + '）是出場框架的第一個鏈上賣點。</p><div class="chart" id="c-p20"></div>') +
      panel('span-5', '頂部三指標', fmt.md(D.cycle.p6_date) + ' · 四年百分位', '<div class="meters">' + meter('MVRV Z', '<0 底 · >3.5 頂', p6.mvrv_z, fmt.n(p6.mvrv_z, 0), '百分位', [80, 85, 90]) + meter('NUPL', '淨未實現損益', p6.nupl, fmt.n(p6.nupl, 0), '百分位', [80, 85, 90]) + meter('Puell', '礦工收入倍數', p6.puell, fmt.n(p6.puell, 0), '百分位', [80, 85, 90]) + '</div><p class="note">任兩項到 80 進入頂部區；到 85 連 5 天多賣兩階；到 90 在 10 個交易日內賣完。</p>' ) +
      panel('span-7', '冪律：價格 ÷ 合理價', '每天只用當天以前資料擬合', '<p class="say">現在 <b>' + fmt.n(pl.ratio, 2) + ' 倍</b>（合理價 ' + fmt.usd(pl.fair) + '）。頂部倍數每輪縮小，照這個速度，下一輪頂部約在合理價的 ' + fmt.n((pl.next_top_ratio || [])[0], 2) + '–' + fmt.n((pl.next_top_ratio || [])[1], 2) + ' 倍。</p><div class="chart" id="c-pl"></div>', '<div class="seg" id="pl-seg"><button aria-pressed="false" data-v="all">2012 起</button><button aria-pressed="true" data-v="2020">2020 起</button></div>') +
      panel('span-5', 'Tidemark 綜合訊號', '第三方模型 · ' + fmt.md(tm.price_date) + ' 資料', '<div class="meters">' + meter('頂部訊號', '≥50 窗口 · ≥70 警戒', (tm.top || {}).signal || 0, fmt.n((tm.top || {}).signal, 1), (tm.top || {}).level || '—', [50, 70]) + meter('熱度', '五類加權', (tm.top || {}).heat || 0, fmt.n((tm.top || {}).heat, 1), (tm.top || {}).zone || '', [40, 65]) + meter('底部訊號', '≥50 底部區', (tm.bottom || {}).signal || 0, fmt.n((tm.bottom || {}).signal, 1), (tm.bottom || {}).level || '—', [50, 70]) + meter('冷度', '估值・礦工・價格結構', (tm.bottom || {}).cold || 0, fmt.n((tm.bottom || {}).cold, 1), '', []) + '</div>' +
        '<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:62%"><col style="width:38%"></colgroup><tbody>' + (tm.cats || []).map(function (x) { return '<tr><td>' + esc(x[0]) + (x[2] === 'partial' ? '＊' : '') + '</td><td><div class="pct"><i><b class="' + ((x[1] || 0) >= 80 ? 'hot' : '') + '" style="width:' + (x[1] || 0) + '%"></b></i><span class="num">' + (x[1] == null ? '—' : fmt.n(x[1], 0)) + '</span></div></td></tr>'; }).join('') + '</tbody></table></div><p class="note">' + esc((tm.cycle_test || {}).verdict || '') + '</p>') +
      '</div>';
  };
  V.cycle.after = function () {
    var M = D.cycle.model, cols = { '直接修復': 'var(--s4)', '淺回檔': 'var(--s1)', '基準雙底': 'var(--s2)', '延後新低': 'var(--s3)' };
    var md = function (y, m) { return Math.round(Date.UTC(y, m - 1, 15) / 864e5); };
    var series = Object.keys(M.nodes).map(function (k) { return { name: k, data: M.nodes[k].map(function (p) { return [md(p[0], p[1]), p[2]]; }), color: cols[k], dash: '5 5', w: 1.8, end: false }; });
    var real = M.realized.map(function (p) { return [md(p[0], p[1]), p[2]]; }); real.push([dnOf(D.meta.bar_date), D.price.bar.c]);
    series.push({ name: '已實現', data: real, color: 'var(--ink)', w: 2.6 });
    mount($('#c-path'), function (el) { lineChart(el, { h: el.clientWidth < 520 ? 260 : 340, log: true, series: series, hbands: [{ y0: M.top_model.p10, y1: M.top_model.p90, color: 'var(--flare-dim)' }], refs: [{ y: M.top_model.median, color: 'var(--flare)', label: '頂部中位 ' + fmt.k(M.top_model.median) }], vlines: [{ x: dnOf(D.cycle.next_halving_est), label: '2028/04 減半' }], tipFmt: fmt.usd, aria: '四條長期路徑' }); });
    var p20 = D.cycle.p20 || {};
    mount($('#c-p20'), function (el) { var top = dnOf('2025-10-06'), tv = (p20.rows || []).filter(function (r) { return Math.abs(r[0] - top) <= 2; })[0]; lineChart(el, { series: [{ name: '比值', data: p20.rows || [], color: 'var(--s1)', area: true }], refs: [{ y: 0.75, color: 'var(--down)', label: '0.75 第一階 ≈ ' + fmt.k(p20.k075) }, { y: 0.8, color: 'var(--down)', label: '0.80 第二階', below: false }], marks: tv ? [{ x: tv[0], y: tv[1], label: '2025 頂 ' + tv[1].toFixed(2), left: true }] : [], yFmt: function (v) { return v.toFixed(1); }, tipFmt: function (v) { return v.toFixed(3); }, aria: 'MVRV 除以前一輪高點' }); });
    var pl = D.cycle.powerlaw || {}, rng = '2020';
    function drawPl(el) {
      var rows = (pl.rows || []).map(function (r) { return [r[0], Math.pow(10, r[1])]; }); if (rng === '2020') rows = rows.filter(function (r) { return r[0] >= dnOf('2020-01-01'); });
      var mk = (pl.tops || []).concat(pl.bottoms || []).map(function (t) { var x = dnOf(t[0]); return rows.length && x >= rows[0][0] ? { x: x, y: t[1], label: t[1].toFixed(2), color: t[1] >= 1 ? 'var(--flare)' : 'var(--orbit)', below: t[1] < 1 } : null; }).filter(Boolean);
      lineChart(el, { log: true, series: [{ name: '倍數', data: rows, color: 'var(--s3)' }], hbands: [{ y0: (pl.bottom_band || [0.24, 0.48])[0], y1: (pl.bottom_band || [0.24, 0.48])[1], color: 'var(--orbit-dim)' }], refs: [{ y: 1, color: 'var(--ink-3)', label: '1.0 合理價' }], marks: mk, yFmt: function (v) { return v >= 1 ? v.toFixed(v >= 10 ? 0 : 1) : v.toFixed(2); }, tipFmt: function (v) { return v.toFixed(2) + '×'; }, aria: '價格除以冪律合理價' });
    }
    mount($('#c-pl'), drawPl);
    $('#pl-seg').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; rng = b.getAttribute('data-v'); this.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); drawPl($('#c-pl')); });
  };

  V.market = function () {
    var p = D.price, ma = p.ma, c = p.bar.c, vp = p.volprofile || {};
    var lv = [[D.exit.framework.ladder[0], '出場第一階'], [D.cycle.cm.k080_price, 'MVRV 0.80 線'], [D.cycle.cm.k075_price, 'MVRV 0.75 線'], [D.cycle.cm.price_ath_close, '歷史收盤新高'], [vp.va_high_outer, '近 20 日價值區上緣'], [vp.poc, '近 20 日成交最密集價'], [ma.sma20, '20 日均線'], [vp.va_low, '近 20 日價值區下緣'], [ma.sma50, '50 日均線'], [ma.sma200, '200 日均線（避險線）'], [D.cycle.cm.realized_price, '全網平均成本（實現價）']].filter(function (x) { return x[0]; }).sort(function (a, b) { return b[0] - a[0]; });
    var tbl = '<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:30%"><col style="width:24%"><col style="width:46%"></colgroup><thead><tr><th>價位</th><th class="num">距收盤</th><th>是什麼</th></tr></thead><tbody>' + lv.map(function (x) { var d = (x[0] / c - 1) * 100; return '<tr><td class="num" style="text-align:left">' + fmt.usd(x[0]) + '</td><td class="num" style="color:' + (d >= 0 ? 'var(--up)' : 'var(--down)') + '">' + fmt.pct(d) + '</td><td>' + x[1] + '</td></tr>'; }).join('') + '</tbody></table></div>';
    var ma2 = [['5 日', ma.sma5], ['20 日', ma.sma20], ['50 日', ma.sma50], ['111 日', ma.sma111], ['200 日', ma.sma200], ['350 日', ma.sma350]];
    var mat = '<div class="meters">' + ma2.map(function (m) { var d = (c / m[1] - 1) * 100; return meter(m[0] + '均線', fmt.usd(m[1]), 50 + Math.max(-50, Math.min(50, d * 2)), fmt.pct(d), d >= 0 ? '價格在上方' : '價格在下方', [50]); }).join('') + '</div><p class="note">中線＝均線位置；圓點越往右，價格越高於該均線。</p>';
    return readBar('market') + '<div class="kpis">' + kpi('收盤', fmt.usd(c), fmt.pct(p.bar.chg_pct, 2) + ' · 當日區間位置 ' + fmt.n(p.bar.close_pos_pct, 0) + '%') + kpi('ATR14（簡單平均）', fmt.usd(p.atr.atr14), '約 ' + fmt.n(p.atr.atr14 / c * 100, 1) + '% / 日') + kpi('實際波動 RV30', fmt.n(p.vol.rv30, 1) + '%', 'RV7 ' + fmt.n(p.vol.rv7, 1) + '% · RV90 ' + fmt.n(p.vol.rv90, 1) + '%') + kpi('Mayer 倍數', fmt.n(p.mayer.mayer, 2), '價格 ÷ 200 日均線') + kpi('Pi Cycle', fmt.n(p.pi_cycle, 2), '111 日 ÷ 2×350 日；≥1 為歷史頂部訊號', p.pi_cycle * 100) + '</div><div class="grid">' +
      panel('span-8', '近 20 天 K 線', 'Kraken 日線 · UTC', '<div class="chart" id="c-cd"></div>') +
      panel('span-4', '關鍵價位', '', tbl) +
      panel('span-6', '價格與均線', '', mat) +
      panel('span-6', '價格長期走勢', 'CoinMetrics · 對數刻度', '<div class="chart" id="c-long"></div>', '<div class="seg" id="lg-seg"><button aria-pressed="false" data-v="all">2012 起</button><button aria-pressed="true" data-v="4y">近 4 年</button></div>') + '</div>';
  };
  V.market.after = function () {
    var p = D.price, H = p.history || [], rng = '4y';
    mount($('#c-cd'), function (el) { candleChart(el, p.rows20 || [], [{ v: p.ma.sma20, label: '20 日 ' + fmt.k(p.ma.sma20), color: 'var(--s1)' }, { v: (p.volprofile || {}).va_high_outer, label: '價值區上緣', color: 'var(--flare)' }, { v: (p.volprofile || {}).poc, label: 'POC', color: 'var(--ink-3)' }]); });
    function drawLong(el) {
      var rows = rng === '4y' ? H.filter(function (r) { return r[0] >= H[H.length - 1][0] - 1461; }) : H;
      var mk = D.cycle.tops.concat(D.cycle.bottoms).map(function (t) { var x = dnOf(t[0]); return rows.length && x >= rows[0][0] ? { x: x, y: t[1], label: fmt.k(t[1]), color: t[1] > 50000 || D.cycle.tops.some(function (q) { return q[0] === t[0]; }) ? 'var(--flare)' : 'var(--orbit)', below: !D.cycle.tops.some(function (q) { return q[0] === t[0]; }), left: true } : null; }).filter(Boolean);
      lineChart(el, { log: true, series: [{ name: '價格', data: rows, color: 'var(--s1)', area: true }], marks: mk, vlines: D.cycle.halvings.map(function (h) { return { x: dnOf(h), label: '' }; }), tipFmt: fmt.usd, aria: '長期價格' });
    }
    mount($('#c-long'), drawLong);
    $('#lg-seg').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; rng = b.getAttribute('data-v'); this.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); drawLong($('#c-long')); });
  };

  V.deriv = function () {
    var dv = D.deriv, d = dv.deriv || {}, r = dv.rr25 || {}, o = dv.options || {};
    var big = (o.expiries || []).slice().sort(function (a, b) { return b.oi - a.oi; })[0] || {};
    return readBar('deriv') + '<div class="kpis">' + kpi('DVOL', fmt.n((dv.dvol || {}).value, 1), '一年第 ' + fmt.n((dv.dvol || {}).pct_1y, 0) + ' 百分位', (dv.dvol || {}).pct_1y) + kpi('IV − RV30（同源）', fmt.n((dv.samesource || {}).iv_minus_rv30, 2), '負值＝隱含波動比實際便宜') + kpi('永續資金費率', fmt.pct(d.funding_ann, 1), '年化 · 期貨基差中位 ' + fmt.n(d.basis_median, 1) + '%') + kpi('25Δ 風險逆轉', fmt.n(r.rr, 2), r.expiry + ' · ATM ' + fmt.n(r.atm_iv, 1) + '%') + kpi('選擇權未平倉', fmt.n(o.total_oi) + ' 顆', '最大到期 ' + (big.expiry || '—') + '（' + fmt.n(big.share, 0) + '%）') + '</div><div class="grid">' +
      panel('span-8', '隱含波動 vs 實際波動', 'Deribit DVOL · Kraken RV30 · 近一年', legend([['DVOL', 'var(--s1)'], ['RV30', 'var(--s2)']]) + '<div class="chart" id="c-vol"></div>') +
      panel('span-4', '期貨基差曲線', '年化 % · 排除 7 天內到期', '<div class="chart" id="c-basis"></div><p class="note">資金費率年化 ' + fmt.pct(d.funding_ann, 1) + '；永續 OI ' + fmt.usd(d.perp_oi_usd_m) + 'M。</p>') +
      panel('span-6', '各到期未平倉', '買權 / 賣權（顆）', legend([['買權', 'var(--s4)'], ['賣權', 'var(--s3)']]) + '<div class="chart" id="c-oi"></div>') +
      panel('span-6', '最大到期的履約價分布', ((dv.viz || {}).options || {}).strikes ? dv.viz.options.strikes.expiry + ' · Max Pain ' + fmt.k(dv.viz.options.strikes.maxpain) : '', '<div id="c-strike"></div>') + '</div>';
  };
  V.deriv.after = function () {
    var v = D.deriv.viz || {};
    mount($('#c-vol'), function (el) { var rows = (v.vol || {}).rows || []; lineChart(el, { series: [{ name: 'DVOL', data: rows.map(function (r) { return [r[0], r[1]]; }), color: 'var(--s1)' }, { name: 'RV30', data: rows.map(function (r) { return [r[0], r[2]]; }), color: 'var(--s2)' }], yFmt: function (x) { return x.toFixed(0); }, tipFmt: function (x) { return x.toFixed(1) + '%'; }, aria: '波動率' }); });
    mount($('#c-basis'), function (el) { var cv = (v.basis || {}).curve || []; lineChart(el, { h: 200, xType: 'num', series: [{ name: '年化基差', data: cv, color: 'var(--s4)', area: true }], xticks: cv.filter(function (p, i) { return i % 2 === 0; }).map(function (p) { return [p[0], Math.round(p[0]) + 'd']; }), xTipFmt: function (x) { return Math.round(x) + ' 天到期'; }, yFmt: function (x) { return x.toFixed(1) + '%'; }, tipFmt: function (x) { return x.toFixed(2) + '%'; }, y0: 0, aria: '基差曲線' }); });
    mount($('#c-oi'), function (el) {
      var ex = ((v.options || {}).expiries || []), W = Math.max(280, el.clientWidth), Ht = 230, ML = 8, MR = 52, MT = 10, MB = 26, pw = W - ML - MR, ph = Ht - MT - MB;
      var mx = Math.max.apply(null, ex.map(function (e) { return e[2] + e[3]; })) || 1, st = niceStep(mx, 4), top = Math.ceil(mx / st) * st, bw = pw / ex.length, s = '';
      var Y = function (q) { return MT + (1 - q / top) * ph; };
      for (var t = 0; t <= top; t += st) s += '<line class="' + (t ? 'gl' : 'base') + '" x1="' + ML + '" x2="' + (ML + pw) + '" y1="' + Y(t).toFixed(1) + '" y2="' + Y(t).toFixed(1) + '"/><text class="ax" x="' + (ML + pw + 8) + '" y="' + (Y(t) + 3.5).toFixed(1) + '">' + fmt.k(t) + '</text>';
      ex.forEach(function (e, i) { var x = ML + i * bw + 3, w = bw - 6, yc = Y(e[2]), yp = Y(e[2] + e[3]); s += '<g class="oi" data-i="' + i + '"><rect x="' + x.toFixed(1) + '" y="' + yc.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + (MT + ph - yc).toFixed(1) + '" rx="3" fill="var(--s4)"/><rect x="' + x.toFixed(1) + '" y="' + yp.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + Math.max(0, yc - yp - 2).toFixed(1) + '" rx="3" fill="var(--s3)"/></g><text class="ax" x="' + (x + w / 2).toFixed(1) + '" y="' + (Ht - 8) + '" text-anchor="middle">' + fmt.md(e[0]) + '</text>'; });
      el.innerHTML = svgEl(W, Ht, s, '各到期未平倉');
      el.querySelectorAll('.oi').forEach(function (g) { var e = ex[+g.getAttribute('data-i')]; g.addEventListener('pointermove', function (ev) { showTip(ev.clientX, ev.clientY, '<div class="t">' + e[0] + ' · ' + e[1] + ' 天</div><div class="r"><i style="background:var(--s4)"></i><span>買權</span><b>' + fmt.n(e[2]) + '</b></div><div class="r"><i style="background:var(--s3)"></i><span>賣權</span><b>' + fmt.n(e[3]) + '</b></div><div class="r"><i></i><span>Max Pain</span><b>' + fmt.k(e[4]) + '</b></div>'); }); g.addEventListener('pointerleave', hideTip); });
    });
    var sk0 = ((v.options || {}).strikes || {}).rows || [], el = $('#c-strike'), cc = D.price.bar.c, bk = {};
    /* 只看收盤 ±30%，依數量自動分箱到 26 列以內，避免出現捲軸 */
    sk0 = sk0.filter(function (r) { return r[0] >= cc * 0.7 && r[0] <= cc * 1.3; });
    var bs = 1000; while (sk0.length && (sk0[sk0.length - 1][0] - sk0[0][0]) / bs > 26) bs = bs === 1000 ? 2500 : bs * 2;
    sk0.forEach(function (r) { var k = Math.floor(r[0] / bs) * bs; if (!bk[k]) bk[k] = [k, 0, 0]; bk[k][1] += r[1]; bk[k][2] += r[2]; });
    var sk = Object.keys(bk).map(function (k) { return bk[k]; }).sort(function (a, b) { return a[0] - b[0]; });
    if (el) { var mx = Math.max.apply(null, sk.map(function (r) { return Math.max(r[1], r[2]); })) || 1, c = D.price.bar.c;
      el.innerHTML = '<div class="ladder dense">' + sk.slice().reverse().map(function (r) { var near = c >= r[0] && c < r[0] + bs; return '<div class="row' + (near ? ' cur' : '') + '" style="grid-template-columns:minmax(0,1fr) 64px minmax(0,1fr)"><span class="b" style="direction:rtl"><i style="width:' + (r[2] / mx * 100).toFixed(1) + '%;background:var(--s3);left:auto;right:0"></i></span><span class="p" style="text-align:center">' + fmt.k(r[0]) + '</span><span class="b"><i style="width:' + (r[1] / mx * 100).toFixed(1) + '%;background:var(--s4)"></i></span></div>'; }).join('') + '</div><div class="legend" style="margin-top:8px;justify-content:space-between"><span style="color:var(--s3)"><i></i><b style="color:var(--ink-2);font-weight:400">← 賣權</b></span><span style="color:var(--s4)"><b style="color:var(--ink-2);font-weight:400">買權 →</b><i></i></span></div>'; }
  };

  V.flows = function () {
    var fr = D.flows.fred || {}, etf = D.flows.etf || [], full = etf.filter(function (r) { return !r.partial; });
    var last = full[full.length - 1] || {}, s7 = full.slice(-7).reduce(function (a, r) { return a + r.musd; }, 0), p7 = full.slice(-14, -7).reduce(function (a, r) { return a + r.musd; }, 0);
    var nq = fr.NASDAQCOM || {}, dx = fr.DTWEXBGS || {}, tn = fr.DGS10 || {}, rr = D.flows.dfii10 || {};
    return readBar('flows') + '<div class="kpis">' + kpi('最近完整日 ETF', (last.musd >= 0 ? '+' : '') + fmt.n(last.musd, 1) + 'M', fmt.md(last.d) + ' · 美元') + kpi('近 7 個完整日', (s7 >= 0 ? '+' : '') + fmt.n(s7, 0) + 'M', '前 7 日 ' + (p7 >= 0 ? '+' : '') + fmt.n(p7, 0) + 'M') + kpi('BTC–那斯達克 30 日相關', fmt.n(nq.corr30, 2), fmt.md(nq.last_date) + ' · 高於 0.5 代表同漲同跌', (nq.corr30 + 1) * 50) + kpi('BTC–美元 30 日相關', fmt.n(dx.corr30, 2), 'FRED 廣義美元指數', (dx.corr30 + 1) * 50) + kpi('10 年期實質利率', fmt.n(rr.value, 2) + '%', '20 日 ' + (rr.chg_20obs_bp >= 0 ? '+' : '') + rr.chg_20obs_bp + 'bp · 名目 ' + fmt.n(tn.last, 2) + '%') + '</div><div class="grid">' +
      panel('span-12', '現貨 ETF 每日淨流量', 'The Block（與 Farside 同口徑）· 百萬美元 · 淡色＝暫定或尚未完整', '<div class="chart" id="c-etf"></div>') + '</div>';
  };
  V.flows.after = function () {
    var etf = D.flows.etf || [];
    mount($('#c-etf'), function (el) { barChart(el, { h: 260, data: etf.map(function (r) { return [fmt.md(r.d), r.musd, '<div class="t">' + r.d + (r.partial ? (r.src ? '（暫定）' : '（部分回報）') : '') + '</div><div class="r"><i style="background:' + (r.musd >= 0 ? 'var(--up)' : 'var(--down)') + '"></i><span>淨流量</span><b>' + (r.musd >= 0 ? '+' : '') + fmt.n(r.musd, 1) + 'M</b></div>' + (r.src ? '<div class="t" style="font-weight:400;max-width:240px;white-space:normal">' + esc(r.src) + '</div>' : ''), r.partial]; }), yFmt: function (v) { return v + 'M'; }, aria: 'ETF 淨流量' }); });
  };

  V.onchain = function () {
    var oc = D.onchain, m = oc.metrics || {}, tr = oc.top_radar || {}, ch = D.chips, fl = ch.flow || {}, u = ch.urpd || {}, mi = oc.mining || {}, ex = oc.exchange || {};
    var rows = [
      ['MVRV Z', m['mvrv-zscore'], '估值；<0 底部、>3.5 頂部'], ['NUPL', m['nupl'], '淨未實現損益'], ['Puell', m['puell-multiple'], '礦工收入倍數'],
      ['SOPR', m['sopr'], '>1 平均獲利出場'], ['aSOPR', m['asopr'], '排除一小時內轉手'], ['STH-SOPR', m['sth-sopr'], '短期持有者'], ['LTH-SOPR', m['lth-sopr'], '長期持有者'],
      ['非流動性供給', m['illiquid-supply'], '長期不動的幣'], ['高流動性供給', m['highly-liquid-supply'], '浮動籌碼']
    ].filter(function (r) { return r[1]; });
    var t = '<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:22%"><col style="width:20%"><col style="width:28%"><col style="width:30%"></colgroup><thead><tr><th>指標</th><th class="num">讀值</th><th>四年百分位</th><th>說明</th></tr></thead><tbody>' + rows.map(function (r) { var v = r[1], big = Math.abs(v.value) > 1e5; return '<tr><td>' + r[0] + '<div class="note">' + fmt.md(v.date) + '</div></td><td class="num">' + (big ? fmt.n(v.value / 1e6, 2) + 'M' : fmt.n(v.value, 3)) + '</td><td>' + (v.pct_4y == null ? '—' : '<div class="pct"><i><b class="' + (v.pct_4y >= 80 ? 'hot' : '') + '" style="width:' + v.pct_4y + '%"></b></i><span class="num">' + fmt.n(v.pct_4y, 0) + '</span></div>') + '</td><td style="color:var(--ink-2)">' + r[2] + '</td></tr>'; }).join('') + '</tbody></table></div>';
    var radar = [['LTH MVRV Z', tr['lth-mvrv-zscore'], 2], ['獲利供給 %', tr['supply-in-profit-pct'], 1], ['實現市值成長率', tr['realized-cap-growth-rate'], 2], ['LTH 30 日淨部位', tr['lth-net-position-change-30d-btc'], 0]].filter(function (r) { return r[1]; });
    var rt = '<div class="tbl-wrap"><table class="tbl"><colgroup><col style="width:34%"><col style="width:22%"><col style="width:22%"><col style="width:22%"></colgroup><thead><tr><th>頂部雷達</th><th class="num">現在</th><th class="num">2025 頂部</th><th>本輪位置</th></tr></thead><tbody>' + radar.map(function (r) { var v = r[1]; return '<tr><td>' + r[0] + '</td><td class="num">' + fmt.n(v.value, r[2]) + '</td><td class="num">' + fmt.n(v.extreme_near_2025_top, r[2]) + '</td><td><div class="pct"><i><b style="width:' + v.pct_since_2022_11 + '%"></b></i><span class="num">' + fmt.n(v.pct_since_2022_11, 0) + '</span></div></td></tr>'; }).join('') + '</tbody></table></div>';
    return readBar('onchain') + '<div class="kpis">' + kpi('短期持有者獲利比例', fmt.n((fl.sth_in_profit_pct || {}).value, 1) + '%', '7 天前 ' + fmt.n((fl.sth_in_profit_pct || {}).d7, 1) + '%', (fl.sth_in_profit_pct || {}).value) + kpi('短期持有者成本', fmt.usd((fl.sth_vs_tmm || {}).sth_cost), '真實市場均價 ' + fmt.usd((fl.sth_vs_tmm || {}).tmm)) + kpi('交易所供給', fmt.n(ex.exchange_supply_share_pct, 2) + '%', '7 日 ' + fmt.pct(ex.exchange_supply_chg7_pct, 2) + ' · 90 日 ' + fmt.pct(ex.exchange_supply_chg90_pct, 2)) + kpi('算力 7 日均', fmt.n(mi.hash7, 0) + ' EH/s', '週 ' + fmt.pct(mi.wk_chg_pct, 1) + ' · hashprice $' + fmt.n(mi.hashprice, 1)) + kpi('下次難度調整', fmt.pct(mi.diff_next_pct, 1), fmt.md(mi.retarget) + ' · 進度 ' + fmt.n(mi.diff_progress, 0) + '%', mi.diff_progress) + '</div><div class="grid">' +
      panel('span-5', '籌碼分布（URPD）', fmt.md(u.date) + ' · 每 2,000 美元一格', '<p class="say">現價這一格堆了 <b>' + fmt.n(u.cur_btc / 1e4, 0) + ' 萬顆</b>（' + fmt.n(u.cur_pct, 1) + '%）；下方最近大堆 ' + (u.below_cluster ? fmt.k(u.below_cluster.range[0]) + '–' + fmt.k(u.below_cluster.range[1]) : '—') + '。</p><div id="c-urpd"></div>') +
      panel('span-7', '短期持有者：成本 vs 價格', 'bitcoin-data · 近 2 年', legend([['短期持有者成本', 'var(--s2)'], ['真實市場均價', 'var(--s3)']]) + '<div class="chart" id="c-cost"></div>' + '<div class="panel-h" style="margin-top:6px"><h2>短期持有者獲利比例</h2><span class="src">2025 頂部 ' + fmt.n((ch.viz || {}).top_vals ? ch.viz.top_vals.profit : null, 1) + '%</span></div><div class="chart" id="c-profit"></div>') +
      panel('span-7', '鏈上指標', 'bitcoin-data.com', t) + panel('span-5', '頂部雷達', '2022/11 起本輪百分位', rt) + '</div>';
  };
  V.onchain.after = function () {
    var v = D.chips.viz || {}, u = v.urpd || {}, c = D.price.bar.c, el = $('#c-urpd');
    if (el && u.band) {
      var pv = {}; ((u.prev7 || {}).band || []).forEach(function (b) { pv[b[0]] = b[1]; });
      var rows = u.band.filter(function (b) { return b[0] >= c * 0.62 && b[0] <= c * 1.4; }).slice().reverse().map(function (b) { var cur = c >= b[0] && c < b[0] + (u.width || 2000); return { label: fmt.k(b[0]), v: b[1], color: cur ? 'var(--flare)' : 'var(--s1)', cls: cur ? 'cur' : '', right: fmt.n(b[1] / 1e4, 1) + '萬', prev: pv[b[0]], tip: '<div class="t">' + fmt.usd(b[0]) + '–' + fmt.usd(b[0] + (u.width || 2000)) + '</div><div class="r"><i style="background:var(--s1)"></i><span>籌碼</span><b>' + fmt.n(b[1]) + ' 顆</b></div>' + (pv[b[0]] != null ? '<div class="r"><i></i><span>7 天前</span><b>' + fmt.n(pv[b[0]]) + '</b></div>' : '') }; });
      el.innerHTML = ladderHtml(rows, { dense: true }); bindLadder(el, rows);
    }
    mount($('#c-cost'), function (el) { var r = v.cost || []; lineChart(el, { h: 220, series: [{ name: '短期持有者成本', data: r.map(function (x) { return [x[0], x[2]]; }), color: 'var(--s2)' }, { name: '真實市場均價', data: r.map(function (x) { return [x[0], x[3]]; }), color: 'var(--s3)' }], refs: [{ y: c, color: 'var(--ink-3)', label: '收盤 ' + fmt.k(c), below: true }], tipFmt: fmt.usd, aria: '成本線' }); });
    mount($('#c-profit'), function (el) { lineChart(el, { h: 170, series: [{ name: '獲利比例', data: v.profit || [], color: 'var(--s4)', area: true }], y0: 0, y1: 100, yFmt: function (x) { return x + '%'; }, tipFmt: function (x) { return x.toFixed(1) + '%'; }, aria: '短期持有者獲利比例' }); });
  };

  V.book = function () {
    var o = D.orderbook; if (!o) return '<p class="err">本日未取得掛單簿資料。</p>';
    var w = o.walls || {}, rd = o.rounds || {}, t = o.totals || {};
    var walls = function (arr, col) { return (arr || []).slice(0, 5).map(function (x) { return '<div class="event"><span class="d">' + fmt.usd(x[0]) + '</span><span style="color:var(--ink-2)">' + esc(x[2]) + ' 最多</span><span class="num" style="color:' + col + '">$' + fmt.n(x[1], 1) + 'M</span></div>'; }).join(''); };
    return readBar('book') + '<div class="kpis">' + kpi('快照中間價', fmt.usd(o.mid), (o.ts || '').replace('T', ' ').replace('+00:00', ' UTC')) + kpi('±15% 買單合計', '$' + fmt.n(t.wide_bid, 0) + 'M', '現貨 $' + fmt.n(t.wide_bid_spot, 0) + 'M') + kpi('±15% 賣單合計', '$' + fmt.n(t.wide_ask, 0) + 'M', '現貨 $' + fmt.n(t.wide_ask_spot, 0) + 'M') + kpi('買賣比', fmt.n(t.wide_bid / t.wide_ask, 2), '>1 下方承接較厚') + '</div><div class="grid">' +
      panel('span-8', '全景：每 1,000 美元一格', '7 個整本可得的場所 · ±15%', legend([['買單', 'var(--up)'], ['賣單', 'var(--down)']]) + '<div id="c-book"></div>') +
      panel('span-4', '最大的牆', '', '<div class="panel-h"><h2 style="color:var(--down)">上方賣牆</h2></div><div class="events">' + walls(w.ask, 'var(--down)') + '</div><div class="panel-h" style="margin-top:8px"><h2 style="color:var(--up)">下方買牆</h2></div><div class="events">' + walls(w.bid, 'var(--up)') + '</div>' +
        '<div class="panel-h" style="margin-top:8px"><h2>整數關卡</h2></div><div class="events">' + Object.keys(rd).sort().reverse().map(function (k) { var r = rd[k]; return '<div class="event"><span class="d">' + fmt.usd(+k) + '</span><span style="color:var(--ink-2)">' + (r.side === 'a' ? '賣' : '買') + '方第 ' + r.rank + '／' + r.of + ' 名</span><span class="num">$' + fmt.n(r.musd, 1) + 'M</span></div>'; }).join('') + '</div><p class="note">掛單可隨時撤；Binance 期貨與 Bybit 讀不到，永續部分偏低估。</p>') + '</div>';
  };
  V.book.after = function () {
    var o = D.orderbook, el = $('#c-book'); if (!o || !el) return;
    var ven = o.wide.venues, lab = function (k) { return (o.meta[k] || {}).label || k; };
    var rows = o.wide.rows.map(function (r) { var tot = r[2].reduce(function (a, b) { return a + b; }, 0); return { label: fmt.k(r[0]) + (r[1] === 'a' ? ' ▲' : ' ▼'), v: tot, color: r[1] === 'a' ? 'var(--down)' : 'var(--up)', cls: r[0] === Math.floor(o.mid / 1000) * 1000 ? 'mid' : '', right: '$' + fmt.n(tot, 1) + 'M', tip: '<div class="t">' + fmt.usd(r[0]) + ' · ' + (r[1] === 'a' ? '賣單' : '買單') + '</div>' + r[2].map(function (v, i) { return v >= 0.5 ? '<div class="r"><i style="background:' + (r[1] === 'a' ? 'var(--down)' : 'var(--up)') + '"></i><span>' + esc(lab(ven[i])) + '</span><b>$' + fmt.n(v, 1) + 'M</b></div>' : ''; }).join('') }; });
    el.innerHTML = ladderHtml(rows, { dense: true }); bindLadder(el, rows);
  };

  V.exit = function () {
    var F = D.exit.framework, S = D.exit.status, c = S.close;
    return readBar('exit') + '<div class="grid">' +
      panel('span-12', '出場模擬器', esc(F.unit), '<div class="sim"><div class="sim-ctrl"><label for="sim-px">拖動看看：如果收盤到這個價位，框架會賣出多少？</label><span class="big" id="sim-v">' + fmt.usd(c) + '</span><input type="range" id="sim-px" min="60000" max="240000" step="1000" value="' + Math.round(c / 1000) * 1000 + '"><div class="legend"><span>60K</span><span style="margin-left:auto">240K</span></div><div class="stair" id="sim-stair"></div></div><div class="donut-wrap" id="sim-donut"></div></div>') +
      panel('span-6', '鏈上觸發', 'MVRV ÷ 前一輪高點', '<div class="rules">' + F.onchain.map(function (r) { var run = r.id === 'p20a' ? S.p20_run_075 : r.id === 'p20b' ? S.p20_run_080 : null; return '<div class="rule"><span class="t">' + (r.k ? '比值 ≥ ' + r.k : '新高背離') + '</span><span class="d">' + esc(r.rule) + '</span><span class="chip">' + (run != null ? run + ' / 5 天' : '未啟用') + '</span></div>'; }).join('') + '</div><p class="note">現在比值 ' + fmt.n(S.p20_ratio, 3) + '；0.75 約對應 ' + fmt.usd(S.k075_price) + '、0.80 約 ' + fmt.usd(S.k080_price) + '（隨實現價每天移動）。</p>') +
      panel('span-6', '其他規則', '', '<div class="rules"><div class="rule"><span class="t">200 日均線避險</span><span class="d">' + esc(F.hedge.rule) + '</span><span class="chip">' + S.below_sma200_run + ' / 5 天</span></div><div class="rule"><span class="t">訊號加速</span><span class="d">' + esc(F.accelerate) + '</span><span class="chip">' + ['mvrv_z', 'nupl', 'puell'].map(function (k) { return fmt.n((S.p6 || {})[k], 0); }).join('／') + '</span></div><div class="rule"><span class="t">時間停損</span><span class="d">' + esc(F.time_stop) + '</span><span class="chip">2029/10 起</span></div></div><p class="note">框架是本站對「週期頂部分批出場」的建議做法，只是參考，不是投資建議；每個人的部位與需求不同。</p>') + '</div>';
  };
  V.exit.after = function () {
    var F = D.exit.framework, inp = $('#sim-px'), S = D.exit.status;
    function upd() {
      var px = +inp.value, hit = F.ladder.filter(function (x) { return px >= x; }).length, sold = hit * F.per_step_pct;
      $('#sim-v').textContent = fmt.usd(px);
      $('#sim-stair').innerHTML = F.ladder.slice().reverse().map(function (x, i) { var on = px >= x; return '<div class="step' + (on ? ' on' : '') + '"><span class="dot"></span><span class="p">' + fmt.usd(x) + '</span><span class="d">第 ' + (F.ladder.length - i) + ' 階 · 距今 ' + fmt.pct((x / S.close - 1) * 100, 0) + '</span><span class="q">' + (on ? '賣 ' : '') + F.per_step_pct + '%</span></div>'; }).join('');
      var R = 78, C = 2 * Math.PI * R, frac = sold / 100;
      $('#sim-donut').innerHTML = '<svg viewBox="0 0 200 200" role="img" aria-label="已賣出比例"><circle cx="100" cy="100" r="' + R + '" fill="none" stroke="var(--deck-3)" stroke-width="16"/><circle cx="100" cy="100" r="' + R + '" fill="none" stroke="var(--flare)" stroke-width="16" stroke-dasharray="' + (C * frac).toFixed(1) + ' ' + C.toFixed(1) + '" transform="rotate(-90 100 100)" style="transition:stroke-dasharray .4s var(--ease)"/><text x="100" y="98" text-anchor="middle" style="font-family:var(--f-mono);font-size:34px" fill="var(--ink)">' + sold + '%</text><text x="100" y="124" text-anchor="middle" style="font-size:12px" fill="var(--ink-3)">已分批賣出</text></svg><span class="note">價格階梯單獨計算；鏈上觸發會提前賣出、從最高的階往下註銷，總量不變。</span>';
    }
    inp.addEventListener('input', upd); upd();
  };

  V.method = function () {
    return '<div class="grid">' + panel('span-7', '這是什麼', '', '<div class="prose"><p>破曉（Daybreak）是每天清晨的第一份比特幣簡報：先告訴你今天發生了什麼、為什麼重要，再用數據說明市場在週期裡的位置，以及離分批出場還有多遠。</p><p>每天兩段更新：台北 08:20（UTC 00:20）資料管線自動抓取 Kraken、Deribit、CoinMetrics、bitcoin-data、mempool.space、FRED、13 個交易所掛單簿與 Tidemark，算出所有指標；之後由 Claude 查證當天新聞、讀數據，寫成頭條、今日要聞解讀與各版的「今日判讀」。數字全部來自管線，判讀只解釋數字，不改數字。</p>' +
      '<h3>原則</h3><p>先給結論再給證據。寧可標示「本日未取得」，也不推估或沿用舊數字。不同資料商的數字不相減。分數一律附樣本數，樣本少於 30 不下結論。</p><h3>限制</h3><p>週期模型只有 3–4 輪歷史，所有「遞減」推論都假設趨勢延續。冪律擬合線會隨新資料下修。掛單隨時可撤。短線預測不連動出場規則。bitcoin-data 免費額度有限，部分變化較慢的鏈上指標每 2 天更新一次，以資料日期標示。</p>' +
      '<h3>免責聲明</h3><p>本站內容僅供研究與教育參考，不構成投資建議。加密資產波動極大，請依自身情況判斷並自負風險。</p></div>') +
      panel('span-5', '資料來源', '', '<div class="events">' + [['價格、均線、ATR', 'Kraken 日線（UTC）'], ['波動率、基差、選擇權', 'Deribit 公開 API'], ['MVRV、交易所供給、冪律', 'CoinMetrics Community'], ['SOPR、NUPL、籌碼', 'bitcoin-data.com'], ['算力、難度', 'mempool.space'], ['相關係數、利率', 'FRED'], ['ETF 流量', 'The Block（與 Farside 同口徑）'], ['掛單簿', 'Coinbase、Bitstamp、Gemini、Bitfinex、Kraken、Binance、OKX、Gate、MEXC、Deribit、Hyperliquid'], ['綜合訊號', 'Tidemark（north7.github.io）']].map(function (r) { return '<div class="event" style="grid-template-columns:minmax(0,1fr) minmax(0,1.2fr)"><span>' + r[0] + '</span><span style="color:var(--ink-2)">' + r[1] + '</span></div>'; }).join('') + '</div><p class="note">資料日 ' + D.meta.bar_date + ' · 管線產出 ' + (D.meta.generated_utc || '').replace('T', ' ').slice(0, 16) + ' UTC · 結論 ' + (N ? (N.written_utc || '').replace('T', ' ').slice(0, 16) + ' UTC' : '—') + '</p>') + '</div>';
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
      var mh = r[0] === 'overview' ? '' : '<header class="mod-h"><span class="idx">' + ('0' + (i + 1)).slice(-2) + '</span><h1>' + r[1] + '</h1><p>' + r[2] + ' · ' + fmt.md(D.meta.bar_date) + ' 收盤版</p></header>';
      var body; try { body = V[r[0]](); } catch (e) { body = '<p class="err">這個模組載入失敗：' + esc(e.message) + '</p>'; console.error(e); }
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
    document.title = (id === 'overview' ? '破曉 Daybreak' : r[1] + '｜破曉 Daybreak');
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
    var tt = $('#theme');
    function setTheme(v) { if (v === 'dark') document.documentElement.setAttribute('data-theme', 'dark'); else document.documentElement.removeAttribute('data-theme'); tt.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x.getAttribute('data-t') === v); }); }
    tt.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; var v = b.getAttribute('data-t'); setTheme(v); try { localStorage.setItem('daybreak.theme', v); } catch (er) {} mounted.forEach(function (el) { el._draw && el._draw(el); }); });
    try { setTheme(localStorage.getItem('daybreak.theme') === 'dark' ? 'dark' : 'light'); } catch (e) {}
    var pad = function (x) { return ('0' + x).slice(-2); };
    function tick() { var t = new Date(); var nx = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate(), 0, 30)); if (nx <= t) nx = new Date(+nx + 864e5); var d = Math.floor((nx - t) / 1000); $('#nxt').textContent = 'T−' + pad(Math.floor(d / 3600)) + ':' + pad(Math.floor(d % 3600 / 60)) + ':' + pad(d % 60); }
    tick(); setInterval(tick, 1000);
    var fs = $('#fs'); fs.addEventListener('click', function () { var d = document; try { if (d.fullscreenElement) d.exitFullscreen(); else d.documentElement.requestFullscreen().catch(function () {}); } catch (e) {} });
    var c = D.price.bar;
    $('#tk-px').textContent = fmt.usd(c.c);
    $('#tk-chg').textContent = fmt.pct(c.chg_pct, 2); $('#tk-chg').className = 'chip ' + (c.chg_pct >= 0 ? 'up' : 'down');
    $('#tk-stance').innerHTML = '<i></i>' + esc(N ? N.stance.label : '—');
    $('#tk-asof').textContent = fmt.md(D.meta.bar_date) + ' 收盤 · UTC';
    $('#ed-date').textContent = D.meta.bar_date + (N ? ' · 第 ' + N.edition + ' 期' : '');
    $('#ed-gen').textContent = '資料 ' + (D.meta.generated_utc || '').slice(11, 16) + ' UTC 產出';
  }

  function load(u) { return fetch(u, { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); }); }
  Promise.all([load('data/latest.json'), load('data/notes.json').catch(function () { return null; })]).then(function (a) {
    D = a[0]; N = a[1] && a[1].date === D.meta.bar_date ? a[1] : (a[1] ? Object.assign({}, a[1], { stale: true }) : null);
    shell();
    renderAll();
    var start = location.hash.slice(1);
    if (start && start !== 'overview' && $('#pg-' + start)) {
      go(start);   // 字型載入後版面會變高，載完再對齊一次（使用者已自行捲動就不動）
      var y0 = window.scrollY; if (document.fonts) document.fonts.ready.then(function () { if (Math.abs(window.scrollY - y0) < 2) go(start); });
    } else { window.scrollTo(0, 0); activate(ROUTES[0][0]); }
  }).catch(function (e) { $('#view').innerHTML = '<p class="err">資料載入失敗：' + esc(e.message) + '。請稍後重新整理。</p>'; });
})();
