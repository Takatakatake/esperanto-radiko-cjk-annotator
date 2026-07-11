# -*- coding: utf-8 -*-
"""New axis: same word decomposed DIFFERENTLY across documents = at least one is wrong."""
import os, re, sys, collections, html as htmllib
sys.stdout.reconfigure(encoding='utf-8')
CORP = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630\_project_root_misc\京大エス研html文書＿Github"
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)

def parse_words(t):
    t = t[t.find("<body"):] if "<body" in t else t
    t = re.sub(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", lambda x: "\x01" + x.group(1) + "\x01", t)
    t = re.sub(r"<[^>]+>", " ", t); t = htmllib.unescape(t)
    parts = re.split(r"(\x01.*?\x01)", t); words = []; br = []; bw = ""
    for part in parts:
        if part.startswith("\x01") and part.endswith("\x01") and len(part) >= 2:
            r = part[1:-1]; br.append(r); bw += r
        else:
            seg = ""
            for ch in part:
                if ch.isalpha() or ch in "-'": seg += ch
                else:
                    if seg: bw += seg; br.append(seg); seg = ""
                    if bw.strip(): words.append((bw, br))
                    bw = ""; br = []
            if seg: bw += seg; br.append(seg)
    if bw.strip(): words.append((bw, br))
    return words

word_decomps = collections.defaultdict(lambda: collections.Counter())  # lower(word) -> Counter(decomp -> count)
word_docs = collections.defaultdict(lambda: collections.defaultdict(set))  # word -> decomp -> {docs}
for r, _, fs in os.walk(CORP):
    if os.sep + '.git' in r: continue
    for f in fs:
        if not f.lower().endswith(('.html', '.htm')): continue
        h = open(LP(os.path.join(r, f)), encoding='utf-8', errors='ignore').read()
        for word, br in parse_words(h):
            rp = [x for x in br if x.strip()]
            if len(rp) < 1: continue
            nz = word.lower()
            if not re.fullmatch(r"[a-zĉĝĥĵŝŭ\-']+", nz): continue
            dec = '/'.join(p.lower() for p in rp)
            word_decomps[nz][dec] += 1
            word_docs[nz][dec].add(f[:26])

# words with >=2 distinct decompositions
conflicts = []
for w, dc in word_decomps.items():
    if len(dc) >= 2:
        # ignore pure whitespace/case variants (already lowercased)
        variants = list(dc.items())
        conflicts.append((w, variants))
conflicts.sort(key=lambda x: -sum(c for _, c in x[1]))
print(f"文書間で分解が揺れる語: {len(conflicts)}")
for w, variants in conflicts[:60]:
    vs = ' | '.join(f"{d}×{c}" for d, c in sorted(variants, key=lambda x: -x[1]))
    print(f"  {w:22s}: {vs}")
