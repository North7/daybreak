#!/usr/bin/env python3
"""Bitview 的四組資料（2026-11-16 使用者看過目錄盤點後決定「四項都做」）：
損失地板、賺賠分布、籌碼集中度（改用現成序列）、老幣移動。

用 /api/series/bulk 一次帶 3 條（有重量上限），總共約 36 次請求、一分鐘上下。只留已收完的日子（日期早於今天 UTC）。
1 損失地板（bedrock_unweighted_floor_*）：價格跌到哪裡，虧損的幣佔全部供給的比例會到它自己歷史最糟的 5%／2%／1%／0.5%／0.1%。
  門檻是逐日累積的（只用到那一天為止的歷史），不是用整段歷史回頭算。未加權版：每顆幣算一次。
2 賺賠分布（profitability/*_percent_supply_share）：25 格賺賠幅度各佔多少供給，全體、短期、長期持有者各一份。
  存成「虧損的」「虧 10%／20%／30%／50% 以上的」五條累計線，加上今天、30 天前、2022 年低點那天的分組。
3 籌碼集中度（supply_density）：最後一次移動價格在當天價格 ±5% 內的幣佔供給的比例。和 bitview.conc_rows 自己從 URPD 算的平均差 0.01 個百分點。
4 老幣移動（age_*_transfer_volume_sum_24h）：放了 1 年以上、5 年以上的幣每天在鏈上移動的顆數。換錢包、交易所整理冷錢包也算，不等於賣出。
全部只作讀值。Bitview 改序列名稱時（https://bitview.space/api 的 What changed）整組會失敗，collect.py 只記 errors，build.py 沿用前一天的。"""
import datetime as dt, json, subprocess, time

BULK = 'https://bitview.space/api/series/bulk?series={}&index=day1&start={}'
START = 730   # day1 第 730 筆＝2011-01-01
E0 = dt.date(2009, 1, 1); EP = dt.date(1970, 1, 1)
FP = ['p95', 'p98', 'p99', 'p99_5', 'p99_9']; FPCT = [5, 2, 1, .5, .1]
PB = ['profit_over_1000', 'profit_500_to_1000', 'profit_300_to_500', 'profit_200_to_300', 'profit_100_to_200'] + ['profit_%d_to_%d' % (a, a + 10) for a in range(90, -1, -10)] + ['loss_%d_to_%d' % (a, a + 10) for a in range(0, 100, 10)]
COH = [('all', ''), ('sth', 'sth_'), ('lth', 'lth_')]
A1 = ['1y_to_18m', '18m_to_2y', '2y_to_3y', '3y_to_4y', '4y_to_5y']; A5 = ['5y_to_6y', '6y_to_7y', '7y_to_8y', '8y_to_10y', '10y_to_12y', '12y_to_15y', 'over_15y']
LOWS = [('2014-06-01', '2015-12-31'), ('2018-06-01', '2019-06-30'), ('2020-01-01', '2020-06-30'), ('2022-06-01', '2023-03-31')]   # 歷次低點所在的區間，低點取區間裡的最低收盤
NAMES = ['price_close'] + ['bedrock_unweighted_floor_' + p for p in FP] + ['bedrock_unweighted_supply_in_loss_share_threshold_' + p for p in FP] + ['supply_in_loss_share'] \
    + ['%s%s_percent_supply_share' % (pre, b) for _, pre in COH for b in PB] \
    + ['supply_density', 'supply_density_in_profit', 'supply_density_in_loss', 'sth_supply_density', 'lth_supply_density'] \
    + ['age_%s_transfer_volume_sum_24h' % a for a in A1 + A5]


def _curl(url):
    out = subprocess.run(['curl', '-sS', '-A', 'daybreak-pipeline', '--max-time', '90', url], capture_output=True, text=True).stdout
    return json.loads(out) if out.strip().startswith('[') else {'error': out[:160]}


def fetch(names=NAMES, n=3):
    """一次請求有重量上限（32 萬；2011 起的每日序列一條約 8 萬，每天多一點），所以一次 3 條；超重就自動少帶一條再試"""
    S = {}; i = 0
    while i < len(names):
        part = names[i:i + n]; j = _curl(BULK.format(','.join(part), START))
        if isinstance(j, dict) and 'weight_exceeded' in str(j) and n > 1: n -= 1; continue
        if not isinstance(j, list) or len(j) != len(part): raise RuntimeError(f'Bitview bulk {part[0]}…：{str(j)[:160]}')
        for nm, x in zip(part, j):
            if x.get('start') != START or not isinstance(x.get('data'), list): raise RuntimeError(f'Bitview {nm} 起點或格式不對')
            S[nm] = x['data']
        i += len(part); time.sleep(0.3)
    return S


def build(last, S=None):
    """last＝最新一個收完的日子（YYYY-MM-DD）。回傳 dict(date, floors, pnl, dens, old)；資料不夠丟錯"""
    S = S or fetch(); N = (dt.date.fromisoformat(last) - E0).days - START + 1
    if min(len(v) for v in S.values()) < N: raise RuntimeError(f'Bitview 還沒有 {last} 的資料')
    px = S['price_close']; day = lambda i: (E0 + dt.timedelta(days=START + i)).isoformat(); ix = lambda d: (dt.date.fromisoformat(d) - E0).days - START; dnum = lambda i: (E0 - EP).days + START + i
    if not px[N - 1]: raise RuntimeError('Bitview 最新一天沒有價格')
    samp = lambda a, keep=(): sorted(set(range(N - 1, a - 1, -4)) | {i for i in keep if a <= i < N})   # 每 4 天一點，從最新一天往回數（和供給分位成本線一樣）
    R0 = lambda v: None if v is None else round(v); R2 = lambda v: None if v is None else round(v, 2)
    # ── 1 損失地板 ──
    F = [S['bedrock_unweighted_floor_' + p] for p in FP]; TH = [S['bedrock_unweighted_supply_in_loss_share_threshold_' + p] for p in FP]
    cur = [F[k][N - 1] for k in range(5)]
    if not all(cur) or not all(cur[k] >= cur[k + 1] for k in range(4)): raise RuntimeError(f'Bitview 損失地板不完整或順序不對：{cur}')
    a12 = ix('2012-01-01'); ok = [i for i in range(a12, N) if F[0][i] and px[i]]
    lows = []
    for a, b in LOWS:
        i = min(range(ix(a), ix(b) + 1), key=lambda q: px[q]); lows.append(dict(d=day(i), dn=dnum(i), px=R0(px[i]), broke=sum(1 for k in range(5) if F[k][i] and px[i] < F[k][i]), floors=[R0(F[k][i]) for k in range(5)]))
    brk, lastb = [], -999
    for i in ok:
        if px[i] < F[0][i]:
            if i - lastb > 120:
                w = px[i:min(N, i + 366)]; brk.append(dict(d=day(i), px=R0(px[i]), worst=round((min(w) / px[i] - 1) * 100), y1=round((px[i + 365] / px[i] - 1) * 100) if i + 365 < N else None))
            lastb = i
    a17 = ix('2017-01-01'); below = sum(1 for i in ok if px[i] < F[0][i])
    run = 0
    while run < N and px[N - 1 - run] < F[0][N - 1 - run]: run += 1
    floors = dict(cur=[R0(v) for v in cur], pct=FPCT, thr=[R2(TH[k][N - 1]) for k in range(5)], loss=R2(S['supply_in_loss_share'][N - 1]), px=R0(px[N - 1]),
                  below=sum(1 for v in cur if px[N - 1] < v), below_days=run, below1_pct=round(below / len(ok) * 100, 1), since='2012-01-01', lows=lows, breaks=brk,
                  rows=[[dnum(i), R0(px[i])] + [R0(F[k][i]) for k in range(5)] for i in samp(a17, [ix(q['d']) for q in lows])])
    # ── 2 賺賠分布 ──
    def grp(v):   # 25 格併成 9 組：賺 100% 以上、50–100%、10–50%、0–10%；虧 0–10%、10–20%、20–30%、30–50%、50% 以上
        g = lambda keys: round(sum(v[PB.index(k)] or 0 for k in keys), 2)
        return [g(PB[:5]), g(PB[5:10]), g(PB[10:14]), g(PB[14:15]), g(PB[15:16]), g(PB[16:17]), g(PB[17:18]), g(PB[18:20]), g(PB[20:])]
    def depth(v):   # 累計：虧損的、虧 10%／20%／30%／50% 以上的
        L = [v[PB.index('loss_%d_to_%d' % (a, a + 10))] or 0 for a in range(0, 100, 10)]
        return [round(sum(L[k:]), 2) for k in (0, 1, 2, 3, 5)]
    pnl = dict(groups=['p100', 'p50', 'p10', 'p0', 'l0', 'l10', 'l20', 'l30', 'l50'], low22=lows[-1]['d'])
    for nm, pre in COH:
        V = [S['%s%s_percent_supply_share' % (pre, b)] for b in PB]; at = lambda i: [V[k][i] for k in range(25)]
        tot = sum(x or 0 for x in at(N - 1))
        if abs(tot - 100) > 1.5: raise RuntimeError(f'Bitview 賺賠分布 {nm} 合計 {tot:.1f}%，不是 100%')
        dser = [depth(at(i)) if V[14][i] is not None or V[15][i] is not None else None for i in range(N)]; a13 = ix('2013-01-01')
        pc = lambda k: round(sum(1 for i in range(a13, N) if dser[i] and dser[i][k] < dser[N - 1][k]) / max(1, sum(1 for i in range(a13, N) if dser[i])) * 100)
        pnl[nm] = dict(cur=grp(at(N - 1)), prev30=grp(at(N - 31)), low22=grp(at(ix(lows[-1]['d']))), depth=dser[N - 1], depth30=dser[N - 31], depth_low22=dser[ix(lows[-1]['d'])],
                       pct10=pc(1), pct_since='2013-01-01', rows=[[dnum(i), R0(px[i])] + dser[i] for i in samp(a17) if dser[i]])
    # ── 3 籌碼集中度 ──
    sd = S['supply_density']; a18 = ix('2018-01-01')
    dens = dict(cur=R2(sd[N - 1]), profit=R2(S['supply_density_in_profit'][N - 1]), loss=R2(S['supply_density_in_loss'][N - 1]), sth=R2(S['sth_supply_density'][N - 1]), lth=R2(S['lth_supply_density'][N - 1]),
                rows=[[day(i), R2(px[i]), R2(sd[i])] for i in range(a18, N) if sd[i] is not None and px[i]])
    if len(dens['rows']) < N - a18 - 30 or dens['rows'][-1][0] != last: raise RuntimeError('Bitview supply_density 缺太多天')
    # ── 4 老幣移動 ──
    def tot(bands): return [sum((S['age_%s_transfer_volume_sum_24h' % b][i] or 0) for b in bands) for i in range(N)]
    o5 = tot(A5); o1 = [x + y for x, y in zip(tot(A1), o5)]
    ma = lambda v, n, i: sum(v[i - n + 1:i + 1]) / n
    a16 = ix('2016-01-01')
    def one(v):
        m30 = [ma(v, 30, i) for i in range(a16, N)]; cur30 = m30[-1]; top = max(range(len(m30)), key=lambda q: m30[q])
        return dict(d1=R0(v[N - 1]), a7=R0(ma(v, 7, N - 1)), a30=R0(cur30), a30_prev=R0(m30[-31]), pct=round(sum(1 for x in m30 if x < cur30) / len(m30) * 100), med=R0(sorted(m30)[len(m30) // 2]), max=R0(m30[top]), max_d=day(a16 + top))
    old = dict(y1=one(o1), y5=one(o5), since='2016-01-01', rows=[[dnum(i), R0(px[i]), R0(ma(o1, 7, i)), R0(ma(o1, 30, i)), R0(ma(o5, 7, i)), R0(ma(o5, 30, i))] for i in samp(a16)])
    return dict(date=last, src='Bitview', link='https://bitview.space', n=len(NAMES), floors=floors, pnl=pnl, dens=dens, old=old,
                note='損失地板：虧損的幣佔供給的比例到歷史最糟 5%／2%／1%／0.5%／0.1% 時的價格，門檻逐日累積；賺賠分布：各賺賠幅度佔供給 %；集中度：現價 ±5% 內的幣佔供給 %；老幣移動：1 年以上、5 年以上的幣每天移動的顆數（7 日、30 日平均）；只作讀值')


if __name__ == '__main__':
    import sys
    d = build(sys.argv[1]); print(json.dumps({k: (v if k not in ('rows',) else len(v)) for k, v in d['floors'].items()}, ensure_ascii=False)); print({k: d['pnl']['all'][k] for k in ('cur', 'prev30', 'low22', 'depth', 'pct10')}); print({k: v for k, v in d['dens'].items() if k != 'rows'}, len(d['dens']['rows'])); print(d['old']['y1'], d['old']['y5'], len(d['old']['rows'])); print('bytes', len(json.dumps(d)))
