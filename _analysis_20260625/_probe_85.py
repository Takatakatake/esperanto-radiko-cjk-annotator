# -*- coding: utf-8 -*-
"""別漢字85件(app≠注入版・両側ラテン無)を抽出し、各語の語根が注入版で一意(singleton)か曖昧か診断。
   一意な語根のみ揃えれば同綴り衝突(mi=肌/我, kaj=和/码)を回避できる。"""
import re, sys, json, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
INJ = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\漢字注入_学習者版_20260620.txt"
FULL = re.compile(r"[̀-ͯʰ-˿ᴀ-ᶿ⁰-₟Ⱡ-Ɀ]")
def fs(s): return FULL.sub("", s)
LAT = re.compile(r"[a-zĉĝĥĵŝŭ]", re.I)
ENDINGS = ["ojn","ajn","oj","aj","on","an","en","os","is","as","us","o","a","e","i","n","j","u","s","t"]
def stem(s):
    for e in ENDINGS:
        if s.endswith(e): return s[:-len(e)]
    return s
# 1) 別漢字85件を deployed mismatch から抽出
mis = json.load(open(BASE + r"\_analysis_20260625\out\kanji_mismatch.json", encoding="utf-8"))
betsu = [(w, mk, ak) for w, mk, ak in mis if not LAT.search(stem(mk)) and not LAT.search(stem(ak))]
print(f"deployed真差 {len(mis)} 中 別漢字(両側漢字・app≠master) = {len(betsu)}")
# 2) 注入版を全走査: root_kanji Counter(曖昧性) + word->pieces
LINE = re.compile(r'^(.*?)⟦(.*?)⟧')
root_kanji = collections.defaultdict(collections.Counter)
word_pieces = {}
with open(INJ, encoding="utf-8") as f:
    for line in f:
        m = LINE.match(line.rstrip("\n"))
        if not m: continue
        head = m.group(1).strip(); kanji = m.group(2)
        if " " in head or "#" in head: continue
        hp = [p for p in head.split("/") if p]
        kp = kanji.split("/")
        if len(hp) != len(kp): continue
        w = norm("".join(hp))
        word_pieces.setdefault(w, list(zip([norm(x) for x in hp], kp)))
        for r, kj in zip(hp, kp):
            r = norm(r); kjs = fs(kj.strip())
            if len(r) >= 2 and kjs and not LAT.fullmatch(kjs):
                root_kanji[r][kjs] += 1
def ambig(r): return len(root_kanji.get(r, {})) > 1
safe = []; collision = []; nopiece = []
for w, mk, ak in betsu:
    pcs = word_pieces.get(w)
    if not pcs:
        nopiece.append((w, mk, ak)); continue
    bad_roots = [r for r, _ in pcs if len(r) >= 2 and ambig(r)]
    if bad_roots:
        collision.append((w, mk, ak, bad_roots))
    else:
        safe.append((w, mk, ak, [r for r, _ in pcs if len(r) >= 2]))
print(f"\n  安全(全語根が注入版で一意)  : {len(safe)}")
print(f"  同綴り衝突(曖昧語根含む)     : {len(collision)}")
print(f"  注入版に該当語無し           : {len(nopiece)}")
print("\n--- 安全に揃えられる語(語根一意) ---")
for w, mk, ak, roots in safe:
    print(f"  {w:18s} 注入={mk:12s} app={ak:10s} 語根={roots}")
print("\n--- 同綴り衝突で要注意(揃えるなら per-word) ---")
for w, mk, ak, bad in collision:
    print(f"  {w:18s} 注入={mk:12s} app={ak:10s} 曖昧語根={bad}->{[dict(root_kanji[r]) for r in bad]}")
if nopiece:
    print("\n--- 注入版に分解行が無い(別要因) ---")
    for w, mk, ak in nopiece: print(f"  {w:18s} 注入={mk:12s} app={ak}")
json.dump({"safe":[[w,mk,ak] for w,mk,ak,_ in safe], "collision":[[w,mk,ak] for w,mk,ak,_ in collision]},
          open(BASE + r"\_analysis_20260625\out\_betsu85.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
