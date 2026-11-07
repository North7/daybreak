#!/usr/bin/env python3
"""X 回覆配圖（2026-11-04 建立）：依 data/replies.json 裡每則回覆的 image 欄位出圖到 data/replies/<n>.png。
版面、字型、配色沿用 pipeline/picks.py 的「今日圖表」卡（1080×1350，X 不會裁切）；圖上的語言跟著回覆（en → 英文圖、zh → 中文圖）。
image 欄位：{"chart": "<picks.py 的圖表 id，例如 cbp、sopr、etf、cohort、cost>", "title": "<圖上的大標題>"}
           或 {"chart": "liq", "title": "...", "marks": [75000, 76200, ...]}：本站推算的清算價位分布（OKX），marks 是原文提到的價位。
           或 {"chart": "ad", "title": "..."}：老幣累積（供給端，近兩年），適合回應講需求端／新買家／賣方枯竭的貼文。
           或 {"chart": "sec", "title": "..."}：賣方衰竭常數（CheckOnChain，近兩年，標 0.13 極端線）。
           或 {"chart": "lthloss", ...}：長期持有者虧損比例（CheckOnChain，2018 年起，虛線＝本輪熊底高點）。
           或 {"chart": "bands", ...}：短期持有者成本帶（Bitview，近兩年，±1、±2 標準差）。
           或 {"chart": "agecost", ...}：6–12 與 12–18 個月持幣成本（Bitview，2023 年起，底部寫上次死叉／金叉）。
           或 {"chart": "rpl", ...}：實現獲利 ÷ 實現虧損 90 天平均（CheckOnChain，2018 年起，對數刻度，1＝獲利和虧損一樣多；2026-11-05 加）。
           或 {"chart": "chg", "title": "...", "from": "2026-09-17", "marks": [{"d": "2026-10-02", "zh": "非農", "en": "NFP"}], "span": ["2026-10-07", "2026-10-08"]}：
             每日漲跌幅柱狀圖（data/history/index.json，Kraken 日線），marks 標事件日、span 標一段連跌；適合對質「某天數據公布後跌了多少」（2026-11-07 加）。
           lthloss、bands、agecost 是 2026-11-04 網站新加的圖（資料在 latest.json 的 onchain.lthloss、onchain.sth_bands、cycle.age_cost）。
需要 pipeline/picks.py（PR #19「每日推薦發文圖表」）與 Pillow；字型同 share_card.py。
用法（在倉庫根目錄）：python3 ops/replies/cards.py --fonts <字型資料夾>
只作讀值：圖只放市場資訊，不放出場框架。"""
import argparse, base64, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import picks as PK   # noqa: E402
from signals import g, T   # noqa: E402
sys.path.insert(0, os.path.join(ROOT, 'ops', 'articles'))
import charts as AC   # noqa: E402  長文的畫法：可自訂 x／y 刻度（rpl 用對數刻度）；要在下面包 draw_line_chart 之前 import

OUT = os.path.join(ROOT, 'data', 'replies')


def k(v): return f'{v / 1000:.1f}K'.replace('.0K', 'K')


def c_liq(L, marks, marks_label=None):
    h = g(L, 'deriv.liq_heat'); nb, lo, step, c = h['nb'], h['lo'], h['step'], h['close']
    raw = base64.b64decode(h['heat'])[-nb:]                     # 最後一個小時的分布（每 100 美元一格；超過 cap 的格子被截在 cap）
    rows = [(lo + j * step, raw[j] / 255 * h['cap']) for j in range(nb)]
    lb, ab = h['below'][0], h['above'][0]
    return dict(kind='liq', rows=rows, step=step, close=c, marks=marks or [],
                name=T('推算清算價位', 'Estimated liquidation levels'),
                sub=T('OKX 永續未平倉量＋假設 5–100 倍槓桿推算；每 100 美元一格的顆數；不是實際倉位',
                      'From OKX perpetual open interest with assumed 5–100x leverage; BTC per $100 bucket; a model, not actual positions'),
                series=[dict(name=T('多單清算', 'Long liquidations'), color=PK.S2), dict(name=T('空單清算', 'Short liquidations'), color=PK.S1)]
                       + ([dict(name=T(*(marks_label or ('原文價位', 'Levels in the post'))), color=PK.INK)] if marks else []),
                src='OKX（推算）', asof=h['asof'][:10],
                stats=[PK.S('下方 5% 內多單', 'Longs within 5% below', f'{h["within5"]["below"]:,} 顆', f'{h["within5"]["below"]:,} BTC'),
                       PK.S('上方 5% 內空單', 'Shorts within 5% above', f'{h["within5"]["above"]:,} 顆', f'{h["within5"]["above"]:,} BTC'),
                       PK.S('最大多單帶', 'Largest long band', f'{k(lb["lo"])}–{k(lb["hi"])}')])


def c_ad(L, end):
    """供給端：一年以上未動供給的 30 天變化 − 30 天新挖出的幣（onchain.ad 是 CryptoQuant 定義「新挖出 − 未動變化」，這裡反過來畫，
    高於 0＝老幣增加得比新挖出的還多，比較直覺）。"""
    a = g(L, 'onchain.ad'); rows = [r for r in a['rows'] if r[0] > end - 730]; net = -a['value']
    sg = lambda v, d, u: ('+' if v >= 0 else '−') + format(abs(v) / d, u)
    return dict(kind='line', name=T('老幣淨增加（供給端）', 'Old coins vs new supply'),
                sub=T('一年以上沒動的幣 30 天變化 − 同期新挖出的幣；高於 0＝老幣增加得比新挖出的還多',
                      '30-day change in coins unmoved for 1+ year, minus 30-day new issuance; above 0 means old coins grow faster than new supply'),
                series=[dict(name=T('每日值', 'Daily'), rows=[(r[0], -r[1]) for r in rows], color=PK.INK3, width=3),
                        dict(name=T('30 日平均', '30-day average'), rows=[(r[0], -r[2]) for r in rows], color=PK.S1, width=7)],
                refs=[dict(y=0)], yf=lambda v: f'{v / 1e3:,.0f}K', src='CheckOnChain HODL Waves（推算）', asof=a['date'],
                stats=[PK.S('一年以上未動 30 日', '1y+ unmoved, 30 days', sg(a['inact_chg30'], 1e4, '.1f') + ' 萬顆', sg(a['inact_chg30'], 1e3, ',.0f') + 'K BTC'),
                       PK.S('30 天新挖出', 'Mined in 30 days', f'{a["issued30"] / 1e4:.2f} 萬顆', f'{a["issued30"] / 1e3:,.1f}K BTC'),
                       PK.S('老幣淨增加', 'Net old-coin growth', sg(net, 1e4, '.1f') + ' 萬顆', sg(net, 1e3, ',.0f') + 'K BTC')])


def c_sec(L, end):
    """賣方衰竭常數（CheckOnChain）：近兩年，0.13 極端線；底部三格：上次進極端區的低點、之後的次低點、最新。"""
    s = g(L, 'onchain.sec'); rows = [(r[0], r[1]) for r in s['rows'] if r[0] > end - 730]
    hit = next((h for h in reversed(s.get('hits') or []) if h.get('low_date')), None); rl = s.get('recent_low') or {}
    st = []
    if hit: st.append(PK.S(f'極端區低點（{PK.md(hit["low_date"], "zh")}）', f'Extreme low ({PK.md(hit["low_date"], "en")})', f'{hit["low"]:.4f}'))
    if rl: st.append(PK.S(f'次低點（{PK.md(rl["date"], "zh")}）', f'Higher low ({PK.md(rl["date"], "en")})', f'{rl["value"]:.4f}'))
    st.append(PK.S(f'最新（{PK.md(s["date"], "zh")}）', f'Latest ({PK.md(s["date"], "en")})', f'{s["value"]:.4f}'))
    return dict(kind='line', name=T('賣方衰竭常數', 'Seller exhaustion constant'),
                sub=T(f'獲利供給比例 × 30 天價格波動；低於 {s["th"]}＝極端衰竭區（歷史上約 {s["th_share"]}% 的日子）',
                      f'Supply in profit × 30-day volatility; below {s["th"]} is the extreme zone (about {s["th_share"]}% of days in history)'),
                series=[dict(name=T('賣方衰竭常數', 'SEC'), rows=rows, color=PK.S1, width=5)],
                refs=[dict(y=s['th'], label=T(f'{s["th"]} 極端區', f'{s["th"]} extreme zone'))], yf=lambda v: f'{v:.2f}',
                src='CheckOnChain', asof=s['date'], stats=st)


def c_lthloss(L, end):
    """長期持有者虧損比例（CheckOnChain，2018 年起，含 2019、2022、本輪三個熊底高點）；虛線＝本輪高點。"""
    s = g(L, 'onchain.lthloss'); rows = [(r[0], r[1]) for r in s['rows'] if r[0] >= PK.dn('2018-06-01')]
    if rows and rows[-1][0] == PK.dn(s['date']): rows[-1] = (rows[-1][0], s['value'])   # rows 是每 4 天取最高值；線尾換成當天的值，和標題、底部數字一致
    pk = s['peaks'][-1]; prev = s['peaks'][-2]
    return dict(kind='line', name=T('長期持有者虧損比例', 'Long-term holder supply in loss'),
                sub=T('持有 155 天以上的幣，有多少比例買在現價之上（%）；虛線是本輪熊底的高點',
                      'Share of coins held 155+ days that were bought above today\'s price (%); dashed line is this cycle\'s bear-market peak'),
                series=[dict(name=T('長期持有者虧損比例', 'LTH supply in loss'), rows=rows, color=PK.S1, width=5, area=True)],
                refs=[dict(y=pk['value'])],   # 不加文字標籤：會壓到 2019 年的高點，副標已經說明虛線
                yf=lambda v: f'{v:.0f}%', src='CheckOnChain', asof=s['date'],
                stats=[PK.S(f'最新（{PK.md(s["date"], "zh")}）', f'Latest ({PK.md(s["date"], "en")})', f'{s["value"]}%'),
                       PK.S(f'本輪高點（{pk["date"][:7].replace("-", "/")}）', f'This cycle\'s peak ({pk["date"][:7]})', f'{pk["value"]}%'),
                       PK.S(f'上一輪（{prev["date"][:7].replace("-", "/")}）', f'Last cycle ({prev["date"][:7]})', f'{prev["value"]}%')])


def c_bands(L, end):
    """短期持有者成本帶（Bitview）：成本 ×（近 4 年「價格 ÷ 成本」的平均 ± 1、2 個標準差），近兩年。"""
    b = g(L, 'onchain.sth_bands'); now = b['now']
    rows = [r for r in b['rows'] if r[0] > end - 730]
    band = lambda k_: [(r[0], r[2] * (r[3] + k_ * r[4])) for r in rows]
    z = now['z']
    return dict(kind='line', name=T('短期持有者成本帶', 'STH cost basis bands'),
                sub=T('短期持有者成本 ×（近 4 年「價格 ÷ 成本」的平均 ± 1、2 個標準差）',
                      'STH cost basis × (4-year mean of price ÷ cost, ± 1 and 2 standard deviations)'),
                series=[dict(name=T('+2 標準差', '+2 SD'), rows=band(2), color=PK.S3, width=3),
                        dict(name=T('±1 標準差', '±1 SD'), rows=band(1), color=PK.S2, width=4),
                        dict(name=T('−1', '−1'), rows=band(-1), color=PK.S2, width=4, faint=True),
                        dict(name=T('−2', '−2'), rows=band(-2), color=PK.S3, width=3, faint=True),
                        dict(name=T('短期持有者成本', 'STH cost basis'), rows=[(r[0], r[2]) for r in rows], color=PK.S1, width=6),
                        dict(name=T('收盤', 'Close'), rows=[(r[0], r[1]) for r in rows], color=PK.INK3, width=4)],
                yf=lambda v: f'{v / 1e3:,.0f}K', src='Bitview · Kraken', asof=b['date'],
                stats=[PK.S('現在位置', 'Now at', ('+' if z >= 0 else '−') + f'{abs(z):.2f} 個標準差', ('+' if z >= 0 else '−') + f'{abs(z):.2f} SD'),
                       PK.S('−1 標準差', '−1 SD', PK.usd(now['bands']['-1'])),
                       PK.S('+1 標準差', '+1 SD', PK.usd(now['bands']['1']))])


def c_agecost(L, end):
    """6–12 與 12–18 個月持幣成本（Bitview），2023 年起；底部三格：兩條線的現值、上次交叉。"""
    a = g(L, 'cycle.age_cost'); rows = [r for r in a['rows'] if r[0] >= PK.dn('2023-01-01')]
    lc = a['last_cross']; kind = {'death': ('死叉', 'death cross'), 'golden': ('金叉', 'golden cross')}.get(lc['kind'], (lc['kind'], lc['kind']))
    return dict(kind='line', name=T('6–12 與 12–18 個月持幣成本', '6–12 vs 12–18 month cost basis'),
                sub=T('兩個年齡層的平均買價；6–12 個月線跌破 12–18 個月線＝死叉，重新上穿＝金叉',
                      'Average buy price of two age bands; 6–12m falling below 12–18m is a death cross, crossing back above a golden cross'),
                series=[dict(name=T('收盤', 'Close'), rows=[(r[0], r[1]) for r in rows if r[1]], color=PK.INK3, width=3),
                        dict(name=T('6–12 個月', '6–12 months'), rows=[(r[0], r[2]) for r in rows], color=PK.S1, width=6),
                        dict(name=T('12–18 個月', '12–18 months'), rows=[(r[0], r[3]) for r in rows], color=PK.S2, width=6)],
                yf=lambda v: f'{v / 1e3:,.0f}K', src='Bitview · Kraken', asof=a['date'],
                stats=[PK.S('6–12 個月成本', '6–12m cost', PK.usd(a['c612'])),
                       PK.S('12–18 個月成本', '12–18m cost', PK.usd(a['c1218'])),
                       PK.S(f'上次交叉（{PK.md(lc["date"], "zh")}）', f'Last cross ({PK.md(lc["date"], "en")})',
                            f'{kind[0]}，{a["days_since"]} 天前', f'{kind[1]}, {a["days_since"]}d ago')])


def c_rpl(L, end):
    """實現獲利 ÷ 實現虧損，90 天平均（CheckOnChain），2018 年起，對數刻度；1＝獲利和虧損一樣多。"""
    import math
    r = g(L, 'onchain.rpl'); lg = math.log10
    rows = [(x[0], lg(x[1])) for x in r['rows'] if x[0] >= PK.dn('2018-01-01') and x[1] > 0]
    return dict(kind='line', name=T('實現獲利 ÷ 實現虧損（90 天平均）', 'Realized profit ÷ realized loss (90-day avg)'),
                sub=T('全網賣出時實現的獲利除以虧損，取 90 天平均；對數刻度；低於 1＝認賠多於獲利',
                      'Network-wide realized profit ÷ realized loss, 90-day average; log scale; below 1 = more loss-taking'),
                series=[dict(name=T('90 天平均', '90-day average'), rows=rows, color=PK.S1, width=5)],
                refs=[dict(y=0, lx=0.3, label=T('1＝獲利和虧損一樣多', '1 = profit equals loss'))],
                xticks=AC.years(rows[0][0], rows[-1][0], 1), yticks=[lg(v) for v in (0.3, 1, 3, 10, 30)],
                yf=lambda v: f'{10 ** v:.2g}', src='CheckOnChain', asof=r['date'],
                stats=[PK.S(f'最新（{PK.md(r["date"], "zh")}）', f'Latest ({PK.md(r["date"], "en")})', f'{r["value"]:.2f}'),
                       PK.S(f'高於 1（{PK.md(r["since"], "zh")} 起）', f'Above 1 (since {PK.md(r["since"], "en")})', f'{r["since_days"]} 天', f'{r["since_days"]} days'),
                       PK.S('最近 7 天每日比值', 'Daily ratio, last 7 days', f'{r["last7"]:.2f}')])


def c_chg(L, end, im):
    """每日漲跌幅（data/history/index.json）；marks 是事件日（虛線＋標籤），span 是一段連續下跌（括號＋合計）。"""
    H = json.load(open(os.path.join(ROOT, 'data', 'history', 'index.json')))
    H = [r for r in H if r['date'] >= im.get('from', '2026-09-17') and r.get('chg_pct') is not None]
    by = {r['date']: r for r in H}
    marks = [dict(m, x=PK.dn(m['d']), v=by[m['d']]['chg_pct']) for m in im.get('marks') or [] if m['d'] in by]
    sp_ = im.get('span'); span = None
    if sp_:
        a = [r for r in H if r['date'] < sp_[0]][-1]['close']; b = by[sp_[1]]['close']
        span = dict(x0=PK.dn(sp_[0]), x1=PK.dn(sp_[1]), v=(b / a - 1) * 100)
    pct = lambda v: ('+' if v >= 0 else '−') + f'{abs(v):.1f}%'
    st = [PK.S(f'{PK.md(m["d"], "zh")} {m["zh"]}當天', f'{m["en"]} day, {PK.md(m["d"], "en")}', pct(m['v'])) for m in marks]
    if span: st.insert(1, PK.S(f'{PK.md(sp_[0], "zh")}–{PK.md(sp_[1], "zh")[-2:].lstrip("/")} 兩天', f'{PK.md(sp_[0], "en")}–{sp_[1][-2:].lstrip("0")}, two days', pct(span['v'])))
    return dict(kind='chg', name=T('比特幣每日漲跌幅', 'Bitcoin daily change'),
                sub=T('每日收盤對前一日（%）；虛線是事件日', 'Daily close vs prior close (%); dashed lines mark event days'),
                rows=[(PK.dn(r['date']), r['chg_pct']) for r in H], marks=marks, span=span, pct=pct,
                series=[dict(name=T('上漲', 'Up'), color=PK.UP), dict(name=T('下跌', 'Down'), color=PK.RED)],
                src='Kraken', asof=H[-1]['date'], stats=st[:3])


def draw_chg(d, box, sp, lang, Fn):
    import datetime as dt
    x0, y0, x1, y1 = box; px1 = x1 - 150; top = y0 + 110; pb = y1 - 70
    rows = sp['rows']; xa, xb = rows[0][0] - 0.6, rows[-1][0] + 0.6
    ys = [v for _, v in rows] + [0]; ya, yb = min(ys), max(ys); pad = (yb - ya) * 0.08; ya, yb = ya - pad, yb + pad
    X = lambda x: x0 + (x - xa) / (xb - xa) * (px1 - x0)
    Y = lambda v: pb - (v - ya) / (yb - ya) * (pb - top)
    tf = Fn['mono'](34, 500); cj = lambda z, w: Fn['cjk'](z, w) if lang == 'zh' else Fn['mono'](int(z * 0.92), w)
    for t in PK.nice(ya, yb):
        d.line([x0, Y(t), px1, Y(t)], fill=PK.LINE, width=2)
        d.text((px1 + 18, Y(t)), (f'{t:+.0f}%' if t else '0%').replace('-', '−'), font=tf, fill=PK.INK3, anchor='lm')
    bw = (px1 - x0) / (xb - xa) * 0.7; mx = {m['x'] for m in sp['marks']}
    sx = sp['span']
    for x, v in rows:
        c = PK.UP if v >= 0 else PK.RED
        if not (x in mx or (sx and sx['x0'] <= x <= sx['x1'])): c = PK.tint(c, 0.45)
        d.rectangle([X(x) - bw / 2, min(Y(v), Y(0)), X(x) + bw / 2, max(Y(v), Y(0))], fill=c)
    d.line([x0, Y(0), px1, Y(0)], fill=PK.INK, width=3)
    e = dt.date(1970, 1, 1)
    for x, _ in rows:   # x 軸：每月 1 日和 15 日
        dd = e + dt.timedelta(days=x)
        if dd.day in (1, 15):
            d.line([X(x), pb, X(x), pb + 14], fill=PK.INK3, width=2)
            lab = f'{dd.month}/{dd.day}' if lang == 'zh' else f'{PK.MON[dd.month - 1]} {dd.day}'
            d.text((X(x), pb + 24), lab, font=Fn['mono'](30, 500), fill=PK.INK3, anchor='mt')
    d.line([x0, pb, px1, pb], fill=PK.INK3, width=2)
    lf = cj(32, 900)
    for m in sp['marks']:
        vdash(d, X(m['x']), top - 10, pb, PK.INK, 3)
        t = f'{PK.md(m["d"], "zh")} {m["zh"]} {sp["pct"](m["v"])}' if lang == 'zh' else f'{m["en"]} {PK.md(m["d"], "en")} {sp["pct"](m["v"])}'
        bb = d.textbbox((X(m['x']), top - 18), t, font=lf, anchor='mb')
        sh = max(0, bb[2] - px1) - min(0, bb[0] - x0)
        d.rectangle([bb[0] - 8 - sh, bb[1] - 4, bb[2] + 8 - sh, bb[3] + 4], fill=PK.PAPER)
        d.text((X(m['x']) - sh, top - 18), t, font=lf, fill=PK.INK, anchor='mb')
    if sx:
        lo = min(v for x, v in rows if sx['x0'] <= x <= sx['x1']); yy = Y(lo) + 26; a, b = X(sx['x0']) - bw, X(sx['x1']) + bw
        d.line([a, yy, b, yy], fill=PK.RED, width=4); d.line([a, yy - 12, a, yy], fill=PK.RED, width=4); d.line([b, yy - 12, b, yy], fill=PK.RED, width=4)
        t = (f'兩天 {sp["pct"](sx["v"])}' if lang == 'zh' else f'2 days {sp["pct"](sx["v"])}')
        d.text(((a + b) / 2, yy + 12), t, font=lf, fill=PK.RED, anchor='mt')


EXTRA = {'ad': c_ad, 'sec': c_sec, 'lthloss': c_lthloss, 'bands': c_bands, 'agecost': c_agecost, 'rpl': c_rpl}   # picks.py 沒有、回覆配圖另外加的圖表


def vdash(d, x, y0, y1, color, w=3, dash=16, gap=12):
    y = y0
    while y < y1:
        d.line([x, y, x, min(y + dash, y1)], fill=color, width=w); y += dash + gap


def draw_liq(d, box, sp, lang, Fn):
    x0, y0, x1, y1 = box; px1 = x1 - 150; top = y0 + 120; pb = y1 - 70   # 上方留給價位標籤，下方留給 x 軸
    rows, step, c = sp['rows'], sp['step'], sp['close']
    xa, xb = rows[0][0], rows[-1][0] + step; ymax = max(v for _, v in rows) * 1.08 or 1
    X = lambda p: x0 + (p - xa) / (xb - xa) * (px1 - x0)
    Y = lambda v: pb - v / ymax * (pb - top)
    tf = Fn['mono'](34, 500)
    for t in PK.nice(0, ymax):
        d.line([x0, Y(t), px1, Y(t)], fill=PK.LINE, width=2)
        d.text((px1 + 18, Y(t)), f'{t:,.0f}', font=tf, fill=PK.INK3, anchor='lm')
    bw = (px1 - x0) / len(rows)
    for p, v in rows:
        if v <= 0 or p < c < p + step: continue
        col = PK.S2 if p + step <= c else PK.S1
        d.rectangle([X(p) + 1, Y(v), X(p) + bw - 1, pb], fill=col)
    d.line([x0, pb, px1, pb], fill=PK.INK, width=3)
    p = (int(xa) // 2000 + 1) * 2000
    while p < xb:
        d.line([X(p), pb, X(p), pb + 14], fill=PK.INK3, width=2)
        d.text((X(p), pb + 24), f'{p // 1000}K', font=Fn['mono'](32, 500), fill=PK.INK3, anchor='mt'); p += 2000
    lf = Fn['mono'](30, 800); labs = []
    for i, m in enumerate(sorted(sp['marks'])):
        if not xa <= m <= xb: continue
        vdash(d, X(m), top, pb, PK.INK, 3)
        labs.append((X(m), top - 14 - (i % 2) * 44, k(m)))
    d.line([X(c), top - 20, X(c), pb], fill=PK.RED, width=5)
    for x, y, t in labs:
        bb = d.textbbox((x, y), t, font=lf, anchor='mb'); d.rectangle([bb[0] - 6, bb[1] - 4, bb[2] + 6, bb[3] + 4], fill=PK.PAPER)
        d.text((x, y), t, font=lf, fill=PK.INK, anchor='mb')
    cl = f'推算時 {PK.usd(c)}' if lang == 'zh' else f'At estimate {PK.usd(c)}'   # 清算快照當下（每天 08:00）的價格，不是日線收盤
    d.text((X(c) + 14, pb - (pb - top) * 0.55), cl, font=Fn['cjk'](34, 900) if lang == 'zh' else Fn['mono'](32, 800), fill=PK.RED, anchor='lm')


_line = PK.draw_line_chart
PK.draw_line_chart = lambda d, box, sp, lang, Fn: (draw_liq if sp.get('kind') == 'liq' else draw_chg if sp.get('kind') == 'chg' else _line)(d, box, sp, lang, Fn)


def build_spec(L, im):
    """image 欄位 → 圖表規格。stats 可覆寫底部三格：[{"zh_label", "en_label", "zh", "en"}]（快訊用，例如換成盤中低點）。"""
    end = PK.dn(g(L, 'meta.bar_date'))
    ml = im.get('marks_label')   # 例如 {"zh": "今天低點", "en": "Today's low"}；預設「原文價位」
    sp = (c_liq(L, im.get('marks'), (ml['zh'], ml['en']) if ml else None) if im['chart'] == 'liq'
          else c_chg(L, end, im) if im['chart'] == 'chg'
          else EXTRA[im['chart']](L, end) if im['chart'] in EXTRA
          else PK.spec(L, im['chart']))
    if sp and im.get('stats'):
        sp['stats'] = [PK.S(s['zh_label'], s['en_label'], s['zh'], s.get('en', s['zh'])) for s in im['stats']]
    return sp


def main(fonts_dir):
    import share_card as SC
    Fn = SC.fonts(fonts_dir)
    L = json.load(open(os.path.join(ROOT, 'data', 'latest.json')))
    rp = json.load(open(os.path.join(ROOT, 'data', 'replies.json')))
    rd = lambda f: json.load(open(os.path.join(ROOT, 'data', f))) if os.path.exists(os.path.join(ROOT, 'data', f)) else None
    notes = {'zh': rd('notes.json'), 'en': rd('notes.en.json')}
    os.makedirs(OUT, exist_ok=True); keep = set()
    for it in rp['items']:
        im = it.get('image')
        if not im: continue
        if im.get('site'): keep.add(f'{it["n"]}.png'); continue   # 網站原圖由 site_cards.py 截
        lang = 'zh' if it['lang'] == 'zh' else 'en'
        sp = build_spec(L, im)
        if not sp: print('skip', it['n'], im['chart'], '（沒有這張圖或資料不足）'); continue
        fn = f'{it["n"]}.png'
        PK.card(L, notes[lang], sp, im['title'], lang, Fn, os.path.join(OUT, fn)); keep.add(fn)
    for fn in os.listdir(OUT):   # 清掉前一天的圖
        if fn not in keep: os.remove(os.path.join(OUT, fn)); print('removed', fn)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--fonts', required=True)
    main(ap.parse_args().fonts)
