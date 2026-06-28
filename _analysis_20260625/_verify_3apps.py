# -*- coding: utf-8 -*-
"""3アプリ(JP/ZH/KO)のデプロイ済みJSON(ルビ・漢字 両モード)が正しく動き、
   tier17/18の是正(tereno/akrediti)が反映されているかを一括確認。"""
import re, sys, json
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
APPS = {'JP': r"\Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool",
        'ZH': r"\Esperanto-Hanzi-Converter-and-Ruby-Annotation-Tool-Chinese",
        'KO': r"\Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool-Korean"}
WORDS = ['tereno', 'akrediti', 'anemia', 'malsanulejo']
for key, d in APPS.items():
    APPDIR = BASE + d; DATA = APPDIR + r"\Appの运行に使用する各类文件"
    sys.path.insert(0, APPDIR)
    import importlib, esp_text_replacement_module as m
    importlib.reload(m)
    ps = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
    pl = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
    def load(name):
        dd = json.load(open(lp(DATA + name), encoding="utf-8"))
        return (dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"],
                dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"],
                dd["全域替换用のリスト(列表)型配列(replacements_final_list)"])
    try:
        RB = load(r"\最终的な替换用リスト(列表)(合并3个JSON文件).json")
        KJ = load(r"\最终的な替换用リスト(列表)_漢字化_新割当版.json")
    except Exception as e:
        print(f"[{key}] JSON読込失敗: {e}"); continue
    def roots(t, JS, fmt):
        GL, G2, GG = JS
        h = m.orchestrate_comprehensive_esperanto_text_replacement(" "+t+" ", ps, GL, pl, GG, G2, fmt)
        toks=[]; pos=0
        for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', h):
            for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+', re.sub(r'<[^>]+>','',h[pos:mm.start()]), re.I): toks.append(ch)
            toks.append(mm.group(1)); pos=mm.end()
        for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+', re.sub(r'<[^>]+>','',h[pos:]), re.I): toks.append(ch)
        return '/'.join(toks)
    print(f"=== [{key}] ルビJSON {len(RB[2])}件 / 漢字JSON {len(KJ[2])}件 ===")
    for w in WORDS:
        rb = roots(w, RB, 'HTML格式_Ruby文字_大小调整')
        kj = roots(w, KJ, 'HTML格式_Ruby文字_大小调整_汉字替换')
        print(f"  {w:14s} ルビ分解={rb:20s} 漢字分解={kj}")
