# -*- coding: utf-8 -*-
"""漢字トラックのgold忠実化(ユーザー要望「漢字化は偽分解に忠実に」):
   COARSER+BAREの193語について、goldの深分解でword_kanjiエントリを構築。
   保守規則(偽の友衝突の回避):
     - 漢字割当はマスターcsvに存在する片のみ(発明厳禁)
     - 片長>=4 または SAFE集合(ik/log/logi/metr/graf/fit/derm/drom/naŭt)のみ漢字化
     - 危険な短片(in/id/at/it/ol/uri/an/em/on等)と未割当片はラテン素通し
     - 既存word_kanjiキーがある語(=既にキュレーション済み)には触れない
     - 漢字が1片も付かない語は登録しない(現状維持)
   --write で書込。"""
import json, sys, os, re, csv
sys.stdout.reconfigure(encoding='utf-8')
WRITE = '--write' in sys.argv
ROOT = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630"
BASE = ROOT + r"\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630"
OUT = os.path.join(BASE, '_analysis_20260625', 'out')
GOLD = ROOT + r"\エスペラント辞書徹底語根分解_20260630\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ','C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s

cls = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanji_fidelity.json'), encoding='utf-8'))
targets = [w for w in cls['BARE']] + [w for w, _, _ in cls['COARSER']]
targets = sorted(set(targets))
print(f"対象(COARSER+BARE): {len(targets)}")

gm = {}
for ln in open(LP(GOLD), encoding='utf-8'):
    w = ln.split(':', 1)[0].strip()
    if not w or ' ' in w or w.startswith('#'): continue
    cw = circ(w).replace('-', '')
    gm.setdefault(cw.replace('/', '').lower(), cw.lower())

kanji = {}
for row in csv.reader(open(LP(os.path.join(OUT, 'kanji_root.csv')), encoding='utf-8')):
    if len(row) >= 2 and row[0] and row[1].strip():
        kanji[row[0].strip()] = row[1].strip()

SAFE = {'ik', 'log', 'logi', 'metr', 'graf', 'fit', 'derm', 'drom', 'naŭt'}
GRAM = {'o', 'a', 'i', 'e', 'u', 'n', 'j', 'oj', 'on', 'aj', 'an', 'en'}
wkp = LP(os.path.join(OUT, 'word_kanji.json'))
wk = json.load(open(wkp, encoding='utf-8'))
wk_nosl = {k.replace('/', ''): k for k in wk}

built = {}
skipped = {'既存キー': 0, '漢字ゼロ': 0, 'gold無': 0}
for w in targets:
    if w not in gm: skipped['gold無'] += 1; continue
    if w in wk_nosl or w.rstrip('oaieun') in wk_nosl: skipped['既存キー'] += 1; continue
    pieces = [p for p in gm[w].split('/') if p]
    entry = []; n_k = 0
    for p in pieces:
        if p in GRAM:
            entry.append([p, p])
        elif p in kanji and (len(p) >= 4 or p in SAFE):
            entry.append([p, kanji[p]]); n_k += 1
        else:
            entry.append([p, p])
    if n_k == 0: skipped['漢字ゼロ'] += 1; continue
    built['/'.join(pieces)] = entry

print(f"構築: {len(built)} / skip: {skipped}")
for k, v in list(built.items())[:14]:
    print(f"  {k:28s} → {''.join(g for _, g in v)}")
if WRITE:
    for key, entry in built.items():
        wk[key] = entry
    json.dump(wk, open(wkp, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f"word_kanji書込 → 計{len(wk)}語形")
else:
    print("(dry-run: --write で書込)")
