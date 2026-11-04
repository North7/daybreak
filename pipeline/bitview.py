"""Bitview（https://bitview.space，Bitcoin Research Kit 開源專案的公開 API；免費、不用金鑰、當天更新）。
2026-11-04 使用者決定：「短期持有者成本 vs 真實市場均價」改用 Bitview，同時新增短期持有者成本帶（Murphy 的「短期持有者成本基礎模型」）
與 6–12／12–18 個月持幣成本線（wander）。
為什麼換：真實市場均價 Bitview 和 CheckOnChain（兩家各自從節點算）2016 年以來差距中位數 0.01%、最大 0.38%；
bitcoin-data 過去一年一直高 0.6–2.1%，而且晚約 7 天。短期持有者成本三家差約 0.1%。
做法：每條序列一次請求（day1，2011 起），只留已收完的日子（日期早於今天 UTC；當天的值是盤中）。
6–12 個月成本＝6–9 個月與 9–12 個月兩段的實現市值合計 ÷ 供給合計（Bitview 沒有 6–12 個月這一段）。
每天另讀 CheckOnChain 的真實市場均價驗算（collect.py 在兩家差超過 0.5% 時記進 errors）。
失敗時用上一次成功的快取 coc_cache/bitview.json（超過 4 天不再沿用，見 coc._cache），再失敗由 collect.py 退回 bitcoin-data，頁面標示來源。
Bitview 會改序列名稱（API 0.13 版，改動列在 https://bitview.space/api 的 What changed）：抓不到時先查那裡。"""
import datetime as dt, json, os, subprocess
import coc

API = 'https://bitview.space/api/series/{}/day1?start={}'
PAGE = 'https://bitview.space'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coc_cache', 'bitview.json')   # 放在 coc_cache：每日工作流程會一起提交
START = 730   # day1 的第 0 筆是 2009-01-01，第 730 筆是 2011-01-01
NAMES = ('date', 'price_close', 'sth_realized_price', 'true_market_mean', 'age_6m_to_9m_realized_cap', 'age_9m_to_1y_realized_cap',
         'age_6m_to_9m_supply', 'age_9m_to_1y_supply', 'age_1y_to_18m_realized_price')
COLS = ('px', 'sth', 'tmm', 'c612', 'c1218')   # 快取每列：[日期, 價格, 短期持有者成本, 真實市場均價, 6–12 個月成本, 12–18 個月成本]
COC_TMM = 'https://charts-cdn.checkonchain.com/btconchain/cointime/cointime_pricing_all_1/cointime_pricing_all_1_light.html'


def _get(name):
    out = subprocess.run(['curl', '-sS', '--max-time', '60', API.format(name, START)], capture_output=True, text=True).stdout
    j = json.loads(out) if out.strip().startswith('{') else {}
    if not isinstance(j.get('data'), list): raise RuntimeError(f'Bitview {name}：{out[:160]}')
    return j['start'], j['data']


def _r(v):
    if v is None or v != v or v <= 0: return None
    return round(v) if v >= 1000 else round(v, 2)


def fetch(today=None):
    today = today or dt.datetime.now(dt.timezone.utc).date().isoformat()
    S = {n: _get(n) for n in NAMES}
    if len({s for s, _ in S.values()}) != 1 or len({len(d) for _, d in S.values()}) != 1:
        raise RuntimeError('Bitview 各序列的起點或長度不一致：' + ', '.join(f'{n} {s}+{len(d)}' for n, (s, d) in S.items()))
    g = {n: d for n, (_, d) in S.items()}
    rows = []
    for i, d in enumerate(g['date']):
        if d >= today: continue
        sup = (g['age_6m_to_9m_supply'][i] or 0) + (g['age_9m_to_1y_supply'][i] or 0)
        c612 = ((g['age_6m_to_9m_realized_cap'][i] or 0) + (g['age_9m_to_1y_realized_cap'][i] or 0)) / sup if sup > 1 else None
        rows.append([d] + [_r(v) for v in (g['price_close'][i], g['sth_realized_price'][i], g['true_market_mean'][i], c612, g['age_1y_to_18m_realized_price'][i])])
    if len(rows) < 5000 or not rows[-1][2] or not rows[-1][3]: raise RuntimeError(f'Bitview 只有 {len(rows)} 天或最新一天缺值，格式可能改了')
    return rows


def get():
    """回傳 (rows, 狀態說明)。失敗時用上一次成功的快取（超過 4 天就讓錯誤往上丟）"""
    try:
        rows = fetch(); coc._save(CACHE, PAGE, rows, keep=10000)
        return rows, 'live'
    except Exception as e:
        cj = coc._cache(CACHE)
        return cj['rows'], f'cache {cj["fetched_utc"]}（{e}）'


def cols(rows):
    """{'px': {date: 值}, 'sth': …, 'tmm': …, 'c612': …, 'c1218': …}；缺值的日子不放"""
    return {k: {r[0]: r[j + 1] for r in rows if r[j + 1] is not None} for j, k in enumerate(COLS)}


def check_tmm(tmm):
    """和 CheckOnChain 的真實市場均價對照最近一個共同日期"""
    ct = coc._trace(coc._traces(COC_TMM), 'True Market Mean')
    d = max(x for x in ct if x in tmm)
    return dict(date=d, bitview=round(tmm[d]), checkonchain=round(ct[d]), diff_pct=round((tmm[d] / ct[d] - 1) * 100, 2))
