# -*- coding: utf-8 -*-
"""第68R: マスターexportが「ラテン維持」と定める語を、語スコープで素のラテンに固定する。
   DRY既定 / --apply。

■ 背景
  gen-g で _homonym.tsv に語スコープ付きの同音異義が追加された:
      pol  插  sep  inter/pol/i, inter/pol/aĵ/o, ekster/pol/i, ekster/pol/o, pol/i
  マスターexportもこれと整合している:
      pol/i → 插ᴾi   (数学の補間する)
      pol/a → pola   (ポーランドの: ラテン維持)
      pol/o → polo   (ラテン維持)
  ところがアプリは語根単位で 插ᴾ を当てるため、pola(ポーランドの) まで 插ᴾa になる。
  = マスターの語スコープ指定をアプリが消費していない。

■ 本スクリプトの範囲(意図的に狭い)
  マスターexportの値が **全ASCII(=ラテン維持の宣言)** である語のうち、
  ここで明示した語だけを素のラテンに固定する。
  固有名詞クラスのラテン維持328語は別台帳(_latin_maintained_adjudication_20260725.json)
  でユーザー裁定により保留中であり、本スクリプトでは扱わない。

■ 安全設計
  1. マスターexportを実際に読み、対象語の値が全ASCII(ラテン維持)であることを検証する。
     一致しなければ fail-closed で停止(思い込みで固定しない)。
  2. 追加キーは空白パディングの完全一致キー。その語形にしか発火しない。
  3. 現在の出力が実際に漢字化されている語形だけを対象にする。
"""
import json, os, re, sys, argparse
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--frozen', required=True, help='凍結マスターのディレクトリ')
ap.add_argument('--export-name', default='_漢字割当エクスポート_学習者版_20260723.tsv')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'

# 対象: (マスターexportの見出し, 素の語幹, 付ける語尾)
#   pol/a と pol/o はマスターがラテン維持。pol/i(数学の補間)だけが 插ᴾ。
#   ★pol/o は対象外。マスターには5文字語根 polo=马球(ポロ競技, polo/ĉemiz/o=ポロシャツ)が
#     別に存在し、表層 polo が pol/o(ポーランド人) と衝突している。ラテン固定すると
#     実使用語彙ゲートで polo/Polo/poloj/polon の马球が消える(実測4語)。
#     表層衝突の裁定はマスター側の管轄なので、ここでは触らず照会に回す。
LOCKS = [
    ('pol/a', 'pol', ['a', 'aj', 'an', 'ajn']),
]

exp = {}
for ln in open(LP(os.path.join(A.frozen, A.export_name)), encoding='utf-8', errors='replace'):
    f = ln.rstrip('\n').split('\t')
    if len(f) >= 4 and f[0]: exp.setdefault(f[0].strip(), f[3].strip())
print(f'マスターexport 見出し: {len(exp)}')

targets = []
for head, stem, ends in LOCKS:
    v = exp.get(head)
    if v is None:
        raise SystemExit(f'マスターexportに見出しが無い: {head!r}')
    if not v.isascii():
        raise SystemExit(f'マスターexportがラテン維持ではない: {head!r} = {v!r}')
    print(f'  {head:<10} export={v!r} → ラテン維持を確認')
    for e in ends:
        for form in (stem + e, (stem + e).upper(), stem[0].upper() + stem[1:] + e):
            targets.append(form)
targets = sorted(set(targets))
print(f'固定対象の語形: {len(targets)} 件 {targets}')

# 現在の出力を確認(漢字化されているものだけ対象にする)
sys.path.insert(0, os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA'))
import esp_text_replacement_module as M
d = json.load(open(LP(os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA',
                                   'app_data', '置換リスト_漢字.json')), encoding='utf-8'))
GL = d['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = d['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
# 前回の投入分($R68L)を外した状態で「本来どう出るか」を判定する(再実行できるように)
GG = [e for e in d[KEY] if not (len(e) > 2 and isinstance(e[2], str) and '$R68L' in e[2])]
ps = M.import_placeholders(os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA', 'app_data', 'placeholders_skip.txt'))
pl = M.import_placeholders(os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA', 'app_data', 'placeholders_localcapture.txt'))
RT = re.compile(r'<rt[^>]*>.*?</rt>', re.S); TAG = re.compile(r'<[^>]+>')
def plain(w):
    o = M.orchestrate_comprehensive_esperanto_text_replacement(
        ' ' + w + ' ', ps, GL, pl, GG, G2, 'HTML格式_Ruby文字_大小调整_汉字替换')
    return TAG.sub('', RT.sub('', o)).strip()

need = []
for w in targets:
    cur = plain(w)
    if cur != w:
        need.append((w, cur))
        print(f'  対象 {w:<10} 現在={cur!r} → ラテン固定')
if not need:
    print('固定が必要な語形は無い(既にラテン)'); sys.exit(0)
print(f'\n書換 {len(need)} 語形')
if DRY:
    print('(DRY-RUN: --apply で書込)'); sys.exit(0)

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
    """エンジンが照合時に使う「約物パディング後の形」を再現する。"""
    s = _PAD.sub(lambda m: ' ' + _BOL + m.group(1) + _BOL + ' ', s)
    return _APOS_R.sub(lambda m: m.group(0) + _BOL + ' ', s)

def splice(GG, new_rows):
    """新エントリを「自分を部分文字列として含む既存キーの直後、無ければ先頭」に差し込む。

    ★単純な先頭挿入は不可(実測): ' Pola ' を先頭に置くと語句キー ' Pola Retradio '
      より先に発火して語句単位エントリを潰す。
    ★「長さ順の位置」も不可: 全域リストは厳密な長さ降順ではないため位置が下がりすぎ、
      パディング無しの旧全語キーに負ける(ルビ側 atonio で実測)。
    ★包含判定は **パディング後の形** で行う: 'Buraku-min' はテキスト側が
      ' Buraku ␁-␁ min ' になるため、生の文字列では見えない内部一致が起きる。
    """
    cand = [(i, padkey(e[0])) for i, e in enumerate(GG)
            if isinstance(e[0], str) and (' ' in e[0].strip() or _PAD.search(e[0]))]
    groups = {}
    for r in new_rows:
        k = padkey(r[0]); p = 0
        for i, mk in cand:
            if len(mk) > len(k) and k in mk: p = max(p, i + 1)
        groups.setdefault(p, []).append(r)
    out = list(GG)
    for p in sorted(groups, reverse=True):
        out[p:p] = groups[p]
    return out

for lang in ('JA', 'ZH', 'KO'):
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_漢字.json')
    dd = json.load(open(LP(path), encoding='utf-8'))
    # 再実行できるように、前回の投入分($R68L)をいったん取り除いてから入れ直す
    gg = [e for e in dd[KEY]
          if not (len(e) > 2 and isinstance(e[2], str) and '$R68L' in e[2])]
    removed = len(dd[KEY]) - len(gg)
    used = {e[2] for e in gg if len(e) > 2}
    rows = []
    for n, (w, _cur) in enumerate(need):
        ph = f' $R68L{n:04d}{"" if lang == "JA" else lang}$ '
        if ph in used: raise SystemExit(f'placeholder collision: {ph}')
        rows.append([' ' + w + ' ', ' ' + w + ' ', ph])
    dd[KEY] = splice(gg, rows)
    atomic_file_copy(LP(path), LP(path + '.bak_preLatinLock'))
    atomic_json_dump(LP(path), dd)
    print(f'[{lang}] 語句キーの直後/先頭に挿入 {len(rows)} (旧投入 {removed} 件を除去 / '
          f'全域 {len(gg)} -> {len(dd[KEY])})')
print('適用完了')
