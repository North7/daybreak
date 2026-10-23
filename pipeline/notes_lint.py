#!/usr/bin/env python3
"""檢查當期 data/notes.json／notes.en.json 是否符合 docs/CLAUDE_DAILY.md 的格式與長度規則（2026-10-21 建立）。
2026-10-21 自我檢查發現：事件表連 7 期缺 CPI、摘要寫到 4–6 句、頭條 76–107 字、制式提醒句每期約 20 次，都是規則有寫但沒人檢查。
用法（在倉庫根目錄）：python3 pipeline/notes_lint.py   # 有問題會列出並以非零結束
2026-10-23：加查 findings／followups（發現與追蹤），上一期從 data/archive/ 讀"""
import json, os, re, sys, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJK = re.compile(r'[一-鿿]')
HEAD_ZH, HEAD_EN, SUM_ZH, SUM_EN = 60, 150, 180, 480   # 頭條與摘要的字數上限（字元）
BOILER = ('只作讀值', '不改變', '不是框架條件', '不碰')   # 制式提醒句；news[].read 本來就要寫影不影響週期，不算在內
BOILER_MAX = 4
F_KEYS = ('id', 'title', 'module', 'signals', 'confidence', 'lean', 'lean_why', 'what', 'why', 'alt', 'history', 'so', 'next', 'check')   # 2026-10-23 發現與追蹤
F_TITLE_ZH, F_TITLE_EN = 30, 90
STATUS = ('open', 'confirmed', 'refuted', 'expired')
EVENTS = {'CPI': 'CPI', 'FOMC': 'FOMC', '非農': '非農', '難度調整': '難度', 'Deribit 到期': 'Deribit', '月底路徑重估': '路徑'}


def texts(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items(): yield from texts(v, path + '.' + k)
    elif isinstance(o, list):
        for v in o: yield from texts(v, path)
    elif isinstance(o, str): yield path, o


def _get(o, path):
    for k in path.split('.'):
        if not isinstance(o, dict) or k not in o: return None
        o = o[k]
    return o


def lint_findings(n, en, L, prev):
    """findings／followups（2026-10-23）：欄位齊全、標題是結論長度、check 的 path 在 latest.json 是數字、signals id 存在；
    上一期每則 finding 與上一期 open 的 followup，這期都要有一筆 followup。"""
    bad = []; fs = n.get('findings')
    if fs is None: return ['缺 findings（沒有值得寫的發現就給空陣列 []）']
    if len(fs) > 3: bad.append(f'findings {len(fs)} 則，上限 3')
    sg = (L or {}).get('signals') or {}; known = {x['id'] for x in sg.get('items') or []} | set(sg.get('more') or [])
    ids = [f.get('id') for f in fs]
    if len(set(ids)) != len(ids): bad.append('findings 的 id 重複')
    for f in fs:
        fid = f.get('id') or '?'
        miss = [k for k in F_KEYS if f.get(k) in (None, '') and k != 'signals']
        if miss: bad.append(f'finding {fid} 缺欄位：{"、".join(miss)}')
        if not str(fid).startswith(n.get('date', '') + '-'): bad.append(f'finding id {fid} 應為 {n.get("date")}-序號')
        if len(f.get('title', '')) > F_TITLE_ZH: bad.append(f'finding {fid} 標題 {len(f.get("title", ""))} 字，上限 {F_TITLE_ZH}')
        if f.get('confidence') not in ('high', 'medium', 'low'): bad.append(f'finding {fid} confidence 要是 high／medium／low')
        if f.get('lean') not in ('bull', 'bear', 'neutral'): bad.append(f'finding {fid} lean 要是 bull／bear／neutral')
        unk = [x for x in f.get('signals') or [] if x not in known]
        if unk: bad.append(f'finding {fid} 引用了 signals 沒有的 id：{unk}')
        if not f.get('signals') and len(f.get('why', '')) < 40: bad.append(f'finding {fid} 沒有引用 signal，why 要寫明依據')
        bad += [f'finding {fid} {x}' for x in _check_ok(f.get('check'), L, n.get('date'), need=True)]
    pf = [f['id'] for f in (prev or {}).get('findings') or [] if f.get('id')] + [f['id'] for f in (prev or {}).get('followups') or [] if f.get('status') == 'open' and f.get('id')]
    fu = n.get('followups') or []; have = {f.get('id') for f in fu}
    miss = [x for x in pf if x not in have]
    if miss: bad.append(f'followups 缺上一期的：{miss}（每則上期 finding 與 open 的追蹤都要列一筆）')
    for f in fu:
        if f.get('status') not in STATUS: bad.append(f'followup {f.get("id")} status 要是 {"／".join(STATUS)}')
        if not f.get('say'): bad.append(f'followup {f.get("id")} 缺 say')
        if f.get('status') == 'open': bad += [f'followup {f.get("id")} {x}' for x in _check_ok(f.get('check'), L, n.get('date'), need=False)]
    if en is not None:
        if [f.get('id') for f in en.get('findings') or []] != ids: bad.append('英文版 findings 的 id／順序和中文版不同')
        if [f.get('id') for f in en.get('followups') or []] != [f.get('id') for f in fu]: bad.append('英文版 followups 和中文版不同')
        if [f.get('lean') for f in en.get('findings') or []] != [f.get('lean') for f in fs]: bad.append('英文版 findings 的 lean 和中文版不同')
        if [json.dumps([(c.get('path'), c.get('op'), c.get('value')) for c in _cl(f.get('check'))]) for f in en.get('findings') or []] != [json.dumps([(c.get('path'), c.get('op'), c.get('value')) for c in _cl(f.get('check'))]) for f in fs]:
            bad.append('英文版 findings 的 check 和中文版不同')
        for f in en.get('findings') or []:
            if len(f.get('title', '')) > F_TITLE_EN: bad.append(f'英文 finding {f.get("id")} 標題超過 {F_TITLE_EN} 字元')
    return bad


def _cl(ck): return [ck] if isinstance(ck, dict) else list(ck or [])


def _check_ok(ck, L, date, need):
    cs = _cl(ck); bad = []
    if need and not 1 <= len(cs) <= 2: bad.append(f'check 要 1–2 個，現在 {len(cs)} 個')
    for c in cs:
        v = _get(L or {}, c.get('path', ''))
        if not isinstance(v, (int, float)) or isinstance(v, bool): bad.append(f'check path {c.get("path")} 在 latest.json 不是數字')
        if c.get('op') not in ('<', '<=', '>', '>='): bad.append(f'check op {c.get("op")} 要是 < <= > >=')
        if not isinstance(c.get('value'), (int, float)): bad.append('check value 要是數字')
        if c.get('means') not in ('confirm', 'refute'): bad.append('check means 要是 confirm 或 refute')
        if not c.get('by') or (date and c['by'] < date): bad.append(f'check by（期限）{c.get("by")} 要是今天或之後的日期')
    return bad


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
    L = json.load(open(D('latest.json')))
    bad = lint(n, en, L['meta']['bar_date'])
    arc = sorted(f for f in os.listdir(D('archive')) if re.fullmatch(r'\d{4}-\d{2}-\d{2}\.json', f) and f[:10] < n.get('date', '')) if os.path.isdir(D('archive')) else []
    bad += lint_findings(n, en, L, json.load(open(os.path.join(D('archive'), arc[-1]))) if arc else None)
    for b in bad: print('✗', b)
    print(f"notes {n.get('date')} No.{n.get('edition')}：{'有 ' + str(len(bad)) + ' 項要修' if bad else '通過'}")
    sys.exit(1 if bad else 0)
