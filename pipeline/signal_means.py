# -*- coding: utf-8 -*-
"""異動的白話說明（2026-11-06 使用者要求：「圖上有異動字樣的，不知道在哪裡可以看怎樣的異動，異動哪裡了，異動說明什麼，意味著什麼」）。

signals.build() 偵測完之後呼叫 annotate()，每一則異動加三個欄位：
  rule   這次觸發的是哪條規則（白話、帶門檻）
  means  這類異動一般代表什麼（依方向；只寫一般含意，不寫預測、不給目標價或買賣區）
  hist   「翻轉」類原本沒有歷史對照，能從現有序列算的就補上（過去同樣翻轉的日期與之後 30 天價格變化）
"""


def T(zh, en): return {'zh': zh, 'en': en}


# ---------- 指標的極端值／7 日急變：key → (偏高或急升, 偏低或急降) ----------
SERIES_MEANS = {
    'price': (T('價格在近一年的高檔（或一週漲很多）：多數持有者獲利、追價情緒升溫；高檔區獲利了結的賣壓也比較大。', 'Price is near the top of its 1-year range (or rose fast this week): most holders are in profit and chasing picks up; profit-taking pressure is also highest up here.'),
              T('價格在近一年的低檔（或一週跌很多）：近期進場的人多數套牢，恐慌賣壓容易集中，也常是情緒最差的時候。', 'Price is near the bottom of its 1-year range (or fell fast this week): short-term holders are mostly under water, panic selling tends to cluster, and sentiment is usually at its worst.')),
    'dvol': (T('選擇權變貴：市場願意付更高的價錢買保險，預期接下來波動變大，常出現在急跌或重大事件前後。', 'Options got expensive: traders pay up for protection and expect bigger swings, typical around sharp drops or major events.'),
             T('選擇權很便宜：市場預期接下來很平靜；這種低檔常是大行情前的醞釀期，但不告訴你方向。', 'Options are cheap: traders expect calm. Such lows often precede a big move, but they say nothing about its direction.')),
    'rv30': (T('過去 30 天價格實際震得很兇，市場處在劇烈波動階段。', 'Price actually swung hard over the last 30 days; the market is in a violent phase.'),
             T('過去 30 天價格異常平靜；波動低檔通常不會維持太久，之後常有一段放量突破，方向不定。', 'Price was unusually calm over the last 30 days; low volatility rarely lasts and often ends in a breakout, in either direction.')),
    'ivrv': (T('選擇權定價的波動比實際波動高很多：市場在為未來的不確定付溢價，偏向避險、緊張。', 'Options price in far more volatility than is being realized: traders pay a premium for uncertainty and lean defensive.'),
             T('選擇權定價的波動低於實際波動：市場對未來比較放心，甚至低估了目前的風險。', 'Options price in less volatility than is being realized: traders are relaxed, perhaps underpricing current risk.')),
    'sth-sopr': (T('短期持有者賣出時的獲利倍數偏高：短期持有者在賺錢賣出，獲利了結增加；上漲中常見，太高代表短線過熱。', 'Short-term holders are selling at a high profit multiple: short-term holders are taking profit. Common in rallies; very high readings mean the short term is overheated.'),
                 T('短期持有者普遍賠錢賣：短期持有者在認賠出場，常出現在恐慌或回檔的低點附近；認賠潮過去後賣壓會減輕。', 'Short-term holders are selling at a loss: short-term holders are capitulating, typically near panic or pullback lows; selling pressure eases once the wave passes.')),
    'sth-profit': (T('短期持有者實現的獲利大增：短期持有者在逢高獲利了結，短線賣壓變大。', 'Short-term holders realized a lot of profit: short-term holders are selling into strength, adding short-term supply.'),
                   T('短期持有者實現的獲利很少：賺錢可賣的人不多，或大家不急著賣。', 'Short-term holders realized little profit: few have gains to sell, or nobody is in a hurry.')),
    'sth-loss': (T('短期持有者實現的虧損大增：短期持有者集中認賠，常出現在急跌的恐慌段；認賠集中釋放後，賣壓常會減輕。', 'Short-term holders realized heavy losses: short-term holders are capitulating, typical of panic drops; selling often eases after such a flush.'),
                 T('短期持有者實現的虧損很少：沒什麼人在賠錢賣，套牢賣壓低。', 'Short-term holders realized few losses: hardly anyone is selling at a loss, so trapped-supply pressure is low.')),
    'sth-plr': (T('短期持有者的獲利遠大於虧損：短期持有者整體在賺錢賣，市場偏強，但也代表獲利了結在進行。', 'Short-term holder profits far exceed losses: short-term holders are selling at a gain overall, a sign of strength but also of profit-taking.'),
                T('短期持有者的虧損大於獲利：短期持有者整體在賠錢賣，市場偏弱，常見於回檔或底部區。', 'Short-term holder losses outweigh profits: short-term holders are selling at a loss overall, typical of pullbacks or bottoming phases.')),
    'npl': (T('全網一天實現的淨獲利很大：持有者在大量獲利了結，常見於上漲途中或局部高點。', 'The network realized a large net profit in one day: heavy profit-taking, common during rallies or near local highs.'),
            T('全網一天實現的淨虧損很大：持有者在大量認賠，常見於恐慌下跌、局部低點附近。', 'The network realized a large net loss in one day: heavy loss-selling, common in panic drops near local lows.')),
    'npl-cum30': (T('過去 30 天累計大量獲利了結（占市值的比例在四年高檔）：歷來出現在週期頂部附近的派發階段。', 'Heavy profit-taking over 30 days (a 4-year high as a share of market cap): historically seen in distribution phases near cycle tops.'),
                  T('過去 30 天累計大量認賠（四年低檔）：歷來出現在熊市底部或深度回檔的投降階段。', 'Heavy loss-selling over 30 days (a 4-year low): historically seen in capitulation near bear-market bottoms or deep pullbacks.')),
    'sth-in-profit': (T('幾乎所有短期持有者都在賺錢：上漲動能強，但人人有獲利時，獲利了結的誘因也最大，常是短線過熱。', 'Nearly all short-term holders are in profit: momentum is strong, but the urge to take profit is at its highest, often a short-term overheating sign.'),
                      T('大多數短期持有者都在虧錢、整體套牢，恐慌情緒高；歷來這類低檔常接近局部低點。', 'Most short-term holders are under water, trapped and fearful; such lows have often been near local bottoms.')),
    'sth-lth': (T('短期持有者的持幣比例上升：幣從長期持有者流到短期持有者手上，常見於上漲時長期持有者獲利出貨。', 'Short-term holders hold a growing share: coins are moving from long-term holders to short-term holders, typical of long-term holders selling into a rally.'),
                T('長期持有者的持幣比例上升：幣沉澱到長期持有者手上、換手變少，常見於整理或累積階段。', 'Long-term holders hold a growing share: coins are settling with long-term holders and changing hands less, typical of consolidation or accumulation.')),
    'cbp': (T('Coinbase 比 Binance 貴很多：美國買盤（包含機構）特別積極。', 'Coinbase trades well above Binance: US buyers, institutions included, are unusually keen.'),
            T('Coinbase 比 Binance 便宜很多：美國現貨買盤疲弱、甚至在賣，美國資金觀望。', 'Coinbase trades well below Binance: US spot demand is weak or selling, and US money is on the sidelines.')),
    'stables': (T('穩定幣供給快速增加：場邊可以買幣的資金變多，是加密市場潛在的買盤。', 'Stablecoin supply is growing fast: more dry powder on the sidelines, potential buying power for crypto.'),
                T('穩定幣供給快速減少：資金從加密市場撤出（贖回成美元），可以用來買幣的子彈變少。', 'Stablecoin supply is shrinking fast: money is leaving crypto (redeemed for dollars), leaving less dry powder to buy with.')),
    'rcliq': (T('實現市值增加得快：新資金以較高的成本流進比特幣。', 'Realized cap is growing fast: new money is flowing into bitcoin at higher cost bases.'),
              T('實現市值增加得慢甚至減少：新資金流入放緩，或有人在低於成本處賣出。', 'Realized cap is growing slowly or shrinking: inflows are fading, or coins are being sold below cost.')),
    'p20': (T('MVRV 相對前一輪高點偏高：整體帳面獲利接近過去頂部的水準，離出場框架的鏈上賣點更近。', 'MVRV is high relative to the prior peak: aggregate paper profit is nearing past-top levels and the exit plan\'s on-chain sell point is closer.'),
            T('MVRV 相對前一輪高點偏低：整體帳面獲利很薄，離頂部區還遠。', 'MVRV is low relative to the prior peak: aggregate paper profit is thin and the top zone is far away.')),
    'oc-mvrv-zscore': (T('市值相對全體持有者的總成本偏高（估值熱）：帳面獲利大，歷來高檔接近週期頂部。', 'Market value is high relative to holders\' total cost (hot valuation): big paper gains; highs have historically been near cycle tops.'),
                       T('市值相對總成本偏低（估值冷）：歷來低檔接近週期底部。', 'Market value is low relative to total cost (cold valuation): lows have historically been near cycle bottoms.')),
    'oc-nupl': (T('整體帳面獲利占市值的比例高：市場情緒偏樂觀到貪婪。', 'Paper profit is a large share of market cap: sentiment runs from optimism to greed.'),
                T('整體帳面獲利很薄甚至虧損：市場情緒偏悲觀到投降。', 'Paper profit is thin or negative: sentiment runs from pessimism to capitulation.')),
    'oc-puell-multiple': (T('礦工收入相對一年平均偏高：礦工有賣幣獲利的誘因，歷來高檔接近頂部。', 'Miner revenue is high versus its 1-year average: miners have reason to sell; highs have historically been near tops.'),
                          T('礦工收入相對一年平均偏低：礦工收入受壓，弱勢礦工可能被迫賣幣或關機，歷來低檔接近底部。', 'Miner revenue is low versus its 1-year average: miners are squeezed and weak ones may sell or shut down; lows have historically been near bottoms.')),
    'oc-asopr': (T('所有賣出的幣平均獲利倍數偏高：市場在大量獲利了結。', 'Coins sold are fetching a high average profit multiple: the market is taking profit heavily.'),
                 T('所有賣出的幣平均在賠錢：全市場在認賠，常見於恐慌與底部區。', 'Coins sold are, on average, sold at a loss: market-wide loss-selling, typical of panic and bottoming phases.')),
    'oc-lth-sopr': (T('長期持有者賣出時的獲利倍數偏高：長期持有者在高獲利下出貨，常見於牛市後段。', 'Long-term holders are selling at a high profit multiple: long-term holders are distributing at big gains, typical of late bull markets.'),
                    T('長期持有者也在低獲利甚至賠錢賣：連長期持有者都撐不住，歷來出現在熊市的投降階段。', 'Long-term holders are selling at thin gains or losses: even long-term holders are giving up, historically a bear-market capitulation sign.')),
    'oc-illiquid-supply': (T('長期不動的幣變多：幣被收進不常交易的錢包，市場上可流通的籌碼變少，偏累積。', 'Illiquid supply is rising: coins are moving into wallets that rarely trade, shrinking the tradable float; leans toward accumulation.'),
                           T('長期不動的幣減少：沉睡的幣被喚醒、流回市場，可以賣的籌碼變多。', 'Illiquid supply is falling: dormant coins are waking and returning to the market, adding sellable supply.')),
    'oc-highly-liquid-supply': (T('頻繁交易的幣變多：籌碼在交易所與活躍錢包之間流動，短線買賣活躍、可賣籌碼多。', 'Highly liquid supply is rising: coins are cycling through exchanges and active wallets; trading is busy and sellable supply is ample.'),
                                T('頻繁交易的幣變少：籌碼流出活躍市場，短線賣壓的潛在來源減少。', 'Highly liquid supply is falling: coins are leaving the active market, reducing a source of short-term selling.')),
    'oc-lth-mvrv-zscore': (T('長期持有者的帳面獲利偏高：長期持有者獲利豐厚，出貨誘因大，歷來高檔接近頂部。', 'Long-term holders sit on large paper gains: long-term holders have strong reason to sell; highs have historically been near tops.'),
                           T('長期持有者的帳面獲利很薄：連長期持有者都接近成本，歷來低檔接近熊市底部。', 'Long-term holders sit on thin paper gains: even long-term holders are near cost; lows have historically been near bear-market bottoms.')),
    'oc-supply-in-profit-pct': (T('幾乎所有的幣都在獲利：市場普遍賺錢，歷來高於 95% 時接近局部或週期高點。', 'Nearly all coins are in profit: broad gains; readings above 95% have historically been near local or cycle highs.'),
                                T('很多幣處於虧損：套牢盤多，歷來低於 50% 時接近熊市底部。', 'Many coins are at a loss: lots of trapped supply; readings below 50% have historically been near bear-market bottoms.')),
    'oc-lth-net-position-change-30d-btc': (T('長期持有者 30 天淨增加很多：長期持有者在累積（也包含幣放滿 155 天自動算成長期持有者）。', 'Long-term holders added a lot over 30 days: long-term holders are accumulating (this also counts coins that simply aged past 155 days).'),
                                           T('長期持有者 30 天淨減少很多：長期持有者在賣出，常見於上漲中獲利了結或頂部區的派發。', 'Long-term holders shed a lot over 30 days: long-term holders are selling, typical of profit-taking in rallies or distribution near tops.')),
}

# ---------- 狀態翻轉：key → (成立時, 不成立時) ----------
FLIP_MEANS = {
    'above_sma200': (T('收盤站回 200 日均線：長期趨勢重新轉為向上的訊號之一；假突破也常見，通常看能不能連續守住。', 'The close is back above the 200-day average: one sign the long-term trend is turning up again. False breaks are common, so what matters is whether it holds.'),
                     T('收盤跌破 200 日均線：長期趨勢轉弱的訊號之一；出場框架裡 200 日均線也是避險線。', 'The close fell below the 200-day average: one sign the long-term trend is weakening; it is also the hedge line in the exit plan.')),
    'above_sth_cost': (T('價格回到短期持有者成本之上：短期持有者整體由虧轉盈，賣壓減輕，常被視為短線轉強。', 'Price is back above the short-term holder cost: short-term holders flip to a profit as a group and selling eases, usually read as short-term strength.'),
                       T('價格跌破短期持有者成本：短期持有者整體轉為虧損，容易出現回本或停損賣壓。', 'Price fell below the short-term holder cost: short-term holders are now at a loss as a group, inviting break-even and stop-loss selling.')),
    'above_tmm': (T('價格站上真實市場均價：活躍投資人整體回到獲利，這條線歷來是多空分界。', 'Price is above the true market mean: active investors are back in profit as a group; this line has long separated bull and bear phases.'),
                  T('價格跌破真實市場均價：活躍投資人整體轉為虧損，歷來是轉弱的訊號。', 'Price fell below the true market mean: active investors are at a loss as a group, historically a sign of weakening.')),
    'funding_pos': (T('永續合約不再由空方付費：空單擁擠解除，回到中性附近（OKX、Hyperliquid 的中性是年化 10.95%，要明顯高過它才算多單擁擠）。', 'Shorts no longer pay longs: the short crowding has cleared and funding is back near neutral (OKX and Hyperliquid sit at 10.95% a year when neutral; only well above that means crowded longs).'),
                    T('永續合約改由空方付費給多方：槓桿偏空，若價格上漲容易出現軋空。', 'Perpetual shorts now pay longs: leverage leans short, so a rally can turn into a short squeeze.')),
    'iv_gt_rv': (T('選擇權定價的波動回到實際波動之上：市場重新為不確定付溢價，偏謹慎。', 'Implied volatility is back above realized: traders again pay a premium for uncertainty and lean cautious.'),
                 T('選擇權定價的波動低於實際波動：選擇權相對便宜，市場低估了目前的波動。', 'Implied volatility fell below realized: options are cheap relative to actual swings, so the market is underpricing current volatility.')),
    'rr_pos': (T('買權比賣權貴：選擇權市場押注上漲的需求大於避險。', 'Calls are pricier than puts: demand for upside bets outweighs hedging.'),
               T('賣權比買權貴：選擇權市場花更多錢在防跌避險，情緒偏謹慎。', 'Puts are pricier than calls: more money is going into downside protection; sentiment is cautious.')),
    'sopr_ge1': (T('短期持有者整體從賠錢賣變成賺錢賣：認賠潮告一段落，短線賣壓減輕；能不能站穩在 1 之上，常被當成回檔結束的確認。', 'Short-term holders went from selling at a loss to selling at a profit: the loss-selling wave has paused and short-term pressure eases; holding above 1 is often taken as confirmation that a pullback is over.'),
                 T('短期持有者整體轉為賠錢賣：短期持有者開始認賠，短線轉弱；在上漲趨勢中，1 常是回檔的支撐。', 'Short-term holders started selling at a loss: short-term holders are capitulating and the short term weakens; in uptrends, 1 often acts as pullback support.')),
    'npl7_pos': (T('近 7 天全網由淨認賠轉為淨獲利：持有者整體回到賺錢賣出，情緒回穩。', 'The 7-day network total flipped from net loss to net profit: holders are selling at a gain again and sentiment is steadier.'),
                 T('近 7 天全網由淨獲利轉為淨認賠：持有者整體在賠錢賣出，情緒轉弱。', 'The 7-day network total flipped from net profit to net loss: holders are selling at a loss and sentiment is weakening.')),
    'rcliq_pos': (T('實現市值 30 天變化轉正：資金重新流入比特幣。', 'The 30-day change in realized cap turned positive: money is flowing back into bitcoin.'),
                  T('實現市值 30 天變化轉負：資金淨流出，歷來多在熊市才出現。', 'The 30-day change in realized cap turned negative: net outflows, historically seen mostly in bear markets.')),
    'cbp_pos': (T('Coinbase 溢價轉正：美國買盤重新比海外積極。', 'The Coinbase premium turned positive: US buyers are again keener than offshore ones.'),
                T('Coinbase 溢價轉負：美國買盤轉弱，海外相對積極。', 'The Coinbase premium turned negative: US demand has weakened relative to offshore.')),
    'hash_cap': (T('算力短期均線跌破長期均線（礦工投降）：礦工在關機、被迫賣幣，歷來出現在礦工壓力大的時候。', 'Short-term hashrate fell below the long-term average (miner capitulation): miners are shutting down and may be forced to sell, historically when miner stress is high.'),
                 T('礦工投降結束、算力回升：Hash Ribbons 的原始解讀把這看成礦工壓力解除、中長期轉強的訊號（本站只作讀值）。', 'Miner capitulation ended and hashrate is recovering: the original Hash Ribbons reading treats this as miner stress lifting and a medium-term turn up (shown as a reading only).')),
    'tm_top': (T('第三方 Tidemark 的頂部訊號到 50 以上：模型認為進入頂部觀察窗口（本站只作讀值）。', 'Third-party Tidemark\'s top signal is at 50 or above: the model sees a top-watch window (shown as a reading only).'),
               T('Tidemark 頂部訊號回到 50 以下：模型的頂部觀察窗口關閉。', 'Tidemark\'s top signal fell back below 50: the model\'s top-watch window has closed.')),
    'tm_bottom': (T('Tidemark 底部訊號到 50 以上：模型認為進入底部觀察窗口（本站只作讀值）。', 'Tidemark\'s bottom signal is at 50 or above: the model sees a bottom-watch window (shown as a reading only).'),
                  T('Tidemark 底部訊號回到 50 以下：模型的底部觀察窗口關閉。', 'Tidemark\'s bottom signal fell back below 50: the bottom-watch window has closed.')),
    'top_zone': (T('頂部三指標任兩項到四年第 80 百分位：歷來接近週期頂部區（只作讀值，不連動賣出）。', 'Two of the top-3 indicators reached the 80th 4-year percentile: historically near cycle-top territory (a reading only, not tied to selling).'),
                 T('頂部三指標離開頂部區：估值從高檔退下來。', 'The top-3 indicators left the top zone: valuations have cooled from their highs.')),
}

# ---------- 其他：key → 依方向的說明（'up'／'down'／'flat' 或單一說明） ----------
OTHER_MEANS = {
    'sma200': T('價格貼近 200 日均線：長期趨勢的分界，站上或跌破都會引來大量關注，附近容易拉鋸。', 'Price is near the 200-day average: the long-term trend line; crossing it draws attention and price often chops around it.'),
    'sth-cost': T('價格貼近短期持有者成本：短期持有者在這裡回到成本，跌破就轉為虧損；這條線在上漲中常是支撐、下跌中常是壓力。', 'Price is near the short-term holder cost: short-term holders break even here and fall into a loss below it; the line often supports rallies and caps declines.'),
    'tmm': T('價格貼近真實市場均價：活躍投資人的平均成本、歷來的多空分界，附近容易拉鋸。', 'Price is near the true market mean: the average cost of active investors and a long-standing bull/bear line; price often chops around it.'),
    'sth-cluster': T('價格貼近短期持有者籌碼最厚的地方：很多人在這裡買進，價格回到這裡時常出現解套賣壓，站穩之後則會轉為支撐。', 'Price is near the thickest pile of short-term holder coins: many bought here, so price often meets break-even selling, which turns into support once it holds.'),
    'urpd-transfer': T('大量的幣一天內「搬」到現價，多半是交易所或託管機構的內部轉帳，不是真的換手；這段期間的籌碼圖會失真。', 'A large block of coins "moved" to the current price in a day, most likely an internal exchange or custodian transfer rather than real trading; supply charts are distorted for a while.'),
    'exit-step': T('收盤離出場框架的第一階不遠：收盤到了，框架就照規則分批賣出第一階（這是框架規則，不是預測）。', 'The close is near the exit plan\'s first step: if a close reaches it, the plan sells the first tranche by rule (a rule, not a forecast).'),
    'k075': T('離 MVRV 0.75 線不遠：連 5 天站上這條線是出場框架的第一個鏈上賣點。', 'Close to the MVRV 0.75 line: five straight days above it is the exit plan\'s first on-chain sell point.'),
    'px1y': {'up': T('收盤創一年新高：過去一年買進的人全部獲利，趨勢強；新高附近的獲利了結也多。', 'A 1-year closing high: everyone who bought in the past year is in profit and the trend is strong; profit-taking also clusters near new highs.'),
             'down': T('收盤創一年新低：過去一年買進的人全部套牢，情緒最差，常伴隨恐慌賣壓。', 'A 1-year closing low: everyone who bought in the past year is under water; sentiment is at its worst and panic selling is common.')},
    'price-day': {'up': T('單日漲幅在近一年最大的 3%：大漲常由軋空或消息推動，隔天常有回吐，要看能不能延續。', 'A one-day gain in the largest 3% of the past year: big up days are often driven by short squeezes or news and partly given back; what matters is follow-through.'),
                  'down': T('單日跌幅在近一年最大的 3%：常伴隨清算與恐慌，短線賣壓集中釋放。', 'A one-day drop in the largest 3% of the past year: usually comes with liquidations and panic, flushing out short-term selling.')},
    'etf': {'up': T('ETF 連續淨流入：美國現貨需求持續，傳統資金在買。', 'Consecutive ETF net inflows: steady US spot demand from traditional money.'),
            'down': T('ETF 連續淨流出：美國現貨需求轉弱，傳統資金在撤。', 'Consecutive ETF net outflows: US spot demand is fading as traditional money pulls back.')},
    'sopr-below': T('短期持有者連續多天賠錢賣：認賠潮延續，短期持有者的耐心在耗盡；歷來長段認賠之後常接近局部低點，但會持續多久不一定。', 'Short-term holders have sold at a loss for many days running: the capitulation is dragging on; long stretches like this have often been near local lows, but how long they last varies.'),
    'profit-into-drop': T('價格下跌的那天，短期持有者反而大量獲利了結：先前低價買進的人趁機出場，常見於上漲之後的第一次回檔。', 'Short-term holders took heavy profit on a down day: earlier, cheaper buyers are cashing out, common on the first pullback after a rally.'),
    'sth-capitulation': T('短期持有者實現虧損很大、而且 SOPR 小於 1：短期持有者集中認賠出場，歷來常出現在局部低點附近。', 'Short-term holders realized heavy losses with SOPR below 1: short-term holders are capitulating together, historically often near local lows.'),
    'squeeze': T('價格上漲、資金費率卻是負的：上漲主要由空方回補推動，不是新多單；回補結束後動能可能減弱。', 'Price rose while funding was negative: the move is driven by shorts covering rather than new longs; momentum can fade once covering ends.'),
    'leverage-chase': T('上漲伴隨很高的資金費率：多方用槓桿追價，價格回落時容易出現多單清算。', 'A rally with very high funding: longs are chasing with leverage, so a dip can trigger long liquidations.'),
    'vol-squeeze': T('隱含與實際波動同時在低檔：市場很平靜，這種壓縮之後常有一段大波動，但方向不定。', 'Implied and realized volatility are both low: the market is very calm, and such compression is often followed by a big move in either direction.'),
    'etf-price-div': {'up': T('ETF 大量流入、價格卻在跌：機構在買，但其他地方（例如長期持有者或衍生品）的賣壓更大。', 'Large ETF inflows while price falls: institutions are buying, but selling elsewhere (long-term holders, derivatives) is heavier.'),
                      'down': T('ETF 大量流出、價格卻在漲：這段上漲不是 ETF 推動的，可能來自衍生品或其他市場的買盤。', 'Large ETF outflows while price rises: the rally is not ETF-driven and may come from derivatives or other venues.')},
    # 2026-11-06 指標擴充（oc_extra.py）
    'rloss-div': T('價格比前一個低點更低，但當時賣在虧損的金額小了兩成以上：願意認賠的人變少，恐慌在退。2013 年起 18 次，30 天後 14 次上漲；但 2022/05 之後還跌了 26%。', 'Price made a lower low but the loss realized at that low was 20%+ smaller: fewer holders are willing to sell at a loss and fear is fading. 18 cases since 2013, 14 higher 30 days later; but May 2022 fell another 26%.'),
    'rloss-cap': T('價格更低、認賠也更大：恐慌性賣出正在放大（投降）。歷來投降常出現在下跌的後段，但不一定是最後一次。', 'Lower price with bigger loss-taking: panic selling is growing (capitulation). It often comes late in a decline, but not necessarily for the last time.'),
    'grad-div': {'up': T('價格創擺動新低、資金與價格梯度卻沒有：資金撤出的速度比價格下跌慢，大級別上是築底的形態。', 'Price made a lower swing low but the capital-price gauge did not: capital is leaving more slowly than price is falling, a basing pattern on the long frame.'),
                 'down': T('價格創擺動新高、梯度卻沒有：價格靠情緒推升、新資金沒有跟上，之後常先回調。', 'Price made a higher swing high but the gauge did not: the rise runs on sentiment while new capital lags, and a pullback often comes first.')},
    'mom-div': T('價格創擺動新高、獲利了結的力道（SOPR × 銷毀幣天數）卻比前一次弱：推升的力量在衰減。2015 年起之後 60 天內最大跌幅中位數約 −21%（任一天約 −9%）。', 'Price made a higher swing high while profit-taking momentum (SOPR × coin days destroyed) was weaker than before: the push is fading. Since 2015 the median max drawdown within 60 days afterwards is about −21% (about −9% for any day).'),
    'rup-floor': T('全體未實現獲利佔市值的比例跌到 35% 以下：2012 年起只有週期底部附近出現過（2015、2018–19、2020/03、2022、2026/06）。', 'Total unrealized profit fell below 35% of market cap: since 2012 this has only happened near cycle bottoms (2015, 2018–19, March 2020, 2022, June 2026).'),
    'stage': T('市場階段由寫死的規則判定（P23）；階段改變代表規則條件翻過去了，原因可以看週期版的市場階段與佐證燈號。', 'The market stage is set by fixed rules (P23); a change means a rule condition flipped. The Cycle page\'s market stage and supporting lights show why.'),
}
FG_MEANS = {'xfear': T('恐懼貪婪指數進入極度恐懼：市場情緒最差，歷來常接近短線低點，但不代表會馬上反彈。', 'Fear & Greed entered extreme fear: sentiment is at its worst, often near short-term lows, though a bounce is not guaranteed to follow quickly.'),
            'xgreed': T('恐懼貪婪指數進入極度貪婪：情緒過熱，追價的風險升高。', 'Fear & Greed entered extreme greed: sentiment is overheated and chasing gets riskier.'),
            'mid': T('恐懼貪婪指數回到一般區間：情緒從極端回到中性。', 'Fear & Greed is back in the middle range: sentiment has returned from an extreme.')}
LIGHT_MEANS = (T('這盞佐證燈亮起：這項條件支持目前的市場階段。佐證燈只顯示，不參與階段判定。', 'This supporting light turned on: the condition now supports the current market stage. Supporting lights are shown only and do not decide the stage.'),
               T('這盞佐證燈熄滅：這項條件不再支持目前的市場階段。佐證燈只顯示，不參與階段判定。', 'This supporting light turned off: the condition no longer supports the current market stage. Supporting lights are shown only and do not decide the stage.'))
CLUSTER_MEANS = T('同一類的好幾項同時異動：單一指標可能是雜訊，同類多項一起動比較值得注意；各項的意思看各自的說明。', 'Several signals of the same kind fired together: one indicator alone can be noise, several moving at once deserve more attention; see each one for its meaning.')


def _means(s):
    k, d, kind = s.get('key'), s.get('dir'), s.get('kind')
    if kind in ('extreme', 'jump') and k in SERIES_MEANS: return SERIES_MEANS[k][0 if d == 'up' else 1]
    if kind == 'cross':
        if k in FLIP_MEANS: return FLIP_MEANS[k][0 if d == 'up' else 1]
        if k and k.startswith('light_'): return LIGHT_MEANS[0 if d == 'up' else 1]
        if k == 'fg_zone': return FG_MEANS.get(s['id'].split(':')[-1])
    if k and k.startswith('cluster-'): return CLUSTER_MEANS
    m = OTHER_MEANS.get(k)
    if isinstance(m, dict) and 'zh' not in m: return m.get(d) or m.get('up')   # 依方向分的說明；單一說明本身也是 {zh, en}
    return m


def _rule(s, ext, jmp, cmb, near, near_exit, four_year):
    k, kind, p = s.get('key'), s.get('kind'), s.get('pct')
    up = s.get('dir') == 'up'
    if kind == 'extreme':
        yz, ye = ('近四年', 'last 4 years') if k in four_year else ('近一年', 'last year')
        return T(f'把{yz}每天的數值排名，今天落在{"最高" if up else "最低"}的 {100 - ext}%（第 {p} 百分位）。',
                 f'Ranked against every day of the {ye}, today is in the {"top" if up else "bottom"} {100 - ext}% (percentile {p}).')
    if kind == 'jump':
        if k == 'price-day': return T('單日漲跌幅放進近一年每天的漲跌幅排名，落在最大的 3%。', 'The one-day move ranks in the largest 3% of daily moves over the past year.')
        return T(f'和 7 天前比的變化，放進近一年每天的 7 日變化排名，落在{"漲得最多" if up else "跌得最多"}的 {100 - jmp}%（第 {p} 百分位）。',
                 f'The change versus 7 days ago ranks in the {100 - jmp}% {"largest rises" if up else "largest drops"} of the past year (percentile {p}).')
    if kind == 'cross':
        return T('和上一期（前一天的資料）比，這個狀態翻過來了。每天只比較前後兩期，所以只有翻轉當天會出現，之後幾天標「第 N 天」。',
                 'Compared with the previous edition (the prior day\'s data), this state flipped. Only consecutive editions are compared, so it fires on the day of the flip and then counts days.')
    if kind == 'level':
        if k in ('exit-step', 'k075'): return T(f'收盤離這個價位 {near_exit:.0f}% 以內。', f'The close is within {near_exit:.0f}% of this level.')
        if k == 'px1y': return T(f'收盤{"高於" if up else "低於"}過去一年的每一天。', f'The close is {"above" if up else "below"} every close of the past year.')
        if k == 'sth-cluster': return T(f'收盤離短期持有者最厚的那一格不到 {near:.0f}%。', f'The close is within {near:.0f}% of the thickest short-term holder band.')
        return T(f'收盤離這條線不到 {near:.0f}%（現在 {s.get("dist_pct")}%）。', f'The close is within {near:.0f}% of this line (now {s.get("dist_pct")}%).')
    if kind == 'streak':
        return T(f'同一方向連續 {s.get("run")} 天（5 天以上才列）。', f'{s.get("run")} days in a row in the same direction (listed from 5 days).')
    if kind == 'combo':
        R = {'profit-into-drop': T(f'短期持有者實現獲利到近一年最高的 {100 - cmb}%，而且當天價格下跌。', f'Short-term holder realized profit in the top {100 - cmb}% of the past year on a day price fell.'),
             'sth-capitulation': T(f'短期持有者實現虧損到近一年最高的 {100 - cmb}%，而且 SOPR 小於 1。', f'Short-term holder realized loss in the top {100 - cmb}% of the past year with SOPR below 1.'),
             'squeeze': T('單日漲 1% 以上，加權資金費率卻小於 0。', 'A daily gain of 1% or more with weighted funding below 0.'),
             'leverage-chase': T('單日漲 1.5% 以上，加權資金費率 20%（年化）以上。', 'A daily gain of 1.5% or more with weighted funding at 20% (annualized) or higher.'),
             'vol-squeeze': T('DVOL 在近一年第 20 百分位以下，RV30 也在近半年第 20 百分位以下。', 'DVOL at or below its 20th 1-year percentile and RV30 at or below its 20th 6-month percentile.'),
             'rloss-div': T('價格擺動低點（前後 7 天最低、比之前 30 天最高跌 6% 以上）比 75 天內前一個更低，當時的認賠峰值小 20% 以上。', 'A swing low (lowest close within 7 days either side, 6%+ below the prior 30-day high) below the previous one within 75 days, with a loss peak 20%+ smaller.'),
             'rloss-cap': T('價格擺動低點比 75 天內前一個更低，當時的認賠峰值大 25% 以上。', 'A swing low below the previous one within 75 days, with a loss peak 25%+ larger.'),
             'grad-div': T('價格擺動高點（低點）比前一個更高（更低），資金與價格梯度的對應峰（谷）卻沒有；確認後 7 天內列出。', 'A swing high (low) above (below) the previous one while the capital-price gauge\'s matching peak (trough) is not; listed for 7 days after confirmation.'),
             'mom-div': T('價格擺動高點比 180 天內前一個更高，鏈上勢能的正值峰值卻較低；確認後 7 天內列出。', 'A swing high above the previous one within 180 days with a lower positive momentum peak; listed for 7 days after confirmation.'),
             'rup-floor': T('相對未實現獲利（未實現獲利 ÷ 市值）≤ 35%。', 'Relative unrealized profit (unrealized profit ÷ market cap) at or below 35%.'),
             'etf-price-div': T('近 5 個完整交易日 ETF 合計流入 5 億美元以上、價格卻跌 3% 以上（或反過來）。', 'Over the last 5 complete trading days, ETF flows of $500M or more in one direction while price moved 3% or more the other way.')}
        if k in R: return R[k]
        if k and k.startswith('cluster-'): return T(f'同一類有 3 項以上同時異動（這次 {len(s.get("members") or [])} 項）。', f'Three or more signals of the same kind at once ({len(s.get("members") or [])} this time).')
    return None


def _flip_rows(L, k, g, _rows, _ma7, _ivrv):
    """翻轉類的歷史對照用的序列：回傳 (rows[(x, v)], 門檻)；v 在門檻以上＝狀態成立。"""
    if k == 'sopr_ge1': return _rows(L, 'chips.viz.sopr.rows', 1), 1.0
    if k in ('above_sma200', 'above_sth_cost', 'above_tmm'):
        col = {'above_sma200': 2, 'above_sth_cost': 5, 'above_tmm': 6}[k]
        rows = [(r[0], r[1] / r[col] - 1) for r in g(L, 'cycle.levels.rows') or [] if len(r) > col and r[1] and r[col]]
        return rows, 0.0
    if k == 'rcliq_pos': return _rows(L, 'flows.rc_liq.rows', 1), 0.0
    if k == 'cbp_pos': return _ma7(_rows(L, 'flows.cb_premium.rows', 1)), 0.0
    if k == 'iv_gt_rv': return _ivrv(L), 0.0
    return None, None


def annotate(sig, L, px, S):
    """S＝signals 模組（取門檻與工具函式，避免循環 import）。"""
    four = {key for key, *_r in S.SERIES if '4' in _r[-3]}
    for s in sig:
        if s.get('kind') == 'error': continue
        try:
            m = _means(s)
            if m: s['means'] = m
            r = _rule(s, S.EXT, S.JMP, S.CMB, S.NEAR, S.NEAR_EXIT, four)
            if r: s['rule'] = r
            if s.get('kind') == 'cross' and not s.get('hist') and s.get('key') in ('sopr_ge1', 'above_sma200', 'above_sth_cost', 'above_tmm', 'rcliq_pos', 'cbp_pos', 'iv_gt_rv'):
                rows, th = _flip_rows(L, s['key'], S.g, S._rows, S._ma7, S._ivrv)
                rows = sorted(rows or [])
                if len(rows) > 30:
                    on = s.get('dir') == 'up'
                    cond = lambda i: i > 0 and (rows[i][1] >= th) == on and (rows[i - 1][1] >= th) != on
                    s['hist'] = S._history(rows, cond, px, len(rows) - 1)
                    s['hist']['what'] = 'cross'
        except Exception as e:   # 說明失敗不影響偵測本身
            s.setdefault('note_err', str(e))
    return sig
