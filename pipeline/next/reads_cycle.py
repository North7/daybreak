# -*- coding: utf-8 -*-
"""週期頁的讀數（2026-11-17，取代舊版抽來的讀數；規則見 reads.py）。每個函式回傳 (一句結論中, 英, [最多三條事實])"""
import datetime as dt
from reads import sg, pc, pu, n0, sn0, wan, kb, md, ymd, ym, ord_en, it, M, mde, ymde, yme, MON

SG = [('深夜', 'Deep night', '底部區', 'bottom zone'), ('入夜', 'Nightfall', '下跌', 'falling'), ('破曉', 'Daybreak', '初升', 'early rise'), ('白晝', 'Daylight', '上升', 'rising'), ('黃昏', 'Dusk', '過熱', 'overheated')]
HEAT = dict(lnupl=('長期持有者的帳面獲利（NUPL）', 'long-term holders\' paper profit (NUPL)'), rup=('帳面獲利佔市值', 'paper profit as a share of market cap'), pl=('價格對長期趨勢價', 'price against the long-run trend'), rr=('儲備風險', 'reserve risk'), mvz=('市值對成本（MVRV-Z）', 'value vs cost (MVRV-Z)'))
STN = {'熊市': 'Bear market', '轉換期': 'Transition', '牛市': 'Bull market'}
EVN = dict(mom12='12-month momentum', mvrv1y='MVRV vs its one-year mean', rcgrowth='Capital inflow', xs90='Exchange Balance', sth='Short-term holder cost', tmm='STH cost vs true market mean')
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

def cyccmp(L):   # 2026-11-25 改寫（WRITING.md）：先講這輪跌得比前幾輪淺、前幾輪的時間表套不上，數字少放
    c = L['cycle']['cycle_cmp']; cur = next(x for x in c['cycles'] if x['now']); prev = [x for x in c['cycles'] if not x['now']]; bk = [x['back_day'] for x in prev if x.get('back_day')]
    a = cur['at']['pct']; pm, pn = max(x['at']['pct'] for x in prev), min(x['at']['pct'] for x in prev); sh = a > pm + 10
    if sh:
        sz = '這一輪從頂部跌了 %d%%，前幾輪同一時間都跌得深得多：這輪跌得淺，前幾輪「頂部一年後見底、再花兩三年回到頂部價」的時間表不能直接套。' % round(abs(a))
        se = 'This cycle is %d%% off its top, while past cycles were far deeper by the same day: it has fallen less, so the old timetable of a bottom a year after the top and two or three more years back to the top does not simply carry over.' % round(abs(a))
    elif a < pn - 10:
        sz = '這一輪從頂部跌了 %d%%，比前幾輪同一時間都深：這輪跌得比以前重，前幾輪的時間表只能當參考。' % round(abs(a))
        se = 'This cycle is %d%% off its top, deeper than past cycles by the same day: it has fallen harder than before, so the old timetable is a guide at most.' % round(abs(a))
    else:
        sz = '這一輪從頂部跌了 %d%%，和前幾輪同一時間差不多：前幾輪的時間表可以參考，但只有三輪可以比。' % round(abs(a))
        se = 'This cycle is %d%% off its top, about where past cycles were by the same day: the old timetable is a guide, but there are only three to compare.' % round(abs(a))
    lw = [abs(x['low']['pct']) for x in prev]; ld = [x['low']['day'] for x in prev]; yrz = '大約在頂部一年後' if 300 <= min(ld) and max(ld) <= 450 else '在頂部後第 %d–%d 天' % (min(ld), max(ld)); yre = 'about a year after the top' if 300 <= min(ld) and max(ld) <= 450 else '%d–%d days after the top' % (min(ld), max(ld))
    early = cur['low']['day'] < min(ld) and cur['low']['pct'] > -min(lw) + 10
    return sz, se, [
        it('和前幾輪同一天比', 'Versus past cycles on this day', pc(a), pc(a), 'neu', '這輪的頂部在 %s（%s），今天是頂部後第 %d 天；前幾輪走到同一天，都比頂部低 %.0f–%.0f%%。' % (ymd(cur['top']), usd(cur['top_price']), c['day_now'], abs(pm), abs(pn)),
           'This cycle topped on %s at %s; today is day %d after it. Past cycles on the same day were %.0f–%.0f%% below their tops.' % (ymde(cur['top']), usd(cur['top_price']), c['day_now'], abs(pm), abs(pn))),
        it('這輪的低點', "This cycle's low", pc(cur['low']['pct']), pc(cur['low']['pct']), 'neu',
           '到目前最深是頂部後第 %d 天（%s）。前幾輪最深跌掉 %.0f–%.0f%%，%s才見底%s；如果之後跌破這個低點，這輪的底就要往後改。' % (cur['low']['day'], ym(cur['low']['date']), min(lw), max(lw), yrz, '，這輪的低點來得早、也淺得多' if early else ''),
           'The deepest point so far came on day %d (%s). Past cycles fell %.0f–%.0f%% at worst and bottomed %s%s. If price breaks below this low, the cycle bottom moves later.' % (cur['low']['day'], yme(cur['low']['date']), min(lw), max(lw), yre, '; this low came sooner and was far shallower' if early else '')),
        it('回到頂部價要多久', 'Time to get back to the top', '%.1f–%.1f 年' % (min(bk) / 365.0, max(bk) / 365.0), '%.1f–%.1f years' % (min(bk) / 365.0, max(bk) / 365.0), 'neu',
           '前幾輪從頂部算起，要這麼久才重新站回頂部價。%s' % ('這輪跌得淺，不一定要那麼久，也不保證比較快。' if sh else '這輪不一定照走。'),
           'How long past cycles took, counting from the top, to close above it again. %s' % ('This one fell less, so it may not take that long, but there is no guarantee it will be faster.' if sh else 'This cycle need not follow.'))]

def capeff(L):   # 2026-11-25 改寫：先解釋已實現市值，一串倍數只留頭尾
    c = L['onchain']['capeff']; cy = c['cycles']; cu = c['cur']; sm = [x['same'] for x in cy]
    mm = lambda m: ('%.0f' % m) if m >= 20 else ('%.1f' % m)
    lo, hi = min(s['mult'] for s in sm), max(s['mult'] for s in sm); flat = abs(cu['mult'] - 1) < .1
    pz = '比前幾輪同一時間都慢' if cu['mult'] < lo else '比前幾輪同一時間都快' if cu['mult'] > hi else '和前幾輪同一時間差不多'
    pe = 'slower than every past cycle at this point' if cu['mult'] < lo else 'faster than every past cycle at this point' if cu['mult'] > hi else 'in line with past cycles at this point'
    sz = '這一輪從底部到現在，%s，%s；而且比特幣越大，每一輪能漲的倍數越小，這張只是背景。' % (('價格幾乎沒動（%.2f 倍）' if flat else '價格是底部的 %.2f 倍') % cu['mult'], pz)
    se = 'Since this cycle\'s bottom, %s, %s. And the bigger Bitcoin gets, the smaller each cycle\'s run: this chart is context only.' % (('price has barely moved (%.2f×)' if flat else 'price has reached %.2f× the bottom') % cu['mult'], pe)
    more = cu['add_b'] > max(s['add_b'] for s in sm) and cu['mult'] < lo
    return sz, se, [
        it('每輪能漲的倍數', 'How far each cycle ran', '%s×' % mm(cy[-1]['mult']), '%s×' % mm(cy[-1]['mult']), 'neu',
           '從熊市底部漲到牛市頂部的倍數一輪比一輪小：最早一輪 %s 倍，上一輪只剩這麼多；流進來的錢卻一輪比一輪多，上一輪約 %s 億美元。' % (mm(cy[0]['mult']), n0(cy[-1]['add_b'] * 10)),
           'The climb from bear bottom to bull top shrinks every cycle: %s× in the first, only this much in the last, even though more money came in each time (about $%sB last cycle).' % (mm(cy[0]['mult']), n0(cy[-1]['add_b']))),
        it('前幾輪同一時間', 'Past cycles at this point', '%.2f–%.2f×' % (lo, hi), '%.2f–%.2f×' % (lo, hi), 'neu',
           ('前幾輪從底部起算 %d 天時，價格已經是底部的這麼多倍，已實現市值卻幾乎沒增加；這一輪多流進 %s，價格反而漲得比較少。' % (cu['days'], yiz(abs(cu['add_b'])).lstrip('+'))) if more else
           ('前幾輪從底部起算 %d 天時，價格是底部的這麼多倍；同一時間已實現市值的變化在 %s 到 %s 之間。' % (cu['days'], yiz(min(s['add_b'] for s in sm)), yiz(max(s['add_b'] for s in sm)))),
           ('%d days after their bottoms, past cycles were already this many times higher, with almost no realized cap added; this cycle has taken in %s and risen less.' % (cu['days'], bb(abs(cu['add_b'])))) if more else
           ('%d days after their bottoms, past cycles were this many times higher; realized cap changed by %s to %s over the same stretch.' % (cu['days'], bbs(min(s['add_b'] for s in sm)), bbs(max(s['add_b'] for s in sm))))),
        it('每流入 1 美元', 'Per $1 that came in', '$%.1f' % cy[-1]['lev'], '$%.1f' % cy[-1]['lev'], 'neu',
           '到頂部時，每流進 1 美元，市值增加多少：最早一輪 $%.1f，上一輪剩這麼多，同樣的錢推得越來越少。' % cy[0]['lev'],
           'At each top, how much market cap every $1 in had added: $%.1f in the first cycle, this much in the last. The same money moves price less and less.' % cy[0]['lev'])]

PN = {'直接修復': 'direct recovery', '淺回檔': 'shallow pullback', '基準雙底': 'base-case double bottom', '延後新低': 'delayed new low'}
PBAND = .12   # 同 pipeline/path_review.py 的 BAND：fan 的上下緣是四種走法今天的最低／最高值再往外 12%
def path(L):   # 2026-11-25 改寫：先說現價在四種走法的哪裡，再講長期；權重白話
    import re
    m = L['cycle']['model']; w = m['weights']; t = m['top_model']; px = L['price']['bar']['c']; f = m.get('fan') or {}; top = max(w, key=w.get)
    lo = f['lo'] / (1 - PBAND) if f.get('lo') else None; hi = f['hi'] / (1 + PBAND) if f.get('hi') else None
    hiall = all(max(n[2] for n in ns) > L['cycle']['tops'][-1][1] for ns in m['nodes'].values())
    tz = '長期四種都還走向比上一輪更高的頂部，中位數約 %s' % usd(t['median']) if hiall else '頂部模型估計下一輪頂部的中位數約 %s' % usd(t['median'])
    te = 'in the long run all four still head for a higher top than last cycle, median about %s' % usd(t['median']) if hiall else 'the top model puts the next top\'s median at about %s' % usd(t['median'])
    if lo and px < lo:
        sz = '現在價格掉到四種走法最低那條的下方：短期比我們的模型預期的弱；%s。' % tz; se = 'Price has dropped below the lowest of the four paths: weaker than our model expected in the near term; %s.' % te
    elif hi and px > hi:
        sz = '現在價格高過四種走法最高的那條：短期比我們的模型預期的強；%s。' % tz; se = 'Price is above the highest of the four paths: stronger than our model expected in the near term; %s.' % te
    else:
        sz = '價格還在四種走法的範圍裡，「%s」的機會最大；%s。' % (top, tz); se = 'Price is still inside the four paths, with %s the most likely; %s.' % (PN.get(top, top), te)
    kr = next((r for r in reversed(m.get('reviews') or []) if r.get('kind') == 'kill'), None) if w.get('直接修復') == 0 else None
    kn = re.sub(r'[^\d,]', '', kr['why']) if kr else ''
    kz = ('「直接修復」在 %s 收盤跌破 $%s 時判定失效，權重歸零。' % (md(kr['date']), kn)) if kr else ''; ke = (' Direct recovery was ruled out on %s, when the close fell below $%s.' % (mde(kr['date']), kn)) if kr else ''
    run = f.get('run') or 0; need = f.get('need') or 10
    if lo and px < lo: gz = '現在收盤比最低那條低約 %d%%%s。' % (round((1 - px / lo) * 100), '，超出範圍已經連 %d 天' % run if run else ''); ge = ' The close is about %d%% below the lowest path%s.' % (round((1 - px / lo) * 100), ', outside the range for %d days running' % run if run else '')
    elif hi and px > hi: gz = '現在收盤比最高那條高約 %d%%%s。' % (round((px / hi - 1) * 100), '，超出範圍已經連 %d 天' % run if run else ''); ge = ' The close is about %d%% above the highest path%s.' % (round((px / hi - 1) * 100), ', outside the range for %d days running' % run if run else '')
    else: gz = '收盤連 %d 天超出四種走法的範圍 %d%% 以上，才重畫走法本身。' % (need, PBAND * 100); ge = ' Only %d straight closes more than %d%% outside all four paths would get the paths themselves redrawn.' % (need, PBAND * 100)
    return sz, se, [
        it('哪種走法機會最大', 'Most likely path', '%s %d%%' % (top, w[top]), '%s %d%%' % (PN.get(top, top).capitalize(), w[top]), 'neu',
           '權重是我們估計每種走法發生的機會，四種加起來 100%%。其他三種：%s。%s' % ('、'.join('%s %d%%' % (k, v) for k, v in w.items() if k != top), kz),
           'The weights are our estimate of how likely each path is; the four add up to 100%%. The other three: %s.%s' % (', '.join('%s %d%%' % (PN.get(k, k), v) for k, v in w.items() if k != top), ke)),
        it('下一輪頂部', 'Next top', usd(t['median']), usd(t['median']), 'neu', '頂部模型估計下一輪頂部有 80%% 的機會落在 %s–%s，時間在 %s；這是模型的推估，不是目標價。' % (usd(t['p10']), usd(t['p90']), t['timing']),
           'The top model gives an 80%% chance that the next top lands between %s and %s, in %s. It is a model estimate, not a price target.' % (usd(t['p10']), usd(t['p90']), t.get('timing_en') or t['timing'])),
        it('下次調整', 'Next re-check', md(m['next_review']), mde(m['next_review']), 'neu', '每個月底用收盤調整一次權重：收盤越接近哪一種走法，那種的權重就調高。%s' % gz,
           'Weights are adjusted at each month-end close: the closer the close is to a path, the more its weight goes up.%s' % ge)]

def long(L):   # 2026-11-25 改寫：減半先解釋；只是背景
    cy = L['cycle']; tp = cy['tops'][-1]; hv = cy['halvings']; d = L['price']['monthly']['date']; px = L['price']['bar']['c']; hd = days(hv[-1], d)
    lag = [days(next(h for h in reversed(hv) if h < t[0]), t[0]) for t in cy['tops']]; nm = round(days(d, cy['next_halving_est']) / 30.44)
    dn_ = abs(px / tp[1] - 1) * 100; up_ = px > tp[1]
    if up_:
        sz = '價格比上一輪頂部高 %.0f%%%s；這張只是背景。' % (dn_, '，離下一次減半還有約 %d 個月' % nm if nm > 0 else ''); se = 'Price is %.0f%% above the last cycle top%s. This chart is context only.' % (dn_, ', about %d months before the next halving' % nm if nm > 0 else '')
    else:
        sz = '價格比上一輪頂部低 %.0f%%：照過去的節奏，頂部已經過了%s；這張只是背景。' % (dn_, '，離下一次減半還有約 %d 個月' % nm if nm > 0 else ''); se = 'Price is %.0f%% below the last cycle top: on the old rhythm the top is behind us%s. This chart is context only.' % (dn_, ', with the next halving about %d months away' % nm if nm > 0 else '')
    a, b = min(lag[:-1]), max(lag[:-1]); fit = '這輪的時間點和以前差不多' if a <= lag[-1] <= b else '這輪來得比以前早' if lag[-1] < a else '這輪來得比以前晚'
    fite = 'so this one came on the usual schedule' if a <= lag[-1] <= b else 'so this one came earlier' if lag[-1] < a else 'so this one came later'
    return sz, se, [
        it('上一輪頂部', 'Last cycle top', usd(tp[1]), usd(tp[1]), 'neu', '%s 見頂，是減半後 %d 天；前幾輪頂部在減半後 %d–%d 天，%s。' % (ymd(tp[0]), lag[-1], a, b, fit),
           'It came on %s, %d days after the halving; earlier tops came %d–%d days after, %s.' % (ymde(tp[0]), lag[-1], a, b, fite)),
        it('距離上次減半', 'Since the last halving', '%s 天' % n0(hd), '%s days' % n0(hd), 'neu', '減半是大約每四年一次、礦工新挖出的比特幣減少一半。上次在 %s，下一次估計在 %s。' % (ymd(hv[-1]), ym(cy['next_halving_est'])),
           'A halving cuts the new bitcoin paid to miners in half, about every four years. The last was on %s; the next is estimated for %s.' % (ymde(hv[-1]), yme(cy['next_halving_est'])))]

def mon(L):   # 2026-11-25 改寫：只有十幾個樣本，季節性不能當方向
    m = L['price']['monthly']; c = m['cur']; mo = int(m['month'][5:7]); nm = '%d 月' % mo; ne = MONF[mo - 1]
    lz = '多半上漲' if c['up'] * 2 > c['n'] else '多半下跌' if c['up'] * 2 < c['n'] else '漲跌各半'; le = 'mostly rose' if c['up'] * 2 > c['n'] else 'mostly fell' if c['up'] * 2 < c['n'] else 'split evenly'
    sz = '%s到目前 %s；過去的 %s%s，但樣本很少，月份的規律不能拿來猜這個月會怎麼收。' % (nm, pc(m['mtd']), nm, lz)
    se = '%s so far: %s. Past %ss %s, but with so few years the calendar cannot tell you how this month will end.' % (ne, pc(m['mtd']), ne, le)
    return sz, se, [
        it('這個月到目前', 'This month so far', pc(m['mtd']), pc(m['mtd']), 'up' if m['mtd'] > 0 else 'down', '從上個月底的 %s 算到 %s，月底前還會變；今年到目前 %s。' % (usd(m['base']), md(m['date']), pc(m['ytd'])),
           'From last month\'s close of %s to %s; it can still change before month-end. Year to date: %s.' % (usd(m['base']), mde(m['date']), pc(m['ytd']))),
        it('過去的 %s' % nm, 'Past %ss' % ne, '%d 年裡 %d 年漲' % (c['n'], c['up']), '%d of %d up' % (c['up'], c['n']), 'neu',
           '中位數 %s（一半的年份比它好、一半比它差）；好壞差很多，最好的 %d 年 %s、最差的 %d 年 %s。' % (pc(c['med']), c['best_y'], pc(c['best'], 0), c['worst_y'], pc(c['worst'], 0)),
           'Median %s (half the years did better, half worse). The spread is wide, from %s in %d to %s in %d.' % (pc(c['med']), pc(c['best'], 0), c['best_y'], pc(c['worst'], 0), c['worst_y']))]

CARDS = dict(dawn=dawn, stage=stage, regime=regime, hnupl=hnupl, rup=rup, aviv=aviv, rrisk=rrisk, pl=pl, p6=p6, p20=p20, pi=pi, tmh=tmh, lthloss=lthloss, npl365=npl365, agecost=agecost, hashr=hashr, cyccmp=cyccmp, capeff=capeff, path=path, long=long, mon=mon)
# 舊版沒有「怎麼讀」的卡片，這裡補上（中、英各三行內）
HOWX = {
    'stage': (['只看兩件事：價格和 200 日均線（過去 200 天收盤的平均），加上「投降」有沒有出現過。', '熊市 → 過渡 → 牛市；牛市成立後鎖定，要在往下走的均線下連 30 天才退回熊市，所以標籤反應慢。', '其他佐證只顯示、不參與判定；這是背景標籤，不指短線方向。'],
              ['Only two things count: price against the 200-day MA (the average close of the past 200 days), and whether a capitulation has happened.', 'Bear → transition → bull. Once bull, it is locked until price spends 30 days under a falling average, so the label is slow.', 'The other checks are shown but decide nothing. It is a background label, not a short-term direction.']),
    'rup': (['還沒賣的幣帳面上賺的錢，佔市值的百分比（只算賺的，不扣賠的）。', '35% 是歷次熊市尾聲附近的地板，35–37.5% 是近地板區。', '跌到這一帶之後一年多半比較高，但進來後幾個月內常再跌一段。'],
            ['Paper profit on unsold coins as a share of market cap (gains only, losses not netted).', '35% has been the floor near the end of past bear markets; 35–37.5% is the near-floor zone.', 'A year after reaching this zone price was usually higher, but it often fell further in the months after.']),
    'p6': (['三個找頂部的指標，各自和近 4 年比排名：0 最冷、100 最熱，80 以上算熱。', '任兩項到 80 以上，才算進入頂部區。', '只看估值，不看時間；很冷不代表已經到底。'],
           ['Three top-finding indicators, each ranked against the last four years: 0 is coldest, 100 hottest, 80 and above is hot.', 'Any two at 80 or above count as the top zone.', 'Valuation only, not timing; cold does not mean the bottom is in.']),
    'pi': (['圖上：大數字和橫條是 111 日均線（約四個月的平均價）÷ 350 日均線的兩倍（約一年平均價的兩倍），橫條上的刻度是 1。', '怎麼看：越接近 1，代表價格幾個月內漲得越遠超過一年的平均；2013、2017、2021 年的頂部都在碰到 1 的前後不久。', '小心：2025 年的頂部沒碰到 1，頂部一輪比一輪溫和，以後可能更難碰到；它只看價格，和鏈上指標一起看。'],
           ['On the chart: the big number and bar are the 111-day average (about four months) ÷ twice the 350-day average (about twice the one-year average); the tick on the bar is 1.', 'Reading it: the closer to 1, the further price has run above its yearly average within months; the 2013, 2017 and 2021 tops all came soon around a touch of 1.', 'Caveat: the 2025 top never reached 1, and as tops get milder it may get harder to reach; it uses price alone, so read it with the on-chain gauges.']),
    'hashr': (['圖上：上格是價格，圓圈是 Capriole 原版訊號那天（一年後較高是綠、較低是紅、還不到一年另一色）；下格是算力的 30 日和 60 日平均，淡紅底是投降期。', '怎麼看：30 日平均跌到 60 日平均下面，代表有礦工在關機；原版訊號是投降結束後、價格開始轉強的那天。2021 年以前之後一年都較高，2021 年以後和隨便一天差不多。', '小心：礦機效率、託管和算力出租改變了礦工關機的原因；它只看礦工，和其他指標一起看。'],
              ['On the chart: price on top, with circles on the days of Capriole\'s original signal (green if higher a year later, red if lower, another colour if under a year); below, the 30- and 60-day hashrate averages, with capitulation shaded red.', 'Reading it: the 30-day average falling below the 60-day means miners are switching off; the original signal is the day price turns up after capitulation ends. Before 2021 price was always higher a year later; since then it has done about as well as any day.', 'Caveat: rig efficiency, hosting and hashrate rental have changed why miners switch off; it only covers miners, so read it with the rest.']),
    'cyccmp': (['每條線是一輪：從那一輪的頂部算起，之後每天的收盤比頂部低多少。', '找到「今天」那條直線，看這輪的線比前幾輪高還是低：比較高就是跌得比較淺。', '只有三輪可以比；這輪跌得淺、形狀不像，前幾輪的時間表不能直接套。'],
               ['Each line is one cycle: how far every close after its top sat below that top.', 'Find the "Today" line and see whether this cycle sits above or below the others: higher means a shallower fall.', 'There are only three cycles to compare, and this one has fallen less and looks different, so their timetable does not simply carry over.']),
}
