"""網站圖表截圖（2026-11-05 建立）：用本機 Chrome 無頭模式開「本機的網站檔案」（內建小伺服器，127.0.0.1:8790），
截指定圖表面板成 PNG，同時存一份圖上文字的位置（刻度、標籤）給 annotate.py 換算座標。只用 Python 標準函式庫（自帶最小 WebSocket）。
發文配圖用：clean=1 會藏掉解讀、表格、說明、按鈕，只留標題列、圖例、圖；theme 用 dark（2026-11-05 使用者選深色）。
usage（倉庫根目錄）: python3 ops/post/site_shot.py <jobs.json> <輸出資料夾>
jobs.json: {"lang": "zh"|"en", "theme": "dark"|"light", "width": 1440,
            "items": [{"page": "onchain", "sel": "#c-lthloss", "out": "b1-lthloss-dark", "clean": 1, "pre": "<等動畫跑完的 js>"}]}
輸出：<out>.png（2 倍解析度）與 <out>.json（圖上文字位置，CSS px）
有任何一張沒截成（找不到圖、量到高度 0、位置一直在動）就印 ERROR、不寫那張的檔案，最後結束碼 1。

2026-11-09 桌面寬度偶爾截錯位置或整片空白，查到兩個原因：
  ① 網站桌面版延後畫圖（drawUpTo／drawAhead／drawIdle），其餘的版捲近或閒置時才補畫，版面會長高；
  ② 原本用 captureBeyondViewport 截圖，Chrome 截圖時會把視窗暫時縮成 1×1 再還原——網站當成跨過 860px，
     切到手機版（捲回頂端、只顯示一版、圖用窄寬度重畫）再切回來，截圖和版面重排在賽跑，所以截到別張、截到窄圖或空白。
  改成：每張先捲到底等版面高度穩定（settle）→ 捲到目標、連量兩次位置一樣才截 → 只截畫面內（不用 captureBeyondViewport；
  面板比視窗高就只加高視窗，寬度不變）→ 截完再量一次，位置變了就重截。畫面上壓到截圖範圍的固定／黏住的元素（手機頂欄、換頁掃描線）截圖時先藏起來。
"""
import base64, contextlib, json, os, socket, struct, subprocess, sys, tempfile, time, urllib.request

import shutil
# 2026-11-06：GitHub Actions（ubuntu）也要能截圖（每日推薦圖表改用網站原圖）：先看環境變數 CHROME，再找 Mac 的 Chrome，再找 Linux 的 google-chrome／chromium
CHROME = os.environ.get('CHROME') or next((c for c in ('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',) if os.path.exists(c)), None) \
    or shutil.which('google-chrome') or shutil.which('google-chrome-stable') or shutil.which('chromium') or shutil.which('chromium-browser') \
    or '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
PORT = 9333
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # 倉庫根目錄（本機的網站檔案）
SITE = 'http://127.0.0.1:8790/'


class WS:
    def __init__(self, url):
        assert url.startswith('ws://'); rest = url[5:]; hostport, path = rest.split('/', 1)
        host, port = hostport.split(':')
        self.s = socket.create_connection((host, int(port)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f'GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                        f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        buf = b''
        while b'\r\n\r\n' not in buf: buf += self.s.recv(4096)
        head, self.buf = buf.split(b'\r\n\r\n', 1)
        assert b' 101 ' in head.split(b'\r\n')[0], head
        self.id = 0

    def _read(self, n):
        while len(self.buf) < n:
            c = self.s.recv(1 << 20)
            if not c: raise EOFError
            self.buf += c
        out, self.buf = self.buf[:n], self.buf[n:]; return out

    def send(self, obj):
        data = json.dumps(obj).encode(); mask = os.urandom(4); n = len(data)
        hdr = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack('>H', n) if n < 65536 else bytes([0x80 | 127]) + struct.pack('>Q', n))
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        msg = b''
        while True:
            b0, b1 = self._read(2); n = b1 & 0x7F
            if n == 126: n = struct.unpack('>H', self._read(2))[0]
            elif n == 127: n = struct.unpack('>Q', self._read(8))[0]
            if b1 & 0x80: mk = self._read(4); p = bytes(b ^ mk[i % 4] for i, b in enumerate(self._read(n)))
            else: p = self._read(n)
            msg += p
            if b0 & 0x80: break
        return json.loads(msg)

    def call(self, method, **params):
        self.id += 1; mid = self.id; self.send(dict(id=mid, method=method, params=params))
        while True:
            m = self.recv()
            if m.get('id') == mid:
                if 'error' in m: raise RuntimeError(f'{method}: {m["error"]}')
                return m.get('result', {})

    def js(self, expr):
        r = self.call('Runtime.evaluate', expression=expr, returnByValue=True, awaitPromise=True)
        if 'exceptionDetails' in r: raise RuntimeError(r['exceptionDetails'])
        return r['result'].get('value')


def wait(ws, expr, t=30):
    t0 = time.time()
    while time.time() - t0 < t:
        try:
            if ws.js(expr): return True
        except Exception: pass
        time.sleep(0.4)
    return False


def settle(ws, limit=10.0):
    """捲到底讓延後畫的版都畫完（drawAhead 會把畫面三個高度內的版補畫），文件高度連兩次一樣（間隔 300ms）、字型載完才算穩定；最多等 limit 秒。"""
    t0 = time.time(); last = None
    while time.time() - t0 < limit:
        h, fs = ws.js('window.scrollTo(0, document.documentElement.scrollHeight); [document.documentElement.scrollHeight, document.fonts ? document.fonts.status : "loaded"]')
        if h == last and fs == 'loaded': return True
        last = h; time.sleep(0.3)
    return False


def measure(ws, sel, box='section.panel'):
    """外框（預設 section.panel）與圖的位置（文件座標，CSS px），加上目前的捲動位置與視窗高度；ng／gh：圖裡 svg／canvas 的個數與最大高度"""
    return ws.js(f'''(function(){{var c=document.querySelector({json.dumps(sel)}); if(!c) return null; var p=c.closest({json.dumps(box)}); if(!p) return null;
        var r=p.getBoundingClientRect(), cr=c.getBoundingClientRect(), sy=window.scrollY, sx=window.scrollX, gh=0, gs=c.querySelectorAll("svg,canvas");
        gs.forEach(function(g){{gh=Math.max(gh, g.getBoundingClientRect().height);}});
        return {{x:r.left+sx, y:r.top+sy, w:r.width, h:r.height, cy:cr.top+sy, ch:cr.height, cw:cr.width, ng:gs.length, gh:gh, sy:sy, vh:window.innerHeight}};}})()''')


def same(a, b, keys=('x', 'y', 'w', 'h', 'cy', 'ch')):
    return bool(a and b) and all(abs(a[k] - b[k]) < 0.5 for k in keys)


def clip_of(box, crop):
    """截圖範圍（文件座標）：預設整個外框；crop=chart 是外框頂到圖底（含標題列、解讀、圖例、圖）"""
    h = box['cy'] + box['ch'] - box['y'] + 16 if crop == 'chart' else box['h']
    return dict(x=box['x'], y=box['y'], width=box['w'], height=h, scale=1)


# 截圖時藏起來：壓到截圖範圍、又不是外框本身或它外層的固定／黏住元素（手機頂欄、換頁掃描線、提示框…），截完還原
HIDE_JS = '''(function(sel, box, x, y, w, h){var p=document.querySelector(sel).closest(box), sx=window.scrollX, sy=window.scrollY, n=0;
    document.querySelectorAll("body *:not(svg *)").forEach(function(e){ if (e.contains(p) || p.contains(e)) return;
      var ps=getComputedStyle(e).position; if (ps!=="fixed" && ps!=="sticky") return; var b=e.getBoundingClientRect();
      if (b.width<=0 || b.height<=0 || b.right<=x-sx || b.left>=x-sx+w || b.bottom<=y-sy || b.top>=y-sy+h) return;
      e.setAttribute("data-shot-vis", e.style.visibility); e.style.visibility="hidden"; n++; });
    return n;})'''
UNHIDE_JS = '''document.querySelectorAll("[data-shot-vis]").forEach(function(e){e.style.visibility=e.getAttribute("data-shot-vis"); e.removeAttribute("data-shot-vis");}); true'''
# 圖上所有文字（刻度、標籤）的位置，相對截圖左上角、CSS px；給 annotate.py 換算座標用
GEO_JS = '''(function(){var c=document.querySelector(%s), p=c.closest(%s), pr=p.getBoundingClientRect();
    return Array.from(c.querySelectorAll("svg text")).map(function(t){var b=t.getBoundingClientRect();
      return {t:(t.textContent||"").trim(), x:b.left-pr.left+b.width/2, y:b.top-pr.top+b.height/2, l:b.left-pr.left, r:b.right-pr.left, anchor:t.getAttribute("text-anchor")||""};});})()'''


def shoot(ws, sel, view, crop=None, box='section.panel', tries=6):
    """捲到目標、連量兩次位置一樣、整個範圍在畫面內才截；截完再量一次，動了就重來。
    sel：圖表容器；box：截圖外框（sel 往上找最近的）；view：browser() 給的視窗參數（加高視窗後用它還原）。
    回傳 (png, clip, geo)；截不成回傳 (None, 原因)"""
    q, bq = json.dumps(sel), json.dumps(box); vh, why = view['height'], '位置一直在動'
    try:
        for k in range(tries):
            ws.js(f'document.querySelector({q}).closest({bq}).scrollIntoView({{block:"start"}}); true'); time.sleep(1.0 if k == 0 else 0.6)
            a = measure(ws, sel, box); time.sleep(0.3); b = measure(ws, sel, box)
            if not same(a, b): why = '位置一直在動'; continue
            if b['w'] <= 0 or b['ch'] <= 0 or (b['ng'] and b['gh'] <= 0):
                why = f'圖的高度是 0（外框 {b["w"]:.0f}×{b["h"]:.0f}、圖 {b["cw"]:.0f}×{b["ch"]:.0f}、svg/canvas 高 {b["gh"]:.0f}）'; time.sleep(0.6); continue
            c = clip_of(b, crop)
            if c['height'] > b['vh']:   # 外框比視窗高：只加高視窗（寬度不變，網站不會切成手機版），再量一次
                vh = int(c['height']) + 40; why = '外框比視窗高'
                ws.call('Emulation.setDeviceMetricsOverride', **dict(view, height=vh)); time.sleep(0.5); continue
            if c['y'] < b['sy'] - 0.5 or c['y'] + c['height'] > b['sy'] + b['vh'] + 0.5:   # 不在畫面內（例如 scroll-padding）：直接捲到範圍頂端再量
                ws.js(f'window.scrollTo(0, {c["y"]}); true'); why = '捲不到截圖範圍'; time.sleep(0.6); continue
            ws.js(f'{HIDE_JS}({q}, {bq}, {c["x"]}, {c["y"]}, {c["width"]}, {c["height"]})')
            try: r = ws.call('Page.captureScreenshot', format='png', clip=c)
            finally: ws.js(UNHIDE_JS)
            d = measure(ws, sel, box)
            if not same(b, d, ('x', 'y', 'w', 'h', 'cy', 'ch', 'sy')): why = '截圖時版面動了'; continue
            return base64.b64decode(r['data']), c, ws.js(GEO_JS % (q, bq))
        return None, why
    finally:
        if vh != view['height']: ws.call('Emulation.setDeviceMetricsOverride', **view); time.sleep(0.3)


def serve():
    import functools, http.server, threading
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=REPO)
    h.func.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8790), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv


@contextlib.contextmanager
def browser(W, H=1000, dpr=2, mobile=False, theme='light', lang='zh'):
    """開本機網站伺服器與無頭 Chrome，設好視窗、深淺色、語言；yield (ws, view)。
    view 是 Emulation.setDeviceMetricsOverride 的參數，shoot() 加高視窗後用它還原。site_cards.py 也用這個（2026-11-10 抽出來共用）"""
    srv = serve(); prof = tempfile.mkdtemp(prefix='daybreak-chrome-')   # 暫存的 Chrome 設定檔，不寫進倉庫
    p = subprocess.Popen([CHROME, '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={prof}', '--hide-scrollbars'] + (['--no-sandbox'] if sys.platform.startswith('linux') else []) + [
                          '--no-first-run', '--no-default-browser-check', f'--window-size={W},{H}', 'about:blank'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # 2026-11-09：GitHub Actions 上 Chrome 第一次啟動有時超過 10 秒，中文圖排第一個就截不到（tg 沒值）；等到 30 秒，等不到就講清楚
        tg = None
        for _ in range(150):
            try: tg = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json')); break
            except Exception: time.sleep(0.2)
        if tg is None: raise RuntimeError(f'Chrome 30 秒內沒開好 remote debugging（port {PORT}）')
        ws = WS(next(t for t in tg if t['type'] == 'page')['webSocketDebuggerUrl'])
        ws.call('Page.enable'); ws.call('Runtime.enable')
        view = dict(width=W, height=H, deviceScaleFactor=dpr, mobile=mobile)
        ws.call('Emulation.setDeviceMetricsOverride', **view)
        ws.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': theme}])
        ws.call('Page.navigate', url=SITE); wait(ws, LOADED)
        print('at', ws.js('location.href + " " + document.readyState + " " + document.title'))
        ws.js(f"localStorage.setItem('daybreak.lang', '{lang}'); localStorage.setItem('daybreak.theme', '{theme}'); localStorage.setItem('daybreak.nohold', '1'); true")   # nohold：判讀撰寫中也截最新數字（2026-11-06）
        yield ws, view
    finally:
        p.terminate(); srv.shutdown()


LOADED = 'location.href.indexOf("8790") > 0 && document.readyState === "complete"'


def goto(ws, page):
    """整頁重新載入並跳到某一版（網址帶毫秒時間戳，一定重載，前一張的 pre／clean 不會留下來）"""
    ws.js('window.__old = 1; true')
    ws.call('Page.navigate', url=SITE + '?v=' + str(int(time.time() * 1000)) + '#' + page)
    wait(ws, '!window.__old'); wait(ws, LOADED); time.sleep(1.0)


def ready(ws, sel):
    """截圖前準備：手機版收起的組先展開；捲到底等延後畫的版都畫好、版面穩定"""
    # 2026-11-09 手機版長頁收合（foldGroups）：目標在收起的組裡（面板 0×0）就按「展開這組其餘 N 張」，網站會依實際寬度重畫
    if ws.js(f'''(function(){{var p=document.querySelector({json.dumps(sel)}).closest(".panel.gmore"); if(!p) return false;
        var b=document.querySelector('.gmore-btn[data-gm="'+p.getAttribute("data-gm")+'"]'); if(b) b.click(); return true;}})()'''): time.sleep(0.6)
    if not settle(ws): print('注意：版面 10 秒內高度沒穩定，照樣往下（截圖前還會再確認位置）', sel, file=sys.stderr)


def main():
    jobs = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True); fails = []
    with browser(jobs.get('width', 1440), theme=jobs.get('theme', 'light'), lang=jobs['lang']) as (ws, view):
        cur = None
        for it in jobs['items']:
            if it['page'] != cur: goto(ws, it['page']); cur = it['page']
            sel = json.dumps(it['sel'])
            need = '' if it.get('html') else ' && e.querySelector("svg,canvas")'   # html=1：用 div 畫的圖（例如籌碼分布 URPD）不等 svg
            ok = wait(ws, f'(function(){{var e=document.querySelector({sel}); return !!(e{need});}})()', 40)
            if not ok: print('ERROR MISSING', it['sel'], file=sys.stderr); fails.append(it['out']); continue
            ready(ws, it['sel'])
            if it.get('pre'): ws.js(it['pre']); time.sleep(0.8)
            if it.get('dump'): print(ws.js(f'''(function(){{var p=document.querySelector({sel}).closest("section.panel"); return Array.from(p.children).map(function(c){{return c.tagName+"."+c.className+"#"+c.id+" | "+(c.textContent||"").slice(0,50).replace(/\\s+/g," ")+" | h="+Math.round(c.getBoundingClientRect().height);}}).join("\\n");}})()''')); continue
            if it.get('clean'):   # 發文用：只留標題列、圖例、圖；解讀、表格、說明、按鈕都藏起來
                ws.js(f'''(function(){{var p=document.querySelector({sel}).closest("section.panel");
                    p.querySelectorAll(".interp,#ac-say,.rd,.tbl-wrap,p.note").forEach(function(e){{e.style.display="none";}});
                    p.querySelectorAll("button").forEach(function(b){{b.style.visibility="hidden"; var q=b.parentElement; if(Array.prototype.every.call(q.children,function(c){{return c.tagName==="BUTTON";}})) q.style.visibility="hidden";}});
                    p.querySelectorAll(".panel-h a").forEach(function(a){{if(a.textContent.trim()==="#")a.style.visibility="hidden";}});
                    return true;}})()'''); time.sleep(0.6)
                it['crop'] = 'chart'
            png, *rest = shoot(ws, it['sel'], view, crop=it.get('crop'))
            if png is None:   # 不輸出空白或截錯的圖
                print('ERROR', it['out'], it['sel'], rest[0], file=sys.stderr); fails.append(it['out']); continue
            clip, geo = rest
            fn = os.path.join(out, it['out'] + '.png'); open(fn, 'wb').write(png)
            print('wrote', fn, round(clip['width']), 'x', round(clip['height']))
            json.dump(dict(dpr=2, texts=geo), open(os.path.join(out, it['out'] + '.json'), 'w'), ensure_ascii=False)
        if fails: print('ERROR 沒截成：', ', '.join(fails), file=sys.stderr)
    if fails: sys.exit(1)


if __name__ == '__main__':
    main()
