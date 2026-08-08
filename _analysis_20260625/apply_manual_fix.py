# -*- coding: utf-8 -*-
"""自動レビューが漏らした明確な残存 false friend を高信頼で手動補正。"""
import json, sys, shutil
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp
OUT = BASE + r"\_analysis_20260625\out"

# key(E_stem語形) -> 修正。pieces: [[root,ja,zh,ko],...]  / whole: 単語全体1ルビ {ja,zh,ko}
CORR = {
  # man(希薄manos)は不透明な借用 → 全体語訳
  "man/o/metr": {"whole": {"ja":"圧力計","zh":"压力计","ko":"압력계"}},
  # 電子(elektron単一語根) on=粒子(分数でない)。elektr=電,on=子で形態素表示
  "elektr/on": {"pieces": [["elektr","電","电","전"],["on","子","子","자"]]},
  # komandit は合資の単一語根。komand(指揮)は別形態素 → 全体語訳
  "komand/it": {"whole": {"ja":"合資","zh":"合资","ko":"합자"}},
}

anno = {}
for L in ('ja','zh','ko'):
    with open(lp(OUT + f"\\word_anno_{L}.json"), encoding="utf-8") as f:
        anno[L] = json.load(f)

done = []
for key, c in CORR.items():
    present = key in anno['ja']
    if "whole" in c:
        sn = key.replace('/','')
        for L in ('ja','zh','ko'):
            anno[L][key] = [[sn, c["whole"][L]]]
    elif "pieces" in c:
        # keyの各片に一致するrootのグロスを置換
        fmap = {p[0]: {'ja':p[1],'zh':p[2],'ko':p[3]} for p in c["pieces"]}
        for L in ('ja','zh','ko'):
            cur = anno[L].get(key)
            if not cur: continue
            anno[L][key] = [[p, (fmap[p][L] if p in fmap else g)] for p,g in cur]
    done.append((key, present))

for L in ('ja','zh','ko'):
    src = OUT + f"\\word_anno_{L}.json"
    shutil.copy2(lp(src), lp(src + ".bak_preManual"))
    with open(lp(src),"w",encoding="utf-8") as g: json.dump(anno[L],g,ensure_ascii=False)
print("手動補正:", done)
for k in CORR: print(f"  {k} → ja {anno['ja'].get(k)}")
