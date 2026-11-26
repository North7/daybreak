#!/usr/bin/env python3
"""那斯達克年內最大回撤，和那斯達克再跌時 BTC 同期跌多少（2026-11-26 使用者看了 Murphy 一則貼文後說「都加」）。

1 歷年回撤：那斯達克綜合指數（FRED NASDAQCOM，1971-02 起）每個自然年裡，從當年最高收盤到之後最低收盤跌了多少。
  1972–2025 共 54 個完整年：中位數 14.9%，18 年超過 20%，10 年超過 30%（1973、74、87、90、2000–02、08、2020、22）。今年到目前另外算。
2 BTC 跟著跌多少：2013 年起每一天，看之後 H（125）天裡那斯達克最深再跌幾 %、BTC 最深再跌幾 %，照那斯達克那段跌多少分三組，
  算 BTC 最深跌 10% 以上、20% 以上的比例和中位數，加上「任何一天」的對照。每天都算一次，相鄰的日子重疊很多，實際獨立的樣本少很多。
  2026-11-26 驗算：任何一天 59%／40%；那斯達克再跌 5–10% 63%／38%；再跌 10% 以上 83%／68%。只作讀值，是「如果那斯達克這樣跌」的對照，不是預測。"""
import bisect, datetime as dt, statistics as st

H = 125   # 大約到下一季結束
GROUPS = [('none', -5, 100, '那斯達克沒再跌 5%', 'Nasdaq fell less than 5% more'), ('mid', -10, -5, '那斯達克再跌 5%–10%', 'Nasdaq fell 5%–10% more'),
          ('big', -100, -10, '那斯達克再跌 10% 以上', 'Nasdaq fell 10% or more')]


def _mdd(pts):
    """pts＝[(日期, 收盤)]，回傳（最大回撤 %、高點日、高點、低點日、低點）"""
    pk = pts[0]; best = (0.0, pts[0][0], pts[0][1], pts[0][0], pts[0][1])
    for d, v in pts:
        if v > pk[1]: pk = (d, v)
        x = (v / pk[1] - 1) * 100
        if x < best[0]: best = (x, pk[0], pk[1], d, v)
    return best


def _fwd(keys, S, d):
    e = (dt.date.fromisoformat(d) + dt.timedelta(H)).isoformat(); i = bisect.bisect_right(keys, d); j = bisect.bisect_right(keys, e)
    if j >= len(keys): return None   # 還沒走完 H 天
    w = [S[k] for k in keys[i:j]]
    return (min(w) / S[d] - 1) * 100 if w else None


def build(ndq, btc, last):
    D = sorted(d for d in ndq if d <= last and ndq[d])
    if len(D) < 10000: raise RuntimeError('那斯達克歷史不夠長')
    by = {}
    for d in D: by.setdefault(int(d[:4]), []).append((d, ndq[d]))
    cy = int(D[-1][:4]); years = []
    for y in range(1972, cy + 1):
        if y not in by: continue
        m = _mdd(by[y]); years.append(dict(y=y, dd=round(m[0], 1), pk=m[1], lo=m[3]))
    full = [x for x in years if x['y'] < cy]; cur = years[-1]; v = [x['dd'] for x in full]
    yp = max(by[cy], key=lambda p: p[1])
    cur.update(now=round((ndq[D[-1]] / yp[1] - 1) * 100, 1), ypk=yp[0], ypv=round(yp[1]), last=round(ndq[D[-1]]))
    # BTC 跟著跌多少
    BK = sorted(d for d in btc if btc[d]); NK = D
    R = []
    for d in NK:
        if d < '2013-01-01' or d not in btc: continue
        n, b = _fwd(NK, ndq, d), _fwd(BK, btc, d)
        if n is not None and b is not None: R.append((d, n, b))
    if len(R) < 1000: raise RuntimeError('BTC 和那斯達克重疊的日子不夠')
    def stat(x):
        b = [r[2] for r in x]
        return dict(n=len(b), p10=round(sum(1 for q in b if q <= -10) / len(b) * 100), p20=round(sum(1 for q in b if q <= -20) / len(b) * 100), med=round(st.median(b)))
    sc = dict(H=H, since=R[0][0], until=R[-1][0], any=stat(R),
              groups=[dict(id=g, zh=z, en=e, **stat([r for r in R if lo < r[1] <= hi])) for g, lo, hi, z, e in GROUPS])
    return dict(date=D[-1], src='FRED NASDAQCOM', years=years, cur=cur, n=len(full), y0=full[0]['y'], y1=full[-1]['y'], med=round(st.median(v), 1),
                n20=sum(1 for q in v if q < -20), n30=sum(1 for q in v if q < -30), deeper=sum(1 for q in v if q < cur['dd']), sc=sc,
                note='年內最大回撤＝當年最高收盤到之後最低收盤；BTC 對照：2013 年起每一天看之後 %d 天的最深跌幅，相鄰日子重疊，只作讀值' % H)
