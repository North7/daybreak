#!/usr/bin/env python3
"""選擇權的立體檢視要的整張表：每個到期日 × 每 2,000 美元一格的買權、賣權未平倉，和每個到期日的隱含波動率微笑
（2026-11-16 使用者要求：履約價分布、隱含波動率期限結構各加一個立體檢視，規則見 page.html ㉛）。

輸入是 collect.py 已經在抓的 Deribit get_book_summary_by_currency（kind=option），不多發請求。
未平倉：只留還沒到期、合計 2,000 顆以上的到期日；價位範圍跟著指數價（約 −38% 到 +55%）。
隱含波動率：每個履約價用價外那一邊的標記隱含波動率（低於遠期價用賣權、高於用買權），線性內插到 2,000 美元一格；
只給指數價 −22% 到 +24% 這一段（近的到期日掛的履約價少，再寬就沒有報價）。只作讀值。"""
import datetime as dt, re

MON = dict(JAN=1, FEB=2, MAR=3, APR=4, MAY=5, JUN=6, JUL=7, AUG=8, SEP=9, OCT=10, NOV=11, DEC=12)
KW, MIN_OI, IVN = 2000, 2000, 15


def build(result, ix, today):
    """result＝Deribit 回傳的 result 陣列；ix＝指數價；today＝date。回傳 options.grid，資料不夠回 None"""
    E = {}
    for o in result or []:
        m = re.match(r'BTC-(\d+)([A-Z]{3})(\d+)-(\d+)-([CP])', o.get('instrument_name') or '')
        if not m: continue
        d = dt.date(2000 + int(m.group(3)), MON[m.group(2)], int(m.group(1)))
        E.setdefault(d, []).append((int(m.group(4)), m.group(5), o.get('open_interest') or 0, o.get('mark_iv'), o.get('underlying_price')))
    if not E or not ix: return None
    k0 = int(ix * .62 // 10000 * 10000); k1 = int(-(-ix * 1.55 // 10000) * 10000); nk = (k1 - k0) // KW
    ik0 = int(ix * .78 // KW * KW)
    out = []
    for d in sorted(E):
        v = E[d]; tc = sum(x[2] for x in v if x[1] == 'C'); tp = sum(x[2] for x in v if x[1] == 'P')
        if d <= today or tc + tp < MIN_OI: continue
        F = next((x[4] for x in v if x[4]), ix); c = [0.0] * nk; p = [0.0] * nk
        for K, cp, oi, _, _ in v:
            i = (K - k0) // KW
            if 0 <= i < nk: (c if cp == 'C' else p)[i] += oi
        ks = sorted({x[0] for x in v})
        pain = min(ks, key=lambda s: sum(oi * max(0, s - K) if cp == 'C' else oi * max(0, K - s) for K, cp, oi, _, _ in v))
        otm = sorted((K, iv) for K, cp, oi, iv, _ in v if iv and ((cp == 'P' and K < F) or (cp == 'C' and K >= F)))
        if not otm: continue
        ivg = []
        for i in range(IVN + 1):
            k = ik0 + i * KW
            if k < otm[0][0] or k > otm[-1][0]: ivg.append(None); continue
            a = max((x for x in otm if x[0] <= k), key=lambda x: x[0]); b = min((x for x in otm if x[0] >= k), key=lambda x: x[0])
            ivg.append(round(a[1] if a[0] == b[0] else a[1] + (b[1] - a[1]) * (k - a[0]) / (b[0] - a[0]), 1))
        top = max(v, key=lambda x: x[2])
        out.append(dict(d=d.isoformat(), dte=(d - today).days, f=round(F), c=[round(x) for x in c], p=[round(x) for x in p], tc=round(tc), tp=round(tp), pain=pain,
                        iv=ivg, atm=round(min(otm, key=lambda x: abs(x[0] - F))[1], 1), top=[round(top[2]), top[0], top[1]]))
    if len(out) < 3: return None
    return dict(date=today.isoformat(), spot=round(ix), k0=k0, kw=KW, nk=nk, ivx=dict(k0=ik0, kw=KW, n=IVN), exps=out, src='Deribit',
                note='每個到期日 × 每 2,000 美元一格：c／p＝買權／賣權未平倉（顆），tc／tp＝整個到期日合計，pain＝最大痛點，top＝[最大的一檔的未平倉, 履約價, C／P]；'
                     'iv＝價外那一邊的標記隱含波動率（%），從 ivx.k0 起每 ivx.kw 一格、共 ivx.n + 1 點，沒有報價是 null；atm＝平值；只作讀值')
