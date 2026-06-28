# -*- coding: utf-8 -*-
"""kanji_mismatch.json(17019件)を識別子マーカーを両側対称に除去して再判定。
   何件が「マーカー差のみ(=漢字本体は一致)」で、何件が真の漢字内容差かを定量化する。
   これで真の漢字内容一致率を得る。"""
import re, sys, json
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
mis = json.load(open(BASE + r"\_analysis_20260625\out\kanji_mismatch.json", encoding="utf-8"))
# 上付き識別子マーカー全域(modifier letter superscripts)
MARK = re.compile(r"[ʰ-˿ᴬ-ᵪᶛ-ᶿ⁰-₟]")
def strip(s): return MARK.sub("", s)
marker_only = 0
genuine = []
for w, mk, ak in mis:
    if strip(mk) == strip(ak):
        marker_only += 1
    else:
        genuine.append((w, mk, ak, strip(mk), strip(ak)))
TOTAL = 44598
EXACT = 27579
print(f"既存exact一致 {EXACT}/{TOTAL} ({EXACT*1000//TOTAL/10}%)")
print(f"不一致 {len(mis)} の内訳:")
print(f"  マーカー差のみ(漢字本体一致) : {marker_only}")
print(f"  真の漢字内容差               : {len(genuine)}")
true_match = EXACT + marker_only
print(f"\n=== 真の漢字内容一致 {true_match}/{TOTAL} ({true_match*1000//TOTAL/10}%) ===")
print(f"\n--- 真の内容差 上位40(マーカー除去後も異なる) ---")
for w, mk, ak, sm, sa in genuine[:40]:
    print(f"  {w:18s} master={sm:16s} app={sa}")
json.dump([[w, sm, sa] for w, mk, ak, sm, sa in genuine],
          open(BASE + r"\_analysis_20260625\out\_kanji_genuine_diff.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
