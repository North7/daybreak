#!/usr/bin/env python3
"""Coinbase 溢價（2026-11-12 起扣掉 USDT 對美元的折溢價）。

原本：Coinbase BTC-USD ÷ Binance BTC-USDT − 1。USDT 不等於 1 美元時，這個數字裡混了 USDT 自己的折溢價：
2026-11-10 沒扣的 7 日平均是 −0.137%，其中約 −0.13% 是 USDT 低於 1 美元，扣掉後只剩 −0.007%。
現在：Coinbase BTC-USD ÷（Binance BTC-USDT × Coinbase USDT-USD）− 1，三個都用每日 UTC 收盤。
扣掉之後兩地價差只有幾個基點（近四年 7 日平均的 5%–95% 大約在 −0.012%～+0.015%），所以門檻改用自己的歷史分位，不再用固定的 −0.15%。
沒扣的數字（raw）和 USDT 對美元（usdt）都留著：USDT 折價本身代表有人把穩定幣換回美元。
USDT-USD 取不到時退回沒扣的算法（adj=False），門檻用舊的。只作讀值。"""
import datetime as dt

_EP = dt.date(1970, 1, 1)
dn = lambda s: (dt.date.fromisoformat(s) - _EP).days


def _pctl(arr, v):
    arr = [x for x in arr if x is not None]
    return round(sum(x < v for x in arr) / len(arr) * 100, 1) if arr else None


def _ma(v, n): return [None] * (n - 1) + [sum(v[i - n + 1:i + 1]) / n for i in range(n - 1, len(v))]


def _q(v, p):
    s = sorted(x for x in v if x is not None)
    return s[int((len(s) - 1) * p)] if s else None


def build(cb, bn, usdt, last):
    """cb／bn／usdt＝{日期: 收盤}（Coinbase BTC-USD、Binance BTC-USDT、Coinbase USDT-USD）；last＝資料日。回傳 flows.cb_premium。"""
    days = sorted(d for d in set(cb) & set(bn) if d <= last)
    adj = len([d for d in days if usdt.get(d)]) >= len(days) * 0.9 and bool(days) and bool(usdt.get(days[-1]))
    if adj: days = [d for d in days if usdt.get(d)]
    raw = [(cb[d] / bn[d] - 1) * 100 for d in days]
    val = [(cb[d] / (bn[d] * usdt[d]) - 1) * 100 for d in days] if adj else raw
    a7, a30, r7, r30 = _ma(val, 7), _ma(val, 30), _ma(raw, 7), _ma(raw, 30)
    out = dict(date=days[-1], pct=round(val[-1], 4), avg7=round(a7[-1], 4), avg30=round(a30[-1], 4),
               pct_own=_pctl(val, val[-1]), avg7_pct_own=_pctl(a7, a7[-1]), avg30_pct_own=_pctl(a30, a30[-1]), n=len(val), since=days[0], adj=adj,
               rows=[[dn(d), round(val[i], 4), round(cb[d]), round(raw[i], 3), round(usdt[d], 5) if adj else None] for i, d in enumerate(days)],
               raw=dict(pct=round(raw[-1], 3), avg7=round(r7[-1], 3), avg30=round(r30[-1], 3)))
    if adj:
        ud = [(usdt[d] - 1) * 100 for d in days]; u7, u30 = _ma(ud, 7), _ma(ud, 30)
        out.update(deep=round(_q(a7, .05), 4), rearm=0.0, band=[round(_q(a7, .10), 4), round(_q(a7, .90), 4)],
                   usdt=dict(px=round(usdt[days[-1]], 5), disc=round(ud[-1], 3), disc7=round(u7[-1], 3), disc30=round(u30[-1], 3), disc7_pct_own=_pctl(u7, u7[-1])),
                   note='Coinbase BTC-USD ÷（Binance BTC-USDT × Coinbase USDT-USD）每日收盤 − 1，已扣掉 USDT 對美元的折溢價；只作讀值')
    else:
        out.update(deep=-0.15, rearm=-0.05, band=[-0.02, 0.02], usdt=None,
                   note='Coinbase BTC-USD ÷ Binance BTC-USDT 每日收盤 − 1（今天取不到 USDT-USD，沒有扣掉 USDT 的折溢價）；只作讀值')
    return out
