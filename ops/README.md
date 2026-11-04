# 破曉運營 · Daybreak Ops

網站本身（`index.html`、`pipeline/`、`data/`）負責「產出簡報」；`ops/` 負責「把簡報推出去」：每日發文、每日推薦圖表與解說、短影片。

> 這個資料夾在 GitHub Pages 上也會被公開（`https://north7.github.io/daybreak/ops/...`），頁面都加了 `noindex`，但不要放帳號、金鑰或未公開的東西。

## 結構

```
ops/
  README.md          這份說明
  post/index.html    X 發文小幫手（原本的根目錄 post.html，2026-11-04 搬進來；根目錄 post.html 現在只轉址到這裡）
  post/flash.py      快訊配圖 → data/flash/<id>-<語言>.png（依 data/flash.json）
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
    cards.py           回覆配圖 → data/replies/<n>.png
    check.py           檢查 replies.json 與 flash.json（語言、字數、簡體字、框架用詞、配圖）
```

## 目標：X 創作者分潤（Original Content Rewards）

2026-11-04 使用者的進度：藍勾追蹤者 91／500、近 90 天藍勾首頁曝光離 50 萬還很遠。兩條都只算藍勾，而且**回覆不算曝光**。所以：

- **回覆負責漲追蹤**：只挑藍勾大帳號、發文 30 分鐘內回、帶圖（Grok 規則已要求 10 則至少 8 則藍勾）。
- **原創貼文負責衝曝光**：每天 3–5 則原創、都帶圖；日報中英文分兩則發；盤中有事件就發快訊；大帳號的貼文用「引用」而不是只回覆（引用算原創）。
- 不做互粉、買粉、互刷互動（違反 X 的平台操縱規則，可能失去分潤資格）。

## 每日流程

| 時間 | 誰做 | 做什麼 | 產出 |
|---|---|---|---|
| 08:30 | Claude 每日任務（`docs/CLAUDE_DAILY.md`） | 寫中英 X 貼文草稿並推播到手機；挑今日推薦圖表、寫中英解說 | `data/x_post.json`、`data/picks.json` |
| 推送後 | GitHub Actions `share.yml` | 畫當日分享圖、今日推薦圖表 | `data/share.png`、`data/share-en.png`、`data/picks/` |
| 你 | 手機開發文小幫手 | 一鍵把圖文送進 X | <https://north7.github.io/daybreak/ops/post/> |
| 你／Claude | 本機 | 做當日短影片（見下） | `ops/video/out/` |
| 日報後 | Grok → Claude → 你 | Grok 找可回覆的 X 貼文，Claude 讀原文、依當日數據寫回覆和配圖，你在回覆小幫手照順序回（標「建議引用」的用引用發） | `data/replies.json`、`data/replies/`；<https://north7.github.io/daybreak/ops/replies/> |
| 盤中有事時 | Claude → 你 | 新低／新高、ETF 數據、大爆倉：寫中英文快訊和配圖，放到發文小幫手最上面 | `data/flash.json`、`data/flash/` |

## 發文小幫手

<https://north7.github.io/daybreak/ops/post/>（舊網址 `post.html` 會自動轉過來，手機書籤不用改）

讀 `data/x_post.json`：中英文各一則，顯示 X 字數（與 `pipeline/x_len.py` 相同算法），手機可用分享選單把圖文一起送進 X、存圖到相簿、開 X App 發文視窗、複製文字。

下方「今日推薦圖表 · Today's picks」讀 `data/picks.json` 與 `data/picks/index.json`：每張圖中英文各一份，可分享（圖＋解說）、存到相簿、複製解說、下載。`picks.json` 還不是當天的時候，只顯示 Actions 自動挑好的圖（沒有解說）。

最上方「快訊 · Breaking」讀 `data/flash.json`，只顯示 36 小時內的快訊；按鈕和當日貼文一樣（手機分享選單圖文一起送進 X）。

## 快訊

什麼時候發：這一段行情的新低／新高、關鍵價位被穿過（短期持有者成本、清算帶、整數關卡）、ETF 單日大額流入流出公布、大爆倉。使用者說「有什麼可以發」時也照這個做。

1. 查即時數字：Kraken 價格與當日高低點、OKX 資金費率、Coinbase 對幣安的價差；和 `data/latest.json`、`data/notes.json` 的價位、籌碼、清算帶對照。
2. 寫 `data/flash.json`：每則 `{"id", "time"（UTC）, "title", "note", "zh", "en", "image"}`；中英文分開寫、都要有人味（同 `replies/README.md`），只講資訊，結尾帶 2–3 個 hashtag（中文 `#比特幣 #BTC`＋主題、英文 `#Bitcoin #BTC`＋主題）。`image` 同回覆配圖，另可用 `title_zh`／`title_en` 和 `stats`（覆寫底部三格，例如換成盤中低點）。
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

每天請 Grok 找 10 則值得用數據回覆的 X 貼文（中文 6、英文 4，以藍勾博主為主，Murphy 必看）（規則在 [`replies/grok-prompt.md`](replies/grok-prompt.md)），把結果貼給 Claude 寫回覆和配圖（規則在 [`replies/README.md`](replies/README.md)），再到回覆小幫手 <https://north7.github.io/daybreak/ops/replies/> 照順序回。英文貼文回英文、中文貼文回繁體中文；和短影片同一個原則：只放資訊，預設不貼連結。

## 之後可以加

- 影片模板化：把 `make_short_0xx.py` 共用的繪圖函式抽成一份，每期只換分鏡與旁白 JSON。
- 發文紀錄：每天發了什麼、哪張圖、成效（手動填），回頭看哪種內容有效。
