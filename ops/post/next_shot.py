"""新版首頁圖表截圖（2026-11-11 建立）：長文、貼文配圖改截新版首頁（index.html，pipeline/next/ 產生）的卡片。
舊版 classic.html 2026-11-17 已刪除，截卡片都用這支；這支只多一層「找到卡片、切到那一頁、整理畫面」，開瀏覽器和截圖沿用 site_shot.py。
usage（倉庫根目錄）: python3 ops/post/next_shot.py <jobs.json> <輸出資料夾>
       python3 ops/post/next_shot.py --list            # 列出每張圖的代號（k）、所在分頁、標題
jobs.json: {"lang": "zh"|"en", "width": 1440, "height": 1000,
            "items": [{"k": "oih", "out": "oih", "view": "card"|"fx", "clean": 1, "nosay": 0, "rg": 365|1095|0, "m": 1, "ly": "sp"|"ov", "pre": "<js>"}]}
  k      圖的代號：data/next.js 裡 site.chapters[].groups[].charts[].k（網站加圖、換位置都不會變；--list 可查）
  view   card（預設）＝分頁裡的那張卡片（半寬卡 678px、整排卡 1372px，width 1440 時）；fx＝點開的放大檢視（整個視窗寬，高度跟 height 走）；
         share＝網站的分享模式（2026-11-11 起，index.html?share&k=…）：固定 16:9（1600×900），字級放大、補坐標刻度、頁尾有網站名、資料來源和日期，
         直接就是一張發文用的圖，**長文配圖優先用這個**；share45＝分享模式 4:5（1080×1350）
  clean  1＝藏掉按鈕（放大、區間、版面切換、說明）和「我們的看法」（.sy-view），發文用；share 模式網站自己就會藏
  nosay  1＝連讀數（.sy-read）也藏，整塊結論都不留（正文自己講的時候用）
  rg     區間：365＝1 年、1095＝3 年、0＝全部；m＝第幾個模式（卡片上的切換鈕，從 0 起）；ly＝sp 上下兩格／ov 疊在一格
  d3     立體檢視（只有 view=share／share45，圖：urpd、strike、ivt）：{"d3v": "ob", "yaw": -29, "pit": 32, "ex": 1, "wk": "2025-02-16", "sel": "96000,2025-02-16"}，
         每個鍵都可省；空 dict {} 就是預設的立體斜看。要錄成影片用 ops/post/d3_video.py
         11/16 #177 起還有 xr＝"50000,110000"（只畫這段價位／履約價）、yr＝"2024-11-01,2025-08-31"（只畫這段週／到期日）、fit＝1（照當下角度撐滿）、zoom＝1.4（倍率，超出會裁掉）。
         建議 xr＋fit；再加 zoom 容易切掉邊上的刻度。帶了範圍，圖下說明會自動補「這張只畫…」，別裁掉
  xy     只有 view=share／share45：[["YYYY-MM-DD", 數值, "p"|""], …]，截圖當下用網站的 window.daybreakXY(圖代號, 日期, 數值, pane) 換成座標，
         寫進 <out>.json 的 xy（CSS px，左上角＝截圖左上角；pane "p"＝上格價格）。annotate.py 會自己帶這個，通常不用手寫（2026-11-16）
輸出：<out>.png（2 倍解析度）與 <out>.json（card／fx：圖上文字位置；share：xy 座標；CSS px，給 annotate.py）
分享模式截圖前會檢查畫面上沒有首頁大數字下的階段標籤（「…・持有」「… · hold」這種動作結論），有就不截。
只有深色（新版預設深夜，沒有存主題）。動畫用 prefers-reduced-motion 關掉（進場動畫、數字翻牌、五個 AI 游標都不會出現）。
出場框架的卡片（出場分頁全部、今天分頁的「行動與要盯的價位」「出場」）不截：社群內容不放出場框架。
有任何一張沒截成就印 ERROR、不寫那張的檔案，最後結束碼 1。
"""
import base64, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import site_shot as S

SITE = 'http://127.0.0.1:8790/index.html'
STAGE_RE = r'/・\s*持有|·\s*hold\b/i'   # 首頁大數字下的階段標籤（「深夜・持有」「Night · hold」）：動作結論，截圖錄影都不能露（2026-11-12 規則）
BLOCK = lambda ch_id, k: ch_id == 'exit' or k.startswith('x_') or k in ('t_act', 'q_exit')   # 出場框架不進社群配圖


def catalog():
    """讀 data/next.js，回傳 {k: dict(ch=分頁序號, ch_id, ch_zh, key='組_序', zh, en, fx=能不能放大)}"""
    s = open(os.path.join(S.REPO, 'data', 'next.js'), encoding='utf-8').read()
    D = json.loads(s[s.index('{'):s.rindex('}') + 1]); cat = {}
    for ci, c in enumerate(D['site']['chapters']):
        for gi, g in enumerate(c.get('groups') or []):
            for xi, x in enumerate(g.get('charts') or []):
                cat[x['k']] = dict(k=x['k'], ch=ci, ch_id=c['id'], ch_zh=c['zh'], key=f'{gi + 1}_{xi}', zh=x.get('zh', ''), en=x.get('en', ''), fx=not x.get('nofx'), na=bool(x.get('na')))
    return cat


def open_card(ws, c, lang):
    """整頁重載、切到那一頁，等那張卡片出現（標題對得上才算，避免還停在上一頁同位置的卡片）"""
    S.goto(ws, '')
    S.wait(ws, '!!(window.DAYBREAK_NEXT && document.querySelector("#oc-crumb button[data-ch]"))', 30)   # 要回傳布林：DOM 元素傳回來是 {}，Python 當成 False
    if c['ch']: ws.js(f'document.querySelector(\'#oc-crumb button[data-ch="{c["ch"]}"]\').click(); true')
    sel = f'.fc[data-k="{c["k"]}"] .ol[data-ck="{c["k"]}"]'   # 2026-11-11 起網站在卡片上放了固定的圖代號（North7/daybreak#114）
    if S.wait(ws, f'!!document.querySelector({json.dumps(sel)})', 30): return sel
    sel = '#oc-ol' + c['key']; title = c['en'] if lang == 'en' else c['zh']   # 舊掛點：位置＋標題比對
    ok = S.wait(ws, f'(function(){{var e=document.querySelector({json.dumps(sel)}), h=e&&e.querySelector("h4"); return !!(h && h.textContent.trim()==={json.dumps(title)});}})()', 10)
    return sel if ok else None


CLEAN_JS = '''(function(sel, nosay){var r=document.querySelector(sel);
    r.querySelectorAll(".fx-b").forEach(function(e){e.style.visibility="hidden";});
    r.querySelectorAll(".ol-ctl,.ol-how,.sy-m").forEach(function(e){e.style.display="none";});
    r.querySelectorAll(".sy-view").forEach(function(e){e.style.display="none";});   // 「我們的看法」「會改變看法」不進社群配圖
    if (nosay) r.querySelectorAll(".ol-say").forEach(function(e){e.style.display="none";});
    r.querySelectorAll('[id^="oc-pr"]').forEach(function(e){ if (/移動游標|Move across/.test(e.textContent)) e.style.display="none"; });   // 「在圖上移動游標…」的操作提示
    r.querySelectorAll(".ol-f").forEach(function(e){ if (!Array.prototype.some.call(e.children, function(c){return c.style.display!=="none" && c.getBoundingClientRect().height>0;})) e.style.display="none"; });   // 頁尾只剩說明鈕就整排收掉
    var f=document.querySelector("#oc-fx"); if (f && f.contains(r)) { f.querySelectorAll(".fx-x").forEach(function(e){e.style.visibility="hidden";}); f.querySelectorAll(".os-h").forEach(function(e){e.style.display="none";}); }   // 放大檢視最上面那行網站導覽（01 / 04 槓桿…）對發文沒用，2026-11-11 藏掉
    return true;})'''


def d3_query(it):
    """立體檢視（2026-11-16，North7/daybreak#175，urpd／strike／ivt）：it['d3'] 是 dict，有就加 m=d3 和鏡頭參數。
    d3v＝flat｜ob｜top；yaw、pit 度（斜看預設 yaw=-29、pit=32）；ex 攤開 0–1（0＝平面）；wk＝哪一週／哪個到期日；sel＝"價位,週"（urpd）或 "履約價,到期日"。
    網址的 m 是「第幾個檢視」（d3 或 1），攤開程度在網址叫 ex。帶了鏡頭參數就停在那裡，不會自己站起來"""
    d = it.get('d3')
    if d is None: return ''
    from urllib.parse import quote
    return '&m=d3' + ''.join(f'&{key}={quote(str(v), safe=",")}' for key, v in d.items() if v is not None)   # 鍵照原樣帶進網址，網站之後加的參數（放大、價格範圍…）不用改這裡


# 2026-11-16 一次截 61 張時有兩張截到首頁「今天」（含出場框架的字）、一張畫面平鋪成好幾份：連續切換視窗尺寸時的競態。
# 截圖前後都確認：分享框開著、是這張圖、蓋滿視窗、視窗尺寸和網址都對；不對就整張重來（main 最多 3 次）
SANE_JS = '''(function(k, W, H){var f=document.querySelector("#oc-fx");
    if (!f || f.hidden || !f.classList.contains("on")) return "分享框沒開";
    if (!f.querySelector('#oc-olF[data-ck="' + k + '"]')) return "分享框裡不是這張圖";
    if (innerWidth !== W || innerHeight !== H || devicePixelRatio !== 2) return "視窗 " + innerWidth + "x" + innerHeight + " @" + devicePixelRatio;
    var r = f.getBoundingClientRect(); if (r.left > 2 || r.top > 2 || r.width < W - 4 || r.height < H - 4) return "分享框沒蓋滿視窗";
    var q = new URLSearchParams(location.search); if (!q.has("share") || q.get("k") !== k) return "網址不是這張圖的分享模式";
    return "";})(%s, %d, %d)'''


def shoot_share(ws, view, k, it, geo=None):
    """分享模式：視窗設成 16:9（1600×900）或 4:5（1080×1350），開 index.html?share&k=…，整個畫面就是那張圖。回傳 (png, 尺寸說明) 或 (None, 原因)。
    geo 給一個 dict 就填進座標資料（dpr、尺寸、it['xy'] 換出來的座標），給 <out>.json／annotate.py 用；site_cards.py 不用帶"""
    r45 = it.get('view') == 'share45'; W, H = (1080, int(it.get('h') or 1350)) if r45 else (1600, 900)   # h：4:5 模式的視窗高度（site_cards.py 要在上面加標題，留出那一段）
    ws.call('Emulation.setDeviceMetricsOverride', width=W, height=H, deviceScaleFactor=2, mobile=False)
    try:
        ws.js('window.__old = 1; true')
        ws.call('Page.navigate', url=f'{S.SITE}?{"share=45" if r45 else "share"}&k={k}{d3_query(it)}&v={int(time.time() * 1000)}')
        S.wait(ws, '!window.__old'); S.wait(ws, S.LOADED)
        q = json.dumps(f'#oc-fx.on #oc-olF[data-ck="{k}"]')
        if not S.wait(ws, f'!!document.querySelector({q})', 30): return None, '分享模式沒打開這張圖（網址參數或 data-ck 掛點變了？）'
        for attr in ('m', 'rg', 'ly'):   # 分享模式按鈕是藏起來的，用程式按一樣有效
            if attr in it and not (attr == 'm' and 'd3' in it):   # 立體檢視已經從網址打開，再按模式鈕會切回去
                hit = ws.js(f'(function(){{var b=document.querySelector({q}).querySelector(\'.ol-ctl button[data-{attr}="{it[attr]}"]\'); if(!b) return false; b.click(); return true;}})()')
                if not hit: print(f'注意：{k} 沒有 {attr}={it[attr]} 這個按鈕，略過', file=sys.stderr)
                time.sleep(0.8)
        ws.js(f'document.querySelectorAll({q} + " .sy-view").forEach(function(e){{e.style.display="none";}}); true')   # 網站已經藏了，再保險一次
        if it.get('nosay'): ws.js(f'document.querySelectorAll({q} + " .ol-say").forEach(function(e){{e.style.display="none";}}); true')
        if it.get('pre'): ws.js(it['pre'])
        if not S.wait(ws, f'(function(){{var e=document.querySelector({q}); return !!(e && e.querySelector("svg,canvas,.rl") && (!document.fonts || document.fonts.status==="loaded"));}})()', 20): return None, '分享模式的圖沒畫出來'
        if 'd3' in it and not S.wait(ws, '!!(window.__d3 && window.__d3.ready)', 20): return None, '立體檢視沒畫出來（__d3.ready 一直是 false）'
        time.sleep(1.2)
        if ws.js(f'{STAGE_RE}.test((document.querySelector("#oc-fx")||document.body).innerText)'): return None, '畫面上有階段標籤（…・持有／· hold），動作結論不進社群配圖'
        xy = []
        for d, v, *pane in it.get('xy') or []:   # 圖代號、日期、數值 → 視窗座標（分享模式整個視窗就是截圖，不用再位移）
            r = ws.js(f'(function(){{var r=window.daybreakXY({json.dumps(k)}, {json.dumps(d)}, {json.dumps(v)}, {json.dumps((pane or [""])[0] or None)}); return r ? {{x:r.x, y:r.y, t0:r.t0, t1:r.t1, lo:r.lo, hi:r.hi}} : null;}})()')
            if not r or r.get('x') is None or r.get('y') is None: return None, f'daybreakXY 換不出座標：{d} {v} {pane}（日期超出圖的範圍？上格價格要帶 "p"）'
            xy.append(dict(d=d, v=v, pane=(pane or [''])[0], x=r['x'], y=r['y'], t0=r.get('t0'), t1=r.get('t1')))
        bad = ws.js(SANE_JS % (json.dumps(k), W, H))
        if bad: return None, f'截圖前檢查沒過：{bad}'
        r = ws.call('Page.captureScreenshot', format='png')
        # 2026-11-16（#186）：截完再核對一次還停在這張圖，頁面中途被換掉（例如除錯埠被別的程式佔走）就不交出這張；SANE_JS 同時核對網址的 k、放大檢視的 data-ck、視窗尺寸
        bad = ws.js(SANE_JS % (json.dumps(k), W, H))
        if bad: return None, f'截圖後檢查沒過：{bad}'
        if geo is not None: geo.update(dpr=2, k=k, view=it.get('view'), w=W, h=H, xy=xy)
        return base64.b64decode(r['data']), f'{W} x {H}（分享模式 {"4:5" if r45 else "16:9"}）'
    finally:
        ws.call('Emulation.setDeviceMetricsOverride', **view); time.sleep(0.3)


def main():
    cat = catalog()
    if sys.argv[1] == '--list':
        for k, c in cat.items(): print(f'{c["ch_zh"]}\t{k}\t{c["zh"]}' + ('' if c['fx'] else '\t（不能放大）') + ('\t（不截：出場框架）' if BLOCK(c['ch_id'], k) else ''))
        return
    jobs = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True); fails = []; lang = jobs.get('lang', 'zh')
    S.SITE = SITE
    with S.browser(jobs.get('width', 1440), H=jobs.get('height', 1000), theme='dark', lang=lang) as (ws, view):
        ws.call('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': 'dark'}, {'name': 'prefers-reduced-motion', 'value': 'reduce'}])
        for it in jobs['items']:
            k = it['k']; c = cat.get(k); name = it.get('out', k); fx = it.get('view') == 'fx'; share = str(it.get('view', '')).startswith('share')
            def fail(why): print('ERROR', name, k, why, file=sys.stderr); fails.append(name)
            if not c: fail('data/next.js 裡沒有這個代號（--list 可查）'); continue
            if BLOCK(c['ch_id'], k): fail('出場框架的卡片不截（社群內容不放出場框架）'); continue
            if c['na']: fail('這張卡片目前沒有資料'); continue
            if (fx or share) and not c['fx']: fail('這張卡片不能放大，改用 view=card'); continue
            if share:
                for _ in range(3):
                    geo = {}; png, why = shoot_share(ws, view, k, it, geo)
                    if png is not None or '檢查沒過' not in why and '沒打開' not in why and '沒畫出來' not in why: break
                    print('重試', name, why, file=sys.stderr); time.sleep(1)
                if png is None: fail(why); continue
                fn = os.path.join(out, name + '.png'); open(fn, 'wb').write(png); print('wrote', fn, why)
                json.dump(geo, open(os.path.join(out, name + '.json'), 'w'), ensure_ascii=False); continue
            sel = open_card(ws, c, lang)
            if not sel: fail('切到分頁後找不到卡片'); continue
            if not S.settle(ws): print('注意：版面 10 秒內高度沒穩定，照樣往下', k, file=sys.stderr)
            box = '.fc'
            if fx:
                ws.js(f'document.querySelector({json.dumps(sel)}).closest(".fc").querySelector("[data-fx]").click(); true')
                sel, box = '#oc-olF', '#oc-fx article.os'
                if not S.wait(ws, '!!document.querySelector("#oc-fx.on #oc-olF .ol-t")', 15): fail('放大檢視沒打開'); continue
                time.sleep(0.6)
            q = json.dumps(sel)
            for attr in ('m', 'rg', 'ly'):   # 模式 → 區間 → 版面，每按一次卡片會重畫
                if attr in it:
                    hit = ws.js(f'(function(){{var b=document.querySelector({q}).querySelector(\'.ol-ctl button[data-{attr}="{it[attr]}"]\'); if(!b) return false; b.click(); return true;}})()')
                    if not hit: print(f'注意：{k} 沒有 {attr}={it[attr]} 這個按鈕，略過', file=sys.stderr)
                    time.sleep(0.8)
            if it.get('pre'): ws.js(it['pre']); time.sleep(0.8)
            if it.get('clean') or it.get('nosay'): ws.js(f'{CLEAN_JS}({q}, {1 if it.get("nosay") else 0})'); time.sleep(0.6)
            crop = None
            if fx:   # 底下那排同組小圖不進配圖：只截到卡片內容的底（頁尾那排數字，沒有就到圖底）再留 24px
                crop = ws.js(f'''(function(){{var r=document.querySelector({q}), top=r.closest({json.dumps(box)}).getBoundingClientRect().top, b=0;
                    r.querySelectorAll(".ol-f,.ol-c,.ol-a,.ol-b,.rl").forEach(function(e){{var x=e.getBoundingClientRect(); if(x.height>0) b=Math.max(b, x.bottom);}});
                    var o=document.querySelector("#oc-orF"), ot=o?o.getBoundingClientRect().top:1e9; return Math.min(b+24, ot-6)-top;}})()''')
            else:    # 同一排的卡片會被拉成一樣高，藏掉按鈕後底下會空一截：讓這張卡片照自己的內容高度
                ws.js(f'var f=document.querySelector({q}).closest(".fc"); f.style.alignSelf="flex-start"; f.style.height="auto"; true'); time.sleep(0.4)
            if not S.wait(ws, f'(function(){{var e=document.querySelector({q}); return !!(e && (e.querySelector("svg,canvas") || e.querySelector(".rl,.ol-c")));}})()', 20): fail('卡片裡沒有圖'); continue
            png, *rest = S.shoot(ws, sel, view, crop=crop, box=box)
            if png is None: fail(rest[0]); continue
            clip, geo = rest
            fn = os.path.join(out, name + '.png'); open(fn, 'wb').write(png)
            print('wrote', fn, round(clip['width']), 'x', round(clip['height']))
            json.dump(dict(dpr=2, texts=geo), open(os.path.join(out, name + '.json'), 'w'), ensure_ascii=False)
        if fails: print('ERROR 沒截成：', ', '.join(fails), file=sys.stderr)
    if fails: sys.exit(1)


if __name__ == '__main__':
    main()
