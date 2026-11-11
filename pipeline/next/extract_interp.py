# -*- coding: utf-8 -*-
"""把舊版網站（classic.html）每個面板的讀值（interp）、提示（note）抽出來，給新版首頁的每張圖當白話結論：
python3 pipeline/next/extract_interp.py [en] → pipeline/next/interp.zh.json／interp.en.json（2026-11-11 起首頁換成新版，舊版搬到 classic.html）"""
import sys, os, json, time, subprocess, tempfile, urllib.request
HERE0 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE0, '..', '..', 'ops', 'post')); import site_shot as S
HERE = os.path.dirname(os.path.abspath(__file__)); en = 'en' in sys.argv
S.serve(); prof = tempfile.mkdtemp(prefix='dbx-'); PORT = 9366
p = subprocess.Popen([S.CHROME, '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={prof}', '--hide-scrollbars', '--no-first-run', '--window-size=1500,1000', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    tg = None
    for _ in range(150):
        try: tg = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json')); break
        except Exception: time.sleep(0.2)
    ws = S.WS(next(t for t in tg if t['type'] == 'page')['webSocketDebuggerUrl']); ws.call('Page.enable'); ws.call('Runtime.enable')
    ws.call('Emulation.setDeviceMetricsOverride', width=1500, height=1000, deviceScaleFactor=1, mobile=False)
    ws.call('Page.addScriptToEvaluateOnNewDocument', source="try{localStorage.setItem('daybreak.lang','%s')}catch(e){}" % ('en' if en else 'zh'))
    ws.call('Page.navigate', url='http://127.0.0.1:8790/classic.html'); S.wait(ws, 'document.readyState === "complete"'); time.sleep(4)
    ids = json.loads(ws.js('JSON.stringify(Array.prototype.map.call(document.querySelectorAll("[id^=pg-]"), function(e){return e.id.slice(3)}))'))
    for i in ids:
        ws.js('location.hash = "#%s"; 1' % i); time.sleep(1.6)
    ws.js('window.scrollTo(0, document.documentElement.scrollHeight); 1'); time.sleep(2.5)
    out = ws.js("""JSON.stringify(Array.prototype.map.call(document.querySelectorAll('section.panel'), function (p) {
      var tx = function (e) { return e ? e.textContent.replace(/\\s+/g, ' ').trim() : ''; }, pg = p.closest('[id^=pg-]');
      return { page: pg ? pg.id.slice(3) : '', id: p.id || '', title: tx(p.querySelector('.panel-h h2')), src: tx(p.querySelector('.panel-h .src')), charts: Array.prototype.map.call(p.querySelectorAll('[id^=c-]'), function (c) { return c.id.slice(2); }),
        items: Array.prototype.map.call(p.querySelectorAll('.interp .it'), function (it) { var tn = it.querySelector('.tn'); var cg = it.querySelector('.chg'), cb = cg ? cg.querySelector('b') : null, chg = cg ? tx(cg).slice(cb ? tx(cb).length : 0).trim() : '', dd = tx(it.querySelector('.d')); if (cg) dd = dd.slice(0, dd.length - tx(cg).length).trim(); return { k: tx(it.querySelector('.k')), v: tx(it.querySelector('.v')), tone: tn ? (tn.className.replace('tn', '').trim() || 'neu') : 'neu', d: dd, chg: chg, view: it.classList.contains('view') ? 1 : 0, more: it.closest('.rd-more') ? 1 : 0 }; }),
        flags: Array.prototype.map.call(p.querySelectorAll('.sig-flag summary b'), tx),
        kids: Array.prototype.map.call(p.children, function (c) { return c.tagName.toLowerCase() + '.' + String(c.className).split(' ').slice(0, 2).join('.') + ':' + tx(c).length; }),
        says: Array.prototype.filter.call(p.children, function (c) { return c.matches('p.say'); }).map(tx), rd: [].concat.apply([], Array.prototype.filter.call(p.children, function (c) { return c.matches('div.rd'); }).map(function (c) { var out = []; (function walk(n) { Array.prototype.forEach.call(n.children, function (k) { if (k.children.length && !/^(P|LI|B|SPAN|SUMMARY)$/.test(k.tagName)) walk(k); else { var s = tx(k); if (s) out.push((/^(B|SUMMARY)$/.test(k.tagName) ? '#' : '') + s); } }); })(c); return out.length ? out : [tx(c)]; })), notes: Array.prototype.filter.call(p.children, function (c) { return c.matches('p.note'); }).map(tx) };
    }))""")
    D = json.loads(out); fn = 'interp.%s.json' % ('en' if en else 'zh'); json.dump(D, open(os.path.join(HERE, fn), 'w', encoding='utf-8'), ensure_ascii=False)
    print('pages', ids); print('panels', len(D), 'with items', sum(1 for x in D if x['items']), 'items', sum(len(x['items']) for x in D), 'views', sum(1 for x in D for it in x['items'] if it['view']))
finally:
    p.terminate()
