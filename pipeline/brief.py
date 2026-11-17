"""印出 data/latest.json 的精簡數字摘要（略去圖表陣列），給每日結論任務讀，避免把整份資料讀進上下文。
用法：python3 pipeline/brief.py [latest.json 路徑]
2026-10-23：異動偵測 signals 放在最前面（每日任務先讀它找「發現」）；active／base 是偵測器自己的狀態，略去"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'data', 'latest.json')))
DROP = {'rows', 'model_rows', 'rows20', 'history', 'viz', 'wide', 'near', 'band', 'cost', 'profit', 'ratio', 'meta_venues', 'nodes', 'realized', 'episodes', 'conc_hist', 'heat', 'candles'}
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
if ch: out.setdefault('chips', {})['conc5_read'] = dict(pct=ch[-1][2], d7=next((r[2] for r in reversed(ch) if r[0] <= ch[-1][0] - 7), None), days=len(ch), since=str(__import__('datetime').date(1970, 1, 1) + __import__('datetime').timedelta(days=ch[0][0])), src='Bitview（2026-11-05 起；2018 起每 3 天一點、近期每天）')
co = (d.get('chips') or {}).get('cohort')   # 2026-10-27：長短期持有者籌碼（推算）：格子陣列略去，只留最厚的格子與近 30 天換手最多的格子
if co:
    top = lambda rows, k, n=3: [[r[0], r[k]] for r in sorted(rows or [], key=lambda r: -r[k])[:n]]
    f = co.get('flow') or {}
    out.setdefault('chips', {})['cohort_read'] = dict(sth_top=top(co.get('rows'), 1), lth_top_above_price=top([r for r in co.get('rows') or [] if r[0] >= co.get('price', 0)], 2),
                                                      sth_spent_top=top(f.get('rows'), 1), lth_spent_top=top(f.get('rows'), 2), new_top=top(f.get('rows'), 3))
if d.get('orderbook'):
    ob = d['orderbook']; out['orderbook'] = {k: ob.get(k) for k in ('ts', 'mid', 'walls', 'rounds', 'totals')}
# 2026-11-17 使用者：「今日判讀只是在描述數據，並不是判讀，需要的是綜合所有數據後的判讀，需要有觀點」。
# 給日報一份網站每張指標卡今天的偏向（pipeline/next/leans.py，和網站上「我們的看法」同一套），分頁統計，綜合判讀時當依據
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'next')); import leans as _ln
    _nx = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'next.js'), encoding='utf-8').read(); _nx = json.loads(_nx[_nx.index('{'):_nx.rindex('}') + 1])
    _pg = {c['k']: ch['id'] for ch in _nx['site']['chapters'] for g in ch.get('groups') or [] for c in g.get('charts') or []}
    _lv = {}
    for _k, _f in _ln.FN.items():
        if _k not in _pg or _k in ('dawnc', 'regc', 'p6v', 'radarv', 'tm', 'soprf', 'avgdc', 'whalet'): continue   # 附屬卡和主卡同一個看法，不重複算
        try: _v = _f(d)
        except Exception: continue
        if not _v: continue
        _e = _lv.setdefault(_pg[_k], dict(up=0, down=0, neu=0, cards=[])); _e[_v[0]] += 1; _e['cards'].append([_k, _v[0], _v[1]])
    out['leans'] = dict(note='每張指標卡今天的偏向（up 偏多／down 偏空／neu 中性）＋立場短句；cycle＝長線估值與週期，lv＝價位與籌碼，sell＝賣壓，buy＝買盤與資金，lev＝槓桿與情緒（短線）', pages=_lv)
except Exception as _e:
    out['leans'] = dict(error=repr(_e))
print(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
