# -*- coding: utf-8 -*-
"""
漢字化モード(参照2 新漢字割り当て)を3アプリへ統合。
 - 新漢字CSV(out/kanji_root.csv, 参照2 漢字注入版由来 7791語根)を各アプリへ配置
 - 改善済み分解設定(deployed) + word_kanji(per-word漢字) + 漢字化フォーマットで
   漢字化モードの最終JSONを生成・配置
形態: <ruby>漢字<rt>エス語根</rt></ruby> (漢字本文・語根ルビ=学習補助)
  python apply_kanji.py [--write]
"""
import json, sys, re, shutil, os
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp
OUT = BASE + r"\_analysis_20260625\out"
WRITE = '--write' in sys.argv
FMT = 'HTML格式_Ruby文字_大小调整_汉字替换'   # 漢字本文・語根ルビ
KANJI_CSV_SRC = OUT + r"\kanji_root.csv"
KANJI_CSV_NAME = r"\世界语词根-汉字对应列表_参照2新割当_7791.csv"
KANJI_JSON_NAME = r"\置換リスト_漢字.json"

APPS={'JP':r"\Esperanto-Kanji-Ruby-JA",
      'ZH':r"\Esperanto-Kanji-Ruby-ZH",
      'KO':r"\Esperanto-Kanji-Ruby-KO"}
ESTEM=r"\E_stem.json"
ROOTS=r"\root_list.txt"
STEM=r"\分解設定.json"; USER=r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"

with open(lp(OUT+r"\word_kanji.json"),encoding='utf-8') as f: word_kanji=json.load(f)
print(f"word_kanji {len(word_kanji)}語形 / FMT={FMT}")

# 漢字化「偽分解」(ユーザー方針: 注釈ルビ=コーパス準拠で一体, 漢字=マスター準拠で分解)。
# ルビ用に一体化強制した国際語のうち、マスターgold語根分解辞書が分解する語
# (psikologi→psik/o/logi, agresiv→agres/iv, esperant→esper/ant 等)は、
# 漢字モードでは強制を外して偽分解し、マスター漢字割り当てを各語根に適用する。
# ルビ側(apply_confirmed)は一体のまま不変(独立生成)。
KANJI_DECOMPOSE = {"esperant"}
_grv = OUT + r"\gold_revert_roots.json"   # マスターgoldが分解する国際語根(51)
if os.path.exists(lp(_grv)):
    KANJI_DECOMPOSE |= set(json.load(open(lp(_grv), encoding="utf-8")))

def _kanji_settings(DATA):
    """漢字用設定: KANJI_DECOMPOSEの一体化強制を除去した一時設定を作り、パスを返す。"""
    with open(lp(DATA+STEM), encoding="utf-8") as f: sett = json.load(f)
    sett = [e for e in sett if not (isinstance(e, list) and len(e) >= 1
            and str(e[0]).replace('/', '') in KANJI_DECOMPOSE)]
    tmp = DATA + r"\_kanji_settings_tmp.json"
    with open(lp(tmp), "w", encoding="utf-8") as g: json.dump(sett, g, ensure_ascii=False)
    return tmp

def process(key, write):
    d=APPS[key]; APPDIR=BASE+d; DATA=APPDIR+r"\app_data"
    # 新漢字CSVを配置
    if write:
        shutil.copy2(lp(KANJI_CSV_SRC), lp(DATA+KANJI_CSV_NAME))
    csvp = DATA+KANJI_CSV_NAME if (write and os.path.exists(lp(DATA+KANJI_CSV_NAME))) else KANJI_CSV_SRC
    kset = _kanji_settings(DATA)
    combined=generate(APPDIR,DATA,csvp,kset,DATA+USER,DATA+ESTEM,DATA+ROOTS,FMT,word_anno=word_kanji)
    os.remove(lp(kset))
    if write:
        with open(lp(DATA+KANJI_JSON_NAME),'w',encoding='utf-8') as g: json.dump(combined,g,ensure_ascii=False,indent=2)
        print(f"  [{key}] 漢字化JSON書込: ...{KANJI_JSON_NAME}")
    else:
        print(f"  [{key}] 生成のみ(未書込) 全域エントリ {len(combined['全域替换用のリスト(列表)型配列(replacements_final_list)'])}")
    return combined

# JP検証
combined=process('JP', WRITE)
sys.path.insert(0, BASE+APPS['JP'])
from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement as orch, import_placeholders as imp
DATA=BASE+APPS['JP']+r"\app_data"
ps=imp(lp(DATA+r"\placeholders_skip.txt")); pl=imp(lp(DATA+r"\placeholders_localcapture.txt"))
g_=combined["全域替换用のリスト(列表)型配列(replacements_final_list)"]; l_=combined["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]; c_=combined["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
def seg(t): return orch(t,ps,l_,pl,g_,c_,FMT)
def plain(t): return re.sub(r'<[^>]+>','',seg(t))
print("\n  漢字化検証(漢字本文のみ抽出):")
samples=['La rapida bruna vulpo saltas trans la dormema hundo.',
         'Mi amas vin kaj ŝi konstruas grandan domon.',
         'Datumoj pri nomadoj montras ke ili vojaĝis tra Abu-Dabio.',
         'elektrono','komputilo','internacia','scienco']
for s in samples:
    # rt(ルビ=語根)を除き親文字(漢字)のみ表示して漢字化結果を見る
    h=seg(s)
    kanji_only=re.sub(r'<rt[^>]*>.*?</rt>','',h); kanji_only=re.sub(r'<[^>]+>','',kanji_only)
    print(f"    {s}")
    print(f"      漢字: {kanji_only}")
if WRITE:
    process('ZH', True); process('KO', True)
    print("\n3アプリ漢字化統合完了")
