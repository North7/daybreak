"""網站圖表截圖（2026-11-05 建立）：用本機 Chrome 無頭模式開「本機的網站檔案」（內建小伺服器，127.0.0.1:8790），
截指定圖表面板成 PNG，同時存一份圖上文字的位置（刻度、標籤）給 annotate.py 換算座標。只用 Python 標準函式庫（自帶最小 WebSocket）。
發文配圖用：clean=1 會藏掉解讀、表格、說明、按鈕，只留標題列、圖例、圖；theme 用 dark（2026-11-05 使用者選深色）。
usage（倉庫根目錄）: python3 ops/post/site_shot.py <jobs.json> <輸出資料夾>
jobs.json: {"lang": "zh"|"en", "theme": "dark"|"light", "width": 1440,
            "items": [{"page": "onchain", "sel": "#c-lthloss", "out": "b1-lthloss-dark", "clean": 1, "pre": "<等動畫跑完的 js>"}]}
輸出：<out>.png（2 倍解析度）與 <out>.json（圖上文字位置，CSS px）
"""
import base64, json, os, socket, struct, subprocess, sys, time, urllib.request

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
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


def serve():
    import functools, http.server, threading
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=REPO)
    h.func.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8790), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv


def main():
    srv = serve()
    jobs = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    import tempfile; prof = tempfile.mkdtemp(prefix='daybreak-chrome-')   # 暫存的 Chrome 設定檔，不寫進倉庫
    W = jobs.get('width', 1440)
    p = subprocess.Popen([CHROME, '--headless=new', f'--remote-debugging-port={PORT}', f'--user-data-dir={prof}', '--hide-scrollbars',
                          '--no-first-run', '--no-default-browser-check', f'--window-size={W},1000', 'about:blank'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try: tg = json.load(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json')); break
            except Exception: time.sleep(0.2)
        page = next(t for t in tg if t['type'] == 'page')
        ws = WS(page['webSocketDebuggerUrl'])
        ws.call('Page.enable'); ws.call('Runtime.enable')
        ws.call('Emulation.setDeviceMetricsOverride', width=W, height=1000, deviceScaleFactor=2, mobile=False)
        ws.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': jobs.get('theme', 'light')}])
        ws.call("Page.navigate", url=SITE); wait(ws, "location.href.indexOf(\"8790\") > 0 && document.readyState === \"complete\"")
        print('at', ws.js('location.href + " " + document.readyState + " " + document.title'))
        ws.js(f"localStorage.setItem('daybreak.lang', '{jobs['lang']}'); localStorage.setItem('daybreak.theme', '{jobs.get('theme', 'light')}'); true")
        cur = None
        for it in jobs['items']:
            if it['page'] != cur:
                ws.js('window.__old = 1; true')
                ws.call('Page.navigate', url=SITE + '?v=' + str(int(time.time())) + '#' + it['page']); cur = it['page']
                wait(ws, '!window.__old'); wait(ws, "location.href.indexOf(\"8790\") > 0 && document.readyState === \"complete\""); time.sleep(1.0)
            sel = json.dumps(it['sel'])
            ok = wait(ws, f'(function(){{var e=document.querySelector({sel}); return !!(e && e.querySelector("svg,canvas"));}})()', 40)
            if not ok: print('MISSING', it['sel']); continue
            if it.get('pre'): ws.js(it['pre']); time.sleep(0.8)
            if it.get('dump'): print(ws.js(f'''(function(){{var p=document.querySelector({sel}).closest("section.panel"); return Array.from(p.children).map(function(c){{return c.tagName+"."+c.className+"#"+c.id+" | "+(c.textContent||"").slice(0,50).replace(/\\s+/g," ")+" | h="+Math.round(c.getBoundingClientRect().height);}}).join("\\n");}})()''')); continue
            if it.get('clean'):   # 發文用：只留標題列、圖例、圖；解讀、表格、說明、按鈕都藏起來
                ws.js(f'''(function(){{var p=document.querySelector({sel}).closest("section.panel");
                    p.querySelectorAll(".interp,#ac-say,.rd,.tbl-wrap,p.note").forEach(function(e){{e.style.display="none";}});
                    p.querySelectorAll("button").forEach(function(b){{b.style.visibility="hidden"; var q=b.parentElement; if(Array.prototype.every.call(q.children,function(c){{return c.tagName==="BUTTON";}})) q.style.visibility="hidden";}});
                    p.querySelectorAll(".panel-h a").forEach(function(a){{if(a.textContent.trim()==="#")a.style.visibility="hidden";}});
                    return true;}})()'''); time.sleep(0.6)
                it['crop'] = 'chart'
            ws.js(f'document.querySelector({sel}).closest("section.panel").scrollIntoView({{block:"start"}}); true'); time.sleep(1.2)
            box = ws.js(f'''(function(){{var c=document.querySelector({sel}), p=c.closest("section.panel"), r=p.getBoundingClientRect(), cr=c.getBoundingClientRect();
                var sy=window.scrollY, sx=window.scrollX;
                return {{x:r.left+sx, y:r.top+sy, w:r.width, h:r.height, cy:cr.top+sy, ch:cr.height}};}})()''')
            y, h = box['y'], box['h']
            if it.get('crop') == 'chart':   # 面板頂到圖底（含標題列、解讀、圖例、圖）
                h = box['cy'] + box['ch'] - box['y'] + 16
            r = ws.call('Page.captureScreenshot', format='png', captureBeyondViewport=True,
                        clip=dict(x=box['x'], y=y, width=box['w'], height=h, scale=1))
            fn = os.path.join(out, it['out'] + '.png'); open(fn, 'wb').write(base64.b64decode(r['data']))
            print('wrote', fn, round(box['w']), 'x', round(h))
            # 圖上所有文字（刻度、標籤）的位置，相對截圖左上角、CSS px；給 annotate.py 換算座標用
            geo = ws.js(f'''(function(){{var c=document.querySelector({sel}), p=c.closest("section.panel"), pr=p.getBoundingClientRect();
                return Array.from(c.querySelectorAll("svg text")).map(function(t){{var b=t.getBoundingClientRect();
                  return {{t:(t.textContent||"").trim(), x:b.left-pr.left+b.width/2, y:b.top-pr.top+b.height/2, l:b.left-pr.left, r:b.right-pr.left, anchor:t.getAttribute("text-anchor")||""}};}});}})()''')
            json.dump(dict(dpr=2, texts=geo), open(os.path.join(out, it['out'] + '.json'), 'w'), ensure_ascii=False)
    finally:
        p.terminate(); srv.shutdown()


if __name__ == '__main__':
    main()
