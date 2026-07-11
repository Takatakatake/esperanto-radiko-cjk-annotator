# -*- coding: utf-8 -*-
"""コーパス不一致から「参照が1語根とする語をアプリが過分割」している語根を自動抽出。
   各語根のHTML参照グロス・総出現数を集計し、汎用強制候補リストを作る。"""
import re, sys, json, html as htmllib, os, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
CORP = BASE + r"\京大エス研html文書＿Github"

# 全HTMLから語根キーのグロス収集
gloss = {}
for root, dirs, files in os.walk(lp(CORP)):
    for f in files:
        if not f.lower().endswith(('.html', '.htm')): continue
        try: t = open(os.path.join(root, f), encoding='utf-8', errors='ignore').read()
        except Exception: continue
        for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', t):
            b = norm(mm.group(1)); g = htmllib.unescape(re.sub(r'<[^>]+>', '', mm.group(2)))
            if b and g and b not in gloss: gloss[b] = g

mm = json.load(open(lp(BASE + r"\_analysis_20260625\out\corpus_mismatch_before11.json"), encoding="utf-8"))  # [ref,app,count] tier11適用前
GRAM = {'o','oj','on','ojn','a','aj','an','ajn','e','en','n','j','jn','i','as','is','os','us','u','at','it','ot','int','ant','ont'}

def spans(pieces):
    out = []; c = 0
    for p in pieces:
        out.append((c, c + len(p), p)); c += len(p)
    return out

# 過分割語根 = refの1ピースが、appで複数ピースに割れている
cand = collections.Counter()       # root -> 出現数
cand_ctx = collections.defaultdict(set)
for ref, app, c in mm:
    rp = [p for p in ref.split('/') if p]; ap = [p for p in app.split('/') if p]
    if ''.join(rp) != ''.join(ap): continue
    aset = set()  # app境界位置
    cc = 0
    for p in ap[:-1]: cc += len(p); aset.add(cc)
    for s, e, p in spans(rp):
        if p in GRAM or len(p) < 3: continue       # 文法語尾・短すぎは対象外
        # このref語根の内部(s<pos<e)にapp境界があれば過分割
        if any(s < b < e for b in aset):
            cand[p] += c
            cand_ctx[p].add(f"{ref}|{app}")

# === 多数決: 参照コーパス全体で各候補語根が「1語根扱い」される頻度 vs「分解される」頻度 ===
# 参照(HTML)全体の(語,分解,count)を再集計
def parse_words(t):
    t = t[t.find('<body'):] if '<body' in t else t
    t = re.sub(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', lambda x: '\x01'+x.group(1)+'\x01', t)
    t = re.sub(r'<[^>]+>', ' ', t); t = htmllib.unescape(t)
    out = []; parts = re.split(r'(\x01.*?\x01)', t); br=[]; bw=''
    for part in parts:
        if part.startswith('\x01') and part.endswith('\x01') and len(part)>=2:
            r=part[1:-1]; br.append(norm(r)); bw+=r
        else:
            seg=''
            for ch in part:
                if ch.isalpha() or ch in "-'": seg+=ch
                else:
                    if seg: bw+=seg; br.append(norm(seg)); seg=''
                    if bw.strip(): out.append((bw,br))
                    bw=''; br=[]
            if seg: bw+=seg; br.append(norm(seg))
    if bw.strip(): out.append((bw,br))
    return out
refpairs = collections.Counter()
for root, dirs, files in os.walk(lp(CORP)):
    for f in files:
        if not f.lower().endswith(('.html','.htm')): continue
        try: t=open(os.path.join(root,f),encoding='utf-8',errors='ignore').read()
        except Exception: continue
        for w, br in parse_words(t):
            rp=[norm(x) for x in br if norm(x)]
            if len(rp)<2: continue
            nz=norm(w)
            if not re.fullmatch(r'[a-zĉĝĥĵŝŭ\-]+', nz): continue
            refpairs[(nz,'/'.join(rp))]+=1
# 各候補Pについて atomic(=Pが1ピース) vs split(=P範囲内にref境界) を集計
atomic = collections.Counter(); split = collections.Counter()
CANDS = set(cand)
for (nz, refd), c in refpairs.items():
    rp=[p for p in refd.split('/') if p]
    # atomic: Pがそのままピース
    for p in rp:
        if p in CANDS: atomic[p]+=c
    # split: 各候補Pがnzの部分文字列で、その範囲内にref境界がある
    bset=set(); cc=0
    for p in rp[:-1]: cc+=len(p); bset.add(cc)
    for P in CANDS:
        idx=nz.find(P)
        while idx!=-1:
            s,e=idx,idx+len(P)
            if any(s<b<e for b in bset): split[P]+=c; break
            idx=nz.find(P, idx+1)

rows = []
for r, c in cand.most_common():
    g = gloss.get(norm(r))
    rows.append({'root': r, 'count': c, 'gloss': g, 'atomic': atomic[r], 'split': split[r]})
# 採用条件: グロス有 かつ 参照が多数派で1語根扱い(atomic > split*2 かつ split小)
withg = [x for x in rows if x['gloss']]
keep = [x for x in withg if x['atomic'] >= max(2 * x['split'], x['split'] + 2)]
drop = [x for x in withg if x not in keep]
print(f"過分割語根候補(グロス有) {len(withg)} → 多数決採用 {len(keep)}")
print(f"採用 総出現数: {sum(x['count'] for x in keep)}")
print("\n--- 採用(atomic≫split) 上位45 ---")
for x in sorted(keep, key=lambda y:-y['count'])[:45]:
    print(f"  x{x['count']:4d}  atom{x['atomic']:4d}/spl{x['split']:3d}  {x['root']:15s} = {x['gloss']}")
print("\n--- 除外(参照も分解する=多数派split) 上位20 ---")
for x in sorted(drop, key=lambda y:-y['count'])[:20]:
    print(f"  x{x['count']:4d}  atom{x['atomic']:4d}/spl{x['split']:3d}  {x['root']:15s} = {x['gloss']}")
json.dump(keep, open(lp(BASE + r"\_analysis_20260625\out\oversplit_candidates.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
