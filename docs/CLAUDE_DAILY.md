# Claude 每日結論任務（破曉 Daybreak）

> 這份是排程任務的完整指示。建立排程時，把下面「任務指示」整段貼進排程的 prompt。時間：每天 UTC 00:30（台北 08:30）。排程目前用的就是下面這段（2026-10-13 同步）；改這份檔案後，排程也會因為「以倉庫為準」那一句讀到新版。
> 2026-10-21 整理：原本散在步驟 4 與寫作規則裡、按加入日期排的規則，改依版面分組，內容不變。

## 任務指示

你負責 破曉 Daybreak（GitHub 倉庫 `daybreak`，GitHub Pages 公開網站）的每日頭條、各版判讀與今日要聞解讀，中文版（`data/notes.json`，繁體中文）與英文版（`data/notes.en.json`）兩份都要寫。數字由 GitHub Actions 每天約 UTC 00:06 產生在 `data/latest.json`；你的工作是讀數字、寫判讀，然後提交。**你不改任何數字，也不改網站程式。**

**以倉庫為準**：拉下 main 後先**完整**讀 `docs/CLAUDE_DAILY.md` 的「任務指示」，特別是「### 步驟」逐條讀完（步驟會增加，例如 X 貼文草稿），不要只比對部分段落就判定相同。它若和這份指示不同，以檔案為準（網站改版時只會更新那個檔）。

### 隱私鐵則（最高優先）
這是公開倉庫，提交歷史永久可查。任何檔案都不得出現任何人的實際持倉數量、以顆數表示的個人買賣數量、資金或生活開支金額。出場框架一律以百分比表示（每階 12.5%、避險 20%）。市場數據（ETF 流量、選擇權未平倉、URPD 籌碼、掛單簿金額）不受此限。

### 步驟
1. 拉最新的 main。確認 `data/latest.json` 的 `meta.bar_date` 等於今天 UTC 日期的前一天。不是的話（GitHub 定時排程常延遲數小時）：執行 `date -u +%FT%TZ > .github/run-daily`，提交（訊息 `ci: trigger daily data`）並推送到 main，這會立刻觸發資料管線（約 2–3 分鐘）；之後每 3 分鐘拉一次，最多等 20 分鐘。仍不是就停止，不寫 notes，回報「資料管線今天沒有更新」。
2. 執行 `python3 pipeline/brief.py` 讀精簡摘要（約 20KB）。**不要讀整份 latest.json**；需要某個欄位就用 python 取。各欄位怎麼寫，見下面「各版判讀」。
3. 讀上一期 `data/notes.json`（用來比較變化、延續期數）。
3a. **找發現（今天最重要的一步，2026-10-23 起）**：brief 最前面的 `signals` 是資料管線依寫死規則偵測出的異動（`pipeline/signals.py`），`signals.checks` 是上一期 findings／followups 寫下的追蹤條件今天成不成立。先讀完這兩塊，再讀其他數字；依下面「發現與追蹤」的規則寫 `findings` 與 `followups`，頭條、摘要、各版判讀都從這裡出發。
3b. **結構分析（2026-10-27 起）**：每週一，或 `signals` 出現 `level:sth-cluster`、價格穿越短期持有者成本／真實市場均價時，依下面「結構分析」的八步，至少寫一則從行情問題出發的 finding（不是從異動出發）。其他天有值得回答的問題也可以寫。
4. ETF 暫定值（你唯一可以改資料檔的情況）：ETF 由資料管線每天從 The Block 自動更新（`pipeline/etf.py`，與 Farside 同口徑；Farside 擋自動抓取，不要再去讀它），**除了這個例外，你不改 `data/etf.json`**。比最新完整日更新的交易日，如果查到**兩個獨立來源**（例如 Farside 經媒體轉述、SoSoValue）的合計淨流量差距在 2% 以內，可以在 `data/etf.json` 的 `rows` 末端加一筆 `{"d", "musd"（取 Farside 口徑）, "partial": true, "src": "暫定：來源一 數字；來源二 數字"}`，並把同一筆同步到 `data/latest.json` 的 `flows.etf`；只有一個來源或差距超過 2% 就不加。The Block 公布後資料管線會自動覆寫。
5. 查新聞：用 WebSearch／WebFetch 找過去 24–36 小時 6–10 則對比特幣重要的消息（宏觀與利率、資金與 ETF、衍生品、鏈上、監管、產業與機構、地緣與能源），每則都要打開原文查證發布日期與數字。來源與寫法見「新聞」。
6. 查研報：先用 WebFetch 打開 Glassnode 研報列表 https://research.glassnode.com （The Week On-chain 約每週二／三、Market Pulse 每週日、Macro Special 不定期），找出最近 7 天的每一期並打開原文讀重點；再查 The Block Research、K33、Coinbase Institutional 週評，以及其他具名研究機構最近 7 天的新研報／週報。每一期的 `date` 寫原文發布日、`url` 寫原文網址。確認列表上真的沒有新一期，才沿用最近一期並在 `research.summary` 寫明「無新一期」。
7. 寫 `data/notes.json`（格式見下）。`edition` 為上一期 +1（若上一期的 `date` 已等於 `meta.bar_date`，代表是同一天重寫，`edition` 不變）；`date` 等於 `meta.bar_date`；`written_utc` 寫實際的 UTC 時間（用 `date -u` 取得，不要估）。寫完後另寫英文版 `data/notes.en.json`（見「英文版」）。
8. 驗證：執行 `python3 pipeline/notes_lint.py`，檢查格式、各項數量、頭條與摘要長度、制式提醒句次數、事件表必備項目、英文版沒有中文字；有任何一項沒過就改到通過才提交。再用 python 掃描兩個檔，確認沒有違反隱私鐵則的內容。
9. X 貼文草稿（中英各一則）：寫 `data/x_post.json` = `{"date": bar_date, "edition", "zh", "en", "image_zh": "https://north7.github.io/daybreak/data/share.png", "image_en": "https://north7.github.io/daybreak/data/share-en.png", "link": "https://north7.github.io/daybreak/?utm_source=x"}`。分享圖由 GitHub Actions 在你推送後自動產生（`pipeline/share_card.py`，用 headline 與資料），你不用畫。
   - 格式（中文；英文同結構，用 `【Daybreak No.007｜Oct 12】`）：
     ```
     【破曉 No.007｜10/12】
     <headline，可縮短，保留關鍵數字>

     ・市場階段：牛市（第 4 天）
     ・ETF 7 個交易日（至 10/09）：−5.58 億美元
     ・<今天最重要的 finding：結論＋一個關鍵數字；沒有 finding 才用最重要的數字或事件>

     完整解讀 👉 https://north7.github.io/daybreak/?utm_source=x
     ```
   - 數字一律取自 brief 與當期 notes，不新增查不到出處的數字；市場階段天數＝bar_date 減 `cycle.stage.since` 加 1；ETF 那一行＝`flows.etf` 最後 7 個非暫定日合計，括號寫最後一個非暫定日（英文 `・ETF 7 trading days to Oct 9: −$558M`），與分享圖一致；不寫「近 7 日」，因為 The Block 常晚一到兩個交易日，頭條若寫更新的暫定值，讀者會以為兩個數字矛盾。
   - 執行 `python3 pipeline/x_len.py`，兩則都要 ≤ 280（X 的算法：中文字算 2、網址算 23）；超過就縮短 headline 那行。
   - 不放 hashtag 以外的標記；hashtag 最多 1 個（中文 `#比特幣`、英文 `#Bitcoin`）。不喊單、不寫價格目標或「該買／該賣」；出場框架只用百分比；隱私鐵則同樣適用。
10. 提交訊息 `notes: <bar_date>`（notes.json、notes.en.json、x_post.json 一起），推送到 main。
11. 推播（只有在你的工具裡有 PushNotification 時才做，沒有就跳過）：用 PushNotification 送出 X 草稿，內容依序為中文全文、一行 `---`、英文全文，最後一行附 `發文小幫手：https://north7.github.io/daybreak/post.html`（可一鍵複製、開 X 發文視窗、存圖）；不要加其他說明。

### notes.json 格式
```json
{
  "date": "YYYY-MM-DD", "written_utc": "ISO 時間", "edition": 2,
  "stance": {"label": "週期中段・持有", "tone": "neutral|warm|hot|cold", "short": "四到八個字"},
  "headline": "號外大標題：一句話總結今天 BTC 市場的全貌，或今天最重大的消息；至少含一個關鍵數字（不放收盤價、漲跌幅）",
  "summary": "最多三句、180 字以內：今天的判斷、理由、該盯什麼",
  "watch": [{"label": "200 日均線", "value": 71657, "note": "觸發條件與距離"}, "…共三項"],
  "modules": {
    "overview": {"lead": "一句結論", "points": ["每點一句，最多 3–4 個數字"]},
    "cycle": {}, "market": {}, "deriv": {}, "flows": {}, "onchain": {}, "exit": {}
  },
  "news": [{"time": "YYYY-MM-DD", "cat": "宏觀｜資金｜衍生品｜鏈上｜監管｜產業｜機構｜地緣", "impact": "bull|bear|neutral", "weight": 1,
            "title": "發生了什麼（一句，含關鍵數字）", "source": "媒體名，日期", "url": "原文網址",
            "read": "解讀：對 BTC 的意義，並對照本站數據（例如 ETF 近 7 日合計、交易所供給、資金費率），說明會改變什麼、不會改變什麼", "module": "相關版面 id（flows/deriv/onchain/cycle…）"}],
  "events": [{"date": "YYYY-MM-DD", "label": "事件"}],
  "actions": [{"kind": "do|dont|watch|flip", "head": "一句粗體結論", "text": "補充：價位、距離、條件"}],
  "changes": [{"dir": "up|down|flat", "title": "變了什麼（含數字）", "fig": "前後對照的數字", "say": "所以呢：會改變什麼、不會改變什麼"}],
  "findings": [{"id": "YYYY-MM-DD-1（bar_date 加序號）", "title": "結論一句（有判斷，不是數字描述）", "module": "onchain", "chart": "sthpnl（圖表 id，連結用）",
                "signals": ["extreme:sth-profit:hi", "combo:profit-into-drop"], "confidence": "high|medium|low",
                "lean": "bull|bear|neutral", "lean_why": "一句：為什麼偏多／偏空（對價格的一般含意）",
                "what": "發生了什麼：關鍵數字與資料日期", "why": "拆解與交叉比對：是哪一邊在動、哪些獨立資料印證或矛盾",
                "alt": "其他解釋與資料限制", "history": "過去同樣情況（日期、樣本數）", "so": "改變了什麼、沒改變什麼",
                "next": "接下來看什麼：條件與時間",
                "check": [{"path": "onchain.sth_pnl.profit", "op": "<|<=|>|>=", "value": 4000, "by": "YYYY-MM-DD", "means": "confirm|refute", "label": "實現獲利回到 4,000 顆以下"}]}],
  "followups": [{"id": "上期 finding 的 id", "title": "原標題", "since": "第一次發現的日期", "status": "open|confirmed|refuted|expired",
                 "say": "一句：結果如何（引用 signals.checks 的今天數值）", "check": "繼續追蹤時可更新條件（格式同上，可省略）"}],
  "research": {"summary": "一句話：最新研報和本站讀值是否一致",
               "items": [{"source": "Glassnode", "title": "研報名稱", "date": "YYYY-MM-DD", "url": "原文網址", "access": "full|title_only",
                          "points": "重點（含價位數字）", "meaning": "對本站判斷的意義"}]}
}
```

### 寫作規則

#### 共通
- 每個模組 `lead` 是一句結論（先說「所以呢」：這一版今天最值得注意的是什麼、代表什麼），**不是數字清單**；不好的例子：「短期持有者回到獲利：獲利比例由 68.6% 升到 78.2%、賣出盈虧比 1.008；近 7 日淨實現獲利 +10.85 億…」（整句都是數字）。`points` 2–4 點，每點一句、最多 3–4 個數字，全部取自 brief 的數字，標明資料日期（若晚於收盤日）；這一版有 finding 時，第一點寫它和這一版其他數字的關係。
- 不寫短線價格預測（不預測未來幾天的漲跌、區間或機率）。
- 第三方模型（Tidemark）只作讀值。不同資料商的數字不相減。分數一律附樣本數。寧可寫「本日未取得」，也不推估或沿用昨天的數字。
- 頁首「資料狀態」若顯示延遲，判讀要標明。某項資料沒取到（`meta.errors` 有它）時寫「本日未取得」並照抄錯誤訊息裡的原因（例如某來源被 Cloudflare 擋下），不要自己猜成「解析失敗」。
- 頁面上每個數字已有依固定門檻自動產生的解讀（`assets/app.js` 的「數字解讀」區塊：各版「這些數字代表什麼」與鏈上表格下方的解讀列），每張圖下方也有自動「現在／怎麼讀」。各版 `modules` 的判讀不必逐項重述，也不必重述圖上讀數，重點放在跨指標的綜合結論與今天的變化；若你的判讀和自動解讀方向不同，要寫出原因。
- 制式提醒句（「只作讀值」「不改變框架」「不是框架條件」「不碰…」）全期最多 4 次（新聞的 `read` 不算，那裡本來就要說影不影響週期判斷）。網站的方法說明與每張圖下方的讀法已經寫過，不必每點重複；只在讀值容易被誤會成買賣訊號，或你的判讀和自動解讀方向不同時才寫。規則指定要附的限制（例如「線性外推、不是預測」、淨實現損益在 ETF 時代可能變鈍）照寫，不算在內。

#### 發現與追蹤（findings／followups，2026-10-23 起；網站頭版最上方「今日發現」）
這是日報最有價值的部分：讀者自己看得到數字，看不到的是「哪裡不尋常、為什麼、代表什麼、接下來看什麼」。各版判讀只是補充。
- **數量**：`findings` 0–3 則，依重要性排序。今天真的沒有值得寫的，就給空陣列，不要硬湊；硬湊的發現比沒有更糟。
- **從哪裡來**：先看 `signals.items`（依分數排序；`kind`：extreme 一年 2% 極端值、jump 7 日急變、cross 狀態翻轉、level 關鍵價位、streak 連續、combo 跨指標組合與同主題多項同時異動）。每則 finding 的 `signals` 至少列一個 id；signals 沒抓到、但你從數據或新聞看出的，可以 `signals: []`，在 `why` 寫明依據。同一件事的多個 signal 合成一則，不要拆成好幾則。`new: true` 的優先；連續好幾天的（`days`）只有在有新發展時才再寫成 finding，否則放進 followups。
- **深度要求（每則都要做到）**：
  1. **title 是結論**：一句有判斷的話（例：「短線買家趁跌集中獲利了結」），不是數字描述（不要「實現獲利 7,940 顆、第 98.9 百分位」）。30 字以內。
  2. **拆解**：先問「是哪一邊在動」。能拆就拆：SOPR → 實現獲利／實現虧損（`decomp`）；資金費率 → 各交易所；ETF → 哪幾天、是不是單日；價格 → 現貨（Coinbase 溢價、ETF）還是衍生品（資金費率、清算）推動。
  3. **交叉比對**：至少用兩個不同來源或不同類型的指標互相印證，或指出它們矛盾（矛盾本身常常就是發現）。寫明各自的資料日期；不同資料商的數字不相減。
  4. **其他解釋**（`alt`）：至少一個，加上資料限制（平滑、晚幾天、單日、口徑、交易所錢包整理或大額轉帳）。
  5. **歷史**（`history`）：signal 的 `hist` 有過去同樣情況的日期、`fwd30`（之後 30 天價格變化）、`fwd30_med` 與同期基準 `base30_med`、樣本數 `n`。可以引用，但一定附樣本數；`n` < 5 寫「樣本太少，只能當背景」；不得寫成預測（不要「歷史上之後會漲」）。`ctx`（「N 天來最高，上次 …」）也可以用。
  6. **所以呢**（`so`）：改變了什麼、沒改變什麼（對市場階段、出場框架、其他判讀的影響）。
  7. **可驗證**（`next` 與 `check`）：寫出接下來會確認或推翻這個判斷的條件與期限（通常 1–7 天）。`check` 1–2 個，`path` 必須是 latest.json 裡存在的數字欄位（例如 `onchain.sth_pnl.profit`、`chips.viz.sopr.value`、`deriv.funding_multi.weighted_now`、`price.bar.c`、`deriv.dvol.value`），`means` 寫這個條件成立代表 confirm（確認）還是 refute（推翻）。資料管線下一期會自動算出成不成立（`signals.checks`）。
  8. **confidence**：high＝多個獨立來源一致且不是單日；medium＝有印證但有明顯限制；low＝單一來源或單日。
  9. **多空**（`lean`，2026-10-23 使用者要求）：這則發現整體偏多（bull）、偏空（bear）還是中性（neutral），`lean_why` 一句說為什麼，開頭不要再寫「偏多／偏空」（網站已經標了；例：「獲利籌碼在下跌中湧出，短線供給增加；不是恐慌，不代表週期轉空」）。和新聞的 `impact` 同一套標準：描述這件事對價格的一般含意，不是預測；多空互見、真的分不出來才用 neutral，不要為了保險都寫中性。網站會依各則的 lean 算出整體多空。
- **不准**：價格預測、買賣建議、把同時發生寫成因果、把同一個數字換句話說當發現、引用 brief 沒有的數字。
- **追蹤**（`followups`）：上一期的每一則 finding，以及上一期 followups 裡 status 為 open 的，這期都要列一筆（`notes_lint.py` 會檢查）。依 `signals.checks`：條件成立且 means＝confirm → confirmed；成立且 means＝refute → refuted；過了期限（`expired`）還沒成立 → expired；其他 → open（可以更新 check 繼續追）。`say` 一句講結果，引用今天的數值。confirmed／refuted／expired 列這一次就結案，下期不用再列。
- **和其他欄位的關係**：最重要的 finding 若比今天的新聞重要，頭條就寫它的結論；摘要第一句也從 findings 來。`changes` 只記 findings 沒寫到的其他變化，不要重複。

#### 結構分析：從數據推出行情邏輯（2026-10-27 起）
異動型的發現回答「哪裡不尋常」；結構分析回答「行情接下來的邏輯是什麼」。範本是 Murphy〈跌破 $80K 的 BTC，潛在拋壓有多大？〉上下篇：把籌碼拆成長期／短期持有者，比較行情啟動前和現在誰賣給誰，再推「跌到哪裡、誰會賣、誰會接」。讀者自己看得到每個數字，看不到的是把它們串成一條邏輯。
- **格式**：和異動型 finding 相同（`signals` 可以是空陣列，在 `why` 寫明依據）。`title` 寫推出來的邏輯（例：「低點買家已大半換手，80–86K 新籌碼成為回調深度的關鍵」），不是問題本身。
- **八步**（每一步都要能在 brief 找到數字；找不到就不寫那一步，也不推估）：
  1. **問題**：一句話、能被數據回答。例：跌破某價位的潛在賣壓有多大？這波反彈是誰在買、誰在賣？上方解套賣壓在哪？是現貨還是槓桿在推？
  2. **拆參與者**：誰持有、誰在動（見下表）。同一個總數，拆開以後常常方向相反，那才是重點。
  3. **成本地圖**：各群體的成本在哪（短期持有者成本、真實市場均價、長期持有者成本、`chips.cohort_read.sth_top` 最厚的格子、`deriv.options` 大量未平倉的履約價、`orderbook` 的牆）。價格相對成本的位置決定誰在獲利、誰在水下、誰會防守。
  4. **比較兩個時點**：行情啟動前 vs 現在（`chips.cohort.flow`、`cmp`；7／30 日變化）。看誰變多、誰變少、籌碼換手到哪個價位，不要只描述現在。
  5. **分清事實與推算**：資料商直接公布的數字、價格沒走過的區間（`chips.cohort.flow.model_free_above`）是事實；`chips.cohort` 價格走過區間內的拆分是推算，寫明「推算」並引用 `chips.cohort.val` 的驗證差距。
  6. **用行為確認**：帳面虧損不等於會賣、帳面獲利不等於會倒貨；單日大量的「賣出」先看是不是搬家日（`chips.cohort.transfers`），逐筆 UTXO 的指標分不出內部轉帳。用實際行為印證：STH-SOPR 與認賠低點（`chips.sopr_read`）、短期持有者實現獲利／虧損（`onchain.sth_pnl`）、淨實現損益（`onchain.npl`）、LTH 30 日淨部位（`onchain.top_radar`）、交易所供給、ETF。寫出哪些印證、哪些矛盾。
  7. **情境**：用 `chips.cohort.loss`：價格到某價位時帳面虧損的短期／長期持有者有多少、哪一層增加最快；籌碼薄的區間價格走得快，厚的地方容易停（支撐或解套壓力）。只寫「如果到 X，Y 會在水下」這種條件句，不寫機率、目標價或幾天內會到。
  8. **結論與推翻條件**：結論寫成邏輯鏈（「A 已經發生，所以 B；C 還沒發生，所以 D 還不成立」），`next` 與 `check` 寫會確認或推翻它的數字與期限（例：`price.bar.c` 收在最厚籌碼下方 3 天、`onchain.sth_pnl.loss` 升破某值）。
- **可拆的維度（現有資料）**：
  | 問題 | 拆法 | brief 欄位 |
  |---|---|---|
  | 籌碼與潛在賣壓 | 長期／短期持有者 × 成本格、約 30 天換手、跌到各價位的帳面虧損 | `chips.cohort`、`chips.cohort_read`、`chips.urpd` |
  | 短線買家是否投降 | 實現獲利 vs 實現虧損、SOPR 認賠低點一次比一次深或淺 | `onchain.sth_pnl`、`chips.sopr_read`、`onchain.npl` |
  | 老手是否派發 | LTH 30 日淨部位（這段方向從哪天開始、同期價格怎麼走）、高位套牢盤的變化（不靠模型）、LTH-SOPR | `onchain.lth_color`、`onchain.top_radar`、`chips.cohort.flow.model_free_above`、`onchain.metrics.lth-sopr` |
  | 誰在推價格 | 現貨（ETF、Coinbase 溢價）vs 槓桿（資金費率、基差、DVOL） | `flows.etf`、`flows.cb_premium`、`deriv.funding_multi`、`deriv.deriv`、`deriv.dvol` |
  | 上下方的牆 | 掛單簿、選擇權履約價與到期、整數關卡 | `orderbook`、`deriv.options` |
  | 資金背景 | 穩定幣、實現市值 30 日變化、實質利率、美元 | `flows.stables`、`flows.rc_liq`、`flows.dfii10`、`flows.fred` |
- **寫法**：先結論再證據；每個數字附資料日期與來源；推算的數字標「推算」；不同資料商的數字不相減；本站是逐筆 UTXO，不和 Glassnode 實體調整的數字比大小（方向可以比）；引用外部分析師（例如 Murphy）時寫明他用的資料口徑，和本站數字不同時說明可能原因，不要硬湊成一致。

#### 頭條與摘要
- 頭條（headline）是號外大標題：一句話總結今天整個 BTC 市場的狀況（資金、宏觀、衍生品、鏈上，誰在主導、方向是什麼），或今天最重大的單一消息。**至少要有一個關鍵數字**（網站會把標題裡的數字標成號外紅，全黑的標題不好看），選最能說明今天狀況的數字，例如 ETF 淨流量、殖利率、清算金額、資金費率、鏈上轉移量、市場階段天數；不要用收盤價、漲跌幅、盤中高低點這類頁面上已經顯示的數字。不好的例子：「BTC 收 81,684（−1.91%）；離 200 日均線仍有 13.8%，出場框架 0 條觸發。」好的例子：「10 年期美債殖利率衝上 5.36%、油價破 100 美元，ETF 單日流出 4.85 億，市場轉入避險。」
- 長度（`notes_lint.py` 會檢查）：頭條 60 字以內（英文 150 字元）；摘要最多三句、180 字以內（英文 480 字元）。10/13–10/20 頭條 76–107 字、摘要 4–6 句，分享圖要縮到四行小字，手機上也太長；寧可少一個數字，也不要把整段寫進頭條。
- 頭條與出場框架：見下一節。

#### 出場框架、watch、actions、changes
- 出場框架任何一條觸發時（`exit.status.steps_hit` 非空、`p20_run_075`／`p20_run_080` ≥ 5、`below_sma200_run` ≥ 5、頂部三指標任兩項 ≥ 80），headline 必須第一句寫明，stance.tone 用 hot 或 cold。接近觸發時（收盤距 200 日均線、MVRV 0.75 線或出場第一階 5% 以內；`below_sma200_run`、`p20_run_075`、`p20_run_080` 任一 ≥ 3；或頂部三指標任兩項 ≥ 75）可以在 headline 點出。沒有觸發也不接近時，headline 不提出場框架、不寫「0 條觸發」、不寫離 200 日均線多遠（這些留在 watch 與各版）。
- `watch` 固定三項：200 日均線（避險線）、MVRV 0.75 線（`exit.status.k075_price`）、出場第一階（`exit.status.next_step`），附距離。
- `actions`（今天該做什麼、盯什麼）4–6 項，依序：`do` 可以做（依出場框架今天的動作，沒有觸發就寫不動）、`dont` 不要做（最容易犯的錯）、`watch` 要盯（今明兩天的事件與價位，附台北時間）、`flip` 會推翻（什麼收盤條件會讓框架動作，附價位與距離）。一律用框架語言（「依框架」「避險減 20%」），不寫任何人的持倉狀態。
- `changes`（今天變了什麼）3–5 項，只寫相對上一期真正改變的事：價格與量、資金流、衍生品、鏈上、市場階段天數；`fig` 寫「昨天 → 今天」的數字。沒有變化的不列。各版另外指定要記一筆的情況（實現市值 30 日正負翻轉、短期持有者成本真的上穿真實市場均價）見下面。

#### 各版判讀
**cycle（市場階段）**
- 市場階段由資料管線依寫死規則計算（`cycle.stage`：熊市／轉換期／牛市；牛市＝投降出現過且收盤連 30 日在上升的 200 日均線之上），你只引用，不改判；`cycle` 模組要寫現在的階段、天數（`above_rising_run`／30）與佐證燈號（`cycle.stage.evidence` 的 `ok`／`n`，並點名哪幾項亮、哪幾項沒亮）。佐證燈號只表示證據強弱，不要寫成「還差某條件才算牛市」。
- 佐證燈號有 6 盞，第 6 盞 `tmm`＝短期持有者成本高於真實市場均價（Murphy 的 STH-RP vs TMMP；bitcoin-data，晚約 7 天）。它是落後指標（2016、2019、2023 三次上穿都比週期底部晚 12–18 個月，2019 年上穿後仍跌近六成），只作佐證。真的交叉時在 changes 記一筆。
- brief 的 `cycle.stage.viz_reads` 有兩個讀值：`tmm_cross`（以近 30 日速度線性外推的交叉日）與 `mom12.flat_flip`（價格不動時 12 個月動能燈號翻轉的日子）；引用時一律寫明「線性外推／價格不動的假設，不是預測」，不寫成時間壓力或買賣建議。

**market（價格）**
- 短週期（brief 的 `price.swing`，收盤價 15% 反轉才算新的一段）：可寫目前這一段走了多久、多少、離本段結束線多遠；只作讀值，不連動任何規則。

**deriv（衍生品）**
- 資金費率用 brief 的 `deriv.funding_multi.weighted_now`（Deribit、OKX、Hyperliquid 以未平倉加權）；25Δ 風險逆轉是 30 天固定期限。
- 掛單簿不是獨立版面（modules 沒有 book），掛單重點寫進 deriv 判讀。
- 籌碼集中度（現價 ±5%）：brief 的 `chips.flow.conc5`（URPD 晚約 1 天，按 ±5% 區間重疊比例計、除以 CoinMetrics 流通量）與 `chips.conc5_read`（7 天前、紀錄天數）。可和 DVOL 一起寫「籌碼擠在現價附近時，離開這一帶波動容易放大」，但只說波動、不說方向；本站自 2026-10-01 才有紀錄，**不套任何門檻（包括 Murphy 的 13%／15%）**、不寫「偏高／偏低」，只寫數值與 7 日變化。

**flows（資金）**
- ETF：從 brief 的 `flows.etf` 讀數字；The Block 只公布已完整的交易日，最新完整日通常比 bar_date 晚一到兩個交易日，寫的時候標明日期。若最新完整日比 bar_date 落後超過 2 個交易日，在 flows 寫明「ETF 資料延遲」。暫定值的規則見步驟 4。
- 實現市值 30 日變化（brief 的 `flows.rc_liq`）：只當資金背景寫進 flows 判讀（例：「實現市值 30 日 +1.3%，資金仍在流入」）；轉為 ≤0 或由 ≤0 轉正時在 changes 記一筆。不得寫成加倉或賣出訊號，也不連動市場階段與出場框架（歷史上 2018、2021-06、2022-01 的歸零之後仍大跌，見資金版說明）。
- 可引用穩定幣供給（`flows.stables`）、Coinbase 溢價（`flows.cb_premium`）、恐懼貪婪（`flows.fear_greed`）。

**onchain（鏈上）**
- 頂部三指標（MVRV Z／NUPL／Puell）由 CoinMetrics 自算，資料日期通常是收盤前一天，照實寫該日期（不要寫成 bitcoin-data 那種晚約 6 天的舊日期）。
- 可引用算力帶（`onchain.hash_ribbons`）。
- 短期持有者認賠賣壓（STH-SOPR）：brief 的 `chips.sopr_read` 有最新值與最近三次認賠低點（`kind`：easing＝價格回到前次認賠低點附近但深度較淺、賣壓遞減；heavier＝較深、賣壓加重）。可引用，但要寫明資料日期（來自 CheckOnChain，晚約 1 天、日線；盤中集中認賠會被當天的獲利賣出平均掉，日線不一定跌破 1），只作讀值、不寫成買點或見底預測。
- 每日淨實現損益：brief 的 `onchain.npl`（CoinMetrics 實現市值日變化 − 新發行，晚約 1 天；`usd_m` 當日淨值百萬美元、`rank_1y` 在之前 365 天的百分位、`sum7_usd_m`／`sum7_prev_usd_m` 近 7 日與前 7 日合計、`loss_spike_last`／`profit_spike_last` 最近一次 ≤2／≥98 百分位）。可寫「獲利了結降溫／增溫」「出現明顯認賠」並附數字與日期；只有淨值，不寫成獲利或認賠的總額。**不把認賠高峰寫成買點或見底，不把獲利高峰寫成頂部**。
  - 單日高峰（2026-10-18 即時可行回測，2015 起、每串高峰取第一天）：認賠高峰之後 30／90 日與平常沒有差別；獲利高峰之後 30 日中位 +12.9%（平常 +3.2%），但一輪比一輪弱（+21.5%→+12.3%→+5.0%），只能當趨勢強的佐證。
  - 30 日累計模式（`onchain.npl.cum30`：`pct_4y` 4 年百分位、`thr_pct_mcap` 觸發線、`trig` 歷次首次跌破、`min_since_top` 本輪最深）：跌破 4 年第 3 百分位過去 5 次（2015–2022）1 年後都上漲，但 3 次之後還再跌 17–44%，本輪沒有觸發，只能寫成「週期級別的認賠／底部區佐證」。ETF 時代這個訊號可能變鈍（ETF 股份在股市換手不上鏈、只有淨贖回才移動鏈上的幣；2025-10～2026-06 下跌中 ETF 只淨贖回約 13.4 萬顆、約一成八，本輪按跌幅換算的認賠只有前幾輪一半；過去 5 次觸發都在 2024-01 ETF 上市之前），寫到它時要附這個限制，不寫「沒觸發所以還沒見底」。
- 長短期持有者籌碼（`chips.cohort`，2026-10-27 起，`pipeline/cohort_urpd.py`）：**「現在」與「變化」來源不同**（2026-10-28 起）。`src`＝`checkonchain` 時，`rows`／`tot`／`loss`（現在的分布）來自 CheckOnChain 依每顆幣實際幣齡算的公開圖表（Bitcoin Research Kit，資料日 `now_date`，已套用搬家修正），不是推算；`src`＝`model` 表示 CheckOnChain 當天沒取到、退回推算。`model_rows`／`model_tot`、`cmp`、`flow` 一律是推算（bitcoin-data URPD × 幣齡分布 × 每日價格區間），`vs` 是推算和實際的差距（`sth_diff_pct` 總量、`misplaced_pct` 分錯格的比例）。`tot` 總量與平均成本；`rows` 每 2,000 美元一格的［價位, STH, LTH］（brief 略去，看 `chips.cohort_read` 的最厚格子）；`flow` 和約 30 天前比（`sth_spent`／`lth_spent` 那時的短期／長期持有者動了多少、`new` 之後買進還沒動的、`model_free_above` 價格沒碰過的高位區，變化就是賣出、不靠模型）；`loss` 收盤跌到各價位時帳面虧損的 STH／LTH；`val` 推算的 STH 成本 vs bitcoin-data 公布值。寫法：現在的分布在 `src`＝`checkonchain` 時寫「CheckOnChain，資料日」，不寫推算；變化（`flow`、`cmp`）一律標「推算」，可引用 `vs` 或 `val` 的差距；逐筆 UTXO、不是實體調整，交易所整理錢包會被算成換手，換手量偏高，不和 Glassnode／Murphy 的數字比大小；帳面虧損不等於會賣，要配合 STH-SOPR 與實現虧損寫；URPD 本身晚 1–2 天，寫明 `chips.cohort.date`。
  - **搬家日**（`chips.cohort.transfers`、signal `jump:urpd-transfer`，2026-10-27 起）：某天遠離現價的格子大量流出、同一天等量出現在現價那一格，逐筆 UTXO 會把它算成賣出再買進，但量大又集中的多半是同一實體整併錢包。模型已把這批幣放回原本的成本與幣齡（`raw` 是不修正的原樣）。寫法：這幾天的流出**不寫成賣出或低點買家離場**，寫「疑似內部轉帳」；同一天的淨實現獲利、STH-SOPR、短期持有者實現獲利高峰也是逐筆 UTXO 算的，會被同一筆搬家灌大，不能拿來佐證有人在賣。教訓（2026-10-22）：62–66K 一天少 19 萬顆、全進 80–82K，本站當時寫成「低點買家在賣」；Murphy 與 @market_beggar 指出 Glassnode 實體調整的 STH 已實現利潤當天沒有反應，是機構內部調倉。
- 價格 × 長期持有者動向（`onchain.lth_color`，2026-10-29 起，`pipeline/stage_viz.py` 的 `lth_color_viz`）：鏈上版的價格線依長期持有者 30 日淨部位上色（紅＝淨減、灰＝持平 ±5 萬顆內、藍＝淨增，±40 萬顆最深），資料就是 bitcoin-data `lth-net-position-change-30d`，不另打 API。`run` 是這段方向（只看正負）從 `start` 起連續 `days` 天、期間最深 `extreme`、同期價格 `price0`→`price`（`price_chg_pct`）；`prev_same` 是這段之前上一次一樣深的日子；`pct_4y` 四年百分位；`vs_hi1y_pct` 距一年高點。寫法：重點是**方向和價格的組合**——價格漲、老手淨減＝趁反彈出貨，上方有供給；價格跌、老手淨增＝持有者不賣；價格跌、老手也減＝賣壓來自老幣。`run.days` 很短（例如 ≤ 7）代表剛翻方向，值得當發現寫。不可寫成「吸籌評分」或和 Glassnode 的 Accumulation Trend Score 比較：那個以實體計、排除交易所，是不同指標；bitcoin-data 同名的 `accumulation-trend-score` 是這條線的換算。淨增也包括幣放滿 155 天自動轉成長期持有者，不寫成「有人在買」。
- 鯨魚分層（`onchain.whales`，BitInfoCharts 依地址餘額）**2026-10-21 起暫停**（BitInfoCharts 擋自動抓取，brief 沒有 `onchain.whales`）：判讀不提鯨魚分層，也不寫「本日未取得」；brief 重新出現 `onchain.whales` 時才恢復，恢復後的寫法：可寫大戶（100–10K）30 日與本段以來的增減；≥10K 多為交易所與託管，不寫成大戶買賣；只作讀值，不連動任何規則。

#### 新聞
- 每則消息的解讀都要回扣本站數據，說清楚它是短線雜訊還是會影響週期判斷；單一來源或數字不一致者在 title 後標「（未核實）」。
- 新聞的 `url` 與 `source` 用原始報導（通訊社、主流財經與加密媒體、官方公告、發行商網站）。Substack 摘要、每日彙整頁、行情回顧網站（10/18–10/19 用過 bitcoinnewsdigest、investrade）只能拿來找線索，要點進它引用的原文查證後引用原文；找不到原文就不列，或在 title 後標「（未核實）」。
- 新聞 `weight` 3＝頭條級、2＝重要、1＝參考，頭版會依 weight 排序取前四則。

#### 研報
- `research`（權威研報）：每列寫來源與日期、重點（含價位數字）、對本站判斷的意義；沒讀到全文的 `access` 填 `title_only`，且不作判斷依據。研報結論與本站讀值衝突時，在 `meaning` 寫明衝突與本站採用哪個、為什麼。

#### 事件表
- `events` 滾動維護未來 60 天：難度調整（`onchain.mining.retarget`）、FOMC、CPI、非農、Deribit 月度與季度到期、每個月底的路徑重估、Tidemark 低點驗證日 2026-12-19。官方排程優先；官方還沒公布的寫慣例日期並標「待官方排程確認」。**每一類都必須在**：CPI 公布後要立刻補上下一次（10/14–10/20 連 7 期漏掉 11 月的 CPI）；季度到期（例如 12/25）在 60 天內就要列，不能只寫在衍生品版。

#### 英文版
- 寫完 `data/notes.json` 後，另寫 `data/notes.en.json`：結構、欄位、數字、日期、網址、`impact`、`kind`、`dir`、`module` 與中文版完全相同，只把文字欄位（headline、summary、stance.label／short、watch[].label／note、modules 各版 lead／points、news[].title／read／source、events[].label、actions[].head／text、changes[].title／fig／say、findings[] 的 title／lean_why／what／why／alt／history／so／next 與 check[].label、followups[].title／say、research.summary 與 items[].points／meaning；研報原文標題本來就是英文的照抄）翻成自然的英文。
- `news[].cat` **保持中文**（網站用它篩選，英文版顯示時自動換成 Macro／Flows 等）；除此之外不應有任何中文字（`notes_lint.py` 會掃描）。
- 台北時間後面加註 UTC；金額用 $ 與 K／M／B，不用「萬／億」；「資金面」譯成 flows（funding 只指資金費率）。
- 英文版網站讀這個檔，缺檔或日期比中文舊時會退回中文並標示。隱私鐵則同樣適用。

### 回報
最後用 3 行以內摘要：今天的結論、findings 幾則（標題）與 followups 結果、出場框架有沒有任何觸發、市場階段、哪些資料沒取到、X 草稿字數（x_len.py 的結果）。
