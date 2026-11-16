"""網站立體圖逐格錄影（2026-11-16 建立）：籌碼地形（urpd）、履約價全部到期（strike）、波動率曲面（ivt）錄成 MP4。
網站的分享模式（North7/daybreak#175）有 window.__d3.set({view, yaw, pit, m, wk, sel})：設完當下就畫好、不走彈簧，
所以這裡一格一格設角度、截圖、送進 ffmpeg，每次錄出來都一樣。開瀏覽器和本機伺服器沿用 site_shot.py。
usage（倉庫根目錄）: python3 ops/post/d3_video.py <job.json> <out.mp4>
job.json: {"k": "urpd", "ratio": "45"|"169", "fps": 30, "dpr": 1, "lang": "zh",
           "keys": [{"t": 0, "yaw": 0, "pit": 0, "m": 0}, {"t": 2.5, "yaw": -29, "pit": 32, "m": 1}, ...],   # 關鍵格，中間用 ease-in-out 補
           "events": [{"t": 8, "sel": [96000, "2025-02-16"], "wk": "2025-02-16"}],                         # 到了這個時間點設一次（選柱子、切一刀；sel 給 null 取消）
           "end": 11,                                                                                     # 總長（秒），最後一個關鍵格之後停住
           "url": {"px": "50000,110000"}}                                                                 # 選填：額外的網址參數，照原樣帶
  yaw、pit 是度；m 是攤開的程度 0–1（0＝平面）。4:5 是 1080×1350、16:9 是 1600×900（dpr 1.2 就是 1920×1080）。
需要 ffmpeg：PATH 上有就用，沒有就用 imageio_ffmpeg（pip install imageio-ffmpeg）。輸出放 ops/video/out/，不進 git。
"""
import base64, json, os, shutil, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import site_shot as S


def ffmpeg():
    f = shutil.which('ffmpeg')
    if f: return f
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def ease(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def cam(keys, t):
    if t <= keys[0]['t']: return keys[0]
    for a, b in zip(keys, keys[1:]):
        if t <= b['t']:
            u = ease((t - a['t']) / max(1e-9, b['t'] - a['t']))
            return {q: a[q] + (b[q] - a[q]) * u for q in ('yaw', 'pit', 'm')}
    return keys[-1]


def main():
    job = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    k = job['k']; r45 = job.get('ratio', '45') == '45'; W, H = (1080, 1350) if r45 else (1600, 900)
    fps = job.get('fps', 30); dpr = job.get('dpr', 1); keys = sorted(job['keys'], key=lambda x: x['t'])
    events = sorted(job.get('events', []), key=lambda x: x['t']); end = job.get('end', keys[-1]['t'] + 2)
    S.SITE = 'http://127.0.0.1:8790/index.html'
    with S.browser(W, H=H, dpr=dpr, theme='dark', lang=job.get('lang', 'zh')) as (ws, view):
        ws.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': 'dark'}, {'name': 'prefers-reduced-motion', 'value': 'reduce'}])
        k0 = keys[0]
        ws.js('window.__old = 1; true')
        extra = ''.join(f'&{q}={v}' for q, v in job.get('url', {}).items())   # 只能從網址設的參數（例如價格範圍），鍵照原樣帶
        ws.call('Page.navigate', url=f'{S.SITE}?{"share=45" if r45 else "share"}&k={k}&m=d3&yaw={k0["yaw"]}&pit={k0["pit"]}&ex={k0["m"]}{extra}&v={int(time.time() * 1000)}')
        S.wait(ws, '!window.__old'); S.wait(ws, S.LOADED)
        if not S.wait(ws, '!!(window.__d3 && window.__d3.ready && (!document.fonts || document.fonts.status==="loaded"))', 30): sys.exit('ERROR 立體檢視沒畫出來（__d3.ready 一直是 false）')
        ws.js('var st=document.createElement("style"); st.textContent="*{scrollbar-width:none!important} ::-webkit-scrollbar{display:none!important}"; document.head.appendChild(st); true')   # 右邊那條捲軸不進影片
        time.sleep(1.0)
        n = int(round(end * fps)); ei = 0
        ff = subprocess.Popen([ffmpeg(), '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(fps), '-i', '-',
                               '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'slow', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
        for i in range(n):
            t = i / fps; o = dict(cam(keys, t))
            while ei < len(events) and events[ei]['t'] <= t:
                for q, v in events[ei].items():   # sel、wk，或網站之後加的其他 __d3.set 欄位
                    if q != 't': o[q] = v
                ei += 1
            if not ws.js(f'window.__d3.set({json.dumps(o)})'): sys.exit(f'ERROR 第 {i} 格 __d3.set 沒設到')
            png = base64.b64decode(ws.call('Page.captureScreenshot', format='png')['data'])
            ff.stdin.write(png)
            if i % fps == 0: print(f'{t:.0f}s', end=' ', flush=True)
        ff.stdin.close(); ff.wait()
        if ff.returncode: sys.exit('ERROR ffmpeg 失敗')
    print('\nwrote', out, f'{n} 格、{end} 秒、{W * dpr:.0f}×{H * dpr:.0f}')


if __name__ == '__main__':
    main()
