#!/usr/bin/env python3
"""長貼文臨時圖（2026-11-07〈期中選舉〉用）：網站上沒有的對照，照網站深色版型自己畫。
資料：pipeline/coc_cache/bitview.json 的每日收盤（Bitview，2011 起）；週期底取 latest.json 的 cycle.bottoms 日期。
usage（倉庫根目錄）: python3 ops/post/midterm_chart.py <輸出資料夾> <字型資料夾>
輸出：midterm-paths.png（四次期中選舉前後的走勢，以選舉日收盤為 0%）、midterm-bottoms.png（週期底離選舉日幾天）
只描述過去，不預測；樣本只有三次。"""
import datetime as dt, json, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import share_card as SC
from PIL import Image, ImageDraw

out, fonts = sys.argv[1:3]; os.makedirs(out, exist_ok=True); Fn = SC.fonts(fonts)
BG, PANEL, GRID, INK, INK3 = (12, 12, 13), (20, 19, 28), (44, 43, 50), '#F2F0EA', '#9C978E'
COL = {'2014': '#2BB39A', '2018': '#9C978E', '2022': '#8B7BF0', '2026': '#FF5A40'}
EL = {'2014': '2014-11-04', '2018': '2018-11-06', '2022': '2022-11-08', '2026': '2026-11-03'}
B = json.load(open(os.path.join(ROOT, 'pipeline', 'coc_cache', 'bitview.json')))
PX = {r[0]: r[1] for r in B['rows'] if r[1]}
L = json.load(open(os.path.join(ROOT, 'data', 'latest.json')))
BOT = {b[:4] if b[:4] != '2015' else '2014': b for b, _ in L['cycle']['bottoms']}   # 2015/01 的底屬於 2014 那次選舉
D = dt.date.fromisoformat
last = max(PX)


def series(y, lo=-180, hi=730):
    e = D(EL[y]); p0 = PX[EL[y]]; s = []
    for k in range(lo, hi + 1):
        day = (e + dt.timedelta(days=k)).isoformat()
        if day > last: break
        if day in PX: s.append((k, PX[day] / p0))
    return s, p0


def head(d, W, title, sub):
    d.text((0, 40), title, font=Fn['cjk'](52, 900), fill=INK, anchor='lt')
    d.text((W, 52), sub, font=Fn['cjk'](32, 500), fill=INK3, anchor='rt')


# ---- 圖：四次期中選舉前後 ----
W, H = 2280, 1100; img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
head(d, W - 40, '期中選舉前後的比特幣', 'Bitview 每日收盤 · 以選舉日收盤為 0% · 對數刻度')
lx = 0
for y in ('2014', '2018', '2022', '2026'):
    nm = '這次（2026）' if y == '2026' else y
    d.rectangle([lx, 150, lx + 48, 162], fill=COL[y]); lx += 62
    f = Fn['cjk'](34, 700); d.text((lx, 156), nm, font=f, fill=INK, anchor='lm'); lx += d.textlength(nm, font=f) + 44
x0, y0, x1, y1 = 60, 210, W - 170, H - 90
d.rectangle([x0, y0, x1, y1], fill=PANEL)
ka, kb = -180, 730; ra, rb = math.log10(0.45), math.log10(5.2)
X = lambda k: x0 + (k - ka) / (kb - ka) * (x1 - x0)
Y = lambda r: y1 - (math.log10(r) - ra) / (rb - ra) * (y1 - y0)
tf = Fn['mono'](32, 500)
for r, lab in ((0.5, '−50%'), (1, '0%'), (2, '+100%'), (4, '+300%')):
    d.line([x0, Y(r), x1, Y(r)], fill=GRID if r != 1 else (90, 88, 96), width=2)
    d.text((x1 + 16, Y(r)), lab, font=tf, fill=INK3, anchor='lm')
for k, lab in ((-180, '選前半年'), (0, '選舉日'), (365, '1 年後'), (730, '2 年後')):
    d.line([X(k), y1, X(k), y1 + 14], fill=INK3, width=2)
    d.text((X(k), y1 + 24), lab, font=Fn['cjk'](32, 500), fill=INK3, anchor='lt' if k == ka else 'rt' if k == kb else 'mt')
for yy in range(y0, y1, 22): d.line([X(0), yy, X(0), yy + 11], fill=(120, 118, 126), width=3)
for y in ('2014', '2018', '2022', '2026'):
    s, p0 = series(y); pts = [(X(k), Y(r)) for k, r in s]
    d.line(pts, fill=COL[y], width=10 if y == '2026' else 5, joint='curve')
    b = BOT[y]; kb_ = (D(b) - D(EL[y])).days; rb_ = PX[b] / p0
    bx, by = X(kb_), Y(rb_); r = 13 if y == '2026' else 10
    d.ellipse([bx - r, by - r, bx + r, by + r], fill=COL[y], outline='#FFFFFF', width=3)
    lab = '這次的底' if y == '2026' else '底'   # 細節放在下一張圖，這裡只標位置
    f = Fn['cjk'](32, 900); dy = 46
    d.text((bx, by + dy), lab, font=f, fill=COL[y], anchor='mt')
img.save(os.path.join(out, 'midterm-paths.png')); print('wrote midterm-paths.png')

# ---- 圖：週期底離選舉日幾天 ----
W, H = 2280, 760; img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
head(d, W - 40, '這輪的底，比選舉早到了', '週期底的日期 − 選舉日（天）')
cx = 1180; sc = 6.0; top = 190; rh = 118
d.line([cx, top - 20, cx, top + 4 * rh], fill=(120, 118, 126), width=4)
d.text((cx, top + 4 * rh + 20), '選舉日', font=Fn['cjk'](32, 700), fill=INK3, anchor='mt')
d.text((cx - 30, top - 30), '← 選前', font=Fn['cjk'](32, 500), fill=INK3, anchor='rb'); d.text((cx + 30, top - 30), '選後 →', font=Fn['cjk'](32, 500), fill=INK3, anchor='lb')
for i, y in enumerate(('2014', '2018', '2022', '2026')):
    s, p0 = series(y); b = BOT[y]; k = (D(b) - D(EL[y])).days; yc = top + i * rh + rh / 2
    d.text((60, yc), '這次 2026' if y == '2026' else f'{y} 期中', font=Fn['cjk'](40, 900), fill=COL[y] if y == '2026' else INK, anchor='lm')
    xa, xb = sorted((cx, cx + k * sc)); d.rounded_rectangle([xa, yc - 30, xb, yc + 30], radius=10, fill=COL[y])
    lab = f'{b.replace("-", "/")}　選前 {-k} 天' if k < 0 else f'{b.replace("-", "/")}　選後 {k} 天，再跌 {round((1 - PX[b] / p0) * 100)}%'
    f = Fn['cjk'](34, 700)
    if k < 0: d.text((xb - 24, yc), lab, font=f, fill='#FFFFFF', anchor='rm')
    else: d.text((xb + 24, yc), lab, font=f, fill=INK, anchor='lm')
img.save(os.path.join(out, 'midterm-bottoms.png')); print('wrote midterm-bottoms.png')
