# -*- coding: utf-8 -*-
"""第92R: ルビ軌道が**無関係な同綴り語の訳語を露出している**語を、マスターの裁定どおりに直す。
   DRY既定 / --apply。

■ 何が壊れているか(全数測定で確定)
  マスターは `ur` を2つの別語として扱っている。

      ur/o          ⟦原牛/o⟧              ← 単独の ur/o = オーロックス(絶滅した野生牛)
      ur/gener/a    ⟦尿ᵁᴿ/生ᴳᴿ/a⟧         ← ★複合語の中の ur = 尿
      uro/gener/a   ⟦尿ᵁᴼ/生ᴳᴿ/a⟧
      uro/log/o     ⟦尿ᵁᴼ/学家/o⟧   uro/grafi/o ⟦尿ᵁᴼ/志ᴳ/o⟧

  漢字軌道はこの区別を正しく実装している(尿ᵁᴿ / 尿ᵁᴼ のセンチネル付き)が、
  **ルビ軌道は `ur` に一律でオーロックスの訳語を当てていた**。

      urgener   ルビ ur[野牛] gener[生成]      ← ★誤り。漢字は 尿ᵁᴿ[ur] 生ᴳᴿ[gener]
      urogener  ルビ ur[野牛] o gener[生成]    ← ★誤り。分節も漢字(uro|gener)と違う
      urogenera ルビ uro[尿] gener[生成] a     ← これだけ正しい = アプリ内部で自己矛盾

  ★同じ族の兄弟は既に正しい: urolog*/urografi*/urogenera は uro[尿]、
    urat*(尿酸塩)は urat[尿酸塩] と融合済み。**壊れているのは gener 族の6キーだけ。**

■ 語義の根拠(発明ゼロ)
  1. マスター学習者版エクスポート  ur/gener/a -> 尿ᵁᴿ/生ᴳᴿ/a    (片 ur の漢字が 尿)
  2. アプリ自身の既存キー urogenera -> uro[尿] gener[生成] a  (訳語の出所=DONOR)
  3. 辞書側 Phase 626 の独立記述「PIV `ur/o`② の定義は *Urina aparato (en kunmetaĵoj)*
     ＝複合語の中でしか意味を持たない」「単独登録の `ur/o` は L42290＝オーロックスという
     無関係な homograph。無標分割はこれを何の警告もなく露出していた」

  ★語根CSVは引かない。CSV の `ur` は**単独義=オーロックス**なので、引くと退行する
    (aĵ/et と同型の罠。訳語は**配信中の同族キー**から採る)。

■ 巻き添えが無いことの実測
  マスター全表層 61,854 語のうち urgener/urogener を部分文字列に含むのは
  `urgenera` `urogenera` の **2語のみ**。京大コーパス 16,169 語では **0語**。
  ∴ パディング無しキーでも語境界を越えて他語を壊さない(deven* の失敗とは違う)。

■ 安全設計
  1. 片の綴りを固定表で持ち、キーの表層を切り出して小文字化したものが表と一致しなければ捨てる。
  2. 訳語は DONOR キーの現行値から採る。DONOR が期待の形に分解できなければ**全体を中止**。
  3. 第2片(gener)の訳語は現行値と DONOR が一致することを確かめる(食い違えば中止)。
  4. 組み直した値の表層が元のキーの表層と一致することを検証する(大小も保つ)。
  5. 3言語で分節(ベース列)が完全一致することを検証する。一致しなければ全体を中止。
  6. 既存キーの**値だけ**を差し替える。新規キー・重複キーは作らない(冪等)。
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

# 訳語の出所。このキーの現行値が [uro→G1, gener→G2, 'a'] に分解できることを必須とする。
DONOR = 'urogenera'
DONOR_SHAPE = ['uro', 'gener']        # ルビのベース列(この順・この綴り)
DONOR_TAIL = 'a'                       # 末尾のリテラル

# 是正対象。片の列は (語根の小文字綴り, 訳語をDONORのどのベースから採るか)。
TARGETS = [
    ('urgener',  [('ur',  'uro'), ('gener', 'gener')]),
    ('urogener', [('uro', 'uro'), ('gener', 'gener')]),
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
    for pre, pieces in TARGETS:
        if s.startswith(pre): return pre, pieces
    return None, None

# ── 計画づくり(言語ごとに独立に作り、最後に3言語で突き合わせる) ──────────
plan = {}; segof = {}; stat = collections.Counter(); skipped = []
donors = {}
for lang in ('JA', 'ZH', 'KO'):
    app_dir = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    d = json.load(open(LP(os.path.join(app_dir, 'app_data', '置換リスト_ルビ.json')),
                       encoding='utf-8'))
    helper = load_app_replacement_helper(app_dir)
    cw = json.load(open(LP(os.path.join(app_dir, 'app_data', 'char_widths.json')),
                        encoding='utf-8'))

    # ---- ① DONOR から訳語を採る(発明ゼロの起点) ----
    dg = None
    for name in LISTS:
        for e in d[name]:
            if isinstance(e[0], str) and e[0].strip() == DONOR:
                ps = parse(e[1])
                bases = [p[0] for p in ps if not isinstance(p, str)]
                tail = ''.join(p for p in ps if isinstance(p, str)).strip()
                if bases != DONOR_SHAPE or tail != DONOR_TAIL:
                    raise SystemExit(f'★DONOR {DONOR} の形が期待と違う({lang}): '
                                     f'bases={bases} tail={tail!r} : 中止')
                dg = {p[0]: p[1] for p in ps if not isinstance(p, str)}
    if dg is None:
        raise SystemExit(f'★DONOR {DONOR} が見つからない({lang}): 中止')
    donors[lang] = dg
    print(f'[{lang}] 訳語の出所 {DONOR} -> ' + ' / '.join(f'{k}[{v}]' for k, v in dg.items()))

    per = {}
    for li, name in enumerate(LISTS):
        for idx, e in enumerate(d[name]):
            if not isinstance(e[0], str): continue
            surf = e[0].strip()
            pre, pieces = famof(surf)
            if pre is None: continue
            if surf.lower() == DONOR: continue          # DONOR 自身は触らない
            cur = parse(e[1])
            if surface(cur).strip() != surf:
                skipped.append((lang, e[0], '現行値の表層がキーと違う')); continue
            # 表層を片の長さで切り出し、綴りが表と一致するか確かめる(大小はキーのまま保つ)
            segs = []; pos = 0; ok = True
            for txt, _src in pieces:
                seg = surf[pos:pos + len(txt)]; pos += len(txt)
                if seg.lower() != txt: ok = False; break
                segs.append(seg)
            if not ok:
                skipped.append((lang, e[0], '片の綴りが表と一致しない')); continue
            rest = surf[pos:]
            # ---- ② 第2片以降は「現行値の訳語」と DONOR が一致することを確かめる ----
            curg = {p[0].lower(): p[1] for p in cur if not isinstance(p, str)}
            bad = None
            for (txt, src), seg in zip(pieces, segs):
                if txt == 'gener' and txt in curg and curg[txt] != dg[src]:
                    bad = f'gener の訳語が DONOR と違う({curg[txt]!r} != {dg[src]!r})'
            if bad:
                skipped.append((lang, e[0], bad)); continue
            buf = []
            for (txt, src), seg in zip(pieces, segs):
                buf.append(helper.output_format(seg, dg[src], FMT, cw))
            buf.append(rest)
            val = ''.join(buf)
            new = parse(val)
            if surface(new) != surf:
                skipped.append((lang, e[0], '組み直した表層が不一致')); continue
            if [p[1] for p in new if not isinstance(p, str)] != [dg[s] for _t, s in pieces]:
                skipped.append((lang, e[0], '訳語が意図と違う')); continue
            # ★pairs()/parse() は前後の空白パディングも literal 片として拾うため、
            #   ここで足し直すと二重になる(第86Rで実際に踏んだ)。元値の外側の空白だけを移す。
            pad_l = e[1][:len(e[1]) - len(e[1].lstrip())]
            pad_r = e[1][len(e[1].rstrip()):]
            per[(li, idx)] = (e[0], pad_l + val + pad_r)
            segof.setdefault(e[0], {})[lang] = '/'.join(
                p[0] for p in new if not isinstance(p, str))
    plan[lang] = per
    print(f'[{lang}] 対象キー {len(per)}')

# ── DONOR の訳語が3言語で独立に採れていることの確認 ─────────────────
if len(set(tuple(sorted(donors[l].items())) for l in ('JA', 'ZH', 'KO'))) == 1:
    print('※3言語のDONOR訳語が同一(ZH/KOが未翻訳の可能性) — 内容を目視すること')

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
def sh(x):
    return ''.join('«' + p + '»' if isinstance(p, str) else f'{p[0]}[{p[1]}]' for p in parse(x))
samples = collections.defaultdict(list)
for lang in ('JA', 'ZH', 'KO'):
    d = json.load(open(LP(os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}',
                                       'app_data', '置換リスト_ルビ.json')), encoding='utf-8'))
    for (li, idx), (k, v) in sorted(plan[lang].items()):
        old = d[LISTS[li]][idx][1]
        if old.strip() == v.strip(): stat[f'{lang}:既に正しい'] += 1; continue
        stat[f'{lang}:★是正'] += 1
        samples[lang].append((k.strip(), sh(old), sh(v)))
print('内訳: ' + ' / '.join(f'{k}={v}' for k, v in sorted(stat.items())))
for lang in ('JA', 'ZH', 'KO'):
    print(f'\n[{lang}]')
    for k, o, n in samples[lang]:
        print(f'   {k}\n     現在 {o}\n     以後 {n}')
if A.report:
    json.dump({'stat': dict(stat), 'skipped': skipped, 'donor': donors,
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
    atomic_file_copy(LP(path), LP(path + '.bak_preR92U'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 値の差替 {n} 件(キー数・重複キーは不変)')
print('適用完了')
