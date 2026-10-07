"""Daybreak 資料建置：把 collect.py 輸出的 today.json 整理成網站讀的 data/latest.json，並更新 data/history/。
用法（在倉庫根目錄）：python3 pipeline/build.py pipeline/today.json
只輸出市場資料與模型讀值；不含任何個人持倉資訊。"""
import json, sys, os, math, subprocess, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
td = json.load(open(sys.argv[1] if len(sys.argv) > 1 else P('pipeline', 'today.json')))
model = json.load(open(P('data', 'model.json')))
etf = json.load(open(P('data', 'etf.json')))
EP = dt.date(1970, 1, 1)
dn = lambda s: (dt.date.fromisoformat(s[:10]) - EP).days

def get(url):
    out = subprocess.run(['curl', '-sS', '--max-time', '60', url], capture_output=True, text=True).stdout
    return json.loads(out)

# 長期價格（CoinMetrics，每 7 天一點，2012 起）
hist = []
try:
    cm = get('https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=PriceUSD&frequency=1d&start_time=2012-01-01&page_size=10000')['data']
    px = [(x['time'][:10], float(x['PriceUSD'])) for x in cm if x.get('PriceUSD')]
    hist = [[dn(d), round(p, 2)] for d, p in px[::-7]][::-1]
    if hist[-1][0] != dn(px[-1][0]): hist.append([dn(px[-1][0]), round(px[-1][1], 2)])
except Exception as e:
    print('price history failed', e)

c = td['bar']['c']; ma = td['ma']; cmr = td.get('cm_radar') or {}
ladder = model['exit_framework']['ladder']
nxt = next((x for x in ladder if x > c), None)
onchain = {k: {kk: v.get(kk) for kk in ('date', 'value', 'pct_4y', 'ma7', 'chg30_pct')} for k, v in (td.get('onchain') or {}).items() if isinstance(v, dict)}

out = {
  'meta': {'bar_date': td['bar_date'], 'generated_utc': td.get('generated_utc'), 'errors': td.get('errors', []), 'bd_rotation': td.get('bd_rotation'),
           'sources': ['Kraken', 'Deribit', 'CoinMetrics Community', 'bitcoin-data.com', 'mempool.space', 'FRED', 'Farside', 'Tidemark', '13 個交易所掛單簿']},
  'price': {'bar': td['bar'], 'ma': ma, 'atr': td.get('atr'), 'vol': td.get('vol'), 'mayer': td.get('mayer'), 'pi_cycle': td.get('pi_cycle'),
            'range20_pos_pct': td.get('range20_pos_pct'), 'volprofile': td.get('volprofile_v2'), 'rows20': td.get('chart_rows_20d'), 'history': hist},
  'deriv': {'dvol': td.get('dvol'), 'deriv': td.get('deriv'), 'rr25': td.get('rr25'), 'samesource': td.get('samesource'),
            'options': {'total_oi': (td.get('options') or {}).get('total_oi'), 'expiries': [{k: e.get(k) for k in ('expiry', 'dte', 'oi', 'share', 'pc', 'maxpain', 'top_calls', 'top_puts')} for e in (td.get('options') or {}).get('expiries', [])]},
            'viz': {k: (td.get('ex_viz') or {}).get(k) for k in ('vol', 'basis', 'options')}},
  'flows': {'etf': etf['rows'], 'fred': td.get('fred'), 'dfii10': (td.get('extra') or {}).get('dfii10')},
  'onchain': {'metrics': onchain, 'top_radar': td.get('top_radar'), 'cost_ratio': td.get('lth_sth_cost_ratio'), 'mining': td.get('mining'),
              'exchange': {k: cmr.get(k) for k in ('exchange_supply_btc', 'exchange_supply_share_pct', 'exchange_supply_chg7_pct', 'exchange_supply_chg30_pct', 'exchange_supply_chg90_pct', 'exchange_supply_date')}},
  'chips': {'flow': {k: v for k, v in (td.get('murphy_flow') or {}).items() if k != 'urpd'}, 'urpd': {k: v for k, v in ((td.get('murphy_flow') or {}).get('urpd') or {}).items() if k != 'band'}, 'viz': td.get('murphy_viz')},
  'orderbook': td.get('orderbook_viz'),
  'cycle': {'cm': {k: cmr.get(k) for k in ('date', 'mvrv', 'realized_price', 'prior_cycle_peak', 'mvrv_vs_prior', 'k075_price', 'k080_price', 'mvrv_vs_365d_max', 'price_ath_close', 'divergence', 'p20_run_ge075', 'p20_run_ge080')},
            'p20': (td.get('ex_viz') or {}).get('p20'), 'p6': (td.get('ex_viz') or {}).get('p6'), 'p6_date': (td.get('ex_viz') or {}).get('p6_date'),
            'powerlaw': dict(td.get('powerlaw') or {}, rows=((td.get('ex_viz') or {}).get('powerlaw') or {}).get('rows')),
            'tidemark': td.get('tidemark'), 'stage': td.get('market_stage'), 'model': model['paths'], 'halvings': model['halvings'],
            'next_halving_est': model['next_halving_est'], 'tops': model['cycle_tops'], 'bottoms': model['cycle_bottoms']},
  'exit': {'framework': model['exit_framework'], 'status': {
            'close': c, 'sma200': ma.get('sma200'), 'below_sma200_run': (td.get('p19') or {}).get('below_sma200_run'),
            'next_step': nxt, 'next_step_dist_pct': round((nxt / c - 1) * 100, 1) if nxt else None, 'steps_hit': [x for x in ladder if x <= c],
            'p20_ratio': cmr.get('mvrv_vs_prior'), 'k075_price': cmr.get('k075_price'), 'k080_price': cmr.get('k080_price'),
            'p20_run_075': cmr.get('p20_run_ge075'), 'p20_run_080': cmr.get('p20_run_ge080'),
            'p6': (td.get('ex_viz') or {}).get('p6')}},
}
json.dump(out, open(P('data', 'latest.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
snap = {'date': td['bar_date'], 'close': c, 'chg_pct': td['bar'].get('chg_pct'), 'p20': cmr.get('mvrv_vs_prior'), 'pl_ratio': (td.get('powerlaw') or {}).get('ratio'),
        'dvol': (td.get('dvol') or {}).get('value'), 'tm_top': ((td.get('tidemark') or {}).get('top') or {}).get('signal'), 'tm_bottom': ((td.get('tidemark') or {}).get('bottom') or {}).get('signal')}
idx_f = P('data', 'history', 'index.json')
idx = json.load(open(idx_f)) if os.path.exists(idx_f) else []
idx = [x for x in idx if x['date'] != snap['date']] + [snap]
json.dump(sorted(idx, key=lambda x: x['date'])[-800:], open(idx_f, 'w'), ensure_ascii=False, indent=0)
print('built data/latest.json', td['bar_date'], os.path.getsize(P('data', 'latest.json')), 'bytes')

# 給下一次 collect.py 用的最小前一日狀態（URPD 週變化、ATR 回測）；只含市場資料
sm_f = P('pipeline', 'state_min.json')
sm = json.load(open(sm_f)) if os.path.exists(sm_f) else {'series': [], '_conventions': {'position_framework_p19_state': {'ladder_filled': [], 'cancelled_price_levels': []}}}
row = {'bar_date': td['bar_date'], 'c': c, 'atr14': (td.get('atr') or {}).get('atr14'), 'atr7': (td.get('atr') or {}).get('atr7'),
       'murphy_flow': {'urpd': {k: ((td.get('murphy_flow') or {}).get('urpd') or {}).get(k) for k in ('date', 'band')}}}
sm['series'] = [r for r in sm['series'] if r.get('bar_date') != row['bar_date']] + [row]
sm['series'] = sorted(sm['series'], key=lambda r: r['bar_date'])[-21:]
json.dump(sm, open(sm_f, 'w'), ensure_ascii=False, separators=(',', ':'))
