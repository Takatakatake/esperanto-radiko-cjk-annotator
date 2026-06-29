# -*- coding: utf-8 -*-
"""先頭1字孤立 自動補正の効果と回帰をコーパス全体で測定。
   baseline(現状) vs autofix(孤立語のみ autofix_decomp で上書き) を、京大ルビ境界に対し比較。
   報告: 全体一致 前/後、先頭1字孤立 件数 前/後、新規不一致(回帰)の有無。"""
import re, sys, json, html as htmllib, os, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
CORP = BASE + r"\京大エス研html文書＿Github"
if not os.path.isdir(CORP):
    CORP = os.path.normpath(BASE + r"\..\fuyou\_project_root_misc\京大エス研html文書＿Github")
APP = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, APP)
import esp_text_replacement_module as m
import esp_overlay_module as ov
DATA = APP + r"\app_data"
dd = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
FMT = "HTML格式_Ruby文字_大小调整"

def _roots(h):
    toks, pos = [], 0
    for mm in re.finditer(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", h):
        for ch in re.findall(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+", re.sub(r"<[^>]+>", "", h[pos:mm.start()])): toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    for ch in re.findall(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+", re.sub(r"<[^>]+>", "", h[pos:])): toks.append(ch)
    return [norm(t) for t in toks if norm(t)]

def app_batch(words, chunk=2500):
    out = {}
    for s in range(0, len(words), chunk):
        b = words[s:s+chunk]
        h = m.orchestrate_comprehensive_esperanto_text_replacement("\n".join(" "+w+" " for w in b), ps, GL, pl, GG, G2, FMT)
        ls = h.split("\n")
        if len(ls) != len(b):
            for w in b: out[w] = None
            continue
        for w, ln in zip(b, ls): out[w] = _roots(ln)
    return out

def parse_words(t):
    t = t[t.find("<body"):] if "<body" in t else t
    t = re.sub(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", lambda x: "\x01"+x.group(1)+"\x01", t)
    t = re.sub(r"<[^>]+>", " ", t); t = htmllib.unescape(t)
    parts = re.split(r"(\x01.*?\x01)", t); words=[]; br=[]; bw=""
    for part in parts:
        if part.startswith("\x01") and part.endswith("\x01") and len(part)>=2:
            r=part[1:-1]; br.append(norm(r)); bw+=r
        else:
            seg=""
            for ch in part:
                if ch.isalpha() or ch in "-'": seg+=ch
                else:
                    if seg: bw+=seg; br.append(seg); seg=""
                    if bw.strip(): words.append((bw,br))
                    bw=""; br=[]
            if seg: bw+=seg; br.append(seg)
    if bw.strip(): words.append((bw,br))
    return words

def cuts(s):
    pp=[p for p in s.split("/") if p]; b=set(); c=0
    for p in pp[:-1]: c+=len(p); b.add(c)
    return b

# コーパス収集
pair=collections.Counter()
for root,_d,files in os.walk(lp(CORP)):
    for f in files:
        if not f.lower().endswith((".html",".htm")): continue
        try: t=open(os.path.join(root,f),encoding="utf-8",errors="ignore").read()
        except Exception: continue
        for word,brr in parse_words(t):
            rp=[norm(x) for x in brr if norm(x)]
            if len(rp)<2: continue
            nz=norm(word)
            if not re.fullmatch(r"[a-zĉĝĥĵŝŭ\-]+",nz): continue
            pair[(nz,"/".join(rp))]+=1
uniq=sorted({nz for (nz,_) in pair})
print(f"ユニーク語 {len(uniq)} / pair {len(pair)}  baseline分解中...")
base=app_batch(uniq)

# 先頭1字孤立 = baseline分解の先頭片が1文字
def is_strand(ap): return ap is not None and len(ap)>=2 and len(ap[0])==1 and ap[0].lower() not in "aeiou"
stranded=[w for w in uniq if is_strand(base.get(w))]
print(f"baseline 先頭1字孤立語: {len(stranded)} 種")
# autofix 上書き(孤立語のみ)
fix={}
for w in stranded:
    d=ov.autofix_decomp(w, DATA)
    if d and d.replace("/","")==w:
        fix[w]=[p for p in d.split("/") if p]
print(f"autofix で再分解した語: {len(fix)} 種")
still=[w for w in fix if is_strand(fix[w])]
print(f"autofix後も孤立が残る語: {len(still)}  {still[:10]}")

# 境界一致 前/後、回帰チェック(孤立でない語は不変→影響なしを構造的に保証)
def match_count(use_fix):
    tot=mat=fc=0; newmis=[]
    for (nz,refd),c in pair.items():
        ap=base.get(nz)
        if ap is None or "".join(ap)!=nz:
            # baselineが語を完全再構成できない場合のみ fix を試す
            if use_fix and nz in fix and "".join(fix[nz])==nz: ap=fix[nz]
            else: continue
        used = fix[nz] if (use_fix and nz in fix) else ap
        if "".join(used)!=nz: continue
        tot+=c
        if cuts(refd)==cuts("/".join(used)): mat+=c
        else:
            if use_fix and nz in fix: newmis.append((nz,refd,"/".join(used),c))
    return tot,mat,newmis
t0,mb,_=match_count(False)
t1,mf,nm=match_count(True)
print(f"\n=== 境界一致 baseline {mb}/{t0} ({mb*1000//t0/10}%)  ->  autofix {mf}/{t1} ({mf*1000//t1/10}%) ===")
print(f"改善: {mf-mb:+d} トークン")
# 孤立語の不一致が減ったか
print("\n孤立語15種の 前/後 (期待=コーパス):")
arb=json.load(open(lp(BASE+r"\_analysis_20260625\out\_corpus_arbitration.json"),encoding="utf-8"))
for e in sorted(arb.get("NOTINGOLD_先頭1字孤立",[]),key=lambda x:-x["count"])[:15]:
    w=e["word"]; b="/".join(base.get(w,[])); f="/".join(fix.get(w,base.get(w,[])))
    print(f"  {w:13s} base={b:18s} autofix={f:16s} 期待={e['corpus']}")
