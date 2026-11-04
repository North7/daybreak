"""英文版文字檢查（2026-10-12 起；2026-11-04 擴充）。在倉庫根目錄執行：python3 pipeline/check_i18n.py；有問題會列出並以非零結束。
1. assets/app.js 裡每個 _t('…') 的中文都要在 assets/i18n-en.js 有英文（缺的字在英文版會顯示中文）。
2. 2026-11-04：10/27 之後新增的文字大多直接寫成 _T(中文, 英文) 或 h(…) 說明，第 1 項看不到。這裡再掃一遍所有含中文的字串常值，
   不在 _t／_T／h(…) 呼叫裡、也不是 [中文, 英文] 這種成對寫法的，列成「可能沒翻」。真的只在中文版用的（資料鍵、比對用的字）寫進 ZH_OK。"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, 'assets', 'app.js'), encoding='utf-8').read()
dic = open(os.path.join(ROOT, 'assets', 'i18n-en.js'), encoding='utf-8').read()
lit = r"(['\"])((?:(?!\1)[^\\]|\\.)*)\1"
used = {m.group(2) for m in re.finditer(r"_t\(" + lit + r"\)", src)}
have = {m.group(2) for m in re.finditer(r"^\s*" + lit + r":", dic, re.M)}
miss = sorted(used - have)
for k in miss: print('缺英文：', k)
print(f'_t 字串 {len(used)} 個，字典 {len(have)} 個，缺 {len(miss)} 個')

CJK = re.compile(r'[　-〿㐀-鿿＀-￯]')
CALLS = {'_t', '_T', 'h'}   # 這幾個呼叫裡的中文都有英文（_t 查字典、_T 與 h 第二個參數就是英文）
# 只在中文介面或當資料鍵用、不會原樣出現在英文版的字（英文版另有對照表或不顯示）
ZH_OK = {'直接修復', '淺回檔', '基準雙底', '延後新低', '宏觀', '資金', '衍生品', '鏈上', '監管', '產業', '機構', '地緣', '、', '，', '；', '：', '（', '）', '。'}


def tokens(s):
    """極簡 JS 斷詞：回傳 (位置, 種類, 文字)，種類是 str／punc／word；略過註解與正規表示式"""
    i, n, out, prev = 0, len(s), [], ''
    while i < n:
        c = s[i]
        if c in ' \t\r\n': i += 1; continue
        if s.startswith('//', i): i = s.find('\n', i); i = n if i < 0 else i; continue
        if s.startswith('/*', i): i = s.find('*/', i + 2) + 2; continue
        if c in '\'"`':
            j = i + 1
            while j < n and s[j] != c: j += 2 if s[j] == '\\' else 1
            out.append((i, 'str', s[i + 1:j])); prev = 'str'; i = j + 1; continue
        if c == '/' and (prev in ('', 'punc') and (not out or out[-1][2] not in (')', ']'))):   # 正規表示式
            j, cls = i + 1, False
            while j < n and (s[j] != '/' or cls):
                if s[j] == '\\': j += 1
                elif s[j] == '[': cls = True
                elif s[j] == ']': cls = False
                j += 1
            i = j + 1
            while i < n and s[i].isalpha(): i += 1
            prev = 'str'; continue
        m = re.match(r'[A-Za-z_$][\w$]*|\d[\w.]*', s[i:i + 80])
        if m: out.append((i, 'word', m.group(0))); prev = 'word'; i += len(m.group(0)); continue
        out.append((i, 'punc', c)); prev = 'punc'; i += 1
    return out


T = tokens(src)
stack, warn = [], []   # stack：每層括號 (開括號, 呼叫名稱)
for k, (pos, kind, txt) in enumerate(T):
    if kind == 'punc' and txt in '([{':
        name = T[k - 1][2] if txt == '(' and k and T[k - 1][1] == 'word' else None
        stack.append((txt, name)); continue
    if kind == 'punc' and txt in ')]}':
        if stack: stack.pop()
        continue
    if kind != 'str' or not CJK.search(txt) or txt.strip() in ZH_OK: continue
    if any(nm in CALLS for _, nm in stack): continue
    nx = T[k + 1:k + 3]   # [中文, 英文] 成對：後面緊接逗號與不含中文的字串
    if len(nx) == 2 and nx[0][2] == ',' and nx[1][1] == 'str' and not CJK.search(nx[1][2]): continue
    pv = T[k - 2:k]
    if len(pv) == 2 and pv[1][2] == ',' and pv[0][1] == 'str' and not CJK.search(pv[0][2]): continue
    if k + 1 < len(T) and T[k + 1][2] == ':': continue   # 物件的鍵（對照表）
    if k >= 2 and T[k - 1][2] == '=' and T[k - 2][2] == '=': continue   # 和資料比對（=== '牛市'），不顯示
    back = []   # 同一個敘述（往回到分號為止）
    for t in reversed(T[max(0, k - 120):k]):
        if t[2] == ';': break
        back.append(t)
    if any(t[1] == 'word' and t[2] == 'LANG' for t in back): continue   # LANG === 'en' ? 英文 : 中文 的中文那一邊
    if any(t[1] == 'word' and t[2] in ('dirZ', 'pctWord') for t in T[max(0, k - 8):k]): continue   # 中文專用變數／由 pctWord 自己翻
    warn.append((src.count('\n', 0, pos) + 1, txt))
for ln, txt in warn: print(f'可能沒翻（app.js:{ln}）：{txt[:70]}')
print(f'不在翻譯函式裡的中文字串 {len(warn)} 個')
sys.exit(1 if miss or warn else 0)
