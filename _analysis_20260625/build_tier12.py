# -*- coding: utf-8 -*-
"""tier12: 派生接尾辞+文法語尾の融合(gras/ulo→gras/ul/o)を汎用分割。
   B_接尾辞融合カテゴリから接尾辞を抽出し、各接尾辞を低優先のnominal paradigmで強制。
   実語根(regulo=regul/o)はE_stemが高優先で勝つので衝突しない。"""
import json, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
OUT = BASE + r"\_analysis_20260625\out"
mm = json.load(open(lp(OUT + r"\corpus_mismatch.json"), encoding="utf-8"))
GRAM = {'o','oj','on','ojn','a','aj','an','ajn','e','en'}
# B型抽出: refの末尾2片が [接尾辞, 文法語尾] で、appがそれを1片に融合
suf = collections.Counter()
for ref, app, c in mm:
    rp = [p for p in ref.split('/') if p]; ap = [p for p in app.split('/') if p]
    if ''.join(rp) != ''.join(ap): continue
    if len(rp) != len(ap) + 1: continue
    if rp[-1] not in GRAM: continue
    # appの末尾片 == refの末尾2片の結合
    if ap and ap[-1] == rp[-2] + rp[-1] and ap[:-1] == rp[:-2]:
        suf[rp[-2]] += c
print("B型接尾辞(融合している語幹側) 出現数:")
for s, c in suf.most_common(): print(f"  {s:6s}: {c}")
# 派生接尾辞のみ採用(文法語尾そのものや曖昧短綴りは除外)
DERIV = {'ul','in','et','eg','ar','aĉ','aĵ','ant','int','ont','iĉ','er','estr','id','ec','em','end','ebl','ind','obl','op','um','il','ej','an','at','it','ot','ig','iĝ','nj','ĉj'}
picked = [s for s, c in suf.most_common() if s in DERIV]
print(f"\n採用接尾辞 {len(picked)}: {picked}")
# 各接尾辞を target "suf/o" で(nominal paradigmが o/oj/on/a/aj/an/e 等を生成)
t12 = [{"w": s + "o", "target": s + "/o"} for s in picked]
json.dump(t12, open(lp(OUT + r"\confirmed_tier12.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"confirmed_tier12.json: {len(t12)}件")
