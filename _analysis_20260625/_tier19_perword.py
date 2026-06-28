# -*- coding: utf-8 -*-
"""衝突語(forti/fero/rego)を per-word「固定形(ne)」で強制。語根パラダイムを作らないので
   部分文字列衝突(fer⊂feria等)を起こさない。書込なしでJP生成し、是正＋無衝突を検証。"""
import re, sys, json, os
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp
APPDIR = BASE + r"\Esperanto-Kanji-Ruby-JA"; DATA = APPDIR + r"\app_data"
ESTEM=r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json"
ROOTS=r"\世界语全部词根_约11137个_202501.txt"; STEM=r"\分解設定.json"
USER=r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"; CSV=r"\エスペラント語根-日本語訳ルビ対応リスト.csv"; FMT='HTML格式_Ruby文字_大小调整'
# 現行設定(tier18) + per-word「ne」エントリ
with open(lp(DATA+STEM), encoding="utf-8") as f: settings = json.load(f)
PERWORD = [["fort/i",55000,["ne"]], ["fer/o",45000,["ne"]], ["reg/o",45000,["ne"]],
           ["fer/oj",46000,["ne"]], ["fer/o/n",46000,["ne"]]]
settings2 = settings + PERWORD
tmp = DATA + r"\_settings_perword_tmp.json"
with open(lp(tmp),"w",encoding="utf-8") as g: json.dump(settings2,g,ensure_ascii=False)
with open(lp(BASE+r"\_analysis_20260625\out\word_anno_ja.json"),encoding='utf-8') as f: wa=json.load(f)
combined = generate(APPDIR,DATA,DATA+CSV,tmp,DATA+USER,DATA+ESTEM,DATA+ROOTS,FMT,word_anno=wa)
os.remove(lp(tmp))
GL=combined["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2=combined["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG=combined["全域替换用のリスト(列表)型配列(replacements_final_list)"]
sys.path.insert(0, APPDIR); import esp_text_replacement_module as m
ps=m.import_placeholders(lp(DATA+r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
pl=m.import_placeholders(lp(DATA+r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
def rt(t):
    h=m.orchestrate_comprehensive_esperanto_text_replacement(" "+t+" ",ps,GL,pl,GG,G2,FMT)
    toks=[];pos=0
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>',h):
        for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+',re.sub(r'<[^>]+>','',h[pos:mm.start()]),re.I):toks.append(ch)
        toks.append(mm.group(1));pos=mm.end()
    for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+',re.sub(r'<[^>]+>','',h[pos:]),re.I):toks.append(ch)
    return '/'.join(toks)
print("=== 是正対象(直るべき) ===")
for w in ['forti','fero','feroj','feron','rego']: print(f"  {w:14s} -> {rt(w)}")
print("=== 衝突チェック(変わってはいけない) ===")
for w in ['feria','ferio','fortostreĉo','laboregi','fervojo','fera','regi','registro','vino']: print(f"  {w:14s} -> {rt(w)}")
