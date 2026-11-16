# -*- coding: utf-8 -*-
"""槓桿頁的讀數（2026-11-17，取代舊版抽來的讀數；規則見 reads.py）。每個函式回傳 (一句結論中, 英, [最多三條事實])"""
from reads import sg, pc, pu, n0, sn0, wan, kb, yi, bn, md, ymd, ym, ord_en, it, M, mde, ymde, yme

def usd(v): return '$' + n0(v)
def st(s, z=True): return ('%d/%d 次上漲、中位數 %s' if z else '%d of %d higher, median %s') % (s['up'], s['n'], pc(s['med']))
def mm(v): return (M if v < 0 else '') + ('$%.2fB' % (abs(v) / 1000) if abs(v) >= 1000 else '$%dM' % round(abs(v)))

def fh(L):
    x = L['deriv']['fund_hist']; ng, ht = x['neg'], x['hot']; v = x['value']
    lv = '槓桿多單擁擠' if v >= ht['th'] else '空方付費，槓桿偏空' if v < 0 else '多方付費，水準不高'; le = 'crowded leveraged longs' if v >= ht['th'] else 'shorts are paying, so leverage leans short' if v < 0 else 'longs are paying, at a modest level'
    return '資金費率 7 日平均 %s（年化），%s。' % (pc(v), lv), 'Funding is %s annualized (7-day average): %s.' % (pc(v), le), [
        it('7 日平均', '7-day average', pc(v), pc(v), 'neu', '30 天前 %s；2021 年以來第 %d 百分位，已連 %d 天%s。' % (pc(x['v30']), x['pct'], x['run'], '為正' if v >= 0 else '為負'),
           '%s thirty days ago; the %s percentile since 2021, %s for %d days.' % (pc(x['v30']), ord_en(x['pct']), 'positive' if v >= 0 else 'negative', x['run'])),
        it('轉負之後', 'After turning negative', '%d / %d' % (ng['st']['up'], ng['st']['n']), '%d / %d' % (ng['st']['up'], ng['st']['n']), 'neu', '90 天後 %s（任一天 %d%%、%s）；最近一次 %s。' % (st(ng['st']), x['base']['up'], pc(x['base']['med']), ym(ng['ev'][-1]['date'])),
           '90 days on: %s (any day: %d%%, %s); last in %s.' % (st(ng['st'], False), x['base']['up'], pc(x['base']['med']), yme(ng['ev'][-1]['date']))),
        it('升到 %d%% 以上之後' % ht['th'], 'After topping %d%%' % ht['th'], '%d / %d' % (ht['st']['up'], ht['st']['n']), '%d / %d' % (ht['st']['up'], ht['st']['n']), 'neu', '90 天後 %s；多單擁擠之後常有一次清洗。' % st(ht['st']),
           '90 days on: %s; crowded longs are often flushed afterwards.' % st(ht['st'], False))]

def basis(L):
    d = L['deriv']['deriv']; c = d['basis_curve']; lo = min(r[1] for r in c); hi = max(r[1] for r in c); near = c[0][1] >= c[-1][1]
    lv = '偏高' if d['basis_median'] > 15 else '偏低' if d['basis_median'] < 3 else '中性'; le = 'high' if d['basis_median'] > 15 else 'low' if d['basis_median'] < 3 else 'neutral'
    return '各期限年化基差 %.1f–%.1f%%，%s；水準%s。' % (lo, hi, '近月較高' if near else '遠月較高', lv), 'Annualized basis runs %.1f–%.1f%% across expiries, %s; the level is %s.' % (lo, hi, 'higher up front' if near else 'higher further out', le), [
        it('中位數', 'Median', pu(d['basis_median']), pu(d['basis_median']), 'neu', '3–15% 屬常態；太高代表槓桿多頭擁擠，負值代表恐慌。', '3–15% is normal; too high means crowded leveraged longs, negative means panic.'),
        it('最近的到期', 'Nearest expiry', pu(c[0][1]), pu(c[0][1]), 'neu', '%.0f 天後到期；最遠 %.0f 天 %s。' % (c[0][0], c[-1][0], pu(c[-1][1])), '%.0f days out; the furthest, %.0f days, is %s.' % (c[0][0], c[-1][0], pu(c[-1][1]))),
        it('永續資金費率', 'Perp funding', pu(d['funding_ann']), pu(d['funding_ann']), 'neu', '年化；比基差中位數%s %.2f 個百分點。' % ('低' if d['perp_minus_basis_pp'] < 0 else '高', abs(d['perp_minus_basis_pp'])),
           'Annualized; %.2f points %s the median basis.' % (abs(d['perp_minus_basis_pp']), 'below' if d['perp_minus_basis_pp'] < 0 else 'above'))]

def oih(L):
    o = L['deriv']['oi_hist']; up = o['chg30'] > 0; pu_ = o['px30'] > 0
    rd = ('價格跌、未平倉增：逆勢開新倉，槓桿在堆' if up and not pu_ else '價格漲、未平倉增：新資金跟進' if up and pu_ else '價格跌、未平倉減：槓桿在退' if not pu_ else '價格漲、未平倉減：空單回補')
    re_ = ('price down, open interest up: new positions against the move, leverage building' if up and not pu_ else 'price and open interest both up: new money following' if up and pu_ else 'price and open interest both down: leverage unwinding' if not pu_ else 'price up, open interest down: shorts covering')
    sh = '槓桿在堆' if up and not pu_ else '新資金跟進' if up else '槓桿在退' if not pu_ else '空單回補'
    return '未平倉 %s，30 天 %s、價格 %s：%s。' % (wan(o['btc'], False), pc(o['chg30']), pc(o['px30']), sh), 'Open interest is about %s, %s over 30 days (price %s): %s.' % (kb(o['btc'], False), pc(o['chg30']), pc(o['px30']), re_.split(': ')[1]), [
        it('合計', 'Total', wan(o['btc'], False), kb(o['btc'], False), 'neu', '約 $%.1fB，2021 年以來第 %d 百分位；7 天 %s、90 天 %s。' % (o['usd_b'], o['pct'], pc(o['chg7']), pc(o['chg90'])),
           'About $%.1fB, the %s percentile since 2021; %s over 7 days and %s over 90.' % (o['usd_b'], ord_en(o['pct']), pc(o['chg7']), pc(o['chg90']))),
        it('30 天：價格 / 未平倉', '30 days: price / OI', '%s / %s' % (pc(o['px30']), pc(o['chg30'])), '%s / %s' % (pc(o['px30']), pc(o['chg30'])), 'neu', rd + '。', re_[:1].upper() + re_[1:] + '.'),
        it('幣本位占比', 'Coin-margined share', pu(o['coin_share']), pu(o['coin_share']), 'neu', '一年前 %s；越低，跌價時連環清算的放大效果越小。' % pu(o['coin_share_1y']), '%s a year ago; the lower it is, the less a fall feeds on itself through margin.' % pu(o['coin_share_1y']))]

def lsa(L):
    x = L['deriv']['ls_acct']; h, l = x['hi'], x['lo']; v = x['binance']
    sz = 'Binance %s 的帳戶做多（第 %d 百分位）%s。' % (pu(v), x['pct'], '，偏多擁擠' if v >= x['p90'] else '，偏空' if v <= x['p10'] else ''); se = '%s of Binance accounts are long (the %s percentile since 2021)%s.' % (pu(v), ord_en(x['pct']), ', a crowded long' if v >= x['p90'] else ', leaning short' if v <= x['p10'] else '')
    return sz, se, [
        it('現在', 'Now', 'Binance %s' % pu(v), 'Binance %s' % pu(v), 'neu', '30 天前 %s、中位數 %s；Bybit %s。' % (pu(x['b30']), pu(x['med']), pu(x['bybit'])), '%s thirty days ago, median %s; Bybit %s.' % (pu(x['b30']), pu(x['med']), pu(x['bybit']))),
        it('≥ %s 之後' % pu(x['p90']), 'After ≥ %s' % pu(x['p90']), '%d / %d' % (h['st']['up'], h['st']['n']), '%d / %d' % (h['st']['up'], h['st']['n']), 'neu', '90 天後 %s（任一天 %d%%）。' % (st(h['st']), x['base']['up']), '90 days on: %s (any day: %d%%).' % (st(h['st'], False), x['base']['up'])),
        it('≤ %s 之後' % pu(x['p10']), 'After ≤ %s' % pu(x['p10']), '%d / %d' % (l['st']['up'], l['st']['n']), '%d / %d' % (l['st']['up'], l['st']['n']), 'neu', '90 天後 %s；算的是帳戶數，比較像散戶情緒。' % st(l['st']), '90 days on: %s. It counts accounts, so it reads like retail mood.' % st(l['st'], False))]

def lqv(L):
    x = L['deriv']['liq_vol']; d30 = x['d30']; h = x['hi_long']; tot = d30['long'] + d30['short']
    return '近 30 天被清算的多單佔 %.0f%%（多單 %s、空單 %s）。' % (d30['share'], mm(d30['long']), mm(d30['short'])), 'Longs made up %.0f%% of liquidations over 30 days (%s of longs, %s of shorts).' % (d30['share'], mm(d30['long']), mm(d30['short'])), [
        it('多單占比', 'Long share', '%.0f%%' % d30['share'], '%.0f%%' % d30['share'], 'down' if d30['share'] >= 60 else 'neu', '2022/10 以來第 %d 百分位；近 7 天 %.0f%%、90 天 %.0f%%。' % (x['share_pct'], x['d7']['share'], x['d90']['share']),
           'The %s percentile since Oct 2022; %.0f%% over 7 days and %.0f%% over 90.' % (ord_en(x['share_pct']), x['d7']['share'], x['d90']['share'])),
        it('30 天總量', '30-day total', mm(tot), mm(tot), 'neu', '第 %d 百分位；最近一天多單 %s、空單 %s。' % (x['tot30_pct'], mm(x['day']['long']), mm(x['day']['short'])), 'The %s percentile; the latest day: %s longs, %s shorts.' % (ord_en(x['tot30_pct']), mm(x['day']['long']), mm(x['day']['short']))),
        it('多單 ≥ %d%% 之後' % h['th'], 'After longs ≥ %d%%' % h['th'], '%d / %d' % (h['st']['up'], h['st']['n']), '%d / %d' % (h['st']['up'], h['st']['n']), 'neu', '90 天後 %s（任一天 %d%%）；樣本少。' % (st(h['st']), x['base']['up']), '90 days on: %s (any day: %d%%). Few cases.' % (st(h['st'], False), x['base']['up']))]

def vol(L):
    d = L['deriv']['dvol']; rv = (L['price'].get('vol') or {}); r30 = rv.get('rv30') or rv.get('rv_30')
    sp = d['value'] - r30 if r30 is not None else None
    sz = 'DVOL %.1f（一年第 %d 百分位）%s。' % (d['value'], round(d['pct_1y']), '，和實際波動 %.1f 差不多' % r30 if sp is not None and abs(sp) < 3 else '，比實際波動%s %.1f 點' % ('高' if sp > 0 else '低', abs(sp)) if sp is not None else '')
    se = 'DVOL is %.1f (the %s percentile of the year)%s.' % (d['value'], ord_en(d['pct_1y']), ', about level with realized volatility of %.1f' % r30 if sp is not None and abs(sp) < 3 else ', %.1f points %s realized' % (abs(sp), 'above' if sp > 0 else 'below') if sp is not None else '')
    out = [it('DVOL', 'DVOL', '%.1f' % d['value'], '%.1f' % d['value'], 'neu', '前一天 %.1f；一年第 %d 百分位。' % (d['prev'], round(d['pct_1y'])), '%.1f the day before; the %s percentile of the year.' % (d['prev'], ord_en(d['pct_1y'])))]
    if sp is not None:
        out.append(it('IV − RV30', 'IV − RV30', sg(sp, 1), sg(sp, 1), 'neu', '相差不到 3 點：選擇權定價大致公允。' if abs(sp) < 3 else '隱含比實際高：有恐慌溢價。' if sp > 0 else '隱含比實際低：選擇權便宜。',
                      'Within 3 points: options are fairly priced.' if abs(sp) < 3 else 'Implied above realized: a fear premium.' if sp > 0 else 'Implied below realized: options are cheap.'))
    return sz, se, out

def ivt(L):
    x = L['deriv']['ivterm']; t = x['t']; p = x['prev7']; inv = x['slope'] > 0
    sz = '7 天 %.1f%%、90 天 %.1f%%，相差 %s 點%s。' % (t['7'], t['90'], sg(x['slope'], 1), '（倒掛：近月較貴）' if inv else ''); se = '7-day %.1f%%, 90-day %.1f%%: a %s-point gap%s.' % (t['7'], t['90'], sg(x['slope'], 1), ' (inverted: the front is dearer)' if inv else '')
    return sz, se, [
        it('7 − 90 天', '7 − 90 days', sg(x['slope'], 1), sg(x['slope'], 1), 'warn' if inv else 'neu', '30 天 %.1f%%、180 天 %.1f%%；%s' % (t['30'], t['180'], '近月貴，常見於急跌或大事件前後。' if inv else '遠月較貴，是平常的形狀。'),
           '30-day %.1f%%, 180-day %.1f%%; %s' % (t['30'], t['180'], 'a dear front end is common around sharp falls or big events.' if inv else 'a dearer back end is the normal shape.')),
        it('和 7 天前比', 'Versus a week ago', '%s → %s' % (sg(p['slope'], 1), sg(x['slope'], 1)), '%s → %s' % (sg(p['slope'], 1), sg(x['slope'], 1)), 'neu', '7 天 %s 點、90 天 %s 點。' % (sg(t['7'] - p['t']['7'], 1), sg(t['90'] - p['t']['90'], 1)), '7-day %s points, 90-day %s points.' % (sg(t['7'] - p['t']['7'], 1), sg(t['90'] - p['t']['90'], 1)))]

def oi(L):
    o = L['deriv']['options']; e = max(o['expiries'], key=lambda e: e['oi']); px = L['price']['bar']['c']
    return '最大的到期是 %s（佔 %.0f%%），最大痛點 %s。' % (ymd(e['expiry']), e['share'], usd(e['maxpain'])), 'The largest expiry is %s (%.0f%% of open interest), max pain %s.' % (ymde(e['expiry']), e['share'], usd(e['maxpain'])), [
        it('最大到期', 'Largest expiry', md(e['expiry']), mde(e['expiry']), 'neu', '賣權 ÷ 買權 %.2f；最大痛點比收盤%s %.0f%%。' % (e['pc'], '高' if e['maxpain'] > px else '低', abs(e['maxpain'] / px - 1) * 100),
           'Put ÷ call %.2f; max pain is %.0f%% %s the close.' % (e['pc'], abs(e['maxpain'] / px - 1) * 100, 'above' if e['maxpain'] > px else 'below')),
        it('全部未平倉', 'All open interest', wan(o['total_oi'], False), kb(o['total_oi'], False), 'neu', '共 %d 個到期日；到期前價格被拉向最大痛點的證據薄弱。' % len(o['expiries']), '%d expiries in all; the evidence that price is pulled to max pain is thin.' % len(o['expiries']))]

def prem(L):
    p = L['deriv']['prem']; neg = p['a7'] < 0; m = lambda v: (M if v < 0 else '+' if v > 0 else '') + '$%.1fM' % abs(v)
    return '權利金差 7 日平均 %s，%s已 %d 天。' % (m(p['a7']), '偏買賣權' if neg else '偏買買權', p['run']), 'The 7-day average premium gap is %s, tilted to %s for %d days.' % (m(p['a7']), 'puts' if neg else 'calls', p['run']), [
        it('最近一天', 'Latest day', m(p['net']), m(p['net']), 'down' if p['net'] < 0 else 'up', '買方花在買權 $%.0fM、賣權 $%.0fM。' % (p['call'], p['put']), 'Buyers spent $%.0fM on calls and $%.0fM on puts.' % (p['call'], p['put'])),
        it('轉負之後', 'After turning negative', '%d / %d' % (p['r30']['up'], p['r30']['n']), '%d / %d' % (p['r30']['up'], p['r30']['n']), 'neu', '%s 起 %d 次，30 天後 %s；資料只有一年。' % (ym(p['since']), p['n_flips'], st(p['r30'])), '%d times since %s; 30 days on: %s. Only a year of data.' % (p['n_flips'], yme(p['since']), st(p['r30'], False)))]

def pcr(L):
    p = L['deriv']['pcr']; r = p['rr25']
    sz = '25Δ 風險逆轉 %s：%s；看跌／看漲比 %.2f。' % (sg(r, 2), '賣權較貴，市場在買下跌保護' if r < 0 else '買權較貴，市場在追上漲', p['oi_pcr']); se = '25-delta risk reversal %s: %s; put/call ratio %.2f.' % (sg(r, 2), 'puts are dearer, so the market is buying downside protection' if r < 0 else 'calls are dearer, so the market is chasing upside', p['oi_pcr'])
    return sz, se, [
        it('25Δ 風險逆轉', '25Δ risk reversal', sg(r, 2), sg(r, 2), 'down' if r < -5 else 'neu', '30 天期；賣權比買權%s %.1f 點。' % ('貴' if r < 0 else '便宜', abs(r)), '30-day; puts are %.1f points %s than calls.' % (abs(r), 'dearer' if r < 0 else 'cheaper')),
        it('看跌／看漲比', 'Put/call ratio', '%.2f' % p['oi_pcr'], '%.2f' % p['oi_pcr'], 'neu', '未平倉；24 小時成交 %.2f。大於 1＝看跌部位比較多。' % p['vol_pcr'], 'Open interest; 24-hour volume %.2f. Above 1 means more puts.' % p['vol_pcr'])]

def fng(L):
    f = L['flows']['fng_hist']; v = f['value']
    lz = '極度恐懼' if v <= f['lo'] else '恐懼' if v < 45 else '極度貪婪' if v >= f['hi'] else '貪婪' if v > 55 else '中性'; le = 'extreme fear' if v <= f['lo'] else 'fear' if v < 45 else 'extreme greed' if v >= f['hi'] else 'greed' if v > 55 else 'neutral'
    s30 = f['f30'] if v <= f['lo'] else f['g30'] if v >= f['hi'] else None
    out = [it('恐懼貪婪指數', 'Fear & Greed', '%d · %s' % (v, lz), '%d · %s' % (v, le), 'neu', '一個月前 %d；2018 年以來第 %d 百分位。' % (f['d30'], round(f['pct'])), '%d a month ago; the %s percentile since 2018.' % (f['d30'], ord_en(f['pct'])))]
    out.append(it('極度恐懼之後', 'After extreme fear', '%d / %d' % (f['f30']['up'], f['f30']['n']), '%d / %d' % (f['f30']['up'], f['f30']['n']), 'neu', '30 天後 %s（任一天 %d%%）；第一次掉進去常不是底。' % (st(f['f30']), f['base30']['up']),
                  '30 days on: %s (any day: %d%%). The first drop into it is often not the bottom.' % (st(f['f30'], False), f['base30']['up'])))
    out.append(it('極度貪婪之後', 'After extreme greed', '%d / %d' % (f['g30']['up'], f['g30']['n']), '%d / %d' % (f['g30']['up'], f['g30']['n']), 'neu', '30 天後 %s；樣本很少。' % st(f['g30']), '30 days on: %s. Very few cases.' % st(f['g30'], False)))
    return '恐懼貪婪指數 %d（%s），一週前 %d、30 日平均 %.0f。' % (v, lz, f['d7'], f['avg30']), 'Fear & Greed is %d (%s), from %d a week ago; 30-day average %.0f.' % (v, le, f['d7'], f['avg30']), out

def wiki(L):
    w = L['flows']['wiki']; s = w['s30']
    return '維基百科瀏覽量是一年中位數的 %.2f 倍（每天約 %s 次）。' % (w['ratio'], n0(w['v7'])), 'Wikipedia views are %.2f times the one-year median (about %s a day).' % (w['ratio'], n0(w['v7'])), [
        it('7 日平均', '7-day average', '×%.2f' % w['ratio'], '×%.2f' % w['ratio'], 'warn' if w['ratio'] >= w['spike'] else 'neu', '一個月前 ×%.2f；絕對量在 2016 年以來第 %d 百分位。' % (w['r30'], round(w['pct'])), '×%.2f a month ago; the absolute level is the %s percentile since 2016.' % (w['r30'], ord_en(w['pct']))),
        it('暴增之後', 'After spikes', '%d / %d' % (s['up'], s['n']), '%d / %d' % (s['up'], s['n']), 'neu', '到中位數 %.1f 倍以上共 %d 次，30 天後 %s；頂部和急跌都會暴增。' % (w['spike'], len(w['spikes']), st(s)),
           '%d times at %.1f× the median or more; 30 days on: %s. Both tops and crashes cause spikes.' % (len(w['spikes']), w['spike'], st(s, False)))]

CARDS = dict(fh=fh, basis=basis, oih=oih, lsa=lsa, lqv=lqv, vol=vol, ivt=ivt, oi=oi, prem=prem, pcr=pcr, fng=fng, wiki=wiki)
HOWX = {
    'pcr': (['25Δ 風險逆轉：同樣價外程度的買權減賣權的隱含波動率；負值代表賣權較貴，市場在買下跌保護。', '看跌／看漲比：Deribit 全部到期的賣權未平倉 ÷ 買權未平倉；大於 1 代表看跌部位較多。', '兩者都是情緒的溫度計，不是方向訊號。'],
            ['25-delta risk reversal: call minus put implied volatility at the same distance out of the money; negative means puts are dearer and the market is buying protection.', 'Put/call ratio: Deribit put open interest ÷ call open interest across all expiries; above 1 means more puts.', 'Both are sentiment gauges, not direction signals.']),
}
