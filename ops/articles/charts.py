#!/usr/bin/env python3
"""X 長文配圖（2026-11-04 建立）：沿用 pipeline/picks.py 的版型（1080×1350、同一套字型與配色），另加幾張長歷史的週期圖。
圖上的數字都直接取自 data/latest.json，不另算；只放市場資訊，不放出場框架（MVRV ÷ 前一輪高點、200 日均線避險、價格階梯都不畫）。

用法（在倉庫根目錄）：
  python3 ops/articles/charts.py --fonts <字型資料夾> [--out ops/articles/img/<日期>]
字型同 share_card.py（NotoSansTC、Archivo、JetBrainsMono，下載網址見 .github/workflows/share.yml）。

新圖：
  analog   四輪對照：從週期低點起算的漲幅（週線收盤，cycle.regime.rows 的價格）
  regime   週線多空分數 2013 年起（cycle.regime.rows）
  powerlaw 價格 ÷ 冪律趨勢價 2012 年起（cycle.powerlaw.rows，對數）
沿用 picks.py 的圖：cost、cbp、sopr、rcliq、oc-lth-net-position-change-30d-btc。"""
import json, os, sys, math, argparse, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import picks as PK                                        # noqa: E402
from picks import T, S, INK, INK3, LINE, RED, S1, S2, S3, UP, dashed, nice   # noqa: E402
from signals import dn, ds                                # noqa: E402

TAG = {'zh': '長文圖表', 'en': 'LONG READ'}


def years(xa, xb, every=2):
    """x 軸只標年份（長歷史用）。"""
    out = []
    for y in range(dt.date.fromordinal(dt.date(1970, 1, 1).toordinal() + xa).year + 1, 2100):
        x = dn(f'{y}-01-01')
        if x > xb: break
        if y % every == 0: out.append((x, str(y), str(y)))
    return out


def draw(d, box, sp, lang, Fn):
    """picks.draw_line_chart 的變體：可自訂 x 刻度（xticks）與 y 刻度（yticks）；沒給就照原本的畫法。"""
    if not sp.get('xticks') and not sp.get('yticks'): return ORIG(d, box, sp, lang, Fn)
    x0, y0, x1, y1 = box; px1 = x1 - 150
    ser = sp['series']; xs = [r[0] for s in ser for r in s['rows']]; ys = [r[1] for s in ser for r in s['rows']]
    ys += [r['y'] for r in sp.get('refs') or []] + list(sp.get('yticks') or [])
    if any(s.get('bars') for s in ser): ys.append(0)
    xa, xb = min(xs), max(xs); ya, yb = min(ys), max(ys); pad = (yb - ya) * 0.06 or 1; ya, yb = ya - pad, yb + pad
    pb = y1 - 70
    X = lambda x: x0 + (x - xa) / ((xb - xa) or 1) * (px1 - x0)
    Y = lambda y: pb - (y - ya) / ((yb - ya) or 1) * (pb - y0)
    tf = Fn['mono'](34, 500)
    for t in sp.get('yticks') or nice(ya, yb):
        d.line([x0, Y(t), px1, Y(t)], fill=LINE, width=2)
        d.text((px1 + 18, Y(t)), sp['yf'](t).replace('-', '−'), font=tf, fill=INK3, anchor='lm')
    xf = Fn['cjk'](32, 500) if lang == 'zh' else Fn['mono'](32, 500)
    for x, lz, le in sp['xticks']:
        xx = X(x); d.line([xx, pb, xx, pb + 14], fill=INK3, width=2)
        d.text((xx, pb + 24), lz if lang == 'zh' else le, font=xf, fill=INK3, anchor='mt')
    d.line([x0, pb, px1, pb], fill=INK, width=3)
    lab = Fn['cjk'](30, 700) if lang == 'zh' else Fn['mono'](30, 700)
    for r in sp.get('refs') or []:
        if r['y'] == 0 and not r.get('dash'): d.line([x0, Y(0), px1, Y(0)], fill=INK, width=3)
        else: dashed(d, x0, px1, Y(r['y']), r.get('color') or INK, 3)
        if r.get('label'): d.text((x0 + 8 + (px1 - x0) * r.get('lx', 0), Y(r['y']) - 10), r['label'][lang], font=lab, fill=r.get('color') or INK, anchor='lb')
    for s in ser:
        rows = s['rows']
        if s.get('bars'):
            bw = max(3, (px1 - x0) / ((xb - xa) or 1) * 7 * 0.9)
            for r in rows:
                c = UP if r[1] >= 0 else RED
                d.rectangle([X(r[0]) - bw / 2, min(Y(r[1]), Y(0)), X(r[0]) + bw / 2, max(Y(r[1]), Y(0))], fill=PK.tint(c, 0.8))
            continue
        pts = [(X(x), Y(y)) for x, y in rows]
        d.line(pts, fill=s['color'], width=s.get('width', 6), joint='curve')
        lx, ly = pts[-1]; rr = s.get('width', 6) + 6
        d.ellipse([lx - rr, ly - rr, lx + rr, ly + rr], fill=s['color'], outline=PK.PAPER, width=4)
        if s.get('end'):   # 線尾標籤
            d.text((lx + rr + 10, ly), s['end'][lang], font=lab, fill=s['color'], anchor='lm')


ORIG = PK.draw_line_chart
PK.draw_line_chart = draw


def pct(v): return ('+' if v >= 0 else '−') + f'{abs(v):.0f}%'


def c_analog(L):
    c = L['cycle']; rows = c['regime']['rows']; out = []
    cols = {'2015-01-14': (S3, T('2015', '2015')), '2018-12-15': (INK3, T('2019', '2019')),
            '2022-11-21': (S1, T('2023', '2023')), '2026-06-30': (RED, T('這輪', 'This cycle'))}
    at18 = {}
    for b, p in c['bottoms']:
        if b not in cols: continue
        x0 = dn(b); col, nm = cols[b]
        seg = [(0.0, 0.0)] + [((r[0] - x0) / 7, (r[2] / p - 1) * 100) for r in rows if 3 < r[0] - x0 <= 52 * 7]
        at18[b] = min(seg, key=lambda s: abs(s[0] - 18))
        out.append(dict(name=nm, rows=seg, color=col, width=10 if b == '2026-06-30' else 5))
    cur = out[-1]['rows'][-1]
    st = [S(f'這輪第 {cur[0]:.0f} 週', f'This cycle, week {cur[0]:.0f}', pct(cur[1])),
          S('2015 同期', '2015, same week', pct(at18['2015-01-14'][1])),
          S('2019／2023 同期', '2019 / 2023, same week', f'{pct(at18["2018-12-15"][1])} / {pct(at18["2022-11-21"][1])}', f'{pct(at18["2018-12-15"][1])} / {pct(at18["2022-11-21"][1])}')]
    return dict(kind='line', name=T('四輪對照：從週期低點起算', 'Four cycles, measured from the low'),
                sub=T('週線收盤相對週期低點的漲幅；低點：2015/01/14、2018/12/15、2022/11/21、2026/06/30', 'Weekly close vs. the cycle low; lows on Jan 14 2015, Dec 15 2018, Nov 21 2022, Jun 30 2026'),
                series=out, refs=[dict(y=0)], xticks=[(w, '低點' if w == 0 else f'{w} 週', 'Low' if w == 0 else f'wk {w}') for w in (0, 13, 26, 39, 52)],
                yticks=[0, 50, 100, 150, 200, 250], yf=lambda v: f'{v:+.0f}%' if v else '0%', src='CoinMetrics', asof=ds(rows[-1][0]), stats=st)


def c_regime(L):
    r = L['cycle']['regime']; rows = [(x[0], x[1]) for x in r['rows']]
    last_up = [f for f in r['flips'] if f['dir'] == 1 and f.get('weeks')][-1]
    return dict(kind='line', name=T('週線多空分數', 'Weekly regime score'),
                sub=T('六項週期指標各自對歷史中位數標準化後平均；綠＝多方、紅＝空方，連 4 週在另一邊才算翻轉', 'Six cycle inputs, each scaled to its own history and averaged; green = bull, red = bear; a flip needs 4 weeks on the other side'),
                series=[dict(name=T('分數', 'Score'), rows=rows, bars=True)], refs=[dict(y=0)], xticks=years(rows[0][0], rows[-1][0]),
                yf=lambda v: f'{v:+.0f}' if v else '0', src='Daybreak（CoinMetrics 等）', asof=r['date'],
                stats=[S(f'最新（{PK.md(r["date"], "zh")}）', f'Latest ({PK.md(r["date"], "en")})', f'{r["value"]:.2f}'),
                       S('翻多起', 'Bullish since', PK.md(r['since'], 'zh') + f'（{r["weeks"]} 週）', PK.md(r['since'], 'en') + f' ({r["weeks"]} wks)'),
                       S(f'上次翻多 {last_up["date"][:7].replace("-", "/")}', f'Last flip up {last_up["date"][:7]}', f'維持 {last_up["weeks"]} 週', f'{last_up["weeks"]} weeks')])


def c_powerlaw(L):
    p = L['cycle']['powerlaw']; rows = [(x[0], x[1]) for x in p['rows']]
    lg = math.log10; bl, bh = p['bottom_band']
    tops = '／'.join(f'{t[1]:g}' for t in p['tops'])
    return dict(kind='line', name=T('價格 ÷ 冪律趨勢價', 'Price ÷ power-law trend'),
                sub=T('對數刻度；1x＝長期趨勢價，歷次週期底部落在 0.24–0.48x', 'Log scale; 1x = the long-run trend price; past cycle lows fell between 0.24x and 0.48x'),
                series=[dict(name=T('倍數', 'Ratio'), rows=rows, color=S1, width=5)],
                refs=[dict(y=0, dash=True, label=T('1x 趨勢價', '1x trend')), dict(y=lg(bh), color=S3), dict(y=lg(bl), color=S3, lx=0.36, label=T(f'底部帶 {bl:g}–{bh:g}x', f'Bottom band {bl:g}–{bh:g}x'))],
                xticks=years(rows[0][0], rows[-1][0]), yticks=[lg(v) for v in (0.25, 0.5, 1, 2, 4, 8)],
                yf=lambda v: f'{10 ** v:.2g}x', src='CoinMetrics（Daybreak 擬合）', asof=p['date'],
                stats=[S(f'最新（{PK.md(p["date"], "zh")}）', f'Latest ({PK.md(p["date"], "en")})', f'{p["ratio"]:.2f}x'),
                       S('歷次底部', 'Past lows', f'{bl:g}–{bh:g}x'), S('歷次頂部', 'Past tops', tops.replace('／', '→') + 'x', tops.replace('／', '→') + 'x')])


# 每張圖：(檔名, 規格, 中文標題, 英文標題)；標題的數字都查得到（latest.json／notes.json）
def plan(L):
    end = dn(L['meta']['bar_date'])
    return [
        ('1-analog', c_analog(L), '第 18 週漲 31%，這輪走得跟 2015 年一樣慢', 'Week 18, up 31%: this cycle is moving as slowly as 2015'),
        ('2-regime', c_regime(L), '週線多空分數 9/21 翻多，0.88 仍偏弱', 'The weekly regime score flipped bullish on Sep 21, but 0.88 is still weak'),
        ('3-powerlaw', c_powerlaw(L), '價格只有冪律趨勢價的 0.53 倍，靠近歷史底部那一側', 'Price is 0.53x the power-law trend, closer to past lows than past tops'),
        ('4-cost', PK.c_cost(L, end), '收盤 77,332 還站在短期持有者成本之上', 'The 77,332 close still sits above the short-term holder cost basis'),
        ('5-rcliq', PK.c_generic(L, end, 'rcliq'), '實現市值連 72 天成長，只是越來越慢', 'Realized cap has grown for 72 straight days, just more slowly'),
        ('6-cbp', PK.c_cbp(L, end), 'Coinbase 溢價 7 日均 −0.19%，美國現貨不買', 'Coinbase premium 7-day avg −0.19%: US spot isn\'t buying'),
        ('7-lth', PK.c_generic(L, end, 'oc-lth-net-position-change-30d-btc'), '老手 30 天淨減持 149,737 顆', 'Long-term holders net sold 149,737 BTC in 30 days'),
        ('8-sopr', PK.c_sopr(L, end), 'STH-SOPR 連 5 天低於 1，短線買家在認賠', 'STH-SOPR below 1 for 5 days: short-term buyers are selling at a loss'),
    ]


COVER = {'zh': dict(title='牛到底來了沒？', sub=['從低點起算第 18 週 +31%', '和 2015 年一樣慢'], tag='長文', max=200),
         'en': dict(title='Is the bull actually here?', sub=['Week 18 from the low: +31%,', 'as slow as 2015'], tag='LONG READ', max=150)}


def cover(L, lang, Fn, out):
    """X 長文封面：5:2 橫圖（以 2 倍畫 3000×1200，存成 1500×600）。左邊標題、右邊四輪對照的線（同 c_analog）。"""
    from PIL import Image, ImageDraw
    import share_card as SC
    W2, H2, M2 = 3000, 1200, 150; C = COVER[lang]; sp = c_analog(L)
    img = Image.new('RGB', (W2, H2), PK.PAPER); d = ImageDraw.Draw(img)
    d.rectangle([M2, 110, W2 - M2, 122], fill=INK)
    # 左：標籤、標題、副標
    tf = Fn['cjk'](60, 900) if lang == 'zh' else Fn['mono'](54, 800)
    tw = d.textlength(C['tag'], font=tf); d.rectangle([M2, 180, M2 + tw + 64, 272], fill=RED); d.text((M2 + 32, 226), C['tag'], font=tf, fill='#FFFFFF', anchor='lm')
    bd = dt.date.fromisoformat(L['meta']['bar_date'])
    d.text((M2 + tw + 104, 226), f'DAYBREAK   {bd:%Y.%m.%d}' + (' 收盤數據' if lang == 'zh' else ' close data'), font=Fn['cjk'](44, 500) if lang == 'zh' else Fn['mono'](44, 500), fill=INK3, anchor='lm')
    lw = 1420
    for size in range(C['max'], 90, -6):
        hf = Fn['head'](size); lines = SC.wrap(C['title'], hf, lw)
        if len(lines) <= 2: break
    y = 330
    for ln in lines:
        x = M2
        for a, _ in ln: d.text((x, y), a, font=hf, fill=INK); x += hf.getlength(a)
        y += int(size * 1.22)
    sf = Fn['head'](78 if lang == 'zh' else 66); y += 30
    for s_ in C['sub']:
        x = M2
        for a, red in SC.atoms(s_): d.text((x, y), a, font=sf, fill=RED if red else INK); x += sf.getlength(a)
        y += 100
    # 右：四輪對照
    x0, y0, x1, y1 = 1720, 300, W2 - M2 - 170, 1000
    xs = [r[0] for s in sp['series'] for r in s['rows']]; ys = [r[1] for s in sp['series'] for r in s['rows']]
    xa, xb, ya, yb = 0, max(xs), min(ys + [0]) - 8, max(ys) + 8
    X = lambda v: x0 + (v - xa) / (xb - xa) * (x1 - x0); Y = lambda v: y1 - (v - ya) / (yb - ya) * (y1 - y0)
    af = Fn['mono'](36, 500)
    for t in (0, 100, 200):
        d.line([x0, Y(t), x1, Y(t)], fill=INK if t == 0 else LINE, width=3 if t == 0 else 2)
        d.text((x1 + 16, Y(t)), f'+{t}%' if t else '0%', font=af, fill=INK3, anchor='lm')
    for w in (0, 26, 52):
        lab = ('低點' if lang == 'zh' else 'Low') if w == 0 else (f'{w} 週' if lang == 'zh' else f'wk {w}')
        d.text((X(w), y1 + 24), lab, font=Fn['cjk'](36, 500) if lang == 'zh' else af, fill=INK3, anchor='mt')
    lf = Fn['cjk'](40, 900) if lang == 'zh' else Fn['mono'](38, 800)
    for s in sp['series']:
        pts = [(X(a), Y(b)) for a, b in s['rows']]; w = 12 if s['color'] == RED else 6
        d.line(pts, fill=s['color'], width=w, joint='curve')
        lx, ly = pts[-1]; r = w + 6; d.ellipse([lx - r, ly - r, lx + r, ly + r], fill=s['color'], outline=PK.PAPER, width=4)
        if s['color'] == RED:   # 只標這輪，墊紙色底
            bb = d.textbbox((lx, ly - r - 16), s['name'][lang], font=lf, anchor='mb'); d.rectangle([bb[0] - 8, bb[1] - 6, bb[2] + 8, bb[3] + 6], fill=PK.PAPER)
            d.text((lx, ly - r - 16), s['name'][lang], font=lf, fill=RED, anchor='mb')
    lx = x0   # 圖例（和標籤列同一行）
    for s in sp['series']:
        d.rectangle([lx, 220, lx + 48, 234], fill=s['color']); lx += 62
        d.text((lx, 227), s['name'][lang], font=lf, fill=INK, anchor='lm'); lx += d.textlength(s['name'][lang], font=lf) + 44
    # 頁尾
    fy = H2 - 90
    d.arc([M2, fy - 28, M2 + 56, fy + 28], 180, 360, fill=RED, width=8); d.line([M2 - 8, fy, M2 + 64, fy], fill=INK, width=8)
    d.text((M2 + 88, fy), '破曉 DAYBREAK' if lang == 'zh' else 'DAYBREAK', font=Fn['cjk'](42, 900) if lang == 'zh' else Fn['mono'](42, 800), fill=INK, anchor='lm')
    d.text((W2 - M2, fy), 'north7.github.io/daybreak   ·   X @songpu717', font=Fn['mono'](40), fill=INK3, anchor='rm')
    img.resize((W2 // 2, H2 // 2), Image.LANCZOS).save(out, optimize=True); print('wrote', os.path.relpath(out, ROOT))


if __name__ == '__main__':
    import share_card as SC
    ap = argparse.ArgumentParser(); ap.add_argument('--fonts', required=True); ap.add_argument('--out')
    a = ap.parse_args()
    L = json.load(open(os.path.join(ROOT, 'data', 'latest.json')))
    notes = {'zh': json.load(open(os.path.join(ROOT, 'data', 'notes.json'))), 'en': json.load(open(os.path.join(ROOT, 'data', 'notes.en.json')))}
    od = a.out or os.path.join(ROOT, 'ops', 'articles', 'img', dt.date.today().isoformat()); os.makedirs(od, exist_ok=True)
    Fn = SC.fonts(a.fonts)
    cover(L, 'zh', Fn, os.path.join(od, '0-cover.png')); cover(L, 'en', Fn, os.path.join(od, '0-cover-en.png'))
    for fid, sp, tz, te in plan(L):
        if not sp: print('skip', fid); continue
        for lang, title, fn in (('zh', tz, f'{fid}.png'), ('en', te, f'{fid}-en.png')):
            PK.card(L, notes[lang], sp, title, lang, Fn, os.path.join(od, fn), tag=TAG)
