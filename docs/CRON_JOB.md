# 用 cron-job.org 準時觸發資料管線

## 為什麼要這樣做

GitHub Actions 自己的定時排程（`schedule`）在這個倉庫每天都晚 5–7 小時才跑（2026-10-08 到 10-12 實測：
設定 UTC 00:05，實際 05:30–07:05）。現在每天的資料能準時，是因為 Claude 每日任務在 00:30 發現資料沒更新、自己推送觸發；
鏈上快取（Prefetch on-chain，設定 UTC 22:40）則晚到隔天 01:00 以後，比當天資料建置還晚，輪替指標因此多舊一天。

改由 cron-job.org 準時呼叫 GitHub 的 `repository_dispatch` API。兩個工作流程都已經接受這種觸發；
同一天重複呼叫時會自動略過（「今天已更新就結束」），所以多設一個備援時間不會浪費額度。
原本的 `schedule` 與 Claude 推送觸發都保留當備援。

## 一、建立 GitHub token（只需要一次）

1. 打開 <https://github.com/settings/personal-access-tokens/new>（Fine-grained token）。
2. **Token name**：`daybreak-cron`；**Expiration**：選 1 年（到期前 GitHub 會寄信提醒，換新 token 後回 cron-job.org 更新）。
3. **Repository access**：選 **Only select repositories** → 勾 `North7/daybreak`。
4. **Permissions** → **Repository permissions** → **Contents** 設為 **Read and write**（`repository_dispatch` 需要這個權限；其他都不用開）。
5. 按 **Generate token**，複製以 `github_pat_` 開頭的字串。這串只會顯示一次，不要貼到任何公開的地方（包括這個倉庫）。

## 二、在 cron-job.org 建兩個工作

登入 <https://console.cron-job.org> → **Create cronjob**。兩個工作的設定只有「標題、時間、event_type」不同。

### 工作 A：每日資料（Daily data）

**COMMON 分頁**

| 欄位 | 填什麼 |
|---|---|
| Title | `daybreak daily-data` |
| URL | `https://api.github.com/repos/North7/daybreak/dispatches` |
| Execution schedule | 選 **Custom**，時區 **UTC**；Minutes 勾 `6` 與 `20`，Hours 勾 `0`，Days／Months／Weekdays 全選 |

（UTC 00:06＝台北 08:06：日線 00:00 收盤後幾分鐘；00:20 是備援，資料已更新時會自動略過。）

**ADVANCED 分頁**

| 欄位 | 填什麼 |
|---|---|
| Request method | **POST** |
| Request headers | `Authorization` ＝ `Bearer github_pat_…`（貼上第一步的 token）<br>`Accept` ＝ `application/vnd.github+json`<br>`Content-Type` ＝ `application/json`<br>`User-Agent` ＝ `daybreak-cron` |
| Request body | `{"event_type":"daily-data"}` |
| Timeout | 30 秒 |
| Treat redirects with HTTP 3xx status code as success | 不勾 |

Notifications 建議勾「執行失敗時寄信」。

### 工作 B：鏈上快取（Prefetch on-chain）

複製工作 A（列表上的 **⋯ → Clone**），改三個地方：

| 欄位 | 填什麼 |
|---|---|
| Title | `daybreak prefetch` |
| Execution schedule | 時區 UTC；Minutes 勾 `40`，Hours 勾 `22`（＝台北 06:40） |
| Request body | `{"event_type":"prefetch"}` |

## 三、測試

1. 在 cron-job.org 工作列表按 **Test run**（或 ▶）。成功時回應狀態是 **204 No Content**。
   - 401／403：token 貼錯、過期，或權限不是 Contents: Read and write。
   - 404：URL 打錯，或 token 沒有勾到 `North7/daybreak`。
   - 422：Request body 不是合法 JSON。
2. 打開 <https://github.com/North7/daybreak/actions>，應該看到一個新的執行，觸發來源是 `repository_dispatch`。
   當天資料已經更新過的話，它會在「Skip if already updated」那一步之後直接結束，這是正常的。

## 四、之後

- token 到期前一週 GitHub 會寄信；重新產生一個，回到兩個工作把 `Authorization` 換掉即可。
- 想暫停：在 cron-job.org 把工作關掉就好，GitHub 原本的排程與 Claude 的推送觸發仍會運作（只是比較晚）。
