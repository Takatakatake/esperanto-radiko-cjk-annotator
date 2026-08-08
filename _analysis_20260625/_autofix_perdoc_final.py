# -*- coding: utf-8 -*-
"""自動補正(先頭1字孤立)を組み込んだ後の、京大エス研コーパス全文書 最終精度測定。
   baseline(現状の分解) と autofix適用後 を、文書別・全体で京大ルビ境界に対し比較。
   報告: 文書別 前/後 の最低・中央値、全体 前/後、残存する子音始まり孤立の数。"""
import re, sys, json, html as htmllib, os, collections, statistics
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
import esp_text_replacement_module as m, esp_overlay_module as ov
DATA = APP + r"\app_data"
dd = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
FMT = "HTML格式_Ruby文字_大小调整"

def _roots(h):
    t, p = [], 0
    for mm in re.finditer(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", h):
        for ch in re.findall(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+", re.sub(r"<[^>]+>", "", h[p:mm.start()])): t.append(ch)
        t.append(mm.group(1)); p = mm.end()
    for ch in re.findall(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+", re.sub(r"<[^>]+>", "", h[p:])): t.append(ch)
    return [norm(x) for x in t if norm(x)]

def app_batch(ws, chunk=2500):
    o = {}
    for s in range(0, len(ws), chunk):
        b = ws[s:s+chunk]
        h = m.orchestrate_comprehensive_esperanto_text_replacement("\n".join(" "+w+" " for w in b), ps, GL, pl, GG, G2, FMT)
        ls = h.split("\n")
        if len(ls) != len(b):
            for w in b: o[w] = None
            continue
        for w, ln in zip(b, ls): o[w] = _roots(ln)
    return o

def parse_words(t):
    t = t[t.find("<body"):] if "<body" in t else t
    t = re.sub(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", lambda x: "\x01"+x.group(1)+"\x01", t)
    t = re.sub(r"<[^>]+>", " ", t); t = htmllib.unescape(t)
    words, br, bw = [], [], ""
    for part in re.split(r"(\x01.*?\x01)", t):
        if part.startswith("\x01") and part.endswith("\x01") and len(part) >= 2:
            r = part[1:-1]; br.append(norm(r)); bw += r
        else:
            seg = ""
            for ch in part:
                if ch.isalpha() or ch in "-'": seg += ch
                else:
                    if seg: bw += seg; br.append(seg); seg = ""
                    if bw.strip(): words.append((bw, br))
                    bw = ""; br = []
            if seg: bw += seg; br.append(seg)
    if bw.strip(): words.append((bw, br))
    return words

def cuts(s):
    pp = [p for p in s.split("/") if p]; b = set(); c = 0
    for p in pp[:-1]: c += len(p); b.add(c)
    return b

docs = {}
for root, _d, files in os.walk(lp(CORP)):
    for f in files:
        if not f.lower().endswith((".html", ".htm")): continue
        try: t = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
        except Exception: continue
        pc = collections.Counter()
        for word, brr in parse_words(t):
            rp = [norm(x) for x in brr if norm(x)]
            if len(rp) < 2: continue
            nz = norm(word)
            if not re.fullmatch(r"[a-zĉĝĥĵŝŭ\-]+", nz): continue
            pc[(nz, "/".join(rp))] += 1
        if pc: docs[f] = pc
uniq = sorted({nz for pc in docs.values() for (nz, _) in pc})
print(f"ルビ文書 {len(docs)} / ユニーク語 {len(uniq)}  baseline分解中...")
base = app_batch(uniq)

# 自動補正: 子音始まり孤立語のみ再分解で上書き
def strand(ap): return ap and len(ap) >= 2 and len(ap[0]) == 1 and ap[0].lower() not in "aeiou"
fix = {}
for w in uniq:
    if strand(base.get(w)):
        d = ov.autofix_decomp(w, DATA)
        if d and d.replace("/", "") == w:
            fix[w] = [p for p in d.split("/") if p]
def dec(w, use):
    ap = fix[w] if (use and w in fix) else base.get(w)
    return ap
remain = sum(1 for w in uniq if strand(dec(w, True)))
print(f"baseline 子音始まり孤立: {sum(1 for w in uniq if strand(base.get(w)))}種 / autofix再分解 {len(fix)}種 / autofix後残存 {remain}種")

def perdoc(use):
    rows = []; gt = gm = 0
    for name, pc in docs.items():
        tot = mat = 0
        for (nz, refd), c in pc.items():
            ap = dec(nz, use)
            if ap is None or "".join(ap) != nz: continue
            tot += c
            if cuts(refd) == cuts("/".join(ap)): mat += c
        if tot: rows.append(mat*1000//tot/10); gt += tot; gm += mat
    return rows, gm, gt
rb, gmb, gtb = perdoc(False)
rf, gmf, gtf = perdoc(True)
print(f"\n=== 文書別境界一致 ===")
print(f"  baseline: 最低 {min(rb):.1f}% / 中央 {statistics.median(rb):.1f}% / 全{len(rb)}文書")
print(f"  autofix : 最低 {min(rf):.1f}% / 中央 {statistics.median(rf):.1f}% / 全{len(rf)}文書")
print(f"\n=== コーパス全体 ===")
print(f"  baseline {gmb}/{gtb} ({gmb*1000//gtb/10}%)  ->  autofix {gmf}/{gtf} ({gmf*1000//gtf/10}%)  改善 {gmf-gmb:+d}token")
worse = sum(1 for a, b in zip(sorted(rb), sorted(rf)) if b < a)
print(f"  文書別で悪化した文書(ソート比較の粗目安): {worse}")
