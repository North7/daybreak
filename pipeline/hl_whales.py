"""Hyperliquid 大戶的 BTC 部位（2026-11-04 使用者要求；Hyperliquid 公開 API，免費、不用金鑰）。只作讀值。
做法：排行榜（stats-data.hyperliquid.xyz，約 40MB）取帳戶淨值前 TOP 名，逐一查 clearinghouseState，彙總 BTC 永續部位：
多空各有幾個帳戶、合計幾顆、名目價值、名目加權槓桿，以及清算價落在收盤上下 10% 內的合計。
隱私（docs/CLAUDE_DAILY.md：不出現任何人的實際持倉數量）：不存地址、不存單一帳戶的部位；任何一組少於 MIN_N 個帳戶時只給帳戶數、不給數量。
2026-11-04 試做時，前 300 名只有 36 個帳戶有 BTC 部位，清算價在收盤 ±30% 內的只有 5 個帳戶、各自一個價位，
所以不在清算熱力圖上畫個別清算價（等於公開個人部位、而且資訊很少），只給彙總。
限制：只有 Hyperliquid；大帳戶可能是做市或避險（空單多不一定代表看空）；排行榜每天更新一次。"""
import json, subprocess, time

LB = 'https://stats-data.hyperliquid.xyz/Mainnet/leaderboard'
INFO = 'https://api.hyperliquid.xyz/info'
TOP, MIN_N, NEAR = 300, 2, 0.10


def _post(body):
    out = subprocess.run(['curl', '-sS', '--max-time', '20', '-X', 'POST', INFO, '-H', 'Content-Type: application/json', '-d', json.dumps(body)],
                         capture_output=True, text=True).stdout
    return json.loads(out) if out.strip().startswith('{') else None


def build(close, asof):
    out = subprocess.run(['curl', '-sS', '--max-time', '120', LB], capture_output=True, text=True).stdout
    rows = json.loads(out)['leaderboardRows']
    top = sorted(rows, key=lambda r: -float(r['accountValue']))[:TOP]
    floor = float(top[-1]['accountValue']); pos, fails = [], 0
    for r in top:
        j = _post({'type': 'clearinghouseState', 'user': r['ethAddress']})
        if not j: fails += 1; continue
        for a in j.get('assetPositions', []):
            p = a.get('position') or {}
            sz = float(p.get('szi') or 0)
            if p.get('coin') == 'BTC' and sz:
                pos.append((sz, float(p.get('positionValue') or 0), float(p['liquidationPx']) if p.get('liquidationPx') else None))
        time.sleep(0.12)
    if fails > TOP * 0.2: raise RuntimeError(f'Hyperliquid 查詢失敗 {fails}/{TOP}')

    def grp(P):
        n = len(P); g = dict(n=n)
        if n >= MIN_N:
            v = sum(x[1] for x in P)
            g.update(btc=round(sum(abs(x[0]) for x in P)), usd_m=round(v / 1e6))
        return g
    L = [x for x in pos if x[0] > 0]; S = [x for x in pos if x[0] < 0]
    nl = [x for x in L if x[2] and close * (1 - NEAR) <= x[2] < close]; ns = [x for x in S if x[2] and close < x[2] <= close * (1 + NEAR)]
    return dict(asof=asof, scanned=len(top) - fails, floor_usd_m=round(floor / 1e6, 1), with_btc=len(pos), long=grp(L), short=grp(S),
                near=dict(pct=round(NEAR * 100), long=grp(nl), short=grp(ns)),
                note=f'Hyperliquid 帳戶淨值前 {TOP} 名的 BTC 永續部位彙總；不列個別帳戶，少於 {MIN_N} 個帳戶的組只給帳戶數；只有 Hyperliquid、大帳戶可能是做市或避險；只作讀值')
