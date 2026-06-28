# -*- coding: utf-8 -*-
"""teren/forti等の明確な過分解を、ルビモードと漢字モードの両デプロイ済JSONで確認。
   どのモードで過分解しているかを正確に特定する。"""
import re, sys, json
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
appdir = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, appdir)
import esp_text_replacement_module as m
DATA = appdir + r"\app_data"
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
def load(name):
    dd = json.load(open(lp(DATA + name), encoding="utf-8"))
    return (dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"],
            dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"],
            dd["全域替换用のリスト(列表)型配列(replacements_final_list)"])
RUBY = load(r"\置換リスト_ルビ.json")
KANJI = load(r"\置換リスト_漢字.json")
def roots(t, JS, fmt):
    GL, G2, GG = JS
    h = m.orchestrate_comprehensive_esperanto_text_replacement(" " + t + " ", ps, GL, pl, GG, G2, fmt)
    toks = []; pos = 0
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', h):
        for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+', re.sub(r'<[^>]+>', '', h[pos:mm.start()]), re.I): toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+', re.sub(r'<[^>]+>', '', h[pos:]), re.I): toks.append(ch)
    return '/'.join(toks)
def kanji(t):
    GL, G2, GG = KANJI
    h = m.orchestrate_comprehensive_esperanto_text_replacement(" " + t + " ", ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整_汉字替换")
    kj = re.sub(r'<rt[^>]*>.*?</rt>', '', h); return re.sub(r'<[^>]+>', '', kj).strip()
WORDS = ['tereno','terena','terenoj','forti','forta','fortaj','forto','domeno','posteno','fero','rego','ligi','liganta','debato']
print(f"{'語':12s} {'ルビ分解':22s} {'漢字分解':22s} {'漢字':10s}")
print("-"*70)
for w in WORDS:
    print(f"{w:12s} {roots(w, RUBY, 'HTML格式_Ruby文字_大小调整'):22s} {roots(w, KANJI, 'HTML格式_Ruby文字_大小调整_汉字替换'):22s} {kanji(w)}")
