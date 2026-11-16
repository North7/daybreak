"""在網站圖表截圖上標出文中引用的數字（2026-11-05 使用者要求：文中提到、圖上找得到的數字要標出位置）。
座標由圖自己的刻度換算（site_shot.py 存的 .json）：年份標籤在每年 1/1、% 刻度線性、價格與比值刻度對數。
usage（倉庫根目錄）: python3 ops/post/annotate.py <spec.json> <截圖資料夾> <輸出資料夾> <字型資料夾>
spec: {"<raw name>": {"axes": {"<axis>": {"kind": "lin"|"log", "unit": "%"|"", "yrange": [y0, y1]}}, "palette": {...},
                       "marks": [{"axis": "<axis>", "date": "YYYY-MM-DD", "v": 6.5, "label": "...", "color": "s2"|"#hex",
                                  "lv": <label value>, "ldx": <label x offset, CSS px>, "anchor": "middle"|"start"|"end",
                                  "dot": true, "plain": false}]}}
  yrange picks which tick labels belong to an axis (CSS px, top of the screenshot = 0). Year labels sit at Jan 1.
  Legacy: "axis": "pct" at the image level = one linear % axis over all % labels.

2026-11-16 起（舊版 classic.html 停用第二步）改用新版首頁：spec 帶 "k"（圖代號，next_shot.py --list 查）就走新版——
  這支自己呼叫 next_shot.py 截分享模式，座標由網站的 window.daybreakXY(圖代號, 日期, 數值, pane) 在截圖當下算好，不再從刻度回推。
  {"<name>": {"k": "rup", "view": "share"|"share45", "lang": "zh"|"en", "m": 1, "rg": 365, "palette": {...},
              "marks": [{"date": "YYYY-MM-DD", "v": 34.4, "pane": ""|"p", "label": "...", "lv": <標籤放的數值>, "ldx": <CSS px>, ...}]}}
  pane "p"＝上格的價格（數值寫美元），不寫＝主圖。<截圖資料夾> 放原始截圖和座標（<name>.png／.json），<輸出資料夾> 放標好的圖。
  m／rg／ly 跟 next_shot.py 一樣（切換檢視、區間、版面）。舊格式（沒有 k，讀 site_shot.py 存的刻度）照舊能用，但舊版頁面之後會刪掉。
"""
import datetime as dt, json, math, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pipeline'))
from PIL import Image, ImageDraw, ImageColor
import share_card as SC

spec, rawdir, outdir, fonts = sys.argv[1:5]
Fn = SC.fonts(fonts); os.makedirs(outdir, exist_ok=True)


def fit(pairs):
    n = len(pairs); mx = sum(a for a, _ in pairs) / n; my = sum(b for _, b in pairs) / n
    b = sum((a - mx) * (c - my) for a, c in pairs) / sum((a - mx) ** 2 for a, _ in pairs)
    return lambda v: my + b * (v - mx)


def num(t):
    t = t.replace(',', '').replace('−', '-'); sg = -1 if t.startswith('-') else 1   # 2026-11-09：刻度有正負號（-20%、+40%）也要認得
    m = re.fullmatch(r'\$?([\d.]+)(K|%)?', t.lstrip('+-'))
    if not m: return None
    try: return sg * float(m.group(1)) * (1000 if m.group(2) == 'K' else 1)
    except ValueError: return None


SPEC = json.load(open(spec, encoding='utf-8'))


def shoot_new():
    """有 k 的項目：照語言分批交給 next_shot.py 截分享模式，每個標記要兩個座標（點的位置、標籤的高度）"""
    import subprocess, tempfile
    by = {}
    for name, s in SPEC.items():
        if not s.get('k'): continue
        xy = []
        for m in s['marks']:
            pane = m.get('pane', ''); xy += [[m['date'], m['v'], pane], [m['date'], m.get('lv', m['v']), pane]]
        it = dict(k=s['k'], out=name, view=s.get('view', 'share'), xy=xy, **{a: s[a] for a in ('m', 'rg', 'ly', 'd3', 'pre') if a in s})
        by.setdefault(s.get('lang', 'zh'), []).append(it)
    for lang, items in by.items():
        jf = os.path.join(tempfile.mkdtemp(prefix='annot-'), 'jobs.json'); json.dump(dict(lang=lang, items=items), open(jf, 'w'))
        subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'next_shot.py'), jf, rawdir], check=True)


def draw(name, s, pts):
    """pts：每個標記一組 (x, y, 標籤 y)，都是圖片像素"""
    im = Image.open(os.path.join(rawdir, name + '.png')).convert('RGB'); d = ImageDraw.Draw(im)
    pal = s.get('palette') or {}
    lf = Fn['cjk'](24, 800)
    for m, (x, y, ly) in zip(s['marks'], pts):
        col = pal.get(m.get('color'), m.get('color', '#FFD23F'))
        lx = x + m.get('ldx', 0) * K
        if m.get('plain'):
            d.text((lx, ly), m['label'], font=Fn['cjk'](22, 700), fill=col, anchor={'start': 'lm', 'end': 'rm'}.get(m.get('anchor'), 'mm'))
            continue
        tw = d.textlength(m['label'], font=lf); pw, ph = tw + 26, 40
        an = m.get('anchor', 'middle')
        bx0 = lx - pw / 2 if an == 'middle' else lx if an == 'start' else lx - pw
        bx0 = max(4, min(im.width - pw - 4, bx0)); by0 = ly - ph / 2
        cx = min(max(x, bx0), bx0 + pw); cy = by0 + ph if y > by0 + ph else by0 if y < by0 else ly
        if abs(cy - y) > 4 or abs(cx - x) > 4: d.line([cx, cy, x, y], fill=col, width=3)
        d.rounded_rectangle([bx0, by0, bx0 + pw, by0 + ph], radius=ph / 2, fill=col)
        # 2026-11-09 使用者：黃底白字看不清楚 → 淺色底自動用深色字（相對亮度 > 0.4 算淺）
        rgb = ImageColor.getrgb(col); lum = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255
        d.text((bx0 + pw / 2, ly), m['label'], font=lf, fill='#141414' if lum > 0.4 else '#FFFFFF', anchor='mm')
        if m.get('dot', True):
            r = 9; d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline='#FFFFFF', width=3)
    im.save(os.path.join(outdir, name + '.png')); print('annotated', name, len(s['marks']))


shoot_new()
for name, s in SPEC.items():
    g = json.load(open(os.path.join(rawdir, name + '.json'))); K = g['dpr']
    if s.get('k'):   # 新版：座標是網站算的（CSS px），乘上 dpr 就是圖片像素
        P2 = g['xy']; draw(name, s, [(P2[2 * i]['x'] * K, P2[2 * i]['y'] * K, P2[2 * i + 1]['y'] * K) for i in range(len(s['marks']))]); continue
    T = g['texts']
    # 2026-11-09：x 軸標籤除了「2026」也可能是「25/7」（2025 年 7 月 1 日）；只有一個年份標籤時單靠年份算不出比例
    def _xd(t):
        if re.fullmatch(r'20\d\d', t): return dt.date(int(t), 1, 1)
        m = re.fullmatch(r'(\d\d)/(\d{1,2})', t)
        return dt.date(2000 + int(m.group(1)), int(m.group(2)), 1) if m else None
    X = fit([(_xd(t['t']).toordinal(), t['x']) for t in T if t.get('anchor') == 'middle' and _xd(t['t'])])
    axes = s.get('axes') or {'pct': {'kind': 'lin', 'unit': '%', 'yrange': [0, 1e9]}}
    Y = {}
    for an, ax in axes.items():
        lo, hi = ax['yrange']
        ticks = [(num(t['t']), t['y']) for t in T if num(t['t']) is not None and lo <= t['y'] <= hi
                 and (t['t'].endswith('%') if ax.get('unit') == '%' else not t['t'].endswith('%')) and t['x'] > 900]
        if ax['kind'] == 'log':
            f = fit([(math.log10(v), y) for v, y in ticks]); Y[an] = (lambda f: lambda v: f(math.log10(v)))(f)
        else:
            Y[an] = fit(ticks)
        print(name, an, 'ticks', [v for v, _ in ticks])
    first = next(iter(axes))
    pts = []
    for m in s['marks']:
        Ya = Y[m.get('axis', first)]
        pts.append((X(dt.date.fromisoformat(m['date']).toordinal()) * K, Ya(m['v']) * K, Ya(m.get('lv', m['v'])) * K))
    draw(name, s, pts)
