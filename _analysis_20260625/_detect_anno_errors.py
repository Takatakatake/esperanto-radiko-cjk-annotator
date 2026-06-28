# -*- coding: utf-8 -*-
"""注釈版ドラフト(参照1)の同綴り誤訳を機械検出。
   ある語根Rの日訳が圧倒的に1つに支配される(>=90%)のに、少数の語で別訳を使っている場合、
   その少数語は誤訳の可能性が高い(fer=鉄が支配的なのに fervoja で fer=休日 等)。
   app は無改変。参照1で人手修正いただくためのレポート。"""
import re, sys, json, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
ANNO = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416_日中韓注釈版_ドラフト.txt"
LINE_RE = re.compile(r'^(.*?)【日=(.*?)｜中=(.*?)｜韓=(.*?)】(.*)$')
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
# 1) 語根→日訳 頻度 と 各(語根,訳)→使用語例
root_gloss = collections.defaultdict(collections.Counter)
occ = collections.defaultdict(list)
rows = []
with open(ANNO, encoding="utf-8") as f:
    for line in f:
        line=line.rstrip('\n')
        m=LINE_RE.match(line)
        if not m: continue
        head=m.group(1).strip(); ja=m.group(2); dfn=m.group(5).lstrip(':').strip()
        if '#' in head: continue
        al=align(head, ja)
        if al is None: continue
        for wp in al:
            word=''.join(p for p,_ in wp)
            for p,t in wp:
                pr=norm(p); t=t.strip()
                if len(pr)>=2 and t and not re.fullmatch(r'[a-zĉĝĥĵŝŭ!\-]+', t):
                    root_gloss[pr][t]+=1
                    occ[(pr,t)].append((word,dfn))
# 2) 支配的訳>=90% かつ 少数異訳(<=3語)を誤訳候補として抽出
flags=[]
for r,ctr in root_gloss.items():
    tot=sum(ctr.values())
    if tot<8: continue
    dom,domn=ctr.most_common(1)[0]
    if domn/tot < 0.9: continue
    for t,n in ctr.items():
        if t==dom or n>3: continue
        for word,dfn in occ[(r,t)][:2]:
            flags.append((r,dom,domn,t,word,dfn))
print(f"同綴り誤訳候補(支配訳>=90%の語根で少数異訳) {len(flags)}件")
print(f"{'語根':8s} {'支配訳':10s} {'誤訳?':8s} {'使用語':16s} 定義")
for r,dom,domn,t,word,dfn in sorted(flags)[:60]:
    print(f"  {r:8s} {dom:9s}({domn:4d}) ≠{t:8s} {word:16s} {dfn[:30]}")
json.dump([{"root":r,"dominant":dom,"wrong":t,"word":word,"def":dfn} for r,dom,domn,t,word,dfn in flags],
          open(BASE+r"\_analysis_20260625\out\_anno_master_errors.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n保存: out/_anno_master_errors.json (参照1修正用)")
