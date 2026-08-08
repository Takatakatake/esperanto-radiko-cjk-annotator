# -*- coding: utf-8 -*-
"""3アプリ(JA/ZH/KO)の注釈ルビの『分解(語根境界)が一致しているか』を全語で測定。
   gold∪漢字単一語を3アプリでルビ化し、各語の境界cutを比較。不一致語を分類・カタログ化。
   出力: out/_anno_divergence.json (分解が割れる語の三言語詳細)。"""
import re, sys, json, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

words = set()
GOLD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
with open(lp(GOLD), encoding="utf-8") as f:
    for line in f:
        if ":" not in line: continue
        d = line.split(":", 1)[0].strip()
        if " " in d or d.startswith("-") or d.endswith("-"): continue
        w = norm("".join(p for p in d.split("/") if p))
        if re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", w): words.add(w)
INJ = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\漢字化・語彙資料\エスペラント語根＿漢字割り当て＿20260621\漢字注入_学習者版_20260620.txt"
Lr = re.compile(r"^(.*?)⟦")
with open(lp(INJ), encoding="utf-8") as f:
    for line in f:
        mm = Lr.match(line.rstrip("\n"))
        if not mm: continue
        h = mm.group(1).strip()
        if " " in h or "#" in h: continue
        w = norm("".join(p for p in h.split("/") if p))
        if re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", w): words.add(w)
words = sorted(words)
print(f"検証語 {len(words)}")

APPS = {"JA": r"\Esperanto-Kanji-Ruby-JA", "ZH": r"\Esperanto-Kanji-Ruby-ZH", "KO": r"\Esperanto-Kanji-Ruby-KO"}
for d in APPS.values(): sys.path.insert(0, BASE + d)

def engine(d):
    import importlib, esp_text_replacement_module as m; importlib.reload(m)
    DATA = BASE + d + r"\app_data"; dd = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
    GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]; G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]; GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
    ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt")); pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
    return (m, ps, GL, pl, GG, G2)

def decomp_map(eng):
    m, ps, GL, pl, GG, G2 = eng; out = {}
    CH = 2500
    for s in range(0, len(words), CH):
        b = words[s:s+CH]
        h = m.orchestrate_comprehensive_esperanto_text_replacement("\n".join(" "+w+" " for w in b), ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
        ls = h.split("\n")
        if len(ls) != len(b): continue
        for w, ln in zip(b, ls):
            segs = []
            roots = re.findall(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", ln)
            # rb列(語根境界) + グロス
            out[w] = [(norm(r), g.replace("<br>", "")) for r, g in roots]
    return out

maps = {}
for k, d in APPS.items():
    print(f"[{k}] 分解中..."); maps[k] = decomp_map(engine(d))

def cuts(segs):
    b = set(); c = 0
    for r, _ in segs[:-1]: c += len(r); b.add(c)
    return frozenset(b)

div = []
agree = 0
for w in words:
    sj, sz, sk = maps["JA"].get(w), maps["ZH"].get(w), maps["KO"].get(w)
    if not (sj and sz and sk): continue
    cj, cz, ck = cuts(sj), cuts(sz), cuts(sk)
    if cj == cz == ck:
        agree += 1
    else:
        div.append({"w": w,
                    "JA": "/".join(r for r, _ in sj), "ZH": "/".join(r for r, _ in sz), "KO": "/".join(r for r, _ in sk),
                    "JA_g": [list(x) for x in sj], "ZH_g": [list(x) for x in sz], "KO_g": [list(x) for x in sk]})
tot = agree + len(div)
print(f"\n=== 3アプリ分解一致 {agree}/{tot} = {round(agree*100/tot,2)}%  / 不一致 {len(div)} 語 ===")
# 不一致の型
typ = collections.Counter()
for e in div:
    nj, nz, nk = e["JA"].count("/"), e["ZH"].count("/"), e["KO"].count("/")
    if nz == nk and nz != nj: typ["JA だけ違う(JA丸ごと/中韓分割 等)"] += 1
    elif nj == nk and nj != nz: typ["ZH だけ違う"] += 1
    elif nj == nz and nj != nk: typ["KO だけ違う"] += 1
    else: typ["三者三様"] += 1
for k, v in typ.most_common(): print(f"   {v:5d}  {k}")
OUT = BASE + r"\_analysis_20260625\out"
json.dump(div, open(lp(OUT + r"\_anno_divergence.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"保存: out/_anno_divergence.json ({len(div)}語)")
print("\n--- 不一致 例(出現順 最大25) ---")
for e in div[:25]:
    print(f"  {e['w']:16s} JA={e['JA']:20s} ZH={e['ZH']:20s} KO={e['KO']}")
