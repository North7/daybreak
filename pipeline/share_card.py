#!/usr/bin/env python3
"""每日分享圖（2026-10-13 建立）：號外風格 16:9 圖卡，給 X 貼文附圖用。
讀 data/latest.json 與 data/notes.json（英文版讀 data/notes.en.json），輸出 data/share.png、data/share-en.png。
頭條取自當期日報；標題裡的數字標號外紅（規則與網站相同）；底部三格固定為市場階段、ETF 7 個完整交易日（標明截至哪天）、短期持有者成本（STH 實現價格）與收盤在它上方或下方多少。
2026-11-08：第三格原為「離出場第一階」，X 貼文只放資訊、不放出場框架，改成短期持有者成本；網站本身的出場框架不變。
字型與網站相同（Noto Sans TC 900、Archivo 窄體、JetBrains Mono），由 --fonts 指定的資料夾讀取。
用法（在倉庫根目錄）：python3 pipeline/share_card.py --fonts <字型資料夾>"""
import json, os, re, sys, argparse, datetime as dt
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
W, H, M = 1200, 675, 64
# 2026-11-12：改成深色。純黑太刺眼，改用「破曉漸層」：上方深藍灰往下轉暖（從夜到天亮），文字略帶暖米色、紅色稍柔；
# 底紋同網站的網點。PAPER 是漸層上端，PAPER_BOTTOM 是下端
PAPER, PAPER_BOTTOM, INK, INK3, RED, LINE = '#15171F', '#2B1F22', '#ECE8E0', '#8E8C92', '#FF6A45', '#33343E'
DOT, DOT_STEP = '#22242D', 22
NUM = re.compile(r'(\d{1,2}/\d{1,2}(?!\d)|[+\-−$]?\d[\d,.]*(?:\s?(?:%|億|萬|千|兆|倍|個基點|基點|bp|K|M|B)(?![A-Za-z]))?)')
TXT = {
    'zh': dict(tag='號外', stage='市場階段', etf='ETF 7 個交易日（至 {}）', sth='短期持有者成本', above='收盤在上方', below='收盤在下方', day='第 {} 天',
               names={'熊市': '熊市', '轉換期': '熊牛轉換期', '牛市': '牛市'}, wd='一二三四五六日', close='收盤版'),
    'en': dict(tag='EXTRA', stage='MARKET STAGE', etf='ETF · 7 DAYS TO {}', sth='STH COST BASIS', above='CLOSE ABOVE', below='CLOSE BELOW', day='day {}',
               names={'熊市': 'Bear', '轉換期': 'Transition', '牛市': 'Bull'}, wd=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], close='close'),
}

def fonts(d):
    f = lambda name, size, axes: (lambda ft: (ft.set_variation_by_axes(axes), ft)[1])(ImageFont.truetype(os.path.join(d, name), size))
    return dict(head=lambda s: f('NotoSansTC[wght].ttf', s, [900]), cjk=lambda s, w=700: f('NotoSansTC[wght].ttf', s, [w]),
                num=lambda s: f('Archivo[wdth,wght].ttf', s, [900, 62]), mono=lambda s, w=500: f('JetBrainsMono[wght].ttf', s, [w]))

def atoms(text):
    """切成可換行的最小單位（中文逐字、英數整詞），各帶是否為數字（紅色）。"""
    out, pos = [], 0
    for m in list(NUM.finditer(text)) + [None]:
        seg = text[pos:m.start()] if m else text[pos:]
        for a in re.findall(r'[A-Za-z][\w\'’.-]*\s*|\s+|.', seg): out.append((a, False))
        if m: out.append((m.group(0) + (' ' if text[m.end():m.end() + 1] == ' ' else ''), True)); pos = m.end() + (1 if text[m.end():m.end() + 1] == ' ' else 0)
    return out

def wrap(text, font, width):
    lines, cur, cw = [], [], 0
    for a, red in atoms(text):
        w = font.getlength(a)
        if cur and cw + w > width and a.strip() and a not in '，。、；：）」』！？,.;:!?)':
            lines.append(cur); cur, cw = [], 0
            if not a.strip(): continue
        cur.append((a, red)); cw += w
    if cur: lines.append(cur)
    return lines

def card(lang, latest, notes, F, out):
    T = TXT[lang]; img = Image.new('RGB', (W, H), PAPER); d = ImageDraw.Draw(img)
    t, b = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in (PAPER, PAPER_BOTTOM))
    for y in range(H):   # 破曉漸層：由上往下
        f = y / (H - 1); d.line([(0, y), (W, y)], fill=tuple(round(t[j] + (b[j] - t[j]) * f) for j in range(3)))
    for gy in range(DOT_STEP // 2, H, DOT_STEP):   # 網點底紋
        for gx in range(DOT_STEP // 2, W, DOT_STEP): d.ellipse([gx - 1, gy - 1, gx + 1, gy + 1], fill=DOT)
    d.rectangle([M, 52, W - M, 58], fill=INK)   # 號外粗頂線
    tag = F['cjk'](26, 900) if lang == 'zh' else F['mono'](22, 800)
    tw = d.textlength(T['tag'], font=tag); d.rectangle([M, 76, M + tw + 28, 116], fill=RED); d.text((M + 14, 96), T['tag'], font=tag, fill='#FFFFFF', anchor='lm')
    bd = dt.date.fromisoformat(latest['meta']['bar_date'])
    meta = f"DAYBREAK No.{notes.get('edition', 0):03d}   {bd:%Y.%m.%d}（{T['wd'][bd.weekday()]}）{T['close']}" if lang == 'zh' else \
           f"DAYBREAK No.{notes.get('edition', 0):03d}   {T['wd'][bd.weekday()]} {bd:%b %d, %Y} {T['close']}"
    d.text((M + tw + 52, 96), meta, font=F['mono'](20) if lang == 'en' else F['cjk'](20, 500), fill=INK3, anchor='lm')
    # 頭條：自動縮字，最多 4 行
    for size in range(74, 36, -2):   # 頭條區高 300px（150 到 450），放得下才停
        hf = F['head'](size); lines = wrap(notes['headline'], hf, W - 2 * M)
        if len(lines) <= 4 and len(lines) * int(size * 1.28) <= 300: break
    y, lh = 150, int(size * 1.28)
    for ln in lines[:4]:
        x = M
        for a, red in ln:
            d.text((x, y), a, font=hf, fill=RED if red else INK); x += hf.getlength(a)
        y += lh
    # 底部三格
    st = (latest.get('cycle') or {}).get('stage') or {}
    days = (bd - dt.date.fromisoformat(st['since'])).days + 1 if st.get('since') else None
    stage = T['names'].get(st.get('stage'), '—') + (('・' if lang == 'zh' else ' · ') + T['day'].format(days) if days and st.get('stage') == '牛市' else '')
    rows = [r for r in (latest.get('flows') or {}).get('etf', []) if not r.get('partial')][-7:]
    s7 = sum(r['musd'] for r in rows) if rows else None
    etf = '—' if s7 is None else (f"{'+' if s7 >= 0 else '−'}{abs(s7) / 100:.2f} 億" if lang == 'zh' else f"{'+' if s7 >= 0 else '−'}${abs(s7):,.0f}M")
    # 短期持有者成本：數字放大，旁邊小字兩行寫收盤在它上方或下方多少（只是位置，不帶操作結論）
    sth = (((latest.get('onchain') or {}).get('metrics') or {}).get('sth-realized-price') or {}).get('value')
    close = ((latest.get('price') or {}).get('bar') or {}).get('c')
    sth_v = '—' if not sth else f"{sth:,.0f}"
    sth_side = None if not (sth and close) else (T['above'] if close >= sth else T['below'], f"{abs(close / sth - 1) * 100:.1f}%")
    top = 470; d.rectangle([M, top, W - M, top + 2], fill=INK); cw = (W - 2 * M) / 3
    # 2026-10-21：標上最後一個完整交易日。The Block 通常晚一到兩個交易日，頭條若寫更新的暫定值，「近 7 日」看起來會和頭條矛盾
    etf_k = T['etf'].format((f"{dt.date.fromisoformat(rows[-1]['d']):%-m/%-d}" if lang == 'zh' else f"{dt.date.fromisoformat(rows[-1]['d']):%b %-d}".upper()) if rows else '—')
    for i, (k, v) in enumerate(((T['stage'], stage), (etf_k, etf), (T['sth'], sth_v))):
        x = M + i * cw + (0 if i == 0 else 24)
        if i: d.line([M + i * cw, top + 22, M + i * cw, top + 118], fill=LINE, width=1)
        d.text((x, top + 30), k, font=F['mono'](17) if lang == 'en' else F['cjk'](18, 500), fill=INK3)
        vf = F['cjk'](42, 900) if re.search(r'[一-鿿]', v) else F['num'](58)
        d.text((x, top + 62), v, font=vf, fill=RED if v.startswith('−') and i == 1 else INK)
        if i == 2 and sth_side:
            sx = x + d.textlength(v, font=vf) + 16; sf = F['mono'](16) if lang == 'en' else F['cjk'](18, 500)
            d.text((sx, top + 70), sth_side[0], font=sf, fill=INK3)
            d.text((sx, top + 93), sth_side[1], font=F['num'](30), fill=INK)
    # 頁尾：日出 logo、網址、X 帳號
    fy = H - 44; d.line([M, fy - 22, W - M, fy - 22], fill=LINE, width=1)
    d.arc([M, fy - 14, M + 28, fy + 14], 180, 360, fill=RED, width=4); d.line([M - 4, fy, M + 32, fy], fill=INK, width=4)
    d.text((M + 44, fy), 'DAYBREAK', font=F['cjk'](20, 900) if lang == 'zh' else F['mono'](20, 800), fill=INK, anchor='lm')
    d.text((W - M, fy), 'X @songpu717', font=F['mono'](19), fill=INK3, anchor='rm')
    img.save(out, optimize=True)
    print('wrote', out, 'headline lines', len(lines), 'size', size)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--fonts', required=True); a = ap.parse_args()
    F = fonts(a.fonts); latest = json.load(open(P('data', 'latest.json')))
    for lang, nf, out in (('zh', 'notes.json', 'share.png'), ('en', 'notes.en.json', 'share-en.png')):
        try: notes = json.load(open(P('data', nf)))
        except FileNotFoundError: print('skip', nf); continue
        if notes.get('date') != latest['meta']['bar_date']: print('skip', nf, '日期與資料不同', notes.get('date')); continue
        card(lang, latest, notes, F, P('data', out))
