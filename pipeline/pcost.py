#!/usr/bin/env python3
"""比特幣生產成本（2026-11-17 使用者要求：看了 CryptoWallSt_ 的「Produktionskosten」回測後說「做」）。

模型是 jv_finance 開源的 TradingView「Bitcoin Cost Of Production」：成本 ＝ α × 難度^k ÷ 每天發行量（區塊獎勵合計＋手續費），
取 90 天平均。原腳本沒公布 α、k；用 CryptoWallSt_ 圖上公布的 9 個成本值反推，α＝12、k＝0.45、90 天簡單平均，誤差都在約 1% 以內。
α、k 是拿同一段價格歷史擬合的，曲線本來就會貼在過去的低點下面，回測命中率會偏高；網站上照實寫。

資料：Bitview 的 difficulty、subsidy_sum_24h、fee_share_24h（手續費佔礦工收入 %）、price_close，每天 2 次請求（bv_more.fetch）。
手續費 BTC ＝ 獎勵 × 佔比 ÷ (1 − 佔比)，所以發行量 ＝ 獎勵 ÷ (1 − 佔比)。只作讀值。"""
import datetime as dt, statistics as st
import bv_more

ALPHA, K, N = 12, .45, 90
GAP = 14             # 14 天內再跌破算同一次
SINCE = '2015-01-01'  # 回測從這天起（2015 年以前價格沒有跌破過）
ROW_FROM = '2013-01-01'
HALV = ['2012-11-28', '2016-07-09', '2020-05-11', '2024-04-20']
NEXT_HALV = '2028-04'   # 估計（每 210,000 個區塊）
EP = dt.date(1970, 1, 1)
dn = lambda d: (dt.date.fromisoformat(d) - EP).days


def build(last, S=None, px=None):
    """px＝全站統一的每日收盤（collect.py 的 PXC，Kraken 優先）；有就蓋過 Bitview 的價格，和其他卡同一天的收盤一致"""
    px = px or {}
    S = S or bv_more.fetch(['price_close', 'difficulty', 'subsidy_sum_24h', 'fee_share_24h'])
    day = lambda i: (bv_more.E0 + dt.timedelta(days=bv_more.START + i)).isoformat()
    n = min(len(v) for v in S.values())
    D, P, R = [], {}, {}
    for i in range(n):
        d = day(i)
        if d > last: break
        pv, df, sb, fs = (S[k][i] for k in ('price_close', 'difficulty', 'subsidy_sum_24h', 'fee_share_24h'))
        if not (pv and df and sb) or fs is None or fs >= 100: continue
        D.append(d); P[d] = px.get(d, pv); R[d] = ALPHA * df ** K / (sb / (1 - fs / 100))
    if not D or D[-1] < (dt.date.fromisoformat(last) - dt.timedelta(days=3)).isoformat(): raise RuntimeError(f'Bitview 還沒有 {last} 的資料')
    C = {}
    for i in range(N - 1, len(D)): C[D[i]] = sum(R[D[j]] for j in range(i - N + 1, i + 1)) / N
    M = [d for d in D if d in C]; ix = {d: i for i, d in enumerate(M)}

    def fwd(d, h):
        t = dn(d) + h; j = next((k for k in range(ix[d], len(M)) if dn(M[k]) >= t), None)
        return round((P[M[j]] / P[d] - 1) * 100, 1) if j is not None and dn(M[j]) - t <= 3 else None

    def mdd(d, h):
        t = dn(d) + h; w = [P[M[k]] for k in range(ix[d] + 1, len(M)) if dn(M[k]) <= t]
        return round((min(w) / P[d] - 1) * 100, 1) if w and dn(M[-1]) >= t else None

    cross, prev = [], None
    for d in M:
        b = P[d] < C[d]
        if b and prev is False: cross.append(d)
        prev = b
    sig, lastc = [], None
    for d in cross:
        if d >= SINCE and (lastc is None or dn(d) - dn(lastc) > GAP): sig.append(d)
        lastc = d
    ev = [dict(d=d, px=round(P[d]), cost=round(C[d]), f30=fwd(d, 30), f90=fwd(d, 90), f180=fwd(d, 180), f365=fwd(d, 365), dd90=mdd(d, 90)) for d in sig]

    def stat(k):
        v = [e[k] for e in ev if e[k] is not None]
        return dict(n=len(v), up=sum(x > 0 for x in v), med=round(st.median(v), 1)) if v else None

    def base(h):
        v = [x for d in M if d >= SINCE for x in [fwd(d, h)] if x is not None]
        return dict(n=len(v), up=round(sum(x > 0 for x in v) / len(v) * 100), med=round(st.median(v), 1))

    lows = []
    for a, b in bv_more.LOWS:   # 歷次週期低點那段時間，價格離成本最近（最低）的一天
        w = [d for d in M if a <= d <= b]
        if w: m = min(w, key=lambda d: P[d] / C[d]); lows.append(dict(d=m, px=round(P[m]), cost=round(C[m]), gap=round((P[m] / C[m] - 1) * 100, 1)))
    d1 = M[-1]; gap = (P[d1] / C[d1] - 1) * 100; k = len(M) - 1
    while k > 0 and (P[M[k - 1]] < C[M[k - 1]]) == (P[d1] < C[d1]): k -= 1
    rows = []
    for i in range(len(M) - 1, -1, -2):   # 每 2 天一點，從最新一天往回
        if M[i] < ROW_FROM: break
        rows.append([dn(M[i]), round(P[M[i]], 2), round(C[M[i]], 2)])
    rows.reverse()
    bw = [d for d in M if d >= SINCE]
    worst = [e for e in ev if e['dd90'] is not None]
    return dict(date=d1, price=round(P[d1]), cost=round(C[d1]), gap=round(gap, 1), below=P[d1] < C[d1], since=M[k], run=dn(d1) - dn(M[k]),
                c30=round(C[M[max(0, len(M) - 31)]]), events=ev, crosses=len([d for d in cross if d >= SINCE]),
                s30=stat('f30'), s90=stat('f90'), s180=stat('f180'), b30=base(30), b90=base(90), b180=base(180),
                worst=min(worst, key=lambda e: e['dd90']) if worst else None,
                share=round(sum(P[d] < C[d] for d in bw) / len(bw) * 100, 1), lows=lows, halv=HALV, next_halv=NEXT_HALV,
                deep=(lambda m: dict(d=m, gap=round((P[m] / C[m] - 1) * 100, 1)))(min(bw, key=lambda d: P[d] / C[d])),
                alpha=ALPHA, k=K, n=N, rows=rows, src='Bitview',
                note='成本＝α × 難度^k ÷ 每天發行量（獎勵＋手續費），%d 天平均；events＝%s 起收盤跌破成本（%d 天內再跌破算同一次），f30／f90／f180／f365＝之後漲跌 %%、dd90＝90 天內最大跌幅；'
                     'lows＝歷次週期低點那段時間價格離成本最近的一天；α、k 用同一段歷史擬合，只作讀值' % (N, SINCE, GAP))
