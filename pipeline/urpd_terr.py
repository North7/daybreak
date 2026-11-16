#!/usr/bin/env python3
"""籌碼地形：每週一筆的籌碼分布，疊成「價位 × 時間 × 幣數」（2026-11-16 使用者要求：籌碼分布加一個立體檢視，
平面和立體要能互相切換、看得到變形過程；柱子點上去要看得到它代表什麼）。

Bitview 的 URPD（全部供給，每 1,000 美元一格）併成每 2,000 美元一格。每個星期日留一筆，再加最新的一天當最前面那一刀。
歷史存在 pipeline/coc_cache/urpd_terr.json（星期日那幾筆抓過就不再抓），平常每天只多抓最新一天，缺的星期日一次最多補 MAX_NEW 筆。
逐筆 UTXO、沒有做實體歸併；和「籌碼分布」那張圖（CheckOnChain）來源不同，同一格的數字會差 1% 上下。只作讀值。"""
import datetime as dt, json, os, time

URL = 'https://bitview.space/api/urpd/all/{}?agg=lin1000'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coc_cache', 'urpd_terr.json')
W, NB, WEEKS, MAX_NEW = 2000, 125, 104, 16          # 每格 2,000 美元；存 0–25 萬美元；兩年；一次最多補幾筆


def _one(curl, date):
    """回傳 [收盤, 全部供給（百枚）, 每 2,000 美元一格的幣數（百枚）]"""
    j = curl(URL.format(date)); b = j.get('buckets') or {}
    if j.get('date') != date or not b.get('price') or not j.get('close'): raise RuntimeError(f'Bitview URPD all {date}：{str(j)[:120]}')
    row = [0.0] * NB
    for p, s in zip(b['price'], b['supply']):
        i = int(p // W)
        if 0 <= i < NB: row[i] += s or 0
    return [round(j['close']), round(sum(s or 0 for s in b['supply']) / 100), [round(v / 100) for v in row]]


def _load():
    try: return json.load(open(CACHE))
    except Exception: return dict(w=W, weeks={})


def _save(c):
    with open(CACHE, 'w') as f:          # 一週一行，之後每次只多一行，差異好讀
        f.write('{"w": %d, "weeks": {\n' % W)
        f.write(',\n'.join('"%s": %s' % (d, json.dumps(c['weeks'][d], separators=(',', ':'))) for d in sorted(c['weeks'])))
        f.write('\n}}\n')


def sundays(last, weeks=WEEKS):
    d = dt.date.fromisoformat(last); d -= dt.timedelta(days=(d.weekday() + 1) % 7)          # 最近一個星期日（含當天）
    return [(d - dt.timedelta(days=7 * i)).isoformat() for i in range(weeks, -1, -1)]


def build(last, curl=None, weeks=WEEKS):
    """last＝'YYYY-MM-DD'。回傳 chips.urpd_terr；最新一天抓不到就丟錯（由呼叫的人記進 errors），補歷史失敗只是少幾週"""
    if curl is None:
        import bitview; curl = bitview._curl
    c = _load(); want = sundays(last, weeks); new = 0
    for d in reversed(want):          # 從近的補起
        if d in c['weeks'] or new >= MAX_NEW: continue
        try: c['weeks'][d] = _one(curl, d); new += 1; time.sleep(0.3)
        except Exception: break
    for d in [d for d in c['weeks'] if d < want[0]]: del c['weeks'][d]
    if new: _save(c)
    head = c['weeks'].get(last) or _one(curl, last)
    days = [d for d in want if d in c['weeks'] and d < last]
    if len(days) < 26: raise RuntimeError(f'urpd_terr：歷史只有 {len(days)} 週')
    S = [c['weeks'][d] for d in days] + [head]; dates = days + [last]; px = [s[0] for s in S]
    p0 = int(min(px) * .68 // 10000 * 10000); p1 = int(-(-max(px) * 1.05 // 10000) * 10000); i0, i1 = p0 // W, min(NB, p1 // W)
    return dict(date=last, w=W, p0=p0, nb=i1 - i0, dates=dates, px=px, tot=[s[1] for s in S], g=[s[2][i0:i1] for s in S], src='Bitview', link='https://bitview.space',
                note='Bitview URPD 全部供給，每 2,000 美元一格；每個星期日一筆、最後一筆是最新的一天；g 和 tot 的單位是百枚；只畫 p0 到 p0 + nb × w 這一段；逐筆 UTXO、沒有做實體歸併；只作讀值')


if __name__ == '__main__':
    import sys; r = build(sys.argv[1]); print(r['date'], len(r['dates']), r['dates'][0], r['p0'], r['nb'], r['px'][-1], max(max(x) for x in r['g']))
