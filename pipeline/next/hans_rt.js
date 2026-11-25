/* 簡體中文（2026-11-25，使用者：「產品增加簡體選項」）。assets/hans.js 由 pipeline/next/hans.py --js 用這個檔加上 OpenCC 的字典產生，不要直接改 assets/hans.js。
   做法：網站的字照舊用繁體寫（page.html、各 *_data.py、每日讀數），選了「简」才在瀏覽器裡把畫面上的字轉成簡體：
   - conv(s)：OpenCC tw2sp（台灣正體 → 大陸簡體，含用詞：網路→网络、資訊→信息），演算法逐行照 opencc-python-reimplemented 0.1.7 移植，
     字典也是它的（tw2sp.json 的兩組），所以和部署時產生的簡體主題頁（hans.py）同一套結果；最後再套 hans.py 的金融用詞表 TERMS（聯準會→美联储……）。
   - on()：整頁的字和 title／aria-label／placeholder 這類屬性轉過去，之後頁面新畫上去的字（MutationObserver）、canvas 上畫的字（fillText）也一起轉；
     中文字型換成 Noto Sans SC（同一個字兩岸寫法不同，用繁體字型排簡體字會混著台灣字形）。
   - off()：切回繁體或英文時，被轉過的字和屬性換回原本的繁體。
   不轉的地方：<script>、<style>、輸入框裡使用者打的字、標了 data-nohans 的元素。 */
(function () {
  'use strict';
  if (window.DaybreakHans) return;
  var CH = __CHAIN__, TM = __TERMS__;
  CH.forEach(function (g) { g.forEach(function (t) { if (t.k != null) { var d = Object.create(null); for (var i = 0; i < t.k.length; i++) d[t.k[i]] = t.v[i]; t.d = d; } }); });
  /* 斷句（OpenCC 的 PhraseExtract 分隔字元，和 Python 版同一串） */
  var SEP = /(\s+|-|,|\.|\?|!|\*|　|，|。|、|；|：|？|！|…|“|”|‘|’|『|』|「|」|﹁|﹂|—|－|（|）|《|》|〈|〉|～|．|／|＼|︒|︑|︔|︓|︿|﹀|︹|︺|︙|︐|［|﹇|］|﹈|︕|︖|︰|︳|︴|︽|︾|︵|︶|｛|︷|｝|︸|﹃|﹄|【|︻|】|︼)/;
  var HZ = /[㐀-鿿豈-﫿]/;
  /* 在字串裡找最長、最左的詞（__findMatch） */
  function find(s, t, hint) {
    var n = s.length, L = Math.min(n, t.m); if (hint) L = Math.min(L, hint);
    for (; L >= t.n; L--) for (var i = 0; i + L <= n; i++) { var v = t.d[s.substr(i, L)]; if (v !== undefined) return [v, i, L]; }
    return null;
  }
  /* 一組字典（StringTree.create_parse_tree＋inorder）：先換最長的詞，左右剩下的再各自找；同一組裡前面的字典換過的，後面的不再換 */
  function group(s, g) {
    var root = { v: s, l: null, r: null, h: null }, work = [root], un = [], di, c, m, v, i, L, tmp;
    for (di = 0; di < g.length; di++) {
      while (work.length) {
        c = work.pop(); m = find(c.v, g[di], c.h);
        if (m) {
          v = c.v; i = m[1]; L = m[2]; c.v = m[0]; c.h = null;
          if (i > 0) { c.l = { v: v.slice(0, i), l: null, r: null, h: L }; work.push(c.l); }
          if (i + L < v.length) { c.r = { v: v.slice(i + L), l: null, r: null, h: L }; work.push(c.r); }
        } else { c.h = null; un.push(c); }
      }
      tmp = work; work = un; un = tmp;
    }
    var out = '', st = [], cur = root;
    for (;;) { while (cur) { st.push(cur); cur = cur.l; } if (!st.length) break; cur = st.pop(); out += cur.v; cur = cur.r; }
    return out;
  }
  var CACHE = new Map();
  function conv(s) {
    if (typeof s !== 'string' || !HZ.test(s)) return s;
    var hit = CACHE.get(s); if (hit !== undefined) return hit;
    var p = s.split(SEP), j, k;
    for (j = 0; j < p.length; j += 2) if (p[j] && HZ.test(p[j])) for (k = 0; k < CH.length; k++) p[j] = group(p[j], CH[k]);
    var o = p.join('');
    for (j = 0; j < TM.length; j++) if (o.indexOf(TM[j][0]) >= 0) o = o.split(TM[j][0]).join(TM[j][1]);
    if (CACHE.size > 8000) CACHE.clear(); CACHE.set(s, o);
    return o;
  }

  /* ── 畫面 ── */
  var ON = false, TX = new WeakMap(), AT = new WeakMap(), ATTR = ['title', 'aria-label', 'placeholder', 'alt', 'data-tip', 'data-src'], SKIP = 'script,style,textarea,input,[data-nohans]';
  var BR = /[⠀-⣿]/;   // 換語言時的點字動畫（字先變成點字再解回來）：中間的畫面不轉也不記，不然會蓋掉原本的繁體，切回繁體時還原不了
  function txt(n, chk) {
    var s = n.nodeValue; if (!s || !HZ.test(s) || BR.test(s)) return;
    if (chk) { var pe = n.parentElement; if (!pe || pe.closest(SKIP)) return; }
    var r = TX.get(n); if (r && r.c === s) return;   // 自己剛寫的
    var c = conv(s); TX.set(n, { o: s, c: c }); if (c !== s) n.nodeValue = c;
  }
  function el(e) {
    for (var i = 0; i < ATTR.length; i++) {
      var a = ATTR[i], s = e.getAttribute(a); if (!s || !HZ.test(s)) continue;
      var r = AT.get(e); if (!r) { r = {}; AT.set(e, r); }
      if (r[a] && r[a].c === s) continue;
      var c = conv(s); r[a] = { o: s, c: c }; if (c !== s) e.setAttribute(a, c);
    }
  }
  var FIL = { acceptNode: function (n) { return n.nodeType === 1 && n.matches(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; } };
  function walk(root, fn, fe) {
    if (root.nodeType === 3) { var pe = root.parentElement; if (pe && !pe.closest(SKIP)) fn(root); return; }
    if (root.nodeType === 1) { if (root.closest(SKIP)) return; fe(root); } else if (root.nodeType !== 9 && root.nodeType !== 11) return;
    var w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, FIL), n;
    while ((n = w.nextNode())) { if (n.nodeType === 3) fn(n); else fe(n); }
  }
  var MO = new MutationObserver(function (rs) {
    if (!ON) return;
    for (var i = 0; i < rs.length; i++) {
      var r = rs[i];
      if (r.type === 'characterData') txt(r.target, true);
      else if (r.type === 'attributes') { if (!r.target.closest(SKIP)) el(r.target); }
      else for (var j = 0; j < r.addedNodes.length; j++) { var a = r.addedNodes[j]; if (a.isConnected) walk(a, txt, el); }
    }
  });
  /* canvas 上畫的字（圖上的刻度、標註） */
  [window.CanvasRenderingContext2D, window.OffscreenCanvasRenderingContext2D].forEach(function (K) {
    if (!K) return;
    ['fillText', 'strokeText', 'measureText'].forEach(function (f) { var o = K.prototype[f]; if (!o) return; K.prototype[f] = function (t) { if (ON && typeof t === 'string' && HZ.test(t)) { var a = Array.prototype.slice.call(arguments); a[0] = conv(t); return o.apply(this, a); } return o.apply(this, arguments); }; });
  });
  /* 字型：把 Noto Sans SC 的字型檔登記成「Noto Sans TC」，比原本的晚宣告，同一段字碼優先用它；頁面上所有寫著 Noto Sans TC 的地方（CSS、canvas）都不用改 */
  var FS = null;
  function font(on) {
    if (FS) { FS.media = on ? 'all' : 'not all'; return; }
    if (!on || !window.fetch) return;
    FS = document.createElement('style'); FS.id = 'hans-font'; (document.head || document.documentElement).appendChild(FS);
    fetch('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400..900&display=swap').then(function (r) { return r.text(); })
      .then(function (css) { FS.textContent = css.replace(/font-family:\s*'Noto Sans SC'/g, "font-family: 'Noto Sans TC'"); }).catch(function () {});
  }
  function on() {
    if (ON) return; ON = true; font(true);
    MO.observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTR });
    walk(document.documentElement, txt, el);
  }
  function off() {
    if (!ON) return; MO.takeRecords(); MO.disconnect(); ON = false; font(false);
    walk(document.documentElement, function (n) { var r = TX.get(n); if (r && n.nodeValue === r.c && r.c !== r.o) n.nodeValue = r.o; TX.delete(n); },
      function (e) { var r = AT.get(e); if (!r) return; for (var a in r) if (e.getAttribute(a) === r[a].c && r[a].c !== r[a].o) e.setAttribute(a, r[a].o); AT.delete(e); });
  }
  window.DaybreakHans = { conv: conv, on: on, off: off, get active() { return ON; } };
})();
