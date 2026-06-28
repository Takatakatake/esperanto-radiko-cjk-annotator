# -*- coding: utf-8 -*-
"""展開後検証(日本語版): 実テキスト＋サンプル語で旧(backup)→新(deployed)を比較。"""
import json, sys, re, glob, random
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
sys.path.insert(0, BASE + r"\Esperanto-Kanji-Ruby-JA")
from gen_replacement import lp
from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement, import_placeholders as imp

APP = BASE + r"\Esperanto-Kanji-Ruby-JA"
DATA = APP + r"\app_data"
FINAL = DATA + r"\置換リスト_ルビ.json"
BK = glob.glob(lp(DATA + r"\_backup_before_decomp_update_*\置換リスト_ルビ.json"))
BK = sorted(BK)[-1]
FMT = 'HTML格式_Ruby文字_大小调整'

def load(p):
    with open(lp(p), encoding='utf-8') as f:
        d = json.load(f)
    return (d["全域替换用のリスト(列表)型配列(replacements_final_list)"],
            d["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"],
            d["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"])

new_g, new_l, new_2 = load(FINAL)
old_g, old_l, old_2 = load(BK)
ph_skip = imp(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
ph_local = imp(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))

def run(text, g, l, t):
    return orchestrate_comprehensive_esperanto_text_replacement(text, ph_skip, l, ph_local, g, t, FMT)

def plain(html):
    return re.sub(r'<[^>]+>', '', html)
def segs(html):
    return re.findall(r'<rt[^>]*>(.*?)</rt>', html)

print("="*72)
print("【展開後検証: 実テキスト処理 (新JSON)】")
with open(lp(APP + r"\例句_Esperanto文本.txt"), encoding='utf-8') as f:
    lines = [l.strip() for l in f if l.strip()][:6]
for ln in lines[:4]:
    out = run(ln, new_g, new_l, new_2)
    print(f"  IN : {ln[:70]}")
    print(f"  OUT: {plain(out)[:120]}")

print("\n" + "="*72)
print("【サンプル語: 旧→新の訳/ローマ字セグメント】")
TESTS = ["monomanio","fizioterapio","anemometro","aerobia","ekspresionismo",
         "telegrafreto","reorganizi","aŭtomobilo","zoologio","germaniumo",
         "amiko","hundo","bona","lernejano","esperanto","internacia","lingvo"]
chg=0
for w in TESTS:
    o = segs(run(w, old_g, old_l, old_2)); n = segs(run(w, new_g, new_l, new_2))
    mark = "★" if o!=n else "  "
    if o!=n: chg+=1
    print(f" {mark}[{w}] 旧={o} 新={n}")
print(f"  変化 {chg}/{len(TESTS)}")

# ランダム gold 語の分解変化率
print("\n" + "="*72)
print("【ランダム抽出: 旧→新で分解(セグメント)が変化した割合】")
random.seed(42)
with open(lp(DATA + r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json"), encoding='utf-8') as f:
    estem = json.load(f)
words = list({x[0].replace('/','')+'o' for x in estem if len(x)==2})
sample = random.sample(words, 300)
changed = 0
for w in sample:
    if segs(run(w, old_g, old_l, old_2)) != segs(run(w, new_g, new_l, new_2)):
        changed += 1
print(f"  300語中 分解/訳が変化: {changed} ({changed/3:.1f}%)")
