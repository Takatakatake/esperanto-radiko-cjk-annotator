# -*- coding: utf-8 -*-
"""日中韓注釈ルビの品質監査(データ収集)。
   デプロイ済み3アプリ(JA/ZH/KO)で gold∪漢字マスター 単一語を実際にルビ化し、
   語根→グロスを言語別に収集 → 語根ごとの (JA,ZH,KO) 対応表を作る。
   検出: ①被覆率(言語別) ②欠落(ある言語だけ訳なし/latin残り) ③言語間で被覆が割れる語根
        ④グロスが疑わしい(空/latin/過長=合成語義の疑い)。
   出力: out/_anno_jck_table.json (全語根の三言語対応), out/_anno_flags.json (要審査)。"""
import re, sys, json, os, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

# 語リスト = gold ∪ 漢字注入(単一語)
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
L = re.compile(r"^(.*?)⟦")
with open(lp(INJ), encoding="utf-8") as f:
    for line in f:
        m = L.match(line.rstrip("\n"))
        if not m: continue
        h = m.group(1).strip()
        if " " in h or "#" in h: continue
        w = norm("".join(p for p in h.split("/") if p))
        if re.fullmatch(r"[a-zĉĝĥĵŝŭ]+", w): words.add(w)
words = sorted(words)
print(f"検証語リスト(gold∪漢字単一語) = {len(words)} 語")

LATIN = re.compile(r"[a-zĉĝĥĵŝŭ]", re.I)
APPS = {"JA": (r"\Esperanto-Kanji-Ruby-JA", r"\エスペラント語根-日本語訳ルビ対応リスト.csv"),
        "ZH": (r"\Esperanto-Kanji-Ruby-ZH", r"\世界语词根-中文注释对应列表.csv"),
        "KO": (r"\Esperanto-Kanji-Ruby-KO", r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv")}

# 語根→グロス(言語別, 最頻)。語根は実際に出た content root(>=2字)。
root_gloss = {k: collections.defaultdict(collections.Counter) for k in APPS}
cover = {k: {"total": 0, "fully": 0, "partial": 0, "none": 0} for k in APPS}
for key, (d, _csv) in APPS.items():
    APPDIR = BASE + d; DATA = APPDIR + r"\app_data"; sys.path.insert(0, APPDIR)
    import importlib, esp_text_replacement_module as m; importlib.reload(m)
    dd = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
    GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
    G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
    GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
    ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
    pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
    CH = 2500
    for s in range(0, len(words), CH):
        b = words[s:s+CH]
        h = m.orchestrate_comprehensive_esperanto_text_replacement("\n".join(" "+w+" " for w in b), ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
        lines = h.split("\n")
        if len(lines) != len(b): continue
        for w, ln in zip(b, lines):
            cover[key]["total"] += 1
            roots = re.findall(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", ln)
            content = [(norm(r), g.replace("<br>", "")) for r, g in roots if len(norm(r)) >= 2]
            if not content:
                cover[key]["none"] += 1; continue
            gl = 0
            for r, g in content:
                ok = bool(g) and not LATIN.fullmatch(g) and g != r
                if ok: gl += 1; root_gloss[key][r][g] += 1
            if gl == len(content): cover[key]["fully"] += 1
            elif gl > 0: cover[key]["partial"] += 1
            else: cover[key]["none"] += 1
    c = cover[key]; print(f"  [{key}] 完全被覆 {c['fully']}/{c['total']} = {round(c['fully']*100/c['total'],2)}% / 部分 {c['partial']} / 無 {c['none']} / 収集語根 {len(root_gloss[key])}")

# 語根ごとの三言語対応表
allroots = sorted(set().union(*[set(root_gloss[k]) for k in APPS]))
def top(key, r):
    c = root_gloss[key].get(r)
    return c.most_common(1)[0][0] if c else None
table = {}
flags = collections.defaultdict(list)
for r in allroots:
    ja, zh, ko = top("JA", r), top("ZH", r), top("KO", r)
    table[r] = {"ja": ja, "zh": zh, "ko": ko}
    miss = [L for L, g in (("JA", ja), ("ZH", zh), ("KO", ko)) if not g]
    if miss and len(miss) < 3:                       # 一部言語だけ欠落(整合崩れ)
        flags["一部言語のみ欠落"].append({"root": r, **table[r]})
    if len(miss) == 3:
        flags["三言語とも欠落"].append({"root": r, **table[r]})
    # 過長グロス(合成語義の疑い): 句読点/長さ
    for L, g in (("JA", ja), ("ZH", zh), ("KO", ko)):
        if g and (len(g) >= 8):
            flags["過長グロス(合成語義疑い)"].append({"root": r, "lang": L, "gloss": g})
            break

print(f"\n=== 三言語対応表 語根数 {len(table)} ===")
print("--- フラグ集計 ---")
for k, v in sorted(flags.items(), key=lambda x: -len(x[1])):
    print(f"  {len(v):5d}  {k}")
OUT = BASE + r"\_analysis_20260625\out"
json.dump(table, open(lp(OUT + r"\_anno_jck_table.json"), "w", encoding="utf-8"), ensure_ascii=False)
json.dump({k: v for k, v in flags.items()}, open(lp(OUT + r"\_anno_flags.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("保存: out/_anno_jck_table.json, out/_anno_flags.json")
print("\n--- 一部言語のみ欠落 例(最大15) ---")
for e in flags["一部言語のみ欠落"][:15]:
    print(f"  {e['root']:16s} ja={e['ja']}  zh={e['zh']}  ko={e['ko']}")
