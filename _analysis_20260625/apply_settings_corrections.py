# -*- coding: utf-8 -*-
"""
アプリの語根分解法設定JSON(世界语单词词根分解方法...)に、明確な分解誤りの補正エントリを追加。
仕組みに沿った段階補正。  python apply_settings_corrections.py <JP|ZH|KO> [--write]
"""
import json, sys, os, shutil, re
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp
APPS = {'JP':(r"\Esperanto-Kanji-Ruby-JA",r"\エスペラント語根-日本語訳ルビ対応リスト.csv",'ja'),
        'ZH':(r"\Esperanto-Kanji-Ruby-ZH",r"\世界语词根-中文注释对应列表.csv",'zh'),
        'KO':(r"\Esperanto-Kanji-Ruby-KO",r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv",'ko')}
ESTEM=r"\E_stem.json"
ROOTS=r"\root_list.txt"; FINAL=r"\置換リスト_ルビ.json"
STEM=r"\分解設定.json"; USER=r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"; FMT='HTML格式_Ruby文字_大小调整'

# 明確な分解誤りの補正(言語非依存)。[分解(/), 優先度, 接尾辞]
CORRECTIONS = [
  ["akompan", 75000, ["verbo_s1","verbo_s2","o","a","e"]],   # akompani→akompan/i (×a/kompani company誤マッチ)
  ["brokant", 75000, ["verbo_s1","verbo_s2","o","a"]],        # brokant/i (×brok/ant 過剰分割)
]

key=sys.argv[1]; write='--write' in sys.argv
d,csvn,lang=APPS[key]; APPDIR=BASE+d; DATA=APPDIR+r"\app_data"
sp=DATA+STEM
with open(lp(sp),encoding='utf-8') as f: settings=json.load(f)
# 既存の同一分解エントリを除去してから追加(重複防止)
corr_keys={c[0].replace('/','') for c in CORRECTIONS}
settings=[e for e in settings if not (isinstance(e,list) and len(e)==3 and isinstance(e[0],str) and e[0].replace('/','') in corr_keys)]
settings += [list(c) for c in CORRECTIONS]
print(f"[{key}] 設定エントリ数 {len(settings)} (補正{len(CORRECTIONS)}件追加)")

with open(lp(OUT_TMP:=DATA+r"\_settings_corrected_tmp.json"),'w',encoding='utf-8') as g:
    json.dump(settings,g,ensure_ascii=False,indent=1)

with open(lp(BASE+r"\_analysis_20260625\out\word_anno_"+lang+".json"),encoding='utf-8') as f:
    word_anno=json.load(f)
combined=generate(APPDIR,DATA,DATA+csvn,OUT_TMP,DATA+USER,DATA+ESTEM,DATA+ROOTS,FMT,word_anno=word_anno)

# 検証
sys.path.insert(0,APPDIR)
from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement as orch, import_placeholders as imp
g_=combined["全域替换用のリスト(列表)型配列(replacements_final_list)"]; l_=combined["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]; c_=combined["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
ps=imp(lp(DATA+r"\placeholders_skip.txt")); pl=imp(lp(DATA+r"\placeholders_localcapture.txt"))
def segs(w): return re.findall(r'<rt[^>]*>(.*?)</rt>', orch(w,ps,l_,pl,g_,c_,FMT))
print("  検証:")
for w in ['akompani','brokanti','radiatoro','amiko','elektrono']:
    print(f"    {w:12s} {segs(w)}")

if write:
    shutil.copy2(lp(sp),lp(sp+".bak_preCorrections"))
    shutil.copy2(lp(sp+".bak_preCorrections"),lp(sp))  # keep
    with open(lp(sp),'w',encoding='utf-8') as g: json.dump(settings,g,ensure_ascii=False,indent=1)
    with open(lp(DATA+FINAL),'w',encoding='utf-8') as g: json.dump(combined,g,ensure_ascii=False,indent=2)
    os.remove(lp(OUT_TMP))
    print(f"  [{key}] 書込完了")
else:
    os.remove(lp(OUT_TMP))
    print("  検証のみ(未書込)")
