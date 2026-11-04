#!/usr/bin/env python3
"""長文預覽頁：把 ops/articles/<日期>-<主題>.md 轉成一頁 HTML，圖放在 ［圖 n］／[Chart n] 標的位置，方便照著在 X 長文編輯器貼文、插圖。
用法（在倉庫根目錄）：python3 ops/articles/preview.py ops/articles/2026-11-04-is-the-bull-here.md
輸出：同資料夾、同檔名的 .html（隨網站部署到 GitHub Pages，加 noindex）。圖讀 img/<日期>/<n>-*.png（英文 -en.png）。"""
import html, os, re, sys, glob

src = sys.argv[1]; base = os.path.dirname(os.path.abspath(src)); stem = os.path.splitext(os.path.basename(src))[0]
date = stem[:10]; md = open(src, encoding='utf-8').read()
IMG = {}
for p in glob.glob(os.path.join(base, 'img', date, '*.png')):
    fn = os.path.basename(p); m = re.match(r'(\d+)-(.+?)(-en)?\.png$', fn)
    if m: IMG[(int(m.group(1)), 'en' if m.group(3) else 'zh')] = f'img/{date}/{fn}'

MARK = re.compile(r'\s*(?:［圖 (\d+)(?:：([^］]*))?］|\[Chart (\d+)(?::\s*([^\]]*))?\])\s*')


def inline(t):
    t = html.escape(t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\*(.+?)\*', r'<em>\1</em>', t)
    t = re.sub(r'`(.+?)`', r'<code>\1</code>', t)
    return re.sub(r'(https://[^\s<，。)]+)', r'<a href="\1">\1</a>', t)


def fig(n, cap, lang):
    p = IMG.get((n, lang))
    if not p: return f'<p class="miss">（找不到圖 {n}）</p>'
    lab = f'圖 {n}' if lang == 'zh' else f'Chart {n}'
    fn = os.path.basename(p)
    return (f'<figure id="{lang}-fig{n}"><img src="{p}" alt="{html.escape(cap or lab)}" loading="lazy">'
            f'<figcaption><span class="n">{lab}</span>{html.escape(cap or "")}<a class="dl" href="{p}" download>{fn} ↓</a></figcaption></figure>')


def body(text, lang):
    """把一段 markdown 轉成 HTML，同時回傳要貼進 X 的純文字（拿掉圖位標記）。"""
    out, plain, ul, ol = [], [], False, False
    def close():
        nonlocal ul, ol
        if ul: out.append('</ul>'); ul = False
        if ol: out.append('</ol>'); ol = False
    for ln in text.strip().splitlines():
        figs = [(int(m.group(1) or m.group(3)), m.group(2) or m.group(4)) for m in MARK.finditer(ln)]
        rest = MARK.sub(' ', ln).rstrip()
        if not rest.strip():
            close()
            for n, c in figs: out.append(fig(n, c, lang))
            if not figs: plain.append('')
            continue
        plain.append(rest.replace('**', '').replace('*', ''))
        if rest.startswith('- '):
            if ol: out.append('</ol>'); ol = False
            if not ul: out.append('<ul>'); ul = True
            out.append(f'<li>{inline(rest[2:])}</li>')
        elif re.match(r'\d+\. ', rest):
            if ul: out.append('</ul>'); ul = False
            if not ol: out.append('<ol>'); ol = True
            item = re.sub(r'^\d+\. ', '', rest); out.append(f'<li>{inline(item)}</li>')
        elif re.fullmatch(r'\*\*[^*]+\*\*', rest.strip()):
            close(); lvl = 'h2' if re.match(r'\*\*([一二三四五六七八九十]+、|\d+\. |結論|Bottom line)', rest.strip()) else 'h3'
            out.append(f'<{lvl}>{inline(rest.strip()[2:-2])}</{lvl}>')
        elif rest.startswith('#') and lang and re.fullmatch(r'(#\S+\s*)+', rest.strip()):
            close(); out.append(f'<p class="tags">{inline(rest)}</p>')
        else:
            close(); out.append(f'<p>{inline(rest)}</p>')
        for n, c in figs: close(); out.append(fig(n, c, lang))
    close()
    return '\n'.join(out), re.sub(r'\n{3,}', '\n\n', '\n'.join(plain)).strip()


def section(lang, head):
    s = md.split(f'## {head}', 1)[1]; s = re.split(r'\n---\n|\n## ', s, 1)[0]
    title = s.split('### ', 2)[1].split('\n', 1)[1].strip()
    b = s.split('### ', 3)[2].split('\n', 1)[1]
    short = s.split('### ', 4)[3].split('\n', 1)[1]
    short = '\n'.join(l[2:] if l.startswith('> ') else l.lstrip('>') for l in short.strip().splitlines())
    h, plain = body(b, lang)
    steps = {'zh': ['在 X 開「文章」（Articles）→ 新增', '封面放圖 1，標題貼上', '內文依序貼上；看到圖的位置就插入那張圖（右下角可下載）',
                    '發布後，用下面的短貼文「引用」這篇長文再發一次'],
             'en': ['On X, open Articles → Write', 'Use Chart 1 as the cover; paste the title', 'Paste the body in order; insert each chart where it appears (download link under each)',
                    'After publishing, quote the article with the short post below']}[lang]
    nfig = len({n for (n, l) in IMG if l == lang})
    return f'''<section id="{lang}" class="art" lang="{'zh-Hant' if lang == 'zh' else 'en'}">
<div class="how"><b>{'怎麼發' if lang == 'zh' else 'How to post'}</b><ol>{''.join(f'<li>{x}</li>' for x in steps)}</ol>
<div class="btns"><button data-copy="{lang}-title">{'複製標題' if lang == 'zh' else 'Copy title'}</button><button data-copy="{lang}-body">{'複製內文（不含圖位）' if lang == 'zh' else 'Copy body (no chart markers)'}</button><button data-copy="{lang}-short">{'複製短貼文' if lang == 'zh' else 'Copy short post'}</button></div>
<p class="meta">{nfig} {'張圖' if lang == 'zh' else 'charts'} · ops/articles/img/{date}/</p></div>
<h1>{html.escape(title)}</h1>
{h}
<div class="short"><b>{'帶出長文的短貼文' if lang == 'zh' else 'Short post to share the article'}</b><p>{inline(short).replace(chr(10), '<br>')}</p></div>
<textarea hidden id="{lang}-title">{html.escape(title)}</textarea><textarea hidden id="{lang}-body">{html.escape(plain)}</textarea><textarea hidden id="{lang}-short">{html.escape(short)}</textarea>
</section>'''


ttl = re.search(r'^# (.+)$', md, re.M).group(1)
page = f'''<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>Daybreak 長文預覽</title>
<style>
:root{{--paper:#EEECE6;--ink:#0A0A0A;--ink3:#6B675F;--line:#D2CEC4;--red:#FF3B1F;--card:#F7F6F2}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--paper:#141412;--ink:#F1F0EC;--ink3:#A29E95;--line:#34322E;--red:#FF5A40;--card:#1E1D1A}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.8 -apple-system,"PingFang TC","Noto Sans TC",sans-serif}}
header{{position:sticky;top:0;z-index:2;background:var(--paper);border-bottom:3px solid var(--ink);padding:12px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}}
header b{{font-size:15px}}header .tabs{{margin-left:auto;display:flex;gap:6px}}
.tabs button,.btns button{{font:inherit;font-size:14px;border:2px solid var(--ink);background:transparent;color:var(--ink);padding:4px 12px;cursor:pointer}}
.tabs button[aria-pressed=true]{{background:var(--ink);color:var(--paper)}}
main{{max-width:720px;margin:0 auto;padding:16px 16px 80px}}
.art{{display:none}}.art.on{{display:block}}
h1{{font-size:28px;line-height:1.35;margin:28px 0 8px}}h2{{font-size:21px;margin:36px 0 8px;padding-top:12px;border-top:2px solid var(--ink)}}h3{{font-size:18px;margin:26px 0 4px}}
p,li{{margin:10px 0}}a{{color:var(--red)}}code{{font-size:14px}}
figure{{margin:20px 0;background:var(--card);border:1px solid var(--line);padding:10px}}figure img{{display:block;width:100%;height:auto}}
figcaption{{font-size:14px;color:var(--ink3);margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;align-items:baseline}}
figcaption .n{{background:var(--red);color:#fff;padding:0 8px;font-weight:700}}figcaption .dl{{margin-left:auto}}
.how,.short{{background:var(--card);border:1px solid var(--line);padding:12px 16px;margin:16px 0;font-size:15px}}.how ol{{margin:6px 0;padding-left:22px}}
.btns{{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}}.meta{{color:var(--ink3);font-size:14px;margin:8px 0 0}}
.tags{{color:var(--ink3)}}.miss{{color:var(--red)}}
</style></head><body>
<header><b>破曉 Daybreak · 長文預覽</b><span style="color:var(--ink3);font-size:14px">{html.escape(ttl)}</span>
<div class="tabs"><button data-tab="zh" aria-pressed="true">中文</button><button data-tab="en" aria-pressed="false">English</button></div></header>
<main>{section('zh', '中文')}{section('en', 'English')}</main>
<script>
const show=l=>{{document.querySelectorAll('.art').forEach(s=>s.classList.toggle('on',s.id===l));document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.tab===l));try{{localStorage.setItem('art-lang',l)}}catch(e){{}}}};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>show(b.dataset.tab));
let l='zh';try{{l=localStorage.getItem('art-lang')||(location.hash.slice(1)==='en'?'en':'zh')}}catch(e){{}}show(l);
document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=async()=>{{const t=document.getElementById(b.dataset.copy).value,o=b.textContent;try{{await navigator.clipboard.writeText(t);b.textContent='✓'}}catch(e){{b.textContent='✗'}}setTimeout(()=>b.textContent=o,1200)}});
</script></body></html>'''
out = os.path.join(base, stem + '.html'); open(out, 'w', encoding='utf-8').write(page); print('wrote', os.path.relpath(out))
