"""Hyperliquid 大戶的 BTC 部位（2026-11-04 使用者要求；Hyperliquid 公開 API，免費、不用金鑰）。只作讀值。
做法：排行榜（stats-data.hyperliquid.xyz，約 40MB）取帳戶淨值前 TOP 名，逐一查 clearinghouseState，彙總 BTC 永續部位：
多空各有幾個帳戶、合計幾顆、名目價值、名目加權槓桿，以及清算價落在收盤上下 10% 內的合計。
隱私（docs/CLAUDE_DAILY.md：不出現任何人的實際持倉數量）：不存地址、不存單一帳戶的部位；任何一組少於 MIN_N 個帳戶時只給帳戶數、不給數量。
2026-11-04 試做時，前 300 名只有 36 個帳戶有 BTC 部位，清算價在收盤 ±30% 內的只有 5 個帳戶、各自一個價位，
所以當時不在清算熱力圖上畫個別清算價（等於公開個人部位、而且資訊很少），只給彙總。
2026-11-05 使用者要求把 Hyperliquid 畫進清算熱力圖：改掃前 TOP＝2000 名（3 條連線並行，約 4–5 分鐘），
清算價在收盤 ±BAND_PCT 內的帳戶按 BAND_W 美元一格彙總成 bands，每格要同時滿足：
  ① 至少 BAND_MIN 個帳戶；② 最大一個帳戶佔該格顆數不超過 BAND_TOP（避免一格其實就是一個人）。
不符合的格子不畫，只併進 hidden（全部不畫的格子合計；帳戶數少於 MIN_N 時也只給帳戶數）。這是實際清算價，不是推算。
限制：只有 Hyperliquid；大帳戶可能是做市或避險（空單多不一定代表看空）；排行榜每天更新一次；清算價會隨保證金和價格變動。"""
import json, subprocess, time
from concurrent.futures import ThreadPoolExecutor

LB = 'https://stats-data.hyperliquid.xyz/Mainnet/leaderboard'
INFO = 'https://api.hyperliquid.xyz/info'
TOP, MIN_N, NEAR = 2000, 2, 0.10
BAND_W, BAND_PCT, BAND_MIN, BAND_TOP = 1000, 0.25, 5, 0.5
WORKERS = 3   # Hyperliquid info 每分鐘 1200 權重、clearinghouseState 每次 2 → 最多每秒 10 次；3 條連線約每秒 7 次


def _post(body):
    for k in range(3):
        out = subprocess.run(['curl', '-sS', '--max-time', '20', '-X', 'POST', INFO, '-H', 'Content-Type: application/json', '-d', json.dumps(body)],
                             capture_output=True, text=True).stdout
        if out.strip().startswith('{'): return json.loads(out)
        if out.strip() == 'null': return {}   # 查無此帳戶（排行榜有、但已經沒有部位資料）：當作沒有部位，不算失敗
        time.sleep(1 + k)   # 被限流時退一下再試
    return None


def _btc(addr):
    j = _post({'type': 'clearinghouseState', 'user': addr})
    if not j: return None
    out = []
    for a in j.get('assetPositions', []):
        p = a.get('position') or {}
        sz = float(p.get('szi') or 0)
        if p.get('coin') == 'BTC' and sz:
            out.append((sz, float(p.get('positionValue') or 0), float(p['liquidationPx']) if p.get('liquidationPx') else None))
    return out


def build(close, asof):
    out = subprocess.run(['curl', '-sS', '--max-time', '120', LB], capture_output=True, text=True).stdout
    rows = json.loads(out)['leaderboardRows']
    top = sorted(rows, key=lambda r: -float(r['accountValue']))[:TOP]
    floor = float(top[-1]['accountValue'])
    with ThreadPoolExecutor(WORKERS) as ex:
        res = list(ex.map(lambda r: _btc(r['ethAddress']), top))
    fails = sum(1 for x in res if x is None)
    if fails > TOP * 0.2: raise RuntimeError(f'Hyperliquid 查詢失敗 {fails}/{TOP}')
    pos = [p for x in res if x for p in x]

    def grp(P):
        n = len(P); g = dict(n=n)
        if n >= MIN_N:
            v = sum(x[1] for x in P)
            g.update(btc=round(sum(abs(x[0]) for x in P)), usd_m=round(v / 1e6))
        return g
    L = [x for x in pos if x[0] > 0]; S = [x for x in pos if x[0] < 0]
    nl = [x for x in L if x[2] and close * (1 - NEAR) <= x[2] < close]; ns = [x for x in S if x[2] and close < x[2] <= close * (1 + NEAR)]
    # 清算價分格（多單的清算價在收盤下方、空單在上方；反方向的是已經深度獲利、清算價很遠的，不在這個範圍）
    cells = {}
    for x in pos:
        lp = x[2]
        if not lp or abs(lp / close - 1) > BAND_PCT: continue
        side = 'long' if x[0] > 0 else 'short'
        if (side == 'long') != (lp < close): continue
        cells.setdefault((int(lp // BAND_W * BAND_W), side), []).append(abs(x[0]))
    bands, hid = [], []
    for (lo, side), sz in sorted(cells.items()):
        tot = sum(sz)
        if len(sz) >= BAND_MIN and tot > 0 and max(sz) / tot <= BAND_TOP:
            bands.append(dict(lo=lo, hi=lo + BAND_W, side=side, n=len(sz), btc=round(tot)))
        else: hid += sz
    hidden = dict(n=len(hid))
    if len(hid) >= MIN_N: hidden['btc'] = round(sum(hid))
    return dict(asof=asof, scanned=len(top) - fails, floor_usd_m=round(floor / 1e6, 1), with_btc=len(pos), long=grp(L), short=grp(S),
                near=dict(pct=round(NEAR * 100), long=grp(nl), short=grp(ns)),
                bands=dict(w=BAND_W, pct=round(BAND_PCT * 100), min_n=BAND_MIN, max_share=BAND_TOP, rows=bands, hidden=hidden),
                note=f'Hyperliquid 帳戶淨值前 {TOP} 名的 BTC 永續部位彙總；不列個別帳戶，少於 {MIN_N} 個帳戶的組只給帳戶數；'
                     f'熱力圖上的 Hyperliquid 清算價每格 {BAND_W} 美元、至少 {BAND_MIN} 個帳戶且最大一個不超過一半才畫；只有 Hyperliquid、大帳戶可能是做市或避險；只作讀值')
