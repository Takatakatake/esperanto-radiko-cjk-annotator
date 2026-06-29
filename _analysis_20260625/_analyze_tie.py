# -*- coding: utf-8 -*-
"""「重要語彙・派生形の分解は、同じ文字数の中では優先されるべき」原理の検証。
   2890重要語のgold不一致を、①国名-i/o等の構造天井 ②同片数の境界違い(=同長タイの可能性)
   ③app粗(長語勝ち=greedy, ユーザー対象外) に分類し、真の『同長タイ負け』があるか特定する。"""
import csv, re, sys, json
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
GOLD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
gold = {}
with open(lp(GOLD), encoding="utf-8") as f:
    for line in f:
        if ":" not in line: continue
        d = line.split(":", 1)[0].strip()
        if " " in d or d.startswith("-") or d.endswith("-"): continue
        gw = norm("".join(p for p in d.split("/") if p))
        if re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", gw): gold.setdefault(gw, "/".join(p for p in norm(d).split("/") if p))
CSV = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\30_重要語彙CSV_日中対照_2890語\2890 Gravaj Esperantaj Vortoj kun Signifoj en la Japana, Ĉina.csv"
words = []
for r in list(csv.reader(open(lp(CSV), encoding="utf-8")))[1:]:
    if not r or not r[0].strip(): continue
    e = r[0].strip()
    if e.startswith("-") or e.endswith("-") or " " in e: continue
    w = norm(e)
    if re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", w): words.append(w)
words = sorted(set(words))
APP = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, APP); DATA = APP + r"\app_data"
import esp_text_replacement_module as m
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt")); pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
dd = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]; G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]; GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
def roots(w):
    h = m.orchestrate_comprehensive_esperanto_text_replacement(" " + w + " ", ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
    t = []; pos = 0
    for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>', h):
        for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+', re.sub(r'<[^>]+>', '', h[pos:mm.start()]), re.I): t.append(ch)
        t.append(mm.group(1)); pos = mm.end()
    for ch in re.findall(r'[a-zĉĝĥĵŝŭ]+', re.sub(r'<[^>]+>', '', h[pos:]), re.I): t.append(ch)
    return [norm(x) for x in t]
def cuts(s):
    pp = [p for p in s.split("/") if p]; b = set(); c = 0
    for p in pp[:-1]: c += len(p); b.add(c)
    return b
cat = {"国名/-i-(構造天井)": [], "同片数_境界違い(同長タイ?)": [], "app粗_長語勝ち(対象外)": [], "app細": [], "その他": []}
for w in words:
    if w not in gold: continue
    rt = roots(w)
    if "".join(rt) != w: continue
    a = "/".join(rt); g = gold[w]
    if cuts(a) == cuts(g): continue
    pa = [p for p in a.split("/") if p]; pg = [p for p in g.split("/") if p]
    if "i" in pg and "i" not in pa: cat["国名/-i-(構造天井)"].append((w, g, a))
    elif len(pa) == len(pg): cat["同片数_境界違い(同長タイ?)"].append((w, g, a))
    elif len(pa) < len(pg): cat["app粗_長語勝ち(対象外)"].append((w, g, a))
    elif len(pa) > len(pg): cat["app細"].append((w, g, a))
    else: cat["その他"].append((w, g, a))
print("2890重要語(gold収録)の不一致 分類:\n")
for k, v in cat.items():
    print(f"[{k}] {len(v)}語")
    for w, g, a in v[:12]: print(f"    {w:16s} gold={g:20s} app={a}")
    print()
