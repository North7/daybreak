# -*- coding: utf-8 -*-
"""GEO 第二批（2026-11-20，使用者：「接著做第二批」）：每張圖一頁、每天的簡報一頁，中英各自一個網址。
AI 搜尋引用的是「直接回答一個問題」的頁面（「比特幣 MVRV 現在多少、代表什麼」「11/19 比特幣為什麼跌」），不是要跑 JS 的儀表板。

寫出（都是純 HTML，不用 JS 也看得完整；人點進來可以一鍵打開互動圖）：
  charts/<k>/        每張圖：表態和理由、各項讀數、這張圖在看什麼、怎麼看、要小心、資料來源、同一頁的其他圖（中文）
  en/charts/<k>/     英文版
  charts/、en/charts/  六個問題分組的索引
  brief/<日期>/      每天的簡報（data/archive）：頭條、整體、摘要、要盯的價位、各版結論、今日發現；英文封存有的日期才有 en/brief/<日期>/
  brief/、en/brief/  簡報索引
  sitemap.xml        在原本的 4 個網址後面加上以上全部（含 hreflang 中英對照）

這些頁面不進程式庫：每次部署時（cloudflare.yml）寫進上傳的資料夾，每天跟著資料更新，也不會讓每天的提交多出幾百個檔。
本機預覽：python3 pipeline/next/pages.py --out <資料夾>（資料夾裡要先有網站的其他檔，sitemap.xml 會被改寫）。
頁面規則（整批一起定，不要一頁一頁改）：
  ① 深色近黑底、暖白字，跟著系統切淺色紙色底；字體、顏色、DAYBREAK 標誌和數據頁同一套；左右留白 22px 起、寬螢幕到 56px，內容寬最多 760px
  ② 由上往下：所在的頁和問題（等寬小字）→ 圖名 → 表態膠囊＋一句理由 → 「打開互動圖」→ 讀數 → 說明；不用框裡再套框，區塊之間只用細線
  ③ 表態顏色：偏多綠、偏空紅、中性灰（數據頁同一組）；其他地方不加顏色
  ④ 右上角「中／EN」是另一個語言的網址（不是切換鈕），兩個語言互相標 hreflang
  ⑤ 署名只用 Aron；頁尾寫明不給交易建議"""
import json, glob, os, sys, re, html, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geo   # 讀好的資料（NX、PAGES、LEANS、QS…）和一張圖的一句話（geo.read）
from geo import esc, SITE, PERSON, WEBSITE, TN, QS, PAGES, LEANS, NX, _MON

REPO = geo.REPO
DATE = geo.DATE
PREV = json.load(open(os.path.join(REPO, 'data', 'leans.json'), encoding='utf-8')).get('prev', {})
HOW = json.load(open(os.path.join(HERE, 'how.json'), encoding='utf-8'))
PG = {q['id']: q for q in QS}
CHART_PG = {c['k']: q['id'] for q in QS for c in geo.charts(q['id'])}
MOD = {'overview': ('總覽', 'Overview'), 'cycle': ('週期', 'Cycle'), 'market': ('價格結構', 'Price structure'), 'onchain': ('鏈上', 'On-chain'),
       'flows': ('資金流', 'Flows'), 'deriv': ('衍生品', 'Derivatives'), 'book': ('掛單簿', 'Order book'), 'exit': ('出場', 'Exit'), 'news': ('新聞', 'News')}
LEAN_CLS = {'up': 'up', 'down': 'dn', 'neu': 'nu', 'warn': 'nu', 'bull': 'up', 'bear': 'dn', 'neutral': 'nu'}
LOGO = '<svg viewBox="0 0 64 64" aria-hidden="true"><path d="M18 40a14 14 0 0 1 28 0" fill="none" stroke="#FF4F1F" stroke-width="5"/><path d="M6 40h52" stroke="currentColor" stroke-width="5"/></svg>'

CSS = """:root{color-scheme:dark;--bg:#060607;--ink:#EDEDE8;--ink2:#B4B0A7;--ink3:#7E7A72;--line:#232327;--sheet:#0E0E10;--up:#2FD08A;--dn:#FF4A2E;--nu:#8F8F8A;--brand:#FF4F1F;
--gx:clamp(22px,4vw,56px);--f-sans:"Geist","Noto Sans TC",system-ui,sans-serif;--f-head:"Inter Tight","Noto Sans TC",system-ui,sans-serif;--f-mono:"Geist Mono",ui-monospace,monospace}
@media (prefers-color-scheme:light){:root{color-scheme:light;--bg:#F2F0EA;--ink:#17171A;--ink2:#4D4A44;--ink3:#837F77;--line:#DCD8CE;--sheet:#E9E6DD;--up:#0F9A63;--dn:#E2401F;--nu:#8A867E}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.75 var(--f-sans);-webkit-font-smoothing:antialiased}
a{color:inherit}main,header,footer{max-width:calc(760px + 2 * var(--gx));margin:0 auto;padding-left:var(--gx);padding-right:var(--gx)}
header{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-top:18px;padding-bottom:18px}
.lg{display:inline-flex;align-items:center;gap:8px;font:600 13px/1 var(--f-mono);letter-spacing:.14em;text-decoration:none}.lg svg{width:22px;height:22px}
.lang{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:3px;font:500 12px/1 var(--f-mono)}
.lang a,.lang b{padding:6px 11px;border-radius:999px;text-decoration:none}.lang b{background:var(--ink);color:var(--bg);font-weight:600}.lang a{color:var(--ink3)}.lang a:hover{color:var(--ink)}
.mono{font:500 11.5px/1.6 var(--f-mono);letter-spacing:.06em;color:var(--ink3);text-transform:uppercase}
.crumb{margin:22px 0 0}.crumb a{text-decoration:none;border-bottom:1px solid var(--line)}.crumb a:hover{color:var(--ink)}
h1{font:700 clamp(30px,6vw,46px)/1.15 var(--f-head);letter-spacing:-.01em;margin:10px 0 4px}
h1.long{font-size:clamp(25px,4.4vw,34px);line-height:1.3}
.sub{color:var(--ink3);margin:0 0 18px;font-size:15px}
h2{font:650 19px/1.4 var(--f-head);margin:0 0 10px}
.lean{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:18px 0 10px}
.pill{display:inline-flex;align-items:center;gap:7px;font:600 13px/1 var(--f-sans);padding:7px 12px 7px 10px;border-radius:999px;border:1px solid currentColor}
.pill:before{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}
.pill.up{color:var(--up)}.pill.dn{color:var(--dn)}.pill.nu{color:var(--nu)}
.fig{display:block;margin:0 0 22px;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:#060607;transition:transform .3s cubic-bezier(.3,1.5,.5,1)}.fig:hover{transform:translateY(-2px)}.fig img{display:block;width:100%;height:auto}
.read{font:500 clamp(18px,2.6vw,21px)/1.65 var(--f-sans);margin:0 0 22px}
.cta{display:inline-flex;align-items:center;gap:8px;background:var(--ink);color:var(--bg);text-decoration:none;font:600 14px/1 var(--f-sans);padding:13px 18px;border-radius:999px;transition:transform .25s cubic-bezier(.3,1.6,.5,1)}
.cta:hover{transform:translateY(-2px)}.cta:active{transform:scale(.96)}
section{border-top:1px solid var(--line);padding:26px 0 6px;margin-top:30px}
.items{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:22px 28px;margin:4px 0 0;padding:0;list-style:none}
.items li{min-width:0}.items .v{font:700 clamp(22px,3.4vw,28px)/1.25 var(--f-head);margin:4px 0 4px;overflow-wrap:anywhere}.items .v.up{color:var(--up)}.items .v.dn{color:var(--dn)}
.items p{margin:0;color:var(--ink2);font-size:14.5px;line-height:1.65}
p{margin:0 0 14px}.dim{color:var(--ink2)}
ul.list{margin:0;padding:0;list-style:none}ul.list li{padding:14px 0;border-bottom:1px solid var(--line)}ul.list li:last-child{border-bottom:0}
ul.list a.t{font-weight:600;text-decoration:none}ul.list a.t:hover{text-decoration:underline}
ul.list .pill{font-size:11.5px;padding:4px 9px 4px 8px;margin-right:8px;vertical-align:2px}ul.list .pill:before{width:6px;height:6px}
ul.list p{margin:6px 0 0;color:var(--ink2);font-size:15px}
ul.pts{margin:0 0 8px;padding-left:1.15em}ul.pts li{margin:0 0 8px;color:var(--ink2)}
.src{font-size:13.5px;color:var(--ink3)}
.pn{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}.pn a{text-decoration:none}.pn a:hover{text-decoration:underline}
.f{border-top:1px solid var(--line);padding:20px 0 0;margin-top:22px}.f h3{font:600 16px/1.45 var(--f-sans);margin:0 0 6px}
footer{padding-top:36px;padding-bottom:48px;color:var(--ink3);font-size:13.5px}footer a{color:var(--ink2)}
@media (prefers-reduced-motion:reduce){.cta,.fig{transition:none}}"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500..700&family=Geist:wght@400..600&family=Geist+Mono:wght@500;600&family=Noto+Sans+TC:wght@400..700&display=swap">')


def dzh(d):
    return '%d/%d/%d' % (int(d[:4]), int(d[5:7]), int(d[8:10]))


def den(d):
    return '%s %d, %s' % (_MON[int(d[5:7]) - 1], int(d[8:10]), d[:4])


def ld(graph):
    s = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, separators=(',', ':'))
    return '<script type="application/ld+json">%s</script>' % s.replace('</', '<\\/')


def shell(en, path_zh, path_en, title, desc, body, graph, og=None):
    """一頁的外框。path_zh／path_en 是兩個語言的網址（不含網域，結尾斜線）；沒有另一個語言的版本就傳 None"""
    me = path_en if en else path_zh
    alt = ''.join('<link rel="alternate" hreflang="%s" href="%s%s">' % (hl, SITE, p) for hl, p in (('zh-Hant', path_zh), ('en', path_en)) if p)
    if path_zh and path_en: alt += '<link rel="alternate" hreflang="x-default" href="%s%s">' % (SITE, path_en)
    up = '../' * me.count('/')   # 回到網站根目錄的相對路徑
    if en: lang = ('<a href="%s%s" hreflang="zh-Hant">中</a>' % (up, path_zh) if path_zh else '') + '<b>EN</b>'
    else: lang = '<b>中</b>' + ('<a href="%s%s" hreflang="en">EN</a>' % (up, path_en) if path_en else '')
    return ('<!doctype html><html lang="%s"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            '<title>%s</title><meta name="description" content="%s"><link rel="canonical" href="%s%s">%s'
            '<meta property="og:type" content="article"><meta property="og:site_name" content="Daybreak"><meta property="og:title" content="%s"><meta property="og:description" content="%s">'
            '<meta property="og:url" content="%s%s"><meta property="og:image" content="%s"><meta name="twitter:card" content="summary_large_image">'
            '<meta name="theme-color" content="#F2F0EA" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#060607" media="(prefers-color-scheme: dark)">'
            '<link rel="icon" href="%sassets/favicon.svg" type="image/svg+xml">%s<style>%s</style>%s</head><body>'
            '<header><a class="lg" href="%sapp/%s">%sDAYBREAK</a><nav class="lang" aria-label="%s">%s</nav></header><main>%s</main>'
            '<footer>%s</footer></body></html>') % (
        'en' if en else 'zh-Hant', esc(title), esc(desc), SITE, me, alt, esc(title), esc(desc), SITE, me, og or SITE + 'assets/og-en.png?v=20261112',
        up, FONTS, CSS, ld(graph), up, '?lang=en' if en else '?lang=zh', LOGO, 'Language' if en else '語言', lang, body, footer(en, up))


def footer(en, up):
    if en:
        return ('Daybreak, by Aron. Code computes every number; AI only explains them. Daybreak makes no trade calls; readings are for information only.<br>'
                '<a href="%sapp/?lang=en">Daybreak app</a> · <a href="%sen/charts/">All charts</a> · <a href="%sen/brief/">Daily briefs</a> · <a href="%scase-study/en/">Case study</a>') % (up, up, up, up)
    return ('Daybreak，Aron 製作。數字由程式計算，AI 只負責解釋；不給交易建議，判讀僅供參考。<br>'
            '<a href="%sapp/?lang=zh">打開 Daybreak</a> · <a href="%scharts/">所有圖</a> · <a href="%sbrief/">每日簡報</a> · <a href="%scase-study/">Case study</a>') % (up, up, up, up)


def pill(lean, en):
    if lean not in TN and lean not in LEAN_CLS: return ''
    t = TN.get(lean) or {'bull': TN['up'], 'bear': TN['down'], 'neutral': TN['neu']}[lean]
    return '<span class="pill %s">%s</span>' % (LEAN_CLS[lean], t[1 if en else 0])


def crumbs(graph_id, items):
    return {'@type': 'BreadcrumbList', '@id': graph_id, 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': SITE + p} for i, (n, p) in enumerate(items)]}


# ---------- 每張圖一頁 ----------
IMG_DIR = None


def img(k, en):
    """那張圖的靜態小圖（部署時從 Release「chart-img」解開到 charts-img/），有就回傳網站根目錄起的路徑（帶日期，換日就換網址）"""
    rel = 'charts-img/%s/%s.jpg' % ('en' if en else 'zh', k)
    return (rel + '?v=' + DATE) if IMG_DIR and os.path.exists(os.path.join(os.path.dirname(IMG_DIR), rel)) else None


def how(k, en):
    """how.json：圖上／怎麼看／小心（英文是 What／Reading／Caveat 直接接內文）"""
    out = {}
    for s in (HOW.get(k) or {}).get('he' if en else 'hz') or []:
        if en:
            m = re.match(r'^(What|Reading|Caveat)(.*)$', s, re.S)
            if m: out[{'What': 'on', 'Reading': 'read', 'Caveat': 'care'}[m[1]]] = m[2].strip()
        else:
            m = re.match(r'^(圖上|怎麼看|小心)：(.*)$', s, re.S)
            if m: out[{'圖上': 'on', '怎麼看': 'read', '小心': 'care'}[m[1]]] = m[2].strip()
    return out


def chart_page(c, en):
    k = c['k']; pid = CHART_PG[k]; q = PG[pid]; up = '../../../' if en else '../../'
    nm = geo.name(c, en); other = c.get('zh') if en else c.get('en')
    lean = LEANS.get(k); prev = PREV.get(k)
    rd = geo.read(c, en)
    say = c.get('say') or {}
    pz = 'en/charts/%s/' % k if en else 'charts/%s/' % k
    b = ['<p class="mono crumb"><a href="%s%s">%s</a> / <a href="%s%s#%s">%s</a></p>' % (up, 'en/charts/' if en else 'charts/', 'All charts' if en else '所有圖', up, 'en/charts/' if en else 'charts/', pid, esc(q['en'] if en else q['zh'])),
         '<p class="mono" style="margin:14px 0 0">%s</p>' % esc(q['qe'] if en else q['qz']),
         '<h1>%s</h1>' % esc(nm)]
    if other and other != nm: b.append('<p class="sub">%s</p>' % esc(other))
    chg = ''
    if lean and prev and prev != lean and prev in TN and lean in TN:
        chg = ('<span class="mono">Changed today from %s</span>' % TN[prev][1].lower()) if en else ('<span class="mono">今天由%s轉%s</span>' % (TN[prev][0], TN[lean][0]))
    b.append('<div class="lean">%s<span class="mono">%s</span>%s</div>' % (pill(lean, en), ('%s close' % den(DATE)) if en else ('%s 收盤' % dzh(DATE)), chg))
    if rd: b.append('<p class="read">%s</p>' % esc(re.sub(r'^(偏多|偏空|中性)：|^(Bullish|Bearish|Neutral): ', '', rd)))   # 膠囊已經寫了表態；有限定（「偏多（長線）：」）的照留
    im = img(k, en)
    if im:   # 2026-11-20 靜態小圖（chart_img.js 用分享模式截的），點了打開互動圖
        b.append('<a class="fig" href="%sapp/?k=%s&amp;lang=%s"><img src="%s%s" width="1200" height="675" alt="%s" decoding="async"></a>' % (up, k, 'en' if en else 'zh', up, im, esc('%s · %s' % (nm, ('%s close' % den(DATE)) if en else ('%s 收盤' % dzh(DATE))))))
    b.append('<a class="cta" href="%sapp/?k=%s&amp;lang=%s">%s →</a>' % (up, k, 'en' if en else 'zh', 'Open the interactive chart' if en else '打開互動圖'))
    its = [it for it in (say.get('items') or []) if (it.get('ve') if en else it.get('vz'))]
    if its:
        li = []
        for it in its:
            tone = {'up': ' up', 'down': ' dn'}.get(it.get('tone'), '')
            li.append('<li><div class="mono">%s</div><div class="v%s">%s</div><p>%s</p></li>' % (esc(it.get('ke' if en else 'kz') or ''), tone, esc(it.get('ve' if en else 'vz') or ''), esc(it.get('de' if en else 'dz') or '')))
        b.append('<section><h2>%s</h2><ul class="items">%s</ul></section>' % ('Readings' if en else '讀數', ''.join(li)))
    h = how(k, en); d = c.get('de' if en else 'dz') or ''
    sec = []
    if d and d != rd: sec.append('<h2>%s</h2><p>%s</p>' % ('What this chart shows' if en else '這張圖在看什麼', esc(d)))
    if h.get('on'): sec.append('<p class="dim">%s</p>' % esc(h['on']))
    if h.get('read'): sec.append('<h2 style="margin-top:22px">%s</h2><p>%s</p>' % ('How to read it' if en else '怎麼看', esc(h['read'])))
    if h.get('care'): sec.append('<h2 style="margin-top:22px">%s</h2><p>%s</p>' % ('Caveats' if en else '要小心', esc(h['care'])))
    src = c.get('srce' if en else 'src')
    if src: sec.append('<p class="src">%s%s</p>' % ('Source: ' if en else '資料來源：', esc(src)))
    if sec: b.append('<section>%s</section>' % ''.join(sec))
    sib = [x for x in geo.charts(pid) if x['k'] != k]
    if sib:
        b.append('<section><h2>%s</h2><ul class="list">%s</ul></section>' % (('More on “%s”' % q['qe']) if en else '同一頁的其他圖：%s' % q['qz'],
                 ''.join('<li>%s<a class="t" href="../%s/">%s</a></li>' % (pill(LEANS.get(x['k']), en), x['k'], esc(geo.name(x, en))) for x in sib)))
    title = '%s · %s · Daybreak' % (nm, TN[lean][1] if lean in TN else 'Bitcoin') if en else '%s · %s · Daybreak 比特幣' % (nm, TN[lean][0] if lean in TN else '比特幣')
    desc = rd or d
    pg_id = SITE + pz + '#page'
    graph = [WEBSITE, PERSON,
             {'@type': 'Article', '@id': pg_id, 'url': SITE + pz, 'headline': '%s: %s' % (nm, rd)[:110] if rd else nm, 'description': desc, 'inLanguage': 'en' if en else 'zh-Hant',
              'datePublished': DATE, 'dateModified': DATE, 'author': {'@id': PERSON['@id']}, 'publisher': {'@id': PERSON['@id']}, 'isPartOf': {'@id': WEBSITE['@id']},
              'about': [{'@type': 'Thing', 'name': 'Bitcoin', 'sameAs': 'https://en.wikipedia.org/wiki/Bitcoin'}, {'@type': 'Thing', 'name': c.get('en') or nm}]} | ({'image': SITE + im} if im else {}),
             crumbs(SITE + pz + '#crumbs', [('Daybreak', 'app/'), ('All charts' if en else '所有圖', 'en/charts/' if en else 'charts/'), (nm, pz)])]
    return shell(en, 'charts/%s/' % k, 'en/charts/%s/' % k, title, desc, ''.join(b), graph, og=(SITE + im) if im else None)


def charts_index(en):
    p = 'en/charts/' if en else 'charts/'; n = sum(1 for _ in geo.ALL)
    b = ['<p class="mono crumb">%s</p>' % (('%s close · %d charts' % (den(DATE), n)) if en else ('%s 收盤 · %d 張圖' % (dzh(DATE), n))),
         '<h1>%s</h1>' % ('Every Daybreak chart, and where it leans today' if en else 'Daybreak 每一張圖，和它今天的表態'),
         '<p class="dim">%s</p>' % esc(geo.INTRO_EN if en else geo.INTRO_ZH)]
    for q in QS:
        lead = q.get('lead_en' if en else 'lead_zh') or ''
        li = ''.join('<li>%s<a class="t" href="%s/">%s</a><p>%s</p></li>' % (pill(LEANS.get(c['k']), en), c['k'], esc(geo.name(c, en)), esc(geo.read(c, en))) for c in geo.charts(q['id']))
        b.append('<section id="%s"><p class="mono">%s</p><h2>%s</h2>%s<ul class="list">%s</ul></section>' % (q['id'], esc(q['en'] if en else q['zh']), esc(q['qe'] if en else q['qz']), ('<p class="dim">%s</p>' % esc(lead)) if lead else '', li))
    t = 'All Bitcoin charts · Daybreak' if en else '所有比特幣指標圖 · Daybreak'
    graph = [WEBSITE, PERSON, {'@type': 'CollectionPage', '@id': SITE + p + '#page', 'url': SITE + p, 'name': t, 'inLanguage': 'en' if en else 'zh-Hant', 'dateModified': DATE, 'isPartOf': {'@id': WEBSITE['@id']},
                               'author': {'@id': PERSON['@id']}}]
    return shell(en, 'charts/', 'en/charts/', t, geo.INTRO_EN if en else geo.INTRO_ZH, ''.join(b), graph)


# ---------- 每天的簡報 ----------
def archive():
    out = {}
    for f in glob.glob(os.path.join(REPO, 'data', 'archive', '20??-??-??.json')):
        d = os.path.basename(f)[:10]
        try:
            z = json.load(open(f, encoding='utf-8'))
            e = json.load(open(f[:-5] + '.en.json', encoding='utf-8')) if os.path.exists(f[:-5] + '.en.json') else None
        except Exception as ex:
            print('archive skip', d, ex); continue
        if z.get('headline'): out[d] = (z, e if e and e.get('headline') else None)
    return out


def brief_page(d, A, ds, en):
    z, e = A[d]; a = e if en else z; i = ds.index(d)
    pz, pe = 'brief/%s/' % d, ('en/brief/%s/' % d if e else None)
    me = pe if en else pz
    up = '../' * me.count('/')
    base = up + ('en/brief/' if en else 'brief/')
    b = ['<p class="mono crumb"><a href="%s">%s</a> / No.%s</p>' % (base, 'Daily briefs' if en else '每日簡報', z.get('edition') or ''),
         '<p class="mono" style="margin:14px 0 0">%s</p>' % (('%s close edition' % den(d)) if en else ('%s 收盤版' % dzh(d))),
         '<h1 class="long">%s</h1>' % esc(a['headline'])]   # 簡報頭條是一整句，字級比圖名小一號
    st = (a.get('stance') or {}).get('label')
    tone = {'cold': 'dn', 'warm': 'up'}.get((a.get('stance') or {}).get('tone'), 'nu')
    if st: b.append('<div class="lean"><span class="pill %s">%s</span></div>' % (tone, esc(st)))
    if a.get('summary'): b.append('<p class="read">%s</p>' % esc(a['summary']))
    if d == DATE: b.append('<a class="cta" href="%sapp/?lang=%s">%s →</a>' % (up, 'en' if en else 'zh', 'Open today’s Daybreak' if en else '打開今天的 Daybreak'))
    w = a.get('watch') or []
    if w:
        li = ''.join('<li><div class="mono">%s</div><div class="v">%s</div><p>%s</p></li>' % (esc(x.get('label') or ''), esc(format(x['value'], ',') if isinstance(x.get('value'), (int, float)) else str(x.get('value') or '')), esc(x.get('note') or '')) for x in w)
        b.append('<section><h2>%s</h2><ul class="items">%s</ul></section>' % ('Levels to watch' if en else '要盯的價位', li))
    for mk, m in (a.get('modules') or {}).items():
        if not isinstance(m, dict) or not (m.get('lead') or m.get('points')): continue
        nm = MOD.get(mk, (mk, mk))[1 if en else 0]
        b.append('<section><p class="mono">%s</p>%s%s</section>' % (esc(nm), ('<h2>%s</h2>' % esc(m['lead'])) if m.get('lead') else '',
                 ('<ul class="pts">%s</ul>' % ''.join('<li>%s</li>' % esc(p) for p in m['points'])) if m.get('points') else ''))
    fs = [f for f in (a.get('findings') or []) if isinstance(f, dict) and f.get('title')]
    if fs:
        h = []
        for f in fs:
            ck = f.get('chart'); link = ''
            if ck in CHART_PG: link = ' <a href="%s%s%s/">%s</a>' % (up, 'en/charts/' if en else 'charts/', ck, 'Chart →' if en else '看這張圖 →')
            h.append('<div class="f"><h3>%s %s</h3>%s%s%s</div>' % (pill(f.get('lean'), en), esc(f['title']), ('<p>%s</p>' % esc(f['what'])) if f.get('what') else '',
                     ('<p class="dim">%s</p>' % esc(f['why'])) if f.get('why') else '', ('<p class="src">%s</p>' % link.strip()) if link else ''))
        b.append('<section><h2>%s</h2>%s</section>' % ('Today’s findings' if en else '今日發現', ''.join(h)))
    cards = z.get('cards') or {}
    if cards:
        n = {k: sum(1 for v in cards.values() if (v or {}).get('lean') == k) for k in ('up', 'down', 'neu')}
        b.append('<p class="src" style="margin-top:26px">%s</p>' % (('Charts that day: %d bullish, %d bearish, %d neutral.' if en else '這一天各圖的表態：偏多 %d、偏空 %d、中性 %d。') % (n['up'], n['down'], n['neu'])))
    nav = []
    if i > 0 and (not en or A[ds[i - 1]][1]): nav.append('<a href="../%s/">← %s</a>' % (ds[i - 1], den(ds[i - 1]) if en else dzh(ds[i - 1])))
    else: nav.append('<span></span>')
    if i + 1 < len(ds) and (not en or A[ds[i + 1]][1]): nav.append('<a href="../%s/">%s →</a>' % (ds[i + 1], den(ds[i + 1]) if en else dzh(ds[i + 1])))
    b.append('<section class="pn">%s</section>' % ''.join(nav))
    t = ('Bitcoin, %s: %s' % (den(d), a['headline'])) if en else ('比特幣 %s：%s' % (dzh(d), a['headline']))
    graph = [WEBSITE, PERSON,
             {'@type': 'Article', '@id': SITE + me + '#page', 'url': SITE + me, 'headline': a['headline'][:110], 'description': a.get('summary') or a['headline'], 'inLanguage': 'en' if en else 'zh-Hant',
              'datePublished': d, 'dateModified': (z.get('written_utc') or d)[:10], 'author': {'@id': PERSON['@id']}, 'publisher': {'@id': PERSON['@id']}, 'isPartOf': {'@id': WEBSITE['@id']},
              'about': {'@type': 'Thing', 'name': 'Bitcoin', 'sameAs': 'https://en.wikipedia.org/wiki/Bitcoin'}},
             crumbs(SITE + me + '#crumbs', [('Daybreak', 'app/'), ('Daily briefs' if en else '每日簡報', 'en/brief/' if en else 'brief/'), (dzh(d) if not en else den(d), me)])]
    return shell(en, pz, pe, t, a.get('summary') or a['headline'], ''.join(b), graph)


def brief_index(A, ds, en):
    li = []
    for d in reversed(ds):
        z, e = A[d]
        if en and not e: continue
        a = e if en else z
        st = (a.get('stance') or {}).get('label') or ''
        li.append('<li><div class="mono">%s · No.%s%s</div><a class="t" href="%s/">%s</a></li>' % (den(d) if en else dzh(d), z.get('edition') or '', (' · ' + esc(st)) if st else '', d, esc(a['headline'])))
    t = 'Daily Bitcoin briefs · Daybreak' if en else '比特幣每日簡報 · Daybreak'
    b = '<p class="mono crumb">%s</p><h1>%s</h1><p class="dim">%s</p><section><ul class="list">%s</ul></section>' % (
        ('%d editions' % len(li)) if en else ('%d 期' % len(li)), 'Daily Bitcoin briefs' if en else '每日簡報',
        'One close-of-day reading every day: headline, overall lean, levels to watch and what each part of the market says.' if en else '每天收盤後一份判讀：頭條、整體偏向、要盯的價位，和市場各部分怎麼說。', ''.join(li))
    p = 'en/brief/' if en else 'brief/'
    graph = [WEBSITE, PERSON, {'@type': 'CollectionPage', '@id': SITE + p + '#page', 'url': SITE + p, 'name': t, 'inLanguage': 'en' if en else 'zh-Hant', 'dateModified': ds[-1], 'isPartOf': {'@id': WEBSITE['@id']}}]
    return shell(en, 'brief/', 'en/brief/', t, t, b, graph)


def write(out, path, s):
    p = os.path.join(out, path, 'index.html'); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(s)


def main():
    global IMG_DIR
    ap = argparse.ArgumentParser(); ap.add_argument('--out'); ap.add_argument('--img-list', action='store_true'); o = ap.parse_args()
    if o.img_list:   # chart_img.js 要截的圖：分享模式打得開的（不能放大的清單型圖沒有分享模式）
        print(json.dumps([c['k'] for c in geo.ALL if not c.get('nofx') and not c.get('na')])); return
    out = os.path.abspath(o.out); urls = []   # (zh 網址, en 網址, lastmod)
    IMG_DIR = os.path.join(out, 'charts-img')
    for c in geo.ALL:
        for en in (False, True): write(out, ('en/charts/%s' if en else 'charts/%s') % c['k'], chart_page(c, en))
        urls.append(('charts/%s/' % c['k'], 'en/charts/%s/' % c['k'], DATE))
    for en in (False, True): write(out, 'en/charts' if en else 'charts', charts_index(en))
    urls.append(('charts/', 'en/charts/', DATE))
    A = archive(); ds = sorted(A)
    for d in ds:
        write(out, 'brief/%s' % d, brief_page(d, A, ds, False))
        if A[d][1]: write(out, 'en/brief/%s' % d, brief_page(d, A, ds, True))
        urls.append(('brief/%s/' % d, 'en/brief/%s/' % d if A[d][1] else None, d))
    for en in (False, True): write(out, 'en/brief' if en else 'brief', brief_index(A, ds, en))
    urls.append(('brief/', 'en/brief/', ds[-1] if ds else DATE))
    sm = os.path.join(out, 'sitemap.xml'); s = open(sm, encoding='utf-8').read()
    add = []
    for z, e, lm in urls:
        alt = ''.join('<xhtml:link rel="alternate" hreflang="%s" href="%s%s"/>' % (hl, SITE, p) for hl, p in (('zh-Hant', z), ('en', e)) if p and e)
        for p in (z, e):
            if p: add.append('<url><loc>%s%s</loc><lastmod>%s</lastmod>%s</url>\n' % (SITE, p, lm, alt))
    s = s.replace('</urlset>', ''.join(add) + '</urlset>')
    open(sm, 'w', encoding='utf-8').write(s)
    print('pages: %d charts ×2, %d briefs (%d en), %d sitemap urls added -> %s' % (len(geo.ALL), len(ds), sum(1 for d in ds if A[d][1]), len(add), out))


if __name__ == '__main__':
    main()
