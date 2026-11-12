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
    c_profit = dict(k='profit', zh='短期持有者獲利比例', en='Short-term holders in profit', f='p1', rows=ch['viz']['profit'], kw=1, ph=.4, dom=[0, 100],
      ser=[ser(1, zh='獲利比例', en='In profit', col='c4', fill=1)], refs=[dict(v=50, col='k2'), dict(v=97.5, col='dn', zh='97.5% 賣出線', en='97.5% sell line')], zones=[dict(lo=97.5, hi=100, col='dn', zh='高於 97.5% 賣出線', en='Above the 97.5% sell line', nz='97.5% 賣出線', ne='the 97.5% sell line')],
      leg=[['up', '週 K 收漲', 'Weekly candle up', 'box'], ['dn', '週 K 收跌', 'Weekly candle down', 'box']],
      dz='短期持有者手上的幣，有多少比例現在是賺的。上格是 BTC 週 K（對數刻度）。', de='The share of short-term holder coins currently in profit. Top pane: BTC weekly candles (log scale).')
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
    c_rpl = dict(k='rpl', zh='實現獲利 ÷ 虧損（90 天）', en='Realized profit ÷ loss (90d)', f='x2', rows=rp['rows'], p=2, log=1, ser=[ser(1, zh='獲利 ÷ 虧損', en='Profit ÷ loss', t='split', base=1, w=1.6)],
      refs=[dict(v=1, col='ink', solid=1)], spans=[dict(a=dn(e['start']), b=dn(e['end']), col='dn', op=.12, below=1) for e in rp['reds']],
      leg=[['up', '1 以上（獲利了結較多）', 'Above 1 (more profit-taking)', 'line'], ['dn', '1 以下（認賠較多）', 'Below 1 (more loss-taking)', 'line']],
      dz='全網 90 天平均的實現獲利，除以實現虧損。橘底是歷次跌到 1 以下的期間。', de='The 90-day average of network realized profit divided by realized loss. Orange bands mark past stays below 1.')
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
