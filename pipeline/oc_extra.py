"""2026-11-06 使用者要求：一批鏈上指標與讀法（指標擴充），用本站自己的資料（Bitview，免費、不佔 bitcoin-data 額度）重做。
產品內不寫個人名字。每一項都照實寫回測（樣本數、勝率、和同期任一天比），只作讀值，不是買賣訊號。

第一批：供給分位成本線（quant_viz）、短期持有者虧損比例的歷次（sthl_viz）、相對未實現獲利的地板（rup_viz）、
       全網已實現虧損峰值背離（rloss_viz）、長短期持有者供給比的 30 日變化（lsrchg_viz）。
第二批：資金與價格增量梯度（grad_viz）、鏈上勢能（mom_viz）、回調壓力清單（pullback_viz）。
bv＝bitview.cols(rows)：{欄位: {日期: 值}}；px＝統一收盤（PXC），缺日用 Bitview 自己的收盤。x 一律為 1970-01-01 起的天數。"""
import bisect, math, statistics as st
from stage_viz import dn, ds, thin

QK = [('q45', 45), ('q50', 50), ('q55', 55), ('q60', 60), ('q65', 65), ('q75', 75), ('q85', 85), ('q95', 95)]


def _P(bv, px):
    return lambda d: px.get(d, bv['px'].get(d))


def _fwd(D, ix, P, d, n):
    """d 之後 n 天的漲跌 %（以日期回推，資料不夠回傳 None）"""
    i = ix.get(d)
    if i is None: return None
    t = dn(d) + n
    j = next((k for k in range(i, len(D)) if dn(D[k]) >= t), None)
    return round((P(D[j]) / P(d) - 1) * 100, 1) if j is not None and dn(D[j]) - t <= 3 else None


def _dd(D, ix, P, d, n):
    """d 之後 n 天內的最大跌幅 %（相對 d 當天）"""
    i = ix.get(d); p0 = P(d); t = dn(d) + n
    w = [P(D[k]) for k in range(i + 1, len(D)) if dn(D[k]) <= t]
    return round((min(w) / p0 - 1) * 100, 1) if w and dn(D[-1]) >= t else None


def _base(D, ix, P, n, since):
    """同期任一天的 n 天後漲跌：中位數與上漲比例（給回測對照）"""
    v = [f for d in D if d >= since for f in [_fwd(D, ix, P, d, n)] if f is not None]
    return dict(n=len(v), med=round(st.median(v), 1), up=round(sum(x > 0 for x in v) / len(v) * 100)) if v else None


def _stat(v):
    v = [x for x in v if x is not None]
    return dict(n=len(v), up=sum(x > 0 for x in v), med=round(st.median(v), 1)) if v else dict(n=0, up=0, med=None)


# ---------- 供給分位成本線 ----------
# 全體供給依「最後一次移動時的價格」排序，第 q 百分位的價格（Bitview cost_basis_by_coin_pXX）。價格剛好等於 q 線時，獲利供給 ≈ q%：
#   所以「獲利供給回到 65%」對應的價格就是 0.65 分位線。上方分位線是解套賣壓所在，下方是成本密集的承接區；只作讀值
Q_FROM = '2017-01-01'


def quant_viz(bv, px, last, bottoms=(), step=4):
    P = _P(bv, px); qs = {k: bv.get(k) or {} for k, _ in QK}; ps = bv.get('psip') or {}
    D = [d for d in sorted(qs['q75']) if d <= last and P(d) and all(qs[k].get(d) for k, _ in QK)]
    if len(D) < 1500: return None
    ix = {d: i for i, d in enumerate(D)}; d1 = D[-1]; p1 = P(d1)
    back = lambda n: max((d for d in D if dn(d) <= dn(d1) - n), default=None); d30 = back(30)
    cur = {str(q): round(qs[k][d1]) for k, q in QK}
    chg30 = {str(q): round((qs[k][d1] / qs[k][d30] - 1) * 100, 1) for k, q in QK} if d30 else {}
    below = [q for k, q in QK if qs[k][d1] <= p1]; above = [q for k, q in QK if qs[k][d1] > p1]
    # 站上 0.75 分位：之前連續 ≥ 90 天收在下方
    ups, run, last_above = [], 0, None
    for d in D:
        if P(d) < qs['q75'][d]: run += 1
        else:
            if run >= 90 and d >= '2015-01-01': ups.append(dict(date=d, price=round(P(d)), below_days=run, r90=_fwd(D, ix, P, d, 90), r365=_fwd(D, ix, P, d, 365)))
            run = 0; last_above = d
    # 獲利供給（PSIP）：歷次熊底附近低於 50% 的天數；熊牛過渡期的回調（之前 90 天內 ≥ 75%、之後跌到 ≤ 65%）回到多低
    PD = [d for d in sorted(ps) if d <= last]
    bear50 = []
    for b in bottoms:
        bd = b[0] if isinstance(b, (list, tuple)) else b
        if bd < '2014-01-01': continue
        w = [d for d in PD if abs(dn(d) - dn(bd)) <= 365]
        if w: bear50.append(dict(bottom=bd, days=sum(ps[d] < 50 for d in w), min=round(min(ps[d] for d in w), 1)))
    pulls, i = [], 0
    pix = {d: k for k, d in enumerate(PD)}
    while i < len(PD):
        d = PD[i]
        if d >= '2015-01-01' and ps[d] <= 65 and i and ps[PD[i - 1]] > 65 and any(ps[PD[k]] >= 75 for k in range(max(0, i - 90), i)):
            w = PD[i:i + 61]; m = min(w, key=ps.get)
            pulls.append(dict(date=d, low_date=m, low=round(ps[m], 1), price=round(P(m)) if P(m) else None, r90=_fwd(D, ix, P, m, 90) if m in ix else None))
            i += 60; continue
        i += 1
    rows = thin([[dn(d), round(P(d))] + [round(qs[k][d]) for k, _ in QK] for d in D if d >= Q_FROM], step)
    return dict(date=d1, price=round(p1), cur=cur, chg30=chg30, below=below, above=above, psip=ps.get(d1), psip30=ps.get(d30) if d30 else None,
                last_above75=last_above, below75_days=run, ups75=ups, bear50=bear50, pulls=pulls, keys=[q for _, q in QK], rows=rows, src='Bitview',
                note='全體供給依最後一次移動的價格排序後的第 q 百分位（Bitview cost_basis_by_coin）；價格等於 q 線時獲利供給約 q%；逐筆 UTXO、不是實體調整；只作讀值')


# ---------- 短期持有者虧損比例（＝100 − 短期持有者獲利比例）的歷次 ----------
# 高於 50%＝一半以上的短期持有者在虧損。歷次升到 60% 以上的時間點與之後的漲跌（隔 60 天以上算新的一次）。只作讀值
SL_FROM = '2015-01-01'


def sthl_viz(bv, px, last):
    P = _P(bv, px); sp = bv.get('sthp') or {}
    D = [d for d in sorted(sp) if d <= last and P(d)]
    if len(D) < 1500: return None
    ix = {d: i for i, d in enumerate(D)}; sl = {d: 100 - sp[d] for d in D}; d1 = D[-1]
    H = [d for d in D if d >= SL_FROM]
    eps, prev = [], None
    for d in H:
        if sl[d] >= 60 and (prev is None or dn(d) - dn(prev) > 60) and sl.get(D[ix[d] - 1], 0) < 60:
            w = [x for x in H if dn(d) <= dn(x) <= dn(d) + 60]; m = max(w, key=sl.get)
            eps.append(dict(date=d, price=round(P(d)), peak=round(sl[m], 1), peak_date=m, r30=_fwd(D, ix, P, d, 30), r90=_fwd(D, ix, P, d, 90), dd30=_dd(D, ix, P, d, 30)))
        if sl[d] >= 60: prev = d
    run = 0
    for d in reversed(D):
        if sl[d] >= 50: run += 1
        else: break
    return dict(date=d1, value=round(sl[d1], 1), mean_all=round(st.mean(sl[d] for d in H), 1), mean21=round(st.mean(sl[d] for d in D if d >= '2021-01-01'), 1),
                share50=round(sum(sl[d] >= 50 for d in H) / len(H) * 100, 1), run50=run, eps=eps, base30=_base(D, ix, P, 30, SL_FROM), base90=_base(D, ix, P, 90, SL_FROM),
                stat30=_stat([e['r30'] for e in eps]), stat90=_stat([e['r90'] for e in eps]), since=SL_FROM, src='Bitview',
                note='短期持有者（150 天內移動過的幣）中、目前價格低於最後移動價格的比例（Bitview）；逐筆 UTXO；只作讀值')


# ---------- 相對未實現獲利（RUP）的地板 ----------
# RUP＝全體未實現獲利 ÷ 市值（%）。2012 年起只有週期底部附近會掉到 35% 以下（2015、2018–19、2020/03、2022/11–2023/01、2026/06–08），
#   一般年份的最低點都在 36% 以上。地板＝35%（門檻寫死、不回頭調）。只作讀值
RUP_FLOOR, RUP_FROM = 35.0, '2012-01-01'
# 近地板區（2026-11-11 使用者要求）：35%–37.5%。2012 年起牛市年份的最低點都在 37.5% 以上（2013 45%、2017 46%、2021 51%、2024 47%、2025 42%），
#   掉進這一區的都是熊市後段到復甦初期（2014 年底–2016、2018–20、2022–23、2026）。門檻寫死、不回頭調。
#   回測（寫進 near）：這一區的日子一年後都比當天高，但 90 天後和任一天差不多，而且第一次掉進來之後常常還再跌一段。只作讀值
RUP_NEAR = 37.5


def rup_viz(bv, px, last, tops=(), step=4):
    P = _P(bv, px); r = bv.get('rup') or {}
    D = [d for d in sorted(r) if RUP_FROM <= d <= last and P(d)]
    if len(D) < 1500: return None
    ix = {d: i for i, d in enumerate(D)}; d1 = D[-1]
    eps = []
    for d in D:
        if r[d] > RUP_FLOOR: continue
        if eps and dn(d) - dn(eps[-1]['end']) <= 60:
            e = eps[-1]; e['end'] = d; e['days'] += 1
            if r[d] < e['min']: e['min'], e['min_date'] = r[d], d
        else: eps.append(dict(start=d, end=d, days=1, min=r[d], min_date=d))
    for e in eps:
        e['min'] = round(e['min'], 1); e['price'] = round(P(e['start'])); e['low_price'] = round(P(e['min_date']))
        e['r180'], e['r365'] = _fwd(D, ix, P, e['start'], 180), _fwd(D, ix, P, e['start'], 365)
        w = [d for d in D if 0 <= dn(d) - dn(e['start']) <= 180]   # 進入地板之後 180 天內，價格還再跌多少
        e['dd180'] = round((min(P(d) for d in w) / P(e['start']) - 1) * 100, 1) if w and dn(D[-1]) - dn(e['start']) >= 30 else None
        e['open'] = dn(d1) - dn(e['end']) <= 60 and r[d1] <= RUP_FLOOR
    back = lambda n: max((d for d in D if dn(d) <= dn(d1) - n), default=None); d30 = back(30)
    y = [d for d in D if dn(d) > dn(d1) - 365]; lo = min(y, key=r.get)
    rows = []
    for i in range(0, len(D), step):   # 每段取最低，地板不會被抽樣抽掉
        blk = D[i:i + step]; m = min(blk, key=r.get); rows.append([dn(m), round(P(m)), round(r[m], 2)])
    if rows[-1][0] != dn(d1): rows.append([dn(d1), round(P(d1)), round(r[d1], 2)])
    tv = []   # 各輪週期頂部前後 45 天內的最高值（頂部的讀數一輪比一輪低）
    for t in tops:
        td = t[0] if isinstance(t, (list, tuple)) else t; w = [d for d in D if abs(dn(d) - dn(td)) <= 45]
        if w: m = max(w, key=r.get); tv.append(dict(top=td, date=m, value=round(r[m], 1)))
    yr_lo = [dict(year=y, value=round(min(r[d] for d in D if d.startswith(str(y))), 1)) for y in range(int(D[0][:4]), int(d1[:4]) + 1) if any(d.startswith(str(y)) for d in D)]
    # 近地板區（地板以上、RUP_NEAR 以下）
    N = [dn(d) for d in D]
    def fw(i, n):   # 第 i 天之後 n 天的漲跌 %
        j = bisect.bisect_left(N, N[i] + n)
        return (P(D[j]) / P(D[i]) - 1) * 100 if j < len(D) and N[j] - N[i] - n <= 3 else None
    def fst(I, n):
        v = [x for x in (fw(i, n) for i in I) if x is not None]
        return dict(n=len(v), up=round(sum(x > 0 for x in v) / len(v) * 100), med=round(st.median(v), 1)) if v else None
    inf = lambda d: any(e['start'] <= d <= e['end'] for e in eps)
    neps = []   # 畫圖用：近地板區的期間（不含已經畫成地板區的期間）
    for d in D:
        if r[d] > RUP_NEAR or inf(d): continue
        if neps and dn(d) - dn(neps[-1]['end']) <= 14 and not any(neps[-1]['end'] < e['start'] and e['end'] < d for e in eps): neps[-1]['end'] = d
        else: neps.append(dict(start=d, end=d))
    waves = []   # 每一波：掉到 RUP_NEAR 以下（中間回到上面不超過 60 天算同一波）
    for i, d in enumerate(D):
        if r[d] > RUP_NEAR: continue
        if waves and dn(d) - dn(waves[-1]['end']) <= 60: waves[-1]['end'] = d
        else: waves.append(dict(start=d, end=d, i=i))
    for w in waves:
        i = w.pop('i'); nx = [P(D[k]) for k in range(i, len(D)) if N[k] - N[i] <= 180]
        w['price'] = round(P(w['start'])); w['floor'] = any(w['start'] <= e['start'] <= w['end'] for e in eps)
        w['dd180'] = round((min(nx) / P(w['start']) - 1) * 100, 1) if N[-1] - N[i] >= 30 else None
        f = fw(i, 365); w['r365'] = round(f, 1) if f is not None else None
        w['open'] = dn(d1) - dn(w['end']) <= 60
    NI = [i for i, d in enumerate(D) if RUP_FLOOR < r[d] <= RUP_NEAR]; AI = range(len(D))
    run = 0
    for d in reversed(D):
        if r[d] <= RUP_NEAR: run += 1
        else: break
    ylo = [y for y in yr_lo if y['value'] > RUP_NEAR]
    near = dict(hi=RUP_NEAR, days=len(NI), share=round(len(NI) / len(D) * 100, 1), run=run, eps=neps, waves=waves,
                s90=fst(NI, 90), s365=fst(NI, 365), b90=fst(AI, 90), b365=fst(AI, 365), other_lo=min(ylo, key=lambda y: y['value']) if ylo else None)
    return dict(date=d1, value=round(r[d1], 1), d30=round(r[d30], 1) if d30 else None, floor=RUP_FLOOR, gap=round(r[d1] - RUP_FLOOR, 1),
                zone='floor' if r[d1] <= RUP_FLOOR else 'near' if r[d1] <= RUP_NEAR else None, near=near,
                med=round(st.median(r[d] for d in D), 1), share_below=round(sum(r[d] <= RUP_FLOOR for d in D) / len(D) * 100, 1), tops=tv,
                yr_lo=yr_lo, other_lo=min((y for y in yr_lo if y['value'] > RUP_FLOOR), key=lambda y: y['value'], default=None),
                lo1y=dict(date=lo, value=round(r[lo], 1)), eps=eps, rows=rows, since=RUP_FROM, src='Bitview',
                note='相對未實現獲利＝全體未實現獲利 ÷ 市值（Bitview，逐筆 UTXO）；地板 35% 與近地板區 37.5% 是本站依 2012 年起的歷史設定；只作讀值')


# ---------- 全網已實現虧損：峰值背離 ----------
# 每日已實現虧損（Bitview realized_loss_sum_24h，美元，不是實體調整）÷ 市值。價格擺動低點（前後 7 天最低、比之前 30 天最高跌 ≥ 6%）
#   取前後 3 天內最大的認賠；和前一個擺動低點（75 天內）比：價格更低但認賠峰值小 20% 以上＝背離（想賣的人變少），更大＝投降。
#   搬家日（同一實體內部轉帳，見 cohort_urpd.transfers）那天的虧損不算峰值。2013 年起回測寫在 back。只作讀值
RL_W, RL_DD, RL_LOOK, RL_GAP, RL_FROM = 7, 0.06, 30, 75, '2013-01-01'


def _supply(bv, d):
    a, b = (bv.get('lths') or {}).get(d), (bv.get('sths') or {}).get(d)
    return a + b if a and b else None


def _chain(D, P, rel, L, since, W=3, k=1.3, tol=0.02):
    pk = []
    for i, d in enumerate(D):
        if d < since or i < 30 or rel[d] <= 0: continue
        if rel[d] < k * st.median(rel[D[j]] for j in range(i - 30, i)): continue
        if rel[d] < max(rel[D[j]] for j in range(max(0, i - W), min(len(D), i + W + 1))): continue
        pk.append((i, d))
    links, step = [], 0
    for (ia, a), (ib, b) in zip(pk, pk[1:]):
        pa, pb, ra, rb = P(a), P(b), rel[a], rel[b]
        if pb > pa * (1 + tol): kind, step = 'reset', 0
        elif rb < ra * 0.9: step += 1; kind = 'div'
        elif rb > ra * 1.1: kind = 'break' if step else 'cap'; step = 0
        else: kind = 'flat'
        links.append(dict(a=a, b=b, kind=kind, step=step if kind == 'div' else 0, pa=round(pa), pb=round(pb), ua=round(L[a] / 1e6), ub=round(L[b] / 1e6),
                          ra=round(ra, 2), rb=round(rb, 2), conf=ib + W < len(D)))
    return [d for _, d in pk], links


# 2026-11-18 使用者要求（Glassnode 週報〈Capitulation Meets Support〉那張「虧損到了只有週期低點才見過的程度」）：
#   7 日平均的每日已實現虧損 ÷ 過去 365 天的已實現獲利合計（萬分之／天）。用一年的獲利當分母，不同年代可以放在同一把尺上比。
#   門檻是到當天為止的全部歷史的第 95 百分位（不偷看未來）；超過門檻、和上一次超過隔 20 天以上算新的一次。
#   Bitview 逐筆 UTXO、不是實體調整，搬家日的虧損不算；獲利是 6 個持有時間組的已實現獲利加總。只作讀值
CAP_Q, CAP_GAP, CAP_FROM = .95, 20, '2014-01-01'


def _rl_cap(bv, D, P, L, skip, ix, step=4):
    G = [bv.get('ap%d' % i) or {} for i in range(1, 7)]
    D = [d for d in D if all(d in g for g in G)]
    if len(D) < 2000: return None
    pr = [sum(g[d] for g in G) for d in D]; lo = [0 if d in skip else L[d] for d in D]; cp = [0]
    for a in pr: cp.append(cp[-1] + a)
    v = {}
    for i in range(365, len(D)):
        p365 = cp[i + 1] - cp[i - 364]
        if p365 > 0: v[D[i]] = sum(lo[i - 6:i + 1]) / 7 / p365 * 1e4
    V = [d for d in D if d in v]; hist, q = [], {}
    for d in V:
        if d >= CAP_FROM and len(hist) > 300: q[d] = hist[int(len(hist) * CAP_Q)]
        bisect.insort(hist, v[d])
    Q = [d for d in V if d in q]; d1 = Q[-1]; eps, last = [], None
    for d in Q:
        if v[d] <= q[d]: continue
        if last is None or dn(d) - dn(last) > CAP_GAP: eps.append(dict(start=d, peak=d))
        if v[d] > v[eps[-1]['peak']]: eps[-1]['peak'] = d
        eps[-1]['end'] = last = d
    for e in eps:
        e.update(peak_v=round(v[e['peak']], 1), q=round(q[e['start']], 1), price=round(P(e['start'])), r60=_fwd(D, ix, P, e['start'], 60), r180=_fwd(D, ix, P, e['start'], 180),
                 dd180=_dd(D, ix, P, e['start'], 180) if dn(d1) - dn(e['start']) >= 180 else None)
    rows = []
    for i in range(0, len(Q), step):
        m = max(Q[i:i + step], key=v.get); rows.append([dn(m), round(P(m)), round(v[m], 1), round(q[m], 1)])
    if rows[-1][0] != dn(d1): rows.append([dn(d1), round(P(d1)), round(v[d1], 1), round(q[d1], 1)])
    hi = next((d for d in reversed(Q) if d < d1 and v[d] > v[d1]), None)
    done = [e for e in eps if e['r180'] is not None]
    return dict(date=d1, v=round(v[d1], 1), q=round(q[d1], 1), above=v[d1] > q[d1], hi_since=hi, eps=eps, n=len(eps),
                back=dict(r60=_stat([e['r60'] for e in eps]), r180=_stat([e['r180'] for e in done]), dd180=_stat([e['dd180'] for e in done])), rows=rows,
                note='7 日平均的每日已實現虧損 ÷ 過去 365 天已實現獲利合計（萬分之／天）；門檻＝到當天為止的歷史第 95 百分位；Bitview，不是實體調整；只作讀值')


def rloss_viz(bv, px, last, transfers=(), days=420, show=150):
    P = _P(bv, px); L = bv.get('rloss') or {}
    D = [d for d in sorted(L) if d <= last and P(d) and _supply(bv, d)]
    if len(D) < 1500: return None
    ix = {d: i for i, d in enumerate(D)}; d1 = D[-1]; skip = {t['date'] for t in transfers or []}
    rel = {d: (0 if d in skip else L[d]) / (P(d) * _supply(bv, d)) * 1e4 for d in D}   # 萬分之（bp）
    def peak(i):
        k = max(range(max(0, i - 3), min(len(D), i + 4)), key=lambda j: rel[D[j]]); return k
    lows = []
    for i in range(RL_LOOK, len(D)):
        d = D[i]
        if d < RL_FROM: continue
        lo, hi = max(0, i - RL_W), min(len(D), i + RL_W + 1)
        conf = i + RL_W < len(D)
        if not conf and i < len(D) - 1: continue   # 未確認的只看最後一天（暫定低點）
        if P(d) != min(P(D[j]) for j in range(lo, hi)): continue
        if P(d) > (1 - RL_DD) * max(P(D[j]) for j in range(i - RL_LOOK, i)): continue
        k = peak(i); lows.append(dict(date=d, price=round(P(d)), peak_date=D[k], peak_bp=round(rel[D[k]], 2), peak_usd_m=round(L[D[k]] / 1e6), confirmed=conf))
    pairs = []
    for a, b in zip(lows, lows[1:]):
        if dn(b['date']) - dn(a['date']) > RL_GAP or b['price'] >= a['price']: continue
        kind = 'div' if b['peak_bp'] < 0.8 * a['peak_bp'] else ('cap' if b['peak_bp'] > 1.25 * a['peak_bp'] else 'flat')
        pairs.append(dict(prev=a['date'], date=b['date'], price=b['price'], prev_price=a['price'], prev_bp=a['peak_bp'], bp=b['peak_bp'], kind=kind, confirmed=b['confirmed'],
                          r30=_fwd(D, ix, P, b['date'], 30), r90=_fwd(D, ix, P, b['date'], 90)))
    back = {k: dict(r30=_stat([p['r30'] for p in pairs if p['kind'] == k]), r90=_stat([p['r90'] for p in pairs if p['kind'] == k])) for k in ('div', 'cap')}
    # 近期的認賠峰值（30 日中位數的 2 倍以上、前後 5 天最大）：圖上依序編號
    E = D[-days:]; peaks = []
    for i, d in enumerate(E):
        j = ix[d]; w = [rel[D[k]] for k in range(max(0, j - 30), j)]
        if not w or rel[d] < 2 * st.median(w): continue
        if rel[d] < max(rel[D[k]] for k in range(max(0, j - 5), min(len(D), j + 6))): continue
        peaks.append(dict(date=d, bp=round(rel[d], 2), usd_m=round(L[d] / 1e6), price=round(P(d))))
    rows = [[dn(d), round(P(d)), round(L[d] / 1e6), round(rel[d], 2), 1 if d in skip else 0] for d in E[-show:]]   # 圖只畫近 150 天（峰值看得清楚）
    cur = next((p for p in reversed(pairs) if dn(d1) - dn(p['date']) <= 30), None)
    # 認賠峰值鏈（圖上的背離輔助線）：近 show 天全部畫出；2013 年起回測「背離連到第 2 次以上」之後的漲跌、以及 30 天內被打破的比例
    _, ch = _chain(D, P, rel, L, RL_FROM)
    d2 = [c for c in ch if c['kind'] == 'div' and c['step'] >= 2]
    brk = lambda c: any(x['kind'] == 'break' and c['b'] < x['b'] and dn(x['b']) - dn(c['b']) <= 30 for x in ch)
    chain_back = dict(n=len(d2), r30=_stat([_fwd(D, ix, P, c['b'], 30) for c in d2]), r90=_stat([_fwd(D, ix, P, c['b'], 90) for c in d2]),
                      broken30=sum(brk(c) for c in d2 if dn(d1) - dn(c['b']) >= 30), done=sum(1 for c in d2 if dn(d1) - dn(c['b']) >= 30),
                      n1=sum(c['kind'] == 'div' for c in ch), nbreak=sum(c['kind'] == 'break' for c in ch))
    E2 = E[-show:]; chain = [c for c in ch if c['a'] >= E2[0]]
    # 2026-11-06 使用者：「只有短期的？沒有長期的圖？」→ 全部歷史：每日已實現虧損 ÷ 市值（萬分之，跨年份才能比），每 4 天取最大（尖峰不會被抽樣抽掉）；
    #   輔助線只畫回測用的兩種：二次以上背離、背離被打破
    H = [d for d in D if d >= RL_FROM]; hist = []
    for i in range(0, len(H), 4):
        blk = H[i:i + 4]; m = max(blk, key=rel.get); hist.append([dn(m), round(P(m)), round(rel[m], 2)])
    if hist[-1][0] != dn(d1): hist.append([dn(d1), round(P(d1)), round(rel[d1], 2)])
    hlinks = [c for c in ch if (c['kind'] == 'div' and c['step'] >= 2) or c['kind'] == 'break']
    return dict(date=d1, usd_m=round(L[d1] / 1e6), bp=round(rel[d1], 2), usd7_m=round(sum(L[D[k]] for k in range(len(D) - 7, len(D))) / 1e6),
                lows=[x for x in lows if dn(d1) - dn(x['date']) <= days], pairs=pairs[-12:], cur=cur, back=back,
                base30=_base(D, ix, P, 30, RL_FROM), base90=_base(D, ix, P, 90, RL_FROM), n_div=sum(p['kind'] == 'div' for p in pairs), n_cap=sum(p['kind'] == 'cap' for p in pairs),
                peaks=peaks[-8:], chain=chain, chain_back=chain_back, hist=hist, hlinks=hlinks, skip=sorted(skip), rows=rows, src='Bitview', cap=_rl_cap(bv, D, P, L, skip, ix),
                note='全網每日已實現虧損（Bitview，美元，逐筆 UTXO、不是實體調整）÷ 市值；擺動低點＝前後 7 天最低且比之前 30 天最高跌 ≥ 6%；搬家日不算；只作讀值')


# ---------- 長短期持有者供給比：30 日變化 ----------
# 負＝老幣被花掉、由短期持有者接手（需求在吸收供給）；正＝籌碼沉澱（也包括幣放滿 155 天自動轉成長期）。
#   各輪週期頂部前一年（主升段）與熊底後一年（過渡期）負值天數的比例。只作讀值
LC_FROM = '2015-01-01'


def lsrchg_viz(bv, px, last, bottoms=(), tops=(), step=3):
    P = _P(bv, px); ls, ss = bv.get('lths') or {}, bv.get('sths') or {}
    D = [d for d in sorted(ls) if d <= last and ss.get(d) and P(d)]
    if len(D) < 1500: return None
    r = {d: ls[d] / ss[d] for d in D}; c = {}
    for i, d in enumerate(D):
        j = next((k for k in range(i, -1, -1) if dn(D[k]) <= dn(d) - 30), None)
        if j is not None and dn(d) - dn(D[j]) <= 33: c[d] = (r[d] / r[D[j]] - 1) * 100
    C = [d for d in D if d in c and d >= LC_FROM]; d1 = C[-1]
    sign = c[d1] < 0; run_from = d1
    for d in reversed(C):
        if (c[d] < 0) != sign: break
        run_from = d
    share = lambda a, b: (lambda w: round(sum(c[d] < 0 for d in w) / len(w) * 100) if w else None)([d for d in C if a <= d <= b])
    up = [dict(top=t[0], neg=share(ds(dn(t[0]) - 365), t[0])) for t in tops if t[0] >= LC_FROM]
    tr = [dict(bottom=b[0], neg=share(b[0], ds(dn(b[0]) + 365)), open=dn(d1) - dn(b[0]) < 365) for b in bottoms if b[0] >= LC_FROM]
    rows = thin([[dn(d), round(P(d)), round(c[d], 2)] for d in C], step)
    return dict(date=d1, value=round(c[d1], 2), ratio=round(r[d1], 2), neg=sign, since=run_from, days=dn(d1) - dn(run_from) + 1,
                up=up, trans=tr, all_neg=round(sum(c[d] < 0 for d in C) / len(C) * 100), rows=rows, src='Bitview',
                note='長期持有者供給 ÷ 短期持有者供給（Bitview，155 天分界）的 30 日變化 %；只作讀值')


# ---------- 離高點的回撤（2026-11-13 使用者要求） ----------
DD_FIRST = '2011-11-18'   # 2011–13 那一輪的底部收盤（model.json 的 cycle_bottoms 從 2015 起，這一輪的起點補在這裡）


# ---------- 短期持有者成本帶的短期震盪（2026-11-15 使用者要求） ----------
# 同一個比值（價格 ÷ 短期持有者成本），改成和最近 SO_W 天比：(比值 − 平均) ÷ (SO_K × 標準差)。−1 以下是短期超賣，+1 以上是短期過熱。
#   成本帶（stage_viz.sth_bands_viz）用近 4 年，是慢的版本；這裡是快的版本，看最近跌得急不急。
# 參數：外面同類圖沒有公開參數，拿圖上九個高低點比對，約 140 天、2 個標準差最合（平均誤差 0.07）。
# 回測（2013 起，到 2026-11-14，第一次跌破 −1、相隔 30 天，共 19 次，網站統一收盤）：全部合起來 30 天後 63% 上漲、中位數 +2.4%，和任何一天（56%、+2.7%）沒有差別；
#   牛市段（週期底到頂）12 次，10 次上漲、中位數 +12.2%；熊市段 7 次，2 次上漲、中位數 −5.1%，之後 30 天內中位數再跌 15%。
#   牛熊用 model.json 的週期頂底來分，是事後才知道的。只作讀值。
SO_W, SO_K, SO_FROM = 140, 2, '2013-01-01'


def sthosc_viz(bv, px, last, bottoms=(), tops=(), step=3, keep=1100):
    P = _P(bv, px); sth = bv.get('sth') or {}; D = [d for d in sorted(sth) if d <= last and P(d) and sth[d]]
    if len(D) < 3000: return None
    N = len(D); p = [P(d) for d in D]; m = [p[i] / sth[D[i]] for i in range(N)]
    o, mu, sd = [None] * N, [None] * N, [None] * N; s1 = s2 = 0.0
    for i in range(N):
        s1 += m[i]; s2 += m[i] * m[i]
        if i >= SO_W: s1 -= m[i - SO_W]; s2 -= m[i - SO_W] ** 2
        if i >= SO_W - 1:
            mu[i] = s1 / SO_W; sd[i] = math.sqrt(max(0.0, s2 / SO_W - mu[i] * mu[i]))
            if sd[i] > 0: o[i] = (m[i] - mu[i]) / (SO_K * sd[i])
    i0 = next(i for i, d in enumerate(D) if d >= SO_FROM and o[i] is not None); e = N - 1
    if o[e] is None: return None
    B = [b[0] for b in bottoms]; T = [t[0] for t in tops]
    bull = lambda d: max([b for b in B if b <= d] or ['']) > max([t for t in T if t <= d] or [''])   # 最近一個錨點是底：牛市段
    fw = lambda i, n: (p[i + n] / p[i] - 1) * 100 if i + n < N else None
    dd = lambda i, n: (min(p[i:i + n + 1]) / p[i] - 1) * 100 if i + n < N else None
    r1 = lambda v: None if v is None else round(v, 1)
    ev, eps, lastj = [], [], -999   # ev＝第一次跌破 −1（相隔 30 天）；eps＝每一段超賣裡最深的那天（給圖上的圓圈）
    for i in range(i0, N):
        if o[i] is not None and o[i] <= -1:
            if i - lastj > 30:
                ev.append(dict(d=D[i], v=round(o[i], 2), px=round(p[i]), bull=bull(D[i]), f30=r1(fw(i, 30)), f90=r1(fw(i, 90)), dd30=r1(dd(i, 30)))); eps.append([i])
            else: eps[-1].append(i)
            lastj = i
    lows = [dict(d=D[k], v=round(o[k], 2), bull=bull(D[k])) for k in (min(c, key=lambda i: o[i]) for c in eps)]
    def summ(sel):
        f = [x['f30'] for x in ev if sel(x) and x['f30'] is not None]; g = [x['dd30'] for x in ev if sel(x) and x['dd30'] is not None]
        return dict(n=len(f), up=sum(v > 0 for v in f), med=round(st.median(f), 1), dd=round(st.median(g), 1)) if f else dict(n=0, up=0, med=None, dd=None)
    base = [fw(i, 30) for i in range(i0, N) if fw(i, 30) is not None]
    rows = [[dn(D[i]), round(o[i], 3), round(p[i], 2 if p[i] < 100 else 0)] for i in range(i0, N) if o[i] is not None]
    cut = rows[-1][0] - keep; old = [r for r in rows if r[0] < cut]
    rows = [max(old[i:i + step], key=lambda r: abs(r[1])) for i in range(0, len(old), step)] + [r for r in rows if r[0] >= cut]   # 更早的每 step 天留離零最遠的那天，尖峰不會被抽掉
    S = sth[D[e]]; below = [i for i in range(i0, N) if o[i] is not None and o[i] <= -1]
    return dict(date=D[e], close=round(p[e]), value=round(o[e], 2), prev7=round(o[e - 7], 2), window=SO_W, k=SO_K, bull=bull(D[e]),
                now=dict(sth=round(S), mid=round(S * mu[e]), lo=round(S * (mu[e] - SO_K * sd[e])), hi=round(S * (mu[e] + SO_K * sd[e]))),
                last_below=D[below[-1]] if below else None, below_pct=round(len(below) / (N - i0) * 100, 1), lows=lows, ev=ev,
                stats=dict(all=summ(lambda x: True), bull=summ(lambda x: x['bull']), bear=summ(lambda x: not x['bull']),
                           base=dict(up=round(sum(v > 0 for v in base) / len(base) * 100), med=round(st.median(base), 1))),
                rows=rows, src='Bitview',
                note='（價格 ÷ 短期持有者成本 − 近 %d 天平均）÷（%d × 標準差）；−1 以下短期超賣、+1 以上短期過熱；牛熊用事後才知道的週期頂底來分；只作讀值' % (SO_W, SO_K))


# ---------- 離成本線和均線多遠（2026-11-15 使用者要求） ----------
# 價格和九條線各比一次：log(價格 ÷ 線) 在「到當天為止的全部歷史」裡排第幾 %（不偷看未來），九個取平均。
#   慢的六條：冪律（只用當天以前的資料擬合，每 30 天重擬）、Cointime 價格、真實市場均價、實現價、365 天鏈上均價、200 週均線；
#   快的三條：短期持有者成本、90 天鏈上均價、200 日均線。鏈上均價＝這段期間全網鏈上轉帳的金額 ÷ 顆數。
# 研究（2013 起，到 2026-11-14）：和晨昏指數熱度的相關 0.89（724 週），大方向相同；差別是這裡只用價格和成本線、而且拿全部歷史排名。
#   每一輪波動都比上一輪小，所以近年的低點比較難排到最前面：前三輪熊市最低 0.0／3.4／4.1，這一輪到目前最低 11.5。
#   第一次跌到 10 以下 4 次（2014-09、2018-11、2020-03、2022-06），一年後 −41%／+81%／+931%／+15%，之後一年內最深還再跌 10%–56%：是便宜區，不是底。只作讀值。
AVG_FROM = '2013-01-01'
AVG_L = [('pl', 's'), ('ctp', 's'), ('tmm', 's'), ('rp', 's'), ('v365', 's'), ('w200', 's'), ('sth', 'f'), ('v90', 'f'), ('d200', 'f')]


def avg_viz(bv, px, last, tops=(), step=3, keep=1100):
    P = _P(bv, px); D = [d for d in sorted(bv.get('px') or {}) if d <= last and P(d)]
    if len(D) < 3000 or not all(bv.get(k) for k in ('ctp', 'tvu', 'tvb', 'sth', 'tmm', 'rp')): return None
    N = len(D); p = [P(d) for d in D]; g = lambda k: [bv[k].get(d) for d in D]
    def sma(n):
        out, s = [None] * N, 0.0
        for i in range(N):
            s += p[i]
            if i >= n: s -= p[i - n]
            if i >= n - 1: out[i] = s / n
        return out
    tu, tb = g('tvu'), g('tvb')
    def vwap(n):
        out, su, sb = [None] * N, 0.0, 0.0
        for i in range(N):
            su += tu[i] or 0; sb += tb[i] or 0
            if i >= n: su -= tu[i - n] or 0; sb -= tb[i - n] or 0
            if i >= n - 1 and sb > 0: out[i] = su / sb
        return out
    pl = [None] * N; sx = sy = sxx = sxy = 0.0; fit = None
    for i, d in enumerate(D):
        x = math.log(dn(d) - dn('2009-01-03')); y = math.log(p[i]); sx += x; sy += y; sxx += x * x; sxy += x * y; n = i + 1
        if d >= '2012-01-01' and (fit is None or i % 30 == 0):
            b = (sxy - sx * sy / n) / (sxx - sx * sx / n); fit = (sy / n - b * sx / n, b)
        if fit: pl[i] = math.exp(fit[0] + fit[1] * x)
    M = dict(pl=pl, ctp=g('ctp'), tmm=g('tmm'), rp=g('rp'), v365=vwap(365), w200=sma(1400), sth=g('sth'), v90=vwap(90), d200=sma(200))
    def rank(m):   # 每天：log(價格 ÷ 線) 在到當天為止的歷史裡的百分位 0–100（滿 365 天才開始）
        out, h = [None] * N, []
        for i in range(N):
            if not m[i] or m[i] <= 0: continue
            r = math.log(p[i] / m[i]); bisect.insort(h, r)
            if len(h) >= 365: out[i] = (bisect.bisect_left(h, r) + bisect.bisect_right(h, r)) / 2 / len(h) * 100
        return out
    Q = {k: rank(M[k]) for k, _ in AVG_L}
    def mean(keys, need):
        out = [None] * N
        for i in range(N):
            v = [Q[k][i] for k in keys if Q[k][i] is not None]
            if len(v) >= need: out[i] = sum(v) / len(v)
        return out
    SL = [k for k, q in AVG_L if q == 's']; FA = [k for k, q in AVG_L if q == 'f']
    ix, sl, fa = mean(SL + FA, 6), mean(SL, 4), mean(FA, 2)
    i0 = next(i for i, d in enumerate(D) if d >= AVG_FROM and ix[i] is not None); e = N - 1
    if ix[e] is None or sl[e] is None or fa[e] is None: return None
    f365 = lambda i: (p[i + 365] / p[i] - 1) * 100 if i + 365 < N else None
    dd365 = lambda i: (min(p[i:i + 366]) / p[i] - 1) * 100 if i + 365 < N else None
    # 每一輪熊市的最低讀值：相鄰兩個週期頂之間（最後一段到現在）
    T = [t[0] for t in tops if t[0] >= D[i0]]; lows = []
    for j, t in enumerate(T):
        a = D.index(t) if t in D else None; b = (D.index(T[j + 1]) if T[j + 1] in D else None) if j + 1 < len(T) else e
        if a is None or b is None: continue
        k = min((i for i in range(a, b + 1) if ix[i] is not None), key=lambda i: ix[i])
        lows.append(dict(d=D[k], v=round(ix[k], 1), px=round(p[k]), cur=j + 1 == len(T)))
    first = [i for i in range(i0, N) if ix[i] is not None and D[i] < (T[0] if T else D[i0])]
    if first:
        k = min(first, key=lambda i: ix[i])
        if ix[k] <= 20: lows.insert(0, dict(d=D[k], v=round(ix[k], 1), px=round(p[k]), cur=False))
    # 第一次跌到 10 以下（相隔 90 天）之後一年
    ev, lastj = [], -999
    for i in range(i0, N):
        if ix[i] is not None and ix[i] <= 10:
            if i - lastj > 90: ev.append(dict(d=D[i], v=round(ix[i], 1), px=round(p[i]), f365=None if f365(i) is None else round(f365(i), 1), dd365=None if dd365(i) is None else round(dd365(i), 1)))
            lastj = i
    def bk(lo, hi):
        v = [f365(i) for i in range(i0, N) if ix[i] is not None and lo <= ix[i] < hi and f365(i) is not None]
        return dict(n=len(v), up=round(sum(x > 0 for x in v) / len(v) * 100), med=round(st.median(v))) if v else None
    comps = [dict(key=k, grp=q, line=round(M[k][e]), pct=round(Q[k][e], 1), dist=round((p[e] / M[k][e] - 1) * 100, 1)) for k, q in AVG_L if Q[k][e] is not None and M[k][e]]
    r1 = lambda v: None if v is None else round(v, 1)
    rows = [[dn(D[i]), r1(ix[i]), round(p[i], 2 if p[i] < 100 else 0), r1(sl[i]), r1(fa[i])] for i in range(i0, N)]
    cut = rows[-1][0] - keep; old = [r for r in rows if r[0] < cut]
    rows = [min(old[i:i + step], key=lambda r: r[1]) for i in range(0, len(old), step)] + [r for r in rows if r[0] >= cut]   # 更早的每 step 天留讀值最低的那天，谷底不會被抽掉
    return dict(date=D[e], close=round(p[e]), value=r1(ix[e]), slow=r1(sl[e]), fast=r1(fa[e]), prev7=r1(ix[e - 7]), comps=comps, lows=lows, ev10=ev,
                bk=dict(lo=bk(0, 15), mid=bk(15, 20), all=bk(0, 101)), rows=rows, src='Bitview',
                note='價格和九條成本線、均線的距離，各自在到當天為止的全部歷史裡的百分位，取平均（慢六條、快三條）；不偷看未來；每輪波動變小，近年的低點較難排到最前面；只作讀值')


def dd_viz(bv, px, last, bottoms=(), tops=(), step=3, keep=1100):
    """兩種回撤，都用收盤：
    cyc＝每一輪從底部起算，收盤比「底部以來的最高收盤」低多少 %，只算底部到頂部（最後一輪到現在）；
    ath＝收盤比歷史最高收盤低多少 %。
    週期的頂、底沿用 model.json（和全站其他圖同一套）。最後一個底如果被跌破，cyc 的最後一段要重算，所以圖上寫明起點。只作讀值。"""
    P = _P(bv, px); D = [d for d in sorted(bv.get('px') or {}) if d <= last and P(d)]
    if len(D) < 1500: return None
    T = [t[0] for t in tops]; B = [DD_FIRST] + [b[0] for b in bottoms]
    segs = []   # (底, 頂或 None)
    for b in B:
        t = next((x for x in T if x > b), None)
        if b >= D[0]: segs.append((b, t))
    if not segs or segs[-1][1] is not None: return None   # 最後一個底之後已經有頂：沒有「這一輪」可畫
    cyc, past, deep = {}, [], []
    for b, t in segs:
        m = 0; w = []
        for d in D:
            if d < b or (t and d > t): continue
            m = max(m, P(d)); cyc[d] = (P(d) / m - 1) * 100; w.append(d)
        if not w: continue
        lo = min(w, key=lambda d: cyc[d])
        if t: past += [cyc[d] for d in w]; deep.append(dict(d=lo, v=round(cyc[lo], 1), bottom=b, top=t))
        else: cur = dict(bottom=b, bottom_px=round(P(b)), high=max(w, key=P), deep=dict(d=lo, v=round(cyc[lo], 1)))
    ath, m = {}, 0
    for d in D:
        m = max(m, P(d)); ath[d] = (P(d) / m - 1) * 100
    d1 = D[-1]; now = cyc[d1]; ps = sorted(past); q = lambda f: round(ps[int((len(ps) - 1) * f)], 1)
    hi = cur['high']; ah = max(D, key=P)
    rows = [[dn(d), None if d not in cyc else round(cyc[d], 2), round(P(d), 2 if P(d) < 100 else 0), round(ath[d], 2)] for d in D if d >= DD_FIRST]   # 從第一輪的底開始畫（更早的價格不到 1 美元，價格刻度會變成 $0）
    cut = rows[-1][0] - keep; old = [r for r in rows if r[0] < cut]
    def pick(g):   # 更早的每 step 天留一筆：留歷史高點回撤最深的那天，谷底不會被抽掉；這一組裡有週期內的值就帶著
        r = list(min(g, key=lambda r: r[3])); c = [x[1] for x in g if x[1] is not None]
        r[1] = min(c) if c and r[1] is not None else r[1]; return r
    rows = [pick(old[i:i + step]) for i in range(0, len(old), step)] + [r for r in rows if r[0] >= cut]
    return dict(date=d1, close=round(P(d1)),
                cyc=dict(value=round(now, 1), high=hi, high_px=round(P(hi)), days=dn(d1) - dn(hi), bottom=cur['bottom'], bottom_px=cur['bottom_px'], deep=cur['deep'],
                         past=dict(n=len(ps), cycles=len(deep), mean=round(sum(ps) / len(ps), 1), med=q(.5), p25=q(.25), deeper=round(sum(v < now for v in ps) / len(ps) * 100), deep=deep)),
                ath=dict(value=round(ath[d1], 1), high=ah, high_px=round(P(ah)), days=dn(d1) - dn(ah),
                         bottoms=[dict(d=b[0], v=round(ath[b[0]], 1)) for b in bottoms if b[0] in ath]),
                rows=rows, src='Bitview',
                note='收盤比高點低多少 %：cyc 是每一輪底部以來的最高收盤（只算底到頂），ath 是歷史最高收盤；週期頂底沿用 model.json；只作讀值')


# ---------- 背離偵測（共用） ----------
def _swings(D, P, W, hi):
    """價格擺動高（hi=True）／低點：前後 W 天的最高／最低；最後 W 天內的不確認"""
    out = []
    for i in range(W, len(D) - W):
        w = [P(D[j]) for j in range(i - W, i + W + 1)]
        if P(D[i]) == (max(w) if hi else min(w)): out.append(i)
    return out


def _divs(D, ix, P, z, W, gap, since):
    """價格新高但指標沒新高（頂背離）、價格新低但指標沒新低（底背離）；指標取擺動點前後 3 天的極值。附 30／90 天後漲跌與 60 天內最大跌幅"""
    out = []
    for hi in (True, False):
        S = [i for i in _swings(D, P, W, hi) if D[i] >= since and D[i] in z]
        for a, b in zip(S, S[1:]):
            if dn(D[b]) - dn(D[a]) > gap: continue
            pa, pb = P(D[a]), P(D[b])
            za = (max if hi else min)(z[D[k]] for k in range(a - 3, a + 4) if D[k] in z)
            zb = (max if hi else min)(z[D[k]] for k in range(b - 3, b + 4) if D[k] in z)
            if hi and pb > pa and zb < za: kind = 'top'
            elif not hi and pb < pa and zb > za: kind = 'bot'
            else: continue
            d = D[b]; out.append(dict(kind=kind, prev=D[a], date=d, price=round(pb), prev_price=round(pa), za=round(za, 2), zb=round(zb, 2), r30=_fwd(D, ix, P, d, 30), r90=_fwd(D, ix, P, d, 90), dd60=_dd(D, ix, P, d, 60)))
    return sorted(out, key=lambda x: x['date'])


def _divstat(divs):
    o = {}
    for k in ('top', 'bot'):
        L = [x for x in divs if x['kind'] == k]
        dd = [x['dd60'] for x in L if x['dd60'] is not None]
        o[k] = dict(n=len(L), r30=_stat([x['r30'] for x in L]), r90=_stat([x['r90'] for x in L]), dd60_med=round(st.median(dd), 1) if dd else None)
    return o


# ---------- 資金與價格增量梯度 ----------
# x＝價格 N 天的對數漲跌 − 已實現價格（全體平均買進成本）N 天的對數漲跌：正＝價格跑得比資金流入快（靠情緒），負＝價格跌得比資金撤出快。
#   除以 x 自己過去 4 年的標準差（無前視），N＝30 天（小級別）與 120 天（大級別）。背離：價格新低但梯度沒新低＝資金撤得比價格跌得慢。只作讀值
GR_FROM, GR_Z = '2015-01-01', 1460


def _grad(D, P, RP, N):
    x = {}
    for i in range(N, len(D)):
        d, d0 = D[i], D[i - N]
        if dn(d) - dn(d0) > N + 3: continue
        x[d] = math.log(P(d) / P(d0)) - math.log(RP[d] / RP[d0])
    K = sorted(x); z = {}; s1 = s2 = 0.0; q = []
    for d in K:   # 滾動標準差（之前 4 年，含當天）
        v = x[d]; q.append(v); s1 += v; s2 += v * v
        if len(q) > GR_Z: o = q.pop(0); s1 -= o; s2 -= o * o
        if len(q) >= 365:
            n = len(q); sd = math.sqrt(max(s2 / n - (s1 / n) ** 2, 1e-12)); z[d] = x[d] / sd
    return z


def grad_viz(bv, px, last, step=3):
    P = _P(bv, px); RP = bv.get('rp') or {}
    D = [d for d in sorted(RP) if d <= last and P(d) and RP.get(d)]
    if len(D) < 2000: return None
    ix = {d: i for i, d in enumerate(D)}; d1 = D[-1]
    z30, z120 = _grad(D, P, RP, 30), _grad(D, P, RP, 120)
    dv30, dv120 = _divs(D, ix, P, z30, 10, 150, GR_FROM), _divs(D, ix, P, z120, 20, 240, GR_FROM)
    rows = thin([[dn(d), round(P(d)), round(z30[d], 2) if d in z30 else None, round(z120[d], 2) if d in z120 else None] for d in D if d >= '2017-01-01'], step)
    return dict(date=d1, z30=round(z30[d1], 2), z120=round(z120[d1], 2), div30=dv30[-12:], div120=[x for x in dv120 if x['date'] >= '2017-01-01'], back30=_divstat(dv30), back120=_divstat(dv120),
                base30=_base(D, ix, P, 30, GR_FROM), base90=_base(D, ix, P, 90, GR_FROM), rows=rows, src='Bitview',
                note='（價格 N 天對數漲跌 − 已實現價格 N 天對數漲跌）÷ 自己過去 4 年的標準差；N＝30／120；背離＝價格擺動新高／新低而梯度沒有；只作讀值')


# ---------- 鏈上勢能 ----------
# m＝（SOPR − 1）× 每日銷毀幣天數，14 日指數平均（千）：正＝賣出的幣在獲利、而且老幣在動（獲利了結的力道），負＝認賠。
#   頂背離＝價格擺動新高但正值峰值較低（推升的獲利了結變弱）。2015 年起回測：背離之後 60 天內的最大跌幅。只作讀值
MO_FROM = '2015-01-01'


def mom_viz(bv, px, last, step=3):
    P = _P(bv, px); so, cd = bv.get('sopr') or {}, bv.get('cdd') or {}
    D = [d for d in sorted(so) if d <= last and P(d) and cd.get(d) is not None]
    if len(D) < 2000: return None
    ix = {d: i for i, d in enumerate(D)}; m = {}; e = None; a = 2 / 15
    for d in D:
        v = (so[d] - 1) * cd[d] / 1e3; e = v if e is None else e + a * (v - e); m[d] = e
    dv = [x for x in _divs(D, ix, P, m, 10, 180, MO_FROM) if x['kind'] == 'top' and x['za'] > 0]
    d1 = D[-1]; hump = None
    if m[d1] > 0:
        k = len(D) - 1
        while k > 0 and m[D[k - 1]] > 0: k -= 1
        pk = max(D[k:], key=m.get); hump = dict(start=D[k], peak=pk, peak_v=round(m[pk]))
    rows = thin([[dn(d), round(P(d)), round(m[d], 1)] for d in D if d >= '2017-01-01'], step)
    dd = [x['dd60'] for x in dv if x['dd60'] is not None]
    w2 = _w2(D, ix, P, m)
    return dict(date=d1, value=round(m[d1], 1), hump=hump, w2=w2, divs=[x for x in dv if x['date'] >= '2017-01-01'], n=len(dv), dd60_med=round(st.median(dd), 1) if dd else None,
                dd60_q=[round(sorted(dd)[len(dd) // 4], 1), round(sorted(dd)[len(dd) * 3 // 4], 1)] if len(dd) >= 4 else None,
                r30=_stat([x['r30'] for x in dv]), base_dd60=(lambda v: round(st.median(v), 1) if v else None)([x for d in D if d >= MO_FROM for x in [_dd(D, ix, P, d, 60)] if x is not None]),
                base30=_base(D, ix, P, 30, MO_FROM), rows=rows, src='Bitview',
                note='（全網 SOPR − 1）× 每日銷毀幣天數，14 日指數平均（千）；頂背離＝價格擺動新高而正值峰值較低；只作讀值')


# 2026-11-28 使用者要求（看了一則「勢能先一個深谷、再一個較淺的第二谷，就是值得注意的位置」的讀法後說「加」）：第二個低谷。
#   深谷＝勢能為負、落在自己過去一年最低 5% 以內，而且是前後 20 天最低；之後 10–75 天內出現較淺的負值低谷（前後 7 天最低），
#   兩谷之間至少回升深谷深度的 30%；第二谷之後第 7 天勢能仍高於第二谷才算成立（標在那一天）。這個定義抓得到 2026 年 2 月、6 月那兩次。
#   回測：2015 年起 15 次，90 天後較高 7 次，中位數 −8%，比任一天差；只有「極端深谷」（低於自己過去一年標準差的 −1 倍）那 8 次比較好，
#   但那種深谷多半本身就在週期底部，這一輪還沒出現。門檻是看過歷史才定的，只作讀值
W2_Q, W2_Z, W2_RISE, W2_LO, W2_HI, W2_K1, W2_K2, W2_CONF = .05, -1.0, .3, 10, 75, 20, 7, 7


def _w2(D, ix, P, m):
    import math
    v = [m[d] for d in D]; N = len(D); th, sd = [None] * N, [None] * N
    for i in range(365, N):
        w = v[i - 365:i]; th[i] = sorted(w)[int(365 * W2_Q)]; mu = sum(w) / 365; sd[i] = math.sqrt(sum((x - mu) ** 2 for x in w) / 365)
    lmin = lambda i, k: all(v[i] <= v[j] for j in range(max(0, i - k), min(N, i + k + 1)))

    def scan(deep_ok):
        ev, cur = [], None
        for a in [i for i in range(365, N) if D[i] >= MO_FROM and v[i] < 0 and deep_ok(i) and lmin(i, W2_K1)]:
            b2 = next((b for b in range(a + W2_LO, min(N, a + W2_HI)) if v[b] < 0 and v[b] > v[a] and lmin(b, W2_K2)
                       and max(v[a:b]) - v[a] >= W2_RISE * -v[a] and max(v[a:b]) > v[b]), None)
            if b2 is not None and b2 + W2_CONF < N and v[b2 + W2_CONF] > v[b2]:
                s = b2 + W2_CONF
                if not ev or ev[-1]['t2'] != D[b2]:
                    ev.append(dict(t1=D[a], v1=round(v[a], 1), t2=D[b2], v2=round(v[b2], 1), date=D[s], v=round(v[s], 1), price=round(P(D[s])),
                                   r90=_fwd(D, ix, P, D[s], 90), r180=_fwd(D, ix, P, D[s], 180), dd180=_dd(D, ix, P, D[s], 180), x=bool(sd[a] and v[a] / sd[a] <= W2_Z)))
            elif N - 1 - a < W2_HI:   # 最近的深谷，第二谷還沒成立
                cur = dict(t1=D[a], v1=round(v[a], 1), need=round(v[a] * (1 - W2_RISE), 1), hi=round(max(v[a:]), 1),
                           risen=max(v[a:]) - v[a] >= W2_RISE * -v[a], days_left=W2_HI - (N - 1 - a), x=bool(sd[a] and v[a] / sd[a] <= W2_Z))
        return ev, cur
    ev, cur = scan(lambda i: v[i] <= th[i])
    xe = [e for e in ev if e['x']]
    return dict(eps=ev, cur=cur, r90=_stat([e['r90'] for e in ev]), r180=_stat([e['r180'] for e in ev]), dd180=[e['dd180'] for e in ev if e['dd180'] is not None],
                x90=_stat([e['r90'] for e in xe]), base90=_base(D, ix, P, 90, MO_FROM))


# ---------- 回調壓力清單 ----------
# 過去熊牛過渡期回調的後段常同時出現的條件（只用本站每天有的資料，可回測的三項 + 兩項輔助）：
#   ① 價格回到短期持有者成本 3% 以內或以下 ② 獲利供給 ≤ 65% ③ 短期持有者虧損 ≥ 50% ④ 賣方衰竭低於自己的極端區（輔助）⑤ 已實現虧損峰值背離（輔助）。
#   回測只用 ①–③：2015 年起三項同時成立的日子，之後 30／90 天漲跌（和同期任一天比）。只作讀值，不是買點
def pullback_viz(bv, px, last, sec=None, rloss=None):
    P = _P(bv, px); sth, ps, sp = bv.get('sth') or {}, bv.get('psip') or {}, bv.get('sthp') or {}
    D = [d for d in sorted(ps) if d <= last and P(d) and sth.get(d) and sp.get(d) is not None]
    if len(D) < 1500: return None
    ix = {d: i for i, d in enumerate(D)}; d1 = D[-1]
    c = lambda d: (P(d) <= sth[d] * 1.03, ps[d] <= 65, 100 - sp[d] >= 50)
    hit = [d for d in D if d >= '2015-01-01' and all(c(d))]
    eps, prev = [], None
    for d in hit:   # 隔 30 天以上算新的一段
        if prev is None or dn(d) - dn(prev) > 30: eps.append(dict(start=d, end=d, days=1, price=round(P(d))))
        else: eps[-1]['end'] = d; eps[-1]['days'] += 1
        prev = d
    for e in eps: e['r30'], e['r90'] = _fwd(D, ix, P, e['start'], 30), _fwd(D, ix, P, e['start'], 90)
    a, b, cc = c(d1)
    items = [dict(id='sth', ok=a, v=round((P(d1) / sth[d1] - 1) * 100, 1), ref=round(sth[d1])), dict(id='psip', ok=b, v=round(ps[d1], 1)), dict(id='sthl', ok=cc, v=round(100 - sp[d1], 1))]
    if sec and sec.get('value') is not None and sec.get('th') is not None: items.append(dict(id='sec', ok=sec['value'] <= sec['th'], v=sec['value'], ref=sec['th'], aux=True))
    if rloss is not None: cur = rloss.get('cur'); items.append(dict(id='rloss', ok=bool(cur and cur['kind'] == 'div'), v=(cur or {}).get('kind'), aux=True))
    return dict(date=d1, items=items, n_ok=sum(1 for x in items if x['ok']), n=len(items), eps=eps[-10:], n_eps=len(eps), days=len(hit),
                r30=_stat([e['r30'] for e in eps]), r90=_stat([e['r90'] for e in eps]), base30=_base(D, ix, P, 30, '2015-01-01'), base90=_base(D, ix, P, 90, '2015-01-01'),
                src='Bitview', note='①–③ 每天可回測（2015 年起三項同時成立的日子，隔 30 天以上算新的一段）；④⑤ 只看現在；只作讀值、不是買點')


# ---------- 已實現獲利 ÷ 虧損（一年合計） ----------
# 2026-11-17 使用者要求（看了一張「已實現獲利 365 日均 ÷ 已實現虧損 365 日均」的圖）：「已實現獲利 ÷ 虧損」卡多一個一年的檢視。
#   做法是全網每天的已實現獲利、已實現虧損（Bitview，美元，不是實體調整）各自加總 365 天再相除；原本 90 天那個檢視是 CheckOnChain 的每日比值取平均，
#   平均法會被少數獲利特別大的日子拉高，這裡改用合計相除。各年齡組的已實現獲利（ap1–ap6）加起來就是全網已實現獲利，不多發請求。
#   低於 1＝一整年認賠多於獲利。過去 2012、2015、2018–19、2022–23 四段都落在週期底部區；但比值的最低點落後價格的最低點，轉紅也不等於見底。只作讀值
Y1_N, Y1_MIN = 365, 14
Y1_CONF, Y1_CONF_MAX = .10, .8   # 見底確認：比值從段內最低點回升 10%，而且那個最低點在 0.8 以下
H_N, H_LO, H_S30 = 180, .6, .3   # 2026-11-20 使用者：「能結合一年的低點和90天的低點找出尋找價格低點的規律嗎？或者再加其他時間維度」→「加到卡片上」：
#   半年合計 < 0.6 而且 30 天合計 < 0.3＝兩個窗口同時很低；2011 年起每輪只亮一段，都在週期價格低點前後。門檻是看過歷史才定的（換 0.5–0.6／0.25–0.30 結果差不多），只作讀值
Y1_NEAR = 90   # 2026-11-17 跌破 1 前後找價格最低點的範圍（天）；只算週期底（那天是前後一年最低價）


def rpl365_viz(bv, px, last, block=4, bottoms=()):
    P = _P(bv, px); L = bv.get('rloss') or {}; G = [bv.get('ap%d' % i) or {} for i in range(1, 7)]
    D = [d for d in sorted(L) if d <= last and P(d) and all(d in g for g in G)]
    if len(D) < 2000: return None
    pr = [sum(g[d] for g in G) for d in D]; lo = [L[d] for d in D]
    cp, cl = [0], [0]
    for a, b in zip(pr, lo): cp.append(cp[-1] + a); cl.append(cl[-1] + b)
    m, sp, sl = {}, {}, {}
    for i in range(Y1_N - 1, len(D)):
        a, b = cp[i + 1] - cp[i + 1 - Y1_N], cl[i + 1] - cl[i + 1 - Y1_N]
        if b > 0 and a > 0: m[D[i]], sp[D[i]], sl[D[i]] = a / b, a, b
    M = [d for d in D if d in m and d >= '2012-01-01']; d1 = M[-1]; ix = {d: i for i, d in enumerate(D)}
    reds, cur = [], None
    for d in M:
        if m[d] < 1:
            if cur is None: cur = dict(start=d, end=d, low=m[d], low_date=d)
            cur['end'] = d
            if m[d] < cur['low']: cur['low'], cur['low_date'] = m[d], d
        elif cur: reds.append(cur); cur = None
    if cur: reds.append(dict(cur, open=True))
    reds = [x for x in reds if dn(x['end']) - dn(x['start']) + 1 >= Y1_MIN]
    for x in reds:
        W = [d for d in M if x['start'] <= d <= x['end']]; pl = min(W, key=P)
        x.update(days=dn(x['end']) - dn(x['start']) + 1, low=round(x['low'], 3), low_price=round(P(x['low_date'])), start_price=round(P(x['start'])),
                 plow=pl, plow_price=round(P(pl)), dd=round((P(pl) / P(x['start']) - 1) * 100, 1), lag=round((P(x['low_date']) / P(pl) - 1) * 100, 1),
                 r365=None if x.get('open') else _fwd(D, ix, P, x['low_date'], 365))
    for x in reds:   # 2026-11-17 見底確認：段內比值第一次從當時的最低點回升 10%（最低點在 0.8 以下）那天；之後價格有沒有再跌破那天以前的最低價
        W = [d for d in M if x['start'] <= d <= x['end']]; run = 9; c = None
        for d in W:
            run = min(run, m[d])
            if run < Y1_CONF_MAX and m[d] >= run * (1 + Y1_CONF): c = d; break
        if not c: continue
        lo_ = min(P(d) for d in M if x['start'] <= d <= c); fut = [P(d) for d in D if d > c]
        x.update(conf=c, conf_px=round(P(c)), conf_gain=round((P(c) / lo_ - 1) * 100, 1), conf_broken=bool(fut) and min(fut) < lo_)
    for x in reds:   # 2026-11-17 使用者問「低於 1 的點、回升點和價格底部有什麼規律」：跌破 1 前後 Y1_NEAR 天內（到期間結束）價格最低的那天
        W = [d for d in D if dn(x['start']) - Y1_NEAR <= dn(d) and d <= x['end']]; nl = min(W, key=P)
        x.update(near=nl, near_price=round(P(nl)), near_gap=dn(nl) - dn(x['start']), near_rgap=dn(x['low_date']) - dn(nl),
                 cyc=P(nl) <= min(P(d) for d in D if abs(dn(d) - dn(nl)) <= 365))   # 2012 那段不是週期底（2011/11 更低），不算
    below = m[d1] < 1; k = len(M) - 1
    while k > 0 and (m[M[k - 1]] < 1) == below: k -= 1
    d30 = M[max(0, len(M) - 1 - 30)]
    rows = []
    for i in range(len(M) - 1, -1, -block):   # 每 block 天取一點；段內有低於 1 的日子取最低那天（同 stage_viz.rpl_viz）
        seg = M[max(0, i - block + 1): i + 1]; lo_ = min(seg, key=m.get); d_ = lo_ if m[lo_] < 1 else seg[-1]
        if i == len(M) - 1 and d_ != seg[-1]: rows.append([dn(seg[-1]), round(m[seg[-1]], 3), round(P(seg[-1]))])
        rows.append([dn(d_), round(m[d_], 3), round(P(d_))])
    rows.reverse()
    done = [x for x in reds if not x.get('open')]
    # 2026-11-20 使用者（運營轉來）：「90 天」原本是 CheckOnChain 每日比值取平均，單日極端值（90 天裡最大一天 20 倍）把它拉到 2.28，
    #   合計相除只有 1.32，和卡片上「最近 7 天 0.17」的判讀打架。90 天和 7、30 天都改成同一份 Bitview 資料的合計相除
    sr = lambda n, i: (lambda a, b: round(a / b, 3) if a > 0 and b > 0 else None)(cp[i + 1] - cp[i + 1 - n], cl[i + 1] - cl[i + 1 - n])
    iz = len(D) - 1; s7, s30 = sr(7, iz), sr(30, iz)
    m9 = {D[i]: v for i in range(89, len(D)) for v in [sr(90, i)] if v}
    M9 = [d for d in D if d in m9 and d >= '2012-01-01']; r9, cur = [], None
    for d in M9:
        if m9[d] < 1:
            if cur is None: cur = dict(start=d, end=d)
            cur['end'] = d
        elif cur: r9.append(cur); cur = None
    if cur: r9.append(dict(cur, open=True))
    r9 = [x for x in r9 if dn(x['end']) - dn(x['start']) + 1 >= 5]
    ab9 = m9[M9[-1]] >= 1; k9 = len(M9) - 1
    while k9 > 0 and (m9[M9[k9 - 1]] >= 1) == ab9: k9 -= 1
    rw9 = []
    for i in range(len(M9) - 1, -1, -block):
        seg = M9[max(0, i - block + 1): i + 1]; lo_ = min(seg, key=m9.get); d_ = lo_ if m9[lo_] < 1 else seg[-1]
        if i == len(M9) - 1 and d_ != seg[-1]: rw9.append([dn(seg[-1]), m9[seg[-1]], round(P(seg[-1]))])
        rw9.append([dn(d_), m9[d_], round(P(d_))])
    rw9.reverse()
    # 半年＋30 天：每天的兩個比值、同時很低的期間（第一次亮起、之後 180 天內的最低價、再跌多少、一年後）
    hz_ = {D[i]: (sr(H_N, i), sr(30, i)) for i in range(H_N - 1, len(D))}; MH = [d for d in D if d in hz_ and hz_[d][0] and hz_[d][1]]
    onz = lambda d: hz_[d][0] < H_LO and hz_[d][1] < H_S30
    zs, last_ = [], None
    for d in MH:
        if onz(d):
            if last_ is None or dn(d) - dn(last_) > 90: zs.append(dict(start=d, end=d, days=0))
            zs[-1]['end'] = d; zs[-1]['days'] += 1; last_ = d
    for z in zs:
        W_ = [d for d in D if z['start'] <= d and dn(d) <= dn(z['end']) + 180]; lo_ = min(W_, key=P)
        z.update(px=round(P(z['start'])), low=lo_, low_px=round(P(lo_)), lead=dn(lo_) - dn(z['start']), dd=round((P(lo_) / P(z['start']) - 1) * 100, 1),
                 r365=_fwd(D, ix, P, z['start'], 365), open=dn(D[-1]) - dn(z['end']) < 180)
    rwh = []
    for i in range(len(MH) - 1, -1, -block):
        seg = MH[max(0, i - block + 1): i + 1]; lo_ = min(seg, key=lambda d: hz_[d][0]); d_ = lo_ if hz_[lo_][0] < 1 else seg[-1]
        if i == len(MH) - 1 and d_ != seg[-1]: rwh.append([dn(seg[-1]), hz_[seg[-1]][0], round(P(seg[-1])), hz_[seg[-1]][1]])
        rwh.append([dn(d_), hz_[d_][0], round(P(d_)), hz_[d_][1]])
    rwh.reverse()
    w180 = dict(value=hz_[MH[-1]][0], s30=hz_[MH[-1]][1], on=onz(MH[-1]), lo=H_LO, s30_lo=H_S30, zones=zs, rows=rwh)
    w90 = dict(value=m9[M9[-1]], above=ab9, since=M9[k9], since_days=dn(M9[-1]) - dn(M9[k9]), v10=m9[M9[max(0, len(M9) - 11)]], reds=r9, rows=rw9)
    # 2026-11-20 使用者（運營轉來）：圖上畫歷次週期的價格低點（data/model.json 的 cycle_bottoms，和網站其他地方同一套），讓人看到價格見底那天比值還沒到最低
    lows = [dict(d=b[0], px=round(P(b[0])), y1=round(m[b[0]], 3) if b[0] in m else None, r90=m9.get(b[0]), r180=(hz_.get(b[0]) or (None,))[0]) for b in bottoms if b[0] in ix and P(b[0])]
    return dict(date=d1, value=round(m[d1], 3), price=round(P(d1)), below=below, s7=s7, s30=s30, w90=w90, w180=w180, lows=lows, since=M[k], since_days=dn(d1) - dn(M[k]), since_price=round(P(M[k])),
                chg=round((P(d1) / P(M[k]) - 1) * 100, 1), v30=round(m[d30], 3), profit_b=round(sp[d1] / 1e9, 1), loss_b=round(sl[d1] / 1e9, 1),
                cur_low=round(reds[-1]['low'], 3) if reds and reds[-1].get('open') else None, conf_at=round(reds[-1]['low'] * (1 + Y1_CONF), 3) if reds and reds[-1].get('open') and reds[-1]['low'] < Y1_CONF_MAX else None,
                confirmed=bool(reds and reds[-1].get('open') and reds[-1].get('conf')), conf_n=sum(1 for x in done if x.get('conf')), conf_ok=sum(1 for x in done if x.get('conf') and not x['conf_broken']),
                conf_gain=[min(x['conf_gain'] for x in done if x.get('conf')), max(x['conf_gain'] for x in done if x.get('conf'))] if any(x.get('conf') for x in done) else None,
                near=(lambda B: dict(n=len(B), gap=[min(x['near_gap'] for x in B), max(x['near_gap'] for x in B)], dd=min(x['dd'] for x in B),
                                     rgap=[min(x['near_rgap'] for x in B), max(x['near_rgap'] for x in B)]) if B else None)([x for x in done if x['cyc']]),
                reds=reds, past_low=[min(x['low'] for x in done), max(x['low'] for x in done)] if done else None,
                r365=_stat([x['r365'] for x in done]), base365=_base(D, ix, P, 365, '2012-01-01'), rows=rows, src='Bitview',
                note='全網每天的已實現獲利、已實現虧損（美元）各加總 365 天再相除；低於 1＝一整年認賠多於獲利；reds＝14 天以上低於 1 的期間（dd＝期間內最大跌幅、lag＝比值最低那天的價格比期間最低價高多少、r365＝比值最低那天之後一年）；只作讀值')
