# -*- coding: utf-8 -*-
"""最終検証(日本語版): 元の状態(分解前backup) → 現状(分解+訳統合後) を比較。訳ギャップ解消を確認。"""
import json, sys, re, glob, random
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
sys.path.insert(0, BASE + r"\Esperanto-Kanji-Ruby-JA")
from gen_replacement import lp
from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement, import_placeholders as imp

APP = BASE + r"\Esperanto-Kanji-Ruby-JA"
DATA = APP + r"\Appの运行に使用する各类文件"
FINAL = DATA + r"\最终的な替换用リスト(列表)(合并3个JSON文件).json"
# 元の状態 = 分解前backup(最初のbackup)
ORIG = sorted(glob.glob(lp(DATA + r"\_backup_before_decomp_update_*\最终的な替换用リスト(列表)(合并3个JSON文件).json")))[0]
FMT = 'HTML格式_Ruby文字_大小调整'

def load(p):
    with open(lp(p), encoding='utf-8') as f: d = json.load(f)
    return (d["全域替换用のリスト(列表)型配列(replacements_final_list)"],
            d["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"],
            d["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"])
new_g,new_l,new_2 = load(FINAL)
old_g,old_l,old_2 = load(ORIG)
ph_skip = imp(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
ph_local = imp(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
def run(t,g,l,c): return orchestrate_comprehensive_esperanto_text_replacement(t,ph_skip,l,ph_local,g,c,FMT)
def segs(h): return re.findall(r'<rt[^>]*>(.*?)</rt>', h)
def plain(h): return re.sub(r'<[^>]+>','',h)

print("="*72); print("【最終検証: 元(分解前) → 現状(分解+訳統合)】")
TESTS=["zoologio","monomanio","fizioterapio","anemometro","aerobia","ekspresionismo",
       "telegrafreto","aŭtomobilo","amiko","hundo","bona","internacia","lernejano","biologio","demokratio"]
for w in TESTS:
    o=segs(run(w,old_g,old_l,old_2)); n=segs(run(w,new_g,new_l,new_2))
    print(f"  [{w}]\n     元 : {o}\n     現 : {n}")

print("\n【実テキスト(現状)】")
with open(lp(APP + r"\例句_Esperanto文本.txt"), encoding='utf-8') as f:
    lines=[l.strip() for l in f if l.strip()][:3]
for ln in lines:
    print(f"  {plain(run(ln,new_g,new_l,new_2))[:130]}")

print("\n【訳カバレッジ: ランダム400語で訳セグメントが空(=訳なし)の割合】")
random.seed(7)
with open(lp(DATA + r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json"), encoding='utf-8') as f:
    estem=json.load(f)
words=list({x[0].replace('/','')+'o' for x in estem if len(x)==2})
sample=random.sample(words,400)
old_empty=sum(1 for w in sample if not segs(run(w,old_g,old_l,old_2)))
new_empty=sum(1 for w in sample if not segs(run(w,new_g,new_l,new_2)))
print(f"  訳なし(空)語数: 元 {old_empty}/400 ({old_empty/4:.1f}%) → 現 {new_empty}/400 ({new_empty/4:.1f}%)")
