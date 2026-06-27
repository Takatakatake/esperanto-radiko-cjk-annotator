# -*- coding: utf-8 -*-
"""tier11: コーパス自動抽出の過分割語根を参照グロスで一括強制(汎用ルール)。
   - len>=4 のみ(短語根の部分文字列衝突を回避)
   - word_anno_ja に注入 + 多片sibling除去(衝突回避)
   - 動詞glossは /i, それ以外 /o (nominal paradigmで屈折一括)
   既存tier(4/9/10)や代名詞と重複する語根は除外。"""
import sys, json, os, shutil, re
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
OUT = BASE + r"\_analysis_20260625\out"
cands = json.load(open(lp(OUT + r"\oversplit_candidates.json"), encoding="utf-8"))

# 相関詞/代名詞は別tier(7/8/10)で処理済 or 特殊targetが必要なため除外。
# その他は多数決(extract_oversplitのatomic≫split)を信頼。len>=3許容。
SKIP = {"tiu","tio","tia","tie","kiu","kio","kia","kie","ĉiu","ĉio","iu","io","ia","ie",
        "mi","vi","li","ni","ĝi","si","ili","ci","oni"}
# 回帰検出で特定した原因語根(部分文字列窃取/接尾辞融合/参照も分解)を除外
_culp = OUT + r"\tier11_culprits.json"
if os.path.exists(lp(_culp)):
    SKIP |= set(json.load(open(lp(_culp), encoding="utf-8")))
def is_verb(g):
    return bool(re.search(r'(する|える|いる|きる|ぐ|ぶ|つ|ねる|べる|てる)$', g)) or g.startswith("(を)") or g.startswith("(に)")

picked = []
for x in cands:
    r = x['root']; g = x['gloss']
    if len(r) < 3: continue
    if r in SKIP: continue
    if not re.fullmatch(r'[a-zĉĝĥĵŝŭ]+', r): continue
    picked.append({'root': r, 'gloss': g, 'verb': is_verb(g), 'count': x['count']})
print(f"tier11 採用 {len(picked)} 語根 (len>=4, グロス有), 計{sum(p['count'] for p in picked)}出現")

# word_anno_ja 注入(冪等: .bak_preTier9 から国際語tier9注入を再現した状態が必要なので、
#   ここでは現行word_anno_ja を直接更新。tier11専用バックアップで冪等化)
wa_path = OUT + r"\word_anno_ja.json"
bak = wa_path + ".bak_preTier11"
if not os.path.exists(lp(bak)): shutil.copy2(lp(wa_path), lp(bak))
wa = json.load(open(lp(bak), encoding="utf-8"))   # 常にtier11適用前(=tier9注入済)から
for p in picked:
    r = p['root']
    for k in [k for k in list(wa.keys()) if k.replace('/', '') == r and k != r]:
        wa.pop(k, None)
    wa[r] = [[r, p['gloss']]]
json.dump(wa, open(lp(wa_path), "w", encoding="utf-8"), ensure_ascii=False)

t11 = [{"w": p['root'] + "o", "target": p['root'] + ("/i" if p['verb'] else "/o")} for p in picked]
json.dump(t11, open(lp(OUT + r"\confirmed_tier11.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"confirmed_tier11.json: {len(t11)}件  (動詞 {sum(1 for p in picked if p['verb'])})")
print("動詞例:", [p['root'] for p in picked if p['verb']][:12])
