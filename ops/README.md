# 破曉運營 · Daybreak Ops

網站本身（`index.html`、`pipeline/`、`data/`）負責「產出簡報」；`ops/` 放把簡報推出去用的小工具和手機頁面。

> 這個資料夾在 GitHub Pages 上也會被公開，頁面都加了 `noindex`。運營的策略文件 2026-11-08 起搬到私人倉庫（不公開）。在本機跑的工具會自己找到它，找不到時會說怎麼設定。

## 結構

```
ops/
  post/       X 發文小幫手 index.html（https://north7.github.io/daybreak/ops/post/）、快訊與長貼文配圖、網站截圖
  replies/    回覆小幫手 index.html（https://north7.github.io/daybreak/ops/replies/）、讀貼文與配圖工具、check.py
  picks/      每日推薦圖表的說明（程式在 pipeline/picks.py，圖在 data/picks/）
  video/      短影片腳本（輸出放 video/out/，不進 git）
  articles/   長文草稿與配圖
  log/        log.py（成效紀錄工具）
  opsprivate.py  工具找私人倉庫位置用（環境變數 DAYBREAK_OPS_PRIVATE，或公開倉庫旁邊的資料夾）
```
