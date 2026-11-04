#!/usr/bin/env python3
"""快訊配圖（2026-11-04 建立）：依 data/flash.json 每則快訊的 image 出圖到 data/flash/<id>-zh.png、<id>-en.png（只出有文字的語言）。
版面與圖表沿用 ops/replies/cards.py（picks.py 的卡片）；image 欄位同回覆配圖，另外：
  title_zh／title_en：中英文圖的大標題；stats：覆寫底部三格 [{"zh_label", "en_label", "zh", "en"}]（例如換成盤中低點）。
用法（在倉庫根目錄）：python3 ops/post/flash.py --fonts <字型資料夾>
只作讀值：快訊只放市場資訊，不放出場框架或買賣建議。"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'ops', 'replies'))
import cards as C   # noqa: E402

OUT = os.path.join(ROOT, 'data', 'flash')


def main(fonts_dir):
    import share_card as SC
    Fn = SC.fonts(fonts_dir)
    rd = lambda f: json.load(open(os.path.join(ROOT, 'data', f), encoding='utf-8'))
    L, fl = rd('latest.json'), rd('flash.json')
    notes = {'zh': rd('notes.json'), 'en': rd('notes.en.json')}
    os.makedirs(OUT, exist_ok=True); keep = set()
    for it in fl.get('items', []):
        im = it.get('image')
        if not im: continue
        sp = C.build_spec(L, im)
        if not sp: print('skip', it['id'], im['chart'], '（沒有這張圖或資料不足）'); continue
        for lang in ('zh', 'en'):
            if not it.get(lang): continue
            fn = f'{it["id"]}-{lang}.png'
            C.PK.card(L, notes[lang], sp, im.get(f'title_{lang}') or sp['name'][lang], lang, Fn, os.path.join(OUT, fn)); keep.add(fn)
    for fn in os.listdir(OUT):   # 清掉已經不在 flash.json 裡的圖
        if fn not in keep: os.remove(os.path.join(OUT, fn)); print('removed', fn)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--fonts', required=True)
    main(ap.parse_args().fonts)
