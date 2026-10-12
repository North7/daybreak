# 破曉 Daybreak

每天清晨的第一份比特幣簡報：今日要聞與解讀、市場數據、週期位置與分批出場框架。純靜態網站（HTML／CSS／JS，無建置步驟），部署在 GitHub Pages。

## 結構

```
index.html              網站入口（10 個版面：頭版、消息、週期、價格、衍生品、資金、鏈上、出場框架、往期、方法；號外風格，日刊／夜刊兩種主題；掛單簿 2026-10-12 起縮成衍生品版的小卡）
manifest.webmanifest    加到手機主畫面用（圖示在 assets/icon-*.png；分享預覽圖 assets/og.png）
assets/app.css          品牌與版面（深色優先，含淺色主題）
assets/app.js           路由、圖表、互動（無外部套件）；文字用 _t() 包起來，英文版查 assets/i18n-en.js
assets/i18n-en.js       英文字典（中文原句 → 英文）；改過 app.js 的文字後跑 pipeline/check_i18n.py
assets/logo.svg         Logo（也是 favicon）
data/latest.json        每日資料（由 GitHub Actions 產生，不要手改）
data/notes.en.json      notes.json 的英文版（每日任務同時寫；缺檔時英文版退回中文）
data/notes.json         每日頭條、各版判讀、今天該做什麼、今天變了什麼、今日要聞與研報解讀（由 Claude 每日任務寫入）
data/etf.json           ETF 每日淨流量（資料管線從 The Block 自動更新，與 Farside 同口徑）
data/model.json         固定模型參數：出場框架、長期路徑（每月檢討時才改）
data/history/index.json 每日快照索引
data/archive/           往期封存：每一期的 notes（與英文版）＋ index.json（頭條、當天收盤、之後漲跌、要盯的價位有沒有被碰到）
pipeline/collect.py     抓取所有 API 並計算指標 → pipeline/today.json
pipeline/build.py       today.json → data/latest.json；最後呼叫 archive.py 封存前一期
pipeline/archive.py     往期封存與判讀回顧（一次性回填：python3 pipeline/archive.py --backfill-git）
pipeline/brief.py       印出精簡摘要給 Claude 讀
pipeline/etf.py         從 The Block 更新 ETF 每日淨流量
pipeline/check_i18n.py  檢查 app.js 每個 _t() 字串都有英文
pipeline/stamp_assets.py 改過 assets/ 後執行：更新 index.html 的 ?v= 版本號，避免手機拿到新舊混搭的 CSS／JS
pipeline/bd_rotation.py bitcoin-data 請求分配：每日即時 6 個 + 前一晚 8 個（全部每天更新）
pipeline/bd_cache/      前一晚抓的鏈上指標快取（由 Prefetch on-chain 寫入）
pipeline/params.json    collect.py 需要的兩個參數
pipeline/state_min.json 前一日的最小狀態（URPD 週變化、ATR 回測）
.github/workflows/daily.yml     每天 UTC 00:06 由 cron-job.org 觸發更新資料（GitHub 自己的排程會晚 5–7 小時，只當備援；見 docs/CRON_JOB.md）
.github/workflows/prefetch.yml  每天 UTC 22:40 由 cron-job.org 觸發，抓 8 個鏈上指標（備援同上）
.github/workflows/check.yml     PR 合併前檢查：語法、英文字典、版本號、用無頭瀏覽器渲染每一版（tests/smoke.js）
.github/workflows/etf.yml       每天 UTC 14:00 補抓 ETF 流量
docs/CLAUDE_DAILY.md    Claude 每日結論任務的完整指示
docs/CRON_JOB.md        cron-job.org 準時觸發的設定步驟
```

## 部署（一次性）

1. 建立公開倉庫 `daybreak`，把這個資料夾的內容推上去（main 分支）。
2. Settings → Pages → Source 選「Deploy from a branch」，Branch 選 `main`、資料夾 `/ (root)`。
3. Settings → Actions → General → Workflow permissions 選「Read and write permissions」。
4. Actions 頁面手動執行一次「Daily data」，確認 `data/latest.json` 有更新。
5. 在 Claude Code 連上這個倉庫，建立每日排程任務，指示內容見 `docs/CLAUDE_DAILY.md`（UTC 00:30＝台北 08:30，晚於資料更新）。

## 每日流程

| 時間（UTC） | 誰 | 做什麼 | 耗 token |
|---|---|---|---|
| 22:40（前一天） | cron-job.org → GitHub Actions | 抓 8 個鏈上指標進 `pipeline/bd_cache/` | 0 |
| 00:06 | cron-job.org → GitHub Actions | 抓資料（含 ETF）、算指標、更新 `data/latest.json`、封存前一期、提交 | 0 |
| 00:30 | Claude 排程任務 | 讀摘要、查新聞與研報、寫頭條與消息解讀到 `data/notes.json`、提交 | 少量 |

網站讀到的 `notes.json` 日期若和資料日不同，仍會顯示上一期的判讀，數字部分永遠是最新的。

## 語言

網站有中文與英文兩種版本。使用者在頁面上選過語言就一直沿用（存在瀏覽器 localStorage）；沒選過時，依訪客 IP 所在國家決定預設：台灣、香港、澳門、中國大陸、新加坡用中文，其他地區用英文。國家由瀏覽器向 api.country.is（備援 get.geojs.io）查詢，結果快取 7 天；查不到時看瀏覽器語言。數字的解讀由前端產生，兩種語言都有；每日判讀與新聞需要每日任務另寫 `data/notes.en.json`。

## 隱私

這是公開倉庫，所有歷史提交永久可查。網站只放市場資料與通用的出場框架（以「100% ＝ 本週期打算賣出的全部持倉」計），不得出現任何人的實際持倉數量、買賣數量或資金金額。

## 已知限制

- bitcoin-data.com 免費層每小時 10 次、每日 15 次。2026-10-12 起頂部三指標（MVRV Z／NUPL／Puell）改用 CoinMetrics 自算（只晚 1 天；bitcoin-data 版晚約 6 天），並退役 realized-price、realized-cap-growth-rate、sopr，現在每天共 14 次：00:06 即時抓 6 個、前一晚 22:40 抓 8 個，全部每天更新。bitcoin-data 部分序列本身晚 5–6 天，頁首「資料狀態」會列出每個來源的落後天數。
- 其他免費來源（2026-10-12 新增）：DefiLlama（穩定幣供給）、Coinbase 與 Binance 日線（Coinbase 溢價）、OKX 與 Hyperliquid（資金費率，與 Deribit 以未平倉加權）、alternative.me（恐懼貪婪指數）；任一失敗只影響該項。
- 鯨魚分層持幣來自 BitInfoCharts 的分布歷史頁（一次請求、不佔 bitcoin-data 額度）；地址不等於實體，≥10K 多為交易所與託管。若對方改版或擋 GitHub Actions，該區塊顯示「本日未取得」，不影響其他資料。
- Farside 用 Cloudflare 擋所有自動抓取，ETF 改用 The Block 的圖表 JSON（pipeline/etf.py，逐日與 Farside 比對一致）；The Block 只公布已完整的交易日，約晚一天。
- 掛單簿是 Actions 執行當下的快照；Binance 期貨與 Bybit 讀不到。2026-10-12 起只在衍生品版留一張摘要卡。
- 內文中文用系統字型，只有標題載入 Noto Sans TC 900；Google Fonts 在中國大陸讀不到時，版面用備用字型，已確認不會橫向溢出。

僅供研究參考，非投資建議。
