# -*- coding: utf-8 -*-
"""「今天」這一頁的資料：頭版和消息併成一頁。頭部是晨報，下面三段：六個問題各一句、今天要做什麼、消息。site_data.py 會 import。"""

def build(L, N, E, dn, pm):
    E = E or {}
    g = lambda d, k, dflt=None: (d or {}).get(k, dflt)
    en = lambda lst, i, k, zh: (g(lst[i], k) if isinstance(lst, list) and i < len(lst) and isinstance(lst[i], dict) else None) or zh
    row = lambda zh, en_, **k: dict(zh=zh, en=en_, **k)
    md = lambda s: s[5:].replace('-', '/') if s else ''
    MZ = N['modules']; ME = E.get('modules') or {}
    close = pm['px']; dw = L['cycle']['dawn']; fl = L['chips']['flow']; dv = L['deriv']; ex = L['exit']['status']; fw = L['exit']['framework']
    # ── 六個問題各一句（page.html 規則 ㊵，2026-11-20 使用者：「六張概覽卡內容重複，要整理」）──
    # 一張卡只有四樣：問題、一個大數字、那一版的 lead 一句、這一頁的偏向統計（build.py 的 _qa_tally 補）。
    # 各版的 points 只放在那一頁的頭部，不再搬到這裡（原本四行重點和頭版摘要、彼此之間一再重複）。
    # 大數字不能和頭部重複：頭部已經有收盤價和「要盯的價位」（200 日均線、MVRV 0.75 線、出場第一階），所以價位卡不用收盤、出場卡不用離第一階多遠
    sb = (L['onchain'].get('sth_bands') or {}).get('rows') or []; sbg = (sb[-1][1] / sb[-1][2] - 1) * 100 if sb and sb[-1][2] else None
    e20 = (L.get('flows') or {}).get('etf20') or {}; nh = len(ex.get('steps_hit') or []); nl = len(fw.get('ladder') or [])
    Q = [('cycle', '週期', 'Cycle', '現在在週期的哪裡', 'Where we are in the cycle', 'cycle', dict(v=dw['heat'], f='n1'), '晨昏指數的熱度', 'Dawn–Dusk heat'),
         ('lv', '價位', 'Levels', '價格站在哪些成本和關卡上', 'Which cost bases and levels price is standing on', 'market', dict(v=round(sbg, 1), f='pct1') if sbg is not None else None, '收盤離短期持有者成本', 'Close vs short-term holder cost'),
         ('sell', '賣壓', 'Selling', '賣壓出清了沒', 'Has the selling been worked through', 'onchain', dict(v=fl['sth_in_profit_pct']['value'], f='p1'), '短期持有者獲利供給佔比', 'Short-Term Holder Supply in Profit (%)'),
         ('buy', '買盤', 'Demand', '誰在買、錢從哪裡來', 'Who is buying and where the money comes from', 'flows', dict(v=e20['sum'], f='usdM') if e20.get('sum') is not None else None, '現貨 ETF 近 %d 個交易日淨流' % e20.get('n', 20), 'Spot ETF net flow, last %d trading days' % e20.get('n', 20)),
         ('lev', '槓桿', 'Leverage', '槓桿和情緒擠不擠', 'How crowded leverage and sentiment are', 'deriv', dict(v=dv['fund_hist']['value'], f='p1'), '資金費率（年化）', 'Funding rate (annualized)'),
         ('exit', '出場', 'Exit', '那我該怎麼做', 'So what do I do', 'exit', dict(v='%d / %d' % (nh, nl), f='txt', ve='%d / %d' % (nh, nl)) if nl else None, '出場梯子已觸發的階數', 'Exit ladder steps triggered')]
    qc = []
    for cid, zh, en_, qz, qe, mod, hs, hz, he in Q:
        m = MZ.get(mod) or {}; me = ME.get(mod) or {}
        c = dict(k='q_' + cid, zh=zh + '：' + qz, en=en_ + ': ' + qe, dz=m.get('lead') or '', de=me.get('lead') or m.get('lead') or '', go=cid, nofx=1,
                 qa=dict(n={}) if cid != 'exit' else dict(n={}, nz='出場照規則行動，不表態多空。', ne='Exit follows its rules; it takes no side on direction.'))
        if hs: c['hs'] = hs; c['hz'] = hz; c['he'] = he
        qc.append(c)
    # ── 今天要做什麼 ──
    AK = dict(do=('照做', 'Do', 'up', 'ok'), dont=('不做', "Don't", 'dn', 'ban'), watch=('要盯', 'Watch', 'c5', 'eye'), flip=('會推翻', 'Would overturn', 'ac', 'flip'))   # 第四個是圖示代號（page.html 規則 ㉑）
    A = N.get('actions') or []; AE = E.get('actions') or []
    c_act = dict(k='t_act', zh='行動與要盯的價位', en='Actions and levels to watch', nofx=1, dz='照出場框架，今天該做什麼、不該做什麼、要盯哪裡，以及什麼情況會推翻現在的看法。', de='What the exit plan says to do today, what not to do, what to watch, and what would overturn the current view.',
      list=dict(rows=[row(a.get('head') or '', en(AE, i, 'head', a.get('head') or ''), v=AK.get(a.get('kind'), ('', '', 'ink'))[0], ve=AK.get(a.get('kind'), ('', '', 'ink'))[1], col=AK.get(a.get('kind'), ('', '', 'ink'))[2], ic=(AK.get(a.get('kind')) or (0, 0, 0, None))[3], nz=a.get('text') or '', ne=en(AE, i, 'text', a.get('text') or '')) for i, a in enumerate(A)]))
    C = N.get('changes') or []; CE = E.get('changes') or []
    c_chg = dict(k='t_chg', zh='今天變了什麼', en='What changed today', nofx=1, dz='和昨天比，有變化的幾件事。', de='What moved since yesterday.',
      list=dict(rows=[row(c.get('title') or '', en(CE, i, 'title', c.get('title') or ''), v='上升' if c.get('dir') == 'up' else '下降' if c.get('dir') == 'down' else '持平', ve='Up' if c.get('dir') == 'up' else 'Down' if c.get('dir') == 'down' else 'Flat', ic='up' if c.get('dir') == 'up' else 'dn' if c.get('dir') == 'down' else 'go', io=1, col='up' if c.get('dir') == 'up' else 'dn' if c.get('dir') == 'down' else 'k2',
                          nz=(c.get('fig') or '') + '。' + (c.get('say') or ''), ne=en(CE, i, 'fig', c.get('fig') or '') + '. ' + en(CE, i, 'say', c.get('say') or '')) for i, c in enumerate(C)]))
    EV = [e for e in (N.get('events') or []) if e.get('date', '') >= N.get('date', '')][:8]; EVE = {e.get('date', '') + str(i): e for i, e in enumerate(E.get('events') or [])}
    eve = [e for e in (E.get('events') or []) if e.get('date', '') >= N.get('date', '')][:8]
    c_evt = dict(k='t_evt', zh='接下來的日期', en='Coming dates', nofx=1, dz='接下來會影響行情的日子。', de='Dates ahead that could move the market.',
      list=dict(rows=[row(e.get('label') or '', (eve[i].get('label') if i < len(eve) else None) or e.get('label') or '', v=md(e.get('date')), ve=md(e.get('date'))) for i, e in enumerate(EV)]))
    # ── 消息 ──
    IM = dict(bull=('利多', 'Bullish', 'up', 'up'), bear=('利空', 'Bearish', 'dn', 'dn'), neutral=('中性', 'Neutral', 'k2', 'flat'))
    NW = sorted(N.get('news') or [], key=lambda x: -(x.get('weight') or 0)); NE = {x.get('url'): x for x in (E.get('news') or [])}
    def nrow(x):
        im = IM.get(x.get('impact'), IM['neutral']); xe = NE.get(x.get('url')) or {}
        return row(x.get('title') or '', xe.get('title') or x.get('title') or '', v=im[0], ve=im[1], col=im[2], ic=im[3], u=x.get('url'), nz=(x.get('cat') or '') + ' · ' + (x.get('source') or '') + '｜' + (x.get('read') or ''), ne=(xe.get('cat') or x.get('cat') or '') + ' · ' + (xe.get('source') or x.get('source') or '') + ' | ' + (xe.get('read') or x.get('read') or ''))
    c_news = dict(k='t_news', zh='今日要聞', en="Today's news", nofx=1, wide=1, dz='每則新聞下面是它對行情的意思。依重要性排。', de='Each story is followed by what it means for the market, ordered by weight.', list=dict(rows=[nrow(x) for x in NW]))
    R = N.get('research') or {}; RE = E.get('research') or {}; RI = R.get('items') or []; RIE = RE.get('items') or []
    c_res = dict(k='t_res', zh='權威研報怎麼看', en='What institutional research says', nofx=1, dz=R.get('summary') or '', de=RE.get('summary') or R.get('summary') or '',
      list=dict(rows=[row((x.get('source') or '') + '：' + (x.get('title') or ''), (x.get('source') or '') + ': ' + en(RIE, i, 'title', x.get('title') or ''), v=md(x.get('date')), ve=md(x.get('date')), u=x.get('url'), nz=x.get('points') or '', ne=en(RIE, i, 'points', x.get('points') or '')) for i, x in enumerate(RI)]))
    LN = dict(bull=('偏多', 'Leans up', 'up', 'up'), bear=('偏空', 'Leans down', 'dn', 'dn'), neutral=('中性', 'Neutral', 'k2', 'flat'))
    F = N.get('findings') or []; FE = E.get('findings') or []
    c_find = dict(k='t_find', zh='今日發現', en="Today's findings", nofx=1, dz='今天從數據裡看到、值得記下來追蹤的幾件事。每一則之後會回頭檢查對不對。', de='What today\'s data showed that is worth recording and checking later. Each one is revisited to see whether it held.',
      list=dict(rows=[row(x.get('title') or '', en(FE, i, 'title', x.get('title') or ''), v=LN.get(x.get('lean'), LN['neutral'])[0], ve=LN.get(x.get('lean'), LN['neutral'])[1], col=LN.get(x.get('lean'), LN['neutral'])[2], ic=LN.get(x.get('lean'), LN['neutral'])[3], nz=(x.get('what') or '') + (x.get('lean_why') or ''), ne=en(FE, i, 'what', x.get('what') or '') + ' ' + en(FE, i, 'lean_why', x.get('lean_why') or '')) for i, x in enumerate(F)]))
    FU = (N.get('followups') or [])[:6]; FUE = E.get('followups') or []
    SN = dict(open=('追蹤中', 'Open', 'c5', 'pend'), confirmed=('成立', 'Held', 'up', 'ok'), refuted=('不成立', 'Failed', 'dn', 'close'))
    c_fol = dict(k='t_fol', zh='之前的發現，現在怎樣', en='Earlier findings, checked', nofx=1, dz='前幾天記下來的發現，今天回頭看有沒有成立。', de='Findings recorded on earlier days, checked again today.',
      list=dict(rows=[row(x.get('title') or '', en(FUE, i, 'title', x.get('title') or ''), v=SN.get(x.get('status'), SN['open'])[0], ve=SN.get(x.get('status'), SN['open'])[1], col=SN.get(x.get('status'), SN['open'])[2], ic=SN.get(x.get('status'), SN['open'])[3], nz=x.get('say') or '', ne=en(FUE, i, 'say', x.get('say') or '')) for i, x in enumerate(FU)]))
    # ── 跟昨天比（2026-11-25，讀者建議「標出跟昨天比的變化，不只是水位」；deltas.py）：幾個關鍵讀數的日變化，變化大的排前面，每個都說平常算不算大 ──
    import deltas
    DL = deltas.build(L); c_dlt = None
    if DL and DL['rows']:
        MI = lambda v: v.replace('-', '−')
        def dv(x):   # 右邊的變化量
            if x.get('flow'): return MI('%+.1f 億美元' % (x['t'] / 100)), MI('%+.0fM USD' % x['t'])
            if x['unit'] == '%': return MI('%+.1f%%' % x['ch']), MI('%+.1f%%' % x['ch'])
            if x['unit'] == 'pt': return MI('%+.3f 個百分點' % x['ch'] if abs(x['ch']) < .01 else '%+.2f 個百分點' % x['ch']), MI('%+.3f pt' % x['ch'] if abs(x['ch']) < .01 else '%+.2f pt' % x['ch'])
            return ('持平', 'Flat') if not x['ch'] else (MI('%+d' % x['ch']), MI('%+d' % x['ch']))
        LV = [('變化平常', 'An ordinary move'), ('變化偏大', 'A larger move than usual'), ('變化很大', 'A big move')]
        def dz(x):
            q = '' if x['p'] is None else ('（過去一年只有 %d%% 的日子動得比這多）' % (100 - x['p']) if x['lvl'] else '')
            qe = '' if x['p'] is None else (' (only %d%% of days in the past year moved more)' % (100 - x['p']) if x['lvl'] else '')
            if x.get('flow'):
                yz = ('淨流入' if x['y'] > 0 else '淨流出') + ' %.1f 億美元' % (abs(x['y']) / 100); tz = ('淨流入' if x['t'] > 0 else '淨流出') + ' %.1f 億美元' % (abs(x['t']) / 100)
                tr = ('流出變少' if abs(x['t']) < abs(x['y']) else '流出變多') if x['t'] < 0 and x['y'] < 0 else ('流入變多' if x['t'] > x['y'] else '流入變少') if x['t'] > 0 and x['y'] > 0 else ('從流出轉成流入' if x['t'] > 0 else '從流入轉成流出')
                ye = ('in' if x['y'] > 0 else 'out') + 'flow of $%.0fM' % abs(x['y']); te = ('in' if x['t'] > 0 else 'out') + 'flow of $%.0fM' % abs(x['t'])
                tre = ('smaller outflow' if abs(x['t']) < abs(x['y']) else 'bigger outflow') if x['t'] < 0 and x['y'] < 0 else ('bigger inflow' if x['t'] > x['y'] else 'smaller inflow') if x['t'] > 0 and x['y'] > 0 else ('flipped to inflow' if x['t'] > 0 else 'flipped to outflow')
                return ('%s %s，前一天%s：%s。%s%s。' % (md(x['d']), tz, yz, tr, LV[x['lvl']][0], q)), ('%s: net %s, after a net %s the day before: %s. %s%s.' % (md(x['d']), te, ye, tre, LV[x['lvl']][1], qe))
            if not x['lvl']: return ('昨天 %s → 今天 %s，變化平常。' % (MI(x['fz'](x['y'])), MI(x['fz'](x['t'])))), ('%s yesterday, %s today: an ordinary move.' % (MI(x['fe'](x['y'])), MI(x['fe'](x['t']))))   # 平常的小波動不替它講意思，免得把雜訊講成訊號
            return ('昨天 %s → 今天 %s：%s。%s%s。' % (MI(x['fz'](x['y'])), MI(x['fz'](x['t'])), x['mz'], LV[x['lvl']][0], q)), ('%s yesterday, %s today: %s. %s%s.' % (MI(x['fe'](x['y'])), MI(x['fe'](x['t'])), x['me'], LV[x['lvl']][1], qe))
        big = [x for x in DL['rows'] if x['lvl']]
        c_dlt = dict(k='t_dlt', zh='跟昨天比', en='Since yesterday', nofx=1, wide=1,
          dz='幾個關鍵讀數今天和前一天（%s）比變了多少，變化大的排前面。「平常算不算大」是和這個讀數過去一年每天的變化比；只有變化偏大的才上色，平常的小波動不用太在意。%s' % (md(DL['d0']), ('今天動得比平常大的是' + '、'.join(x['zh'].split('（')[0] for x in big) + '。') if big else '今天沒有哪一項動得比平常大。'),
          de='How much a few key readings moved since the previous day (%s), biggest moves first. "Usual or not" compares today\'s move with every day of the past year; only larger-than-usual moves are coloured, ordinary wiggles are not worth much attention. %s' % (md(DL['d0']), ('Moving more than usual today: ' + ', '.join(x['en'].split(' (')[0] for x in big) + '.') if big else 'Nothing moved more than usual today.'),
          list=dict(rows=[row(x['zh'], x['en'], v=dv(x)[0], ve=dv(x)[1], col='ac' if x['lvl'] == 2 else 'c5' if x['lvl'] == 1 else 'k2', nz=dz(x)[0], ne=dz(x)[1]) for x in DL['rows']]))
    G = ([dict(zh='跟昨天比', en='Since yesterday', sz='幾個關鍵讀數今天變了多少，變化大的排前面', se='How key readings moved since yesterday, biggest first', charts=[c_dlt])] if c_dlt else []) + \
        [dict(zh='六個問題各一句', en='The six questions, one line each', sz='每個問題今天的結論，點進去看證據', se="Today's verdict on each question; open the page for the evidence", charts=qc),
         dict(zh='今天要做什麼', en='What to do today', sz='行動、變化、接下來的日子', se='Actions, changes and dates ahead', charts=[c_act, c_chg, c_evt]),
         dict(zh='消息', en='News', sz='新聞、研報、今天的發現', se="News, research and today's findings", charts=[c_news, c_res, c_find, c_fol])]
    st = N.get('stance') or {}; ste = E.get('stance') or {}; W = N.get('watch') or []; WE = E.get('watch') or []
    brief = dict(edition=N.get('edition'), date=N.get('date'), hz=N.get('headline') or '', he=E.get('headline') or N.get('headline') or '', sz=N.get('summary') or '', se=E.get('summary') or N.get('summary') or '',
                 st=[st.get('label') or '', ste.get('label') or st.get('label') or '', st.get('tone') or 'neutral'], close=close, chg=L['price']['bar']['chg_pct'],
                 watch=[row(w.get('label') or '', en(WE, i, 'label', w.get('label') or ''), v=w.get('value'), f='usd0', nz=w.get('note') or '', ne=en(WE, i, 'note', w.get('note') or '')) for i, w in enumerate(W)])
    return G, brief
