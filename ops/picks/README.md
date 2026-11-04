# 每日推薦發文圖表

每天從網站已有的圖表裡挑 1–3 張「今天最值得發」的，各附一段可直接貼到 X／Threads 的中英文解說，在發文小幫手（`ops/post/`）下方的「今日推薦圖表 · Today's picks」一起顯示。2026-11-04 第一版上線。

## 流程

| 時間 | 誰做 | 做什麼 | 產出 |
|---|---|---|---|
| 08:30 | Claude 每日任務（`docs/CLAUDE_DAILY.md` 步驟 9a） | `python3 pipeline/picks.py plan` 看候選圖 → 挑 1–3 張寫解說 → `python3 pipeline/picks.py check` | `data/picks.json` |
| 推送後 | GitHub Actions `share.yml` | `python3 pipeline/picks.py render --fonts ~/fonts` | `data/picks/<id>.png`、`<id>-en.png`、`index.json` |
| 你 | 手機開發文小幫手 | 分享（圖＋解說）、存圖、複製解說 | <https://north7.github.io/daybreak/ops/post/> |

## 怎麼挑圖（`pipeline/picks.py`）

1. 當期 `data/notes.json` 的 `findings`（今日發現）各帶一張 `chart`，依序優先。
2. 再依 `data/latest.json` 的 `signals`（`pipeline/signals.py` 偵測的異動）分數補，同一張圖只出一次，最多 3 張。
3. 不推和出場框架有關的：`page = exit` 的異動、週期佐證燈號（`ev-*`）、MVRV ÷ 前一輪高點（`p20`）、200 日均線相關異動、頂部區。
4. 今天完全沒有異動就推價格走勢（`ov-px`）。

畫得出來的圖：`ov-px` 價格、`cost` 短期持有者成本與真實市場均價、`cohort` 長短期持有者籌碼、`cbp` Coinbase 溢價、`sopr` 短期持有者 SOPR、`stab` 穩定幣、`etf` ETF 淨流量、`sthpnl` 短期持有者實現損益、`vol` 隱含／實際波動、`npl` 每日淨實現損益，以及 `signals.py` 序列目錄裡的其他圖（鏈上指標 `oc-*`、`profit`、`rcliq`，畫成近一年一條線）。

## 圖

1080×1350（4:5 直式，X、Threads、IG 都不裁切），中英各一張，字型與配色同分享圖（Noto Sans TC 900、Archivo 窄體、JetBrains Mono；紙色底、號外紅）。版面：今日圖表標籤與期數 → 大標題（數字標紅；預設用該圖分數最高的異動標題）→ 圖名與一句說明 → 圖 → 資料來源與日期 → 底部三格關鍵數字 → 網址與 X 帳號。圖上的數字都直接取自 `latest.json`。

本機出圖：

```bash
python3 pipeline/picks.py render --fonts <放 NotoSansTC[wght].ttf、Archivo[wdth,wght].ttf、JetBrainsMono[wght].ttf 的資料夾>
```

## `data/picks.json`

```json
{
  "date": "2026-11-03",
  "edition": 29,
  "picks": [
    {
      "id": "cohort",
      "chart": "data/picks/cohort.png",
      "chart_en": "data/picks/cohort-en.png",
      "why": "為什麼今天推這張（給自己看）",
      "zh": "可直接貼的中文解說",
      "en": "Ready-to-post English caption"
    }
  ]
}
```

可選 `title_zh`／`title_en`：改圖上的大標題。

解說規則（`picks.py check` 會擋）：數字只引用、不改（每個數字都要在 plan 的資料或當期 notes 裡查得到）；每則 ≤ 280（X 算法）；只講市場資訊，不寫出場框架、觸發、價格階梯、MVRV 0.75 線、200 日均線避險、動作結論，也不喊單；英文版沒有中文字。

`picks.json` 不存在或不是當期時，Actions 照樣自動挑 3 張畫圖（`data/picks/index.json` 記錄畫了哪些），發文小幫手只顯示圖、標明「還沒有解說」。
