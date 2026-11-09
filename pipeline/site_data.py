"""網站用的精簡資料（2026-11-09 UI 審查：載入速度）。

data/latest.json 是完整資料（約 1.7 MB、gzip 約 650 KB），資料管線、運營工具、檢查工具都讀它，內容不動。
網站改讀這裡產生的 data/site.json：內容完全相同，只把「每列第一欄是日期序號的數字表」（[[日, 值, 值…], …]，約 100 組）
改成按欄存放，日期欄只記起點與間隔（不等距的記差值），gzip 後約小 30%。網頁下載後由 app.js 的 unpack() 還原成原本的結構，
其他程式照舊讀 D.xxx.rows。

  {"$r": [x0, step, n], "c": [[第 2 欄…], [第 3 欄…], …]}   日期等距
  {"$r": [x0], "dx": [差值…], "c": [[…], …]}                  日期不等距

寫出前先用 unpack() 還原一次，和原始資料完全相同才寫；不同（或資料裡本來就有 "$r" 這個鍵）就照原樣寫，網站一樣能讀。
latest.prev.json（判讀撰寫中先顯示的上一份數字）同樣產生 site.prev.json。

用法：python3 pipeline/site_data.py          重新產生（build.py、etf.py 寫完 latest.json 後會呼叫 write_all()）
      python3 pipeline/site_data.py --check  檢查 site*.json 還原後和 latest*.json 完全相同（PR 檢查會跑）
手動改了 data/latest.json（例如一次性補值）之後，一定要再跑一次第一行，不然網站還是舊資料。
"""
import json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MARK = '$r'
MIN_ROWS = 20


def _scalar(v):
    return v is None or isinstance(v, (int, float, str, bool))


def _is_rows(a):
    """數字表：至少 20 列、每列等長且至少 2 欄、第一欄是整數（日期序號）、其餘都是純值。"""
    if not isinstance(a, list) or len(a) < MIN_ROWS or not isinstance(a[0], list):
        return False
    w = len(a[0])
    if w < 2:
        return False
    for r in a:
        if not isinstance(r, list) or len(r) != w or not isinstance(r[0], int) or isinstance(r[0], bool):
            return False
        if not all(_scalar(v) for v in r[1:]):
            return False
    return True


def _has_mark(o):
    if isinstance(o, dict):
        return MARK in o or any(_has_mark(v) for v in o.values())
    if isinstance(o, list):
        return any(_has_mark(v) for v in o)
    return False


def pack(o):
    if isinstance(o, dict):
        return {k: pack(v) for k, v in o.items()}
    if isinstance(o, list):
        if _is_rows(o):
            xs = [r[0] for r in o]
            d = [b - a for a, b in zip(xs, xs[1:])]
            cols = [[r[i] for r in o] for i in range(1, len(o[0]))]
            if len(set(d)) == 1:
                return {MARK: [xs[0], d[0], len(xs)], 'c': cols}
            return {MARK: [xs[0]], 'dx': d, 'c': cols}
        return [pack(v) for v in o]
    return o


def unpack(o):
    """與 assets/app.js 的 unpack() 相同的還原規則（改一邊要改另一邊）。"""
    if isinstance(o, list):
        return [unpack(v) for v in o]
    if isinstance(o, dict):
        r = o.get(MARK)
        if r is not None and 'c' in o:
            n = len(o['c'][0])
            out, x = [], r[0]
            for i in range(n):
                if i:
                    x += r[1] if len(r) > 1 else o['dx'][i - 1]
                out.append([x] + [col[i] for col in o['c']])
            return out
        return {k: unpack(v) for k, v in o.items()}
    return o


def _same(a, b):
    """逐一比對，連型別都要一樣（Python 的 1 == 1.0、True == 1 不算數）。"""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b or (a != a and b != b)


def write(src, dst):
    if not os.path.exists(src):
        return None
    L = json.load(open(src, encoding='utf-8'))
    P = L
    if not _has_mark(L):
        try:
            Q = pack(L)
            if _same(unpack(json.loads(json.dumps(Q))), L):
                P = Q
            else:
                print('site_data: 還原後和原始資料不同，照原樣寫', dst)
        except Exception as e:
            print('site_data: 轉換失敗，照原樣寫', dst, e)
    else:
        print('site_data: 資料裡已有', MARK, '這個鍵，照原樣寫', dst)
    json.dump(P, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    return os.path.getsize(dst)


def write_all():
    out = {}
    for a, b in (('latest.json', 'site.json'), ('latest.prev.json', 'site.prev.json')):
        try:
            n = write(os.path.join(ROOT, 'data', a), os.path.join(ROOT, 'data', b))
            if n is not None:
                out[b] = n
        except Exception as e:
            print('site_data failed', b, e)
    if out:
        print('site_data:', ', '.join(f'{k} {v} bytes' for k, v in out.items()))
    return out


def check():
    bad = []
    for a, b in (('latest.json', 'site.json'), ('latest.prev.json', 'site.prev.json')):
        src, dst = os.path.join(ROOT, 'data', a), os.path.join(ROOT, 'data', b)
        if not os.path.exists(src):
            continue
        if not os.path.exists(dst):
            bad.append(f'{b} 不存在'); continue
        if not _same(unpack(json.load(open(dst, encoding='utf-8'))), json.load(open(src, encoding='utf-8'))):
            bad.append(f'{b} 和 {a} 不一致')
    for m in bad:
        print('site_data:', m)
    if bad:
        print('請執行 python3 pipeline/site_data.py 後再提交（網站讀 site.json，改了 latest.json 要重新產生）')
    return not bad


if __name__ == '__main__':
    import sys
    if '--check' in sys.argv:
        sys.exit(0 if check() else 1)
    write_all()
