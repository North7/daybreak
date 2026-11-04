# X 互動回覆

目的：在別人的比特幣討論裡，補上 Daybreak 才有的數字，讓看到的人記住這個帳號、回頭追蹤。不是去貼連結。

挑文章只看一件事：**這篇在講的東西，Daybreak 今天有沒有一個具體數字能印證、補充或反駁它。**有的才回，再依時效和曝光排優先順序。

## 每日流程

1. **找文（Grok）**：日報出來後，把 [`grok-prompt.md`](grok-prompt.md) 裡的整段貼給 Grok。它會讀當天的 `data/notes.json`，回傳一張最多 8 則的候選表（英文 5、中文 3，每則有分數和建議角度）。
2. **寫回覆（Claude）**：在 `daybreak-ops` 資料夾開 session，把 Grok 的表格（或 CSV 檔）貼上，說「幫我寫回覆」。Claude 照下面的步驟寫好，推到 main。
3. **回覆（你）**：手機打開回覆小幫手 <https://north7.github.io/daybreak/ops/replies/>，照順序一則一則回。

## 回覆小幫手

`ops/replies/index.html` 讀 `data/replies.json` 與 `data/replies/<n>.png`：

- 每則顯示原文（即時讀自 api.fxtwitter.com，讀不到就顯示摘要）、我們的回覆與 X 字數、配圖、用到的數字。
- 手機：「存配圖」→ 存到相簿；「複製回覆並開原文」→ X App 打開那則貼文，按回覆、貼上、加圖。
- 電腦：「在 X 回覆」開好回覆視窗並帶入文字；配圖要先下載再自己加。
- 「標記已回覆」只記在那台裝置；跳過的貼文收在最下面，附原因。

## Claude 寫回覆的步驟

1. **讀原文**：`python3 ops/replies/fetch.py <Grok 的 CSV 或網址>`。Grok 的摘要、語言、粉絲數常常錯，一律以原文為準。原文不是中文或英文、粉絲不到 2,000、或內容是標題黨、喊單、操作建議的，標成跳過並寫原因。
2. **讀當天的數據**：`data/notes.json`（英文 `data/notes.en.json`）的 headline、findings、news、modules，數字細節查 `data/latest.json`、`data/etf.json` 等。只引用數據裡有的數字，不改數字、不自己推算新數字。`notes.json` 的日期不是當期時，先跟使用者確認。
3. **寫 `data/replies.json`**（格式見下），需要配圖的加 `image`。
4. **出圖**：`python3 ops/replies/cards.py --fonts <字型資料夾>`（需要 `pipeline/picks.py` 與 Pillow；字型同 `share_card.py`）。打開每張圖看一遍。
5. **檢查**：`python3 ops/replies/check.py`（欄位、語言、簡體字、字數、出場框架用詞、配圖檔）。
6. **提交**：`replies: <日期>`（`data/replies.json` 與 `data/replies/`），推到 main。GitHub Pages 約 1 分鐘後更新。
7. 在對話裡回報：發文順序、跳過哪些與原因、需要使用者留意的地方。

## 回覆規則

- **語言**：英文貼文回英文，中文貼文（簡體或繁體）一律用繁體中文回。其他語言不回。
- **一則只講一個重點**，附上日期和來源（例如「ETF 11/02 −3.99 億，兩日 −10.4 億（The Block）」）。來源寫數據的原始出處，不是寫 Daybreak。
- **只講資訊**：不提出場框架（觸發條數、價格階梯、MVRV 賣出線、200 日均線避險），不給買賣建議，不寫「今天不動」這類動作結論。和短影片同一個原則。
- **預設不放連結**。對方問數據來源，或真的需要看圖時，才附 `https://north7.github.io/daybreak/`。
- **語氣是補充，不是糾正**：要反駁時，先承認對方說對的部分，再用數字說明另一面。
- **長度**：X 加權字數 280 以內（中文字算 2、網址算 23），最好在 200 左右，手機上一眼看完。
- 不寫 emoji 串、hashtag、「DYOR」「NFA」這類套話。

**依建議角度寫**

| 角度 | 怎麼寫 |
|---|---|
| 補數據 | 對方說了 A，補一個他沒提到、但指向同一件事的數字 |
| 交叉驗證 | 用另一個來源或指標確認（或削弱）對方的數字 |
| 提出反例 | 「X 是對的，不過 Y 顯示……」：一個數字、一個解讀 |
| 回答提問 | 直接回答，第一句就給數字 |

**配圖**：回覆的重點數字在某張圖上看得出來時才配（例如 Coinbase 溢價走勢、STH-SOPR、ETF 流量、籌碼分布、清算價位）。圖的語言跟回覆一樣；原文提到價位時，清算圖用 `marks` 把那些價位標出來。

## data/replies.json

```json
{
  "date": "2026-11-04",          // 回覆的日期
  "data_date": "2026-11-03",     // 用的是哪一期數據（latest.json 的 bar_date）
  "edition": 29,
  "items": [{
    "n": 5,                      // Grok 表格的編號；配圖檔名 data/replies/5.png
    "order": 1,                  // 建議回覆順序
    "status": "send",            // send／optional／skip
    "url": "https://x.com/<帳號>/status/<ID>", "id": "<ID>",
    "author": "<帳號>", "name": "<名稱>", "followers": 414401, "posted": "2026-11-03T17:01:00Z",
    "lang": "en",                // 原文的實際語言（fetch.py 讀到的）
    "angle": "交叉驗證",
    "summary": "原文重點（自己的話，原文讀不到時顯示）",
    "reply": "可直接貼的回覆",
    "sources": "用到的數字 · 日期 · 來源",
    "note": "給使用者的提醒；跳過時寫原因",
    "image": {"chart": "liq", "title": "圖上的大標題", "marks": [75000, 76200]}   // 可省略
  }]
}
```

`image.chart` 可用 `pipeline/picks.py` 的圖表 id（`cbp`、`sopr`、`etf`、`cohort`、`cost`、`stab`、`npl` 等），或 `liq`（推算清算價位分布，OKX）。
