"""2026-11-06 使用者要求：一批鏈上指標與讀法（指標擴充），用本站自己的資料（Bitview，免費、不佔 bitcoin-data 額度）重做。
產品內不寫個人名字。每一項都照實寫回測（樣本數、勝率、和同期任一天比），只作讀值，不是買賣訊號。

第一批：供給分位成本線（quant_viz）、短期持有者虧損比例的歷次（sthl_viz）、相對未實現獲利的地板（rup_viz）、
       全網實現虧損峰值背離（rloss_viz）、長短期持有者供給比的 30 日變化（lsrchg_viz）。
第二批：資金與價格增量梯度（grad_viz）、鏈上勢能（mom_viz）、回調壓力清單（pullback_viz）。
bv＝bitview.cols(rows)：{欄位: {日期: 值}}；px＝統一收盤（PXC），缺日用 Bitview 自己的收盤。x 一律為 1970-01-01 起的天數。"""
import math, statistics as st
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
    return dict(date=d1, value=round(r[d1], 1), d30=round(r[d30], 1) if d30 else None, floor=RUP_FLOOR, gap=round(r[d1] - RUP_FLOOR, 1),
                med=round(st.median(r[d] for d in D), 1), share_below=round(sum(r[d] <= RUP_FLOOR for d in D) / len(D) * 100, 1), tops=tv,
                yr_lo=yr_lo, other_lo=min((y for y in yr_lo if y['value'] > RUP_FLOOR), key=lambda y: y['value'], default=None),
                lo1y=dict(date=lo, value=round(r[lo], 1)), eps=eps, rows=rows, since=RUP_FROM, src='Bitview',
                note='相對未實現獲利＝全體未實現獲利 ÷ 市值（Bitview，逐筆 UTXO）；地板 35% 是本站依 2012 年起的歷史設定；只作讀值')


# ---------- 全網實現虧損：峰值背離 ----------
# 每日實現虧損（Bitview realized_loss_sum_24h，美元，不是實體調整）÷ 市值。價格擺動低點（前後 7 天最低、比之前 30 天最高跌 ≥ 6%）
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
    return dict(date=d1, usd_m=round(L[d1] / 1e6), bp=round(rel[d1], 2), usd7_m=round(sum(L[D[k]] for k in range(len(D) - 7, len(D))) / 1e6),
                lows=[x for x in lows if dn(d1) - dn(x['date']) <= days], pairs=pairs[-12:], cur=cur, back=back,
                base30=_base(D, ix, P, 30, RL_FROM), base90=_base(D, ix, P, 90, RL_FROM), n_div=sum(p['kind'] == 'div' for p in pairs), n_cap=sum(p['kind'] == 'cap' for p in pairs),
                peaks=peaks[-8:], chain=chain, chain_back=chain_back, skip=sorted(skip), rows=rows, src='Bitview',
                note='全網每日實現虧損（Bitview，美元，逐筆 UTXO、不是實體調整）÷ 市值；擺動低點＝前後 7 天最低且比之前 30 天最高跌 ≥ 6%；搬家日不算；只作讀值')


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
# x＝價格 N 天的對數漲跌 − 實現價格（全體平均買進成本）N 天的對數漲跌：正＝價格跑得比資金流入快（靠情緒），負＝價格跌得比資金撤出快。
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
                note='（價格 N 天對數漲跌 − 實現價格 N 天對數漲跌）÷ 自己過去 4 年的標準差；N＝30／120；背離＝價格擺動新高／新低而梯度沒有；只作讀值')


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
    return dict(date=d1, value=round(m[d1], 1), hump=hump, divs=[x for x in dv if x['date'] >= '2017-01-01'], n=len(dv), dd60_med=round(st.median(dd), 1) if dd else None,
                dd60_q=[round(sorted(dd)[len(dd) // 4], 1), round(sorted(dd)[len(dd) * 3 // 4], 1)] if len(dd) >= 4 else None,
                r30=_stat([x['r30'] for x in dv]), base_dd60=(lambda v: round(st.median(v), 1) if v else None)([x for d in D if d >= MO_FROM for x in [_dd(D, ix, P, d, 60)] if x is not None]),
                base30=_base(D, ix, P, 30, MO_FROM), rows=rows, src='Bitview',
                note='（全網 SOPR − 1）× 每日銷毀幣天數，14 日指數平均（千）；頂背離＝價格擺動新高而正值峰值較低；只作讀值')


# ---------- 回調壓力清單 ----------
# 過去熊牛過渡期回調的後段常同時出現的條件（只用本站每天有的資料，可回測的三項 + 兩項輔助）：
#   ① 價格回到短期持有者成本 3% 以內或以下 ② 獲利供給 ≤ 65% ③ 短期持有者虧損 ≥ 50% ④ 賣方衰竭低於自己的極端區（輔助）⑤ 實現虧損峰值背離（輔助）。
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
