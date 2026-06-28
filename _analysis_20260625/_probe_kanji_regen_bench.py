# -*- coding: utf-8 -*-
"""【非破壊・書込なし】最新ソース(再生成word_kanji + master per-root CSV)で漢字JSONを
   メモリ上に再生成し、全44599語の漢字マスター一致を再測定。
   旧デプロイ版との差(=直った件数 / 回帰した件数)を出す。デプロイはしない。"""
import re, sys, json, os, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
FULL = re.compile(r"[̀-ͯʰ-˿ᴀ-ᶿ⁰-₟Ⱡ-Ɀ]")
def fs(s): return FULL.sub("", s)
OUT = BASE + r"\_analysis_20260625\out"
INJ = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\漢字注入_学習者版_20260620.txt"
APPDIR = BASE + r"\Esperanto-Kanji-Ruby-JA"
DATA = APPDIR + r"\app_data"
FMT = 'HTML格式_Ruby文字_大小调整_汉字替换'
ESTEM = r"\E_stem.json"
ROOTS = r"\root_list.txt"
STEM = r"\分解設定.json"
USER = r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"
KANJI_CSV_SRC = OUT + r"\kanji_root.csv"
with open(lp(OUT + r"\word_kanji.json"), encoding='utf-8') as f: word_kanji = json.load(f)
KANJI_DECOMPOSE = {"esperant"}
_grv = OUT + r"\gold_revert_roots.json"
if os.path.exists(lp(_grv)): KANJI_DECOMPOSE |= set(json.load(open(lp(_grv), encoding="utf-8")))
with open(lp(DATA + STEM), encoding="utf-8") as f: sett = json.load(f)
sett = [e for e in sett if not (isinstance(e, list) and len(e) >= 1 and str(e[0]).replace('/', '') in KANJI_DECOMPOSE)]
tmp = DATA + r"\_kanji_settings_regenprobe.json"
with open(lp(tmp), "w", encoding="utf-8") as g: json.dump(sett, g, ensure_ascii=False)
print("漢字JSON再生成中(書込なし)...")
combined = generate(APPDIR, DATA, KANJI_CSV_SRC, tmp, DATA + USER, DATA + ESTEM, DATA + ROOTS, FMT, word_anno=word_kanji)
os.remove(lp(tmp))
GL = combined["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = combined["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = combined["全域替换用のリスト(列表)型配列(replacements_final_list)"]
sys.path.insert(0, APPDIR)
import esp_text_replacement_module as m
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
def app_kanji_batch(words, chunk=2000):
    out = {}
    for s in range(0, len(words), chunk):
        b = words[s:s+chunk]
        h = m.orchestrate_comprehensive_esperanto_text_replacement("\n".join(" "+w+" " for w in b), ps, GL, pl, GG, G2, FMT)
        lines = h.split("\n")
        if len(lines) != len(b):
            for w in b: out[w] = None
            continue
        for w, ln in zip(b, lines):
            kj = re.sub(r'<rt[^>]*>.*?</rt>', '', ln); kj = re.sub(r'<[^>]+>', '', kj).strip()
            out[w] = kj
    return out
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
        pairs.setdefault(word, "".join(p for p in kanji.split("/")))
uniq = sorted(pairs)
print(f"マスター語数 {len(pairs)} をバッチ漢字化中...")
appres = app_kanji_batch(uniq)
total = content = 0; newdiff = {}
for w, mk in pairs.items():
    ak = appres.get(w)
    if ak is None: continue
    total += 1
    if fs(ak) == fs(mk): content += 1
    else: newdiff[w] = (fs(mk), fs(ak))
print(f"\n=== 再生成版 漢字内容一致 {content}/{total} ({content*1000//max(total,1)/10}%) ===")
# 旧diffとの比較
old = json.load(open(OUT + r"\kanji_mismatch.json", encoding="utf-8"))
old_true = {w for w, mk, ak in old if fs(mk) != fs(ak)}
new_set = set(newdiff)
fixed = old_true - new_set
regressed = new_set - old_true
print(f"旧真差 {len(old_true)} 件 → 直った {len(fixed)} / 残存 {len(old_true & new_set)} / 新規回帰 {len(regressed)}")
print(f"\n--- 直った例(旧diffで今回マスター一致) 上位30 ---")
for w in sorted(fixed)[:30]:
    print(f"  {w}")
if regressed:
    print(f"\n--- ⚠新規回帰 (前は一致→今回不一致) 全{len(regressed)}件 ---")
    for w in sorted(regressed)[:60]:
        mk, ak = newdiff[w]; print(f"  {w:20s} master={mk:14s} app={ak}")
json.dump({"new_total_diff": len(newdiff), "fixed": sorted(fixed), "regressed": {w: newdiff[w] for w in regressed}},
          open(OUT + r"\_kanji_regen_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
# 残存diffの分類(再生成後に残る差は何か)
LAT = re.compile(r"[a-zĉĝĥĵŝŭ]", re.I)
ENDINGS = ["ojn","ajn","oj","aj","on","an","en","os","is","as","us","o","a","e","i","n","j","u","s","t"]
def stem(s):
    for e in ENDINGS:
        if s.endswith(e): return s[:-len(e)]
    return s
rc = collections.Counter()
for w, (mk, ak) in newdiff.items():
    if LAT.search(stem(mk)): rc["②master自体ラテン残(改善不能)"] += 1
    elif LAT.search(stem(ak)):
        rc["2a_app未変換romaji" if not re.search(r"[一-龥]", ak) else "2b_app孤立ラテン(過分解)"] += 1
    else: rc["3_別漢字(単一語根等)"] += 1
print("\n=== 再生成後の残存差 分類 ===")
for k, v in rc.most_common(): print(f"  {k}: {v}")
