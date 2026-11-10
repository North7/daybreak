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
SIG = {'oc-puell-multiple': 'p6v', 'cost': 'levels', 'ov-px': 'levels', 'stab': 'stab', 'cohort': 'cohort'}
TONE = {'up': 'up', 'down': 'down', 'warn': 'warn'}
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
        return dict(kz=z['k'], ke=e['k'], vz=z['v'], ve=e['v'], tone=TONE.get(z['tone'], 'neu'), dz=z['d'], de=e['d'], cz=z.get('chg') or '', ce=e.get('chg') or '', view=z['view'])
    def say(k):
        c = X.get(k)
        if c is None: return None
        return c.setdefault('say', dict(items=[], sz='', se='', hz=[], he=[]))
    chart2key = {}
    for z, e in zip(Z, E):
        pid = z['id'][3:] if z['id'].startswith('pn-') else z['id']
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
        if a_ is not None and b_ is not None and b_.get('say') and not (a_.get('say') and (a_['say']['items'] or a_['say']['sz'])):
            a_['say'] = dict(copy=1, items=list(b_['say']['items']), sz=b_['say']['sz'], se=b_['say']['se'], hz=(a_.get('say') or {}).get('hz') or [], he=(a_.get('say') or {}).get('he') or [])
    have = [c for c in X.values() if c.get('say') and (c['say']['items'] or c['say']['sz'])]
    for c in X.values():
        if c.get('say') and not (c['say']['items'] or c['say']['sz'] or c['say']['hz']): del c['say']
    return dict(charts=len(have), items=sum(len(c['say']['items']) for c in have), views=sum(1 for c in have for i in c['say']['items'] if i['view']), sig=n, total=len(X), none=sorted(k for k, c in X.items() if not c.get('say') and not c.get('na')))
