# -*- coding: utf-8 -*-
"""籌碼集中度回落到 6% 以下（2026-11-26 使用者看了 Murphy 一則貼文：「10/28 超過 15%……最好回落到 6% 或以下，本輪回調籌碼再分配才算完成第一步」，說「加」）。

用網站自己的集中度（chips.conc_hist，2018 起每天：現價 ±5% 內的籌碼佔供給 %）取 7 日平均，每日值很跳，7 日平均接近他用的 Glassnode 圖。
高集中＝7 日平均升破它自己 2018 年以來的第 90 百分位（相隔 30 天內不另算）；之後 180 天內第一次降到 6% 以下，算一次「回落」。
看回落那天之後 90 天：收盤比當時高的次數、漲跌中位數、期間最深跌幅中位數；對照任何一天。2026-11-26 驗算 12 次：83% 上漲、+18.7%、−7.6%；任何一天 53%、+2.8%、−13.9%。
用每日值不平均時效果弱很多（21 次、62%、+7.1%），樣本也少。只作讀值。"""
import statistics as st

LO, H, WIN = 6.0, 90, 180


def bt(rows):
    """rows＝[[日數, 收盤, 集中度 %]]（每天一筆）。回傳 ma（和 rows 對齊）、p90、回落事件、回測、現在的狀態"""
    C = [r[2] for r in rows]; P = [r[1] for r in rows]; N = len(rows)
    ma = [round(st.mean(C[max(0, i - 6):i + 1]), 2) for i in range(N)]
    p90 = sorted(ma)[int(N * .9)]
    hi, last = [], -999
    for i in range(1, N):
        if ma[i] >= p90 and ma[i - 1] < p90 and i - last > 30: hi.append(i); last = i
    def fw(i):
        if i + H >= N: return None
        w = P[i + 1:i + H + 1]; return dict(r=round((P[i + H] / P[i] - 1) * 100, 1), dd=round(min(0, (min(w) / P[i] - 1) * 100), 1))
    ev = []
    for h in hi:
        j = next((k for k in range(h + 1, min(N, h + WIN + 1)) if ma[k] <= LO), None)
        if j is None or (ev and ev[-1]['i'] == j): continue
        pk = max(range(h, j), key=lambda k: ma[k]); f = fw(j)
        ev.append(dict(i=j, dn=rows[j][0], v=ma[j], pk_dn=rows[pk][0], pk=ma[pk], r90=f and f['r'], dd90=f and f['dd']))
    done = [e for e in ev if e['r90'] is not None]
    base = [fw(i) for i in range(N)]; base = [b for b in base if b]
    stat = lambda L_, r, d: dict(n=len(L_), up=sum(1 for x in L_ if x[r] > 0), med=round(st.median(x[r] for x in L_), 1), dd=round(st.median(x[d] for x in L_), 1)) if L_ else None
    # 現在：最近一次升破高檔以來的最高點、有沒有降到 6% 以下過
    h0 = hi[-1] if hi else None; cur = None
    if h0 is not None and N - 1 - h0 <= WIN:
        pk = max(range(h0, N), key=lambda k: ma[k]); j = next((k for k in range(h0 + 1, N) if ma[k] <= LO), None)
        cur = dict(pk_dn=rows[pk][0], pk=ma[pk], below_dn=rows[j][0] if j is not None else None, days=N - 1 - pk)
    for e in ev: e.pop('i')
    return dict(ma=ma, p90=round(p90, 1), lo=LO, h=H, ev=ev, bt=stat(done, 'r90', 'dd90'), base=stat(base, 'r', 'dd'), now=ma[-1], cur=cur)
