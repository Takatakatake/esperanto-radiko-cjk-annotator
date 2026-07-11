# -*- coding: utf-8 -*-
"""§3.5: 同一注釈テキストで<br>位置が異なる箇所の検出。"""
import os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
CORP = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630\_project_root_misc\京大エス研html文書＿Github"
PFX=chr(92)+chr(92)+chr(63)+chr(92)
def LP(p): return PFX+os.path.abspath(p)
# グロス(br除去形) -> br入り変種のCounter
variants=collections.defaultdict(collections.Counter)
samp={}
for r,_,fs in os.walk(CORP):
    if os.sep+'.git' in r: continue
    for f in fs:
        if not f.endswith('.html'): continue
        h=open(LP(os.path.join(r,f)),encoding='utf-8',errors='ignore').read()
        for m in re.finditer(r'<rt[^>]*>((?:[^<]|<br\s*/?>)*?<br\s*/?>(?:[^<]|<br\s*/?>)*?)</rt>',h):
            g=m.group(1)
            key=re.sub(r'<br\s*/?>','',g).strip()
            norm=re.sub(r'<br\s*/?>','<br>',g).strip()
            variants[key][norm]+=1
            samp.setdefault((key,norm),f[:24])
print("同一グロスで<br>位置が揺れるケース:")
found=0
for key,vc in sorted(variants.items(),key=lambda x:-sum(x[1].values())):
    if len(vc)<2: continue
    found+=1
    vs=' | '.join(f"'{v}'×{c}" for v,c in vc.most_common()[:3])
    print(f"  [{key[:16]:16s}] {vs}"[:130])
    if found>=25: break
print(f"揺れ総数: {sum(1 for k,v in variants.items() if len(v)>=2)}")
# §3.5指名2ケース
for key,target in [('たった今','たった<br>今'),('ある種の','ある<br>種の')]:
    vc=variants.get(key,{})
    print(f"指名ケース '{key}': {dict(vc)} → 統一先 '{target}'")
