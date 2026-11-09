"""2026-11-09 使用者要求（「還能做什麼市場情緒層面的圖表」→「按照你說的做」）：三張情緒圖，外加開始累積選擇權看跌／看漲比。
都是免費、不用金鑰的公開資料，不佔 bitcoin-data 額度；只作讀值、不是買賣訊號，回測一律附樣本數。

fng_viz   恐懼貪婪指數全部歷史（alternative.me，2018/02 起）：歷次極度恐懼（≤ 20）、極度貪婪（≥ 80）之後 30／90 天漲跌。
wiki_viz  散戶關注度：英文維基百科「Bitcoin」條目每日瀏覽量（Wikimedia 公開 API，2015/07 起，只算真人 user）。
          7 日平均 ÷ 自己過去一年的中位數；大量新手湧入時會暴增（2017/12、2021 年都是），只代表關注度，不分買賣。
cot_viz   CME 機構持倉：CFTC 每週「金融期貨交易者持倉」（Traders in Financial Futures）的 CME 比特幣期貨（代號 133741，每口 5 顆）。
          槓桿基金（避險基金、CTA）與資產管理機構的淨部位（多單 − 空單）。槓桿基金的空單很大一部分是基差交易
          （買現貨／ETF、放空期貨賺價差），不等於看空；週二持倉、週五公布。
pcr_update 選擇權看跌／看漲比（Deribit 全部到期的未平倉與 24 小時成交）與 25Δ 風險逆轉：每天存一筆到 coc_cache/opt_daily.json。
          Deribit 不提供歷史，從 2026-11-09 開始累積，之後再畫圖。
x 一律為 1970-01-01 起的天數；px＝統一收盤 {日期: 價}。"""
import datetime as dt, json, os, statistics as st, subprocess
from stage_viz import dn, thin
from oc_extra import _fwd, _base, _stat

UA = 'Daybreak/1.0 (https://north7.github.io/daybreak)'   # Wikimedia 要求說明用途的 User-Agent（不放個人資料）
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)))
OPT_DAILY = os.path.join(ROOT, 'coc_cache', 'opt_daily.json')


def _get(url, timeout=60):
    out = subprocess.run(['curl', '-sS', '--max-time', str(timeout), '-A', UA, url], capture_output=True, text=True).stdout
    if not out.strip().startswith(('{', '[')): raise RuntimeError(f'{url[:80]}：{out[:120]}')
    return json.loads(out)


def _prices(px, last):
    D = sorted(d for d in px if d <= last and px[d])
    return D, {d: i for i, d in enumerate(D)}, (lambda d: px.get(d))


def _near_price(px, D, d):
    """d 當天或之前最近一天的收盤（週資料、缺日用）"""
    import bisect
    i = bisect.bisect_right(D, d) - 1
    return (D[i], px[D[i]]) if i >= 0 else (None, None)


def _eps(D, ix, P, days, cond, gap=30):
    """條件成立的段落起點（隔 gap 天以上算新的一段），附 30／90 天後漲跌"""
    out, prev = [], None
    for d in days:
        if not cond(d): continue
        if prev is None or dn(d) - dn(prev) > gap:
            d0 = d if d in ix else None
            if d0: out.append(dict(date=d, price=round(P(d)), r30=_fwd(D, ix, P, d, 30), r90=_fwd(D, ix, P, d, 90)))
        prev = d
    return out


# ---------- 恐懼貪婪指數 ----------
FG_LO, FG_HI = 20, 80


def fng_viz(px, last, step=2):
    j = _get('https://api.alternative.me/fng/?limit=0&format=json')
    fg = sorted((dt.datetime.fromtimestamp(int(x['timestamp']), dt.timezone.utc).date().isoformat(), int(x['value']), x['value_classification']) for x in j['data'])
    fg = [x for x in fg if x[0] <= last]
    if len(fg) < 1000: raise RuntimeError(f'恐懼貪婪只有 {len(fg)} 天')
    D, ix, P = _prices(px, last); V = {d: v for d, v, _ in fg}; days = [d for d, _, _ in fg if d in ix]
    d1, v1, lab = fg[-1]
    zone = lambda v: 'xf' if v <= FG_LO else 'xg' if v >= FG_HI else 'mid'
    z1, since = zone(v1), d1
    for d, v, _ in reversed(fg):
        if zone(v) != z1: break
        since = d
    fear = _eps(D, ix, P, days, lambda d: V[d] <= FG_LO); greed = _eps(D, ix, P, days, lambda d: V[d] >= FG_HI)
    H = [v for _, v, _ in fg]; back = lambda n: V.get((dt.date.fromisoformat(d1) - dt.timedelta(days=n)).isoformat())
    rows = thin([[dn(d), round(P(d)), V[d]] for d in days], step)
    if rows[-1][0] != dn(d1) and d1 in ix: rows.append([dn(d1), round(P(d1)), v1])
    lo = min(fg, key=lambda x: x[1]); hi = max(fg, key=lambda x: x[1])
    return dict(date=d1, value=v1, label=lab, d7=back(7), d30=back(30), avg30=round(st.mean(H[-30:]), 1), pct=round(sum(h < v1 for h in H) / len(H) * 100, 1),
                zone=z1, since=since, lo=FG_LO, hi=FG_HI, low=dict(date=lo[0], value=lo[1]), high=dict(date=hi[0], value=hi[1]),
                share_xf=round(sum(h <= FG_LO for h in H) / len(H) * 100, 1), share_xg=round(sum(h >= FG_HI for h in H) / len(H) * 100, 1),
                fear=fear, greed=greed, f30=_stat([e['r30'] for e in fear]), f90=_stat([e['r90'] for e in fear]), g30=_stat([e['r30'] for e in greed]), g90=_stat([e['r90'] for e in greed]),
                base30=_base(D, ix, P, 30, fg[0][0]), base90=_base(D, ix, P, 90, fg[0][0]), since_first=fg[0][0], rows=rows, src='alternative.me',
                note='alternative.me 恐懼貪婪指數（0 極度恐懼、100 極度貪婪）；極度恐懼 ≤ 20、極度貪婪 ≥ 80（隔 30 天以上算新的一段）；情緒是反向參考，只作讀值')


# ---------- 散戶關注度（維基百科瀏覽量） ----------
WK_SPIKE = 2.5


def wiki_viz(px, last, step=2):
    end = last.replace('-', '')
    j = _get(f'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Bitcoin/daily/20150701/{end}')
    raw = sorted((f"{x['timestamp'][:4]}-{x['timestamp'][4:6]}-{x['timestamp'][6:8]}", int(x['views'])) for x in j['items'])
    if len(raw) < 2000: raise RuntimeError(f'維基百科瀏覽量只有 {len(raw)} 天')
    days = [d for d, _ in raw]; v = [x for _, x in raw]
    v7, med, ratio = {}, {}, {}
    import bisect
    win = []
    for i, d in enumerate(days):
        v7[d] = sum(v[max(0, i - 6):i + 1]) / len(v[max(0, i - 6):i + 1])
        bisect.insort(win, v7[d])
        if i >= 365: win.pop(bisect.bisect_left(win, v7[days[i - 365]]))
        if i >= 365: med[d] = win[len(win) // 2]; ratio[d] = v7[d] / med[d]
    D, ix, P = _prices(px, last); R_ = [d for d in days if d in ratio and d in ix]
    d1 = R_[-1]; H = [v7[d] for d in R_]
    spikes = _eps(D, ix, P, R_, lambda d: ratio[d] >= WK_SPIKE, gap=60)
    for e in spikes:   # 這一段的最高倍數
        w = [d for d in R_ if 0 <= dn(d) - dn(e['date']) <= 60]; m = max(w, key=lambda d: ratio[d]); e['peak'] = round(ratio[m], 1); e['peak_date'] = m
    rows = thin([[dn(d), round(P(d)), round(v7[d]), round(ratio[d], 2)] for d in R_], step)
    if rows[-1][0] != dn(d1): rows.append([dn(d1), round(P(d1)), round(v7[d1]), round(ratio[d1], 2)])
    top = max(R_, key=lambda d: v7[d]); back = max((d for d in R_ if dn(d) <= dn(d1) - 30), default=None)
    return dict(date=d1, v7=round(v7[d1]), med=round(med[d1]), ratio=round(ratio[d1], 2), r30=round(ratio[back], 2) if back else None, pct=round(sum(h < v7[d1] for h in H) / len(H) * 100, 1),
                peak=dict(date=top, v7=round(v7[top])), spike=WK_SPIKE, spikes=spikes, s30=_stat([e['r30'] for e in spikes]), s90=_stat([e['r90'] for e in spikes]),
                base30=_base(D, ix, P, 30, R_[0]), base90=_base(D, ix, P, 90, R_[0]), rows=rows, src='Wikimedia',
                note='英文維基百科「Bitcoin」條目每日瀏覽量（只算真人）；7 日平均 ÷ 過去一年中位數；倍數 ≥ 2.5 算暴增（隔 60 天以上算新的一段）；只代表關注度、不分買賣，只作讀值')


# ---------- CME 機構持倉（CFTC） ----------
COT_CODE, COT_BTC = '133741', 5


def cot_viz(px, last):
    q = ('https://publicreporting.cftc.gov/resource/gpe5-46if.json?$select=report_date_as_yyyy_mm_dd,open_interest_all,lev_money_positions_long,lev_money_positions_short,'
         'asset_mgr_positions_long,asset_mgr_positions_short&$where=cftc_contract_market_code=%27' + COT_CODE + '%27&$order=report_date_as_yyyy_mm_dd&$limit=5000')
    j = _get(q.replace(' ', '%20'))
    f = lambda r, k: int(float(r.get(k) or 0))
    W = [(r['report_date_as_yyyy_mm_dd'][:10], f(r, 'open_interest_all'), f(r, 'lev_money_positions_long') - f(r, 'lev_money_positions_short'),
          f(r, 'asset_mgr_positions_long') - f(r, 'asset_mgr_positions_short'), f(r, 'lev_money_positions_short')) for r in j]
    W = [w for w in W if w[0] <= last and w[1] > 0]
    if len(W) < 200: raise RuntimeError(f'CFTC 只有 {len(W)} 週')
    D = sorted(d for d in px if d <= last and px[d])
    rows = []
    for d, oi, lev, am, ls in W:
        _, p = _near_price(px, D, d)
        rows.append([dn(d), round(p) if p else None, lev * COT_BTC, am * COT_BTC, oi * COT_BTC])
    d1, oi1, lev1, am1, ls1 = W[-1]; w4 = W[-5] if len(W) > 4 else None; w52 = W[-53] if len(W) > 52 else None
    L = [w[2] for w in W]; A = [w[3] for w in W]
    pct = lambda H, v: round(sum(h < v for h in H) / len(H) * 100, 1)
    return dict(date=d1, lev=lev1 * COT_BTC, am=am1 * COT_BTC, oi=oi1 * COT_BTC, lev_short_share=round(ls1 / oi1 * 100, 1),
                lev4=(lev1 - w4[2]) * COT_BTC if w4 else None, am4=(am1 - w4[3]) * COT_BTC if w4 else None, oi52=round((oi1 / w52[1] - 1) * 100, 1) if w52 else None,
                lev_pct=pct(L, lev1), am_pct=pct(A, am1), lev_min=dict(date=W[L.index(min(L))][0], v=min(L) * COT_BTC), am_max=dict(date=W[A.index(max(A))][0], v=max(A) * COT_BTC),
                since=W[0][0], weeks=len(W), rows=rows, src='CFTC', code=COT_CODE,
                note='CFTC 金融期貨交易者持倉（Traders in Financial Futures，期貨部分），CME 比特幣期貨 133741，每口 5 顆；淨部位＝多單 − 空單；'
                     '槓桿基金的空單多半是基差交易（買現貨或 ETF、放空期貨），不等於看空；週二持倉、週五公布；只作讀值')


# ---------- 選擇權看跌／看漲比（開始累積） ----------
def pcr_update(opt_result, last, rr25=None):
    oi_p = sum(o.get('open_interest') or 0 for o in opt_result if o['instrument_name'].endswith('-P'))
    oi_c = sum(o.get('open_interest') or 0 for o in opt_result if o['instrument_name'].endswith('-C'))
    vo_p = sum(o.get('volume') or 0 for o in opt_result if o['instrument_name'].endswith('-P'))
    vo_c = sum(o.get('volume') or 0 for o in opt_result if o['instrument_name'].endswith('-C'))
    if not oi_c or not vo_c: raise RuntimeError('Deribit 選擇權未平倉或成交是 0')
    try: c = json.load(open(OPT_DAILY))
    except Exception: c = {'_about': 'Deribit BTC 選擇權每日快照（資料管線 00:06 UTC 左右取得，記在前一個收盤日）：看跌／看漲比（未平倉、24 小時成交，單位 BTC）與 30 天 25Δ 風險逆轉；2026-11-09 開始累積', 'days': {}}
    c['days'][last] = dict(oi_pcr=round(oi_p / oi_c, 3), vol_pcr=round(vo_p / vo_c, 3), oi_put=round(oi_p), oi_call=round(oi_c),
                           rr25=(rr25 or {}).get('rr'))
    os.makedirs(os.path.dirname(OPT_DAILY), exist_ok=True)
    json.dump(c, open(OPT_DAILY, 'w'), ensure_ascii=False, indent=0, sort_keys=True)
    days = sorted(c['days']); x = c['days'][last]
    return dict(date=last, oi_pcr=x['oi_pcr'], vol_pcr=x['vol_pcr'], oi_put=x['oi_put'], oi_call=x['oi_call'], rr25=x['rr25'], first=days[0], n=len(days),
                rows=[[dn(d), c['days'][d]['oi_pcr'], c['days'][d]['vol_pcr'], c['days'][d].get('rr25')] for d in days], src='Deribit',
                note='Deribit BTC 選擇權全部到期：看跌未平倉 ÷ 看漲未平倉、24 小時成交同理；> 1＝買看跌（避險或看空）的部位比看漲多；每天累積一筆，只作讀值')
