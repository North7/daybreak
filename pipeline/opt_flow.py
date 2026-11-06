"""2026-11-06 使用者要求（指標擴充，第三批，衍生品版）：
① 選擇權 Gamma 曝險（依履約價）：Deribit 每個合約的未平倉 × Black-Scholes gamma × 價格² × 1%，正負號用「推算的做市商部位」：
   逐筆成交裡主動方（taker）買進＝客戶買、做市商賣，所以做市商部位 ≈ −（主動買進 − 主動賣出）的累計，再限制在未平倉以內。
   正 Gamma＝做市商逆勢對沖（漲了賣、跌了買），價格容易被吸住；負 Gamma＝順勢對沖，波動會被放大。推算、只作讀值。
② 選擇權買方權利金差：每天主動買進買權（call）付出的權利金 − 主動買進賣權（put）付出的權利金（美元）。正＝錢押上漲，負＝買下跌保護。
③ OKX 現貨主動買賣差（主動買進量 − 主動賣出量，BTC）：OKX rubik 公開統計（日線是 UTC+8 的日界；Binance 從本站伺服器連不到）。
資料：Deribit history API（逐筆成交，免費、不用金鑰）、OKX rubik。快取 coc_cache/deribit_flow.json、okx_taker.json（每日工作流程會一起提交）。
第一次建立快取要回補一年的逐筆成交（約 2,000 次請求，本機跑一次）；之後每天只補前一天。"""
import datetime as dt, json, math, os, re, statistics as st, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DF_CACHE = os.path.join(HERE, 'coc_cache', 'deribit_flow.json')
OK_CACHE = os.path.join(HERE, 'coc_cache', 'okx_taker.json')
HIST = 'https://history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time?currency=BTC&kind=option&start_timestamp={}&end_timestamp={}&count=1000&sorting=asc'
MON = {m: i + 1 for i, m in enumerate(['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'])}
NAME = re.compile(r'BTC-(\d+)([A-Z]{3})(\d+)-(\d+)-([CP])')
EP = dt.date(1970, 1, 1)
dn = lambda s: (dt.date.fromisoformat(s) - EP).days


def _get(url, tries=3):
    for k in range(tries):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'daybreak'}), timeout=40))
        except Exception:
            if k == tries - 1: raise
            time.sleep(1.5 * (k + 1))


def _parse(name):
    m = NAME.match(name)
    if not m: return None
    exp = dt.datetime(2000 + int(m.group(3)), MON[m.group(2)], int(m.group(1)), 8, tzinfo=dt.timezone.utc)
    return exp, int(m.group(4)), m.group(5)


def _load(p, empty):
    try: return json.load(open(p))
    except Exception: return empty


def update_trades(now=None, backfill_days=365, max_pages=4000, log=print):
    """把逐筆成交補到現在：每天的權利金（主動買／賣 × 買權／賣權，美元）、每個合約的主動方向淨量。回傳快取"""
    now = now or dt.datetime.now(dt.timezone.utc)
    c = _load(DF_CACHE, {})
    if not c.get('last_ts'): c = dict(days={}, net={}, last_ts=int((now.timestamp() - backfill_days * 86400) * 1000), tail=[])
    t0, t1 = c['last_ts'], int(now.timestamp() * 1000); seen = set(c.get('tail') or []); pages = 0
    while t0 < t1 and pages < max_pages:
        r = _get(HIST.format(t0, t1))['result']; T = r.get('trades') or []; pages += 1
        for x in T:
            if x['trade_id'] in seen: continue
            seen.add(x['trade_id'])
            p = _parse(x['instrument_name'])
            if not p: continue
            d = dt.datetime.fromtimestamp(x['timestamp'] / 1000, dt.timezone.utc).date().isoformat()
            usd = x['price'] * x['amount'] * x['index_price']; buy = x['direction'] == 'buy'
            row = c['days'].setdefault(d, [0, 0, 0, 0, 0])   # 主動買 call、主動買 put、主動賣 call、主動賣 put（美元）、筆數
            row[(0 if buy else 2) + (0 if p[2] == 'C' else 1)] += usd; row[4] += 1
            c['net'][x['instrument_name']] = c['net'].get(x['instrument_name'], 0) + (x['amount'] if buy else -x['amount'])
        if not T or not r.get('has_more'): t0 = t1; break
        nt = T[-1]['timestamp']
        if nt <= t0: nt = t0 + 1   # 同一毫秒超過 1000 筆時往前推，避免卡住
        t0 = nt; seen = {x['trade_id'] for x in T if x['timestamp'] >= nt}   # 下一頁從同一毫秒開始，這幾筆會再出現一次
        if pages % 200 == 0: log(f'deribit trades: {pages} pages, at {dt.datetime.fromtimestamp(t0 / 1000, dt.timezone.utc):%Y-%m-%d %H:%M}')
    c['last_ts'] = t0; c['tail'] = sorted(seen)[-200:]
    today = now.date().isoformat()   # 已到期的合約不再需要淨量
    c['net'] = {k: round(v, 1) for k, v in c['net'].items() if (lambda p: p and p[0] > now)(_parse(k)) and abs(v) >= 0.1}
    c['days'] = {d: [round(v) for v in row] for d, row in sorted(c['days'].items()) if dn(d) >= dn(today) - 800}
    c['fetched_utc'] = now.isoformat(timespec='seconds'); c['pages'] = pages
    os.makedirs(os.path.dirname(DF_CACHE), exist_ok=True)
    json.dump(c, open(DF_CACHE, 'w'), separators=(',', ':'))
    return c


def _N1(x): return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def gex_viz(opt_result, net, now=None, urpd_band=None, width=2000, span=0.25, horizon=45):
    """依履約價的 Gamma 曝險（百萬美元／價格變動 1%）：主要到期日（45 天內未平倉最多的那一個）與 45 天內全部。推算、只作讀值"""
    now = now or dt.datetime.now(dt.timezone.utc); E = {}; F0 = None; cov = [0, 0]
    for o in opt_result:
        p = _parse(o['instrument_name']); oi = o.get('open_interest') or 0; iv = (o.get('mark_iv') or 0) / 100; F = o.get('underlying_price')
        if not p or not oi or not iv or not F: continue
        exp, K, cp = p; T = (exp - now).total_seconds() / (365 * 86400)
        if T <= 0 or T * 365 > horizon: continue
        F0 = F0 or o.get('estimated_delivery_price') or F
        s = iv * math.sqrt(T); d1 = (math.log(F / K) + 0.5 * s * s) / s; g = _N1(d1) / (F * s)
        dealer = -max(-oi, min(oi, net.get(o['instrument_name'], 0)))
        cov[0] += abs(dealer); cov[1] += oi
        e = E.setdefault(exp.date().isoformat(), {'oi': 0, 'k': {}}); e['oi'] += oi
        kk = e['k'].setdefault(K, [0.0, 0.0, 0.0])   # gex 美元、買權未平倉、賣權未平倉
        kk[0] += dealer * g * F * F * 0.01; kk[1 if cp == 'C' else 2] += oi
    if not E or not F0: return None
    tot = sum(e['oi'] for e in E.values())
    main = max(E, key=lambda x: E[x]['oi'])
    lo, hi = F0 * (1 - span), F0 * (1 + span)
    ks = sorted({K for e in E.values() for K in e['k'] if lo <= K <= hi and K % 1000 == 0})
    rows = [[K, round(E[main]['k'].get(K, [0])[0] / 1e6, 1), round(sum(e['k'].get(K, [0])[0] for e in E.values()) / 1e6, 1),
             round(E[main]['k'].get(K, [0, 0, 0])[1]), round(E[main]['k'].get(K, [0, 0, 0])[2])] for K in ks]
    pos = sorted([r for r in rows if r[2] > 0], key=lambda r: -r[2])[:3]; neg = sorted([r for r in rows if r[2] < 0], key=lambda r: r[2])[:3]
    # 和籌碼峰重疊：正 Gamma 前三名的履約價落在現價 ±15% 內最大的五個籌碼格（每 2,000 美元一格）
    overlap = []
    if urpd_band:
        near = sorted([b for b in urpd_band if abs(b[0] + width / 2 - F0) <= 0.15 * F0], key=lambda b: -b[1])[:5]
        for r in pos:
            b = next((b for b in near if b[0] <= r[0] < b[0] + width or abs(b[0] + width / 2 - r[0]) <= width / 2), None)
            if b: overlap.append(dict(strike=r[0], gex=r[2], bucket=b[0], btc=b[1]))
    up, dn_ = [r for r in rows if r[0] > F0], [r for r in rows if r[0] <= F0]
    return dict(ts=now.isoformat(timespec='minutes'), spot=round(F0), main=main, main_share=round(E[main]['oi'] / tot * 100, 1), n_exp=len(E), oi45=round(tot),
                total=round(sum(r[2] for r in rows), 1), above=round(sum(r[2] for r in up), 1), below=round(sum(r[2] for r in dn_), 1),
                pos=pos, neg=neg, overlap=overlap, coverage=round(cov[0] / cov[1] * 100) if cov[1] else None, rows=rows, src='Deribit',
                note='推算：做市商部位＝−（主動買進 − 主動賣出）的累計（Deribit 逐筆成交，回補一年），限制在未平倉以內；gamma 用 Black-Scholes 與 Deribit 標記隱含波動；百萬美元／價格變動 1%；只作讀值')


def prem_viz(cache, px, last, days=365):
    """選擇權買方權利金差（主動買 call − 主動買 put，百萬美元）與 7 日平均。7 日平均轉負（隔 30 天以上算新的一次）之後 30 天的漲跌。只作讀值"""
    dd = cache.get('days') or {}
    D = [d for d in sorted(dd) if d <= last and d < (cache.get('fetched_utc') or '9')[:10]]   # 當天未收完不放
    if len(D) < 30: return None
    net = {d: (dd[d][0] - dd[d][1]) / 1e6 for d in D}; a7 = {}
    for i, d in enumerate(D): w = D[max(0, i - 6):i + 1]; a7[d] = sum(net[x] for x in w) / len(w)
    ix = {d: i for i, d in enumerate(D)}
    def fwd(d, n):
        t = dn(d) + n; j = next((k for k in range(ix[d], len(D)) if dn(D[k]) >= t), None)
        return round((px[D[j]] / px[d] - 1) * 100, 1) if j is not None and px.get(D[j]) and px.get(d) else None
    flips, prev = [], None
    for i, d in enumerate(D[7:], 7):
        if a7[d] < 0 <= a7[D[i - 1]] and (prev is None or dn(d) - dn(prev) > 30):
            flips.append(dict(date=d, price=round(px[d]) if px.get(d) else None, r30=fwd(d, 30))); prev = d
    E = D[-days:]; d1 = D[-1]
    rows = [[dn(d), round(px[d]) if px.get(d) else None, round(net[d], 1), round(a7[d], 1), round(dd[d][0] / 1e6, 1), round(dd[d][1] / 1e6, 1)] for d in E]
    run = 0
    for d in reversed(E):
        if (a7[d] < 0) == (a7[d1] < 0): run += 1
        else: break
    r30 = [f['r30'] for f in flips if f['r30'] is not None]
    return dict(date=d1, net=round(net[d1], 1), a7=round(a7[d1], 1), call=round(dd[d1][0] / 1e6, 1), put=round(dd[d1][1] / 1e6, 1), run=run,
                flips=flips[-8:], n_flips=len(flips), r30=dict(n=len(r30), up=sum(x > 0 for x in r30), med=round(st.median(r30), 1) if r30 else None),
                since=D[0], rows=rows, src='Deribit',
                note='每天主動買進買權的權利金 − 主動買進賣權的權利金（Deribit 逐筆成交，美元，UTC 日界）；只作讀值')


def okx_update(now=None):
    """OKX 現貨主動買／賣量（BTC）：日線（UTC+8 日界，近 180 天）併進快取，小時線（近 30 天）只留最新。回傳快取"""
    now = now or dt.datetime.now(dt.timezone.utc)
    c = _load(OK_CACHE, {'days': {}, 'hours': []})
    d = _get('https://www.okx.com/api/v5/rubik/stat/taker-volume?ccy=BTC&instType=SPOT&period=1D')['data']
    for ts, sell, buy in d:
        day = (dt.datetime.fromtimestamp(int(ts) / 1000, dt.timezone.utc) + dt.timedelta(hours=8)).date().isoformat()
        c['days'][day] = [round(float(buy), 1), round(float(sell), 1)]
    h = _get('https://www.okx.com/api/v5/rubik/stat/taker-volume?ccy=BTC&instType=SPOT&period=1H')['data']
    k = _get('https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar=1H&limit=100')['data'] + \
        _get('https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar=1H&limit=100&after=' + str(int(now.timestamp() * 1000) - 100 * 3600 * 1000))['data']
    kc = {int(x[0]): float(x[4]) for x in k}
    c['hours'] = sorted([[int(ts) // 3600000, round(float(buy) - float(sell), 1), kc.get(int(ts) + 3600000) or kc.get(int(ts))] for ts, sell, buy in h])
    try:   # 2026-11-06 指標擴充：OKX 合約主動買／賣量（美元，每頁 72 天、API 最多回 180 天；快取逐日累積，第一次補 3 頁）
        pp, end = c.setdefault('perp', {}), None; c.pop('perp_err', None)
        for _ in range(1 if len(pp) > 60 else 3):
            p = _get('https://www.okx.com/api/v5/rubik/stat/taker-volume?ccy=BTC&instType=CONTRACTS&period=1D' + (f'&end={end}' if end else ''))['data']
            if not p or (end and int(p[-1][0]) >= end): break
            for ts, sell, buy in p:
                pp[(dt.datetime.fromtimestamp(int(ts) / 1000, dt.timezone.utc) + dt.timedelta(hours=8)).date().isoformat()] = [round(float(buy)), round(float(sell))]
            end = int(p[-1][0])
        c['perp'] = dict(sorted(pp.items())[-1500:])
    except Exception as e: c['perp_err'] = str(e)[:200]
    c['days'] = dict(sorted(c['days'].items())[-800:]); c['fetched_utc'] = now.isoformat(timespec='seconds')
    os.makedirs(os.path.dirname(OK_CACHE), exist_ok=True)
    json.dump(c, open(OK_CACHE, 'w'), separators=(',', ':'))
    return c


def svd_viz(cache, px, last, days=365, hours=168):
    dd = cache.get('days') or {}
    today8 = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=8)).date().isoformat()
    D = [d for d in sorted(dd) if d < today8][-days:]
    if len(D) < 20: return None
    delta = {d: dd[d][0] - dd[d][1] for d in D}
    rows = [[dn(d), round(px[d]) if px.get(d) else None, round(delta[d], 1), dd[d][0], dd[d][1]] for d in D]
    d1 = D[-1]; w7 = D[-7:]
    H = (cache.get('hours') or [])[-hours:]
    neg_run = 0
    for d in reversed(D):
        if delta[d] < 0: neg_run += 1
        else: break
    return dict(date=d1, delta=round(delta[d1], 1), sum7=round(sum(delta[d] for d in w7), 1), neg7=sum(delta[d] < 0 for d in w7), neg_run=neg_run,
                h24=round(sum(x[1] for x in H[-24:]), 1) if H else None, hours=H, rows=rows, src='OKX',
                note='OKX 現貨 BTC 主動買進量 − 主動賣出量（rubik 公開統計；日線是 UTC+8 的日界，價格用 UTC 收盤）；只有 OKX，不是全市場；只作讀值')
