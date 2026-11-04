# 每日推薦發文圖表（規劃中）

目標：每天從網站已有的圖表裡挑 1–3 張「今天最值得發」的，各附一段可直接貼到 X／Threads 的解說，在發文小幫手裡一起顯示。

## 打算的做法

1. **挑圖**：沿用 `pipeline/signals.py` 已偵測的異動與每日任務寫的「今日發現」（`data/notes.json` 的 `findings`），哪個指標今天在動，就推哪張圖。
2. **出圖**：用 `pipeline/share_card.py` 同一套字型與配色，把該圖表畫成適合社群的直式／方形圖，存到 `data/picks/`。
3. **解說**：每日任務另寫 `data/picks.json`，每張圖一則中英文解說（數字只引用、不改數字；只講資訊，不講出場框架）。
4. **顯示**：發文小幫手（`ops/post/`）加一區「今日推薦圖表」，每張圖都能分享、存圖、複製解說。

`data/picks.json` 草案：

```json
{
  "date": "2026-11-04",
  "picks": [
    {
      "id": "funding",
      "chart": "data/picks/funding.png",
      "why": "為什麼今天推這張（給自己看）",
      "zh": "可直接貼的中文解說",
      "en": "Ready-to-post English caption"
    }
  ]
}
```
