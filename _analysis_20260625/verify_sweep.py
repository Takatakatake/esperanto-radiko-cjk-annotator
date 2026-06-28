# -*- coding: utf-8 -*-
import json, sys, re
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625"); sys.path.insert(0, BASE + r"\Esperanto-Kanji-Ruby-JA")
from gen_replacement import lp
from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement as orch, import_placeholders as imp
DATA = BASE + r"\Esperanto-Kanji-Ruby-JA\Appの运行に使用する各类文件"
FMT='HTML格式_Ruby文字_大小调整'
with open(lp(DATA + r"\最终的な替换用リスト(列表)(合并3个JSON文件).json"),encoding='utf-8') as f: d=json.load(f)
g=d["全域替换用のリスト(列表)型配列(replacements_final_list)"]; l=d["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]; c=d["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
ps=imp(lp(DATA+r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt")); pl=imp(lp(DATA+r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
def segs(w): return re.findall(r'<rt[^>]*>(.*?)</rt>', orch(w,ps,l,pl,g,c,FMT))
for w in ["manometro","aeroplano","fonografo","fonometro","cefalopodoj","gastropodoj","deismo","izobaro",
          "elektrono","elektronmikroskopo","halogenido","empirismo","komanditi","endokardito","antifono",
          "anestezio","agronomio","biologio","kulturo","amiko"]:
    print(f"  {w:18s} {segs(w)}")
