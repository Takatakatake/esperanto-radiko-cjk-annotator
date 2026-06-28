# -*- coding: utf-8 -*-
import json, sys, re, os
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
FMT = 'HTML格式_Ruby文字_大小调整_汉字替换'
KJ = r"\置換リスト_漢字.json"
APPS = {'JP': r"\Esperanto-Kanji-Ruby-JA",
        'ZH': r"\Esperanto-Kanji-Ruby-ZH",
        'KO': r"\Esperanto-Kanji-Ruby-KO"}
TEXT = "La juna studento lernas Esperanton kaj diligente legas multajn interesajn librojn pri scienco kaj historio en la universitato."
for key, d in APPS.items():
    DATA = BASE + d + r"\app_data"
    path = DATA + KJ
    print(f"=== {key}  ({os.path.getsize(lp(path))//1024//1024}MB) ===")
    sys.path.insert(0, BASE + d)
    import importlib
    m = importlib.import_module('esp_text_replacement_module')
    with open(lp(path), encoding='utf-8') as f:
        dd = json.load(f)
    GL = dd['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
    G2 = dd['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
    GG = dd['全域替换用のリスト(列表)型配列(replacements_final_list)']
    ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
    pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
    h = m.orchestrate_comprehensive_esperanto_text_replacement(TEXT, ps, GL, pl, GG, G2, FMT)
    kanji_only = re.sub(r'<rt[^>]*>.*?</rt>', '', h); kanji_only = re.sub(r'<[^>]+>', '', kanji_only)
    print("  漢字本文:", kanji_only)
    del sys.modules['esp_text_replacement_module']
