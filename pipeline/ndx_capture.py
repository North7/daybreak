"""BTC 對那斯達克 100：跟漲少、跟跌多（2026-11-25 使用者要求，Glassnode 週報〈The Canary in the Coal Mine〉那張 Bitcoin Falls More Than Stocks and Rises Less）。

近 60 個美股交易日：
  跟漲＝那斯達克 100 上漲的日子，BTC 平均漲幅 ÷ 那斯達克平均漲幅（< 1 代表漲得比它少）
  跟跌＝那斯達克 100 下跌的日子，BTC 平均跌幅 ÷ 那斯達克平均跌幅（> 1 代表跌得比它多）
兩個同時成立就是「跟漲少、跟跌多」。進入這個狀態的日子（離上一次進入 45 天內的不另算一段）之後 60 天的 BTC 漲跌做回測，
和任意一天之後 60 天對照。BTC 用網站的日收盤（UTC），美股用紐約收盤，兩者差約 3 小時。只作讀值。
"""
import datetime as dt
import statistics as st

W, FWD, GAP, FROM = 60, 60, 45, '2013-01-01'
dn = lambda d: (dt.date.fromisoformat(d) - dt.date(1970, 1, 1)).days


def build(pxc, ndx, last, step=4):
    days = sorted(pxc); P = lambda d: pxc[d]
    D = sorted(d for d in ndx if d in pxc and d <= last)
    R = [(D[i], pxc[D[i]] / pxc[D[i - 1]] - 1, ndx[D[i]] / ndx[D[i - 1]] - 1) for i in range(1, len(D))]
    cap = []
    for i in range(W - 1, len(R)):
        w = R[i - W + 1:i + 1]; up = [x for x in w if x[2] > 0]; dw = [x for x in w if x[2] < 0]
        if not up or not dw: continue
        uc = st.mean(x[1] for x in up) / st.mean(x[2] for x in up); dc = st.mean(x[1] for x in dw) / st.mean(x[2] for x in dw)
        cap.append((R[i][0], uc, dc, uc < 1 and dc > 1))
    cap = [c for c in cap if c[0] >= FROM]
    if len(cap) < 500: return None
    ix = {d: i for i, d in enumerate(days)}

    def fwd(d):   # 之後 60 個日曆天的 BTC 漲跌（%）；還沒走完回 None
        t = (dt.date.fromisoformat(d) + dt.timedelta(FWD)).isoformat()
        return round((pxc[t] / pxc[d] - 1) * 100, 1) if t in pxc and t <= last else None

    eps, spans, prev, cur = [], [], False, None
    for d, uc, dc, on in cap:
        if on and not prev:
            if not eps or dn(d) - dn(eps[-1]['start']) > GAP: eps.append(dict(start=d, px=round(P(d)), r60=fwd(d)))
            if cur and dn(d) - dn(cur[1]) <= 15: cur[1] = d   # 中間只斷幾天的接成同一段塗色
            else:
                if cur: spans.append(cur)
                cur = [d, d]
        elif on: cur[1] = d
        prev = on
    if cur: spans.append(cur)
    done = [e['r60'] for e in eps if e['r60'] is not None]
    base = [(pxc[(dt.date.fromisoformat(d) + dt.timedelta(FWD)).isoformat()] / pxc[d] - 1) * 100 for d in days
            if cap[0][0] <= d and (dt.date.fromisoformat(d) + dt.timedelta(FWD)).isoformat() in pxc]
    start = {e['start']: e['r60'] for e in eps}; rows = []
    for k, (d, uc, dc, on) in enumerate(cap):
        if k % step and d not in start and k != len(cap) - 1: continue
        rows.append([dn(d), round(P(d)), round(uc * 100, 1), round(dc * 100, 1), start.get(d)])
    d1, uc, dc, on = cap[-1]
    since = None
    if on:
        for c in reversed(cap):
            if not c[3]: break
            since = c[0]
    return dict(date=d1, uc=round(uc * 100, 1), dc=round(dc * 100, 1), on=on, since=since, eps=eps,
                spans=[[dn(a), dn(b)] for a, b in spans], rows=rows,
                back=dict(n=len(done), lower=sum(v < 0 for v in done), med=round(st.median(done), 1) if done else None),
                base=dict(n=len(base), lower=round(sum(v < 0 for v in base) / len(base) * 100), med=round(st.median(base), 1)),
                note='近 60 個美股交易日：那斯達克 100 漲的日子 BTC 平均漲幅 ÷ 那斯達克平均漲幅（跟漲）、跌的日子同樣算（跟跌）；跟漲 < 100% 且跟跌 > 100% 為「跟漲少、跟跌多」；'
                     '相隔 45 天內再進入不另算一段；之後 60 個日曆天的 BTC 漲跌；BTC 用 UTC 日收盤、美股紐約收盤；那斯達克 100 來自 FRED（常晚幾天）；只作讀值')
