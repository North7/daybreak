"""破曉 No.015（10/20）直式短影片：1080×1920、30fps，Pillow 逐格繪製後交給 ffmpeg 編碼。
用法：python make_short_015.py <repo> <fonts> <out.mp4> [--frames 秒,秒,...]"""
import json, math, os, subprocess, sys, datetime as D
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

REPO, FONTS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
W, H, FPS = 1080, 1920, 30
M = 84
PAPER, INK, INK2, INK3, LINE = '#EEECE6', '#0A0A0A', '#3A3833', '#7A766F', '#D2CEC4'
RED, UP, DOWN, DECK = '#FF3B1F', '#00805A', '#D7261C', '#F6F5F1'


# ---------- fonts / colours ----------
@lru_cache(None)
def _font(name, size, axes):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    f.set_variation_by_axes(list(axes))
    return f

cjk = lambda s, w=700: _font('NotoSansTC[wght].ttf', int(s), (w,))
num = lambda s, w=900, wd=62: _font('Archivo[wdth,wght].ttf', int(s), (w, wd))
mono = lambda s, w=500: _font('JetBrainsMono[wght].ttf', int(s), (w,))

def rgb(c):
    c = c.lstrip('#'); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))

def mix(c, a, bg=PAPER):
    """把顏色 c 以透明度 a 疊在單色底 bg 上（背景都是平塗，用混色代替 alpha）。"""
    a = max(0.0, min(1.0, a)); c1, c0 = rgb(c), rgb(bg)
    return tuple(round(c0[i] + (c1[i] - c0[i]) * a) for i in range(3))

# ---------- easing ----------
clamp = lambda x: max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3
def back(x):
    x = clamp(x); c = 1.6; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def ph(t, start, dur=0.45): return ease((t - start) / dur)

def runs(d, x, y, parts, a=1.0, bg=PAPER, anchor='ls'):
    """依基線排一行混合字型文字；parts = [(文字, 字型, 顏色)]。回傳結束 x。"""
    if a <= 0.01: return x
    if anchor[0] in 'mr':
        tw = sum(f.getlength(s) for s, f, _ in parts)
        x -= tw / 2 if anchor[0] == 'm' else tw
    for s, f, c in parts:
        d.text((x, y), s, font=f, fill=mix(c, a, bg), anchor='ls'); x += f.getlength(s)
    return x


# ---------- data ----------
L = json.load(open(os.path.join(REPO, 'data', 'latest.json')))
N = json.load(open(os.path.join(REPO, 'data', 'notes.json')))
ETF = json.load(open(os.path.join(REPO, 'data', 'etf.json')))['rows'][-12:]
HIST = json.load(open(os.path.join(REPO, 'data', 'history', 'index.json')))
day = lambda s: (D.date.fromisoformat(s) - D.date(1970, 1, 1)).days
first_daily = day(HIST[0]['date'])
SERIES = [(a, b) for a, b in L['price']['history'] if day('2026-04-01') <= a < first_daily]
SERIES += [(day(r['date']), r['close']) for r in HIST]
bar = L['price']['bar']
CLOSE, CHG = bar['c'], bar['chg_pct']
PREV = CLOSE / (1 + CHG / 100)
SMA200 = L['price']['ma']['sma200']
assert N['date'] == '2026-10-20' and N['edition'] == 15, '腳本文字是為 No.015 寫的'


# ---------- persistent chrome ----------
def logo(d, cx, base, s, rise=1.0, a=1.0):
    r = 14 * s; lw = max(3, round(5 * s * 0.9))
    off = (1 - rise) * r * 1.2
    d.arc([cx - r, base - r + off, cx + r, base + r + off], 180, 360, fill=mix(RED, a), width=lw)
    if off: d.rectangle([cx - r - lw, base, cx + r + lw, base + 2 * r + lw], fill=rgb(PAPER))  # 地平線以下遮掉，像日出
    d.rectangle([cx - 26 * s, base - lw / 2, cx + 26 * s, base + lw / 2], fill=mix(INK, a))

def chrome(d, T, total):
    d.rectangle([0, 0, W * T / total, 8], fill=rgb(RED))
    logo(d, M + 26, 132, 1.0)
    d.text((M + 70, 132), '破曉 DAYBREAK', font=cjk(38, 900), fill=rgb(INK), anchor='lm')
    d.text((W - M, 132), 'No.015 · 2026/10/20', font=mono(28, 600), fill=rgb(INK3), anchor='rm')
    d.rectangle([M, 188, W - M, 192], fill=rgb(INK))

def kicker(d, t, y, text, color=RED):
    a = ph(t, 0.05, 0.35)
    f = cjk(36, 900); tw = f.getlength(text)
    if a > 0: d.rectangle([M, y, M + (tw + 36) * a, y + 58], fill=mix(color, 1))
    if a > 0.6: d.text((M + 18, y + 29), text, font=f, fill=mix('#FFFFFF', (a - .6) / .4, color), anchor='lm')

def headline(d, t, y, text, start=0.15, size=92):
    a = ph(t, start); runs(d, M, y + (1 - a) * 40, [(text, cjk(size, 900), INK)], a)


# ---------- scenes ----------
def s_hook(d, t):
    kicker(d, t, 250, '號外 · 10/20 日報')
    y = 470
    for i, line in enumerate(['比特幣現貨 ETF', '一天淨流入']):
        a = ph(t, 0.15 + i * 0.22); runs(d, M, y + i * 150 + (1 - a) * 50, [(line, cjk(122, 900), INK)], a)
    a = ph(t, 0.6, 0.5); v = 5.27 * ease((t - 0.6) / 1.1)
    yy = 850 + 230
    runs(d, M, yy + (1 - a) * 50, [(f'{v:.2f}', num(300), RED), (' 億美元', cjk(110, 900), INK)], a)
    a = ph(t, 1.9)
    d.rectangle([M, 1190, M + 12, 1390], fill=mix(RED, a))
    runs(d, M + 44, 1262, [('9/22 以來最大單日', cjk(58, 900), INK)], a)
    runs(d, M + 44, 1350, [('幾乎全靠 IBIT 一檔：', cjk(50, 700), INK2), ('+6.65 億', cjk(50, 900), UP)], a)
    a = ph(t, 2.5)
    runs(d, M, 1480, [('10/19 暫定值（Farside、SoSoValue 兩來源一致）', cjk(32, 500), INK3)], a)


def s_price(d, t, img):
    kicker(d, t, 250, 'BTC 週二收盤（10/20）')
    k = ease((t - 0.1) / 1.2); v = PREV + (CLOSE - PREV) * k
    a = ph(t, 0.1)
    runs(d, M - 6, 590 + (1 - a) * 40, [(f'{v:,.0f}', num(270), INK)], a)
    runs(d, M, 705, [(f'+{CHG:.2f}%', num(72), UP), ('  盤中探 81,100 後收高，收在當日區間 82% 處', cjk(32, 500), INK2)], ph(t, 0.6))

    # 價格線：2x 超取樣後縮小，線條才平滑
    X0, Y0, CW, CH = M, 770, W - 2 * M, 580
    S = 2; layer = Image.new('RGBA', (CW * S, CH * S), (0, 0, 0, 0)); g = ImageDraw.Draw(layer)
    xs = [p[0] for p in SERIES]; ys = [p[1] for p in SERIES]
    lo, hi = 54000, 96000
    px = lambda x: (x - xs[0]) / (xs[-1] - xs[0]) * (CW - 150) * S
    py = lambda y: (1 - (y - lo) / (hi - lo)) * CH * S
    for gy in (60000, 70000, 80000, 90000):
        g.line([(0, py(gy)), (CW * S, py(gy))], fill=rgb(LINE) + (255,), width=2)
    # 200 日均線（今日值）虛線
    ya = ph(t, 1.6)
    if ya > 0:
        yy = py(SMA200)
        for x in range(0, int(CW * S * ya), 28): g.line([(x, yy), (x + 16, yy)], fill=rgb(INK3) + (255,), width=4)
    prog = ease((t - 0.3) / 1.8)
    n = max(2, int(len(SERIES) * prog) + 1)
    pts = [(px(x), py(y)) for x, y in SERIES[:n]]
    if prog < 1 and n < len(SERIES):  # 末端內插，讓線條平順地長出來
        f = len(SERIES) * prog - (n - 1)
        (x1, y1), (x2, y2) = SERIES[n - 1], SERIES[n]
        pts[-1] = (px(x1 + (x2 - x1) * f), py(y1 + (y2 - y1) * f)) if f > 0 else pts[-1]
    g.line(pts, fill=rgb(INK) + (255,), width=7, joint='curve')
    lx, ly = pts[-1]; g.ellipse([lx - 14, ly - 14, lx + 14, ly + 14], fill=rgb(RED) + (255,))
    img.alpha_composite(layer.resize((CW, CH), Image.LANCZOS), (X0, Y0))

    for gy in (60000, 70000, 80000, 90000):
        d.text((X0 + CW, Y0 + py(gy) / S), f'{gy // 1000}K', font=mono(24), fill=rgb(INK3), anchor='rm')
    if ya > 0:
        runs(d, X0 + CW - 90, Y0 + py(SMA200) / S + 42, [('200 日均線 72,649', cjk(30, 700), INK3)], ya, anchor='rs')
    a = ph(t, 1.3)
    lx, ly = px(day('2026-06-30')) / S + X0, py(58525) / S + Y0
    runs(d, lx, ly + 52, [('6/30 低點 58,525', cjk(30, 700), INK2)], a, anchor='ms')
    a = ph(t, 2.1)
    lx = px(xs[-1]) / S + X0
    runs(d, lx + 10, Y0 + py(91500) / S, [('6/30 起 +41.7%', cjk(34, 900), RED)], a, anchor='rs')

    a = ph(t, 2.6, 0.5)
    y = 1400 + (1 - a) * 30
    d.rounded_rectangle([M, y, W - M, y + 120], 18, fill=mix(INK, a))
    runs(d, M + 36, y + 78, [('市場階段', cjk(40, 500), '#B6B2AA'), ('  牛市・第 12 天', cjk(52, 900), '#FFFFFF')], a, bg=INK)
    runs(d, W - M - 36, y + 76, [('連 41 日站上 200 日線', cjk(30, 500), '#B6B2AA')], a, bg=INK, anchor='rs')


def s_etf(d, t):
    kicker(d, t, 250, '資金面 · 現貨 ETF')
    headline(d, t, 420, '大額流入回來了…', size=96)
    runs(d, M, 500, [('每日淨流量，億美元（10/02–10/19）', cjk(32, 500), INK3)], ph(t, 0.3))
    X0, BASE, CW = M, 900, W - 2 * M
    scale = 260 / 527
    bw = CW / len(ETF)
    d.line([(X0, BASE), (X0 + CW * ph(t, 0.2, 0.5), BASE)], fill=rgb(INK), width=3)
    for i, r in enumerate(ETF):
        last = i == len(ETF) - 1
        st = 0.4 + i * 0.07 + (0.35 if last else 0)
        k = back((t - st) / (0.6 if last else 0.4))
        h = r['musd'] * scale * max(0, k)
        x = X0 + i * bw + bw * 0.16
        col = RED if last else (UP if r['musd'] >= 0 else DOWN)
        y1, y2 = (BASE - h, BASE) if h >= 0 else (BASE, BASE - h)
        if abs(h) > 0.5: d.rectangle([x, y1, x + bw * 0.68, y2], fill=mix(col, 1 if last else 0.85))
        lab = D.date.fromisoformat(r['d']).strftime('%-m/%-d')
        if i % 2 == 1 or last:
            d.text((x + bw * 0.34, 1190), lab, font=mono(24, 600 if last else 400), fill=mix(RED if last else INK3, ph(t, st)), anchor='mm')
    a = ph(t, 1.6)
    if a > 0:
        x = X0 + (len(ETF) - 1) * bw + bw * 0.5
        runs(d, x + bw * 0.4, BASE - 260 - 24, [('+5.27', num(76), RED)], a, anchor='rs')
        runs(d, x + bw * 0.4, BASE - 260 - 108, [('暫定', cjk(28, 700), RED)], a, anchor='rs')

    a = ph(t, 2.4, 0.5); y = 1290 + (1 - a) * 30
    d.rectangle([M, y, W - M, y + 230], fill=mix(DECK, a), outline=mix(INK, a), width=3)
    runs(d, M + 36, y + 76, [('…但別急著說趨勢反轉', cjk(46, 900), INK)], a, bg=DECK)
    runs(d, M + 36, y + 146, [('近 7 個完整交易日仍是 ', cjk(36, 500), INK2), ('−4.51 億', cjk(36, 900), DOWN)], a, bg=DECK)
    runs(d, M + 36, y + 200, [('Coinbase 溢價也還是負的，美國買盤偏弱', cjk(32, 500), INK3)], a, bg=DECK)


def s_deriv(d, t):
    kicker(d, t, 250, '衍生品')
    headline(d, t, 420, '價格收高，槓桿反而降溫', size=80)
    runs(d, M, 520, [('三家加權永續資金費率（年化）', cjk(34, 500), INK3)], ph(t, 0.3))
    a = ph(t, 0.4); k = ease((t - 0.7) / 1.0)
    runs(d, M, 700, [('9.77%', num(130, 700), INK3)], a)
    if k > 0:
        x2 = M + num(130, 700).getlength('9.77%')
        d.line([(M - 6, 655), (x2 + 6, 655)], fill=mix(INK3, a), width=6)
    v = 9.77 + (8.13 - 9.77) * k
    runs(d, M + 380, 700, [('→ ', cjk(90, 900), INK), (f'{v:.2f}%', num(190), UP)], a)
    rows = [('OKX', '8.99%', '6.02%'), ('Deribit', '7.46%', '2.99%'), ('Hyperliquid', '10.95%', '持平')]
    for i, (n, x0, x1) in enumerate(rows):
        a = ph(t, 1.2 + i * 0.15); y = 800 + i * 70
        runs(d, M, y, [(n, mono(34, 700), INK)], a)
        runs(d, W - M, y, [(x0, mono(34, 400), INK3), ('  →  ', mono(34, 400), INK3), (x1, mono(34, 700), UP) if x1 != '持平' else (x1, cjk(34, 700), INK)], a, anchor='rs')
        d.line([(M, y + 22), (W - M, y + 22)], fill=mix(LINE, a), width=2)

    a = ph(t, 2.2)
    runs(d, M, 1110, [('但選擇權仍在買下跌保護', cjk(52, 900), INK)], a)
    runs(d, M, 1180, [('30 天風險逆轉 ', cjk(36, 500), INK2), ('−3.3', num(50), DOWN), ('   DVOL 一年第 16 百分位', cjk(36, 500), INK2)], a)
    a = ph(t, 2.9, 0.5); y = 1270 + (1 - a) * 30
    d.rectangle([M, y, W - M, y + 180], fill=mix(RED, a))
    runs(d, M + 36, y + 76, [('解讀', cjk(32, 700), '#FFE3DC')], a, bg=RED)
    runs(d, M + 36, y + 142, [('這次是現貨走在槓桿前面', cjk(56, 900), '#FFFFFF')], a, bg=RED)


def s_exit(d, t):
    kicker(d, t, 250, '分批出場框架')
    headline(d, t, 410, '0 條觸發，也沒有接近', size=84)
    # 垂直價格尺：70K（下）到 130K（上）
    TOP, BOT, AX = 520, 1330, M + 200
    lo, hi = 68000, 130000
    py = lambda p: BOT - (p - lo) / (hi - lo) * (BOT - TOP)
    a = ph(t, 0.2, 0.6)
    d.line([(AX, BOT), (AX, BOT - (BOT - TOP) * a)], fill=rgb(INK), width=4)
    for p in range(70000, 131000, 10000):
        if py(p) >= BOT - (BOT - TOP) * a:
            d.line([(AX - 14, py(p)), (AX, py(p))], fill=rgb(INK), width=3)
            d.text((AX - 26, py(p)), f'{p // 1000}K', font=mono(26), fill=rgb(INK3), anchor='rm')
    cy = py(CLOSE)
    marks = [(125000, '出場第一階', '+50.7%', '收盤觸及即賣 12.5%', 0.9),
             (112203, 'MVRV 0.75 線', '+35.3%', '鏈上第一個賣出觸發', 1.2),
             (72649, '200 日均線', '−12.4%', '連 5 日收在其下才避險 20%', 1.5)]
    for p, name, pct, note, st in marks:
        k = ease((t - st) / 0.7); y = py(p)
        if k <= 0: continue
        # 從現價往目標拉出的距離線
        yy = cy + (y - cy) * k
        d.line([(AX + 30, cy), (AX + 30, yy)], fill=mix(INK3, k), width=3)
        d.line([(AX, y), (AX + 60, y)], fill=mix(INK, k), width=4)
        runs(d, AX + 84, y + 4, [(name, cjk(40, 900), INK), ('  ' + f'{p:,}', mono(30, 600), INK3)], k)
        runs(d, AX + 84, y + 56, [(pct, num(48), UP if pct[0] == '+' else DOWN), ('  ' + note, cjk(28, 500), INK2)], k)
    a = ph(t, 0.5)
    pulse = 1 + 0.25 * math.sin(t * 6) if t > 0.8 else 1
    r = 16 * pulse
    d.ellipse([AX - r, cy - r, AX + r, cy + r], fill=mix(RED, a))
    runs(d, AX + 52, cy + 14, [('◀ 現價 82,936', cjk(36, 900), RED)], a)

    a = ph(t, 2.6, 0.5); y = 1400 + (1 - a) * 30
    d.rectangle([M, y, W - M, y + 150], fill=mix(INK, a))
    runs(d, M + 36, y + 100, [('今天：', cjk(60, 700), '#B6B2AA'), ('不動', cjk(86, 900), '#FFFFFF')], a, bg=INK)
    runs(d, W - M - 36, y + 96, [('兩個動作點都很遠', cjk(32, 500), '#B6B2AA')], a, bg=INK, anchor='rs')


def s_cal(d, t):
    kicker(d, t, 250, '接下來要盯')
    headline(d, t, 420, '這幾個日期', size=96)
    items = [('10/23', '美國 10 月 PMI 初值', '台北 21:45'),
             ('10/29', 'FOMC 利率決議', '台北 02:00 · 多預期本月按兵不動'),
             ('10/30', 'Deribit 月度選擇權到期', '占未平倉 35.3%，最大痛點 78,000'),
             ('11/03', '美國期中選舉', '')]
    for i, (dt, lab, sub) in enumerate(items):
        a = ph(t, 0.4 + i * 0.3, 0.5); y = 560 + i * 210; x = M + (1 - a) * 60
        d.line([(M, y), (W - M, y)], fill=mix(INK, a), width=3)
        runs(d, x, y + 130, [(dt, num(110), RED)], a)
        runs(d, x + 300, y + 82, [(lab, cjk(46, 900), INK)], a)
        if sub: runs(d, x + 300, y + 142, [(sub, cjk(30, 500), INK3)], a)
    a = ph(t, 1.9)
    runs(d, M, 1440, [('眼前支撐：最密集價 82,750 · 50 日均線 81,568', cjk(32, 700), INK2)], a)


def s_outro(d, t):
    a = ph(t, 0.0, 0.5); rise = ease((t - 0.1) / 1.0)
    logo(d, W / 2, 760, 7.0, rise=rise, a=a)
    runs(d, W / 2, 960, [('破曉 DAYBREAK', cjk(104, 900), INK)], ph(t, 0.5), anchor='ms')
    runs(d, W / 2, 1050, [('每天清晨的第一份比特幣簡報', cjk(46, 700), INK2)], ph(t, 0.7), anchor='ms')
    a = ph(t, 1.0)
    d.rectangle([M + 60, 1130, W - M - 60, 1230], fill=mix(RED, a))
    runs(d, W / 2, 1197, [('daybreak.aronlab.dev', mono(42, 700), '#FFFFFF')], a, bg=RED, anchor='ms')
    runs(d, W / 2, 1300, [('完整解讀・中英雙語・每日更新', cjk(34, 500), INK3)], ph(t, 1.2), anchor='ms')
    runs(d, W / 2, 1460, [('資料整理，非投資建議', cjk(28, 500), INK3)], ph(t, 1.4), anchor='ms')


SCENES = [(s_hook, 4.4), (s_price, 5.6), (s_etf, 5.4), (s_deriv, 5.2), (s_exit, 5.8), (s_cal, 4.4), (s_outro, 3.6)]
XF = 0.3  # 場景交叉淡化秒數
# --audio <資料夾>：用 make_audio.py 產生的 timing.json 拉長場景以配合配音，並用 mix.wav 當音軌
AUDIO = sys.argv[sys.argv.index('--audio') + 1] if '--audio' in sys.argv else None
BASE = [d for _, d in SCENES]
if AUDIO:
    SCENES = [(fn, d) for (fn, _), d in zip(SCENES, json.load(open(os.path.join(AUDIO, 'timing.json')))['durs'])]
TOTAL = sum(d for _, d in SCENES)


def scene_img(i, t):
    fn, dur = SCENES[i]
    t *= BASE[i] / dur  # 場景被配音拉長時，入場動畫按比例放慢，跟上旁白
    img = Image.new('RGBA', (W, H), rgb(PAPER) + (255,)); d = ImageDraw.Draw(img)
    fn(d, t, img) if fn is s_price else fn(d, t)
    return img


def frame(T):
    start = 0
    for i, (_, dur) in enumerate(SCENES):
        if T < start + dur or i == len(SCENES) - 1: break
        start += dur
    t = T - start
    img = scene_img(i, t)
    if i + 1 < len(SCENES) and t > SCENES[i][1] - XF:
        k = (t - (SCENES[i][1] - XF)) / XF
        nxt = scene_img(i + 1, t - SCENES[i][1])  # 下一場景以負時間開始，入場動畫仍停在起點
        img = Image.blend(img, nxt, ease(k))
    d = ImageDraw.Draw(img); chrome(d, T, TOTAL)
    return img.convert('RGB')


if __name__ == '__main__':
    if '--frames' in sys.argv:
        for s in sys.argv[sys.argv.index('--frames') + 1].split(','):
            frame(float(s)).save(f'{OUT}_{s}.png')
        sys.exit()
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    n = int(TOTAL * FPS)
    p = subprocess.Popen([ff, '-y', '-loglevel', 'error',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          *(['-i', os.path.join(AUDIO, 'mix.wav'), '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '44100', '-ac', '2']
                            if AUDIO else ['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100']),
                          '-shortest', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
                          '-profile:v', 'high', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', OUT],
                         stdin=subprocess.PIPE)
    for f in range(n):
        p.stdin.write(frame(f / FPS).tobytes())
        if f % 150 == 0: print(f'{f}/{n}', flush=True)
    p.stdin.close(); p.wait()
    frame(SCENES[0][1] - 0.6).save(OUT.replace('.mp4', '-cover.png'))
    print('done', OUT, f'{TOTAL:.1f}s')
