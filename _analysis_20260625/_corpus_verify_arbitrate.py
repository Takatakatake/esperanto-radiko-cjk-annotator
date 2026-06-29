# -*- coding: utf-8 -*-
"""京大エス研HTMLコーパス全文書(171ファイル)の語根分解を検証し、不一致を gold(参照1学習者版)を
   裁定者として【アプリ誤り / コーパス誤り / 設計上正しい同綴り / 構造的天井 / 裁定不能】に切り分ける。
   出力: 文書別精度 + 裁定バケット(件数・例) + out/ へバケットJSON(workflow敵対検証用)。"""
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
appdir = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, appdir)
import esp_text_replacement_module as m
DATA = appdir + r"\app_data"
dd = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))

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

def _roots_from_html(h):
    toks, pos = [], 0
    for mm in re.finditer(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", h):
        for ch in re.findall(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+", re.sub(r"<[^>]+>", "", h[pos:mm.start()])): toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    for ch in re.findall(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+", re.sub(r"<[^>]+>", "", h[pos:])): toks.append(ch)
    return [norm(t) for t in toks if norm(t)]

def app_roots_batch(words, chunk=2500):
    out = {}
    for s in range(0, len(words), chunk):
        batch = words[s:s+chunk]
        h = m.orchestrate_comprehensive_esperanto_text_replacement("\n".join(" "+w+" " for w in batch), ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
        lines = h.split("\n")
        if len(lines) != len(batch):
            for w in batch: out[w] = None
            continue
        for w, ln in zip(batch, lines): out[w] = _roots_from_html(ln)
    return out

def parse_words(t):
    t = t[t.find("<body"):] if "<body" in t else t
    t = re.sub(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", lambda x: "\x01" + x.group(1) + "\x01", t)
    t = re.sub(r"<[^>]+>", " ", t); t = htmllib.unescape(t)
    parts = re.split(r"(\x01.*?\x01)", t); words = []; buf_roots = []; buf_word = ""
    for part in parts:
        if part.startswith("\x01") and part.endswith("\x01") and len(part) >= 2:
            r = part[1:-1]; buf_roots.append(norm(r)); buf_word += r
        else:
            seg = ""
            for ch in part:
                if ch.isalpha() or ch in "-'": seg += ch
                else:
                    if seg: buf_word += seg; buf_roots.append(seg); seg = ""
                    if buf_word.strip(): words.append((buf_word, buf_roots))
                    buf_word = ""; buf_roots = []
            if seg: buf_word += seg; buf_roots.append(seg)
    if buf_word.strip(): words.append((buf_word, buf_roots))
    return words

# ---- 全文書を走査: 文書別ペア + 集計 ----
docs = {}   # docname -> Counter((word, ref))
for root, _dirs, files in os.walk(lp(CORP)):
    for f in files:
        if not f.lower().endswith((".html", ".htm")): continue
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
print(f"ルビ付き文書 {len(docs)} / 走査完了")

uniq = sorted({nz for pc in docs.values() for (nz, _) in pc})
print(f"ユニーク語 {len(uniq)} をorchestrate中...")
appcache = app_roots_batch(uniq)

# ---- 文書別精度 ----
doc_rows = []
agg_mis = collections.Counter()
g_total = g_match = 0
for name, pc in docs.items():
    total = match = 0
    for (nz, refd), c in pc.items():
        ap = appcache.get(nz)
        if ap is None or "".join(ap) != nz: continue
        total += c
        if cuts(refd) == cuts("/".join(ap)): match += c
        else: agg_mis[(nz, refd, "/".join(ap))] += c
    if total:
        doc_rows.append((name, total, match, match*1000//total/10))
        g_total += total; g_match += match
doc_rows.sort(key=lambda r: r[3])
print(f"\n=== 文書別 境界一致(下位15, 全{len(doc_rows)}文書) ===")
for name, total, match, pct in doc_rows[:15]:
    print(f"  {pct:5.1f}%  {match:5d}/{total:<5d}  {name[:60]}")
print(f"  ... 上位は軒並み98-100%。中央値 {sorted(r[3] for r in doc_rows)[len(doc_rows)//2]:.1f}%")
print(f"\n=== コーパス全体 {g_match}/{g_total} ({g_match*1000//g_total/10}%)  不一致 {g_total-g_match} ===")

# ---- 不一致を gold で裁定 ----
GRAM = {"o","oj","on","ojn","a","aj","an","ajn","e","en","n","j","jn","i","as","is","os","us","u"}
def first_char_isolated(app):  # 先頭1文字孤立(真欠陥クラス)
    pp = [p for p in app.split("/") if p]
    return len(pp) >= 2 and len(pp[0]) == 1
buckets = collections.defaultdict(list)
tally = collections.Counter()
for (word, refd, appd), c in agg_mis.items():
    g = gold_decomp.get(word)
    ca, cr = cuts(appd), cuts(refd)
    if g is None:
        cat = "NOTINGOLD_先頭1字孤立" if first_char_isolated(appd) else (
              "NOTINGOLD_app粗(同綴り候補)" if len(cuts(appd)) < len(cuts(refd)) else "NOTINGOLD_その他")
    else:
        cg = cuts(g)
        if cg == ca and cg != cr: cat = "コーパス誤り_app正(gold一致)"
        elif cg == cr and cg != ca: cat = "app誤り_真欠陥(gold=コーパス)"
        elif cg == ca and cg == cr: cat = "謎(gold=両方)"  # 起きないはず
        else:
            cat = "gold第三分解_app寄り" if (len(cg ^ ca) <= len(cg ^ cr)) else "gold第三分解_コーパス寄り"
    tally[cat] += c
    if len(buckets[cat]) < 60:
        buckets[cat].append({"word": word, "corpus": refd, "app": appd, "gold": g, "count": c})

print("\n=== 不一致579の gold 裁定(インスタンス数) ===")
for cat, n in tally.most_common():
    print(f"  {n:4d}  {cat}")
print("\n--- 各バケット例(最大6) ---")
for cat, n in tally.most_common():
    print(f"[{cat}]  計{n}")
    for e in sorted(buckets[cat], key=lambda x: -x["count"])[:6]:
        print(f"   x{e['count']:<3d} word={e['word']:18s} corpus={e['corpus']:20s} app={e['app']:20s} gold={e['gold']}")

OUT = BASE + r"\_analysis_20260625\out"
json.dump({c: buckets[c] for c in buckets}, open(lp(OUT + r"\_corpus_arbitration.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump([{"name": n, "total": t, "match": mt, "pct": p} for n, t, mt, p in doc_rows],
          open(lp(OUT + r"\_corpus_perdoc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n保存: out/_corpus_arbitration.json, out/_corpus_perdoc.json")
