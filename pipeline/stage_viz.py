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


def tmm_light(sth, tmm, src='bitcoin-data，晚約 7 天'):
    """第 6 盞：短期持有者成本 vs 真實市場均價（兩條同一家同日比較，不跨資料商相減；2026-11-04 起是 Bitview，失敗時退回 bitcoin-data）。"""
    cd = sorted(set(sth) & set(tmm))
    if len(cd) < 31: return None
    d = cd[-1]; s0, t0 = sth[d], tmm[d]
    return dict(id='tmm', label='短期持有者成本 vs 真實市場均價', ok=s0 > t0, value=round((s0 / t0 - 1) * 100, 2), unit='%',
                cond=f'短期持有者成本高於真實市場均價（{src}）', src=src.split('，')[0], date=d, est=_cross(sth, tmm, cd))


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


def build(mv, ex, sth, tmm, last, src='bitcoin-data'):
    """mv：CoinMetrics (date, price, mvrv, mktcap, supply)；ex：(date, 交易所供給)；sth、tmm：{date: 美元}（src 那一家，2026-11-04 起是 Bitview）。"""
    d = [x[0] for x in mv]; p = [x[1] for x in mv]; m = [x[2] for x in mv]; rc = [x[3] / x[2] for x in mv]
    start = (dt.date.fromisoformat(d[-1]) - dt.timedelta(days=365 * YEARS)).isoformat(); i0 = bisect.bisect_left(d, start)
    V = dict(start=start, step=STEP, source=f'價格與 MVRV、實現市值、交易所供給：CoinMetrics；短期持有者成本、真實市場均價：{src}', cost_src=src)
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
    V.update(cost_viz(sth, tmm, start))
    return V


def cost_viz(sth, tmm, start):
    """短期持有者成本（與價格同一張圖）、短期持有者成本 vs 真實市場均價 ＋ 以近 30 日速度的外推（2026-11-04 從 build 拆出，補值時可單獨重算）"""
    V = dict(sth=dict(v=thin([[dn(t), round(v)] for t, v in sorted(sth.items()) if t >= start])))
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


def canon_px(ser, px):
    """2026-11-04：{date: (值…, 來源自帶的價格)} 的價格換成網站統一的收盤（px，Kraken 優先、更早 CoinMetrics）；px 沒有的日子保留原值"""
    return {d: tuple(v[:-1]) + (px.get(d, v[-1]),) for d, v in ser.items()}


# 2026-11-02 使用者要求（Murphy〈卖方衰竭指数〉）：賣方衰竭常數＝獲利供給比例 × 30 天價格波動（Checkmate 設計，資料取自 CheckOnChain，見 coc.get_sec）。
#   CheckOnChain 的刻度和 Glassnode 版不同（Murphy 的 0.01 線不能套），極端區用本身的歷史分布：低於 0.13 約是 2011 年起最低 1% 的日子。只作讀值
SEC_TH, SEC_FROM, SEC_ROWS = 0.13, '2011-01-01', '2012-01-01'


def sec_viz(ser, last, th=SEC_TH, block=4):
    """ser：{date: (常數, 價格)}。回傳圖表資料（每 block 天取最低值，低點不會被抽樣漏掉）、現值百分位、歷次跌破與之後的價格表現。"""
    D = sorted(d for d in ser if SEC_FROM <= d <= last)
    if len(D) < 1000: return None
    v = {d: ser[d][0] for d in D}; px = {d: ser[d][1] for d in D}; d1 = D[-1]; cur = v[d1]
    hits, lastb = [], None
    for d in D:
        if v[d] < th:
            if lastb is None or dn(d) - dn(lastb) > 90: hits.append(dict(date=d, price=round(px[d])))
            lastb = d
    for h in hits:   # 第一次跌破後 90 天內的最低值；之後 90／180／365 天的漲跌與一年內最大回撤
        t = dn(h['date']); p0 = px[h['date']]; win = [x for x in D if t <= dn(x) <= t + 90]; m = min(win, key=v.get)
        h.update(low=round(v[m], 4), low_date=m, low_price=round(px[m]))
        for n in (90, 180, 365):
            x = ds(t + n); h[f'r{n}'] = round((px[x] / p0 - 1) * 100, 1) if x in px else None
        y = [px[x] for x in D if t <= dn(x) <= t + 365]
        h['dd365'] = round((min(y) / p0 - 1) * 100, 1) + 0.0; h['done'] = dn(d1) - t >= 365
    w30 = [x for x in D if dn(x) > dn(d1) - 30]; r = min(w30, key=v.get)
    rows, k0 = [], next(i for i, d in enumerate(D) if d >= SEC_ROWS)
    for i in range(len(D) - 1, k0 - 1, -block):   # 由最新往回切
        seg = D[max(k0, i - block + 1): i + 1]; m = min(seg, key=v.get)
        # 2026-11-04：低點標在它自己那天（原本標在段尾，日期最多差 3 天、價格也是段尾的）；最新一天另外補上，圖的終點一定是最新值
        if i == len(D) - 1 and m != seg[-1]: rows.append([dn(seg[-1]), round(v[seg[-1]], 4), round(px[seg[-1]])])
        rows.append([dn(m), round(v[m], 4), round(px[m])])
    rows.reverse()
    vals = sorted(v.values())
    return dict(date=d1, value=round(cur, 4), price=round(px[d1]), pct=round(sum(x < cur for x in vals) / len(vals) * 100, 1), th=th,
                th_share=round(sum(x < th for x in vals) / len(vals) * 100, 1), since=D[0],
                min=dict(date=min(D, key=v.get), value=round(min(vals), 4)), hits=hits,
                recent_low=dict(date=r, value=round(v[r], 4), price=round(px[r])), rows=rows,
                note='CheckOnChain 賣方衰竭常數＝獲利供給比例 × 30 天價格波動；刻度和 Glassnode 版不同；極端區＝低於 0.13（本身歷史最低約 1%）；只作讀值')


# 2026-11-02 使用者要求（貝格先生的 Realized P/L 比率圖）：全網實現獲利 ÷ 實現虧損，取 90 天平均（Glassnode 圖的做法），資料取自 CheckOnChain（coc.get_rpl）。
#   低於 1＝認賠多於獲利（紅色）。歷史上大段紅色都在熊市；回到 1 以上之後多半到週期頂部都沒再跌破，但 2019/12–2020/1 例外。只作讀值
RPL_N, RPL_FROM, RPL_MAJOR = 90, '2011-01-01', 60


def rpl_viz(ser, last, block=4):
    """ser：{date: (每日比值, 價格)}。回傳 90 天平均的圖表資料、紅色期間（低於 1）、最近 7 天每日比值與「維持這個水準何時跌破 1」的試算。"""
    D = sorted(d for d in ser if d <= last)
    if len(D) < 1000: return None
    r = [ser[d][0] for d in D]; px = {d: ser[d][1] for d in D}
    m = {D[i]: sum(r[i - RPL_N + 1:i + 1]) / RPL_N for i in range(RPL_N - 1, len(D))}
    M = [d for d in D if d in m and d >= RPL_FROM]; d1 = M[-1]
    reds, cur = [], None
    for d in M:
        if m[d] < 1:
            if cur is None: cur = dict(start=d, end=d, low=m[d], low_date=d)
            cur['end'] = d
            if m[d] < cur['low']: cur['low'], cur['low_date'] = m[d], d
        elif cur: reds.append(cur); cur = None
    if cur: reds.append(dict(cur, open=True))
    reds = [x for x in reds if dn(x['end']) - dn(x['start']) + 1 >= 5]
    for x in reds:
        x['days'] = dn(x['end']) - dn(x['start']) + 1; x['low'] = round(x['low'], 3); x['low_price'] = round(px[x['low_date']]); x['major'] = x['days'] >= RPL_MAJOR
        e = ds(dn(x['end']) + 365); x['r365'] = round((px[e] / px[x['end']] - 1) * 100, 1) if e in px and not x.get('open') else None
    for x in reds:   # 大段紅色結束後一年內，有沒有再跌回 1 以下
        if x['major'] and not x.get('open'):
            t = dn(x['end']); x['relapse'] = [dict(start=y['start'], days=y['days'], low=y['low']) for y in reds if t < dn(y['start']) <= t + 365]
    above = m[d1] >= 1
    k = len(M) - 1
    while k > 0 and (m[M[k - 1]] >= 1) == above: k -= 1
    l7 = sum(r[-7:]) / 7
    proj = None   # 每日比值維持最近 7 天平均時，90 天平均哪天會穿過 1（只是試算）
    w = r[-RPL_N:]
    for n in range(1, 366):
        w = w[1:] + [l7]
        if (sum(w) / RPL_N >= 1) != above: proj = dict(date=ds(dn(D[-1]) + n), days=n, daily=round(l7, 3)); break
    rows, k0 = [], next(i for i, d in enumerate(M) if d >= '2012-01-01')
    for i in range(len(M) - 1, k0 - 1, -block):
        # 2026-11-04：每 block 天取一點；段內有低於 1 的日子就取最低那天（原本固定取段尾，5–59 天的短紅段可能在線上看不到）
        seg = M[max(k0, i - block + 1): i + 1]; lo_ = min(seg, key=m.get); d_ = lo_ if m[lo_] < 1 else seg[-1]
        if i == len(M) - 1 and d_ != seg[-1]: rows.append([dn(seg[-1]), round(m[seg[-1]], 3), round(px[seg[-1]])])
        rows.append([dn(d_), round(m[d_], 3), round(px[d_])])
    rows.reverse()
    return dict(date=d1, value=round(m[d1], 3), price=round(px[d1]), above=above, since=M[k], since_days=dn(d1) - dn(M[k]),
                first2=next((d for d in M[k:] if m[d] >= 2), None) if above else None,
                daily=[[d, round(ser[d][0], 3)] for d in D[-14:]], last7=round(l7, 3), proj=proj, reds=reds, rows=rows,
                note='CheckOnChain 全網實現獲利 ÷ 實現虧損，每日比值取 90 天平均；低於 1＝認賠多於獲利；試算假設每日比值維持最近 7 天平均；只作讀值')


# 2026-11-03 使用者要求（CryptoPainter 的 JT_Regime_Osc 不公開，做我們自己的版本）：週線多空分數。
#   用網站已有、可追溯到 2013 年的六個訊號合成一條以零為中心的柱狀圖，每一項都看得到原因：
#   200 日均線位置、12 個月動能、MVRV 對一年均值、實現市值 30 日、交易所供給 90 日（減少為正）、實現獲利 ÷ 虧損 90 天平均（log10）。
#   每項先除以自己 2013 年起絕對值的中位數再取 tanh（典型大小約 ±0.76、極端趨近 ±1），六項平均後乘 6，範圍 −6 到 +6。
#   多空翻轉＝連續 4 週在另一邊才算（第一週為翻轉日），避免在零軸附近來回跳。只作讀值
REG_KEYS = ('d200', 'mom12', 'mvrv1y', 'rc30', 'xs90', 'rpl')
REG_FROM, REG_CONFIRM = '2013-01-01', 4


def regime_viz(cm, rpl, last, step=7, px=None):
    """cm：CoinMetrics [(date, 價格, MVRV, 市值, 流通量, 交易所供給)]；rpl：{date: 每日實現獲利 ÷ 虧損 或 (比值, 價格)}。"""
    rows = [x for x in cm if x[0] <= last and x[2]]
    D = [x[0] for x in rows]; P = [x[1] for x in rows]; MV = [x[2] for x in rows]; RC = [x[3] / x[2] for x in rows]; EX = [x[5] for x in rows]
    n = len(D)
    if n < 800: return None
    cp, cm_ = [0.0], [0.0]
    for i in range(n): cp.append(cp[-1] + P[i]); cm_.append(cm_[-1] + MV[i])
    rr = {d: (v[0] if isinstance(v, (list, tuple)) else v) for d, v in (rpl or {}).items()}
    RD = sorted(rr); r90, s = {}, 0.0
    for i, d in enumerate(RD):
        s += rr[d]
        if i >= 90: s -= rr[RD[i - 90]]
        if i >= 89: r90[d] = s / 90
    raw = {}
    for i in range(365, n):
        d = D[i]
        raw[d] = dict(d200=P[i] / ((cp[i + 1] - cp[i - 199]) / 200) - 1, mom12=math.log(P[i] / P[i - 365]),
                      mvrv1y=MV[i] / ((cm_[i + 1] - cm_[i - 364]) / 365) - 1, rc30=RC[i] / RC[i - 30] - 1,
                      xs90=-(EX[i] / EX[i - 90] - 1) if EX[i] and EX[i - 90] else None, rpl=math.log10(r90[d]) if r90.get(d) else None)
    days = [d for d in D if d in raw and d >= REG_FROM]
    sc = {}
    for k in REG_KEYS:
        a = sorted(abs(raw[d][k]) for d in days if raw[d][k] is not None)
        sc[k] = (a[len(a) // 2] if a else 0) or 1e-9   # 2026-11-04：某一項整條缺（例如實現損益比沒抓到）時其餘五項照算，不讓整張消失
    def score(d):
        v = [math.tanh(raw[d][k] / sc[k]) for k in REG_KEYS if raw[d][k] is not None]
        return sum(v) / len(v) * len(REG_KEYS) if v else None
    W = days[::-1][::step][::-1]   # 由最新一天往回每 7 天一點
    S = [(d, score(d)) for d in W]; S = [x for x in S if x[1] is not None]
    pi = {d: (px or {}).get(d, P[i]) for i, d in enumerate(D)}   # 顯示與翻轉後漲跌用統一收盤（2026-11-04）；分數本身仍用 CoinMetrics 價格算
    flips, reg, run = [], (1 if S[0][1] >= 0 else -1), 0
    for j, (d, v) in enumerate(S):
        sg = 1 if v >= 0 else -1
        run = run + 1 if sg != reg else 0
        if run >= REG_CONFIRM:
            reg = sg; f = S[j - REG_CONFIRM + 1][0]; t = dn(f)
            fw = {w: (round((pi[ds(t + w * 7)] / pi[f] - 1) * 100, 1) if ds(t + w * 7) in pi else None) for w in (26, 52)}
            flips.append(dict(date=f, dir=sg, price=round(pi[f]), r26=fw[26], r52=fw[52])); run = 0
    for a, b in zip(flips, flips[1:]): a['weeks'] = (dn(b['date']) - dn(a['date'])) // 7
    d1, v1 = S[-1]; last_f = flips[-1] if flips else None
    pend = 0
    for d, v in reversed(S):
        if (1 if v >= 0 else -1) != reg: pend += 1
        else: break
    return dict(date=d1, value=round(v1, 2), prev=round(S[-2][1], 2), prev4=round(S[-5][1], 2), regime=reg,
                since=last_f['date'] if last_f else None, weeks=(dn(d1) - dn(last_f['date'])) // 7 if last_f else None, pending=pend,
                comps=[dict(key=k, raw=round(raw[d1][k], 4) if raw[d1][k] is not None else None, val=round(math.tanh(raw[d1][k] / sc[k]), 2) if raw[d1][k] is not None else None) for k in REG_KEYS],
                scales={k: round(sc[k], 4) for k in REG_KEYS}, flips=flips, rows=[[dn(d), round(v, 2), round(pi[d])] for d, v in S],
                note='六項（200 日均線位置、12 個月動能、MVRV 對一年均值、實現市值 30 日、交易所供給 90 日、實現獲利 ÷ 虧損 90 天）各除以自己的歷史中位數取 tanh 後平均 ×6；連續 4 週在另一邊才算翻轉；只作讀值')


# 2026-11-03 使用者要求（CryptoQuant 的 Apparent Demand，@xwinfinance 的圖）：表觀需求（30 天合計）＝30 天新挖出的幣 − 30 天內 1 年以上未動供給的變化。
#   1 年以上供給取自 CheckOnChain HODL Waves（coc.get_hodl1y，逐筆 UTXO、不是實體調整）；新挖出的幣照減半時程 × 每天 144 個區塊估。
#   單日 1 年以上供給掉超過 max(10 萬, 20 倍日變化中位數) 標成「疑似搬家」（交易所／託管整理錢包，CryptoQuant 的版本看不到這種尖峰），
#   這批幣若一直不動會在一年後同一天滿一年、把數值拉低同樣的量（回音）。數字照實顯示、不修改。只作讀值
AD_FROM, AD_MOVE = '2020-01-01', 100000


def _subsidy(d):
    for h, s in (('2028-04-15', 1.5625), ('2024-04-20', 3.125), ('2020-05-11', 6.25), ('2016-07-09', 12.5), ('2012-11-28', 25.0)):
        if d >= h: return s * 144
    return 50.0 * 144


def ad_viz(ser, last, step=3):
    """ser：{date: (1 年以上供給, 價格)}。回傳 30 天表觀需求、它的 30 日平均、疑似搬家日與回音、圖表資料。"""
    D = sorted(d for d in ser if d <= last)
    if len(D) < 800: return None
    iv = {d: ser[d][0] for d in D}; px = {d: ser[d][1] for d in D}; ix = {d: k for k, d in enumerate(D)}
    ad = {}; ad1y = {}; sub = [_subsidy(d) for d in D]; cs = [0.0]
    for v in sub: cs.append(cs[-1] + v)
    for k in range(30, len(D)):
        d = D[k]; ad[d] = cs[k + 1] - cs[k - 29] - (iv[d] - iv[D[k - 30]])
        if k >= 365: ad1y[d] = cs[k + 1] - cs[k - 364] - (iv[d] - iv[D[k - 365]])   # 2026-11-05 1 年版（365 天合計）
    A = [d for d in D if d in ad]
    sma = {A[k]: sum(ad[A[j]] for j in range(k - 29, k + 1)) / 30 for k in range(29, len(A))}
    dl = [(D[k], iv[D[k]] - iv[D[k - 1]]) for k in range(1, len(D)) if D[k] >= '2016-01-01']
    med = sorted(abs(v) for _, v in dl)[len(dl) // 2]; thr = max(AD_MOVE, 20 * med)
    moves = []
    for d, v in dl:   # 相鄰幾天的大量搬動併成一次
        if v > -thr: continue
        if moves and dn(d) - dn(moves[-1]['end']) <= 2: moves[-1]['end'] = d; moves[-1]['btc'] += round(-v)
        else: moves.append(dict(start=d, end=d, btc=round(-v)))
    dmap = dict(dl)
    for m in moves:   # 回音：一年後那幾天 1 年以上供給的最大單日增加（驗證過 2023-07-28 → 2024-07-27、2024-10-08 → 2025-10-08 都對得上）
        m['echo'] = ds(dn(m['start']) + 365)
        if m['echo'] <= last: m['echo_rise'] = round(max(dmap.get(ds(dn(m['echo']) + k), 0) for k in range(-2, 4)))
    d1 = A[-1]; w7 = A[-8] if len(A) > 8 else None
    vals = sorted(ad[d] for d in A if d >= AD_FROM)
    rows = [[dn(d), round(ad[d]), round(sma[d]) if d in sma else None, round(px[d]), round(ad1y[d]) if d in ad1y else None] for d in A if d >= AD_FROM][::-1][::step][::-1]
    # 2026-11-05 使用者要求（補充指標 PDF）：1 年版。「30 天負、1 年正」常被說成牛市中的回調，照實列出 2016 起這種組合之後 90 天的價格變化
    v1 = sorted(ad1y[d] for d in A if d >= AD_FROM and d in ad1y)
    fw = [(px[D[ix[d] + 90]] / px[d] - 1) * 100 for d in A if d >= '2016-01-01' and d in ad1y and ad[d] < 0 < ad1y[d] and ix[d] + 90 < len(D)]
    fa = [(px[D[ix[d] + 90]] / px[d] - 1) * 100 for d in A if d >= '2016-01-01' and ix[d] + 90 < len(D)]
    med = lambda a: sorted(a)[len(a) // 2] if a else None
    y1 = dict(value=round(ad1y[d1]), issued=round(cs[ix[d1] + 1] - cs[ix[d1] - 364]), inact_chg=round(iv[d1] - iv[D[ix[d1] - 365]]),
              pct=round(sum(x < ad1y[d1] for x in v1) / len(v1) * 100, 1),
              combo=dict(days=len(fw), up90_pct=round(sum(x > 0 for x in fw) / len(fw) * 100) if fw else None, med90=round(med(fw), 1) if fw else None,
                         all_up90_pct=round(sum(x > 0 for x in fa) / len(fa) * 100), all_med90=round(med(fa), 1), since='2016-01-01')) if d1 in ad1y else None
    up = [m for m in moves if d1 < m['echo'] <= ds(dn(d1) + 60)]
    rec = [m for m in moves if dn(d1) - 30 < dn(m['start']) <= dn(d1) or dn(d1) - 30 < dn(m['echo']) <= dn(d1)]
    return dict(date=d1, value=round(ad[d1]), sma30=round(sma[d1]), d7=round(ad[w7]) if w7 else None, price=round(px[d1]),
                inact=round(iv[d1]), inact_chg30=round(iv[d1] - iv[D[ix[d1] - 30]]), issued30=round(sum(_subsidy(D[j]) for j in range(ix[d1] - 29, ix[d1] + 1))),
                pct=round(sum(x < ad[d1] for x in vals) / len(vals) * 100, 1), since=AD_FROM, moves=moves[-12:], echo_soon=up, in_window=rec, move_thr=round(thr),
                y1=y1, rows=rows, note='rows 第 5 欄是 1 年版（365 天合計）；CryptoQuant 定義：30 天新挖出的幣 − 30 天內 1 年以上未動供給的變化；1 年以上供給取自 CheckOnChain HODL Waves（逐筆 UTXO）；新挖出的幣照減半時程估；只作讀值')


# 2026-11-05 使用者要求（補充指標 PDF：LTH／STH Supply Ratio）：長短期持有者供給比＝長期持有者供給 ÷ 短期持有者供給（Bitview lth_supply／sth_supply）。
#   上升＝籌碼沉澱（也包括幣放滿 155 天自動轉成長期），下降＝短期籌碼增加（長期持有者分發或短期持有者進場）。和「長期持有者 30 日淨部位」同一件事的比例版，
#   只放進「價格 × 長期持有者動向」的判讀，不另開圖。只作讀值
LS_FROM = '2015-01-01'


def lsr_viz(bv, last):
    ls, ss = bv.get('lths') or {}, bv.get('sths') or {}
    D = [d for d in sorted(ls) if d <= last and ss.get(d)]
    if len(D) < 800: return None
    r = {d: ls[d] / ss[d] for d in D}; d1 = D[-1]
    at = lambda n: next((d for d in reversed(D) if dn(d) <= dn(d1) - n), None)
    a30, a365 = at(30), at(365)
    y = [d for d in D if dn(d) > dn(d1) - 365]; hi, lo = max(y, key=r.get), min(y, key=r.get)
    H = [r[d] for d in D if d >= LS_FROM]
    return dict(date=d1, value=round(r[d1], 2), lth=round(ls[d1]), sth=round(ss[d1]),
                d30=round(r[a30], 2) if a30 else None, chg30_pct=round((r[d1] / r[a30] - 1) * 100, 1) if a30 else None,
                d365=round(r[a365], 2) if a365 else None, hi1y=dict(date=hi, value=round(r[hi], 2)), lo1y=dict(date=lo, value=round(r[lo], 2)),
                pct=round(sum(v < r[d1] for v in H) / len(H) * 100, 1), since=LS_FROM, src='Bitview',
                note='長期持有者供給 ÷ 短期持有者供給（Bitview，持有 155 天分界）；上升也包括幣放滿 155 天自動轉成長期；只作讀值')


# 2026-11-05 使用者要求（補充指標 PDF：已實現虧損）：長期持有者已實現虧損（Bitview lth_realized_loss_sum_24h，美元；不是 Glassnode 的實體調整版）。
#   相對值＝7 日合計 ÷ 市值（價格 × 長短期持有者供給合計），跨年份才能比。擺動低點＝收盤是前後 30 天最低、且比之前 180 天最高跌 ≥ 20%；低點的值取前後 7 天內最大。
#   2011 起驗證：「低點一次比一次低、虧損一次比一次小＝賣壓衰竭」不成立。2015、2018、2022 三次熊市（前一個頂部到底部後 45 天）都是底部那次低點虧損最大
#   （2015-01 0.86%、2018-12 2.86%、2022-11 1.30%；本輪 2026-06 0.29%）；2018 年 6→8→10 月虧損縮小（0.84 → 0.29 → 0.48）之後還有一次最大的投降。只作讀值
RL_FROM, RL_WIN = '2015-01-01', 30


def lthrl_viz(bv, px, last, bottoms, tops, step=3):
    L, ls, ss = bv.get('lthrl') or {}, bv.get('lths') or {}, bv.get('sths') or {}
    P = lambda d: px.get(d, bv['px'].get(d))
    D = [d for d in sorted(L) if d <= last and P(d) and ls.get(d) and ss.get(d)]
    if len(D) < 1500: return None
    usd, rel = {}, {}
    for j, d in enumerate(D):
        u = sum(L[D[i]] for i in range(max(0, j - 6), j + 1)); usd[d] = u; rel[d] = u / (P(d) * (ls[d] + ss[d])) * 100
    lows = []
    for j in range(RL_WIN, len(D) - RL_WIN):
        p = P(D[j])
        if p == min(P(D[i]) for i in range(j - RL_WIN, j + RL_WIN + 1)) and p <= 0.8 * max(P(D[i]) for i in range(max(0, j - 180), j)):
            k = max(range(max(0, j - 7), min(len(D), j + 8)), key=lambda i: rel[D[i]])
            lows.append(dict(date=D[j], price=round(p), rel=round(rel[D[k]], 3), usd_m=round(usd[D[k]] / 1e6)))
    tp = [t for t, _ in tops]; bear = []
    for bd, _ in bottoms:   # 每次熊市：前一個頂部之後到這個底部（含前後 45 天）的擺動低點
        t0 = max((t for t in tp if t < bd), default=None)
        if not t0 or bd < RL_FROM: continue
        w = [x for x in lows if t0 < x['date'] <= ds(dn(bd) + 45)]
        if not w: continue
        b = max(w, key=lambda x: x['rel'])
        bear.append(dict(top=t0, bottom=bd, lows=w, max=b, last_is_max=b is w[-1]))
    d1 = D[-1]; t_last = tp[-1] if tp else None
    H = [rel[d] for d in D if d >= RL_FROM]
    rows = []
    E = [d for d in D if d >= RL_FROM]
    for i in range(0, len(E), step):   # 每段取最大，尖峰不會被抽樣抽掉
        blk = E[i:i + step]; m = max(blk, key=rel.get); rows.append([dn(m), round(rel[m], 3), round(P(m))])
    if rows and rows[-1][0] != dn(d1): rows.append([dn(d1), round(rel[d1], 3), round(P(d1))])
    return dict(date=d1, rel=round(rel[d1], 3), usd7_m=round(usd[d1] / 1e6), price=round(P(d1)), pct=round(sum(v < rel[d1] for v in H) / len(H) * 100, 1),
                since=RL_FROM, lows_now=[x for x in lows if t_last and x['date'] > t_last], bears=bear, rows=rows, src='Bitview',
                note='長期持有者已實現虧損（Bitview，美元，不是實體調整）7 日合計 ÷ 市值；擺動低點＝前後 30 天最低且比之前 180 天最高跌 ≥ 20%；只作讀值')


# 2026-11-04 使用者要求（ForeDex／加密貝兒的 Supply In Loss % - LTH）：長期持有者虧損比例（CheckOnChain，coc.get_lthloss）。只作讀值。
#   歷輪高點＝各熊市底部（model.json 的 cycle_bottoms）前後 240 天內的最高值；「之後最高」＝高點後 90–730 天內的最高值（驗證「脫離底部後不再創新高」）。
#   打破規律的價位：用 CheckOnChain 依實際幣齡算的長期持有者籌碼分布（cohort，每 2,000 美元一格、格內均勻）推算虧損比例超過這輪高點的價格；
#   最近買進的短期持有者滿 155 天後會轉成長期持有者，價格不漲時這條線會上移，所以每天重算
LL_FROM = '2013-01-01'


def _loss_at(rows, p):
    tot = sum(r[2] for r in rows) or 1; s = 0.0
    for lo, sth, lth in rows:
        if lo >= p: s += lth
        elif lo + 2000 > p: s += lth * (lo + 2000 - p) / 2000
    return s / tot


def lthloss_viz(ser, last, bottoms, cohort=None, block=4):
    """ser：{date: (比例 0–1, 價格)}；bottoms：[[date, price], ...]；cohort：{date, rows:[[價位下緣, STH, LTH]]}"""
    D = sorted(d for d in ser if LL_FROM <= d <= last)
    if len(D) < 800: return None
    v = {d: ser[d][0] for d in D}; px = {d: ser[d][1] for d in D}; d1 = D[-1]
    peaks = []
    for bd, bp in bottoms:
        w = [d for d in D if abs(dn(d) - dn(bd)) <= 240]
        if not w: continue
        pk = max(w, key=v.get); a = [d for d in D if dn(pk) + 90 <= dn(d) <= dn(pk) + 730]
        am = max(a, key=v.get) if a and dn(d1) - dn(pk) >= 730 else None
        peaks.append(dict(bottom=bd, date=pk, value=round(v[pk] * 100, 1), price=round(px[pk]),
                          after_max=dict(date=am, value=round(v[am] * 100, 1), price=round(px[am])) if am else None))
    lp = peaks[-1] if peaks else None
    pm = min((d for d in D if lp and d > lp['date']), key=v.get, default=None)
    out = dict(date=d1, value=round(v[d1] * 100, 1), price=round(px[d1]), peaks=peaks,
               post_min=dict(date=pm, value=round(v[pm] * 100, 1), price=round(px[pm])) if pm else None,
               post_max=round(max(v[d] for d in D if lp and d > lp['date']) * 100, 1) if lp and d1 > lp['date'] else None,
               note='CheckOnChain 長期持有者（持有 ≥155 天）虧損比例；打破規律的價位由 CheckOnChain 長期持有者籌碼分布推算，每天重算；只作讀值')
    rows = []
    for i in range(len(D) - 1, -1, -block):   # 每 4 天取最高值，高點不會被抽樣漏掉
        seg = D[max(0, i - block + 1): i + 1]; m = max(seg, key=v.get)
        # 2026-11-05：高點標在它自己那天（原本標在段尾）；最新一天另外補上，線尾一定是當天值。
        #   原本最後一段取 4 天最高，11/04 線尾畫在 33.6%、旁邊文字寫 31.5%（同 sec_viz、rpl_viz 的做法）
        if i == len(D) - 1 and m != seg[-1]: rows.append([dn(seg[-1]), round(v[seg[-1]] * 100, 1), round(px[seg[-1]])])
        rows.append([dn(m), round(v[m] * 100, 1), round(px[m])])
    out['rows'] = rows[::-1]
    if cohort and cohort.get('rows') and lp:
        R = cohort['rows']; tgt = lp['value'] / 100
        grid = [p for p in range(int(px[d1]) // 500 * 500, 20000, -500)]
        bp = next((p for p in grid if _loss_at(R, p) >= tgt), None)
        out['cohort'] = dict(date=cohort.get('date'), at_close=round(_loss_at(R, px[d1]) * 100, 1), break_price=bp,
                             table=[[p, round(_loss_at(R, p) * 100, 1)] for p in range(int(px[d1]) // 2000 * 2000, max(20000, (bp or 50000) - 4000), -4000)])
    return out


# 2026-11-04 使用者要求（Murphy〈短期持有者成本基礎模型〉，Glassnode 的 STH cost basis ±1/±2 標準差）：資料 Bitview（bitview.get）。
#   帶＝短期持有者成本 ×（近 4 年〔1,460 天〕「價格 ÷ 短期持有者成本」的平均 ± k 個標準差）。帶的中心不是成本線，所以上下不對稱。
#   驗算：2026-11-04 的 −1 標準差算出 68,991，Murphy 寫約 68,900。價格用網站統一收盤（px，沒有的日子用 Bitview 自帶的價格）。只作讀值
#   2026-11-05 加 ±0.5 標準差兩條（bands 的鍵 '0.5'、'-0.5'）：離現價最近的上下兩條，前端畫成點線
SB_W, SB_FROM = 1460, '2022-01-01'


def sth_bands_viz(bv, px, last, step=3):
    sth = bv['sth']; P = {d: px.get(d, bv['px'].get(d)) for d in sth}
    D = [d for d in sorted(sth) if d <= last and P.get(d)]
    if len(D) < SB_W + 200: return None
    r = [P[d] / sth[d] for d in D]; s1 = s2 = 0.0; mu, sd = {}, {}
    for i, x in enumerate(r):
        s1 += x; s2 += x * x
        if i >= SB_W: s1 -= r[i - SB_W]; s2 -= r[i - SB_W] ** 2
        if i >= SB_W - 1:
            m = s1 / SB_W; mu[D[i]] = m; sd[D[i]] = math.sqrt(max(0.0, s2 / SB_W - m * m))
    z = {d: (P[d] / sth[d] - mu[d]) / sd[d] for d in mu if sd[d] > 0}
    d1 = D[-1]; S = sth[d1]; Z = sorted(z)
    last4 = [d for d in Z if dn(d) > dn(d1) - SB_W]
    hi120 = max((d for d in Z if dn(d) > dn(d1) - 120), key=z.get)
    lastof = lambda f: next((d for d in reversed(Z) if f(z[d])), None)
    rows = thin([[dn(d), round(P[d]), round(sth[d]), round(mu[d], 4), round(sd[d], 4)] for d in D if d >= SB_FROM and d in mu], step)
    return dict(date=d1, src='Bitview', window=SB_W, rows=rows,
                now=dict(px=round(P[d1]), sth=round(S), mu=round(mu[d1], 4), sd=round(sd[d1], 4), z=round(z[d1], 2), center=round(S * mu[d1]),
                         bands={str(k): round(S * (mu[d1] + k * sd[d1])) for k in (-2, -1, -0.5, 0.5, 1, 2)}),   # 2026-11-05 加 ±0.5（使用者決定，點子清單）
                stats=dict(above1_pct=round(sum(z[d] >= 1 for d in last4) / len(last4) * 100, 1), below1_pct=round(sum(z[d] <= -1 for d in last4) / len(last4) * 100, 1),
                           last_above1=lastof(lambda v: v >= 1), last_below1=lastof(lambda v: v <= -1), max120=dict(date=hi120, z=round(z[hi120], 2))),
                note='短期持有者成本（Bitview）×（近 4 年價格 ÷ 成本的平均 ± k 個標準差）；Glassnode 的同類模型；只作讀值')


# 2026-11-04 使用者要求（wander〈6M–12M 與 12M–18M 成本線〉，原圖用 Bitview／BRK）：兩個年齡層的平均買價（實現價格）。資料 Bitview（bitview.get）。
#   6–12 個月線跌破 12–18 個月線（死叉）大致在熊底附近，重新上穿（金叉）在主升段前後；交叉日與間隔照實列出。只作讀值
AC_FROM, AC_X = '2015-01-01', '2012-01-01'   # 圖從 2015 起（2014 年 12–18 個月線還在反映 2012–13 年的幣，會把刻度拉到 10 美元）


def age_cost_viz(bv, px, last, step=4):
    a, b = bv['c612'], bv['c1218']
    D = [d for d in sorted(set(a) & set(b)) if d <= last]
    if len(D) < 1000: return None
    P = lambda d: px.get(d, bv['px'].get(d))
    xs = []
    for i in range(1, len(D)):
        if D[i] < AC_X: continue
        up0, up1 = a[D[i - 1]] > b[D[i - 1]], a[D[i]] > b[D[i]]
        if up0 != up1: xs.append(dict(date=D[i], kind='golden' if up1 else 'death', cost=round(a[D[i]]), price=round(P(D[i]) or 0)))
    for i, x in enumerate(xs):
        nx = xs[i + 1] if i + 1 < len(xs) else None
        x['days_to_next'] = dn(nx['date']) - dn(x['date']) if nx else None
    d1 = D[-1]; lx = xs[-1] if xs else None
    c3 = bv.get('c36') or {}; c1 = bv.get('c1m') or {}
    rows = thin([[dn(d), round(P(d)) if P(d) else None, round(a[d]), round(b[d]), round(c3[d]) if d in c3 else None, round(c1[d]) if d in c1 else None] for d in D if d >= AC_FROM], step)
    return dict(date=d1, src='Bitview', rows=rows, crosses=[x for x in xs if x['date'] >= AC_FROM], c612=round(a[d1]), c1218=round(b[d1]),
                gap_pct=round((a[d1] / b[d1] - 1) * 100, 1), price=round(P(d1)), last_cross=lx, days_since=dn(d1) - dn(lx['date']) if lx else None,
                c36=_c36_view(c3, P, D, d1), c1m=_c1m_view(c1, P, D, d1, bv.get('sth') or {}),
                note='Bitview：6–12 個月＝6–9、9–12 個月兩段的實現市值合計 ÷ 供給合計；12–18 個月＝age_1y_to_18m_realized_price；3–6 個月＝3–4、4–5、5–6 個月三段合計；只作讀值')


# 2026-11-05 使用者要求（X 帳號掃描：CryptoQuant 的 Trader Realized Price、短期持有者成本）：1 週–1 個月持幣成本（Bitview age_1w_to_1m_realized_price）＝最近一個月進場、
#   還沒動的人的平均買價。列出和收盤的距離、30 天變化、這次在線上／線下連續幾天、和短期持有者成本的距離。只作讀值
def _c1m_view(c1, P, D, d1, sth):
    DD = [d for d in D if d in c1 and P(d)]
    if not DD or DD[-1] != d1: return None
    above = P(d1) >= c1[d1]; k = len(DD) - 1
    while k > 0 and (P(DD[k - 1]) >= c1[DD[k - 1]]) == above: k -= 1
    return dict(cost=round(c1[d1]), price=round(P(d1)), gap_pct=round((P(d1) / c1[d1] - 1) * 100, 1), above=above, since=DD[k], days=len(DD) - k,
                chg30=round(c1[d1] - c1[DD[-31]]) if len(DD) > 31 else None, sth=round(sth[d1]) if sth.get(d1) else None,
                vs_sth_pct=round((c1[d1] / sth[d1] - 1) * 100, 1) if sth.get(d1) else None)


# 2026-11-04 使用者要求（3–6 個月持幣成本，價格上穿後的天數）：價格由下往上穿越 3–6 個月成本的日子。熊市後的第一次（之前在線下 ≥ 250 天）另外標出，
#   列出之後 180 天內的最高收盤與天數（「約 80 天到頂」只有 2019 年吻合：2015、2023 的半年高點在 170 天後）。只作讀值，不做到頂倒數
C36_BEAR = 250


def _c36_view(c3, P, D, d1):
    if not c3: return None
    DD = [d for d in D if d in c3 and P(d)]
    ups, below = [], 0
    for i, d in enumerate(DD):
        if P(d) < c3[d]: below += 1; continue
        if below >= 30 and d >= '2012-01-01':
            w = [x for x in DD[i:] if dn(x) - dn(d) <= 180]; hi = max(w, key=P)
            ups.append(dict(date=d, below=below, price=round(P(d)), cost=round(c3[d]), bear=below >= C36_BEAR,
                            hi=dict(date=hi, price=round(P(hi)), days=dn(hi) - dn(d)), done=dn(d1) - dn(d) >= 180))
        below = 0
    last_up = ups[-1] if ups else None
    above = P(d1) >= c3[d1]
    return dict(cost=round(c3[d1]), price=round(P(d1)), gap_pct=round((P(d1) / c3[d1] - 1) * 100, 1), above=above,
                chg30=round(c3[d1] - c3[DD[-31]]) if len(DD) > 31 else None, ups=[u for u in ups if u['date'] >= AC_FROM],
                since=dict(date=last_up['date'], days=dn(d1) - dn(last_up['date'])) if above and last_up else None)


# 2026-11-04 使用者要求（Glassnode 週報〈Retesting the Breakout〉）：價格和下方各條成本線、均線放在同一張圖。
#   均線用統一收盤（px：Kraken 優先、更早 CoinMetrics）；短期持有者成本、真實市場均價、實現價、長期持有者成本用 Bitview（同一家）。
#   50 週均線＝350 日均線。只作讀值：列出價格上下各條線的位置與距離，不說「守住就延續」
LV_FROM, LV_NEAR = '2025-06-01', 8
LV_KEYS = ('sma200', 'sma365', 'sma350', 'sth', 'tmm', 'rp', 'lth', 'act')   # 2026-11-05 加 act：活躍投資人成本（Bitview active_price，Cointime）


def levels_viz(bv, px, last, step=2):
    D = sorted(d for d in px if d <= last)
    P = [px[d] for d in D]; n = len(D)
    if n < 400: return None
    cs = [0.0]
    for v in P: cs.append(cs[-1] + v)
    sma = lambda i, w: (cs[i + 1] - cs[i + 1 - w]) / w if i >= w - 1 else None
    bvv = lambda k, d: (bv.get(k) or {}).get(d)
    def row(i):
        d = D[i]; vals = [sma(i, 200), sma(i, 365), sma(i, 350)] + [bvv(k, d) for k in ('sth', 'tmm', 'rp', 'lth', 'act')]
        return [dn(d), round(P[i])] + [round(v) if v else None for v in vals]
    rows = thin([row(i) for i in range(n) if D[i] >= LV_FROM], step)
    i = n - 1; c = P[i]; now = row(i)
    levels = sorted([dict(key=k, value=v, dist_pct=round((v / c - 1) * 100, 1)) for k, v in zip(LV_KEYS, now[2:]) if v], key=lambda x: -x['value'])
    near = [x for x in levels if x['value'] < c and x['dist_pct'] >= -LV_NEAR]
    # 2026-11-05 使用者要求（X 帳號掃描：Glassnode「85K 一直把價格擋回來」）：活躍投資人成本今年收在上方的天數、最近一次穿越。只作讀值
    A = bv.get('act') or {}; act = None
    if A.get(D[i]):
        y0 = D[i][:4] + '-01-01'; YD = [d for d in D if d >= y0 and A.get(d)]; ab = [d for d in YD if px[d] > A[d]]
        AD = [d for d in D if A.get(d)]; xs = [AD[k] for k in range(1, len(AD)) if (px[AD[k]] > A[AD[k]]) != (px[AD[k - 1]] > A[AD[k - 1]])]
        act = dict(value=round(A[D[i]]), dist_pct=round((A[D[i]] / c - 1) * 100, 1), above=c > A[D[i]], ytd_days=len(YD), ytd_above=len(ab),
                   last_above=ab[-1] if ab else None, last_cross=dict(date=xs[-1], up=px[xs[-1]] > A[xs[-1]]) if xs else None)
    return dict(date=D[i], price=round(c), levels=levels, near=dict(pct=LV_NEAR, lo=min(x['value'] for x in near), hi=max(x['value'] for x in near), keys=[x['key'] for x in near]) if near else None,
                act=act, rows=rows, note='價格、200／365／350 日均線（統一收盤）與 Bitview 的短期持有者成本、真實市場均價、實現價、長期持有者成本、活躍投資人成本（rows 第 10 欄）；50 週＝350 日；只作讀值')


# 2026-11-05 使用者要求（Look Into Bitcoin〈Bitcoin Cycle Capital Flows〉）：實現市值加權的幣齡，1 個月內換手（投機、新錢）與 1–2 年沒動（長線、循環投資人）
#   各佔全體實現市值的 %（Bitview）。頂部時 1 個月內的比例衝高（2017 年 66%、2021 年 51%），熊底時 1–2 年的比例最高（2019 年 42%、2022 年 47%）。只作讀值
CF_FROM = '2015-06-01'


def _peaks(ser, D, sep=500, top=6, floor=0):
    out = []
    for d in sorted(D, key=lambda x: -ser[x]):
        if ser[d] < floor: break
        if any(abs(dn(d) - dn(p)) < sep for p in out): continue
        out.append(d)
        if len(out) == top: break
    return sorted(out)


def capflow_viz(bv, px, last, step=3):
    a, b = bv.get('cf1m') or {}, bv.get('cf12') or {}
    D = [d for d in sorted(set(a) & set(b)) if CF_FROM <= d <= last]
    if len(D) < 800: return None
    P = lambda d: px.get(d, bv['px'].get(d))
    d1 = D[-1]; back = lambda k: max((d for d in D if dn(d) <= dn(d1) - k), default=None)
    d30, d365 = back(30), back(365)
    rows = thin([[dn(d), round(P(d)) if P(d) else None, round(a[d], 1), round(b[d], 1)] for d in D], step)
    return dict(date=d1, src='Bitview', price=round(P(d1)), m1=round(a[d1], 1), y12=round(b[d1], 1),
                m1_30=round(a[d30], 1) if d30 else None, y12_30=round(b[d30], 1) if d30 else None, m1_1y=round(a[d365], 1) if d365 else None, y12_1y=round(b[d365], 1) if d365 else None,
                peaks_m1=[[d, round(a[d], 1)] for d in _peaks(a, D, floor=15)], peaks_y12=[[d, round(b[d], 1)] for d in _peaks(b, D, floor=25)],
                rows=rows, note='Bitview：1 個月內＝<1h、1h–1d、1d–1w、1w–1m 四段實現市值合計；1–2 年＝1y–18m、18m–2y；÷ 全體實現市值；只作讀值')


# 2026-11-07 指標擴充（取代 2026-11-05 的四項短期持有者百分位版「短期壓力分數」）：本站自製的一對讀值，只用每日收盤。
#   動能品質（0–1）：近 21 天日報酬的平均 ÷ 標準差 × √21（t 值），再用常態分布換成 0–1（Φ(0.7 × t)）。漲得又快又穩接近 1，跌得又快又穩接近 0。
#   賣壓累積（0–100）：動能品質低於 0.45 時每天加 30 ×（0.45 − 動能），高於 0.45 時每天減 50 ×（動能 − 0.45），動能一到 0.7 以上直接歸零，夾在 0–100。
#     弱勢拖得越久累積越高（急跌一兩天不會馬上到 100），一段又快又穩的上漲就清空；參數照這個行為挑選，三組相近參數的回測差不多。
#   底部組合＝賣壓 100 且動能 < 0.3（和上一次相隔 60 天以上才算新的一次）。回測照實列出：30／90 天後漲跌、等賣壓回到 0 再出場的結果、分年代；
#   強勢動能（賣壓 0 且動能 > 0.85）之後多半繼續漲，不是頂部訊號，也照實列出。只作讀值、不是買賣訊號。
SX_N, SX_K, SX_TH, SX_UP, SX_DN, SX_RESET, SX_FROM, SX_GAP = 21, 0.7, 0.45, 30, 50, 0.7, '2012-06-01', 60


def stress_viz(bv, px, last, step=3, keep=1095):
    P_ = lambda d: px.get(d) or (bv.get('px') or {}).get(d)
    D = [d for d in sorted(set(px) | set(bv.get('px') or {})) if '2011-06-01' <= d <= last and P_(d)]
    if len(D) < 1500: return None
    P = [P_(d) for d in D]; n = len(D)
    lr = [0.0] + [math.log(P[i] / P[i - 1]) for i in range(1, n)]
    Phi = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
    S, R, r = [None] * n, [None] * n, 0.0
    for i in range(SX_N, n):
        w = lr[i - SX_N + 1: i + 1]; m = sum(w) / SX_N; sd = (sum((a - m) ** 2 for a in w) / (SX_N - 1)) ** 0.5
        s = Phi(SX_K * m / sd * math.sqrt(SX_N)) if sd > 0 else 0.5
        if s >= SX_RESET: r = 0.0
        elif s < SX_TH: r = min(100.0, r + SX_UP * (SX_TH - s))
        else: r = max(0.0, r - SX_DN * (s - SX_TH))
        S[i], R[i] = s, r
    i0 = next(i for i, d in enumerate(D) if d >= SX_FROM)
    fwd = lambda i, h: (P[i + h] / P[i] - 1) * 100 if i + h < n else None
    med = lambda v: round(sorted(v)[len(v) // 2], 1) if v else None
    def stat(ix, h):
        v = [x for x in (fwd(i, h) for i in ix) if x is not None]
        return dict(n=len(v), up=sum(x > 0 for x in v), med=med(v))
    def base(h):
        v = [x for x in (fwd(i, h) for i in range(i0, n)) if x is not None]
        return dict(up=round(sum(x > 0 for x in v) / len(v) * 100), med=med(v))
    def eps(cond):
        out, lastk = [], -10 ** 9
        for i in range(i0, n):
            if cond(i):
                if i - lastk > SX_GAP: out.append(i)
                lastk = i
        return out
    bot = eps(lambda i: R[i] >= 99.5 and S[i] < 0.3)
    ev = []
    for i in bot:
        j = next((k for k in range(i + 1, n) if R[k] == 0), None)
        ev.append(dict(date=D[i], price=round(P[i]), f30=None if fwd(i, 30) is None else round(fwd(i, 30), 1), f90=None if fwd(i, 90) is None else round(fwd(i, 90), 1),
                       exit=D[j] if j else None, ret=round((P[j] / P[i] - 1) * 100, 1) if j else None, days=(j - i) if j else None,
                       dip=round((min(P[i:(j if j else n - 1) + 1]) / P[i] - 1) * 100, 1)))
    done = [e for e in ev if e['ret'] is not None]
    era = []
    for lo, hi in (('2012', '2017'), ('2018', '2022'), ('2023', last[:4])):
        x = [e for e in done if lo <= e['date'][:4] <= hi]
        era.append(dict(lo=lo, hi=hi, n=len(x), win=sum(e['ret'] > 0 for e in x)))
    top = eps(lambda i: R[i] == 0 and S[i] > 0.85)
    k = n - 1; d1 = D[k]; rk = round(R[k])
    z0 = next((j for j in range(k, i0, -1) if R[j - 1] == 0), None) if R[k] > 0 else None   # 這一段從 0 升上來的第一天
    at100 = next((k - j for j in range(k, i0, -1) if R[j] < 99.5), 0) if R[k] >= 99.5 else 0
    s2 = round(S[k], 2)   # 現況標籤用頁面上顯示的兩位小數判斷（0.296 顯示 0.30，就不說「已低於 0.3」）
    near = R[k] >= 60 and (R[k] >= 99.5 or s2 < 0.3 or (R[k] >= 75 and s2 < 0.35))
    state = 'bottom' if R[k] >= 99.5 and s2 < 0.3 else 'near' if near else 'build' if R[k] > 0 else 'strong' if s2 > 0.85 else 'calm'
    cut = dn(d1) - keep
    rows = [[dn(D[i]), round(P[i]), round(R[i]), round(S[i], 3)] for i in range(i0, n) if dn(D[i]) >= cut or (n - 1 - i) % step == 0]
    b7 = D.index(d1) - 7
    return dict(date=d1, price=round(P[k]), r=rk, s=round(S[k], 2), r7=round(R[b7]), s7=round(S[b7], 2), state=state,
                rise_from=D[z0] if z0 else None, at100=at100, max30=round(max(R[k - 29: k + 1])),
                ev=ev, f30=stat(bot, 30), f90=stat(bot, 90), base30=base(30), base90=base(90),
                ex=dict(n=len(done), win=sum(e['ret'] > 0 for e in done), med=med([e['ret'] for e in done]), days=med([e['days'] for e in done]), dip=med([e['dip'] for e in done])),
                era=era, top=dict(n=len(top), f90=stat(top, 90), last=D[top[-1]] if top else None), since=SX_FROM,
                prm=dict(n=SX_N, k=SX_K, th=SX_TH, up=SX_UP, dn=SX_DN, reset=SX_RESET), rows=rows,
                note='本站自製，只用每日收盤：動能品質＝Φ(0.7 × 近 21 天報酬 t 值)；賣壓累積＝動能低於 0.45 時累加、高於時遞減、到 0.7 歸零（0–100）；只作讀值、不是買賣訊號')


# 2026-11-05 使用者要求（X 帳號掃描：頂部後 13 個月前幾輪跌 71–80%、這輪約 35%；回到前高花的時間比跌下去久）：各輪週期頂部之後，
#   每天收盤 ÷ 頂部收盤，畫在同一個「頂部後第幾天」的橫軸上。頂部用 model.json 的 cycle_tops（收盤價），價格用統一收盤。
#   每輪列出：今天這個天數時的位置、最低點（第幾天、跌幅）、從底部到重新站上頂部價花幾天。只作讀值，不推論這輪會怎麼走
CC_DAYS, CC_STEP = 1300, 3


def cycle_cmp_viz(px, tops, last):
    D = sorted(d for d in px if d <= last)
    if len(D) < 2000 or len(tops) < 2: return None
    I = {d: k for k, d in enumerate(D)}
    t_now = tops[-1][0]; n_now = dn(last) - dn(t_now)
    out = []
    for t, tp in tops:
        if t not in I: continue
        k0 = I[t]; top = px[t]; pts = []
        for k in range(k0, len(D)):
            n = dn(D[k]) - dn(t)
            if n > CC_DAYS: break
            pts.append((n, px[D[k]] / top))
        if len(pts) < 30: continue
        lo = min(pts, key=lambda p: p[1]); back = next((p[0] for p in pts if p[0] > lo[0] and p[1] >= 1), None)
        at = next((p for p in reversed(pts) if p[0] <= n_now), None)
        rows = [[n, round(r, 4)] for n, r in pts if n % CC_STEP == 0 or n == pts[-1][0]]
        out.append(dict(top=t, top_price=round(top), now=t == t_now, rows=rows,
                        at=dict(day=at[0], pct=round((at[1] - 1) * 100, 1)) if at else None,
                        low=dict(day=lo[0], pct=round((lo[1] - 1) * 100, 1), date=ds(dn(t) + lo[0]), price=round(top * lo[1])),
                        back_day=back, back_after_low=back - lo[0] if back else None))
    return dict(date=last, day_now=n_now, cycles=out, days=CC_DAYS,
                note='各輪週期頂部（model.json cycle_tops）之後每天收盤 ÷ 頂部收盤；at＝今天這個天數時的位置；low＝頂部後最低；back_day＝最低之後第一次收回頂部價的天數；只作讀值')
