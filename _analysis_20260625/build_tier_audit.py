# -*- coding: utf-8 -*-
"""
段階的精度向上の仕組み(修正版): gold見出し(=デプロイ済み分解)を3ティアに分類し監査。
Tier1=2890重要語彙(語形で突合) > Tier2=PEJVO由来(gold行≤44104) > Tier3=PIV由来(>44104)。
ティア別に「分解済み率」「全語根片に訳がある率」を報告し、Tier1詳細を保存。
"""
import re, sys, csv, json, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp, hat_to_circumflex, replace_esperanto_chars

CSV2890 = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\30_重要語彙CSV_日中対照_2890語\2890 Gravaj Esperantaj Vortoj kun Signifoj en la Japana, Ĉina.csv"
GOLD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
OUT = BASE + r"\_analysis_20260625\out"
PEJVO_MAX = 44104
ENDINGS = {'o','a','e','i','u','oj','aj','on','an','ojn','ajn','as','is','os','us','n','j'}

def norm(p):
    return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

# Tier1: 2890語の語形(スラッシュ無し正規化, 接辞は'-'除去)
tier1 = {}
with open(lp(CSV2890), encoding="utf-8") as f:
    for row in csv.reader(f):
        if not row or row[0] == 'Esperanto' or not row[0]: continue
        e = norm(row[0].strip().strip('-')).replace('/', '').replace(' ', '')
        if e:
            tier1[e] = row[3] if len(row) > 3 else ''

# 注釈版 日訳マップ
anno_ja = {}
with open(lp(OUT + r"\anno_root_ja.csv"), encoding="utf-8") as f:
    for row in csv.reader(f):
        if len(row) >= 2: anno_ja[row[0]] = row[1]

def covered(stem):
    pieces = [norm(p) for p in stem.split('/') if len(p) >= 2 and p not in ENDINGS]
    return bool(pieces) and all(p in anno_ja for p in pieces)

stats = {t: {'n':0,'multi':0,'trans':0} for t in (1,2,3)}
t1_rows = []
t1_seen = set()
with open(lp(GOLD), encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        line = line.rstrip('\n')
        if not line or line.startswith('##') or ':' not in line: continue
        head = line.split(':')[0]
        for w in head.split(' '):
            wc = replace_esperanto_chars(w, hat_to_circumflex).lower().strip()
            if '#' in wc or not wc: continue
            nosl = wc.replace('/', '')
            t = 1 if nosl in tier1 else (2 if i <= PEJVO_MAX else 3)
            s = stats[t]; s['n'] += 1
            if '/' in wc: s['multi'] += 1
            cov = covered(wc)
            if cov: s['trans'] += 1
            if t == 1 and nosl not in t1_seen:
                t1_seen.add(nosl)
                t1_rows.append([nosl, tier1[nosl], wc, '' if cov else 'NEEDS_TRANS'])

names = {1:'Tier1 (2890重要語彙)', 2:'Tier2 (PEJVO由来 行≤44104)', 3:'Tier3 (PIV由来 行>44104)'}
print("="*72)
print("【段階的精度監査(修正版): gold見出し=デプロイ分解 をティア別に】")
print(f"Tier1 重要語形(2890CSV): {len(tier1)}  / gold内で一致した重要語形: {len(t1_seen)}")
for t in (1,2,3):
    s = stats[t]
    if not s['n']: continue
    print(f"\n{names[t]}: 見出し {s['n']}")
    print(f"   分解済み(複数片) {s['multi']/s['n']*100:.1f}%")
    print(f"   全語根片に日訳あり {s['trans']/s['n']*100:.1f}%  (未訳含む見出し {s['n']-s['trans']})")

# Tier1詳細保存(レベル昇順=易しい順) — 重要語の分解と訳を一望、未訳をフラグ
t1_rows.sort(key=lambda r: (r[1], r[0]))
with open(lp(OUT + r"\tier1_2890_audit.csv"), "w", encoding="utf-8", newline="") as g:
    w = csv.writer(g); w.writerow(['root_nosl','level','deployed_decomp','flag']); w.writerows(t1_rows)
need = sum(1 for r in t1_rows if r[3])
print(f"\nTier1詳細: out/tier1_2890_audit.csv ({len(t1_rows)}語, 未訳フラグ {need})")
