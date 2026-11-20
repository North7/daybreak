# -*- coding: utf-8 -*-
"""首頁的建置（2026-11-11 起取代舊版；舊版 2026-11-17 從倉庫刪除，讀數全部由 reads.py 產生）：
1. 從 data/latest.json、data/notes*.json 組出每一頁、每張圖要用的資料（site_data.py 和各頁的 *_data.py）。
3. 寫 data/next.js（window.DAYBREAK_NEXT），並把 page.html 寫成 app/index.html（只換資料檔的版本號）。
   2026-11-20 根網址改放介紹頁（pipeline/intro/build.py 寫根目錄的 index.html），數據頁搬到 /app/。
   2026-11-15 瘦身：卡片多的頁（週期、價位、賣壓、買盤、槓桿）的卡片另外寫成 data/next-<頁>.js，點到那一頁才載（頁面閒下來時也會先在背景載）。
   data/next.js 裡這幾頁只留每張卡的代號、名稱這些小欄位（ops/post/next_shot.py 的目錄照樣讀得到），和每頁的主圖（桌機分頁卡片上的小圖要用）。
用法：python3 pipeline/next/build.py（舊的 --no-interp 參數照收，不再有作用）
每日資料流程（daily.yml）和日報推送後（share.yml）都會跑一次。"""
import json, os, sys, datetime as dt, bisect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import subprocess, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(REPO, 'data', 'latest.json'), encoding='utf-8'))
N = json.load(open(os.path.join(REPO, 'data', 'notes.json'), encoding='utf-8'))
# 2026-11-19 使用者同意 Gemini 的建議：發現與追蹤的文字裡出現「2026-11-16-1」這種原始代號，讀者看不懂。顯示時換成「11/16 第 1 則發現」／"finding 1 of Nov 16"
#   （id、since 欄位本身不動；notes_lint 也會擋，這裡是寫漏時的保險）
import re as _re
_RID = _re.compile(r'( ?)(?<![\d-])(20\d\d)-(\d\d)-(\d\d)-(\d{1,2})(?![\d-])( ?)')   # 中文：前面的空格留著（數字前），後面的拿掉（換成的字以中文結尾）
_MON = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
def _rid(o, en, k=''):
    if isinstance(o, dict): return {k_: (v if k_ in ('id', 'since') else _rid(v, en, k_)) for k_, v in o.items()}
    if isinstance(o, list): return [_rid(v, en, k) for v in o]
    if isinstance(o, str): return _RID.sub((lambda m: '%sfinding %d of %s %d%s' % (m[1], int(m[5]), _MON[int(m[3]) - 1], int(m[4]), m[6])) if en else (lambda m: '%s%d/%d 第 %d 則發現' % (m[1], int(m[3]), int(m[4]), int(m[5]))), o)
    return o
N = _rid(N, False)
# 2026-11-18 使用者：「右邊寫 17 日收盤版，但看起來判讀內容沒變」。整期一起換（2026-11-06 的規則，舊版 app.js 的 HELD；新版漏了）：
#   資料管線先寫好新一天的 latest.json，日報判讀約 15–30 分鐘後才提交。這段時間判讀還是上一期，就整期沿用上一份數字（latest.prev.json，
#   pipeline/build.py 換日前存的），日期、價格、卡片都和判讀對得上；判讀一提交（share.yml 重建）就整期換新
HELD = None
try:
    _pf = os.path.join(REPO, 'data', 'latest.prev.json')
    if N.get('date') != L['meta']['bar_date'] and os.path.exists(_pf):
        _P = json.load(open(_pf, encoding='utf-8'))
        if _P['meta']['bar_date'] == N.get('date'): HELD = L['meta']['bar_date']; L = _P
except Exception as e: print('held check failed', e)
print('held', HELD and '%s data waiting for notes; showing %s' % (HELD, L['meta']['bar_date']))
EP = dt.date(1970, 1, 1); dn = lambda s: (dt.date.fromisoformat(s) - EP).days; ymd = lambda n: (EP + dt.timedelta(n)).isoformat()

dw = L['cycle']['dawn']; R = dw['rows']                       # [day, heat, price, stage, dir]
days = [r[0] for r in R]
def align(rows, col, tol=6):
    xs = [r[0] for r in rows]; out = []
    for d in days:
        k = bisect.bisect_right(xs, d) - 1
        out.append(rows[k][col] if k >= 0 and d - xs[k] <= tol and rows[k][col] is not None else None)
    return out
hn = L['onchain']['hnupl']['rows']                             # [day, price, lth, sth]
fg = L['flows']['fng_hist']['rows']                            # [day, price, value]
fu = L['deriv']['fund_hist']['rows']                           # [day, price, 7d avg annualized %]
st = L['flows']['stables']['rows']                             # [day, usd_b]
sm = {r[0]: r[1] for r in st}
def p30(d):
    for k in (30, 31, 29, 32, 28):
        if sm.get(d - k): return round((sm[d] / sm[d - k] - 1) * 100, 2)
    return None
stab = [[r[0], p30(r[0])] for r in st]; stab = [r for r in stab if r[1] is not None]
px = [r[2] for r in R]
mayer = [round(px[i] / (sum(px[i - 39:i + 1]) / 40), 3) if i >= 39 else None for i in range(len(px))]
wk = dict(t0=days[0], n=len(days), heat=[r[1] for r in R], px=px, stg=[r[3] for r in R], dir=[r[4] for r in R],
          nupl=[None if v is None else round(v, 3) for v in align(hn, 3)], fng=align(fg, 2), fund=[None if v is None else round(v, 1) for v in align(fu, 2)],
          stab=align(stab, 1), mayer=mayer)
assert all(days[i + 1] - days[i] == 7 for i in range(len(days) - 1)), 'weekly step'

u = L['chips']['viz']['urpd']; W = u.get('width', 2000); c = L['price']['bar']['c']
band = sorted([b for b in u['band'] if 50000 <= b[0] < 126000])
def win(lo, hi, k, more):
    best = None
    for i in range(len(band) - k + 1):
        w = band[i:i + k]
        if w[0][0] < lo or w[-1][0] + W > hi: continue
        t = sum(b[1] for b in w)
        if best is None or (t > best[2] if more else t < best[2]): best = [w[0][0], w[-1][0] + W, t]
    return best
cur = int(c // W) * W
thick = win(c * 0.8, c * 1.25, 5, True)
thin = win(c * 0.8, min(cur, 10**9), 4, False) if thick[0] > c else win(max(thick[1], cur + W), c * 1.2, 4, False)

sr = [[r[0], r[1]] for r in L['chips']['stress']['rows'][-30:]]
if sr[-1][0] == dn(L['meta']['bar_date']): sr[-1][1] = round(c)
d30 = sr
lv = L['cycle']['levels']; w50 = lv['w50']
lvrows = [[r[0], r[1], r[2], r[4], r[5], r[6]] for r in lv['rows']]   # day, price, sma200, w50, sth cost, true market mean
etf = [[e['d'], e['musd'], 1 if e.get('partial') else 0] for e in L['flows']['etf']]
full = [e for e in L['flows']['etf'] if not e.get('partial')]
sc = L['flows']['stables']; stg = L['cycle']['stage']; fl = L['chips']['flow']
brk = [b for b in w50['breaks'] if b.get('weeks') is not None]
import oc_data
E_ = _rid(json.load(open(os.path.join(REPO, 'data', 'notes.en.json'), encoding='utf-8')), True) if os.path.exists(os.path.join(REPO, 'data', 'notes.en.json')) else None
import site_data
SITE = site_data.build(L, N, E_, dn)
import say_data, reads
_NE = E_
print('reads', reads.apply(SITE['chapters'], L, N, _NE))   # 2026-11-17 新版自己產生的讀數（reads.py），做好的頁不再用舊版的
print('say', say_data.attach(SITE['chapters'], L))
def _qa_tally():
    """㊵ 今天頁六張概覽卡的偏向：數那一頁每張圖「我們的看法」的方向（和每段答案同一套：AI 判讀的 lean 已經蓋上去），偏空多就偏空、偏多多就偏多、打平是中性"""
    CH = {ch['id']: ch for ch in SITE['chapters']}; out = {}
    for g in (CH.get('today') or {}).get('groups') or []:
        for c in g.get('charts') or []:
            if 'qa' not in c: continue
            n = {}
            for g2 in (CH.get(c.get('go')) or {}).get('groups') or []:
                for c2 in g2.get('charts') or []:
                    y = c2.get('say') or {}
                    if y.get('copy'): continue
                    v = next((q for q in y.get('items') or [] if q.get('view')), None)
                    if v: n[v['tone']] = n.get(v['tone'], 0) + 1
            if n and not c['qa'].get('nz'):
                c['qa']['n'] = n; c['qa']['tone'] = 'down' if n.get('down', 0) > n.get('up', 0) else 'up' if n.get('up', 0) > n.get('down', 0) else 'neu'
            out[c['k']] = n
    return out
print('qa', _qa_tally())
def _lean_flip():
    """2026-11-18 偏向翻牌（page.html ㉟ 1）：data/leans.json 記住每個資料日最後一次的偏向。換了資料日，前一天的那份變成「昨天」；
    今天和昨天不一樣的卡，看法那一項帶 pt＝昨天的偏向、pd＝昨天的資料日，頁面上的偏向膠囊從昨天翻到今天。同一天重跑（share.yml）不動「昨天」"""
    p = os.path.join(REPO, 'data', 'leans.json'); bd = L['meta']['bar_date']
    try: S = json.load(open(p, encoding='utf-8'))
    except Exception: S = {}
    vw = {}
    for ch in SITE['chapters']:
        for g in ch.get('groups') or []:
            for c in g.get('charts') or []:
                v = next((q for q in (c.get('say') or {}).get('items') or [] if q.get('view')), None)
                if v: vw[c['k']] = v
    if S.get('date') != bd: S = dict(prev_date=S.get('date'), prev=S.get('today') or {}) if S.get('date') and S['date'] < bd else {}
    S.update(date=bd, today={k: v['tone'] for k, v in vw.items()})
    json.dump(S, open(p, 'w', encoding='utf-8'), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    P = S.get('prev') or {}; n = 0
    for k, v in vw.items():
        if P.get(k) and P[k] != v['tone']: v['pt'] = P[k]; v['pd'] = S.get('prev_date'); n += 1
    return dict(date=bd, prev=S.get('prev_date'), flips=n)
print('lean flip', _lean_flip() if not HELD else 'skipped (held)')   # 沿用上一期時不動 leans.json，免得把新一天的紀錄蓋回前一天
def _sigs():
    """2026-11-18 訊號清單（page.html ㉟ 6）：右下角的訊號提示點開是今天全部的訊號，其他頁的卡片資料是之後才載入的，所以清單先放在 next.js"""
    out = []
    for ch in SITE['chapters']:
        for g in ch.get('groups') or []:
            for c in g.get('charts') or []:
                for q in c.get('sig') or []: out.append(dict(p=ch['id'], k=c['k'], zh=c.get('zh'), en=c.get('en'), tz=q['tz'], te=q['te'], new=q.get('new', 0)))
    return out
SIGS = _sigs(); print('sigs', len(SIGS))
# 2026-11-16 舊版（classic.html）對外下線：舊網址 #頁/代號 的「代號」是舊版的面板（pn-…）或圖（c-…），對到新版的圖代號，頁面讀到就轉過去（page.html ㉝）
def _old_map():
    have = {c['k'] for ch in SITE['chapters'] for g in ch.get('groups') or [] for c in g.get('charts') or []}
    out = {a: k for a, k in json.load(open(os.path.join(HERE, 'old.json'), encoding='utf-8')).items() if k in have}   # 2026-11-17 從舊版凍結的對照（舊面板、舊圖 id、別名 → 新版圖代號）
    for k in have: out.setdefault(k, k)   # 舊版和新版同名的
    return out
OLD = _old_map(); print('old links', len(OLD))
import pm_data
try:   # 2026-11-16 頁尾「資料來源」要寫每天從 Bitview 抓幾條序列：直接數 bitview.COLS，不寫死
    sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); import bitview as _bv; BVN = len(_bv.COLS)
except Exception as e: print('bitview count failed', e); BVN = None
D = dict(
    site=SITE, pm=pm_data.build(L), bvn=BVN, old=OLD, sigs=SIGS,
    date=L['meta']['bar_date'], issue=N.get('edition'), price=round(c), chg=L['price']['bar']['chg_pct'],
    headline=N['headline'], summary=N['summary'], stance=N.get('stance'), leads={k: m.get('lead') for k, m in N['modules'].items()},
    dawn=dict(heat=dw['heat'], stage=dw['stage'], weeks=dw['stage_weeks'], heat4=dw['heat4']),
    _w50=dict(date=w50['date'], close=w50['close'], ma=w50['ma'], dist=w50['dist_pct'], above=w50['above'], prev_run=(w50.get('cross') or {}).get('prev_run'), live=w50.get('live'),
                        n=len(brk), fast=sum(1 for b in brk if b['weeks'] <= 2), slow=[b['weeks'] for b in brk if b['weeks'] >= 26], slow_y=[b['date'][:4] for b in brk if b['weeks'] >= 26]),
    stage=dict(name=stg['stage'], since=stg['since'], run=stg['above_rising_run'], sma200=round(stg['sma200'])),
    stabNow=dict(usd=sc['usd_b'], p30=sc['chg30_pct'], d30=sc['chg30_usd_b'], pct=sc['pct30']), etf5=round(sum(e['musd'] for e in full[-5:])),
    now=dict(sthProfit=fl['sth_in_profit_pct']['value'], fund=L['deriv']['fund_hist']['value'], dvol=L['deriv']['dvol']['value'], fng=L['flows']['fng_hist']['value'],
             mvrvPrior=L['cycle']['cm']['mvrv_vs_prior'], k075=L['cycle']['cm']['k075_price'], ladder1=L['exit']['framework']['ladder'][0]),
)
print('urpd thick', thick, 'thin', thin, '| w50', {k: v for k, v in D['_w50'].items() if k != 'live'}, D['_w50']['live']); D.pop('_w50')   # 2026-11-16 頁面不再讀 wk、lv、stab、etf、urpd、d30、w50、marks、th（只有設計提案的程式在讀，已刪）；日誌照舊印
print('stage', D['stage'], '| stab', D['stabNow'], '| etf5', D['etf5'], '| now', D['now'], '| dawn', D['dawn'])
LZ_MIN = 20000   # 卡片資料超過這個大小（位元組）的頁才拆出去
STUB = ('k', 'zh', 'en', 'nofx', 'na', 'go', 'sim', 'wide')   # 留在 next.js 的欄位：next_shot 的目錄、頁面切換前用不到其他欄位
keep = set()
for ch in D['site']['chapters']:
    gs = ch.get('groups') or []; gj = json.dumps(gs, ensure_ascii=False, separators=(',', ':'))
    if ch['id'] == 'today' or ch.get('todo') or len(gj) < LZ_MIN: continue
    h = ch.get('hero') or [0, 0]; fn = 'next-%s.js' % ch['id']; keep.add(fn)
    open(os.path.join(REPO, 'data', fn), 'w', encoding='utf-8').write('(window.DAYBREAK_CH=window.DAYBREAK_CH||{})[%s]=%s;\n' % (json.dumps(ch['id']), gj))
    ch['lz'] = hashlib.sha1(gj.encode('utf-8')).hexdigest()[:10]
    ch['groups'] = [dict({k: v for k, v in g.items() if k != 'charts'}, charts=[c if (gi, ci_) == tuple(h) else dict({k: c[k] for k in STUB if k in c}, stub=1) for ci_, c in enumerate(g['charts'])]) for gi, g in enumerate(gs)]
for fn in os.listdir(os.path.join(REPO, 'data')):   # 頁改名或不再拆出去時，舊檔一起清掉
    if fn.startswith('next-') and fn.endswith('.js') and fn not in keep: os.remove(os.path.join(REPO, 'data', fn))
js = json.dumps(D, ensure_ascii=False, separators=(',', ':'))
open(os.path.join(REPO, 'data', 'next.js'), 'w', encoding='utf-8').write('window.DAYBREAK_NEXT=' + js + ';\n')
print('split:', ', '.join('%s %d KB' % (f, os.path.getsize(os.path.join(REPO, 'data', f)) // 1024) for f in sorted(keep)))
ver = hashlib.sha1(js.encode('utf-8')).hexdigest()[:10]
page = open(os.path.join(HERE, 'page.html'), encoding='utf-8').read(); assert page.count('../data/next.js?v=__V__') == 1
# 2026-11-19 SEO（使用者同意 Gemini 的建議）：頁面內容全靠 JS 畫，原始 HTML 裡沒有今天的結論，爬蟲幾乎抓不到字。
#   把當期日期、頭條、摘要（中英）直接寫進 HTML（#oc-static，頁面跑起來就藏起來），另外寫 sitemap.xml
#   2026-11-20 GEO 第一批：文字版擴大成每張圖的表態和理由、加結構化資料，改由 geo.py 在介紹頁建好之後填（<!--STATIC-->、<!--LDJSON--> 兩個記號留在 HTML 裡給它換）
assert page.count('<!--STATIC-->') == 1 and page.count('<!--LDJSON-->') == 1
open(os.path.join(REPO, 'sitemap.xml'), 'w', encoding='utf-8').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    + ''.join('<url><loc>%s</loc><lastmod>%s</lastmod>%s</url>\n' % (u, lm, x) for u, lm, x in (
        ('https://daybreak.aronlab.dev/', L['meta']['bar_date'], '<changefreq>daily</changefreq><xhtml:link rel="alternate" hreflang="zh-Hant" href="https://daybreak.aronlab.dev/?lang=zh"/><xhtml:link rel="alternate" hreflang="en" href="https://daybreak.aronlab.dev/?lang=en"/>'),
        ('https://daybreak.aronlab.dev/app/', L['meta']['bar_date'], '<changefreq>daily</changefreq><xhtml:link rel="alternate" hreflang="zh-Hant" href="https://daybreak.aronlab.dev/app/?lang=zh"/><xhtml:link rel="alternate" hreflang="en" href="https://daybreak.aronlab.dev/app/?lang=en"/>'),
        ('https://daybreak.aronlab.dev/case-study/', '2026-11-19', ''), ('https://daybreak.aronlab.dev/case-study/en/', '2026-11-19', '')))
    + '</urlset>\n')
os.makedirs(os.path.join(REPO, 'app'), exist_ok=True)
open(os.path.join(REPO, 'app', 'index.html'), 'w', encoding='utf-8').write(page.replace('../data/next.js?v=__V__', '../data/next.js?v=' + ver))
print('wrote data/next.js', len(js), 'bytes; app/index.html', len(page), 'bytes; v=' + ver, '| bar', D['date'], '| notes', N.get('date'))
# 2026-11-19 介紹頁用剛寫好的 data/next*.js 重建（2026-11-20 起它就是根目錄的 index.html）；失敗只印出來，不影響數據頁，根目錄留著上一版
try:
    subprocess.run([sys.executable, os.path.join(REPO, 'pipeline', 'intro', 'build.py')], check=True)
except Exception as e:
    print('intro build failed:', e)
# 2026-11-20 GEO：數據頁和介紹頁的文字版、結構化資料，llms.txt、latest.md、latest.en.md（見 geo.py）。失敗只印出來，頁面照常上線
try:
    subprocess.run([sys.executable, os.path.join(HERE, 'geo.py')], check=True)
except Exception as e:
    print('geo build failed:', e)
