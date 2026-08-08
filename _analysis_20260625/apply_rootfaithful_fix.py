# -*- coding: utf-8 -*-
"""
root-faithful修正workflowの結果を word_anno_{ja,zh,ko}.json に適用する。
fix_type1: 各語のword_annoエントリの語根片グロスを語根忠実値に置換。
whole_word: 単語全体を1ルビ(定義訳)に。
uncertain: 触らず、レビュー用に列挙。
"""
import json, sys, re, os, shutil
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp
OUT = BASE + r"\_analysis_20260625\out"
WF_OUT = r"C:\Users\yt\AppData\Local\Temp\claude\d--GoogleDrive202510--------20----------------------------20260624\46f52639-acfa-48a8-8c2f-e95e8e59b22d\tasks\wfw28thw0.output"
ENDINGS = ['oj','aj','ojn','ajn','as','is','os','us','on','an','o','a','e','i','u','j','n']

# --- workflow結果読み込み ---
with open(lp(WF_OUT), encoding="utf-8") as f:
    content = f.read()
# result JSON抽出 (出力ファイルは {summary, logs, result:{...}} 構造)
obj = json.loads(content)
res = obj.get('result', obj)
fixes = res.get('fixes', [])
wholes = res.get('wholes', [])
uncertain = res.get('uncertain', [])
print(f"workflow結果: fix={len(fixes)} whole={len(wholes)} uncertain={len(uncertain)}")

# --- 既存マップ ---
anno = {}
for L in ('ja','zh','ko'):
    with open(lp(OUT + f"\\word_anno_{L}.json"), encoding="utf-8") as f:
        anno[L] = json.load(f)
nosl2key = {k.replace('/',''): k for k in anno['ja'].keys()}

def find_key(word_nosl):
    """fix語(語尾付きnosl)から word_anno キー(語幹)を特定。"""
    if word_nosl in nosl2key: return nosl2key[word_nosl]
    for e in ENDINGS:
        if word_nosl.endswith(e):
            st = word_nosl[:-len(e)]
            if st in nosl2key: return nosl2key[st]
    return None

applied = 0; compound = 0; skipped = []
def apply_pieces(key, fixed_map):
    changed = False
    for L in ('ja','zh','ko'):
        cur = anno[L].get(key)
        if not cur: continue
        new = []
        for piece, gloss in cur:
            if piece in fixed_map and fixed_map[piece].get(L):
                new.append([piece, fixed_map[piece][L]]); changed = True
            else:
                new.append([piece, gloss])
        anno[L][key] = new
    return changed

for fx in fixes:
    word = fx['word']
    fp = fx.get('fixed_pieces') or []
    if not fp: continue
    fixed_map = {p['root']: p for p in fp if p.get('root')}
    key = find_key(word)
    if key and apply_pieces(key, fixed_map):
        applied += 1
    else:
        # 複合語: 構成要素キーに適用(キーの全片がfixed_mapにあり、keyのnoslがwordに含まれる)
        hit = False
        for k in list(anno['ja'].keys()):
            kn = k.replace('/','')
            if kn and kn in word:
                pieces = [p for p in k.split('/') if len(p) >= 2]
                if pieces and any(p in fixed_map for p in pieces):
                    if apply_pieces(k, fixed_map): hit = True
        if hit: compound += 1
        else: skipped.append(word)

# whole_word: 単語全体1ルビ
whole_applied = 0
for wh in wholes:
    word = wh['word']; w = wh.get('whole') or {}
    key = find_key(word)
    if not key: skipped.append(word+'(whole)'); continue
    stem_nosl = key.replace('/','')
    for L in ('ja','zh','ko'):
        if w.get(L):
            anno[L][key] = [[stem_nosl, w[L]]]
    whole_applied += 1

# 保存(バックアップ)
for L in ('ja','zh','ko'):
    src = OUT + f"\\word_anno_{L}.json"
    shutil.copy2(lp(src), lp(src + ".bak_preRootfaithful"))
    with open(lp(src), "w", encoding="utf-8") as g:
        json.dump(anno[L], g, ensure_ascii=False)

print(f"適用: 単語版fix={applied}  複合語fix={compound}  whole_word={whole_applied}")
print(f"未マップ(要確認) {len(skipped)}: {skipped[:20]}")
print(f"uncertain(人手レビュー) {len(uncertain)}: {uncertain}")
# 検算: anestez, agronom, hidr 周辺
for k in ['an/estez','agr/o/nom/i','astr/o/nom/i','cikl/hidr/o/karbon','amel/az']:
    if k in anno['ja']: print(f"  確認 {k} → ja {anno['ja'][k]}")
