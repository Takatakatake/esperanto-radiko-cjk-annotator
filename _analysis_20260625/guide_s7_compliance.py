# -*- coding: utf-8 -*-
"""Guide §7 canonical-gloss compliance: corpus affix/function-word glosses vs guide standard."""
import os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
BASE = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630\_project_root_misc\京大エス研html文書＿Github"
CORP = BASE
GUIDE = os.path.join(BASE, 'esperanto_html_redaktado', 'エスペラントルビHTML修正ガイド260328.txt')
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)

# --- Parse §7 standard glosses: lines like "  root  = gloss   (count)" ---
std = {}
in7 = False
for ln in open(LP(GUIDE), encoding='utf-8'):
    if re.match(r'^7\.\s', ln): in7 = True
    if re.match(r'^8\.\s', ln): in7 = False
    if not in7: continue
    m = re.match(r'^\s{2,}([a-zĉĝĥĵŝŭ]{1,6})\s*=\s*([^(※←★\n]+)', ln)
    if m:
        root = m.group(1).strip()
        gloss = m.group(2).strip().replace('<br>', '').replace(' ', '')
        # first gloss only (before 揺れ notes); skip la/kaj (旧慣例 explicitly allowed)
        if root and gloss and root not in ('la', 'kaj'):
            std.setdefault(root, gloss)
print(f"§7標準グロス: {len(std)}語根")

# Known adjudicated-legit exceptions (context-valid alternate glosses)
LEGIT = {
    'en': {'円'}, 'kun': {'[日]訓読み'}, 'ĉar': {'車両', '荷車', '[語]車両'},
    'on': {'[日]音読み'}, 'ĝis': {'さよなら'}, 'al': {'[略]AI', '対格'},
    'da': {'[語]海'}, 'or': {'[化]金', '職業者'}, 'ĉe': {'ところで'},
}

# --- Corpus affix gloss distribution ---
dist = collections.defaultdict(collections.Counter)
sample = {}
for r, _, fs in os.walk(CORP):
    if os.sep + '.git' in r: continue
    for f in fs:
        if not f.endswith('.html') or 'index' in f.lower() or f.endswith(('_ZH.html', '_KO.html')): continue
        h = open(LP(os.path.join(r, f)), encoding='utf-8', errors='ignore').read()
        for m in re.finditer(r'<ruby>([a-zĉĝĥĵŝŭ]{1,6})<rt[^>]*>((?:[^<]|<br\s*/?>)*?)</rt></ruby>', h):
            root = m.group(1).lower()
            if root not in std: continue
            g = re.sub(r'<br\s*/?>|\s', '', m.group(2))
            dist[root][g] += 1
            sample.setdefault((root, g), f[:26])

# --- Detect deviations from standard (excluding legit + proper-noun-tagged) ---
print("\n【§7標準から外れたグロス（正当例外・固有名詞注記を除く）】")
found = 0
for root, gc in sorted(dist.items()):
    canon = std[root]
    for g, n in gc.most_common():
        gn = g.replace('（', '(').replace('）', ')')
        if gn == canon: continue
        if g in LEGIT.get(root, set()): continue
        if re.match(r'^\[.', g): continue  # proper-noun/category tag
        # normalize punctuation variants
        if re.sub(r'[;；,、。()（）]', '', gn) == re.sub(r'[;；,、。()（）]', '', canon): continue
        found += 1
        print(f"  {root:6s} 標準='{canon}' 実='{g}' ×{n}  [{sample[(root,g)]}]")
print(f"\n逸脱候補: {found}")
