# -*- coding: utf-8 -*-
"""賣壓頁的讀數（2026-11-17，取代舊版抽來的讀數；規則見 reads.py）。每個函式回傳 (一句結論中, 英, [最多三條事實])"""
from reads import sg, pc, pu, n0, sn0, wan, kb, yi, bn, md, ymd, ym, ord_en, it, M, mde, ymde, yme

PBN = dict(sth=('回到短期成本', 'price back at short-term holder cost'), psip=('獲利供給 ≤65%', 'supply in profit ≤ 65%'), sthl=('短期虧損 ≥50%', 'short-term holders in loss ≥ 50%'),
           sec=('賣方衰竭', 'seller exhaustion'), rloss=('認賠背離', 'realized-loss divergence'))
AGN = dict(lt1m=('1 個月內', 'under 1 month'), m1_6=('1–6 個月', '1–6 months'), m6_12=('6–12 個月', '6–12 months'), y1_2=('1–2 年', '1–2 years'), y2_5=('2–5 年', '2–5 years'), y5p=('5 年以上', '5+ years'))
def usd(v): return '$' + n0(v)
def kusd(v): return '$%.1fK' % (v / 1000.0)
def f1(v): return (M if v < 0 else '') + '%.1f' % abs(v)
def st(s, z=True):   # {n, up, med} → '6/13 次上漲、中位數 −0.4%'
    return ('%d/%d 次上漲、中位數 %s' if z else '%d of %d higher, median %s') % (s['up'], s['n'], pc(s['med']))

def pullback(L):
    x = L['onchain']['pullback']; ok = [i for i in x['items'] if i['ok']]; op = next((e for e in x['eps'] if e.get('r30') is None and e is x['eps'][-1]), None); pv = [e for e in x['eps'] if e.get('r30') is not None][-1]
    sz = '五項中 %d 項成立：%s。' % (x['n_ok'], '、'.join(PBN[i['id']][0] for i in ok) if ok else '一項都沒有'); se = '%d of five hold: %s.' % (x['n_ok'], ', '.join(PBN[i['id']][1] for i in ok) if ok else 'none')
    out = [it('①–③ 同時成立之後', 'After ①–③ together', '%d / %d' % (x['r30']['up'], x['r30']['n']), '%d / %d' % (x['r30']['up'], x['r30']['n']), 'neu',
              '%d 年起 %d 段，30 天後 %s（任一天 %d%%）。' % (2015, x['n_eps'], st(x['r30']), x['base30']['up']),
              '%d stretches since 2015: 30 days on, %s (any day: %d%%).' % (x['n_eps'], st(x['r30'], False), x['base30']['up'])),
           it('90 天後', '90 days on', pc(x['r90']['med']), pc(x['r90']['med']), 'neu', '%s（任一天 %s）；熊市中段也常成立，不是買點。' % (st(x['r90']), pc(x['base90']['med'])),
              '%s (any day: %s). It often holds mid-bear too, so it is not a buy signal.' % (st(x['r90'], False), pc(x['base90']['med'])))]
    if op:
        out.append(it('這一段', 'This stretch', '第 %d 天' % op['days'], 'Day %d' % op['days'], 'neu', '%s 起三項同時成立；上一段 %s 起 %d 天，30 天後 %s。' % (md(op['start']), ym(pv['start']), pv['days'], pc(pv['r30'], 0)),
                      'All three since %s; the last stretch began %s, ran %d days, and was %s 30 days on.' % (mde(op['start']), yme(pv['start']), pv['days'], pc(pv['r30'], 0))))
    return sz, se, out

def sx(L):
    s = L['chips']['stress']; f = s['rupf']; ex = s['ex']; last = s['ev'][-1] if s['ev'] else {}
    if s['state'] == 'bottom':
        sz = '賣壓 %d、動能 %.2f：底部組合成立（賣壓到 100 第 %d 天）。' % (s['r'], s['s'], s['at100']); se = 'Pressure %d, momentum %.2f: the bottom combination holds (day %d at 100).' % (s['r'], s['s'], s['at100'])
    elif s['state'] == 'strong':
        sz = '賣壓 %d、動能 %.2f：漲得又快又穩。' % (s['r'], s['s']); se = 'Pressure %d, momentum %.2f: a fast, steady rise.' % (s['r'], s['s'])
    else:
        sz = '賣壓 %d、動能 %.2f：%s。' % (s['r'], s['s'], '賣壓在累積' if s['r'] > 0 else '沒有賣壓'); se = 'Pressure %d, momentum %.2f: %s.' % (s['r'], s['s'], 'pressure is building' if s['r'] > 0 else 'no pressure')
    lo = (last.get('rup') or 99) <= f['th']; g = f['lo'] if lo else f['hi']; o = f['hi'] if lo else f['lo']
    return sz, se, [
        it('底部組合之後', 'After the bottom combination', '%d / %d' % (s['f90']['up'], s['f90']['n']), '%d / %d' % (s['f90']['up'], s['f90']['n']), 'neu', '90 天後 %s（任一天 %d%%、%s）；30 天內常還有一跌。' % (st(s['f90']), s['base90']['up'], pc(s['base90']['med'])),
           '90 days on, %s (any day: %d%%, %s); another leg down within 30 days is common.' % (st(s['f90'], False), s['base90']['up'], pc(s['base90']['med']))),
        it('離地板近不近', 'How near the floor', '%d / %d' % (g['f90']['up'], g['f90']['n']), '%d / %d' % (g['f90']['up'], g['f90']['n']), 'neu',
           '組合出現時相對未實現獲利在 %g%% %s的 %d 次，90 天後 %d 次上漲；%s的只有 %d/%d。' % (f['th'], '以下' if lo else '以上', g['f90']['n'], g['f90']['up'], '以上' if lo else '以下', o['f90']['up'], o['f90']['n']),
           'With relative unrealized profit %s %g%% on the day, %d of %d were higher 90 days on; %s it, only %d of %d.' % ('at or below' if lo else 'above', f['th'], g['f90']['up'], g['f90']['n'], 'above' if lo else 'at or below', o['f90']['up'], o['f90']['n'])),
        it('等賣壓歸零', 'Until pressure resets', '%d / %d' % (ex['win'], ex['n']), '%d / %d' % (ex['win'], ex['n']), 'neu', '從組合到賣壓歸零，%d/%d 次收高，中位數 %s、%d 天，途中再跌 %s。' % (ex['win'], ex['n'], pc(ex['med']), ex['days'], pc(ex['dip'])),
           'From the combination to the reset, %d of %d ended higher, median %s over %d days, with a further dip of %s on the way.' % (ex['win'], ex['n'], pc(ex['med']), ex['days'], pc(ex['dip'])))]

def profit(L):
    x = L['onchain']['sthl']; ep = x['eps'][-1]; op = ep.get('r30') is None
    sz = '短期持有者只有 %.1f%% 在獲利，%.1f%% 在虧損%s。' % (100 - x['value'], x['value'], '（連 %d 天過半）' % x['run50'] if x['value'] >= 50 else ''); se = 'Only %.1f%% of short-term holder coins are in profit; %.1f%% are at a loss%s.' % (100 - x['value'], x['value'], ' (over half for %d days)' % x['run50'] if x['value'] >= 50 else '')
    out = [it('虧損比例', 'At a loss', pu(x['value']), pu(x['value']), 'down' if x['value'] >= 50 else 'neu', '2015 年起平均 %s，高於 50%% 的日子佔 %.0f%%。' % (pu(x['mean_all']), x['share50']), 'Average %s since 2015; above 50%% on %.0f%% of days.' % (pu(x['mean_all']), x['share50'])),
           it('升到 60% 以上之後', 'After rising above 60%', '%d / %d' % (x['stat30']['up'], x['stat30']['n']), '%d / %d' % (x['stat30']['up'], x['stat30']['n']), 'neu', '30 天後 %s（任一天 %d%%、%s）。' % (st(x['stat30']), x['base30']['up'], pc(x['base30']['med'])),
              '30 days on, %s (any day: %d%%, %s).' % (st(x['stat30'], False), x['base30']['up'], pc(x['base30']['med'])))]
    if op:
        out.append(it('這一段最高', 'Peak this time', pu(ep['peak']), pu(ep['peak']), 'neu', '%s 升過 60%%，最高在 %s；熊市裡會升到 90%% 以上。' % (md(ep['date']), md(ep['peak_date'])), 'Above 60%% since %s, peaking on %s; in bear markets it climbs past 90%%.' % (mde(ep['date']), mde(ep['peak_date']))))
    return sz, se, out

def sopr(L):
    s = L['chips']['viz']['sopr']; d = s['dips']; cur = d[-1] if d and d[-1].get('open') else None; pv = d[-2] if cur and len(d) > 1 else None
    below = s['value'] < 1
    sz = ('短期持有者 SOPR %.3f，賠錢賣已連 %d 天。' % (s['value'], s['below_run'])) if below else '短期持有者 SOPR %.3f，賣價高於買價。' % s['value']
    se = ('Short-term holder SOPR is %.3f: selling at a loss for %d days running.' % (s['value'], s['below_run'])) if below else 'Short-term holder SOPR is %.3f: selling above cost.' % s['value']
    out = [it('最新', 'Latest', '%.3f' % s['value'], '%.3f' % s['value'], 'down' if below else 'up', '%s；1 以下是賣價低於買價。' % md(s['date']), '%s; below 1 means selling for less than was paid.' % mde(s['date']))]
    if cur and pv:
        hv = cur['sopr'] < pv['sopr']
        out.append(it('這次跌破', 'This dip', '%.3f' % cur['sopr'], '%.3f' % cur['sopr'], 'down' if hv else 'up', '比上一次（%s 的 %.3f）%s：賣壓%s。' % (md(pv['d']), pv['sopr'], '更低' if hv else '高', '加重' if hv else '遞減'),
                      '%s the last dip (%.3f on %s): selling pressure is %s.' % ('Below' if hv else 'Above', pv['sopr'], mde(pv['d']), 'heavier' if hv else 'easing')))
    yr = [x for x in d if x['d'] >= str(int(s['date'][:4]) - 1) + s['date'][4:]]
    if yr:
        lo = min(yr, key=lambda x: x['sopr'])
        out.append(it('近一年', 'Past year', '%d 次' % len(yr), '%d times' % len(yr), 'neu', '跌破 1 共 %d 次，最深 %.3f（%s）。' % (len(yr), lo['sopr'], ym(lo['d'])), 'It fell below 1 %d times; the deepest was %.3f (%s).' % (len(yr), lo['sopr'], yme(lo['d']))))
    return sz, se, out

def pnlr(L):
    p = L['onchain']['sth_pnl']; d = p['d7']
    dz, de = ('主要是認賠變多', 'mostly because loss-taking rose') if d.get('drive') == 'loss' else ('主要是獲利了結變少', 'mostly because profit-taking fell') if p['ratio'] < d['ratio'] else ('主要是獲利了結變多', 'mostly because profit-taking rose')
    return '短期持有者實現獲利是虧損的 %.2f 倍（7 天前 %.2f），%s。' % (p['ratio'], d['ratio'], dz), 'Short-term holders realized %.2f times as much profit as loss (%.2f a week ago), %s.' % (p['ratio'], d['ratio'], de), [
        it('實現獲利', 'Realized profit', wan(p['profit'], False), kb(p['profit'], False), 'neu', '%s；7 天前 %s（%s）。' % (md(p['date']), wan(d['profit'], False), pc(d['profit_chg_pct'])), '%s; %s a week earlier (%s).' % (mde(p['date']), kb(d['profit'], False), pc(d['profit_chg_pct']))),
        it('實現虧損', 'Realized loss', wan(p['loss'], False), kb(p['loss'], False), 'neu', '7 天前 %s（%s）。' % (wan(d['loss'], False), pc(d['loss_chg_pct'])), '%s a week earlier (%s).' % (kb(d['loss'], False), pc(d['loss_chg_pct'])))]

def sthsig(L):
    x = L['onchain']['sthsig']; c = x['cap']; t = x['tp']; b = x['base']
    if c['on']: sz, se = '集中認賠第 %d 天：認賠強度 %.1f。' % (c['days'], x['zl']), 'Concentrated loss-taking, day %d: loss intensity %.1f.' % (c['days'], x['zl'])
    elif t['on']: sz, se = '集中止盈第 %d 天：止盈強度 %.1f。' % (t['days'], x['zp']), 'Concentrated profit-taking, day %d: profit intensity %.1f.' % (t['days'], x['zp'])
    else: sz, se = '兩邊都不集中：止盈 %s、認賠 %s。' % (f1(x['zp']), f1(x['zl'])), 'Neither is concentrated: profit %s, loss %s.' % (f1(x['zp']), f1(x['zl']))
    g = c if (c['on'] or not t['on']) else t; nm, ne = ('集中認賠', 'concentrated loss-taking') if g is c else ('集中止盈', 'concentrated profit-taking')
    side = 'up' if x['above200'] else 'dn'; s30 = g[side]['f30']; b30 = b[side]['f30']
    return sz, se, [
        it('現在', 'Now', '%s · %s' % (f1(x['zp']), f1(x['zl'])), '%s · %s' % (f1(x['zp']), f1(x['zl'])), 'neu', '止盈、認賠強度；7 天前 %s、%s，超過 2 算集中。' % (f1(x['zp7']), f1(x['zl7'])), 'Profit and loss intensity; %s and %s a week ago. Above 2 counts as concentrated.' % (f1(x['zp7']), f1(x['zl7']))),
        it('%s之後' % nm, 'After %s' % ne, '%d / %d' % (g['all']['f90']['up'], g['all']['f90']['n']), '%d / %d' % (g['all']['f90']['up'], g['all']['f90']['n']), 'neu',
           '2012 年起 90 天後 %s（任一天 %d%%、%s）。' % (st(g['all']['f90']), b['all']['f90']['up'], pc(b['all']['f90']['med'])), 'Since 2012, 90 days on: %s (any day: %d%%, %s).' % (st(g['all']['f90'], False), b['all']['f90']['up'], pc(b['all']['f90']['med']))),
        it('均線%s（現在）' % ('上方' if x['above200'] else '下方'), '%s the 200-day MA (now)' % ('Above' if x['above200'] else 'Below'), '%d / %d' % (s30['up'], s30['n']), '%d / %d' % (s30['up'], s30['n']), 'neu',
           '收盤在 200 日均線%s時，30 天後 %s（任一天 %d%%）。' % ('上方' if x['above200'] else '下方', st(s30), b30['up']),
           'With the close %s the 200-day MA, 30 days on: %s (any day: %d%%).' % ('above' if x['above200'] else 'below', st(s30, False), b30['up']))]

def conf(L):
    c = L['onchain']['sthconf']; bz = dict(mid=('轉換期', 'transition'), pos=('偏有信心', 'confident'), neg=('信心不足', 'lacking confidence')).get(c['band'], (c['band'], c['band']))
    gap = (c['spend'] / c['hold'] - 1) * 100
    sz = '信心 %s，%s第 %d 天%s。' % (sg(c['value'], 3), bz[0], c['days'], '：方向還不明確' if c['band'] == 'mid' else ''); se = 'Confidence is %s: %s, day %d%s.' % (sg(c['value'], 3), bz[1], c['days'], ', so the direction is unclear' if c['band'] == 'mid' else '')
    dn = c['band'] == 'pos' or (c['band'] == 'mid' and c.get('last_side') == 'pos'); s = c['dn90'] if dn else c['up90']; b = c['base90']
    return sz, se, [
        it('對趨勢的信心', 'Confidence', sg(c['value'], 3), sg(c['value'], 3), 'up' if c['value'] >= c['nb'] else 'down' if c['value'] <= -c['nb'] else 'neu', '一週前 %s；±%g 之間是轉換期。' % (sg(c['d7'], 3), c['nb']), '%s a week ago; between ±%g is transition.' % (sg(c['d7'], 3), c['nb'])),
        it('兩個成本', 'Two costs', '%s / %s' % (kusd(c['spend']), kusd(c['hold'])), '%s / %s' % (kusd(c['spend']), kusd(c['hold'])), 'neu', '這 7 天賣出的幣成本比還在持有的%s %.1f%%。' % ('低' if gap < 0 else '高', abs(gap)),
           'Coins sold this week cost %.1f%% %s those still held.' % (abs(gap), 'less than' if gap < 0 else 'more than')),
        it('過去轉%s之後' % ('負' if dn else '正'), 'After past turns %s' % ('negative' if dn else 'positive'), '%d / %d' % (s['up'], s['n']), '%d / %d' % (s['up'], s['n']), 'neu', '90 天後 %s（任一天 %d%%、%s）；樣本少。' % (st(s), b['up'], pc(b['med'])),
           '90 days on: %s (any day: %d%%, %s). Few cases.' % (st(s, False), b['up'], pc(b['med'])))]

def npl(L):
    n = L['onchain']['npl']; c = n['cum30']; ls = n['loss_spike_last']; v = n['usd_m']
    sz = '最新一天淨實現損益 %s，近一年第 %d 百分位。' % (yi(v), round(n['rank_1y'])); se = 'Net realized P&L on the latest day was %s, the %s percentile of the year.' % (bn(v), ord_en(n['rank_1y']))
    w = n['sum7_usd_m'] < n['sum7_prev_usd_m']
    return sz, se, [
        it('近 7 天', 'Last 7 days', yi(n['sum7_usd_m']), bn(n['sum7_usd_m']), 'down' if n['sum7_usd_m'] < 0 else 'up', '前 7 天 %s：%s。' % (yi(n['sum7_prev_usd_m']), '認賠變多' if w and n['sum7_usd_m'] < 0 else '比前一週好'),
           'The week before: %s; %s.' % (bn(n['sum7_prev_usd_m']), 'more loss-taking' if w and n['sum7_usd_m'] < 0 else 'better than the week before')),
        it('30 天累計', '30-day total', pc(c['pct_mcap'], 2), pc(c['pct_mcap'], 2), 'neu', '%s，佔市值 %s；過去投降約在 %s。' % (yi(c['usd_m']), pc(c['pct_mcap'], 2), pc(c['thr_pct_mcap'], 1)),
           '%s, %s of market cap; past capitulations ran to about %s.' % (bn(c['usd_m']), pc(c['pct_mcap'], 2), pc(c['thr_pct_mcap'], 1))),
        it('上次明顯認賠', 'Last big loss day', md(ls['date']), mde(ls['date']), 'neu', '%s %s，近一年最極端的 %d%%。' % (ymd(ls['date']), yi(ls['usd_m']), max(1, round(ls['rank'] + .5))), '%s on %s, in the most extreme %d%% of the year.' % (bn(ls['usd_m']), ymde(ls['date']), max(1, round(ls['rank'] + .5))))]

def agepl(L):
    a = L['onchain']['agepl']; G = a['groups']
    tp = sorted(range(len(G)), key=lambda i: -a['prof'][i])[:2]; tl = sorted(range(len(G)), key=lambda i: -a['loss'][i])[:2]
    sz = '6 個月以上的人佔實現獲利 %.0f%%、實現虧損 %.0f%%；認賠多是近期進場的人。' % (a['lth_prof'], a['lth_loss']) if a['lth_loss'] < 50 else '6 個月以上的人佔實現獲利 %.0f%%、實現虧損 %.0f%%。' % (a['lth_prof'], a['lth_loss'])
    se = 'Holders of 6+ months account for %.0f%% of realized profit and %.0f%% of realized loss%s.' % (a['lth_prof'], a['lth_loss'], '; most loss-taking is by recent buyers' if a['lth_loss'] < 50 else '')
    return sz, se, [
        it('誰在獲利了結', 'Who takes profit', '%s %.0f%%' % (AGN[G[tp[0]]][0], a['prof'][tp[0]]), '%s %.0f%%' % (AGN[G[tp[0]]][1], a['prof'][tp[0]]), 'neu',
           '30 天實現獲利 %s，其次是 %s（%.0f%%）。' % (yi(a['prof_m'], False), AGN[G[tp[1]]][0], a['prof'][tp[1]]), '%s of realized profit over 30 days; next is %s (%.0f%%).' % (bn(a['prof_m'], False), AGN[G[tp[1]]][1], a['prof'][tp[1]])),
        it('誰在認賠', 'Who takes losses', '%s %.0f%%' % (AGN[G[tl[0]]][0], a['loss'][tl[0]]), '%s %.0f%%' % (AGN[G[tl[0]]][1], a['loss'][tl[0]]), 'neu',
           '30 天實現虧損 %s，其次是 %s（%.0f%%）。' % (yi(a['loss_m'], False), AGN[G[tl[1]]][0], a['loss'][tl[1]]), '%s of realized loss over 30 days; next is %s (%.0f%%).' % (bn(a['loss_m'], False), AGN[G[tl[1]]][1], a['loss'][tl[1]]))]

def rpl(L):
    if (L['onchain'].get('rpl365') or {}).get('w90') and L['onchain']['rpl365'].get('s7'): return None   # 2026-11-20 一年是預設、90 天改合計相除：讀數在 oc_data 組（兩個檢視各一份）
    r = L['onchain']['rpl']; maj = [x for x in r['reds'] if x['major']]; done = [x for x in maj[:-1] if x.get('relapse') is not None]; last = maj[-1]
    rl = [x for x in done if x['relapse']]
    sz = ('90 天實現獲利是虧損的 %.2f 倍，但最近 7 天只有 %.2f。' if r['last7'] < 1 <= r['value'] else '90 天實現獲利是虧損的 %.2f 倍，最近 7 天 %.2f。') % (r['value'], r['last7'])
    se = ('Over 90 days realized profit is %.2f times loss, but only %.2f over the last 7.' if r['last7'] < 1 <= r['value'] else 'Over 90 days realized profit is %.2f times loss; %.2f over the last 7.') % (r['value'], r['last7'])
    out = [it('90 天平均', '90-day average', '%.2f' % r['value'], '%.2f' % r['value'], 'up' if r['value'] >= 1 else 'down',
              '%s 回到 1 以上（%d 天）；上一段低於 1 是 %s–%s，%d 天。' % (md(r['since']), r['since_days'], ym(last['start']), last['end'][5:7], last['days']) if r['above'] else '%s 跌破 1，已 %d 天。' % (md(r['since']), r['since_days']),
              'Back above 1 on %s (%d days); the last spell below 1 ran %s–%s, %d days.' % (mde(r['since']), r['since_days'], yme(last['start']), yme(last['end']), last['days']) if r['above'] else 'Below 1 since %s, %d days.' % (mde(r['since']), r['since_days']))]
    y = L['onchain'].get('rpl365')
    if y and y.get('past_low') and r.get('proj') and r['above']:   # 2026-11-17：卡片只顯示三行，有一年合計時把最近 7 天併進 90 天那一行
        out[0]['dz'] = '%s 回到 1 以上（%d 天）；最近 7 天只有 %.2f，照這樣約 %s 跌回 1 以下。' % (md(r['since']), r['since_days'], r['last7'], ymd(r['proj']['date']))
        out[0]['de'] = 'Back above 1 on %s (%d days); only %.2f over the last 7, which would take the average below 1 around %s.' % (mde(r['since']), r['since_days'], r['last7'], ymde(r['proj']['date']))
    elif r.get('proj') and r['above']:
        out.append(it('最近 7 天', 'Last 7 days', '%.2f' % r['last7'], '%.2f' % r['last7'], 'down' if r['last7'] < 1 else 'up', '照這個水準，約 %s（%d 天後）跌回 1 以下。' % (ymd(r['proj']['date']), r['proj']['days']), 'At this pace the average drops below 1 around %s (%d days).' % (ymde(r['proj']['date']), r['proj']['days'])))
    if y and y.get('past_low'):   # 2026-11-17 一年合計（oc_extra.rpl365_viz）
        sz += ('一年合計 %.2f，%s 起低於 1。' if y['below'] else '一年合計 %.2f，在 1 以上。') % (y['value'], md(y['since']))
        se += (' Over one year it is %.2f, below 1 since %s.' if y['below'] else ' Over one year it is %.2f, above 1.') % (y['value'], mde(y['since']))
        pl = '過去四段最低 %.2f–%.2f' % tuple(y['past_low']); ple = 'past spells bottomed at %.2f–%.2f' % tuple(y['past_low'])
        out.append(it('一年合計', 'One-year sum', '%.2f' % y['value'], '%.2f' % y['value'], 'down' if y['below'] else 'up',
                      ('%s 跌破 1（當天 %s），已 %d 天、價格 %s；%s。' % (md(y['since']), kusd(y['since_price']), y['since_days'], pc(y['chg']), pl)) if y['below'] else ('%s 回到 1 以上，已 %d 天；%s。' % (md(y['since']), y['since_days'], pl)),
                      ('Below 1 since %s (at %s), %d days, price %s; %s.' % (mde(y['since']), kusd(y['since_price']), y['since_days'], pc(y['chg']), ple)) if y['below'] else ('Back above 1 since %s, %d days; %s.' % (mde(y['since']), y['since_days'], ple))))
        dn_ = [x for x in y['reds'] if not x.get('open')]; r_ = y['r365']; b_ = y['base365']
        out.append(it('一年低於 1 之後', 'After a year below 1', '%d / %d' % (r_['up'], r_['n']), '%d / %d' % (r_['up'], r_['n']), 'neu',
                      '比值最低那天之後一年都上漲，中位數 %s（任一天 %s）。但最低點落後價格，當時已比最低價高 %d–%d%%；跌破 1 之後期間內最多再跌 %.0f%%%s。' % (pc(r_['med'], 0), pc(b_['med'], 0), min(x['lag'] for x in dn_), max(x['lag'] for x in dn_), -min(x['dd'] for x in dn_), '，這次已跌 %.0f%%' % -y['reds'][-1]['dd'] if y['reds'][-1].get('open') and y['reds'][-1]['dd'] < 0 else ''),
                      'A year after the ratio\'s low, price was up every time, median %s (any day %s). But the low lags price: by then price was %d–%d%% above its bottom; after dropping below 1, price fell at most another %.0f%%%s.' % (pc(r_['med'], 0), pc(b_['med'], 0), min(x['lag'] for x in dn_), max(x['lag'] for x in dn_), -min(x['dd'] for x in dn_), '; this time it is already down %.0f%%' % -y['reds'][-1]['dd'] if y['reds'][-1].get('open') and y['reds'][-1]['dd'] < 0 else '')))
    if len(out) < 3: out.append(it('紅色結束之後', 'After long red spells', '%d / %d' % (len(rl), len(done)), '%d / %d' % (len(rl), len(done)), 'neu', '60 天以上低於 1 的段落結束後一年內，又跌回 1 以下的次數。', 'Spells of 60+ days below 1 that relapsed below 1 within a year of ending.'))
    return sz, se, out

def rloss(L):
    r = L['onchain']['rloss']; ch = r.get('chain') or []; cb = r['chain_back']; cp = r['back']['cap']['r30']
    sz = '每日實現虧損 %s，7 天合計 %s。' % (yi(r['usd_m'], False), yi(r['usd7_m'], False)); se = 'Daily realized loss is %s (%.1f basis points of market cap), %s over 7 days.' % (bn(r['usd_m'], False), r['bp'], bn(r['usd7_m'], False))
    out = []
    if ch:
        c = ch[-1]; KN = dict(div=('背離', 'Divergence'), flat=('差不多', 'Similar'), cap=('投降', 'Capitulation'), brk=('背離被打破', 'Divergence broken'))
        k = KN.get('brk' if c['kind'] == 'break' else c['kind'], (c['kind'], c['kind']))
        out.append(it('最近兩個峰值', 'Last two peaks', k[0] + ('' if c.get('conf') else '（暫定）'), k[1] + ('' if c.get('conf') else ' (provisional)'), 'down' if c['kind'] in ('break', 'cap') else 'neu',
                      '%s %s → %s %s，價格 %s → %s。' % (md(c['a']), yi(c['ua'], False), md(c['b']), yi(c['ub'], False), kusd(c['pa']), kusd(c['pb'])), '%s %s → %s %s, price %s → %s.' % (mde(c['a']), bn(c['ua'], False), mde(c['b']), bn(c['ub'], False), kusd(c['pa']), kusd(c['pb']))))
    out.append(it('二次背離之後', 'After a second divergence', '%d / %d' % (cb['r30']['up'], cb['r30']['n']), '%d / %d' % (cb['r30']['up'], cb['r30']['n']), 'neu',
                  '30 天後 %s（任一天 %d%%）；%d 次在 30 天內被打破。' % (st(cb['r30']), r['base30']['up'], cb['broken30']), '30 days on: %s (any day: %d%%); %d were broken within 30 days.' % (st(cb['r30'], False), r['base30']['up'], cb['broken30'])))
    out.append(it('投降之後', 'After capitulation', '%d / %d' % (cp['up'], cp['n']), '%d / %d' % (cp['up'], cp['n']), 'neu', '認賠比前一個峰值多 1 成以上，30 天後 %s。' % st(cp), 'Losses 10%%+ above the prior peak; 30 days on: %s.' % st(cp, False)))
    return sz, se, out

def ssr(L):
    s = L['onchain']['ssr']; r = s['r365']; lv = '低檔區' if s['pct4'] <= 10 else '高檔' if s['pct4'] >= 90 else '平常水準'; le = 'the low zone' if s['pct4'] <= 10 else 'a high level' if s['pct4'] >= 90 else 'a normal level'
    return '賣方風險比 %.2f%%，近 4 年第 %d 百分位：%s。' % (s['all'] * 100, round(s['pct4']), lv), 'The sell-side risk ratio is %.2f%%, the %s percentile of four years: %s.' % (s['all'] * 100, ord_en(s['pct4']), le), [
        it('全網（7 天）', 'All holders (7 days)', '%.2f%%' % (s['all'] * 100), '%.2f%%' % (s['all'] * 100), 'neu', '30 天前 %.2f%%；短期持有者 %.2f%%、長期 %.2f%%。' % (s['all30'] * 100, s['sth'] * 100, s['lth'] * 100),
           '%.2f%% thirty days ago; short-term holders %.2f%%, long-term %.2f%%.' % (s['all30'] * 100, s['sth'] * 100, s['lth'] * 100)),
        it('進入低檔區之後', 'After entering the low zone', '%d / %d' % (r['up'], r['n']), '%d / %d' % (r['up'], r['n']), 'neu', '一年後 %s（任一天 %d%%）；現在要 %.2f%% 以下。' % (st(r), s['base365']['up'], s['lo4'] * 100),
           'A year on: %s (any day: %d%%). It now takes %.2f%% or less.' % (st(r, False), s['base365']['up'], s['lo4'] * 100)),
        it('頂部的讀數', 'Readings at tops', '→'.join('%.1f' % (t['value'] * 100) for t in s['tops']) + '%', '→'.join('%.1f' % (t['value'] * 100) for t in s['tops']) + '%', 'neu', '一輪比一輪低，所以用近 4 年比，不套固定門檻。', 'Lower each cycle, so it is ranked against four years rather than a fixed line.')]

def sec(L):
    s = L['onchain']['sec']; h = s['hits']; last = h[-1]; dn = [x for x in h if x.get('done')]; up = [x for x in dn if (x.get('r365') or 0) > 0]; dd = [x for x in dn if (x.get('dd365') or 0) < -10]
    sz = '賣方衰竭常數 %.3f（第 %d 百分位）%s。' % (s['value'], round(s['pct']), '，在 %g 以下' % s['th'] if s['value'] < s['th'] else '，沒有在 %g 以下' % s['th']); se = 'The seller exhaustion constant is %.3f (the %s percentile)%s.' % (s['value'], ord_en(s['pct']), ', below %g' % s['th'] if s['value'] < s['th'] else ', not below %g' % s['th'])
    out = [it('現在', 'Now', '%.3f' % s['value'], '%.3f' % s['value'], 'neu', '2011 年起第 %d 百分位；低於 %g 的日子只佔 %.1f%%。' % (round(s['pct']), s['th'], s['th_share']), 'The %s percentile since 2011; below %g on only %.1f%% of days.' % (ord_en(s['pct']), s['th'], s['th_share'])),
           it('上次跌破', 'Last break', ym(last['date']), yme(last['date']), 'neu', '%s 跌破，之後最低 %.3f（%s，%s）。' % (ymd(last['date']), last['low'], md(last['low_date']), usd(last['low_price'])),
              'Broke on %s; the low after was %.3f (%s, %s).' % (ymde(last['date']), last['low'], mde(last['low_date']), usd(last['low_price']))),
           it('歷次跌破之後', 'After past breaks', '%d / %d' % (len(up), len(dn)), '%d / %d' % (len(up), len(dn)), 'neu', '走完一年的 %d 次，一年後都較高；但 %d 次先跌超過 10%%。' % (len(dn), len(dd)) if len(up) == len(dn) else '走完一年的 %d 次，%d 次一年後較高。' % (len(dn), len(up)),
              'All %d with a full year after were higher a year on, though %d first fell more than 10%%.' % (len(dn), len(dd)) if len(up) == len(dn) else '%d of the %d with a full year after were higher.' % (len(up), len(dn)))]
    return sz, se, out

def mom(L):
    m = L['onchain']['mom']; v = m['value']; ld = m['divs'][-1]
    sz = '鏈上勢能 %s：%s。' % (sg(v, 0), '賣出的幣整體在認賠' if v < 0 else '賣出的幣整體有獲利'); se = 'On-chain momentum is %s: %s.' % (sg(v, 0), 'coins sold are at a loss overall' if v < 0 else 'coins sold are in profit overall')
    return sz, se, [
        it('現在', 'Now', sg(v, 0), sg(v, 0), 'down' if v < 0 else 'up', '負值代表獲利了結的推力暫時消失。' if v < 0 else '正值代表獲利了結在推動。', 'Negative means the push from profit-taking has faded for now.' if v < 0 else 'Positive means profit-taking is driving it.'),
        it('頂背離之後', 'After top divergences', pc(m['dd60_med'], 0), pc(m['dd60_med'], 0), 'neu', '%d 次，60 天內最大跌幅中位數 %s（任一天 %s）。' % (m['n'], pc(m['dd60_med']), pc(m['base_dd60'])), '%d cases; median worst drop within 60 days %s (any day: %s).' % (m['n'], pc(m['dd60_med']), pc(m['base_dd60']))),
        it('最近一次頂背離', 'Last top divergence', ym(ld['date']), yme(ld['date']), 'neu', '%s，之後 60 天最多跌 %s。' % (ymd(ld['date']), pc(ld['dd60'], 0)), '%s; it fell as much as %s over the next 60 days.' % (ymde(ld['date']), pc(ld['dd60'], 0)))]

def lthrl(L):
    x = L['onchain']['lthrl']; lw = x['lows_now']; pb = [b['max'] for b in x['bears'][:-1]]
    return '長期持有者 7 天認賠 %s，佔市值 %.2f%%。' % (yi(x['usd7_m'], False), x['rel']), 'Long-term holders realized %s of losses over 7 days, %.2f%% of market cap (the %s percentile).' % (bn(x['usd7_m'], False), x['rel'], ord_en(x['pct'])), [
        it('現在', 'Now', '%.2f%%' % x['rel'], '%.2f%%' % x['rel'], 'neu', '2015 年以來第 %d 百分位：現價附近仍有長期持有者認賠。' % round(x['pct']), 'The %s percentile since 2015: some long-term holders are still selling at a loss here.' % ord_en(x['pct'])),
        it('本輪各低點', 'This cycle\'s lows', '/'.join('%.2f' % l['rel'] for l in lw) + '%', '/'.join('%.2f' % l['rel'] for l in lw) + '%', 'neu', '%s 三個低點前後 7 天的最大值。' % '、'.join(ym(l['date']) for l in lw), 'The 7-day max around the lows of %s.' % ', '.join(yme(l['date']) for l in lw)),
        it('歷輪熊市', 'Past bear markets', '/'.join('%.2f' % b['rel'] for b in pb) + '%', '/'.join('%.2f' % b['rel'] for b in pb) + '%', 'neu', '前三輪最大的一次；這輪最多 %.2f%%，沒有大規模投降。' % max(l['rel'] for l in lw),
           'The largest in each of the past three; this cycle peaked at %.2f%%, with no mass capitulation.' % max(l['rel'] for l in lw))]

def miners(L):
    m = L['onchain']['mining']; h = L['onchain']['hash_ribbons']; px = L['price']['bar']['c']; be = m['breakeven']; mt = m['block_time_s'] / 60
    K = [('17J@0.05', '17 J/TH'), ('20J@0.06', '20 J/TH'), ('25J@0.07', '25 J/TH')]; under = [n for k, n in K if be.get(k) and px < be[k]]
    sz = '算力這週 %s（%s EH/s）；下次難度調整預計 %s。' % (pc(m['wk_chg_pct']), n0(m['hash7']), pc(m['diff_next_pct'])); se = 'Hashrate %s this week (%s EH/s); the next difficulty adjustment is set for %s.' % (pc(m['wk_chg_pct']), n0(m['hash7']), pc(m['diff_next_pct']))
    return sz, se, [
        it('算力', 'Hashrate', '%s EH/s' % n0(m['hash7']), '%s EH/s' % n0(m['hash7']), 'down' if m['wk_chg_pct'] <= -5 else 'neu', '一週前 %s EH/s；30 日均 %s，比 60 日均%s %.1f%%。' % (n0(m['hash7_prev']), n0(m['hash30']), '高' if h['ratio'] >= 1 else '低', abs(h['ratio'] - 1) * 100),
           '%s EH/s a week ago; the 30-day average is %s, %.1f%% %s the 60-day.' % (n0(m['hash7_prev']), n0(m['hash30']), abs(h['ratio'] - 1) * 100, 'above' if h['ratio'] >= 1 else 'below')),
        it('電費兩平價', 'Power break-even', usd(be['20J@0.06']), usd(be['20J@0.06']), 'neu', '20 J/TH 礦機；%s。' % ('收盤低於 %s 的兩平價' % '、'.join(under) if under else '收盤高於三種礦機的兩平價'),
           'For 20 J/TH rigs; %s.' % ('the close is under break-even for %s' % ', '.join(under) if under else 'the close is above break-even for all three rig types')),
        it('下次難度調整', 'Next difficulty adjustment', pc(m['diff_next_pct']), pc(m['diff_next_pct']), 'neu', '平均 %.1f 分鐘出一塊（目標 10），%s 預計。' % (mt, md(m['retarget'])), 'Blocks every %.1f minutes on average (target 10), due %s.' % (mt, mde(m['retarget'])))]

CARDS = dict(pullback=pullback, sx=sx, profit=profit, sopr=sopr, pnlr=pnlr, sthsig=sthsig, conf=conf, npl=npl, agepl=agepl, rpl=rpl, rloss=rloss, ssr=ssr, sec=sec, mom=mom, lthrl=lthrl, miners=miners)
HOWX = {
    'pcost': (['生產成本用挖礦難度估算礦工挖一顆幣花的錢：難度越高、每天發行越少，成本越高。', '價格跌到成本下面，礦工賣一顆就虧一顆，過去多半撐不久。', '減半那天發行量少一半，成本在之後 90 天內漲到約 2 倍，常讓價格「被動」落到成本下面。'],
              ['Production cost uses mining difficulty to estimate what it costs miners to produce one coin: higher difficulty or lower issuance means a higher cost.', 'Below cost, miners lose money on every coin they sell, which has rarely lasted.', 'A halving cuts issuance in half, so cost roughly doubles over the next 90 days and often leaves price below it without any sell-off.']),
    'miners': (['算力是全網礦機的總運算量；一週掉 10% 以上，常是礦工在關機。', '電費兩平價是三種效率的礦機在不同電價下，賣幣剛好付得起電費的價格。', '難度每 2,016 個區塊調整一次，讓平均出塊時間回到 10 分鐘。'],
               ['Hashrate is the network\'s total mining power; a drop of 10% or more in a week often means miners are switching off.', 'Power break-even is the price at which three rig efficiencies just cover their electricity at different power costs.', 'Difficulty resets every 2,016 blocks to bring block times back to 10 minutes.']),
}
