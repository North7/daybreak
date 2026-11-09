"""在網站圖表截圖上標出文中引用的數字（2026-11-05 使用者要求：文中提到、圖上找得到的數字要標出位置）。
座標由圖自己的刻度換算（site_shot.py 存的 .json）：年份標籤在每年 1/1、% 刻度線性、價格與比值刻度對數。
usage（倉庫根目錄）: python3 ops/post/annotate.py <spec.json> <截圖資料夾> <輸出資料夾> <字型資料夾>
spec: {"<raw name>": {"axes": {"<axis>": {"kind": "lin"|"log", "unit": "%"|"", "yrange": [y0, y1]}}, "palette": {...},
                       "marks": [{"axis": "<axis>", "date": "YYYY-MM-DD", "v": 6.5, "label": "...", "color": "s2"|"#hex",
                                  "lv": <label value>, "ldx": <label x offset, CSS px>, "anchor": "middle"|"start"|"end",
                                  "dot": true, "plain": false}]}}
  yrange picks which tick labels belong to an axis (CSS px, top of the screenshot = 0). Year labels sit at Jan 1.
  Legacy: "axis": "pct" at the image level = one linear % axis over all % labels.
"""
import datetime as dt, json, math, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'pipeline'))
from PIL import Image, ImageDraw
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


for name, s in json.load(open(spec, encoding='utf-8')).items():
    g = json.load(open(os.path.join(rawdir, name + '.json'))); K = g['dpr']; T = g['texts']
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
    im = Image.open(os.path.join(rawdir, name + '.png')).convert('RGB'); d = ImageDraw.Draw(im)
    pal = s.get('palette') or {}
    lf = Fn['cjk'](24, 800)
    for m in s['marks']:
        Ya = Y[m.get('axis', first)]
        x = X(dt.date.fromisoformat(m['date']).toordinal()) * K; y = Ya(m['v']) * K
        col = pal.get(m.get('color'), m.get('color', '#FFD23F'))
        lx = x + m.get('ldx', 0) * K; ly = Ya(m.get('lv', m['v'])) * K
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
        d.text((bx0 + pw / 2, ly), m['label'], font=lf, fill='#FFFFFF', anchor='mm')
        if m.get('dot', True):
            r = 9; d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline='#FFFFFF', width=3)
    im.save(os.path.join(outdir, name + '.png')); print('annotated', name, len(s['marks']))
