# -*- coding: utf-8 -*-
"""整站骨架原型的資料：照「一個今天、六個問題」分章。價位是完整的一片；賣壓、買盤、週期先放已經做好的圖。build.py 會 import。"""
import oc_data, pm_data, cycle_data, today_data, exit_data, sell_data, lev_data, buy_data

def build(L, N, E, dn):
    oc = oc_data.build(L, N, E, dn); X = dict(oc['charts']); pm = pm_data.build(L); tE = dn(L['meta']['bar_date']); close = pm['px']
    ser = lambda c, **k: dict(c=c, **k)
    usd = lambda v: '$' + format(int(round(v)), ',')
    # ── 價位 › 成本線 ──
    lv = L['cycle']['levels']
    X['levels'] = dict(k='levels', zh='成本線與均線', en='Cost bases and moving averages', hz='收盤', he='Close', one=1, tf='lin', f='usd0', rows=lv['rows'],
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
    if not L['flows'].get('etfcost'):
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
    X['urpd'] = dict(k='urpd', zh='籌碼分布（URPD）', en='Supply distribution (URPD)', hz='現價這一格佔流通量', he='Share of supply in the current bucket',
      dist=dict(kind='one', step=uv['width'], rows=uv['band'], hl=hl, base='color-mix(in srgb, var(--c3) 45%, var(--k2))', unit='btc', leg=[['c4', '現價附近最厚的一段', 'Thickest stretch near price'], ['c5', '另一側最薄的一段', 'Thinnest stretch on the other side'], ['color-mix(in srgb, var(--c3) 45%, var(--k2))', '其餘（每 $2,000 一格）', 'The rest ($2,000 buckets)']]),
      hs=dict(v=u['cur_pct'], f='p2'), dz='每一格是最後一次在那個價位移動的幣。厚的地方是很多人的成本，價格到那裡容易停；薄的地方沒什麼人的成本，價格容易快速穿過。', de='Each bucket holds the coins that last moved at that price. Thick zones are where many holders\' costs sit and price tends to stall; thin zones have few and price tends to move through quickly.')
    X['cohort'] = dict(k='cohort', zh='長短期持有者籌碼', en='Long- vs short-term holder supply', hz='短期持有者平均成本', he='STH average cost',
      dist=dict(kind='split', cl='ac', cr='c3', la=['短期持有者', 'Short-term'], lb=['長期持有者', 'Long-term'], zone=([co['window']['lo'], co['window']['hi'], '近 155 天的價格範圍', 'Price range of the last 155 days'] if co.get('window') else None), step=co['width'], rows=[[r[0], round(r[2]), round(r[1])] for r in co['rows']], unit='btc', leg=[['c3', '長期持有者（155 天以上）', 'Long-term holders (155d+)'], ['ac', '短期持有者', 'Short-term holders']]),
      hs=dict(v=co['tot']['sth_cost'], f='usd0'), dz='同一張籌碼分布，依持有時間分成兩群，背對背放：左邊是短期持有者，右邊是長期持有者。短期持有者的幣在現價上方，是套牢的賣壓；在現價下方，是第一層支撐。', de='The same distribution split by holding time, back to back: short-term holders on the left, long-term on the right. Short-term holder coins above price are underwater sellers; below price they form the first support.')
    # ── 價位 › 短線的牆 ──
    op = L['deriv']['viz']['options']; g = L['deriv']['gex']; lh = L['deriv']['liq_heat']; ob = L['orderbook']
    X['strike'] = dict(k='strike', zh='履約價分布', en='Open interest by strike', hz='最大痛點（%s 到期）' % op['strikes']['expiry'][5:].replace('-', '/'), he='Max pain (%s expiry)' % op['strikes']['expiry'][5:].replace('-', '/'),
      dist=dict(kind='split', rows=op['strikes']['rows'], unit='n', la=['賣權', 'Puts'], lb=['買權', 'Calls'], leg=[['dn', '賣權未平倉', 'Put open interest'], ['up', '買權未平倉', 'Call open interest']]),
      hs=dict(v=op['strikes']['maxpain'], f='usd0'), dz='主要到期日在各個履約價的未平倉量，左邊是賣權、右邊是買權。量大的履約價在到期前常常變成關卡。', de='Open interest by strike for the main expiry: puts on the left, calls on the right. Strikes with large open interest often act as levels into expiry.')
    gn = [r for r in g['rows'] if abs(r[0] / float(g.get('spot') or close) - 1) <= .10]; gk = ([max(gn, key=lambda r: r[2])[0]] if gn and max(r[2] for r in gn) > 0 else []) + ([min(gn, key=lambda r: r[2])[0]] if gn and min(r[2] for r in gn) < 0 else [])   # 照現有網站：現價 ±10% 內最大的正 Gamma 和最大的負 Gamma 用全色，其餘暗掉
    X['gex'] = dict(k='gex', zh='Gamma 曝險（推算）', en='Gamma exposure (estimated)', hz='全部合計，百萬美元／1%', he='Total, $M per 1% move',
      dist=dict(kind='sign', pg=0, rows=[[r[0], r[2]] for r in g['rows']], keys=gk, unit='m', la=['為負：放大波動', 'Negative: amplifies'], lb=['為正：定住價格', 'Positive: pins'], leg=[['up', 'Gamma 為正（定住價格）', 'Positive gamma (pins price)'], ['dn', 'Gamma 為負（放大波動）', 'Negative gamma (amplifies moves)'], ['k2', '亮的兩條：現價 ±10% 內最大的正、負 Gamma', 'Bright bars: largest positive and negative gamma within ±10%']]),
      hs=dict(v=g['total'], f='s1'), dz='做市商在各個履約價的 Gamma。為正的價位，做市商會逆著價格買賣，價格容易被定住；為負的價位會順著價格買賣，波動會被放大。這是推算，不是實際部位。', de='Dealer gamma by strike. Where it is positive, dealers trade against the move and price tends to pin; where negative, they trade with it and moves are amplified. Estimated, not actual positions.')
    hb_ = __import__('base64').b64decode(lh['heat']); last = hb_[-lh['nb']:]
    w5 = lh.get('within5') or {}
    nz_ = sorted(v for v in hb_ if v); htop = max(1, nz_[int(len(nz_) * .998)]) if nz_ else 255   # 色階上限：整份快照的 99.8 百分位（照舊版 liqTopOf）
    hbands = [dict(b, side='long') for b in (lh.get('below') or [])[:1]] + [dict(b, side='short') for b in (lh.get('above') or [])[:1]]
    X['liq'] = dict(k='liq', zh='清算價位（推算）', en='Liquidation levels (estimated)', hz='現價下方 5% 內的多單清算，顆', he='Long liquidations within 5% below, BTC',
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
      dz='最近 20 根日 K，加上這 20 天成交最密的價位和價值區（七成成交量所在的範圍）。', de='The last 20 daily candles, with the price where most volume traded over those 20 days and the value area holding about 70% of it.')
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
    FS = [fsrc('etf', '現貨 ETF', 'Spot ETFs', 'L'), fsrc('pr-us', '美國現貨溢價', 'US spot premium', 'L'), fsrc('pr-asia', '亞洲場外溢價', 'Asia OTC premium', 'L'), fsrc('kp', '韓國溢價', 'Korea premium', 'L'), fsrc('exflow', '交易所淨流量', 'Exchange netflow', 'L', 1), fsrc('svd', '現貨主動買賣', 'Spot taker flow', 'L'),
          fsrc('ad', '表觀需求', 'Apparent demand', 'R'), fsrc('rcliq', '實現市值 30 日', 'Realized cap, 30-day', 'R'), fsrc('stab', '穩定幣供給', 'Stablecoin supply', 'R'), fsrc('whale', '大戶 30 日', 'Whales, 30-day', 'R'), fsrc('lthnet', '長期持有者 30 日', 'Long-term holders, 30-day', 'R')]
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
        grp('成本線', 'Cost lines', '各群人的成本和均線在哪裡', 'Where each group\'s cost and the moving averages sit', ['levels', 'sthgap', 'quant', 'etfcost']),
        grp('籌碼在哪', 'Where supply sits', '哪些價位的籌碼厚、哪些薄', 'Which prices hold thick supply and which thin', ['urpd', 'cohort', 'conc']),
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
