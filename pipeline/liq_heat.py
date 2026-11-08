"""清算熱力圖（推算；2026-11-02 使用者要求，參考 CoinGlass 的爆倉熱力圖）。只作讀值、不是實際倉位。
資料：2026-11-08 起用 Coinalyze（使用者申請的免費 key，見 coinalyze.py）的多家交易所 BTC 永續未平倉量：Binance、Bybit、OKX、Hyperliquid、HTX、Bitfinex、Deribit 共 11 個合約，
  價格用 Binance USDT 永續 K 線。最近約 84 天用 1 小時線，更早用 4 小時線補到約 D4 天前。沒有 key 或 Coinalyze 失敗時，照舊用 OKX 公開 API（只有 OKX，1 小時線 42 天＋4 小時線到約 130 天前）。
  Binance、Bybit 的原始 API 從本站的伺服器所在地讀不到（受限地區），Coinalyze 是第三方彙整，所以讀得到。
做法（與 CoinGlass 同類的模型，參數是本站的假設）：
  1. 未平倉量增加＝新開倉；每張合約同時有一多一空，兩邊各記一份。進場價攤在那一根 K 線的最低到最高之間（5 個點）。
     多個合約時各自算增減：增加的加總成新開倉，減少的加總按比例減（不互相抵銷，A 所開倉、B 所平倉是兩件事）。幣本位合約的未平倉量是美元，用收盤價換成顆。
  2. 槓桿假設 5–100 倍、對數均勻（16 檔）；多單清算價＝進場價 ×（1 − 1/槓桿 + 維持保證金 0.4%），空單＝進場價 ×（1 + 1/槓桿 − 0.4%）。
  3. 價格走過的清算價視為已清算、移除（多單看該根最低、空單看最高）；未平倉量減少時，所有倉位按減少的比例一起減。
  4. 每 50 美元一格累計；圖上每 100 美元一格。剩下的多單一定在收盤下方、空單一定在上方（走過就清掉了）。
2026-11-08 也加：長期範圍（12 小時線約 2.7 年，存最近 2 年每天一欄，另存 data/liq_long.json，網頁點了才載入）與每日多空清算量（Coinalyze 實際清算紀錄，不是推算）。
已知限制：槓桿分布是假設，換一組假設亮帶會移動；計算起點之前的舊倉位不知道進場價，不計入；Coinalyze 沒有 Bitget、Gate 的未平倉。"""
import base64, datetime as dt, math, time
import coinalyze as cz

OI_INST = ('BTC-USDT-SWAP', 'BTC-USD-SWAP')
PX_INST = 'BTC-USDT-SWAP'
PAGES = 10                        # 1 小時線每頁 100 根 → 約 42 天（OKX 最多給 60 天）
PAGES4 = 8                        # 4 小時線每頁 100 根 → 約 133 天，只用 1 小時線之前的部分
NL, LMIN, LMAX, MM = 16, 5, 100, 0.004
LEV = [LMIN * (LMAX / LMIN) ** (k / (NL - 1)) for k in range(NL)]
SPLIT = (0.1, 0.3, 0.5, 0.7, 0.9)
G, DB, SHOW = 50, 100, 168        # 計算格、圖上格（美元）、存下的小時數（7 天）
H = 3600000
H4 = 4 * H
D4 = 330                          # Coinalyze：4 小時線往前補幾天（1 小時線只有約 84 天）
GL, DBL, DAYS_L = 100, 500, 730   # 長期範圍：計算格、圖上格（美元）、存幾天
LV_FROM = '2022-10-01'            # 每日多空清算量從哪天開始：Coinalyze 的 Binance、Bybit、OKX、HTX 清算紀錄 2022 年 9 月下旬才開始（更早只有 Deribit、Bitfinex，不能比）


def _pages(get, base, key, n):
    out, cur = {}, ''
    for _ in range(n):
        j = get(base + (f'&{key}={cur}' if cur else ''))
        d = (j or {}).get('data') if isinstance(j, dict) else None
        if not d: break
        for r in d: out[int(r[0])] = r
        cur = d[-1][0]; time.sleep(0.45)   # rubik 統計端點每 2 秒 5 次
    return out


def _series(get, per, pages):
    oi = {}
    for inst in OI_INST:
        rows = _pages(get, f'https://www.okx.com/api/v5/rubik/stat/contracts/open-interest-history?instId={inst}&period={per}&limit=100', 'end', pages)
        if not rows: raise RuntimeError(f'OKX {inst} {per} 未平倉歷史取不到')
        for t, r in rows.items(): oi.setdefault(t, {})[inst] = float(r[2])
    k = _pages(get, f'https://www.okx.com/api/v5/market/history-candles?instId={PX_INST}&bar={per}&limit=100', 'after', pages + 1)
    px = {t: [float(x) for x in r[1:5]] for t, r in k.items() if len(r) < 9 or r[8] == '1'}   # 只用已收完的 K 線
    oi = {t: sum(v.values()) for t, v in oi.items() if len(v) == len(OI_INST)}
    return oi, px


def fetch(get):
    """回傳 (oi, px, dur)：1 小時線之前接 4 小時線（只取完全在第一根 1 小時線之前的 4 小時 K 線）；dur＝每根的長度"""
    oi1, px1 = _series(get, '1H', PAGES)
    T1 = [t for t in oi1 if t in px1]
    if not T1: raise RuntimeError('OKX 1 小時資料取不到')
    t1 = min(T1); oi, px, dur = {}, {}, {}
    try:
        oi4, px4 = _series(get, '4H', PAGES4)
        for t in oi4:
            if t in px4 and t + H4 <= t1: oi[t], px[t], dur[t] = oi4[t], px4[t], H4
    except Exception: pass   # 4 小時線失敗時照舊只用 1 小時線
    for t in T1: oi[t], px[t], dur[t] = oi1[t], px1[t], H
    return oi, px, dur


def fetch_cz(now_s):
    """Coinalyze：回傳 (oi, px, dur)；oi＝{合約: {t: 未平倉}}（毫秒）。1 小時線之前接 4 小時線（只取完全在第一根 1 小時線之前的）"""
    oi1, px1 = cz.oi_btc('1hour', now_s - 100 * 86400, now_s)
    t1 = min(px1); oi4, px4 = {}, {}
    try: oi4, px4 = cz.oi_btc('4hour', now_s - D4 * 86400, t1)
    except Exception: pass   # 4 小時線失敗時只用 1 小時線
    oi = {s: {t * 1000: v for t, v in list(oi4.get(s, {}).items()) + list(oi1.get(s, {}).items())} for s in set(oi1) | set(oi4)}
    px, dur = {}, {}
    for t, k in px4.items(): px[t * 1000], dur[t * 1000] = k, H4
    for t, k in px1.items(): px[t * 1000], dur[t * 1000] = k, H
    return oi, px, dur


def flows(oi, px, dur, usd=()):
    """每根 K 線的（新開倉顆數, 舊倉保留比例）。oi＝{合約: {t: 未平倉}}；usd 裡的合約是美元，用這根收盤價換成顆。
    前一根接得上（間隔＝前一根的長度）才算；各合約自己算增減，增加的加總、減少的按占比一起減"""
    T = sorted(px); fl = {}
    for i in range(1, len(T)):
        t, p = T[i], T[i - 1]
        if t - p != dur.get(p, H): continue
        c = px[t][3]; add = cut = base = 0.0
        for s, h in oi.items():
            a, b = h.get(p), h.get(t)
            if a is None or b is None: continue
            k = 1 / c if s in usd else 1.0
            d = (b - a) * k; base += a * k
            if d > 0: add += d
            else: cut -= d
        if base > 0: fl[t] = (add, max(0.0, 1 - cut / base))
    return fl


def model(fl, px, keep, g=G):
    """跑整段；keep(t) 為真的那幾根存快照 (t, [o,h,l,c], 每格多＋空)。回傳 (g0, snaps)"""
    T = sorted(px)
    lo_all = min(px[t][2] for t in T); hi_all = max(px[t][1] for t in T)
    g0 = math.floor(lo_all * (1 - 1 / LMIN) / g) * g; n = int(math.ceil(hi_all * (1 + 1 / LMIN) / g) * g - g0) // g + 1
    lg, sh = [0.0] * n, [0.0] * n
    j_ = lambda p: min(n - 1, max(0, int((p - g0) // g)))
    snaps = []
    for t in T[1:]:
        o, h, l, c = px[t]
        a = j_(l); lg[a:] = [0.0] * (n - a)          # 多單：清算價 ≥ 這根最低的都觸發
        b = j_(h); sh[:b + 1] = [0.0] * (b + 1)      # 空單：清算價 ≤ 這根最高的都觸發
        add, kp = fl.get(t, (0.0, 1.0))
        if kp < 1: lg = [x * kp for x in lg]; sh = [x * kp for x in sh]
        if add > 0:
            w = add / len(SPLIT) / NL
            for q in SPLIT:
                pe = l + (h - l) * q
                for L in LEV:
                    lg[j_(pe * (1 - 1 / L + MM))] += w; sh[j_(pe * (1 + 1 / L - MM))] += w
        if keep(t): snaps.append((t, [o, h, l, c], [x + y for x, y in zip(lg, sh)]))
    return g0, snaps


def build(get, now_s=None):
    now_s = int(now_s or time.time()); src = 'cz'; why = None
    try:
        if not cz.ok(): raise RuntimeError('沒有 COINALYZE_API_KEY')
        oi, px, dur = fetch_cz(now_s); usd = cz.USD
    except Exception as e:
        src, why = 'okx', str(e)
        o1, px, dur = fetch(get); oi = {'OKX': o1}; usd = ()
    T = sorted(px)
    if len(T) < SHOW + 24: raise RuntimeError(f'小時資料不足（{len(T)} 根）')
    fl = flows(oi, px, dur, usd)
    g0, snaps = model(fl, px, lambda t, z=T[-SHOW]: t >= z)
    lo = math.floor(min(s[1][2] for s in snaps) * 0.93 / DB) * DB; hi = math.ceil(max(s[1][1] for s in snaps) * 1.07 / DB) * DB
    nb = (hi - lo) // DB; r = DB // G
    i0 = (lo - g0) // G
    cols = [[sum(s[2][i0 + j * r: i0 + (j + 1) * r]) for j in range(nb)] for s in snaps]
    nz = sorted(v for col in cols for v in col if v > 0)
    cap = nz[int(len(nz) * 0.995)] if nz else 1.0
    raw = bytes(min(255, round(v / cap * 255)) for col in cols for v in col)
    t_last, k_last = snaps[-1][0], snaps[-1][1]; c = k_last[3]; last = cols[-1]
    since = dt.datetime.fromtimestamp(T[0] / 1000, dt.timezone.utc).date().isoformat()
    if src == 'cz':
        tl = T[-1]; oi_now = sum(h[tl] / (c if s in usd else 1) for s, h in oi.items() if tl in h)
        md = dict(src='Coinalyze', exch=cz.exch(oi), n=len(oi), oi_btc=round(oi_now), bars4h=sum(v == H4 for v in dur.values()))
        note = '推算：Coinalyze 彙整的多家交易所 BTC 永續未平倉量＋假設槓桿；不是實際倉位，也不是 CoinGlass 的數字；只作讀值'
    else:
        md = dict(src='OKX ' + '＋'.join(OI_INST), exch=['OKX'], n=len(OI_INST), bars4h=sum(v == H4 for v in dur.values()), fallback=why)
        note = '推算：OKX BTC 永續逐小時未平倉量＋假設槓桿（Coinalyze 這次取不到，暫用 OKX）；不是實際倉位；只作讀值'
    md.update(lev=f'{LMIN}–{LMAX} 倍對數均勻 {NL} 檔', mm=MM, hours_used=len(T), since=since)
    out = dict(asof=dt.datetime.fromtimestamp((t_last + H) / 1000, dt.timezone.utc).isoformat(timespec='minutes'),
               t0=snaps[0][0], hours=len(snaps), lo=lo, step=DB, nb=nb, cap=round(cap, 2), close=round(c),
               heat=base64.b64encode(raw).decode(), candles=[[round(x) for x in s[1]] for s in snaps],
               hr=[(s[0] - snaps[0][0]) // H for s in snaps],   # 2026-11-04：每根 K 線距 t0 幾小時（漏一小時時，頁面的時間標籤不會整段錯位）
               above=_bands(last, lo, c, 1), below=_bands(last, lo, c, -1),
               within5=dict(above=round(sum(v for j, v in enumerate(last) if c < lo + j * DB <= c * 1.05)),
                            below=round(sum(v for j, v in enumerate(last) if c * 0.95 <= lo + (j + 1) * DB < c))),
               far=_far(snaps[-1][2], g0, c, lo, hi),   # 2026-11-04：畫面（收盤 ±7%）外、±25% 內最亮的一塊
               model=md, note=note)
    return out


def build_long(now_s=None):
    """2026-11-08：長期範圍。Coinalyze 12 小時線（約 2.7 年）跑同一個模型，存最近 DAYS_L 天、每天收盤時（12:00 那根收完）的快照一欄，每 500 美元一格。
    另存 data/liq_long.json（約 200 KB），網頁點「2 年」才載入"""
    now_s = int(now_s or time.time())
    oi, px = cz.oi_btc('12hour', now_s - 1100 * 86400, now_s)
    oi = {s: {t * 1000: v for t, v in h.items()} for s, h in oi.items()}; px = {t * 1000: k for t, k in px.items()}
    dur = {t: 12 * H for t in px}
    fl = flows(oi, px, dur, cz.USD)
    T = sorted(px); d_last = T[-1] // 86400000 * 86400000; d0 = d_last - (DAYS_L - 1) * 86400000
    g0, snaps = model(fl, px, lambda t: t >= d0 and t % 86400000 == 12 * H, GL)
    days = [s[0] // 86400000 * 86400000 for s in snaps]
    cd = []
    for s, d in zip(snaps, days):
        a = px.get(d); k = s[1]
        cd.append([round(a[0]) if a else round(k[0]), round(max(k[1], a[1] if a else 0)), round(min(k[2], a[2] if a else k[2])), round(k[3])])
    lo = math.floor(min(k[2] for k in cd) * 0.85 / DBL) * DBL; hi = math.ceil(max(k[1] for k in cd) * 1.12 / DBL) * DBL
    nb = (hi - lo) // DBL; r = DBL // GL; i0 = (lo - g0) // GL
    cols = [[sum(s[2][max(0, i0 + j * r): max(0, i0 + (j + 1) * r)]) for j in range(nb)] for s in snaps]
    nz = sorted(v for col in cols for v in col if v > 0)
    cap = nz[int(len(nz) * 0.995)] if nz else 1.0
    raw = bytes(min(255, round(v / cap * 255)) for col in cols for v in col)
    return dict(asof=dt.datetime.fromtimestamp((snaps[-1][0] + 12 * H) / 1000, dt.timezone.utc).isoformat(timespec='minutes'),
                t0=days[0], days=len(days), dd=[(d - days[0]) // 86400000 for d in days], lo=lo, step=DBL, nb=nb, cap=round(cap, 2),
                heat=base64.b64encode(raw).decode(), candles=cd,
                model=dict(src='Coinalyze', exch=cz.exch(oi), n=len(oi), bars=len(T), since=dt.datetime.fromtimestamp(T[0] / 1000, dt.timezone.utc).date().isoformat(), lev=f'{LMIN}–{LMAX} 倍對數均勻 {NL} 檔', mm=MM),
                note='推算：Coinalyze 多家交易所 BTC 永續 12 小時未平倉量＋假設槓桿；每天一欄；不是實際倉位；只作讀值')


def build_vol(now_s=None, last=None):
    """2026-11-08 使用者要求（X 上清算圖的「30 天多單清算比較多」）：每日多單、空單各被強制平倉多少（美元）。Coinalyze 彙整的交易所實際清算紀錄，
    不是推算；交易所公開的清算資料可能少報（例如 Binance 每秒只推一筆），實際可能更多。last＝最後一根已收盤日線（之後的不算）"""
    now_s = int(now_s or time.time())
    frm = int(dt.datetime.fromisoformat('2020-01-01').replace(tzinfo=dt.timezone.utc).timestamp())
    L = cz.hist('liquidation-history', 'daily', frm, now_s, convert_to_usd='true')
    P = (cz.hist('ohlcv-history', 'daily', frm, now_s, (cz.PX,)).get(cz.PX) or {})
    ymd = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat()
    lg, sh, cover, stale = {}, {}, {}, {}
    for s, h in L.items():
        if not h: continue
        e = cz.NAME.get(s.rsplit('.', 1)[-1], s)
        if max(h) < now_s - 7 * 86400: stale[e] = ymd(max(h)); continue   # 已停更的合約（Deribit 停在 2023-10）不算，前後才能比
        cover[e] = min(cover.get(e, '9999'), ymd(min(h)))
        for t, r in h.items():
            d = ymd(t); lg[d] = lg.get(d, 0) + (r.get('l') or 0); sh[d] = sh.get(d, 0) + (r.get('s') or 0)
    px = {ymd(t): r['c'] for t, r in P.items()}
    D = [d for d in sorted(lg) if d in px and (last is None or d <= last)]
    if len(D) < 400: raise RuntimeError(f'Coinalyze 清算量不足（{len(D)} 天）')
    m = lambda v: round(v / 1e6, 1)
    def win(n, k=None):
        k = len(D) if k is None else k; w = D[max(0, k - n):k]
        a, b = sum(lg[d] for d in w), sum(sh[d] for d in w)
        return dict(long=m(a), short=m(b), share=round(a / (a + b) * 100, 1) if a + b else None)
    # 30 天多單占比的歷史分位（LV_FROM 起，每天一個 30 天窗）＋偏多單（≥ 70%）之後 90 天的價格
    k0 = next(i for i, d in enumerate(D) if d >= LV_FROM)
    sh30 = {D[k - 1]: win(30, k)['share'] for k in range(k0 + 30, len(D) + 1)}   # 每個 30 天窗都在 LV_FROM 之後
    tot30 = {D[k - 1]: sum(lg[d] + sh[d] for d in D[k - 30:k]) for k in range(k0 + 30, len(D) + 1)}
    cur = win(30); vs = sorted(v for v in sh30.values() if v is not None)
    pct = round(sum(v <= cur['share'] for v in vs) / len(vs) * 100) if vs and cur['share'] is not None else None
    tv = sorted(tot30.values()); tpct = round(sum(v <= tot30[D[-1]] for v in tv) / len(tv) * 100)
    def ep(th, side):   # 30 天多單占比越過門檻（≥ th 或 ≤ th）的那天，30 天內只算一次；之後 90 天報酬
        out, lastd = [], None
        for d in sorted(sh30):
            v = sh30[d]
            if v is None or not (v >= th if side > 0 else v <= th): continue
            if lastd and (dt.date.fromisoformat(d) - dt.date.fromisoformat(lastd)).days < 30: lastd = d; continue
            lastd = d; i = D.index(d)
            if i + 90 < len(D): out.append(dict(date=d, share=v, r90=round((px[D[i + 90]] / px[d] - 1) * 100, 1)))
        return out
    def stat(ev):
        r = sorted(e['r90'] for e in ev); n = len(r)
        return dict(n=n, up=sum(x > 0 for x in r), med=r[n // 2] if n % 2 else round((r[n // 2 - 1] + r[n // 2]) / 2, 1)) if n else dict(n=0)
    bi = [i for i, d in enumerate(D) if d >= LV_FROM and i + 90 < len(D)]
    br = sorted((px[D[i + 90]] / px[D[i]] - 1) * 100 for i in bi)
    base = dict(up=round(sum(x > 0 for x in br) / len(br) * 100), med=round(br[len(br) // 2], 1))
    hi_l, hi_s = ep(70, 1), ep(30, -1)
    top = []   # 清算最多的 6 天；10 天內只留最大的一天（不然相鄰兩天的膠囊疊在一起，圖上只剩一個）
    for d in sorted((d for d in D if d >= LV_FROM), key=lambda d: -(lg[d] + sh[d])):
        if all(abs((dt.date.fromisoformat(d) - dt.date.fromisoformat(e)).days) > 10 for e in top): top.append(d)
        if len(top) == 6: break
    EPD = dt.date(1970, 1, 1); dn = lambda s: (dt.date.fromisoformat(s) - EPD).days
    rows = [[dn(d), round(px[d]), m(sh[d]), -m(lg[d])] for d in D if d >= LV_FROM]
    return dict(date=D[-1], day=dict(long=m(lg[D[-1]]), short=m(sh[D[-1]])), d7=win(7), d30=cur, d90=win(90),
                share_pct=pct, tot30_pct=tpct, hi_long=dict(th=70, ev=hi_l[-6:], st=stat(hi_l)), hi_short=dict(th=30, ev=hi_s[-6:], st=stat(hi_s)), base=base,
                top=[dict(date=d, long=m(lg[d]), short=m(sh[d])) for d in sorted(top)], rows=rows, from_=LV_FROM,
                src='Coinalyze', link=cz.LINK, exch=[e for e in cz.EXCH if e in cover], cover=cover, stale=stale, missing=[e for e in cz.EXCH if e not in cover],
                note='美元（百萬）；Coinalyze 彙整的交易所實際強制平倉紀錄，不是推算；Binance 公開的清算資料每秒只推一筆，會少報很多；Hyperliquid 沒有、Deribit 停在 2023-10；適合比多空，不適合看總額；只作讀值')


def _far(col, g0, c, lo, hi, w=1000, span=0.25, keep=0.6):
    """畫面範圍外（下方 c×0.75～lo、上方 hi～c×1.25）最亮的一塊：每 1,000 美元合計，從峰值往兩邊延伸到低於峰值 60% 為止"""
    agg = {}
    for i, v in enumerate(col):
        k = int((g0 + i * G) // w * w); agg[k] = agg.get(k, 0) + v
    out = {}
    for side, a, b in (('below', c * (1 - span), lo), ('above', hi, c * (1 + span))):
        ks = sorted(k for k in agg if a <= k and k + w <= b and agg[k] > 0)
        if not ks: continue
        pk = max(ks, key=agg.get); x = y = pk
        while x - w in agg and x - w >= a and agg[x - w] >= agg[pk] * keep: x -= w
        while y + w in agg and y + 2 * w <= b and agg[y + w] >= agg[pk] * keep: y += w
        out[side] = dict(lo=x, hi=y + w, btc=round(sum(agg[k] for k in range(x, y + w, w))), dist_pct=round(((x + y + w) / 2 / c - 1) * 100, 1))
    return out


def _bands(col, lo, c, side, top=2, sep=600, keep=0.6):
    """最亮的價格帶：先找最高的格子，往兩邊延伸到低於峰值 60% 為止；峰與峰至少隔 600 美元。"""
    idx = [j for j in range(len(col)) if (lo + j * DB > c if side > 0 else lo + (j + 1) * DB <= c) and col[j] > 0]
    out, used = [], set()
    for j in sorted(idx, key=lambda j: -col[j]):
        if any(b['lo'] - sep < lo + j * DB < b['hi'] + sep for b in out): continue   # 2026-11-04：峰值落在已選的帶（含前後 600 美元）裡就跳過，避免同一帶重複
        if j in used: continue
        a = b_ = j
        while a - 1 in idx and a - 1 not in used and col[a - 1] >= col[j] * keep: a -= 1
        while b_ + 1 in idx and b_ + 1 not in used and col[b_ + 1] >= col[j] * keep: b_ += 1
        used.update(range(a - 1, b_ + 2))   # 已選的帶與緊鄰一格不再延伸進去
        mid = lo + (a + b_ + 1) * DB / 2
        out.append(dict(lo=lo + a * DB, hi=lo + (b_ + 1) * DB, btc=round(sum(col[a:b_ + 1])), dist_pct=round((mid / c - 1) * 100, 1)))
        if len(out) == top: break
    return out
