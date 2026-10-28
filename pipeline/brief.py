"""印出 data/latest.json 的精簡數字摘要（略去圖表陣列），給每日結論任務讀，避免把整份資料讀進上下文。
用法：python3 pipeline/brief.py [latest.json 路徑]
2026-10-23：異動偵測 signals 放在最前面（每日任務先讀它找「發現」）；active／base 是偵測器自己的狀態，略去"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'latest.json')))
DROP = {'rows', 'model_rows', 'rows20', 'history', 'viz', 'wide', 'near', 'band', 'cost', 'profit', 'ratio', 'meta_venues', 'nodes', 'realized', 'episodes', 'conc_hist'}
def slim(o, depth=0):
    if isinstance(o, dict):
        return {k: slim(v, depth + 1) for k, v in o.items() if k not in DROP}
    if isinstance(o, list):
        if len(o) > 24: return f'[{len(o)} 筆，略]'
        return [slim(x, depth + 1) for x in o]
    return o
sg = d.get('signals') or {}
out = dict(signals={k: v for k, v in sg.items() if k not in ('active', 'base')}, **slim({k: v for k, v in d.items() if k != 'signals'}))
sp = (d.get('onchain') or {}).get('sth_pnl')   # 2026-10-23：DROP 的 ratio（籌碼圖用）會連帶刪掉這裡的 ratio，補回摘要
if sp: out['onchain']['sth_pnl'] = {k: v for k, v in sp.items() if k != 'rows'}
if (d.get('flows') or {}).get('etf'):   # ETF 有 60 筆會被上面省略，摘要只放最近 10 個交易日與最新完整日
    e = d['flows']['etf']; out['flows']['etf'] = e[-10:]
    out['flows']['etf_last_complete'] = next((r['d'] for r in reversed(e) if not r.get('partial')), None)
sv = ((d.get('cycle') or {}).get('stage') or {}).get('viz') or {}   # 2026-10-14：佐證燈號走勢圖只留讀值（陣列略去）
if sv: out['cycle']['stage']['viz_reads'] = dict(mom12={k: (sv.get('mom12') or {}).get(k) for k in ('hi30', 'flat_flip')}, tmm_cross=(sv.get('tmm') or {}).get('est'))
so = ((d.get('chips') or {}).get('viz') or {}).get('sopr')   # 2026-10-14：短期持有者認賠賣壓只留讀值
if so: out.setdefault('chips', {})['sopr_read'] = dict(date=so.get('date'), value=so.get('value'), below_run=so.get('below_run'), last_dips=(so.get('dips') or [])[-3:])
ch = (d.get('chips') or {}).get('conc_hist') or []   # 2026-10-15：籌碼集中度（現價 ±5%）只留最新與 7 天前、紀錄天數
if ch: out.setdefault('chips', {})['conc5_read'] = dict(pct=ch[-1][2], d7=next((r[2] for r in reversed(ch) if r[0] <= ch[-1][0] - 7), None), days=len(ch), since='2026-10-01')
co = (d.get('chips') or {}).get('cohort')   # 2026-10-27：長短期持有者籌碼（推算）：格子陣列略去，只留最厚的格子與近 30 天換手最多的格子
if co:
    top = lambda rows, k, n=3: [[r[0], r[k]] for r in sorted(rows or [], key=lambda r: -r[k])[:n]]
    f = co.get('flow') or {}
    out.setdefault('chips', {})['cohort_read'] = dict(sth_top=top(co.get('rows'), 1), lth_top_above_price=top([r for r in co.get('rows') or [] if r[0] >= co.get('price', 0)], 2),
                                                      sth_spent_top=top(f.get('rows'), 1), lth_spent_top=top(f.get('rows'), 2), new_top=top(f.get('rows'), 3))
if d.get('orderbook'):
    ob = d['orderbook']; out['orderbook'] = {k: ob.get(k) for k in ('ts', 'mid', 'walls', 'rounds', 'totals')}
print(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
