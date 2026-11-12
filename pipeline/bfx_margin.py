#!/usr/bin/env python3
"""Bitfinex 槓桿多空（2026-11-12 使用者要求，參考業界常看的「Bitfinex 保證金多單」）。

Bitfinex 公開的 stats1 接口有 BTC/USD 保證金交易的多單和空單總量（顆），只有每分鐘一筆，沒有日線。
每天取 UTC 當天最後一筆當收盤值，存在 data/bfx_margin.json（rows＝[[日數, 多單, 空單]]），每日流程只補缺的那幾天。
這是 Bitfinex 一家交易所的保證金部位，多單長期遠大於空單（借美元買幣的大戶多），所以看的是多單自己的增減，不是多空比。
接口限流很嚴：連續打十幾次就會擋，長時間下來一分鐘只能抓一兩次（第一次補四年歷史花了好幾個小時），所以自己排隊，每 13 秒一次，被擋就照回應寫的秒數等。
每日流程用 daily()：只補缺的一兩天（兩次請求），被擋最多等一次、40 秒，再不行就用檔案裡已有的，圖會晚一天，不拖住整個流程。只作讀值。"""
import datetime as dt, json, os, sys, time, urllib.error, urllib.request

URL = 'https://api-pub.bitfinex.com/v2/stats1/pos.size:1m:tBTCUSD:%s/hist?limit=%d&sort=1&start=%d'
HERE = os.path.dirname(os.path.abspath(__file__)); PATH = os.path.join(HERE, '..', 'data', 'bfx_margin.json')
_EP = dt.date(1970, 1, 1); DAY = 86400000
dn = lambda s: (dt.date.fromisoformat(s) - _EP).days
_last = [0.0]; PATIENT = [True]   # PATIENT＝被限流時要不要照它說的時間等（補歷史要，每日流程不要）


def _get(side, start, limit=10000, gap=13):
    for k in range(6):
        w = _last[0] + gap - time.time()
        if w > 0: time.sleep(w)
        _last[0] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(URL % (side, limit, start), headers={'User-Agent': 'daybreak-pipeline'}), timeout=60) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and k < (5 if PATIENT[0] else 1): time.sleep(min(600 if PATIENT[0] else 40, float(e.headers.get('Retry-After') or 60)) + 5); continue   # 被擋時回應會寫要等幾秒，照它等；自己亂重試會被擋更久
            raise RuntimeError(f'Bitfinex {side} HTTP {e.code}')
        except (urllib.error.URLError, TimeoutError) as e:
            if k < 2: time.sleep(5); continue
            raise RuntimeError(f'Bitfinex {side} {e}')


def closes(side, d0, d1):
    """d0～d1（日數，含）每天 UTC 最後一筆。一次最多 10000 分鐘（約 6.9 天），所以 6 天一批"""
    out = {}; d = d0
    while d <= d1:
        pts = _get(side, d * DAY) or []
        if not pts: break
        for t, v in pts:
            k = t // DAY
            if d <= k <= d1: out[k] = v   # 由舊到新，留下當天最後一筆
        nxt = pts[-1][0] // DAY
        if len(pts) < 10000: break
        d = nxt if nxt > d else d + 6     # 最後一天可能沒收完，下一批從那天重抓
    return out


def update(last, path=PATH, since=None, cap=40, log=None):
    """補到 last（'YYYY-MM-DD'）那天。回傳 rows。since＝第一次建檔從哪天開始；cap＝一次最多補幾天（每日流程用，避免拖太久）"""
    try: J = json.load(open(path))
    except Exception: J = dict(rows=[])
    rows = {r[0]: r for r in J.get('rows') or []}; d1 = dn(last)
    d0 = max(rows) + 1 if rows else dn(since or last) - 0
    if not since and d1 - d0 >= cap: d0 = d1 - cap + 1
    while d0 <= d1:
        e = min(d1, d0 + 59)
        L = closes('long', d0, e); S = closes('short', d0, e)
        for k in sorted(set(L) & set(S)): rows[k] = [k, round(L[k], 2), round(S[k], 2)]
        if log: log(f'{(_EP + dt.timedelta(d0)).isoformat()}–{(_EP + dt.timedelta(e)).isoformat()} {len(rows)} 天')
        J = dict(note='Bitfinex BTC/USD 保證金多單、空單（顆），每天 UTC 最後一筆；來源 api-pub.bitfinex.com stats1 pos.size', rows=[rows[k] for k in sorted(rows)])
        json.dump(J, open(path, 'w'), separators=(',', ':'))
        d0 = e + 1
    return [rows[k] for k in sorted(rows) if k <= d1]


def daily(last, path=PATH):
    """每日流程用：補到 last，被限流不久等；補不到就回傳檔案裡已有的（圖晚一天）。檔案也沒有才丟錯"""
    PATIENT[0] = False
    try: return update(last, path)
    except Exception:
        try: rows = json.load(open(path)).get('rows') or []
        except Exception: rows = []
        if not rows: raise
        return [r for r in rows if r[0] <= dn(last)]
    finally: PATIENT[0] = True


def build(rows, px, last):
    """rows＝update() 的結果；px＝{日期: 收盤}。回傳 deriv.bfx_margin；資料不夠回傳 None。
    統計：多單 30 日增減，以及「30 日增加超過 10%」「30 日減少超過 10%」之後 30 天價格較高的比例，和隨便一天比。"""
    D = lambda n: (_EP + dt.timedelta(n)).isoformat()
    rs = [r for r in rows if r[0] <= dn(last) and px.get(D(r[0]))]
    if len(rs) < 120: return None
    N = [r[0] for r in rs]; L = [r[1] for r in rs]; S = [r[2] for r in rs]; P = [px[D(n)] for n in N]; n = len(rs)
    ch = lambda v, i, k: (v[i] / v[i - k] - 1) * 100 if i >= k and v[i - k] else None
    c30 = [ch(L, i, 30) for i in range(n)]; f30 = [ch(P, i + 30, 30) if i + 30 < n else None for i in range(n)]
    def stat(test):
        v = [f30[i] for i in range(n) if c30[i] is not None and f30[i] is not None and test(c30[i])]
        return dict(n=len(v), up=round(sum(x > 0 for x in v) / len(v) * 100) if v else None, med=round(sorted(v)[len(v) // 2], 1) if v else None)
    base = [x for x in f30 if x is not None]; hi = max(range(n), key=lambda i: L[i]); s4 = sorted(L)
    return dict(date=D(N[-1]), long=round(L[-1]), short=round(S[-1]), chg7=round(ch(L, n - 1, 7), 1), chg30=round(c30[-1], 1), chg90=round(ch(L, n - 1, 90), 1) if n > 90 else None,
                px30=round(ch(P, n - 1, 30), 1), pct=round(sum(x <= L[-1] for x in s4) / n * 100), hi=dict(date=D(N[hi]), long=round(L[hi])), since=D(N[0]), n=n,
                up10=stat(lambda c: c >= 10), dn10=stat(lambda c: c <= -10), base=dict(n=len(base), up=round(sum(x > 0 for x in base) / len(base) * 100), med=round(sorted(base)[len(base) // 2], 1)) if base else None,
                rows=[[N[i], round(P[i]), round(L[i]), round(S[i]), None if c30[i] is None else round(c30[i], 1)] for i in range(n)], src='Bitfinex', link='https://www.bitfinex.com',
                note='Bitfinex BTC/USD 保證金多單與空單（顆），每天 UTC 最後一筆；只有一家交易所；只作讀值')


if __name__ == '__main__':   # 第一次建檔：python3 pipeline/bfx_margin.py 2022-10-01 [到哪天]
    since = sys.argv[1]; to = sys.argv[2] if len(sys.argv) > 2 else (dt.datetime.utcnow().date() - dt.timedelta(days=1)).isoformat()
    r = update(to, since=since, log=lambda m: print(m, flush=True)); print('done', len(r))
