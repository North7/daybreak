# -*- coding: utf-8 -*-
"""「槓桿」這一頁的資料：槓桿和情緒擠不擠。四組：槓桿、波動、選擇權、情緒。
顏色照現有網站 assets/app.js 每張圖自己的畫法（drawFh、drawOih、drawLsa、drawLqv、drawIvt、drawPr、drawFng、drawWiki，
以及 V.deriv.after 裡的 c-vol、c-basis、c-oi）：s1→c3、s4／warn→c5、up→up、down→dn、ink-2→ink、ink-3→k2。
履約價分布、Gamma、清算價位、掛單簿在「價位」那一頁，這裡不重複。"""


def build(L, N, E, dn, X):
    d = L.get('deriv') or {}; fw = L.get('flows') or {}; vz = d.get('viz') or {}
    ser = lambda c, **k: dict(c=c, **k)
    row = lambda zh, en, v, **k: dict(zh=zh, en=en, v=v, **k)
    R = lambda v, n=2: None if v is None else round(v, n)
    sg = lambda v, n=1: ('%+.*f' % (n, v)).replace('-', '−')
    ymd = lambda s: s.replace('-', '/'); ym = lambda s: s[:7].replace('-', '/'); n0 = lambda v: format(int(round(v)), ',')
    has = lambda x, key='rows': bool(x and x.get(key))
    clip = lambda v: round(max(0, min(100, v)), 1)

    def na(k, zh, en, path, src, wz, we):   # 資料沒來：說清楚缺的是哪一份、這張圖本來要畫什麼
        X[k] = dict(k=k, zh=zh, en=en, na=dict(zh='今天沒有資料：%s（來源 %s）是空的。%s' % (path, src, wz), en='No data today: %s (source: %s) is empty. %s' % (path, src, we)))

    def near(zs, v):   # 狀態列在區間外時只報「離第一個區間還差多少」，所以把離現在比較近的那個區間排前面
        edge = lambda z: min(abs(v - e) for e in (z['lo'], z['hi']) if e is not None)
        return sorted(zs, key=edge) if v is not None else zs

    # ══ 槓桿 ══
    # 資金費率歷史（drawFh）：一條線，零以上綠、零以下橘紅；30% 虛線是 warn 色
    x = d.get('fund_hist')
    if has(x):
        th = (x.get('hot') or {}).get('th') or 30; hs_ = (x.get('hot') or {}).get('st') or {}
        X['fh'] = dict(k='fh', zh='資金費率歷史', en='Funding rate history', hz='7 日平均，年化', he='7-day average, annualized', f='pct1', rng=365, rows=x['rows'], p=1,
          ser=[ser(2, zh='資金費率 7 日平均', en='Funding, 7-day average', t='sign', base=0, w=1.4)],
          refs=[dict(v=th, col='c5', zh='%d%%：做多的槓桿很擠' % th, en='%d%%: leveraged longs are crowded' % th)],
          leg=[['up', '正值：多方付費給空方', 'Positive: longs pay shorts', 'line'], ['dn', '負值：空方付費給多方', 'Negative: shorts pay longs', 'line']],
          dz='%d 家交易所永續合約的資金費率，用未平倉量加權、換成年化，再取 7 日平均。正值是多方付費給空方，越高代表做多的槓桿越擠；轉負代表槓桿偏空。現在高於 %s 以來 %d%% 的日子，虛線是 %d%%%s。' % (
              len(x.get('venues') or []), ym(x['from_']), x['pct'], th, ('，過去升到這裡 %d 次，90 天後有 %d 次上漲' % (hs_['n'], hs_['up'])) if hs_.get('n') else ''),
          de='Funding on perpetuals across %d venues, weighted by open interest, annualized and averaged over 7 days. Positive means longs pay shorts, and the higher it is, the more crowded leveraged longs are; negative means leverage leans short. It is now higher than on %d%% of days since %s; the dashed line is %d%%%s.' % (
              len(x.get('venues') or []), x['pct'], ym(x['from_']), th, (', reached %d times before, with price higher 90 days later in %d of them' % (hs_['n'], hs_['up'])) if hs_.get('n') else ''))
    else:
        na('fh', '資金費率歷史', 'Funding rate history', 'deriv.fund_hist', 'Coinalyze', '這張圖畫多家永續合約以未平倉加權的資金費率，7 日平均、年化。', 'This chart shows open-interest-weighted perpetual funding, 7-day average, annualized.')

    # 期貨基差曲線（V.deriv.after 的 c-basis）：一條 s4 色的線。橫軸是離到期的天數，不是日期
    bs = vz.get('basis') or {}; cv = bs.get('curve') or (d.get('deriv') or {}).get('basis_curve'); dd = d.get('deriv') or {}
    if cv:
        ys = [q[1] for q in cv]; med = bs.get('median', dd.get('basis_median')); fa = bs.get('funding', dd.get('funding_ann'))
        lvl = ('水準偏高，槓桿偏熱', 'which is high: leverage is running hot') if max(ys) > 15 else ('水準很低，做多的需求冷淡', 'which is very low: little demand to be long') if min(ys) < 3 else ('在常態範圍內', 'inside the normal range')
        X['basis'] = dict(k='basis', zh='期貨基差曲線', en='Futures basis curve', hz='各到期日年化基差的中位數', he='Median annualized basis across expiries', hs=dict(v=med if med is not None else sorted(ys)[len(ys) // 2], f='p2'),
          xy=dict(xk='dte', f='p2', series=[dict(zh='年化基差', en='Basis', col='c5', w=2.2, rows=cv)], ref=dict(v=15, zh='15%：槓桿偏熱', en='15%: leverage running hot')),
          dz='期貨比現貨貴多少，換成年化；橫軸是離到期還有幾天（不含 7 天內到期的）。基差高代表大家願意多付錢用期貨做多：3–15%% 算常態，超過 15%% 是槓桿偏熱，低於 3%% 是做多的需求冷淡。現在各到期日在 %.1f–%.1f%%，%s%s。' % (
              min(ys), max(ys), lvl[0], ('；永續資金費率年化 %s%%' % sg(fa)) if fa is not None else ''),
          de='How much futures trade above spot, annualized; the horizontal axis is days to expiry (expiries within 7 days are left out). A high basis means traders pay up to be long through futures: 3–15%% is normal, above 15%% is hot, below 3%% is cold. Expiries now sit at %.1f–%.1f%%, %s%s.' % (
              min(ys), max(ys), lvl[1], ('; perpetual funding is %s%% annualized' % sg(fa)) if fa is not None else ''))
    else:
        na('basis', '期貨基差曲線', 'Futures basis curve', 'deriv.viz.basis.curve', 'Deribit', '這張圖畫各到期日期貨相對現貨的年化溢價。', 'This chart shows the annualized premium of futures over spot for each expiry.')

    # 全市場未平倉量（drawOih）：一條 s4 色的線加面積
    x = d.get('oi_hist')
    if has(x):
        pu = (x.get('px30') or 0) >= 0; ou = (x.get('chg30') or 0) >= 0
        K = {(False, True): ('價格跌、未平倉增加，代表有人逆勢開新倉，槓桿在堆，之後容易有一邊被清算', 'Price down with open interest up means new positions against the move: leverage is building, and one side tends to get liquidated later'),
             (True, True): ('價格漲、未平倉也增加，代表新資金用槓桿在追，漲勢有一部分靠槓桿撐', 'Price up with open interest up means new money is chasing with leverage, so part of the rally rests on it'),
             (False, False): ('價格跌、未平倉減少，代表多單在平倉或被清算，槓桿在退', 'Price down with open interest down means longs are closing or being liquidated: leverage is unwinding'),
             (True, False): ('價格漲、未平倉減少，代表是空單回補在推，槓桿在退', 'Price up with open interest down means short covering is driving it: leverage is unwinding')}[(pu, ou)]
        X['oih'] = dict(k='oih', zh='全市場未平倉量', en='Total open interest', hz='永續合約未平倉合計', he='Perpetual open interest, total', f='btc0', rng=365, rows=[[r[0], r[1], None if r[2] is None else int(round(r[2] * 1000))] for r in x['rows']], p=1,
          ser=[ser(2, zh='永續未平倉', en='Perpetual open interest', col='c5', fill=1, w=1.5)],
          dz='%d 家交易所共 %d 個 BTC 永續合約還沒平倉的部位，換算成顆，現在高於 %s 以來 %d%% 的日子。要和價格一起看：近 30 天價格 %s%%、未平倉 %s%%，%s。' % (
              len(x.get('exch') or []), x.get('n') or 0, ym(x['from_']), x['pct'], sg(x['px30']), sg(x['chg30']), K[0]),
          de='Open positions in %d BTC perpetual contracts on %d venues, in BTC, now higher than on %d%% of days since %s. Read it against price: over 30 days price is %s%% and open interest %s%%. %s.' % (
              x.get('n') or 0, len(x.get('exch') or []), x['pct'], ym(x['from_']), sg(x['px30']), sg(x['chg30']), K[1]))
    else:
        na('oih', '全市場未平倉量', 'Total open interest', 'deriv.oi_hist', 'Coinalyze', '這張圖畫各交易所 BTC 永續合約未平倉量的合計（顆）。', 'This chart shows total open interest in BTC perpetual contracts across venues, in BTC.')

    # 多空帳戶比（drawLsa）：Binance s1、Bybit s4；Binance 前 10% 是紅帶、後 10% 是綠帶；50% 灰線
    x = d.get('ls_acct')
    if has(x):
        p90, p10 = x['p90'], x['p10']
        zs = near([dict(lo=p90, hi=None, col='dn', zh='在最高的一成：做多的帳戶很擠', en='In the top 10%: long accounts are crowded', nz='最高一成的門檻', ne='the top-10% line'),
                   dict(lo=None, hi=p10, col='up', zh='在最低的一成：做多的帳戶很少', en='In the bottom 10%: few accounts are long', nz='最低一成的門檻', ne='the bottom-10% line')], x.get('binance'))
        X['lsa'] = dict(k='lsa', zh='多空帳戶比', en='Long/short account ratio', hz='Binance 持多單的帳戶占比', he='Share of Binance accounts that are long', f='p1', rng=365, rows=x['rows'], p=1, hero=1,
          ser=[ser(3, zh='Bybit', en='Bybit', col='c5', w=1.2), ser(2, zh='Binance', en='Binance', col='c3', w=1.5)],
          refs=[dict(v=50, col='k2', zh='50%', en='50%')], zones=zs,
          leg=[['dn', 'Binance 最高的一成（≥ %.1f%%）' % p90, 'Binance top 10%% (≥ %.1f%%)' % p90, 'box'], ['up', 'Binance 最低的一成（≤ %.1f%%）' % p10, 'Binance bottom 10%% (≤ %.1f%%)' % p10, 'box']],
          dz='BTCUSDT 永續合約上，持多單的帳戶佔全部有部位帳戶的比例。算的是帳戶數、不是部位大小，比較像散戶的情緒，常當反向參考：大家都做多的時候，容易往下洗。紅色帶和綠色帶是 Binance 在 %s 以來最高和最低的一成。' % ym(x['from_']),
          de='The share of accounts holding longs among all accounts with a BTCUSDT perpetual position. It counts accounts, not position size, so it reads like retail sentiment and is used as a contrarian gauge: when everyone is long, price tends to flush them. The red and green bands are the top and bottom tenth of Binance readings since %s.' % ym(x['from_']))
    else:
        na('lsa', '多空帳戶比', 'Long/short account ratio', 'deriv.ls_acct', 'Coinalyze', '這張圖畫 Binance 和 Bybit 上持多單的帳戶占比。', 'This chart shows the share of accounts that are long on Binance and Bybit.')

    # 每日多空清算量（drawLqv）：空單被清算往上、綠；多單被清算往下、橘紅；平方根刻度；圓圈是清算最多的幾天
    x = d.get('liq_vol')
    if has(x):
        rw = x['rows']; out = []; j = 0; sl = ss = 0.0
        for i, r in enumerate(rw):   # 近 30 天多單佔清算的比例（網站只給最新一個數字 d30.share，這裡照同樣的算法往回算成一條線）
            ss += r[2] or 0; sl += -(r[3] or 0)
            while rw[j][0] <= r[0] - 30: ss -= rw[j][2] or 0; sl -= -(rw[j][3] or 0); j += 1
            out.append([r[0], r[1], r[2], r[3], R(sl / (sl + ss) * 100, 1) if i >= 29 and sl + ss > 0 else None])
        tl = (x.get('hi_long') or {}).get('th') or 70; ts = (x.get('hi_short') or {}).get('th') or 30; d30 = x.get('d30') or {}
        usdm = lambda v: ('$%.2fB' % (v / 1000)) if v >= 1000 else '$%dM' % round(v)
        mk = []
        for t in x.get('top') or []:
            lg = t['long'] >= t['short']; v = t['long'] if lg else t['short']
            mk.append(dict(d=dn(t['date']), v=-v if lg else v, col='dn' if lg else 'up', up=0 if lg else 1, zh=t['date'][2:].replace('-', '/') + ' ' + usdm(v), en=t['date'][2:].replace('-', '/') + ' ' + usdm(v)))
        zs = near([dict(lo=tl, hi=None, col='dn', zh='多單佔 %d%% 以上：被迫賣出的多' % tl, en='Longs at %d%% or more: mostly forced selling' % tl, nz='多單佔 %d%% 的門檻' % tl, ne='the %d%% long-share line' % tl),
                   dict(lo=None, hi=ts, col='up', zh='多單佔 %d%% 以下：被迫買回的多' % ts, en='Longs at %d%% or less: mostly forced buying' % ts, nz='多單佔 %d%% 的門檻' % ts, ne='the %d%% long-share line' % ts)], out[-1][4])
        X['lqv'] = dict(k='lqv', zh='每日多空清算量', en='Daily long and short liquidations', hz='近 30 天的清算裡，多單佔的比例', he='Longs as a share of the last 30 days of liquidations', rng=365, rows=out, p=1,
          dz='每天被交易所強制平倉的 BTC 永續多單和空單（百萬美元），是實際紀錄、不是推算。多單被清算多，是下跌時被迫賣出的多；空單多，是上漲時被迫買回的多。交易所公開的清算資料會少報，所以看多空的比例，不要看總額%s。' % (
              ('；近 30 天多單 %s、空單 %s' % (usdm(d30['long']), usdm(d30['short']))) if d30.get('long') is not None else ''),
          de='BTC perpetual longs and shorts force-closed by exchanges each day ($M), from actual records, not an estimate. More long liquidations mean forced selling on the way down; more short liquidations mean forced buying on the way up. Public liquidation feeds under-report, so compare longs with shorts rather than reading the totals%s.' % (
              ('; over 30 days, longs %s and shorts %s' % (usdm(d30['long']), usdm(d30['short']))) if d30.get('long') is not None else ''),
          modes=[dict(mz='每日', me='Daily', f='usdM', tf='sqrt', hero=2, marks=mk,
                      ser=[ser(2, zh='空單被清算（往上）', en='Shorts liquidated (up)', t='bar', col='up'), ser(3, zh='多單被清算（往下）', en='Longs liquidated (down)', t='bar', col='dn'), ser(4, hide=1, f='p1')],
                      leg=[['k2', '圓圈：清算最多的幾天', 'Circles: the largest days', 'ring']]),
                 dict(mz='30 日多單占比', me='30-day long share', f='p1', hero=0, dom=[0, 100],
                      ser=[ser(4, zh='近 30 天清算裡多單佔的比例', en='Longs as a share of 30-day liquidations', col='c5', w=1.6)], refs=[dict(v=50, col='k2', zh='50%', en='50%')], zones=zs,
                      leg=[['dn', '多單佔 %d%% 以上' % tl, 'Longs at %d%% or more' % tl, 'box'], ['up', '多單佔 %d%% 以下' % ts, 'Longs at %d%% or less' % ts, 'box']])])
    else:
        na('lqv', '每日多空清算量', 'Daily long and short liquidations', 'deriv.liq_vol', 'Coinalyze', '這張圖畫每天被強制平倉的多單和空單，以及近 30 天多單佔的比例。', 'This chart shows daily long and short liquidations and the 30-day share of longs.')

    # ══ 波動 ══
    # 隱含 vs 實際波動（V.deriv.after 的 c-vol）：DVOL s4、RV30 s1；兩線之間隱含高塗綠、實際高塗橘紅。
    # 規格沒有「兩線之間上色」，所以差距另外做成一條正負上色的線，放在第二個檢視
    v = vz.get('vol'); dv = d.get('dvol') or {}
    if has(v):
        rows = [[r[0], r[1], r[2], R(r[1] - r[2], 2) if r[1] is not None and r[2] is not None else None] for r in v['rows']]
        pc = dv.get('pct_1y', v.get('dvol_pct_1y'))
        X['vol'] = dict(k='vol', zh='隱含波動 vs 實際波動', en='Implied vs realized volatility', hz='隱含 − 實際（點）', he='Implied − realized (points)', f='p1', rows=rows,
          dz='隱含波動（DVOL）是選擇權價格反推出來、市場預期未來 30 天會動多大；實際波動（RV30）是過去 30 天真的動了多大，兩個都是年化。隱含比實際高，代表市場在為之後的波動多付錢；實際比隱含高，代表選擇權低估了波動。%s' % (
              ('DVOL 現在 %.1f%%，在近一年第 %d 百分位。' % (dv['value'], round(pc))) if dv.get('value') is not None and pc is not None else ''),
          de='Implied volatility (DVOL) is the 30-day move the options market is pricing; realized volatility (RV30) is how much price actually moved over the last 30 days. Both are annualized. Implied above realized means the market is paying up for future movement; realized above implied means options underpriced it. %s' % (
              ('DVOL is now %.1f%%, at the %s percentile of the past year.' % (dv['value'], ordinal(round(pc)))) if dv.get('value') is not None and pc is not None else ''),
          modes=[dict(mz='兩條線', me='Both lines', hero=2, ser=[ser(1, zh='隱含波動 DVOL', en='Implied (DVOL)', col='c5', w=1.7), ser(2, zh='實際波動 RV30', en='Realized (RV30)', col='c3', w=1.7), ser(3, hide=1, t='sign', base=0, f='s1')], bands=[dict(a=1, b=2, col='up', col2='dn', op=.2)],
                      leg=[['up', '隱含比實際高', 'Implied above realized', 'box'], ['dn', '實際比隱含高', 'Realized above implied', 'box']]),
                 dict(mz='差距', me='Gap', hero=0, f='s1', ser=[ser(3, zh='隱含 − 實際', en='Implied − realized', t='sign', base=0, w=1.5)],
                      leg=[['up', '隱含比實際高', 'Implied above realized', 'box'], ['dn', '實際比隱含高', 'Realized above implied', 'box']])])
    else:
        na('vol', '隱含波動 vs 實際波動', 'Implied vs realized volatility', 'deriv.viz.vol', 'Deribit DVOL、Kraken RV30', '這張圖比較選擇權預期的波動和過去 30 天實際的波動。', 'This chart compares the volatility options are pricing with what was realized over the last 30 days.')

    # 隱含波動率期限結構（drawIvt）：今天 s4 實線、7 天前 ink-2 虛線、30 天前 ink-3 細虛線。橫軸是離到期的天數
    x = d.get('ivterm')
    if has(x, 'curve') and x.get('t'):
        t = x['t']; tv = lambda k: t.get(str(k), t.get(k)); p7 = x.get('prev7') or {}; p30 = x.get('prev30') or {}
        S = []
        if p30.get('curve'): S.append(dict(zh='一個月前', en='30d ago', col='k2', w=1.3, dash='2 3', rows=p30['curve']))
        if p7.get('curve'): S.append(dict(zh='一週前', en='7d ago', col='ink', w=1.4, dash='5 4', rows=p7['curve']))
        S.append(dict(zh='今天', en='Today', col='c5', w=2.2, rows=x['curve']))
        ST = dict(inv=('近月比較貴，是倒掛', 'near-dated is pricier: inverted'), flat=('兩邊相差不到 1 點，大致持平', 'less than a point apart: roughly flat'), norm=('遠月比較貴，是正常的形狀', 'longer-dated is pricier: the normal shape'))[x.get('state') if x.get('state') in ('inv', 'flat', 'norm') else 'flat']
        X['ivt'] = dict(k='ivt', zh='隱含波動率期限結構', en='Implied volatility term structure', hz='7 天 − 90 天（點）；正的是倒掛', he='7 days − 90 days (points); positive = inverted', hs=dict(v=x.get('slope'), f='s2'),
          xy=dict(xk='dte', f='p1', series=S, ref=None, marks=[dict(x=k_, y=tv(k_), col='c5', zh='%d 天 %.1f%%' % (k_, tv(k_)), en='%dd %.1f%%' % (k_, tv(k_))) for k_ in (7, 90) if tv(k_) is not None]),
          dz='每個到期日價平選擇權的隱含波動，橫軸是離到期還有幾天。遠月比近月高是平靜時的正常形狀；近月比遠月高叫倒掛，代表市場覺得眼前幾天的風險比較大。現在 7 天 %.1f%%、90 天 %.1f%%，%s%s' % (
              tv(7), tv(90), ST[0], '。' if S[:-1] else '；曲線從 %s 起每天存一張，滿 7 天、30 天後會疊上當時的曲線來比。' % ymd(x.get('since') or '')),
          de='At-the-money implied volatility for each expiry, against days to expiry. Longer-dated above near-dated is the calm-market shape; near-dated above longer-dated is an inversion, meaning the market sees more risk in the next few days. Now 7 days is %.1f%% and 90 days %.1f%%, %s%s' % (
              tv(7), tv(90), ST[1], '.' if S[:-1] else '; the curve has been saved daily since %s, and the curves from 7 and 30 days ago will be overlaid once they exist.' % (x.get('since') or '')))
        if X['ivt']['xy']['ref'] is None: del X['ivt']['xy']['ref']
    else:
        na('ivt', '隱含波動率期限結構', 'Implied volatility term structure', 'deriv.ivterm', 'Deribit', '這張圖畫各到期日價平選擇權的隱含波動：今天、7 天前、30 天前各一條。', 'This chart shows at-the-money implied volatility by expiry: today, 7 days ago and 30 days ago.')

    # ══ 選擇權 ══
    # 各到期未平倉（V.deriv.after 的 c-oi）：網站是每個到期日一根柱子，買權綠、賣權橘紅疊起來。
    # 橫軸是未來的到期日，不是時間序列，所以做成清單：橫條長度是那個到期日的未平倉量
    op = vz.get('options') or {}; ex = op.get('expiries')
    if ex:
        tt = op.get('totals') or {}; ca = tt.get('call_btc') or sum(e[2] for e in ex); pa = tt.get('put_btc') or sum(e[3] for e in ex); al = (ca + pa) or 1; mx = max(e[2] + e[3] for e in ex) or 1
        ub = lambda b: ('約 %s 億美元' % n0(b * 10), 'about $%.1fB' % b) if b is not None else (None, None)
        rows = [row('買權合計', 'Calls, all expiries', ca, f='btc0', bar=clip(ca / al * 100), col='up', nz=ub(tt.get('call_usd_b'))[0], ne=ub(tt.get('call_usd_b'))[1]),
                row('賣權合計', 'Puts, all expiries', pa, f='btc0', bar=clip(pa / al * 100), col='dn', nz=ub(tt.get('put_usd_b'))[0], ne=ub(tt.get('put_usd_b'))[1])]
        for e in ex:
            tot = e[2] + e[3]
            if tot / al < .01: continue
            pcr_ = e[3] / e[2] if e[2] else None; col = 'k2' if pcr_ is None else 'up' if pcr_ < .7 else 'dn' if pcr_ > 1 else 'k2'   # 照網站 dvInterp：賣權／買權 < 0.7 偏多、> 1 偏避險、中間算平衡
            rows.append(row('%s 到期（%d 天後）' % (ymd(e[0]), e[1]), '%s (%dd)' % (e[0], e[1]), '買 %s · 賣 %s' % (n0(e[2]), n0(e[3])), ve='C %s · P %s' % (n0(e[2]), n0(e[3])), seg=[[clip(e[2] / mx * 100), 'up'], [clip(e[3] / mx * 100), 'dn']], col=col if tot >= mx else None,
                            nz='佔全部 %d%% · 賣權 ÷ 買權 %s · 最大痛點 $%s' % (round(tot / al * 100), '—' if pcr_ is None else '%.2f' % pcr_, n0(e[4])), ne='%d%% of all · put ÷ call %s · max pain $%s' % (round(tot / al * 100), '—' if pcr_ is None else '%.2f' % pcr_, n0(e[4]))))
        X['oi'] = dict(k='oi', zh='各到期未平倉', en='Open interest by expiry', hz='選擇權未平倉合計', he='Options open interest, total', hs=dict(v=op.get('total') or (ca + pa), f='btc0'), list=dict(rows=rows),
          dz='每個到期日還沒平倉的買權和賣權（顆），橫條綠色那段是買權、橘紅色那段是賣權，總長是那個到期日的未平倉量，量越大、到期前對價格的牽動越大。量最大的那個到期日，數字會依賣權 ÷ 買權上色：不到七成是綠色（偏押上漲），超過一是橘紅色（偏避險）。佔全部不到 1% 的到期日不列。',
          de='Open calls and puts for each expiry (BTC); in each bar the green part is calls and the orange-red part puts; total length is that expiry\'s open interest, and the bigger it is, the more it can pull on price into expiry. For the largest expiry the figure is coloured by put ÷ call: green under 0.7 (leaning to upside bets), orange-red above 1 (leaning to hedges). Expiries under 1% of the total are left out.')
    else:
        na('oi', '各到期未平倉', 'Open interest by expiry', 'deriv.viz.options.expiries', 'Deribit', '這張卡列出每個到期日的買權和賣權未平倉量。', 'This card lists call and put open interest for each expiry.')

    # 選擇權買方權利金差（drawPr）：每日柱子正綠負橘紅；7 日平均是 s4 色的線。大數字的顏色照網站數字卡：7 日平均的正負
    x = d.get('prem')
    if has(x):
        rows = [[r[0], r[1], r[2], r[3]] for r in x['rows'] if r[1]]
        X['prem'] = dict(k='prem', zh='選擇權買方權利金差', en='Options buyer premium: calls − puts', hz='7 日平均，百萬美元', he='7-day average, $M', f='s1', rows=rows, p=1, hero=2,
          ser=[ser(2, zh='每日：買權 − 賣權', en='Daily: calls − puts', t='bar', base=0), ser(3, zh='7 日平均', en='7-day average', col='c5', w=2), ser(3, hide=1, t='sign', base=0)],
          leg=[['up', '買權花得多：錢押在上漲', 'Calls lead: betting on upside', 'box'], ['dn', '賣權花得多：在買下跌保護', 'Puts lead: buying downside protection', 'box']],
          dz='每天主動買進買權付出的權利金，減掉主動買進賣權付出的權利金（百萬美元）。只算願意主動付錢的買方：正值是錢押在上漲，負值是在買下跌保護。沙金色的線是 7 日平均%s。' % (
              ('，最近一天買權 %.1f、賣權 %.1f' % (x['call'], x['put'])) if x.get('call') is not None and x.get('put') is not None else ''),
          de='Premium paid each day by takers buying calls, minus premium paid by takers buying puts ($M). Only the aggressive buyer is counted: positive means money is betting on upside, negative means it is buying downside protection. The sand line is the 7-day average%s.' % (
              ('; on the latest day, calls %.1f and puts %.1f' % (x['call'], x['put'])) if x.get('call') is not None and x.get('put') is not None else ''))
    else:
        na('prem', '選擇權買方權利金差', 'Options buyer premium: calls − puts', 'deriv.prem', 'Deribit', '這張圖畫每天主動買進買權和賣權的權利金差，以及 7 日平均。', 'This chart shows the daily gap between premium paid for calls and for puts, with its 7-day average.')

    # 看跌／看漲比、25Δ 風險逆轉：網站只有讀數（dvInterp），歷史才累積幾天，還不能畫圖
    pc = d.get('pcr') or {}; rr = d.get('rr25') or {}
    if pc.get('oi_pcr') is not None or rr.get('rr') is not None:
        rows = []
        if pc.get('oi_pcr') is not None:
            o = pc['oi_pcr']
            rows.append(row('賣權 ÷ 買權（未平倉）', 'Put ÷ call (open interest)', o, f='x2', bar=clip(o * 50), mk=50, col='c5' if o >= 1 else 'ink',
                            nz='賣權比買權多，偏防守' if o >= 1 else '買權明顯比較多' if o <= .6 else '買權比較多，但不極端', ne='More puts than calls: defensive' if o >= 1 else 'Calls clearly dominate' if o <= .6 else 'Calls lead, but not to an extreme'))
        if pc.get('vol_pcr') is not None:
            o = pc['vol_pcr']
            rows.append(row('賣權 ÷ 買權（24 小時成交）', 'Put ÷ call (24h volume)', o, f='x2', bar=clip(o * 50), mk=50, col='c5' if o >= 1 else 'ink', nz='今天成交的賣權比買權多' if o >= 1 else '今天成交的買權比賣權多', ne='More puts than calls traded today' if o >= 1 else 'More calls than puts traded today'))
        if rr.get('rr') is not None:
            o = rr['rr']
            rows.append(row('25Δ 風險逆轉（%s）' % rr.get('expiry', '30d').replace('d', ' 天'), '25Δ risk reversal (%s)' % rr.get('expiry', '30d'), o, f='s2', bar=clip(50 + o * 5), mk=50, col='up' if o > 2 else 'dn' if o < -2 else 'ink',
                            nz=('買權比賣權貴 %.1f 點：選擇權市場偏向押上漲' % o) if o > 2 else ('賣權比買權貴 %.1f 點：市場在買下跌保護' % -o) if o < -2 else '接近 0：押漲和押跌的需求大致平衡',
                            ne=('Calls cost %.1f points more than puts: leaning to upside bets' % o) if o > 2 else ('Puts cost %.1f points more than calls: buying downside protection' % -o) if o < -2 else 'Near 0: demand for upside and downside is balanced'))
            for kz, ke, key in (('25Δ 買權的隱含波動', '25Δ call implied vol', 'call_iv'), ('25Δ 賣權的隱含波動', '25Δ put implied vol', 'put_iv'), ('價平的隱含波動', 'At-the-money implied vol', 'atm_iv')):
                if rr.get(key) is not None: rows.append(row(kz, ke, rr[key], f='p1'))
        hv = pc.get('oi_pcr') if pc.get('oi_pcr') is not None else rr.get('rr')
        X['pcr'] = dict(k='pcr', zh='看跌／看漲比與風險逆轉', en='Put/call ratio and risk reversal', hz='賣權未平倉 ÷ 買權未平倉' if pc.get('oi_pcr') is not None else '25Δ 風險逆轉', he='Put open interest ÷ call open interest' if pc.get('oi_pcr') is not None else '25Δ risk reversal',
          hs=dict(v=hv, f='x2' if pc.get('oi_pcr') is not None else 's2'), list=dict(rows=rows),
          dz='兩個看選擇權市場偏哪一邊的讀數。賣權 ÷ 買權大於 1（直線的位置），代表避險或看空的部位比看漲的多；風險逆轉是同樣距離的買權和賣權誰比較貴，負的是賣權貴、市場在買下跌保護。%s' % (
              ('這兩個數字從 %s 起每天存一筆，目前 %d 筆，累積夠了才畫走勢。' % (ymd(pc['first']), pc.get('n') or 0)) if pc.get('first') and (pc.get('n') or 0) < 60 else ''),
          de='Two readings of which way the options market leans. A put ÷ call ratio above 1 (the tick) means more hedging or bearish positions than bullish ones; the risk reversal compares equally distant calls and puts, and negative means puts cost more, so the market is buying downside protection. %s' % (
              ('Both have been saved daily since %s (%d readings so far); a history chart needs more of them.' % (pc['first'], pc.get('n') or 0)) if pc.get('first') and (pc.get('n') or 0) < 60 else ''))
    else:
        na('pcr', '看跌／看漲比與風險逆轉', 'Put/call ratio and risk reversal', 'deriv.pcr、deriv.rr25', 'Deribit', '這張卡列出賣權 ÷ 買權的比值和 25Δ 風險逆轉。', 'This card lists the put ÷ call ratio and the 25-delta risk reversal.')

    # ══ 情緒 ══
    # 恐懼貪婪指數（drawFng）：線是 s4；≤ 20 的底是 down 色、≥ 80 的底是 up 色
    x = fw.get('fng_hist')
    if has(x):
        lo, hi = x.get('lo', 20), x.get('hi', 80); f30 = x.get('f30') or {}
        zs = near([dict(lo=None, hi=lo, col='dn', zh='極度恐懼（≤ %d）' % lo, en='Extreme fear (≤ %d)' % lo, nz='極度恐懼的門檻', ne='the extreme-fear line'),
                   dict(lo=hi, hi=None, col='up', zh='極度貪婪（≥ %d）' % hi, en='Extreme greed (≥ %d)' % hi, nz='極度貪婪的門檻', ne='the extreme-greed line')], x.get('value'))
        X['fng'] = dict(k='fng', zh='恐懼貪婪指數', en='Fear & Greed Index', hz='0 極度恐懼，100 極度貪婪', he='0 = extreme fear, 100 = extreme greed', f='n0', rows=x['rows'], p=1, dom=[0, 100],
          ser=[ser(2, zh='恐懼貪婪指數', en='Fear & Greed', col='c5', w=1.3)], zones=zs,
          refs=[dict(v=50, col='k2'), dict(v=lo, col='dn', zh='極度恐懼 ≤ %d' % lo, en='Extreme fear ≤ %d' % lo), dict(v=hi, col='up', zh='極度貪婪 ≥ %d' % hi, en='Extreme greed ≥ %d' % hi)],
          dz='由波動、成交量、社群熱度、搜尋熱度等合成的情緒分數，0 是極度恐懼、100 是極度貪婪。情緒是反向參考，但不是買賣訊號%s。' % (
              ('：過去 %d 次跌到 %d 以下之後的 30 天，只有 %d 次上漲，第一次掉進去不一定是底' % (f30['n'], lo, f30['up'])) if f30.get('n') else ''),
          de='A sentiment score built from volatility, volume, social activity and search trends: 0 is extreme fear, 100 extreme greed. Sentiment is a contrarian reference, not a trading signal%s.' % (
              (': of the %d past drops to %d or below, price was higher 30 days later only %d times, so the first dip into fear is not necessarily the low' % (f30['n'], lo, f30['up'])) if f30.get('n') else ''))
    else:
        na('fng', '恐懼貪婪指數', 'Fear & Greed Index', 'flows.fng_hist', 'alternative.me', '這張圖畫恐懼貪婪指數的歷史，以及 20 以下、80 以上兩個極端區。', 'This chart shows the history of the Fear & Greed Index with its extreme zones at 20 and 80.')

    # 散戶關注度（drawWiki）：線是 s1、對數刻度；暴增線以上的底是 down 色
    x = fw.get('wiki')
    if has(x):
        sp = x.get('spike', 2.5); nsp = len(x.get('spikes') or [])
        X['wiki'] = dict(k='wiki', zh='散戶關注度：維基百科瀏覽量', en='Retail attention: Wikipedia page views', hz='7 日平均瀏覽量 ÷ 過去一年的中位數', he='7-day average views ÷ past-year median', f='x2', log=1, rows=[[r[0], r[1], r[3]] for r in x['rows']], p=1,
          ser=[ser(2, zh='7 日平均 ÷ 過去一年中位數', en='7-day avg ÷ past-year median', col='c3', w=1.3)],
          refs=[dict(v=1, col='k2', zh='1 倍：和過去一年差不多', en='1×: in line with the past year'), dict(v=sp, col='dn', zh='暴增 ≥ %g 倍' % sp, en='Spike ≥ %g×' % sp)],
          zones=[dict(lo=sp, hi=None, col='dn', zh='暴增：關注度是平常的 %g 倍以上' % sp, en='Spike: attention at %g× normal or more' % sp, nz='暴增線', ne='the spike line')],
          dz='英文維基百科「Bitcoin」條目每天的瀏覽量，取 7 日平均，再除以自己過去一年的中位數，看關注度有沒有突然升溫。大量新手湧進來的時候會暴增，頂部和急跌都會出現；它只代表有人在查，不分買賣%s。' % (
              ('。%s 以來到 %g 倍以上只有 %d 次' % (ym(ymd_of(x['rows'][0][0])), sp, nsp)) if nsp else ''),
          de='Daily views of the English Wikipedia "Bitcoin" article as a 7-day average, divided by its own past-year median, to see whether attention is suddenly heating up. It spikes when newcomers pour in, at tops and in crashes alike; it only shows people looking things up, not whether they buy or sell%s.' % (
              ('. It has reached %g× only %d times since %s' % (sp, nsp, ymd_of(x['rows'][0][0])[:7])) if nsp else ''))
    else:
        na('wiki', '散戶關注度：維基百科瀏覽量', 'Retail attention: Wikipedia page views', 'flows.wiki', 'Wikimedia', '這張圖畫維基百科「Bitcoin」條目的 7 日平均瀏覽量，除以過去一年的中位數。', 'This chart shows the 7-day average views of the Wikipedia "Bitcoin" article divided by its past-year median.')

    grp = lambda zh, en, sz, se, keys: dict(zh=zh, en=en, sz=sz, se=se, charts=[X[k_] for k_ in keys if k_ in X])
    return [grp('槓桿', 'Leverage', '做多的槓桿擠不擠，最近是誰在被清算', 'How crowded leveraged longs are, and who has been getting liquidated', ['fh', 'basis', 'oih', 'lsa', 'lqv']),
            grp('波動', 'Volatility', '選擇權市場預期接下來會動多大', 'How big a move the options market is pricing', ['vol', 'ivt']),
            grp('選擇權', 'Options', '未平倉堆在哪個到期日，錢押在哪一邊', 'Which expiries hold the open interest, and which side money is paying for', ['oi', 'prem', 'pcr']),
            grp('情緒', 'Sentiment', '大家是害怕還是貪心，新手有沒有湧進來', 'Whether the crowd is fearful or greedy, and whether newcomers are pouring in', ['fng', 'wiki'])]


def ordinal(n):
    return '%d%s' % (n, 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))


def ymd_of(day):
    import datetime as dt
    return (dt.date(1970, 1, 1) + dt.timedelta(int(day))).isoformat()
