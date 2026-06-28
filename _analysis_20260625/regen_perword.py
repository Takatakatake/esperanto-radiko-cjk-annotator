# -*- coding: utf-8 -*-
"""
per-word(文脈依存)注釈で最終JSONを再生成。
  python regen_perword.py <JP|ZH|KO> [--write]
--write 無し: 生成してサンプル語で検証のみ(書き込まない)。
"""
import json, sys, os, shutil, datetime, re, glob
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp
OUT = BASE + r"\_analysis_20260625\out"
FMT = 'HTML格式_Ruby文字_大小调整'
APPS = {
 'JP': (r"\Esperanto-Kanji-Ruby-JA", r"\エスペラント語根-日本語訳ルビ対応リスト.csv", 'ja'),
 'ZH': (r"\Esperanto-Kanji-Ruby-ZH", r"\世界语词根-中文注释对应列表.csv", 'zh'),
 'KO': (r"\Esperanto-Kanji-Ruby-KO", r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv", 'ko'),
}
ESTEM = r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json"
ROOTS = r"\世界语全部词根_约11137个_202501.txt"
FINAL = r"\置換リスト_ルビ.json"
STEM  = r"\世界语单词词根分解方法の使用者自定义设置.json"
USER  = r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"

key = sys.argv[1]; write = '--write' in sys.argv
d, csvn, lang = APPS[key]
APPDIR = BASE + d; DATA = APPDIR + r"\app_data"
with open(lp(OUT + f"\\word_anno_{lang}.json"), encoding="utf-8") as f:
    word_anno = json.load(f)
print(f"[{key}] word_anno {len(word_anno)} 語形 ロード, 生成中...")
combined = generate(APPDIR, DATA, DATA+csvn, DATA+STEM, DATA+USER, DATA+ESTEM, DATA+ROOTS, FMT, word_anno=word_anno)

# 検証(JPのみ詳細)
if lang == 'ja':
    sys.path.insert(0, APPDIR)
    from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement, import_placeholders as imp
    ph_skip = imp(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
    ph_local = imp(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
    g = combined["全域替换用のリスト(列表)型配列(replacements_final_list)"]
    l = combined["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
    c = combined["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
    def run(t): return orchestrate_comprehensive_esperanto_text_replacement(t,ph_skip,l,ph_local,g,c,FMT)
    def segs(h): return re.findall(r'<rt[^>]*>(.*?)</rt>', h)
    print("  --- 文脈依存検証(per-word) ---")
    for w in ["monomanio","mono","monero","kulturo","abelkulturo","akvokulturo","zoologio","biologio",
              "amiko","hundo","bona","internacia","kuracisto","komunismo","alkoholismo"]:
        print(f"    {w:14s} {segs(run(w))}")

if write:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = DATA + r"\_backup_before_perword_" + ts
    os.makedirs(lp(bdir), exist_ok=True)
    shutil.copy2(lp(DATA + FINAL), lp(os.path.join(bdir, os.path.basename(DATA + FINAL))))
    with open(lp(DATA + FINAL), 'w', encoding='utf-8') as gg:
        json.dump(combined, gg, ensure_ascii=False, indent=2)
    sz = os.path.getsize(lp(DATA + FINAL))/(1024*1024)
    print(f"  [{key}] 書込完了 ({sz:.1f}MB, backup={os.path.basename(bdir)})")
else:
    print(f"  [{key}] 検証のみ(未書込)")
