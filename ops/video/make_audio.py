"""破曉 No.015 短影片的配音與配樂。
配音：edge-tts 的台灣神經語音（預設曉臻 zh-TW-HsiaoChenNeural）逐場景合成；配樂：numpy 自己合成（沒有版權問題）。
輸出 timing.json（每場景秒數，給 make_short.py）與 mix.wav（配音＋配樂，配音時配樂自動壓低）。
用法：python make_audio.py <工作資料夾> [語音名稱] [旁白 JSON]
Gemini 配音：TTS_ENGINE=gemini、語音名稱給 Gemini 的聲音（例如 Charon），金鑰讀 ~/.gemini_key（GEMINI_API_KEY=…，不進 git）。
  整份稿子一次送（免費方案一個模型一天 10 次），照停頓切回每場景；同一份稿子、聲音、模型會用工作資料夾裡的快取，不再叫 API。
  TTS_MODEL 換模型（預設 gemini-3.8-flash-tts），TTS_TEMPO 調速（例如 1.08，不變音高）。"""
import json, os, subprocess, sys, wave
import numpy as np

OUT = sys.argv[1]
SR = 44100
VOICE = sys.argv[2] if len(sys.argv) > 2 else 'zh-TW-HsiaoChenNeural'
RATE = os.environ.get('TTS_RATE', '+8%')   # 語速；SPI 那支用 +20%
BASE = [4.4, 5.6, 5.4, 5.2, 5.8, 4.4, 3.6]   # 原本的場景長度（沒有配音時）
LEAD, TAIL = 0.25, 0.55                      # 每場景配音前留白／後留白
LINES = [
    '比特幣 ETF 一天淨流入五點二七億美元，九月以來最大，幾乎全靠 I B I T 一檔。',
    '週二收在八萬兩千九百三十六美元，從六月低點已經漲了四成，市場階段是牛市第十二天。',
    '不過別急：近七個完整交易日，ETF 合計還是淨流出四點五一億。',
    '槓桿反而在降溫，資金費率從九點七七降到八點一三。這次，是現貨走在槓桿前面。',
    '出場框架零條觸發：離兩百日均線還有一成二，離第一個賣出點還差三成五。今天，不動。',
    '接下來盯：二十三號 PMI、二十九號 FOMC、三十號選擇權月度到期。',
    '破曉，每天清晨的第一份比特幣簡報。',
]
if len(sys.argv) > 3:  # 第三個參數：每期的旁白 JSON {"base": [...], "lines": [...]}
    _c = json.load(open(sys.argv[3])); BASE, LINES = _c['base'], _c['lines']


def tts(i, text):
    import imageio_ffmpeg
    mp3, p = os.path.join(OUT, f'vo_{i}.mp3'), os.path.join(OUT, f'vo_{i}.wav')
    subprocess.run([os.path.join(os.path.dirname(sys.executable), 'edge-tts'), '--voice', VOICE, f'--rate={RATE}',
                    '--text', text, '--write-media', mp3], check=True, capture_output=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', mp3, '-ac', '1', '-ar', str(SR), p], check=True)
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    nz = np.flatnonzero(np.abs(x) > 0.01)          # 去掉頭尾靜音，時間才準
    return x[max(0, nz[0] - 200): nz[-1] + 2000]


ENGINE = os.environ.get('TTS_ENGINE', 'edge')
NOTES = ("### DIRECTOR'S NOTES\n"
         "Style: Taiwanese Mandarin, a friend who follows markets chatting casually, curious, natural, not a news anchor.\n"
         "Pace: lively, slightly fast, a clear pause between paragraphs.\n"
         "Pronounce SPI as the letters S-P-I; say Daybreak and BTC in English.\n"
         "Only read the transcript below.\n\n### TRANSCRIPT\n")


def gemini_all(lines):
    """整份稿子一次合成，回傳每段的波形（SR）。"""
    import base64, hashlib, re, time, urllib.error, urllib.request, imageio_ffmpeg
    model = os.environ.get('TTS_MODEL', 'gemini-3.8-flash-tts')
    prompt = NOTES + '\n\n'.join(lines)
    raw = os.path.join(OUT, 'gemini_' + hashlib.sha1(f'{model}|{VOICE}|{prompt}'.encode()).hexdigest()[:10] + '.wav')
    if not os.path.exists(raw):
        key = [l.split('=', 1)[1].strip() for l in open(os.path.expanduser('~/.gemini_key')) if l.startswith('GEMINI_API_KEY=')][0]
        body = {'contents': [{'parts': [{'text': prompt}]}],
                'generationConfig': {'responseModalities': ['AUDIO'],
                                     'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': VOICE}}}}}
        req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                                     data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
        for _ in range(6):
            try:
                r = json.load(urllib.request.urlopen(req, timeout=300)); break
            except urllib.error.HTTPError as e:
                m = e.read().decode()
                if e.code == 429 and 'PerMinute' in m:
                    time.sleep(float((re.search(r'retry in ([\d.]+)s', m) or [0, 30])[1]) + 2); continue
                sys.exit(f'Gemini {e.code}: ' + (re.search(r'"message": "([^"]*)', m) or [0, m[:300]])[1])
        d = r['candidates'][0]['content']['parts'][0]['inlineData']
        pcm = base64.b64decode(d['data'])
        if pcm[:4] == b'RIFF': open(raw, 'wb').write(pcm)
        else:   # 舊模型回傳裸 PCM（audio/L16;rate=24000）
            with wave.open(raw, 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(int((re.search(r'rate=(\d+)', d.get('mimeType', '')) or [0, 24000])[1])); w.writeframes(pcm)
    p = raw[:-4] + '_sr.wav'
    tempo = os.environ.get('TTS_TEMPO')
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', raw, '-ac', '1', '-ar', str(SR),
                    *(['-af', f'atempo={tempo}'] if tempo else []), p], check=True)
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    # 10ms 一格的音量，找出停頓；用每段字數推估的位置挑最合理的 N-1 個停頓當切點
    hop = SR // 100; rms = np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, 'same')[::hop])
    on = rms > max(0.006, rms.max() * 0.03); idx = np.flatnonzero(on); a0, a1 = idx[0], idx[-1]
    gaps, k = [], a0
    while k < a1:
        if not on[k]:
            j = k
            while j < a1 and not on[j]: j += 1
            if j - k >= 15: gaps.append((k, j))
            k = j
        k += 1
    n = len(lines); cum = np.cumsum([len(l) for l in lines])[:-1] / sum(len(l) for l in lines)
    exp = a0 + cum * (a1 - a0)
    score = lambda g, b: (g[1] - g[0]) / 100 - 0.15 * abs((g[0] + g[1]) / 2 - exp[b]) / 100
    best = {}
    for b in range(n - 1):   # DP：第 b 個切點用第 c 個停頓
        for c, g in enumerate(gaps):
            prev = max((best[(b - 1, d)] for d in range(c) if (b - 1, d) in best), default=None, key=lambda v: v[0]) if b else (0, [])
            if prev is not None: best[(b, c)] = (prev[0] + score(g, b), prev[1] + [c])
    cuts = [gaps[c] for c in max((v for (b, _), v in best.items() if b == n - 2), key=lambda v: v[0])[1]]
    edges = [a0] + [v for g in cuts for v in g] + [a1 + 1]
    segs = [x[max(0, s * hop - 200): e * hop + 2000] for s, e in zip(edges[::2], edges[1::2])]
    for l, sg, g in zip(lines, segs, cuts + [None]):
        print(f'{len(sg) / SR:5.2f}s {len(l) / (len(sg) / SR):4.1f} 字/秒  停頓 {"" if g is None else (g[1] - g[0]) / 100:<5} {l[:14]}')
    return segs


# ---------- 配音與場景時間 ----------
vo = gemini_all(LINES) if ENGINE == 'gemini' else [tts(i, s) for i, s in enumerate(LINES)]
durs = [round(max(b, LEAD + len(v) / SR + TAIL), 2) for b, v in zip(BASE, vo)]
starts = np.concatenate([[0], np.cumsum(durs)[:-1]])
TOTAL = float(sum(durs)); N = int(TOTAL * SR) + SR
voice = np.zeros(N, np.float32)
for v, s in zip(vo, starts):
    a = int((s + LEAD) * SR); voice[a:a + len(v)] += v
voice *= 0.89 / np.abs(voice).max()


# ---------- 配樂：C–G–Am–F，96 BPM ----------
t = np.arange(N) / SR
BPM = 96; beat = 60 / BPM; bar = beat * 4
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
CHORDS = [[48, 55, 60, 64, 67], [43, 55, 59, 62, 67], [45, 57, 60, 64, 69], [41, 57, 60, 65, 69]]  # C G Am F
rng = np.random.default_rng(15)

def env_ar(n, att, rel):
    e = np.ones(n, np.float32); a, r = int(att * SR), int(rel * SR)
    e[:a] = np.linspace(0, 1, a); e[-r:] *= np.linspace(1, 0, r); return e

def tone(f, n, harm=6, tilt=1.6, detune=0.0):
    tt = np.arange(n) / SR; y = np.zeros(n, np.float32)
    for k in range(1, harm + 1):
        y += np.sin(2 * np.pi * f * k * tt * (1 + detune) + k) / k ** tilt
    return y

def place(buf, x, at):
    a = int(at * SR); b = min(len(buf), a + len(x))
    if b > a: buf[a:b] += x[:b - a]

pad, bass, pluck, drums = (np.zeros(N, np.float32) for _ in range(4))
nbars = int(np.ceil(TOTAL / bar)) + 1
arp = [2, 3, 4, 3, 2, 3, 4, 1]
for b in range(nbars):
    ch = CHORDS[b % 4]; t0 = b * bar; n = int((bar + 0.6) * SR)
    e = env_ar(n, 0.5, 0.9)
    for m in ch[1:]:
        place(pad, (tone(hz(m), n, 5, 1.8, 0.0015) + tone(hz(m), n, 5, 1.8, -0.0015)) * e * 0.5, t0)
    for q in (0, 2):  # 低音：每小節第 1、3 拍
        nb = int(beat * 1.8 * SR); eb = np.exp(-np.arange(nb) / SR * 2.2) * env_ar(nb, 0.01, 0.1)
        place(bass, tone(hz(ch[0] - 12), nb, 3, 2.5) * eb, t0 + q * beat)
    for k in range(8):  # 八分音符琶音
        m = ch[arp[k]] + 12; np_ = int(0.5 * SR)
        ep = np.exp(-np.arange(np_) / SR * 9) * env_ar(np_, 0.004, 0.05)
        place(pluck, tone(hz(m), np_, 4, 2.2) * ep * (1.0 if k % 2 == 0 else 0.7), t0 + k * beat / 2)
    for q in range(4):  # 鼓：1、3 拍大鼓，反拍 hi-hat
        if b == 0 and q < 2: continue
        if q in (0, 2):
            nk = int(0.35 * SR); tk = np.arange(nk) / SR
            f = 45 + 75 * np.exp(-tk * 30)
            place(drums, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tk * 9) * 0.9, t0 + q * beat)
        nh = int(0.05 * SR); hn = np.diff(rng.standard_normal(nh + 1)).astype(np.float32)
        place(drums, hn * np.exp(-np.arange(nh) / SR * 70) * 0.10, t0 + q * beat + beat / 2)

# 場景轉換的輕微 whoosh（濾過的噪音由小到大）
whoosh = np.zeros(N, np.float32)
for s in starts[1:]:
    nw = int(0.5 * SR); w = rng.standard_normal(nw).astype(np.float32)
    w = np.convolve(w, np.ones(24) / 24, 'same')
    place(whoosh, w * np.linspace(0, 1, nw) ** 2 * 0.25, s - 0.45)

def norm(x, rms):  return x * (rms / (np.sqrt(np.mean(x ** 2)) + 1e-9))
music = norm(pad, .05) + norm(bass, .06) + norm(pluck, .025) + norm(drums, .04) + whoosh

# 配音時把配樂壓低（簡易側鏈）
lvl = np.convolve(np.abs(voice), np.ones(int(0.03 * SR)) / int(0.03 * SR), 'same') > 0.01
duck = np.where(lvl, 0.38, 1.0).astype(np.float32)
k = int(0.25 * SR); duck = np.convolve(np.pad(duck, k, mode='edge'), np.ones(k) / k, 'same')[k:-k]
fi, fo = int(0.3 * SR), int(2.0 * SR)
music[:fi] *= np.linspace(0, 1, fi)
end = int(TOTAL * SR); music[end - fo:end] *= np.linspace(1, 0, fo); music[end:] = 0

# 配樂跟著人聲響度走（以 −15 dB 的人聲為基準），換不同聲音時人聲與配樂的比例不變
vr = np.sqrt(np.mean(voice[:end][lvl[:end]] ** 2)); music *= vr / 0.178
mix = (voice + music * duck * 0.9)[:end]
mix = np.tanh(mix * 1.1) / np.tanh(1.1)          # 輕微柔性限幅
mix = (mix / np.abs(mix).max() * 0.95 * 32767).astype(np.int16)
with wave.open(os.path.join(OUT, 'mix.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(mix.tobytes())
json.dump({'durs': durs, 'base': BASE, 'lines': LINES}, open(os.path.join(OUT, 'timing.json'), 'w'), ensure_ascii=False)
print('scenes', durs, 'total', round(TOTAL, 2))
for i, v in enumerate(vo): print(i, round(len(v) / SR, 2), 's')
db = lambda x: round(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9), 1)
on = lvl[:end]
print('voice (spoken)', db(voice[:end][on]), 'dB; music under voice', db((music * duck * 0.9)[:end][on]),
      'dB; music in gaps', db((music * duck * 0.9)[:end][~on]), 'dB')
