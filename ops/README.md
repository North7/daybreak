# 破曉運營 · Daybreak Ops

網站本身（`index.html`、`pipeline/`、`data/`）負責「產出簡報」；`ops/` 放把簡報推出去用的小工具和手機頁面。

> 這個資料夾在 GitHub Pages 上也會被公開，頁面都加了 `noindex`。運營的策略文件 2026-11-08 起搬到私人倉庫（不公開）。在本機跑的工具會自己找到它，找不到時會說怎麼設定。

> **2026-11-17 舊版網站（`classic.html`）從倉庫刪除**：截圖、推薦圖表、回覆卡片、標註都截新版卡片（`ops/post/next_shot.py`，圖代號用 `--list` 查）；舊的面板代號（`#c-sthband` 這種）由 `data/next.js` 的 `old` 對照表自動換成新版代號。貼文裡的 `https://daybreak.aronlab.dev/#page/key` 舊連結會轉到新版對應的圖。

## 結構

```
ops/
  app/        破曉運營台（2026-11-08 起發文、回覆合成一個工具）：app.js、app.css、shell.html（兩頁的範本）；post/ 預設「今天發文」、replies/ 預設「回覆」
  post/       X 發文小幫手 index.html（https://daybreak.aronlab.dev/ops/post/）、快訊與長貼文配圖、網站截圖
  replies/    回覆小幫手 index.html（https://daybreak.aronlab.dev/ops/replies/）、讀貼文與配圖工具、check.py
  picks/      每日推薦圖表的說明（程式在 pipeline/picks.py，圖在 data/picks/）
  video/      短影片腳本（輸出放 video/out/，不進 git）
  articles/   長文草稿與配圖
  log/        log.py（成效紀錄工具）
  opsprivate.py  工具找私人倉庫位置用（環境變數 DAYBREAK_OPS_PRIVATE，或公開倉庫旁邊的資料夾）
```
