"""Coinalyze 的四張圖（2026-11-08 使用者要求「四項都做」）：資金費率歷史、多交易所主動買賣、全市場未平倉量、多空帳戶比。
都是日線（Coinalyze 日線全部保留），價格用 Binance USDT 永續日收盤。只作讀值；統計只是歷史描述，不是買賣訊號。
共用 coinalyze.daily()：同一次執行裡同樣的請求只抓一次。"""
import datetime as dt
import json, subprocess
import coinalyze as cz

EP = dt.date(1970, 1, 1)
dn = lambda s: (dt.date.fromisoformat(s) - EP).days
ymd = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat()


def _px(to):
    return {ymd(t): r['c'] for t, r in (cz.daily('ohlcv-history', (cz.PX,), to).get(cz.PX) or {}).items()}


def _pct(vals, v):
    s = sorted(x for x in vals if x is not None)
    return round(sum(x <= v for x in s) / len(s) * 100) if s and v is not None else None


def _fwd(D, px, i, n=90):
    return round((px[D[i + n]] / px[D[i]] - 1) * 100, 1) if i + n < len(D) else None


def _stat(ev):
    r = sorted(e['r90'] for e in ev if e.get('r90') is not None); n = len(r)
    if not n: return dict(n=0)
    return dict(n=n, up=sum(x > 0 for x in r), med=r[n // 2] if n % 2 else round((r[n // 2 - 1] + r[n // 2]) / 2, 1))


def _base(D, px, d0):
    br = sorted(x for x in (_fwd(D, px, i) for i, d in enumerate(D) if d >= d0) if x is not None)
    return dict(up=round(sum(x > 0 for x in br) / len(br) * 100), med=br[len(br) // 2]) if br else None


def _events(D, val, px, cond, d0, gap=30):
    """cond(前一天, 今天) 為真的那天算一次（距上次至少 gap 天）；附 90 天後報酬"""
    out, last = [], None
    for i in range(1, len(D)):
        d = D[i]
        if d < d0 or val.get(D[i - 1]) is None or val.get(d) is None or not cond(val[D[i - 1]], val[d]): continue
        if last and (dt.date.fromisoformat(d) - dt.date.fromisoformat(last)).days < gap: continue
        last = d; out.append(dict(date=d, v=round(val[d], 1), price=round(px[d]), r90=_fwd(D, px, i)))
    return out


# ---------- 1. 資金費率歷史 ----------
FS = {'Binance': 'BTCUSDT_PERP.A', 'Bybit': 'BTCUSDT.6', 'OKX': 'BTCUSDT_PERP.3', 'Hyperliquid': 'BTC.H'}
PER = {'BTC.H': 24}          # 每天結算幾次（其他 3 次）
FH_FROM, FH_HOT = '2021-01-01', 30


def fund_hist(last, to=None):
    """各家 USDT 永續（Hyperliquid 是 USDC）每日資金費率年化 %，以當天未平倉美元加權；每日值＝當天（開＋高＋低＋收）÷ 4（和逐小時平均比誤差約 9%，只用收盤約 26%）。
    畫 7 日平均。統計：7 日平均轉負、升到 30% 以上之後 90 天"""
    F = cz.daily('funding-rate-history', tuple(FS.values()), to)
    O = cz.daily('open-interest-history', tuple(FS.values()), to)   # 原始單位（顆）：要求換成美元的日線只從 2022-09 開始
    px = _px(to); w = {}
    for s in FS.values():
        for t, r in (F.get(s) or {}).items():
            oi = ((O.get(s) or {}).get(t) or {}).get('c')
            if not oi: continue
            d = ymd(t); a = (r['o'] + r['h'] + r['l'] + r['c']) / 4 * PER.get(s, 3) * 365   # 同一天各家用顆數加權＝用美元加權
            x = w.setdefault(d, [0.0, 0.0, 0]); x[0] += a * oi; x[1] += oi; x[2] += 1
    D = [d for d in sorted(w) if d in px and d <= last and w[d][1] > 0]
    day = {d: w[d][0] / w[d][1] for d in D}
    m7 = {D[i]: sum(day[x] for x in D[i - 6:i + 1]) / 7 for i in range(6, len(D))}
    D7 = [d for d in D if d in m7]; d1 = D7[-1]
    neg = _events(D7, m7, px, lambda a, b: a >= 0 > b, FH_FROM)
    hot = _events(D7, m7, px, lambda a, b: a < FH_HOT <= b, FH_FROM)
    run = 0
    for d in reversed(D7):
        if (m7[d] >= 0) != (m7[d1] >= 0): break
        run += 1
    hi = max((d for d in D7 if d >= FH_FROM), key=lambda d: m7[d])
    rows = [[dn(d), round(px[d]), round(m7[d], 2)] for d in D7 if d >= FH_FROM][::-1][::2][::-1]
    return dict(date=d1, value=round(m7[d1], 2), day=round(day[d1], 2), v30=round(m7[D7[-31]], 2) if len(D7) > 30 else None,
                pct=_pct([m7[d] for d in D7 if d >= FH_FROM], m7[d1]), run=run, hi=dict(date=hi, value=round(m7[hi], 1)),
                neg=dict(ev=neg[-6:], st=_stat(neg)), hot=dict(th=FH_HOT, ev=hot[-6:], st=_stat(hot)), base=_base(D7, px, FH_FROM),
                venues=[k for k, s in FS.items() if F.get(s)], n_last=w[d1][2], rows=rows, from_=FH_FROM, src='Coinalyze', link=cz.LINK,
                note='年化 %；每日值＝當天（開＋高＋低＋收）÷ 4，以未平倉美元加權，畫 7 日平均；Hyperliquid 2024-10 起才有；只作讀值')


# ---------- 2. 多交易所主動買賣 ----------
TK_SPOT = {'Coinbase': 'BTCUSD.C', 'Bybit 現貨': 'sBTCUSDT.6'}           # Coinalyze 沒有 Binance 現貨 BTCUSDT、OKX 現貨 → Binance 現貨直接讀
TK_PERP = {'Binance': 'BTCUSDT_PERP.A', 'Bybit': 'BTCUSDT.6', 'OKX': 'BTCUSDT_PERP.3'}   # 都以顆計
TK_FROM = '2021-08-04'       # Bybit 現貨 2021-07-05 起；30 天加總要湊滿


def _bn_spot(to):
    """Binance 現貨 BTCUSDT 日線（data-api.binance.vision；從本站伺服器讀得到）：{日期: (成交量, 主動買)}"""
    out, end = {}, int(to) * 1000 - 1
    for _ in range(4):
        u = f'https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=1000&endTime={end}'
        r = json.loads(subprocess.run(['curl', '-sS', '--max-time', '40', u], capture_output=True, text=True).stdout or '[]')
        if not isinstance(r, list) or not r: break
        for k in r:
            if k[6] < int(to) * 1000: out[ymd(k[0] // 1000)] = (float(k[5]), float(k[9]))
        end = r[0][0] - 1
        if ymd(r[0][0] // 1000) < TK_FROM: break
    return out


def taker(last, to=None):
    """每天主動買 − 主動賣（顆）＝ 2 × 主動買 − 成交量。現貨：Binance＋Coinbase＋Bybit；永續：Binance、Bybit、OKX 的 USDT 永續。畫 30 天加總"""
    to = int(to or __import__('time').time()) // 86400 * 86400
    px = _px(to); bn = _bn_spot(to)
    sp = cz.daily('ohlcv-history', tuple(TK_SPOT.values()), to); pp = cz.daily('ohlcv-history', tuple(TK_PERP.values()), to)
    net = lambda r: 2 * (r.get('bv') or 0) - (r.get('v') or 0)
    S, P, CB = {}, {}, {}
    for d, (v, b) in bn.items(): S[d] = S.get(d, 0) + 2 * b - v
    for k, s in TK_SPOT.items():
        for t, r in (sp.get(s) or {}).items():
            d = ymd(t); S[d] = S.get(d, 0) + net(r)
            if k == 'Coinbase': CB[d] = net(r)
    for s in TK_PERP.values():
        for t, r in (pp.get(s) or {}).items(): d = ymd(t); P[d] = P.get(d, 0) + net(r)
    D = [d for d in sorted(set(S) & set(P)) if d in px and d <= last]
    if len(D) < 400: raise RuntimeError(f'主動買賣資料不足（{len(D)} 天）')
    sm = lambda X, n, i: sum(X.get(x, 0) for x in D[max(0, i - n + 1):i + 1])
    s30 = {D[i]: sm(S, 30, i) for i in range(29, len(D))}; p30 = {D[i]: sm(P, 30, i) for i in range(29, len(D))}
    c30 = {D[i]: sm(CB, 30, i) for i in range(29, len(D))}
    K = [d for d in D if d >= TK_FROM and d in s30]; d1 = K[-1]; i1 = len(D) - 1
    rows = [[dn(d), round(px[d]), round(s30[d] / 1e3, 1), round(p30[d] / 1e3, 1)] for d in K][::-1][::2][::-1]
    md = lambda X: round(sorted(X[d] for d in K)[len(K) // 2])   # 中位數：永續的主動賣長期偏多（30 天加總常態是負的），要和自己的常態比，不能只看正負
    return dict(date=d1, spot=dict(d1=round(S[d1]), d7=round(sm(S, 7, i1)), d30=round(s30[d1]), pct=_pct([s30[d] for d in K], s30[d1]), med=md(s30)),
                perp=dict(d1=round(P[d1]), d7=round(sm(P, 7, i1)), d30=round(p30[d1]), pct=_pct([p30[d] for d in K], p30[d1]), med=md(p30)),
                cb=dict(d7=round(sm(CB, 7, i1)), d30=round(c30[d1]), pct=_pct([c30[d] for d in K], c30[d1]), med=md(c30)),
                spot_venues=['Binance'] + [k.replace(' 現貨', '') for k in TK_SPOT], perp_venues=list(TK_PERP),
                rows=rows, from_=TK_FROM, src='Coinalyze＋Binance', link=cz.LINK,
                note='顆；主動買 − 主動賣（吃單方向，不含掛單）；現貨 Binance BTCUSDT（Binance 公開資料）＋Coinbase＋Bybit，永續 Binance、Bybit、OKX 的 USDT 永續；畫 30 天加總；只作讀值')


# ---------- 3. 全市場未平倉量 ----------
OH_FROM = '2021-01-01'


def oi_hist(last, to=None):
    """11 個 BTC 永續（見 coinalyze.SYM）每日收盤未平倉量（顆）；幣本位合約是美元，÷ Binance 永續收盤換成顆，另計占比。
    用原始單位（要求換成美元的日線只從 2022-09 開始）。合約陸續上線（Binance USDC 2024-01、Hyperliquid 2024），長期走勢含新合約的貢獻"""
    O = cz.daily('open-interest-history', cz.SYM, to); px = _px(to)
    tot, coin, n = {}, {}, {}
    for s, h in O.items():
        for t, r in (h or {}).items():
            d = ymd(t)
            if d not in px: continue
            b = r['c'] / px[d] if s in cz.USD else r['c']; tot[d] = tot.get(d, 0) + b; n[d] = n.get(d, 0) + 1
            if s in cz.USD: coin[d] = coin.get(d, 0) + b
    D = [d for d in sorted(tot) if d <= last]; d1 = D[-1]
    K = [d for d in D if d >= OH_FROM]
    ch = lambda k: round((tot[d1] / tot[D[-1 - k]] - 1) * 100, 1) if len(D) > k else None
    pc = lambda k: round((px[d1] / px[D[-1 - k]] - 1) * 100, 1) if len(D) > k else None
    hi = max(K, key=lambda d: tot[d])
    rows = [[dn(d), round(px[d]), round(tot[d] / 1e3, 1)] for d in K][::-1][::2][::-1]
    return dict(date=d1, btc=round(tot[d1]), usd_b=round(tot[d1] * px[d1] / 1e9, 1), coin_share=round(coin.get(d1, 0) / tot[d1] * 100, 1),
                coin_share_1y=round(coin.get(D[-366], 0) / tot[D[-366]] * 100, 1) if len(D) > 365 else None,
                chg7=ch(7), chg30=ch(30), chg90=ch(90), px30=pc(30), px90=pc(90), pct=_pct([tot[d] for d in K], tot[d1]),
                hi=dict(date=hi, btc=round(tot[hi])), n=n[d1], rows=rows, from_=OH_FROM, src='Coinalyze', link=cz.LINK,
                exch=cz.exch([s for s, h in O.items() if h]),
                note='顆；各合約每日收盤未平倉（幣本位的美元 ÷ Binance 永續收盤）；合約陸續上線，長期增加有一部分是新合約；只作讀值')


# ---------- 4. 多空帳戶比 ----------
LS = {'Binance': 'BTCUSDT_PERP.A', 'Bybit': 'BTCUSDT.6'}
LS_FROM = '2021-01-01'


def ls_acct(last, to=None):
    """持多單的帳戶占比（%，帳戶數，不是部位大小）：Binance、Bybit 的 BTCUSDT 永續（OKX 在 Coinalyze 沒有）。
    統計：Binance 升到 2021 年起的前 10%、降到後 10% 之後 90 天"""
    L = cz.daily('long-short-ratio-history', tuple(LS.values()), to); px = _px(to)
    v = {k: {ymd(t): r['l'] for t, r in (L.get(s) or {}).items()} for k, s in LS.items()}
    B = v['Binance']; D = [d for d in sorted(B) if d in px and d <= last]; d1 = D[-1]
    K = [d for d in D if d >= LS_FROM]; sv = sorted(B[d] for d in K)
    p90, p10 = sv[int(len(sv) * 0.9)], sv[int(len(sv) * 0.1)]
    hi = _events(D, B, px, lambda a, b: a < p90 <= b, LS_FROM); lo = _events(D, B, px, lambda a, b: a > p10 >= b, LS_FROM)
    rows = [[dn(d), round(px[d]), round(B[d], 1), round(v['Bybit'][d], 1) if v['Bybit'].get(d) is not None else None] for d in K][::-1][::2][::-1]
    k30 = D[-31] if len(D) > 30 else None
    return dict(date=d1, binance=round(B[d1], 1), bybit=round(v['Bybit'].get(d1), 1) if v['Bybit'].get(d1) is not None else None,
                b30=round(B[k30], 1) if k30 else None, pct=_pct(sv, B[d1]), p90=round(p90, 1), p10=round(p10, 1),
                med=round(sv[len(sv) // 2], 1), hi=dict(ev=hi[-6:], st=_stat(hi)), lo=dict(ev=lo[-6:], st=_stat(lo)), base=_base(D, px, LS_FROM),
                rows=rows, from_=LS_FROM, src='Coinalyze', link=cz.LINK,
                note='持多單的帳戶占比（帳戶數，不是部位大小）；Binance、Bybit 的 BTCUSDT 永續；只作讀值')


ESYM = tuple(s_.replace('BTC', 'ETH') for s_ in cz.SYM)   # 同樣 11 個合約的 ETH 版


def oi_eth(last, to=None):
    """槓桿在 ETH 還是 BTC（2026-11-12 使用者要求）：同樣 7 家交易所、11 個永續合約，ETH 和 BTC 各自的未平倉合計（都換成美元），
    以及 ETH 占兩者合計的比例。比例上升＝新開的槓桿比較多押在 ETH 上，通常是市場願意冒更多風險；下降＝槓桿退回 BTC。
    換成美元的日線只從 2022-09 開始。價格漲跌本身會改變比例（ETH 漲得比 BTC 多，比例就會上升），所以要和 ETH/BTC 匯率一起看。只作讀值。"""
    B = cz.daily('open-interest-history', cz.SYM, to, convert_to_usd='true'); E = cz.daily('open-interest-history', ESYM, to, convert_to_usd='true'); px = _px(to)
    tb, te = {}, {}
    for O, T in ((B, tb), (E, te)):
        for s_, h in O.items():
            for t, r in (h or {}).items(): T[ymd(t)] = T.get(ymd(t), 0) + (r['c'] or 0)
    D = [d for d in sorted(tb) if d <= last and d in te and d in px and tb[d] > 0 and te[d] > 0]
    if len(D) < 120: raise RuntimeError(f'ETH／BTC 未平倉日線太少（{len(D)} 天）')
    sh = [te[d] / (tb[d] + te[d]) * 100 for d in D]; n = len(D)
    ago = lambda v, k: v[-1 - k] if n > k else None
    pc = lambda T, k: round((T[D[-1]] / T[D[-1 - k]] - 1) * 100, 1) if n > k else None
    hi = max(range(n), key=lambda i: sh[i]); lo = min(range(n), key=lambda i: sh[i])
    return dict(date=D[-1], share=round(sh[-1], 1), chg7=round(sh[-1] - ago(sh, 7), 1), chg30=round(sh[-1] - ago(sh, 30), 1), chg90=round(sh[-1] - ago(sh, 90), 1) if n > 90 else None,
                pct=_pct(sh, sh[-1]), btc_usd_b=round(tb[D[-1]] / 1e9, 1), eth_usd_b=round(te[D[-1]] / 1e9, 1), btc30=pc(tb, 30), eth30=pc(te, 30),
                hi=dict(date=D[hi], share=round(sh[hi], 1)), lo=dict(date=D[lo], share=round(sh[lo], 1)), since=D[0], n=n,
                rows=[[dn(d), round(px[d]), round(sh[i], 2), round(tb[d] / 1e9, 2), round(te[d] / 1e9, 2)] for i, d in enumerate(D)][::-1][::2][::-1],
                src='Coinalyze', link=cz.LINK, exch=cz.exch([s_ for s_, h in E.items() if h]),
                note='ETH 永續未平倉 ÷（BTC＋ETH 永續未平倉），都換成美元；7 家交易所各 11 個合約；合約陸續上線；只作讀值')
