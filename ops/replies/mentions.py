#!/usr/bin/env python3
"""找出別人回我們、我們還沒接的留言（2026-11-08 建立，給排程任務自動接話用）。

做法（都讀 api.fxtwitter.com，不需登入）：
1. /2/profile/songpu717/statuses?with_replies=true：我們最近的原創和回覆（翻頁到 --since-hours 之前）。
2. 每一則 /2/conversation/<id>：底下別人的直接回覆。
3. 已經接過的不列：我們有一則回覆的對象就是那則留言、或 data/replies.json 裡已經有那則留言的 id。
4. 算「第幾輪」：從我們那則往上追，同一串裡我們已經回過幾次（同串最多兩輪，見 README「X 演算法的限制」）。

用法（在倉庫根目錄）：
  python3 ops/replies/mentions.py                 # 我們最近 30 小時的貼文底下、最近 12 小時的新留言
  python3 ops/replies/mentions.py --since-hours 48 --reply-hours 24 --json out.json
只讀不寫；寫回覆照 README「接續對話」。"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

HANDLE = 'songpu717'
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UA = {'User-Agent': 'daybreak-ops/1.0'}
_cache = {}


def fetch(url):
    for n in range(3):
        try:
            time.sleep(0.35)
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25))
        except Exception:
            if n == 2: raise
            time.sleep(2)


def status(i):
    if i not in _cache:
        try: _cache[i] = fetch(f'https://api.fxtwitter.com/status/{i}').get('tweet') or {}
        except Exception: _cache[i] = {}
    return _cache[i]


def parent_of(t):
    r = t.get('replying_to') or {}
    return (r.get('status') if isinstance(r, dict) else None) or t.get('replying_to_status')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since-hours', type=float, default=30, help='看我們多久以內發的貼文底下')
    ap.add_argument('--reply-hours', type=float, default=12, help='只列多久以內的新留言')
    ap.add_argument('--json', help='另外存成 JSON')
    a = ap.parse_args()
    now = time.time(); t0 = now - a.since_hours * 3600; r0 = now - a.reply_hours * 3600

    ours, cur = [], None
    # 2026-11-08：fxtwitter 每頁不是照時間排（第 2 頁還會有比第 1 頁最舊那則更新的），
    # 原本「這頁最舊的早於 t0 就停」會漏掉後面頁的貼文（漏了 BirdTechVision 那則接話）。
    # 改成整頁都早於 t0、連續兩頁才停，最多 12 頁，用 id 去重。
    old_pages = 0
    for _ in range(12):   # 翻頁
        q = 'with_replies=true' + (f'&cursor={urllib.parse.quote(cur)}' if cur else '')
        d = fetch(f'https://api.fxtwitter.com/2/profile/{HANDLE}/statuses?{q}')
        res = [t for t in d.get('results') or [] if (t.get('author') or {}).get('screen_name', '').lower() == HANDLE.lower()]
        ours += res
        for t in res: _cache[t['id']] = t
        cur = ((d.get('cursor') or {}).get('bottom'))
        if not res or not cur: break
        old_pages = old_pages + 1 if max(t.get('created_timestamp') or 0 for t in res) < t0 else 0
        if old_pages >= 2: break
    ours = list({t['id']: t for t in ours if (t.get('created_timestamp') or 0) >= t0}.values())
    answered = {parent_of(t) for t in ours if parent_of(t)}
    try:
        done = {str(i.get('id')) for i in json.load(open(os.path.join(ROOT, 'data', 'replies.json'), encoding='utf-8')).get('items', [])}
    except Exception:
        done = set()

    out = []
    for p in ours:
        try: conv = fetch(f'https://api.fxtwitter.com/2/conversation/{p["id"]}')
        except Exception as e: print('讀取失敗', p['id'], e, file=sys.stderr); continue
        for r in conv.get('replies') or []:
            au = r.get('author') or {}
            if au.get('screen_name', '').lower() == HANDLE.lower(): continue
            if parent_of(r) and parent_of(r) != p['id']: continue          # 只要直接回我們這則的
            if (r.get('created_timestamp') or 0) < r0: continue
            if r['id'] in answered or r['id'] in done: continue
            # 往上追：同一串我們已經回過幾次
            rounds, x, seen = 0, p, 0
            while x and seen < 8:
                if (x.get('author') or {}).get('screen_name', '').lower() == HANDLE.lower(): rounds += 1
                pid = parent_of(x); x = status(pid) if pid else None; seen += 1
            root = x if x is not None else {}
            par = status(parent_of(p)) if parent_of(p) else {}
            out.append({
                'id': r['id'], 'url': f'https://x.com/{au.get("screen_name")}/status/{r["id"]}',
                'author': au.get('screen_name'), 'name': au.get('name'), 'followers': au.get('followers'),
                'verified': bool((au.get('verification') or {}).get('verified')),
                'posted': r.get('created_at'), 'lang': r.get('lang'), 'text': r.get('text'),
                'likes': r.get('likes'), 'views': r.get('views'),
                'our_id': p['id'], 'our_text': p.get('text'), 'our_rounds': rounds,
                'above': {'author': (par.get('author') or {}).get('screen_name'), 'text': (par.get('text') or '')[:200]} if par else None,
                'is_original': not parent_of(p),
            })
    out.sort(key=lambda o: o.get('posted') or '')
    if a.json:
        json.dump(out, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'我們最近 {a.since_hours:g} 小時的 {len(ours)} 則貼文底下，最近 {a.reply_hours:g} 小時有 {len(out)} 則還沒接的留言\n')
    for i, o in enumerate(out, 1):
        tag = '原創底下' if o['is_original'] else f'我們已回 {o["our_rounds"]} 輪'
        print(f'#{i} @{o["author"]}（{o["followers"] or 0:,} 粉{"，藍勾" if o["verified"] else ""}）{o["posted"]}  {tag}  {o["url"]}')
        print('   他：' + (o['text'] or '').replace('\n', ' ')[:200])
        print('   我們：' + (o['our_text'] or '').replace('\n', ' ')[:120])


if __name__ == '__main__':
    main()
