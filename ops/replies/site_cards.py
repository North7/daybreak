"""回覆配圖：直接截網站原圖（2026-11-05 使用者要求「多用新圖、儘量用網站原圖」）。
data/replies.json 裡 image 帶 "site" 的，用本機 Chrome 無頭模式開本機網站檔案，截那張圖的面板，
上方加圖片大標題（image.title）、下方加破曉頁尾，存成 data/replies/<n>.png。沒有 site 的照舊由 cards.py 畫。
依賴 ops/post/site_shot.py（WebSocket、本機伺服器）與 pipeline/share_card.py（字型）。

image 範例：
  {"site": {"page": "onchain", "sel": "#c-sthband"}, "title": "……"}
  {"site": {"page": "cycle", "sel": "#c-ev-tmm", "box": ".evc", "pre": "document.querySelector('.ev-open').click()"}, "title": "……"}
  page：網站分頁（overview／onchain／cycle／market／flows／deriv）；sel：圖表容器；
  box：要截的外框（sel 往上找最近的這個選擇器，預設 section.panel）；pre：截圖前要跑的 JS（例如展開收合區）；
  keep_note：true 時保留面板裡的解讀文字（預設藏掉解讀、表格、說明、按鈕，只留標題列、圖例、圖）。
語言跟回覆一樣（zh 回覆截中文版、en 截英文版），深色主題。
usage（倉庫根目錄）: python3 ops/replies/site_cards.py --fonts <字型資料夾> [--only 3,7]
"""
import argparse, base64, io, json, os, subprocess, sys, tempfile, time, urllib.request

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


def shoot(items, lang, tmp):
    """items: [(n, site)]，回傳 {n: PNG bytes}（2 倍解析度）。"""
    srv = SS.serve(); prof = tempfile.mkdtemp(prefix='daybreak-chrome-'); W = 1440; got = {}
    p = subprocess.Popen([SS.CHROME, '--headless=new', f'--remote-debugging-port={SS.PORT}', f'--user-data-dir={prof}', '--hide-scrollbars',
                          '--no-first-run', '--no-default-browser-check', f'--window-size={W},1000', 'about:blank'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try: tg = json.load(urllib.request.urlopen(f'http://127.0.0.1:{SS.PORT}/json')); break
            except Exception: time.sleep(0.2)
        ws = SS.WS(next(t for t in tg if t['type'] == 'page')['webSocketDebuggerUrl'])
        ws.call('Page.enable'); ws.call('Runtime.enable')
        ws.call('Emulation.setDeviceMetricsOverride', width=W, height=1000, deviceScaleFactor=2, mobile=False)
        ws.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': 'dark'}])
        ws.call('Page.navigate', url=SS.SITE); SS.wait(ws, 'document.readyState === "complete"')
        ws.js(f"localStorage.setItem('daybreak.lang', '{lang}'); localStorage.setItem('daybreak.theme', 'dark'); localStorage.setItem('daybreak.nohold', '1'); true")   # nohold：判讀撰寫中也截最新數字（2026-11-06）
        for n, st in items:   # 每張重新載入，前一張的 pre／clean 不會留下來
            ws.js('window.__old = 1; true')
            ws.call('Page.navigate', url=SS.SITE + '?v=' + str(int(time.time() * 1000)) + '#' + st['page'])
            SS.wait(ws, '!window.__old'); SS.wait(ws, 'document.readyState === "complete"'); time.sleep(1.0)
            sel = json.dumps(st['sel']); box = json.dumps(st.get('box', 'section.panel'))
            if not SS.wait(ws, f'(function(){{var e=document.querySelector({sel}); return !!(e && (e.querySelector("svg,canvas") || e.children.length));}})()', 40):
                print('MISSING', n, st['sel']); continue
            if st.get('pre'): ws.js(st['pre']); time.sleep(1.2)
            ws.js(f'{CLEAN}(document.querySelector({sel}).closest({box}), {json.dumps(bool(st.get("keep_note")))})'); time.sleep(0.6)
            ws.js(f'document.querySelector({sel}).closest({box}).scrollIntoView({{block:"start"}}); true'); time.sleep(1.2)
            # 拿掉描線動畫：captureBeyondViewport 會暫時改視窗大小，.more 小圖的描線動畫會重播，只截到第 0 幀（2026-11-05「本地數據分析」查到）
            ws.js("document.querySelectorAll('.chart .draw').forEach(function(p){p.classList.remove('draw')}); document.getAnimations().forEach(function(a){try{a.finish();}catch(e){}}); true"); time.sleep(0.3)
            r = ws.js(f'''(function(){{var c=document.querySelector({sel}), p=c.closest({box}), b=p.getBoundingClientRect(), cr=c.getBoundingClientRect();
                return {{x:b.left+scrollX, y:b.top+scrollY, w:b.width, h:cr.bottom-b.top+16}};}})()''')
            if r['h'] < 80: print('TOO SMALL', n, st['sel'], r); continue
            shot = ws.call('Page.captureScreenshot', format='png', captureBeyondViewport=True,
                           clip=dict(x=r['x'], y=r['y'], width=r['w'], height=r['h'], scale=1))
            got[n] = base64.b64decode(shot['data']); print('shot', n, lang, st['page'], st['sel'], round(r['w']), 'x', round(r['h']))
    finally:
        p.terminate(); srv.shutdown()
    return got


def compose(png, title, lang, Fn, out):
    """上：大標題；中：網站截圖；下：破曉頁尾。輸出寬 1600。"""
    RED, INK, INK3, LINE = '#FF3B1F', '#F2F0EA', '#9C978E', '#3A3936'
    im = Image.open(io.BytesIO(png)).convert('RGB'); bg = im.getpixel((im.width // 2, 8))
    P = 72; W = max(im.width + 2 * P, 2200); tf = Fn['cjk'](64, 900)   # 窄面板（半寬圖）也撐到 2200，標題和頁尾才放得下；圖置中
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
    d.text((W - P, fy), 'north7.github.io/daybreak   ·   X @songpu717', font=Fn['mono'](34), fill=INK3, anchor='rm')
    w = 1600; img = img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
    img.save(out, optimize=True); print('wrote', out, img.size)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--fonts', required=True); ap.add_argument('--only', default='')
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
        for n, png in shoot(items, lang, None).items():
            compose(png, meta[n][0], lang, Fn, os.path.join(OUT, f'{n}.png'))


if __name__ == '__main__':
    main()
