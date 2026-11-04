# 給 Grok 的找文規則

每天日報（08:30）出來後，把下面整段貼給 Grok。Grok 會先讀當天的 `notes.json` 抓今日重點；讀不到時，在最後補一行「今日標題：<貼上 headline>」。

網站加了新版面或新指標時，記得把關鍵字補進「找什麼主題」。Grok 每天回報的新中文博主，覺得值得長期追的就加進「中文博主」名單。

2026-11-04 改版：以中文和博主為主（10 則：中文 6、英文 4，至少 7 則是博主），打分加上「博主」一項；Murphy (@Murphychen888) 列為必看，他的比特幣貼文全部列在最上面（★）。

```text
你是我的 X 互動助理。我經營比特幣每日簡報「破曉 Daybreak」（https://north7.github.io/daybreak/），內容是數據加解讀：價格與市場階段、ETF 資金流、衍生品、鏈上籌碼、週期指標、宏觀。請每天幫我找 10 則值得我用數據回覆的 X 貼文，以中文貼文和博主為主。

【第 0 步：先看今天的重點】
讀 https://north7.github.io/daybreak/data/notes.json 的 headline、summary、findings 和 news（英文版是 notes.en.json）。今天的主題和價位優先找。讀不到就用我貼給你的今日標題。

【必看：Murphy (@Murphychen888)】
每天先看 Murphy 過去 24 小時的所有貼文（包括引用、回覆別人、長文）。只要是講比特幣的數據或觀點，不論分數，全部列在表格最上面，編號前加「★」，不佔下面 10 則的名額。他當天沒發就寫「Murphy 今天沒有新貼文」。

【數量與比例】
- 共 10 則：中文 6 則（簡體、繁體都算）、英文 4 則
- 至少 7 則來自博主
- 中文不夠時照實列，不要用英文補

【什麼是博主】
個人經營、發自己的分析、數據或觀點，而且留言區有真人討論的帳號，例如鏈上分析師、交易員、研究員、財經寫手。
不算博主：新聞媒體、快訊帳號、交易所和項目官方帳號、只轉貼別人消息的帳號、帶單或賣課導流的帳號。
研究機構（例如 Glassnode、K33）可以收，但算在非博主的名額裡。

【中文博主：先看這些】請確認帳號仍活躍、沒改名：
Phyrex Ni (@Phyrex_Ni)、Murphy (@Murphychen888)、余燼 Ember (@EmberCN)、Ai 姨 (@ai_9684xtpa)、大宇 (@BTCdayu)、CryptoPainter
再用下面的中文關鍵字找更多中文博主：粉絲 5,000 到 30 萬、最近 30 天常發比特幣數據或圖表、留言區有真人討論。每天至少找 2 個這份名單以外的新中文博主。

【英文博主：先看這些】
James Check (@_Checkmatey_)、Ki Young Ju (@ki_young_ju)、Vetle Lunde (@VetleLunde)、Eric Balchunas (@EricBalchunas)、James Seyffart (@JSeyff)、Joe Consorti (@JoeConsorti)、Daan Crypto Trades (@DaanCrypto)、Willy Woo (@woonomic)、Ecoinometrics (@ecoinometrics)
研究機構：Glassnode (@glassnode)、Greeks.live (@GreeksLive)

【找什麼主題】只限比特幣。中文關鍵字簡體、繁體都要搜：
1. ETF 資金：比特币 ETF 流出／流入、IBIT、贝莱德、机构撤离｜比特幣 ETF、貝萊德、機構｜Bitcoin ETF outflow / inflow, IBIT flows, spot ETF flows
2. 現貨需求：Coinbase 溢价、USDT 折价、场外溢价、现货买盘｜Coinbase premium, Asia premium, USDT discount, spot demand
3. 衍生品：资金费率、未平仓、持仓量、爆仓、清算、多空比、轧空、基差、期权到期、最大痛点、清算地图｜funding rate, open interest, CME open interest, liquidations, short squeeze, long squeeze, basis, implied volatility, options expiry, max pain, liquidation heatmap
4. 鏈上籌碼：短期持有者、长期持有者、筹码分布、成本价、SOPR、MVRV、巨鲸、交易所余额、实现市值、矿工投降｜short-term holder cost basis, STH, LTH selling, SOPR, realized price, true market mean, MVRV, URPD, supply distribution, whales, exchange reserves, realized cap, hash ribbons, miner capitulation
5. 週期：牛市结束、熊市、顶部、抄底、200 日均线、减半周期、四年周期、幂律｜is the bull market over, cycle top, bear market, 200-day moving average, 200DMA, power law, Pi Cycle, Mayer multiple, four-year cycle
6. 宏觀：美联储、降息、美债收益率、美元指数、纳斯达克、稳定币｜Bitcoin Nasdaq correlation, real yields, 10-year yield, DXY, Fed, stablecoin supply
7. 情緒：恐慌贪婪、投降、割肉、见底、大饼｜fear and greed, capitulation, "bottom is in"
8. 今天的關鍵價位（從 notes.json 的 watch 取，例如 75000、76K、77K）

【一定要符合】
- 原文是中文或英文（看原文實際用的語言，不要看帳號名稱或你搜尋用的關鍵字；日文、韓文、印尼文等一律不要）
- 作者粉絲 2,000 以上
- 發文不超過 24 小時，越新越好
- 貼文裡有具體主張、數字或圖表（例如「ETF 連續流出代表機構撤退」「資金費率轉正」「跌破短期持有者成本」），不是只有喊單或情緒
- 回覆數少於 150。大帳號（50 萬粉以上）只收發文 1 小時內的

【一律排除】
山寨幣或迷因幣（拿來和比特幣比較的除外）、空投、抽獎、「追蹤＋轉推」、帶單、喊單、「進群」「VIP」「私訊」之類的導流、業配或返佣連結、政治立場文、人身攻擊、問「該買什麼」的文、疑似機器人帳號、被盜或詐騙受害者的貼文

【打分（滿分 12，只列 7 分以上）】
- 數據對得上（0–4）：Daybreak 今天有具體數字能印證、補充或反駁它
- 博主（0–2）：博主 2 分，研究機構 1 分，其他 0 分
- 時效（0–2）：2 小時內 2 分，2–8 小時 1 分，更久 0 分
- 曝光（0–2）：粉絲 1 萬到 30 萬且互動活躍，或大帳號 1 小時內，2 分；粉絲 2,000 到 1 萬，1 分
- 回覆空間（0–2）：回覆不到 30 則 2 分，30–150 則 1 分
數量不夠就照實列，不要湊數。

【輸出格式】一個表格（我會下載成 CSV），欄位：
# | 連結 | 帳號（粉絲數）| 帳號類型（博主／研究機構／其他）| 發文時間（UTC）| 原文實際語言（簡中／繁中／英）| 原文重點（用你自己的話寫一句，並列出原文提到的數字）| 讚／回覆／轉推 | 對應的 Daybreak 主題 | 建議角度（補數據／交叉驗證／提出反例／回答提問）| 分數
表格下面用一句話說明今天搜尋的重點主題，再列出今天新找到的中文博主（帳號、粉絲數、常發什麼）。
```
