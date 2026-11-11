#!/usr/bin/env python3
"""美國現貨 BTC ETF 每日淨流量（2026-10-08 建立）。
2026-10-08 起用 The Block 的圖表 JSON（Farside 用 Cloudflare 擋所有自動抓取，雲端與本機都回 403）；2026-11-09 起 The Block 下架（410／404），
2026-11-11 改用 CoinMarketCap 的逐檔資料（見 etf_src.py：只取美國現貨 ETF，沒有 MSBT，和 The Block／Farside 大多一樣、偶爾差幾百萬美元）。
CoinMarketCap 還沒有的日子保留原本的列（partial=true，例如每日任務依兩個獨立來源寫入的暫定值，附 src），之後由它的數字覆寫。
用法（在倉庫根目錄）：python3 pipeline/etf.py   # 更新 data/etf.json，並同步 data/latest.json 的 flows.etf
失敗時不改任何檔案、照常結束，網站沿用既有數字並以資料日期標示。"""
import json, os, sys, datetime as dt
import etf_src

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
KEEP = 60
ABOUT = '美國現貨 BTC ETF 每日淨流量（百萬美元，美國現貨 ETF 合計，不含香港）。資料管線每天從 CoinMarketCap 自動更新（2026-11-11 起；之前是 The Block，11/09 下架）；CoinMarketCap 沒有 MSBT，和 Farside 偶爾差幾百萬美元。partial=true 表示當天尚未完整回報。'


def fetch():
    F, funds = etf_src.fetch()
    return {d: round(sum(v.values()) / 1e6, 1) for d, v in F.items()}, len(funds)


ROLL_N, ROLL_TH = 20, -1500   # 近 20 個交易日合計低於 −15 億美元算一段流出（2026-11-12，參考 Glassnode 週報的定義）


def roll20(tb):
    """近 20 個交易日的合計淨流量（百萬美元）與歷次流出段落。tb＝{日期: 當天合計}，上市（2024-01-11）起的每個交易日。只作讀值。"""
    D = sorted(tb); v = [tb[d] for d in D]
    if len(D) < ROLL_N + 5: return None
    s = [None] * (ROLL_N - 1) + [sum(v[i - ROLL_N + 1:i + 1]) for i in range(ROLL_N - 1, len(v))]
    st, cur = [], None
    for i, x in enumerate(s):
        if x is None: continue
        if x < ROLL_TH:
            if cur is None: cur = dict(a=D[i], min=x, min_d=D[i], n=0)
            cur['n'] += 1; cur['b'] = D[i]
            if x < cur['min']: cur['min'], cur['min_d'] = x, D[i]
        elif cur is not None: st.append(cur); cur = None
    if cur is not None: cur['open'] = True; st.append(cur)
    for q in st: q['min'] = round(q['min'])
    xs = [x for x in s if x is not None]
    ep = dt.date(1970, 1, 1); dn = lambda d: (dt.date.fromisoformat(d) - ep).days
    return dict(date=D[-1], n=ROLL_N, th=ROLL_TH, sum=round(s[-1]), prev5=round(s[-6]) if s[-6] is not None else None, pct_own=round(sum(x < s[-1] for x in xs) / len(xs) * 100, 1),
                in_stretch=s[-1] < ROLL_TH, stretches=st, since=D[0], rows=[[dn(D[i]), round(x)] for i, x in enumerate(s) if x is not None])

if __name__ == '__main__':
    f = P('data', 'etf.json'); etf = json.load(open(f))
    try: tb, nf = fetch()
    except Exception as e: print('ETF 未更新：', e); sys.exit(0)
    last_tb = max(tb)
    rows = {r['d']: r for r in etf['rows']}
    for d, v in tb.items(): rows[d] = {'d': d, 'musd': v, 'partial': False}
    rows = [r for d, r in sorted(rows.items()) if r['d'] in tb or r['d'] > last_tb][-KEEP:]   # 來源已涵蓋的日子一律用它的數字
    try: r20 = roll20({d: v for d, v in tb.items() if d <= last_tb})
    except Exception as e: print('roll20 失敗：', e); r20 = etf.get('roll20')
    etf.update(_about=ABOUT, source=etf_src.SOURCE, source_url=etf_src.SOURCE_URL,
               updated_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), last_complete=last_tb, rows=rows, roll20=r20)
    json.dump(etf, open(f, 'w'), ensure_ascii=False, indent=1)
    lf = P('data', 'latest.json')
    if os.path.exists(lf):
        lat = json.load(open(lf)); lat.setdefault('flows', {})['etf'] = rows; lat['flows']['etf20'] = r20
        json.dump(lat, open(lf, 'w'), ensure_ascii=False, separators=(',', ':'))
        try:   # 2026-11-09 網站讀的 data/site.json 跟著更新（pipeline/site_data.py）
            import site_data; site_data.write(lf, P('data', 'site.json'))
        except Exception as e:
            print('site_data failed', e)
    print(f'ETF 已更新：{nf} 檔，最新完整日 {last_tb}，共 {len(rows)} 筆；最近：', [(r["d"], r["musd"]) for r in rows[-4:]])
