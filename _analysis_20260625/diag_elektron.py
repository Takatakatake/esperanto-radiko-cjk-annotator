# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp
OUT = BASE + r"\_analysis_20260625\out"
DATA = BASE + r"\Esperanto-Kanji-Ruby-JA\app_data"
ESTEM = DATA + r"\E_stem.json"
wa = json.load(open(lp(OUT + r"\word_anno_ja.json"), encoding="utf-8"))
wn = {}
for k,v in wa.items(): wn.setdefault(k.replace('/',''), v)
es = json.load(open(lp(ESTEM), encoding="utf-8"))
print("word_anno['elektr/on'] =", wa.get('elektr/on'))
print("word_anno_nosl['elektron'] =", wn.get('elektron'))
print("word_anno_nosl['komandit'] =", wn.get('komandit'))
print("--- E_stem entries containing 'elektron' (nosl) ---")
for x in es:
    if x[0].replace('/','')=='elektron': print("  ", x)
print("--- E_stem entries nosl startswith 'komandit' ---")
for x in es:
    if x[0].replace('/','').startswith('komandit'): print("  ", x)
print("--- 最終JSONで 'elektrono' を含むkeyの値 ---")
fj = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
for e in fj["全域替换用のリスト(列表)型配列(replacements_final_list)"]:
    if e[0]=='elektrono':
        print("  ", e[0], '->', e[1][:120]); break
