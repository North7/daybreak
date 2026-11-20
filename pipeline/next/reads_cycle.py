# -*- coding: utf-8 -*-
"""週期頁的讀數（2026-11-17，取代舊版抽來的讀數；規則見 reads.py）。每個函式回傳 (一句結論中, 英, [最多三條事實])"""
import datetime as dt
from reads import sg, pc, pu, n0, sn0, wan, kb, md, ymd, ym, ord_en, it, M, mde, ymde, yme, MON

SG = [('深夜', 'Deep night', '底部區', 'bottom zone'), ('入夜', 'Nightfall', '下跌', 'falling'), ('破曉', 'Daybreak', '初升', 'early rise'), ('白晝', 'Daylight', '上升', 'rising'), ('黃昏', 'Dusk', '過熱', 'overheated')]
HEAT = dict(lnupl=('長期持有者 NUPL', 'long-term holder NUPL'), rup=('未實現獲利 ÷ 市值', 'unrealized profit ÷ market cap'), pl=('冪律殘差', 'power-law residual'), rr=('儲備風險', 'reserve risk'), mvz=('MVRV-Z', 'MVRV-Z'))
STN = {'熊市': 'Bear market', '轉換期': 'Transition', '牛市': 'Bull market'}
EVN = dict(mom12='12-month momentum', mvrv1y='MVRV vs its one-year mean', rcgrowth='Capital inflow', xs90='Exchange supply', sth='Short-term holder cost', tmm='STH cost vs true market mean')
RGN = dict(d200=('200 日均線', '200-day MA'), mom12=('12 個月動能', '12-month momentum'), mvrv1y=('MVRV 對一年均值', 'MVRV vs its one-year mean'), rc30=('實現市值', 'realized cap'), xs90=('交易所供給', 'exchange supply'), rpl=('實現獲利 ÷ 虧損', 'realized profit ÷ loss'))
LNS = dict(cap=('投降', 'Capitulation'), hope=('希望／恐懼', 'Hope / fear'), opt=('樂觀／焦慮', 'Optimism / anxiety'), belief=('信念／否認', 'Belief / denial'), euph=('興奮／貪婪', 'Euphoria / greed'))
MFZ = '一二三四五六七八九十'
def mz(m): return ('十' + MFZ[m - 11]) if m > 10 else MFZ[m - 1] if m < 10 else '十'
MONF = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
def usd(v): return '$' + n0(v)
def kusd(v): return '$%.1fK' % (v / 1000.0)
def yr(d): return d[:4]
def bb(b): return '$0' if not b else ('$%.1fB' % b) if abs(b) < 100 else ('$%sB' % n0(b))   # 十億美元
def bbs(b): return ('+' if b > 0 else M if b < 0 else '') + bb(abs(b))
def wl(vs, sign=True): return '、'.join(('+' if v > 0 and sign else M if v < 0 else '') + n0(abs(v) / 1e4) for v in vs) + ' 萬顆'   # 一串萬顆
def ml(vs, sign=True): return ', '.join(('+' if v > 0 and sign else M if v < 0 else '') + '%.2fM' % (abs(v) / 1e6) for v in vs) + ' BTC'
def yiz(b): return '0' if not b else ('+' if b > 0 else M if b < 0 else '') + n0(abs(b) * 10) + ' 億美元'
def days(a, b): return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days

def dawn(L):
    d = L['cycle']['dawn']; s = SG[d['stage']]; lo = min(d['heat_c'], key=lambda c: c['pct']); st = next(x for x in d['stats'] if x['stage'] == d['stage']); b = d['base']
    rz, re_ = ('多方', 'long') if d['regime'] > 0 else ('空方', 'short')
    sz = '熱度 %.0f，%s（%s）；方向%s，第 %d 週。' % (d['heat'], s[0], s[2], rz, d['weeks'])
    se = 'Heat %.0f: %s (%s); direction %s, week %d.' % (d['heat'], s[1], s[3], re_, d['weeks'])
    return sz, se, [
        it('現在', 'Now', s[0], s[1], 'neu', '這階段第 %d 週；過去 %d 週一年後 %d%% 上漲、中位數 %s（全部的週 %d%%）。' % (d['stage_weeks'], st['weeks'], st['y1']['up'], pc(st['y1']['med'], 0), b['up']),
           'Week %d of this stage; of %d such weeks since 2013, %d%% were higher a year later, median %s (all weeks: %d%%).' % (d['stage_weeks'], st['weeks'], st['y1']['up'], pc(st['y1']['med'], 0), b['up'])),
        it('熱度', 'Heat', '%.0f / 100' % d['heat'], '%.0f / 100' % d['heat'], 'neu', '4 週前 %.0f、13 週前 %.0f；五項估值裡最低的是%s，近 4 年第 %d 百分位。' % (d['heat4'], d['heat13'], HEAT[lo['key']][0], lo['pct']),
           '%.0f four weeks ago and %.0f thirteen weeks ago; the lowest of the five valuations is %s, the %s percentile of four years.' % (d['heat4'], d['heat13'], HEAT[lo['key']][1], ord_en(lo['pct']))),
        it('方向', 'Direction', rz, re_.capitalize(), 'up' if d['regime'] > 0 else 'down', '%s 翻%s；四項趨勢合計 %s，連 4 週在另一邊才翻。' % (ymd(d['since']), '多' if d['regime'] > 0 else '空', sg(d['trend'], 2)),
           'Turned %s on %s; the four trend inputs sum to %s, and it takes four weeks on the other side to flip.' % (re_, ymde(d['since']), sg(d['trend'], 2)))]

def stage(L):
    s = L['cycle']['stage']; e = s['evidence']; ok = [x for x in e['items'] if x['ok']]; px = L['price']['bar']['c']; gap = (px / s['sma200'] - 1) * 100
    lk = s['stage'] == '牛市'   # 2026-11-20：牛市是鎖定的標籤，一句結論就講清楚，鎖定的規則和進度在卡上第一列（cycle_data.py），證據裡不再重講
    sz = '市場階段：%s（%s 起%s），收盤在 200 日均線%s %.0f%%。' % (s['stage'], md(s['since']), '，鎖定中' if lk else '', '上' if gap >= 0 else '下', abs(gap)); se = 'Market stage: %s (since %s%s), with the close %.0f%% %s the 200-day MA.' % (STN.get(s['stage'], s['stage']).lower(), mde(s['since']), ', locked' if lk else '', abs(gap), 'above' if gap >= 0 else 'below')
    if s['stage'] == '牛市':
        rz, re_ = '牛市鎖定；要在下降的 200 日均線下連 30 天才退回熊市。', 'Bull is locked in; it takes 30 days under a falling 200-day MA to go back to bear.'
    elif s['stage'] == '轉換期':
        rz, re_ = '在上升的 200 日均線上連 30 天成為牛市；連 5 天收在下方退回熊市。', '30 days above a rising 200-day MA makes it bull; 5 closes below send it back to bear.'
    else:
        rz, re_ = '投降出現過、收盤站上上升的 200 日均線，才進入轉換期。', 'It needs a capitulation and a close above a rising 200-day MA to enter transition.'
    return sz, se, [
        *([] if lk else [it('階段', 'Stage', s['stage'], STN.get(s['stage'], s['stage']), 'neu', rz, re_)]),
        it('200 日均線', '200-day MA', usd(s['sma200']), usd(s['sma200']), 'neu', '收盤%s均線 %.1f%%；均線%s（30 天前 %s）。' % ('高於' if gap >= 0 else '低於', abs(gap), '還在上升' if s['sma200_rising'] else '在下降', usd(s['sma200_30d_ago'])),
           'The close is %.1f%% %s it; the average is %s (%s 30 days ago).' % (abs(gap), 'above' if gap >= 0 else 'below', 'still rising' if s['sma200_rising'] else 'falling', usd(s['sma200_30d_ago']))),
        it('佐證燈', 'Supporting lights', '%d / %d' % (len(ok), e['n']), '%d / %d' % (len(ok), e['n']), 'neu', ('亮的：%s。' % '、'.join(x['label'] for x in ok) if ok else '一盞都沒亮。') + '只作佐證，不參與判定。',
           ('On: %s. ' % ', '.join(EVN.get(x['id'], x['id']).lower() for x in ok) if ok else 'None are on. ') + 'They support the label but do not decide it.')]

def regime(L):
    r = L['cycle']['regime']; on = r['regime'] > 0; neg = r['value'] < 0
    up = [c for c in r['comps'] if c['val'] >= .15]; dn = [c for c in r['comps'] if c['val'] <= -.15]
    fl = [f for f in r['flips'] if f['dir'] == (1 if on else -1) and f.get('r52') is not None]; good = [f for f in fl if (f['r52'] > 0) == on]; bad = [f for f in fl if f not in good]
    if r['pending']:
        sz = '分數 %s，%s第 %d 週；再 %d 週才翻%s（%s 起是%s）。' % (sg(r['value'], 2), '轉負' if neg else '轉正', r['pending'], 4 - r['pending'], '空' if on else '多', md(r['since']), '多方' if on else '空方')
        se = 'The score is %s, %d week%s on the %s side; %d more and it flips %s (%s since %s).' % (sg(r['value'], 2), r['pending'], '' if r['pending'] == 1 else 's', 'negative' if neg else 'positive', 4 - r['pending'], 'short' if on else 'long', 'long' if on else 'short', mde(r['since']))
    else:
        sz = '分數 %s，%s第 %d 週（%s 起）。' % (sg(r['value'], 2), '多方' if on else '空方', r['weeks'], md(r['since'])); se = 'The score is %s: %s for %d weeks (since %s).' % (sg(r['value'], 2), 'long' if on else 'short', r['weeks'], mde(r['since']))
    return sz, se, [
        it('多空分數', 'Score', sg(r['value'], 2), sg(r['value'], 2), 'up' if r['value'] > 0 else 'down', '一週前 %s、四週前 %s；範圍 −6 到 +6，絕對值小於 1 容易反覆。' % (sg(r['prev'], 2), sg(r['prev4'], 2)),
           '%s a week ago and %s four weeks ago. It runs from −6 to +6, and below 1 either way it flips easily.' % (sg(r['prev'], 2), sg(r['prev4'], 2))),
        it('六項', 'Six inputs', '%d 多 %d 空' % (len(up), len(dn)), '%d long, %d short' % (len(up), len(dn)), 'neu', '偏多：%s；偏空：%s。' % ('、'.join(RGN[c['key']][0] for c in up) or '無', '、'.join(RGN[c['key']][0] for c in dn) or '無'),
           'Long: %s. Short: %s.' % (', '.join(RGN[c['key']][1] for c in up) or 'none', ', '.join(RGN[c['key']][1] for c in dn) or 'none')),
        it('過去翻%s之後' % ('多' if on else '空'), 'After past %s turns' % ('long' if on else 'short'), '%d / %d' % (len(good), len(fl)), '%d / %d' % (len(good), len(fl)), 'neu',
           '2013 年以來 %d 次，%d 次一年後%s；錯的：%s。' % (len(fl), len(good), '較高' if on else '較低', '、'.join('%s %s' % (ym(f['date']), pc(f['r52'], 0)) for f in bad) or '無'),
           '%d since 2013, %d %s a year later; the misses: %s.' % (len(fl), len(good), 'higher' if on else 'lower', ', '.join('%s %s' % (yme(f['date']), pc(f['r52'], 0)) for f in bad) or 'none'))]

def hnupl(L):
    h = L['onchain']['hnupl']; s = LNS.get(h['stage'], (h['stage'], h['stage'])); r = h['r30']; b = h['base30']; bt = h['bottoms'][-1]
    sz = '長期持有者 NUPL %.3f，短期 %s：%s。' % (h['lth'], sg(h['sth'], 3), '新進場的人整體虧損' if h['sth'] < 0 else '新進場的人整體有獲利')
    se = 'Long-term holder NUPL is %.3f and short-term %s: %s.' % (h['lth'], sg(h['sth'], 3), 'recent buyers are underwater as a group' if h['sth'] < 0 else 'recent buyers are in profit as a group')
    pre = min(x['value'] for x in h['bottoms'][:-1])
    return sz, se, [
        it('長期持有者', 'Long-term holders', '%.3f' % h['lth'], '%.3f' % h['lth'], 'neu', '%s區；30 天前 %.3f。這輪底部 %s，前三輪都在 −0.3 以下。' % (s[0], h['lth30'], sg(bt['value'], 3)),
           '%s; %.3f thirty days ago. This cycle\'s bottom was %s, while the past three all fell below −0.3.' % (s[1], h['lth30'], sg(bt['value'], 3))),
        it('短期持有者', 'Short-term holders', sg(h['sth'], 3), sg(h['sth'], 3), 'down' if h['sth'] < 0 else 'up', '%s %s 0；30 天前 %s。' % (md(h['cross']['date']), '升上' if h['cross']['up'] else '跌破', sg(h['sth30'], 3)),
           '%s 0 on %s; %s thirty days ago.' % ('Rose above' if h['cross']['up'] else 'Fell below', mde(h['cross']['date']), sg(h['sth30'], 3))),
        it('由負轉正之後', 'After turning positive', '%d / %d' % (r['up'], r['n']), '%d / %d' % (r['up'], r['n']), 'neu', '短期持有者轉正後 30 天上漲的次數，中位數 %s（任一天 %d%%、%s）。' % (pc(r['med']), b['up'], pc(b['med'])),
           'Rises 30 days after short-term NUPL turned positive, median %s (any day: %d%%, %s).' % (pc(r['med']), b['up'], pc(b['med'])))]

def rup(L):
    r = L['onchain']['rup']; n = r['near']; op = next((e for e in r['eps'] if e.get('open')), None); dd = [w['dd180'] for w in n['waves'] if w.get('dd180') is not None]
    if r['zone'] == 'floor':
        sz = '相對未實現獲利 %.1f%%，在 %.0f%% 地板之下（第 %d 天）。' % (r['value'], r['floor'], op['days'] if op else 1); se = 'Relative unrealized profit is %.1f%%, under the %.0f%% floor (day %d).' % (r['value'], r['floor'], op['days'] if op else 1)
    elif r['value'] <= n['hi']:
        sz = '相對未實現獲利 %.1f%%，在近地板區（%.0f–%.1f%%）。' % (r['value'], r['floor'], n['hi']); se = 'Relative unrealized profit is %.1f%%, in the near-floor zone (%.0f–%.1f%%).' % (r['value'], r['floor'], n['hi'])
    else:
        sz = '相對未實現獲利 %.1f%%，離 %.0f%% 地板 %.1f 個百分點。' % (r['value'], r['floor'], r['gap']); se = 'Relative unrealized profit is %.1f%%, %.1f points above the %.0f%% floor.' % (r['value'], r['gap'], r['floor'])
    return sz, se, [
        it('現在', 'Now', pu(r['value']), pu(r['value']), 'neu', '30 天前 %s；一年最低 %s（%s）。' % (pu(r['d30']), pu(r['lo1y']['value']), md(r['lo1y']['date'])), '%s thirty days ago; the one-year low is %s (%s).' % (pu(r['d30']), pu(r['lo1y']['value']), mde(r['lo1y']['date']))),
        it('進近地板區一年後', 'A year after the near-floor zone', '%d%%' % n['s365']['up'], '%d%%' % n['s365']['up'], 'neu', '走完一年的 %d 天裡 %d%% 較高，中位數 %s（任一天 %d%%、%s）。' % (n['s365']['n'], n['s365']['up'], pc(n['s365']['med'], 0), n['b365']['up'], pc(n['b365']['med'], 0)),
           '%d%% of the %d days with a full year after were higher, median %s (any day: %d%%, %s).' % (n['s365']['up'], n['s365']['n'], pc(n['s365']['med'], 0), n['b365']['up'], pc(n['b365']['med'], 0))),
        it('但 90 天內', 'But within 90 days', '%d%%' % n['s90']['up'], '%d%%' % n['s90']['up'], 'neu', '90 天後上漲只有 %d%%；每一波進來後 180 天內都再跌過 %s 到 %s。' % (n['s90']['up'], pc(max(dd), 0), pc(min(dd), 0)),
           'Only %d%% higher 90 days on; every wave fell another %s to %s within 180 days.' % (n['s90']['up'], pc(max(dd), 0), pc(min(dd), 0)))]

def aviv(L):
    a = L['onchain']['aviv']; r = a['r365']; b = a['base365']
    sz = ('價格是真實市場均價的 %.3f 倍，連 %d 天低於 1：活躍投資人整體虧損。' if a['below'] else '價格是真實市場均價的 %.3f 倍，高於 1 已 %d 天：活躍投資人整體有獲利。') % (a['value'], a['run'])
    se = ('Price is %.3f times the true market mean, below 1 for %d days: active investors are underwater as a group.' if a['below'] else 'Price is %.3f times the true market mean, above 1 for %d days: active investors are in profit as a group.') % (a['value'], a['run'])
    return sz, se, [
        it('現在', 'Now', '%.3f' % a['value'], '%.3f' % a['value'], 'neu', '真實市場均價 %s；近 4 年第 %d 百分位。' % (usd(a['tmm']), round(a['pct4'])), 'True market mean %s; the %s percentile of four years.' % (usd(a['tmm']), ord_en(a['pct4']))),
        it('跌破 1 之後', 'After dropping below 1', '%d / %d' % (r['up'], r['n']), '%d / %d' % (r['up'], r['n']), 'neu', '低於 1 達 10 天以上的段落，一年後上漲的次數，中位數 %s（任一天 %d%%）。' % (pc(r['med']), b['up']),
           'Stretches of 10+ days below 1 that were higher a year later, median %s (any day: %d%%).' % (pc(r['med']), b['up'])),
        it('歷次底部', 'Past bottoms', '%.2f→%.2f' % (a['bottoms'][0]['value'], a['bottoms'][-1]['value']), '%.2f→%.2f' % (a['bottoms'][0]['value'], a['bottoms'][-1]['value']), 'neu',
           '底部一輪比一輪高：%s；熊市裡常長時間待在 1 以下。' % '、'.join('%.2f' % x['value'] for x in a['bottoms']), 'Each bottom higher than the last: %s. Bear markets often sit below 1 for a long time.' % ', '.join('%.2f' % x['value'] for x in a['bottoms']))]

def rrisk(L):
    r = L['onchain']['rrisk']; v = r['value'] * 1000; low = r['pct4'] <= 10; e = r['r365']
    sz = '儲備風險 %.2f‰，近 4 年第 %d 百分位%s。' % (v, round(r['pct4']), '，在低檔區第 %d 天' % r['run'] if low else ''); se = 'Reserve risk is %.2f‰, the %s percentile of four years%s.' % (v, ord_en(r['pct4']), ', day %d in the low zone' % r['run'] if low else '')
    return sz, se, [
        it('現在', 'Now', '%.2f‰' % v, '%.2f‰' % v, 'neu', '全部歷史第 %d 百分位；頂部從 %.1f‰ 降到 %.1f‰，所以用近 4 年比。' % (round(r['pct']), r['tops'][0]['value'] * 1000, r['tops'][-1]['value'] * 1000),
           'The %s percentile of all history; tops fell from %.1f‰ to %.1f‰, so it is ranked against four years.' % (ord_en(r['pct']), r['tops'][0]['value'] * 1000, r['tops'][-1]['value'] * 1000)),
        it('歷次底部', 'Past bottoms', ' / '.join('%d' % round(b['pct4']) for b in r['bp4']), ' / '.join('%d' % round(b['pct4']) for b in r['bp4']), 'neu',
           '各輪底部在當時近 4 年的百分位；%s 年底只到第 %d，單看會漏掉底部。' % (max(r['bp4'], key=lambda b: b['pct4'])['date'][:4], round(max(b['pct4'] for b in r['bp4']))),
           'Each bottom\'s four-year percentile at the time; %s only reached the %s, so this alone can miss a bottom.' % (max(r['bp4'], key=lambda b: b['pct4'])['date'][:4], ord_en(max(b['pct4'] for b in r['bp4'])))),
        it('進入低檔區之後', 'After entering the low zone', '%d / %d' % (e['up'], e['n']), '%d / %d' % (e['up'], e['n']), 'neu', '走完一年的 %d 段，一年後上漲的次數，中位數 %s；樣本少、結果不一。' % (e['n'], pc(e['med'])),
           'Of the %d stretches with a full year after, those higher a year on; median %s. Few samples, mixed results.' % (e['n'], pc(e['med'])))]

def pl(L):
    p = L['cycle']['powerlaw']; lo, hi = p['bottom_band']; a, b = p['next_top_ratio']; ta, tb = p['next_top_price']
    zone = ('落在歷次底部帶（%.2f–%.2f 倍）' % (lo, hi), 'inside the band of past bottoms (%.2f–%.2f×)' % (lo, hi)) if p['ratio'] <= hi else ('高於歷次底部帶', 'above the band of past bottoms')
    return '價格是冪律合理價的 %.2f 倍，%s。' % (p['ratio'], zone[0]), 'Price is %.2f times its power-law fair value, %s.' % (p['ratio'], zone[1]), [
        it('倍數', 'Multiple', '%.2f×' % p['ratio'], '%.2f×' % p['ratio'], 'neu', '合理價 %s，價格%s趨勢 %.0f%%。' % (usd(p['fair']), '低於' if p['ratio'] < 1 else '高於', abs(p['ratio'] - 1) * 100),
           'Fair value is %s; price is %.0f%% %s the trend.' % (usd(p['fair']), abs(p['ratio'] - 1) * 100, 'below' if p['ratio'] < 1 else 'above')),
        it('歷次頂部', 'Past tops', '→'.join('%.1f' % t[1] for t in p['tops']), '→'.join('%.1f' % t[1] for t in p['tops']), 'neu', '頂部倍數一輪比一輪小；底部在 %.2f–%.2f 倍之間。' % (lo, hi), 'Each top a smaller multiple than the last; bottoms sat between %.2f× and %.2f×.' % (lo, hi)),
        it('下一輪頂部', 'Next top', '%.2f–%.2f×' % (a, b), '%.2f–%.2f×' % (a, b), 'neu', '照縮小的速度推，約 %s–%s；樣本只有 4 輪。' % (usd(ta), usd(tb)), 'At the same rate of shrinkage, about %s–%s. Only four cycles to go on.' % (usd(ta), usd(tb)))]

def p6(L):
    p = L['cycle']['p6']; R = [('MVRV Z', 'MVRV Z', p['mvrv_z']), ('NUPL', 'NUPL', p['nupl']), ('Puell 倍數', 'Puell multiple', p['puell'])]; hot = sum(1 for r in R if r[2] >= 80)
    sz = '頂部三指標 %d 項到 80%s。' % (hot, '，已進入頂部區' if hot >= 2 else '；任兩項到 80 才算頂部區'); se = '%d of the top three indicators are at 80%s.' % (hot, ', so this is the top zone' if hot >= 2 else '; any two at 80 make a top zone')
    return sz, se, [it(z, e, '%d' % round(v), '%d' % round(v), 'warn' if v >= 80 else 'neu', '近 4 年第 %d 百分位%s。' % (round(v), '，已到 80' if v >= 80 else '，離 80 還差 %d' % round(80 - v)),
                       'The %s percentile of four years%s.' % (ord_en(v), ', at 80 or above' if v >= 80 else ', %d short of 80' % round(80 - v))) for z, e, v in R]

def p20(L):
    c = L['cycle']['cm']; v = c['mvrv_vs_prior']; up = (c['k075_price'] / L['price']['bar']['c'] - 1) * 100
    sz = 'MVRV 是前一輪高點的 %.2f 倍，%s 0.75 線。' % (v, '已站上' if v >= .75 else '還沒到'); se = 'MVRV is %.2f of the prior cycle\'s peak, %s the 0.75 line.' % (v, 'above' if v >= .75 else 'well short of')
    return sz, se, [
        it('現在', 'Now', '%.3f' % v, '%.3f' % v, 'neu', 'MVRV %.3f ÷ 前一輪高點 %.3f。' % (c['mvrv'], c['prior_cycle_peak']), 'MVRV %.3f ÷ the prior peak of %.3f.' % (c['mvrv'], c['prior_cycle_peak'])),
        it('0.75 線', 'The 0.75 line', usd(c['k075_price']), usd(c['k075_price']), 'neu', '價格約要到這裡（比收盤高 %.0f%%）；連 5 天站上才算觸發。' % up, 'Price would need to reach about here (%.0f%% above the close); it counts after five days above.' % up),
        it('0.80 線', 'The 0.80 line', usd(c['k080_price']), usd(c['k080_price']), 'neu', '比收盤高 %.0f%%。' % ((c['k080_price'] / L['price']['bar']['c'] - 1) * 100), '%.0f%% above the close.' % ((c['k080_price'] / L['price']['bar']['c'] - 1) * 100))]

def pi(L):
    v = L['price']['pi_cycle']
    sz = 'Pi Cycle %.2f，%s。' % (v, '已到 1，觸發頂部訊號' if v >= 1 else '離觸發（1）還遠' if v < .8 else '接近觸發（1）'); se = 'Pi Cycle is %.2f, %s.' % (v, 'at 1: the top signal has fired' if v >= 1 else 'far from the trigger at 1' if v < .8 else 'close to the trigger at 1')
    return sz, se, [it('Pi Cycle', 'Pi Cycle', '%.2f' % v, '%.2f' % v, 'warn' if v >= .9 else 'neu', '111 日均線是 350 日均線兩倍的 %.0f%%；到 1 才觸發，只看價格。' % (v * 100), 'The 111-day MA is %.0f%% of twice the 350-day MA; it fires at 1, and uses price alone.' % (v * 100))]

def tmh(L):
    t = L['cycle']['tidemark']; tp, bt = t['top'], t['bottom']; ct = t.get('cycle_test') or {}
    sz = '頂部訊號 %.0f、底部訊號 %.0f：%s。' % (tp['signal'], bt['signal'], '兩邊都還沒到 50' if max(tp['signal'], bt['signal']) < 50 else '底部訊號到了 50' if bt['signal'] >= 50 else '頂部訊號到了 50')
    se = 'Top signal %.0f, bottom signal %.0f: %s.' % (tp['signal'], bt['signal'], 'neither has reached 50' if max(tp['signal'], bt['signal']) < 50 else 'the bottom signal is at 50 or more' if bt['signal'] >= 50 else 'the top signal is at 50 or more')
    out = [it('頂部', 'Top', '%.0f' % tp['signal'], '%.0f' % tp['signal'], 'warn' if tp['signal'] >= 50 else 'neu', '熱度 %.0f、時間 %.0f；50 是頂部窗口、70 高度警戒。' % (tp['heat'], tp['timing']), 'Heat %.0f, timing %.0f; 50 opens the top window and 70 is high alert.' % (tp['heat'], tp['timing'])),
           it('底部', 'Bottom', '%.0f' % bt['signal'], '%.0f' % bt['signal'], 'neu', '冷度 %.0f、時間 %.0f；50 是底部區、70 強烈底部。' % (bt['cold'], bt['timing']), 'Cold %.0f, timing %.0f; 50 is the bottom zone and 70 a strong bottom.' % (bt['cold'], bt['timing']))]
    if ct.get('status') == 'testing':
        out.append(it('本輪低點', 'This cycle\'s low', '驗證中', 'Testing', 'neu', '到 %s 都沒跌破 %s（%s），就支持「這個低點是週期底部」。' % (ymd(ct['decisive_date']), usd(ct['low_price']), md(ct['low_date'])),
                      'If %s (%s) holds through %s, that supports this low being the cycle bottom.' % (usd(ct['low_price']), mde(ct['low_date']), ymde(ct['decisive_date']))))
    return sz, se, out

def lthloss(L):
    x = L['onchain']['lthloss']; pk = x['peaks'][-1]; pm = x.get('post_min'); co = x.get('cohort') or {}; prev = x['peaks'][:-1]
    sz = '長期持有者 %.1f%% 在虧損%s。' % (x['value'], '；跌破約 %s 就超過這輪高點' % usd(co['break_price']) if co.get('break_price') else '')
    se = '%.1f%% of long-term holder coins are underwater%s.' % (x['value'], '; below about %s it would top this cycle\'s peak of %.1f%%' % (usd(co['break_price']), pk['value']) if co.get('break_price') else '')
    out = [it('現在', 'Now', pu(x['value']), pu(x['value']), 'neu', '這輪高點 %s（%s）%s。' % (pu(pk['value']), md(pk['date']), '，之後最低 %s（%s）' % (pu(pm['value']), md(pm['date'])) if pm else ''),
              'This cycle\'s peak was %s (%s)%s.' % (pu(pk['value']), mde(pk['date']), ', and the low since %s (%s)' % (pu(pm['value']), mde(pm['date'])) if pm else ''))]
    if co.get('break_price'):
        out.append(it('分界', 'The line', '≈ %s' % usd(co['break_price']), '≈ %s' % usd(co['break_price']), 'neu', '照現在的籌碼推算，跌到這裡會打破「脫離底部後不再創新高」；每天重算。',
                      'From today\'s coin distribution; below here would break the pattern of no new high after the bottom. Recomputed daily.'))
    out.append(it('前幾輪', 'Past cycles', '/'.join('%.0f%%' % p['value'] for p in prev), '/'.join('%.0f%%' % p['value'] for p in prev), 'neu', '熊市底部的高點；脫離底部後最高只到 %s，都沒再創新高。' % '、'.join('%.0f%%' % p['after_max']['value'] for p in prev if p.get('after_max')),
                  'Peaks at past bear bottoms; afterwards they only reached %s, never a new high.' % ', '.join('%.0f%%' % p['after_max']['value'] for p in prev if p.get('after_max'))))
    return sz, se, out

def npl365(L):
    n = L['onchain']['npl365']; v = n['value'] * 1000; v30 = n['v30'] * 1000; pb = [b['value'] * 1000 for b in n['bottoms'] if not b['now']]; tp = [t['value'] * 1000 for t in n['tops']]
    deeper = v < v30
    sz = '近一年淨實現損益 %s：整體在%s，%s。' % (wan(v), '認賠' if v < 0 else '獲利了結', '還在加深' if (deeper and v < 0) or (not deeper and v > 0) else '比 30 天前收斂')
    se = 'Net realized profit and loss over a year is %s: holders are %s on balance, %s.' % (kb(v), 'taking losses' if v < 0 else 'taking profit', 'and it is still deepening' if (deeper and v < 0) or (not deeper and v > 0) else 'though less than 30 days ago')
    out = [it('近一年', 'Past year', wan(v), kb(v), 'down' if v < 0 else 'up', '%s30 天前 %s。' % ('%s 起轉負；' % md(n['neg_since']) if n.get('neg_since') and v < 0 else '', wan(v30)), '%s%s thirty days ago.' % ('Negative since %s; ' % mde(n['neg_since']) if n.get('neg_since') and v < 0 else '', kb(v30)))]
    if v < 0:
        out.append(it('和熊市底部比', 'Against past bear bottoms', '%d%%' % round(v / pb[-1] * 100), '%d%%' % round(v / pb[-1] * 100), 'neu', '約上一輪的 %d%%；前三輪最深 %s。' % (round(v / pb[-1] * 100), wl(pb)),
                      'About %d%% of the last cycle; the past three bottomed at %s.' % (round(v / pb[-1] * 100), ml(pb))))
    out.append(it('頂部前後', 'Around tops', wan(tp[-1]), kb(tp[-1]), 'neu', '頂部前後半年的最高：%s，最近一輪最少。' % wl(tp), 'The highest within six months of each top: %s; the latest was the smallest.' % ml(tp)))
    return sz, se, out

def agecost(L):
    a = L['cycle']['age_cost']; c = a['c36']; lc = a['last_cross']; px = a['price']
    dc = [x['days_to_next'] for x in a['crosses'] if x['kind'] == lc['kind'] and x.get('days_to_next')]
    sz = '3–6 個月成本 %s，收盤%s；更早買的兩批%s。' % (usd(c['cost']), '高 %.1f%%' % c['gap_pct'] if c['above'] else '低 %.1f%%' % abs(c['gap_pct']), '都還在虧損' if px < min(a['c612'], a['c1218']) else '有獲利' if px > max(a['c612'], a['c1218']) else '一賺一賠')
    se = 'The 3–6 month cost is %s, with the close %.1f%% %s it; the 6–12 and 12–18 month groups are %s.' % (usd(c['cost']), abs(c['gap_pct']), 'above' if c['above'] else 'below', 'both still underwater' if px < min(a['c612'], a['c1218']) else 'both in profit' if px > max(a['c612'], a['c1218']) else 'split')
    return sz, se, [
        it('3–6 個月', '3–6 months', usd(c['cost']), usd(c['cost']), 'up' if c['above'] else 'down', '收盤%s，%s 起 %d 天；30 天%s %s。' % ('在上方' if c['above'] else '在下方', md(c['since']['date']), c['since']['days'], '下降' if c['chg30'] < 0 else '上升', usd(abs(c['chg30']))),
           'The close has been %s it since %s, %d days; it %s %s in 30 days.' % ('above' if c['above'] else 'below', mde(c['since']['date']), c['since']['days'], 'fell' if c['chg30'] < 0 else 'rose', usd(abs(c['chg30'])))),
        it('兩條長線', 'The two longer lines', '%s / %s' % (kusd(a['c612']), kusd(a['c1218'])), '%s / %s' % (kusd(a['c612']), kusd(a['c1218'])), 'neu',
           '6–12 個月比 12–18 個月%s %.1f%%；%s %s叉，至今 %d 天。' % ('低' if a['gap_pct'] < 0 else '高', abs(a['gap_pct']), md(lc['date']), '死' if lc['kind'] == 'death' else '金', a['days_since']),
           '6–12 months is %.1f%% %s 12–18 months; a %s cross on %s, %d days ago.' % (abs(a['gap_pct']), 'below' if a['gap_pct'] < 0 else 'above', lc['kind'], mde(lc['date']), a['days_since'])),
        it('過去%s叉到%s叉' % (('死', '金') if lc['kind'] == 'death' else ('金', '死')), 'Past %s to %s crosses' % ((('death', 'golden') if lc['kind'] == 'death' else ('golden', 'death'))), '%d–%d 天' % (min(dc), max(dc)), '%d–%d days' % (min(dc), max(dc)), 'neu',
           '這兩條是半年到一年半前的買價，比價格落後很多。', 'Both lines are what people paid six to eighteen months ago, so they lag price a long way.')]

def hashr_bv(L, hb):   # 2026-11-19 Hash Ribbons 改成圖（bv_more.py 第 7 項）：讀值照回測，用 Bitview 的算力，和圖同一份
    SG_ = lambda v: ('+%d%%' % v) if v >= 0 else ('−%d%%' % -v)
    YMD = lambda d_: d_.replace('-', '/'); bys = hb['buys']; pre, post, bp = hb['pre'], hb['post'], hb['base_post']
    yr0 = L['meta']['bar_date'][:4]; ty = [b for b in bys if b['d'][:4] == yr0]; lb = bys[-1] if bys else None
    items = [
        it('現在', 'Now', '投降中' if hb['cap'] else '沒有投降', 'Capitulating' if hb['cap'] else 'No capitulation', 'neu',
         '30 日均算力 %s EH/s，60 日均 %s EH/s，比值 %.3f，這個狀態已經 %d 天。%s' % (format(hb['m30'], ',.0f'), format(hb['m60'], ',.0f'), hb['ratio'], hb['run'], ('上一次原版買點是 %s（收盤 $%s）。' % (YMD(lb['d']), format(lb['px'], ','))) if lb else ''),
         'The 30-day average hashrate is %s EH/s against %s EH/s for the 60-day, a ratio of %.3f, %d days in this state. %s' % (format(hb['m30'], ',.0f'), format(hb['m60'], ',.0f'), hb['ratio'], hb['run'], ('The last original buy was on %s (close $%s).' % (lb['d'], format(lb['px'], ','))) if lb else '')),
        it('2021 年以前', 'Before 2021', '%d 次裡 %d 次漲' % (pre['n'], pre['up']), '%d of %d up' % (pre['up'], pre['n']), 'neu',
         '原版買點一年後的漲跌：%s。' % '、'.join('%s %s' % (b['d'][:7].replace('-', '/'), SG_(b['r365'])) for b in bys if b['d'] < '2021' and b['r365'] is not None),
         'A year after each original buy: %s.' % ', '.join('%s %s' % (b['d'][:7], SG_(b['r365'])) for b in bys if b['d'] < '2021' and b['r365'] is not None)),
        it('2021 年以後', 'Since 2021', '%d 次裡 %d 次漲' % (post['n'], post['up']), '%d of %d up' % (post['up'], post['n']), 'neu',
         '滿一年的：%s，中位數 %s。同期隨便一天買進，一年後漲的機率 %d%%、中位數 %s。' % ('、'.join('%s %s' % (b['d'][:7].replace('-', '/'), SG_(b['r365'])) for b in bys if b['d'] >= '2021' and b['r365'] is not None), SG_(post['med']), bp['up'], SG_(bp['med'])),
         'With a full year: %s; median %s. Buying on any day in that span was up a year later %d%% of the time, median %s.' % (', '.join('%s %s' % (b['d'][:7], SG_(b['r365'])) for b in bys if b['d'] >= '2021' and b['r365'] is not None), SG_(post['med']), bp['up'], SG_(bp['med']))),
        it('%s 年' % yr0, 'In %s' % yr0, '%d 次買點' % len(ty), '%d buys' % len(ty), 'neu',
         '今年投降、恢復來回好幾次：%s（括號是到現在最近一個滿 90／180 天的漲跌）。' % '、'.join('%s（%s）' % (YMD(b['d'])[5:], SG_(b['r180']) + '／180 天' if b['r180'] is not None else SG_(b['r90']) + '／90 天' if b['r90'] is not None else '還不到 90 天') for b in ty),
         'Capitulation came and went several times this year: %s (in brackets, the latest 90- or 180-day result so far).' % ', '.join('%s (%s)' % (b['d'][5:], SG_(b['r180']) + ' at 180d' if b['r180'] is not None else SG_(b['r90']) + ' at 90d' if b['r90'] is not None else 'under 90 days') for b in ty))]
    sz = '%s；原版買點 2021 年以後一年後 %d 次裡 %d 次漲，和隨便一天差不多。' % ('礦工在投降' if hb['cap'] else '30 日均算力在 60 日均上面，沒有投降', post['n'], post['up'])
    se = '%s; since 2021 the original buy was up a year later %d times out of %d, about the same as any day.' % ('Miners are capitulating' if hb['cap'] else 'The 30-day hashrate is above the 60-day: no capitulation', post['up'], post['n'])
    return sz, se, items
def hashr(L):
    hb = (L['onchain'].get('bvx') or {}).get('hrib')
    if hb: return hashr_bv(L, hb)
    h = L['onchain']['hash_ribbons']; g = (h['ratio'] - 1) * 100
    sz = ('30 日均算力比 60 日均%s %.1f%%，已 %d 天：%s。' % ('高' if g >= 0 else '低', abs(g), h['state_days'], '礦工在投降' if h['capitulation'] else '礦工沒有投降'))
    se = 'The 30-day average hashrate is %.1f%% %s the 60-day, for %d days: %s.' % (abs(g), 'above' if g >= 0 else 'below', h['state_days'], 'miners are capitulating' if h['capitulation'] else 'no miner capitulation')
    return sz, se, [it('算力帶', 'Ribbon ratio', '%.3f' % h['ratio'], '%.3f' % h['ratio'], 'down' if h['capitulation'] else 'neu', '上次%s在 %s；近 90 天最低 %.3f。' % ('進入投降' if h['capitulation'] else '從投降恢復', md(h['last_cross']), h['min_ratio_90d']),
                       'Last %s on %s; the 90-day low is %.3f.' % ('entered capitulation' if h['capitulation'] else 'recovered from capitulation', mde(h['last_cross']), h['min_ratio_90d']))]

def cyccmp(L):
    c = L['cycle']['cycle_cmp']; cur = next(x for x in c['cycles'] if x['now']); prev = [x for x in c['cycles'] if not x['now']]; bk = [x['back_day'] for x in prev if x.get('back_day')]
    sz = '頂部後第 %d 天 %s，前幾輪同一天都在 %s 以下。' % (c['day_now'], pc(cur['at']['pct']), pc(max(x['at']['pct'] for x in prev), 0)); se = 'Day %d after the top: %s. Past cycles were all below %s on the same day.' % (c['day_now'], pc(cur['at']['pct']), pc(max(x['at']['pct'] for x in prev), 0))
    return sz, se, [
        it('第 %d 天' % c['day_now'], 'Day %d' % c['day_now'], pc(cur['at']['pct']), pc(cur['at']['pct']), 'neu', '頂部 %s %s；前幾輪同一天 %s。' % (ymd(cur['top']), usd(cur['top_price']), '、'.join(pc(x['at']['pct'], 0) for x in prev)),
           'Top on %s at %s; past cycles on this day: %s.' % (ymde(cur['top']), usd(cur['top_price']), ', '.join(pc(x['at']['pct'], 0) for x in prev))),
        it('最低點', 'Low', pc(cur['low']['pct']), pc(cur['low']['pct']), 'neu', '第 %d 天（%s）；前幾輪 %s，第 %d–%d 天。' % (cur['low']['day'], ym(cur['low']['date']), '、'.join(pc(x['low']['pct']) for x in prev), min(x['low']['day'] for x in prev), max(x['low']['day'] for x in prev)),
           'Day %d (%s); past cycles %s, on days %d–%d.' % (cur['low']['day'], ymde(cur['low']['date']), ', '.join(pc(x['low']['pct']) for x in prev), min(x['low']['day'] for x in prev), max(x['low']['day'] for x in prev))),
        it('回到頂部價', 'Back to the top', '%s–%s 天' % (n0(min(bk)), n0(max(bk))), '%s–%s days' % (n0(min(bk)), n0(max(bk))), 'neu', '前幾輪重回頂部價花的天數；這輪跌得淺得多，不一定照走。', 'How long past cycles took to reclaim the top; this drawdown is far shallower, so the timing may not carry over.')]

def capeff(L):
    c = L['onchain']['capeff']; cy = c['cycles']; cu = c['cur']; sm = [x['same'] for x in cy]
    sz = '這一輪 %d 天：流入 %s、價格 %.2f 倍。' % (cu['days'], yiz(cu['add_b']), cu['mult']); se = '%d days into this cycle: %s in and %.2f times the price.' % (cu['days'], bbs(cu['add_b']), cu['mult'])
    mm = lambda m: ('%.0f' % m) if m >= 20 else ('%.1f' % m)
    return sz, se, [
        it('一輪比一輪', 'Cycle by cycle', '%s×' % mm(cy[-1]['mult']), '%s×' % mm(cy[-1]['mult']), 'neu', '底到頂的價格倍數 %s 倍，流入卻一輪比一輪多。' % '→'.join(mm(x['mult']) for x in cy), 'Bottom-to-top multiples of %s×, while the money in grew every cycle.' % '→'.join(mm(x['mult']) for x in cy)),
        it('前幾輪同一天', 'Past cycles at this point', '%.2f–%.2f×' % (min(s['mult'] for s in sm), max(s['mult'] for s in sm)), '%.2f–%.2f×' % (min(s['mult'] for s in sm), max(s['mult'] for s in sm)), 'neu',
           '流入 %s 到 %s；這輪流入較多、漲得較少。' % (yiz(max(s['add_b'] for s in sm)) if max(s['add_b'] for s in sm) else '0', yiz(min(s['add_b'] for s in sm))) if cu['add_b'] > max(s['add_b'] for s in sm) and cu['mult'] < min(s['mult'] for s in sm) else '流入 %s 到 %s。' % (yiz(max(s['add_b'] for s in sm)), yiz(min(s['add_b'] for s in sm))),
           ('Flows of %s to %s; this cycle has taken in more and risen less.' if cu['add_b'] > max(s['add_b'] for s in sm) and cu['mult'] < min(s['mult'] for s in sm) else 'Flows of %s to %s.') % (bbs(max(s['add_b'] for s in sm)), bbs(min(s['add_b'] for s in sm)))),
        it('每 1 美元', 'Per $1 in', '$%.1f' % cy[-1]['lev'], '$%.1f' % cy[-1]['lev'], 'neu', '到頂部時每流入 1 美元，市值增加 %s。' % '→'.join('$%.1f' % x['lev'] for x in cy), 'At each top, every $1 in added %s of market cap.' % ' → '.join('$%.1f' % x['lev'] for x in cy))]

PN = {'直接修復': 'direct recovery', '淺回檔': 'shallow pullback', '基準雙底': 'base-case double bottom', '延後新低': 'delayed new low'}
def path(L):
    m = L['cycle']['model']; w = m['weights']; t = m['top_model']; top = max(w, key=w.get); lo, hi = min(w.values()), max(w.values())
    sz = '四種走法權重 %d–%d%%%s；頂部模型中位 %s。' % (lo, hi, '，差不多' if hi - lo <= 10 else '，%s最高' % top, usd(t['median'])); se = 'The four paths are weighted %d–%d%%%s; the top model\'s median is %s.' % (lo, hi, ', close to even' if hi - lo <= 10 else ', %s highest' % PN.get(top, top), usd(t['median']))
    rv = (m.get('reviews') or [{}])[-1]
    return sz, se, [
        it('權重', 'Weights', '/'.join('%d' % v for v in w.values()), '/'.join('%d' % v for v in w.values()), 'neu', '、'.join('%s %d%%' % (k, v) for k, v in w.items()) + '。', ', '.join('%s %d%%' % (PN.get(k, k).capitalize() if i == 0 else PN.get(k, k), v) for i, (k, v) in enumerate(w.items())) + '.'),
        it('頂部模型', 'Top model', usd(t['median']), usd(t['median']), 'neu', '80%% 區間 %s–%s，時間 %s。' % (usd(t['p10']), usd(t['p90']), t['timing']), '80%% range %s–%s, timed for %s.' % (usd(t['p10']), usd(t['p90']), t.get('timing_en') or t['timing'])),
        it('下次檢討', 'Next review', md(m['next_review']), mde(m['next_review']), 'neu', '每月底依收盤重新加權%s。' % ('；%s 收 %s' % (md(rv['close_date']), usd(rv['close'])) if rv.get('close') else ''),
           'Re-weighted on each month-end close%s.' % ('; %s closed at %s' % (mde(rv['close_date']), usd(rv['close'])) if rv.get('close') else ''))]

def long(L):
    cy = L['cycle']; tp = cy['tops'][-1]; hv = cy['halvings']; d = L['price']['monthly']['date']; px = L['price']['bar']['c']; hd = days(hv[-1], d)
    lag = [days(next(h for h in reversed(hv) if h < t[0]), t[0]) for t in cy['tops']]
    sz = '收盤比上一輪頂部低 %.1f%%；距上次減半 %s 天。' % (abs(px / tp[1] - 1) * 100, n0(hd)); se = 'The close is %.1f%% below the last cycle top; %s days since the last halving.' % (abs(px / tp[1] - 1) * 100, n0(hd))
    return sz, se, [
        it('上一輪頂部', 'Last cycle top', usd(tp[1]), usd(tp[1]), 'neu', '%s，減半後 %d 天；前幾輪頂部在減半後 %d–%d 天。' % (ymd(tp[0]), lag[-1], min(lag[:-1]), max(lag[:-1])), '%s, %d days after the halving; earlier tops came %d–%d days after.' % (ymde(tp[0]), lag[-1], min(lag[:-1]), max(lag[:-1]))),
        it('減半', 'Halving', '%s 天' % n0(hd), '%s days' % n0(hd), 'neu', '上次 %s；下一次估計 %s。' % (ymd(hv[-1]), ym(cy['next_halving_est'])), 'Last on %s; the next is estimated for %s.' % (ymde(hv[-1]), yme(cy['next_halving_est'])))]

def mon(L):
    m = L['price']['monthly']; c = m['cur']; mo = int(m['month'][5:7]); nm = '%d 月' % mo; ne = MONF[mo - 1]
    sz = '%s至今 %s；過去 %d 年有 %d 年上漲，中位數 %s。' % (nm, pc(m['mtd']), c['n'], c['up'], pc(c['med'])); se = '%s so far: %s; in %d past %ss it rose %d times, median %s.' % (ne, pc(m['mtd']), c['n'], ne, c['up'], pc(c['med']))
    return sz, se, [
        it('這個月', 'This month', pc(m['mtd']), pc(m['mtd']), 'up' if m['mtd'] > 0 else 'down', '從上月底 %s 到 %s；今年至今 %s，月底前還會變。' % (usd(m['base']), md(m['date']), pc(m['ytd'])), 'From last month\'s close of %s to %s; %s year to date. It can still change before month-end.' % (usd(m['base']), mde(m['date']), pc(m['ytd']))),
        it('過去的 %s' % nm, 'Past %ss' % ne, '%d / %d' % (c['up'], c['n']), '%d / %d' % (c['up'], c['n']), 'neu', '最好 %d 年 %s，最差 %d 年 %s；只描述過去。' % (c['best_y'], pc(c['best'], 0), c['worst_y'], pc(c['worst'], 0)), 'Best %d at %s, worst %d at %s. It describes the past only.' % (c['best_y'], pc(c['best'], 0), c['worst_y'], pc(c['worst'], 0)))]

CARDS = dict(dawn=dawn, stage=stage, regime=regime, hnupl=hnupl, rup=rup, aviv=aviv, rrisk=rrisk, pl=pl, p6=p6, p20=p20, pi=pi, tmh=tmh, lthloss=lthloss, npl365=npl365, agecost=agecost, hashr=hashr, cyccmp=cyccmp, capeff=capeff, path=path, long=long, mon=mon)
# 舊版沒有「怎麼讀」的卡片，這裡補上（中、英各三行內）
HOWX = {
    'stage': (['熊市 → 轉換期 → 牛市，只看價格和 200 日均線，加上投降有沒有出現過。', '牛市一旦成立就鎖定，要在下降的均線下待滿 30 天才退回熊市。', '佐證燈只顯示，不參與判定；這是標籤，不是買賣訊號。'],
              ['Bear → transition → bull, judged only by price against the 200-day MA and whether a capitulation has happened.', 'Once bull, it is locked until price spends 30 days under a falling average.', 'The supporting lights are for reference and do not decide the stage. It is a label, not a trade signal.']),
    'rup': (['未實現獲利 ÷ 市值：還沒賣的幣整體賺了市值的百分之幾。', '35% 是歷次熊市底部附近的地板，35–37.5% 是近地板區。', '近地板區之後一年多半較高，但進來後幾個月內常再跌一段。'],
            ['Unrealized profit ÷ market cap: how much of the market cap is paper profit.', '35% has been the floor near past bear bottoms; 35–37.5% is the near-floor zone.', 'A year after the near-floor zone was usually higher, but price often fell further in the months after entering it.']),
    'p6': (['三個估值指標各自和過去四年比的百分位，80 以上算熱。', '任兩個到 80 以上才算進入頂部區。', '只看估值，不看時間；只作讀值。'],
           ['Three valuation indicators, each ranked against the past four years; 80 or above is hot.', 'Any two at 80 or above count as the top zone.', 'Valuation only, not timing. Reading only.']),
    'pi': (['111 日均線 ÷（350 日均線 × 2）；到 1 代表短期均線追上長期均線的兩倍。', '過去幾次到 1 都在頂部附近，但每一輪的頂部不一定都會碰到。', '只用價格，和鏈上指標一起看。'],
           ['111-day MA ÷ (350-day MA × 2); 1 means the short average has caught up with twice the long one.', 'Past touches of 1 came near tops, but not every top has reached it.', 'It uses price alone; read it with the on-chain gauges.']),
    'hashr': (['算力 30 日均 ÷ 60 日均；低於 1 代表算力在下降，礦工在投降。', '原版買點（投降結束後價格轉強）2021 年以前很準，2021 年以後和隨便一天差不多。', '只看礦工，和其他指標一起看。'],
              ['30-day ÷ 60-day average hashrate; below 1 means hashrate is falling and miners are capitulating.', 'The original buy (price turning up after capitulation) worked well before 2021; since then it has done about as well as any day.', 'It only covers miners; read it with the rest.']),
    'cyccmp': (['每條線是一輪頂部之後每天的收盤，和那一輪頂部比跌了多少。', '橫軸是頂部後第幾天，可以直接和前幾輪同一天比。', '只有三輪樣本，這輪的走法不一定一樣。'],
               ['Each line is the daily close after a cycle top, as a drop from that top.', 'The x-axis is days since the top, so today lines up with the same day in past cycles.', 'Only three past cycles; this one need not follow them.']),
}
