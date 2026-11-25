# -*- coding: utf-8 -*-
"""繁體 → 簡體（2026-11-25，使用者：「加簡體版」）。主題頁（topics.py）的簡體版 zh-hans/<主題>/ 用這支把整頁 HTML 轉過去。
用 OpenCC 的 tw2sp（台灣用語 → 大陸用語：網路→网络、資訊→信息、程式→程序），再補一張金融用語對照：
大陸讀者習慣的說法和台灣不同（聯準會→美联储、殖利率→收益率、選擇權→期权、未平倉→持仓），不補的話讀起來像台灣網站硬轉的。
套件：opencc-python-reimplemented==0.1.7（純 Python）。部署和檢查流程會先裝；沒裝到就回傳 None，主題頁只出繁體和英文，不會壞。
2026-11-25 首頁和數據頁也有簡體了：瀏覽器用的轉換器 assets/hans.js 由這支的 js() 產生（同一份字典、同一張 TERMS），網站上所有地方的簡體都是同一套轉法。"""
# OpenCC 的「台灣用語 → 大陸用語」表（TWPhrasesRev）是給電腦軟體用的，有些詞在這個網站的意思不一樣，照轉會錯：
#   「價格線上的圓圈」→「价格在线」、「離線 17.2%」（離均線多遠）→「脱机」、「指標」→「指针」、「冪律通道」→「信道」、「序列」→「串行」、「底部的連線」→「连接」……
# DROP 的詞不用那張表（只做繁簡字轉換：线上、离线、指标、通道），TWO 的詞改成這裡寫的說法（寫繁體，後面還會再轉一次簡體）。
# 新加的詞先跑 python3 pipeline/next/hans.py --check 看網站上用到的台灣用語都轉成什麼
DROP = {'線上', '離線', '指標', '通道', '序列', '連線', '堆疊', '模擬', '簡報', '複製', '整合', '互動'}
TWO = {'介面': '界面', '預設': '默認', '相簿': '相冊', '檢視': '視圖'}
try:
    from opencc import OpenCC
    _CC = OpenCC('tw2sp')
    for _gi, _g in enumerate(_CC._dict_chain):
        for _di, _f in enumerate(_g):
            if str(_f).endswith('TWPhrasesRev.txt'):
                _m = _CC._dict_chain_data[_gi][_di][2]
                for _k in DROP: _m.pop(_k, None)
                _m.update(TWO)
except Exception as e:   # 沒裝套件：不出簡體版
    # 2026-11-25 印到 stderr：pages.py --img-list 的 stdout 要是純 JSON（chart-img.yml、daily.yml 會接著解析），沒裝 opencc 的執行機印到 stdout 會讓截圖壞掉
    print("hans: opencc not available, skipping zh-Hans pages:", e, file=__import__("sys").stderr)
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


def js():
    """assets/hans.js：瀏覽器用的轉換器（網站首頁、數據頁選「简」時才載入）＝ hans_rt.js ＋ OpenCC tw2sp 的字典 ＋ 上面的 TERMS。
    字典是固定的（不跟每天的資料走），所以這個檔進程式庫；換 OpenCC 版本或改 TERMS 時重跑：python3 pipeline/next/hans.py --js
    （跑完記得把 page.html、pipeline/intro/page.html 裡 assets/hans.js?v= 換成印出來的版本號）"""
    import json, os, hashlib
    chain = []
    for g in _CC._dict_chain_data:
        out = []
        for mx, mn, d in g:
            m = {}
            for k, v in d.items():
                v = v.split(' ')[0]   # 一對多時和 Python 版一樣取第一個
                if any(ord(ch) > 0xFFFF for ch in k + v): continue    # 罕用的擴充區字（JS 的字串長度算法不同）；網站上不會出現
                m[k] = v
            t = {'m': max(map(len, m)), 'n': min(map(len, m))}
            if t['m'] == 1 and all(len(v) == 1 for v in m.values()): t.update(k=''.join(m), v=''.join(m.values()))   # 單字對單字：兩條字串，省一半大小
            else: t['d'] = m
            out.append(t)
        chain.append(out)
    rt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hans_rt.js'), encoding='utf-8').read()
    out = rt.replace('__CHAIN__', json.dumps(chain, ensure_ascii=False, separators=(',', ':'))).replace('__TERMS__', json.dumps(TERMS, ensure_ascii=False, separators=(',', ':')))
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'hans.js')
    open(p, 'w', encoding='utf-8').write(out)
    print('wrote assets/hans.js', len(out.encode('utf-8')), 'bytes; v=' + hashlib.sha1(out.encode('utf-8')).hexdigest()[:10])


def check():
    """網站上（數據頁、介紹頁、每天的資料）用到的台灣用語各轉成什麼，給人看一遍；改 DROP／TWO 前後跑"""
    import os, re, glob, json
    R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    txt = '\n'.join(open(f, encoding='utf-8').read() for f in [os.path.join(R, 'pipeline', 'next', 'page.html'), os.path.join(R, 'pipeline', 'intro', 'page.html')] + glob.glob(os.path.join(R, 'data', 'next*.js')))
    txt = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m[1], 16)), txt)
    for gi, g in enumerate(_CC._dict_chain_data[:1]):
        for mx, mn, d in g:
            hits = sorted(((txt.count(k), k, v.split(' ')[0]) for k, v in d.items() if len(k) > 1 and k in txt), reverse=True)
            print(' '.join('%s→%s(%d)' % (k, convert(k), n) for n, k, v in hits))


if __name__ == '__main__':
    import sys
    if '--js' in sys.argv: js()
    if '--check' in sys.argv: check()
