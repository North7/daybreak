#!/usr/bin/env python3
"""連結預覽卡（2026-10-13）：網址貼到 X、Telegram 等處自動顯示的 1200x630 圖，由 index.html 的 og:image／twitter:image 指向。
預設英文版 assets/og-en.png；中文版 assets/og.png 保留，給中文場合用。
2026-11-12 重畫（使用者：預覽圖還是舊的淺色版、寫著「破曉」，要和現在的同步）：
  - 顏色和每日分享圖同一套深色「破曉漸層」（share_card.py 的 PAPER…，改那邊這裡會跟著變），右下角是放大的 logo（地平線上的日出）。
  - 品牌名中英文都只寫 DAYBREAK；副標列的是新版首頁的幾個分頁（週期、價位、賣壓、買盤、槓桿），不寫出場框架（X 上只放資訊）。
  - X 會把標題疊在圖的左下角，所以左下 150px 不放字。
  - 改了圖要把 index.html／classic.html 裡 og:image 後面的 ?v= 換掉，X 才會重抓。
字型與分享圖相同，由 --fonts 指定。用法：python3 pipeline/og_card.py --fonts <字型資料夾>"""
import os, argparse
from PIL import Image, ImageDraw
from share_card import fonts, PAPER, PAPER_BOTTOM, INK, INK3, RED, DOT, DOT_STEP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, M, SS = 1200, 630, 72, 2   # SS：放大兩倍畫再縮回來，弧線才不會有鋸齒
URL = 'daybreak.aronlab.dev'
TXT = {
    'en': dict(tag='The first Bitcoin brief of the morning', tabs='CYCLE · LEVELS · SELL PRESSURE · DEMAND · LEVERAGE', when=[('Every morning, 08:30 Taipei · English / ', 'mono'), ('中文', 'cjk')]),
    'zh': dict(tag='每天清晨的第一份比特幣簡報', tabs='週期 · 價位 · 賣壓 · 買盤 · 槓桿', when=[('每天早上 ', 'cjk'), ('08:30', 'mono'), ('（台北）· 中文 / ', 'cjk'), ('English', 'mono')]),
}


def card(lang, F, out):
    T = TXT[lang]; img = Image.new('RGB', (W * SS, H * SS), PAPER); d = ImageDraw.Draw(img)
    t, b = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in (PAPER, PAPER_BOTTOM))
    for y in range(H * SS):   # 破曉漸層：由上往下
        f = y / (H * SS - 1); d.line([(0, y), (W * SS, y)], fill=tuple(round(t[j] + (b[j] - t[j]) * f) for j in range(3)))
    for gy in range(DOT_STEP // 2, H, DOT_STEP):   # 網點底紋
        for gx in range(DOT_STEP // 2, W, DOT_STEP): d.ellipse([(gx - 1) * SS, (gy - 1) * SS, (gx + 1) * SS, (gy + 1) * SS], fill=DOT)
    cx, cy, r, sw = 968, 556, 180, 28   # 放大的 logo：弧是太陽，橫線是地平線，一路畫到右邊界
    d.arc([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], 180, 360, fill=RED, width=sw * SS)
    d.rectangle([(cx - r - 120) * SS, (cy - sw / 2) * SS, W * SS, (cy + sw / 2) * SS], fill=INK)
    fz = lambda kind, size, *a: F[kind](size * SS, *a)
    put = lambda x, y, s, font, fill: d.text((x * SS, y * SS), s, font=font, fill=fill, anchor='ls')
    put(M, 96, URL, fz('mono', 22), INK3)
    put(M - 6, 262, 'DAYBREAK', fz('num', 168), INK)
    if lang == 'en': put(M, 346, T['tag'], fz('num', 54), INK); put(M, 404, T['tabs'], fz('mono', 23), INK3)
    else: put(M, 346, T['tag'], fz('head', 50), INK); put(M, 404, T['tabs'], fz('cjk', 24, 500), INK3)
    x = M
    for s, kind in T['when']:
        ft = fz('cjk', 23, 500) if kind == 'cjk' else fz('mono', 23); put(x, 442, s, ft, INK3); x += ft.getlength(s) / SS
    img.resize((W, H), Image.LANCZOS).save(out, optimize=True); print('wrote', out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--fonts', required=True); a = ap.parse_args()
    F = fonts(a.fonts)
    card('en', F, os.path.join(ROOT, 'assets', 'og-en.png'))
    card('zh', F, os.path.join(ROOT, 'assets', 'og.png'))
