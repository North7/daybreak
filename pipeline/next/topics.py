# -*- coding: utf-8 -*-
"""GEO 主題頁（2026-11-25，使用者：「幫我 GEO btc 鏈上數據與宏觀週期，BTC 指標數據，BTC 週期分析，BTC 數據分析」「BTC 鏈上數據分析」「以及其他相關關鍵字」）。
搜尋和 AI 會用這些詞找資料，網站原本只有「六個問題」的分法和一張張圖的單頁，沒有一頁正面回答「比特幣週期分析」「比特幣鏈上數據分析」這種題目。
每個主題一頁（中英各一），部署時由 pages.py 呼叫寫出（不進程式庫）：
  bitcoin-cycle/        比特幣週期分析（四年週期、減半、牛熊、見底了嗎、離頂多遠、鏈上數據與宏觀週期）
  bitcoin-onchain/      比特幣鏈上數據分析（持有者成本、MVRV／SOPR／NUPL、籌碼、大戶、交易所流量、礦工）
  bitcoin-macro/        比特幣宏觀分析（利率、美元、美股、流動性、穩定幣、ETF）
  bitcoin-etf/          比特幣 ETF 數據分析（2026-11-27 加：現貨 ETF 資金流、ETF 持有成本、上市公司、CME 機構、美國現貨溢價）
  bitcoin-derivatives/  比特幣衍生品數據（資金費率、未平倉、多空比、清算、選擇權）
  en/<同上>/           英文版
頁面由上往下：今天的結論 → 一段固定的說明 → 常見問題（答案是當天幾張圖的表態和理由，FAQPage 結構化資料）→ 相關圖分組列出（表態膠囊＋一句理由＋單頁連結）→ 其他主題。
版面和單頁同一套（pages.py 的 shell、CSS）；圖的清單照代號挑，某張圖改名或拿掉就自動略過，不會壞。
固定說明的文字照 aron-style 的中文文案規則寫（第一句就是內容，不自問自答，不用「不是 A，是 B」）。"""
import re
import geo
import hans as HANS   # 2026-11-25 簡體版：整頁轉換
from geo import esc, SITE, PERSON, WEBSITE, TN, LEANS

HUBS = [
    dict(id='bitcoin-cycle', ch='cycle',
         nz='週期分析', ne='Cycle analysis',
         h1z='比特幣週期分析：現在走到週期的哪裡', h1e='Bitcoin cycle analysis: where Bitcoin is in its cycle',
         kz='比特幣週期分析, BTC 週期分析, BTC 週期, 四年週期, 減半週期, 牛熊週期, 鏈上數據與宏觀週期, 比特幣抄底指標, 比特幣頂部指標',
         kh='比特币周期分析, BTC 周期, 比特币四年周期, 减半周期, 牛熊周期, 比特币抄底指标, 比特币逃顶指标, 比特币见底了吗',
         ke='Bitcoin cycle analysis, BTC cycle, four-year cycle, halving cycle, bull and bear market, cycle top indicators, cycle bottom indicators',
         iz='比特幣大約每四年走完一輪牛熊，時間和減半大致對得上，但每一輪的長短和漲跌幅都不一樣。這一頁把 Daybreak 跟週期有關的圖放在一起：現在是哪個階段、估值離歷來的底和頂多遠、頂部和底部指標各自怎麼說。每張圖每天用前一天的收盤更新，都寫出偏多、偏空或中性和理由。',
         ie='Bitcoin has moved through a bull and bear market roughly every four years, loosely in step with the halving, though each cycle has run a different length and size. This page gathers the Daybreak charts that track the cycle: which stage Bitcoin is in, how far valuation sits from past bottoms and tops, and what the top and bottom indicators say. Every chart updates daily from the previous close and is marked bullish, bearish or neutral with a reason.',
         secs=[('階段與熱度', 'Stage and heat', ['dawn', 'dawnc', 'stage', 'regime', 'regc', 'path', 'cyccmp', 'dd', 'long', 'mon', 'capeff']),
               ('估值：離歷來的底和頂多遠', 'Valuation: distance from past bottoms and tops', ['avgd', 'avgdc', 'hnupl', 'rup', 'aviv', 'rrisk', 'pl', 'p20', 'psx', 'cvdd', 'lthloss', 'npl365', 'agecost']),
               ('頂部指標', 'Top indicators', ['p6', 'p6v', 'radar', 'radarv', 'pi']),
               ('底部訊號', 'Bottom signals', ['tm', 'tmh', 'sx', 'vddm', 'hashr'])],
         faq=[('比特幣現在在週期的哪個位置？', 'Where is Bitcoin in its cycle right now?', ['dawn', 'stage', 'regime']),
              ('比特幣見底了嗎？底部指標怎麼說？', 'Has Bitcoin bottomed? What do the bottom indicators say?', ['tm', 'rup', 'lthloss', 'sx']),
              ('比特幣離週期頂部還有多遠？', 'How far is Bitcoin from a cycle top?', ['p20', 'pi', 'radar']),
              ('這一輪和前幾輪週期比起來如何？', 'How does this cycle compare with past cycles?', ['cyccmp', 'dd'])]),
    dict(id='bitcoin-onchain', ch=None,
         nz='鏈上數據分析', ne='On-chain analysis',
         h1z='比特幣鏈上數據分析：持有者成本、獲利與籌碼', h1e='Bitcoin on-chain data analysis: holder cost, profit and supply',
         kz='比特幣鏈上數據分析, 比特幣鏈上分析, BTC 鏈上分析, BTC 鏈上數據, 鏈上指標, MVRV, SOPR, NUPL, 已實現價格, 短期持有者成本, 長期持有者, 籌碼分布, 大戶, 交易所淨流量',
         kh='比特币链上数据分析, 比特币链上分析, BTC 链上数据, 链上指标, MVRV, SOPR, NUPL, 已实现价格, 短期持有者成本, 长期持有者, 筹码分布, 巨鲸, 交易所净流入',
         ke='Bitcoin on-chain analysis, BTC on-chain data, on-chain indicators, MVRV, SOPR, NUPL, realized price, short-term holder cost basis, long-term holders, URPD, whales, exchange netflow',
         iz='比特幣鏈上分析看的是比特幣在區塊鏈上的實際移動：每一枚幣上次換手的價格、誰拿著、拿了多久、賣出時是賺是賠。這一頁把 Daybreak 的鏈上圖分成四組：持有者成本與籌碼、獲利與虧損、持有者在做什麼、礦工。資料主要來自 Bitview、CheckOnChain 和 CoinMetrics，每張圖每天更新，都寫出表態和理由。',
         ie='On-chain data tracks how bitcoin actually moves on the blockchain: the price each coin last changed hands at, who holds it, for how long, and whether it was sold at a profit or a loss. This page groups the Daybreak on-chain charts into holder cost and supply, profit and loss, what holders are doing, and miners. Data comes mainly from Bitview, CheckOnChain and CoinMetrics; every chart updates daily and is marked bullish, bearish or neutral with a reason.',
         secs=[('持有者成本與籌碼', 'Holder cost and supply', ['levels', 'sthgap', 'quant', 'floors', 'tiercost', 'urpd', 'urpdchg', 'cohort', 'conc', 'pnlb']),
               ('獲利與虧損：MVRV、SOPR、NUPL', 'Profit and loss: MVRV, SOPR, NUPL', ['hnupl', 'rup', 'p20', 'profit', 'psx', 'sopr', 'soprf', 'pnlr', 'npl', 'npl365', 'rpl', 'rloss', 'lthrl', 'agepl', 'sthsig']),
               ('持有者在做什麼：長短期、大戶、交易所', 'What holders are doing: long vs short term, whales, exchanges', ['lthnet', 'lsrchg', 'sthd', 'oldc', 'vddm', 'dorm', 'supliq', 'whale', 'whalet', 'whstrip', 'exflow', 'exch', 'mom', 'conf', 'ssr', 'sec']),
               ('礦工', 'Miners', ['miners', 'pcost', 'hashr'])],
         faq=[('比特幣短期持有者的成本現在多少？價格在成本之上還是之下？', 'What is the Bitcoin short-term holder cost basis now, and is price above or below it?', ['sthgap', 'levels']),
              ('現在有多少比特幣在獲利？', 'How much of the Bitcoin supply is in profit right now?', ['psx', 'profit', 'hnupl']),
              ('長期持有者在賣嗎？', 'Are long-term holders selling?', ['lthnet', 'lthrl', 'oldc']),
              ('大戶在買還是在賣？', 'Are whales buying or selling?', ['whale', 'whalet']),
              ('交易所的比特幣在流入還是流出？', 'Is bitcoin flowing into or out of exchanges?', ['exflow', 'exch'])]),
    dict(id='bitcoin-macro', ch='buy',
         nz='宏觀分析', ne='Macro analysis',
         h1z='比特幣宏觀分析：利率、美元、流動性與資金流', h1e='Bitcoin macro analysis: rates, the dollar, liquidity and fund flows',
         kz='比特幣宏觀分析, BTC 宏觀分析, 比特幣宏觀, 比特幣 ETF 資金流, 現貨 ETF 淨流入, 穩定幣供給, 利率, 美元, 美股相關性, 流動性週期, 聯準會',
         kh='比特币宏观分析, 比特币宏观, 比特币 ETF 资金流, 现货 ETF 净流入, 稳定币, 美联储, 美债收益率, 美元指数, 美股, 流动性',
         ke='Bitcoin macro analysis, Bitcoin macro, Bitcoin ETF flows, spot ETF net flows, stablecoin supply, interest rates, US dollar, correlation with stocks, liquidity cycle, Fed',
         iz='比特幣的價格不只看鏈上，也看錢從哪裡進來：現貨 ETF 每天的申購贖回、穩定幣的供給、美國和亞洲買盤的溢價，以及利率、美元和美股的方向。這一頁把這些圖放在一起，每張圖每天更新，都寫出表態和理由。',
         ie='Bitcoin\'s price also depends on where the money comes from: daily creations and redemptions in spot ETFs, stablecoin supply, the premiums paid by US and Asian buyers, and the direction of rates, the dollar and stocks. This page puts those charts together; every chart updates daily and is marked bullish, bearish or neutral with a reason.',
         secs=[('機構與 ETF', 'Institutions and ETFs', ['etf', 'etf20', 'etfcost', 'treasury', 'cot']),
               ('資金與流動性', 'Money and liquidity', ['stab', 'usdt-usd', 'rcliq', 'rlc', 'capflow', 'grad', 'ad', 'dmd']),
               ('各地的買盤', 'Where the buying comes from', ['pr-us', 'pr-neg', 'pr-asia', 'kp']),
               ('宏觀：利率、美元、美股', 'Macro: rates, the dollar, stocks', ['stk', 'r2y', 'fedmkt', 'macro']),
               ('情緒', 'Sentiment', ['fng', 'wiki'])],
         faq=[('現貨比特幣 ETF 最近是淨流入還是淨流出？', 'Are spot Bitcoin ETFs seeing net inflows or outflows lately?', ['etf20', 'etf']),
              ('利率和美元現在對比特幣是什麼影響？', 'How are rates and the dollar affecting Bitcoin now?', ['macro', 'r2y', 'fedmkt']),
              ('比特幣現在和美股的關係如何？', 'How is Bitcoin trading relative to stocks?', ['stk']),
              ('市場的資金和流動性在增加還是減少？', 'Is money and liquidity flowing into the market or out of it?', ['rlc', 'stab', 'rcliq'])]),
    dict(id='bitcoin-etf', ch='buy',
         nz='ETF 數據分析', ne='ETF data',
         h1z='比特幣 ETF 數據分析：資金流、持有成本與機構部位', h1e='Bitcoin ETF data analysis: flows, holder cost and institutional positioning',
         kz='比特幣ETF數據分析, 比特幣 ETF 資金流, 比特幣 ETF 淨流入, 現貨比特幣 ETF, IBIT, ETF 持有者成本, 上市公司持幣, Strategy, CME 機構持倉, 機構資金',
         kh='比特币ETF数据分析, 比特币 ETF 资金流, 比特币 ETF 净流入, 现货比特币 ETF, IBIT, ETF 持仓成本, 上市公司持币, 微策略, CME 机构持仓, 机构资金',
         ke='Bitcoin ETF data analysis, Bitcoin ETF flows, spot Bitcoin ETF net inflows, IBIT, ETF holder cost basis, public company bitcoin holdings, Strategy, CME COT, institutional flows',
         iz='現貨比特幣 ETF 在 2024 年 1 月上市後，成了美國資金進出比特幣最直接的管道。這一頁看機構的錢：ETF 每天的淨流入流出、近 20 個交易日的合計、ETF 買家的平均成本，以及上市公司持幣、CME 期貨的機構持倉和美國現貨的買盤溢價。ETF 數字來自 CoinMarketCap 的逐檔資料，每張圖每天更新，都寫出表態和理由。',
         ie='Since spot Bitcoin ETFs launched in January 2024 they have become the most direct route for US money into and out of bitcoin. This page follows institutional money: daily ETF net flows, the 20-session total, the average cost of ETF buyers, plus public-company holdings, institutional positioning in CME futures and the premium US spot buyers pay. ETF figures come from per-fund data on CoinMarketCap; every chart updates daily and is marked bullish, bearish or neutral with a reason.',
         secs=[('ETF 資金流', 'ETF flows', ['etf20', 'etf']),
               ('ETF 買家的成本', 'What ETF buyers paid', ['etfcost']),
               ('其他機構', 'Other institutions', ['treasury', 'cot']),
               ('美國現貨買盤', 'US spot demand', ['pr-us', 'pr-neg'])],
         faq=[('現貨比特幣 ETF 最近是淨流入還是淨流出？', 'Are spot Bitcoin ETFs seeing net inflows or outflows lately?', ['etf20', 'etf']),
              ('ETF 買家的平均成本是多少？現在賺還是賠？', 'What did ETF buyers pay on average, and are they in profit?', ['etfcost']),
              ('上市公司（Strategy）的持幣成本在哪？現在賺還是賠？', 'Where is the cost basis of public companies such as Strategy, and are they in profit?', ['treasury']),
              ('CME 的機構在做多還是做空？', 'Are institutions on CME long or short?', ['cot']),
              ('美國的現貨買盤強嗎？', 'How strong is US spot buying?', ['pr-us'])]),
    dict(id='bitcoin-derivatives', ch='lev',
         nz='衍生品數據', ne='Derivatives data',
         h1z='比特幣衍生品數據：資金費率、未平倉、多空比與清算', h1e='Bitcoin derivatives data: funding, open interest, long/short ratio and liquidations',
         kz='比特幣資金費率, 比特幣未平倉量, 多空比, 比特幣清算, 清算價位, 選擇權, 隱含波動率, 看跌看漲比, 恐懼貪婪指數',
         kh='比特币资金费率, 比特币持仓量, 多空比, 比特币爆仓, 清算地图, 期权, 隐含波动率, 恐惧贪婪指数',
         ke='Bitcoin funding rate, Bitcoin open interest, long/short ratio, Bitcoin liquidations, liquidation levels, options, implied volatility, put/call ratio, fear and greed index',
         iz='永續合約、期貨和選擇權的部位，常常決定短線的波動有多大。這一頁看槓桿擠不擠：資金費率、未平倉量、多空帳戶比、清算量和推算的清算價位，以及選擇權市場的隱含波動和看跌看漲比。資料來自 Coinalyze、Deribit、OKX、Binance 等，每張圖每天更新，都寫出表態和理由。',
         ie='Positioning in perpetual swaps, futures and options often sets how violent short-term moves get. This page checks how crowded leverage is: funding rates, open interest, the long/short account ratio, liquidation volume and estimated liquidation levels, plus implied volatility and the put/call ratio in options. Data comes from Coinalyze, Deribit, OKX, Binance and others; every chart updates daily and is marked bullish, bearish or neutral with a reason.',
         secs=[('資金費率與基差', 'Funding and basis', ['fh', 'basis', 'pr-perp']),
               ('未平倉與多空', 'Open interest and long/short', ['oih', 'oieth', 'lsa', 'bfx', 'hlw']),
               ('清算', 'Liquidations', ['lqv', 'liq']),
               ('選擇權', 'Options', ['vol', 'ivt', 'orng', 'oi', 'prem', 'pcr', 'strike', 'gex']),
               ('情緒', 'Sentiment', ['fng'])],
         faq=[('比特幣的資金費率現在多少？', 'What is the Bitcoin funding rate now?', ['fh']),
              ('槓桿擠不擠？未平倉量和多空比怎麼說？', 'How crowded is leverage? What do open interest and the long/short ratio say?', ['oih', 'lsa']),
              ('最近的清算多嗎？清算價位在哪裡？', 'Have liquidations been heavy, and where are the liquidation levels?', ['lqv', 'liq']),
              ('選擇權市場怎麼看後市？', 'What is the options market pricing in?', ['pcr', 'orng', 'vol'])]),
]


def _all():
    return {c['k']: c for p in geo.PAGES for c in geo.charts(p)}


def _reason(c, en):
    """一張圖的理由：拿掉句首的表態（「長線偏多：」「Bullish on the long view: 」，旁邊已經有表態）和重複的圖名（「市場階段：牛市…」）；
    帶限定的（「偏多但在邊緣：」）照留"""
    r = geo.read(c, en) or ''
    if en:
        for _ in range(2):
            r = re.sub(r'^((long|short)-term |near-term )?(bullish|bearish|neutral)( \([^)]{0,24}\)| on the [a-z -]{1,16})?: ', '', r, flags=re.I)
        nm = geo.name(c, True)
        if r.lower().startswith(nm.lower() + ': '): r = r[len(nm) + 2:]
        return r[:1].upper() + r[1:]
    for _ in range(2):   # geo.read 會在「長線偏多：…」前面再補一個「偏多：」，兩層都拿掉
        r = re.sub(r'^(長線|短線|中線)?(偏多|偏空|中性)(（[^）]{0,12}）)?：', '', r)
    nm = geo.name(c, False)
    return r[len(nm) + 1:] if r.startswith(nm + '：') else r


def answer(keys, en, A, P):
    """常見問題的答案：那幾張圖今天的表態和理由（圖不在就略過）"""
    parts = []
    for k in keys:
        c = A.get(k)
        if not c: continue
        lab = TN.get(LEANS.get(k), ('', ''))[1 if en else 0]
        parts.append(('%s (%s): %s' if en else '%s（%s）：%s') % (geo.name(c, en), lab.lower() if en else lab, _reason(c, en)) if lab else
                     ('%s: %s' if en else '%s：%s') % (geo.name(c, en), _reason(c, en)))
    if not parts: return []
    head = ('As of the %s close.' % P.den(geo.DATE)) if en else ('截至 %s 收盤。' % P.dzh(geo.DATE))
    return [head] + [p if p.endswith(('.', '。')) else p + ('.' if en else '。') for p in parts]   # 網頁上一行一張圖，結構化資料接成一段


def hub_page(h, en, P, hans=False):
    """hans=True：簡體版（zh-hans/<主題>/），內容照繁體寫，最後整頁用 hans.py 轉"""
    A = _all(); up = '../../' if (en or hans) else '../'
    # 2026-11-25 圖和簡報的單頁也有簡體版了（pages.py）：簡體主題頁連到簡體的單頁、打開數據頁時帶 ?lang=hans
    CP = 'en/charts/' if en else ('zh-hans/charts/' if hans else 'charts/'); BP = 'en/brief/' if en else ('zh-hans/brief/' if hans else 'brief/'); LGP = 'en' if en else ('hans' if hans else 'zh')
    pre = 'en/' if en else ('zh-hans/' if hans else '')
    me = pre + '%s/' % h['id']
    secs = [(sz, se, [A[k] for k in ks if k in A]) for sz, se, ks in h['secs']]
    cs = [c for _, _, l in secs for c in l]
    n = {t: sum(1 for c in cs if LEANS.get(c['k']) == t) for t in ('up', 'down', 'neu')}
    q = P.PG.get(h['ch']) if h['ch'] else None
    lead = (q.get('lead_en' if en else 'lead_zh') or '') if q else ''
    if en and not geo.EN: lead = ''
    cz = '%s 收盤 · 這頁 %d 張圖：偏多 %d、偏空 %d、中性 %d' % (P.dzh(geo.DATE), len(cs), n['up'], n['down'], n['neu'])
    ce = '%s close · %d charts here: %d bullish, %d bearish, %d neutral' % (P.den(geo.DATE), len(cs), n['up'], n['down'], n['neu'])
    b = ['<p class="mono crumb"><a href="%sapp/?lang=%s">Daybreak</a> / %s</p>' % (up, LGP, esc(h['ne'] if en else h['nz'])),
         '<p class="mono" style="margin:14px 0 0">%s</p>' % esc(ce if en else cz),
         '<h1 class="long">%s</h1>' % esc(h['h1e'] if en else h['h1z'])]
    if lead: b.append('<p class="read">%s</p>' % esc(lead))
    b.append('<p class="dim">%s</p>' % esc(h['ie'] if en else h['iz']))
    b.append('<a class="cta" href="%sapp/?lang=%s">%s →</a>' % (up, LGP, 'Open the interactive Daybreak' if en else '打開互動版 Daybreak'))
    faq = [(qe if en else qz, answer(ks, en, A, P), ks) for qz, qe, ks in h['faq']]
    faq = [f for f in faq if f[1]]
    if faq:
        b.append('<section><h2>%s</h2>%s</section>' % ('Questions people ask' if en else '常見問題', ''.join(
            '<div class="f"><h3>%s</h3><p>%s</p><p class="src">%s</p></div>' % (esc(qq), '<br>'.join(esc(x) for x in aa), ' · '.join(
                '<a href="%s%s%s/">%s</a>' % (up, CP, k, esc(geo.name(A[k], en))) for k in ks if k in A)) for qq, aa, ks in faq)))
    for sz, se, l in secs:
        if not l: continue
        b.append('<section><h2>%s</h2><ul class="list">%s</ul></section>' % (esc(se if en else sz), ''.join(
            '<li>%s<a class="t" href="%s%s%s/">%s</a><p>%s</p></li>' % (P.pill(LEANS.get(c['k']), en), up, CP, c['k'], esc(geo.name(c, en)), esc(_reason(c, en))) for c in l)))
    oth = [x for x in HUBS if x['id'] != h['id']]
    b.append('<section><h2>%s</h2><ul class="list">%s<li><a class="t" href="%s%s">%s</a></li><li><a class="t" href="%s%s">%s</a></li></ul></section>' % (
        'More from Daybreak' if en else 'Daybreak 的其他主題',
        ''.join('<li><a class="t" href="%s%s%s/">%s</a></li>' % (up, pre, x['id'], esc(x['h1e'] if en else x['h1z'])) for x in oth),
        up, CP, 'Bitcoin data and indicators: every chart and where it leans today' if en else '比特幣數據與指標：每一張圖和它今天的表態',
        up, BP, 'Bitcoin market analysis: the daily brief' if en else '比特幣行情分析：每日簡報'))
    title = '%s · Daybreak' % (h['h1e'] if en else h['h1z'])
    desc = (h['ie'] if en else h['iz'])
    pid = SITE + me
    graph = [WEBSITE, PERSON,
             {'@type': 'CollectionPage', '@id': pid + '#page', 'url': pid, 'name': h['h1e'] if en else h['h1z'], 'description': desc,
              'keywords': h['ke'] if en else ((h['kz'] + ', ' + h['kh']) if hans else h['kz']),
              'inLanguage': 'en' if en else ('zh-Hans' if hans else 'zh-Hant'), 'dateModified': geo.DATE, 'isPartOf': {'@id': WEBSITE['@id']}, 'author': {'@id': PERSON['@id']},
              'about': {'@type': 'Thing', 'name': 'Bitcoin', 'sameAs': 'https://en.wikipedia.org/wiki/Bitcoin'},
              'hasPart': [{'@type': 'WebPage', 'url': '%s%s%s/' % (SITE, CP, c['k']), 'name': geo.name(c, en)} for c in cs]},
             P.crumbs(pid + '#crumbs', [('Daybreak', 'app/'), (h['ne'] if en else h['nz'], me)])]
    if faq:
        graph.append({'@type': 'FAQPage', '@id': pid + '#faq', 'url': pid, 'inLanguage': 'en' if en else ('zh-Hans' if hans else 'zh-Hant'),
                      'mainEntity': [{'@type': 'Question', 'name': qq, 'acceptedAnswer': {'@type': 'Answer', 'text': ' '.join(aa)}} for qq, aa, _ in faq]})
    page = P.shell(en, '%s/' % h['id'], 'en/%s/' % h['id'], title, desc, ''.join(b), graph,
                   path_hans=('zh-hans/%s/' % h['id']) if HANS.available() else None, hans=hans)
    return HANS.convert(page) if hans else page


def write_all(out, P):
    """pages.py 的 main 呼叫：寫出四個主題頁（繁、簡、英），回傳 sitemap 要加的 (繁體網址, 英文網址, lastmod, 簡體網址)"""
    urls = []
    for h in HUBS:
        for en in (False, True):
            P.write(out, ('en/%s' if en else '%s') % h['id'], hub_page(h, en, P))
        if HANS.available(): P.write(out, 'zh-hans/%s' % h['id'], hub_page(h, False, P, hans=True))
        urls.append(('%s/' % h['id'], 'en/%s/' % h['id'], geo.DATE, ('zh-hans/%s/' % h['id']) if HANS.available() else None))
    return urls
