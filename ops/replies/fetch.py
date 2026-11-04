#!/usr/bin/env python3
"""讀 X 原文（2026-11-04 建立）：從參數裡的網址、貼文 ID 或檔案（例如 Grok 給的表格 CSV）找出所有貼文，
經 api.fxtwitter.com（公開、不需登入）讀原文，印出帳號、粉絲、發文時間、實際語言、互動數與全文。
寫回覆前先跑這個，核對 Grok 的摘要、語言和粉絲數（Grok 常標錯）。
用法（在倉庫根目錄）：python3 ops/replies/fetch.py ~/Downloads/table.csv
                      python3 ops/replies/fetch.py https://x.com/<帳號>/status/<ID> ..."""
import json, os, re, sys, urllib.request

ID = re.compile(r'(?:x|twitter)\.com/(\w+)/status/(\d+)')


def targets(args):
    out = []
    for a in args:
        text = open(os.path.expanduser(a), encoding='utf-8').read() if os.path.exists(os.path.expanduser(a)) else a
        found = [i for _, i in ID.findall(text)] or ([a] if a.isdigit() else [])
        for i in found:
            if i not in out: out.append(i)
    return out


def get(i):
    req = urllib.request.Request(f'https://api.fxtwitter.com/status/{i}', headers={'User-Agent': 'daybreak-replies'})
    return json.load(urllib.request.urlopen(req, timeout=20)).get('tweet') or {}


if __name__ == '__main__':
    ids = targets(sys.argv[1:])
    if not ids: sys.exit('沒有找到貼文網址或 ID')
    for n, i in enumerate(ids, 1):
        try: t = get(i)
        except Exception as e: print(f'#{n} {i}: 讀取失敗 {e}\n'); continue
        a = t.get('author') or {}
        blue = '藍勾' if (a.get('verification') or {}).get('verified') else '非藍勾'
        print(f'#{n} @{a.get("screen_name")}（{a.get("followers"):,} 粉，{blue}）{t.get("created_at")}  語言={t.get("lang")}  '
              f'讚 {t.get("likes")} / 回覆 {t.get("replies")} / 轉推 {t.get("retweets")} / 瀏覽 {t.get("views")}  {t.get("url")}')
        print(t.get('text', ''))
        q = t.get('quote')
        if q: print(f'  〔引用 @{(q.get("author") or {}).get("screen_name")}〕{q.get("text", "")[:300]}')
        print()
