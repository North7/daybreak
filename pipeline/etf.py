#!/usr/bin/env python3
"""美國現貨 BTC ETF 每日淨流量（2026-10-08 建立）。
Farside 用 Cloudflare 擋所有自動抓取（雲端與本機都回 403），改用 The Block 的圖表 JSON：
各檔 ETF 逐日淨流量，2026-09-14～10-05 逐日與 Farside 合計比對，差距 ≤ 0.1 百萬美元。
The Block 只公布已完整的交易日（約晚一天）；它還沒有的日子保留原本的列（例如 Farside 的當日部分值），之後由完整數字覆寫。
用法（在倉庫根目錄）：python3 pipeline/etf.py   # 更新 data/etf.json，並同步 data/latest.json 的 flows.etf
失敗時不改任何檔案、照常結束，網站沿用既有數字並以資料日期標示。"""
import json, os, sys, urllib.request, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
URL = 'https://www.theblock.co/api/charts/chart/etfs/bitcoin-etf/spot-bitcoin-etf-flows'
KEEP = 60

def fetch():
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 (daybreak data pipeline)', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as r:
        series = json.load(r)['chart']['jsonFile']['Series']
    tot, n = {}, {}
    for fund in series.values():
        for p in fund['Data']:
            if p.get('Result') is None: continue
            d = dt.datetime.fromtimestamp(p['Timestamp'], dt.timezone.utc).date().isoformat()
            tot[d] = tot.get(d, 0) + p['Result'] / 1e6; n[d] = n.get(d, 0) + 1
    if not tot: raise RuntimeError('The Block 回傳沒有資料')
    return {d: round(v, 1) for d, v in tot.items()}, len(series)

if __name__ == '__main__':
    f = P('data', 'etf.json'); etf = json.load(open(f))
    try: tb, nf = fetch()
    except Exception as e: print('ETF 未更新：', e); sys.exit(0)
    last_tb = max(tb)
    rows = {r['d']: r for r in etf['rows']}
    for d, v in tb.items(): rows[d] = {'d': d, 'musd': v, 'partial': False}
    rows = [r for d, r in sorted(rows.items()) if r['d'] in tb or r['d'] > last_tb][-KEEP:]   # The Block 已涵蓋的日子一律用它的完整數字
    etf.update(_about='美國現貨 BTC ETF 每日淨流量（百萬美元，全部現貨 ETF 合計）。資料管線每天從 The Block 自動更新，與 Farside 同口徑；partial=true 表示當天尚未完整回報。',
               source='The Block', source_url='https://www.theblock.co/data/etfs/bitcoin-etf/spot-bitcoin-etf-flows',
               updated_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), last_complete=last_tb, rows=rows)
    json.dump(etf, open(f, 'w'), ensure_ascii=False, indent=1)
    lf = P('data', 'latest.json')
    if os.path.exists(lf):
        lat = json.load(open(lf)); lat.setdefault('flows', {})['etf'] = rows
        json.dump(lat, open(lf, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'ETF 已更新：{nf} 檔，最新完整日 {last_tb}，共 {len(rows)} 筆；最近：', [(r["d"], r["musd"]) for r in rows[-4:]])
