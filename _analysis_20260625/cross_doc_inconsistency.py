# -*- coding: utf-8 -*-
"""New axis: same word decomposed DIFFERENTLY across documents = at least one is wrong."""
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
    r'<ruby\b[^>]*>\s*([^<]+?)\s*<rt\b[^>]*>.*?</rt\s*>\s*</ruby\s*>',
    re.IGNORECASE | re.DOTALL,
)
WORD_BREAK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
    "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
    "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table",
    "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
}
TAG_NAME = re.compile(r"<\s*/?\s*([A-Za-z0-9]+)")

def parse_words(t):
    """Return only words containing ruby, with ruby-bearing segments as the signature."""
    body_match = re.search(r'<body\b', t, re.IGNORECASE)
    t = t[body_match.start():] if body_match else t
    out = []; i = 0; n = len(t); cur = []
    def flush():
        nonlocal cur
        if cur and any(is_ruby for _, is_ruby in cur):
            word = ''.join(part for part, _ in cur)
            if re.fullmatch(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ\-']+", word):
                signature = '/'.join(part.lower() for part, is_ruby in cur if is_ruby)
                out.append((word, signature))
        cur = []
    while i < n:
        m = RUBY.match(t, i)
        if m:
            cur.append((htmllib.unescape(m.group(1)).strip(), True)); i = m.end(); continue
        ch = t[i]
        if ch == '<':
            j = t.find('>', i)
            tag = t[i:j + 1] if j >= 0 else t[i:]
            tag_name = TAG_NAME.match(tag)
            if tag_name and tag_name.group(1).lower() in WORD_BREAK_TAGS:
                flush()
            i = j + 1 if j >= 0 else n; continue
        if ch.isalpha() or ch in "-'":
            j = i
            while j < n and (t[j].isalpha() or t[j] in "-'"): j += 1
            cur.append((t[i:j], False)); i = j; continue
        flush(); i += 1
    flush()
    return out

word_decomps = collections.defaultdict(lambda: collections.Counter())  # lower(word) -> Counter(decomp -> count)
word_docs = collections.defaultdict(lambda: collections.defaultdict(set))  # word -> decomp -> {docs}
for r, _, fs in os.walk(CORP):
    if os.sep + '.git' in r: continue
    for f in fs:
        if not f.lower().endswith(('.html', '.htm')): continue
        h = open(LP(os.path.join(r, f)), encoding='utf-8', errors='ignore').read()
        for word, dec in parse_words(h):
            nz = word.lower()
            if not re.fullmatch(r"[a-zĉĝĥĵŝŭ\-']+", nz): continue
            word_decomps[nz][dec] += 1
            word_docs[nz][dec].add(os.path.relpath(os.path.join(r, f), CORP).replace(os.sep, '/'))

# words with >=2 distinct decompositions
conflicts = []
for w, dc in word_decomps.items():
    if len(dc) >= 2:
        # ignore pure whitespace/case variants (already lowercased)
        variants = list(dc.items())
        conflicts.append((w, variants))
conflicts.sort(key=lambda x: -sum(c for _, c in x[1]))
print(f"文書間で分解が揺れる語: {len(conflicts)}")
for w, variants in conflicts:
    vs = ' | '.join(f"{d}×{c}" for d, c in sorted(variants, key=lambda x: -x[1]))
    print(f"  {w:22s}: {vs}")
