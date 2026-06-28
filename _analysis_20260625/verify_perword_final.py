# -*- coding: utf-8 -*-
"""デプロイ済みper-word JSONで、偽の友/過細分解語・文脈依存・退行を最終確認(JP)。"""
import json, sys, re, glob, random
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
sys.path.insert(0, BASE + r"\Esperanto-Kanji-Ruby-JA")
from gen_replacement import lp
from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement, import_placeholders as imp
APP = BASE + r"\Esperanto-Kanji-Ruby-JA"; DATA = APP + r"\app_data"
FINAL = DATA + r"\置換リスト_ルビ.json"
ORIG = sorted(glob.glob(lp(DATA + r"\_backup_before_decomp_update_*\置換リスト_ルビ.json")))[0]
FMT='HTML格式_Ruby文字_大小调整'
def load(p):
    with open(lp(p),encoding='utf-8') as f: d=json.load(f)
    return (d["全域替换用のリスト(列表)型配列(replacements_final_list)"],d["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"],d["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"])
ng,nl,n2=load(FINAL); og,ol,o2=load(ORIG)
ps=imp(lp(DATA+r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt")); pl=imp(lp(DATA+r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
def run(t,g,l,c): return orchestrate_comprehensive_esperanto_text_replacement(t,ps,l,pl,g,c,FMT)
def segs(h): return re.findall(r'<rt[^>]*>(.*?)</rt>',h)
print("【偽の友/過細分解語(per-word注釈)】")
for w in ["agronomo","agronomio","manometro","anestezio","analfabeto","telegrafreto","aerolito","biologio","monomanio","mono"]:
    print(f"  {w:13s} {segs(run(w,ng,nl,n2))}")
print("\n【訳カバレッジ: ランダム400語の訳なし率(元→per-word現)】")
random.seed(11)
with open(lp(DATA + r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json"),encoding='utf-8') as f: es=json.load(f)
ws=list({x[0].replace('/','')+'o' for x in es if len(x)==2}); sm=random.sample(ws,400)
oe=sum(1 for w in sm if not segs(run(w,og,ol,o2))); ne=sum(1 for w in sm if not segs(run(w,ng,nl,n2)))
print(f"  訳なし: 元 {oe}/400 ({oe/4:.1f}%) → per-word現 {ne}/400 ({ne/4:.1f}%)")
print("\n【実テキスト(per-word現)】")
with open(lp(APP+r"\例句_Esperanto文本.txt"),encoding='utf-8') as f: ls=[l.strip() for l in f if l.strip()][:2]
for ln in ls: print("  "+re.sub(r'<[^>]+>','',run(ln,ng,nl,n2))[:120])
