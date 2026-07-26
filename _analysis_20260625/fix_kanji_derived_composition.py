# -*- coding: utf-8 -*-
"""第69R補遺: マスターに見出しが無い派生語について、漢字の合成順序の誤りを是正する。
   DRY既定 / --apply。

■ 対象(意図的に狭い)
  マスターの `_漢字割当エクスポート` に見出しが**無い**生産的派生語のうち、
  アプリの漢字合成が語頭を食っているもの。

    teatristoj  tea + 悲ᵀˢ(trist)        → 剧(teatr) + 家(ist)
    povuloj     p   + 卵(ov) + 者(ul)     → 能(pov) + 者(ul)
    paperaĵojn  p   + 现ᴬ(aper) + 物(aĵ)  → 纸(paper) + 物(aĵ)
    ŝtatuloj    網纱(tul)                → 国ˢ̂(ŝtat) + 者(ul)
    portan      直角(ort)                → 运(port)
    terara      错(erar)                 → 地(ter) + 群(ar)
    monulo      零(nul)                  → 钱(mon) + 者(ul)

  ★マスターに見出しがある語は**対象外**。マスター自身が深く割っている場合
    (procento → pro/cent/o → pro百o、erudito → erud/it/o → erud受o、
     urato → ur/at/o → ur盐ᴬo)、それは偽分解を尊重した意図的な割り当てであり、
    ルビ側の粗い分節(procent / erudit / urat)に合わせてはならない。
    この取り違えで当初 41 件を「欠陥」と誤検出した。

■ 権威
  分節  … ルビ軌道(第68R/69Rで是正済み)の語根列
  漢字  … マスター由来の語根→漢字表(out/kanji_root.csv = resync がマスターから生成)
  漢字が無い語根は素のラテンにする。訳語も漢字も発明しない。

■ 安全設計
  1. マスターexportに見出しがある語は触らない(fail-closed)。
  2. 構築後、rt(エス語根)+素片が表層と一致することを検証する。
  3. 追加キーは空白パディングの完全一致キー。挿入位置は「自分を部分文字列として含む
     既存キーの直後、無ければ先頭」。包含判定は約物パディング後の形で行う。
  4. 再実行できるように、前回の投入分($R69D)を外して測り、入れ直す。
"""
import json, os, re, sys, argparse, collections, hashlib
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump
from gen_replacement import load_app_replacement_helper

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--frozen', required=True)
ap.add_argument('--targets', required=True, help='kanji_headtrunc_true.json')
ap.add_argument('--export-name', default='_漢字割当エクスポート_学習者版_20260723.tsv')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
FMT = 'HTML格式_Ruby文字_大小调整_汉字替换'
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>'); BR = re.compile(r'<br\s*/?>')

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

# ── マスター: 見出し集合 と 語根→漢字 ──────────────────────────────
EXPW = set()
for ln in open(LP(os.path.join(A.frozen, A.export_name)), encoding='utf-8', errors='replace'):
    f = ln.rstrip('\n').split('\t')
    if len(f) >= 4: EXPW.add(circ(f[2].strip()))
K2 = {}
for ln in open(LP(os.path.join(ROOT, '_analysis_20260625', 'out', 'kanji_root.csv')),
                encoding='utf-8', errors='replace'):
    f = [x.strip().strip('"') for x in ln.rstrip('\n').split(',')]
    if len(f) >= 2 and f[0]: K2.setdefault(f[0], f[1])
print(f'マスター見出し {len(EXPW)} / 語根→漢字 {len(K2)}')

# ── アプリ ─────────────────────────────────────────────────────
app_dir = os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA')
sys.path.insert(0, app_dir)
import esp_text_replacement_module as M
helper = load_app_replacement_helper(app_dir)
with open(LP(os.path.join(app_dir, 'app_data', 'char_widths.json')), encoding='utf-8') as fp:
    CW = json.load(fp)
def load(mode):
    f = '置換リスト_ルビ.json' if mode == 'ruby' else '置換リスト_漢字.json'
    d = json.load(open(LP(os.path.join(app_dir, 'app_data', f)), encoding='utf-8'))
    GG = d[KEY]
    if mode == 'kanji':
        GG = [e for e in GG if not (len(e) > 2 and isinstance(e[2], str) and '$R69D' in e[2])]
    return (d['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)'],
            d['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)'], GG)
ps = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_skip.txt'))
pl = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_localcapture.txt'))
GLr, G2r, GGr = load('ruby'); GLk, G2k, GGk = load('kanji')
def conv_ruby(t):
    return M.orchestrate_comprehensive_esperanto_text_replacement(
        t, ps, GLr, pl, GGr, G2r, 'HTML格式_Ruby文字_大小调整')
def conv_kanji(t):
    return M.orchestrate_comprehensive_esperanto_text_replacement(
        t, ps, GLk, pl, GGk, G2k, FMT)
def kanji_surface(h):
    return TAG.sub('', re.sub(r'<rt[^>]*>.*?</rt>', '', h, flags=re.S)).strip()

# ── 対象 ───────────────────────────────────────────────────────
# ── 除外(実測で不適切と判断) ────────────────────────────────────
EXCLUDE = {
    # マスターは単数 procento を pro/cent/o -> pro百o と割る。複数形だけ 率oj にすると
    # **マスターの単数形と食い違う**。マスターの分解に合わせて据え置く。
    'procentoj': 'マスター単数 procento=pro百o と整合させる',
    'procentojn': '同上', 'procenton': '同上',
    # rakontis のタイポ断片。rak(架)も kon(认)も無意味。
    'rakonis': 'コーパスのタイポ断片(rakontis)。どの語根も当てはまらない',
    # 標準語形でない断片。
    'kili': '標準語形でない断片',
}
tg = json.load(open(LP(A.targets), encoding='utf-8'))
targets = [x['w'] for x in tg
           if x['cls'] == 'ordinary' and x['w'] not in EXPW and x['w'] not in EXCLUDE]
if EXCLUDE: print('除外: ' + ' / '.join(f'{k}({v[:24]})' for k, v in EXCLUDE.items()))
print(f'対象候補(普通の語・マスターに見出し無し): {len(targets)}  {targets}')

entries, skipped = [], []
for w in targets:
    rb = conv_ruby(' ' + w + ' ').strip()
    # ルビ出力を (種別, 表層片) の列に分解する
    pieces, pos = [], 0
    for m in RUBY.finditer(rb):
        if m.start() > pos:
            b = TAG.sub('', rb[pos:m.start()])
            if b: pieces.append(('B', b))
        pieces.append(('R', TAG.sub('', m.group(1))))
        pos = m.end()
    if pos < len(rb):
        b = TAG.sub('', rb[pos:])
        if b: pieces.append(('B', b))
    if ''.join(t for _, t in pieces) != w:
        skipped.append((w, 'ルビ出力から表層を再構成できない')); continue
    buf, used = [], 0
    for kind, t in pieces:
        if kind == 'B': buf.append(t); continue
        kan = K2.get(t) or K2.get(t.lower())
        if not kan or kan == t: buf.append(t); continue      # 漢字が無い語根は素のラテン
        # 大文字語形では漢字側の大小は無関係。エス語根はそのまま rt に載せる
        buf.append(helper.output_format(t, kan, FMT, CW)); used += 1
    if not used:
        skipped.append((w, '使える漢字が1つも無い')); continue
    val = ''.join(buf)
    # 検証: rt(エス語根)+素片 が表層と一致するか
    esp, pos = [], 0
    for m in RUBY.finditer(val):
        if m.start() > pos: esp.append(TAG.sub('', val[pos:m.start()]))
        esp.append(BR.sub('', TAG.sub('', m.group(2)))); pos = m.end()
    if pos < len(val): esp.append(TAG.sub('', val[pos:]))
    if ''.join(esp) != w:
        skipped.append((w, '表層の再構成に失敗')); continue
    cur = conv_kanji(' ' + w + ' ').strip()
    if kanji_surface(cur) == kanji_surface(val):
        skipped.append((w, '変化なし')); continue
    entries.append([' ' + w + ' ', ' ' + val + ' ', None])
    print(f'   {w:<20} {kanji_surface(cur)[:24]:<24} -> {kanji_surface(val)[:24]}')

# 大小変種
base = list(entries)
for k, v, _ in base:
    w = k.strip()
    for vv in (w[0].upper() + w[1:], w.upper()):
        if vv == w or any(e[0].strip() == vv for e in entries): continue
        rb = conv_ruby(' ' + vv + ' ').strip()
        pieces, pos = [], 0
        for m in RUBY.finditer(rb):
            if m.start() > pos:
                b = TAG.sub('', rb[pos:m.start()])
                if b: pieces.append(('B', b))
            pieces.append(('R', TAG.sub('', m.group(1)))); pos = m.end()
        if pos < len(rb):
            b = TAG.sub('', rb[pos:])
            if b: pieces.append(('B', b))
        if ''.join(t for _, t in pieces) != vv: continue
        buf, used = [], 0
        for kind, t in pieces:
            if kind == 'B': buf.append(t); continue
            kan = K2.get(t) or K2.get(t.lower())
            if not kan or kan == t: buf.append(t); continue
            buf.append(helper.output_format(t, kan, FMT, CW)); used += 1
        if not used: continue
        val = ''.join(buf)
        esp, pos = [], 0
        for m in RUBY.finditer(val):
            if m.start() > pos: esp.append(TAG.sub('', val[pos:m.start()]))
            esp.append(BR.sub('', TAG.sub('', m.group(2)))); pos = m.end()
        if pos < len(val): esp.append(TAG.sub('', val[pos:]))
        if ''.join(esp) != vv: continue
        if kanji_surface(conv_kanji(' ' + vv + ' ')) == kanji_surface(val): continue
        entries.append([' ' + vv + ' ', ' ' + val + ' ', None])
print(f'\n追加キー: {len(entries)} 件 (大小変種込み) / 見送り {len(skipped)}')
for w, r in skipped: print(f'   見送り {w:<20} {r}')

if DRY:
    print('\n(DRY-RUN: --apply で書込)'); sys.exit(0)

for lang in ('JA', 'ZH', 'KO'):
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_漢字.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    gg = [e for e in d[KEY]
          if not (len(e) > 2 and isinstance(e[2], str) and '$R69D' in e[2])]
    removed = len(d[KEY]) - len(gg)
    used_ph = {e[2] for e in gg if len(e) > 2}
    where = {}
    for i, e in enumerate(gg):
        if isinstance(e[0], str) and e[0] not in where: where[e[0]] = i
    rows, replaced = [], 0
    for n, (k, v, _) in enumerate(entries):
        j = where.get(k)
        if j is not None:
            gg[j] = [k, v, gg[j][2]]; replaced += 1; continue
        ph = f' $R69D{n:04d}{"" if lang == "JA" else lang}$ '
        if ph in used_ph: raise SystemExit(f'placeholder collision: {ph}')
        rows.append([k, v, ph])
    d[KEY] = splice(gg, rows)
    atomic_file_copy(LP(path), LP(path + '.bak_preR69D'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 挿入 {len(rows)} / 差替 {replaced} (旧投入 {removed} 除去 / '
          f'全域 {len(gg)} -> {len(d[KEY])})')
print('適用完了')
