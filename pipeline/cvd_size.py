#!/usr/bin/env python3
"""依成交單大小分的累計買賣差（CVD，2026-11-12 使用者要求）。

資料是 Binance 公開的 BTCUSDT 現貨逐筆成交檔（data.binance.vision，每天一個 zip，約 10–30 MB，前一天的檔隔天才上架）。
每一筆依成交金額分五級：不到 1 千、1 千–1 萬、1 萬–10 萬、10 萬–100 萬、100 萬美元以上；主動買進算正、主動賣出算負。
每天每一級記淨額和總成交額（百萬美元），存在 data/cvd_size.json，每日流程只補缺的那幾天。
限制要寫清楚：(1) 只有 Binance 一家的現貨；(2) 逐筆檔是「同一張市價單在同一個價位的成交」合成一筆，一張大單吃掉好幾個價位會被拆成好幾筆，
所以大單會被低估；(3) 大戶可以把單拆小。只作讀值。"""
import datetime as dt, io, json, os, sys, tempfile, urllib.error, urllib.request, zipfile

URL = 'https://data.binance.vision/data/spot/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-%s.zip'
EDGES = (1e3, 1e4, 1e5, 1e6)
HERE = os.path.dirname(os.path.abspath(__file__)); PATH = os.path.join(HERE, '..', 'data', 'cvd_size.json')
_EP = dt.date(1970, 1, 1)
dn = lambda s: (dt.date.fromisoformat(s) - _EP).days
D = lambda n: (_EP + dt.timedelta(n)).isoformat()


def one(day):
    """一天的檔 → [淨額×5, 成交額×5]（百萬美元），檔還沒上架回傳 None"""
    tmp = tempfile.NamedTemporaryFile(suffix='.zip', delete=False); tmp.close()
    try:
        try:
            with urllib.request.urlopen(urllib.request.Request(URL % day, headers={'User-Agent': 'daybreak-pipeline'}), timeout=180) as r, open(tmp.name, 'wb') as f:
                while True:
                    b = r.read(1 << 20)
                    if not b: break
                    f.write(b)
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            raise
        buy = [0.0] * 5; sell = [0.0] * 5
        z = zipfile.ZipFile(tmp.name)
        with z.open(z.namelist()[0]) as f:
            for line in io.TextIOWrapper(f, 'ascii', errors='replace'):
                p = line.split(',')
                try: u = float(p[1]) * float(p[2])
                except (ValueError, IndexError): continue   # 有的月份第一列是欄名
                k = 0
                while k < 4 and u >= EDGES[k]: k += 1
                if p[6][:1] in 'Tt': sell[k] += u     # is_buyer_maker＝True：買方掛單，主動的是賣方
                else: buy[k] += u
        return [round((buy[k] - sell[k]) / 1e6, 2) for k in range(5)] + [round((buy[k] + sell[k]) / 1e6, 1) for k in range(5)]
    finally:
        try: os.unlink(tmp.name)
        except OSError: pass


def update(last, path=PATH, since=None, cap=12, log=None):
    """補到 last 那天（檔還沒上架就停在前一天）。回傳 rows＝[[日數, 淨額×5, 成交額×5]]"""
    try: J = json.load(open(path))
    except Exception: J = dict(rows=[])
    rows = {r[0]: r for r in J.get('rows') or []}; d1 = dn(last)
    d0 = max(rows) + 1 if rows else dn(since or last)
    if not since and d1 - d0 >= cap: d0 = d1 - cap + 1
    def save():
        json.dump(dict(note='Binance BTCUSDT 現貨逐筆成交依金額分五級（<1千、1千–1萬、1萬–10萬、10萬–100萬、≥100萬美元）：每天的主動買減主動賣、總成交額，百萬美元；來源 data.binance.vision',
                       edges=list(EDGES), rows=[rows[k] for k in sorted(rows)]), open(path, 'w'), separators=(',', ':'))
    for k in range(d0, d1 + 1):
        v = one(D(k))
        if v is None:
            if log: log(f'{D(k)} 還沒上架')
            if k >= d1 - 2: break        # 最新一兩天還沒上架是正常的
            continue
        rows[k] = [k] + v
        if log and (k - d0) % 30 == 0: log(f'{D(k)} {len(rows)} 天'); save()
    save()
    return [rows[k] for k in sorted(rows) if k <= d1]


NAMES = [('不到 1 千美元', 'Under $1K'), ('1 千–1 萬', '$1K–10K'), ('1 萬–10 萬', '$10K–100K'), ('10 萬–100 萬', '$100K–1M'), ('100 萬以上', '$1M+')]


def build(rows, px, last):
    """回傳 flows.cvd_size；資料不夠回傳 None。三組：小單（不到 1 萬）、中單（1 萬–10 萬）、大單（10 萬以上）的累計淨額（從第一天累計，百萬美元）"""
    rs = [r for r in rows if r[0] <= dn(last) and px.get(D(r[0]))]
    if len(rs) < 60: return None
    G = lambda r: (r[1] + r[2], r[3], r[4] + r[5]); V = lambda r: (r[6] + r[7], r[8], r[9] + r[10])
    cum = [0.0, 0.0, 0.0]; out = []
    for r in rs:
        g = G(r); cum = [cum[i] + g[i] for i in range(3)]
        out.append([r[0], round(px[D(r[0])])] + [round(c, 1) for c in cum] + [round(x, 1) for x in g])
    def win(k):
        w = rs[-k:]; return [round(sum(G(r)[i] for r in w), 1) for i in range(3)]
    def share(k):
        w = rs[-k:]; t = [sum(V(r)[i] for r in w) for i in range(3)]; s = sum(t) or 1; return [round(x / s * 100, 1) for x in t]
    return dict(date=D(rs[-1][0]), since=D(rs[0][0]), n=len(rs), d7=win(7), d30=win(30), d90=win(90) if len(rs) >= 90 else None, share30=share(30),
                px30=round((px[D(rs[-1][0])] / px[D(rs[-31][0])] - 1) * 100, 1) if len(rs) > 30 else None, rows=out, src='Binance', link='https://data.binance.vision',
                note='Binance BTCUSDT 現貨逐筆成交依金額分級的主動買減主動賣（百萬美元）；小單＝不到 1 萬美元、中單＝1 萬–10 萬、大單＝10 萬以上；一張大單吃好幾個價位會被拆成好幾筆，大單會被低估；只作讀值')


if __name__ == '__main__':   # 第一次建檔：python3 pipeline/cvd_size.py 2023-11-01 [到哪天]
    since = sys.argv[1]; to = sys.argv[2] if len(sys.argv) > 2 else (dt.datetime.utcnow().date() - dt.timedelta(days=1)).isoformat()
    r = update(to, since=since, log=lambda m: print(m, flush=True)); print('done', len(r))
