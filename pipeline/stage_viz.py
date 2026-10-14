"""市場階段佐證燈號的走勢圖資料與第 6 盞燈（2026-10-14 使用者要求）。
只作讀值、不參與 P23 判定；collect.py 在 G4c 呼叫，不另打 API（沿用 CoinMetrics 與 bitcoin-data 已抓的序列）。
x 一律為 1970-01-01 起的天數（頁面 JS 轉回日期）；序列每 STEP 天取一點，最後一點一定保留。"""
import bisect, datetime as dt

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
