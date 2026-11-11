# -*- coding: utf-8 -*-
"""「今天」這一頁的資料：頭版和消息併成一頁。頭部是晨報，下面三段：六個問題各一句、今天要做什麼、消息。site_data.py 會 import。"""

def build(L, N, E, dn, pm):
    E = E or {}
    g = lambda d, k, dflt=None: (d or {}).get(k, dflt)
    en = lambda lst, i, k, zh: (g(lst[i], k) if isinstance(lst, list) and i < len(lst) and isinstance(lst[i], dict) else None) or zh
    row = lambda zh, en_, **k: dict(zh=zh, en=en_, **k)
    md = lambda s: s[5:].replace('-', '/') if s else ''
    MZ = N['modules']; ME = E.get('modules') or {}
    close = pm['px']; dw = L['cycle']['dawn']; fl = L['chips']['flow']; dv = L['deriv']; ex = L['exit']['status']
    # ── 六個問題各一句 ──
    Q = [('cycle', '週期', 'Cycle', '現在在週期的哪裡', 'Where we are in the cycle', 'cycle', dict(v=dw['heat'], f='n1'), '晨昏指數的熱度', 'Dawn–Dusk heat'),
         ('lv', '價位', 'Levels', '價格站在哪些成本和關卡上', 'Which cost bases and levels price is standing on', 'market', dict(v=close, f='usd0'), '收盤', 'Close'),
         ('sell', '賣壓', 'Selling', '賣壓出清了沒', 'Has the selling been worked through', 'onchain', dict(v=fl['sth_in_profit_pct']['value'], f='p1'), '短期持有者獲利比例', 'Short-term holders in profit'),
         ('buy', '買盤', 'Demand', '誰在買、錢從哪裡來', 'Who is buying and where the money comes from', 'flows', None, None, None),
         ('lev', '槓桿', 'Leverage', '槓桿和情緒擠不擠', 'How crowded leverage and sentiment are', 'deriv', dict(v=dv['fund_hist']['value'], f='p1'), '資金費率（年化）', 'Funding rate (annualized)'),
         ('exit', '出場', 'Exit', '那我該怎麼做', 'So what do I do', 'exit', dict(v=ex['next_step_dist_pct'], f='pct1'), '離出場第一階', 'Distance to the first exit step')]
    qc = []
    for cid, zh, en_, qz, qe, mod, hs, hz, he in Q:
        m = MZ.get(mod) or {}; me = ME.get(mod) or {}; pz = m.get('points') or []; pe = me.get('points') or []
        c = dict(k='q_' + cid, zh=zh + '：' + qz, en=en_ + ': ' + qe, dz=m.get('lead') or '', de=me.get('lead') or m.get('lead') or '', go=cid, nofx=1,
                 list=dict(rows=[row(p, pe[i] if i < len(pe) else p, nv=1) for i, p in enumerate(pz)]))
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
    G = [dict(zh='六個問題各一句', en='The six questions, one line each', sz='每個問題今天的結論，點進去看證據', se="Today's verdict on each question; open the page for the evidence", charts=qc),
         dict(zh='今天要做什麼', en='What to do today', sz='行動、變化、接下來的日子', se='Actions, changes and dates ahead', charts=[c_act, c_chg, c_evt]),
         dict(zh='消息', en='News', sz='新聞、研報、今天的發現', se="News, research and today's findings", charts=[c_news, c_res, c_find, c_fol])]
    st = N.get('stance') or {}; ste = E.get('stance') or {}; W = N.get('watch') or []; WE = E.get('watch') or []
    brief = dict(edition=N.get('edition'), date=N.get('date'), hz=N.get('headline') or '', he=E.get('headline') or N.get('headline') or '', sz=N.get('summary') or '', se=E.get('summary') or N.get('summary') or '',
                 st=[st.get('label') or '', ste.get('label') or st.get('label') or '', st.get('tone') or 'neutral'], close=close, chg=L['price']['bar']['chg_pct'],
                 watch=[row(w.get('label') or '', en(WE, i, 'label', w.get('label') or ''), v=w.get('value'), f='usd0', nz=w.get('note') or '', ne=en(WE, i, 'note', w.get('note') or '')) for i, w in enumerate(W)])
    return G, brief
