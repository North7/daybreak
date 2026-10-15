"""CheckOnChain 公開圖表的 STH-SOPR（2026-10-15 使用者選擇方案 A）。
bitcoin-data 的 SOPR 系列晚約 7 天；CheckOnChain 的公開圖表（charts.checkonchain.com）晚約 1 天，而且是從 2009 起的完整日線。
做法：每天讀一次圖表頁（約 7MB），從頁內 Plotly 資料取出「STH-SOPR > 1」與「STH-SOPR < 1」兩條（同一條 STH-SOPR 依 1 拆成兩段著色），合併回原序列。
不佔 bitcoin-data 的每日額度。頁面改版或抓取失敗時，退回上一次成功存下的 coc_cache/sth-sopr.json（頁面照常顯示資料本身的日期）。
資料屬 CheckOnChain（James Check），頁面標明來源並連回原圖；與 bitcoin-data 的 STH-SOPR 是不同資料商，不互相相減。"""
import base64, datetime as dt, json, os, struct, subprocess

URL = 'https://charts-cdn.checkonchain.com/btconchain/realised/sthsopr_indicator/sthsopr_indicator_light.html'
PAGE = 'https://charts.checkonchain.com/btconchain/realised/sthsopr_indicator/sthsopr_indicator_light.html'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coc_cache', 'sth-sopr.json')


def _trace(traces, name):
    t = next(t for t in traces if t.get('name') == name)
    y = t['y']
    if isinstance(y, dict):   # Plotly 的二進位格式：base64 的 float64
        b = base64.b64decode(y['bdata']); y = struct.unpack('<%dd' % (len(b) // 8), b)
    return {x[:10]: v for x, v in zip(t['x'], y) if v is not None and v == v}


def fetch():
    html = subprocess.run(['curl', '-sS', '--max-time', '90', URL], capture_output=True, text=True).stdout
    i = html.find('Plotly.newPlot(')
    if i < 0: raise RuntimeError('CheckOnChain 頁面沒有 Plotly 資料（可能改版）')
    traces, _ = json.JSONDecoder().raw_decode(html[html.find('[', i):])
    gt, lt = _trace(traces, 'STH-SOPR > 1'), _trace(traces, 'STH-SOPR < 1')
    ser = {d: (gt[d] if gt[d] != 1 else lt.get(d, 1.0)) for d in gt}
    if len(ser) < 1000: raise RuntimeError(f'CheckOnChain STH-SOPR 只有 {len(ser)} 筆，格式可能改了')
    return ser


def get():
    """回傳 (序列 {date: value}, 狀態說明)。失敗時用上一次成功的快取。"""
    try:
        ser = fetch()
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        rows = sorted(ser.items())
        now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
        with open(CACHE, 'w') as f:   # 只留最近 1,500 天（四年百分位夠用）；一列一筆，每日提交的 diff 只有新增的幾行
            f.write('{"fetched_utc": "%s", "source": "%s", "rows": [\n' % (now, PAGE))
            f.write(',\n'.join(json.dumps([d, round(v, 5)]) for d, v in rows[-1500:]) + '\n]}\n')
        return ser, 'live'
    except Exception as e:
        cj = json.load(open(CACHE))   # 沒有快取就讓錯誤往上丟，由呼叫端記錄
        return {d: v for d, v in cj['rows']}, f'cache {cj["fetched_utc"]}（{e}）'
