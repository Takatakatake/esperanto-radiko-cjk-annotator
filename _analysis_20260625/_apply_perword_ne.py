# -*- coding: utf-8 -*-
"""衝突語(forti/fero/rego等, tier17/18で除外)を per-word「固定形(ne)」で3アプリへ強制是正。
   語根パラダイムを作らないので部分文字列衝突しない。ルビ+漢字 両モード。冪等(.bak)。
   python _apply_perword_ne.py [--write]"""
import json, sys, re, shutil, os
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp
OUT = BASE + r"\_analysis_20260625\out"; WRITE='--write' in sys.argv
# per-word「ne」固定形(decomp)。是正対象の衝突語のみ。
PERWORD_DECOMP = ["fort/i","reg/o"]   # 名指しforti＋rego のみ(verb形, 検証でクリーン)。名詞語は境界ずれで除外
def ne_entries():
    out=[]
    for d in PERWORD_DECOMP:
        nosl=d.replace('/',''); out.append([d, len(nosl)*10000+5000, ["ne"]])
    return out
APPS={'JP':(r"\Esperanto-Kanji-Ruby-JA",r"\エスペラント語根-日本語訳ルビ対応リスト.csv",'ja'),
      'ZH':(r"\Esperanto-Kanji-Ruby-ZH",r"\世界语词根-中文注释对应列表.csv",'zh'),
      'KO':(r"\Esperanto-Kanji-Ruby-KO",r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv",'ko')}
ESTEM=r"\E_stem.json"
ROOTS=r"\root_list.txt"; FINAL=r"\置換リスト_ルビ.json"
STEM=r"\分解設定.json"; USER=r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"; FMT='HTML格式_Ruby文字_大小调整'
def process(key, write):
    d,csvn,lang=APPS[key]; APPDIR=BASE+d; DATA=APPDIR+r"\app_data"; sp=DATA+STEM
    bak=sp+".bak_preTier19perword"
    if write and os.path.exists(lp(bak)): shutil.copy2(lp(bak),lp(sp))  # 冪等: 先に復元
    with open(lp(sp),encoding='utf-8') as f: settings=json.load(f)
    # 既存の同一nosl「ne」エントリ除去(再適用安全)
    nosl_set={d.replace('/','') for d in PERWORD_DECOMP}
    settings=[e for e in settings if not (isinstance(e,list) and len(e)==3 and str(e[0]).replace('/','') in nosl_set and e[2]==["ne"])]
    settings=settings+ne_entries()
    tmp=DATA+r"\_settings_perword_tmp.json"
    with open(lp(tmp),'w',encoding='utf-8') as g: json.dump(settings,g,ensure_ascii=False)
    with open(lp(OUT+f"\\word_anno_{lang}.json"),encoding='utf-8') as f: wa=json.load(f)
    combined=generate(APPDIR,DATA,DATA+csvn,tmp,DATA+USER,DATA+ESTEM,DATA+ROOTS,FMT,word_anno=wa)
    if write:
        if not os.path.exists(lp(bak)): shutil.copy2(lp(sp),lp(bak))  # 初回のみ pristine保存
        with open(lp(sp),'w',encoding='utf-8') as g: json.dump(settings,g,ensure_ascii=False,indent=1)
        with open(lp(DATA+FINAL),'w',encoding='utf-8') as g: json.dump(combined,g,ensure_ascii=False,indent=2)
        os.remove(lp(tmp)); print(f"  [{key}] per-word ne {len(PERWORD_DECOMP)}件 → ルビJSON書込")
    else:
        os.remove(lp(tmp)); print(f"  [{key}] 生成のみ(未書込)")
    return combined
if WRITE:
    for k in ('JP','ZH','KO'): process(k, True)
    print("3アプリ ルビJSON書込完了。次に apply_kanji.py --write で漢字も再生成。")
else:
    process('JP', False); print("テスト生成OK(未書込)")
