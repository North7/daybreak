"""Tidemark 頂部／底部訊號的歷史（2026-11-09 使用者要求「借鑑 Tidemark 的歷史圖」）。

Tidemark（tidemark.aronlab.dev，第三方公開模型）沒有獨立的歷史檔，歷史只內嵌在頁面裡（`D = {...}`，
2011 起每週、近一年每日）。這裡每天抓一次頁面、取出需要的欄位；抓不到或格式變了就沿用上一份 data/latest.json 的
cycle.tidemark.hist，標 stale，不讓流程失敗。只作讀值、不連動倉位、不進預測調整。

輸出 rows：[天數(1970 起), 價格, 頂部訊號, 熱度, 時機, 底部訊號, 冷度]
"""
import datetime as dt, json, os, re

URL = 'https://tidemark.aronlab.dev/'
KEYS = ['p', 'sig', 'heat', 'tim', 'bsig', 'cold']
E0 = dt.date(1970, 1, 1)


def _r(v, k):
    if v is None: return None
    if k == 'p': return round(v, 2) if v < 100 else round(v)
    return round(v, 1)


def parse(html):
    m = re.search(r'(?:const|var|let)\s+D\s*=\s*', html or '')
    if not m: raise ValueError('頁面裡找不到 D = {...}')
    D, _ = json.JSONDecoder().raw_decode(html[m.end():])
    miss = [k for k in ['d'] + KEYS if k not in D]
    if miss: raise ValueError('缺欄位 ' + ','.join(miss))
    rows = []
    for i, d in enumerate(D['d']):
        r = [(dt.date.fromisoformat(d) - E0).days] + [_r(D[k][i], k) for k in KEYS]
        if r[1] is None: continue
        rows.append(r)
    rows.sort(key=lambda r: r[0])
    if len(rows) < 500: raise ValueError(f'只有 {len(rows)} 筆，太少')
    return rows


def build(get, tm_latest=None):
    """get：collect.py 的 get（非 JSON 回傳文字）；tm_latest：Tidemark latest.json（取歷次頂底與本輪低點）"""
    tl = tm_latest or {}
    ct = ((tl.get('bottom') or {}).get('cycle_test') or {})
    low = (ct.get('current_low') or {})
    meta = dict(tops=tl.get('cycle_tops') or [], bottoms=tl.get('cycle_bottoms') or [],
                low=dict(date=low.get('date'), price=low.get('price'), status=ct.get('status'), decisive_date=ct.get('decisive_date')) if low.get('date') else None)
    try:
        rows = parse(get(URL))
        return dict(rows=rows, from_=(E0 + dt.timedelta(rows[0][0])).isoformat(), to=(E0 + dt.timedelta(rows[-1][0])).isoformat(), stale=False, **meta)
    except Exception as e:
        try:
            old = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'latest.json')))
            h = ((old.get('cycle') or {}).get('tidemark') or {}).get('hist')
            if h and h.get('rows'):
                h = dict(h, stale=True, error=str(e)[:120]); h.update({k: v for k, v in meta.items() if v})
                return h
        except Exception:
            pass
        raise
