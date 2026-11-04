"""清算熱力圖（推算；2026-11-02 使用者要求，參考 CoinGlass 的爆倉熱力圖）。只作讀值、不是實際倉位。
資料：OKX 公開 API 的 BTC 永續（USDT 本位 BTC-USDT-SWAP＋幣本位 BTC-USD-SWAP）逐小時未平倉量（顆）與 BTC-USDT-SWAP 逐小時 K 線，
最近 60 天用 1 小時線；2026-11-04 起更早的部分用 4 小時線補到約 130 天前（OKX 1 小時的未平倉歷史只給 60 天），才看得到 8 月突破時留下的槓桿（每日約 55 次請求，不佔 bitcoin-data 額度）。Binance、Bybit 的未平倉歷史從本站的伺服器所在地讀不到（受限地區），所以只有 OKX。
做法（與 CoinGlass 同類的模型，參數是本站的假設）：
  1. 未平倉量增加＝新開倉；每張合約同時有一多一空，兩邊各記一份。進場價攤在那一小時的最低到最高之間（5 個點）。
  2. 槓桿假設 5–100 倍、對數均勻（16 檔）；多單清算價＝進場價 ×（1 − 1/槓桿 + 維持保證金 0.4%），空單＝進場價 ×（1 + 1/槓桿 − 0.4%）。
  3. 價格走過的清算價視為已清算、移除（多單看該小時最低、空單看最高）；未平倉量減少時，所有倉位按減少的比例一起減。
  4. 每 50 美元一格累計；圖上每 100 美元一格。剩下的多單一定在收盤下方、空單一定在上方（走過就清掉了）。
已知限制：只有 OKX；槓桿分布是假設，換一組假設亮帶會移動；計算起點之前的舊倉位不知道進場價，不計入。"""
import base64, datetime as dt, math, time

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


def model(oi, px, dur=None):
    dur = dur or {}
    T = sorted(t for t in oi if t in px)
    if len(T) < SHOW + 24: raise RuntimeError(f'OKX 小時資料不足（{len(T)} 小時）')
    lo_all = min(px[t][2] for t in T); hi_all = max(px[t][1] for t in T)
    g0 = math.floor(lo_all * (1 - 1 / LMIN) / G) * G; n = int(math.ceil(hi_all * (1 + 1 / LMIN) / G) * G - g0) // G + 1
    lg, sh = [0.0] * n, [0.0] * n
    j_ = lambda p: min(n - 1, max(0, int((p - g0) // G)))
    snaps = []
    for i in range(1, len(T)):
        t = T[i]; o, h, l, c = px[t]
        a = j_(l); lg[a:] = [0.0] * (n - a)          # 多單：清算價 ≥ 這小時最低的都觸發
        b = j_(h); sh[:b + 1] = [0.0] * (b + 1)      # 空單：清算價 ≤ 這小時最高的都觸發
        d = oi[t] - oi[T[i - 1]] if t - T[i - 1] == dur.get(T[i - 1], H) else 0.0   # 前一根接得上才算新開倉
        if d > 0:
            w = d / len(SPLIT) / NL
            for q in SPLIT:
                pe = l + (h - l) * q
                for L in LEV:
                    lg[j_(pe * (1 - 1 / L + MM))] += w; sh[j_(pe * (1 + 1 / L - MM))] += w
        elif d < 0 and oi[T[i - 1]] > 0:
            k = max(0.0, 1 + d / oi[T[i - 1]])
            lg = [x * k for x in lg]; sh = [x * k for x in sh]
        if i >= len(T) - SHOW: snaps.append((t, [o, h, l, c], [x + y for x, y in zip(lg, sh)]))
    return g0, snaps


def build(get):
    oi, px, dur = fetch(get)
    g0, snaps = model(oi, px, dur)
    lo = math.floor(min(s[1][2] for s in snaps) * 0.93 / DB) * DB; hi = math.ceil(max(s[1][1] for s in snaps) * 1.07 / DB) * DB
    nb = (hi - lo) // DB; r = DB // G
    i0 = (lo - g0) // G
    cols = [[sum(s[2][i0 + j * r: i0 + (j + 1) * r]) for j in range(nb)] for s in snaps]
    nz = sorted(v for col in cols for v in col if v > 0)
    cap = nz[int(len(nz) * 0.995)] if nz else 1.0
    raw = bytes(min(255, round(v / cap * 255)) for col in cols for v in col)
    t_last, k_last = snaps[-1][0], snaps[-1][1]; c = k_last[3]; last = cols[-1]
    out = dict(asof=dt.datetime.fromtimestamp((t_last + H) / 1000, dt.timezone.utc).isoformat(timespec='minutes'),
               t0=snaps[0][0], hours=len(snaps), lo=lo, step=DB, nb=nb, cap=round(cap, 2), close=round(c),
               heat=base64.b64encode(raw).decode(), candles=[[round(x) for x in s[1]] for s in snaps],
               hr=[(s[0] - snaps[0][0]) // H for s in snaps],   # 2026-11-04：每根 K 線距 t0 幾小時（OKX 漏一小時時，頁面的時間標籤不會整段錯位）
               above=_bands(last, lo, c, 1), below=_bands(last, lo, c, -1),
               within5=dict(above=round(sum(v for j, v in enumerate(last) if c < lo + j * DB <= c * 1.05)),
                            below=round(sum(v for j, v in enumerate(last) if c * 0.95 <= lo + (j + 1) * DB < c))),
               far=_far(snaps[-1][2], g0, c, lo, hi),   # 2026-11-04：畫面（收盤 ±7%）外、±25% 內最亮的一塊
               model=dict(src='OKX ' + '＋'.join(OI_INST), lev=f'{LMIN}–{LMAX} 倍對數均勻 {NL} 檔', mm=MM, hours_used=len(oi), since=dt.datetime.fromtimestamp(min(oi) / 1000, dt.timezone.utc).date().isoformat(), bars4h=sum(v == H4 for v in dur.values())),
               note='推算：OKX BTC 永續逐小時未平倉量＋假設槓桿；不是實際倉位，也不是 CoinGlass 的數字；只有 OKX；只作讀值')
    return out


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
