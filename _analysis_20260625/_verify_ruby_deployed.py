# -*- coding: utf-8 -*-
"""デプロイ済みルビ注釈モード(最终的な替换用リスト...合并3个JSON文件.json)を検証。
 - 長文の語根分解＋訳ルビ(学習補助)
 - 語根忠実性: an/estez が 否定/感覚 で出る(麻酔でない)こと
 - ルビサイズ: サイズクラス(XXL_L等)が付与されること"""
import json, sys, re, os
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
FMT = 'HTML格式_Ruby文字_大小调整'
RUBY = r"\最终的な替换用リスト(列表)(合并3个JSON文件).json"
APPS = {'JP': r"\Esperanto-Kanji-Ruby-JA",
        'ZH': r"\Esperanto-Kanji-Ruby-ZH",
        'KO': r"\Esperanto-Kanji-Ruby-KO"}
TEXT = "La juna studento lernas Esperanton kaj diligente legas multajn interesajn librojn pri scienco kaj historio."
def pairs(html):
    out=[]; pos=0
    for m in re.finditer(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', html):
        pre=re.sub(r'<[^>]+>','',html[pos:m.start()]).strip()
        if pre: out.append((pre,''))
        out.append((m.group(1), m.group(2))); pos=m.end()
    return out
for key, d in APPS.items():
    DATA = BASE + d + r"\Appの运行に使用する各类文件"
    print(f"=== {key} ===")
    sys.path.insert(0, BASE + d)
    import importlib; m = importlib.import_module('esp_text_replacement_module')
    with open(lp(DATA + RUBY), encoding='utf-8') as f: dd = json.load(f)
    GL = dd['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
    G2 = dd['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
    GG = dd['全域替换用のリスト(列表)型配列(replacements_final_list)']
    ps = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
    pl = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
    def seg(t): return m.orchestrate_comprehensive_esperanto_text_replacement(t,ps,GL,pl,GG,G2,FMT)
    h = seg(TEXT)
    print("  [長文 語根/訳]:", ' '.join(f'{b}={g}' if g else b for b,g in pairs(h)))
    for w in ['anestezo','anestezi','kulturo']:
        print(f"  [{w}]:", ' '.join(f'{b}={g}' if g else b for b,g in pairs(seg(w))))
    # サイズクラス確認(1語の生HTML)
    raw=seg('elektrono')
    print("  [elektrono 生HTML]:", raw[:200])
    del sys.modules['esp_text_replacement_module']
