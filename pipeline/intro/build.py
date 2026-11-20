# -*- coding: utf-8 -*-
"""介紹頁（/intro/）的建置。2026-11-19 新增。
讀首頁已經建好的 data/next.js、data/next-*.js、data/leans.json、data/notes.en.json，寫出：
  data/intro.js     window.DAYBREAK_INTRO：每張圖的表態、資料種類、所屬的頁、中英圖名（讀圖掃描用），加上當期的期數、收盤、頭條、判讀（中英）
  index.html        根目錄（2026-11-20 起根網址就是介紹頁）：pipeline/intro/page.html 換上資料檔的版本號
  intro/index.html 是固定的轉址檔（舊的 /intro/ 連結轉到 /?intro），不在這裡寫
圖的張數、每頁幾張、每種資料幾張都從資料算，不寫死（使用者：「圖的數量可能會一直增加」）。
用法：python3 pipeline/intro/build.py（pipeline/next/build.py 跑完會接著呼叫；失敗不影響首頁）"""
import json, glob, os, hashlib

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

CH, NM = [], []
for pid in ORDER:
    for g in PAGES[pid]:
        for c in g['charts']:
            # 第 5 欄：「今天」頁的六個問題各自對應哪一頁（第 02 段讀完那一頁的圖就點亮它），其他圖是 -1
            go = ORDER.index(c['go']) if pid == 'today' and c.get('go') in ORDER else -1
            CH.append([c['k'], LEANS.get(c['k'], ''), layer(pid, c), ORDER.index(pid), go])
            NM.append([c.get('zh') or c['k'], c.get('en') or c.get('zh') or c['k']])

st = NX.get('stance') or {}
OUT = {
    'date': NX['date'], 'issue': NX.get('issue'), 'close': NX.get('price'), 'n': len(CH),
    'head': [NX.get('headline') or '', EN.get('headline') or ''],
    'stance': [st.get('short') or st.get('label') or '', (EN.get('stance') or {}).get('short') or (EN.get('stance') or {}).get('label') or ''],
    'lay': LAY, 'pg': ORDER, 'pgn': [PGN.get(p, [p, p]) for p in ORDER], 'ch': CH, 'nm': NM,
}
js = 'window.DAYBREAK_INTRO=' + json.dumps(OUT, ensure_ascii=False, separators=(',', ':')) + ';\n'
open(D_('intro.js'), 'w', encoding='utf-8').write(js)
ver = hashlib.sha1(js.encode('utf-8')).hexdigest()[:10]
page = open(os.path.join(HERE, 'page.html'), encoding='utf-8').read()
assert page.count('data/intro.js?v=__V__') == 1
open(os.path.join(REPO, 'index.html'), 'w', encoding='utf-8').write(page.replace('data/intro.js?v=__V__', 'data/intro.js?v=' + ver))
print('wrote data/intro.js', len(js), 'bytes;', len(CH), 'charts; index.html v=' + ver)
