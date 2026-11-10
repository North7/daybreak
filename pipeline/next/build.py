# -*- coding: utf-8 -*-
"""新版首頁（2026-11-11 起取代舊版，舊版搬到 classic.html）的建置：
1. 先用無頭 Chrome 跑舊版 classic.html，抽出每個面板的白話讀值（extract_interp.py → interp.zh.json／interp.en.json；失敗就沿用上一次的檔案）。
2. 從 data/latest.json、data/notes*.json 組出每一頁、每張圖要用的資料（site_data.py 和各頁的 *_data.py）。
3. 寫 data/next.js（window.DAYBREAK_NEXT＝整包資料），並把 page.html 寫成倉庫根目錄的 index.html（只換資料檔的版本號）。
用法：python3 pipeline/next/build.py [--no-interp]
每日資料流程（daily.yml）和日報推送後（share.yml）都會跑一次。"""
import json, os, sys, datetime as dt, bisect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import subprocess, hashlib
if '--no-interp' not in sys.argv:
    for _a in ([], ['en']):
        try: subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extract_interp.py')] + _a, check=True, timeout=240)
        except Exception as _e: print('extract_interp', _a, '失敗，沿用上一次的讀值：', _e)
HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(REPO, 'data', 'latest.json'), encoding='utf-8'))
N = json.load(open(os.path.join(REPO, 'data', 'notes.json'), encoding='utf-8'))
EP = dt.date(1970, 1, 1); dn = lambda s: (dt.date.fromisoformat(s) - EP).days; ymd = lambda n: (EP + dt.timedelta(n)).isoformat()

dw = L['cycle']['dawn']; R = dw['rows']                       # [day, heat, price, stage, dir]
days = [r[0] for r in R]
def align(rows, col, tol=6):
    xs = [r[0] for r in rows]; out = []
    for d in days:
        k = bisect.bisect_right(xs, d) - 1
        out.append(rows[k][col] if k >= 0 and d - xs[k] <= tol and rows[k][col] is not None else None)
    return out
hn = L['onchain']['hnupl']['rows']                             # [day, price, lth, sth]
fg = L['flows']['fng_hist']['rows']                            # [day, price, value]
fu = L['deriv']['fund_hist']['rows']                           # [day, price, 7d avg annualized %]
st = L['flows']['stables']['rows']                             # [day, usd_b]
sm = {r[0]: r[1] for r in st}
def p30(d):
    for k in (30, 31, 29, 32, 28):
        if sm.get(d - k): return round((sm[d] / sm[d - k] - 1) * 100, 2)
    return None
stab = [[r[0], p30(r[0])] for r in st]; stab = [r for r in stab if r[1] is not None]
px = [r[2] for r in R]
mayer = [round(px[i] / (sum(px[i - 39:i + 1]) / 40), 3) if i >= 39 else None for i in range(len(px))]
wk = dict(t0=days[0], n=len(days), heat=[r[1] for r in R], px=px, stg=[r[3] for r in R], dir=[r[4] for r in R],
          nupl=[None if v is None else round(v, 3) for v in align(hn, 3)], fng=align(fg, 2), fund=[None if v is None else round(v, 1) for v in align(fu, 2)],
          stab=align(stab, 1), mayer=mayer)
assert all(days[i + 1] - days[i] == 7 for i in range(len(days) - 1)), 'weekly step'

u = L['chips']['viz']['urpd']; W = u.get('width', 2000); c = L['price']['bar']['c']
band = sorted([b for b in u['band'] if 50000 <= b[0] < 126000])
def win(lo, hi, k, more):
    best = None
    for i in range(len(band) - k + 1):
        w = band[i:i + k]
        if w[0][0] < lo or w[-1][0] + W > hi: continue
        t = sum(b[1] for b in w)
        if best is None or (t > best[2] if more else t < best[2]): best = [w[0][0], w[-1][0] + W, t]
    return best
cur = int(c // W) * W
thick = win(c * 0.8, c * 1.25, 5, True)
thin = win(c * 0.8, min(cur, 10**9), 4, False) if thick[0] > c else win(max(thick[1], cur + W), c * 1.2, 4, False)

sr = [[r[0], r[1]] for r in L['chips']['stress']['rows'][-30:]]
if sr[-1][0] == dn(L['meta']['bar_date']): sr[-1][1] = round(c)
d30 = sr
lv = L['cycle']['levels']; w50 = lv['w50']
lvrows = [[r[0], r[1], r[2], r[4], r[5], r[6]] for r in lv['rows']]   # day, price, sma200, w50, sth cost, true market mean
etf = [[e['d'], e['musd'], 1 if e.get('partial') else 0] for e in L['flows']['etf']]
full = [e for e in L['flows']['etf'] if not e.get('partial')]
sc = L['flows']['stables']; stg = L['cycle']['stage']; fl = L['chips']['flow']
brk = [b for b in w50['breaks'] if b.get('weeks') is not None]
import oc_data
E_ = json.load(open(os.path.join(REPO, 'data', 'notes.en.json'), encoding='utf-8')) if os.path.exists(os.path.join(REPO, 'data', 'notes.en.json')) else None
import site_data
SITE = site_data.build(L, N, E_, dn)
import say_data
print('say', say_data.attach(SITE['chapters'], L))
import pm_data
D = dict(
    site=SITE, pm=pm_data.build(L),
    date=L['meta']['bar_date'], issue=N.get('edition'), price=round(c), chg=L['price']['bar']['chg_pct'],
    headline=N['headline'], summary=N['summary'], stance=N.get('stance'), leads={k: m.get('lead') for k, m in N['modules'].items()},
    wk=wk, marks=[dict(d=dn(m['date']), kind=m['kind'], heat=m['heat']) for m in dw['marks']], th=dw['th'],
    dawn=dict(heat=dw['heat'], stage=dw['stage'], weeks=dw['stage_weeks'], heat4=dw['heat4']),
    urpd=dict(price=round(c), date=u['date'], w=W, band=band, thick=thick, thin=thin),
    lv=lvrows, w50=dict(date=w50['date'], close=w50['close'], ma=w50['ma'], dist=w50['dist_pct'], above=w50['above'], prev_run=(w50.get('cross') or {}).get('prev_run'), live=w50.get('live'),
                        n=len(brk), fast=sum(1 for b in brk if b['weeks'] <= 2), slow=[b['weeks'] for b in brk if b['weeks'] >= 26], slow_y=[b['date'][:4] for b in brk if b['weeks'] >= 26]),
    stage=dict(name=stg['stage'], since=stg['since'], run=stg['above_rising_run'], sma200=round(stg['sma200'])),
    stab=[r for r in stab if r[0] >= dn(L['meta']['bar_date']) - 1100], stabNow=dict(usd=sc['usd_b'], p30=sc['chg30_pct'], d30=sc['chg30_usd_b'], pct=sc['pct30']),
    etf=etf, etf5=round(sum(e['musd'] for e in full[-5:])),
    d30=d30,
    now=dict(sthProfit=fl['sth_in_profit_pct']['value'], fund=L['deriv']['fund_hist']['value'], dvol=L['deriv']['dvol']['value'], fng=L['flows']['fng_hist']['value'],
             mvrvPrior=L['cycle']['cm']['mvrv_vs_prior'], k075=L['cycle']['cm']['k075_price'], ladder1=L['exit']['framework']['ladder'][0]),
)
print('urpd thick', thick, 'thin', thin, '| w50', {k: v for k, v in D['w50'].items() if k != 'live'}, D['w50']['live'])
print('stage', D['stage'], '| stab', D['stabNow'], '| etf5', D['etf5'], '| now', D['now'], '| dawn', D['dawn'])
js = json.dumps(D, ensure_ascii=False, separators=(',', ':'))
open(os.path.join(REPO, 'data', 'next.js'), 'w', encoding='utf-8').write('window.DAYBREAK_NEXT=' + js + ';\n')
ver = hashlib.sha1(js.encode('utf-8')).hexdigest()[:10]
page = open(os.path.join(HERE, 'page.html'), encoding='utf-8').read(); assert page.count('data/next.js?v=__V__') == 1
open(os.path.join(REPO, 'index.html'), 'w', encoding='utf-8').write(page.replace('data/next.js?v=__V__', 'data/next.js?v=' + ver))
print('wrote data/next.js', len(js), 'bytes; index.html', len(page), 'bytes; v=' + ver, '| bar', D['date'], '| notes', N.get('date'))
