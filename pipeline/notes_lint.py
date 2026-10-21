#!/usr/bin/env python3
"""檢查當期 data/notes.json／notes.en.json 是否符合 docs/CLAUDE_DAILY.md 的格式與長度規則（2026-10-21 建立）。
2026-10-21 自我檢查發現：事件表連 7 期缺 CPI、摘要寫到 4–6 句、頭條 76–107 字、制式提醒句每期約 20 次，都是規則有寫但沒人檢查。
用法（在倉庫根目錄）：python3 pipeline/notes_lint.py   # 有問題會列出並以非零結束"""
import json, os, re, sys, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJK = re.compile(r'[一-鿿]')
HEAD_ZH, HEAD_EN, SUM_ZH, SUM_EN = 60, 150, 180, 480   # 頭條與摘要的字數上限（字元）
BOILER = ('只作讀值', '不改變', '不是框架條件', '不碰')   # 制式提醒句；news[].read 本來就要寫影不影響週期，不算在內
BOILER_MAX = 4
EVENTS = {'CPI': 'CPI', 'FOMC': 'FOMC', '非農': '非農', '難度調整': '難度', 'Deribit 到期': 'Deribit', '月底路徑重估': '路徑'}


def texts(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items(): yield from texts(v, path + '.' + k)
    elif isinstance(o, list):
        for v in o: yield from texts(v, path)
    elif isinstance(o, str): yield path, o


def lint(n, en, bar_date):
    bad = []
    if n.get('date') != bar_date: bad.append(f"date {n.get('date')} ≠ bar_date {bar_date}")
    h, s = n.get('headline', ''), n.get('summary', '')
    if not re.search(r'\d', h): bad.append('頭條沒有數字')
    if len(h) > HEAD_ZH: bad.append(f'頭條 {len(h)} 字，上限 {HEAD_ZH}')
    sents = [x for x in re.split(r'[。！？]', s) if x.strip()]
    if len(sents) > 3: bad.append(f'摘要 {len(sents)} 句，上限 3 句')
    if len(s) > SUM_ZH: bad.append(f'摘要 {len(s)} 字，上限 {SUM_ZH}')
    for k, lo, hi in (('watch', 3, 3), ('actions', 4, 6), ('changes', 3, 5), ('news', 6, 10)):
        c = len(n.get(k) or [])
        if not lo <= c <= hi: bad.append(f'{k} {c} 項，應為 {lo}–{hi}')
    for m, v in (n.get('modules') or {}).items():
        c = len(v.get('points') or [])
        if not 2 <= c <= 4: bad.append(f'modules.{m} points {c} 點，應為 2–4')
    body = json.dumps({k: v for k, v in n.items() if k != 'news'}, ensure_ascii=False) + ''.join(x.get('title', '') for x in n.get('news') or [])
    c = sum(body.count(p) for p in BOILER)
    if c > BOILER_MAX: bad.append(f'制式提醒句（{"／".join(BOILER)}）{c} 次，上限 {BOILER_MAX}（新聞解讀不算）')
    ev = n.get('events') or []; ed = [e.get('date', '') for e in ev]; lab = ' '.join(e.get('label', '') for e in ev)
    if any(d < bar_date for d in ed): bad.append(f'events 有已過去的日期：{[d for d in ed if d < bar_date]}')
    if ed != sorted(ed): bad.append('events 沒有依日期排序')
    miss = [k for k, kw in EVENTS.items() if kw not in lab]
    if miss: bad.append(f'events 缺：{"、".join(miss)}（未來 60 天內每一類都會發生；官方未公布就寫慣例日期並標「待官方排程確認」）')
    if ed and max(ed) < (dt.date.fromisoformat(bar_date) + dt.timedelta(days=45)).isoformat(): bad.append(f'events 只排到 {max(ed)}，應滾動到 60 天後')
    if en is None: bad.append('缺 notes.en.json'); return bad
    if (en.get('date'), en.get('edition')) != (n.get('date'), n.get('edition')): bad.append('英文版 date／edition 和中文版不同')
    if len(en.get('headline', '')) > HEAD_EN: bad.append(f"英文頭條 {len(en.get('headline', ''))} 字元，上限 {HEAD_EN}")
    if len(en.get('summary', '')) > SUM_EN: bad.append(f"英文摘要 {len(en.get('summary', ''))} 字元，上限 {SUM_EN}")
    cjk = sorted({p for p, t in texts(en) if CJK.search(t) and not p.endswith('news.cat')})
    if cjk: bad.append(f'英文版有中文字：{cjk[:5]}')
    if [x.get('url') for x in en.get('news') or []] != [x.get('url') for x in n.get('news') or []]: bad.append('英文版 news 和中文版不一致')
    return bad


if __name__ == '__main__':
    D = lambda f: os.path.join(ROOT, 'data', f)
    n = json.load(open(D('notes.json'))); en = json.load(open(D('notes.en.json'))) if os.path.exists(D('notes.en.json')) else None
    bad = lint(n, en, json.load(open(D('latest.json')))['meta']['bar_date'])
    for b in bad: print('✗', b)
    print(f"notes {n.get('date')} No.{n.get('edition')}：{'有 ' + str(len(bad)) + ' 項要修' if bad else '通過'}")
    sys.exit(1 if bad else 0)
