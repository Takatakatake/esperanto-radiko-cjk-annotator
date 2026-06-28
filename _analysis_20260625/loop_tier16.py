# -*- coding: utf-8 -*-
"""tier16 forceable集合を 退行0近くへ自動収束させる。
   corpusは一度だけ解析し、毎反復は JSON再生成→再orchestrate→退行原因candidate除外。"""
import re, sys, json, html as htmllib, os, collections, subprocess
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
CORP = BASE + r"\京大エス研html文書＿Github"
appdir = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, appdir)
import esp_text_replacement_module as m
DATA = appdir + r"\app_data"
JSONP = lp(DATA + r"\置換リスト_ルビ.json")
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))

def _roots_from_html(h):
    toks = []; pos = 0
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', h):
        pre = re.sub(r'<[^>]+>', '', h[pos:mm.start()])
        for ch in re.findall(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', pre): toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    tail = re.sub(r'<[^>]+>', '', h[pos:])
    for ch in re.findall(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', tail): toks.append(ch)
    return [norm(t) for t in toks if norm(t)]

def parse_words(t):
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
                    if seg: buf_word += seg; buf_roots.append(seg); seg = ''
                    if buf_word.strip(): words.append((buf_word, buf_roots))
                    buf_word = ''; buf_roots = []
            if seg: buf_word += seg; buf_roots.append(seg)
    if buf_word.strip(): words.append((buf_word, buf_roots))
    return words

def cuts(s):
    psx = [p for p in s.split('/') if p]; b = set(); c = 0
    for p in psx[:-1]: c += len(p); b.add(c)
    return b

# --- corpus を一度だけ解析 ---
pair_count = collections.Counter()
for root, dirs, files in os.walk(lp(CORP)):
    for f in files:
        if not f.lower().endswith(('.html', '.htm')): continue
        try: t = open(os.path.join(root, f), encoding='utf-8', errors='ignore').read()
        except Exception: continue
        for word, br in parse_words(t):
            rp = [norm(x) for x in br if norm(x)]
            if len(rp) < 2: continue
            nz = norm(word)
            if not re.fullmatch(r'[a-zĉĝĥĵŝŭ\-]+', nz): continue
            pair_count[(nz, '/'.join(rp))] += 1
uniq_words = sorted({nz for (nz, _) in pair_count})
print(f"corpus解析完了: {len(pair_count)}ペア {len(uniq_words)}語")

def orchestrate_all():
    dd = json.load(open(JSONP, encoding="utf-8"))
    GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
    G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
    GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
    out = {}
    for s in range(0, len(uniq_words), 2500):
        batch = uniq_words[s:s+2500]
        text = "\n".join(" " + w + " " for w in batch)
        h = m.orchestrate_comprehensive_esperanto_text_replacement(text, ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
        lines = h.split("\n")
        if len(lines) != len(batch):
            for w in batch: out[w] = None
            continue
        for w, ln in zip(batch, lines): out[w] = _roots_from_html(ln)
    return out

def bench(appcache):
    total = match = 0; mis = collections.Counter()
    for (nz, refd), c in pair_count.items():
        ap = appcache.get(nz)
        if ap is None or ''.join(ap) != nz: continue
        total += c
        if cuts(refd) == cuts('/'.join(ap)): match += c
        else: mis[(refd, '/'.join(ap))] += c
    return total, match, mis

GRAM = {'o','oj','on','ojn','a','aj','an','ajn','e','en','n','j','jn','i','as','is','os','us','u'}
def strip_gram(nz):
    for e in sorted(GRAM, key=len, reverse=True):
        if nz.endswith(e) and len(nz) > len(e): return nz[:-len(e)]
    return nz

before = {(r, a): c for r, a, c in json.load(open(lp("out/corpus_mismatch_before16.json"), encoding="utf-8"))}
fc = json.load(open(lp("out/_forceable16.json"), encoding="utf-8"))
t15 = {x['w'] for x in json.load(open(lp("out/confirmed_tier15.json"), encoding="utf-8"))}
cands = []
for ref, app in fc:
    w = ''.join(p for p in ref.split('/') if p)
    if w in t15: continue
    cands.append({'w': w, 'target': ref})

for it in range(1, 11):
    json.dump(cands, open(lp("out/confirmed_tier16.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    subprocess.run([sys.executable, lp("apply_confirmed.py"), "16", "--write"], cwd=lp("."), capture_output=True)
    total, match, mis = bench(orchestrate_all())
    reg = {(r, a): c for (r, a), c in mis.items() if (r, a) not in before}
    nreg = sum(reg.values())
    fixed = sum(c for (r, a), c in before.items() if (r, a) not in mis)
    print(f"[反復{it}] cands={len(cands)} 一致={match}/{total} ({match*1000//total/10}%) 解消={fixed} 退行={nreg}件({len(reg)}種)")
    if nreg == 0: print("  → 退行0 達成"); break
    # culprit特定
    stem_cul = set(); lead_cul = set(); word_cul = set()
    for (r, a), c in reg.items():
        rp = [p for p in r.split('/') if p]; ap = [p for p in a.split('/') if p]
        nz = ''.join(rp)
        stem_cul.add(strip_gram(nz)); word_cul.add(nz)
        rset = set(rp)
        for p in ap:                       # appにあってrefに無い片(spurious)
            if p not in rset and len(p) >= 2: lead_cul.add(p)
    newc = []; removed = 0
    for e in cands:
        pcs = [p for p in e['target'].split('/') if p]
        stem = ''.join(pcs[:-1]) if (pcs[-1] in ('o','a','e','i') and len(pcs[-1]) == 1) else ''.join(pcs)
        if (stem in stem_cul or e['w'] in word_cul or e['w'] in stem_cul
                or any(p in lead_cul for p in pcs)):
            removed += 1; continue
        newc.append(e)
    print(f"  culprit除外 {removed} (stem{len(stem_cul)}/spurious{len(lead_cul)})")
    if removed == 0: print("  → これ以上特定不可、終了"); break
    cands = newc

json.dump(cands, open(lp("out/confirmed_tier16.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n最終 tier16: {len(cands)}語")
