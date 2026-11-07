"""運營私人倉庫的位置（2026-11-08 起）。

策略文件、固定名單、成效紀錄搬到私人倉庫 North7/daybreak-ops-private，公開倉庫只留工具。
這裡的工具（scan.py、check.py、log.py）要讀寫那些檔案時，用 path('replies', 'watchlist.json') 這樣取路徑。

找法：先看環境變數 DAYBREAK_OPS_PRIVATE（私人倉庫根目錄）；沒有就從這個檔案往上找，
哪一層的旁邊有 daybreak-ops-private/ 就用它（所以在 daybreak-ops/、它的 worktree、daybreak/ 都找得到）。
找不到就直接結束並說怎麼 clone。
"""
import os
import sys

NAME = 'daybreak-ops-private'
CLONE = f"git clone https://github.com/North7/{NAME}.git '/Users/aron/Documents/Claude Code/{NAME}'"


def _ok(d):
    return d and os.path.isdir(os.path.join(d, 'ops'))


def root():
    env = os.environ.get('DAYBREAK_OPS_PRIVATE')
    if env:
        if _ok(env):
            return env
        sys.exit(f'DAYBREAK_OPS_PRIVATE={env} 不是運營私人倉庫（裡面沒有 ops/）。')
    p = os.path.dirname(os.path.abspath(__file__))
    while True:
        up = os.path.dirname(p)
        if _ok(os.path.join(up, NAME)):
            return os.path.join(up, NAME)
        if up == p:
            break
        p = up
    sys.exit(f'找不到運營私人倉庫 {NAME}（watchlist、成效紀錄、回覆規則 2026-11-08 起放那裡）。\n'
             f'請先 clone 到公開倉庫旁邊：\n  {CLONE}\n或設環境變數 DAYBREAK_OPS_PRIVATE 指到它的根目錄。')


def path(*parts):
    """私人倉庫 ops/ 底下的路徑，例如 path('log') 或 path('replies', 'watchlist.json')。"""
    return os.path.join(root(), 'ops', *parts)
