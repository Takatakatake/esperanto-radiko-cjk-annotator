# -*- coding: utf-8 -*-
"""tier18候補の各 target の強制語根が、gold他語を部分文字列で横取りしないか検査。
   forced stem(nosl)が、別の gold語Wの接頭辞で、かつ gold(W)が forced stem で始まらない場合は衝突危険。"""
import json, sys, os, glob
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def _norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
OUT = BASE + r"\_analysis_20260625\out"
GOLD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
if not os.path.exists(GOLD):
    for b in reversed(sorted(glob.glob(os.path.join(os.environ['USERPROFILE'],'Downloads','エスペラント_backup_*')))):
        g=os.path.join(b,'語根分解辞書_WSL','世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt')
        if os.path.exists(g): GOLD=g; break
gold_map={}
with open(GOLD,encoding='utf-8') as f:
    for line in f:
        line=line.rstrip('\n')
        if not line or line.startswith('##') or ':' not in line: continue
        for w in line.split(':')[0].split(' '):
            wc=_norm(w)
            if '#' in wc or not wc: continue
            ps=[p for p in wc.split('/') if p]
            if ps: gold_map.setdefault(''.join(ps), ps)
cands = json.load(open(OUT + r"\confirmed_tier18.json", encoding="utf-8"))
safe=[]; risky=[]
for c in cands:
    pieces=[p for p in c['target'].split('/') if p]
    stem_nosl=''.join(pieces[:-1]) if (len(pieces)>=2 and pieces[-1] in ('o','a','e','i','n')) else ''.join(pieces)
    first=pieces[0]
    # 強制語根候補: stem全体 と 先頭片。これらが他gold語を接頭辞横取りするか
    bad=None
    for probe in {stem_nosl, first}:
        if len(probe)<2: continue
        for w,gp in gold_map.items():
            if w!=stem_nosl and w.startswith(probe) and len(w)>len(probe):
                # gold(W)が probe を1語根の先頭として持たない → 横取り危険
                if gp[0]!=probe and not (''.join(gp).startswith(probe) and gp[0].startswith(probe)):
                    # probe が gold(W) の最初の語根の途中で切れる = 横取り
                    if not w.startswith(stem_nosl) or stem_nosl=='':
                        bad=(probe,w,'/'.join(gp)); break
        if bad: break
    (risky if bad else safe).append((c['w'], c['target'], bad))
print(f"安全 {len(safe)} / 危険 {len(risky)}")
print("\n--- 危険(衝突=除外候補) ---")
for w,t,bad in risky: print(f"  {w:20s} {t:18s} 衝突: {bad[0]}⊂{bad[1]}({bad[2]})")
print("\n--- 安全(残す) ---")
for w,t,_ in safe: print(f"  {w:20s} {t}")
json.dump([{"w":w,"target":t} for w,t,_ in safe], open(OUT+r"\_tier18_safe.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
