#!/usr/bin/env python3
"""各層地址的 7 日持幣變化熱力條（2026-11-12 新增，參考業界「吸籌趨勢」那種一層一條色帶的畫法）。

資料是 Bitview 依地址餘額分層的持幣量（和「大戶 30 日淨變化」同一份）。每一層、每一天算「這 7 天持幣量變了多少」，
再除以這一層自己近 4 年 7 日變化絕對值的第 90 百分位，夾在 −1～+1：+1 是這一層少見的大幅增加，−1 是少見的大幅減少。
這不是 Glassnode 的 Accumulation Trend Score（那個有做實體歸併、依錢包大小加權），只是地址餘額分層的增減；
一個地址不等於一個人，交易所和託管整理錢包會讓幣在層之間移動，所以看連續幾天的顏色，不看單日。只作讀值。"""
import bisect, datetime as dt

KEYS = ('b1', 'b10', 'b100', 'b1k', 'b10k', 'b100k')
COH = [('ge10k', [5]), ('1k_10k', [4]), ('100_1k', [3]), ('10_100', [2]), ('1_10', [1]), ('lt1', [0])]   # 由大到小，畫的時候最大的在最上面
_EP = dt.date(1970, 1, 1)
dn = lambda s: (dt.date.fromisoformat(s) - _EP).days


def build(BV, last, days=165):
    """BV＝bitview.cols(rows)（{欄: {日期: 值}}）。回傳 onchain.whales.strip；資料不夠回傳 None。"""
    if not BV or not BV.get('b1'): return None
    D = [d for d in sorted(BV['b1']) if d <= last and all(d in BV[k] for k in KEYS + ('sths', 'lths'))]
    if len(D) < 400: return None
    N = [dn(d) for d in D]; W = []
    for d in D:
        b = [BV[k][d] for k in KEYS]; W.append([BV['sths'][d] + BV['lths'][d] - sum(b)] + b[:4] + [b[4] + b[5]])
    def back(j, n):
        k = bisect.bisect_right(N, N[j] - n) - 1
        return k if k >= 0 and N[j] - N[k] <= n + 3 else None
    out = []; j0 = max(0, len(D) - days); h0 = max(0, len(D) - 1461)
    for key, ix in COH:
        val = lambda j: sum(W[j][q] for q in ix)
        ch = {}
        for j in range(h0, len(D)):
            b = back(j, 7)
            if b is not None and val(b): ch[j] = (val(j) / val(b) - 1) * 100
        mags = sorted(abs(v) for v in ch.values())
        ref = mags[int((len(mags) - 1) * .9)] if mags else 0
        if not ref: return None
        sc = [None if j not in ch else round(max(-1, min(1, ch[j] / ref)), 2) for j in range(j0, len(D))]
        pc = [None if j not in ch else round(ch[j], 3) for j in range(j0, len(D))]
        run = 0; sg = None
        for v in reversed(pc):   # 最近連續幾天同方向
            if v is None or v == 0: break
            if sg is None: sg = v > 0
            if (v > 0) != sg: break
            run += 1
        out.append(dict(key=key, s=sc, p=pc, ref=round(ref, 3), now=pc[-1], run=run, up=bool(sg)))
    px = BV.get('px') or {}
    return dict(date=D[-1], n=7, days=[N[j] for j in range(j0, len(D))], px=[px.get(D[j]) for j in range(j0, len(D))], tiers=out)
