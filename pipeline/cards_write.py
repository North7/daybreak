#!/usr/bin/env python3
"""把主卡判讀寫進 data/notes.json（cards：{圖代號: {"lean", "text"}}）和 data/notes.en.json（cards：{圖代號: 英文}），保留兩個檔原本的手排格式。
用法：python3 pipeline/cards_write.py <cards.json>
cards.json＝{"date": 資料日, "cards": {"dawn": {"lean": "up|down|neu", "zh": "…", "en": "…"}, …}}；日期要等於 notes.json 的 date，不然拒寫。2026-11-17 建立。"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = json.load(open(sys.argv[1], encoding='utf-8')); C = src['cards']
for k, v in C.items():
    assert v.get('lean') in ('up', 'down', 'neu') and v.get('zh') and v.get('en'), '%s 缺 lean／zh／en' % k
def put(f, body):
    p = os.path.join(ROOT, 'data', f); s = open(p, encoding='utf-8').read()
    n = json.loads(s); assert n.get('date') == src['date'], '%s 的 date %s ≠ %s，拒寫' % (f, n.get('date'), src['date'])
    s = re.sub(r',\s*"cards":\s*\{.*?\n  \}(?=\s*\}\s*$)', '', s, flags=re.S).rstrip()   # 拿掉舊的 cards 區塊（同一天重寫）
    assert s.endswith('}')
    s = s[:-1].rstrip() + ',\n  "cards": {\n' + ',\n'.join('    %s: %s' % (json.dumps(k), b) for k, b in body) + '\n  }\n}\n'
    json.loads(s); open(p, 'w', encoding='utf-8').write(s)
put('notes.json', [(k, '{"lean": "%s", "text": %s}' % (v['lean'], json.dumps(v['zh'], ensure_ascii=False))) for k, v in C.items()])
put('notes.en.json', [(k, json.dumps(v['en'], ensure_ascii=False)) for k, v in C.items()])
print('wrote %d cards' % len(C))
