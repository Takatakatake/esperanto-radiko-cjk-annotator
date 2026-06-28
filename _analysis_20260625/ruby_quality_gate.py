# -*- coding: utf-8 -*-
"""
ルビ表示品質ゲート: デプロイ済みJSONの全ルビについて
 (1) class が ratio(=rt幅/rb幅) から算出される期待classと一致するか
 (2) <br>数 ↔ class 整合 (XXXS_S=2, XXS_S=1, 他=0) — 1行注釈にXXXS_S等だとルビ浮き
を検証。違反を報告(必要なら--fixで再算出)。生成パイプラインの事後検証ゲート。
  python ruby_quality_gate.py <JP|ZH|KO>
"""
import json, sys, re
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
APPS = {'JP':r"\Esperanto-Kanji-Ruby-JA",
        'ZH':r"\Esperanto-Kanji-Ruby-ZH",
        'KO':r"\Esperanto-Kanji-Ruby-KO"}
key = sys.argv[1] if len(sys.argv)>1 else 'JP'
APPDIR = BASE + APPS[key]; DATA = APPDIR + r"\app_data"
with open(lp(DATA + r"\Unicode_BMP全范围文字幅(宽)_Arial16.json"), encoding='utf-8') as f:
    CW = json.load(f)
def width(t): return sum(CW.get(c,8) for c in t)
def expected_class(rb, rt_nobr):
    wr, wm = width(rt_nobr), width(rb)
    if wm == 0: return None
    r = wr/wm
    if r>6: return 'XXXS_S'
    if r>9/3: return 'XXS_S'
    if r>9/4: return 'XS_S'
    if r>9/5: return 'S_S'
    if r>9/6: return 'M_M'
    if r>9/7: return 'L_L'
    if r>9/8: return 'XL_L'
    return 'XXL_L'
BROK = {'XXXS_S':2,'XXS_S':1}  # それ以外は0
RUBY = re.compile(r'<ruby>(.*?)<rt class="([^"]*)">(.*?)</rt></ruby>')
with open(lp(DATA + r"\置換リスト_ルビ.json"), encoding='utf-8') as f:
    data = json.load(f)
g = data["全域替换用のリスト(列表)型配列(replacements_final_list)"]
total=0; cls_bad=0; br_bad=0; ex_cls=[]; ex_br=[]
for entry in g:
    new = entry[1]
    for m in RUBY.finditer(new):
        rb, cls, rt = m.group(1), m.group(2), m.group(3)
        if '<' in rb: continue  # ネスト等はskip
        if rb != rb.lower(): continue  # 大文字/文頭大文字variantは基本形のclassを継承する設計のためskip
        total += 1
        rt_nobr = rt.replace('<br>','')
        exp = expected_class(rb, rt_nobr)
        if exp and cls != exp:
            cls_bad += 1
            if len(ex_cls)<8: ex_cls.append((rb,rt_nobr[:10],cls,exp))
        nbr = rt.count('<br>')
        want = BROK.get(cls, 0)
        if nbr != want:
            br_bad += 1
            if len(ex_br)<8: ex_br.append((rb,cls,nbr,want))
print(f"[{key}] ルビ総数 {total}")
print(f"  class↔ratio 不一致: {cls_bad} ({cls_bad/max(total,1)*100:.3f}%)")
for rb,rt,c,e in ex_cls: print(f"    rb={rb} rt={rt} class={c} 期待={e}")
print(f"  <br>↔class 不一致: {br_bad} ({br_bad/max(total,1)*100:.3f}%)")
for rb,c,n,w in ex_br: print(f"    rb={rb} class={c} br={n} 期待={w}")
print("  → 0%なら生成パイプライン(output_format)がルビサイズを正しく付与している証左")
