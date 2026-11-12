"""配樂（numpy 自己合成，沒有版權問題）：C–G–Am–F 墊底、低音、八分音符琶音、鼓，場景轉換前加 whoosh。
從 make_audio.py 抽出來給沒有配音的短影片用（2026-11-12）。music(秒數, 轉場時間點, bpm) → float32 單聲道 44.1k"""
import numpy as np
SR = 44100

def music(total, cuts=(), bpm=104, seed=15):
    N = int(total * SR) + SR; rng = np.random.default_rng(seed)
    beat = 60 / bpm; bar = beat * 4
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    CH = [[48, 55, 60, 64, 67], [43, 55, 59, 62, 67], [45, 57, 60, 64, 69], [41, 57, 60, 65, 69]]
    def env(n, a, r):
        e = np.ones(n, np.float32); a, r = int(a * SR), int(r * SR); e[:a] = np.linspace(0, 1, a); e[-r:] *= np.linspace(1, 0, r); return e
    def tone(f, n, h=6, tilt=1.6, det=0.0):
        tt = np.arange(n) / SR; y = np.zeros(n, np.float32)
        for k in range(1, h + 1): y += np.sin(2 * np.pi * f * k * tt * (1 + det) + k) / k ** tilt
        return y
    def place(buf, x, at):
        a = int(at * SR); b = min(len(buf), a + len(x))
        if b > a: buf[a:b] += x[:b - a]
    pad, bass, pluck, drums, wh = (np.zeros(N, np.float32) for _ in range(5))
    arp = [2, 3, 4, 3, 2, 3, 4, 1]
    for b in range(int(np.ceil(total / bar)) + 1):
        ch = CH[b % 4]; t0 = b * bar; n = int((bar + 0.6) * SR); e = env(n, 0.4, 0.9)
        for m in ch[1:]: place(pad, (tone(hz(m), n, 5, 1.8, .0015) + tone(hz(m), n, 5, 1.8, -.0015)) * e * 0.5, t0)
        for q in (0, 2):
            nb = int(beat * 1.8 * SR); eb = np.exp(-np.arange(nb) / SR * 2.2) * env(nb, .01, .1)
            place(bass, tone(hz(ch[0] - 12), nb, 3, 2.5) * eb, t0 + q * beat)
        for k in range(8):
            npl = int(0.45 * SR); ep = np.exp(-np.arange(npl) / SR * 9) * env(npl, .004, .05)
            place(pluck, tone(hz(ch[arp[k]] + 12), npl, 4, 2.2) * ep * (1.0 if k % 2 == 0 else 0.7), t0 + k * beat / 2)
        for q in range(4):
            if q in (0, 2):
                nk = int(0.35 * SR); tk = np.arange(nk) / SR; f = 45 + 75 * np.exp(-tk * 30)
                place(drums, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tk * 9) * 0.9, t0 + q * beat)
            nh = int(0.05 * SR); hn = np.diff(rng.standard_normal(nh + 1)).astype(np.float32)
            place(drums, hn * np.exp(-np.arange(nh) / SR * 70) * 0.12, t0 + q * beat + beat / 2)
    for s in cuts:
        nw = int(0.45 * SR); w = np.convolve(rng.standard_normal(nw).astype(np.float32), np.ones(24) / 24, 'same')
        place(wh, w * np.linspace(0, 1, nw) ** 2 * 0.3, s - 0.42)
    nrm = lambda x, r: x * (r / (np.sqrt(np.mean(x ** 2)) + 1e-9))
    m = nrm(pad, .05) + nrm(bass, .06) + nrm(pluck, .03) + nrm(drums, .045) + wh
    fi, fo = int(0.15 * SR), int(1.8 * SR); end = int(total * SR)
    m[:fi] *= np.linspace(0, 1, fi); m[end - fo:end] *= np.linspace(1, 0, fo); m = m[:end]
    m = np.tanh(m * 2.2) / np.tanh(2.2)
    return (m / np.abs(m).max() * 0.9).astype(np.float32)
