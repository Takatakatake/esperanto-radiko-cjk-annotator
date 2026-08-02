# -*- coding: utf-8 -*-
"""第88R: Phase 619 サイドカーの**族取り残し**を補完する(mukoz 基語)。DRY既定 / --apply。

■ 何が取り残されたか
  別セッションの Phase 619 サイドカー(19eeb29)は普通語7件を京大水準の粗いルビに直したが、
  `mukoz/aĵ`(派生語)だけを採り、**基語 `mukoz` を採らなかった**。
  gold は両方とも同じ扱いである:

      学習者版  muk/oz/o##偽分解        muk/oz/aĵ/o##偽分解
      学術版    mukoz/o                mukoz/aĵ/o

  結果、族内で描画が食い違う(実測):

      mukozaĵo -> mukoz[粘膜] aĵ[事物] o     (Phase 619 で是正済み)
      mukozo   -> muk[粘液] oz[膜] o        ★取り残し
      ※しかも同じ語根 oz が mukozo では「膜」、mukozaĵo では「症」と揺れていた。

■ 方針
  ★Phase 619 のポリシーモジュール(SHA固定・第三者の封印された証跡)には**触らない**。
    phase532 -> 558 -> 598 -> 619 と同じく、**既存の注釈名前空間に1エントリを重ねる**だけにする。
  ★訳語は Phase 619 が `mukoz/aĵ` に登録した `mukoz` の値をそのまま使う(発明ゼロ・族内で完全一致)。
      JA 粘膜 / ZH 黏膜 / KO 점막   ——gold の `muk/oz/o:【解】粘膜` とも一致する。
  ★漢字軌道は `ruby_track_only` により不変(二軌道の原則)。

■ 触るもの
  1. 分解設定.json ×3        : ["mukoz", 59000, [10語尾, word_boundary,
                                ruby_context_annotation:@phase619-ruby:mukoz, ruby_track_only]]
                               (優先度は既存規則 表層長×10000+9000 に従う。mukoz=5字 -> 59000)
  2. word_anno.json ×3 と out/word_anno_{ja,zh,ko}.json ×3 : @phase619-ruby:mukoz
  3. _word_anno_boundary_scope_manifest.json : build_word_anno_boundary_manifest.py で再生成
  4. 置換リスト_ルビ.json ×3  : 30語形(10語尾×3大小)を output_format で生成して挿入
  5. test_generation_regressions.py : ruby_track の期待集合に mukoz を追加

■ 安全設計
  - 生成した各行は「ルビを剥いだ表層＝キーの表層」を検証(fail-closed)。
  - 3言語で分節が完全一致することを検証。
  - 既存キーがあれば値を差し替え、無ければ第68Rの作法で挿入する
    (自分を部分文字列として含む既存キーの直後、無ければ先頭。包含判定は約物パディング後)。
  - 冪等(何度実行しても同じ結果)。
"""
import json, os, re, sys, argparse, collections
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return p if p.startswith(PFX) else PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump
from gen_replacement import load_app_replacement_helper
from r88_mukoz_ruby_policy import normalize_existing_payload_row

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument(
    '--no-backup', action='store_true',
    help='formal regeneration only: skip large .bak_preR88M copies',
)
A = ap.parse_args()
DRY = not A.apply
FMT = 'HTML格式_Ruby文字_大小调整'
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
BRt = re.compile(r'<br\s*/?>')
MARK = '$R88M'
STEM = 'mukoz'
ANNO_KEY = '@phase619-ruby:mukoz'
SIBLING = 'mukoz/aĵ'                       # 訳語の出所(Phase 619 が登録済み)
ENDINGS = ['o', 'oj', 'on', 'ojn', 'a', 'aj', 'an', 'ajn', 'e', 'en']
PRIORITY = len(STEM) * 10000 + 9000        # 既存規則: 表層長×10000+9000


def backup_before_write(path):
    if not A.no_backup:
        atomic_file_copy(LP(path), LP(path + '.bak_preR88M'))

# ── 約物パディング(第68Rで確定した挿入作法) ─────────────────────────
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

def splice(GG, new_rows):
    cand = [(i, padkey(e[0])) for i, e in enumerate(GG)
            if isinstance(e[0], str) and (' ' in e[0].strip() or _PAD.search(e[0]))]
    groups = collections.defaultdict(list)
    for r in new_rows:
        k = padkey(r[0]); p = 0
        for i, mk in cand:
            if len(mk) > len(k) and k in mk: p = max(p, i + 1)
        groups[p].append(r)
    out = list(GG)
    for p in sorted(groups, reverse=True):
        out[p:p] = groups[p]
    return out

def cased(s, mode):
    if mode == 'lower': return s
    if mode == 'title': return s[:1].upper() + s[1:]
    return s.upper()

# ── 訳語を Phase 619 の兄弟エントリから取る(発明ゼロ) ────────────────
GLOSS = {}
for lang in ('JA', 'ZH', 'KO'):
    wa = json.load(open(LP(os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}',
                                        'app_data', 'word_anno.json')), encoding='utf-8'))
    if SIBLING not in wa:
        raise SystemExit(f'★Phase 619 の {SIBLING} が見つからない({lang}) — 前提が崩れている')
    pair = next((p for p in wa[SIBLING] if p[0] == STEM), None)
    if pair is None:
        raise SystemExit(f'★{SIBLING} に語根 {STEM} が無い({lang})')
    GLOSS[lang] = pair[1]
    if ANNO_KEY in wa and wa[ANNO_KEY] != [[STEM, pair[1]]]:
        raise SystemExit(f'★{ANNO_KEY} が既に別の値で存在する({lang})')
print('訳語(Phase 619 の mukoz/aĵ から継承): ' +
      ' / '.join(f'{l}={GLOSS[l]}' for l in ('JA', 'ZH', 'KO')))

plan = {}; segof = {}
for lang in ('JA', 'ZH', 'KO'):
    app_dir = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    helper = load_app_replacement_helper(app_dir)
    cw = json.load(open(LP(os.path.join(app_dir, 'app_data', 'char_widths.json')),
                        encoding='utf-8'))
    rows = []
    for end in ENDINGS:
        for mode in ('lower', 'title', 'upper'):
            surf = cased(STEM, mode) + (end.upper() if mode == 'upper' else end)
            base = cased(STEM, mode)
            val = helper.output_format(base, GLOSS[lang], FMT, cw) + \
                (end.upper() if mode == 'upper' else end)
            vis = ''; pos = 0
            for m in RUBY.finditer(val):
                if m.start() > pos: vis += TAG.sub('', val[pos:m.start()])
                vis += TAG.sub('', m.group(1)); pos = m.end()
            if pos < len(val): vis += TAG.sub('', val[pos:])
            if vis != surf:
                raise SystemExit(f'★表層不一致 {lang} {surf}: {vis!r}')
            segof.setdefault(surf, {})[lang] = '/'.join(
                TAG.sub('', m.group(1)) for m in RUBY.finditer(val))
            rows.append((surf, val))
    plan[lang] = rows
    print(f'[{lang}] 生成 {len(rows)} 語形')

bad = [s for s, m in segof.items() if len(set(m.values())) != 1]
if bad: raise SystemExit(f'★3言語で分節が食い違う: {bad[:5]}')
print(f'3言語の分節一致: ○ ({len(segof)} 語形)')
print('例: ' + ' / '.join(f'{s}' for s, _ in plan["JA"][:6]))

if DRY:
    print('\n(DRY-RUN: --apply で書込)')
    sys.exit(0)

for lang in ('JA', 'ZH', 'KO'):
    app_dir = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    # (1) 置換リスト_ルビ.json
    path = os.path.join(app_dir, 'app_data', '置換リスト_ルビ.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    gg = [e for e in d[KEY]
          if not (len(e) > 2 and isinstance(e[2], str) and MARK in e[2])]
    used = {e[2] for e in gg if len(e) > 2 and isinstance(e[2], str)}
    where = {}
    for i, e in enumerate(gg):
        if isinstance(e[0], str): where.setdefault(e[0], i)
    new_rows = []; replaced = 0
    for n, (surf, val) in enumerate(plan[lang]):
        k = ' ' + surf + ' '
        j = where.get(k, where.get(surf))
        if j is not None:
            # Existing noun rows predate R88 and keep their placeholder core,
            # but all three fields must share the same word-boundary padding.
            # Updating only the rendered field makes mukoz leak into amukozo.
            gg[j] = normalize_existing_payload_row(
                gg[j], surface=surf, rendered=val,
            )
            replaced += 1; continue
        ph = f' {MARK}{n:05d}{"" if lang == "JA" else lang}$ '
        if ph in used: raise SystemExit(f'placeholder collision: {ph}')
        new_rows.append([k, ' ' + val + ' ', ph])
    d[KEY] = splice(gg, new_rows)
    backup_before_write(path)
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] ルビ: 挿入 {len(new_rows)} / 差替 {replaced}')

    # (2) 分解設定.json
    sp = os.path.join(app_dir, 'app_data', '分解設定.json')
    s = json.load(open(LP(sp), encoding='utf-8'))
    flags = ENDINGS + ['word_boundary',
                       f'ruby_context_annotation:{ANNO_KEY}', 'ruby_track_only']
    idx = next((i for i, e in enumerate(s)
                if isinstance(e, list) and e and e[0] == SIBLING), None)
    if idx is None: raise SystemExit(f'★分解設定に {SIBLING} が無い({lang})')
    exist = next((i for i, e in enumerate(s) if isinstance(e, list) and e and e[0] == STEM), None)
    if exist is None:
        s.insert(idx, [STEM, PRIORITY, flags])
        act = '挿入'
    else:
        s[exist] = [STEM, PRIORITY, flags]; act = '更新'
    backup_before_write(sp)
    # ★分解設定.json は indent=1 の可読JSON。atomic_json_dump の既定(indent=None)で
    #   書くと 44,135行が1行に潰れ、差分が読めなくなる(第88Rで実際に踏んだ)。
    atomic_json_dump(LP(sp), s, indent=1)
    print(f'[{lang}] 分解設定: {act} ["{STEM}", {PRIORITY}, …]')

    # (3) word_anno.json と out/ の鏡
    for wp in (os.path.join(app_dir, 'app_data', 'word_anno.json'),
               os.path.join(ROOT, '_analysis_20260625', 'out',
                            f'word_anno_{lang.lower()}.json')):
        w = json.load(open(LP(wp), encoding='utf-8'))
        w[ANNO_KEY] = [[STEM, GLOSS[lang]]]
        backup_before_write(wp)
        atomic_json_dump(LP(wp), w)
    print(f'[{lang}] word_anno: {ANNO_KEY} = {GLOSS[lang]} (配信＋out鏡)')
print('適用完了 — 続けて build_word_anno_boundary_manifest.py で台帳を再生成すること')
