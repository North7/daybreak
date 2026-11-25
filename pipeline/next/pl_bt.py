# -*- coding: utf-8 -*-
"""冪律倍數的回測（2026-11-25，使用者：「給出可以指導交易的觀點，不是數據機器人」）。
倍數＝價格 ÷ 冪律合理價；合理價每天只用當天以前的價格擬合（cycle.powerlaw.rows，無前視），所以這個回測沒有偷看未來。
看「倍數在門檻以下的日子」買進：一年後漲跌、一年內最多再跌多少；連續的日子併成一輪（相隔 180 天以上才算新的一輪）。"""
import bisect

TH = 0.45   # 門檻：歷次熊底倍數 0.24–0.48，取 0.45（2012 年以來約 12% 的日子在這以下）


def bt(L, th=TH):
    pl = L['cycle']['powerlaw']; R = [(r[0], 10 ** r[1]) for r in pl['rows']]
    S = L['chips']['stress']['rows']; ds = [r[0] for r in S]; px = [r[1] for r in S]
    def at(d):
        i = bisect.bisect_left(ds, d); return i if i < len(ds) else None
    rows, eps, last = [], [], None
    for d, r in R:
        if r > th: continue
        if last is None or d - last > 180: eps.append(d)
        last = d
        i, j = at(d), at(d + 365)
        if i is None or j is None or d + 365 > ds[-1]: continue
        w = px[i:j + 1]; rows.append(((px[j] / px[i] - 1) * 100, (min(w) / px[i] - 1) * 100))
    if not rows: return None
    y = sorted(a for a, _ in rows); dd = sorted(b for _, b in rows)
    cur = eps[-1] if eps and R[-1][1] <= th else None   # 這一輪第一次跌進門檻那天
    ci = at(cur) if cur else None
    below = round(sum(1 for _, r in R if r <= R[-1][1]) / len(R) * 100)
    return dict(th=th, n=len(rows), up=sum(1 for a in y if a > 0), med=round(y[len(y) // 2]), worst=round(dd[0]), dmed=round(dd[len(dd) // 2]),
                eps=len(eps) - (1 if cur else 0), years=[__import__('datetime').date.fromordinal(719163 + d).year for d in (eps[:-1] if cur else eps)], cur=cur, cur_chg=None if ci is None else round((px[-1] / px[ci] - 1) * 100), cheaper=below)
