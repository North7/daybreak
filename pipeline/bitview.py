"""Bitview（https://bitview.space，Bitcoin Research Kit 開源專案的公開 API；免費、不用金鑰、晚 1 天）。
2026-11-04 使用者決定：「短期持有者成本 vs 真實市場均價」改用 Bitview，同時新增短期持有者成本帶與 6–12／12–18 個月持幣成本。
為什麼換：真實市場均價 Bitview 和 CheckOnChain（兩家各自從節點算）2016 年以來差距中位數 0.01%、最大 0.38%；
bitcoin-data 過去一年一直高 0.6–2.1%，而且晚約 7 天。短期持有者成本三家差約 0.1%。
2026-11-04 第二批（使用者要求）：長短期持有者成本、aSOPR、長期持有者 SOPR 也改用這裡（bitcoin-data 版晚 6–7 天）；
加 3–6 個月持幣成本、按地址餘額分層的持幣量（鯨魚分層，取代被 Cloudflare 擋下的 BitInfoCharts），
以及任一天的長短期持有者籌碼分布（urpd_rows，給長短期持有者籌碼圖的「30 天前」用實際值）。
做法：每條序列一次請求（day1，2011 起），只留已收完的日子（日期早於今天 UTC；當天的值是盤中）。
6–12 個月成本＝6–9、9–12 個月兩段的實現市值合計 ÷ 供給合計；3–6 個月＝3–4、4–5、5–6 個月三段合計（Bitview 沒有這兩段）。
每天另讀 CheckOnChain 的真實市場均價驗算（collect.py 在兩家差超過 0.5% 時記進 errors）。
失敗時用上一次成功的快取 coc_cache/bitview.json（超過 4 天不再沿用，見 coc._cache），collect.py 再看各項要不要退回 bitcoin-data。
Bitview 會改序列名稱（API 0.13 版，改動列在 https://bitview.space/api 的 What changed）：抓不到時先查那裡。"""
import datetime as dt, json, os, subprocess, time
import coc

API = 'https://bitview.space/api/series/{}/day1?start={}'
URPD = 'https://bitview.space/api/urpd/{}/{}?agg=lin1000'
PAGE = 'https://bitview.space'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coc_cache', 'bitview.json')   # 放在 coc_cache：每日工作流程會一起提交
START = 730   # day1 的第 0 筆是 2009-01-01，第 730 筆是 2011-01-01
_band = lambda bands: ([f'age_{b}_realized_cap' for b in bands], [f'age_{b}_supply' for b in bands])
# 快取每列：[日期] + COLS；每欄是 (Bitview 序列, 小數位數) 或 (實現市值序列, 供給序列) 合併算出的成本
COLS = [('px', 'price_close', 2), ('sth', 'sth_realized_price', 2), ('tmm', 'true_market_mean', 2),
        ('c612', _band(('6m_to_9m', '9m_to_1y')), 2), ('c1218', 'age_1y_to_18m_realized_price', 2),
        ('lth', 'lth_realized_price', 2), ('asopr', 'adjusted_sopr_24h', 4), ('lsopr', 'lth_sopr_24h', 4),
        ('c36', _band(('3m_to_4m', '4m_to_5m', '5m_to_6m')), 2), ('sths', 'sth_supply', 0), ('lths', 'lth_supply', 0),
        ('b1', 'balance_1_to_10_btc_supply', 0), ('b10', 'balance_10_to_100_btc_supply', 0), ('b100', 'balance_100_to_1k_btc_supply', 0),
        ('b1k', 'balance_1k_to_10k_btc_supply', 0), ('b10k', 'balance_10k_to_100k_btc_supply', 0), ('b100k', 'balance_over_100k_btc_supply', 0),
        ('sthp', 'sth_supply_in_profit_share', 2), ('rp', 'realized_price', 2),
        # 2026-11-05：循環資金流（實現市值加權的幣齡：1 個月內、1–2 年各佔全體實現市值的 %）
        ('cf1m', ('share', ['age_under_1h_realized_cap', 'age_1h_to_1d_realized_cap', 'age_1d_to_1w_realized_cap', 'age_1w_to_1m_realized_cap'], 'realized_cap'), 2),
        ('cf12', ('share', ['age_1y_to_18m_realized_cap', 'age_18m_to_2y_realized_cap'], 'realized_cap'), 2),
        ('ssopr', 'sth_sopr_24h', 4),
        ('lthrl', 'lth_realized_loss_sum_24h', 0),
        ('act', 'active_price', 2), ('c1m', 'age_1w_to_1m_realized_price', 2),
        # 2026-11-06 使用者要求（指標擴充，見 oc_extra.py）：供給分位成本線（全體供給依最後一次移動價格排序的第 q 百分位）、
        #   全體獲利供給 %、相對未實現獲利（未實現獲利 ÷ 市值 %）、全網每日實現虧損（美元）、每日銷毀幣天數、全網 SOPR
        ('q45', 'cost_basis_by_coin_p45', 2), ('q50', 'cost_basis_by_coin_median', 2), ('q55', 'cost_basis_by_coin_p55', 2), ('q60', 'cost_basis_by_coin_p60', 2),
        ('q65', 'cost_basis_by_coin_p65', 2), ('q75', 'cost_basis_by_coin_p75', 2), ('q85', 'cost_basis_by_coin_p85', 2), ('q95', 'cost_basis_by_coin_p95', 2),
        ('psip', 'supply_in_profit_share', 2), ('rup', ('share', ['unrealized_profit'], 'market_cap'), 2),
        ('rloss', 'realized_loss_sum_24h', 0), ('cdd', 'coindays_destroyed_sum_24h', 0), ('sopr', 'sopr_24h', 4)]   # 2026-11-05：活躍投資人成本（Cointime Active Price）、1 週–1 個月持幣成本（levels_viz／age_cost_viz）   # 2026-11-05：長期持有者已實現虧損（美元／日，stage_viz.lthrl_viz）   # 2026-11-05：短期持有者 SOPR（每日），給本站自製的短期壓力分數（stage_viz.stress_viz）   # 2026-11-04：短期持有者獲利比例（%）、全體實現價（關鍵價位圖）
KEYS = [k for k, _, _ in COLS]
COC_TMM = 'https://charts-cdn.checkonchain.com/btconchain/cointime/cointime_pricing_all_1/cointime_pricing_all_1_light.html'


def _curl(url):
    out = subprocess.run(['curl', '-sS', '--max-time', '60', url], capture_output=True, text=True).stdout
    return json.loads(out) if out.strip().startswith('{') else {'error': out[:160]}


def _get(name):
    j = _curl(API.format(name, START))
    if not isinstance(j.get('data'), list): raise RuntimeError(f'Bitview {name}：{str(j)[:160]}')
    return j['start'], j['data']


def _r(v, nd):
    if v is None or v != v or v < 0 or (nd == 2 and v == 0): return None
    if nd == 2: return round(v) if v >= 1000 else round(v, 2)
    return round(v, nd) if nd else round(v)


def fetch(today=None):
    today = today or dt.datetime.now(dt.timezone.utc).date().isoformat()
    _ns = lambda src: [src] if isinstance(src, str) else (src[1] + [src[2]] if src[0] == 'share' else src[0] + src[1])
    names = ['date'] + [n for _, src, _ in COLS for n in _ns(src)]
    S = {n: _get(n) for n in dict.fromkeys(names)}
    if len({s for s, _ in S.values()}) != 1:
        raise RuntimeError('Bitview 各序列的起點不一致：' + ', '.join(f'{n} {s}' for n, (s, d) in S.items()))
    g = {n: d for n, (_, d) in S.items()}; n0 = min(len(d) for d in g.values())
    rows = []
    for i, d in enumerate(g['date'][:n0]):
        if d >= today: continue
        row = [d]
        for k, src, nd in COLS:
            if isinstance(src, str): v = g[src][i]
            elif src[0] == 'share':
                den = g[src[2]][i] or 0; v = sum(g[c][i] or 0 for c in src[1]) / den * 100 if den > 0 else None
            else:
                sup = sum(g[s][i] or 0 for s in src[1]); v = sum(g[c][i] or 0 for c in src[0]) / sup if sup > 1 else None
            row.append(_r(v, nd))
        rows.append(row)
    if len(rows) < 5000 or not rows[-1][2] or not rows[-1][3]: raise RuntimeError(f'Bitview 只有 {len(rows)} 天或最新一天缺值，格式可能改了')
    return rows


def get():
    """回傳 (rows, 狀態說明)。失敗時用上一次成功的快取（超過 4 天就讓錯誤往上丟）"""
    try:
        rows = fetch()
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, 'w') as f:   # 同 coc._save，第一列記欄位名稱（舊快取沒有這列時照舊順序讀）
            f.write('{"fetched_utc": "%s", "source": "%s", "cols": %s, "rows": [\n' % (dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), PAGE, json.dumps(KEYS)))
            f.write(',\n'.join(json.dumps(r) for r in rows) + '\n]}\n')
        return rows, 'live'
    except Exception as e:
        cj = coc._cache(CACHE)
        keys = cj.get('cols') or KEYS[:5]
        return [[r[0]] + [r[1 + keys.index(k)] if k in keys and 1 + keys.index(k) < len(r) else None for k in KEYS] for r in cj['rows']], f'cache {cj["fetched_utc"]}（{e}）'


def cols(rows):
    """{'px': {date: 值}, 'sth': …}；缺值的日子不放"""
    return {k: {r[0]: r[j + 1] for r in rows if j + 1 < len(r) and r[j + 1] is not None} for j, k in enumerate(KEYS)}


def check_tmm(tmm):
    """和 CheckOnChain 的真實市場均價對照最近一個共同日期"""
    ct = coc._trace(coc._traces(COC_TMM), 'True Market Mean')
    d = max(x for x in ct if x in tmm)
    return dict(date=d, bitview=round(tmm[d]), checkonchain=round(ct[d]), diff_pct=round((tmm[d] / ct[d] - 1) * 100, 2))


def urpd_rows(date, w=2000):
    """某一天長短期持有者的籌碼分布，併成每 w 美元一格：dict(date, rows=[[價位下緣, STH, LTH]])（與 coc.get_cohort 同格式）。
    Bitview 依每顆幣的實際幣齡算（和 CheckOnChain 的長短期持有者分布圖同一套 Bitcoin Research Kit），逐筆 UTXO、未做實體調整"""
    out = {}
    for j, coh in enumerate(('sth', 'lth')):
        u = _curl(URPD.format(coh, date)); b = u.get('buckets') or {}
        if u.get('date') != date or not b.get('price'): raise RuntimeError(f'Bitview URPD {coh} {date}：{str(u)[:120]}')
        for p, s in zip(b['price'], b['supply']):
            k = int(p // w * w); out.setdefault(k, [0.0, 0.0])[j] += s or 0
        time.sleep(0.3)
    return dict(date=date, rows=[[k, round(v[0]), round(v[1])] for k, v in sorted(out.items())])


# 2026-11-05 使用者要求（籌碼結構＋集中度）：籌碼集中度＝全體 URPD 裡「最後一次移動價格在當天收盤 ±5% 內」的幣 ÷ 全部供給。
#   用 Bitview 的 log1000 分格（每格約 0.2%，2018 年的低價位也夠細）；歷史 2018 起一次補好（每 3 天一點、近 60 天每天），之後每天補新的一天。
#   2026-11-05 起網站上的集中度統一用這個（原本是 CheckOnChain URPD 2,000 美元一格 ÷ CoinMetrics 流通量，數字約低 1–3 個百分點、只有 10/01 起）。只作讀值
CONC = os.path.join(os.path.dirname(CACHE), 'conc.json')
URPD_ALL = 'https://bitview.space/api/urpd/all/{}?agg=log1000'


def conc_one(date):
    j = _curl(URPD_ALL.format(date)); b = j.get('buckets') or {}
    if j.get('date') != date or not b.get('price') or not j.get('supply'): raise RuntimeError(f'Bitview URPD all {date}：{str(j)[:120]}')
    c, tot = j['close'], j['supply']
    s = lambda k: sum(v for p, v in zip(b['price'], b['supply']) if v and c * (1 - k) <= p <= c * (1 + k))
    s5 = s(0.05)
    return dict(date=date, close=round(c, 2), c5=round(s5 / tot * 100, 2), c10=round(s(0.10) / tot * 100, 2), btc5=round(s5), supply=round(tot))


def conc_rows(last, max_new=20):
    """回傳 (rows=[[日期, 收盤, ±5% %, ±10% %]], 最新一天的明細 dict 或 None)。快取 coc_cache/conc.json，缺的日子補到 last 為止"""
    rows = json.load(open(CONC))['rows'] if os.path.exists(CONC) else []
    d = dt.date.fromisoformat(rows[-1][0]) + dt.timedelta(days=1) if rows else dt.date.fromisoformat(last) - dt.timedelta(days=30)
    one, n = None, 0
    while d.isoformat() <= last and n < max_new:
        one = conc_one(d.isoformat()); rows.append([one['date'], one['close'], one['c5'], one['c10']]); d += dt.timedelta(days=1); n += 1; time.sleep(0.3)
    if n:
        with open(CONC, 'w') as f:
            f.write('{"fetched_utc": "%s", "source": "%s", "cols": ["close", "c5", "c10"], "rows": [\n' % (dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), PAGE))
            f.write(',\n'.join(json.dumps(r) for r in rows) + '\n]}\n')
    if one is None and rows and rows[-1][0] == last:   # 今天已經在快取裡（同一天重跑）：再取一次明細給讀值用
        one = conc_one(last)
    return rows, one
