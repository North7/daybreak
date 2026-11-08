"""晨昏指數（Dawn–Dusk Index；2026-11-08 使用者要求「用現在所有數據做一個更準確的週期圖，新的我們自己取名」，和週線多空分數並列）。
把一輪週期當成一天：深夜（底部區）→ 破曉（初升）→ 白晝（上升）→ 黃昏（過熱）→ 入夜（下跌）。
  熱度 0–100：五項估值各自和「過去 4 年」比的百分位，取平均。這五項是研究時約 20 個候選裡和事後週期位置最貼近的：
    長期持有者 NUPL、未實現獲利 ÷ 市值、冪律殘差（log 價格 − 只用當天以前資料擬合的冪律）、儲備風險（log）、MVRV-Z（市值 − 實現市值，÷ 到當天為止的市值標準差）。
  方向：四項趨勢各除以「到當天為止」的絕對值中位數取 tanh，平均；連續 4 週在另一邊才翻轉：
    價格 ÷ 200 日均線、價格 ÷ 短期持有者成本、aSOPR 30 日平均、實現獲利 ÷ 虧損 90 日平均（log10）。
  階段：熱度 ≥ 80 黃昏、≤ 10 深夜；其餘看方向：空方入夜；多方且熱度 < 50 破曉、≥ 50 白晝。
所有標準化都只用當天以前的資料（不偷看未來）。研究（2013–2025，666 週）：熱度和事後週期位置的等級相關 0.82（週線多空分數 0.49）；
  熱度 ≥ 80 之後一年中位數約 −3%（週線多空分數的「過熱」之後 +89%）。近兩輪鏈上估值都比價格先見頂（2021、2025），黃昏常提早出現。只作讀值。"""
import bisect, datetime as dt, math

EP = dt.date(1970, 1, 1)
dn = lambda s: (dt.date.fromisoformat(s) - EP).days
ds = lambda n: (EP + dt.timedelta(days=n)).isoformat()
HOT, COLD, MID, CONFIRM, WIN = 0.8, 0.1, 0.5, 4, 1460
HK = ('lnupl', 'rup', 'pl', 'rr', 'mvz')
TK = ('d200', 'sth', 'asopr', 'rpl')
FROM = '2013-01-01'


def _pct(ser, D, win=WIN, minn=365):
    """每天 → 這個值在最近 win 天（到今天為止）裡的百分位 0..1"""
    out, hist, q = {}, [], []
    for d in D:
        v = ser.get(d)
        if v is None: continue
        bisect.insort(hist, v); q.append(v)
        if len(q) > win: hist.pop(bisect.bisect_left(hist, q.pop(0)))
        if len(hist) >= minn: out[d] = (bisect.bisect_left(hist, v) + bisect.bisect_right(hist, v)) / 2 / len(hist)
    return out


def _tz(ser, D, minn=180):
    """每天 → tanh(值 ÷ 到今天為止的絕對值中位數)"""
    out, h = {}, []
    for d in D:
        v = ser.get(d)
        if v is None: continue
        bisect.insort(h, abs(v))
        if len(h) >= minn: out[d] = math.tanh(v / (h[len(h) // 2] or 1e-9))
    return out


def _ma(ser, n, D):
    out, q, s = {}, [], 0.0
    for d in D:
        v = ser.get(d)
        if v is None: continue
        q.append(v); s += v
        if len(q) > n: s -= q.pop(0)
        if len(q) == n: out[d] = s / n
    return out


def _avg(src, keys, D, need):
    out = {}
    for d in D:
        v = [src[k][d] for k in keys if d in src[k]]
        if len(v) >= need: out[d] = sum(v) / len(v)
    return out


def stage_of(h, reg):
    if h >= HOT: return 4
    if h <= COLD: return 0
    if reg < 0: return 1
    return 2 if h < MID else 3


def build(bv, cm, rpl, last, px_show=None, tops=(), bottoms=()):
    """bv：bitview.cols()；cm：CoinMetrics [(date, 價格, MVRV, 市值, 流通量, 交易所供給)]；rpl：CheckOnChain 實現獲利 ÷ 虧損 {date: 值 或 (值, 價格)}"""
    rows = [x for x in cm if x[0] <= last and x[1] and x[3]]
    D = [x[0] for x in rows]
    if len(D) < 2000: return None
    px = {x[0]: x[1] for x in rows}; mcap = {x[0]: x[3] for x in rows}; rcap = {x[0]: x[3] / x[2] for x in rows if x[2]}
    pxs = {d: (px_show or {}).get(d, px[d]) for d in D}   # 顯示與報酬用網站統一收盤；指標本身用 CoinMetrics 價格
    raw = {k: {} for k in HK + TK}
    g = lambda k: bv.get(k) or {}
    for d in D:
        if g('lnupl').get(d) is not None: raw['lnupl'][d] = g('lnupl')[d]
        if g('rup').get(d) is not None: raw['rup'][d] = g('rup')[d]
        if g('rr').get(d): raw['rr'][d] = math.log(g('rr')[d])
    # 冪律殘差：log 價格對 log（創世區塊後天數）做最小平方，只用到當天的資料；每 30 天重擬一次
    sx = sy = sxx = sxy = 0.0; n = 0; fit = None
    for i, d in enumerate(D):
        x = math.log(dn(d) - dn('2009-01-03')); y = math.log(px[d]); sx += x; sy += y; sxx += x * x; sxy += x * y; n += 1
        if d >= '2012-01-01' and (fit is None or i % 30 == 0):
            b = (sxy - sx * sy / n) / (sxx - sx * sx / n); fit = (sy / n - b * sx / n, b)
        if fit: raw['pl'][d] = y - (fit[0] + fit[1] * x)
    s1 = s2 = 0.0; n = 0
    for d in D:   # MVRV-Z：(市值 − 實現市值) ÷ 到當天為止的市值標準差
        m = mcap[d]; s1 += m; s2 += m * m; n += 1
        if n > 365 and d in rcap: raw['mvz'][d] = (m - rcap[d]) / math.sqrt(max(1e-9, s2 / n - (s1 / n) ** 2))
    m200 = _ma(px, 200, D); asopr30 = _ma(g('asopr'), 30, D)
    rr_ = {d: (v[0] if isinstance(v, (list, tuple)) else v) for d, v in (rpl or {}).items()}; rpl90 = _ma(rr_, 90, sorted(rr_))
    for d in D:
        if d in m200: raw['d200'][d] = px[d] / m200[d] - 1
        if g('sth').get(d): raw['sth'][d] = px[d] / g('sth')[d] - 1
        if d in asopr30: raw['asopr'][d] = asopr30[d] - 1
        if rpl90.get(d): raw['rpl'][d] = math.log10(rpl90[d])
    P = {k: _pct(raw[k], D) for k in HK}; Z = {k: _tz(raw[k], D) for k in TK}
    heat = _avg(P, HK, D, 4); trend = _avg(Z, TK, D, 3)
    W = [d for d in D if d >= FROM and d in heat and d in trend][::-1][::7][::-1]   # 由最新一天往回每 7 天一點
    reg, run, R, flips = (1 if trend[W[0]] >= 0 else -1), 0, {}, []
    for j, d in enumerate(W):
        s = 1 if trend[d] >= 0 else -1
        run = run + 1 if s != reg else 0
        if run >= CONFIRM: reg, run = s, 0; flips.append(dict(date=W[j - CONFIRM + 1], dir=s))
        R[d] = reg
    ST = {d: stage_of(heat[d], R[d]) for d in W}
    d1 = W[-1]; idx = {d: i for i, d in enumerate(D)}
    fwd = lambda d, n: (pxs[D[idx[d] + n]] / pxs[d] - 1) * 100 if idx[d] + n < len(D) else None
    def st_(xs):
        xs = sorted(x for x in xs if x is not None); k = len(xs)
        return dict(n=k, up=round(sum(x > 0 for x in xs) / k * 100), med=round(xs[k // 2] if k % 2 else (xs[k // 2 - 1] + xs[k // 2]) / 2)) if k else dict(n=0)
    stats = [dict(stage=k, weeks=sum(1 for d in W if ST[d] == k), y1=st_([fwd(d, 364) for d in W if ST[d] == k]), m6=st_([fwd(d, 182) for d in W if ST[d] == k])) for k in range(5)]
    base = st_([fwd(d, 364) for d in W])
    qs = sorted((heat[d], fwd(d, 364)) for d in W if fwd(d, 364) is not None); nq = len(qs)
    quint = [round(sorted(y for _, y in qs[i * nq // 5:(i + 1) * nq // 5])[(nq // 5) // 2]) for i in range(5)] if nq >= 50 else None
    near = lambda t, f: f([heat[d] for d in W if abs(dn(d) - dn(t)) <= 28] or [float('nan')])   # 頂／底前後 4 週內的最高／最低熱度
    marks = [dict(date=t[0], kind='top', heat=round(near(t[0], max) * 100)) for t in tops if t[0] >= FROM] + \
            [dict(date=b[0], kind='bottom', heat=round(near(b[0], min) * 100)) for b in bottoms if b[0] >= FROM]
    run_w = 0
    for d in reversed(W):
        if ST[d] != ST[d1]: break
        run_w += 1
    lf = flips[-1] if flips else None
    return dict(date=d1, heat=round(heat[d1] * 100, 1), heat4=round(heat[W[-5]] * 100, 1), heat13=round(heat[W[-14]] * 100, 1), stage=ST[d1], stage_weeks=run_w,
                regime=R[d1], since=lf['date'] if lf else None, weeks=(dn(d1) - dn(lf['date'])) // 7 if lf else None, trend=round(trend[d1], 2),
                heat_c=[dict(key=k, raw=round(raw[k][d1], 4) if d1 in raw[k] else None, pct=round(P[k][d1] * 100) if d1 in P[k] else None) for k in HK],
                trend_c=[dict(key=k, raw=round(raw[k][d1], 4) if d1 in raw[k] else None, z=round(Z[k][d1], 2) if d1 in Z[k] else None) for k in TK],
                stats=stats, base=base, quint=quint, marks=marks, flips=flips[-8:], th=dict(hot=round(HOT * 100), cold=round(COLD * 100), mid=round(MID * 100)),
                rows=[[dn(d), round(heat[d] * 100, 1), round(pxs[d]), ST[d]] for d in W],
                note='熱度＝五項估值和過去 4 年比的百分位平均；方向＝四項趨勢，連續 4 週才翻；只用當天以前的資料；只作讀值')
