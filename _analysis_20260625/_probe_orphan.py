# -*- coding: utf-8 -*-
"""孤立先頭文字 過分解(a/kred/it, f/ort, sp/ort 等)の機構解明。
   対象語の正しい全体語根がGG(主置換リスト)に存在するか、なぜ内部部分語に横取りされるかを診断。"""
import re, sys, json
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
appdir = BASE + r"\Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool"; sys.path.insert(0, appdir)
import esp_text_replacement_module as m
DATA = appdir + r"\Appの运行に使用する各类文件"
dd = json.load(open(lp(DATA + r"\最终的な替换用リスト(列表)(合并3个JSON文件).json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
pl = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
def roots(t):
    h = m.orchestrate_comprehensive_esperanto_text_replacement(" "+t+" ", ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
    toks = []; pos = 0
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', h):
        for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+', re.sub(r'<[^>]+>', '', h[pos:mm.start()]), re.I): toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+', re.sub(r'<[^>]+>', '', h[pos:]), re.I): toks.append(ch)
    return '/'.join(toks)
# GGキー集合(置換対象の生テキスト=各エントリの[0])
gg_keys = set()
for e in GG:
    if isinstance(e, (list, tuple)) and e: gg_keys.add(e[0])
print(f"GGエントリ数 {len(GG)} / ユニークkey {len(gg_keys)}")
# 孤立先頭文字を生む語(gold/corpus残差より)。期待全体根 -> 対象屈折語
WORDS = {
    'akredit': ['akredit','akrediti','akreditis'],
    'apart':   ['apart','aparta','apartigi'],
    'fort':    ['fort','forti','forta'],
    'sport':   ['sport','sporti','sportocentro'],
    'baron':   ['baron','barono'],
    'reg':     ['reg','rego','regi'],
    'fer':     ['fer','fero'],
    'tradici': ['tradici','tradicio','tradiciojn'],
    'lig':     ['lig','ligi','liganta'],
    'kred':    ['kred','kredi'],
    'ort':     ['ort','orta'],
    'port':    ['port','porti'],
}
for stem, forms in WORDS.items():
    inGG = stem in gg_keys
    # GGに含まれる、stemを部分文字列に持つ短いkey(横取り犯候補)
    stealers = sorted([k for k in gg_keys if k and k in stem and k != stem and len(k) >= 3], key=len)
    print(f"\n[{stem}] GG收录={inGG}  内部横取り候補(GG収録の部分根)={stealers}")
    for f in forms:
        print(f"    {f:18s} -> {roots(f)}")
