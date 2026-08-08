# -*- coding: utf-8 -*-
"""第120R: ルビ軌道×コーパス実使用語彙の分節健全性スイープ(初)で見つかった
   単独語形の人名ガーブル(Kanae→Kan[アシ]ae)を裸化する。DRY既定 / --apply。

■ 診断(2026-08-08, scratchpad r120_ruby_corpus_sweep.py)
  検査対象8,819語(マスター表層から導出可能なコーパス語)で境界違反3・無注釈14。
  - spirante=呼吸の意でアプリが正(摩擦音spirant/oとの裸同綴り・第118Rコーパス実文確認済)
  - mine=コーパス実文0件(語彙抽出アーティファクト) → 据置
  - 無注釈14=人名・独語・外来断片でルビ無しが正 → 据置
  - ★真の欠陥は Kanae(村上かなえ・実文1件)のみ。
■ 前提の実測: 実文の句 'MURAKAMI (poste HIROSE) Kanae' は京大由来の**句スコープキー**が
  既にGGに存在し [人名]村上（後の広瀬）かなえ と正しく描画される。壊れるのは単独入力時のみ。
  本裸化キーはspliceの包含判定により句キーの**直後**に入るため、句の描画には一切影響しない。
■ 是正: ' Kanae '(と、現に壊れていれば ' Kanaen ')→ 恒等(ルビ無し)。3言語同一。冪等($R120K)。
  漢字軌道は第118Rで同名をラテン恒等化済みであり、両軌道の単独入力挙動が揃う。
"""
import json, os, re, sys, argparse
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AN = os.path.join(ROOT, '_analysis_20260625')
sys.path.insert(0, AN)
from atomic_json import atomic_file_copy, atomic_json_dump

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
TAGID = '$R120K'
CANDS = ['Kanae', 'Kanaen']

RT = re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>'); TAG = re.compile(r'<[^>]+>')
def disp(seg): return TAG.sub('', RT.sub('', seg)).strip()

sys.path.insert(0, os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA'))
import esp_text_replacement_module as M
DATA = {}
for lang in ('JA', 'ZH', 'KO'):
    p = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_ルビ.json')
    DATA[lang] = (p, json.load(open(LP(p), encoding='utf-8')))
def strip_mine(gg):
    return [e for e in gg if not (len(e) > 2 and isinstance(e[2], str) and TAGID in e[2])]

d0 = DATA['JA'][1]
GGm = strip_mine(d0[KEY])
GL = d0['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = d0['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
appj = os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA')
ps_ = M.import_placeholders(os.path.join(appj, 'app_data', 'placeholders_skip.txt'))
pl_ = M.import_placeholders(os.path.join(appj, 'app_data', 'placeholders_localcapture.txt'))
def render(t, gg):
    return M.orchestrate_comprehensive_esperanto_text_replacement(
        ' ' + t + ' ', ps_, GL, pl_, gg, G2, 'HTML格式_Ruby文字_大小调整')

targets = []
for w in CANDS:
    o = render(w, GGm)
    if '<ruby>' in o:
        targets.append(w); print(f'対象 {w}: 現在={disp(o)} + ルビあり → 裸化')
    else:
        print(f'skip {w}: 既に裸({disp(o)})')
if not targets:
    print('対象なし'); sys.exit(0)

PHRASE = 'MURAKAMI (poste HIROSE) Kanae'
before_phrase = render(PHRASE, GGm)

_BOL = chr(1)
_HAT12 = ''.join(chr(c) for c in (264, 265, 284, 285, 292, 293, 308, 309, 348, 349, 364, 365))
_LATEXT = chr(192) + '-' + chr(214) + chr(216) + '-' + chr(246) + chr(248) + '-' + chr(591)
_APOS = chr(39) + chr(8217)
_KEEP = ('A-Za-z0-9' + _HAT12 + _LATEXT + chr(37) + chr(64) + _APOS
         + ' ' + chr(10) + chr(13) + chr(1))
_PAD = re.compile('([^' + _KEEP + '])')
_LTR = 'A-Za-z' + _HAT12 + _LATEXT
_APOS_R = re.compile('[' + _APOS + '](?=[' + _LTR + '])')
def padkey(s):
    s = _PAD.sub(lambda m: ' ' + _BOL + m.group(1) + _BOL + ' ', s)
    return _APOS_R.sub(lambda m: m.group(0) + _BOL + ' ', s)
def splice(gg, new_rows):
    cand_ = [(i, padkey(e[0])) for i, e in enumerate(gg)
             if isinstance(e[0], str) and (' ' in e[0].strip() or _PAD.search(e[0]))]
    groups = {}
    for r in new_rows:
        k = padkey(r[0]); p = 0
        for i, mk in cand_:
            if len(mk) > len(k) and k in mk: p = max(p, i + 1)
        groups.setdefault(p, []).append(r)
    out = list(gg)
    for p in sorted(groups, reverse=True):
        out[p:p] = groups[p]
    return out

# ★プレースホルダに可読語(SIM/TEST等)を使うと実在キーに食われて復元不能になる(第120R実測)。
#   実績形式($R…数字…$)のみ使用可。
sim = splice(GGm, [[' ' + w + ' ', ' ' + w + ' ', f' $R120T9{n:02d}$ ']
                   for n, w in enumerate(targets)])
for w in targets:
    o = render(w, sim)
    if '<ruby>' in o or disp(o) != w:
        raise SystemExit(f'fail-closed: {w} 裸化されず: {disp(o)}')
after_phrase = render(PHRASE, sim)
if after_phrase != before_phrase:
    raise SystemExit('fail-closed: 句スコープ描画が変化した(順序違反)')
print(f'シミュレーションOK: 単独{targets}は裸化・句 {PHRASE!r} の描画は不変')

if DRY:
    print('(DRY-RUN: --apply で書込)'); sys.exit(0)

for lang in ('JA', 'ZH', 'KO'):
    path, dd = DATA[lang]
    gg = strip_mine(dd[KEY])
    removed = len(dd[KEY]) - len(gg)
    used = {e[2] for e in gg if len(e) > 2}
    rows = []
    for n, w in enumerate(targets):
        ph = f' {TAGID}{n:02d}{"" if lang == "JA" else lang}$ '
        if ph in used: raise SystemExit(f'placeholder collision: {ph}')
        rows.append([' ' + w + ' ', ' ' + w + ' ', ph])
    dd[KEY] = splice(gg, rows)
    atomic_file_copy(LP(path), LP(path + '.bak_preR120'))
    atomic_json_dump(LP(path), dd)
    print(f'[{lang}] 挿入 {len(rows)} (旧{TAGID} {removed} 件除去 / 全域 {len(gg)} -> {len(dd[KEY])})')
print('適用完了。ルビ4ゲート(62k/実使用語彙/京大粗さ/粗大化)を回すこと。')
