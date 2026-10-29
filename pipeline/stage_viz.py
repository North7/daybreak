"""市場階段佐證燈號的走勢圖資料與第 6 盞燈（2026-10-14 使用者要求）。
只作讀值、不參與 P23 判定；collect.py 在 G4c 呼叫，不另打 API（沿用 CoinMetrics 與 bitcoin-data 已抓的序列）。
x 一律為 1970-01-01 起的天數（頁面 JS 轉回日期）；序列每 STEP 天取一點，最後一點一定保留。"""
import bisect, datetime as dt, math

EP = dt.date(1970, 1, 1)
YEARS, STEP, AHEAD, PROJ_MAX = 3, 3, 120, 365
dn = lambda s: (dt.date.fromisoformat(s) - EP).days
ds = lambda n: (EP + dt.timedelta(days=n)).isoformat()


def thin(rows, step=STEP):
    return rows[::-1][::step][::-1]


def _at_or_before(dates, t):   # 以日期回推（資料缺日時不以列位置代替）；沒有回傳 None
    b = bisect.bisect_right(dates, t) - 1
    return b if b >= 0 else None


def tmm_light(sth, tmm):
    """第 6 盞：短期持有者成本 vs 真實市場均價（兩條都是 bitcoin-data，同一家同日比較，不跨資料商相減）。"""
    cd = sorted(set(sth) & set(tmm))
    if len(cd) < 31: return None
    d = cd[-1]; s0, t0 = sth[d], tmm[d]
    return dict(id='tmm', label='短期持有者成本 vs 真實市場均價', ok=s0 > t0, value=round((s0 / t0 - 1) * 100, 2), unit='%',
                cond='短期持有者成本高於真實市場均價（bitcoin-data，晚約 7 天）', date=d, est=_cross(sth, tmm, cd))


def _cross(sth, tmm, cd):
    """以近 30 日的速度線性外推兩條線何時交叉。只是讀值：前提是速度不變，價格跌破短期持有者成本時成本線就不再上升。"""
    d = cd[-1]; j = _at_or_before(cd, (dt.date.fromisoformat(d) - dt.timedelta(days=30)).isoformat())
    if j is None: return None
    n = (dt.date.fromisoformat(d) - dt.date.fromisoformat(cd[j])).days or 1
    a, b = (sth[d] - sth[cd[j]]) / n, (tmm[d] - tmm[cd[j]]) / n   # 每天變化（美元）
    gap = tmm[d] - sth[d]
    out = dict(sth_per_day=round(a, 1), tmm_per_day=round(b, 1), basis_days=n, direction='up' if gap > 0 else 'down')
    rel = a - b if gap > 0 else b - a
    if rel <= 0: return dict(out, days=None)   # 以目前速度不會交叉
    days = abs(gap) / rel
    if days > PROJ_MAX: return dict(out, days=None)
    days = round(days)
    return dict(out, days=days, date=ds(dn(d) + days), sth_at=round(sth[d] + a * days), tmm_at=round(tmm[d] + b * days))


def build(mv, ex, sth, tmm, last):
    """mv：CoinMetrics (date, price, mvrv, mktcap, supply)；ex：(date, 交易所供給)；sth、tmm：bitcoin-data {date: 美元}。"""
    d = [x[0] for x in mv]; p = [x[1] for x in mv]; m = [x[2] for x in mv]; rc = [x[3] / x[2] for x in mv]
    start = (dt.date.fromisoformat(d[-1]) - dt.timedelta(days=365 * YEARS)).isoformat(); i0 = bisect.bisect_left(d, start)
    V = dict(start=start, step=STEP, source='價格與 MVRV、實現市值、交易所供給：CoinMetrics；短期持有者成本、真實市場均價：bitcoin-data')
    V['px'] = thin([[dn(d[k]), round(p[k])] for k in range(i0, len(d))])
    # 12 個月動能：一年前的價格（往後延伸 AHEAD 天：未來每一天要比的那個價格現在就已知道）
    ago = []
    for k in range(i0, len(d) + AHEAD):
        t = dn(d[k]) if k < len(d) else dn(d[-1]) + (k - len(d) + 1)
        j = _at_or_before(d, ds(t - 365))
        if j is not None: ago.append([t, round(p[j])])
    nxt = [r for r in ago if dn(d[-1]) < r[0] <= dn(d[-1]) + 30]
    hi30 = max(nxt, key=lambda r: r[1]) if nxt else None
    now_ok = p[-1] > p[_at_or_before(d, ds(dn(d[-1]) - 365))]
    flip = next((r for r in ago if r[0] > dn(d[-1]) and (p[-1] > r[1]) != now_ok), None)   # 價格不動時，燈號第一個會翻轉的日子
    V['mom12'] = dict(ago=thin(ago[:len(d) - i0]) + ago[len(d) - i0:][STEP - 1::STEP], ahead_from=dn(d[-1]),
                      hi30=dict(date=ds(hi30[0]), price=hi30[1], vs_now_pct=round((p[-1] / hi30[1] - 1) * 100, 1)) if hi30 else None,
                      flat_flip=dict(date=ds(flip[0]), price=flip[1]) if flip else None)
    # MVRV 與自己的一年均值（與燈號同算法：最近 365 筆平均）
    V['mvrv1y'] = dict(v=thin([[dn(d[k]), round(m[k], 3)] for k in range(i0, len(d))]),
                       ma=thin([[dn(d[k]), round(sum(m[k - 364:k + 1]) / 365, 3)] for k in range(max(i0, 364), len(d))]))
    # 資金流入：實現市值 30 日變化（%）
    rg = []
    for k in range(i0, len(d)):
        j = _at_or_before(d, (dt.date.fromisoformat(d[k]) - dt.timedelta(days=30)).isoformat())
        if j is not None: rg.append([dn(d[k]), round((rc[k] / rc[j] - 1) * 100, 2)])
    V['rcgrowth'] = dict(v=thin(rg))
    # 交易所供給 90 日變化（%；與燈號同算法：往前第 90 筆）
    ed = [x[0] for x in ex]; e0 = bisect.bisect_left(ed, start)
    V['xs90'] = dict(v=thin([[dn(ex[k][0]), round((ex[k][1] / ex[k - 90][1] - 1) * 100, 2)] for k in range(max(e0, 90), len(ex))]))
    # 短期持有者成本（與價格同一張圖）
    V['sth'] = dict(v=thin([[dn(t), round(v)] for t, v in sorted(sth.items()) if t >= start]))
    # 短期持有者成本 vs 真實市場均價 ＋ 以近 30 日速度的外推
    cd = sorted(set(sth) & set(tmm))
    if cd:
        est = _cross(sth, tmm, cd); x0 = dn(cd[-1])
        proj = None
        if est and est.get('sth_per_day') is not None:
            span = est['days'] if est.get('days') else 90   # 不會交叉時只畫 90 天，讓人看到兩條線的方向
            proj = dict(sth=[[x0, round(sth[cd[-1]])], [x0 + span, round(sth[cd[-1]] + est['sth_per_day'] * span)]],
                        tmm=[[x0, round(tmm[cd[-1]])], [x0 + span, round(tmm[cd[-1]] + est['tmm_per_day'] * span)]])
        V['tmm'] = dict(tmm=thin([[dn(t), round(tmm[t])] for t in cd if t >= start]), est=est, proj=proj,
                        crosses=[[dn(cd[k]), 'up' if sth[cd[k]] > tmm[cd[k]] else 'down'] for k in range(1, len(cd))
                                 if (sth[cd[k]] > tmm[cd[k]]) != (sth[cd[k - 1]] > tmm[cd[k - 1]]) and cd[k] >= start])
    return V


def sopr_viz(sopr, px, days=365, depth=0.995, near=0.04, within=60):
    """2026-10-14 使用者要求：短期持有者認賠賣壓（STH-SOPR；2026-10-15 起資料來自 CheckOnChain，晚約 1 天）。只作讀值、不連動任何規則。
    認賠段＝SOPR 連續低於 1 的日子；段內最低點＝這次認賠的深度（最低 < depth 才算一次）。
    價格回到前一次認賠低點附近（±near）、且相隔 ≤ within 天時，比較兩次深度：比上次淺＝賣壓遞減，比上次深＝賣壓加重。
    日線粒度：隔幾天內的兩次下殺可能落在同一段。"""
    s = sorted(sopr.items())
    if len(s) < 60: return None
    last = s[-1][0]; start = (dt.date.fromisoformat(last) - dt.timedelta(days=days)).isoformat()
    dips, seg = [], []
    for t, v in s + [(None, 9)]:
        if t is not None and v < 1: seg.append((t, v)); continue
        if seg:
            m = min(seg, key=lambda z: z[1])
            if m[1] < depth: dips.append(dict(d=m[0], sopr=round(m[1], 4), days_below=len(seg), open=t is None))
            seg = []
    for i, dp in enumerate(dips):
        p = px.get(dp['d']); dp['price'] = round(p) if p else None
        if not p: continue
        prev = [q for q in dips[:i] if q.get('price') and 0 < (dt.date.fromisoformat(dp['d']) - dt.date.fromisoformat(q['d'])).days <= within and abs(p / q['price'] - 1) <= near]
        if prev:
            q = prev[-1]; dp['vs'] = dict(d=q['d'], sopr=q['sopr'], price=q['price'])
            dp['kind'] = 'easing' if dp['sopr'] > q['sopr'] else 'heavier' if dp['sopr'] < q['sopr'] else 'flat'
    rows = [[dn(t), round(v, 4), round(px[t]) if t in px else None] for t, v in s if t >= start]
    lv = s[-1][1]
    return dict(date=last, value=round(lv, 4), rows=rows, dips=[dict(dp, x=dn(dp['d'])) for dp in dips if dp['d'] >= start],
                below_run=next((k for k, (_, v) in enumerate(reversed(s)) if v >= 1), len(s)),
                note='CheckOnChain，晚約 1 天；日線。只作讀值')


def sth_pnl_viz(pnl, px, days=365):
    """2026-10-23 使用者要求：短期持有者實現獲利與實現虧損（CheckOnChain，BTC，已平滑）。只作讀值、不連動任何規則。
    和 7 天前比，各自變化多少，用來分辨獲利 ÷ 虧損的升降是哪一邊帶動的（兩邊取對數變化比大小）。"""
    s = sorted(pnl.items())
    if len(s) < 30: return None
    last, (p, l) = s[-1]; start = (dt.date.fromisoformat(last) - dt.timedelta(days=days)).isoformat()
    d7 = (dt.date.fromisoformat(last) - dt.timedelta(days=7)).isoformat()
    p7, l7 = pnl.get(d7, (None, None))
    out = dict(date=last, profit=round(p), loss=round(l), ratio=round(p / l, 2) if l else None,
               rows=[[dn(t), round(a), round(b), round(px[t]) if t in px else None] for t, (a, b) in s if t >= start],
               note='CheckOnChain，晚約 1 天；BTC；數值已平滑。只作讀值')
    if p7 and l7:
        lp, ll = math.log(p / p7), -math.log(l / l7)   # 兩項相加＝獲利 ÷ 虧損的對數變化
        out['d7'] = dict(date=d7, profit=round(p7), loss=round(l7), ratio=round(p7 / l7, 2),
                         profit_chg_pct=round((p / p7 - 1) * 100, 1), loss_chg_pct=round((l / l7 - 1) * 100, 1),
                         drive='profit' if abs(lp) >= abs(ll) else 'loss')
    return out


# 2026-10-14 使用者要求：鏈上指標表與頂部雷達的每一項都畫近 3 年走勢（配價格線，價格沿用 build() 的 px）。只作讀值。
#   (key, 畫法, 參考線)：ma7＝畫 7 日均（SOPR 日值雜訊大）；p80＝四年 80 百分位（頂部三指標的頂部區門檻）；top2025＝2025 頂部附近的極值；one＝1.0
OC_VIZ = [('mvrv-zscore', 'raw', 'p80'), ('nupl', 'raw', 'p80'), ('puell-multiple', 'raw', 'p80'),
          ('asopr', 'ma7', 'one'), ('sth-sopr', 'ma7', 'one'), ('lth-sopr', 'ma7', 'one'),
          ('illiquid-supply', 'raw', None), ('highly-liquid-supply', 'raw', None),
          ('lth-mvrv-zscore', 'raw', 'top2025'), ('supply-in-profit-pct', 'raw', 'top2025'), ('lth-net-position-change-30d-btc', 'raw', 'top2025')]


def onchain_viz(SER, years=YEARS, step=STEP):
    out = {}
    for key, how, ref in OC_VIZ:
        ser = sorted((SER.get(key) or {}).items())
        if len(ser) < 30: continue
        last = ser[-1][0]; start = (dt.date.fromisoformat(last) - dt.timedelta(days=365 * years)).isoformat()
        vals = [v for _, v in ser]
        if how == 'ma7': pts = [[dn(ser[k][0]), round(sum(vals[k - 6:k + 1]) / 7, 4)] for k in range(6, len(ser)) if ser[k][0] >= start]
        else: pts = [[dn(t), round(v, 4) if abs(v) < 1e4 else round(v)] for t, v in ser if t >= start]
        o = dict(date=last, how=how, rows=thin(pts, step), last=pts[-1][1] if pts else None)
        if ref == 'p80':
            w4 = sorted(v for t, v in ser if t >= (dt.date.fromisoformat(last) - dt.timedelta(days=1461)).isoformat())
            o['ref'] = dict(kind='p80', y=round(w4[int(len(w4) * 0.8)], 4))
        elif ref == 'top2025':
            at = [v for t, v in ser if '2025-09-22' <= t <= '2025-10-20']
            if at: o['ref'] = dict(kind='top2025', y=round((min if 'net-position' in key else max)(at), 4))
        elif ref == 'one': o['ref'] = dict(kind='one', y=1.0)
        # 方向：與 30 天前、90 天前比（同一畫法）
        for dd in (30, 90):
            j = _at_or_before([ds(r[0]) for r in pts], ds(pts[-1][0] - dd)) if pts else None
            if j is not None: o[f'chg{dd}'] = round(pts[-1][1] - pts[j][1], 4)
        out[key] = o
    return out


# 2026-10-29 使用者要求（貝格先生轉的 Glassnode「吸籌趨勢評分」圖）：價格線依長期持有者 30 日淨部位上色。只作讀值。
#   Glassnode 的評分要先把地址歸成實體、排除交易所與礦工（付費資料），做不出來；bitcoin-data 同名的 accumulation-trend-score
#   與 LTH 30 日淨部位相關 0.97（同一個數字換算），所以直接用已抓的 lth-net-position-change-30d-btc，不另打 API。
#   淨部位上升也包括幣放滿 155 天自動算成長期持有者，不等於有人買入。
LC_CLIP, LC_FLAT = 400000, 50000   # 顏色最深（±40 萬顆）；|淨部位| < 5 萬顆算持平


def lth_color_viz(lth, px, step=2, clip=LC_CLIP, flat=LC_FLAT):
    """lth：{date: 30 日淨部位（顆）}；px：{date: 收盤}。回傳價格線上色資料與讀值（目前這段顏色從哪天開始、期間價格變化、上一次一樣深）。"""
    cd = sorted(t for t in lth if t in px)
    if len(cd) < 60: return None
    last = cd[-1]; v = lth[last]; vals = sorted(lth[t] for t in cd)
    sg = lambda x: (x > 0) - (x < 0)   # 這段從哪天開始只看正負（顏色的「持平」只是幅度小，方向沒變）
    k = len(cd) - 1
    while k > 0 and sg(lth[cd[k - 1]]) == sg(v): k -= 1
    seg = [lth[t] for t in cd[k:]]
    run = dict(start=cd[k], days=(dt.date.fromisoformat(last) - dt.date.fromisoformat(cd[k])).days + 1, sign=sg(v),
               price0=round(px[cd[k]]), price=round(px[last]), price_chg_pct=round((px[last] / px[cd[k]] - 1) * 100, 1),
               extreme=round(min(seg) if v < 0 else max(seg)))
    # 這段之前，上一次淨部位一樣深（同方向、絕對值不小於現在）
    prev = next((t for t in reversed(cd[:k]) if abs(v) >= flat and (lth[t] <= v if v < 0 else lth[t] >= v)), None)
    y1 = [px[t] for t in px if ds(dn(last) - 365) <= t <= last]
    out = dict(date=last, last=round(v), pct_4y=round(sum(x < v for x in vals) / len(vals) * 100, 1), clip=clip, flat=flat, run=run,
               prev_same=dict(date=prev, value=round(lth[prev]), price=round(px[prev])) if prev else None,
               hi1y=round(max(y1)), vs_hi1y_pct=round((px[last] / max(y1) - 1) * 100, 1),
               rows=thin([[dn(t), round(px[t]), round(lth[t])] for t in cd], step),
               note='bitcoin-data lth-net-position-change-30d；不是 Glassnode 的吸籌趨勢評分（那個以實體計、排除交易所）；淨部位上升也包括幣放滿 155 天自動轉成長期持有者；只作讀值')
    j = _at_or_before(cd, ds(dn(last) - 30))
    if j is not None: out['chg30'] = round(v - lth[cd[j]])
    return out
