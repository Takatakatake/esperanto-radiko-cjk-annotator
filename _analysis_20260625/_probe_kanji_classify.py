# -*- coding: utf-8 -*-
"""kanji_mismatch.json を完全なマーカー集合で再分類。
   (1)マーカー差のみ(ⱽ等の取りこぼし含む) (2)app残存ラテン=未変換/孤立先頭文字 (3)真の漢字選択差。"""
import re, sys, json, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
mis = json.load(open(BASE + r"\_analysis_20260625\out\kanji_mismatch.json", encoding="utf-8"))
# 完全な識別子マーカー集合: 結合ダイア・spacing modifier・音声拡張(上付きᴬ等)・上下付き・Latin-Ext-C(ⱽ)
FULL = re.compile(r"[̀-ͯʰ-˿ᴀ-ᶿ⁰-₟Ⱡ-Ɀ]")
def fs(s): return FULL.sub("", s)
LAT = re.compile(r"[a-zĉĝĥĵŝŭ]", re.I)
ENDINGS = ["ojn","ajn","oj","aj","on","an","en","os","is","as","us","o","a","e","i","n","j","u","s","t"]
def strip_one_ending(s):
    for e in ENDINGS:
        if s.endswith(e): return s[:-len(e)]
    return s
cat = collections.Counter(); ex = collections.defaultdict(list)
for w, mk, ak in mis:
    smk, sak = fs(mk), fs(ak)
    if smk == sak:
        k = "1_マーカー差のみ(漢字同一)"
    else:
        stem = strip_one_ending(sak)
        if LAT.search(stem):
            # appに語幹ラテンが残る = 未変換 or 孤立先頭文字
            if not re.search(r"[一-龥]", sak):
                k = "2a_app完全未変換(romaji残)"
            else:
                k = "2b_app孤立ラテン混入(過分解由来)"
        else:
            k = "3_真の漢字選択差(master≠app)"
    cat[k] += 1
    if len(ex[k]) < 22: ex[k].append((w, smk, sak))
print(f"kanji_mismatch.json 総数 {len(mis)}")
print("=== 完全マーカー集合での再分類 ===")
for k, v in cat.most_common(): print(f"  {k}: {v}")
TOTAL = 44599; EXACT_AND_MARKER = TOTAL - len(mis)
true_content = EXACT_AND_MARKER + cat["1_マーカー差のみ(漢字同一)"]
print(f"\n真の漢字内容一致(ⱽ等込み補正後) = {true_content}/{TOTAL} ({true_content*1000//TOTAL/10}%)")
print(f"真の差 = {len(mis)-cat['1_マーカー差のみ(漢字同一)']}件 (内訳: 2a={cat['2a_app完全未変換(romaji残)']}, 2b={cat['2b_app孤立ラテン混入(過分解由来)']}, 3={cat['3_真の漢字選択差(master≠app)']})")
for k in ["2a_app完全未変換(romaji残)","2b_app孤立ラテン混入(過分解由来)","3_真の漢字選択差(master≠app)"]:
    print(f"\n--- {k} (例) ---")
    for w, smk, sak in ex[k]: print(f"  {w:20s} master={smk:14s} app={sak}")
