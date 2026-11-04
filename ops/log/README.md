# 成效紀錄

每天發了什麼、對方有沒有回應、瀏覽多少。目的是回頭看哪種內容有效，再調整 Grok 找文規則和回覆寫法。2026-11-04 開始記錄。

> 這個資料夾在 GitHub Pages 上公開。只記 X 上本來就公開的東西（貼文、瀏覽、誰回應、新追蹤的帳號），不放帳號密碼或私訊；完整的追蹤者名單不進 git。

## 什麼時候記

| 時機 | Claude 做什麼 |
|---|---|
| 你說「記錄今天」、或傳通知截圖 | 1. `update`：自動加入當天的原創貼文、更新瀏覽、讀每則底下的留言、做追蹤者快照（藍勾數、新增了誰、回覆對象有沒有回追）。2. 回覆讀不到個人頁的回覆分頁，用內建瀏覽器（已登入 X）讀「回覆」分頁，`add` 進紀錄。3. 按讚讀不到，看通知截圖填 `back.liked` |
| 隔天寫新回覆之前 | `update` 前一天（瀏覽在 24 小時後才比較穩定），跑 `summary`，用一兩句話告訴你昨天哪些有效、藍勾追蹤離 500 還差多少；有明顯規律再提議改 Grok 規則或回覆寫法 |
| 有人在我們貼文底下留言 | `comments` 會列出來；需要回的，在對話裡提醒你並附草稿 |
| 你傳創作者分潤頁截圖時 | 和追蹤者快照的藍勾數對照（兩邊可能差幾個，以分潤頁為準），寫進 `account.note` |
| 記錄時發現你發出去的和草稿不一樣 | 把差別記到 [`../brand/voice.md`](../brand/voice.md) 的「使用者改稿紀錄」，之後照著寫 |

## 進行中的實驗

清單在 [`../brand/content-map.md`](../brand/content-map.md)「實驗清單」。記錄時用 `style` 標寫法，`summary` 會自動比較：

- **日報開頭**（2026-11-05 起）：之前的日報貼文標 `公告式`（10/20–11/04 已補記 9 則當基準），11/05 起標 `數字開頭`。

## 指令（在倉庫根目錄）

```bash
python3 ops/log/log.py update 2026-11-04        # sync＋refresh＋comments＋followers 一次做完（不寫日期＝今天）
python3 ops/log/log.py add 2026-11-04 reply https://x.com/songpu717/status/<ID> ...
python3 ops/log/log.py summary
```

- 日期一律用台北時間。
- `sync`：讀個人頁的原創貼文（不含回覆），自動分類：引用→`quote`、含「破曉 No.」→`daily`（並標 `公告式`／`數字開頭`）、和 `data/flash.json`、`data/picks.json` 開頭相同→`flash`／`pick`、連到長文→`article`，其他→`post`。分錯就直接改 `kind`。
- `add` 的類型：上面幾種，加上 `reply`（回覆 Grok 找的貼文）、`followup`（回覆別人在我們貼文底下的留言）。會自動讀時間、語言、回覆或引用的對象、對方粉絲數、有沒有圖、瀏覽／讚／留言／轉推；對象在當天 `data/replies.json` 裡的話，帶上編號 `ref`、角度和配圖。
- `comments`：每則底下別人的留言存在 `comments`（誰、藍勾、粉絲數、前 60 字）；回覆或引用的對象本人有留言，自動填 `back.replied`。
- `followers`：讀完整追蹤者名單，記總數、藍勾數；和上一次快照比，記新增了誰（`new_list`）、少了幾人；回覆對象出現在新增名單裡就填 `back.followed`。名單只存在本機 `~/.cache/daybreak-ops/`，不進 git。
- 數字都讀自 api.fxtwitter.com（第三方、公開、不需登入）。它讀不到通知、按讚名單、回覆分頁、搜尋；哪天改版讀不到了，就回到用內建瀏覽器和通知截圖。

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
