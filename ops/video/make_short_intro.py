"""Daybreak 介紹 Short（沒有配音，配樂＋大字）：1080×1920、30fps、深色。
素材：<素材資料夾>/shots/*.png（next_shot.py 的 share45：dawn、levels、sx、pr-us、fh）、<素材資料夾>/mob/ch_*.png（手機版 390×844、3 倍的各頁第一屏）。
出場框架不進畫面：手機版不用「今天」（有「持有」標籤）和「價位」（圖上有出場階梯、MVRV 賣出線），截圖時也把出場卡片藏掉。
用法：python make_short_intro.py <素材資料夾> <fonts> <out.mp4> [--frames 秒,秒,...]"""
import math, os, subprocess, sys, wave
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from music import music, SR

ASSET, FONTS, OUT = sys.argv[1:4]
W, H, FPS, M = 1080, 1920, 30, 72
BG, PANEL, INK, INK2, INK3, LINE = '#0A0A0A', '#151517', '#F2F0EA', '#C9C5BC', '#8E897F', '#2A2927'
RED, GRN, CY, ORG = '#FF4D2E', '#C6F432', '#3FD4E8', '#FF8A3D'
BPM = 104; BEAT = 60 / BPM

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
def inout(x): x = clamp(x); return x * x * (3 - 2 * x)
def ph(t, s, d=0.35): return ease((t - s) / d)
def text(d, xy, s, f, c, a=1.0, anchor='ls', bg=BG):
    if a > 0.01: d.text(xy, s, font=f, fill=mix(c, a, bg), anchor=anchor)

# ---------- 素材 ----------
SH = {k: Image.open(os.path.join(ASSET, 'shots', k + '.png')).convert('RGB') for k in ('dawn', 'levels', 'sx', 'pr-us', 'fh')}
MOB = {k: Image.open(os.path.join(ASSET, 'mob', f'ch_{k}.png')).convert('RGB') for k in ('cycle', 'sell', 'buy', 'lev')}
MOB = {k: v.crop((0, 0, v.width, int(v.height * 784 / 844))) for k, v in MOB.items()}   # 切掉底部分頁列（裡面有「出場」）
PW = 560; PH = round(PW * MOB['buy'].height / MOB['buy'].width)
MOBS = {k: v.resize((PW, PH), Image.LANCZOS) for k, v in MOB.items()}

def phone(img, scr, cx, top, a=1.0, scale=1.0):
    """手機外框＋螢幕。scr 是已經縮好的螢幕圖（PW×PH）。"""
    w, h = int(PW * scale), int(PH * scale); bz = int(18 * scale)
    s = scr if scale == 1 else scr.resize((w, h), Image.LANCZOS)
    x0, y0 = int(cx - w / 2), int(top)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0 - bz, y0 - bz, x0 + w + bz, y0 + h + bz], int(70 * scale), fill=mix('#26262B', a), outline=mix('#44444C', a), width=3)
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w, h], int(54 * scale), fill=int(255 * a))
    img.paste(s, (x0, y0), m)

def chrome(d, T, total):
    d.rectangle([0, 0, W * T / total, 8], fill=rgb(RED))
    r = 22; cx, cy = M + 24, 118
    d.arc([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=rgb(RED), width=7); d.line([(cx - r - 7, cy), (cx + r + 7, cy)], fill=rgb(INK), width=7)
    text(d, (M + 70, 118), 'DAYBREAK', cjk(36, 900), INK, anchor='lm')
    text(d, (W - M, 118), 'daybreak.aronlab.dev', mono(26, 600), INK3, anchor='rm')

# ---------- 場景（長度都是拍子的整數倍，轉場落在拍點上） ----------
def s_hook(img, d, t):
    for i, (s, c) in enumerate((('BTC 現在', INK), ('走到哪了？', RED))):
        a = ph(t, i * 0.18, 0.3); text(d, (M, 360 + i * 150 + (1 - a) * 40), s, cjk(132, 900), c, a)
    a = ph(t, 0.9); text(d, (M, 640), '每天早上，一分鐘看完', cjk(52, 800), INK2, a)
    k = ease((t - 0.6) / 1.1); phone(img, MOBS['buy'], W / 2, 720 + (1 - k) * 900, a=clamp(k * 1.5))

PAGES = [('cycle', '週期', '現在在週期的哪裡'), ('sell', '賣壓', '賣壓出清了沒'), ('buy', '買盤', '誰在買、錢從哪裡來'), ('lev', '槓桿', '槓桿和情緒擠不擠')]
def s_pages(img, d, t):
    seg = 3 * BEAT; i = min(len(PAGES) - 1, int(t / seg)); u = t - i * seg
    text(d, (M, 330), '一頁回答一個問題', cjk(70, 900), INK, ph(t, 0.0))
    # 分頁籤
    x = M
    for j, (_, lab, _) in enumerate(PAGES):
        f = cjk(40, 900); tw = f.getlength(lab); on = j == i
        d.rounded_rectangle([x, 380, x + tw + 44, 446], 33, fill=rgb(RED) if on else rgb(PANEL))
        text(d, (x + 22, 413), lab, f, '#0A0A0A' if on else INK3, anchor='lm', bg=RED if on else PANEL); x += tw + 60
    text(d, (M, 520), PAGES[i][2] + '？', cjk(50, 800), INK2, ph(u, 0.05, 0.25))
    # 手機：像左右滑動一樣換頁
    cx = W / 2; top = 620
    if u < 0.35 and i > 0:
        k = inout(u / 0.35); off = (PW + 120) * k
        phone(img, MOBS[PAGES[i - 1][0]], cx - off, top); phone(img, MOBS[PAGES[i][0]], cx + PW + 120 - off, top)
    else:
        phone(img, MOBS[PAGES[i][0]], cx, top)

CHARTS = [('dawn', '週期', '晨昏指數：現在在週期的哪裡'), ('levels', '價位', '價格站在哪些成本線上'), ('sx', '賣壓', '賣壓累積：賣的人倒完了沒'),
          ('pr-us', '買盤', 'Coinbase 溢價：美國買盤在不在'), ('fh', '槓桿', '資金費率：槓桿擠不擠')]
CW = 900; CHH = round(CW * 1350 / 1080)
CIMG = {k: v.resize((CW, CHH), Image.LANCZOS) for k, v in SH.items()}
def s_charts(img, d, t):
    seg = 4 * BEAT; i = min(len(CHARTS) - 1, int(t / seg)); u = t - i * seg
    k, tag, cap = CHARTS[i]
    f = cjk(36, 900); tw = f.getlength(tag)
    d.rounded_rectangle([M, 236, M + tw + 36, 292], 6, fill=rgb(RED)); text(d, (M + 18, 264), tag, f, '#0A0A0A', anchor='lm', bg=RED)
    text(d, (M, 380), cap, cjk(58, 900), INK, ph(u, 0.05, 0.25))
    z = 1.0 + 0.05 * (u / seg); a = ph(u, 0.0, 0.3)
    im = CIMG[k].resize((int(CW * z), int(CHH * z)), Image.LANCZOS)
    x0 = int((W - im.width) / 2); y0 = 440 - int((im.height - CHH) / 2)
    if a < 1:   # 跟上一張交叉淡化，不閃黑
        prev = CIMG[CHARTS[i - 1][0]].resize((int(CW * 1.05), int(CHH * 1.05)), Image.LANCZOS).crop(((int(CW * 1.05) - im.width) // 2, (int(CHH * 1.05) - im.height) // 2, (int(CW * 1.05) - im.width) // 2 + im.width, (int(CHH * 1.05) - im.height) // 2 + im.height)) if i else Image.new('RGB', im.size, rgb(BG))
        im = Image.blend(prev, im, a)
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width, im.height], 24, fill=255)
    img.paste(im, (x0, y0), m)
    d.rounded_rectangle([x0, y0, x0 + im.width, y0 + im.height], 24, outline=rgb(LINE), width=3)

def s_facts(img, d, t):
    rows = [('100+', '張圖表，五個問題', RED), ('每天', '收盤後自動更新', INK), ('免費', '中文 / English', GRN)]
    for i, (big, small, c) in enumerate(rows):
        a = ph(t, 0.1 + i * 0.35, 0.35); y = 520 + i * 270 + (1 - a) * 40
        text(d, (M, y), big, num(190) if big[0].isdigit() else cjk(170, 900), c, a)
        text(d, (M + 470, y - 40), small, cjk(50, 800), INK2, a)

def s_outro(img, d, t):
    a = ph(t, 0.0, 0.5); rise = ease((t - 0.1) / 0.9); cx, cy = W / 2, 760; r = 84
    off = (1 - rise) * r * 1.3
    d.arc([cx - r, cy - r + off, cx + r, cy + r + off], 180, 360, fill=mix(RED, a), width=24)
    d.rectangle([cx - r - 30, cy + 12, cx + r + 30, cy + 2 * r + 40], fill=rgb(BG))
    d.line([(cx - r - 30, cy), (cx + r + 30, cy)], fill=mix(INK, a), width=24)
    text(d, (cx, 960), 'DAYBREAK', cjk(130, 900), INK, ph(t, 0.3), anchor='ms')
    text(d, (cx, 1050), '每天一分鐘，看 BTC 走到哪', cjk(50, 800), INK2, ph(t, 0.5), anchor='ms')
    a = ph(t, 0.8)
    d.rounded_rectangle([M + 70, 1120, W - M - 70, 1224], 20, fill=mix(RED, a))
    text(d, (cx, 1190), 'daybreak.aronlab.dev', mono(48, 700), '#FFFFFF', a, anchor='ms', bg=RED)
    text(d, (cx, 1300), 'X @songpu717', mono(38, 600), INK2, ph(t, 1.0), anchor='ms')
    text(d, (cx, 1380), '資料整理，非投資建議', cjk(30, 500), INK3, ph(t, 1.2), anchor='ms')

SCENES = [(s_hook, 6), (s_pages, 12), (s_charts, 20), (s_facts, 7), (s_outro, 9)]   # 拍數
DURS = [n * BEAT for _, n in SCENES]; TOTAL = sum(DURS); XF = 0.18

def scene(i, t):
    img = Image.new('RGB', (W, H), rgb(BG)); d = ImageDraw.Draw(img); SCENES[i][0](img, d, max(0.0, t)); return img

def frame(T):
    s = 0
    for i, dur in enumerate(DURS):
        if T < s + dur or i == len(DURS) - 1: break
        s += dur
    t = T - s; img = scene(i, t)
    if i + 1 < len(DURS) and t > DURS[i] - XF:
        img = Image.blend(img, scene(i + 1, 0), inout((t - (DURS[i] - XF)) / XF))
    chrome(ImageDraw.Draw(img), T, TOTAL); return img

if __name__ == '__main__':
    if '--frames' in sys.argv:
        for x in sys.argv[sys.argv.index('--frames') + 1].split(','): frame(float(x)).save(f'{OUT}_{x}.png')
        sys.exit()
    cuts = list(np.cumsum(DURS)[:-1])
    a = music(TOTAL, cuts, BPM); wav = OUT.replace('.mp4', '.wav')
    with wave.open(wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((a * 32767).astype(np.int16).tobytes())
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe(); n = int(TOTAL * FPS)
    p = subprocess.Popen([ff, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-i', wav, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '44100', '-ac', '2', '-shortest',
                          '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                          '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
    for f in range(n):
        p.stdin.write(frame(f / FPS).tobytes())
        if f % 300 == 0: print(f'{f}/{n}', flush=True)
    p.stdin.close(); p.wait(); os.remove(wav)
    frame(DURS[0] - 0.3).save(OUT.replace('.mp4', '-cover.png'))
    print('done', OUT, f'{TOTAL:.1f}s')
