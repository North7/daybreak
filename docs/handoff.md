# 交接文件（網站與資料管線）

給接手「破曉 Daybreak」網站／管線工作的 Claude session。最後更新：2026-11-05（原 session：claude.ai/code 的「數據分析方案」）。

> **2026-11-11 首頁換成新版**（`pipeline/next/`，說明見 `pipeline/next/README.md`）。舊版首頁搬到 `classic.html`：以下內容講的都是舊版，檔案和流程不變，只是網址從 `index.html` 變成 `classic.html`；舊網址 `/#page/key` 會轉過去。改舊版後的檢查照舊，另外多一支 `node tests/smoke_next.js` 測新版。

## 1. 專案是什麼

- 比特幣每日簡報網站：<https://north7.github.io/daybreak/>（GitHub Pages，repo `North7/daybreak`，分支 `main`）。
- 十個版面：頭版、消息、週期、鏈上、價格、資金、衍生品、出場框架、往期、方法。中英雙語（`_t`／`_T`）、日刊／夜刊兩種主題。
  - 日刊／夜刊切換（2026-11-09）：「晨昏線」——新的一刊從切換鈕往外漫開，交界一圈暮色光帶，地平線日月圖示跟著變，程式在 `assets/app.js` 的 `ttGo`／`ttBand`／`ttKnob`／`ttDone`。用瀏覽器的 View Transition：舊版面是靜態快照、新版面是即時畫面，換刊（整頁重算）在動畫開始前做完，動畫只動 `::view-transition-new(root)` 的圓形裁切、`::view-transition-old(root)` 的濾鏡和光帶畫布 `.tt-dusk`（自己的 view-transition-name，所以疊在最上層），這些動畫一律暫停、由程式逐格設 currentTime（所以能拖曳停住）。不要改回逐一改全站顏色變數或整頁濾層＋換刊點暮色（11/09 前兩版，中間會一片灰、換刊點卡一格）；兩端必須等於原本的日刊、夜刊（淺色底色不能變）。拖回原處取消時先把即時畫面換回原刊、隔兩格再結束過渡，避免閃。切換鈕的光圈 `.tt-ring`（`ttRing`／`ttRingRun`，11/09 使用者：只在切換時繞一圈、直接在邊框上、慢一點、要有發光感）沿邊框繞一圈約 1.9 秒，自己計時、換刊結束後繼續繞完；過渡中靠 `html.tt-vt .tt-ring` 的 view-transition-name 疊在光帶上面，新一次換刊前一定先移除舊的（同名會讓 View Transition 失敗）；光暈只用在這顆鈕。換刊後的圖表重畫：看得到的在快照底下同步畫，其餘等過渡結束再分批（`ttCharts`／`ttDrawRest`），不要改回一次重畫全部。
  - 換語言（2026-11-09）：`pickLang` 先存「看得到的畫面」快照（`lfxSnap`）和捲動位置到 `sessionStorage` 的 `daybreak.lfx`，字亂碼 0.3 秒後重新載入；`index.html` 的 body 開頭腳本把 6 份亂碼快照擺進 shadow DOM（`.lfx-ghost`，樣式從已載入的 app.css 逐條抄進去、選擇器的 html／:root／body 換成 `.lfx-html`／`.lfx-body`）、CSS 輪播（不靠 JS，主執行緒忙也會動），資料畫好後 `langIn` 拿掉快照、把新頁面的字從亂碼解碼、接回捲動位置。`html.lfx-came` 讓進場動畫直接到位，4 秒後拿掉。快照放 shadow DOM 是為了不被 `#view .pg` 之類的全頁查詢與 id 抓到（會重複算進搜尋與目錄）；不要改回 iframe：iPhone 的瀏覽器要等主畫面有足夠的字才換掉舊畫面，iframe 裡的字不算，換語言時會顯示被往上推一截的舊畫面約 0.35 秒。快照裡直接含字的區塊鎖住原本高度、英文字母只換同寬度組的字，亂碼不會改變折行把版面推動。開機時看到 `lfx-came` 就只切到網址那一版、不回頂也不對齊（手機版 `go` 會呼叫 `toTop`，它的鎖捲動和 80／250／500 毫秒的回頂檢查會把 `langIn` 接回的位置拉回頂端，畫面會跳）。
- 每天的流程：
  1. **資料**：`.github/workflows/daily.yml`，每天 UTC 00:05（台北 08:05）起跑；GitHub 自己的排程常延遲，由 cron-job.org 準時呼叫（見 `docs/CRON_JOB.md`）。跑 `pipeline/collect.py` → `pipeline/build.py` → 寫 `data/latest.json`，並提交 `data/`、`pipeline/coc_cache/` 等快取。
  2. **文字日報**：另一個排程（UTC 00:15，台北 08:15；2026-11-06 起，原本 00:30）照 `docs/CLAUDE_DAILY.md` 寫 `notes.json`、`notes.en.json`、`x_post.json`。
- 主要檔案：
  - `pipeline/collect.py`：所有 API 抓取與計算（區塊用 `# G4d.`、`# G9b.` 這類標籤分段）。
  - `pipeline/build.py`：整理成完整資料 `data/latest.json`，再由 `pipeline/site_data.py` 產生網站實際讀的 `data/site.json`（內容相同、數字表按欄存放，gzip 約小 30%）；`pipeline/brief.py`：給日報的精簡版。
  - `pipeline/bitview.py`（Bitview 鏈上資料＋快取）、`pipeline/stage_viz.py`（各圖的資料）、`pipeline/hl_whales.py`（Hyperliquid）、`pipeline/liq_heat.py`（清算熱力圖、2 年範圍、每日多空清算量）、`pipeline/coinalyze.py`（Coinalyze 讀取；key 在 GitHub secret `COINALYZE_API_KEY`，本機 `~/.config/daybreak/coinalyze.key`）。
  - `assets/app.js`（全部頁面與圖，自己寫的 SVG 圖表：`lineChart`、`twoPane`、`panel`、`interpHtml`、`legend`）、`assets/app.css`。
  - 文件：`docs/CLAUDE_DAILY.md`（日報寫法與資料欄位）、`docs/chart-style.md`（圖表風格與配色）、`docs/indicator-ideas.md`（運營記的指標點子）、`README.md`（變更紀錄、資料來源）。

## 2. 工作規矩（使用者定的，必須遵守）

- **一律用繁體中文回覆。**
- **產品內不出現任何人名**（例如分析師名字）；圖和讀值只寫指標本身。
- **隱私**：任何檔案都不得出現任何人的實際持倉數量、以顆數表示的個人買賣數量、資金或生活開支。Hyperliquid 只給彙總，且同一組要 ≥ 5 個帳戶、最大一個不超過一半才給數量。
- **讀值＋觀點**：2026-11-05 起使用者要求「不只說數據，要基於數據給出具體觀點」。面板讀值的第一列「我們的看法」寫傾向、理由、會改變看法的條件（`assets/app.js` 的 `viewRow`；2026-11-06 起排第一列，頭版的「我們的看法」總表由 `VIEWS` 彙整，新增看法時兩邊都要接）。仍然不寫目標價、不標買賣區、不連動倉位；樣本少就照實寫樣本數。
- **配色**（`docs/chart-style.md`）：主色按指標類型——成本與價位＝橙 `--s2`、獲利與情緒＝紫 `--s1`、籌碼與供給＝青綠 `--s3`、資金與衍生品＝金 `--s4`；有方向的（正負、多空、流入流出）一律綠＝正、品牌橘紅＝負，文字用 `--down-ink`（2026-11-09 紅綠規則 v2）；分類、週期階段 `--stg0`–`--stg4`、熱力圖的多色保留；不發光、不加圖底光暈和頂端漸層色條。圖例顏色要和線一致（今天抓到兩處不一致才修）。
- **每個指標只有一個家**：改既有面板，不重複做一張。
- **版面**（2026-11-06 整理）：鏈上版分四組、週期版分三組，用 `grpH()` 加組名（版內目錄自動分組）；新面板放進對的組。圖表面板裡，細項讀值超過 3 列會自動收進「更多讀值」、圖後面的表格自動收成「展開表格」、長說明只露兩行（`interpHtml`、`tidyPanel`），不用手動收。
- **省 bitcoin-data 免費額度**（每天約 10 次）：不要為了測試重跑整條管線；新欄位用一次性補值寫進 `data/latest.json`，隔天自動更新再正式算。**改完 `latest.json` 一定要再跑 `python3 pipeline/site_data.py`**：網站讀的是 `data/site.json`，不重產網站還是舊資料（PR 檢查 `site_data.py --check` 會擋）。
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
| 「籌碼結構與集中度」：上格價格＋右緣長短期持有者籌碼分布，中格集中度（改用 Bitview，2018 起）（11/05 的下格「短期壓力分數」已在 11/07 換成獨立的「賣壓累積與動能品質」，見 5d） | 衍生品版 | `chips.conc_hist`、`chips.conc_stats`；快取 `pipeline/coc_cache/conc.json` |
| 修：圖例顏色對不上（RV30、籌碼集中度）、讀值太長壓到標籤、手機收起來的小圖只剩最後一點 | — | — |
| 隱含波動率期限結構（2026-11-08，見 5e） | 衍生品版 | `deriv.ivterm`；快取 `pipeline/coc_cache/iv_term.json` |
| 月度報酬熱力表（2026-11-08，見 5e） | 價格版 | `price.monthly` |
| 內容重組與導覽：三版新分組、四張需求圖與兩張價格類圖搬家、全站搜尋、側欄子目錄、手機目錄鈕（2026-11-08，見 5f） | 全站 | `grpH`、`buildFind`、`buildSubnav`、`grpSpy` |
| 短期持有者供給 90 天變化（2026-11-08） | 鏈上版「長期持有者與大戶」 | `onchain.sthd`（`stage_viz.sthd_viz`，Bitview `sths`；rows 第 3 欄千顆） |
| 短期持有者集中止盈與認賠（2026-11-11，本站自製） | 鏈上版「賣出的人賺還是賠」 | `onchain.sthsig`（`stage_viz.sthsig_viz`，Bitview `ap1`＋`ap2`、`al1`＋`al2` ÷ `sth`×`sths`；5 日指數平均、105 天 z 分數、門檻 2；rows＝[日, 收盤, 止盈強度, −認賠強度]）；異動 `sth_tp`、`sth_cap` |
| 清算熱力圖改 Coinalyze 多家交易所（11 個合約，取不到退回 OKX）＋「2 年」範圍（2026-11-08） | 衍生品版「槓桿與清算」 | `deriv.liq_heat`（`model.src`＝Coinalyze／OKX；`long`＝2 年檔的時間）；`data/liq_long.json`（`liq_heat.build_long`，點了才載入） |
| 晨昏指數（2026-11-08，和週線多空分數並列） | 週期版「現在的階段」、頭版「方向」 | `cycle.dawn`（`pipeline/dawn.py`；rows＝[天數, 熱度, 收盤, 階段 0–4, 方向 ±1]；candles＝月 K [月初天數, 開, 高, 低, 收]（`dawn.fetch_ohlc`，Bitview price_ohlc）；圖是網點上下模式 `drawDawn`（色票 `DW_VIV`、`dwCol`；樣稿與研究在本機 `.claude/research/dawn/`），不用五個階段色；stats＝各階段之後半年、一年；marks＝歷次頂底的熱度） |
| 資金費率歷史、全市場未平倉量、多空帳戶比（2026-11-08，Coinalyze 日線） | 衍生品版「槓桿與清算」 | `deriv.fund_hist`、`deriv.oi_hist`、`deriv.ls_acct`（`pipeline/cz_viz.py`；rows 每 2 天一點） |
| 現貨與永續的主動買賣（多交易所，2026-11-08） | 衍生品版「現貨訂單流」 | `deriv.taker`（`cz_viz.taker`；Binance 現貨走 data-api.binance.vision；30 天加總，和中位數 `med` 比） |
| 每日多空清算量（2026-11-08） | 衍生品版「槓桿與清算」 | `deriv.liq_vol`（`liq_heat.build_vol`；rows＝[天數, 收盤, 空單百萬美元, −多單百萬美元]；2022-10 起；Hyperliquid 沒有、Deribit 停在 2023-10，不計入） |

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

- 資料：CoinMetrics 社群版同一次請求加抓 `FlowInExNtv`／`FlowOutExNtv`；各檔 ETF 流量（2026-11-11 起 CoinMarketCap，`pipeline/etf_src.py`，`etf.py` 和 ETF 持有者成本各抓一次；之前是 The Block，11/09 下架）；Upbit KRW-BTC 日線（每天約 16 次，200 天一頁回到 2017）；Frankfurter 歐洲央行匯率（失敗改 FRED `DEXKOUS`，本機常逾時）；OKX 合約主動買賣在 `opt_flow.okx_update` 同一次更新，存在 `okx_taker.json` 的 `perp`（API 只給 180 天，從 2026-05-11 起累積）。
- ETF 持有者成本是推算（不含 GBTC、平均成本法、用收盤價），和看託管地址收幣時間的鏈上做法會有差距；引用時寫「推算」。ETF 流量晚一天公布，所以成本日期常比價格早一天（`date` 對 `px_date`）。
- 交易所淨流量的回測和任一天差不多，不要寫成買賣訊號；韓國溢價衝上 5% 之後 90 天偏弱（4/10 次上漲），樣本只有 10 次。
- 每輪資金效率的底部、頂部日期取自 `data/model.json`（`cycle_bottoms`／`cycle_tops`），模型改了表會跟著變；2011 那輪的底部是 2011-06 到 2012-06 的最低收盤。
- `oxPane` 新選項：`plines`（畫在價格格的線，如 ETF 成本）、`fit`（縱軸只看目前選的時間範圍）、`tfmt(v, row)` 第二個參數是整列資料。

## 5d. 2026-11-07 賣壓累積與動能品質（`stage_viz.stress_viz`）

- 取代 11/05 的「短期壓力分數」（四項短期持有者指標的百分位）。新的只用每日收盤（統一收盤 PXC，缺的日子用 Bitview 收盤），不打新的 API。
- 動能品質＝Φ(0.7 × 近 21 天日報酬的 t 值)。賣壓累積（2026-11-11 起）＝用短線動能 f 加減：f＝Φ(日報酬的指數加權平均 ÷ 指數加權標準差 × √10)，跨度 10 天；f < 0.45 時每天加 20 ×（0.45 − f）、> 0.45 時減 20 ×（f − 0.45），夾在 0–100，沒有歸零規則。參數常數在 `stage_viz.py` 的 `SX_*`。
- 2026-11-11 英文名定為 Sell Pressure Index（SPI，使用者決定）；`assets/app.js`、`pipeline/next/sell_data.py` 的英文字串都用這個名字。新版首頁中文版圖名下附英文名的規則見 `pipeline/next/README.md`（⑳）。
- 2026-11-11 稍晚再改成平均版（使用者決定）：賣壓累積＝上面那條（慢線）和快線各佔一半（`SX_FW` = 0.5）。快線：u＝「當天對數報酬 ÷ 近 30 天日報酬標準差」的 5 天指數平均；u < 0 時每天加 12 × |u|^0.7、u > 0 時減 14 × u^0.7，夾在 0–100（`SX_F*`）。不直接換成快線，是因為快線在連跌的行情裡太早到 100（2012 年起同一波的進場價在急跌時高出 16–41%）；取平均後到 100 的時間跟慢線走（26 次裡 21 次同一天），100 以下的讀數反應變快。快線比重 25–75% 的進場結果都一樣，不要為了抓幾天內反轉的低點把它調到 100%。歷史讀數全部重算（11/07–11/09：86、91、94 → 87、93、96；11/10 一樣是 100）。
- 2026-11-11 之前賣壓累積用 21 天動能（加 30、減 50、動能 ≥ 0.7 歸零）：反彈時幾乎不回落，11/07 就到 100。使用者決定改成短線動能，歷史讀數全部重算（11/07–11/09：100、100、100 → 86、91、94）。換的理由只有貼近度，底部組合的回測沒有因此變好；門檻或加減比例稍微動一點整條線的高低會差很多，不要隨手調。賣壓有路徑依賴：一定要從 2011 年的資料一路算下來，不能只算最近一段。
- 底部組合＝賣壓 100 且動能 < 0.3，和上一次相隔 60 天以上才算新的一次。回測二十幾次，換收盤價來源（CoinMetrics 對 Bitview）勝率就差 2 次左右；2018–22 與熊市初期多次失靈。引用時寫次數，不要寫成高確定性的買點。
- 動能 > 0.85 且賣壓 0（「強勢動能」）之後 90 天多半繼續漲，不是頂部訊號。
- 欄位：`r`、`s`、`r7`、`s7`、`state`（bottom／near／build／strong／calm）、`rise_from`、`at100`、`ev`（每次底部組合：30／90 天、出場日、報酬、中途最深）、`f30`／`f90`／`base30`／`base90`、`ex`、`era`、`top`、`rows`（[x, 價格, 賣壓, 動能]，近 3 年每天、更早每 3 天一點）。

## 5e. 2026-11-08 隱含波動率期限結構、月度報酬熱力表（`opt_flow.term_viz`、`stage_viz.monthly_viz`）

- 來源是 Grok 整理的「網站還沒有的圖」提案，挑了兩張資料現成的。其他提案的評估：兩年均線倍數「頂部在 5 倍線」不成立（2021/11 是 2.6 倍、2025/10 是 1.6 倍）；未平倉 ÷ 市值、各交易所主動買賣比要 Binance／Bybit 衍生品資料，GitHub 的美國機器通常連不到（可以試 data.binance.vision 的每日檔）；CFTC 槓桿基金部位（publicreporting.cftc.gov，CME 代碼 133741）免費、本機測過可用，還沒做。
- 期限結構：Deribit 選擇權 book summary 的 `mark_iv` 與 `underlying_price`，每個到期日取遠期價兩側最近的價外履約價、依 ln(K/F) 內插出價平 IV；固定期限用總變異數內插、不外插（比最近到期還短時最多差一倍用最近那個）。排除 3 天內到期：週六快照時 2–3 天後到期的只有 32–35%，其他都在 37–40%。
- Deribit 沒有免費的歷史曲線（`get_mark_price_history` 只有 DVOL 用的那幾個合約），所以每天快照一次存進 `pipeline/coc_cache/iv_term.json`（每天一行，留 500 天），鍵是 bar date、`ts` 是實際快照時間。第一條（11/06）是 11/07 16:32 UTC 補拍的。`prev7`／`prev30` 找差 2 天內的那一條；`rows` 滿 30 條才畫斜率走勢（`#c-ivts`）。逐筆成交（history API）的 IV 推算遠月樣本太少（2 小時內遠月只有個位數筆），沒有拿來回補。
- 月度報酬：統一收盤 PXC（Kraken 優先、更早 CoinMetrics），2013 年起；`rows` 是 [年, 12 個月, 全年]，`stats` 是各月 n／up／med／best／worst（不含本月），`cur` 是本月的統計加最好、最差的年份。
- 欄位：`deriv.ivterm` 的 `curve`（[到期天數, IV]）、`t`（7／30／90／180 天）、`slope`（7 天 − 90 天）、`state`（inv／flat／norm，±1 點）、`prev7`、`prev30`、`rows`（[x, 價格, 斜率, 7 天, 90 天]）、`n`、`since`；`price.monthly` 的 `mtd`、`ytd`、`base`（上月底收盤）、`cur`、`rows`、`stats`、`ystat`。

## 5f. 2026-11-08 內容重組與導覽（`grpH`、`buildFind`、`buildSubnav`、`grpSpy`）

- 使用者要求「重新設計內容結構、分割、佈局，更易讀、易定位、易查找，交互更好」。全站約 95 個面板、70 多張圖，鏈上版一版就 29 個。
- **分組**：價格（`mk-leg`／`mk-ma`／`mk-long`）、資金（`fl-etf`／`fl-buy`／`fl-dmd`／`fl-liq`）、衍生品（`dv-vol`／`dv-lev`／`dv-opt`／`dv-spot`）新增分組；鏈上改成 `oc-cost`／`oc-pnl`／`oc-sell`／`oc-lth`／`oc-all`。組標題用 `grpH(代號, 中文, 英文, 一句問題)`，圖數由 `grpCounts()` 在建目錄時補上。新圖放進最貼近的一組；一組太長（7 張以上）再拆。
- **搬家**：`concPanel`（衍生品 → 鏈上成本與位置）、`sxPanel`（衍生品 → 價格這一段行情）、`adPanel`／`dmdPanel`／`cfPanel`／`grPanel`（鏈上 → 資金鏈上需求）。**搬面板一定連 `mount` 一起搬到新版面的 `.after()`**：手機只畫目前這一版，`mount` 留在舊版面的話，新版面的圖會是空的。`picks.py` 的鍵（`deriv/sx`、`onchain/ad` 等）沒改：截圖用桌面寬度、所有版面都畫，選擇器找得到；舊網址由 `jumpTo` 跟著圖走。
- **搜尋**：`buildFind()` 從 DOM 建索引（版面、組、頭版大標、面板），別名在 `FKW`（[中文, 英文]，才過得了 `check_i18n.py`；不要放付費指標的名字），`TERMS` 的詞也併進去；面板的「現在」讀值用 `RD[圖].now()`。快捷鍵 ⌘K／Ctrl+K／「/」；結果用 `go('版面/代號')` 跳。
- **定位**：`anchorEl` 也找 `#grp-代號` 與任何 id，所以 `#deriv/dv-opt` 這種組網址能用；組標題用 `toHead()` 對齊頂部列下緣。`grpSpy()` 在捲動時更新頂部小標、側欄子目錄的 `.on`、手機「目錄」鈕的文字。
- **修**：`toTop()` 在 500ms 的最後一次回頂檢查會蓋掉 `jumpTo` 在 350ms 的捲動，手機上跳圖一直停在版面頂端；加 `jumping` 計數，跳轉期間不回頂。同一版裡跳不再先回版面頂端。`toTop` 解除捲動鎖除了 requestAnimationFrame 也加計時器（背景分頁不跑 rAF）。

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
