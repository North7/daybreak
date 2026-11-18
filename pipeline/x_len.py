#!/usr/bin/env python3
"""檢查 data/x_post.json 的中英文貼文是否在 X 的 280 加權字元內（2026-10-13 建立）。
X 的算法：中日韓字與全形符號算 2、其他字元算 1、網址一律算 23。
用法（在倉庫根目錄）：python3 pipeline/x_len.py   # 空白才以非零結束
2026-11-18 起日報正文＝當期 summary（使用者：「日報配圖已經是頭版標題，文字就可以改為下面的詳細說明那段」），常超過 280，用 X 的長貼文發：超過只提醒"""
import json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = re.compile(r'https?://\S+')

def weight(text):
    n = 23 * len(URL.findall(text)); text = URL.sub('', text)
    return n + sum(2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1 for ch in text)

if __name__ == '__main__':
    post = json.load(open(os.path.join(ROOT, 'data', 'x_post.json')))
    bad = False
    for k in ('zh', 'en'):
        w = weight(post.get(k, '')); bad |= not post.get(k)
        print(f'{k}: {w}/280' + ('  空白' if not post.get(k) else '  超過 280：用長貼文發' if w > 280 else ''))
    sys.exit(1 if bad else 0)
