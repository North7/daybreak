#!/usr/bin/env python3
"""bitcoin-data.com 請求分配（2026-10-08 建立）。
免費層每個 IP 每小時 10 次、每日 15 次（實測第 11 次回 429 RATE_LIMIT_HOUR_EXCEEDED）；管線共用 20 個端點，一次抓完必定超限。
分配：每日 UTC 00:05 collect.py 即時抓 CORE 10 個；其餘 10 個分 A／B 兩組，由本腳本在前一晚 UTC 22:40 依日期輪替抓 5 個寫進 bd_cache/，
collect.py 只讀快取。合計每日 15 次、任一小時不超過 10 次。輪替指標每 2 天更新一次，頁面照常顯示資料本身的日期。
用法（在倉庫根目錄）：python3 pipeline/bd_rotation.py [--group A|B]   # 不給 --group 時依 UTC 日期奇偶輪替"""
import json, os, sys, subprocess, argparse, datetime as dt

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bd_cache')
# 每日即時：頂部三指標（出場框架 P6）、成本基礎（成本比需同日）、籌碼流向四項（頁面圖表）
CORE = {'mvrv-zscore', 'nupl', 'puell-multiple', 'realized-price', 'sth-realized-price', 'lth-realized-price',
        'sth-lth-ratio', 'percent-sth-in-profit', 'true-market-mean', 'urpd'}
GROUPS = {'A': ['sopr', 'asopr', 'sth-sopr', 'lth-sopr', 'realized-cap-growth-rate'],
          'B': ['illiquid-supply', 'highly-liquid-supply', 'lth-mvrv-zscore', 'supply-in-profit-pct', 'lth-net-position-change-30d-btc']}


def fetch(m):
    """回傳序列（list）；限流或格式不對時丟出可讀的錯誤。"""
    out = subprocess.run(['curl', '-sS', '--max-time', '40', f'https://bitcoin-data.com/v1/{m}'], capture_output=True, text=True).stdout
    try: js = json.loads(out)
    except ValueError: raise RuntimeError(f'bitcoin-data 回應不是 JSON：{out[:80]!r}')
    if isinstance(js, dict) and js.get('error'):
        e = js['error']; raise RuntimeError(f"bitcoin-data {e.get('status')} {e.get('code') or e.get('message')}")
    if not isinstance(js, list) or not js: raise RuntimeError('bitcoin-data 回應不是序列')
    return js


def load(m):
    """讀輪替快取；回傳 (rows, fetched_utc)。"""
    try: cj = json.load(open(os.path.join(CACHE, f'{m}.json')))
    except FileNotFoundError: raise RuntimeError('輪替快取尚無資料')
    return cj['rows'], cj['fetched_utc']


def save(m, rows):
    os.makedirs(CACHE, exist_ok=True)
    rows = [{k: v for k, v in r.items() if k != 'unixTs'} for r in rows]
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    with open(os.path.join(CACHE, f'{m}.json'), 'w') as f:   # 一列一筆，讓每日提交的 diff 只有新增的幾行
        f.write('{"m": %s, "fetched_utc": %s, "rows": [\n' % (json.dumps(m), json.dumps(now)))
        f.write(',\n'.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in rows))
        f.write('\n]}\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--group', choices=sorted(GROUPS))
    ap.add_argument('--skip-if-fresh', action='store_true', help='這組今天（UTC）已抓過就不再打 API（備援排程用）')
    args = ap.parse_args(); today = dt.datetime.now(dt.timezone.utc).date()
    g = args.group or 'AB'[today.toordinal() % 2]
    if args.skip_if_fresh:
        try:
            if all(load(m)[1][:10] == today.isoformat() for m in GROUPS[g]): print(f'{g} 今天已抓過，略過'); sys.exit(0)
        except RuntimeError: pass
    ok = 0
    for m in GROUPS[g]:
        try: rows = fetch(m); save(m, rows); ok += 1; print(f'{g} {m}: {len(rows)} 筆，最新 {rows[-1].get("d") or rows[-1].get("theDate")}')
        except Exception as e: print(f'{g} {m}: 失敗 {e}')
    sys.exit(0 if ok else 1)
