# -*- coding: utf-8 -*-
"""
漢字注入_学習者版(参照2)から、漢字化モード用の
  - word_kanji.json   : E_stem語形 -> [(語根, 漢字)]  (per-word, 識別子付き)
  - kanji_root.csv     : 語根 -> 最頻漢字  (per-root フォールバック)
を構築。形式: head/with/slashes⟦漢字/語尾⟧:def
"""
import re, sys, json, collections, csv
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp, hat_to_circumflex, replace_esperanto_chars
INJ = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\漢字注入_学習者版_20260620.txt"
OUT = BASE + r"\_analysis_20260625\out"
LINE_RE = re.compile(r'^(.*?)⟦(.*?)⟧')
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
def align(head, kanji):
    hpw=[hw.split('/') for hw in head.split(' ')]; flat=kanji.split('/'); out=[]; fi=0; carry=None
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

word_kanji={}; root_kanji=collections.defaultdict(collections.Counter)
n=0; ok=0
with open(lp(INJ), encoding="utf-8") as f:
    for line in f:
        line=line.rstrip('\n')
        if not line or line.startswith('##') or '⟦' not in line: continue
        m=LINE_RE.match(line)
        if not m: continue
        head=m.group(1).strip(); kanji=m.group(2)
        if '#' in head: continue
        n+=1
        al=align(head, kanji)
        if al is None: continue
        ok+=1
        for word_pairs in al:
            if len(word_pairs)<2: continue
            pieces_norm=[norm(p) for p,_ in word_pairs]
            key='/'.join(pieces_norm[:-1])
            if not key or '#' in key: continue
            val=[[norm(p), kj.strip()] for (p,kj) in word_pairs[:-1]]
            if key not in word_kanji:
                word_kanji[key]=val
            for (p,kj) in word_pairs[:-1]:
                r=norm(p); kj=kj.strip()
                # 語尾/ラテン片(o,a,i等)はskip。漢字片のみ
                if len(r)>=2 and kj and not re.fullmatch(r'[a-zĉĝĥĵŝŭ!\-]+', kj):
                    root_kanji[r][kj]+=1

with open(lp(OUT+r"\word_kanji.json"),"w",encoding="utf-8") as g:
    json.dump(word_kanji,g,ensure_ascii=False)
# per-root CSV(最頻漢字)
hdr="###エスペラント語根→漢字(参照2 漢字注入版由来 最頻)\n世界语单词##,候选汉字##\n"
with open(lp(OUT+r"\kanji_root.csv"),"w",encoding="utf-8",newline="") as g:
    g.write(hdr)
    w=csv.writer(g)
    for r,cnt in sorted(root_kanji.items()):
        w.writerow([r, cnt.most_common(1)[0][0]])
print(f"漢字注入版 行{n} 整合{ok}  word_kanji語形{len(word_kanji)}  per-root漢字{len(root_kanji)}")
# サンプル
for k in ['abel/ej','abel/kultur','akv/o/kultur','elektr/on','mon','an/estez']:
    print(f"  {k} -> {word_kanji.get(k)}")
