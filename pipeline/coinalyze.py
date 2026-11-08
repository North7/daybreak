"""Coinalyze 讀取（2026-11-08 使用者申請了免費 API key，用來把清算熱力圖從只有 OKX 改成多家交易所，並加每日多空清算量）。
key 放在環境變數 COINALYZE_API_KEY（GitHub secret 同名；本機在 ~/.config/daybreak/coinalyze.key）。沒有 key 時 ok() 為 False，呼叫端照舊用 OKX。
限制：每分鐘 40 次，一次最多 20 個合約、每個合約算 1 次；分鐘以下到 12 小時線只保留最近 1,500–2,000 根，日線全部保留。
使用條款要求標明資料來源並附連結（https://coinalyze.net）。"""
import json, os, time, urllib.error, urllib.parse, urllib.request

BASE = 'https://api.coinalyze.net/v1/'
LINK = 'https://coinalyze.net'
# BTC 永續：2026-11-08 依未平倉量取前 11 個（約占 Coinalyze 有收錄的 BTC 永續未平倉 97%）。Coinalyze 沒有 Bitget、Gate 的未平倉
SYM = ('BTCUSDT_PERP.A', 'BTCUSDC_PERP.A', 'BTCUSD_PERP.A',      # Binance：USDT、USDC、幣本位
       'BTCUSDT.6', 'BTCUSD.6',                                   # Bybit
       'BTCUSDT_PERP.3', 'BTCUSD_PERP.3',                         # OKX
       'BTC.H',                                                   # Hyperliquid
       'BTCUSDT_PERP.4', 'BTCUSDT_PERP.F', 'BTC-PERPETUAL.2')     # HTX、Bitfinex、Deribit
USD = {'BTCUSD_PERP.A', 'BTCUSD.6', 'BTCUSD_PERP.3', 'BTC-PERPETUAL.2'}   # 幣本位：未平倉量、清算量是美元，其餘是顆
EXCH = ('Binance', 'Bybit', 'OKX', 'Hyperliquid', 'HTX', 'Bitfinex', 'Deribit')
NAME = {'A': 'Binance', '6': 'Bybit', '3': 'OKX', 'H': 'Hyperliquid', '4': 'HTX', 'F': 'Bitfinex', '2': 'Deribit'}   # 合約代碼最後一碼＝交易所


def exch(syms):
    """合約清單 → 交易所名稱（依 EXCH 的順序）"""
    n = {NAME.get(s.rsplit('.', 1)[-1]) for s in syms}
    return [e for e in EXCH if e in n]
PX = 'BTCUSDT_PERP.A'      # 價格 K 線用 Binance USDT 永續
IV = {'1hour': 3600, '4hour': 14400, '12hour': 43200, 'daily': 86400}
_calls = []                # 最近一分鐘內的呼叫（時間, 次數），自己先排隊，不等 429


def key():
    return (os.environ.get('COINALYZE_API_KEY') or '').strip()


def ok():
    return bool(key())


def _pace(n):
    while True:
        t = time.time(); _calls[:] = [c for c in _calls if t - c[0] < 61]
        if sum(c[1] for c in _calls) + n <= 38: _calls.append((t, n)); return
        time.sleep(max(1.0, 61 - (t - _calls[0][0])))


def get(path, n=1, **q):
    url = BASE + path + ('?' + urllib.parse.urlencode(q) if q else '')
    for k in range(6):
        _pace(n)
        try:
            req = urllib.request.Request(url, headers={'api_key': key(), 'User-Agent': 'daybreak-pipeline'})
            with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and k < 5: time.sleep(float(e.headers.get('Retry-After') or 15) + 1); continue
            raise RuntimeError(f'Coinalyze {path} HTTP {e.code}')
        except (urllib.error.URLError, TimeoutError) as e:
            if k < 2: time.sleep(5); continue
            raise RuntimeError(f'Coinalyze {path} {e}')


def hist(ep, iv, frm, to, syms=SYM, **q):
    """{合約: {開盤時間（秒）: 列}}；只留已收完的 K 線（開盤＋長度 ≤ to）"""
    out = {}
    for i in range(0, len(syms), 20):
        s = syms[i:i + 20]
        for x in get(ep, n=len(s), symbols=','.join(s), interval=iv, **{'from': int(frm), 'to': int(to)}, **q) or []:
            out[x['symbol']] = {r['t']: r for r in x.get('history') or [] if r['t'] + IV[iv] <= to}
    return out


DAY0 = 1546300800         # 2019-01-01：日線從這天開始要
_memo = {}


def daily(ep, syms, to=None, **q):
    """日線（全部保留）：{合約: {t: 列}}，只到已收完的那天；同一次執行裡同樣的請求只抓一次（各圖共用價格、未平倉）"""
    to = int(to or time.time()) // 86400 * 86400
    k = (ep, tuple(syms), to, tuple(sorted(q.items())))
    if k not in _memo: _memo[k] = hist(ep, 'daily', DAY0, to, tuple(syms), **q)
    return _memo[k]


def oi_btc(iv, frm, to):
    """各合約未平倉量（顆或美元，見 USD）與 Binance USDT 永續 K 線 {t: [o, h, l, c]}"""
    oi = {s: {t: r['c'] for t, r in h.items()} for s, h in hist('open-interest-history', iv, frm, to).items() if h}
    px = {t: [r['o'], r['h'], r['l'], r['c']] for t, r in (hist('ohlcv-history', iv, frm, to, (PX,)).get(PX) or {}).items()}
    if not px or len(oi) < 5: raise RuntimeError(f'Coinalyze {iv} 未平倉或 K 線取不到（{len(oi)} 個合約）')
    return oi, px
