# -*- coding: utf-8 -*-
"""ルビサイズ修正(大文字変種のクラス再計算)込みで、3アプリのルビJSONを現在の分解設定から再生成。
   分解(語根境界)・訳は不変。大文字始まり語のルビサイズだけが正しくなる。
   python _regen_ruby_sizefix.py [--write]"""
import json, sys, os, shutil
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp
OUT = BASE + r"\_analysis_20260625\out"; WRITE = '--write' in sys.argv
APPS = {'JP': (r"\Esperanto-Kanji-Ruby-JA", r"\エスペラント語根-日本語訳ルビ対応リスト.csv", 'ja'),
        'ZH': (r"\Esperanto-Kanji-Ruby-ZH", r"\世界语词根-中文注释对应列表.csv", 'zh'),
        'KO': (r"\Esperanto-Kanji-Ruby-KO", r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv", 'ko')}
ESTEM = r"\E_stem.json"; ROOTS = r"\root_list.txt"; STEM = r"\分解設定.json"
USER = r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"; FINAL = r"\置換リスト_ルビ.json"
FMT = 'HTML格式_Ruby文字_大小调整'
for key, (d, csvn, lang) in APPS.items():
    APPDIR = BASE + d; DATA = APPDIR + r"\app_data"
    with open(lp(OUT + f"\\word_anno_{lang}.json"), encoding='utf-8') as f: wa = json.load(f)
    print(f"[{key}] 再生成中...")
    combined = generate(APPDIR, DATA, DATA + csvn, DATA + STEM, DATA + USER, DATA + ESTEM, DATA + ROOTS, FMT, word_anno=wa)
    n = len(combined["全域替换用のリスト(列表)型配列(replacements_final_list)"])
    if WRITE:
        tgt = DATA + FINAL
        bak = tgt + ".bak_preRubySizeFix"
        if not os.path.exists(lp(bak)): shutil.copy2(lp(tgt), lp(bak))
        with open(lp(tgt), 'w', encoding='utf-8') as g: json.dump(combined, g, ensure_ascii=False, indent=2)
        print(f"  [{key}] ルビJSON書込 (GG {n}件)")
    else:
        print(f"  [{key}] 生成のみ (GG {n}件, 未書込)")
print("完了。" + ("書込済(.bak退避済)。次に _verify_rubysize で確認 → apply_kanji で漢字も再生成。" if WRITE else "テストOK(--write で書込)。"))
