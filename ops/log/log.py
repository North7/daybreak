#!/usr/bin/env python3
"""成效紀錄（2026-11-04 建立）：每天發了什麼、對方有沒有回應、瀏覽多少，回頭看哪種內容有效。
紀錄檔是私人倉庫 daybreak-ops-private 的 ops/log/<日期>.json（2026-11-08 起；日期＝台北時間），格式見同一處的 README.md。用法（在倉庫根目錄）：

  python3 ops/log/log.py update [日期]                     一次做完下面四件事（預設：今天）
  python3 ops/log/log.py sync [日期]                       從個人頁讀那天發的原創貼文，自動加進紀錄並分類
  python3 ops/log/log.py refresh [日期]                    重新讀那天每則的瀏覽／讚／回覆／轉推
  python3 ops/log/log.py comments [日期]                   讀每則底下的留言：誰回、是不是藍勾；回覆對象本人有回就填 back.replied
  python3 ops/log/log.py followers [日期]                  追蹤者快照：總數、藍勾數、比上次多了誰；回覆對象有回追就填 back.followed
  python3 ops/log/log.py add <日期> <類型> <網址或ID>...    手動加（回覆一定要用這個：個人頁讀不到回覆分頁）
  python3 ops/log/log.py summary                          彙整所有紀錄

類型：daily（日報貼文）、flash（快訊）、pick（推薦圖表）、quote（引用）、article（長文或長文的短貼文）、
      post（其他原創）、reply（回覆 Grok 找的貼文）、followup（回覆別人在我們貼文底下的留言）。
數字讀自 api.fxtwitter.com（第三方、公開、不需登入）；它讀不到通知、按讚名單和回覆分頁，這些還是要看通知截圖。
追蹤者名單只存在本機 ~/.cache/daybreak-ops/（用來比對新增），不進 git。"""
import glob, json, os, re, statistics, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'ops'))
import opsprivate   # noqa: E402
DIR = opsprivate.path('log')   # 2026-11-08 起紀錄檔在私人倉庫 daybreak-ops-private/ops/log/（README 也在那裡）
HANDLE = 'songpu717'
GOAL = 500                                   # 原創內容獎勵（2026-09-07 起取代創作者分潤）要的藍勾追蹤數
GOAL_IMP = 500_000                           # 原創內容獎勵要的近 90 天藍勾首頁曝光（回覆不算）
TPE = timezone(timedelta(hours=8))
CACHE = os.path.expanduser('~/.cache/daybreak-ops')
UA = {'User-Agent': 'daybreak-ops-log'}
KINDS = ('daily', 'flash', 'pick', 'quote', 'article', 'post', 'reply', 'followup')
KIND_ZH = {'daily': '日報貼文', 'flash': '快訊', 'pick': '推薦圖表', 'quote': '引用', 'article': '長文',
           'post': '其他原創', 'reply': '回覆', 'followup': '回覆留言'}
ID = re.compile(r'(?:x|twitter)\.com/\w+/status/(\d+)')


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')


def today():
    return datetime.now(TPE).strftime('%Y-%m-%d')


def fetch(url):
    for n in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25))
        except Exception:
            if n == 2: raise
            time.sleep(2)


def get(i):
    return fetch(f'https://api.fxtwitter.com/status/{i}').get('tweet') or {}


def fx2(p):
    time.sleep(0.4)
    return fetch('https://api.fxtwitter.com/2/' + p)


def tpe_date(s):
    return datetime.strptime(s, '%a %b %d %H:%M:%S %z %Y').astimezone(TPE).strftime('%Y-%m-%d')


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


def entry(i, kind):
    t = get(i)
    q = t.get('quote') or {}
    to_id = t.get('replying_to_status') or q.get('id')
    p = {'id': i, 'kind': kind, 'at': t.get('created_at'), 'lang': lang(t),
         'to': t.get('replying_to') or (q.get('author') or {}).get('screen_name'), 'to_id': to_id,
         'image': bool(t.get('media')), 'text': t.get('text', '')[:80].replace('\n', ' ')}
    if kind == 'daily':
        p['style'] = daily_style(t.get('text', ''))
    if to_id:
        p.update(replies_ref(to_id))
        if 'to_followers' not in p:
            try:
                p['to_followers'] = (get(to_id).get('author') or {}).get('followers')
            except Exception:
                pass
    p.update(metrics(t))
    p['back'] = {}
    return p


def daily_style(text):
    """日報開頭實驗（2026-11-05 起）：【破曉 No.xxx】開頭是公告式，其他是數字開頭。"""
    head = re.sub(r'^\s*(#BTC\s*)?', '', text)
    return '公告式' if head.startswith('【') or re.match(r'No\.\d+', head) else '數字開頭'


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
        p = entry(i, kind)
        D['posts'].append(p); have.add(i)
        print(f'+ {KIND_ZH[kind]} → @{p["to"] or "-"}  瀏覽 {p["views"]}  {p["text"][:40]}')
    D['metrics_at'] = now()
    save(D)


def heads(rel, *keys):
    """data/ 裡當天草稿的開頭（用來辨認快訊、推薦圖表）。"""
    try:
        J = json.load(open(os.path.join(ROOT, 'data', rel), encoding='utf-8'))
    except Exception:
        return []
    items = J.get('items') or J.get('picks') or []
    return [re.sub(r'\s+', '', it[k])[:14] for it in items for k in keys if it.get(k)]


def classify(t):
    text = t.get('text', '')
    flat = re.sub(r'\s+', '', text)
    if t.get('quote'):
        return 'quote'
    if re.search(r'破曉 ?No\.|Daybreak No\.', text):
        return 'daily'
    if any(flat.startswith(h) for h in heads('flash.json', 'zh', 'en')):
        return 'flash'
    if any(flat.startswith(h) for h in heads('picks.json', 'zh', 'en')):
        return 'pick'
    if t.get('article') or 'x.com/i/article' in text or '/ops/articles/' in text:
        return 'article'
    return 'post'


def sync(date):
    """讀個人頁的原創貼文（不含回覆），把那天發的加進紀錄。"""
    D = load(date)
    have = {p['id'] for p in D['posts']}
    cur, added = None, 0
    for _ in range(6):
        d = fx2(f'profile/{HANDLE}/statuses' + (f'?cursor={urllib.parse.quote(cur)}' if cur else ''))
        rs = d.get('results') or []
        older = False
        for s in rs:
            if (s.get('author') or {}).get('screen_name', HANDLE).lower() != HANDLE.lower():
                continue                                   # 轉推別人的
            dd = tpe_date(s['created_at'])
            if dd < date: older = True; continue
            if dd != date or s['id'] in have: continue
            t = get(s['id'])
            p = entry(s['id'], classify(t))
            D['posts'].append(p); have.add(s['id']); added += 1
            print(f'+ {KIND_ZH[p["kind"]]}  瀏覽 {p["views"]}  {p["text"][:40]}')
        cur = (d.get('cursor') or {}).get('bottom')
        if older or not rs or not cur:
            break
    D['metrics_at'] = now()
    save(D)
    print(f'{date}：新加 {added} 則原創（類型是自動判斷的，不對就改 kind）')


def refresh(date):
    D = load(date)
    for p in D['posts']:
        try:
            p.update(metrics(get(p['id'])))
        except Exception as e:
            print('讀取失敗', p['id'], e)
    D['metrics_at'] = now()
    save(D)
    print(f'{date}：{len(D["posts"])} 則已更新瀏覽等數字（{D["metrics_at"]}）')


def comments(date):
    """每則底下的留言（含串裡的後續回覆），不算自己的。"""
    D = load(date)
    n = 0
    for p in D['posts']:
        try:
            d = fx2(f'conversation/{p["id"]}')
        except Exception as e:
            print('讀取失敗', p['id'], e); continue
        cs = []
        for r in d.get('replies') or []:
            a = r.get('author') or {}
            if a.get('screen_name', '').lower() == HANDLE.lower():
                continue
            cs.append({'by': a.get('screen_name'), 'verified': bool((a.get('verification') or {}).get('verified')),
                       'followers': a.get('followers'), 'id': r.get('id'), 'text': (r.get('text') or '')[:60].replace('\n', ' ')})
        p['comments'] = cs
        n += len(cs)
        mine = [c for c in cs if p.get('to') and (c['by'] or '').lower() == p['to'].lower()]
        if mine and p['kind'] in ('reply', 'quote', 'followup'):
            p.setdefault('back', {})['replied'] = max(len(mine), (p.get('back') or {}).get('replied') or 0)
    D['comments_at'] = now()
    save(D)
    print(f'{date}：{len(D["posts"])} 則底下共 {n} 則別人的留言')


def followers(date):
    """追蹤者快照。X 給的名單是最新追蹤的排最前面。"""
    D = load(date)
    total = (fetch(f'https://api.fxtwitter.com/{HANDLE}').get('user') or {}).get('followers')
    users, seen, cur = [], set(), None
    for _ in range(60):
        d = fx2(f'profile/{HANDLE}/followers' + (f'?cursor={urllib.parse.quote(cur)}' if cur else ''))
        new = [u for u in d.get('results') or [] if u['id'] not in seen]
        for u in new: seen.add(u['id'])
        users += new
        cur = (d.get('cursor') or {}).get('bottom')
        if not new or not cur:
            break
    ver = lambda u: bool((u.get('verification') or {}).get('verified'))
    nver = sum(ver(u) for u in users)
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, f'followers-{HANDLE}.json')
    prev = json.load(open(cp)) if os.path.exists(cp) else None
    a = D.setdefault('account', {})
    # 2026-11-08：同一天跑第二次時，原本會用「比上一次快照」的結果蓋掉當天的新增名單（25 人變 0）。
    # 這天已經記過快照的話，新增的累加上去、名單合併。
    again = bool(a.get('followers_at')) and 'new_list' in a
    a.update({'followers': total, 'followers_listed': len(users), 'verified_followers': nver, 'followers_at': now()})
    if prev:
        old = set(prev['ids'])
        fresh = [u for u in users if u['id'] not in old]
        # 2026-11-11 使用者問「今天誰取關了我」：以前只記人數，名單一覆蓋就查不到是誰。快照改成存 id→帳號，取關的人記名字。
        names_prev = prev.get('names') or {}
        gone_ids = old - seen
        gone_list = [{'by': names_prev.get(i, f'id:{i}'), 'verified': (prev.get('verified') or {}).get(i), 'at': now()} for i in sorted(gone_ids)]
        gone = len(gone_ids)
        lst = [{'by': u['screen_name'], 'verified': ver(u), 'followers': u.get('followers')} for u in fresh]
        if again:
            have = {x['by'] for x in a.get('new_list') or []}
            lst = (a.get('new_list') or []) + [x for x in lst if x['by'] not in have]
            gone += a.get('unfollowed') or 0
            gone_list = (a.get('unfollowed_list') or []) + gone_list
        a['new_followers'] = len(lst)
        a['new_verified_followers'] = sum(1 for x in lst if x['verified'])
        a['unfollowed'] = gone
        a['unfollowed_list'] = gone_list
        a['new_list'] = lst
        names = {u['screen_name'].lower() for u in fresh}
        for p in D['posts']:
            if p.get('to') and p['to'].lower() in names and p['kind'] in ('reply', 'quote', 'followup'):
                p.setdefault('back', {})['followed'] = True
        print(f'比上次（{prev["at"]}）多了 {len(fresh)} 人（藍勾 {a["new_verified_followers"]}），少了 {len(gone_ids)} 人'
              + (('：' + '、'.join('@' + x['by'] if not x['by'].startswith('id:') else x['by'] for x in gone_list[-len(gone_ids):])) if gone_ids else ''))
        if gone_ids and len(users) < (total or 0):
            print(f'  名單只讀到 {len(users)}／{total} 人，少掉的人裡可能有幾位只是這次沒讀到，不一定是取關')
    else:
        print('第一次快照，下次才比得出新增的是誰')
    json.dump({'at': now(), 'ids': [u['id'] for u in users], 'names': {u['id']: u['screen_name'] for u in users},
               'verified': {u['id']: ver(u) for u in users}}, open(cp, 'w'))
    save(D)
    print(f'追蹤 {total}（名單讀到 {len(users)}），藍勾 {nver}，離 {GOAL} 還差 {GOAL - nver}')


def update(date):
    sync(date); refresh(date); comments(date); followers(date)


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
    last = next((D['account'] for D in reversed(days) if (D.get('account') or {}).get('verified_followers')), None)
    if last:
        print(f'藍勾追蹤 {last["verified_followers"]}／{GOAL}（還差 {GOAL - last["verified_followers"]}）')
    imp = next(((D['date'], D['account']['verified_impressions_90d']) for D in reversed(days) if (D.get('account') or {}).get('verified_impressions_90d')), None)
    if imp:
        print(f'近 90 天藍勾曝光 {imp[1]:,}／{GOAL_IMP:,}（{imp[0]}，後台數字含回覆，只算原創會更少）')
    if last or imp:
        print()
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
    for k in KINDS:
        kp = [p for p in ps if p['kind'] == k and p.get('style')]
        styles = sorted({p['style'] for p in kp})
        if len(styles) > 1:
            table(f'{KIND_ZH[k]}：依寫法', [(s, [p for p in kp if p['style'] == s]) for s in styles], k == 'reply')
    rs = [p for p in ps if p['kind'] == 'reply']
    if rs:
        table('回覆：依語言', [(l, [p for p in rs if p.get('lang') == l]) for l in ('zh', 'en')], True)
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
    cs = [(p, c) for p in ps for c in p.get('comments') or []]
    if cs:
        print('\n### 誰在我們的貼文底下留言\n')
        who = {}
        for p, c in cs:
            who.setdefault(c['by'], []).append(c)
        for by, l in sorted(who.items(), key=lambda x: -len(x[1])):
            c = l[0]
            print(f'- @{by}（{"藍勾" if c["verified"] else "非藍勾"}，{c.get("followers") or "?"} 粉）：{len(l)} 則')


if __name__ == '__main__':
    a = sys.argv[1:]
    cmd = a[0] if a else ''
    day = a[1] if len(a) > 1 else today()
    if cmd == 'add' and len(a) >= 4:
        add(a[1], a[2], a[3:])
    elif cmd in ('sync', 'refresh', 'comments', 'followers', 'update'):
        globals()[cmd](day)
    elif cmd == 'summary':
        summary()
    else:
        sys.exit(__doc__)
