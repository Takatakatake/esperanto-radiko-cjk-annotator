# -*- coding: utf-8 -*-
"""複合句(空白区切り固有名・概念句 5717)の漢字一致を測定。デプロイ済み漢字JSON使用。
   句全体の漢字列(空白/スラッシュ除去・マーカー除去)を master と比較。"""
import re, sys, json, os
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
INJ = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\漢字注入_学習者版_20260620.txt"
FULL = re.compile(r"[̀-ͯʰ-˿ᴀ-ᶿ⁰-₟Ⱡ-Ɀ]")
def fs(s): return FULL.sub("", s)
appdir = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, appdir)
import esp_text_replacement_module as m
DATA = appdir + r"\app_data"
dd = json.load(open(lp(DATA + r"\置換リスト_漢字.json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
LINE = re.compile(r'^(.*?)⟦(.*?)⟧')
# 複合句を収集: head に空白あり・#無し
phrases = {}
with open(lp(INJ), encoding="utf-8") as f:
    for line in f:
        mm = LINE.match(line.rstrip("\n"))
        if not mm: continue
        head = mm.group(1).strip(); kanji = mm.group(2)
        if "#" in head or " " not in head: continue
        # 句テキスト(語境界=空白を保持, スラッシュ除去, 大文字は固有名詞として保持) と master漢字列
        cf = lambda s: replace_esperanto_chars(s, hat_to_circumflex).strip()
        text = " ".join(cf("".join(p for p in w.split("/") if p)) for w in head.split(" "))
        if not re.fullmatch(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ ]+", text): continue
        mk = re.sub(r"[ /]", "", kanji)
        phrases.setdefault(text, mk)
print(f"複合句 {len(phrases)} を漢字化中...")
items = sorted(phrases)
def kanji_of(text):
    h = m.orchestrate_comprehensive_esperanto_text_replacement(" " + text + " ", ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整_汉字替换")
    kj = re.sub(r'<rt[^>]*>.*?</rt>', '', h); kj = re.sub(r'<[^>]+>', '', kj)
    return re.sub(r"\s", "", kj)
total = content = 0; mis = []
# バッチ(改行区切り)
CH = 1500
appres = {}
for s in range(0, len(items), CH):
    b = items[s:s+CH]
    h = m.orchestrate_comprehensive_esperanto_text_replacement("\n".join(" "+t+" " for t in b), ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整_汉字替换")
    lines = h.split("\n")
    if len(lines) != len(b):
        for t in b: appres[t] = None
        continue
    for t, ln in zip(b, lines):
        kj = re.sub(r'<rt[^>]*>.*?</rt>', '', ln); kj = re.sub(r'<[^>]+>', '', kj)
        appres[t] = re.sub(r"\s", "", kj)
for t, mk in phrases.items():
    ak = appres.get(t)
    if ak is None: continue
    total += 1
    if fs(ak) == fs(mk): content += 1
    elif len(mis) < 100000: mis.append((t, fs(mk), fs(ak)))
print(f"\n=== 複合句 漢字内容一致 {content}/{total} ({content*1000//max(total,1)/10}%)  不一致 {total-content} ===")
print("不一致 上位30:")
for t, mk, ak in mis[:30]:
    print(f"  {t:28s} master={mk:18s} app={ak}")
json.dump(mis, open(lp(BASE + r"\_analysis_20260625\out\_phrase_mismatch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
