# -*- coding: utf-8 -*-
"""第86R: 愛称形の ZH/KO ルビ訳語が「エスペラント綴りそのもの」な4語を直す。DRY既定 / --apply。

■ 何が起きているか(全数測定 2026-07-28)
  配信ルビで **ZH 1,431箇所(異なり1,122語) / KO 1,404箇所(異なり1,108語)** が
  「訳語＝エスペラント綴り」になっている。大半は京大コーパス由来の外国固有名詞・略語で、
  日本語だけが読みを持ち、ZH/KO は綴りを置いたままになっている。

      Anjo   JA=[人名]アンヨ   ZH=[人名]Anjo   KO=[인명]Anjo

■ ★一括適用は禁止(実測した罠)
  「語根CSVに訳語がある」390件のうち**約半分は同綴りの別語**で、当てると偽の友になる。
      ARDO(人名アルド)→炽热   AVN(略:古典学園)→祖父   Ada(人名)→持续
      Aina(人名)→阿伊努      Ando(人名)→安第斯      Eskalo(雑誌名)→梯子
      Edo(江戸時代)→科       FAJRO(略:比青年集会)→火  Aŭg(略:8月)→或
  機械的な弁別子は無い。よって**一括では触らない**。

■ この回で直す範囲(閉じた4語)
  Phase 619(gen-p)がマスターで裁定した**愛称接尾辞の固有名14語**に限定する。
  この14語は語根が定義上その語自身(Anj+o, Emi+nj+o, Jo+ĉj+o, Pe+ĉj+o)であり、
  同綴り別語ではない。うち ZH/KO が未翻訳なのは京大コーパス実在の4語だけで、
  残り10語は既に正しい訳語を持つ(Janj=雅妮娅/야냐 等)＝族内の取り残しである。

      Anjo    ZH [人名]Anjo   -> [人名]安妮娅      KO [인명]Anjo   -> [인명]안야
      Eminjo  ZH [词]Eminjo   -> [词]埃米昵称      KO [어휘]Eminjo -> [어휘]에밀리오애칭
      Joĉjo   ZH [人名]Joĉjo  -> [人名]约乔        KO [인명]Joĉjo  -> [인명]요초
      Peĉjo   ZH [人名]Peĉjo  -> [人名]彼佳        KO [인명]Peĉjo  -> [인명]페챠

  訳語は**各言語の語根CSVから引くだけ**で1文字も作らない。角括弧の接頭辞は現行のまま残す
  (最小変更)。**日本語は一切触らない**(京大コーパス本体が Anjo[[人名]アンヨ]×60回 等で
  そう振っており、アプリはそれに完全一致している＝正しい)。

■ 安全設計
  1. ルビのベース(表層)と分節は**一切変えない**。訳語の文字列だけを差し替える。
  2. 差し替え対象は「訳語の実体がベースと同一(=未翻訳)」の箇所のみ。
  3. 語根CSVに訳語が無い言語があればその語ごと中止(fail-closed)。
  4. 適用後に3言語の分節が完全一致することを検証する。
  5. 既存キーの値だけを差し替える(新規キー・重複キーを作らない=冪等)。
"""
import csv, glob, json, os, re, sys, argparse
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return p if p.startswith(PFX) else PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump
from gen_replacement import load_app_replacement_helper

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
A = ap.parse_args()
DRY = not A.apply
FMT = 'HTML格式_Ruby文字_大小调整'
LISTS = ['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)',
         '二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)',
         '全域替换用のリスト(列表)型配列(replacements_final_list)']
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
BR = re.compile(r'<br\s*/?>')
BRACKET = re.compile(r'^(\[[^\]]*\])?(.*)$', re.S)

# (表層, 語根CSVのキー) — Phase 619 が裁定した14語のうち ZH/KO 未翻訳の4語
TARGETS = [('Anjo', 'anj'), ('Eminjo', 'eminj'), ('Joĉjo', 'joĉj'), ('Peĉjo', 'peĉj')]
LANGS = ('ZH', 'KO')          # ★日本語は触らない

def pairs(v):
    out = []; pos = 0
    for m in RUBY.finditer(v):
        if m.start() > pos:
            t = TAG.sub('', v[pos:m.start()])
            if t: out.append(t)
        out.append((TAG.sub('', m.group(1)), BR.sub('', TAG.sub('', m.group(2)))))
        pos = m.end()
    if pos < len(v):
        t = TAG.sub('', v[pos:])
        if t: out.append(t)
    return out

def surface(ps):
    return ''.join(p if isinstance(p, str) else p[0] for p in ps)

def load_gloss(lang):
    d = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data')
    path = max(glob.glob(os.path.join(d, '*.csv')), key=os.path.getsize)
    g = {}
    with open(LP(path), encoding='utf-8', newline='') as fh:
        for row in csv.reader(fh):
            if row and row[0].strip(): g.setdefault(row[0].strip(), row[1] if len(row) > 1 else '')
    return g, os.path.basename(path)

GL = {}
for lang in LANGS:
    GL[lang], nm = load_gloss(lang)
    print(f'[{lang}] 語根CSV: {nm} ({len(GL[lang])})')
missing = [(l, r) for l in LANGS for _, r in TARGETS if not GL[l].get(r)]
if missing:
    raise SystemExit(f'★語根CSVに訳語が無い: {missing}')
print('必要な語根訳: ' + ' / '.join(
    f'{r}=' + '·'.join(GL[l][r] for l in LANGS) for _, r in TARGETS))

plan = {}; stat = {}
for lang in LANGS:
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_ルビ.json')
    app_dir = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    helper = load_app_replacement_helper(app_dir)
    cw = json.load(open(LP(os.path.join(app_dir, 'app_data', 'char_widths.json')), encoding='utf-8'))
    d = json.load(open(LP(path), encoding='utf-8'))
    per = {}; n = 0
    for li, name in enumerate(LISTS):
        for idx, e in enumerate(d[name]):
            if not isinstance(e[0], str): continue
            ps = pairs(e[1])
            if not any(not isinstance(p, str) for p in ps): continue
            hit = False; out = []
            for p in ps:
                if isinstance(p, str): out.append(p); continue
                base, gloss = p
                tgt = next((r for w, r in TARGETS if base.lower() == w.lower()), None)
                if tgt is None: out.append(p); continue
                m = BRACKET.match(gloss)
                pre, core = (m.group(1) or ''), m.group(2).strip()
                if core.lower() != base.lower(): out.append(p); continue   # 既に翻訳済み
                out.append((base, pre + GL[lang][tgt])); hit = True
            if not hit: continue
            val = ''.join(p if isinstance(p, str)
                          else helper.output_format(p[0], p[1], FMT, cw) for p in out)
            new = pairs(val)
            if surface(new) != surface(ps):
                raise SystemExit(f'★表層が変わった {lang} {e[0]!r}')
            if [q[0] for q in new if not isinstance(q, str)] != \
               [q[0] for q in ps if not isinstance(q, str)]:
                raise SystemExit(f'★分節が変わった {lang} {e[0]!r}')
            # ★pairs() は前後の空白パディングも literal 片として拾うので、
            #   val には既にパディングが含まれている。ここで足すと二重になる
            #   (DRY-RUNの目視で « » が «  » になって発覚)。
            per[(li, idx)] = (e[0], val); n += 1
    plan[lang] = per; stat[lang] = n
    print(f'[{lang}] 差し替え対象 {n} キー')

ks = [set(v[0] for v in plan[l].values()) for l in LANGS]
if ks[0] != ks[1]:
    raise SystemExit(f'★ZH/KOで対象キーが違う: {sorted(ks[0] ^ ks[1])[:10]}')
print(f'ZH/KOの対象キー一致: ○ ({len(ks[0])} キー)')

lang0 = LANGS[0]
d0 = json.load(open(LP(os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang0}',
                                    'app_data', '置換リスト_ルビ.json')), encoding='utf-8'))
shown = set()
for (li, idx), (k, v) in sorted(plan[lang0].items()):
    old = d0[LISTS[li]][idx][1]
    def sh(x): return ''.join('«' + p + '»' if isinstance(p, str) else f'{p[0]}[{p[1]}]'
                              for p in pairs(x))
    key = k.strip().lower()
    if key in shown: continue
    shown.add(key)
    print(f'   {k.strip():<14} 現在 {sh(old)}\n   {"":<14} 以後 {sh(v)}')

if DRY:
    print('\n(DRY-RUN: --apply で書込)'); sys.exit(0)

for lang in LANGS:
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_ルビ.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    n = 0
    for (li, idx), (k, v) in plan[lang].items():
        e = d[LISTS[li]][idx]
        if e[0] != k: raise SystemExit(f'★添字がずれている {lang} {idx}')
        if e[1] == v: continue
        d[LISTS[li]][idx] = [e[0], v] + list(e[2:])
        n += 1
    atomic_file_copy(LP(path), LP(path + '.bak_preR86Z'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 値の差替 {n} 件(キー数・分節・表層は不変)')
print('適用完了 (日本語は無変更)')
