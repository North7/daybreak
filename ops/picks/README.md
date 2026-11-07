# 每日推薦發文圖表

每天從網站的面板裡挑 **1 張**，回答一個讀者今天會問的問題，附一段可直接貼到 X／Threads 的中英文解說，在發文小幫手（`ops/post/`）下方的「今日推薦圖表 · Today's picks」顯示。2026-11-04 第一版上線，2026-11-06 改成第二版。

## 為什麼改（2026-11-06）

使用者：「目前的每日推薦圖表沒什麼意義」。第一版的問題：

1. 11/03、11/04、11/05 三天推的都是短期持有者成本、籌碼分布、Coinbase 溢價。挑圖照異動分數排，價格在成本線附近時永遠是這幾張。
2. 解說只是把數字念一遍（「−0.156%、7 日平均 −0.170%、30 日平均 −0.137%」），讀者不知道代表什麼。
3. 圖是重畫的淺色簡化版，資訊比網站原圖少，也和長貼文的深色原圖不是同一套。
4. 和日報頭條講同一件事。發文紀錄裡也沒有一則推薦圖表被發出去。

## 第二版怎麼做

| 時間 | 誰做 | 做什麼 | 產出 |
|---|---|---|---|
| 08:15 | Claude 每日任務（`docs/CLAUDE_DAILY.md` 步驟 9a） | `python3 pipeline/picks.py plan` 看候選面板 → 想讀者今天在問什麼 → 挑 1 張、寫問句標題與解說 → `python3 pipeline/picks.py check` | `data/picks.json` |
| 推送後 | GitHub Actions `share.yml` | `python3 pipeline/picks.py render --fonts ~/fonts`：用 `ops/post/site_shot.py` 截網站深色原圖（clean 模式），上方加今日圖表標籤、期數和問句標題 | `data/picks/<id>.png`、`<id>-en.png`、`index.json`、`history.json` |
| 你 | 手機開發文小幫手 | 分享（圖＋解說）、存圖、複製解說；「網站這張圖」連到網站面板 | <https://north7.github.io/daybreak/ops/post/> |

- **候選面板**：`pipeline/picks.py` 的 `PANELS`（網站面板 id `#page/key`、截圖用的圖、讀值在 `latest.json` 的位置）。今天有異動的排前面，每張附異動的白話含意（`means`）、過去同樣情況（`hist`）和面板的讀值（`data`，新指標多半帶回測）。
- **不重複**：最近 7 天推過的面板（`data/picks/history.json`，render 自動記）和長貼文用過的面板（`data/longposts.json` 每則的 `charts` 欄，寫長貼文時順手填）都不能挑。
- **不推**（`SKIP_PANELS`）：MVRV ÷ 前一輪高點（0.75 線）、短期持有者獲利比例（97.5% 賣出線）、長期路徑（推估）、掛單簿（快照）、各到期未平倉。
- **截圖失敗時**：有對應舊版圖的面板（成本線、籌碼、溢價、ETF、穩定幣、SOPR、實現損益、波動、資金流入）改畫第一版的簡化圖；沒有的就這天沒圖。
- picks.json 不是當期（每日任務沒寫）時，Actions 自動挑排第一、最近沒用過的面板，只有圖、沒有解說。

## 寫法

- **標題是問句**：讀者今天會問的一句話，例如「為什麼比特幣老在 76K 附近打轉？」「短期持有者七成在虧，以前這樣之後怎麼走？」。
- **解說三件事**：現在的讀值 → 過去同樣情況之後怎樣（勝率照實寫，例如「16 次裡 11 次」；沒有回測就不硬湊）→ 這代表什麼。每個術語講後果。
- 語氣照運營的 voice.md（2026-11-08 起在私人倉庫 `daybreak-ops-private/ops/brand/voice.md`，本機放在公開倉庫旁邊；讀不到就照這裡寫的規則）（真人說話，不要 AI 腔；持有者用語只用短期持有者／長期持有者；選擇權第一次出現寫「選擇權（期權）」，hashtag 用 #期權）。
- 只放市場資訊：不寫出場框架、觸發、價格階梯、MVRV 0.75 線、200 日均線避險、動作結論，不喊單；背離、回調壓力清單這類讀值也不能寫成買點。推算或單一交易所的數字要註明。

## `data/picks.json`

```json
{
  "date": "2026-11-05",
  "edition": 31,
  "picks": [
    {
      "id": "deriv/gex",
      "chart": "data/picks/deriv-gex.png",
      "chart_en": "data/picks/deriv-gex-en.png",
      "why": "為什麼挑這張（給自己看）",
      "q_zh": "為什麼比特幣老在 76K 附近打轉？",
      "q_en": "Why does BTC keep circling 76K?",
      "zh": "可直接貼的中文解說",
      "en": "Ready-to-post English caption"
    }
  ]
}
```

`picks.py check` 會擋：日期不是當期、不是 1 張、面板不存在或在 `recent`／`skip` 裡、標題或解說空白、標題太長、超過 280（X 算法）、出場框架或買賣字眼（「避險」「hedge」「sell」也算）、AI 腔或不用的詞（同 `ops/replies/check.py`）、查不到出處的數字、英文版有中文字。

## 本機

```bash
python3 pipeline/picks.py plan                     # 候選面板（JSON）
python3 pipeline/picks.py check                    # 檢查 data/picks.json
python3 pipeline/picks.py render --fonts <字型資料夾>   # 截圖＋出圖（要有 Chrome）
```

第一版的指令還留著：`plan-v1`、`render-v1`；舊格式的 picks.json（id 是 `cost`、`cohort` 這類）`check` 與 `render` 會照第一版處理。第一版的 `card()`、`spec()` 長文配圖（`ops/articles/charts.py`）還在用。

## 前一晚先講好方向（2026-11-08 起）

運營和使用者前一晚決定好隔天推哪張時，寫 `ops/picks/hint.json`：`bar`（要用的數據日期，台北隔天早上 08:15 的排程用的是前一天收盤）、`id`、`fallback`、`q_zh`／`q_en`、`angle`、`if`（什麼情況就不照用）、`post_at`。`picks.py plan` 只在 `bar` 對得上時輸出 `hint`，每日任務照它寫；過期的提示自動忽略，不用刪。
