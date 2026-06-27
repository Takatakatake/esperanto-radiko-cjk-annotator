# -*- coding: utf-8 -*-
"""HTMLベンチを実行し、不一致を(ref,app)別インスタンス数つきで出力。
   python bench_instances.py <html名>"""
import re, sys, json, html as htmllib, os, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
HTML = sys.argv[1] if len(sys.argv) > 1 else "vere_aux_fantazie.html"
appdir = BASE + r"\Esperanto-Kanji-Converter-and-Ruby-Annotation-Tool"; sys.path.insert(0, appdir)
import esp_text_replacement_module as m
DATA = appdir + r"\Appの运行に使用する各类文件"
dd = json.load(open(lp(DATA + r"\最终的な替换用リスト(列表)(合并3个JSON文件).json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
pl = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
def app_roots(word):
    h = m.orchestrate_comprehensive_esperanto_text_replacement(word, ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
    toks = []; pos = 0
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', h):
        pre = re.sub(r'<[^>]+>', '', h[pos:mm.start()])
        for ch in re.findall(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', pre): toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    tail = re.sub(r'<[^>]+>', '', h[pos:])
    for ch in re.findall(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', tail): toks.append(ch)
    return [norm(t) for t in toks if norm(t)]
t = open(os.path.join(BASE, HTML), encoding="utf-8").read()
t = t[t.find('<body'):] if '<body' in t else t
t = re.sub(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', lambda x: '\x01' + x.group(1) + '\x01', t)
t = re.sub(r'<[^>]+>', ' ', t); t = htmllib.unescape(t)
parts = re.split(r'(\x01.*?\x01)', t); words = []; buf_roots = []; buf_word = ''
for part in parts:
    if part.startswith('\x01') and part.endswith('\x01') and len(part) >= 2:
        r = part[1:-1]; buf_roots.append(norm(r)); buf_word += r
    else:
        seg = ''
        for ch in part:
            if ch.isalpha() or ch in "-'": seg += ch
            else:
                if seg: buf_word += seg; buf_roots.append(('LIT', seg)); seg = ''
                if buf_word.strip(): words.append((buf_word, buf_roots))
                buf_word = ''; buf_roots = []
        if seg: buf_word += seg; buf_roots.append(('LIT', seg))
if buf_word.strip(): words.append((buf_word, buf_roots))
def rp_(br): return [norm(r[1]) if isinstance(r, tuple) else r for r in br if (r[1] if isinstance(r, tuple) else r)]
def cuts(p):
    b = set(); c = 0
    for x in p[:-1]: c += len(x); b.add(c)
    return b
cache = {}
total = match = 0; pair = collections.Counter()
for word, br in words:
    rp = rp_(br)
    if len(rp) < 2: continue
    nz = norm(word)
    if not re.fullmatch(r'[a-zĉĝĥĵŝŭ\-]+', nz): continue
    if nz not in cache: cache[nz] = app_roots(nz)
    ap = cache[nz]
    if ''.join(ap) != nz: continue
    total += 1
    if cuts(rp) == cuts(ap): match += 1
    else: pair[('/'.join(rp), '/'.join(ap))] += 1
print(f"=== {HTML} ===")
print(f"比較可 {total}  一致 {match}  ({match*100//max(total,1)}%)  不一致 {total-match}")
# 構造分類
def classify(r, a):
    rp = [p for p in r.split('/') if p]; ap = [p for p in a.split('/') if p]
    nr, na = len(rp), len(ap)
    if na < nr:
        # 接尾辞+語尾の粒度(ref末尾が ..X/oj or ..X/o で app が末尾結合)
        if rp[-1] in ('o','oj','on','ojn','a','aj','an','ajn','e','j','n') and na == nr-1: return 'B_接尾辞粒度(末尾語尾未分割)'
        if na == 1: return 'A_同綴り保持(全体一体/設計)'
        return 'D_その他過少'
    if na > nr: return 'C_過分解(国際/固有)'
    return 'E_境界位置'
cat = collections.Counter()
catex = collections.defaultdict(list)
for (r, a), c in pair.items():
    k = classify(r, a); cat[k] += c
    if len(catex[k]) < 14: catex[k].append((c, r, a))
print("\n--- カテゴリ別インスタンス数 ---")
for k, v in cat.most_common(): print(f"  {k}: {v}")
for k, _ in cat.most_common():
    print(f"\n[{k}] 代表例(件数つき):")
    for c, r, a in sorted(catex[k], reverse=True): print(f"  x{c:3d}  ref={r:20s} app={a}")
json.dump([[r,a,c] for (r,a),c in pair.most_common()], open(lp(BASE+r"\_analysis_20260625\out\vere_mismatch.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
