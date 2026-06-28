# -*- coding: utf-8 -*-
"""デプロイ済みJSONで代表テキストを処理し、ルビ表示確認用HTMLを3言語分生成(Downloads)。"""
import json, sys, os, re
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
FMT = 'HTML格式_Ruby文字_大小调整'
APPS = {
 'JP': r"\Esperanto-Kanji-Ruby-JA",
 'ZH': r"\Esperanto-Kanji-Ruby-ZH",
 'KO': r"\Esperanto-Kanji-Ruby-KO",
}
DEMO = """Saluton, kara amiko! Mi lernas Esperanton kaj la internacia lingvo estas bona.
La anestezio kaj la biologio kaj la zoologio estas sciencoj.
La hidrokarbono kaj la amelazo estas en kemio.
Abelkulturo kaj akvokulturo kaj kulturo: malsamaj sencoj de kultur.
La agronomo studas, kaj monomanio estas malsana stato.
Hundoj kaj katoj vivas en la domo de la lernejano."""

dl = os.path.join(os.environ["USERPROFILE"], "Downloads", "エスペラント_ルビ確認_20260625")
os.makedirs(lp(dl), exist_ok=True)

for key, d in APPS.items():
    APPDIR = BASE + d; DATA = APPDIR + r"\app_data"
    sys.path.insert(0, APPDIR)
    # 各アプリのモジュールは同一だが、import済みなら再利用される(関数は同一実装)
    import importlib
    import esp_text_replacement_module as M
    importlib.reload(M)
    with open(lp(DATA + r"\置換リスト_ルビ.json"), encoding='utf-8') as f:
        cmb = json.load(f)
    g = cmb["全域替换用のリスト(列表)型配列(replacements_final_list)"]
    l = cmb["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
    c = cmb["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
    ps = M.import_placeholders(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
    pl = M.import_placeholders(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
    out = M.orchestrate_comprehensive_esperanto_text_replacement(DEMO, ps, l, pl, g, c, FMT)
    html = M.apply_ruby_html_header_and_footer(out, FMT)
    path = os.path.join(dl, f"sample_{key}.html")
    with open(lp(path), "w", encoding="utf-8") as h:
        h.write(html)
    print(f"[{key}] {path}")
print(f"\nブラウザで開いて確認してください: {dl}")
