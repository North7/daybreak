"""回覆配圖：直接截網站原圖（2026-11-05 使用者要求「多用新圖、儘量用網站原圖」）。
data/replies.json 裡 image 帶 "site" 的，用本機 Chrome 無頭模式開本機網站檔案，截那張圖的面板，
上方加圖片大標題（image.title）、下方加破曉頁尾，存成 data/replies/<n>.png。沒有 site 的照舊由 cards.py 畫。
依賴 ops/post/site_shot.py（開 Chrome、本機伺服器、截圖流程）與 pipeline/share_card.py（字型）。

image 範例：
  {"site": {"page": "onchain", "sel": "#c-sthband"}, "title": "……"}
  {"site": {"page": "cycle", "sel": "#c-ev-tmm", "box": ".evc", "pre": "document.querySelector('.ev-open').click()"}, "title": "……"}
  page：網站分頁（overview／onchain／cycle／market／flows／deriv）；sel：圖表容器；
  box：要截的外框（sel 往上找最近的這個選擇器，預設 section.panel）；pre：截圖前要跑的 JS（例如展開收合區）；
  keep_note：true 時保留面板裡的解讀文字（預設藏掉解讀、表格、說明、按鈕，只留標題列、圖例、圖）。
語言跟回覆一樣（zh 回覆截中文版、en 截英文版），深色主題。
usage（倉庫根目錄）: python3 ops/replies/site_cards.py --fonts <字型資料夾> [--only 3,7]
"""
import argparse, io, json, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'ops', 'post')); sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import site_shot as SS
from PIL import Image, ImageDraw

OUT = os.path.join(ROOT, 'data', 'replies')
CLEAN = '''(function(p, keep){
  p.querySelectorAll((keep ? "" : ".interp,#ac-say,p.note,") + ".rd,.tbl-wrap").forEach(function(e){e.style.display="none";});
  p.querySelectorAll("button").forEach(function(b){b.style.visibility="hidden"; var q=b.parentElement; if(Array.prototype.every.call(q.children,function(c){return c.tagName==="BUTTON";})) q.style.visibility="hidden";});
  p.querySelectorAll(".panel-h a").forEach(function(a){if(a.textContent.trim()==="#")a.style.visibility="hidden";});
  return true;})'''


def shoot(items, lang, tmp, mobile=True):
    """items: [(n, site)]，回傳 {n: PNG bytes}。mobile（2026-11-08 預設）：用手機寬度 430、3 倍解析度截網站的手機版圖，
    字和圖例相對變大，X 在手機上看得清楚；--desktop 回到 1440 寬、2 倍。
    2026-11-10：開 Chrome、換頁、截圖改用 site_shot.py 的共用流程（browser／goto／ready／shoot）：不用 captureBeyondViewport
    （桌面寬度會讓網站暫時切成手機版重排，截到別張或空白），先捲到底等版面穩定、連量兩次位置一樣才截、截完再確認。"""
    W = 430 if mobile else 1440; DPR = 3 if mobile else 2; got = {}
    with SS.browser(W, 932 if mobile else 1000, dpr=DPR, mobile=mobile, theme='dark', lang=lang) as (ws, view):
        for n, st in items:   # 每張重新載入，前一張的 pre／clean 不會留下來
            SS.goto(ws, st['page'])
            sel = json.dumps(st['sel']); box = st.get('box', 'section.panel')
            if not SS.wait(ws, f'(function(){{var e=document.querySelector({sel}); return !!(e && (e.querySelector("svg,canvas") || e.children.length));}})()', 40):
                print('MISSING', n, st['sel']); continue
            SS.ready(ws, st['sel'])
            if st.get('pre'): ws.js(st['pre']); time.sleep(1.2)
            ws.js(f'{CLEAN}(document.querySelector({sel}).closest({json.dumps(box)}), {json.dumps(bool(st.get("keep_note")))})'); time.sleep(0.6)
            # 描線動畫（.chart .draw）直接跑完，不要截到畫到一半的線（2026-11-05「本地數據分析」查到 .more 小圖只截到第 0 幀）
            ws.js("document.querySelectorAll('.chart .draw').forEach(function(p){p.classList.remove('draw')}); document.getAnimations().forEach(function(a){try{a.finish();}catch(e){}}); true"); time.sleep(0.3)
            png, *rest = SS.shoot(ws, st['sel'], view, crop='chart', box=box)
            if png is None: print('ERROR', n, st['sel'], rest[0]); continue
            c = rest[0]
            if c['height'] < 80: print('TOO SMALL', n, st['sel'], c); continue
            got[n] = png; print('shot', n, lang, st['page'], st['sel'], round(c['width']), 'x', round(c['height']))
    return got


def compose(png, title, lang, Fn, out, mobile=True):
    """上：大標題；中：網站截圖；下：破曉頁尾。手機版輸出寬 1080（直式），桌面版 1600。"""
    RED, INK, INK3, LINE = '#FF3B1F', '#F2F0EA', '#9C978E', '#3A3936'
    im = Image.open(io.BytesIO(png)).convert('RGB'); bg = im.getpixel((im.width // 2, 8))
    P = 72; W = (im.width + 2 * P) if mobile else max(im.width + 2 * P, 2200); tf = Fn['cjk'](64 if not mobile else 66, 900)   # 窄面板（半寬圖）也撐到 2200，標題和頁尾才放得下；圖置中
    d0 = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    import re
    lines, cur = [], ''   # 標題太長就斷行：中文逐字、英數整詞
    for tok in re.findall(r'[A-Za-z0-9$.,%:+\-−–’\']+\s*|\s+|.', title):
        if cur and d0.textlength(cur + tok.rstrip(), font=tf) > W - 2 * P: lines.append(cur.rstrip()); cur = tok.lstrip()
        else: cur += tok
    lines.append(cur.rstrip()); lh = 88; TOP = 64 + lh * len(lines) + 36; FOOT = 150
    img = Image.new('RGB', (W, TOP + im.height + FOOT), bg); d = ImageDraw.Draw(img)
    d.rectangle([P, 40, P + 90, 48], fill=RED)
    for i, t in enumerate(lines): d.text((P, 64 + i * lh + lh / 2), t, font=tf, fill=INK, anchor='lm')
    img.paste(im, ((W - im.width) // 2, TOP))
    fy = img.height - 70; d.line([P, fy - 52, W - P, fy - 52], fill=LINE, width=2)
    d.arc([P, fy - 26, P + 52, fy + 26], 180, 360, fill=RED, width=8); d.line([P - 8, fy, P + 60, fy], fill=INK, width=8)
    d.text((P + 84, fy), '破曉 DAYBREAK' if lang == 'zh' else 'DAYBREAK', font=Fn['cjk'](38, 900), fill=INK, anchor='lm')
    d.text((W - P, fy), 'X @songpu717', font=Fn['mono'](30 if mobile else 34), fill=INK3, anchor='rm')
    w = 1080 if mobile else 1600; img = img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
    img.save(out, optimize=True); print('wrote', out, img.size)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--fonts', required=True); ap.add_argument('--only', default='')
    ap.add_argument('--desktop', action='store_true', help='用桌面寬度截（2026-11-08 前的做法）'); ap.add_argument('--out', default=OUT, help='輸出資料夾（試圖用）')
    a = ap.parse_args()
    import share_card as SC
    Fn = SC.fonts(a.fonts); only = {int(x) for x in a.only.split(',') if x}
    rp = json.load(open(os.path.join(ROOT, 'data', 'replies.json'))); os.makedirs(OUT, exist_ok=True)
    todo = {'zh': [], 'en': []}; meta = {}
    for it in rp['items']:
        im = it.get('image') or {}
        if not im.get('site') or (only and it['n'] not in only): continue
        lang = 'zh' if it['lang'] == 'zh' else 'en'
        todo[lang].append((it['n'], im['site'])); meta[it['n']] = (im['title'], lang)
    for lang, items in todo.items():
        if not items: continue
        for n, png in shoot(items, lang, None, mobile=not a.desktop).items():
            compose(png, meta[n][0], lang, Fn, os.path.join(a.out, f'{n}.png'), mobile=not a.desktop)


if __name__ == '__main__':
    main()
