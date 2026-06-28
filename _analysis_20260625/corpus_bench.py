# -*- coding: utf-8 -*-
"""京大エス研HTMLコーパス全体でアプリ分解 vs 参照を比較。
   不一致を形態素パターン別に集計し、汎用的に直せる法則を抽出する。"""
import re, sys, json, html as htmllib, os, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
CORP = BASE + r"\京大エス研html文書＿Github"
appdir = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, appdir)
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
        pre = re.sub(r'<[^>]+>', '', h[pos:mm.start()])
        for ch in re.findall(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', pre): toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    tail = re.sub(r'<[^>]+>', '', h[pos:])
    for ch in re.findall(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', tail): toks.append(ch)
    return [norm(t) for t in toks if norm(t)]

def app_roots_batch(words, chunk=2500):
    """全語を改行区切りで一括orchestrate(per-word呼びは遅すぎ→バッチ)。各語は前後空白で
       standalone境界を再現。出力を改行で分割し語ごとにルビ根を抽出。"""
    out = {}
    for s in range(0, len(words), chunk):
        batch = words[s:s+chunk]
        text = "\n".join(" " + w + " " for w in batch)
        h = m.orchestrate_comprehensive_esperanto_text_replacement(text, ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
        lines = h.split("\n")
        if len(lines) != len(batch):
            # 改行がruby内に紛れた場合のフォールバック(まず無い)
            for w in batch: out[w] = None
            continue
        for w, ln in zip(batch, lines):
            out[w] = _roots_from_html(ln)
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

# 全HTML集計: (word_nz, ref_decomp) -> count
pair_count = collections.Counter()
nfile = 0
for root, dirs, files in os.walk(lp(CORP)):
    for f in files:
        if not f.lower().endswith(('.html', '.htm')): continue
        try:
            t = open(os.path.join(root, f), encoding='utf-8', errors='ignore').read()
        except Exception: continue
        ws = parse_words(t)
        if ws: nfile += 1
        for word, br in ws:
            rp = [norm(x) for x in br if norm(x)]
            if len(rp) < 2: continue
            nz = norm(word)
            if not re.fullmatch(r'[a-zĉĝĥĵŝŭ\-]+', nz): continue
            pair_count[(nz, '/'.join(rp))] += 1
print(f"集計ファイル {nfile}, ユニーク(語,分解) {len(pair_count)}")

def cuts(s):
    ps = [p for p in s.split('/') if p]; b = set(); c = 0
    for p in ps[:-1]: c += len(p); b.add(c)
    return b
uniq_words = sorted({nz for (nz, _) in pair_count})
print(f"ユニーク語 {len(uniq_words)} をバッチorchestrate中...")
appcache = app_roots_batch(uniq_words)
total = match = 0; mis = collections.Counter()
for (nz, refd), c in pair_count.items():
    ap = appcache.get(nz)
    if ap is None or ''.join(ap) != nz: continue
    total += c
    if cuts(refd) == cuts('/'.join(ap)): match += c
    else: mis[(refd, '/'.join(ap))] += c
print(f"\n=== コーパス全体 境界一致 {match}/{total} ({match*1000//max(total,1)/10}%)  不一致 {total-match} ===")

# パターン分類: 末尾差分の形態素で
def tail_pattern(r, a):
    rp = [p for p in r.split('/') if p]; ap = [p for p in a.split('/') if p]
    nr, na = len(rp), len(ap)
    GRAM = ('o','oj','on','ojn','a','aj','an','ajn','e','en','n','j','jn','i','as','is','os','us','u')
    if na < nr:  # appが粗
        if na == 1: return 'A_全体一体(同綴り/設計)'
        if nr - na == 1 and rp[-1] in GRAM:
            return f'B_末尾語尾結合(+{rp[-1]})'   # X/Y/oj vs X/Yoj
        return 'D_その他過少'
    if na > nr: return 'C_過分解(余分境界)'
    return 'E_境界位置ずれ'
patt = collections.Counter(); pex = collections.defaultdict(list)
for (r, a), c in mis.items():
    p = tail_pattern(r, a); patt[p] += c
    if len(pex[p]) < 18: pex[p].append((c, r, a))
print("\n--- 不一致パターン別インスタンス数 ---")
for p, v in patt.most_common(): print(f"  {p}: {v}")
for p, _ in patt.most_common():
    print(f"\n[{p}]")
    for c, r, a in sorted(pex[p], reverse=True): print(f"  x{c:4d} ref={r:22s} app={a}")
json.dump([[r, a, c] for (r, a), c in mis.most_common()], open(lp(BASE + r"\_analysis_20260625\out\corpus_mismatch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
