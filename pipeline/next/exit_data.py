# -*- coding: utf-8 -*-
"""「出場」這一頁的資料：頭部是離出場線多遠的跑道，下面是每條規則現在的距離、模擬器、觸發條件。site_data.py 會 import。"""

def build(L, N, E, dn, X):
    ex = L['exit']; st = ex['status']; fw = ex['framework']; close = st['close']; lad = fw['ladder']; per = fw['per_step_pct']
    row = lambda zh, en, v, **k: dict(zh=zh, en=en, v=v, **k)
    usd = lambda v: '$' + format(int(round(v)), ','); pc = lambda v: ('%+.1f%%' % ((v / close - 1) * 100)).replace('-', '−')
    p6 = st['p6']; mx = max(p6.values()); hit = len(st.get('steps_hit') or []); run = st['below_sma200_run']
    rows = [
      row('200 日避險線', '200-day hedge line', st['sma200'], f='usd0', bar=run / 5.0 * 100, mk=100, col='c4', nz='收盤在線的上方 %s。要連 5 天收在下面才減 20%%，現在連續 %d 天。' % (pc(st['sma200']).replace('−', '').replace('+', ''), run), ne='The close is %s above the line. It takes 5 straight closes below to cut 20%%; the count is %d.' % (pc(st['sma200']).replace('−', '').replace('+', ''), run)),
      row('MVRV ÷ 前一輪高點', 'MVRV ÷ prior-cycle peak', st['p20_ratio'], f='n3', bar=st['p20_ratio'] / .75 * 100, mk=100, col='c5', nz='到 0.75 是第一個鏈上賣點，換成價格大約是 %s，還差 %s。要連 5 天。' % (usd(st['k075_price']), pc(st['k075_price'])), ne='0.75 is the first on-chain sell, about %s in price terms, %s away. It needs 5 straight days.' % (usd(st['k075_price']), pc(st['k075_price']))),
      row('價格階梯的下一階', 'Next step on the price ladder', st['next_step'], f='usd0', bar=close / st['next_step'] * 100, mk=100, col='ac', nz='還差 %s。收盤碰到就賣 %g%%，已經賣了 %d 階。' % (pc(st['next_step']), per, hit), ne='%s away. A close at that level sells %g%%; %d steps sold so far.' % (pc(st['next_step']), per, hit)),
      row('頂部三指標裡最高的百分位', 'Highest percentile of the top three', mx, f='n0', bar=mx, mk=80, col='ac' if mx >= 80 else 'c5', nz='任兩項到 80 標為頂部區。只作讀值，不連動賣出。', ne='Any two at 80 mark the top zone. A reading only; no selling attached.'),
      row('時間停損', 'Time stop', '2029/10', ve='Oct 2029', nz=fw['time_stop'], ne=fw['time_stop_en'])]
    X['x_now'] = dict(k='x_now', zh='現在離每條規則多遠', en='Distance to each rule right now', nofx=1, hz='最近的一條是 200 日避險線，在收盤下方', he='The nearest is the 200-day hedge line, below the close', hs=dict(v=(st['sma200'] / close - 1) * 100, f='pct1'), list=dict(rows=rows),
      dz='每條規則現在的位置。橫條是離觸發多近，直線是觸發點。%s。' % fw['unit'], de='Where each rule stands now. The bar shows how close it is to firing; the tick is the trigger. %s.' % fw['unit_en'])
    X['x_sim'] = dict(k='x_sim', zh='出場模擬器', en='Exit simulator', nofx=1, sim=dict(ladder=lad, per=per, lo=60000, hi=240000, close=round(close)),
      dz='拖動價格，看價格階梯會賣掉多少。階梯一共 %d 階，每階 %g%%，從 %s 到 %s。鏈上觸發和避險是另外算的，不在這裡。' % (len(lad), per, usd(lad[0]), usd(lad[-1])), de='Drag the price to see how much the price ladder would sell. There are %d steps of %g%% each, from %s to %s. On-chain triggers and the hedge are separate and not included here.' % (len(lad), per, usd(lad[0]), usd(lad[-1])))
    oc = fw['onchain']; r075 = st.get('p20_run_075', 0); r080 = st.get('p20_run_080', 0)
    X['x_oc'] = dict(k='x_oc', zh='鏈上觸發', en='On-chain triggers', nofx=1, go='cycle', hz='MVRV ÷ 前一輪高點', he='MVRV ÷ prior-cycle peak', hs=dict(v=st['p20_ratio'], f='n3'),
      list=dict(rows=[row(o['rule'], o.get('rule_en') or o['rule'], ('連續 %d 天' % (r075 if o.get('k') == .75 else r080)) if o.get('k') else '還沒啟用', ve=('%d days' % (r075 if o.get('k') == .75 else r080)) if o.get('k') else 'Not active', col='c5') for o in oc]),
      dz='三條和價格無關、看鏈上估值的賣點。走勢圖在「週期」那一頁的頂部訊號。', de='Three sell rules that follow on-chain valuation rather than price. The chart is on the Cycle page under top signals.')
    hg = fw['hedge']
    X['x_other'] = dict(k='x_other', zh='其他規則', en='Other rules', nofx=1,
      list=dict(rows=[row('200 日避險', '200-day hedge', '減 %d%%' % hg['pct'], ve='Cut %d%%' % hg['pct'], col='c4', nz=hg['rule'], ne=hg['rule_en']), row('頂部三指標', 'Top three indicators', '只作讀值', ve='Reading only', nz=fw['top3'], ne=fw['top3_en']), row('時間停損', 'Time stop', '2029/10', ve='Oct 2029', nz=fw['time_stop'], ne=fw['time_stop_en'])]),
      dz='價格階梯和鏈上觸發以外的三條。%s' % fw['name'], de='The three rules besides the price ladder and the on-chain triggers. %s' % fw['name'])
    G = [dict(zh='現在的位置', en='Where things stand', sz='每條規則離觸發多遠，價格到哪裡會賣多少', se='How far each rule is from firing, and how much sells at what price', charts=[X['x_now'], X['x_sim']]),
         dict(zh='觸發條件', en='The rules', sz='鏈上的賣點、避險、時間停損', se='On-chain sells, the hedge and the time stop', charts=[X['x_oc'], X['x_other']])]
    runway = dict(close=round(close), sma200=round(st['sma200']), k075=st['k075_price'], k080=st['k080_price'], ladder=lad, per=per, dist=st['next_step_dist_pct'], hit=hit)
    return G, runway
