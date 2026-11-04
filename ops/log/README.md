# 成效紀錄

每天發了什麼、對方有沒有回應、瀏覽多少。目的是回頭看哪種內容有效，再調整 Grok 找文規則和回覆寫法。2026-11-04 開始記錄。

> 這個資料夾在 GitHub Pages 上公開。只記 X 上本來就公開的東西（貼文、瀏覽、誰回應），不放帳號密碼或私訊。

## 什麼時候記

| 時機 | Claude 做什麼 |
|---|---|
| 你傳通知截圖、或說「記錄今天」 | 用內建瀏覽器（已登入 X）讀你的「回覆」和「貼文」分頁，把當天發出的每一則 `add` 進紀錄；再依通知截圖填 `back`（對方按讚、回覆、追蹤）和 `account` |
| 隔天寫新回覆之前 | `refresh` 前一天（瀏覽在 24 小時後才比較穩定），跑 `summary`，用一兩句話告訴你昨天哪些有效；有明顯規律再提議改 Grok 規則或回覆寫法 |
| 你傳創作者分潤頁截圖時 | 更新 `account.verified_followers` |

## 指令（在倉庫根目錄）

```bash
python3 ops/log/log.py add 2026-11-04 reply https://x.com/songpu717/status/<ID> ...
python3 ops/log/log.py refresh 2026-11-04
python3 ops/log/log.py summary
```

- `add` 的類型：`daily`（日報貼文）、`flash`（快訊）、`pick`（推薦圖表）、`quote`（引用）、`reply`（回覆 Grok 找的貼文）、`followup`（回覆別人在我們貼文底下的留言）。
- `add` 會自動讀時間、語言、回覆或引用的對象、對方粉絲數、有沒有圖、瀏覽／讚／留言／轉推；對象在當天 `data/replies.json` 裡的話，會帶上編號 `ref`、角度和配圖。
- 數字都讀自 api.fxtwitter.com（公開、不需登入）。

## 格式：`ops/log/<日期>.json`

```json
{
  "date": "2026-11-04",
  "metrics_at": "2026-11-04T08:26Z",        // 瀏覽等數字最後讀取的時間
  "account": {
    "followers": 393,                       // 個人頁的追蹤數
    "verified_followers": 91,               // 創作者分潤頁的藍勾追蹤（有截圖才填）
    "new_followers": 12,                    // 通知裡的新追蹤
    "note": "數字的時間與來源"
  },
  "posts": [{
    "id": "<自己這則的 ID>", "kind": "reply", "at": "...", "lang": "zh",
    "to": "serlo123", "to_id": "<對方貼文 ID>", "to_followers": 8453,
    "ref": 9, "angle": "交叉驗證", "chart": "cost", "image": true,
    "style": "人味版",                      // 寫法有變化時標，用來比較
    "views": 64, "likes": 1, "replies": 1, "rt": 0,
    "back": {"liked": true, "replied": 1, "followed": true, "note": "對方回了什麼"}
  }],
  "unsent": ["準備了但沒發的"],
  "notes": ["當天的觀察"]
}
```

`back` 是**回覆對象本人**的回應（引用就是被引用的人）；其他人的留言寫在 `note`。
