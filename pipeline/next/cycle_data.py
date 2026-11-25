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
    # 2026-11-20 使用者：「『階段鎖定』的說明換個位置放」。原本「牛市一旦成立就鎖定」只藏在「證據」和右下的說明裡，卡上只看到大字「牛市」加偏多，
    #   和收盤已在下降的 200 日均線下 15% 打架。現在鎖定直接寫在大字上方（hz），清單第一列是「退回／前進到下一階段」的進度條，佐證燈排在後面
    bb = st.get('bear_back') or {}; bn = (st.get('bull_need') or {}).get('run', 30); ar = st.get('above_rising_run', 0)
    if st['stage'] == '牛市':
        n_, N_ = st.get('below_falling_run', 0), bb.get('bull_below_falling_run', 30)
        prog = [row('退回熊市的進度', 'Progress back to bear', '%d / %d 天' % (n_, N_), ve='%d / %d days' % (n_, N_), bar=n_ / N_ * 100, col='dn' if n_ else 'k2',
                    nz='牛市成立後鎖定：收盤要在下降中的 200 日均線下連 %d 天才退回熊市。收盤已在均線下 %d 天，%s。' % (N_, st.get('below_run', 0), '均線還在上升，還沒開始算' if st.get('sma200_rising') else '均線轉成下降後算到第 %d 天' % n_),
                    ne='Bull is locked once set: it takes %d straight closes under a falling 200-day MA to go back to bear. The close has been under the MA for %d days; %s.' % (N_, st.get('below_run', 0), 'the MA is still rising, so the count has not started' if st.get('sma200_rising') else 'since the MA turned down, this is day %d' % n_))]
    elif st['stage'] in ('過渡', '過渡期', '轉換期'):
        b_, N2 = st.get('below_run', 0), bb.get('transition_below_run', 5)
        prog = [row('成為牛市的進度', 'Progress to bull', '%d / %d 天' % (ar, bn), ve='%d / %d days' % (ar, bn), bar=ar / bn * 100, col='up' if ar else 'k2', nz='收盤在上升的 200 日均線上連 %d 天成為牛市。' % bn, ne='%d straight closes above a rising 200-day MA make it bull.' % bn),
                row('退回熊市的進度', 'Progress back to bear', '%d / %d 天' % (b_, N2), ve='%d / %d days' % (b_, N2), bar=b_ / N2 * 100, col='dn' if b_ else 'k2', nz='連 %d 天收在均線下退回熊市。' % N2, ne='%d straight closes below the MA send it back to bear.' % N2)]
    else:
        cs = st.get('capitulation_seen'); k_ = (1 if cs else 0) + (1 if ar else 0)
        prog = [row('進入過渡的條件', 'To enter transition', '%d / 2' % k_, ve='%d / 2' % k_, bar=k_ / 2 * 100, col='up' if k_ else 'k2',
                    nz='投降訊號%s；收盤%s上升的 200 日均線。' % ('出現過' if cs else '還沒出現', '站上' if ar else '還沒站上'), ne='Capitulation %s; the close is %s a rising 200-day MA.' % ('seen' if cs else 'not seen yet', 'above' if ar else 'not yet above'))]
    X['stage'] = dict(k='stage', zh='市場階段', en='Market stage', hz=('從 %s 起・鎖定中' if st['stage'] == '牛市' else '從 %s 起') % st['since'].replace('-', '/'), he=('Since %s, locked' if st['stage'] == '牛市' else 'Since %s') % st['since'], hs=dict(v=st['stage'], f='txt', ve=STN.get(st['stage'], st['stage'])),
      list=dict(rows=prog + [row(e['label'], EVN.get(e['id'], e['label']), evv(e), ve=evv(e), col='up' if e['ok'] else 'k2', nz=('成立：' if e['ok'] else '不成立：') + e['cond'], ne='Met' if e['ok'] else 'Not met') for e in st['evidence']['items']]),
      dz='這是什麼：用最簡單的規則替市場貼標籤，只看價格和 200 日均線（過去 200 天收盤的平均，常被當成長期趨勢線），加上「投降」有沒有出現過（大跌之後大量認賠賣出）。三個階段：熊市 → 過渡 → 牛市。投降出現過、收盤又站上還在往上走的 200 日均線，進入過渡；這樣連 30 天，成為牛市並鎖定。'
         '怎麼看：大字是現在的階段；第一列是往下一個階段走的進度，後面六項是其他佐證，綠色代表成立，只作參考、不參與判定。'
         '要保留的地方：鎖定是為了不被短暫跌破洗掉標籤，代價是反應慢：價格跌破均線之後，還會顯示牛市好一段時間。',
      de='What it is: the simplest possible label for the market, using only price against the 200-day MA (the average close of the past 200 days, often used as the long-run trend line) and whether a capitulation (heavy loss-taking after a big fall) has happened. Three stages: bear → transition → bull. A capitulation plus a close above a still-rising 200-day MA starts the transition; 30 straight days of that makes it bull, and it locks. '
         'How to read it: the big text is the current stage; the first row is progress toward the next stage, and the six rows after it are other checks, green when met, shown for reference only. '
         'Caveats: the lock keeps a brief dip from flipping the label, at the cost of speed: after price breaks below the average, the card can still say bull for quite a while.')
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
      dz='這是什麼：本站自己的中期多空分數。把六個項目（價格對 200 日均線、一年來的漲跌、市值對持有成本、流入的資金、交易所裡的幣、賣出的人賺多還是賠多）各自和自己的歷史比，合成一個 −6 到 +6 的分數：正的代表中期趨勢往上，負的代表往下；要連 4 週在另一邊才算翻轉。'
         '怎麼看：每根柱子是一週，顏色是當週的階段：分數為負是熊；熊市滿 26 週之後翻正的頭 26 週是初牛，之後是牛；到 +4 以上是過熱，−4 以下是極熊。'
         '要保留的地方：連 4 週才算翻轉，所以轉折會晚幾週；分數在 0 附近（−1 到 +1）容易來回翻，過去也有翻多之後一年反而更低的時候。',
      de='What it is: our own medium-term score. Six inputs (price against the 200-day MA, the one-year change, market value against holders\' cost, money flowing in, coins on exchanges, and whether sellers are taking profits or losses) are each compared with their own history and combined into a score from −6 to +6: positive means the medium-term trend is up, negative down; it takes four weeks on the other side to flip. '
         'How to read it: each bar is a week, coloured by that week\'s stage: negative is bear; the first 26 positive weeks after a bear run of 26 weeks or more are early bull, then bull; +4 and above is overheated, −4 and below extreme bear. '
         'Caveats: the four-week rule makes turns show up late; near 0 (−1 to +1) the score flips easily, and some past long flips were followed by lower prices a year on.')
    RGN = dict(d200=('價格對 200 日均線', 'Price vs 200-day MA'), mom12=('一年來的漲跌', 'One-year change'), mvrv1y=('市值對成本（比一年平均）', 'Value vs cost, against its 1-year mean'), rc30=('流入的資金（30 日）', 'Money flowing in, 30-day'), xs90=('交易所裡的幣（90 日）', 'Coins on exchanges, 90-day'), rpl=('賣出的人賺多還是賠多（90 日）', 'Sellers\' profit vs loss, 90-day'),
               sth=('價格對短期持有者成本', 'Price vs short-term holder cost'), asopr=('賣出的幣賺還是賠（30 日）', 'Coins sold at a profit or loss, 30-day'), lnupl=('長期持有者的帳面獲利', 'Long-term holders\' paper profit'), rup=('帳面獲利佔市值', 'Paper profit ÷ market cap'), pl=('價格對長期趨勢價', 'Price vs long-run trend'), rr=('儲備風險', 'Reserve risk'), mvz=('市值對成本（MVRV-Z）', 'Value vs cost (MVRV-Z)'))
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
      dz=('這是什麼：晨昏指數把一輪週期比成一天，從深夜（最便宜）走到黃昏（過熱）。它看兩件事。熱度：五項估值（例如持有者帳面賺多少、價格離長期趨勢多遠）各自和近 4 年比排第幾，平均成 0 到 100，0 是近 4 年最便宜。方向：四項趨勢指標合起來往上還是往下。'
          '兩個合起來分五段：熱度 %d 以下是深夜（底部區），%d 以上是黃昏（過熱）；中間方向往下是入夜（下跌），方向往上、熱度低於 %d 是破曉（初升），%d 以上是白晝（上升）。'
          '怎麼看：下格是每週的熱度，上格是價格，兩條線都用當時那一段的顏色；圓圈是歷次週期的頂和底，旁邊是當時的熱度。'
          '要保留的地方：熱度只和近 4 年比，所以每一輪都會有「最便宜」的時候，不代表絕對便宜；近兩輪估值都比價格先見頂，黃昏常提早出現；2013 年以來只有三輪多，統計只是歷史描述。') % (th['cold'], th['hot'], th['mid'], th['mid']),
      de=('What it is: the Dawn–Dusk Index treats a cycle as one day, from deep night (cheapest) to dusk (overheated). It looks at two things. Heat: five valuation measures (such as how much paper profit holders have, or how far price is from its long-run trend), each ranked against the last four years and averaged into 0–100, where 0 is the cheapest of those years. Direction: whether four trend measures, taken together, point up or down. '
          'Together they give five stages: heat at %d or below is deep night (bottom zone), %d or above is dusk (overheated); in between, a downward direction is nightfall (falling), an upward one with heat under %d is daybreak (early rise), and %d or more is daylight (rising). '
          'How to read it: the lower panel is weekly heat and the upper one price, both coloured by the stage at the time; circles mark past cycle tops and bottoms, with the heat then. '
          'Caveats: heat is only ranked against four years, so every cycle has a "cheapest" stretch that is not cheap in absolute terms; in the last two cycles valuations peaked before price, so dusk tends to come early; there are only about three cycles since 2013, so the statistics describe history.') % (th['cold'], th['hot'], th['mid'], th['mid']))
    comp = [row(RGN[c['key']][0], RGN[c['key']][1], c['pct'], f='n0', bar=c['pct'], mk=th['hot'], col=hcol(c['pct']), nz='估值 · 和近 4 年比的排名', ne='Valuation · rank against four years') for c in dw['heat_c']] + \
           [row(RGN[c['key']][0], RGN[c['key']][1], c['z'], f='s2', nz='趨勢 · 正的往上、負的往下', ne='Trend · positive up, negative down', **zbar(c['z'])) for c in dw['trend_c']]
    X['dawnc'] = dict(k='dawnc', zh='晨昏指數的組成', en='What the Dawn–Dusk Index is made of', hz='熱度', he='Heat', hs=dict(v=dw['heat'], f='n1'), list=dict(rows=comp),
      dz=('這是什麼：把晨昏指數拆開來看。前五列是熱度的來源，後四列是方向的來源。'
          '怎麼看：估值那五列，每一項和近 4 年比排第幾（0＝近 4 年最便宜，100＝最貴），五個的平均就是熱度，橫條上的直線是黃昏的門檻 %d。趨勢那四列，往右（綠）是往上、往左（紅）是往下，直線是 0，四個合起來決定方向。'
          '要保留的地方：這張只是拆開的數字，位置判斷看晨昏指數那張；排名只和近 4 年比。') % th['hot'],
      de=('What it is: the Dawn–Dusk Index taken apart. The first five rows feed the heat, the last four the direction. '
          'How to read it: each valuation row is ranked against the last four years (0 = the cheapest of those years, 100 = the richest); their average is the heat, and the tick on the bar marks the dusk line at %d. In the four trend rows, right (green) is up and left (red) is down, the tick is 0, and together they set the direction. '
          'Caveats: these are only the parts; the position call is on the Dawn–Dusk card, and the ranks only cover four years.') % th['hot'])
    X['regc'] = dict(k='regc', zh='週線多空分數的組成', en='What the regime score is made of', hz='分數', he='Score', hs=dict(v=rg['value'], f='s2'),
      list=dict(rows=[row(RGN[c['key']][0], RGN[c['key']][1], c['val'], f='s2', bar=max(0, min(100, 50 + c['val'] * 50)), mk=50, col='up' if c['val'] >= .15 else 'dn' if c['val'] <= -.15 else 'k2') for c in rg['comps']]),
      dz='這是什麼：把週線多空分數拆成六項，每一項和自己的歷史比，換成 −1 到 +1。怎麼看：往右是偏多、往左是偏空，直線是 0；+0.15 以上算偏多（綠）、−0.15 以下算偏空（紅），中間算持平（灰）。六項加起來就是多空分數。要保留的地方：單一項目常來回，幾項同一邊才有意義。',
      de='What it is: the weekly regime score split into its six inputs, each compared with its own history and scaled from −1 to +1. How to read it: right leans long, left leans short, the tick is 0; +0.15 or more counts as long (green), −0.15 or less as short (red), in between flat (grey). The six add up to the score. Caveats: single inputs swing back and forth; it matters when several point the same way.')
    # ── 估值冷熱 ──
    hn = o['hnupl']
    X['hnupl'] = dict(k='hnupl', zh='長期和短期持有者的帳面賺賠（NUPL）', en='Paper profit of long- and short-term holders (NUPL)', hz='長期持有者 NUPL', he='Long-term holder NUPL', f='n3', rows=hn['rows'], p=1, hero=1,
      ser=[ser(3, zh='短期持有者 NUPL', en='Short-term holder NUPL', col='ac', w=1, op=.7), ser(2, zh='長期持有者 NUPL', en='Long-term holder NUPL', col='c3', w=1.9)],
      zones=[dict(lo=None, hi=0, col='c3', zh='低於 0：投降（整體虧損）', en='Below 0: capitulation (a loss overall)'), dict(lo=0, hi=.25, col='c4', zh='0–0.25：希望', en='0–0.25: hope'), dict(lo=.25, hi=.5, col='up', zh='0.25–0.5：樂觀', en='0.25–0.5: optimism'), dict(lo=.5, hi=.75, col='c5', zh='0.5–0.75：信念', en='0.5–0.75: belief'), dict(lo=.75, hi=None, col='ac', zh='高於 0.75：過熱', en='Above 0.75: overheated')],
      marks=[dict(d=dn(t['date']), v=t['value'], col='ac', up=1, zh='%s %.2f' % (yr(t['date']), t['value']), en='%s %.2f' % (yr(t['date']), t['value'])) for t in hn['tops']] + [dict(d=dn(t['date']), v=t['value'], col='c3', up=0, zh='%s %.2f' % (yr(t['date']), t['value']), en='%s %.2f' % (yr(t['date']), t['value'])) for t in hn['bottoms']],
      dz='這是什麼：NUPL 是「帳面賺賠佔市值的比例」：所有還沒賣的幣，照現在的價格算，賺的減掉賠的，再除以市值。這裡分成長期持有者（幣放超過 150 天沒動）和短期持有者（不到 150 天，多半是最近買的人）。長期持有者的帳面獲利越厚，越接近頂部；越薄，越接近底部。'
         '怎麼看：粗線是長期持有者，細的橘線是短期持有者，橘線在 0 上面代表最近買的人整體在賺、下面是在賠。底色是長期持有者的五個區間，由冷到熱：0 以下投降、0–0.25 希望、0.25–0.5 樂觀、0.5–0.75 信念、0.75 以上過熱；圓圈是歷次頂和底的讀數。'
         '要保留的地方：頂部的讀數一輪比一輪低，這一輪底部長期持有者也沒有跌成虧損；區間的界線是常見分法，不是定律。',
      de='What it is: NUPL is paper profit or loss as a share of market cap: for every unsold coin, gains minus losses at today\'s price, divided by market cap. It is split into long-term holders (coins unmoved for 150+ days) and short-term holders (under 150 days, mostly recent buyers). The fatter long-term holders\' paper profit, the nearer a top; the thinner, the nearer a bottom. '
         'How to read it: the thick line is long-term holders and the thin orange line short-term holders; orange above 0 means recent buyers are in profit as a group, below 0 at a loss. The shading marks five long-term holder bands, cold to hot: below 0 capitulation, 0–0.25 hope, 0.25–0.5 optimism, 0.5–0.75 belief, above 0.75 overheated; circles mark readings at past tops and bottoms. '
         'Caveats: top readings fall every cycle, and this cycle\'s long-term holders never went underwater at the bottom; the bands are a common convention, not a law.')
    av = o.get('avgd')   # 2026-11-15 離成本線和均線多遠（oc_extra.avg_viz）：走勢一張（綜合／快和慢），九條線各自的百分位一張
    if av:
        AVN = dict(pl=('冪律', 'Power law'), ctp=('Cointime 價格', 'Cointime price'), tmm=('真實市場均價', 'True market mean'), rp=('實現價', 'Realized price'), v365=('365 天鏈上均價', '365-day on-chain average price'),
                   w200=('200 週均線', '200-week MA'), sth=('短期持有者成本', 'STH cost'), v90=('90 天鏈上均價', '90-day on-chain average price'), d200=('200 日均線', '200-day MA'))
        aym = lambda s_: s_[:7].replace('-', '/'); an1 = lambda v: '%.1f' % v; apc = lambda v: ('%.1f%%' % abs(v))
        past = [x for x in av['lows'] if not x['cur']]; cur = next((x for x in av['lows'] if x['cur']), None)
        amk = [dict(d=dn(x['d']), v=x['v'], col='c3', up=0, zh='%s %s' % (aym(x['d']), an1(x['v'])), en='%s %s' % (x['d'][:7], an1(x['v']))) for x in av['lows']]
        ev = [e_ for e_ in av['ev10'] if e_['f365'] is not None]; eup = sum(e_['f365'] > 0 for e_ in ev); edd = min([e_['dd365'] for e_ in ev] or [0]); bk = av['bk']
        aleg = [['c3', '每一輪熊市的最低讀值', 'Lowest reading of each bear market', 'ring']] + ([['k2', '10：前幾輪熊市都跌破過', '10: broken in every earlier bear market', 'dash']] if past and all(x['v'] < 10 for x in past) else [])
        X['avgd'] = dict(k='avgd', zh='離成本線和均線多遠', en='Distance from cost bases and averages', f='n1', rows=av['rows'], p=2, dom=[0, 100], rng=0,
          modes=[dict(mz='綜合', me='Overall', hz='九條線的平均排名（0＝歷史最低，100＝最高）', he='Average rank of the nine lines (0 = lowest ever, 100 = highest)', ser=[ser(1, zh='平均排名', en='Average rank', col='c3', w=1.8)],
                      refs=[dict(v=10, col='k2')], marks=amk, leg=aleg),
                 dict(mz='快和慢', me='Fast and slow', hz='快線（三條）的平均排名', he='Average rank, three fast lines', hero=1, rng=1095,
                      ser=[ser(3, zh='慢線（六條）', en='Slow lines (six)', col='c3', w=1.7), ser(4, zh='快線（三條）', en='Fast lines (three)', col='c5', w=1.4)])],
          dz='這是什麼：把價格和九條常見的成本線、均線各比一次（例如所有幣的平均成本、短期持有者成本、200 週均線、長期趨勢價），看今天的距離在到當天為止的全部歷史裡排第幾（0＝歷史上最低，100＝最高），九個取平均。數字越低，代表價格比這些線低得越少見，也就是越便宜。'
             '怎麼看：「綜合」是九條的平均，圓圈是每一輪熊市的最低讀值，虛線是 10。「快和慢」把九條分成兩組：快線（短期持有者成本、90 天鏈上均價、200 日均線）跟得快，快線比慢線低，代表最近跌得急。'
             '要保留的地方：它拿全部歷史排名，而每一輪的波動都比上一輪小，近年的低點比較難排到最前面；樣本只有幾輪週期，大方向和晨昏指數的熱度一樣。',
          de='What it is: price is compared with nine common cost lines and averages (such as the average cost of all coins, the short-term holder cost, the 200-week MA and the long-run trend price); for each, today\'s distance is ranked against all history up to that day (0 = the lowest ever, 100 = the highest), and the nine ranks are averaged. The lower the number, the rarer it is for price to sit this far below the lines, so the cheaper it is. '
             'How to read it: "Overall" is the average of the nine; circles mark the lowest reading of each bear market, and the dashed line is 10. "Fast and slow" splits the lines in two: the fast ones (short-term holder cost, 90-day on-chain average price, 200-day MA) react quickly, and fast below slow means the recent fall was quick. '
             'Caveats: it ranks against all history, and each cycle swings less than the one before, so recent lows rarely reach the very bottom of the ranking; there are only a few cycles, and its broad direction matches the Dawn–Dusk heat.')
        arow = lambda c_: row(AVN[c_['key']][0], AVN[c_['key']][1], c_['pct'], f='n0', bar=c_['pct'], col=hcol(c_['pct']),
                              nz='%s · 線在 $%s · 價格比它%s %s' % ('慢' if c_['grp'] == 's' else '快', format(c_['line'], ','), '低' if c_['dist'] < 0 else '高', apc(c_['dist'])),
                              ne='%s · line at $%s · price %s %s' % ('Slow' if c_['grp'] == 's' else 'Fast', format(c_['line'], ','), apc(c_['dist']), 'below' if c_['dist'] < 0 else 'above'))
        X['avgdc'] = dict(k='avgdc', zh='九條線各自排第幾', en='Where price ranks against each line', hz='平均', he='Average', hs=dict(v=av['value'], f='n1'), list=dict(rows=[arow(c_) for c_ in av['comps']]),
          dz='這是什麼：把「離成本線和均線多遠」拆成九條線各自來看。每一條的數字是價格離它的距離在全部歷史裡排第幾（0＝歷史上最低的位置，100＝最高），九個的平均就是那張圖的讀數。'
             '怎麼看：小字是這條線現在在多少錢，和價格比它高或低多少；「慢」的線變得慢（例如所有幣的平均成本、200 週均線），「快」的線跟得快。鏈上均價是這段期間鏈上轉帳的金額除以顆數，可以想成這段期間換手的平均價格。'
             '要保留的地方：價格在某條線上面，不代表那條線的排名就高：每條線的歷史擺幅不一樣。',
          de='What it is: "Distance from cost bases and averages" split into its nine lines. Each number is where price\'s distance from that line ranks in all history (0 = the lowest ever, 100 = the highest); the average of the nine is the reading on that chart. '
             'How to read it: the small print gives the line\'s current level and how far price is above or below it; "slow" lines move slowly (such as the average cost of all coins or the 200-week MA), "fast" lines react quickly. The on-chain average price is the dollar value of on-chain transfers in the period divided by the coins moved, roughly the average price at which coins changed hands. '
             'Caveats: price being above a line does not mean that line ranks high, because each line has swung by different amounts in the past.')
        from say_data import own   # 2026-11-15 這兩張是新版自己的圖，舊版沒有讀值可以接，直接寫
        zs = lambda t: (' ' if t[:1].isascii() else '') + t + (' ' if t[-1:].isascii() else '')   # 中文句子裡夾英文、數字開頭的名稱，前後留空格
        v0, v7 = av['value'], av.get('prev7'); evy = [e_ for e_ in ev if e_['f365'] is not None]; worst = min(evy, key=lambda e_: e_['dd365']) if evy else None
        # 2026-11-25 照 WRITING.md：標題講位置（便宜區、貴區、中間），百分位改成「歷史上只有 X% 的日子更低」，同一個數字只出現一次
        deeper = past and all(x['v'] < v0 for x in past)
        if v0 <= 20:
            asz = '和九條成本線、均線比，平均來說歷史上只有約 %d%% 的日子價格比現在更低：這是便宜區；%s。' % (round(v0), '但前幾輪熊底都比現在更低，還有往下的空間' if deeper else '已經和前幾輪熊底差不多低，但便宜區不等於最低點')
            ase = 'Against nine cost lines and averages, on average only about %d%% of days in history had price lower than now: a cheap zone, %s.' % (round(v0), 'though past bear bottoms all went lower, so there is room to fall' if deeper else 'about as low as past bear bottoms, though a cheap zone is not the exact low')
        elif v0 >= 80:
            asz = '和九條成本線、均線比，平均來說歷史上只有約 %d%% 的日子價格比現在更高：這是貴區，接近過去頂部的位置。' % round(100 - v0)
            ase = 'Against nine cost lines and averages, on average only about %d%% of days in history had price higher than now: a rich zone, where past tops sat.' % round(100 - v0)
        else:
            asz = '和九條成本線、均線比，價格在歷史的中段（平均排名 %d，0＝最低、100＝最高）：不便宜也不貴。' % round(v0)
            ase = 'Against nine cost lines and averages, price is mid-history (average rank %d, 0 = lowest, 100 = highest): neither cheap nor rich.' % round(v0)
        X['avgd']['say'] = own([
            ('這一輪最低', "This cycle's low", an1(cur['v']) if cur else '—', an1(cur['v']) if cur else '—', 'neu',
             '這一輪到目前最低是在 %s；前幾輪熊底是 %s。每一輪波動都比上一輪小，近年的低點比較難排到最前面。' % (aym(cur['d']), '、'.join(an1(x['v']) for x in past)) if cur else '這一輪還沒有低點。',
             'This cycle\'s lowest so far came in %s; earlier bear markets bottomed at %s. Each cycle swings less than the one before, so recent lows rarely reach the very bottom of the ranking.' % (cur['d'][:7], ', '.join(an1(x['v']) for x in past)) if cur else 'No low yet in this cycle.'),
            ('第一次跌破 10 之後', 'After first breaking 10', '%d 次裡 %d 次一年後漲' % (len(evy), eup), 'Up a year on: %d of %d' % (eup, len(evy)), 'neu',
             '過去第一次跌到 10 以下的那幾次，%s；但 %s 那次之後一年內還再跌了 %s：這是便宜區，不是底。' % ('多半一年後比當時高' if eup * 2 > len(evy) else '一年後比當時高的不到一半', aym(worst['d']), apc(worst['dd365'])) if worst else '還沒有跌到 10 以下的紀錄。',
             '%s first breaks below 10 were followed by a higher price a year on, but after the %s case price fell another %s within the year: a cheap zone, not a bottom.' % ('Most' if eup * 2 > len(evy) else 'Fewer than half of', worst['d'][:7], apc(worst['dd365'])) if worst else 'No break below 10 on record.'),
            ('一週前', 'A week ago', an1(v7) if v7 is not None else '—', an1(v7) if v7 is not None else '—', 'neu',
             '這一週%s了 %s：%s。' % ('降' if v0 < v7 else '升', an1(abs(v0 - v7)), '價格離這些線更遠、更便宜' if v0 < v7 else '價格往這些線靠近了一些') if v7 is not None else '沒有一週前的讀值。',
             '%s %s this week: %s.' % ('Down' if v0 < v7 else 'Up', an1(abs(v0 - v7)), 'price moved further below the lines, cheaper' if v0 < v7 else 'price moved a little closer to the lines') if v7 is not None else 'No reading from a week ago.')],
          asz, ase)
        cs_ = sorted(av['comps'], key=lambda c_: c_['pct']); lo_, hi_ = cs_[0], cs_[-1]; n10 = sum(1 for c_ in cs_ if c_['pct'] < 10)
        cline = lambda c_, en=False: (('price is %s %s it' % (apc(c_['dist']), 'below' if c_['dist'] < 0 else 'above')) if en else ('價格比它%s %s' % ('低' if c_['dist'] < 0 else '高', apc(c_['dist']))))
        rk = lambda c_: ('歷史上沒有一天，價格相對這條線比現在更低' if round(c_['pct']) <= 0 else '歷史上%s %d%% 的日子，價格相對這條線比現在更低' % ('只有' if c_['pct'] < 50 else '有', round(c_['pct'])))
        rke = lambda c_: ('no day in history had price lower against this line' if round(c_['pct']) <= 0 else '%s%d%% of days in history had price lower against this line' % ('only ' if c_['pct'] < 50 else '', round(c_['pct'])))
        X['avgdc']['say'] = own([
            ('最便宜的一條', 'Cheapest line', AVN[lo_['key']][0], AVN[lo_['key']][1], 'neu', '%s；%s。' % (rk(lo_), cline(lo_)), '%s; %s.' % (rke(lo_)[0].upper() + rke(lo_)[1:], cline(lo_, True))),
            ('最貴的一條', 'Richest line', AVN[hi_['key']][0], AVN[hi_['key']][1], 'neu', '九條裡最不便宜的是這條：%s；%s。' % (rk(hi_), cline(hi_)), 'The least cheap of the nine: %s; %s.' % (rke(hi_), cline(hi_, True)))],
          ('九條線裡有 %d 條已經排到歷史最低的 10%% 以內，最便宜的是%s' % (n10, zs(AVN[lo_['key']][0]).rstrip()) if n10 else '九條線都還沒排到歷史最低的 10%% 以內，最便宜的是%s' % zs(AVN[lo_['key']][0]).rstrip()),
          ('%d of the nine lines are already in the lowest 10%% of history; the cheapest is the %s' % (n10, AVN[lo_['key']][1]) if n10 else 'None of the nine lines is in the lowest 10%% of history yet; the cheapest is the %s' % AVN[lo_['key']][1]))
    rr = o['rrisk']
    X['rrisk'] = dict(k='rrisk', zh='儲備風險', en='Reserve risk', f='n5', rows=rr['rows'], p=1, log=1, hero=2,
      ser=[ser(3, zh='近 4 年最低 10%', en='4-year bottom 10%', col='c4', dash='4 3', w=1), ser(4, zh='近 4 年最高 10%', en='4-year top 10%', col='c5', dash='4 3', w=1), ser(2, zh='儲備風險', en='Reserve risk', col='c3', w=1.8)],
      spans=[dict(a=dn(e['start']), b=dn(e['end']), col='c4', op=.18) for e in rr['eps']], leg=[['c4', '在低檔區的期間', 'Time in the low zone', 'box']],
      dz='這是什麼：儲備風險比的是價格和長期持有者的信心。老手把幣放著不賣的時間越久、價格又越低，數值越低，代表「現在的價格相對持有者的信心很便宜」；價格衝高、老手開始賣，數值就變高。單位 ‰ 是千分之一。'
         '怎麼看：實線是儲備風險（對數刻度）；兩條虛線是近 4 年最低 10% 和最高 10% 的門檻，每天跟著移動；青色區塊是落在最低 10% 的期間。'
         '要保留的地方：頂部一輪比一輪低，整條線被壓扁，所以和近 4 年比，不和全部歷史比；2018 年的熊底沒有掉進最低 10%，單看這張會漏掉底部。',
      de='What it is: reserve risk compares price with long-term holders\' conviction. The longer seasoned holders sit on their coins and the lower the price, the lower the reading: price is cheap relative to holders\' conviction. When price runs up and they start selling, it rises. The unit ‰ means per thousand. '
         'How to read it: the solid line is reserve risk (log scale); the two dashed lines are the lowest-10% and highest-10% marks of the last four years, moving daily; cyan bands mark stays in the lowest 10%. '
         'Caveats: tops fall every cycle and squash the line, so it is compared with four years, not all history; the 2018 bear bottom never reached the lowest 10%, so this gauge alone can miss a bottom.')
    p6 = cy['p6']; hot = lambda v: 'ac' if v >= 80 else 'c5'
    X['p6'] = dict(k='p6', zh='頂部三指標', en='Top three indicators', hz='進入頂部區的有幾個', he='How many are in the top zone', hs=dict(v=sum(1 for v in p6.values() if v >= 80), f='n0'),
      list=dict(rows=[row('MVRV Z', 'MVRV Z', p6['mvrv_z'], f='n0', bar=p6['mvrv_z'], mk=80, bc='ac', nz='市值對成本 · 和近 4 年比的排名', ne='Value vs cost · rank against four years'), row('NUPL', 'NUPL', p6['nupl'], f='n0', bar=p6['nupl'], mk=80, bc='ac', nz='帳面賺賠 · 和近 4 年比的排名', ne='Paper profit · rank against four years'),
                      row('Puell 倍數', 'Puell multiple', p6['puell'], f='n0', bar=p6['puell'], mk=80, bc='ac', nz='礦工收入 · 和近 4 年比的排名', ne='Miner income · rank against four years')]),
      dz='這是什麼：三個常用來找週期頂部的指標。MVRV Z：市值比所有幣的平均成本高多少（換算成和平常相比的倍數）；NUPL：全體帳面賺賠佔市值的比例；Puell 倍數：礦工今天的收入是過去一年平均的幾倍。每一項都和自己近 4 年比排第幾，0 最冷、100 最熱。'
         '怎麼看：橫條是排名，直線是 80（近 4 年最熱的 20%）；任兩項到 80 以上，算進入頂部區。'
         '要保留的地方：只看估值，不看時間；而且只說離頂部多遠，很冷不代表已經到底。',
      de='What it is: three indicators commonly used to spot cycle tops. MVRV Z: how far market value sits above the average cost of all coins (scaled against its usual swings); NUPL: all holders\' paper profit or loss as a share of market value; Puell multiple: miners\' income today against their one-year average. Each is ranked against its own last four years, 0 coldest, 100 hottest. '
         'How to read it: bars show the rank and the tick is 80 (the hottest 20% of four years); any two at 80 or above count as the top zone. '
         'Caveats: valuation only, not timing; it only measures distance from a top, and cold does not mean the bottom is in.')
    vz = o['viz']
    def vmode(key, zh, en, f, rz, re_, col='c3'):
        v = vz[key]; return dict(mz=zh, me=en, rows=v['rows'], f=f, ser=[ser(1, zh=zh, en=en, col=col, w=1.6)], refs=[dict(v=v['ref']['y'], col='dn', zh=rz, en=re_)] if v.get('ref') else [])
    X['p6v'] = dict(k='p6v', zh='頂部三指標的走勢', en='Top three indicators over time',
      dz='這是什麼：頂部三指標近一年的原始數值，可以切換：MVRV Z（市值比平均成本高多少）、NUPL（全體帳面賺賠佔市值）、Puell 倍數（礦工收入對一年平均）。怎麼看：紅色虛線是各自近 4 年的熱門檻（只有 20% 的日子比它高），線碰到虛線，那一項就算「熱」。要保留的地方：門檻每天跟著近 4 年移動，不是固定的數字。',
      de='What it is: the raw values of the three top indicators over the past year, one at a time: MVRV Z (how far value sits above average cost), NUPL (all holders\' paper profit as a share of value) and the Puell multiple (miner income against its one-year average). How to read it: the red dashed line is each one\'s hot line for the last four years (only 20% of days were higher); when the line touches it, that indicator counts as hot. Caveats: the hot line moves with the four-year window; it is not a fixed number.',
      modes=[vmode('mvrv-zscore', 'MVRV Z', 'MVRV Z', 'n3', '近 4 年的熱門檻', 'Four-year hot line'), vmode('nupl', 'NUPL', 'NUPL', 'n3', '近 4 年的熱門檻', 'Four-year hot line'), vmode('puell-multiple', 'Puell 倍數', 'Puell multiple', 'n3', '近 4 年的熱門檻', 'Four-year hot line', 'c5')])
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
    fairl = dict(c=3, zh='趨勢價（冪律合理價）', en='Trend price (power-law fair value)', col='k2', dash='3 3')
    X['pl'] = dict(k='pl', zh='冪律：比特幣的長期趨勢價', en='Power law: Bitcoin\'s long-run trend price',
      modes=[dict(mz='在通道裡的高低', me='Place in the channel', hz='通道位置（0%＝貼著底線，100%＝碰到頂線）', he='Channel position (0% = on the bottom line, 100% = at the top line)', rows=plr, p=1, f='p1', tf='lin', dom=[-4, 104], ax=[100, 50, 0],
                  ser=[ser(2, zh='通道位置', en='Channel position', t='cat', cc=6, cols=SC, w=2, names=PLN)], zones=[dict(lo=PCUT[i_], hi=PCUT[i_ + 1], col=SC[i_]) for i_ in range(5)],
                  top=[dict(c=4, zh='頂線（歷次牛頂的連線）', en='Top line (through past tops)', col='dn', dash='5 4'), fairl, dict(c=5, zh='底線（歷次熊底的連線）', en='Bottom line (through past bottoms)', col='c3', dash='5 4')],
                  leg=[[SC[i_], PLN[i_][0] + ' %d–%d%%' % (PCUT[i_], PCUT[i_ + 1]), PLN[i_][1] + ' %d–%d%%' % (PCUT[i_], PCUT[i_ + 1]), 'box'] for i_ in range(5)]),
             dict(mz='是趨勢價的幾倍', me='Multiple of trend', hz='價格 ÷ 趨勢價', he='Price ÷ trend price', rows=plr, p=1, f='x2', log=1, ser=[ser(7, zh='價格 ÷ 趨勢價', en='Price ÷ trend price', col='ac', w=1.7)], refs=[dict(v=1, col='k2', zh='1 倍＝剛好在趨勢價', en='1× = exactly on trend')], top=[fairl],
                  zones=[dict(lo=bb[0], hi=bb[1], col='c3', zh='在歷次底部的範圍內', en='Inside the range of past bottoms', nz='歷次底部範圍', ne='the range of past bottoms')],
                  marks=[dict(d=dn(t[0]), v=t[1], col='dn' if t[1] >= 1 else 'c3', up=1 if t[1] >= 1 else 0, zh='%s %.2f×' % (yr(t[0]), t[1]), en='%s %.2f×' % (yr(t[0]), t[1])) for t in pl['tops'] + pl['bottoms']],
                  leg=[['c3', '歷次底部的範圍 %.2f–%.2f×' % (bb[0], bb[1]), 'Range of past bottoms %.2f–%.2f×' % (bb[0], bb[1]), 'box']])],
      dz='冪律是什麼：把比特幣 2010 年以來的價格畫在對數圖上，它一直沿著一條越來越平的曲線往上長，這條線就是冪律趨勢，可以想成「照過去的成長速度，今天大概值多少」，這裡叫趨勢價（每天只用當天以前的價格算，沒有偷看未來）。價格會繞著它上下擺：牛市頂部衝到它的好幾倍，熊市底部跌到它的 %.2f–%.2f 倍。''「在通道裡的高低」：把歷次熊底連成一條底線、歷次牛頂連成一條頂線，0%% 是貼著底線（跌破也顯示 0%%）、100%% 是碰到頂線，線從冷色到熱色分五段。「是趨勢價的幾倍」：價格直接除以趨勢價，1 倍就是剛好在趨勢上。''要保留的地方：底線和頂線是事後把過去的底和頂連起來的，只有四輪；比特幣越長越大，以後的擺幅可能更小，便宜也可能便宜很久。' % (bb[0], bb[1]), de='What a power law is: plot Bitcoin\'s price since 2010 on a log chart and it keeps climbing along a curve that flattens over time. That curve is the power-law trend: roughly what Bitcoin is worth today if it keeps growing at its past pace, called the trend price here (each day fitted only on prices up to that day, so no hindsight). Price swings around it: bull-market tops reach several times the trend, bear-market bottoms fall to %.2f–%.2f× of it. ''Place in the channel: past bear bottoms are joined into a bottom line and past bull tops into a top line; 0%% is on the bottom line (below it also shows 0%%) and 100%% is at the top line, coloured from cool to hot in five bands. Multiple of trend: price divided by the trend price; 1× is exactly on trend. ''Caveats: the bottom and top lines join past lows and highs after the fact, and there are only four cycles. As Bitcoin grows its swings may shrink, and cheap can stay cheap for a long time.' % (bb[0], bb[1]))
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
    from say_data import own   # 2026-11-15 頂部雷達：舊版面板只有資料來源、沒有讀值，直接寫
    zs = lambda t: (' ' if t[:1].isascii() else '') + t + (' ' if t[-1:].isascii() else '')
    rmx = max(tr.items(), key=lambda kv: kv[1]['pct_since_2022_11'])
    X['radar']['say'] = own([(RN[k2][0], RN[k2][1], fx(RN[k2][2], x['value']), fx(RN[k2][2], x['value']).replace(' 萬顆', '0K BTC'), 'warn' if x['pct_since_2022_11'] >= 90 else 'neu',
                              '%s在 2022 年 11 月以來的第 %d 百分位；2025 年頂部附近的極值是 %s。' % (zs(RN[k2][0]).lstrip(), round(x['pct_since_2022_11']), fx(RN[k2][2], x['extreme_near_2025_top'])),
                              '%s is at percentile %d since November 2022; its extreme near the 2025 top was %s.' % (RN[k2][1], round(x['pct_since_2022_11']), fx(RN[k2][2], x['extreme_near_2025_top']).replace(' 萬顆', '0K BTC'))) for k2, x in tr.items()],
                            '三項裡最高的是%s，第 %d 百分位' % (zs(RN[rmx[0]][0]).rstrip(), round(rmx[1]['pct_since_2022_11'])), 'Highest of the three: %s, percentile %d' % (RN[rmx[0]][1], round(rmx[1]['pct_since_2022_11'])))
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
    # ── 2026-11-19 Hash Ribbons 改成圖（bv_more.py 第 7 項；使用者傳 Capriole 的 TradingView 圖：「可以做出這種線嗎？提示買入時間」，看過回測後「做，照實標」）──
    #   上格價格，下格算力 30／60 日均線（對數），兩線之間 30 日在上綠、在下紅；投降期塗淡紅底；原版買點畫在價格上：一年後漲綠圈、跌紅圈、還不到一年用青色（不和結局同色，㉝）
    hb = (o.get('bvx') or {}).get('hrib')
    if hb and len(hb.get('rows') or []) > 300:
        SG_ = lambda v: ('+%d%%' % v) if v >= 0 else ('−%d%%' % -v)
        YMD = lambda d_: d_.replace('-', '/'); bys = hb['buys']; pre, post, bp = hb['pre'], hb['post'], hb['base_post']
        bcol = lambda b: 'c4' if b['r365'] is None else 'up' if b['r365'] > 0 else 'dn'
        yr0 = L['meta']['bar_date'][:4]; ty = [b for b in bys if b['d'][:4] == yr0]; lb = bys[-1] if bys else None
        X['hashr'] = dict(k='hashr', zh='Hash Ribbons', en='Hash Ribbons', hz='30 日均算力', he='30-day average hashrate', f='ehs', tf='log', p=4, npc=1, hero=1, rng=1095, rows=hb['rows'],
          ser=[ser(2, zh='60 日均線', en='60-day average', col='k2', w=1.2), ser(1, zh='30 日均線', en='30-day average', col='up', w=1.7)],
          bands=[dict(a=1, b=2, col='up', col2='dn', op=.3)],
          spans=[dict(a=a_, b=b_, col='dn', soft=1) for a_, b_ in hb['spans']],
          marks=[dict(d=b['dn'], v=b['px'], on='p', col=bcol(b), up=1, zh='' if b['r365'] is None else '一年 ' + SG_(b['r365']), en='' if b['r365'] is None else '1y ' + SG_(b['r365'])) for b in bys],
          leg=[['dn', '投降期（30 日均在 60 日均下面）', 'Capitulation (30-day below 60-day)', 'box'], ['up', '原版買點：一年後漲', 'Original buy: up a year later', 'ring'], ['dn', '原版買點：一年後跌', 'Original buy: down a year later', 'ring'], ['c4', '原版買點：還不到一年，不知道是哪一種', 'Original buy: under a year, outcome unknown', 'ring']],
          src='Bitview · %d/%d' % (int(o['bvx']['date'][5:7]), int(o['bvx']['date'][8:10])), srce='Bitview · ' + o['bvx']['date'][5:].replace('-', '/'),
          dz='算力的 30 日平均跌到 60 日平均下面，代表礦工在關機（投降期，淡紅底）。Capriole 原版的買點：投降結束之後，價格 10 日均線第一次站上 20 日均線那天，圖上用圓圈標在價格上。'
             '這裡只算持續 %d 天以上的投降。回測：2021 年以前 %d 次，一年後 %d 次漲，中位數 %s；2021 年以後滿一年的 %d 次，%d 次漲，中位數 %s，同期隨便一天買進一年後漲的機率 %d%%、中位數 %s，差不多。'
             '礦機效率、託管和算力出租改變了礦工關機的原因，投降和價格的關係比以前弱。只作讀值。' % (hb['min_eps'], pre['n'], pre['up'], SG_(pre['med']), post['n'], post['up'], SG_(post['med']), bp['up'], SG_(bp['med'])),
          de='When the 30-day hashrate average drops below the 60-day, miners are switching off (capitulation, red shade). Capriole\'s original buy: after capitulation ends, the first day the 10-day price average crosses above the 20-day; circles mark it on price. '
             'Only capitulations of %d days or more count here. Backtest: before 2021, %d signals, %d up a year later, median %s; since 2021, %d with a full year, %d up, median %s, against %d%% up and a %s median for buying on any day in that span, about the same. '
             'Rig efficiency, hosting and hashrate rental have changed why miners switch off, so the link to price is weaker than it was. A reading only.' % (hb['min_eps'], pre['n'], pre['up'], SG_(pre['med']), post['n'], post['up'], SG_(post['med']), bp['up'], SG_(bp['med'])))
    # ── 2026-11-19 獲利供給：全體 vs 扣掉十年老幣（pipeline/bv_more.py 第 6 項；使用者看了白仙女〈浮盈籌碼佔比，剔除休眠超過 10 年的幣〉的研究後說「加這張卡」）──
    #   只放讀值和歷次熊底，不放對方的分檔建倉規則（網站不給操作建議）；他的 36%／40% 兩條線只有最近兩輪碰過，也不畫
    q_ = (o.get('bvx') or {}).get('psx')
    if q_ and len(q_.get('rows') or []) > 300:
        from say_data import own
        P1 = lambda v: '%.1f%%' % v; YM = lambda d_: d_[:7].replace('-', '/'); lw = q_['lows']; lc = lw[-1]
        done = [c_ for c_ in q_['cross45'] if c_['y1'] is not None]; nup = sum(1 for c_ in done if c_['y1'] > 0); wst = min(c_['worst'] for c_ in done) if done else 0
        ml = lambda w, k: '' if w[k]['d'][:4] == '2020' else P1(w[k]['v'])   # 圖上只寫數字（年份看橫軸，手機上才放得下）；2020 年 3 月的急跌離 2018 太近，只畫圈，數字在讀數裡
        pmk = [dict(d=w['ex']['dn'], v=w['ex']['v'], col='c5', up=0, zh=ml(w, 'ex'), en=ml(w, 'ex')) for w in lw] + \
              [dict(d=w['raw']['dn'], v=w['raw']['v'], col='c3', up=1, zh=ml(w, 'raw'), en=ml(w, 'raw')) for w in lw if w['raw']['v'] - w['ex']['v'] >= 1]
        X['psx'] = dict(k='psx', zh='獲利供給：全體 vs 扣掉十年老幣', en='Supply in profit: all vs excluding 10-year-old coins',
          modes=[dict(mz='兩條比較', me='Both', hz='扣掉十年老幣，在獲利的比例', he='In profit, excluding 10-year-old coins', f='p1', rng=0, p=4, npc=1, hero=1, dom=[25, 100], rows=q_['rows'],
                      ser=[ser(1, zh='全體', en='All supply', col='c3', w=1.5), ser(2, zh='扣掉十年老幣', en='Excluding 10-year-old coins', col='c5', w=2)],
                      refs=[dict(v=50, col='k2', zh='50%', en='50%')], marks=pmk,
                      leg=[['c5', '扣掉十年老幣：歷次熊底', 'Excluding old coins: past bear lows', 'ring'], ['c3', '全體：歷次熊底（2020 年起兩條才分開）', 'All supply: past bear lows (the lines split from 2020)', 'ring']]),
                 dict(mz='十年老幣佔流通量', me='Share of 10-year-old coins', hz='放了 10 年以上的幣佔流通量', he='Coins unmoved for 10+ years, share of supply', f='p1', rng=0, p=4, npc=1, hero=0, rows=q_['rows'],
                      ser=[ser(3, zh='10 年以上的幣佔流通量', en='10+ year coins, share of supply', col='c4', w=2)])],
          src='Bitview · %d/%d' % (int(L['onchain']['bvx']['date'][5:7]), int(L['onchain']['bvx']['date'][8:10])), srce='Bitview · ' + L['onchain']['bvx']['date'][5:].replace('-', '/'),
          dz='在獲利的幣（現價比它最後一次移動時的價格高）佔供給的比例，7 日平均。一條是全體，一條扣掉放了 10 年以上沒動的幣（含中本聰時期的幣，現在佔流通量 %s，%s 年才開始有）。'
             '這些幣成本極低、幾乎永遠算在獲利，而且越積越多，會把全體的比例墊高：不扣的話熊底一輪比一輪高，扣掉之後反過來一輪比一輪低，所以兩種都沒有一條固定的線能跨輪通用。圓圈是歷次熊底那段的最低點。'
             '第二個檢視是 10 年以上的幣佔流通量多少。老幣不一定是遺失的，哪天動了就會回到計算裡。逐筆 UTXO，沒有排除交易所內部移轉。只作讀值。' % (P1(q_['old']), q_['old_first'][:4]),
          de='The share of supply in profit (price above where each coin last moved), as a 7-day average. One line is all supply; the other leaves out coins unmoved for 10+ years (Satoshi-era coins included; %s of supply now, and none before %s). '
             'Those coins cost almost nothing, sit in profit nearly always and keep piling up, which props up the all-supply share: left in, each bear bottom sits higher than the last; taken out, each sits lower. Neither version has a fixed line that works across cycles. Circles mark the low of each bear phase. '
             'The second view shows how much of supply has been still for 10+ years. Old coins are not necessarily lost; any that move rejoin the count. Per UTXO, with exchange-internal transfers not excluded. A reading only.' % (P1(q_['old']), q_['old_first'][:4]))
        X['psx']['say'] = own([
            ('扣掉十年老幣', 'Excluding 10-year-old coins', P1(q_['ex']), P1(q_['ex']), 'up' if q_['ex'] <= 45 else 'neu',
             '扣掉放了 10 年以上沒動的幣，在獲利的比例 7 日平均 %s，30 天前是 %s；%s 年以來只有 %s 的日子比現在低。' % (P1(q_['ex']), P1(q_['ex30']), q_['since'][:4], P1(q_['pct'])),
             'Leaving out coins unmoved for 10+ years, %s of supply is in profit on a 7-day average, against %s 30 days ago; since %s only %s of days were lower.' % (P1(q_['ex']), P1(q_['ex30']), q_['since'][:4], P1(q_['pct']))),
            ('全體', 'All supply', P1(q_['raw']), P1(q_['raw']), 'neu',
             '不扣的話是 %s，30 天前 %s。差的 %.1f 個百分點來自老幣：它們佔流通量 %s，幾乎全部算在獲利。' % (P1(q_['raw']), P1(q_['raw30']), q_['raw'] - q_['ex'], P1(q_['old'])),
             'With them left in it is %s, against %s 30 days ago. The %.1f-point gap comes from the old coins: %s of supply, nearly all of it in profit.' % (P1(q_['raw']), P1(q_['raw30']), q_['raw'] - q_['ex'], P1(q_['old']))),
            ('歷次熊底', 'Past bear lows', '這一輪 ' + P1(lc['ex']['v']), 'This cycle ' + P1(lc['ex']['v']), 'neu',
             '扣掉老幣的最低點：%s，這一輪是 %s 的 %s。不扣的話：%s。' % ('、'.join('%s 年 %s' % (w['ex']['d'][:4], P1(w['ex']['v'])) for w in lw[:-1]), YM(lc['ex']['d']), P1(lc['ex']['v']), '、'.join('%s 年 %s' % (w['raw']['d'][:4], P1(w['raw']['v'])) for w in lw)),
             'Lows excluding old coins: %s; this cycle %s on %s. With them left in: %s.' % (', '.join('%s in %s' % (P1(w['ex']['v']), w['ex']['d'][:4]) for w in lw[:-1]), P1(lc['ex']['v']), lc['ex']['d'].replace('-', '/'), ', '.join('%s in %s' % (P1(w['raw']['v']), w['raw']['d'][:4]) for w in lw))),
            ('第一次跌破 45%', 'First drop below 45%', '%d 次裡 %d 次一年後漲' % (len(done), nup), '%d of %d up a year on' % (nup, len(done)), 'neu',
             '扣掉老幣的比例每一段第一次跌破 45%%（回到 60%% 以上才算新的一段）：%s。滿一年的 %d 次，一年後 %d 次是漲的；但跌破之後一年內最多再跌 %d%%。次數少，只作讀值。' % ('、'.join('%s（一年後 %+d%%）' % (YM(c_['d']), c_['y1']) if c_['y1'] is not None else '%s（還沒滿一年）' % YM(c_['d']) for c_ in q_['cross45']), len(done), nup, abs(wst)),
             'Each first drop of the excluded share below 45%% (a new episode starts only after a return above 60%%): %s. Of the %d with a full year since, %d were up a year later, but price fell as much as another %d%% within that year. Few cases; a reading only.' % (', '.join('%s (%+d%% a year on)' % (c_['d'][:7], c_['y1']) if c_['y1'] is not None else '%s (under a year ago)' % c_['d'][:7] for c_ in q_['cross45']), len(done), nup, abs(wst)))],
            '扣掉十年老幣，%s 的幣在獲利，%s 年以來只有 %s 的日子比現在低。' % (P1(q_['ex']), q_['since'][:4], P1(q_['pct'])),
            'Excluding 10-year-old coins, %s of supply is in profit; since %s only %s of days were lower.' % (P1(q_['ex']), q_['since'][:4], P1(q_['pct'])))
    # ── 2026-11-24 CVDD（pipeline/bv_more.py 第 8 項；使用者看了一篇用 CVDD 找熊底的研究後說「做新卡」）──
    #   價格對數座標配 CVDD 線，第二個檢視是收盤高出 CVDD 多少；照實寫：常數是事後調的、只有四輪
    cq = (o.get('bvx') or {}).get('cvdd')
    if cq and len(cq.get('rows') or []) > 300:
        from say_data import own
        Uc = lambda v: '$' + format(int(round(v)), ','); P1 = lambda v: '%.1f%%' % v; SGc = lambda v: ('+%d%%' % v) if v >= 0 else ('−%d%%' % -v); YM = lambda d_: d_[:7].replace('-', '/'); MDc = lambda d_: '%d/%d' % (int(d_[5:7]), int(d_[8:10]))
        cl, cn = cq['lows'], cq['now']; done = [e for e in cq['eps'] if e['y1'] is not None]; nup = sum(1 for e in done if e['y1'] > 0); wst = abs(min(e['worst'] for e in done)) if done else 0
        z, an = cq['z25'], cq['any180']; bd = (int(cq['date'][5:7]), int(cq['date'][8:10])) if cq.get('date') else None
        bvd = o['bvx']['date']; rg = '%s–%s' % (P1(min(w['prem'] for w in cl)), P1(max(w['prem'] for w in cl)))
        X['cvdd'] = dict(k='cvdd', zh='CVDD：歷次熊底的長期地板', en='CVDD: the long-run floor under past bear lows',
          modes=[dict(mz='價格與 CVDD', me='Price and CVDD', hz='CVDD（累計價值幣天銷毀）', he='CVDD (cumulative value-days destroyed)', one=1, f='usd0', log=1, rng=0, hero=2, rows=cq['rows'],
                      ser=[ser(3, zh='BTC 價格', en='BTC price', col='ink', w=1.3, op=.7), ser(2, zh='CVDD 高出 25%', en='CVDD +25%', col='c4', dash='4 3', w=1), ser(1, zh='CVDD', en='CVDD', col='c5', w=2)],
                      marks=[dict(d=w['dn'], v=w['px'], on=0, col='c5', up=0, zh='+' + P1(w['prem']), en='+' + P1(w['prem'])) for w in cl] + [dict(d=cn['dn'], v=cn['px'], on=0, col='ac', up=0, zh='+' + P1(cn['prem']), en='+' + P1(cn['prem']))],
                      leg=[['c5', '歷次熊底離 CVDD 最近的一天（收盤高出多少）', 'Closest close to CVDD in each past bear (premium)', 'ring'], ['ac', '這一輪到目前最近的一天', 'This cycle\'s closest so far', 'ring']]),
                 dict(mz='價格是它的幾倍', me='Price ÷ CVDD', hz='價格 ÷ CVDD', he='Price ÷ CVDD', f='x2', log=1, rng=0, p=3, npc=1, hero=0, rows=cq['rows'],   # 用倍數配對數座標：2013、2017 年的高峰（上千 %）和靠近地板的 1.0x 倍都看得清楚
                      ser=[ser(5, zh='價格 ÷ CVDD', en='Price ÷ CVDD', col='c5', w=1.8)],
                      refs=[dict(v=1.25, col='c4', zh='高出 25%', en='25% above'), dict(v=1, col='dn', zh='CVDD', en='CVDD')],
                      marks=[dict(d=w['dn'], v=round(1 + w['prem'] / 100, 3), col='c5', up=0, zh=P1(w['prem']), en=P1(w['prem'])) for w in cl] + [dict(d=cn['dn'], v=round(1 + cn['prem'] / 100, 3), col='ac', up=0, zh=P1(cn['prem']), en=P1(cn['prem']))])],
          src='Bitview · %d/%d' % (int(bvd[5:7]), int(bvd[8:10])), srce='Bitview · ' + bvd[5:].replace('-', '/'),
          dz='CVDD（累計價值幣天銷毀）：每天被移動的幣「放了幾天 × 當天價格」從 2009 年累加，再除以市場運行的天數和一個常數 600 萬。'
             '它幾乎只往上走（過去一年 %s），不太受短期漲跌影響。2014 年以來四次熊底，收盤最接近時都還高出它 %s，沒有跌破過。'
             '要保留的地方：600 萬這個常數是原作者事後調出來、讓過去的低點剛好碰到線，所以「沒跌破過」有一部分是調出來的；而且只有四輪。用收盤價，算最低價的話會更近一點。只作讀值。' % (SGc(cq['grow']), rg),
          de='CVDD (cumulative value-days destroyed): each day\'s coin-days destroyed times that day\'s price, summed from 2009, then divided by market age in days and a constant of 6 million. '
             'It almost only rises (%s over the past year) and barely reacts to short swings. In the four bear lows since 2014, the closest close was still %s above it; it has never closed below. '
             'Caveats: the 6 million constant was tuned after the fact so past lows touch the line, so "never broken" is partly by design, and there are only four cycles. Closing prices; intraday lows come a little closer. A reading only.' % (SGc(cq['grow']), rg))
        X['cvdd']['say'] = own([
            ('高出 CVDD', 'Above CVDD', P1(cq['prem']), P1(cq['prem']), 'up' if cq['prem'] < 25 else 'neu',
             '收盤 %s，CVDD %s，高出 %s；30 天前高出 %s。這一輪到目前最近的是 %s，高出 %s。' % (Uc(cq['px']), Uc(cq['v']), P1(cq['prem']), P1(cq['prem30']), MDc(cn['d']), P1(cn['prem'])),
             'Close %s, CVDD %s: %s above; 30 days ago %s. This cycle\'s closest so far was %s, at %s.' % (Uc(cq['px']), Uc(cq['v']), P1(cq['prem']), P1(cq['prem30']), cn['d'][5:].replace('-', '/'), P1(cn['prem']))),
            ('歷次熊底', 'Past bear lows', '中位數 ' + P1(cq['low_med']), 'Median ' + P1(cq['low_med']), 'neu',
             '收盤最接近 CVDD 時高出：%s，中位數 %s。照今天的 CVDD 換算，高出 %s 是 %s，高出 25%% 是 %s。' % ('、'.join('%s 年 %s' % (w['d'][:4], P1(w['prem'])) for w in cl), P1(cq['low_med']), P1(cq['low_med']), Uc(cq['at_med']), Uc(cq['at25'])),
             'Closest closes above CVDD: %s; median %s. On today\'s CVDD, %s above is %s and 25%% above is %s.' % (', '.join('%s in %s' % (P1(w['prem']), w['d'][:4]) for w in cl), P1(cq['low_med']), P1(cq['low_med']), Uc(cq['at_med']), Uc(cq['at25']))),
            ('第一次高出不到 25%', 'First time under 25%', '%d 次裡 %d 次一年後漲' % (len(done), nup), '%d of %d up a year on' % (nup, len(done)), 'neu',
             '每一段第一次高出不到 25%%（回到 60%% 以上才算新的一段）：%s。之後一年內最多再跌 %d%%。2014 年以來高出不到 25%% 的 %d 天，之後 180 天 %d%% 是漲的、中位數 %s（隨便一天是 %d%%、%s）；只有四輪，只作讀值。'
             % ('、'.join('%s（一年後 %s）' % (YM(e['d']), SGc(e['y1'])) if e['y1'] is not None else '%s（還沒滿一年）' % YM(e['d']) for e in cq['eps']), wst, z['n'], z['up'], SGc(z['med']), an['up'], SGc(an['med'])),
             'Each first close under 25%% above (a new episode starts after a return above 60%%): %s. Price fell up to another %d%% within the year after. Since 2014, %d days under 25%%: %d%% were up 180 days later, median %s (any day: %d%%, %s). Only four cycles; a reading only.'
             % (', '.join('%s (%s a year on)' % (e['d'][:7], SGc(e['y1'])) if e['y1'] is not None else '%s (under a year ago)' % e['d'][:7] for e in cq['eps']), wst, z['n'], z['up'], SGc(z['med']), an['up'], SGc(an['med']))),
            ('地板在往上', 'The floor keeps rising', SGc(cq['grow']) + '／年', SGc(cq['grow']) + ' a year', 'neu',
             'CVDD 一年前 %s，現在 %s，一年 %s。橫盤越久，同樣的距離對應的價格越高：底部不一定要跌到今天算出來的價位。' % (Uc(cq['v365']), Uc(cq['v']), SGc(cq['grow'])),
             'CVDD was %s a year ago and is %s now, %s in a year. The longer price moves sideways, the higher the same distance sits: a bottom need not reach today\'s numbers.' % (Uc(cq['v365']), Uc(cq['v']), SGc(cq['grow'])))],
            '收盤高出 CVDD %s；過去四次熊底最近時高出 %s，中位數換算今天約 %s。' % (P1(cq['prem']), rg, Uc(cq['at_med'])),
            'The close is %s above CVDD; past bear lows came within %s, and the median on today\'s CVDD is about %s.' % (P1(cq['prem']), rg, Uc(cq['at_med'])))
    # ── 2026-11-25 VDD 倍數（pipeline/bv_more.py 第 10 項；使用者傳了 Checkonchain 那張加註「底背离」的圖，看過回測後說「加成新卡」）──
    #   上格價格，下格倍數（對數），熱度分區照原圖；底背離放寬版標在價格上、照一年後的結果上色，嚴格版（倍數翻倍）圈在倍數上；照實寫放寬版和隨便一天差不多
    vq = (o.get('bvx') or {}).get('vddm')
    if vq and len(vq.get('rows') or []) > 300:
        from say_data import own
        N2 = lambda v: '%.2f' % v; SGv = lambda v: ('+%d%%' % v) if v >= 0 else ('−%d%%' % -v); YM = lambda d_: d_[:7].replace('-', '/')
        ZN = lambda v: ('冷', 'cold') if v < .75 else ('涼', 'cool') if v < 1.4 else ('溫', 'warm') if v < 2.9 else ('熱', 'hot')
        vs, vl, bs, bl, bb = vq['strict'], vq['loose'], vq['bs'], vq['bl'], vq['base']; bvd = o['bvx']['date']
        ecol = lambda e: 'c4' if e['r365'] is None else 'up' if e['r365'] > 0 else 'dn'
        fails = [e for e in vl if e['r365'] is not None and e['r365'] <= 0]; lf = fails[-1] if fails else None
        dv = vq['div']; st = 2 if dv is not None and dv >= 2 else 1 if dv is not None and dv >= 1.5 else 0
        X['vddm'] = dict(k='vddm', zh='VDD 倍數：放久的幣動得多不多', en='VDD Multiple: are long-held coins moving',
          hz='VDD 倍數（30 日 ÷ 365 日）', he='VDD Multiple (30-day ÷ 365-day)', f='n2', log=1, p=2, npc=1, hero=0, rng=0, rows=vq['rows'],
          ser=[ser(1, zh='VDD 倍數', en='VDD Multiple', col='c5', w=1.6)],
          zones=[dict(lo=None, hi=.75, col='c3', zh='冷：低於 0.75', en='Cold: below 0.75', nz='冷區 0.75', ne='the 0.75 cold line'), dict(lo=1.4, hi=2.9, col='c5', zh='溫：1.4–2.9', en='Warm: 1.4–2.9', nz='溫區 1.4', ne='the 1.4 warm line'), dict(lo=2.9, hi=None, col='ac', zh='熱：高於 2.9', en='Hot: above 2.9', nz='熱區 2.9', ne='the 2.9 hot line')],
          refs=[dict(v=1, col='k2', zh='一年平均', en='1-year average')],
          marks=[dict(d=e['dn'], v=e['px'], on='p', col=ecol(e), up=0, zh='' if e['r365'] is None else '一年 ' + SGv(e['r365']), en='' if e['r365'] is None else '1y ' + SGv(e['r365'])) for e in vl]
                + [dict(d=e['dn'], v=e['m'], col='ink', up=1, zh='×%.1f' % e['x'], en='×%.1f' % e['x']) for e in vs],
          leg=[['up', '底背離（放寬版）：一年後漲', 'Divergence (loose): up a year later', 'ring'], ['dn', '底背離（放寬版）：一年後跌', 'Divergence (loose): down a year later', 'ring'],
               ['c4', '還不到一年，不知道是哪一種', 'Under a year, outcome unknown', 'ring'], ['ink', '嚴格版：倍數到 60 天前的 2 倍以上', 'Strict: multiple at 2× its level 60 days earlier', 'ring']],
          src='Bitview · %d/%d' % (int(bvd[5:7]), int(bvd[8:10])), srce='Bitview · ' + bvd[5:].replace('-', '/'),
          dz='VDD（價值幣天銷毀）：每天被移動的幣「放了幾天 × 當天價格」。倍數是它的 30 日平均 ÷ 365 日平均，高於 1 代表最近一個月放久的幣動得比過去一年平常多。熱度分區照 Checkonchain 原圖（2.9／1.4／0.75）。'
             '底背離：收盤在 60 日低點 3%% 以內、比 60 天前跌 10%% 以上，倍數卻升到 60 天前的 1.5 倍以上（放寬版，圓圈畫在價格上，照一年後漲跌上色）或 2 倍以上（嚴格版，圈在倍數上），前後 60 天只算一次。'
             '回測（%s 年起）：嚴格版 %d 次，一年後 %d 次漲；放寬版滿一年的 %d 次，%d 次漲、中位數 %s，同期隨便一天一年後漲的機率 %d%%、中位數 %s，差不多。'
             '倍數升高只代表放得久、價值高的幣在移動，可能是長期持有者認賠投降，也可能是還在出貨，換錢包和交易所整理冷錢包也算。幣天數用 Bitview，和 Checkonchain 近年差 5%% 上下、早年差得多。只作讀值。'
             % (vq['since'][:4], bs['n'], bs['up'], bl['n'], bl['up'], SGv(bl['med']), bb['up'], SGv(bb['med'])),
          de='VDD (value-days destroyed): each day\'s coins moved, weighted by how long they sat and by that day\'s price. The multiple is its 30-day average ÷ its 365-day average; above 1 means long-held coins moved more this month than in a usual day of the past year. Heat bands follow the Checkonchain original (2.9 / 1.4 / 0.75). '
             'Bottom divergence: the close within 3%% of its 60-day low and down 10%% or more on 60 days earlier, while the multiple rose to 1.5× its level 60 days earlier (loose; circles on price, coloured by the move a year later) or 2× (strict; circled on the multiple); one count per 60 days. '
             'Backtest since %s: the strict version fired %d times, %d up a year later; the loose version %d times with a full year, %d up, median %s, against %d%% up and a %s median for any day, about the same. '
             'A rising multiple only means old, high-value coins are moving: long-term holders capitulating or still distributing, wallet reshuffles and exchange cold-storage moves included. Coin-days from Bitview, within about 5%% of Checkonchain in recent years and further apart early on. A reading only.'
             % (vq['since'][:4], bs['n'], bs['up'], bl['n'], bl['up'], SGv(bl['med']), bb['up'], SGv(bb['med'])))
        hz_ = ('價格 60 天跌了 %d%%，VDD 倍數反而升到 60 天前的 %.2f 倍：%s' % (abs(vq['chg60']), vq['x60'], '嚴格版的底背離成立' if st == 2 else '放寬版的底背離成立，嚴格版（2 倍）還沒到' if st == 1 else '還不算底背離')) if vq['chg60'] < 0 and vq['x60'] > 1 else \
              ('VDD 倍數 %s，60 天前 %s；價格 60 天 %s，沒有底背離' % (N2(vq['v']), N2(vq['v60']), SGv(vq['chg60'])))
        he_ = ('Price fell %d%% in 60 days while the VDD Multiple rose to %.2f× its level then: %s' % (abs(vq['chg60']), vq['x60'], 'the strict divergence is on' if st == 2 else 'the loose divergence is on, the strict one (2×) is not' if st == 1 else 'not a divergence yet')) if vq['chg60'] < 0 and vq['x60'] > 1 else \
              ('VDD Multiple %s, %s 60 days ago; price %s over 60 days, no bottom divergence' % (N2(vq['v']), N2(vq['v60']), SGv(vq['chg60'])))
        X['vddm']['say'] = own([
            ('底背離', 'Bottom divergence', '嚴格版成立' if st == 2 else '放寬版成立' if st == 1 else '沒有', 'Strict, on' if st == 2 else 'Loose, on' if st == 1 else 'None', 'up' if st == 2 else 'neu',
             hz_ + '。', he_ + '.'),
            ('VDD 倍數', 'VDD Multiple', N2(vq['v']), N2(vq['v']), 'neu',
             '%s（%s區），30 天前 %s、60 天前 %s；%s 年以來 %s 的日子比現在低。' % (N2(vq['v']), ZN(vq['v'])[0], N2(vq['v30']), N2(vq['v60']), vq['since'][:4], '%.1f%%' % vq['pct']),
             '%s (%s), against %s 30 days ago and %s 60 days ago; since %s, %s of days were lower.' % (N2(vq['v']), ZN(vq['v'])[1], N2(vq['v30']), N2(vq['v60']), vq['since'][:4], '%.1f%%' % vq['pct'])),
            ('嚴格版', 'Strict version', '%d 次裡 %d 次一年後漲' % (bs['n'], bs['up']), '%d of %d up a year on' % (bs['up'], bs['n']), 'neu',
             '倍數到 60 天前 2 倍以上：%s，都在熊底附近，但只有 %d 次。' % ('、'.join('%s（×%.1f，一年後 %s）' % (YM(e['d']), e['x'], SGv(e['r365'])) if e['r365'] is not None else '%s（×%.1f，還沒滿一年）' % (YM(e['d']), e['x']) for e in vs), len(vs)),
             'Multiple at 2× or more: %s, all near bear lows, but only %d cases.' % (', '.join('%s (×%.1f, %s a year on)' % (e['d'][:7], e['x'], SGv(e['r365'])) if e['r365'] is not None else '%s (×%.1f, under a year ago)' % (e['d'][:7], e['x']) for e in vs), len(vs))),
            ('放寬版', 'Loose version', '%d 次裡 %d 次一年後漲' % (bl['n'], bl['up']), '%d of %d up a year on' % (bl['up'], bl['n']), 'neu',
             '倍數到 1.5 倍以上：滿一年的 %d 次，%d 次漲、中位數 %s；隨便一天一年後漲的機率 %d%%、中位數 %s，差不多。%s' % (bl['n'], bl['up'], SGv(bl['med']), bb['up'], SGv(bb['med']), ('最近一次跌的是 %s，之後一年 %s、一年內最多跌 %d%%。' % (YM(lf['d']), SGv(lf['r365']), abs(lf['worst']))) if lf else ''),
             'At 1.5× or more: %d with a full year, %d up, median %s; any day: %d%% up, median %s, about the same.%s' % (bl['n'], bl['up'], SGv(bl['med']), bb['up'], SGv(bb['med']), (' The latest miss was %s: %s a year on, down as much as %d%% within it.' % (lf['d'][:7], SGv(lf['r365']), abs(lf['worst']))) if lf else ''))],
            ('價格 60 天跌 %d%%、VDD 倍數升到 60 天前的 %.2f 倍：%s' % (abs(vq['chg60']), vq['x60'], '嚴格版底背離成立，過去 %d 次都在熊底，但只有 %d 次。' % (bs['n'], bs['n']) if st == 2 else '放寬版底背離成立，但這一版過去和隨便一天差不多；嚴格版（2 倍）還沒到。')) if st else
            'VDD 倍數 %s（%s區），沒有底背離；嚴格版過去 %d 次都在熊底。' % (N2(vq['v']), ZN(vq['v'])[0], bs['n']),
            ('Price is down %d%% in 60 days while the VDD Multiple is %.2f× its level then: %s' % (abs(vq['chg60']), vq['x60'], 'the strict divergence is on; all %d past cases were at bear lows, but there are only %d.' % (bs['n'], bs['n']) if st == 2 else 'the loose divergence is on, though it has done no better than any day; the strict one (2×) is not.')) if st else
            'VDD Multiple %s (%s), no bottom divergence; all %d strict cases were at bear lows.' % (N2(vq['v']), ZN(vq['v'])[1], bs['n']))
    # ── 和歷史比 ──
    cc = cy['cycle_cmp']; CCOL = ['k2', 'c3', 'c4', 'ac']; NC = len(cy['cycle_cmp']['cycles'])
    X['cyccmp'] = dict(k='cyccmp', zh='和前幾輪比：頂部之後', en='Versus past cycles: after the top', hz='現在比這一輪頂部', he='Now, versus this cycle\'s top', hs=dict(v=(cc['cycles'][-1]['rows'][-1][1] - 1) * 100, f='pct1'),
      xy=dict(xk='days', log=1, f='xpct', series=[dict(zh=yr(c['top']) + (' 這一輪' if c['now'] else ''), en=yr(c['top']) + (' (now)' if c['now'] else ''), col=CCOL[(i + 4 - NC) % 4], w=2.4 if c['now'] else 1.4, op=1 if c['now'] else .8, rows=c['rows']) for i, c in enumerate(cc['cycles'])], ref=dict(v=1, col='k2', zh='頂部收盤', en='Top close'), vl=[dict(x=cc['day_now'], col='k2', zh='今天', en='Today')]),
      dz='把每一輪的頂部對齊在第 0 天，看頂部之後每天的收盤比頂部高或低多少（−50%% 是跌掉一半）。橘色是這一輪，現在是頂部後第 %d 天。' % cc['day_now'], de='Each cycle aligned at its top on day 0, showing how far every later close sits above or below that top (−50%% means half gone). Orange is this cycle, now %d days past its top.' % cc['day_now'])
    ddv = o.get('dd')   # 2026-11-13 離高點的回撤（oc_extra.dd_viz）：兩個視角，週期的頂底沿用全站同一套
    if ddv:
        dc, da = ddv['cyc'], ddv['ath']; ps = dc['past']; ymz = lambda s_: s_[:7].replace('-', '/'); sl = lambda s_: s_.replace('-', '/'); mn = lambda v: ('%.0f%%' % v).replace('-', '−'); mn1 = lambda v: ('%.1f%%' % v).replace('-', '−')
        DST = [['在高點', 'At the high'], ['在高點下方', 'Below the high']]
        dmk = [dict(d=dn(x['d']), v=x['v'], col='dn', up=0, zh='%s %s' % (ymz(x['d']), mn(x['v'])), en='%s %s' % (x['d'][:7], mn(x['v']))) for x in ps['deep']]
        amk = [dict(d=dn(x['d']), v=x['v'], col='dn' if x['d'] == dc['bottom'] else 'c3', up=0, zh='%s 底 %s' % (yr(x['d']), mn(x['v'])), en='%s low %s' % (yr(x['d']), mn(x['v']))) for x in da['bottoms']]
        X['dd'] = dict(k='dd', zh='離高點的回撤', en='Drawdown from the high',
          modes=[dict(mz='這一輪低點以來', me='Since the cycle low', hz='離這一輪的高點', he="From this cycle's high", f='pct1', rows=[[r[0], r[1], r[2]] for r in ddv['rows']], p=2, npc=1,
                      ser=[ser(1, zh='離這一輪高點', en="From the cycle's high", t='sign', base=0, st=DST, w=1.5)], refs=[dict(v=ps['med'], col='k2')],
                      marks=dmk, leg=[['k2', '前四輪的中位數 %s' % mn1(ps['med']), 'Median of the past four, %s' % mn1(ps['med']), 'dash'], ['dn', '每一輪最深的一次', 'Deepest pullback of each cycle', 'ring']]),
                 dict(mz='歷史高點', me='All-time high', hz='離歷史高點', he='From the all-time high', f='pct1', rng=0, rows=[[r[0], r[3], r[2]] for r in ddv['rows']], p=2, npc=1,
                      ser=[ser(1, zh='離歷史高點', en='From the all-time high', t='split', base=0, st=DST, w=1.5)], refs=[dict(v=0, col='k2', solid=1)],
                      marks=amk, leg=[['c3', '週期底部', 'Cycle bottoms', 'ring'], ['dn', '這一輪目前的低點', "This cycle's low so far", 'ring']])],
          dz='收盤比高點低多少，兩個視角。「這一輪低點以來」：每一輪從底部起算，和這段期間的最高收盤比，只畫底部到頂部；這一輪從 %s 的低點（$%s）起算，高點是 %s 的 $%s，如果之後跌破那個低點，這一段就要重算。前四輪從底到頂的日子裡，一半比 %s 淺，%d%% 比現在深。「歷史高點」：和歷史最高收盤（%s 的 $%s）比，圓圈是每一輪的底部。只作讀值。'
             % (sl(dc['bottom']), format(dc['bottom_px'], ','), sl(dc['high']), format(dc['high_px'], ','), mn1(ps['med']), ps['deeper'], sl(da['high']), format(da['high_px'], ',')),
          de='How far the close sits below the high, in two views. "Since the cycle low": each cycle is measured from its bottom against the highest close since then, drawn from bottom to top only. This cycle starts at the %s low ($%s) and its high is $%s on %s; if that low breaks, this stretch has to be redrawn. Across the past four cycles, half of all bottom-to-top days were shallower than %s and %d%% were deeper than now. "All-time high": measured against the highest close on record ($%s on %s); circles mark each cycle bottom. A reading only.'
             % (dc['bottom'], format(dc['bottom_px'], ','), format(dc['high_px'], ','), dc['high'], mn1(ps['med']), ps['deeper'], format(da['high_px'], ','), da['high']))
        from say_data import own   # 2026-11-15 新版自己的圖，直接寫讀值
        X['dd']['say'] = own([
            ('離這一輪高點', "From this cycle's high", mn1(dc['value']), mn1(dc['value']), 'warn' if dc['value'] <= ps['p25'] else 'neu',
             '收盤比這一輪的高點（%s 的 $%s）低 %s。前四輪從底到頂的日子裡，只有 %d%% 比現在深。' % (sl(dc['high']), format(dc['high_px'], ','), mn1(abs(dc['value'])), ps['deeper']),
             "The close is %s below this cycle's high ($%s on %s). Across the past four cycles, only %d%% of bottom-to-top days were deeper than now." % (mn1(abs(dc['value'])), format(dc['high_px'], ','), dc['high'], ps['deeper'])),
            ('前四輪的中位數', 'Median of the past four', mn1(ps['med']), mn1(ps['med']), 'neu',
             '前四輪從底部到頂部的日子，一半的時候回撤比 %s 淺；最淺的四分之三在 %s 以內。' % (mn1(abs(ps['med'])), mn1(abs(ps['p25']))),
             'On half of all bottom-to-top days in the past four cycles the pullback was shallower than %s; three quarters stayed within %s.' % (mn1(abs(ps['med'])), mn1(abs(ps['p25'])))),
            ('離歷史高點', 'From the all-time high', mn1(da['value']), mn1(da['value']), 'neu',
             '收盤比歷史最高收盤（%s 的 $%s）低 %s，已經 %d 天。' % (sl(da['high']), format(da['high_px'], ','), mn1(abs(da['value'])), da['days']),
             'The close is %s below the record close ($%s on %s), %d days on.' % (mn1(abs(da['value'])), format(da['high_px'], ','), da['high'], da['days']))],
          '離這一輪高點 %s，前四輪只有 %d%% 的日子比現在深' % (mn1(dc['value']), ps['deeper']), "%s from this cycle's high; only %d%% of past bottom-to-top days were deeper" % (mn1(dc['value']), ps['deeper']))
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
      dz='四種可能的走法和各自的權重，每個月依實際價格重新加權。橘色底是頂部模型的 80%% 區間，時間落在 %s。下次檢討 %s。' % (md['top_model']['timing'], md['next_review'].replace('-', '/')), de='Four possible paths with their weights, re-weighted each month against the actual price. The orange band is the top model\'s 80%% range, timed for %s. Next review %s.' % (md['top_model']['timing_en'], md['next_review']))
    hv = [dn(h) for h in cy['halvings']]; px = [[r[0], r[1]] for r in L['chips']['stress']['rows']]
    X['long'] = dict(k='long', zh='價格長期走勢', en='Long-term price', hz='收盤', he='Close', one=1, f='usd0', rng=0, rows=px, ser=[ser(1, zh='BTC 價格', en='BTC price', col='ac', w=1.5)],
      marks=[dict(d=dn(t[0]), v=t[1], on=0, col='dn', up=1, zh='%s 頂' % yr(t[0]), en='%s top' % yr(t[0])) for t in cy['tops']] + [dict(d=dn(t[0]), v=t[1], on=0, col='dn' if t[1] > 50000 else 'c3', up=0, zh='%s 底' % yr(t[0]), en='%s low' % yr(t[0])) for t in cy['bottoms']],
      vl=[dict(d=h, col='k2', dash='4 3') for h in hv], leg=[['dn', '週期頂部', 'Cycle tops', 'ring'], ['c3', '週期底部', 'Cycle bottoms', 'ring'], ['k2', '減半日', 'Halvings', 'dash']],
      dz='全部歷史的收盤，對數刻度：同樣的高度代表同樣的漲跌比例。過去幾輪的頂部大約在減半後 12 到 18 個月，底部大約在頂部後一年。', de='All closes on a log scale, where equal heights are equal percentage moves. Past tops came roughly 12–18 months after a halving, and bottoms about a year after the top.')
    mo = p['monthly']
    X['mon'] = dict(k='mon', zh='月度報酬', en='Monthly returns', hz='今年到現在', he='Year to date', hs=dict(v=mo['ytd'], f='pct1'), grid=dict(rows=mo['rows'], stats=mo['stats'], ystat=mo.get('ystat'), month=mo.get('month')),
      dz='每個月月底對上個月月底的漲跌 %%，%d 年起。下面兩列是每個月的中位數，和歷年裡上漲的比例（50%% 以上綠色）；加框的是這個月。' % mo['since'], de='Month-end to month-end returns in %%, since %d. The two bottom rows give each month\'s median and the share of years it rose (green at half or more); the outlined cell is the current month.' % mo['since'])
    grp = lambda zh, en, sz, se, keys: dict(zh=zh, en=en, sz=sz, se=se, charts=[X[k_] for k_ in keys if k_ in X])
    G = [grp('現在的階段', 'Where we are', '熊市、過渡還是牛市，偏多還是偏空', 'Bear, transition or bull; leaning long or short', ['dawn', 'dawnc', 'stage', 'regime', 'regc']),
         grp('估值冷熱', 'Valuation heat', '和過去比，現在算貴還是便宜', 'Rich or cheap against history', ['avgd', 'avgdc', 'hnupl', 'rup', 'aviv', 'rrisk', 'pl', 'p6', 'p6v']),
         grp('頂部訊號', 'Top signals', '離頂部有多近', 'How close to a top', ['p20', 'radar', 'radarv', 'pi', 'tm', 'tmh']),
         grp('底部訊號', 'Bottom signals', '過去的底部長什麼樣，現在像不像', 'What past bottoms looked like, and whether this resembles one', [k_ for k_ in ['lthloss', 'npl365', 'psx', 'cvdd', 'vddm', 'agecost', 'hashr'] if k_ not in ('psx', 'cvdd', 'vddm') or k_ in X]),
         grp('和歷史比', 'Against history', '和前幾輪、和模型比', 'Against past cycles and models', ['cyccmp', 'dd', 'capeff', 'path', 'long', 'mon'])]
    s1 = dw['stats'][k] if k < len(dw['stats']) else {}
    hvs = [dn(h) for h in cy['halvings']] + [dn(cy['next_halving_est'])]
    dial = dict(stage=k, heat=dw['heat'], weeks=dw['stage_weeks'], stages=[[s[0], s[1], s[2], s[3], s[4]] for s in SG], comp=comp, y1=(s1.get('y1') or {}), nweeks=s1.get('weeks'), th=th, hv=hvs,
                rows=[[r[0], r[1], r[3], r[2]] for r in dw['rows'] if r[0] >= hvs[0] and r[1] is not None],
                marks=[[dn(m['date']), m['heat'], m['kind'], yr(m['date'])[2:] + ('頂' if m['kind'] == 'top' else '底'), "'" + yr(m['date'])[2:] + (' top' if m['kind'] == 'top' else ' low')] for m in dw['marks'] if dn(m['date']) >= hvs[0]],
                stats=[[x.get('weeks'), (x.get('y1') or {}).get('med'), (x.get('y1') or {}).get('up')] for x in dw['stats']])
    return G, dial
