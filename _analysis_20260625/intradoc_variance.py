# -*- coding: utf-8 -*-
"""同一文書内で同じ語が2通り以上にルビ分解される=校正漏れ(片方が誤り)。文脈同一なので強い信号。"""
import os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
CORP = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630\_project_root_misc\京大エス研html文書＿Github"
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)
RUBY = re.compile(r'<ruby>([^<]+)<rt[^>]*>((?:[^<]|<br\s*/?>)*?)</rt></ruby>')
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
            cur.append((m.group(1), re.sub(r'<br\s*/?>|\s', '', m.group(2)))); i = m.end(); continue
        ch = body[i]
        if ch == '<':
            j = body.find('>', i); i = j + 1 if j >= 0 else n; continue
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
        if not f.endswith('.html') or f.endswith(('_ZH.html', '_KO.html')): continue
        h = open(LP(os.path.join(r, f)), encoding='utf-8', errors='ignore').read()
        body = h[h.find('<body'):] if '<body' in h else h
        wm = collections.defaultdict(collections.Counter)
        wg = {}
        for w, rub, gl in words_with_gloss(body):
            wm[w][rub] += 1
            wg[(w, rub)] = gl
        for w, cc in wm.items():
            if len(cc) >= 2:
                # ルビ分解が文書内で複数(=校正漏れ)
                variants = cc.most_common()
                hits.append((f[:30], w, variants, {v: wg[(w, v)] for v, _ in variants}))
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
    print(f"  [{f[:26]}] {w:20s}: {vs}")
