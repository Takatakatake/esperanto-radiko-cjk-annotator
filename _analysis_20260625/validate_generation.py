# -*- coding: utf-8 -*-
"""
生成ポートの忠実性検証:
現行ソース(既存 E_stem/語根リスト/CSV/設定)で再生成し、
アプリ同梱の既存 最終置換JSON と (old->new) マッピングが一致するか確認。
"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp

APP = BASE + r"\Esperanto-Kanji-Ruby-JA"
DATA = APP + r"\Appの运行に使用する各类文件"

combined = generate(
    app_module_dir=APP,
    data_dir=DATA,
    csv_path=DATA + r"\エスペラント語根-日本語訳ルビ対応リスト.csv",
    stemming_json_path=DATA + r"\世界语单词词根分解方法の使用者自定义设置.json",
    user_repl_json_path=DATA + r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json",
    estem_path=DATA + r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json",
    rootlist_path=DATA + r"\世界语全部词根_约11137个_202501.txt",
    format_type='HTML格式_Ruby文字_大小调整',
)

with open(lp(DATA + r"\最终的な替换用リスト(列表)(合并3个JSON文件).json"), encoding="utf-8") as f:
    existing = json.load(f)

KEYS = [
    "全域替换用のリスト(列表)型配列(replacements_final_list)",
    "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)",
    "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)",
]

def to_map(lst):
    d = {}
    for e in lst:
        d[e[0]] = e[1]   # old -> new (placeholder無視)
    return d

print("="*70)
print("【生成ポート 忠実性検証 (現行ソース再生成 vs 既存JSON)】")
for k in KEYS:
    mine = combined[k]
    exist = existing.get(k, [])
    mm, em = to_map(mine), to_map(exist)
    keys_match = set(mm) == set(em)
    val_mismatch = [(o, mm[o], em[o]) for o in (set(mm) & set(em)) if mm[o] != em[o]]
    only_mine = set(mm) - set(em)
    only_exist = set(em) - set(mm)
    print(f"\n--- {k.split('(')[0]} ---")
    print(f"  自前 件数 : {len(mine)} / 既存 件数 : {len(exist)}")
    print(f"  old集合 一致 : {keys_match}")
    print(f"  値(new)相違 : {len(val_mismatch)} 件")
    print(f"  自前のみ old : {len(only_mine)} 件  例:{sorted(only_mine)[:8]}")
    print(f"  既存のみ old : {len(only_exist)} 件  例:{sorted(only_exist)[:8]}")
    for o, mnew, enew in val_mismatch[:5]:
        print(f"    値相違 [{o}]\n      自前: {mnew[:90]}\n      既存: {enew[:90]}")
