# 破曉 Daybreak

每天清晨的第一份比特幣簡報：今日要聞與解讀、市場數據、週期位置與分批出場框架。純靜態網站（HTML／CSS／JS，無建置步驟），部署在 GitHub Pages。

## 結構

```
index.html              網站入口（10 個版面：頭版、消息、週期、價格、衍生品、資金、鏈上、掛單簿、出場框架、方法；號外風格，日刊／夜刊兩種主題）
assets/app.css          品牌與版面（深色優先，含淺色主題）
assets/app.js           路由、圖表、互動（無外部套件）
assets/logo.svg         Logo（也是 favicon）
data/latest.json        每日資料（由 GitHub Actions 產生，不要手改）
data/notes.json         每日頭條、各版判讀與今日要聞解讀（由 Claude 每日任務寫入）
data/etf.json           ETF 每日淨流量（由 Claude 每日任務從 Farside 更新）
data/model.json         固定模型參數：出場框架、長期路徑（每月檢討時才改）
data/history/index.json 每日快照索引
pipeline/collect.py     抓取所有 API 並計算指標 → pipeline/today.json
pipeline/build.py       today.json → data/latest.json
pipeline/brief.py       印出精簡摘要給 Claude 讀
pipeline/params.json    collect.py 需要的兩個參數
pipeline/state_min.json 前一日的最小狀態（URPD 週變化、ATR 回測）
.github/workflows/daily.yml  每天 UTC 00:20 自動更新資料
docs/CLAUDE_DAILY.md    Claude 每日結論任務的完整指示
```

## 部署（一次性）

1. 建立公開倉庫 `daybreak`，把這個資料夾的內容推上去（main 分支）。
2. Settings → Pages → Source 選「Deploy from a branch」，Branch 選 `main`、資料夾 `/ (root)`。
3. Settings → Actions → General → Workflow permissions 選「Read and write permissions」。
4. Actions 頁面手動執行一次「Daily data」，確認 `data/latest.json` 有更新。
5. 在 Claude Code 連上這個倉庫，建立每日排程任務，指示內容見 `docs/CLAUDE_DAILY.md`（建議 UTC 01:10，晚於資料更新）。

## 每日流程

| 時間（UTC） | 誰 | 做什麼 | 耗 token |
|---|---|---|---|
| 00:20 | GitHub Actions | 抓資料、算指標、更新 `data/latest.json`、提交 | 0 |
| 01:10 | Claude 排程任務 | 讀摘要、查新聞、更新 ETF、寫頭條與消息解讀到 `data/notes.json`、提交 | 少量 |

網站讀到的 `notes.json` 日期若和資料日不同，仍會顯示上一期的判讀，數字部分永遠是最新的。

## 隱私

這是公開倉庫，所有歷史提交永久可查。網站只放市場資料與通用的出場框架（以「100% ＝ 本週期打算賣出的全部持倉」計），不得出現任何人的實際持倉數量、買賣數量或資金金額。

## 已知限制

- bitcoin-data.com 免費層每小時約 10 次請求；GitHub Actions 的共用 IP 偶爾會被限流，失敗的項目在網站上顯示「本日未取得」。
- Farside 擋自動化請求，所以 ETF 由 Claude 任務用網頁讀取更新。
- 掛單簿是 Actions 執行當下的快照；Binance 期貨與 Bybit 讀不到。

僅供研究參考，非投資建議。
