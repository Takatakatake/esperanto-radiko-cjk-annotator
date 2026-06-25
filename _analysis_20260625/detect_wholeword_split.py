# -*- coding: utf-8 -*-
"""
人工グロス検出: 「断片グロスの連結 ⊆ 単語全体の定義」のとき、
全体語の訳を形態素に割り付けた人工グロス(語根↔意味が非対応)と判定。
注釈版の各偽分解系行で検査し、該当語リストを out/artificial_split.json に保存。
"""
import re, sys, json, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp, hat_to_circumflex, replace_esperanto_chars
ANNO = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416_日中韓注釈版_ドラフト.txt"
OUT = BASE + r"\_analysis_20260625\out"
LINE_RE = re.compile(r'^(.*?)【日=(.*?)｜中=(.*?)｜韓=(.*?)】:?(.*)$')
ENDINGS = {'o','a','e','i','u','oj','aj','on','an','ojn','ajn','as','is','os','us','n','j'}
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
def align(head, trans):
    hpw=[hw.split('/') for hw in head.split(' ')]; flat=trans.split('/'); out=[]; fi=0; carry=None
    for wi,hp in enumerate(hpw):
        np=len(hp); tp=[]
        for k in range(np):
            if carry is not None: tp.append(carry); carry=None; continue
            if fi>=len(flat): return None
            pc=flat[fi]; fi+=1
            if k==np-1 and wi<len(hpw)-1 and ' ' in pc: e,r=pc.split(' ',1); tp.append(e); carry=r
            else: tp.append(pc)
        if len(tp)!=np: return None
        out.append(list(zip(hp,tp)))
    if fi!=len(flat) or carry is not None: return None
    return out
def clean_def(d):
    d = re.sub(r'【[^】]*】','',d); d = re.sub(r'［[^］]*］','',d); d = re.sub(r'\([^)]*\)','',d)
    d = re.sub(r'（[^）]*）','',d); d = re.sub(r'\{[^}]*\}','',d)
    d = re.sub(r'[>=]+\S+','',d)
    return d

MARK = ['##偽分解(PIV正式分解)','##偽分解','##過細分解','##強語根分解','##エス的分解']
artificial = []
n_fakedecomp = 0
with open(lp(ANNO), encoding="utf-8") as f:
    for line in f:
        line=line.rstrip('\n')
        if not line or line.startswith('##') or '【日=' not in line: continue
        m=LINE_RE.match(line)
        if not m: continue
        head=m.group(1).strip(); sja=m.group(2); rest=line.split('】',1)[1]
        marks=[mk for mk in MARK if mk in rest]
        if '#' in head: continue
        is_fake = any('偽分解' in mk or '過細' in mk or '強語根' in mk or 'エス的' in mk for mk in marks)
        if not is_fake: continue
        n_fakedecomp += 1
        al = align(head, sja)
        if al is None: continue
        # definition部(:より後, マーカー前)
        defpart = rest.split(':',1)[1] if ':' in rest else rest
        defpart = defpart.split('##')[0]
        cdef = clean_def(defpart)
        # 各語(複合句は語ごと)で検査
        for wp in al:
            glosses = [t.strip() for p,t in wp if len(norm(p))>=2 and norm(p) not in ENDINGS and t.strip() and not re.fullmatch(r'[a-zĉĝĥĵŝŭ!\-]+', t.strip())]
            if len(glosses) < 2: continue
            concat = ''.join(glosses)
            # 連結が定義の連続部分(各断片1-2文字中心)なら人工割り付けの疑い
            short = all(len(g) <= 2 for g in glosses)
            if concat and concat in cdef.replace(' ','') and short:
                word = ''.join(norm(p) for p,_ in wp)
                decomp = '/'.join(norm(p) for p,_ in wp)
                artificial.append({'word':word,'decomp':decomp,
                    'glosses':[[norm(p),t.strip()] for p,t in wp],
                    'def':defpart.strip()[:60],'marks':marks})
                break

# 語単位で重複除去
seen=set(); uniq=[]
for a in artificial:
    if a['word'] in seen: continue
    seen.add(a['word']); uniq.append(a)
with open(lp(OUT + r"\artificial_split.json"), "w", encoding="utf-8") as g:
    json.dump(uniq, g, ensure_ascii=False, indent=1)
print(f"偽分解系行(整合): {n_fakedecomp}")
print(f"人工グロス(連結⊆定義 かつ 各片≤2字)検出: {len(uniq)} 語")
print("\n--- 例 ---")
for a in uniq[:30]:
    gs='/'.join(t for _,t in a['glosses'])
    print(f"  {a['decomp']:22s} 日={gs:14s} 定義={a['def'][:24]}  {a['marks']}")
print(f"\n保存: out/artificial_split.json ({len(uniq)}語)")
