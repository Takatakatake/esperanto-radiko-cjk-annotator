# -*- coding: utf-8 -*-
import json, sys, os, re
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
def eng(d):
    sys.path.insert(0, os.path.join(BASE, d))
    import importlib, esp_text_replacement_module as m; importlib.reload(m)
    DATA = os.path.join(BASE, d, "app_data")
    dd = json.load(open(lp(os.path.join(DATA, "置換リスト_ルビ.json")), encoding="utf-8"))
    GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
    G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
    GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
    ps = m.import_placeholders(lp(os.path.join(DATA, "placeholders_skip.txt")))
    pl = m.import_placeholders(lp(os.path.join(DATA, "placeholders_localcapture.txt")))
    return m, ps, GL, pl, GG, G2
for key, d in (("JA", "Esperanto-Kanji-Ruby-JA"), ("KO", "Esperanto-Kanji-Ruby-KO")):
    m, ps, GL, pl, GG, G2 = eng(d)
    for w in ("brazilano", "afrikano"):
        h = m.orchestrate_comprehensive_esperanto_text_replacement(" " + w + " ", ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整").strip()
        print(f"{key} {w}: {h}")
    print()
# KO GG で brazilan を含む置換old
DATA = os.path.join(BASE, "Esperanto-Kanji-Ruby-KO", "app_data")
dd = json.load(open(lp(os.path.join(DATA, "置換リスト_ルビ.json")), encoding="utf-8"))
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
hits = [e for e in GG if "brazilan" in e[0] or "brazil/an" in e[0]]
print(f"KO GG で 'brazilan' を含む old: {len(hits)}件")
for e in hits[:6]: print(f"  old={e[0]!r} -> new={e[1][:70]!r}")
# JA GG にはあるか
DATA2 = os.path.join(BASE, "Esperanto-Kanji-Ruby-JA", "app_data")
dd2 = json.load(open(lp(os.path.join(DATA2, "置換リスト_ルビ.json")), encoding="utf-8"))
GG2 = dd2["全域替换用のリスト(列表)型配列(replacements_final_list)"]
hits2 = [e for e in GG2 if "brazilan" in e[0]]
print(f"JA GG で 'brazilan' を含む old: {len(hits2)}件")
for e in hits2[:6]: print(f"  old={e[0]!r} -> new={e[1][:70]!r}")
