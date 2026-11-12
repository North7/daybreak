"""SPI（賣壓累積）直式短影片，YouTube Shorts／X 共用：1080×1920、30fps、深色，Pillow 逐格畫、ffmpeg 編碼。
數字全部讀 data/latest.json 的 chips.stress（本站自製指標，只作讀值）；旁白和字幕在 lines_spi.json。
用法：python make_short_spi.py <repo> <fonts> <out.mp4> [--audio <make_audio.py 的輸出資料夾>] [--frames 秒,秒,...]"""
import json, math, os, subprocess, sys, statistics as st, datetime as D
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

REPO, FONTS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
W, H, FPS, M = 1080, 1920, 30, 72
BG, PANEL, INK, INK2, INK3, LINE = '#0A0A0A', '#151517', '#F2F0EA', '#C9C5BC', '#8E897F', '#2A2927'
RED, GRN, CY, ORG = '#FF4D2E', '#C6F432', '#3FD4E8', '#FF8A3D'
CAP_Y = 1430          # 字幕基準線；Shorts 下方約 1/5 會被標題和按鈕蓋住，內容都放在這條線以上
RIGHT = W - 150       # 右側留給 Shorts 的按鈕


@lru_cache(None)
def _font(name, size, axes):
    f = ImageFont.truetype(os.path.join(FONTS, name), size); f.set_variation_by_axes(list(axes)); return f
cjk = lambda s, w=700: _font('NotoSansTC[wght].ttf', int(s), (w,))
num = lambda s, w=900, wd=62: _font('Archivo[wdth,wght].ttf', int(s), (w, wd))
mono = lambda s, w=500: _font('JetBrainsMono[wght].ttf', int(s), (w,))

def rgb(c): c = c.lstrip('#'); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
def mix(c, a, bg=BG):
    a = max(0.0, min(1.0, a)); c1, c0 = rgb(c), rgb(bg); return tuple(round(c0[i] + (c1[i] - c0[i]) * a) for i in range(3))
clamp = lambda x: max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3
def back(x): x = clamp(x); c = 1.6; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def ph(t, s, dur=0.45): return ease((t - s) / dur)

def runs(d, x, y, parts, a=1.0, bg=BG, anchor='ls'):
    if a <= 0.01: return x
    if anchor[0] in 'mr':
        tw = sum(f.getlength(s) for s, f, _ in parts); x -= tw / 2 if anchor[0] == 'm' else tw
    for s, f, c in parts:
        d.text((x, y), s, font=f, fill=mix(c, a, bg), anchor='ls'); x += f.getlength(s)
    return x


# ---------- data ----------
S = json.load(open(os.path.join(REPO, 'data', 'latest.json')))['chips']['stress']
EV = [e for e in S['ev'] if e['ret'] is not None]; CUR = [e for e in S['ev'] if e['ret'] is None][-1]
ROWS = S['rows']                                   # [日數, 收盤, 賣壓累積, 動能品質]
d2s = lambda n: D.date(1970, 1, 1) + D.timedelta(n)
s2d = lambda s: (D.date.fromisoformat(s) - D.date(1970, 1, 1)).days
WIN = sum(e['ret'] > 0 for e in EV); E23 = [e for e in EV if e['date'] >= '2023']
BIG = [e for e in EV if e['ret'] <= -10]
DIP10 = sum(e['dip'] <= -10 for e in EV); DIPMED = st.median(e['dip'] for e in EV)
assert len(EV) == 20 and WIN == 15 and all(e['ret'] > 0 for e in E23) and len(E23) == 6, '旁白寫死 20 次、15 次、2023 後 6/6'
assert [e['date'][:4] for e in BIG] == ['2014', '2022'] and S['f90']['med'] == 17.8 and S['base90']['med'] == 9.9
assert S['date'] == '2026-11-11' and S['r'] == 100 and S['at100'] == 2, '旁白寫的是 11/11 收盤 100、第 2 天'
L = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lines_spi.json')))


# ---------- chrome ----------
def logo(d, cx, cy, s=1.0, a=1.0, rise=1.0):
    r = 26 * s; lw = max(4, round(8 * s)); off = (1 - rise) * r * 1.3
    d.arc([cx - r, cy - r + off, cx + r, cy + r + off], 180, 360, fill=mix(RED, a), width=lw)
    if off: d.rectangle([cx - r - lw, cy + lw / 2, cx + r + lw, cy + 2 * r + lw * 2], fill=rgb(BG))
    d.line([(cx - r - 8 * s, cy), (cx + r + 8 * s, cy)], fill=mix(INK, a), width=lw)

def chrome(d, T, total):
    d.rectangle([0, 0, W * T / total, 8], fill=rgb(RED))
    logo(d, M + 26, 118, 0.85)
    d.text((M + 76, 118), 'DAYBREAK', font=cjk(36, 900), fill=rgb(INK), anchor='lm')
    d.text((W - M, 118), 'SPI · 賣壓累積', font=cjk(30, 700), fill=rgb(INK3), anchor='rm')
    d.line([(M, 168), (W - M, 168)], fill=rgb(LINE), width=2)

def kicker(d, t, y, text, color=RED):
    a = ph(t, 0.05, 0.35); f = cjk(34, 900); tw = f.getlength(text)
    if a > 0: d.rectangle([M, y, M + (tw + 36) * a, y + 56], fill=rgb(color))
    if a > 0.6: d.text((M + 18, y + 28), text, font=f, fill=mix('#0A0A0A', (a - .6) / .4, color), anchor='lm')

def headline(d, t, y, text, start=0.12, size=84, color=INK):
    a = ph(t, start); runs(d, M, y + (1 - a) * 36, [(text, cjk(size, 900), color)], a)


# ---------- scenes（t 是場景內秒數，以 base 長度設計） ----------
def s_hook(d, t, img):
    """開頭先把圖放出來：近一年價格＋SPI，標出今年三次滿格和現在的位置（YouTube 的人沒看過 X 上的圖）。"""
    kicker(d, t, 240, 'Daybreak 自製指標')
    a = ph(t, 0.0, 0.4); runs(d, M, 400 + (1 - a) * 30, [('賣壓滿格，是壞消息嗎？', cjk(84, 900), INK)], a)
    runs(d, M, 470, [('賣壓累積 SPI（0–100），2026 年到現在', cjk(34, 600), INK3)], ph(t, 0.3))
    rows = [r for r in ROWS if r[0] >= s2d('2026-01-01')]   # 只畫今年，跟「今年第 3 次」對得上
    x0, x1 = M, RIGHT - 10
    py0, py1, sy0, sy1 = 540, 820, 900, 1210
    lo, hi = min(r[1] for r in rows) * 0.96, max(r[1] for r in rows) * 1.03
    px = lambda n: x0 + (n - rows[0][0]) / (rows[-1][0] - rows[0][0]) * (x1 - x0)
    pp = lambda v: py1 - (v - lo) / (hi - lo) * (py1 - py0)
    ps = lambda v: sy1 - v / 100 * (sy1 - sy0)
    ga = ph(t, 0.4)
    for v in (0, 50, 100):
        y = ps(v); d.line([(x0, y), (x1, y)], fill=mix(LINE, ga), width=2)
        d.text((x1 + 8, y), str(v), font=mono(24), fill=mix(INK3, ga), anchor='lm')
    for k in range(0, int(x1 - x0), 22):
        d.line([(x0 + k, ps(100)), (x0 + k + 11, ps(100))], fill=mix(RED, ga * 0.8), width=3)
    for p_, lab in ((70000, '70K'), (90000, '90K'), (110000, '110K')):
        if lo < p_ < hi: d.text((x1 + 8, pp(p_)), lab, font=mono(22), fill=mix(INK3, ga), anchor='lm'); d.line([(x0, pp(p_)), (x1, pp(p_))], fill=mix(LINE, ga * 0.6), width=1)
    d.text((x0, py0 - 14), 'BTC 收盤', font=cjk(26, 700), fill=mix(INK3, ga), anchor='ls')
    d.text((x1 + 8, sy0 - 40), 'SPI', font=mono(24, 700), fill=mix(INK3, ga), anchor='lm')
    for mo in (1, 4, 7, 10):   # 月份
        d.text((px(s2d(f'2026-{mo:02d}-01')), sy1 + 30), f'{mo} 月', font=cjk(24, 600), fill=mix(INK3, ga), anchor='mm')
    k = ease((t - 0.6) / 2.4); n = max(2, int(len(rows) * k))
    S2 = 2; lay = Image.new('RGBA', (W * S2, H * S2), (0, 0, 0, 0)); g = ImageDraw.Draw(lay)
    g.line([(px(r[0]) * S2, pp(r[1]) * S2) for r in rows[:n]], fill=rgb(INK) + (255,), width=5, joint='curve')
    poly = [(px(rows[0][0]) * S2, sy1 * S2)] + [(px(r[0]) * S2, ps(r[2]) * S2) for r in rows[:n]] + [(px(rows[n - 1][0]) * S2, sy1 * S2)]
    g.polygon(poly, fill=rgb(RED) + (235,))
    img.alpha_composite(lay.resize((W, H), Image.LANCZOS))
    # 近一年的滿格日
    full = [e for e in S['ev'] if s2d(e['date']) >= rows[0][0]]
    for i, e in enumerate(full):
        nn = s2d(e['date']); cur = e['ret'] is None
        ka = ph(t, 0.6 + 2.4 * (nn - rows[0][0]) / (rows[-1][0] - rows[0][0]), 0.3)
        if ka <= 0: continue
        x, y = px(nn), ps(100)
        col = CY if cur else INK
        d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=mix(col, ka), outline=rgb(BG), width=3)
        d.ellipse([x - 7, pp(e['price']) - 7, x + 7, pp(e['price']) + 7], fill=mix(col, ka))
        dt = D.date.fromisoformat(e['date'])
        if not cur: d.text((x, y - 26), f'{dt.month}/{dt.day}', font=mono(24, 700), fill=mix(INK2, ka), anchor='ms')
    a = ph(t, 3.2, 0.4)
    if a > 0:
        x, y = px(s2d(CUR['date'])), ps(100)
        pul = 1 + 0.3 * math.sin(t * 6)
        d.ellipse([x - 20 * pul, y - 20 * pul, x + 20 * pul, y + 20 * pul], outline=mix(CY, a), width=3)
        d.rounded_rectangle([x - 300, y - 120, x - 30, y - 40], 14, fill=mix(CY, a))
        d.text((x - 165, y - 80), '現在：滿格 100', font=cjk(34, 900), fill=mix('#0A0A0A', a, CY), anchor='mm')
    a = ph(t, 4.0)
    runs(d, M, 1300, [('11/10 收盤到 100，今年第 3 次；11/11 還在 100', cjk(36, 700), INK2)], a)


def gauge(d, y, frac, col, a):
    d.rounded_rectangle([M, y, RIGHT, y + 64], 14, fill=mix(LINE, a))
    if frac > 0.005: d.rounded_rectangle([M, y, M + max(28, (RIGHT - M) * min(frac, 1)), y + 64], 14, fill=mix(col, a))

def s_what(d, t, img):
    kicker(d, t, 240, '它量什麼')
    headline(d, t, 410, '只看每天收盤，量兩件事', size=70)
    a = ph(t, 0.7)
    runs(d, M, 560, [('① 跌了多久', cjk(54, 900), ORG)], a)
    runs(d, M, 616, [('弱勢每多拖一天就加一點，大約兩週才滿', cjk(32, 500), INK3)], a)
    k = clamp((t - 1.0) / 2.6); g1 = math.floor(k * 14) / 14     # 一格一格往上加
    gauge(d, 650, g1, ORG, a)
    a = ph(t, 1.9)
    runs(d, M, 830, [('② 跌得多兇', cjk(54, 900), RED)], a)
    runs(d, M, 886, [('大跌那天，直接跳上去', cjk(32, 500), INK3)], a)
    g2 = 0.18 * back((t - 2.1) / 0.4) + 0.5 * back((t - 2.9) / 0.4) + 0.32 * back((t - 3.5) / 0.4)
    gauge(d, 920, g2, RED, a)
    a = ph(t, 4.3, 0.5); y = 1080 + (1 - a) * 30
    d.rounded_rectangle([M, y, RIGHT, y + 220], 18, fill=mix(PANEL, a), outline=mix(RED, a), width=3)
    runs(d, M + 36, y + 92, [('兩邊都滿 ', cjk(56, 900), INK), ('＝ 100', num(78), RED)], a, bg=PANEL)
    runs(d, M + 36, y + 170, [('賣的人又久、又用力地賣了一輪', cjk(38, 700), INK2)], a, bg=PANEL)


def s_why(d, t, img):
    kicker(d, t, 240, '為什麼有用')
    headline(d, t, 410, '想賣的人，是有限的', size=84)
    cols, rws, cs = 12, 5, 62
    x0 = M; y0 = 520
    gone = clamp((t - 2.0) / 2.6)                 # 一排一排賣掉
    for j in range(rws):
        for i in range(cols):
            idx = j * cols + i; keep = idx >= int(gone * 52)   # 留下少數
            a = ph(t, 0.4 + idx * 0.012, 0.3)
            col = (ORG if j < 3 else RED) if keep else LINE
            if a > 0: d.rounded_rectangle([x0 + i * (cs + 12) * 0.98, y0 + j * (cs + 14), x0 + i * (cs + 12) * 0.98 + cs, y0 + j * (cs + 14) + cs], 12, fill=mix(col, a))
    a = ph(t, 1.0)
    d.rounded_rectangle([M, 920, M + 30, 950], 8, fill=mix(ORG, a)); runs(d, M + 48, 948, [('這五個月才上車、已經賠錢的人', cjk(36, 700), INK2)], a)
    d.rounded_rectangle([M, 980, M + 30, 1010], 8, fill=mix(RED, a)); runs(d, M + 48, 1008, [('被清掉的槓桿', cjk(36, 700), INK2)], a)
    a = ph(t, 3.6, 0.5)
    runs(d, M, 1150 + (1 - a) * 30, [('賣一輪，就少一輪', cjk(84, 900), RED)], a)
    runs(d, M, 1230, [('鏈上也對得上：短期持有者今年認賠最集中的幾段，', cjk(30, 500), INK3)], ph(t, 4.2))
    runs(d, M, 1276, [('都落在 SPI 滿格前後', cjk(30, 500), INK3)], ph(t, 4.2))


# 價格（對數）＋ 20 次滿格
CX0, CX1, CY0, CY1 = M, W - M, 500, 1070
LO, HI = math.log10(5), math.log10(200000)
DX0, DX1 = ROWS[0][0], ROWS[-1][0]
cx = lambda n: CX0 + (n - DX0) / (DX1 - DX0) * (CX1 - CX0)
cy = lambda p: CY1 - (math.log10(max(p, 5)) - LO) / (HI - LO) * (CY1 - CY0)

def s_chart(d, t, img):
    kicker(d, t, 240, '2012 年以來')
    headline(d, t, 410, '滿格 20 次，後來呢？', size=80)
    for p, lab in ((10, '$10'), (100, '$100'), (1000, '$1K'), (10000, '$10K'), (100000, '$100K')):
        y = cy(p); d.line([(CX0, y), (CX1, y)], fill=rgb(LINE), width=2)
        d.text((CX0 + 4, y - 8), lab, font=mono(24), fill=rgb(INK3), anchor='ls')
    for yr in (2014, 2017, 2020, 2023, 2026):
        x = cx(s2d(f'{yr}-01-01')); d.text((x, CY1 + 36), str(yr), font=mono(26), fill=rgb(INK3), anchor='mm')
    prog = ease((t - 0.3) / 3.4); end = DX0 + (DX1 - DX0) * prog
    S2 = 2; lay = Image.new('RGBA', (W * S2, H * S2), (0, 0, 0, 0)); g = ImageDraw.Draw(lay)
    pts = [(cx(r[0]) * S2, cy(r[1]) * S2) for r in ROWS if r[0] <= end]
    if len(pts) > 1: g.line(pts, fill=rgb(INK2) + (255,), width=5, joint='curve')
    seen_w = seen = 0
    for e in EV + [CUR]:
        n = s2d(e['date'])
        if n > end: continue
        k = back((t - (0.3 + 3.4 * (n - DX0) / (DX1 - DX0) * 0.75)) / 0.35) if prog < 1 else 1   # 線經過就冒出來
        k = max(0, min(k, 1.3)); x, y = cx(n) * S2, cy(e['price']) * S2; r = 15 * S2 * k
        col = CY if e is CUR else (GRN if e['ret'] > 0 else RED)
        if e is CUR:
            pul = 1 + 0.25 * math.sin(t * 6); g.ellipse([x - r * 1.7 * pul, y - r * 1.7 * pul, x + r * 1.7 * pul, y + r * 1.7 * pul], outline=rgb(CY) + (200,), width=4)
        else:
            seen += 1; seen_w += e['ret'] > 0
        g.ellipse([x - r, y - r, x + r, y + r], fill=rgb(col) + (255,), outline=rgb(BG) + (255,), width=4)
    img.alpha_composite(lay.resize((W, H), Image.LANCZOS))
    a = ph(t, 0.6)
    xe = runs(d, M, 1250, [(f'{seen_w}', num(110), GRN), (' / 20', num(110, 700), INK3)], a)
    runs(d, xe + 36, 1204, [('SPI 退回 0 那天', cjk(34, 700), INK2)], a)
    runs(d, xe + 36, 1250, [('價格比滿格那天高', cjk(34, 700), GRN)], a)
    a = ph(t, 4.0)
    d.ellipse([M, 1290, M + 22, 1312], fill=mix(RED, a)); runs(d, M + 34, 1311, [('比滿格那天低', cjk(28, 500), INK3)], a)
    d.ellipse([M + 270, 1290, M + 292, 1312], fill=mix(CY, a)); runs(d, M + 304, 1311, [('這次（11/10）', cjk(28, 500), INK3)], a)


def s_stats(d, t, img):
    kicker(d, t, 240, '滿格之後三個月')
    headline(d, t, 410, '漲幅中位數', size=84)
    base = 1030; sc = 22
    for i, (lab, v, col, st0) in enumerate((('SPI 滿格那天', S['f90']['med'], GRN, 0.5), ('平常隨便一天', S['base90']['med'], INK3, 1.4))):
        k = ease((t - st0) / 1.0); x0 = M + i * 420; h = v * sc * k; a = ph(t, st0 - 0.2)
        d.rounded_rectangle([x0, base - h, x0 + 300, base], 16, fill=mix(col, a))
        runs(d, x0, base - h - 24, [(f'+{v * k:.1f}%', num(96), col)], a)
        runs(d, x0, base + 60, [(lab, cjk(40, 800), INK2)], a)
    a = ph(t, 3.0)
    runs(d, M, 1180, [('2023 年以後 6 次', cjk(46, 900), INK)], a)
    runs(d, M, 1232, [('SPI 退回 0 那天，全部比滿格高', cjk(32, 600), INK3)], a)
    for i in range(6):
        k = back((t - 3.4 - i * 0.22) / 0.35); r = 30 * clamp(k)
        x = M + 640 + (i % 3) * 82 + 30; y = 1170 + (i // 3) * 76
        if k > 0: d.ellipse([x - r, y - r, x + r, y + r], fill=rgb(GRN))
        if k > 0.8: d.text((x, y), '✓', font=cjk(34, 900), fill=rgb(BG), anchor='mm')


def s_caveat(d, t, img):
    kicker(d, t, 240, '要先知道的', INK3)
    headline(d, t, 410, '它不是抓最低點', size=90)
    a = ph(t, 0.8)
    runs(d, M, 560, [('中途多半還會再往下探一段', cjk(46, 800), INK2)], a)
    runs(d, M, 720, [(f'{DIP10}', num(150), RED), (' / 20', num(90, 700), INK3)], a)
    runs(d, M + 330, 660, [('次中途再跌一成以上', cjk(36, 700), INK2)], a)
    runs(d, M + 330, 712, [(f'中位數 −{abs(DIPMED):.0f}%', cjk(36, 700), INK3)], a)
    a = ph(t, 2.8)
    runs(d, M, 860, [('真正大賠的兩次，都在熊市中段', cjk(46, 800), INK)], a)
    for i, e in enumerate(BIG):
        k = ph(t, 3.3 + i * 0.4, 0.4); y = 920 + i * 150 + (1 - k) * 30
        d.rounded_rectangle([M, y, RIGHT, y + 126], 16, fill=mix(PANEL, k), outline=mix(RED, k), width=3)
        dt = D.date.fromisoformat(e['date'])
        runs(d, M + 32, y + 82, [(f'{dt.year}/{dt.month:02d}', num(64), INK)], k, bg=PANEL)
        runs(d, RIGHT - 32, y + 80, [('退回 0 時 ', cjk(32, 600), INK3), (f'−{abs(e["ret"]):.0f}%', num(64), RED)], k, bg=PANEL, anchor='rs')
    runs(d, M, 1260, [('另外 3 次沒收高的，只差 3% 上下', cjk(32, 600), INK3)], ph(t, 4.4))


def s_now(d, t, img):
    kicker(d, t, 240, '現在', CY)
    a = ph(t, 0.1)
    runs(d, M, 420, [('11/11 收盤', cjk(46, 700), INK2)], a)
    runs(d, M - 6, 610, [('SPI ', num(150, 700), INK), ('100', num(200), RED)], ph(t, 0.3))
    runs(d, M + 640, 610, [(f'第 {S["at100"]} 天', cjk(56, 900), INK2)], ph(t, 0.6))
    # 近 180 天：價格（上）＋ SPI（下）
    rows = [r for r in ROWS if r[0] >= ROWS[-1][0] - 180]
    x0, x1, y0, y1, z0, z1 = M, RIGHT, 690, 960, 990, 1130
    lo, hi = min(r[1] for r in rows) * 0.97, max(r[1] for r in rows) * 1.02
    px = lambda n: x0 + (n - rows[0][0]) / (rows[-1][0] - rows[0][0]) * (x1 - x0)
    k = ease((t - 0.5) / 2.2); n = max(2, int(len(rows) * k))
    S2 = 2; lay = Image.new('RGBA', (W * S2, H * S2), (0, 0, 0, 0)); g = ImageDraw.Draw(lay)
    g.line([(px(r[0]) * S2, (y1 - (r[1] - lo) / (hi - lo) * (y1 - y0)) * S2) for r in rows[:n]], fill=rgb(INK) + (255,), width=6, joint='curve')
    poly = [(px(rows[0][0]) * S2, z1 * S2)] + [(px(r[0]) * S2, (z1 - r[2] / 100 * (z1 - z0)) * S2) for r in rows[:n]] + [(px(rows[n - 1][0]) * S2, z1 * S2)]
    g.polygon(poly, fill=rgb(RED) + (255,))
    img.alpha_composite(lay.resize((W, H), Image.LANCZOS))
    d.text((x0, z0 - 10), 'SPI', font=mono(24, 700), fill=rgb(INK3), anchor='ls')
    d.text((x0, y0 - 10), 'BTC 收盤，近 6 個月', font=cjk(26, 600), fill=rgb(INK3), anchor='ls')
    a = ph(t, 3.0, 0.5); y = 1180 + (1 - a) * 30
    runs(d, M, y + 40, [('接下來看：SPI 往下退的時候', cjk(42, 800), INK)], a)
    runs(d, M, y + 100, [('價格有沒有跟著站穩', cjk(42, 800), CY)], a)


def s_outro(d, t, img):
    a = ph(t, 0.0, 0.5)
    logo(d, W / 2, 700, 3.2, a=a, rise=ease((t - 0.1) / 1.0))
    runs(d, W / 2, 880, [('DAYBREAK', cjk(120, 900), INK)], ph(t, 0.4), anchor='ms')
    runs(d, W / 2, 970, [('每天一分鐘，看 BTC 走到哪', cjk(46, 700), INK2)], ph(t, 0.6), anchor='ms')
    a = ph(t, 0.9)
    d.rounded_rectangle([M + 80, 1040, W - M - 80, 1140], 18, fill=mix(RED, a))
    runs(d, W / 2, 1106, [('daybreak.aronlab.dev', mono(46, 700), '#FFFFFF')], a, bg=RED, anchor='ms')
    runs(d, W / 2, 1210, [('X @songpu717', mono(38, 600), INK2)], ph(t, 1.1), anchor='ms')
    runs(d, W / 2, 1290, [('本站自製指標，只作讀值，非投資建議', cjk(28, 500), INK3)], ph(t, 1.3), anchor='ms')


FNS = [s_hook, s_what, s_why, s_chart, s_stats, s_caveat, s_now, s_outro]
BASE = L['base']; assert len(BASE) == len(FNS) == len(L['caps'])
AUDIO = sys.argv[sys.argv.index('--audio') + 1] if '--audio' in sys.argv else None
DURS = json.load(open(os.path.join(AUDIO, 'timing.json')))['durs'] if AUDIO else BASE
TOTAL = sum(DURS); XF = 0.3; LEAD, TAIL = 0.25, 0.55

# 字幕時間：每場景內依旁白字數平均分配
CAPS = []
st0 = 0
for i, caps in enumerate(L['caps']):
    span = max(0.5, DURS[i] - LEAD - TAIL); w = [len(c) for c in caps]; acc = st0 + LEAD
    for c, n in zip(caps, w):
        dt = span * n / sum(w); CAPS.append((acc, acc + dt, c, i)); acc += dt
    st0 += DURS[i]

def caption(d, T):
    for a0, a1, text, i in CAPS:
        if a0 - 0.05 <= T < a1 + (0.25 if i < len(FNS) - 1 else 9):
            f = cjk(48, 900); tw = f.getlength(text); x = (W - tw) / 2
            k = ph(T, a0 - 0.05, 0.15)
            d.rounded_rectangle([x - 28, CAP_Y - 62, x + tw + 28, CAP_Y + 22], 16, fill=mix('#000000', 0.9 * k, BG))
            d.text((W / 2, CAP_Y), text, font=f, fill=mix('#FFFFFF', k), anchor='ms'); return

def scene_img(i, t):
    if i: t *= BASE[i] / DURS[i]   # 開頭不放慢：圖要在 3 秒內畫完、標出現在的位置，之後停著讓旁白講
    img = Image.new('RGBA', (W, H), rgb(BG) + (255,)); FNS[i](ImageDraw.Draw(img), t, img); return img

def frame(T):
    s = 0
    for i, dur in enumerate(DURS):
        if T < s + dur or i == len(DURS) - 1: break
        s += dur
    t = T - s; img = scene_img(i, t)
    if i + 1 < len(DURS) and t > DURS[i] - XF:
        img = Image.blend(img, scene_img(i + 1, t - DURS[i]), ease((t - (DURS[i] - XF)) / XF))
    d = ImageDraw.Draw(img); chrome(d, T, TOTAL); caption(d, T)
    return img.convert('RGB')


if __name__ == '__main__':
    if '--frames' in sys.argv:
        for x in sys.argv[sys.argv.index('--frames') + 1].split(','): frame(float(x)).save(f'{OUT}_{x}.png')
        sys.exit()
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe(); n = int(TOTAL * FPS)
    p = subprocess.Popen([ff, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          *(['-i', os.path.join(AUDIO, 'mix.wav'), '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '44100', '-ac', '2']
                            if AUDIO else ['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100']),
                          '-shortest', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p',
                          '-profile:v', 'high', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
    for f in range(n):
        p.stdin.write(frame(f / FPS).tobytes())
        if f % 300 == 0: print(f'{f}/{n}', flush=True)
    p.stdin.close(); p.wait()
    frame(DURS[0] - 0.6).save(OUT.replace('.mp4', '-cover.png'))
    print('done', OUT, f'{TOTAL:.1f}s')
