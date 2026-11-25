#!/usr/bin/env python3
"""2 年期美債殖利率減聯準會目標利率上限（2026-11-12 新增，參考 Glassnode 週報的做法）。

2 年期殖利率反映市場認為未來兩年政策利率平均會在哪裡：高於現在的目標利率＝債市在押加息，低於＝在押降息。
資料都是官方來源、免金鑰：
- 2 年期殖利率：美國財政部每日殖利率曲線（home.treasury.gov，一年一個 CSV，2021 年起每天抓 6 個左右的小檔）。
- 聯準會目標利率：紐約聯準銀行的 EFFR API，每天附目標區間（targetRateTo＝上限）；最新幾天還沒公布時沿用上一個值。
本機連不到 FRED 的時候也能驗算，所以不用 FRED。任何一邊取不到就整項不出（頁面顯示沒有資料），不推估。只作讀值。"""
import bisect, csv, datetime as dt, io, json, os

START = '2021-06-01'
_EP = dt.date(1970, 1, 1)
dn = lambda s: (dt.date.fromisoformat(s) - _EP).days
TSY = 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/%d/all?type=daily_treasury_yield_curve&field_tdr_date_value=%d&page&_format=csv'
EFFR = 'https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json?startDate=2021-01-01&endDate=%s'


def parse_tsy(text):
    out = {}
    for r in csv.DictReader(io.StringIO(text or '')):
        try:
            m, d, y = r['Date'].split('/'); out['%s-%s-%s' % (y, m, d)] = float(r['2 Yr'])
        except Exception:
            pass
    return out


def parse_effr(js):
    if isinstance(js, str): js = json.loads(js)
    return {x['effectiveDate']: float(x['targetRateTo']) for x in (js or {}).get('refRates') or [] if x.get('targetRateTo') is not None}


# 2026-11-25 過去幾年的殖利率存起來，每天只抓今年那個檔：財政部網站一個檔要 15–20 秒，原本每天重抓 2021 年起全部（約 110 秒，
# 每日資料最慢的一段之一；倉庫考慮改私有，Actions 要算額度）。舊年度的數字不會再變；過完年 10 天才存，年底最後幾天和修正都出來了
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coc_cache', 'tsy2y.json')


def fetch(get, last):
    """get＝collect.py 的 get(url)（JSON 回傳物件、其他回傳文字）。回傳 (2 年期殖利率, 目標利率上限)，都是 {日期: %}。"""
    try: C = json.load(open(CACHE, encoding='utf-8'))
    except Exception: C = {}
    y2, ly, new = {}, int(last[:4]), False
    for y in range(2021, ly + 1):
        if str(y) in C and y < ly: y2.update(C[str(y)]); continue
        d = parse_tsy(get(TSY % (y, y))); y2.update(d)
        if y < ly and len(d) > 200 and last >= '%d-01-10' % (y + 1): C[str(y)] = d; new = True
    if new:
        with open(CACHE, 'w', encoding='utf-8') as f: json.dump(C, f, separators=(',', ':'), sort_keys=True)
    return y2, parse_effr(get(EFFR % last))


def build(y2, ff, last):
    fk = sorted(ff)
    def F(d):
        i = bisect.bisect_right(fk, d) - 1
        return ff[fk[i]] if i >= 0 else None
    D = [d for d in sorted(y2) if START <= d <= last and F(d) is not None]
    if len(D) < 250 or not fk or dn(D[-1]) - dn(fk[-1]) > 10 or dn(last) - dn(D[-1]) > 10: return None   # 任何一邊太舊就不出
    g = [round(y2[d] - F(d), 2) for d in D]
    mx = max(range(len(g)), key=lambda i: g[i]); mn = min(range(len(g)), key=lambda i: g[i])
    k = len(g) - 1
    while k > 0 and (g[k - 1] > 0) == (g[-1] > 0): k -= 1
    last_chg = next((fk[i] for i in range(len(fk) - 1, 0, -1) if ff[fk[i]] != ff[fk[i - 1]]), None)
    return dict(date=D[-1], y2=y2[D[-1]], ff=F(D[-1]), ff_date=fk[-1], ff_changed=last_chg, gap=g[-1], gap20=g[-21] if len(g) > 21 else None,
                max=dict(v=g[mx], d=D[mx]), min=dict(v=g[mn], d=D[mn]), side_since=D[k], since=D[0], n=len(D),
                rows=[[dn(d), y2[d], F(d), g[i]] for i, d in enumerate(D)],
                note='2 年期美債殖利率（美國財政部）減聯準會目標利率上限（紐約聯準銀行），單位百分點；只作讀值')
