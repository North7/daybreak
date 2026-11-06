# 交接文件（網站與資料管線）

給接手「破曉 Daybreak」網站／管線工作的 Claude session。最後更新：2026-11-05（原 session：claude.ai/code 的「數據分析方案」）。

## 1. 專案是什麼

- 比特幣每日簡報網站：<https://north7.github.io/daybreak/>（GitHub Pages，repo `North7/daybreak`，分支 `main`）。
- 十個版面：頭版、消息、週期、鏈上、價格、資金、衍生品、出場框架、往期、方法。中英雙語（`_t`／`_T`）、日刊／夜刊兩種主題。
- 每天的流程：
  1. **資料**：`.github/workflows/daily.yml`，每天 UTC 00:05（台北 08:05）起跑；GitHub 自己的排程常延遲，由 cron-job.org 準時呼叫（見 `docs/CRON_JOB.md`）。跑 `pipeline/collect.py` → `pipeline/build.py` → 寫 `data/latest.json`，並提交 `data/`、`pipeline/coc_cache/` 等快取。
  2. **文字日報**：另一個排程（UTC 00:15，台北 08:15；2026-11-06 起，原本 00:30）照 `docs/CLAUDE_DAILY.md` 寫 `notes.json`、`notes.en.json`、`x_post.json`。
- 主要檔案：
  - `pipeline/collect.py`：所有 API 抓取與計算（區塊用 `# G4d.`、`# G9b.` 這類標籤分段）。
  - `pipeline/build.py`：整理成網站用的 `data/latest.json`；`pipeline/brief.py`：給日報的精簡版。
  - `pipeline/bitview.py`（Bitview 鏈上資料＋快取）、`pipeline/stage_viz.py`（各圖的資料）、`pipeline/hl_whales.py`（Hyperliquid）、`pipeline/liq_heat.py`（清算熱力圖）。
  - `assets/app.js`（全部頁面與圖，自己寫的 SVG 圖表：`lineChart`、`twoPane`、`panel`、`interpHtml`、`legend`）、`assets/app.css`。
  - 文件：`docs/CLAUDE_DAILY.md`（日報寫法與資料欄位）、`docs/chart-style.md`（圖表風格與配色）、`docs/indicator-ideas.md`（運營記的指標點子）、`README.md`（變更紀錄、資料來源）。

## 2. 工作規矩（使用者定的，必須遵守）

- **一律用繁體中文回覆。**
- **產品內不出現任何人名**（例如分析師名字）；圖和讀值只寫指標本身。
- **隱私**：任何檔案都不得出現任何人的實際持倉數量、以顆數表示的個人買賣數量、資金或生活開支。Hyperliquid 只給彙總，且同一組要 ≥ 5 個帳戶、最大一個不超過一半才給數量。
- **讀值＋觀點**：2026-11-05 起使用者要求「不只說數據，要基於數據給出具體觀點」。面板讀值的第一列「我們的看法」寫傾向、理由、會改變看法的條件（`assets/app.js` 的 `viewRow`；2026-11-06 起排第一列，頭版的「我們的看法」總表由 `VIEWS` 彙整，新增看法時兩邊都要接）。仍然不寫目標價、不標買賣區、不連動倉位；樣本少就照實寫樣本數。
- **配色**（`docs/chart-style.md`）：主色按指標類型——成本與價位＝橙 `--s2`、獲利與情緒＝紫 `--s1`、籌碼與供給＝青綠 `--s3`、資金與衍生品＝金 `--s4`；綠紅只給有方向的意思；週期階段用 `--stg0`–`--stg4`（冷→熱）。圖例顏色要和線一致（今天抓到兩處不一致才修）。
- **每個指標只有一個家**：改既有面板，不重複做一張。
- **版面**（2026-11-06 整理）：鏈上版分四組、週期版分三組，用 `grpH()` 加組名（版內目錄自動分組）；新面板放進對的組。圖表面板裡，細項讀值超過 3 列會自動收進「更多讀值」、圖後面的表格自動收成「展開表格」、長說明只露兩行（`interpHtml`、`tidyPanel`），不用手動收。
- **省 bitcoin-data 免費額度**（每天約 10 次）：不要為了測試重跑整條管線；新欄位用一次性補值寫進 `data/latest.json`，隔天自動更新再正式算。
- **流程**：改完 → 檢查 → 開 PR → 等「Site checks」通過 → 用完整 head SHA 合併 → 等 Pages 部署 → 到線上再檢查一次。使用者說「上線／推上去」就是這整套。
- 提交訊息結尾兩行（照 session 給的格式）；不要在提交、PR 裡寫模型名稱。

## 3. 改完要跑的檢查

```bash
python3 pipeline/stamp_assets.py          # 改了 assets 一定要跑（換快取版本號）
python3 pipeline/check_i18n.py            # 「不在翻譯函式裡的中文字串」必須是 0
python3 -m http.server 8765 &             # 本機預覽
BASE=http://localhost:8765/ node tests/smoke.js        # 中英 × 1280／390，十個版面 0 錯誤
BASE=https://north7.github.io/daybreak/ node tests/smoke.js   # 上線後再跑一次
```

- Playwright 與 Chromium 已裝好（`require('playwright')`）；截圖看圖再交差，日刊、夜刊、手機（390px）都要看。
- 管線改動：把新區塊單獨拿出來跑（用快取資料），不要整條重跑。

## 4. 2026-11-05 上線的變更（PR #31–#38）

| 項目 | 在哪 | 資料／欄位 |
|---|---|---|
| 全站圖表升級：圖區頂端漸層條、圖底光暈、彩色線發光（淺色底較淡）、最新一點心跳（只在畫面內、捲動時暫停、空心圈不跳） | 全站 | `app.css` 末段、`app.js` 的 `animateLines`、`pulseIO` |
| 主色按指標類型分 | 全站 | 見 `docs/chart-style.md` |
| 週線多空分數五段上色（極熊／熊／初牛／牛／過熱），面板寫目前階段 | 週期版 | `regStages()`；門檻 ±4、初牛＝熊市滿 26 週後轉正的頭 26 週 |
| 冪律圖「通道位置」（0%＝歷次底部連線、100%＝逐輪下降的頂部連線） | 週期版 | `plChan()`（前端算） |
| 長期持有者虧損比例線尾改成當天值 | 鏈上版 | `stage_viz.lthloss_viz` |
| Coinbase 溢價改版：每日柱＋7 日平均、上格價格、4 年歷史、打開網頁時的即時值（瀏覽器直接向 Coinbase、Binance 取） | 資金版 | `flows.cb_premium`（rows 第三欄是 Coinbase 收盤） |
| 清算熱力圖加 Hyperliquid：掃前 2,000 名，同一個 1,000 美元價位 ≥ 5 帳戶且最大一個 ≤ 一半才在右緣畫白條（目前沒有聚集，所以沒畫） | 衍生品版 | `deriv.hl_whales.bands` |
| 「籌碼結構與集中度」：上格價格＋右緣長短期持有者籌碼分布，中格集中度（改用 Bitview，2018 起），下格本站自製「短期壓力分數」 | 衍生品版 | `chips.conc_hist`、`chips.conc_stats`、`chips.stress`；快取 `pipeline/coc_cache/conc.json` |
| 修：圖例顏色對不上（RV30、籌碼集中度）、讀值太長壓到標籤、手機收起來的小圖只剩最後一點 | — | — |

## 5. 待辦（照優先順序）

1. **確認 2026-11-06 的第一次完整每日更新**（最重要）。今天新加的四塊管線（Bitview 集中度、短期壓力分數、Hyperliquid 2,000 名、Coinbase 溢價 4 年）都只單獨跑過，明天是第一次在完整流程裡跑。檢查方法：
   - `data/latest.json` 的 `meta.errors` 有沒有 `conc bitview`、`bitview stress`、`hl_whales`、`cb_premium` 開頭的錯誤。
   - `meta.bar_date` 是 2026-11-05；`chips.flow.conc5.src` 是 `Bitview`；`chips.stress.date`、`deriv.hl_whales.scanned`（約 2,000）、`flows.cb_premium.since`（約 2022-09）都有值。
   - `pipeline/coc_cache/bitview.json` 的 `cols` 多了 `ssopr`；`pipeline/coc_cache/conc.json` 多了 11/05 一列。
   - 每日工作的時間限制是 15 分鐘，原本約 3.4 分鐘，Hyperliquid 掃描加約 2 分鐘。
2. **短期持有者成本帶加 ±0.5 標準差兩條細線**（運營記在 `docs/indicator-ideas.md`「已有、可以改進」）：鏈上版成本帶 `sth_bands_viz`／`SB_K`，工作量小。
3. **點子清單「待評估」**：Ahr999、DeFi 借貸流動性、ETF 發行商鏈上轉帳、Active Realized Price、BTC 主導率。之前看過，優先度都偏低。
4. **選做**：個別圖表再加大字讀數卡、峰值標籤（規則見 `docs/chart-style.md`）。

## 5b. 2026-11-06 指標擴充（`oc_extra.py`、`opt_flow.py`）

- 參考資料是付費內容，**只存在本機** `.claude/research/subs/`（git 不追蹤）：`index.json`、`catalogue_group1-4.md`（逐張圖的說明）、`img/`。公開 repo、網站、PR、commit 都不能出現參考資料的原文、原圖或出處的人名。
- 網站上只放用本站資料重做的版本：鏈上版（回調壓力清單、供給分位成本線、實現虧損峰值背離、鏈上勢能、長短期供給比 30 日變化、資金與價格增量梯度；籌碼分布加雙錨與缺口；短期持有者獲利比例加虧損比例的歷次）、週期版（相對未實現獲利的地板）、衍生品版（Gamma 曝險推算、買方權利金差、OKX 現貨主動買賣差）。每項都附回測，沒有優勢的照寫（例如回調壓力清單、短期持有者虧損 > 60%）。
- 做不到：BRS、BSS（Glassnode 付費 ML 模型）；交易所流量依轉帳金額分層、實體調整的指標（要付費的實體標籤）；他的 TradingView 付費腳本。
- `coc_cache/deribit_flow.json`：Deribit 選擇權逐筆成交的每日權利金與每個未到期合約的主動方向淨量（Gamma 曝險的做市商方向靠它）。第一次在本機回補了一年（約 4,400 頁、45 分鐘）；每日管線只補前一天（約 12 頁）。**快取不見時每日管線只補 3 天**，Gamma 曝險的覆蓋率會很低，要在本機重跑 `python3 -c "import opt_flow as F; F.update_trades(backfill_days=366, max_pages=7000)"`（在 pipeline/ 底下）再提交。
- `coc_cache/okx_taker.json`：OKX 日線（UTC+8 日界）會一直累積，API 本身只給 180 天。
- **Bitview 依賴變大**（2026-11-06）：鏈上與週期版約 20 張圖靠 Bitview（`bitview.py` 每天約 110 次請求、全表約 70 秒，含 `bv_extra.py` 六項）。Bitview 失敗時用 `coc_cache/bitview.json` 快取，超過 4 天就顯示「本日未取得」，會一次空掉很多張；若常失敗，考慮把部分序列改回 CheckOnChain 或分兩批抓。

## 5c. 2026-11-06 指標擴充再六項（`cq_extra.py`）

- 資料：CoinMetrics 社群版同一次請求加抓 `FlowInExNtv`／`FlowOutExNtv`；The Block 各檔 ETF 流量（`etf.py` 之外再抓一次同一份 JSON）；Upbit KRW-BTC 日線（每天約 16 次，200 天一頁回到 2017）；Frankfurter 歐洲央行匯率（失敗改 FRED `DEXKOUS`，本機常逾時）；OKX 合約主動買賣在 `opt_flow.okx_update` 同一次更新，存在 `okx_taker.json` 的 `perp`（API 只給 180 天，從 2026-05-11 起累積）。
- ETF 持有者成本是推算（不含 GBTC、平均成本法、用收盤價），和看託管地址收幣時間的鏈上做法會有差距；引用時寫「推算」。ETF 流量晚一天公布，所以成本日期常比價格早一天（`date` 對 `px_date`）。
- 交易所淨流量的回測和任一天差不多，不要寫成買賣訊號；韓國溢價衝上 5% 之後 90 天偏弱（4/10 次上漲），樣本只有 10 次。
- 每輪資金效率的底部、頂部日期取自 `data/model.json`（`cycle_bottoms`／`cycle_tops`），模型改了表會跟著變；2011 那輪的底部是 2011-06 到 2012-06 的最低收盤。
- `oxPane` 新選項：`plines`（畫在價格格的線，如 ETF 成本）、`fit`（縱軸只看目前選的時間範圍）、`tfmt(v, row)` 第二個參數是整列資料。

## 6. 容易踩的坑

- **頂部一輪比一輪低的指標，不要用全部歷史的百分位或固定門檻**（2026-11-06 使用者：「看起來儲備風險的峰值在逐漸降低中」）：儲備風險、賣方風險比、AVIV、長期持有者 NUPL、相對未實現獲利、MVRV 都是這樣，全部歷史的最低 10% 會偏向近年（儲備風險 2018 年底的底部沒進去、回測 7 次有 4 次在 2022 年後）。`bv_extra._roll` 給近 4 年滾動百分位，低檔區用它判定；引用百分位時寫明是近 4 年還是全部歷史。

- **集中度在 11/05 換算法**：Bitview 的值比舊的 CheckOnChain 算法高約 1–3 個百分點（11/04：18.25% 對 15.29%，舊值留在 `pct_checkonchain`）。跨 11/05 比較時不要把差距當成市場變化。
- **短期壓力分數不是 BRS**：BRS 是 Glassnode 付費、算法不公開的指標。本站分數照 BRS 用法回測 2018–22 年 7 次只有 1 次獲利，只看相對高低，不能寫成 BRS 或買賣訊號。
- **Coinbase 溢價**：「收斂回 0 以上」沒有額外資訊（5 次 3 次漲，和隨便一天差不多）；網站上的「即時」值是讀者瀏覽器自己抓的，日報不引用。
- **Hyperliquid 白條沒出現是正常的**：代表沒有聚集；不要為了畫出來放寬格子或門檻（放寬到 2,000／5,000 美元時，唯一夠 5 個帳戶的格子最大一個佔 57–58%，等於公開個人部位）。
- **畫在隱藏元素裡的圖**：`animateLines` 現在遇到藏著的圖會跳過動畫；新加的折疊區塊也要確認展開前後都畫得出來。
- **`git` 指令裡用 heredoc 寫檔有時會被安全檢查擋下**（誤判成刪除）：改用寫檔工具建檔再執行。
- **網站打不開**：先查 githubstatus.com（11/04 有一次 GitHub Pages 事故），再用 Playwright 載入線上版看錯誤；11/05 使用者回報時線上其實正常。
- **運營 session 跑在使用者電腦上**，雲端 session 看不到它，它也找不到雲端 session；要直接互傳訊息，那台電腦要開 Remote Control。在那之前由使用者轉貼。
