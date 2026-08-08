# -*- coding: utf-8 -*-
"""Tier3検証WF出力から out/confirmed_tier3.json を構築。
 confirmed(agree): decompA / confirmed(agree=false): OVERRIDES優先→decompA
 conflict: CONFLICT_FIX(FIX採用) / 他はKEEP。整合性チェック付き。"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
OUT = BASE + r"\_analysis_20260625\out"
WF = r"C:\Users\yt\AppData\Local\Temp\claude\d--GoogleDrive202510--------20----------------------------20260624\46f52639-acfa-48a8-8c2f-e95e8e59b22d\tasks\wfq9oined.output"
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

# agree=false で decompA を採らない(私の確定)ケース
OVERRIDES = {
 "Pont-Eu^ksen/o":      "pont-eŭksen/o",          # 古典名は併合(pont=橋の偽友回避)
 "1,2,3-propantriol/o": "1,2,3-propantriol/o",    # 化学名は併合
 "C^efec^-s^los/il/o":  "ĉefeĉ-ŝlos/il/o",         # gold併合
}
# conflict のうちFIX採用(target指定)。未掲載はKEEP
CONFLICT_FIX = {
 "montenegr/a":     "montenegr/a",     # Montenegro 固有名詞1単位(←mont/e/negr)
 "h^ilopod/oj":     "ĥilopod/oj",      # 分類群1単位(←ĥilo/pod)
 "2-propan/ol/o":   "2-propan/ol/o",   # 化学標準(位置番号付着)
 "servil/a":        "servil/a",        # servile 1語根(←serv/il)
 "spionit/o":       "spionit/o",       # gold 1語根
 "undek/":          "undek",           # 11 結合形1単位(←un/dek)
}

with open(lp(WF),encoding='utf-8') as f: data=json.load(f)
res=data["result"]
out=[]; problems=[]
def add(w, target, gold=None):
    # 選んだ分解が語と不一致(検証者が末尾語尾を落とした等)ならgoldにフォールバック
    if gold is not None and target.replace('/','')!=norm(w).replace('/',''):
        target=norm(gold)
    if target.replace('/','')!=norm(w).replace('/',''):
        problems.append((w,target,target.replace('/',''),norm(w).replace('/','')))
    out.append({"w":w,"target":target})

for e in res["confirmed"]:
    w=e["w"]; g=e.get("g")
    if w in OVERRIDES: add(w, OVERRIDES[w], g)
    else: add(w, e["decompA"], g)   # agree問わずAの完全形。不足分はgold
for c in res["conflict"]:
    if c["w"] in CONFLICT_FIX: add(c["w"], CONFLICT_FIX[c["w"]], c.get("g"))

print(f"Tier3 確定FIX {len(out)} (confirmed {len(res['confirmed'])} + conflict採用 {len(CONFLICT_FIX)})")
print(f"KEEP: reject {len(res['rejected'])} + conflict-keep {len(res['conflict'])-len(CONFLICT_FIX)}")
if problems:
    print(f"\n!! 整合性問題 {len(problems)}:")
    for w,t,nt,nw in problems: print(f"   w={w} target={t} {nt}!={nw}")
else:
    print("整合性チェック: 全件OK")
with open(lp(OUT+"\\confirmed_tier3.json"),'w',encoding='utf-8') as g:
    json.dump(out,g,ensure_ascii=False,indent=1)
print("保存: out/confirmed_tier3.json")
