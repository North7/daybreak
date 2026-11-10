# -*- coding: utf-8 -*-
"""價位地圖原型的資料：所有「某個價位有什麼」的東西放到同一條價格軸。build.py 會 import。"""
import base64

def build(L):
    px = L['price']['bar']['c']; lv = L['cycle']['levels']['levels']; q = L['onchain']['quant']['cur']; ma = L['price']['ma']; ex = L['exit']
    vp = L['price'].get('volprofile') or {}; op = L['deriv']['viz']['options']; g = L['deriv']['gex']; lh = L['deriv']['liq_heat']; ob = L['orderbook']; co = L['chips']['cohort']
    NM = dict(act='活躍投資人成本', tmm='真實市場均價', sma365='365 日均線', sth='短期持有者成本', w50='50 週均線', sma200='200 日均線', rp='實現價', lth='長期持有者成本')
    LC = dict(act='ac', tmm='c4', sma365='c5', sth='ac', w50='ink', sma200='c3', rp='k2', lth='k2')   # 和「成本線與均線」那張圖同色
    QC = {'45': 'c3', '50': 'color-mix(in srgb, var(--c3) 50%, var(--c4))', '55': 'c4', '60': 'up', '65': 'c5', '75': 'color-mix(in srgb, var(--c5) 45%, var(--ac))', '85': 'ac'}
    lines = [[x['value'], NM[x['key']], 'ma' if x['key'] in ('sma365', 'sma200', 'w50') else 'cost', LC[x['key']]] for x in lv if x['key'] in NM]
    lines += [[round(ma['sma20']), '20 日均線', 'ma', 'ac'], [round(ma['sma50']), '50 日均線', 'ma', 'ink']]
    lines += [[v, '成本分位 %s%%' % k, 'q', QC[str(k)]] for k, v in q.items() if str(k) in QC]
    if vp: lines += [[vp['poc'], '20 日成交最密', 'vp', 'k2'], [vp['va_high_outer'], '20 日價值區上緣', 'vp', 'dn']]
    lines += [[op['strikes']['maxpain'], '選擇權最大痛點', 'opt']]
    st = ex['status']
    lines += [[st['k075_price'], 'MVRV ÷ 前高 0.75', 'exit'], [st['k080_price'], 'MVRV ÷ 前高 0.80', 'exit']] + [[v, '出場階梯 %d' % (i + 1), 'exit'] for i, v in enumerate(ex['framework']['ladder'])]
    b = base64.b64decode(lh['heat']); nb = lh['nb']; last = b[-nb:]
    liq = [[lh['lo'] + i * lh['step'], sum(last[i:i + 5])] for i in range(0, nb, 5)]
    return dict(px=round(px), lines=lines,
                urpd=dict(w=co['width'], rows=[[r[0], round(r[1]), round(r[2])] for r in co['rows']]),
                opt=dict(exp=op['strikes']['expiry'], rows=op['strikes']['rows']),
                gex=[[r[0], r[2]] for r in g['rows']],
                liq=dict(step=lh['step'] * 5, rows=liq),
                book=dict(step=ob['wide']['step'], rows=[[r[0], r[1], round(sum(r[2]), 1)] for r in ob['wide']['rows']]))
