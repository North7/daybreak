#!/usr/bin/env python3
"""每日推薦發文圖表（2026-11-04 建立，規劃見 ops/picks/README.md）。
挑圖：當期 notes.json 的 findings（每日任務寫的「今日發現」，各帶一張 chart）優先，再依 latest.json 的 signals 分數補，最多 3 張；
      同一張圖只出一次。和出場框架有關的不推：page='exit' 的異動、週期佐證燈號（ev-*）、MVRV ÷ 前一輪高點（p20，0.75 線的來源）、
      200 日均線（避險線）相關的異動。
出圖：與 share_card.py 同一套字型與配色，1080×1350（4:5 直式，X、Threads、IG 都不會裁切），中英各一張：
      data/picks/<id>.png、data/picks/<id>-en.png；另寫 data/picks/index.json（這次畫了哪些）。圖上的數字都直接取自 latest.json，不另算。
解說：每日任務先跑 `plan` 看候選圖與圖上的數字，再寫 data/picks.json（每張圖中英文解說各一則，數字只引用、不改）。
      `render` 依 picks.json 的順序出圖；picks.json 不存在或日期不是當期時，改用自動挑的前 3 張（沒有解說，只有圖）。
用法（在倉庫根目錄）：
  python3 pipeline/picks.py plan                           # 印出候選圖、挑選理由、圖上數字（JSON），不需要字型與 Pillow
  python3 pipeline/picks.py check                          # 檢查 data/picks.json（日期、張數、字數、不談框架、數字都查得到出處）
  python3 pipeline/picks.py render --fonts <字型資料夾>      # 出圖到 data/picks/（字型同 share_card.py）
只作讀值：圖與解說只放市場資訊，不放出場框架、觸發條件、價格階梯或動作結論。"""
import json, os, re, sys, argparse, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signals import g, F, SERIES, dn, ds, T   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
MAX_PICKS, MAX_CAND = 3, 6
SKIP_CHART = re.compile(r'^(ev-|p20$)')                          # 週期佐證燈號、MVRV ÷ 前一輪高點（出場框架的 0.75 線）
SKIP_KEY = {'sma200', 'above_sma200', 'exit-step', 'k075', 'top_zone'}   # 200 日均線（避險線）、出場階、頂部區


# ---------- 數字格式（中英文各一份；圖上與 plan 輸出共用） ----------
def usd(v): return '$' + format(round(v), ',')


def musd(v, lang):
    s = '+' if v >= 0 else '−'
    if lang == 'zh': return f'{s}{abs(v) / 100:.2f} 億美元'
    return s + ('$' + format(abs(v) / 1e3, ',.2f') + 'B' if abs(v) >= 1000 else '$' + format(abs(v), ',.1f') + 'M')


def btc(v, lang):
    if lang == 'zh': return f'{v / 1e4:,.1f} 萬顆' if abs(v) >= 1e4 else f'{round(v):,} 顆'
    return f'{v / 1e6:,.2f}M BTC' if abs(v) >= 1e6 else (f'{v / 1e3:,.0f}K BTC' if abs(v) >= 1e4 else f'{round(v):,} BTC')


def spct(v, n=2): return ('+' if v >= 0 else '−') + format(abs(v), f',.{n}f') + '%'


def md(d, lang):
    d = dt.date.fromisoformat(d) if isinstance(d, str) else d
    return f'{d.month}/{d.day}' if lang == 'zh' else f'{d:%b} {d.day}'


def both(fn, *a): return T(fn(*a, 'zh'), fn(*a, 'en'))


def S(zh, en, vz, ve=None): return dict(label=T(zh, en), value=T(vz, ve if ve is not None else vz))


def last(rows, i=1):
    for r in reversed(rows):
        if r[i] is not None: return r
    return None


def tail(rows, days, end):
    return [r for r in rows if r[0] > end - days]


# ---------- 圖表目錄：chart id → 規格 ----------
# 規格：kind（line／bars／cohort）、series［name, rows=(x, y), color, width, area, faint］、refs［y, label］、
#       yf（刻度格式）、stats（底部三格，label／value 中英）、src（資料來源）、asof（資料日期）、sub（一句說明）
INK, INK3, PAPER, LINE, RED = '#0A0A0A', '#7A766F', '#EEECE6', '#D2CEC4', '#FF3B1F'
S1, S2, S3, UP = '#5B49D6', '#C2531A', '#008571', '#00805A'


def c_px(L, end):
    h = tail(g(L, 'price.history') or [], 365, end); c = g(L, 'price.bar.c')
    hi = max(h, key=lambda r: r[1]); lo = min(h, key=lambda r: r[1])
    return dict(kind='line', name=T('比特幣價格', 'Bitcoin price'), sub=T('近一年每日收盤（美元）', 'Daily close over the past year (USD)'),
                series=[dict(name=T('收盤', 'Close'), rows=[(r[0], r[1]) for r in h], color=INK, area=True)],
                yf=lambda v: f'{v / 1e3:,.0f}K', src='Kraken', asof=g(L, 'meta.bar_date'),
                stats=[S('收盤', 'Close', usd(c)), S(f'一年高點（{md(ds(hi[0]), "zh")}）', f'1-year high ({md(ds(hi[0]), "en")})', usd(hi[1])),
                       S(f'一年低點（{md(ds(lo[0]), "zh")}）', f'1-year low ({md(ds(lo[0]), "en")})', usd(lo[1]))])


def c_cost(L, end):
    rows = g(L, 'chips.viz.cost') or []; f = g(L, 'chips.flow.sth_vs_tmm') or {}
    ser = lambda i: [(r[0], r[i]) for r in rows if r[i] is not None]
    return dict(kind='line', name=T('短期持有者成本與真實市場均價', 'STH cost basis and true market mean'),
                sub=T('近兩年：收盤、短期持有者成本（155 天內換手的幣）、真實市場均價（活躍投資人的成本）',
                      'Past two years: close, short-term holder cost (coins moved within 155 days), true market mean (active investors\' cost)'),
                series=[dict(name=T('收盤', 'Close'), rows=ser(1), color=INK3, width=4),
                        dict(name=T('短期持有者成本', 'STH cost basis'), rows=ser(2), color=S1, width=7),
                        dict(name=T('真實市場均價', 'True market mean'), rows=ser(3), color=S2, width=7)],
                yf=lambda v: f'{v / 1e3:,.0f}K', src=(f.get('source') or 'bitcoin-data') + ' · Kraken', asof=f.get('date') or g(L, 'meta.bar_date'),
                stats=[S('收盤', 'Close', usd(g(L, 'price.bar.c'))), S('短期持有者成本', 'STH cost basis', usd(f['sth_cost'])), S('真實市場均價', 'True market mean', usd(f['tmm']))])


def c_cohort(L, end):
    co = g(L, 'chips.cohort'); w = co.get('width') or 2000; px = co['price']
    rows = [r for r in co['rows'] if px * 0.62 <= r[0] + w / 2 <= px * 1.42]
    top = max(co['rows'], key=lambda r: r[1])
    ex = co.get('src') == 'checkonchain'
    return dict(kind='cohort', name=T('長短期持有者籌碼分布', 'Where short- and long-term holders sit'),
                sub=T('每 2,000 美元一格：左邊短期持有者（持有不到 155 天）、右邊長期持有者；橫線是收盤',
                      '$2,000 buckets: short-term holders (under 155 days) on the left, long-term holders on the right; the line is the close'),
                rows=rows, width=w, price=px, src='CheckOnChain' if ex else 'bitcoin-data URPD（推算）' , asof=co.get('now_date') or co.get('date'),
                stats=[S('短期持有者', 'Short-term holders', btc(co['tot']['sth'], 'zh'), btc(co['tot']['sth'], 'en')),
                       S('短期持有者平均成本', 'STH average cost', usd(co['tot']['sth_cost'])),
                       S(f'最厚一格 {top[0] // 1000}–{(top[0] + w) // 1000}K', f'Thickest {top[0] // 1000}–{(top[0] + w) // 1000}K', btc(top[1], 'zh'), btc(top[1], 'en'))])


def c_cbp(L, end):
    p = g(L, 'flows.cb_premium'); rows = [(r[0], r[1]) for r in p['rows']]
    ma = [(rows[i][0], sum(v for _, v in rows[i - 6:i + 1]) / 7) for i in range(6, len(rows))]
    return dict(kind='line', name=T('Coinbase 溢價', 'Coinbase premium'), sub=T('Coinbase 美元報價相對 Binance 的價差（%）；細條是每日，線是 7 日平均',
                                                                             'Coinbase BTC-USD vs Binance BTC-USDT (%); bars are daily, the line is the 7-day average'),
                series=[dict(name=T('每日', 'Daily'), rows=rows, color=INK3, bars=True, faint=True), dict(name=T('7 日平均', '7-day average'), rows=ma, color=RED, width=7)],
                refs=[dict(y=0)], yf=lambda v: f'{v:.2f}%', src='Coinbase · Binance', asof=p['date'],
                stats=[S(f'今日（{md(p["date"], "zh")}）', f'Latest ({md(p["date"], "en")})', f'{p["pct"]:.3f}%'.replace('-', '−')),
                       S('7 日平均', '7-day average', f'{p["avg7"]:.3f}%'.replace('-', '−')), S('30 日平均', '30-day average', f'{p["avg30"]:.3f}%'.replace('-', '−'))])


def c_sopr(L, end):
    s = g(L, 'chips.viz.sopr'); v7 = g(L, 'onchain.viz.sth-sopr.last')
    return dict(kind='line', name=T('短期持有者 SOPR', 'Short-term holder SOPR'), sub=T('短期持有者賣出價 ÷ 買入價；低於 1＝整體賠錢賣', 'Sell price ÷ buy price of short-term holders; below 1 means selling at a loss'),
                series=[dict(name=T('STH-SOPR', 'STH-SOPR'), rows=[(r[0], r[1]) for r in s['rows']], color=S1, width=5)],
                refs=[dict(y=1, label=T('1＝不賺不賠', '1 = break-even'))], yf=lambda v: f'{v:.2f}', src='CheckOnChain', asof=s['date'],
                stats=[S(f'最新（{md(s["date"], "zh")}）', f'Latest ({md(s["date"], "en")})', f'{s["value"]:.4f}'),
                       S('7 日平均', '7-day average', f'{v7:.4f}' if v7 else '—'),
                       S('連續低於 1', 'Days below 1', f'{s.get("below_run") or 0} 天', f'{s.get("below_run") or 0}')])


def c_stab(L, end):
    s = g(L, 'flows.stables')
    return dict(kind='line', name=T('穩定幣供給', 'Stablecoin supply'), sub=T('全部美元穩定幣流通量（十億美元）', 'Total circulating USD stablecoins ($B)'),
                series=[dict(name=T('穩定幣', 'Stablecoins'), rows=[(r[0], r[1]) for r in s['rows']], color=S3, area=True)],
                yf=lambda v: f'${v:,.0f}B', src='DefiLlama', asof=s['date'],
                stats=[S(f'流通量（{md(s["date"], "zh")}）', f'Supply ({md(s["date"], "en")})', f'${s["usd_b"]:,.1f}B'),
                       S('7 日變化', '7-day change', spct(s['chg7_pct'])), S('30 日變化', '30-day change', spct(s['chg30_pct']))])


def c_etf(L, end):
    rows = g(L, 'flows.etf') or []; full = [r for r in rows if not r.get('partial')]; s7 = full[-7:]
    pr = rows[-1] if rows and rows[-1].get('partial') else None
    st = [S(f'{md(full[-1]["d"], "zh")} 淨流量', f'{md(full[-1]["d"], "en")} net flow', musd(full[-1]['musd'], 'zh'), musd(full[-1]['musd'], 'en')),
          S(f'7 個交易日（至 {md(full[-1]["d"], "zh")}）', f'7 trading days to {md(full[-1]["d"], "en")}', musd(sum(r['musd'] for r in s7), 'zh'), musd(sum(r['musd'] for r in s7), 'en'))]
    st.append(S(f'{md(pr["d"], "zh")} 暫定', f'{md(pr["d"], "en")} preliminary', musd(pr['musd'], 'zh'), musd(pr['musd'], 'en')) if pr else
              S('連續同方向', 'Same-direction run', *_etf_run(full)))
    return dict(kind='line', name=T('美國現貨比特幣 ETF 淨流量', 'US spot bitcoin ETF net flows'), sub=T('每個交易日合計淨流入／流出（百萬美元）；淡色是暫定值', 'Daily net flows across all funds ($M); the lighter bar is preliminary'),
                series=[dict(name=T('淨流量', 'Net flow'), rows=[(dn(r['d']), r['musd'], r.get('partial')) for r in rows], bars=True, signed=True)],
                refs=[dict(y=0)], yf=lambda v: f'{v:,.0f}', src='The Block' + ('（暫定：Farside、SoSoValue）' if pr else ''), asof=rows[-1]['d'], stats=st)


def _etf_run(full):
    n, sg = 0, full[-1]['musd'] >= 0
    for r in reversed(full):
        if (r['musd'] >= 0) != sg: break
        n += 1
    return (f'{"流入" if sg else "流出"} {n} 天', f'{n} days of {"inflows" if sg else "outflows"}')


def c_sthpnl(L, end):
    p = g(L, 'onchain.sth_pnl')
    return dict(kind='line', name=T('短期持有者實現獲利與虧損', 'Short-term holder realized profit and loss'), sub=T('短期持有者每天賣出時實現的獲利、虧損（顆，已平滑）', 'Profit and loss short-term holders realized on coins sold (BTC, smoothed)'),
                series=[dict(name=T('實現獲利', 'Realized profit'), rows=[(r[0], r[1]) for r in p['rows'] if r[1] is not None], color=UP, width=6),
                        dict(name=T('實現虧損', 'Realized loss'), rows=[(r[0], r[2]) for r in p['rows'] if r[2] is not None], color=RED, width=6)],
                yf=lambda v: f'{v / 1e3:,.0f}K' if v >= 1e3 else f'{v:,.0f}', src='CheckOnChain', asof=p['date'],
                stats=[S(f'獲利（{md(p["date"], "zh")}）', f'Profit ({md(p["date"], "en")})', btc(p['profit'], 'zh'), btc(p['profit'], 'en')),
                       S('虧損', 'Loss', btc(p['loss'], 'zh'), btc(p['loss'], 'en')), S('獲利 ÷ 虧損', 'Profit ÷ loss', f'{p["ratio"]:.2f}')])


def c_vol(L, end):
    rows = g(L, 'deriv.viz.vol.rows') or []; r = last(rows)
    return dict(kind='line', name=T('隱含波動與實際波動', 'Implied vs realized volatility'), sub=T('DVOL（選擇權隱含波動）與 30 日實際波動（年化 %）', 'DVOL (options-implied) and 30-day realized volatility (annualized %)'),
                series=[dict(name=T('DVOL', 'DVOL'), rows=[(x[0], x[1]) for x in rows if x[1] is not None], color=S1, width=6),
                        dict(name=T('RV30', 'RV30'), rows=[(x[0], x[2]) for x in rows if x[2] is not None], color=S2, width=6)],
                yf=lambda v: f'{v:.0f}', src='Deribit · Kraken', asof=ds(r[0]),
                stats=[S('DVOL', 'DVOL', f'{r[1]:.1f}'), S('RV30', 'RV30', f'{r[2]:.1f}'), S('IV − RV30', 'IV − RV30', ('+' if r[1] >= r[2] else '−') + f'{abs(r[1] - r[2]):.1f}')])


def c_npl(L, end):
    n = g(L, 'onchain.npl')
    return dict(kind='line', name=T('每日淨實現損益', 'Daily net realized profit/loss'), sub=T('全網當天賣出的幣：實現獲利 − 實現虧損（百萬美元）', 'Network-wide realized profit minus realized loss on coins moved ($M)'),
                series=[dict(name=T('淨實現損益', 'Net realized P/L'), rows=[(r[0], r[2]) for r in n['rows'] if r[2] is not None], bars=True, signed=True)],
                refs=[dict(y=0)], yf=lambda v: f'{v:,.0f}', src='CoinMetrics', asof=n['date'],
                stats=[S(f'最新（{md(n["date"], "zh")}）', f'Latest ({md(n["date"], "en")})', musd(n['usd_m'], 'zh'), musd(n['usd_m'], 'en')),
                       S('近 7 日', 'Past 7 days', musd(n['sum7_usd_m'], 'zh'), musd(n['sum7_usd_m'], 'en')),
                       S('前 7 日', 'Prior 7 days', musd(n['sum7_prev_usd_m'], 'zh'), musd(n['sum7_prev_usd_m'], 'en'))])


def _series_meta(chart):
    return next((s for s in SERIES if s[5] == chart), None)


def _fmt(v, f, lang):
    if f == 'btc': return btc(v, lang)
    if f == 'musd': return musd(v, lang)
    if f == 'int': return btc(v, lang)
    return F(v, f, lang)


def c_generic(L, end, chart):
    """其他圖：鏈上指標（oc-*）讀 onchain.viz，其餘用 signals.SERIES 的取值函式；只畫近一年一條線。"""
    m = _series_meta(chart)
    if not m: return None
    key, zh, en, th, page, _, get, f, *_ = m
    vz = g(L, 'onchain.viz.' + chart[3:]) if chart.startswith('oc-') else None
    rows = sorted(get(L)); rows = tail(rows, 365, rows[-1][0]) if rows else []
    if len(rows) < 20: return None
    x, v = rows[-1]; refs = []
    ref = (vz or {}).get('ref') or {}
    if ref.get('kind') == 'one': refs.append(dict(y=1, label=T('1', '1')))
    elif ref.get('kind') == 'top2025': refs.append(dict(y=ref['y'], label=T('2025 年高點時', 'At the 2025 top')))
    p30 = next((r for r in reversed(rows) if r[0] <= x - 30), None)
    nf = lambda w: _fmt(w, f, 'en').replace(' BTC', '')
    st = [S(f'最新（{md(ds(x), "zh")}）', f'Latest ({md(ds(x), "en")})', _fmt(v, f, 'zh'), _fmt(v, f, 'en'))]
    if p30: st.append(S(f'30 天前（{md(ds(p30[0]), "zh")}）', f'30 days ago ({md(ds(p30[0]), "en")})', _fmt(p30[1], f, 'zh'), _fmt(p30[1], f, 'en')))
    lo, hi = min(rows, key=lambda r: r[1]), max(rows, key=lambda r: r[1])
    st.append(S('一年區間', '1-year range', f'{_fmt(lo[1], f, "zh")} – {_fmt(hi[1], f, "zh")}', f'{nf(lo[1])} – {nf(hi[1])}'))
    return dict(kind='line', name=T(zh, en), sub=T('近一年', 'Past year'), series=[dict(name=T(zh, en), rows=rows, color=S1, width=6)], refs=refs,
                yf=lambda w: nf(w), src='bitcoin-data' if chart.startswith('oc-') else GSRC.get(chart, 'Daybreak'), asof=ds(x), stats=st)


GSRC = {'profit': 'bitcoin-data', 'rcliq': 'CoinMetrics'}
CHARTS = {'ov-px': c_px, 'cost': c_cost, 'cohort': c_cohort, 'cbp': c_cbp, 'sopr': c_sopr, 'stab': c_stab, 'etf': c_etf,
          'sthpnl': c_sthpnl, 'vol': c_vol, 'npl': c_npl}


def spec(L, chart):
    if not chart or SKIP_CHART.match(chart): return None
    end = dn(g(L, 'meta.bar_date'))
    try: return CHARTS[chart](L, end) if chart in CHARTS else c_generic(L, end, chart)
    except Exception as e:   # 資料缺欄位就不推這張，不讓整個流程失敗
        print('skip chart', chart, repr(e), file=sys.stderr); return None


# ---------- 挑圖 ----------
def load(name):
    try: return json.load(open(P('data', name)))
    except (FileNotFoundError, ValueError): return None


def candidates(L, notes=None, notes_en=None):
    """候選圖（依序）：當期 findings 的圖，再來是 signals 依分數。每張附挑選理由、相關異動、圖上數字。"""
    bar = g(L, 'meta.bar_date'); sig = g(L, 'signals.items') or []
    by_chart = {}
    for s in sig:
        if s.get('page') == 'exit' or s.get('key') in SKIP_KEY or not s.get('chart'): continue
        by_chart.setdefault(s['chart'], []).append(s)
    out, seen = [], set()

    def add(chart, why, finding=None):
        if chart in seen: return
        sp = spec(L, chart)
        if not sp: return
        seen.add(chart); ss = by_chart.get(chart, [])
        out.append(dict(id=chart, why=why, finding=finding, title=ss[0]['title'] if ss else sp['name'], name=sp['name'],
                        signals=[dict(id=s['id'], title=s['title'], fig=s.get('fig'), ctx=s.get('ctx')) for s in ss],
                        stats=[dict(label=x['label'], value=x['value']) for x in sp['stats']], asof=sp['asof'], src=sp['src']))

    if notes and notes.get('date') == bar:
        fe = {f.get('id'): f for f in (notes_en or {}).get('findings') or []} if (notes_en or {}).get('date') == bar else {}
        for f in notes.get('findings') or []:
            if any(k in SKIP_KEY for k in (f.get('signals') or [])) and f.get('module') == 'exit': continue
            add(f.get('chart'), T(f'今日發現：{f.get("title", "")}', f'Today\'s finding: {(fe.get(f.get("id")) or {}).get("title") or f.get("id")}'), f.get('id'))
    for s in sorted((s for ss in by_chart.values() for s in ss), key=lambda s: -s.get('score', 0)):
        add(s['chart'], T(f'異動：{s["title"]["zh"]}', f'Signal: {s["title"]["en"]}'))
    if not out: add('ov-px', T('今天沒有明顯異動，推價格走勢', 'No notable signal today; price chart'))
    return out[:MAX_CAND]


def plan(L):
    notes, notes_en = load('notes.json'), load('notes.en.json')
    c = candidates(L, notes, notes_en)
    return dict(date=g(L, 'meta.bar_date'), notes_date=(notes or {}).get('date'), pick=[x['id'] for x in c[:MAX_PICKS]], candidates=c,
                note='每日任務：從 candidates 挑 1–3 張（預設 pick），寫 data/picks.json；解說只引用 signals 的 fig 與 stats 的數字，不改數字、不寫出場框架')


# ---------- 檢查 picks.json（每日任務提交前跑） ----------
BAN = re.compile(r'出場|避險|階梯|觸發|減碼|加碼|停損|該買|該賣|買進|賣出訊號|目標價|0\.75 線|框架|exit|hedg|ladder|trigger|price target|take profit|stop.?loss|\bbuy\b|\bsell\b', re.I)
NUMS = lambda t: {n.replace(',', '').lstrip('0') or '0' for n in re.findall(r'\d[\d,]*(?:\.\d+)?', t)}


def check(L):
    """picks.json：日期是當期、1–3 張、id 都能出圖、中英文解說都有且 ≤ 280（X 算法）、不談出場框架與買賣、
    解說裡的每個數字都出現在 plan 的資料（異動、圖上數字）或當期 notes（中英文）裡。回傳問題清單。"""
    from x_len import weight
    pk = load('picks.json'); bar = g(L, 'meta.bar_date'); errs = []
    if not pk: return ['data/picks.json 不存在或不是合法 JSON']
    if pk.get('date') != bar: errs.append(f'date {pk.get("date")} ≠ bar_date {bar}')
    ps = pk.get('picks') or []
    if not 1 <= len(ps) <= MAX_PICKS: errs.append(f'picks 要 1–{MAX_PICKS} 張，現在 {len(ps)}')
    cand = {c['id']: c for c in candidates(L, load('notes.json'), load('notes.en.json'))}
    src = NUMS(json.dumps([cand, load('notes.json'), load('notes.en.json')], ensure_ascii=False))
    for p in ps:
        i = p.get('id')
        if not spec(L, i): errs.append(f'{i}: 沒有這張圖或資料不足'); continue
        if i not in cand: errs.append(f'{i}: 不在今天的候選裡（plan 的 candidates）')
        for k in ('chart', 'chart_en'):
            want = f'data/picks/{i}.png' if k == 'chart' else f'data/picks/{i}-en.png'
            if p.get(k) != want: errs.append(f'{i}: {k} 應為 {want}')
        for lang in ('zh', 'en'):
            for tk in ('title_' + lang,):   # 可選的圖上標題：同樣不談框架、數字查得到
                tt = p.get(tk)
                if tt and BAN.search(tt): errs.append(f'{i}.{tk}: 提到出場框架或買賣（{BAN.search(tt).group(0)}）')
                if tt and NUMS(tt) - src: errs.append(f'{i}.{tk}: 這些數字找不到出處：{", ".join(sorted(NUMS(tt) - src))}')
            t = p.get(lang) or ''
            if not t: errs.append(f'{i}.{lang}: 空白'); continue
            if weight(t) > 280: errs.append(f'{i}.{lang}: {weight(t)}/280 超過')
            if BAN.search(t): errs.append(f'{i}.{lang}: 提到出場框架或買賣（{BAN.search(t).group(0)}）')
            if lang == 'en' and re.search(r'[一-鿿]', t): errs.append(f'{i}.en: 有中文字')
            miss = sorted(NUMS(t) - src)
            if miss: errs.append(f'{i}.{lang}: 這些數字在資料與當期 notes 裡找不到：{", ".join(miss)}')
    return errs


# ---------- 出圖 ----------
W, H, M, K = 2160, 2700, 128, 2      # 以 2 倍畫，最後縮成 1080×1350（線條與文字邊緣才平滑）
WD = {'zh': '一二三四五六日', 'en': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']}
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def tint(c, a):
    """顏色和紙色混合（a＝顏色比例），避免用透明圖層。"""
    h = lambda s: [int(s[i:i + 2], 16) for i in (1, 3, 5)]
    return tuple(round(x * a + y * (1 - a)) for x, y in zip(h(c), h(PAPER)))


def nice(lo, hi, n=5):
    import math
    span = hi - lo or abs(hi) or 1; raw = span / n; e = 10 ** math.floor(math.log10(raw))
    step = next(m * e for m in (1, 2, 2.5, 5, 10) if m * e >= raw)
    t = math.floor(lo / step) * step; out = []
    while t <= hi + step * 1e-9:
        if t >= lo - step * 1e-9: out.append(0.0 if abs(t) < step * 1e-6 else round(t, 10))
        t += step
    return out


def dashed(d, x0, x1, y, color, w=3, dash=18, gap=12):
    x = x0
    while x < x1:
        d.line([x, y, min(x + dash, x1), y], fill=color, width=w); x += dash + gap


def draw_line_chart(d, box, sp, lang, Fn):
    x0, y0, x1, y1 = box; px1 = x1 - 150            # 右側留給 y 軸刻度
    ser = sp['series']; xs = [r[0] for s in ser for r in s['rows']]; ys = [r[1] for s in ser for r in s['rows']]
    ys += [r['y'] for r in sp.get('refs') or []]
    if any(s.get('bars') for s in ser): ys.append(0)
    xa, xb = min(xs), max(xs); ya, yb = min(ys), max(ys); pad = (yb - ya) * 0.08 or 1; ya, yb = ya - pad, yb + pad
    pb = y1 - 70                                   # 下方留給 x 軸日期
    X = lambda x: x0 + (x - xa) / ((xb - xa) or 1) * (px1 - x0)
    Y = lambda y: pb - (y - ya) / ((yb - ya) or 1) * (pb - y0)
    tf = Fn['mono'](34, 500)
    for t in nice(ya, yb):
        d.line([x0, Y(t), px1, Y(t)], fill=LINE, width=2)
        d.text((px1 + 18, Y(t)), sp['yf'](t).replace('-', '−'), font=tf, fill=INK3, anchor='lm')
    # x 軸：依跨度每 1／2／3／6 個月一格，1 月標年份
    a, b = dt.date(1970, 1, 1) + dt.timedelta(days=xa), dt.date(1970, 1, 1) + dt.timedelta(days=xb)
    step = 1 if (xb - xa) <= 200 else 2 if (xb - xa) <= 420 else 3 if (xb - xa) <= 800 else 6
    m = dt.date(a.year, a.month, 1)
    xf = Fn['cjk'](32, 500) if lang == 'zh' else Fn['mono'](32, 500)
    while m <= b:
        if m >= a and (m.month - 1) % step == 0:
            xx = X(dn(m.isoformat())); d.line([xx, pb, xx, pb + 14], fill=INK3, width=2)
            lab = str(m.year) if m.month == 1 else (f'{m.month}月' if lang == 'zh' else MON[m.month - 1])
            d.text((xx, pb + 24), lab, font=xf, fill=INK if m.month == 1 else INK3, anchor='mt')
        m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    d.line([x0, pb, px1, pb], fill=INK, width=3)
    for r in sp.get('refs') or []:
        if r['y'] == 0: d.line([x0, Y(0), px1, Y(0)], fill=INK, width=3)
        else: dashed(d, x0, px1, Y(r['y']), INK, 3)
        if r.get('label'): d.text((x0 + 8, Y(r['y']) - 10), r['label'][lang], font=Fn['cjk'](30, 700) if lang == 'zh' else Fn['mono'](30, 700), fill=INK, anchor='lb')
    for s in ser:
        rows = s['rows']
        if s.get('bars'):
            bw = max(3, (px1 - x0) / ((xb - xa) or 1) * 0.72)
            for r in rows:
                c = s.get('color') or (UP if r[1] >= 0 else RED)
                if s.get('faint'): c = tint(c, 0.35)
                if len(r) > 2 and r[2]: c = tint(c, 0.35)   # 暫定值
                d.rectangle([X(r[0]) - bw / 2, min(Y(r[1]), Y(0)), X(r[0]) + bw / 2, max(Y(r[1]), Y(0))], fill=c)
            continue
        pts = [(X(x), Y(y)) for x, y in rows]
        if s.get('area'): d.polygon(pts + [(pts[-1][0], pb), (pts[0][0], pb)], fill=tint(s['color'], 0.12))
        d.line(pts, fill=s['color'], width=s.get('width', 6), joint='curve')
        lx, ly = pts[-1]; rr = s.get('width', 6) + 6
        d.ellipse([lx - rr, ly - rr, lx + rr, ly + rr], fill=s['color'], outline=PAPER, width=4)


def draw_cohort(d, box, sp, lang, Fn):
    x0, y0, x1, y1 = box; rows = sp['rows']; w = sp['width']; px = sp['price']
    mid = (x0 + x1) / 2; lab_w = 170; half = (x1 - x0 - lab_w) / 2 - 210   # 左右同一比例；外側留 200 給最厚一格的數字
    mx = max(max(r[1], r[2]) for r in rows) or 1
    head = 64; rh = (y1 - y0 - head) / len(rows)
    hf = Fn['cjk'](34, 900) if lang == 'zh' else Fn['mono'](30, 800)
    d.text((mid - lab_w / 2 - 10, y0 + 20), '← 短期持有者' if lang == 'zh' else '← SHORT-TERM', font=hf, fill=S2, anchor='rm')
    d.text((mid + lab_w / 2 + 10, y0 + 20), '長期持有者 →' if lang == 'zh' else 'LONG-TERM →', font=hf, fill=S1, anchor='lm')
    lf = Fn['mono'](28, 500); vf = Fn['cjk'](32, 900) if lang == 'zh' else Fn['mono'](30, 800)
    top = max(rows, key=lambda r: r[1]); labs = []
    for i, r in enumerate(reversed(rows)):        # 高價在上
        yt = y0 + head + i * rh; yc = yt + rh / 2; bh = rh * 0.78
        labs.append((mid, yc, f'{r[0] // 1000}K', lf, INK3, 'mm'))
        ls = r[1] / mx * half; rl = r[2] / mx * half
        if ls: d.rectangle([mid - lab_w / 2 - ls, yc - bh / 2, mid - lab_w / 2, yc + bh / 2], fill=S2 if r is top else tint(S2, 0.75))
        if rl: d.rectangle([mid + lab_w / 2, yc - bh / 2, mid + lab_w / 2 + rl, yc + bh / 2], fill=tint(S1, 0.75))
        if r is top: labs.append((mid - lab_w / 2 - ls - 14, yc, btc(r[1], lang), vf, S2, 'rm'))
    lo = rows[0][0]; hi = rows[-1][0] + w
    yp = y0 + head + (hi - px) / (hi - lo) * (y1 - y0 - head)
    d.line([x0, yp, x1, yp], fill=RED, width=5)
    for x, y, t, f, c, an in labs:                # 標籤畫在收盤線上面，墊紙色底
        bb = d.textbbox((x, y), t, font=f, anchor=an); d.rectangle([bb[0] - 6, bb[1] - 4, bb[2] + 6, bb[3] + 4], fill=PAPER)
        d.text((x, y), t, font=f, fill=c, anchor=an)
    d.text((x1, yp - 10), (f'收盤 {usd(px)}' if lang == 'zh' else f'Close {usd(px)}'), font=Fn['cjk'](34, 900) if lang == 'zh' else Fn['mono'](32, 800), fill=RED, anchor='rb')

def card(L, notes, sp, title, lang, Fn, out, tag=None):
    from PIL import Image, ImageDraw
    import share_card as SC
    img = Image.new('RGB', (W, H), PAPER); d = ImageDraw.Draw(img)
    d.rectangle([M, 104, W - M, 116], fill=INK)
    tag = (tag or {}).get(lang, '今日圖表' if lang == 'zh' else 'CHART OF THE DAY')   # 長文配圖可換標籤或給空字串不畫（ops/articles/charts.py）
    tf = Fn['cjk'](52, 900) if lang == 'zh' else Fn['mono'](44, 800)
    if tag: tw = d.textlength(tag, font=tf); d.rectangle([M, 152, M + tw + 56, 232], fill=RED); d.text((M + 28, 192), tag, font=tf, fill='#FFFFFF', anchor='lm')
    else: tw = -96
    bd = dt.date.fromisoformat(g(L, 'meta.bar_date')); ed = (notes or {}).get('edition', 0) if (notes or {}).get('date') == g(L, 'meta.bar_date') else 0
    meta = (f'DAYBREAK No.{ed:03d}   ' if ed else 'DAYBREAK   ') + (f'{bd:%Y.%m.%d}（{WD["zh"][bd.weekday()]}）收盤版' if lang == 'zh' else f'{WD["en"][bd.weekday()]} {bd:%b %d, %Y} close')
    d.text((M + tw + 96, 192), meta, font=Fn['cjk'](38, 500) if lang == 'zh' else Fn['mono'](38, 500), fill=INK3, anchor='lm')
    # 標題：自動縮字，最多 3 行；數字標紅（規則同分享圖）
    for size in range(116, 64, -4):
        hf = Fn['head'](size); lines = SC.wrap(title, hf, W - 2 * M)
        if len(lines) <= 3 and len(lines) * int(size * 1.26) <= 440: break
    for i in range(len(lines) - 1):   # 左括號不留在行尾
        while lines[i] and lines[i][-1][0].strip() in ('（', '(', '「', '“'): lines[i + 1].insert(0, lines[i].pop())
    y, lh = 280, int(size * 1.26)
    for ln in lines[:3]:
        x = M - (size * 0.5 if ln and ln[0][0] in ('（', '「') else 0)   # 全形左括號字身左半是空白，行首往左移齊邊
        for a, red in ln:
            d.text((x, y), a, font=hf, fill=RED if red else INK); x += hf.getlength(a)
        y += lh
    # 圖名與說明
    y += 24
    nf = Fn['cjk'](48, 900) if lang == 'zh' else Fn['mono'](42, 800)
    d.text((M, y), sp['name'][lang] if lang == 'zh' else sp['name'][lang].upper(), font=nf, fill=INK); y += 72
    sf = Fn['cjk'](36, 500) if lang == 'zh' else Fn['mono'](32, 500)
    for ln in SC.wrap(sp['sub'][lang], sf, W - 2 * M)[:2]:
        d.text((M, y), ''.join(a for a, _ in ln), font=sf, fill=INK3); y += 52
    # 圖
    cb = 2150; box = (M, y + 40, W - M, cb)
    if sp['kind'] == 'cohort': draw_cohort(d, box, sp, lang, Fn)
    else: draw_line_chart(d, box, sp, lang, Fn)
    # 圖例與來源
    ly = cb + 44; x = M; lf = Fn['cjk'](32, 700) if lang == 'zh' else Fn['mono'](30, 700)
    ser = [s for s in sp.get('series') or [] if s.get('color') and not s.get('faint')]
    if len(ser) > 1:
        for s in ser:
            d.rectangle([x, ly - 6, x + 40, ly + 6], fill=s['color']); x += 56
            d.text((x, ly), s['name'][lang], font=lf, fill=INK, anchor='lm'); x += d.textlength(s['name'][lang], font=lf) + 44
    src = (f'資料：{sp["src"]} · 截至 {sp["asof"].replace("-", "/")}' if lang == 'zh' else f'Data: {sp["src"]} · as of {sp["asof"]}')
    if lang == 'en': src = re.sub(r'（[^）]*）', '', src).replace('（推算）', ' (estimate)')
    d.text((W - M, ly), src, font=Fn['cjk'](30, 500) if lang == 'zh' else Fn['mono'](28, 500), fill=INK3, anchor='rm')
    # 底部三格（同分享圖）
    top = 2240; d.rectangle([M, top, W - M, top + 4], fill=INK); n = len(sp['stats']); cw = (W - 2 * M) / n
    for i, st in enumerate(sp['stats']):
        x = M + i * cw + (0 if i == 0 else 40)
        if i: d.line([M + i * cw, top + 40, M + i * cw, top + 230], fill=LINE, width=2)
        d.text((x, top + 52), st['label'][lang], font=Fn['mono'](30, 500) if lang == 'en' else Fn['cjk'](34, 500), fill=INK3)
        v = st['value'][lang]; vf = None
        for vs in (84, 76, 68, 60, 52, 46):
            vf = Fn['cjk'](int(vs * 0.82), 900) if re.search(r'[一-鿿]', v) else Fn['num'](vs)
            if d.textlength(v, font=vf) <= cw - 56: break
        d.text((x, top + 112), v, font=vf, fill=RED if v.startswith('−') and ' – ' not in v else INK)   # 負數標紅（區間不標）
    # 頁尾（同分享圖）
    fy = H - 88; d.line([M, fy - 44, W - M, fy - 44], fill=LINE, width=2)
    d.arc([M, fy - 28, M + 56, fy + 28], 180, 360, fill=RED, width=8); d.line([M - 8, fy, M + 64, fy], fill=INK, width=8)
    d.text((M + 88, fy), '破曉 DAYBREAK' if lang == 'zh' else 'DAYBREAK', font=Fn['cjk'](40, 900) if lang == 'zh' else Fn['mono'](40, 800), fill=INK, anchor='lm')
    d.text((W - M, fy), 'X @songpu717', font=Fn['mono'](38), fill=INK3, anchor='rm')
    img.resize((W // K, H // K), Image.LANCZOS).save(out, optimize=True)
    print('wrote', os.path.relpath(out, ROOT), 'title lines', len(lines), 'size', size)


def render(L, fonts_dir):
    import share_card as SC
    Fn = SC.fonts(fonts_dir); bar = g(L, 'meta.bar_date')
    notes, notes_en, pk = load('notes.json'), load('notes.en.json'), load('picks.json')
    if pk and pk.get('date') == bar and pk.get('picks'):
        items = [(p['id'], {'zh': p.get('title_zh'), 'en': p.get('title_en')}) for p in pk['picks'][:MAX_PICKS]]
        print('picks.json', bar, [i for i, _ in items])
    else:
        c = candidates(L, notes, notes_en)[:MAX_PICKS]; items = [(x['id'], {}) for x in c]
        print('picks.json 不存在或不是當期，自動挑：', [i for i, _ in items])
    od = P('data', 'picks'); os.makedirs(od, exist_ok=True); keep = {'index.json', 'history.json'}; done = []
    cand = {x['id']: x for x in candidates(L, notes, notes_en)}
    for cid, tt in items:
        sp = spec(L, cid)
        if not sp: print('skip', cid, '（沒有這張圖或資料不足）'); continue
        dflt = (cand.get(cid) or {}).get('title') or sp['name']
        for lang, fn in (('zh', f'{cid}.png'), ('en', f'{cid}-en.png')):
            card(L, notes if lang == 'zh' else notes_en, sp, tt.get(lang) or dflt[lang], lang, Fn, os.path.join(od, fn)); keep.add(fn)
        done.append(dict(id=cid, chart=f'data/picks/{cid}.png', chart_en=f'data/picks/{cid}-en.png', name=sp['name']))
    # 這次畫了哪些圖（發文小幫手在 picks.json 不是當期時讀這份，只顯示圖、沒有解說）
    json.dump(dict(date=bar, captions=bool(pk and pk.get('date') == bar and pk.get('picks')), picks=done), open(os.path.join(od, 'index.json'), 'w'), ensure_ascii=False, indent=1)
    for fn in os.listdir(od):   # 清掉前幾天、今天沒選的圖
        if fn not in keep: os.remove(os.path.join(od, fn)); print('removed', fn)



# ======================================================================================
# 第二版（2026-11-06 使用者：「每日推薦圖表沒什麼意義」）：一天一張、網站原圖、回答一個問題
#   原因：舊版三天都推同三張（短期持有者成本、籌碼、Coinbase 溢價），解說只是把數字念一遍，圖是重畫的簡化版，和日報講同一件事。
#   新版：① 每天只推 1 張，從網站的面板裡挑（PANELS），截網站深色原圖（ops/post/site_shot.py clean 模式），上方加一句問句標題；
#        ② 最近 7 天推過的不再推（data/picks/history.json），長貼文用過的也避開（data/longposts.json 的 charts 欄，可選）；
#        ③ 帶出場框架線、或本身是預測的面板不推（SKIP_PANELS）；
#        ④ 解說三件事：現在的讀值、過去同樣情況之後怎樣（勝率照實寫）、這代表什麼。不寫買賣點、目標價。
#   plan 列出候選面板：今天有異動的排前面（附異動的白話含意與歷史對照），其餘面板也列出來，讓每日任務依「讀者今天在問什麼」挑。
#   舊版的 CHARTS／card() 留著：長文配圖（ops/articles/charts.py）還在用；截圖失敗時也拿來當備案。
# ======================================================================================
PICKS_V2 = 1
RECENT_DAYS = 7
# 網站面板：連結 key（#page/key）→ 名稱、截圖用的圖 id、讀值在 latest.json 的位置、對應的異動 chart id、截圖失敗時的舊版圖
#   2026-11-08 內容重組後有幾張圖換了版面（deriv/sx、deriv/conc → 價格／鏈上；onchain/ad、dmd、capflow、grad → 資金），鍵維持原樣：截圖是桌面寬度、每版都畫，選擇器照樣找得到，網站的跳轉也跟著圖走
PANELS = {
    'cycle/rup':      dict(zh='相對未實現獲利：地板', en='Relative unrealized profit: the floor', sel='#c-rup', data=['onchain.rup']),
    'cycle/cyccmp':   dict(zh='和前幾輪比：頂部之後', en='Versus past cycles: after the top', sel='#c-cyccmp', data=['cycle.cycle_cmp']),
    'cycle/pl':       dict(zh='冪律：價格 ÷ 合理價', en='Power law: price ÷ fair value', sel='#c-pl', data=['cycle.powerlaw']),
    # 2026-11-06 PR #56 新增的 Bitview 六項（都沒有出場框架線；高檔區／低檔區是歷史百分位，NUPL 的分區是情緒階段，只是讀值）
    'cycle/hnupl':    dict(zh='長短期持有者 NUPL', en='STH and LTH NUPL', sel='#c-hnupl', data=['onchain.hnupl']),
    'cycle/aviv':     dict(zh='AVIV：價格 ÷ 真實市場均價', en='AVIV: price ÷ true market mean', sel='#c-aviv', data=['onchain.aviv']),
    'cycle/rrisk':    dict(zh='儲備風險', en='Reserve risk', sel='#c-rrisk', data=['onchain.rrisk']),
    'onchain/ssr':    dict(zh='賣方風險比', en='Sell-side risk ratio', sel='#c-ssr', data=['onchain.ssr']),
    'onchain/agepl':  dict(zh='依持有時間的實現獲利／虧損', en='Realized profit/loss by holding age', sel='#c-agepl', data=['onchain.agepl']),
    'onchain/dorm':   dict(zh='Dormancy 與 Liveliness', en='Dormancy and Liveliness', sel='#c-dorm', data=['onchain.dorm']),
    # 2026-11-06 PR #58 新增（韓國溢價的 5% 線是「偏熱」參考線，不是出場框架）
    'onchain/npl365': dict(zh='一年累計淨實現損益（顆）', en='1-year net realized profit/loss (BTC)', sel='#c-npl365', data=['onchain.npl365']),
    'onchain/sthd': dict(zh='短期持有者供給 90 天變化', en='Short-term holder supply, 90-day change', sel='#c-sthd', data=['onchain.sthd']),
    'onchain/dmd':    dict(zh='現貨 vs 永續需求', en='Spot vs perp demand', sel='#c-dmd', data=['onchain.dmd']),
    'flows/etfcost':  dict(zh='ETF 持有者成本', en='ETF holder cost basis', sel='#c-etfcost', data=['flows.etfcost']),
    'flows/exflow':   dict(zh='交易所淨流量', en='Exchange net flows', sel='#c-exflow', data=['flows.exflow']),
    'flows/kp':       dict(zh='韓國溢價', en='Korea premium', sel='#c-kp', data=['flows.kp']),
    'cycle/regime':   dict(zh='週線多空分數', en='Weekly regime score', sel='#c-regime', data=['cycle.regime']),
    'cycle/dawn':     dict(zh='晨昏指數', en='Dawn–Dusk Index', sel='#c-dawn', data=['cycle.dawn']),
    'cycle/tmh':      dict(zh='Tidemark 歷史：頂部與底部訊號', en='Tidemark history: top and bottom signals', sel='#c-tmh', data=['cycle.tidemark.hist']),
    'onchain/quant':  dict(zh='供給分位成本線', en='Supply quantile cost lines', sel='#c-quant', data=['onchain.quant']),
    'onchain/urpd':   dict(zh='籌碼分布（URPD）', en='Supply distribution (URPD)', sel='#c-urpd', html=1, data=['chips.viz']),
    'onchain/sthband': dict(zh='短期持有者成本帶', en='Short-term holder cost bands', sel='#c-sthband', data=['onchain.sth_bands', 'cycle.levels'], sig=['cost', 'ev-sth'], old='cost'),
    'onchain/agecost': dict(zh='依持有時間的持幣成本', en='Cost basis by holding age', sel='#c-agecost', data=['cycle.age_cost']),
    'onchain/sopr':   dict(zh='短期持有者認賠賣壓（STH-SOPR）', en='Short-term holder SOPR', sel='#c-sopr', data=['chips.viz'], sig=['sopr'], old='sopr'),
    'onchain/sthpnl': dict(zh='短期持有者實現獲利與虧損', en='Short-term holder realized profit and loss', sel='#c-sthpnl', data=['onchain.sth_pnl'], sig=['sthpnl'], old='sthpnl'),
    'onchain/sthsig': dict(zh='短期持有者集中止盈與認賠', en='Short-term holder profit-taking and capitulation spikes', sel='#c-sthsig', data=['onchain.sthsig'], sig=['sthsig']),   # 2026-11-11
    'onchain/npl':    dict(zh='每日淨實現損益', en='Daily net realized profit/loss', sel='#c-npl', data=['onchain.npl'], sig=['npl'], old='npl'),
    'onchain/rpl':    dict(zh='實現獲利 ÷ 實現虧損', en='Realized profit ÷ realized loss', sel='#c-rpl', data=['onchain.rpl']),
    'onchain/rloss':  dict(zh='實現虧損：峰值背離', en='Realized loss: peak divergence', sel='#c-rloss', data=['onchain.rloss']),
    'onchain/sec':    dict(zh='賣方衰竭常數', en='Seller exhaustion constant', sel='#c-sec', data=['onchain.sec']),
    'onchain/mom':    dict(zh='鏈上勢能', en='On-chain momentum', sel='#c-mom', data=['onchain.mom']),
    'onchain/cohort': dict(zh='長短期持有者籌碼', en='Short- and long-term holder supply', sel='#c-cohort', html=1, data=['chips.cohort'], sig=['cohort'], old='cohort'),
    'onchain/lthc':   dict(zh='價格 × 長期持有者動向', en='Price × long-term holder flows', sel='#c-lthc', data=['onchain.lth_color']),
    'onchain/lsrchg': dict(zh='長短期持有者供給比：30 日變化', en='LTH/STH supply ratio: 30-day change', sel='#c-lsrchg', data=['onchain.lsrchg']),
    'onchain/lthloss': dict(zh='長期持有者虧損比例', en='Long-term holders in loss', sel='#c-lthloss', data=['onchain.lthloss', 'onchain.lthrl']),
    'onchain/ad':     dict(zh='表觀需求', en='Apparent demand', sel='#c-ad', data=['onchain.ad']),
    'onchain/capflow': dict(zh='循環資金流：投機 vs 長線', en='Capital rotation: speculative vs long-term', sel='#c-capflow', data=['onchain.capflow']),
    'onchain/grad':   dict(zh='資金與價格增量梯度', en='Capital vs price gradient', sel='#c-grad', data=['onchain.grad']),
    'onchain/whale':  dict(zh='鯨魚與大戶動向', en='Whales and large holders', sel='#c-whale', data=['onchain.whales']),
    'market/cd':      dict(zh='近 20 天 K 線', en='Last 20 daily candles', sel='#c-cd', data=['price.bar']),
    'market/long':    dict(zh='價格長期走勢', en='Long-term price', sel='#c-long', data=['cycle.tops', 'cycle.bottoms']),
    'market/levels':  dict(zh='成本線與均線', en='Cost lines and moving averages', sel='#c-levels', data=['cycle.levels'], sig=['cost', 'ov-px'], old='cost'),
    'market/mon':     dict(zh='月度報酬熱力表', en='Monthly returns heatmap', sel='#c-mon', data=['price.monthly']),   # 2026-11-08
    'flows/etf':      dict(zh='現貨 ETF 每日淨流量', en='Spot ETF daily net flows', sel='#c-etf', data=['flows.etf'], sig=['etf'], old='etf'),
    'flows/stab':     dict(zh='穩定幣總供給', en='Stablecoin supply', sel='#c-stab', data=['flows.stables'], sig=['stab'], old='stab'),
    'flows/pr-us':    dict(zh='三地溢價：買盤從哪裡來', en='Premiums: where the bid comes from', sel='#c-pr-us', data=['flows.premium3', 'flows.cb_premium'], sig=['pr-us', 'cbp'], old='cbp'),
    'flows/stkrel':   dict(zh='BTC 對美股', en='BTC vs US stocks', sel='#c-stkrel', data=['flows.btc_vs_stocks']),
    'flows/rcliq':    dict(zh='資金流入：實現市值 30 日變化', en='Capital inflow: realized cap 30-day change', sel='#c-rcliq', data=['flows.rc_liq'], sig=['rcliq'], old='rcliq'),
    'deriv/vol':      dict(zh='隱含波動 vs 實際波動', en='Implied vs realized volatility', sel='#c-vol', data=['deriv.dvol', 'deriv.samesource'], sig=['vol'], old='vol'),
    'deriv/basis':    dict(zh='期貨基差曲線', en='Futures basis curve', sel='#c-basis', data=['deriv.deriv']),
    'deriv/liq':      dict(zh='清算熱力圖（推算）', en='Liquidation heatmap (estimate)', sel='#c-liq', data=['deriv.liq_heat']),
    'deriv/lqv':      dict(zh='每日多空清算量', en='Daily long and short liquidations', sel='#c-lqv', data=['deriv.liq_vol']),
    'deriv/fh':       dict(zh='資金費率歷史', en='Funding rate history', sel='#c-fh', data=['deriv.fund_hist']),
    'deriv/oih':      dict(zh='全市場未平倉量', en='Total open interest', sel='#c-oih', data=['deriv.oi_hist']),
    'deriv/lsa':      dict(zh='多空帳戶比', en='Long/short account ratio', sel='#c-lsa', data=['deriv.ls_acct']),
    'deriv/tk':       dict(zh='現貨與永續的主動買賣（多交易所）', en='Spot vs perpetual taker flow (multi-exchange)', sel='#c-tk', data=['deriv.taker']),
    'deriv/conc':     dict(zh='籌碼結構與集中度', en='Supply structure and concentration', sel='#c-conc', data=['chips.conc_stats']),
    'deriv/sx':       dict(zh='賣壓累積與動能品質', en='Selling pressure and momentum quality', sel='#c-sx', data=['chips.stress']),   # 2026-11-07
    'deriv/ivt':      dict(zh='隱含波動率期限結構', en='Implied volatility term structure', sel='#c-ivt', data=['deriv.ivterm']),   # 2026-11-08
    'deriv/strike':   dict(zh='主要到期的履約價分布', en='Strikes at the main expiry', sel='#c-strike', data=['deriv.viz']),
    'deriv/gex':      dict(zh='選擇權 Gamma 曝險（推算）', en='Options gamma exposure (estimate)', sel='#c-gex', data=['deriv.gex']),
    'deriv/prem':     dict(zh='選擇權買方權利金差', en='Options buyer premium spread', sel='#c-prem', data=['deriv.prem']),
    'deriv/svd':      dict(zh='現貨主動買賣差（OKX）', en='Spot taker delta (OKX)', sel='#c-svd', data=['deriv.svd']),
}
# 不推的面板與原因（2026-11-06 依 voice.md：有出場框架線的圖不用）
SKIP_PANELS = {
    'cycle/p20': 'MVRV ÷ 前一輪高點：出場框架 0.75 線的來源',
    'onchain/profit': '短期持有者獲利比例：圖上有 97.5% 賣出線',
    'cycle/path': '長期路徑：四種走法是推估，不是資訊',
    'deriv/book': '掛單簿：只是快照，隔天就不一樣',
    'cycle/capeff': '每輪資金效率：是表格，截圖只截到空白（要用的話另外截整個面板）',
    'deriv/oi': '各到期未平倉：單看沒有故事，併在履約價分布裡講',
}
SIG_TO_PANEL = {}
for _k, _p in PANELS.items():
    SIG_TO_PANEL.setdefault(_k.split('/')[1], _k)
    for _c in _p.get('sig', []): SIG_TO_PANEL.setdefault(_c, _k)
slug = lambda pid: pid.replace('/', '-')


def _compact(o, depth=0):
    """latest.json 的一段讀值，去掉長序列，只留每日任務寫解說要用的數字與回測。"""
    if isinstance(o, dict):
        return {k: _compact(v, depth + 1) for k, v in o.items() if k not in ('rows', 'hours', 'series', 'heat', 'hr', 'grid', 'cells', 'z', 'hist_rows', 'px')}
    if isinstance(o, list):
        if len(o) > 6: return [_compact(x, depth + 1) for x in o[-4:]] + [f'…共 {len(o)} 筆，只列最後 4 筆']
        return [_compact(x, depth + 1) for x in o]
    return o


def recent_used(bar, days=RECENT_DAYS):
    """最近 days 天推過（history.json）或長貼文標了用過（longposts.json 的 charts）的面板 → {id: 日期}。"""
    out = {}
    try: d0 = dt.date.fromisoformat(bar) - dt.timedelta(days=days)
    except Exception: return out
    for h in (load('picks/history.json') or {}).get('items', []):
        if h.get('date', '') > d0.isoformat() and h.get('date', '') < bar: out.setdefault(h['id'], h['date'])
    lp = load('longposts.json') or {}
    for it in (lp.get('items') if isinstance(lp, dict) else lp) or []:
        for c in it.get('charts') or []:
            if (it.get('time') or '')[:10] > d0.isoformat(): out.setdefault(c, (it.get('time') or '')[:10])
    for u in (lp.get('used') if isinstance(lp, dict) else None) or []:   # 已發、已從 items 刪掉的長貼文
        if (u.get('date') or '') > d0.isoformat() and (u.get('date') or '') < bar:
            for c in u.get('charts') or []: out.setdefault(c, u['date'])
    return out


def candidates2(L, notes=None):
    """候選面板：今天有異動的排前面（依分數），其餘照目錄順序。每張附異動（含白話含意、過去同樣情況）與 latest.json 的讀值。"""
    bar = g(L, 'meta.bar_date'); used = recent_used(bar)
    sig = [s for s in (g(L, 'signals.items') or []) + (g(L, 'signals.more') or []) if isinstance(s, dict)]
    by = {}
    for s in sorted(sig, key=lambda s: -(s.get('score') or 0)):
        if s.get('page') == 'exit' or s.get('key') in SKIP_KEY: continue
        k = SIG_TO_PANEL.get(s.get('chart') or '')
        if k: by.setdefault(k, []).append(s)
    fchart = {}
    if notes and notes.get('date') == bar:
        for f in notes.get('findings') or []:
            k = SIG_TO_PANEL.get(f.get('chart') or '')
            if k: fchart.setdefault(k, f.get('title'))
    order = sorted(PANELS, key=lambda k: (-(by[k][0].get('score') or 0) if k in by else (0 if k in fchart else 1), list(PANELS).index(k)))
    out = []
    for k in order:
        p = PANELS[k]
        out.append(dict(id=k, name=T(p['zh'], p['en']), link=f'https://north7.github.io/daybreak/#{k}',
                        used=used.get(k), finding=fchart.get(k),
                        signals=[dict(title=s.get('title'), fig=s.get('fig'), means=s.get('means'), hist=s.get('hist'), score=s.get('score')) for s in by.get(k, [])[:3]],
                        data={path: _compact(g(L, path)) for path in p.get('data', []) if g(L, path) is not None}))
    return out


def plan2(L):
    notes = load('notes.json'); c = candidates2(L, notes)
    ok = [x for x in c if not x['used']]
    # 2026-11-08：運營那邊可以先寫好當天的方向（ops/picks/hint.json，bar＝要用的數據日期），只在日期對得上時出現
    try: hint = json.load(open(P('ops', 'picks', 'hint.json')))
    except Exception: hint = None
    if not hint or hint.get('bar') != g(L, 'meta.bar_date'): hint = None
    return dict(date=g(L, 'meta.bar_date'), notes_date=(notes or {}).get('date'),
                suggest=ok[0]['id'] if ok else None, hint=hint,
                recent={x['id']: x['used'] for x in c if x['used']}, skip=SKIP_PANELS,
                note=('每日任務：挑 1 張（不限 suggest），先想「讀者今天在問什麼」，再挑最能回答的面板；recent 裡的（最近 7 天用過）不能挑。'
                      '寫 data/picks.json：q_zh／q_en 是圖上的問句標題，zh／en 是解說：現在的讀值、過去同樣情況之後怎樣（勝率照實寫）、這代表什麼。'
                      '數字只能用這裡 data／signals 或當期 notes 有的；不寫出場框架、買賣點、目標價。'),
                candidates=c)


def check2(L, pk):
    from x_len import weight
    bar = g(L, 'meta.bar_date'); errs = []
    if pk.get('date') != bar: errs.append(f'date {pk.get("date")} ≠ bar_date {bar}')
    ps = pk.get('picks') or []
    if len(ps) != 1: errs.append(f'picks 一天 1 張，現在 {len(ps)} 張')
    try:
        sys.path.insert(0, P('ops', 'replies')); from check import AI_WORDS, EN_NAME, EN_NAMES   # 回覆用的 AI 腔清單，推薦圖表也照用；EN_NAME：比特幣→BTC 這類（2026-11-09）
    except Exception: AI_WORDS = EN_NAME = None
    cand = {c['id']: c for c in candidates2(L, load('notes.json'))}
    src = NUMS(json.dumps([cand, load('notes.json'), load('notes.en.json')], ensure_ascii=False))
    for p in ps:
        i = p.get('id')
        if i in SKIP_PANELS: errs.append(f'{i}: 不推（{SKIP_PANELS[i]}）'); continue
        if i not in PANELS: errs.append(f'{i}: 不是網站面板（看 plan 的 candidates）'); continue
        if cand[i]['used']: errs.append(f'{i}: {cand[i]["used"]} 已經用過，最近 {RECENT_DAYS} 天不重複')
        for k, want in (('chart', f'data/picks/{slug(i)}.png'), ('chart_en', f'data/picks/{slug(i)}-en.png')):
            if p.get(k) != want: errs.append(f'{i}: {k} 應為 {want}')
        for lang in ('zh', 'en'):
            q, t = p.get('q_' + lang) or '', p.get(lang) or ''
            if not q: errs.append(f'{i}.q_{lang}: 圖上的問句標題空白')
            if not t: errs.append(f'{i}.{lang}: 解說空白'); continue
            if q and weight(q) > (56 if lang == 'zh' else 70): errs.append(f'{i}.q_{lang}: 標題太長（{weight(q)}），圖上放不下')
            if weight(t) > 280: errs.append(f'{i}.{lang}: {weight(t)}/280 超過')
            for x, tag in ((q, 'q_' + lang), (t, lang)):
                if BAN.search(x): errs.append(f'{i}.{tag}: 提到出場框架或買賣（{BAN.search(x).group(0)}）')
                if AI_WORDS and AI_WORDS.search(x): errs.append(f'{i}.{tag}: AI 腔或不用的詞（{AI_WORDS.search(x).group(0)}，見運營 voice.md）')
                if EN_NAME and lang == 'zh' and EN_NAME.search(x): errs.append(f'{i}.{tag}: 有英文常用名的詞要用英文（{EN_NAME.search(x).group(0)}→{EN_NAMES[EN_NAME.search(x).group(0)]}，見運營 voice.md 用詞）')
                miss = sorted(NUMS(x) - src)
                if miss: errs.append(f'{i}.{tag}: 這些數字在 plan 的資料與當期 notes 裡找不到：{", ".join(miss)}')
            if lang == 'en' and re.search(r'[一-鿿]', q + t): errs.append(f'{i}.en: 有中文字')
            if lang == 'zh' and '選擇權' in t and t.find('選擇權') != t.find('選擇權（期權）'):   # 2026-11-06 使用者：第一次出現寫「選擇權（期權）」
                errs.append(f'{i}.zh: 選擇權第一次出現要寫「選擇權（期權）」（幣圈中文多半說期權）')
    return errs


def shoot(items, lang, out_dir):
    """用 ops/post/site_shot.py 截網站面板（深色、clean）。回傳 {out: 路徑}；Chrome 不在或失敗就回空。"""
    import subprocess, tempfile
    jobs = dict(lang=lang, theme='dark', width=1440, items=[dict(page=k.split('/')[0], sel=PANELS[k]['sel'], out=o, clean=1, **({'html': 1} if PANELS[k].get('html') else {})) for k, o in items])
    jf = os.path.join(tempfile.mkdtemp(prefix='picks-'), 'jobs.json'); json.dump(jobs, open(jf, 'w'))
    try: subprocess.run([sys.executable, P('ops', 'post', 'site_shot.py'), jf, out_dir], check=True, timeout=240)
    except Exception as e: print('截圖失敗', repr(e), file=sys.stderr); return {}
    return {o: os.path.join(out_dir, o + '.png') for _, o in items if os.path.exists(os.path.join(out_dir, o + '.png'))}


def card2(L, notes, shot, q, lang, Fn, out):
    """深色卡：今日圖表標籤與期數 → 問句標題 → 網站原圖 → 頁尾。寬度跟截圖一樣（2 倍畫，存成一半）。"""
    from PIL import Image, ImageDraw
    import share_card as SC
    BG, INK_, INK3_, LINE_ = (12, 12, 13), '#F2F0EA', '#9C978E', '#3A3936'
    im = Image.open(shot).convert('RGB'); Pd = 72; Wc = im.width + 2 * Pd
    tf = Fn['cjk'](36, 900) if lang == 'zh' else Fn['mono'](34, 800)
    tag = '今日圖表' if lang == 'zh' else 'CHART OF THE DAY'
    bd = dt.date.fromisoformat(g(L, 'meta.bar_date')); ed = (notes or {}).get('edition', 0) if (notes or {}).get('date') == g(L, 'meta.bar_date') else 0
    meta = (f'DAYBREAK No.{ed:03d}   ' if ed else 'DAYBREAK   ') + (f'{bd:%Y.%m.%d}（{WD["zh"][bd.weekday()]}）收盤版' if lang == 'zh' else f'{WD["en"][bd.weekday()]} {bd:%b %d, %Y} close')
    for size in range(96, 56, -4):   # 問句標題：自動縮字，最多 2 行
        hf = Fn['head'](size) if lang == 'zh' else Fn['num'](int(size * 1.1)); lines = SC.wrap(q, hf, Wc - 2 * Pd)
        if len(lines) <= 2: break
    lh = int(size * 1.3); top = 56; ty = top + 64 + 44; H = ty + lh * len(lines) + 48 + im.height + 40 + 140
    img = Image.new('RGB', (Wc, H), BG); d = ImageDraw.Draw(img)
    tw = d.textlength(tag, font=tf); d.rounded_rectangle([Pd, top, Pd + tw + 44, top + 64], radius=32, fill=RED)
    d.text((Pd + 22 + tw / 2, top + 32), tag, font=tf, fill='#FFFFFF', anchor='mm')
    d.text((Pd + tw + 72, top + 32), meta, font=Fn['cjk'](32, 500) if lang == 'zh' else Fn['mono'](30, 500), fill=INK3_, anchor='lm')
    y = ty
    for ln in lines:
        x = Pd
        for a, red in ln: d.text((x, y), a, font=hf, fill=RED if red else INK_); x += hf.getlength(a)
        y += lh
    y += 48; img.paste(im, (Pd, y))
    fy = H - 70; d.line([Pd, fy - 52, Wc - Pd, fy - 52], fill=LINE_, width=2)
    d.arc([Pd, fy - 26, Pd + 52, fy + 26], 180, 360, fill=RED, width=8); d.line([Pd - 8, fy, Pd + 60, fy], fill=INK_, width=8)
    d.text((Pd + 84, fy), '破曉 DAYBREAK' if lang == 'zh' else 'DAYBREAK', font=Fn['cjk'](38, 900) if lang == 'zh' else Fn['mono'](38, 800), fill=INK_, anchor='lm')
    d.text((Wc - Pd, fy), 'X @songpu717', font=Fn['mono'](34), fill=INK3_, anchor='rm')
    img.resize((Wc // 2, H // 2), Image.LANCZOS).save(out, optimize=True)
    print('wrote', os.path.relpath(out, ROOT), (Wc // 2, H // 2))


def render2(L, fonts_dir):
    import share_card as SC, tempfile
    Fn = SC.fonts(fonts_dir); bar = g(L, 'meta.bar_date')
    notes, notes_en, pk = load('notes.json'), load('notes.en.json'), load('picks.json')
    cur = bool(pk and pk.get('date') == bar and pk.get('picks'))
    if cur and pk['picks'][0].get('id') in PANELS:
        p = pk['picks'][0]; pid = p['id']; q = {'zh': p.get('q_zh'), 'en': p.get('q_en')}
        print('picks.json', bar, pid)
    else:
        c = [x for x in candidates2(L, notes) if not x['used']]
        if not c: print('沒有候選面板'); return
        pid = c[0]['id']; q = {}; cur = False
        print('picks.json 不存在或不是當期，自動挑：', pid)
    od = P('data', 'picks'); os.makedirs(od, exist_ok=True); tmp = tempfile.mkdtemp(prefix='picks-shot-')
    keep = {'index.json', 'history.json'}; s = slug(pid); name = T(PANELS[pid]['zh'], PANELS[pid]['en'])
    for lang, fn in (('zh', f'{s}.png'), ('en', f'{s}-en.png')):
        shots = shoot([(pid, s + '-' + lang)], lang, tmp)
        if shots:
            card2(L, notes if lang == 'zh' else notes_en, shots[s + '-' + lang], q.get(lang) or name[lang], lang, Fn, os.path.join(od, fn)); keep.add(fn)
        elif PANELS[pid].get('old') and spec(L, PANELS[pid]['old']):   # 備案：截不到網站原圖，改畫舊版的簡化圖
            print('改用舊版圖', PANELS[pid]['old'])
            card(L, notes if lang == 'zh' else notes_en, spec(L, PANELS[pid]['old']), q.get(lang) or name[lang], lang, Fn, os.path.join(od, fn)); keep.add(fn)
        else: print('這張畫不出來', pid, lang)
    done = [dict(id=pid, chart=f'data/picks/{s}.png', chart_en=f'data/picks/{s}-en.png', name=name, link=f'https://north7.github.io/daybreak/#{pid}')] if f'{s}.png' in keep else []
    json.dump(dict(date=bar, captions=cur, picks=done), open(os.path.join(od, 'index.json'), 'w'), ensure_ascii=False, indent=1)
    if done:   # 記下這天推了哪張，之後 7 天不重複（只留 60 天）
        h = load('picks/history.json') or {'items': []}
        h['items'] = [x for x in h['items'] if (x.get('date'), x.get('id')) != (bar, pid)] + [dict(date=bar, id=pid)]   # 當天的紀錄不擋當天（recent_used 只看 bar 之前）
        h['items'] = sorted(h['items'], key=lambda x: x['date'])[-60:]
        json.dump(h, open(os.path.join(od, 'history.json'), 'w'), ensure_ascii=False, indent=1)
    for fn in os.listdir(od):
        if fn not in keep: os.remove(os.path.join(od, fn)); print('removed', fn)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['plan', 'render', 'check', 'plan-v1', 'render-v1']); ap.add_argument('--fonts')
    a = ap.parse_args(); L = json.load(open(P('data', 'latest.json')))
    if a.cmd == 'plan': print(json.dumps(plan2(L), ensure_ascii=False, indent=1))
    elif a.cmd == 'plan-v1': print(json.dumps(plan(L), ensure_ascii=False, indent=1))
    elif a.cmd == 'check':
        pk = load('picks.json')
        if not pk: e = ['data/picks.json 不存在或不是合法 JSON']
        elif all((x.get('id') or '') in PANELS or (x.get('id') or '') in SKIP_PANELS or '/' in (x.get('id') or '') for x in pk.get('picks') or [{}]): e = check2(L, pk)
        else: e = check(L)   # 舊格式（id 是 cost、cohort 這類）照舊檢查
        print('\n'.join(e) if e else 'picks.json OK'); sys.exit(1 if e else 0)
    else:
        if not a.fonts: ap.error('render 需要 --fonts')
        pk = load('picks.json')
        if a.cmd == 'render-v1' or (pk and pk.get('date') == g(L, 'meta.bar_date') and pk.get('picks') and '/' not in (pk['picks'][0].get('id') or '')): render(L, a.fonts)
        else: render2(L, a.fonts)
