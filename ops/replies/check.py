#!/usr/bin/env python3
"""檢查 data/replies.json（2026-11-04 建立）：欄位齊全、語言對（英文貼文回英文、中文貼文回繁體中文、其他語言跳過）、
X 字數 280 以內、不談出場框架、配圖檔存在、數據日期是當期。有錯就以非零結束。
用法（在倉庫根目錄）：python3 ops/replies/check.py"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
sys.path.insert(0, os.path.join(ROOT, 'ops'))
from x_len import weight   # noqa: E402

CJK = re.compile(r'[㐀-鿿]')
SIMP = set('这们说为来对时国会个过还没发么从动场实现价币机构资线买卖盘关头应该开间觉进处净链亿万点涨')
BAN = re.compile(r'出場|階梯|避險|賣出線|減碼|分批賣|exit (plan|ladder|framework)|sell (signal|trigger)|take profit', re.I)
NEED = ('n', 'order', 'status', 'url', 'id', 'author', 'followers', 'posted', 'lang', 'angle', 'summary', 'reply')
HASH = re.compile(r'(^|\s)#[^\s#]+')   # hashtag：原創貼文（引用、快訊）要帶，回覆不帶
# 太機械的寫法（README「要有人味」）：報告式開頭、自稱本站
ROBOT = re.compile(r'^(補一個|補一組|補兩個|Daily data|Our .{0,40}estimate|Data shows)|本站', re.I)
# AI 腔（2026-11-05 研究後訂，見 ops/brand/voice.md「真人說話，不要 AI 腔」）：一出現就擋
AI_WORDS = re.compile(r'新手|老手|新買家|老買家|短線的人|值得注意的是|值得一提|整體而言|總的來說|總而言之|綜上|我的(看法|判斷|結論)是|所以我的判斷|什麼情況會讓我改看法|會讓我改看法|說白了|說穿了|先說結論|結論先講|首先[，,].{0,40}其次|不僅僅?是|而且老實說|說到底|這就是全部|'
                      r'\b(delve|crucial|pivotal|underscores?|testament|tapestry|showcases?|Additionally|Moreover|Furthermore|'
                      r"Here's the thing|That's the whole story|Fun (fact|detail)|No fluff|Let that sink in)\b|——|—", re.I)
# 只提醒、不擋：一天裡出現太多次才是問題
CONTRAST = re.compile(r'不是[^，。？\n]{1,24}[，,、 ]?(而)?是|不等於|\bnot (just |only )?an? [^,.]{1,30}, (but )?|, not an? |isn\'t [^,.]{1,30}[,.] it\'s|rather than', re.I)
DECIMAL = re.compile(r'\d\.\d')
QEND = re.compile(r'[？?]\s*$')
# 2026-11-06 依 @lieflat_3 配對實測（voice.md AI 腔清單）：逐句提醒、不擋
LIST3 = re.compile(r'[^，。！？；：\n]*、[^，。！？；：\n]*、[^，。！？；：\n]*')        # 一個分句裡兩個以上頓號
PREMOD = re.compile(r'[^，。！？；：\n、]{16,}的[^，。！？；：\n、的]{1,6}(?=[，。！？；\n]|$)|的[^，。！？；：\n]{0,8}的[^，。！？；：\n]{0,8}的')  # 過長前置定語／連著三個「的」
SHELL = re.compile(r'對於[^，。]{1,15}(來說|而言)|就[^，。]{1,10}而言|當[^，。]{2,20}時，|(^|\n)(然而|因此|此外)，')


def sentence_notes(tag, t):
    """單篇文字的逐句提醒（長貼文、快訊、回覆共用）：頓號罗列、前置定語、話題殼／句首路標、相鄰三句同款開頭。"""
    out = [f'{tag} 頓號罗列：「{m.group(0).strip()[:40]}」' for m in LIST3.finditer(t)]
    out += [f'{tag} 前置定語太長：「{m.group(0)[:40]}」' for m in PREMOD.finditer(t) if '是' not in m.group(0)]   # 「……是……的底」是謂語，不是前置定語
    out += [f'{tag} 話題殼／句首路標：「{m.group(0).strip()[:30]}」' for m in SHELL.finditer(t)]
    s = [x.strip() for x in re.split(r'[。！？\n]', t) if len(x.strip()) >= 6]
    for i in range(len(s) - 2):
        if s[i][:2] == s[i + 1][:2] == s[i + 2][:2]: out.append(f'{tag} 連三句同款開頭：「{s[i][:12]}…」')
    return out


def check_longposts():
    """data/longposts.json（長貼文）：AI 用語、簡體、框架用詞直接擋；逐句提醒另外印。"""
    p = os.path.join(ROOT, 'data', 'longposts.json')
    if not os.path.exists(p): return [], []
    err, notes = [], []
    for it in json.load(open(p, encoding='utf-8')).get('items', []):
        for lang in ('zh', 'en'):
            t = it.get(lang)
            if not t: continue
            tag = f'長貼文 {it.get("id")} {lang}'
            if AI_WORDS.search(t): err.append(f'{tag} AI 腔（「{AI_WORDS.search(t).group(0)}」）')
            if BAN.search(t): err.append(f'{tag} 提到出場框架或買賣動作：{BAN.search(t).group(0)}')
            if lang == 'zh' and set(t) & SIMP: err.append(f'{tag} 有簡體字：{"".join(sorted(set(t) & SIMP))}')
            notes += sentence_notes(tag, t)
    return err, notes


def check():
    R = json.load(open(os.path.join(ROOT, 'data', 'replies.json'), encoding='utf-8'))
    L = json.load(open(os.path.join(ROOT, 'data', 'latest.json'), encoding='utf-8'))
    err = [f'缺少 {k}' for k in ('date', 'data_date', 'edition', 'items') if k not in R]
    if R.get('data_date') != L['meta']['bar_date']: err.append(f'data_date {R.get("data_date")} 不是當期數據 {L["meta"]["bar_date"]}')
    ns, ids = set(), {}
    for it in R.get('items', []):
        tag = f'#{it.get("n")}'
        err += [f'{tag} 缺少 {k}' for k in NEED if k not in it]
        if it.get('n') in ns: err.append(f'{tag} 編號重複')
        ns.add(it.get('n'))
        # 小幫手用 id 記「已回覆」、也用 id 當回覆對象：接話（kind followup）要填對方那則留言的 id，不能沿用原文的（2026-11-07）
        key = (str(it.get('id')), it.get('mode') == 'quote')
        if key in ids: err.append(f'{tag} 和 #{ids[key]} 的 id 重複（接話要用對方留言的 id，回覆和引用同一則才可以共用）')
        ids[key] = it.get('n')
        if it.get('status') not in ('send', 'optional', 'skip'): err.append(f'{tag} status 只能是 send／optional／skip')
        if str(it.get('id')) not in str(it.get('url')): err.append(f'{tag} id 和網址對不上')
        t = it.get('reply') or ''
        if it.get('status') == 'skip':
            if not it.get('note'): err.append(f'{tag} 跳過要寫原因（note）')
            continue
        if it.get('lang') not in ('zh', 'en'): err.append(f'{tag} 原文是 {it.get("lang")}：只回中文和英文貼文，請改成 skip')
        if not t and not (it.get('mode') == 'quote' and it.get('quote')): err.append(f'{tag} 沒有回覆內容')   # 只引用不回覆的可以留空（2026-11-06）
        if t: err += text_errors(tag + ' 回覆', t, it.get('lang'))
        if t and ONE_LINE.search(t): err.append(f'{tag} 回覆一行裡有兩句（「{ONE_LINE.search(t).group(0)}」）：每句話換一行，見 voice.md 2026-11-08')
        if HASH.search(t): err.append(f'{tag} 回覆不加 hashtag（引用文和快訊才加）')
        q = it.get('quote')
        if q:
            lim = 25000 if it.get('long') else 280   # 2026-11-08：Premium 可以引用發長文（"long": true），X 先顯示前 280 字左右，重點放前面
            if weight(q) + 23 > lim: err.append(f'{tag} 引用文 {weight(q) + 23}/{lim}（含原文網址 23），超過')
            err += [e for e in text_errors(tag + ' 引用文', q, it.get('lang'), lim) if '太機械' not in e]
            if not HASH.search(q): err.append(f'{tag} 引用文結尾要帶 hashtag 關鍵詞（見 README「hashtag」）')
        if it.get('mode') not in (None, 'reply', 'quote'): err.append(f'{tag} mode 只能是 reply／quote')
        if it.get('mode') == 'quote' and not q: err.append(f'{tag} mode 是 quote 但沒有 quote 文字')
        if it.get('image') and not os.path.exists(os.path.join(ROOT, 'data', 'replies', f'{it["n"]}.png')):
            err.append(f'{tag} 有 image 但 data/replies/{it["n"]}.png 不存在（先跑 cards.py）')
    err += repeat_errors(R.get('items', []))
    return err + check_flash()


CERTAIN = re.compile(r'底(早就|已經|已)?(到了|出現|確認)|週期底已|見底了|第二波(真正)?開始|換手完成|該跌的(都)?跌完|熊市(已經)?結束|牛市(已經)?回來|bottom is (in|confirmed)|the bottom is in|bear market is over', re.I)
BIG = 250000   # 2026-11-07：X 對 25 萬粉以上帳號底下的回覆跑 AI 檢查（"llm slop" 標籤，14–30 天，對方收不到通知）


def repeat_errors(items):
    """同一天的回覆／引用不能一字不差重複自己的句子（X 的 copypasta／duplicate 標籤）；25 萬粉以上的回覆要使用者自己改寫。"""
    err = []
    for it in items:
        if it.get('status') == 'skip': continue
        if (it.get('followers') or 0) >= BIG and it.get('mode') != 'quote' and it.get('reply') and it.get('status') != 'optional':
            err.append(f'#{it["n"]} @{it.get("author")} 有 {it["followers"]:,} 粉（25 萬以上）：回覆會被 X 跑 AI 檢查，改成 status "optional" 並在 note 請使用者用自己的話改寫，或改成引用（mode "quote"）')
    # 2026-11-08（帳號分析）：①有外推線／推算日期的圖不配（佐證圖 c-ev-* 畫「近 30 日速度外推」和「外推交叉 12/02」，等於在推未來日期）；
    # ②同一張圖、同一種語言一天只給一則（11/05 兩則 DVOL 回覆圖文幾乎一樣、隔 21 分鐘）；③太肯定的階段斷言要改成帶前提的說法
    imgs = {}
    for it in items:
        if it.get('status') == 'skip' or not it.get('image'): continue
        im = it['image']; key = ((im.get('site') or {}).get('sel') or im.get('chart'), 'zh' if it.get('lang') == 'zh' else 'en')
        if str(key[0]).startswith('#c-ev-'): err.append(f'#{it["n"]} 配圖 {key[0]} 有外推線和推算日期，不配（只放已經發生的走勢）')
        if key in imgs: err.append(f'#{it["n"]} 和 #{imgs[key]} 用同一張圖（{key[0]}，{key[1]}）：同一張圖同一種語言一天只給一則')
        else: imgs[key] = it['n']
    for it in items:
        if it.get('status') == 'skip': continue
        for k in ('reply', 'quote'):
            m = CERTAIN.search(it.get(k) or '')
            if m: err.append(f'#{it["n"]} {"回覆" if k == "reply" else "引用"}「{m.group(0)}」太肯定：改成帶前提的說法（例如「如果 6/30 是這輪的底…」「照過去三輪的時間…」）')
    K = 14; seen = {}; hit = {}
    for it in sorted(items, key=lambda x: x.get('n') or 0):   # 編號小的先：重複算在後寫的那則
        if it.get('status') == 'skip': continue
        for k in ('reply', 'quote'):
            t = re.sub(r'https?://\S+|@\w+|#\S+', '', it.get(k) or '')
            t = re.sub(r'[\s，。、,.!?！？：:；;（）()「」"\'…—-]', '', t.lower())
            for i in range(len(t) - K + 1):
                g = t[i:i + K]
                if g in seen and seen[g] != it['n']:
                    if not it.get('repeat_ok'): hit.setdefault((seen[g], it['n']), g)   # repeat_ok：兩則都已經發出去了，改不了
                else: seen.setdefault(g, it['n'])
    for (a, b), g in hit.items():
        err.append(f'#{a} 和 #{b} 有一樣的句子（「{g}…」）：數字可以一樣，說法要換（X 會把一字不差的重複標成 copypasta）')
    return err


# 2026-11-08 使用者：開頭常是「我和你差不多」「我這邊數據也是」，太機械、像 AI。第一句不要先附和／確認對方，直接講新東西。
ECHO = re.compile(r'我這邊(也|的數據也|看到的也|算的也)?|跟你(的)?(說的|讀數|數字)?(差不多|一樣|對得上|接近)|讀數跟你|數據也(是|一樣)|我也(看到|是這樣|算到)|^(同意|沒錯|對[，,]|確實)|'
                  r'\b(same|too|agreed?|either|as well|matches|lines? up|backs? (you|that|it) up)\b|^(yep|yeah|exactly|true|right)\b', re.I)


# 2026-11-08 使用者：「以後回覆，每句話換一行」。句號／問號／驚嘆號後面還有字就是兩句擠一行；句尾不加「。」。
ONE_LINE = re.compile(r'[。！？][^\n]|(?<!vs)(?<!e\.g)(?<!i\.e)(?<!U\.S)[.!?] +(?=[A-Z0-9$"“(])|。$', re.M)


def first_clause(t):
    return re.split(r'[，。！？\n]|[,.!?](\s|$)', t.strip(), maxsplit=1)[0]


def text_errors(tag, t, lang, lim=280):
    """一段要發出去的文字：字數、語言、簡體字、框架用詞、機械開頭。"""
    err = []
    if weight(t) > lim: err.append(f'{tag} {weight(t)}/{lim}，超過')
    if lang == 'en' and CJK.search(t): err.append(f'{tag}：英文的文字裡有中文')
    if lang == 'zh':
        if not CJK.search(t): err.append(f'{tag}：中文要用繁體中文')
        s = sorted(set(t) & SIMP)
        if s: err.append(f'{tag} 有簡體字：{"".join(s)}')
    if BAN.search(t): err.append(f'{tag} 提到出場框架或買賣動作：{BAN.search(t).group(0)}')
    if ROBOT.search(t): err.append(f'{tag} 太機械（「{ROBOT.search(t).group(0)}」）：先回應對方、用「我」，見 README「要有人味」')
    if AI_WORDS.search(t): err.append(f'{tag} AI 腔（「{AI_WORDS.search(t).group(0)}」）：見 voice.md「真人說話，不要 AI 腔」')
    m = ECHO.search(first_clause(t))
    if m: err.append(f'{tag} 開頭先附和（「{m.group(0)}」）：第一句直接講新東西，見 voice.md 2026-11-08')
    return err


def known_accounts():
    """ops/log/ 裡回覆過的對象（不含今天）＝熟帳號。ops/log/ 2026-11-08 起在私人倉庫。"""
    import glob
    import opsprivate
    R = json.load(open(os.path.join(ROOT, 'data', 'replies.json'), encoding='utf-8'))
    out = set()
    for f in glob.glob(os.path.join(opsprivate.path('log'), '2*.json')):
        if os.path.basename(f)[:10] >= R.get('date', '9'): continue
        for p in json.load(open(f, encoding='utf-8')).get('posts', []):
            if p.get('kind') in ('reply', 'followup') and p.get('to'): out.add(p['to'].lower())
    return out


def tone_notes(items):
    """整批回覆的 AI 腔提醒（不擋）：單則看不出來，排在一起才看得出是同一個模板。"""
    R = [it for it in items if it.get('status') != 'skip' and it.get('reply')]
    if len(R) < 5: return []
    n = len(R); out = []
    def share(f): return sum(1 for it in R if f(it['reply'])) / n
    c = [it['n'] for it in R if CONTRAST.search(it['reply'])]
    if len(c) > max(2, n // 8): out.append(f'對比句（不是 X 是 Y／X 不等於 Y／not X）{len(c)} 則：{c}，一天一兩次就好')
    if share(lambda t: len(DECIMAL.findall(t)) >= 1) > 0.3: out.append(f'帶小數的回覆 {share(lambda t: DECIMAL.search(t)):.0%}，超過三成：能取整就取整')
    # 2026-11-08 使用者：回覆要有深度、嚴謹、有態度、有觀點。「短回覆約三分之一」只看接話；回別人原創太短的另外列出來。
    F = [it['reply'] for it in R if it.get('kind') == 'followup']
    if len(F) >= 5 and sum(1 for t in F if len(t) <= 40) / len(F) < 0.25: out.append(f'接話裡一行就好的短回覆（40 字內）只有 {sum(1 for t in F if len(t) <= 40) / len(F):.0%}，閒聊可以更短')
    thin = [it['n'] for it in R if it.get('kind') != 'followup' and it.get('mode') != 'quote' and len(it['reply'].strip().split('\n')) < 2]
    if thin: out.append(f'回別人原創只有一行：{thin}，看看有沒有接到對方的核心論點、有沒有自己的判斷（voice.md「回覆要有深度、嚴謹、有態度、有觀點」）')
    q = share(lambda t: QEND.search(t))
    if q > 0.3: out.append(f'問句收尾 {q:.0%}：只在真的想知道時問')
    if share(lambda t: re.search(r'[。.]\s*$', t)) > 0.5: out.append('超過一半句尾有句號：手機上打字通常不加')
    for it in items:   # 2026-11-06：長貼文那套逐句提醒，回覆和引用也跑
        if it.get('status') == 'skip': continue
        for k in ('reply', 'quote'):
            if it.get(k): out += sentence_notes(f'#{it["n"]} {"回覆" if k == "reply" else "引用"}', it[k])
    known = known_accounts()   # 2026-11-06：熟帳號三成、新帳號七成（接續對話不算）
    rp = [it for it in R if it.get('kind') != 'followup' and it.get('mode') != 'quote' and it.get('status') == 'send']   # 可選的不算
    kn = [it['author'] for it in rp if it.get('author', '').lower() in known]
    if rp and len(kn) / len(rp) > 0.4: out.append(f'熟帳號 {len(kn)}/{len(rp)} 則（{", ".join(kn)}）：一天 2–3 則就好，其餘回新帳號')
    im = sum(1 for it in R if it.get('image')) / n
    if im > 0.5: out.append(f'配圖 {im:.0%}：只有圖本身就是重點時才配')
    SITE = {'rpl': 'onchain #c-rpl', 'sec': 'onchain #c-sec', 'ad': 'flows #c-ad', 'lthloss': 'onchain #c-lthloss', 'bands': 'onchain #c-sthband',
            'sopr': 'onchain #c-sopr', 'agecost': 'cycle #c-agecost', 'etf': 'flows #c-etf', 'cbp': 'flows #c-pr-us', 'liq': 'deriv #c-liq'}   # 2026-11-07：網站有的圖優先用原圖；2026-11-08 表觀需求搬到資金版（手機寬度截圖只畫目前那一版，版面要寫對）
    for it in R:
        c = (it.get('image') or {}).get('chart')
        if c in SITE: out.append(f'#{it["n"]} 配圖用 cards.py 的 {c}，網站有原圖（{SITE[c]}）：改成 site_cards.py')
    heads = {}
    for it in R: heads.setdefault(it['reply'][:3].lower(), []).append(it['n'])
    dup = {k: v for k, v in heads.items() if len(v) >= 3}
    if dup: out.append(f'開頭重複：{dup}')
    return out


def check_flash():
    """data/flash.json（發文小幫手的快訊）：欄位、文字、配圖檔。檔案不存在就略過。"""
    p = os.path.join(ROOT, 'data', 'flash.json')
    if not os.path.exists(p): return []
    F = json.load(open(p, encoding='utf-8')); err = []; ids = set()
    for it in F.get('items', []):
        tag = f'快訊 {it.get("id")}'
        err += [f'{tag} 缺少 {k}' for k in ('id', 'time', 'title') if not it.get(k)]
        if it.get('id') in ids: err.append(f'{tag} id 重複')
        ids.add(it.get('id'))
        if not (it.get('zh') or it.get('en')): err.append(f'{tag} 中英文至少要有一則')
        for lang in ('zh', 'en'):
            if not it.get(lang): continue
            err += [e for e in text_errors(f'{tag} {lang}', it[lang], lang) if '太機械' not in e]
            if not HASH.search(it[lang]): err.append(f'{tag} {lang} 結尾要帶 hashtag 關鍵詞')
            if it.get('image') and not os.path.exists(os.path.join(ROOT, 'data', 'flash', f'{it["id"]}-{lang}.png')):
                err.append(f'{tag} 有 image 但 data/flash/{it["id"]}-{lang}.png 不存在（先跑 ops/post/flash.py）')
    return err


if __name__ == '__main__':
    e = check()
    print('\n'.join(e) if e else 'replies.json OK')
    tn = tone_notes(json.load(open(os.path.join(ROOT, 'data', 'replies.json'), encoding='utf-8')).get('items', []))
    if tn: print('AI 腔提醒（不擋，排在一起看）：\n- ' + '\n- '.join(tn))
    le, ln = check_longposts()
    if le: print('長貼文（要修，但不影響回覆的檢查結果；已發出的就留著，隔天清掉）：\n- ' + '\n- '.join(le))
    if ln: print('長貼文逐句提醒（不擋，見 voice.md AI 腔清單）：\n- ' + '\n- '.join(ln))
    sys.exit(1 if e else 0)
