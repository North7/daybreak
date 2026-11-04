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
    out, plain, ul, ol = ['<div class="part">'], [], False, False
    def close():
        nonlocal ul, ol
        if ul: out.append('</ul>'); ul = False
        if ol: out.append('</ol>'); ol = False
    for ln in text.strip().splitlines():
        figs = [(int(m.group(1) or m.group(3)), m.group(2) or m.group(4)) for m in MARK.finditer(ln)]
        rest = MARK.sub(' ', ln).rstrip()
        if not rest.strip():
            close()
            for n, c in figs: out.append('</div>' + fig(n, c, lang) + '<div class="part">')
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
        for n, c in figs: close(); out.append('</div>' + fig(n, c, lang) + '<div class="part">')
    close(); out.append('</div>')
    return re.sub(r'<div class="part">\s*</div>', '', '\n'.join(out))   # 圖和圖之間的一段＝一個 part，各有複製鈕（JS 加）


def singles(s, lang):
    """「拆出來的單則貼文」：每則一張卡，附複製文字與配圖下載。"""
    head, rest = s.split('\n', 1); items = rest.split('#### ')
    intro = items[0].strip(); cards = []
    for k, it in enumerate(items[1:], 1):
        lab, body_ = it.split('\n', 1)
        txt = '\n'.join(l[2:] if l.startswith('> ') else l.lstrip('>') for l in body_.strip().splitlines())
        m = re.search(r'`(\d+)-[\w-]+?(?:-en)?\.png`', lab); p = IMG.get((int(m.group(1)), lang)) if m else None
        im = f'<a href="{p}" download><img src="{p}" alt="" loading="lazy"></a>' if p else ''
        cid = f'{lang}-single{k}'
        cards.append(f'<div class="single"><div class="sh">{inline(lab)}</div><div class="sb">{im}<p>{inline(txt).replace(chr(10), "<br>")}</p></div>'
                     f'<div class="btns"><button data-copy="{cid}">{"複製文字" if lang == "zh" else "Copy text"}</button>'
                     + (f'<a class="btn" href="{p}" download>{"下載配圖" if lang == "zh" else "Download chart"}</a>' if p else '') +
                     f'</div><textarea hidden id="{cid}">{html.escape(txt)}</textarea></div>')
    return f'<div class="singles"><h2>{html.escape(head.strip())}</h2><p class="meta">{inline(intro)}</p>{"".join(cards)}</div>'


def section(lang, head):
    s = md.split(f'## {head}', 1)[1]; s = re.split(r'\n---\n|\n## ', s, 1)[0]
    title = s.split('### ', 2)[1].split('\n', 1)[1].strip()
    b = s.split('### ', 3)[2].split('\n', 1)[1]
    parts = s.split('### ', 4)
    short = parts[3].split('\n', 1)[1]
    sing = singles(parts[4], lang) if len(parts) > 4 else ''
    short = '\n'.join(l[2:] if l.startswith('> ') else l.lstrip('>') for l in short.strip().splitlines())
    h = body(b, lang)
    steps = {'zh': ['在 X 開「文章」（Articles）→ 新增', '封面上傳下面的封面圖（5:2 橫圖），標題按「複製標題」貼上', '內文一段一段來：按每段右上的「複製這段」→ 貼到 X → 插入下面那張圖（圖下方可下載）→ 再複製下一段',
                    '發布後，用下面的短貼文「引用」這篇長文再發一次；之後幾天照最下面的「單則貼文」各引用一次'],
             'en': ['On X, open Articles → Write', 'Upload the cover below (5:2 landscape); paste the title with "Copy title"', 'Work part by part: tap "Copy part" → paste into X → insert the chart below it (download link under each) → copy the next part',
                    'After publishing, quote the article with the short post below; over the next days, quote it again with each standalone post at the bottom']}[lang]
    nfig = len({n for (n, l) in IMG if l == lang and n})
    cv = IMG.get((0, lang))
    cov = (f'<figure class="cover"><img src="{cv}" alt="cover"><figcaption><span class="n">{"封面" if lang == "zh" else "Cover"}</span>5:2'
           f'<a class="dl" href="{cv}" download>{os.path.basename(cv)} ↓</a></figcaption></figure>') if cv else ''
    return f'''<section id="{lang}" class="art" lang="{'zh-Hant' if lang == 'zh' else 'en'}">
<div class="how"><b>{'怎麼發' if lang == 'zh' else 'How to post'}</b><ol>{''.join(f'<li>{x}</li>' for x in steps)}</ol>
<div class="btns"><button data-copy="{lang}-title">{'複製標題' if lang == 'zh' else 'Copy title'}</button><button data-copyall="{lang}">{'一次複製全文（不含圖）' if lang == 'zh' else 'Copy full text (no charts)'}</button><button data-copy="{lang}-short">{'複製短貼文' if lang == 'zh' else 'Copy short post'}</button></div>
<p class="meta">{nfig} {'張圖' if lang == 'zh' else 'charts'} · ops/articles/img/{date}/</p>{cov}</div>
<h1>{html.escape(title)}</h1>
{h}
<div class="short"><b>{'帶出長文的短貼文' if lang == 'zh' else 'Short post to share the article'}</b><p>{inline(short).replace(chr(10), '<br>')}</p></div>
{sing}
<textarea hidden id="{lang}-title">{html.escape(title)}</textarea><textarea hidden id="{lang}-short">{html.escape(short)}</textarea>
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
.part{{position:relative;border-left:3px solid transparent;padding-left:12px;margin-left:-15px}}.part:hover{{border-left-color:var(--line)}}
.pbtn{{float:right;font:inherit;font-size:13px;border:2px solid var(--ink);background:var(--paper);color:var(--ink);padding:2px 10px;margin:6px 0 6px 10px;cursor:pointer}}
.pbtn small{{color:var(--ink3);font-size:12px}}
.singles{{margin-top:40px}}.single{{background:var(--card);border:1px solid var(--line);padding:12px 16px;margin:14px 0}}
.sh{{font-size:14px;font-weight:700;margin-bottom:8px}}.sb{{display:flex;gap:14px;align-items:flex-start}}.sb img{{width:120px;height:auto;flex:none;border:1px solid var(--line)}}.sb p{{margin:0;font-size:15px}}
a.btn{{font-size:14px;border:2px solid var(--ink);color:var(--ink);padding:4px 12px;text-decoration:none}}
@media (max-width:480px){{.sb{{flex-direction:column}}.sb img{{width:100%}}}}
</style></head><body>
<header><b>破曉 Daybreak · 長文預覽</b><span style="color:var(--ink3);font-size:14px">{html.escape(ttl)}</span>
<div class="tabs"><button data-tab="zh" aria-pressed="true">中文</button><button data-tab="en" aria-pressed="false">English</button></div></header>
<main>{section('zh', '中文')}{section('en', 'English')}</main>
<script>
const show=l=>{{document.querySelectorAll('.art').forEach(s=>s.classList.toggle('on',s.id===l));document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.tab===l));try{{localStorage.setItem('art-lang',l)}}catch(e){{}}}};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>show(b.dataset.tab));
let l='zh';try{{l=localStorage.getItem('art-lang')||(location.hash.slice(1)==='en'?'en':'zh')}}catch(e){{}}show(l);
// 長文內文用 rich text 複製：段落、標題、粗體、清單照原樣進 X 編輯器；純文字一行一段、不留空行（X 會把空行變成空段落）
const block=n=>n.matches('li')?(n.parentElement.matches('ol')?[...n.parentElement.children].indexOf(n)+1+'. ':'・')+n.textContent.trim():n.textContent.trim();
const rich=async(parts,b)=>{{const box=document.createElement('div');parts.forEach(p=>{{const c=p.cloneNode(true);c.querySelectorAll('.pbtn').forEach(x=>x.remove());c.querySelectorAll('[class]').forEach(x=>x.removeAttribute('class'));box.append(...c.childNodes)}});
 const text=[...box.querySelectorAll('h2,h3,p,li')].map(block).join('\\n'),o=b.innerHTML;
 try{{await navigator.clipboard.write([new ClipboardItem({{'text/html':new Blob([box.innerHTML],{{type:'text/html'}}),'text/plain':new Blob([text],{{type:'text/plain'}})}})])}}catch(e){{try{{await navigator.clipboard.writeText(text)}}catch(e2){{b.textContent='✗';setTimeout(()=>b.innerHTML=o,1200);return}}}}
 b.textContent='✓';setTimeout(()=>b.innerHTML=o,1200)}};
document.querySelectorAll('.art').forEach(s=>{{const zh=s.id==='zh',ps=[...s.querySelectorAll('.part')];ps.forEach((p,i)=>{{const f=p.nextElementSibling&&p.nextElementSibling.matches('figure')?p.nextElementSibling.querySelector('.n').textContent:'';
 const b=document.createElement('button');b.className='pbtn';b.innerHTML=(zh?'複製這段':'Copy part')+` ${{i+1}}/${{ps.length}}`+(f?` <small>${{zh?'貼完插入':'then insert'}} ${{f}}</small>`:'');b.onclick=()=>rich([p],b);p.prepend(b)}});
 const all=s.querySelector('[data-copyall]');if(all)all.onclick=()=>rich(ps,all)}});
document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=async()=>{{const t=document.getElementById(b.dataset.copy).value,o=b.textContent;try{{await navigator.clipboard.writeText(t);b.textContent='✓'}}catch(e){{b.textContent='✗'}}setTimeout(()=>b.textContent=o,1200)}});
</script></body></html>'''
out = os.path.join(base, stem + '.html'); open(out, 'w', encoding='utf-8').write(page); print('wrote', os.path.relpath(out))
