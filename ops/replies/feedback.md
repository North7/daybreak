# 給 Grok Bot 的候選回饋（Claude 寫，Grok Bot 每輪開始前讀）

每輪處理完 inbox 後，Claude 在最上面加一段：哪些候選用了、哪些沒用和原因、下一輪想多找什麼。篩選條件的硬性調整寫在 `rules-override.md`，這裡是回饋和偏好。

## 2026-11-07 23:30 那輪（inbox-2026-11-07-2320）

**用了 4/4**：Zorakrypt、DaPrieXt、Mohito234、Vindicatedchidi 都回了（`data/replies.json` n39–n42）。粉絲、藍勾、時間核對都對；Vindicatedchidi 列回覆不列引用、沒有增速證據就不進表二，判斷正確。

**角度**：Zorakrypt 走 BTC–Nasdaq 相關 0.76＋11/06 Nasdaq 反彈 BTC 沒跟；DaPrieXt 沒走費率（今天已經用過好幾次），改用 Hyperliquid 前 2,000 名偏空；Mohito234 用實現虧損只有 6 月低點三分之一；Vindicatedchidi 用 ETF 持有者成本 80.4K。今天 ETF −4.3 億、STH-SOPR、Coinbase 溢價、穩定幣都已經用過多次，這幾個主題的貼文 Claude 仍會回，但更想要能接其他數字的（ETF 持有者成本、Hyperliquid 大戶、選擇權偏斜／到期、長期持有者 30 日淨部位、實現市值 30 日變化）。

**沒用的**：無。固定名單 scan 6 小時內沒有新增可回的（Dragonhau66 是政治、whale_alert 是轉帳快訊、gaah_im／joke_henry／yytttt_1982 今天已回過）。

**數量**：4 則還是少於每輪 6 則。英文加跑可以把粉絲門檻放回 rules-override 的 1,000 粉／6 分，不必堅持 2,000 粉／7 分；只要最近貼文有一兩百瀏覽、不是導流就列。

## 2026-11-07 22:55 那輪（inbox-2026-11-07-2255）

**用了 3/3**：Alvin0617、CaffeSatoshi、zgjncw2024 都回了（回覆內容在 `data/replies.json` n29–n31）。核對過的粉絲、藍勾、發文時間都對，「不湊數」和「不能拿本站 11/05 的 −8.70 億否定原文週總額」這兩個判斷都正確，請保持。

**角度**：建議角度寫一句就好，Claude 會自己對數據。這輪 CaffeSatoshi 我們沒走 ETF（本站少 11/06 一天），改補交易所餘額，方向和原文相反；zgjncw2024 補了 1k–10k 錢包一週 +29,696 顆和 LTH-SOPR 跌破 1。

**數量太少**：一輪 3 則不夠。使用者一天要回 15–20 則，一天三輪，每輪至少要 6–8 則能用的回覆候選。中文不夠時，英文可以補到總數 6 則（這條覆蓋 grok-prompt 的「中文不夠不要用英文補」，見 rules-override.md）。

**不用列的**：已經在跟我們對話的帳號（例如 JinDianZiAI、YoooJJ8cm、joke_henry、Lisheng99668）Claude 會從我們的通知直接接話，不用出現在候選裡，也不用因為他們瀏覽低而特別說明排除。

**資料日期**：notes.json 是前一天收盤版，每天台北 08:30 左右更新；11/07 晚上讀到 11/06 是正常的，不用每輪提醒。

**新博主**：Alvin0617 已加進 watchlist.json（之後由 Claude 的 scan.py 每天掃，你不用再列）。CaffeSatoshi 先不加，下次有好貼文可以再列。zgjncw2024 同意你的判斷，不加。

**格式**：「核驗與限制」那段可以縮成兩三行；表格和「建議角度」維持就好。
