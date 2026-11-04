#!/usr/bin/env python3
"""成效紀錄（2026-11-04 建立）：每天發了什麼、對方有沒有回應、瀏覽多少，回頭看哪種內容有效。
紀錄檔是 ops/log/<日期>.json，格式見 ops/log/README.md。用法（在倉庫根目錄）：

  python3 ops/log/log.py add <日期> <類型> <網址或ID>...   把自己發的貼文加進那天的紀錄（自動讀回覆對象、時間、瀏覽等）
  python3 ops/log/log.py refresh [日期]                    重新讀那天每則的瀏覽／讚／回覆／轉推（預設：最近一天）
  python3 ops/log/log.py summary                          彙整所有紀錄

類型：daily（日報貼文）、flash（快訊）、pick（推薦圖表）、quote（引用）、reply（回覆 Grok 找的貼文）、
      followup（回覆別人在我們貼文底下的留言）。數字讀自 api.fxtwitter.com（公開、不需登入）。"""
import glob, json, os, re, statistics, sys, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR = os.path.join(ROOT, 'ops', 'log')
KINDS = ('daily', 'flash', 'pick', 'quote', 'reply', 'followup')
KIND_ZH = {'daily': '日報貼文', 'flash': '快訊', 'pick': '推薦圖表', 'quote': '引用', 'reply': '回覆', 'followup': '回覆留言'}
ID = re.compile(r'(?:x|twitter)\.com/\w+/status/(\d+)')


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')


def get(i):
    req = urllib.request.Request(f'https://api.fxtwitter.com/status/{i}', headers={'User-Agent': 'daybreak-ops-log'})
    return json.load(urllib.request.urlopen(req, timeout=20)).get('tweet') or {}


def path(date):
    return os.path.join(DIR, f'{date}.json')


def load(date):
    p = path(date)
    if os.path.exists(p):
        return json.load(open(p, encoding='utf-8'))
    return {'date': date, 'account': {}, 'posts': [], 'notes': []}


def save(D):
    json.dump(D, open(path(D['date']), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(path(D['date']), 'a', encoding='utf-8').write('\n')


def metrics(t):
    return {'views': t.get('views'), 'likes': t.get('likes'), 'replies': t.get('replies'), 'rt': t.get('retweets')}


def lang(t):
    l = t.get('lang') or ''
    return 'zh' if l.startswith('zh') or l == 'ja' and re.search(r'[一-鿿]', t.get('text', '')) else l


def replies_ref(to_id):
    """回覆對象如果在 data/replies.json 裡，帶回編號、角度、配圖。"""
    try:
        R = json.load(open(os.path.join(ROOT, 'data', 'replies.json'), encoding='utf-8'))
    except Exception:
        return {}
    for it in R.get('items', []):
        if it.get('id') == to_id:
            return {'ref': it.get('n'), 'angle': it.get('angle'), 'chart': (it.get('image') or {}).get('chart'),
                    'to_followers': it.get('followers')}
    return {}


def add(date, kind, args):
    if kind not in KINDS:
        sys.exit(f'類型要是 {"、".join(KINDS)} 之一')
    D = load(date)
    have = {p['id'] for p in D['posts']}
    for a in args:
        m = ID.search(a)
        i = m.group(1) if m else a
        if i in have:
            print('已經有了', i); continue
        t = get(i)
        q = t.get('quote') or {}
        to_id = t.get('replying_to_status') or q.get('id')
        p = {'id': i, 'kind': kind, 'at': t.get('created_at'), 'lang': lang(t),
             'to': t.get('replying_to') or (q.get('author') or {}).get('screen_name'), 'to_id': to_id,
             'image': bool(t.get('media')), 'text': t.get('text', '')[:80].replace('\n', ' ')}
        if to_id:
            p.update(replies_ref(to_id))
            if 'to_followers' not in p:
                try:
                    p['to_followers'] = (get(to_id).get('author') or {}).get('followers')
                except Exception:
                    pass
        p.update(metrics(t))
        p['back'] = {}
        D['posts'].append(p); have.add(i)
        print(f'+ {KIND_ZH[kind]} → @{p["to"] or "-"}  瀏覽 {p["views"]}  {p["text"][:40]}')
    D['metrics_at'] = now()
    save(D)


def refresh(date):
    D = load(date)
    for p in D['posts']:
        try:
            p.update(metrics(get(p['id'])))
        except Exception as e:
            print('讀取失敗', p['id'], e)
    D['metrics_at'] = now()
    save(D)
    print(f'{date}：{len(D["posts"])} 則已更新（{D["metrics_at"]}）')


def responded(p):
    b = p.get('back') or {}
    return bool(b.get('liked') or b.get('replied') or b.get('followed'))


def row(name, ps, with_back):
    v = [p['views'] for p in ps if isinstance(p.get('views'), int)]
    cells = [name, str(len(ps)), f'{statistics.mean(v):.0f}' if v else '-', f'{statistics.median(v):.0f}' if v else '-',
             str(sum(p.get('likes') or 0 for p in ps)), str(sum(p.get('replies') or 0 for p in ps))]
    if with_back:
        n = sum(responded(p) for p in ps)
        cells.append(f'{n}/{len(ps)}')
    return '| ' + ' | '.join(cells) + ' |'


def table(title, groups, with_back=False):
    head = ['', '則數', '平均瀏覽', '中位數', '讚', '留言'] + (['對方有回應'] if with_back else [])
    print(f'\n### {title}\n')
    print('| ' + ' | '.join(head) + ' |')
    print('|' + '---|' * len(head))
    for name, ps in groups:
        if ps: print(row(name, ps, with_back))


def tier(n):
    if not isinstance(n, int): return '粉絲數不明'
    return '對方 < 1 萬粉' if n < 10_000 else '對方 1–10 萬粉' if n < 100_000 else '對方 > 10 萬粉'


def summary():
    days = [json.load(open(f, encoding='utf-8')) for f in sorted(glob.glob(os.path.join(DIR, '20*.json')))]
    if not days:
        sys.exit('還沒有紀錄')
    print('### 每天\n')
    print('| 日期 | 追蹤 | 藍勾追蹤 | 新追蹤 | 發了幾則 | 總瀏覽 | 數字讀取時間 |')
    print('|---|---|---|---|---|---|---|')
    for D in days:
        a = D.get('account') or {}
        tot = sum(p.get('views') or 0 for p in D['posts'])
        print(f'| {D["date"]} | {a.get("followers", "-")} | {a.get("verified_followers") or "-"} | {a.get("new_followers", "-")} '
              f'| {len(D["posts"])} | {tot:,} | {D.get("metrics_at", "-")} |')
    ps = [p for D in days for p in D['posts']]
    table('依類型', [(KIND_ZH[k], [p for p in ps if p['kind'] == k]) for k in KINDS])
    rs = [p for p in ps if p['kind'] == 'reply']
    if rs:
        table('回覆：依語言', [(l, [p for p in rs if p.get('lang') == l]) for l in ('zh', 'en')], True)
        styles = sorted({p.get('style') for p in rs if p.get('style')})
        if styles:
            table('回覆：依寫法', [(s, [p for p in rs if p.get('style') == s]) for s in styles], True)
        table('回覆：有沒有配圖', [('有圖', [p for p in rs if p.get('image')]), ('沒圖', [p for p in rs if not p.get('image')])], True)
        tiers = ('對方 < 1 萬粉', '對方 1–10 萬粉', '對方 > 10 萬粉', '粉絲數不明')
        table('回覆：依對方大小', [(t, [p for p in rs if tier(p.get('to_followers')) == t]) for t in tiers], True)
    back = [p for p in ps if responded(p)]
    if back:
        print('\n### 有回應的對象\n')
        for p in back:
            b = p['back']
            what = '、'.join(x for x, k in (('按讚', 'liked'), ('回覆', 'replied'), ('追蹤', 'followed')) if b.get(k))
            print(f'- @{p.get("to")}（{KIND_ZH[p["kind"]]}，{p.get("lang")}）：{what}' + (f'；{b["note"]}' if b.get('note') else ''))


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['add'] and len(a) >= 4:
        add(a[1], a[2], a[3:])
    elif a[:1] == ['refresh']:
        files = sorted(glob.glob(os.path.join(DIR, '20*.json')))
        if not files and len(a) < 2: sys.exit('還沒有紀錄')
        refresh(a[1] if len(a) > 1 else os.path.basename(files[-1])[:10])
    elif a[:1] == ['summary']:
        summary()
    else:
        sys.exit(__doc__)
