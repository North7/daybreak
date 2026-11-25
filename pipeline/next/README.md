# 新版首頁（2026-11-11 上線）

網站的數據頁 `app/index.html`（網址 /app/）從這裡產生；2026-11-20 起根目錄的 `index.html` 是介紹頁（`pipeline/intro/`），舊連結和來過的人會由它轉到 /app/。舊版首頁 `classic.html` 2026-11-16 起不再部署，2026-11-17 從倉庫刪除（連同 `assets/app.js`、`app.css`、`i18n-en.js`、`data/site.json`）；舊版的網址（`/#onchain/sthsig` 這種）由首頁轉到新版對應的圖（`D.old`，規則 ㉝）。

## 怎麼產生

```
python3 pipeline/next/build.py
```

1. `build.py` 讀 `data/latest.json`、`data/notes.json`、`data/notes.en.json`，交給 `site_data.py` 和各頁的 `*_data.py`（今天、週期、價位、賣壓、買盤、槓桿、出場）。
2. 讀數：`reads.py` 加上各頁的 `reads_buy.py`、`reads_cycle.py`、`reads_sell.py`、`reads_lv.py`、`reads_lev.py`（一句結論＋最多三條事實；「怎麼讀」凍結在 `how.json`，舊版沒有的在各模組的 `HOWX`）。`say_data.py` 掛當天的異動訊號（`sigmap.json`：訊號的舊圖 id → 新版代號）和資料來源（`src_lab.py`＋`src.json`，日期每天換成資料日）。舊網址對照在 `old.json`。這三個 JSON 是 2026-11-17 刪舊版前凍結的。
3. 寫出 `data/next.js`（`window.DAYBREAK_NEXT` = 整包資料，約 2.3 MB）和 `app/index.html`（＝`page.html`，只換 `../data/next.js?v=` 的版本號）。

## 什麼時候會重建

- 每日資料流程 `daily.yml`：資料更新後跑一次（這時日報還沒寫，頭條是前一天的）。
- 日報推送 `notes*.json` 後，`share.yml` 再跑一次，換成當天的頭條和導言。
- 改了這個資料夾的東西、推到 main 時，`share.yml` 也會跑。

## 改版面

直接改 `page.html`（樣式和程式都在裡面），然後 `python3 pipeline/next/build.py --no-interp`，再跑 `node tests/smoke_next.js`。
`page.html` 是 2026-11-11 從設計提案（第 63 版）轉過來的；提案期間的設計規則、色彩來源寫在 `page.html` 樣式開頭的註解（①–⑭）。

### 「AI 把頁面畫出來」的進場效果（規則 ⑲，2026-11-11 改版）

五個 AI（排版、文案、數據、圖表、校對）的游標把卡片一張張畫出來。2026-11-11 使用者嫌原本彩度太高、黑底刺眼、右下的膠囊在手機上太佔位，改成：
- 顏色：五個 AI 都是次要文字色 `--k2` 混 14% 系列色，幾乎同一個灰，只留很淡的色相差別（`.oc` 上的 `--ag-lay`／`--ag-txt`／`--ag-num`／`--ag-cht`／`--ag-chk`）。不用綠、紅（只給漲跌）。
- 線一律 1px 實線、低不透明度，沒有填色塊、陰影、光暈、彈跳；游標的名字和標籤是 10px 小字。
- 手機（≤700px）每張卡只留外框、一個游標、打字游標和上色。
- 右下的狀態膠囊（`.ag-dock`）只剩五個小點加一行小字（手機只有小點）；畫的時候小點慢慢亮暗（`agBusy`），畫完 2.4 秒收起成小點，有訊號留數字（點一下到下一張訊號卡），沒訊號就淡出。
- 訊號卡是靜止的 1px 細框，圖釘 22px、不脈動。
- `.oc` 水平裁切（`overflow-x: clip`），游標從畫面外飛進來時頁面不會被撐寬。
- 畫過的卡片不重畫（⑱）、`prefers-reduced-motion` 和分享模式不跑，都照舊。完整規則在 `page.html` 的 ⑲ 註解。

### 手機左右滑（規則 ㉒，2026-11-11）

觸控單指橫滑（橫向 ≥ 64px、是直向的 2 倍以上、0.7 秒內放開）：頁面上換到下一頁／上一頁（`navCh`，和點分頁同一個動作），放大檢視裡換同一段的下一張／上一張（`fxGo`，和點下面的小圖同一個動作），兩頭不繞回去。不搶別人的手勢：手指落在 `.ol-c`（圖，左右是十字線）、`.or`、能左右捲的區塊、輸入框和滑桿、`touch-action` 不是 `auto` 的元件、找圖，或螢幕邊緣 24px 內，都不觸發。新加會左右拖的元件時，給它 `touch-action`（或讓它能左右捲）就會自動被排除。完整規則在 `page.html` 程式裡的 ㉒ 註解。

### 圖示（規則 ㉑，2026-11-11）

一套畫法：16×16 格、1.5 線寬、圓頭、只有線、顏色跟旁邊的字。路徑都在 `page.html` 的 `ICP`；`IC(名)` 是按鈕裡的 16px 圖示，`ICS(名)` 是跟字一起排的小圖示。
- 七頁各有一個圖示，代號就是頁的 id（`today`、`cycle`、`lv`、`sell`、`buy`、`lev`、`exit`）。只用在手機底部分頁、「今天」頁六個問題卡片的標題前、找圖的分區標題前；桌機頂部導覽維持純文字。新增一頁時要在 `ICP` 補同名的路徑，不補就只有字。
- 清單列（`list.rows`）的 `ic` 是狀態標籤前的圖示代號，`io=1` 是只顯示圖示（字留給讀屏）。`today_data.py` 的 `AK`／`IM`／`LN`／`SN` 第四個值就是它；新的狀態詞要一起給圖示代號，沒給就只有字。
- 手機（≤700px）圖名旁的資料來源文字換成圖示鈕（`.src-b`），點了用提示條顯示；桌機和分享模式照舊顯示文字。
- 不換成圖示的：區間按鈕、語言切換、圖例、「讀數」「異動」這類小標。完整規則在 `page.html` 的 ㉑ 註解。

### 中文版圖名附英文名（規則 ⑳，2026-11-11）

中文版每張圖的圖名下面有一行英文名（`.ol-e`），就是這張圖資料裡的 `en`；英文版不變。由 `page.html` 的 `enName(c)` 決定要不要加：中英文同名的不加、代號是 `q_`／`t_`／`x_` 開頭的（「今天」頁文字卡片、出場規則卡片）不加、英文尾巴的括號中文名已經有了（URPD）就拿掉。段落標題、頁名、清單、地圖小格、內文都維持中文。新加的圖只要照常填 `zh`／`en` 就會有。

### 簡體中文（2026-11-25）

右上角語言切換是三段「繁／简／EN」（`#oc-lg`，介紹頁是 `#lgs`，同一顆滑塊、同一個點字動畫）。簡體不是另一份文案：
- 頁面照繁體畫（`lang` 仍是 `'zh'`，另有 `hz`），選了简就載入 `assets/hans.js`（約 46 KB，gzip 27 KB），在瀏覽器裡把畫面上的字、title／aria-label 這類屬性、canvas 上畫的字轉成簡體，之後新畫上去的也轉（MutationObserver）；切回繁體或英文時換回原本的字。中文字型換成 Noto Sans SC（把它的字型檔登記成「Noto Sans TC」，CSS 不用改）。
- 轉法是 OpenCC 的 tw2sp（台灣正體 → 大陸簡體，含用詞），再套 `hans.py` 的金融用詞表 `TERMS`（聯準會→美联储……）。OpenCC 的台灣→大陸用詞表是給電腦軟體用的，`hans.py` 的 `DROP`／`TWO` 把在這裡意思不同的詞拿掉或改掉（「價格線上」不能變「价格在线」、「指標」不能變「指针」）。`assets/hans.js` 的演算法逐行照 Python 版移植，結果和部署時產生的簡體單頁一字不差。
- 改了 `hans.py`（TERMS、DROP、TWO）或 `hans_rt.js` 要重產：`python3 pipeline/next/hans.py --js`，再跑 `build.py`（兩頁的 `hans.js?v=` 由 build 換成檔案的雜湊）。檢查流程會重產一次，和提交的不一樣就擋下來。`python3 pipeline/next/hans.py --check` 列出網站上用到的台灣用語各轉成什麼。
- 網址：`?lang=hans`（也收 `zh-hans`、`zh-cn`、`sc`），和 `?lang=zh／en` 一樣只管這一次；選過的記在 `daybreak.lang = 'hans'`。沒選過時，瀏覽器是 zh-CN／zh-SG／zh-Hans 的人預設簡體。
- 給搜尋引擎的靜態頁（`pages.py`，部署時寫）：每張圖、索引、每日簡報、主題頁都有 `zh-hans/…` 一份，`zh-hans/feed.xml`、`latest.zh-hans.md`，三個語言互標 hreflang，sitemap 也有。
- 不轉的：`<script>`、`<style>`、輸入框、標了 `data-nohans` 的元素；分享圖（`share_card.py`）、運營截圖（`next_shot.py`）照舊只有繁體和英文。

## 注意

- 這裡的 `site_data.py` 和 `pipeline/site_data.py` 同名但無關；`build.py` 會先找這個資料夾裡的模組。
- 數字格式只能用 `page.html` 裡 `FM` 有定義的（例如 `n1`、`n3`、`pct1`；沒有 `n2`），寫錯會整頁報錯。
- 每日推薦圖表（`pipeline/picks.py`）、回覆卡片、長文配圖都用 `ops/post/next_shot.py` 截這裡的新版卡片（`site_shot.py` 只剩共用的開瀏覽器、截圖流程）。
- `next_shot.py` 靠下面這些掛點找卡片。改名或拿掉的話，它會報 ERROR、結束碼 1：
  - `data/next.js`：`site.chapters[].groups[].charts[]` 的 `k`、`id`、`zh`／`en`、`nofx`、`na`
  - 分頁：`#oc-crumb button[data-ch="N"]`
  - 卡片：`#oc-ol<組>_<序>`（組從 1、序從 0）、外框 `.fc`、標題 `h4`
  - 放大檢視：卡片裡的 `[data-fx]`、`#oc-fx.on`、`#oc-olF`、`#oc-orF`、`.fx-x`
  - 卡片內：`.ol-ctl button[data-rg|data-m|data-ly]`、`.ol-say`、`.sy-m`、`.ol-how`、`.fx-b`、`.ol-f`、`.ol-c`、`[id^="oc-pr"]`
  - 關動畫靠 `prefers-reduced-motion: reduce` 那一段，語言靠 `localStorage` 的 `daybreak.lang`
  - 2026-11-11 起另有：卡片外框 `.fc[data-k="圖代號"]`、卡片內容 `.ol[data-ck="圖代號"]`（放大檢視的 `#oc-olF` 也有），可以直接用圖代號找，不必比對標題
  - 結論分兩塊：`.sy-read`（讀數）和 `.sy-view`（我們的看法、會改變看法）；社群配圖只要藏 `.sy-view`
  - `window.daybreakXY(圖代號, 日期, 數值, 'p')`：回傳那個日期、數值在視窗裡的座標（CSS px），另附這張圖的時間範圍、縱軸範圍和刻度；`'p'` 是上格的價格
- 改了上面任何一項，先跑 `python3 ops/post/next_shot.py --list` 和一張實際截圖確認。

## 分享模式

網址加 `?share`（16:9）或 `?share=45`（4:5），再加 `&k=圖代號` 就直接打開那張圖的放大檢視，例如 `app/index.html?share&k=oih`。分享模式會：
- 字級放大 1.3 倍，圖上的刻度、標註一起放大
- 藏掉按鈕、放大檢視上面的導覽列、下面那排同段的圖、「我們的看法」
- 每張卡片底下加一行：網站名、網址、資料來源、資料日期
- 把放大檢視固定成 16:9 或 4:5，關掉所有動畫

規則寫在 `page.html` 樣式的 ⑮。

訪客用的入口：每張圖的放大檢視右上有「複製連結」（複製上面這個分享網址）和「下載圖片」（在看不見的框裡開分享模式 1600×900，用 html-to-image 轉成 3200×1800 的 PNG；手機能用系統分享就跳分享）。程式在 `page.html` 的 `copyLink`、`savePng`。
