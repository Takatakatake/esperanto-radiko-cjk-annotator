# -*- coding: utf-8 -*-
"""新規ファイル 202607 の語根分解ミス・注釈ミスを、JAアプリ(master標準)と突き合わせて検出。
   既定=dry-run(分解差・グロス差を一覧表示)。--write で「分解が違う語」のみ app の正ルビへ置換
   (rb不変・タグ収支検証・.bak退避)。グロスのみの差は別途レビュー対象として出力。"""
import re, sys, json, os, html as htmllib, collections, shutil
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
WRITE = "--write" in sys.argv
F = BASE + r"\_project_root_misc\京大エス研html文書＿Github\revuoj\revuo-orienta\2026\202607_Revuo_eltiritaj_Esperantaj_pagxoj_kun_japanaj_tradukoj.html"

APP = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, APP)
import esp_text_replacement_module as m
import esp_overlay_module as ov
DATA = APP + r"\app_data"
dd = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt")); pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
FMT = "HTML格式_Ruby文字_大小调整"
RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>", re.S)
_ESP = "a-zA-ZĉĝĥĵŝŭĈĜĤĴŜŬ"

def app_render(surface):
    h = m.orchestrate_comprehensive_esperanto_text_replacement(" " + surface + " ", ps, GL, pl, GG, G2, FMT)
    # 先頭1字孤立 autofix
    auto = ov.auto_overlay_entries(h, DATA, "ruby") if "<ruby>" in h else []
    if auto:
        h = m.orchestrate_comprehensive_esperanto_text_replacement(" " + surface + " ", ps, GL, pl, ov.merge_overlay(GG, auto), G2, FMT)
    return h.strip()

def segs(fragment):
    out = []; pos = 0
    for mm in RUBY.finditer(fragment):
        for run in re.findall(r"[" + _ESP + r"]+", re.sub(r"<[^>]+>", " ", fragment[pos:mm.start()])): out.append((run, None))
        out.append((mm.group(1), mm.group(2).replace("<br>", ""))); pos = mm.end()
    for run in re.findall(r"[" + _ESP + r"]+", re.sub(r"<[^>]+>", " ", fragment[pos:])): out.append((run, None))
    return out
def cuts(sg):
    b = set(); c = 0
    for r, _ in sg[:-1]: c += len(r); b.add(c)
    return frozenset(b)

def iter_words(html):
    toks = []; pos = 0
    for mm in RUBY.finditer(html):
        if mm.start() > pos: toks.append(("G", html[pos:mm.start()], pos, mm.start()))
        toks.append(("R", mm.group(1), mm.start(), mm.end())); pos = mm.end()
    if pos < len(html): toks.append(("G", html[pos:], pos, len(html)))
    i = 0
    while i < len(toks):
        if toks[i][0] != "R": i += 1; continue
        start = toks[i][2]; end = toks[i][3]; surface = toks[i][1]; j = i
        while True:
            if j + 1 < len(toks) and toks[j + 1][0] == "R":
                j += 1; surface += toks[j][1]; end = toks[j][3]; continue
            if j + 2 < len(toks) and toks[j + 1][0] == "G" and toks[j + 2][0] == "R" and re.fullmatch(r"[" + _ESP + r"]{1,4}", toks[j + 1][1]):
                surface += toks[j + 1][1]; j += 2; surface += toks[j][1]; end = toks[j][3]; continue
            if j + 1 < len(toks) and toks[j + 1][0] == "G":
                ml = re.match(r"^[" + _ESP + r"]+", toks[j + 1][1])
                if ml: surface += ml.group(0); end = toks[j + 1][2] + ml.end()
            break
        yield (start, end, surface, html[start:end])
        i = j + 1

def rb_letters(h):
    h = re.sub(r"<rt[^>]*>.*?</rt>", "", h, flags=re.S)
    return re.sub(r"[^" + _ESP + r"]", "", re.sub(r"<[^>]+>", "", h))

html = open(lp(F), encoding="utf-8", errors="ignore").read()
body0 = html.find("<body")
decomp_mismatch = []; gloss_mismatch = []
fixes = []
need = {}
words = [(s, e, surf, raw) for (s, e, surf, raw) in iter_words(html) if not (body0 >= 0 and s < body0)]
uniq = sorted({surf for _, _, surf, _ in words if "-" not in surf and "'" not in surf})
for s in uniq: need[s] = app_render(s)

for start, end, surface, raw in words:
    if "-" in surface or "'" in surface: continue
    rep = need.get(surface)
    if not rep or "<ruby>" not in rep: continue
    cur = segs(raw); app = segs(rep)
    if rb_letters(rep) != re.sub(r"[^" + _ESP + r"]", "", surface): continue
    if cuts(cur) != cuts(app):
        decomp_mismatch.append((surface, "/".join(r for r, _ in cur), "/".join(r for r, _ in app)))
        fixes.append((start, end, raw, rep, surface))
    else:
        # 同分解だがグロスが違う根
        for (rc, gc), (ra, ga) in zip(cur, app):
            if gc is not None and ga is not None and norm(rc) == norm(ra) and gc.strip() and gc.strip() != ga.strip():
                gloss_mismatch.append((surface, rc, gc.strip(), ga.strip()))

print(f"202607: 多片語 {len(words)} / ユニーク {len(uniq)}")
print(f"\n=== ① 分解ミス(202607 vs JAアプリ) {len(decomp_mismatch)}語 ===")
for w, c, a in decomp_mismatch[:40]:
    print(f"  {w:20s} 202607={c:24s} → app={a}")
print(f"\n=== ② グロス差(同分解・根の訳違い) {len(gloss_mismatch)}件 (上位40) ===")
for w, r, gc, ga in gloss_mismatch[:40]:
    print(f"  {w:18s} 根={r:10s} 202607={gc:12s} app={ga}")
OUT = BASE + r"\_analysis_20260625\out"
json.dump({"decomp": decomp_mismatch, "gloss": gloss_mismatch},
          open(lp(OUT + r"\_202607_mismatch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n保存: out/_202607_mismatch.json")

if WRITE:
    print("\n=== 適用(分解ミスのみ app正ルビへ置換) ===")
    before = rb_letters(html)
    for start, end, raw, rep, surface in sorted(fixes, key=lambda x: -x[0]):
        assert html[start:end] == raw
        html = html[:start] + rep + html[end:]
    if rb_letters(html) != before:
        print("  NG rb不変違反 → 中止"); sys.exit(1)
    if html.count("<ruby>") != html.count("</ruby>") or len(re.findall(r"<rt\b", html)) != html.count("</rt>"):
        print("  NG タグ収支 → 中止"); sys.exit(1)
    bak = F + ".bak_202607fix"
    if not os.path.exists(lp(bak)): shutil.copy2(lp(F), lp(bak))
    open(lp(F), "w", encoding="utf-8").write(html)
    print(f"  分解ミス {len(fixes)}箇所を修正(rb不変・タグ収支OK)。.bak退避。")
