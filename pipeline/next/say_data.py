# -*- coding: utf-8 -*-
"""卡片的異動訊號（sig）、資料來源（src，見 src_lab.py）和讀數的共用工具（heads、wan、own）。
2026-11-17 舊版網站刪除：讀數全部由 reads.py 和各頁 *_data.py 產生；原本從舊版面板抽的讀值、資料來源、訊號對照都已凍結或改寫（sigmap.json、src.json）。"""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
SIG = {'oc-puell-multiple': 'p6v', 'cost': 'levels', 'ov-px': 'levels', 'stab': 'stab', 'cohort': 'cohort'}
# ── 卡片上的結論標題（2026-11-11）：不要「標籤：數字」把大數字重講一遍，挑讀值說明裡第一句白話 ──
NUM = re.compile(r'[−+\-]?\$?\d[\d,.:/]*\s?(?:%|‰|×|倍|萬顆|萬|顆|天|個|[KMB]\b)?')
def _nums(t): return len(NUM.findall(t))
def _strip(t): return re.sub(r'\s+', ' ', re.sub(r'（[^（）]*）|\([^()]*\)', '', t)).strip(' ，,；;：:')
DEFN = ('多單被清算多', 'More long liq', '美國現貨的代表', 'The US spot')   # 這幾句是定義，不是結論
LISTY = ('圖上', '怎麼', '過去', '最近', '前幾', '歷次', '每輪', '頂部', '底部', '週期', '兩條', '規則', '樣本', 'How', 'On the chart', 'Past', 'Recent', 'Tops', 'Bottoms', 'Rule', 'Last', 'Colour', 'Color', 'Each', 'Deepest', 'Sample', '正 Gamma', 'Largest', '美國現貨的代表', 'The US spot', '多單被清算多', 'More long liq')   # 最後幾個是定義或標籤，不是結論
def meaning(d, en=False, at=None):
    """從一段讀值說明挑一句白話當標題：數字最多一個、不太長；「數字：意思」這種取冒號後面。挑不到回傳空字串"""
    if not d: return ''
    d = re.sub(r'（[^（）]*）|\([^()]*\)', '', d)   # 括號先拿掉，英文括號裡的「incl. ETF」才不會被當成句號切開
    ss = [x for x in re.split(r'(?<=[.!?;])\s+' if en else r'[。！？；]', d) if x.strip()][:3]
    if at is not None and at < len(ss):   # 英文先試和中文同一句，兩種語言講的才是同一件事
        r = meaning(ss[at], en)
        if r: return r
    if at is not None: return ''
    mx = 92 if en else 40; mw = 18 if en else 6
    ok = lambda t: not t.startswith(DEFN) and not re.search(r'\d\s?\S{0,2}$', t) and _nums(t) <= 1 and 4 <= len(t) <= mx and len(NUM.sub('', t).strip(' ，,、')) >= mw   # 去掉數字後還要有一段話，不能只是「一年最低 34.5%」
    for s0 in ss:
        s = _strip(s0).rstrip('.')
        if not s: continue
        c = ': ' if en else '：'
        if _nums(s) == 0 and ok(s): return s
        if c in s:
            a, b = s.split(c, 1); a, b = a.strip(), b.strip()
            if _nums(a) >= 1 and ok(b): return b[0].upper() + b[1:] if en else b
            # 冒號前面沒有數字、本身是一個狀態（「底部組合成立」「集中認賠中」）才用；「最近幾段：…」「Tops: …」這種是清單的標籤，不用
            if _nums(a) == 0 and (12 if en else 5) <= len(a) <= (40 if en else 16) and not a.startswith(LISTY): return a
            continue
        if ok(s): return s
    return ''
def heads(dz, de):
    """中文挑一句；英文挑同一句（挑不到就兩邊都不用，避免兩種語言的標題講不同的事）"""
    z = meaning(dz)
    if not z: return '', ''
    zs = [x for x in re.split(r'[。！？；]', re.sub(r'（[^（）]*）|\([^()]*\)', '', dz)) if x.strip()][:3]
    i = next((j for j, x in enumerate(zs) if meaning(x) == z), None)
    e = meaning(de, True, i) if i is not None else ''
    if e and _nums(z) == 0 and _nums(e) > 0: e = ''   # 句子對不上（中文沒有數字、英文有）就兩邊都不用
    if e: e = e[0].upper() + e[1:]
    return (z, e) if e else ('', '')
# 中文裡一萬顆以上寫成「萬顆」，和圖上、圖例一致
def wan(t):
    def f(m):
        sg, n = m.group(1) or '', int(m.group(2).replace(',', ''))
        if n < 10000: return m.group(0)
        v = n / 1e4; return sg + (('%.1f' % v) if v >= 10 else ('%.2f' % v)).rstrip('0').rstrip('.') + ' 萬顆'
    return re.sub(r'([−+\-]?)(\d{1,3}(?:,\d{3})+)\s?顆', f, t or '')
LAB = re.compile(r'^(圖上|怎麼看|小心)')


def own(items, sz='', se=''):
    """新版首頁自己才有的圖（舊版沒有對應的面板）直接帶讀值。items＝[(標題中, 標題英, 數值中, 數值英, 語氣 up／down／warn／neu, 說明中, 說明英)]。
    attach() 遇到已經有 say 的圖會沿用（setdefault），不會蓋掉。"""
    out = []
    for kz, ke, vz, ve, tone, dz, de in items:
        hm, hme = heads(wan(dz), de)
        out.append(dict(kz=kz, ke=ke, vz=wan(vz), ve=ve, tone=tone if tone in ('up', 'down', 'warn') else 'neu', dz=wan(dz), de=de, cz='', ce='', view=0, hm=hm, hme=hme))
    return dict(items=out, sz=wan(sz), se=se, hz=[], he=[])

SIGK = json.load(open(os.path.join(HERE, 'sigmap.json'), encoding='utf-8'))   # 訊號的舊版圖 id → 新版圖代號（2026-11-17 從舊版凍結；signals.py 的 chart 欄位沿用舊版的 id）


def attach(chapters, L):
    import src_lab
    X = {}
    for ch in chapters:
        for g in ch['groups']:
            for c in g['charts']: X.setdefault(c['k'], c)
    nsrc = src_lab.apply(X, L)
    n = 0
    for s_ in (L.get('signals') or {}).get('items') or []:
        k = SIG.get(s_.get('chart')) or SIGK.get(s_.get('chart'))
        c = X.get(k) if k else None
        if c is None: continue
        g = lambda f: ((s_.get(f) or {}).get('zh') or '', (s_.get(f) or {}).get('en') or '')
        c.setdefault('sig', []).append(dict(tz=g('title')[0], te=g('title')[1], fz=g('fig')[0], fe=g('fig')[1], mz=g('means')[0], me=g('means')[1], rz=g('rule')[0], re=g('rule')[1], new=1 if s_.get('new') else 0)); n += 1
    # 組成／走勢這類附屬的圖沒有自己的讀數，沿用主圖的結論和資料來源
    for k_, src_ in (('regc', 'regime'), ('dawnc', 'dawn'), ('p6v', 'p6'), ('radarv', 'radar'), ('tm', 'tmh'), ('soprf', 'sopr')):
        a_, b_ = X.get(k_), X.get(src_)
        if a_ is not None and b_ is not None and b_.get('src') and not a_.get('src'): a_['src'], a_['srce'] = b_['src'], b_['srce']
        if a_ is not None and b_ is not None and b_.get('say') and not (a_.get('say') and (a_['say']['items'] or a_['say']['sz'])):
            a_['say'] = dict(copy=1, items=list(b_['say']['items']), sz=b_['say']['sz'], se=b_['say']['se'], hz=(a_.get('say') or {}).get('hz') or [], he=(a_.get('say') or {}).get('he') or [])
    have = [c for c in X.values() if c.get('say') and (c['say']['items'] or c['say']['sz'])]
    for c in X.values():
        if c.get('say') and not (c['say']['items'] or c['say']['sz'] or c['say']['hz']): del c['say']
    return dict(charts=len(have), items=sum(len(c['say']['items']) for c in have), sig=n, src=nsrc, total=len(X), none=sorted(k for k, c in X.items() if not c.get('say') and not c.get('na')))
