# -*- coding: utf-8 -*-
"""マスター漢字割り当て(漢字注入_学習者版 = 全語の漢字分解の答え)と
   アプリ漢字化モードの一致を測定。漢字マスターをフル活用できているかの本質検証。"""
import re, sys, json, os, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
# 識別子マーカー(上付きmodifier letter群 + 同綴り根識別の結合ダイアクリティカル)を除去。
# 漢字「本体」の一致を測るには master/app 双方から対称に除去する必要がある(旧版はapp側のみ
# 一部除去・master側未除去の非対称比較で、同一漢字を大量に「不一致」誤判定していた)。
_STRIP_MARK = re.compile(r"[̀-ͯʰ-˿ᴀ-ᶿ⁰-₟Ⱡ-Ɀ]")  # 結合ダイア/spacing修飾/音声拡張(上付き)/上下付き/Latin-Ext-C(ⱽ)
def strip_mark(s): return _STRIP_MARK.sub("", s)
INJ = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\漢字注入_学習者版_20260620.txt"
appdir = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, appdir)
import esp_text_replacement_module as m
DATA = appdir + r"\app_data"
dd = json.load(open(lp(DATA + r"\置換リスト_漢字.json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
def app_kanji_batch(words, chunk=2000):
    out = {}
    for s in range(0, len(words), chunk):
        b = words[s:s+chunk]
        h = m.orchestrate_comprehensive_esperanto_text_replacement("\n".join(" "+w+" " for w in b), ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整_汉字替换")
        # rt(ルビ=語根)除去 → 親文字(漢字)のみ。各行=各語
        lines = h.split("\n")
        if len(lines) != len(b):
            for w in b: out[w] = None
            continue
        for w, ln in zip(b, lines):
            kj = re.sub(r'<rt[^>]*>.*?</rt>', '', ln); kj = re.sub(r'<[^>]+>', '', kj).strip()
            out[w] = kj  # マーカーは保持(比較時に双方から対称除去する)
    return out
# 漢字注入パース: decomp⟦kanji⟧:gloss
LINE = re.compile(r'^(.*?)⟦(.*?)⟧')
pairs = {}
with open(lp(INJ), encoding="utf-8") as f:
    for line in f:
        mm = LINE.match(line.rstrip("\n"))
        if not mm: continue
        head = mm.group(1).strip(); kanji = mm.group(2)
        if " " in head or "#" in head: continue
        word = norm("".join(p for p in head.split("/") if p))
        if not re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", word): continue
        # master kanji = ⟦⟧内のスラッシュ除去(語尾o/a/i等もそのまま含む)
        mk = "".join(p for p in kanji.split("/"))
        pairs.setdefault(word, mk)
print(f"漢字注入マスター 語数 {len(pairs)}")
uniq = sorted(pairs)
print("バッチ漢字化中...")
appres = app_kanji_batch(uniq)
total = exact = content = marker_only = 0; mis = []
for w, mk in pairs.items():
    ak = appres.get(w)
    if ak is None: continue
    total += 1
    if ak == mk:
        exact += 1; content += 1
    elif strip_mark(ak) == strip_mark(mk):
        content += 1; marker_only += 1   # 漢字本体一致・識別子マーカーのみ差
    elif len(mis) < 100000:
        mis.append((w, strip_mark(mk), strip_mark(ak)))   # 真の漢字内容差
print(f"\n=== 漢字内容一致(マーカー対称除去) {content}/{total} ({content*1000//max(total,1)/10}%) ===")
print(f"    内訳: 完全一致 {exact}, マーカー差のみ {marker_only}, 真の内容差 {len(mis)}")
print(f"    (参考: 識別子マーカー込みの完全一致は {exact}/{total} = {exact*1000//max(total,1)/10}%)")
print("\n真の漢字内容差 上位40(語: master漢字 != app漢字, マーカー除去後):")
for w, mk2, ak2 in mis[:40]:
    print(f"  {w:16s} master={mk2:14s} app={ak2}")
json.dump(mis, open(lp(BASE + r"\_analysis_20260625\out\kanji_mismatch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
