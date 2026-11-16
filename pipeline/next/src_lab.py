# -*- coding: utf-8 -*-
"""卡片右上那一行的資料來源標籤（例：Coinalyze · 11/15）。
2026-11-17 舊版網站刪除前，這些標籤是從舊版面板抽出來的；這裡凍結了當時的寫法（src.json），{d} 每天換成資料日（meta.bar_date）。
快照時間、持倉日這類不是資料日的，在 dyn() 裡從 latest.json 算。卡片自己已經有 src 的（各頁 *_data.py 設的）不動。"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = json.load(open(os.path.join(HERE, 'src.json'), encoding='utf-8'))
def _md(d): return '%d/%d' % (int(d[5:7]), int(d[8:10]))
def _mdd(d): return d[5:10]   # '11-16'
def dyn(L):
    out = {}
    def put(k, f):
        try: out[k] = f()
        except Exception: pass
    fl, dv = L.get('flows') or {}, L.get('deriv') or {}
    put('stk', lambda: ('FRED · Kraken · %s' % _md(fl['btc_vs_stocks']['date']),) * 2)
    put('cot', lambda: ('CFTC · 每週 · %s 持倉' % _md(fl['cot']['date']), 'CFTC · weekly · positions as of %s' % _md(fl['cot']['date'])))
    put('ivt', lambda: ('Deribit 標記隱含波動 · 價平 · 快照 %s UTC' % dv['ivterm']['ts'], 'Deribit mark IV · at the money · snapshot %s UTC' % dv['ivterm']['ts']))
    put('liq', lambda: ('Coinalyze · %d 家交易所永續 · 快照 %s %s UTC' % (len(dv['liq_heat']['model']['exch']), _md(dv['liq_heat']['asof']), dv['liq_heat']['asof'][11:16]),
                        'Coinalyze · perpetuals on %d exchanges · snapshot %s %s UTC' % (len(dv['liq_heat']['model']['exch']), _md(dv['liq_heat']['asof']), dv['liq_heat']['asof'][11:16])))
    put('gex', lambda: ('Deribit · %s %s UTC' % (_mdd(dv['gex']['ts']), dv['gex']['ts'][11:16]),) * 2)
    put('book', lambda: ('%d 個交易所 · ±15%% · 快照 %s %s UTC' % (len(L['orderbook']['meta']) - 1, _mdd(L['orderbook']['ts']), L['orderbook']['ts'][11:16]),
                         '%d exchanges · ±15%% · snapshot %s %s UTC' % (len(L['orderbook']['meta']) - 1, _mdd(L['orderbook']['ts']), L['orderbook']['ts'][11:16])))
    def strike():
        s = dv['viz']['options']['strikes']; pc = dv['pcr']; px = L['price']['bar']['c']; mp = s['maxpain']
        c, p = pc['oi_call'] * px / 1e9, pc['oi_put'] * px / 1e9
        return ('%s · Max Pain %dK · 全部到期：買權 %.1fB／賣權 %.1fB 美元' % (_md(s['expiry']), round(mp / 1000), c, p), '%s · Max Pain %dK · all expiries: calls $%.1fB / puts $%.1fB' % (_md(s['expiry']), round(mp / 1000), c, p))
    put('strike', strike)
    put('path', lambda: ('每月底重估 · 下次 %s' % L['cycle']['model']['next_review'], 'Re-estimated at each month-end · next %s' % L['cycle']['model']['next_review']))
    return out
def apply(X, L):
    """X＝{圖代號: 卡片}；回傳補上的張數"""
    d = _md(L['meta']['bar_date']); D = dyn(L); n = 0
    for k, c in X.items():
        if c.get('src'): continue
        t = D.get(k) or SRC.get(k)
        if not t: continue
        c['src'], c['srce'] = t[0].replace('{d}', d), t[1].replace('{d}', d); n += 1
    return n
