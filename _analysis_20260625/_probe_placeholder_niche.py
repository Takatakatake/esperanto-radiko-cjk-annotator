# -*- coding: utf-8 -*-
"""ユーザー案(未割当ラテンを稀少Unicode異形に置換)の「真の出番」を定量化。
   真の差309件のうち、master値自体にラテン字が残る語=どんなに頑張ってもラテンが残る語(=プレースホルダの唯一の niche)
   vs master値が完全に漢字=マスター再現で正解が出せる語、を数える。"""
import re, sys, json
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
mis = json.load(open(BASE + r"\_analysis_20260625\out\kanji_mismatch.json", encoding="utf-8"))
FULL = re.compile(r"[̀-ͯʰ-˿ᴀ-ᶿ⁰-₟Ⱡ-Ɀ]")
def fs(s): return FULL.sub("", s)
LAT = re.compile(r"[a-zĉĝĥĵŝŭ]", re.I)
ENDINGS = ["ojn","ajn","oj","aj","on","an","en","os","is","as","us","o","a","e","i","n","j","u","s","t"]
def stem(s):
    s = fs(s)
    for e in ENDINGS:
        if s.endswith(e): return s[:-len(e)]
    return s
master_latin = []      # masterでもラテン残=プレースホルダniche
master_full = []       # master完全漢字=マスター再現で正解
for w, mk, ak in mis:
    if fs(mk) == fs(ak):  # マーカー差のみは除外
        continue
    if LAT.search(stem(mk)):
        master_latin.append((w, fs(mk), fs(ak)))
    else:
        master_full.append((w, fs(mk), fs(ak)))
print(f"真の差(マーカー差除く) = {len(master_latin)+len(master_full)} 件")
print(f"  ① master完全漢字 → マスター再現で正解が出せる(本当に直せる) : {len(master_full)}")
print(f"  ② masterでもラテン残 → 何をしても断片が残る(ユーザー案の唯一のniche): {len(master_latin)}")
print(f"\n--- ② masterでもラテンが残る語(ここだけがプレースホルダ候補) ---")
for w, mk, ak in master_latin:
    print(f"  {w:22s} master={mk:16s} app={ak}")
