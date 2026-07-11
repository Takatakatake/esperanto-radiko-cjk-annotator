# -*- coding: utf-8 -*-
"""京大エス研HTMLコーパス全文書(171ファイル)の語根分解精度を【デプロイ実機=autofix込み】で総点検。
   - baseline(GG貪欲) と autofix(先頭1字孤立 自動補正=実機の挙動) の両方を測る
   - 全文書の境界一致率を表に(下位/分布/中央値)、out/_audit_perdoc.json に全件
   - 不一致を gold(参照1学習者版) で裁定し、
       (1) コーパス自身の分解誤り(app正・gold一致)  -> out/_audit_corpus_errors.json
       (2) 真のapp欠陥(gold=コーパス, app誤り)        -> out/_audit_app_errors.json
       (3) 構造的天井(国名-i/o 等) / 同綴りホモグラフ / 裁定不能 -> out/_audit_ceiling.json
   を人間可読のカタログとして出力する。
   python _corpus_full_audit.py
"""
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

# ---- gold(学習者版) word -> decomposition ----
GOLD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
gold_decomp = {}
with open(lp(GOLD), encoding="utf-8") as f:
    for line in f:
        if ":" not in line: continue
        d = line.split(":", 1)[0].strip()
        if " " in d or d.startswith("-") or d.endswith("-") or not d: continue
        w = norm("".join(p for p in d.split("/") if p))
        if re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", w):
            gold_decomp.setdefault(w, "/".join(p for p in norm(d).split("/") if p))
print(f"gold(学習者版) 収録 {len(gold_decomp)} 語")

def cuts(s):
    pp = [p for p in s.split("/") if p]; b = set(); c = 0
    for p in pp[:-1]: c += len(p); b.add(c)
    return b

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
    t = re.sub(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", lambda x: "\x01" + x.group(1) + "\x01", t)
    t = re.sub(r"<[^>]+>", " ", t); t = htmllib.unescape(t)
    parts = re.split(r"(\x01.*?\x01)", t); words = []; br = []; bw = ""
    for part in parts:
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

# ---- 全文書を走査 ----
docs = {}   # docname -> Counter((word, ref))
nfiles = 0
for root, _dirs, files in os.walk(lp(CORP)):
    for f in files:
        if not f.lower().endswith((".html", ".htm")): continue
        nfiles += 1
        try: t = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
        except Exception: continue
        pc = collections.Counter()
        for word, br in parse_words(t):
            rp = [norm(x) for x in br if norm(x)]
            if len(rp) < 2: continue
            nz = norm(word)
            if not re.fullmatch(r"[a-zĉĝĥĵŝŭ\-]+", nz): continue
            pc[(nz, "/".join(rp))] += 1
        if pc: docs[f] = pc
print(f"走査ファイル {nfiles} / ルビ付き文書 {len(docs)}")

uniq = sorted({nz for pc in docs.values() for (nz, _) in pc})
print(f"ユニーク多片語 {len(uniq)} を baseline 分解中...")
base = app_batch(uniq)

# ---- autofix(実機挙動): 先頭が子音1字の孤立語のみ再分解 ----
def is_strand(ap): return ap is not None and len(ap) >= 2 and len(ap[0]) == 1 and ap[0].lower() not in "aeiou"
stranded = [w for w in uniq if is_strand(base.get(w))]
fix = {}
for w in stranded:
    d = ov.autofix_decomp(w, DATA)
    if d and d.replace("/", "") == w:
        fix[w] = [p for p in d.split("/") if p]
print(f"先頭子音1字孤立 {len(stranded)} 種 → autofix再分解 {len(fix)} 種")

def app_decomp(nz, use_fix):
    """実機の最終分解(autofix適用後)。完全再構成できなければ None。"""
    ap = base.get(nz)
    if use_fix and nz in fix and "".join(fix[nz]) == nz:
        ap = fix[nz]
    if ap is None or "".join(ap) != nz: return None
    return "/".join(ap)

# ---- 文書別精度(baseline & autofix) ----
def perdoc(use_fix):
    rows = []; gt = gm = 0; agg = collections.Counter()
    for name, pc in docs.items():
        total = match = 0
        for (nz, refd), c in pc.items():
            ad = app_decomp(nz, use_fix)
            if ad is None: continue
            total += c
            if cuts(refd) == cuts(ad): match += c
            else: agg[(nz, refd, ad)] += c
        if total:
            rows.append((name, total, match, round(match*100/total, 2)))
            gt += total; gm += match
    rows.sort(key=lambda r: r[3])
    return rows, gt, gm, agg

rows_b, gt_b, gm_b, _ = perdoc(False)
rows, gt, gm, agg_mis = perdoc(True)

print(f"\n=== コーパス全体 境界一致 ===")
print(f"  baseline : {gm_b}/{gt_b}  ({round(gm_b*100/gt_b,3)}%)  不一致 {gt_b-gm_b}")
print(f"  autofix  : {gm}/{gt}  ({round(gm*100/gt,3)}%)  不一致 {gt-gm}   (実機=デプロイ状態)")
pcts = sorted(r[3] for r in rows)
print(f"\n=== 文書別(全{len(rows)}文書, autofix) ===")
print(f"  最小 {pcts[0]}% / 中央 {statistics.median(pcts)}% / 平均 {round(statistics.mean(pcts),2)}% / 最大 {pcts[-1]}%")
buckets_pct = collections.Counter()
for p in pcts:
    if p == 100: buckets_pct["100%"] += 1
    elif p >= 99.5: buckets_pct["99.5-99.99%"] += 1
    elif p >= 99: buckets_pct["99.0-99.49%"] += 1
    elif p >= 98: buckets_pct["98.0-98.99%"] += 1
    else: buckets_pct["<98%"] += 1
for k in ["100%", "99.5-99.99%", "99.0-99.49%", "98.0-98.99%", "<98%"]:
    if buckets_pct[k]: print(f"    {k:14s}: {buckets_pct[k]} 文書")
print(f"\n  下位12文書:")
for name, total, match, pct in rows[:12]:
    print(f"    {pct:6.2f}%  {match:5d}/{total:<5d}  {name[:58]}")

# ---- 不一致を gold で裁定 ----
def first_char_isolated(app):
    pp = [p for p in app.split("/") if p]
    return len(pp) >= 2 and len(pp[0]) == 1 and pp[0].lower() not in "aeiou"
def country_io(word, refd, appd):
    # 国名 -i/o 構造天井: gold/corpus = ROOT/i/o, app = ROOT/io
    return ("/i/o" in "/"+refd or refd.endswith("/i/o")) and "io" in appd

buckets = collections.defaultdict(list)
tally = collections.Counter()
for (word, refd, appd), c in agg_mis.items():
    g = gold_decomp.get(word)
    ca, cr = cuts(appd), cuts(refd)
    if g is None:
        cat = "天井_先頭1字孤立(残)" if first_char_isolated(appd) else (
              "裁定不能_NOTINGOLD_app粗" if len(ca) < len(cr) else "裁定不能_NOTINGOLD_app細")
    else:
        cg = cuts(g)
        if cg == ca and cg != cr:
            cat = "コーパス誤り_app正(gold一致)"
        elif cg == cr and cg != ca:
            cat = "天井_国名-i/o" if country_io(word, refd, appd) else "app誤り_真欠陥(gold=コーパス)"
        elif cg == ca and cg == cr:
            cat = "謎(gold=両方)"
        else:
            cat = "gold第三分解_app寄り" if (len(cg ^ ca) <= len(cg ^ cr)) else "gold第三分解_コーパス寄り"
    tally[cat] += c
    buckets[cat].append({"word": word, "corpus": refd, "app": appd, "gold": g, "count": c})

print(f"\n=== 不一致 {gt-gm} の gold 裁定(インスタンス数 / ユニーク語数) ===")
for cat, n in tally.most_common():
    print(f"  {n:5d} inst / {len(buckets[cat]):4d} 語   {cat}")

print("\n--- 主要バケットの例(出現数上位8) ---")
for cat in ["コーパス誤り_app正(gold一致)", "app誤り_真欠陥(gold=コーパス)", "天井_国名-i/o", "天井_先頭1字孤立(残)"]:
    if cat not in buckets: continue
    print(f"\n[{cat}]  計{tally[cat]}inst / {len(buckets[cat])}語")
    for e in sorted(buckets[cat], key=lambda x: -x["count"])[:8]:
        print(f"   x{e['count']:<3d} {e['word']:18s} corpus={e['corpus']:22s} app={e['app']:22s} gold={e['gold']}")

# ---- 出力 ----
OUT = BASE + r"\_analysis_20260625\out"
def dump(name, lst): json.dump(sorted(lst, key=lambda x: -x["count"]), open(lp(OUT+name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
dump(r"\_audit_corpus_errors.json", buckets.get("コーパス誤り_app正(gold一致)", []))
dump(r"\_audit_app_errors.json", buckets.get("app誤り_真欠陥(gold=コーパス)", []))
ceil = buckets.get("天井_国名-i/o", []) + buckets.get("天井_先頭1字孤立(残)", []) \
     + buckets.get("gold第三分解_コーパス寄り", []) + buckets.get("gold第三分解_app寄り", [])
dump(r"\_audit_ceiling.json", ceil)
dump(r"\_audit_notingold_appfine.json", buckets.get("裁定不能_NOTINGOLD_app細", []))
dump(r"\_audit_notingold_appcoarse.json", buckets.get("裁定不能_NOTINGOLD_app粗", []))
json.dump([{"name": n, "total": t, "match": mt, "pct": p} for n, t, mt, p in rows],
          open(lp(OUT + r"\_audit_perdoc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"files": nfiles, "docs": len(docs), "tokens": gt, "match_autofix": gm,
           "pct_autofix": round(gm*100/gt, 3), "match_baseline": gm_b, "pct_baseline": round(gm_b*100/gt_b, 3),
           "tally": dict(tally)}, open(lp(OUT + r"\_audit_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n保存: out/_audit_{{summary,perdoc,corpus_errors,app_errors,ceiling}}.json")
