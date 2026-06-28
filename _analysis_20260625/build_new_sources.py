# -*- coding: utf-8 -*-
"""
WSL学習者版(ゴールドスタンダード)から
  - 新 E_stem_with_Part_Of_Speech_list.json
  - 新 語根リスト .txt
を生成し、_analysis_20260625/out/ に保存する。
語根リストは「新E_stemの全スラッシュ片」から作るため、
E_stemの各片が必ず語根リストに存在し、分解=ゴールドのスラッシュ が保証される。
"""
import json, os, sys, re
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import normalize_lines, extract_estem, lp

GOLD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
OUTDIR = BASE + r"\_analysis_20260625\out"
os.makedirs(OUTDIR, exist_ok=True)

# 既存(比較用)
APP = BASE + r"\Esperanto-Kanji-Ruby-JA"
DATA = APP + r"\app_data"
OLD_ESTEM = DATA + r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json"
OLD_ROOTS = DATA + r"\世界语全部词根_约11137个_202501.txt"

# --- gold 読み込み・抽出 ---
lines = normalize_lines(GOLD, skip_marker_lines=True)
new_estem = extract_estem(lines)

# --- 新語根リスト: 新E_stemの全片(len>=2) ---
roots = set()
for item in new_estem:
    if len(item) != 2:
        continue
    stem = item[0]
    for piece in stem.split('/'):
        p = piece.strip()
        if len(p) >= 2 and '#' not in p and not any(c.isdigit() for c in p):
            roots.add(p)
new_roots = sorted(roots, key=lambda r: (-len(r), r))

# --- 旧データとの比較 ---
with open(lp(OLD_ESTEM), encoding="utf-8") as f:
    old_estem = json.load(f)
with open(lp(OLD_ROOTS), encoding="utf-8") as f:
    old_roots = [l.strip() for l in f if l.strip()]

old_estem_set = set((x[0], x[1]) for x in old_estem if len(x) == 2)
new_estem_set = set((x[0], x[1]) for x in new_estem if len(x) == 2)
old_root_set, new_root_set = set(old_roots), set(new_roots)

print("="*70)
print("【新ソース生成 (gold学習者版由来)】")
print(f"新 E_stem entry数      : {len(new_estem)}  (旧: {len(old_estem)})")
print(f"新 E_stem ユニーク数    : {len(new_estem_set)}  (旧: {len(old_estem_set)})")
print(f"新 語根数              : {len(new_roots)}  (旧: {len(old_roots)})")
print(f"  語根 新規追加        : {len(new_root_set - old_root_set)}")
print(f"  語根 旧のみ(消失)     : {len(old_root_set - new_root_set)}")
print(f"    消失例: {sorted(old_root_set - new_root_set)[:30]}")
print(f"  語根 新規例          : {sorted(new_root_set - old_root_set)[:30]}")

# --- 保存 ---
with open(lp(OUTDIR + r"\new_E_stem_with_Part_Of_Speech_list.json"), "w", encoding="utf-8") as g:
    json.dump(new_estem, g, ensure_ascii=False, indent=2)
with open(lp(OUTDIR + r"\new_rootlist.txt"), "w", encoding="utf-8") as g:
    for r in new_roots:
        g.write(r + "\n")
print(f"\n保存完了:\n  {OUTDIR}\\new_E_stem_with_Part_Of_Speech_list.json\n  {OUTDIR}\\new_rootlist.txt")
