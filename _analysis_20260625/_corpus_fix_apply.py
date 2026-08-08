# -*- coding: utf-8 -*-
"""京大コーパスHTML全ファイルの「コーパス自身の分解誤り」を、アプリの正しい分解で機械修正。
   - 修正対象 = 敵対裁定で APP_RIGHT(コーパス誤り) と確定した語のうち、
     ホモグラフ/丸ごと曖昧/両者誤りを除いた「明確な形態論的誤り」のみ。
   - 各該当語の出現箇所で、アプリ(JA版 raw orchestrate)が出す正しい<ruby>列を生成し、
     その箇所のHTMLスパンだけを差し替える。rb(原綴り)は不変・<ruby>境界のみ修正。
   - 安全策: dry-run既定。--write でのみ書込(各ファイル .bak_corpusfix 退避)。
     書込後に「タグ除去後の全アルファベット列が修正前と一致(rb不変)」「ruby/rtタグ収支一致」を検証。
   使い方: python _corpus_fix_apply.py            (dry-run)
           python _corpus_fix_apply.py --write    (適用)
"""
import re, os, sys, json, html as htmllib, collections, shutil
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import lp
from extract_lib import hat_to_circumflex, replace_esperanto_chars
def norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
WRITE = "--write" in sys.argv
CORP = BASE + r"\_project_root_misc\京大エス研html文書＿Github"

APP = BASE + r"\Esperanto-Kanji-Ruby-JA"; sys.path.insert(0, APP)
import esp_text_replacement_module as m
DATA = APP + r"\app_data"
dd = json.load(open(lp(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
ps = m.import_placeholders(lp(DATA + r"\placeholders_skip.txt"))
pl = m.import_placeholders(lp(DATA + r"\placeholders_localcapture.txt"))
FMT = "HTML格式_Ruby文字_大小调整"

# ---- 確定誤りパターン (敵対裁定 corpusErrors=APP_RIGHT) ----
TASK = r"C:\Users\yt\AppData\Local\Temp\claude\d--GoogleDrive202510--------20----------------------------20260624\46f52639-acfa-48a8-8c2f-e95e8e59b22d\tasks\wkkb1m50g.output"
corpusErr = json.load(open(TASK, encoding="utf-8"))["result"]["corpusErrors"]
# ホモグラフ/丸ごと曖昧/前覆審で擁護/稀語崩れ は除外(機械修正の安全域外)
EXCLUDE = {"adon", "adone", "tiba", "etos", "argentan", "domen", "iniciatoro",
           "amon", "dion", "anton", "antoni", "ndemande", "auster",
           "areopologio", "areopologia", "areopologiajn", "areopologion",
           "renkejtigxon", "renkejtiĝon", "bizaraĵon", "bizarajxon",
           # 境界は正しいがアプリのグロスが同綴り接辞で誤る語(目視点検で除外):
           # etn/o/log(log=気を引く), an/estez(an=成員), mening/it(it=受動完了),
           # nitr/at(at=受動継続), gastr/o/skop/on(on=分数), anti/sept/ik(sept=中隔),
           # tri/lit(lit=ベッド), mez/orient(orient=方位定める;東) 文脈不適
           "etnologo", "tibetologo", "anestezi", "meningito", "nitrato",
           "gastroskopon", "antiseptiko", "trilitajn", "mezorienton"}

RUBY = re.compile(r"<ruby>(.*?)<rt[^>]*>.*?</rt></ruby>", re.S)
_ESP = "a-zA-ZĉĝĥĵŝŭĈĜĤĴŜŬ"

def segments(fragment):
    """HTML断片を語根セグメント列に: ruby rb と 裸アルファベット連を順に。(語の分解=このセグメント列)"""
    segs = []; pos = 0
    for mm in RUBY.finditer(fragment):
        gap = fragment[pos:mm.start()]
        for run in re.findall(r"[" + _ESP + r"]+", re.sub(r"<[^>]+>", " ", gap)):
            segs.append(run)
        segs.append(mm.group(1)); pos = mm.end()
    for run in re.findall(r"[" + _ESP + r"]+", re.sub(r"<[^>]+>", " ", fragment[pos:])):
        segs.append(run)
    return segs

def cuts(segs):
    b = set(); c = 0
    for s in segs[:-1]:
        c += len(s); b.add(c)
    return frozenset(b)

def cuts_str(s):
    return cuts([p for p in s.split("/") if p])

# CONFIRMED[(lemma, コーパス分解cuts)] = アプリ(正)分解cuts。完全一致した出現だけ修正する。
CONFIRMED = {}
for e in corpusErr:
    lem = norm(e["w"])
    if lem in {norm(x) for x in EXCLUDE}: continue
    CONFIRMED[(lem, cuts_str(e["corpus"]))] = cuts_str(e["app"])
TARGET = {k[0] for k in CONFIRMED}
print(f"確定誤りパターン: {len(CONFIRMED)} 件 / 対象lemma {len(TARGET)} 語")
print("  " + ", ".join(sorted(TARGET)))

def app_render(surface):
    """surface 1語をアプリで描画し、<ruby>列HTMLを返す(前後空白除去)。"""
    h = m.orchestrate_comprehensive_esperanto_text_replacement(" " + surface + " ", ps, GL, pl, GG, G2, FMT)
    return h.strip()

# ---- 語スパン抽出(オフセット保持) ----
def iter_words(html):
    """html中の『連続ruby + 内部連結文字(タグ/空白無しの純エス文字) + 末尾語尾』= 1語 を返す。"""
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
            if j + 1 < len(toks) and toks[j + 1][0] == "R":     # 隣接ruby=同語
                j += 1; surface += toks[j][1]; end = toks[j][3]; continue
            if j + 2 < len(toks) and toks[j + 1][0] == "G" and toks[j + 2][0] == "R" \
                    and re.fullmatch(r"[" + _ESP + r"]{1,4}", toks[j + 1][1]):  # 連結母音(空白/タグ無し)
                surface += toks[j + 1][1]; j += 2; surface += toks[j][1]; end = toks[j][3]; continue
            if j + 1 < len(toks) and toks[j + 1][0] == "G":     # 語終端: 末尾語尾を取り込む
                mlead = re.match(r"^[" + _ESP + r"]+", toks[j + 1][1])
                if mlead: surface += mlead.group(0); end = toks[j + 1][2] + mlead.end()
            break
        raw = html[start:end]
        yield (start, end, surface, raw, segments(raw))
        i = j + 1

# ---- 全ファイル走査 ----
files = []
for root, _d, fs in os.walk(CORP):
    for f in fs:
        if f.lower().endswith((".html", ".htm")): files.append(os.path.join(root, f))
files.sort()

# 確定誤りパターンに一致する出現を収集し、surfaceのアプリ描画をキャッシュ
need = set()
per_file_cand = {}
lemma_seen = collections.Counter()      # lemma別 出現総数
lemma_hit = collections.Counter()       # lemma別 確定誤り一致数
for path in files:
    html = open(path, encoding="utf-8", errors="ignore").read()
    body0 = html.find("<body")
    cand = []
    for start, end, surface, raw, segs in iter_words(html):
        if body0 >= 0 and start < body0: continue
        lemma = norm(surface)
        if lemma not in TARGET: continue
        if "-" in surface or "'" in surface: continue
        lemma_seen[lemma] += 1
        if (lemma, cuts(segs)) not in CONFIRMED: continue   # 確定誤りパターンのみ
        lemma_hit[lemma] += 1
        cand.append((start, end, surface, raw, segs))
        need.add(surface)
    if cand: per_file_cand[path] = cand

render = {}
for s in sorted(need):
    try: render[s] = app_render(s)
    except Exception: render[s] = None

# ---- 計画を確定(アプリ描画が確定の正分解と一致・rb(親文字)不変・ruby存在のみ) ----
# rb_letters: rt(グロス)を除いた親文字(=原エスペラント文)のみのアルファベット列。§12-Gの不変対象。
def rb_letters(h):
    h = re.sub(r"<rt[^>]*>.*?</rt>", "", h, flags=re.S)
    return re.sub(r"[^" + _ESP + r"]", "", re.sub(r"<[^>]+>", "", h))
def esp_only(s): return re.sub(r"[^" + _ESP + r"]", "", s)

total_fix = 0; sample = []; skipped = collections.Counter()
final_plan = {}
for path, cand in per_file_cand.items():
    fixes = []
    for start, end, surface, raw, segs in cand:
        rep = render.get(surface)
        if not rep or "<ruby>" not in rep: skipped["app描画不可"] += 1; continue
        if rb_letters(rep) != esp_only(surface): skipped["app親文字≠surface"] += 1; continue
        if rb_letters(raw) != esp_only(surface): skipped["span親文字≠surface"] += 1; continue
        app_segs = segments(rep)
        want = CONFIRMED[(norm(surface), cuts(segs))]
        if cuts(app_segs) != want: skipped["app描画≠確定正分解"] += 1; continue
        fixes.append((start, end, raw, rep, surface, "/".join(segs), "/".join(app_segs)))
    if fixes:
        final_plan[path] = fixes
        total_fix += len(fixes)
        for fx in fixes[:2]:
            if len(sample) < 30: sample.append((os.path.basename(path), fx[4], fx[5], fx[6]))

print(f"\n=== lemma別 出現/確定誤り一致 ===")
for lem in sorted(lemma_seen):
    print(f"  {lemma_hit[lem]:>3}/{lemma_seen[lem]:<3}  {lem}")

print(f"\n=== 修正計画 ===")
print(f"対象ファイル {len(final_plan)} / 総修正箇所 {total_fix}")
print(f"スキップ: {dict(skipped)}")
print(f"\n--- 修正サンプル(最大30) surface: コーパス分解 → アプリ分解 ---")
for fn, surf, c, a in sample:
    print(f"  [{fn[:30]:30s}] {surf:16s} {c:22s} → {a}")

if not WRITE:
    print(f"\n(dry-run。--write で適用)")
    json.dump({os.path.basename(p): [(f[5], f[6]) for f in fx] for p, fx in final_plan.items()},
              open(lp(BASE + r"\_analysis_20260625\out\_corpus_fix_plan.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("計画保存: out/_corpus_fix_plan.json")
    sys.exit(0)

# ---- 適用(後方差し替え) ----
print(f"\n=== 適用(--write) ===")
changed = 0
for path, fixes in final_plan.items():
    html = open(path, encoding="utf-8", errors="ignore").read()
    before_letters = rb_letters(html)
    before_ruby = html.count("<ruby>"); before_rtc = len(re.findall(r"<rt\b", html))
    for start, end, raw, rep, surface, cs, as_ in sorted(fixes, key=lambda x: -x[0]):
        assert html[start:end] == raw, f"span不一致 {path} {surface}"
        html = html[:start] + rep + html[end:]
    # 検証: 親文字(原エスペラント文)が完全不変か
    if rb_letters(html) != before_letters:
        print(f"  [NG rb不変違反] {os.path.basename(path)} → スキップ(書込まない)"); continue
    if html.count("<ruby>") != html.count("</ruby>") or len(re.findall(r"<rt\b", html)) != html.count("</rt>"):
        print(f"  [NG タグ収支] {os.path.basename(path)} → スキップ"); continue
    bak = path + ".bak_corpusfix"
    if not os.path.exists(bak): shutil.copy2(path, bak)
    open(path, "w", encoding="utf-8").write(html)
    changed += 1
    print(f"  [OK] {os.path.basename(path)[:46]:46s} {len(fixes)}箇所修正 (+{html.count('<ruby>')-before_ruby}ruby)")
print(f"\n修正完了: {changed}ファイル / {total_fix}箇所。各 .bak_corpusfix 退避済。")
print("次: _corpus_full_audit.py を再実行してコーパス誤り減少・無回帰を確認。")
