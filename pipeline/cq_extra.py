"""2026-11-06 指標擴充（使用者：「6 個都做」）。全部用免費資料，不佔 bitcoin-data 額度：
① 交易所淨流量（CoinMetrics 社群版 FlowInExNtv／FlowOutExNtv）
② 現貨 vs 永續需求（現貨＝表觀需求 ad；永續＝OKX 合約主動買 − 主動賣，rubik，快取 coc_cache/okx_taker.json 的 perp）
③ ETF 持有者成本（The Block 各檔 ETF 逐日淨流量 ÷ 當天收盤，平均成本法；不含 GBTC：它在轉換前就持有約 62 萬顆，成本不是流量買出來的）
④ 一年累計淨實現損益（顆）（CoinMetrics：實現市值當日變化 − 新發行，同 collect.py G1e，÷ 當天價格）
⑤ 韓國溢價（Upbit KRW-BTC ÷（美元收盤 × 美元兌韓元）− 1；匯率用歐洲央行參考匯率 Frankfurter，失敗退回 FRED DEXKOUS）
⑥ 每輪資金效率（CoinMetrics 實現市值：每輪從底部到頂部流入多少資金、價格漲幾倍）
每項附回測或歷史對照，只作讀值、不是買賣訊號。x 一律為 1970-01-01 起的天數。"""
import bisect, csv, datetime as dt, io, json, statistics as st, time, urllib.parse, urllib.request
from stage_viz import dn, ds, thin
from oc_extra import _fwd, _base, _stat
from bv_extra import _roll, _zone_eps

UA = {'User-Agent': 'Mozilla/5.0 (daybreak data pipeline)', 'Accept': 'application/json'}


def _get(url, raw=False, tries=3, timeout=40):
    for k in range(tries):
        try:
            b = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
            return b.decode() if raw else json.loads(b)
        except Exception:
            if k == tries - 1: raise
            time.sleep(2 * (k + 1))


def _pxf(px):
    return lambda d: px.get(d)


# ---------- ① 交易所淨流量 ----------
# 淨流量＝流入 − 流出（顆，CoinMetrics 依交易所地址歸屬，會事後修正）。30 天合計為負＝幣在離開交易所（買了提走、放冷錢包），正＝幣在流向交易所（準備賣）。
#   強流出／強流入＝30 天合計在近 4 年的最低／最高 10%（流量規模隨交易所地址變多而變大，用近 4 年比）
def exflow_viz(cmj, px, last, step=3):
    P = _pxf(px)
    F = {x['time'][:10]: (float(x['FlowInExNtv']), float(x['FlowOutExNtv'])) for x in cmj if x.get('FlowInExNtv') and x.get('FlowOutExNtv') and x['time'][:10] <= last}
    D = [d for d in sorted(F) if d >= '2013-01-01' and P(d)]
    if len(D) < 1500: return None
    net = {d: F[d][0] - F[d][1] for d in D}; s30 = {}
    for j, d in enumerate(D):
        if j >= 29 and dn(d) - dn(D[j - 29]) == 29: s30[d] = sum(net[D[k]] for k in range(j - 29, j + 1))
    S = [d for d in D if d in s30]; ix = {d: i for i, d in enumerate(S)}
    p4 = _roll(s30, S); R4 = [d for d in S if d in p4]; rx = {d: i for i, d in enumerate(R4)}
    out_eps = _zone_eps(p4, R4, rx, P, lambda v: v <= 10); in_eps = _zone_eps(p4, R4, rx, P, lambda v: v >= 90)
    d1 = S[-1]; back = lambda n: max((d for d in S if dn(d) <= dn(d1) - n), default=None); d30 = back(30)
    run = 0
    for d in reversed(S):
        if (s30[d] < 0) == (s30[d1] < 0): run += 1
        else: break
    rows = thin([[dn(d), round(P(d)), round(net[d]), round(s30[d])] for d in S if d >= '2017-01-01'], step)
    if rows[-1][0] != dn(d1): rows.append([dn(d1), round(P(d1)), round(net[d1]), round(s30[d1])])
    return dict(date=d1, net=round(net[d1]), s30=round(s30[d1]), s30_30=round(s30[d30]) if d30 else None, pct4=p4.get(d1), run=run, out=s30[d1] < 0,
                out_eps=[{k: e[k] for k in ('start', 'end')} for e in out_eps], out_last=out_eps[-3:], n_out=len(out_eps), out_r90=_stat([e['r90'] for e in out_eps]), in_eps=[{k: e[k] for k in ('start', 'end')} for e in in_eps], in_last=in_eps[-3:], n_in=len(in_eps), in_r90=_stat([e['r90'] for e in in_eps]),
                base90=_base(S, ix, P, 90, '2015-01-01'), rows=rows, src='CoinMetrics',
                note='流入 − 流出（顆，CoinMetrics 社群版，依交易所地址歸屬、會事後修正）；強流出／強流入＝30 天合計在近 4 年最低／最高 10%；只作讀值')


# ---------- ② 現貨 vs 永續需求 ----------
# 現貨需求＝表觀需求（30 天新挖出的幣 − 1 年以上未動供給的變化，顆，見 stage_viz.ad_viz）；永續需求＝OKX 合約 30 天主動買 − 主動賣（美元）。
#   兩條單位不同，圖上各除以自己近一年絕對值的最大值（−1 到 1），只看方向與相對強弱。回測：現貨需求 30 天合計由負轉正（隔 60 天以上）之後 60 天的漲跌
def demand_viz(ad, perp, px, last):
    if not ad or not ad.get('rows'): return None
    A = [(r[0], r[1], r[3]) for r in ad['rows'] if r[1] is not None]   # (x, 30 天表觀需求, 價格)；每 3 天一點
    Ad = {r[0]: r[1] for r in A}; Pd = {r[0]: r[2] for r in A}
    flips, prev = [], None
    for (x0, a0, _), (x1, a1, p1) in zip(A, A[1:]):
        if a0 < 0 <= a1 and (prev is None or x1 - prev > 60):
            j = next((r for r in A if r[0] >= x1 + 60), None)
            flips.append(dict(date=ds(x1), price=round(p1), r60=round((j[2] / p1 - 1) * 100, 1) if j and j[0] - x1 <= 66 else None)); prev = x1
    base = [(b[2] / a[2] - 1) * 100 for a in A for b in [next((r for r in A if r[0] >= a[0] + 60), None)] if b and b[0] - a[0] <= 66]
    pdays = {d: v[0] - v[1] for d, v in (perp or {}).items() if d <= last}
    PD = sorted(pdays); p30 = {}
    for j in range(29, len(PD)):
        if dn(PD[j]) - dn(PD[j - 29]) == 29: p30[PD[j]] = sum(pdays[PD[k]] for k in range(j - 29, j + 1))
    x_last = A[-1][0]; yr = [abs(v) for x, v in Ad.items() if x > x_last - 365] or [1]; ms = max(yr) or 1
    pyr = [abs(v) for d, v in p30.items() if dn(d) > dn(max(p30)) - 365] if p30 else [1]; mp = max(pyr) or 1
    x0 = dn('2024-01-01')
    rows = [[x, round(Pd[x]), round(Ad[x] / ms, 3), None, round(Ad[x])] for x, _, _ in A if x >= x0]
    pr = {dn(d): v for d, v in p30.items()}
    for r in rows:
        k = min((x for x in pr if abs(x - r[0]) <= 1), key=lambda x: abs(x - r[0]), default=None)
        if k is not None: r[3] = round(pr[k] / mp, 3); r.append(round(pr[k] / 1e6))
        else: r.append(None)
    pl = max(p30) if p30 else None
    r60 = [f['r60'] for f in flips if f['r60'] is not None]
    return dict(date=ds(x_last), spot=round(A[-1][1]), spot_pos=A[-1][1] >= 0, perp=round(p30[pl] / 1e6) if pl else None, perp_date=pl, perp_pos=(p30[pl] >= 0) if pl else None,
                flips=flips[-8:], n_flips=len(flips), r60=dict(n=len(r60), up=sum(v > 0 for v in r60), med=round(st.median(r60), 1) if r60 else None),
                base60=dict(n=len(base), up=round(sum(v > 0 for v in base) / len(base) * 100) if base else None, med=round(st.median(base), 1) if base else None),
                perp_since=PD[0] if PD else None, rows=rows, src='CheckOnChain（表觀需求）· OKX',
                note='現貨＝表觀需求 30 天（顆）；永續＝OKX 合約 30 天主動買 − 主動賣（美元，日界 UTC+8）；圖上各除以自己近一年絕對值最大值；只作讀值')


# ---------- ③ ETF 持有者成本 ----------
TB = ['https://www.theblock.co/api/tbco/charts/chart/etfs/bitcoin-etf/spot-bitcoin-etf-flows', 'https://www.theblock.co/api/charts/chart/etfs/bitcoin-etf/spot-bitcoin-etf-flows']


def _tb_series():
    err = None
    for u in TB:
        try: js = _get(u); return (js.get('data') or js)['chart']['jsonFile']['Series']
        except Exception as e: err = e
    raise RuntimeError(f'The Block：{err}')


def etf_cost_viz(px, last, step=1):
    P = _pxf(px); S = _tb_series(); tot, alltot = {}, {}
    for k, f in S.items():
        for p in f['Data']:
            if p.get('Result') is None: continue
            d = dt.datetime.fromtimestamp(p['Timestamp'], dt.timezone.utc).date().isoformat()
            if d > last: continue
            alltot[d] = alltot.get(d, 0) + p['Result']
            if 'GBTC' not in k.upper(): tot[d] = tot.get(d, 0) + p['Result']
    cu = cb = 0; C = {}
    for d in sorted(tot):   # 平均成本法：流入以當天收盤買進；流出依當時平均成本移出
        p = P(d)
        if not p: continue
        btc = tot[d] / p
        if tot[d] >= 0: cu += tot[d]; cb += btc
        else: avg = cu / cb if cb else p; cb += btc; cu += btc * avg
        if cb > 0: C[d] = (cu / cb, cb)
    D = sorted(C)
    if len(D) < 200: return None
    d1 = D[-1]; c1, h1 = C[d1]; p1 = P(d1)
    below = 0
    for d in reversed(D):
        if P(d) < C[d][0]: below += 1
        else: break
    crosses = [d for a, d in zip(D, D[1:]) if (P(a) < C[a][0]) != (P(d) < C[d][0])]
    gp = {d: (P(d) / C[d][0] - 1) * 100 for d in D}; dmin = min(D, key=gp.get)
    s30 = lambda T: sum(v for d, v in T.items() if dn(d1) - 30 < dn(d) <= dn(d1)) / 1e6
    rows = thin([[dn(d), round(P(d)), round(C[d][0]), round(C[d][1] / 1e3, 1), round(gp[d], 1)] for d in D], step)
    dl = max((d for d in px if d <= last), default=d1); pl = P(dl) or p1   # ETF 流量晚一天公布：成本用最後一天，價格用最新收盤
    return dict(date=d1, cost=round(c1), held=round(h1), price=round(p1), gap=round((p1 / c1 - 1) * 100, 1), px_date=dl, px_now=round(pl), gap_now=round((pl / c1 - 1) * 100, 1), below=pl < c1, run=below if p1 < c1 else 0,
                last_cross=crosses[-1] if crosses else None, n_cross=len(crosses), days_below=sum(gp[d] < 0 for d in D), n_days=len(D), since=D[0], min_gap=round(gp[dmin], 1), min_date=dmin, flow30=round(s30(tot)), flow30_all=round(s30(alltot)), funds=len(S), rows=rows, src='The Block',
                note='不含 GBTC 的現貨 ETF：每天淨流量 ÷ 當天收盤＝買進（或賣出）的顆數，平均成本法；GBTC 轉換前就持有約 62 萬顆，成本不是流量買出來的，所以不算；推算、只作讀值')


# ---------- ④ 一年累計淨實現損益（顆） ----------
def npl365_viz(nd, last, bottoms=(), tops=(), step=4):
    """nd＝collect.py G1e 的 [(日期, 價格, 當日淨實現損益美元, 市值)]"""
    B = {d: v / p for d, p, v, _ in nd if p and d <= last}; Px = {d: p for d, p, _, _ in nd}
    D = sorted(B); y = {}
    for j in range(364, len(D)):
        if dn(D[j]) - dn(D[j - 364]) == 364: y[D[j]] = sum(B[D[k]] for k in range(j - 364, j + 1))
    Y = [d for d in sorted(y) if d >= '2012-01-01']
    if len(Y) < 1000: return None
    d1 = Y[-1]; back = lambda n: max((d for d in Y if dn(d) <= dn(d1) - n), default=None); d30 = back(30)
    bt = []
    for b in bottoms:
        bd = b[0] if isinstance(b, (list, tuple)) else b
        w = [d for d in Y if -180 <= dn(d) - dn(bd) <= 240 or (b == bottoms[-1] and d >= bd)]
        if w: m = min(w, key=y.get); bt.append(dict(bottom=bd, date=m, value=round(y[m] / 1e3), now=b == bottoms[-1] and m == d1))
    tp = []
    for t in tops:
        td = t[0] if isinstance(t, (list, tuple)) else t
        w = [d for d in Y if abs(dn(d) - dn(td)) <= 180]
        if w: m = max(w, key=y.get); tp.append(dict(top=td, date=m, value=round(y[m] / 1e3)))
    neg_since = None
    for d in reversed(Y):
        if y[d] < 0: neg_since = d
        else: break
    rows = []
    for i in range(0, len(Y), step):   # 每段取最低（負的深度不會被抽樣抽掉）
        blk = Y[i:i + step]; m = min(blk, key=y.get); rows.append([dn(m), round(Px[m]), round(y[m] / 1e3, 1)])
    if rows[-1][0] != dn(d1): rows.append([dn(d1), round(Px[d1]), round(y[d1] / 1e3, 1)])
    return dict(date=d1, value=round(y[d1] / 1e3), v30=round(y[d30] / 1e3) if d30 else None, neg_since=neg_since, bottoms=bt, tops=tp, rows=rows, src='CoinMetrics',
                note='每天的淨實現損益（實現市值變化 − 新發行，美元）÷ 當天價格，365 天合計（千顆）；CoinMetrics；只作讀值')


# ---------- ⑤ 韓國溢價 ----------
def kp_viz(px, last, step=3):
    P = _pxf(px); up, to = [], None
    for _ in range(18):
        r = _get('https://api.upbit.com/v1/candles/days?market=KRW-BTC&count=200' + ('&to=' + urllib.parse.quote(to) if to else ''))
        if not r: break
        up += r; to = r[-1]['candle_date_time_utc'].replace('T', ' '); time.sleep(0.2)
    U = {x['candle_date_time_utc'][:10]: x['trade_price'] for x in up}
    try:
        fx = {d: v['KRW'] for d, v in _get('https://api.frankfurter.app/2017-12-01..?from=USD&to=KRW')['rates'].items()}; fsrc = '歐洲央行參考匯率（Frankfurter）'
    except Exception:
        fx = {r['observation_date']: float(r['DEXKOUS']) for r in csv.DictReader(io.StringIO(_get('https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXKOUS&cosd=2017-12-01', True, timeout=60))) if r['DEXKOUS'] not in ('', '.')}; fsrc = 'FRED DEXKOUS'
    FD = sorted(fx)
    def fxat(d): i = bisect.bisect_right(FD, d) - 1; return (fx[FD[i]], FD[i]) if i >= 0 else (None, None)
    K = {}
    for d in sorted(U):
        if d > last or not P(d): continue
        r, fd = fxat(d)
        if r and dn(d) - dn(fd) <= 5: K[d] = (U[d] / (P(d) * r) - 1) * 100
    D = sorted(K)
    if len(D) < 500: return None
    a7 = {d: st.mean(K[D[k]] for k in range(max(0, j - 6), j + 1)) for j, d in enumerate(D)}
    p4 = _roll(a7, D); d1 = D[-1]; ix = {d: i for i, d in enumerate(D)}
    hot = _zone_eps(a7, D, ix, P, lambda v: v >= 5); cold = _zone_eps(a7, D, ix, P, lambda v: v <= -1)
    yr = []
    for y in range(int(D[0][:4]), int(d1[:4]) + 1):
        w = [d for d in D if d.startswith(str(y))]
        if w: m = max(w, key=a7.get); n = min(w, key=a7.get); yr.append(dict(year=y, max=round(a7[m], 1), max_date=m, min=round(a7[n], 1), min_date=n))
    rows = thin([[dn(d), round(P(d)), round(K[d], 2), round(a7[d], 2)] for d in D], step)
    if rows[-1][0] != dn(d1): rows.append([dn(d1), round(P(d1)), round(K[d1], 2), round(a7[d1], 2)])
    return dict(date=d1, value=round(K[d1], 2), a7=round(a7[d1], 2), a30=round(st.mean(K[d] for d in D[-30:]), 2), pct4=p4.get(d1), med=round(st.median(K.values()), 2),
                years=yr, fx_src=fsrc, hot=[{k: e[k] for k in ('start', 'end', 'price', 'r90')} for e in hot], hot90=_stat([e['r90'] for e in hot]), cold=[{k: e[k] for k in ('start', 'end', 'price', 'r90')} for e in cold], cold90=_stat([e['r90'] for e in cold]),
                base90=_base(D, ix, P, 90, D[0]), rows=rows, src='Upbit',
                note='Upbit KRW-BTC 日收盤（UTC）÷（美元收盤 × 美元兌韓元）− 1；匯率用歐洲央行參考匯率（週末沿用前一個工作日）；只作讀值')


# ---------- ⑥ 每輪資金效率 ----------
# 每輪從熊市底部到週期頂部：實現市值增加多少（＝真正流入的資金）、價格漲幾倍；「每 10 億美元淨流入推升多少 %」一輪比一輪小
def capeff_viz(mv, last, tops=(), bottoms=()):
    """mv＝collect.py 的 [(日期, 價格, MVRV, 市值, 供給)]"""
    rc = {d: mc / m for d, p, m, mc, _ in mv if m and d <= last}; px = {d: p for d, p, *_ in mv}; mcap = {d: mc for d, p, m, mc, _ in mv}
    D = sorted(rc)
    if not D: return None
    near = lambda t: min(D, key=lambda d: abs(dn(d) - dn(t)))
    w11 = [d for d in D if '2011-06-01' <= d <= '2012-06-01']
    B = ([min(w11, key=px.get)] if w11 else []) + [b[0] for b in bottoms]; T = [t[0] for t in tops]
    cyc = []
    for b in B:
        t = next((t for t in T if t > b), None); b2 = near(b)
        if t:
            t2 = near(t); add = (rc[t2] - rc[b2]) / 1e9; mult = px[t2] / px[b2]
            mca = (mcap[t2] - mcap[b2]) / 1e9; c_ = None
            if cur_days := (dn(D[-1]) - dn(near(B[-1]))) if B else None:   # 同樣是底部後第 N 天（N＝本輪已走的天數）時的讀值，給本輪對照
                e = near(ds(dn(b2) + cur_days)); c_ = dict(add_b=round((rc[e] - rc[b2]) / 1e9, 1), mult=round(px[e] / px[b2], 2))
            cyc.append(dict(bottom=b2, top=t2, rc_b=round(rc[b2] / 1e9, 2), add_b=round(add, 1), mca_b=round(mca), lev=round(mca / add, 1) if add > 0 else None, mult=round(mult, 1), days=dn(t2) - dn(b2), same=c_))
    lb = near(B[-1]) if B else None; d1 = D[-1]
    cur = None
    if lb and lb not in [c['bottom'] for c in cyc]:
        add = (rc[d1] - rc[lb]) / 1e9; mca = (mcap[d1] - mcap[lb]) / 1e9
        cur = dict(bottom=lb, date=d1, rc_b=round(rc[lb] / 1e9, 1), add_b=round(add, 1), mca_b=round(mca), lev=round(mca / add, 1) if add > 0 else None, mult=round(px[d1] / px[lb], 2), days=dn(d1) - dn(lb), rc_now=round(rc[d1] / 1e9))
    return dict(date=d1, cycles=cyc, cur=cur, src='CoinMetrics',
                note='實現市值（市值 ÷ MVRV，CoinMetrics）由熊市底部到週期頂部的增加＝這一輪真正流入的資金；市值增加 ÷ 流入＝每 1 美元流入帶動多少市值；價格倍數同一段；只作讀值')
