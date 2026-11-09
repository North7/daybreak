#!/usr/bin/env python3
"""檢查當期 data/notes.json／notes.en.json 是否符合 docs/CLAUDE_DAILY.md 的格式與長度規則（2026-10-21 建立）。
2026-10-21 自我檢查發現：事件表連 7 期缺 CPI、摘要寫到 4–6 句、頭條 76–107 字、制式提醒句每期約 20 次，都是規則有寫但沒人檢查。
用法（在倉庫根目錄）：python3 pipeline/notes_lint.py   # 有問題會列出並以非零結束
2026-10-23：加查 findings／followups（發現與追蹤），上一期從 data/archive/ 讀
2026-11-09：加查「說重點」的固定說法與中文常用名（使用者要日報照運營長文的寫法；詞表取自 daybreak-ops/ops/replies/check.py 的 AI_WORDS、EN_NAMES）
2026-11-09：加查去 AI 味第二輪（運營 voice.md 同名一節；lieflat 人類 vs AI 配對實測、Wikipedia「Signs of AI writing」）：套話直接擋，句型與口頭禪只提醒（△，不影響結束碼）"""
import json, os, re, sys, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CJK = re.compile(r'[一-鿿]')
HEAD_ZH, HEAD_EN, SUM_ZH, SUM_EN = 60, 150, 180, 480   # 頭條與摘要的字數上限（字元）
BOILER = ('只作讀值', '不改變', '不是框架條件', '不碰')   # 制式提醒句；news[].read 本來就要寫影不影響週期，不算在內
BOILER_MAX = 4
F_KEYS = ('id', 'title', 'module', 'signals', 'confidence', 'lean', 'lean_why', 'what', 'why', 'alt', 'history', 'so', 'next', 'check')   # 2026-10-23 發現與追蹤
F_TITLE_ZH, F_TITLE_EN = 30, 90
STATUS = ('open', 'confirmed', 'refuted', 'expired')
# 2026-11-09 說重點：結論講成市場的事實、兩種走法直接講，不寫「看錯／照舊走／找不到誰／看了一圈」（見 docs/CLAUDE_DAILY.md 寫作規則）
VAGUE = re.compile(r'看錯|照舊走|照舊在走|不一定照舊|找不到誰|找不到有誰|看了一圈|我找不到|我沒找到|could be wrong|I\'m wrong|I was wrong|nobody I can find|I can\'t find any', re.I)
EN_NAMES = {'比特幣': 'BTC', '以太坊': 'ETH', '以太幣': 'ETH', '那斯達克': 'Nasdaq', '納斯達克': 'Nasdaq', '標普': 'S&P 500', '輝達': 'Nvidia', '英偉達': 'Nvidia',
            '微策略': 'Strategy', '幣安': 'Binance', '貝萊德': 'BlackRock', '富達': 'Fidelity', '灰度': 'Grayscale'}   # 中文版有英文常用名的直接用英文（hashtag 不算）
EN_NAME = re.compile(r'(?<!#)(' + '|'.join(EN_NAMES) + ')')
SKIP = ('.url', '.source', '.cat', '.time')   # 新聞的網址、來源名、分類、時間不檢查
# 2026-11-09 去 AI 味第二輪（見 docs/CLAUDE_DAILY.md「去 AI 味」），一出現就擋。新聞標題是轉述別家的標題，不算
AIW = (('泛指來源：說是誰（「X 上這兩天好幾則」、資料商名），或刪掉直接講正確解讀；別人的說法用「」框起來',
        re.compile(r"很多人說|不少人說|大家都說|(?<![沒没])有人說|市場普遍|普遍認為|不少人認為|很多人認為|\b(lots of people|(?<!how )many people|some (people )?say)\b", re.I)),
       ('書面填充詞／淺層分析尾句：刪掉直接講；尾句寫具體後果，沒有後果就刪',
        re.compile(r"某種程度|一定程度上|本質上|換句話說|不難發現|毋庸置疑|顯而易見|值得注意的是|凸顯|彰顯|體現了|反映了[^，。；]{0,16}的重要性|\b(the reality is|to be clear|let's be (clear|honest)|at the end of the day|bottom line|in other words|key takeaway|game.?changers?)\b", re.I)),
       ('固定收尾句：樣本小、外推寫進引用數字的那一句（「2012 年以來才 3 次」「照近 30 天的速度直線外推」），不另起一句',
        re.compile(r"只能當個?(參考|背景)|有變化再更新|\b(not a forecast|only as background|background only)\b", re.I)))
# 只提醒：一則解讀（一版、一則 finding……）裡出現第二次才算
FOCUS = re.compile(r"分辨的方法是|要盯的是|要看的是|要注意的是|關鍵在於|關鍵是|的原因是|真正的(問題|差別|重點)是|What(?:'s| is) (?:missing|different|new|changed|interesting) is|The (?:tell|catch|difference|problem|key|short version) is", re.I)
CONTRAST = re.compile(r"不是[^，。？\n]{1,24}[，,、 ]?(而)?是|不等於|\bnot (just |only )?an? [^,.]{1,30}, (but )?|, not an? |isn't [^,.]{1,30}[,.] it's|rather than", re.I)
PET = {'比較像': 2, '真的': 3, '其實': 3, '我覺得': 3, 'to me': 2, 'though': 2}   # 一天全部解讀加起來的上限
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


def units(doc):
    """一則解讀＝一個單位：頭條＋摘要、各版（lead＋points）、各則 finding、各則 action／change／followup、新聞解讀。"""
    yield '頭條摘要', [doc.get('headline', ''), doc.get('summary', '')]
    for m, v in (doc.get('modules') or {}).items(): yield f'modules.{m}', [v.get('lead', '')] + list(v.get('points') or [])
    for f in doc.get('findings') or []: yield f'finding {f.get("id")}', [f.get(k) for k in ('title', 'what', 'why', 'alt', 'history', 'so', 'next', 'lean_why') if isinstance(f.get(k), str)]
    for i, a in enumerate(doc.get('actions') or []): yield f'actions[{i}]', [a.get('text', '')]; yield f'actions[{i}].head', [a.get('head', '')]
    for i, c in enumerate(doc.get('changes') or []): yield f'changes[{i}]', [c.get('title', ''), c.get('say', '')]
    for f in doc.get('followups') or []: yield f'followup {f.get("id")}', [f.get('say', '')]
    for i, x in enumerate(doc.get('news') or []): yield f'news[{i}]', [x.get('read', '')]


def _sents(t, zh):
    return [x.strip() for x in (re.split(r'(?<=[。！？；])|\n', t) if zh else re.split(r'(?<=[.!?;])\s+|\n', t)) if x and x.strip()]


def _tail(t):   # 收尾句比對用：去掉標點與空白
    return re.sub(r'[\W_]', '', t)


def lint_voice(doc, zh, prev=None):
    """去 AI 味第二輪（2026-11-09）。回傳 (要修, 提醒)。不抓精確數字、序數、設問、「這意味著」、被動句、段首連接詞（實測不是 AI 味）。"""
    bad, warn, tag = [], [], '' if zh else '英文版'
    for why, rx in AIW:
        hit = {}
        for p, t in texts(doc):
            if p.endswith(SKIP) or p.endswith('news.title'): continue
            for m in rx.finditer(t): hit.setdefault(m.group(0), set()).add(p)
        for w, ps in hit.items(): bad.append(f'{tag}有「{w}」（{"、".join(sorted(ps)[:3])}）：{why}')
    U = list(units(doc)); allt = '\n'.join(t for _, ts in U for t in ts if t)
    for lab, ts in U:
        body = '\n'.join(t for t in ts if t)
        f = [m.group(0) for m in FOCUS.finditer(body)]
        if len(f) > 1: warn.append(f'{tag}{lab} 焦點後置 {len(f)} 處（{"／".join(f)}）：直接講後面那件事，一則最多一次')
        c = len(CONTRAST.findall(body))
        if c > 1: warn.append(f'{tag}{lab}「不是 X，是 Y」對比句 {c} 處：一則最多 1 處')
    pets = []
    for w, mx in PET.items():
        if w[0].isascii() == zh: continue
        k = len(re.findall(r'\bthough(?=[,.;!?]|$)' if w == 'though' else (r'\b' + re.escape(w) + r'\b' if w[0].isascii() else re.escape(w)), allt, re.I | re.M))
        if k > mx: pets.append(f'{w} {k} 次（上限 {mx}）')
    if pets: warn.append(f'{tag}口頭禪：' + '、'.join(pets) + '，判斷詞換著用（就是／八成／應該是／看起來像／多半；looks like／my guess is／probably）')
    ss = [x for _, ts in U for t in ts if t for x in _sents(t, zh)]
    so = sum(1 for x in ss if re.match(r'所以' if zh else r'So\b', x))
    if so > 4: warn.append(f'{tag}「{"所以" if zh else "So"}」開頭的句子 {so} 句：一天最多三四次，結論已經在前面')
    punch, tails = [], {}
    for lab, ts in U:   # 新聞解讀照規則要寫影不影響週期、action 的 head 是狀態列，這兩種不算收尾句；用數字或細節收的也不算
        if lab.startswith('news') or lab.endswith('.head'): continue
        for t in ts:
            s_ = _sents(t or '', zh)
            if not s_ or re.search(r'\d', s_[-1]): continue
            if len(s_) >= 2 and len(_tail(s_[-1]) if zh else s_[-1]) <= (8 if zh else 25): punch.append(f'{lab}「{s_[-1]}」')
            if len(_tail(s_[-1])) >= 6: tails.setdefault(_tail(s_[-1]), []).append(lab)
    if len(punch) > 2: warn.append(f'{tag}短句收尾 {len(punch)} 處（{"；".join(punch[:4])}）：一天一兩處就好，其他用數字或細節收')
    rep = [f'「{k[:16]}」×{len(v)}' for k, v in tails.items() if len(v) >= 3]
    if rep: warn.append(f'{tag}同一句收尾用了好幾次：{"、".join(rep)}：每則解讀都同一句型收尾就是模板')
    if prev:
        pt = {_tail(_sents(t, zh)[-1]) for lab, ts in units(prev) if not (lab.startswith('news') or lab.endswith('.head')) for t in ts if t and _sents(t, zh)}
        same = sorted({k for k in tails if k in pt})
        if same: warn.append(f'{tag}和上一期用同一句收尾：{"、".join("「" + k[:16] + "」" for k in same[:3])}：固定收尾句不要每天一樣')
    return bad, warn


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
    for doc, tag in ((n, ''), (en, '英文版')):
        if doc is None: continue
        hit = {}
        for p, t in texts(doc):
            if p.endswith(SKIP): continue
            for m in VAGUE.finditer(t): hit.setdefault(m.group(0), []).append(p)
        for w, ps in hit.items(): bad.append(f'{tag}有「{w}」（{"、".join(sorted(set(ps))[:3])}）：說重點，結論講成市場的事實、兩種走法直接講，見寫作規則')
    names = {}
    for p, t in texts(n):
        if not p.endswith(SKIP):
            for w in EN_NAME.findall(t): names.setdefault(w, set()).add(p)
    if names: bad.append('中文版的常用名要用英文：' + '、'.join(f'{w}→{EN_NAMES[w]}（{"、".join(sorted(ps)[:2])}）' for w, ps in names.items()))
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
    prev = json.load(open(os.path.join(D('archive'), arc[-1]))) if arc else None
    bad += lint_findings(n, en, L, prev)
    pen = os.path.join(D('archive'), arc[-1][:10] + '.en.json') if arc else ''
    warn = []
    for doc, zh, pv in ((n, True, prev), (en, False, json.load(open(pen)) if os.path.exists(pen) else None)):
        if doc is None: continue
        b, w = lint_voice(doc, zh, pv); bad += b; warn += w
    for b in bad: print('✗', b)
    for w in warn: print('△', w)
    print(f"notes {n.get('date')} No.{n.get('edition')}：{'有 ' + str(len(bad)) + ' 項要修' if bad else '通過'}" + (f'；{len(warn)} 項提醒（△，看過再決定要不要改）' if warn else ''))
    sys.exit(1 if bad else 0)
