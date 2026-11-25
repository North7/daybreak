# ops/replies

運營的策略文件 2026-11-08 起搬到私人倉庫（不公開）。在本機跑的工具會自己找到它，找不到時會說怎麼設定。

這裡留下的是工具和手機用的回覆小幫手：

- `index.html`：回覆小幫手，讀 `data/replies.json` 與 `data/replies/<n>.png`。2026-11-25 起線上版從 `/ops-live/` 即時讀 GitHub 上 main 的最新版（`functions/ops-live/`），推送回覆、長文不再觸發整站部署；推上去就讀得到（沒設 `GH_READ_TOKEN` 時 GitHub 會快取最多 5 分鐘）
- `fetch.py`、`scan.py`、`mentions.py`：讀 X 公開貼文（api.fxtwitter.com）
- `cards.py`、`site_cards.py`：回覆配圖
- `check.py`：檢查 `data/replies.json`、`data/flash.json`
