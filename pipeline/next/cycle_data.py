# -*- coding: utf-8 -*-
"""「週期」這一頁的資料：頭部的週期儀，加五個小問題。site_data.py 會 import。
階段色照現有網站 stg0–4：深夜 c3、入夜 c4、破曉 up、白晝 c5、黃昏 ac。"""

SG = [('深夜', 'Deep night', '底部區', 'bottom zone', 'c3'), ('入夜', 'Nightfall', '下跌', 'falling', 'c4'), ('破曉', 'Daybreak', '初升', 'early rise', 'up'), ('白晝', 'Daylight', '上升', 'rising', 'c5'), ('黃昏', 'Dusk', '過熱', 'overheated', 'ac')]
SC = [s[4] for s in SG]
HG = [(0, 'c3'), (20, 'c4'), (45, 'up'), (70, 'c5'), (90, 'ac'), (100, 'ac')]
def hcol(v):   # 照現有網站 dwCol：熱度 0/20/45/70/90 對到五個階段色，中間線性內插
    v = max(0, min(100, v))
    for i in range(len(HG) - 1):
        if v <= HG[i + 1][0]:
            f = int(round((v - HG[i][0]) / float((HG[i + 1][0] - HG[i][0]) or 1) * 10) * 10); a, b = HG[i][1], HG[i + 1][1]
            return a if f <= 0 or a == b else b if f >= 100 else 'color-mix(in srgb, var(--%s) %d%%, var(--%s))' % (b, f, a)
    return 'ac'
def gsm(v, sg):   # 高斯平滑（照現有網站 dwGs）
    import math
    K = int(math.ceil(sg * 3)); out = []
    for i in range(len(v)):
        a = w = 0.0
        for k in range(-K, K + 1):
            j = i + k
            if j < 0 or j >= len(v) or v[j] is None: continue
            q = math.exp(-k * k / (2.0 * sg * sg)); a += v[j] * q; w += q
        out.append(round(a / w, 2) if w else None)
    return out

def build(L, N, E, dn, X):
    cy = L['cycle']; o = L['onchain']; p = L['price']; tE = dn(L['meta']['bar_date'])
    ser = lambda c, **k: dict(c=c, **k)
    yr = lambda s: s[:4]
    row = lambda zh, en, v, **k: dict(zh=zh, en=en, v=v, **k)
    # ── 現在的階段 ──
    st = cy['stage']; EVN = dict(mom12='12-month momentum', mvrv1y='MVRV vs its 1-year mean', rcgrowth='Capital inflow', xs90='Exchange supply', sth='Short-term holder cost', tmm='STH cost vs true market mean')
    def evv(e):
        v = e.get('value'); u = e.get('unit') or ''
        return '—' if v is None else (('%+.1f%%' % v).replace('-', '−') if u == '%' else ('$' + format(int(v), ',') if v > 1000 else '%.2f' % v))
    STN = {'牛市': 'Bull market', '熊市': 'Bear market', '過渡': 'Transition', '過渡期': 'Transition'}
    X['stage'] = dict(k='stage', zh='市場階段', en='Market stage', hz='從 %s 起' % st['since'].replace('-', '/'), he='Since ' + st['since'], hs=dict(v=st['stage'], f='txt', ve=STN.get(st['stage'], st['stage'])),
      list=dict(rows=[row(e['label'], EVN.get(e['id'], e['label']), evv(e), ve=evv(e), col='up' if e['ok'] else 'k2', nz=('成立：' if e['ok'] else '不成立：') + e['cond'], ne='Met' if e['ok'] else 'Not met') for e in st['evidence']['items']]),
      dz='三個階段：熊市、過渡、牛市。見過投降訊號、而且收盤站上還在上升的 200 日均線，進入過渡；這樣連續 30 天，進入牛市並鎖定。下面六盞燈只是佐證，不參與判定。', de='Three stages: bear, transition, bull. A capitulation signal plus a close above a rising 200-day average starts the transition; 30 straight days of that locks in a bull market. The six lights below are supporting evidence only.')
    rg = cy['regime']
    # 照現有網站 regStages：每週分到五個階段之一。≥ +4 過熱、≤ −4 極熊、分數為負是熊；空方滿 26 週後翻多的頭 26 週是初牛，其餘是牛
    RSN = [['極熊', 'Extreme bear'], ['熊', 'Bear'], ['初牛', 'Early bull'], ['牛', 'Bull'], ['過熱', 'Overheated']]; HOT, EARLY = 4, 26
    seg = [dict(t=-10 ** 9, dir=1 if rg['rows'][0][1] >= 0 else -1, prev=0)]
    for f in rg.get('flips') or []:
        pv = seg[-1]; tt = dn(f['date']); seg.append(dict(t=tt, dir=f['dir'], prev=0 if pv['t'] < 0 else int(round((tt - pv['t']) / 7.0))))
    rrows = []; jx = 0
    for r in rg['rows']:
        while jx + 1 < len(seg) and seg[jx + 1]['t'] <= r[0]: jx += 1
        gg = seg[jx]; v = r[1]; w = (r[0] - gg['t']) / 7.0
        stg = 4 if v >= HOT else 0 if v <= -HOT else 1 if v < 0 else ((2 if (w < EARLY and gg['prev'] >= EARLY) else 3) if gg['dir'] > 0 else (2 if w >= EARLY else 3))
        rrows.append([r[0], r[1], r[2], stg])
    X['regime'] = dict(k='regime', zh='週線多空分數', en='Weekly regime score', f='s2', rows=rrows, p=2, dom=[-6, 6],
      ser=[ser(1, zh='多空分數', en='Regime score', t='bar', base=0, cc=3, cols=SC, names=RSN)], refs=[dict(v=4, col='ac', zh='過熱 ≥ +4', en='Overheated ≥ +4'), dict(v=-4, col='c3', zh='極熊 ≤ −4', en='Extreme bear ≤ −4')],
      leg=[[SC[i_], RSN[i_][0], RSN[i_][1], 'box'] for i_ in range(5)],
      dz='六個項目各自和自己的中位數比，合成 −6 到 +6 的分數。柱子的顏色是當週的階段：分數為負是熊，空方滿 26 週之後翻多的頭 26 週是初牛，之後是牛，到 +4 以上是過熱、−4 以下是極熊。', de='Six inputs, each measured against its own median, combined into a score from −6 to +6. Bars take the colour of that week\'s stage: negative is bear; the first 26 weeks after a bear run of 26 weeks or more is early bull, then bull; +4 and above is overheated, −4 and below extreme bear.')
    RGN = dict(d200=('價格 ÷ 200 日均線', 'Price ÷ 200-day MA'), mom12=('12 個月動能', '12-month momentum'), mvrv1y=('MVRV 對一年均值', 'MVRV vs 1-year mean'), rc30=('實現市值 30 日', 'Realized cap, 30-day'), xs90=('交易所供給 90 日', 'Exchange supply, 90-day'), rpl=('實現獲利 ÷ 虧損 90 日', 'Realized profit ÷ loss, 90-day'),
               sth=('價格 ÷ 短期持有者成本', 'Price ÷ STH cost'), asopr=('aSOPR 30 日', 'aSOPR, 30-day'), lnupl=('長期持有者 NUPL', 'LTH NUPL'), rup=('未實現獲利 ÷ 市值', 'Unrealized profit ÷ market cap'), pl=('冪律殘差', 'Power-law residual'), rr=('儲備風險', 'Reserve risk'), mvz=('MVRV-Z', 'MVRV-Z'))
    zbar = lambda z: dict(bar=max(0, min(100, 50 + z * 50)), mk=50, col='up' if z > 0 else 'dn')
    dw = cy['dawn']; k = dw['stage']; th = dw['th']
    hv_ = [r[1] for r in dw['rows']]; hS = gsm(hv_, 5); hC = gsm(hv_, 11); drows = [list(r[:5]) + [hS[i], hC[i]] for i, r in enumerate(dw['rows'])]
    def hat(arr, d):
        i = min(range(len(drows)), key=lambda j: abs(drows[j][0] - d)); return arr[i]
    dck = [list(c[:5]) + [hat(hC, c[0] + 15)] for c in dw['candles']]
    dvl = []
    for m in dw['marks']:
        d = dn(m['date'])
        if m['kind'] == 'top':
            near = [c for c in dck if abs(c[0] - d) < 120]; best = max(near, key=lambda c: c[2]) if near else None
            if best: dvl.append(dict(d=best[0] + 15, pa=best[2], col='ink', zh=yr(m['date']) + ' 頂', en=yr(m['date']) + ' top'))
        else: dvl.append(dict(d=d, va=min(50, hat(hS, d) or 0), col='ink', zh=yr(m['date']) + ' 底', en=yr(m['date']) + ' low'))
    X['dawn'] = dict(k='dawn', zh='晨昏指數', en='Dawn–Dusk Index', hz='熱度（0–100）', he='Heat (0–100)', f='n1', rows=[list(r_[:5]) for r_ in dw['rows']], p=2, dom=[0, 100], rng=0,
      ser=[ser(1, zh='熱度', en='Heat', t='cat', cc=3, cols=SC, w=2, names=[[s_[0] + '（' + s_[2] + '）', s_[1] + ' (' + s_[3] + ')'] for s_ in SG])],
      refs=[dict(v=th['hot'], col='ac', zh='黃昏 ≥ %d' % th['hot'], en='Dusk ≥ %d' % th['hot']), dict(v=50, col='k2'), dict(v=th['cold'], col='c3', zh='深夜 ≤ %d' % th['cold'], en='Deep night ≤ %d' % th['cold'])],
      marks=[dict(d=dn(m['date']), v=m['heat'], col='ac' if m['kind'] == 'top' else 'c3', up=1 if m['kind'] == 'top' else 0, zh='%s %s %d' % (yr(m['date']), '頂' if m['kind'] == 'top' else '底', m['heat']), en='%s %s %d' % (yr(m['date']), 'top' if m['kind'] == 'top' else 'low', m['heat'])) for m in dw['marks']],
      leg=[[s_[4], s_[0] + '（' + s_[2] + '）', s_[1] + ' (' + s_[3] + ')', 'line'] for s_ in SG],
      dz='把一輪週期當成一天。熱度是五項估值和過去四年比的百分位平均；方向看四項趨勢，兩個合起來分成五個階段。下格的熱度線和上格的價格線都用當時那個階段的顏色：深夜（底部區）、入夜（下跌）、破曉（初升）、白晝（上升）、黃昏（過熱）。圓圈是歷次週期的頂和底。', de='One cycle as one day. Heat is the average 4-year percentile of five valuation measures; direction comes from four trend measures, and together they give five stages. The heat line below and the price line above both take the colour of the stage at the time: deep night (bottom zone), nightfall (falling), daybreak (early rise), daylight (rising), dusk (overheated). Circles mark past cycle tops and bottoms.')
    comp = [row(RGN[c['key']][0], RGN[c['key']][1], c['pct'], f='n0', bar=c['pct'], mk=th['hot'], col=hcol(c['pct']), nz='熱度來源 · 四年百分位', ne='Heat input · 4-year percentile') for c in dw['heat_c']] + \
           [row(RGN[c['key']][0], RGN[c['key']][1], c['z'], f='s2', nz='方向來源', ne='Trend input', **zbar(c['z'])) for c in dw['trend_c']]
    X['dawnc'] = dict(k='dawnc', zh='晨昏指數的組成', en='What the Dawn–Dusk Index is made of', hz='熱度', he='Heat', hs=dict(v=dw['heat'], f='n1'), list=dict(rows=comp),
      dz='五項熱度來源的四年百分位，平均就是熱度；直線是黃昏的門檻 %d。四項方向來源的平均決定多空，直線是零。' % th['hot'], de='The five heat inputs as 4-year percentiles; their average is the heat, and the tick marks the dusk threshold at %d. The four trend inputs set the direction; their tick is zero.' % th['hot'])
    X['regc'] = dict(k='regc', zh='週線多空分數的組成', en='What the regime score is made of', hz='分數', he='Score', hs=dict(v=rg['value'], f='s2'),
      list=dict(rows=[row(RGN[c['key']][0], RGN[c['key']][1], c['val'], f='s2', bar=max(0, min(100, 50 + c['val'] * 50)), mk=50, col='up' if c['val'] >= .15 else 'dn' if c['val'] <= -.15 else 'k2') for c in rg['comps']]), dz='六個項目各自的分數，範圍 −1 到 +1，直線是零。+0.15 以上算偏多（綠）、−0.15 以下算偏空（紅），中間是持平（灰）。加總就是多空分數。', de='Each of the six inputs scored from −1 to +1, with the tick at zero. At +0.15 or more an input counts as bullish (green), at −0.15 or less bearish (red), in between flat (grey). Their sum is the regime score.')
    # ── 估值冷熱 ──
    hn = o['hnupl']
    X['hnupl'] = dict(k='hnupl', zh='長短期持有者 NUPL', en='Long- and short-term holder NUPL', hz='長期持有者 NUPL', he='LTH NUPL', f='n3', rows=hn['rows'], p=1, hero=1,
      ser=[ser(3, zh='短期持有者 NUPL', en='STH NUPL', col='ac', w=1, op=.7), ser(2, zh='長期持有者 NUPL', en='LTH NUPL', col='c3', w=1.9)],
      zones=[dict(lo=None, hi=0, col='c3', zh='低於 0：整體虧損', en='Below 0: at a loss'), dict(lo=0, hi=.25, col='c4', zh='0–0.25', en='0–0.25'), dict(lo=.25, hi=.5, col='up', zh='0.25–0.5', en='0.25–0.5'), dict(lo=.5, hi=.75, col='c5', zh='0.5–0.75', en='0.5–0.75'), dict(lo=.75, hi=None, col='ac', zh='高於 0.75：過熱', en='Above 0.75: overheated')],
      marks=[dict(d=dn(t['date']), v=t['value'], col='ac', up=1, zh='%s %.2f' % (yr(t['date']), t['value']), en='%s %.2f' % (yr(t['date']), t['value'])) for t in hn['tops']] + [dict(d=dn(t['date']), v=t['value'], col='c3', up=0, zh='%s %.2f' % (yr(t['date']), t['value']), en='%s %.2f' % (yr(t['date']), t['value'])) for t in hn['bottoms']],
      dz='NUPL 是帳面損益佔市值的比例。底色是長期持有者 NUPL 的五個區間，由冷到熱；細的橘線是短期持有者，在零的上面還是下面代表最近買的人賺還是賠。', de='NUPL is paper profit or loss as a share of market cap. The shading marks five bands of long-term holder NUPL, cold to hot; the thin orange line is short-term holders, above or below zero.')
    rr = o['rrisk']
    X['rrisk'] = dict(k='rrisk', zh='儲備風險', en='Reserve risk', f='n5', rows=rr['rows'], p=1, log=1, hero=2,
      ser=[ser(3, zh='近 4 年最低 10%', en='4-year bottom 10%', col='c4', dash='4 3', w=1), ser(4, zh='近 4 年最高 10%', en='4-year top 10%', col='c5', dash='4 3', w=1), ser(2, zh='儲備風險', en='Reserve risk', col='c3', w=1.8)],
      spans=[dict(a=dn(e['start']), b=dn(e['end']), col='c4', op=.18) for e in rr['eps']], leg=[['c4', '在低檔區的期間', 'Time in the low zone', 'box']],
      dz='價格相對長期持有者的信心。數值低代表價格便宜、而持有者不願意賣。青色區塊是歷次落在近四年最低一成的期間。', de='Price relative to long-term holder conviction. Low readings mean price is cheap while holders refuse to sell. Cyan bands mark past stays in the bottom tenth of the last four years.')
    p6 = cy['p6']; hot = lambda v: 'ac' if v >= 80 else 'c5'
    X['p6'] = dict(k='p6', zh='頂部三指標', en='Top three indicators', hz='進入頂部區的有幾個', he='How many are in the top zone', hs=dict(v=sum(1 for v in p6.values() if v >= 80), f='n0'),
      list=dict(rows=[row('MVRV Z', 'MVRV Z', p6['mvrv_z'], f='n0', bar=p6['mvrv_z'], mk=80, bc='ac', nz='四年百分位', ne='4-year percentile'), row('NUPL', 'NUPL', p6['nupl'], f='n0', bar=p6['nupl'], mk=80, bc='ac', nz='四年百分位', ne='4-year percentile'),
                      row('Puell 倍數', 'Puell multiple', p6['puell'], f='n0', bar=p6['puell'], mk=80, bc='ac', nz='四年百分位', ne='4-year percentile')]),
      dz='三個指標各自在過去四年的百分位，直線是 80。任兩個到 80 以上算進入頂部區。只作讀值。', de='Each indicator as a percentile of the past four years; the tick is 80. Any two at 80 or above count as the top zone. Reading only.')
    vz = o['viz']
    def vmode(key, zh, en, f, rz, re_, col='c3'):
        v = vz[key]; return dict(mz=zh, me=en, rows=v['rows'], f=f, ser=[ser(1, zh=zh, en=en, col=col, w=1.6)], refs=[dict(v=v['ref']['y'], col='dn', zh=rz, en=re_)] if v.get('ref') else [])
    X['p6v'] = dict(k='p6v', zh='頂部三指標的走勢', en='Top three indicators over time', dz='近一年的原始數值。紅色虛線是各自四年來的第 80 百分位。', de='Raw values over the past year. The red dashed line is each one\'s 80th percentile of the last four years.',
      modes=[vmode('mvrv-zscore', 'MVRV Z', 'MVRV Z', 'n3', '四年第 80 百分位', '80th percentile'), vmode('nupl', 'NUPL', 'NUPL', 'n3', '四年第 80 百分位', '80th percentile'), vmode('puell-multiple', 'Puell 倍數', 'Puell multiple', 'n3', '四年第 80 百分位', '80th percentile', 'c5')])
    pl = cy['powerlaw']; bb = pl['bottom_band']
    import math
    g0 = dn('2009-01-03')
    def pfit(P):
        xs = [math.log10(dn(q[0]) - g0) for q in P]; ys = [math.log10(q[1]) for q in P]; n = float(len(xs)); mx = sum(xs) / n; my = sum(ys) / n
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs); return my - b * mx, b
    PU = pfit(pl['tops']); PLo = pfit(pl['bottoms']); pup = lambda t: PU[0] + PU[1] * math.log10(t - g0); plo = lambda t: PLo[0] + PLo[1] * math.log10(t - g0)
    pxm = dict((r[0], r[1]) for r in L['chips']['stress']['rows']); plr = []
    for r in pl['rows']:
        px_ = pxm.get(r[0])
        if not px_: continue
        pos = max(0.0, min(100.0, (r[1] - plo(r[0])) / (pup(r[0]) - plo(r[0])) * 100)); fair = px_ / 10 ** r[1]
        plr.append([r[0], px_, round(pos, 1), round(fair), round(fair * 10 ** pup(r[0])), round(fair * 10 ** plo(r[0])), 0 if pos < 15 else 1 if pos < 35 else 2 if pos < 55 else 3 if pos < 75 else 4, round(10 ** r[1], 4)])
    PLN = [['底部區', 'Bottom zone'], ['偏低', 'Low'], ['中段', 'Middle'], ['偏高', 'High'], ['頂部區', 'Top zone']]; PCUT = [0, 15, 35, 55, 75, 100]
    fairl = dict(c=3, zh='冪律合理價', en='Power-law fair value', col='k2', dash='3 3')
    X['pl'] = dict(k='pl', zh='冪律：通道位置與倍數', en='Power law: channel position and multiple',
      modes=[dict(mz='通道位置', me='Channel position', rows=plr, p=1, f='p1', tf='lin', dom=[-4, 104], ax=[100, 50, 0],
                  ser=[ser(2, zh='通道位置', en='Channel position', t='cat', cc=6, cols=SC, w=2, names=PLN)], zones=[dict(lo=PCUT[i_], hi=PCUT[i_ + 1], col=SC[i_]) for i_ in range(5)],
                  top=[dict(c=4, zh='通道頂部線', en='Channel top', col='dn', dash='5 4'), fairl, dict(c=5, zh='通道底部線', en='Channel bottom', col='c3', dash='5 4')],
                  leg=[[SC[i_], PLN[i_][0] + ' %d–%d%%' % (PCUT[i_], PCUT[i_ + 1]), PLN[i_][1] + ' %d–%d%%' % (PCUT[i_], PCUT[i_ + 1]), 'box'] for i_ in range(5)]),
             dict(mz='倍數', me='Multiple', rows=plr, p=1, f='x2', log=1, ser=[ser(7, zh='價格 ÷ 冪律合理價', en='Price ÷ power-law fair value', col='ac', w=1.7)], refs=[dict(v=1, col='k2', zh='1.0 合理價', en='1.0 fair value')], top=[fairl],
                  zones=[dict(lo=bb[0], hi=bb[1], col='c3', zh='在歷次底部的範圍內', en='Inside the range of past bottoms', nz='歷次底部範圍', ne='the range of past bottoms')],
                  marks=[dict(d=dn(t[0]), v=t[1], col='dn' if t[1] >= 1 else 'c3', up=1 if t[1] >= 1 else 0, zh='%s %.2f×' % (yr(t[0]), t[1]), en='%s %.2f×' % (yr(t[0]), t[1])) for t in pl['tops'] + pl['bottoms']],
                  leg=[['c3', '歷次底部的範圍 %.2f–%.2f×' % (bb[0], bb[1]), 'Range of past bottoms %.2f–%.2f×' % (bb[0], bb[1]), 'box']])],
      dz='價格長期沿著一條冪律趨勢走，這條趨勢當成合理價。通道位置：0%% 是歷次底部的連線、100%% 是逐輪下降的頂部連線，線的顏色依五段切換。倍數：價格除以合理價，歷次底部落在 %.2f 到 %.2f 倍之間。' % (bb[0], bb[1]), de='Price has followed a power-law trend over the long run; that trend is taken as fair value. Channel position: 0%% is the line through past bottoms, 100%% the falling line through past tops, and the line changes colour across five bands. Multiple: price divided by fair value; past bottoms fell between %.2f× and %.2f×.' % (bb[0], bb[1]))
    # ── 頂部訊號 ──
    p20 = cy['p20']
    X['p20'] = dict(k='p20', zh='MVRV ÷ 前一輪高點', en='MVRV ÷ prior-cycle peak', f='n3', rows=p20['rows'], ser=[ser(1, zh='MVRV ÷ 前高', en='MVRV ÷ prior peak', col='c3', w=1.7)],
      refs=[dict(v=.75, col='dn', zh='0.75：第一個鏈上賣點（約 $%s）' % format(p20['k075'], ','), en='0.75: first on-chain sell (about $%s)' % format(p20['k075'], ',')), dict(v=.8, col='dn', zh='0.80', en='0.80')],
      marks=[dict(d=r_[0], v=r_[1], col='dn', up=1, zh='2025 頂 %.2f' % r_[1], en='2025 top %.2f' % r_[1]) for r_ in [min(p20['rows'], key=lambda q_: abs(q_[0] - dn('2025-10-06')))] if abs(r_[0] - dn('2025-10-06')) <= 7],
      zones=[dict(lo=.75, hi=None, col='dn', zh='在賣點以上', en='Above the sell line', nz='0.75 賣點', ne='the 0.75 sell line')],
      dz='現在的 MVRV 除以上一輪的最高 MVRV。連五天站上 0.75 是出場框架的第一個鏈上賣點，0.80 是第二個。', de='Today\'s MVRV divided by the previous cycle\'s peak MVRV. Five straight days above 0.75 is the exit plan\'s first on-chain sell; 0.80 is the second.')
    tr = o['top_radar']; RN = {'lth-mvrv-zscore': ('長期持有者 MVRV Z', 'LTH MVRV Z', 'n3'), 'supply-in-profit-pct': ('獲利供給比例', 'Supply in profit', 'p1'), 'lth-net-position-change-30d-btc': ('長期持有者 30 日淨部位', 'LTH 30-day net position', 'btc')}
    fx = lambda f, v: ('%.2f' % v) if f == 'n3' else ('%.1f%%' % v) if f == 'p1' else (('%+.1f 萬顆' % (v / 1e4)).replace('-', '−'))
    def rtone(k2, x):
        v = x['value']
        if k2 == 'lth-mvrv-zscore': return 'dn' if x['pct_since_2022_11'] >= 90 else None
        if k2 == 'supply-in-profit-pct': return 'dn' if v >= 95 else 'up' if v <= 50 else None
        return 'up' if v > 0 else 'dn' if v <= x['p10_since_2022_11'] else None
    X['radar'] = dict(k='radar', zh='頂部雷達', en='Top radar', hz='三項裡最高的百分位', he='Highest percentile of the three', hs=dict(v=max(x['pct_since_2022_11'] for x in tr.values()), f='n0'),
      list=dict(rows=[row(RN[k2][0], RN[k2][1], x['value'], f=RN[k2][2], bar=x['pct_since_2022_11'], bc='ink', col=rtone(k2, x), nz='2025 頂部附近的極值 ' + fx(RN[k2][2], x['extreme_near_2025_top']), ne='Extreme near the 2025 top ' + fx(RN[k2][2], x['extreme_near_2025_top']).replace(' 萬顆', '0K BTC')) for k2, x in tr.items()]),
      dz='三個在 2025 年頂部附近出現極值的指標。橫條是 2022 年 11 月以來的百分位。', de='Three measures that hit extremes near the 2025 top. Bars show the percentile since November 2022.')
    X['radarv'] = dict(k='radarv', zh='頂部雷達的走勢', en='Top radar over time', dz='近一年的原始數值。紅色虛線是 2025 年頂部附近的極值。', de='Raw values over the past year. The red dashed line is the extreme reached near the 2025 top.',
      modes=[vmode(k2, RN[k2][0], RN[k2][1], RN[k2][2], '2025 頂部附近的極值', 'Extreme near the 2025 top', 'c3' if k2 == 'lth-mvrv-zscore' else 'c4') for k2 in tr])
    pi = p['pi_cycle']
    X['pi'] = dict(k='pi', zh='Pi Cycle', en='Pi Cycle', hz='111 日均線 ÷（350 日均線 × 2）', he='111-day MA ÷ (350-day MA × 2)', hs=dict(v=pi, f='n3'),
      list=dict(rows=[row('現在的比值', 'Ratio now', pi, f='n3', bar=pi * 100, mk=100, bc='ac', col='dn' if pi >= 1 else 'c5' if pi >= .9 else None, nz='到 1 就是過去幾輪頂部出現的訊號', ne='A reading of 1 has marked past cycle tops')]),
      dz='111 日均線追上兩倍的 350 日均線時，過去幾輪都在頂部附近。比值離 1 越近越接近。', de='When the 111-day average catches up with twice the 350-day average, past cycles were near their top. The closer the ratio is to 1, the nearer that point.')
    tm = cy['tidemark']; tl = lambda v: 'ac' if v is not None and v >= 70 else 'c5' if v is not None and v >= 50 else 'k2'
    CE = {'鏈上估值': 'On-chain valuation', '持有者行為': 'Holder behaviour', '資金流與機構': 'Flows and institutions', '槓桿與衍生品': 'Leverage and derivatives', '情緒': 'Sentiment'}
    X['tm'] = dict(k='tm', zh='Tidemark 綜合訊號', en='Tidemark composite signal', hz='頂部訊號（0–100）', he='Top signal (0–100)', hs=dict(v=tm['top']['signal'], f='n1'),
      list=dict(rows=[row('頂部訊號', 'Top signal', tm['top']['signal'], f='n1', bar=tm['top']['signal'], mk=[50, 70], bc='ac', nz='50 進入窗口、70 警戒', ne='50 opens the window, 70 is the alert'), row('底部訊號', 'Bottom signal', tm['bottom']['signal'], f='n1', bar=tm['bottom']['signal'], mk=[50, 70], bc='ac', nz='50 進入底部區', ne='50 opens the bottom zone'),
                      row('熱度', 'Heat', tm['top']['heat'], f='n1', bar=tm['top']['heat'], mk=[40, 65], bc='ac'), row('冷度', 'Cold', tm['bottom']['cold'], f='n1', bar=tm['bottom']['cold'], bc='ac')] +
                     [row(c[0], CE.get(c[0], c[0]), c[1], f='n1', bar=c[1] if c[1] is not None else None, bc='ac' if (c[1] or 0) >= 80 else 'ink', nz='分項' if c[1] is not None else '這一項今天沒有資料', ne='Category' if c[1] is not None else 'No data today') for c in tm['cats']]),
      dz='第三方的綜合訊號，把鏈上估值、資金流、槓桿、情緒等分項合成頂部和底部兩個 0–100 的分數。', de='A third-party composite: on-chain valuation, flows, leverage and sentiment combined into two 0–100 scores, one for tops and one for bottoms.')
    th_ = tm['hist']['rows']; tmt = [dict(d=dn(d_), col='k2', dash='4 3') for d_ in tm['hist'].get('tops') or []]; tmb = [dict(d=dn(d_), col='k2', dash='4 3') for d_ in tm['hist'].get('bottoms') or []] + ([dict(d=dn(tm['hist']['low']['date']), col='up', dash='1 3', op=.9)] if (tm['hist'].get('low') or {}).get('date') else [])
    X['tmh'] = dict(k='tmh', zh='Tidemark 歷史', en='Tidemark history', dz='兩個視角。頂部：橘是頂部訊號、沙金是熱度、灰虛線是時機，橫線是 50 窗口和 70 警戒。底部：綠是底部訊號、藍是冷度，橫線是 50 底部區。', de='Two views. Top: orange is the top signal, sand is heat, grey dashed is timing. Bottom: green is the bottom signal, blue is cold. Dashed lines mark the 50 and 70 thresholds.',
      modes=[dict(mz='頂部視角', me='Top view', rows=th_, p=1, f='n1', dom=[0, 100], hero=2, ser=[ser(4, zh='時機', en='Timing', col='k2', dash='4 3', w=1), ser(3, zh='熱度', en='Heat', col='c5', w=1.2), ser(2, zh='頂部訊號', en='Top signal', col='dn', w=2)], refs=[dict(v=50, col='k2', zh='50 窗口', en='50 window'), dict(v=70, col='k2', zh='70 警戒', en='70 alert')], vl=tmt, leg=[['k2', '歷次週期頂部', 'Past cycle tops', 'dash']]),
             dict(mz='底部視角', me='Bottom view', rows=th_, p=1, f='n1', dom=[0, 100], hero=1, ser=[ser(6, zh='冷度', en='Cold', col='c3', w=1.2), ser(5, zh='底部訊號', en='Bottom signal', col='up', w=2)], refs=[dict(v=50, col='k2', zh='50 底部區', en='50 bottom zone')], vl=tmb, leg=[['k2', '歷次週期底部', 'Past cycle bottoms', 'dash'], ['up', '這一輪目前的低點', 'This cycle\'s low so far', 'dash']])])
    # ── 底部訊號 ──
    ac = cy['age_cost']; cr = ac['crosses']
    apx = ser(1, zh='BTC 價格', en='BTC price', col='ink', w=1.3, op=.7); c36 = ac.get('c36') or {}
    X['agecost'] = dict(k='agecost', zh='依持有時間的持幣成本', en='Holder cost by coin age',
      modes=[dict(mz='6–12 與 12–18 個月', me='6–12 vs 12–18 months', hz='收盤', he='Close', one=1, f='usd0', rows=ac['rows'], ser=[apx, ser(3, zh='持有 12–18 個月的成本', en='Cost of coins held 12–18 months', col='c3', w=2), ser(2, zh='持有 6–12 個月的成本', en='Cost of coins held 6–12 months', col='ac', w=2)],
                  marks=[dict(d=dn(x['date']), v=x['cost'], on=0, col='up' if x['kind'] == 'golden' else 'dn', up=1 if x['kind'] == 'golden' else 0, zh=x['date'][:7].replace('-', '/') + (' 上穿' if x['kind'] == 'golden' else ' 下穿'), en=x['date'][:7] + (' cross up' if x['kind'] == 'golden' else ' cross down')) for x in cr]),
             dict(mz='3–6 個月', me='3–6 months', hz='收盤', he='Close', one=1, f='usd0', rows=ac['rows'], ser=[apx, ser(4, zh='持有 3–6 個月的成本', en='Cost of coins held 3–6 months', col='ac', w=2)],
                  marks=[dict(d=dn(u_['date']), v=u_['cost'], on=0, col='up' if u_.get('bear') else 'k2', up=0, zh=u_['date'][:7].replace('-', '/') + ' 站回', en=u_['date'][:7] + ' reclaimed') for u_ in c36.get('ups') or []],
                  leg=[['up', '熊市之後第一次站回', 'First reclaim after a bear market', 'ring'], ['k2', '其他幾次站回', 'Other reclaims', 'ring']]),
             dict(mz='1 週–1 個月', me='1 week–1 month', hz='收盤', he='Close', one=1, f='usd0', rows=ac['rows'], ser=[apx, ser(5, zh='持有 1 週–1 個月的成本', en='Cost of coins held 1 week–1 month', col='ac', w=2)])],
      dz='把幣依持有時間分組，各組的平均成本。第一個視角：橘線（6–12 個月）跌到藍紫線（12–18 個月）下面，過去都在熊市底部附近；重新穿回上面，大約是主升段的開始。另外兩個視角各看一組成本和價格的關係。', de='Coins grouped by holding time, with each group\'s average cost. First view: the orange line (6–12 months) falling below the violet line (12–18 months) has come near bear-market bottoms; crossing back above has roughly marked the main bull leg. The other two views each set one group\'s cost against price.')
    hr = o['hash_ribbons']
    X['hashr'] = dict(k='hashr', zh='Hash Ribbons', en='Hash Ribbons', hz='算力 30 日均 ÷ 60 日均', he='Hashrate 30-day ÷ 60-day average', hs=dict(v=hr['ratio'], f='n3'),
      list=dict(rows=[row('現在的比值', 'Ratio now', hr['ratio'], f='n3', col='c5' if hr['capitulation'] else None, nz='低於 1 是礦工投降' if not hr['capitulation'] else '礦工投降中', ne='Below 1 means miner capitulation'),
                      row('這個狀態已經', 'In this state for', '%d 天' % hr['state_days'], ve='%d days' % hr['state_days']), row('上次交叉', 'Last cross', hr['last_cross'].replace('-', '/'), ve=hr['last_cross']), row('近 90 天最低', '90-day low', hr['min_ratio_90d'], f='n3')]),
      dz='算力的 30 日平均跌到 60 日平均下面，代表礦工在關機，過去常出現在底部附近；重新站回上面是投降結束。現有網站只有讀數、沒有圖，這裡照樣只放讀數。', de='When the 30-day hashrate average drops below the 60-day average, miners are switching off, which has often come near bottoms; crossing back above ends the capitulation. The live site shows readings only, and so does this card.')
    # ── 和歷史比 ──
    cc = cy['cycle_cmp']; CCOL = ['k2', 'c3', 'c4', 'ac']; NC = len(cy['cycle_cmp']['cycles'])
    X['cyccmp'] = dict(k='cyccmp', zh='和前幾輪比：頂部之後', en='Versus past cycles: after the top', hz='現在是這一輪頂部的', he='Now, as a share of this cycle\'s top', hs=dict(v=cc['cycles'][-1]['rows'][-1][1] * 100, f='p1'),
      xy=dict(xk='days', log=1, f='x2', series=[dict(zh=yr(c['top']) + (' 這一輪' if c['now'] else ''), en=yr(c['top']) + (' (now)' if c['now'] else ''), col=CCOL[(i + 4 - NC) % 4], w=2.4 if c['now'] else 1.4, op=1 if c['now'] else .8, rows=c['rows']) for i, c in enumerate(cc['cycles'])], ref=dict(v=1, col='k2', zh='頂部收盤', en='Top close'), vl=[dict(x=cc['day_now'], col='k2', zh='今天', en='Today')]),
      dz='把每一輪的頂部對齊在第 0 天，看頂部之後每天的收盤是頂部的幾倍。橘色是這一輪，現在是頂部後第 %d 天。' % cc['day_now'], de='Each cycle aligned at its top on day 0, showing every later close as a multiple of that top. Orange is this cycle, now %d days past its top.' % cc['day_now'])
    ce = o['capeff']; cema = max(math.log10(1 + max(0, c_['add_b'])) for c_ in ce['cycles'] + [ce['cur']]) or 1; cemm = max(math.log10(max(1, c_['mult'])) for c_ in ce['cycles'] + [ce['cur']]) or 1
    X['capeff'] = dict(k='capeff', zh='每輪資金效率', en='Capital efficiency by cycle', hz='這一輪到現在的價格倍數', he='This cycle\'s price multiple so far', hs=dict(v=ce['cur']['mult'], f='x2'),
      list=dict(rows=[row('%s → %s' % (yr(c['bottom']), yr(c['top'])) if not now_ else '%s → 現在' % yr(c['bottom']), '%s → %s' % (yr(c['bottom']), yr(c['top'])) if not now_ else '%s → now' % yr(c['bottom']), ('%.0f×' % c['mult']) if c['mult'] >= 20 else ('%.1f×' % c['mult']) if c['mult'] >= 10 else ('%.2f×' % c['mult']),
                          col='c4' if now_ else None, bar=math.log10(1 + max(0, c['add_b'])) / cema * 100, bc='c4', bar2=math.log10(max(1, c['mult'])) / cemm * 100, bc2='c5',
                          nz='流入 %s 億美元 · %d 天' % (format(int(round(c['add_b'] * 10)), ','), c.get('days') or 0), ne='$%sB in · %d days' % (format(c['add_b'], ',.1f'), c.get('days') or 0)) for c, now_ in [(c_, 0) for c_ in ce['cycles']] + [(ce['cur'], 1)]]),
      dz='每一輪從底到頂，實現市值增加了多少（流入的資金），換來幾倍的價格。每列兩條橫條：青色是流入的資金、金色是價格倍數，長度是對數。市場越大，同樣的資金推得越少。', de='For each cycle from bottom to top: how much realized cap was added (capital in) and what price multiple it bought. Two bars per row, on a log scale: cyan for capital in, gold for the price multiple. The bigger the market, the less each dollar moves it.')
    md = cy['model']; ym = lambda y, m: y + (m - 1) / 12.0; PN = {'直接修復': 'Direct recovery', '淺回檔': 'Shallow pullback', '基準雙底': 'Base case: double bottom', '延後新低': 'Delayed new low'}; PC = {'直接修復': 'c5', '淺回檔': 'c3', '基準雙底': 'ac', '延後新低': 'c4'}; nh = cy['next_halving_est']
    X['path'] = dict(k='path', zh='長期路徑：四種走法', en='Long-term paths: four scenarios', hz='頂部模型的中位數', he='Top-model median', hs=dict(v=md['top_model']['median'], f='usd0'),
      xy=dict(xk='ym', log=1, f='usd0', series=[dict(zh='%s %d%%' % (n, md['weights'][n]), en='%s %d%%' % (PN.get(n, n), md['weights'][n]), col=PC.get(n, 'k2'), w=1.4, op=.9, dash='5 4', rows=[[ym(a[0], a[1]), a[2]] for a in rows]) for i, (n, rows) in enumerate(md['nodes'].items())] + [dict(zh='已實現', en='Realized', col='ink', w=2.4, rows=[[ym(a[0], a[1]), a[2]] for a in md['realized']])],
              band=[md['top_model']['p10'], md['top_model']['p90'], 'dn'], vl=[dict(x=int(nh[:4]) + (int(nh[5:7]) - 1 + (int(nh[8:10]) - 1) / 30.0) / 12.0, col='k2', zh='下一次減半（估）', en='Next halving (est.)')], ref=dict(v=md['top_model']['median'], col='dn', zh='頂部中位 $%s' % format(md['top_model']['median'], ','), en='Top median $%s' % format(md['top_model']['median'], ','))),
      dz='四種可能的走法和各自的權重，每個月依實際價格重新加權。橘色底是頂部模型的八成區間，時間落在 %s。下次檢討 %s。' % (md['top_model']['timing'], md['next_review'].replace('-', '/')), de='Four possible paths with their weights, re-weighted each month against the actual price. The orange band is the top model\'s 80%% range, timed for %s. Next review %s.' % (md['top_model']['timing_en'], md['next_review']))
    hv = [dn(h) for h in cy['halvings']]; px = [[r[0], r[1]] for r in L['chips']['stress']['rows']]
    X['long'] = dict(k='long', zh='價格長期走勢', en='Long-term price', hz='收盤', he='Close', one=1, f='usd0', rng=0, rows=px, ser=[ser(1, zh='BTC 價格', en='BTC price', col='ac', w=1.5)],
      marks=[dict(d=dn(t[0]), v=t[1], on=0, col='dn', up=1, zh='%s 頂' % yr(t[0]), en='%s top' % yr(t[0])) for t in cy['tops']] + [dict(d=dn(t[0]), v=t[1], on=0, col='dn' if t[1] > 50000 else 'c3', up=0, zh='%s 底' % yr(t[0]), en='%s low' % yr(t[0])) for t in cy['bottoms']],
      vl=[dict(d=h, col='k2', dash='4 3') for h in hv], leg=[['dn', '週期頂部', 'Cycle tops', 'ring'], ['c3', '週期底部', 'Cycle bottoms', 'ring'], ['k2', '減半日', 'Halvings', 'dash']],
      dz='全部歷史的收盤，對數刻度：同樣的高度代表同樣的漲跌比例。過去幾輪的頂部大約在減半後 12 到 18 個月，底部大約在頂部後一年。', de='All closes on a log scale, where equal heights are equal percentage moves. Past tops came roughly 12–18 months after a halving, and bottoms about a year after the top.')
    mo = p['monthly']
    X['mon'] = dict(k='mon', zh='月度報酬', en='Monthly returns', hz='今年到現在', he='Year to date', hs=dict(v=mo['ytd'], f='pct1'), grid=dict(rows=mo['rows'], stats=mo['stats'], ystat=mo.get('ystat'), month=mo.get('month')),
      dz='每個月月底對上個月月底的漲跌 %%，%d 年起。下面兩列是每個月的中位數，和歷年裡上漲的比例（五成以上綠色）；加框的是這個月。' % mo['since'], de='Month-end to month-end returns in %%, since %d. The two bottom rows give each month\'s median and the share of years it rose (green at half or more); the outlined cell is the current month.' % mo['since'])
    grp = lambda zh, en, sz, se, keys: dict(zh=zh, en=en, sz=sz, se=se, charts=[X[k_] for k_ in keys if k_ in X])
    G = [grp('現在的階段', 'Where we are', '熊市、過渡還是牛市，偏多還是偏空', 'Bear, transition or bull; leaning long or short', ['dawn', 'dawnc', 'stage', 'regime', 'regc']),
         grp('估值冷熱', 'Valuation heat', '和過去比，現在算貴還是便宜', 'Rich or cheap against history', ['hnupl', 'rup', 'aviv', 'rrisk', 'pl', 'p6', 'p6v']),
         grp('頂部訊號', 'Top signals', '離頂部有多近', 'How close to a top', ['p20', 'radar', 'radarv', 'pi', 'tm', 'tmh']),
         grp('底部訊號', 'Bottom signals', '過去的底部長什麼樣，現在像不像', 'What past bottoms looked like, and whether this resembles one', ['lthloss', 'npl365', 'agecost', 'hashr']),
         grp('和歷史比', 'Against history', '和前幾輪、和模型比', 'Against past cycles and models', ['cyccmp', 'capeff', 'path', 'long', 'mon'])]
    s1 = dw['stats'][k] if k < len(dw['stats']) else {}
    hvs = [dn(h) for h in cy['halvings']] + [dn(cy['next_halving_est'])]
    dial = dict(stage=k, heat=dw['heat'], weeks=dw['stage_weeks'], stages=[[s[0], s[1], s[2], s[3], s[4]] for s in SG], comp=comp, y1=(s1.get('y1') or {}), nweeks=s1.get('weeks'), th=th, hv=hvs,
                rows=[[r[0], r[1], r[3], r[2]] for r in dw['rows'] if r[0] >= hvs[0] and r[1] is not None],
                marks=[[dn(m['date']), m['heat'], m['kind'], yr(m['date'])[2:] + ('頂' if m['kind'] == 'top' else '底'), "'" + yr(m['date'])[2:] + (' top' if m['kind'] == 'top' else ' low')] for m in dw['marks'] if dn(m['date']) >= hvs[0]],
                stats=[[x.get('weeks'), (x.get('y1') or {}).get('med'), (x.get('y1') or {}).get('up')] for x in dw['stats']])
    return G, dial
