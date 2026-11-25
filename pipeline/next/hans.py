# -*- coding: utf-8 -*-
"""繁體 → 簡體（2026-11-25，使用者：「加簡體版」）。主題頁（topics.py）的簡體版 zh-hans/<主題>/ 用這支把整頁 HTML 轉過去。
用 OpenCC 的 tw2sp（台灣用語 → 大陸用語：網路→网络、資訊→信息、程式→程序），再補一張金融用語對照：
大陸讀者習慣的說法和台灣不同（聯準會→美联储、殖利率→收益率、選擇權→期权、未平倉→持仓），不補的話讀起來像台灣網站硬轉的。
套件：opencc-python-reimplemented==0.1.7（純 Python）。部署和檢查流程會先裝；沒裝到就回傳 None，主題頁只出繁體和英文，不會壞。"""
try:
    from opencc import OpenCC
    _CC = OpenCC('tw2sp')
except Exception as e:   # 沒裝套件：不出簡體版
    print('hans: opencc not available, skipping zh-Hans pages:', e)
    _CC = None

# 轉完之後再換的詞（左邊是 tw2sp 轉出來的樣子）。長的放前面，避免被短的先換掉
TERMS = [
    ('联准会', '美联储'), ('殖利率', '收益率'), ('选择权', '期权'), ('履约价', '行权价'), ('那斯达克', '纳斯达克'),
    ('未平仓量', '持仓量'), ('未平仓', '持仓'), ('资料来源', '数据来源'), ('资料', '数据'), ('帐户', '账户'),
    ('看跌／看涨比', '看跌/看涨比'), ('标普 500', '标普500'),
    ('升息', '加息'), ('几率', '概率'), ('品质', '质量'), ('获利', '盈利'),
]


def available():
    return _CC is not None


def convert(s):
    """整段文字（或整頁 HTML）轉成簡體；沒有 OpenCC 時回傳 None"""
    if _CC is None: return None
    t = _CC.convert(s)
    for a, b in TERMS: t = t.replace(a, b)
    # 簡體頁用 Noto Sans SC：同一個字（例如「骨」「直」）兩岸的寫法不同，繁體字型排簡體字會混著台灣字形
    return t.replace('Noto+Sans+TC', 'Noto+Sans+SC').replace('"Noto Sans TC"', '"Noto Sans SC"')
