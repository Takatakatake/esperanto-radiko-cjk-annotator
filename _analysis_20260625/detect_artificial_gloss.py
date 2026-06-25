# -*- coding: utf-8 -*-
"""
「語根↔注釈が非対応」(全体語を形態素に無理やり割り付けた人工グロス)を検出。
手法: 各語根の文脈別グロスを集計し、ある語でその語根が「その語根の主流グロスと大きく異なる
1文字グロス」を取る場合を人工グロス候補として抽出。マーカー(##偽分解等)別にも集計。
"""
import re, sys, json, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp, hat_to_circumflex, replace_esperanto_chars
ANNO = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416_日中韓注釈版_ドラフト.txt"
LINE_RE = re.compile(r'^(.*?)【日=(.*?)｜中=(.*?)｜韓=(.*?)】')
MARKERS = ['##偽分解(PIV正式分解)','##偽分解','##過細分解','##強語根分解','##エス的分解']
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
def align(head, trans):
    hpw=[hw.split('/') for hw in head.split(' ')]; flat=trans.split('/'); out=[]; fi=0; carry=None
    for wi,hp in enumerate(hpw):
        np=len(hp); tp=[]
        for k in range(np):
            if carry is not None: tp.append(carry); carry=None; continue
            if fi>=len(flat): return None
            pc=flat[fi]; fi+=1
            if k==np-1 and wi<len(hpw)-1 and ' ' in pc:
                e,r=pc.split(' ',1); tp.append(e); carry=r
            else: tp.append(pc)
        if len(tp)!=np: return None
        out.append(list(zip(hp,tp)))
    if fi!=len(flat) or carry is not None: return None
    return out

# 1st pass: 各語根のグロス頻度(日)
root_gloss = collections.defaultdict(collections.Counter)
lines_data = []
with open(lp(ANNO), encoding="utf-8") as f:
    for line in f:
        line=line.rstrip('\n')
        if not line or line.startswith('##') or '【日=' not in line: continue
        m=LINE_RE.match(line)
        if not m: continue
        head=m.group(1).strip(); sja=m.group(2); rest=line.split('】',1)[1] if '】' in line else ''
        if '#' in head: continue
        marks=[mk for mk in MARKERS if mk in rest]
        al=align(head, sja)
        if al is None: continue
        lines_data.append((head, al, marks))
        for wp in al:
            for p,t in wp:
                rp=norm(p)
                if len(rp)>=2: root_gloss[rp][t.strip()] += 1

root_dom = {r: c.most_common(1)[0][0] for r,c in root_gloss.items()}

# 2nd pass: 人工グロス候補 = 語根が「主流と異なる かつ 1文字 かつ そのグロスが稀(<=2回)」
suspect_words = []
mark_counter = collections.Counter()
total_marked = collections.Counter()
for head, al, marks in lines_data:
    for mk in marks: total_marked[mk]+=1
    flagged = []
    for wp in al:
        for p,t in wp:
            rp=norm(p); tt=t.strip()
            if len(rp)<2: continue
            cnt = root_gloss[rp][tt]
            dom = root_dom[rp]
            if tt != dom and len(tt)==1 and cnt<=2 and len(rp)>=2:
                flagged.append((rp,tt,dom))
    if flagged:
        suspect_words.append((head, flagged, marks))
        for mk in (marks or ['(マーカー無)']): mark_counter[mk]+=1

print("="*70)
print("【注釈版マーカー別 総数(整合行のみ)】")
for mk,c in total_marked.most_common(): print(f"  {mk}: {c}")
print(f"\n人工グロス候補(主流と異なる稀な1文字グロスを含む語): {len(suspect_words)}")
print("  マーカー別内訳:")
for mk,c in mark_counter.most_common(): print(f"    {mk}: {c}")
print("\n--- 人工グロス候補の例 ---")
for head, fl, marks in suspect_words[:25]:
    fs=', '.join(f"{r}→{t}(本来:{d})" for r,t,d in fl)
    print(f"  {head}  [{fs}]  {marks}")
