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
# 2026-11-04 使用者要求（gaah_im 的已實現波動率年低）：RV30 在近一年（365 根日線）裡的百分位、一年最低值與日期。只作讀值
try:
    _rv1y = [(bars[i]['d'], rv(C, 30, i + 1)) for i in range(n - 365, n)]; _mn = min(_rv1y, key=lambda z: z[1])
    R['vol'].update(rv30_pct1y=round(sum(v_ < R['vol']['rv30'] for _, v_ in _rv1y) / len(_rv1y) * 100, 1), rv30_min1y=round(_mn[1], 1), rv30_min1y_date=_mn[0])
except Exception as e: errors.append(f'rv30 一年分位 {e}')
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
        note='判定規則見 build.py stage_p23；佐證燈號見 stage_evidence')
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
    # 真 25Δ RR。2026-10-12 改為 30 天固定期限：取 30 天前後最近的兩個到期（各自 OI ≥ 1000 顆、DTE ≥ 7），
    #   各自求 25Δ 買權／賣權與 ATM 的隱含波動，再以總變異數（σ²T）線性內插到 30 天。舊規則只取 DTE 20–45 的單一到期，
    #   月度到期之間（例如 18 天與 46 天）每月約一週算不出來。兩側缺一時退回舊規則。
    def smile(r_):
        ex_, T_ = r_['expiry'], (r_['dte'] + 8 / 24) / 365; F_ = ix * math.exp(R['deriv']['basis_median'] / 100 * T_)
        def dl(K, cp, s):
            d1 = (math.log(F_ / K) + .5 * s * s * T_) / (s * math.sqrt(T_)); return N(d1) if cp == 'C' else N(d1) - 1
        def at(cp, tgt):
            arr = sorted((dl(K, cp, s), K, s) for K, c_, s in E[ex_]['iv'] if c_ == cp)
            for (d0, k0, s0), (d1_, k1, s1) in zip(arr, arr[1:]):
                if (d0 - tgt) * (d1_ - tgt) <= 0:
                    w = (tgt - d0) / (d1_ - d0) if d1_ != d0 else 0; return s0 + (s1 - s0) * w, k0 + (k1 - k0) * w
            raise ValueError(f'{ex_} 找不到 {cp} {tgt} Δ')
        civ, ck = at('C', .25); piv, pk = at('P', -.25)
        atm = min((z for z in E[ex_]['iv'] if z[1] == 'C'), key=lambda z: abs(z[0] - F_))[2]
        return dict(T=T_, F=F_, c=civ, ck=ck, p=piv, pk=pk, a=atm, r=r_)
    lo_ = [r for r in rows if 7 <= r['dte'] < 30]; hi2 = [r for r in rows if r['dte'] >= 30]
    if lo_ and hi2:
        s1_, s2_ = smile(lo_[-1]), smile(hi2[0]); T30 = 30 / 365; wq = (T30 - s1_['T']) / (s2_['T'] - s1_['T'])
        iv30 = lambda k_: math.sqrt(max((s1_[k_] ** 2 * s1_['T'] + (s2_[k_] ** 2 * s2_['T'] - s1_[k_] ** 2 * s1_['T']) * wq) / T30, 0))
        civ, piv, atm = iv30('c'), iv30('p'), iv30('a')
        R['rr25'] = dict(expiry='30d', method='30 天固定期限（' + s1_['r']['expiry'] + '／' + s2_['r']['expiry'] + ' 總變異數內插）', dte=30,
                         pair=[s1_['r']['expiry'], s2_['r']['expiry']], fwd=round(s1_['F'] + (s2_['F'] - s1_['F']) * wq), atm_iv=round(atm * 100, 2),
                         call_iv=round(civ * 100, 2), put_iv=round(piv * 100, 2), rr=round((civ - piv) * 100, 2),
                         rr_near=round((s1_['c'] - s1_['p']) * 100, 2), rr_far=round((s2_['c'] - s2_['p']) * 100, 2))
    else:
        cand = [r for r in rows if 20 <= r['dte'] <= 45]
        if cand:
            s1_ = smile(cand[0])
            R['rr25'] = dict(expiry=cand[0]['expiry'], method='單一到期（DTE 20–45）', dte=cand[0]['dte'], fwd=round(s1_['F']), atm_iv=round(s1_['a'] * 100, 2),
                             call_iv=round(s1_['c'] * 100, 2), call_k=round(s1_['ck']), put_iv=round(s1_['p'] * 100, 2), put_k=round(s1_['pk']), rr=round((s1_['c'] - s1_['p']) * 100, 2))
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
# B0（原 B9，2026-11-04 移到鏈上段最前面：B 段的長短期持有者成本、SOPR 也用它）。使用者決定：短期持有者成本 vs 真實市場均價改用 Bitview（當天、免費；bitcoin-data 晚約 7 天、真實市場均價偏高約 1.5%），
#   並新增短期持有者成本帶與 6–12／12–18 個月成本線（見 bitview.py、G4f）。兩條線一律同一家（_CSRC）；Bitview 失敗且快取超過 4 天時退回 bitcoin-data。
#   每天拿 CheckOnChain 的真實市場均價驗算，差超過 0.5% 記進 errors
BV, _ST, _TM, _CSRC, _BVCHK = None, None, None, 'bitcoin-data', None
try:
    import bitview
    _bvr, _bvst = bitview.get(); BV = bitview.cols(_bvr)
    if _bvst != 'live': errors.append(f'bitview 用快取：{_bvst}')
    if BV['sth'] and BV['tmm']: _ST, _TM, _CSRC = BV['sth'], BV['tmm'], 'Bitview'
    try:
        _BVCHK = bitview.check_tmm(BV['tmm'])
        if abs(_BVCHK['diff_pct']) > 0.5: errors.append(f"bitview 真實市場均價和 CheckOnChain 差 {_BVCHK['diff_pct']}%（{_BVCHK['date']}）")
    except Exception as e: errors.append(f'bitview 驗算（CheckOnChain 真實市場均價）: {e}')
except Exception as e: errors.append(f'bitview: {e}（短期持有者成本 vs 真實市場均價退回 bitcoin-data）')
# 2026-10-12：mvrv-zscore、nupl、puell-multiple 改由 G1a 用 CoinMetrics 自算（bitcoin-data 版晚約 6 天）；sopr、realized-price 退役（見 bd_rotation.py）
# 2026-10-15：sth-sopr 改用 CheckOnChain（晚約 1 天，見下方 B2 與 coc.py），不再向 bitcoin-data 要（它的 SOPR 系列晚約 7 天）
OC = {'asopr': 'aSopr',
      'lth-sopr': 'lthSopr', 'sth-realized-price': 'sthRealizedPrice',
      'lth-realized-price': 'lthRealizedPrice', 'illiquid-supply': 'illiquidSupply', 'highly-liquid-supply': 'highlyLiquidSupply'}
# 2026-10-01 月度複盤：reserve-risk、active-addresses 退役（零資訊量、零結論變更；省 bitcoin-data 2 次請求，見 revisions／b12）
R['onchain'] = {}; SER = {}
def _oc_stat(m, ser):   # 鏈上指標表的統一算法：最新值、四年百分位、7／30 日變化、7 日均與其百分位
    SER[m] = ser; s_ = sorted(ser.items()); d_, v_ = s_[-1]
    cut = (dt.date.fromisoformat(d_) - dt.timedelta(days=1461)).isoformat(); w4 = [x for dd, x in s_ if dd >= cut]
    ma7 = sum(x for _, x in s_[-7:]) / 7; m7s = [sum(x for _, x in s_[i - 6:i + 1]) / 7 for i in range(6, len(s_))]
    return dict(date=d_, value=v_, pct_4y=round(sum(x < v_ for x in w4) / len(w4) * 100, 1), n=len(w4),
                chg7_pct=_dchg(ser, d_, 7, v_), chg30_pct=_dchg(ser, d_, 30, v_),
                ma7=round(ma7, 4), ma7_pct_own=round(sum(x < ma7 for x in m7s) / len(m7s) * 100, 1))
# 2026-11-04 使用者要求：長短期持有者成本、aSOPR、長期持有者 SOPR 改用 Bitview（B0；bitcoin-data 版晚 6–7 天，也省它的每日額度）。
#   Bitview 失敗時，成本兩項即時向 bitcoin-data 要（不經輪替快取）；兩個 SOPR 已移出輪替，當天就記「本日未取得」
OC_BV = {'sth-realized-price': 'sth', 'lth-realized-price': 'lth', 'asopr': 'asopr', 'lth-sopr': 'lsopr'}
for m, fld in OC.items():
    if m in OC_BV and BV and BV.get(OC_BV[m]):
        try: R['onchain'][m] = dict(_oc_stat(m, BV[OC_BV[m]]), source='Bitview'); continue
        except Exception as e: errors.append(f'onchain {m}（Bitview）: {e}')
    try:
        js = bd_rotation.fetch(m) if m in ('sth-realized-price', 'lth-realized-price') else bd(m); ser = {}
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
# B2. 2026-10-15 使用者選擇：STH-SOPR 改讀 CheckOnChain 公開圖表（晚約 1 天；失敗時用上次成功的快取），不佔 bitcoin-data 額度
_cs = None
try:
    import coc
    _cs, _cst = coc.get()
    R['onchain']['sth-sopr'] = dict(_oc_stat('sth-sopr', _cs), source='CheckOnChain', source_url=coc.PAGE)
    if _cst != 'live': errors.append(f'checkonchain sth-sopr 用快取：{_cst}')
except Exception as e: errors.append(f'checkonchain sth-sopr: {e}')
# B3. 2026-10-23 使用者要求：短期持有者實現獲利／實現虧損分開兩條（CheckOnChain，BTC，已平滑），分辨 SOPR 升降是哪一邊帶動的
_pnl = None
try:
    import coc
    _pnl, _pst = coc.get_pnl()
    if _pst != 'live': errors.append(f'checkonchain sth-pnl 用快取：{_pst}')
except Exception as e: errors.append(f'checkonchain sth-pnl: {e}')
# B4. 2026-10-28 使用者要求：長短期持有者的實際籌碼分布（CheckOnChain urpd_cohort，Bitcoin Research Kit 依每顆幣的實際幣齡算），
#   給 G4e「現在」那一張用，取代推算值。圖上沒有日期，推定與同一輪 STH-SOPR 的最新一天相同；不佔 bitcoin-data 額度
_coh = None
try:
    import coc
    _coh, _chst = coc.get_cohort(max(_cs) if _cs else None)
    if _chst != 'live': errors.append(f'checkonchain urpd-cohort 用快取：{_chst}')
except Exception as e: errors.append(f'checkonchain urpd-cohort: {e}')
_sec = _rpl = _hw1 = None   # B5–B7 只抓資料；圖表在 G1 CoinMetrics 之後用統一的價格算（見 G1b）
# B5. 2026-11-02 使用者要求（Murphy〈卖方衰竭指数〉）：賣方衰竭常數（CheckOnChain，從 2010 起、晚約 1 天；見 coc.get_sec、stage_viz.sec_viz）
try:
    import coc, stage_viz
    _sec, _sest = coc.get_sec()
    if _sest != 'live': errors.append(f'checkonchain seller-exhaustion 用快取：{_sest}')
except Exception as e: errors.append(f'checkonchain seller-exhaustion: {e}')
# B6. 2026-11-02 使用者要求（貝格先生的 Realized P/L 比率）：全網實現獲利 ÷ 實現虧損（CheckOnChain；90 天平均，見 coc.get_rpl、stage_viz.rpl_viz）
try:
    import coc, stage_viz
    _rpl, _rpst = coc.get_rpl()
    if _rpst != 'live': errors.append(f'checkonchain realised-pl-ratio 用快取：{_rpst}')
except Exception as e: errors.append(f'checkonchain realised-pl-ratio: {e}')
# B7. 2026-11-03 使用者要求（CryptoQuant 的 Apparent Demand）：表觀需求＝30 天新挖出的幣 − 30 天內 1 年以上未動供給的變化（CheckOnChain HODL Waves；見 coc.get_hodl1y、stage_viz.ad_viz）
try:
    import coc, stage_viz
    _hw1, _hwst = coc.get_hodl1y()
    if _hwst != 'live': errors.append(f'checkonchain hodl-waves 用快取：{_hwst}')
except Exception as e: errors.append(f'checkonchain hodl-waves: {e}')
# B8. 2026-11-04 使用者要求（Supply In Loss % - LTH）：長期持有者虧損比例（CheckOnChain；打破規律的價位用 B4 的長期持有者籌碼 _coh 推算，見 stage_viz.lthloss_viz）
try:
    import coc, stage_viz, os
    _ll, _llst = coc.get_lthloss()
    if _llst != 'live': errors.append(f'checkonchain lth-loss 用快取：{_llst}')
    _bt = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'model.json')))['cycle_bottoms']
    R['lthloss'] = stage_viz.lthloss_viz(_ll, LAST, _bt, globals().get('_coh'))
except Exception as e: errors.append(f'checkonchain lth-loss: {e}')
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
    cmj = get('https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=PriceUSD,CapMVRVCur,CapMrktCurUSD,SplyCur,SplyExNtv,IssTotUSD,FlowInExNtv,FlowOutExNtv&frequency=1d&start_time=2010-07-18&page_size=10000')['data']
    cm = [(x['time'][:10], float(x['PriceUSD']), float(x['CapMVRVCur']) if x.get('CapMVRVCur') else None, float(x['CapMrktCurUSD']), float(x['SplyCur']),
           float(x['SplyExNtv']) if x.get('SplyExNtv') else None) for x in cmj if x.get('PriceUSD') and x.get('CapMrktCurUSD') and x.get('SplyCur') and x['time'][:10] <= LAST]   # 2026-09-26 修正：CoinMetrics 最新一天常只有 PriceUSD、其餘 null，須一併排除
    mv = [(d_, pr, m_, mc, sp) for d_, pr, m_, mc, sp, _ in cm if m_]
    # 2026-11-04 自我檢查：同一天各圖的價格統一（原本 CheckOnChain 各張圖自帶價格，11/02 四張圖差到 $70）。Kraken 日線收盤優先（頭版的價格），更早的用 CoinMetrics
    PXC = {d_: pr for d_, pr, *_ in cm}; PXC.update({b_['d']: b_['c'] for b_ in bars})
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
# G1a. 2026-10-12：頂部三指標（出場框架 P6）改用 CoinMetrics 自算，只晚 1 天（bitcoin-data 版晚約 6 天）。
#   MVRV Z＝(市值−實現市值)÷市值的全歷史標準差（到當日為止）；NUPL＝(市值−實現市值)÷市值；Puell＝當日發行美元÷近 365 日平均。
#   2026-10-05 同日對照 bitcoin-data：四年百分位 44.7／45.5／82.8 對 44.5／45.0／82.7。輸出欄位與原本 R['onchain'][m] 相同。
try:
    iss = {x['time'][:10]: float(x['IssTotUSD']) for x in cmj if x.get('IssTotUSD')}
    S3 = {'mvrv-zscore': {}, 'nupl': {}, 'puell-multiple': {}}; s1 = s2 = 0.0
    for j_, (d_, _, m_, mc_, _) in enumerate(mv):
        rc_ = mc_ / m_; s1 += mc_; s2 += mc_ * mc_; n_ = j_ + 1
        sd_ = math.sqrt(max(s2 / n_ - (s1 / n_) ** 2, 0)) if n_ > 1 else 0
        if sd_: S3['mvrv-zscore'][d_] = (mc_ - rc_) / sd_
        S3['nupl'][d_] = (mc_ - rc_) / mc_
    isd = sorted(iss)
    for j_ in range(364, len(isd)):
        if (dt.date.fromisoformat(isd[j_]) - dt.date.fromisoformat(isd[j_ - 364])).days == 364:   # 365 個連續日才算
            S3['puell-multiple'][isd[j_]] = iss[isd[j_]] / (sum(iss[t_] for t_ in isd[j_ - 364:j_ + 1]) / 365)
    for m, ser in S3.items():
        SER[m] = ser; s_ = sorted(ser.items()); d_, v_ = s_[-1]
        cut = (dt.date.fromisoformat(d_) - dt.timedelta(days=1461)).isoformat(); w4 = [x for dd, x in s_ if dd >= cut]
        ma7 = sum(x for _, x in s_[-7:]) / 7; m7s = [sum(x for _, x in s_[q_ - 6:q_ + 1]) / 7 for q_ in range(6, len(s_))]
        R['onchain'][m] = dict(date=d_, value=round(v_, 4), pct_4y=round(sum(x < v_ for x in w4) / len(w4) * 100, 1), n=len(w4),
                               chg7_pct=_dchg(ser, d_, 7, v_), chg30_pct=_dchg(ser, d_, 30, v_),
                               ma7=round(ma7, 4), ma7_pct_own=round(sum(x < ma7 for x in m7s) / len(m7s) * 100, 1), source='CoinMetrics')
except Exception as e: errors.append(f'top3 coinmetrics {e}')
# G1e. 2026-10-18 使用者要求：每日淨實現損益（Glassnode 的 Net Realized Profit/Loss 24h，只作讀值）。不另打 API：
#   實現市值（市值 ÷ MVRV）當日變化 − 當日新發行美元＝當天移動的幣「賣價 − 上次移動價」的淨和。只有淨值，沒有獲利／認賠各自的總額。
#   2026-10-18 對照 Glassnode 圖：8/1 −0.98B、8/21 +1.89B、9/22 +2.11B、10/14 −0.20B，方向與大小相符。
#   rank＝當日（÷ 市值）在之前 365 天的百分位；2015 起即時可行回測（每串取第一天）：≤2 的認賠高峰之後與平常無異；≥98 的獲利高峰之後 30 日多半續漲、逐輪減弱
try:
    _iss = {x['time'][:10]: float(x['IssTotUSD']) for x in cmj if x.get('IssTotUSD')}
    _nd = [(mv[j][0], mv[j][1], (mv[j][3] / mv[j][2] - mv[j - 1][3] / mv[j - 1][2] - _iss[mv[j][0]]), mv[j][3]) for j in range(1, len(mv))
           if mv[j][0] in _iss and (dt.date.fromisoformat(mv[j][0]) - dt.date.fromisoformat(mv[j - 1][0])).days == 1]
    _nr = [x[2] / x[3] for x in _nd]
    def _rank(j): w_ = _nr[max(0, j - 365):j]; return round(sum(v_ < _nr[j] for v_ in w_) / len(w_) * 100, 1) if len(w_) >= 300 else None
    _dn0 = lambda s_: (dt.date.fromisoformat(s_) - dt.date(1970, 1, 1)).days   # G4b 的 _dn 在後面才定義
    rows_ = [[_dn0(d_), round(p_), round(v_ / 1e6, 1), _rank(j)] for j, (d_, p_, v_, _) in enumerate(_nd) if j >= len(_nd) - 365]
    last_ = _nd[-1]
    R['npl'] = dict(date=last_[0], usd_m=round(last_[2] / 1e6, 1), rank_1y=rows_[-1][3], sum7_usd_m=round(sum(x[2] for x in _nd[-7:]) / 1e6), sum7_prev_usd_m=round(sum(x[2] for x in _nd[-14:-7]) / 1e6),
                    loss_spike_last=next((dict(date=_nd[j][0], usd_m=round(_nd[j][2] / 1e6), rank=_rank(j)) for j in range(len(_nd) - 1, len(_nd) - 366, -1) if (_rank(j) or 100) <= 2), None),
                    profit_spike_last=next((dict(date=_nd[j][0], usd_m=round(_nd[j][2] / 1e6), rank=_rank(j)) for j in range(len(_nd) - 1, len(_nd) - 366, -1) if (_rank(j) or 0) >= 98), None),
                    rows=rows_, note='CoinMetrics 實現市值日變化 − 新發行；只有淨值；rank＝之前 365 天百分位（÷ 市值）；只作讀值')
    # 2026-10-18 使用者要求：30 日累計版（週期級別的認賠）。ratio＝30 日累計 ÷ 當日市值；trig＝ratio ≤ thr 的第一天（相隔 90 天以上才算新的一次）。
    # 2026-11-04 使用者決定：thr 由「之前 4 年第 3 百分位」改成「之前 4 年（1,460 天）最大 30 日淨獲利 × −1/4」。幅度每輪變小（最大獲利 15% → 10% → 5.75%），
    #   舊規則拿上一輪熊市的大認賠當標準，本輪最深 −2.28% 只到第 7 百分位、沒有觸發。新規則即時可行回測（2015 起）：2015-01、2018-11、2020-03、2022-05、
    #   2022-11、2026-02、2026-06 七次，牛市回落最多只走到線的 46%；係數 0.24–0.27 結果相同。代價：2022 年那次由 6/16 提早到 5/20，之後再跌約 40%。
    #   看過 2026 結果才定的；2028-03 以後 2024-03 的獲利高點移出視窗，線會變淺。舊規則的觸發另存 trig_old 供對照
    _c30 = []
    for j in range(29, len(_nd)):
        if (dt.date.fromisoformat(_nd[j][0]) - dt.date.fromisoformat(_nd[j - 29][0])).days == 29:
            cs_ = sum(x[2] for x in _nd[j - 29:j + 1]); _c30.append((_nd[j][0], _nd[j][1], cs_, cs_ / _nd[j][3]))
    _cr = [x[3] for x in _c30]; c_rows, trig, last_t, trig_old, last_o, gmax = [], [], None, [], None, None
    _new = lambda d0_, lt_: lt_ is None or (dt.date.fromisoformat(d0_) - dt.date.fromisoformat(lt_)).days > 90
    for j, (d_, p_, cs_, r_) in enumerate(_c30):
        w_ = sorted(_cr[max(0, j - 1460):j])
        if d_ < '2015-01-01' or len(w_) < 700: continue
        thr_ = -0.25 * w_[-1] if w_[-1] > 0 else w_[int(len(w_) * 0.03)]; pc_ = round(sum(v_ < r_ for v_ in w_) / len(w_) * 100, 1)
        if j == len(_c30) - 1: k_ = max(range(max(0, j - 1460), j), key=lambda q_: _cr[q_]); gmax = dict(date=_c30[k_][0], pct_mcap=round(_cr[k_] * 100, 2))
        c_rows.append([_dn0(d_), round(p_), round(r_ * 100, 3), round(thr_ * 100, 3), round(cs_ / 1e6), pc_])
        if r_ <= thr_:
            if _new(d_, last_t): trig.append(dict(date=d_, x=_dn0(d_), price=round(p_), usd_m=round(cs_ / 1e6)))
            last_t = d_
        if r_ <= w_[int(len(w_) * 0.03)]:
            if _new(d_, last_o): trig_old.append(d_)
            last_o = d_
    _top = (MV.get('top2025') if 'MV' in globals() else None) or '2025-10-06'; _tx = _dn0(_top)   # 最近一次週期頂部之後最深的一點（看本輪有沒有觸發）
    _mn = min((r_ for r_ in c_rows if r_[0] >= _tx), key=lambda r_: r_[5], default=None)
    R['npl']['cum30'] = dict(date=_c30[-1][0], usd_m=c_rows[-1][4], pct_mcap=c_rows[-1][2], pct_4y=c_rows[-1][5], thr_pct_mcap=c_rows[-1][3], trig=trig, trig_old=trig_old, green_max=gmax,
                             min_since_top=dict(top=_top, x=_mn[0], price=_mn[1], pct_4y=_mn[5], usd_m=_mn[4]) if _mn else None,
                             rows=c_rows[::-1][::2][::-1], note='30 日累計 ÷ 市值；thr＝之前 4 年最大 30 日淨獲利 × −1/4（2026-11-04 起；trig_old 是舊規則 4 年第 3 百分位）；trig＝首次跌破（相隔 90 天）；2015 起每 2 天一點；只作讀值')
except Exception as e: errors.append(f'npl {e}')
# 2026-10-09 P23 修訂：市場階段的佐證燈號（只顯示、不作為門檻）。回測（2014 起、3–4 輪）沒有任何單一指標同時兼顧速度與少假訊號，
# 交易所供給 90 日轉負換視窗長度就失效、且 2025 年 99% 的日子成立，所以從牛市必要條件降為佐證之一
try:
    _d = [x[0] for x in mv]; _p = [x[1] for x in mv]; _m = [x[2] for x in mv]; _rc = [x[3] / x[2] for x in mv]; k = len(mv) - 1
    def _back(days):   # 以日期回推，不以列位置（資料缺日時位置會偏）
        import bisect
        return max(0, bisect.bisect_right(_d, (dt.date.fromisoformat(_d[k]) - dt.timedelta(days=days)).isoformat()) - 1)
    j365, j30 = _back(365), _back(30); m1y = sum(_m[k - 364:k + 1]) / 365
    ev = [dict(id='mom12', label='12 個月動能', ok=_p[k] > _p[j365], value=round((_p[k] / _p[j365] - 1) * 100, 1), unit='%', cond='收盤高於一年前', date=_d[k]),
          dict(id='mvrv1y', label='MVRV 對一年均值', ok=_m[k] > m1y, value=round(_m[k], 3), ref=round(m1y, 3), cond='MVRV 高於自己的一年均值', date=_d[k]),
          dict(id='rcgrowth', label='資金流入', ok=_rc[k] > _rc[j30], value=round((_rc[k] / _rc[j30] - 1) * 100, 2), unit='%', cond='已實現市值 30 日成長為正', date=_d[k])]
    cr = R.get('cm_radar') or {}
    if cr.get('exchange_supply_chg90_pct') is not None:
        ev.append(dict(id='xs90', label='交易所供給', ok=cr['exchange_supply_chg90_pct'] < 0, value=cr['exchange_supply_chg90_pct'], unit='%', cond='90 日變化為負', date=cr.get('exchange_supply_date')))
    sth = sorted((_ST or SER.get('sth-realized-price') or {}).items())   # 2026-11-04 起 Bitview（B9），失敗時 bitcoin-data
    if sth:
        _src = _CSRC if _ST else 'bitcoin-data'
        ev.append(dict(id='sth', label='短期持有者成本', ok=c > sth[-1][1], value=round(sth[-1][1]), cond=f'收盤高於短期持有者成本（{_src}）', src=_src, date=sth[-1][0]))
    R['stage_evidence'] = dict(items=ev, ok=sum(e['ok'] for e in ev), n=len(ev),
                               note='只作佐證、不參與判定。樣本 3–4 輪，任何規則都無法避免 2019 年式的假突破')
except Exception as e: errors.append(f'stage_evidence {e}')
# G1b. 2026-10-12 使用者要求：實現市值 30 日變化（Checkonchain「Realised Cap Liquidity Cycle」的核心），只作資金背景讀值、不作買賣訊號、不連動任何規則。
#   實現市值＝CoinMetrics 市值 ÷ MVRV（與 stage_evidence 的「資金流入」同一數字），不另外請求。回推一律以日期，不以列位置。
try:
    _ep0 = dt.date(1970, 1, 1); _dd = [dt.date.fromisoformat(x) for x in _d]
    def _ago(j, days):   # 第 j 天往前 days 天（含）最近一筆的索引；不足則 None
        t_ = (_dd[j] - dt.timedelta(days=days)).isoformat(); b_ = bisect.bisect_right(_d, t_) - 1
        return b_ if b_ >= 0 else None
    def _chg(j, days):
        b_ = _ago(j, days); return None if b_ is None else _rc[j] / _rc[b_] - 1
    ch30 = [_chg(j, 30) for j in range(len(_d))]
    def _fwd(j, days):   # 第 j 天之後 days 天的價格報酬；資料不夠長回傳 None
        t_ = (_dd[j] + dt.timedelta(days=days)).isoformat(); b_ = bisect.bisect_left(_d, t_)
        return round((_p[b_] / _p[j] - 1) * 100) if b_ < len(_d) else None
    eps, s_ = [], None   # 30 日變化 ≤ 0 的連續期間（2014 起、至少 7 天才列入，避免單日雜訊）
    for j in range(len(_d)):
        z = ch30[j] is not None and ch30[j] <= 0
        if z and s_ is None: s_ = j
        if (not z or j == len(_d) - 1) and s_ is not None:
            e_ = j if z else j - 1
            if _d[s_] >= '2014-01-01' and (_dd[e_] - _dd[s_]).days + 1 >= 7:
                eps.append(dict(start=_d[s_], end=_d[e_], days=(_dd[e_] - _dd[s_]).days + 1, px_start=round(_p[s_]), px_end=round(_p[e_]),
                                ongoing=bool(z and j == len(_d) - 1), fwd180=_fwd(e_, 180), fwd365=_fwd(e_, 365)))
            s_ = None
    run = 0; zero_now = ch30[k] <= 0
    for j in range(k, 0, -1):
        if (ch30[j] is not None and ch30[j] <= 0) == zero_now and (_dd[j] - _dd[j - 1]).days == 1: run += 1
        else: break
    rows = [[(_dd[j] - _ep0).days, round(ch30[j] * 100, 2)] for j in range(len(_d)) if _d[j] >= '2019-01-01' and ch30[j] is not None][::-3][::-1]   # 每 3 天一點（含最新一天）
    R['rc_liquidity'] = dict(date=_d[k], realized_cap_usd_b=round(_rc[k] / 1e9, 1),
                             chg30_pct=round(ch30[k] * 100, 2), chg90_pct=round(_chg(k, 90) * 100, 2), chg180_pct=round(_chg(k, 180) * 100, 2),
                             zero_now=bool(zero_now), state_run_days=run, last_episode=eps[-1] if eps else None, episodes=eps, rows=rows,
                             note='CoinMetrics community 市值 ÷ MVRV 推得；只作資金背景讀值，不作買賣訊號')
except Exception as e: errors.append(f'rc_liquidity {e}')
# G1c. 2026-10-12 使用者要求：短週期＝目前這一段行情。收盤價 15% 反轉才算新的一段（zigzag），只作讀值、不連動任何規則。
#   價格：CoinMetrics 每日（自 2010）＋ Kraken 已收盤日線補到 LAST；本輪＝2022-11-21 低點起的完成段落。
try:
    px = dict(zip(_d, _p)); px.update({b_['d']: b_['c'] for b_ in bars})
    SD = sorted(px); SP = [px[d_] for d_ in SD]; TH = 0.15
    piv, hi_, lo_, dirn = [], 0, 0, 0
    for j in range(1, len(SP)):
        if dirn == 0:
            if SP[j] > SP[hi_]: hi_ = j
            if SP[j] < SP[lo_]: lo_ = j
            if SP[j] >= SP[lo_] * (1 + TH): dirn, piv, hi_ = 1, [lo_], j
            elif SP[j] <= SP[hi_] * (1 - TH): dirn, piv, lo_ = -1, [hi_], j
        elif dirn == 1:
            if SP[j] > SP[hi_]: hi_ = j
            elif SP[j] <= SP[hi_] * (1 - TH): piv.append(hi_); dirn, lo_ = -1, j
        else:
            if SP[j] < SP[lo_]: lo_ = j
            elif SP[j] >= SP[lo_] * (1 + TH): piv.append(lo_); dirn, hi_ = 1, j
    k2 = len(SP) - 1; s0 = piv[-1]; ex_ = hi_ if dirn == 1 else lo_
    cyc = [j for j in piv if SD[j] >= '2022-11-21']
    legs = [dict(start=SD[a_], end=SD[b_], p0=round(SP[a_]), p1=round(SP[b_]), pct=round((SP[b_] / SP[a_] - 1) * 100, 1), days=(dt.date.fromisoformat(SD[b_]) - dt.date.fromisoformat(SD[a_])).days) for a_, b_ in zip(cyc, cyc[1:])]
    ups = [g for g in legs if g['pct'] > 0]; dns = [g for g in legs if g['pct'] < 0]
    cur = dict(dir='up' if dirn == 1 else 'down', start=SD[s0], p0=round(SP[s0]), ext_date=SD[ex_], ext=round(SP[ex_]), close=round(SP[k2]),
               pct=round((SP[k2] / SP[s0] - 1) * 100, 1), ext_pct=round((SP[ex_] / SP[s0] - 1) * 100, 1), days=(dt.date.fromisoformat(SD[k2]) - dt.date.fromisoformat(SD[s0])).days,
               from_ext_pct=round((SP[k2] / SP[ex_] - 1) * 100, 1), end_level=round(SP[ex_] * (1 - TH) if dirn == 1 else SP[ex_] * (1 + TH)))
    same = ups if dirn == 1 else dns
    R['swing'] = dict(date=SD[k2], threshold_pct=round(TH * 100), current=cur, legs=legs[-8:], n_up=len(ups), n_down=len(dns),
                      up_median_pct=round(st.median(g['pct'] for g in ups), 1) if ups else None, up_median_days=st.median(g['days'] for g in ups) if ups else None,
                      down_median_pct=round(st.median(g['pct'] for g in dns), 1) if dns else None, down_median_days=st.median(g['days'] for g in dns) if dns else None,
                      size_rank_pct=round(sum(abs(g['pct']) < abs(cur['ext_pct']) for g in same) / len(same) * 100) if same else None,
                      days_rank_pct=round(sum(g['days'] < cur['days'] for g in same) / len(same) * 100) if same else None,
                      note='收盤價 15% 反轉才算新的一段；本輪＝2022-11-21 低點起已完成的段落；只作讀值，不連動任何規則')
except Exception as e: errors.append(f'swing {e}')
# G1d. 2026-10-12 使用者要求：鯨魚與大戶。BitInfoCharts「依地址餘額分層的持幣量」每日歷史（2021-05 起，一次請求，不佔 bitcoin-data 額度）。
#   地址不等於實體：≥10K 多為交易所冷錢包、ETF 託管；錢包整理會讓幣在分層之間移動。只作讀值。
# 2026-10-21 暫停：BitInfoCharts 改用 Cloudflare 驗證頁擋自動抓取，免費來源找不到替代（CoinMetrics 免費層沒有分層、bitcoin-data 額度已滿）。
#   不抓、不記錯誤，頁面整塊不顯示；找到資料後把 WHALES 改回 True（或換來源）即可回補，下面的計算與頁面都保留。
# 2026-11-04 使用者要求：改用 Bitview 依地址餘額分層的每日持幣量（2011 起，B0 已抓，不另打 API），整塊恢復顯示。
#   小於 1 顆＝長短期持有者供給合計 − 1 顆以上各層；≥10K 含 10K–100K 與 100K 以上兩層。地址不等於實體：交易所、ETF 託管、提幣潮都會讓幣在層之間移動
WHALES = bool(BV and BV.get('b1'))
if WHALES:
    try:
        import bisect
        _wk = ('b1', 'b10', 'b100', 'b1k', 'b10k', 'b100k')
        WD = [d_ for d_ in sorted(BV['b1']) if d_ <= LAST and all(d_ in BV[k_] for k_ in _wk + ('sths', 'lths'))]
        WR = []
        for d_ in WD:
            b_ = [BV[k_][d_] for k_ in _wk]; WR.append((d_, [BV['sths'][d_] + BV['lths'][d_] - sum(b_)] + b_[:4] + [b_[4] + b_[5]]))
        COH = [('lt1', [0]), ('1_10', [1]), ('10_100', [2]), ('100_1k', [3]), ('1k_10k', [4]), ('ge10k', [5])]
        wv = lambda j, ix: sum(WR[j][1][q_] for q_ in ix)
        def wb(j, days):
            t_ = (dt.date.fromisoformat(WD[j]) - dt.timedelta(days=days)).isoformat(); b_ = bisect.bisect_right(WD, t_) - 1
            return b_ if b_ >= 0 and (dt.date.fromisoformat(WD[j]) - dt.date.fromisoformat(WD[b_])).days <= days + 3 else None   # 缺資料超過 3 天就不算
        k3 = len(WD) - 1; leg0 = (R.get('swing') or {}).get('current', {}).get('start')
        jl = bisect.bisect_right(WD, leg0) - 1 if leg0 else None
        out = []
        for key_, ix in COH:
            v_ = wv(k3, ix); chg = {w_: (round(v_ - wv(wb(k3, w_), ix)) if wb(k3, w_) is not None else None) for w_ in (7, 30, 90)}
            h30 = [wv(j, ix) - wv(wb(j, 30), ix) for j in range(max(0, len(WD) - 1461), len(WD)) if wb(j, 30) is not None]   # 近 4 年
            out.append(dict(key=key_, btc=round(v_), chg7=chg[7], chg30=chg[30], chg90=chg[90],
                            pct30=round(sum(x < chg[30] for x in h30) / len(h30) * 100, 1) if chg[30] is not None else None, n30=len(h30),
                            since_leg=round(v_ - wv(jl, ix)) if jl is not None and jl >= 0 else None))
        rows_w = []
        for j in range(len(WD)):
            if WD[j] < (dt.date.fromisoformat(WD[k3]) - dt.timedelta(days=400)).isoformat(): continue
            r_ = [(dt.date.fromisoformat(WD[j]) - dt.date(1970, 1, 1)).days]
            for ix in ([3], [4], [5]):
                b_ = wb(j, 30); r_.append(round(wv(j, ix) - wv(b_, ix)) if b_ is not None else None)
            rows_w.append(r_)
        R['whales'] = dict(date=WD[k3], cohorts=out, leg_start=leg0, rows=rows_w[::-2][::-1],
                           src='Bitview', note='Bitview 依地址餘額分層（2011 起；百分位用近 4 年）；地址不等於實體，≥10K 多為交易所與託管；只作讀值')
    except Exception as e: errors.append(f'whales: {e}')
# G2. bitcoin-data 頂部雷達（放在既有 14 個端點之後；免費層文件寫每小時 10 次、每日 15 次，超額時只有這幾格記 null）
RAD = {'lth-mvrv-zscore': 'lthMvrvZscore', 'supply-in-profit-pct': 'supplyInProfitPct',
       'lth-net-position-change-30d-btc': 'lthNetPositionChange30dBtc'}
R['top_radar'] = {}
for m, fld in RAD.items():
    try:
        js = bd(m); ser = sorted((r['d'], float(r[fld])) for r in js if r.get(fld) not in (None, '')); SER[m] = dict(ser)   # 2026-10-14：完整序列給鏈上走勢圖
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
    # 2026-11-04 使用者要求：改用 Bitview（2011 起、晚 1 天；圖可以畫到 2019），失敗時才即時向 bitcoin-data 要（已移出 CORE）
    if BV and BV.get('sthp'): ser = sorted(BV['sthp'].items()); MFS['percent-sth-in-profit'] = ser; _SIP_SRC = 'Bitview'
    else: ser = sorted((r_['d'], float(r_['percentSthInProfit'])) for r_ in bd_rotation.fetch('percent-sth-in-profit') if r_.get('percentSthInProfit') not in (None, '')); MFS['percent-sth-in-profit'] = ser; _SIP_SRC = 'bitcoin-data'
    d_, v = ser[-1]
    l30 = [(t, x) for t, x in ser if t >= (dt.date.fromisoformat(d_) - dt.timedelta(days=30)).isoformat()]; mn = min(l30, key=lambda z: z[1])
    R['murphy_flow']['sth_in_profit_pct'] = dict(date=d_, value=round(v, 2), d7=round(ser[-8][1], 2), min30=round(mn[1], 2), min30_date=mn[0], source=_SIP_SRC)
except Exception as e: errors.append(f'murphy percent-sth-in-profit: {e}'); R['murphy_flow']['sth_in_profit_pct'] = None
try:
    if _CSRC == 'Bitview': tm, sth = _TM, _ST   # B9；bitcoin-data 的真實市場均價只在 Bitview 失敗時才抓（省每日額度）
    else: tm = {r_['d']: float(r_['trueMarketMean']) for r_ in bd_rotation.fetch('true-market-mean') if r_.get('trueMarketMean') not in (None, '')}; sth = SER.get('sth-realized-price', {}); _ST, _TM = sth, tm   # 已移出 CORE，退回時即時抓
    cd = sorted(set(tm) & set(sth)); d_ = cd[-1]
    diff = [(t, sth[t] / tm[t] - 1) for t in cd]
    last_up = last_dn = None
    for j in range(1, len(diff)):
        if diff[j - 1][1] < 0 <= diff[j][1]: last_up = diff[j][0]
        if diff[j - 1][1] >= 0 > diff[j][1]: last_dn = diff[j][0]
    d30 = (dt.date.fromisoformat(d_) - dt.timedelta(days=30)).isoformat(); p30 = max(t for t in cd if t <= d30)
    R['murphy_flow']['sth_vs_tmm'] = dict(date=d_, sth_cost=round(sth[d_]), tmm=round(tm[d_]), sth_vs_tmm_pct=round(diff[-1][1] * 100, 2),
        sth_cost_chg30=round(sth[d_] - sth[p30]), tmm_chg30=round(tm[d_] - tm[p30]), last_cross_up=last_up, last_cross_down=last_dn,
        source=_CSRC, check=_BVCHK if _CSRC == 'Bitview' else None,
        note=(_CSRC + ' 自身兩條序列同日比較；') + ('2026-11-04 起由 bitcoin-data 改用 Bitview（bitcoin-data 版的交叉日是 2023-11-23 上穿、2026-04-26 下穿）' if _CSRC == 'Bitview' else '已知 2023-11-23 上穿、2026-04-27 下穿可驗算'))
except Exception as e: errors.append(f'murphy true-market-mean: {e}'); R['murphy_flow']['sth_vs_tmm'] = None
try:
    js = bd('urpd'); MFS['urpd_raw'] = js   # 2026-10-27：原始 63 格留給 G4e 存檔
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
        MV['profit'] = [[_dn(t), round(v_, 1)] for t, v_ in _thin([x_ for x_ in MFS['percent-sth-in-profit'] if x_[0] >= '2019-01-01'], 2)]   # 2026-11-04：Bitview 版畫到 2019
        # 2026-10-31 使用者要求：獲利比例圖上方配 BTC 週 K 對照價格。Kraken 週線（週四 00:00 UTC 起算，2013 年起）；
        #   最後一根含今天未收盤的部分，改用已收盤的日線（bars）重算到 LAST。失敗只少 K 線，獲利比例照畫
        try:
            kw_ = get('https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=10080')['result']
            kw_ = next(v_ for k_, v_ in kw_.items() if k_ != 'last'); w0 = MV['profit'][0][0] - 7
            KW = [[_dn(ymd(int(r_[0])))] + [float(x_) for x_ in r_[1:5]] for r_ in kw_ if ymd(int(r_[0])) <= LAST and _dn(ymd(int(r_[0]))) >= w0]
            bb_ = [b_ for b_ in bars if _dn(b_['d']) >= KW[-1][0]]
            if bb_: KW[-1] = [KW[-1][0], bb_[0]['o'], max(b_['h'] for b_ in bb_), min(b_['l'] for b_ in bb_), bb_[-1]['c']]
            MV['kw'] = [[r_[0]] + [round(x_) for x_ in r_[1:]] for r_ in KW]
        except Exception as e: errors.append(f'kraken 週線: {e}')
    _tm = _TM or {}; _sth = _ST or {}; _px = {b_['d']: b_['c'] for b_ in bars}   # 2026-11-04 起 Bitview（B9）
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
    MV['note'] = '只作讀值；供給比、STH 獲利比例每 2 天取一點（2022-10 起，bitcoin-data 免費歷史起點）；成本圖近 2 年：價格 Kraken 收盤、STH 成本與 TMM 為 ' + _CSRC + '（2026-11-04 起 Bitview，晚 1 天）；URPD 2,000 美元一格'
    R['murphy_viz'] = MV
except Exception as e: errors.append(f'murphy_viz {e}')
# G4d. 2026-10-15 使用者要求：籌碼集中度（Murphy 的「現價 ±5% 內籌碼佔比」，只作讀值、不套他的 13%／15% 門檻）。
#   不另打 API：G4 的 URPD（2,000 美元一格，格內視為均勻分布，按 ±5% 區間重疊比例計入）÷ CoinMetrics 流通量（G1）。
#   分母不用 bitcoin-data 的 pctSupply（其合計約 21M，大於流通量）。價格用當天收盤；URPD 本身晚約 7–9 天。歷史由 build.py 存進 data/history/index.json
try:
    B_ = MFS['urpd']; lo5, hi5 = c * 0.95, c * 1.05
    btc5 = sum(bs * max(0, min(hi_, hi5) - max(lo_, lo5)) / (hi_ - lo_) for lo_, hi_, bs, _ in B_ if hi_ > lo_)
    sply = cm[-1][4]
    R['murphy_flow']['conc5'] = dict(urpd_date=MFS['urpd_date'], price=round(c), lo=round(lo5), hi=round(hi5), btc=round(btc5), supply=round(sply),
                                     pct=round(btc5 / sply * 100, 2), note='URPD 格內均勻分布、按重疊比例計；分母為 CoinMetrics 流通量；只作讀值')
except Exception as e: errors.append(f'conc5 {e}')
# G4d-2. 2026-11-05 使用者要求（籌碼結構＋集中度）：集中度改用 Bitview 全體 URPD（log1000 分格，見 bitview.conc_rows），歷史 2018 起；
#   取得當天值時取代上面 CheckOnChain 的算法（原值留在 pct_checkonchain 對照）；取不到時沿用上面的。只作讀值
try:
    import bitview as _bvm
    _cr, _c1 = _bvm.conc_rows(LAST)
    if _c1 and _c1['date'] == LAST:
        _old = (R.get('murphy_flow') or {}).get('conc5') or {}
        R.setdefault('murphy_flow', {})['conc5'] = dict(urpd_date=LAST, price=round(_c1['close']), lo=round(_c1['close'] * 0.95), hi=round(_c1['close'] * 1.05), btc=_c1['btc5'], supply=_c1['supply'],
                                                       pct=_c1['c5'], pct10=_c1['c10'], pct_checkonchain=_old.get('pct'), src='Bitview',
                                                       note='Bitview 全體 URPD（log1000 分格）裡最後一次移動在收盤 ±5% 內的幣 ÷ 全部供給；2026-11-05 起取代 CheckOnChain 算法；只作讀值')
    R['conc_long'] = [[r[0], round(r[1]), r[2]] for r in _cr]
    # 歷史上集中度高之後的波動：前 10%（2018 起的分位）的日子 vs 其他，之後 30 天的最大單向變動；以及每次首次衝上前 10%（回到中位數以下才重新計）後 30 天漲跌
    _P = (BV or {}).get('px') or {}; _v = sorted(r[2] for r in _cr); _q = lambda p_: _v[int((len(_v) - 1) * p_)]
    def _mv(d_, n_=30):
        t_ = dt.date.fromisoformat(d_); xs = [_P[(t_ + dt.timedelta(days=k_)).isoformat()] for k_ in range(1, n_ + 1) if (t_ + dt.timedelta(days=k_)).isoformat() in _P]
        return max(abs(max(xs) / _P[d_] - 1), abs(min(xs) / _P[d_] - 1)) * 100 if d_ in _P and len(xs) >= n_ * 0.9 else None
    _hi = [m_ for m_ in (_mv(r[0]) for r in _cr if r[2] >= _q(0.9)) if m_ is not None]; _lo = [m_ for m_ in (_mv(r[0]) for r in _cr if r[2] < _q(0.9)) if m_ is not None]
    _ev, _arm = [], True
    for r in _cr:
        if _arm and r[2] >= _q(0.9):
            t_ = (dt.date.fromisoformat(r[0]) + dt.timedelta(days=30)).isoformat()
            _ev.append([r[0], r[2], round((_P[t_] / _P[r[0]] - 1) * 100, 1) if t_ in _P and r[0] in _P else None]); _arm = False
        elif not _arm and r[2] < _q(0.5): _arm = True
    _cn = R['murphy_flow']['conc5']['pct'] if (R.get('murphy_flow') or {}).get('conc5') else _cr[-1][2]
    R['conc_stats'] = dict(since=_cr[0][0], n=len(_cr), p50=_q(0.5), p90=_q(0.9), p95=_q(0.95), max=_v[-1], pct_now=round(sum(x < _cn for x in _v) / len(_v) * 100, 1),
                           hi_med30=round(st.median(_hi), 1) if _hi else None, lo_med30=round(st.median(_lo), 1) if _lo else None,
                           hi_gt15=round(sum(x > 15 for x in _hi) / len(_hi) * 100) if _hi else None, lo_gt15=round(sum(x > 15 for x in _lo) / len(_lo) * 100) if _lo else None,
                           episodes=_ev, note='之後 30 天的最大單向變動（相對當天收盤，取漲或跌較大的一邊）；價格用 Bitview 收盤；只作讀值')
except Exception as e: errors.append(f'conc bitview {e}')
# G4c. 2026-10-14 使用者要求：佐證燈號第 6 盞（短期持有者成本 vs 真實市場均價，Murphy 的 STH-RP vs TMMP；只作佐證、不參與 P23 判定），
#   與六盞燈的走勢圖資料（近 3 年、配價格線；只作讀值）。不另打 API：沿用 G1 的 CoinMetrics 與 G4 已抓的 bitcoin-data 序列。見 stage_viz.py
try:
    import stage_viz
    _tmd = _TM or {}; _sthd = _ST or {}   # 2026-11-04 起 Bitview（B9），失敗時 bitcoin-data
    _it = stage_viz.tmm_light(_sthd, _tmd, 'Bitview' if _CSRC == 'Bitview' else 'bitcoin-data，晚約 7 天') if _tmd and _sthd else None
    if _it and R.get('stage_evidence'):
        _se = R['stage_evidence']; _se['items'].append(_it); _se['ok'] = sum(e['ok'] for e in _se['items']); _se['n'] = len(_se['items'])
    R['stage_viz'] = stage_viz.build(mv, ex, _sthd, _tmd, LAST, _CSRC)
    R['onchain_viz'] = stage_viz.onchain_viz(SER)   # 鏈上指標走勢（近 3 年；價格線沿用 stage_viz 的 px）
    # 2026-10-29：價格 × 長期持有者 30 日淨部位（價格線依淨部位上色；不另打 API）
    try:
        if SER.get('lth-net-position-change-30d-btc'): R['lth_color'] = stage_viz.lth_color_viz(SER['lth-net-position-change-30d-btc'], PXC)
    except Exception as e: errors.append(f'lth_color {e}')
    # 2026-11-03：週線多空分數（六項已有訊號合成；不另打 API，實現獲利 ÷ 虧損沿用 B6 的 _rpl）
    try:
        R['regime'] = stage_viz.regime_viz(cm, _rpl, LAST, px=PXC)
    except Exception as e: errors.append(f'regime {e}')
    # 短期持有者認賠賣壓（STH-SOPR ＋ 價格；放進籌碼流向圖表資料，頁面在鏈上版）
    if SER.get('sth-sopr') and R.get('murphy_viz') is not None:
        R['murphy_viz']['sopr'] = stage_viz.sopr_viz(SER['sth-sopr'], PXC)
    if _pnl: R['sth_pnl'] = stage_viz.sth_pnl_viz(_pnl, PXC)
except Exception as e: errors.append(f'stage_viz {e}')
# G1b. 2026-11-04 自我檢查：B5–B7 抓到的 CheckOnChain 序列在這裡畫，價格欄換成統一的收盤（PXC：Kraken 優先、更早 CoinMetrics；指標本身不變）。
#   獨立一段：上面 stage_viz 出錯不影響這三張；CoinMetrics 沒抓到時沿用 CheckOnChain 自帶的價格
import stage_viz
for _k, _ser, _fn in (('sec', _sec, stage_viz.sec_viz), ('rpl', _rpl, stage_viz.rpl_viz), ('ad', _hw1, stage_viz.ad_viz)):
    if not _ser: continue
    try: R[_k] = _fn(stage_viz.canon_px(_ser, globals().get('PXC') or {}), LAST)
    except Exception as e: errors.append(f'checkonchain {_k} {e}')
# G4f. 2026-11-04 使用者要求：短期持有者成本帶（Murphy 的 STH 成本基礎模型）、6–12／12–18 個月成本線（wander）。資料 Bitview（B9），價格用統一收盤 PXC
if BV:
    for _k, _fn in (('sth_bands', stage_viz.sth_bands_viz), ('age_cost', stage_viz.age_cost_viz), ('levels', stage_viz.levels_viz), ('capflow', stage_viz.capflow_viz), ('stress', stage_viz.stress_viz)):   # levels：2026-11-04 關鍵價位圖；stress：2026-11-07 起改成賣壓累積與動能品質（本站自製，只用每日收盤）
        try: R[_k] = _fn(BV, globals().get('PXC') or {}, LAST)
        except Exception as e: errors.append(f'bitview {_k} {e}')
    # 2026-11-05 使用者要求（補充指標 PDF）：長短期持有者供給比（lsr）、長期持有者已實現虧損（lthrl，要用 model.json 的週期頂部與底部）
    try: R['lsr'] = stage_viz.lsr_viz(BV, LAST)
    except Exception as e: errors.append(f'bitview lsr {e}')
    try:
        _md = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'model.json')))
        R['lthrl'] = stage_viz.lthrl_viz(BV, globals().get('PXC') or {}, LAST, _md['cycle_bottoms'], _md['cycle_tops'])
    except Exception as e: errors.append(f'bitview lthrl {e}')
    # 2026-11-08 使用者要求：短期持有者供給 90 天變化（sthd）
    try: R['sthd'] = stage_viz.sthd_viz(BV, globals().get('PXC') or {}, LAST, _md['cycle_tops'])
    except Exception as e: errors.append(f'bitview sthd {e}')
# 2026-11-05 使用者要求（X 帳號掃描）：和前幾輪比（頂部之後的天數 × 距頂部；只用統一收盤，不靠 Bitview）
try:
    _tops = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'model.json')))['cycle_tops']
    R['cycle_cmp'] = stage_viz.cycle_cmp_viz(globals().get('PXC') or {}, _tops, LAST)
except Exception as e: errors.append(f'cycle_cmp {e}')
# G4e. 2026-10-27 使用者要求：長期／短期持有者籌碼（LTH／STH URPD，Murphy 的拆法）。bitcoin-data 的 URPD 不分持有時間，
#   用 G4 的 URPD × 前一晚 A 組快取的幣齡分布（hodl-waves-supply）× 每日價格區間（Kraken 日線、更早用 CoinMetrics）推算，見 cohort_urpd.py。
#   推算、不是實體調整，只作讀值；每天的 URPD 與幣齡分布存進 cohort_cache/（bitcoin-data 免費層的 URPD 歷史只到約 2026-08-10）
try:
    import cohort_urpd
    try: _hw = bd('hodl-waves-supply')
    except Exception as e: _hw = []; errors.append(f'cohort hodl-waves-supply: {e}')
    _px = {x[0]: (x[1], x[1]) for x in cm}; _px.update({b_['d']: (b_['l'], b_['h']) for b_ in bars})
    R['cohort'] = cohort_urpd.daily(MFS.get('urpd_raw'), _hw, _px, c, SER.get('sth-realized-price'), _coh, bitview.urpd_rows if BV else None)   # 2026-11-04：30 天前也用 Bitview 實際分布
except Exception as e: errors.append(f'cohort {e}'); R['cohort'] = None

# G4h. 2026-11-06 使用者要求（指標擴充，見 oc_extra.py、opt_flow.py；Bitview／Deribit／OKX 免費，不佔 bitcoin-data 額度）：
#   第一、二批鏈上：供給分位成本線、短期持有者虧損比例的歷次、相對未實現獲利的地板、實現虧損峰值背離、長短期供給比 30 日變化、
#   資金與價格增量梯度、鏈上勢能、回調壓力清單。第三批衍生品：Gamma 曝險（推算做市商部位）、選擇權買方權利金差、OKX 現貨主動買賣差。各項獨立，失敗只影響該項
if BV:
    try:
        import oc_extra
        _md2 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'model.json')))
        _pxc, _trf = globals().get('PXC') or {}, (R.get('cohort') or {}).get('transfers') or []
        for _k, _fn in (('quant', lambda: oc_extra.quant_viz(BV, _pxc, LAST, _md2['cycle_bottoms'])), ('sthl', lambda: oc_extra.sthl_viz(BV, _pxc, LAST)),
                        ('rup', lambda: oc_extra.rup_viz(BV, _pxc, LAST, _md2['cycle_tops'])), ('rloss', lambda: oc_extra.rloss_viz(BV, _pxc, LAST, _trf)),
                        ('lsrchg', lambda: oc_extra.lsrchg_viz(BV, _pxc, LAST, _md2['cycle_bottoms'], _md2['cycle_tops'])),
                        ('grad', lambda: oc_extra.grad_viz(BV, _pxc, LAST)), ('mom', lambda: oc_extra.mom_viz(BV, _pxc, LAST)),
                        ('pullback', lambda: oc_extra.pullback_viz(BV, _pxc, LAST, R.get('sec'), R.get('rloss')))):
            try: R[_k] = _fn()
            except Exception as e: errors.append(f'oc_extra {_k} {e}')
    except Exception as e: errors.append(f'oc_extra {e}')
    try:   # 2026-11-06 使用者要求（Bitview 推薦的都做，見 bv_extra.py）：賣方風險比、長短期持有者 NUPL、儲備風險、AVIV、依持有時間的實現損益、Dormancy／Liveliness
        import bv_extra
        _md3 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'model.json'))); _T3, _B3 = _md3['cycle_tops'], _md3['cycle_bottoms']
        for _k, _fn in (('ssr', lambda: bv_extra.ssr_viz(BV, _pxc, LAST, _T3, _B3)), ('hnupl', lambda: bv_extra.nupl_viz(BV, _pxc, LAST, _T3, _B3)),
                        ('rrisk', lambda: bv_extra.rr_viz(BV, _pxc, LAST, _T3, _B3)), ('aviv', lambda: bv_extra.aviv_viz(BV, _pxc, LAST, _T3, _B3)),
                        ('agepl', lambda: bv_extra.age_viz(BV, _pxc, LAST)), ('dorm', lambda: bv_extra.dorm_viz(BV, _pxc, LAST, _T3, _B3))):
            try: R[_k] = _fn()
            except Exception as e: errors.append(f'bv_extra {_k} {e}')
    except Exception as e: errors.append(f'bv_extra {e}')
# G4i. 2026-11-08 指標擴充：月度報酬熱力表（只用統一收盤 PXC，不打新的 API）
try: R['monthly'] = stage_viz.monthly_viz(globals().get('PXC') or {}, LAST)
except Exception as e: errors.append(f'monthly {e}')
try:
    import opt_flow
    try: _dfc = opt_flow.update_trades(now, backfill_days=3, max_pages=300)   # 快取不見時只補 3 天（完整回補一年要在本機跑）
    except Exception as e: _dfc = opt_flow._load(opt_flow.DF_CACHE, {}); errors.append(f'deribit 逐筆成交 {e}')
    try: R['gex'] = opt_flow.gex_viz(opt['result'], _dfc.get('net') or {}, now, ((R.get('murphy_viz') or {}).get('urpd') or {}).get('band'))
    except Exception as e: errors.append(f'gex {e}')
    try: R['ivterm'] = opt_flow.term_viz(opt['result'], now, LAST, globals().get('PXC') or {})   # 2026-11-08 隱含波動率期限結構（每天快照一次，快取 coc_cache/iv_term.json）
    except Exception as e: errors.append(f'ivterm {e}')
    try: R['prem'] = opt_flow.prem_viz(_dfc, globals().get('PXC') or {}, LAST)
    except Exception as e: errors.append(f'prem {e}')
    try: _okc = opt_flow.okx_update(now)
    except Exception as e: _okc = opt_flow._load(opt_flow.OK_CACHE, {}); errors.append(f'okx 主動買賣 {e}')
    try: R['svd'] = opt_flow.svd_viz(_okc, globals().get('PXC') or {}, LAST)
    except Exception as e: errors.append(f'svd {e}')
except Exception as e: errors.append(f'opt_flow {e}')

# G4i. 2026-11-06 指標擴充（見 cq_extra.py；CoinMetrics／The Block／Upbit／OKX 免費，不佔 bitcoin-data 額度）：交易所淨流量、現貨 vs 永續需求、
#   ETF 持有者成本、一年累計淨實現損益（顆）、韓國溢價、每輪資金效率。各項獨立，失敗只影響該項
try:
    import cq_extra
    _md4 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'model.json'))); _pxc4 = globals().get('PXC') or {}
    for _k, _fn in (('exflow', lambda: cq_extra.exflow_viz(cmj, _pxc4, LAST)), ('dmd', lambda: cq_extra.demand_viz(R.get('ad'), (globals().get('_okc') or {}).get('perp'), _pxc4, LAST)),
                    ('etfcost', lambda: cq_extra.etf_cost_viz(_pxc4, LAST)), ('npl365', lambda: cq_extra.npl365_viz(_nd, LAST, _md4['cycle_bottoms'], _md4['cycle_tops'])),
                    ('kp', lambda: cq_extra.kp_viz(_pxc4, LAST)), ('capeff', lambda: cq_extra.capeff_viz(mv, LAST, _md4['cycle_tops'], _md4['cycle_bottoms']))):
        try: R[_k] = _fn()
        except Exception as e: errors.append(f'cq_extra {_k} {e}')
except Exception as e: errors.append(f'cq_extra {e}')

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
        # 2026-11-04 使用者要求（Glassnode 週報的兩大到期對照）：未平倉最大的兩個到期（DTE ≥ 7）都給履約價分布，另給全部到期的買權／賣權合計
        bigs = sorted((r_ for r_ in R['options']['expiries'] if r_['dte'] >= 7), key=lambda z: -z['oi'])[:2]
        _sk = lambda r_: dict(expiry=r_['expiry'], maxpain=r_['maxpain'], rows=[[K_, round(q_['C']), round(q_['P'])] for K_, q_ in sorted(E[r_['expiry']]['k'].items()) if c * 0.65 <= K_ <= c * 1.35 and (q_['C'] + q_['P']) >= 50])
        strikes = _sk(bigs[0]) if bigs else None; strikes2 = _sk(bigs[1]) if len(bigs) > 1 else None
        cb_, pb_ = sum(v_['C'] for v_ in E.values()), sum(v_['P'] for v_ in E.values())
        EX['options'] = dict(total=R['options']['total_oi'], expiries=exps, strikes=strikes, strikes2=strikes2,
                             totals=dict(call_btc=round(cb_), put_btc=round(pb_), call_usd_b=round(cb_ * c / 1e9, 1), put_usd_b=round(pb_ * c / 1e9, 1)))
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
# ---------- G9. 2026-10-12 使用者要求：新增指標（全部免費、只作讀值、不連動任何規則） ----------
def _pctl(arr, v): arr = [x for x in arr if x is not None]; return round(sum(x < v for x in arr) / len(arr) * 100, 1) if arr else None
_ep9 = dt.date(1970, 1, 1); _dn9 = lambda s_: (dt.date.fromisoformat(s_) - _ep9).days
# G9a. 穩定幣總供給（DefiLlama，所有美元穩定幣流通量）：場外可進場的資金量
try:
    sj = get('https://stablecoins.llama.fi/stablecoincharts/all')
    sc = sorted((ymd(int(x['date'])), x['totalCirculatingUSD']['peggedUSD']) for x in sj if (x.get('totalCirculatingUSD') or {}).get('peggedUSD'))
    sc = [x for x in sc if x[0] <= LAST]; sd_ = dict(sc); dS = [x[0] for x in sc]; k9 = len(sc) - 1
    def _sb(j, days):
        t_ = (dt.date.fromisoformat(dS[j]) - dt.timedelta(days=days)).isoformat(); return sd_.get(t_)
    ch = lambda days: (round((sc[k9][1] / _sb(k9, days) - 1) * 100, 2) if _sb(k9, days) else None)
    h30 = [(sc[j][1] / _sb(j, 30) - 1) * 100 for j in range(len(sc)) if dS[j] >= '2021-01-01' and _sb(j, 30)]
    R['stables'] = dict(date=dS[k9], usd_b=round(sc[k9][1] / 1e9, 1), chg7_pct=ch(7), chg30_pct=ch(30), chg90_pct=ch(90),
                        chg30_usd_b=round((sc[k9][1] - _sb(k9, 30)) / 1e9, 1) if _sb(k9, 30) else None, pct30=_pctl(h30, ch(30)), n30=len(h30),
                        rows=[[_dn9(d_), round(v_ / 1e9, 1)] for d_, v_ in sc if d_ >= (dt.date.fromisoformat(LAST) - dt.timedelta(days=730)).isoformat()][::-3][::-1],
                        note='DefiLlama 全部美元穩定幣流通量；只作讀值')
except Exception as e: errors.append(f'stables {e}')
# G9b. Coinbase 溢價：Coinbase BTC-USD 與 Binance BTC-USDT 每日收盤的價差（%）。正值＝美國買盤較強；USDT 偏離 1 美元時會有誤差
try:
    # 2026-11-05 使用者說「沒說服力」：歷史由 300 天延長到約 4 年（Coinbase 每次最多 300 根，分 5 次；Binance 每次 1,000 根，分 2 次），列裡多帶 Coinbase 收盤給價格上格
    _e9 = dt.datetime.combine(dt.date.fromisoformat(LAST) + dt.timedelta(days=1), dt.time(), dt.timezone.utc); cb_, bn_ = {}, {}
    for k_ in range(5):
        e_ = _e9 - dt.timedelta(days=300 * k_); s_ = e_ - dt.timedelta(days=300)
        for x in get(f'https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start={s_.isoformat()}&end={e_.isoformat()}'): cb_[ymd(int(x[0]))] = float(x[4])
        __import__("time").sleep(0.3)
    et_ = int(_e9.timestamp() * 1000)
    for k_ in range(2):
        bnk = get(f'https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=1000&endTime={et_}')
        for x in bnk: bn_[ymd(int(x[0]) // 1000)] = float(x[4])
        et_ = int(bnk[0][0]) - 1
    cd9 = sorted(d_ for d_ in set(cb_) & set(bn_) if d_ <= LAST)
    pr9 = [(d_, (cb_[d_] / bn_[d_] - 1) * 100) for d_ in cd9]; v9 = [x[1] for x in pr9]
    R['cb_premium'] = dict(date=pr9[-1][0], pct=round(v9[-1], 3), avg7=round(sum(v9[-7:]) / 7, 3), avg30=round(sum(v9[-30:]) / 30, 3),
                           pct_own=_pctl(v9, v9[-1]), avg30_pct_own=_pctl([sum(v9[j - 29:j + 1]) / 30 for j in range(29, len(v9))], sum(v9[-30:]) / 30), n=len(v9),
                           rows=[[_dn9(d_), round(x_, 3), round(cb_[d_])] for d_, x_ in pr9], since=pr9[0][0], note='Coinbase BTC-USD ÷ Binance BTC-USDT 每日收盤 − 1；只作讀值')
except Exception as e: errors.append(f'cb_premium {e}')
# G9c. 2026-11-03 使用者要求（CryptoPainter 的「期現差價加權 USDT 溢價率」，權重不公開，改做三地分開看）：三地溢價的另外兩條（美國＝上面的 Coinbase 溢價）。
#   亞洲：OKX 場外 USDT/CNY 報價，買賣兩邊各取最前面 5 筆平均、取中間 ÷ OKX 的美元兌人民幣匯率 − 1。只有當下快照，歷史由 build.py 寫進 data/history/index.json 每日累積。
#   槓桿：OKX BTC 永續 ÷ 現貨，每日（UTC）收盤 − 1，近 300 天。只作讀值
R['premium3'] = {}
try:
    def _c2c(side):
        ads = get(f'https://www.okx.com/v3/c2c/tradingOrders/books?quoteCurrency=CNY&baseCurrency=USDT&side={side}&paymentMethod=all&userType=all')['data'][side]
        ps = sorted((float(x_['price']) for x_ in ads), reverse=(side == 'buy'))[:5]
        if len(ps) < 3: raise RuntimeError(f'OKX 場外 {side} 報價只有 {len(ps)} 筆')
        return sum(ps) / len(ps), ps[0], len(ads)
    s9, sb9, ns9 = _c2c('sell'); b9, bb9, nb9 = _c2c('buy')
    fx9 = float(get('https://www.okx.com/api/v5/market/exchange-rate')['data'][0]['usdCny'])
    mid9 = (s9 + b9) / 2
    R['premium3']['usdt'] = dict(ts=now.isoformat(timespec='minutes'), mid=round(mid9, 4), sell5=round(s9, 4), buy5=round(b9, 4), best_sell=sb9, best_buy=bb9,
                                 fx=fx9, pct=round((mid9 / fx9 - 1) * 100, 3), n_ads=ns9 + nb9, note='OKX 場外 USDT/CNY 買賣各前 5 筆平均的中間價 ÷ OKX 美元兌人民幣匯率 − 1；快照')
except Exception as e: errors.append(f'premium3 usdt {e}')
try:
    def _okx1d(inst):
        out_, cur_ = {}, ''
        for _ in range(3):
            d_ = get(f'https://www.okx.com/api/v5/market/history-candles?instId={inst}&bar=1Dutc&limit=100' + (f'&after={cur_}' if cur_ else ''))['data']
            if not d_: break
            for r_ in d_:
                if r_[8] == '1': out_[ymd(int(r_[0]) // 1000)] = float(r_[4])
            cur_ = d_[-1][0]
        return out_
    sw9, sp9 = _okx1d('BTC-USDT-SWAP'), _okx1d('BTC-USDT')
    pd9 = sorted(d_ for d_ in set(sw9) & set(sp9) if d_ <= LAST)
    pv9 = [(d_, (sw9[d_] / sp9[d_] - 1) * 100) for d_ in pd9]; vv9 = [x_[1] for x_ in pv9]
    a7 = [sum(vv9[j - 6:j + 1]) / 7 for j in range(6, len(vv9))]
    R['premium3']['perp'] = dict(date=pd9[-1], pct=round(vv9[-1], 4), avg7=round(a7[-1], 4), avg30=round(sum(vv9[-30:]) / 30, 4), avg7_pct_own=_pctl(a7, a7[-1]), n=len(vv9),
                                 rows=[[_dn9(d_), round(x_, 4)] for d_, x_ in pv9], note='OKX BTC-USDT 永續 ÷ 現貨 每日（UTC）收盤 − 1')
except Exception as e: errors.append(f'premium3 perp {e}')
# G9c. 算力帶（Hash Ribbons）：算力 30 日均 ÷ 60 日均。<1＝礦工投降期；由 <1 回到 >1 的那天是歷史上常見的底部訊號
try:
    hv = [x[1] for x in hs]; hd = [x[0] for x in hs]
    rib = [(hd[j], sum(hv[j - 29:j + 1]) / 30, sum(hv[j - 59:j + 1]) / 60) for j in range(59, len(hv))]
    st9 = [r_[1] >= r_[2] for r_ in rib]; run9 = 0
    for x_ in reversed(st9):
        if x_ == st9[-1]: run9 += 1
        else: break
    last_cross = next((rib[j][0] for j in range(len(rib) - 1, 0, -1) if st9[j] != st9[j - 1]), None)
    R['hash_ribbons'] = dict(date=rib[-1][0], ma30=round(rib[-1][1], 1), ma60=round(rib[-1][2], 1), ratio=round(rib[-1][1] / rib[-1][2], 4),
                             capitulation=not st9[-1], state_days=run9, last_cross=last_cross, min_ratio_90d=round(min(r_[1] / r_[2] for r_ in rib[-90:]), 4),
                             note='mempool.space 近一年每日算力；30 日均 ÷ 60 日均；只作讀值')
except Exception as e: errors.append(f'hash_ribbons {e}')
# G9d. 多家永續資金費率：Deribit（已抓）、OKX、Hyperliquid 的現值與 7 日平均（年化 %），以未平倉美元加權
try:
    fv = {}
    if R.get('deriv'): fv['Deribit'] = dict(now=R['deriv']['funding_ann'], avg7=None, oi=R['deriv']['perp_oi_usd_m'] * 1e6)
    try:
        oh = get('https://www.okx.com/api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP&limit=21')['data']
        ooi = float(get('https://www.okx.com/api/v5/public/open-interest?instId=BTC-USDT-SWAP')['data'][0]['oiUsd'])
        fv['OKX'] = dict(now=round(float(oh[0]['fundingRate']) * 3 * 365 * 100, 2), avg7=round(sum(float(x['fundingRate']) for x in oh) / len(oh) * 3 * 365 * 100, 2), oi=ooi)
    except Exception as e: errors.append(f'funding okx {e}')
    try:
        hh9 = subprocess.run(['curl', '-sS', '--max-time', '40', '-X', 'POST', 'https://api.hyperliquid.xyz/info', '-H', 'content-type: application/json', '-d',
                              json.dumps({'type': 'fundingHistory', 'coin': 'BTC', 'startTime': int((now.timestamp() - 7 * 86400) * 1000)})], capture_output=True, text=True).stdout
        hh9 = json.loads(hh9)
        ctx9 = json.loads(subprocess.run(['curl', '-sS', '--max-time', '40', '-X', 'POST', 'https://api.hyperliquid.xyz/info', '-H', 'content-type: application/json', '-d',
                                          json.dumps({'type': 'metaAndAssetCtxs'})], capture_output=True, text=True).stdout)
        bi = [u['name'] for u in ctx9[0]['universe']].index('BTC'); bc = ctx9[1][bi]
        fv['Hyperliquid'] = dict(now=round(float(bc['funding']) * 24 * 365 * 100, 2), avg7=round(sum(float(x['fundingRate']) for x in hh9) / len(hh9) * 24 * 365 * 100, 2),
                                 oi=float(bc['openInterest']) * float(bc['markPx']))
    except Exception as e: errors.append(f'funding hyperliquid {e}')
    w9 = sum(v_['oi'] for v_ in fv.values())
    R['funding_multi'] = dict(venues={k_: dict(now=v_['now'], avg7=v_['avg7'], oi_usd_m=round(v_['oi'] / 1e6)) for k_, v_ in fv.items()},
                              weighted_now=round(sum(v_['now'] * v_['oi'] for v_ in fv.values()) / w9, 2) if w9 else None,
                              note='年化 %；Deribit 為現值、OKX 每 8 小時、Hyperliquid 每小時結算；以未平倉美元加權；Binance、Bybit 讀不到')
except Exception as e: errors.append(f'funding_multi {e}')
# G9e. 恐懼貪婪指數（alternative.me）
try:
    fg = get('https://api.alternative.me/fng/?limit=400')['data']
    fg = sorted((ymd(int(x['timestamp'])), int(x['value']), x['value_classification']) for x in fg); fg = [x for x in fg if x[0] <= LAST]
    fvv = [x[1] for x in fg]
    R['fear_greed'] = dict(date=fg[-1][0], value=fvv[-1], label=fg[-1][2], d7=fvv[-8] if len(fvv) > 7 else None, avg30=round(sum(fvv[-30:]) / 30, 1),
                           pct_1y=_pctl(fvv[-365:], fvv[-1]), note='alternative.me；0 極度恐懼、100 極度貪婪；只作讀值')
except Exception as e: errors.append(f'fear_greed {e}')
# G9f. 2026-11-02 使用者要求：清算熱力圖（推算；未平倉量＋假設槓桿，見 liq_heat.py）。不佔 bitcoin-data 額度
#   2026-11-08 起用 Coinalyze 多家交易所（約 50 次、受每分鐘 40 次限制要 1–2 分鐘）；沒有 key 或失敗時照舊用 OKX（約 30 次）
try:
    import liq_heat
    R['liq_heat'] = liq_heat.build(get)
    if liq_heat.cz.ok() and R['liq_heat']['model'].get('fallback'): errors.append(f"liq_heat Coinalyze 取不到，暫用 OKX：{R['liq_heat']['model']['fallback']}")
except Exception as e: errors.append(f'liq_heat {e}')
# G9f2. 2026-11-08 使用者要求：熱力圖的長期範圍（12 小時線約 2.7 年，另存 data/liq_long.json）與每日多空清算量（Coinalyze 實際清算紀錄）。沒有 key 就跳過
try:
    if liq_heat.cz.ok(): R['liq_long'] = liq_heat.build_long()
except Exception as e: errors.append(f'liq_long {e}')
try:
    if liq_heat.cz.ok(): R['liq_vol'] = liq_heat.build_vol(last=LAST)
except Exception as e: errors.append(f'liq_vol {e}')
# G9g. 2026-11-04 使用者要求：Hyperliquid 大戶（帳戶淨值前 300 名）的 BTC 部位彙總（見 hl_whales.py；不列個別帳戶）。約 300 次 Hyperliquid 請求、2–3 分鐘
try:
    import hl_whales
    R['hl_whales'] = hl_whales.build(c, now.isoformat(timespec='minutes'))
except Exception as e: errors.append(f'hl_whales {e}')
# G9h. 2026-11-04 使用者要求（Glassnode 週報）：BTC 對 S&P 500 近 90 個交易日的勝率（BTC 當天漲幅大於標普的比例）與每日平均超額報酬；
#   以及近兩個月和 S&P 500、那斯達克、黃金（Kraken 的 PAXG 代替金價）的相對表現。BTC 用 UTC 日收盤、美股用紐約收盤，兩者差約 3 小時。只作讀值
try:
    def _fred(sid):
        raw = get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}')
        return {l.split(',')[0]: float(l.split(',')[1]) for l in raw.splitlines()[1:] if l.split(',')[1] not in ('.', '')}
    _spx, _ndq = _fred('SP500'), _fred('NASDAQCOM'); _bc = globals().get('PXC') or {b_['d']: b_['c'] for b_ in bars}
    _S = sorted(d_ for d_ in _spx if d_ in _bc and d_ <= LAST)
    _ex = [(_S[j], _bc[_S[j]] / _bc[_S[j - 1]] - 1, _spx[_S[j]] / _spx[_S[j - 1]] - 1) for j in range(1, len(_S))]
    _wr = []
    for j in range(89, len(_ex)):
        w_ = _ex[j - 89:j + 1]; _wr.append([_ex[j][0], sum(b_ > s_ for _, b_, s_ in w_) / 90 * 100, sum(b_ - s_ for _, b_, s_ in w_) / 90 * 100])
    _above = next((r_[0] for r_ in reversed(_wr[:-1]) if r_[1] > 50), None)
    _kp = get('https://api.kraken.com/0/public/OHLC?pair=PAXGUSD&interval=1440')['result']; _kp = next(v_ for k_, v_ in _kp.items() if k_ != 'last')
    _gold = {ymd(int(r_[0])): float(r_[4]) for r_ in _kp if ymd(int(r_[0])) <= LAST}
    _d0 = dt.date.fromisoformat(LAST) - dt.timedelta(days=61); _rel, _base, _lv = [], {}, {}
    for q_ in range(62):
        d_ = (_d0 + dt.timedelta(days=q_)).isoformat(); r_ = [(dt.date.fromisoformat(d_) - dt.date(1970, 1, 1)).days]
        for nm_, ser_ in (('btc', _bc), ('spx', _spx), ('ndq', _ndq), ('gold', _gold)):
            if d_ in ser_: _lv[nm_] = ser_[d_]; _base.setdefault(nm_, ser_[d_])
            r_.append(round((_lv[nm_] / _base[nm_] - 1) * 100, 2) if nm_ in _lv else None)
        _rel.append(r_)
    R['btc_vs_stocks'] = dict(date=_wr[-1][0], win90=round(_wr[-1][1], 1), excess90=round(_wr[-1][2], 3), last_above50=_above,
                              rows=[[(dt.date.fromisoformat(r_[0]) - dt.date(1970, 1, 1)).days, round(r_[1], 1), round(r_[2], 3)] for r_ in _wr if r_[0] >= '2021-01-01'][::-1][::2][::-1],
                              rel=dict(start=_d0.isoformat(), rows=_rel, last=dict(zip(('btc', 'spx', 'ndq', 'gold'), _rel[-1][1:]))),
                              note='勝率＝近 90 個美股交易日裡 BTC 漲幅大於 S&P 500 的比例；超額＝每日平均差（百分點）；BTC 用 UTC 收盤、美股紐約收盤；黃金用 PAXG；只作讀值')
except Exception as e: errors.append(f'btc_vs_stocks {e}')
R.pop('_sig5', None); R.pop('_sig1', None)
R['bd_rotation'] = R_bd
R['errors'] = errors
json.dump(R, open('today.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k_: R[k_] for k_ in ('bar_date', 'bar', 'mayer', 'baserate') if k_ in R}, ensure_ascii=False))
print('t5_baserate', R.get('t5_baserate')); print('errors', errors)
