#!/usr/bin/env python3
"""X 回覆配圖（2026-11-04 建立）：依 data/replies.json 裡每則回覆的 image 欄位出圖到 data/replies/<n>.png。
版面、字型、配色沿用 pipeline/picks.py 的「今日圖表」卡（1080×1350，X 不會裁切）；圖上的語言跟著回覆（en → 英文圖、zh → 中文圖）。
image 欄位：{"chart": "<picks.py 的圖表 id，例如 cbp、sopr、etf、cohort、cost>", "title": "<圖上的大標題>"}
           或 {"chart": "liq", "title": "...", "marks": [75000, 76200, ...]}：本站推算的清算價位分布（OKX），marks 是原文提到的價位。
需要 pipeline/picks.py（PR #19「每日推薦發文圖表」）與 Pillow；字型同 share_card.py。
用法（在倉庫根目錄）：python3 ops/replies/cards.py --fonts <字型資料夾>
只作讀值：圖只放市場資訊，不放出場框架。"""
import argparse, base64, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import picks as PK   # noqa: E402
from signals import g, T   # noqa: E402

OUT = os.path.join(ROOT, 'data', 'replies')


def k(v): return f'{v / 1000:.1f}K'.replace('.0K', 'K')


def c_liq(L, marks):
    h = g(L, 'deriv.liq_heat'); nb, lo, step, c = h['nb'], h['lo'], h['step'], h['close']
    raw = base64.b64decode(h['heat'])[-nb:]                     # 最後一個小時的分布（每 100 美元一格；超過 cap 的格子被截在 cap）
    rows = [(lo + j * step, raw[j] / 255 * h['cap']) for j in range(nb)]
    lb, ab = h['below'][0], h['above'][0]
    return dict(kind='liq', rows=rows, step=step, close=c, marks=marks or [],
                name=T('推算清算價位', 'Estimated liquidation levels'),
                sub=T('OKX 永續未平倉量＋假設 5–100 倍槓桿推算；每 100 美元一格的顆數；不是實際倉位',
                      'From OKX perpetual open interest with assumed 5–100x leverage; BTC per $100 bucket; a model, not actual positions'),
                series=[dict(name=T('多單清算', 'Long liquidations'), color=PK.S2), dict(name=T('空單清算', 'Short liquidations'), color=PK.S1)]
                       + ([dict(name=T('原文價位', 'Levels in the post'), color=PK.INK)] if marks else []),
                src='OKX（推算）', asof=h['asof'][:10],
                stats=[PK.S('下方 5% 內多單', 'Longs within 5% below', f'{h["within5"]["below"]:,} 顆', f'{h["within5"]["below"]:,} BTC'),
                       PK.S('上方 5% 內空單', 'Shorts within 5% above', f'{h["within5"]["above"]:,} 顆', f'{h["within5"]["above"]:,} BTC'),
                       PK.S('最大多單帶', 'Largest long band', f'{k(lb["lo"])}–{k(lb["hi"])}')])


def vdash(d, x, y0, y1, color, w=3, dash=16, gap=12):
    y = y0
    while y < y1:
        d.line([x, y, x, min(y + dash, y1)], fill=color, width=w); y += dash + gap


def draw_liq(d, box, sp, lang, Fn):
    x0, y0, x1, y1 = box; px1 = x1 - 150; top = y0 + 120; pb = y1 - 70   # 上方留給價位標籤，下方留給 x 軸
    rows, step, c = sp['rows'], sp['step'], sp['close']
    xa, xb = rows[0][0], rows[-1][0] + step; ymax = max(v for _, v in rows) * 1.08 or 1
    X = lambda p: x0 + (p - xa) / (xb - xa) * (px1 - x0)
    Y = lambda v: pb - v / ymax * (pb - top)
    tf = Fn['mono'](34, 500)
    for t in PK.nice(0, ymax):
        d.line([x0, Y(t), px1, Y(t)], fill=PK.LINE, width=2)
        d.text((px1 + 18, Y(t)), f'{t:,.0f}', font=tf, fill=PK.INK3, anchor='lm')
    bw = (px1 - x0) / len(rows)
    for p, v in rows:
        if v <= 0 or p < c < p + step: continue
        col = PK.S2 if p + step <= c else PK.S1
        d.rectangle([X(p) + 1, Y(v), X(p) + bw - 1, pb], fill=col)
    d.line([x0, pb, px1, pb], fill=PK.INK, width=3)
    p = (int(xa) // 2000 + 1) * 2000
    while p < xb:
        d.line([X(p), pb, X(p), pb + 14], fill=PK.INK3, width=2)
        d.text((X(p), pb + 24), f'{p // 1000}K', font=Fn['mono'](32, 500), fill=PK.INK3, anchor='mt'); p += 2000
    lf = Fn['mono'](30, 800); labs = []
    for i, m in enumerate(sorted(sp['marks'])):
        if not xa <= m <= xb: continue
        vdash(d, X(m), top, pb, PK.INK, 3)
        labs.append((X(m), top - 14 - (i % 2) * 44, k(m)))
    d.line([X(c), top - 20, X(c), pb], fill=PK.RED, width=5)
    for x, y, t in labs:
        bb = d.textbbox((x, y), t, font=lf, anchor='mb'); d.rectangle([bb[0] - 6, bb[1] - 4, bb[2] + 6, bb[3] + 4], fill=PK.PAPER)
        d.text((x, y), t, font=lf, fill=PK.INK, anchor='mb')
    cl = f'收盤 {PK.usd(c)}' if lang == 'zh' else f'Close {PK.usd(c)}'
    d.text((X(c) + 14, pb - (pb - top) * 0.55), cl, font=Fn['cjk'](34, 900) if lang == 'zh' else Fn['mono'](32, 800), fill=PK.RED, anchor='lm')


_line = PK.draw_line_chart
PK.draw_line_chart = lambda d, box, sp, lang, Fn: (draw_liq if sp.get('kind') == 'liq' else _line)(d, box, sp, lang, Fn)


def main(fonts_dir):
    import share_card as SC
    Fn = SC.fonts(fonts_dir)
    L = json.load(open(os.path.join(ROOT, 'data', 'latest.json')))
    rp = json.load(open(os.path.join(ROOT, 'data', 'replies.json')))
    rd = lambda f: json.load(open(os.path.join(ROOT, 'data', f))) if os.path.exists(os.path.join(ROOT, 'data', f)) else None
    notes = {'zh': rd('notes.json'), 'en': rd('notes.en.json')}
    os.makedirs(OUT, exist_ok=True); keep = set()
    for it in rp['items']:
        im = it.get('image')
        if not im: continue
        lang = 'zh' if it['lang'] == 'zh' else 'en'
        sp = c_liq(L, im.get('marks')) if im['chart'] == 'liq' else PK.spec(L, im['chart'])
        if not sp: print('skip', it['n'], im['chart'], '（沒有這張圖或資料不足）'); continue
        fn = f'{it["n"]}.png'
        PK.card(L, notes[lang], sp, im['title'], lang, Fn, os.path.join(OUT, fn)); keep.add(fn)
    for fn in os.listdir(OUT):   # 清掉前一天的圖
        if fn not in keep: os.remove(os.path.join(OUT, fn)); print('removed', fn)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--fonts', required=True)
    main(ap.parse_args().fonts)
