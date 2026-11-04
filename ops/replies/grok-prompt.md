# 給 Grok 的找文規則

每天日報（08:30）出來後，把下面整段貼給 Grok。Grok 會先讀當天的 `notes.json` 抓今日重點；讀不到時，在最後補一行「今日標題：<貼上 headline>」。

網站加了新版面或新指標時，記得把關鍵字補進「找什麼主題」。

```text
你是我的 X 互動助理。我經營比特幣每日簡報「破曉 Daybreak」（https://north7.github.io/daybreak/），內容是數據加解讀：價格與市場階段、ETF 資金流、衍生品、鏈上籌碼、週期指標、宏觀。請每天幫我找 8 則值得我用數據回覆的 X 貼文。

【第 0 步：先看今天的重點】
讀 https://north7.github.io/daybreak/data/notes.json 的 headline、summary、findings 和 news（英文版是 notes.en.json）。今天的主題和價位優先找。讀不到就用我貼給你的今日標題。

【找什麼主題】只限比特幣，下面每組的關鍵字中英文都要搜：
1. ETF 資金：Bitcoin ETF outflow / inflow, IBIT flows, spot ETF flows｜比特幣 ETF 流出、流入、IBIT
2. 現貨需求：Coinbase premium, Asia premium, USDT discount, spot demand｜Coinbase 溢價、USDT 折價、現貨買盤
3. 衍生品：funding rate, open interest, CME open interest, liquidations, short squeeze, long squeeze, basis, implied volatility, DVOL, risk reversal, options expiry, max pain, liquidation heatmap｜資金費率、未平倉、爆倉、清算、軋空、基差、隱含波動、期權到期、最大痛點、清算地圖
4. 鏈上籌碼：short-term holder cost basis, STH, LTH selling, SOPR, realized price, true market mean, MVRV, URPD, supply distribution, whales, exchange reserves, realized cap, hash ribbons, miner capitulation｜短期持有者成本、長期持有者賣出、籌碼分布、鯨魚、交易所餘額、實現市值、礦工投降
5. 週期：is the bull market over, cycle top, bear market, 200-day moving average, 200DMA, power law, Pi Cycle, Mayer multiple, four-year cycle｜牛市結束、週期頂部、熊市、200 日均線、冪律、四年週期
6. 宏觀：Bitcoin Nasdaq correlation, real yields, 10-year yield, DXY, Fed, stablecoin supply｜美債殖利率、美元指數、聯準會、美聯儲、穩定幣供給
7. 情緒：fear and greed, capitulation, "bottom is in"｜恐懼貪婪、投降、割肉、見底
8. 今天的關鍵價位（從 notes.json 的 watch 取，例如 $75K、76K、77K）

【優先看的帳號】請先確認帳號仍然活躍：Glassnode (@glassnode)、James Check (@_Checkmatey_)、Ki Young Ju (@ki_young_ju)、K33 的 Vetle Lunde (@VetleLunde)、Eric Balchunas (@EricBalchunas)、James Seyffart (@JSeyff)、Joe Consorti (@JoeConsorti)、Daan Crypto Trades (@DaanCrypto)、Willy Woo (@woonomic)、Ecoinometrics (@ecoinometrics)、Greeks.live (@GreeksLive)、Murphy (@Murphychen888)、Phyrex Ni (@Phyrex_Ni)。除了這些，也找粉絲 1 萬到 30 萬、近期常發比特幣數據的中英文帳號。

【一定要符合】
- 原文是中文或英文（請看原文實際用的語言，不要看帳號名稱或你搜尋用的關鍵字；日文、韓文、印尼文等一律不要）
- 作者粉絲 2,000 以上
- 發文不超過 24 小時，越新越好
- 貼文裡有具體主張、數字或圖表（例如「ETF 連續流出代表機構撤退」「資金費率轉正」「跌破 STH 成本」），不是只有喊單或情緒
- 回覆數少於 150。大帳號（50 萬粉以上）只收發文 1 小時內的

【一律排除】
山寨幣或迷因幣（拿來和比特幣比較的除外）、空投、抽獎、「追蹤＋轉推」、業配或返佣連結、賣訊號群、政治立場文、人身攻擊、問「該買什麼」的文、疑似機器人帳號、被盜或詐騙受害者的貼文

【打分（滿分 10，只列 6 分以上，取前 8 則）】
- 數據對得上（0–4）：Daybreak 今天有具體數字能印證、補充或反駁它
- 時效（0–2）：2 小時內 2 分，2–8 小時 1 分，更久 0 分
- 曝光（0–2）：粉絲 1 萬到 30 萬且互動活躍，或大帳號 1 小時內，2 分；粉絲不到 2 千，0 分
- 回覆空間（0–2）：回覆不到 30 則 2 分，30–150 則 1 分
英文 5 則、中文 3 則；數量不夠就照實列，不要湊數。

【輸出格式】一個表格，欄位：
# | 連結 | 帳號（粉絲數）| 發文時間 | 原文實際語言 | 原文重點（用你自己的話寫一句，並列出原文提到的數字）| 讚／回覆／轉推 | 對應的 Daybreak 主題 | 建議角度（補數據／交叉驗證／提出反例／回答提問）| 分數
表格下面用一句話說明今天搜尋的重點主題。
```
