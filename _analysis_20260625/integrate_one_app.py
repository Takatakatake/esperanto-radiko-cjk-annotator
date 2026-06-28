# -*- coding: utf-8 -*-
"""
1アプリの翻訳CSVを「現行保全 + 注釈版でギャップ補完」で更新し、最終JSONを再生成。
  python integrate_one_app.py <JP|ZH|KO>
保守的union: 現行CSVの全エントリを保全し、デプロイ済み語根のうち現行に無いものだけ注釈版から追加。
"""
import json, sys, os, shutil, datetime, csv, re
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars

OUT = BASE + r"\_analysis_20260625\out"
NEW_ROOTS = OUT + r"\new_rootlist.txt"
FMT = 'HTML格式_Ruby文字_大小调整'

APPS = {
 'JP': {'dir': r"\Esperanto-Kanji-Ruby-JA",
        'csv': r"\エスペラント語根-日本語訳ルビ対応リスト.csv", 'lang': 'ja'},
 'ZH': {'dir': r"\Esperanto-Kanji-Ruby-ZH",
        'csv': r"\世界语词根-中文注释对应列表.csv", 'lang': 'zh'},
 'KO': {'dir': r"\Esperanto-Kanji-Ruby-KO",
        'csv': r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv", 'lang': 'ko'},
}
ESTEM_NAME = r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json"
ROOTS_NAME = r"\世界语全部词根_约11137个_202501.txt"
FINAL_NAME = r"\置換リスト_ルビ.json"
STEM_NAME  = r"\分解設定.json"
USER_NAME  = r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"
KEYS = ["全域替换用のリスト(列表)型配列(replacements_final_list)",
        "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)",
        "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]

def norm(p):
    return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

def main():
    key = sys.argv[1]
    app = APPS[key]
    APPDIR = BASE + app['dir']; DATA = APPDIR + r"\app_data"
    csv_path = DATA + app['csv']
    anno_path = OUT + f"\\anno_root_{app['lang']}.csv"

    # 現行CSVの生テキスト保持 + 既存語根集合
    with open(lp(csv_path), encoding="utf-8") as f:
        cur_text = f.read()
    cur_lines = cur_text.split('\n')
    existing = set()
    for row in csv.reader(cur_lines):
        if row and row[0] and '#' not in row[0] and len(row) >= 2 and row[1].strip():
            existing.add(norm(row[0]))

    # 注釈版マップ
    anno = {}
    with open(lp(anno_path), encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0]:
                anno[row[0]] = row[1]

    # デプロイ済み語根
    with open(lp(NEW_ROOTS), encoding="utf-8") as f:
        deployed = [l.strip() for l in f if l.strip()]

    # 追加行(デプロイ済みで現行に無い & 注釈版にある)
    add = []
    for r in deployed:
        if r not in existing and r in anno:
            add.append((r, anno[r]))
    # 末尾に追記(改行整形)
    new_text = cur_text
    if not new_text.endswith('\n'):
        new_text += '\n'
    new_text += f"###↓ここから下は日中韓注釈版(20260416)から自動補完した語根訳(2026-06-25)。{len(add)}件。\n"
    for r, t in add:
        # カンマを含む訳はダブルクォートで囲む
        tt = t.replace('"', '""')
        if ',' in t or '"' in t:
            tt = f'"{tt}"'
        new_text += f"{r},{tt}\n"

    # バックアップ
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = DATA + r"\_backup_before_translation_update_" + ts
    os.makedirs(lp(bdir), exist_ok=True)
    shutil.copy2(lp(csv_path), lp(os.path.join(bdir, os.path.basename(csv_path))))
    shutil.copy2(lp(DATA + FINAL_NAME), lp(os.path.join(bdir, os.path.basename(DATA + FINAL_NAME))))
    print(f"  [{key}] backup -> {bdir}")

    # 新CSV書き込み
    with open(lp(csv_path), 'w', encoding="utf-8", newline='') as g:
        g.write(new_text)
    print(f"  [{key}] CSV更新: 既存{len(existing)} + 補完{len(add)} = {len(existing)+len(add)} 語根")

    # 最終JSON再生成(新E_stem + 新CSV)
    combined = generate(APPDIR, DATA, csv_path, DATA + STEM_NAME, DATA + USER_NAME,
                        DATA + ESTEM_NAME, DATA + ROOTS_NAME, FMT)
    with open(lp(DATA + FINAL_NAME), 'w', encoding='utf-8') as g:
        json.dump(combined, g, ensure_ascii=False, indent=2)
    sz = os.path.getsize(lp(DATA + FINAL_NAME)) / (1024*1024)
    print(f"  [{key}] 最終JSON再生成: 全域={len(combined[KEYS[0]])} 局部={len(combined[KEYS[2]])} ({sz:.1f}MB)  DONE")

if __name__ == '__main__':
    main()
