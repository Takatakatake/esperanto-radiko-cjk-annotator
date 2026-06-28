# -*- coding: utf-8 -*-
"""
分解が変化する語のうち、ゴールド側で ##偽分解/##強語根分解/##エス的分解 と
マークされた語(=学習用の意図的な細分化、訳が劣化しやすい)がどれだけを占めるか定量化。
"""
import json, sys, re, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp, hat_to_circumflex, replace_esperanto_chars

GOLD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
APP = BASE + r"\Esperanto-Kanji-Ruby-JA"
DATA = APP + r"\app_data"
OLD_ESTEM = DATA + r"\E_stem.json"

ENDINGS = {'o','a','e','i','u','oj','aj','on','an','ojn','ajn','as','is','os','us','n'}
MARKERS = ['##偽分解(PIV正式分解)','##偽分解','##強語根分解','##エス的分解']

def cut_ending(pieces):
    if len(pieces) >= 2 and pieces[-1] in ENDINGS:
        return pieces[:-1]
    return pieces

# gold: nosl -> (slash, markerset)
gold = {}
with open(lp(GOLD), encoding='utf-8') as f:
    raw = f.read()
raw = replace_esperanto_chars(raw, hat_to_circumflex).lower()
for line in raw.split('\n'):
    if not line or line.startswith('##') or ':' not in line:
        continue
    head, _, rest = line.partition(':')
    marks = set(m for m in MARKERS if m in rest)
    # 偽分解(PIV) も 偽分解 に含める集計上の簡略化
    head = head.strip()
    for w in head.split(' '):
        w = w.strip()
        if not w or '#' in w: continue
        pieces = [p for p in w.split('/') if p]
        if not pieces: continue
        sp = cut_ending(pieces)
        if not sp: continue
        nosl = ''.join(sp); slash='/'.join(sp)
        # 同一noslに複数定義があるとき、マーカーは和集合
        if nosl in gold:
            gold[nosl] = (gold[nosl][0], gold[nosl][1] | marks)
        else:
            gold[nosl] = (slash, marks)

with open(lp(OLD_ESTEM), encoding='utf-8') as f:
    old_estem = json.load(f)
old = {}
for x in old_estem:
    if len(x)==2:
        old.setdefault(x[0].replace('/',''), set()).add(x[0])

both = set(old) & set(gold)
changed = []
for k in both:
    gslash = gold[k][0]
    if gslash not in old[k]:
        changed.append(k)

# 分類
cnt = collections.Counter()
marked_changed = 0
unmarked_examples = []
marked_examples = []
for k in changed:
    marks = gold[k][1]
    if marks:
        marked_changed += 1
        for m in marks: cnt[m]+=1
        if len(marked_examples)<15:
            marked_examples.append((k, sorted(old[k]), gold[k][0], sorted(marks)))
    else:
        if len(unmarked_examples)<25:
            unmarked_examples.append((k, sorted(old[k]), gold[k][0]))

print("="*72)
print("【分解変化語のマーカー内訳 (旧E_stemとgoldで分解が異なる語)】")
print(f"分解が変化する語(both内)         : {len(changed)}")
print(f"  うち ##マーカー付き(意図的細分): {marked_changed}")
print(f"  うち マーカー無し(=学術的にも変): {len(changed)-marked_changed}")
print("  マーカー別:")
for m,c in cnt.most_common():
    print(f"    {m}: {c}")
print(f"\n  gold総語(nosl)={len(gold)}  旧E_stem語(nosl)={len(old)}  both={len(both)}")
gold_only = set(gold)-set(old)
gold_only_marked = sum(1 for k in gold_only if gold[k][1])
print(f"  gold のみ(新規語)={len(gold_only)}  うちマーカー付き={gold_only_marked}")

print("\n---- マーカー付き変化(意図的細分・訳劣化しやすい) 例 ----")
for k,o,g,m in marked_examples:
    print(f"  [{k}] 旧={o} → gold={g}  {m}")
print("\n---- マーカー無し変化(学術的にも分解が変わる) 例 ----")
for k,o,g in unmarked_examples:
    print(f"  [{k}] 旧={o} → gold={g}")
