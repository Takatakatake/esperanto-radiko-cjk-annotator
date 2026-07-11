# -*- coding: utf-8 -*-
"""ガイド§4(誤分解例)・§6(国名グロス統一)とコーパスの照合。"""
import os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
CORP = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630\_project_root_misc\京大エス研html文書＿Github"
PFX=chr(92)+chr(92)+chr(63)+chr(92)
def LP(p): return PFX+os.path.abspath(p)
RUBY=re.compile(r'<ruby>([^<]+)<rt[^>]*>((?:[^<]|<br\s*/?>)*?)</rt></ruby>')
# 語(連続ruby+裸)を復元
def words(body):
    out=[]; i=0; n=len(body); cur=[]
    def flush():
        nonlocal cur
        if cur and any(g is not None for _,g in cur):
            w=''.join(p for p,_ in cur)
            if re.fullmatch(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ\-']+", w):
                out.append((w, list(cur)))
        cur=[]
    while i<n:
        m=RUBY.match(body,i)
        if m: cur.append((m.group(1), re.sub(r'<br\s*/?>|\s','',m.group(2)))); i=m.end(); continue
        ch=body[i]
        if ch=='<':
            j=body.find('>',i); i=j+1 if j>=0 else n; continue
        if ch.isalpha() or ch in "-'":
            j=i
            while j<n and (body[j].isalpha() or body[j] in "-'"): j+=1
            cur.append((body[i:j],None)); i=j; continue
        flush(); i+=1
    flush()
    return out
# §4: 誤分解パターン(正しくは融合すべき語が2ルビに割れている)
S4_MERGE={'element':'el/ement','interes':'inter/es','princip':'pri/ncip','preciz':'pre/ciz',
 'prezent':'pre/zent','profesi':'pro/fesi','program':'pro/gram','surpriz':'sur/priz',
 'kondiĉ':'kon/diĉ','konstru':'kon/stru','futbal':'fut/bal','kampus':'kamp/us',
 'invest':'in/vest','ident':'i/dent','boreliozo':'borel/iozo','sitelen':'sitel/en'}
# §6: 国名語根(単体は国名、+anで人)
S6_NAT={'angl':'イギリス','franc':'フランス','german':'ドイツ','rus':'ロシア','hebre':'ヘブライ','hispan':'スペイン','pol':'ポーランド'}
s4_hits=collections.Counter(); s4_samp={}
s6_hits=collections.defaultdict(collections.Counter); s6_samp={}
for r,_,fs in os.walk(CORP):
    if os.sep+'.git' in r: continue
    for f in fs:
        if not f.endswith('.html') or f.endswith(('_ZH.html','_KO.html')): continue
        h=open(LP(os.path.join(r,f)),encoding='utf-8',errors='ignore').read()
        body=h[h.find('<body'):] if '<body' in h else h
        for w,cur in words(body):
            rubypcs=[(p,g) for p,g in cur if g is not None]
            rub='/'.join(p.lower() for p,_ in rubypcs)
            # §4: 語幹が誤分解パターンで始まるか
            for stem,bad in S4_MERGE.items():
                if rub==bad or rub.startswith(bad+'/'):
                    s4_hits[stem]+=1; s4_samp.setdefault(stem,(f[:24],w,rub))
            # §6: 国名語根単体(直後がanでない)が「人」グロス
            for i,(p,g) in enumerate(rubypcs):
                pl=p.lower()
                if pl in S6_NAT:
                    nxt=rubypcs[i+1][0].lower() if i+1<len(rubypcs) else ''
                    is_an = nxt.startswith('an')
                    if not is_an and '人' in g:
                        s6_hits[pl][g]+=1; s6_samp.setdefault((pl,g),(f[:24],w))
print("=== §4 誤分解が残存 ===")
if s4_hits:
    for stem,n in s4_hits.most_common():
        f,w,rub=s4_samp[stem]; print(f"  {stem:12s} ×{n} 実={rub} 例={w} [{f}]")
else: print("  なし(全て正しく融合)")
print("\n=== §6 国名語根単体が『人』グロス(anglano等の複合形は除外) ===")
if s6_hits:
    for root,gc in s6_hits.items():
        for g,n in gc.most_common():
            f,w=s6_samp[(root,g)]; print(f"  {root:8s}='{g}' ×{n} 例={w} [{f}] → ガイド='{S6_NAT[root]}'")
else: print("  なし(全て国名グロス)")
