# 新版首頁（2026-11-11 上線）

網站首頁 `index.html` 從這裡產生。舊版首頁搬到 `classic.html`，還在線上、每天照常更新；舊版的網址（`/#onchain/sthsig` 這種）會自動轉過去。

## 怎麼產生

```
python3 pipeline/next/build.py            # 完整：先抽舊版的白話讀值，再組資料
python3 pipeline/next/build.py --no-interp # 只改版面時：沿用上一次的讀值，不開 Chrome
```

1. `extract_interp.py`：用無頭 Chrome 開 `classic.html`，把每個面板的白話讀值抽成 `interp.zh.json`／`interp.en.json`（新版每張圖的「結論」從這裡來）。失敗就沿用上一次提交的檔案。
2. `build.py` 讀 `data/latest.json`、`data/notes.json`、`data/notes.en.json`，交給 `site_data.py` 和各頁的 `*_data.py`（今天、週期、價位、賣壓、買盤、槓桿、出場），`say_data.py` 把讀值接到每張圖。
3. 寫出 `data/next.js`（`window.DAYBREAK_NEXT` = 整包資料，約 2.3 MB）和根目錄的 `index.html`（＝`page.html`，只換 `data/next.js?v=` 的版本號）。

## 什麼時候會重建

- 每日資料流程 `daily.yml`：資料更新後跑一次（這時日報還沒寫，頭條是前一天的）。
- 日報推送 `notes*.json` 後，`share.yml` 再跑一次，換成當天的頭條和導言。
- 改了這個資料夾的東西、推到 main 時，`share.yml` 也會跑。

## 改版面

直接改 `page.html`（樣式和程式都在裡面），然後 `python3 pipeline/next/build.py --no-interp`，再跑 `node tests/smoke_next.js`。
`page.html` 是 2026-11-11 從設計提案（第 63 版）轉過來的；提案期間的設計規則、色彩來源寫在 `page.html` 樣式開頭的註解（①–⑭）。

## 注意

- 這裡的 `site_data.py` 和 `pipeline/site_data.py` 同名但無關；`build.py` 會先找這個資料夾裡的模組。
- 數字格式只能用 `page.html` 裡 `FM` 有定義的（例如 `n1`、`n3`、`pct1`；沒有 `n2`），寫錯會整頁報錯。
- 每日推薦圖表（`pipeline/picks.py`）和回覆卡片用 `ops/post/site_shot.py` 截舊版 `classic.html` 的面板。長文配圖從 2026-11-11 起改用 `ops/post/next_shot.py` 截這裡的新版卡片。
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

網址加 `?share`（16:9）或 `?share=45`（4:5），再加 `&k=圖代號` 就直接打開那張圖的放大檢視，例如 `index.html?share&k=oih`。分享模式會：
- 字級放大 1.3 倍，圖上的刻度、標註一起放大
- 藏掉按鈕、放大檢視上面的導覽列、下面那排同段的圖、「我們的看法」
- 每張卡片底下加一行：網站名、網址、資料來源、資料日期
- 把放大檢視固定成 16:9 或 4:5，關掉所有動畫

規則寫在 `page.html` 樣式的 ⑮。

訪客用的入口：每張圖的放大檢視右上有「複製連結」（複製上面這個分享網址）和「下載圖片」（在看不見的框裡開分享模式 1600×900，用 html-to-image 轉成 3200×1800 的 PNG；手機能用系統分享就跳分享）。程式在 `page.html` 的 `copyLink`、`savePng`。
