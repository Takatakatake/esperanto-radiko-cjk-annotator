# -*- coding: utf-8 -*-
"""
抽出移植の忠実性検証:
旧PEJVO(202501) から E_stem と語根リストを再抽出し、
アプリ同梱の既存ファイルと一致するか確認する。
"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624\_analysis_20260625")
from extract_lib import normalize_lines, extract_estem, extract_roots, lp

APP = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624\Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool"
OLD_PEJVO = APP + r"\20250215_汉字化_世界语文本を汉字替换、或いはHTML格式の翻译rubyを添加するAPPの制作过程を明确に(分かりやすく)整理したFolder\世界语全部单词列表_约44700个(原pejvo.txt)_utf8转换_第二部分以后重点修正_追加2024年版PEJVO更新项目_最终版202501.txt"
DATA = APP + r"\Appの运行に使用する各类文件"
EXIST_ESTEM = DATA + r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json"
EXIST_ROOTS = DATA + r"\世界语全部词根_约11137个_202501.txt"

lines = normalize_lines(OLD_PEJVO, skip_marker_lines=False)

# ---- E_stem ----
my_estem = extract_estem(lines)
with open(lp(EXIST_ESTEM), encoding="utf-8") as f:
    ex_estem = json.load(f)

print("="*64)
print("【E_stem 抽出 検証 (旧PEJVO→自前抽出 vs 既存ファイル)】")
print(f"自前 entry数 : {len(my_estem)}")
print(f"既存 entry数 : {len(ex_estem)}")
# 順序込み完全一致
order_match = (my_estem == ex_estem)
print(f"順序込み完全一致 : {order_match}")
if not order_match:
    # 集合として比較
    my_set = set(tuple(x) for x in my_estem)
    ex_set = set(tuple(x) for x in ex_estem)
    print(f"集合一致 : {my_set == ex_set}")
    print(f"  自前のみ : {len(my_set - ex_set)} 例: {list(my_set - ex_set)[:10]}")
    print(f"  既存のみ : {len(ex_set - my_set)} 例: {list(ex_set - my_set)[:10]}")
    # 順序の最初の相違位置
    for idx in range(min(len(my_estem), len(ex_estem))):
        if my_estem[idx] != ex_estem[idx]:
            print(f"  最初の順序相違 idx={idx}: 自前={my_estem[idx]} 既存={ex_estem[idx]}")
            print(f"    前後(既存): {ex_estem[max(0,idx-2):idx+3]}")
            break

# ---- 語根 ----
my_roots = extract_roots(lines)
with open(lp(EXIST_ROOTS), encoding="utf-8") as f:
    ex_roots = [ln.strip() for ln in f if ln.strip()]

print()
print("="*64)
print("【語根 抽出 検証】")
print(f"自前 語根数 : {len(my_roots)}")
print(f"既存 語根数 : {len(ex_roots)}")
ms, es = set(my_roots), set(ex_roots)
print(f"集合一致 : {ms == es}")
print(f"  自前のみ : {sorted(ms - es)[:20]}")
print(f"  既存のみ : {sorted(es - ms)[:20]}")
