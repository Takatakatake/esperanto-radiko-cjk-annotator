# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp
APP = BASE + r"\Esperanto-Kanji-Ruby-KO"
DATA = APP + r"\app_data"
combined = generate(APP, DATA,
    DATA + r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv",
    DATA + r"\世界语单词词根分解方法の使用者自定义设置.json",
    DATA + r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json",
    DATA + r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json",
    DATA + r"\世界语全部词根_约11137个_202501.txt",
    'HTML格式_Ruby文字_大小调整')
with open(lp(DATA + r"\置換リスト_ルビ.json"), encoding='utf-8') as f:
    ex = json.load(f)
K = "全域替换用のリスト(列表)型配列(replacements_final_list)"
mm = {e[0]: e[1] for e in combined[K]}
em = {e[0]: e[1] for e in ex.get(K, [])}
keys_same = set(mm) == set(em)
diffs = [(o, mm[o], em[o]) for o in (set(mm)&set(em)) if mm[o] != em[o]]
print(f"old集合一致={keys_same}  値相違={len(diffs)}/{len(mm)}")
for o, m, e in diffs[:15]:
    print(f"  [{o}]\n    自前: {m[:120]}\n    既存: {e[:120]}")
