# -*- coding: utf-8 -*-
"""マスター語根分解辞書(gold学習者版 全44100語)とアプリ分解の境界一致を測定。
   コーパスHTMLは部分集合。goldが分解の正本=これと一致しているかが本質。"""
import re, sys, json, os, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
GOLD = r"C:\Users\yt\Downloads\エスペラント_backup_20260627\語根分解辞書_WSL\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
appdir = BASE + r"\Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool"; sys.path.insert(0, appdir)
import esp_text_replacement_module as m
DATA = appdir + r"\Appの运行に使用する各类文件"
dd = json.load(open(lp(DATA + r"\最终的な替换用リスト(列表)(合并3个JSON文件).json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
pl = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
def _roots_from_html(h):
    toks = []; pos = 0
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', h):
        for ch in re.findall(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', re.sub(r'<[^>]+>', '', h[pos:mm.start()])): toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    for ch in re.findall(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', re.sub(r'<[^>]+>', '', h[pos:])): toks.append(ch)
    return [norm(t) for t in toks if norm(t)]
def app_batch(words, chunk=2500):
    out = {}
    for s in range(0, len(words), chunk):
        b = words[s:s+chunk]
        h = m.orchestrate_comprehensive_esperanto_text_replacement("\n".join(" "+w+" " for w in b), ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
        ls = h.split("\n")
        if len(ls) != len(b):
            for w in b: out[w] = None
            continue
        for w, ln in zip(b, ls): out[w] = _roots_from_html(ln)
    return out
# gold パース: 'decomp:gloss' 行、単一語(空白なし)のみ、2片以上
pairs = {}
with open(lp(GOLD), encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")
        if ":" not in line: continue
        decomp = line.split(":", 1)[0].strip()
        if not decomp or decomp.startswith("-") or decomp.endswith("-"): continue   # 接辞見出し
        if " " in decomp: continue                                                   # 複合句
        pieces = [p for p in decomp.split("/") if p]
        if len(pieces) < 2: continue
        nz = norm("".join(pieces))
        if not re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", nz): continue
        pairs.setdefault(nz, "/".join(norm(p) for p in pieces))
print(f"gold 分解語(2片以上, 単一語) {len(pairs)}")
def cuts(s):
    b = set(); c = 0
    for p in [x for x in s.split("/") if x][:-1]: c += len(p); b.add(c)
    return b
uniq = sorted(pairs)
print("バッチorchestrate中...")
appres = app_batch(uniq)
total = match = 0; mis = []
for nz, refd in pairs.items():
    ap = appres.get(nz)
    if ap is None or "".join(ap) != nz: continue
    total += 1
    if cuts(refd) == cuts("/".join(ap)): match += 1
    else: mis.append((refd, "/".join(ap)))
print(f"\n=== gold全体 境界一致 {match}/{total} ({match*1000//max(total,1)/10}%)  不一致 {total-match} ===")
# パターン分類
GR = {'o','oj','on','ojn','a','aj','an','ajn','e','en','n','j','jn','i','as','is','os','us','u'}
def cls(r,a):
    rp=[p for p in r.split('/') if p]; ap=[p for p in a.split('/') if p]
    if len(ap)<len(rp): return 'B_接尾辞/語尾融合' if (len(rp)-len(ap)==1 and rp[-1] in GR) else ('A_全体一体' if len(ap)==1 else 'D_過少')
    if len(ap)>len(rp): return 'C_過分解'
    return 'E_境界位置'
cat=collections.Counter([cls(r,a) for r,a in mis])
print("不一致パターン:", dict(cat.most_common()))
mc=collections.Counter(mis)
print("\n最頻不一致 上位30:")
for (r,a),c in mc.most_common(30): print(f"  x{c} ref={r:24s} app={a}")
json.dump([[r,a] for r,a in mis], open(lp(BASE+r"\_analysis_20260625\out\gold_mismatch.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
