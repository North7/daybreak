#!/usr/bin/env python3
"""檢查 data/replies.json（2026-11-04 建立）：欄位齊全、語言對（英文貼文回英文、中文貼文回繁體中文、其他語言跳過）、
X 字數 280 以內、不談出場框架、配圖檔存在、數據日期是當期。有錯就以非零結束。
用法（在倉庫根目錄）：python3 ops/replies/check.py"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
from x_len import weight   # noqa: E402

CJK = re.compile(r'[㐀-鿿]')
SIMP = set('这们说为来对时国会个过还没发么从动场实现价币机构资线买卖盘关头应该开间觉进处净链亿万点涨')
BAN = re.compile(r'出場|階梯|避險|賣出線|減碼|分批賣|exit (plan|ladder|framework)|sell (signal|trigger)|take profit', re.I)
NEED = ('n', 'order', 'status', 'url', 'id', 'author', 'followers', 'posted', 'lang', 'angle', 'summary', 'reply')
# 太機械的寫法（README「要有人味」）：報告式開頭、自稱本站
ROBOT = re.compile(r'^(補一個|補一組|補兩個|Daily data|Our .{0,40}estimate|Data shows)|本站', re.I)


def check():
    R = json.load(open(os.path.join(ROOT, 'data', 'replies.json'), encoding='utf-8'))
    L = json.load(open(os.path.join(ROOT, 'data', 'latest.json'), encoding='utf-8'))
    err = [f'缺少 {k}' for k in ('date', 'data_date', 'edition', 'items') if k not in R]
    if R.get('data_date') != L['meta']['bar_date']: err.append(f'data_date {R.get("data_date")} 不是當期數據 {L["meta"]["bar_date"]}')
    ns = set()
    for it in R.get('items', []):
        tag = f'#{it.get("n")}'
        err += [f'{tag} 缺少 {k}' for k in NEED if k not in it]
        if it.get('n') in ns: err.append(f'{tag} 編號重複')
        ns.add(it.get('n'))
        if it.get('status') not in ('send', 'optional', 'skip'): err.append(f'{tag} status 只能是 send／optional／skip')
        if str(it.get('id')) not in str(it.get('url')): err.append(f'{tag} id 和網址對不上')
        t = it.get('reply') or ''
        if it.get('status') == 'skip':
            if not it.get('note'): err.append(f'{tag} 跳過要寫原因（note）')
            continue
        if it.get('lang') not in ('zh', 'en'): err.append(f'{tag} 原文是 {it.get("lang")}：只回中文和英文貼文，請改成 skip')
        if not t: err.append(f'{tag} 沒有回覆內容')
        if weight(t) > 280: err.append(f'{tag} 回覆 {weight(t)}/280，超過')
        if it.get('lang') == 'en' and CJK.search(t): err.append(f'{tag} 英文貼文的回覆裡有中文')
        if it.get('lang') == 'zh':
            if not CJK.search(t): err.append(f'{tag} 中文貼文要用繁體中文回')
            s = sorted(set(t) & SIMP)
            if s: err.append(f'{tag} 回覆有簡體字：{"".join(s)}')
        if BAN.search(t): err.append(f'{tag} 回覆提到出場框架或買賣動作：{BAN.search(t).group(0)}')
        if ROBOT.search(t): err.append(f'{tag} 回覆太機械（「{ROBOT.search(t).group(0)}」）：先回應對方、用「我」，見 README「要有人味」')
        if it.get('image') and not os.path.exists(os.path.join(ROOT, 'data', 'replies', f'{it["n"]}.png')):
            err.append(f'{tag} 有 image 但 data/replies/{it["n"]}.png 不存在（先跑 cards.py）')
    return err


if __name__ == '__main__':
    e = check()
    print('\n'.join(e) if e else 'replies.json OK')
    sys.exit(1 if e else 0)
