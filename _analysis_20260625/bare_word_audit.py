# -*- coding: utf-8 -*-
"""§3.2 未注音単語(注釈漏れ)監査: ルビを1つも持たないエスペラント語トークンを検出。
   境界監査はルビ付き語のみ対象のため、この層は今まで一度も測定されていない。"""
import os, re, sys, collections, html as htmllib, json
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)
BASE = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630"
CORP = os.path.join(BASE, '_project_root_misc', '京大エス研html文書＿Github')

# エスペラント語彙(E_stem 68k语幹 + 機能語)
es = json.load(open(LP(os.path.join(BASE, 'Esperanto-Kanji-Ruby-JA', 'app_data', 'E_stem.json')), encoding='utf-8'))
STEMS = set()
for e in es:
    s = (e[0] if isinstance(e, list) else e)
    STEMS.add(str(s).replace('/', '').lower())
FUNC = {'la','kaj','de','en','al','el','por','kun','pri','pro','per','sur','sub','ĉe','ĝis','dum','laŭ','post','inter','kontraŭ','tra','trans','sen','je','da','do','ja','jes','ne','nur','ankaŭ','ankoraŭ','jam','tuj','eĉ','tre','tro','pli','plej','plu','ol','se','ke','ĉu','ĉar','sed','aŭ','nek','mi','vi','li','ŝi','ĝi','ni','ili','oni','si','min','vin','lin','ŝin','ĝin','nin','ilin','onin','sin'}
ENDS = ("ojn","oj","on","o","ajn","aj","an","a","en","e","i","as","is","os","us","u","jn","j","n")
def is_esperanto(w):
    wl = w.lower()
    if wl in FUNC or wl in STEMS: return True
    for s in ENDS:
        if wl.endswith(s) and len(wl) - len(s) >= 2 and wl[:-len(s)] in STEMS:
            return True
    return False

# 語再構成: ルビ片を含む語はルビ有り、含まない語は裸
RUBY = re.compile(r'<ruby>([^<]+)<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt></ruby>')
def scan(body):
    bare = []
    i = 0; n = len(body); cur = []; has_ruby = False
    def flush():
        nonlocal cur, has_ruby
        if cur and not has_ruby:
            w = ''.join(cur)
            if re.fullmatch(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ][A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ']+", w):
                bare.append(w)
        cur = []; has_ruby = False
    while i < n:
        m = RUBY.match(body, i)
        if m:
            cur.append(m.group(1)); has_ruby = True; i = m.end(); continue
        ch = body[i]
        if ch == '<':
            j = body.find('>', i)
            tag = body[i:j+1] if j >= 0 else ''
            i = j + 1 if j >= 0 else n
            if re.match(r'</(p|div|h[1-6]|li|td|th|tr|br|title)', tag) or re.match(r'<(p|div|h[1-6]|li|td|th|tr|br|title)', tag):
                flush()
            continue
        if ch.isalpha() or ch == "'":
            if ord(ch) < 0x3000 or ch in 'ĉĝĥĵŝŭĈĜĤĴŜŬ':
                cur.append(ch); i += 1; continue
            else:
                flush(); i += 1; continue
        flush(); i += 1
    flush()
    return bare

tot = collections.Counter()
bydoc = collections.Counter()
samples = collections.defaultdict(set)
for r, _, fs in os.walk(LP(CORP)):
    if os.sep + '.git' in r: continue
    for f in fs:
        if not f.endswith('.html') or 'index' in f.lower(): continue
        h = open(os.path.join(r, f), encoding='utf-8', errors='ignore').read()
        body = h[h.find('<body'):] if '<body' in h else h
        body = htmllib.unescape(body)
        for w in scan(body):
            if len(w) >= 2 and is_esperanto(w):
                tot[w] += 1
                bydoc[f[:30]] += 1
                if len(samples[w]) < 2: samples[w].add(f[:24])
print(f"裸エスペラント語トークン: {sum(tot.values()):,} (種類 {len(tot):,})")
print("\n=== 頻度上位30 ===")
for w, c in tot.most_common(30):
    print(f"  {w:16s} ×{c:4d}  例:{sorted(samples[w])[:2]}")
print("\n=== 文書別上位10 ===")
for d, c in bydoc.most_common(10):
    print(f"  {d}: {c}")
json.dump({w: c for w, c in tot.most_common(500)}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bare_words.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
