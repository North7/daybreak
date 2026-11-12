#!/usr/bin/env python3
"""預測市場：聯準會下一次利率決議（2026-11-12 使用者要求）。

Polymarket 公開接口。每次會議有一個「Fed Decision in <月份>?」的事件，底下每個結果（降 2 碼以上、降 1 碼、不變、升 1 碼、升 2 碼以上）各是一個市場，
價格就是市場認為那個結果發生的機率。這裡把結果併成三類：升息、不變、降息，各自的機率隨時間的變化。
抓最近一次還沒開的會；會開完之後事件會換成下一次，歷史也跟著換（同一張圖只看同一次會議）。
這是用真錢下注的機率，流動性夠（這個事件成交幾千萬美元），但不是官方數字，也會錯。只作讀值。"""
import datetime as dt, json, re

_EP = dt.date(1970, 1, 1)
MON = dict(January=1, February=2, March=3, April=4, May=5, June=6, July=7, August=8, September=9, October=10, November=11, December=12)


def fed(get, last):
    ev = get('https://gamma-api.polymarket.com/events?closed=false&limit=40&tag_slug=fed-rates&order=volume&ascending=false')
    if not isinstance(ev, list): return None
    c = [e for e in ev if re.match(r'^Fed Decision in \w+\?$', e.get('title') or '') and (e.get('endDate') or '')[:10] >= last]
    if not c: return None
    e = min(c, key=lambda x: x['endDate']); mon = MON.get(e['title'].split()[3].rstrip('?'))
    kind = lambda t: 'up' if 'increase' in t.lower() else 'down' if 'decrease' in t.lower() else 'flat'
    opts = []; T = []   # T＝[(類別, {日: 機率})]，每個結果一份
    for m in e.get('markets') or []:
        t = m.get('groupItemTitle') or ''
        try: p = float(json.loads(m['outcomePrices'])[0]); tok = json.loads(m['clobTokenIds'])[0]
        except Exception: continue
        opts.append(dict(label=t, kind=kind(t), p=round(p * 100, 1)))
        h = get(f'https://clob.polymarket.com/prices-history?market={tok}&interval=max&fidelity=1440')
        day = {}
        for q in (h or {}).get('history') or [] if isinstance(h, dict) else []: day[q['t'] // 86400] = q['p'] * 100   # 每天留最後一筆
        T.append((kind(t), day))
    if not opts: return None
    days = sorted(set(k for _, d_ in T for k in d_)); days = [k for k in days if k <= (dt.date.fromisoformat(last) - _EP).days]
    rows = []; cur = [None] * len(T)
    for k in days:   # 某個結果某一天沒有成交紀錄時沿用前一天的價格，不然三類加起來會突然少一塊
        for i, (_, d_) in enumerate(T):
            if k in d_: cur[i] = d_[k]
        s3 = {'up': 0.0, 'flat': 0.0, 'down': 0.0}
        for i, (kd, _) in enumerate(T): s3[kd] += cur[i] or 0
        rows.append([k, round(s3['up'], 1), round(s3['flat'], 1), round(s3['down'], 1)])
    tot = {k: round(sum(o['p'] for o in opts if o['kind'] == k), 1) for k in ('up', 'flat', 'down')}
    lead = max(tot, key=tot.get); col = {'up': 1, 'flat': 2, 'down': 3}[lead]
    ago = lambda n: next((r[col] for r in reversed(rows) if r[0] <= rows[-1][0] - n), None) if rows else None
    return dict(date=last, title=e['title'], month=mon, end=e['endDate'][:10], vol_m=round(float(e.get('volume') or 0) / 1e6, 1), opts=opts, up=tot['up'], flat=tot['flat'], down=tot['down'],
                lead=lead, lead_p=tot[lead], lead_7d=ago(7), lead_30d=ago(30), rows=rows, src='Polymarket', link='https://polymarket.com/event/' + e['slug'],
                note='Polymarket「聯準會下次決議」各結果的價格（＝市場認為的機率，%），併成升息、不變、降息三類；每天最後一筆；只作讀值')
