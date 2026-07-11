# -*- coding: utf-8 -*-
"""
false-friend sweep workflow(w4yb7v993)の結果を word_anno_{ja,zh,ko}.json に適用。
fix: 文脈で誤形態素だったグロスを語根忠実値へ。whole_word: 全体1ルビ。uncertain: 列挙のみ。
"""
import json, sys, re, shutil
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp
OUT = BASE + r"\_analysis_20260625\out"
WF_OUT = r"C:\Users\yt\AppData\Local\Temp\claude\d--GoogleDrive202510--------20----------------------------20260624\46f52639-acfa-48a8-8c2f-e95e8e59b22d\tasks\w4yb7v993.output"
ENDINGS = ['oj','aj','ojn','ajn','as','is','os','us','on','an','o','a','e','i','u','j','n']

with open(lp(WF_OUT), encoding="utf-8") as f:
    obj = json.loads(f.read())
res = obj.get('result', obj)
fixes = res.get('fixes', []); wholes = res.get('wholes', []); uncertain = res.get('uncertain', [])
print(f"sweep結果: fix={len(fixes)} whole={len(wholes)} uncertain={len(uncertain)}")

with open(lp(OUT + r"\unreviewed_fakedecomp.json"), encoding="utf-8") as f:
    word2decomp = {e['word']: e['decomp'] for e in json.load(f)}

anno = {}
for L in ('ja','zh','ko'):
    with open(lp(OUT + f"\\word_anno_{L}.json"), encoding="utf-8") as f:
        anno[L] = json.load(f)
nosl2key = {k.replace('/',''): k for k in anno['ja'].keys()}

def find_key(word):
    d = word2decomp.get(word)
    if d:
        k = '/'.join(d.split('/')[:-1])
        if k in anno['ja']: return k
    if word in nosl2key: return nosl2key[word]
    for e in ENDINGS:
        if word.endswith(e) and word[:-len(e)] in nosl2key: return nosl2key[word[:-len(e)]]
    return None

def apply_pieces(key, fmap):
    ch=False
    for L in ('ja','zh','ko'):
        cur=anno[L].get(key)
        if not cur: continue
        nv=[]
        for p,g in cur:
            if p in fmap and fmap[p].get(L): nv.append([p,fmap[p][L]]); ch=True
            else: nv.append([p,g])
        anno[L][key]=nv
    return ch

applied=0; compound=0; skipped=[]
for fx in fixes:
    fp=fx.get('fixed_pieces') or []
    if not fp: continue
    fmap={p['root']:p for p in fp if p.get('root')}
    key=find_key(fx['word'])
    if key and apply_pieces(key,fmap): applied+=1
    else:
        hit=False
        for k in list(anno['ja'].keys()):
            kn=k.replace('/','')
            if kn and kn in fx['word']:
                if any(p in fmap for p in k.split('/') if len(p)>=2):
                    if apply_pieces(k,fmap): hit=True
        if hit: compound+=1
        else: skipped.append(fx['word'])

wapplied=0
for wh in wholes:
    w=wh.get('whole') or {}; key=find_key(wh['word'])
    if not key: skipped.append(wh['word']+'(whole)'); continue
    sn=key.replace('/','')
    for L in ('ja','zh','ko'):
        if w.get(L): anno[L][key]=[[sn,w[L]]]
    wapplied+=1

for L in ('ja','zh','ko'):
    src=OUT+f"\\word_anno_{L}.json"
    shutil.copy2(lp(src), lp(src+".bak_preSweep"))
    with open(lp(src),"w",encoding="utf-8") as g: json.dump(anno[L],g,ensure_ascii=False)

print(f"適用: 単語fix={applied} 複合fix={compound} whole={wapplied}")
print(f"未マップ {len(skipped)}: {skipped[:20]}")
print(f"uncertain {len(uncertain)}: {uncertain[:30]}")
for k in ['man/o/metr','log','gen']:
    if k in anno['ja']: print(f"  確認 {k} → {anno['ja'][k]}")
