# -*- coding: utf-8 -*-
"""
第1回レビュー(genuineセット外1447語)で扱わなかった偽分解語=「全断片がgenuineセット内」
の語を抽出。これらは gloss が genuine だが文脈で誤形態素(manometro→手 型)の潜在リスク。
out/unreviewed_fakedecomp.json に保存し、workflow用にチャンク分割。
"""
import re, sys, json, collections, os
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp, hat_to_circumflex, replace_esperanto_chars
ANNO = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416_日中韓注釈版_ドラフト.txt"
OUT = BASE + r"\_analysis_20260625\out"
LINE_RE = re.compile(r'^(.*?)【日=(.*?)｜中=(.*?)｜韓=(.*?)】:?(.*)$')
ENDINGS = {'o','a','e','i','u','oj','aj','on','an','ojn','ajn','as','is','os','us','n','j'}
MARK = ['偽分解','過細分解','強語根','エス的']
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
def is_latin(t): return bool(re.fullmatch(r'[a-zĉĝĥĵŝŭ!\-]+', t or ''))
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

# 既レビュー語(nonfaithful)
with open(lp(OUT + r"\nonfaithful_words.json"), encoding="utf-8") as f:
    reviewed = {e['word'] for e in json.load(f)}

rows=[]
with open(lp(ANNO), encoding="utf-8") as f:
    for line in f:
        line=line.rstrip('\n')
        if not line or line.startswith('##') or '【日=' not in line: continue
        m=LINE_RE.match(line)
        if not m: continue
        head=m.group(1).strip(); sja=m.group(2); rest=line.split('】',1)[1]
        if '#' in head: continue
        if not any(mk in rest for mk in MARK): continue
        al=align(head, sja)
        if al is None: continue
        defp=(rest.split(':',1)[1] if ':' in rest else rest).split('##')[0].strip()
        rows.append((head, al, defp))

unreviewed=[]; seen=set()
for head, al, defp in rows:
    word=''.join(norm(p) for wp in al for p,_ in wp)
    if word in seen or word in reviewed: continue
    seen.add(word)
    # 訳がある語根片が2つ以上ある語のみ(単一語根のみの語は誤形態素リスクなし)
    pieces=[(norm(p),t.strip()) for wp in al for p,t in wp if len(norm(p))>=2 and norm(p) not in ENDINGS and t.strip() and not is_latin(t.strip())]
    if len(pieces) < 2: continue
    unreviewed.append({'word':word,'decomp':'/'.join(norm(p) for wp in al for p,_ in wp),
                       'ja_pieces':[[norm(p),t.strip()] for wp in al for p,t in wp],'def':defp[:70]})

CH = OUT + r"\unrev_chunks"; os.makedirs(lp(CH), exist_ok=True)
# 既存チャンク掃除
for fn in os.listdir(lp(CH)):
    os.remove(lp(os.path.join(CH, fn)))
SIZE=45; n=0
for i in range(0,len(unreviewed),SIZE):
    with open(lp(CH + f"\\uchunk_{n:03d}.json"),"w",encoding="utf-8") as g:
        json.dump(unreviewed[i:i+SIZE], g, ensure_ascii=False, indent=1)
    n+=1
with open(lp(OUT + r"\unreviewed_fakedecomp.json"),"w",encoding="utf-8") as g:
    json.dump(unreviewed, g, ensure_ascii=False, indent=1)
print(f"偽分解語(整合,ユニーク): {len(seen)}  既レビュー: {len(reviewed & seen)}")
print(f"未レビュー(全断片genuine, 多語根): {len(unreviewed)} → {n}チャンク(各{SIZE})")
