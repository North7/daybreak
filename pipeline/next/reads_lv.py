# -*- coding: utf-8 -*-
"""價位頁的讀數（2026-11-17，取代舊版抽來的讀數；規則見 reads.py）。每個函式回傳 (一句結論中, 英, [最多三條事實])"""
from reads import sg, pc, pu, n0, sn0, wan, kb, yi, bn, md, ymd, ym, ord_en, it, M, mde, ymde, yme

LVN = dict(act=('活躍投資人成本', 'active investor cost'), tmm=('真實市場均價', 'true market mean'), sma365=('365 日均線', '365-day MA'), w50=('50 週均線', '50-week MA'),
           sth=('短期持有者成本', 'short-term holder cost'), sma200=('200 日均線', '200-day MA'), rp=('實現價', 'realized price'), lth=('長期持有者成本', 'long-term holder cost'))
def usd(v): return '$' + n0(v)
def kusd(v): return '$%.1fK' % (v / 1000.0)
def kk(v): return '%dK' % round(v / 1000.0)
def rng(a, b): return '%s–%s' % (kk(a), kk(b))
def cap(t): return t[:1].upper() + t[1:]
def close(L): return L['price']['bar']['c']

def levels(L):
    lv = L['cycle']['levels']; px = lv['price']; ab = [x for x in lv['levels'] if x['dist_pct'] > 0]; be = [x for x in lv['levels'] if x['dist_pct'] <= 0]
    tm = next(x for x in lv['levels'] if x['key'] == 'tmm'); nr = min(ab, key=lambda x: x['dist_pct']) if ab else None
    sz = '收盤在 %d 條線裡 %d 條的下方%s。' % (len(lv['levels']), len(ab), '，最近的是 %s（高 %.1f%%）' % (LVN[nr['key']][0], nr['dist_pct']) if nr else '')
    se = 'The close is below %d of %d lines%s.' % (len(ab), len(lv['levels']), '; the nearest is the %s (%.1f%% higher)' % (LVN[nr['key']][1], nr['dist_pct']) if nr else '')
    under = tm['dist_pct'] > 0
    return sz, se, [
        it('真實市場均價', 'True market mean', usd(tm['value']), usd(tm['value']), 'down' if under else 'up', '收盤在它%s %.1f%%：活躍投資人整體%s；這條線歷來是多空分界。' % ('下方' if under else '上方', abs(px / tm['value'] - 1) * 100, '虧損' if under else '獲利'),
           'The close is %.1f%% %s it: active investors are %s as a group. It has long been the line between bull and bear.' % (abs(px / tm['value'] - 1) * 100, 'below' if under else 'above', 'underwater' if under else 'in profit')),
        it('上方', 'Above', '%d 條' % len(ab), '%d lines' % len(ab), 'neu', '、'.join('%s %s' % (LVN[x['key']][0], kusd(x['value'])) for x in sorted(ab, key=lambda x: x['dist_pct'])[:3]) + ('…' if len(ab) > 3 else '') + '。',
           cap(', '.join('%s %s' % (LVN[x['key']][1], kusd(x['value'])) for x in sorted(ab, key=lambda x: x['dist_pct'])[:3])) + (' …' if len(ab) > 3 else '.')),
        it('下方', 'Below', '%d 條' % len(be), '%d lines' % len(be), 'neu', '、'.join('%s %s（%s）' % (LVN[x['key']][0], kusd(x['value']), pc(x['dist_pct'])) for x in sorted(be, key=lambda x: -x['dist_pct'])[:2]) + '。' if be else '沒有。',
           (cap(', '.join('%s %s (%s)' % (LVN[x['key']][1], kusd(x['value']), pc(x['dist_pct'])) for x in sorted(be, key=lambda x: -x['dist_pct'])[:2])) + '.') if be else 'None.')]

def sthgap(L):
    b = L['onchain']['sth_bands']; n = b['now']; s = b['stats']; z = n['z']; B = n['bands']; px = close(L)
    rare = s['below1_pct'] if z <= -1 else s['above1_pct'] if z >= 1 else None
    sz = '收盤在短期持有者成本帶 %s 標準差%s。' % (sg(z, 1), '，近 4 年只有 %.0f%% 的日子這麼%s' % (rare, '低' if z < 0 else '高') if rare is not None else '')
    se = 'The close sits at %s standard deviations on the short-term holder cost band%s.' % (sg(z, 1), '; only %.0f%% of days in four years were this %s' % (rare, 'low' if z < 0 else 'high') if rare is not None else '')
    return sz, se, [
        it('現在位置', 'Position', '%s σ' % sg(z, 1), '%s σ' % sg(z, 1), 'down' if z <= -1 else 'up' if z >= 1 else 'neu', '收盤 %s，在短期持有者成本 %s %s %.1f%%。' % (usd(px), usd(n['sth']), '下方' if px < n['sth'] else '上方', abs(px / n['sth'] - 1) * 100),
           'The close of %s is %.1f%% %s the short-term holder cost of %s.' % (usd(px), abs(px / n['sth'] - 1) * 100, 'below' if px < n['sth'] else 'above', usd(n['sth']))),
        it('下緣', 'Lower bands', '%s / %s' % (kusd(B['-1']), kusd(B['-2'])), '%s / %s' % (kusd(B['-1']), kusd(B['-2'])), 'neu', '−1、−2 標準差；近 4 年 %.0f%% 的日子收在 −1 以下。' % s['below1_pct'], '−1 and −2 standard deviations; %.0f%% of days in four years closed below −1.' % s['below1_pct']),
        it('上緣', 'Upper bands', '%s / %s' % (kusd(B['1']), kusd(B['2'])), '%s / %s' % (kusd(B['1']), kusd(B['2'])), 'neu', '+1、+2 標準差；近 120 天最高到 %s（%s）。' % (sg(s['max120']['z'], 1), md(s['max120']['date'])),
           '+1 and +2 standard deviations; the 120-day high was %s (%s).' % (sg(s['max120']['z'], 1), mde(s['max120']['date'])))]

def quant(L):
    q = L['onchain']['quant']; c = q['cur']; px = q['price']; ks = sorted(int(k) for k in c)
    lo = max((k for k in ks if c[str(k)] <= px), default=None); hi = min((k for k in ks if c[str(k)] > px), default=None)
    pos = ('%.2f–%.2f' % (lo / 100, hi / 100)) if lo and hi else ('%.2f 以下' % (hi / 100)) if hi else '%.2f 以上' % (lo / 100)
    sz = '收盤在 %s 分位線之間；獲利供給 %.1f%%。' % (pos, q['psip']) if lo and hi else '收盤在 %s 分位；獲利供給 %.1f%%。' % (pos, q['psip'])
    se = 'The close sits between the %s quantile lines; %.1f%% of supply is in profit (%.1f%% 30 days ago).' % (pos, q['psip'], q['psip30']) if lo and hi else 'The close is at the %s quantile; %.1f%% of supply is in profit.' % (pos, q['psip'])
    up = [u for u in q['ups75'] if u['below_days'] >= 90][-1]
    return sz, se, [
        it('位置', 'Position', pos, pos, 'neu', '%s%s；分位線會隨換手往現價靠。' % ('%.2f 分位 %s、' % (lo / 100, usd(c[str(lo)])) if lo else '', '%.2f 分位 %s' % (hi / 100, usd(c[str(hi)])) if hi else ''),
           '%s%s; the lines drift toward price as coins change hands.' % ('the %.2f quantile at %s, ' % (lo / 100, usd(c[str(lo)])) if lo else '', 'the %.2f at %s' % (hi / 100, usd(c[str(hi)])) if hi else '')),
        it('回到 65% 獲利', 'Back to 65% in profit', usd(c['65']), usd(c['65']), 'neu', '60%% 約 %s；65%% 這條 30 天 %s。' % (usd(c['60']), pc(q['chg30']['65'])), '60%% at about %s; the 65%% line moved %s in 30 days.' % (usd(c['60']), pc(q['chg30']['65']))),
        it('0.75 分位（上方賣壓）', '0.75 quantile (overhead supply)', usd(c['75']), usd(c['75']), 'neu', '%s 之後連 %d 天在下方；上次壓了 90 天以上後站上是 %s。' % (md(q['last_above75']), q['below75_days'], ym(up['date'])),
           'Below it for %d days since %s; the last reclaim after 90+ days below was %s.' % (q['below75_days'], mde(q['last_above75']), yme(up['date'])))]

def urpd(L):
    u = L['chips']['urpd']; sup = L['chips']['flow']['conc5']['supply']; a, b = u['above_cluster'], u['below_cluster']; cb = u['cur_bucket']
    sz = '現價這一格（%s）有 %s，佔供給 %.1f%%。' % (rng(*cb), wan(u['cur_btc'], False), u['cur_pct'])
    se = 'The bucket at price (%s) holds %s (%.1f%%).' % (rng(*cb), kb(u['cur_btc'], False), u['cur_pct'])
    m = u.get('below_max')   # 2026-11-27 下方 50% 內沒有 50 萬顆以上的格子時，照實寫籌碼薄，並列出最厚的一格
    ib = it('下方最近的大堆', 'Nearest pile below', rng(*b['range']), rng(*b['range']), 'neu', '%s，是第一道籌碼支撐。' % wan(b['btc'], False), '%s, the first layer of support.' % kb(b['btc'], False)) if b else \
         it('下方最近的大堆', 'Nearest pile below', '50% 內沒有', 'None within 50%', 'neu', '現價以下 50%% 內沒有 50 萬顆以上的一格，籌碼支撐薄%s。' % ('；最厚的是 %s，%s' % (rng(*m['range']), wan(m['btc'], False)) if m else ''),
            'No bucket within 50%% below price holds 500K BTC or more, so supply support is thin%s.' % ('; the thickest is %s with %s' % (rng(*m['range']), kb(m['btc'], False)) if m else ''))
    ia = it('上方最近的大堆', 'Nearest pile above', rng(*a['range']), rng(*a['range']), 'neu', '%s：價格回到那裡時，那裡買的人剛好回本，常有解套賣壓。' % wan(a['btc'], False), '%s: buyers there break even if price returns, which often brings selling.' % kb(a['btc'], False)) if a else \
         it('上方最近的大堆', 'Nearest pile above', '沒有', 'None', 'neu', '現價以上沒有 50 萬顆以上的一格。', 'No bucket above price holds 500K BTC or more.')
    return sz, se, [ia, ib,
        it('現價到 $120K', 'Price to $120K', wan(u['btc_price_to_120k'], False), kb(u['btc_price_to_120k'], False), 'neu', '這一段價位的籌碼合計，佔供給約 %.0f%%。' % (u['btc_price_to_120k'] / sup * 100), 'All coins last moved between here and $120K, about %.0f%% of supply.' % (u['btc_price_to_120k'] / sup * 100))]

def cohort(L):
    c = L['chips']['cohort']; t = c['tot']; px = c['price']; f = c['flow']; ls = c['loss']; r0 = ls[0]; r60 = next((r for r in ls if r[0] == 60000), ls[-1]); v = c.get('val') or {}
    gap = (px / t['sth_cost'] - 1) * 100
    sz = '短期持有者 %s、平均成本 %s，收盤%s %.1f%%。' % (wan(t['sth'], False), usd(t['sth_cost']), '低' if gap < 0 else '高', abs(gap)); se = 'Short-term holders hold %s at an average cost of %s; the close is %.1f%% %s.' % (kb(t['sth'], False), usd(t['sth_cost']), abs(gap), 'below' if gap < 0 else 'above')
    out = [it('跌到哪裡誰套牢', 'Who is underwater where', '%d%%' % round(r0[1] / t['sth'] * 100), '%d%%' % round(r0[1] / t['sth'] * 100), 'neu',
              '成本在 %s 以上的短期持有者 %s；跌到 %s 增加到 %d%%。' % (kk(r0[0]), wan(r0[1], False), kk(r60[0]), round(r60[1] / t['sth'] * 100)),
              'Short-term holders with cost above %s: %s; at %s it rises to %d%%.' % (kk(r0[0]), kb(r0[1], False), kk(r60[0]), round(r60[1] / t['sth'] * 100))),
           it('近 %d 天' % f['days'], 'Last %d days' % f['days'], wan(f['sth_spent'] + f['lth_spent'], False), kb(f['sth_spent'] + f['lth_spent'], False), 'neu',
              '推算：短期持有者動了 %s、長期 %s；新買進還沒動的 %s。' % (wan(f['sth_spent'], False), wan(f['lth_spent'], False), wan(f['new'], False)),
              'Estimated: short-term holders moved %s and long-term %s; %s bought since are still unmoved.' % (kb(f['sth_spent'], False), kb(f['lth_spent'], False), kb(f['new'], False)))]
    if v.get('ours'):
        out.append(it('驗證', 'Check', pc(v['diff_pct'], 2), pc(v['diff_pct'], 2), 'neu', '推算的短期持有者成本 %s，Bitview 公布 %s：拆分可信。' % (usd(v['ours']), usd(v['bd'])), 'Our estimated short-term cost is %s against Bitview\'s %s, so the split holds up.' % (usd(v['ours']), usd(v['bd']))))
    return sz, se, out

def conc(L):   # 2026-11-26 改寫（WRITING.md）：加 7 日平均、從高點回落到哪、6% 回測（conc_bt.py）
    from conc_bt import bt
    c5 = L['chips']['flow']['conc5']; s = L['chips']['conc_stats']; h = L['chips']['conc_hist']; w = h[-8][2] if len(h) >= 8 else None; cb = bt(h); cu = cb['cur']; b, a = cb['bt'], cb['base']
    import datetime as _dt
    dd_ = lambda n: _dt.date(1970, 1, 1) + _dt.timedelta(int(n)); mz = lambda n: '%d/%d' % (dd_(n).month, dd_(n).day); me = lambda n: '%s %d' % (['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][dd_(n).month - 1], dd_(n).day)
    if cu and not cu['below_dn']:
        sz = '現價附近的籌碼從 %s 的高點散開，集中度（7 日平均）降到 %.1f%%，還沒到 6%%。' % (mz(cu['pk_dn']), cb['now'])
        se = 'Supply near the price has spread out since the %s high: concentration (7-day average) is down to %.1f%%, not yet 6%%.' % (me(cu['pk_dn']), cb['now'])
    elif cu:
        sz = '現價附近的籌碼從 %s 的高點散開，集中度（7 日平均）%s 已經降到 6%% 以下，現在 %.1f%%。' % (mz(cu['pk_dn']), mz(cu['below_dn']), cb['now'])
        se = 'Supply near the price has spread out since the %s high: concentration (7-day average) fell below 6%% on %s and is %.1f%% now.' % (me(cu['pk_dn']), me(cu['below_dn']), cb['now'])
    elif cb['now'] >= cb['p90']:
        sz = '現價附近的籌碼很集中：7 日平均 %.1f%%，在 2018 年以來的前 10%%，價格一離開這一帶波動容易放大。' % cb['now']; se = 'Supply is packed around the price: the 7-day average is %.1f%%, in the top 10%% since 2018, so a move out of this band tends to be large.' % cb['now']
    else:
        sz = '現價附近的籌碼集中度（7 日平均）%.1f%%，不高也不低。' % cb['now']; se = 'Supply concentration near the price (7-day average) is %.1f%%, neither high nor low.' % cb['now']
    out = [it('今天', 'Today', pu(c5['pct']), pu(c5['pct']), 'warn' if c5['pct'] >= s['p90'] else 'neu', '每日值：現價 ±5%%（%s–%s）內 %s；在賺的佔供給 %.1f%%、在賠的 %.1f%%%s。' % (kusd(c5['lo']), kusd(c5['hi']), wan(c5['btc'], False), c5['in_profit'], c5['in_loss'], '；7 天前 %.1f%%' % w if w is not None else ''),
              'Daily value: %s within ±5%% (%s–%s); %.1f%% of supply in profit and %.1f%% at a loss%s.' % (kb(c5['btc'], False), kusd(c5['lo']), kusd(c5['hi']), c5['in_profit'], c5['in_loss'], '; %.1f%% a week ago' % w if w is not None else '')),
           it('很集中的時候', 'When it is high', '%.0f%% / %.0f%%' % (s['hi_med30'], s['lo_med30']), '%.0f%% / %.0f%%' % (s['hi_med30'], s['lo_med30']), 'neu', '在前 10%% 時，之後 30 天價格最多往一邊走 %.0f%%（中位數），其他日子 %.0f%%；只說波動會變大，不說往哪邊。' % (s['hi_med30'], s['lo_med30']),
              'In the top 10%%, price moved up to %.0f%% one way over the next 30 days (median), versus %.0f%% on other days; it says swings grow, not which way.' % (s['hi_med30'], s['lo_med30']))]
    if b:
        out.append(it('降到 6% 以下之後', 'After dropping below 6%', '%d/%d 次較高' % (b['up'], b['n']), '%d of %d higher' % (b['up'], b['n']), 'neu',
                      '2018 年以來，衝上高檔後第一次降到 6%% 以下有 %d 次：%d 天後 %d 次比當時高、中位數 %s，期間最深中位數 %s；隨便一天是 %d%% 較高、%s、%s。次數很少。' % (b['n'], cb['h'], b['up'], pc(b['med'], 0), pc(b['dd'], 0), round(a['up'] / a['n'] * 100), pc(a['med'], 0), pc(a['dd'], 0)),
                      'Since 2018, the first drop below 6%% after a high happened %d times: %d days later price was higher %d times, median %s, with a median worst dip of %s; any day: %d%% higher, %s, %s. Very few cases.' % (b['n'], cb['h'], b['up'], pc(b['med'], 0), pc(b['dd'], 0), round(a['up'] / a['n'] * 100), pc(a['med'], 0), pc(a['dd'], 0))))
    return sz, se, out

def strike(L):
    s = L['deriv']['viz']['options']['strikes']; r = s['rows']; c = max(r, key=lambda x: x[1]); p = max(r, key=lambda x: x[2]); px = close(L); ex = next((e for e in L['deriv']['options']['expiries'] if e['expiry'] == s['expiry']), None)
    sz = '%s 到期：最大痛點 %s（比收盤%s %.0f%%）。' % (ymd(s['expiry']), usd(s['maxpain']), '高' if s['maxpain'] > px else '低', abs(s['maxpain'] / px - 1) * 100); se = '%s expiry: max pain at %s (%.0f%% %s the close).' % (mde(s['expiry']), usd(s['maxpain']), abs(s['maxpain'] / px - 1) * 100, 'above' if s['maxpain'] > px else 'below')
    out = [it('買權最多', 'Most calls', usd(c[0]), usd(c[0]), 'neu', '%s；量大的履約價到期前常成為關卡。' % wan(c[1], False), '%s; big strikes often act as levels into expiry.' % kb(c[1], False)),
           it('賣權最多', 'Most puts', usd(p[0]), usd(p[0]), 'neu', '%s。' % wan(p[2], False), '%s.' % kb(p[2], False))]
    if ex:
        out.append(it('這個到期日', 'This expiry', '%.0f%%' % ex['share'], '%.0f%%' % ex['share'], 'neu', '全部未平倉 %s中佔 %.0f%%；賣權 ÷ 買權 %.2f。' % (wan(L['deriv']['options']['total_oi'], False), ex['share'], ex['pc']),
                      '%.0f%% of all %s open interest; put ÷ call %.2f.' % (ex['share'], kb(L['deriv']['options']['total_oi'], False), ex['pc'])))
    return sz, se, out

def gex(L):
    g = L['deriv']['gex']; ps = g['pos'][0] if g['pos'] else None; ng = g['neg'][0] if g['neg'] else None
    m = lambda v: ('+' if v > 0 else M if v < 0 else '') + '$%dM' % round(abs(v))
    sz = '45 天內合計 Gamma %s：現價上方 %s、下方 %s。' % (m(g['total']), m(g['above']), m(g['below'])); se = 'Total gamma within 45 days is %s: %s above price and %s below.' % (m(g['total']), m(g['above']), m(g['below']))
    out = []
    if ps: out.append(it('正 Gamma 最大', 'Largest positive', kk(ps[0]), kk(ps[0]), 'neu', '%s；做市商在這裡逆勢買賣，價格容易被定住。' % m(ps[2]), '%s; dealers trade against moves here, so price tends to pin.' % m(ps[2])))
    if ng: out.append(it('負 Gamma 最大', 'Largest negative', kk(ng[0]), kk(ng[0]), 'neu', '%s；到這裡做市商順勢買賣，波動容易放大。' % m(ng[2]), '%s; dealers trade with moves here, so swings tend to grow.' % m(ng[2])))
    out.append(it('主要到期日', 'Main expiry', md(g['main']), mde(g['main']), 'neu', '佔 45 天內未平倉 %.0f%%；推算覆蓋率 %d%%。' % (g['main_share'], g['coverage']), '%.0f%% of open interest within 45 days; estimate covers %d%%.' % (g['main_share'], g['coverage'])))
    return sz, se, out

def liq(L):
    h = L['deriv']['liq_heat']; a = h['above'][0] if h.get('above') else None; b = h['below'][0] if h.get('below') else None; w = h.get('within5') or {}
    sz = '清算最亮的帶：下方 %s、上方 %s。' % ('%s–%s' % (kusd(b['lo']), kusd(b['hi'])) if b else '—', '%s–%s' % (kusd(a['lo']), kusd(a['hi'])) if a else '—')
    se = 'The brightest band below is %s (%s) and above %s (%s).' % ('%s–%s' % (kusd(b['lo']), kusd(b['hi'])) if b else '—', pc(b['dist_pct']) if b else '', '%s–%s' % (kusd(a['lo']), kusd(a['hi'])) if a else '—', pc(a['dist_pct']) if a else '')
    out = []
    if b: out.append(it('下方（多單）', 'Below (longs)', wan(b['btc'], False), kb(b['btc'], False), 'neu', '在收盤 %s；跌到這裡強平是市價賣出，可能加速下跌。' % pc(b['dist_pct']), '%s from the close; forced selling here could speed a fall.' % pc(b['dist_pct'])))
    if a: out.append(it('上方（空單）', 'Above (shorts)', wan(a['btc'], False), kb(a['btc'], False), 'neu', '在收盤 %s；漲到這裡強平是市價買進，可能加速上漲。' % pc(a['dist_pct']), '%s from the close; forced buying here could speed a rise.' % pc(a['dist_pct'])))
    if w: out.append(it('上下 5% 內', 'Within 5%', '%s / %s' % (wan(w['below'], False).replace(' 顆', ''), wan(w['above'], False)), '%s / %s' % (kb(w['below'], False).replace(' BTC', ''), kb(w['above'], False)), 'neu',
                        '下方多單、上方空單；只代表槓桿堆在哪一側，不是方向。', 'Longs below, shorts above; it shows where leverage sits, not direction.'))
    return sz, se, out

def book(L):
    ob = L['orderbook']; t = ob['totals']; r = t['wide_bid'] / t['wide_ask']; ask = ob['walls']['ask'][0]; bid = ob['walls']['bid'][0]
    lab = lambda s: s.replace(' 永續', '')
    sz = '±15%% 內買單 $%dM、賣單 $%dM，買賣比 %.2f%s。' % (round(t['wide_bid']), round(t['wide_ask']), r, '，下方承接較厚' if r >= 1.2 else '，上方賣單較厚' if r <= .83 else ''); se = 'Within ±15%%: $%dM of bids and $%dM of asks, a ratio of %.2f%s.' % (round(t['wide_bid']), round(t['wide_ask']), r, ': thicker support below' if r >= 1.2 else ': heavier selling above' if r <= .83 else '')
    return sz, se, [
        it('最大賣牆', 'Largest ask wall', '%s–%s' % (kk(ask[0]), kk(ask[0] + 1000)), '%s–%s' % (kk(ask[0]), kk(ask[0] + 1000)), 'neu', '%s 掛了 $%dM；掛單隨時可撤，假牆很常見。' % (lab(ask[2]), round(ask[1])), '$%dM on %s; orders can be pulled, and fake walls are common.' % (round(ask[1]), lab(ask[2]).replace('Hyperliquid', 'Hyperliquid perps'))),
        it('最大買牆', 'Largest bid wall', '%s–%s' % (kk(bid[0]), kk(bid[0] + 1000)), '%s–%s' % (kk(bid[0]), kk(bid[0] + 1000)), 'neu', '%s 掛了 $%dM；同樣可以隨時撤。' % (lab(bid[2]), round(bid[1])), '$%dM on %s; it can be pulled too.' % (round(bid[1]), lab(bid[2]).replace('Hyperliquid', 'Hyperliquid perps'))),
        it('快照時間', 'Snapshot', ob['ts'][11:16] + ' UTC', ob['ts'][11:16] + ' UTC', 'neu', '%s 的一張快照，七個交易所每 $1,000 一格。' % md(ob['ts'][:10]), 'One snapshot on %s across seven venues, per $1,000.' % mde(ob['ts'][:10]))]

def legs(L):
    s = L['price']['swing']; c = s['current']; pv = s['legs'][-1]; dn = c['dir'] == 'down'
    sz = '%s段第 %d 天：從 %s 的 %s 起 %s。' % ('下跌' if dn else '上漲', c['days'], md(c['start']), usd(c['p0']), pc(c['pct'])); se = 'Day %d of a%s leg: %s from %s on %s.' % (c['days'], ' down' if dn else 'n up', pc(c['pct']), usd(c['p0']), mde(c['start']))
    n = s['n_down'] if dn else s['n_up']; mm = s['down_median_pct'] if dn else s['up_median_pct']
    return sz, se, [
        it('幅度', 'Size', pc(c['ext_pct']), pc(c['ext_pct']), 'down' if dn else 'up', '%s大於近 %d 段%s的 %d%%（中位數 %s）。' % ('最大跌幅' if dn else '最大漲幅', n, '下跌' if dn else '上漲', s['size_rank_pct'], pc(mm)),
           'The %s is bigger than %d%% of the last %d %s legs (median %s).' % ('deepest drop' if dn else 'biggest gain', s['size_rank_pct'], n, 'down' if dn else 'up', pc(mm))),
        it('本段結束線', 'Leg-end line', usd(c['end_level']), usd(c['end_level']), 'neu', '收盤%s到這裡（%s）才算本段結束。' % ('漲' if dn else '跌', pc((c['end_level'] / c['close'] - 1) * 100)), 'A close at this level (%s) ends the leg.' % pc((c['end_level'] / c['close'] - 1) * 100)),
        it('前一段', 'Previous leg', pc(pv['pct']), pc(pv['pct']), 'up' if pv['pct'] > 0 else 'down', '%s → %s，%d 天。' % (md(pv['start']), md(pv['end']), pv['days']), '%s → %s, %d days.' % (mde(pv['start']), mde(pv['end']), pv['days']))]

def k20(L):
    vp = L['price'].get('volprofile') or {}; px = close(L); m20 = L['price']['ma']['sma20']; lo, hi = vp.get('va_low'), vp.get('va_high_outer')
    where = ('下方', 'below') if px < lo else ('上方', 'above') if px > hi else ('裡面', 'inside')
    sz = '收盤在價值區%s，比成交最密的 %s %s %.1f%%。' % (where[0], usd(vp['poc']), '低' if px < vp['poc'] else '高', abs(px / vp['poc'] - 1) * 100)
    se = 'The close is %s the value area (%s–%s), %.1f%% %s the point of control at %s.' % (where[1], kusd(lo), kusd(hi), abs(px / vp['poc'] - 1) * 100, 'below' if px < vp['poc'] else 'above', usd(vp['poc']))
    r = L['price']['rows20']; up = sum(1 for x in r if x[4] >= x[1])
    return sz, se, [
        it('20 日均線', '20-day MA', usd(m20), usd(m20), 'neu', '收盤%s %.1f%%。' % ('低' if px < m20 else '高', abs(px / m20 - 1) * 100), 'The close is %.1f%% %s it.' % (abs(px / m20 - 1) * 100, 'below' if px < m20 else 'above')),
        it('價值區', 'Value area', '%s–%s' % (kusd(lo), kusd(hi)), '%s–%s' % (kusd(lo), kusd(hi)), 'neu', '這 20 天 70% 成交量的範圍。', 'Where about 70% of the last 20 days\' volume traded.'),
        it('收漲的天數', 'Up days', '%d / %d' % (up, len(r)), '%d / %d' % (up, len(r)), 'neu', '這 20 根日 K 裡收漲的根數。', 'Up candles among the last 20.')]

CARDS = dict(levels=levels, sthgap=sthgap, quant=quant, urpd=urpd, cohort=cohort, conc=conc, strike=strike, gex=gex, liq=liq, book=book, legs=legs, k20=k20)
HOWX = {
    'book': (['七個交易所每 $1,000 一格的掛單金額，綠是買單、紅是賣單。', '買賣比高於 1.2，下方承接較厚；低於 0.83，上方賣單較厚。', '掛單隨時可撤，只能看大概的位置。'],
             ['Resting orders per $1,000 across seven venues: bids in green, asks in red.', 'A bid/ask ratio above 1.2 means thicker support below; under 0.83, heavier selling above.', 'Orders can be pulled at any time, so read it for rough location only.']),
}
