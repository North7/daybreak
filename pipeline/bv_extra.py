"""2026-11-06 使用者要求（「Bitview 還有什麼圖表可以搬過來的」→「推薦的都做」）：用 Bitview（免費、不佔 bitcoin-data 額度）再做六項。
賣方風險比（ssr_viz）、長短期持有者 NUPL（nupl_viz）、儲備風險（rr_viz）、AVIV（aviv_viz）、依持有時間的實現獲利／虧損（age_viz）、
Dormancy 與 Liveliness（dorm_viz）。每項都附歷次頂部／底部的讀值與回測，只作讀值、不是買賣訊號。
bv＝bitview.cols(rows)；px＝統一收盤（PXC），缺日用 Bitview 自己的收盤。x 一律為 1970-01-01 起的天數。"""
import statistics as st
from stage_viz import dn, ds, thin
from oc_extra import _P, _fwd, _base, _stat

FROM = '2012-01-01'


def _near(s, D, d, w, f):
    xs = [s[x] for x in D if abs(dn(x) - dn(d)) <= w]
    return f(xs) if xs else None


def _cyc(s, D, tops, bottoms, dg=4):
    """各輪週期頂部前後 30 天的最高值、底部前後 30 天的最低值"""
    tp = [dict(date=t[0], value=round(_near(s, D, t[0], 30, max), dg)) for t in tops if t[0] >= D[0] and _near(s, D, t[0], 30, max) is not None]
    bt = [dict(date=b[0], value=round(_near(s, D, b[0], 30, min), dg)) for b in bottoms if b[0] >= D[0] and _near(s, D, b[0], 30, min) is not None]
    return tp, bt


def _pct(s, D, v):
    H = [s[d] for d in D]
    return round(sum(x < v for x in H) / len(H) * 100, 1)


def _zone_eps(s, D, ix, P, cond, gap=30):
    """條件成立的段落（隔 gap 天以上算新的一段），附進入時的價格、90／365 天後漲跌"""
    eps = []
    for d in D:
        if not cond(s[d]): continue
        if eps and dn(d) - dn(eps[-1]['end']) <= gap: eps[-1]['end'] = d; eps[-1]['days'] += 1
        else: eps.append(dict(start=d, end=d, days=1))
    for e in eps:
        e['price'] = round(P(e['start'])); e['r90'] = _fwd(D, ix, P, e['start'], 90); e['r365'] = _fwd(D, ix, P, e['start'], 365)
    return eps


ROLL = 1460   # 近 4 年


def _roll(s, D, q=None):
    """近 4 年滾動百分位（每天和自己之前 4 年比，含當天、沒有前視）；q 給定時改回傳近 4 年的第 q 百分位數值（門檻線）"""
    import bisect
    out, win = {}, []
    for j, d in enumerate(D):
        bisect.insort(win, s[d])
        if j >= ROLL: win.pop(bisect.bisect_left(win, s[D[j - ROLL]]))
        if j < 365: continue
        out[d] = win[min(len(win) - 1, int(len(win) * q))] if q is not None else round(bisect.bisect_left(win, s[d]) / len(win) * 100, 1)
    return out


def _prep(bv, px, last, keys):
    P = _P(bv, px); S = [bv.get(k) or {} for k in keys]
    D = [d for d in sorted(S[0]) if FROM <= d <= last and P(d) and all(d in s for s in S)]
    return P, S, D, {d: i for i, d in enumerate(D)}


# ---------- 賣方風險比 ----------
# 賣方風險比＝7 天實現的獲利＋虧損 ÷ 實現市值（Bitview，全網／短期持有者／長期持有者）：賣出的人一共「兌現」了多少帳面損益。
#   很低＝賣出的人很少、而且賣價接近成本，市場在找新的平衡（常在盤整末端、底部區）；很高＝大量獲利了結或認賠（頂部、恐慌）。
#   低檔區＝2012 年起全網值最低的 10%（寫死、不回頭調）。頂部的高點一輪比一輪低（2013 0.70、2017 0.23、2021 0.14），只比相對位置
def ssr_viz(bv, px, last, tops=(), bottoms=(), step=4):
    P, (a, s_, l_), D, ix = _prep(bv, px, last, ['ssr', 'ssr_s', 'ssr_l'])
    if len(D) < 1500: return None
    H = sorted(a[d] for d in D); lo, hi = H[int(len(H) * 0.10)], H[int(len(H) * 0.90)]
    p4, l4, h4 = _roll(a, D), _roll(a, D, 0.10), _roll(a, D, 0.90)
    R4 = [d for d in D if d in p4]; rx = {d: i for i, d in enumerate(R4)}
    d1 = D[-1]; eps = _zone_eps(p4, R4, rx, P, lambda v: v <= 10)
    run = 0
    for d in reversed(R4):
        if p4[d] <= 10: run += 1
        else: break
    tp, bt = _cyc(a, D, tops, bottoms)
    rows = thin([[dn(d), round(P(d)), a[d], s_[d], l_[d], l4.get(d), h4.get(d)] for d in D], step)
    if rows[-1][0] != dn(d1): rows.append([dn(d1), round(P(d1)), a[d1], s_[d1], l_[d1], l4.get(d1), h4.get(d1)])
    back = lambda n: max((d for d in D if dn(d) <= dn(d1) - n), default=None); d30 = back(30)
    return dict(date=d1, all=a[d1], sth=s_[d1], lth=l_[d1], all30=a[d30] if d30 else None, pct=_pct(a, D, a[d1]), pct_s=_pct(s_, D, s_[d1]), pct_l=_pct(l_, D, l_[d1]),
                pct4=p4.get(d1), lo4=l4.get(d1), n_recent=sum(1 for e in eps if e['start'] >= '2022-01-01'), lo=round(lo, 6), hi=round(hi, 6), run=run, eps=eps[-10:], n_eps=len(eps), r90=_stat([e['r90'] for e in eps]), r365=_stat([e['r365'] for e in eps]),
                base90=_base(D, ix, P, 90, FROM), base365=_base(D, ix, P, 365, FROM), tops=tp, bottoms=bt, rows=rows, src='Bitview',
                note='7 天實現獲利＋虧損 ÷ 實現市值（Bitview，逐筆 UTXO）；低檔區＝全網近 4 年滾動百分位 ≤ 10（頂部一輪比一輪低）；只作讀值')


# ---------- 長短期持有者 NUPL ----------
# NUPL＝（帳面獲利 − 帳面虧損）÷ 市值，分長期持有者（不動 ≥150 天）與短期持有者。長期持有者的五個階段（常見的分法）：
#   < 0 投降、0–0.25 希望／恐懼、0.25–0.5 樂觀／焦慮、0.5–0.75 信念／否認、≥ 0.75 狂熱／貪婪。短期持有者以 0 為界：新進場的人整體賺或賠
LN_STAGE = [(0, 'cap'), (0.25, 'hope'), (0.5, 'opt'), (0.75, 'belief'), (9, 'euph')]


def _stage(v):
    return next(k for t, k in LN_STAGE if v < t)


def nupl_viz(bv, px, last, tops=(), bottoms=(), step=4):
    P, (l_, s_), D, ix = _prep(bv, px, last, ['lnupl', 'snupl'])
    if len(D) < 1500: return None
    d1 = D[-1]; tp, bt = _cyc(l_, D, tops, bottoms, 3); stp, sbt = _cyc(s_, D, tops, bottoms, 3)
    since = d1   # 長期持有者目前這個階段從哪天開始
    for d in reversed(D):
        if _stage(l_[d]) != _stage(l_[d1]): break
        since = d
    cross = None   # 短期持有者 NUPL 最近一次穿越 0
    for i in range(len(D) - 1, 0, -1):
        if (s_[D[i]] >= 0) != (s_[D[i - 1]] >= 0): cross = dict(date=D[i], up=s_[D[i]] >= 0); break
    # 短期持有者 NUPL 由負轉正（隔 60 天以上算新的一次）之後的漲跌
    ups, prev = [], None
    for i in range(1, len(D)):
        d = D[i]
        if s_[d] >= 0 > s_[D[i - 1]] and (prev is None or dn(d) - dn(prev) > 60):
            ups.append(dict(date=d, price=round(P(d)), r30=_fwd(D, ix, P, d, 30), r90=_fwd(D, ix, P, d, 90))); prev = d
    back = lambda n: max((d for d in D if dn(d) <= dn(d1) - n), default=None); d30 = back(30)
    rows = thin([[dn(d), round(P(d)), l_[d], s_[d]] for d in D], step)
    if rows[-1][0] != dn(d1): rows.append([dn(d1), round(P(d1)), l_[d1], s_[d1]])
    return dict(date=d1, lth=l_[d1], sth=s_[d1], lth30=l_[d30] if d30 else None, sth30=s_[d30] if d30 else None, stage=_stage(l_[d1]), since=since,
                tops=tp, bottoms=bt, sth_tops=stp, sth_bottoms=sbt, cross=cross, ups=ups[-8:], n_ups=len(ups), r30=_stat([u['r30'] for u in ups]), r90=_stat([u['r90'] for u in ups]),
                base30=_base(D, ix, P, 30, FROM), base90=_base(D, ix, P, 90, FROM), rows=rows, src='Bitview',
                note='（帳面獲利 − 帳面虧損）÷ 市值，分長期持有者（不動 ≥150 天）與短期持有者（Bitview）；只作讀值')


# ---------- 儲備風險 ----------
# 儲備風險＝價格 ÷ 長期持有者的「信心」（他們沒賣、放著不動所累積的機會成本）。低＝價格相對長期持有者的信心便宜，過去都在熊市底部附近；高＝頂部區。
#   低檔區＝2012 年起最低 10%、高檔區＝最高 10%（寫死）
def rr_viz(bv, px, last, tops=(), bottoms=(), step=4):
    P, (r,), D, ix = _prep(bv, px, last, ['rr'])
    if len(D) < 1500: return None
    H = sorted(r[d] for d in D); lo, hi = H[int(len(H) * 0.10)], H[int(len(H) * 0.90)]
    p4, l4, h4 = _roll(r, D), _roll(r, D, 0.10), _roll(r, D, 0.90)
    R4 = [d for d in D if d in p4]; rx = {d: i for i, d in enumerate(R4)}
    d1 = D[-1]; eps = _zone_eps(p4, R4, rx, P, lambda v: v <= 10)
    run = 0
    for d in reversed(R4):
        if p4[d] <= 10: run += 1
        else: break
    tp, bt = _cyc(r, D, tops, bottoms, 5)
    bp4 = [dict(date=b['date'], pct4=p4.get(min(R4, key=lambda d: abs(dn(d) - dn(b['date']))))) for b in bt]   # 各輪底部在當時近 4 年的百分位
    tp, bt = _cyc(r, D, tops, bottoms, 5)
    rows = thin([[dn(d), round(P(d)), r[d], l4.get(d), h4.get(d)] for d in D], step)
    if rows[-1][0] != dn(d1): rows.append([dn(d1), round(P(d1)), r[d1], l4.get(d1), h4.get(d1)])
    return dict(date=d1, value=r[d1], pct=_pct(r, D, r[d1]), pct4=p4.get(d1), lo=lo, hi=hi, lo4=l4.get(d1), bp4=bp4, run=run, eps=eps[-10:], n_eps=len(eps),
                n_recent=sum(1 for e in eps if e['start'] >= '2022-01-01'), r365=_stat([e['r365'] for e in eps]), r90=_stat([e['r90'] for e in eps]),
                base365=_base(D, ix, P, 365, FROM), base90=_base(D, ix, P, 90, FROM), tops=tp, bottoms=bt, rows=rows, src='Bitview',
                note='價格 ÷ 長期持有者的信心（Bitview reserve_risk）；低檔區＝近 4 年滾動百分位 ≤ 10（頂部一輪比一輪低，全部歷史的百分位會偏向近年）；只作讀值')


# ---------- AVIV ----------
# AVIV＝價格 ÷ 真實市場均價（活躍投資人的平均成本，Cointime）：大於 1＝活躍投資人整體獲利。頂部讀數一輪比一輪低、底部一輪比一輪高
def aviv_viz(bv, px, last, tops=(), bottoms=(), step=4):
    P, (v,), D, ix = _prep(bv, px, last, ['aviv'])
    if len(D) < 1500: return None
    d1 = D[-1]; tp, bt = _cyc(v, D, tops, bottoms, 3)
    below = _zone_eps(v, D, ix, P, lambda x: x < 1, gap=20)
    run = 0
    for d in reversed(D):
        if (v[d] < 1) == (v[d1] < 1): run += 1
        else: break
    rows = thin([[dn(d), round(P(d)), v[d]] for d in D], step)
    if rows[-1][0] != dn(d1): rows.append([dn(d1), round(P(d1)), v[d1]])
    tmm = (bv.get('tmm') or {}).get(d1)
    return dict(date=d1, value=v[d1], pct=_pct(v, D, v[d1]), pct4=_roll(v, D).get(d1), run=run, below=v[d1] < 1, tmm=tmm, eps=[e for e in below if e['days'] >= 10][-10:],
                r365=_stat([e['r365'] for e in below if e['days'] >= 10]), base365=_base(D, ix, P, 365, FROM), tops=tp, bottoms=bt, rows=rows, src='Bitview',
                note='價格 ÷ 真實市場均價（Bitview aviv，Cointime）；低於 1＝活躍投資人整體虧損；只作讀值')


# ---------- 依持有時間的實現獲利／虧損 ----------
# 每天賣出的幣依「持有多久」分 6 組，各組實現的獲利與虧損（美元，Bitview 逐筆 UTXO）；看 30 天合計各組佔多少，回答「是老幣在賣還是短線在賣」
AGE_LAB = ['lt1m', 'm1_6', 'm6_12', 'y1_2', 'y2_5', 'y5p']


def age_viz(bv, px, last, days=1095, step=2):
    P = _P(bv, px); PP = [bv.get(f'ap{i}') or {} for i in range(1, 7)]; LL = [bv.get(f'al{i}') or {} for i in range(1, 7)]
    D = [d for d in sorted(PP[0]) if d <= last and P(d) and all(d in s for s in PP + LL)]
    if len(D) < 400: return None
    def s30(S, j): return [sum(S[g][D[k]] or 0 for k in range(max(0, j - 29), j + 1)) for g in range(6)]
    out = []
    for j in range(len(D) - days, len(D)):
        if j < 30: continue
        p, l = s30(PP, j), s30(LL, j); tp, tl = sum(p) or 1, sum(l) or 1
        out.append([dn(D[j]), round(P(D[j])), [round(x / tp * 100, 1) for x in p], [round(x / tl * 100, 1) for x in l], round(tp / 1e6), round(tl / 1e6)])
    d1 = D[-1]; z = out[-1]; z30 = next((r for r in reversed(out) if r[0] <= dn(d1) - 30), None)
    rows = thin(out, step)
    if rows[-1][0] != z[0]: rows.append(z)
    lth = lambda sh: round(sum(sh[2:]), 1)   # 6 個月以上（約等於長期持有者）
    return dict(date=d1, groups=AGE_LAB, prof=z[2], loss=z[3], prof_m=z[4], loss_m=z[5], prof30=z30[2] if z30 else None, loss30=z30[3] if z30 else None,
                lth_prof=lth(z[2]), lth_loss=lth(z[3]), lth_prof30=lth(z30[2]) if z30 else None, rows=rows, src='Bitview',
                note='30 天合計：各持有時間組實現的獲利、虧損各佔多少（Bitview，逐筆 UTXO、不是實體調整）；只作讀值')


# ---------- Dormancy 與 Liveliness ----------
# Dormancy（7 日）＝賣出的幣平均放了幾天：數字高＝老幣在動（長期持有者在賣或搬幣）。Liveliness＝全部持有時間裡已經「花掉」的比例：
#   上升＝老幣在動、長期持有者在花費；下降＝大家在囤。Liveliness 長期往上漂（越來越多幣在某個時間點動過），所以看 90 天變化
def dorm_viz(bv, px, last, tops=(), bottoms=(), step=4):
    P, (dm, lv), D, ix = _prep(bv, px, last, ['dorm', 'live'])
    if len(D) < 1500: return None
    d1 = D[-1]; tp, bt = _cyc(dm, D, tops, bottoms, 1)
    back = lambda n: max((d for d in D if dn(d) <= dn(d1) - n), default=None); d30, d90 = back(30), back(90)
    a30 = {}
    for j, d in enumerate(D):
        w = D[max(0, j - 29):j + 1]; a30[d] = sum(dm[x] for x in w) / len(w)
    lv90 = round((lv[d1] - lv[d90]) * 1000, 2) if d90 else None   # 千分點
    up_from = d1   # Liveliness 90 天變化連續同號從哪天開始（日線連續，用位置回推 90 天）
    for j in range(len(D) - 1, 89, -1):
        if lv90 is None or ((lv[D[j]] - lv[D[j - 90]]) > 0) != (lv90 > 0): break
        up_from = D[j]
    rows = thin([[dn(d), round(P(d)), round(dm[d], 1), round(a30[d], 1), lv[d]] for d in D], step)
    if rows[-1][0] != dn(d1): rows.append([dn(d1), round(P(d1)), round(dm[d1], 1), round(a30[d1], 1), lv[d1]])
    return dict(date=d1, dorm=round(dm[d1], 1), dorm30=round(a30[d1], 1), dorm_pct=_pct(dm, D, dm[d1]), a30_pct=_pct(a30, D, a30[d1]), a30_pct4=_roll(a30, D).get(d1), live=lv[d1], live90=lv90,
                live_since=up_from, live_pct=_pct(lv, D, lv[d1]), tops=tp, bottoms=bt, rows=rows, src='Bitview',
                note='Dormancy＝7 天內賣出的幣平均放了幾天；Liveliness＝全部持有時間裡已花掉的比例（Bitview，Cointime）；只作讀值')
