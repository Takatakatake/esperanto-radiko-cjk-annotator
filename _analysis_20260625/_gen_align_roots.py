# -*- coding: utf-8 -*-
"""別漢字85件のうち「安全(全語根が注入版で一意)」な語の content語根を集めて
   allow-list(_align_roots.json)を作る。build_kanji_sources はこのリストの語根のみ語根忠実揃え。"""
import re, sys, json
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
INJ = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\漢字注入_学習者版_20260620.txt"
OUT = BASE + r"\_analysis_20260625\out"
betsu = json.load(open(OUT + r"\_betsu85.json", encoding="utf-8"))
safe_words = {w for w, mk, ak in betsu["safe"]}
LINE = re.compile(r'^(.*?)⟦(.*?)⟧')
word_roots = {}
with open(INJ, encoding="utf-8") as f:
    for line in f:
        m = LINE.match(line.rstrip("\n"))
        if not m: continue
        head = m.group(1).strip()
        if " " in head or "#" in head: continue
        hp = [norm(p) for p in head.split("/") if p]
        w = "".join(hp)
        word_roots.setdefault(w, hp)
roots = set()
for w in safe_words:
    for r in word_roots.get(w, []):
        if len(r) >= 2: roots.add(r)
json.dump(sorted(roots), open(OUT + r"\_align_roots.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"安全語 {len(safe_words)} -> allow-list語根 {len(roots)}")
print(sorted(roots))
