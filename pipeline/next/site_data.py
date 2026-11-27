# -*- coding: utf-8 -*-
"""整站骨架原型的資料：照「一個今天、六個問題」分章。價位是完整的一片；賣壓、買盤、週期先放已經做好的圖。build.py 會 import。"""
import oc_data, pm_data, cycle_data, today_data, exit_data, sell_data, lev_data, buy_data

def build(L, N, E, dn):
    oc = oc_data.build(L, N, E, dn); X = dict(oc['charts']); pm = pm_data.build(L); tE = dn(L['meta']['bar_date']); close = pm['px']
    ser = lambda c, **k: dict(c=c, **k)
    usd = lambda v: '$' + format(int(round(v)), ',')
    # ── 價位 › 成本線 ──
    lv = L['cycle']['levels']
    _ms = ((L.get('flows') or {}).get('treasury') or {}).get('mstr') or {}   # 2026-11-12：Strategy 的平均買進成本，只有現值，畫成一條水平線
    X['levels'] = dict(k='levels', zh='成本線與均線', en='Cost bases and moving averages', hz='收盤', he='Close', one=1, tf='lin', f='usd0', rows=lv['rows'],
      refs=[dict(v=_ms['cost'], col='c5', zh='Strategy 平均成本 ' + usd(_ms['cost']), en='Strategy average cost ' + usd(_ms['cost']))] if _ms.get('cost') else [],
      ser=[ser(1, zh='BTC 價格', en='BTC price', col='ink', w=1.6), ser(2, zh='200 日均線', en='200-day MA', col='c3', w=1.2), ser(3, zh='365 日均線', en='365-day MA', col='c5', w=1.2), ser(4, zh='50 週均線', en='50-week MA', col='ink', dash='5 4', w=1, op=.6),
           ser(5, zh='短期持有者成本', en='STH cost', col='ac', w=1.6), ser(9, zh='活躍投資人成本', en='Active investor price', col='ac', dash='5 4', w=1.3), ser(6, zh='真實市場均價', en='True market mean', col='c4', w=1.8),
           ser(7, zh='實現價', en='Realized price', col='k2', dash='5 4', w=1.1), ser(8, zh='長期持有者成本', en='LTH cost', col='k2', dash='2 3', w=1.1)],   # 照現有網站：成本類用橘色，活躍投資人用虛線和短期持有者區分
      dz='價格和八條線：三條均線，加上五群人的平均成本。價格在活躍投資人成本上方偏多，在它和真實市場均價之間是盤整，跌破真實市場均價偏空。', de='Price against eight lines: three moving averages and the average cost of five groups. Above the active investor price is constructive; between it and the true market mean is a range; below the true market mean is bearish.')
    q = L['onchain']['quant']; qk = [str(k) for k in q.get('keys') or sorted(q['cur'].keys(), key=int)]
    QC = {'45': 'c3', '50': 'color-mix(in srgb, var(--c3) 50%, var(--c4))', '55': 'c4', '60': 'up', '65': 'c5', '75': 'color-mix(in srgb, var(--c5) 45%, var(--ac))', '85': 'ac'}   # 照現有網站：低分位冷色、高分位暖色
    qs = [ser(1, zh='BTC 價格', en='BTC price', col='ink', w=1.5)] + [ser(2 + i, zh='成本分位 %s%%' % k, en='%s%% quantile' % k, col=QC[k], w=2 if k in ('65', '75') else 1.4) for i, k in enumerate(qk) if k in QC]
    qcol = lambda k: 2 + qk.index(k)
    qb = ([dict(a=qcol('55'), b=qcol('65'), col='c4', op=.12)] if '55' in qk and '65' in qk else []) + ([dict(a=qcol('75'), b=qcol('85'), col='c5', op=.12)] if '75' in qk and '85' in qk else [])   # 照現有網站：55–65% 之間、75–85% 之間各有一條淡色帶
    X['quant'] = dict(k='quant', zh='供給分位成本線', en='Supply cost-basis quantiles', hz='收盤', he='Close', one=1, f='usd0', rows=q['rows'], ser=qs, bands=qb,
      dz='把所有的幣依最後一次移動的價格排序，第 q% 的那個價格就是一條線。價格站在 q 線上，大約就是 q% 的幣在獲利。線在價格上面是壓力，在下面是支撐。顏色由冷到熱：藍色是低分位，橘色是高分位；65% 和 75% 兩條線比較粗，兩段淡色帶是 55–65% 和 75–85%。', de='Sort every coin by the price it last moved at; the q-th percentile is one line. With price on the q line, about q% of supply is in profit. Lines above price act as resistance, lines below as support. Colours run cold to hot: blue for low quantiles, orange for high. The 65% and 75% lines are heavier; the two tinted bands are 55–65% and 75–85%.')
    # ── 2026-11-16 Bitview 的損失地板和賺賠分布（pipeline/bv_more.py；使用者看過目錄盤點後決定做）──
    bx = (L.get('onchain') or {}).get('bvx') or {}; fl = bx.get('floors'); pn = bx.get('pnl')
    from say_data import own as _own
    _md = lambda d_: '%d/%d' % (int(d_[5:7]), int(d_[8:10])); _ym = lambda d_: d_[:7].replace('-', '/'); _p1 = lambda v: ('%.1f%%' % v); _pg = lambda v: ('%g%%' % v)
    if fl and len(fl.get('rows') or []) > 200:
        fc = fl['cur']; fpx = close if bx.get('date') == L['meta']['bar_date'] and close else fl['px']; gap = (fpx / fc[0] - 1) * 100; deep = (fc[4] / fpx - 1) * 100; bv_nb = sum(fpx < f for f in fc)   # 2026-11-17 運營回報：句子寫「收盤」就用全站統一的收盤（Kraken），不用 Bitview 自己的價格
        FC = ['c4', 'color-mix(in srgb, var(--c4) 72%, var(--c3))', 'color-mix(in srgb, var(--c4) 45%, var(--c3))', 'color-mix(in srgb, var(--c4) 20%, var(--c3))', 'c3']   # 淺的一層青、越深越偏藍紫：都是冷色（支撐在下面），和成本線的暖色分開
        lowz = lambda q: '%s %s%s' % (_ym(q['d']), '五層全破' if q['broke'] == 5 else '破 %d 層' % q['broke'] if q['broke'] else '沒破', '（這一輪到目前）' if q.get('open') else '')
        lowe = lambda q: '%s: %s%s' % (q['d'][:7], 'all five broken' if q['broke'] == 5 else '%d broken' % q['broke'] if q['broke'] else 'none broken', ' (this cycle so far)' if q.get('open') else '')
        fser = lambda w0: [ser(1, zh='BTC 價格', en='BTC price', col='ink', w=1.5)] + [ser(2 + i, zh='第 %d 層（最糟 %s）' % (i + 1, _pg(fl['pct'][i])), en='Floor %d (worst %s)' % (i + 1, _pg(fl['pct'][i])), col=FC[i], w=w0 if i == 0 else 1.2) for i in range(5)]
        fmk = lambda f_: [dict(d=q['dn'], v=q['px'], col='c5', up=0, zh=lowz(q), en=lowe(q)) for q in f_['lows'] if q['dn'] >= f_['rows'][0][0] and not q.get('open')]   # 圖從 2017 年畫起，更早的低點只寫在讀數裡；這一輪到目前的低點也只寫在文字裡（標在最右邊會被價格標籤蓋住）
        brk = [b for b in fl['breaks'] if b.get('y1') is not None]; w0 = max(b['worst'] for b in brk); w1 = min(b['worst'] for b in brk); wb = min(brk, key=lambda b: b['y1'])
        X['floors'] = dict(k='floors', zh='損失地板', en='Loss floors', hz='第一層地板', he='First floor', one=1, f='usd0', hero=1, rows=fl['rows'],
          ser=fser(1.9), bands=[dict(a=2, b=6, col='c4', op=.09)], marks=fmk(fl),
          src='Bitview · ' + _md(bx['date']), srce='Bitview · ' + _md(bx['date']),
          dz='價格跌到哪裡，虧損的幣佔全部供給的比例會到它自己歷史上最糟的水準。五條線由淺到深：最糟 5%%、2%%、1%%、0.5%%、0.1%%。門檻只用到當天為止的歷史，逐日累積，不是回頭用整段歷史算的。圓圈是歷次低點，標的是那天跌破了幾層。'
             '地板標的是「痛到歷史等級」的區間，不是保證的底：%d 年以來 %s 的日子收在第一層下面；歷次第一次跌破第一層之後，一年內還再跌 %d%%–%d%%，%s 那次一年後還是 %d%%。每顆幣算一次、逐筆 UTXO，沒有排除遺失的幣和交易所內部移轉。只作讀值。'
             % (int(fl['since'][:4]), _p1(fl['below1_pct']), abs(w0), abs(w1), _ym(wb['d']), wb['y1']),
          de='The price at which the share of supply held at a loss would reach the worst levels in its own history. Five lines from shallow to deep: the worst 5%%, 2%%, 1%%, 0.5%% and 0.1%%. Each threshold uses only the history up to that day, so it accumulates and is not fitted in hindsight. Circles mark past lows, labelled with how many floors that day broke. '
             'The floors mark a zone of historic pain, not a guaranteed bottom: since %d, %s of days closed below the first floor; after each first break of it, price went on to fall another %d%%–%d%% within a year, and after the %s break it was still %d%% a year later. Every coin counts once, per UTXO, with lost coins and exchange-internal transfers not excluded. A reading only.'
             % (int(fl['since'][:4]), _p1(fl['below1_pct']), abs(w0), abs(w1), wb['d'][:7], wb['y1']))
        aw = fl.get('aw')
        if aw and len(aw.get('rows') or []) > 200:   # 2026-11-28 使用者看了 Bitview Bottoms 排名後要的「加權地板」檢視（awake：常動的幣算得重）
            ac_ = aw['cur']; aw_nb = sum(fpx < f for f in ac_); spread = (ac_[0] / ac_[4] - 1) * 100; t15 = aw.get('t15')
            alz = '、'.join(lowz(q) for q in aw['lows']); ale = '; '.join(lowe(q) for q in aw['lows'])
            X['floors']['modes'] = [dict(mz='每顆幣一樣', me='Unweighted'), dict(mz='常動的幣加重', me='Awake-weighted', rows=aw['rows'], ser=fser(1.9), marks=fmk(aw),
              dz='一樣是五層地板，但每顆幣不再一樣重：還常移動的幣算得重，久放不動的老幣幾乎不算（Bitview 的 awake 加權：依幣所在幣齡帶的持有時間已經用掉多少來算）。所以這組看的是「還會動的那群人」虧到歷史最糟的哪裡。'
                 '這群人現在 %s 在虧，不加權是 %s；五層也擠得很近，%s 到 %s 只差 %s，價格一動就連破好幾層。歷次低點：%s。' % (_p1(aw['loss']), _p1(fl['loss']), usd(ac_[4]), usd(ac_[0]), _p1(spread), alz)
                 + ('Bitview 拿 2018、2022、2026 三次底部替 346 條價格線排名（11/27），第 3 層（最糟 1%%）排第 2，價格碰到後最多再跌 10%%；但同樣的算法套到 2015/1 的底部，價格 %s 在 %s 碰到它之後又跌了 %d%%。' % (_ym(t15['d']), usd(t15['v']), t15['miss']) if t15 else '')
                 + '幾輪樣本，地板是痛的區間，不是保證的底。只作讀值。',
              de='The same five floors, but coins no longer count equally: coins that still move weigh more and long-idle coins barely count (Bitview\'s awake weighting, by how much of its age band\'s holding time each coin has used). So these floors track how deep the losses of the coins that still move have gone against their own worst history. '
                 '%s of that supply is at a loss now, against %s unweighted, and the five floors sit close together: %s to %s, only %s apart, so a small move breaks several. Past lows: %s. ' % (_p1(aw['loss']), _p1(fl['loss']), usd(ac_[4]), usd(ac_[0]), _p1(spread), ale)
                 + ('Bitview ranked 346 price lines on the 2018, 2022 and 2026 bottoms (27 Nov): the third floor (worst 1%%) came 2nd, with price falling at most 10%% further after touching it. Under the same rules, at the January 2015 bottom price touched it at %s in %s and then fell another %d%%. ' % (usd(t15['v']), t15['d'][:7], t15['miss']) if t15 else '')
                 + 'Few cycles; the floors mark a zone of pain, not a guaranteed bottom. A reading only.')]
        else: aw = None
        X['floors']['say'] = _own([
            ('第一層地板', 'First floor', usd(fc[0]), usd(fc[0]), 'warn' if bv_nb or gap < 5 else 'neu',
             ('收盤 %s 已經在第一層下面 %s，連續 %d 天。' % (usd(fpx), _p1(-gap), fl['below_days']) if bv_nb else '收盤 %s，在第一層上方 %s。' % (usd(fpx), _p1(gap))) + '跌到第一層，虧損的幣會佔供給的 %s，是歷史最糟 5%% 的水準；現在是 %s。' % (_p1(fl['thr'][0]), _p1(fl['loss'])),
             ('The close of %s is already %s below the first floor, for %d days running. ' % (usd(fpx), _p1(-gap), fl['below_days']) if bv_nb else 'The close of %s sits %s above the first floor. ' % (usd(fpx), _p1(gap))) + 'At the first floor, %s of supply would be held at a loss, a level seen in only the worst 5%% of history; it is %s now.' % (_p1(fl['thr'][0]), _p1(fl['loss']))),
            ('現在破了幾層', 'Floors broken now', '%d 層' % bv_nb, '%d of 5' % bv_nb, 'warn' if bv_nb >= 2 else 'neu',
             '五層依序是 %s。' % '、'.join(usd(v) for v in fc) + '最深一層比收盤低 %s，到那裡虧損的幣佔 %s。' % (_p1(-deep), _p1(fl['thr'][4])) + ('常動的幣加重的版本破 %d 層，這群幣 %s 在虧。' % (aw_nb, _p1(aw['loss'])) if aw else ''),
             'The five floors are %s. ' % ', '.join(usd(v) for v in fc) + 'The deepest sits %s below the close, where %s of supply would be at a loss.' % (_p1(-deep), _p1(fl['thr'][4])) + (' The awake-weighted version has %d broken, with %s of that supply at a loss.' % (aw_nb, _p1(aw['loss'])) if aw else '')),
            ('歷次低點', 'Past lows', '破 %d–%d 層' % (min(q['broke'] for q in fl['lows']), max(q['broke'] for q in fl['lows'])), '%d–%d broken' % (min(q['broke'] for q in fl['lows']), max(q['broke'] for q in fl['lows'])), 'neu',
             '；'.join('%s 的低點 %s，%s' % (_ym(q['d']), usd(q['px']), lowz(q).split(' ', 1)[1]) for q in fl['lows']) + '。',
             '; '.join('the %s low of %s, %s' % (q['d'][:7], usd(q['px']), lowe(q).split(': ', 1)[1]) for q in fl['lows']) + '.')],
            ('收盤已經跌破 %d 層地板。' % bv_nb if bv_nb else '收盤在第一層地板上方 %s，五層都沒破。' % _p1(gap)), ('The close is below %d of the five floors.' % bv_nb if bv_nb else 'The close sits %s above the first floor; none of the five is broken.' % _p1(gap)))
    if pn and all(len((pn.get(k_) or {}).get('rows') or []) > 200 for k_ in ('all', 'sth', 'lth')):
        PC = ['k2', 'c5', 'color-mix(in srgb, var(--c5) 50%, var(--dn))', 'dn', 'color-mix(in srgb, var(--dn) 30%, #E0007A)']   # 越深越紅：黃 → 橘 → 橘紅 → 深桃紅；最外面那條（所有在虧的）用灰色虛線當底。2026-11-17 使用者：「都是紅色，區分不出來」——原本用 ac、ac 和 dn 的混色、dn，但 ac 和 dn 是同一個色（#FF4F1F），三條同色
        PN = [('在虧損的', 'At a loss'), ('虧 10% 以上', 'Down 10% or more'), ('虧 20% 以上', 'Down 20% or more'), ('虧 30% 以上', 'Down 30% or more'), ('虧 50% 以上', 'Down 50% or more')]
        pser = [ser(2 + i, zh=PN[i][0], en=PN[i][1], col=PC[i], w=1.1 if i == 0 else 1.9 if i == 1 else 1.4, **(dict(dash='4 3') if i == 0 else {})) for i in range(5)]
        bv_pm = lambda key, mz, me: dict(mz=mz, me=me, hz='虧 10% 以上的幣', he='Supply down 10% or more', f='p1', p=1, hero=1, rows=pn[key]['rows'], ser=pser)
        bv_A, Sx, Lx = pn['all'], pn['sth'], pn['lth']; d_, d30, dl = bv_A['depth'], bv_A['depth30'], bv_A['depth_low22']; bv_g_ = bv_A['cur']; lw = _ym(pn['low22'])
        X['pnlb'] = dict(k='pnlb', zh='賺賠分布：虧多深', en='Profit and loss spread: how deep the losses run', modes=[bv_pm('all', '全部的幣', 'All supply'), bv_pm('sth', '短期持有者', 'Short-term holders'), bv_pm('lth', '長期持有者', 'Long-term holders')],
          src='Bitview · ' + _md(bx['date']), srce='Bitview · ' + _md(bx['date']),
          dz='把每顆幣用「現在的價格比它最後一次移動時高或低多少」分組，看各組佔供給多少。五條線是累計的：所有在虧的、虧 10% 以上、20% 以上、30% 以上、50% 以上，所以線不會交叉，越下面的線虧得越深。籌碼分布回答成本在哪個價位，這張回答虧多深。'
             '可以切換全部的幣、短期持有者（持有不到 155 天）、長期持有者，各自以自己那一群的幣為 100%。逐筆 UTXO，沒有排除遺失的幣（很早期的幣會一直算在大賺那一組）和交易所內部移轉。只作讀值。',
          de='Every coin is grouped by how far the current price sits above or below the price it last moved at, and each group is shown as a share of supply. The five lines are cumulative: everything at a loss, then down 10%, 20%, 30% and 50% or more, so they never cross and the lower the line, the deeper the loss. The supply distribution says where the cost is; this says how deep the loss is. '
             'Switch between all supply, short-term holders (held under 155 days) and long-term holders; each is a share of its own group. Per UTXO, with lost coins (very early coins stay in the big-profit group) and exchange-internal transfers not excluded. A reading only.')
        X['pnlb']['say'] = _own([
            ('虧 10% 以上', 'Down 10% or more', _p1(d_[1]), _p1(d_[1]), 'warn' if bv_A['pct10'] >= 80 else 'neu',
             '全部的幣裡 %s 在虧損：虧 10%% 以上的 %s、20%% 以上 %s、30%% 以上 %s、虧過半的 %s。%d 年以來 %d%% 的日子，虧 10%% 以上的比例比現在低。30 天前是 %s。' % (_p1(d_[0]), _p1(d_[1]), _p1(d_[2]), _p1(d_[3]), _p1(d_[4]), int(bv_A['pct_since'][:4]), bv_A['pct10'], _p1(d30[1])),
             '%s of all supply is at a loss: %s is down 10%% or more, %s down 20%% or more, %s down 30%% or more and %s down by half or more. Since %d, the share down 10%% or more was lower than now on %d%% of days. Thirty days ago it was %s.' % (_p1(d_[0]), _p1(d_[1]), _p1(d_[2]), _p1(d_[3]), _p1(d_[4]), int(bv_A['pct_since'][:4]), bv_A['pct10'], _p1(d30[1]))),
            ('短期持有者', 'Short-term holders', _p1(Sx['depth'][0]) + ' 在虧', _p1(Sx['depth'][0]) + ' at a loss', 'warn' if Sx['depth'][1] >= 50 else 'neu',
             '持有不到 155 天的幣，%s 在虧損，%s 虧 10%% 以上，%s 虧 20%% 以上。長期持有者是 %s 在虧、%s 虧 30%% 以上。' % (_p1(Sx['depth'][0]), _p1(Sx['depth'][1]), _p1(Sx['depth'][2]), _p1(Lx['depth'][0]), _p1(Lx['depth'][3])),
             'Of coins held under 155 days, %s are at a loss, %s down 10%% or more and %s down 20%% or more. For long-term holders, %s are at a loss and %s down 30%% or more.' % (_p1(Sx['depth'][0]), _p1(Sx['depth'][1]), _p1(Sx['depth'][2]), _p1(Lx['depth'][0]), _p1(Lx['depth'][3]))),
            ('和 %s 低點比' % lw, 'Versus the %s low' % pn['low22'][:7], '虧過半 ' + _p1(d_[4]), _p1(d_[4]) + ' down by half', 'neu',
             '%s 低點那天 %s 在虧，其中虧過半的佔供給 %s；現在在虧的比例是 %s，虧過半的 %s，虧得淺很多。' % (lw, _p1(dl[0]), _p1(dl[4]), _p1(d_[0]), _p1(d_[4])),
             'On the day of the %s low, %s of supply was at a loss and %s was down by half or more; now %s is at a loss and %s is down by half, a much shallower loss.' % (pn['low22'][:7], _p1(dl[0]), _p1(dl[4]), _p1(d_[0]), _p1(d_[4]))),
            ('賺的那一邊', 'The profit side', _p1(bv_g_[0]) + ' 賺一倍以上', _p1(bv_g_[0]) + ' up 100% or more', 'neu',
             '賺一倍以上的幣佔 %s，賺 50%%–100%% 的 %s，賺 10%%–50%% 的 %s，賺不到 10%% 的 %s。30 天前賺 10%%–50%% 的有 %s。' % (_p1(bv_g_[0]), _p1(bv_g_[1]), _p1(bv_g_[2]), _p1(bv_g_[3]), _p1(bv_A['prev30'][2])),
             '%s of supply is up 100%% or more, %s up 50%%–100%%, %s up 10%%–50%% and %s up less than 10%%. Thirty days ago %s was up 10%%–50%%.' % (_p1(bv_g_[0]), _p1(bv_g_[1]), _p1(bv_g_[2]), _p1(bv_g_[3]), _p1(bv_A['prev30'][2])))],
            '%s 的幣在虧損，%s 虧 10%% 以上，沒有到 %s 低點那種虧過半的程度。' % (_p1(d_[0]), _p1(d_[1]), lw) if d_[4] < 1 else '%s 的幣在虧損，%s 虧 10%% 以上，%s 虧過半。' % (_p1(d_[0]), _p1(d_[1]), _p1(d_[4])),
            '%s of supply is at a loss and %s is down 10%% or more, well short of the down-by-half depth of the %s low.' % (_p1(d_[0]), _p1(d_[1]), pn['low22'][:7]) if d_[4] < 1 else '%s of supply is at a loss, %s down 10%% or more and %s down by half.' % (_p1(d_[0]), _p1(d_[1]), _p1(d_[4])))
    tc_t = bx.get('tiers')   # 2026-11-16 大戶地址的持幣成本（bv_more.py）：運營回覆用過自己畫的版本，使用者看了要求網站加
    if tc_t and len(tc_t.get('rows') or []) > 200:
        tc_c = tc_t['cur']; tc_px = close if bx.get('date') == L['meta']['bar_date'] and close else tc_t['px']; tc_g = [round((tc_px / c_ - 1) * 100, 1) for c_ in tc_c];   # 收盤用全站統一的（同損失地板）
        tc_y = tc_t['year']; tc_lg = tc_t.get('longest'); tc_dp = tc_t.get('deep'); tc_nd = tc_t['below_days']; tc_md = lambda d_: '%d/%d' % (int(d_[5:7]), int(d_[8:10]))
        tc_sg = lambda v: ('%+.1f%%' % v).replace('-', '−'); tc_up = lambda v: '上方 %.1f%%' % v if v >= 0 else '下方 %.1f%%' % -v; tc_ue = lambda v: '%.1f%% above' % v if v >= 0 else '%.1f%% below' % -v
        tc_TN = [('100–1k 顆', '100–1K BTC', 'c5'), ('1k–10k 顆', '1K–10K BTC', 'c3'), ('10k–100k 顆', '10K–100K BTC', 'c4')]   # 顏色和「大戶 30 日淨變化」同一組：100–1k 黃、1k–10k 藍紫、1 萬以上青
        tc_runs = '、'.join('%s%s' % (tc_md(r_['start']), '' if r_['days'] == 1 else '–' + tc_md(r_['end'])) + '（%d 天）' % r_['days'] for r_ in tc_t['runs']); tc_rune = ', '.join((r_['start'][5:] if r_['days'] == 1 else r_['start'][5:] + ' to ' + r_['end'][5:]) + ' (%d)' % r_['days'] for r_ in tc_t['runs'])
        X['tiercost'] = dict(k='tiercost', zh='大戶地址的已實現價格', en='Realized Price of Large-Balance Addresses', hz='1k–10k 顆這一層的成本', he='Cost of the 1K–10K BTC tier', one=1, f='usd0', hero=2, rng=365, rows=tc_t['rows'],
          ser=[ser(1, zh='BTC 價格', en='BTC price', col='ink', w=1.3)] + [ser(2 + i_, zh=tc_TN[i_][0], en=tc_TN[i_][1], col=tc_TN[i_][2], w=2.1 if i_ == 1 else 1.5) for i_ in range(3)],
          src='Bitview · ' + _md(bx['date']), srce='Bitview · ' + _md(bx['date']),
          dz='把地址依餘額分成三層（100–1k 顆、1k–10k 顆、10k–100k 顆），每一層的已實現市值除以持幣量，就是這一層的幣平均是在什麼價格最後一次移動的。'
             '這是依地址餘額分層，沒有做實體歸併：一個地址不等於一個人，餘額變了就會換層，1 萬顆以上那一層有不少交易所和託管機構，所以不要把它讀成某一群人的成本，也不是支撐位。這裡只記價格碰到之後待了幾天、多深。只作讀值。',
          de='Addresses are split into three tiers by balance (100–1K, 1K–10K and 10K–100K BTC); each tier\'s realized cap divided by its supply is the average price at which its coins last moved. '
             'The tiers are by address balance, not by entity: one address is not one holder, an address changes tier when its balance changes, and the 10K-plus tier holds many exchanges and custodians, so do not read a line as one group\'s cost, nor as support. This card only records how long and how far price went once it touched a line. A reading only.')
        X['tiercost']['say'] = _own([
            ('1k–10k 顆', '1K–10K BTC', usd(tc_c[1]), usd(tc_c[1]), 'warn' if tc_g[1] < 0 else 'neu',
             '收盤 %s，在這一層成本的%s。30 天前這條線是 %s。' % (usd(tc_px), tc_up(tc_g[1]), usd(tc_t['prev30'][1])),
             'The close of %s is %s this tier\'s cost. Thirty days ago the line was at %s.' % (usd(tc_px), tc_ue(tc_g[1]), usd(tc_t['prev30'][1]))),
            ('另外兩層', 'The other two tiers', '%s／%s' % (usd(tc_c[0]), usd(tc_c[2])), '%s / %s' % (usd(tc_c[0]), usd(tc_c[2])), 'neu',
             '100–1k 顆這一層 %s，收盤在它%s；10k–100k 顆這一層 %s，收盤在它%s。' % (usd(tc_c[0]), tc_up(tc_g[0]), usd(tc_c[2]), tc_up(tc_g[2])),
             'The 100–1K tier is at %s, with the close %s it; the 10K–100K tier is at %s, with the close %s it.' % (usd(tc_c[0]), tc_ue(tc_g[0]), usd(tc_c[2]), tc_ue(tc_g[2]))),
            ('%d 年收在 1k–10k 線下' % tc_y, 'Closes below the 1K–10K line in %d' % tc_y, '%d 天' % tc_nd, '%d days' % tc_nd, 'neu',
             ('共 %d 天：%s。最長連續 %d 天；最深是 %s，收 %s 對成本 %s（%s）。' % (tc_nd, tc_runs, tc_lg['days'], tc_md(tc_dp['d']), usd(tc_dp['px']), usd(tc_dp['cost']), tc_sg(tc_dp['pct'])) if tc_nd else '今年還沒有一天收在這條線下面。'),
             ('%d days in all: %s. The longest run was %d days; the deepest was %s, a close of %s against a cost of %s (%s).' % (tc_nd, tc_rune, tc_lg['days'], tc_dp['d'][5:], usd(tc_dp['px']), usd(tc_dp['cost']), tc_sg(tc_dp['pct'])) if tc_nd else 'No close below this line so far this year.'))],
            '收盤在 1k–10k 顆這一層成本的%s，在 100–1k 顆那一層的%s。' % (tc_up(tc_g[1]), tc_up(tc_g[0])), 'The close is %s the 1K–10K tier\'s cost and %s the 100–1K tier\'s.' % (tc_ue(tc_g[1]), tc_ue(tc_g[0])))
    _c5 = ((L.get('chips') or {}).get('flow') or {}).get('conc5') or {}
    if X.get('conc') and _c5.get('in_profit') is not None:   # 2026-11-16 集中度改用 Bitview 的現成序列後多出來的讀數
        X['conc']['dz'] += '現價上下 5%% 內的幣裡，獲利的佔供給 %s、虧損的 %s；短期持有者自己的集中度是 %s、長期持有者 %s。走勢是 Bitview 每天一筆（2018 年起）。' % (_p1(_c5['in_profit']), _p1(_c5['in_loss']), _p1(_c5['sth']), _p1(_c5['lth']))
        X['conc']['de'] += ' Of the coins within 5%% of price, those in profit are %s of supply and those at a loss %s; short-term holders\' own concentration is %s and long-term holders\' %s. The history is one Bitview reading a day since 2018.' % (_p1(_c5['in_profit']), _p1(_c5['in_loss']), _p1(_c5['sth']), _p1(_c5['lth']))
    ec = L['flows'].get('etfcost') or {}
    if len(ec.get('rows') or []) > 200:   # 2026-11-16 補上：原本只有「沒資料」時的佔位卡，有資料時這張圖反而不在（舊版有，運營回覆用過）。舊版停用前要先補齊
        from say_data import own as _own2
        e_md = lambda d_: '%d/%d' % (int(d_[5:7]), int(d_[8:10])); e_ym = lambda d_: d_.replace('-', '/'); e_p = lambda v: ('%.1f%%' % abs(v)); e_up = lambda v: '上方 ' + e_p(v) if v >= 0 else '下方 ' + e_p(v); e_ue = lambda v: e_p(v) + (' above' if v >= 0 else ' below')
        e_fl = ec['flow30']; e_fz = ('流入 ' if e_fl >= 0 else '流出 ') + ('%.1f 億美元' % (abs(e_fl) / 100) if abs(e_fl) >= 100 else '%d 百萬美元' % abs(e_fl)); e_fe = ('inflow of ' if e_fl >= 0 else 'outflow of ') + ('$%.2fB' % (abs(e_fl) / 1000) if abs(e_fl) >= 1000 else '$%dM' % abs(e_fl))
        X['etfcost'] = dict(k='etfcost', zh='ETF 持有者成本', en='ETF holder cost basis', hz='ETF 買家的平均成本（推算）', he='Average cost of ETF buyers (estimated)', one=1, f='usd0', hero=1, rows=[[r[0], r[1], r[2], r[3]] for r in ec['rows']],
          ser=[ser(1, zh='BTC 價格', en='BTC price', col='ink', w=1.4), ser(2, zh='ETF 平均成本', en='ETF average cost', col='ac', w=2), ser(3, zh='持有（千顆）', en='Held (thousand BTC)', hide=1, f='n1')],
          src='CoinMarketCap · ' + e_md(ec['date']), srce='CoinMarketCap · ' + e_md(ec['date']),
          dz='美國現貨 ETF（不含 GBTC）的買家平均成本：每天的淨流量 ÷ 當天收盤＝那天買進或賣出的顆數，用平均成本法累計（流出依當時的平均成本移出）。GBTC 轉換成 ETF 前就持有約 62 萬顆，那些幣的成本不是流量買出來的，所以不算。'
             'ETF 流量晚一天公布，所以成本線停在前一個交易日。這是推算，不是 ETF 自己公布的數字，也不是支撐位。只作讀值。',
          de='The average cost of US spot ETF buyers (excluding GBTC): each day\'s net flow divided by that day\'s close gives the BTC bought or sold, accumulated with the average-cost method (outflows leave at the average cost at the time). GBTC held about 620K BTC before it converted to an ETF; that cost was not bought through flows, so it is left out. '
             'ETF flows are published a day late, so the cost line stops at the previous trading day. This is an estimate, not a figure the ETFs publish, and it is not support. A reading only.')
        X['etfcost']['say'] = _own2([
            ('ETF 平均成本', 'ETF average cost', usd(ec['cost']), usd(ec['cost']), 'warn' if ec['gap_now'] < 0 else 'neu',
             '截至 %s，不含 GBTC 的現貨 ETF 買家平均成本 %s。%s 收盤 %s，在它的%s%s。' % (e_md(ec['date']), usd(ec['cost']), e_md(ec['px_date']), usd(ec['px_now']), e_up(ec['gap_now']), '，連續 %d 個交易日收在下面' % ec['run'] if ec['run'] else ''),
             'As of %s, the average cost of spot ETF buyers excluding GBTC is %s. The %s close of %s is %s it%s.' % (ec['date'][5:], usd(ec['cost']), ec['px_date'][5:], usd(ec['px_now']), e_ue(ec['gap_now']), ', the %d%s trading day below' % (ec['run'], 'th' if ec['run'] > 3 else ['', 'st', 'nd', 'rd'][ec['run']]) if ec['run'] else '')),
            ('上市以來收在成本下', 'Days below cost since launch', '%d／%d 天' % (ec['days_below'], ec['n_days']), '%d of %d days' % (ec['days_below'], ec['n_days']), 'neu',
             '%s 以來 %d 個交易日裡，%d 天收在成本下面，價格穿越成本線 %d 次，最近一次是 %s。最深是 %s，低 %s。' % (e_ym(ec['since']), ec['n_days'], ec['days_below'], ec['n_cross'], e_ym(ec['last_cross']) if ec.get('last_cross') else '—', e_ym(ec['min_date']), e_p(ec['min_gap'])),
             'Since %s, %d of %d trading days closed below cost, and price crossed the cost line %d times, most recently on %s. The deepest was %s, %s below.' % (ec['since'], ec['days_below'], ec['n_days'], ec['n_cross'], ec.get('last_cross') or '—', ec['min_date'], e_p(ec['min_gap']))),
            ('近 30 天淨流量', '30-day net flow', e_fz, e_fe, 'warn' if e_fl < 0 else 'neu',
             '不含 GBTC 的現貨 ETF 近 30 天淨%s；這些 ETF 合計持有約 %s 萬顆（推算，不含 GBTC 原本的 62 萬顆）。' % (e_fz, '%.0f' % (ec['held'] / 1e4)),
             'Spot ETFs excluding GBTC saw a net %s over 30 days; together they hold about %sK BTC (estimated, excluding GBTC\'s original 620K).' % (e_fe, '{:,}'.format(round(ec['held'] / 1e3))))],
            '收盤在 ETF 買家平均成本 %s 的%s。' % (usd(ec['cost']), e_up(ec['gap_now'])), 'The close is %s the ETF buyers\' average cost of %s.' % (e_ue(ec['gap_now']), usd(ec['cost'])))
    if not ec.get('rows'):
        err = [e for e in (L.get('meta', {}).get('errors') or []) if 'etfcost' in str(e)]
        X['etfcost'] = dict(k='etfcost', zh='ETF 持有者成本', en='ETF holder cost basis', na=dict(zh='今天沒有資料。' + ('來源（The Block）回傳 410，表示這份資料已經下架，需要換來源。' if err and '410' in str(err[0]) else '來源沒有回應。') + '這張圖用每天的 ETF 淨流量乘上當天收盤，估計 ETF 買家的平均成本。', en='No data today: the source (The Block) returned 410, meaning the feed has been withdrawn and needs replacing. This chart estimates the average cost of ETF buyers from daily net flows times each day\'s close.'))
    # ── 價位 › 籌碼在哪（分布型：橫條掛在直的價格軸上）──
    u = L['chips']['urpd']; uv = L['chips']['viz']['urpd']; co = L['chips']['cohort']
    def pick(band, W, c):   # 照現有網站 urpdPick：現價 −20%～+25% 內最厚的連續 5 格，和另一側（或兩側較薄的一邊）最薄的連續 4 格
        B = sorted(band, key=lambda p_: p_[0]); cur = (c // W) * W
        def win(lo, hi, k, more):
            o = None
            for i in range(0, len(B) - k + 1):
                w = B[i:i + k]
                if w[0][0] < lo or w[-1][0] + W > hi or any(j and w[j][0] != w[j - 1][0] + W for j in range(k)): continue
                t = sum(b[1] for b in w)
                if o is None or (t > o[2] if more else t < o[2]): o = (w[0][0], w[-1][0] + W, t)
            return o
        thick = win(c * .8, c * 1.25, 5, True)
        if not thick: return []
        below = lambda hi: win(c * .8, min(hi, cur), 4, False); above = lambda lo: win(max(lo, cur + W), c * 1.2, 4, False)
        if thick[0] <= c < thick[1]:
            x, y = below(thick[0]), above(thick[1]); thin = (x if x[2] <= y[2] else y) if x and y else (x or y)
        else: thin = below(cur) if thick[0] > c else above(cur + W)
        def lab(a, b, t, zh, en):   # 圖上標註：價位範圍、顆數、是什麼（2026-11-11 照舊版加回來）
            r = '%g–%gK' % (a / 1000, b / 1000); w = t / 1e4
            return [a, b, zh and None, '%s · %s 萬顆 · %s' % (r, ('%.0f' % w) if w >= 100 else ('%.1f' % w), zh), '%s · %sK BTC · %s' % (r, format(round(t / 1e3), ','), en)]
        out = [lab(thick[0], thick[1], thick[2], '附近最厚的一團', 'thickest cluster nearby')]
        if thin: out.append(lab(thin[0], thin[1], thin[2], '另一側的薄區', 'thin zone on the other side'))
        out[0][2] = 'c4'
        if len(out) > 1: out[1][2] = 'c5'
        return out
    hl = pick(uv['band'], uv['width'], uv.get('price') or close)
    X['urpd'] = dict(k='urpd', zh='UTXO 已實現價格分布（URPD）', en='UTXO Realized Price Distribution (URPD)', hz='現價這一格佔流通量', he='Share of supply in the current bucket',
      dist=dict(kind='one', step=uv['width'], rows=uv['band'], hl=hl, base='color-mix(in srgb, var(--c3) 45%, var(--k2))', unit='btc', leg=[['c4', '現價附近最厚的一段', 'Thickest stretch near price'], ['c5', '另一側最薄的一段', 'Thinnest stretch on the other side'], ['color-mix(in srgb, var(--c3) 45%, var(--k2))', '其餘（每 $2,000 一格）', 'The rest ($2,000 buckets)']]),
      hs=dict(v=u['cur_pct'], f='p2'), dz='每一格是最後一次在那個價位移動的幣。厚的地方是很多人的成本，價格到那裡容易停；薄的地方沒什麼人的成本，價格容易快速穿過。', de='Each bucket holds the coins that last moved at that price. Thick zones are where many holders\' costs sit and price tends to stall; thin zones have few and price tends to move through quickly.')
    ut = (L.get('chips') or {}).get('urpd_terr')
    if ut and ut.get('g') and len(ut['g']) >= 26:   # 籌碼地形（2026-11-16 使用者要求，規則見 page.html ㉛）：同一張卡多一個檢視，原本的圖是第一個、打開時還是它
        X['urpd']['modes'] = [dict(mz='分布', me='Distribution'), dict(mz='地形', me='Terrain')]
        X['urpd']['d3'] = dict(kind='terr', date=ut['date'], w=ut['w'], p0=ut['p0'], nb=ut['nb'], dates=ut['dates'], px=ut['px'], tot=ut['tot'], g=ut['g'], hl=hl,
                               srcz='地形的資料是 Bitview（每週一筆、每 $2,000 一格），和「分布」那張圖來源不同，同一格會差 1% 上下。', srce='The terrain uses Bitview data (weekly, $2,000 buckets), a different source from the distribution view; the same bucket can differ by about 1%.')
    uc = (L.get('chips') or {}).get('urpd_chg')
    if uc and uc.get('rows'):   # 籌碼搬家（2026-11-12 使用者要求）：近 7 天哪些價位變厚、變薄；顏色是方向（變厚 up、變薄 dn）
        from say_data import own
        wz = lambda v: ('%.1f' % (v / 1e4)) if abs(v) < 995000 else ('%.0f' % (v / 1e4)); ke = lambda v: format(round(v / 1e3), ',')
        bk = lambda p: '$%s–%s' % (format(p, ','), format(p + uc['width'], ',')); md = lambda s: '%d/%d' % (int(s[5:7]), int(s[8:10]))
        up, dn_ = uc.get('up') or [], uc.get('dn') or []
        lz = '、'.join('%s +%s 萬顆' % (bk(p), wz(v)) for p, v in up); le = ', '.join('%s +%sK' % (bk(p), ke(v)) for p, v in up)
        dz_ = '、'.join('%s −%s 萬顆' % (bk(p), wz(-v)) for p, v in dn_); de_ = ', '.join('%s −%sK' % (bk(p), ke(-v)) for p, v in dn_)
        lo_, ga_, mi_, out_ = uc['loss'], uc['gain'], uc['mid'], uc['moved_out']
        rt = lambda a, b: ('約 %.1f 倍' % (a / b), 'about %.1f times as many' % (a / b)) if b > 0 else ('另一邊幾乎沒有', 'almost none on the other side')
        cz, ce = (('賠錢移動的幣比賺錢移動的多（只算分得出來的部分，%s）' % rt(lo_, ga_)[0], 'More coins moved at a loss than at a profit (counting only those that can be told apart, %s)' % rt(lo_, ga_)[1]) if lo_ > ga_ * 1.3 else
                  ('賺錢移動的幣比賠錢移動的多（只算分得出來的部分，%s）' % rt(ga_, lo_)[0], 'More coins moved at a profit than at a loss (counting only those that can be told apart, %s)' % rt(ga_, lo_)[1]) if ga_ > lo_ * 1.3 else
                  ('賠錢移動和賺錢移動的幣差不多（只算分得出來的部分）', 'Coins moved at a loss and at a profit in similar amounts (counting only those that can be told apart)'))
        it = [('這些幣原本的成本', 'Where they came from', '%s 萬 / %s 萬' % (wz(lo_), wz(ga_)), '%sK / %sK' % (ke(lo_), ke(ga_)), 'neu',
               '%s。這 %d 天各價位淨減少的幣合計 %s 萬顆（同一格有進有出會互相抵掉，實際移動的更多）。其中 %s 萬顆原本的成本高於這幾天的最高價 $%s，移動的時候是賠的；%s 萬顆低於最低價 $%s，移動的時候是賺的；其餘 %s 萬顆的成本就在這幾天的價格範圍內，分不出來。變薄最多的三格：%s。'
               % (cz, uc['days'], wz(out_), wz(lo_), format(uc['hi'], ','), wz(ga_), format(uc['lo'], ','), wz(mi_), dz_),
               '%s. Over these %d days the buckets that thinned lost a net %sK BTC (moves in and out of the same bucket cancel, so more actually moved). %sK had a cost above the period high of $%s, so they moved at a loss; %sK were below the low of $%s, so they moved at a profit; the remaining %sK sat inside the period range and cannot be told apart. The three buckets that thinned most: %s.'
               % (ce, uc['days'], ke(out_), ke(lo_), format(uc['hi'], ','), ke(ga_), format(uc['lo'], ','), ke(mi_), de_)),
              ('變厚最多', 'Thickened most', '+%s 萬顆' % wz(up[0][1]) if up else '—', '+%sK BTC' % ke(up[0][1]) if up else '—', 'neu',
               '%s 到 %s 這 %d 天，變厚最多的三格：%s。幣最後一次在鏈上移動的價位，就是它在這張圖上的位置；一格變厚，代表有幣在這個價位換了手或換了地址。' % (md(uc['prev']), md(uc['date']), uc['days'], lz),
               'From %s to %s (%d days), the three buckets that thickened most: %s. A coin sits at the price where it last moved on-chain; a bucket thickens when coins change hands or addresses at that price.' % (uc['prev'], uc['date'], uc['days'], le))]
        if uc.get('thin') and uc.get('thick'):
            tn, tk = uc['thin'], uc['thick']
            it.append(('現價附近最薄', 'Thinnest near price', '%gK' % (tn['p'] / 1000), '%gK' % (tn['p'] / 1000), 'neu',
               '收盤上下 5%% 內最薄的一格是 %s，只有 %s 萬顆；最厚的是 %s，%s 萬顆。薄的地方沒什麼人的成本，價格經過時比較少人防守或解套。這只說明那裡的籌碼少，不代表價格會去那裡。' % (bk(tn['p']), wz(tn['btc']), bk(tk['p']), wz(tk['btc'])),
               'Within 5%% of the close the thinnest bucket is %s with only %sK BTC; the thickest is %s with %sK. Few holders have their cost in a thin bucket, so fewer defend it or sell at break-even there. It only says supply is light there, not that price will go there.' % (bk(tn['p']), ke(tn['btc']), bk(tk['p']), ke(tk['btc']))))
        X['urpdchg'] = dict(k='urpdchg', zh='籌碼搬家：近 7 天哪裡變厚、哪裡變薄', en='Supply on the move: 7-day change by price', hz='近 7 天換了價位的幣（淨額）', he='Coins that changed price in 7 days (net)',
          hs=dict(v='%s 萬顆' % wz(out_), ve='%sK BTC' % ke(out_), f='txt'), src='Bitview · ' + md(uc['date']), srce='Bitview · ' + md(uc['date']),
          dist=dict(kind='sign', pg=0, step=uc['width'], rows=uc['rows'], unit='dbtc', now=1, la=['變薄', 'Thinner'], lb=['變厚', 'Thicker'],
                    zone=[uc['lo'], uc['hi'], '這 7 天的價格範圍', 'Price range of these 7 days'],
                    leg=[['up', '變厚：有幣在這個價位移動進來', 'Thicker: coins moved in at this price'], ['dn', '變薄：原本在這個價位的幣移走了', 'Thinner: coins that sat at this price moved away']]),
          say=own(it, '%s 萬顆換了價位：賠錢移動 %s 萬、賺錢移動 %s 萬' % (wz(out_), wz(lo_), wz(ga_)), '%sK BTC changed price: %sK at a loss, %sK at a profit' % (ke(out_), ke(lo_), ke(ga_))),
          dz='籌碼分布（URPD）今天減 7 天前，每 $1,000 一格。往右的綠色是變厚，往左的紅色是變薄；灰底是這 7 天的價格範圍。幣一移動，原本的那一格變薄、移動當時價位的那一格變厚，所以變厚的格子都在灰底裡。看變薄的格子在哪，就知道這些幣原本的成本：在灰底上方的，是比現在貴的時候買的，移動時是賠的；在灰底下方的，移動時是賺的。鏈上移動不一定是買賣，交易所整理錢包、換地址也算；資料是逐筆 UTXO，沒有做實體歸併，和「籌碼分布」那張每 $2,000 一格的來源不同，數字會有小差異。只作讀值。',
          de='Today\'s supply distribution (URPD) minus the one from 7 days ago, in $1,000 buckets. Green bars to the right thickened, red bars to the left thinned; the grey band is the price range of these 7 days. When a coin moves, its old bucket thins and the bucket at the price of the move thickens, so the thickening sits inside the grey band. Where the thinning sits tells you what those coins cost: above the band they were bought higher and moved at a loss; below it they moved at a profit. On-chain moves are not all sales: exchange wallet reshuffles and address changes count too. The data is per UTXO with no entity adjustment and comes from a different source than the $2,000-bucket distribution chart, so figures differ slightly. A reading only.')
    X['cohort'] = dict(k='cohort', zh='長短期持有者供給', en='Long- vs short-term holder supply', hz='短期持有者平均成本', he='STH average cost',
      dist=dict(kind='split', cl='ac', cr='c3', la=['短期持有者', 'Short-term'], lb=['長期持有者', 'Long-term'], zone=([co['window']['lo'], co['window']['hi'], '近 155 天的價格範圍', 'Price range of the last 155 days'] if co.get('window') else None), step=co['width'], rows=[[r[0], round(r[2]), round(r[1])] for r in co['rows']], unit='btc', leg=[['c3', '長期持有者（155 天以上）', 'Long-term holders (155d+)'], ['ac', '短期持有者', 'Short-term holders']]),
      hs=dict(v=co['tot']['sth_cost'], f='usd0'), dz='同一張籌碼分布，依持有時間分成兩群，背對背放：左邊是短期持有者，右邊是長期持有者。短期持有者的幣在現價上方，是套牢的賣壓；在現價下方，是第一層支撐。', de='The same distribution split by holding time, back to back: short-term holders on the left, long-term on the right. Short-term holder coins above price are underwater sellers; below price they form the first support.')
    _cs = co.get('src'); _cn = 'Bitview' if _cs == 'bitview' else 'CheckOnChain' if _cs == 'checkonchain' else None   # 2026-11-16：「現在」那張的來源寫在卡片上（Bitview；抓不到時是 CheckOnChain，再不行是推算）
    X['cohort']['src'] = (_cn or '推算') + ' · ' + md(co.get('now_date') or co['date']); X['cohort']['srce'] = (_cn or 'Estimate') + ' · ' + md(co.get('now_date') or co['date'])
    # ── 價位 › 短線的牆 ──
    op = L['deriv']['viz']['options']; g = L['deriv']['gex']; lh = L['deriv']['liq_heat']; ob = L['orderbook']
    X['strike'] = dict(k='strike', zh='履約價分布', en='Open interest by strike', hz='最大痛點（%s 到期）' % op['strikes']['expiry'][5:].replace('-', '/'), he='Max pain (%s expiry)' % op['strikes']['expiry'][5:].replace('-', '/'),
      dist=dict(kind='split', rows=op['strikes']['rows'], unit='n', la=['賣權', 'Puts'], lb=['買權', 'Calls'], leg=[['dn', '賣權未平倉', 'Put open interest'], ['up', '買權未平倉', 'Call open interest']]),
      hs=dict(v=op['strikes']['maxpain'], f='usd0'), dz='主要到期日在各個履約價的未平倉量，左邊是賣權、右邊是買權。量大的履約價在到期前常常變成關卡。', de='Open interest by strike for the main expiry: puts on the left, calls on the right. Strikes with large open interest often act as levels into expiry.')
    og = (L['deriv'].get('options') or {}).get('grid')
    if og and len(og.get('exps') or []) >= 3:   # 立體檢視（2026-11-16，規則見 page.html ㉛）：同一張卡多一個檢視，原本的圖是第一個、打開時還是它
        X['strike']['modes'] = [dict(mz='單一到期', me='One expiry'), dict(mz='全部到期', me='All expiries')]
        X['strike']['d3'] = dict(kind='opt', spot=og['spot'], k0=og['k0'], kw=og['kw'], nk=og['nk'], sel=op['strikes']['expiry'], exps=[{k: e[k] for k in ('d', 'dte', 'c', 'p', 'tc', 'tp', 'pain', 'top')} for e in og['exps']],
                                 srcz='「全部到期」把未平倉 2,000 顆以上的到期日排成一排，每 $2,000 一格，只畫 $%dk 到 $%dk；平面是其中一個到期日，賣權在下、買權疊在上。' % (og['k0'] // 1000, (og['k0'] + og['nk'] * og['kw']) // 1000),
                                 srce='"All expiries" lines up every expiry with at least 2,000 BTC of open interest, in $2,000 buckets from $%dk to $%dk; the flat view is one expiry, puts at the bottom and calls stacked on top.' % (og['k0'] // 1000, (og['k0'] + og['nk'] * og['kw']) // 1000))
    gn = [r for r in g['rows'] if abs(r[0] / float(g.get('spot') or close) - 1) <= .10]; gk = ([max(gn, key=lambda r: r[2])[0]] if gn and max(r[2] for r in gn) > 0 else []) + ([min(gn, key=lambda r: r[2])[0]] if gn and min(r[2] for r in gn) < 0 else [])   # 照現有網站：現價 ±10% 內最大的正 Gamma 和最大的負 Gamma 用全色，其餘暗掉
    X['gex'] = dict(k='gex', zh='Gamma 曝險（推算）', en='Gamma exposure (estimated)', hz='全部合計，百萬美元／1%', he='Total, $M per 1% move',
      dist=dict(kind='sign', pg=0, rows=[[r[0], r[2]] for r in g['rows']], keys=gk, unit='m', la=['為負：放大波動', 'Negative: amplifies'], lb=['為正：定住價格', 'Positive: pins'], leg=[['up', 'Gamma 為正（定住價格）', 'Positive gamma (pins price)'], ['dn', 'Gamma 為負（放大波動）', 'Negative gamma (amplifies moves)'], ['k2', '亮的兩條：現價 ±10% 內最大的正、負 Gamma', 'Bright bars: largest positive and negative gamma within ±10%']]),
      hs=dict(v=g['total'], f='s1'), dz='做市商在各個履約價的 Gamma。為正的價位，做市商會逆著價格買賣，價格容易被定住；為負的價位會順著價格買賣，波動會被放大。這是推算，不是實際部位。', de='Dealer gamma by strike. Where it is positive, dealers trade against the move and price tends to pin; where negative, they trade with it and moves are amplified. Estimated, not actual positions.')
    hb_ = __import__('base64').b64decode(lh['heat']); last = hb_[-lh['nb']:]
    w5 = lh.get('within5') or {}
    nz_ = sorted(v for v in hb_ if v); htop = max(1, nz_[int(len(nz_) * .998)]) if nz_ else 255   # 色階上限：整份快照的 99.8 百分位（照舊版 liqTopOf）
    hbands = [dict(b, side='long') for b in (lh.get('below') or [])[:1]] + [dict(b, side='short') for b in (lh.get('above') or [])[:1]]
    X['liq'] = dict(k='liq', zh='清算地圖（推算）', en='Liquidation map (estimated)', hz='現價下方 5% 內的多單清算，顆', he='Long liquidations within 5% below, BTC',
      dist=dict(kind='pos', pg=0, step=lh['step'] * 5, rows=[[lh['lo'] + i * lh['step'], sum(last[i:i + 5])] for i in range(0, lh['nb'], 5)], unit='rel', leg=[['up', '現價上方：空單會被清算', 'Above price: shorts get liquidated'], ['dn', '現價下方：多單會被清算', 'Below price: longs get liquidated']],
        heat=dict(t0=lh['t0'], n=lh['hours'], hr=lh.get('hr'), lo=lh['lo'], step=lh['step'], nb=lh['nb'], cap=lh['cap'], top=htop, heat=lh['heat'], candles=lh['candles'], close=lh['close'], bands=hbands, long=lh.get('long'))), wide=1,
      hs=dict(v=w5.get('below'), f='btc0'), dz='業界常見的清算熱力圖（類似 CoinGlass）。橫軸是最近 7 天、每小時一欄，縱軸是價格；越亮代表推算的待清算量越多，收盤下方是多單、上方是空單，價格走過的亮帶就算清掉了。右邊窄欄是現在這一刻各價位的量，最亮的上下兩段直接標出價位和顆數。做法：多家交易所永續合約的未平倉量增加當成新開倉，假設 5–100 倍槓桿算出清算價。圖上方可以切到「6 個月」：每天一欄、每格 $500，看得到離現價比較遠的大團。這是模型，不是交易所的實際資料。', de='The industry-standard liquidation heatmap (CoinGlass-style). Time runs across the last 7 days, one column per hour; price runs up the side. Brighter means more estimated BTC awaiting liquidation: longs below the close, shorts above; bands that price trades through are cleared. The strip on the right is the amount at each price right now, with the brightest band above and below labelled. Method: rises in perpetual open interest across several exchanges count as new positions, with leverage assumed between 5x and 100x. The switch above the chart changes to six months: one column per day in $500 buckets, which shows the large clusters further from price. A model, not exchange data.')
    X['book'] = dict(k='book', zh='掛單簿', en='Order book', hz='現價 ±15% 內的買單', he='Bids within ±15%',
      dist=dict(kind='side', pg=0, step=ob['wide']['step'], rows=[[r[0], r[1], round(sum(r[2]), 1)] for r in ob['wide']['rows']], unit='usdm', leg=[['up', '買單', 'Bids'], ['dn', '賣單', 'Asks']]),
      hs=dict(v=ob['totals']['wide_bid'], f='usdM'), dz='七個交易所每 $1,000 一格的掛單金額（百萬美元）。這是每天 00:05 UTC 的一張快照，掛單隨時可以撤，只能看大概的位置。', de='Resting orders per $1,000 bucket across seven venues, in $ millions. A snapshot at 00:05 UTC each day; orders can be pulled at any time, so read it for rough location only.')
    # ── 價位 › 這一段行情 ──
    sw = L['price']['swing']; cur = sw['current']; legs = sw['legs']; d0 = dn(legs[0]['start']) - 20; ds = dn(cur['start'])
    prow = [[r[0], r[1], round((r[1] / cur['p0'] - 1) * 100, 1) if r[0] >= ds else None] for r in L['chips']['stress']['rows'] if r[0] >= d0]
    pct = lambda v: ('%+.0f%%' % v).replace('-', '−')
    X['legs'] = dict(k='legs', zh='目前這一段行情', en='The current leg', hz='這一段到現在', he='This leg so far', one=1, f='usd0', rows=prow, hero=1,
      ser=[ser(1, zh='BTC 價格', en='BTC price', col='ink', w=1.5), ser(2, hide=1, f='pct1')],
      spans=[dict(a=dn(x['start']), b=dn(x['end']), col='up' if x['pct'] > 0 else 'dn', op=.08) for x in legs] + [dict(a=ds, b=tE, col='up' if cur['dir'] == 'up' else 'dn', op=.13)],
      marks=[dict(d=dn(x['end']), v=x['p1'], on=0, col='up' if x['pct'] > 0 else 'dn', up=1 if x['pct'] > 0 else 0, zh='%s %d 天' % (pct(x['pct']), x['days']), en='%s %dd' % (pct(x['pct']), x['days'])) for x in legs] +
            [dict(d=dn(cur['ext_date']), v=cur['ext'], on=0, col='up' if cur['dir'] == 'up' else 'dn', up=1 if cur['dir'] == 'up' else 0, zh='這段高點 ' + pct(cur['ext_pct']), en='Leg high ' + pct(cur['ext_pct']))],
      segs=[dict(a=ds, v=cur['end_level'], col='dn')], leg=[['up', '上漲的段落', 'Up legs', 'box'], ['dn', '下跌的段落', 'Down legs', 'box'], ['dn', '這一段的結束線 ' + usd(cur['end_level']), 'Leg-end line ' + usd(cur['end_level']), 'dash']],
      dz='收盤價反轉 15% 才算新的一段。底色是每一段的方向，標記是每段的漲跌幅和天數。虛線是這一段的結束線：收盤跌破它，這一段就算結束。', de='A new leg starts only after a 15% reversal on closes. Shading shows each leg\'s direction; markers give its size and length. The dashed line ends this leg: a close below it and the leg is over.')
    vp = L['price'].get('volprofile') or {}; r20 = L['price']['rows20']; n20 = len(r20)
    X['k20'] = dict(k='k20', zh='近 20 天 K 線', en='Last 20 daily candles', hz='收盤', he='Close', one=1, tf='lin', f='usd0', rows=[[tE - (n20 - 1 - i), r[1], r[2], r[3], r[4]] for i, r in enumerate(r20)],
      ser=[ser(4, t='cand', o=1, h=2, l=3, zh='日 K', en='Daily candles')],
      refs=[dict(v=round(L['price']['ma']['sma20']), col='ac', zh='20 日均線', en='20-day MA')] + ([dict(v=vp['va_high_outer'], col='dn', zh='價值區上緣', en='Value area top'), dict(v=vp['poc'], col='k2', zh='成交最密 ' + usd(vp['poc']), en='Point of control ' + usd(vp['poc']))] if vp else []),   # 照現有網站：20 日均線橘、價值區上緣紅、成交最密灰
      leg=[['up', '收漲', 'Up day', 'box'], ['dn', '收跌', 'Down day', 'box']],
      dz='最近 20 根日 K，加上這 20 天成交最密的價位和價值區（70% 成交量所在的範圍）。', de='The last 20 daily candles, with the price where most volume traded over those 20 days and the value area holding about 70% of it.')
    md = lambda key, f: ((N['modules'].get(key) or {}).get(f), ((E or {}).get('modules', {}).get(key) or {}).get(f))
    grp = lambda zh, en, sz, se, keys: dict(zh=zh, en=en, sz=sz, se=se, charts=[X[k] for k in keys if k in X])
    def chap(id, zh, en, qz, qe, groups=None, mod=None, hero=None, **kw):
        lz, le = md(mod, 'lead') if mod else (None, None); pz, pe = md(mod, 'points') if mod else (None, None)
        return dict(id=id, zh=zh, en=en, qz=qz, qe=qe, groups=groups or [], hero=hero or [0, 0], lead_zh=lz or '', lead_en=le or lz or '', points_zh=pz or [], points_en=pe or pz or [], todo=0 if groups else 1, **kw)
    CYG, CYD = cycle_data.build(L, N, E, dn, X)
    TDG, TDB = today_data.build(L, N, E, dn, pm)
    TDB['px20'] = [[tE - (n20 - 1 - i_), r_[4]] for i_, r_ in enumerate(r20)]   # 頭部那個大數字上面壓的價格線
    EXG, EXR = exit_data.build(L, N, E, dn, X)
    SLG = sell_data.build(L, N, E, dn, X)
    LVG = lev_data.build(L, N, E, dn, X)
    BYG = buy_data.build(L, N, E, dn, X)
    def hrows(c):   # 一張圖的主要數列（大數字那一條）
        if not c: return [], None
        s_ = dict(c)
        if c.get('modes'): s_.update(c['modes'][0])
        if not s_.get('rows') or not s_.get('ser'): return [], None
        q_ = s_['ser'][s_.get('hero', 0)]; col = q_['c']
        return [(r[0], r[col]) for r in s_['rows'] if len(r) > col and r[col] is not None], (q_.get('f') or s_.get('f'))
    BX = {c['k']: c for g_ in BYG for c in g_['charts']}; LX = {c['k']: c for g_ in LVG for c in g_['charts']}; tE_ = dn(L['meta']['bar_date'])
    def fsrc(key, zh, en, side, inv=0):
        rows, f = hrows(BX.get(key))
        if not rows: return None
        v = rows[-1][1]; hist = sorted(abs(r[1]) for r in rows if r[0] >= tE_ - 365) or [abs(v)]
        p90 = hist[min(len(hist) - 1, int(len(hist) * .9))] or 1e-9
        return dict(k=key, zh=zh, en=en, v=v, f=f, dir=(1 if v > 0 else -1 if v < 0 else 0) * (-1 if inv else 1), st=round(max(0.0, min(1.0, abs(v) / p90)), 2), side=side)
    FS = [fsrc('etf', '現貨 ETF', 'Spot ETFs', 'L'), fsrc('pr-us', '美國現貨溢價', 'US spot premium', 'L'), fsrc('pr-asia', '亞洲場外溢價', 'Asia OTC premium', 'L'), fsrc('kp', '韓國溢價', 'Korea premium', 'L'), fsrc('exflow', '交易所淨流量', 'Exchange Netflow', 'L', 1), fsrc('svd', '現貨主動買賣', 'Spot taker flow', 'L'),
          fsrc('ad', '表觀需求', 'Apparent demand', 'R'), fsrc('rcliq', '已實現市值 30 日', 'Realized cap, 30-day', 'R'), fsrc('stab', '穩定幣供給', 'Stablecoin supply', 'R'), fsrc('whale', '大戶 30 日', 'Whales, 30-day', 'R'), fsrc('lthnet', '長期持有者 30 日', 'Long-term holders, 30-day', 'R')]
    FS = [x for x in FS if x]; FLOW = dict(src=FS, nb=sum(1 for x in FS if x['dir'] > 0), ns=sum(1 for x in FS if x['dir'] < 0)) if len(FS) >= 4 else None
    def crow(key, zh, en):
        rows, f = hrows(LX.get(key)); rows = [r for r in rows if r[0] >= tE_ - 365]
        if len(rows) < 30: return None
        vals = sorted(r[1] for r in rows); v = rows[-1][1]; n = len(vals); lo = vals[int(n * .01)]; hi = vals[min(n - 1, int(n * .99))]
        if hi <= lo: return None
        NB = 24; bi = lambda x: max(0, min(NB - 1, int((x - lo) / (hi - lo) * NB))); bins = [0] * NB
        for x in vals: bins[bi(x)] += 1
        return dict(k=key, zh=zh, en=en, v=v, f=f, pct=int(round(sum(1 for x in vals if x <= v) / n * 100)), bins=bins, bi=bi(v), c10=bi(vals[int(n * .1)]) - 1, c90=bi(vals[min(n - 1, int(n * .9))]) + 1)
    CR = [crow('fh', '資金費率', 'Funding rate'), crow('oih', '未平倉量', 'Open interest'), crow('lsa', '持多單的帳戶占比', 'Accounts long'), crow('lqv', '清算裡多單的比例', 'Long share of liquidations'), crow('vol', '隱含 − 實際波動', 'Implied − realized vol'), crow('prem', '選擇權買方權利金差', 'Option premium, calls − puts'), crow('fng', '恐懼貪婪', 'Fear & Greed'), crow('wiki', '維基瀏覽量', 'Wikipedia views')]
    CR = [x for x in CR if x]; CROWD = dict(rows=CR, hot=sum(1 for x in CR if x['pct'] >= 90), cold=sum(1 for x in CR if x['pct'] <= 10)) if len(CR) >= 4 else None
    CH = [
      chap('today', '今天', 'Today', '今天發生什麼、要注意什麼', 'What happened today and what to watch', brief=TDB, groups=TDG),
      chap('cycle', '週期', 'Cycle', '現在在週期的哪裡', 'Where we are in the cycle', mod='cycle', dial=CYD, groups=CYG),
      chap('lv', '價位', 'Levels', '價格站在哪些成本和關卡上', 'Which cost bases and levels price is standing on', mod='market', map=1, groups=[
        grp('成本線', 'Cost lines', '各群人的成本和均線在哪裡', 'Where each group\'s cost and the moving averages sit', [k_ for k_ in ['levels', 'sthgap', 'quant', 'floors', 'tiercost', 'etfcost'] if k_ not in ('floors', 'tiercost') or k_ in X]),
        grp('籌碼在哪', 'Where supply sits', '哪些價位的籌碼厚、哪些薄', 'Which prices hold thick supply and which thin', [k_ for k_ in ['urpd', 'urpdchg', 'cohort', 'conc', 'pnlb'] if k_ != 'pnlb' or 'pnlb' in X]),
        grp('短線的牆', 'Near-term walls', '選擇權、清算和掛單堆在哪裡', 'Where options, liquidations and resting orders pile up', ['strike', 'gex', 'liq', 'book']),
        grp('這一段行情', 'This leg', '現在這一段走了多遠、到哪裡算結束', 'How far this leg has run and where it ends', ['legs', 'k20'])]),
      chap('sell', '賣壓', 'Selling', '賣壓出清了沒', 'Has the selling been worked through', mod='onchain', groups=SLG, hl=(X.get('pullback') or {}).get('list', {}).get('rows'), hlz='回調壓力清單', hle='Pullback pressure checklist'),
      chap('buy', '買盤', 'Demand', '誰在買、錢從哪裡來', 'Who is buying and where the money comes from', mod='flows', groups=BYG, flow=FLOW),
      chap('lev', '槓桿', 'Leverage', '槓桿和情緒擠不擠', 'How crowded leverage and sentiment are', mod='deriv', groups=LVG, crowd=CROWD),
      chap('exit', '出場', 'Exit', '那我該怎麼做', 'So what do I do', mod='exit', run=EXR, groups=EXG),
    ]
    for ch_ in CH:   # 三年的預設範圍會切掉一半以上標注（標記、背離連線、底色期間、直線）的圖，預設改看全部
        for g_ in ch_['groups']:
            for c_ in g_['charts']:
                if c_.get('rng') is not None: continue
                vs_ = [dict(c_, **m_) for m_ in c_['modes']] if c_.get('modes') else [c_]; tot_ = hid_ = 0
                for s_ in vs_:
                    if not s_.get('rows') or not s_.get('ser'): continue
                    t0_ = max(s_['rows'][0][0], tE - 1095)
                    for k_ in ('marks', 'links', 'spans', 'vl'):
                        for m_ in s_.get(k_) or []:
                            tot_ += 1; hid_ += 1 if m_.get('b', m_.get('d', tE)) < t0_ else 0
                if tot_ >= 2 and hid_ * 2 >= tot_: c_['rng'] = 0
    return dict(px=oc['px'], kw=oc['kw'], close=close, chapters=CH)
