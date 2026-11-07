"""破曉 No.016（10/21）直式短影片：1080×1920、30fps，Pillow 逐格繪製後交給 ffmpeg 編碼。
用法：python make_short_016.py <repo> <fonts> <out.mp4> [--frames 秒,秒,...]"""
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
assert N['date'] == '2026-10-21' and N['edition'] == 16, '腳本文字是為 No.016 寫的'


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
    d.text((W - M, 132), 'No.016 · 2026/10/21', font=mono(28, 600), fill=rgb(INK3), anchor='rm')
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
    kicker(d, t, 250, '號外 · 10/21 日報')
    for i, line in enumerate(['比特幣漲了，', '推它的卻是空頭']):
        a = ph(t, 0.15 + i * 0.22); runs(d, M, 470 + i * 150 + (1 - a) * 50, [(line, cjk(122, 900), INK)], a)
    a = ph(t, 0.55)
    runs(d, M, 790, [('空單一天被清算', cjk(56, 700), INK2)], a)
    a = ph(t, 0.6, 0.5); v = 1.88 * ease((t - 0.6) / 1.1)
    runs(d, M, 1080 + (1 - a) * 50, [(f'{v:.2f}', num(300), RED), (' 億美元', cjk(110, 900), INK)], a)
    a = ph(t, 1.9)
    d.rectangle([M, 1190, M + 12, 1390], fill=mix(RED, a))
    runs(d, M + 44, 1262, [('24 小時清算 2.43 億，空單占 77%', cjk(52, 900), INK)], a)
    runs(d, M + 44, 1350, [('上漲是', cjk(50, 700), INK2), ('空方被迫回補', cjk(50, 900), RED), ('，不是追價', cjk(50, 700), INK2)], a)
    a = ph(t, 2.5)
    runs(d, M, 1480, [('清算數據：CoinGlass，10/21', cjk(32, 500), INK3)], a)


def s_price(d, t, img):
    kicker(d, t, 250, 'BTC 週三收盤（10/21）')
    k = ease((t - 0.1) / 1.2); v = PREV + (CLOSE - PREV) * k
    a = ph(t, 0.1)
    runs(d, M - 6, 590 + (1 - a) * 40, [(f'{v:,.0f}', num(270), INK)], a)
    runs(d, M, 705, [(f'+{CHG:.2f}%', num(72), UP), ('  盤中衝上 84,840，站回 20 日均線', cjk(32, 500), INK2)], ph(t, 0.6))

    X0, Y0, CW, CH = M, 770, W - 2 * M, 580
    S = 2; layer = Image.new('RGBA', (CW * S, CH * S), (0, 0, 0, 0)); g = ImageDraw.Draw(layer)
    xs = [p[0] for p in SERIES]
    lo, hi = 54000, 96000
    px = lambda x: (x - xs[0]) / (xs[-1] - xs[0]) * (CW - 150) * S
    py = lambda y: (1 - (y - lo) / (hi - lo)) * CH * S
    for gy in (60000, 70000, 80000, 90000):
        g.line([(0, py(gy)), (CW * S, py(gy))], fill=rgb(LINE) + (255,), width=2)
    ya = ph(t, 1.6)
    if ya > 0:
        yy = py(SMA200)
        for x in range(0, int(CW * S * ya), 28): g.line([(x, yy), (x + 16, yy)], fill=rgb(INK3) + (255,), width=4)
    prog = ease((t - 0.3) / 1.8)
    n = max(2, int(len(SERIES) * prog) + 1)
    pts = [(px(x), py(y)) for x, y in SERIES[:n]]
    if prog < 1 and n < len(SERIES):
        f = len(SERIES) * prog - (n - 1)
        (x1, y1), (x2, y2) = SERIES[n - 1], SERIES[n]
        pts[-1] = (px(x1 + (x2 - x1) * f), py(y1 + (y2 - y1) * f)) if f > 0 else pts[-1]
    g.line(pts, fill=rgb(INK) + (255,), width=7, joint='curve')
    lx, ly = pts[-1]; g.ellipse([lx - 14, ly - 14, lx + 14, ly + 14], fill=rgb(RED) + (255,))
    img.alpha_composite(layer.resize((CW, CH), Image.LANCZOS), (X0, Y0))

    for gy in (60000, 70000, 80000, 90000):
        d.text((X0 + CW, Y0 + py(gy) / S), f'{gy // 1000}K', font=mono(24), fill=rgb(INK3), anchor='rm')
    if ya > 0:
        runs(d, X0 + CW - 90, Y0 + py(SMA200) / S + 42, [(f'200 日均線 {SMA200:,.0f}', cjk(30, 700), INK3)], ya, anchor='rs')
    a = ph(t, 1.3)
    lx, ly = px(day('2026-06-30')) / S + X0, py(58525) / S + Y0
    runs(d, lx, ly + 52, [('6/30 低點 58,525', cjk(30, 700), INK2)], a, anchor='ms')
    a = ph(t, 2.1)
    lx = px(xs[-1]) / S + X0
    runs(d, lx + 10, Y0 + py(91500) / S, [(f"6/30 起 +{L['price']['swing']['current']['pct']}%", cjk(34, 900), RED)], a, anchor='rs')

    a = ph(t, 2.6, 0.5)
    y = 1400 + (1 - a) * 30
    d.rounded_rectangle([M, y, W - M, y + 120], 18, fill=mix(INK, a))
    runs(d, M + 36, y + 78, [('市場階段', cjk(40, 500), '#B6B2AA'), ('  牛市・第 13 天', cjk(52, 900), '#FFFFFF')], a, bg=INK)
    runs(d, W - M - 36, y + 76, [('連 42 日站上 200 日線', cjk(30, 500), '#B6B2AA')], a, bg=INK, anchor='rs')


def s_deriv(d, t):
    kicker(d, t, 250, '衍生品')
    headline(d, t, 420, '價格在漲，費率反而翻負', size=80)
    runs(d, M, 520, [('三家加權永續資金費率（年化）', cjk(34, 500), INK3)], ph(t, 0.3))
    a = ph(t, 0.4); k = ease((t - 0.7) / 1.0)
    runs(d, M, 700, [('8.13%', num(130, 700), INK3)], a)
    if k > 0:
        x2 = M + num(130, 700).getlength('8.13%')
        d.line([(M - 6, 655), (x2 + 6, 655)], fill=mix(INK3, a), width=6)
    v = 8.13 + (-4.48 - 8.13) * k
    sign = '−' if v < 0 else ''
    runs(d, M + 310, 700, [('→ ', cjk(90, 900), INK), (f'{sign}{abs(v):.2f}%', num(165), DOWN if v < 0 else UP)], a)
    rows = [('OKX', '6.02%', '−5.17%'), ('Hyperliquid', '10.95%', '−5.06%'), ('Deribit', '2.99%', '0.02%')]
    for i, (n, x0, x1) in enumerate(rows):
        a = ph(t, 1.2 + i * 0.15); y = 800 + i * 70
        runs(d, M, y, [(n, mono(34, 700), INK)], a)
        runs(d, W - M, y, [(x0, mono(34, 400), INK3), ('  →  ', mono(34, 400), INK3), (x1, mono(34, 700), DOWN if x1[0] == '−' else INK)], a, anchor='rs')
        d.line([(M, y + 22), (W - M, y + 22)], fill=mix(LINE, a), width=2)

    a = ph(t, 2.2)
    runs(d, M, 1110, [('空方付費、被迫回補', cjk(52, 900), INK)], a)
    runs(d, M, 1180, [('費率回正之前，追價的槓桿很少', cjk(36, 500), INK2)], a)
    a = ph(t, 2.9, 0.5); y = 1270 + (1 - a) * 30
    d.rectangle([M, y, W - M, y + 180], fill=mix(RED, a))
    runs(d, M + 36, y + 76, [('解讀', cjk(32, 700), '#FFE3DC')], a, bg=RED)
    runs(d, M + 36, y + 142, [('這是軋空，不是槓桿追價', cjk(56, 900), '#FFFFFF')], a, bg=RED)


def s_etf(d, t):
    kicker(d, t, 250, '資金面 · 現貨 ETF')
    headline(d, t, 420, '近 7 日轉正，但…', size=96)
    runs(d, M, 500, [('每日淨流量，億美元（10/02–10/20）', cjk(32, 500), INK3)], ph(t, 0.3))
    X0, BASE, CW = M, 900, W - 2 * M
    scale = 260 / 527
    rows = ETF + [{'d': '2026-10-20', 'musd': 23.16, 'pending': True}]
    bw = CW / len(rows)
    d.line([(X0, BASE), (X0 + CW * ph(t, 0.2, 0.5), BASE)], fill=rgb(INK), width=3)
    for i, r in enumerate(rows):
        hero, pend = r['d'] == '2026-10-19', r.get('pending')
        st = 0.4 + i * 0.06 + (0.3 if hero else 0) + (0.5 if pend else 0)
        k = back((t - st) / (0.6 if hero else 0.4))
        h = r['musd'] * scale * max(0, k)
        x = X0 + i * bw + bw * 0.16
        col = UP if r['musd'] >= 0 else DOWN
        y1, y2 = (BASE - h, BASE) if h >= 0 else (BASE, BASE - h)
        if pend and k > 0:
            d.rectangle([x, y1 - 2, x + bw * 0.68, y2], outline=mix(INK3, 1), width=3)
        elif abs(h) > 0.5:
            d.rectangle([x, y1, x + bw * 0.68, y2], fill=mix(col, 1 if hero else 0.6))
        lab = D.date.fromisoformat(r['d']).strftime('%-m/%-d')
        if (i % 2 == 0 and i < len(rows) - 3) or hero:
            d.text((x + bw * 0.34, 1190), lab, font=mono(22, 600 if (hero or pend) else 400),
                   fill=mix(UP if hero else INK3, ph(t, st)), anchor='mm')
    a = ph(t, 1.5)
    hx = X0 + (len(rows) - 2) * bw + bw * 0.5
    runs(d, hx, BASE - 260 - 24, [('+5.27', num(72), UP)], a, anchor='ms')
    a = ph(t, 2.0)
    runs(d, X0 + CW, BASE + 86, [('10/20 約 0.23', cjk(30, 900), INK2)], a, anchor='rs')
    runs(d, X0 + CW, BASE + 124, [('單一來源，未計入', cjk(26, 500), INK3)], a, anchor='rs')

    a = ph(t, 2.4, 0.5); y = 1290 + (1 - a) * 30
    d.rectangle([M, y, W - M, y + 230], fill=mix(DECK, a), outline=mix(INK, a), width=3)
    runs(d, M + 36, y + 76, [('…轉正幾乎全靠 10/19 一天', cjk(46, 900), INK)], a, bg=DECK)
    runs(d, M + 36, y + 146, [('近 7 個完整交易日 ', cjk(36, 500), INK2), ('+3.19 億', cjk(36, 900), UP)], a, bg=DECK)
    runs(d, M + 36, y + 200, [('要連續流入，才算現貨買盤回來', cjk(32, 500), INK3)], a, bg=DECK)


def s_cal(d, t):
    kicker(d, t, 250, '接下來要盯')
    headline(d, t, 420, '一個價位、三個日期', size=88)
    items = [('84–86K', '上方賣壓帶', '約 115 萬顆籌碼＋84,000 賣牆'),
             ('10/23', '美國 10 月 PMI 初值', '台北 21:45'),
             ('10/29', 'FOMC 利率決議', '台北 02:00 · 本月升息機率約 15.5%'),
             ('10/30', 'Deribit 月度選擇權到期', '占未平倉 35.2%，最大痛點 78,000')]
    for i, (dt, lab, sub) in enumerate(items):
        a = ph(t, 0.4 + i * 0.3, 0.5); y = 560 + i * 210; x = M + (1 - a) * 60
        d.line([(M, y), (W - M, y)], fill=mix(INK, a), width=3)
        runs(d, x, y + 130, [(dt, num(96), RED)], a)
        runs(d, x + 320, y + 82, [(lab, cjk(46, 900), INK)], a)
        if sub: runs(d, x + 320, y + 142, [(sub, cjk(30, 500), INK3)], a)
    a = ph(t, 1.9)
    runs(d, M, 1440, [('下方支撐：83,000 買牆 · 最密集價 82,750', cjk(32, 700), INK2)], a)


def s_outro(d, t):
    a = ph(t, 0.0, 0.5); rise = ease((t - 0.1) / 1.0)
    logo(d, W / 2, 760, 7.0, rise=rise, a=a)
    runs(d, W / 2, 960, [('破曉 DAYBREAK', cjk(104, 900), INK)], ph(t, 0.5), anchor='ms')
    runs(d, W / 2, 1050, [('每天清晨的第一份比特幣簡報', cjk(46, 700), INK2)], ph(t, 0.7), anchor='ms')
    a = ph(t, 1.0)
    d.rectangle([M + 60, 1130, W - M - 60, 1230], fill=mix(RED, a))
    runs(d, W / 2, 1197, [('X @songpu717', mono(42, 700), '#FFFFFF')], a, bg=RED, anchor='ms')
    runs(d, W / 2, 1300, [('完整解讀・中英雙語・每日更新', cjk(34, 500), INK3)], ph(t, 1.2), anchor='ms')
    runs(d, W / 2, 1460, [('資料整理，非投資建議', cjk(28, 500), INK3)], ph(t, 1.4), anchor='ms')


# 出場框架屬策略，不放進短影片（只放資訊）
SCENES = [(s_hook, 4.4), (s_price, 5.2), (s_deriv, 5.4), (s_etf, 5.2), (s_cal, 4.6), (s_outro, 3.6)]
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
