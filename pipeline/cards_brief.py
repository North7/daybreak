#!/usr/bin/env python3
"""主卡判讀任務（docs/CLAUDE_CARDS.md）讀的精簡摘要：五頁每一段的主卡，加上同一段其他卡的結論和偏向，以及今天頭版的判讀。
用法（倉庫根目錄）：python3 pipeline/cards_brief.py   → 印出 JSON
資料來自 data/next-<頁>.js（網站每天重建的卡片資料）和 data/notes.json。2026-11-17 建立（使用者決定：頭版 Fable 5.2、主卡 Opus 5.5）。"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(f):
    s = open(os.path.join(ROOT, 'data', f), encoding='utf-8').read()
    return json.loads(s[s.index('=[') + 1:s.rindex(']') + 1])
def view(c):
    v = [q for q in (c.get('say') or {}).get('items') or [] if q.get('view')]
    return dict(lean=v[0]['tone'], stance=v[0]['vz'], why=v[0]['dz'], change=v[0].get('cz') or '') if v else None
N = json.load(open(os.path.join(ROOT, 'data', 'notes.json'), encoding='utf-8'))
L = json.load(open(os.path.join(ROOT, 'data', 'latest.json'), encoding='utf-8'))
out = dict(bar_date=L['meta']['bar_date'], notes_date=N.get('date'), close=L['price']['bar']['c'],
           front=dict(headline=N.get('headline'), summary=N.get('summary'), stance=N.get('stance')), leads=[])
for pg in ('cycle', 'lv', 'sell', 'buy', 'lev'):
    for g in load('next-%s.js' % pg):
        c = g['charts'][0]; y = c.get('say') or {}
        out['leads'].append(dict(
            page=pg, section=g['zh'], question=g.get('sz'), k=c['k'], name=c.get('zh'),
            rule_sentence=y.get('sz'), rule_view=view(c),
            facts=[[q['kz'], q['vz'], q['dz']] for q in y.get('items') or [] if not q.get('view')],
            siblings=[dict(k=s['k'], name=s.get('zh'), sentence=(s.get('say') or {}).get('sz'), view=(lambda v: [v['lean'], v['stance']] if v else None)(view(s))) for s in g['charts'][1:]]))
print(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
