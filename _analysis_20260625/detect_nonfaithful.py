# -*- coding: utf-8 -*-
"""
精密な人工グロス検出:
各語根の「非偽分解(合成的)語での日訳」を genuine 意味集合とみなし、
偽分解語で genuine 集合 外 のグロスを取る断片を「語根↔意味 非対応(人工)」候補として抽出。
語根が偽分解語にしか出現しない(genuine集合が空)場合も要レビューとして抽出。
出力: out/nonfaithful_words.json
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

rows=[]  # (head, aligned, is_fake, def)
with open(lp(ANNO), encoding="utf-8") as f:
    for line in f:
        line=line.rstrip('\n')
        if not line or line.startswith('##') or '【日=' not in line: continue
        m=LINE_RE.match(line)
        if not m: continue
        head=m.group(1).strip(); sja=m.group(2); rest=line.split('】',1)[1]
        if '#' in head: continue
        is_fake = any(mk in rest for mk in MARK)
        al=align(head, sja)
        if al is None: continue
        defp = (rest.split(':',1)[1] if ':' in rest else rest).split('##')[0].strip()
        rows.append((head, al, is_fake, defp))

# genuine集合 = 非偽分解語での各語根の日訳
genuine = collections.defaultdict(collections.Counter)
for head, al, is_fake, defp in rows:
    if is_fake: continue
    for wp in al:
        for p,t in wp:
            r=norm(p); tt=t.strip()
            if len(r)>=2 and r not in ENDINGS and tt and not is_latin(tt):
                genuine[r][tt]+=1

# 偽分解語を検査
flagged=[]; seen=set()
for head, al, is_fake, defp in rows:
    if not is_fake: continue
    word=''.join(norm(p) for wp in al for p,_ in wp)
    if word in seen: continue
    bad=[]
    for wp in al:
        for idx,(p,t) in enumerate(wp):
            r=norm(p); tt=t.strip()
            if len(r)<2 or r in ENDINGS or not tt or is_latin(tt): continue
            gset=genuine.get(r)
            if not gset:
                bad.append({'root':r,'gloss':tt,'reason':'genuine集合なし(偽分解専用語根)'})
            elif tt not in gset:
                # genuineに無い → 人工の疑い (ただし頻度1のレアgenuineは許容気味に)
                bad.append({'root':r,'gloss':tt,'reason':f'genuine集合外(genuine例:{list(gset)[:3]})'})
    if bad:
        seen.add(word)
        flagged.append({'word':word,'decomp':'/'.join(norm(p) for wp in al for p,_ in wp),
                        'ja':[[norm(p),t.strip()] for wp in al for p,t in wp],
                        'def':defp[:70],'bad':bad})

with open(lp(OUT + r"\nonfaithful_words.json"), "w", encoding="utf-8") as g:
    json.dump(flagged, g, ensure_ascii=False, indent=1)
print(f"偽分解系語: {len({''.join(norm(p) for wp in al for p,_ in wp) for h,al,f,d in rows if f})}")
print(f"語根↔意味 非対応 候補: {len(flagged)} 語")
# 'genuine集合なし' と 'genuine集合外' の内訳
no_g=sum(1 for x in flagged if all('なし' in b['reason'] for b in x['bad']))
print(f"  全断片がgenuine集合なし(借用専用): {no_g}")
print("\n--- 例(genuine集合外=明確な人工候補) ---")
shown=0
for x in flagged:
    ext=[b for b in x['bad'] if '集合外' in b['reason']]
    if ext and shown<25:
        shown+=1
        bs='; '.join(f"{b['root']}→{b['gloss']}({b['reason'][:24]})" for b in ext)
        print(f"  {x['decomp']:20s} 定義={x['def'][:20]}  | {bs}")
print(f"\n保存: out/nonfaithful_words.json")
