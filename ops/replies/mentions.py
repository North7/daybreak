#!/usr/bin/env python3
"""找出別人回我們、我們還沒接的留言（2026-11-08 建立，給排程任務自動接話用）。

做法（都讀 api.fxtwitter.com，不需登入）：
1. /2/profile/songpu717/statuses?with_replies=true：我們最近的原創和回覆（翻頁到 --since-hours 之前）。
2. 每一則 /2/conversation/<id>：底下別人的直接回覆。
3. 已經接過的不列：我們有一則回覆的對象就是那則留言、或 data/replies.json 裡已經有那則留言的 id。
4. 算「第幾輪」：從我們那則往上追，同一串裡我們已經回過幾次（同串最多兩輪，見 README「X 演算法的限制」）。

2026-11-25 補：只看最近 30 小時的貼文，會漏掉舊原創和置頂文底下的留言（11/12 置頂介紹文 11/21–11/24 有 3 則留言沒接，
使用者在手機上看到才發現）。現在另外掃：最近 --orig-days 天的原創（不含回覆）＋ EVERGREEN 列的置頂、宣傳文，
這些貼文底下最近 --orig-reply-hours 小時的留言也列出來。換置頂時更新 EVERGREEN。

用法（在倉庫根目錄）：
  python3 ops/replies/mentions.py                 # 我們最近 30 小時的貼文底下、最近 12 小時的新留言；加上 7 天內原創＋置頂文底下最近 72 小時的
  python3 ops/replies/mentions.py --since-hours 48 --reply-hours 24 --json out.json
只讀不寫；寫回覆照 README「接續對話」。"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

HANDLE = 'songpu717'
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UA = {'User-Agent': 'daybreak-ops/1.0'}
_cache = {}
# 置頂、宣傳文：發很久了還會有人留言，固定每輪都掃（2026-11-25）
EVERGREEN = ['2120733066939482177']   # 11/12 One minute every morning to see where BTC stands（置頂）


def fetch(url, tries=3):
    for n in range(tries):
        try:
            time.sleep(0.35)
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25))
        except Exception:
            if n == tries - 1: raise
            time.sleep(2 + n * 2)


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
    ap.add_argument('--orig-days', type=float, default=7, help='另外掃多少天內的原創（不含回覆）')
    ap.add_argument('--orig-reply-hours', type=float, default=72, help='舊原創和置頂文底下，列多久以內的留言')
    ap.add_argument('--json', help='另外存成 JSON')
    a = ap.parse_args()
    now = time.time(); t0 = now - a.since_hours * 3600; r0 = now - a.reply_hours * 3600
    o0 = now - a.orig_days * 86400; ro = now - a.orig_reply_hours * 3600

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
    answered = {parent_of(t) for t in ours if parent_of(t)}   # 翻到的全部回覆都算（舊留言可能是更早接的）
    ours = list({t['id']: t for t in ours if (t.get('created_timestamp') or 0) >= t0}.values())
    for t in ours: t['_r0'] = r0
    # 舊原創（不含回覆）＋置頂文：留言窗口放寬到 --orig-reply-hours
    # 2026-11-28：原創一頁只回 20 則（約 2–3 天），第 2 頁常吃到 404，原本 3 次失敗就默默 break，
    # 11/25 CVDD 長文底下 11/26–11/27 三則留言（MceeyCare、yinghong1388、zhoujinyuanfafa）因此一直沒接，使用者在手機上發現。
    # 改成多試幾次（6 次、間隔拉長），真的讀不到就在輸出最後列出來，不再只印到 stderr。
    olds, cur, have, olds_fail = [], None, {t['id'] for t in ours}, None
    for page in range(6):
        q = 'count=50' + (f'&cursor={urllib.parse.quote(cur)}' if cur else '')
        try: d = fetch(f'https://api.fxtwitter.com/2/profile/{HANDLE}/statuses?{q}', tries=6)
        except Exception as e:
            olds_fail = f'原創列表第 {page + 1} 頁讀取失敗（{e}），已讀到 {time.strftime("%m/%d %H:%M", time.localtime(min(t.get("created_timestamp") or now for t in olds))) if olds else "無"} 為止'
            print('讀取原創失敗', e, file=sys.stderr); break
        res = [t for t in d.get('results') or [] if (t.get('author') or {}).get('screen_name', '').lower() == HANDLE.lower() and not parent_of(t)]
        olds += res
        cur = ((d.get('cursor') or {}).get('bottom'))
        if not res or not cur or max(t.get('created_timestamp') or 0 for t in res) < o0: break
    for i in EVERGREEN:
        t = status(i)
        if t: olds.append(t)
    for t in olds:
        if t['id'] in have: continue
        if t['id'] not in EVERGREEN and (t.get('created_timestamp') or 0) < o0: continue
        _cache[t['id']] = t; t['_r0'] = ro; ours.append(t); have.add(t['id'])
    try:
        done = {str(i.get('id')) for i in json.load(open(os.path.join(ROOT, 'data', 'replies.json'), encoding='utf-8')).get('items', [])}
    except Exception:
        done = set()

    out, gaps = [], []
    for p in ours:
        try: conv = fetch(f'https://api.fxtwitter.com/2/conversation/{p["id"]}')
        except Exception as e: print('讀取失敗', p['id'], e, file=sys.stderr); gaps.append((p, '讀取失敗')); continue
        # 2026-11-08：conversation 有時少回留言（hzql7878 回我們給 Murphy 那則，貼文顯示 1 則留言、conversation 回 0 則，
        # 翻 cursor 也是空的），這種只能在瀏覽器打開看。貼文顯示的留言數比讀到的多，就列出來。
        got = len(conv.get('replies') or [])
        if (p.get('replies') or 0) > got and (p.get('created_timestamp') or 0) >= r0 - 12 * 3600:
            gaps.append((p, f'顯示 {p.get("replies")} 則留言、讀到 {got} 則'))
        for r in conv.get('replies') or []:
            au = r.get('author') or {}
            if au.get('screen_name', '').lower() == HANDLE.lower(): continue
            if parent_of(r) and parent_of(r) != p['id']: continue          # 只要直接回我們這則的
            if (r.get('created_timestamp') or 0) < p.get('_r0', r0): continue
            if r['id'] in answered or r['id'] in done: continue
            # 舊貼文的留言：我們可能是很早以前接的、不在翻到的那幾頁，再看一次這則留言底下有沒有我們
            if p.get('_r0') == ro and any((x.get('author') or {}).get('screen_name', '').lower() == HANDLE.lower() and parent_of(x) == r['id']
                                          for x in conv.get('replies') or []): continue
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
    print(f'我們最近 {a.since_hours:g} 小時的貼文（最近 {a.reply_hours:g} 小時的留言）＋{a.orig_days:g} 天內原創和置頂文（最近 {a.orig_reply_hours:g} 小時的留言），共 {len(ours)} 則貼文，有 {len(out)} 則還沒接的留言\n')
    for i, o in enumerate(out, 1):
        tag = '原創底下' if o['is_original'] else f'我們已回 {o["our_rounds"]} 輪'
        print(f'#{i} @{o["author"]}（{o["followers"] or 0:,} 粉{"，藍勾" if o["verified"] else ""}）{o["posted"]}  {tag}  {o["url"]}')
        print('   他：' + (o['text'] or '').replace('\n', ' ')[:200])
        print('   我們：' + (o['our_text'] or '').replace('\n', ' ')[:120])
    if olds_fail:
        print(f'\n⚠ {olds_fail}：{a.orig_days:g} 天內更早的原創底下沒掃到，請重跑一次，或在瀏覽器打開 https://x.com/notifications/mentions 補看')
    if gaps:
        print(f'\n⚠ 這 {len(gaps)} 則 fxtwitter 可能漏了留言，請在瀏覽器打開看底下有沒有還沒接的（或看 https://x.com/notifications/mentions）：')
        for p, why in gaps:
            print(f'   https://x.com/{HANDLE}/status/{p["id"]}  {why}  ' + (p.get('text') or '').replace('\n', ' ')[:60])


if __name__ == '__main__':
    main()
