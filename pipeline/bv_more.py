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
6 獲利供給：全體 vs 扣掉十年老幣（2026-11-19 使用者看了白仙女〈浮盈籌碼佔比，剔除休眠超過 10 年的幣〉的研究後要求）：
  全體＝supply_in_profit ÷ circulating_supply；扣掉＝（獲利供給 − 10 年以上的幣裡在獲利的）÷（流通量 − 10 年以上的幣），各取 7 日平均。
  10 年以上的幣 2019 年才開始有，成本極低、幾乎永遠在獲利，不扣的話熊底一輪比一輪高；扣掉之後反過來一輪比一輪低，沒有一條固定的線能跨輪通用。
7 Hash Ribbons 的線和原版買點（2026-11-19 使用者傳 Capriole 那張 TradingView 圖：「可以做出這種線嗎？提示買入時間」→ 看過回測後「做，照實標」）：
  算力（hashrate，EH/s）的 30 日、60 日均線；30 日跌到 60 日下面是投降期。原版買點：投降結束（30 日回到 60 日上面）之後，價格 10 日均線第一次站上 20 日均線那天。
  只算持續 14 天以上的投降（短的來回太多）。回測照實存：2021 年以前和以後分開，加上同期隨便一天買進的對照。
5 大戶地址的持幣成本（2026-11-16 使用者看了運營回覆用的圖後要求）：餘額 100–1k、1k–10k、10k–100k 顆三層地址各自的已實現市值 ÷ 持幣量。
  Bitview 沒有現成的成本序列，自己除。依地址餘額分層、沒有做實體歸併；一個地址的餘額變了就換層，1 萬顆以上那層有不少交易所和託管機構。
8 CVDD（累計價值幣天銷毀，2026-11-24 使用者看了一篇用它找熊底的研究後說「做新卡」）：每天銷毀的幣天數 × 當天收盤價，從 2009 年累加，
  除以（2009-01-03 創世區塊起的天數 × 6,000,000）。2011 年以前的部分用常數 CVDD_PRE（價格不到 0.3 美元，影響小於百萬分之一）。
  和外部公開數值驗算：2026-11-22 差 0.4%。6,000,000 這個常數是原作者事後調的（讓歷次低點剛好碰到線），所以「從沒跌破」有一部分是調出來的，網站照實寫。
9 長期持有者虧損比例：扣掉十年老幣（2026-11-25 使用者看了一張「扣掉持有 10 年以上的幣」的長期持有者虧損圖後說「加，附上口徑說明」）：
  不扣＝lth_supply_in_loss ÷ lth_supply；扣掉＝（長期持有者虧損供給 − 10 年以上的幣裡在虧損的）÷（長期持有者供給 − 10 年以上的幣），每日值。
  扣掉的那一堆 2019 年才開始有、一輪比一輪多、又幾乎永遠在獲利，所以扣掉版本會一輪比一輪被墊高。對照：每個時點都扣同一批幣
  （vintage 2009–2012：最後一次移動在 2012 年以前、到那天還沒動的幣；2014 年起價格都高於它們的成本，全部在獲利），存在 fix，網站拿來寫口徑說明。
10 VDD 倍數（2026-11-25 使用者傳了一張 Checkonchain「Value Days Destroyed Multiple」加註「底背离」的圖，看過回測後說「加成新卡」）：
  VDD＝每天銷毀的幣天數 × 當天收盤；倍數＝30 日平均 ÷ 365 日平均。和 Checkonchain 的數值比，近年差 4% 上下、早年差到五成（他的幣天數來源不同），
  熱度分區照他的 2.9／1.4／0.75。底背離：收盤在 60 日低點 3% 以內、比 60 天前跌 10% 以上、倍數是 60 天前的 2 倍以上（嚴格版）或 1.5 倍以上（放寬版），
  前後 60 天內只算一次。嚴格版只有 2015-01、2018-12、2022-11 三次，都在熊底；放寬版一年後的漲跌和隨便一天差不多，照實寫。
11 長期持有者認賠退潮（2026-11-26 長文 session 轉告使用者「整理成需求，給產品」：讓讀者自己追「退了沒、像哪一次」）：
  認賠＝長期持有者已實現虧損（lth_realized_loss_sum_24h）7 日合計 ÷ 市值（收盤 × 流通量）。觸發＝這個比例 ≥0.15% 而且是一年新高；
  觸發之間隔 90 天以內算同一次，高峰取那一次裡最高的一天；退潮＝高峰之後第一次掉到高峰的 1/3 以下。套著＝高峰那天長期持有者虧損比例（不扣老幣）。
  2013 年起 8 次。分組照套著 40%：完整走完的 ≥40% 有 4 次，3 次退潮後半年內只再低 2%–9%，2014-12（40.1%）又跌了 53%；<40% 的 3 次再低 15%–52%。
  長文研究挑的 8 個日期有 3 個不同（2014-10、2025-11、2026-07，逐次挑的），網站照這裡的機械規則。只作讀值。
全部只作讀值。Bitview 改序列名稱時（https://bitview.space/api 的 What changed）整組會失敗，collect.py 只記 errors，build.py 沿用前一天的。"""
import datetime as dt, json, subprocess, time

BULK = 'https://bitview.space/api/series/bulk?series={}&index=day1&start={}'
START = 730   # day1 第 730 筆＝2011-01-01
E0 = dt.date(2009, 1, 1); EP = dt.date(1970, 1, 1)
FP = ['p95', 'p98', 'p99', 'p99_5', 'p99_9']; FPCT = [5, 2, 1, .5, .1]
PB = ['profit_over_1000', 'profit_500_to_1000', 'profit_300_to_500', 'profit_200_to_300', 'profit_100_to_200'] + ['profit_%d_to_%d' % (a, a + 10) for a in range(90, -1, -10)] + ['loss_%d_to_%d' % (a, a + 10) for a in range(0, 100, 10)]
COH = [('all', ''), ('sth', 'sth_'), ('lth', 'lth_')]
A1 = ['1y_to_18m', '18m_to_2y', '2y_to_3y', '3y_to_4y', '4y_to_5y']; A5 = ['5y_to_6y', '6y_to_7y', '7y_to_8y', '8y_to_10y', '10y_to_12y', '12y_to_15y', 'over_15y']
TIERS = ['100_to_1k', '1k_to_10k', '10k_to_100k']
OLD10 = ['age_10y_to_12y', 'age_12y_to_15y', 'age_over_15y']   # 放了 10 年以上沒動的幣（含中本聰時期的幣）
CVDD_PRE = 27260845   # 2009-01-01 到 2010-12-31 的「銷毀幣天數 × 收盤價」合計（Bitview 從第 0 天抓一次算的；bulk 只從 2011 年抓）
LOWS = [('2014-06-01', '2015-12-31'), ('2018-06-01', '2019-06-30'), ('2020-01-01', '2020-06-30'), ('2022-06-01', '2023-03-31')]   # 歷次低點所在的區間，低點取區間裡的最低收盤
NAMES = ['price_close'] + ['bedrock_unweighted_floor_' + p for p in FP] + ['bedrock_unweighted_supply_in_loss_share_threshold_' + p for p in FP] + ['supply_in_loss_share'] \
    + ['%s%s_percent_supply_share' % (pre, b) for _, pre in COH for b in PB] \
    + ['supply_density', 'supply_density_in_profit', 'supply_density_in_loss', 'sth_supply_density', 'lth_supply_density'] \
    + ['age_%s_transfer_volume_sum_24h' % a for a in A1 + A5] \
    + ['balance_%s_btc_%s' % (t, m) for t in TIERS for m in ('realized_cap', 'supply')] \
    + ['supply_in_profit', 'circulating_supply'] + ['%s_supply%s' % (a, x) for a in OLD10 for x in ('', '_in_profit')] + ['hashrate'] + ['coindays_destroyed_sum_24h'] \
    + ['lth_supply', 'lth_supply_in_loss'] + ['vintage_%d_supply' % y for y in range(2009, 2013)] + ['lth_realized_loss_sum_24h']


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


def build(last, S=None, pxc=None):
    """last＝最新一個收完的日子（YYYY-MM-DD）。回傳 dict(date, floors, pnl, dens, old)；資料不夠丟錯"""
    S = S or fetch(); N = (dt.date.fromisoformat(last) - E0).days - START + 1
    if min(len(v) for v in S.values()) < N: raise RuntimeError(f'Bitview 還沒有 {last} 的資料')
    day = lambda i: (E0 + dt.timedelta(days=START + i)).isoformat(); px = [(pxc or {}).get(day(i), v) for i, v in enumerate(S['price_close'])]   # 2026-11-17 有全站統一的收盤（collect.py 的 PXC）就用它，和其他卡同一天的收盤一致
    day = lambda i: (E0 + dt.timedelta(days=START + i)).isoformat(); ix = lambda d: (dt.date.fromisoformat(d) - E0).days - START; dnum = lambda i: (E0 - EP).days + START + i
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
    # ── 5 大戶地址的持幣成本 ──
    def cost(t):
        rc, sp = S['balance_%s_btc_realized_cap' % t], S['balance_%s_btc_supply' % t]; return [rc[i] / sp[i] if rc[i] and sp[i] and sp[i] > 1 else None for i in range(N)]
    C = [cost(t) for t in TIERS]; cm = C[1]
    if not all(c[N - 1] for c in C): raise RuntimeError('Bitview 分層成本最新一天缺值')
    y0 = ix(last[:4] + '-01-01'); runs = []; deep = None
    for i in range(y0, N):   # 今年收盤低於 1k–10k 那一層成本的日子：共幾天、分成幾段、最深的一天
        if cm[i] and px[i] < cm[i]:
            if runs and runs[-1]['_e'] == i - 1: runs[-1]['_e'] = i; runs[-1]['days'] += 1
            else: runs.append(dict(_s=i, _e=i, days=1))
            g = (px[i] / cm[i] - 1) * 100
            if deep is None or g < deep['pct']: deep = dict(d=day(i), px=R0(px[i]), cost=R0(cm[i]), pct=round(g, 1))
    for r in runs: r['start'], r['end'] = day(r.pop('_s')), day(r.pop('_e'))
    keep = set(range(max(a17, N - 400), N))   # 近 400 天每天一點（短短幾天的跌破才看得到），更早每 4 天一點
    tiers = dict(keys=TIERS, cur=[R0(c[N - 1]) for c in C], prev30=[R0(c[N - 31]) for c in C], px=R0(px[N - 1]), gap=[round((px[N - 1] / c[N - 1] - 1) * 100, 1) for c in C],
                 year=int(last[:4]), below_days=sum(r['days'] for r in runs), runs=runs, longest=max(runs, key=lambda r: r['days']) if runs else None, deep=deep,
                 rows=[[dnum(i), R0(px[i])] + [R0(c[i]) for c in C] for i in samp(a17, keep) if all(c[i] for c in C)])
    # ── 6 獲利供給：全體 vs 扣掉十年老幣 ──
    sip, cs = S['supply_in_profit'], S['circulating_supply']
    oq = lambda i, x: sum((S['%s_supply%s' % (a, x)][i] or 0) for a in OLD10)
    a12 = ix('2012-01-01'); raw, exr, osh = [None] * N, [None] * N, [None] * N
    for i in range(a12 - 7, N):
        if not sip[i] or not cs[i]: continue
        o_, op_ = oq(i, ''), oq(i, '_in_profit'); raw[i] = sip[i] / cs[i] * 100; exr[i] = (sip[i] - op_) / (cs[i] - o_) * 100; osh[i] = o_ / cs[i] * 100
    def m7(v, i):
        w = v[i - 6:i + 1]; return None if None in w else sum(w) / 7
    r7 = [m7(raw, i) if i >= a12 else None for i in range(N)]; e7 = [m7(exr, i) if i >= a12 else None for i in range(N)]
    if None in (r7[N - 1], e7[N - 1], r7[N - 31], e7[N - 31]): raise RuntimeError('Bitview 獲利供給最新一天缺值')
    top = max(range(ix('2024-01-01'), N), key=lambda q: px[q] or 0)   # 這一輪的頂部（2024 年以來最高收盤），之後的最低點算「這一輪」
    def low(a, b, v):
        k = min((q for q in range(ix(a), min(N, ix(b) + 1)) if v[q] is not None), key=lambda q: v[q]); return dict(d=day(k), dn=dnum(k), v=R2(v[k]))
    pw = [(a, b) for a, b in LOWS] + [(day(top), last)]
    plows = [dict(ex=low(a, b, e7), raw=low(a, b, r7)) for a, b in pw]
    cr, arm = [], True   # 扣掉老幣的 7 日平均第一次跌破 45%（回到 60% 以上才算新的一段）：之後一年的漲跌、一年內最深再跌多少
    for i in range(a12, N):
        if e7[i] is None: continue
        if arm and e7[i] < 45:
            w = [x for x in px[i:min(N, i + 366)] if x]; cr.append(dict(d=day(i), px=R0(px[i]), worst=round((min(w) / px[i] - 1) * 100), y1=round((px[i + 365] / px[i] - 1) * 100) if i + 365 < N and px[i + 365] else None)); arm = False
        if e7[i] > 60: arm = True
    ok = [x for x in e7[a12:] if x is not None]
    psx = dict(ex=R2(e7[N - 1]), raw=R2(r7[N - 1]), ex30=R2(e7[N - 31]), raw30=R2(r7[N - 31]), old=R2(osh[N - 1]), old_first=next(day(i) for i in range(a12, N) if osh[i]), pct=round(sum(1 for x in ok if x < e7[N - 1]) / len(ok) * 100, 1), since='2012-01-01',
               lows=plows, cross45=cr, rows=[[dnum(i), R2(r7[i]), R2(e7[i]), R2(osh[i]), R0(px[i])] for i in samp(a12, [ix(q[k]['d']) for q in plows for k in ('ex', 'raw')]) if e7[i] is not None])
    # ── 9 長期持有者虧損比例：扣掉十年老幣 ──
    ls_, ll_ = S['lth_supply'], S['lth_supply_in_loss']; vq = lambda i: sum((S['vintage_%d_supply' % y][i] or 0) for y in range(2009, 2013))
    a14 = ix('2014-06-01'); lr, lx, lf = [None] * N, [None] * N, [None] * N
    for i in range(a14, N):
        if not ls_[i] or ll_[i] is None: continue
        o_ = oq(i, ''); ol = o_ - oq(i, '_in_profit'); lr[i] = ll_[i] / ls_[i] * 100; lx[i] = (ll_[i] - ol) / (ls_[i] - o_) * 100; lf[i] = ll_[i] / (ls_[i] - vq(i)) * 100
    if None in (lr[N - 1], lx[N - 1], lx[N - 31]): raise RuntimeError('Bitview 長期持有者虧損最新一天缺值')
    def hi(a, b, v):
        k = max((q for q in range(a, min(N, b + 1)) if v[q] is not None), key=lambda q: v[q]); return dict(d=day(k), dn=dnum(k), v=R2(v[k]))
    lw_ = [(ix(a), ix(b)) for a, b in [('2014-06-01', '2016-06-01'), ('2018-06-01', '2019-12-31'), ('2022-06-01', '2023-06-01')]] + [(top, N - 1)]   # 歷輪熊底那段的最高點，最後一段是這一輪（2024 年以來的頂部之後）
    lpk = [dict(ex=hi(a, b, lx), raw=hi(a, b, lr), fix=hi(a, b, lf)) for a, b in lw_]
    lthx = dict(ex=R2(lx[N - 1]), raw=R2(lr[N - 1]), fix=R2(lf[N - 1]), ex30=R2(lx[N - 31]), coins=R0(ll_[N - 1]), old=R0(oq(N - 1, '')), old_first=next(day(i) for i in range(a14, N) if oq(i, '')), since='2014-06-01',
                peaks=lpk, rows=[[dnum(i), R0(px[i]), R2(lr[i]), R2(lx[i])] for i in samp(a14, [ix(q[k]['d']) for q in lpk for k in ('ex', 'raw')]) if lx[i] is not None and px[i]])
    # ── 7 Hash Ribbons ──
    hv = [(v / 1e18 if v else None) for v in S['hashrate'][:N]]
    def sm(v, i, n):
        w = v[i - n + 1:i + 1] if i >= n - 1 else None; return None if not w or None in w else sum(w) / n
    h30 = [sm(hv, i, 30) for i in range(N)]; h60 = [sm(hv, i, 60) for i in range(N)]; p10 = [sm(px, i, 10) for i in range(N)]; p20 = [sm(px, i, 20) for i in range(N)]
    if None in (h30[N - 1], h60[N - 1]): raise RuntimeError('Bitview 算力最新一天缺值')
    capd = [h30[i] is not None and h60[i] is not None and h30[i] < h60[i] for i in range(N)]
    eps, i = [], a12
    while i < N:
        if capd[i]:
            s0 = i
            while i < N and capd[i]: i += 1
            eps.append((s0, i - 1))
        else: i += 1
    fw = lambda k, h: round((px[k + h] / px[k] - 1) * 100) if k + h < N and px[k + h] else None
    buys = []
    for s0, e0 in eps:
        if e0 - s0 + 1 < 14: continue
        k = e0 + 1
        while k < N and not capd[k] and not (p10[k] and p20[k] and p10[k] > p20[k]): k += 1
        if k < N and not capd[k]: buys.append(dict(d=day(k), dn=dnum(k), px=R0(px[k]), cap0=day(s0), cap1=day(e0), days=e0 - s0 + 1, r90=fw(k, 90), r180=fw(k, 180), r365=fw(k, 365)))
    def bt(L):
        v = sorted(b['r365'] for b in L if b['r365'] is not None); return dict(n=len(v), up=sum(1 for x in v if x > 0), med=v[len(v) // 2] if v else None)
    def anyd(a):
        v = sorted(fw(k, 365) for k in range(a, N) if fw(k, 365) is not None); return dict(n=len(v), up=round(sum(1 for x in v if x > 0) / len(v) * 100), med=v[len(v) // 2])
    run = 0
    while run < N and capd[N - 1 - run] == capd[N - 1]: run += 1
    R3 = lambda v: None if v is None else round(v, 3 if v < 10 else 1)
    hrib = dict(m30=R3(h30[N - 1]), m60=R3(h60[N - 1]), ratio=round(h30[N - 1] / h60[N - 1], 4), cap=capd[N - 1], run=run, min_eps=14, since=day(a12),
                buys=buys, pre=bt([b for b in buys if b['d'] < '2021']), post=bt([b for b in buys if b['d'] >= '2021']), base_post=anyd(ix('2021-01-01')), base_all=anyd(a12),
                spans=[[dnum(a), dnum(b)] for a, b in eps],
                rows=[[dnum(k), R3(h30[k]), R3(h60[k]), round(h30[k] / h60[k], 4), R0(px[k])] for k in samp(a12, set(range(N - 1100, N)) | {b['dn'] - dnum(0) for b in buys}) if h30[k] and h60[k]])
    # ── 8 CVDD ──
    cdd, bpx = S['coindays_destroyed_sum_24h'][:N], S['price_close'][:N]; cum = CVDD_PRE; cv = [None] * N
    for i in range(N):
        cum += (cdd[i] or 0) * (bpx[i] or 0); cv[i] = cum / (((dt.date.fromisoformat(day(i)) - dt.date(2009, 1, 3)).days + 1) * 6e6)
    pm = [(px[i] / cv[i] - 1) * 100 if px[i] and cv[i] else None for i in range(N)]
    if pm[N - 1] is None: raise RuntimeError('CVDD 最新一天缺值')
    a14 = ix('2014-01-01')
    def plow(a, b):
        k = min((q for q in range(max(a14, ix(a)), min(N, ix(b) + 1)) if pm[q] is not None), key=lambda q: pm[q]); return dict(d=day(k), dn=dnum(k), px=R0(px[k]), cv=R0(cv[k]), prem=R2(pm[k]))
    clows = [plow(a, b) for a, b in LOWS]; cnow = plow(day(top), last)   # 歷次熊底那段離 CVDD 最近的一天；這一輪＝2024 年以來的頂部之後
    fwd = lambda k, h: (px[k + h] / px[k] - 1) * 100 if k + h < N and px[k + h] else None
    ep, arm = [], True   # 每一段第一次高出不到 25%（回到 60% 以上才算新的一段）：之後一年內最深再跌多少、一年後漲跌
    for i in range(a14, N):
        if pm[i] is None: continue
        if arm and pm[i] < 25:
            w = [x for x in px[i:min(N, i + 366)] if x]; k2 = i + w.index(min(w)); ep.append(dict(d=day(i), dn=dnum(i), px=R0(px[i]), prem=R2(pm[i]), worst=round((min(w) / px[i] - 1) * 100), wd=day(k2), y1=None if fwd(i, 365) is None else round(fwd(i, 365)))); arm = False
        if pm[i] > 60: arm = True
    def bstat(sel, h):
        v = sorted(fwd(k, h) for k in range(a14, N) if pm[k] is not None and sel(pm[k]) and fwd(k, h) is not None); return dict(n=len(v), up=round(sum(1 for x in v if x > 0) / len(v) * 100) if v else None, med=round(v[len(v) // 2]) if v else None)
    pl = sorted(w['prem'] for w in clows); pmed = (pl[1] + pl[2]) / 2
    cvdd = dict(v=R0(cv[N - 1]), px=R0(px[N - 1]), prem=R2(pm[N - 1]), prem30=R2(pm[N - 31]), v365=R0(cv[N - 366]), grow=round((cv[N - 1] / cv[N - 366] - 1) * 100, 1),
                lows=clows, now=cnow, eps=ep, low_med=round(pmed, 1), at_med=R0(cv[N - 1] * (1 + pmed / 100)), at25=R0(cv[N - 1] * 1.25),
                z25=bstat(lambda v: v < 25, 180), any180=bstat(lambda v: True, 180), since='2014-01-01',
                rows=[[dnum(i), R0(cv[i]), R0(cv[i] * 1.25), R0(px[i]), R2(pm[i]), round(px[i] / cv[i], 3)] for i in samp(a12, set(range(N - 1100, N)) | {w['dn'] - dnum(0) for w in clows + [cnow]} | {e['dn'] - dnum(0) for e in ep}) if cv[i] and pm[i] is not None])
    # ── 10 VDD 倍數 ──
    vd = [(cdd[i] or 0) * (bpx[i] or 0) for i in range(N)]; cs = [0.0]
    for v in vd: cs.append(cs[-1] + v)
    vm = [None] * N
    for i in range(364, N):
        b = (cs[i + 1] - cs[i - 364]) / 365; vm[i] = (cs[i + 1] - cs[i - 29]) / 30 / b if b else None
    if vm[N - 1] is None: raise RuntimeError('VDD 倍數最新一天缺值')
    def dv(i):   # 那一天的背離條件：收盤離 60 日低點不到 3%、比 60 天前跌 10% 以上；回傳倍數是 60 天前的幾倍（不成立回傳 None）
        if i < 424 or not px[i] or not px[i - 60] or vm[i] is None or not vm[i - 60]: return None
        w = [x for x in px[i - 59:i + 1] if x]
        return vm[i] / vm[i - 60] if px[i] <= min(w) * 1.03 and px[i] / px[i - 60] - 1 <= -0.10 else None
    def vev(k):
        ev, lst = [], -999
        for i in range(a12, N):
            r = dv(i)
            if r is not None and r >= k:
                if i - lst > 60:
                    w = [x for x in px[i:min(N, i + 366)] if x]
                    ev.append(dict(d=day(i), dn=dnum(i), px=R0(px[i]), m=round(vm[i], 3), m60=round(vm[i - 60], 3), x=round(r, 2), worst=round((min(w) / px[i] - 1) * 100),
                                   r90=None if fwd(i, 90) is None else round(fwd(i, 90)), r180=None if fwd(i, 180) is None else round(fwd(i, 180)), r365=None if fwd(i, 365) is None else round(fwd(i, 365))))
                lst = i
        return ev
    def vbt(L):
        v = sorted(e['r365'] for e in L if e['r365'] is not None); return dict(n=len(v), up=sum(1 for x in v if x > 0), med=v[len(v) // 2] if v else None)
    vs, vl = vev(2), vev(1.5); va = sorted(fwd(k, 365) for k in range(a12, N) if fwd(k, 365) is not None)
    zn = [v for v in vm[a12:] if v is not None]; rn = dv(N - 1)
    vddm = dict(v=round(vm[N - 1], 3), v30=round(vm[N - 31], 3), v60=round(vm[N - 61], 3), x60=round(vm[N - 1] / vm[N - 61], 2), px=R0(px[N - 1]), px60=R0(px[N - 61]),
                chg60=round((px[N - 1] / px[N - 61] - 1) * 100, 1), div=None if rn is None else round(rn, 2), strict=vs, loose=vl, bs=vbt(vs), bl=vbt(vl),
                base=dict(n=len(va), up=round(sum(1 for x in va if x > 0) / len(va) * 100), med=round(va[len(va) // 2])), since='2012-01-01',
                hot=round(sum(1 for v in zn if v > 2.9) / len(zn) * 100, 1), cold=round(sum(1 for v in zn if v < .75) / len(zn) * 100, 1),
                pct=round(sum(1 for v in zn if v < vm[N - 1]) / len(zn) * 100, 1),
                rows=[[dnum(i), round(vm[i], 3), R0(px[i])] for i in samp(a12, set(range(N - 1100, N)) | {ix(e['d']) for e in vl + vs}) if vm[i] is not None and px[i]])
    # ── 11 長期持有者認賠退潮 ──
    lrl, cir = S['lth_realized_loss_sum_24h'], S['circulating_supply']; rl = [None] * N
    for i in range(6, N):
        if px[i] and cir[i]: rl[i] = sum((lrl[k] or 0) for k in range(i - 6, i + 1)) / (px[i] * cir[i]) * 100
    u7m = lambda i: R0(sum((lrl[k] or 0) for k in range(i - 6, i + 1)) / 1e6)
    lsh = lambda i: ll_[i] / ls_[i] * 100 if ls_[i] and ll_[i] is not None else None
    if rl[N - 1] is None or lsh(N - 1) is None: raise RuntimeError('Bitview 長期持有者認賠最新一天缺值')
    a13 = ix('2013-01-01'); y1 = lambda i: max((rl[k] for k in range(max(6, i - 365), i) if rl[k] is not None), default=0)
    trg = [i for i in range(a13, N) if rl[i] is not None and rl[i] >= .15 and rl[i] >= y1(i)]
    eps_ = []
    for i in trg:
        if eps_ and i - eps_[-1][-1] <= 90: eps_[-1].append(i)
        else: eps_.append([i])
    def retr(pk):
        return next((j for j in range(pk + 1, N) if rl[j] is not None and rl[j] < rl[pk] / 3), None)
    def lowp(a, h):
        w = [px[k] for k in range(a, min(N, a + h + 1)) if px[k]]; return round((min(w) / px[a] - 1) * 100) if w else None
    fwd_ = lambda a, h: round((px[a + h] / px[a] - 1) * 100) if a + h < N and px[a + h] else None
    k30 = N - 30; wn = max((k for k in range(k30, N) if rl[k] is not None), key=lambda k: rl[k])   # 現在這一波：近 30 天最高的那天
    ev11 = []
    for e in eps_:
        pk = max(e, key=lambda k: rl[k])
        if pk >= k30: continue   # 高峰在近 30 天內的算「現在這一波」，不放進歷次
        r = retr(pk); sh = lsh(pk)
        ev11.append(dict(d=day(pk), dn=dnum(pk), rel=round(rl[pk], 3), usd_m=u7m(pk), ls=round(sh, 1), hi=sh >= 40, start=day(e[0]),
                         ret=day(r) if r is not None else None, ret_dn=dnum(r) if r is not None else None, rdays=None if r is None else r - pk,
                         low180=None if r is None else lowp(r, 180), r90=None if r is None else fwd_(r, 90), r180=None if r is None else fwd_(r, 180),
                         full=r is not None and r + 180 < N, i=pk))
    rn = retr(wn); yb = max((k for k in range(max(6, wn - 365), wn) if rl[k] is not None), key=lambda k: rl[k])
    now11 = dict(d=day(wn), dn=dnum(wn), rel_pk=round(rl[wn], 3), usd_m=u7m(wn), rel=round(rl[N - 1], 3), usd_now=u7m(N - 1), frac=round(rl[N - 1] / rl[wn] * 100), days=N - 1 - wn,
                 ret=day(rn) if rn is not None else None, ls_pk=round(lsh(wn), 1), ls=round(lsh(N - 1), 1), y1=round(rl[yb], 3), y1_d=day(yb), is_hi=rl[wn] >= .15 and rl[wn] >= rl[yb],
                 big=rl[wn] >= .15)
    def al(pk, a, b, f):
        return [[d, f(pk + d)] for d in range(a, b + 1) if 0 <= pk + d < N and f(pk + d) is not None]
    lr_ = lambda pk: (lambda k: None if rl[k] is None else round(rl[k] / rl[pk] * 100, 1))
    pr_ = lambda pk: (lambda k: None if not px[k] else round(px[k] / px[pk], 4))
    for x_ in ev11 + [now11]:
        pk = ix(x_['d']); x_['al_l'] = al(pk, -20, 60, lr_(pk)); x_['al_p'] = al(pk, -20, 180, pr_(pk))
    for x_ in ev11: x_.pop('i')
    keep = {ix(x_['d']) for x_ in ev11 + [now11]} | {ix(x_['ret']) for x_ in ev11 + [now11] if x_['ret']} | set(range(N - 400, N))
    rows11 = []
    for i in range(a13, N, 3):   # 每 3 天取最高的一天，尖峰不會被抽樣抽掉；高峰、退潮那天和最近 400 天每天都留
        blk = [k for k in range(i, min(N, i + 3)) if rl[k] is not None and px[k]]
        if not blk: continue
        for k in sorted(set([max(blk, key=lambda q: rl[q])]) | {k for k in blk if k in keep}): rows11.append([dnum(k), round(rl[k], 3), R0(px[k])])
    lthw = dict(since='2013-01-01', th=.15, gap=90, eps=ev11, now=now11, rows=rows11)
    return dict(date=last, src='Bitview', link='https://bitview.space', n=len(NAMES), floors=floors, pnl=pnl, dens=dens, old=old, tiers=tiers, psx=psx, lthx=lthx, hrib=hrib, cvdd=cvdd, vddm=vddm, lthw=lthw,
                note='損失地板：虧損的幣佔供給的比例到歷史最糟 5%／2%／1%／0.5%／0.1% 時的價格，門檻逐日累積；賺賠分布：各賺賠幅度佔供給 %；集中度：現價 ±5% 內的幣佔供給 %；老幣移動：1 年以上、5 年以上的幣每天移動的顆數（7 日、30 日平均）；獲利供給：全體和扣掉 10 年以上的幣，在獲利的比例（7 日平均）；CVDD：累計（銷毀幣天數 × 價格）÷（創世起天數 × 600 萬）；VDD 倍數：（銷毀幣天數 × 價格）30 日均 ÷ 365 日均；只作讀值')


if __name__ == '__main__':
    import sys
    d = build(sys.argv[1]); print({k: v for k, v in d['vddm'].items() if k != 'rows'}, len(d['vddm']['rows'])); print({k: v for k, v in d['cvdd'].items() if k != 'rows'}, len(d['cvdd']['rows'])); print({k: v for k, v in d['hrib'].items() if k not in ('rows', 'spans')}, len(d['hrib']['rows'])); print({k: v for k, v in d['psx'].items() if k != 'rows'}, len(d['psx']['rows'])); print({k: v for k, v in d['tiers'].items() if k != 'rows'}, len(d['tiers']['rows'])); print(json.dumps({k: (v if k not in ('rows',) else len(v)) for k, v in d['floors'].items()}, ensure_ascii=False)); print({k: d['pnl']['all'][k] for k in ('cur', 'prev30', 'low22', 'depth', 'pct10')}); print({k: v for k, v in d['dens'].items() if k != 'rows'}, len(d['dens']['rows'])); print(d['old']['y1'], d['old']['y5'], len(d['old']['rows'])); print('bytes', len(json.dumps(d)))
