"""印出 data/latest.json 的精簡數字摘要（略去圖表陣列），給每日結論任務讀，避免把整份資料讀進上下文。
用法：python3 pipeline/brief.py"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(ROOT, 'data', 'latest.json')))
DROP = {'rows', 'rows20', 'history', 'viz', 'wide', 'near', 'band', 'cost', 'profit', 'ratio', 'meta_venues', 'nodes', 'realized'}
def slim(o, depth=0):
    if isinstance(o, dict):
        return {k: slim(v, depth + 1) for k, v in o.items() if k not in DROP}
    if isinstance(o, list):
        if len(o) > 24: return f'[{len(o)} 筆，略]'
        return [slim(x, depth + 1) for x in o]
    return o
out = slim(d)
if (d.get('flows') or {}).get('etf'):   # ETF 有 60 筆會被上面省略，摘要只放最近 10 個交易日與最新完整日
    e = d['flows']['etf']; out['flows']['etf'] = e[-10:]
    out['flows']['etf_last_complete'] = next((r['d'] for r in reversed(e) if not r.get('partial')), None)
if d.get('orderbook'):
    ob = d['orderbook']; out['orderbook'] = {k: ob.get(k) for k in ('ts', 'mid', 'walls', 'rounds', 'totals')}
print(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
