# -*- coding: utf-8 -*-
"""運營配圖的自動清理（2026-11-15 使用者：「基本 3 天之前的圖都不需要存」「新聞數據都是有即時性的，過期了意義不太大」）。
清 data/replies/ 和 data/longposts/ 裡超過 KEEP 天的圖，每日資料流程（daily.yml）提交前跑一次。
  日期：長文圖用檔名開頭的日期（2026-11-14-xxx.png）；回覆圖的檔名是編號、每天會重複用，所以記在 data/img_seen.json：
        每張圖第一次出現（或內容換了）的那天。每日流程只抓最新一版、沒有歷史，所以要自己記。
  保留：KEEP 天內的圖；長文清單（data/longposts.json）裡還沒發出去（沒有 posted）的長文用到的圖。
只刪目前的檔案；git 歷史裡還找得到（要讓程式庫真的變小得改寫歷史，使用者還沒決定）。
用法：python3 pipeline/prune_images.py [--dry] [--seed-from-git]
  --seed-from-git：第一次用，從 git 歷史補每張回覆圖最後一次被改的日期（之後每日流程不需要）。"""
import datetime as dt, hashlib, json, os, re, subprocess, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
DIRS = ('data/replies', 'data/longposts')
EXT = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
SEEN = 'data/img_seen.json'
KEEP = 3
TPE = dt.timezone(dt.timedelta(hours=8))


def today():
    return dt.datetime.now(TPE).date()


def sha(p):
    return hashlib.sha1(open(os.path.join(REPO, p), 'rb').read()).hexdigest()[:10]


def git_date(p):
    out = subprocess.run(['git', 'log', '-1', '--format=%cI', '--', p], cwd=REPO, capture_output=True, text=True).stdout.strip()
    return dt.datetime.fromisoformat(out).astimezone(TPE).date().isoformat() if out else None


def main(dry=False, seed=False):
    t = today(); cut = (t - dt.timedelta(days=KEEP)).isoformat()
    sp = os.path.join(REPO, SEEN)
    seen = json.load(open(sp, encoding='utf-8')) if os.path.exists(sp) else {}
    keep = set()
    try:   # 還沒發出去的長文：圖一定留著
        L = json.load(open(os.path.join(REPO, 'data', 'longposts.json'), encoding='utf-8'))
        for x in L.get('items') or []:
            if not x.get('posted'): keep.update(re.findall(r'data/longposts/[\w.\-]+', json.dumps(x, ensure_ascii=False)))
    except Exception as e:
        print('longposts.json 讀不到，只照日期清：', e)
    files = sorted(os.path.join(d, f) for d in DIRS if os.path.isdir(os.path.join(REPO, d)) for f in os.listdir(os.path.join(REPO, d)) if f.lower().endswith(EXT))
    gone, kept, new = [], 0, {}
    for p in files:
        h = sha(p); m = re.match(r'(\d{4}-\d{2}-\d{2})', os.path.basename(p))
        if m: day = m.group(1)
        elif p in seen and seen[p][0] == h: day = seen[p][1]
        else: day = (git_date(p) if seed else None) or t.isoformat()
        if day < cut and p not in keep:
            gone.append((p, day))
            if not dry: os.remove(os.path.join(REPO, p))
        else:
            kept += 1
            if not m: new[p] = [h, day]
    if not dry:
        with open(sp, 'w', encoding='utf-8') as f: f.write('{\n' + ',\n'.join('%s: %s' % (json.dumps(k), json.dumps(v)) for k, v in sorted(new.items())) + '\n}\n')   # 一張圖一行，每日的 diff 好讀
    print('prune_images：今天 %s，保留 %s 以後的圖；刪 %d 張、留 %d 張%s' % (t, cut, len(gone), kept, '（試跑，沒有刪）' if dry else ''))
    for p, d in gone: print('  -', p, d)
    return gone


if __name__ == '__main__':
    main(dry='--dry' in sys.argv, seed='--seed-from-git' in sys.argv)
