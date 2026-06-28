# -*- coding: utf-8 -*-
"""京大エス研コーパスHTMLの固有名詞ルビ([人名]/[地名]+CJK読み)を流用し、
   アプリで固有名詞を一体強制＋グロス注入する(参照準拠=発明なし)。
   コーパスは名前を一体保持するため、コーパス境界精度も向上する。
   現状: JP版に適用・ベンチ・検証。 python build_propernouns.py [--write]
"""
import os, re, sys, json, glob, collections, shutil
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import generate, lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
WRITE = '--write' in sys.argv
CORP = BASE + r"\京大エス研html文書＿Github"
APPDIR = BASE + r"\Esperanto-Kanji-Ruby-JA"
DATA = APPDIR + r"\app_data"
STEM = DATA + r"\世界语单词词根分解方法の使用者自定义设置.json"
ESTEMP = glob.glob(DATA + r"\PEJVO*E_stem*list*.json")[0]
ROOTS = DATA + r"\世界语全部词根_约11137个_202501.txt"
USER = DATA + r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"
CSV = DATA + r"\エスペラント語根-日本語訳ルビ対応リスト.csv"
FMT = 'HTML格式_Ruby文字_大小调整'
TAG = re.compile(r'^\[(人名|地名|宗教|文|組織|団体|作品|建造物|国名|民族)\]')
FUNC = {'mi','vi','li','ŝi','ĝi','ni','ili','oni','si','la','ne','do','nu','ja','ĉu','ke','se','ĉi','eĉ','kaj','aŭ','du','ok','tri'}

# 1) コーパスから固有名詞(base,gloss)抽出 → 主格citation(対格-n/複数-j剥がし)へ正規化
pair = collections.Counter()
for root, _, files in os.walk(CORP):
    for f in files:
        if not f.lower().endswith(('.html', '.htm')): continue
        try: t = open(os.path.join(root, f), encoding='utf-8', errors='ignore').read()
        except Exception: continue
        for mm in re.finditer(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', t):
            base, rt = mm.group(1), re.sub('<[^>]+>', '', mm.group(2))
            if ' ' in base or '-' in base or not re.match(r'[A-ZĈĜĤĴŜŬ]', base): continue
            if not re.fullmatch(r'[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]+', base): continue
            if TAG.match(rt): pair[(norm(base), rt)] += 1
def citation(nz):
    for e in ('jn','n','j'):
        if nz.endswith(e) and len(nz) - len(e) >= 3: return nz[:-len(e)]
    return nz
cit = collections.defaultdict(lambda: collections.Counter())   # citation -> gloss counter
for (nz, rt), c in pair.items():
    cit[citation(nz)][rt] += c

# 2) E_stem共通語根と衝突しない安全セットのみ(衝突名は大文字限定処理が要るため今回除外)
estem = set()
for e in json.load(open(lp(ESTEMP), encoding='utf-8')):
    s = e[0] if isinstance(e, list) else e
    estem.add(norm(str(s).replace('/', '')))
# 退行原因citation除外(国名/地名でコーパスが分解する語・共通語衝突)
culp_path = BASE + r"\_analysis_20260625\out\_pn_culprits.json"
CULP = set(json.load(open(lp(culp_path), encoding='utf-8'))) if os.path.exists(lp(culp_path)) else set()
def core(nz):  # 文法語尾を全て剥がした核(共通語根衝突判定用)
    for e in ('io','oj','aj','o','a','e','i','n','j'):
        if nz.endswith(e) and len(nz) - len(e) >= 3: return nz[:-len(e)]
    return nz
pn = {}   # citation -> gloss
for c, gl in cit.items():
    if len(c) < 3 or c in FUNC or c in estem: continue
    if c in CULP: continue
    g = gl.most_common(1)[0][0]
    if not g.startswith('[人名]'): continue   # 人名のみ一体(地名/国名はコーパスが分解 pekin/o,japan/io)
    if core(c) in estem: continue             # 核が共通語根(Tom→tom→tomo, Kato→kat猫)なら除外
    pn[c] = g
print(f"固有名詞 人名citation {len(pn)}件 を一体強制対象に (culprit除外{len(CULP)})")

# 3) 設定に一体強制エントリ[citation, prio, []] 追加(冪等: .bak_prePNから復元)
bak = STEM + ".bak_prePN"
if WRITE and os.path.exists(lp(bak)): shutil.copy2(lp(bak), lp(STEM))
settings = json.load(open(lp(STEM), encoding='utf-8'))
existing_pn = {e[0] for e in settings if isinstance(e, list) and len(e) == 3 and e[0] in pn}
for c in pn:
    if c in existing_pn: continue
    settings.append([c, len(c) * 10000 + 5000, []])   # 一体(suffix無し)・高優先
tmp = DATA + r"\_pn_settings_tmp.json"
json.dump(settings, open(lp(tmp), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 4) word_anno_ja にグロス注入(citation -> [[citation, gloss]])
wa = json.load(open(lp(BASE + r"\_analysis_20260625\out\word_anno_ja.json"), encoding='utf-8'))
wa2 = dict(wa)
for c, g in pn.items():
    wa2[c] = [[c, g]]
watmp = BASE + r"\_analysis_20260625\out\_word_anno_ja_pn.json"
json.dump(wa2, open(lp(watmp), 'w', encoding='utf-8'), ensure_ascii=False)

# 5) JP再生成
combined = generate(APPDIR, DATA, CSV, tmp, USER, ESTEMP, ROOTS, FMT, word_anno=wa2)
if WRITE:
    shutil.copy2(lp(STEM), lp(bak))
    json.dump(settings, open(lp(STEM), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    final = DATA + r"\置換リスト_ルビ.json"
    ftmp = final + ".tmp"
    json.dump(combined, open(lp(ftmp), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    json.load(open(lp(ftmp), encoding='utf-8'))  # 検証
    os.replace(lp(ftmp), lp(final))
    print("JP 書込+検証OK")
os.remove(lp(tmp))

# 6) 検証(RO/コーパスの代表的固有名詞)
import esp_text_replacement_module as m
GL = combined['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = combined['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
GG = combined['全域替换用のリスト(列表)型配列(replacements_final_list)']
ps = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_%1854%-%4934%_文字列替换skip用.txt"))
pl = m.import_placeholders(lp(DATA + r"\占位符(placeholders)_@5134@-@9728@_局部文字列替换结果捕捉用.txt"))
def show(t):
    h = m.orchestrate_comprehensive_esperanto_text_replacement(t, ps, GL, pl, GG, G2, FMT)
    return ' '.join(f'{x.group(1)}[{re.sub("<br>","/",x.group(2))}]' for x in re.finditer(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', h))
print("\n固有名詞 検証:")
for w in ['Afanti', 'Sasaki', 'Pablo', 'Ĝjaŭ', 'Sakae', 'Oosugi', 'Masao', 'Londono']:
    print(f"  {w:10s}-> {show(w)}")
