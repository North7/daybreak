# 破曉運營 · Daybreak Ops

網站本身（`index.html`、`pipeline/`、`data/`）負責「產出簡報」；`ops/` 負責「把簡報推出去」：每日發文、每日推薦圖表與解說、短影片。

> 這個資料夾在 GitHub Pages 上也會被公開（`https://north7.github.io/daybreak/ops/...`），頁面都加了 `noindex`，但不要放帳號、金鑰或未公開的東西。

## 結構

```
ops/
  README.md          這份說明
  post/index.html    X 發文小幫手（原本的根目錄 post.html，2026-11-04 搬進來；根目錄 post.html 現在只轉址到這裡）
  post/flash.py      快訊配圖 → data/flash/<id>-<語言>.png（依 data/flash.json）
  post/site_shot.py  網站圖表截圖（本機 Chrome 無頭模式＋內建小伺服器；深色；藏掉解讀文字）＋圖上文字位置 .json
  post/annotate.py   把文中引用的數字標在截圖上（座標由圖自己的刻度換算）
  post/longpost_img.py 長貼文配圖：幾張截圖疊成一張，標「圖1、圖2…」＋頁尾 → data/longposts/<id>.png
  picks/             每日推薦發文圖表＋解說的說明（程式在 pipeline/picks.py，圖在 data/picks/，見 picks/README.md）
  video/             每日短影片腳本（原本在 media/）
    make_audio.py      配音（edge-tts 台灣語音）＋自製配樂 → timing.json、mix.wav
    make_short_015.py  No.015 分鏡（1080×1920、30fps，Pillow 逐格畫、ffmpeg 編碼）
    make_short_016.py  No.016 分鏡（目前最新的版本，下一期從這份複製）
    lines_016.json     No.016 旁白 {"base": [每場景秒數], "lines": [每場景一句]}
    out/               輸出的 mp4、封面、字幕（不進 git，影片太大）
  articles/          X 長文草稿（中英文各一篇＋帶出長文的短貼文），檔名 <日期>-<主題>.md
    preview.py         長文預覽頁：md → 同名 .html，圖插在標好的位置，附複製標題／內文／短貼文按鈕（手機可直接照著發）
    charts.py          長文配圖（沿用 picks.py 版型，另有四輪對照、週線多空分數、冪律三張長歷史圖）→ img/<日期>/
  replies/           X 互動回覆
    index.html         回覆小幫手（讀 data/replies.json 與 data/replies/ 的配圖）
    grok-prompt.md     給 Grok 的找文規則（每天整段貼給 Grok）
    README.md          回覆流程、Claude 寫回覆的規則、replies.json 格式
    fetch.py           讀 X 原文（api.fxtwitter.com），核對 Grok 的摘要
    scan.py            掃固定名單最近 24 小時的貼文，排序、建議主題與配圖
    watchlist.json     固定名單（Murphy 等 27 個帳號）；Grok 只找名單以外的
    cards.py           回覆配圖 → data/replies/<n>.png
    check.py           檢查 replies.json 與 flash.json（語言、字數、簡體字、框架用詞、配圖）
  brand/             品牌與內容方向（2026-11-04 起）
    voice.md           品牌文件：寫給誰、相信什麼、反對什麼、語氣、用詞、使用者改稿紀錄（寫任何要發的東西前先讀）
    content-map.md     內容地圖：四個主題、解說題目、一週節奏、實驗清單
    references.md      參考帳號（Murphy 等）什麼貼文有人看、我們借用什麼
  log/               成效紀錄（2026-11-04 起）
    README.md          什麼時候記、格式
    log.py             update 自動記原創貼文、瀏覽、留言、追蹤者（含藍勾數）；add 手動加回覆；summary 彙整
    <日期>.json        每天一份
```

## 目標：X 創作者分潤（Original Content Rewards）

2026-09-07 起 X 的「創作者分潤」（Creator Revenue Sharing）停止，改成「原創內容獎勵」（Original Content Rewards），原本的會員也要重新申請。2026-11-05 依第三方整理更正（X 官方說明頁讀不到，數字以 Creator Studio → Original Content Rewards 頁為準）：

- **申請門檻**：Premium 訂閱、18 歲以上、**500 個藍勾追蹤**、**近 90 天來自藍勾用戶的首頁曝光 50 萬**（回覆不計入）；人工審核，被拒可在 42 天後重新申請。
- **付錢依據**：只算「合格曝光」：藍勾（Premium）用戶、在首頁時間軸、貼文至少一半顯示在畫面上、同一人只算一次；付費推廣與機器流量不算。每兩週付款。
- **什麼算原創**：要有自己的觀點、分析或自製的圖。不算：照抄、只改寫或加浮水印、**整理別人內容但沒有新觀點**、跨平台搬運、**用自動化工具發的貼文**、被加上社群備註（Community Note）的貼文。所以 Claude 起稿、你手動發，而且每則都要有自己的判斷（不是只列數字）；日報先寫自己的觀點，不要寫成消息整理。

進度：藍勾追蹤 2026-11-04 91（創作者頁）／105（追蹤者名單），11-05 X 後台顯示 103／500；藍勾首頁曝光 7 天 488（11/05），換算 90 天約 6 千，離 50 萬很遠。**11-06 創作者頁：藍勾追蹤 112／500、近 90 天藍勾首頁曝光 136／500,000**（50 萬換算每天約 5,600；加密讀者約兩成是藍勾，等於每天約 2.8 萬的原創總曝光）。瓶頸在原創，不在回覆。

推薦演算法（2026-01 開源，[xai-org/x-algorithm](https://github.com/xai-org/x-algorithm)）裡和我們有關的幾點：

- 「為你推薦」對**沒追蹤我們的人會濾掉我們的回覆**：回覆只在對方的討論串裡被看到，不會被推給陌生人。討論串裡的排序會看原作者有沒有回這則、看的人有沒有追蹤留言者、留言者是不是 Premium。
- 同一個作者短時間連發，後面幾則分數遞減：原創之間隔開（約 2–3 小時）。
- 預測的不只按讚：回覆、轉推、引用、分享、點開頭像、停留、追蹤都算；「不感興趣」「封鎖」「檢舉」是負分。曝光還少的新作者會被往前拉一點。
- **改顯示名稱會讓藍勾暫時消失、等審核**（2026-11-05 改名後藍勾斷了一段，當天回覆在串裡都排在後段、藍勾曝光幾乎是 0）。帳號資料固定下來，要改就在當天的發文和回覆都做完之後。

所以：

- **回覆負責漲追蹤**：回覆不算分潤曝光、也不會被推給陌生人，目的是讓對方回你、追蹤你：挑藍勾帳號、發文不久就回、帶圖；對方回了就接著聊（Grok 規則已要求 10 則至少 8 則藍勾）。
- **原創貼文負責衝曝光**（唯一算分潤的）：每天至少 3 則原創、都帶圖、分三個時段（同一個讀者看到你的第二則，權重只剩約 0.625 倍）：
  - 早上（日報出來後）：日報貼文
  - 中午（12:00–13:00）：推薦圖表（一天一張網站原圖，標題是讀者會問的問題，見 picks/README.md）；短貼文觸及常比長的好，可以只寫一兩句
  - 晚上（20:00–22:30，美股開盤前後）：長貼文，或大帳號新貼文的引用
  - 引用穿插在中間，和前一則隔 2 小時以上；盤中有事件就發快訊；日報中英文分兩則發
- **正文不放連結**（2026-11-06）：帶連結的貼文曝光少約四成（ClimbX 統計 89 則，中位數 −41%）。網站連結發完後貼在自己貼文底下的第一則回覆；發文小幫手的日報和快訊會自動把連結那行拆出來，按「複製連結回覆」。
- **發文後第一個小時回完自己貼文底下的每則留言**：會延長原貼文被推送的時間。
- **表現好的換角度再發**：一般貼文 48 小時後就不再被推薦。瀏覽明顯高於平常的，隔兩三天換個切入點或新數字重寫一則（不是重貼）。
- **回覆照階段加量**（100–1,000 粉這一段）：一天 15–20 則，只回 1 小時內的新貼文為主（最多 6 小時），對象是比我們大 2 到 10 倍的同領域帳號（幾千到幾萬粉），再加幾則大帳號剛發的；熟帳號三成、新帳號七成（`replies/README.md`）。
- **每週一記一次創作者頁的藍勾曝光**（Creator Studio → Original Content Rewards），填 `ops/log/` 當週紀錄的 `account.verified_impressions_90d`；一般後台的總曝光數字會高很多，不能拿來看門檻。
- 不做互粉、買粉、互刷互動（違反 X 的平台操縱規則，可能失去分潤資格）。

## 品牌與內容方向

寫任何要發出去的東西（日報貼文、快訊、解說、回覆、引用、長文、影片）之前，先讀 [`brand/voice.md`](brand/voice.md)：主要寫給拿現貨的中文持有者，角色是「一起看盤的同行」，第一句是數字，只講資訊。要發什麼主題看 [`brand/content-map.md`](brand/content-map.md)（四個主題：籌碼、資金、槓桿、週期，每週一則解說），寫法參考 [`brand/references.md`](brand/references.md)。

## 每日流程

| 時間 | 誰做 | 做什麼 | 產出 |
|---|---|---|---|
| 08:30 | Claude 每日任務（`docs/CLAUDE_DAILY.md`） | 寫中英 X 貼文草稿並推播到手機；挑今日推薦圖表、寫中英解說 | `data/x_post.json`、`data/picks.json` |
| 推送後 | GitHub Actions `share.yml` | 畫當日分享圖、今日推薦圖表 | `data/share.png`、`data/share-en.png`、`data/picks/` |
| 你 | 手機開發文小幫手 | 一鍵把圖文送進 X | <https://north7.github.io/daybreak/ops/post/> |
| 你／Claude | 本機 | 做當日短影片（見下） | `ops/video/out/` |
| 日報後 | Claude＋Grok → Claude → 你 | Claude 掃固定名單、Grok 找名單以外的貼文，Claude 讀原文、依當日數據寫回覆和配圖，你在回覆小幫手照順序回（標「建議引用」的用引用發）；讀原文時看到網站還沒有的指標或圖，順手記下 | `data/replies.json`、`data/replies/`；<https://north7.github.io/daybreak/ops/replies/>；點子記在 [`docs/indicator-ideas.md`](../docs/indicator-ideas.md) |
| 中午、晚上 | Claude → 你 | 每天 1–2 則圖表長貼文（X Premium 長貼文，不是 Article）：寫法見 [`brand/voice.md`](brand/voice.md) 改稿紀錄；配網站原圖（深色、文中數字標在圖上），放到發文小幫手「長貼文」 | `data/longposts.json`、`data/longposts/` |
| 盤中有事時 | Claude → 你 | 新低／新高、ETF 數據、大爆倉：寫中英文快訊和配圖，放到發文小幫手最上面 | `data/flash.json`、`data/flash/` |
| 你傳通知截圖時；隔天寫回覆前 | Claude | 記錄當天發了什麼、誰回應、瀏覽多少；隔天更新數字並彙整 | `ops/log/<日期>.json`（見 [`log/README.md`](log/README.md)） |

## 發文小幫手

<https://north7.github.io/daybreak/ops/post/>（舊網址 `post.html` 會自動轉過來，手機書籤不用改）

讀 `data/x_post.json`：中英文各一則，顯示 X 字數（與 `pipeline/x_len.py` 相同算法），手機可用分享選單把圖文一起送進 X、存圖到相簿、開 X App 發文視窗、複製文字。

下方「今日推薦圖表 · Today's picks」讀 `data/picks.json` 與 `data/picks/index.json`（2026-11-06 起一天一張網站原圖，標題是問句）：中英文各一份，可分享（圖＋解說）、存到相簿、複製解說、下載。`picks.json` 還不是當天的時候，只顯示 Actions 自動挑好的圖（沒有解說）。

最上方「快訊 · Breaking」讀 `data/flash.json`，只顯示 36 小時內的快訊；按鈕和當日貼文一樣（手機分享選單圖文一起送進 X）。

## 快訊

什麼時候發：這一段行情的新低／新高、關鍵價位被穿過（短期持有者成本、清算帶、整數關卡）、ETF 單日大額流入流出公布、大爆倉。使用者說「有什麼可以發」時也照這個做。

1. 查即時數字：Kraken 價格與當日高低點、OKX 資金費率、Coinbase 對幣安的價差；和 `data/latest.json`、`data/notes.json` 的價位、籌碼、清算帶對照。
2. 寫 `data/flash.json`：每則 `{"id", "time"（UTC）, "title", "note", "zh", "en", "image"}`；中英文分開寫、語氣照 `brand/voice.md`（第一句是數字；數字更新到以前發過的快訊時，建議用引用自己那則來發），只講資訊，結尾帶 2–3 個 hashtag（中文 `#比特幣 #BTC`＋主題、英文 `#Bitcoin #BTC`＋主題）。`image` 同回覆配圖，另可用 `title_zh`／`title_en` 和 `stats`（覆寫底部三格，例如換成盤中低點）。
3. 出圖：`python3 ops/post/flash.py --fonts <字型資料夾>`，打開圖看一遍。
4. 檢查：`python3 ops/replies/check.py`（會一起檢查 flash.json）。
5. 提交 `flash: <日期> <事件>`，推到 main；約 1 分鐘後手機打開發文小幫手就在最上面。

## 短影片

```bash
cd ops/video
python make_audio.py out/017 zh-TW-HsiaoChenNeural lines_017.json
python make_short_017.py ../.. ~/fonts out/daybreak-017-short.mp4 --audio out/017
```

需要 Pillow、numpy、ffmpeg、edge-tts，字型與分享圖相同（`share.yml` 下載的 Noto Sans TC、Archivo、JetBrains Mono）。

**內容原則：影片只放資訊**（價格、市場階段、衍生品、ETF 資金、消息、接下來的日期與價位），**不放出場框架**（觸發條數、價格階梯、MVRV 賣出線、200 日均線避險、「今天不動」這類動作結論）。做分鏡與旁白時跳過 `notes.json` 的 `exit` 模組、`watch` 裡的框架線、`actions` 的動作建議。

## 互動回覆

每天找約 10 則值得用數據回覆的 X 貼文（Claude 用 `replies/scan.py` 自己掃固定名單 `replies/watchlist.json`，Murphy 必看；Grok 只找名單以外的 5 則，規則在 [`replies/grok-prompt.md`](replies/grok-prompt.md)），把結果貼給 Claude 寫回覆和配圖（規則在 [`replies/README.md`](replies/README.md)），再到回覆小幫手 <https://north7.github.io/daybreak/ops/replies/> 照順序回。英文貼文回英文、中文貼文回繁體中文；和短影片同一個原則：只放資訊，預設不貼連結。

## 成效紀錄

2026-11-04 開始。你傳 X 通知截圖、或說「記錄今天」時，Claude 跑 `python3 ops/log/log.py update` 自動記下當天的原創貼文、瀏覽、底下的留言和追蹤者快照（藍勾追蹤離 500 還差多少），回覆再用內建瀏覽器讀「回覆」分頁補上、按讚看截圖；隔天寫新回覆之前先更新前一天、跑 `summary`，告訴你哪些有效。細節見 [`log/README.md`](log/README.md)。

## 之後可以加

- 影片模板化：把 `make_short_0xx.py` 共用的繪圖函式抽成一份，每期只換分鏡與旁白 JSON。

## 長貼文（2026-11-05 起）

每天 1–2 則，X Premium 長貼文（不是 X 長文 Article）。發文小幫手的「長貼文」一區**沒處理的一直顯示**（2026-11-05 使用者要求），依建議時間排；發完按「標記已處理」（只記在那台裝置），當天收起來，隔天起不再顯示。

**清理**：不再每天整份換新。Claude 寫新的長貼文之前，先問使用者哪幾則已經發了（或看 `ops/log/` 的成效紀錄），把已處理、而且處理日已經過去的那幾則從 `data/longposts.json` 刪掉，`data/longposts/` 的圖一起刪；沒處理的留著。快訊 `data/flash.json`、`data/flash/` 照舊，過期就刪。

- **寫法**（細節在 `brand/voice.md`）：像 Murphy 日常長貼文的深度和長度（約 600–1,000 字），一個核心指標＋1–2 個佐證；標題句 → 帶日期的數字 → 「何謂…」白話 → 歷史規律 → 現在 → 誰在買、誰在賣（只從大週期講）→ 我的判斷（有信心）→ 什麼情況下結論不成立（不要寫「什麼情況會讓我改看法」這種固定句） → 之後會再追。引用的極值用每日資料核對（`pipeline/coc_cache/bitview.json` 等），不要用 latest.json 裡抽樣過的 rows。
- **配圖**（在倉庫根目錄）：
  1. `python3 ops/post/site_shot.py <jobs.json> <資料夾>`：jobs 寫 `"theme": "dark"`、每張 `"clean": 1`，截網站原圖（上格價格、下格指標）。
  2. `python3 ops/post/annotate.py <spec.json> <資料夾> <輸出> <字型>`：文中提到、圖上找得到的數字都標上去。
  3. `python3 ops/post/longpost_img.py data/longposts/<id>.png <字型> <圖1> <圖2> ...`：疊成一張，標「圖1、圖2…」。X 多圖格子會把橫圖裁掉，所以一則只放這一張。
- `data/longposts.json`：`{"items": [{"id", "time"（建議發文時間，UTC）, "title", "note", "zh", "en"（可省）, "images": ["data/longposts/<id>.png"]}]}`
