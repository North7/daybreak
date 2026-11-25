# -*- coding: utf-8 -*-
"""鏈上內頁原型的資料：21 張圖的完整規格（多條線、色帶、門檻、標記、K 線、籌碼柱、背離連線），build.py 會 import。
顏色對照現有網站：s1→c3、s2→ac、s3→c4、s4／warn→c5、up→up、down→dn。"""

def build(L, N, E, dn):
    o = L['onchain']; ch = L['chips']; cyc = L['cycle']
    R = lambda v, d=2: None if v is None else round(v, d)
    yr = lambda s: s[:4]
    ser = lambda c, **k: dict(c=c, **k)
    # ── 成本與位置 ──
    sb = o['sth_bands']['rows']; KS = [2, 1, .5, -.5, -1, -2]
    sb_rows = [[r[0], r[1], r[2]] + [round(r[2] * (r[3] + k * r[4])) for k in KS] + [R((r[1] / r[2] - 1) * 100, 2) if r[2] else None] for r in sb]
    c_sth = dict(k='sthgap', zh='短期持有者成本帶', en='Short-term holder cost bands', hz='收盤離短期持有者成本', he='Close vs short-term holder cost', one=1, f='usd0', rows=sb_rows, hero=8,
      ser=[ser(1, zh='BTC 價格', en='BTC price', col='ink', w=1.3, op=.7), ser(3, zh='+2 標準差', en='+2σ', col='c3', dash='5 4', w=1.1), ser(4, zh='+1 標準差', en='+1σ', col='c5', w=1.1), ser(5, zh='+0.5 標準差', en='+0.5σ', col='c5', dash='2 3', w=.9),
           ser(6, zh='−0.5 標準差', en='−0.5σ', col='c4', dash='2 3', w=.9), ser(7, zh='−1 標準差', en='−1σ', col='c4', w=1.1), ser(8, zh='−2 標準差', en='−2σ', col='dn', dash='5 4', w=1.1), ser(2, zh='短期持有者成本', en='STH cost', col='ac', w=2),
           ser(9, hide=1, f='pct1')],
      dz='短期持有者是持有不到 155 天的幣。橘線是他們的平均成本，上下六條線是成本乘上近 4 年「價格 ÷ 成本」的平均加減幾個標準差。', de='Short-term holders are coins held under 155 days. The orange line is their average cost; the six lines around it are that cost times the 4-year mean of price ÷ cost, plus or minus standard deviations.')
    so = o.get('sthosc')   # 2026-11-15 短期震盪（oc_extra.sthosc_viz）：同一個比值改成和最近 140 天比，放在成本帶卡片的第二個檢視
    if so:
        sgn = lambda v, nd=2: (('%+.' + str(nd) + 'f') % v).replace('-', '−'); sym = lambda d_: d_[:7].replace('-', '/'); S_ = so['stats']; sa, sbu, sbe = S_['all'], S_['bull'], S_['bear']
        smk = [dict(d=dn(x['d']), v=x['v'], col='up' if x['bull'] else 'dn', up=0, zh='%s %s' % (sym(x['d']), sgn(x['v'])), en='%s %s' % (x['d'][:7], sgn(x['v']))) for x in so['lows']]
        c_sth['modes'] = [dict(mz='成本帶', me='Cost bands'),
                          dict(mz='短期震盪', me='Short-term swing', hz='短期震盪 · 和最近 %d 天比' % so['window'], he='Short-term swing · against the last %d days' % so['window'], one=0, f='s2', rows=so['rows'], p=2, hero=0, rng=1095,
                               ser=[ser(1, zh='短期震盪', en='Short-term swing', col='c5', w=1.5)],
                               refs=[dict(v=0, col='k2', solid=1), dict(v=1, col='k2'), dict(v=-1, col='k2')], marks=smk,
                               leg=[['k2', '+1 短期過熱、−1 短期超賣', '+1 short-term overheated, −1 short-term oversold', 'dash'], ['up', '牛市段的超賣（最深那天）', 'Oversold in a bull phase (deepest day)', 'ring'], ['dn', '熊市段的超賣', 'Oversold in a bear phase', 'ring']])]
        from say_data import own   # 2026-11-15 切到「短期震盪」時，右邊的讀數換成這個檢視自己的（成本帶的讀數是和 4 年比，不適用）
        sv, lo_ = so['value'], so['now']['lo']; brk = sv <= -1
        c_sth['modes'][1]['say'] = own([
            ('短期震盪', 'Short-term swing', sgn(sv), sgn(sv), 'warn' if brk else 'neu',
             '價格 ÷ 短期持有者成本，和最近 %d 天比偏離 %s 個「%d 倍標準差」。%s，對應價位約 $%s。' % (so['window'], sgn(sv), so['k'], '已經跌破 −1（短期超賣）' if brk else ('還沒跌破 −1' if sv < 0 else '在零上方'), format(lo_, ',')),
             'Price ÷ STH cost sits %s "%d standard deviations" from its %d-day average. %s; −1 corresponds to about $%s.' % (sgn(sv), so['k'], so['window'], 'It has broken below −1 (short-term oversold)' if brk else ('It has not broken −1' if sv < 0 else 'It is above zero'), format(lo_, ','))),
            ('現在是', 'Phase now', '牛市段' if so['bull'] else '熊市段', 'Bull phase' if so['bull'] else 'Bear phase', 'neu',
             '照網站的週期頂底，現在算%s。這個分法是事後才確定的：最近的%s被突破就要改。' % ('牛市段' if so['bull'] else '熊市段', '低點' if so['bull'] else '高點'),
             "By the site's cycle tops and bottoms this is a %s phase. That split is only settled afterwards: if the latest %s breaks, it changes." % ('bull' if so['bull'] else 'bear', 'low' if so['bull'] else 'high')),
            ('跌破 −1 之後 30 天', '30 days after breaking −1', '牛 %d/%d、熊 %d/%d 上漲' % (sbu['up'], sbu['n'], sbe['up'], sbe['n']), 'Up %d/%d bull, %d/%d bear' % (sbu['up'], sbu['n'], sbe['up'], sbe['n']), 'neu',
             '牛市段中位數 %s%%，熊市段中位數 %s%%、之後 30 天內中位數再跌 %s%%。合起來和任何一天差不多。' % (sgn(sbu['med'], 1), sgn(sbe['med'], 1), '%.1f' % abs(sbe['dd'])),
             'Median %s%% in bull phases; %s%% in bear phases, with a median further fall of %s%% within those 30 days. Taken together, about the same as any day.' % (sgn(sbu['med'], 1), sgn(sbe['med'], 1), '%.1f' % abs(sbe['dd'])))],
          '短期震盪 %s，%s（約 $%s）' % (sgn(sv), '已跌破 −1' if brk else '還沒跌破 −1', format(lo_, ',')), 'Short-term swing %s, %s (about $%s)' % (sgn(sv), 'below −1' if brk else 'not yet below −1', format(lo_, ',')))
        c_sth['dz'] += ('「短期震盪」把同一個比值（價格 ÷ 成本）改成和最近 %d 天比：偏離平均幾個「%d 倍標準差」，跌破 −1 是短期超賣，升破 +1 是短期過熱；看的是最近跌得急不急，成本帶看的是四年裡的位置。'
                        '2013 年以來第一次跌破 −1 共 %d 次：牛市段 %d 次，30 天後 %d 次上漲、中位數 %s%%；熊市段 %d 次，30 天後 %d 次上漲、中位數 %s%%，之後 30 天內中位數再跌 %s%%。'
                        '合起來 %d%% 上漲，和任何一天（%d%%）差不多。牛熊用事後才知道的週期頂底來分。只作讀值。'
                        % (so['window'], so['k'], sa['n'], sbu['n'], sbu['up'], sgn(sbu['med'], 1), sbe['n'], sbe['up'], sgn(sbe['med'], 1), ('%.1f' % abs(sbe['dd'])), round(sa['up'] / (sa['n'] or 1) * 100), S_['base']['up']))
        c_sth['de'] += (' "Short-term swing" takes the same ratio (price ÷ cost) against its last %d days: how many "%d standard deviations" it sits from the average. Below −1 is short-term oversold, above +1 short-term overheated; it shows how sharp the recent move was, while the bands show the position within four years. '
                        'Since 2013 it first fell below −1 %d times: %d in bull phases, with price higher 30 days later %d times and a median of %s%%; %d in bear phases, higher %d times with a median of %s%%, and a median further fall of %s%% within those 30 days. '
                        'Taken together price was higher %d%% of the time, about the same as any day (%d%%). Bull and bear are split by cycle tops and bottoms, which are only known afterwards. A reading only.'
                        % (so['window'], so['k'], sa['n'], sbu['n'], sbu['up'], sgn(sbu['med'], 1), sbe['n'], sbe['up'], sgn(sbe['med'], 1), ('%.1f' % abs(sbe['dd'])), round(sa['up'] / (sa['n'] or 1) * 100), S_['base']['up']))
    c_profit = dict(k='profit', zh='短期持有者獲利比例', en='Short-term holders in profit', f='p1', rows=ch['viz']['profit'], kw=1, ph=.4, dom=[0, 100],
      ser=[ser(1, zh='獲利比例', en='In profit', col='c4', fill=1)], refs=[dict(v=50, col='k2'), dict(v=97.5, col='dn', zh='97.5% 賣出線', en='97.5% sell line')], zones=[dict(lo=97.5, hi=100, col='dn', zh='高於 97.5% 賣出線', en='Above the 97.5% sell line', nz='97.5% 賣出線', ne='the 97.5% sell line')],
      leg=[['up', '週 K 收漲', 'Weekly candle up', 'box'], ['dn', '週 K 收跌', 'Weekly candle down', 'box']],
      dz='短期持有者手上的幣，有多少比例現在是賺的。上格是 BTC 週 K（對數刻度）。', de='The share of short-term holder coins currently in profit. Top pane: BTC weekly candles (log scale).')
    # 2026-11-16 使用者看了一張外面的圖（價格線照短期持有者獲利比例上色）後要求加的第二個檢視。比例取近 5 天的平均（資料每 2 天一點，取 3 點），顏色用全站的熱度色階
    try:
        _pp = {r[0]: r[1] for r in ch.get('conc_hist') or []}; _pr = ch['viz']['profit']; _hr = []
        for _i, _r in enumerate(_pr):
            _d = next((_k for _k in (_r[0], _r[0] - 1, _r[0] - 2, _r[0] - 3) if _k in _pp), None); _w = [x[1] for x in _pr[max(0, _i - 2):_i + 1] if x[1] is not None]
            if _d is not None and _w and _i >= 2: _hr.append([_r[0], _pp[_d], round(sum(_w) / len(_w), 1)])
        if len(_hr) > 300 and _hr[-1][0] == _pr[-1][0]:
            c_profit['modes'] = [dict(mz='獲利比例', me='Share'),
                dict(mz='塗在價格上', me='On the price', one=1, kw=0, dom=None, f='usd0', hero=1, hz='短期持有者獲利比例（5 日平均）', he='Short-term holders in profit (5-day average)', rows=_hr, refs=[], zones=[],
                     ser=[ser(1, zh='BTC 價格', en='BTC price', t='ramp', rc=2, heat=1), ser(2, hide=1, f='p1')],
                     leg=[['c3', '幾乎都在賠', 'Almost all at a loss', 'box'], ['up', '一半在賺', 'About half in profit', 'box'], ['ac', '幾乎都在賺', 'Almost all in profit', 'box']])]
            c_profit['dz'] += '「塗在價格上」把同一個比例（近 5 天的平均）變成價格線的顏色：越暖代表越多短期持有者在賺，越冷代表越多在賠。趨勢行情裡可以連續好幾個月都是暖色，暖色不等於頂，冷色也不等於底。只作讀值。'
            c_profit['de'] += ' "On the price" turns the same share (averaged over the last 5 days) into the colour of the price line: warmer means more short-term holders in profit, cooler more at a loss. In a trending market it can stay warm for months, so warm is not a top and cool is not a bottom. A reading only.'
    except Exception as _e: print('profit heat view skipped', _e)
    av = o['aviv']
    c_aviv = dict(k='aviv', zh='價格 ÷ 真實市場均價', en='Price ÷ true market mean', f='x2', rows=av['rows'], p=1, log=1, ser=[ser(2, zh='AVIV', en='AVIV', col='ac', w=1.8)],
      zones=[dict(lo=None, hi=1, col='c4', zh='低於 1', en='Below 1', nz='1 以下', ne='below 1')], refs=[dict(v=1, col='c4')], leg=[['c4', '1 以下', 'Below 1', 'box']],
      marks=[dict(d=dn(t['date']), v=t['value'], col='c5', up=1, zh=yr(t['date']) + ' ' + ('%.2f' % t['value']), en=yr(t['date']) + ' ' + ('%.2f' % t['value'])) for t in av['tops']] +
            [dict(d=dn(t['date']), v=t['value'], col='c4', up=0, zh=yr(t['date']) + ' ' + ('%.2f' % t['value']), en=yr(t['date']) + ' ' + ('%.2f' % t['value'])) for t in av['bottoms']],
      dz='真實市場均價是排除長期不動的幣之後，活躍投資人的平均成本。低於 1 是在成本下方。標記是歷次週期的高點和低點。', de='The true market mean is the average cost of active investors, excluding long-dormant coins. Below 1 means price is under it. Markers show past cycle highs and lows.')
    ru = o['rup']; fl = ru['floor']; nr = ru.get('near') or {}; nh = nr.get('hi')   # 2026-11-11 近地板區（地板以上、37.5% 以下），舊資料沒有這一欄
    c_rup = dict(k='rup', zh='相對未實現獲利', en='Relative unrealized profit', f='p1', rows=ru['rows'], p=1, ser=[ser(2, zh='相對未實現獲利', en='Relative unrealized profit', col='c3', fill=1, w=1.8)],
      zones=[dict(lo=None, hi=fl, col='c4', zh='在地板區', en='In the floor zone', nz='地板區', ne='the floor zone')] + ([dict(lo=fl, hi=nh, col='c5', op=.13, zh='在近地板區', en='In the near-floor zone', nz='近地板區', ne='the near-floor zone')] if nh else []),
      refs=[dict(v=fl, col='c4', zh='地板 %g%%' % fl, en='Floor %g%%' % fl)], leg=[['c4', '地板區（≤ %g%%）' % fl, 'Floor zone (≤ %g%%)' % fl, 'box']] + ([['c5', '近地板區（%g–%g%%）' % (fl, nh), 'Near-floor zone (%g–%g%%)' % (fl, nh), 'box']] if nh else []),
      spans=[dict(a=dn(e['start']), b=dn(e['end']), col='c5', op=.16) for e in nr.get('eps') or []] + [dict(a=dn(e['start']), b=dn(e['end']), col='c4', op=.16) for e in ru['eps']],
      marks=[dict(d=dn(e['min_date']), v=e['min'], col='c4', up=0, zh='%s %.1f%%' % (yr(e['min_date']), e['min']), en='%s %.1f%%' % (yr(e['min_date']), e['min'])) for e in ru['eps']],
      dz='全體持有者帳面上的獲利，佔市值的比例。青色區塊是歷次跌進地板區的期間' + ('，淺黃區塊是近地板區（%g–%g%%）：過去只在熊市後段到復甦初期出現。' % (fl, nh) if nh else '。'),
      de='Paper profit of all holders as a share of market cap. Cyan bands mark past stays in the floor zone' + ('; pale-yellow bands mark the near-floor zone (%g–%g%%), seen only from late bear markets to early recoveries.' % (fl, nh) if nh else '.'))
    cs = ch['conc_stats']; co = ch['cohort']; pr = co['price']
    c_conc = dict(k='conc', zh='籌碼集中度', en='Supply concentration', f='p1', rng=365, rows=[[r[0], r[1], R(r[2], 2)] for r in ch['conc_hist']], p=1, ph=.46, hero=0,
      ser=[ser(2, zh='集中度', en='Concentration', col='c4', fill=1, w=1.6)], refs=[dict(v=cs['p90'], col='c5', zh='前 10%%（%.1f%%）' % cs['p90'], en='top 10%% (%.1f%%)' % cs['p90'])],
      marks=[dict(d=dn(e[0]), v=e[1], col='c5', up=1) for e in cs['episodes']],
      zones=[dict(lo=cs['p90'], hi=None, col='c5', zh='在前 10% 高水位', en='In the top 10%', nz='前 10% 高水位', ne='the top-10% line')],
      hist=dict(w=co['width'], bins=[[r[0], round(r[1]), round(r[2])] for r in co['rows']]), pbox=[(L['chips'].get('flow', {}).get('conc5') or {}).get('lo') or round(pr * .95), (L['chips'].get('flow', {}).get('conc5') or {}).get('hi') or round(pr * 1.05)],
      leg=[['c3', '長期持有者籌碼', 'Long-term holder supply', 'box'], ['ac', '短期持有者籌碼', 'Short-term holder supply', 'box'], ['c4', '現價 ±5% 區間', '±5% of price', 'box'], ['c5', '前 10% 高水位', 'Top-10% line', 'dash']],
      dz='最後一次移動在現價上下 5% 內的幣，佔流通量的比例。上格右邊的橫條是各價位的籌碼：紫是長期持有者、橘是短期持有者。', de='Coins that last moved within 5% of the current price, as a share of supply. The bars at the right of the top pane show supply by price: violet for long-term holders, orange for short-term.')
    ll = o['lthloss']; pk = ll['peaks']
    c_lthloss = dict(k='lthloss', zh='長期持有者虧損比例', en='Long-term holders at a loss', f='p1', rows=ll['rows'], p=2, ser=[ser(1, zh='長期持有者虧損比例', en='LTH supply in loss', col='c4', w=1.5)],
      zones=[dict(lo=42, hi=48, col='dn', zh='在歷輪底部區', en='In the past-bottoms zone', nz='歷輪底部區', ne='the past-bottoms zone')], leg=[['dn', '歷輪底部區 42–48%', 'Past bottoms 42–48%', 'box'], ['dn', '這輪高點', "This cycle's peak", 'dash']],
      marks=[dict(d=dn(p['date']), v=p['value'], col='dn', up=1, zh='%s %.1f%%' % (p['date'][:7].replace('-', '/'), p['value']), en='%s %.1f%%' % (p['date'][:7].replace('-', '/'), p['value'])) for p in pk],
      segs=[dict(a=dn(pk[-1]['date']), v=pk[-1]['value'], col='dn')] if pk else [],
      dz='持有超過 155 天的幣裡，現在帳面虧損的比例。過去幾輪底部都落在 42–48%。', de='The share of coins held over 155 days that are currently at a loss. Past cycle bottoms fell in the 42–48% zone.')
    # ── 賣出的人賺還是賠 ──
    so = ch['viz']['sopr']; KD = dict(easing=('up', '賣壓遞減', 'Easing'), heavier=('dn', '賣壓加重', 'Heavier'), flat=('k2', '持平', 'Flat'))
    def dip(d):
        k = KD.get(d.get('kind'), ('k2', None, None)); return dict(d=d['x'], v=d['sopr'], col=k[0], up=0, zh=k[1], en=k[2])
    c_sopr = dict(k='sopr', zh='短期持有者賣出時的盈虧', en='Short-term holder SOPR', f='n3', rows=so['rows'], p=2, ser=[ser(1, zh='STH-SOPR', en='STH-SOPR', col='c3', w=1.6)],
      zones=[dict(lo=.9, hi=1, col='dn', zh='低於 1，賠錢賣', en='Below 1: selling at a loss', nz='1 以下', ne='below 1')], refs=[dict(v=1, col='k2', zh='1.0＝賣在成本', en='1.0 = selling at cost')], marks=[dip(d) for d in so['dips']],
      leg=[['up', '賣壓遞減', 'Easing', 'ring'], ['dn', '賣壓加重', 'Heavier', 'ring']],
      dz='短期持有者賣出的價格除以買進的價格。低於 1 是賠錢賣。圓圈是每次跌破 1 的低點，和上一次比是加重還是遞減。', de='The price short-term holders sell at, divided by the price they paid. Below 1 means selling at a loss. Circles mark each dip below 1 and whether it was heavier or lighter than the one before.')
    sp = o['sth_pnl']['rows']
    c_pnl = dict(k='pnlr', zh='短期持有者實現獲利與虧損', en='STH realized profit and loss', hz='獲利 ÷ 虧損', he='Profit ÷ loss', f='btc0', rows=[[r[0], r[1], r[2], r[3], R(r[1] / r[2], 3) if r[2] else None] for r in sp], p=3, log=1, hero=2,
      ser=[ser(1, zh='實現獲利', en='Realized profit', col='up', w=1.6), ser(2, zh='實現虧損', en='Realized loss', col='dn', w=1.6), ser(4, hide=1, f='x2')],
      dz='短期持有者當天實現的獲利和虧損（顆，對數刻度）。橘線在綠線上面，就是認賠的比較多。', de='Profit and loss realized by short-term holders each day (BTC, log scale). Orange above green means more loss-taking.')
    cf = o['sthconf']; nb = cf.get('nb', .05)
    c_conf = dict(k='conf', zh='對趨勢的信心', en='Confidence in the trend', f='n3', rows=cf['rows'], p=1, ph=.38, minr=.15,
      top=[ser(2, zh='賣出的人的成本', en='Cost of coins sold', col='c3'), ser(3, zh='還在持有的人的成本', en='Cost of coins still held', col='ac')],
      ser=[ser(4, zh='信心', en='Confidence', t='bar', nb=nb, mid='c5')], zones=[dict(lo=-nb, hi=nb, col='c5')],
      leg=[['up', '偏有信心（≥ +%g）' % nb, 'Confident (≥ +%g)' % nb, 'box'], ['dn', '信心不足（≤ −%g）' % nb, 'Lacking confidence (≤ −%g)' % nb, 'box'], ['c5', '轉換期', 'Transition', 'box']],
      dz='短期持有者這 7 天賣出的幣的成本，和他們整體成本的差，除以收盤。上格兩條線就是這兩個成本。', de='Cost of the coins short-term holders sold in 7 days, minus their overall cost, divided by the close. The two lines in the top pane are those two costs.')
    npl = o['npl']; c30 = npl['cum30']
    c_npl = dict(k='npl', zh='淨實現損益', en='Net realized P&L', f='usdM', wide=1,   # 整排寬（2026-11-12 使用者：「這個圖需要比較寬的空間顯示」）：上格價格線上有圓圈、下格是每日柱子，半寬時 180 天擠在一起
       dz='全網每天實現的獲利減掉虧損。上格價格線上的圓圈大小是當天的金額。可以切換成 30 日累計。', de='Network-wide profit realized each day minus losses. Bubbles on the price line are sized by that day\'s amount. Switch to the 30-day total for the longer view.',
      modes=[dict(mz='每日', me='Daily', rng=180, rows=npl['rows'], p=1, sym=1, bub=dict(c=2, rank=3), ser=[ser(2, zh='每日淨實現損益', en='Daily net realized P&L', t='bar')],
                  leg=[['up', '淨獲利', 'Net profit', 'box'], ['dn', '淨認賠', 'Net loss', 'box']]),
             dict(mz='30 日累計', me='30-day total', rng=1460, rows=[list(r_) + [None if r_[3] is None else round(-4 * r_[3], 3)] for r_ in c30['rows']], p=1, hero=2, f='ps2',
                  ser=[ser(2, zh='30 日累計 ÷ 市值', en='30-day total ÷ market cap', t='bar'), ser(3, zh='認賠分界線：之前 4 年最大 30 日淨獲利 × −1/4', en='Loss line: −¼ × prior 4-year max 30-day net profit', col='dn', w=1.2), ser(6, zh='獲利分界線：之前 4 年最大 30 日淨獲利', en='Profit line: prior 4-year max 30-day net profit', col='up', w=1.2), ser(4, hide=1, f='usdM')],
                  marks=[dict(d=t['x'], v=t['price'], on='p', col='ac', up=1, zh=t['date'][:7], en=t['date'][:7]) for t in c30['trig']],
                  leg=[['up', '30 日累計淨獲利', '30-day net profit', 'box'], ['dn', '30 日累計淨認賠', '30-day net loss', 'box'], ['ac', '首次觸發', 'First trigger', 'ring']])])
    n3 = o['npl365']; wan = lambda v: ('+' if v > 0 else '−') + ('%.0f' % abs(v / 10))
    c_n365 = dict(k='npl365', zh='一年累計淨實現損益', en='One-year net realized P&L', f='kbtc', rows=n3['rows'], p=1,
      ser=[ser(2, zh='一年累計', en='One-year sum', t='sign', base=0)], leg=[['up', '獲利了結', 'Profit-taking', 'box'], ['dn', '認賠', 'Loss-taking', 'box']],
      marks=[dict(d=dn(t['date']), v=t['value'], col='up', up=1, zh=yr(t['date']) + ' ' + wan(t['value']) + ' 萬', en=yr(t['date']) + ' ' + ('%+.0fK' % t['value'])) for t in n3['tops']] +
            [dict(d=dn(t['date']), v=t['value'], col='dn', up=0, zh=yr(t['date']) + ' ' + wan(t['value']) + ' 萬', en=yr(t['date']) + ' ' + ('%+.0fK' % t['value'])) for t in n3['bottoms']],
      dz='把每天的淨實現損益換成顆數，加總 365 天。標記是歷次的高點和低點。', de='Daily net realized P&L converted to BTC and summed over 365 days. Markers show past highs and lows.')
    # ── 賣壓強弱與衰竭 ──
    rp = o['rpl']
    c_rpl = dict(k='rpl', zh='實現獲利 ÷ 虧損', en='Realized profit ÷ loss', f='x2', rows=rp['rows'], p=2, log=1, ser=[ser(1, zh='獲利 ÷ 虧損', en='Profit ÷ loss', t='split', base=1, w=1.6)],
      refs=[dict(v=1, col='ink', solid=1)], spans=[dict(a=dn(e['start']), b=dn(e['end']), col='dn', op=.12, below=1) for e in rp['reds']],
      leg=[['up', '1 以上（獲利了結較多）', 'Above 1 (more profit-taking)', 'line'], ['dn', '1 以下（認賠較多）', 'Below 1 (more loss-taking)', 'line']],
      dz='全網 90 天平均的實現獲利，除以實現虧損。橘底是歷次跌到 1 以下的期間。', de='The 90-day average of network realized profit divided by realized loss. Orange bands mark past stays below 1.')
    y1 = o.get('rpl365')
    if y1:   # 2026-11-17 使用者要求：多一個一年的檢視（oc_extra.rpl365_viz，Bitview，合計相除）
        yl = lambda d_: d_[:7].replace('-', '/')
        c_rpl['modes'] = [dict(mz='90 天', me='90 days'),
                          dict(mz='一年', me='One year', src='Bitview · {d}', rows=y1['rows'], p=2, dom=[.2, 10], ser=[ser(1, zh='一年合計獲利 ÷ 虧損', en='One-year profit ÷ loss', t='split', base=1, w=1.6)],
                               refs=[dict(v=1, col='ink', solid=1)] + ([dict(v=y1['conf_at'], a=dn(y1['since']), nt=1, col='up', zh='%.2f 回升 10%%＝底部確認' % y1['conf_at'] if not y1['confirmed'] else '%.2f 已回升 10%%' % y1['conf_at'], en='%.2f a 10%% turn up = bottom confirmed' % y1['conf_at'] if not y1['confirmed'] else '%.2f turned up 10%%' % y1['conf_at'])] if y1['below'] and y1.get('conf_at') else []),   # 2026-11-17 使用者要「回升 10%」確認線：這一段最低點 × 1.1，最低點再往下，線也跟著往下
                               spans=[dict(a=dn(e['start']), b=dn(e['end']), col='dn', op=.12, below=1) for e in y1['reds']],
                               marks=[dict(d=dn(e['low_date']), v=e['low'], col='dn', up=0, zh='%s %.2f' % (yl(e['low_date']), e['low']), en='%s %.2f' % (e['low_date'][:7], e['low'])) for e in y1['reds'] if not e.get('open')],
                               leg=[['up', '1 以上（一年獲利較多）', 'Above 1 (more profit over the year)', 'line'], ['dn', '1 以下（一年認賠較多）', 'Below 1 (more loss over the year)', 'line'], ['dn', '每段的最低點', 'Low of each spell', 'ring']],
                               dz='全網一年合計的實現獲利，除以一年合計的實現虧損（Bitview）。橘底是歷次跌到 1 以下的期間，標記是每段比值最低的那天。' + ('綠色虛線是這一段（%s 起）的確認線：比值從這一段最低點回升 10%%；最低點再往下，線也跟著往下。' % ('%d/%d' % tuple(int(x) for x in y1['since'][5:].split('-'))) if y1['below'] else ''),
                               de='Network realized profit summed over a year, divided by realized loss summed over the same year (Bitview). Orange bands mark past stays below 1; markers show the low of each spell.' + (' The green dashed line, drawn from the start of this spell, is its confirmation level: the ratio 10% off its low; it moves down if the low does.' if y1['below'] else ''))]
        if y1.get('past_low') and y1.get('conf_gain'):   # 2026-11-17 運營回報：切到「一年」時結論句還是 90 天的，和大數字對不上；這個檢視有自己的結論和證據（同 ㉞-9 的版面）
            from say_data import own
            from reads import md as md_, mde as mde_
            v, pl, cg, r_, b_ = y1['value'], y1['past_low'], y1['conf_gain'], y1['r365'], y1['base365']
            sgp = lambda x: ('+' if x > 0 else '−') + '%.0f%%' % abs(x)
            if not y1['below']:
                vt, vz, ve, wz, we = 'neu', '不在底部區', 'Not in the bottom zone', '一年合計獲利多於認賠。', 'Over a year, profit outweighs loss.'
                cz, ce = '跌回 1 以下', 'A drop back below 1'
                sz = '一年合計 %.2f，獲利多於認賠：不在過去週期的底部區。' % v; se = 'One-year profit ÷ loss is %.2f: profit outweighs loss, so this is not the zone where past cycles bottomed.' % v
            elif y1['confirmed']:
                vt, vz, ve, wz, we = 'up', '底部確認', 'Bottom confirmed', '比值已從這段最低點回升 10%%，過去 %d/%d 次之後價格沒再破底。' % (y1['conf_ok'], y1['conf_n']), 'The ratio is 10%% off this spell\'s low; in %d of %d past cases price never made a new low afterwards.' % (y1['conf_ok'], y1['conf_n'])
                cz, ce = '價格跌破這段的最低價', "Price breaking this spell's low"
                sz = '一年合計 %.2f，比值已從最低點回升 10%%：照過去，底已經過了。' % v; se = 'One-year profit ÷ loss is %.2f and 10%% off its low: in past cycles, the bottom was already in by now.' % v
            else:
                vt, vz, ve = 'neu', '底部區、未確認', 'Bottom zone, unconfirmed'
                wz = '一整年認賠多於獲利，過去都是週期底部區；但比值還沒從低點回升，底還沒確認。'; we = 'A full year of more loss than profit has always meant a cycle bottom zone, but the ratio has not turned up from its low yet.'
                cz, ce = '比值回升到 %.2f（最低點 %.2f 的 10%% 以上）' % (y1['conf_at'], y1['cur_low']), 'The ratio rising to %.2f (10%% above its %.2f low)' % (y1['conf_at'], y1['cur_low'])
                sz = '一年合計 %.2f，%s 起低於 1：落在過去週期的底部區，但比值還在最低點、還沒回升，底還沒確認。' % (v, md_(y1['since']))
                se = 'One-year profit ÷ loss is %.2f, below 1 since %s: the zone where past cycles bottomed, but the ratio has not turned up from its low, so no bottom is confirmed yet.' % (v, mde_(y1['since']))
            my = own([('一年合計', 'One-year sum', '%.2f' % v, '%.2f' % v, 'down' if y1['below'] else 'up',
                       ('%s 跌破 1（當天 $%.1fK），已 %d 天、價格 %s；過去四段最低 %.2f–%.2f。' % (md_(y1['since']), y1['since_price'] / 1000, y1['since_days'], sgp(y1['chg']), pl[0], pl[1])) if y1['below'] else ('在 1 以上；過去四段低於 1 時最低 %.2f–%.2f。' % tuple(pl)),
                       ('Below 1 since %s (at $%.1fK), %d days, price %s; past spells bottomed at %.2f–%.2f.' % (mde_(y1['since']), y1['since_price'] / 1000, y1['since_days'], sgp(y1['chg']), pl[0], pl[1])) if y1['below'] else ('Above 1; past spells below 1 bottomed at %.2f–%.2f.' % tuple(pl))),
                     ] + ([('最近 7 天合計', 'Last 7 days', '%.2f' % y1['s7'], '%.2f' % y1['s7'], 'down' if y1['s7'] < 1 else 'up',
                        '最近 7 天合計的實現獲利是虧損的 %.2f 倍，30 天合計 %.2f%s。' % (y1['s7'], y1['s30'], '：認賠還在加重' if y1['s7'] < y1['s30'] < 1 else ''),
                        'Over the last 7 days realized profit was %.2f times realized loss; %.2f over 30 days%s.' % (y1['s7'], y1['s30'], ': loss-taking is still building' if y1['s7'] < y1['s30'] < 1 else ''))] if y1.get('s7') and y1.get('s30') else [])
                     + ([(lambda nr, cu: ('跌破 1 和價格底', 'Cross vs price low', '前 %d～後 %d 天' % (-nr['gap'][0], nr['gap'][1]) if nr['gap'][0] < 0 else '後 %d–%d 天' % tuple(nr['gap']),
                        ('%+d to %+d days' % tuple(nr['gap'])).replace('-', '−'), 'neu',
                        '過去 %d 次週期底，價格最低點在跌破 1 前 %d 天到後 %d 天之間，從跌破當天算最多再跌 %.0f%%；比值自己的最低點又晚約 %d–%d 個月（價格都用每日收盤價）。' % (nr['n'], -min(nr['gap'][0], 0), nr['gap'][1], -nr['dd'], round(nr['rgap'][0] / 30.4), round(nr['rgap'][1] / 30.4))
                        + (('這次收盤最低的 $%.1fK 在 %s，%s；跌破後收盤最多跌 %.0f%%，%s' % (cu['near_price'] / 1000, md_(cu['near']), ('比跌破早 %d 天' % -cu['near_gap']) if cu['near_gap'] < 0 else ('跌破後 %d 天' % cu['near_gap']), -cu['dd'],
                             {(1, 1): '兩項都超出過去範圍。', (1, 0): '時間超出過去範圍。', (0, 1): '跌幅超出過去範圍。', (0, 0): '都還在過去範圍內。'}[(int(not nr['gap'][0] <= cu['near_gap'] <= nr['gap'][1]), int(cu['dd'] < nr['dd']))])) if cu else ''),
                        'At the past %d cycle bottoms, the price low came between %d days before and %d days after the ratio fell below 1, at most %.0f%% under the price on the day it crossed; the ratio\'s own low came about %d–%d months later still (daily closing prices throughout).' % (nr['n'], -min(nr['gap'][0], 0), nr['gap'][1], -nr['dd'], round(nr['rgap'][0] / 30.4), round(nr['rgap'][1] / 30.4))
                        + ((' This time the lowest close of $%.1fK was on %s, %s; since the cross the close has fallen as much as %.0f%%: %s' % (cu['near_price'] / 1000, mde_(cu['near']), ('%d days before the cross' % -cu['near_gap']) if cu['near_gap'] < 0 else ('%d days after the cross' % cu['near_gap']), -cu['dd'],
                             {(1, 1): 'both outside the past range.', (1, 0): 'the timing is outside the past range.', (0, 1): 'the drop is outside the past range.', (0, 0): 'both still inside the past range.'}[(int(not nr['gap'][0] <= cu['near_gap'] <= nr['gap'][1]), int(cu['dd'] < nr['dd']))])) if cu else '')))(
                        y1['near'], y1['reds'][-1] if y1['reds'] and y1['reds'][-1].get('open') else None)] if y1.get('near') else []) + [
                      ('回升 10% 之後', 'After a 10% turn up', '%d / %d 沒再破底' % (y1['conf_ok'], y1['conf_n']), '%d / %d no new low' % (y1['conf_ok'], y1['conf_n']), 'neu',
                       '比值從段內最低點回升 10%% 之後，過去每次價格都沒再跌破之前的最低價；但那時價格已比最低價高 %.0f–%.0f%%，確認來得晚。' % (cg[0], cg[1]),
                       'After the ratio rose 10%% off its low, price never broke its prior low in any past case; but by then price was already %.0f–%.0f%% above that low, so the confirmation comes late.' % (cg[0], cg[1])),
                      ('一年低於 1 之後', 'After a year below 1', '%d / %d 上漲' % (r_['up'], r_['n']), '%d / %d up' % (r_['up'], r_['n']), 'neu',
                       '比值最低那天之後一年，中位數 %s（任一天 %s）。只有 4 段，只作讀值。' % (sgp(r_['med']), sgp(b_['med'])),
                       'A year after the ratio\'s low: median %s (any day %s). Only four spells; a reading, not a signal.' % (sgp(r_['med']), sgp(b_['med'])))], sz, se)
            my['items'].insert(0, dict(kz='我們的看法', ke='Our view', vz=vz, ve=ve, tone=vt, dz=wz, de=we, cz=cz, ce=ce, view=1, hm='', hme=''))
            c_rpl['modes'][1]['say'] = my
        w9 = y1.get('w90')
        if w9 and y1.get('s7') and c_rpl['modes'][1].get('say'):
            # 2026-11-20 使用者（運營轉來截圖）：打開看到 90 天平均 2.28、綠色「在 1 以上 73 天」，判讀卻是偏空（最近 7 天 0.17、一年合計 1 以下），讀者會以為獲利的比認賠的多。
            #   1 打開改成「一年」（和判讀、運營長文一致）：卡片本身換成一年的資料，c._m＝1；檢視順序不動，分享連結的 m＝0／1 意思照舊
            #   2「90 天」改成 Bitview 合計相除（原本 CheckOnChain 每日比值取平均，單日極端值把它拉到 2.28，合計相除 1.32）
            #   3 兩個檢視的讀數都帶最近 7 天合計
            ym = c_rpl['modes'][1]; from say_data import own as own_
            v9, s7, s30 = w9['value'], y1['s7'], y1['s30']
            sx9 = '%d/%d' % tuple(int(x) for x in w9['since'][5:].split('-'))
            if v9 < 1: vt9, vz9, ve9, wz9, we9, cz9, ce9 = 'down', '認賠多於獲利', 'Losses outweigh profits', '90 天合計低於 1。', 'The 90-day sum is below 1.', '回到 1 以上', 'A move back above 1'
            elif s7 < 1: vt9, vz9, ve9, wz9, we9, cz9, ce9 = 'down', '短期轉弱', 'Weakening near term', '90 天合計還在 1 以上，但最近 7 天認賠多於獲利。', 'Still above 1 over 90 days, but losses led over the last 7.', '7 天合計回到 1 以上', 'The 7-day sum back above 1'
            else: vt9, vz9, ve9, wz9, we9, cz9, ce9 = 'up', '獲利多於認賠', 'Profits outweigh losses', '90 天和最近 7 天合計都在 1 以上。', 'Above 1 over both 90 days and the last 7.', '7 天合計跌回 1 以下', 'The 7-day sum falling below 1'
            sy9 = own_([('90 天合計', '90-day sum', '%.2f' % v9, '%.2f' % v9, 'up' if v9 >= 1 else 'down',
                         ('%s 起在 1 以上（%d 天）；10 天前是 %.2f。' if w9['above'] else '%s 起低於 1（%d 天）；10 天前是 %.2f。') % (sx9, w9['since_days'], w9['v10']),
                         ('Above 1 since %s (%d days); %.2f ten days ago.' if w9['above'] else 'Below 1 since %s (%d days); %.2f ten days ago.') % (mde_(w9['since']), w9['since_days'], w9['v10'])),
                        ('最近 7 天合計', 'Last 7 days', '%.2f' % s7, '%.2f' % s7, 'down' if s7 < 1 else 'up', '30 天合計 %.2f。' % s30, '%.2f over 30 days.' % s30)],
                       ('90 天合計 %.2f，%s，但最近 7 天只有 %.2f：認賠在追上獲利。' % (v9, '還在 1 以上' if v9 >= 1 else '已經低於 1', s7)) if s7 < 1 <= v9 else '90 天合計 %.2f，最近 7 天 %.2f。' % (v9, s7),
                       ('The 90-day sum is %.2f, still above 1, but only %.2f over the last 7 days: losses are catching up with profits.' % (v9, s7)) if s7 < 1 <= v9 else 'The 90-day sum is %.2f; %.2f over the last 7 days.' % (v9, s7))
            sy9['items'].insert(0, dict(kz='我們的看法', ke='Our view', vz=vz9, ve=ve9, tone=vt9, dz=wz9, de=we9, cz=cz9, ce=ce9, view=1, hm='', hme=''))
            from reads import HOW as HOW_
            for y_ in (sy9, ym['say']): y_['hz'], y_['he'] = list((HOW_.get('rpl') or {}).get('hz') or []), list((HOW_.get('rpl') or {}).get('he') or [])
            v90 = dict(mz='90 天', me='90 days', src='Bitview · {d}', rows=w9['rows'], p=2, dom=None, marks=[], ser=[ser(1, zh='90 天合計獲利 ÷ 虧損', en='90-day profit ÷ loss', t='split', base=1, w=1.6)],
                       refs=[dict(v=1, col='ink', solid=1)], spans=[dict(a=dn(e['start']), b=dn(e['end']), col='dn', op=.12, below=1) for e in w9['reds']],
                       leg=[['up', '1 以上（獲利了結較多）', 'Above 1 (more profit-taking)', 'line'], ['dn', '1 以下（認賠較多）', 'Below 1 (more loss-taking)', 'line']],
                       dz='全網 90 天合計的實現獲利，除以 90 天合計的實現虧損（Bitview）。用合計相除：單日比值可以到 20 倍，每日比值直接平均會被少數幾天拉高。橘底是歷次跌到 1 以下的期間。',
                       de='Network realized profit summed over 90 days, divided by realized loss summed over the same 90 days (Bitview). Sums are divided rather than daily ratios averaged: a single day can reach 20x, and an average of daily ratios gets pulled up by a few days. Orange bands mark past stays below 1.',
                       say=sy9)
            for k_ in ('rows', 'p', 'dom', 'ser', 'refs', 'spans', 'marks', 'leg', 'dz', 'de', 'say'): c_rpl[k_] = ym[k_]
            lw = [x for x in y1.get('lows') or [] if x.get('px')]
            if lw:   # 2026-11-20 使用者（運營轉來）：「價格低點的垂直線也按照運營配圖那樣在圖上畫出來」：灰色虛線貫穿上下兩格，價格和比值上各一顆點，比值旁寫當天的值
                lyz = lambda d_: '%s/%d' % (d_[:4], int(d_[5:7])); lye = lambda d_: d_[:7]
                def lmk(col_):
                    return ([dict(d=dn(x['d']), v=x['px'], on='p', col='k2', up=0) for x in lw] +
                            [dict(d=dn(x['d']), v=x[col_], col='k2', up=1, zh='%s 價格低點 %.2f' % (lyz(x['d']), x[col_]), en='%s price low %.2f' % (lye(x['d']), x[col_])) for x in lw if x.get(col_)])
                lvl = [dict(d=dn(x['d']), col='k2', dash='5 4', op=.75) for x in lw]
                lleg = ['k2', '週期價格低點（收盤）', 'Cycle price lows (close)', 'dash']
                c_rpl['marks'] = c_rpl['marks'] + lmk('y1'); c_rpl['vl'] = lvl; c_rpl['leg'] = c_rpl['leg'] + [lleg]
                v90.update(marks=lmk('r90'), vl=lvl, leg=v90['leg'] + [lleg])
            wh = y1.get('w180')
            if wh and wh.get('zones'):   # 2026-11-20 使用者：「加到卡片上」：半年＋30 天同時很低（oc_extra.H_LO／H_S30）。三個檢視的證據都加一條，另外多一個「半年」檢視
                zs = wh['zones']; dz_ = [z for z in zs if not z.get('open')] or zs
                ym_ = lambda d_: '%s/%d' % (d_[:4], int(d_[5:7]))
                lz = (min(z['lead'] for z in zs), max(z['lead'] for z in zs)); dd_ = (min(-z['dd'] for z in zs), max(-z['dd'] for z in zs)); cur = zs[-1]
                r1 = [z['r365'] for z in zs if z.get('r365') is not None]
                zi = dict(kz='半年＋30 天同時很低', ke='Half-year and 30-day both low', vz='%d 段都在低點前' % len(zs), ve='%d spells, all before a low' % len(zs), tone='neu',
                          dz='半年合計低於 %.1f、同時 30 天合計低於 %.1f：%s 年起每輪只亮一段（%s），價格最低點都在第一次亮起後 %d–%d 天，亮起後價格還再跌 %.0f–%.0f%%%s。現在半年 %.2f、30 天 %.2f，%s。' % (
                              wh['lo'], wh['s30_lo'], zs[0]['start'][:4], '、'.join(ym_(z['start']) for z in zs), lz[0], lz[1], dd_[0], dd_[1],
                              '；一年後 %d 次都漲（%s）' % (len(r1), '、'.join('%+.0f%%' % x for x in r1)) if r1 and all(x > 0 for x in r1) else '', wh['value'], wh['s30'], '正在區間裡' if wh['on'] else '不在區間'),
                          de='Half-year sum below %.1f while the 30-day sum is below %.1f: since %s it lit once per cycle (%s); the price low came %d–%d days after the first day, and price still fell %.0f–%.0f%% after it%s. Now the half-year sum is %.2f and the 30-day %.2f: %s.' % (
                              wh['lo'], wh['s30_lo'], zs[0]['start'][:4], ', '.join(z['start'][:7] for z in zs), lz[0], lz[1], dd_[0], dd_[1],
                              '; a year later price was up every time (%s)' % ', '.join('%+.0f%%' % x for x in r1) if r1 and all(x > 0 for x in r1) else '', wh['value'], wh['s30'], 'inside the zone' if wh['on'] else 'outside the zone'),
                          cz='', ce='', view=0, hm='', hme='')
                for y_ in (c_rpl['say'], v90['say']): y_['items'].append(dict(zi))
                if wh['on']: vth, vzh, veh, wzh, weh, czh, ceh = 'neu', '低點附近', 'Near a low', '半年和 30 天合計同時很低，過去都落在週期價格低點前後；但亮起後價格還再跌過 %.0f–%.0f%%。' % dd_, 'Both sums are low at once, which has always come around a cycle price low; but price fell another %.0f–%.0f%% after it lit in the past.' % dd_, '30 天合計回到 %.1f 以上' % wh['s30_lo'], 'The 30-day sum back above %.1f' % wh['s30_lo']
                else: vth, vzh, veh, wzh, weh, czh, ceh = 'neu', '不在低點區間', 'Not in the low zone', '半年和 30 天合計沒有同時很低；過去週期價格低點前後都會同時很低。', 'The two sums are not low at the same time; around past cycle price lows they always were.', '半年跌破 %.1f 且 30 天跌破 %.1f' % (wh['lo'], wh['s30_lo']), 'Half-year below %.1f and 30-day below %.1f' % (wh['lo'], wh['s30_lo'])
                syh = own_([('半年合計', 'Half-year sum', '%.2f' % wh['value'], '%.2f' % wh['value'], 'up' if wh['value'] >= 1 else 'down', '門檻 %.1f。' % wh['lo'], 'Threshold %.1f.' % wh['lo']),
                            ('30 天合計', '30-day sum', '%.2f' % wh['s30'], '%.2f' % wh['s30'], 'up' if wh['s30'] >= 1 else 'down', '門檻 %.1f；最近 7 天 %.2f。' % (wh['s30_lo'], s7), 'Threshold %.1f; %.2f over the last 7 days.' % (wh['s30_lo'], s7))],
                           ('半年合計 %.2f、30 天合計 %.2f，%s：過去週期的價格低點前後，兩個都會同時很低。' % (wh['value'], wh['s30'], '同時很低' if wh['on'] else '沒有同時很低')),
                           ('The half-year sum is %.2f and the 30-day %.2f, %s: around past cycle price lows both were low at once.' % (wh['value'], wh['s30'], 'both low' if wh['on'] else 'not both low')))
                syh['items'].insert(0, dict(kz='我們的看法', ke='Our view', vz=vzh, ve=veh, tone=vth, dz=wzh, de=weh, cz=czh, ce=ceh, view=1, hm='', hme=''))
                syh['items'].append(dict(zi)); syh['hz'], syh['he'] = list(c_rpl['say'].get('hz') or []), list(c_rpl['say'].get('he') or [])
                vh = dict(mz='半年', me='Half year', o=1, src='Bitview · {d}', rows=wh['rows'], p=2, dom=None, marks=lmk('r180') if lw else [], vl=lvl if lw else [],
                          ser=[ser(1, zh='半年合計獲利 ÷ 虧損', en='Half-year profit ÷ loss', t='split', base=1, w=1.6), ser(3, zh='30 天合計', en='30-day sum', col='k2', w=.9)],
                          refs=[dict(v=1, col='ink', solid=1), dict(v=wh['lo'], col='c3', zh='半年 %.1f' % wh['lo'], en='Half-year %.1f' % wh['lo']), dict(v=wh['s30_lo'], col='k2', zh='30 天 %.1f' % wh['s30_lo'], en='30-day %.1f' % wh['s30_lo'])],
                          spans=[dict(a=dn(z['start']), b=dn(z['end']), col='c3', op=.2) for z in zs],
                          leg=[['up', '1 以上', 'Above 1', 'line'], ['dn', '1 以下', 'Below 1', 'line'], ['c3', '兩個同時很低', 'Both low at once', 'box']] + ([lleg] if lw else []),
                          dz='全網半年（180 天）合計的實現獲利，除以同期合計的實現虧損（Bitview），細線是 30 天合計。青綠底是兩個同時很低的期間（半年 < %.1f、30 天 < %.1f），過去每輪只亮一段，都在週期價格低點前後；門檻是看過歷史才定的，只有 %d 段，只作讀值。' % (wh['lo'], wh['s30_lo'], len(zs)),
                          de='Network realized profit summed over half a year (180 days), divided by realized loss over the same period (Bitview); the thin line is the 30-day sum. Teal bands mark when both were low at once (half-year < %.1f, 30-day < %.1f): once per cycle in the past, always around a cycle price low. The thresholds were set after looking at history and there are only %d spells: a reading, not a signal.' % (wh['lo'], wh['s30_lo'], len(zs)),
                          say=syh)

            c_rpl['src'] = 'Bitview · {d}'
            c_rpl['modes'] = [v90, dict(mz='一年', me='One year', src='Bitview · {d}')]
            c_rpl['_m'] = 1
            if wh and wh.get('zones'): c_rpl['modes'][0]['o'], c_rpl['modes'][1]['o'] = 0, 2; c_rpl['modes'].append(vh)   # 檢視順序：90 天、半年、一年（m＝0／1 的意思不變，半年是 m＝2）
        else:
          c_rpl['dz'] = '全網 90 天平均的實現獲利，除以實現虧損（CheckOnChain，每日比值取平均）。橘底是歷次跌到 1 以下的期間。「一年」改用一年合計相除，看的是整個週期的位置。'
          c_rpl['de'] = 'The 90-day average of network realized profit divided by realized loss (CheckOnChain, daily ratios averaged). Orange bands mark past stays below 1. "One year" divides one-year sums instead and shows where the cycle stands.'
    rl = o['rloss']; LK = dict(div=('c4', '', '背離', 'Divergence'), cap=('c5', '5 4', None, None)); LK['break'] = ('dn', '5 4', '打破', 'Broken')
    def links(lst, va, vb):
        lst = [x for x in lst if x['kind'] in LK]; out = []; lab = [x for x in lst if x['kind'] != 'cap'][-3:]
        for x in lst:
            k = LK[x['kind']]; z, e = k[2], k[3]
            if x['kind'] == 'div' and x.get('step', 1) >= 2: z, e = '二次背離', '2nd divergence'
            if z and not x.get('conf', True): z, e = z + '（暫定）', e + '?'
            out.append(dict(a=dn(x['a']), b=dn(x['b']), pa=x['pa'], pb=x['pb'], va=x[va], vb=x[vb], col=k[0], dash=k[1], zh=z if x in lab else None, en=e if x in lab else None))
        return out
    c_rloss = dict(k='rloss', zh='每日實現虧損', en='Daily realized loss', f='usdM', dz='每天賠錢賣出的金額。連線是價格和認賠金額的關係：價格更低、認賠卻更少，叫背離。', de='The dollar amount sold at a loss each day. Lines link price lows and loss peaks: a lower price with smaller losses is a divergence.',
      modes=[dict(mz='近 150 天', me='Last 150 days', rows=rl['rows'], p=1, ser=[ser(2, zh='每日實現虧損（百萬美元）', en='Daily realized loss ($M)', t='bar', col='dn', flag=4)], links=links(rl['chain'], 'ua', 'ub'),
                  leg=[['k2', '搬家日', 'Internal-transfer day', 'box'], ['c4', '背離', 'Divergence', 'line'], ['dn', '背離被打破', 'Divergence broken', 'dash'], ['c5', '認賠放大', 'Loss grows', 'dash']]),
             dict(mz='全部歷史', me='Full history', rows=rl['hist'], p=1, tf='sqrt', f='bp', ser=[ser(2, zh='實現虧損 ÷ 市值', en='Realized loss ÷ market cap', col='dn', fill=1, w=1.1)], links=links(rl['hlinks'], 'ra', 'rb'),
                  leg=[['c4', '背離', 'Divergence', 'line'], ['dn', '背離被打破', 'Divergence broken', 'dash'], ['c5', '認賠放大', 'Loss grows', 'dash']])])
    cp_ = rl.get('cap')
    if cp_ and cp_.get('rows'):   # 2026-11-18 使用者要求（Glassnode 週報那張「虧損到了只有週期低點才見過的程度」，見 oc_extra._rl_cap）：第三個檢視，用一年的獲利當分母
        bk = cp_['back']; r6, r18, d18 = bk['r60'], bk['r180'], bk['dd180']; ymz = lambda d: d[:7].replace('-', '/')
        sg = lambda v: ('%+.0f%%' % v).replace('-', '−')
        now_z = ('現在 %.1f，超過門檻 %.1f' % (cp_['v'], cp_['q']) + ('，是 %s 以來最高' % ymz(cp_['hi_since']) if cp_.get('hi_since') else '，是有資料以來最高')) if cp_['above'] else '現在 %.1f，在門檻 %.1f 以下' % (cp_['v'], cp_['q'])
        now_e = ('Now %.1f, above the %.1f line' % (cp_['v'], cp_['q']) + (', the highest since %s' % ymz(cp_['hi_since']) if cp_.get('hi_since') else ', the highest on record')) if cp_['above'] else 'Now %.1f, below the %.1f line' % (cp_['v'], cp_['q'])
        c_rloss['modes'].append(dict(mz='÷ 一年獲利', me='÷ 1-year profit', rows=[r + ([1, -round(r[2] - r[3], 1)] if r[2] > r[3] else [0, None]) for r in cp_['rows']], bub=dict(c=5, rank=6, r=7),   # 2026-11-25 使用者「要，標紅」：第 4 欄＝當天超過門檻，上格價格線那幾段畫成紅色；第 5 欄給價格上的紅點（大小＝超過門檻多少，最大半徑 7；畫圖照正負上色，存成負值才是紅色），照 Glassnode 那張的價格標紅
          p=1, tf='sqrt', f='bp', rng=0, hz='7 日平均 ÷ 一年獲利（萬分之／天）', he='7-day average ÷ 1-year profit (bp per day)',
          ser=[ser(2, zh='虧損 ÷ 一年獲利', en='Loss ÷ 1-year profit', col='dn', fill=1, w=1.1, cc=4, cols={1: 'dn'}), ser(3, zh='門檻：歷史第 95 百分位', en='Line: 95th percentile to date', col='k2', dash='4 3', w=1)],
          marks=[dict(d=dn(e['peak']), v=e['peak_v'], col='dn', up=1, zh=ymz(e['peak']), en=ymz(e['peak'])) for e in cp_['eps'] if e['peak_v'] >= 90 or e is cp_['eps'][-1] or e['peak'] >= '2022-01-01'],
          leg=[['dn', '價格上的紅點：超過門檻的日子（越大超過越多）', 'Red dots on price: days above the line (bigger = further above)', 'ring']],
          dz='7 天平均的每日實現虧損，除以過去一年的實現獲利合計，單位是萬分之（每天）。用一年的獲利當分母，不同年代可以放在同一把尺上比：超過虛線（到當天為止的歷史第 95 百分位）代表認賠的規模，大到只有過去幾次低點附近才見過，上格價格上的紅點就是這些日子，點越大超過門檻越多。%s。'
             '2014 年起超過 %d 次：60 天後 %d 次較高，中位數 %s；180 天後 %d 次較高，中位數 %s，但這 180 天內中途最深的回落中位數 %s，熊市裡的幾次（2018/02、2019/09、2022/05、2022/06）之後還跌了 18%% 到 39%%。資料是 Bitview，不是實體調整。只作讀值。' % (
              now_z, cp_['n'], r6['up'], sg(r6['med']), r18['up'], sg(r18['med']), sg(d18['med'])),
          de='The 7-day average of daily realized loss divided by realized profit over the past year, in basis points per day. Using a year of profit as the base puts different eras on one scale: above the dashed line (the 95th percentile of history up to that day) the losses are as large as only past lows have seen; those days are the red dots on the price above, bigger the further above the line. %s. '
             'It crossed %d times since 2014: higher 60 days later %d times, median %s; higher 180 days later %d times, median %s, though the median drawdown along the way was %s, and in bear markets (2018/02, 2019/09, 2022/05, 2022/06) price still fell 18%% to 39%% afterwards. Bitview data, not entity-adjusted. A reading, not a signal.' % (
              now_e, cp_['n'], r6['up'], sg(r6['med']), r18['up'], sg(r18['med']), sg(d18['med']))))
    ss = o['ssr']; pc = lambda v: None if v is None else round(v * 100, 4)
    c_ssr = dict(k='ssr', zh='賣方風險比', en='Sell-side risk ratio', f='p2', rows=[[r[0], r[1], pc(r[2]), pc(r[3]), pc(r[4]), pc(r[5])] for r in ss['rows']], p=1, log=1, hero=3,
      ser=[ser(5, zh='近 4 年最低 10%', en='4y bottom 10%', col='c4', dash='4 3', w=1), ser(4, zh='長期持有者', en='Long-term holders', col='c3', w=1, op=.65), ser(3, zh='短期持有者', en='Short-term holders', col='ac', w=1, op=.65), ser(2, zh='全網', en='Network', col='c5', w=1.8)],
      spans=[dict(a=dn(e['start']), b=dn(e['end']), col='c4', op=.16) for e in ss['eps']], leg=[['c4', '在低檔區的期間', 'Time in the low zone', 'box']],
      dz='7 天實現的獲利加虧損，佔實現市值的比例，分成全網、短期和長期持有者三條。越低代表越少人願意在這個價位賣。', de='Seven-day realized profit plus loss as a share of realized cap, split into the network, short-term and long-term holders. Lower means fewer holders are willing to sell here.')
    se = o['sec']; sth_ = se['th']
    c_sec = dict(k='sec', zh='賣方衰竭常數', en='Seller exhaustion constant', f='n3', rows=se['rows'], p=2, log=1, ser=[ser(1, zh='賣方衰竭常數', en='Seller exhaustion constant', col='c3', w=1.5)],
      zones=[dict(lo=None, hi=sth_, col='dn', zh='在極端區', en='In the extreme zone', nz='極端區', ne='the extreme zone')], refs=[dict(v=sth_, col='dn')], leg=[['dn', '極端區（低於 %g）' % sth_, 'Extreme zone (below %g)' % sth_, 'box']],
      marks=[dict(d=dn(h['low_date']), v=h['low'], col='dn', up=0, zh=h['low_date'][:7].replace('-', '/'), en=h['low_date'][:7].replace('-', '/')) for h in se['hits']],
      dz='獲利供給比例乘上 30 天波動率。兩個都低，代表賣方快沒力了。圓圈是歷次跌進極端區的低點。', de='Supply in profit times 30-day volatility. When both are low, sellers are running out of force. Circles mark past lows inside the extreme zone.')
    mo_ = o['mom']; dv = mo_['divs']
    c_mom = dict(k='mom', zh='鏈上勢能', en='On-chain momentum', f='s1', rows=mo_['rows'], p=1, tf='slog', ser=[ser(2, zh='鏈上勢能', en='On-chain momentum', t='sign', base=0, w=1.3)],
      links=[dict(a=dn(x['prev']), b=dn(x['date']), pa=x['prev_price'], pb=x['price'], va=x['za'], vb=x['zb'], col='c5', dash='5 4',
                  zh=('頂背離 %s %s%%' % (x['date'][5:].replace('-', '/'), ('%+.0f' % x['dd60']).replace('-', '−'))) if x in dv[-3:] and x.get('dd60') is not None else None,
                  en=('Bear div %s %s%%' % (x['date'][5:].replace('-', '/'), ('%+.0f' % x['dd60']).replace('-', '−'))) if x in dv[-3:] and x.get('dd60') is not None else None) for x in dv],
      leg=[['up', '獲利了結（正）', 'Profit-taking (positive)', 'box'], ['dn', '認賠（負）', 'Loss-taking (negative)', 'box'], ['c5', '頂背離', 'Bearish divergence', 'dash']],
      dz='（全網 SOPR − 1）乘上每日銷毀的幣天數，取 14 日平均。虛線是頂背離：價格創新高，勢能的高點卻比較低。', de='(Network SOPR − 1) times coin-days destroyed, 14-day average. Dashed lines are bearish divergences: price makes a new high while momentum peaks lower.')
    # ── 長期持有者與大戶 ──
    lc = o['lth_color']
    c_lth = dict(k='lthnet', zh='長期持有者 30 日淨部位變化', en='LTH 30-day net position change', f='usd0', rows=lc['rows'], one=1, hero=1,
      ser=[ser(1, zh='BTC 價格', en='BTC price', t='ramp', rc=2, clip=lc['clip']), ser(2, hide=1, f='btc')],
      leg=[['dn', '淨減 ≥ 40 萬', 'Net cut ≥ 400K', 'box'], ['k2', '持平（±5 萬內）', 'Flat (within ±50K)', 'box'], ['up', '淨增 ≥ 40 萬', 'Net add ≥ 400K', 'box']],
      dz='價格線的顏色，是長期持有者 30 天淨增減了多少顆：橘是在減、灰是持平、綠是在增。', de='The price line is coloured by how many BTC long-term holders added or shed over 30 days: orange for cutting, grey for flat, green for adding.')
    ls = o['lsrchg']; tE = dn(L['meta']['bar_date'])
    c_lsr = dict(k='lsrchg', zh='長短期供給比 30 日變化', en='LTH/STH supply ratio, 30-day change', f='pct1', rows=ls['rows'], p=1, ser=[ser(2, zh='30 日變化', en='30-day change', t='sign', base=0, hi='c4', lo='ac', w=1.4)],
      spans=[dict(a=dn(t[0]) - 365, b=dn(t[0]), col='c5', op=.1) for t in cyc['tops']] + [dict(a=dn(t[0]), b=min(tE, dn(t[0]) + 365), col='c4', op=.13) for t in cyc['bottoms']],
      leg=[['ac', '為負：長期持有者的幣流向短期持有者', 'Negative: LTH coins moving to STH', 'box'], ['c4', '為正：籌碼沉澱', 'Positive: supply settling', 'box'], ['c5', '週期頂部前一年', 'Year before a cycle top', 'box'], ['c4', '週期底部後一年', 'Year after a cycle bottom', 'box']],
      dz='長期持有者的幣除以短期持有者的幣，30 天的變化。負值代表幣在往短期持有者移動。', de='Long-term holder supply divided by short-term holder supply, 30-day change. Negative means coins are moving to short-term holders.')
    sd = o['sthd']
    c_sthd = dict(k='sthd', zh='短期持有者供給 90 天變化', en='STH supply, 90-day change', f='kbtc', rows=sd['rows'], p=1, ser=[ser(2, zh='90 天變化', en='90-day change', t='sign', base=0, hi='ac', lo='c4', w=1.5)],
      marks=[dict(d=dn(t['date']), v=t['value'] / 1000, col='ac', up=1, zh='%s +%.0f 萬' % (yr(t['date']), t['value'] / 1e4), en='%s +%.0fK' % (yr(t['date']), t['value'] / 1e3)) for t in sd['tops']],
      leg=[['ac', '增加：舊幣換手', 'Rising: old coins changing hands', 'box'], ['c4', '減少：幣在沉澱', 'Falling: coins settling', 'box']],
      dz='短期持有者手上的幣，90 天增減了多少。增加代表舊幣在換手。標記是歷次週期頂部附近的高點。', de='How much short-term holder supply changed in 90 days. Rising means old coins are changing hands. Markers show the peaks near past cycle tops.')
    do = o['dorm']
    c_dorm = dict(k='dorm', zh='Dormancy', en='Dormancy', f='d1', rows=[[r[0], r[1], r[2], r[3]] for r in do['rows']], p=1, log=1, hero=1,
      ser=[ser(2, zh='Dormancy（7 天）', en='Dormancy (7d)', col='c3', w=.9, op=.55), ser(3, zh='30 天平均', en='30-day average', col='ac', w=1.8)],
      marks=[dict(d=dn(t['date']), v=t['value'], on=1, col='c5', up=1, zh='頂 %s %.0f 天' % (yr(t['date']), t['value']), en='Top %s %.0fd' % (yr(t['date']), t['value'])) for t in do['tops']],
      dz='每顆被花掉的幣平均沉睡了幾天。高代表老幣在動。標記是歷次週期頂部的水位。', de='The average number of days each spent coin had been dormant. High means old coins are moving. Markers show the level at past cycle tops.')
    lr = o['lthrl']
    c_lthrl = dict(k='lthrl', zh='長期持有者已實現虧損', en='LTH realized loss', f='p3', rows=lr['rows'], p=2, ser=[ser(1, zh='已實現虧損 ÷ 市值', en='Realized loss ÷ market cap', col='c3', w=1.5)],
      dz='長期持有者 7 天賠錢賣出的金額，相對市值的大小。', de='What long-term holders sold at a loss over 7 days, relative to market cap.')
    G = [
      dict(id='cost', zh='成本與位置', en='Cost and position', sz='價格相對各群人的成本在哪裡', se="Where price sits against each group's cost", charts=[c_sth, c_profit, c_aviv, c_rup, c_conc, c_lthloss]),
      dict(id='pnl', zh='賣出的人賺還是賠', en='Are sellers in profit or at a loss', sz='短期持有者和全市場賣出時是獲利還是認賠', se='Whether short-term holders, and the market as a whole, sell at a profit or a loss', charts=[c_sopr, c_pnl, c_conf, c_npl, c_n365]),
      dict(id='sell', zh='賣壓強弱與衰竭', en='Selling pressure and exhaustion', sz='賣壓在加大還是快耗盡', se='Is selling building up or running dry', charts=[c_rpl, c_rloss, c_ssr, c_sec, c_mom]),
      dict(id='lth', zh='長期持有者與大戶', en='Long-term holders and whales', sz='長期持有者和大戶在加碼、出貨還是認賠', se='Are long-term holders and whales adding, distributing or selling at a loss', charts=[c_lth, c_lsr, c_sthd, c_dorm, c_lthrl]),
    ]
    px = [[r[0], r[1]] for r in ch['stress']['rows']]
    mo, me = N['modules']['onchain'], (E or {}).get('modules', {}).get('onchain') or {}
    return dict(px=px, kw=ch['viz']['kw'], charts={c['k']: c for g in G for c in g['charts']}, lead_zh=mo['lead'], points_zh=mo['points'], lead_en=me.get('lead') or mo['lead'], points_en=me.get('points') or mo['points'])
