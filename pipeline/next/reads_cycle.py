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

def pl(L):   # 2026-11-25 改寫：使用者「不要把讀者都想的那麼專業」「給出可以指導交易的觀點」——先講冪律是什麼、0% 和倍數代表什麼，再講歷史上之後怎麼走
    import math, pl_bt
    p = L['cycle']['powerlaw']; lo, hi = p['bottom_band']; a, b = p['next_top_ratio']; ta, tb = p['next_top_price']; q = pl_bt.bt(L)
    g0 = dt.date(2009, 1, 3); lx = lambda d: math.log10((dt.date.fromisoformat(d) - g0).days)   # 底線：和 cycle_data.py 冪律圖同一條（歷次底部倍數對 log10(創世起天數) 直線擬合）
    xs = [lx(t[0]) for t in p['bottoms']]; ys = [math.log10(t[1]) for t in p['bottoms']]; mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    bs_ = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs); blp = p['fair'] * 10 ** (my + bs_ * (lx(p['date']) - mx))
    r = p['ratio']; px = L['price']['bar']['c']; under = px < blp   # 顯示用全站統一收盤
    if r <= hi:
        sz = '比特幣跌到長期趨勢價的 %.2f 倍%s：照這張圖，這是長期的底部區間，但底部區間裡還可能再跌一段，也可能待很久。' % (r, '，比歷次熊底連成的底線還低' if under else '，落在歷次熊底的範圍')
        se = 'Bitcoin is down to %.2f× its long-run trend price%s: on this chart that is long-run bottom territory, though price can fall further inside it and stay there a long time.' % (r, ', below the line through past bear bottoms' if under else ', inside the range of past bear bottoms')
    elif r >= a:
        sz = '比特幣到了長期趨勢價的 %.2f 倍，進入推估的下一輪頂部區：照這張圖，這是長期的頂部區間。' % r
        se = 'Bitcoin is at %.2f× its long-run trend price, inside the projected zone for the next top: on this chart that is long-run top territory.' % r
    else:
        sz = '比特幣在長期趨勢價的 %.2f 倍，不在歷次熊底的便宜區，也還沒到頂部區：照這張圖，長期位置在中間。' % r
        se = 'Bitcoin is at %.2f× its long-run trend price, neither in past bear-bottom territory nor near a top: on this chart the long-run position is mid-range.' % r
    pos = ('「通道位置」顯示 0%%，意思是價格已經跌破歷次熊底連成的底線（今天約 %s），比那條線還低 %.0f%%。' % (usd(blp), (1 - px / blp) * 100)) if under else \
          ('歷次熊底連成的底線今天約 %s，價格高出它 %.0f%%。' % (usd(blp), (px / blp - 1) * 100))
    pose = ('"Place in the channel" reads 0%% because price has fallen through the line joining past bear bottoms (about %s today), %.0f%% below it.' % (usd(blp), (1 - px / blp) * 100)) if under else \
           ('The line through past bear bottoms is about %s today; price is %.0f%% above it.' % (usd(blp), (px / blp - 1) * 100))
    cz = ('這一輪 %s 就跌進這區，到現在價格%s：便宜可以維持很久。' % (ym(str(dt.date(1970, 1, 1) + dt.timedelta(q['cur']))), '還在原地' if abs(q['cur_chg']) < 5 else '又%s %d%%' % ('漲了' if q['cur_chg'] > 0 else '跌了', abs(q['cur_chg'])))) if q and q['cur'] else ''
    ce = (' This cycle entered the zone in %s and price is %s since: cheap can stay cheap for a long time.' % (yme(str(dt.date(1970, 1, 1) + dt.timedelta(q['cur']))), 'about where it was' if abs(q['cur_chg']) < 5 else '%s %d%%' % ('up' if q['cur_chg'] > 0 else 'down', abs(q['cur_chg'])))) if q and q['cur'] else ''
    return sz, se, [
        it('現在有多便宜', 'How cheap', '%.2f×' % r, '%.2f×' % r, 'up' if r <= hi else 'neu',
           '照過去 15 年的成長速度，比特幣今天的趨勢價約 %s，現在 %s，是它的 %.0f%%。2012 年以來只有 %d%% 的日子比現在便宜。%s' % (usd(p['fair']), usd(px), r * 100, q['cheaper'] if q else 0, pos),
           'At its past 15-year growth pace, Bitcoin\'s trend price today is about %s; at %s it trades at %.0f%% of that. Only %d%% of days since 2012 were cheaper. %s' % (usd(p['fair']), usd(px), r * 100, q['cheaper'] if q else 0, pose)),
        it('跌到這裡之後', 'What came next', '%d 次一年後都漲' % q['eps'] if q and q['up'] == q['n'] else '—', 'Up a year on, %d of %d' % (q['eps'], q['eps']) if q and q['up'] == q['n'] else '—', 'neu',
           ('過去倍數跌到 %.2f 以下有 %d 次（%s 年）。那段期間的任何一天，一年後的價格都%s，中位數 %+d%%；但之後一年內最多還會再跌 %d%%（一半的時候只再跌 %d%% 以內）。%s只有 %d 次，不保證這次一樣。' % (
               q['th'], q['eps'], '、'.join(str(y) for y in q['years']), '比當時高' if q['up'] == q['n'] else '多半比當時高', q['med'], abs(q['worst']), abs(q['dmed']), cz, q['eps'])) if q else '',
           ('The multiple has fallen below %.2f %d times before (%s). From any of those days, price was %s a year later, median %+d%%, but it fell as much as another %d%% within that year (half the time no more than %d%%).%s Only %d episodes, so no guarantee.' % (
               q['th'], q['eps'], ', '.join(str(y) for y in q['years']), 'higher' if q['up'] == q['n'] else 'mostly higher', q['med'], abs(q['worst']), abs(q['dmed']), ce, q['eps'])) if q else ''),
        it('頂部一輪比一輪低', 'Each top is lower', '下一輪 %.2f–%.2f×' % (a, b), 'Next %.2f–%.2f×' % (a, b), 'neu',
           '每輪牛市頂部是當時趨勢價的幾倍：%s，一輪比一輪小。比特幣越大，漲幅越溫和；照這個速度，下一輪頂部大約只到趨勢價的 %.2f–%.2f 倍。趨勢價自己會繼續往上（2029 年 10 月約 %s），換算約 %s–%s。別拿以前「一輪漲十倍」的經驗來期待。' % ('、'.join('%s 年 %.1f 倍' % (t[0][:4], t[1]) for t in p['tops']), a, b, usd(p['fair_2029_10']), usd(ta), usd(tb)),
           'Each bull top as a multiple of the trend at the time: %s, smaller every time. The bigger Bitcoin gets, the milder its runs; at that pace the next top reaches only about %.2f–%.2f× of trend. The trend itself keeps rising (about %s by October 2029), so that is roughly %s–%s. Don\'t expect the tenfold runs of the past.' % (', '.join('%.1f× in %s' % (t[1], t[0][:4]) for t in p['tops']), a, b, usd(p['fair_2029_10']), usd(ta), usd(tb)))]

def p6(L):
    p = L['cycle']['p6']; R = [('MVRV Z', 'MVRV Z', p['mvrv_z']), ('NUPL', 'NUPL', p['nupl']), ('Puell 倍數', 'Puell multiple', p['puell'])]; hot = sum(1 for r in R if r[2] >= 80)
    sz = '頂部三指標 %d 項到 80%s。' % (hot, '，已進入頂部區' if hot >= 2 else '；任兩項到 80 才算頂部區'); se = '%d of the top three indicators are at 80%s.' % (hot, ', so this is the top zone' if hot >= 2 else '; any two at 80 make a top zone')
    return sz, se, [it(z, e, '%d' % round(v), '%d' % round(v), 'warn' if v >= 80 else 'neu', '近 4 年第 %d 百分位%s。' % (round(v), '，已到 80' if v >= 80 else '，離 80 還差 %d' % round(80 - v)),
                       'The %s percentile of four years%s.' % (ord_en(v), ', at 80 or above' if v >= 80 else ', %d short of 80' % round(80 - v))) for z, e, v in R]

def p20tops(L):   # 這張圖 2021 年起才有：2021、2025 兩次頂部前比值的最高（leans.py 也用）
    rs = [r for r in (L['cycle'].get('p20') or {}).get('rows') or [] if r[1] is not None]; e = lambda d: (dt.date.fromisoformat(d) - dt.date(1970, 1, 1)).days
    a = [r[1] for r in rs if r[0] < e('2022-01-01')]; b = [r[1] for r in rs if e('2024-01-01') <= r[0] < e('2026-01-01')]
    return [max(a), max(b)] if a and b else []

def p20(L):   # 2026-11-25 改寫（WRITING.md）：先講 MVRV 是什麼、比值代表離前一輪頂部的熱度多遠；0.75 是警戒線，不寫交易用語
    c = L['cycle']['cm']; v = c['mvrv_vs_prior']; px = L['price']['bar']['c']; up = (c['k075_price'] / px - 1) * 100; tk = p20tops(L)
    if v >= .75:
        sz = '市場的熱度（MVRV）到了前一輪頂部時的 %.0f%%，站上警戒線：照這張圖，已經接近前一輪頂部的熱度。' % (v * 100)
        se = 'Market heat (MVRV) is at %.0f%% of the last top\'s, above the warning line: on this chart it is close to last cycle\'s peak heat.' % (v * 100)
    elif v >= .65:
        sz = '市場的熱度（MVRV）到了前一輪頂部時的 %.0f%%：照這張圖，開始接近頂部的熱度，價格再漲 %.0f%% 就碰到警戒線。' % (v * 100, up)
        se = 'Market heat (MVRV) is at %.0f%% of the last top\'s: on this chart it is getting close, and another %.0f%% rise would reach the warning line.' % (v * 100, up)
    else:
        sz = '市場的熱度（MVRV）只有前一輪頂部時的 %.0f%%：照這張圖，離頂部還很遠，價格要再漲 %.0f%% 才會碰到警戒線。' % (v * 100, up)
        se = 'Market heat (MVRV) is only %.0f%% of the last top\'s: on this chart a top is far off, and price would need to rise another %.0f%% to reach the warning line.' % (v * 100, up)
    out = [
        it('現在有多熱', 'How hot now', '%.2f' % v, '%.2f' % v, 'warn' if v >= .75 else 'neu',
           '現在價格是所有幣平均成本的 %.2f 倍（這就是 MVRV），前一輪頂部時是 %.2f 倍；兩個相除，1 就是和那時一樣熱。' % (c['mvrv'], c['prior_cycle_peak']),
           'Price is now %.2f× the average cost of all coins (that is MVRV); at the last top it was %.2f×. Divide one by the other: 1 would be as hot as then.' % (c['mvrv'], c['prior_cycle_peak'])),
        it('警戒線在哪', 'Where the warning line is', usd(c['k075_price']), usd(c['k075_price']), 'neu',
           '照今天的成本，比值到 0.75 的價格約在這裡，要連 5 天站上才算數；0.80 線約 %s。' % usd(c['k080_price']),
           'On today\'s cost base, a ratio of 0.75 is about here, and it counts only after five straight days above; the 0.80 line is about %s.' % usd(c['k080_price']))]
    if tk: out.append(it('過去的頂部', 'Past tops', '兩次都到 %.2f' % min(tk), 'Both reached %.2f' % min(tk), 'neu',
                         '這張圖 2021 年起才有：2021 和 2025 年兩次頂部前，比值最高%s。只有兩次，警戒線也是看過去的頂部定的。' % (('都到 %.2f' % tk[0]) if '%.2f' % tk[0] == '%.2f' % tk[1] else '到 %.2f 和 %.2f' % tuple(tk)),
                         'This chart starts in 2021: before the 2021 and 2025 tops the ratio peaked at %s. Only two tops, and the warning line was set by looking at them.' % (('%.2f both times' % tk[0]) if '%.2f' % tk[0] == '%.2f' % tk[1] else '%.2f and %.2f' % tuple(tk))))
    return sz, se, out

def pi(L):   # 2026-11-25 改寫（WRITING.md）：先講兩條均線在量什麼，再講過去碰到 1 的時候
    v = L['price']['pi_cycle']
    if v >= 1:
        sz = '短期漲得太快，到了過去頂部出現的位置：Pi Cycle 碰到 1，前三輪頂部都在這前後。'; se = 'Price has run up too fast, to where past tops appeared: Pi Cycle has reached 1, as it did around the last three tops.'
    elif v >= .8:
        sz = '短期漲得很快，接近過去頂部出現的位置：Pi Cycle %.2f，到 1 才算碰到。' % v; se = 'Price has run up fast, close to where past tops appeared: Pi Cycle is %.2f and reaches the mark at 1.' % v
    else:
        sz = '離頂部還遠：Pi Cycle 只有 %.2f，過去頂部出現時是 1，而且上一輪頂部根本沒碰到。' % v; se = 'A top is far off: Pi Cycle is only %.2f, past tops came at 1, and the last top never reached it.' % v
    return sz, se, [
        it('短期漲得多快', 'How stretched', '%.2f' % v, '%.2f' % v, 'warn' if v >= .9 else 'neu',
           '111 日均線（大約最近四個月的平均價）只有 350 日均線兩倍（大約一年平均價的兩倍）的 %.0f%%。兩者相等，代表價格幾個月內漲得遠遠超過一年的平均。' % (v * 100),
           'The 111-day average (roughly the last four months) is only %.0f%% of twice the 350-day average (roughly twice the one-year average). When they meet, price has run far above its yearly average within months.' % (v * 100)),
        it('過去碰到 1 的時候', 'Past touches of 1', '3 輪碰到、1 輪沒有', '3 cycles yes, 1 no', 'neu',
           '2013、2017 和 2021 年 4 月的頂部，都在碰到 1 的前後不久；2025 年的頂部沒碰到。沒碰到不代表沒有頂部，它只看價格。',
           'The 2013, 2017 and April 2021 tops all came soon around a touch of 1; the 2025 top never reached it. No touch does not mean no top, and it uses price alone.')]

def tmh(L):
    # 2026-11-25 改寫（WRITING.md）：Tidemark 是第三方綜合模型，先講兩個分數在量什麼、現在偏哪一邊；條目最多三條
    t = L['cycle']['tidemark']; tp, bt = t['top'], t['bottom']; ct = t.get('cycle_test') or {}; T, B = tp['signal'], bt['signal']
    if B >= 70: sz, se = '這個外部模型認為已經進入強烈底部區：底部分數 %.0f，過了 70。' % B, 'This outside model puts us in its strong-bottom zone: a bottom score of %.0f, above 70.' % B
    elif B >= 50: sz, se = '這個外部模型認為已經進入底部區：底部分數 %.0f，過了 50 的門檻；它不保證這就是最低點。' % B, 'This outside model puts us in its bottom zone: a bottom score of %.0f, past the line at 50. That does not make this the exact low.' % B
    elif T >= 70: sz, se = '這個外部模型發出頂部高度警戒：頂部分數 %.0f，過了 70。' % T, 'This outside model is on high top alert: a top score of %.0f, above 70.' % T
    elif T >= 50: sz, se = '這個外部模型認為進入頂部窗口：頂部分數 %.0f，過了 50 的門檻。' % T, 'This outside model sees a top window: a top score of %.0f, past the line at 50.' % T
    elif B - T >= 30: sz, se = '這個外部模型認為現在偏向底部，但還沒進入它的底部區：底部分數 %.0f，到 50 才算。' % B, 'This outside model leans toward a bottom but is not in its bottom zone yet: a bottom score of %.0f, with the line at 50.' % B
    elif T - B >= 30: sz, se = '這個外部模型認為現在偏向頂部，但還沒進入頂部窗口：頂部分數 %.0f，到 50 才算。' % T, 'This outside model leans toward a top but has not opened its top window: a top score of %.0f, with the line at 50.' % T
    else: sz, se = '這個外部模型看不出偏向：頂部和底部分數都在 50 以下，差距不大。', 'This outside model shows no lean: both scores are under 50 and close together.'
    lag = '時間已經到了，便宜程度還差一點' if bt['timing'] >= 70 and bt['cold'] < 50 else '便宜程度夠了，時間還沒到' if bt['cold'] >= 50 and bt['timing'] < 50 else '兩邊差不多'
    lage = 'the timing is there, the cheapness not quite' if bt['timing'] >= 70 and bt['cold'] < 50 else 'it is cheap enough, but too early' if bt['cold'] >= 50 and bt['timing'] < 50 else 'the two are about even'
    out = [it('離底部多近', 'How close to a bottom', '%.0f' % B, '%.0f' % B, 'up' if B >= 50 else 'neu',
              '底部分數由兩部分合成：估值有多便宜（冷度 %.0f）、離上一輪頂部的時間是否到了以前見底的時候（時間 %.0f）。%s。50 是底部區、70 強烈底部。' % (bt['cold'], bt['timing'], lag),
              'The bottom score combines how cheap valuations are (cold, %.0f) and whether the time since the last top matches past bottoms (timing, %.0f): %s. 50 is the bottom zone, 70 a strong bottom.' % (bt['cold'], bt['timing'], lage)),
           it('離頂部多近', 'How close to a top', '%.0f' % T, '%.0f' % T, 'warn' if T >= 50 else 'neu',
              '%s頂部分數由熱度（估值多貴，%.0f）和時間（離以前頂部出現的時間多近，%.0f）合成；50 進入頂部窗口、70 高度警戒。' % ('幾乎是零。' if T < 5 else '', tp['heat'], tp['timing']),
              '%sThe top score combines heat (how expensive, %.0f) and timing (how close to when past tops came, %.0f); 50 opens the top window, 70 is high alert.' % ('Close to zero. ' if T < 5 else '', tp['heat'], tp['timing']))]
    if ct.get('status') == 'testing':
        out.append(it('這輪低點的驗證', 'Testing this cycle\'s low', '驗證中', 'Testing', 'neu', '模型自己的檢驗：到 %s 都沒跌破 %s 的 %s，它就認為那是這一輪的底部；跌破就算判斷錯。' % (ymd(ct['decisive_date']), md(ct['low_date']), usd(ct['low_price'])),
                      'The model\'s own test: if the %s low of %s holds through %s, it counts that as this cycle\'s bottom; a break means it was wrong.' % (mde(ct['low_date']), usd(ct['low_price']), ymde(ct['decisive_date']))))
    return sz, se, out

def lthloss(L):
    # 2026-11-25 改寫（WRITING.md）：長期持有者＝幣放了 155 天以上沒動的人；先講現在套牢多少、在不在歷次熊底的範圍，再講規律和分界價
    x = L['onchain']['lthloss']; pk = x['peaks'][-1]; pm = x.get('post_min'); co = x.get('cohort') or {}; prev = x['peaks'][:-1]; v = x['value']
    near = pk['value'] - v < 2
    if v > pk['value']:
        sz = '長期持有者有 %.1f%% 套牢，超過這一輪的高點：過去脫離底部之後都沒發生過，底部的規律被打破了。' % v
        se = '%.1f%% of long-term holders\' coins are underwater, above this cycle\'s peak: that never happened after past bottoms, so the bottom pattern is broken.' % v
    elif v >= 40:
        sz = '長期持有者有 %.1f%% 套牢，和歷次熊底差不多：照這張圖，這是底部區間，%s' % (v, '但比例還貼著這一輪的高點，底部可能還在磨。' if near else '而且已經從這一輪的高點回落。')
        se = '%.1f%% of long-term holders\' coins are underwater, about where past bear bottoms were: on this chart that is bottom territory, %s' % (v, 'though the share is still pressed against this cycle\'s peak, so the bottom may still be forming.' if near else 'and the share has come off this cycle\'s peak.')
    else:
        sz = '長期持有者只有 %.1f%% 套牢，大多還在賺錢：離歷次熊底的範圍還遠。' % v
        se = 'Only %.1f%% of long-term holders\' coins are underwater; most are still in profit, far from past bear-bottom territory.' % v
    out = [it('現在有多少人套牢', 'How many are underwater', pu(v), pu(v), 'up' if 40 <= v <= pk['value'] else 'neu',
              '這一輪到目前最高是 %s 的 %s%s。' % (md(pk['date']), pu(pk['value']), '，之後最低回到 %s 的 %s' % (md(pm['date']), pu(pm['value'])) if pm else ''),
              'This cycle\'s high so far was %s on %s%s.' % (pu(pk['value']), mde(pk['date']), ', and the lowest since was %s on %s' % (pu(pm['value']), mde(pm['date'])) if pm else ''))]
    if co.get('break_price'):
        out.append(it('分界價', 'The line', '≈ %s' % usd(co['break_price']), '≈ %s' % usd(co['break_price']), 'neu', '照長期持有者現在的持有成本推算，收盤跌破這裡，套牢比例就會超過這一輪的高點，「脫離底部後不再創新高」的規律就被打破。每天重算。',
                      'From long-term holders\' current cost basis: a close below here would push the share above this cycle\'s peak and break the pattern of no new high after the bottom. Recomputed daily.'))
    am = [p['after_max']['value'] for p in prev if p.get('after_max')]
    out.append(it('前幾輪', 'Past cycles', '%d 輪都沒再創新高' % len(am), 'No new high in %d of %d' % (len(am), len(am)), 'neu',
                  '前 %d 輪熊底時，這個比例的高點在 %.0f–%.0f%%；脫離底部之後最高只回到 %.0f–%.0f%%，都沒再超過。只有 %d 輪，是事後看出的規律。' % (len(prev), min(p['value'] for p in prev), max(p['value'] for p in prev), min(am), max(am), len(prev)),
                  'At the past %d bear bottoms the share peaked at %.0f–%.0f%%; after leaving the bottom it only got back to %.0f–%.0f%%, never above. Only %d cycles, and a pattern seen in hindsight.' % (len(prev), min(p['value'] for p in prev), max(p['value'] for p in prev), min(am), max(am), len(prev))))
    return sz, se, out

def npl365(L):
    n = L['onchain']['npl365']; v = n['value'] * 1000; v30 = n['v30'] * 1000; pb = [b['value'] * 1000 for b in n['bottoms'] if not b['now']]; tp = [t['value'] * 1000 for t in n['tops']]
    # 2026-11-25 改寫（WRITING.md）：先講這條線是一整年的賺錢賣出減賠錢賣出，再講和以前的熊底、頂部比；統一寫「賺錢賣出／賠錢賣出」
    deeper = v < v30; grow = (deeper and v < 0) or (not deeper and v > 0)
    if v < 0:
        sz = '過去一年市場整體在賠錢賣出，%s' % ('而且還在加深：照這張圖，認賠還沒走完，但深度遠不如以前的熊底。' if grow else '但比 30 天前少：最重的認賠可能過了，深度也遠不如以前的熊底。')
        se = 'Over the past year the market has sold at a loss on balance, %s' % ('and it is still deepening: on this chart the loss-taking is not done, though it is far shallower than past bear bottoms.' if grow else 'but less than 30 days ago: the heaviest loss-taking may be past, and it is far shallower than past bear bottoms.')
    else:
        r = v / tp[-1] * 100
        sz = '過去一年市場整體在賺錢賣出，%s：%s' % ('而且越賣越多' if grow else '但比 30 天前少', '已經接近上一輪頂部前後的水準。' if r >= 80 else '還遠不到以前頂部前後的程度。')
        se = 'Over the past year the market has sold at a profit on balance, %s: %s' % ('and more and more of it' if grow else 'but less than 30 days ago', 'close to the level around the last top.' if r >= 80 else 'nowhere near the levels around past tops.')
    dv = v - v30; W = lambda q: ('+' if q > 0 else M if q < 0 else '') + n0(abs(q) / 1e4) + ' 萬顆'   # 整數萬顆，大數字才好讀
    out = [it('過去一年合計', 'Past year in total', wan(v), kb(v), 'down' if v < 0 else 'up',
              '%s30 天前是 %s，一個月裡%s了 %s。' % ('%s 起轉成負的，賠錢賣出比賺錢賣出多；' % ymd(n['neg_since']) if n.get('neg_since') and v < 0 else '', wan(v30), '又多' if (dv < 0) == (v < 0) else '少', wan(abs(dv), False)),
              '%s%s thirty days ago, %s %s in a month.' % ('Negative since %s: more coins sold at a loss than at a profit; ' % ymde(n['neg_since']) if n.get('neg_since') and v < 0 else '', kb(v30), 'another' if (dv < 0) == (v < 0) else 'down by', kb(abs(dv), False)))]
    if v < 0:
        out.append(it('和以前的熊底比', 'Against past bear bottoms', '上一輪的 %d%%' % round(v / pb[-1] * 100), '%d%% of the last' % round(v / pb[-1] * 100), 'neu',
                      '前 %d 輪熊底，一年合計最深在 %s到 %s之間，這一輪淺得多。' % (len(pb), W(max(pb)), W(min(pb))),
                      'At the past %d bear bottoms the one-year total sank to between %s and %s; this cycle is far shallower.' % (len(pb), kb(max(pb)), kb(min(pb)))))
    i = max(range(len(tp)), key=lambda j: tp[j]); ty = [t['top'][:4] for t in n['tops']]
    out.append(it('頂部前後', 'Around tops', '上一輪最少', 'Smallest last time', 'neu',
                  '頂部前後半年，一年合計的賺錢賣出最多是 %s 年的 %s，上一輪只有 %s。' % (ty[i], W(tp[i]), W(tp[-1])),
                  'Around tops, the one-year total of profit-taking peaked at %s in %s; last cycle it reached only %s.' % (kb(tp[i]), ty[i], kb(tp[-1]))))
    return sz, se, out

def agecost(L):
    # 2026-11-25 改寫（WRITING.md）：補上標題（舊版 c36['since'] 是 None 時整張卡沒有讀數）；先講近期買家賺還是賠，再講兩條長線的交叉
    a = L['cycle']['age_cost']; c = a['c36']; lc = a['last_cross']; px = a['price']; dth = lc['kind'] == 'death'
    dc = [x['days_to_next'] for x in a['crosses'] if x['kind'] == lc['kind'] and x.get('days_to_next')]
    both = '更早買的兩批也都在虧損' if px < min(a['c612'], a['c1218']) else '更早買的兩批都有賺錢' if px > max(a['c612'], a['c1218']) else '更早買的兩批一賺一賠'
    bothe = 'and the two earlier groups are underwater too' if px < min(a['c612'], a['c1218']) else 'while the two earlier groups are in profit' if px > max(a['c612'], a['c1218']) else 'and of the two earlier groups one is up, one down'
    if c['above']:
        sz = '價格比近 3–6 個月買幣的人的成本高 %.1f%%，這批人有賺錢，%s：照這張圖，近期買家撐得住，反彈比較不會遇到解套賣壓。' % (c['gap_pct'], both)
        se = 'Price is %.1f%% above what buyers of the last 3–6 months paid, so they are in profit, %s: on this chart recent buyers are holding up, and rallies meet less break-even selling.' % (c['gap_pct'], bothe)
    else:
        sz = '價格比近 3–6 個月買幣的人的成本低 %.1f%%，%s：照這張圖，還是熊市裡的樣子，反彈到他們的成本附近容易遇到想解套的賣壓。' % (abs(c['gap_pct']), both)
        se = 'Price is %.1f%% below what buyers of the last 3–6 months paid, %s: on this chart it still looks like a bear market, and a rally back to their cost is likely to meet break-even selling.' % (abs(c['gap_pct']), bothe)
    s_ = c.get('since'); sd, sn = (s_['date'], s_['days']) if isinstance(s_, dict) else (s_, c.get('days')) if s_ else (None, None)
    up_ = [u for u in c.get('ups') or [] if u['date'] <= a['date']]; lu = up_[-1] if up_ else None
    tail = ('，%s 起 %d 天' % (ymd(sd), sn)) if sd and sn else ''; taile = (', since %s, %d days' % (ymde(sd), sn)) if sd and sn else ''
    out = [it('近 3–6 個月的買家', 'Buyers of the last 3–6 months', usd(c['cost']), usd(c['cost']), 'up' if c['above'] else 'down',
              '這是他們的平均成本，收盤在它%s%s。這條線 30 天%s了 %s。' % ('上面' if c['above'] else '下面', tail, '下降' if c['chg30'] < 0 else '上升', usd(abs(c['chg30']))),
              'This is their average cost; the close is %s it%s. The line %s %s in 30 days.' % ('above' if c['above'] else 'below', taile, 'fell' if c['chg30'] < 0 else 'rose', usd(abs(c['chg30']))))]
    out.append(it('半年到一年半前的買家', 'Buyers 6–18 months ago', '%s / %s' % (kusd(a['c612']), kusd(a['c1218'])), '%s / %s' % (kusd(a['c612']), kusd(a['c1218'])), 'neu',
                  '6–12 個月前買的平均成本，比 12–18 個月前買的%s %.1f%%，%s 交叉%s。%s' % ('低' if a['gap_pct'] < 0 else '高', abs(a['gap_pct']), ym(lc['date']), '往下' if dth else '往上',
                      '較新的一批買得比較便宜，過去出現在熊市底部附近。' if dth else '較新的一批買得比較貴，過去大約是主升段開始的時候。'),
                  'Coins bought 6–12 months ago cost %.1f%% %s those bought 12–18 months ago; the lines crossed %s in %s. %s' % (abs(a['gap_pct']), 'less than' if a['gap_pct'] < 0 else 'more than', 'down' if dth else 'up', yme(lc['date']),
                      'The newer group bought cheaper, which has come near past bear-market bottoms.' if dth else 'The newer group paid more, which has roughly marked the start of the main bull leg.')))
    if dc: out.append(it('過去要多久翻回來' if dth else '過去要多久翻下去', 'How long it took to flip back', '%d–%d 天' % (min(dc), max(dc)), '%d–%d days' % (min(dc), max(dc)), 'neu',
                         '過去 %d 次從交叉%s到重新%s花的時間；這一輪才過了 %d 天。兩條線是半年到一年半前的買價，比價格落後很多，交叉時價格往往已經走了一段。' % (len(dc), '往下' if dth else '往上', '翻上去' if dth else '翻下去', a['days_since']),
                         'The time it took in %d past cases to go from this cross back the other way; this cycle is %d days in. Both lines are what people paid six to eighteen months ago, so they lag price a long way, and price has usually moved by the time they cross.' % (len(dc), a['days_since'])))
    return sz, se, out

def hashr_bv(L, hb):   # 2026-11-19 Hash Ribbons 改成圖（bv_more.py 第 7 項）：讀值照回測，用 Bitview 的算力，和圖同一份
    SG_ = lambda v: ('+%d%%' % v) if v >= 0 else ('−%d%%' % -v)
    YMD = lambda d_: d_.replace('-', '/'); bys = hb['buys']; pre, post, bp = hb['pre'], hb['post'], hb['base_post']
    yr0 = L['meta']['bar_date'][:4]; ty = [b for b in bys if b['d'][:4] == yr0]; lb = bys[-1] if bys else None
    # 2026-11-25 改寫（WRITING.md）：先講礦工現在在不在關機，再講 Capriole 原版訊號以前準、近年不準；Capriole 原作者的叫法卡上一律寫成「原版訊號」；條目併成三條
    pr = [b['r365'] for b in bys if b['d'] >= '2021' and b['r365'] is not None]
    gap = abs(hb['m30'] / hb['m60'] - 1) * 100
    items = [
        it('礦工現在', 'Miners now', '投降中' if hb['cap'] else '沒有投降', 'Capitulating' if hb['cap'] else 'No capitulation', 'neu',
         '30 日平均算力 %s EH/s，比 60 日平均%s %.1f%%，這個狀態已經 %d 天。%s' % (format(hb['m30'], ',.0f'), '低' if hb['m30'] < hb['m60'] else '高', gap, hb['run'], ('上一次 Capriole 原版訊號是 %s（收盤 $%s）。' % (YMD(lb['d']), format(lb['px'], ','))) if lb else ''),
         'The 30-day average hashrate is %s EH/s, %.1f%% %s the 60-day, %d day%s in this state. %s' % (format(hb['m30'], ',.0f'), gap, 'below' if hb['m30'] < hb['m60'] else 'above', hb['run'], '' if hb['run'] == 1 else 's', ('The last original Capriole signal was on %s (close $%s).' % (lb['d'], format(lb['px'], ','))) if lb else '')),
        it('2021 年以前', 'Before 2021', '%d 次裡 %d 次較高' % (pre['n'], pre['up']), '%d of %d higher' % (pre['up'], pre['n']), 'neu',
         '原版訊號之後一年，價格 %d 次裡 %d 次比當時高，中位數 %s。' % (pre['n'], pre['up'], SG_(pre['med'])),
         'A year after the original signal, price was higher %d times out of %d, median %s.' % (pre['up'], pre['n'], SG_(pre['med']))),
        it('2021 年以後', 'Since 2021', '%d 次裡 %d 次較高' % (post['n'], post['up']), '%d of %d higher' % (post['up'], post['n']), 'neu',
         '滿一年的 %d 次，最好 %s、最差 %s，中位數 %s；同期隨便一天，一年後較高的機率 %d%%、中位數 %s，差不多。%s 年已經出現 %d 次原版訊號，投降、恢復來回好幾次。' % (post['n'], SG_(max(pr)) if pr else '—', SG_(min(pr)) if pr else '—', SG_(post['med']), bp['up'], SG_(bp['med']), yr0, len(ty)),
         'Of the %d with a full year, the best was %s and the worst %s, median %s; any day in that span was higher a year later %d%% of the time, median %s, about the same. %s has already had %d original signals as capitulation came and went.' % (post['n'], SG_(max(pr)) if pr else '—', SG_(min(pr)) if pr else '—', SG_(post['med']), bp['up'], SG_(bp['med']), yr0, len(ty)))]
    if hb['cap']:
        sz = '礦工正在關機（投降）：以前這常出現在底部附近，但近幾年它之後的走勢和隨便一天差不多，只能當背景。'
        se = 'Miners are switching off (capitulation): that used to come near bottoms, but in recent years what followed was about the same as any day, so it is background only.'
    else:
        sz = '算力在增加，礦工沒有投降：這張現在不提供方向，近幾年它的訊號也和隨便一天差不多。'
        se = 'Hashrate is rising and miners are not capitulating: the chart gives no direction now, and in recent years its signal has done about as well as any day.'
    return sz, se, items
def hashr(L):
    hb = (L['onchain'].get('bvx') or {}).get('hrib')
    if hb: return hashr_bv(L, hb)
    h = L['onchain']['hash_ribbons']; g = (h['ratio'] - 1) * 100
    sz = ('%s：30 日平均算力比 60 日平均%s %.1f%%，已經 %d 天。' % ('礦工正在關機（投降）' if h['capitulation'] else '礦工沒有投降，這張現在不提供方向', '高' if g >= 0 else '低', abs(g), h['state_days']))
    se = '%s: the 30-day average hashrate is %.1f%% %s the 60-day, for %d days.' % ('Miners are switching off (capitulation)' if h['capitulation'] else 'No miner capitulation, so the chart gives no direction now', abs(g), 'above' if g >= 0 else 'below', h['state_days'])
    return sz, se, [it('兩條算力均線', 'The two hashrate averages', '%.3f' % h['ratio'], '%.3f' % h['ratio'], 'down' if h['capitulation'] else 'neu', '30 日平均 ÷ 60 日平均，低於 1 是投降。上次%s在 %s；近 90 天最低 %.3f。' % ('進入投降' if h['capitulation'] else '從投降恢復', md(h['last_cross']), h['min_ratio_90d']),
                       '30-day ÷ 60-day average; below 1 is capitulation. Last %s on %s; the 90-day low is %.3f.' % ('entered capitulation' if h['capitulation'] else 'recovered from capitulation', mde(h['last_cross']), h['min_ratio_90d']))]

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
    'pi': (['圖上：大數字和橫條是 111 日均線（約四個月的平均價）÷ 350 日均線的兩倍（約一年平均價的兩倍），橫條上的刻度是 1。', '怎麼看：越接近 1，代表價格幾個月內漲得越遠超過一年的平均；2013、2017、2021 年的頂部都在碰到 1 的前後不久。', '小心：2025 年的頂部沒碰到 1，頂部一輪比一輪溫和，以後可能更難碰到；它只看價格，和鏈上指標一起看。'],
           ['On the chart: the big number and bar are the 111-day average (about four months) ÷ twice the 350-day average (about twice the one-year average); the tick on the bar is 1.', 'Reading it: the closer to 1, the further price has run above its yearly average within months; the 2013, 2017 and 2021 tops all came soon around a touch of 1.', 'Caveat: the 2025 top never reached 1, and as tops get milder it may get harder to reach; it uses price alone, so read it with the on-chain gauges.']),
    'hashr': (['圖上：上格是價格，圓圈是 Capriole 原版訊號那天（一年後較高是綠、較低是紅、還不到一年另一色）；下格是算力的 30 日和 60 日平均，淡紅底是投降期。', '怎麼看：30 日平均跌到 60 日平均下面，代表有礦工在關機；原版訊號是投降結束後、價格開始轉強的那天。2021 年以前之後一年都較高，2021 年以後和隨便一天差不多。', '小心：礦機效率、託管和算力出租改變了礦工關機的原因；它只看礦工，和其他指標一起看。'],
              ['On the chart: price on top, with circles on the days of Capriole\'s original signal (green if higher a year later, red if lower, another colour if under a year); below, the 30- and 60-day hashrate averages, with capitulation shaded red.', 'Reading it: the 30-day average falling below the 60-day means miners are switching off; the original signal is the day price turns up after capitulation ends. Before 2021 price was always higher a year later; since then it has done about as well as any day.', 'Caveat: rig efficiency, hosting and hashrate rental have changed why miners switch off; it only covers miners, so read it with the rest.']),
    'cyccmp': (['每條線是一輪頂部之後每天的收盤，和那一輪頂部比跌了多少。', '橫軸是頂部後第幾天，可以直接和前幾輪同一天比。', '只有三輪樣本，這輪的走法不一定一樣。'],
               ['Each line is the daily close after a cycle top, as a drop from that top.', 'The x-axis is days since the top, so today lines up with the same day in past cycles.', 'Only three past cycles; this one need not follow them.']),
}
