# -*- coding: utf-8 -*-
"""每張指標卡的偏向（2026-11-17 使用者：「指標偏多還是空要有」）。
卡片上「我們的看法」那一塊：偏多／偏空／中性，一句立場、一句理由、什麼情況會改變。手機清單列和每一段的答案也用它。
規則（page.html ㉞-8）：
1. 偏向講的是「這個指標現在對價格的意思」，不是買賣建議。時間尺度跟著指標走（估值看一年、資金與槓桿看幾週）。
2. 有回測的照回測：之後的表現比任一天好才算偏多、差才算偏空；差不多就是中性，即使一般說法認為它是訊號（例：極度恐懼、儲備風險低檔）。
3. 沒有回測的照指標本身的定義（站上／跌破成本、流入／流出、擁擠／清洗）。
4. 只描述位置或波動、不指方向的（集中度、Gamma、期限結構以外的波動率、維基瀏覽量）就寫中性，理由寫「為什麼不指方向」。
5. 只有三種：偏多 up、偏空 down、中性 neu；不用「留意」。
每個函式回傳 (語氣, 立場中, 立場英, 理由中, 理由英, 會改變中, 會改變英)；資料不夠回 None（卡片就不顯示看法）。"""

def V(t, vz, ve, dz, de, cz='', ce=''): return (t, vz, ve, dz, de, cz, ce)
def pc(v, d=1):
    s = ('%.' + str(d) + 'f') % abs(v); return ('+' if v > 0 and float(s) else '−' if v < 0 and float(s) else '') + s + '%'
def usd(v): return '$' + format(int(round(v)), ',')
def better(s, b, k='med', gap=3):   # 回測：比任一天好／差／差不多
    d = s[k] - b[k]; return 'up' if d >= gap else 'down' if d <= -gap else 'neu'
O = lambda L: L['onchain']; F = lambda L: L['flows']; D = lambda L: L['deriv']; C = lambda L: L['cycle']

# ══ 買盤 ══
def etf(L):
    E = [e for e in F(L)['etf'] if not e.get('partial')]; f5 = sum(e['musd'] for e in E[-5:])
    if f5 <= -300: return V('down', 'ETF 在流出', 'ETFs are bleeding', '近 5 個交易日淨流出 %s 百萬美元：機構這一側的買盤在退。' % format(int(-f5), ','), 'Net outflows of $%sM over five sessions: institutional demand is pulling back.' % format(int(-f5), ','), '連續幾天淨流入', 'A run of net inflows')
    if f5 >= 300: return V('up', 'ETF 在流入', 'ETFs are buying', '近 5 個交易日淨流入 %s 百萬美元：機構買盤在進場。' % format(int(f5), ','), 'Net inflows of $%sM over five sessions: institutions are buying.' % format(int(f5), ','), '轉成連續淨流出', 'A turn to steady outflows')
    return V('neu', '流量不大', 'Flows are small', '近 5 個交易日合計 %s 百萬美元，方向不明顯。' % format(int(f5), ','), '$%sM over five sessions: no clear direction.' % format(int(f5), ','))
def cot(L):
    c = F(L)['cot']; d = c['am4']
    if d <= -5000: return V('down', '機構在減多', 'Asset managers are cutting', '資產管理機構 4 週淨多減少：真正看多的那一方在退。槓桿基金的空單多半是基差交易，不算看空。', 'Asset managers cut net longs over four weeks: the directional buyers are retreating. Leveraged-fund shorts are mostly basis trades, not bets.', '資產管理機構重新加多', 'Asset managers adding again')
    if d >= 5000: return V('up', '機構在加多', 'Asset managers are adding', '資產管理機構 4 週淨多增加。槓桿基金的空單多半是基差交易，不算看空。', 'Asset managers added net longs over four weeks. Leveraged-fund shorts are mostly basis trades, not bets.', '資產管理機構轉為減多', 'Asset managers cutting')
    return V('neu', '部位沒有明顯變化', 'Positions are steady', '資產管理機構 4 週淨多變化不大；槓桿基金的空單多半是基差交易。', 'Asset managers\' net long barely moved over four weeks; leveraged-fund shorts are mostly basis trades.')
def pr_us(L):
    p = F(L)['cb_premium']; lo, hi = p['band']
    if p['avg7'] < lo: return V('down', '美國買盤偏弱', 'US buying is weak', '扣掉 USDT 後，Coinbase 價格 7 日平均低於海外：美國現貨這一側在賣。', 'Net of USDT, Coinbase trades below offshore on a 7-day average: US spot is selling.', '價差回到正常帶以上', 'The gap back inside its normal band')
    if p['avg7'] > hi: return V('up', '美國買盤積極', 'US buying is strong', 'Coinbase 價格 7 日平均高於海外：美國現貨在買。', 'Coinbase trades above offshore on a 7-day average: US spot is buying.', '價差掉回正常帶', 'The gap falling back into its band')
    return V('neu', '和海外差不多', 'In line with offshore', '價差在正常帶內，美國買盤沒有特別積極或特別弱。', 'The gap is within its normal band: US buying is neither keen nor weak.')
def pr_asia(L):
    v = F(L)['premium3']['usdt']['pct']
    if v <= -.5: return V('down', '亞洲在換回法幣', 'Asia is cashing out', '場外 USDT 低於匯率：有人把穩定幣換回人民幣，場外資金在流出。', 'OTC USDT trades below the exchange rate: holders are swapping stablecoins back to CNY.', '回到匯率以上', 'A return above the exchange rate')
    if v >= .5: return V('up', '亞洲買盤積極', 'Asian buying is keen', '場外 USDT 高於匯率：有人搶著換成穩定幣進場。', 'OTC USDT trades above the exchange rate: buyers are paying up to get in.', '跌回匯率以下', 'A drop below the exchange rate')
    return V('neu', '亞洲大致平衡', 'Asia is balanced', '場外 USDT 接近匯率，進出大致平衡。', 'OTC USDT is near the exchange rate: flows in and out are balanced.')
def pr_perp(L):
    q = F(L)['premium3']['perp']['avg7_pct_own']
    if q >= 85: return V('down', '槓桿多頭擁擠', 'Leveraged longs are crowded', '永續比現貨貴得少見：多單擁擠，容易被清洗。', 'Perps are unusually rich against spot: longs are crowded and prone to a flush.', '溢價回到平常', 'The premium back to normal')
    if q <= 15: return V('up', '空方擁擠', 'Shorts are crowded', '永續比現貨便宜得少見：空單擁擠，反彈時容易被軋。', 'Perps are unusually cheap against spot: shorts are crowded and prone to a squeeze.', '溢價回到平常', 'The premium back to normal')
    return V('neu', '槓桿不偏', 'Leverage is balanced', '永續對現貨的溢價在平常範圍。', 'The perp premium is in its normal range.')
def kp(L):
    k = F(L)['kp']
    if k['a7'] >= 5:
        t = better(k['hot90'], k['base90'], gap=0); return V('down' if t == 'down' else 'neu', '韓國散戶在追價', 'Korean retail is chasing', '溢價衝上 5%% 之後 90 天中位數 %s，%s任一天的 %s。' % (pc(k['hot90']['med']), '差於' if t == 'down' else '不輸', pc(k['base90']['med'])), 'After topping 5%%, the 90-day median was %s versus %s on any day.' % (pc(k['hot90']['med']), pc(k['base90']['med'])), '溢價回到 2% 以下', 'The premium back under 2%')
    return V('neu', '韓國沒有過熱', 'No Korean froth', '溢價在常態範圍，散戶沒有追價。', 'The premium is in its normal range: no retail chase.', '7 日平均衝上 5%', 'A 7-day average above 5%')
def exflow(L):
    x = F(L)['exflow']
    if x['pct4'] <= 10 and x['out_r90']['med'] > x['base90']['med']: return V('up', '幣在大量離開交易所', 'Coins are leaving exchanges fast', '30 天淨流出在近 4 年最低 10%%；過去這種時候 90 天後中位數 %s，好過任一天的 %s。' % (pc(x['out_r90']['med']), pc(x['base90']['med'])), 'The 30-day outflow is in the lowest tenth of four years; past cases had a 90-day median of %s versus %s on any day.' % (pc(x['out_r90']['med']), pc(x['base90']['med'])), '轉為淨流入', 'A turn to net inflows')
    if x['pct4'] >= 90: return V('down', '幣在大量流入交易所', 'Coins are flooding exchanges', '30 天淨流入在近 4 年最高 10%：潛在賣壓增加。', 'The 30-day inflow is in the top tenth of four years: more coins ready to sell.', '轉為淨流出', 'A turn to net outflows')
    return V('neu', '流量在平常範圍', 'Flows are ordinary', '30 天淨流量不極端；流量本身分不出方向。', 'The 30-day net flow is not extreme; flows alone do not set direction.')
def exch(L):
    c = O(L)['exchange']['exchange_supply_chg30_pct']
    return V('up', '交易所存幣在減', 'Exchange balances are falling', '幣被提走保管，潛在賣壓變少。', 'Coins are being withdrawn, which lowers potential selling.', '30 天轉為增加', 'A 30-day increase') if c < 0 else V('down', '交易所存幣在增', 'Exchange balances are rising', '幣在流進交易所，潛在賣壓增加。', 'Coins are moving onto exchanges, which adds potential selling.', '30 天轉為減少', 'A 30-day decrease')
def ad(L):
    a = O(L)['ad']; y = a['y1']
    if a['value'] < 0 and y['value'] < 0: return V('down', '需求偏弱', 'Demand is weak', '30 天和 1 年都是負的：新買盤追不上舊幣沉澱的速度。', 'Negative on both 30 days and a year: new buying cannot keep pace with coins settling.', '30 天轉正', 'The 30-day reading turning positive')
    if a['value'] > 0 and y['value'] > 0: return V('up', '需求接得住', 'Demand is holding', '30 天和 1 年都是正的：新買盤吃得下新挖和換手的幣。', 'Positive on both horizons: new buying absorbs issuance and turnover.', '30 天轉負', 'The 30-day reading turning negative')
    return V('neu', '兩個尺度不一致', 'Mixed horizons', '30 天和 1 年一正一負，需求還沒有明確方向。', 'One horizon is positive and the other negative: no clear direction yet.')
def dmd(L):
    d = O(L)['dmd']
    if not d['spot_pos'] and not d['perp_pos']: return V('down', '兩邊都沒有新買盤', 'No new buying on either side', '現貨和永續的需求都在減。', 'Spot and perpetual demand are both shrinking.', '現貨需求轉正', 'Spot demand turning positive')
    if d['spot_pos'] and d['perp_pos']: return V('up', '兩邊都在買', 'Both sides are buying', '現貨和永續的需求都在增。', 'Spot and perpetual demand are both growing.', '現貨需求轉負', 'Spot demand turning negative')
    return V('neu', '一邊買一邊賣', 'Split demand', '現貨和永續一增一減，看現貨那邊為主。', 'One side is buying and the other selling; spot matters more.')
def capflow(L):
    c = O(L)['capflow']
    if c['m1'] >= 25: return V('down', '投機升溫', 'Speculation is heating up', '一個月內換手的比重偏高，週期頂部附近常見。', 'A high share turned over within a month, as near past tops.', '短期換手比重回落', 'The short-term share easing')
    if c['y12'] > c['y12_30']: return V('up', '長線比重在升', 'The long-term share is rising', '沒有投機狂熱，放 1–2 年的幣在增加；有一部分只是時間到了一年。', 'No speculative frenzy and more coins sitting 1–2 years; partly just coins passing the one-year mark.', '短期換手比重衝高', 'A jump in short-term turnover')
    return V('neu', '結構穩定', 'A steady mix', '短期和長線的比重都沒有明顯變化。', 'Neither the short- nor long-term share is moving much.')
def grad(L):
    g = O(L)['grad']; z = g['z120']; b = g['back120']
    if z <= -1: return V('up' if b['bot']['r90']['med'] > b['top']['r90']['med'] else 'neu', '價格跌過頭', 'Price has overshot down', '120 日尺度上價格跌得比資金撤出快：價格相對資金偏便宜。', 'On the 120-day scale price has fallen faster than capital has left: cheap relative to flows.', '回到同步（−1 以上）', 'A return above −1')
    if z >= 1: return V('down', '價格漲過頭', 'Price has overshot up', '120 日尺度上價格漲得比資金流入快。', 'On the 120-day scale price has risen faster than capital has arrived.', '回到同步（+1 以下）', 'A return below +1')
    return V('neu', '價格和資金同步', 'In step with capital', '120 日尺度上價格和資金大致同步。', 'On the 120-day scale price and capital are roughly in step.')
def rcliq(L):
    r = F(L)['rc_liq']
    return V('down', '新資金停止流入', 'New money has stalled', '實現市值 30 天沒有增加，新資金沒進來。', 'Realized cap has not grown in 30 days: no new money is coming in.', '30 天轉為增加', 'A 30-day increase') if r['chg30_pct'] <= 0 else V('up', '新資金在流入', 'New money is arriving', '實現市值 30 天在增加。', 'Realized cap grew over 30 days.', '30 天轉為減少', 'A 30-day decline')
def rlc(L):   # 2026-11-22 流動性週期（Checkonchain Liquidity Index）。2013 起之後 180 天：0＝中位數 +81%、全部上漲（只有 3 輪）；1＝+36%、68%；0.2–1 之間＝+3%、51%（平常 +26%、62%），所以中間不指方向
    li = F(L)['rc_liq'].get('li') or {}; v = li.get('idx')
    if v is None: return V('neu', '沒有資料', 'No data', '', '')
    if v < 1e-6: return V('up', '資金底部區', 'Capital bottom zone', '實現市值創一年新低；2013 年以來只有 3 輪，都在週期底部附近，但碰到後價格還再跌 0% 到 −19%。', 'Realized cap is at a one-year low; since 2013 only 3 cycles, each near a cycle bottom, though price fell a further 0% to −19% after the first touch.', '指數離開 0 且實現市值回升', 'The index leaving 0 as realized cap recovers')
    if v >= .999: return V('up', '資金持續流入', 'Capital keeps arriving', '實現市值在 30、90、365 天裡都是最高：新資金一直進來。', 'Realized cap is at its 30-, 90- and 365-day highs: new money keeps arriving.', '指數從 1 掉下來', 'The index dropping from 1')
    return V('neu', '不指方向', 'No direction', '2013 年以來指數在 0.2 到 1 之間時，之後 180 天差不多一半漲一半跌（中位數 +3%，平常是 +26%），不指方向；要看它往 0 還是往 1 走。', 'Since 2013, with the index between 0.2 and 1, the next 180 days rose about half the time (median +3%, against +26% normally): no direction. Watch whether it heads for 0 or 1.', '跌到 0（實現市值一年新低）或回到 1', 'A drop to 0 (realized cap at a one-year low) or a return to 1')
def stab(L):
    s = F(L)['stables']
    return V('down', '場外美元在萎縮', 'Sideline dollars are shrinking', '穩定幣供給 30 天減少，能進場的錢變少。', 'Stablecoin supply shrank over 30 days: less dry powder.', '30 天轉為增加', 'A 30-day increase') if s['chg30_pct'] < 0 else V('up', '場外美元在增加', 'Sideline dollars are growing', '穩定幣供給 30 天增加，能進場的錢變多。', 'Stablecoin supply grew over 30 days: more dry powder.', '30 天轉為減少', 'A 30-day decrease')
def _whale(L):
    C_ = {c['key']: c for c in O(L)['whales']['cohorts']}; d = C_['100_1k']['chg30'] + C_['1k_10k']['chg30']
    return V('down', '大戶在減持', 'Large holders are trimming', '100–10K 顆的地址 30 天合計在減少。', 'Addresses with 100–10K BTC cut holdings over 30 days.', '30 天轉為增加', 'A 30-day increase') if d < 0 else V('up', '大戶在加碼', 'Large holders are adding', '100–10K 顆的地址 30 天合計在增加。', 'Addresses with 100–10K BTC added over 30 days.', '30 天轉為減少', 'A 30-day decrease')
whale = whalet = _whale
def lthnet(L):
    r = O(L)['lth_color']['run']
    if r['sign'] < 0 and r['price_chg_pct'] > -5: return V('neu', '換手中', 'Changing hands', '長期持有者在賣，但價格沒跌、有人接得住；前幾輪走到新高前都經過這種換手。', 'Long-term holders are selling but price has held: someone is absorbing it, as on past paths to new highs.', '價格開始跟著跌', 'Price starting to fall with it')
    if r['sign'] < 0: return V('down', '出貨壓價', 'Distribution weighs on price', '長期持有者在賣，價格跟著跌。', 'Long-term holders are selling and price is falling with it.', '淨部位轉正', 'The net position turning positive')
    return V('up', '在沉澱', 'Settling', '長期持有者在增加持幣。', 'Long-term holders are adding.', '淨部位轉負', 'The net position turning negative')
def lsrchg(L):
    v = O(L)['lsrchg']['value']
    return V('down', '幣在流向短期持有者', 'Coins are moving to short-term holders', '長期持有者在把幣交出去；熊底後一年也常見，所以只是偏空。', 'Long-term holders are handing coins over; common in the year after a bottom too, so only a lean.', '30 天轉正', 'A positive 30-day reading') if v < 0 else V('up', '籌碼在沉澱', 'Supply is settling', '幣從短期流回長期持有者。', 'Coins are moving back to long-term holders.', '30 天轉負', 'A negative 30-day reading')
def sthd(L):
    v = O(L)['sthd']['value']
    return V('down', '舊幣在換手', 'Old coins are changing hands', '短期持有者供給 90 天增加：老幣賣給新人。', 'Short-term holder supply rose over 90 days: old coins are being sold to newcomers.', '90 天轉為減少', 'A 90-day decrease') if v > 0 else V('up', '幣在沉澱', 'Coins are settling', '短期持有者供給 90 天減少：新進的幣放久了。', 'Short-term holder supply fell over 90 days: newer coins are ageing.', '90 天轉為增加', 'A 90-day increase')
def dorm(L):
    p = O(L)['dorm']['a30_pct4']
    if p > 80: return V('down', '老幣在動', 'Old coins are moving', '賣出的幣平均放得比平常久：老手在賣。', 'Coins sold had sat longer than usual: old hands are selling.', '回到平常範圍', 'A return to the normal range')
    if p < 20: return V('up', '老手沒在賣', 'Old hands are not selling', '賣出的多是新幣，老幣不動。', 'Mostly young coins are being sold; old coins stay put.', '升到近 4 年高檔', 'A move into the four-year high range')
    return V('neu', '平常範圍', 'Ordinary', '賣出的幣平均持有時間在近 4 年的平常範圍。', 'The average age of coins sold is within its normal four-year range.')
def svd(L):
    s = D(L)['svd']
    return V('down', '賣方主導', 'Sellers lead', '近 7 天主動賣多於主動買（OKX）。', 'Taker sells exceeded taker buys over 7 days (OKX).', '7 天轉為買方多', 'Buyers leading over 7 days') if s['sum7'] < 0 else V('up', '買方主導', 'Buyers lead', '近 7 天主動買多於主動賣（OKX）。', 'Taker buys exceeded taker sells over 7 days (OKX).', '7 天轉為賣方多', 'Sellers leading over 7 days')
def tk(L):
    t = D(L)['taker']; sp, cb = t['spot'], t['cb']
    if sp['d30'] < sp['med'] and cb['pct'] <= 20: return V('down', '現貨在賣', 'Spot is selling', '30 天現貨主動賣比平常多，Coinbase 尤其重。', 'Spot taker selling is heavier than normal over 30 days, especially on Coinbase.', '現貨回到常態以上', 'Spot back above normal')
    if sp['d30'] > sp['med'] and cb['pct'] >= 50: return V('up', '現貨在買', 'Spot is buying', '30 天現貨主動買比平常多。', 'Spot taker buying is heavier than normal over 30 days.', '現貨跌回常態以下', 'Spot back below normal')
    return V('neu', '買賣接近常態', 'Near normal', '現貨和 Coinbase 的主動買賣沒有一致偏向。', 'Spot and Coinbase taker flows do not agree on a direction.')
def stk(L):
    r = F(L)['btc_vs_stocks']['rel']['rows'][-1]; lag = sum(1 for i in range(3) if r[1] < r[2 + i])
    if lag == 3: return V('down', '相對偏弱', 'Relatively weak', '近兩個月 BTC 落後美股和黃金。', 'Over two months BTC trails stocks and gold.', '追上美股', 'Catching up with stocks')
    if lag == 0: return V('up', '相對偏強', 'Relatively strong', '近兩個月 BTC 贏過美股和黃金。', 'Over two months BTC beats stocks and gold.', '落後美股', 'Falling behind stocks')
    return V('neu', '互有勝負', 'Mixed', '近兩個月 BTC 贏過一部分、落後一部分。', 'Over two months BTC beats some and trails others.')
def macro(L):
    ri = F(L)['dfii10']['value']
    if ri >= 2: return V('down', '利率偏緊', 'Rates are tight', '10 年期實質利率 2% 以上，持有不生息資產的機會成本高。', 'A 10-year real yield above 2% makes holding non-yielding assets costly.', '實質利率回到 1.5% 以下', 'A real yield back under 1.5%')
    if ri < 1.5: return V('up', '利率不緊', 'Rates are easy', '10 年期實質利率低於 1.5%，總經不構成壓力。', 'A 10-year real yield under 1.5%: macro is not a headwind.', '升回 2% 以上', 'A rise back above 2%')
    return V('neu', '總經中性', 'Macro is neutral', '實質利率在中間，BTC 主要跟著美股走。', 'Real yields are middling; BTC mostly follows US stocks.')

# ══ 週期 ══
def dawn(L):   # 2026-11-25 照 WRITING.md：標籤寫位置，理由寫過去這一段之後一年怎麼走（dawn.py 的回測），會改變看法寫離開這一段的條件
    d = C(L)['dawn']; k = d['stage']; st = next(x for x in d['stats'] if x['stage'] == k); t = better(st['y1'], d['base'], gap=10); th = d['th']
    nz = ['深夜', '入夜', '破曉', '白晝', '黃昏'][k]; ne = ['deep night', 'nightfall', 'daybreak', 'daylight', 'dusk'][k]
    lz = ['週期的底部區', '下跌段，還沒到最便宜', '初升段，估值還偏低', '上升段，估值中上', '過熱段，接近頂部'][k]
    le = ['Bottom of the cycle', 'Falling leg, not the cheapest yet', 'Early rise, valuations still low', 'Rising leg, valuations mid-to-high', 'Overheated, near a top'][k]
    cz = ['熱度回到 %d 以上，就離開深夜' % th['cold'], '熱度跌到 %d 以下（深夜），或趨勢翻回往上（破曉）' % th['cold'], '趨勢翻成往下（入夜），或熱度升過 %d（白晝）' % th['mid'],
          '熱度升到 %d（黃昏），或趨勢翻成往下（入夜）' % th['hot'], '熱度跌回 %d 以下' % th['hot']][k]
    ce = ['Heat back above %d, leaving deep night' % th['cold'], 'Heat below %d (deep night), or the trend turning up (daybreak)' % th['cold'], 'The trend turning down (nightfall), or heat above %d (daylight)' % th['mid'],
          'Heat reaching %d (dusk), or the trend turning down (nightfall)' % th['hot'], 'Heat back below %d' % th['hot']][k]
    return V(t, lz, le, '2013 年以來落在%s的週，一年後 %d%% 比當時高、中位數 %s；隨便挑一週則是 %d%%、中位數 %s。只有三輪多的週期可比。' % (nz, st['y1']['up'], pc(st['y1']['med'], 0), d['base']['up'], pc(d['base']['med'], 0)),
             'Of the weeks in %s since 2013, %d%% were higher a year later, median %s; for any week it was %d%%, median %s. Only about three cycles to compare.' % (ne, st['y1']['up'], pc(st['y1']['med'], 0), d['base']['up'], pc(d['base']['med'], 0)), cz, ce)
def stage(L):
    S = C(L)['stage']; s = S['stage']; px = L['price']['bar']['c']; gap = (px / S['sma200'] - 1) * 100
    # 2026-11-20：牛市成立後鎖定，標籤反應慢。收盤跌回 200 日均線下時，標籤還是牛市但趨勢已經不支持，偏向改中性（原本一律偏多，和卡上的數字打架）
    if s == '牛市' and gap < 0: return V('neu', '牛市標籤還在，趨勢已轉弱', 'Bull label, weakening trend', '牛市成立後要在往下走的 200 日均線下連 30 天，才會退回熊市，所以標籤反應慢；收盤已經在均線下，趨勢不支持偏多。', 'Once set, bull only reverts after 30 days under a falling 200-day MA, so the label is slow; the close is already below the average, so the trend does not support a bullish lean.', '收盤站回 200 日均線之上，或在往下走的均線下待滿 30 天（退回熊市）', 'A close back above the 200-day MA, or 30 days under a falling one (back to bear)')
    if s == '牛市': return V('up', '牛市，長期趨勢往上', 'Bull, long-run trend up', '投降出現過，價格也在往上走的 200 日均線上站滿了 30 天：長期趨勢往上。這張沒有回測，看的是規則本身。', 'A capitulation happened and price held 30 days above a rising 200-day MA: the long-run trend is up. There is no backtest here; it is the rule itself.', '在往下走的 200 日均線下連 30 天，就退回熊市', '30 days under a falling 200-day MA sends it back to bear')
    if s == '熊市': return V('down', '熊市，長期趨勢往下', 'Bear, long-run trend down', '還沒同時看到投降、和收盤站上往上走的 200 日均線：長期趨勢還在往下。這張沒有回測，看的是規則本身。', 'There has not yet been both a capitulation and a close above a rising 200-day MA: the long-run trend is still down. No backtest; it is the rule itself.', '投降出現，收盤又站上往上走的 200 日均線', 'A capitulation plus a close above a rising 200-day MA')
    return V('neu', '過渡期，兩邊都還沒確定', 'Transition, not settled either way', '從熊市往牛市走的半路：可能站穩成為牛市，也可能退回熊市。', 'Halfway from bear to bull: it can settle into bull or slip back to bear.', '站穩均線 30 天成為牛市；跌回 5 天退回熊市', '30 days above makes it bull; 5 below sends it back to bear')
def regime(L):   # 理由用過去同方向翻轉之後一年的結果（regime.flips 的 r52）
    r = C(L)['regime']; pos = r['value'] > 0; on = r['regime'] > 0
    fl = [f for f in r['flips'] if f['dir'] == (1 if pos else -1) and f.get('r52') is not None]; ok = sum(1 for f in fl if (f['r52'] > 0) == pos)
    lz = ('中期趨勢往上' if on else '中期趨勢在轉強，快翻多') if pos else ('中期趨勢在轉弱，快翻空' if on else '中期趨勢往下')
    le = ('Medium-term trend up' if on else 'Strengthening, close to flipping long') if pos else ('Weakening, close to flipping short' if on else 'Medium-term trend down')
    return V('up' if pos else 'down', lz, le, '過去分數翻成%s %d 次，%d 次一年後價格比當時%s；但翻轉要連 4 週才算，所以常晚幾週。' % ('多方' if pos else '空方', len(fl), ok, '高' if pos else '低'),
             'The score has flipped %s %d times before; %d times price was %s a year later. A flip needs four weeks, so it often comes late.' % ('long' if pos else 'short', len(fl), ok, 'higher' if pos else 'lower'),
             '分數跌回 0 以下' if pos else '分數回到 0 以上', 'The score back below 0' if pos else 'The score back above 0')
def hnupl(L):   # 長期持有者的區間沒有回測，照位置；理由寫歷次頂和底的讀數
    h = O(L)['hnupl']; s = h['stage']; tmin = min(x['value'] for x in h['tops'])
    if s in ('cap', 'hope'): return V('up', '老手獲利很薄，接近底部區', 'Thin profits, near bottom territory', '長期持有者的帳面獲利，過去只在熊市後段和底部才這麼薄。這張沒有回測之後的漲跌，看的是位置。',
                                      'Long-term holders\' paper profit has only been this thin late in bear markets and at bottoms. There is no backtest of what followed; this is about position.', '升到 0.25 以上，離開底部那一端', 'A rise above 0.25, leaving the bottom end')
    if s in ('belief', 'euph'): return V('down', '老手獲利很厚，接近頂部區', 'Fat profits, near top territory', '過去四輪頂部，長期持有者 NUPL 都在 %.2f 以上，現在已在這個範圍。這張沒有回測之後的漲跌，看的是位置。' % tmin,
                                         'At the past four tops long-term holder NUPL was %.2f or higher, and it is in that range now. No backtest of what followed; this is about position.' % tmin, '回到 0.5 以下', 'A drop below 0.5')
    return V('neu', '中間，不在底也不在頂', 'Mid-range, neither bottom nor top', '長期持有者在「樂觀／焦慮」區：離歷次底部和頂部的讀數都還遠。', 'Long-term holders sit in the optimism/anxiety zone, far from both past bottom and top readings.', '跌破 0.25 或升破 0.5', 'Below 0.25 or above 0.5')
def rup(L):   # 依據 oc_extra 的近地板區回測（near.waves）
    r = O(L)['rup']; n = r['near']; wv = [w for w in n['waves'] if w.get('r365') is not None]; wu = sum(1 for w in wv if w['r365'] > 0)
    if r['value'] <= n['hi']: return V('up', '週期地板附近，底部區', 'Near the cycle floor: bottom territory', '過去 %d 波跌到這一帶，一年後價格%s；但每一波進來後半年內都還再跌過一段：地板不等於最低點。' % (len(wv), '都比當時高' if wu == len(wv) else '有 %d 波比當時高' % wu),
                                      'In the past %d waves into this zone price was %s a year later, but every wave fell further within six months: the floor is not the exact low.' % (len(wv), 'higher every time' if wu == len(wv) else 'higher in %d' % wu), '帳面獲利升回市值的 40% 以上，離開底部區', 'Paper profit back above 40% of market cap, leaving bottom territory')
    tmin = min(x['value'] for x in r['tops'])
    if r['value'] >= 60: return V('down', '帳面獲利很厚，接近頂部區', 'Fat paper profits, near top territory', '過去四輪頂部附近，帳面獲利都在市值的 %.0f%% 以上，現在已在這個範圍。' % tmin, 'Near the past four tops paper profit was %.0f%% of market cap or more, and it is in that range now.' % tmin, '回到 50% 以下', 'A drop below 50%')
    return V('neu', '不在底部也不在頂部', 'Neither bottom nor top', '離 %.0f%% 的週期地板和過去頂部的水準都還遠。' % r['floor'], 'Far from both the %.0f%% cycle floor and past-top levels.' % r['floor'])
def aviv(L):   # 依據跌破 1 之後一年的回測（aviv.r365）
    a = O(L)['aviv']; r = a['r365']; b = a['base365']
    if a['value'] >= 1.5:
        lo_, hi_ = min(x['value'] for x in a['tops']), max(x['value'] for x in a['tops'])
        return V('down', '活躍投資人賺很多，接近頂部區', 'Active investors well in profit, near top territory', '過去頂部是平均成本的 %.1f 到 %.1f 倍，現在已在這個範圍。' % (lo_, hi_), 'Past tops came at %.1f to %.1f times the average cost, and price is in that range now.' % (lo_, hi_), '回到 1.2 倍以下', 'A drop below 1.2×')
    if a['below']:
        worse = r['up'] * 100.0 / max(1, r['n']) < b['up']
        return V('neu', '活躍投資人在賠，熊市位置', 'Active investors underwater: bear-market ground', ('過去跌到成本下面之後，一年後比較高的機率%s隨便一天：熊市會在這裡待很久，跌破本身不是底。' % ('還不如' if worse else '只略高於')),
                 'After past breaks below cost, the odds of being higher a year on were %s any day: bear markets can sit here a long time, and the break itself is not a bottom.' % ('worse than' if worse else 'only slightly better than'), '價格站回活躍投資人的平均成本之上', 'Price back above active investors\' average cost')
    return V('up', '在成本上面，趨勢偏多', 'Above cost, trend on the up side', '活躍投資人整體在賺；這張沒有回測，看的是價格在成本的哪一邊。', 'Active investors are in profit as a group. No backtest here; it is about which side of cost price is on.', '跌回成本下面', 'A fall back below cost')
def rrisk(L):   # 依據進入低檔區之後一年的回測（rrisk.r365）
    r = O(L)['rrisk']; e = r['r365']
    if r['pct4'] <= 10:
        worse = e['up'] * 100.0 / max(1, e['n']) <= r['base365']['up']
        return V('neu', '便宜區，之後好壞參半', 'Cheap zone, mixed record', ('過去掉進這一區的幾段，一年後有漲有跌，整體不比隨便一天好：便宜可以更便宜。' if worse else '過去掉進這一區的幾段，一年後多半比當時高，但只有幾段。'),
                 ('Past stays in this zone were followed by gains and losses alike, no better than any day: cheap can get cheaper.' if worse else 'After past stays in this zone price was mostly higher a year on, but there are only a few.'), '離開近 4 年最低的 10%', 'Leaving the lowest 10% of four years')
    if r['pct4'] >= 90: return V('down', '偏貴，接近頂部區', 'Rich, near top territory', '在近 4 年最高的 10%，歷來接近頂部。', 'In the top 10% of four years, as near past tops.', '回到中間', 'A return to the middle')
    return V('neu', '中間，不便宜也不貴', 'Mid-range, neither cheap nor rich', '儲備風險在近 4 年的中間。', 'Reserve risk is in the middle of its four-year range.')
def pl(L):   # 2026-11-25 表態寫成區間判斷（使用者：不能寫「分批買」這種交易指令，用「長期的底部區間」表達；買不買、怎麼買是用戶自己決定）；依據 pl_bt.py 的回測
    import pl_bt
    p = C(L)['powerlaw']; lo, hi = p['bottom_band']; q = pl_bt.bt(L); low = round(p['fair'] * lo / 1000) * 1000
    if p['ratio'] <= hi and q: return V('up', '長期底部區間', 'Long-run bottom territory', '過去 %d 次跌到這個倍數，一年後價格都%s、中位數 %+d%%；但之後一年內最多還再跌 %d%%：底部區間不等於最低點。' % (q['eps'], '比當時高' if q['up'] == q['n'] else '多半比當時高', q['med'], abs(q['worst'])),
                                        'In the past %d episodes at this multiple, price was %s a year later, median %+d%%, but fell as much as another %d%% within that year: bottom territory is not the exact low.' % (q['eps'], 'higher every time' if q['up'] == q['n'] else 'mostly higher', q['med'], abs(q['worst'])),
                                        '跌到趨勢價的 %.2f 倍（約 $%s，歷史最低倍數）以下，這個規律就被打破' % (lo, format(low, ',')), 'A fall below %.2f× of trend (about $%s, the lowest multiple on record) would break the pattern' % (lo, format(low, ',')))
    if p['ratio'] >= p['next_top_ratio'][0]: return V('down', '長期頂部區間', 'Long-run top territory', '倍數進入下一輪頂部的推估區；過去頂部都出現在趨勢價的好幾倍，而且一輪比一輪低。', 'The multiple is inside the projected range for the next top; past tops came at several times trend, each lower than the last.', '回到推估區以下', 'A drop below that range')
    return V('neu', '長期位置在中間', 'Mid-range on the long run', '比趨勢價低，但還沒跌進歷次熊底的範圍，也離頂部區很遠。', 'Below trend but not yet in past bear-bottom territory, and far from the top zone.', '跌進 %.2f 倍以下' % hi, 'A drop below %.2f×' % hi)
def _top(name_z, name_e, hot, near, far_z, far_e, why_z, why_e):
    if hot: return V('down', '頂部跡象出現', 'Top signs are showing', why_z, why_e, '回到門檻以下', 'A drop back below the line')
    if near: return V('neu', '接近頂部門檻', 'Close to the top line', why_z, why_e, '跨過門檻', 'Crossing the line')
    return V('up', '離頂部還遠', 'Far from a top', far_z, far_e, '升到門檻附近', 'A move near the line')
def p6(L):
    p = C(L)['p6']; v = sorted(p.values()); hot = sum(1 for x in v if x >= 80) >= 2
    return _top('', '', hot, v[-2] >= 65, '三個指標都遠低於 80 的門檻（近 4 年最熱的 20%），看不到頂部跡象。', 'All three are well below 80 (the hottest 20% of four years): no sign of a top.', '任兩項到 80（近 4 年最熱的 20%）才算頂部區。', 'Any two at 80 (the hottest 20% of four years) make a top zone.')
def p20(L):   # 2026-11-25 改寫（WRITING.md）：0.75 是警戒線，不寫交易用語；理由用這張圖僅有的兩次頂部
    import reads_cycle
    v = C(L)['cm']['mvrv_vs_prior']; tk = reads_cycle.p20tops(L)
    hz = ('這張圖只有兩次頂部，頂部前比值都升到 %.2f 以上。' % min(tk)) if tk else ''
    he = (' The chart has only two tops, and before both the ratio rose above %.2f.' % min(tk)) if tk else ''
    r = _top('', '', v >= .75, v >= .65, '市場熱度只有前一輪頂部時的 %.0f%%，離 0.75 警戒線很遠。%s' % (v * 100, hz), 'Market heat is only %.0f%% of the last top\'s, far below the 0.75 warning line.%s' % (v * 100, he),
             '0.75 是警戒線：熱度到了前一輪頂部的四分之三。' + hz, '0.75 is the warning line: three-quarters of the last top\'s heat.' + he)
    return r[:5] + (('升到 0.65 以上，接近 0.75 警戒線', 'A rise above 0.65, near the 0.75 line') if v < .65 else ('站上 0.75 連 5 天', 'Five days above 0.75') if v < .75 else ('跌回 0.75 以下', 'A drop back below 0.75'))
def pi(L):   # 2026-11-25 改寫（WRITING.md）：理由寫過去碰到 1 的時候
    v = L['price']['pi_cycle']
    r = _top('', '', v >= 1, v >= .9, '碰到 1 代表價格幾個月內漲過頭，2013、2017、2021 年的頂部都在那前後，現在離那裡很遠；但 2025 年的頂部也沒碰到，所以它只能提醒，不能保證。',
             'A touch of 1 means price has run too far within months, as around the 2013, 2017 and 2021 tops, and today is far from it; but the 2025 top never reached it either, so it can warn but not promise.',
             '碰到 1 是過去頂部出現的位置；2013、2017、2021 年的頂部都在那前後，2025 年沒碰到。', 'A touch of 1 is where past tops came: around the 2013, 2017 and 2021 tops, though not in 2025.')
    return r[:5] + (('升到 0.9 以上，接近 1', 'A rise above 0.9, close to 1') if v < .9 else ('碰到 1', 'A touch of 1') if v < 1 else ('跌回 1 以下', 'A drop back below 1'))
def radar(L):   # 2026-11-25 改寫（WRITING.md）：百分位寫成「2022 年 11 月以來有多少日子比現在高」
    r = O(L)['top_radar']; ps = [x['pct_since_2022_11'] for x in r.values()]; hot = sum(1 for x in ps if x >= 90) >= 2
    v = _top('', '', hot, max(ps) >= 80, '2025 年頂部時三項同時到了極端，現在三項都離那時很遠。只對過一次頂部，三項也是事後挑的。',
             'At the 2025 top all three hit extremes together; today all three are far from that. Checked against only one top, and the three were picked after the fact.',
             '任兩項排到 2022 年 11 月以來最熱的 10% 就算頂部區；只對過一次頂部。', 'Any two in the hottest 10% of days since November 2022 make a top zone; checked against only one top.')
    return v[:5] + (('任兩項排到 2022 年 11 月以來最熱的 10%', 'Any two in the hottest 10% since November 2022') if not hot else ('回到最熱的 10% 以外', 'Dropping out of the hottest 10%'))
def tmh(L):   # 2026-11-25 改寫（WRITING.md）：Tidemark 是外部的綜合模型；沒有網站自己的回測，理由照實寫
    t = C(L)['tidemark']; tp, bt = t['top']['signal'], t['bottom']['signal']
    if bt >= 50 or (bt - tp >= 30): return V('up', '在模型的底部區' if bt >= 50 else '偏向底部，還沒進底部區', 'In the model\'s bottom zone' if bt >= 50 else 'Leaning to a bottom, not in the zone yet',
                                          '這個外部模型把估值和時間合起來看，離底部比離頂部近得多。它的歷史是用現在的規則回算的，不是當時真的這樣亮，網站也沒有自己回測過。',
                                          'Weighing valuation and timing, this outside model puts us much nearer a bottom than a top. Its history is back-calculated under today\'s rules, not what it showed at the time, and we have not backtested it ourselves.',
                                          '頂部分數升到 50（模型的頂部窗口）' if bt < 50 else '底部分數掉回 50 以下', 'A top score of 50 (the model\'s top window)' if bt < 50 else 'A bottom score back under 50')
    if tp >= 50 or (tp - bt >= 30): return V('down', '在模型的頂部窗口' if tp >= 50 else '偏向頂部，還沒進頂部窗口', 'In the model\'s top window' if tp >= 50 else 'Leaning to a top, not in the window yet',
                                          '這個外部模型把估值和時間合起來看，離頂部比離底部近得多。它的歷史是用現在的規則回算的，網站也沒有自己回測過。', 'Weighing valuation and timing, this outside model puts us much nearer a top than a bottom. Its history is back-calculated under today\'s rules, and we have not backtested it ourselves.',
                                          '頂部分數掉回 50 以下' if tp >= 50 else '底部分數升到 50', 'A top score back under 50' if tp >= 50 else 'A bottom score of 50')
    return V('neu', '兩邊都不明顯', 'Neither side is clear', '頂部和底部分數都在 50 以下、差距不大：這個外部模型現在看不出偏向。', 'Both scores are under 50 and close together: this outside model shows no lean.', '任一邊升到 50', 'Either score reaching 50')
tm = tmh
def lthloss(L):   # 2026-11-25 改寫（WRITING.md）：長期持有者＝幣放了 155 天以上沒動的人；位置寫「歷次熊底的範圍」
    x = O(L)['lthloss']; pk = x['peaks'][-1]['value']; pv = [p['value'] for p in x['peaks'][:-1]]; bp = (x.get('cohort') or {}).get('break_price')
    if x['value'] > pk: return V('down', '底部的規律被打破', 'The bottom pattern is broken', '長期持有者套牢的比例超過這一輪的高點：過去脫離底部之後都沒再發生過，底部可能還沒到。', 'The share of long-term holders underwater is above this cycle\'s peak: that never happened after past bottoms, so the bottom may not be in.', '回到這一輪高點以下', 'A drop back below the cycle peak')
    if x['value'] >= 40: return V('up', '歷次熊底的範圍', 'Past bear-bottom range', '過去 %d 輪這個比例衝到 %.0f–%.0f%% 的高點時，就是熊市底部附近；脫離底部之後都沒再超過那個高點。只有 %d 輪可以對照。' % (len(pv), min(pv), max(pv), len(pv)),
                                  'In the past %d cycles the share peaked at %.0f–%.0f%% around the bear-market bottom and never topped that after leaving it. Only %d cycles to compare.' % (len(pv), min(pv), max(pv), len(pv)),
                                  '收盤跌破分界價，套牢比例超過這一輪的高點' if bp else '套牢比例超過這一輪的高點', 'A close below the line, pushing the share above this cycle\'s peak' if bp else 'The share topping this cycle\'s peak')
    return V('neu', '離歷次熊底還遠', 'Away from past bear bottoms', '長期持有者大多還在賺錢；過去熊底時這個比例都在 %.0f%% 以上。' % min(pv), 'Most long-term holders are still in profit; at past bear bottoms the share was above %.0f%%.' % min(pv), '比例升到 40% 以上', 'The share rising above 40%')
def npl365(L):   # 2026-11-25 改寫（WRITING.md）：統一寫「賺錢賣出／賠錢賣出」；理由用這條線落後價格見底幾個月的事實
    import datetime as dt
    n = O(L)['npl365']; lg = [((dt.date.fromisoformat(b['date']) - dt.date.fromisoformat(b['bottom'])).days / 30.4) for b in n['bottoms'] if not b['now']]
    lag = ('過去 %d 輪，一年合計最深的時候都在價格見底之後 %d–%d 個月：這條線是一整年的加總，會落後價格。' % (len(lg), round(min(lg)), round(max(lg)))) if lg else ''
    lage = (' In the past %d cycles the one-year total bottomed %d–%d months after price did: it sums a whole year, so it lags price.' % (len(lg), round(min(lg)), round(max(lg)))) if lg else ''
    if n['value'] < 0 and n['value'] < n['v30']: return V('down', '認賠還沒走完', 'Loss-taking is not done', '過去一年的賠錢賣出還在增加。' + lag + '還在加深代表認賠還在進行，不代表價格一定還要跌。', 'Selling at a loss over the past year is still growing.' + lage + ' Still deepening means loss-taking is ongoing, not that price must fall further.', '一年合計開始往回升（賠錢賣出變少）', 'The one-year total turning back up')
    if n['value'] < 0: return V('up', '認賠在減少', 'Loss-taking is easing', '一年合計還是負的，但比 30 天前少：最重的認賠可能過了。' + lag, 'Still negative over a year but less than 30 days ago: the heaviest loss-taking may be past.' + lage, '一年合計再創這一輪新低', 'A new low for this cycle')
    if n['value'] > n['tops'][-1]['value'] * .8: return V('down', '賺錢賣出接近上一輪頂部', 'Profit-taking near last top\'s level', '一年合計的賺錢賣出接近上一輪頂部時的水準：以前這種程度都出現在頂部前後。', 'The one-year total of profit-taking is near its level at the last top: that much has come around past tops.', '一年合計明顯回落', 'A clear easing')
    return V('neu', '賺錢賣出不多', 'Mild profit-taking', '一年合計為正、不極端：看不出頂部或底部。', 'Positive over a year, not extreme: no sign of a top or a bottom.', '接近上一輪頂部的水準', 'Nearing the last top\'s level')
def agecost(L):   # 2026-11-25 改寫（WRITING.md）：位置寫「在近期買家成本上面／下面」，理由寫反彈遇到的解套賣壓和這一輪站回又跌破的事
    a = C(L)['age_cost']; c = a['c36']; up_ = [u for u in c.get('ups') or [] if u['date'] <= a['date']]; lu = up_[-1] if up_ else None
    if c['above']: return V('up', '站上近幾個月買家的成本', 'Above recent buyers\' cost', '收盤在近 3–6 個月買家的成本上面，這批人有賺錢，反彈比較不會遇到想解套的賣壓。', 'The close is above the cost of buyers from the last 3–6 months: they are in profit, so rallies meet less break-even selling.', '收盤跌回 %s 以下' % usd(c['cost']), 'A close below %s' % usd(c['cost']))
    rz = ('上一次站回是 %s，沒有守住。' % lu['date'][:7].replace('-', '/')) if lu else ''
    re_ = (' The last reclaim, in %s, did not hold.' % lu['date'][:7]) if lu else ''
    return V('down', '在近幾個月買家的成本下面', 'Below recent buyers\' cost', '收盤在近 3–6 個月買家的成本下面，這批人在虧損，反彈到這附近容易遇到想解套的賣壓。%s' % rz, 'The close is below the cost of buyers from the last 3–6 months: they are underwater, so rallies toward it meet break-even selling.%s' % re_, '收盤站回 %s' % usd(c['cost']), 'A close above %s' % usd(c['cost']))
def hashr(L):   # 2026-11-25 改寫（WRITING.md）：Capriole 原作者的叫法卡上一律寫成「原版訊號」
    hb = (O(L).get('bvx') or {}).get('hrib')
    if hb:   # 2026-11-19 照回測：2021 年以後原版訊號和隨便一天差不多，不管在不在投降都標中性
        q, b = hb['post'], hb['base_post']
        return V('neu', '礦工在投降，但近年不指方向' if hb['cap'] else '近年不比隨便一天好', 'Miners are capitulating, but it says little lately' if hb['cap'] else 'No better than any day lately',
                 '2021 年以後，Capriole 原版訊號之後一年價格 %d 次裡 %d 次較高、中位數 %+d%%；同期隨便一天是 %d%% 較高、中位數 %+d%%，差不多。' % (q['n'], q['up'], q['med'], b['up'], b['med']),
                 'Since 2021, price was higher a year after Capriole\'s original signal %d of %d times, median %+d%%; any day was higher %d%% of the time, median %+d%%, about the same.' % (q['up'], q['n'], q['med'], b['up'], b['med']),
                 '原版訊號之後的表現重新明顯好過隨便一天', 'The signal clearly beating any day again')
    h = O(L)['hash_ribbons']
    if h['capitulation']: return V('neu', '礦工在投降', 'Miners are capitulating', '投降期本身不是訊號，Capriole 原版看的是投降結束之後。', 'Capitulation itself is not the signal; the original looks at what comes after it ends.', '30 日平均回到 60 日平均上面', '30-day back above the 60-day')
    if h['state_days'] <= 30: return V('up', '剛從投降恢復', 'Just recovered', '從投降恢復歷來常在底部附近，但不是每次都準。', 'Recoveries have often come near bottoms, though not every time.', '再次跌回投降', 'A relapse into capitulation')
    return V('neu', '礦工健康', 'Miners are healthy', '算力穩定，這張圖現在不提供方向。', 'Hashrate is steady: the chart gives no direction now.', '跌進投降期', 'A drop into capitulation')
def cyccmp(L):   # 2026-11-25 改寫（WRITING.md）：背景圖，講這輪和前幾輪的時間表差在哪
    c = C(L)['cycle_cmp']; cur = next(x for x in c['cycles'] if x['now']); prev = [x for x in c['cycles'] if not x['now']]
    if cur['at']['pct'] > max(x['at']['pct'] for x in prev) + 10:
        return V('neu', '這輪跌得淺，舊時間表套不上', 'A shallow fall; the old timetable doesn\'t fit', '前幾輪頂部後都跌掉四分之三以上、大約一年後見底；這輪跌得淺得多。跌得淺可能代表這輪的底比較高，也可能還沒跌完，這張圖分不出來，只當背景。',
                 'Past cycles lost three quarters or more after the top and bottomed about a year later; this one has fallen far less. That could mean a higher bottom this time, or that the fall is not over. This chart cannot tell which, so treat it as context.')
    return V('neu', '只是背景，不指方向', 'Context only', '這輪頂部後的跌幅和前幾輪同一時間差不多或更深；但只有三輪可以比，時間表只當參考。', 'This cycle\'s fall since the top is about as deep as past cycles by the same day, or deeper; with only three to compare, the timetable is a guide at most.')
def dd(L):   # 2026-11-25 改寫：前提是這輪的低點守住，跌破就要重算
    x = O(L)['dd']['cyc']; bp = x['bottom_px']; more = sum(1 for d in x['past']['deep'] if d['v'] < x['value'])
    bz = x['bottom'][:7].replace('-', '/'); be = x['bottom'][:7]
    cz = '收盤跌破 %s 的低點 %s：這段就不算上升段，要重算' % (bz, usd(bp)); ce = 'A close below the %s low of %s: this would no longer count as an upswing and gets redrawn' % (be, usd(bp))
    if x['value'] > x['past']['p25']: return V('neu', '上升段裡一般的回檔', 'A typical pullback for an upswing', '前四輪的上升段裡，這種幅度的回檔很常見；這張只說明現在跌得多深，不說接下來的方向，而且前提是這輪的低點守住。',
                                               'Pullbacks of this size were common in the upswings of the past four cycles. This chart only says how deep the fall is, not where price goes next, and it assumes this cycle\'s low holds.', cz, ce)
    if x['past']['deeper'] <= 10: return V('up', '上升段裡少見的深回檔', 'A rare pullback for an upswing', '放在前四輪的上升段裡，這麼深的回檔很少見，過去出現時多半還在上升段中途；前提是這輪的低點守住。',
                                           'Pullbacks this deep were rare in the upswings of the past four cycles, and when they came the upswing was usually not over. That assumes this cycle\'s low holds.', cz, ce)
    return V('neu', '回撤偏深，但不算少見', 'Deep, but not unheard of',
             ('前四輪裡有 %d 輪的上升段出現過比現在更深的回檔。' % more if more else '前四輪上升段裡，比現在深的日子不少。') + '這張只說明現在跌得多深，不說接下來的方向，而且前提是這輪的低點守住。',
             ('In %d of the past four cycles the upswing saw a deeper pullback than this. ' % more if more else 'Past upswings had plenty of days deeper than this. ') + 'This chart only says how deep the fall is, not where price goes next, and it assumes this cycle\'s low holds.', cz, ce)
def capeff(L): return V('neu', '只是背景，不指方向', 'Context only', '比特幣越大，每一輪能漲的倍數越小、同樣的錢推得越少：這張幫你調低對下一輪漲幅的期待，但不說接下來往哪走。',
                        'The bigger Bitcoin gets, the smaller each cycle\'s run and the less each dollar moves it: useful for tempering hopes for the next run, but it says nothing about direction.')
def path(L):   # 2026-11-25 改寫：這是本站自己的推估；「會改變看法」寫白話
    m = C(L)['model']; t = m['top_model']; px = L['price']['bar']['c']; f = m.get('fan') or {}; need = f.get('need') or 10
    ends = all(ns[-1][2] > px for ns in m['nodes'].values())
    if t['median'] > px * 1.3: return V('up', '模型的長期路徑向上', 'Our long-run paths point up',
                                        '%s這是本站自己的推估，短期怎麼走四種各不相同。' % ('四種走法最後都比現價高；但' if ends else ''),
                                        '%shis is our own estimate, and the four paths differ on the way there.' % ('All four paths end above today\'s price, but t' if ends else 'T'),
                                        '收盤掉到四種走法最低那條的下方 12%% 以上、連 %d 天：四種走法都要重畫' % need, 'Closes more than 12%% below the lowest path for %d straight days: all four would need redrawing' % need)
    return V('neu', '接近模型估計的頂部', 'Near the modelled top', '價格已經接近頂部模型估計的下一輪頂部區間（%s–%s）。' % (usd(t['p10']), usd(t['p90'])), 'Price is close to the top model\'s range for the next top (%s–%s).' % (usd(t['p10']), usd(t['p90'])))
def long(L): return V('neu', '只是背景，不指方向', 'Context only', '這張讓你看現在落在全部歷史的哪裡、上一輪頂部離現在多遠。但頂部、底部和減半之間的時間規律只有三四輪，這輪又跌得比以前淺，不能拿來推下一步。',
                      'It shows where today sits in the whole history and how far back the last top was. But the timing between tops, bottoms and halvings rests on three or four cycles, and this one has fallen less than before, so it cannot predict the next move.')
def mon(L):
    m = L['price']['monthly']['cur']
    return V('neu', '只是背景，不指方向', 'Context only', '每個月份只有 %d 個樣本，一兩個極端年份就能把數字拉偏：季節性只描述過去，不能拿來判斷這個月或下個月的方向。' % m['n'],
             'Each month has only %d samples, and one or two extreme years can skew them: seasonality describes the past and cannot tell you which way this month or the next will go.' % m['n'])
def avgd(L):   # 2026-11-25 理由用 oc_extra.avg_viz 的回測（bk：讀值低於 15 的日子一年後）
    a = O(L)['avgd']; v = a['value']; bk = a.get('bk') or {}; lo, al = bk.get('lo'), bk.get('all')
    if v <= 20:
        rz = ('過去讀數在 15 以下的日子，一年後 %d%% 比當時高（隨便一天 %d%%）；但只有幾輪週期，而且第一次跌破 10 之後還可能再跌一段。' % (lo['up'], al['up'])) if lo and al else '歷來屬於便宜區，但不是底。'
        re_ = ('On days below 15, %d%% were higher a year later (any day: %d%%), but there are only a few cycles, and price could still fall after first breaking 10.' % (lo['up'], al['up'])) if lo and al else 'Historically a cheap zone, not a bottom.'
        return V('up', '便宜區，還不是底', 'Cheap zone, not a bottom yet', rz, re_, '平均排名回到 40 以上（歷史中段）', 'The average rank back above 40 (mid-history)')
    if v >= 80: return V('down', '貴區，接近頂部', 'Rich, near a top', '價格高出這些線的程度，歷史上很少比現在更多，歷來接近頂部。', 'Price has rarely been further above these lines, as near past tops.', '回到 60 以下', 'A drop below 60')
    return V('neu', '中間，不便宜也不貴', 'Mid-range, neither cheap nor rich', '價格離這些線的距離在歷史中段。', 'Price\'s distance from these lines is mid-range for history.')

# ══ 賣壓 ══
def pullback(L):
    x = O(L)['pullback']
    if x['n_ok'] >= 3: t = better(x['r90'], x['base90']); return V(t, '回調壓力在高點' if t != 'up' else '回調壓力可能見底', 'Pullback pressure is high' if t != 'up' else 'Pressure may be peaking', '過去三項同時成立後 90 天中位數 %s，任一天 %s：這張清單描述壓力，不是買點。' % (pc(x['r90']['med']), pc(x['base90']['med'])), 'After all three held, the 90-day median was %s versus %s on any day: it describes pressure, not an entry.' % (pc(x['r90']['med']), pc(x['base90']['med'])), '三項裡有兩項解除', 'Two of the three clearing')
    return V('neu', '回調壓力不大', 'Little pullback pressure', '成立的條件不到三項。', 'Fewer than three conditions hold.', '三項同時成立', 'All three holding')
def sx(L):
    s = L['chips']['stress']
    if s['state'] == 'bottom': return V(better(s['f90'], s['base90']), '底部組合成立', 'The bottom combination holds', '過去 90 天後 %d/%d 次上漲、中位數 %s（任一天 %s）；30 天內常還有一跌。' % (s['f90']['up'], s['f90']['n'], pc(s['f90']['med']), pc(s['base90']['med'])), '90 days on, %d of %d were higher, median %s (any day %s); another drop within 30 days was common.' % (s['f90']['up'], s['f90']['n'], pc(s['f90']['med']), pc(s['base90']['med'])), '賣壓歸零前再創新低', 'A new low before pressure resets')
    if s['state'] == 'strong': return V('up', '漲得又快又穩', 'A fast, steady rise', '強勢動能多半是行情延續。', 'Strong momentum has mostly meant continuation.', '動能跌破 0.5', 'Momentum below 0.5')
    if s['state'] in ('build', 'near'): return V('down', '賣壓在累積', 'Pressure is building', '弱勢在延續，還沒到底部組合。', 'Weakness is persisting, short of the bottom combination.', '賣壓到 100 且動能低於 0.3', 'Pressure at 100 with momentum under 0.3')
    return V('neu', '沒有賣壓', 'No pressure', '賣壓為零、動能普通。', 'Zero pressure and ordinary momentum.')
def profit(L):
    x = O(L)['sthl']; v = x['value']
    if v >= 60: t = better(x['stat30'], x['base30']); return V(t, '短期持有者大面積虧損', 'Short-term holders deep underwater', '升到 60%% 以上之後 30 天中位數 %s，任一天 %s；熊市裡會一路升到 90%% 以上。' % (pc(x['stat30']['med']), pc(x['base30']['med'])), 'After topping 60%%, the 30-day median was %s versus %s; in bears it climbs past 90%%.' % (pc(x['stat30']['med']), pc(x['base30']['med'])), '虧損比例再升到 90% 以上', 'A climb above 90%')
    if v <= 5: return V('down', '幾乎全部獲利', 'Nearly all in profit', '短期持有者幾乎全部獲利，獲利了結的壓力大。', 'Almost all short-term holders are in profit: heavy profit-taking pressure.', '回到 90% 以下', 'A drop below 90%')
    return V('neu', '中間區段', 'Middle zone', '短期持有者賺賠參半。', 'Short-term holders are split between profit and loss.')
def sopr(L):
    s = L['chips']['viz']['sopr']; d = s['dips']; cur = d[-1] if d and d[-1].get('open') else None; pv = d[-2] if cur and len(d) > 1 else None
    if s['value'] < 1 and cur and pv and cur['sopr'] < pv['sopr']: return V('down', '賠錢賣在加重', 'Loss-selling is getting heavier', '這次跌破比上一次更深。', 'This dip is deeper than the last.', '回到 1 以上', 'A move back above 1')
    if s['value'] < 1: return V('up', '賠錢賣在減輕', 'Loss-selling is easing', '還在 1 以下，但比上一次淺：賣壓遞減。', 'Still below 1 but shallower than the last dip: pressure is easing.', '跌得比上次深', 'A deeper dip than the last')
    return V('neu', '賣在成本之上', 'Selling above cost', '短期持有者賣出時有獲利。', 'Short-term holders are selling at a profit.')
soprf = sopr
def pnlr(L):
    p = O(L)['sth_pnl']
    if p['ratio'] < .5: return V('down', '認賠為主', 'Mostly loss-taking', '獲利只有虧損的 %.2f 倍。' % p['ratio'], 'Profit is only %.2f times loss.' % p['ratio'], '比值回到 1 以上', 'A ratio back above 1')
    if p['ratio'] > 2: return V('up', '獲利為主', 'Mostly profit-taking', '獲利是虧損的 %.2f 倍，短期持有者整體在賺。' % p['ratio'], 'Profit is %.2f times loss.' % p['ratio'], '比值掉到 1 以下', 'A ratio below 1')
    return V('neu', '賺賠相當', 'Balanced', '獲利和虧損差不多。', 'Profit and loss are similar.')
def sthsig(L):
    x = O(L)['sthsig']; side = 'up' if x['above200'] else 'dn'; g = x['cap'] if x['cap']['on'] or not x['tp']['on'] else x['tp']
    s, b = g[side]['f30'], x['base'][side]['f30']; d = s['up'] / float(s['n']) * 100 - b['up']; t = 'up' if d >= 8 else 'down' if d <= -8 else 'neu'
    nm = '集中認賠' if g is x['cap'] else '集中止盈'; ne = 'concentrated loss-taking' if g is x['cap'] else 'concentrated profit-taking'
    return V(t, '%s，在均線%s' % (nm, '上方' if x['above200'] else '下方'), '%s, %s the 200-day' % (ne.capitalize(), 'above' if x['above200'] else 'below'), '過去在 200 日均線%s時，30 天後 %d/%d 次上漲（任一天 %d%%）。' % ('上方' if x['above200'] else '下方', s['up'], s['n'], b['up']), 'Past cases %s the 200-day: %d of %d higher 30 days on (any day %d%%).' % ('above' if x['above200'] else 'below', s['up'], s['n'], b['up']), '收盤%s 200 日均線' % ('跌破' if x['above200'] else '站上'), 'A close %s the 200-day' % ('below' if x['above200'] else 'above'))
def conf(L):
    c = O(L)['sthconf']; nb = c['nb']
    if c['value'] >= nb: return V('up', '對趨勢有信心', 'Confident', '賣出的幣成本高於還在持有的：持有者沒在恐慌。', 'Coins sold cost more than coins held: holders are not panicking.', '跌到 −%g 以下' % nb, 'A drop below −%g' % nb)
    if c['value'] <= -nb: return V('down', '信心不足', 'Lacking confidence', '賣出的幣成本低於還在持有的：低價買的人在跑。', 'Coins sold cost less than coins held: cheap buyers are bailing.', '回到 +%g 以上' % nb, 'A rise above +%g' % nb)
    return V('neu', '轉換期', 'Transition', '±%g 之間，方向還不明確。' % nb, 'Between ±%g: no clear direction.' % nb, '離開 ±%g' % nb, 'Leaving ±%g' % nb)
def npl(L):
    n = O(L)['npl']
    if n['sum7_usd_m'] < 0: return V('down', '整體在認賠', 'Net loss-taking', '近 7 天淨實現損益為負。', 'Net realized P&L is negative over 7 days.', '7 天轉正', 'A positive 7-day total')
    return V('up', '整體在獲利了結', 'Net profit-taking', '近 7 天淨實現損益為正：賣出的人整體有賺，趨勢健康。', 'Net realized P&L is positive over 7 days: sellers are in profit, a healthy trend.', '7 天轉負', 'A negative 7-day total')
def agepl(L):
    a = O(L)['agepl']
    if a['lth_prof'] >= 60: return V('down', '老手在獲利了結', 'Old hands are taking profit', '6 個月以上的人佔實現獲利 60% 以上。', 'Holders of 6+ months take over 60% of realized profit.', '比重回到一半以下', 'The share back under half')
    if a['lth_loss'] >= 60: return V('neu', '老手也在認賠', 'Old hands are capitulating too', '6 個月以上的人佔實現虧損 60% 以上，常是投降的尾段。', 'Holders of 6+ months take over 60% of realized loss, often the tail of a capitulation.')
    return V('neu', '認賠在新手', 'Losses sit with newcomers', '認賠主要是近期進場的人，老手沒有大量出手。', 'Loss-taking is mostly recent buyers; old hands are not moving much.', '老手的實現獲利比重升過 60%', 'Old hands taking over 60% of profit')
def rpl(L):
    y = O(L).get('rpl365') or {}; w, s7 = y.get('w90'), y.get('s7')
    if w and s7:   # 2026-11-20 卡片打開是一年合計（使用者：判讀和大數字不能打架）；近期用最近 7 天合計（同一份 Bitview，合計相除）
        cz, ce = ('比值回升到 %.2f（最低點 %.2f 的 10%% 以上）' % (y['conf_at'], y['cur_low']), 'The ratio rising to %.2f (10%% above its %.2f low)' % (y['conf_at'], y['cur_low'])) if y.get('conf_at') else ('一年合計回到 1 以上', 'The one-year sum back above 1')
        if y['below'] and y.get('confirmed'): return V('up', '底部確認', 'Bottom confirmed', '一年合計低於 1，比值已從這一段最低點回升 10%；過去之後價格都沒再破底。', 'Below 1 over a year and already 10% off its low; in the past price never made a new low after that.', '價格跌破這一段的最低價', "Price breaking this spell's low")
        if y['below'] and s7 < 1: return V('down', '底部區、認賠還在加重', 'Bottom zone, losses still building', '一年合計低於 1，是過去週期的底部區；但最近 7 天認賠是獲利的 %.0f 倍，比值還沒從低點回升。' % (1 / s7), 'Below 1 over a year, where past cycles bottomed; but losses were %.0fx profits over the last 7 days and the ratio has not turned up from its low.' % (1 / s7), cz, ce)
        if y['below']: return V('neu', '底部區、未確認', 'Bottom zone, unconfirmed', '一年合計低於 1，過去都是週期底部區；最近 7 天獲利多於認賠，但比值還沒從低點回升 10%。', 'Below 1 over a year, a past cycle-bottom zone; profits led over the last 7 days, but the ratio is not yet 10% off its low.', cz, ce)
        if w['value'] < 1: return V('down', '認賠多於獲利', 'Losses outweigh profits', '一年合計在 1 以上，但 90 天合計已低於 1。', 'Above 1 over a year, but the 90-day sum is below 1.', '90 天合計回到 1 以上', 'The 90-day sum back above 1')
        if s7 < 1: return V('down', '短期轉弱', 'Weakening near term', '一年和 90 天合計在 1 以上，但最近 7 天認賠多於獲利。', 'Above 1 over a year and 90 days, but losses led over the last 7.', '7 天合計回到 1 以上', 'The 7-day sum back above 1')
        return V('up', '獲利多於認賠', 'Profits outweigh losses', '一年、90 天和最近 7 天合計都在 1 以上。', 'Above 1 over a year, 90 days and the last 7.', '7 天合計跌回 1 以下', 'The 7-day sum falling below 1')
    r = O(L)['rpl']
    if r['value'] < 1: return V('down', '認賠多於獲利', 'Losses outweigh profits', '90 天平均低於 1。', 'The 90-day average is below 1.', '回到 1 以上', 'A move back above 1')
    if r['last7'] < 1: return V('down', '短期轉弱', 'Weakening near term', '90 天還在 1 以上，但最近 7 天認賠多於獲利。', 'Still above 1 over 90 days, but losses led over the last 7.', '每日比值回到 1 以上', 'Daily readings back above 1')
    return V('up', '獲利多於認賠', 'Profits outweigh losses', '90 天和最近 7 天都在 1 以上。', 'Above 1 over both 90 days and the last 7.', '7 天跌回 1 以下', 'The 7-day falling below 1')
def rloss(L):
    r = O(L)['rloss']; c = (r.get('chain') or [{}])[-1]; k = c.get('kind')
    if k == 'break': return V('down', '背離被打破', 'Divergence broken', '價格更低、認賠反而更多：賣壓還在加重。', 'A lower price with bigger losses: pressure is still building.', '下一個峰值認賠變少', 'Smaller losses at the next peak')
    if k == 'div': return V('up', '認賠背離', 'Loss divergence', '價格更低、認賠卻更少：賣方在衰竭。', 'A lower price with smaller losses: sellers are tiring.', '背離被打破', 'The divergence breaking')
    if k == 'cap': return V(better(r['back']['cap']['r30'], r['base30']), '投降', 'Capitulation', '認賠比前一個峰值多 10%% 以上；過去投降之後 30 天中位數 %s。' % pc(r['back']['cap']['r30']['med']), 'Losses 10%%+ above the prior peak; past capitulations had a 30-day median of %s.' % pc(r['back']['cap']['r30']['med']))
    return V('neu', '峰值差不多', 'Similar peaks', '最近兩個認賠峰值差不多。', 'The last two loss peaks are similar.')
def ssr(L):
    s = O(L)['ssr']
    if s['pct4'] <= 10: return V(better(s['r365'], s['base365']), '賣的人少', 'Few sellers', '低檔區之後一年中位數 %s，任一天 %s；常在盤整末端。' % (pc(s['r365']['med']), pc(s['base365']['med'])), 'After the low zone the one-year median was %s versus %s; often late in a range.' % (pc(s['r365']['med']), pc(s['base365']['med'])), '離開低檔區', 'Leaving the low zone')
    if s['pct4'] >= 90: return V('down', '賣的人多', 'Many sellers', '實現的獲利加虧損在近 4 年高檔。', 'Realized profit plus loss is high for four years.', '回到中間', 'A return to the middle')
    return V('neu', '平常水準', 'Normal level', '近 4 年的中間。', 'Mid-range for four years.', '跌進低檔區', 'A drop into the low zone')
def sec(L):
    s = O(L)['sec']
    if s['value'] < s['th']: return V('up', '賣方衰竭', 'Sellers exhausted', '跌破 %g 之後，走完一年的每一次一年後都較高（樣本少）。' % s['th'], 'After each break below %g with a full year after, price was higher a year on (few cases).' % s['th'], '升回門檻以上', 'A move back above the line')
    return V('neu', '還沒衰竭', 'Not exhausted', '沒有在 %g 以下，這張現在不提供方向。' % s['th'], 'Not below %g: no direction from this chart now.' % s['th'], '跌破 %g' % s['th'], 'A drop below %g' % s['th'])
def mom(L):
    v = O(L)['mom']['value']
    return V('down', '沒有獲利推力', 'No profit-taking push', '賣出的幣整體在認賠，上漲少了獲利盤的推力。', 'Coins sold are at a loss overall: rallies lack a profit-taking tailwind.', '轉為正值', 'A positive reading') if v < 0 else V('up', '有獲利推力', 'Profit-taking push', '賣出的幣整體有獲利，勢能在多方。', 'Coins sold are in profit overall: momentum is up.', '轉為負值或出現頂背離', 'A negative reading or a top divergence')
def lthrl(L):
    x = O(L)['lthrl']
    if x['pct'] >= 95: return V('up', '長期持有者投降', 'Long-term holders capitulating', '認賠規模在 2015 年以來最高 5%，常是賣壓的尾段。', 'Losses in the top 5% since 2015, often the tail of selling.', '認賠快速消退', 'Losses fading fast')
    if x['pct'] >= 60: return V('down', '賣壓還沒清乾淨', 'Selling is not done', '長期持有者在現價附近仍有人認賠，但沒到投降的規模。', 'Some long-term holders still sell at a loss here, short of capitulation.', '升到投降規模或回落到平常', 'Capitulation scale, or a fade to normal')
    return V('neu', '平常水準', 'Normal', '長期持有者的認賠不多。', 'Long-term holder losses are small.')
def miners(L):
    m = O(L)['mining']; px = L['price']['bar']['c']; be = m['breakeven']
    if px < be['20J@0.06']: return V('down', '礦工在虧電費', 'Miners are losing money', '收盤低於主流礦機的電費兩平價，礦工被迫賣幣的壓力大。', 'The close is below break-even for mainstream rigs: miners may be forced sellers.', '價格回到兩平價之上', 'Price back above break-even')
    if px > be['25J@0.07']: return V('up', '礦工有利潤', 'Miners are profitable', '收盤高於三種礦機的兩平價。', 'The close is above break-even for all three rig types.', '跌破 20 J/TH 兩平價', 'A drop below the 20 J/TH break-even')
    return V('neu', '舊礦機在虧', 'Old rigs are losing', '主流礦機還有利潤，最舊的那一批在虧電費。', 'Mainstream rigs are profitable; only the oldest are under water.', '跌破 20 J/TH 兩平價', 'A drop below the 20 J/TH break-even')
def psx(L):   # 2026-11-19 獲利供給扣掉十年老幣（bv_more.py 第 6 項）：照「第一次跌破 45%」的回測；高的一端牛市初期也常到，不指方向（2026-11-25 文字照 WRITING.md 改寫）
    q = O(L)['bvx']['psx']; done = [c for c in q['cross45'] if c['y1'] is not None]; nup = sum(1 for c in done if c['y1'] > 0); wst = abs(min(c['worst'] for c in done)) if done else 0
    if q['ex'] <= 45 and done and nup == len(done): return V('up', '歷次熊底的位置', 'Where past bear bottoms were', '過去 %d 次第一次跌破 45%%，一年後價格都比當時高，但之間最多再跌 %d%%：底部區間不等於最低點。' % (len(done), wst), 'In all %d past first drops below 45%%, price was higher a year later, but it fell as much as another %d%% in between: bottom territory is not the exact low.' % (len(done), wst), '回到 60% 以上，離開熊底的位置', 'A return above 60%, out of bear-bottom territory')
    if q['ex'] >= 95: return V('neu', '幾乎全部在賺錢', 'Nearly all in profit', '95% 以上在牛市初期也常出現，之後還大漲，不能單獨當頂部訊號。', 'Readings above 95% also show up early in bull markets, before big gains: not a top signal on its own.', '跌破 45%', 'A drop below 45%')
    return V('neu', '不在熊底也不在高檔', 'Neither bottom nor top', '扣掉十年老幣後 %.1f%% 在賺錢：不在歷次熊底的位置，也不在高檔。' % q['ex'], '%.1f%% in profit excluding 10-year-old coins: neither where past bear bottoms were nor high.' % q['ex'], '跌破 45%', 'A drop below 45%')
def cvdd(L):   # 2026-11-24 CVDD（bv_more.py 第 8 項）：照「每一段第一次高出不到 25%」的回測；只有四輪，常數是事後調的，所以只到偏多、理由寫清楚（2026-11-25 文字照 WRITING.md 改寫）
    q = O(L)['bvx']['cvdd']; done = [e for e in q['eps'] if e['y1'] is not None]; nup = sum(1 for e in done if e['y1'] > 0); wst = abs(min(e['worst'] for e in done)) if done else 0
    if q['prem'] < 25 and done and nup == len(done): return V('up', '歷次熊底的位置', 'Where past bear bottoms were', '過去 %d 次第一次靠近到高出不到 25%%，一年後價格都比當時高，但之間最多再跌 %d%%；只有四輪，地板線的常數也是事後調的。' % (len(done), wst), 'In all %d past first moves to within 25%%, price was higher a year later, but fell as much as another %d%% in between; only four cycles, and the floor\'s constant was tuned after the fact.' % (len(done), wst), '收盤跌破 CVDD（從沒發生過），或回到高出 60% 以上', 'A close below CVDD (never seen), or back above 60%')
    if q['prem'] < 60: return V('neu', '靠近地板，但還沒到', 'Closer, not there yet', '收盤高出 CVDD %.1f%%；歷次熊底最近時是 %.1f%%–%.1f%%。' % (q['prem'], min(w['prem'] for w in q['lows']), max(w['prem'] for w in q['lows'])), 'The close is %.1f%% above CVDD; past bear lows came within %.1f%%–%.1f%%.' % (q['prem'], min(w['prem'] for w in q['lows']), max(w['prem'] for w in q['lows'])), '高出不到 25%', 'Under 25% above')
    return V('neu', '離地板遠', 'Far above the floor', 'CVDD 是熊底的參考線，離得遠時不指方向，也不是頂部訊號。', 'CVDD marks bear-low territory; far above it, it says nothing about direction and is not a top signal.', '高出不到 25%', 'Under 25% above')
def vddm(L):   # 2026-11-25 VDD 倍數（bv_more.py 第 10 項）：嚴格版底背離只有三次、都在熊底 → 偏多；放寬版和隨便一天差不多 → 中性（同日文字照 WRITING.md 改寫）
    q = O(L)['bvx']['vddm']; dv = q['div']; bs, bl, bb = q['bs'], q['bl'], q['base']
    if dv is not None and dv >= 2 and bs['n'] and bs['up'] == bs['n']: return V('up', '出現熊底才見過的強背離', 'A strong divergence, seen only at bear lows', '價格在低點，放久的幣卻動得是 60 天前的 %.1f 倍；過去 %d 次一年後價格都比當時高，但只有 %d 次。' % (dv, bs['n'], bs['n']), 'Price is at a low while long-held coins move %.1f× as much as 60 days earlier; all %d past cases were higher a year later, but there are only %d.' % (dv, bs['n'], bs['n']), '價格再創新低、倍數回落', 'A new price low with the multiple falling back')
    if dv is not None and dv >= 1.5: return V('neu', '較弱的底背離', 'A weak divergence', '價格在低點，倍數是 60 天前的 %.2f 倍：這種程度過去 %d 次有 %d 次一年後較高，和隨便一天的 %d%% 差不多，不能當底部證據。' % (dv, bl['n'], bl['up'], bb['up']), 'Price at a low with the multiple at %.2f× its level 60 days earlier: at this strength %d of %d past cases were higher a year later, about the same as any day (%d%%), so it is not evidence of a bottom.' % (dv, bl['up'], bl['n'], bb['up']), '倍數升到 60 天前的 2 倍以上（嚴格版）', 'The multiple reaching 2× its level 60 days earlier (strict)')
    if q['v'] > 2.9: return V('neu', '熱區', 'Hot zone', '放久的幣大量移動，過去多在牛市段出現，不能單獨當頂部訊號。', 'Long-held coins are moving heavily; this has mostly shown up in bull phases and is not a top signal on its own.', '回到 1.4 以下', 'A drop below 1.4')
    return V('neu', '沒有背離', 'No divergence', 'VDD 倍數 %.2f，價格和放久的幣的動靜沒有反向。' % q['v'], 'VDD Multiple %.2f, with no split between price and old-coin movement.' % q['v'], '價格在低點、倍數升到 60 天前的 2 倍以上', 'Price at a low with the multiple at 2× its level 60 days earlier')
def oldc(L):
    y5 = O(L)['bvx']['old']['y5']
    if y5['pct'] >= 90: return V('down', '老幣大量移動', 'Old coins are moving', '5 年以上的幣移動量在 2016 年以來最高 10%。', '5-year-old coins are moving at a top-tenth pace since 2016.', '回到平常', 'A return to normal')
    return V('neu', '老幣移動在平常範圍', 'Old-coin moves are ordinary', '5 年以上的幣第 %d 分位，不算多。' % y5['pct'], '5-year-old coins at the %dth percentile: not heavy.' % y5['pct'], '升到最高 10%', 'A move into the top tenth')

# ══ 價位 ══
def levels(L):
    lv = C(L)['levels']; tm = next(x for x in lv['levels'] if x['key'] == 'tmm')
    return V('down', '在多空分界下方', 'Below the bull–bear line', '收盤在真實市場均價 %s 下方，活躍投資人整體虧損。' % usd(tm['value']), 'The close is below the true market mean of %s: active investors are underwater.' % usd(tm['value']), '站回 %s' % usd(tm['value']), 'A close above %s' % usd(tm['value'])) if tm['dist_pct'] > 0 else \
           V('up', '在多空分界上方', 'Above the bull–bear line', '收盤在真實市場均價 %s 上方。' % usd(tm['value']), 'The close is above the true market mean of %s.' % usd(tm['value']), '跌破 %s' % usd(tm['value']), 'A close below %s' % usd(tm['value']))
def sthgap(L):
    z = O(L)['sth_bands']['now']['z']
    if z <= -1: return V('up', '短線超賣', 'Short-term oversold', '−1 標準差以下近 4 年只有不到 10% 的日子，賣壓多半已集中釋放。', 'Below −1 standard deviation on under a tenth of days in four years: selling has largely been released.', '跌到 −2 標準差', 'A drop to −2 standard deviations')
    if z >= 1: return V('down', '短線過熱', 'Short-term overheated', '+1 標準差以上，短期持有者獲利豐厚、容易獲利了結。', 'Above +1: short-term holders are well in profit and apt to sell.', '回到 +0.5 以下', 'A drop below +0.5')
    return V('up' if z > 0 else 'down', '在成本%s' % ('上方' if z > 0 else '下方'), '%s cost' % ('Above' if z > 0 else 'Below'), '收盤在短期持有者成本帶的%s半部。' % ('上' if z > 0 else '下'), 'The close is in the %s half of the band.' % ('upper' if z > 0 else 'lower'), '穿過成本線', 'A cross of the cost line')
def quant(L):
    q = O(L)['quant']
    if q['psip'] <= 55: return V('up', '獲利供給接近熊底水準', 'Supply in profit near bear-bottom levels', '獲利供給 %.0f%%；每輪熊底都短暫掉到 50%% 以下。' % q['psip'], '%.0f%% of supply is in profit; every bear bottom briefly dipped under 50%%.' % q['psip'], '回到 65% 以上', 'A return above 65%')
    if q['psip'] >= 95: return V('down', '幾乎全部獲利', 'Nearly all in profit', '獲利供給 95% 以上，獲利了結壓力大。', 'Over 95% in profit: heavy profit-taking pressure.', '回到 90% 以下', 'A drop below 90%')
    return V('neu', '中間區段', 'Middle zone', '獲利供給在中間。', 'Supply in profit is mid-range.')
def urpd(L):
    u = L['chips']['urpd']; px = L['price']['bar']['c']; b, a = u['below_cluster'], u['above_cluster']; db = px / b['range'][1] - 1; da = a['range'][0] / px - 1
    return V('neu', '下有支撐、上有解套', 'Support below, supply above', '下方大堆離 %.0f%%、上方大堆離 %.0f%%；籌碼只說哪裡有人，不說方向。' % (db * 100, da * 100), 'The pile below is %.0f%% away and the one above %.0f%%; supply says where holders are, not direction.' % (db * 100, da * 100), '跌破下方大堆', 'A break of the pile below')
def cohort(L):
    t = L['chips']['cohort']['tot']; px = L['chips']['cohort']['price']
    return V('down', '多數短期持有者套牢', 'Most short-term holders are underwater', '收盤在短期持有者平均成本 %s 下方，反彈容易遇到解套賣壓。' % usd(t['sth_cost']), 'The close is below their average cost of %s: rallies meet break-even selling.' % usd(t['sth_cost']), '站回 %s' % usd(t['sth_cost']), 'A close above %s' % usd(t['sth_cost'])) if px < t['sth_cost'] else \
           V('up', '短期持有者多數獲利', 'Most short-term holders are in profit', '收盤在短期持有者平均成本 %s 上方，下方有承接。' % usd(t['sth_cost']), 'The close is above their average cost of %s: support below.' % usd(t['sth_cost']), '跌破 %s' % usd(t['sth_cost']), 'A close below %s' % usd(t['sth_cost']))
def conc(L): return V('neu', '不指方向', 'No direction', '集中度只說價格離開這一帶時波動會不會放大，不說往哪邊。', 'Concentration says whether a move out of this band will be large, not which way.')
def strike(L):
    s = D(L)['viz']['options']['strikes']; pc_ = D(L)['pcr']['oi_pcr']
    return V('neu', '證據薄弱', 'Weak evidence', '最大痛點 %s、全部到期買權比賣權多（P/C %.2f）；到期前被拉向最大痛點的證據很薄。' % (usd(s['maxpain']), pc_), 'Max pain is %s and calls outnumber puts (P/C %.2f); the pull toward max pain is weakly supported.' % (usd(s['maxpain']), pc_))
def gex(L):
    g = D(L)['gex']
    return V('neu', '波動會%s' % ('被放大' if g['total'] < 0 else '被壓住'), 'Moves %s' % ('amplified' if g['total'] < 0 else 'damped'), '合計 Gamma 為%s：說的是波動大小，不是方向；這是推算。' % ('負' if g['total'] < 0 else '正'), 'Total gamma is %s: it speaks to volatility, not direction, and it is an estimate.' % ('negative' if g['total'] < 0 else 'positive'))
def liq(L):
    w = D(L)['liq_heat'].get('within5') or {}; a, b = w.get('above') or 0, w.get('below') or 0
    if b > a * 1.3: return V('down', '下方多單較多', 'More longs below', '下方 5%% 內待清算的多單多 %.1f 倍：跌下去容易連環強平。' % (b / max(a, 1)), '%.1fx more longs to liquidate within 5%% below: a fall could cascade.' % (b / max(a, 1)), '下方多單被清掉', 'Longs below being flushed')
    if a > b * 1.3: return V('up', '上方空單較多', 'More shorts above', '上方 5% 內待清算的空單較多：漲上去容易軋空。', 'More shorts to liquidate within 5% above: a rise could squeeze.', '上方空單被清掉', 'Shorts above being flushed')
    return V('neu', '兩邊差不多', 'Balanced', '上下 5% 內的待清算量差不多。', 'Liquidations within 5% are balanced on both sides.')
def book(L):
    t = L['orderbook']['totals']; r = t['wide_bid'] / t['wide_ask']
    if r >= 1.2: return V('up', '下方承接較厚', 'Thicker bids below', '買賣比 %.2f；掛單可以隨時撤，只看大概。' % r, 'Bid/ask ratio %.2f; orders can be pulled, so treat it as rough.' % r, '比值掉到 1 以下', 'A ratio under 1')
    if r <= .83: return V('down', '上方賣單較厚', 'Heavier asks above', '買賣比 %.2f。' % r, 'Bid/ask ratio %.2f.' % r, '比值回到 1 以上', 'A ratio above 1')
    return V('neu', '兩邊差不多', 'Balanced book', '買賣比 %.2f。' % r, 'Bid/ask ratio %.2f.' % r)
def legs(L):
    c = L['price']['swing']['current']
    return V('down', '下跌段還沒結束', 'The down leg is not over', '要收盤漲到 %s 才算轉成上漲段。' % usd(c['end_level']), 'It takes a close at %s to turn it into an up leg.' % usd(c['end_level']), '收盤到 %s' % usd(c['end_level']), 'A close at %s' % usd(c['end_level'])) if c['dir'] == 'down' else \
           V('up', '上漲段還沒結束', 'The up leg is not over', '要收盤跌到 %s 才算轉成下跌段。' % usd(c['end_level']), 'It takes a close at %s to turn it into a down leg.' % usd(c['end_level']), '收盤到 %s' % usd(c['end_level']), 'A close at %s' % usd(c['end_level']))
def k20(L):
    vp = L['price']['volprofile']; px = L['price']['bar']['c']; m = L['price']['ma']['sma20']
    if px < vp['va_low'] and px < m: return V('down', '短線偏弱', 'Weak near term', '收盤在價值區和 20 日均線下方。', 'The close is below the value area and the 20-day MA.', '站回 20 日均線', 'A close above the 20-day MA')
    if px > vp['va_high_outer'] and px > m: return V('up', '短線偏強', 'Strong near term', '收盤在價值區和 20 日均線上方。', 'The close is above the value area and the 20-day MA.', '跌回價值區', 'A drop back into the value area')
    return V('neu', '在價值區附近', 'Around the value area', '收盤在價值區裡或均線兩側。', 'The close is inside the value area or around the 20-day MA.')
def pcost(L):   # 2026-11-17 生產成本（pipeline/pcost.py）：有回測，照回測；參數是同一段歷史擬合的，理由裡寫明
    p = O(L)['pcost']; s, b = p['s90'], p['b90']
    if p['below']: return V('up' if s['med'] - b['med'] >= 3 else 'neu', '跌破生產成本', 'Below production cost', '過去跌破後 90 天 %d/%d 上漲、中位數 %s，任一天 %s；但這條線是用同一段歷史擬合的。' % (s['up'], s['n'], pc(s['med'], 0), pc(b['med'], 0)),
                            'In the past %d of %d breaks were higher 90 days later (median %s vs %s for any day), but the line was fitted on the same history.' % (s['up'], s['n'], pc(s['med'], 0), pc(b['med'], 0)), '收盤站回 %s 之上' % usd(p['cost']), 'A close back above %s' % usd(p['cost']))
    return V('neu', '在生產成本上方', 'Above production cost', '收盤比成本高 %.1f%%；這張在跌破時才有方向。' % p['gap'], 'The close is %.1f%% above cost; this chart only gives direction on a break.' % p['gap'], '收盤跌破 %s' % usd(p['cost']), 'A close below %s' % usd(p['cost']))
def floors(L):
    f = O(L)['bvx']['floors']
    if f['below']: return V('up', '跌破損失地板', 'Below a loss floor', '過去跌破地板多在週期底部附近（樣本少）。', 'Past breaks of the floors came near cycle bottoms (few cases).', '站回第一層之上', 'A move back above the first floor')
    return V('neu', '還在地板上方', 'Above the floors', '五層都沒破；這張在破地板時才有方向。', 'None of the five is broken; it only gives direction when one breaks.', '跌破第一層', 'A break of the first floor')
def tiercost(L):
    t = O(L)['bvx']['tiers']; px = L['price']['bar']['c']; c = t['cur'][1]
    return V('up', '在大戶成本之上', 'Above whale cost', '收盤在 1K–10K 顆那一層的成本 %s 上方；今年跌破都很短。' % usd(c), 'The close is above the 1K–10K tier\'s cost of %s; breaks this year were brief.' % usd(c), '跌破 %s' % usd(c), 'A close below %s' % usd(c)) if px > c else \
           V('down', '跌破大戶成本', 'Below whale cost', '收盤在 1K–10K 顆那一層的成本 %s 下方。' % usd(c), 'The close is below the 1K–10K tier\'s cost of %s.' % usd(c), '站回 %s' % usd(c), 'A close above %s' % usd(c))
def etfcost(L):
    e = F(L)['etfcost']
    return V('down', 'ETF 買家在虧損', 'ETF buyers are underwater', '收盤在 ETF 平均成本 %s 下方，連 %d 個交易日；近 30 天在淨流出。' % (usd(e['cost']), e['run']), 'The close is below the ETF average cost of %s for %d sessions, with net outflows over 30 days.' % (usd(e['cost']), e['run']), '站回 %s' % usd(e['cost']), 'A close above %s' % usd(e['cost'])) if e['below'] else \
           V('up', 'ETF 買家有獲利', 'ETF buyers are in profit', '收盤在 ETF 平均成本 %s 上方。' % usd(e['cost']), 'The close is above the ETF average cost of %s.' % usd(e['cost']), '跌破 %s' % usd(e['cost']), 'A close below %s' % usd(e['cost']))
def urpdchg(L):
    u = L['chips']['urpd_chg']
    if u['loss'] > u['gain'] * 3: return V('neu', '高位的人在認賠換手', 'High-cost holders are capitulating', '這 7 天移動的幣多是賠錢移動：高位籌碼換到低位，換完之後上方賣壓會變輕。', 'Most coins moved at a loss this week: high-cost supply is resetting lower, which lightens overhead selling once done.')
    return V('neu', '換手平常', 'Ordinary turnover', '賺錢和賠錢移動的差不多。', 'Coins moved at a profit and at a loss in similar amounts.')
def pnlb(L):
    a = O(L)['bvx']['pnl']['all']
    if a['pct10'] >= 85: return V('up', '虧損深度少見', 'Unusually deep losses', '虧 10%% 以上的比例比 2013 年以來 %d%% 的日子高，歷來在熊市後段。' % a['pct10'], 'The share down 10%%+ is higher than on %d%% of days since 2013, as late in past bears.' % a['pct10'], '虧損比例回落到一般', 'Losses easing back')
    return V('neu', '虧損深度一般', 'Ordinary loss depth', '虧損的深度不極端。', 'Loss depth is not extreme.')

# ══ 槓桿 ══
def fh(L):
    x = D(L)['fund_hist']; v = x['value']
    if v >= x['hot']['th']: return V(better(x['hot']['st'], x['base']) if better(x['hot']['st'], x['base']) == 'down' else 'down', '多單擁擠', 'Crowded longs', '多方付高費用，之後常有一次清洗。', 'Longs are paying up, often followed by a flush.', '回到 15% 以下', 'A drop below 15%')
    if v < 0: return V(better(x['neg']['st'], x['base']), '空方付費', 'Shorts are paying', '轉負之後 90 天中位數 %s，任一天 %s。' % (pc(x['neg']['st']['med']), pc(x['base']['med'])), 'After turning negative the 90-day median was %s versus %s.' % (pc(x['neg']['st']['med']), pc(x['base']['med'])), '轉回正值', 'A positive reading')
    return V('neu', '槓桿不擁擠', 'Leverage is not crowded', '費率為正但不高。', 'Funding is positive but modest.', '升到 30% 或轉負', 'Above 30% or negative')
def basis(L):
    m = D(L)['deriv']['basis_median']
    if m > 15: return V('down', '期貨太貴', 'Futures are rich', '基差 15% 以上代表槓桿多頭擁擠。', 'Basis above 15% means crowded leveraged longs.', '回到 10% 以下', 'Back under 10%')
    if m < 3: return V('up', '期貨便宜', 'Futures are cheap', '基差很低，市場偏悲觀。', 'A thin basis means a gloomy market.', '回到 5% 以上', 'Back above 5%')
    return V('neu', '基差正常', 'Normal basis', '3–15% 之間屬常態。', '3–15% is normal.')
def oih(L):
    o = D(L)['oi_hist']; up, pu = o['chg30'] > 0, o['px30'] > 0
    if up and not pu: return V('down', '逆勢加槓桿', 'Leverage building into a fall', '價格跌、未平倉增：之後容易有一邊被清算。', 'Price down, open interest up: one side is likely to be liquidated.', '未平倉回落', 'Open interest falling')
    if not up and not pu: return V('up', '槓桿在退', 'Leverage is unwinding', '價格跌、未平倉也減：清洗中，之後比較乾淨。', 'Price and open interest both down: a cleanup that leaves less leverage.', '未平倉重新堆高', 'Open interest rebuilding')
    if up and pu: return V('up', '新資金跟進', 'New money following', '價格和未平倉一起漲。', 'Price and open interest are rising together.', '價格轉跌、未平倉續增', 'Price falling while OI keeps rising')
    return V('neu', '空單回補', 'Short covering', '價格漲、未平倉減：多半是空單回補，持續性要再看。', 'Price up, open interest down: mostly short covering.')
def lsa(L):
    x = D(L)['ls_acct']; v = x['binance']
    if v >= x['p90']: return V(better(x['hi']['st'], x['base']), '散戶擠在多方', 'Retail crowded long', '前 10%% 之後 90 天中位數 %s，任一天 %s。' % (pc(x['hi']['st']['med']), pc(x['base']['med'])), 'After the top tenth the 90-day median was %s versus %s.' % (pc(x['hi']['st']['med']), pc(x['base']['med'])), '回到 %.0f%% 以下' % x['med'], 'A drop below %.0f%%' % x['med'])
    if v <= x['p10']: return V(better(x['lo']['st'], x['base']), '散戶擠在空方', 'Retail crowded short', '後 10%% 之後 90 天中位數 %s，任一天 %s。' % (pc(x['lo']['st']['med']), pc(x['base']['med'])), 'After the bottom tenth the 90-day median was %s versus %s.' % (pc(x['lo']['st']['med']), pc(x['base']['med'])), '回到中位數以上', 'A move above the median')
    return V('neu', '帳戶多空平常', 'Ordinary account split', '做多帳戶的比例在平常範圍。', 'The long share of accounts is ordinary.')
def lqv(L):
    x = D(L)['liq_vol']; s = x['d30']['share']; h = x['hi_long']
    if s >= h['th']: return V(better(h['st'], x['base']), '多單被大量清洗', 'Longs heavily flushed', '多單占比 %d%% 以上之後 90 天中位數 %s，任一天 %s；樣本少。' % (h['th'], pc(h['st']['med']), pc(x['base']['med'])), 'After long share above %d%%, the 90-day median was %s versus %s; few cases.' % (h['th'], pc(h['st']['med']), pc(x['base']['med'])), '多單占比回落到 60% 以下', 'A long share under 60%')
    return V('neu', '清算平常', 'Ordinary liquidations', '多空清算比例沒有一面倒。', 'Liquidations are not one-sided.')
def vol(L): return V('neu', '波動不指方向', 'Volatility has no direction', '隱含波動說的是預期波動多大，不說往哪邊。', 'Implied volatility speaks to how big moves may be, not which way.')
def ivt(L):
    x = D(L)['ivterm']
    if x['slope'] > 0: return V('down', '近月貴：市場緊張', 'Front end dear: stress', '期限結構倒掛，常見於急跌或清算潮。', 'An inverted curve is common in sharp falls and liquidation waves.', '回到正常（近月比遠月便宜）', 'A normal curve again')
    return V('neu', '期限結構正常', 'A normal curve', '遠月比近月貴，市場不緊張。', 'Longer expiries cost more: no stress.')
def oi(L): return V('neu', '證據薄弱', 'Weak evidence', '到期前價格被拉向最大痛點的證據很薄，這張看的是關卡在哪。', 'The pull toward max pain is weakly supported; read it for where the levels are.')
def prem(L):
    p = D(L)['prem']
    if p['a7'] < 0: return V(better(p['r30'], {'med': 0}) if p['r30']['n'] >= 5 else 'down', '在買下跌保護', 'Buying protection', '7 日平均偏賣權；過去轉負之後 30 天中位數 %s（%d 次）。' % (pc(p['r30']['med']), p['r30']['n']), 'Tilted to puts; after past turns negative the 30-day median was %s (%d cases).' % (pc(p['r30']['med']), p['r30']['n']), '轉為偏買權', 'A tilt back to calls')
    return V('up', '在買上漲', 'Buying upside', '7 日平均偏買權。', 'The 7-day average tilts to calls.', '轉為偏賣權', 'A tilt to puts')
def pcr(L):
    r = D(L)['pcr']['rr25']
    if r <= -5: return V('down', '偏防守', 'Defensive', '賣權比買權貴 %.1f 點，市場在買保護。' % -r, 'Puts are %.1f points dearer than calls: the market is buying protection.' % -r, '風險逆轉回到 −2 以上', 'Risk reversal back above −2')
    if r >= 3: return V('up', '偏進攻', 'Aggressive', '買權比賣權貴，市場在追上漲。', 'Calls are dearer than puts: the market is chasing upside.', '回到 0 以下', 'A drop below 0')
    return V('neu', '情緒平衡', 'Balanced', '風險逆轉接近 0。', 'Risk reversal is near zero.')
def fng(L):
    f = F(L)['fng_hist']; v = f['value']
    if v <= f['lo']: return V(better(f['f30'], f['base30']), '極度恐懼', 'Extreme fear', '過去極度恐懼之後 30 天中位數 %s，比任一天（%s）差：第一次掉進去常不是底。' % (pc(f['f30']['med']), pc(f['base30']['med'])), 'After extreme fear the 30-day median was %s, worse than any day (%s): the first drop in is often not the bottom.' % (pc(f['f30']['med']), pc(f['base30']['med'])), '回到 25 以上', 'A move above 25')
    if v >= f['hi']: return V(better(f['g30'], f['base30']), '極度貪婪', 'Extreme greed', '過去極度貪婪之後 30 天中位數 %s（樣本很少）。' % pc(f['g30']['med']), 'After extreme greed the 30-day median was %s (very few cases).' % pc(f['g30']['med']), '回到 75 以下', 'A drop below 75')
    return V('neu', '情緒不極端', 'Not extreme', '恐懼貪婪在中間。', 'Fear & Greed is mid-range.')
def wiki(L): return V('neu', '關注度不指方向', 'Attention has no direction', '散戶湧入時暴增，頂部和急跌都會；只有 4 次。', 'Spikes come with retail rushes at tops and crashes alike; only four cases.')
def oieth(L): return V('neu', '槓桿在哪一邊', 'Where leverage sits', 'ETH 和 BTC 的槓桿比例說的是投機往哪裡去，不說 BTC 的方向。', 'The ETH/BTC leverage split shows where speculation goes, not BTC\'s direction.')
def bfx(L):
    b = D(L)['bfx_margin']
    return V('neu', '看不出方向', 'No clear signal', '多單增減之後的表現和任一天差不多（%d%% 對 %d%%）。' % (b['up10']['up'], b['base']['up']), 'Moves in margin longs were followed by roughly ordinary returns (%d%% vs %d%%).' % (b['up10']['up'], b['base']['up']))
def hlw(L): return V('neu', '看變化不看水位', 'Watch changes, not levels', '大帳戶裡有做市和對沖，長期淨空是常態；歷史只有幾天。', 'Large accounts include market makers and hedgers, so a standing net short is normal; history is only days long.')

avgdc = avgd
def etf20(L):
    e = F(L)['etf20']
    if e['in_stretch']: return V('down', '在一段流出裡', 'Inside an outflow stretch', '20 個交易日合計低於 −%s 百萬美元的流出段還沒結束。' % format(-e['th'], ','), 'The 20-session total is still below −$%sM: the outflow stretch is ongoing.' % format(-e['th'], ','), '合計回到 −%s 百萬以上' % format(-e['th'], ','), 'A total back above −$%sM' % format(-e['th'], ','))
    return V('up' if e['sum'] > 0 else 'neu', '20 日合計為%s' % ('正' if e['sum'] > 0 else '負'), 'The 20-session total is %s' % ('positive' if e['sum'] > 0 else 'negative'), '20 個交易日合計 %s 百萬美元。' % format(int(e['sum']), ','), '$%sM over 20 sessions.' % format(int(e['sum']), ','))
def treasury(L):
    m = F(L)['treasury']['mstr']
    if m['pnl_pct'] < 0: return V('down', '最大買家帳面虧損', 'The biggest buyer is underwater', 'Strategy 的平均成本 %s 在收盤之上；它靠發股發債買幣，虧損時加碼的能力受限。' % usd(m['cost']), 'Strategy\'s average cost of %s is above the close; it funds buying with stock and debt, which gets harder underwater.' % usd(m['cost']), '站回 %s' % usd(m['cost']), 'A close above %s' % usd(m['cost']))
    return V('neu', '最大買家有獲利', 'The biggest buyer is in profit', 'Strategy 的平均成本在收盤之下。', 'Strategy\'s average cost is below the close.')
def pr_neg(L): return pr_us(L)
def usdt_usd(L):
    u = F(L)['cb_premium']['usdt']
    if u['disc7_pct_own'] <= 10: return V('down', '穩定幣在換回美元', 'Stablecoins are being cashed out', 'USDT 7 日平均折價在近四年最低 10%：有人把穩定幣換回美元，場外資金在退。', 'USDT\'s 7-day discount is in its lowest tenth of four years: holders are swapping back to dollars.', '折價收斂到 −0.05% 以內', 'The discount narrowing inside −0.05%')
    return V('neu', '穩定幣貼近 1 美元', 'Stablecoins near $1', 'USDT 折價不深。', 'USDT\'s discount is shallow.')
def whstrip(L):
    T = {t['key']: t for t in O(L)['whales']['strip']['tiers']}; a, b = T['1k_10k']['up'], T['100_1k']['up']
    if a and b: return V('up', '兩層大戶都在加', 'Both large tiers are adding', '1K–10K 和 100–1K 顆兩層 7 天都在增加。', 'Both the 1K–10K and 100–1K tiers added over 7 days.', '其中一層轉為減少', 'Either tier turning down')
    if not a and not b: return V('down', '兩層大戶都在減', 'Both large tiers are trimming', '1K–10K 和 100–1K 顆兩層 7 天都在減少。', 'Both large tiers trimmed over 7 days.', '其中一層轉為增加', 'Either tier turning up')
    return V('neu', '大戶一加一減', 'Large tiers are split', '1K–10K 顆在%s、100–1K 顆在%s，方向不一致。' % ('加' if a else '減', '加' if b else '減'), 'The 1K–10K tier is %s and the 100–1K tier %s.' % ('adding' if a else 'trimming', 'adding' if b else 'trimming'))
def supliq(L):
    m = O(L)['metrics']; il = m['illiquid-supply']['chg30_pct']
    return V('up', '幣在流向不賣的人', 'Coins are moving to holders who do not sell', '非流動性供給 30 天 %s。' % pc(il), 'Illiquid supply is %s over 30 days.' % pc(il), '30 天轉為減少', 'A 30-day decrease') if il > 0 else V('down', '幣在流向會賣的人', 'Coins are moving to active sellers', '非流動性供給 30 天 %s。' % pc(il), 'Illiquid supply is %s over 30 days.' % pc(il), '30 天轉為增加', 'A 30-day increase')
def cvdsz(L):
    b = F(L)['cvd_size']['d30'][2]
    return V('down', '大單在賣', 'Large orders are selling', '近 30 天 10 萬美元以上的主動單淨賣出。', 'Taker orders over $100K net sold over 30 days.', '大單轉為淨買', 'Large orders turning net buyers') if b < 0 else V('up', '大單在買', 'Large orders are buying', '近 30 天 10 萬美元以上的主動單淨買入。', 'Taker orders over $100K net bought over 30 days.', '大單轉為淨賣', 'Large orders turning net sellers')
def r2y(L):
    g = F(L)['rates2y']['gap']
    if g >= .5: return V('down', '債市押升息', 'Bonds price hikes', '2 年期殖利率高出聯準會利率 %.2f 個百分點；利率往上對不生息資產是逆風。' % g, 'The 2-year yield is %.2f points above the policy rate; rising rates are a headwind for non-yielding assets.' % g, '差距回到 0 附近', 'The gap back near zero')
    if g <= -.5: return V('up', '債市押降息', 'Bonds price cuts', '2 年期殖利率低於聯準會利率，市場在押降息。', 'The 2-year yield sits below the policy rate: cuts are priced.', '差距回到 0 附近', 'The gap back near zero')
    return V('neu', '利率預期持平', 'Rates seen flat', '2 年期和聯準會利率差不多。', 'The 2-year yield is close to the policy rate.')
def fedmkt(L):
    f = F(L)['fed_mkt']
    if f['lead'] == 'up': return V('down', '市場押升息', 'Markets bet on a hike', '下次決議升息機率 %.0f%%。' % f['lead_p'], 'A %.0f%% chance of a hike at the next decision.' % f['lead_p'], '升息機率掉到一半以下', 'Hike odds below half')
    if f['lead'] == 'down': return V('up', '市場押降息', 'Markets bet on a cut', '下次決議降息機率 %.0f%%。' % f['lead_p'], 'A %.0f%% chance of a cut at the next decision.' % f['lead_p'], '降息機率掉到一半以下', 'Cut odds below half')
    return V('neu', '市場押不變', 'Markets expect a hold', '下次決議最可能不變。', 'A hold is most likely at the next decision.')

FN = {k: v for k, v in dict(globals()).items() if callable(v) and not k.startswith('_') and k not in ('V', 'pc', 'usd', 'better', 'O', 'F', 'D', 'C')}
FN.update({'pr-us': pr_us, 'pr-asia': pr_asia, 'pr-perp': pr_perp, 'pr-neg': pr_neg, 'usdt-usd': usdt_usd})
