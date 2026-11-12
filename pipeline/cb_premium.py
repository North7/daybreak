#!/usr/bin/env python3
"""Coinbase 溢價（2026-11-12 起扣掉 USDT 對美元的折溢價）。

原本：Coinbase BTC-USD ÷ Binance BTC-USDT − 1。USDT 不等於 1 美元時，這個數字裡混了 USDT 自己的折溢價：
2026-11-10 沒扣的 7 日平均是 −0.137%，其中約 −0.13% 是 USDT 低於 1 美元，扣掉後只剩 −0.007%。
現在：Coinbase BTC-USD ÷（Binance BTC-USDT × Coinbase USDT-USD）− 1，三個都用每日 UTC 收盤。
扣掉之後兩地價差只有幾個基點（近四年 7 日平均的 5%–95% 大約在 −0.012%～+0.015%），所以門檻改用自己的歷史分位，不再用固定的 −0.15%。
沒扣的數字（raw）和 USDT 對美元（usdt）都留著：USDT 折價本身代表有人把穩定幣換回美元。
usdt（2026-11-12 加統計）：USDT 對美元自己的深度折價線、歷次跌破的段落、這個月的平均（見 usdt_stats），新版首頁有單獨一張圖。
neg（2026-11-12）：沒扣的溢價「連續為負」的段落，每一段拆成 USDT 折價和扣掉後剩下的兩塊（見 streaks）。
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


def streaks(rows, min_n=19, th=-0.01):
    """沒扣 USDT 的每日溢價連續小於 0 的段落（2026-11-12）。rows＝build() 的 rows（[日, 扣掉後, 收盤, 沒扣, USDT]）。
    每一段拆成三個平均：沒扣的（raw）、USDT 對美元的折溢價（usdt）、扣掉後剩下的（adj）。
    list＝連負 min_n 天以上的段落（含還在進行的），cur＝現在這一段（不管幾天；今天不是負的就是 None），
    rank＝現在這一段在 list 裡依天數排第幾，n20＝扣掉後近 20 天有幾天小於 0。
    th：結束的段落裡扣掉後平均還低於 th 的算「扣完還是負的」（deep），其他算「扣完接近 0」（flat）。只作讀值。"""
    rs = [r for r in rows if r[3] is not None and r[4] is not None and r[1] is not None]
    if len(rs) < 60: return None
    def one(i, j, opn):
        g = rs[i:j + 1]; n = len(g)
        return dict(a=g[0][0], b=g[-1][0], n=n, raw=round(sum(r[3] for r in g) / n, 3), usdt=round(sum((r[4] - 1) * 100 for r in g) / n, 3),
                    adj=round(sum(r[1] for r in g) / n, 5), p0=g[0][2], p1=g[-1][2], open=opn)
    out = []; i0 = None
    for i, r in enumerate(rs):
        if r[3] < 0:
            if i0 is None: i0 = i
        elif i0 is not None: out.append(one(i0, i - 1, False)); i0 = None
    cur = one(i0, len(rs) - 1, True) if i0 is not None else None
    lst = [x for x in out if x['n'] >= min_n] + ([cur] if cur and cur['n'] >= min_n else [])
    done = [x for x in lst if not x['open']]; deep = [x for x in done if x['adj'] <= th]; flat = [x for x in done if x['adj'] > th]
    rank = 1 + sum(x['n'] > cur['n'] for x in lst) if cur and cur['n'] >= min_n else None
    return dict(min=min_n, th=th, since=rs[0][0], list=lst, cur=cur, rank=rank, longest=max((x['n'] for x in lst), default=None),
                n20=sum(r[1] < 0 for r in rs[-20:]), deep=len(deep), flat=len(flat),
                flat_rng=[min(x['adj'] for x in flat), max(x['adj'] for x in flat)] if flat else None,
                deep_span=[min(x['a'] for x in deep), max(x['b'] for x in deep)] if deep else None)


def usdt_stats(rows):
    """USDT 對美元（Coinbase USDT-USD 每日收盤 − 1）自己的統計（2026-11-12，使用者要求 USDT 單獨一張圖）。rows＝build() 的 rows。
    deep／hi＝7 日平均近四年第 5／95 百分位；ep＝7 日平均跌破 deep 的段落（回到第 25 百分位以上才算結束），
    每段記開始、結束、最深的值和日期、開始那天的收盤、開始後 30 天的漲跌（r30，還沒滿 30 天是 None）；
    base＝隨便一天 30 天後價格較高的比例；mon＝這個月到目前的平均價格和它在所有月份裡排第幾低。只作讀值。"""
    rs = [r for r in rows if r[4] is not None and r[2] is not None]
    if len(rs) < 60: return {}
    n = len(rs); d = [(r[4] - 1) * 100 for r in rs]; a7 = _ma(d, 7); deep, hi, re_ = _q(a7, .05), _q(a7, .95), _q(a7, .25)
    def at(i, k):
        t = rs[i][0] + k
        for j in range(i, n):
            if rs[j][0] >= t: return (rs[j][2] / rs[i][2] - 1) * 100
        return None
    ep = []; on = None
    for i, v in enumerate(a7):
        if v is None: continue
        if v < deep:
            if on is None: on = [i, i, v, i]
            on[1] = i
            if v < on[2]: on[2], on[3] = v, i
        elif on is not None and v > re_: ep.append(on + [False]); on = None
    if on is not None: ep.append(on + [True])
    b30 = [x for x in (at(i, 30) for i in range(n)) if x is not None]
    mon = {}
    for r in rs: mon.setdefault((_EP + dt.timedelta(r[0])).isoformat()[:7], []).append(r[4])
    avg = sorted((sum(v) / len(v), k) for k, v in mon.items()); cur = (_EP + dt.timedelta(rs[-1][0])).isoformat()[:7]
    rank = 1 + [k for _, k in avg].index(cur); oth = [(a, k) for a, k in avg if k != cur]
    return dict(deep=round(deep, 4), hi=round(hi, 4), rearm=round(re_, 4), base=round(sum(x > 0 for x in b30) / len(b30) * 100, 1) if b30 else None,
                ep=[dict(a=rs[e[0]][0], b=rs[e[1]][0], min=round(e[2], 3), d=rs[e[3]][0], p0=rs[e[0]][2], r30=None if at(e[0], 30) is None else round(at(e[0], 30), 1), open=e[4]) for e in ep],
                mon=dict(ym=cur, avg=round(sum(mon[cur]) / len(mon[cur]), 5), n=len(mon[cur]), rank=rank, months=len(avg), low=dict(ym=oth[0][1], avg=round(oth[0][0], 5)) if oth else None))


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
        out['neg'] = streaks(out['rows']); out['usdt'].update(usdt_stats(out['rows']))
    else:
        out.update(deep=-0.15, rearm=-0.05, band=[-0.02, 0.02], usdt=None,
                   note='Coinbase BTC-USD ÷ Binance BTC-USDT 每日收盤 − 1（今天取不到 USDT-USD，沒有扣掉 USDT 的折溢價）；只作讀值')
    return out
