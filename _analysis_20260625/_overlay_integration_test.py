# -*- coding: utf-8 -*-
"""main.py のフローを忠実に再現して、保存済み補正がルビ・漢字両モードで効くことを確認。
   本番 user_corrections.json は退避→テスト→復元で汚さない。3アプリ全て検査。"""
import re, sys, json, os, shutil
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625"); from gen_replacement import lp
APPS = {"JP": r"\Esperanto-Kanji-Ruby-JA", "ZH": r"\Esperanto-Kanji-Ruby-ZH", "KO": r"\Esperanto-Kanji-Ruby-KO"}
# 補正の検証セット: 是正対象 と 壊れてはいけない長語
CORR = ["sport/i", "fort/i"]
PROBE = ["sporti", "forti", "sportisto", "transporti", "fortikaĵo", "forte"]

def extract(h):
    toks, pos = [], 0
    for mm in re.finditer(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", h):
        for ch in re.findall(r"[a-zĉĝĥĵŝŭ]+", re.sub(r"<[^>]+>", "", h[pos:mm.start()]), re.I): toks.append(ch)
        toks.append(mm.group(1)); pos = mm.end()
    for ch in re.findall(r"[a-zĉĝĥĵŝŭ]+", re.sub(r"<[^>]+>", "", h[pos:]), re.I): toks.append(ch)
    return "/".join(toks)

for key, d in APPS.items():
    APP = BASE + d; DATA = APP + r"\app_data"
    sys.path.insert(0, APP)
    import importlib
    import esp_text_replacement_module as m; importlib.reload(m)
    import esp_overlay_module as ov; importlib.reload(ov)
    prod = os.path.join(DATA, ov.OVERLAY_FILE); bak = None
    if os.path.exists(prod): bak = prod + ".itbak"; shutil.copy2(prod, bak); os.remove(prod)
    try:
        for c in CORR: ov.add_correction(DATA, c)
        ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
        pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
        print(f"\n===== [{key}] 補正 {CORR} 適用 =====")
        for jsonname, fmt, mode in [(r"\置換リスト_ルビ.json", "HTML格式_Ruby文字_大小调整", "ruby"),
                                     (r"\置換リスト_漢字.json", "HTML格式_Ruby文字_大小调整_汉字替换", "kanji")]:
            dd = json.load(open(lp(DATA + jsonname), encoding="utf-8"))
            GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
            G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
            GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
            GG = ov.merge_overlay(GG, ov.load_overlay_entries(DATA, mode))
            print(f"  --- {mode} ---")
            for w in PROBE:
                h = m.orchestrate_comprehensive_esperanto_text_replacement(" " + w + " ", ps, GL, pl, GG, G2, fmt)
                print(f"     {w:12s} -> {extract(h)}")
    finally:
        if os.path.exists(prod): os.remove(prod)
        if bak: shutil.move(bak, prod)
    sys.path.remove(APP)
print("\n後始末完了(本番 user_corrections.json は未作成/復元)。期待: sporti=sport/i, forti=fort/i に是正、",
      "sportisto/transporti/fortikaĵo/forte は不変。")
