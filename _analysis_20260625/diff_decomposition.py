# -*- coding: utf-8 -*-
"""
診断ツール: アプリ現行の E_stem 分解 (旧PEJVO 202501由来) を
WSL ゴールドスタンダード (学習者版 20260416) の分解と比較し、改善余地を定量化する。
アプリのデータは一切変更しない（読み取り専用）。
"""
import json, sys, io, collections, re
sys.stdout.reconfigure(encoding="utf-8")

APP_DIR = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624\Esperanto-Kanji-Ruby-JA\app_data"
ESTEM = APP_DIR + r"\E_stem.json"
ROOTLIST = APP_DIR + r"\root_list.txt"

GOLD_LEARNER = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"

# x形式→字上符 (gold が x形式の可能性に備える。学習者版は字上符だが念のため)
x2c = {'cx':'ĉ','gx':'ĝ','hx':'ĥ','jx':'ĵ','sx':'ŝ','ux':'ŭ','Cx':'Ĉ','Gx':'Ĝ','Hx':'Ĥ','Jx':'Ĵ','Sx':'Ŝ','Ux':'Ŭ'}
def to_circ(t):
    for a,b in x2c.items(): t=t.replace(a,b)
    return t

# 文法語尾（最後のスラッシュ片がこれなら語尾とみなしカット）
ENDINGS = {'o','a','e','i','u','oj','aj','on','an','oin','ojn','ajn','as','is','os','us','n'}

def cut_ending(pieces):
    """gold の見出し pieces から末尾の文法語尾片を1つ落として stem を得る"""
    if len(pieces) >= 2 and pieces[-1] in ENDINGS:
        return pieces[:-1]
    return pieces

# ---- 1) 現行 E_stem 読み込み ----
with open(ESTEM, encoding="utf-8") as f:
    estem = json.load(f)

cur = collections.defaultdict(set)   # nosl(語尾cut済) -> {slash表記,...}
cur_pos = collections.defaultdict(set)
for item in estem:
    if len(item) != 2: continue
    stem, pos = item
    nosl = stem.replace('/','')
    cur[nosl].add(stem)
    cur_pos[nosl].add(pos)

# ---- 2) gold 学習者版 読み込み ----
gold = collections.defaultdict(set)  # nosl -> {slash表記,...}
gold_markers = collections.Counter()
n_lines = 0
n_head_multi = 0
with open(GOLD_LEARNER, encoding="utf-8") as f:
    for line in f:
        line = line.rstrip('\n')
        if not line or line.startswith('##'):  # 行頭 ##重複語 等
            continue
        if ':' not in line:
            continue
        head, _, rest = line.partition(':')
        # 行末マーカー集計（rest 側にある）
        for m in ('##偽分解(PIV正式分解)','##偽分解','##過細分解','##強語根分解','##エス的分解'):
            if m in rest:
                gold_markers[m]+=1
        head = head.strip()
        if not head:
            continue
        # 接辞見出し（-a, -ant- 等）はスキップ（語根抽出は別途）
        if head.startswith('-') or head.endswith('-'):
            continue
        head = to_circ(head)
        # 複合句（スペース区切り）は各語を別個に扱う
        words = head.split(' ')
        if len(words) > 1:
            n_head_multi += 1
        for w in words:
            w = w.strip()
            if not w or '/' not in w and len(w) < 2:
                continue
            pieces = w.split('/')
            pieces = [p for p in pieces if p != '']  # 念のため空片除去
            if not pieces: continue
            stem_pieces = cut_ending(pieces)
            if not stem_pieces: continue
            slash = '/'.join(stem_pieces)
            nosl = ''.join(stem_pieces)
            gold[nosl].add(slash)
        n_lines += 1

# ---- 3) 比較 ----
both = set(cur) & set(gold)
only_cur = set(cur) - set(gold)
only_gold = set(gold) - set(cur)

identical = 0
differ = 0
differ_examples = []
gold_finer = 0   # gold の方が分解が細かい（スラッシュが多い）
gold_coarser = 0
for k in both:
    cs = cur[k]; gs = gold[k]
    if cs == gs:
        identical += 1
    else:
        differ += 1
        # 代表として最も細かい表記同士を比較
        c_best = max(cs, key=lambda s: s.count('/'))
        g_best = max(gs, key=lambda s: s.count('/'))
        if g_best.count('/') > c_best.count('/'):
            gold_finer += 1
        elif g_best.count('/') < c_best.count('/'):
            gold_coarser += 1
        if len(differ_examples) < 40:
            differ_examples.append((k, sorted(cs), sorted(gs)))

print("="*70)
print("【E_stem 分解 差分診断: 現行(旧PEJVO202501) vs Gold(学習者版20260416)】")
print("="*70)
print(f"現行 E_stem ユニーク語幹数(語尾cut, nosl)   : {len(cur)}")
print(f"Gold 見出し由来 ユニーク語幹数(nosl)        : {len(gold)}")
print(f"  gold 複合句見出し(スペース含む)行数       : {n_head_multi}")
print(f"両方に存在 (比較対象)                       : {len(both)}")
print(f"  └ 分解 完全一致                          : {identical}  ({identical/max(len(both),1)*100:.1f}%)")
print(f"  └ 分解 相違                              : {differ}  ({differ/max(len(both),1)*100:.1f}%)")
print(f"        ├ gold の方が細かい                : {gold_finer}")
print(f"        └ gold の方が粗い                  : {gold_coarser}")
print(f"現行のみ存在 (gold に無い語幹)              : {len(only_cur)}")
print(f"gold のみ存在 (現行 E_stem に無い語幹)      : {len(only_gold)}")
print()
print("Gold 行末マーカー出現数:")
for m,c in gold_markers.most_common():
    print(f"  {m}: {c}")
print()
print("---- 分解が相違する例 (最大40件) ----")
for k, cs, gs in differ_examples:
    print(f"  [{k}]  現行={cs}  →  gold={gs}")
