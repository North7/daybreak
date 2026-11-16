# -*- coding: utf-8 -*-
"""買盤頁的讀數（2026-11-17，取代舊版抽來的讀數；規則見 reads.py）。每個函式回傳 (一句結論中, 英, [最多三條事實])"""
import datetime as dt
from reads import sg, pc, pu, n0, sn0, wan, kb, yi, bn, md, ymd, ym, ord_en, it, M, mde, ymde, yme

def etf(L):
    E = [e for e in L['flows']['etf'] if not e.get('partial')]
    if len(E) < 8: return None
    last = E[-1]; s = 1 if last['musd'] >= 0 else -1; run = []
    for e in reversed(E):
        if (1 if e['musd'] >= 0 else -1) != s: break
        run.append(e)
    tot = sum(e['musd'] for e in run); f5 = sum(e['musd'] for e in E[-5:]); px = L['price']['bar']['c']; btc = tot * 1e6 / px
    days = (dt.date.fromisoformat(last['d']) - dt.date.fromisoformat(run[-1]['d'])).days + 1; mined = days * 450
    wz, we = ('淨流出', 'net outflows') if s < 0 else ('淨流入', 'net inflows')
    sz = '現貨 ETF 連 %d 個交易日%s，合計 %s（到 %s）。' % (len(run), wz, yi(abs(tot), False), md(last['d']))
    se = 'Spot ETFs have seen %d straight trading days of %s, %s in all (to %s).' % (len(run), we, bn(abs(tot), False), mde(last['d']))
    return sz, se, [
        it('最近完整日', 'Latest full day', yi(last['musd']), bn(last['musd']), 'down' if last['musd'] < 0 else 'up', '%s 的%s。' % (md(last['d']), '淨流出' if last['musd'] < 0 else '淨流入'), 'Net %s on %s.' % ('outflow' if last['musd'] < 0 else 'inflow', mde(last['d']))),
        it('這一段合計', 'This run', yi(tot), bn(tot), 'down' if s < 0 else 'up', '換算約 %s，是同期礦工新挖約 %s 顆的 %.1f 倍。' % (wan(abs(btc), False), n0(mined), abs(btc) / mined),
           'About %s at today\'s close, %.1f times the roughly %s BTC miners issued over the same days.' % (kb(abs(btc), False), abs(btc) / mined, n0(mined))),
        it('近 5 個交易日', 'Last 5 trading days', yi(f5), bn(f5), 'down' if f5 < 0 else 'up', '看連續方向和 5–7 天合計，比單日重要。', 'The run and the 5–7 day total matter more than any single day.')]

def cot(L):
    c = L['flows']['cot']; d = md(c['date'])
    sz = '槓桿基金淨%s %s、資產管理機構淨%s %s（%s 持倉）。' % ('空' if c['lev'] < 0 else '多', wan(abs(c['lev']), False), '多' if c['am'] >= 0 else '空', wan(abs(c['am']), False), d)
    se = 'Leveraged funds are net %s %s and asset managers net %s %s (positions as of %s).' % ('short' if c['lev'] < 0 else 'long', kb(abs(c['lev']), False), 'long' if c['am'] >= 0 else 'short', kb(abs(c['am']), False), mde(c['date']))
    return sz, se, [
        it('槓桿基金', 'Leveraged funds', wan(c['lev']), kb(c['lev']), 'neu', '4 週前比 %s。空單多半是基差交易，淨空不等於看空。' % wan(c['lev4']), '%s versus four weeks ago. Their shorts are mostly basis trades, so net short is not a bearish bet.' % kb(c['lev4'])),
        it('資產管理機構', 'Asset managers', wan(c['am']), kb(c['am']), 'neu', '4 週前比 %s；%s 年以來第 %d 百分位。' % (wan(c['am4']), c['since'][:4], round(c['am_pct'])), '%s versus four weeks ago; the %s percentile since %s.' % (kb(c['am4']), ord_en(c['am_pct']), c['since'][:4])),
        it('CME 未平倉', 'CME open interest', wan(c['oi'], False), kb(c['oi'], False), 'neu', '比一年前%s %.0f%%。' % ('少' if c['oi52'] < 0 else '多', abs(c['oi52'])), '%.0f%% %s than a year ago.' % (abs(c['oi52']), 'lower' if c['oi52'] < 0 else 'higher'))]

def pr_us(L):
    p = L['flows']['cb_premium']; u = p['usdt']; r = p['raw']; lo, hi = p['band']
    st = ('比海外弱' if p['avg7'] < lo else '比海外積極' if p['avg7'] > hi else '和海外差不多'); ste = ('weaker than offshore' if p['avg7'] < lo else 'stronger than offshore' if p['avg7'] > hi else 'about the same as offshore')
    sz = '扣掉 USDT 後，兩地價差 7 日平均 %s：美國買盤%s。' % (pc(p['avg7'], 3), st); se = 'Net of USDT, the 7-day average gap is %s: US buying is %s.' % (pc(p['avg7'], 3), ste)
    return sz, se, [
        it('7 日平均', '7-day average', pc(p['avg7'], 3), pc(p['avg7'], 3), 'neu', '扣掉 USDT 後；30 日平均 %s，近四年第 %d 百分位。' % (pc(p['avg30'], 3), round(p['avg30_pct_own'])), 'Net of USDT; the 30-day average is %s, the %s percentile over four years.' % (pc(p['avg30'], 3), ord_en(p['avg30_pct_own']))),
        it('一般看到的溢價', 'The usual premium', pc(r['avg7'], 3), pc(r['avg7'], 3), 'neu', '沒扣 USDT 的 7 日平均；其中 %s 是 USDT 自己不等於 1 美元。' % pc(u['disc7'], 3), 'The 7-day average before netting out USDT; %s of it is USDT itself trading off $1.' % pc(u['disc7'], 3)),
        it('USDT 對美元', 'USDT vs the dollar', '%.4f' % u['px'], '$%.4f' % u['px'], 'neu', '7 日平均 %s，近四年只有 %d%% 的日子更低；折價代表有人把穩定幣換回美元。' % (pc(u['disc7'], 2), round(u['disc7_pct_own'])),
           '7-day average %s; lower on only %d%% of days in four years. A discount means stablecoins are being swapped back into dollars.' % (pc(u['disc7'], 2), round(u['disc7_pct_own'])))]

def pr_asia(L):
    u = L['flows']['premium3']['usdt']; v = u['pct']
    st, ste = ('接近匯率，亞洲買賣大致平衡' if abs(v) < .5 else '高於匯率，亞洲買盤積極' if v > 0 else '低於匯率，亞洲有人在換回人民幣'), ('close to the exchange rate: buying and selling in Asia are balanced' if abs(v) < .5 else 'above the exchange rate: Asian buyers are keen' if v > 0 else 'below the exchange rate: Asian holders are cashing out')
    return '亞洲場外 USDT 溢價 %s，%s。' % (pc(v, 2), st), 'The Asian OTC USDT premium is %s, %s.' % (pc(v, 2), ste), [
        it('OKX 場外 USDT', 'OKX OTC USDT', '%.3f 人民幣' % u['mid'], 'CNY %.3f' % u['mid'], 'neu', '匯率 %.3f；只有每日快照（%s）。' % (u['fx'], u['ts'][:10].replace('-', '/')), 'Exchange rate %.3f; one snapshot a day (%s).' % (u['fx'], ymde(u['ts'][:10])))]

def pr_perp(L):
    p = L['flows']['premium3']['perp']; q = p['avg7_pct_own']
    st, ste = ('永續偏貴，槓桿多頭偏擠' if q >= 85 else '永續偏便宜，槓桿偏空' if q <= 15 else '和平常差不多，槓桿沒有明顯偏向'), ('perps are rich and leveraged longs crowded' if q >= 85 else 'perps are cheap and leverage leans short' if q <= 15 else 'about normal, with leverage leaning neither way')
    return 'OKX 永續對現貨 %s（7 日平均），%s。' % (pc(p['avg7'], 3), st), 'OKX perps versus spot are %s (7-day average): %s.' % (pc(p['avg7'], 3), ste), [
        it('7 日平均', '7-day average', pc(p['avg7'], 3), pc(p['avg7'], 3), 'neu', '平常（30 日平均）%s；近 %d 天第 %d 百分位。' % (pc(p['avg30'], 3), p['n'], round(q)), 'Normal (30-day average) is %s; the %s percentile of the last %d days.' % (pc(p['avg30'], 3), ord_en(q), p['n']))]

def kp(L):
    k = L['flows']['kp']; h = k['hot90']; b = k['base90']; hot = k['a7'] >= 5
    sz = ('韓國溢價 %s（7 日平均），韓國散戶在追價。' if hot else '韓國溢價 %s（7 日平均），在常態範圍，韓國散戶沒有明顯追價。') % pc(k['a7'], 2)
    se = ('The Korean premium is %s (7-day average): Korean retail is chasing.' if hot else 'The Korean premium is %s (7-day average), within its normal range: no sign of Korean retail chasing.') % pc(k['a7'], 2)
    lh = k['hot'][-1]
    return sz, se, [
        it('7 日平均', '7-day average', pc(k['a7'], 2), pc(k['a7'], 2), 'warn' if hot else 'neu', '最新一天 %s、30 日 %s；近 4 年第 %d 百分位。' % (pc(k['value'], 2), pc(k['a30'], 2), round(k['pct4'])), 'Latest day %s, 30-day %s; the %s percentile over four years.' % (pc(k['value'], 2), pc(k['a30'], 2), ord_en(k['pct4']))),
        it('衝上 5% 之後', 'After topping 5%', '%d/%d' % (h['up'], h['n']), '%d/%d' % (h['up'], h['n']), 'neu', '90 天後上漲的次數，中位數 %s；任一天是 %d%% 上漲、%s。' % (pc(h['med']), b['up'], pc(b['med'])), 'Rises 90 days later, median %s; any day: %d%% up, %s.' % (pc(h['med']), b['up'], pc(b['med']))),
        it('最近一次', 'Last time', ym(lh['start']), yme(lh['start']), 'neu', '%s 衝上 5%%（$%s），90 天後 %s。' % (ymd(lh['start']), n0(lh['price']), pc(lh['r90']) if lh.get('r90') is not None else '還沒滿 90 天'), 'Topped 5%% on %s at $%s; %s 90 days later.' % (ymde(lh['start']), n0(lh['price']), pc(lh['r90']) if lh.get('r90') is not None else 'not yet'))]

def exflow(L):
    x = L['flows']['exflow']; o, i_, b = x['out_r90'], x['in_r90'], x['base90']
    sz = ('幣在離開交易所：30 天合計 %s，已連續 %d 天淨流出。' if x['s30'] < 0 else '幣在流入交易所：30 天合計 %s，已連續 %d 天淨流入。') % (wan(x['s30']), x['run'])
    se = ('Coins are leaving exchanges: %s over 30 days, net outflows for %d days.' if x['s30'] < 0 else 'Coins are moving onto exchanges: %s over 30 days, net inflows for %d days.') % (kb(x['s30']), x['run'])
    return sz, se, [
        it('30 天合計', '30-day total', wan(x['s30']), kb(x['s30']), 'neu', '近 4 年第 %d 百分位；30 天前 %s。' % (round(x['pct4']), wan(x['s30_30'])), 'The %s percentile over four years; %s thirty days ago.' % (ord_en(x['pct4']), kb(x['s30_30']))),
        it('強流出之後', 'After heavy outflows', '%d/%d' % (o['up'], o['n']), '%d/%d' % (o['up'], o['n']), 'neu', '進入近 4 年最低 10%% 後 90 天上漲次數，中位數 %s（任一天 %d%%、%s）。' % (pc(o['med']), b['up'], pc(b['med'])), 'Rises 90 days after entering the lowest 10%%, median %s (any day: %d%%, %s).' % (pc(o['med']), b['up'], pc(b['med']))),
        it('強流入之後', 'After heavy inflows', '%d/%d' % (i_['up'], i_['n']), '%d/%d' % (i_['up'], i_['n']), 'neu', '中位數 %s。流量本身分不出方向，要和價格一起看。' % pc(i_['med']), 'Median %s. Flows alone do not tell direction; read them with price.' % pc(i_['med']))]

def exch(L):
    e = L['onchain']['exchange']; c30, c90 = e['exchange_supply_chg30_pct'], e['exchange_supply_chg90_pct']
    sz = '交易所供給 %s，30 天 %s（幣在%s交易所）。' % (pu(e['exchange_supply_share_pct'], 2), pc(c30, 2), '流入' if c30 > 0 else '離開')
    se = 'Exchange supply is %s, %s over 30 days (coins are %s exchanges).' % (pu(e['exchange_supply_share_pct'], 2), pc(c30, 2), 'moving onto' if c30 > 0 else 'leaving')
    return sz, se, [
        it('30 天', '30 days', pc(c30, 2), pc(c30, 2), 'neu', '流入代表潛在賣壓增加，流出代表幣被提走保管。' if c30 > 0 else '幣被提走保管，潛在賣壓減少。', 'Inflows add potential selling; outflows mean coins are being withdrawn.' if c30 > 0 else 'Coins are being withdrawn, which lowers potential selling.'),
        it('90 天', '90 days', pc(c90, 2), pc(c90, 2), 'neu', ('和 30 天方向相反，趨勢還不明確。' if (c30 > 0) != (c90 > 0) else '和 30 天同方向。'), ('The opposite direction to 30 days, so the trend is unclear.' if (c30 > 0) != (c90 > 0) else 'The same direction as 30 days.'))]

def ad(L):
    a = L['onchain']['ad']; y = a['y1']; cb = y['combo']; neg = a['value'] < 0 and y['value'] < 0
    view = it('我們的看法', 'Our read', '需求偏弱' if neg else '需求接得住', 'Demand is weak' if neg else 'Demand is holding', 'warn' if neg else 'neu',
              ('30 天和 1 年都是負的：新買盤追不上舊幣沉澱的速度；30 天版有一部分是一年前換手的回音。' if neg else '至少有一個時間尺度是正的：新買盤還接得住沉澱的速度。'),
              ('Both the 30-day and 1-year readings are negative: old coins being taken up cannot keep pace with coins ageing past a year. Part of the 30-day reading is an echo of turnover a year ago, but the 1-year reading is negative too.' if neg else 'At least one horizon is positive: new buying still keeps pace with coins settling.'), view=1)
    sz = ('30 天和 1 年的表觀需求都是負的，新買盤偏弱。' if neg else '表觀需求 30 天 %s。' % wan(a['value'])); se = ('Apparent demand is negative over both 30 days and a year: new buying is weak.' if neg else 'Apparent demand over 30 days is %s.' % kb(a['value']))
    out = [view, it('30 天', '30 days', wan(a['value']), kb(a['value']), 'warn' if a['value'] < 0 else 'neu', '新挖 %s，1 年以上沒動的幣多了 %s；%s 年以來第 %d 百分位。' % (wan(a['issued30'], False), wan(a['inact_chg30'], False), a['since'][:4], round(a['pct'])),
                       '%s newly mined while coins unmoved for a year rose %s; the %s percentile since %s.' % (kb(a['issued30'], False), kb(a['inact_chg30'], False), ord_en(a['pct']), a['since'][:4])),
           it('1 年', '1 year', wan(y['value']), kb(y['value']), 'neu', '%s 年以來這種組合 %d 天，之後 90 天 %d%% 上漲（任一天 %d%%）。' % (cb['since'][:4], cb['days'], cb['up90_pct'], cb['all_up90_pct']), 'This combination came on %d days since %s; %d%% rose over the next 90 days (any day: %d%%).' % (cb['days'], cb['since'][:4], cb['up90_pct'], cb['all_up90_pct']))]
    return sz, se, out

def dmd(L):
    d = L['onchain']['dmd']; r, b = d['r60'], d['base60']; f = d['flips'][-1]
    both = not d['spot_pos'] and not d['perp_pos']
    sz = ('現貨和永續的需求都在減，兩邊都沒有新買盤。' if both else '現貨需求 %s、永續需求 %s。' % ('增' if d['spot_pos'] else '減', '增' if d['perp_pos'] else '減'))
    se = ('Spot and perpetual demand are both shrinking: no new buying on either side.' if both else 'Spot demand is %s and perpetual demand is %s.' % ('rising' if d['spot_pos'] else 'falling', 'rising' if d['perp_pos'] else 'falling'))
    return sz, se, [
        it('現貨（30 天）', 'Spot (30 days)', wan(d['spot']), kb(d['spot']), 'down' if d['spot'] < 0 else 'up', '表觀需求 30 天。', 'Apparent demand over 30 days.'),
        it('永續（30 天）', 'Perps (30 days)', yi(d['perp']), bn(d['perp']), 'down' if d['perp'] < 0 else 'up', 'OKX 永續主動買 − 主動賣。', 'OKX perpetual taker buys minus sells.'),
        it('現貨轉正之後', 'After spot turns positive', '%d/%d' % (r['up'], r['n']), '%d/%d' % (r['up'], r['n']), 'neu', '60 天後上漲次數，中位數 %s（任一天 %d%%、%s）；上次 %s。' % (pc(r['med']), b['up'], pc(b['med']), ymd(f['date'])), 'Rises 60 days later, median %s (any day: %d%%, %s); last on %s.' % (pc(r['med']), b['up'], pc(b['med']), ymde(f['date'])))]

def capflow(L):
    c = L['onchain']['capflow']; p1, py = c['peaks_m1'], c['peaks_y12']
    return ('一個月內換手 %s、1–2 年沒動 %s：沒有投機狂熱，長線比重在升。' % (pu(c['m1']), pu(c['y12'])) if c['m1'] < 25 else '一個月內換手 %s，投機在升溫。' % pu(c['m1'])), \
           ('Coins turned over within a month are %s and those unmoved for 1–2 years %s: no speculative frenzy, and the long-term share is rising.' % (pu(c['m1']), pu(c['y12'])) if c['m1'] < 25 else 'Coins turned over within a month are %s: speculation is heating up.' % pu(c['m1'])), [
        it('1 個月內換手', 'Turned over in a month', pu(c['m1']), pu(c['m1']), 'neu', '一年前 %s；週期頂部會衝高（%s %s、%s %s）。' % (pu(c['m1_1y']), ym(p1[1][0]), pu(p1[1][1]), ym(p1[3][0]), pu(p1[3][1])), '%s a year ago; it spikes near cycle tops (%s at %s, %s at %s).' % (pu(c['m1_1y']), pu(p1[1][1]), yme(p1[1][0]), pu(p1[3][1]), yme(p1[3][0]))),
        it('1–2 年沒動', 'Unmoved 1–2 years', pu(c['y12']), pu(c['y12']), 'up' if c['y12'] > c['y12_30'] else 'neu', '一年前 %s、30 天前 %s；熊底附近最大（%s %s），多半是放滿一年的幣。' % (pu(c['y12_1y']), pu(c['y12_30']), ym(py[-2][0]), pu(py[-2][1])),
           '%s a year ago and %s thirty days ago; it peaks near bear-market bottoms (%s at %s). Mostly coins passing the one-year mark, so partly just time.' % (pu(c['y12_1y']), pu(c['y12_30']), pu(py[-2][1]), yme(py[-2][0])))]

def grad(L):
    g = L['onchain']['grad']; b = g['back120']; z1, z3 = g['z120'], g['z30']
    dz = lambda z: '價格跌得比資金撤出快很多' if z <= -1 else '價格漲得比資金流入快很多' if z >= 1 else '價格和資金大致同步'
    de = lambda z: 'price is falling much faster than capital is leaving' if z <= -1 else 'price is rising much faster than capital is arriving' if z >= 1 else 'price and capital are roughly in step'
    d1, d3 = g['div120'][-1], g['div30'][-1]; kz = lambda d: '底背離' if d['kind'] == 'bot' else '頂背離'; ke = lambda d: 'bullish divergence' if d['kind'] == 'bot' else 'bearish divergence'
    sh = lambda z: '價格偏弱' if z <= -1 else '價格偏強' if z >= 1 else '大致同步'
    return '近 30 天%s；120 天%s（%s 個標準差）。' % (dz(z3), sh(z1), sg(z1, 2)), 'Over 30 days %s; over 120 days %s (%s standard deviations).' % (de(z3), de(z1), sg(z1, 2)), [
        it('大級別（120 日）', '120-day', sg(z1, 2), sg(z1, 2), 'neu', '最近一次背離：%s %s。' % (ymd(d1['date']), kz(d1)), 'Last divergence: %s on %s.' % (ke(d1), ymde(d1['date']))),
        it('小級別（30 日）', '30-day', sg(z3, 2), sg(z3, 2), 'neu', '最近一次背離：%s %s。小級別容易被消息打破。' % (ymd(d3['date']), kz(d3)), 'Last divergence: %s on %s. The short scale is easily broken by news.' % (ke(d3), ymde(d3['date']))),
        it('120 日背離之後', 'After 120-day divergences', '%d/%d' % (b['bot']['r90']['up'], b['bot']['r90']['n']), '%d/%d' % (b['bot']['r90']['up'], b['bot']['r90']['n']), 'neu',
           '底背離 90 天後上漲的次數，中位數 %s；頂背離 %d/%d、中位數 %s。' % (pc(b['bot']['r90']['med']), b['top']['r90']['up'], b['top']['r90']['n'], pc(b['top']['r90']['med'])),
           'Rises 90 days after a bullish divergence, median %s; after a bearish one %d/%d, median %s.' % (pc(b['bot']['r90']['med']), b['top']['r90']['up'], b['top']['r90']['n'], pc(b['top']['r90']['med'])))]

def rcliq(L):
    r = L['flows']['rc_liq']; e = r['last_episode']; z = r['chg30_pct'] <= 0
    sz = ('實現市值 30 天 %s，新資金停止流入已 %d 天。' % (pc(r['chg30_pct'], 2), r['state_run_days']) if z else '實現市值 30 天 %s，新資金還在流入。' % pc(r['chg30_pct'], 2))
    se = ('Realized cap is %s over 30 days: new money stopped coming in %d days ago.' % (pc(r['chg30_pct'], 2), r['state_run_days']) if z else 'Realized cap is %s over 30 days: new money is still coming in.' % pc(r['chg30_pct'], 2))
    return sz, se, [
        it('30 天變化', '30-day change', pc(r['chg30_pct'], 2), pc(r['chg30_pct'], 2), 'down' if z else 'up', '90 天 %s、180 天 %s。只是資金背景，不是買賣訊號。' % (pc(r['chg90_pct'], 2), pc(r['chg180_pct'], 2)), '%s over 90 days and %s over 180. Background, not a trade signal.' % (pc(r['chg90_pct'], 2), pc(r['chg180_pct'], 2))),
        it('上一次停止流入', 'Last stall', '%d 天' % e['days'], '%d days' % e['days'], 'neu', '%s–%s。' % (ymd(e['start']), ymd(e['end'])), '%s to %s.' % (ymde(e['start']), ymde(e['end'])))]

def stab(L):
    s = L['flows']['stables']; dn = s['chg30_pct'] < 0
    sz = '穩定幣 %s 億美元，30 天%s %s 億（%s），%s。' % (n0(s['usd_b'] * 10), '少' if dn else '多', n0(abs(s['chg30_usd_b']) * 10), pc(s['chg30_pct'], 2), '場外美元在萎縮' if dn else '場外美元在增加')
    se = 'Stablecoin supply is $%.1fB, %s $%.1fB (%s) over 30 days: %s.' % (s['usd_b'], 'down' if dn else 'up', abs(s['chg30_usd_b']), pc(s['chg30_pct'], 2), 'sideline dollars are shrinking' if dn else 'sideline dollars are growing')
    return sz, se, [
        it('30 天', '30 days', '%s 億美元' % sn0(s['chg30_usd_b'] * 10), sg(s['chg30_usd_b']) + 'B', 'down' if dn else 'up', '%s，2021 年以來第 %d 百分位。' % (pc(s['chg30_pct'], 2), round(s['pct30'])), '%s, the %s percentile since 2021.' % (pc(s['chg30_pct'], 2), ord_en(s['pct30']))),
        it('7 天', '7 days', pc(s['chg7_pct'], 2), pc(s['chg7_pct'], 2), 'neu', '90 天 %s。' % pc(s['chg90_pct'], 2), '%s over 90 days.' % pc(s['chg90_pct'], 2))]

def _coh(L): return {c['key']: c for c in L['onchain']['whales']['cohorts']}
def whale(L):
    C = _coh(L); a, b, c = C['100_1k'], C['1k_10k'], C['ge10k']; d30 = a['chg30'] + b['chg30']; d7 = a['chg7'] + b['chg7']
    st = ('這個月在減持' if d30 < 0 else '這個月在加碼') + (('，最近一週仍在賣' if d30 < 0 else '，但最近一週在賣') if d7 < 0 else ('，但最近一週在買' if d30 < 0 else '')); ste = ('trimming this month' if d30 < 0 else 'adding this month') + (', still selling this week' if d7 < 0 else ', buying this week')
    return '大戶 30 天 %s、7 天 %s：%s。' % (wan(d30), wan(d7), st), 'Large holders (100–10K BTC addresses): %s over 30 days and %s over 7: %s.' % (kb(d30), kb(d7), ste), [
        it('100–1K 顆', '100–1K BTC', wan(a['chg30']), kb(a['chg30']), 'neu', '30 天；7 天 %s。' % wan(a['chg7']), '30 days; %s over 7.' % kb(a['chg7'])),
        it('1K–10K 顆', '1K–10K BTC', wan(b['chg30']), kb(b['chg30']), 'neu', '30 天；7 天 %s。' % wan(b['chg7']), '30 days; %s over 7.' % kb(b['chg7'])),
        it('1 萬顆以上', 'Over 10K BTC', wan(c['chg30']), kb(c['chg30']), 'neu', '30 天；多半是交易所和託管，看方向就好。', '30 days; mostly exchanges and custodians, so read the direction only.')]

def whalet(L):
    C = list(_coh(L).values()); up = [c for c in C if c['chg30'] > 0]; lo = min(C, key=lambda c: c['chg30']); hi = max(C, key=lambda c: c['chg30'])
    N = {'lt1': ('1 顆以下', 'under 1 BTC'), '1_10': ('1–10 顆', '1–10 BTC'), '10_100': ('10–100 顆', '10–100 BTC'), '100_1k': ('100–1K 顆', '100–1K BTC'), '1k_10k': ('1K–10K 顆', '1K–10K BTC'), 'ge10k': ('1 萬顆以上', 'over 10K BTC')}
    return '30 天持幣增加 %d 層、減少 %d 層；%s減最多（%s）。' % (len(up), len(C) - len(up), N[lo['key']][0], wan(lo['chg30'])), \
           'Over 30 days %d tiers added and %d trimmed; the %s tier cut most (%s).' % (len(up), len(C) - len(up), N[lo['key']][1], kb(lo['chg30'])), [
        it('加最多', 'Added most', N[hi['key']][0], N[hi['key']][1], 'neu', '30 天 %s。' % wan(hi['chg30']), '%s over 30 days.' % kb(hi['chg30']))]

def lthnet(L):
    l = L['onchain']['lth_color']; r = l['run']; ls = L['onchain']['lsrchg']; ps = l['prev_same']
    sell = r['sign'] < 0; hold = r['price_chg_pct'] > -5
    view = it('我們的看法', 'Our read', '換手中' if sell and hold else '出貨壓價' if sell else '在沉澱', 'Changing hands' if sell and hold else 'Distribution weighs on price' if sell else 'Settling', 'neu' if hold or not sell else 'warn',
              ('籌碼從長期轉到短期持有者，價格沒跌、有人接得住；前幾輪走到新高前都經過這種換手。' if sell and hold else '長期持有者在賣，價格跟著跌。' if sell else '長期持有者在增加持幣。'),
              ('Coins are passing from long- to short-term holders, and someone is absorbing them (price has held). Past cycles all went through this on the way from the true market mean to new highs.' if sell and hold else 'Long-term holders are selling and price is falling with it.' if sell else 'Long-term holders are adding.'), view=1)
    sz = ('長期持有者從 %s 起淨%s %d 天，同期價格 %s。' % (md(r['start']), '減' if sell else '增', r['days'], pc(r['price_chg_pct'], 0)))
    se = 'Long-term holders have been net %s for %d days since %s, with price %s over the same stretch.' % ('sellers' if sell else 'buyers', r['days'], mde(r['start']), pc(r['price_chg_pct'], 0))
    return sz, se, [view,
        it('30 天淨部位', '30-day net position', wan(l['last']), kb(l['last']), 'warn' if l['last'] < 0 else 'neu', '四年來第 %d 百分位；這一段最多 %s。' % (round(l['pct_4y']), wan(r['extreme'])), 'The %s percentile over four years; this run peaked at %s.' % (ord_en(l['pct_4y']), kb(r['extreme']))),
        it('長短期供給比', 'LTH/STH supply ratio', '%.2f' % ls['ratio'], '%.2f' % ls['ratio'], 'neu', '30 天 %s：%s。' % (pc(ls['value']), '幣在流向短期持有者' if ls['value'] < 0 else '籌碼在沉澱'), '%s over 30 days: %s.' % (pc(ls['value']), 'coins are moving to short-term holders' if ls['value'] < 0 else 'supply is settling'))]

def lsrchg(L):
    s = L['onchain']['lsrchg']; t = s['trans']; neg = s['value'] < 0
    sz = ('長短期供給比 30 天 %s、連 %d 天為負：幣在流向短期持有者。' if neg else '長短期供給比 30 天 %s、連 %d 天為正：籌碼在沉澱。') % (pc(s['value']), s['days'])
    se = ('The LTH/STH supply ratio is %s over 30 days, negative for %d days: long-term holders\' coins are moving to short-term holders.' if neg else 'The LTH/STH supply ratio is %s over 30 days, positive for %d days: supply is settling.') % (pc(s['value']), s['days'])
    hist = '、'.join('%s %d%%' % (x['bottom'][:4], x['neg']) for x in t if not x.get('open')); cur = [x for x in t if x.get('open')]
    return sz, se, [
        it('熊底後一年為負', 'Negative in the year after a bottom', '%d%%' % cur[0]['neg'] if cur else '—', '%d%%' % cur[0]['neg'] if cur else '—', 'neu', '熊底後一年為負的天數：%s；這一輪還未滿一年。' % hist if cur else hist,
           'Share of days negative in the year after a bottom: %s; this cycle %d%% (under a year).' % (', '.join('%s %d%%' % (x['bottom'][:4], x['neg']) for x in t if not x.get('open')), cur[0]['neg']) if cur else '')]

def sthd(L):
    s = L['onchain']['sthd']; u, b = s['up'], s['base']; tp = s['tops'][-1]; pos = s['value'] > 0
    sz = ('短期持有者供給 90 天 %s：舊幣在換手。' if pos else '短期持有者供給 90 天 %s：幣在沉澱。') % wan(s['value']); se = ('Short-term holder supply is %s over 90 days: old coins are changing hands.' if pos else 'Short-term holder supply is %s over 90 days: coins are settling.') % kb(s['value'])
    return sz, se, [
        it('90 天變化', '90-day change', wan(s['value']), kb(s['value']), 'neu', '這一段最高 %s %s，之後回落 %s。' % (md(s['peak']['date']), wan(s['peak']['value']), wan(abs(s['off_peak']), False)), 'This run peaked at %s on %s and has eased %s since.' % (kb(s['peak']['value']), mde(s['peak']['date']), kb(abs(s['off_peak']), False))),
        it('上一輪頂部附近', 'Near the last top', wan(tp['value']), kb(tp['value']), 'neu', '每輪頂部前後的最大值；現在 %s。' % wan(s['value']), 'The largest reading around each cycle top; now %s.' % kb(s['value'])),
        it('轉正之後', 'After turning positive', '%d/%d' % (u['up'], u['n']), '%d/%d' % (u['up'], u['n']), 'neu', '90 天後上漲的次數，中位數 %s（任一天 %d%%、%s）；翻正翻負不是買賣訊號。' % (pc(u['med']), b['up'], pc(b['med'])), 'Rises 90 days later, median %s (any day: %d%%, %s); flips are not trade signals.' % (pc(u['med']), b['up'], pc(b['med'])))]

def dorm(L):
    d = L['onchain']['dorm']; t, bt = d['tops'][-1], d['bottoms'][-2]
    lv = '在近 4 年的平常範圍' if 20 <= d['a30_pct4'] <= 80 else '偏高，老幣在動' if d['a30_pct4'] > 80 else '偏低，賣出的多是新幣'
    lve = 'within its normal four-year range' if 20 <= d['a30_pct4'] <= 80 else 'high: old coins are moving' if d['a30_pct4'] > 80 else 'low: mostly young coins are being sold'
    return '賣出的幣平均放了 %.1f 天（30 天平均），%s。' % (d['dorm30'], lv), 'Coins spent had sat %.1f days on average (30-day average), %s.' % (d['dorm30'], lve), [
        it('30 天平均', '30-day average', '%.1f 天' % d['dorm30'], '%.1f days' % d['dorm30'], 'neu', '近 4 年第 %d 百分位；%s 頂部附近 %.1f 天、%s 底部附近 %.1f 天。' % (round(d['a30_pct4']), t['date'][:4], t['value'], bt['date'][:4], bt['value']), 'The %s percentile over four years; %.1f days near the %s top and %.1f near the %s bottom.' % (ord_en(d['a30_pct4']), t['value'], t['date'][:4], bt['value'], bt['date'][:4])),
        it('Liveliness 90 天', 'Liveliness, 90 days', sg(d['live90'], 2) + '‰', sg(d['live90'], 2) + '‰', 'neu', '花掉的持有時間比新累積的%s；看方向不看絕對值。' % ('多' if d['live90'] > 0 else '少'), 'Holding time spent is %s than time added; read the direction, not the level.' % ('greater' if d['live90'] > 0 else 'less'))]

def svd(L):
    s = L['deriv']['svd']
    return '近 7 天主動%s比主動%s多 %s 顆，最近 %d 天賣方主導。' % ('買' if s['sum7'] >= 0 else '賣', '賣' if s['sum7'] >= 0 else '買', n0(abs(s['sum7'])), s['neg_run']) if s['neg_run'] else '近 7 天主動買賣差 %s 顆。' % sn0(s['sum7']), \
           'Over 7 days taker %s exceeded taker %s by %s BTC; sellers have led for %d days.' % ('buys' if s['sum7'] >= 0 else 'sells', 'sells' if s['sum7'] >= 0 else 'buys', n0(abs(s['sum7'])), s['neg_run']) if s['neg_run'] else 'Taker buys minus sells over 7 days: %s BTC.' % sn0(s['sum7']), [
        it('最近一天', 'Latest day', sn0(s['delta']) + ' 顆', sn0(s['delta']) + ' BTC', 'neu', '7 天裡 %d 天賣方主導。' % s['neg7'], 'Sellers led on %d of the 7 days.' % s['neg7']),
        it('近 24 小時', 'Last 24 hours', sn0(s['h24']) + ' 顆', sn0(s['h24']) + ' BTC', 'neu', 'OKX 單一交易所，只作讀值。', 'One exchange (OKX); a reading only.')]

def tk(L):
    t = L['deriv']['taker']; sp, pp, cb = t['spot'], t['perp'], t['cb']
    sb = sp['d30'] > sp['med']; pb = pp['d30'] > pp['med']; cbw = cb['pct'] <= 10
    sz = '30 天現貨比常態多%s、永續比常態多%s%s。' % ('買' if sb else '賣', '買' if pb else '賣', '；Coinbase 現貨賣得比平常重很多' if cbw else '')
    se = 'Over 30 days spot is %s than normal and perps are %s than normal%s.' % ('buying more' if sb else 'selling more', 'buying more' if pb else 'selling more', '; Coinbase spot is selling far more than usual' if cbw else '')
    return sz, se, [
        it('現貨 30 天', 'Spot, 30 days', wan(sp['d30']), kb(sp['d30']), 'neu', '常態 %s，%s 以來第 %d 百分位。' % (wan(sp['med']), ym(t['from_']), sp['pct']), 'Normal is %s; the %s percentile since %s.' % (kb(sp['med']), ord_en(sp['pct']), yme(t['from_']))),
        it('永續 30 天', 'Perps, 30 days', wan(pp['d30']), kb(pp['d30']), 'neu', '常態 %s，第 %d 百分位；永續長期就是賣多，要和常態比。' % (wan(pp['med']), pp['pct']), 'Normal is %s, the %s percentile; perps always lean to selling, so compare with normal.' % (kb(pp['med']), ord_en(pp['pct']))),
        it('Coinbase 現貨', 'Coinbase spot', wan(cb['d30']), kb(cb['d30']), 'warn' if cbw else 'neu', '常態 %s，第 %d 百分位；美國現貨的代表。' % (wan(cb['med']), cb['pct']), 'Normal is %s, the %s percentile; the US spot proxy.' % (kb(cb['med']), ord_en(cb['pct'])))]

def stk(L):
    b = L['flows']['btc_vs_stocks']; r = b['rel']['rows'][-1]; nm = [('S&P 500', 'the S&P 500'), ('那斯達克', 'the Nasdaq'), ('黃金', 'gold')]
    lag = [nm[i] for i in range(3) if r[1] < r[2 + i]]
    jz = lambda a: '、'.join(a[:-1]) + '和' + a[-1] if len(a) > 1 else a[0]; je = lambda a: ', '.join(a[:-1]) + ' and ' + a[-1] if len(a) > 1 else a[0]
    sz = '近兩個月 BTC %s，%s。' % (pc(r[1]), ('落後 ' + jz([n[0] for n in lag])) if lag else '贏過美股和黃金')
    se = 'Over two months BTC is %s, %s.' % (pc(r[1]), ('behind ' + je([n[1] for n in lag])) if lag else 'ahead of stocks and gold')
    return sz, se, [
        it('近兩個月', 'Two months', pc(r[1]), pc(r[1]), 'neu', '自 %s：S&P 500 %s、那斯達克 %s、黃金 %s。' % (ymd(b['rel']['start']), pc(r[2]), pc(r[3]), pc(r[4])), 'Since %s: S&P 500 %s, Nasdaq %s, gold %s.' % (ymde(b['rel']['start']), pc(r[2]), pc(r[3]), pc(r[4]))),
        it('90 日勝率', '90-day win rate', '%.0f%%' % b['win90'], '%.0f%%' % b['win90'], 'neu', '近 90 個美股交易日 BTC 漲幅大於 S&P 500 的比例；上次高於 50%% 是 %s。' % md(b['last_above50']), 'Share of the last 90 US sessions where BTC beat the S&P 500; last above 50%% on %s.' % mde(b['last_above50']))]

def macro(L):
    f = L['flows']['fred']; nq, dx = f['NASDAQCOM']['corr30'], f['DTWEXBGS']['corr30']; ri = L['flows']['dfii10']
    hi = nq >= .5
    return ('BTC 和那斯達克高度同步（30 天相關 %.2f）；美元不是現在的主要驅動。' % nq if hi and abs(dx) < .3 else 'BTC 和那斯達克 30 天相關 %.2f、和美元 %.2f。' % (nq, dx)), \
           ('BTC moves closely with the Nasdaq (30-day correlation %.2f); the dollar is not the main driver now.' % nq if hi and abs(dx) < .3 else 'BTC\'s 30-day correlation is %.2f with the Nasdaq and %.2f with the dollar.' % (nq, dx)), [
        it('BTC–那斯達克', 'BTC–Nasdaq', '%.2f' % nq, '%.2f' % nq, 'warn' if hi else 'neu', '美股大跌時 BTC 很難獨善其身。' if hi else '關係不強。', 'When US tech sells off, BTC rarely escapes.' if hi else 'A weak link.'),
        it('BTC–美元', 'BTC–dollar', sg(dx, 2), sg(dx, 2), 'neu', '關係不明顯。' if abs(dx) < .3 else ('美元走強時 BTC 偏弱。' if dx < 0 else '和美元同向。'), 'No clear link.' if abs(dx) < .3 else ('BTC tends to weaken as the dollar strengthens.' if dx < 0 else 'Moves with the dollar.')),
        it('10 年期實質利率', '10-year real yield', '%.2f%%' % ri['value'], '%.2f%%' % ri['value'], 'neu', ('2%% 以上偏緊，持有不生息資產的機會成本高；近 20 天 %s 個基點。' if ri['value'] >= 2 else '近 20 天 %s 個基點。') % sg(ri['chg_20obs_bp'], 0), ('Above 2%% is tight: holding a non-yielding asset costs more; %s bp over 20 days.' if ri['value'] >= 2 else '%s bp over 20 days.') % sg(ri['chg_20obs_bp'], 0))]

CARDS = {'etf': etf, 'cot': cot, 'pr-us': pr_us, 'pr-asia': pr_asia, 'pr-perp': pr_perp, 'kp': kp, 'exflow': exflow, 'exch': exch, 'ad': ad, 'dmd': dmd, 'capflow': capflow, 'grad': grad, 'rcliq': rcliq, 'stab': stab,
         'whale': whale, 'whalet': whalet, 'lthnet': lthnet, 'lsrchg': lsrchg, 'sthd': sthd, 'dorm': dorm, 'svd': svd, 'tk': tk, 'stk': stk, 'macro': macro}
