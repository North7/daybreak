#!/usr/bin/env python3
"""USDC 對美元（2026-11-12 使用者要求，和 USDT 對美元同一套）。

Coinbase 上 USDC 和美元是 1:1 互換，沒有 USDC-USD 的成交價，所以用 Bitstamp 的 USDC/USD 每日收盤。
統計沿用 cb_premium.usdt_stats（深度折價線、歷次跌破、月平均），這樣兩種穩定幣的讀法一致。
USDC 平常比 USDT 更貼近 1 美元（發行商直接兌付），所以折溢價的幅度小很多；2023/03 矽谷銀行事件那幾天例外。只作讀值。"""
import datetime as dt
import cb_premium

_EP = dt.date(1970, 1, 1)
dn = lambda s: (dt.date.fromisoformat(s) - _EP).days
ymd = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat()


def usdc(get, pxc, last):
    """get＝collect.py 的 get(url)；pxc＝{日期: BTC 收盤}。回傳 flows.usdc；資料不夠回傳 None"""
    px = {}; end = None
    for _ in range(2):   # 一次最多 1000 天，抓兩次約 5 年半
        j = get('https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=86400&limit=1000' + (f'&end={end}' if end else ''))
        o = (j or {}).get('data', {}).get('ohlc') if isinstance(j, dict) else None
        if not o: break
        for r in o: px[ymd(int(r['timestamp']))] = float(r['close'])
        end = int(o[0]['timestamp']) - 86400
    days = [d for d in sorted(px) if d <= last and pxc.get(d) and d >= '2022-10-01' and 0.9 < px[d] < 1.1]
    if len(days) < 120 or dn(last) - dn(days[-1]) > 3: return None
    rows = [[dn(d), None, round(pxc[d]), None, round(px[d], 5)] for d in days]
    disc = [(px[d] - 1) * 100 for d in days]; a7 = cb_premium._ma(disc, 7)
    out = dict(date=days[-1], px=round(px[days[-1]], 5), disc=round(disc[-1], 3), disc7=round(a7[-1], 3), disc7_pct_own=cb_premium._pctl(a7, a7[-1]), since=days[0], n=len(days),
               rows=[[r[0], r[4], r[2]] for r in rows], src='Bitstamp', link='https://www.bitstamp.net', note='Bitstamp USDC/USD 每日收盤 − 1；只作讀值')
    out.update(cb_premium.usdt_stats(rows))
    return out
