# -*- coding: utf-8 -*-
"""ルビサイズ検証(要件7.4 / ruby_css_verifier.py 系)。
   アプリ生成のルビHTMLに対し、ratio=幅(rt)/幅(rb) から期待CSSクラスを計算し、
   実クラスと照合。アプリの output_format と同一閾値・同一幅データなので一致するはずだが、
   実機生成物で食い違いゼロを定量確認する。対象: 2890重要語 + ベンチHTML2文書。"""
import re, sys, json, csv, os, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
APP = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, APP); DATA = APP + r"\app_data"
import esp_text_replacement_module as m
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt")); pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
dd = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
WIDTH = json.load(open(lp(DATA + r"\char_widths.json"), encoding="utf-8"))
def width(t): return sum(WIDTH.get(c, 8) for c in t)

# ruby_css_verifier.py と同一の閾値
THRESHOLDS = [(6.0,"XXXS_S"),(3.0,"XXS_S"),(9/4,"XS_S"),(9/5,"S_S"),(9/6,"M_M"),(9/7,"L_L"),(9/8,"XL_L")]
def expected_cls(rb, rt_clean):
    rb_w = width(rb)
    if rb_w == 0: return "XXL_L"
    ratio = width(rt_clean) / rb_w
    for th, cls in THRESHOLDS:
        if ratio > th: return cls
    return "XXL_L"
RUBY_RE = re.compile(r'<ruby>([^<]+)<rt\s+class="([^"]+)">([^<]*(?:<br>[^<]*)*)</rt></ruby>')

def check(html):
    tot = mis = 0; ex = collections.Counter()
    for mm in RUBY_RE.finditer(html):
        rb, css, rt_raw = mm.group(1), mm.group(2), mm.group(3)
        rt_clean = re.sub(r'<br>', '', rt_raw)
        exp = expected_cls(rb, rt_clean)
        tot += 1
        if css != exp:
            mis += 1
            if len(ex) < 15: ex[(rb, rt_clean, css, exp)] += 1
    return tot, mis, ex

def render(text):
    return m.orchestrate_comprehensive_esperanto_text_replacement(text, ps, pl and ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整") if False else \
           m.orchestrate_comprehensive_esperanto_text_replacement(text, ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")

# --- (1) 2890重要語 ---
CSV = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\30_重要語彙CSV_日中対照_2890語\2890 Gravaj Esperantaj Vortoj kun Signifoj en la Japana, Ĉina.csv"
words = []
for r in list(csv.reader(open(lp(CSV), encoding="utf-8")))[1:]:
    if not r or not r[0].strip(): continue
    e = r[0].strip()
    if e.startswith("-") or e.endswith("-") or " " in e: continue
    w = norm(e)
    if re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", w): words.append(w)
words = sorted(set(words))
html_words = render("\n".join(" "+w+" " for w in words))
t1, m1, ex1 = check(html_words)
print(f"=== (1) 重要2890語 ({len(words)}語) のルビ ===")
print(f"  ルビ総数 {t1}  サイズ規則不一致 {m1} ({m1*1000//max(t1,1)/10}%)")
for (rb, rt, a, e), c in ex1.most_common(10): print(f"    rb={rb:10s} rt={rt[:14]:16s} 実={a:8s} 期待={e}")

# --- (2) ベンチHTML2文書のエスペラント本文を再ルビ化して検証 ---
MISC = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\fuyou\_project_root_misc"
import html as htmllib
def plain_eo(path):
    t = open(path, encoding="utf-8", errors="ignore").read()
    t = t[t.find('<body'):] if '<body' in t else t
    t = re.sub(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', lambda x: x.group(1), t)  # 元の語に戻す
    t = re.sub(r'<[^>]+>', ' ', t); t = htmllib.unescape(t)
    return " ".join(re.findall(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+", t)[:4000])
for name, fn in [("vere_aux_fantazie", "vere_aux_fantazie.html"),
                 ("meznivela_sola", "Esperanto_meznivela_sola_lernolibro_verkita_de_sro_fujximaki_260215.html")]:
    p = os.path.join(MISC, fn)
    if not os.path.exists(p): print(f"  {name}: not found"); continue
    h = render(plain_eo(p))
    t, mi, ex = check(h)
    print(f"=== (2) {name} 本文先頭4000語のルビ ===")
    print(f"  ルビ総数 {t}  サイズ規則不一致 {mi} ({mi*1000//max(t,1)/10}%)")
    for (rb, rt, a, e), c in ex.most_common(6): print(f"    rb={rb:10s} rt={rt[:14]:16s} 実={a:8s} 期待={e}")
