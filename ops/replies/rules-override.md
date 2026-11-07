# 臨時篩選調整（Grok Bot 每輪開始前先讀）

這個檔案是 Claude 和使用者寫給 Grok Bot 的臨時規則，優先於 `grok-prompt.md`。過期的條目會刪掉；每條都寫日期和原因。

**寫入位置（2026-11-07）**：每輪結果只推到 `grok/inbox` 分支（沒有就從 main 開），只新增 `ops/replies/inbox-YYYY-MM-DD-HHMM.md`、更新 `ops/replies/strategy-log.md`。不要推到 main、不要動其他檔案、不要開 PR。這個檔案、`watchlist.json`、`data/replies.json` 都在 main 上，從 https://north7.github.io/daybreak/ 讀。

## 2026-11-07

0. **數量**：每輪回覆候選至少 6 則能用的；中文不夠時，英文可以補到總數 6 則（覆蓋 grok-prompt 的「中文不夠時不要用英文補」）。

1. **已經處理過的貼文不要再列**：讀 https://north7.github.io/daybreak/data/replies.json ，`items` 裡每個 `id` 和 `author` 當天都已經回過或看過。同一個作者當天已經有一則，就不要再列他的別則（除非是 2 小時內的新貼文，而且主題不一樣）。
2. **新帳號優先**：使用者要「熟帳號三成、新帳號七成」。watchlist.json 以外、我們沒回過的帳號才算新帳號；表一至少八成要是新帳號。
3. **放寬但不要零瀏覽**：候選太少時可以放寬到粉絲 1,000 以上、6 小時內，但最近貼文平常要有一兩百以上瀏覽。11/07 幾批候選很多是剛發幾分鐘、瀏覽個位數的小帳號（例如 CT_Richt3r、JackThuypx21685、Rasdamsama），回了沒人看，不要列。
4. **不要列純數據快訊**：只貼單一 ETF 一行數字（例如 FarsideUK「WisdomTree 0」）、日文或越南文夾雜的行情快訊（CoinPost_Alert、JackThuypx21685）、新聞轉述帳號（FINANCIERNEWS、cryptoslaunch、CryptoNews_op）不算候選。
5. **網站有圖對得上的優先**：使用者要「能配圖的盡量配」。主題是 ETF 每日流量、穩定幣供給、Coinbase 溢價、STH-SOPR、清算價位、均線與成本線、實現獲利÷虧損的貼文，分數「數據對得上」給滿。
6. **出場框架類的博主不要推薦長期追**：例如 817BIBI（以「8 萬以下維持減倉」這類操作規則為主、推自己的服務）、Lisheng99668（瀏覽中位數 55、比特幣貼文不到一半）。11/07 已核對過，不加。
