#!/usr/bin/env python3
"""2 年期美債殖利率減聯準會目標利率上限（2026-11-12 新增，參考 Glassnode 週報的做法）。

2 年期殖利率反映市場認為未來兩年政策利率平均會在哪裡：高於現在的目標利率＝債市在押加息，低於＝在押降息。
資料都是官方來源、免金鑰：
- 2 年期殖利率：美國財政部每日殖利率曲線（home.treasury.gov，一年一個 CSV，2021 年起每天抓 6 個左右的小檔）。
- 聯準會目標利率：紐約聯準銀行的 EFFR API，每天附目標區間（targetRateTo＝上限）；最新幾天還沒公布時沿用上一個值。
本機連不到 FRED 的時候也能驗算，所以不用 FRED。任何一邊取不到就整項不出（頁面顯示沒有資料），不推估。只作讀值。"""
import bisect, csv, datetime as dt, io, json

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


def fetch(get, last):
    """get＝collect.py 的 get(url)（JSON 回傳物件、其他回傳文字）。回傳 (2 年期殖利率, 目標利率上限)，都是 {日期: %}。"""
    y2 = {}
    for y in range(2021, int(last[:4]) + 1): y2.update(parse_tsy(get(TSY % (y, y))))
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
