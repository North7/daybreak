"""回覆配圖：直接截網站原圖（2026-11-05 使用者要求「多用新圖、儘量用網站原圖」）。
data/replies.json 裡 image 帶 "site" 的，用本機 Chrome 無頭模式開本機網站檔案，截那張圖的面板，
上方加圖片大標題（image.title）、下方加 Daybreak 頁尾，存成 data/replies/<n>.png。沒有 site 的照舊由 cards.py 畫。
依賴 ops/post/site_shot.py（開 Chrome、本機伺服器、截圖流程）與 pipeline/share_card.py（字型）。

image 範例：
  {"site": {"page": "onchain", "sel": "#c-sthband"}, "title": "……"}
  {"site": {"page": "cycle", "sel": "#c-ev-tmm", "box": ".evc", "pre": "document.querySelector('.ev-open').click()"}, "title": "……"}
  page：網站分頁（overview／onchain／cycle／market／flows／deriv）；sel：圖表容器；
  box：要截的外框（sel 往上找最近的這個選擇器，預設 section.panel）；pre：截圖前要跑的 JS（例如展開收合區）；
  keep_note：true 時保留面板裡的解讀文字（預設藏掉解讀、表格、說明、按鈕，只留標題列、圖例、圖）。
語言跟回覆一樣（zh 回覆截中文版、en 截英文版），深色主題。

2026-11-16 起改截新版首頁（舊版 classic.html 已不部署，North7/daybreak#182）：
  {"site": {"k": "sthgap"}, "title": "……"}                 新寫法：k 是新版圖代號（python3 ops/post/next_shot.py --list 查）
  {"site": {"k": "profit", "m": 1, "rg": 365}, "title": "…"}  m＝第幾個檢視、rg＝區間（365／1095／0），同 next_shot.py
  舊寫法（page＋sel）照樣能用：sel 會用 data/next.js 的 old 對照表自動換成新版代號（#c-sthband → sthgap）。
  對不到新版的（例如 #c-etfcost）、或帶了 pre／box 的（舊版才有的收合區），還是截舊版，並印「仍截舊版」；舊版從倉庫拿掉之前要把這些換掉。
  新版用網站的分享模式 4:5 截（next_shot.py 的 share45），上面加大標題，整張最高 1080×1350；頁尾是網站自己的（Daybreak、網址、資料來源、日期）。
  2026-11-20：比 4:5 矮的卡片（例如 whstrip），網站會把內容和頁尾排在上面、下面整片空白；合成時把頁尾以下的空白裁掉，只留 BOTTOM 那段邊距，不再補成 1350。
  （2026-11-17 舊版 classic.html 已從倉庫刪除，--classic 退路拿掉了。）
usage（倉庫根目錄）: python3 ops/replies/site_cards.py --fonts <字型資料夾> [--only 3,7]
"""
import argparse, io, json, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'ops', 'post')); sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import site_shot as SS
import next_shot as NS
from PIL import Image, ImageChops, ImageDraw

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


def old_map():
    """舊版面板代號 → 新版圖代號（data/next.js 的 old 欄位，網站每天重建）"""
    try:
        t = open(os.path.join(ROOT, 'data', 'next.js'), encoding='utf-8').read()
        return json.loads(t[t.index('{'):t.rindex('}') + 1]).get('old') or {}
    except Exception as e:
        print('注意：讀不到 data/next.js 的 old 對照表，全部照舊截舊版', e); return {}


def resolve(st, old=None):
    """image.site → 新版圖代號；回 None 表示只能截舊版（對不到新版，或用了舊版才有的 pre／box）"""
    if st.get('k'): return st['k']
    if st.get('pre') or st.get('box'): return None
    return (old_map() if old is None else old).get(str(st.get('sel', '')).replace('#c-', ''))


TITLE_PX, TITLE_LH, TITLE_TOP, TITLE_GAP, PAD = 100, 132, 64, 40, 44   # 2 倍解析度下的標題字級、行高、上下留白、左右邊距（對齊分享圖自己的邊距）


def title_layout(title, Fn, W=2160):
    """標題怎麼排：回傳 (每行文字, 字型, 標題那一段的高度, 左邊距)，都是 2 倍解析度的像素。
    分享圖在比 1350 矮的視窗裡會維持 4:5、左右留邊置中，所以標題的左邊距要跟著圖的內容對齊；邊距變大可能多折一行，算兩三輪到穩定。"""
    import re
    tf = Fn['cjk'](TITLE_PX, 900); d0 = ImageDraw.Draw(Image.new('RGB', (10, 10))); pad = PAD
    for _ in range(4):
        lines, cur = [], ''   # 標題太長就斷行：中文逐字、英數整詞
        for tok in re.findall(r'[A-Za-z0-9$.,%:+\-−–’\']+\s*|\s+|.', title):
            if cur and d0.textlength(cur + tok.rstrip(), font=tf) > W - 2 * pad: lines.append(cur.rstrip()); cur = tok.lstrip()
            else: cur += tok
        lines.append(cur.rstrip()); band = TITLE_TOP + TITLE_LH * len(lines) + TITLE_GAP
        sc = (2700 - band) / 2700; p2 = round(W * (1 - sc) / 2 + PAD * sc)
        if p2 == pad: break
        pad = p2
    return lines, tf, band, pad


def shoot_next(items, lang, Fn):
    """items: [(n, k, site, title)]，回傳 {n: PNG bytes}。新版首頁的分享模式 4:5；視窗高度先扣掉標題那一段，加上標題後整張是 1080×1350。"""
    cat = NS.catalog(); got = {}; classic = SS.SITE
    SS.SITE = NS.SITE
    try:
        with SS.browser(1440, H=1000, theme='dark', lang=lang) as (ws, view):
            ws.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': 'dark'}, {'name': 'prefers-reduced-motion', 'value': 'reduce'}])
            for n, k, st, title in items:
                c = cat.get(k)
                why = ('data/next.js 裡沒有這個代號（next_shot.py --list 可查）' if not c else '出場框架的卡片不截' if NS.BLOCK(c['ch_id'], k)
                       else '這張卡片目前沒有資料' if c['na'] else '這張卡片不能放大' if not c['fx'] else '')
                if why: print('ERROR', n, k, why); continue
                band = title_layout(title, Fn)[2]
                it = dict(view='share45', h=1350 - round(band / 2), **{a: st[a] for a in ('m', 'rg', 'ly', 'd3', 'nosay') if a in st})
                png, why = NS.shoot_share(ws, view, k, it)
                if png is None: print('ERROR', n, k, why); continue
                got[n] = png; print('shot', n, lang, k, why)
    finally:
        SS.SITE = classic
    return got


BOTTOM = 72   # 2 倍解析度：頁尾文字下面留的邊距（約 36px）


def trim_bottom(im, bg, tol=10):
    """把截圖最下面一段純底色裁掉，留 BOTTOM 的邊距；省不到 BOTTOM 的（卡片本來就排滿）原樣回傳。"""
    diff = ImageChops.difference(im, Image.new('RGB', im.size, bg)).convert('L').point(lambda v: 255 if v > tol else 0)
    box = diff.getbbox()
    if not box: return im
    keep = min(im.height, box[3] + BOTTOM)
    return im.crop((0, 0, im.width, keep)) if im.height - keep >= BOTTOM else im


def compose_next(png, title, Fn, out):
    """上：紅色短線＋大標題；下：網站分享圖（已經有 Daybreak、網址、資料來源的頁尾）。輸出 1080 寬。"""
    RED, INK = '#FF3B1F', '#F2F0EA'
    im = Image.open(io.BytesIO(png)).convert('RGB'); bg = im.getpixel((8, 8)); lines, tf, band, pad = title_layout(title, Fn, im.width)
    im = trim_bottom(im, bg)
    img = Image.new('RGB', (im.width, band + im.height), bg); d = ImageDraw.Draw(img)
    d.rectangle([pad, 36, pad + 110, 46], fill=RED)
    for i, t in enumerate(lines): d.text((pad, TITLE_TOP + i * TITLE_LH + TITLE_LH / 2), t, font=tf, fill=INK, anchor='lm')
    img.paste(im, (0, band))
    img = img.resize((1080, round(img.height * 1080 / img.width)), Image.LANCZOS)
    img.save(out, optimize=True); print('wrote', out, img.size)


def compose(png, title, lang, Fn, out, mobile=True):
    """上：大標題；中：網站截圖；下：Daybreak 頁尾。手機版輸出寬 1080（直式），桌面版 1600。"""
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
    d.text((P + 84, fy), 'DAYBREAK', font=Fn['cjk'](38, 900), fill=INK, anchor='lm')   # 2026-11-12 使用者：中文也不寫「破曉」
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
    todo = {'zh': [], 'en': []}; new = {'zh': [], 'en': []}; meta = {}; old = old_map(); want = set()
    for it in rp['items']:
        im = it.get('image') or {}
        if not im.get('site') or (only and it['n'] not in only): continue
        lang = 'zh' if it['lang'] == 'zh' else 'en'; st = im['site']; k = resolve(st, old); want.add(it['n'])
        if k: new[lang].append((it['n'], k, st, im['title']))
        else:   # 2026-11-17 舊版 classic.html 已刪除，沒有對應新版代號的不能截
            print('ERROR', it['n'], st.get('sel') or st.get('k'), '新版沒有對應的圖（用 python3 ops/post/next_shot.py --list 查代號，寫成 {"k": …}）'); continue
        meta[it['n']] = (im['title'], lang)
    done = set()
    for lang, items in new.items():
        if not items: continue
        for n, png in shoot_next(items, lang, Fn).items():
            compose_next(png, meta[n][0], Fn, os.path.join(a.out, f'{n}.png')); done.add(n)
    for lang, items in todo.items():
        if not items: continue
        for n, png in shoot(items, lang, None, mobile=not a.desktop).items():
            compose(png, meta[n][0], lang, Fn, os.path.join(a.out, f'{n}.png'), mobile=not a.desktop); done.add(n)
    if want - done: print('ERROR 沒截成：', ', '.join(f'#{n}' for n in sorted(want - done))); sys.exit(1)


if __name__ == '__main__':
    main()
