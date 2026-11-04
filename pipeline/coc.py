"""CheckOnChain 公開圖表的 STH-SOPR（2026-10-15 使用者選擇方案 A）。
bitcoin-data 的 SOPR 系列晚約 7 天；CheckOnChain 的公開圖表（charts.checkonchain.com）晚約 1 天，而且是從 2009 起的完整日線。
做法：每天讀一次圖表頁（約 7MB），從頁內 Plotly 資料取出「STH-SOPR > 1」與「STH-SOPR < 1」兩條（同一條 STH-SOPR 依 1 拆成兩段著色），合併回原序列。
不佔 bitcoin-data 的每日額度。頁面改版或抓取失敗時，退回上一次成功存下的 coc_cache/sth-sopr.json（頁面照常顯示資料本身的日期）。
資料屬 CheckOnChain（James Check），頁面標明來源並連回原圖；與 bitcoin-data 的 STH-SOPR 是不同資料商，不互相相減。
2026-10-23 使用者要求：另讀「Realised Value [BTC]」圖（realisedpnl_bycohort_2，約 1.5MB）的短期持有者實現獲利、實現虧損兩條，
用來分辨 STH-SOPR 的升降是獲利了結變多還是認賠變少。單位 BTC；數值已經 CheckOnChain 平滑（圖上沒標明視窗），快取在 coc_cache/sth-pnl.json。
2026-10-28 使用者要求：讀「URPD 依長短期持有者拆分」圖（urpd_cohort，約 160KB，Bitcoin Research Kit 依每顆幣的實際幣齡算），
併成本站的 2,000 美元一格，取代長短期持有者籌碼「現在」那一張的推算值。圖上沒有日期，資料日推定與同一輪讀到的 STH-SOPR 最新一天相同；快取在 coc_cache/urpd-cohort.json。"""
import base64, datetime as dt, json, os, struct, subprocess

URL = 'https://charts-cdn.checkonchain.com/btconchain/realised/sthsopr_indicator/sthsopr_indicator_light.html'
PAGE = 'https://charts.checkonchain.com/btconchain/realised/sthsopr_indicator/sthsopr_indicator_light.html'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coc_cache', 'sth-sopr.json')
PNL_URL = 'https://charts-cdn.checkonchain.com/btconchain/realised/realisedpnl_bycohort_2/realisedpnl_bycohort_2_light.html'
PNL_PAGE = 'https://charts.checkonchain.com/btconchain/realised/realisedpnl_bycohort_2/realisedpnl_bycohort_2_light.html'
PNL_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coc_cache', 'sth-pnl.json')


def _trace(traces, name):
    t = next(t for t in traces if t.get('name') == name)
    y = t['y']
    if isinstance(y, dict):   # Plotly 的二進位格式：base64 的 float64
        b = base64.b64decode(y['bdata']); y = struct.unpack('<%dd' % (len(b) // 8), b)
    return {x[:10]: v for x, v in zip(t['x'], y) if v is not None and v == v}


def _traces(url):
    html = subprocess.run(['curl', '-sS', '--max-time', '90', url], capture_output=True, text=True).stdout
    i = html.find('Plotly.newPlot(')
    if i < 0: raise RuntimeError('CheckOnChain 頁面沒有 Plotly 資料（可能改版）')
    return json.JSONDecoder().raw_decode(html[html.find('[', i):])[0]


def _save(path, page, lines, keep=1500):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    with open(path, 'w') as f:   # 只留最近 1,500 天（四年百分位夠用）；一列一筆，每日提交的 diff 只有新增的幾行
        f.write('{"fetched_utc": "%s", "source": "%s", "rows": [\n' % (now, page))
        f.write(',\n'.join(json.dumps(r) for r in lines[-keep:]) + '\n]}\n')


# 2026-11-04 自我檢查：快取只當短暫備援。超過 CACHE_MAX_DAYS 天沒成功抓到就讓錯誤往上丟，
#   該項在頁面上顯示「本日未取得」，不再無限期沿用舊資料（資料原則：不推估、不沿用舊數字）
CACHE_MAX_DAYS = 4


def _cache(path):
    cj = json.load(open(path))
    age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(cj['fetched_utc'])).total_seconds() / 86400
    if age > CACHE_MAX_DAYS: raise RuntimeError(f'快取已 {age:.0f} 天沒更新（上限 {CACHE_MAX_DAYS} 天），不再沿用')
    return cj


def fetch():
    traces = _traces(URL)
    gt, lt = _trace(traces, 'STH-SOPR > 1'), _trace(traces, 'STH-SOPR < 1')
    ser = {d: (gt[d] if gt[d] != 1 else lt.get(d, 1.0)) for d in gt}
    if len(ser) < 1000: raise RuntimeError(f'CheckOnChain STH-SOPR 只有 {len(ser)} 筆，格式可能改了')
    return ser


def get():
    """回傳 (序列 {date: value}, 狀態說明)。失敗時用上一次成功的快取。"""
    try:
        ser = fetch()
        _save(CACHE, PAGE, [[d, round(v, 5)] for d, v in sorted(ser.items())])
        return ser, 'live'
    except Exception as e:
        cj = _cache(CACHE)   # 沒有快取就讓錯誤往上丟，由呼叫端記錄
        return {d: v for d, v in cj['rows']}, f'cache {cj["fetched_utc"]}（{e}）'


COH_URL = 'https://charts-cdn.checkonchain.com/btconchain/urpd/urpd_cohort/urpd_cohort_light.html'
COH_PAGE = 'https://charts.checkonchain.com/btconchain/urpd/urpd_cohort/urpd_cohort_light.html'
COH_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coc_cache', 'urpd-cohort.json')


def _arr(a):
    """Plotly 陣列：一般 list，或 {'dtype', 'bdata'} 的 base64 二進位"""
    if isinstance(a, list): return a
    b = base64.b64decode(a['bdata']); f = {'f8': 'd', 'f4': 'f', 'i4': 'i', 'i2': 'h', 'i1': 'b', 'u1': 'B', 'u2': 'H', 'u4': 'I'}[a.get('dtype', 'f8')]
    return list(struct.unpack('<%d%s' % (len(b) // struct.calcsize(f), f), b))


def fetch_cohort(w=2000, nb=63):
    """[[價位下緣, STH, LTH], ...]，nb 格、每格 w 美元。原圖是對數分格（每格約 1.16%，x＝下緣、另附寬度），按重疊比例分進各格"""
    traces = _traces(COH_URL)
    lt = next(t for t in traces if t.get('name') == 'Long-Term Holder Supply'); st = next(t for t in traces if t.get('name') == 'Short-Term Holder Supply')
    x, wd, yl, ys = _arr(lt['x']), _arr(lt['width']), _arr(lt['y']), _arr(st['y'])
    if not (len(x) == len(wd) == len(yl) == len(ys)) or _arr(st['x']) != x: raise RuntimeError('CheckOnChain URPD 分組格式不對（長短期兩條的格子不一致）')
    out = [[k * w, 0.0, 0.0] for k in range(nb)]; top = nb * w
    for x0, dx, a, b in zip(x, wd, yl, ys):
        x0, x1 = min(x0, top - 1), min(x0 + max(dx, 1e-9), top)   # 超出最上一格的併進最上一格（目前最高約 125.9K，不會發生）
        for k in range(int(x0 // w), int((x1 - 1e-9) // w) + 1):
            f = (min(x1, (k + 1) * w) - max(x0, k * w)) / (x1 - x0)
            out[k][1] += b * f; out[k][2] += a * f
    tot = sum(r[1] + r[2] for r in out)
    if tot < 1.5e7: raise RuntimeError(f'CheckOnChain URPD 分組合計只有 {tot:,.0f} 顆，格式可能改了')
    return [[k, round(s_, 1), round(l_, 1)] for k, s_, l_ in out]


def get_cohort(date_hint):
    """回傳 (dict(date, rows), 狀態說明)。date_hint：同一輪 STH-SOPR 的最新日期（這張圖沒有標日期）。失敗時用上一次成功的快取"""
    try:
        rows = fetch_cohort()
        os.makedirs(os.path.dirname(COH_CACHE), exist_ok=True)
        now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
        json.dump(dict(fetched_utc=now, source=COH_PAGE, date=date_hint, rows=rows), open(COH_CACHE, 'w'), separators=(',', ':'))
        return dict(date=date_hint, rows=rows), 'live'
    except Exception as e:
        cj = _cache(COH_CACHE)
        return dict(date=cj['date'], rows=cj['rows']), f'cache {cj["fetched_utc"]}（{e}）'


def fetch_pnl():
    """{date: (實現獲利, 實現虧損)}，單位 BTC；虧損在原圖是負值，這裡轉成正的大小。"""
    traces = _traces(PNL_URL)
    pr, ls = _trace(traces, 'Realised Profit STH'), _trace(traces, 'Realised Loss STH')
    ser = {d: (pr[d], abs(ls[d])) for d in pr if d in ls}
    if len(ser) < 1000: raise RuntimeError(f'CheckOnChain STH 實現損益只有 {len(ser)} 筆，格式可能改了')
    return ser


def get_pnl():
    """回傳 (序列 {date: (獲利, 虧損)}, 狀態說明)。失敗時用上一次成功的快取。"""
    try:
        ser = fetch_pnl()
        _save(PNL_CACHE, PNL_PAGE, [[d, round(p, 2), round(l, 2)] for d, (p, l) in sorted(ser.items())])
        return ser, 'live'
    except Exception as e:
        cj = _cache(PNL_CACHE)
        return {d: (p, l) for d, p, l in cj['rows']}, f'cache {cj["fetched_utc"]}（{e}）'


# 2026-11-02 使用者要求（Murphy〈卖方衰竭指数〉）：賣方衰竭常數＝獲利供給比例 × 30 天價格波動（Checkmate 設計）。
#   CheckOnChain 的圖從 2010 起、晚約 1 天；刻度和 Glassnode 版（Murphy 的 0.01 線）不同，頁面用自己的歷史分布畫極端區。
#   快取存完整歷史（約 6,000 行），歷次跌破的統計要用到 2011 年起的資料
SEC_URL = 'https://charts-cdn.checkonchain.com/btconchain/unrealised/seller_exhaustion_constant_supply/seller_exhaustion_constant_supply_light.html'
SEC_PAGE = 'https://charts.checkonchain.com/btconchain/unrealised/seller_exhaustion_constant_supply/seller_exhaustion_constant_supply_light.html'
SEC_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coc_cache', 'seller-exhaustion.json')


def fetch_sec():
    """{date: (賣方衰竭常數, 價格)}"""
    traces = _traces(SEC_URL)
    se, px = _trace(traces, 'Seller Exhaustion Constant'), _trace(traces, 'Price')
    ser = {d: (se[d], px[d]) for d in se if d in px and se[d] > 0}
    if len(ser) < 3000: raise RuntimeError(f'CheckOnChain 賣方衰竭常數只有 {len(ser)} 筆，格式可能改了')
    return ser


def get_sec():
    """回傳 (序列 {date: (常數, 價格)}, 狀態說明)。失敗時用上一次成功的快取。"""
    try:
        ser = fetch_sec()
        _save(SEC_CACHE, SEC_PAGE, [[d, round(v, 5), round(p, 2)] for d, (v, p) in sorted(ser.items())], keep=10000)
        return ser, 'live'
    except Exception as e:
        cj = _cache(SEC_CACHE)
        return {d: (v, p) for d, v, p in cj['rows']}, f'cache {cj["fetched_utc"]}（{e}）'


# 2026-11-02 使用者要求（貝格先生的 Realized Profit / Realized Loss 比率圖）：全網實現獲利 ÷ 實現虧損。
#   原圖把每日比值取 log10 後拆成正、負兩條（＋ve／−ve），這裡合併再還原成比值；90 天平均在 stage_viz.rpl_viz 算
RPL_URL = 'https://charts-cdn.checkonchain.com/btconchain/realised/realisedpnl_ratio_all/realisedpnl_ratio_all_light.html'
RPL_PAGE = 'https://charts.checkonchain.com/btconchain/realised/realisedpnl_ratio_all/realisedpnl_ratio_all_light.html'
RPL_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coc_cache', 'realised-pl-ratio.json')


def fetch_rpl():
    """{date: (實現獲利 ÷ 實現虧損 每日比值, 價格)}"""
    traces = _traces(RPL_URL)
    pos, neg, px = _trace(traces, 'Realised Profit/Loss Ratio (+ve)'), _trace(traces, 'Realised Profit/Loss Ratio (-ve)'), _trace(traces, 'Price')
    ser = {d: (10 ** (pos[d] if pos[d] != 0 else neg.get(d, 0)), px[d]) for d in pos if d in px and px[d] > 0}
    if len(ser) < 3000: raise RuntimeError(f'CheckOnChain 實現損益比只有 {len(ser)} 筆，格式可能改了')
    return ser


def get_rpl():
    """回傳 (序列 {date: (比值, 價格)}, 狀態說明)。失敗時用上一次成功的快取。"""
    try:
        ser = fetch_rpl()
        _save(RPL_CACHE, RPL_PAGE, [[d, round(v, 4), round(p, 2)] for d, (v, p) in sorted(ser.items())], keep=10000)
        return ser, 'live'
    except Exception as e:
        cj = _cache(RPL_CACHE)
        return {d: (v, p) for d, v, p in cj['rows']}, f'cache {cj["fetched_utc"]}（{e}）'


# 2026-11-03 使用者要求（CryptoQuant 的 Apparent Demand）：1 年以上沒動過的供給＝HODL Waves（BTC）中 1 年以上各帶的合計。
#   圖約 4.5MB、從 2009 起；快取只存 [日期, 1 年以上供給, 價格]，表觀需求在 stage_viz.ad_viz 算
HW_URL = 'https://charts-cdn.checkonchain.com/btconchain/supply/hodl_waves_0/hodl_waves_0_light.html'
HW_PAGE = 'https://charts.checkonchain.com/btconchain/supply/hodl_waves_0/hodl_waves_0_light.html'
HW_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coc_cache', 'hodl-1y.json')
HW_1Y = ('1y-18m', '18m-2y', '2y-3y', '3y-4y', '4y-5y', '5y-6y', '6y-7y', '7y-8y', '8y-10y', '>10y')


def fetch_hodl1y():
    """{date: (1 年以上供給, 價格)}"""
    traces = _traces(HW_URL)
    names = {t.get('name') for t in traces}
    miss = [b for b in HW_1Y if b not in names]
    if miss: raise RuntimeError(f'CheckOnChain HODL Waves 少了 {miss}，格式可能改了')
    bands = [_trace(traces, b) for b in HW_1Y]; px = _trace(traces, 'Price (USD)')
    ser = {d: (sum(b.get(d, 0) for b in bands), px[d]) for d in bands[-1] if d in px and px[d] > 0}
    if len(ser) < 3000: raise RuntimeError(f'CheckOnChain HODL Waves 只有 {len(ser)} 筆，格式可能改了')
    return ser


def get_hodl1y():
    """回傳 (序列 {date: (1 年以上供給, 價格)}, 狀態說明)。失敗時用上一次成功的快取。"""
    try:
        ser = fetch_hodl1y()
        _save(HW_CACHE, HW_PAGE, [[d, round(v), round(p, 2)] for d, (v, p) in sorted(ser.items())], keep=10000)
        return ser, 'live'
    except Exception as e:
        cj = _cache(HW_CACHE)
        return {d: (v, p) for d, v, p in cj['rows']}, f'cache {cj["fetched_utc"]}（{e}）'
