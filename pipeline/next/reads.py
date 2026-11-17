# -*- coding: utf-8 -*-
"""新版自己產生的讀數（2026-11-17 起，手機長頁改版第二步：舊版網站停用的第三步）。
規則（page.html ㉞-7，使用者照建議）：每張卡一句結論（40 字內）＋最多三條事實（每條 50 字內）＋收起的「怎麼讀」三行。
數字都從 data/latest.json（L）讀；回測的統計在資料流程裡已經算好（collect.py、oc_extra.py 等），這裡只組句子。
「怎麼讀這張圖」是固定說明，從舊版凍結在 how.json，不再每天從舊版抽。
做好的頁：買盤（reads_buy）、週期（reads_cycle）、賣壓（reads_sell）、價位（reads_lv）、槓桿（reads_lev）；say_data.attach 遇到 say['own'] 的卡片就不再掛舊版的讀數（資料來源、異動照舊）。只作讀值。"""
import json, os, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
HOW = json.load(open(os.path.join(HERE, 'how.json'), encoding='utf-8')) if os.path.exists(os.path.join(HERE, 'how.json')) else {}
M = '−'
HOWX = {}   # 各頁模組補的「怎麼讀」（舊版沒有的卡片）
def sg(v, d=1):
    s = ('%.' + str(d) + 'f') % abs(v); return ('+' if v > 0 and float(s) else M if v < 0 and float(s) else '') + s
def pc(v, d=1): return sg(v, d) + '%'
def pu(v, d=1): return ('%.' + str(d) + 'f%%') % v
def n0(v): return format(int(round(v)), ',')
def sn0(v): return ('+' if v > 0 else M if v < 0 else '') + n0(abs(v))
def wan(v, sign=True):
    a = abs(v); s = (('%.1f' % (a / 1e4)).rstrip('0').rstrip('.') + ' 萬顆') if a >= 1e4 else n0(a) + ' 顆'
    return (('+' if v > 0 else M if v < 0 else '') if sign else '') + s
def kb(v, sign=True):
    a = abs(v); s = ('%.2fM BTC' % (a / 1e6)) if a >= 1e6 else (('%.1f' % (a / 1e3)).rstrip('0').rstrip('.') + 'K BTC') if a >= 1e4 else n0(a) + ' BTC'
    return (('+' if v > 0 else M if v < 0 else '') if sign else '') + s
def yi(musd, sign=True):   # 百萬美元 → 億美元
    a = abs(musd); s = ('%.2f 億美元' % (a / 100)) if a >= 100 else ('%d 百萬美元' % round(a))
    return (('+' if musd > 0 else M if musd < 0 else '') if sign else '') + s
def bn(musd, sign=True):
    a = abs(musd); s = ('$%.2fB' % (a / 1000)) if a >= 1000 else ('$%dM' % round(a))
    return (('+' if musd > 0 else M if musd < 0 else '') if sign else '') + s
def md(d): return '%d/%d' % (int(d[5:7]), int(d[8:10]))
def ymd(d): return d.replace('-', '/')
def ym(d): return d[:7].replace('-', '/')
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
def mde(d): return '%s %d' % (MON[int(d[5:7]) - 1], int(d[8:10]))
def ymde(d): return '%s %d, %s' % (MON[int(d[5:7]) - 1], int(d[8:10]), d[:4])
def yme(d): return '%s %s' % (MON[int(d[5:7]) - 1], d[:4])
def ord_en(n): n = int(round(n)); return '%d%s' % (n, 'th' if 10 < n % 100 < 14 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))
def it(kz, ke, vz, ve, tone, dz, de, view=0, cz='', ce=''):
    return dict(kz=kz, ke=ke, vz=vz, ve=ve, tone=tone, dz=dz, de=de, view=view, cz=cz, ce=ce)
def say(k, sz, se, items):
    """組成卡片的 say：和 say_data.own 同一個格式，多一個 own＝1"""
    from say_data import heads, wan as wz
    out = []
    for q in items[:3]:
        hm, hme = heads(wz(q['dz']), q['de'])
        out.append(dict(kz=q['kz'], ke=q['ke'], vz=wz(q['vz']), ve=q['ve'], tone=q['tone'] if q['tone'] in ('up', 'down', 'warn') else 'neu', dz=wz(q['dz']), de=q['de'], cz=q['cz'], ce=q['ce'], view=q['view'], hm=hm, hme=hme))
    h = HOW.get(k) or ({'hz': HOWX[k][0], 'he': HOWX[k][1]} if k in HOWX else {})
    return dict(items=out, sz=wz(sz), se=se, hz=list(h.get('hz') or []), he=list(h.get('he') or []), own=1)

def apply(chapters, L, N=None, E=None):
    """把做好的頁的讀數掛到卡片上；某一張出錯就跳過那一張（照舊用舊版的），不影響其他"""
    import reads_buy, reads_cycle, reads_sell, reads_lv, reads_lev
    F = {}; X = {}
    for m_ in (reads_buy, reads_cycle, reads_sell, reads_lv, reads_lev):
        F.update(m_.CARDS); HOWX.update(getattr(m_, 'HOWX', {}))
    for ch in chapters:
        for g in ch['groups']:
            for c in g['charts']: X.setdefault(c['k'], c)
    done, bad = [], []
    for k, fn in F.items():
        if k not in X: continue
        try:
            r = fn(L)
            if r: X[k]['say'] = say(k, *r); done.append(k)
        except Exception as e: bad.append('%s: %s' % (k, e))
    nl = lean(X, L)
    # 2026-11-17 使用者：「先把今天的主卡用 Opus 5.5 更新一遍，我看看效果」。判讀檔的 cards＝每段主卡的綜合判讀（AI 寫，日期要等於資料日），
    # 蓋掉規則產生的一句結論；沒有或過期就照舊用規則的句子。偏向（我們的看法）照舊由 leans.py 決定
    nc = 0
    if N and N.get('date') == L['meta']['bar_date']:
        ce = (E or {}).get('cards') or {} if (E or {}).get('date') == N.get('date') else {}
        for k, z in (N.get('cards') or {}).items():
            c = X.get(k)
            if c is None or not c.get('say') or not z: continue
            c['say']['sz'] = z; c['say']['se'] = ce.get(k) or c['say'].get('se') or z; c['say']['ai'] = 1; nc += 1
    return dict(done=len(done), bad=bad, lean=nl, cards=nc)

def lean(X, L):
    """每張指標卡的偏向（leans.py，2026-11-17 使用者：「指標偏多還是空要有」）：放成讀數裡的「我們的看法」（view＝1），排在最前面；原本的看法換掉"""
    import leans
    n, bad = 0, []
    for k, fn in leans.FN.items():
        c = X.get(k)
        if c is None or not c.get('say') or c['say'].get('copy'): continue
        try: v = fn(L)
        except Exception as e: bad.append('%s: %s' % (k, e)); continue
        if not v: continue
        t, vz, ve, dz, de, cz, ce = v
        y = c['say']; y['items'] = [q for q in y.get('items') or [] if not q.get('view')]
        y['items'].insert(0, dict(kz='我們的看法', ke='Our view', vz=vz, ve=ve, tone=t if t in ('up', 'down') else 'neu', dz=dz, de=de, cz=cz, ce=ce, view=1, hm='', hme='')); n += 1
    return dict(n=n, bad=bad)
