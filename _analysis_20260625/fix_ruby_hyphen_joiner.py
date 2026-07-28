# -*- coding: utf-8 -*-
"""第85R: ハイフン複合語で**継ぎ目の母音がルビのベースに食い込む**欠陥を語スコープで直す。
   DRY既定 / --apply。

■ 何が壊れているか(全数測定で確定)
  配信ルビの <ruby>ベース にハイフンを含むものは3言語とも 310 種。うち
  **「母音-」で始まり、かつ同じ語の中でそれより前に別のルビがある**ものが 18 種あり、
  これらは直前の形態素の文法語尾(o/i)を自分のベースに巻き込んでいる。

      gaŭlo-romiano   gaŭl[ガリア] + o-rom[ローマ] + ian[成員]      ★
      oto-rino-…      ot[耳] + o-rin[鼻] + o-laring[喉頭] + …      ★
      saksio-anhalto  saksi[ザクセン] + o-anhalt[アンハルト]        ★
      aŭstri-hungario aŭstr[オーストリア] + i-hungari[ハンガリー]   ★
      reti-romanĉa    ret[網] + i-romanĉ[ロマンシュ]                ★

  ★各族の**主格単数の語形だけは既に正しい**(` Saksio-Anhalto ` は
    Saks[ザクセン]«io-»Anhalt[アンハルト]«o» と振れている)。
    壊れているのは同じ族の**語尾変化形・大小変種 193 キー**であり、
    「見出しだけ直して語尾変化形を落とす」型の取り残しそのものである。

■ 正しい境界の根拠(発明ゼロ)
  マスター(学習者版 gold / 漢字割当エクスポート)の片は継ぎ目の母音を**語根の外**に置く。

      ot/o-rin/o-laring/o/log/o   ⟦耳ᴼᵀ/o-鼻ᴿ/o-喉ᴸ/o/学家/o⟧
        -> 漢字は rin にだけ掛かり `o-` はラテンのまま = 語根は rin
      Saks/i/o-Anhalt/o           Au^str/i-Hungar/i/o    ret/i-romanc^/a

  よって語根は ot,rin,laring,log / Saks,Anhalt / Aŭstr,Hungar / ret,romanĉ であり、
  `o-` `io-` `i-` は継ぎ目のリテラルである。

■ gen-o(Phase 613)の追随を1件含む
      Gau^l/o-Rom/i/an/o ##偽分解  (学習者版)
      Gau^l/o-Romi/an/o            (学術版・Phase 613 で Rom/i -> Romi に是正)
  ルビ軌道は粗い側(学術版)に倣うので `Romi` を1語根として扱う。

■ ★訳語は1文字も作らない・変えない
  各キーの**現行の値から (ベース, 訳語) の対を順に取り出し、訳語をそのまま**使う。
  境界だけを動かす。語根CSVは引かない。
    実測した罠: CSV の ot は「受動将然」、log は「気を引く」であり、
    この複合語で配信中の 耳 / 学者 とは別物。CSV から引き直すと**退行**する。

■ 安全設計
  1. 各族について「片の綴り(小文字)」を固定表で持ち、キーの表層を切り出して
     小文字化したものが表と一致しなければその語を捨てる(fail-closed)。
  2. 現行値のルビ数が族の語根数と一致しなければ捨てる。
  3. 組み直した値の表層(ルビを剥いだもの)が元のキーの表層と一致することを検証する。
  4. 訳語の集合が変わっていないことを検証する。
  5. 3言語で分節(ベース列)が完全一致することを検証する。一致しなければ全体を中止。
  6. 既存キーの**値だけ**を差し替える。新規キー・重複キーは作らない。
     (何度実行しても同じ結果になる=冪等)
"""
import json, os, re, sys, argparse, collections
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump
from gen_replacement import load_app_replacement_helper

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--report', default='')
A = ap.parse_args()
DRY = not A.apply
FMT = 'HTML格式_Ruby文字_大小调整'
LISTS = ['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)',
         '二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)',
         '全域替换用のリスト(列表)型配列(replacements_final_list)']
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
BR = re.compile(r'<br\s*/?>')

R, L = 'R', 'L'          # R=語根(ルビを振る) / L=継ぎ目や語尾(素のラテン)
FAMILIES = [
    # (照合する接頭辞(小文字), 片の列 [(種別, 小文字綴り)])
    ('aŭstri-hungar',   [(R, 'aŭstr'), (L, 'i-'), (R, 'hungar')]),
    ('oto-rino-laring', [(R, 'ot'), (L, 'o-'), (R, 'rin'), (L, 'o-'),
                         (R, 'laring'), (L, 'o'), (R, 'log')]),
    ('reti-romanĉ',     [(R, 'ret'), (L, 'i-'), (R, 'romanĉ')]),
    ('saksio-anhalt',   [(R, 'saks'), (L, 'io-'), (R, 'anhalt')]),
    ('gaŭlo-romi',      [(R, 'gaŭl'), (L, 'o-'), (R, 'romi'), (R, 'an')]),
]

def parse(v):
    """値を [literal | (ベース, 訳語)] の列に分解する。"""
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

def famof(surf):
    s = surf.lower()
    for pre, pieces in FAMILIES:
        if s.startswith(pre): return pre, pieces
    return None, None

# ── 計画づくり(言語ごとに独立に作り、最後に3言語で突き合わせる) ──────────
plan = {}; segof = {}; stat = collections.Counter(); skipped = []
for lang in ('JA', 'ZH', 'KO'):
    app_dir = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    d = json.load(open(LP(os.path.join(app_dir, 'app_data', '置換リスト_ルビ.json')),
                       encoding='utf-8'))
    helper = load_app_replacement_helper(app_dir)
    cw = json.load(open(LP(os.path.join(app_dir, 'app_data', 'char_widths.json')),
                        encoding='utf-8'))
    per = {}
    for li, name in enumerate(LISTS):
        for idx, e in enumerate(d[name]):
            if not isinstance(e[0], str): continue
            surf = e[0].strip()
            pre, pieces = famof(surf)
            if pre is None: continue
            cur = parse(e[1])
            if surface(cur).strip() != surf:
                skipped.append((lang, e[0], '現行値の表層がキーと違う')); continue
            nroot = sum(1 for k, _ in pieces if k == R)
            gl = [p[1] for p in cur if not isinstance(p, str)]
            if len(gl) != nroot:
                skipped.append((lang, e[0], f'ルビ数 {len(gl)} != 語根数 {nroot}')); continue
            # 表層を片の長さで切り出し、綴りが表と一致するか確かめる
            segs = []; pos = 0; ok = True
            for kind, txt in pieces:
                seg = surf[pos:pos + len(txt)]; pos += len(txt)
                if seg.lower() != txt: ok = False; break
                segs.append((kind, seg))
            if not ok:
                skipped.append((lang, e[0], '片の綴りが表と一致しない')); continue
            rest = surf[pos:]
            gi = 0; buf = []
            for kind, seg in segs:
                if kind == L: buf.append(seg); continue
                buf.append(helper.output_format(seg, gl[gi], FMT, cw)); gi += 1
            buf.append(rest)
            val = ''.join(buf)
            new = parse(val)
            if surface(new) != surf:
                skipped.append((lang, e[0], '組み直した表層が不一致')); continue
            if [p[1] for p in new if not isinstance(p, str)] != gl:
                skipped.append((lang, e[0], '訳語が変わった')); continue
            pad_l = e[1][:len(e[1]) - len(e[1].lstrip())]
            pad_r = e[1][len(e[1].rstrip()):]
            per[(li, idx)] = (e[0], pad_l + val + pad_r)
            segof.setdefault(e[0], {})[lang] = '/'.join(
                p[0] for p in new if not isinstance(p, str))
    plan[lang] = per
    print(f'[{lang}] 対象キー {len(per)}')

# ── 3言語で分節が完全一致することの検証(ユーザーの絶対要件) ────────────
keys = [set(v[0] for v in plan[l].values()) for l in ('JA', 'ZH', 'KO')]
if not (keys[0] == keys[1] == keys[2]):
    raise SystemExit('★3言語で対象キー集合が違う: 中止')
bad = [k for k, m in segof.items() if len(set(m.values())) != 1]
if bad:
    for k in bad[:5]: print('  ', k, segof[k])
    raise SystemExit(f'★分節が3言語で食い違う {len(bad)} 件: 中止')
print(f'3言語の分節一致: ○ ({len(segof)} キー)')

# ── 変化の内訳 ────────────────────────────────────────────────
n_change = 0
samples = collections.defaultdict(list)
for lang in ('JA',):
    d = json.load(open(LP(os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA',
                                       'app_data', '置換リスト_ルビ.json')), encoding='utf-8'))
    for (li, idx), (k, v) in plan[lang].items():
        old = d[LISTS[li]][idx][1]
        if old.strip() == v.strip(): stat['既に正しい'] += 1; continue
        stat['★是正'] += 1; n_change += 1
        pre, _ = famof(k.strip())
        if len(samples[pre]) < 3:
            def sh(x): return ''.join(
                '«' + p + '»' if isinstance(p, str) else f'{p[0]}[{p[1]}]' for p in parse(x))
            samples[pre].append((k.strip(), sh(old), sh(v)))
print('内訳: ' + ' / '.join(f'{k}={v}' for k, v in stat.most_common()))
for pre, ss in samples.items():
    print(f'\n[{pre}]')
    for k, o, n in ss:
        print(f'   {k}\n     現在 {o}\n     以後 {n}')
if A.report:
    json.dump({'stat': dict(stat), 'skipped': skipped,
               'samples': {k: v for k, v in samples.items()}},
              open(LP(A.report), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if skipped:
    print(f'\nskip {len(skipped)} 件')
    for s in skipped[:8]: print('   ', s)

if DRY:
    print('\n(DRY-RUN: --apply で書込)'); sys.exit(0)

for lang in ('JA', 'ZH', 'KO'):
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_ルビ.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    n = 0
    for (li, idx), (k, v) in plan[lang].items():
        e = d[LISTS[li]][idx]
        if e[0] != k: raise SystemExit(f'★添字がずれている {lang} {idx} {e[0]!r} != {k!r}')
        if e[1] == v: continue
        d[LISTS[li]][idx] = [e[0], v] + list(e[2:])
        n += 1
    atomic_file_copy(LP(path), LP(path + '.bak_preR85J'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 値の差替 {n} 件(キー数・重複キーは不変)')
print('適用完了')
