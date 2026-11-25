# -*- coding: utf-8 -*-
"""「跟昨天比」（2026-11-25，讀者 @LegoLiew 建議：標出跟昨天比的變化，不只是水位；使用者說「做」）。
今天＝latest.json，昨天＝latest.prev.json（pipeline/build.py 換日前存的上一份）。兩份是同一天（判讀還沒提交、整期沿用上一份）就不出這張卡。
「平常算不算大」：今天的變化，和這個讀數過去一年每天的變化比排第幾。網站上的序列有的每 2–3 天一點，
那幾條用「k 天的變化 ÷ √k」當成一天的變化（隨機漫步的換算），只拿來分「很大／偏大／平常」三級，不當精確數字。"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))


def _rank(x, base):
    base = [abs(v) for v in base if v is not None]
    return round(sum(1 for v in base if v < abs(x)) / len(base) * 100) if base else None


def _steps(rows, col, n=365, pct=False):
    """rows＝[[日, …], …]；回傳最近 n 天裡每一段的變化換算成一天"""
    r = [x for x in rows if x[col] is not None]; t0 = r[-1][0] - n if r else 0; out = []
    for a, b in zip(r, r[1:]):
        if b[0] <= t0 or b[0] == a[0]: continue
        k = b[0] - a[0]; d = (b[col] / a[col] - 1) * 100 if pct else b[col] - a[col]
        if pct and not a[col]: continue
        out.append(d / math.sqrt(k))
    return out


def build(L):
    try: P = json.load(open(os.path.join(HERE, '..', '..', 'data', 'latest.prev.json'), encoding='utf-8'))
    except Exception: return None
    d0, d1 = P['meta']['bar_date'], L['meta']['bar_date']
    if d0 >= d1: return None
    g = lambda o, *ks: (lambda v: v)(__import__('functools').reduce(lambda a, k: (a or {}).get(k) if isinstance(a, dict) else None, ks, o))
    out = []
    def add(key, zh, en, y, t, base, unit, fz, fe, up, dn_, upe, dne, pct=False, p=None):
        if y is None or t is None: return
        ch = (t / y - 1) * 100 if pct else t - y
        p = _rank(ch, base) if p is None else p
        lvl = 2 if p is not None and p >= 90 else 1 if p is not None and p >= 70 else 0
        out.append(dict(k=key, zh=zh, en=en, y=y, t=t, ch=ch, p=p, lvl=lvl, unit=unit, fz=fz, fe=fe, mz=up if ch > 0 else dn_ if ch < 0 else '沒有變', me=upe if ch > 0 else dne if ch < 0 else 'unchanged', pct=pct))
    # 價格：全站統一收盤；日變化的基準用 chips.stress 的每日收盤
    S = L['chips']['stress']['rows']
    add('px', '收盤價', 'Close', P['price']['bar']['c'], L['price']['bar']['c'], _steps(S, 1, pct=True), '%', lambda v: '$' + format(round(v), ','), lambda v: '$' + format(round(v), ','),
        '上漲', '下跌', 'up', 'down', pct=True)
    # ETF：比的是當天的淨流量本身（流量就是變化），大小和近 60 個交易日的流量比
    E0 = [e for e in P['flows']['etf'] if not e.get('partial')]; E1 = [e for e in L['flows']['etf'] if not e.get('partial')]
    if E0 and E1 and E1[-1]['d'] > E0[-1]['d']:
        y, t = E0[-1]['musd'], E1[-1]['musd']; p = _rank(t, [e['musd'] for e in E1[-60:]])
        out.append(dict(k='etf', zh='現貨 ETF 淨流量', en='Spot ETF net flow', y=y, t=t, ch=t, p=p, lvl=2 if p >= 90 else 1 if p >= 70 else 0, unit='flow', flow=1,
                        mz='淨流入' if t > 0 else '淨流出', me='net inflow' if t > 0 else 'net outflow', d=E1[-1]['d']))
    f0, f1 = g(P, 'deriv', 'fund_hist'), g(L, 'deriv', 'fund_hist')
    if f0 and f1: add('fund', '資金費率（年化，7 日平均）', 'Funding (annualized, 7-day avg)', f0['value'], f1['value'], _steps(f1['rows'], 2), 'pt', lambda v: '%.2f%%' % v, lambda v: '%.2f%%' % v,
                      '多單付的費用變高，槓桿多頭變擠', '多頭槓桿降溫', 'longs paying more, leverage getting crowded', 'long leverage cooling')
    o0, o1 = g(P, 'deriv', 'oi_hist'), g(L, 'deriv', 'oi_hist')
    if o0 and o1: add('oi', '期貨未平倉', 'Futures open interest', o0['btc'], o1['btc'], _steps(o1['rows'], 2, pct=True), '%', lambda v: '%.1f 萬顆' % (v / 1e4), lambda v: '%sK BTC' % format(round(v / 1e3), ','),
                      '槓桿部位增加', '槓桿部位減少', 'more leveraged positions', 'leveraged positions shrinking', pct=True)
    c0, c1 = g(P, 'flows', 'cb_premium'), g(L, 'flows', 'cb_premium')
    if c0 and c1:
        v = [x[1] for x in c1['rows']]; a7 = [sum(v[i - 6:i + 1]) / 7 for i in range(6, len(v))]
        add('cbp', 'Coinbase 溢價（扣掉 USDT，7 日平均）', 'Coinbase premium (net of USDT, 7-day avg)', c0['avg7'], c1['avg7'], [b - a for a, b in zip(a7[-366:], a7[-365:])], 'pt', lambda v: '%+.3f%%' % v, lambda v: '%+.3f%%' % v,
            '美國買方比海外積極一點', '美國買方變弱', 'US buyers a little keener', 'US buyers weaker')
    s0, s1 = g(P, 'flows', 'stables'), g(L, 'flows', 'stables')
    if s0 and s1: add('stab', '穩定幣流通量', 'Stablecoin supply', s0['usd_b'], s1['usd_b'], _steps(s1['rows'], 1, pct=True), '%', lambda v: '%s 億美元' % format(round(v * 10), ','), lambda v: '$%.1fB' % v,
                      '場邊的美元變多', '場邊的美元變少', 'more dollars on the sidelines', 'fewer dollars on the sidelines', pct=True)
    q0, q1 = g(P, 'flows', 'fear_greed'), g(L, 'flows', 'fear_greed')
    if q0 and q1: add('fng', '恐懼貪婪指數', 'Fear & Greed', q0['value'], q1['value'], _steps(L['flows']['fng_hist']['rows'], 2), 'n', lambda v: '%d' % v, lambda v: '%d' % v,
                      '情緒回暖', '更恐懼', 'sentiment warming', 'more fearful')
    out.sort(key=lambda x: -(x['p'] or 0))
    return dict(d0=d0, d1=d1, rows=out)
