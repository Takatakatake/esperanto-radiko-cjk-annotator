# -*- coding: utf-8 -*-
"""
新ソース(gold由来 E_stem/語根リスト)で日本語版の最終置換JSONを再生成し、
旧JSONとサンプル語のエンドツーエンド出力を比較して分解改善を検証する。
"""
import json, sys, re
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp

APP = BASE + r"\Esperanto-Kanji-Ruby-JA"
DATA = APP + r"\Appの运行に使用する各类文件"
OUT = BASE + r"\_analysis_20260625\out"
sys.path.insert(0, APP)
from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement, import_placeholders as imp2

CSV = DATA + r"\エスペラント語根-日本語訳ルビ対応リスト.csv"
STEM = DATA + r"\世界语单词词根分解方法の使用者自定义设置.json"
USER = DATA + r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"
OLD_ESTEM = DATA + r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json"
OLD_ROOTS = DATA + r"\世界语全部词根_约11137个_202501.txt"
NEW_ESTEM = OUT + r"\new_E_stem_with_Part_Of_Speech_list.json"
NEW_ROOTS = OUT + r"\new_rootlist.txt"
FMT = 'HTML格式_Ruby文字_大小调整'

def build(estem, roots):
    return generate(APP, DATA, CSV, STEM, USER, estem, roots, FMT)

print("旧ソースでJSON生成中...")
old_combined = build(OLD_ESTEM, OLD_ROOTS)
print("新ソースでJSON生成中...")
new_combined = build(NEW_ESTEM, NEW_ROOTS)

# 新JSON保存
with open(lp(OUT + r"\new_最终的な替换用リスト(列表)(合并3个JSON文件).json"), "w", encoding="utf-8") as g:
    json.dump(new_combined, g, ensure_ascii=False, indent=2)

for name, c in [("旧", old_combined), ("新", new_combined)]:
    print(f"{name} リスト件数: 全域={len(c['全域替换用のリスト(列表)型配列(replacements_final_list)'])} "
          f"2文字={len(c['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)'])} "
          f"局部={len(c['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)'])}")

# --- エンドツーエンド比較 ---
ph_skip = imp2(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
ph_local = imp2(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))

def run(text, combined):
    return orchestrate_comprehensive_esperanto_text_replacement(
        text, ph_skip,
        combined['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)'],
        ph_local,
        combined['全域替换用のリスト(列表)型配列(replacements_final_list)'],
        combined['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)'],
        FMT)

def strip_to_segments(html):
    """HTMLルビ出力から、ルビ(rt内)を除いた構造を簡易抽出して分解境界を見る。
    <ruby>X<rt ...>Y</rt></ruby> -> [Y] を連結 (訳語側) で表示。"""
    # rt の中身(訳/ローマ字)を | で区切って並べる
    segs = re.findall(r'<rt[^>]*>(.*?)</rt>', html)
    plain = re.sub(r'<[^>]+>', '', html)
    return plain, segs

TESTS = ["monomanio","aerobia","fizioterapio","anemometro","ekspresionismo",
         "papiliono","mikrono","sinkrono","altruismo","agronomo","bigamio",
         "telegrafreto","reorganizi","amiko","hundo","bona","lernejano"]

print("\n" + "="*72)
print("【エンドツーエンド分解比較 (旧JSON → 新JSON)】 訳/ローマ字セグメント")
for w in TESTS:
    o_plain, o_seg = strip_to_segments(run(w, old_combined))
    n_plain, n_seg = strip_to_segments(run(w, new_combined))
    changed = "★変化" if o_seg != n_seg else "  同じ"
    print(f"{changed} [{w}]")
    print(f"      旧: {o_seg}")
    print(f"      新: {n_seg}")
