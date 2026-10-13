#!/usr/bin/env python3
"""連結預覽卡（2026-10-13）：網址貼到 X、Telegram 等處自動顯示的 1200x630 圖，由 index.html 的 og:image／twitter:image 指向。
預設英文版 assets/og-en.png（DAYBREAK 為主、破曉為副）；中文版 assets/og.png 保留（破曉為主），給中文場合用。
字型與分享圖相同，由 --fonts 指定。用法：python3 pipeline/og_card.py --fonts <字型資料夾>"""
import os, argparse
from PIL import Image, ImageDraw
from share_card import fonts, PAPER, INK, INK3, RED

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1200, 630

def logo(d, cx=180, y=215):
    d.arc([cx - 50, y - 50, cx + 50, y + 50], 180, 360, fill=RED, width=14)
    d.rectangle([cx - 80, y - 6, cx + 78, y + 6], fill=INK)

def en(F, out):
    img = Image.new('RGB', (W, H), '#F1F0EC'); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 14], fill=RED); logo(d)
    d.text((300, 215), 'DAYBREAK', font=F['num'](150), fill=INK, anchor='ls')
    d.text((304, 300), '破曉', font=F['head'](56), fill=INK, anchor='ls')
    d.text((90, 470), 'The first Bitcoin brief of the morning', font=F['num'](52), fill=INK, anchor='ls')
    d.text((90, 520), 'Cycle stage · market data · ETF flows · staged exit framework', font=F['mono'](24), fill=INK3, anchor='ls')
    d.text((90, 556), '每天清晨的第一份比特幣簡報・中文 / English', font=F['cjk'](24, 500), fill=INK3, anchor='ls')
    img.save(out, optimize=True); print('wrote', out)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--fonts', required=True); a = ap.parse_args()
    en(fonts(a.fonts), os.path.join(ROOT, 'assets', 'og-en.png'))
