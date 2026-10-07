#!/usr/bin/env python3
"""BTC 日報資料管線（2026-09-22 建立；2026-09-23 週檢：補 vwap／trades、新增 extra 狀態讀值區塊；2026-09-25：成本比 7 日均、G 區頂部雷達與 P19 狀態；2026-09-26：修正 CoinMetrics 最新一天欄位為 null 時整段失敗；2026-09-27 週檢：補回 T+5 經驗分位、交易所供給 7 日變化與其一年百分位；P23 市場階段欄位；2026-10-02：G5 掛單簿深度，Coinbase／Kraken／Bitstamp 三家合計，只作讀值；同日 G4b 籌碼流向圖表資料 murphy_viz、G6 圖表資料 ex_viz；2026-10-06：G7 Tidemark 頂部／底部綜合訊號、G8 冪律讀值（無前視），只作讀值；G5b 掛單簿全景：13 個場所、±15% 每 1,000 美元與 ±1% 每 100 美元分格，輸出 orderbook_viz 給頁面柱狀圖）。一次抓齊所有 API 並自算，輸出 today.json。
用法：python3 collect.py [--up 90000 --down 82288] [--prev-state state.json]
- 以 bash date 決定「最後一根已收盤 UTC 日線」＝今天 UTC 日期的前一天。
- 不抓 ETF（Farside 需 WebFetch，另行處理）。任何來源失敗 → 該欄位 null 並記在 errors，不推估。
口徑與日報 _conventions 相同：ATR 為簡單平均、RV 用 ddof=1 年化 √365、EMA 以 SMA 播種、
算力 7 日均＝最後 7 個完整日、hashprice＝144 塊獎勵×收盤÷PH/s、P8 分桶凍結邊界 p67=1.063（至 2026-10-20）。
"""
import json, math, statistics as st, datetime as dt, subprocess, sys, re, argparse
from statistics import NormalDist
N = NormalDist().cdf
ap = argparse.ArgumentParser()
ap.add_argument('--up', type=float); ap.add_argument('--down', type=float)
ap.add_argument('--p67', type=float, default=1.063)
ap.add_argument('--prev-state')
a = ap.parse_args()
errors = []
def get(url):
    try:
        out = subprocess.run(['curl', '-sS', '--max-time', '40', url], capture_output=True, text=True).stdout
        return json.loads(out) if out.strip().startswith(('{', '[')) else out
    except Exception as e:
        errors.append(f'{url}: {e}'); return None
# 2026-10-08：bitcoin-data 免費層每小時 10 次、每日 15 次，20 個端點改由 bd_rotation.py 分配：CORE 即時抓，其餘讀前一晚輪替快取（頁面照常顯示資料本身日期）
import bd_rotation
R_bd = {}   # 讀快取的端點 → 抓取時間，寫進 R['bd_rotation']
def bd(m):
    if m in bd_rotation.CORE: return bd_rotation.fetch(m)
    rows, fetched = bd_rotation.load(m); R_bd[m] = fetched
    return rows
now = dt.datetime.now(dt.timezone.utc)
LAST = (now.date() - dt.timedelta(days=1)).isoformat()   # 最後一根已收盤日線
R = {'generated_utc': now.isoformat(timespec='seconds'), 'bar_date': LAST}
ymd = lambda ts: dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime('%Y-%m-%d')

# ---------- A. Kraken ----------
k = get('https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440')
key = [x for x in k['result'] if x != 'last'][0]
bars = [dict(d=ymd(int(r[0])), o=float(r[1]), h=float(r[2]), l=float(r[3]), c=float(r[4]), vw=float(r[5]), v=float(r[6]), n=int(r[7])) for r in k['result'][key]]
bars = [b for b in bars if b['d'] <= LAST]
assert bars[-1]['d'] == LAST, f'Kraken 最後一根是 {bars[-1]["d"]}，不是 {LAST}（剛收的日線未出，不可退回前一天）'
C = [b['c'] for b in bars]; H = [b['h'] for b in bars]; L = [b['l'] for b in bars]; n = len(C); c = C[-1]; p = bars[-2]
sma = lambda w, e=n: sum(C[e - w:e]) / w
def _dchg(ser, d_, k_, v_):   # 2026-10-07 a9：以日期回推 k 天；該日缺值回傳 None，不以列位置代替
    b_ = ser.get((dt.date.fromisoformat(d_) - dt.timedelta(days=k_)).isoformat())
    return round((v_ / b_ - 1) * 100, 2) if b_ else None

def ema(w):
    kf = 2 / (w + 1); e = sum(C[:w]) / w
    for x in C[w:]: e = x * kf + e * (1 - kf)
    return e
tr = [max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])) for i in range(1, n)]
def rv(series, w, end=None):
    end = len(series) if end is None else end
    rets = [math.log(series[i] / series[i - 1]) for i in range(end - w, end)]
    return st.stdev(rets) * math.sqrt(365) * 100
park = lambda w: math.sqrt(sum(math.log(H[i] / L[i]) ** 2 for i in range(n - w, n)) / (4 * math.log(2) * w)) * math.sqrt(365) * 100
b = bars[-1]
R['bar'] = dict(o=b['o'], h=b['h'], l=b['l'], c=c, v=round(b['v'], 2), chg_pct=round((c / p['c'] - 1) * 100, 2),
                range_pct=round((b['h'] - b['l']) / p['c'] * 100, 2), close_pos_pct=round((c - b['l']) / (b['h'] - b['l']) * 100, 1),
                vwap=b['vw'], trades=b['n'], vol_vs_prev=round(b['v'] / p['v'], 3), vol_vs_20dma=round(b['v'] / (sum(x['v'] for x in bars[-20:]) / 20), 3))
R['ma'] = {f'sma{w}': round(sma(w), 1) for w in (5, 10, 20, 50, 111, 200, 350)}
R['ma'].update(ema50=round(ema(50), 1), ema200=round(ema(200), 1))
R['atr'] = dict(atr14=round(sum(tr[-14:]) / 14, 1), atr7=round(sum(tr[-7:]) / 7, 1),
                backtest_prev_atr14=round(sum(tr[-15:-1]) / 14, 1), backtest_prev_atr7=round(sum(tr[-8:-1]) / 7, 1))
R['vol'] = dict(rv7=round(rv(C, 7), 2), rv30=round(rv(C, 30), 2), rv90=round(rv(C, 90), 2), park7=round(park(7), 2), park30=round(park(30), 2))
R['vol']['rv7_rv30'] = round(R['vol']['rv7'] / R['vol']['rv30'], 3)
s200 = sma(200); R['mayer'] = dict(mayer=round(c / s200, 4), line_1_2=round(1.2 * s200, 1))
R['pi_cycle'] = round(sma(111) / (2 * sma(350)), 4)
lo20, hi20 = min(C[-20:]), max(C[-20:])
R['range20_pos_pct'] = round((c - lo20) / (hi20 - lo20) * 100, 1)
# 成交量分布
bk = {}
for x in bars[-20:]:
    s0 = int(x['l'] // 250) * 250; nb = int((x['h'] - s0) // 250) + 1
    for i in range(nb): bk[s0 + i * 250] = bk.get(s0 + i * 250, 0) + x['v'] / nb
tot = sum(bk.values()); acc = 0; va = []
for kk, vv in sorted(bk.items(), key=lambda z: -z[1]):
    acc += vv; va.append(kk)
    if acc / tot >= .7: break
R['volprofile'] = dict(poc=max(bk, key=bk.get), poc_share=round(max(bk.values()) / tot * 100, 1), va_low=min(va), va_high=max(va),
                      va_high_outer=max(va) + 250, note='格子 key＝下緣；va_high 為最高格下緣（舊口徑），va_high_outer＝最高格外緣（2026-10-07 a4）')
# 2026-10-07 a4 v2：每根日線的量依 [L,H] 與每格 [k,k+250) 的交集長度分量（日線均勻分量估計），自 10/09 重設凍結值起生效、不追溯
bk2 = {}
for x in bars[-20:]:
    L_, H_ = x['l'], x['h']; span = max(H_ - L_, 1e-9); k0 = int(L_ // 250) * 250
    while k0 < H_:
        ov = min(H_, k0 + 250) - max(L_, k0)
        if ov > 0: bk2[k0] = bk2.get(k0, 0) + x['v'] * ov / span
        k0 += 250
tot2 = sum(bk2.values()); acc2 = 0; va2 = []
for kk, vv in sorted(bk2.items(), key=lambda z: -z[1]):
    acc2 += vv; va2.append(kk)
    if acc2 / tot2 >= .7: break
R['volprofile_v2'] = dict(poc=max(bk2, key=bk2.get), poc_share=round(max(bk2.values()) / tot2 * 100, 1), va_low=min(va2), va_high_outer=max(va2) + 250,
                          method='日線均勻分量估計：每根日線成交量依 [L,H] 與每格交集長度分配；格寬 250；va_high_outer＝最高格外緣；v2 自 2026-10-09 生效')
R['chart_rows_20d'] = [[x['d'][5:].replace('-', '/'), round(x['o']), round(x['h']), round(x['l']), round(x['c'])] for x in bars[-20:]]

# ---------- 2026-09-27 P23：市場階段（熊市／熊牛轉換期／牛市）所需的價格欄位 ----------
try:
    def _s200(e): return sum(C[e - 199:e + 1]) / 200
    def _cnt(f):
        r = 0
        for j in range(n - 1, 240, -1):
            if f(j): r += 1
            else: break
        return r
    R['market_stage'] = dict(
        sma200=round(_s200(n - 1), 1), sma200_30d_ago=round(_s200(n - 31), 1), sma200_rising=_s200(n - 1) > _s200(n - 31),
        above_rising_run=_cnt(lambda j: C[j] > _s200(j) and _s200(j) > _s200(j - 30)),
        below_run=_cnt(lambda j: C[j] < _s200(j)),
        below_falling_run=_cnt(lambda j: C[j] < _s200(j) and _s200(j) < _s200(j - 30)),
        note='燈號二看 cm_radar.exchange_supply_chg90_pct <0；判定規則見 _conventions.market_stage_p23')
except Exception as e: errors.append(f'market_stage {e}')

# ---------- 條件式基準率（P8）＋ P13 阻力特徵 ----------
def rvat(i, w): return st.stdev([math.log(C[j] / C[j - 1]) for j in range(i - w + 1, i + 1)])
side = 'exp' if rvat(n - 1, 7) / rvat(n - 1, 30) >= a.p67 else ('cmp' if rvat(n - 1, 7) / rvat(n - 1, 30) < 0.764 else 'mid')
above = c > sma(20); upper = R['range20_pos_pct'] >= 50
samp = []
for i in range(30, n - 1):
    r_ = rvat(i, 7) / rvat(i, 30)
    s_ = 'exp' if r_ >= a.p67 else ('cmp' if r_ < 0.764 else 'mid')
    lo_, hi_ = min(C[i - 19:i + 1]), max(C[i - 19:i + 1])
    if s_ == side and (C[i] > sum(C[i - 19:i + 1]) / 20) == above and (((C[i] - lo_) / (hi_ - lo_) if hi_ > lo_ else .5) >= .5) == upper:
        samp.append(i)
up1 = [C[i + 1] > C[i] for i in samp]
q = lambda arr, pp: sorted(arr)[int(pp * (len(arr) - 1))]
r1 = [C[i + 1] / C[i] - 1 for i in samp]
R['baserate'] = dict(bucket=side, above_sma20=above, upper_half=upper, n_t1=len(samp), p_up=round(sum(up1) / len(up1) * 100, 2),
                     uncond_all=round(sum(C[i + 1] > C[i] for i in range(n - 1)) / (n - 1) * 100, 2),
                     uncond_1y=round(sum(C[i + 1] > C[i] for i in range(n - 366, n - 1)) / 365 * 100, 2),
                     uncond_90d=round(sum(C[i + 1] > C[i] for i in range(n - 91, n - 1)) / 90 * 100, 2),
                     emp_q10=round(q(r1, .1) * 100, 2), emp_q90=round(q(r1, .9) * 100, 2), emp_q025=round(q(r1, .025) * 100, 2), emp_q975=round(q(r1, .975) * 100, 2))
# 2026-09-27 週檢補回：T+5 經驗分位（同一條件式樣本、參考收盤後第 5 根收盤報酬；自 9/22 起管線未輸出）
try:
    r5_ = [C[i + 5] / C[i] - 1 for i in samp if i + 5 < n]
    R['baserate'].update(n_t5_emp=len(r5_), emp5_q10=round(q(r5_, .1) * 100, 2), emp5_q90=round(q(r5_, .9) * 100, 2))
except Exception as e: errors.append(f't5 empirical {e}')
if a.up and a.down:
    upp, dnp = a.up / c - 1, a.down / c - 1; cu = cd = cn = 0; t5 = [i for i in samp if i + 5 < n]
    for i in t5:
        h_ = None
        for j in range(i + 1, i + 6):
            rr = C[j] / C[i] - 1
            if rr >= upp: h_ = 'u'; break
            if rr <= dnp: h_ = 'd'; break
        cu += h_ == 'u'; cd += h_ == 'd'; cn += h_ is None
    R['t5_baserate'] = dict(up=a.up, down=a.down, up_pct=round(upp * 100, 2), down_pct=round(dnp * 100, 2), n=len(t5),
                            p=[round(cu / len(t5) * 100, 1), round(cn / len(t5) * 100, 1), round(cd / len(t5) * 100, 1)])
# P13 阻力被擋特徵（今天是否適用）
r20 = max(C[-21:-1]); rej = sum(1 for j in range(n - 10, n) if H[j] > r20 and C[j] < r20)
R['p13_resistance_feature'] = dict(r20_max_close=r20, near=bool(r20 * .985 <= c < r20), rejections_10d=rej,
    note='Bitstamp 2021-2026 回測：阻力下1.5%內 5日內收上 60.6%(n=254)；≥2次被擋 62.2%(n=180)；≥3次被擋 68.2%(n=107)；T+1 收紅 47-48%，無方向訊號')

# ---------- σ / 區間 / 觸及 ----------
dv = get(f'https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&start_timestamp={int((now.timestamp()-366*86400)*1000)}&end_timestamp={int(now.timestamp()*1000)}&resolution=86400')
try:
    dvs = [(ymd(x[0] / 1000), x[4]) for x in dv['result']['data']]
    dvs = [x for x in dvs if x[0] <= LAST]; dvol = dvs[-1][1]; yr = [v for _, v in dvs[-365:]]
    R['dvol'] = dict(date=dvs[-1][0], value=dvol, prev=dvs[-2][1], pct_1y=round(sum(v < dvol for v in yr) / len(yr) * 100, 1))
except Exception as e:
    errors.append(f'dvol {e}'); dvol = None; R['dvol'] = None
if dvol:
    sig = (dvol / 100 + R['vol']['rv7'] / 100 + R['vol']['rv30'] / 100) / 3 / math.sqrt(365)
    floor_on = R['dvol']['pct_1y'] < 10
    if floor_on: sig = max(sig, R['vol']['rv30'] / 100 / math.sqrt(365))
    s5 = sig * math.sqrt(5)
    R['sigma'] = dict(daily_pct=round(sig * 100, 4), floor_rule_applied=floor_on,
        t1_ci80=[round(c * math.exp(-1.2816 * sig)), round(c * math.exp(1.2816 * sig))], t1_ci95=[round(c * math.exp(-1.96 * sig)), round(c * math.exp(1.96 * sig))],
        t5_ci80=[round(c * math.exp(-1.2816 * s5)), round(c * math.exp(1.2816 * s5))], t5_ci95=[round(c * math.exp(-1.96 * s5)), round(c * math.exp(1.96 * s5))])
    def touch(lv): bb = math.log(lv / c); return round(min(1, 2 * N(-abs(bb) / s5)) * 100)
    R['touch5d_fn'] = 'touch5d＝五次日收盤（T+1..T+5）任一收在價位之上（上方價位）或之下（下方價位）的機率；零對數漂移常態日步長，固定種子 20261006、20 萬條路徑；touch5d_continuous＝舊反射公式 2·N(−|ln(L/c)|/(σ√5))，只作參考（2026-10-07 a1）'
    R['_sig1'] = sig
    R['_sig5'] = s5

# ---------- Deribit 衍生品 ----------
idx = get('https://www.deribit.com/api/v2/public/get_index_price?index_name=btc_usd'); ix = idx['result']['index_price'] if idx else None
R['deribit_index'] = ix
MON = dict(JAN=1, FEB=2, MAR=3, APR=4, MAY=5, JUN=6, JUL=7, AUG=8, SEP=9, OCT=10, NOV=11, DEC=12)
fut = get('https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=future')
try:
    curve = []; perp = None
    for f in fut['result']:
        if f['instrument_name'] == 'BTC-PERPETUAL': perp = f; continue
        m = re.match(r'BTC-(\d+)([A-Z]{3})(\d+)$', f['instrument_name'])
        if not m: continue
        ex = dt.datetime(2000 + int(m.group(3)), MON[m.group(2)], int(m.group(1)), 8, tzinfo=dt.timezone.utc)
        dte = (ex - now).total_seconds() / 86400
        if dte >= 7: curve.append((round(dte, 1), round((f['mark_price'] / ix - 1) / (dte / 365) * 100, 2)))
    curve.sort(); med = st.median(x[1] for x in curve); fund = perp['funding_8h'] * 3 * 365 * 100
    R['deriv'] = dict(basis_curve=curve, basis_median=round(med, 2), funding_ann=round(fund, 2), perp_minus_basis_pp=round(fund - med, 2),
                      perp_oi_usd_m=round(perp['open_interest'] / 1e6, 1), perp_mark=perp['mark_price'])
except Exception as e: errors.append(f'futures {e}')
opt = get('https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option')
try:
    E = {}
    for o in opt['result']:
        m = re.match(r'BTC-(\d+)([A-Z]{3})(\d+)-(\d+)-([CP])', o['instrument_name'])
        if not m: continue
        ex = dt.date(2000 + int(m.group(3)), MON[m.group(2)], int(m.group(1))).isoformat(); K = int(m.group(4)); cp = m.group(5)
        e = E.setdefault(ex, {'C': 0, 'P': 0, 'k': {}, 'iv': []}); oi = o.get('open_interest') or 0
        e[cp] += oi; kk = e['k'].setdefault(K, {'C': 0, 'P': 0}); kk[cp] += oi
        if o.get('mark_iv'): e['iv'].append((K, cp, o['mark_iv'] / 100))
    tot = sum(v['C'] + v['P'] for v in E.values()); rows = []
    for ex, v in sorted(E.items()):
        t = v['C'] + v['P']
        if t < 1000: continue
        ks = sorted(v['k']); mp = min(ks, key=lambda S: sum(q['C'] * max(0, S - K) + q['P'] * max(0, K - S) for K, q in v['k'].items()))
        rows.append(dict(expiry=ex, dte=(dt.date.fromisoformat(ex) - now.date()).days, oi=round(t), share=round(t / tot * 100, 1),
                         pc=round(v['P'] / v['C'], 2) if v['C'] else None, maxpain=mp,
                         top_calls=[[K, round(q['C'])] for K, q in sorted(v['k'].items(), key=lambda z: -z[1]['C'])[:3]],
                         top_puts=[[K, round(q['P'])] for K, q in sorted(v['k'].items(), key=lambda z: -z[1]['P'])[:3]],
                         call_80k=round(v['k'].get(80000, {}).get('C', 0))))
    R['options'] = dict(total_oi=round(tot), expiries=rows)
    # 真 25Δ RR：DTE 20–45 中最近的一個到期
    cand = [r for r in rows if 20 <= r['dte'] <= 45]
    if cand:
        ex = cand[0]['expiry']; T = (cand[0]['dte'] + 8 / 24) / 365; F = ix * math.exp(R['deriv']['basis_median'] / 100 * T)
        def dl(K, cp, s):
            d1 = (math.log(F / K) + .5 * s * s * T) / (s * math.sqrt(T)); return N(d1) if cp == 'C' else N(d1) - 1
        def at(cp, tgt):
            arr = sorted((dl(K, cp, s), K, s) for K, c_, s in E[ex]['iv'] if c_ == cp)
            for (d0, k0, s0), (d1_, k1, s1) in zip(arr, arr[1:]):
                if (d0 - tgt) * (d1_ - tgt) <= 0:
                    w = (tgt - d0) / (d1_ - d0) if d1_ != d0 else 0; return s0 + (s1 - s0) * w, k0 + (k1 - k0) * w
        civ, ck = at('C', .25); piv, pk = at('P', -.25)
        atm = min((z for z in E[ex]['iv'] if z[1] == 'C'), key=lambda z: abs(z[0] - F))
        R['rr25'] = dict(expiry=ex, dte=cand[0]['dte'], fwd=round(F), atm_iv=round(atm[2] * 100, 2), call_iv=round(civ * 100, 2), call_k=round(ck),
                         put_iv=round(piv * 100, 2), put_k=round(pk), rr=round((civ - piv) * 100, 2))
except Exception as e: errors.append(f'options {e}')
# 同源 RV30（Deribit 永續小時線自建 00:00 UTC 日界）
hh = get(f'https://www.deribit.com/api/v2/public/get_tradingview_chart_data?instrument_name=BTC-PERPETUAL&start_timestamp={int((now.timestamp()-45*86400)*1000)}&end_timestamp={int(now.timestamp()*1000)}&resolution=60')
try:
    daily = {}
    for t, cl in zip(hh['result']['ticks'], hh['result']['close']): daily[ymd(t / 1000)] = cl
    ss = [v for d_, v in sorted(daily.items()) if d_ <= LAST]
    R['samesource'] = dict(rv30=round(rv(ss, 30), 2), rv7=round(rv(ss, 7), 2))
    if dvol: R['samesource']['iv_minus_rv30'] = round(dvol - R['samesource']['rv30'], 2)
except Exception as e: errors.append(f'samesource {e}')

# ---------- B. 鏈上 ----------
OC = {'mvrv-zscore': 'mvrvZscore', 'nupl': 'nupl', 'puell-multiple': 'puellMultiple', 'sopr': 'sopr', 'asopr': 'aSopr', 'sth-sopr': 'sthSopr',
      'lth-sopr': 'lthSopr', 'realized-price': 'realizedPrice', 'sth-realized-price': 'sthRealizedPrice',
      'lth-realized-price': 'lthRealizedPrice', 'illiquid-supply': 'illiquidSupply', 'highly-liquid-supply': 'highlyLiquidSupply'}
# 2026-10-01 月度複盤：reserve-risk、active-addresses 退役（零資訊量、零結論變更；省 bitcoin-data 2 次請求，見 revisions／b12）
R['onchain'] = {}; SER = {}
for m, fld in OC.items():
    try:
        js = bd(m); ser = {}
        for r in js:
            vv = r.get(fld, r.get(fld.lower()))
            if vv not in (None, ''): ser[r['d']] = float(vv)
        SER[m] = ser; s_ = sorted(ser.items()); d_, v_ = s_[-1]
        cut = (dt.date.fromisoformat(d_) - dt.timedelta(days=1461)).isoformat(); w4 = [x for dd, x in s_ if dd >= cut]
        ma7 = sum(x for _, x in s_[-7:]) / 7; m7s = [sum(x for _, x in s_[i - 6:i + 1]) / 7 for i in range(6, len(s_))]
        R['onchain'][m] = dict(date=d_, value=v_, pct_4y=round(sum(x < v_ for x in w4) / len(w4) * 100, 1), n=len(w4),
                               chg7_pct=_dchg(ser, d_, 7, v_), chg30_pct=_dchg(ser, d_, 30, v_),
                               ma7=round(ma7, 4), ma7_pct_own=round(sum(x < ma7 for x in m7s) / len(m7s) * 100, 1))
        if m == 'illiquid-supply': R['onchain'][m]['aug31'] = ser.get('2026-08-31')
    except Exception as e: errors.append(f'onchain {m}: {e}')
try:
    # 2026-09-23 週檢：第三轉換條件量化＝STH 成本基礎 ÷ LTH 成本基礎（＝LTH-MVRV ÷ STH-MVRV，與價格無關）
    sr, lr_ = R['onchain']['sth-realized-price'], R['onchain']['lth-realized-price']
    if sr['date'] == lr_['date']:
        R['lth_sth_cost_ratio'] = dict(date=sr['date'], ratio=round(sr['value'] / lr_['value'], 3), note='2022-09~2023-03 唯一一次 ≤1.10；2023-05 起一直 >1.30')
        cd = sorted(set(SER['sth-realized-price']) & set(SER['lth-realized-price'])); rr = [SER['sth-realized-price'][d] / SER['lth-realized-price'][d] for d in cd]
        r7 = [sum(rr[i - 6:i + 1]) / 7 for i in range(6, len(rr))]; R['lth_sth_cost_ratio']['ma7'] = round(r7[-1], 4); R['lth_sth_cost_ratio']['ma7_pct_own'] = round(sum(x < r7[-1] for x in r7) / len(r7) * 100, 1); R['lth_sth_cost_ratio']['ma7_n'] = len(r7)
    else: errors.append('lth_sth_cost_ratio: 日期不一致，不計算')
except Exception as e: errors.append(f'lth_sth_cost_ratio {e}')

# ---------- C. 挖礦 ----------
try:
    hr = get('https://mempool.space/api/v1/mining/hashrate/1y')
    hs = [(ymd(x['timestamp']), x['avgHashrate'] / 1e18) for x in hr['hashrates']]; hs = [x for x in hs if x[0] <= LAST]
    m7 = sum(v for _, v in hs[-7:]) / 7; p7 = sum(v for _, v in hs[-14:-7]) / 7
    rw = get('https://mempool.space/api/v1/mining/reward-stats/144'); btcd = int(rw['totalReward']) / 1e8
    hp = btcd * c / (m7 * 1000)
    df = get('https://mempool.space/api/v1/difficulty-adjustment')
    R['mining'] = dict(hash7=round(m7, 1), hash7_prev=round(p7, 1), wk_chg_pct=round((m7 / p7 - 1) * 100, 2), window=[hs[-7][0], hs[-1][0]],
                       hash30=round(sum(v for _, v in hs[-30:]) / 30, 1), btc_day=round(btcd, 2), fee_share_pct=round(int(rw['totalFee']) / int(rw['totalReward']) * 100, 2),
                       hashprice=round(hp, 2), breakeven={f'{j}J@{e}': round(j * 24 * e / hp * c) for j, e in ((17, .05), (20, .06), (25, .07))},
                       diff_next_pct=round(df['difficultyChange'], 2), diff_progress=round(df['progressPercent'], 2), blocks_left=df['remainingBlocks'],
                       block_time_s=round(df['timeAvg'] / 1000, 1), retarget=ymd(df['estimatedRetargetDate'] / 1000))
except Exception as e: errors.append(f'mining {e}')


# ---------- E. 週檢 2026-09-23 升格的狀態讀值（只作狀態，不進任何預測調整；秩相關五年非重疊樣本不顯著） ----------
X = {}
try:
    raw = get('https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10')
    ser = [(l.split(',')[0], float(l.split(',')[1])) for l in raw.splitlines()[1:] if l.split(',')[1] not in ('.', '')]
    X['dfii10'] = dict(date=ser[-1][0], value=ser[-1][1], chg_20obs_bp=round((ser[-1][1] - ser[-21][1]) * 100))
except Exception as e: errors.append(f'dfii10 {e}')
# 2026-10-01 月度複盤：NFCI、穩定幣總市值、Coinbase 價差、OKX 未平倉退役（180 日與五年非重疊檢定皆無資訊量、本月零結論變更），不再抓取
R['extra'] = X

# ---------- F. FNG / FRED ----------
# 2026-10-01 月度複盤：恐懼貪婪指數退役（規則已隨 P19 作廢；180 日 ρ −0.04、五年非重疊 −0.04 p=0.47；本月零結論變更），不再抓取
btc = {x['d']: x['c'] for x in bars}
for sid in ('NASDAQCOM', 'DTWEXBGS', 'DGS10'):
    try:
        raw = get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}')
        ser = [(l.split(',')[0], float(l.split(',')[1])) for l in raw.splitlines()[1:] if l.split(',')[1] not in ('.', '')]
        out = dict(last_date=ser[-1][0], last=ser[-1][1])
        if sid != 'DGS10':
            sd = dict(ser); com = sorted(set(sd) & set(btc))[-31:]
            br = [math.log(btc[com[i]] / btc[com[i - 1]]) for i in range(1, len(com))]; sr = [math.log(sd[com[i]] / sd[com[i - 1]]) for i in range(1, len(com))]
            out['corr30'] = round(st.correlation(br, sr), 3)
        R.setdefault('fred', {})[sid] = out
    except Exception as e: errors.append(f'fred {sid} {e}')

# ---------- Bitstamp 四年百分位（Mayer / Pi Cycle） ----------
try:
    bsd = {}
    for endts in (int(now.timestamp()), int(now.timestamp()) - 1000 * 86400):
        for r in get(f'https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000&end={endts}')['data']['ohlc']:
            bsd[ymd(int(r['timestamp']))] = float(r['close'])
    it = sorted((d_, v) for d_, v in bsd.items() if d_ <= LAST); bc = [v for _, v in it]
    cut = (dt.date.fromisoformat(LAST) - dt.timedelta(days=1461)).isoformat()
    may = [(it[i][0], bc[i] / (sum(bc[i - 199:i + 1]) / 200)) for i in range(199, len(bc))]
    pic = [(it[i][0], (sum(bc[i - 110:i + 1]) / 111) / (2 * sum(bc[i - 349:i + 1]) / 350)) for i in range(349, len(bc))]
    m4 = [v for d_, v in may if d_ >= cut]; p4 = [v for d_, v in pic if d_ >= cut]
    R['bitstamp'] = dict(n=len(bc), mayer_pct_4y=round(sum(v < R['mayer']['mayer'] for v in m4) / len(m4) * 100, 1),
                         mayer_1_2_pct=round(sum(v < 1.2 for v in m4) / len(m4) * 100, 1),
                         pi_pct_4y=round(sum(v < R['pi_cycle'] for v in p4) / len(p4) * 100, 1))
except Exception as e: errors.append(f'bitstamp {e}')

# ---------- G. 2026-09-25 新增：頂部／底部雷達（使用者要求加重頂部鏈上指標） ----------
# G1. CoinMetrics community（免金鑰、自 2010 年、每日）：MVRV 比值、實現價、週期衰減校正、價格新高 vs MVRV 背離、交易所供給
try:
    cmj = get('https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=PriceUSD,CapMVRVCur,CapMrktCurUSD,SplyCur,SplyExNtv&frequency=1d&start_time=2010-07-18&page_size=10000')['data']
    cm = [(x['time'][:10], float(x['PriceUSD']), float(x['CapMVRVCur']) if x.get('CapMVRVCur') else None, float(x['CapMrktCurUSD']), float(x['SplyCur']),
           float(x['SplyExNtv']) if x.get('SplyExNtv') else None) for x in cmj if x.get('PriceUSD') and x.get('CapMrktCurUSD') and x.get('SplyCur') and x['time'][:10] <= LAST]   # 2026-09-26 修正：CoinMetrics 最新一天常只有 PriceUSD、其餘 null，須一併排除
    mv = [(d_, pr, m_, mc, sp) for d_, pr, m_, mc, sp, _ in cm if m_]
    dts = [x[0] for x in mv]; M_ = [x[2] for x in mv]; PR = [x[1] for x in mv]; i = len(mv) - 1
    import bisect
    def _win(j):   # 2026-10-07 a9：以日期邊界 [t−1461d, t−365d] 篩選，不以列位置代替（資料缺日時位置會偏）
        t_ = dt.date.fromisoformat(dts[j]); a_ = bisect.bisect_left(dts, (t_ - dt.timedelta(days=1461)).isoformat()); b_ = bisect.bisect_right(dts, (t_ - dt.timedelta(days=365)).isoformat())
        return max(M_[a_:b_])
    prior = _win(i)            # 前週期峰＝[t−4年, t−1年] 的 MVRV 最高值（無前視）
    mx365 = max(M_[i - 364:i + 1]); ath = max(PR[:i]); rp = mv[i][3] / mv[i][2] / mv[i][4]
    cyc = [x for x in mv if x[0] >= '2022-11-21']
    def _ratio(j): return M_[j] / _win(j)
    run75 = run80 = 0
    def _consec(j): return (dt.date.fromisoformat(dts[j]) - dt.date.fromisoformat(dts[j - 1])).days == 1   # a9：缺日＝中斷
    for j in range(i, i - 60, -1):
        if _ratio(j) >= 0.75: run75 += 1
        else: break
        if not _consec(j): break
    for j in range(i, i - 60, -1):
        if _ratio(j) >= 0.80: run80 += 1
        else: break
        if not _consec(j): break
    ex = [(d_, e) for d_, _, _, _, _, e in cm if e]
    R['cm_radar'] = dict(date=dts[i], mvrv=round(M_[i], 4), realized_price=round(rp), prior_cycle_peak=round(prior, 4),
                         mvrv_vs_prior=round(M_[i] / prior, 4), k070_price=round(0.70 * prior * rp), k075_price=round(0.75 * prior * rp), k080_price=round(0.80 * prior * rp),
                         mvrv_365d_max=round(mx365, 4), mvrv_vs_365d_max=round(M_[i] / mx365, 4), price_ath_close=round(ath), is_ath=PR[i] >= ath,
                         divergence=bool(PR[i] >= ath and M_[i] <= 0.9 * mx365),
                         p20_run_ge075=run75, p20_run_ge080=run80, p20_k075_fires=run75 >= 5, p20_k080_fires=run80 >= 5,
                         cycle_mvrv_min_since_2025top=round(min(x[2] for x in mv if x[0] >= '2025-10-06'), 4),
                         exchange_supply_btc=round(ex[-1][1]), exchange_supply_date=ex[-1][0], exchange_supply_share_pct=round(ex[-1][1] / cm[-1][4] * 100, 3),
                         exchange_supply_chg30_pct=round((ex[-1][1] / ex[-31][1] - 1) * 100, 2), exchange_supply_chg7_pct=round((ex[-1][1] / ex[-8][1] - 1) * 100, 2), exchange_supply_chg7_1y_pctile=round(sum((ex[j][1] / ex[j - 7][1] - 1) < (ex[-1][1] / ex[-8][1] - 1) for j in range(len(ex) - 365, len(ex))) / 365 * 100, 1), exchange_supply_chg90_pct=round((ex[-1][1] / ex[-91][1] - 1) * 100, 2),
                         note='CoinMetrics community；MVRV 口徑與 bitcoin-data 的 MVRV Z 不同，不相減、不混用。交易所供給為 CoinMetrics 自有地址歸屬')
except Exception as e: errors.append(f'coinmetrics {e}')
# G2. bitcoin-data 頂部雷達（放在既有 14 個端點之後；免費層文件寫每小時 10 次、每日 15 次，超額時只有這幾格記 null）
RAD = {'lth-mvrv-zscore': 'lthMvrvZscore', 'supply-in-profit-pct': 'supplyInProfitPct', 'realized-cap-growth-rate': 'realizedCapGrowthRate',
       'lth-net-position-change-30d-btc': 'lthNetPositionChange30dBtc'}
R['top_radar'] = {}
for m, fld in RAD.items():
    try:
        js = bd(m); ser = sorted((r['d'], float(r[fld])) for r in js if r.get(fld) not in (None, ''))
        cy = [v for d_, v in ser if d_ >= '2022-11-21']; v = ser[-1][1]
        at_top = [v_ for d_, v_ in ser if '2025-09-22' <= d_ <= '2025-10-20']
        R['top_radar'][m] = dict(date=ser[-1][0], value=round(v, 4), pct_since_2022_11=round(sum(x < v for x in cy) / len(cy) * 100, 1),
                                 p90_since_2022_11=round(sorted(cy)[int(len(cy) * 0.9)], 4), p10_since_2022_11=round(sorted(cy)[int(len(cy) * 0.1)], 4),
                                 extreme_near_2025_top=round((min if 'net-position' in m else max)(at_top), 4) if at_top else None)
    except Exception as e: errors.append(f'top_radar {m}: {e}')
# G4. 2026-09-29 使用者要求：籌碼流向（Murphy 框架，只作讀值、不連動 P19／P20）。bitcoin-data 每日 +4 次；失敗記 null、不推估
R['murphy_flow'] = {}; MFS = {}   # MFS：G4 抓到的完整序列，給 G4b 畫圖用（2026-10-02）
def _bd_series(m, fld):
    js = bd(m)
    try: json.dump(js, open(f'raw_{m}.json', 'w'))
    except Exception: pass
    out_ = sorted((r['d'], float(r[fld])) for r in js if r.get(fld) not in (None, '')); MFS[m] = out_
    return out_
try:
    ser = _bd_series('sth-lth-ratio', 'sthLthRatio'); d_, v = ser[-1]; dd = dict(ser)
    back = lambda k: ser[-1 - k][1] if len(ser) > k else None
    cy = [x for t, x in ser if t >= '2022-11-21']; l90 = [(t, x) for t, x in ser if t >= (dt.date.fromisoformat(d_) - dt.timedelta(days=90)).isoformat()]
    mn = min(l90, key=lambda z: z[1])
    R['murphy_flow']['sth_lth_ratio'] = dict(date=d_, value=round(v, 4), d7=round(back(7), 4), d30=round(back(30), 4),
        pct_since_2022_11=round(sum(x < v for x in cy) / len(cy) * 100, 1), min90=round(mn[1], 4), min90_date=mn[0])
except Exception as e: errors.append(f'murphy sth-lth-ratio: {e}'); R['murphy_flow']['sth_lth_ratio'] = None
try:
    ser = _bd_series('percent-sth-in-profit', 'percentSthInProfit'); d_, v = ser[-1]
    l30 = [(t, x) for t, x in ser if t >= (dt.date.fromisoformat(d_) - dt.timedelta(days=30)).isoformat()]; mn = min(l30, key=lambda z: z[1])
    R['murphy_flow']['sth_in_profit_pct'] = dict(date=d_, value=round(v, 2), d7=round(ser[-8][1], 2), min30=round(mn[1], 2), min30_date=mn[0])
except Exception as e: errors.append(f'murphy percent-sth-in-profit: {e}'); R['murphy_flow']['sth_in_profit_pct'] = None
try:
    tm = dict(_bd_series('true-market-mean', 'trueMarketMean')); sth = SER.get('sth-realized-price', {})
    cd = sorted(set(tm) & set(sth)); d_ = cd[-1]
    diff = [(t, sth[t] / tm[t] - 1) for t in cd]
    last_up = last_dn = None
    for j in range(1, len(diff)):
        if diff[j - 1][1] < 0 <= diff[j][1]: last_up = diff[j][0]
        if diff[j - 1][1] >= 0 > diff[j][1]: last_dn = diff[j][0]
    d30 = (dt.date.fromisoformat(d_) - dt.timedelta(days=30)).isoformat(); p30 = max(t for t in cd if t <= d30)
    R['murphy_flow']['sth_vs_tmm'] = dict(date=d_, sth_cost=round(sth[d_]), tmm=round(tm[d_]), sth_vs_tmm_pct=round(diff[-1][1] * 100, 2),
        sth_cost_chg30=round(sth[d_] - sth[p30]), tmm_chg30=round(tm[d_] - tm[p30]), last_cross_up=last_up, last_cross_down=last_dn,
        note='bitcoin-data 自身兩條序列同日比較；已知 2023-11-23 上穿、2026-04-27 下穿可驗算')
except Exception as e: errors.append(f'murphy true-market-mean: {e}'); R['murphy_flow']['sth_vs_tmm'] = None
try:
    js = bd('urpd')
    try: json.dump(js, open('raw_urpd.json', 'w'))
    except Exception: pass
    B = sorted((float(r['priceLower']), float(r['priceUpper']), float(r['btcSupply']), float(r.get('pctSupply') or 0)) for r in js); ud = js[-1].get('theDate'); MFS['urpd'] = B; MFS['urpd_date'] = ud
    cur = next(b for b in B if b[0] <= c < b[1])
    below = next(((lo_, hi_, bs, pc) for lo_, hi_, bs, pc in reversed(B) if hi_ <= cur[0] and bs >= 5e5), None)
    above = next(((lo_, hi_, bs, pc) for lo_, hi_, bs, pc in B if lo_ >= cur[1] and bs >= 5e5), None)
    big = max(B, key=lambda b: b[2])
    R['murphy_flow']['urpd'] = dict(date=ud, bucket_width=cur[1] - cur[0], cur_bucket=[cur[0], cur[1]], cur_btc=round(cur[2]), cur_pct=round(cur[3], 2),
        below_cluster=dict(range=[below[0], below[1]], btc=round(below[2])) if below else None, above_cluster=dict(range=[above[0], above[1]], btc=round(above[2])) if above else None,
        btc_price_to_120k=round(sum(bs for lo_, hi_, bs, pc in B if lo_ >= cur[1] and hi_ <= 120000)), largest=dict(range=[big[0], big[1]], btc=round(big[2])),
        top_buckets=[[b[0], b[1], round(b[2])] for b in sorted(B, key=lambda b: -b[2])[:6]])
except Exception as e: errors.append(f'murphy urpd: {e}')

# G4b. 2026-10-02 使用者要求：籌碼流向圖表資料（只作讀值）。不另打 API：沿用 G4 已抓的序列（MFS）、主軌 SER['sth-realized-price'] 與 Kraken 日線 bars
try:
    _ep = dt.date(1970, 1, 1)
    _dn = lambda s_: (dt.date.fromisoformat(s_) - _ep).days       # 日期 → 1970 起的天數（頁面 JS 轉回日期）
    def _thin(pairs, step):
        out = pairs[::-1][::step][::-1]
        return out
    MV = dict(top2025='2025-10-06')
    _tv = lambda m_: dict(MFS.get(m_) or []).get('2025-10-06')
    MV['top_vals'] = dict(ratio=_tv('sth-lth-ratio'), profit=_tv('percent-sth-in-profit'))   # 2025 頂部當日原值（圖上標記用，不受每 2 天取點影響）
    if MFS.get('sth-lth-ratio'):
        MV['ratio'] = [[_dn(t), round(v_, 4)] for t, v_ in _thin(MFS['sth-lth-ratio'], 2)]
    if MFS.get('percent-sth-in-profit'):
        MV['profit'] = [[_dn(t), round(v_, 1)] for t, v_ in _thin(MFS['percent-sth-in-profit'], 2)]
    _tm = dict(MFS.get('true-market-mean') or []); _sth = SER.get('sth-realized-price', {}); _px = {b_['d']: b_['c'] for b_ in bars}
    if _tm and _sth:
        d0 = (dt.date.fromisoformat(LAST) - dt.timedelta(days=730)).isoformat()
        days = sorted(t for t in set(_px) | set(_tm) | set(_sth) if t >= d0)
        rows_ = [[_dn(t), round(_px[t]) if t in _px else None, round(_sth[t]) if t in _sth else None, round(_tm[t]) if t in _tm else None] for t in days]
        rows_ = [r_ for r_ in rows_ if any(x is not None for x in r_[1:])]
        MV['cost'] = _thin(rows_, 2)   # _thin 由最後一點往回取，最新一點一定保留
    if MFS.get('urpd'):
        B_ = MFS['urpd']; lo_b = int(c * 0.62 // 2000 * 2000)
        band = [[int(b_[0]), round(b_[2])] for b_ in B_ if b_[0] >= lo_b]
        prev7 = None
        try:
            ps_ = json.load(open(a.prev_state)) if a.prev_state else None
            want = (dt.date.fromisoformat(MFS['urpd_date']) - dt.timedelta(days=7)).isoformat()
            for r_ in reversed((ps_ or {}).get('series', [])):
                u_ = ((r_.get('murphy_flow') or {}).get('urpd') or {})
                if u_.get('band') and u_.get('date') and u_['date'] <= want:
                    prev7 = dict(date=u_['date'], band=u_['band']); break
        except Exception as e: errors.append(f'murphy_viz prev7 {e}')
        MV['urpd'] = dict(date=MFS['urpd_date'], width=2000, price=round(c), band=band, prev7=prev7)
        if R['murphy_flow'].get('urpd'): R['murphy_flow']['urpd']['band'] = [[int(b_[0]), round(b_[2])] for b_ in B_ if b_[0] >= 40000]   # 寫進 series 以累積週變化
    MV['note'] = '只作讀值；供給比、STH 獲利比例每 2 天取一點（2022-10 起，bitcoin-data 免費歷史起點）；成本圖近 2 年：價格 Kraken 收盤、STH 成本與 TMM 為 bitcoin-data（市場組晚約 7 天）；URPD 2,000 美元一格'
    R['murphy_viz'] = MV
except Exception as e: errors.append(f'murphy_viz {e}')

# ---------- G5. 2026-10-02 使用者要求：掛單簿深度（Coinbase／Kraken／Bitstamp 三家合計，舊口徑保留供序列比較；Binance 現貨改由 G5b 經 data-api.binance.vision 取得，Binance 期貨 451、Bybit 403 不可用）。只作讀值，不連動任何規則 ----------
try:
    OBS = {'coinbase': 'https://api.exchange.coinbase.com/products/BTC-USD/book?level=2',
           'kraken': 'https://api.kraken.com/0/public/Depth?pair=XBTUSD&count=500',
           'bitstamp': 'https://www.bitstamp.net/api/v2/order_book/btcusd/'}
    books = {}
    for nm, u in OBS.items():
        try:
            j = get(u)
            if nm == 'kraken': j = [v for kk_, v in j['result'].items()][0]
            bb_ = [(float(x[0]), float(x[1])) for x in j['bids']]; aa_ = [(float(x[0]), float(x[1])) for x in j['asks']]
            if bb_ and aa_: books[nm] = (bb_, aa_)
        except Exception as e: errors.append(f'orderbook {nm}: {e}')
    if books:
        mids = {nm: (bb_[0][0] + aa_[0][0]) / 2 for nm, (bb_, aa_) in books.items()}
        mid = st.median(mids.values())
        def _band(pct):
            bsum = sum(p_ * q_ for bb_, aa_ in books.values() for p_, q_ in bb_ if p_ >= mid * (1 - pct))
            asum = sum(p_ * q_ for bb_, aa_ in books.values() for p_, q_ in aa_ if p_ <= mid * (1 + pct))
            return round(bsum / 1e6, 1), round(asum / 1e6, 1), round((bsum - asum) / (bsum + asum), 3) if bsum + asum else None
        b1, a1, i1 = _band(0.01); b2, a2, i2 = _band(0.02)
        def _walls(side):
            bins = {}
            for bb_, aa_ in books.values():
                for p_, q_ in (aa_ if side == 'ask' else bb_):
                    if (side == 'ask' and mid < p_ <= mid * 1.05) or (side == 'bid' and mid * 0.95 <= p_ < mid):
                        k_ = int(p_ // 250 * 250); bins[k_] = bins.get(k_, 0) + p_ * q_
            return [[k_, round(v_ / 1e6, 1)] for k_, v_ in sorted(bins.items(), key=lambda z: -z[1])[:3]]
        cov = {nm: [max(-50.0, round((bb_[-1][0] / mids[nm] - 1) * 100, 2)), min(50.0, round((aa_[-1][0] / mids[nm] - 1) * 100, 2))] for nm, (bb_, aa_) in books.items()}   # ±50 為上限（遠端垃圾掛單）
        per = {}
        for nm, (bb_, aa_) in books.items():
            bs_ = sum(p_ * q_ for p_, q_ in bb_ if p_ >= mid * 0.99); as_ = sum(p_ * q_ for p_, q_ in aa_ if p_ <= mid * 1.01)
            per[nm] = [round(bs_ / 1e6, 1), round(as_ / 1e6, 1)]
        R['orderbook'] = dict(ts=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'), exchanges=sorted(books), mid=round(mid),
                              bid1_musd=b1, ask1_musd=a1, imb1=i1, bid2_musd=b2, ask2_musd=a2, imb2=i2,
                              ask_walls_5pct=_walls('ask'), bid_walls_5pct=_walls('bid'), per_exchange_1pct=per, coverage_pct=cov,
                              note='快照（非全日）；imb＝(買−賣)/(買+賣)；Kraken 只回 500 檔，覆蓋不足 ±2%／±5% 的部分低估；掛單可隨時撤，只作讀值')
except Exception as e: errors.append(f'orderbook {e}')

# ---------- G5b. 2026-10-02 使用者要求：掛單簿全景（大範圍柱狀圖用）。只作讀值，不連動任何規則 ----------
# 寬範圍 ±15%（每 1,000 美元一格，與 Hyperliquid 的桶寬一致）只收「整本掛單簿都抓得到」的場所，近價 ±1%（每 100 美元一格）另收 Binance／OKX 等只回近價的場所。
# 不同場所的數字只做加總（同一單位：美元名目），不相減。USDT／USDC 計價視同美元（價差約 0.1% 以內，小於一格）。
try:
    import concurrent.futures as _cf
    def _post(u, body):
        try:
            out = subprocess.run(['curl', '-sS', '--max-time', '30', '-X', 'POST', '-H', 'Content-Type: application/json', '-d', json.dumps(body), u], capture_output=True, text=True).stdout
            return json.loads(out)
        except Exception as e:
            errors.append(f'orderbook_viz post {u}: {e}'); return None
    _pq = lambda rows: [(float(r[0]), float(r[1])) for r in rows]
    # 每個場所：(標籤, 類型, 計價, 抓取函式→(bids, asks)，每列 (價格, 美元名目), 桶寬, 桶方向)
    # 桶方向：None＝逐價；'agg'＝交易所已把掛單併成桶（買方桶 p 代表 [p, p+w)，賣方桶 p 代表 (p−w, p]）
    def _usd(rows): return [(p_, p_ * q_) for p_, q_ in rows]
    def _f_coinbase():
        j = get('https://api.exchange.coinbase.com/products/BTC-USD/book?level=2'); return _usd(_pq(j['bids'])), _usd(_pq(j['asks']))
    def _f_bitstamp():
        j = get('https://www.bitstamp.net/api/v2/order_book/btcusd/'); return _usd(_pq(j['bids'])), _usd(_pq(j['asks']))
    def _f_gemini():
        j = get('https://api.gemini.com/v1/book/btcusd?limit_bids=0&limit_asks=0')
        return _usd([(float(x['price']), float(x['amount'])) for x in j['bids']]), _usd([(float(x['price']), float(x['amount'])) for x in j['asks']])
    def _f_bitfinex():
        j = get('https://api-pub.bitfinex.com/v2/book/tBTCUSD/P2?len=250')
        return _usd([(float(r[0]), float(r[2])) for r in j if r[2] > 0]), _usd([(float(r[0]), -float(r[2])) for r in j if r[2] < 0])
    def _f_kraken():
        j = get('https://api.kraken.com/0/public/Depth?pair=XBTUSD&count=500'); j = list(j['result'].values())[0]; return _usd(_pq(j['bids'])), _usd(_pq(j['asks']))
    def _f_binance():
        j = get('https://data-api.binance.vision/api/v3/depth?symbol=BTCUSDT&limit=5000'); return _usd(_pq(j['bids'])), _usd(_pq(j['asks']))
    def _f_okx():
        j = get('https://www.okx.com/api/v5/market/books-full?instId=BTC-USDT&sz=5000')['data'][0]; return _usd(_pq(j['bids'])), _usd(_pq(j['asks']))
    def _f_gate():
        j = get('https://api.gateio.ws/api/v4/spot/order_book?currency_pair=BTC_USDT&limit=100&interval=10'); return _usd(_pq(j['bids'])), _usd(_pq(j['asks']))
    def _f_mexc():
        j = get('https://api.mexc.com/api/v3/depth?symbol=BTCUSDT&limit=5000'); return _usd(_pq(j['bids'])), _usd(_pq(j['asks']))
    def _f_deribit():   # BTC-PERPETUAL：amount 已是美元名目
        j = get('https://www.deribit.com/api/v2/public/get_order_book?instrument_name=BTC-PERPETUAL&depth=10000')['result']; return _pq(j['bids']), _pq(j['asks'])
    def _f_krakenfut():  # PF_XBTUSD：數量以 BTC 計
        j = get('https://futures.kraken.com/derivatives/api/v3/orderbook?symbol=PF_XBTUSD')['orderBook']; return _usd(_pq(j['bids'])), _usd(_pq(j['asks']))
    def _f_okxswap():    # BTC-USDT-SWAP：每張 0.01 BTC
        j = get('https://www.okx.com/api/v5/market/books-full?instId=BTC-USDT-SWAP&sz=5000')['data'][0]
        return _usd([(float(r[0]), float(r[1]) * 0.01) for r in j['bids']]), _usd([(float(r[0]), float(r[1]) * 0.01) for r in j['asks']])
    def _f_hl(sf):
        def f():
            j = _post('https://api.hyperliquid.xyz/info', {'type': 'l2Book', 'coin': 'BTC', 'nSigFigs': sf})['levels']
            return _usd([(float(x['px']), float(x['sz'])) for x in j[0]]), _usd([(float(x['px']), float(x['sz'])) for x in j[1]])
        return f
    VEN = {   # key: (標籤, spot/perp, 計價, 函式, 桶寬)
        'coinbase': ('Coinbase', 'spot', 'USD', _f_coinbase, 0), 'bitstamp': ('Bitstamp', 'spot', 'USD', _f_bitstamp, 0),
        'gemini': ('Gemini', 'spot', 'USD', _f_gemini, 0), 'bitfinex': ('Bitfinex', 'spot', 'USD', _f_bitfinex, 100),
        'kraken': ('Kraken', 'spot', 'USD', _f_kraken, 0), 'binance': ('Binance', 'spot', 'USDT', _f_binance, 0),
        'okx': ('OKX', 'spot', 'USDT', _f_okx, 0), 'gate': ('Gate', 'spot', 'USDT', _f_gate, 10), 'mexc': ('MEXC', 'spot', 'USDT', _f_mexc, 0),
        'deribit': ('Deribit 永續', 'perp', 'USD', _f_deribit, 0), 'krakenfut': ('Kraken 永續', 'perp', 'USD', _f_krakenfut, 0),
        'okxswap': ('OKX 永續', 'perp', 'USDT', _f_okxswap, 0),
        'hyperliquid': ('Hyperliquid 永續', 'perp', 'USDC', _f_hl(2), 1000),       # 寬範圍用：每 1,000 美元一桶（20 桶）
        'hyperliquid_n': ('Hyperliquid 永續', 'perp', 'USDC', _f_hl(3), 100),     # 近價用：每 100 美元一桶（20 桶）
    }
    OB = {}
    def _run(k_):
        try:
            b_, a_ = VEN[k_][3]()
            b_ = sorted([x for x in b_ if x[0] > 0 and x[1] > 0], key=lambda z: -z[0]); a_ = sorted([x for x in a_ if x[0] > 0 and x[1] > 0], key=lambda z: z[0])
            return k_, (b_, a_) if b_ and a_ else None
        except Exception as e:
            errors.append(f'orderbook_viz {k_}: {e}'); return k_, None
    with _cf.ThreadPoolExecutor(max_workers=8) as ex_:
        for k_, v_ in ex_.map(_run, list(VEN)):
            if v_: OB[k_] = v_
    _core = [OB[k_] for k_ in ('coinbase', 'kraken', 'bitstamp', 'binance', 'gemini') if k_ in OB]
    if len(_core) >= 2:
        vmid = st.median([(b_[0][0] + a_[0][0]) / 2 for b_, a_ in _core])
        def _cov(k_):
            b_, a_ = OB[k_]; w_ = VEN[k_][4]
            return [max(-50.0, round((b_[-1][0] / vmid - 1) * 100, 2)), min(50.0, round(((a_[-1][0]) / vmid - 1) * 100, 2))]
        COV = {k_: _cov(k_) for k_ in OB}
        def _bins(keys, step, pct):
            lo_, hi_ = vmid * (1 - pct), vmid * (1 + pct)
            rows = {}   # (bin, side) -> {venue: usd}
            def add(bn, sd, k_, v_):
                if lo_ - step <= bn <= hi_:
                    d_ = rows.setdefault((bn, sd), {}); d_[k_] = d_.get(k_, 0) + v_
            for k_ in keys:
                b_, a_ = OB[k_]; w_ = VEN[k_][4]
                for sd, side_rows in (('b', b_), ('a', a_)):
                    for p_, v_ in side_rows:
                        if w_ == 0: add(int(p_ // step * step), sd, k_, v_)                      # 逐價
                        elif w_ <= step:                                                           # 細桶：以桶中點歸格（買方桶 [p,p+w)、賣方桶 (p−w,p]）
                            rep = p_ + w_ / 2 if sd == 'b' else p_ - w_ / 2; add(int(rep // step * step), sd, k_, v_)
                        else:                                                                      # 粗桶：均分到涵蓋的格子（近似）
                            s0 = p_ if sd == 'b' else p_ - w_; n_ = int(round(w_ / step))
                            for i_ in range(n_): add(int((s0 + i_ * step) // step * step), sd, k_, v_ / n_)
            out = []
            for (bn, sd), d_ in sorted(rows.items(), key=lambda z: (-z[0][0], z[0][1])):
                # 只保留在正確一側的格（買方格須低於現價、賣方格須高於現價；現價所在格兩側都留）
                if sd == 'a' and bn + step <= vmid: continue
                if sd == 'b' and bn > vmid: continue
                out.append([bn, sd, [round(d_.get(k_, 0) / 1e6, 2) for k_ in keys]])
            return out
        WIDE_PCT, NEAR_PCT = 0.15, 0.01
        wide_keys = [k_ for k_ in ('coinbase', 'bitstamp', 'gemini', 'bitfinex', 'deribit', 'krakenfut', 'hyperliquid') if k_ in OB
                     and COV[k_][0] <= -WIDE_PCT * 100 and COV[k_][1] >= WIDE_PCT * 100]
        near_keys = [k_ for k_ in ('binance', 'coinbase', 'okx', 'kraken', 'bitstamp', 'gemini', 'bitfinex', 'gate', 'mexc', 'hyperliquid_n', 'okxswap', 'deribit', 'krakenfut') if k_ in OB]
        excl = {k_: f'覆蓋只到 {COV[k_][0]}%／+{COV[k_][1]}%' for k_ in OB if k_ not in wide_keys and k_ != 'hyperliquid_n'}
        wide = _bins(wide_keys, 1000, WIDE_PCT); near = _bins(near_keys, 100, NEAR_PCT)
        def _tot(rows, sd): return {r_[0]: sum(r_[2]) for r_ in rows if r_[1] == sd}
        wa, wb = _tot(wide, 'a'), _tot(wide, 'b')
        def _top(d_, n_=5): return [[k_, round(v_, 1)] for k_, v_ in sorted(d_.items(), key=lambda z: -z[1])[:n_]]
        def _lead(rows, bn, sd, keys):
            for r_ in rows:
                if r_[0] == bn and r_[1] == sd:
                    i_ = max(range(len(keys)), key=lambda j_: r_[2][j_]); return VEN[keys[i_]][0]
            return None
        rounds = {}
        for lv in range(int(vmid * 0.85 // 5000 + 1) * 5000, int(vmid * 1.15) - 999, 5000):
            sd = 'a' if lv > vmid else 'b'; d_ = wa if sd == 'a' else wb
            v_ = d_.get(lv, 0.0); rk = sorted(d_.values(), reverse=True).index(v_) + 1 if lv in d_ else None
            rounds[str(lv)] = dict(side=sd, musd=round(v_, 1), rank=rk, of=len(d_), lead=_lead(wide, lv, sd, wide_keys))
        spot_i = [i_ for i_, k_ in enumerate(wide_keys) if VEN[k_][1] == 'spot']
        def _tot_i(rows, sd, idx): return {r_[0]: sum(r_[2][i_] for i_ in idx) for r_ in rows if r_[1] == sd}
        walls_spot = dict(ask=_top(_tot_i(wide, 'a', spot_i), 3), bid=_top(_tot_i(wide, 'b', spot_i), 3))
        def _sum(rows, sd, idx=None): return round(sum(sum(r_[2][i_] for i_ in (idx if idx is not None else range(len(r_[2])))) for r_ in rows if r_[1] == sd), 1)
        R['orderbook_viz'] = dict(
            ts=dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'), mid=round(vmid),
            wide=dict(step=1000, pct=WIDE_PCT, venues=wide_keys, rows=wide), near=dict(step=100, pct=NEAR_PCT, venues=near_keys, rows=near),
            meta={k_: dict(label=VEN[k_][0], kind=VEN[k_][1], quote=VEN[k_][2], bucket=VEN[k_][4], cov=COV[k_]) for k_ in OB},
            walls=dict(ask=[x + [_lead(wide, x[0], 'a', wide_keys)] for x in _top(wa)], bid=[x + [_lead(wide, x[0], 'b', wide_keys)] for x in _top(wb)]),
            walls_spot=walls_spot, rounds=rounds, excluded_wide=excl,
            totals=dict(wide_bid=_sum(wide, 'b'), wide_ask=_sum(wide, 'a'), wide_bid_spot=_sum(wide, 'b', spot_i), wide_ask_spot=_sum(wide, 'a', spot_i),
                        near_bid=_sum(near, 'b'), near_ask=_sum(near, 'a')),
            note='快照；寬範圍只收整本掛單簿可得的場所（現貨 Coinbase／Bitstamp／Gemini／Bitfinex，永續 Deribit／Kraken／Hyperliquid）；Binance、OKX 等 API 只回近價約 ±1%，只放在近價圖；寬範圍每 1,000 美元一格（買方格 [p, p+1000)、賣方格同）；USDT／USDC 視同美元；掛單可隨時撤，只作讀值')
        if 'orderbook' in R:   # 小摘要寫進 series（日報把 R['orderbook'] 原樣寫入 series）
            R['orderbook'].update(wide_ask_walls=R['orderbook_viz']['walls']['ask'][:3], wide_bid_walls=R['orderbook_viz']['walls']['bid'][:3],
                                  wide_bid15_musd=R['orderbook_viz']['totals']['wide_bid'], wide_ask15_musd=R['orderbook_viz']['totals']['wide_ask'],
                                  round_levels={k_: [v_['musd'], v_['rank']] for k_, v_ in rounds.items()}, wide_venues=wide_keys)
except Exception as e: errors.append(f'orderbook_viz {e}')

# ---------- G6. 2026-10-02 使用者要求：圖表化（圖表的可讀性比文字強）。不另打 API：沿用本檔已抓的資料，輸出 ex_viz 給頁面常駐圖表區 ----------
try:
    _ep6 = dt.date(1970, 1, 1); _dn6 = lambda s_: (dt.date.fromisoformat(s_) - _ep6).days
    EX = {}
    # ① 波動率：DVOL（Deribit）與 RV30（Kraken 日線，滾動 30 日）近一年，每 2 天一點
    try:
        _rv = {}
        for j_ in range(31, len(C)):
            _rv[bars[j_]['d']] = round(rv(C, 30, j_ + 1), 2)
        _dvd = dict(dvs)
        _days = sorted(t for t in set(_dvd) | set(_rv) if t >= (dt.date.fromisoformat(LAST) - dt.timedelta(days=365)).isoformat())
        _rows = [[_dn6(t), round(_dvd[t], 2) if t in _dvd else None, _rv.get(t)] for t in _days]
        EX['vol'] = dict(rows=_rows[::-1][::2][::-1], dvol_pct_1y=(R.get('dvol') or {}).get('pct_1y'))
    except Exception as e: errors.append(f'ex_viz vol {e}')
    # ② 期貨基差曲線（年化 %，排除 DTE<7）與永續資金費率
    if R.get('deriv'):
        EX['basis'] = dict(curve=R['deriv']['basis_curve'], median=R['deriv']['basis_median'], funding=R['deriv']['funding_ann'])
    # ③ 選擇權：各到期未平倉（買權／賣權，BTC）與最大季度到期的各履約價分布（現價 ±35%）
    if R.get('options'):
        exps = []
        for r_ in R['options']['expiries']:
            e_ = E.get(r_['expiry'], {})
            exps.append([r_['expiry'], r_['dte'], round(e_.get('C', 0)), round(e_.get('P', 0)), r_['maxpain']])
        big = max((r_ for r_ in R['options']['expiries'] if r_['dte'] >= 7), key=lambda z: z['oi'], default=None)
        strikes = None
        if big:
            kk_ = E[big['expiry']]['k']
            strikes = dict(expiry=big['expiry'], maxpain=big['maxpain'],
                           rows=[[K_, round(q_['C']), round(q_['P'])] for K_, q_ in sorted(kk_.items()) if c * 0.65 <= K_ <= c * 1.35 and (q_['C'] + q_['P']) >= 50])
        EX['options'] = dict(total=R['options']['total_oi'], expiries=exps, strikes=strikes)
    # ④ P20 觸發距離：CoinMetrics MVRV ÷ 前一輪高點（[t−4 年, t−1 年] 最高值，無前視），2021 起每 3 天一點
    try:
        j0 = next(j_ for j_ in range(len(dts)) if dts[j_] >= '2021-01-01')
        EX['p20'] = dict(rows=[[_dn6(dts[j_]), round(_ratio(j_), 4)] for j_ in list(range(i, j0 - 1, -3))[::-1]],
                         k075=R['cm_radar']['k075_price'], k080=R['cm_radar']['k080_price'], now=R['cm_radar']['mvrv_vs_prior'])
    except Exception as e: errors.append(f'ex_viz p20 {e}')
    # ⑤ 頂部三指標（P6）四年百分位
    EX['p6'] = {k_: (R['onchain'].get(m_) or {}).get('pct_4y') for k_, m_ in (('mvrv_z', 'mvrv-zscore'), ('nupl', 'nupl'), ('puell', 'puell-multiple'))}
    EX['p6_date'] = (R['onchain'].get('mvrv-zscore') or {}).get('date')
    EX['price'] = round(c); EX['bar_date'] = LAST
    EX['note'] = '只作讀值；波動率近一年每 2 天一點；基差排除 DTE<7；選擇權只計 Deribit；P20 比值為 CoinMetrics MVRV，口徑與 bitcoin-data 的 MVRV Z 不同'
    R['ex_viz'] = EX
except Exception as e: errors.append(f'ex_viz {e}')

# ---------- G7. 2026-10-06 使用者要求：Tidemark 頂部／底部綜合訊號（第三方公開模型 north7.github.io/tidemark，只作讀值、不連動倉位、不進預測調整） ----------
try:
    _tm = get('https://north7.github.io/tidemark/latest.json')
    if not isinstance(_tm, dict) or 'top_signal' not in _tm: raise ValueError('回應不是預期的 JSON')
    _b = _tm.get('bottom') or {}; _ct = _b.get('cycle_test') or {}; _cl = _ct.get('current_low') or {}
    _tw = (_tm.get('timing') or {}); _wh = _tw.get('expected_window_by_halving') or {}; _wl = _tw.get('expected_window_by_low') or {}
    _bw = (_b.get('timing') or {}).get('window_by_top') or {}
    _src = _tm.get('sources') or {}
    R['tidemark'] = dict(
        date=_tm.get('date'), generated_at=_tm.get('generated_at'), price_date=_tm.get('price_date'), price_usd=_tm.get('price_usd'), stale=_tm.get('stale'),
        lag_days=(dt.date.fromisoformat(LAST) - dt.date.fromisoformat(_tm['price_date'])).days if _tm.get('price_date') else None,
        top=dict(signal=_tm.get('top_signal'), level=_tm.get('signal_level'), heat=_tm.get('heat_score'), timing=_tm.get('timing_score'), zone=_tm.get('zone'), hot_categories=_tm.get('hot_categories')),
        bottom=dict(signal=_tm.get('bottom_signal'), level=_tm.get('bottom_level'), cold=_tm.get('cold_score'), timing=_tm.get('bottom_timing_score')),
        cats=[[v_.get('label'), v_.get('score'), v_.get('status'), v_.get('effective_weight')] for v_ in (_tm.get('categories') or {}).values()],
        bgroups=[[k_, (v_ or {}).get('score'), (v_ or {}).get('weight')] for k_, v_ in (_b.get('groups') or {}).items()],
        bind=[[v_.get('label'), v_.get('value'), v_.get('score')] for v_ in (_b.get('indicators') or {}).values()],
        top_window=dict(by_halving=[_wh.get('full_from'), _wh.get('center'), _wh.get('full_to')], by_low=[_wl.get('full_from'), _wl.get('center'), _wl.get('full_to')]),
        bottom_window_by_top=[_bw.get('full_from'), _bw.get('center'), _bw.get('full_to')],
        cycle_test=dict(status=_ct.get('status'), decisive_date=_ct.get('decisive_date'), verdict=_ct.get('verdict'), low_date=_cl.get('date'), low_price=_cl.get('price')),
        stale_sources=[k_ for k_, v_ in _src.items() if (v_ or {}).get('stale') or not (v_ or {}).get('available', True)],
        rules=dict(top=(_tm.get('rules') or {}).get('signal_level'), bottom=(_tm.get('rules') or {}).get('bottom_level')))
except Exception as e: errors.append(f'tidemark {e}')

# ---------- G8. 2026-10-06 使用者要求：冪律（Power Law）讀值。只用 CoinMetrics 價格（G1 已抓），無前視：每一天的合理價只用當天以前的資料擬合；只作讀值、不連動倉位 ----------
try:
    _G = dt.date(2009, 1, 3)
    _pl = [(d_, pr) for d_, pr, *_ in cm if d_ >= '2010-07-18' and pr > 0]
    _X = [math.log10((dt.date.fromisoformat(d_) - _G).days) for d_, _ in _pl]; _Y = [math.log10(pr) for _, pr in _pl]
    _sx = _sy = _sxx = _sxy = 0.0; _fit = []          # 累加最小平方：第 k 天的係數只用 0..k
    for k_, (x_, y_) in enumerate(zip(_X, _Y)):
        _sx += x_; _sy += y_; _sxx += x_ * x_; _sxy += x_ * y_; n_ = k_ + 1
        if n_ >= 365:
            b_ = (n_ * _sxy - _sx * _sy) / (n_ * _sxx - _sx * _sx); a_ = (_sy - b_ * _sx) / n_; _fit.append((a_, b_))
        else: _fit.append(None)
    _ratio = [(10 ** (_Y[k_] - (f_[0] + f_[1] * _X[k_]))) if f_ else None for k_, f_ in enumerate(_fit)]
    _a, _b = _fit[-1]; _fair = lambda D: 10 ** (_a + _b * math.log10((D - _G).days))
    _idx = {d_: k_ for k_, (d_, _) in enumerate(_pl)}
    _tops = [(d_, round(_ratio[_idx[d_]], 2)) for d_ in ('2013-12-04', '2017-12-16', '2021-11-08', '2025-10-06') if d_ in _idx]
    _bots = [(d_, round(_ratio[_idx[d_]], 2)) for d_ in ('2015-01-14', '2018-12-15', '2022-11-21', '2026-06-30') if d_ in _idx]
    _dec = [_tops[j_][1] / _tops[j_ + 1][1] for j_ in range(len(_tops) - 1)]          # 每輪頂部倍數縮小幾倍
    _nx = (round(_tops[-1][1] / max(_dec), 2), round(_tops[-1][1] / min(_dec), 2))     # 下一輪頂部倍數區間（依過去縮小倍數的最大與最小）
    _T = dt.date(2029, 10, 1); _f29 = _fair(_T)
    R['powerlaw'] = dict(date=_pl[-1][0], price=round(_pl[-1][1], 1), fair=round(_fair(dt.date.fromisoformat(_pl[-1][0]))), ratio=round(_ratio[-1], 3),
                         slope=round(_b, 3), intercept=round(_a, 3), tops=_tops, bottoms=_bots, top_decay=[round(z_, 2) for z_ in _dec],
                         next_top_ratio=_nx, fair_2029_10=round(_f29), next_top_price=[round(_f29 * _nx[0], -3), round(_f29 * _nx[1], -3)],
                         bottom_band=[min(z_[1] for z_ in _bots), max(z_[1] for z_ in _bots)],
                         note='log10(價)＝a＋b·log10(距 2009-01-03 天數)，每天只用當天以前的 CoinMetrics 價格擬合（無前視）；頂部推估＝最近一次頂部倍數 ÷ 過去每輪縮小倍數（最大～最小），乘 2029-10-01 合理價；樣本只有 4 輪，僅作長期路徑交叉驗證，不連動倉位')
    if R.get('ex_viz') is not None:
        _ep8 = dt.date(1970, 1, 1)
        R['ex_viz']['powerlaw'] = dict(rows=[[(dt.date.fromisoformat(_pl[k_][0]) - _ep8).days, round(math.log10(_ratio[k_]), 4)] for k_ in range(len(_pl) - 1, -1, -5) if _ratio[k_] and _pl[k_][0] >= '2012-01-01'][::-1],
                                       **{k_: R['powerlaw'][k_] for k_ in ('date', 'ratio', 'fair', 'tops', 'bottoms', 'bottom_band', 'next_top_ratio', 'next_top_price', 'fair_2029_10')})
except Exception as e: errors.append(f'powerlaw {e}')

# G3. P19 狀態：收盤連續幾日在 200 日均線之下（Kraken）
try:
    run = 0
    for j in range(n - 1, 199, -1):
        if C[j] < sum(C[j - 199:j + 1]) / 200: run += 1
        else: break
    LAD = (125000, 135000, 145000, 155000, 165000, 180000, 195000, 215000); done = set()
    if a.prev_state:   # 2026-10-07 a6：由帳目（已成交＋已註銷）推導下一個未完成階，不再以價格推
        try:
            _ps = json.load(open(a.prev_state))['_conventions']['position_framework_p19_state']
            done = {int(x if not isinstance(x, dict) else x.get('level')) for x in (_ps.get('ladder_filled') or []) + (_ps.get('cancelled_price_levels') or [])}
        except Exception as e: errors.append(f'p19 ledger {e}')
    open_ = [x for x in LAD if x not in done]
    R['p19'] = dict(sma200=round(sum(C[-200:]) / 200, 1), close=c, below_sma200_run=run, next_ladder=(open_[0] if open_ else None),
                    triggered_today=[x for x in open_ if c >= x], ladder_done=sorted(done),
                    note='next_ladder＝帳目上第一個未完成階；triggered_today＝本根收盤 ≥ 的未完成階（多階同日照順序扣量，見 _conventions.active_rules）')
except Exception as e: errors.append(f'p19 {e}')

# ---------- 前一日對照（若給 --prev-state） ----------
if a.prev_state:
    try:
        ps = json.load(open(a.prev_state)); last = ps['series'][-1]
        R['prev_row'] = {k_: last.get(k_) for k_ in ('bar_date', 'c', 'atr14', 'atr7', 'dvol', 'perp_minus_basis_pp_samesource', 'fng', 'mayer', 'two_week_count', 'rv30')}
        _pr = next((r_ for r_ in reversed(ps['series']) if r_.get('bar_date') == bars[-2]['d']), None)   # 2026-10-07 a5：按日期比對
        if not _pr or _pr.get('atr14') is None or _pr.get('atr7') is None: R['atr_backtest_match'] = 'incomparable'
        else: R['atr_backtest_match'] = abs(R['atr']['backtest_prev_atr14'] - _pr['atr14']) < 0.2 and abs(R['atr']['backtest_prev_atr7'] - _pr['atr7']) < 0.2
    except Exception as e: errors.append(f'prev_state {e}')
# 2026-10-07 a1：觸及機率改為「五次日收盤」事件（固定種子蒙地卡羅）；舊連續反射公式改名 touch5d_continuous 只作參考
try:
    import numpy as np
    _s1 = R['_sig1']; _rng = np.random.default_rng(20261006); _cum = np.cumsum(_rng.normal(0.0, _s1, size=(200000, 5)), axis=1)
    _mx, _mn = _cum.max(axis=1), _cum.min(axis=1)
    _lv = {a.up, a.down, (R.get('p13_resistance_feature') or {}).get('r20_max_close'), round(R['ma']['sma20']), R['volprofile']['va_high_outer'], R['volprofile']['poc']}
    _b = int(c // 1000 * 1000); _lv |= {_b - 1000, _b, _b + 1000, _b + 2000}
    _lv = sorted(round(x) for x in _lv if x)
    def _tmc(L_):
        g_ = math.log(L_ / c)
        return round(float((_mx >= g_).mean() if L_ > c else (_mn <= g_).mean()) * 100, 1)
    R['touch5d'] = {str(x): _tmc(x) for x in _lv}
    R['touch5d_continuous'] = {str(x): round(min(1, 2 * N(-abs(math.log(x / c)) / (_s1 * math.sqrt(5)))) * 100, 1) for x in _lv}
except Exception as e: errors.append(f'touch5d {e}')
R.pop('_sig5', None); R.pop('_sig1', None)
R['bd_rotation'] = R_bd
R['errors'] = errors
json.dump(R, open('today.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k_: R[k_] for k_ in ('bar_date', 'bar', 'mayer', 'baserate') if k_ in R}, ensure_ascii=False))
print('t5_baserate', R.get('t5_baserate')); print('errors', errors)
