# -*- coding: utf-8 -*-
"""週期頁的讀數（2026-11-17，取代舊版抽來的讀數；規則見 reads.py）。每個函式回傳 (一句結論中, 英, [最多三條事實])"""
import datetime as dt
from reads import sg, pc, pu, n0, sn0, wan, kb, md, ymd, ym, ord_en, it, M, mde, ymde, yme, MON

SG = [('深夜', 'Deep night', '底部區', 'bottom zone'), ('入夜', 'Nightfall', '下跌', 'falling'), ('破曉', 'Daybreak', '初升', 'early rise'), ('白晝', 'Daylight', '上升', 'rising'), ('黃昏', 'Dusk', '過熱', 'overheated')]
HEAT = dict(lnupl=('長期持有者的帳面獲利（NUPL）', 'long-term holders\' paper profit (NUPL)'), rup=('帳面獲利佔市值', 'paper profit as a share of market cap'), pl=('價格對長期趨勢價', 'price against the long-run trend'), rr=('儲備風險', 'reserve risk'), mvz=('市值對成本（MVRV-Z）', 'value vs cost (MVRV-Z)'))
STN = {'熊市': 'Bear market', '轉換期': 'Transition', '牛市': 'Bull market'}
EVN = dict(mom12='12-month momentum', mvrv1y='MVRV vs its one-year mean', rcgrowth='Capital inflow', xs90='Exchange supply', sth='Short-term holder cost', tmm='STH cost vs true market mean')
RGN = dict(d200=('價格對 200 日均線', 'price vs the 200-day MA'), mom12=('一年來的漲跌', 'the one-year change'), mvrv1y=('市值對成本（和一年平均比）', 'market value vs cost (against its one-year mean)'), rc30=('流入的資金', 'money flowing in'), xs90=('交易所裡的幣', 'coins on exchanges'), rpl=('賣出的人賺多還是賠多', 'whether sellers take profits or losses'))
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

# 2026-11-25 週期頁「現在的階段」「估值冷熱」照 WRITING.md 改寫：先講這是什麼、數字代表什麼，再講現在在哪個位置；不寫交易指令
DPOS = [('估值是週期裡最便宜的一段，屬於底部區', 'valuations are at the cheapest stretch of the cycle, bottom territory'),
        ('估值不算貴、趨勢往下，是下跌段', 'valuations are not rich and the trend points down, the falling leg'),
        ('估值還偏低、趨勢已經轉上，是初升段', 'valuations are still low and the trend has turned up, the early rise'),
        ('估值到了中上、趨勢往上，是上升段', 'valuations are mid-to-high and the trend is up, the rising leg'),
        ('估值接近過去頂部的水準，是過熱段', 'valuations are near past-top levels, the overheated leg')]
def dawn(L):
    d = L['cycle']['dawn']; k = d['stage']; s = SG[k]; st = next(x for x in d['stats'] if x['stage'] == k); m6 = st['m6']; hot = d['heat'] >= 50
    ex = (max if hot else min)(d['heat_c'], key=lambda c: c['pct']); on = d['regime'] > 0; agree = (d['trend'] > 0) == on
    bz, be = ('過去在這一段，半年後多半比當時還低', 'six months on, price was usually lower in this stage') if m6['up'] < 50 else \
             ('這一段可能一待好幾個月，半年後不一定比現在高', 'this stage can last months, and six months on price was not always higher') if m6['up'] < 80 else \
             ('樣本只有幾輪週期', 'there are only a few cycles of history')
    sz = '晨昏指數在「%s」（熱度 %.0f，滿分 100）：%s；但%s。' % (s[0], d['heat'], DPOS[k][0], bz)
    se = 'The Dawn–Dusk Index is at %s (heat %.0f out of 100): %s, though %s.' % (s[1].lower(), d['heat'], DPOS[k][1], be)
    if hot: xz, xe = ('近 4 年只有 %d%% 的日子比現在高' % (100 - ex['pct']), 'only %d%% of days in four years were higher' % (100 - ex['pct'])) if ex['pct'] < 100 else ('近 4 年沒有一天比現在高', 'no day in four years was higher')
    else: xz, xe = ('近 4 年只有 %d%% 的日子比現在低' % ex['pct'], 'only %d%% of days in four years were lower' % ex['pct']) if ex['pct'] > 0 else ('近 4 年沒有一天比現在低', 'no day in four years was lower')
    return sz, se, [
        it('估值有多熱' if hot else '估值有多冷', 'How hot valuations are' if hot else 'How cold valuations are', '%.0f / 100' % d['heat'], '%.0f / 100' % d['heat'], 'neu',
           '熱度＝五項估值各自和近 4 年比的排名，再取平均：0 是近 4 年最便宜，100 是最貴。4 週前是 %.0f。五項裡最%s的是「%s」，%s。' % (d['heat4'], '熱' if hot else '冷', HEAT[ex['key']][0], xz),
           'Heat is the average of five valuation measures, each ranked against the last four years: 0 is the cheapest of those years, 100 the richest. It was %.0f four weeks ago. The %s of the five is %s: %s.' % (d['heat4'], 'hottest' if hot else 'coldest', HEAT[ex['key']][1], xe)),
        it('這一段之後半年', 'Six months on from this stage', '%d%% 比當時高' % m6['up'], '%d%% higher' % m6['up'], 'neu',
           '現在是「%s」的第 %d 週。2013 年以來落在這一段的 %d 週裡，半年後價格比當時高的佔這麼多，中位數 %s。' % (s[0], d['stage_weeks'], st['weeks'], pc(m6['med'], 0)),
           'This is week %d of %s. Of the %d weeks in this stage since 2013, that share was higher six months later, with a median change of %s.' % (d['stage_weeks'], s[1].lower(), st['weeks'], pc(m6['med'], 0))),
        it('趨勢方向', 'Trend direction', '往上' if on else '往下', 'Up' if on else 'Down', 'up' if on else 'down',
           '%s 起判定為往%s。四項趨勢指標（價格對 200 日均線、價格對短期持有者成本等）合計 %s，%s；要連 4 週在另一邊才會翻。' % (ymd(d['since']), '上' if on else '下', sg(d['trend'], 2), '方向一致' if agree else '已經偏向另一邊'),
           'Judged %s since %s. The four trend measures (price against the 200-day MA, against the short-term holder cost and so on) sum to %s, %s; it takes four weeks on the other side to flip.' % ('up' if on else 'down', ymde(d['since']), sg(d['trend'], 2), 'in line with it' if agree else 'already leaning the other way'))]

def stage(L):
    s = L['cycle']['stage']; e = s['evidence']; ok = [x for x in e['items'] if x['ok']]; px = L['price']['bar']['c']; gap = (px / s['sma200'] - 1) * 100
    lk = s['stage'] == '牛市'   # 2026-11-20：牛市是鎖定的標籤，鎖定的規則和進度在卡上第一列（cycle_data.py），證據裡不再重講
    N_ = (s.get('bear_back') or {}).get('bull_below_falling_run', 30); left = max(0, N_ - s.get('below_falling_run', 0)); uz, ue = ('上', 'above') if gap >= 0 else ('下', 'below')
    if lk and gap < 0:
        tz = ('收盤若一直待在往下走的均線下面，再 %d 天就退回熊市' % left) if not s['sma200_rising'] else '均線還在往上，退回熊市的倒數還沒開始'
        te = ('if the close stays under the falling average, it reverts to bear in %d more days' % left) if not s['sma200_rising'] else 'the average is still rising, so the countdown back to bear has not started'
        sz = '標籤還是「牛市」，但那是鎖定的結果：收盤已在 200 日均線下 %.0f%%，趨勢其實轉弱了；%s。' % (abs(gap), tz)
        se = 'The label still says bull, but only because it is locked: the close is %.0f%% below the 200-day MA and the trend has weakened; %s.' % (abs(gap), te)
    elif lk:
        sz = '市場階段是牛市（%s 起）：收盤在 200 日均線上 %.0f%%，長期趨勢往上；但這張只看價格和均線，不看貴不貴。' % (md(s['since']), gap)
        se = 'The market stage is bull (since %s): the close is %.0f%% above the 200-day MA and the long-run trend is up, though this card only looks at price and the average, not at valuation.' % (mde(s['since']), gap)
    elif s['stage'] == '轉換期':
        sz = '市場在熊市和牛市之間的過渡期（收盤在 200 日均線%s %.0f%%）：還要站穩一段時間才算牛市，跌回均線下就會退回熊市。' % (uz, abs(gap))
        se = 'The market is in transition between bear and bull (the close is %.0f%% %s the 200-day MA): it needs to hold above for a while to count as bull, and falling back below sends it back to bear.' % (abs(gap), ue)
    else:
        cs = s.get('capitulation_seen')
        sz = '市場階段是熊市（收盤在 200 日均線%s %.0f%%）：%s。' % (uz, abs(gap), '投降已經出現過，還差收盤站上往上走的均線，才會進入過渡期' if cs else '還沒看到投降，長期趨勢往下')
        se = 'The market stage is bear (the close is %.0f%% %s the 200-day MA): %s.' % (abs(gap), ue, 'a capitulation has happened; a close above a rising average would start the transition' if cs else 'no capitulation yet, and the long-run trend is down')
    if s['stage'] == '轉換期':
        rz, re_ = '收盤在往上走的 200 日均線上連 30 天，成為牛市；連 5 天收在均線下，退回熊市。', '30 straight closes above a rising 200-day MA make it bull; 5 closes below send it back to bear.'
    else:
        rz, re_ = '要先出現投降，收盤再站上往上走的 200 日均線，才進入過渡期。', 'It needs a capitulation, then a close above a rising 200-day MA, to enter the transition.'
    dn_ = not s['sma200_rising'] and gap < 0
    return sz, se, [
        *([] if lk else [it('下一步', 'What comes next', s['stage'], STN.get(s['stage'], s['stage']), 'neu', rz, re_)]),
        it('長期均線', 'The long-term average', usd(s['sma200']), usd(s['sma200']), 'neu',
           '200 日均線＝過去 200 天收盤的平均，常被當成長期趨勢線。它%s（30 天前 %s）%s。' % ('還在往上' if s['sma200_rising'] else '在往下走', usd(s['sma200_30d_ago']), '：價格在它下面越久，它就被拉得越低' if dn_ else ''),
           'The 200-day MA is the average close of the past 200 days, often used as the long-run trend line. It is %s (%s 30 days ago)%s.' % ('still rising' if s['sma200_rising'] else 'falling', usd(s['sma200_30d_ago']), ': the longer price stays below it, the lower it gets pulled' if dn_ else '')),
        it('其他佐證', 'Other checks', '%d / %d 項成立' % (len(ok), e['n']), '%d of %d met' % (len(ok), e['n']), 'neu',
           ('成立的：%s。' % '、'.join(x['label'] for x in ok) if ok else '一項都不成立：一年來的漲跌、資金流入、短期持有者成本都還不支持牛市。') + '這幾項只作參考，不決定階段。',
           ('Met: %s. ' % ', '.join(EVN.get(x['id'], x['id']).lower() for x in ok) if ok else 'None are met: the one-year change, money inflows and the short-term holder cost all fail to support a bull market. ') + 'They are for reference and do not decide the stage.')]

def regime(L):
    r = L['cycle']['regime']; on = r['regime'] > 0; neg = r['value'] < 0; v, p1, p4 = r['value'], r['prev'], r['prev4']
    up = [c for c in r['comps'] if c['val'] >= .15]; dn = [c for c in r['comps'] if c['val'] <= -.15]
    fl = [f for f in r['flips'] if f['dir'] == (1 if on else -1) and f.get('r52') is not None]; good = [f for f in fl if (f['r52'] > 0) == on]; bad = [f for f in fl if f not in good]
    if r['pending']:
        wz = len(dn) > len(up) if on else len(up) > len(dn)
        tz = ('六項裡多數已經轉弱，中期趨勢在往下' if on else '六項裡多數已經轉強，中期趨勢在往上') if wz else '但六項多空互見，還可能翻不過去'
        te = ('most of the six inputs have weakened and the medium-term trend is turning down' if on else 'most of the six inputs have strengthened and the medium-term trend is turning up') if wz else 'but the six inputs are split, so it may not flip'
        sz = '週線多空分數已經連 %d 週是%s的，再 %d 週就正式翻成%s：%s。' % (r['pending'], '負' if neg else '正', 4 - r['pending'], '空方' if on else '多方', tz)
        se = 'The weekly score has been %s for %d week%s; %d more and it officially flips %s: %s.' % ('negative' if neg else 'positive', r['pending'], '' if r['pending'] == 1 else 's', 4 - r['pending'], 'short' if on else 'long', te)
    else:
        tz, te = ('但分數接近 0，容易來回翻', 'though the score is near 0 and flips easily') if abs(v) < 1 else ('但要連 4 週才翻，轉折會晚幾週', 'though it takes four weeks to flip, so turns show up late')
        sz = '週線多空分數是%s的，%s已經 %d 週：中期趨勢往%s；%s。' % ('正' if on else '負', '多方' if on else '空方', r['weeks'], '上' if on else '下', tz)
        se = 'The weekly score is %s, %s for %d weeks: the medium-term trend is %s, %s.' % ('positive' if on else 'negative', 'long' if on else 'short', r['weeks'], 'up' if on else 'down', te)
    mv = '一路往下' if v < p1 < p4 else '一路往上' if v > p1 > p4 else '上下來回'; mve = 'falling all the way' if v < p1 < p4 else 'rising all the way' if v > p1 > p4 else 'going back and forth'
    return sz, se, [
        it('分數的走向', 'Where the score is heading', sg(v, 2), sg(v, 2), 'up' if v > 0 else 'down', '一週前 %s、四週前 %s，%s。分數從 −6 到 +6，越接近 0 越容易來回翻。' % (sg(p1, 2), sg(p4, 2), mv),
           '%s a week ago and %s four weeks ago, %s. The score runs from −6 to +6; the nearer 0, the more easily it flips.' % (sg(p1, 2), sg(p4, 2), mve)),
        it('六項各偏哪邊', 'Which way the six lean', '%d 多 %d 空' % (len(up), len(dn)), '%d long, %d short' % (len(up), len(dn)), 'neu', '偏多：%s；偏空：%s。' % ('、'.join(RGN[c['key']][0] for c in up) or '無', '、'.join(RGN[c['key']][0] for c in dn) or '無'),
           'Long: %s. Short: %s.' % (', '.join(RGN[c['key']][1] for c in up) or 'none', ', '.join(RGN[c['key']][1] for c in dn) or 'none')),
        it('過去翻%s之後' % ('多' if on else '空'), 'After past %s turns' % ('long' if on else 'short'), '%d / %d 次對' % (len(good), len(fl)), '%d of %d right' % (len(good), len(fl)), 'neu',
           '2013 年以來翻%s %d 次，%d 次一年後價格比當時%s；看錯的是 %s。' % ('多' if on else '空', len(fl), len(good), '高' if on else '低', '、'.join('%s（之後一年 %s）' % (ym(f['date']), pc(f['r52'], 0)) for f in bad) or '沒有'),
           '%d %s turns since 2013; %d were followed by a %s price a year later. The misses: %s.' % (len(fl), 'long' if on else 'short', len(good), 'higher' if on else 'lower', ', '.join('%s (%s over the next year)' % (yme(f['date']), pc(f['r52'], 0)) for f in bad) or 'none'))]

def hnupl(L):
    h = L['onchain']['hnupl']; s = LNS.get(h['stage'], (h['stage'], h['stage'])); r = h['r30']; b = h['base30']; bt = h['bottoms'][-1]; pre = h['bottoms'][:-1]
    thin, fat = h['stage'] in ('cap', 'hope'), h['stage'] in ('belief', 'euph')
    pz, pe = ('落在過去熊市後段到底部的區間', 'in the range seen from late bear markets into bottoms') if thin else ('落在過去週期後段到頂部的區間', 'in the range seen late in past cycles, near tops') if fat else ('在中間，不在底部也不在頂部', 'mid-range, neither bottom nor top')
    sz = '長期持有者的帳面獲利%s（NUPL %.2f），%s；%s。' % ('只剩薄薄一層' if thin else '很厚' if fat else '還有一些', h['lth'], pz,
         ('但這一輪的底部比前幾輪高，不一定會跌成虧損' if bt['value'] > max(x['value'] for x in pre) else '短期持有者' + ('整體在賠' if h['sth'] < 0 else '整體在賺')) if thin else ('短期持有者整體在賠' if h['sth'] < 0 else '短期持有者整體也在賺'))
    se = 'Long-term holders\' paper profit is %s (NUPL %.2f), %s; %s.' % ('thin' if thin else 'fat' if fat else 'moderate', h['lth'], pe,
         ('but this cycle\'s bottom sat higher than earlier ones, so it need not turn into a loss' if bt['value'] > max(x['value'] for x in pre) else 'short-term holders are ' + ('underwater' if h['sth'] < 0 else 'in profit')) if thin else ('short-term holders are underwater' if h['sth'] < 0 else 'short-term holders are in profit too'))
    return sz, se, [
        it('老手的帳面獲利', 'Long-term holders', '%.2f' % h['lth'], '%.2f' % h['lth'], 'neu', '幣放超過 150 天沒動的人，落在「%s」區；30 天前還有 %.2f。過去三輪熊底都跌到 −0.3 以下（整體虧損），這一輪最低只到 %s。' % (s[0], h['lth30'], sg(bt['value'], 2)),
           'Holders whose coins have not moved for 150+ days, now in the %s zone; %.2f thirty days ago. The past three bear bottoms all fell below −0.3 (a loss overall); this cycle\'s low was only %s.' % (s[1].lower(), h['lth30'], sg(bt['value'], 2))),
        it('最近買的人', 'Recent buyers', sg(h['sth'], 2), sg(h['sth'], 2), 'down' if h['sth'] < 0 else 'up', '幣放不到 150 天的人，%s %s 0：%s。30 天前是 %s。' % (md(h['cross']['date']), '升上' if h['cross']['up'] else '跌破', '最近買的人平均買貴了，整體在賠' if h['sth'] < 0 else '最近買的人整體有賺', sg(h['sth30'], 2)),
           'Holders of under 150 days %s 0 on %s: %s. It was %s thirty days ago.' % ('rose above' if h['cross']['up'] else 'fell below', mde(h['cross']['date']), 'recent buyers paid too much on average and are underwater' if h['sth'] < 0 else 'recent buyers are in profit as a group', sg(h['sth30'], 2))),
        it('最近買的人轉賺之後', 'After recent buyers turn profitable', '%d 次裡 %d 次漲' % (r['n'], r['up']), 'Up %d of %d' % (r['up'], r['n']), 'neu',
           '過去短期持有者由賠轉賺 %d 次，30 天後價格上漲的佔這麼多、中位數 %s；隨便挑一天是 %d%%、%s。%s' % (r['n'], pc(r['med']), b['up'], pc(b['med']), '現在還是負的，這一條要等它轉正才用得上。' if h['sth'] < 0 else ''),
           'Short-term holders have turned from loss to profit %d times; that many were followed by a rise 30 days later, median %s (any day: %d%%, %s).%s' % (r['n'], pc(r['med']), b['up'], pc(b['med']), ' It is still negative now, so this only applies once it turns positive.' if h['sth'] < 0 else ''))]

def rup(L):
    r = L['onchain']['rup']; n = r['near']; op = next((e for e in r['eps'] if e.get('open')), None); dd = [w['dd180'] for w in n['waves'] if w.get('dd180') is not None]
    if r['zone'] == 'floor':
        sz = '還沒賣的幣，帳面獲利只剩市值的 %.0f%%，跌破 %.0f%% 的週期地板：過去只在熊市尾聲出現；但跌破之後還常再跌一段。' % (r['value'], r['floor'])
        se = 'Paper profit on unsold coins is down to %.0f%% of market cap, under the %.0f%% cycle floor: this has only happened late in bear markets, though price often fell further after breaking it.' % (r['value'], r['floor'])
    elif r['value'] <= n['hi']:
        sz = '還沒賣的幣，帳面獲利佔市值 %.1f%%，接近 %.0f%% 的週期地板：過去只在熊市後段到復甦初期出現；但進來之後幾個月內常再跌一段。' % (r['value'], r['floor'])
        se = 'Paper profit on unsold coins is %.1f%% of market cap, near the %.0f%% cycle floor: seen only from late bear markets into early recoveries, though price often fell further within months of getting here.' % (r['value'], r['floor'])
    else:
        sz = '還沒賣的幣，帳面獲利佔市值 %.1f%%，離週期地板還有 %.1f 個百分點：不在底部區。' % (r['value'], r['gap']); se = 'Paper profit on unsold coins is %.1f%% of market cap, %.1f points above the cycle floor: not bottom territory.' % (r['value'], r['gap'])
    s365 = n['s365']; allup = s365['up'] >= 100
    return sz, se, [
        it('一個月前', 'A month ago', pu(r['d30']), pu(r['d30']), 'neu', '30 天前是 %s；一年來最低是 %s（%s）。%s' % (pu(r['d30']), pu(r['lo1y']['value']), md(r['lo1y']['date']), ('這是跌破地板的第 %d 天。' % op['days']) if r['zone'] == 'floor' and op else ''),
           '%s thirty days ago; the one-year low was %s (%s).%s' % (pu(r['d30']), pu(r['lo1y']['value']), mde(r['lo1y']['date']), (' This is day %d under the floor.' % op['days']) if r['zone'] == 'floor' and op else '')),
        it('跌到這一帶，一年後', 'A year after reaching this zone', '都比當時高' if allup else '%d%% 比當時高' % s365['up'], 'All higher' if allup else '%d%% higher' % s365['up'], 'neu',
           '過去落在 %.1f%% 以下、之後走完一年的 %d 天，一年後%s，中位數 %s；隨便挑一天只有 %d%%、%s。' % (n['hi'], s365['n'], '每一天都比當時高' if allup else '比當時高的佔這麼多', pc(s365['med'], 0), n['b365']['up'], pc(n['b365']['med'], 0)),
           'Of the %d days at or below %.1f%% with a full year after, %s a year later, median %s (any day: %d%%, %s).' % (s365['n'], n['hi'], 'every one was higher' if allup else 'that share was higher', pc(s365['med'], 0), n['b365']['up'], pc(n['b365']['med'], 0))),
        it('但之後幾個月', 'But in the months after', '90 天後 %d%% 較高' % n['s90']['up'], '%d%% higher at 90 days' % n['s90']['up'], 'neu',
           ('90 天後比當時高的，和隨便一天（%d%%）差不多' % n['b90']['up'] if abs(n['s90']['up'] - n['b90']['up']) <= 5 else '90 天後比當時高的，%s隨便一天（%d%%）' % ('高於' if n['s90']['up'] > n['b90']['up'] else '低於', n['b90']['up'])) + '；每一波跌進這一帶之後，半年內都還再跌過 %d%% 到 %d%%。' % (round(abs(max(dd))), round(abs(min(dd)))),
           'At 90 days that is %s any day (%d%%); after every wave into this zone, price fell another %d%% to %d%% within six months.' % ('about the same as' if abs(n['s90']['up'] - n['b90']['up']) <= 5 else 'better than' if n['s90']['up'] > n['b90']['up'] else 'worse than', n['b90']['up'], round(abs(max(dd))), round(abs(min(dd)))))]

def aviv(L):
    a = L['onchain']['aviv']; r = a['r365']; b = a['base365']
    if a['below']:
        sz = '價格只有活躍投資人平均成本的 %.2f 倍，他們整體在賠已經 %d 天：這是熊市常見的位置，但過去熊市可以在成本下面待一年以上。' % (a['value'], a['run'])
        se = 'Price is only %.2f× the average cost of active investors, who have been underwater as a group for %d days: a typical bear-market spot, though past bear markets stayed below cost for over a year.' % (a['value'], a['run'])
    else:
        hi = a['value'] >= 1.5
        sz = '價格是活躍投資人平均成本的 %.2f 倍，他們整體在賺（已 %d 天）：%s。' % (a['value'], a['run'], '接近過去頂部的水準' if hi else '趨勢在多方這一邊，離過去頂部的水準還遠')
        se = 'Price is %.2f× the average cost of active investors, who have been in profit for %d days: %s.' % (a['value'], a['run'], 'near past-top levels' if hi else 'the trend is on the up side, still far from past-top levels')
    p4 = round(a['pct4'])
    return sz, se, [
        it('平均成本在哪', 'Where their cost is', usd(a['tmm']), usd(a['tmm']), 'neu',
           '活躍投資人（排除很久沒動的幣）的平均成本約在這裡。近 4 年只有 %d%% 的日子，價格對它的倍數比現在低。' % p4 if p4 > 0 else '活躍投資人（排除很久沒動的幣）的平均成本約在這裡。近 4 年沒有一天，價格對它的倍數比現在低。',
           'Roughly what active investors (leaving out long-dormant coins) paid on average. Only %d%% of days in four years had a lower multiple than now.' % p4 if p4 > 0 else 'Roughly what active investors (leaving out long-dormant coins) paid on average. No day in four years had a lower multiple than now.'),
        it('跌破成本之後', 'After falling below cost', '一年後 %d / %d 段漲' % (r['up'], r['n']), 'Up a year on: %d of %d' % (r['up'], r['n']), 'neu',
           '過去價格跌到成本下面 10 天以上有 %d 段，一年後比當時高的有這麼多、中位數 %s；隨便挑一天是 %d%%。單看跌破，%s。' % (r['n'], pc(r['med']), b['up'], '不比平常好' if r['up'] * 100.0 / max(1, r['n']) < b['up'] else '比平常好一些'),
           'Price has spent 10+ days below cost %d times; that many were higher a year later, median %s (any day: %d%%). On its own, a break below is %s.' % (r['n'], pc(r['med']), b['up'], 'no better than usual' if r['up'] * 100.0 / max(1, r['n']) < b['up'] else 'a little better than usual')),
        it('底部一輪比一輪高', 'Each bottom is higher', '%.2f→%.2f 倍' % (a['bottoms'][0]['value'], a['bottoms'][-1]['value']), '%.2f→%.2f×' % (a['bottoms'][0]['value'], a['bottoms'][-1]['value']), 'neu',
           '歷次熊底跌到成本的幾倍：%s，一輪比一輪接近 1，跌得越來越淺。' % '、'.join('%s 年 %.2f' % (x['date'][:4], x['value']) for x in a['bottoms']),
           'Each bear bottom as a multiple of cost: %s. Each is closer to 1 than the last, so the falls are getting shallower.' % ', '.join('%.2f in %s' % (x['value'], x['date'][:4]) for x in a['bottoms']))]

def rrisk(L):
    r = L['onchain']['rrisk']; v = r['value'] * 1000; low = r['pct4'] <= 10; high = r['pct4'] >= 90; e = r['r365']
    if low:
        sz = '儲備風險掉到近 4 年最低的 10%% 以內（第 %d 天）：價格相對老手的信心很便宜，算底部區；但過去掉進這一區之後，結果好壞參半。' % r['run']
        se = 'Reserve risk is in the lowest 10%% of four years (day %d): price is cheap against long-term holders\' conviction, bottom territory, though what followed past stays was mixed.' % r['run']
    elif high:
        sz = '儲備風險在近 4 年最高的 10%：價格跑在老手信心的前面，接近頂部區。'; se = 'Reserve risk is in the top 10% of four years: price is running ahead of long-term holders\' conviction, near top territory.'
    else:
        sz = '儲備風險在近 4 年的中間：不便宜也不貴；這張單看也容易漏掉底部。'; se = 'Reserve risk is mid-range for four years: neither cheap nor rich, and on its own this gauge can miss a bottom.'
    p4, pa = round(r['pct4']), round(r['pct']); mx = max(r['bp4'], key=lambda b: b['pct4'])
    return sz, se, [
        it('現在有多低', 'How low it is', '%.2f‰' % v, '%.2f‰' % v, 'neu', '‰ 是千分之一。近 4 年只有 %d%% 的日子比現在低，拿全部歷史比只有 %d%%。頂部一輪比一輪低，整條線越壓越扁，所以主要和近 4 年比。' % (p4, pa),
           '‰ means per thousand. Only %d%% of days in four years were lower, and %d%% in all history. Tops fall every cycle and squash the line, so it is mainly compared with the last four years.' % (p4, pa)),
        it('歷次底部', 'Past bottoms', ' / '.join('%d' % round(b['pct4']) for b in r['bp4']), ' / '.join('%d' % round(b['pct4']) for b in r['bp4']), 'neu',
           '各輪熊底當時在近 4 年裡有多低（0＝近 4 年最低）。%s 年那次沒有掉進最低的 10%%，單看這張會漏掉底部。' % mx['date'][:4] if mx['pct4'] > 10 else '各輪熊底當時在近 4 年裡有多低（0＝近 4 年最低），每一次都掉進了最低的 10%。',
           'How low each bear bottom was against its own four years at the time (0 = the lowest). The %s bottom never reached the lowest 10%%, so this gauge alone can miss a bottom.' % mx['date'][:4] if mx['pct4'] > 10 else 'How low each bear bottom was against its own four years at the time (0 = the lowest); every one reached the lowest 10%.'),
        it('掉進這一區之後', 'After entering the low zone', '一年後 %d / %d 段漲' % (e['up'], e['n']), 'Up a year on: %d of %d' % (e['up'], e['n']), 'neu',
           '走完一年的 %d 段裡，一年後比當時高的有這麼多，中位數 %s；隨便挑一天是 %d%%。樣本很少。' % (e['n'], pc(e['med']), r['base365']['up']),
           'Of the %d stretches with a full year after, that many were higher a year on, median %s (any day: %d%%). Very few cases.' % (e['n'], pc(e['med']), r['base365']['up']))]

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

P6N = [('MVRV Z（市值對成本）', 'MVRV Z (value vs cost)', 'mvrv_z', '市值比所有幣的平均成本高多少', 'how far market value sits above the average cost of all coins'),
       ('NUPL（帳面賺賠）', 'NUPL (paper profit)', 'nupl', '全體帳面賺賠佔市值的比例', 'all holders\' paper profit or loss as a share of market value'),
       ('Puell（礦工收入）', 'Puell (miner income)', 'puell', '礦工今天的收入是過去一年平均的幾倍', 'miners\' income today against their one-year average')]
def p6(L):
    p = L['cycle']['p6']; vs = sorted(p.values()); hot = sum(1 for v in vs if v >= 80); near = vs[-2] >= 65
    if hot >= 2: sz, se = '頂部三指標有 %d 項到了近 4 年最熱的 20%%：已經進入頂部區，但頂部區不等於最高點。' % hot, '%d of the three top indicators are in the hottest 20%% of four years: this is the top zone, though the top zone is not the exact peak.' % hot
    elif near: sz, se = '頂部三指標有兩項接近頂部門檻：還沒進入頂部區，但已經不遠。', 'Two of the three top indicators are close to the top line: not the top zone yet, but not far.'
    else: sz, se = '頂部三指標都還很冷，離頂部區很遠：這張只說離頂部多遠，不說底部在哪。', 'All three top indicators are cold, far from the top zone. This card only measures distance from a top, not where the bottom is.'
    return sz, se, [it(z, e, '%d' % round(p[k]), '%d' % round(p[k]), 'warn' if p[k] >= 80 else 'neu', '%s；%s。' % (wz, '排名已經到了 80，算熱' if p[k] >= 80 else '排名離 80 還差 %d' % round(80 - p[k])),
                       '%s; %s.' % (we[0].upper() + we[1:], 'its rank has reached 80, so it counts as hot' if p[k] >= 80 else 'its rank is %d short of 80' % round(80 - p[k]))) for z, e, k, wz, we in P6N]

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
    'stage': (['只看兩件事：價格和 200 日均線（過去 200 天收盤的平均），加上「投降」有沒有出現過。', '熊市 → 過渡 → 牛市；牛市成立後鎖定，要在往下走的均線下連 30 天才退回熊市，所以標籤反應慢。', '其他佐證只顯示、不參與判定；這是背景標籤，不指短線方向。'],
              ['Only two things count: price against the 200-day MA (the average close of the past 200 days), and whether a capitulation has happened.', 'Bear → transition → bull. Once bull, it is locked until price spends 30 days under a falling average, so the label is slow.', 'The other checks are shown but decide nothing. It is a background label, not a short-term direction.']),
    'rup': (['還沒賣的幣帳面上賺的錢，佔市值的百分比（只算賺的，不扣賠的）。', '35% 是歷次熊市尾聲附近的地板，35–37.5% 是近地板區。', '跌到這一帶之後一年多半比較高，但進來後幾個月內常再跌一段。'],
            ['Paper profit on unsold coins as a share of market cap (gains only, losses not netted).', '35% has been the floor near the end of past bear markets; 35–37.5% is the near-floor zone.', 'A year after reaching this zone price was usually higher, but it often fell further in the months after.']),
    'p6': (['三個找頂部的指標，各自和近 4 年比排名：0 最冷、100 最熱，80 以上算熱。', '任兩項到 80 以上，才算進入頂部區。', '只看估值，不看時間；很冷不代表已經到底。'],
           ['Three top-finding indicators, each ranked against the last four years: 0 is coldest, 100 hottest, 80 and above is hot.', 'Any two at 80 or above count as the top zone.', 'Valuation only, not timing; cold does not mean the bottom is in.']),
    'pi': (['111 日均線 ÷（350 日均線 × 2）；到 1 代表短期均線追上長期均線的兩倍。', '過去幾次到 1 都在頂部附近，但每一輪的頂部不一定都會碰到。', '只用價格，和鏈上指標一起看。'],
           ['111-day MA ÷ (350-day MA × 2); 1 means the short average has caught up with twice the long one.', 'Past touches of 1 came near tops, but not every top has reached it.', 'It uses price alone; read it with the on-chain gauges.']),
    'hashr': (['算力 30 日均 ÷ 60 日均；低於 1 代表算力在下降，礦工在投降。', '原版買點（投降結束後價格轉強）2021 年以前很準，2021 年以後和隨便一天差不多。', '只看礦工，和其他指標一起看。'],
              ['30-day ÷ 60-day average hashrate; below 1 means hashrate is falling and miners are capitulating.', 'The original buy (price turning up after capitulation) worked well before 2021; since then it has done about as well as any day.', 'It only covers miners; read it with the rest.']),
    'cyccmp': (['每條線是一輪頂部之後每天的收盤，和那一輪頂部比跌了多少。', '橫軸是頂部後第幾天，可以直接和前幾輪同一天比。', '只有三輪樣本，這輪的走法不一定一樣。'],
               ['Each line is the daily close after a cycle top, as a drop from that top.', 'The x-axis is days since the top, so today lines up with the same day in past cycles.', 'Only three past cycles; this one need not follow them.']),
}
