#!/usr/bin/env python3
"""長期／短期持有者籌碼分布（LTH-URPD／STH-URPD）推算。2026-10-27 使用者要求（Murphy〈跌破 $80K 的 BTC，潛在拋壓有多大？〉上下篇的做法）。

bitcoin-data 的 URPD 只有全體籌碼（2,000 美元一格），沒有依持有時間拆開；Glassnode 的 LTH／STH URPD 要付費。
做法：把「每一天新產生、到今天還沒動的幣」放進當天價格區間（Kraken 日線高低點；更早用 CoinMetrics 收盤）所在的格子，再用兩組實際資料校正
  · 列（幣齡）：bitcoin-data hodl-waves-supply 的 13 個幣齡帶（0–1 天、1 天–1 週 … 10 年以上）
  · 欄（成本）：bitcoin-data urpd 每一格的 BTC
  J[t, b] ＝ 第 t 天產生、還沒動、落在第 b 格的 BTC。第一個快照用每日均勻的先驗做 IPF（交替縮放列與欄直到兩邊都吻合）；
  之後每個快照以前一個快照的 J 當舊幣的起點（舊幣只會被花掉、不會變多，所以設上限）、新的日子用均勻先驗，再做一次 IPF，
  這時只對齊 6 個月以內的幣齡帶。舊的籌碼堆（例如 84–86K）會被帶著走，不會被新買的幣稀釋。STH＝155 天內產生的幣，其餘為 LTH（Glassnode 與 bitcoin-data 的門檻）。J 很稀疏（每天只落在 1–3 格），以 (t, b, v) 三個陣列存。
已知限制（頁面與每日任務都要照寫）：
  · 不是實體調整：Glassnode 的 entity-adjusted 會剔除同一實體內部轉帳；交易所、託管整理錢包在這裡會被當成賣出再買進，換手量偏高
  · bitcoin-data URPD 合計約 1,810 萬顆，比流通量少約 200 萬顆（應是中本聰時期的 P2PK 等），差額從「10 年以上」扣掉
  · 價格正在交易的格子同時有舊幣與新幣，拆分靠模型；過去 155 天價格沒到過的格子只有 LTH，不靠模型
  · bitcoin-data 免費層的 URPD 歷史只到約 2026-08-10；之後靠 cohort_cache/urpd.json 每日存檔
驗證（2026-10-27）：STH 成本沒有拿去校正，推算值與 bitcoin-data sth-realized-price 在 2026-09-06～10-20 的 13 個日期差 −0.3%～+0.2%；
  STH 總量與 bitcoin-data sth-lth-ratio 換算值差 −5%～+3%；LTH 30 日變化比 bitcoin-data 的 lth-net-position-change-30d 多賣約 6–9 萬顆（方向一致）。
collect.py 每天呼叫 daily()；單獨執行：python3 pipeline/cohort_urpd.py（讀 cohort_cache/，價格向 CoinMetrics 與 Kraken 抓，不打 bitcoin-data）"""
import json, os, subprocess, datetime as dt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cohort_cache')
W, NB, LTH_DAYS = 2000, 63, 155                      # 2,000 美元一格，0–126K；155 天
D0 = dt.date(2009, 1, 3)
BANDS = [('age_0d_1d', 0, 1), ('age_1d_1w', 1, 7), ('age_1w_1m', 7, 30), ('age_1m_3m', 30, 90), ('age_3m_6m', 90, 180),
         ('age_6m_1y', 180, 365), ('age_1y_2y', 365, 730), ('age_2y_3y', 730, 1095), ('age_3y_4y', 1095, 1460),
         ('age_4y_5y', 1460, 1825), ('age_5y_7y', 1825, 2555), ('age_7y_10y', 2555, 3650), ('age_10y', 3650, 10 ** 6)]
EDGES = np.array([x for _, x, _ in BANDS[1:]])
MID = (np.arange(NB) + 0.5) * W
YOUNG = 5                                             # 之後的快照只強制對齊前 5 個幣齡帶（0 天–6 個月）
ROW0 = 40000 // W                                     # 頁面與摘要只輸出 40K 以上的格子（STH 不會出現在更低的價位）
_i = lambda d: (dt.date.fromisoformat(d) - D0).days
_d = lambda t: (D0 + dt.timedelta(days=int(t))).isoformat()


def _save(path, obj):
    with open(path, 'w') as f:   # 一天一列，每日提交的 diff 只有新增的那一行
        f.write('{\n' + ',\n'.join(f'{json.dumps(k)}: {json.dumps(v, separators=(",", ":"))}' for k, v in sorted(obj.items())) + '\n}\n')


def _load(name):
    p = os.path.join(CACHE, name)
    return json.load(open(p)) if os.path.exists(p) else {}


def archive(urpd_rows, hw_rows):
    """把當天的 URPD（63 格）與 hodl-waves-supply 併進 cohort_cache/；回傳 (U, HW)"""
    os.makedirs(CACHE, exist_ok=True)
    U, HW = _load('urpd.json'), _load('hodl_waves.json')
    if urpd_rows:
        U[urpd_rows[0]['theDate']] = [[int(r['priceLower']), round(float(r['btcSupply']), 1)] for r in urpd_rows]
    for r in hw_rows or []:
        try: HW[r['d']] = [round(float(r[k]), 1) for k, _, _ in BANDS]
        except (KeyError, TypeError, ValueError): pass
    _save(os.path.join(CACHE, 'urpd.json'), U); _save(os.path.join(CACHE, 'hodl_waves.json'), HW)
    return U, HW


def prior(px, last):
    """每日的先驗：第 t 天產生的幣平均攤進當天 [低, 高] 所在的格子 → 稀疏陣列 (t, b, w)"""
    T, B, V = [], [], []; top = NB * W - 1
    for t in range(_i(last) + 1):
        lo, hi = px.get(_d(t), (0.0, 0.0)); lo, hi = min(lo, top), min(hi, top)
        if hi - lo < 1: T.append(t); B.append(int(lo // W)); V.append(1.0); continue
        for b in range(int(lo // W), int(hi // W) + 1):
            T.append(t); B.append(b); V.append((min(hi, (b + 1) * W) - max(lo, b * W)) / (hi - lo))
    return np.array(T), np.array(B), np.array(V)


def snapshots(U, HW):
    """可用的快照（有 URPD 也有前 2 天內的幣齡分布）→ {日期: (URPD 63 格, 幣齡 13 帶)}。
    只有 40K 以上的快照（2026-10-27 從 state_min.json 歷史補的種子）低於 40K 的格子用前後兩個完整快照內插（那裡只有 LTH，變化很小）"""
    vec = lambda rows: np.bincount([int(p) // W for p, _ in rows], [x for _, x in rows], NB)
    full = sorted(d for d, v in U.items() if min(p for p, _ in v) == 0); hwd = sorted(HW); out = {}
    for d in sorted(U):
        h = [x for x in hwd if x <= d and _i(d) - _i(x) <= 2]
        if not h or not full: continue
        if d in full: u = vec(U[d])
        else:
            lo = max([x for x in full if x <= d], default=full[0]); hi = min([x for x in full if x >= d], default=full[-1])
            w = 0 if lo == hi else (_i(d) - _i(lo)) / (_i(hi) - _i(lo))
            u = (1 - w) * vec(U[lo]) + w * vec(U[hi])
            for p, x in U[d]: u[int(p) // W] = x
        out[d] = (u, np.array(HW[h[-1]], float))
    return out


def thin(dates, keep_days=400, every=7):
    """跑鏈的快照：近 400 天全部用（每個快照約 0.02 秒），更早的每 7 天取一個，讓計算量不會無限增加"""
    if not dates: return []
    last = _i(dates[-1]); out = [dates[0]]
    for d in dates[1:]:
        if last - _i(d) <= keep_days or _i(d) - _i(out[-1]) >= every: out.append(d)
    return out


def ipf(t, b, v, T, U, R, cap=None, tol=1e-7, iters=3000):
    """交替縮放 v，讓各幣齡帶合計＝R、各格合計＝U。
    cap＝前一個快照的值：舊幣只會被花掉、不會變多，所以前 len(cap) 項不得超過 cap；這時只對齊 6 個月以內的幣齡帶（STH 所在），
    更老的帶不強制（帶內每天的分配是近似的，強制對齊會逼模型把老幣在日子之間搬來搬去）。2026-10-27 對照：不設上限時 LTH 30 日變化（9/20→10/20）
    算成 −24.5 萬顆，設上限後 −17.4 萬顆，bitcoin-data lth-net-position-change-30d 是 −11.4 萬顆"""
    band = np.searchsorted(EDGES, T - t, side='right')
    R = R.copy(); R[-1] -= R.sum() - U.sum()              # URPD 少的約 200 萬顆視為最古老的幣
    v = v.copy(); n = 0 if cap is None else len(cap); on = np.arange(len(R)) < (len(R) if cap is None else YOUNG)
    for k in range(iters):
        v *= np.where(on, R / np.maximum(np.bincount(band, v, len(R)), 1e-12), 1.0)[band]
        if n: v[:n] = np.minimum(v[:n], cap)
        cs = np.bincount(b, v, NB); v *= np.where(cs > 0, U / np.maximum(cs, 1e-12), 0)[b]
        if n: v[:n] = np.minimum(v[:n], cap)
        if k % 25 == 24 and np.abs(np.bincount(band, v, len(R)) - R)[on].sum() < tol * U.sum(): break
    res = (np.abs(np.bincount(band, v, len(R)) - R)[on].sum() / R[on].sum() + np.abs(np.bincount(b, v, NB) - U).sum() / U.sum()) / 2
    return v, res


def run(U, HW, px):
    """跑整條鏈；回傳 {日期: dict(t, b, v, T, urpd, sth, lth, resid, sth_cost, lth_cost)}（t/b/v 依附加順序，前一個快照的項目在前）"""
    S = snapshots(U, HW); ds = thin(sorted(S))
    if not ds: return {}
    FT, FB, FV = prior(px, ds[-1]); out = {}; t = b = v = None; prev = None
    for d in ds:
        u, R = S[d]; T = _i(d)
        if v is None:
            m = FT <= T; t, b, v = FT[m], FB[m], FV[m]
        else:
            g = T - _i(prev); m = (FT > _i(prev)) & (FT <= T)
            young = sum(R[j] * max(0, min(y, g) - x) / (min(y, T + 1) - x) for j, (_, x, y) in enumerate(BANDS) if x < g)
            cap = v; t, b, v = np.concatenate([t, FT[m]]), np.concatenate([b, FB[m]]), np.concatenate([v, FV[m] * young / g])
        v, res = ipf(t, b, v, T, u, R, None if prev is None else cap)
        s_ = t > T - LTH_DAYS
        sth, lth = np.bincount(b[s_], v[s_], NB), np.bincount(b[~s_], v[~s_], NB)
        out[d] = dict(t=t, b=b, v=v, T=T, urpd=u, sth=sth, lth=lth, resid=res,
                      sth_cost=float((sth * MID).sum() / sth.sum()), lth_cost=float((lth * MID).sum() / lth.sum()))
        prev = d
    return out


def summarize(res, px, close, bd_sth_cost=None):
    """頁面與每日摘要要的讀值（只作讀值；推算，附驗證）"""
    ds = sorted(res); d = ds[-1]; r = res[d]; T = r['T']
    rows = lambda x: [[k * W, round(float(x['sth'][k])), round(float(x['lth'][k]))] for k in range(ROW0, NB)]
    # 過去 155 天價格走過的區間：區間外只有 LTH，不靠模型
    win = [px[_d(x)] for x in range(T - LTH_DAYS + 1, T + 1) if _d(x) in px]
    lo155, hi155 = min(a for a, _ in win), max(h for _, h in win)
    out = dict(date=d, price=round(close), width=W, rows=rows(r), below_lth=round(float(r['lth'][:ROW0].sum())),
               tot=dict(sth=round(float(r['sth'].sum())), lth=round(float(r['lth'].sum())), sth_cost=round(r['sth_cost']), lth_cost=round(r['lth_cost'])),
               window=dict(lo=round(lo155), hi=round(hi155)), resid=round(r['resid'], 5), snapshots=len(ds))
    # 和約 30 天前的快照比：誰賣了、誰買了
    c0 = [x for x in ds if T - res[x]["T"] >= 30]
    if c0:
        a = res[c0[-1]]; Ta = a['T']; n = len(a['v']); va, vb, tb, bb = a['v'], r['v'][:n], r['t'][:n], r['b'][:n]
        old_sth = tb > Ta - LTH_DAYS                                   # 那時是 STH 的幣
        sp = va - vb                                                   # 已經動了的部分
        newm = np.arange(len(r['v'])) >= n
        sp_sth, sp_lth = np.bincount(bb[old_sth], sp[old_sth], NB), np.bincount(bb[~old_sth], sp[~old_sth], NB)
        new_b = np.bincount(r['b'][newm], r['v'][newm], NB)
        aged = vb[old_sth & (tb <= T - LTH_DAYS)].sum()
        hi_since = max(h for x, (_, h) in px.items() if a['T'] < _i(x) <= T); lo_since = min(l_ for x, (l_, _) in px.items() if a['T'] < _i(x) <= T)
        out['cmp'] = dict(date=c0[-1], rows=rows(a), tot=dict(sth=round(float(a['sth'].sum())), lth=round(float(a['lth'].sum())), sth_cost=round(a['sth_cost'])))
        out['flow'] = dict(start=c0[-1], end=d, days=T - Ta, sth0=round(float(va[old_sth].sum())), sth_spent=round(float(sp_sth.sum())),
                           sth_aged=round(float(aged)), sth_still=round(float(vb[old_sth & (tb > T - LTH_DAYS)].sum())),
                           lth0=round(float(va[~old_sth].sum())), lth_spent=round(float(sp_lth.sum())), new=round(float(new_b.sum())),
                           rows=[[k * W, round(float(sp_sth[k])), round(float(sp_lth[k])), round(float(new_b[k]))] for k in range(ROW0, NB)],
                           untouched=dict(above=round(hi_since), below=round(lo_since)))
        # 價格這段期間沒碰過、而且 155 天內也沒碰過的格子：只有 LTH、也沒有新幣進來，變化就是賣出（不靠模型）
        top = int(max(hi_since, hi155) // W) + 1
        out['flow']['model_free_above'] = dict(lo=top * W, before=round(float(a['urpd'][top:].sum())), after=round(float(r['urpd'][top:].sum())))
    # 跌到哪裡誰套牢：成本在該價位之上的幣
    p0 = int(close // W) * W
    out['loss'] = [[p, round(float(r['sth'][p // W:].sum())), round(float(r['lth'][p // W:].sum()))] for p in range(p0, max(int(close * 0.75), 0), -W)]
    if bd_sth_cost:   # 驗證：bitcoin-data 晚約 7 天，取鏈上最晚一個兩邊都有的日期
        v_ = [x for x in ds if x in bd_sth_cost]
        if v_: x = v_[-1]; out['val'] = dict(date=x, ours=round(res[x]['sth_cost']), bd=round(bd_sth_cost[x]), diff_pct=round((res[x]['sth_cost'] / bd_sth_cost[x] - 1) * 100, 2))
    out['note'] = '推算（IPF：bitcoin-data URPD × 幣齡分布 × 每日價格區間）；逐筆 UTXO、不是實體調整；只作讀值'
    return out


def daily(urpd_rows, hw_rows, px, close, bd_sth_cost=None):
    """collect.py 每天呼叫：存檔 → 跑鏈 → 讀值"""
    U, HW = archive(urpd_rows, hw_rows)
    res = run(U, HW, px)
    return summarize(res, px, close, bd_sth_cost) if res else None


def _get(url):
    return json.loads(subprocess.run(['curl', '-sS', '--max-time', '90', url], capture_output=True, text=True).stdout)


def prices():
    px = {r['time'][:10]: (float(r['PriceUSD']),) * 2 for r in _get(
        'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=PriceUSD&frequency=1d&start_time=2010-07-18&page_size=10000')['data']}
    k = _get('https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440')['result']
    for r in next(v for kk, v in k.items() if kk != 'last'):
        px[dt.datetime.fromtimestamp(r[0], dt.timezone.utc).date().isoformat()] = (float(r[3]), float(r[2]))
    return px


if __name__ == '__main__':
    U, HW = _load('urpd.json'), _load('hodl_waves.json'); px = prices()
    res = run(U, HW, px)
    for d, r in res.items():
        print(f"{d} 殘差 {r['resid']:.5f}  STH {r['sth'].sum()/1e4:,.0f} 萬顆 成本 {r['sth_cost']:,.0f}  LTH {r['lth'].sum()/1e4:,.0f} 萬顆 成本 {r['lth_cost']:,.0f}")
    s = summarize(res, px, px[max(px)][1])
    print(json.dumps({k: v for k, v in s.items() if k not in ('rows', 'cmp', 'loss')} | {'flow': {k: v for k, v in (s.get('flow') or {}).items() if k != 'rows'}}, ensure_ascii=False))
