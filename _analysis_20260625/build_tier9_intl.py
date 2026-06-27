# -*- coding: utf-8 -*-
"""tier9: HTML参照(ユーザー公認の注釈源)から国際/固有語のグロスを抽出し、
JP版word_annoに注入 + 語根強制(target root/o)で過分解(a/dek/va, ek/ologi 等)を解消。
ZH/KOは参照1(WSL)不通でグロス源無し→該当語は現状維持(force-whole再分割で退行なし)。"""
import re, sys, json, html as htmllib, os, shutil
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

# HTML参照グロス(語根キー)
gloss = {}
for H in ["Esperanto_meznivela_sola_lernolibro_verkita_de_sro_fujximaki_260215.html", "vere_aux_fantazie.html"]:
    p = os.path.join(BASE, H)
    if not os.path.exists(p): continue
    t = open(p, encoding="utf-8").read()
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', t):
        b = norm(mm.group(1)); g = htmllib.unescape(re.sub(r'<[^>]+>', '', mm.group(2)))
        if b and g and b not in gloss: gloss[b] = g

# 対象: 過分解されている国際/固有語(ref=whole or root+gram)。HTML語根グロスを持つもの。
ROOTS = ["ideologi","ekologi","ideogram","antibiotik","pseudonim","ŝang","austr",
         "milovan","papalag","dividend","radiofoni","sovetuni","adekv","argent",
         "irkuck","detektiv","agresiv","intensiv",
         "telefon","efektiv","karakteriz","mir","kiran"]  # vereベンチ由来の国際/語根過分解
# uk/um(2文字, -um-接尾辞/minimumo等を侵食) と ocel(グロス無) は除外
OUT = BASE + r"\_analysis_20260625\out"

# 1) word_anno_ja に注入(冪等: バックアップ→既存読込→更新)
wa_path = OUT + r"\word_anno_ja.json"
bak = wa_path + ".bak_preTier9"
if not os.path.exists(lp(bak)): shutil.copy2(lp(wa_path), lp(bak))
wa = json.load(open(lp(bak), encoding="utf-8"))   # 常にpristineから
added = {}
for r in ROOTS:
    g = gloss.get(norm(r))
    if g:
        # gold由来の多片sibling(ide/o/logi等)を除去 → word_anno_nosl の setdefault で
        # 1片版(=HTML準拠の一体分解)が確実に採用される(衝突回避)
        for k in [k for k in list(wa.keys()) if k.replace('/', '') == r and k != r]:
            wa.pop(k, None)
        wa[r] = [[r, g]]; added[r] = g
# tier10連携: 対格代名詞/相関詞の名詞stem(min=鉱山等)をword_annoから除去。
# →裸の min/vin/tion 等は force(safe_replace)で mi/n に分解、mino/vino等は per-root CSV
#   グロス(鉱山/ぶどう酒)で min/o のまま(長語=高優先で保全)。word_anno横取りを回避。
PRON_ACC_NOUN = ["min", "vin", "lin", "ĝin", "nin", "sin", "tion", "ion"]
removed_wa = []
for r in PRON_ACC_NOUN:
    for k in [k for k in list(wa.keys()) if k.replace('/', '') == r]:
        wa.pop(k, None); removed_wa.append(k)
json.dump(wa, open(lp(wa_path), "w", encoding="utf-8"), ensure_ascii=False)
print(f"word_anno_ja 対格名詞除去: {removed_wa}")

# ZH/KO も同様に対格名詞stemを除去(裸対格を分解・-o名詞はper-root CSVグロスで保持)。
# 国際語グロスはZH/KOはper-root CSV由来(psikologi=心理学 等)で安定するため注入不要。
for lang in ["zh", "ko"]:
    wp = OUT + f"\\word_anno_{lang}.json"
    if not os.path.exists(lp(wp)): continue
    bk = wp + ".bak_preTier9"
    if not os.path.exists(lp(bk)): shutil.copy2(lp(wp), lp(bk))
    w2 = json.load(open(lp(bk), encoding="utf-8"))
    rm = []
    for r in PRON_ACC_NOUN:
        for k in [k for k in list(w2.keys()) if k.replace('/', '') == r]:
            w2.pop(k, None); rm.append(k)
    json.dump(w2, open(lp(wp), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"word_anno_{lang} 対格名詞除去: {rm}")
print(f"word_anno_ja 注入 {len(added)}語:")
for r, g in added.items(): print(f"  {r:12s}-> {g}")

# 2) tier9 確定: target=root/o (nominal paradigm)。動詞語根は /i (addverbで動詞形も生成)
VERB = {"telefon", "karakteriz"}
t9 = [{"w": r + "o", "target": r + ("/i" if r in VERB else "/o")} for r in ROOTS if norm(r) in gloss]
json.dump(t9, open(lp(OUT + r"\confirmed_tier9.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nconfirmed_tier9.json: {len(t9)}件")
