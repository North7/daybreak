#!/usr/bin/env python3
"""美國現貨 BTC ETF 逐檔每日淨流量（2026-11-11 起；etf.py 的每日合計與 cq_extra.py 的 ETF 持有者成本共用）。
原本用 The Block 的圖表 JSON，2026-11-09 起兩個網址都下架（410／404），改用 CoinMarketCap 網站自己用的 data-api（免金鑰）：
- /data-api/v3/etf/detail/netflow/list?category=btc：逐日逐檔淨流量（美元與顆數），2024-01-11 上市起，一頁 100 天；date="0" 那列是累計，不用。
- /data-api/v3/etf/list?category=btc：每檔的國家。合計（total）含香港 ETF（CHINAAMC、HARVEST、BOSERA&HASHKEY），只取 country=us 的檔。
- 還沒回報的日子是全 0 的空列（例如當天與前一天晚上），丟掉。
2026-11-11 比對 The Block 過去的數字（git 裡 82 個完整交易日）：10/13–11/06 有 13/18 天完全一樣，其餘差 4 百萬美元以內；
7–9 月常少 5–10 百萬、09/22 少 99 百萬、08/12 美國各檔全空。CoinMarketCap 只有 11 檔美國現貨 ETF（The Block 有 12 檔），沒有 MSBT（Morgan Stanley）。
Farside、SoSoValue 網頁擋自動抓取（403）；Bitbo 的表只有最近十來天、合計和 Farside 差很多，不用。"""
import json, time, urllib.request, datetime as dt

API = 'https://api.coinmarketcap.com/data-api/v3/etf'
UA = {'User-Agent': 'Mozilla/5.0 (daybreak data pipeline)', 'Accept': 'application/json'}
NON_US = {'CHINAAMC', 'HARVEST', 'BOSERA&HASHKEY'}   # 國家清單取不到時的備援
SOURCE, SOURCE_URL = 'CoinMarketCap', 'https://coinmarketcap.com/etf/bitcoin/'


def _get(path, tries=3):
    for k in range(tries):
        try:
            js = json.load(urllib.request.urlopen(urllib.request.Request(API + path, headers=UA), timeout=40))
            st = js.get('status') or {}
            if str(st.get('error_code', '0')) != '0': raise RuntimeError(f"{st.get('error_code')} {st.get('error_message')}")
            return js.get('data')
        except Exception:
            if k == tries - 1: raise
            time.sleep(3 * (k + 1))


def fetch():
    """回傳 ({日期: {代號: 美元}}, 美國現貨 ETF 代號)；只含已回報的日子。失敗就丟例外，呼叫端照常沿用舊資料。"""
    try: us = {x['ticker'] for x in _get('/list?category=btc') or [] if (x.get('country') or '').lower() == 'us'}
    except Exception: us = None
    pts = []
    for page in range(1, 40):
        p = (_get(f'/detail/netflow/list?category=btc&size=100&page={page}') or {}).get('points') or []
        if not p: break
        pts += p; time.sleep(0.5)
    out, funds = {}, set()
    for p in pts:
        if str(p.get('date')) in ('', '0', 'None'): continue
        day = dt.datetime.fromtimestamp(int(p['date']) / 1000, dt.timezone.utc).date().isoformat()
        f = {k: float(v['usd']) for k, v in p.items() if k not in ('date', 'total') and isinstance(v, dict) and v.get('usd') is not None and (k in us if us else k not in NON_US)}
        if not any(f.values()): continue
        out[day] = f; funds |= set(f)
    if len(out) < 300: raise RuntimeError(f'CoinMarketCap 只回 {len(out)} 天')
    return out, sorted(funds)


if __name__ == '__main__':
    F, funds = fetch(); D = sorted(F)
    print(f'{len(funds)} 檔：{funds}；{D[0]}–{D[-1]}，{len(D)} 天；最近：', [(d, round(sum(F[d].values()) / 1e6, 1)) for d in D[-5:]])
