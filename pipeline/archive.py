"""往期封存與判讀回顧（2026-10-12 建立）。
每天 build.py 跑的時候 data/notes.json 還是前一期（每日任務之後才寫新的一期），把它（與 notes.en.json）存成
data/archive/<date>.json／<date>.en.json，再重建 data/archive/index.json：每期的頭條、立場、當天收盤、之後到今天的漲跌，
以及當期「要盯的價位」（watch）之後有沒有被收盤碰到、哪一天碰到。只用市場資料與已公開的判讀，不含任何個人資訊。
用法：build.py 自動呼叫 update()；一次性回填：python3 pipeline/archive.py --backfill-git"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, 'data', 'archive')


def _save(n, suffix):
    d = n.get('date')
    if not d: return False
    os.makedirs(A, exist_ok=True)
    with open(os.path.join(A, f'{d}{suffix}.json'), 'w') as f: json.dump(n, f, ensure_ascii=False, separators=(',', ':'))
    return True


def snapshot():
    """把目前的 notes.json／notes.en.json 存進封存（同一天重寫時覆蓋成最後一版）。"""
    for name, suf in (('notes.json', ''), ('notes.en.json', '.en')):
        p = os.path.join(ROOT, 'data', name)
        if os.path.exists(p):
            try: _save(json.load(open(p)), suf)
            except ValueError: pass


def rebuild_index():
    """重建 index.json。收盤取自 data/history/index.json（每日快照）。"""
    hist = json.load(open(os.path.join(ROOT, 'data', 'history', 'index.json')))
    close = {h['date']: h['close'] for h in hist if h.get('close')}
    days = sorted(close); last = days[-1] if days else None
    out = []
    for fn in sorted(os.listdir(A)) if os.path.isdir(A) else []:
        if not fn.endswith('.json') or fn.endswith('.en.json') or fn == 'index.json': continue
        n = json.load(open(os.path.join(A, fn))); d = n['date']; c0 = close.get(d)
        en_p = os.path.join(A, d + '.en.json'); en = json.load(open(en_p)) if os.path.exists(en_p) else None
        after = [t for t in days if t > d]
        watch = []
        for i, w in enumerate(n.get('watch') or []):
            v = w.get('value'); hit = None
            if v and c0:
                up = v > c0
                hit = next((t for t in after if (close[t] >= v if up else close[t] <= v)), None)
            row = dict(label=w.get('label'), value=v, dist_pct=round((v / c0 - 1) * 100, 1) if v and c0 else None, hit=hit)
            if en and i < len(en.get('watch') or []): row['label_en'] = en['watch'][i].get('label')
            watch.append(row)
        e = dict(date=d, edition=n.get('edition'), headline=n.get('headline'), stance=(n.get('stance') or {}).get('label'),
                 close=c0, chg_since_pct=round((close[last] / c0 - 1) * 100, 1) if c0 and last and last > d else None, days_since=len(after), watch=watch)
        if en: e.update(headline_en=en.get('headline'), stance_en=(en.get('stance') or {}).get('label'))
        # 2026-10-23：發現與追蹤結果也進索引（之後可以算有幾成被確認／推翻）
        if n.get('findings') is not None:
            e['findings'] = [dict(id=f.get('id'), title=f.get('title'), confidence=f.get('confidence'), lean=f.get('lean'), signals=f.get('signals')) for f in n.get('findings') or []]
            e['followups'] = [dict(id=f.get('id'), status=f.get('status')) for f in n.get('followups') or []]
        out.append(e)
    out.sort(key=lambda e: e['date'], reverse=True)
    with open(os.path.join(A, 'index.json'), 'w') as f:
        json.dump(dict(as_of=last, editions=out), f, ensure_ascii=False, separators=(',', ':'))
    return len(out)


def update():
    snapshot(); return rebuild_index()


def backfill_git():
    """從 git 歷史找出每個日期最後一版的 notes.json 存進封存（不覆蓋已存在的檔）。"""
    hs = subprocess.run(['git', '-C', ROOT, 'log', '--format=%H', '--', 'data/notes.json'], capture_output=True, text=True).stdout.split()
    seen = set()
    for h in hs:   # 新到舊：每個日期第一次看到的就是最後一版
        raw = subprocess.run(['git', '-C', ROOT, 'show', f'{h}:data/notes.json'], capture_output=True, text=True).stdout
        try: n = json.loads(raw)
        except ValueError: continue
        d = n.get('date')
        if d and d not in seen and not os.path.exists(os.path.join(A, f'{d}.json')): _save(n, ''); seen.add(d)
    return sorted(seen)


if __name__ == '__main__':
    if '--backfill-git' in sys.argv: print('回填', backfill_git())
    print('封存', update(), '期')
