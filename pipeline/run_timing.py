"""每日資料管線的計時（2026-11-25，使用者：「每日資料為什麼要跑 8–9 分鐘，先把計時加上」）。
collect.py 一開頭 import 這支就生效，不用改其他程式。結束時印一張表（stderr），在 GitHub Actions 裡也寫進這次執行的 Summary：
  - 各區段（collect.py 裡「# ---------- X ----------」的標題）花了多少時間，以及那段時間在哪個模組裡（coinalyze.py、bitview.py…）
  - 每個網站的請求次數和總秒數（curl 子程序和 urllib 都算）
  - 主動等待（time.sleep）的總秒數和位置：限流時照對方要求等，這段時間 Actions 一樣算分鐘數
做法：背景執行緒每 0.25 秒看一次主執行緒停在哪一行（取樣，誤差約 ±0.25 秒）；網路請求和 sleep 另外包一層記實際秒數。只記時間，不改任何結果。
倉庫考慮改私有，私有庫的 Actions 要算額度；每日資料一個月約 840 分鐘，先量清楚再決定要省哪裡。
"""
import atexit, collections, os, re, subprocess, sys, threading, time, urllib.parse, urllib.request

T0 = time.time()
DT = 0.25
_sleep = time.sleep
_MAIN = threading.main_thread().ident
_SCRIPT = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else ''
_HERE = os.path.dirname(os.path.abspath(__file__))

by_sec = collections.Counter()     # 區段 → 秒
by_mod = collections.Counter()     # (區段, 模組) → 秒
by_host = collections.defaultdict(lambda: [0, 0.0])   # 網站 → [次數, 秒]
sleeps = collections.defaultdict(lambda: [0, 0.0])    # 檔名:行 → [次數, 秒]


def _sections():
    out = []
    try:
        for i, l in enumerate(open(_SCRIPT, encoding='utf-8'), 1):
            m = re.match(r'#\s*-{5,}\s*(.+?)\s*-{5,}\s*$', l)
            if m: out.append((i, re.sub(r'[（(：:].*$', '', m.group(1)).strip()[:28] or m.group(1)[:28]))
    except Exception:
        pass
    return out


SECS = _sections()


def _sec(line):
    name = '開頭'
    for l, n in SECS:
        if l <= line: name = n
        else: break
    return '%s（%d 行起）' % (name, max([l for l, _ in SECS if l <= line] or [1]))


def _where(f):
    """主執行緒現在的位置 → (collect.py 的區段, 它呼叫進去的模組)"""
    called = None
    while f is not None:
        fn = f.f_code.co_filename
        if os.path.abspath(fn) == _SCRIPT:
            return _sec(f.f_lineno), called or os.path.basename(_SCRIPT)
        if os.path.dirname(os.path.abspath(fn)) == _HERE and not fn.endswith('run_timing.py'):
            called = os.path.basename(fn)   # 往上走，最後留下的是 collect.py 直接呼叫的那個模組
        elif called is None:
            called = '（%s）' % os.path.basename(fn)   # 標準庫：subprocess、json、ssl…
        f = f.f_back
    return '（collect.py 之外）', called or '?'


def _sampler():
    while True:
        _sleep(DT)
        f = sys._current_frames().get(_MAIN)
        if f is None: continue
        s, m = _where(f)
        by_sec[s] += DT; by_mod[(s, m)] += DT


def _host(url):
    try: return urllib.parse.urlsplit(url).hostname or '?'
    except Exception: return '?'


_run = subprocess.run
def _timed_run(cmd, *a, **k):
    t = time.time()
    try: return _run(cmd, *a, **k)
    finally:
        if isinstance(cmd, (list, tuple)) and cmd and os.path.basename(str(cmd[0])) == 'curl':
            u = next((x for x in cmd if isinstance(x, str) and x.startswith('http')), '')
            h = by_host[_host(u)]; h[0] += 1; h[1] += time.time() - t
subprocess.run = _timed_run

_urlopen = urllib.request.urlopen
def _timed_urlopen(req, *a, **k):
    t = time.time()
    try: return _urlopen(req, *a, **k)
    finally:
        u = req if isinstance(req, str) else getattr(req, 'full_url', '')
        h = by_host[_host(u)]; h[0] += 1; h[1] += time.time() - t
urllib.request.urlopen = _timed_urlopen

def _timed_sleep(s):
    f = sys._getframe(1)
    key = '%s:%d' % (os.path.basename(f.f_code.co_filename), f.f_lineno)
    v = sleeps[key]; v[0] += 1; v[1] += max(0.0, float(s))
    return _sleep(s)
time.sleep = _timed_sleep


def _report():
    total = time.time() - T0
    L = ['### 每日資料計時（collect.py，共 %.0f 秒）' % total, '',
         '**各區段**（取樣，每格 %.2f 秒）' % DT, '', '| 區段 | 秒 | 主要花在 |', '|---|---:|---|']
    for s, v in by_sec.most_common():
        if v < 1: continue
        mods = sorted(((m, x) for (ss, m), x in by_mod.items() if ss == s), key=lambda t: -t[1])[:3]
        L.append('| %s | %.0f | %s |' % (s, v, '、'.join('%s %.0f' % (m, x) for m, x in mods)))
    L += ['', '**網路請求**', '', '| 網站 | 次數 | 秒 |', '|---|---:|---:|']
    for h, (n, x) in sorted(by_host.items(), key=lambda t: -t[1][1]):
        if x >= 0.5: L.append('| %s | %d | %.1f |' % (h, n, x))
    sl = sorted(sleeps.items(), key=lambda t: -t[1][1])
    L += ['', '**主動等待（time.sleep）共 %.0f 秒**' % sum(v[1] for _, v in sl), '', '| 位置 | 次數 | 秒 |', '|---|---:|---:|']
    for k_, (n, x) in sl:
        if x >= 0.5: L.append('| %s | %d | %.1f |' % (k_, n, x))
    txt = '\n'.join(L) + '\n'
    try: sys.stderr.write('\n' + txt)
    except Exception: pass
    p = os.environ.get('GITHUB_STEP_SUMMARY')
    if p:
        try: open(p, 'a', encoding='utf-8').write(txt)
        except Exception: pass


threading.Thread(target=_sampler, daemon=True).start()
atexit.register(_report)
