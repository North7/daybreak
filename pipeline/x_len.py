#!/usr/bin/env python3
"""檢查 data/x_post.json 的中英文貼文是否在 X 的 280 加權字元內（2026-10-13 建立）。
X 的算法：中日韓字與全形符號算 2、其他字元算 1、網址一律算 23。
用法（在倉庫根目錄）：python3 pipeline/x_len.py   # 超過就以非零結束"""
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
        w = weight(post.get(k, '')); bad |= w > 280 or not post.get(k)
        print(f'{k}: {w}/280' + ('  超過或空白' if w > 280 or not post.get(k) else ''))
    sys.exit(1 if bad else 0)
