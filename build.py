"""Static site builder for hyeonlee.net
content/posts/*.html (header comment + body) -> dist/
"""
import json, re, os, html, shutil, glob, datetime
from urllib.parse import quote, unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, 'dist')
C = json.load(open(os.path.join(ROOT, 'config.json'), encoding='utf-8'))
E = html.escape
KST = datetime.timezone(datetime.timedelta(hours=9))
LABELS = C.get('labels', {})
HIDDEN = set(C.get('hidden_categories', []))
UNLISTED = set(C.get('unlisted', []))

SVG = {
    'search': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
    'moon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg>',
    'menu': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    'down': '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>',
}


# ---------- tags ----------
def tkey(t):
    return re.sub(r'[\s\-_·]', '', t.lower())


ALIAS = {tkey(k): v for k, v in C.get('tag_alias', {}).items()}
DROP = {tkey(t) for t in C.get('tag_drop', [])}


def norm_tags(raw):
    out, seen = [], set()
    for t in raw:
        k = tkey(t)
        if not k or k in DROP:
            continue
        v = ALIAS.get(k, t)
        if tkey(v) not in seen:
            seen.add(tkey(v)); out.append(v)
    return out


# ---------- load ----------
def parse(path):
    raw = open(path, encoding='utf-8').read()
    m = re.match(r'\s*<!--(.*?)-->\s*', raw, re.S)
    meta = {}
    for line in m.group(1).strip().splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            meta[k.strip()] = v.strip()
    body = raw[m.end():]
    pid = meta.get('id') or os.path.basename(path).split('.')[0]
    p = dict(id=int(pid), title=meta['제목'], cat=meta.get('카테고리', 'Archive'),
             tags=norm_tags([t.strip() for t in meta.get('태그', '').split(',') if t.strip()]),
             date=meta.get('날짜', ''), mod=meta.get('수정', meta.get('날짜', '')),
             fmt=meta.get('형식', 'html' if ('<style' in body or '<article' in body) else 'legacy'),
             thumb=meta.get('썸네일'), body=body, draft=meta.get('공개', '').lower() in ('n', 'no', '비공개'))
    p['excerpt'] = excerpt(body)
    txt = re.sub(r'<style.*?</style>|<script.*?</script>|<pre.*?</pre>', '', body, flags=re.S)
    txt = re.sub(r'\s+', '', re.sub(r'<[^>]+>', ' ', txt))
    p['mins'] = max(1, round(len(txt) / 400))
    p['series'] = None
    for s in C['series']:
        if s.get('category') and not (p['cat'] == s['category'] or p['cat'].startswith(s['category'] + '/')):
            continue
        if s.get('pattern'):
            mm = re.search(s['pattern'], body)
        elif s.get('title'):
            mm = re.search(s['title'], p['title'])
        else:
            mm = True
        if mm:
            num = None
            if mm is not True and mm.groups() and (mm.group(1) or '').isdigit():
                num = int(mm.group(1))
            p['series'] = [s['key'], num]
            break
    return p


def excerpt(c, n=150):
    m = re.search(r'class="(?:mxb|hl|pc)-lead"[^>]*>(.*?)</p>', c, re.S)
    t = m.group(1) if m else c
    t = re.sub(r'<style.*?</style>|<script.*?</script>|<figcaption.*?</figcaption>', '', t, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'\s+', ' ', html.unescape(t)).strip()
    return t[:n]


def top_of(p):
    return p['cat'].split('/')[0]


allposts = [parse(f) for f in glob.glob(os.path.join(ROOT, 'content/posts/*.html'))]
allposts = [p for p in allposts if not p['draft']]
allposts.sort(key=lambda p: (p['date'], p['id']), reverse=True)
posts = [p for p in allposts if top_of(p) not in HIDDEN and top_of(p) not in UNLISTED]  # listings, menu, search, feeds
SER = {s['key']: s for s in C['series']}
for s in C['series']:
    members = sorted([p for p in posts if p['series'] and p['series'][0] == s['key']], key=lambda p: (p['date'], p['id']))
    for i, p in enumerate(members, 1):
        if p['series'][1] is None:
            p['series'][1] = i
    s['count'] = len(members)
    s['posts'] = sorted(members, key=lambda p: (p['series'][1], p['date']))

# tag counts (listed posts only)
TAGC = {}
for p in posts:
    for t in p['tags']:
        TAGC[t] = TAGC.get(t, 0) + 1
TAGPAGE = {t for t, n in TAGC.items() if n >= C.get('tag_min', 2)}


def in_cat(p, c):
    return p['cat'] == c or p['cat'].startswith(c + '/')


def count(c):
    return sum(1 for p in posts if in_cat(p, c))


def lbl(c):
    return ' · '.join(LABELS.get(x, x) for x in c.split('/'))


# menu = config order + any unknown categories
menu = [[top, list(subs)] for top, subs in C['menu'] if top not in HIDDEN]
for p in posts:
    top, *sub = p['cat'].split('/')
    item_ = next((m for m in menu if m[0] == top), None)
    if not item_:
        menu.append([top, []]); item_ = menu[-1]
    if sub and sub[0] not in item_[1]:
        item_[1].append(sub[0])
menu = [[t, [s for s in subs if count(f'{t}/{s}')]] for t, subs in menu if count(t)]


def cat_url(c):
    return '/category/' + '/'.join(quote(x) for x in c.split('/')) + '/'


def tag_url(t):
    return '/tag/' + quote(t.replace('/', '-'), safe='') + '/'


def purl(p):
    return f'/{p["id"]}/'


def fdate(d):
    return d[:10].replace('-', '.')


# ---------- body transforms ----------
EMOJI_MAP = {'✅': '✓', '✔️': '✓', '✔': '✓', '☑️': '✓', '❌': '✕', '✖️': '✕', '❎': '✕', '⭐': '★', '🌟': '★'}
EMOJI_RE = re.compile('(?:[\U0001F000-\U0001FAFF\u2600-\u2604\u2607-\u26FF\u2700-\u2712\u2714\u2716-\u27BF\u2B50\u2B06\u2B07\u2B05\u27A1\u2934\u2935\u3030\u303D\u3297\u3299\u203C\u2049\u2139\u24C2\u21A9\u21AA\u231A\u231B\u2328\u23CF\u23E9-\u23F3\u23F8-\u23FA][\uFE0F\u200D\u20E3]*)+[ \u00a0]?')


def clean_emoji(s):
    for k, v in EMOJI_MAP.items():
        s = s.replace(k, v)
    s = re.sub('([0-9#*])\uFE0F?\u20E3[ \u00a0]?', r'\1. ', s)
    s = EMOJI_RE.sub('', s)
    return s.replace('\uFE0F', '')


def transform(p):
    body = p['body']
    body = re.sub(r'href="(?:https?://hyeonlee\.net)?/(\d+)"', r'href="/\1/"', body)
    n = [0]

    def alt(m):
        n[0] += 1
        return f'{m.group(1)}alt="{E(p["title"])} 그림 {n[0]}"'
    body = re.sub(r'(<img\b[^>]*?)alt=""', alt, body)
    if p['fmt'] != 'pc':
        body = clean_emoji(body)
    # headings -> ids + toc
    lvl = 'h2' if len(re.findall(r'<h2[\s>]', body)) >= 3 else ('h3' if len(re.findall(r'<h3[\s>]', body)) >= 3 else None)
    toc = []
    if lvl:
        def hid(m):
            attrs, inner = m.group(1) or '', m.group(2)
            text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', inner))).strip()
            if not text:
                return m.group(0)
            idm = re.search(r'\bid="([^"]+)"', attrs)
            hid_ = idm.group(1) if idm else f's{len(toc) + 1}'
            toc.append((hid_, text[:60]))
            if not idm:
                attrs = f' id="{hid_}"' + attrs
            return f'<{lvl}{attrs}>{inner}</{lvl}>'
        body = re.sub(rf'<{lvl}(\s[^>]*)?>(.*?)</{lvl}>', hid, body, flags=re.S)
    return body, (toc if len(toc) >= 4 else [])


# ---------- components ----------
def head(title, desc, url, image=None, extra='', noindex=False):
    full = f"{title} | {C['site']}" if title != C['site'] else title
    img = C['url'] + (image or '/img/og.png')
    ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={C["adsense"]}" '
           f'crossorigin="anonymous"></script>') if C.get('adsense') else ''
    if C.get('goatcounter'):
        ads += f'<script data-goatcounter="https://{C["goatcounter"]}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>'
    robots = '<meta name="robots" content="noindex,follow">\n' if noindex else ''
    return f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(full)}</title>
<meta name="description" content="{E(desc)}">
{robots}<link rel="canonical" href="{C['url']}{url}">
<meta property="og:type" content="{'article' if extra else 'website'}">
<meta property="og:site_name" content="{C['site']}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{C['url']}{url}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="google-site-verification" content="{C['google_verification']}">
<link rel="alternate" type="application/rss+xml" title="{C['site']}" href="/rss.xml">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap">
<link rel="stylesheet" href="/base.css?v={VER}">
<script>try{{var t=localStorage.getItem('theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
{ads}
{extra}
</head>
<body>
{header()}'''


def header():
    nav = []
    for top, subs in menu:
        if not subs:
            nav.append(f'<div><a class="top" href="{cat_url(top)}">{E(lbl(top))}</a></div>')
        else:
            dd = f'<a href="{cat_url(top)}">전체<span>{count(top)}</span></a>' + ''.join(
                f'<a href="{cat_url(top + "/" + s)}">{E(lbl(s))}<span>{count(top + "/" + s)}</span></a>' for s in subs)
            nav.append(f'<div><button class="top" type="button">{E(lbl(top))}{SVG["down"]}</button><div class="dd">{dd}</div></div>')
    nav.append(f'<div><a class="top" href="/series/">시리즈</a></div>')
    drawer = ''.join(
        f'<a href="{cat_url(t)}">{E(lbl(t))}<span>{count(t)}</span></a>' + ''.join(
            f'<a class="sub" href="{cat_url(t + "/" + s)}">{E(lbl(s))}<span>{count(t + "/" + s)}</span></a>' for s in subs)
        for t, subs in menu) + f'<a href="/series/">시리즈</a><a href="{C["about"]}">소개</a>'
    return f'''<header class="hd"><div class="wrap">
  <a class="logo" href="/">{C['site']}</a>
  <nav class="nav">{''.join(nav)}</nav>
  <div class="tools">
    <a class="about-lk" href="{C['about']}">소개</a>
    <a class="icon-btn" href="/search/" aria-label="검색">{SVG['search']}</a>
    <button class="icon-btn" id="theme" type="button" aria-label="화면 모드 전환">{SVG['moon']}</button>
    <button class="icon-btn menu-btn" id="menu" type="button" aria-label="메뉴" aria-expanded="false">{SVG['menu']}</button>
  </div>
</div><div class="drawer" id="drawer"><div class="wrap">{drawer}</div></div></header>'''


def footer():
    return f'''<footer class="ft"><div class="wrap"><span>© {C['site']}</span><nav><a href="{C['about']}">소개</a><a href="/series/">시리즈</a><a href="/rss.xml">RSS</a></nav></div></footer>
<script src="/site.js?v={VER}" defer></script>
</body></html>'''


def ser_badge(p, link=False):
    if not p['series']:
        return ''
    s = SER[p['series'][0]]
    t = f'{E(s["name"])} {p["series"][1]}/{s["count"]}'
    return f'<a class="sr" href="{ser_url(s)}">{t}</a>' if link else f'<span class="sr">{t}</span>'


def item(p, feat=False):
    ex = f'<p class="le">{E(p["excerpt"])}</p>' if p['excerpt'] and p['excerpt'] != p['title'] else ''
    return (f'<li{" class=feat" if feat else ""}><a href="{purl(p)}"><div><p class="lt">{E(p["title"])}</p>{ex}'
            f'<div class="lm">{ser_badge(p)}<span class="cat">{E(lbl(p["cat"]))}</span><span class="dot"></span>'
            f'<span>{fdate(p["date"])}</span></div></div></a></li>')


def side():
    cats = ''.join(
        f'<li><a href="{cat_url(t)}">{E(lbl(t))}<span>{count(t)}</span></a>' +
        (('<ul>' + ''.join(f'<li><a href="{cat_url(t + "/" + s)}">{E(lbl(s))}<span>{count(t + "/" + s)}</span></a></li>' for s in subs) + '</ul>') if subs else '') +
        '</li>' for t, subs in menu)
    sers = ''.join(f'<li><a href="{ser_url(s)}">{E(s["name"])}<span>{s["count"]}</span></a></li>' for s in C['series'] if s['count'])
    return (f'<aside class="side"><div class="card"><h3>카테고리</h3><ul class="cats">{cats}</ul></div>'
            f'<div class="card"><h3>시리즈</h3><ul class="cats">{sers}</ul></div></aside>')


def write(path, s):
    full = os.path.join(DIST, unquote(path).lstrip('/'))
    if full.endswith('/'):
        full += 'index.html'
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, 'w', encoding='utf-8').write(s)


def listing(title, sub, url, items, tabs='', noindex=False):
    lis = ''.join(item(p) for p in items) or '<li class="empty">글이 없습니다</li>'
    return (head(title, f'{title} · {len(items)}편', url, noindex=noindex) +
            f'<section class="band"><div class="wrap"><h1>{E(title)}</h1><p>{E(sub)}</p></div></section>'
            f'<main class="flat"><div class="wrap"><div class="grid lift"><div class="card">{tabs}'
            f'<ul class="list" data-page="10">{lis}</ul><div class="pager"></div></div>{side()}</div></div></main>' + footer())


def ser_url(s):
    return f'/series/{s["key"].lower()}/'


def ser_card(s):
    return (f'<a class="card ser" href="{ser_url(s)}"><span class="badge p">시리즈</span><span class="t">{E(s["name"])}</span>'
            f'<p class="d">{E(s["desc"])}</p><div class="cnt">{s["count"]}편</div></a>')


# ---------- build ----------
VER = datetime.datetime.now(KST).strftime('%Y%m%d%H%M')
if os.path.exists(DIST):
    shutil.rmtree(DIST)
shutil.copytree(os.path.join(ROOT, 'static'), DIST)

# home
BYID = {p['id']: p for p in allposts}
feat = [BYID[i] for i in C.get('featured', []) if i in BYID]
ser_cards = ''.join(ser_card(s) for s in C['series'] if s['count'] and s.get('home'))
home_list = ''.join(item(p) for p in [q for q in posts if q not in feat][:8])
feat_list = ''.join(item(p, True) for p in feat)
write('/', head(C['site'], C['lead'], '/') + f'''<section class="hero"><div class="hero-bg"></div><div class="wrap">
  <h1>{C['site']}</h1><p class="lead">{E(C['lead'])}</p>
  <div class="links"><a class="btn solid" href="{C['about']}">소개</a><a class="btn" href="/series/">시리즈 보기</a></div>
</div></section>
<main class="flat"><div class="wrap">
  <div class="series lift">{ser_cards}</div>
  <div class="grid"><div class="col">
    <div class="card"><div class="sec-h"><h2 class="h2">대표 글</h2></div><ul class="list">{feat_list}</ul></div>
    <div class="card"><div class="sec-h"><h2 class="h2">최근 글</h2><a href="/category/">전체 보기</a></div><ul class="list">{home_list}</ul></div>
  </div>{side()}</div>
</div></main>''' + footer())

# all posts
write('/category/', listing('전체 글', f'{len(posts)}편', '/category/', posts))

# categories
for top, subs in menu:
    for c in [top] + [f'{top}/{s}' for s in subs]:
        items = [p for p in posts if in_cat(p, c)]
        tabs = ''
        if subs:
            tabs = '<div class="seg">' + f'<a class="{"on" if c == top else ""}" href="{cat_url(top)}">전체 {count(top)}</a>' + ''.join(
                f'<a class="{"on" if c == top + "/" + s else ""}" href="{cat_url(top + "/" + s)}">{E(lbl(s))} {count(top + "/" + s)}</a>' for s in subs) + '</div>'
        write(cat_url(c), listing(lbl(c), f'{len(items)}편', cat_url(c), items, tabs))

# series
write('/series/', head('시리즈', '연재 글 모음', '/series/') +
      '<section class="band"><div class="wrap"><h1>시리즈</h1><p>' + f'{sum(1 for s in C["series"] if s["count"])}개' + '</p></div></section>'
      '<main class="flat"><div class="wrap"><div class="series lift">' + ''.join(ser_card(s) for s in C['series'] if s['count']) + '</div></div></main>' + footer())
for s in C['series']:
    if s['count']:
        write(ser_url(s), listing(s['name'], f'{s["count"]}편 · {s["desc"]}', ser_url(s), s['posts']))

# tags (only tags shared by 2+ posts)
for t in TAGPAGE:
    items = [p for p in posts if t in p['tags']]
    write(tag_url(t), listing('#' + t, f'{len(items)}편', tag_url(t), items))


# posts
def related(p, n=3):
    pool = [q for q in posts if q is not p and not (p['series'] and q['series'] and q['series'][0] == p['series'][0])]
    def score(q):
        s = len(set(q['tags']) & set(p['tags'])) * 2
        if q['cat'] == p['cat']:
            s += 3
        elif top_of(q) == top_of(p):
            s += 1
        return (s, q['date'])
    pool.sort(key=score, reverse=True)
    return [q for q in pool[:n] if score(q)[0] > 0]


GISCUS = C['giscus']
for p in allposts:
    hidden = top_of(p) in HIDDEN
    if p['series'] and not hidden:
        sp = SER[p['series'][0]]['posts']
        i = sp.index(p)
        prev, nxt = (sp[i - 1] if i > 0 else None), (sp[i + 1] if i + 1 < len(sp) else None)
        kp, kn = '이전 편', '다음 편'
    else:
        same = [q for q in allposts if q['cat'] == p['cat']]
        i = same.index(p)
        prev, nxt = (same[i + 1] if i + 1 < len(same) else None), (same[i - 1] if i > 0 else None)
        kp, kn = '이전 글', '다음 글'
    top, *sub = p['cat'].split('/')
    if hidden or top in UNLISTED:
        crumb = f'<span>{E(lbl(top))}</span>' + (f'<span>›</span><span>{E(lbl(sub[0]))}</span>' if sub else '')
    else:
        crumb = f'<a href="{cat_url(top)}">{E(lbl(top))}</a>' + (f'<span>›</span><a href="{cat_url(p["cat"])}">{E(lbl(sub[0]))}</a>' if sub else '')
    tags = ''.join(f'<a class="tag" href="{tag_url(t)}">#{E(t)}</a>' for t in p['tags'] if t in TAGPAGE and not hidden)
    pn = (f'<a class="card prev" href="{purl(prev)}"><div class="k">{kp}</div><div class="t">{E(prev["title"])}</div></a>' if prev else '<span></span>') + \
         (f'<a class="card next" href="{purl(nxt)}"><div class="k">{kn}</div><div class="t">{E(nxt["title"])}</div></a>' if nxt else '')
    body, toc = transform(p)
    paper = ' paper' if p['fmt'] == 'html' and 'var(--g90)' not in body and 'class="pb pb-' not in body else ''
    if p['fmt'] == 'legacy':
        body = f'<div class="legacy">{body}</div>'
    kind = ' k-aws' if p['cat'] == 'Study/AWS' else ''
    # series box
    serbox = ''
    if p['series'] and not hidden:
        s = SER[p['series'][0]]
        lis = ''.join(f'<li{" class=on" if q is p else ""}><a href="{purl(q)}"><span>{q["series"][1]}</span>{E(q["title"])}</a></li>' for q in s['posts'])
        serbox = (f'<details class="card serbox"><summary><span class="k">시리즈</span><b>{E(s["name"])}</b>'
                  f'<span class="n">{p["series"][1]}/{s["count"]}</span></summary><ol>{lis}</ol></details>')
    rel = '' if hidden else related(p)
    relbox = ''
    if rel:
        relbox = '<div class="card relbox"><h2 class="h2">함께 읽을 글</h2><ul class="list">' + ''.join(item(q) for q in rel) + '</ul></div>'
    cm = ''
    if GISCUS.get('repo_id') and GISCUS.get('category_id'):
        cm = (f'<div class="card cmt"><h2 class="h2">댓글</h2><script src="https://giscus.app/client.js" data-repo="{GISCUS["repo"]}" '
              f'data-repo-id="{GISCUS["repo_id"]}" data-category="{GISCUS["category"]}" data-category-id="{GISCUS["category_id"]}" '
              f'data-mapping="pathname" data-strict="1" data-reactions-enabled="1" data-emit-metadata="0" data-input-position="top" '
              f'data-theme="preferred_color_scheme" data-lang="ko" data-loading="lazy" crossorigin="anonymous" async></script></div>')
    ld = json.dumps({"@context": "https://schema.org", "@type": "BlogPosting", "headline": p['title'],
                     "datePublished": p['date'].replace(' ', 'T') + ':00+09:00', "dateModified": p['mod'].replace(' ', 'T') + ':00+09:00',
                     "url": f"{C['url']}{purl(p)}", "author": {"@type": "Person", "name": C['site']}}, ensure_ascii=False)
    hl = ''
    if p['fmt'] == 'legacy' and '<pre' in body:
        hl = ('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">'
              '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js" defer></script>'
              '<script>addEventListener("DOMContentLoaded",function(){if(window.hljs)document.querySelectorAll(".legacy pre code").forEach(function(e){hljs.highlightElement(e)})})</script>')
    tocbox = ''
    if toc:
        tocbox = '<aside class="toc"><div class="toc-in"><p>목차</p><ol>' + ''.join(f'<li><a href="#{E(h)}">{E(t)}</a></li>' for h, t in toc) + '</ol></div></aside>'
    meta = f'<span>{fdate(p["date"])}</span><span class="dot"></span><span>{p["mins"]}분</span>' + (f'{ser_badge(p, True)}' if p['series'] and not hidden else '')
    foot = f'<div class="post-foot tags">{tags}</div>' if tags else ''
    write(purl(p), head(p['title'], p['excerpt'] or p['title'], purl(p), p['thumb'],
                        f'<script type="application/ld+json">{ld}</script>{hl}', noindex=hidden) + f'''
<main class="post"><div class="wrap"><div class="post-grid{' has-toc' if toc else ''}">
  <div class="post-col">
    <header class="post-h"><div class="crumb">{crumb}</div><h1>{E(p['title'])}</h1><div class="lm">{meta}</div></header>
    <article class="card post-card{paper}{kind}"><div class="post-body">{body}</div>{foot}</article>
    {serbox}
    <nav class="pn" aria-label="이전 다음">{pn}</nav>
    {relbox}{cm}
  </div>{tocbox}
</div></div></main>''' + footer())

# redirects for moved category pages
for old, new in C.get('redirects', {}).items():
    write(old, f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="robots" content="noindex">'
               f'<link rel="canonical" href="{C["url"]}{new}"><meta http-equiv="refresh" content="0; url={new}">'
               f'<title>이동</title></head><body><a href="{new}">이동</a></body></html>')

# search
idx = [dict(i=p['id'], t=p['title'], e=p['excerpt'], c=lbl(p['cat']), d=fdate(p['date']), g=p['tags']) for p in posts]
json.dump(idx, open(os.path.join(DIST, 'search.json'), 'w', encoding='utf-8'), ensure_ascii=False)
write('/search/', head('검색', '글 검색', '/search/', noindex=True) +
      '<section class="band"><div class="wrap"><h1>검색</h1><p>제목·요약·태그</p></div></section>'
      '<main class="flat"><div class="wrap"><div class="grid lift"><div class="card"><form class="search-box" onsubmit="return false">'
      '<input id="q" type="search" placeholder="검색어 입력" autocomplete="off" aria-label="검색어"></form>'
      '<ul class="list" id="results"></ul></div>' + side() + '</div></div></main>' + footer())

# 404
write('/404.html', head('페이지 없음', '페이지를 찾을 수 없습니다', '/404.html', noindex=True) +
      '<section class="band"><div class="wrap"><h1>페이지를 찾을 수 없습니다</h1><p>주소가 바뀌었거나 삭제된 글입니다</p></div></section>'
      '<main class="flat"><div class="wrap"><div class="card lift pad"><a class="btn" href="/">홈으로</a> <a class="btn" href="/search/">검색</a></div></div></main>' + footer())

# rss
now = datetime.datetime.now(KST)
def rfc(d):
    return datetime.datetime.strptime(d[:16], '%Y-%m-%d %H:%M').replace(tzinfo=KST).strftime('%a, %d %b %Y %H:%M:%S +0900')
rss = ''.join(f'<item><title>{E(p["title"])}</title><link>{C["url"]}{purl(p)}</link><guid>{C["url"]}{purl(p)}</guid>'
              f'<pubDate>{rfc(p["date"])}</pubDate><category>{E(lbl(p["cat"]))}</category><description>{E(p["excerpt"])}</description></item>' for p in posts[:30])
open(os.path.join(DIST, 'rss.xml'), 'w', encoding='utf-8').write(
    f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{C["site"]}</title><link>{C["url"]}</link>'
    f'<description>{E(C["lead"])}</description><language>ko</language><lastBuildDate>{now.strftime("%a, %d %b %Y %H:%M:%S +0900")}</lastBuildDate>{rss}</channel></rss>')

# sitemap / robots / ads / CNAME
listed_extra = [p for p in allposts if top_of(p) in UNLISTED]
urls = [('/', None), ('/category/', None), ('/series/', None)] + [(cat_url(t), None) for t, _ in menu] + \
       [(cat_url(f'{t}/{s}'), None) for t, ss in menu for s in ss] + [(ser_url(s), None) for s in C['series'] if s['count']] + \
       [(purl(p), p['mod'][:10]) for p in posts + listed_extra]
open(os.path.join(DIST, 'sitemap.xml'), 'w', encoding='utf-8').write(
    '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
    ''.join(f'<url><loc>{C["url"]}{u}</loc>' + (f'<lastmod>{m}</lastmod>' if m else '') + '</url>' for u, m in urls) + '</urlset>')
open(os.path.join(DIST, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nDisallow: /admin/\nSitemap: {C["url"]}/sitemap.xml\n')
if C.get('adsense'):
    open(os.path.join(DIST, 'ads.txt'), 'w').write(f'google.com, {C["adsense"].replace("ca-", "")}, DIRECT, f08c47fec0942fa0\n')
open(os.path.join(DIST, 'CNAME'), 'w').write(C['url'].split('//')[1] + '\n')
open(os.path.join(DIST, '.nojekyll'), 'w').write('')
print(f'built {len(posts)} listed / {len(allposts)} total posts, {len(TAGPAGE)} tag pages, {len(menu)} top categories -> {DIST}')
