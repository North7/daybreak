"""長貼文配圖：把幾張（已標註的）網站圖表截圖疊成一張直式圖，每張上方標紅色「圖1、圖2…」，對應內文；底部破曉頁尾。
一則貼文用一張合成圖：X 的多圖格子會把橫式圖裁掉（2 張並排每格約 7:8），單張圖在時間軸上完整顯示。
usage（倉庫根目錄）: python3 ops/post/longpost_img.py <輸出.png> <字型資料夾> <圖1.png> [<圖2.png> ...]"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pipeline'))
from PIL import Image, ImageDraw
import share_card as SC

out, fonts, *panels = sys.argv[1:]
Fn = SC.fonts(fonts); RED, INK, INK3, LINE = '#FF3B1F', '#F2F0EA', '#9C978E', '#3A3936'
ims = [Image.open(p).convert('RGB') for p in panels]
bg = ims[0].getpixel((ims[0].width // 2, 30))
P, TAG, GAP, TOP, FOOT = 72, 60, 64, 56, 140
if len(ims) == 1: TAG = -14   # 2026-11-06：只有一張圖（短貼文）就不標「圖1」
W = max(i.width for i in ims) + 2 * P
H = TOP + sum(TAG + 14 + i.height for i in ims) + GAP * (len(ims) - 1) + 40 + FOOT
img = Image.new('RGB', (W, H), bg); d = ImageDraw.Draw(img)
y = TOP; tf = Fn['cjk'](34, 900)
for n, im in enumerate(ims, 1):
    if len(ims) > 1:
        t = f'圖{n}'; tw = d.textlength(t, font=tf)
        d.rounded_rectangle([P, y, P + tw + 40, y + TAG], radius=TAG / 2, fill=RED)
        d.text((P + 20 + tw / 2, y + TAG / 2), t, font=tf, fill='#FFFFFF', anchor='mm')
    y += TAG + 14; img.paste(im, (P, y)); y += im.height + GAP
fy = H - 70; d.line([P, fy - 52, W - P, fy - 52], fill=LINE, width=2)
d.arc([P, fy - 26, P + 52, fy + 26], 180, 360, fill=RED, width=8); d.line([P - 8, fy, P + 60, fy], fill=INK, width=8)
d.text((P + 84, fy), '破曉 DAYBREAK', font=Fn['cjk'](38, 900), fill=INK, anchor='lm')
d.text((W - P, fy), 'X @songpu717', font=Fn['mono'](34), fill=INK3, anchor='rm')
img.resize((W // 2, H // 2), Image.LANCZOS).save(out, optimize=True); print('wrote', out, (W // 2, H // 2), round(W / H, 2))
