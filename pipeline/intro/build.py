# -*- coding: utf-8 -*-
"""介紹頁（/intro/）的建置。2026-11-19 新增。
讀首頁已經建好的 data/next.js、data/next-*.js、data/leans.json、data/notes.en.json，寫出：
  data/intro.js     window.DAYBREAK_INTRO：每張圖的表態、資料種類、所屬的頁、中英圖名（第 02 段掃描用）、極簡小圖，加上當期的期數、收盤、頭條、判讀（中英）
  index.html        根目錄（2026-11-20 起根網址就是介紹頁）：pipeline/intro/page.html 換上資料檔的版本號
  intro/index.html 是固定的轉址檔（舊的 /intro/ 連結轉到 /?intro），不在這裡寫
圖的張數、每頁幾張、每種資料幾張都從資料算，不寫死（使用者：「圖的數量可能會一直增加」）。
用法：python3 pipeline/intro/build.py（pipeline/next/build.py 跑完會接著呼叫；失敗不影響首頁）"""
import json, glob, math, os, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
D_ = lambda *p: os.path.join(REPO, 'data', *p)

def ld(path):
    s = open(path, encoding='utf-8').read()
    return json.loads(s[s.index('=') + 1:s.rindex('}') + 1])

NX = ld(D_('next.js'))
PAGES = {c['id']: c['groups'] for c in NX['site']['chapters']}
for f in glob.glob(D_('next-*.js')):
    t = open(f, encoding='utf-8').read()
    PAGES[t[t.index('["') + 2:t.index('"]')]] = json.loads(t[t.index(']=') + 2:].rstrip().rstrip(';'))
ORDER = ['today', 'cycle', 'lv', 'sell', 'buy', 'lev', 'exit']
ORDER = [p for p in ORDER if p in PAGES] + [p for p in PAGES if p not in ORDER]
PGN = {c['id']: [c.get('zh') or c['id'], c.get('en') or c['id']] for c in NX['site']['chapters']}
LEANS = json.load(open(D_('leans.json'), encoding='utf-8')).get('today', {})
try:
    EN = json.load(open(D_('notes.en.json'), encoding='utf-8'))
except Exception:
    EN = {}
if EN.get('date') != NX.get('date'):   # 英文判讀還沒跟上這一期時不要拿上一期的
    EN = {}

# 六種資料：先看資料來源的字，再看所在的頁（介紹頁用的粗分，不影響首頁）
LAY = [('鏈上', 'On-chain'), ('價格結構', 'Price structure'), ('衍生品', 'Derivatives'), ('資金流', 'Flows'), ('宏觀情緒', 'Macro & sentiment'), ('綜合', 'Composite')]
KW = [(2, ['Coinalyze', 'Deribit', 'OKX', 'Bitfinex', 'Hyperliquid', '買權', '年化', '資金費率', '未平倉']),
      (3, ['Coinbase', 'CoinMarketCap', 'DefiLlama', 'CFTC', 'Upbit', '財政部', '表觀需求', 'ETF', '穩定幣']),
      (4, ['FRED', 'alternative.me', 'Wikimedia', '恐懼', '利率']),
      (1, ['Kraken', '統一收盤', '交易所', '收盤價', '均線', '冪律']),
      (0, ['Bitview', 'CheckOnChain', 'CoinMetrics', 'bitcoin-data', 'mempool', 'HODL', 'MVRV', '持有者'])]
DEF = {'cycle': 0, 'lv': 1, 'sell': 0, 'buy': 3, 'lev': 2, 'exit': 1, 'today': 5}

def layer(pid, c):
    if pid == 'today':
        return 5
    txt = (c.get('src') or '') + ' ' + c.get('zh', '')
    for li, ws in KW:
        if any(w in txt for w in ws):
            return li
    return DEF.get(pid, 0)

# 每張圖的極簡小圖（和首頁「找圖」地圖同一份資料）：['l', 指標線, 價格線或 None] 或 ['b', 柱]，數值正規化
NP = 40
def num(v): return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
def resample(vals, n=NP):
    vals = [v for v in vals if num(v)]
    if len(vals) < 4: return None
    if len(vals) <= n: return vals
    return [vals[min(len(vals) - 1, round(i * (len(vals) - 1) / (n - 1)))] for i in range(n)]
def norm(vals, log=False):
    if vals is None: return None
    if log and all(v > 0 for v in vals): vals = [math.log(v) for v in vals]
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-12: return [0.5] * len(vals)
    return [round((v - lo) / (hi - lo), 2) for v in vals]
def col(rows, c): return [r[c] for r in rows if isinstance(r, list) and len(r) > c]

def mini(c):
    src = c
    if 'modes' in c and not any(k in c for k in ('rows', 'dist', 'xy', 'list')) and c['modes'] and isinstance(c['modes'][0], dict):
        src = {**c, **c['modes'][0]}
    rows = src.get('rows')
    if isinstance(rows, list) and len(rows) > 20 and isinstance(rows[0], list):
        rows = rows[-320:]
        ser, ci = src.get('ser') or [], None
        if ser:
            h = src.get('hero'); s = ser[h] if isinstance(h, int) and 0 <= h < len(ser) else ser[0]
            ci = s.get('c') if isinstance(s, dict) else None
        if not isinstance(ci, int):
            p = src.get('p'); ci = next((k for k in range(1, len(rows[0])) if k != p), 1)
        a = norm(resample(col(rows, ci)), log=src.get('tf') == 'log')
        b, p = None, src.get('p')
        if isinstance(p, int) and p != ci: b = norm(resample(col(rows, p)), log=True)
        if a: return ['l', a, b]
    d = src.get('dist')
    if isinstance(d, dict) and isinstance(d.get('rows'), list) and d['rows'] and isinstance(d['rows'][0], list):
        v = [r[1] for r in d['rows'] if len(r) > 1 and num(r[1])]
        if len(v) > 44:
            k = math.ceil(len(v) / 44); v = [max(v[i:i + k], key=abs) for i in range(0, len(v), k)]
        m = max((abs(x) for x in v), default=0)
        if m > 0 and len(v) >= 4: return ['b', [round(x / m, 2) for x in v]]
    xy = src.get('xy')
    if isinstance(xy, dict) and isinstance(xy.get('series'), list) and xy['series']:
        ss = [s for s in xy['series'] if isinstance(s, dict) and isinstance(s.get('rows'), list) and len(s['rows']) > 3]
        if ss:
            a = norm(resample([r[1] for r in ss[-1]['rows'] if len(r) > 1]), log=bool(xy.get('log')))
            b = norm(resample([r[1] for r in ss[0]['rows'] if len(r) > 1]), log=bool(xy.get('log'))) if len(ss) > 1 else None
            if a: return ['l', a, b]
    li = src.get('list')
    if isinstance(li, dict) and isinstance(li.get('rows'), list):
        v = [r.get('bar') for r in li['rows'] if isinstance(r, dict) and num(r.get('bar'))]
        m = max((abs(x) for x in v), default=0)
        if len(v) >= 4 and m > 0: return ['b', [round(x / m, 2) for x in v]]
    return None

CH, MINI, NM = [], [], []
for pid in ORDER:
    for g in PAGES[pid]:
        for c in g['charts']:
            # 第 5 欄：「今天」頁的六個問題各自對應哪一頁（第 02 段讀完那一頁的圖就點亮它），其他圖是 -1
            go = ORDER.index(c['go']) if pid == 'today' and c.get('go') in ORDER else -1
            CH.append([c['k'], LEANS.get(c['k'], ''), layer(pid, c), ORDER.index(pid), go])
            NM.append([c.get('zh') or c['k'], c.get('en') or c.get('zh') or c['k']])
            try:
                MINI.append(mini(c))
            except Exception:
                MINI.append(None)

st = NX.get('stance') or {}
OUT = {
    'date': NX['date'], 'issue': NX.get('issue'), 'close': NX.get('price'), 'n': len(CH),
    'head': [NX.get('headline') or '', EN.get('headline') or ''],
    'stance': [st.get('short') or st.get('label') or '', (EN.get('stance') or {}).get('short') or (EN.get('stance') or {}).get('label') or ''],
    'lay': LAY, 'pg': ORDER, 'pgn': [PGN.get(p, [p, p]) for p in ORDER], 'ch': CH, 'nm': NM, 'mini': MINI,
}
js = 'window.DAYBREAK_INTRO=' + json.dumps(OUT, ensure_ascii=False, separators=(',', ':')) + ';\n'
open(D_('intro.js'), 'w', encoding='utf-8').write(js)
ver = hashlib.sha1(js.encode('utf-8')).hexdigest()[:10]
page = open(os.path.join(HERE, 'page.html'), encoding='utf-8').read()
assert page.count('data/intro.js?v=__V__') == 1
open(os.path.join(REPO, 'index.html'), 'w', encoding='utf-8').write(page.replace('data/intro.js?v=__V__', 'data/intro.js?v=' + ver))
print('wrote data/intro.js', len(js), 'bytes;', len(CH), 'charts,', sum(1 for m in MINI if m), 'with mini charts; index.html v=' + ver)
