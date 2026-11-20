# -*- coding: utf-8 -*-
"""GEO（讓 ChatGPT、Perplexity、Claude、Google AI 摘要讀得到、引用得到 Daybreak）。2026-11-20 新增，使用者：「先做第一批」。
AI 爬蟲（GPTBot、ClaudeBot、PerplexityBot）不跑 JavaScript：改之前首頁只抓得到 34 個字、/app/ 只有頭條和摘要，一百多張圖的判讀都看不到。
這支在 pipeline/next/build.py 和 pipeline/intro/build.py 都跑完之後接著跑，讀它們剛寫好的 data/next*.js，寫出：
  app/index.html  <!--STATIC--> 換成當期的完整文字版（頭條、摘要、六個問題的結論、每張圖的名稱／表態／理由／資料來源，中英各一份）；
                  <!--LDJSON--> 換成結構化資料（WebPage＋Dataset＋當期簡報 Article，dateModified＝當期日期）
  index.html      介紹頁同樣兩個記號：Daybreak 是什麼、誰做的、怎麼做、今天的結論（給不跑 JS 的讀者），和 WebSite＋Person 結構化資料
  llms.txt        給 AI 的網站說明（llmstxt.org 的格式）
  latest.md       當期完整判讀的 Markdown 版（中文）；latest.en.md 英文版
文字版在頁面跑起來時立刻藏起來（緊接在後面的 script），畫面上看到的還是互動版。
署名一律只用「Aron」（使用者的公開名稱規則），不放其他名字或帳號。
用法：python3 pipeline/next/geo.py（build.py 最後會呼叫；失敗只印出來，頁面照常上線，只是少了這些）"""
import json, glob, os, html, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
SITE = 'https://daybreak.aronlab.dev/'
D_ = lambda *p: os.path.join(REPO, 'data', *p)
esc = html.escape
_MON = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def ld(path):
    s = open(path, encoding='utf-8').read()
    return json.loads(s[s.index('=') + 1:s.rindex('}') + 1])


NX = ld(D_('next.js'))
CHS = NX['site']['chapters']
PAGES = {c['id']: c.get('groups') or [] for c in CHS}
for f in glob.glob(D_('next-*.js')):
    t = open(f, encoding='utf-8').read()
    PAGES[t[t.index('["') + 2:t.index('"]')]] = json.loads(t[t.index(']=') + 2:].rstrip().rstrip(';'))
LEANS = json.load(open(D_('leans.json'), encoding='utf-8')).get('today', {})
try:
    EN = json.load(open(D_('notes.en.json'), encoding='utf-8'))
except Exception:
    EN = {}
if EN.get('date') != NX.get('date'):
    EN = {}
DATE = NX['date']; ED = NX.get('issue')
TODAY = next((c for c in CHS if c['id'] == 'today'), {})
BR = TODAY.get('brief') or {}
ST = NX.get('stance') or {}; STE = EN.get('stance') or {}
QS = [c for c in CHS if c['id'] != 'today' and not c.get('todo')]   # 六個問題（週期、價位、賣壓、買盤、槓桿、出場）
TN = {'up': ('偏多', 'Bullish'), 'down': ('偏空', 'Bearish'), 'neu': ('中性', 'Neutral'), 'warn': ('留意', 'Watch')}


def charts(pid):
    for g in PAGES.get(pid) or []:
        for c in g.get('charts') or []:
            yield c


ALL = [c for q in QS for c in charts(q['id'])]
# 張數和表態統計和介紹頁（pipeline/intro/build.py）同一個算法：所有頁的圖都算，包括「今天」頁那六張問題卡，對外只有一個數字
ANY = [c for p in PAGES for c in charts(p)]
NCH = len(ANY)
TALLY = {k: sum(1 for c in ANY if LEANS.get(c['k']) == k) for k in ('up', 'down', 'neu')}
DZH = '%d/%d/%d' % (int(DATE[:4]), int(DATE[5:7]), int(DATE[8:10]))
DEN = '%s %d, %s' % (_MON[int(DATE[5:7]) - 1], int(DATE[8:10]), DATE[:4])
PRICE = NX.get('price'); CHG = NX.get('chg')
HE = BR.get('he') if EN else ''; SE = BR.get('se') if EN else ''


def read(c, en):
    """一張圖的一句話：卡片自己的表態句（say.sz／se，已經以「偏空：」開頭），沒有就用表態＋圖在說什麼"""
    s = (c.get('say') or {}).get('se' if en else 'sz') or ''
    lab = TN.get(LEANS.get(c['k']), ('', ''))[1 if en else 0]
    if s:
        return s if (not lab or s.startswith(lab)) else '%s%s%s' % (lab, ': ' if en else '：', s)
    d = c.get('de' if en else 'dz') or ''
    return ('%s%s%s' % (lab, ': ' if en else '：', d)) if lab else d


def tally(en):
    n = NCH - sum(TALLY.values())   # 沒有表態的是參考用的圖（出場框架、今天頁的問題卡等）
    if en: return '%d charts. Today: %d bullish, %d bearish, %d neutral%s.' % (NCH, TALLY['up'], TALLY['down'], TALLY['neu'], ', %d reference charts without a lean' % n if n else '')
    return '%d 張圖。今天偏多 %d、偏空 %d、中性 %d%s。' % (NCH, TALLY['up'], TALLY['down'], TALLY['neu'], '，另外 %d 張是不表態的參考圖' % n if n else '')


def name(c, en):
    return (c.get('en') if en else c.get('zh')) or c.get('zh') or c['k']


INTRO_ZH = ('Daybreak 是 Aron 做的免費比特幣每日判讀。每天台北時間早上 08:30 前更新，用 %d 張自建與公開的指標，從鏈上、價格結構、衍生品、資金流、宏觀情緒拆開比特幣，'
            '回答六個問題：%s每張圖都表態偏多、偏空或中性，並寫出理由。數字由程式計算，AI 只負責解釋，不計算也不做決定；不給交易建議。') % (NCH, ''.join(q['qz'] + '？' for q in QS))   # 問題本身有頓號（誰在買、錢從哪裡來），用問號隔開
INTRO_EN = ('Daybreak is a free daily Bitcoin brief built by Aron. It updates every morning before 08:30 Taipei time, reading %d original and public indicators across on-chain data, '
            'price structure, derivatives, fund flows and macro sentiment to answer six questions: %s. Every chart takes a side (bullish, bearish or neutral) and says why. '
            'Code computes every number; AI only explains them, it does not calculate or decide. Daybreak makes no trade calls.') % (NCH, '; '.join(q['qe'] for q in QS))


# ---------- 文字版（給不跑 JS 的爬蟲） ----------
def _sec_html(en):
    L = 'en' if en else 'zh-Hant'
    h = ['<section lang="%s">' % L]
    if en:
        h.append('<h2>%s close edition, No.%s</h2>' % (DEN, ED))
        if HE: h.append('<p><strong>%s</strong></p><p>%s</p>' % (esc(HE), esc(SE)))
        if STE.get('label'): h.append('<p>Overall: %s</p>' % esc(STE['label']))
    else:
        h.append('<h2>%s 收盤版 No.%s</h2><p><strong>%s</strong></p><p>%s</p>' % (DZH, ED, esc(BR.get('hz') or NX.get('headline') or ''), esc(BR.get('sz') or NX.get('summary') or '')))
        if ST.get('label'): h.append('<p>整體：%s</p>' % esc(ST['label']))
    if PRICE: h.append('<p>%s $%s (%+.1f%%)</p>' % ('BTC close' if en else 'BTC 收盤', format(PRICE, ','), CHG or 0))
    for q in QS:
        lead = q.get('lead_en' if en else 'lead_zh') or ''
        if en and not EN: lead = ''
        h.append('<section><h3>%s: %s</h3>' % (esc(q['en']), esc(q['qe'])) if en else '<section><h3>%s：%s</h3>' % (esc(q['zh']), esc(q['qz'])))
        if lead: h.append('<p>%s</p>' % esc(lead))
        pts = q.get('points_en' if en else 'points_zh') or []
        if pts and (EN or not en): h.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % esc(p) for p in pts))
        li = []
        for c in charts(q['id']):
            src = c.get('srce' if en else 'src') or ''
            li.append('<li><strong>%s</strong>%s：%s%s</li>' % (esc(name(c, en)), '' if en else '（%s）' % esc(c.get('en') or ''), esc(read(c, en)), (' <small>%s</small>' % esc(src)) if src else '')
                      if not en else '<li><strong>%s</strong>: %s%s</li>' % (esc(name(c, en)), esc(read(c, en)), (' <small>%s</small>' % esc(src)) if src else ''))
        h.append('<ul>%s</ul></section>' % ''.join(li))
    h.append('</section>')
    return ''.join(h)


def static_app():
    return ('<main id="oc-static"><h1>Daybreak · 比特幣每日判讀 · Daily Bitcoin brief</h1><p lang="zh-Hant">%s</p><p lang="en">%s</p>' % (esc(INTRO_ZH), esc(INTRO_EN))
            + _sec_html(False) + _sec_html(True)
            + '<p><a href="../?intro">Daybreak 是什麼 · What is Daybreak</a> · <a href="../case-study/">Case study</a> · <a href="../latest.md">latest.md</a> · <a href="../latest.en.md">latest.en.md</a></p></main>')


def static_intro():
    tz, te = tally(False), tally(True)
    h = ['<main id="seo-static"><h1>Daybreak · 比特幣多維判讀 · Bitcoin, read across every dimension</h1>',
         '<section lang="en"><p>%s</p>' % esc(INTRO_EN),
         '<h2>The six questions</h2><ul>%s</ul>' % ''.join('<li><a href="app/#%s">%s</a>: %s</li>' % (q['id'], esc(q['en']), esc(q['qe'])) for q in QS)]
    if HE: h.append('<h2>Latest: %s close, No.%s</h2><p><strong>%s</strong></p><p>%s</p>' % (DEN, ED, esc(HE), esc(SE)))
    h.append('<p>%s</p></section>' % te)
    h += ['<section lang="zh-Hant"><p>%s</p>' % esc(INTRO_ZH),
          '<h2>六個問題</h2><ul>%s</ul>' % ''.join('<li><a href="app/#%s">%s</a>：%s</li>' % (q['id'], esc(q['zh']), esc(q['qz'])) for q in QS),
          '<h2>最新一期：%s 收盤版 No.%s</h2><p><strong>%s</strong></p><p>%s</p><p>%s</p></section>' % (DZH, ED, esc(BR.get('hz') or ''), esc(BR.get('sz') or ''), tz),
          '<p><a href="app/">Open Daybreak · 打開 Daybreak</a> · <a href="case-study/">Case study</a> · <a href="llms.txt">llms.txt</a> · <a href="latest.md">latest.md</a> · <a href="latest.en.md">latest.en.md</a></p></main>']
    return ''.join(h)


# ---------- 結構化資料 ----------
PERSON = {'@type': 'Person', '@id': 'https://aronlab.dev/#aron', 'name': 'Aron', 'url': 'https://aronlab.dev/'}
WEBSITE = {'@type': 'WebSite', '@id': SITE + '#site', 'name': 'Daybreak', 'alternateName': ['Daybreak 比特幣多維判讀', 'Daybreak Bitcoin brief'], 'url': SITE,
           'inLanguage': ['zh-Hant', 'en'], 'description': INTRO_EN, 'creator': {'@id': PERSON['@id']}, 'publisher': {'@id': PERSON['@id']}}


def _ld(graph):
    s = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, separators=(',', ':'))
    return '<script type="application/ld+json">%s</script>' % s.replace('</', '<\\/')


def ld_intro():
    return _ld([WEBSITE, PERSON])


def ld_app():
    g = [WEBSITE, PERSON,
         {'@type': 'WebPage', '@id': SITE + 'app/#page', 'url': SITE + 'app/', 'name': 'Daybreak · The first Bitcoin brief of the morning', 'isPartOf': {'@id': WEBSITE['@id']},
          'inLanguage': ['zh-Hant', 'en'], 'dateModified': DATE, 'about': {'@type': 'Thing', 'name': 'Bitcoin', 'sameAs': 'https://en.wikipedia.org/wiki/Bitcoin'},
          'author': {'@id': PERSON['@id']}, 'mainEntity': {'@id': SITE + 'app/#data'}},
         {'@type': 'Dataset', '@id': SITE + 'app/#data', 'name': 'Daybreak Bitcoin indicators', 'url': SITE + 'app/',
          'description': 'Daily readings of %d Bitcoin indicators (on-chain, price structure, derivatives, fund flows, macro sentiment), each marked bullish, bearish or neutral with a reason. Updated every day.' % NCH,
          'creator': {'@id': PERSON['@id']}, 'dateModified': DATE, 'isAccessibleForFree': True, 'temporalCoverage': '2013-01-01/' + DATE,
          'variableMeasured': [c.get('en') or c['k'] for c in ALL]},
         {'@type': 'Article', '@id': SITE + 'app/#brief-zh', 'headline': BR.get('hz') or NX.get('headline'), 'description': BR.get('sz') or NX.get('summary'), 'inLanguage': 'zh-Hant',
          'datePublished': DATE, 'dateModified': DATE, 'author': {'@id': PERSON['@id']}, 'publisher': {'@id': PERSON['@id']}, 'isPartOf': {'@id': SITE + 'app/#page'}, 'url': SITE + 'app/?lang=zh'}]
    if HE:
        g.append({'@type': 'Article', '@id': SITE + 'app/#brief-en', 'headline': HE, 'description': SE, 'inLanguage': 'en', 'datePublished': DATE, 'dateModified': DATE,
                  'author': {'@id': PERSON['@id']}, 'publisher': {'@id': PERSON['@id']}, 'isPartOf': {'@id': SITE + 'app/#page'}, 'url': SITE + 'app/?lang=en'})
    return _ld(g)


# ---------- Markdown ----------
def md(en):
    o = []
    if en:
        o += ['# Daybreak · %s close edition, No.%s' % (DEN, ED), '', '> ' + INTRO_EN, '', 'Source: %sapp/?lang=en · by Aron · updated %s' % (SITE, DATE), '']
        if HE: o += ['## Headline', '', '**%s**' % HE, '', SE, '']
        if STE.get('label'): o += ['Overall: %s' % STE['label'], '']
    else:
        o += ['# Daybreak · %s 收盤版 No.%s' % (DZH, ED), '', '> ' + INTRO_ZH, '', '來源：%sapp/?lang=zh · Aron · 更新 %s' % (SITE, DATE), '',
              '## 頭條', '', '**%s**' % (BR.get('hz') or ''), '', BR.get('sz') or '', '']
        if ST.get('label'): o += ['整體：%s' % ST['label'], '']
    if PRICE: o += ['%s $%s (%+.1f%%)' % ('BTC close' if en else 'BTC 收盤', format(PRICE, ','), CHG or 0), '']
    o += [tally(en), '']
    for q in QS:
        o += ['## %s: %s' % (q['en'], q['qe']) if en else '## %s：%s' % (q['zh'], q['qz']), '']
        lead = q.get('lead_en' if en else 'lead_zh') or ''
        if lead and (EN or not en): o += [lead, '']
        pts = q.get('points_en' if en else 'points_zh') or []
        if pts and (EN or not en): o += ['- ' + p for p in pts] + ['']
        for c in charts(q['id']):
            src = c.get('srce' if en else 'src') or ''
            o += ['### %s' % name(c, en) + ('' if en else '（%s）' % (c.get('en') or '')), '', read(c, en), '']
            d = c.get('de' if en else 'dz') or ''
            if d and (c.get('say') or {}).get('se' if en else 'sz'): o += [('What it shows: ' if en else '這張圖：') + d, '']
            if src: o += [('Source: ' if en else '資料來源：') + src, '']
    o += ['---', '', 'Daybreak makes no trade calls. Readings are for information only.' if en else 'Daybreak 不給交易建議，判讀僅供參考。', '']
    return '\n'.join(o)


def llms():
    o = ['# Daybreak', '', '> ' + INTRO_EN, '', INTRO_ZH, '',
         'Built and maintained by Aron (Aron Lab, https://aronlab.dev/). Bilingual: Traditional Chinese and English. Latest edition: %s close, No.%s.' % (DEN, ED), '',
         '## Latest reading', '']
    if HE: o += ['%s — %s' % (HE, SE), '']
    o += ['- [Full latest reading, English (Markdown)](%slatest.en.md): headline, six questions, every chart with its lean, reason and source' % SITE,
          '- [完整最新判讀，中文（Markdown）](%slatest.md)' % SITE, '',
          '## Pages', '',
          '- [Daybreak app](%sapp/): the daily brief and all %d charts, interactive (needs JavaScript); add ?lang=en or ?lang=zh' % (SITE, NCH)]
    o += ['- [%s](%sapp/#%s): %s' % (q['en'], SITE, q['id'], q['qe']) for q in QS]
    o += ['- [Case study](%scase-study/en/): how Daybreak was designed and built, and how it checks its own calls (中文版：%scase-study/)' % (SITE, SITE), '',
          '## Method', '',
          '- Data: free public sources (Bitview, CheckOnChain, CoinMetrics, Coinalyze, Binance, OKX, Deribit, Coinbase, Kraken, DefiLlama, FRED and others); each chart names its source and date.',
          '- Code computes every number and every rule. AI writes the daily explanation from those numbers; it does not calculate and does not decide.',
          '- Every chart is marked bullish, bearish or neutral with a one-line reason. The site makes no trade calls.', '',
          '## Optional', '',
          '- [Sitemap](%ssitemap.xml)' % SITE, '']
    return '\n'.join(o)


def put(path, marks):
    p = os.path.join(REPO, path); s = open(p, encoding='utf-8').read()
    for k, v in marks.items():
        assert s.count(k) == 1, (path, k, s.count(k))
        s = s.replace(k, v)
    open(p, 'w', encoding='utf-8').write(s)
    return len(s)


if __name__ == '__main__':
    a = put(os.path.join('app', 'index.html'), {'<!--STATIC-->': static_app(), '<!--LDJSON-->': ld_app()})
    b = put('index.html', {'<!--STATIC-->': static_intro(), '<!--LDJSON-->': ld_intro()})
    for fn, s in (('llms.txt', llms()), ('latest.md', md(False)), ('latest.en.md', md(True))):
        open(os.path.join(REPO, fn), 'w', encoding='utf-8').write(s)
    print('geo: %d charts (%s) | app/index.html %d bytes, index.html %d bytes | llms.txt, latest.md, latest.en.md written | en %s' % (NCH, TALLY, a, b, bool(EN)))
