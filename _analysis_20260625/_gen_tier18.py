# -*- coding: utf-8 -*-
"""gold_mismatch.json から「アプリが過分解(app片数 > gold片数)」の語を抽出し、
   gold分解を target とする tier18候補を作る。gold=分解の正本。衝突語は配備後の回帰で除外する。"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
OUT = BASE + r"\_analysis_20260625\out"
gm = json.load(open(OUT + r"\gold_mismatch.json", encoding="utf-8"))
cands = []
for ref, app in gm:
    rp = [p for p in ref.split('/') if p]; ap = [p for p in app.split('/') if p]
    if len(ap) > len(rp):  # app過分解
        # 先頭1文字孤立 or 余分境界。gold(ref)を正解とする。
        cands.append({"w": "".join(rp), "target": ref})
# 重複除去
seen = set(); uniq = []
for c in cands:
    if c["w"] in seen: continue
    seen.add(c["w"]); uniq.append(c)
json.dump(uniq, open(OUT + r"\confirmed_tier18.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"gold過分解 候補 {len(uniq)} 件")
for c in uniq[:50]:
    print(f"  {c['w']:22s} -> {c['target']}")
