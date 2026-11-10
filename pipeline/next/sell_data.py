# -*- coding: utf-8 -*-
"""「賣壓：賣壓出清了沒」這一頁的資料：五個小問題。十一張圖沿用 oc_data.py 已經做好的（X 裡），這裡補五張：
回調壓力清單、賣壓累積與動能品質、依持有時間的實現獲利／虧損、SOPR 三個視角、礦工讀數。
顏色照現有網站 assets/app.js：
  回調壓力清單 pbPanel ＋ app.css .light.on：成立＝--up→up，沒成立＝--ink-3→k2
  賣壓累積 drawSx：賣壓＝--down→dn、動能＝--s3→c4、動能 0.3 線和底部組合的底色＝--s3→c4、標記依之後 90 天漲跌 up／dn
  持有時間 drawAge 的 AGE_COL：stg4, stg3, stg2, s3, stg1, stg0 → ac, c5, up, c4, c4, c3（s3 和 stg1 在這套色盤是同一個青色，2–5 年改用虛線分開）
  SOPR drawOc：線＝ocCol 預設 --s1→c3，參考線＝--down→dn
  礦工 ocInterp／hashRibRead：只有 warn／neu 兩種語氣，warn→c5，其餘不上色"""

AGE_COL = ['ac', 'c5', 'up', 'c4', 'color-mix(in srgb, var(--c4) 45%, var(--c3))', 'c3']   # 2–5 年在現有網站是另一個藍青色，這裡用青和藍紫的中間色分開
AGE_NM = [('1 個月內', '< 1 month'), ('1–6 個月', '1–6 months'), ('6–12 個月', '6–12 months'), ('1–2 年', '1–2 years'), ('2–5 年', '2–5 years'), ('5 年以上', '5+ years')]
PB_LAB = dict(sth=('① 價格回到短期持有者成本', '① Price back at short-term holder cost'), psip=('② 獲利供給 ≤ 65%', '② Supply in profit ≤ 65%'), sthl=('③ 短期持有者虧損 ≥ 50%', '③ Short-term holders in loss ≥ 50%'),
              sec=('④ 賣方衰竭進極端區', '④ Seller exhaustion in the extreme zone'), rloss=('⑤ 實現虧損峰值背離', '⑤ Realized-loss peak divergence'))
RL_KIND = dict(div=('背離', 'divergence'), cap=('投降', 'capitulation'), flat=('差不多', 'similar'))
# 沿用的十一張圖，萬一 X 裡沒有，用這裡的名字出一張「沒有資料」
REUSE = dict(profit=('短期持有者獲利比例', 'Short-term holders in profit'), sopr=('短期持有者賣出時的盈虧', 'Short-term holder SOPR'), pnlr=('短期持有者實現獲利與虧損', 'STH realized profit and loss'), conf=('對趨勢的信心', 'Confidence in the trend'),
             npl=('淨實現損益', 'Net realized P&L'), rpl=('實現獲利 ÷ 虧損（90 天）', 'Realized profit ÷ loss (90d)'), rloss=('每日實現虧損', 'Daily realized loss'), ssr=('賣方風險比', 'Sell-side risk ratio'),
             sec=('賣方衰竭常數', 'Seller exhaustion constant'), mom=('鏈上勢能', 'On-chain momentum'), lthrl=('長期持有者已實現虧損', 'LTH realized loss'))

def build(L, N, E, dn, X):
    o = L.get('onchain') or {}; ch = L.get('chips') or {}
    ser = lambda c, **k: dict(c=c, **k)
    row = lambda zh, en, v, **k: dict(zh=zh, en=en, v=v, **k)
    sg = lambda v, d=1: ('%+.*f%%' % (d, v)).replace('-', '−')          # +1.2%／−0.4%
    usd = lambda v: '$' + format(int(round(v)), ',')
    sl = lambda s: s.replace('-', '/')
    md = lambda s: s[5:].replace('-', '/')
    nodata = lambda k, zh, en, wz, we: dict(k=k, zh=zh, en=en, na=dict(zh=wz, en=we))
    close = ((L.get('price') or {}).get('bar') or {}).get('c')

    # ── 1. 回調壓力清單（onchain.pullback）：五盞燈，一列一盞 ──
    def pullback():
        x = o.get('pullback')
        if not x or not x.get('items'): return nodata('pullback', '回調壓力清單', 'Pullback pressure checklist', '今天沒有這份資料。這張清單看五個條件有幾個成立：價格回到短期持有者成本、獲利供給 65% 以下、短期持有者虧損 50% 以上、賣方衰竭進極端區、實現虧損峰值背離。',
                                                  'No data today. The checklist counts how many of five conditions hold: price back at short-term holder cost, supply in profit at or below 65%, short-term holders in loss at or above 50%, seller exhaustion in its extreme zone, and a realized-loss divergence.')
        def cond(it):
            i = it['id']
            if i == 'sth': return ('收盤在成本 %s 的 3%% 以內或以下' % usd(it['ref']), 'Close within 3%% of, or below, the %s cost' % usd(it['ref'])) if it.get('ref') else ('收盤在成本的 3% 以內或以下', 'Close within 3% of, or below, the cost')
            if i == 'psip': return ('全體供給有多少在獲利，65% 以下算成立', 'Share of all coins in profit; 65% or less counts')
            if i == 'sthl': return ('短期持有者的幣有多少在虧損，50% 以上算成立', 'Share of short-term holder coins at a loss; 50% or more counts')
            if i == 'sec': return ('賣方衰竭常數低於 %g（輔助，只看現在）' % it.get('ref', .13), 'Seller exhaustion constant below %g (auxiliary, current only)' % it.get('ref', .13))
            return ('近 30 天內出現一對價格更低、認賠卻更少的低點（輔助，只看現在）', 'A pair of lows within 30 days with a lower price but smaller losses (auxiliary, current only)')
        def light(it):
            i = it['id']; ok = bool(it.get('ok')); cz, ce = cond(it); lab = PB_LAB.get(i, (i, i)); v = it.get('v')
            r = row(lab[0], lab[1], v, col='up' if ok else 'k2', nz=('成立：' if ok else '未成立：') + cz, ne=('Lit: ' if ok else 'Not lit: ') + ce[0].lower() + ce[1:])
            if i == 'sth': r['f'] = 'pct1'
            elif i == 'sec': r['f'] = 'n3'
            elif i == 'rloss':
                k = RL_KIND.get(v) if isinstance(v, str) else None
                r['v'] = k[0] if k else None
                if k: r['ve'] = k[1]
            else:
                r['f'] = 'p1'
                if v is not None: r['bar'] = v; r['mk'] = 65 if i == 'psip' else 50
            return r
        rows = [light(it) for it in x['items']]
        def stat(lbz, lbe, s, base):
            if not s or not s.get('n'): return row(lbz, lbe, '樣本不足', ve='Too few cases')
            return row(lbz, lbe, '%d / %d 次上漲' % (s['up'], s['n']), ve='%d of %d rose' % (s['up'], s['n']),
                       nz='中位數 %s' % sg(s['med']) + ('；同期任一天買進是 %d%% 上漲、中位數 %s' % (base['up'], sg(base['med'])) if base else ''),
                       ne='Median %s' % sg(s['med']) + ('; any day in the same period: %d%% rose, median %s' % (base['up'], sg(base['med'])) if base else ''))
        if x.get('r30'): rows.append(stat('①–③ 同時成立之後 30 天', '30 days after ①–③ all held', x.get('r30'), x.get('base30')))
        if x.get('r90'): rows.append(stat('①–③ 同時成立之後 90 天', '90 days after ①–③ all held', x.get('r90'), x.get('base90')))
        if x.get('n_eps'):
            rows.append(row('2015 年起三項同時成立', 'Stretches with ①–③ all lit since 2015', '%d 段' % x['n_eps'], ve='%d stretches' % x['n_eps'],
                            nz='共 %s 天，隔 30 天以上算新的一段。熊市中段（2018、2022 年）也常三項同時成立。' % format(x.get('days') or 0, ','), ne='%s days in all; a gap of 30+ days starts a new stretch. All three also line up in the middle of bear markets (2018, 2022).' % format(x.get('days') or 0, ',')))
        eps = x.get('eps') or []
        if eps and eps[-1].get('end') == x.get('date') and all(it.get('ok') for it in x['items'][:3]):
            e = eps[-1]; rows.append(row('這一段從 %s 開始' % sl(e['start']), 'Current stretch began %s' % e['start'], '%d 天' % e['days'], ve='%d days' % e['days'], col='up', nz='開始那天收盤 %s' % usd(e['price']), ne='Close on the first day: %s' % usd(e['price'])))
        n_ok = x.get('n_ok', sum(1 for it in x['items'] if it.get('ok'))); n = x.get('n', len(x['items']))
        return dict(k='pullback', zh='回調壓力清單', en='Pullback pressure checklist', hz='五盞燈亮了幾盞', he='Lights lit, out of five', hs=dict(v='%d / %d' % (n_ok, n), f='txt', ve='%d of %d' % (n_ok, n)), list=dict(rows=rows),
                    dz='過去熊市轉牛市的過渡期，回調走到後段時常同時出現這五個條件。前三項每天可以回測，後兩項只看現在。這張清單說的是回調的壓力釋放到哪裡，不是買點。',
                    de='Five conditions that have tended to show up together late in pullbacks during past bear-to-bull transitions. The first three can be back-tested daily; the last two are current readings only. The list shows how far pullback pressure has been released, not a buy signal.')

    # ── 2. 賣壓累積與動能品質（chips.stress）：照 drawSx，動能乘 100 和賣壓畫在同一個 0–100 的高度 ──
    def sx():
        x = ch.get('stress')
        if not x or not x.get('rows') or x.get('r') is None: return nodata('sx', '賣壓累積與動能品質', 'Selling pressure and momentum quality', '今天沒有這份資料。這張圖只用每日收盤，算弱勢拖了多久（賣壓累積 0–100）和近 21 天漲跌得多快多穩（動能品質 0–1）。',
                                                                            'No data today. Built from daily closes only, this chart tracks how long weakness has dragged on (pressure, 0–100) and how fast and steady the last 21 days were (momentum quality, 0–1).')
        prm = x.get('prm') or {}; th = prm.get('th', .45); rs = prm.get('reset', .7)
        rows = [[r[0], r[1], r[2], None if r[3] is None else round(r[3] * 100, 1)] for r in x['rows']]; last = rows[-1][0]
        ev = x.get('ev') or []
        def mk(e):
            f = e.get('f90')
            return dict(d=dn(e['date']), v=100, up=0, col='c4' if f is None else 'up' if f >= 0 else 'dn', zh='底部組合' if f is None else '90 天 ' + sg(f, 0), en='combo' if f is None else '90d ' + sg(f, 0))
        return dict(k='sx', zh='賣壓累積與動能品質', en='Selling pressure and momentum quality', hz='賣壓累積（0–100）', he='Selling pressure (0–100)', f='n0', rng=365, rows=rows, p=1, dom=[0, 100], hero=1,
          ser=[ser(3, zh='動能品質 × 100', en='Momentum quality × 100', col='c4', w=1.4), ser(2, zh='賣壓累積', en='Selling pressure', col='dn', w=1.9)],
          refs=[dict(v=30, col='c4', zh='動能 0.3', en='Momentum 0.3')],
          zones=[dict(lo=100, hi=None, col='dn', zh='賣壓累積到 100', en='Pressure at 100', nz='100', ne='100')],
          spans=[dict(a=dn(e['date']), b=dn(e['exit']) if e.get('exit') else last, col='c4', op=.12) for e in ev],
          marks=[mk(e) for e in ev],
          leg=[['c4', '底部組合出現到賣壓歸零', 'Bottom combination until pressure resets', 'box'], ['up', '組合之後 90 天上漲', 'Higher 90 days after the combination', 'ring'], ['dn', '組合之後 90 天下跌', 'Lower 90 days after the combination', 'ring']],
          dz='本站自製，只用每日收盤。動能品質＝近 21 天日報酬的平均 ÷ 標準差 × √21，用常態分布換成 0–1（圖上乘以 100）：漲得又快又穩接近 1、跌得又快又穩接近 0。賣壓累積用另一個比較短的動能來加減：日報酬的指數加權平均 ÷ 指數加權標準差（跨度 10 天，越近的日子權重越大），同樣換成 0–1；低於 %g 時每天往上加（離得越遠加越多）、高於 %g 時以同樣速度往下減，夾在 0–100，所以反彈當天就會回落。賣壓到 100 而且動能品質低於 0.3 叫底部組合，青色底是從組合出現到賣壓歸零的期間。回測只有二十次左右，換一個收盤價來源或參數稍微調一下，次數和勝率就會變幾次。2026-11-11 起賣壓累積改用這個短線動能，歷史讀數一併重算。只作讀值，不是買賣訊號。' % (th, th),
          de='Home-made, from daily closes only. Momentum quality is the mean ÷ standard deviation of the last 21 daily returns × √21, mapped to 0–1 with the normal distribution (drawn × 100): near 1 for a fast, steady rise, near 0 for a fast, steady fall. Selling pressure runs on a second, shorter momentum: the exponentially weighted mean ÷ standard deviation of daily returns (span 10 days, recent days weigh more), mapped to 0–1 the same way. It adds up each day that sits below %g (more the further below) and drains at the same rate when above, capped at 0–100, so a bounce pulls it back the same day. Pressure at 100 with momentum quality under 0.3 is the bottom combination; cyan bands run from each one until pressure resets. The backtest has only about twenty cases; a different close source or a small parameter change shifts the counts by a few. Since 2026-11-11 selling pressure uses this short momentum, and the history was recalculated. Reading only, not a trade signal.' % th)

    # ── 3. 依持有時間的實現獲利／虧損（onchain.agepl）：網站是堆疊面積，這裡的規格沒有堆疊，改成一組一條線，再加一條 6 個月以上合計 ──
    def agepl():
        x = o.get('agepl')
        if not x or not x.get('rows'): return nodata('agepl', '依持有時間的實現獲利／虧損', 'Realized profit and loss by holding time', '今天沒有這份資料。這張圖把每天賣出的幣依持有多久分成六組，看 30 天的實現獲利和實現虧損各是哪幾組貢獻的。',
                                                      'No data today. This chart groups coins sold each day by how long they were held, showing which groups account for the 30-day realized profit and realized loss.')
        def mode(k, mz, me, hz, he, th, zz, ze):
            rows = []
            for r in x['rows']:
                if not r[k] or len(r[k]) < 6: continue
                v = [r[k][g] or 0 for g in range(6)]; cum = [round(sum(v[g:]), 2) for g in range(6)]   # 堆疊：最老的在最下面，第 g 組的頂＝它和比它老的加起來
                rows.append([r[0], r[1]] + v + [round(sum(v[2:6]), 1)] + cum + [0])
            return dict(mz=mz, me=me, hz=hz, he=he, rows=rows, notag=1,
                        ser=[ser(9 + g, vc=2 + g, zh='持有 ' + AGE_NM[g][0], en='Held ' + AGE_NM[g][1], col=AGE_COL[g], w=1, op=.9) for g in range(6)] + [ser(8, hide=1, zh='6 個月以上合計', en='6+ months, total')],
                        bands=[dict(a=9 + g, b=(10 + g) if g < 5 else 15, col=AGE_COL[g], op=.62) for g in range(6)])
        return dict(k='agepl', zh='依持有時間的實現獲利／虧損', en='Realized profit and loss by holding time', f='p1', p=1, dom=[0, 100], hero=6,
          dz='每天賣出的幣依持有多久分成六組，色塊是各組在 30 天合計裡的佔比，疊起來是 100%，最老的在最下面；可以切換看實現獲利或實現虧損。大數字是持有 6 個月以上四組的合計：它在實現虧損裡升高，代表放了半年以上的人也開始認賠。資料是逐筆計算，交易所內部搬幣也會被算成一筆賣出。',
          de='Coins sold each day are grouped by holding time; each layer is that group\'s share of the 30-day total, stacked to 100% with the oldest at the bottom. Switch between realized profit and realized loss. The headline figure is the four groups held 6+ months combined: when it rises in realized loss, holders of more than half a year are selling at a loss too. The data is per transaction output, so an exchange moving coins internally counts as a sale.',
          modes=[mode(2, '實現獲利', 'Realized profit', '6 個月以上佔實現獲利', '6+ months\' share of realized profit', 50, '獲利了結有一半以上來自持有 6 個月以上的人', 'Over half of profit-taking comes from coins held 6+ months'),
                 mode(3, '實現虧損', 'Realized loss', '6 個月以上佔實現虧損', '6+ months\' share of realized loss', 40, '持有 6 個月以上的人也在認賠（佔四成以上）', 'Holders of 6+ months are selling at a loss too (40% or more)')])

    # ── 4. SOPR 三個視角（onchain.viz）：照 drawOc，線 c3、參考線 dn ──
    def soprf():
        vz = o.get('viz') or {}
        SP = [('asopr', '全網', 'Network', 'aSOPR（7 日均）', 'aSOPR (7-day avg)'), ('lth-sopr', '長期持有者', 'Long-term holders', 'LTH-SOPR（7 日均）', 'LTH-SOPR (7-day avg)'), ('sth-sopr', '短期持有者', 'Short-term holders', 'STH-SOPR（7 日均）', 'STH-SOPR (7-day avg)')]
        ms = []
        for key, mz, me, zh, en in SP:
            v = vz.get(key); rows = [r for r in (v or {}).get('rows') or [] if r[1] is not None and r[1] > 0]
            if not rows: continue
            ry = (v.get('ref') or {}).get('y')
            ms.append(dict(mz=mz, me=me, hz=zh, he=en, rows=rows, ser=[ser(1, zh=zh, en=en, col='c3', w=1.7)],
                           refs=[dict(v=ry, col='dn', zh='%.1f＝賣在成本' % ry, en='%.1f = selling at cost' % ry)] if ry is not None else [],
                           zones=[dict(lo=None, hi=ry, col='dn', zh='低於 %g，賠錢賣' % ry, en='Below %g: selling at a loss' % ry, nz='%g 以下' % ry, ne='below %g' % ry)] if ry is not None else []))
        if not ms: return nodata('soprf', 'SOPR：全網、長期、短期', 'SOPR: network, long-term, short-term', '今天沒有這份資料。SOPR 是賣出的價格除以買進的價格，高於 1 是賺錢賣、低於 1 是賠錢賣。', 'No data today. SOPR is the price coins are sold at divided by the price they were bought at: above 1 is selling at a profit, below 1 at a loss.')
        return dict(k='soprf', zh='SOPR：全網、長期、短期', en='SOPR: network, long-term, short-term', f='n3', modes=ms,
          dz='SOPR 是賣出的價格除以買進的價格，這裡取 7 日平均：高於 1 是賺錢賣，低於 1 是賠錢賣。三個視角是全網（排除一小時內轉手的幣）、長期持有者和短期持有者。長期持有者跌破 1 很少見，過去多半出現在深熊。',
          de='SOPR is the price coins are sold at divided by the price they were bought at, here as a 7-day average: above 1 is selling at a profit, below 1 at a loss. The three views are the whole network (excluding coins moved within an hour), long-term holders and short-term holders. Long-term holders dropping below 1 is rare and has mostly come deep in bear markets.')

    # ── 5. 礦工讀數（onchain.mining、onchain.hash_ribbons）：網站沒有圖，只有讀數 ──
    def miners():
        mi = o.get('mining') or {}; hr = o.get('hash_ribbons') or {}
        if mi.get('hash7') is None and hr.get('ratio') is None: return nodata('miners', '礦工：算力、收入與難度', 'Miners: hashrate, revenue and difficulty', '今天沒有這份資料。這張卡看礦工有沒有被迫關機：算力、每單位算力的收入、下次難度調整，和算力 30 日均對 60 日均的比值。',
                                                                              'No data today. This card checks whether miners are being forced offline: hashrate, revenue per unit of hashrate, the next difficulty adjustment, and the 30-day versus 60-day hashrate average.')
        rows = []; eh = lambda v: format(int(round(v)), ',') + ' EH/s'
        if mi.get('hash7') is not None:
            w = mi.get('wk_chg_pct')
            wz = '' if w is None else '一週 %s' % sg(w) + ('，礦工持續投入，沒有投降跡象' if w >= 0 else '，明顯下降，留意礦工投降（過去常出現在底部附近）' if w < -5 else '，小幅下降')
            we = '' if w is None else '%s on the week' % sg(w) + ('; miners keep adding machines, no sign of capitulation' if w >= 0 else '; a clear drop, watch for miner capitulation (often seen near past bottoms)' if w < -5 else '; a small drop')
            if mi.get('hash7_prev') is not None: wz += '。前一週 ' + eh(mi['hash7_prev']) + '。'; we += '. Previous week: ' + eh(mi['hash7_prev']) + '.'
            rows.append(row('算力 7 日平均', 'Hashrate, 7-day average', eh(mi['hash7']), ve=eh(mi['hash7']), nz=wz, ne=we, **(dict(col='c5') if w is not None and w < -5 else {})))
        if hr.get('ratio') is not None:
            cap = bool(hr.get('capitulation')); r = hr['ratio']; d = hr.get('state_days') or 0
            if cap: nz_ = '30 日均算力低於 60 日均（已 %d 天）：礦工投降期，過去多出現在底部附近；回到 1 以上才是傳統上的恢復訊號。' % d; ne_ = 'The 30-day hashrate average is below the 60-day (%d days): miner capitulation, common near past bottoms; the classic signal comes when it recovers above 1.' % d
            else:
                nz_ = '30 日均算力高於 60 日均 %s（已 %d 天）：礦工狀態健康。' % (sg((r - 1) * 100), d) + ('上次由投降期恢復在 %s。' % sl(hr['last_cross']) if hr.get('last_cross') else '')
                ne_ = 'The 30-day hashrate average is %s above the 60-day (%d days): miners are healthy.' % (sg((r - 1) * 100), d) + (' The last recovery from capitulation was on %s.' % hr['last_cross'] if hr.get('last_cross') else '')
            rows.append(row('Hash Ribbons：算力 30 日均 ÷ 60 日均', 'Hash Ribbons: 30-day ÷ 60-day hashrate', r, f='n3', nz=nz_, ne=ne_, **(dict(col='c5') if cap else {})))
            if hr.get('min_ratio_90d') is not None:
                m = hr['min_ratio_90d']; rows.append(row('近 90 天最低比值', 'Lowest ratio in 90 days', m, f='n3', nz='低於 1，代表這 90 天內出現過礦工投降。' if m < 1 else '這 90 天沒有跌到 1 以下。', ne='Below 1: miners capitulated at some point in these 90 days.' if m < 1 else 'It has not dropped below 1 in these 90 days.'))
        if mi.get('hashprice') is not None:
            nz_ = '每 1 PH/s 算力一天的收入（144 個區塊的獎勵 × 收盤 ÷ 全網算力）。'; ne_ = 'Daily revenue per 1 PH/s of hashrate (the reward of 144 blocks × close ÷ network hashrate).'
            if mi.get('btc_day') is not None: nz_ += '每天新挖約 %s 顆' % format(int(round(mi['btc_day'])), ','); ne_ += ' About %s BTC mined a day' % format(int(round(mi['btc_day'])), ',')
            if mi.get('btc_day') is not None and mi.get('fee_share_pct') is not None: nz_ += '，手續費佔收入 %.1f%%。' % mi['fee_share_pct']; ne_ += ', with fees at %.1f%% of revenue.' % mi['fee_share_pct']
            rows.append(row('Hashprice', 'Hashprice', '$%.2f' % mi['hashprice'], ve='$%.2f' % mi['hashprice'], nz=nz_, ne=ne_))
        for k, be in (mi.get('breakeven') or {}).items():
            j, _, e = k.partition('J@'); under = close is not None and close < be
            rows.append(row('電費損益兩平價：%s J/TH 礦機、電價 $%s' % (j, e), 'Power breakeven: %s J/TH machines at $%s per kWh' % (j, e), be, f='usd0',
                            nz='收盤低於這個價：這類礦機在虧電費。' if under else '收盤高於這個價：這類礦機付完電費還有賺。', ne='Close is below it: these machines lose money on power.' if under else 'Close is above it: these machines still earn after power.', **(dict(col='c5') if under else {})))
        if mi.get('diff_next_pct') is not None:
            dv = mi['diff_next_pct']; nz_ = ''; ne_ = ''
            if mi.get('retarget'): nz_ += '預計 %s 調整' % md(mi['retarget']); ne_ += 'Expected on %s' % mi['retarget']
            if mi.get('diff_progress') is not None: nz_ += '，進度 %.0f%%' % mi['diff_progress']; ne_ += ', %.0f%% of the way there' % mi['diff_progress']
            if mi.get('blocks_left') is not None: nz_ += '，還剩 %s 個區塊' % format(mi['blocks_left'], ','); ne_ += ', %s blocks left' % format(mi['blocks_left'], ',')
            if mi.get('block_time_s') is not None: nz_ += '。目前平均 %.1f 分鐘出一個塊（目標 10 分鐘）' % (mi['block_time_s'] / 60); ne_ += '. Blocks now take %.1f minutes on average (target 10)' % (mi['block_time_s'] / 60)
            nz_ += ('。上調：礦工競爭加劇、成本上升。' if dv >= 0 else '。下調：礦工壓力減輕。'); ne_ += ('. An increase: more competition and higher costs for miners.' if dv >= 0 else '. A cut: less pressure on miners.')
            rows.append(row('下次難度調整', 'Next difficulty adjustment', dv, f='pct1', nz=nz_.lstrip('，。'), ne=ne_.lstrip(',. '), **(dict(bar=mi['diff_progress'], bc='ac') if mi.get('diff_progress') is not None else {})))
        c = dict(k='miners', zh='礦工：算力、收入與難度', en='Miners: hashrate, revenue and difficulty', list=dict(rows=rows),
          dz='礦工的收入不夠付電費時會關機、賣幣，是另一種賣壓來源。算力的 30 日平均跌到 60 日平均下面叫礦工投降，過去常出現在底部附近。現有網站這幾項只有讀數、沒有走勢圖，這裡照樣只放讀數。',
          de='When revenue no longer covers power, miners switch off and sell coins, which is another source of selling. The 30-day hashrate average falling below the 60-day is called miner capitulation and has often come near bottoms. The live site has readings only for these, no chart, and so does this card.')
        if mi.get('hash7') is not None: c.update(hz='算力 7 日平均', he='Hashrate, 7-day average', hs=dict(v=eh(mi['hash7']), f='txt', ve=eh(mi['hash7'])))
        else: c.update(hz='算力 30 日均 ÷ 60 日均', he='Hashrate 30-day ÷ 60-day average', hs=dict(v=hr['ratio'], f='n3'))
        return c

    # ── 短期持有者集中止盈與認賠（onchain.sthsig）：照線上站 drawSthSig，止盈強度往上（up）、認賠強度畫成負值往下（dn），超過門檻的期間鋪底色 ──
    def sthsig():
        x = o.get('sthsig')
        if not x or not x.get('rows'): return nodata('sthsig', '短期持有者集中止盈與認賠', 'Short-term holder profit-taking and capitulation spikes', '今天沒有這份資料。這張圖看持有未滿 6 個月的幣，是不是正在集中獲利了結或集中認賠。', 'No data today. This chart shows whether coins held under 6 months are being sold in a burst of profit-taking or of loss-taking.')
        th = (x.get('prm') or {}).get('th', 2.0); rows = x['rows']; last = rows[-1][0]; runs = x.get('runs') or []
        def mk(r):
            return dict(d=r[3], v=(r[4] if r[2] else -r[4]), up=1 if r[2] else 0, col='up' if r[2] else 'dn', zh=('集中止盈 ' if r[2] else '集中認賠 ') + ('%.1f' % r[4]), en=('Profit-taking ' if r[2] else 'Capitulation ') + ('%.1f' % r[4]))
        return dict(k='sthsig', zh='短期持有者集中止盈與認賠', en='Short-term holder profit-taking and capitulation spikes', hz='認賠強度（畫成負值，−%g 以下＝集中認賠）' % th, he='Capitulation strength (drawn negative; below −%g = spike)' % th, f='n1', rng=365, rows=rows, p=1, hero=1,
          ser=[ser(2, zh='止盈強度', en='Profit-taking strength', col='up', w=1.6), ser(3, zh='認賠強度（負值）', en='Capitulation strength (negative)', col='dn', w=1.6)],
          refs=[dict(v=th, col='up', zh='止盈門檻 +%g' % th, en='Profit-taking threshold +%g' % th), dict(v=-th, col='dn', zh='認賠門檻 −%g' % th, en='Capitulation threshold −%g' % th), dict(v=0, col='k2')],
          spans=[dict(a=r[0], b=max(r[1], r[0] + 1), col='up' if r[2] else 'dn', op=.16) for r in runs],
          marks=[mk(r) for r in runs if r[0] >= last - 400],
          leg=[['up', '集中止盈（止盈強度超過 %g）' % th, 'Profit-taking spike (strength above %g)' % th, 'box'], ['dn', '集中認賠（認賠強度超過 %g）' % th, 'Capitulation spike (strength above %g)' % th, 'box']],
          dz='本站自製，資料 Bitview（逐筆 UTXO、不是實體調整）。取持有未滿 6 個月的幣每天的實現獲利和實現虧損（美元），各自除以短期持有者的實現市值，5 日指數平均後和自己近 105 天比（z 分數）。綠線是止盈強度，往上；紅線是認賠強度，畫成負值、往下；超過 ±%g 的期間鋪底色。集中止盈常出現在反彈的後段，集中認賠常出現在急跌的後段，但兩者都可以連續出現很多天。只作讀值，不是買賣訊號。' % th,
          de='Home-made, from Bitview data (per UTXO, not entity-adjusted). It takes the profit and the loss realized each day on coins held under 6 months (USD), divides each by the short-term holder realized cap, smooths with a 5-day exponential average and compares it with its own last 105 days (z-score). Green is profit-taking strength, upward; red is capitulation strength, drawn negative, downward; periods beyond ±%g are shaded. Profit-taking spikes tend to come late in a bounce and capitulation spikes late in a sharp fall, but either can persist for many days. Reading only, not a trade signal.' % th)

    for fn in (pullback, sx, agepl, soprf, miners, sthsig):
        c = fn(); X[c['k']] = c
    def old(k):   # 沿用的圖；萬一沒有，出一張「沒有資料」，不要整張消失
        return X[k] if X.get(k) else nodata(k, REUSE[k][0], REUSE[k][1], '今天沒有這張圖的資料。', 'No data for this chart today.')
    grp = lambda id_, zh, en, sz, se, keys: dict(id=id_, zh=zh, en=en, sz=sz, se=se, charts=[old(k) if k in REUSE else X[k] for k in keys])
    return [
        grp('sum', '總表', 'Summary', '五盞燈亮了幾盞，弱勢拖了多久', 'How many of the five lights are lit, and how long weakness has dragged on', ['pullback', 'sx']),
        grp('who', '誰套牢', 'Who is underwater', '最近買進的人有多少還在賺', 'How many recent buyers are still in profit', ['profit']),
        grp('pnl', '賣的人賺還是賠', 'Are sellers in profit or at a loss', '賣出的人是獲利了結還是認賠，是哪一群人在賣', 'Whether sellers are taking profit or cutting losses, and which holders are selling', ['sopr', 'pnlr', 'sthsig', 'conf', 'npl', 'agepl', 'soprf']),
        grp('exh', '衰竭', 'Exhaustion', '賣壓在加大還是快耗盡', 'Is selling building up or running dry', ['rpl', 'rloss', 'ssr', 'sec', 'mom', 'lthrl']),
        grp('miners', '礦工', 'Miners', '礦工有沒有被迫關機、賣幣', 'Are miners being forced to switch off and sell', ['miners']),
    ]
