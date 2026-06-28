# -*- coding: utf-8 -*-
"""デプロイ済みアプリのルビ注釈(語根→日本語訳)を実際に出力して、語根忠実注釈が機能しているか実証。
   偽分解語(an/emi, esperant等)・通常語・PIV語を確認。"""
import re, sys, json
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
appdir = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, appdir)
import esp_text_replacement_module as m
DATA = appdir + r"\Appの运行に使用する各类文件"
dd = json.load(open(lp(DATA + r"\最终的な替换用リスト(列表)(合并3个JSON文件).json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
pl = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
def anno(t):
    h = m.orchestrate_comprehensive_esperanto_text_replacement(" "+t+" ", ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
    out = []
    pos = 0
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', h):
        pre = re.sub(r'<[^>]+>', '', h[pos:mm.start()])
        for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+', pre, re.I): out.append(f"{ch}")
        out.append(f"{mm.group(1)}「{mm.group(2)}」"); pos = mm.end()
    tail = re.sub(r'<[^>]+>', '', h[pos:])
    for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+', tail, re.I): out.append(ch)
    return ' / '.join(out)
WORDS = ['abelbredisto', 'anemia', 'esperanto', 'esperante', 'tereno', 'malsanulejo',
         'albuminurio', 'internacia', 'lernejeto', 'fervojo']
print("=== アプリのルビ注釈(語根「日本語訳」)実証 ===")
for w in WORDS:
    print(f"  {w:16s} -> {anno(w)}")
