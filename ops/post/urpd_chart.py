"""籌碼分布（URPD）配圖：每 2,000 美元一格的直條圖，標出一段厚的、一段薄的，加現價線。2026-11-09 為英文長文〈50 週均線〉畫的，使用者說「這張圖做的很好看」，收進來重用。
讀 data/latest.json 的 chips.viz.urpd（Bitview）。深色、網站同字型，輸出 2280 寬，直接丟給 longpost_img.py。
usage（倉庫根目錄）: python3 ops/post/urpd_chart.py <輸出.png> <字型資料夾> [--zh] [--thick 76000 86000] [--thin 66000 74000] [--lo 50000] [--hi 126000]
  --thick／--thin 不給就只畫現價線；價格區間是左閉右開（76000 86000 = 76K 起到 86K 前，五格）。"""
import sys, os, json, argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pipeline')); import share_card as SC
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('fonts'); ap.add_argument('--zh', action='store_true')
ap.add_argument('--thick', nargs=2, type=int); ap.add_argument('--thin', nargs=2, type=int); ap.add_argument('--lo', type=int, default=50000); ap.add_argument('--hi', type=int, default=126000)
a = ap.parse_args(); Fn = SC.fonts(a.fonts); zh = a.zh
BG, PANEL, GRID, INK, INK3 = (12, 12, 13), (20, 19, 28), (44, 43, 50), '#F2F0EA', '#9C978E'
BAR, THICK, THIN, PX = '#4A4F7A', '#FF8A3D', '#2FBF8F', '#F2F0EA'
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
L = json.load(open(os.path.join(REPO, 'data', 'latest.json'), encoding='utf-8'))
u = L['chips']['viz']['urpd']; band = [(p, s) for p, s in u['band'] if a.lo <= p < a.hi]; price = u['price']
md = u['date'][5:].replace('-', '/')
W, H = 2280, 1160; img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
d.text((0, 36), '籌碼分布：幣是在哪個價位買的' if zh else 'Where the coins were bought: supply by cost basis', font=Fn['cjk'](50, 900), fill=INK, anchor='lt')
d.text((W - 10, 48), f'每 2,000 美元一格 · Bitview URPD · {md}' if zh else f'$2,000 buckets · Bitview URPD · {md}', font=Fn['mono' if not zh else 'cjk'](30, 500), fill=INK3, anchor='rt')
x0, y0, x1, y1 = 30, 130, W - 30, H - 30
d.rectangle([x0, y0, x1, y1], fill=PANEL)
left, right, top, bot = x0 + 150, x1 - 60, y0 + 40, y1 - 90
n = len(band); step = (right - left) / n; bw = step * 0.72
mx = max(s for _, s in band) * 1.42
Yv = lambda s: bot - s / mx * (bot - top)
for v in (250000, 500000, 750000, 1000000):
    if v > mx: break
    d.line([left, Yv(v), right, Yv(v)], fill=GRID, width=2)
    d.text((left - 16, Yv(v)), (f'{v // 10000} 萬' if zh else f'{v // 1000}K'), font=Fn['cjk' if zh else 'mono'](26, 500), fill=INK3, anchor='rm')
d.text((left - 16, top - 8), '顆' if zh else 'BTC', font=Fn['cjk' if zh else 'mono'](24, 500), fill=INK3, anchor='rb')
def inside(p, rg): return bool(rg) and rg[0] <= p < rg[1]
for k, (p, s) in enumerate(band):
    cx = left + step * (k + 0.5)
    col = THICK if inside(p, a.thick) else THIN if inside(p, a.thin) else BAR
    d.rounded_rectangle([cx - bw / 2, Yv(s), cx + bw / 2, bot], radius=5, fill=col)
    if p % 10000 == 0:
        d.text((cx - step / 2, bot + 18), (f'{p // 1000}K' if zh else f'${p // 1000}K'), font=Fn['mono'](26, 500), fill=INK3, anchor='mt')
        d.line([cx - step / 2, bot, cx - step / 2, bot + 10], fill=GRID, width=2)
cxp = left + (price - a.lo) / 2000 * step
d.line([cxp, top + 60, cxp, bot], fill=PX, width=3)
d.text((cxp - 10, top + 70), (f'週日收盤 {price / 1000:.1f}K' if zh else f'Sunday close ${price / 1000:.1f}K'), font=Fn['cjk'](28, 800), fill=PX, anchor='rm')
def tot(rg): return sum(s for p, s in band if inside(p, rg))
def callout(rg, text, col, dy=70):
    cx = left + ((rg[0] + rg[1]) / 2 - a.lo) / 2000 * step; peak = max(s for p, s in band if inside(p, rg))
    yy = Yv(peak) - dy; lf = Fn['cjk'](28, 800); tw = d.textlength(text, font=lf) + 30
    bx = max(left + tw / 2, min(right - tw / 2, cx))
    d.line([cx, Yv(peak) - 8, cx, yy + 22], fill=col, width=2)
    d.rounded_rectangle([bx - tw / 2, yy - 22, bx + tw / 2, yy + 22], radius=22, fill=col)
    d.text((bx, yy), text, font=lf, fill='#141414', anchor='mm')
def rng(rg): return f'{rg[0] // 1000}–{rg[1] // 1000}K'
if a.thick:
    t = tot(a.thick); callout(a.thick, (f'{rng(a.thick)}：{t / 1e4:.0f} 萬顆，整張圖最厚的一團' if zh else f'${rng(a.thick)}: {t / 1e6:.1f}M BTC, the thickest cluster on the map'), THICK)
if a.thin:
    t = tot(a.thin); callout(a.thin, (f'{rng(a.thin)}：只有 {t / 1e4:.0f} 萬顆，下面的薄區' if zh else f'${rng(a.thin)}: only {t / 1e6:.1f}M, the thin zone below'), THIN)
d.text((left, y1 - 14), ('每根柱子＝最後一次在鏈上移動是在那個價位的幣，也就是持有者的成本。厚的地方是等著回本的人，薄的地方價格走得快。' if zh else
        "Each bar = BTC whose last on-chain move was at that price, i.e. the holders' cost basis. Thick buckets: people waiting to get back to even. Thin ones: price moves fast."),
       font=Fn['cjk'](25, 500), fill=INK3, anchor='lb')
img.save(a.out); print('wrote', a.out, img.size)
