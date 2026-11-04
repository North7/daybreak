#!/usr/bin/env python3
"""固定名單掃描（2026-11-04 建立）：直接讀 watchlist.json 每個帳號最近的原創貼文，
篩出值得用數據回覆的，依 Grok 同一套 12 分制排序，並建議主題與配圖。名單以外的新帳號才交給 Grok 找。

用法（在倉庫根目錄）：
  python3 ops/replies/scan.py                 最近 24 小時
  python3 ops/replies/scan.py --hours 12      最近 12 小時
  python3 ops/replies/scan.py --all           低於 7 分的也列出
  python3 ops/replies/scan.py --out <檔名.csv>  另存 CSV（fetch.py 可以直接讀）

讀自 api.fxtwitter.com 的個人頁貼文（第三方、公開、不需登入）；只有原創貼文和引用，沒有他們回覆別人的貼文。
已經在 data/replies.json、或 ops/log/ 裡回覆過的貼文會略過。"""
import argparse, csv, glob, json, os, re, sys, time, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'daybreak-ops-scan'}

BTC = re.compile(r'btc|bitcoin|比特币|比特幣|大饼|大餅', re.I)
SPAM = re.compile(r'空投|抽奖|抽獎|giveaway|airdrop|返佣|返傭|进群|進群|VIP|私信|私訊|referral|邀请码|邀請碼|跟单|跟單', re.I)
# 主題 → (關鍵字, 建議配圖；None＝沒有現成的回覆配圖)
TOPICS = {
    'ETF 資金': (r'ETF|IBIT|FBTC|贝莱德|貝萊德|blackrock|inflow|outflow|净流|淨流', 'etf'),
    '現貨溢價': (r'coinbase ?(溢价|溢價|premium)|premium|溢价|溢價|折价|折價|场外|場外|美国现货|美國現貨', 'cbp'),
    '槓桿清算': (r'清算|爆仓|爆倉|liquidat|资金费率|資金費率|funding|未平仓|未平倉|open interest|\bOI\b|杠杆|槓桿|leverage|多空比|squeeze|轧空|軋空', 'liq'),
    '籌碼分布': (r'筹码|籌碼|URPD|短期持有|长期持有|長期持有|\bSTH\b|\bLTH\b|巨鲸|巨鯨|whale|交易所余额|交易所餘額|exchange (reserve|balance)|提币|提幣|withdraw', 'cohort'),
    '成本線': (r'成本|cost basis|realized price|实现价格|實現價格|STH-RP|TMMP|true market mean', 'cost'),
    'SOPR／認賠': (r'SOPR|亏损|虧損|认赔|認賠|割肉|capitulat|realized loss', 'sopr'),
    '賣方衰竭': (r'卖方衰竭|賣方衰竭|seller exhaustion', 'sec'),
    '新買家／老幣': (r'新买家|新買家|first buy|老币|老幣|一年以上', 'ad'),
    '週期': (r'牛市|熊市|周期|週期|cycle|均线|均線|200 ?(日|D|day)|幂律|冪律|power law|减半|減半|halving|金叉|死叉|底部|顶部|頂部', None),
    '宏觀': (r'美联储|美聯儲|聯準會|\bFed\b|降息|加息|利率|美债|美債|yield|DXY|纳斯达克|那斯達克|nasdaq|选举|選舉|election', None),
}


def fetch(url):
    for n in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25))
        except Exception:
            if n == 2: raise
            time.sleep(2)


def done_ids():
    """已經寫過回覆、或已經回覆過的貼文。"""
    ids = set()
    try:
        ids |= {it['id'] for it in json.load(open(os.path.join(ROOT, 'data', 'replies.json'), encoding='utf-8'))['items']}
    except Exception:
        pass
    for f in glob.glob(os.path.join(ROOT, 'ops', 'log', '20*.json')):
        ids |= {p.get('to_id') for p in json.load(open(f, encoding='utf-8')).get('posts', []) if p.get('to_id')}
    return ids


def topics(text):
    return [(k, chart) for k, (pat, chart) in TOPICS.items() if re.search(pat, text, re.I)]


def score(acc, s, hrs, tps):
    a = s.get('author') or {}
    f = a.get('followers') or 0
    blue = bool((a.get('verification') or {}).get('verified'))
    dt = [t for t in tps if t[0] not in ('週期', '宏觀')]       # Daybreak 有具體數字的主題
    data = 4 if len(dt) >= 2 else 3 if dt else 2 if any(t[0] == '週期' for t in tps) else 1 if tps else 0
    blogger = 2 if acc['type'] == 'blogger' else 1
    fresh = 2 if hrs <= 2 else 1 if hrs <= 8 else 0
    reach = 2 if 10_000 <= f <= 300_000 or (f > 300_000 and hrs <= 1) else 1 if 2_000 <= f < 10_000 else 0
    if not blue: reach = min(reach, 1)
    room = 2 if (s.get('replies') or 0) < 30 else 1 if s['replies'] <= 150 else 0
    return data + blogger + fresh + reach + room, dict(數據=data, 博主=blogger, 時效=fresh, 曝光=reach, 回覆空間=room)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hours', type=float, default=24)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--out')
    ap.add_argument('--top', type=int, default=15, help='最多列幾則（0＝不限）')
    o = ap.parse_args()
    W = json.load(open(os.path.join(HERE, 'watchlist.json'), encoding='utf-8'))['accounts']
    skip, now, rows, miss = done_ids(), time.time(), [], []
    for acc in W:
        try:
            d = fetch(f'https://api.fxtwitter.com/2/profile/{acc["handle"]}/statuses')
        except Exception as e:
            miss.append(f'{acc["handle"]}（{e}）'); continue
        time.sleep(0.4)
        for s in d.get('results') or []:
            a = s.get('author') or {}
            if a.get('screen_name', '').lower() != acc['handle'].lower() or s.get('replying_to'):
                continue                                         # 轉推別人、或回覆別人
            hrs = (now - (s.get('created_timestamp') or 0)) / 3600
            if hrs > o.hours or s['id'] in skip:
                continue
            text = s.get('text') or ''
            q = (s.get('quote') or {}).get('text') or ''
            lang = (s.get('lang') or '')
            lang = 'zh' if lang.startswith('zh') or (lang in ('ja', 'und', 'qme', 'qht') and re.search(r'[一-鿿]', text)) else lang
            why = []
            if lang not in ('zh', 'en'): why.append(f'語言 {lang}')
            if (a.get('followers') or 0) < 2000: why.append('粉絲不到 2,000')
            if SPAM.search(text): why.append('像廣告或導流')
            tps = topics(text + ' ' + q)
            if not BTC.search(text + ' ' + q): why.append('沒講比特幣')
            elif not tps: why.append('沒有對得上的主題')
            if (a.get('followers') or 0) > 500_000 and hrs > 1: why.append('大帳號超過 1 小時')
            sc, parts = score(acc, s, hrs, tps)
            rows.append({'must': bool(acc.get('must')) and not why, 'score': sc, 'parts': parts, 'why': why, 'acc': acc, 's': s,
                         'hrs': hrs, 'lang': lang, 'tps': tps,
                         'chart': next((c for _, c in tps if c), None)})
    ok = [r for r in rows if not r['why'] and (r['must'] or r['score'] >= 7 or o.all)]
    ok.sort(key=lambda r: (not r['must'], -r['score'], r['hrs']))
    per, kept = {}, []                                           # 同一個帳號最多列 2 則（必看不限）
    for r in ok:
        h = r['acc']['handle']
        if r['must'] or per.get(h, 0) < 2:
            kept.append(r); per[h] = per.get(h, 0) + 1
    ok = kept[:o.top] if o.top else kept
    print(f'掃描 {len(W)} 個帳號、最近 {o.hours:g} 小時：{len(rows)} 則原創，列出 {len(ok)} 則' + ('' if o.all else '（7 分以上＋必看，每個帳號最多 2 則）'))
    if miss: print('讀不到：' + '、'.join(miss))
    print('\n| # | 帳號（粉絲） | 藍勾 | 幾小時前 | 語言 | 主題 → 配圖 | 讚／回覆／瀏覽 | 分數 | 開頭 | 連結 |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for n, r in enumerate(ok, 1):
        s, a = r['s'], r['s'].get('author') or {}
        tp = '、'.join(k for k, _ in r['tps']) or '-'
        print(f'| {"★" if r["must"] else ""}{n} | @{a.get("screen_name")}（{a.get("followers"):,}） | {"是" if (a.get("verification") or {}).get("verified") else "否"} '
              f'| {r["hrs"]:.1f} | {r["lang"]} | {tp} → {r["chart"] or "-"} | {s.get("likes")}／{s.get("replies")}／{s.get("views")} '
              f'| {r["score"]} | {(s.get("text") or "")[:50].replace(chr(10), " ").replace("|", "／")} | {s.get("url")} |')
    reasons = {}
    for r in rows:
        for w in r['why']:
            reasons[w] = reasons.get(w, 0) + 1
    if reasons:
        print('\n排除：' + '、'.join(f'{w} {n} 則' for w, n in sorted(reasons.items(), key=lambda x: -x[1])))
    print('\n這只是初篩：寫回覆前照 README 先用 fetch.py 讀原文，內容不對（不是在講比特幣數據、廣告、政治）就跳過。')
    if o.out:
        with open(o.out, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['#', '連結', '帳號', '粉絲', '藍勾', '發文時間（UTC）', '語言', '主題', '建議配圖', '讚', '回覆', '瀏覽', '分數', '分數明細', '原文開頭'])
            for n, r in enumerate(ok, 1):
                s, a = r['s'], r['s'].get('author') or {}
                w.writerow([('★' if r['must'] else '') + str(n), s.get('url'), a.get('screen_name'), a.get('followers'),
                            '是' if (a.get('verification') or {}).get('verified') else '否',
                            datetime.fromtimestamp(s.get('created_timestamp') or 0, timezone.utc).strftime('%Y-%m-%d %H:%M'),
                            r['lang'], '、'.join(k for k, _ in r['tps']), r['chart'] or '', s.get('likes'), s.get('replies'),
                            s.get('views'), r['score'], json.dumps(r['parts'], ensure_ascii=False), (s.get('text') or '')[:120]])
        print(f'\n另存 {o.out}')


if __name__ == '__main__':
    main()
