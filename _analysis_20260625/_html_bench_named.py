# -*- coding: utf-8 -*-
"""要件7.4: 名指しの2ベンチHTML(vere_aux_fantazie / meznivela_sola)について
   app分解 vs 京大エス研ルビ分解を【文書単位】で境界一致測定。
   「この2文書程度の語根分解精度を再現できれば最高」(ユーザー明言)を定量レポート化。
   corpus_bench.py の実証済みヘルパを流用。"""
import re, sys, json, html as htmllib, os, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
appdir = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, appdir)
import esp_text_replacement_module as m
DATA = appdir + r"\app_data"
dd = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))

# 名指し2文書(fuyouへ退避済の京大エス研コーパス内)
MISC = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\fuyou\_project_root_misc"
DOCS = {
    "vere_aux_fantazie":   os.path.join(MISC, "vere_aux_fantazie.html"),
    "meznivela_sola(藤巻)": os.path.join(MISC, "Esperanto_meznivela_sola_lernolibro_verkita_de_sro_fujximaki_260215.html"),
}

def _roots_from_html(h):
    toks = []; pos = 0
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', h):
        pre = re.sub(r'<[^>]+>', '', h[pos:mm.start()])
        for ch in re.findall(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', pre): toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    tail = re.sub(r'<[^>]+>', '', h[pos:])
    for ch in re.findall(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', tail): toks.append(ch)
    return [norm(t) for t in toks if norm(t)]

def app_roots_batch(words, chunk=2500):
    out = {}
    for s in range(0, len(words), chunk):
        batch = words[s:s+chunk]
        text = "\n".join(" " + w + " " for w in batch)
        h = m.orchestrate_comprehensive_esperanto_text_replacement(text, ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
        lines = h.split("\n")
        if len(lines) != len(batch):
            for w in batch: out[w] = None
            continue
        for w, ln in zip(batch, lines): out[w] = _roots_from_html(ln)
    return out

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
    pp = [p for p in s.split('/') if p]; b = set(); c = 0
    for p in pp[:-1]: c += len(p); b.add(c)
    return b

def tail_pattern(r, a):
    rp = [p for p in r.split('/') if p]; ap = [p for p in a.split('/') if p]
    nr, na = len(rp), len(ap)
    GRAM = ('o','oj','on','ojn','a','aj','an','ajn','e','en','n','j','jn','i','as','is','os','us','u')
    if na < nr:
        if na == 1: return 'A_全体一体(同綴り/設計)'
        if nr - na == 1 and rp[-1] in GRAM: return f'B_末尾語尾結合(+{rp[-1]})'
        return 'D_その他過少'
    if na > nr: return 'C_過分解(余分境界)'
    return 'E_境界位置ずれ'

allpairs = collections.Counter()
docpairs = {}
for name, path in DOCS.items():
    if not os.path.exists(path): print(f"!! NOT FOUND: {path}"); continue
    t = open(path, encoding='utf-8', errors='ignore').read()
    pc = collections.Counter()
    for word, br in parse_words(t):
        rp = [norm(x) for x in br if norm(x)]
        if len(rp) < 2: continue
        nz = norm(word)
        if not re.fullmatch(r'[a-zĉĝĥĵŝŭ\-]+', nz): continue
        pc[(nz, '/'.join(rp))] += 1; allpairs[(nz, '/'.join(rp))] += 1
    docpairs[name] = pc

uniq = sorted({nz for pc in docpairs.values() for (nz, _) in pc})
print(f"2文書 ユニーク(語,分解)={sum(len(p) for p in docpairs.values())}  ユニーク語={len(uniq)} をorchestrate中...\n")
appcache = app_roots_batch(uniq)

def report(name, pc):
    total = match = 0; mis = collections.Counter()
    for (nz, refd), c in pc.items():
        ap = appcache.get(nz)
        if ap is None or ''.join(ap) != nz: continue
        total += c
        if cuts(refd) == cuts('/'.join(ap)): match += c
        else: mis[(refd, '/'.join(ap))] += c
    pct = match*1000//max(total,1)/10
    print(f"=== [{name}] 多片語トークン境界一致 {match}/{total} ({pct}%)  不一致 {total-match} ===")
    patt = collections.Counter(); pex = collections.defaultdict(list)
    for (r, a), c in mis.items():
        p = tail_pattern(r, a); patt[p] += c
        if len(pex[p]) < 6: pex[p].append((c, r, a))
    for p, v in patt.most_common(): print(f"   {p}: {v}")
    for p, _ in patt.most_common():
        for c, r, a in sorted(pex[p], reverse=True)[:4]:
            print(f"      x{c:3d} ref={r:24s} app={a}")
    print()
    return total, match

gt = gm = 0
for name, pc in docpairs.items():
    t_, m_ = report(name, pc); gt += t_; gm += m_
print(f"=== 【2文書 合算】境界一致 {gm}/{gt} ({gm*1000//max(gt,1)/10}%)  不一致 {gt-gm} ===")
json.dump([[r, a, c] for (r, a), c in allpairs.most_common()][:1],
          open(lp(BASE + r"\_analysis_20260625\out\_named_html_pairs_head.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
