# 破曉運營 · Daybreak Ops

網站本身（`index.html`、`pipeline/`、`data/`）負責「產出簡報」；`ops/` 負責「把簡報推出去」：每日發文、每日推薦圖表與解說、短影片。

> 這個資料夾在 GitHub Pages 上也會被公開（`https://north7.github.io/daybreak/ops/...`），頁面都加了 `noindex`，但不要放帳號、金鑰或未公開的東西。

## 結構

```
ops/
  README.md          這份說明
  post/index.html    X 發文小幫手（原本的根目錄 post.html，2026-11-04 搬進來；根目錄 post.html 現在只轉址到這裡）
  picks/             每日推薦發文圖表＋解說（規劃中，見 picks/README.md）
  video/             每日短影片腳本（原本在 media/）
    make_audio.py      配音（edge-tts 台灣語音）＋自製配樂 → timing.json、mix.wav
    make_short_015.py  No.015 分鏡（1080×1920、30fps，Pillow 逐格畫、ffmpeg 編碼）
    make_short_016.py  No.016 分鏡（目前最新的版本，下一期從這份複製）
    lines_016.json     No.016 旁白 {"base": [每場景秒數], "lines": [每場景一句]}
    out/               輸出的 mp4、封面、字幕（不進 git，影片太大）
  replies/           X 互動回覆
    index.html         回覆小幫手（讀 data/replies.json 與 data/replies/ 的配圖）
    grok-prompt.md     給 Grok 的找文規則（每天整段貼給 Grok）
    README.md          回覆流程、Claude 寫回覆的規則、replies.json 格式
    fetch.py           讀 X 原文（api.fxtwitter.com），核對 Grok 的摘要
    cards.py           回覆配圖 → data/replies/<n>.png
    check.py           檢查 replies.json（語言、字數、簡體字、框架用詞、配圖）
```

## 每日流程

| 時間 | 誰做 | 做什麼 | 產出 |
|---|---|---|---|
| 08:30 | Claude 每日任務（`docs/CLAUDE_DAILY.md`） | 寫中英 X 貼文草稿並推播到手機 | `data/x_post.json` |
| 推送後 | GitHub Actions `share.yml` | 畫當日分享圖 | `data/share.png`、`data/share-en.png` |
| 你 | 手機開發文小幫手 | 一鍵把圖文送進 X | <https://north7.github.io/daybreak/ops/post/> |
| 你／Claude | 本機 | 做當日短影片（見下） | `ops/video/out/` |
| 日報後 | Grok → Claude → 你 | Grok 找可回覆的 X 貼文，Claude 讀原文、依當日數據寫回覆和配圖，你在回覆小幫手照順序回 | `data/replies.json`、`data/replies/`；<https://north7.github.io/daybreak/ops/replies/> |

## 發文小幫手

<https://north7.github.io/daybreak/ops/post/>（舊網址 `post.html` 會自動轉過來，手機書籤不用改）

讀 `data/x_post.json`：中英文各一則，顯示 X 字數（與 `pipeline/x_len.py` 相同算法），手機可用分享選單把圖文一起送進 X、存圖到相簿、開 X App 發文視窗、複製文字。

## 短影片

```bash
cd ops/video
python make_audio.py out/017 zh-TW-HsiaoChenNeural lines_017.json
python make_short_017.py ../.. ~/fonts out/daybreak-017-short.mp4 --audio out/017
```

需要 Pillow、numpy、ffmpeg、edge-tts，字型與分享圖相同（`share.yml` 下載的 Noto Sans TC、Archivo、JetBrains Mono）。

**內容原則：影片只放資訊**（價格、市場階段、衍生品、ETF 資金、消息、接下來的日期與價位），**不放出場框架**（觸發條數、價格階梯、MVRV 賣出線、200 日均線避險、「今天不動」這類動作結論）。做分鏡與旁白時跳過 `notes.json` 的 `exit` 模組、`watch` 裡的框架線、`actions` 的動作建議。

## 互動回覆

每天請 Grok 找 8 則值得用數據回覆的 X 貼文（規則在 [`replies/grok-prompt.md`](replies/grok-prompt.md)），把結果貼給 Claude 寫回覆和配圖（規則在 [`replies/README.md`](replies/README.md)），再到回覆小幫手 <https://north7.github.io/daybreak/ops/replies/> 照順序回。英文貼文回英文、中文貼文回繁體中文；和短影片同一個原則：只放資訊，預設不貼連結。

## 之後可以加

- `picks/`：每天從當日數據挑 1–3 張最值得發的圖，附一段可直接貼的解說（見 `picks/README.md`）。
- 影片模板化：把 `make_short_0xx.py` 共用的繪圖函式抽成一份，每期只換分鏡與旁白 JSON。
- 發文紀錄：每天發了什麼、哪張圖、成效（手動填），回頭看哪種內容有效。
