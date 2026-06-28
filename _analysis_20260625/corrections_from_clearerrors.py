# -*- coding: utf-8 -*-
"""
clear_errors_tier{N}.json を元に、各アプリの語根分解法設定JSONを補正:
 - 競合する既存エントリ(同一nosl=旧E_stem向け誤分解強制)を除去(棚卸し)
 - goldの正しい分解を高優先度で追加
3アプリ適用→再生成→検証。
  python corrections_from_clearerrors.py <tier> [--write]
"""
import json, sys, re, shutil, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
OUT = BASE + r"\_analysis_20260625\out"
TIER=int(sys.argv[1]); WRITE='--write' in sys.argv
ENDINGS_SET={'o','a','e','i','u','oj','aj','on','an','ojn','ajn','as','is','os','us','n','j'}
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

with open(lp(OUT+f"\\clear_errors_tier{TIER}.json"),encoding='utf-8') as f:
    errors=json.load(f)

# 各誤りから 補正エントリ(分解, 優先度, 接尾辞) と 除去対象nosl を導出
def make_correction(gold_decomp):
    pieces=[p for p in gold_decomp.split('/') if p]
    if not pieces: return None
    nosl=''.join(pieces)
    last=pieces[-1]
    if len(pieces)>=2 and last in ('o','a','e','i') and len(last)==1:
        stem='/'.join(pieces[:-1]); stem_nosl=''.join(pieces[:-1])
        suffixes=["verbo_s1","verbo_s2","o","a","e"]
    else:
        # 固定形(alten等)や語尾でない末尾: 全体を強制
        stem=gold_decomp; stem_nosl=nosl
        suffixes=["ne"]
    prio=len(stem_nosl)*10000+4000
    return {'stem':stem,'stem_nosl':stem_nosl,'prio':prio,'suffixes':suffixes,'word_nosl':nosl}

corrs={}; remove_nosl=set()
for e in errors:
    c=make_correction(e['gold'])
    if not c: continue
    corrs[c['stem_nosl']]=c
    remove_nosl.add(c['stem_nosl']); remove_nosl.add(c['word_nosl'])
print(f"Tier{TIER} 明確誤り {len(errors)} → 補正エントリ {len(corrs)}")
for sn,c in list(corrs.items())[:30]:
    print(f"  force [{c['stem']}] prio={c['prio']} suf={c['suffixes']}")

APPS={'JP':(r"\Esperanto-Kanji-Ruby-JA",r"\エスペラント語根-日本語訳ルビ対応リスト.csv",'ja'),
      'ZH':(r"\Esperanto-Kanji-Ruby-ZH",r"\世界语词根-中文注释对应列表.csv",'zh'),
      'KO':(r"\Esperanto-Kanji-Ruby-KO",r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv",'ko')}
ESTEM=r"\PEJVO(世界语全部单词列表)'全部'について、词尾(a,i,u,e,o,n等)をcutし、comma(,)で隔てて词性と併せて记录した列表(E_stem_with_Part_Of_Speech_list).json"
ROOTS=r"\世界语全部词根_约11137个_202501.txt"; FINAL=r"\置換リスト_ルビ.json"
STEM=r"\分解設定.json"; USER=r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"; FMT='HTML格式_Ruby文字_大小调整'

def process(key, write):
    d,csvn,lang=APPS[key]; APPDIR=BASE+d; DATA=APPDIR+r"\app_data"
    sp=DATA+STEM
    with open(lp(sp),encoding='utf-8') as f: settings=json.load(f)
    # 競合除去: nosl が remove_nosl に含まれる既存3要素エントリを削除
    removed=0; kept=[]
    for e in settings:
        if isinstance(e,list) and len(e)==3 and isinstance(e[0],str):
            ns=e[0].replace('/','').strip()
            if ns in remove_nosl: removed+=1; continue
        kept.append(e)
    settings=kept
    for sn,c in corrs.items():
        settings.append([c['stem'], c['prio'], list(c['suffixes'])])
    tmp=DATA+r"\_settings_tier_tmp.json"
    with open(lp(tmp),'w',encoding='utf-8') as g: json.dump(settings,g,ensure_ascii=False,indent=1)
    with open(lp(OUT+f"\\word_anno_{lang}.json"),encoding='utf-8') as f: word_anno=json.load(f)
    combined=generate(APPDIR,DATA,DATA+csvn,tmp,DATA+USER,DATA+ESTEM,DATA+ROOTS,FMT,word_anno=word_anno)
    import os
    if write:
        shutil.copy2(lp(sp),lp(sp+".bak_preTier"+str(TIER)))
        with open(lp(sp),'w',encoding='utf-8') as g: json.dump(settings,g,ensure_ascii=False,indent=1)
        with open(lp(DATA+FINAL),'w',encoding='utf-8') as g: json.dump(combined,g,ensure_ascii=False,indent=2)
        os.remove(lp(tmp))
        print(f"  [{key}] 除去{removed} 追加{len(corrs)} → 書込完了")
    else:
        os.remove(lp(tmp)); print(f"  [{key}] 除去{removed} 追加{len(corrs)} (未書込)")
    return combined

# JP検証
combined=process('JP', False)
sys.path.insert(0, BASE+APPS['JP'][0])
from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement as orch, import_placeholders as imp
DATA=BASE+APPS['JP'][0]+r"\app_data"
ps=imp(lp(DATA+r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt")); pl=imp(lp(DATA+r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
g_=combined["全域替换用のリスト(列表)型配列(replacements_final_list)"]; l_=combined["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]; c_=combined["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
def segplain(w): return re.sub(r'<[^>]+>','',orch(w,ps,l_,pl,g_,c_,FMT))
print("  検証(誤り語):")
for e in errors[:12]:
    full=''.join(p for p in e['gold'].split('/') if p)
    print(f"    {full:14s} {segplain(full)}")
if WRITE:
    process('ZH', True); process('KO', True); process('JP', True)
    print("3アプリ書込完了")
