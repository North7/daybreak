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
def dawn(L):
    d = C(L)['dawn']; st = next(x for x in d['stats'] if x['stage'] == d['stage']); t = better(st['y1'], d['base'], gap=10)
    nm = ['深夜', '入夜', '破曉', '白晝', '黃昏'][d['stage']]; ne = ['deep night', 'nightfall', 'daybreak', 'daylight', 'dusk'][d['stage']]
    return V(t, '%s：%s' % (nm, {'up': '估值便宜', 'down': '估值偏貴', 'neu': '中間地帶'}[t]), '%s: %s' % (ne.capitalize(), {'up': 'cheap', 'down': 'rich', 'neu': 'middling'}[t]),
             '過去這個階段之後一年中位數 %s，任一週 %s。' % (pc(st['y1']['med'], 0), pc(d['base']['med'], 0)), 'After this stage the one-year median was %s, versus %s for any week.' % (pc(st['y1']['med'], 0), pc(d['base']['med'], 0)), '熱度升到 45 以上（破曉）', 'Heat above 45 (daybreak)' if t == 'up' else 'A change of stage')
def stage(L):
    S = C(L)['stage']; s = S['stage']; px = L['price']['bar']['c']; gap = (px / S['sma200'] - 1) * 100
    # 2026-11-20：牛市成立後鎖定，標籤反應慢。收盤跌回 200 日均線下時，標籤還是牛市但趨勢已經不支持，偏向改中性（原本一律偏多，和卡上的數字打架）
    if s == '牛市' and gap < 0: return V('neu', '牛市標籤鎖定中', 'Bull label, locked', '牛市成立後鎖定，要在下降的 200 日均線下連 30 天才退回熊市，標籤反應慢；收盤已在均線下 %.0f%%，趨勢不支持偏多。' % -gap, 'Bull is locked once set and only reverts after 30 days under a falling 200-day MA, so the label is slow; the close is %.0f%% below the MA, so the trend no longer supports a bullish lean.' % -gap, '收盤站回 200 日均線之上', 'A close back above the 200-day MA')
    if s == '牛市': return V('up', '牛市階段', 'Bull stage', '投降出現過、價格曾在上升的 200 日均線上站滿 30 天；跌在下降的均線下 30 天才退回熊市。', 'A capitulation happened and price held 30 days above a rising 200-day MA; it takes 30 days under a falling MA to revert.', '在下降的 200 日均線下 30 天', '30 days under a falling 200-day MA')
    if s == '熊市': return V('down', '熊市階段', 'Bear stage', '還沒有投降加站上上升的 200 日均線。', 'No capitulation plus close above a rising 200-day MA yet.', '收盤站上上升的 200 日均線', 'A close above a rising 200-day MA')
    return V('neu', '轉換期', 'Transition', '介於熊市和牛市之間。', 'Between bear and bull.', '站上均線 30 天或跌回 5 天', '30 days above or 5 below the average')
def regime(L):
    r = C(L)['regime']
    return V('up' if r['value'] > 0 else 'down', '週線分數為%s' % ('正' if r['value'] > 0 else '負'), 'Weekly score is %s' % ('positive' if r['value'] > 0 else 'negative'), '六項合成分數 %s；連 4 週在另一邊才正式翻轉。' % ('%+.2f' % r['value']).replace('-', '−'), 'The six-input score is %s; it takes four weeks on the other side to flip.' % ('%+.2f' % r['value']).replace('-', '−'), '分數回到%s' % ('負值' if r['value'] > 0 else '正值'), 'The score crossing back')
def hnupl(L):
    s = O(L)['hnupl']['stage']
    if s in ('cap', 'hope'): return V('up', '長期持有者獲利很薄', 'LTH profit is thin', '長期持有者的帳面獲利在歷來底部附近的區間。', 'Long-term holder paper profit is in the range seen near past bottoms.', '升到 0.5 以上', 'A rise above 0.5')
    if s in ('belief', 'euph'): return V('down', '長期持有者獲利很厚', 'LTH profit is fat', '長期持有者的帳面獲利在歷來頂部附近的區間。', 'Long-term holder paper profit is in the range seen near past tops.', '回到 0.5 以下', 'A drop below 0.5')
    return V('neu', '中間區段', 'Middle zone', '長期持有者在「樂觀／焦慮」區，不在底部也不在頂部。', 'Long-term holders sit in the optimism/anxiety zone: neither bottom nor top.', '跌破 0.25 或升破 0.5', 'Below 0.25 or above 0.5')
def rup(L):
    r = O(L)['rup']; n = r['near']
    if r['value'] <= n['hi']: return V('up', '接近週期地板', 'Near the cycle floor', '近地板區之後一年 %d%% 較高（任一天 %d%%）；但 90 天內常再跌一段。' % (n['s365']['up'], n['b365']['up']), '%d%% were higher a year after the near-floor zone (any day: %d%%), though another drop within 90 days was common.' % (n['s365']['up'], n['b365']['up']), '升回 40% 以上', 'A move back above 40%')
    if r['value'] >= 60: return V('down', '獲利很厚', 'Profits are fat', '未實現獲利佔市值 60% 以上，歷來接近頂部。', 'Paper profit above 60% of market cap has come near past tops.', '回到 50% 以下', 'A drop below 50%')
    return V('neu', '中間區段', 'Middle zone', '離地板和頂部都還遠。', 'Far from both the floor and the top zone.')
def aviv(L):
    a = O(L)['aviv']
    if a['value'] >= 1.5: return V('down', '活躍投資人獲利很厚', 'Active investors are well in profit', '1.5 倍以上歷來接近頂部。', 'Readings above 1.5 have come near past tops.', '回到 1.2 以下', 'A drop below 1.2')
    if a['below']: return V('neu', '虧損，但不是買點', 'Underwater, not a buy signal', '低於 1 之後一年 %d/%d 次上漲，比任一天（%d%%）還差：熊市裡會在 1 以下待很久。' % (a['r365']['up'], a['r365']['n'], a['base365']['up']), 'After falling below 1, %d of %d were higher a year on, worse than any day (%d%%): bears can sit below 1 for long.' % (a['r365']['up'], a['r365']['n'], a['base365']['up']), '站回 1 以上', 'A move back above 1')
    return V('up', '站在 1 以上', 'Above 1', '活躍投資人整體有獲利，趨勢在多方。', 'Active investors are in profit as a group: the trend is up.', '跌破 1', 'A drop below 1')
def rrisk(L):
    r = O(L)['rrisk']
    if r['pct4'] <= 10: return V('neu', '便宜，但過去結果不一', 'Cheap, mixed record', '低檔區之後一年 %d/%d 段上漲、中位數 %s，不比任一天好。' % (r['r365']['up'], r['r365']['n'], pc(r['r365']['med'])), 'After the low zone, %d of %d stretches were higher a year on, median %s: no better than any day.' % (r['r365']['up'], r['r365']['n'], pc(r['r365']['med'])), '離開低檔區', 'Leaving the low zone')
    if r['pct4'] >= 90: return V('down', '偏貴', 'Rich', '近 4 年最高 10%，歷來接近頂部。', 'In the top tenth of four years, as near past tops.', '回到中間', 'A return to the middle')
    return V('neu', '中間區段', 'Middle zone', '儲備風險在近 4 年的中間。', 'Reserve risk is in the middle of its four-year range.')
def pl(L):
    p = C(L)['powerlaw']; lo, hi = p['bottom_band']
    if p['ratio'] <= hi: return V('up', '長期很便宜', 'Cheap on the long trend', '價格落在歷次底部的倍數帶（%.2f–%.2f 倍）。' % (lo, hi), 'Price sits in the band of past bottoms (%.2f–%.2f×).' % (lo, hi), '回到 0.7 倍以上', 'A move above 0.7×')
    if p['ratio'] >= p['next_top_ratio'][0]: return V('down', '接近推估的頂部倍數', 'Near the projected top multiple', '倍數進入下一輪頂部的推估區。', 'The multiple is inside the projected range for the next top.', '回到推估區以下', 'A drop below that range')
    return V('neu', '趨勢下方的中間', 'Below trend, mid-range', '比冪律合理價低，但不在底部帶。', 'Below fair value but outside the bottom band.')
def _top(name_z, name_e, hot, near, far_z, far_e, why_z, why_e):
    if hot: return V('down', '頂部跡象出現', 'Top signs are showing', why_z, why_e, '回到門檻以下', 'A drop back below the line')
    if near: return V('neu', '接近頂部門檻', 'Close to the top line', why_z, why_e, '跨過門檻', 'Crossing the line')
    return V('up', '離頂部還遠', 'Far from a top', far_z, far_e, '升到門檻附近', 'A move near the line')
def p6(L):
    p = C(L)['p6']; v = sorted(p.values()); hot = sum(1 for x in v if x >= 80) >= 2
    return _top('', '', hot, v[-2] >= 65, '三個指標都離 80 很遠，沒有頂部跡象；它只能說離頂部多遠，不說底部。', 'All three are far below 80: no top signs. It only measures distance from a top, not from a bottom.', '任兩項到 80 才算頂部區。', 'Any two at 80 make a top zone.')
def p20(L):
    v = C(L)['cm']['mvrv_vs_prior']
    return _top('', '', v >= .75, v >= .65, 'MVRV 只有前一輪高點的 %.2f 倍，離 0.75 很遠。' % v, 'MVRV is only %.2f of the prior peak, far from 0.75.' % v, '0.75 是頂部警戒線。', '0.75 is the top warning line.')
def pi(L):
    v = L['price']['pi_cycle']
    return _top('', '', v >= 1, v >= .9, '只有 %.2f，離觸發（1）很遠。' % v, 'Only %.2f, far from the trigger at 1.' % v, '到 1 觸發。', 'It fires at 1.')
def radar(L):
    r = O(L)['top_radar']; ps = [x['pct_since_2022_11'] for x in r.values()]
    return _top('', '', sum(1 for x in ps if x >= 90) >= 2, max(ps) >= 80, '三項都不在本輪的高檔（最高第 %d 百分位）。' % round(max(ps)), 'None of the three is high for this cycle (top reading: the %dth percentile).' % round(max(ps)), '兩項到本輪第 90 百分位算頂部區。', 'Two at this cycle\'s 90th percentile make a top zone.')
def tmh(L):
    t = C(L)['tidemark']; tp, bt = t['top']['signal'], t['bottom']['signal']
    if bt >= 50 or (bt - tp >= 30): return V('up', '偏向底部那一邊', 'Leaning to the bottom side', '底部訊號 %.0f、頂部訊號 %.0f：模型認為更接近底部。' % (bt, tp), 'Bottom signal %.0f, top signal %.0f: the model sees it closer to a bottom.' % (bt, tp), '頂部訊號升到 50', 'A top signal of 50')
    if tp >= 50 or (tp - bt >= 30): return V('down', '偏向頂部那一邊', 'Leaning to the top side', '頂部訊號 %.0f、底部訊號 %.0f。' % (tp, bt), 'Top signal %.0f, bottom signal %.0f.' % (tp, bt), '頂部訊號回到 50 以下', 'A top signal back under 50')
    return V('neu', '兩邊都不明顯', 'Neither side is clear', '頂部和底部訊號都在 50 以下、差距不大。', 'Both signals are under 50 and close together.')
tm = tmh
def lthloss(L):
    x = O(L)['lthloss']; pk = x['peaks'][-1]['value']
    if x['value'] > pk: return V('down', '規律被打破', 'The pattern is broken', '長期持有者虧損比例超過這輪高點：脫離底部後不再創新高的規律失效。', 'The long-term holder loss share is above this cycle\'s peak: the no-new-high pattern has failed.', '回到這輪高點以下', 'A drop back below the cycle peak')
    if x['value'] >= 40: return V('up', '在歷輪底部區間', 'In the past-bottom range', '虧損比例落在歷輪熊底的 42–53%% 附近，而且還沒超過這輪高點 %.1f%%。' % pk, 'The share sits near the 42–53%% range of past bear bottoms and has not topped this cycle\'s %.1f%%.' % pk, '超過這輪高點 %.1f%%' % pk, 'Topping %.1f%%' % pk)
    return V('neu', '離底部區間還遠', 'Away from the bottom range', '長期持有者大多還在獲利。', 'Most long-term holders are still in profit.')
def npl365(L):
    n = O(L)['npl365']
    if n['value'] < 0 and n['value'] < n['v30']: return V('down', '認賠還在加深', 'Loss-taking is deepening', '一年累計還在往下：認賠還沒走完。', 'The one-year total is still falling: loss-taking is not done.', '開始往回升', 'A turn back up')
    if n['value'] < 0: return V('up', '認賠在收斂', 'Loss-taking is easing', '一年累計還是負的，但比 30 天前少：最壞的認賠可能過了。', 'Still negative over a year but less than 30 days ago: the worst may be past.', '再創新低', 'A new low')
    if n['value'] > n['tops'][-1]['value'] * .8: return V('down', '獲利了結很多', 'Heavy profit-taking', '一年累計接近上一輪頂部的水準。', 'The one-year total is near the last top\'s level.', '回落', 'An easing')
    return V('neu', '獲利了結溫和', 'Mild profit-taking', '一年累計為正、不極端。', 'Positive over a year, not extreme.')
def agecost(L):
    c = C(L)['age_cost']['c36']
    return V('up', '站上近期買家成本', 'Above recent buyers\' cost', '收盤在 3–6 個月買家成本 %s 之上，這批人有獲利。' % usd(c['cost']), 'The close is above the 3–6 month buyers\' cost of %s: they are in profit.' % usd(c['cost']), '跌回 %s 以下' % usd(c['cost']), 'A close below %s' % usd(c['cost'])) if c['above'] else \
           V('down', '在近期買家成本下方', 'Below recent buyers\' cost', '收盤在 3–6 個月買家成本 %s 之下，這批人在虧損，反彈容易遇到解套賣壓。' % usd(c['cost']), 'The close is below the 3–6 month buyers\' cost of %s: rallies meet break-even selling.' % usd(c['cost']), '站回 %s' % usd(c['cost']), 'A close above %s' % usd(c['cost']))
def hashr(L):
    hb = (O(L).get('bvx') or {}).get('hrib')
    if hb:   # 2026-11-19 照回測：2021 年以後原版買點和隨便一天差不多，不管在不在投降都標中性
        q, b = hb['post'], hb['base_post']
        return V('neu', '礦工在投降' if hb['cap'] else '近年不比隨便一天好', 'Miners are capitulating' if hb['cap'] else 'No better than any day lately',
                 '2021 年以後原版買點一年後 %d 次裡 %d 次漲、中位數 %+d%%；隨便一天 %d%% 漲、中位數 %+d%%。' % (q['n'], q['up'], q['med'], b['up'], b['med']),
                 'Since 2021 the original buy was up a year later %d of %d times, median %+d%%; any day was up %d%% of the time, median %+d%%.' % (q['up'], q['n'], q['med'], b['up'], b['med']),
                 '買點之後的勝率明顯高過隨便一天', 'Buys clearly beating any day')
    h = O(L)['hash_ribbons']
    if h['capitulation']: return V('neu', '礦工在投降', 'Miners are capitulating', '投降期本身不是買點，等它恢復。', 'Capitulation itself is not the signal; the recovery is.', '30 日均回到 60 日均之上', '30-day back above the 60-day')
    if h['state_days'] <= 30: return V('up', '剛從投降恢復', 'Just recovered', '從投降恢復歷來常在底部附近，但不是每次都準。', 'Recoveries have often come near bottoms, though not every time.', '再次跌回投降', 'A relapse into capitulation')
    return V('neu', '礦工健康', 'Miners are healthy', '算力穩定，這張圖現在不提供方向。', 'Hashrate is steady: the chart gives no direction now.', '跌進投降期', 'A drop into capitulation')
def cyccmp(L):
    c = C(L)['cycle_cmp']; cur = next(x for x in c['cycles'] if x['now'])
    return V('neu', '淺週期，時間表不適用', 'A shallow cycle', '這輪跌幅 %s，前幾輪都在 −75%% 以下，前幾輪的時間表不能直接套。' % pc(cur['at']['pct']), 'This drawdown is %s versus below −75%% before, so past timelines may not apply.' % pc(cur['at']['pct']))
def dd(L):
    x = O(L)['dd']['cyc']
    if x['past']['deeper'] <= 10: return V('up', '回撤少見地深', 'An unusually deep pullback', '前四輪從底到頂的日子只有 %d%% 比現在深。' % x['past']['deeper'], 'Only %d%% of bottom-to-top days in past cycles were deeper.' % x['past']['deeper'], '跌破這輪底部', 'A break of the cycle low')
    return V('neu', '牛市裡的一般回撤', 'An ordinary pullback', '前四輪從底到頂的日子有 %d%% 比現在深，不算極端。' % x['past']['deeper'], '%d%% of bottom-to-top days in past cycles were deeper: not extreme.' % x['past']['deeper'])
def capeff(L): return V('neu', '背景，不指方向', 'Context only', '這張比的是每輪資金推動價格的效率，說明漲幅會越來越小，不說接下來的方向。', 'It compares how efficiently money lifts price each cycle: gains shrink, but it says nothing about direction.')
def path(L):
    m = C(L)['model']; t = m['top_model']; px = L['price']['bar']['c']
    return V('up', '長期路徑向上', 'The long path points up', '四種走法的終點都在現價之上，頂部模型中位 %s（%s）；短期路線各有不同。' % (usd(t['median']), t['timing']), 'All four paths end above today\'s price; the top model\'s median is %s (%s). Near-term routes differ.' % (usd(t['median']), t.get('timing_en') or t['timing']), '跌破延後新低那條路線', 'Falling below the delayed-new-low path') if t['median'] > px * 1.3 else V('neu', '接近模型頂部', 'Near the model top', '價格接近頂部模型的區間。', 'Price is near the top model\'s range.')
def long(L): return V('neu', '長期背景', 'Long-run context', '這張是全部歷史和減半時間點，給背景，不給方向。', 'All of history with halvings marked: context, not direction.')
def mon(L):
    m = L['price']['monthly']['cur']
    return V('neu', '季節性很弱', 'Seasonality is weak', '只有 %d 個樣本，月份效應不能當方向。' % m['n'], 'Only %d samples: month effects are not a direction.' % m['n'])
def avgd(L):
    a = O(L)['avgd']; v = a['value']
    if v <= 20: return V('up', '離成本線很遠的便宜區', 'Deep below cost lines', '九條線的平均百分位在 20 以下：歷來屬於便宜區（不是底）。', 'The average percentile is under 20: historically a cheap zone, not a bottom.', '升回 40 以上', 'A move above 40')
    if v >= 80: return V('down', '離成本線很遠的貴區', 'Far above cost lines', '平均百分位 80 以上，歷來接近頂部。', 'Above 80, as near past tops.', '回到 60 以下', 'A drop below 60')
    return V('neu', '中間區段', 'Middle zone', '平均百分位在中間。', 'The average percentile is mid-range.')

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
def psx(L):   # 2026-11-19 獲利供給扣掉十年老幣（bv_more.py 第 6 項）：照「第一次跌破 45%」的回測；高的一端牛市初期也常到，不指方向
    q = O(L)['bvx']['psx']; done = [c for c in q['cross45'] if c['y1'] is not None]; nup = sum(1 for c in done if c['y1'] > 0); wst = abs(min(c['worst'] for c in done)) if done else 0
    if q['ex'] <= 45 and done and nup == len(done): return V('up', '接近歷次熊底', 'Near past bear lows', '扣掉十年老幣後 %.1f%% 在獲利；過去 %d 次第一次跌破 45%%，一年後都是漲的，但一年內最多再跌 %d%%。' % (q['ex'], len(done), wst), '%.1f%% in profit excluding 10-year-old coins; all %d past first drops below 45%% were up a year later, though price fell up to another %d%% within that year.' % (q['ex'], len(done), wst), '回到 60% 以上', 'A return above 60%')
    if q['ex'] >= 95: return V('neu', '幾乎全部獲利', 'Nearly all in profit', '95% 以上在牛市初期也常出現，之後還大漲，不能單獨當頂部訊號。', 'Readings above 95% also show up early in bull markets, before big gains: not a top signal on its own.', '跌破 45%', 'A drop below 45%')
    return V('neu', '中間區段', 'Middle zone', '扣掉十年老幣後 %.1f%% 在獲利，不在熊底區也不在高檔。' % q['ex'], '%.1f%% in profit excluding 10-year-old coins: neither bear-bottom nor top territory.' % q['ex'], '跌破 45%', 'A drop below 45%')
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
