# -*- coding: utf-8 -*-
"""把現有網站每個面板的讀值（extract_interp.py 抽出來的 interp.zh.json / interp.en.json）和異動訊號掛到原型的圖上。
一張圖得到：say＝結論和讀值（items）、一句話（sz/se）、「怎麼讀這張圖」（hz/he，分段）；sig＝當天的異動。"""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
MAP = {'regime': ['regime'], 'dawn': ['dawn'], 'rup': ['rup'], 'hnupl': ['hnupl'], 'p20': ['p20'], 'aviv': ['aviv'], 'rrisk': ['rrisk'], 'cyccmp': ['cyccmp'], 'capeff': ['capeff'], 'pl': ['pl'], 'tmh': ['tmh'], 'path': ['path'], 'cycle-1': ['stage'],
       'quant': ['quant'], 'urpd': ['urpd'], 'profit': ['profit'], 'sthband': ['sthgap'], 'agecost': ['agecost'], 'conc': ['conc'], 'sopr': ['sopr'], 'sthpnl': ['pnlr'], 'sthsig': ['sthsig'], 'conf': ['conf'], 'npl': ['npl'], 'npl365': ['npl365'], 'rpl': ['rpl'], 'rloss': ['rloss'], 'ssr': ['ssr'], 'sec': ['sec'], 'mom': ['mom'],
       'cohort': ['cohort'], 'lthc': ['lthnet'], 'lsrchg': ['lsrchg'], 'sthd': ['sthd'], 'agepl': ['agepl'], 'dorm': ['dorm'], 'lthloss': ['lthloss', 'lthrl'], 'whale': ['whale', 'whalet'], 'pullback': ['pullback'],
       'cd': ['k20'], 'sx': ['sx'], 'levels': ['levels'], 'long': ['long'], 'mon': ['mon'], 'market-2': ['legs'],
       'etf': ['etf'], 'pr-us': ['pr-us', 'pr-asia', 'pr-perp'], 'kp': ['kp'], 'exflow': ['exflow'], 'ad': ['ad'], 'dmd': ['dmd'], 'capflow': ['capflow'], 'grad': ['grad'], 'stab': ['stab'], 'rcliq': ['rcliq'], 'stkrel': ['stk'], 'fng': ['fng'], 'wiki': ['wiki'], 'cot': ['cot'],
       'vol': ['vol'], 'ivt': ['ivt'], 'basis': ['basis'], 'fh': ['fh'], 'oih': ['oih'], 'lsa': ['lsa'], 'liq': ['liq'], 'lqv': ['lqv'], 'oi': ['oi'], 'strike': ['strike'], 'gex': ['gex'], 'prem': ['prem'], 'svd': ['svd'], 'tk': ['tk'], 'book': ['book']}
# 一個面板對到好幾張圖時，哪幾列讀值給哪一張（沒列的給第一張）
SPLIT = {'pr-us': {2: 'pr-asia', 3: 'pr-perp'}, 'lthloss': {4: 'lthrl', 5: 'lthrl', 6: 'lthrl'}}
# 「這些數字代表什麼」那幾個總表面板：第幾列給哪幾張圖
IDX = {'onchain-1': {2: ['exch'], 3: ['miners'], 4: ['miners', 'hashr'], 5: ['miners']}, 'market-1': {6: ['pi']},
       'flows-1': {0: ['etf'], 1: ['etf'], 7: ['etf'], 2: ['macro'], 3: ['macro'], 4: ['macro'], 5: ['rcliq'], 6: ['stab']},
       'deriv-1': {0: ['vol'], 2: ['vol'], 4: ['pcr'], 5: ['pcr'], 6: ['oi']}, 'exit-1': {1: ['p20'], 2: ['p6']}}
SRCP = {'p6': ['p6', 'p6v'], 'radar': ['radar', 'radarv']}
SIG = {'oc-puell-multiple': 'p6v', 'cost': 'levels', 'ov-px': 'levels', 'stab': 'stab', 'cohort': 'cohort'}
TONE = {'up': 'up', 'down': 'down', 'warn': 'warn'}
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

def attach(chapters, L):
    try:
        Z = json.load(open(os.path.join(HERE, 'interp.zh.json'), encoding='utf-8')); E = json.load(open(os.path.join(HERE, 'interp.en.json'), encoding='utf-8'))
    except Exception:
        return dict(charts=0, items=0)
    if len(E) != len(Z): E = Z
    X = {}
    for ch in chapters:
        for g in ch['groups']:
            for c in g['charts']: X.setdefault(c['k'], c)
    def item(z, e):
        return dict(kz=z['k'], ke=e['k'], vz=wan(z['v']), ve=e['v'], tone=TONE.get(z['tone'], 'neu'), dz=wan(z['d']), de=e['d'], cz=wan(z.get('chg') or ''), ce=e.get('chg') or '', view=z['view'], **dict(zip(('hm', 'hme'), heads(wan(z['d']), e['d']))))
    def say(k):
        c = X.get(k)
        if c is None: return None
        return c.setdefault('say', dict(items=[], sz='', se='', hz=[], he=[]))
    chart2key = {}
    for z, e in zip(Z, E):
        pid = z['id'][3:] if z['id'].startswith('pn-') else z['id']
        for k in SRCP.get(pid, []):   # 沒有讀值、但有資料來源的面板
            if z.get('src') and k in X and not X[k].get('src'): X[k]['src'], X[k]['srce'] = z['src'], e.get('src') or z['src']
        if pid in IDX:
            for i, keys in IDX[pid].items():
                if i < len(z['items']):
                    for k in keys:
                        y = say(k)
                        if y is not None: y['items'].append(item(z['items'][i], e['items'][i] if i < len(e['items']) else z['items'][i]))
            continue
        keys = MAP.get(pid)
        if not keys: continue
        for cid in z['charts']: chart2key[cid] = keys[0]
        for k in keys:   # 資料來源：舊版面板右上那一行（例：Coinalyze · 11/9）
            if z.get('src') and k in X and not X[k].get('src'): X[k]['src'], X[k]['srce'] = z['src'], e.get('src') or z['src']
        sp = SPLIT.get(pid, {})
        for i, it in enumerate(z['items']):
            y = say(sp.get(i, keys[0]))
            if y is not None: y['items'].append(item(it, e['items'][i] if i < len(e['items']) else it))
        for k in keys:
            y = say(k)
            if y is None: continue
            rz, re_ = list(z.get('rd') or []), list(e.get('rd') or [])
            # 「怎麼讀這張圖」前面如果有一句「現在…」，那是當下的讀數，拿來當一句話
            if rz and not rz[0].startswith('#') and len(rz) > 1:
                nz = re.sub(r'^現在', '', rz[0]).strip(); ne = re.sub(r'^Now', '', re_[0]).strip() if re_ else nz
                if not y['sz']: y['sz'], y['se'] = nz, ne
                rz, re_ = rz[1:], re_[1:]
            if z.get('says') and k == keys[0]: y['sz'], y['se'] = z['says'][0], (e.get('says') or z['says'])[0]
            y['sz'] = wan(y['sz'])
            y['hz'] = [LAB.sub(lambda m: m.group(1) + '：', s_) for s_ in rz if not s_.startswith('#')]; y['he'] = [s_ for s_ in re_ if not s_.startswith('#')]
    n = 0
    for s_ in (L.get('signals') or {}).get('items') or []:
        k = SIG.get(s_.get('chart')) or chart2key.get(s_.get('chart'))
        c = X.get(k) if k else None
        if c is None: continue
        g = lambda f: ((s_.get(f) or {}).get('zh') or '', (s_.get(f) or {}).get('en') or '')
        c.setdefault('sig', []).append(dict(tz=g('title')[0], te=g('title')[1], fz=g('fig')[0], fe=g('fig')[1], mz=g('means')[0], me=g('means')[1], rz=g('rule')[0], re=g('rule')[1], new=1 if s_.get('new') else 0)); n += 1
    # 組成／走勢這類附屬的圖沒有自己的面板，沿用主圖的結論
    for k_, src_ in (('regc', 'regime'), ('dawnc', 'dawn'), ('p6v', 'p6'), ('tm', 'tmh'), ('soprf', 'sopr')):
        a_, b_ = X.get(k_), X.get(src_)
        if a_ is not None and b_ is not None and b_.get('src') and not a_.get('src'): a_['src'], a_['srce'] = b_['src'], b_['srce']
        if a_ is not None and b_ is not None and b_.get('say') and not (a_.get('say') and (a_['say']['items'] or a_['say']['sz'])):
            a_['say'] = dict(copy=1, items=list(b_['say']['items']), sz=b_['say']['sz'], se=b_['say']['se'], hz=(a_.get('say') or {}).get('hz') or [], he=(a_.get('say') or {}).get('he') or [])
    have = [c for c in X.values() if c.get('say') and (c['say']['items'] or c['say']['sz'])]
    for c in X.values():
        if c.get('say') and not (c['say']['items'] or c['say']['sz'] or c['say']['hz']): del c['say']
    return dict(charts=len(have), items=sum(len(c['say']['items']) for c in have), views=sum(1 for c in have for i in c['say']['items'] if i['view']), sig=n, total=len(X), none=sorted(k for k, c in X.items() if not c.get('say') and not c.get('na')))
