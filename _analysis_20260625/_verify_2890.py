# -*- coding: utf-8 -*-
"""第1優先群=重要語彙2890語(うち単語2807)の最終確認。
   自動補正込み(デプロイ実機相当)で ①分解の健全性(先頭1字孤立) ②gold境界一致
   ③日中韓の注釈(各語根に訳) ④漢字 の被覆を測定。問題語を列挙。"""
import csv, re, sys, json, os, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
CSV = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\30_重要語彙CSV_日中対照_2890語\2890 Gravaj Esperantaj Vortoj kun Signifoj en la Japana, Ĉina.csv"

# 単語(接辞・句を除く)
words = []
for r in list(csv.reader(open(CSV, encoding="utf-8")))[1:]:
    if not r or not r[0].strip(): continue
    e = r[0].strip()
    if e.startswith("-") or e.endswith("-") or " " in e: continue
    w = norm(e)
    if re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", w): words.append(w)
words = sorted(set(words))
print(f"重要単語 {len(words)} 語を検証\n")

# gold(学習者版) word->cuts
GOLD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
gold = {}
with open(lp(GOLD), encoding="utf-8") as f:
    for line in f:
        if ":" not in line: continue
        d = line.split(":", 1)[0].strip()
        if " " in d or d.startswith("-") or d.endswith("-"): continue
        gw = norm("".join(p for p in d.split("/") if p))
        if re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", gw): gold.setdefault(gw, norm(d))
def cuts(s):
    pp=[p for p in s.split("/") if p]; b=set(); c=0
    for p in pp[:-1]: c+=len(p); b.add(c)
    return b

APPS = {"JP": r"\Esperanto-Kanji-Ruby-JA", "ZH": r"\Esperanto-Kanji-Ruby-ZH", "KO": r"\Esperanto-Kanji-Ruby-KO"}
LATIN = re.compile(r"[a-zĉĝĥĵŝŭ]", re.I)

def roots_of(html):
    toks, pos = [], 0
    for mm in re.finditer(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", html):
        for ch in re.findall(r"[a-zĉĝĥĵŝŭ]+", re.sub(r"<[^>]+>", "", html[pos:mm.start()]), re.I): toks.append((ch, None))
        toks.append((mm.group(1), mm.group(2))); pos = mm.end()
    for ch in re.findall(r"[a-zĉĝĥĵŝŭ]+", re.sub(r"<[^>]+>", "", html[pos:]), re.I): toks.append((ch, None))
    return toks  # [(surface, rt or None)]

results = {}
for key, d in APPS.items():
    APPDIR = BASE + d; DATA = APPDIR + r"\app_data"; sys.path.insert(0, APPDIR)
    import importlib, esp_text_replacement_module as m, esp_overlay_module as ov
    importlib.reload(m); importlib.reload(ov)
    ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
    pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
    def load(name):
        dd = json.load(open(lp(DATA + name), encoding="utf-8"))
        return (dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"],
                dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"],
                dd["全域替换用のリスト(列表)型配列(replacements_final_list)"])
    GLr, G2r, GGr = load(r"\置換リスト_ルビ.json")
    GLk, G2k, GGk = load(r"\置換リスト_漢字.json")
    FMT_R = "HTML格式_Ruby文字_大小调整"; FMT_K = "HTML格式_Ruby文字_大小调整_汉字替换"

    def batch(words, GL, G2, GG, fmt, mode, ch=2000):
        out = {}
        for s in range(0, len(words), ch):
            b = words[s:s+ch]
            h = m.orchestrate_comprehensive_esperanto_text_replacement("\n".join(" "+w+" " for w in b), ps, GL, pl, GG, G2, fmt)
            lines = h.split("\n")
            if len(lines) != len(b):
                for w in b: out[w] = None
                continue
            # 自動補正(先頭1字孤立)を行単位で適用相当: 検出語をoverlayし再描画
            stranded = set()
            for w, ln in zip(b, lines):
                tk = roots_of(ln)
                if tk and len(tk[0][0]) == 1 and tk[0][0].lower() not in "aeiou" and len(tk) >= 2 and tk[1][1] is not None:
                    stranded.add(w)
            if stranded:
                auto = ov.auto_overlay_entries("\n".join(lines), DATA, mode)
                if auto:
                    GG2 = ov.merge_overlay(GG, auto)
                    h = m.orchestrate_comprehensive_esperanto_text_replacement("\n".join(" "+w+" " for w in b), ps, GL, pl, GG2, G2, fmt)
                    lines = h.split("\n")
            for w, ln in zip(b, lines): out[w] = roots_of(ln)
        return out
    rb = batch(words, GLr, G2r, GGr, FMT_R, "ruby")
    kj = batch(words, GLk, G2k, GGk, FMT_K, "kanji")

    strand = anno_full = kanji_cov = goldmatch = goldtotal = 0
    bad_strand=[]; bad_anno=[]; bad_kanji=[]
    for w in words:
        tr = rb.get(w); tk = kj.get(w)
        if not tr or "".join(t[0] for t in tr) != w: continue
        # 先頭1字孤立(子音)
        if len(tr[0][0]) == 1 and tr[0][0].lower() not in "aeiou" and len(tr) >= 2:
            strand += 1; bad_strand.append(w)
        # 注釈被覆: 内容語根(2字以上)が全て訳を持つ
        content = [(s, rt) for s, rt in tr if len(s) >= 2]
        if content:
            glossed = sum(1 for s, rt in content if rt and not LATIN.fullmatch(rt) and rt != s)
            if glossed == len(content): anno_full += 1
            else: bad_anno.append(w)
        # 漢字被覆: 漢字モードは表層(base)が漢字なので、ラテン綴りはrt側。latin再構成で語一致確認。
        def klat(s, rt): return rt if (rt is not None and not LATIN.search(s)) else s
        if tk and "".join(klat(s, rt) for s, rt in tk) == w:
            haskanji = any((not LATIN.search(s)) for s, rt in tk if s)
            if haskanji: kanji_cov += 1
            else: bad_kanji.append(w)
        # gold境界
        if w in gold:
            goldtotal += 1
            if cuts(gold[w]) == cuts("/".join(t[0] for t in tr)): goldmatch += 1
    n = len(words)
    print(f"=== [{key}] 重要{n}語 ===")
    print(f"  先頭1字孤立(自動補正後): {strand}  {bad_strand[:8]}")
    print(f"  注釈 全語根に訳: {anno_full}/{n} = {anno_full*1000//n/10}%   無訳語例: {bad_anno[:8]}")
    print(f"  漢字 被覆: {kanji_cov}/{n} = {kanji_cov*1000//n/10}%   漢字なし例: {bad_kanji[:8]}")
    if goldtotal: print(f"  gold境界一致(gold収録{goldtotal}語): {goldmatch}/{goldtotal} = {goldmatch*1000//goldtotal/10}%")
    sys.path.remove(APPDIR)
    results[key]={"strand":strand,"anno":anno_full,"kanji":kanji_cov,"n":n}
print("\n総括:", results)
