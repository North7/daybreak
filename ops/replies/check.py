#!/usr/bin/env python3
"""檢查 data/replies.json（2026-11-04 建立）：欄位齊全、語言對（英文貼文回英文、中文貼文回繁體中文、其他語言跳過）、
X 字數 280 以內、不談出場框架、配圖檔存在、數據日期是當期。有錯就以非零結束。
用法（在倉庫根目錄）：python3 ops/replies/check.py"""
import json, os, re, sys
from collections import Counter
from statistics import mean, pstdev

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
# AI 腔（2026-11-05 研究後訂，見 ops/brand/voice.md「真人說話，不要 AI 腔」）：一出現就擋；2026-11-09 加「我會說是／不會叫它／再說它／得先看到／我會把…看成／先講清楚」（替判斷貼標籤的翻譯腔）和「什麼情況代表我看錯／最後提醒一下」（每篇都有的模板句）
# 2026-11-09 使用者：「我這邊數據」「我這邊算的」「on my end」這類自稱很 AI，一律不用，直接講數字
# 2026-11-09 使用者：開頭「看了一圈，現在找不到誰在接」像是能力不夠找不到，誰還要往下看；要講的是「現在真的沒人接」。
# 2026-11-09 使用者：「不能說看錯，另外什麼是照舊走，舊是怎麼走的，不照舊會怎麼走，直接說出來」。
# 2026-11-09 使用者改稿：同意對方不用說出來、不幫對方核對數字（n60「我很同意」、n45「這句我同意」「跟你寫的 73,150 對得上」、n47「我是佩服的」都被刪）
AI_WORDS = re.compile(r'我很同意|這句我同意|這點我同意|我是佩服|跟你寫的[^，。\n]{0,12}對得上|看錯|照舊走|照舊在走|could be wrong|I\'m wrong|I was wrong|找不到誰|找不到有誰|看了一圈|我找不到|我沒找到|nobody I can find|I can\'t find any|我這邊|我们这边|我們這邊|我算(的|在|出來|到)|算出來是|新手|老手|新買家|老買家|短線的人|值得注意的是|值得一提|整體而言|總的來說|總而言之|綜上|我的(看法|判斷|結論)是|所以我的判斷|什麼情況會讓我改看法|會讓我改看法|我會說(是|它)|(不會|會)叫它|再說它|(得|要)先看到|我會把[^，。\n]{1,20}看成|先講清楚|什麼情況代表我看錯|最後提醒一下|說白了|說穿了|先說結論|結論先講|首先[，,].{0,40}其次|不僅僅?是|而且老實說|說到底|這就是全部|'
                      r'\b(delve|crucial|pivotal|underscores?|testament|tapestry|showcases?|Additionally|Moreover|Furthermore|'
                      r"on (my|our) end|on my side|by my (math|count|numbers|estimate)|my estimate (puts|is|has)|Here's the thing|That's the whole story|Fun (fact|detail)|No fluff|Let that sink in|"
                      # 2026-11-09 第二輪（voice.md「去 AI 味第二輪」）：泛指來源、過度禮貌、固定收尾、淺層分析尾句、書面填充詞、英文套話
                      r"Lots of people|Many people|Some say|A lot of people (are )?(saying|think)|The reality is|Let's be (clear|honest)|To be clear|At the end of the day|bottom line|In other words|Think of it (as|this way)|key takeaway|game.?changers?|not a forecast|"
                      r"Great (point|post|thread|analysis|chart|call)|Well said|Spot on|Nice (breakdown|work|chart|call)|Thanks for sharing|Love this)\b|"
                      r'很多人說|不少人說|大家都說|某種程度|一定程度上|本質上|換句話說|不難發現|毋庸置疑|顯而易見|凸顯了?|彰顯|體現了|只能當個?參考|說得好|好文|感謝分享|謝謝分享|受教了|學到了|兩堆|分堆|幾堆|那堆|這堆|第[一二三]堆|——|—', re.I)   # 2026-11-09 使用者：「分成兩堆，沒人會用堆來形容」→ 分類寫「兩種走法」；「一堆多單」這種量詞不擋
# 只提醒、不擋：一天裡出現太多次才是問題
CONTRAST = re.compile(r'不是[^，。？\n]{1,24}[，,、 ]?(而)?是|不等於|\bnot (just |only )?an? [^,.]{1,30}, (but )?|, not an? |isn\'t [^,.]{1,30}[,.] it\'s|rather than', re.I)
DECIMAL = re.compile(r'\d\.\d')
QEND = re.compile(r'[？?]\s*$')
# 2026-11-06 依 @lieflat_3 配對實測（voice.md AI 腔清單）：逐句提醒、不擋
LIST3 = re.compile(r'[^，。！？；：\n]*、[^，。！？；：\n]*、[^，。！？；：\n]*')        # 一個分句裡兩個以上頓號
PREMOD = re.compile(r'[^，。！？；：\n、]{16,}的[^，。！？；：\n、的]{1,6}(?=[，。！？；\n]|$)|的[^，。！？；：\n]{0,8}的[^，。！？；：\n]{0,8}的')  # 過長前置定語／連著三個「的」
SHELL = re.compile(r'對於[^，。]{1,15}(來說|而言)|就[^，。]{1,10}而言|當[^，。]{2,20}時，|(^|\n)(然而|因此|此外)，')
# 2026-11-09 第二輪：焦點後置／假分裂句（Claude 指紋，lieflat +0.47）：新資訊吊到句尾。直接講後面那件事，一篇最多一次
FOCUS = re.compile(r'(分辨的方法|要盯的|要看的|要注意的|真正的(問題|差別|重點)|的原因)是|What(\'s| is) (missing|different|new|changed|interesting) is|The (tell|catch|difference|problem|key|messy part|tricky part|short version) is', re.I)
# 固定收尾段「這週看兩件事：」連續幾篇都有就是模板（voice.md 第二輪）
CLOSER = re.compile(r'[這本]週[先]?看[兩三幾]件事|[Tt]wo things to watch|things to watch this week|What (I\'m|to) watch(ing)? this week')
# 長貼文有沒有講「對交易來說這代表什麼」（voice.md「要有交易上的意義」2026-11-09）：歷史對照基準、什麼翻過去讀法就換、風險偏哪邊、交易心理。沒看到只提醒。
TRADE = re.compile(r'隨便挑|任一天|隨機|跟.{0,6}天差不多|\d+ ?(次|段|回).{0,30}(之後|後).{0,30}(漲|跌|高|低)|站回|站穩|翻回|跌破|突破|翻過|翻負|讀法|分辨|反過來|改(變|看)(判斷|想法|看法)|改變.{0,4}判斷|不成立|就(是|代表|不是).{0,10}(底|頂|訊號|方向)|風險偏|比較擠|是空的|沒.{0,4}墊|雜訊|'
                   r'random day|any (given|random) day|\d+ (times|cases|crossings)|out of \d+|would mean|tell (the two|them) apart|change my mind|lopsided|the (risk|downside|upside) is|is noise|reclaim|back above|breaks? (below|above)|below it|above it', re.I)


def sentence_notes(tag, t):
    """單篇文字的逐句提醒（長貼文、快訊、回覆共用）：頓號罗列、前置定語、話題殼／句首路標、相鄰三句同款開頭。"""
    out = [f'{tag} 頓號罗列：「{m.group(0).strip()[:40]}」' for m in LIST3.finditer(t)]
    out += [f'{tag} 前置定語太長：「{m.group(0)[:40]}」' for m in PREMOD.finditer(t) if '是' not in m.group(0)]   # 「……是……的底」是謂語，不是前置定語
    out += [f'{tag} 話題殼／句首路標：「{m.group(0).strip()[:30]}」' for m in SHELL.finditer(t)]
    out += [f'{tag} 焦點後置（「{m.group(0)}」）：直接講後面那件事（voice.md 2026-11-09 第二輪）' for m in FOCUS.finditer(t)]
    s = [x.strip() for x in re.split(r'[。！？\n]', t) if len(x.strip()) >= 6]
    for i in range(len(s) - 2):
        if s[i][:2] == s[i + 1][:2] == s[i + 2][:2]: out.append(f'{tag} 連三句同款開頭：「{s[i][:12]}…」')
    return out


def longpost_notes(tag, t, lang):
    """單篇長貼文的結構提醒（不擋，voice.md「去 AI 味第二輪」2026-11-09）：小標數、段落長度都一樣、對比句、每段短句收尾。
    lieflat 配對實測：人寫的長文一篇 0–1 個小標（AI 1.26 個／千字）、段落長度 CV 人類 0.83（AI 0.31）、「不是 A 而是 B」人類 0.22 次／千字（AI 0.94）。"""
    body = re.sub(r'（數據：[^）]*）|\(Data:[^)]*\)|#\S+|https?://\S+', '', t)
    paras = [p.strip() for p in body.split('\n') if p.strip()][1:]   # 第一行是標題
    heads = [p for p in paras if len(p) <= (22 if lang == 'zh' else 60) and not re.search(r'[。）)!?.]$|\d[KkMm%]?$', p)]
    out = []
    if len(heads) > 3: out.append(f'{tag} 小標 {len(heads)} 個（{"／".join(h[:10] for h in heads[:4])}…）：人寫的長文一篇 0–1 個，最多留 3 個，其餘併進段落第一句')
    pl = [len(p) for p in paras if p not in heads]
    if len(pl) >= 4 and pstdev(pl) / mean(pl) < 0.3: out.append(f'{tag} 段落長度都差不多（{min(pl)}–{max(pl)} 字）：併一段長的、留一段短的，不要為了參差硬拆')
    c = len(CONTRAST.findall(body))
    if c > 1: out.append(f'{tag} 對比句（不是 X 是 Y／not X）{c} 處：一篇最多 1 處')
    short = 0
    for p in paras:
        if p in heads: continue
        ss = [x.strip() for x in re.split(r'[。！？.!?]', p) if x.strip()]
        if len(ss) >= 3 and len(ss[-1]) <= (10 if lang == 'zh' else 30): short += 1
    if short > 2: out.append(f'{tag} {short} 段都用一句短的收尾：一篇一兩處就好，其他段用數字或細節收')
    if not TRADE.search(body): out.append(f'{tag} 沒看到「對交易來說這代表什麼」的句子：是不是訊號（跟隨便挑一天比，帶次數）、什麼價位／數字翻過去讀法就換、風險偏哪邊、哪種感覺是雜訊，挑一種寫（voice.md「要有交易上的意義」2026-11-09）')
    return out


def check_longposts():
    """data/longposts.json（長貼文）：AI 用語、簡體、框架用詞直接擋；逐句、結構提醒另外印。"""
    p = os.path.join(ROOT, 'data', 'longposts.json')
    if not os.path.exists(p): return [], []
    err, notes = [], []
    items = json.load(open(p, encoding='utf-8')).get('items', [])
    for it in items:
        for lang in ('zh', 'en'):
            t = it.get(lang)
            if not t: continue
            tag = f'長貼文 {it.get("id")} {lang}'
            if AI_WORDS.search(t): err.append(f'{tag} AI 腔（「{AI_WORDS.search(t).group(0)}」）')
            if BAN.search(t): err.append(f'{tag} 提到出場框架或買賣動作：{BAN.search(t).group(0)}')
            if lang == 'zh' and set(t) & SIMP: err.append(f'{tag} 有簡體字：{"".join(sorted(set(t) & SIMP))}')
            if lang == 'zh' and not it.get('posted') and EN_NAME.search(t): err.append(f'{tag} 有英文常用名的詞要用英文：' + '、'.join(sorted(set(EN_NAME.findall(t)))) + '（voice.md 用詞，2026-11-09）')
            notes += sentence_notes(tag, t)
            notes += longpost_notes(tag, t, lang)
    closers = [it.get('id') for it in items if CLOSER.search((it.get('zh') or '') + (it.get('en') or ''))]
    if len(closers) >= 2: notes.append(f'長貼文 {len(closers)} 篇都用「這週看幾件事」收尾：{closers}，連著幾篇就是模板，併進結論段或換個寫法')
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
        if t: err += [e for e in text_errors(tag + ' 回覆', t, it.get('lang')) if not (it.get('posted') and ('英文常用名' in e or 'AI 腔' in e))]   # 已發出的不用改（規則是發出之後才加的，2026-11-09）
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


# 2026-11-09 使用者：「以後文章比特幣就用 BTC，這種有英文的常用名詞就用英文，世界很少有人用中文比特幣，還有納斯達克這種詞」。hashtag（#比特幣）不算。
EN_NAMES = {'比特幣': 'BTC', '比特币': 'BTC', '以太坊': 'ETH', '以太幣': 'ETH', '那斯達克': 'Nasdaq', '納斯達克': 'Nasdaq', '標普': 'S&P 500',
            '輝達': 'Nvidia', '英偉達': 'Nvidia', '微策略': 'Strategy', '幣安': 'Binance', '貝萊德': 'BlackRock', '富達': 'Fidelity', '灰度': 'Grayscale'}
EN_NAME = re.compile(r'(?<!#)(' + '|'.join(EN_NAMES) + ')')


def text_errors(tag, t, lang, lim=280):
    """一段要發出去的文字：字數、語言、簡體字、框架用詞、機械開頭。"""
    err = []
    if weight(t) > lim: err.append(f'{tag} {weight(t)}/{lim}，超過')
    if lang == 'en' and CJK.search(t): err.append(f'{tag}：英文的文字裡有中文')
    if lang == 'zh':
        if not CJK.search(t): err.append(f'{tag}：中文要用繁體中文')
        s = sorted(set(t) & SIMP)
        if s: err.append(f'{tag} 有簡體字：{"".join(s)}')
    if lang == 'zh' and EN_NAME.search(t):
        w = sorted(set(EN_NAME.findall(t))); err.append(f'{tag} 有英文常用名的詞要用英文：' + '、'.join(f'{x}→{EN_NAMES[x]}' for x in w) + '（voice.md 用詞，2026-11-09）')
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
    # 2026-11-09 使用者：「回覆更是這樣，多說觀點和結論，數據少量支持就行，不然很像數據機器人」。日期（11/06、2025/10）、年份、網址、「200 日均線」「30 天」這種名稱不算數字。
    NUM = re.compile(r'(?<![\d/.])(?!(?:19|20)\d\d(?![\d,]))\d[\d,]*(?:\.\d+)?(?![\d/])(?!-day|-week| ?(?:日|週)均線| ?天)')   # 年份、200 日均線、30 天這種名稱不算
    many = [it['n'] for it in R if len(NUM.findall(re.sub(r'https?://\S+', '', it['reply']))) > 3]
    if many: out.append(f'數字超過 3 個：{many}，第一行先講判斷，數字留一兩個撐它就好（voice.md「觀點為主、數據為輔」）')
    q = share(lambda t: QEND.search(t))
    if q > 0.3: out.append(f'問句收尾 {q:.0%}：只在真的想知道時問')
    if share(lambda t: re.search(r'[。.]\s*$', t)) > 0.5: out.append('超過一半句尾有句號：手機上打字通常不加')
    # 2026-11-09 第二輪（voice.md「去 AI 味第二輪」）：11/08 禁掉附和開頭之後，第一行長出「X 是真的，但」這種讓步開頭（當天 26%）；第三行「所以」收結論（26%）；口頭禪；長度、行數太整齊
    CONCEDE = re.compile(r'是真的|沒錯|說得對|說得通|對得上|這點你|is real|isn\'t the only|isn\'t wrong|fair,? but|^(True|Fair)\b|\bthough$', re.I)
    cc = [it['n'] for it in R if CONCEDE.search(it['reply'].strip().split('\n')[0])]
    if len(cc) > max(2, n // 6): out.append(f'第一行讓步開頭（是真的，但／沒錯／說得對／isn\'t the only／though）{len(cc)} 則：{cc}，一天兩三則就好，直接講不同意的點或新東西')
    so = [it['n'] for it in R if re.search(r'(^|\n)(所以|So\b)', it['reply'])]
    if len(so) > max(3, n // 5): out.append(f'有一行用「所以／So」開頭 {len(so)} 則：{so}，結論已經在第一行，最後一行放細節或留白')
    PET = {'比較像': 2, '真的': 3, '其實': 3, '我覺得': 3, 'to me': 2, 'though': 2, "I don't think": 2}
    pets = []
    for w, m in PET.items():
        k = sum(1 for it in R if re.search((r'\b' if w[0].isascii() else '') + re.escape(w) + (r'\b' if w[-1].isascii() else ''), it['reply']))
        if k > m: pets.append(f'{w} {k} 則')
    if pets: out.append('口頭禪：' + '、'.join(pets) + '，換著講（就是／八成／應該是／看起來像／my guess is／probably）')
    Z = [len(re.sub(r'\s', '', it['reply'])) for it in R if it.get('lang') == 'zh']
    if len(Z) >= 8 and pstdev(Z) / mean(Z) < 0.35: out.append(f'中文回覆長度太整齊（{min(Z)}–{max(Z)} 字，CV {pstdev(Z) / mean(Z):.2f}）：要有一行的、也有五行的')
    ln = Counter(len(it['reply'].strip().split('\n')) for it in R if it.get('kind') != 'followup')
    if ln and ln.most_common(1)[0][1] / sum(ln.values()) > 0.5: out.append(f'回原創的回覆 {ln.most_common(1)[0][1]}/{sum(ln.values())} 則都是 {ln.most_common(1)[0][0]} 行：行數要亂')
    for it in items:   # 2026-11-06：長貼文那套逐句提醒，回覆和引用也跑
        if it.get('status') == 'skip': continue
        for k in ('reply', 'quote'):
            if it.get(k): out += sentence_notes(f'#{it["n"]} {"回覆" if k == "reply" else "引用"}', it[k])
    known = known_accounts()   # 2026-11-06：熟帳號三成、新帳號七成（接續對話不算）
    rp = [it for it in R if it.get('kind') != 'followup' and it.get('mode') != 'quote' and it.get('status') == 'send']   # 可選的不算
    kn = [it['author'] for it in rp if it.get('author', '').lower() in known]
    if rp and len(kn) / len(rp) > 0.4: out.append(f'熟帳號 {len(kn)}/{len(rp)} 則（{", ".join(kn)}）：一天 2–3 則就好，其餘回新帳號')
    # 2026-11-09 晚上使用者同意（當天成效：3 萬粉以上互動率 0.07%、1k–3 萬粉 2.83%；69 則裡 39 則零互動）：一天 35–40 則、曝光型 1–2 則且配圖、引用最多 2 則
    live = [it for it in items if it.get('status') != 'skip']
    big = [it for it in live if it.get('kind') != 'followup' and it.get('mode') != 'quote' and (it.get('followers') or 0) >= 30000]
    if len(big) > 2: out.append(f'3 萬粉以上的回覆 {len(big)} 則（{", ".join("#" + str(it["n"]) for it in big)}）：一天 1–2 則就好，其餘回 1k–3 萬粉的博主')
    noimg = [it['n'] for it in big if not it.get('image')]
    if noimg: out.append(f'3 萬粉以上的回覆沒配圖：{noimg}，曝光型一律配網站圖（真的沒有就在 note 寫原因）')
    qn = [it['n'] for it in live if it.get('mode') == 'quote']
    if len(qn) > 2: out.append(f'引用 {len(qn)} 則：{qn}，一天最多 2 則')
    if len(live) > 40: out.append(f'今天已經 {len(live)} 則（不含按讚就好的）：一天 35–40 則，之後只做接話')
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
