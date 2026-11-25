# -*- coding: utf-8 -*-
"""IndexNow：網站部署好之後通知 Bing（ChatGPT 搜尋大量用 Bing 的索引）、Yandex、Seznam 等「這幾頁更新了」，不用等它們自己來抓。2026-11-20 GEO 第一批新增。
金鑰檔是根目錄的 f4af452c772ca762ae6ba9c8a566e5c5.txt（公開的，IndexNow 用它確認網站是我們的）。
只在每天日報上線後（cloudflare.yml 接在 Share cards 之後的那次部署）送一次；失敗只印出來，不影響部署。
用法：python3 pipeline/indexnow.py"""
import json, urllib.request

KEY = 'f4af452c772ca762ae6ba9c8a566e5c5'
HOST = 'daybreak.aronlab.dev'
URLS = ['/', '/app/', '/llms.txt', '/latest.md', '/latest.en.md', '/charts/', '/en/charts/', '/brief/', '/en/brief/']
# 2026-11-25 主題頁（pipeline/next/topics.py）：常見問題的答案每天跟著換
URLS += ['/%s%s/' % (l, h) for h in ('bitcoin-cycle', 'bitcoin-onchain', 'bitcoin-macro', 'bitcoin-derivatives') for l in ('', 'en/', 'zh-hans/')]
# 2026-11-20 GEO 第二批：當天的簡報頁（每張圖的頁每天也會變，但一次送 240 頁太多；它們靠 sitemap 和索引頁的連結被找到）
import os
try:   # 2026-11-21 當天的簡報頁用當期判讀（notes.json）的日期，封存要晚大半天才寫
    _n = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'notes.json'); _d = json.load(open(_n, encoding='utf-8'))['date']
    URLS += ['/brief/%s/' % _d, '/en/brief/%s/' % _d, '/feed.xml', '/en/feed.xml']
except Exception as e:
    print('indexnow: no notes date', e)

body = json.dumps({'host': HOST, 'key': KEY, 'keyLocation': 'https://%s/%s.txt' % (HOST, KEY), 'urlList': ['https://' + HOST + u for u in URLS]}).encode()
try:
    r = urllib.request.urlopen(urllib.request.Request('https://api.indexnow.org/indexnow', body, {'Content-Type': 'application/json; charset=utf-8', 'User-Agent': 'daybreak-indexnow'}), timeout=30)
    print('indexnow', r.status, len(URLS), 'urls')   # 200 收到，202 收到但金鑰還在驗證
except Exception as e:
    print('indexnow failed:', e)
