# -*- coding: utf-8 -*-
"""残不一致をカテゴリ別インスタンス数で定量化 + HTML参照グロス抽出"""
import re, sys, json, html as htmllib, collections, os
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
HTML = sys.argv[1] if len(sys.argv) > 1 else "Esperanto_meznivela_sola_lernolibro_verkita_de_sro_fujximaki_260215.html"
appdir = BASE + r"\Esperanto-Kanji-Ruby-JA"
sys.path.insert(0, appdir)
import esp_text_replacement_module as m
DATA = appdir + r"\app_data"
dd = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
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
gloss = {}
for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', t):
    gloss.setdefault(norm(mm.group(1)), mm.group(2))
t = re.sub(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', lambda x: '\x01' + x.group(1) + '\x01', t)
t = re.sub(r'<[^>]+>', ' ', t); t = htmllib.unescape(t)
parts = re.split(r'(\x01.*?\x01)', t); words = []; buf_roots = []; buf_word = ''
for part in parts:
    if part.startswith('\x01') and part.endswith('\x01') and len(part) >= 2:
        r = part[1:-1]; buf_roots.append(norm(r)); buf_word += r
    else:
        seg = ''
        for ch in part:
            if ch.isalpha() or ch in "-'":
                seg += ch
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
HOMO = {'vin','sin','min','ĝin','nin','lin','tion','ion','etos','tenis','amas','amon','havaj','teren','dion','adon','ojn','ason'}
IOCTRY = {'japanion','koreion','jugoslavio','bulgario','jugoslavion','bulgarion'}
IV = {'agresivan','intensivan','intensivajn','detektivajn'}
cat = collections.Counter(); examples = collections.defaultdict(set)
for word, br in words:
    rp = rp_(br)
    if len(rp) < 2: continue
    nz = norm(word)
    if not re.fullmatch(r'[a-zĉĝĥĵŝŭ\-]+', nz): continue
    ap = app_roots(nz)
    if ''.join(ap) != nz: continue
    if cuts(rp) == cuts(ap): cat['一致'] += 1; continue
    if nz in HOMO: k = '①同綴り保持(設計上正しい)'
    elif nz in IOCTRY: k = '②io国名境界(許容)'
    elif nz in IV: k = '③-iv形容詞(app=接尾辞分解で良)'
    else: k = '④その他(国際/固有/微差)'
    cat[k] += 1; examples[k].add(f"{'/'.join(rp)}|{'/'.join(ap)}")
print(f"=== 残不一致 カテゴリ別インスタンス数 ({HTML[:30]}) ===")
for k, v in cat.most_common():
    print(f"  {k}: {v}")
print("\n--- ④その他の中身(直せる候補) ---")
for e in sorted(examples['④その他(国際/固有/微差)']): print(f"  {e}")
print("\n--- HTML参照グロス(過分解国際/固有語) ---")
for w in ['ideologio','ideologia','ekologio','ekologion','ideogramojn','antibiotiko','pseudonimo','ŝango','austra','milovano','papalago','irkucko']:
    print(f"  {w:14s}: {gloss.get(norm(w))}")
