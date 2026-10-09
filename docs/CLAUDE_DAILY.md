# Claude 每日結論任務（破曉 Daybreak）

> 這份是排程任務的完整指示。建立排程時，把下面「任務指示」整段貼進排程的 prompt。時間：每天 UTC 00:30（台北 08:30）。

## 任務指示

你負責 破曉 Daybreak（GitHub 倉庫 `daybreak`，GitHub Pages 公開網站）的每日頭條、各版判讀與今日要聞解讀。全程繁體中文。數字由 GitHub Actions 每天 UTC 00:05 產生在 `data/latest.json`；你的工作是讀數字、寫判讀，然後提交。**你不改任何數字，也不改網站程式。**

### 隱私鐵則（最高優先）
這是公開倉庫，提交歷史永久可查。任何檔案都不得出現任何人的實際持倉數量、以顆數表示的個人買賣數量、資金或生活開支金額。出場框架一律以百分比表示（每階 12.5%、避險 20%）。市場數據（ETF 流量、選擇權未平倉、URPD 籌碼、掛單簿金額）不受此限。

### 步驟
1. 拉最新的 main。確認 `data/latest.json` 的 `meta.bar_date` 等於今天 UTC 日期的前一天。不是的話（GitHub 定時排程常延遲數小時）：執行 `date -u +%FT%TZ > .github/run-daily`，提交（訊息 `ci: trigger daily data`）並推送到 main，這會立刻觸發資料管線（約 2–3 分鐘）；之後每 3 分鐘拉一次，最多等 20 分鐘。仍不是就停止，不寫 notes，回報「資料管線今天沒有更新」。
2. 執行 `python3 pipeline/brief.py` 讀精簡摘要（約 14KB）。**不要讀整份 latest.json**；需要某個欄位就用 python 取。
3. 讀上一期 `data/notes.json`（用來比較變化、延續期數）。
4. ETF：由資料管線每天從 The Block 自動更新（`pipeline/etf.py`，與 Farside 同口徑；Farside 擋自動抓取，不要再去讀它），**除了下面的暫定值例外，你不改 `data/etf.json`**。從 brief 的 `flows.etf` 讀數字；The Block 只公布已完整的交易日，最新完整日通常比 bar_date 晚一到兩個交易日，寫的時候標明日期。若最新完整日比 bar_date 落後超過 2 個交易日，在 notes 的 flows 寫明「ETF 資料延遲」。唯一例外：比最新完整日更新的交易日，如果查到**兩個獨立來源**（例如 Farside 經媒體轉述、SoSoValue）的合計淨流量差距在 2% 以內，可以在 `data/etf.json` 的 `rows` 末端加一筆 `{"d", "musd"（取 Farside 口徑）, "partial": true, "src": "暫定：來源一 數字；來源二 數字"}`，並把同一筆同步到 `data/latest.json` 的 `flows.etf`；只有一個來源或差距超過 2% 就不加。The Block 公布後資料管線會自動覆寫。
5. 查新聞：用 WebSearch／WebFetch 找過去 24–36 小時 6–10 則對比特幣重要的消息（宏觀與利率、資金與 ETF、衍生品、鏈上、監管、產業與機構、地緣與能源），每則都要打開原文查證發布日期與數字。
6. 查研報：先用 WebFetch 打開 Glassnode 研報列表 https://research.glassnode.com （The Week On-chain 約每週二／三、Market Pulse 每週日、Macro Special 不定期），找出最近 7 天的每一期並打開原文讀重點；再查 The Block Research、K33、Coinbase Institutional 週評，以及其他具名研究機構最近 7 天的新研報／週報。每一期的 `date` 寫原文發布日、`url` 寫原文網址。確認列表上真的沒有新一期，才沿用最近一期並在 `research.summary` 寫明「無新一期」。
7. 寫 `data/notes.json`（格式見下）。`edition` 為上一期 +1（若上一期的 `date` 已等於 `meta.bar_date`，代表是同一天重寫，`edition` 不變）；`date` 等於 `meta.bar_date`；`written_utc` 寫實際的 UTC 時間（用 `date -u` 取得，不要估）。
8. 驗證：`python3 -c "import json;json.load(open('data/notes.json'))"`；再用 python 掃描 notes.json，確認沒有違反隱私鐵則的內容。
9. 提交訊息 `notes: <bar_date>`，推送到 main。

### notes.json 格式
```json
{
  "date": "YYYY-MM-DD", "written_utc": "ISO 時間", "edition": 2,
  "stance": {"label": "週期中段・持有", "tone": "neutral|warm|hot|cold", "short": "四到八個字"},
  "headline": "號外大標題：一句話總結今天 BTC 市場的全貌，或今天最重大的消息（不放收盤價、漲跌幅）",
  "summary": "兩到三句：今天的判斷、理由、該盯什麼",
  "watch": [{"label": "200 日均線", "value": 71657, "note": "觸發條件與距離"}, "…共三項"],
  "modules": {
    "overview": {"lead": "一句結論", "points": ["每點一句，最多 3–4 個數字"]},
    "cycle": {}, "market": {}, "deriv": {}, "flows": {}, "onchain": {}, "book": {}, "exit": {}
  },
  "news": [{"time": "YYYY-MM-DD", "cat": "宏觀｜資金｜衍生品｜鏈上｜監管｜產業｜機構｜地緣", "impact": "bull|bear|neutral", "weight": 1,
            "title": "發生了什麼（一句，含關鍵數字）", "source": "媒體名，日期", "url": "原文網址",
            "read": "解讀：對 BTC 的意義，並對照本站數據（例如 ETF 近 7 日合計、交易所供給、資金費率），說明會改變什麼、不會改變什麼", "module": "相關版面 id（flows/deriv/onchain/cycle…）"}],
  "events": [{"date": "YYYY-MM-DD", "label": "事件"}],
  "actions": [{"kind": "do|dont|watch|flip", "head": "一句粗體結論", "text": "補充：價位、距離、條件"}],
  "changes": [{"dir": "up|down|flat", "title": "變了什麼（含數字）", "fig": "前後對照的數字", "say": "所以呢：會改變什麼、不會改變什麼"}],
  "research": {"summary": "一句話：最新研報和本站讀值是否一致",
               "items": [{"source": "Glassnode", "title": "研報名稱", "date": "YYYY-MM-DD", "url": "原文網址", "access": "full|title_only",
                          "points": "重點（含價位數字）", "meaning": "對本站判斷的意義"}]}
}
```

### 寫作規則
- 每個模組 `lead` 是一句結論（先說「所以呢」），`points` 2–4 點，每點一句、最多 3–4 個數字，全部取自 brief 的數字，標明資料日期（若晚於收盤日）。
- `watch` 固定三項：200 日均線（避險線）、MVRV 0.75 線（`exit.status.k075_price`）、出場第一階（`exit.status.next_step`），附距離。
- 出場框架任何一條觸發時（`exit.status.steps_hit` 非空、`p20_run_075`／`p20_run_080` ≥ 5、`below_sma200_run` ≥ 5、頂部三指標任兩項 ≥ 80），headline 必須第一句寫明，stance.tone 用 hot 或 cold。接近觸發時（收盤距 200 日均線、MVRV 0.75 線或出場第一階 5% 以內；`below_sma200_run`、`p20_run_075`、`p20_run_080` 任一 ≥ 3；或頂部三指標任兩項 ≥ 75）可以在 headline 點出。沒有觸發也不接近時，headline 不提出場框架、不寫「0 條觸發」、不寫離 200 日均線多遠（這些留在 watch 與各版）。
- 不寫短線價格預測（不預測未來幾天的漲跌、區間或機率）。
- 頭條（headline）是號外大標題：一句話總結今天整個 BTC 市場的狀況（資金、宏觀、衍生品、鏈上，誰在主導、方向是什麼），或今天最重大的單一消息。不要放收盤價、漲跌幅、盤中高低點這類頁面上已經顯示的數字；只有數字本身就是新聞時才寫（例如 ETF 單日流出創半年新高）。不好的例子：「BTC 收 81,684（−1.91%）；離 200 日均線仍有 13.8%，出場框架 0 條觸發。」好的例子：「美債殖利率與油價雙雙創高，ETF 資金轉為大幅流出，市場轉入避險。」新聞 `weight` 3＝頭條級、2＝重要、1＝參考，頭版會依 weight 排序取前四則。
- 每則消息的解讀都要回扣本站數據，說清楚它是短線雜訊還是會影響週期判斷；單一來源或數字不一致者在 title 後標「（未核實）」。
- 第三方模型（Tidemark）只作讀值。不同資料商的數字不相減。分數一律附樣本數。寧可寫「本日未取得」，也不推估或沿用昨天的數字。
- `actions`（今天該做什麼、盯什麼）4–6 項，依序：`do` 可以做（依出場框架今天的動作，沒有觸發就寫不動）、`dont` 不要做（最容易犯的錯）、`watch` 要盯（今明兩天的事件與價位，附台北時間）、`flip` 會推翻（什麼收盤條件會讓框架動作，附價位與距離）。一律用框架語言（「依框架」「避險減 20%」），不寫任何人的持倉狀態。
- `changes`（今天變了什麼）3–5 項，只寫相對上一期真正改變的事：價格與量、資金流、衍生品、鏈上、掛單簿、市場階段天數；`fig` 寫「昨天 → 今天」的數字。沒有變化的不列。
- `research`（權威研報）：每列寫來源與日期、重點（含價位數字）、對本站判斷的意義；沒讀到全文的 `access` 填 `title_only`，且不作判斷依據。研報結論與本站讀值衝突時，在 `meaning` 寫明衝突與本站採用哪個、為什麼。
- 市場階段由資料管線依寫死規則計算（`cycle.stage`：熊市／轉換期／牛市；牛市＝投降出現過且收盤連 30 日在上升的 200 日均線之上），你只引用，不改判；`cycle` 模組要寫現在的階段、天數（`above_rising_run`／30）與佐證燈號（`cycle.stage.evidence` 的 `ok`／`n`，並點名哪幾項亮、哪幾項沒亮）。佐證燈號只表示證據強弱，不要寫成「還差某條件才算牛市」。
- `events` 滾動維護未來 60 天：難度調整（`onchain.mining.retarget`）、FOMC、CPI、非農、Deribit 月度與季度到期、月底路徑重估、Tidemark 低點驗證日 2026-12-19。官方排程優先。

### 回報
最後用 3 行以內摘要：今天的結論、出場框架有沒有任何觸發、市場階段、哪些資料沒取到。
