# ops/replies

運營的策略文件 2026-11-08 起搬到私人倉庫（不公開）。在本機跑的工具會自己找到它，找不到時會說怎麼設定。

這裡留下的是工具和手機用的回覆小幫手：

- `index.html`：回覆小幫手，讀 `data/replies.json` 與 `data/replies/<n>.png`
- `fetch.py`、`scan.py`、`mentions.py`：讀 X 公開貼文（api.fxtwitter.com）
- `cards.py`、`site_cards.py`：回覆配圖
- `check.py`：檢查 `data/replies.json`、`data/flash.json`
