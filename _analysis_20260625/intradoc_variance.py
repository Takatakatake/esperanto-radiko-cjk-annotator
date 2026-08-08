# -*- coding: utf-8 -*-
"""同一文書内で同じ語が2通り以上にルビ分解される=校正漏れ(片方が誤り)。文脈同一なので強い信号。"""
import os, re, sys, collections, html as htmllib
sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORP = os.environ.get(
    "ESP_CORPUS_PATH",
    os.path.join(BASE, "_project_root_misc", "京大エス研html文書＿Github"),
)
if not os.path.isdir(CORP):
    raise FileNotFoundError(
        f"京大エス研HTMLコーパスが見つかりません: {CORP}\n"
        "別の場所にある場合は ESP_CORPUS_PATH を指定してください。"
    )
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)
RUBY = re.compile(
    r'<ruby\b[^>]*>\s*([^<]+?)\s*<rt\b[^>]*>((?:[^<]|<br\s*/?>)*?)</rt\s*>\s*</ruby\s*>',
    re.IGNORECASE | re.DOTALL,
)
WORD_BREAK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
    "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
    "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table",
    "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
}
TAG_NAME = re.compile(r"<\s*/?\s*([A-Za-z0-9]+)")
def words_with_gloss(body):
    out = []; i = 0; n = len(body); cur = []
    def flush():
        nonlocal cur
        if cur and any(g is not None for _, g in cur):
            word = ''.join(p for p, _ in cur)
            if re.fullmatch(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ\-']+", word):
                rub = '/'.join(p.lower() for p, g in cur if g is not None)
                gl = {p.lower(): re.sub(r'<br\s*/?>|\s', '', g) for p, g in cur if g is not None}
                out.append((word.lower(), rub, gl))
        cur = []
    while i < n:
        m = RUBY.match(body, i)
        if m:
            cur.append((htmllib.unescape(m.group(1)).strip(), re.sub(r'<br\s*/?>|\s', '', m.group(2)))); i = m.end(); continue
        ch = body[i]
        if ch == '<':
            j = body.find('>', i)
            tag = body[i:j + 1] if j >= 0 else body[i:]
            tag_name = TAG_NAME.match(tag)
            if tag_name and tag_name.group(1).lower() in WORD_BREAK_TAGS:
                flush()
            i = j + 1 if j >= 0 else n; continue
        if ch.isalpha() or ch in "-'":
            j = i
            while j < n and (body[j].isalpha() or body[j] in "-'"): j += 1
            cur.append((body[i:j], None)); i = j; continue
        flush(); i += 1
    flush()
    return out
hits = []
for r, _, fs in os.walk(CORP):
    if os.sep + '.git' in r: continue
    for f in fs:
        if not f.lower().endswith('.html') or f.upper().endswith(('_ZH.HTML', '_KO.HTML')): continue
        full_path = os.path.join(r, f)
        rel_path = os.path.relpath(full_path, CORP).replace(os.sep, '/')
        h = open(LP(full_path), encoding='utf-8', errors='ignore').read()
        body_match = re.search(r'<body\b', h, re.IGNORECASE)
        body = h[body_match.start():] if body_match else h
        wm = collections.defaultdict(collections.Counter)
        wg = {}
        for w, rub, gl in words_with_gloss(body):
            wm[w][rub] += 1
            wg[(w, rub)] = gl
        for w, cc in wm.items():
            if len(cc) >= 2:
                # ルビ分解が文書内で複数(=校正漏れ)
                variants = cc.most_common()
                hits.append((rel_path, w, variants, {v: wg[(w, v)] for v, _ in variants}))
# 語尾のみ違い/大小のみを除外し、語幹の切り方が違うものだけ
def stem_key(rub):
    return rub  # ルビ部分そのまま(語尾は裸なので既に除外されている)
real = []
for f, w, variants, gls in hits:
    keys = set(v for v, _ in variants)
    if len(keys) >= 2:
        real.append((f, w, variants, gls))
real.sort(key=lambda x: -sum(c for _, c in x[2]))
print(f"同一文書内で分解が揺れる語: {len(real)}")
for f, w, variants, gls in real[:40]:
    vs = ' | '.join(f"{v}×{c}" for v, c in variants)
    print(f"  [{f}] {w:20s}: {vs}")
