# -*- coding: utf-8 -*-
"""
検証ワークフロー出力(wfeaf7t34.output)から out/confirmed_tier2.json を構築。
 - confirmed(agree=true): target=decompA
 - confirmed(agree=false): OVERRIDES の私の確定判断を使用
 - conflict: CONFLICT_FIX(FIX採用＋target) / それ以外はskip(KEEP)
target整合性チェック: target からスラッシュを除いた文字列が norm(w) と一致すること。
"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
OUT = BASE + r"\_analysis_20260625\out"
WF = r"C:\Users\yt\AppData\Local\Temp\claude\d--GoogleDrive202510--------20----------------------------20260624\46f52639-acfa-48a8-8c2f-e95e8e59b22d\tasks\wfeaf7t34.output"
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

# agree=false の確定 target (私の判断)
OVERRIDES = {
 "Brunej-Darusalam/o": "brunej-darusalam/o",
 "Kolonja-Ponape/o":   "kolonja/-/ponape/o",
 "Ho-C^i-Min-urb/o":   "ho-ĉi-min/-/urb/o",
 "Min-river/o":        "min/-/river/o",
 "Nova-Zeml/o":        "nova-zeml/o",
 "Oven-Stanlej/a":     "oven-stanlej/a",
 "Port-Moresb/o":      "port/-/moresb/o",
 "Porto-Algr/o":       "porto/-/algr/o",
 "Porto-Rik/o":        "porto/-/rik/o",
 "Port-Said/o":        "port/-/said/o",
 "te/on":              "te/on",
 "princ/o-elekt/ist/o":"princ/o/-/elekt/ist/o",
}
# conflict の確定 (FIX採用のみ target を指定。未掲載はKEEP=skip)
CONFLICT_FIX = {
 "Bet-Leh^em/o":  "bet-leĥem/o",
 "C^omo-Langm/o": "ĉomo-langm/o",
 "Kuku-Nor/o":    "kuku-nor/o",
 # nj/o-knab/o, Porto-Nov/o は KEEP
}

with open(lp(WF),encoding='utf-8') as f:
    data=json.load(f)
res=data["result"]
out=[]; problems=[]
def add(w, target):
    nz_t=target.replace('/','')
    nz_w=norm(w).replace('/','')
    if nz_t!=nz_w:
        problems.append((w,target,nz_t,nz_w))
    out.append({"w":w,"target":target})

for e in res["confirmed"]:
    w=e["w"]
    if w in OVERRIDES:
        add(w, OVERRIDES[w])
    elif e.get("agree"):
        add(w, e["decompA"])
    else:
        problems.append((w,"<agree=false かつ OVERRIDES未登録>","",""))
for c in res["conflict"]:
    w=c["w"]
    if w in CONFLICT_FIX:
        add(w, CONFLICT_FIX[w])

print(f"確定FIX {len(out)} 件 (confirmed {len(res['confirmed'])} + conflict採用 {len(CONFLICT_FIX)})")
print(f"REJECT(KEEP) {len(res['rejected'])} + conflict-keep 2 = {len(res['rejected'])+2}")
if problems:
    print(f"\n!! 整合性問題 {len(problems)} 件:")
    for w,t,nt,nw in problems:
        print(f"   w={w} target={t}  nz_target={nt} != nz_word={nw}")
else:
    print("整合性チェック: 全件OK")
with open(lp(OUT+"\\confirmed_tier2.json"),'w',encoding='utf-8') as g:
    json.dump(out,g,ensure_ascii=False,indent=1)
print("保存: out/confirmed_tier2.json")
