#!/usr/bin/env python3
"""長期／短期持有者籌碼分布（LTH-URPD／STH-URPD）推算。2026-10-27 原型，尚未接進每日管線（collect.py／build.py 不呼叫）。

bitcoin-data 的 URPD 只有全體籌碼（2,000 美元一格），沒有依持有時間拆開；Glassnode 的 LTH／STH URPD 要付費。
做法：把「每一天新產生、到今天還沒動的幣」放進當天價格區間所在的格子，再用兩組實際資料校正
  · 列（幣齡）：bitcoin-data hodl-waves-supply 的 13 個幣齡帶（0–1 天、1 天–1 週 … 10 年以上）
  · 欄（成本）：bitcoin-data urpd 每一格的 BTC
  J[t, b] = 第 t 天產生、還沒動、落在第 b 格的 BTC。第一個快照用每日均勻的先驗做 IPF（交替縮放列與欄直到兩邊都吻合）；
  之後每個快照以前一個快照的 J 當舊幣的先驗、新的日子用均勻先驗，再做一次 IPF。這樣舊的籌碼堆（例如 84–86K）會被帶著走，
  不會被當天新買的幣稀釋。STH＝155 天內產生的幣，其餘為 LTH（Glassnode 與 bitcoin-data 的門檻）。
已知限制：
  · 不是實體調整（Glassnode 的 entity-adjusted 會把同一實體內部轉帳剔除，交易所整理錢包在這裡會讓幣「變年輕」）
  · bitcoin-data URPD 合計約 1,810 萬顆，比流通量少約 200 萬顆（應是中本聰時期的 P2PK 等），差額從「10 年以上」扣掉
  · 價格正在交易的那幾格同時有舊幣與新幣，拆分靠模型；完全沒交易到的格子，LTH／STH 不靠模型（只有一種）
  · bitcoin-data 免費層只有約 2026-08-10 起的 URPD 歷史；之後要靠每日存檔
驗證（2026-10-27 原型）：推算的 STH 成本與 bitcoin-data sth-realized-price 差 0.1–0.5%（08-12、10-01、10-07、10-15、10-20）
用法：python3 pipeline/cohort_urpd.py [--fetch] [--out 檔案]
  --fetch 會向 bitcoin-data 要 2 次（最新 urpd、近 500 天 hodl-waves-supply），注意免費層每個 IP 每日 15 次；價格讀 CoinMetrics 與 Kraken"""
import argparse, json, os, subprocess, datetime as dt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cohort_cache')
W, NB, LTH_DAYS = 2000, 63, 155                      # 2,000 美元一格，0–126K；155 天
D0 = dt.date(2009, 1, 3)
BANDS = [('age_0d_1d', 0, 1), ('age_1d_1w', 1, 7), ('age_1w_1m', 7, 30), ('age_1m_3m', 30, 90), ('age_3m_6m', 90, 180),
         ('age_6m_1y', 180, 365), ('age_1y_2y', 365, 730), ('age_2y_3y', 730, 1095), ('age_3y_4y', 1095, 1460),
         ('age_4y_5y', 1460, 1825), ('age_5y_7y', 1825, 2555), ('age_7y_10y', 2555, 3650), ('age_10y', 3650, 10 ** 6)]
MID = (np.arange(NB) + 0.5) * W
_i = lambda d: (dt.date.fromisoformat(d) - D0).days


def _get(url):
    out = subprocess.run(['curl', '-sS', '--max-time', '90', url], capture_output=True, text=True).stdout
    return json.loads(out)


def fetch():
    """更新 cohort_cache/：urpd.json 加入最新一天（全部 63 格）、hodl_waves.json 換成近 500 天"""
    os.makedirs(CACHE, exist_ok=True)
    up = os.path.join(CACHE, 'urpd.json'); U = json.load(open(up)) if os.path.exists(up) else {}
    js = _get('https://bitcoin-data.com/v1/urpd')
    if not isinstance(js, list) or not js: raise RuntimeError(f'bitcoin-data urpd 回應不是序列：{str(js)[:80]}')
    U[js[0]['theDate']] = [[r['priceLower'], round(r['btcSupply'], 1)] for r in js]
    s0 = (dt.date.today() - dt.timedelta(days=500)).isoformat()
    hw = _get(f'https://bitcoin-data.com/v1/hodl-waves-supply?startday={s0}&size=1000')
    if not isinstance(hw, list) or not hw: raise RuntimeError(f'bitcoin-data hodl-waves-supply 回應不是序列：{str(hw)[:80]}')
    _save(up, U); _save(os.path.join(CACHE, 'hodl_waves.json'), {r['d']: [round(float(r[k]), 1) for k, _, _ in BANDS] for r in hw})


def _save(path, obj):
    with open(path, 'w') as f:   # 一天一列，每日提交的 diff 只有新增的那幾行
        f.write('{\n' + ',\n'.join(f'{json.dumps(k)}: {json.dumps(v, separators=(",", ":"))}' for k, v in sorted(obj.items())) + '\n}\n')


def prices():
    """每日 [低, 高]：Kraken 日線（近 720 天）；更早用 CoinMetrics 收盤（低＝高）"""
    px = {r['time'][:10]: (float(r['PriceUSD']),) * 2 for r in _get(
        'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=PriceUSD&frequency=1d&start_time=2010-07-18&page_size=10000')['data']}
    k = _get('https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440')['result']
    for r in next(v for kk, v in k.items() if kk != 'last'):
        px[dt.datetime.fromtimestamp(r[0], dt.timezone.utc).date().isoformat()] = (float(r[3]), float(r[2]))
    return px


def day_matrix(px, last):
    """F[t] ＝ 第 t 天產生的幣在各格的比例（當天價格區間平均攤進各格）"""
    F = np.zeros((_i(last) + 1, NB)); top = NB * W - 1
    for t in range(len(F)):
        lo, hi = px.get((D0 + dt.timedelta(days=t)).isoformat(), (0.0, 0.0)); lo, hi = min(lo, top), min(hi, top)
        if hi - lo < 1: F[t, int(lo // W)] = 1; continue
        for b in range(int(lo // W), int(hi // W) + 1): F[t, b] = (min(hi, (b + 1) * W) - max(lo, b * W)) / (hi - lo)
    return F


def snapshots(U):
    """URPD 快照 → 63 格向量。只有 40K 以上的快照（從 state_min.json 歷史補來的）低於 40K 的格子用前後兩個完整快照線性內插（那裡只有 LTH，變化很小）"""
    full = {d: v for d, v in U.items() if min(p for p, _ in v) == 0}; fd = sorted(full); out = {}
    vec = lambda rows: np.bincount([int(p) // W for p, _ in rows], [x for _, x in rows], NB)
    for d, rows in sorted(U.items()):
        if d in full: out[d] = vec(rows); continue
        lo = max([x for x in fd if x <= d], default=fd[0]); hi = min([x for x in fd if x >= d], default=fd[-1])
        w = 0 if lo == hi else (_i(d) - _i(lo)) / (_i(hi) - _i(lo))
        u = (1 - w) * vec(full[lo]) + w * vec(full[hi])
        for p, x in rows: u[int(p) // W] = x
        out[d] = u
    return out


def ipf(P, R, band, U, iters=1500):
    R = R.copy(); R[-1] -= R.sum() - U.sum()        # URPD 少的約 200 萬顆視為最古老的幣
    X = P.copy()
    for _ in range(iters):
        X *= (R / np.maximum(np.bincount(band, X.sum(1), len(R)), 1e-12))[band][:, None]
        cs = X.sum(0); X *= np.where(cs > 0, U / np.maximum(cs, 1e-12), 0)[None, :]
    res = (np.abs(X.sum(0) - U).sum() + np.abs(np.bincount(band, X.sum(1), len(R)) - R).sum()) / U.sum() / 2
    return X, res


def run(U, HW, px):
    snaps = {d: u for d, u in snapshots(U).items() if d in HW}
    F = day_matrix(px, max(snaps)); J = None; prev = None; out = {}
    for d, u in snaps.items():
        T = _i(d); R = np.array(HW[d], float); band = np.zeros(T + 1, int)
        for a in range(T + 1): band[T - a] = next(j for j, (_, x, y) in enumerate(BANDS) if x <= a < y)
        if J is None: J, res = ipf(F[:T + 1], R, band, u)
        else:
            g = T - _i(prev)
            young = sum(R[j] * max(0, min(y, g) - x) / (min(y, T + 1) - x) for j, (_, x, y) in enumerate(BANDS) if x < g)
            J, res = ipf(np.vstack([J, F[_i(prev) + 1:T + 1] * young / g]), R, band, u)
        sth, lth = J[T - LTH_DAYS + 1:].sum(0), J[:T - LTH_DAYS + 1].sum(0)
        out[d] = dict(J=J, urpd=u, sth=sth, lth=lth, resid=res, sth_cost=(sth * MID).sum() / sth.sum(), lth_cost=(lth * MID).sum() / lth.sum())
        prev = d
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--fetch', action='store_true'); ap.add_argument('--out')
    a = ap.parse_args()
    if a.fetch: fetch()
    U = json.load(open(os.path.join(CACHE, 'urpd.json'))); HW = json.load(open(os.path.join(CACHE, 'hodl_waves.json')))
    res = run(U, HW, prices())
    for d, r in res.items():
        print(f"{d} 殘差 {r['resid']:.4f}  STH {r['sth'].sum()/1e4:,.0f} 萬顆 成本 {r['sth_cost']:,.0f}  LTH {r['lth'].sum()/1e4:,.0f} 萬顆 成本 {r['lth_cost']:,.0f}")
    if a.out:
        json.dump({d: dict(urpd=r['urpd'].round().tolist(), sth=r['sth'].round().tolist(), lth=r['lth'].round().tolist(),
                           sth_cost=round(r['sth_cost']), lth_cost=round(r['lth_cost']), resid=round(r['resid'], 5)) for d, r in res.items()},
                  open(a.out, 'w'))
