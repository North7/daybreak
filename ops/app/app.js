/* 破曉運營台（2026-11-08 重做）：發文與回覆合成一個工具、兩個分頁，所有卡片同一套結構。
   今天發文：日報（data/x_post.json）、推薦圖表（data/picks.json＋data/picks/index.json）、快訊（data/flash.json）、長貼文（data/longposts.json），照建議時間排。
   回覆：data/replies.json；原文點開時才即時讀 api.fxtwitter.com。
   卡片：標頭（時間／類型／標題／狀態）→ 點開：說明 → 中文／English 或 回覆／引用 切換 → 文字＋字數 → 配圖 → 動作（主要「發到 X」，其次複製文字、存圖）→ 標記已發。
   已發／已回只記在這台裝置（localStorage daybreak.done.v2：{鍵: 台北日期}；讀得到舊的 daybreak.longdone、daybreak-replied-<日期>）。
   標記完成後自動收起、打開下一則。資料格式沒變，排程任務不用改。 */
(function () {
  'use strict';
  var ROOT = '../../', T = Date.now(), MOBILE = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
  var URL_RE = /https?:\/\/\S+/g;
  var FILES = {}, TEXT = {}, CARDS = {};   // FILES／TEXT 的鍵是「卡片鍵|語言或模式」

  // ---------- 小工具 ----------
  function weight(t) {   // 與 pipeline/x_len.py 相同：中日韓全形與 emoji 2、其他 1、網址 23
    var n = (t.match(URL_RE) || []).length * 23; t = t.replace(URL_RE, '');
    for (var ch of t) n += /[ᄀ-ᅟ⺀-꓏가-힣豈-﫿︰-﹏＀-｠￠-￦　-〿\u{1F300}-\u{1FAFF}\u{20000}-\u{3FFFD}]/u.test(ch) ? 2 : 1;
    return n;
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function tpe(d) { return new Date(d).toLocaleDateString('sv-SE', { timeZone: 'Asia/Taipei' }); }
  function hm(d) { return new Date(d).toLocaleTimeString('en-GB', { timeZone: 'Asia/Taipei', hour: '2-digit', minute: '2-digit' }); }
  function md(s) { return s ? s.slice(5).replace('-', '/') : ''; }
  function at(date, hhmm) { return new Date(date + 'T' + hhmm + ':00+08:00'); }
  var TODAY = tpe(Date.now());
  function img(path) { return ROOT + String(path).replace(/^https:\/\/north7\.github\.io\/daybreak\//, '') + '?t=' + T; }
  function getJSON(u) { return fetch(ROOT + u + '?t=' + T).then(function (r) { if (!r.ok) throw r.status; return r.json(); }); }
  function copy(t) { try { return navigator.clipboard.writeText(t); } catch (e) { return Promise.reject(e); } }
  var toastT;
  function toast(msg) { var el = document.getElementById('toast'); el.textContent = msg; el.classList.add('show'); clearTimeout(toastT); toastT = setTimeout(function () { el.classList.remove('show'); }, 2200); }
  function fans(n) { return n >= 10000 ? (n / 10000).toFixed(1).replace(/\.0$/, '') + ' 萬粉' : Number(n || 0).toLocaleString() + ' 粉'; }
  function ago(iso) { var m = (Date.now() - new Date(iso).getTime()) / 60000; return m < 60 ? Math.max(1, Math.round(m)) + ' 分鐘前' : m < 2880 ? Math.round(m / 60) + ' 小時前' : Math.round(m / 1440) + ' 天前'; }
  function num(n) { return n >= 10000 ? (n / 1000).toFixed(1).replace(/\.0$/, '') + 'K' : Number(n || 0).toLocaleString(); }
  function splitLink(t) {   // 2026-11-06：正文帶連結曝光少約四成，連結那一行拆出來，發完貼在自己的第一則回覆
    var keep = [], link = [];
    String(t || '').split('\n').forEach(function (l) { (/https?:\/\/\S+/.test(l) ? link : keep).push(l); });
    return [keep.join('\n').replace(/\n{3,}/g, '\n\n').trim(), link.join('\n').trim()];
  }
  function prefetch(k, urls, names) {   // 分享選單要在同一次點擊內叫出，圖要先抓好
    if (!urls.length) return;
    Promise.all(urls.map(function (u, i) { return fetch(u).then(function (r) { return r.blob(); }).then(function (b) { return new File([b], names[i], { type: 'image/png' }); }); }))
      .then(function (fs) { FILES[k] = fs; }).catch(function () {});
  }

  // ---------- 已發／已回（這台裝置） ----------
  var DK = 'daybreak.done.v2', DONE = {};
  try { DONE = JSON.parse(localStorage.getItem(DK) || '{}'); } catch (e) {}
  try {   // 舊版的紀錄併進來
    var old = JSON.parse(localStorage.getItem('daybreak.longdone') || '{}');
    Object.keys(old).forEach(function (id) { if (!DONE['long:' + id]) DONE['long:' + id] = old[id]; });
    Object.keys(localStorage).forEach(function (k) {
      var m = /^daybreak-replied-(\d{4}-\d\d-\d\d)$/.exec(k); if (!m) return;
      JSON.parse(localStorage.getItem(k) || '[]').forEach(function (id) { if (!DONE['reply:' + id]) DONE['reply:' + id] = m[1]; });
    });
  } catch (e) {}
  function saveDone() { try { localStorage.setItem(DK, JSON.stringify(DONE)); } catch (e) {} }
  var POSTED = {};   // 資料裡的 posted（台北日期）：Claude 記錄已發出的，每台裝置都算已發
  function isDone(k) { return !!DONE[k] || !!POSTED[k]; }
  // 2026-11-08：「不發／不回」標記（這台裝置，daybreak.skip.v2：{鍵: 台北日期}）；和已發互斥
  var SK = 'daybreak.skip.v2', SKIP = {};
  try { SKIP = JSON.parse(localStorage.getItem(SK) || '{}'); } catch (e) {}
  function saveSkip() { try { localStorage.setItem(SK, JSON.stringify(SKIP)); } catch (e) {} }
  function isSkip(k) { return !!SKIP[k] && !isDone(k); }
  // 2026-11-08 成效：一次連發 18 則的那批，每則瀏覽中位數只有 14（分開發的 20–47）。記下每則「已回」的時間，
  // 一小時內回到 PACE 則就在上方提醒，建議下一批幾點再發。只記在這台裝置（daybreak.donetimes：{鍵: 毫秒}）。
  var TK = 'daybreak.donetimes', DT = {}, PACE = 8;
  try { DT = JSON.parse(localStorage.getItem(TK) || '{}'); } catch (e) {}
  function paceNote() {
    var now = Date.now(), ts = Object.keys(DT).filter(function (k) { return k.indexOf('reply:') === 0 && now - DT[k] < 3600e3; }).map(function (k) { return DT[k]; }).sort();
    if (ts.length < PACE) return '';
    var t = new Date(ts[ts.length - PACE] + 3600e3), hm = String(t.getHours()).padStart(2, '0') + ':' + String(t.getMinutes()).padStart(2, '0');
    return '<span class="warn">這一小時已回 ' + ts.length + ' 則，下一批建議 ' + hm + ' 之後再發</span>';
  }
  function footHtml(k, reply) {
    var L = reply ? ['已回', '標記已回', '不回'] : ['已發', '標記已發', '不發'];
    if (POSTED[k]) return '<div class="foot"><span class="note">已記錄發出（' + md(POSTED[k]) + '）</span></div>';
    if (isDone(k)) return '<div class="foot"><button class="done-btn on" data-act="done">✓ ' + L[0] + ' · 復原</button></div>';
    if (isSkip(k)) return '<div class="foot"><button class="skip-btn on" data-act="skip">已設為' + L[2] + ' · 復原</button></div>';
    return '<div class="foot"><button class="skip-btn" data-act="skip">' + L[2] + '</button><button class="done-btn" data-act="done">' + L[1] + '</button></div>';
  }

  // ---------- 分頁 ----------
  var TAB = (location.hash || '').replace('#', '') || document.body.dataset.tab || 'today';
  function setTab(t) {
    TAB = t === 'replies' ? 'replies' : 'today';
    document.querySelectorAll('.tab').forEach(function (b) { b.classList.toggle('on', b.dataset.tab === TAB); });
    document.querySelectorAll('.view').forEach(function (v) { v.hidden = v.id !== 'v-' + TAB; });
    history.replaceState(null, '', '#' + TAB);
    document.title = TAB === 'replies' ? '回覆 · 破曉運營台' : '今天發文 · 破曉運營台';
  }

  // ---------- 共用的卡片內容 ----------
  function countLine(t, lim, longMode) {
    var w = weight(t);
    if (longMode) return '<div class="count"><span>長文 · X 先顯示前 280 字左右，重點放前兩段</span><span class="' + (w > lim ? 'over' : '') + '">' + [...t].length + ' 字</span></div>';
    return '<div class="count"><span></span><span class="' + (w > lim ? 'over' : '') + '">' + w + ' / ' + lim + '</span></div>';
  }
  function imgActs(k, imgs, names) {
    if (!imgs.length) return '';
    if (MOBILE) return '<button class="btn" data-act="save" data-k="' + k + '">存圖</button>';
    return imgs.map(function (u, i) {
      var n = imgs.length > 1 ? ' ' + (i + 1) : '';
      return (window.ClipboardItem ? '<button class="btn" data-act="copyimg" data-k="' + k + '" data-i="' + i + '">複製圖片' + n + '</button>' : '') +
        '<a class="btn ghost" href="' + u + '" download="' + esc(names[i]) + '">下載' + n + '</a>';
    }).join('');
  }
  function textBlock(t, foldable) {
    var long = t.length > 420 || (foldable && t.split('\n').length > 9);
    return '<pre class="txt' + (long ? ' fold' : '') + '">' + esc(t) + '</pre>' + (long ? '<button class="linkish" data-act="unfold">展開全文</button>' : '');
  }
  function noteBlock(note) {
    if (!note) return '';
    var long = note.length > 90;
    return '<p class="note' + (long ? ' clamp2' : '') + '">' + esc(note) + '</p>' + (long ? '<button class="linkish" data-act="unclamp">看完整說明</button>' : '');
  }

  // ---------- 今天發文 ----------
  var POSTS = [];
  var TYPE = { daily: ['日報', 't-daily'], pick: ['推薦圖表', 't-pick'], long: ['長貼文', 't-long'], flash: ['快訊', 't-flash'] };

  function buildPosts(xp, fl, lp, pj, ix) {
    var out = [];
    if (xp) {   // 日報：每天早上日報出來就發
      var d = { key: 'daily:' + xp.date, type: 'daily', when: at(TODAY, '08:30'), title: 'No.' + String(xp.edition || 0).padStart(3, '0') + ' 日報', sub: md(xp.date) + ' 收盤', langs: {} };
      [['zh', xp.image_zh], ['en', xp.image_en]].forEach(function (L) {
        if (!xp[L[0]]) return; var sp = splitLink(xp[L[0]]);
        d.langs[L[0]] = { text: sp[0], link: sp[1], imgs: L[1] ? [img(L[1])] : [], names: ['daybreak-' + xp.date + '-' + L[0] + '.png'], lim: 280 };
      });
      out.push(d);
    }
    if (pj || ix) {   // 推薦圖表：解說和圖同一天才放解說
      var withText = pj && pj.picks && pj.picks.length && (!ix || ix.date === pj.date);
      var list = withText ? pj.picks : (ix && ix.picks) || [], date = withText ? pj.date : ix && ix.date;
      var names = {}; ((ix && ix.picks) || []).forEach(function (x) { names[x.id] = x; });
      list.forEach(function (q) {
        var nm = (names[q.id] || {}).name || {}, p = { key: 'pick:' + date + ':' + q.id, type: 'pick', when: at(TODAY, (q.post_at || '12:00').slice(0, 5)),
          title: q.q_zh || nm.zh || q.id, sub: nm.zh || '', note: q.why, link: (names[q.id] || {}).link, langs: {} };
        ['zh', 'en'].forEach(function (lang) {
          var ch = lang === 'zh' ? (q.chart || 'data/picks/' + q.id + '.png') : (q.chart_en || 'data/picks/' + q.id + '-en.png');
          p.langs[lang] = { text: (withText && q[lang]) || '', imgs: [img(ch)], names: ['daybreak-' + date + '-' + q.id + (lang === 'en' ? '-en' : '') + '.png'], lim: 280 };
        });
        out.push(p);
      });
    }
    ((fl && fl.items) || []).filter(function (x) { return tpe(x.time) === TODAY; }).forEach(function (x) {   // 快訊：只留今天的
      var f = { key: 'flash:' + x.id, type: 'flash', when: new Date(x.time), title: x.title || '快訊', note: x.note, langs: {} };
      ['zh', 'en'].forEach(function (lang) {
        if (!x[lang]) return; var sp = splitLink(x[lang]);
        f.langs[lang] = { text: sp[0], link: sp[1], imgs: x.image ? [img('data/flash/' + x.id + '-' + lang + '.png')] : [], names: ['daybreak-flash-' + x.id + '-' + lang + '.png'], lim: 280 };
      });
      out.push(f);
    });
    ((lp && lp.items) || []).forEach(function (x) {   // 長貼文：沒發的一直留著；之前就標記已發的不再顯示
      var k = 'long:' + x.id; if (x.posted) POSTED[k] = x.posted;
      if ((DONE[k] || x.posted || SKIP[k] || '9') < TODAY) return;
      var ims = (x.images || []).map(img), L = { key: k, type: 'long', when: new Date(x.time), title: x.title || '', note: x.note, langs: {} };
      ['zh', 'en'].forEach(function (lang) {
        if (!x[lang]) return;
        L.langs[lang] = { text: x[lang], imgs: ims, names: ims.map(function (_, i) { return 'daybreak-' + x.id + (ims.length > 1 ? '-' + (i + 1) : '') + (lang === 'en' ? '-en' : '') + '.png'; }), lim: 25000, long: true };
      });
      out.push(L);
    });
    out.forEach(function (p) { Object.keys(p.langs).forEach(function (l) { var o = p.langs[l]; TEXT[p.key + '|' + l] = o.text; prefetch(p.key + '|' + l, o.imgs, o.names); }); CARDS[p.key] = p; });
    return out;
  }

  function postCard(p) {
    var dn = isDone(p.key), sk = isSkip(p.key), langs = Object.keys(p.langs), first = langs[0], now = Date.now();
    var day = tpe(p.when), st = dn ? '<span class="state ok">已發</span>' : sk ? '<span class="state">不發</span>' : p.when.getTime() <= now ? '<span class="state due">該發了</span>' : '<span class="state">稍後</span>';
    var tl = day === TODAY ? hm(p.when) : (day < TODAY ? '之前 ' : '') + md(day) + ' ' + hm(p.when);
    var h = '<button class="card-h stack" data-act="toggle"><span class="row1"><span class="time">' + tl + '</span><span class="chip ' + TYPE[p.type][1] + '">' + TYPE[p.type][0] + '</span>' +
      '<span class="sp"></span>' + st + '<span class="chev">›</span></span><span class="title">' + esc(p.title) + (p.sub ? '<small>' + esc(p.sub) + '</small>' : '') + '</span></button>';
    var b = noteBlock(p.note) + (p.link ? '<p class="note"><a href="' + esc(p.link) + '" target="_blank" rel="noopener">網站上的這張圖 ↗</a></p>' : '');
    if (langs.length > 1) b += '<div class="seg">' + langs.map(function (l) { return '<button data-act="lang" data-v="' + l + '" class="' + (l === first ? 'on' : '') + '">' + (l === 'zh' ? '中文' : 'English') + '</button>'; }).join('') + '</div>';
    b += langs.map(function (l) {
      var o = p.langs[l], k = p.key + '|' + l;
      var body = o.text ? countLine(o.text, o.lim, o.long) + textBlock(o.text, o.long) : '<p class="note">解說還沒寫好，先只有圖。</p>';
      return '<div class="lp" data-lang="' + l + '"' + (l === first ? '' : ' hidden') + '>' + body +
        (o.imgs.length ? '<div class="imgs">' + o.imgs.map(function (u) { return '<img src="' + u + '" alt="" loading="lazy">'; }).join('') + '</div>' : '') +
        '<div class="acts"><button class="btn primary" data-act="post" data-k="' + k + '"' + (o.text ? '' : ' disabled') + '>' + (MOBILE ? '分享到 X' : '發到 X') + '</button>' +
        (o.text && MOBILE ? '<a class="btn" data-act="app" data-k="' + k + '" href="twitter://post?message=' + encodeURIComponent(o.text.length <= 1500 ? o.text : '') + '">打開 X App</a>' : '') +
        (o.text ? '<button class="btn" data-act="copy" data-k="' + k + '">複製文字</button>' : '') + imgActs(k, o.imgs, o.names) + '</div>' +
        (o.link ? (TEXT[k + ':link'] = o.link, '<div class="sub-box"><p>發完後，在自己這則底下回覆這行連結（正文帶連結曝光少約四成）</p><pre>' + esc(o.link) + '</pre><button class="btn ghost" data-act="copy" data-k="' + k + ':link">複製連結</button></div>') : '') +
        '</div>';
    }).join('');
    b += footHtml(p.key, false);
    return '<article class="card' + (dn || sk ? ' done' : '') + '" data-key="' + esc(p.key) + '">' + h + '<div class="card-b">' + b + '</div></article>';
  }

  function renderPosts() {
    var el = document.getElementById('v-today');
    var byT = function (a, b) { return a.when - b.when; };
    var todo = POSTS.filter(function (p) { return !isDone(p.key) && !isSkip(p.key); }).sort(byT);
    var done = POSTS.filter(function (p) { return isDone(p.key); }).sort(byT), skipped = POSTS.filter(function (p) { return isSkip(p.key); }).sort(byT);
    var due = todo.filter(function (p) { return p.when.getTime() <= Date.now(); }).length;
    document.getElementById('b-today').textContent = todo.length; document.getElementById('b-today').classList.toggle('zero', !todo.length);
    el.innerHTML = '<div class="summary"><span>待發 <b>' + todo.length + '</b></span>' + (due ? '<span class="warn">該發了 ' + due + '</span>' : '') + '<span>已發 <b>' + done.length + '</b></span>' + (skipped.length ? '<span>不發 <b>' + skipped.length + '</b></span>' : '') + '<span>' + md(TODAY) + ' 台北</span></div>' +
      (todo.length ? todo.map(postCard).join('') : '<p class="empty">今天的都處理完了</p>') +
      (done.length ? '<div class="group-h">已完成</div>' + done.map(postCard).join('') : '') +
      (skipped.length ? '<details class="group"><summary>不發 ' + skipped.length + ' 則</summary>' + skipped.map(postCard).join('') + '</details>' : '');
  }

  // ---------- 回覆 ----------
  var R = null, RFILTER = 'all', RFETCHED = {};
  function replyKey(x) { return 'reply:' + x.id; }
  function rfilter(x) {
    return RFILTER === 'all' || (RFILTER === 'follow' && x.kind === 'followup') || (RFILTER === 'new' && x.kind !== 'followup') || (RFILTER === 'quote' && (x.mode === 'quote' || (x.quote && !x.reply)));
  }
  function replyCard(x, i) {
    var k = replyKey(x), dn = isDone(k), sk = isSkip(k), skip = x.status === 'skip', t = x.reply || '', q = x.quote || '';
    var modes = []; if (t) modes.push('reply'); if (q) modes.push('quote');
    var first = x.mode === 'quote' && q ? 'quote' : modes[0];
    var im = x.image ? img('data/replies/' + x.n + '.png') : '', nm = 'daybreak-reply-' + R.date + '-' + x.n + '.png';
    TEXT[k + '|reply'] = t; TEXT[k + '|quote'] = q; CARDS[k] = x;
    if (im && !FILES[k + '|reply']) prefetch(k + '|reply', [im], [nm]);
    var tags = (x.kind === 'followup' ? '<span class="tag follow">接話</span>' : '') + (x.mode === 'quote' ? '<span class="tag hot">建議引用</span>' : '') +
      (x.status === 'optional' ? '<span class="tag">可選</span>' : '') + '<span class="tag">' + esc(x.angle || '') + '</span>' + '<span class="tag blue" data-v="' + x.id + '" hidden>藍勾</span>';
    var h = '<button class="card-h" data-act="toggle"><span class="who"><span class="ord">' + x.n + '</span><span class="name">@' + esc(x.author) + '</span>' +
      '<span class="fans">' + fans(x.followers) + ' · ' + ago(x.posted) + '</span>' + tags + '<span class="line2">' + esc(x.summary || '') + '</span></span>' +
      (dn ? '<span class="state ok">已回</span>' : sk ? '<span class="state">不回</span>' : '') + '<span class="chev">›</span></button>';
    var b = '<div class="orig fold" id="o' + x.id + '">' + esc(x.summary) + '<span class="m">摘要（點開後讀原文）</span></div>' +
      '<button class="linkish" data-act="unfold-orig" hidden>展開原文</button> <a class="orig-link" href="' + esc(x.url) + '" target="_blank" rel="noopener">在 X 看原文 ↗</a>';
    if (skip) { b += noteBlock(x.note); return '<article class="card" data-key="' + k + '">' + h + '<div class="card-b">' + b + '</div></article>'; }
    if (modes.length > 1) b += '<div class="seg">' + modes.map(function (m) { return '<button data-act="lang" data-v="' + m + '" class="' + (m === first ? 'on' : '') + '">' + (m === 'reply' ? '回覆' : '引用') + '</button>'; }).join('') + '</div>';
    b += modes.map(function (m) {
      var tx = m === 'reply' ? t : q, kk = k + '|' + m, lim = m === 'quote' && x.long ? 25000 : 280, w = weight(tx) + (m === 'quote' ? 23 : 0);
      var cnt = '<div class="count"><span>' + (m === 'quote' ? '引用發文 · 算原創、計入首頁曝光' + (x.long ? ' · 長文，X 先顯示前 280 字左右' : '') : '回覆') + '</span><span class="' + (w > lim ? 'over' : '') + '">' + w + ' / ' + (lim === 25000 ? '25,000' : lim) + '</span></div>';
      var prim = MOBILE ? '<a class="btn primary" data-act="open" data-k="' + kk + '" href="' + esc(x.url) + '">複製並打開 X' + (m === 'quote' ? '（轉推 → 引用）' : '') + '</a>'
        : m === 'reply' ? '<a class="btn primary" data-act="intent" data-k="' + kk + '" href="' + esc('https://x.com/intent/post?in_reply_to=' + x.id + '&text=' + encodeURIComponent(tx)) + '" target="_blank" rel="noopener">在 X 回覆</a>'
        : '<a class="btn primary" data-act="intent" data-k="' + kk + '" href="' + esc('https://x.com/intent/post?text=' + encodeURIComponent(tx) + '&url=' + encodeURIComponent(x.url)) + '" target="_blank" rel="noopener">引用發文</a>';
      return '<div class="lp" data-lang="' + m + '"' + (m === first ? '' : ' hidden') + '>' + cnt + textBlock(tx, x.long) +
        (im ? '<div class="imgs small"><img src="' + im + '" alt="" loading="lazy"></div>' : '') +
        '<div class="acts">' + prim + '<button class="btn" data-act="copy" data-k="' + kk + '">複製文字</button>' + imgActs(k + '|reply', im ? [im] : [], [nm]) + '</div></div>';
    }).join('');
    if (x.sources || x.note) b += '<details class="more"><summary>數字來源與備註</summary>' + (x.sources ? '<p>數字：' + esc(x.sources) + '</p>' : '') + (x.note ? '<p>' + esc(x.note) + '</p>' : '') + '</details>';
    b += footHtml(k, true);
    return '<article class="card' + (dn || sk ? ' done' : '') + '" data-key="' + k + '">' + h + '<div class="card-b">' + b + '</div></article>';
  }
  function renderReplies() {
    var el = document.getElementById('v-replies'); if (!R) return;
    var items = R.items.slice().sort(function (a, b) { return b.n - a.n; });   // 2026-11-08 使用者：照寫完的先後倒序，最新（n 最大）在最上面
    var act = items.filter(function (x) { return x.status !== 'skip'; }), skip = items.filter(function (x) { return x.status === 'skip'; });
    var todo = act.filter(function (x) { return !isDone(replyKey(x)) && !isSkip(replyKey(x)); }), done = act.filter(function (x) { return isDone(replyKey(x)); }), mine = act.filter(function (x) { return isSkip(replyKey(x)); });
    document.getElementById('b-replies').textContent = todo.length; document.getElementById('b-replies').classList.toggle('zero', !todo.length);
    var cnt = { all: todo.length, follow: todo.filter(function (x) { return x.kind === 'followup'; }).length, new: todo.filter(function (x) { return x.kind !== 'followup'; }).length,
      quote: todo.filter(function (x) { return x.mode === 'quote' || (x.quote && !x.reply); }).length };
    var F = [['all', '全部'], ['follow', '接話'], ['new', '新貼文'], ['quote', '建議引用']].filter(function (f) { return f[0] === 'all' || cnt[f[0]]; });
    var idx = {}; act.forEach(function (x, i) { idx[x.id] = i; });
    var show = todo.filter(rfilter);
    el.innerHTML = '<div class="summary"><span>' + md(R.date) + ' 清單' + (R.date !== TODAY ? ' <span class="warn">（不是今天的）</span>' : '') + '</span><span>數據 No.' + String(R.edition || 0).padStart(3, '0') + '（' + md(R.data_date) + ' 收盤）</span>' +
      '<span>待回 <b>' + todo.length + '</b></span><span>已回 <b>' + done.length + '</b></span>' + (mine.length ? '<span>不回 <b>' + mine.length + '</b></span>' : '') + paceNote() + '</div>' +
      '<div class="filters">' + F.map(function (f) { return '<button class="fchip' + (RFILTER === f[0] ? ' on' : '') + '" data-act="filter" data-v="' + f[0] + '">' + f[1] + ' ' + cnt[f[0]] + '</button>'; }).join('') + '</div>' +
      (show.length ? show.map(function (x) { return replyCard(x, idx[x.id]); }).join('') : '<p class="empty">' + (todo.length ? '這一類沒有待回的' : '今天的都回完了') + '</p>') +
      (done.length ? '<details class="group"><summary>已回 ' + done.length + ' 則</summary>' + done.map(function (x) { return replyCard(x, idx[x.id]); }).join('') + '</details>' : '') +
      (mine.length ? '<details class="group"><summary>不回 ' + mine.length + ' 則</summary>' + mine.map(function (x) { return replyCard(x, idx[x.id]); }).join('') + '</details>' : '') +
      (skip.length ? '<details class="group"><summary>Claude 建議跳過 ' + skip.length + ' 則（點開看原因）</summary>' + skip.map(function (x) { return replyCard(x, 0); }).join('') + '</details>' : '');
  }
  function loadOrig(x) {   // 原文：點開時才讀 fxtwitter，讀不到就留摘要
    if (RFETCHED[x.id]) return; RFETCHED[x.id] = 1;
    fetch('https://api.fxtwitter.com/status/' + x.id).then(function (r) { return r.json(); }).then(function (j) {
      var tw = j && j.tweet; if (!tw) throw 0;
      document.querySelectorAll('[data-v="' + x.id + '"]').forEach(function (v) { v.hidden = !(tw.author && tw.author.verification && tw.author.verification.verified); });
      document.querySelectorAll('#o' + x.id).forEach(function (el) {
        el.innerHTML = esc(tw.text) + '<span class="m">原文 · ♥ ' + num(tw.likes) + ' · 回覆 ' + num(tw.replies) + ' · 轉推 ' + num(tw.retweets) + (tw.views ? ' · 瀏覽 ' + num(tw.views) : '') + (tw.media && tw.media.all && tw.media.all.length ? ' · 附圖 ' + tw.media.all.length : '') + '</span>';
        var more = el.nextElementSibling; if (more && el.scrollHeight > el.clientHeight + 4) more.hidden = false;
      });
    }).catch(function () { document.querySelectorAll('#o' + x.id + ' .m').forEach(function (m) { m.textContent = '摘要（原文讀取失敗，請在 X 看原文）'; }); });
  }

  // ---------- 開合 ----------
  function openCard(card, on) {
    if (!card) return;
    card.classList.toggle('open', on);
    if (on && card.dataset.key.indexOf('reply:') === 0) loadOrig(CARDS[card.dataset.key]);
  }
  function openFirst(viewId) {
    var c = document.querySelector('#' + viewId + ' > .card:not(.done)');
    if (c) openCard(c, true);
  }

  // ---------- 動作 ----------
  function postX(k, btn) {
    var t = TEXT[k] || '', f = FILES[k], canF = f && navigator.canShare && navigator.canShare({ files: f });
    copy(t).catch(function () {});
    if (MOBILE && navigator.share) {
      if (f && !canF) toast('圖還在載入，先只帶文字');
      toast('在選單裡選 X；文字已複製，沒帶進去就貼上');   // 2026-11-08：網頁沒辦法直接把圖送進 X App，只能透過分享選單
      navigator.share(canF ? { files: f, text: t } : { text: t }).catch(function () {});
      return;
    }
    var u = 'https://x.com/intent/post?text=' + encodeURIComponent(t), fit = u.length <= 4900;   // X 的 intent 網址上限約 5,000 字元
    window.open(fit ? u : 'https://x.com/compose/post', '_blank', 'noopener');
    toast(fit ? (f ? '文字已帶入；圖片按「複製圖片」再貼到發文框' : '已打開發文框') : '全文太長帶不進去，已複製，打開後直接貼上');
  }
  function mark(card, which) {   // which：done（已發／已回）或 skip（不發／不回），兩者互斥
    var k = card.dataset.key, S = which === 'skip' ? SKIP : DONE, other = which === 'skip' ? DONE : SKIP, on = !S[k];
    if (on) { S[k] = TODAY; delete other[k]; } else delete S[k];
    saveDone(); saveSkip();
    if (which === 'done') { if (on) DT[k] = Date.now(); else delete DT[k]; Object.keys(DT).forEach(function (q) { if (Date.now() - DT[q] > 2 * 86400e3) delete DT[q]; }); try { localStorage.setItem(TK, JSON.stringify(DT)); } catch (e) {} }
    var reply = k.indexOf('reply:') === 0;
    if (reply) renderReplies(); else renderPosts();
    if (on) { toast((which === 'skip' ? (reply ? '已設為不回' : '已設為不發') : (reply ? '已回' : '已發')) + '，打開下一則'); openFirst(reply ? 'v-replies' : 'v-today'); }
    else openCard(document.querySelector('.card[data-key="' + CSS.escape(k) + '"]'), true);
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-act]'); if (!b) return;
    var act = b.dataset.act, card = b.closest('.card');
    if (act === 'tab') { setTab(b.dataset.tab); return; }
    if (act === 'help') { document.getElementById('help').showModal(); return; }
    if (act === 'filter') { RFILTER = b.dataset.v; renderReplies(); openFirst('v-replies'); return; }
    if (act === 'toggle') { openCard(card, !card.classList.contains('open')); return; }
    if (act === 'lang') {
      card.querySelectorAll('.seg button').forEach(function (x) { x.classList.toggle('on', x === b); });
      card.querySelectorAll('.lp').forEach(function (p) { p.hidden = p.dataset.lang !== b.dataset.v; });
      return;
    }
    if (act === 'unfold') { var p = b.previousElementSibling; p.classList.remove('fold'); b.remove(); return; }
    if (act === 'unfold-orig') { var o = b.previousElementSibling; o.classList.remove('fold'); b.hidden = true; return; }
    if (act === 'unclamp') { b.previousElementSibling.classList.remove('clamp2'); b.remove(); return; }
    if (act === 'copy') { copy(TEXT[b.dataset.k] || '').then(function () { toast('已複製'); }, function () { toast('複製失敗'); }); return; }
    if (act === 'post') { postX(b.dataset.k, b); nudge(card); return; }
    if (act === 'open') { copy(TEXT[b.dataset.k] || '').catch(function () {}); nudge(card); return; }   // 不擋預設：連結照常打開（手機會跳到 X App）
    if (act === 'intent') { nudge(card); return; }
    if (act === 'app') { copy(TEXT[b.dataset.k] || '').catch(function () {}); toast('文字已複製；配圖先按「存圖」，再從相簿加'); nudge(card); return; }   // 不擋預設：twitter:// 打開 X App 發文框
    if (act === 'save') {
      var f = FILES[b.dataset.k];
      if (!f || !navigator.canShare || !navigator.canShare({ files: f })) { toast('圖還在載入…'); return; }
      navigator.share({ files: f }).catch(function () {}); return;
    }
    if (act === 'copyimg') {
      var fs = FILES[b.dataset.k]; if (!fs) { toast('圖還在載入…'); return; }
      navigator.clipboard.write([new ClipboardItem({ 'image/png': fs[+(b.dataset.i || 0)] })]).then(function () { toast('圖片已複製，貼到 X 發文框'); }, function () { toast('複製失敗，改用下載'); });
      return;
    }
    if (act === 'done' || act === 'skip') { mark(card, act); return; }
  });
  function nudge(card) { var d = card && card.querySelector('.done-btn'); if (d && !d.classList.contains('on')) { d.classList.remove('nudge'); void d.offsetWidth; d.classList.add('nudge'); } }

  // ---------- 啟動 ----------
  setTab(TAB);
  window.addEventListener('hashchange', function () { var h = location.hash.replace('#', ''); if (h && h !== TAB) setTab(h); });
  var soft = function (p) { return p.catch(function () { return null; }); };
  Promise.all([soft(getJSON('data/x_post.json')), soft(getJSON('data/flash.json')), soft(getJSON('data/longposts.json')), soft(getJSON('data/picks.json')), soft(getJSON('data/picks/index.json'))]).then(function (r) {
    if (r[0]) document.getElementById('meta').textContent = 'No.' + String(r[0].edition || 0).padStart(3, '0') + ' · ' + md(r[0].date) + ' 收盤';
    POSTS = buildPosts(r[0], r[1], r[2], r[3], r[4]);
    renderPosts(); openFirst('v-today');
  });
  getJSON('data/replies.json').then(function (j) { R = j; renderReplies(); openFirst('v-replies'); })
    .catch(function () { document.getElementById('v-replies').innerHTML = '<p class="empty">讀取失敗：data/replies.json</p>'; });
})();
