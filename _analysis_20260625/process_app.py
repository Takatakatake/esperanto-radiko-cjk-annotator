# -*- coding: utf-8 -*-
"""
1アプリを処理 (1プロセス1アプリ; モジュールimportキャッシュ回避)。
  python process_app.py <JP|ZH|KO> <validate|deploy>
validate: 旧ソースで再生成し既存JSONと一致確認。
deploy  : 既存ファイルをバックアップ→新ソース(E_stem/語根リスト)を配置→新ソースで最終JSON再生成。
"""
import json, sys, os, shutil, datetime
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp

OUT = BASE + r"\_analysis_20260625\out"
NEW_ESTEM = OUT + r"\new_E_stem_with_Part_Of_Speech_list.json"
NEW_ROOTS = OUT + r"\new_rootlist.txt"
FMT = 'HTML格式_Ruby文字_大小调整'

APPS = {
 'JP': {'dir': r"\Esperanto-Kanji-Ruby-JA",
        'csv': r"\エスペラント語根-日本語訳ルビ対応リスト.csv"},
 'ZH': {'dir': r"\Esperanto-Kanji-Ruby-ZH",
        'csv': r"\世界语词根-中文注释对应列表.csv"},
 'KO': {'dir': r"\Esperanto-Kanji-Ruby-KO",
        'csv': r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv"},
}
ESTEM_NAME = r"\E_stem.json"
ROOTS_NAME = r"\root_list.txt"
FINAL_NAME = r"\置換リスト_ルビ.json"
STEM_NAME  = r"\分解設定.json"
USER_NAME  = r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"

KEYS = [
    "全域替换用のリスト(列表)型配列(replacements_final_list)",
    "二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)",
    "局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)",
]

def to_map(lst):
    return {e[0]: e[1] for e in lst}

def main():
    key, mode = sys.argv[1], sys.argv[2]
    app = APPS[key]
    APPDIR = BASE + app['dir']
    DATA = APPDIR + r"\app_data"
    csv = DATA + app['csv']
    stem = DATA + STEM_NAME
    user = DATA + USER_NAME
    old_estem = DATA + ESTEM_NAME
    old_roots = DATA + ROOTS_NAME
    final = DATA + FINAL_NAME

    if mode == 'validate':
        combined = generate(APPDIR, DATA, csv, stem, user, old_estem, old_roots, FMT)
        with open(lp(final), encoding='utf-8') as f:
            existing = json.load(f)
        ok = True
        for k in KEYS:
            mm, em = to_map(combined[k]), to_map(existing.get(k, []))
            same = (mm == em)
            ok = ok and same
            print(f"  [{key}] {k.split('(')[0]}: 件数 自{len(combined[k])}/既{len(existing.get(k,[]))} 一致={same}")
        print(f"  [{key}] VALIDATE {'PASS' if ok else 'FAIL'}")
        return

    if mode == 'deploy':
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bdir = DATA + r"\_backup_before_decomp_update_" + ts
        os.makedirs(lp(bdir), exist_ok=True)
        # バックアップ
        for src in (old_estem, old_roots, final):
            base = os.path.basename(src)
            shutil.copy2(lp(src), lp(os.path.join(bdir, base)))
        print(f"  [{key}] backup -> {bdir}")
        # 新ソース配置 (E_stem, 語根リスト)
        shutil.copy2(lp(NEW_ESTEM), lp(old_estem))
        shutil.copy2(lp(NEW_ROOTS), lp(old_roots))
        print(f"  [{key}] new E_stem & rootlist 配置完了")
        # 新ソースで最終JSON再生成
        combined = generate(APPDIR, DATA, csv, stem, user, old_estem, old_roots, FMT)
        with open(lp(final), 'w', encoding='utf-8') as g:
            json.dump(combined, g, ensure_ascii=False, indent=2)
        sz = os.path.getsize(lp(final)) / (1024*1024)
        print(f"  [{key}] 最終JSON再生成: 全域={len(combined[KEYS[0]])} 2文字={len(combined[KEYS[1]])} 局部={len(combined[KEYS[2]])}  ({sz:.1f} MB)")
        print(f"  [{key}] DEPLOY DONE")
        return

if __name__ == '__main__':
    main()
