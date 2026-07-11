# -*- coding: utf-8 -*-
"""
clear_errors_tier{N}.json を機械的に分類:
 SKIP  : 語頭/語末がハイフン=辞書見出しの接辞形(実テキスト非出現)
 KEEP  : gold と app の形態素境界集合(/ と語中ハイフン両方を境界)が一致
         → アプリは語根忠実(ハイフンのトークン化差のみ)。gold強制すると複合グロス化するため触らない
 FIX   : 境界集合が不一致=アプリが形態素内部で誤分割 → gold分解を強制
出力: out/fix_tier{N}.json (FIX対象のみ word/gold/app)
  python classify_tier_errors.py <tier>
"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
OUT = BASE + r"\_analysis_20260625\out"
TIER = int(sys.argv[1]) if len(sys.argv)>1 else 2

def canon_cuts(decomp):
    """decomp(スラッシュ区切り)の形態素境界オフセット集合。/ と語中ハイフンの両方を境界とする。"""
    word = decomp.replace('/','')
    cuts=set(); pos=0
    for ch in decomp:
        if ch=='/': cuts.add(pos)
        else: pos+=1
    for i,ch in enumerate(word):
        if ch=='-': cuts.add(i); cuts.add(i+1)
    cuts.discard(0); cuts.discard(len(word))
    return cuts, word

with open(lp(OUT+f"\\clear_errors_tier{TIER}.json"),encoding='utf-8') as f:
    errors=json.load(f)

fix=[]; keep=[]; skip=[]; mismatch=[]
for e in errors:
    gold=e['gold']; app=e['app']
    gw=gold.replace('/','')
    # 接辞見出し(語頭/語末ハイフン) → スキップ
    if gw.startswith('-') or gw.endswith('-'):
        skip.append(e); continue
    gc,gwd=canon_cuts(gold); ac,awd=canon_cuts(app)
    if gwd!=awd:
        mismatch.append(e); continue   # 文字列不一致(想定外) → 要確認
    if gc==ac:
        keep.append(e)
    else:
        fix.append(e)

print(f"Tier{TIER} clear_errors {len(errors)} 分類:")
print(f"  FIX(gold強制)        {len(fix)}")
print(f"  KEEP(アプリ語根忠実)  {len(keep)}")
print(f"  SKIP(接辞見出し)      {len(skip)}")
print(f"  MISMATCH(文字列不整合) {len(mismatch)}")
with open(lp(OUT+f"\\fix_tier{TIER}.json"),'w',encoding='utf-8') as g:
    json.dump(fix,g,ensure_ascii=False,indent=1)
print(f"  保存: out/fix_tier{TIER}.json")
print("\n--- FIX 一覧 ---")
for e in fix:
    print(f"  {e['word']:28s} gold={e['gold']:24s} app={e['app']}")
if mismatch:
    print("\n--- MISMATCH(要確認) ---")
    for e in mismatch:
        print(f"  {e['word']:28s} gold={e['gold']:24s} app={e['app']}")
if skip:
    print(f"\n--- SKIP(接辞見出し) {len(skip)}件 ---")
    print("  "+", ".join(e['gold'] for e in skip))
