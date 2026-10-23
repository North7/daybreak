"""異動偵測（2026-10-23 使用者要求：日報要有「發現」——特殊異動、關鍵節點、主要變化，不只是放數據）。
build.py 組好 latest.json 之後呼叫 build(L, prev, notes)，輸出 L['signals']；brief.py 把它放在最前面給每日任務讀。
只用網站上已經有的序列（每個異動都能連到一張圖），規則寫死、可重算：
  extreme  單一序列落在近一年最高或最低 2%（依序列各自之前 365 天排名）
  jump     7 日變化落在近一年 7 日變化的最高或最低 2%
  cross    狀態翻轉（和上一期 latest.json 比）：價格穿過 200 日均線或短期持有者成本、資金費率翻正負、IV−RV 翻正負、SOPR 穿過 1 …
  level    靠近關鍵價位（±3%）、收盤一年新高／新低、離出場第一階或 MVRV 0.75 線 5% 以內
  streak   連續：ETF 同方向連 5 個交易日以上、SOPR 連 5 天低於 1
  combo    跨指標組合（趁跌獲利了結、集中認賠、軋空、槓桿追價、波動壓縮、資金與價格背離）與同一主題 3 項以上同時異動
每個異動附：資料日期、上一次同樣極端是哪天（「N 天來最高」）、過去幾次同樣情況與之後 30 天的價格變化（附樣本數，只給每日任務當背景，網站不顯示）。
另外檢查上一期 notes.json 的 findings／followups 寫下的追蹤條件（check），自動算出成立與否，給下一期回顧用。
只作讀值：不連動任何規則，也不是買賣訊號。"""
import datetime as dt, statistics as stx

EP = dt.date(1970, 1, 1)
dn = lambda s: (dt.date.fromisoformat(s[:10]) - EP).days
ds = lambda x: (EP + dt.timedelta(days=int(x))).isoformat()
md = lambda x: ds(x)[5:].replace('-', '/')
EXT, JMP, CMB = 98, 98, 95          # 極端值、7 日變化、組合規則的百分位門檻
NEAR, NEAR_EXIT = 3.0, 5.0          # 靠近關鍵價位、出場線的距離（%）
MIN_N, WIN = 120, 365               # 排名至少要有的點數、排名視窗（天）
TOP = 10                            # 網站與 brief 只列分數最高的幾個
THEME = {'price': ('價格', 'Price'), 'vol': ('波動與衍生品', 'Volatility & derivatives'), 'holders': ('持有者行為', 'Holder behavior'),
         'flows': ('資金', 'Flows'), 'cycle': ('週期', 'Cycle')}


def g(o, path, d=None):
    for k in path.split('.'):
        if isinstance(o, dict) and k in o: o = o[k]
        elif isinstance(o, list) and k.lstrip('-').isdigit() and -len(o) <= int(k) < len(o): o = o[int(k)]
        else: return d
    return o


def T(zh, en): return {'zh': zh, 'en': en}


def Z(zh): return zh + ' ' if zh[-1:].isascii() else zh   # 中文名以英數結尾時，後面接中文要空一格


def F(v, f, lang):
    """數字格式（中英共用，只有單位不同）。"""
    if v is None: return '—'
    if f == 'usd': return '$' + format(round(v), ',')
    if f == 'musd': return ('+' if v >= 0 else '−') + '$' + (format(abs(v) / 1e3, ',.2f') + 'B' if abs(v) >= 1000 else format(abs(v), ',.0f') + 'M')
    if f == 'busd': return '$' + format(v, ',.1f') + 'B'
    if f == 'btc': return format(round(v), ',') + (' 顆' if lang == 'zh' else ' BTC')
    if f == 'pct': return format(v, ',.2f') + '%'
    if f == 'spct': return ('+' if v >= 0 else '−') + format(abs(v), ',.2f') + '%'
    if f == 'int': return format(round(v), ',')
    return format(v, ',.' + str(f) + 'f') if isinstance(f, int) else str(v)


# ---------- 序列目錄：(key, 中文名, 英文名, 主題, 版面, 圖表 id, 取值, 格式, 規則, 7 日變化算法, 附註) ----------
def _rows(L, path, i=1):
    return [(r[0], r[i]) for r in (g(L, path) or []) if r[i] is not None]


def _ratio_rows(L):
    return [(r[0], r[1] / r[2]) for r in (g(L, 'onchain.sth_pnl.rows') or []) if r[1] is not None and r[2]]


def _ivrv(L):
    return [(r[0], r[1] - r[2]) for r in (g(L, 'deriv.viz.vol.rows') or []) if r[1] is not None and r[2] is not None]


def _ma7(rows):
    return [(rows[i][0], sum(v for _, v in rows[i - 6:i + 1]) / 7) for i in range(6, len(rows))]


SM = T('CheckOnChain 已平滑，單日大額轉帳也會被算成賣出', 'smoothed by CheckOnChain; a single large transfer can show up as selling')
SERIES = [
    ('price', '收盤價', 'Close', 'price', 'overview', 'ov-px', lambda L: _rows(L, 'chips.viz.sopr.rows', 2), 'usd', 'j', 'rel', None),
    ('dvol', 'DVOL（隱含波動）', 'DVOL (implied vol)', 'vol', 'deriv', 'vol', lambda L: _rows(L, 'deriv.viz.vol.rows', 1), 1, 'ej', 'diff', None),
    ('rv30', 'RV30（實際波動）', 'RV30 (realized vol)', 'vol', 'deriv', 'vol', lambda L: _rows(L, 'deriv.viz.vol.rows', 2), 1, 'ej', 'diff', None),
    ('ivrv', 'IV − RV30', 'IV − RV30', 'vol', 'deriv', 'vol', _ivrv, 1, 'ej', 'diff', None),
    ('sth-sopr', '短期持有者 SOPR', 'STH-SOPR', 'holders', 'onchain', 'sopr', lambda L: _rows(L, 'chips.viz.sopr.rows', 1), 4, 'ej', 'diff', T('日線，盤中集中認賠會被同一天的獲利賣出平均掉', 'daily; intraday capitulation gets averaged with same-day profit taking')),
    ('sth-profit', '短期持有者實現獲利', 'STH realized profit', 'holders', 'onchain', 'sthpnl', lambda L: _rows(L, 'onchain.sth_pnl.rows', 1), 'btc', 'ej', 'rel', SM),
    ('sth-loss', '短期持有者實現虧損', 'STH realized loss', 'holders', 'onchain', 'sthpnl', lambda L: _rows(L, 'onchain.sth_pnl.rows', 2), 'btc', 'ej', 'rel', SM),
    ('sth-plr', '短期持有者獲利 ÷ 虧損', 'STH profit ÷ loss', 'holders', 'onchain', 'sthpnl', _ratio_rows, 2, 'ej', 'rel', SM),
    ('npl', '每日淨實現損益', 'Daily net realized P/L', 'holders', 'onchain', 'npl', lambda L: _rows(L, 'onchain.npl.rows', 2), 'musd', 'e', None, None),
    ('npl-cum30', '30 日累計淨實現損益（占市值）', '30-day net realized P/L (% of market cap)', 'holders', 'onchain', 'npl', lambda L: _rows(L, 'onchain.npl.cum30.rows', 2), 'spct', 'e4', None, None),
    ('sth-in-profit', '短期持有者獲利比例', 'STH supply in profit', 'holders', 'onchain', 'profit', lambda L: [(r[0], r[1]) for r in g(L, 'chips.viz.profit') or []], 'pct', 'ej', 'diff', None),
    ('sth-lth', '短期 ÷ 長期持有者供給', 'STH ÷ LTH supply', 'holders', 'onchain', 'cost', lambda L: [(r[0], r[1]) for r in g(L, 'chips.viz.ratio') or []], 4, 'j', 'diff', None),
    ('cbp', 'Coinbase 溢價（7 日均）', 'Coinbase premium (7-day avg)', 'flows', 'flows', 'cbp', lambda L: _ma7(_rows(L, 'flows.cb_premium.rows', 1)), 3, 'ej', 'diff', None),
    ('stables', '穩定幣供給', 'Stablecoin supply', 'flows', 'flows', 'stab', lambda L: _rows(L, 'flows.stables.rows', 1), 'busd', 'j', 'rel', None),
    ('rcliq', '實現市值 30 日變化', 'Realized cap 30-day change', 'flows', 'flows', 'rcliq', lambda L: _rows(L, 'flows.rc_liq.rows', 1), 'spct', 'ej', 'diff', None),
    ('p20', 'MVRV ÷ 前一輪高點', 'MVRV ÷ prior cycle peak', 'cycle', 'cycle', 'p20', lambda L: _rows(L, 'cycle.p20.rows', 1), 3, 'j', 'diff', None),
] + [('oc-' + k, zh, en, th, 'onchain', 'oc-' + k, (lambda k: lambda L: _rows(L, 'onchain.viz.' + k + '.rows', 1))(k), f, rule, chg, None) for k, zh, en, th, f, rule, chg in (
    ('mvrv-zscore', 'MVRV Z', 'MVRV Z', 'cycle', 2, 'ej', 'diff'), ('nupl', 'NUPL', 'NUPL', 'cycle', 3, 'ej', 'diff'), ('puell-multiple', 'Puell 倍數', 'Puell multiple', 'cycle', 2, 'ej', 'diff'),
    ('asopr', 'aSOPR（7 日均）', 'aSOPR (7-day avg)', 'holders', 4, 'ej', 'diff'), ('lth-sopr', '長期持有者 SOPR（7 日均）', 'LTH-SOPR (7-day avg)', 'holders', 3, 'ej', 'diff'),
    ('illiquid-supply', '非流動供給', 'Illiquid supply', 'holders', 'int', 'j', 'rel'), ('highly-liquid-supply', '高流動供給', 'Highly liquid supply', 'holders', 'int', 'j', 'rel'),
    ('lth-mvrv-zscore', '長期持有者 MVRV Z', 'LTH MVRV Z', 'cycle', 2, 'ej', 'diff'), ('supply-in-profit-pct', '獲利供給比例', 'Supply in profit', 'cycle', 'pct', 'ej', 'diff'),
    ('lth-net-position-change-30d-btc', '長期持有者 30 日淨部位', 'LTH 30-day net position', 'holders', 'int', 'ej', 'diff'))]


# ---------- 工具 ----------
def _at(rows, x, tol=4):
    """rows 裡 x 當天或之前最近的一點（相差 tol 天內）。"""
    best = None
    for d, v in rows:
        if d > x: break
        best = (d, v)
    return best if best and x - best[0] <= tol else None


def _rank(rows, i, win=WIN):
    """第 i 點在它之前 win 天內的百分位（同值算一半）；點數不夠回傳 None。"""
    x, v = rows[i]; h = [w for d, w in rows[:i] if d >= x - win]
    if len(h) < MIN_N: return None
    return (sum(w < v for w in h) + 0.5 * sum(w == v for w in h)) / len(h) * 100


def _chg(rows, i, how, days=7):
    p = _at(rows[:i], rows[i][0] - days, tol=3)
    if not p: return None
    return (rows[i][1] / p[1] - 1) * 100 if how == 'rel' and p[1] else rows[i][1] - p[1]


def _chg_rows(rows, how):
    return [(rows[i][0], c) for i in range(len(rows)) for c in [_chg(rows, i, how)] if c is not None]


def _px_map(L):
    """價格查表：每日（近一年）優先，其次每 3 天（近 3 年），再其次每 7 天（2012 起）。"""
    m = {}
    for path, i in (('price.history', 1), ('cycle.stage.viz.px', 1), ('chips.viz.sopr.rows', 2), ('onchain.sth_pnl.rows', 3)):
        for r in g(L, path) or []:
            if r[i]: m[r[0]] = r[i]
    c, bd = g(L, 'price.bar.c'), g(L, 'meta.bar_date')   # 收盤當天：CoinMetrics 序列還沒有，用 Kraken 收盤補上
    if c and bd: m.setdefault(dn(bd), c)
    return sorted(m.items())


def _fwd(px, x, days=30):
    a, b = _at(px, x, 7), _at(px, x + days, 7)
    return round((b[1] / a[1] - 1) * 100, 1) if a and b and b[0] > a[0] else None


def _episodes(rows, cond, gap=14):
    """符合 cond(i) 的日子，相隔超過 gap 天才算新的一次；回傳每次的第一天索引。"""
    out, last = [], None
    for i in range(len(rows)):
        if cond(i):
            if last is None or rows[i][0] - rows[last][0] > gap: out.append(i)
            last = i
    return out


def _history(rows, cond, px, cur_i):
    """過去同樣情況（不含這一次）的日期、數值與之後 30 天價格變化；外加同一段期間每天的 30 天變化中位數當基準。"""
    eps = [i for i in _episodes(rows, cond) if rows[cur_i][0] - rows[i][0] > 14]
    past = [dict(d=ds(rows[i][0]), v=round(rows[i][1], 4), fwd30=_fwd(px, rows[i][0])) for i in eps]
    f = [p['fwd30'] for p in past if p['fwd30'] is not None]
    base = [c for c in (_fwd(px, d) for d, _ in rows[::3] if d <= rows[cur_i][0] - 30) if c is not None]
    return dict(n=len(past), last=past[-5:], fwd30_med=round(stx.median(f), 1) if f else None, base30_med=round(stx.median(base), 1) if base else None,
                since=ds(rows[0][0]))


def _since(rows, i, up):
    """上一次至少這麼極端是哪天（往前找整段序列）。"""
    v = rows[i][1]
    for d, w in reversed(rows[:i]):
        if (w >= v if up else w <= v): return d
    return None


# ---------- 單一序列：極端值、7 日變化 ----------
def _single(L, bar, px):
    out = []
    for key, zh, en, th, page, chart, get, f, rule, how, cav in SERIES:
        try: rows = sorted(get(L))
        except Exception: continue
        if len(rows) < MIN_N + 1: continue
        i = len(rows) - 1; x, v = rows[i]
        if bar - x > 10: continue   # 太舊的序列不判斷
        win = 1461 if '4' in rule else WIN
        name = T(zh, en); best = None
        if 'e' in rule:
            r = _rank(rows, i, win)
            if r is not None and (r >= EXT or r <= 100 - EXT):
                up = r >= EXT; sd = _since(rows, i, up)
                cond = lambda k, up=up: (lambda q: q is not None and (q >= EXT if up else q <= 100 - EXT))(_rank(rows, k, win))
                yr = '四年' if win > WIN else '一年'; yre = '4-year' if win > WIN else '1-year'
                best = dict(id=f'extreme:{key}:{"hi" if up else "lo"}', kind='extreme', key=key, dir='up' if up else 'down', theme=th, page=page, chart=chart,
                            date=ds(x), x=x, value=round(v, 4), pct=round(r, 1), score=2 + abs(r - 50) / 25,
                            title=T(f'{Z(zh)}到近{yr}{"最高" if up else "最低"}的 2%', f'{en} at a {yre} {"high" if up else "low"} (top 2%)' if up else f'{en} at a {yre} low (bottom 2%)'),
                            fig=T(f'{F(v, f, "zh")}（{md(x)}），近{yr}第 {r:.1f} 百分位', f'{F(v, f, "en")} ({md(x)}), {yre} percentile {r:.1f}'),
                            ctx=_since_txt(sd, x, rows, up, f), hist=_history(rows, cond, px, i), caveat=cav)
        if 'j' in rule and how:
            cr = _chg_rows(rows, how)
            if len(cr) > MIN_N and cr[-1][0] == x:
                k = len(cr) - 1; r = _rank(cr, k)
                if r is not None and (r >= JMP or r <= 100 - JMP) and (best is None or abs(r - 50) / 25 + 1.5 > best['score']):
                    up = r >= JMP; c = cr[k][1]; p0 = _at(rows[:i], x - 7, 3)
                    cond = lambda kk, up=up: (lambda q: q is not None and (q >= JMP if up else q <= 100 - JMP))(_rank(cr, kk))
                    cz = F(c, 'spct', 'zh') if how == 'rel' else ('+' if c >= 0 else '−') + F(abs(c), f, 'zh')
                    ce = F(c, 'spct', 'en') if how == 'rel' else ('+' if c >= 0 else '−') + F(abs(c), f, 'en')
                    best = dict(id=f'jump:{key}:{"up" if up else "down"}', kind='jump', key=key, dir='up' if up else 'down', theme=th, page=page, chart=chart,
                                date=ds(x), x=x, value=round(v, 4), chg=round(c, 4), pct=round(r, 1), score=1.5 + abs(r - 50) / 25,
                                title=T(f'{zh} 7 日{"急升" if up else "急降"}', f'{en}: sharp 7-day {"rise" if up else "drop"}'),
                                fig=T(f'{F(p0[1], f, "zh")} → {F(v, f, "zh")}（{cz}，{md(x)}）；7 日變化在近一年第 {r:.1f} 百分位', f'{F(p0[1], f, "en")} → {F(v, f, "en")} ({ce}, {md(x)}); 7-day change at 1-year percentile {r:.1f}'),
                                ctx=None, hist=_history(cr, cond, px, k), caveat=cav)
        if best: out.append(best)
    return out


def _since_txt(sd, x, rows, up, f):
    if sd is None: return T(f'整段資料（{ds(rows[0][0])[:7]} 起）{"最高" if up else "最低"}', f'{"Highest" if up else "Lowest"} in the whole series (since {ds(rows[0][0])[:7]})')
    w = dict(rows)[sd]
    return T(f'{x - sd} 天來{"最高" if up else "最低"}（上次 {ds(sd).replace("-", "/")}，{F(w, f, "zh")}）', f'{"Highest" if up else "Lowest"} in {x - sd} days (last {ds(sd).replace("-", "/")}, {F(w, f, "en")})')


# ---------- 狀態翻轉（和上一期比） ----------
def states(L):
    c = g(L, 'price.bar.c'); s = {}
    put = lambda k, v: s.__setitem__(k, v) if v is not None else None
    sma, sth, tmm = g(L, 'price.ma.sma200'), g(L, 'onchain.metrics.sth-realized-price.value'), g(L, 'chips.flow.sth_vs_tmm.tmm')
    if c and sma: put('above_sma200', c > sma)
    if c and sth: put('above_sth_cost', c > sth)
    if c and tmm: put('above_tmm', c > tmm)
    fw = g(L, 'deriv.funding_multi.weighted_now'); put('funding_pos', None if fw is None else fw > 0)
    iv = g(L, 'deriv.samesource.iv_minus_rv30'); put('iv_gt_rv', None if iv is None else iv > 0)
    rr = g(L, 'deriv.rr25.rr'); put('rr_pos', None if rr is None else rr > 0)
    so = g(L, 'chips.viz.sopr.value'); put('sopr_ge1', None if so is None else so >= 1)
    n7 = g(L, 'onchain.npl.sum7_usd_m'); put('npl7_pos', None if n7 is None else n7 > 0)
    rc = g(L, 'flows.rc_liq.chg30_pct'); put('rcliq_pos', None if rc is None else rc > 0)
    cb = g(L, 'flows.cb_premium.avg7'); put('cbp_pos', None if cb is None else cb > 0)
    put('hash_cap', g(L, 'onchain.hash_ribbons.capitulation'))
    fg = g(L, 'flows.fear_greed.value'); put('fg_zone', None if fg is None else 'xfear' if fg < 25 else 'xgreed' if fg > 75 else 'mid')
    put('stage', g(L, 'cycle.stage.stage'))
    for it in g(L, 'cycle.stage.evidence.items') or []: put('light_' + it['id'], bool(it.get('ok')))
    for k in ('top', 'bottom'):
        sg = g(L, f'cycle.tidemark.{k}.signal'); put('tm_' + k, None if sg is None else sg >= 50)
    p6 = g(L, 'exit.status.p6') or {}
    if p6: put('top_zone', sum((p6.get(k) or 0) >= 80 for k in ('mvrv_z', 'nupl', 'puell')) >= 2)
    return s


# (狀態, 主題, 版面, 圖表, 成立時的中英標題, 不成立時的中英標題)
FLIP = {
    'above_sma200': ('price', 'market', 'ov-px', T('收盤站回 200 日均線之上', 'Close back above the 200-day average'), T('收盤跌破 200 日均線', 'Close fell below the 200-day average')),
    'above_sth_cost': ('holders', 'onchain', 'cost', T('價格站上短期持有者成本', 'Price above short-term holder cost basis'), T('價格跌破短期持有者成本', 'Price below short-term holder cost basis')),
    'above_tmm': ('holders', 'onchain', 'cost', T('價格站上真實市場均價', 'Price above the true market mean'), T('價格跌破真實市場均價', 'Price below the true market mean')),
    'funding_pos': ('vol', 'deriv', None, T('加權資金費率翻正（多方付費）', 'Weighted funding turned positive (longs pay)'), T('加權資金費率翻負（空方付費）', 'Weighted funding turned negative (shorts pay)')),
    'iv_gt_rv': ('vol', 'deriv', 'vol', T('隱含波動回到實際波動之上', 'Implied vol back above realized'), T('隱含波動跌到實際波動之下', 'Implied vol fell below realized')),
    'rr_pos': ('vol', 'deriv', None, T('25Δ 風險逆轉翻正（買權較貴）', '25Δ risk reversal turned positive (calls richer)'), T('25Δ 風險逆轉翻負（賣權較貴）', '25Δ risk reversal turned negative (puts richer)')),
    'sopr_ge1': ('holders', 'onchain', 'sopr', T('短期持有者 SOPR 回到 1 之上', 'STH-SOPR back above 1'), T('短期持有者 SOPR 跌破 1（轉為賠錢賣）', 'STH-SOPR fell below 1 (selling at a loss)')),
    'npl7_pos': ('holders', 'onchain', 'npl', T('近 7 日淨實現損益轉為淨獲利', '7-day net realized P/L turned to net profit'), T('近 7 日淨實現損益轉為淨認賠', '7-day net realized P/L turned to net loss')),
    'rcliq_pos': ('flows', 'flows', 'rcliq', T('實現市值 30 日變化轉正（資金回流）', 'Realized cap 30-day change turned positive'), T('實現市值 30 日變化轉負（資金流出）', 'Realized cap 30-day change turned negative')),
    'cbp_pos': ('flows', 'flows', 'cbp', T('Coinbase 溢價 7 日均轉正', 'Coinbase premium 7-day average turned positive'), T('Coinbase 溢價 7 日均轉負', 'Coinbase premium 7-day average turned negative')),
    'hash_cap': ('cycle', 'onchain', None, T('算力帶進入礦工投降', 'Hash Ribbons: miner capitulation started'), T('算力帶脫離礦工投降', 'Hash Ribbons: miner capitulation ended')),
    'tm_top': ('cycle', 'cycle', None, T('Tidemark 頂部訊號站上 50', 'Tidemark top signal at or above 50'), T('Tidemark 頂部訊號跌回 50 之下', 'Tidemark top signal back below 50')),
    'tm_bottom': ('cycle', 'cycle', None, T('Tidemark 底部訊號站上 50', 'Tidemark bottom signal at or above 50'), T('Tidemark 底部訊號跌回 50 之下', 'Tidemark bottom signal back below 50')),
    'top_zone': ('cycle', 'cycle', None, T('頂部三指標進入頂部區（任兩項 ≥ 80）', 'Top-3 indicators entered the top zone (any two ≥ 80)'), T('頂部三指標離開頂部區', 'Top-3 indicators left the top zone')),
}


def _flips(L, prev):
    if not prev: return []
    a, b = states(prev), states(L); out = []
    for k, now in b.items():
        was = a.get(k)
        if was is None or was == now: continue
        if k == 'stage':
            out.append(dict(id='cross:stage', kind='cross', key=k, dir='flat', theme='cycle', page='cycle', chart=None, score=6,
                            title=T(f'市場階段：{was} → {now}', f'Market stage: {was} → {now}'), fig=T('依寫死規則判定（P23）', 'set by fixed rules (P23)'))); continue
        if k == 'fg_zone':
            fz = {'xfear': ('極度恐懼', 'extreme fear'), 'xgreed': ('極度貪婪', 'extreme greed'), 'mid': ('一般區間', 'the middle range')}
            out.append(dict(id=f'cross:fg:{now}', kind='cross', key=k, dir='flat', theme='flows', page='flows', chart=None, score=2.5,
                            title=T(f'恐懼貪婪進入{fz[now][0]}', f'Fear & Greed moved into {fz[now][1]}'), fig=T(f'指數 {g(L, "flows.fear_greed.value")}', f'index {g(L, "flows.fear_greed.value")}'))); continue
        if k.startswith('light_'):
            it = next((x for x in g(L, 'cycle.stage.evidence.items') or [] if 'light_' + x['id'] == k), {})
            out.append(dict(id=f'cross:{k}:{"on" if now else "off"}', kind='cross', key=k, dir='up' if now else 'down', theme='cycle', page='cycle', chart='ev-' + it.get('id', ''), score=3,
                            title=T(f'佐證燈號「{it.get("label", k)}」{"亮起" if now else "熄滅"}', f'Supporting light "{it.get("id", k)}" turned {"on" if now else "off"}'),
                            fig=T(f'條件：{it.get("cond", "")}；現值 {it.get("value")}', f'condition: {it.get("cond", "")}; now {it.get("value")}'))); continue
        th, page, chart, on, off = FLIP[k]
        out.append(dict(id=f'cross:{k}:{"on" if now else "off"}', kind='cross', key=k, dir='up' if now else 'down', theme=th, page=page, chart=chart,
                        score=4 if k in ('above_sma200', 'above_sth_cost', 'sopr_ge1', 'top_zone', 'hash_cap') else 3, title=on if now else off, fig=_flip_fig(k, L, prev)))
    return out


def _flip_fig(k, L, prev):
    c, c0 = g(L, 'price.bar.c'), g(prev, 'price.bar.c')
    ref = {'above_sma200': 'price.ma.sma200', 'above_sth_cost': 'onchain.metrics.sth-realized-price.value', 'above_tmm': 'chips.flow.sth_vs_tmm.tmm'}.get(k)
    if ref: return T(f'收盤 {F(c0, "usd", "zh")} → {F(c, "usd", "zh")}，線在 {F(g(L, ref), "usd", "zh")}', f'close {F(c0, "usd", "en")} → {F(c, "usd", "en")}; line at {F(g(L, ref), "usd", "en")}')
    path = {'funding_pos': ('deriv.funding_multi.weighted_now', 'spct'), 'iv_gt_rv': ('deriv.samesource.iv_minus_rv30', 2), 'rr_pos': ('deriv.rr25.rr', 2),
            'sopr_ge1': ('chips.viz.sopr.value', 4), 'npl7_pos': ('onchain.npl.sum7_usd_m', 'musd'), 'rcliq_pos': ('flows.rc_liq.chg30_pct', 'spct'),
            'cbp_pos': ('flows.cb_premium.avg7', 3), 'tm_top': ('cycle.tidemark.top.signal', 0), 'tm_bottom': ('cycle.tidemark.bottom.signal', 0)}.get(k)
    if not path: return T('', '')
    a, b = g(prev, path[0]), g(L, path[0])
    return T(f'{F(a, path[1], "zh")} → {F(b, path[1], "zh")}', f'{F(a, path[1], "en")} → {F(b, path[1], "en")}')


# ---------- 關鍵價位、新高新低 ----------
def _levels(L, bar):
    c = g(L, 'price.bar.c'); out = []
    if not c: return out
    for key, path, zh, en, th, page, chart in (('sma200', 'price.ma.sma200', '200 日均線', '200-day average', 'price', 'market', 'ov-px'),
                                              ('sth-cost', 'onchain.metrics.sth-realized-price.value', '短期持有者成本', 'short-term holder cost basis', 'holders', 'onchain', 'cost'),
                                              ('tmm', 'chips.flow.sth_vs_tmm.tmm', '真實市場均價', 'true market mean', 'holders', 'onchain', 'cost')):
        v = g(L, path)
        if not v: continue
        d = (c / v - 1) * 100
        if abs(d) <= NEAR:
            out.append(dict(id=f'level:{key}', kind='level', key=key, dir='up' if d >= 0 else 'down', theme=th, page=page, chart=chart, score=3 + (NEAR - abs(d)) / NEAR, value=round(v), dist_pct=round(d, 2),
                            title=T(f'價格貼近{zh}（{F(d, "spct", "zh")}）', f'Price near the {en} ({F(d, "spct", "en")})'),
                            fig=T(f'收盤 {F(c, "usd", "zh")}，{zh} {F(v, "usd", "zh")}', f'close {F(c, "usd", "en")}; {en} {F(v, "usd", "en")}')))
    for key, path, dpath, zh, en in (('exit-step', 'exit.status.next_step', 'exit.status.next_step_dist_pct', '出場第一階', 'the first exit step'),
                                     ('k075', 'exit.status.k075_price', None, 'MVRV 0.75 線', 'the MVRV 0.75 line')):
        v = g(L, path); d = g(L, dpath) if dpath else ((v / c - 1) * 100 if v else None)
        if v and d is not None and 0 <= d <= NEAR_EXIT:
            out.append(dict(id=f'level:{key}', kind='level', key=key, dir='up', theme='cycle', page='exit', chart=None, score=5, value=round(v), dist_pct=round(d, 2),
                            title=T(f'離{zh}只剩 {d:.1f}%', f'Only {d:.1f}% from {en}'), fig=T(f'{zh} {F(v, "usd", "zh")}', f'{en} {F(v, "usd", "en")}')))
    px = _rows(L, 'chips.viz.sopr.rows', 2)
    h = [v for x, v in px if bar - WIN <= x < bar]
    if len(h) > MIN_N and (c > max(h) or c < min(h)):
        up = c > max(h); sd = next((x for x, v in reversed([p for p in _px_map(L) if p[0] < bar - WIN]) if (v >= c if up else v <= c)), None)
        out.append(dict(id=f'level:px1y:{"hi" if up else "lo"}', kind='level', key='px1y', dir='up' if up else 'down', theme='price', page='market', chart='ov-px', score=4,
                        title=T(f'收盤創一年{"新高" if up else "新低"}', f'Close at a 1-year {"high" if up else "low"}'),
                        fig=T(f'{F(c, "usd", "zh")}；前一年{"最高" if up else "最低"} {F(max(h) if up else min(h), "usd", "zh")}', f'{F(c, "usd", "en")}; prior-year {"high" if up else "low"} {F(max(h) if up else min(h), "usd", "en")}'),
                        ctx=T(f'上一次這麼{"高" if up else "低"}是 {ds(sd)}', f'last this {"high" if up else "low"}: {ds(sd)}') if sd else None))
    chg = g(L, 'price.bar.chg_pct'); ab = [abs(a / b - 1) * 100 for (_, a), (_, b) in zip(px[1:], px[:-1]) if b]
    if chg is not None and len(ab) > MIN_N:
        r = sum(x < abs(chg) for x in ab) / len(ab) * 100
        if r >= 97:
            out.append(dict(id=f'jump:price-day:{"up" if chg > 0 else "down"}', kind='jump', key='price-day', dir='up' if chg > 0 else 'down', theme='price', page='market', chart='ov-px', score=2.5 + (r - 97),
                            title=T(f'單日{"大漲" if chg > 0 else "大跌"} {F(chg, "spct", "zh")}', f'Big one-day {"gain" if chg > 0 else "drop"} {F(chg, "spct", "en")}'),
                            fig=T(f'單日漲跌幅在近一年第 {r:.1f} 百分位', f'one-day move at 1-year percentile {r:.1f}')))
    return out


# ---------- 連續 ----------
def _streaks(L):
    out = []; e = [r for r in g(L, 'flows.etf') or [] if not r.get('partial') and r.get('musd') is not None]
    if e:
        sg = e[-1]['musd'] > 0; n = 0
        for r in reversed(e):
            if (r['musd'] > 0) != sg: break
            n += 1
        if n >= 5:
            tot = sum(r['musd'] for r in e[-n:])
            out.append(dict(id=f'streak:etf:{"in" if sg else "out"}', kind='streak', key='etf', dir='up' if sg else 'down', theme='flows', page='flows', chart='etf', score=2 + min(n, 12) / 4, run=n,
                            title=T(f'ETF 連 {n} 個交易日淨{"流入" if sg else "流出"}', f'ETF net {"inflows" if sg else "outflows"} {n} trading days in a row'),
                            fig=T(f'合計 {F(tot, "musd", "zh")}（至 {e[-1]["d"]}）', f'total {F(tot, "musd", "en")} (through {e[-1]["d"]})')))
    br = g(L, 'chips.viz.sopr.below_run') or 0
    if br >= 5:
        out.append(dict(id='streak:sopr-below', kind='streak', key='sopr-below', dir='down', theme='holders', page='onchain', chart='sopr', score=2 + min(br, 20) / 5, run=br,
                        title=T(f'短期持有者連 {br} 天賠錢賣（SOPR < 1）', f'STH-SOPR below 1 for {br} days in a row'), fig=T(f'最新 {g(L, "chips.viz.sopr.value")}', f'latest {g(L, "chips.viz.sopr.value")}')))
    return out


# ---------- 跨指標組合 ----------
def _combos(L, sig, px):
    out = []; by = {s['key']: s for s in sig}
    pr = _rows(L, 'onchain.sth_pnl.rows', 1); ls = _rows(L, 'onchain.sth_pnl.rows', 2)
    pm = dict(_px_map(L))
    def day_chg(x):
        a, b = pm.get(x), pm.get(x - 1)
        return (a / b - 1) * 100 if a and b else None
    if len(pr) > MIN_N:
        i = len(pr) - 1; rp = _rank(pr, i); x = pr[i][0]; dc = day_chg(x)
        if rp is not None and rp >= CMB and dc is not None and dc < 0:
            out.append(dict(id='combo:profit-into-drop', kind='combo', key='profit-into-drop', dir='down', theme='holders', page='onchain', chart='sthpnl', date=ds(x), x=x, score=5,
                            title=T('短期持有者趁跌集中獲利了結', 'Short-term holders took profit into a down day'),
                            fig=T(f'實現獲利 {F(pr[i][1], "btc", "zh")}（近一年第 {rp:.1f} 百分位），當天價格 {F(dc, "spct", "zh")}（{md(x)}）', f'realized profit {F(pr[i][1], "btc", "en")} (1-year percentile {rp:.1f}); price {F(dc, "spct", "en")} that day ({md(x)})'),
                            caveat=SM, hist=_history(pr, lambda k: (lambda q: q is not None and q >= CMB and (day_chg(pr[k][0]) or 0) < 0)(_rank(pr, k)), px, i)))
        if len(ls) > MIN_N:
            j = len(ls) - 1; rl = _rank(ls, j); so = g(L, 'chips.viz.sopr.value')
            if rl is not None and rl >= CMB and so is not None and so < 1:
                out.append(dict(id='combo:sth-capitulation', kind='combo', key='sth-capitulation', dir='down', theme='holders', page='onchain', chart='sthpnl', date=ds(ls[j][0]), x=ls[j][0], score=5,
                                title=T('短期持有者集中認賠', 'Short-term holders capitulating'), fig=T(f'實現虧損 {F(ls[j][1], "btc", "zh")}（近一年第 {rl:.1f} 百分位），SOPR {so}', f'realized loss {F(ls[j][1], "btc", "en")} (1-year percentile {rl:.1f}), SOPR {so}'),
                                caveat=SM, hist=_history(ls, lambda k: (lambda q: q is not None and q >= CMB)(_rank(ls, k)), px, j)))
    # SOPR 的變化拆成「獲利變多」還是「虧損變少」（STH 實現獲利／虧損兩條）
    w = g(L, 'onchain.sth_pnl.d7'); sop = next((s for s in sig if s['key'] in ('sth-sopr', 'sopr_ge1')), None)
    if w and sop:
        up = g(L, 'onchain.sth_pnl.ratio', 0) >= w['ratio']
        dz, de = (('獲利了結變多', 'more profit taking') if up else ('獲利了結變少', 'less profit taking')) if w['drive'] == 'profit' else (('認賠變少', 'less loss selling') if up else ('認賠變多', 'more loss selling'))
        sop['decomp'] = T(f'拆解：和 7 天前比，實現獲利 {F(w["profit_chg_pct"], "spct", "zh")}、實現虧損 {F(w["loss_chg_pct"], "spct", "zh")}，主要是{dz}', f'breakdown: versus 7 days ago, realized profit {F(w["profit_chg_pct"], "spct", "en")}, realized loss {F(w["loss_chg_pct"], "spct", "en")}; mainly {de}')
    chg, fw = g(L, 'price.bar.chg_pct'), g(L, 'deriv.funding_multi.weighted_now')
    if chg is not None and fw is not None and chg >= 1 and fw < 0:
        out.append(dict(id='combo:squeeze', kind='combo', key='squeeze', dir='up', theme='vol', page='deriv', chart=None, score=4,
                        title=T('上漲但資金費率為負：軋空推動', 'Rally with negative funding: short covering'), fig=T(f'收盤 {F(chg, "spct", "zh")}，加權資金費率 {F(fw, "spct", "zh")}（年化）', f'close {F(chg, "spct", "en")}, weighted funding {F(fw, "spct", "en")} (annualized)')))
    if chg is not None and fw is not None and chg >= 1.5 and fw >= 20:
        out.append(dict(id='combo:leverage-chase', kind='combo', key='leverage-chase', dir='up', theme='vol', page='deriv', chart=None, score=4,
                        title=T('上漲伴隨高資金費率：槓桿追價', 'Rally with high funding: leveraged chasing'), fig=T(f'收盤 {F(chg, "spct", "zh")}，加權資金費率 {F(fw, "spct", "zh")}（年化）', f'close {F(chg, "spct", "en")}, weighted funding {F(fw, "spct", "en")} (annualized)')))
    dvp = g(L, 'deriv.dvol.pct_1y'); rv = _rows(L, 'deriv.viz.vol.rows', 2)
    if dvp is not None and len(rv) > 60:
        h = [v for _, v in rv[:-1]]; rvp = sum(v < rv[-1][1] for v in h) / len(h) * 100
        if dvp <= 20 and rvp <= 20:
            cz = g(L, 'chips.flow.conc5.pct')
            out.append(dict(id='combo:vol-squeeze', kind='combo', key='vol-squeeze', dir='flat', theme='vol', page='deriv', chart='vol', score=3.5,
                            title=T('波動壓縮：隱含與實際波動都在低檔', 'Volatility compression: implied and realized both low'),
                            fig=T(f'DVOL 一年第 {dvp:.0f} 百分位、RV30 第 {rvp:.0f} 百分位（近半年）' + (f'；現價 ±5% 籌碼 {cz}%' if cz else ''), f'DVOL 1-year percentile {dvp:.0f}, RV30 percentile {rvp:.0f} (6 months)' + (f'; {cz}% of supply within ±5%' if cz else '')),
                            caveat=T('波動率不告訴你方向', 'volatility says nothing about direction')))
    e = [r for r in g(L, 'flows.etf') or [] if not r.get('partial') and r.get('musd') is not None][-5:]
    if len(e) == 5:
        tot = sum(r['musd'] for r in e); a, b = _at(px, dn(e[0]['d']) - 1, 4), _at(px, dn(e[-1]['d']), 4)
        pc = (b[1] / a[1] - 1) * 100 if a and b else None
        if pc is not None and ((tot >= 500 and pc <= -3) or (tot <= -500 and pc >= 3)):
            out.append(dict(id='combo:etf-price-div', kind='combo', key='etf-price-div', dir='up' if tot > 0 else 'down', theme='flows', page='flows', chart='etf', score=4,
                            title=T('ETF 資金和價格背離', 'ETF flows diverging from price'),
                            fig=T(f'近 5 個完整交易日 ETF {F(tot, "musd", "zh")}，同期價格 {F(pc, "spct", "zh")}（{e[0]["d"][5:]}–{e[-1]["d"][5:]}）', f'ETF {F(tot, "musd", "en")} over the last 5 complete days, price {F(pc, "spct", "en")} ({e[0]["d"][5:]}–{e[-1]["d"][5:]})')))
    return out


def _clusters(sig):
    out = []
    for th, (zh, en) in THEME.items():
        ss = [s for s in sig if s.get('theme') == th and s['kind'] != 'combo']
        if len(ss) >= 3:
            out.append(dict(id=f'combo:cluster:{th}', kind='combo', key='cluster-' + th, dir='flat', theme=th, page=ss[0]['page'], chart=None, score=3 + len(ss) / 2, members=[s['id'] for s in ss],
                            title=T(f'{zh}：{len(ss)} 項同時異動', f'{en}: {len(ss)} signals at once'), fig=T('、'.join(s['title']['zh'] for s in ss[:4]), '; '.join(s['title']['en'] for s in ss[:4]))))
    return out


# ---------- 追蹤條件 ----------
OPS = {'<': lambda a, b: a < b, '<=': lambda a, b: a <= b, '>': lambda a, b: a > b, '>=': lambda a, b: a >= b}


def checks(L, notes):
    """上一期 findings／followups 寫的 check：{"path": latest.json 的路徑, "op": "<|<=|>|>=", "value": 數字, "by": 期限}。"""
    out = []; bar = g(L, 'meta.bar_date')
    items = [(f.get('id'), f.get('title'), f.get('check'), notes.get('date')) for f in notes.get('findings') or []]
    items += [(f.get('id'), f.get('title'), f.get('check'), f.get('since')) for f in notes.get('followups') or [] if f.get('status') in ('open', 'ongoing')]
    for fid, title, ck, since in items:
        for c in ([ck] if isinstance(ck, dict) else ck or []):
            v = g(L, c.get('path', '')); op = OPS.get(c.get('op'))
            met = op(v, c['value']) if op and isinstance(v, (int, float)) and isinstance(c.get('value'), (int, float)) else None
            out.append(dict(id=fid, title=title, since=since, path=c.get('path'), op=c.get('op'), value=c.get('value'), now=v, met=met,
                            by=c.get('by'), expired=bool(c.get('by') and bar and bar > c['by']), means=c.get('means'), label=c.get('label')))
    return out


# ---------- 主程式 ----------
SNAP = ('meta.bar_date', 'price.bar.c', 'price.ma.sma200', 'onchain.metrics.sth-realized-price.value', 'chips.flow.sth_vs_tmm.tmm', 'deriv.funding_multi.weighted_now',
        'deriv.samesource.iv_minus_rv30', 'deriv.rr25.rr', 'chips.viz.sopr.value', 'onchain.npl.sum7_usd_m', 'flows.rc_liq.chg30_pct', 'flows.cb_premium.avg7',
        'onchain.hash_ribbons.capitulation', 'flows.fear_greed.value', 'cycle.stage.stage', 'cycle.stage.evidence.items', 'cycle.tidemark.top.signal',
        'cycle.tidemark.bottom.signal', 'exit.status.p6', 'signals.active')


def snapshot(L):
    """上一期快照：只留狀態翻轉要用的欄位（巢狀結構和 latest.json 相同，g() 照樣能讀）。"""
    out = {}
    for p in SNAP:
        v = g(L, p)
        if v is None: continue
        if p == 'cycle.stage.evidence.items': v = [{k: it.get(k) for k in ('id', 'label', 'ok', 'cond', 'value')} for it in v]
        o = out; ks = p.split('.')
        for k in ks[:-1]: o = o.setdefault(k, {})
        o[ks[-1]] = v
    return out


def build(L, prev=None, notes=None):
    bar = dn(g(L, 'meta.bar_date')); px = _px_map(L)
    sig = []
    for fn in (lambda: _single(L, bar, px), lambda: _flips(L, prev), lambda: _levels(L, bar), lambda: _streaks(L)):
        try: sig += fn()
        except Exception as e: sig.append(dict(id='error', kind='error', title=T(f'偵測失敗：{e}', f'detector failed: {e}'), score=0))
    try: sig += _combos(L, sig, px)
    except Exception as e: sig.append(dict(id='error:combo', kind='error', title=T(f'組合規則失敗：{e}', f'combo rules failed: {e}'), score=0))
    sig += _clusters(sig)
    act0 = g(prev or {}, 'signals.active') or {}; act = {}
    for s in sig:
        if s.get('kind') == 'error': continue
        first = act0.get(s['id'], g(L, 'meta.bar_date')); act[s['id']] = first
        s['first_seen'] = first; s['days'] = bar - dn(first) + 1; s['new'] = s['days'] == 1
        s['score'] = round(s['score'] * (1.5 if s['new'] else max(0.35, 0.75 ** (s['days'] - 1))), 2)
        s.setdefault('date', g(L, 'meta.bar_date'))
    sig.sort(key=lambda s: -s['score'])
    ck = []
    try: ck = checks(L, notes or {})
    except Exception as e: ck = [dict(id='error', title=f'追蹤條件檢查失敗：{e}')]
    return dict(base=prev, date=g(L, 'meta.bar_date'), n=len([s for s in sig if s.get('kind') != 'error']), n_series=len(SERIES), items=sig[:TOP], more=[s['id'] for s in sig[TOP:]],
                errors=[s['title']['zh'] for s in sig if s.get('kind') == 'error'], active=act, checks=ck, states=states(L),
                note='規則寫死（pipeline/signals.py）：一年 2% 極端值、7 日變化 2% 極端值、狀態翻轉、關鍵價位 ±3%、連續、跨指標組合；hist 只給每日任務當背景。只作讀值')
