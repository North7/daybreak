#!/usr/bin/env python3
"""籌碼搬家：近 7 天哪些價位的籌碼變厚、哪些變薄（2026-11-12 使用者要求）。

Bitview 的 URPD（全部供給，每 1,000 美元一格）今天和 7 天前各取一次，相減。
一顆幣最後一次在鏈上移動的價位，就是它在 URPD 的位置：幣一移動，原本那一格變薄、移動當時價位的那一格變厚。
變薄的幣依原本的成本分三類：
  成本高於這 7 天最高價：移動的時候是賠的；
  成本低於這 7 天最低價：移動的時候是賺的；
  成本落在這 7 天的價格範圍內：分不出來。
鏈上移動不一定是買賣（交易所整理錢包、換地址也算），逐筆 UTXO、沒有做實體歸併，所以只講「移動」，不講「賣出」。只作讀值。"""
import datetime as dt, time

URL = 'https://bitview.space/api/urpd/all/{}?agg=lin1000'
W = 1000


def _one(curl, date):
    j = curl(URL.format(date)); b = j.get('buckets') or {}
    if j.get('date') != date or not b.get('price') or not j.get('close'): raise RuntimeError(f'Bitview URPD all {date}：{str(j)[:120]}')
    return j['close'], {int(p): (s or 0) for p, s in zip(b['price'], b['supply'])}


def build(last, bars, curl=None, days=7):
    """last＝'YYYY-MM-DD'；bars＝[{d, h, l}]（日線，含這 7 天）。回傳 chips.urpd_chg；抓不到就丟錯（由呼叫的人記進 errors）"""
    if curl is None:
        import bitview; curl = bitview._curl
    prev = (dt.date.fromisoformat(last) - dt.timedelta(days=days)).isoformat()
    close, m1 = _one(curl, last); time.sleep(0.3); _, m0 = _one(curl, prev)
    wk = [b for b in bars if prev < b['d'] <= last]
    if len(wk) < days - 1: raise RuntimeError(f'urpd_chg：這 {days} 天的日線只有 {len(wk)} 根')
    hi, lo = max(b['h'] for b in wk), min(b['l'] for b in wk)
    D = {p: m1.get(p, 0) - m0.get(p, 0) for p in set(m0) | set(m1)}
    out = -sum(v for v in D.values() if v < 0); inn = sum(v for v in D.values() if v > 0)
    loss = -sum(v for p, v in D.items() if v < 0 and p >= hi)          # 整格都在這 7 天最高價之上
    gain = -sum(v for p, v in D.items() if v < 0 and p + W <= lo)      # 整格都在這 7 天最低價之下
    rows = [[p, round(D[p]), round(m1.get(p, 0))] for p in sorted(D) if close * .55 <= p <= close * 3]
    top = lambda sgn: [[p, round(v)] for p, v in sorted(D.items(), key=lambda x: -x[1] * sgn)[:3] if v * sgn > 0]
    near = [(m1.get(p, 0), p) for p in D if close * .95 <= p and p + W <= close * 1.05]
    thin, thick = (min(near), max(near)) if near else (None, None)
    return dict(date=last, prev=prev, days=days, width=W, close=round(close), hi=round(hi), lo=round(lo), rows=rows,
                moved_out=round(out), moved_in=round(inn), loss=round(loss), gain=round(gain), mid=round(out - loss - gain), up=top(1), dn=top(-1),
                thin=dict(p=thin[1], btc=round(thin[0])) if thin else None, thick=dict(p=thick[1], btc=round(thick[0])) if thick else None,
                src='Bitview', link='https://bitview.space',
                note='Bitview URPD 全部供給、每 1,000 美元一格，今天減 7 天前；鏈上移動不一定是買賣；只作讀值')
