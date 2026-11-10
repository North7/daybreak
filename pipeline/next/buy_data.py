# -*- coding: utf-8 -*-
"""「買盤：誰在買、錢從哪裡來」這一頁的資料：六組。site_data.py 會 import。
顏色照現有網站 assets/app.js 每張圖自己的 draw 函式：s1→c3、s2→ac、s3→c4、s4／warn→c5、up→up、down→dn、ink-2→ink、ink-3→k2。
每張圖旁邊的註解寫的是顏色取自哪一個函式。缺資料的圖改放「沒有資料」的卡片，不整張拿掉。
為了控制頁面大小，很長的歷史在三年以前的部分抽稀（見 thin），近三年每一筆都留。"""
import datetime as dt

EP = dt.date(1970, 1, 1)


def build(L, N, E, dn, X):
    f = L.get('flows') or {}; o = L.get('onchain') or {}; dv = L.get('deriv') or {}; cy = L.get('cycle') or {}
    ser = lambda c, **k: dict(c=c, **k)
    row = lambda zh, en, v, **k: dict(zh=zh, en=en, v=v, **k)
    R = lambda v, d=2: None if v is None else round(v, d)
    day = lambda n: EP + dt.timedelta(int(n))
    ymd = lambda s: s.replace('-', '/')                               # '2026-11-08' → '2026/11/08'
    ym = lambda n: day(n).strftime('%Y/%m')                           # 日數 → '2026/11'
    md = lambda s: '%d/%d' % (int(s[5:7]), int(s[8:10]))              # '2026-11-08' → '11/8'
    mi = lambda s: s.replace('-', '−')
    pc = lambda v, d=0: mi('%+.*f%%' % (d, v))                        # +12%、−3%
    sn = lambda v: ('+' if v > 0 else '−' if v < 0 else '') + format(abs(int(round(v))), ',')   # +26,522
    usdm = lambda v: ('+' if v >= 0 else '−') + '$' + (('%.2fB' % (abs(v) / 1000)) if abs(v) >= 1000 else ('%.0fM' % abs(v)))
    NA = lambda k, zh, en, sz, se: dict(k=k, zh=zh, en=en, na=dict(zh='今天沒有資料：%s沒有取得。' % sz, en='No data today: %s is missing.' % se))
    has = lambda x, key='rows', n=2: bool(x) and isinstance(x.get(key), list) and len(x[key]) >= n

    def thin(rows, col, step=3, keep=1100):   # 控制頁面大小：近 3 年（預設範圍）每一筆都留；更早的每 step 筆留一筆，留 col 那一欄絕對值最大的，極值不會被抽掉
        cut = rows[-1][0] - keep; old = [r for r in rows if r[0] < cut]
        return [max(old[i:i + step], key=lambda r: abs(r[col] or 0)) for i in range(0, len(old), step)] + [r for r in rows if r[0] >= cut]

    def ma7(vals):   # 7 日平均（前 6 筆為 None），照現有網站 ma7r
        return [None if i < 6 else sum(vals[i - 6:i + 1]) / 7 for i in range(len(vals))]

    def runmarks(rows, i, min_run, min_abs, lab):   # 照現有網站 oxRunMarks：每段同號期間（至少 min_run 天）標出最大值；最後一段不標
        out = []; st = 0; n = len(rows)
        for j in range(1, n + 1):
            if j < n and (rows[j][i] >= 0) == (rows[st][i] >= 0): continue
            if j < n and rows[j - 1][0] - rows[st][0] >= min_run:
                ex = max(rows[st:j], key=lambda r: abs(r[i]))
                if abs(ex[i]) >= min_abs: out.append(dict(d=ex[0], v=ex[i], col='up' if ex[i] >= 0 else 'dn', up=1 if ex[i] >= 0 else 0, zh=lab(ex), en=lab(ex)))
            st = j
        return out

    # ════ 1. 機構 ════
    def c_etf():   # 顏色：V.flows.after 裡 #c-etf 的 barChart（正綠、負紅；暫定或部分回報的那天淡掉→灰；最近連續同方向的一段和之前最大的一天用全色）
        e = f.get('etf')
        if not e: return NA('etf', '現貨 ETF 每日淨流量', 'Spot ETF daily net flow', 'ETF 每日淨流量（flows.etf）', 'the daily ETF flow feed (flows.etf)')
        rows = []; run = 0; prev = None
        for r in e:
            up = r['musd'] >= 0; run = r['musd'] + (run if prev == up else 0); prev = up
            rows.append([dn(r['d']), r['musd'], 1 if r.get('partial') else 0, round(run, 1), 0])
        n = len(e); k = n - 1; sg = e[-1]['musd'] >= 0
        while k > 0 and (e[k - 1]['musd'] >= 0) == sg: k -= 1
        days = n - k; part = any(r.get('partial') for r in e[k:]); col = 'up' if sg else 'dn'
        ex = max(range(k), key=lambda i: abs(e[i]['musd'])) if k > 0 else None
        for i_, r_ in enumerate(rows): r_[4] = .45 if r_[2] else 0 if (i_ >= k or i_ == ex) else .3
        runv = sum(r['musd'] for r in e[k:]); tipv = (min if not sg else max)(r['musd'] for r in e[k:])
        hz = ('連續 %d 個交易日淨%s的合計' % (days, '流入' if sg else '流出')) if days > 1 else '最新一個交易日的淨流量'
        he = ('Net %s for %d sessions running, total' % ('inflow' if sg else 'outflow', days)) if days > 1 else 'Latest session, net flow'
        if part: hz += '（最新一天是暫定值）'; he += ' (latest day provisional)'
        return dict(k='etf', zh='現貨 ETF 每日淨流量', en='Spot ETF daily net flow', hz=hz, he=he, f='usdM', rows=rows, hero=1,
          ser=[ser(1, zh='每日淨流量', en='Daily net flow', t='bar', dim=4), ser(3, hide=1, t='bar', f='usdM')], refs=[dict(v=0, col='k2', solid=1)],
          marks=([dict(d=rows[ex][0], v=e[ex]['musd'], col='up' if e[ex]['musd'] >= 0 else 'dn', up=1 if e[ex]['musd'] >= 0 else 0, zh=md(e[ex]['d']) + ' ' + usdm(e[ex]['musd']) + ('，這段期間最大的單日流入' if e[ex]['musd'] >= 0 else '，這段期間最大的單日流出'), en=md(e[ex]['d']) + ' ' + usdm(e[ex]['musd']) + (', largest daily inflow in the window' if e[ex]['musd'] >= 0 else ', largest daily outflow in the window'))] if ex is not None else []) +
                ([dict(d=rows[-1][0], v=tipv, col=col, up=1 if sg else 0, zh='近 %d 天連續%s %s%s' % (days, '流入' if sg else '流出', usdm(runv), '（含暫定）' if part else ''), en='%d days of %s, %s%s' % (days, 'inflow' if sg else 'outflow', usdm(runv), ' (incl. provisional)' if part else ''))] if days > 1 else []),
          leg=[[col, '全色：最近連續同方向的一段，和之前最大的單日；其餘的日子調淡，暫定值也較淡', 'Full colour: the latest same-direction run and the largest earlier day; other days are dimmed, as is a provisional value', 'box']],
          dz='美國現貨 ETF 每個交易日淨流入或流出的金額（百萬美元）。全色的柱子是最近這段連續同方向的日子，和在這之前金額最大的一天，兩處都有文字標出金額；其餘的日子調淡。最新一天如果是暫定值，顏色也會比較淡。',
          de='Net money into or out of US spot ETFs each trading day ($M). Full-colour bars are the latest run of same-direction days and the largest day before it, both labelled with their amounts; other days are dimmed. A provisional latest day is drawn lighter too.')

    def c_cot():   # 顏色：drawCot（槓桿基金 s1→c3、資產管理機構 s3→c4）
        x = f.get('cot')
        if not has(x): return NA('cot', 'CME 機構持倉', 'CME institutional positioning', 'CFTC 每週持倉報告（flows.cot）', 'the weekly CFTC positioning report (flows.cot)')
        return dict(k='cot', zh='CME 機構持倉', en='CME institutional positioning', hz='槓桿基金淨部位（%s 的持倉）' % md(x['date']), he='Leveraged funds, net (positions as of %s)' % x['date'], f='btc0',
          rows=thin([r for r in x['rows'] if r[1]], 2, 2), p=1,
          ser=[ser(2, zh='槓桿基金淨部位', en='Leveraged funds, net', col='c3', w=1.5), ser(3, zh='資產管理機構淨部位', en='Asset managers, net', col='c4', w=1.5)], refs=[dict(v=0, col='k2', solid=1)],
          dz='CME 比特幣期貨每週的淨部位（多單減空單，換算成顆）。槓桿基金的空單多半是買現貨或 ETF、放空期貨的套利，淨空變大不等於看空；資產管理機構較少做套利，淨多比較接近真的看多。持倉是週二的、週五才公布。',
          de='Weekly net positions in CME bitcoin futures (longs minus shorts, in BTC). Much of the leveraged-fund short is arbitrage (long spot or ETFs, short futures), so a bigger net short is not a bearish bet; asset managers do less arbitrage, so their net long is closer to a real bullish position. Positions are as of Tuesday and published on Friday.')

    # ════ 2. 各地買盤 ════
    p3 = f.get('premium3') or {}

    def c_prus():   # 顏色：drawCbPrem（每日柱 ≥0 綠、<0 紅；7 日平均 s4→c5；深度折價線和它下面的底色 down→dn；歷次跌破的圓圈 down→dn）
        x = f.get('cb_premium'); rs = [r for r in (x or {}).get('rows') or [] if r[2] is not None]
        if len(rs) < 60: return NA('pr-us', '美國現貨：Coinbase 溢價', 'US spot: Coinbase premium', 'Coinbase 對 Binance 的每日價差（flows.cb_premium）', 'the daily Coinbase vs Binance spread (flows.cb_premium)')
        DEEP, REARM = -0.15, -0.05; a7 = ma7([r[1] for r in rs])
        def at(i, n):
            t = rs[i][0] + n
            for k in range(i, len(rs)):
                if rs[k][0] >= t: return (rs[k][2] / rs[i][2] - 1) * 100
            return None
        ev = []; armed = True   # 照現有網站 cbStats：7 日平均跌破 −0.15% 記一次，回到 −0.05% 以上才重新計
        for i, a in enumerate(a7):
            if a is None: continue
            if armed and a < DEEP: ev.append((i, a, at(i, 30))); armed = False
            elif not armed and a > REARM: armed = True
        vs_ = sorted(r[1] for r in rs if r[1] is not None); qv = lambda p_: vs_[int((len(vs_) - 1) * p_)]; ylo = min(-0.3, qv(.005) * 1.1); yhi = max(.2, qv(.995) * 1.1)
        return dict(k='pr-us', zh='美國現貨：Coinbase 溢價', en='US spot: Coinbase premium', hz='7 日平均', he='7-day average', f='p3', rows=[[r[0], r[1], r[2], R(a7[i], 4), None if r[1] is None else max(ylo, min(yhi, r[1]))] for i, r in enumerate(rs)], p=2, hero=1, dom=[R(ylo, 3), R(yhi, 3)],
          ser=[ser(4, vc=1, zh='每日', en='Daily', t='bar', op=.42), ser(3, zh='7 日平均', en='7-day average', col='c5', w=1.8)],
          refs=[dict(v=0, col='k2', solid=1), dict(v=DEEP, col='dn', zh='深度折價線 −0.15%', en='Deep-discount line −0.15%')],
          zones=[dict(lo=None, hi=DEEP, col='dn', zh='7 日平均在深度折價區', en='7-day average in the deep-discount zone', nz='深度折價線', ne='the deep-discount line')],
          marks=[dict(d=rs[i][0], v=R(a, 4), col='dn', up=0, zh=None if r30 is None else '30 天 ' + pc(r30), en=None if r30 is None else '30d ' + pc(r30)) for i, a, r30 in ev],
          leg=[['dn', '7 日平均跌破 −0.15% 的那一天，和之後 30 天的漲跌', 'Days the 7-day average broke −0.15%, with the 30-day change after', 'ring']],
          dz='Coinbase 的美元價格除以 Binance 的 USDT 價格再減 1，大於 0 代表美國買方比海外積極。柱子是每天的值，沙金色的線是 7 日平均。7 日平均跌破 −0.15% 算深度折價，圓圈是歷次跌破的那一天，旁邊是之後 30 天的漲跌。',
          de='Coinbase\'s USD price divided by Binance\'s USDT price, minus 1; above 0 means US buyers are keener than offshore. Bars are daily values and the sand line is the 7-day average. A 7-day average below −0.15% counts as a deep discount; circles mark each break, labelled with the price change 30 days later.')

    def c_prasia():   # 顏色：drawPrem 的 one('c-pr-asia', …, 'var(--s4)')→c5、零軸 ink-3→k2；±0.3% 的持平帶取自 premSay 的門檻，現有網站圖上沒畫，區帶顏色依意義選
        h = [r for r in p3.get('usdt_hist') or [] if r[1] is not None]; u = p3.get('usdt') or {}
        if len(h) < 2: return NA('pr-asia', '亞洲：場外 USDT 溢價', 'Asia: OTC USDT premium', 'OKX 場外 USDT 報價的每日快照（flows.premium3.usdt_hist，至少要兩天）', 'the daily OKX OTC USDT snapshot (flows.premium3.usdt_hist; it needs at least two days)')
        d0 = day(h[0][0])
        return dict(k='pr-asia', zh='亞洲：場外 USDT 溢價', en='Asia: OTC USDT premium', hz='最新一次快照' + ('（USDT 約 %.3f 人民幣、匯率 %.3f）' % (u['mid'], u['fx']) if u.get('mid') and u.get('fx') else ''),
          he='Latest snapshot' + (' (USDT about %.3f CNY vs a %.3f FX rate)' % (u['mid'], u['fx']) if u.get('mid') and u.get('fx') else ''), f='ps2', rows=h,
          ser=[ser(1, zh='場外 USDT 溢價', en='OTC USDT premium', col='c5', w=1.8)],
          refs=[dict(v=0, col='k2', solid=1), dict(v=.3, col='k2', zh='持平帶 ±0.3%', en='Flat band ±0.3%'), dict(v=-.3, col='k2')],
          zones=[dict(lo=-.3, hi=.3, col='k2', zh='接近匯率，亞洲買賣大致平衡', en='Near the FX rate: Asian flows roughly balanced', nz='持平帶', ne='the flat band'),
                 dict(lo=.3, hi=None, col='up', zh='溢價：有人搶著換 USDT 進場', en='Premium: buyers are rushing into USDT'),
                 dict(lo=None, hi=-.3, col='dn', zh='折價：換回人民幣的人比較多', en='Discount: more people are cashing out to yuan')],
          dz='OKX 場外用人民幣買賣 USDT 的中間價，除以美元兌人民幣匯率再減 1。高於 +0.3%% 是有人搶著換 USDT 進場，低於 −0.3%% 是換回人民幣的人比較多，中間算持平。這條只有每天一次的快照，紀錄從 %s 開始累積，目前 %d 天。' % (d0.strftime('%Y/%m/%d'), len(h)),
          de='The mid price of USDT against the yuan on OKX\'s OTC desk, divided by the USD/CNY rate, minus 1. Above +0.3%% means buyers are rushing into USDT; below −0.3%% means more people are cashing out to yuan; in between is flat. One snapshot a day, recorded since %s (%d days so far).' % (d0.isoformat(), len(h)))

    def c_prperp():   # 顏色：drawPrem 的 one('c-pr-perp', ma7(…), 'var(--s4)')→c5、零軸 ink-3→k2；「比平常貴／便宜」取自 premSay（自己歷史的第 70／30 百分位），現有網站圖上沒畫，區帶顏色依意義選
        x = p3.get('perp') or {}; rs = [r for r in x.get('rows') or [] if r[1] is not None]
        if len(rs) < 30: return NA('pr-perp', '槓桿：永續對現貨', 'Leverage: perpetual vs spot', 'OKX 永續對現貨的每日價差（flows.premium3.perp）', 'the daily OKX perpetual vs spot spread (flows.premium3.perp)')
        a7 = ma7([r[1] for r in rs]); rows = [[r[0], round(a7[i], 4)] for i, r in enumerate(rs) if a7[i] is not None]
        s = sorted(r[1] for r in rows); q30 = s[int((len(s) - 1) * .3)]; q70 = s[int((len(s) - 1) * .7)]
        return dict(k='pr-perp', zh='槓桿：永續對現貨', en='Leverage: perpetual vs spot', hz='7 日平均', he='7-day average', f='p3', rows=rows,
          ser=[ser(1, zh='永續對現貨（7 日平均）', en='Perpetual vs spot (7-day average)', col='c5', w=1.8)], refs=[dict(v=0, col='k2', solid=1)],
          zones=[dict(lo=q70, hi=None, col='up', zh='比平常貴：多單願意付溢價追價', en='Richer than usual: longs are paying up to chase', nz='比平常貴的那條線', ne='the richer-than-usual line'),
                 dict(lo=None, hi=q30, col='dn', zh='比平常便宜：槓桿偏空或在避險', en='Cheaper than usual: leverage leans short or is hedging')],
          leg=[['up', '近 %d 天最高的三成' % len(rs), 'Top 30%% of the last %d days' % len(rs), 'box'], ['dn', '最低的三成', 'Bottom 30%', 'box']],
          dz='OKX 永續合約的價格除以現貨價格再減 1，取 7 日平均。永續平常就略低於現貨，所以和自己的歷史比：落在近 %d 天最高的三成是比平常貴，多單願意付溢價追價；落在最低的三成是比平常便宜，槓桿偏空或在避險。' % len(rs),
          de='The OKX perpetual price divided by spot, minus 1, as a 7-day average. Perpetuals usually sit slightly below spot, so the line is judged against its own history: in the top 30%% of the last %d days it is richer than usual (longs paying up to chase); in the bottom 30%% it is cheaper than usual (leverage leaning short or hedging).' % len(rs))

    def c_kp():   # 顏色：drawKp（每日 ink-3→k2 細線；7 日平均 溢價綠、折價紅；5% 線 warn→c5；壓縮刻度）
        x = f.get('kp')
        if not has(x): return NA('kp', '韓國溢價', 'Korea premium', 'Upbit 韓元價格和匯率（flows.kp）', 'the Upbit won price and FX feed (flows.kp)')
        return dict(k='kp', zh='韓國溢價', en='Korea premium', hz='7 日平均', he='7-day average', f='ps2', rows=thin(x['rows'], 3), p=1, tf='slog', hero=1,
          ser=[ser(2, zh='每日', en='Daily', col='k2', w=1, op=.45), ser(3, zh='7 日平均', en='7-day average', t='sign', base=0, w=1.8)],
          refs=[dict(v=5, col='c5', zh='5%：偏熱', en='5%: running hot')], zones=[dict(lo=5, hi=None, col='c5', zh='高於 5%：韓國散戶在追價', en='Above 5%: Korean retail is chasing', nz='5% 偏熱線', ne='the 5% line')],
          leg=[['up', '7 日平均：溢價', '7-day average: premium', 'line'], ['dn', '7 日平均：折價', '7-day average: discount', 'line']],
          dz='Upbit 的韓元價格換成美元後，比美元價格貴多少。灰線是每天的值，粗線是 7 日平均；7 日平均到 5% 以上代表韓國散戶在追價。縱軸是壓縮過的刻度，因為 2018 年初曾經到 50%。',
          de='How much more Upbit\'s won price costs than the dollar price once converted. The grey line is the daily value and the thick line the 7-day average; a 7-day average above 5% means Korean retail is chasing. The vertical scale is compressed because the premium reached 50% in early 2018.')

    def c_exflow():   # 顏色：drawExf（30 天合計 split:[down, up]＝正值流入紅、負值流出綠；強流出期間底色 up、強流入期間底色 down）
        x = f.get('exflow')
        if not has(x): return NA('exflow', '交易所淨流量', 'Exchange netflow', '交易所流入和流出（flows.exflow）', 'the exchange inflow and outflow feed (flows.exflow)')
        t0 = x['rows'][0][0]; vb = lambda eps, col: [dict(a=dn(e['start']), b=dn(e['end']) + 2, col=col, op=.14) for e in eps or [] if dn(e['end']) >= t0]
        return dict(k='exflow', zh='交易所淨流量', en='Exchange netflow', hz='30 天合計', he='30-day sum', f='btc', rows=thin(x['rows'], 3), p=1,
          ser=[ser(3, zh='30 天合計', en='30-day sum', t='sign', base=0, hi='dn', lo='up', w=1.6)], spans=vb(x.get('out_eps'), 'up') + vb(x.get('in_eps'), 'dn'),
          leg=[['up', '淨流出：幣在離開交易所', 'Net outflow: coins leaving exchanges', 'line'], ['dn', '淨流入：幣在流向交易所', 'Net inflow: coins arriving at exchanges', 'line'],
               ['up', '強流出（近 4 年最低 10%）', 'Strong outflow (4-year bottom 10%)', 'box'], ['dn', '強流入（近 4 年最高 10%）', 'Strong inflow (4-year top 10%)', 'box']],
          dz='流入交易所的幣減掉流出的幣，30 天合計。負值（綠）是幣在離開交易所，正值（橘紅）是幣在流向交易所。底色是 30 天合計落在近 4 年最低一成（強流出）或最高一成（強流入）的期間。',
          de='Coins flowing into exchanges minus coins flowing out, summed over 30 days. Negative (green) means coins are leaving exchanges; positive (orange-red) means coins are arriving. Shading marks periods when the 30-day sum was in the lowest tenth (strong outflow) or highest tenth (strong inflow) of the past four years.')

    def c_exch():   # 現有網站只有讀數（ocInterp：減少偏多→綠、增加是潛在賣壓→紅），沒有走勢圖，所以是清單卡
        x = o.get('exchange') or {}
        if x.get('exchange_supply_share_pct') is None: return NA('exch', '交易所供給', 'Exchange supply', '交易所持幣量（onchain.exchange）', 'the exchange holdings reading (onchain.exchange)')
        def chg(zh, en, key):
            v = x.get(key)
            if v is None: return row(zh, en, '—', ve='—')
            return row(zh, en, v, f='ps2', col='up' if v < 0 else 'dn' if v > 0 else 'k2', nz='幣在離開交易所，可賣的現貨變少' if v < 0 else '幣在流入交易所，潛在賣壓增加', ne='Coins are leaving exchanges: less spot for sale' if v < 0 else 'Coins are arriving at exchanges: more potential selling')
        b = x.get('exchange_supply_btc'); dt_ = x.get('exchange_supply_date') or ''
        return dict(k='exch', zh='交易所供給', en='Exchange supply', hz='交易所持有的幣佔流通量', he='Share of supply held on exchanges', hs=dict(v=x['exchange_supply_share_pct'], f='p2'),
          list=dict(rows=([row('交易所持有的幣', 'Coins held on exchanges', '%.1f 萬顆' % (b / 1e4), ve='%.2fM BTC' % (b / 1e6), nz='資料日 ' + ymd(dt_), ne='As of ' + dt_)] if b else []) +
                    [row('佔流通量', 'Share of supply', x['exchange_supply_share_pct'], f='p2', bar=x['exchange_supply_share_pct'], col='c4'),
                     chg('7 天變化', '7-day change', 'exchange_supply_chg7_pct'), chg('30 天變化', '30-day change', 'exchange_supply_chg30_pct'), chg('90 天變化', '90-day change', 'exchange_supply_chg90_pct')]),
          dz='交易所地址持有的幣。減少代表幣離開交易所、可賣的現貨變少；增加代表幣流入交易所、潛在賣壓增加。地址歸屬會事後修正，看方向不看小數；現有網站沒有這一項的歷史走勢，這裡只放讀數。',
          de='Coins held at exchange addresses. A fall means coins are leaving and less spot is for sale; a rise means coins are arriving and potential selling grows. Address attribution is revised later, so read the direction, not the decimals; the live site has no history for this, so the card shows readings only.')

    # ════ 3. 鏈上需求 ════
    def c_ad():   # 顏色：drawAd（30 天柱 ≥0 綠、<0 紅；它的 30 日平均 ink-2→ink 虛線；1 年版 s3→c4，乘 30/365 放在同一個刻度；疑似搬家 warn→c5）
        x = o.get('ad')
        if not has(x): return NA('ad', '表觀需求（30 天與 1 年）', 'Apparent demand (30 days and 1 year)', '表觀需求（onchain.ad）', 'the apparent demand series (onchain.ad)')
        rows = [[r[0], r[1], r[2], r[3], None if len(r) < 5 or r[4] is None else round(r[4] * 30 / 365)] for r in x['rows']]; y1 = any(r[4] is not None for r in rows[-5:])
        return dict(k='ad', zh='表觀需求（30 天與 1 年）', en='Apparent demand (30 days and 1 year)', hz='30 天合計', he='30-day sum', f='btc', rows=thin(rows, 1), p=3,
          ser=[ser(1, zh='表觀需求（30 天）', en='Apparent demand (30 days)', t='bar'), ser(2, zh='它的 30 日平均', en='Its 30-day average', col='ink', dash='4 3', w=1.3)] + ([ser(4, zh='1 年版（換算成每 30 天）', en='1-year version (per 30 days)', col='c4', w=1.6)] if y1 else []),
          vl=[dict(d=dn(m['start']), col='c5', dash='2 4', only='v', op=.95) for m in x.get('moves') or []], leg=[['c5', '疑似搬家（交易所或託管整理錢包）', 'Likely wallet reshuffle (exchange or custodian)', 'dash']],
          dz='30 天新挖出的幣，減掉「一年以上沒動過的供給」30 天的變化：舊幣醒來被市場接走時是正的，滿一年沒動的幣增加得比新挖出的快時是負的。虛線是它的 30 日平均，青線是同樣算法的 365 天合計，換算成每 30 天。沙金色的直條是疑似交易所或託管整理錢包的日子，不是真的需求。',
          de='Coins mined in 30 days minus the 30-day change in supply unmoved for a year or more: positive when old coins wake up and are absorbed, negative when coins reaching one year unmoved outpace new issuance. The dashed line is its 30-day average; the cyan line is the same sum over 365 days, scaled to a 30-day rate. Sand bars mark days that look like exchange or custodian wallet reshuffles, not real demand.')

    def c_dmd():   # 顏色：drawDmd（現貨 s3→c4 粗線、永續 s2→ac；現貨轉正的標記 s3→c4）
        x = o.get('dmd')
        if not has(x): return NA('dmd', '現貨需求和永續需求', 'Spot vs perpetual demand', '現貨與永續需求（onchain.dmd）', 'the spot and perpetual demand series (onchain.dmd)')
        return dict(k='dmd', zh='現貨需求和永續需求', en='Spot vs perpetual demand', hz='現貨需求 30 天合計', he='Spot demand, 30-day sum', f='s2', rng=365, rows=x['rows'], p=1, hero=2,
          ser=[ser(2, zh='現貨（表觀需求 30 天）', en='Spot (30-day apparent demand)', col='c4', w=1.9), ser(3, zh='永續（OKX 30 天主動買 − 賣）', en='Perpetuals (OKX 30-day taker buy − sell)', col='ac', w=1.5), ser(4, hide=1, t='sign', f='btc')],
          refs=[dict(v=0, col='k2', solid=1)],
          marks=[dict(d=dn(m['date']), v=0, col='c4', up=1, zh='轉正' if m.get('r60') is None else '60 天 ' + pc(m['r60']), en='turns +' if m.get('r60') is None else '60d ' + pc(m['r60'])) for m in x.get('flips') or []],
          leg=[['c4', '現貨需求由負轉正，旁邊是之後 60 天的漲跌', 'Spot demand turns positive, with the 60-day change after', 'ring']],
          dz='現貨是表觀需求的 30 天合計（顆），永續是 OKX 合約 30 天主動買減主動賣（美元）。兩條單位不同，各自除以近一年絕對值的最大值，只比方向和相對強弱。圓圈是現貨需求由負轉正的日子，旁邊是之後 60 天的漲跌。',
          de='Spot is 30-day apparent demand (BTC); perpetuals are OKX contracts\' 30-day taker buys minus taker sells (USD). The units differ, so each is divided by its own largest absolute value of the past year, to compare direction and relative strength only. Circles mark days when spot demand turned from negative to positive, labelled with the price change 60 days later.')

    def c_capflow():   # 顏色：drawCapflow（CF_M1＝s2→ac 一個月內換手、CF_Y12＝s1→c3 一到兩年沒動；週期頂部底色 warn→c5、熊市底部底色 s3→c4；峰值標記用各自的線色）
        x = o.get('capflow')
        if not has(x): return NA('capflow', '循環資金流：投機和長線', 'Cycle capital flows: speculation vs conviction', '各持有時間的實現市值佔比（onchain.capflow）', 'realized cap by holding time (onchain.capflow)')
        pk = lambda p, col: dict(d=dn(p[0]), v=p[1], col=col, up=1, zh='%s %.0f%%' % (p[0][:4], p[1]), en='%s %.0f%%' % (p[0][:4], p[1]))
        band = lambda d, col: dict(a=dn(d) - 45, b=dn(d) + 45, col=col, op=.13, zh='頂' if col == 'c5' else '底', en='Top' if col == 'c5' else 'Low')
        return dict(k='capflow', zh='循環資金流：投機和長線', en='Cycle capital flows: speculation vs conviction', hz='一到兩年沒動的幣，佔全體實現市值', he='Coins unmoved for 1–2 years, share of realized cap', f='p1', rng=0, rows=thin(x['rows'], 2), p=1, dom=[0, 70],
          ser=[ser(3, zh='1–2 年沒動（長線）', en='Unmoved 1–2 years (conviction)', col='c3', fill=1, w=2), ser(2, zh='1 個月內換手（投機）', en='Moved within a month (speculation)', col='ac', fill=1, w=2)],
          spans=[band(t[0], 'c5') for t in cy.get('tops') or []] + [band(b[0], 'c4') for b in cy.get('bottoms') or []],
          marks=[pk(p, 'ac') for p in x.get('peaks_m1') or [] if p[1] >= 30] + [pk(p, 'c3') for p in x.get('peaks_y12') or [] if p[0] != x.get('date') and p[1] >= 40],
          leg=[['c5', '週期頂部前後 45 天', '45 days either side of a cycle top', 'box'], ['c4', '熊市底部前後 45 天', '45 days either side of a bear-market bottom', 'box']],
          dz='把每顆幣用買進成本計價，看各種持有時間佔多少。橘線是最近一個月換手的幣（投機、新錢），過去在週期頂部衝得很高；藍紫線是一到兩年沒動的幣（長線），在熊市底部附近最大。底色是歷次週期頂部和底部的前後 45 天。',
          de='Each coin is valued at its purchase cost, then split by holding time. The orange line is coins that changed hands in the last month (speculation, new money), which spiked at past cycle tops; the violet line is coins unmoved for one to two years (conviction), which peaks near bear-market bottoms. Shading marks 45 days either side of past cycle tops and bottoms.')

    def c_grad():   # 顏色：drawGr（30 日 s2→ac 細線、120 日 s4→c5 粗線；頂背離 warn→c5、底背離 s3→c4，虛線連兩個擺動點）；+1.5 的警示取自 grSay 的門檻
        x = o.get('grad')
        if not has(x): return NA('grad', '資金與價格增量梯度', 'Capital vs price momentum', '資金與價格梯度（onchain.grad）', 'the capital vs price gauge (onchain.grad)')
        dvs = x.get('div120') or []; KD = dict(top=('c5', '頂背離', 'Bear div'), bot=('c4', '底背離', 'Bull div'))
        return dict(k='grad', zh='資金與價格增量梯度', en='Capital vs price momentum', hz='120 日（幾個標準差）', he='120-day (standard deviations)', f='s2', rows=thin(x['rows'], 3), p=1, hero=1,
          ser=[ser(2, zh='30 日', en='30-day', col='ac', w=1, op=.55), ser(3, zh='120 日', en='120-day', col='c5', w=2, fill=1)], refs=[dict(v=0, col='k2', solid=1)],
          zones=[dict(lo=1.5, hi=None, col='c5', zh='高於 +1.5：價格跑得比資金快很多', en='Above +1.5: price far ahead of capital', nz='+1.5 警示線', ne='the +1.5 line')],
          links=[dict(a=dn(d['prev']), b=dn(d['date']), pa=d['prev_price'], pb=d['price'], va=d['za'], vb=d['zb'], col=KD[d['kind']][0], dash='5 4',
                      zh=(KD[d['kind']][1] + ' ' + md(d['date'])) if d in dvs[-3:] else None, en=(KD[d['kind']][2] + ' ' + md(d['date'])) if d in dvs[-3:] else None) for d in dvs if d.get('kind') in KD],
          leg=[['c5', '頂背離', 'Bearish divergence', 'dash'], ['c4', '底背離', 'Bullish divergence', 'dash']],
          dz='價格 N 天的漲跌，減掉實現價格（全體的平均買進成本）N 天的漲跌，再除以自己過去 4 年的標準差。正值代表價格跑得比真正進場的資金快。虛線是 120 日那條的背離：價格創新高或新低，梯度卻沒有跟上。',
          de='The N-day change in price minus the N-day change in realized price (the average cost of all coins), divided by its own 4-year standard deviation. Positive means price is running ahead of the money actually coming in. Dashed lines are divergences on the 120-day line: price makes a new high or low and the gauge does not follow.')

    def c_rcliq():   # 顏色：V.flows.after 裡 #c-rcliq 的 oxPane（30 日變化 split:[up, down]＝>0 綠、≤0 紅；≤0 的期間底色 down→dn）
        x = f.get('rc_liq')
        if not has(x): return NA('rcliq', '資金流入：實現市值 30 日變化', 'Capital inflow: realized cap, 30-day change', '實現市值（flows.rc_liq）', 'the realized cap series (flows.rc_liq)')
        rows = x['rows']; t0 = rows[0][0]; cap = x.get('realized_cap_usd_b')
        return dict(k='rcliq', zh='資金流入：實現市值 30 日變化', en='Capital inflow: realized cap, 30-day change', hz='30 日變化' + ('（實現市值 %.2f 兆美元）' % (cap / 1000) if cap else ''), he='30-day change' + (' (realized cap $%.2fT)' % (cap / 1000) if cap else ''),
          f='ps2', rng=0, rows=thin(rows, 1), ser=[ser(1, zh='30 日變化', en='30-day change', t='sign', base=0, w=1.5)],
          spans=[dict(a=max(t0, dn(e['start'])), b=dn(e['end']) + 1, col='dn', op=.08) for e in x.get('episodes') or [] if dn(e['end']) >= t0],
          marks=runmarks(rows, 1, 60, 4, lambda r: ym(r[0]) + ' ' + pc(r[1])), leg=[['dn', '小於等於 0 的期間', 'Periods at or below 0', 'box']],
          dz='實現市值是每顆幣用最後一次移動時的價格計價後的加總，可以看成全體持有者的總成本。30 日變化大於 0 代表有新資金用更高的價格接手；小於等於 0（橘紅底色）代表新資金停止流入。這只是資金背景，不是買賣訊號。',
          de='Realized cap values every coin at the price it last moved at, so it is roughly the total cost of all holders. A 30-day change above 0 means new money is paying higher prices; at or below 0 (orange-red shading) means inflows have stalled. Background only, not a trading signal.')

    def c_stab():   # 顏色：drawFlowCharts 裡 #c-stab 的 oxPane（30 天增減 split:[up, down]＝增加綠、減少紅）
        x = f.get('stables'); m = {r[0]: r[1] for r in (x or {}).get('rows') or []}; rows = []
        for d, v in sorted(m.items()):   # 照現有網站：30 天前那一筆（前後差兩天內都算）
            b = next((m[d - k] for k in (30, 31, 29, 32, 28) if m.get(d - k)), None)
            if b: rows.append([d, round((v / b - 1) * 100, 2)])
        if len(rows) < 2: return NA('stab', '穩定幣總供給', 'Total stablecoin supply', '穩定幣流通量（flows.stables）', 'the stablecoin supply series (flows.stables)')
        tot = x.get('usd_b')
        return dict(k='stab', zh='穩定幣總供給', en='Total stablecoin supply', hz='30 天增減' + ('（總量 %s 億美元）' % format(int(round(tot * 10)), ',') if tot else ''), he='30-day change' + (' (total $%.0fB)' % tot if tot else ''),
          f='ps2', rows=thin(rows, 1), ser=[ser(1, zh='30 天增減', en='30-day change', t='sign', base=0, w=1.5)], marks=runmarks(rows, 1, 60, 2, lambda r: ym(r[0]) + ' ' + pc(r[1], 1)),
          leg=[['up', '增加：場外美元變多', 'Rising: more dollars on the sidelines', 'box'], ['dn', '減少：場外美元萎縮', 'Falling: sidelined dollars shrinking', 'box']],
          dz='全部美元穩定幣流通量的 30 天增減。穩定幣是加密市場裡等著進場的美元：增加代表場外的錢變多，減少代表在萎縮。圓圈是每一段連續增加或減少期間的最大值。',
          de='The 30-day change in all US-dollar stablecoins in circulation. Stablecoins are the dollars waiting on the sidelines of crypto: a rise means more of them, a fall means they are shrinking. Circles mark the extreme of each run of growth or contraction.')

    # ════ 4. 大戶與長期持有者 ════
    wh = o.get('whales') or {}
    COH = {'lt1': ('散戶 <1 BTC', 'Shrimp <1 BTC'), '1_10': ('1–10 BTC', 'Crabs 1–10 BTC'), '10_100': ('10–100 BTC', 'Fish 10–100 BTC'), '100_1k': ('鯊魚 100–1K', 'Sharks 100–1K'), '1k_10k': ('鯨魚 1K–10K', 'Whales 1K–10K'), 'ge10k': ('≥10K', '≥10K')}

    def c_whale():   # 顏色：drawWhale（鯊魚 100–1K s4→c5、鯨魚 1K–10K s1→c3、≥10K s3→c4、零軸 ink-3→k2）
        if not has(wh): return NA('whale', '大戶 30 日淨變化', 'Big holders, 30-day net change', '依地址餘額分層的持幣量（onchain.whales）', 'holdings by address tier (onchain.whales)')
        rows = [[r[0], r[1], r[2], r[3], None if r[1] is None or r[2] is None else r[1] + r[2]] for r in wh['rows']]
        return dict(k='whale', zh='大戶 30 日淨變化', en='Big holders, 30-day net change', hz='持有 100 到 1 萬顆的地址，30 天合計', he='Addresses holding 100–10K BTC, 30-day total', f='btc', rows=rows, hero=3,
          ser=[ser(1, zh='鯊魚 100–1K', en='Sharks 100–1K', col='c5', w=1.5), ser(2, zh='鯨魚 1K–10K', en='Whales 1K–10K', col='c3', w=1.5), ser(3, zh='≥10K', en='≥10K', col='c4', w=1.4), ser(4, hide=1, t='sign', f='btc')],
          refs=[dict(v=0, col='k2', solid=1)],
          dz='依地址餘額分層，各層 30 天增減了多少顆。一個地址不等於一個人，一萬顆以上多半是交易所和託管；錢包整理也會讓幣在分層之間移動，所以看 30 天以上的方向，不看單日的跳動。',
          de='Addresses grouped by balance, showing how many BTC each tier gained or shed over 30 days. One address is not one person, and the 10K-plus tier is mostly exchanges and custodians; wallet reshuffles also move coins between tiers, so read the direction over 30 days or more, not single-day jumps.')

    def c_whalet():   # 現有網站 whalePanel 的表格：增加綠、減少紅、持平灰
        co = [c for c in wh.get('cohorts') or [] if c.get('key') in COH]
        if not co: return NA('whalet', '各層地址的持幣變化', 'Holdings by address tier', '依地址餘額分層的持幣量（onchain.whales.cohorts）', 'holdings by address tier (onchain.whales.cohorts)')
        by = {c['key']: c for c in co}; big = sum((by.get(k) or {}).get('chg30') or 0 for k in ('100_1k', '1k_10k')); leg = wh.get('leg_start') or ''
        tone = lambda v: 'up' if v > 0 else 'dn' if v < 0 else 'k2'
        def one(c):
            v = c.get('chg30') or 0
            return row(COH[c['key']][0], COH[c['key']][1], sn(v) + ' 顆', ve=sn(v) + ' BTC', col=tone(v), bar=c.get('pct30'), mk=50,
                       nz='持幣 %.0f 萬顆 · 7 天 %s · 90 天 %s · 這一段以來 %s' % (c['btc'] / 1e4, sn(c.get('chg7') or 0), sn(c.get('chg90') or 0), sn(c.get('since_leg') or 0)),
                       ne='Holds %.2fM BTC · 7d %s · 90d %s · this leg %s' % (c['btc'] / 1e6, sn(c.get('chg7') or 0), sn(c.get('chg90') or 0), sn(c.get('since_leg') or 0)))
        return dict(k='whalet', zh='各層地址的持幣變化', en='Holdings by address tier', hz='持有 100 到 1 萬顆的地址，30 天合計', he='Addresses holding 100–10K BTC, 30-day total', hs=dict(v=big, f='btc'),
          list=dict(rows=[one(c) for c in reversed(co)]),
          dz='每一層地址 30 天的淨增減，橫條是這個數字在近 4 年的百分位，直線是中間值 50。下面小字是持幣量，和 7 天、90 天、這一段行情（%s 起）以來的增減。' % ymd(leg),
          de='Each tier\'s 30-day net change; the bar is that figure\'s percentile over the past four years, with the tick at 50. The small print gives holdings and the change over 7 days, 90 days and since this leg began (%s).' % leg)

    def c_supliq():   # 顏色：drawOc 的 ocCol（OC_KIND 裡 illiquid-supply、highly-liquid-supply 都是 s3→c4）
        vz = o.get('viz') or {}; MD = [('illiquid-supply', '非流動性供給', 'Illiquid supply'), ('highly-liquid-supply', '高流動性供給', 'Highly liquid supply')]
        modes = [dict(mz=zh, me=en, rows=vz[k]['rows'], hz=zh + '（顆）', he=en + ' (BTC)', ser=[ser(1, zh=zh, en=en, col='c4', w=1.7)]) for k, zh, en in MD if has(vz.get(k))]
        if not modes: return NA('supliq', '流動性供給', 'Supply by liquidity', '非流動性和高流動性供給（onchain.viz）', 'illiquid and highly liquid supply (onchain.viz)')
        return dict(k='supliq', zh='流動性供給', en='Supply by liquidity', f='btc0', modes=modes,
          dz='依錢包的花費習慣分類。非流動性供給是長期不動的錢包持有的幣，增加代表囤幣、浮動籌碼變少；高流動性供給是常在交易的錢包持有的幣，增加代表可交易的籌碼變多。分類是估算的，會事後修正。',
          de='Coins classified by how their wallets spend. Illiquid supply sits in wallets that rarely spend; a rise means hoarding and less float. Highly liquid supply sits in wallets that trade often; a rise means more tradable float. The classification is an estimate and is revised later.')

    # ════ 5. 主動買賣 ════
    def c_svd():   # 顏色：drawSv、drawSvH（主動買多綠、主動賣多紅的柱）
        x = dv.get('svd'); rs = [r for r in (x or {}).get('rows') or [] if r[1]]
        if len(rs) < 2: return NA('svd', '現貨主動買賣差（OKX）', 'Spot taker buy − sell (OKX)', 'OKX 現貨主動買賣量（deriv.svd）', 'OKX spot taker volumes (deriv.svd)')
        roll = lambda vals, n: [None if i < n - 1 else round(sum(vals[i - n + 1:i + 1]), 1) for i in range(len(vals))]
        s7 = roll([r[2] for r in rs], 7)
        modes = [dict(mz='每日', me='Daily', hz='7 天合計', he='7-day total', rows=[[r[0], r[1], r[2], s7[i]] for i, r in enumerate(rs)], p=1, hero=1,
                      ser=[ser(2, zh='每日主動買 − 賣', en='Daily taker buy − sell', t='bar'), ser(3, hide=1, t='bar', f='btc0')])]
        hs = [h for h in x.get('hours') or [] if h[2]]
        if len(hs) >= 24:   # 橫軸是「日數」：每小時那一根放在它結束的時間，最後一小時對齊到當天日線收盤的位置
            last = hs[-1][0]; base = last // 24; s24 = roll([h[1] for h in hs], 24)
            modes.append(dict(mz='每小時', me='Hourly', hz='近 24 小時合計', he='Last 24 hours, total', rows=[[round(base - (last - h[0]) / 24.0, 4), h[2], h[1], s24[i]] for i, h in enumerate(hs)], p=1, hero=1,
                              ser=[ser(2, zh='每小時主動買 − 賣', en='Hourly taker buy − sell', t='bar'), ser(3, hide=1, t='bar', f='btc0')]))
        return dict(k='svd', zh='現貨主動買賣差（OKX）', en='Spot taker buy − sell (OKX)', f='btc0', modes=modes,
          dz='OKX 現貨用市價主動買進的量，減掉主動賣出的量（顆）。下跌時主動賣出慢慢收斂、轉成買多，代表殺跌的人變少、開始有人主動接。只有 OKX 一家，日線用 UTC+8 的日界；每小時那一頁是近 7 天，每一根放在那一小時結束的位置。',
          de='Market buys minus market sells of spot BTC on OKX. During a drop, taker selling that fades and turns to net buying means fewer people are dumping and someone has started to buy actively. OKX only; daily bars use UTC+8 days, and the hourly view covers the last 7 days with each bar placed at the end of its hour.')

    def c_tk():   # 顏色：drawTk（現貨 s1→c3、永續 s2→ac，各自的中位數虛線同色）；「比常態多買／多賣」取自 tkPanel 兩張讀數卡（≥ 中位數綠、否則紅）
        x = dv.get('taker')
        if not has(x): return NA('tk', '現貨與永續的主動買賣', 'Spot vs perpetual taker flow', '多家交易所的主動買賣量（deriv.taker）', 'multi-exchange taker volumes (deriv.taker)')
        sm = (x.get('spot') or {}).get('med'); pm = (x.get('perp') or {}).get('med'); sv = ' + '.join(x.get('spot_venues') or []); pv = ', '.join(x.get('perp_venues') or [])
        return dict(k='tk', zh='現貨與永續的主動買賣', en='Spot vs perpetual taker flow', hz='現貨 30 天合計', he='Spot, 30-day sum', f='kbtc', rng=365, rows=thin(x['rows'], 2), p=1,
          ser=[ser(2, zh='現貨 30 天', en='Spot, 30 days', col='c3', w=1.5), ser(3, zh='永續 30 天', en='Perpetuals, 30 days', col='ac', w=1.5)],
          refs=[dict(v=0, col='k2', solid=1)] + ([dict(v=sm / 1e3, col='c3', zh='現貨的常態', en='Spot, typical')] if sm is not None else []) + ([dict(v=pm / 1e3, col='ac', zh='永續的常態', en='Perpetuals, typical')] if pm is not None else []),
          zones=[dict(lo=sm / 1e3, hi=None, col='up', zh='現貨比常態多買', en='Spot: more buying than usual', nz='現貨的常態線', ne='the typical spot level'), dict(lo=None, hi=sm / 1e3, col='dn', zh='現貨比常態多賣', en='Spot: more selling than usual')] if sm is not None else [],
          leg=[['k2', '虛線：各自的常態（中位數）', 'Dashed: each one\'s typical level (median)', 'dash']],
          dz='主動買減主動賣的 30 天加總（顆）。現貨是 %s 合計，永續是 %s 的 USDT 永續合計。永續長期就是主動賣比較多，所以要和虛線（各自的中位數）比，不是看正負；現貨主導的走勢通常比永續主導的走得穩。' % (sv.replace(' + ', '＋') or '幾家交易所', pv.replace(', ', '、') or '幾家交易所'),
          de='The 30-day sum of taker buys minus taker sells (BTC). Spot is %s combined; perpetuals are the USDT contracts on %s. Perpetual taker selling runs high over time, so compare each line with its dashed median rather than with zero; moves led by spot usually hold better than ones led by perpetuals.' % (sv or 'several exchanges', pv or 'several venues'))

    # ════ 6. 大環境 ════
    def c_stk():   # 顏色：drawStk（BTC s2→ac、S&P 500 ink、那斯達克 s1→c3、黃金 s4→c5；90 日勝率 s4→c5 面積、50% 線 ink-3→k2）；高於 50% 的區帶取自 stkSay（>50 是正面），顏色依意義選
        x = f.get('btc_vs_stocks') or {}; rel = x.get('rel') or {}; modes = []
        if has(rel):
            modes.append(dict(mz='近兩個月漲跌', me='Two-month change', hz='BTC 自 %s 以來' % md(rel.get('start') or '0000-00-00'), he='BTC since ' + (rel.get('start') or ''), f='pct1', rows=rel['rows'],
              ser=[ser(1, zh='BTC', en='BTC', col='ac', w=1.8), ser(2, zh='S&P 500', en='S&P 500', col='ink', w=1.4), ser(3, zh='那斯達克', en='Nasdaq', col='c3', w=1.4), ser(4, zh='黃金', en='Gold', col='c5', w=1.4)], refs=[dict(v=0, col='k2', solid=1)]))
        if has(x):
            modes.append(dict(mz='贏過 S&P 500 的比例', me='Win rate vs S&P 500', hz='近 90 個交易日，BTC 漲幅大於 S&P 500 的比例', he='Share of the last 90 sessions BTC beat the S&P 500', f='p1', rows=x['rows'],
              ser=[ser(1, zh='90 日勝率', en='90-session win rate', col='c5', fill=1, w=1.6)], refs=[dict(v=50, col='k2', zh='50%', en='50%')],
              zones=[dict(lo=50, hi=None, col='up', zh='高於 50%：BTC 贏的天數比較多', en='Above 50%: BTC wins on more days', nz='50% 線', ne='the 50% line')]))
        if not modes: return NA('stk', 'BTC 對美股和黃金', 'BTC vs stocks and gold', 'BTC 和美股、黃金的比較（flows.btc_vs_stocks）', 'the BTC vs stocks and gold comparison (flows.btc_vs_stocks)')
        return dict(k='stk', zh='BTC 對美股和黃金', en='BTC vs stocks and gold', modes=modes,
          dz='第一頁是近兩個月 BTC、S&P 500、那斯達克和黃金各自的漲跌。第二頁是近 90 個美股交易日裡，BTC 當天漲幅大於 S&P 500 的比例，高於 50% 代表 BTC 贏的天數比較多。黃金用一枚代表一盎司黃金的代幣代替。',
          de='The first view shows how BTC, the S&P 500, the Nasdaq and gold have each moved over the last two months. The second is the share of the last 90 US sessions in which BTC rose more than the S&P 500; above 50% means BTC won on more days. Gold is proxied by a token backed by one ounce of gold.')

    def c_macro():   # 現有網站只有讀數（V.flows 的 kpi 和 flInterp），沒有走勢圖，所以是清單卡；語氣色照 flInterp：warn→c5、neg→dn、pos→up、其餘灰
        fr = f.get('fred') or {}; nq = fr.get('NASDAQCOM') or {}; dx = fr.get('DTWEXBGS') or {}; tn = fr.get('DGS10') or {}; rr = f.get('dfii10') or {}; rows = []
        if nq.get('corr30') is not None:
            c = nq['corr30']
            rows.append(row('BTC 和那斯達克的 30 日相關', 'BTC–Nasdaq 30-day correlation', c, f='s2', bar=(c + 1) * 50, mk=75, col='c5' if c >= .5 else 'k2',
              nz='高度同步：美股大跌時 BTC 很難獨善其身' if c >= .5 else '有些同步，但不緊密' if c >= .2 else '幾乎無關，BTC 走自己的路' if c > -.2 else '反向，少見',
              ne='Moving together: BTC will struggle to escape a stock sell-off' if c >= .5 else 'Loosely in step' if c >= .2 else 'Almost unrelated: BTC is going its own way' if c > -.2 else 'Moving opposite, which is rare'))
        if dx.get('corr30') is not None:
            c = dx['corr30']
            rows.append(row('BTC 和美元指數的 30 日相關', 'BTC–dollar index 30-day correlation', c, f='s2', bar=(c + 1) * 50, mk=50, col='k2',
              nz='明顯反向：美元走強時 BTC 通常受壓' if c <= -.3 else '同向，少見' if c >= .3 else '關係不明顯，美元不是現在的主要推力', ne='Clearly opposite: a stronger dollar usually weighs on BTC' if c <= -.3 else 'Same direction, which is rare' if c >= .3 else 'No clear link: the dollar is not the main driver now'))
        if rr.get('value') is not None:
            v = rr['value']; bp = rr.get('chg_20obs_bp') or 0
            lv = ('實質利率為負，對不生息的資產有利', 'Negative real yield: good for assets that pay no income') if v < 0 else ('0–1%：寬鬆', '0–1%: loose') if v < 1 else ('1–2%：中性偏緊', '1–2%: neutral to tight') if v < 2 else ('2% 以上：偏緊，持有不生息資產的機會成本高', 'Above 2%: tight, a high cost for holding assets that pay no income')
            ch = ('近 20 個交易日上升 %d 個基點，壓力增加' % bp, 'up %d bp over 20 sessions, more pressure' % bp) if bp >= 20 else ('近 20 個交易日下降 %d 個基點，壓力減輕' % -bp, 'down %d bp over 20 sessions, less pressure' % -bp) if bp <= -20 else ('近 20 個交易日變化不大', 'little change over 20 sessions')
            rows.append(row('10 年期實質利率', '10-year real yield', v, f='p2', col='dn' if bp >= 20 else 'up' if bp <= -20 else 'k2', nz=lv[0] + '；' + ch[0], ne=lv[1] + '; ' + ch[1]))
        if tn.get('last') is not None: rows.append(row('10 年期美債殖利率（名目）', '10-year Treasury yield (nominal)', tn['last'], f='p2', nz='資料日 ' + ymd(tn.get('last_date') or ''), ne='As of ' + (tn.get('last_date') or '')))
        if nq.get('last') is not None: rows.append(row('那斯達克指數', 'Nasdaq Composite', format(int(round(nq['last'])), ','), ve=format(int(round(nq['last'])), ','), nz='資料日 ' + ymd(nq.get('last_date') or ''), ne='As of ' + (nq.get('last_date') or '')))
        if dx.get('last') is not None: rows.append(row('廣義美元指數', 'Broad dollar index', '%.1f' % dx['last'], ve='%.1f' % dx['last'], nz='資料日 ' + ymd(dx.get('last_date') or ''), ne='As of ' + (dx.get('last_date') or '')))
        if not rows: return NA('macro', '利率、美元與相關性', 'Rates, the dollar and correlations', '利率、美元和相關係數（flows.fred、flows.dfii10）', 'rates, the dollar and correlations (flows.fred, flows.dfii10)')
        hs = dict(hz='BTC 和那斯達克的 30 日相關', he='BTC–Nasdaq 30-day correlation', hs=dict(v=nq['corr30'], f='s2')) if nq.get('corr30') is not None else {}
        return dict(k='macro', zh='利率、美元與相關性', en='Rates, the dollar and correlations', list=dict(rows=rows),
          dz='BTC 和那斯達克、美元指數的 30 日相關係數，加上 10 年期美債的實質利率和名目殖利率。相關係數高於 0.5 代表同漲同跌；實質利率越高，持有不生息資產的機會成本越高。現有網站沒有這幾項的走勢圖，這裡只放讀數。',
          de='The 30-day correlation of BTC with the Nasdaq and with the dollar index, plus the real and nominal 10-year Treasury yields. A correlation above 0.5 means they rise and fall together; the higher the real yield, the higher the cost of holding an asset that pays no income. The live site has no charts for these, so this card shows readings only.', **hs)

    def reuse(k, zh, en):   # 已經在鏈上那一頁做好的圖，直接拿來用
        return X[k] if k in X else NA(k, zh, en, '「%s」這張圖（鏈上那一頁還沒做出來）' % zh, 'the "%s" chart (not built by the on-chain page)' % en)

    def grp(zh, en, sz, se, charts):
        for c in charts: X[c['k']] = c
        return dict(zh=zh, en=en, sz=sz, se=se, charts=charts)

    return [
        grp('機構', 'Institutions', 'ETF 和 CME 的機構資金是進還是出', 'Is institutional money in ETFs and on CME coming in or going out', [c_etf(), c_cot()]),
        grp('各地買盤', 'Regional demand', '美國、亞洲、韓國哪邊在買，幣往交易所進還是出', 'Which region is buying, and whether coins are moving onto or off exchanges', [c_prus(), c_prasia(), c_prperp(), c_kp(), c_exflow(), c_exch()]),
        grp('鏈上需求', 'On-chain demand', '新的需求接不接得住供給，新的錢有沒有進來', 'Is new demand absorbing supply, and is new money arriving', [c_ad(), c_dmd(), c_capflow(), c_grad(), c_rcliq(), c_stab()]),
        grp('大戶與長期持有者', 'Whales and long-term holders', '大戶和長期持有者在加碼、出貨還是不動', 'Are whales and long-term holders adding, distributing or sitting still',
            [c_whale(), c_whalet(), reuse('lthnet', '長期持有者 30 日淨部位變化', 'LTH 30-day net position change'), reuse('lsrchg', '長短期供給比 30 日變化', 'LTH/STH supply ratio, 30-day change'),
             reuse('sthd', '短期持有者供給 90 天變化', 'STH supply, 90-day change'), reuse('dorm', 'Dormancy', 'Dormancy'), c_supliq()]),
        grp('主動買賣', 'Taker flow', '誰在用市價主動買、誰在主動賣', 'Who is hitting the market to buy, and who to sell', [c_svd(), c_tk()]),
        grp('大環境', 'Macro', '美股、黃金、利率和美元怎麼走', 'What stocks, gold, rates and the dollar are doing', [c_stk(), c_macro()]),
    ]
