"""長期路徑的每月例行重估（2026-11-03 使用者要求自動化；10/31 那次沒有人做）。規則沿用舊日報已裁示的版本：
  · 錨點（2026-09-20 P3）：四條路徑的起點＝上一個月底收盤，每月換一次；已實現線補上月底收盤。後面的節點不動，
    換錨後已在錨點當月或之前的節點刪掉（端點固定時換起點本身就是改形狀，P3 已接受）。
  · 權重（2026-10-01 P26 (a)）：以月底收盤 C 對各路徑當月值 m_i 做對數常態似然 L_i＝exp(−(ln C − ln m_i)²／(2·0.12²))，
    post_i ∝ w_i·L_i，新權重＝round((w_i + post_i)／2)，總和調回 100。似然用換錨前的節點算。計算過程記在 paths.reviews。
  · 失效（2026-09-20 P4）：收盤跌破 61,000 →「直接修復」權重歸零，按比例分給其他三條。
  · 形狀（2026-09-29 包絡規則）：收盤超出四條路徑當天內插值上下緣 12% 以上連 10 個交易日才需要重估形狀。
    這需要判斷，這裡只標記 reshape_needed，不自動改。
build.py 每天呼叫：到了 next_review（月底）而且那個月有收盤，就做一次並寫回 data/model.json。"""
import calendar, datetime as dt, json, math

SIGMA, BAND, RUN, KILL, KILLED = 0.12, 0.12, 10, 61000, '直接修復'


def _t(y, m, d=1):   # 以月為單位的時間座標：節點 [年, 月, 值] 落在該月起點
    return y * 12 + m - 1 + (d - 1) / calendar.monthrange(y, m)[1]


def _at(nodes, t):
    pts = [(_t(a, b), v) for a, b, v in nodes]
    if t <= pts[0][0]: return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t0 <= t <= t1: return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return pts[-1][1]


def month_val(nodes, y, m): return _at(nodes, _t(y, m))


def _round100(w):   # 最大餘數法取整到 1%，總和 100
    base = {k: math.floor(v) for k, v in w.items()}; left = 100 - sum(base.values())
    for k in sorted(w, key=lambda k: -(w[k] - base[k]))[:max(0, left)]: base[k] += 1
    return base


def fan(paths, closes, upto):
    """到 upto 為止，收盤連續超出包絡上下 12% 的天數，以及當天的包絡上下緣"""
    run, lo, hi = 0, None, None
    for d in sorted(x for x in closes if x <= upto and x > paths['anchor'][0]):
        y, m, dd = map(int, d.split('-')); t = _t(y, m, dd)
        v = [_at(n, t) for n in paths['nodes'].values()]; lo, hi = min(v), max(v)
        run = run + 1 if (closes[d] > hi * (1 + BAND) or closes[d] < lo * (1 - BAND)) else 0
    return dict(run=run, need=RUN, lo=round(lo * (1 - BAND)) if lo else None, hi=round(hi * (1 + BAND)) if hi else None, reshape_needed=run >= RUN)


def review(paths, closes, last):
    """closes：{date: 收盤}；last：最新已收盤日。回傳 (是否改了 paths, 本次做的紀錄)。paths 直接就地修改"""
    done, changed = [], False
    w = paths['weights']
    if w.get(KILLED) and any(v < KILL for d, v in closes.items() if paths['anchor'][0] < d <= last):
        k = w[KILLED]; rest = {n: x for n, x in w.items() if n != KILLED}; s = sum(rest.values()) or 1
        nw = _round100({n: (x + k * x / s if n != KILLED else 0) for n, x in w.items()})
        rec = dict(kind='kill', date=last, before=dict(w), after=nw, why=f'收盤跌破 {KILL:,}')
        paths.setdefault('reviews', []).append(rec); done.append(rec); paths['weights'] = w = nw; changed = True
    while paths.get('next_review') and paths['next_review'] <= last:
        nr = paths['next_review']; y, m = int(nr[:4]), int(nr[5:7])
        inm = sorted(d for d in closes if d[:7] == nr[:7] and d <= nr)
        if not inm: break
        C = closes[inm[-1]]
        mi = {n: month_val(nodes, y, m) for n, nodes in paths['nodes'].items()}
        L = {n: math.exp(-(math.log(C) - math.log(mi[n])) ** 2 / (2 * SIGMA ** 2)) for n in mi}
        z = sum(w[n] * L[n] for n in mi) or 1
        post = {n: w[n] * L[n] / z * 100 for n in mi}
        nw = _round100({n: (w[n] + post[n]) / 2 for n in mi})
        fz = fan(paths, closes, nr)
        rec = dict(kind='monthly', month=nr[:7], date=nr, close_date=inm[-1], close=round(C), m={n: round(v) for n, v in mi.items()},
                   L={n: round(v, 3) for n, v in L.items()}, post={n: round(v, 1) for n, v in post.items()}, before=dict(w), after=nw,
                   fan_run=fz['run'], reshape_needed=fz['reshape_needed'], killed=w.get(KILLED) == 0)
        # 換錨：起點＝月底收盤；錨點當月或之前的其他節點刪掉
        for n, nodes in paths['nodes'].items():
            paths['nodes'][n] = [[y, m, round(C)]] + [x for x in nodes[1:] if _t(x[0], x[1]) > _t(y, m)]
        if not any(r[0] == y and r[1] == m for r in paths['realized']): paths['realized'].append([y, m, round(C)])
        paths['anchor'] = [inm[-1], round(C)]
        paths['weights'] = w = nw
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        paths['next_review'] = f'{ny}-{nm:02d}-{calendar.monthrange(ny, nm)[1]:02d}'
        paths.setdefault('reviews', []).append(rec); done.append(rec); changed = True
    return changed, done


def write_paths(path, paths):
    """只改寫 data/model.json 的 "paths" 區塊（在檔案最後），沿用手寫格式：陣列與小物件放一行，diff 只有變的那幾行"""
    s = open(path, encoding='utf-8').read(); i = s.index('  "paths": {')
    J = lambda x: json.dumps(x, ensure_ascii=False)
    keys = [k for k in ('anchor', 'weights', 'nodes', 'realized', 'top_model', 'next_review', 'reviews') if k in paths]
    out = []
    for k in keys:
        v = paths[k]
        if k == 'nodes': out.append('    "nodes": {\n' + ',\n'.join(f'      {J(n)}: {J(x)}' for n, x in v.items()) + '\n    }')
        elif k == 'reviews': out.append('    "reviews": [\n' + ',\n'.join('      ' + J(r) for r in v) + '\n    ]')
        else: out.append(f'    {J(k)}: {J(v)}')
    open(path, 'w', encoding='utf-8').write(s[:i] + '  "paths": {\n' + ',\n'.join(out) + '\n  }\n}\n')
