# -*- coding: utf-8 -*-
"""第92R新設ゲート: **マスターが同綴り語根を区別しているのに、ルビ軌道が区別していない**語を
   全数で洗い出す。読み取り専用(--report で JSON 出力)。

■ なぜ要るか(第92Rで実際に取り逃していた軸)
  マスターは同じ綴りの語根に**語ごとに違う漢字**を割り当てて同綴り衝突を解決している。

      ur/o        -> 原牛/o          (オーロックス)
      ur/gener/a  -> 尿ᵁᴿ/生ᴳᴿ/a     (泌尿。同じ綴り ur だが別語)

  漢字軌道はこの区別を実装しているが、**ルビ軌道は語根CSVの単独義に倒れる**ことがあり、
  `urgenera` に「野牛」という**偽の友**が出ていた。既存の2つの忠実度ゲートは
  「分節」と「注釈の有無」しか見ないので、**訳語の中身が違ってもPASSする**=構造的な死角。

■ 検出ロジック(発明ゼロ・機械的)
  1. 学習者版エクスポートの f0(エスペラント分解)/f1(漢字分解)を片ごとに対応づけ、
     語根 -> {漢字} の多値写像を作る。**マスターが2値以上を与える語根**が「区別している語根」。
  2. 同じ語根について、アプリのルビが与える訳語を語ごとに集め、語根 -> {訳語} を作る。
  3. ★マスターが区別している(|漢字|>=2)のに、ルビが区別していない(|訳語|==1)語根を報告する。
     さらに、どの語形でどちらの語義に倒れているかを並べて、人が裁定できる形にする。

■ ★★このレンズは「候補出し」であって判定器ではない(第92Rで実測した偽陽性率)
  23件出たうち、**実際に是正できたのは epi の1語根(18キー)だけ**だった。理由は
  **ルビ軌道が粗く、複合語を語根に割らずに丸ごと融合している**から。

      マスター  albumin/uri/o ⟦白蛋白/尿/o⟧          ルビ albuminuri[蛋白尿]«o»  ← 融合・正しい
      マスター  himen/o/pter/oj ⟦膜/o/翅/oj⟧         ルビ himenopter[膜翅類]«oj» ← 融合・正しい
      マスター  kosm/o/goni/o ⟦宇/o/源ᴳᴼ/o⟧          ルビ kosmogoni[宇宙進化論]«o»← 融合・正しい

  つまり「マスターが語根を区別している」だけでは欠陥にならない。**ルビが実際にその語根を
  ベースとして露出し、かつ別語義の側に倒れている**ときだけが欠陥。
  → 判定は `fix_ruby_sense_by_kanji.py` の fail-closed 機構(同じキーの漢字片を引き、
     対象の漢字でなければ触らない)に任せる。このレンズの出力を鵜呑みにして数えない。

■ 偽陽性になりやすいもの(報告はするが自動判定はしない)
  - センチネル付き漢字(尿ᵁᴿ / 尿ᵁᴼ)は**同じ基底字**なので、剥がして数えた集合も併記する。
    基底字が1種類なら「マスターも実質1義」なので優先度は低い。
  - 語尾・接辞(o/a/j/n など)は対象外。
"""
import argparse, collections, io, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument('--export', default='')
ap.add_argument('--report', default='')
ap.add_argument('--min-words', type=int, default=1)
A = ap.parse_args()

EXPORT = A.export or (
    r'D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学'
    r'\エスペラントの漢字化プロジェクト総結集20260630\エスペラント語根＿漢字割り当て＿20260630'
    r'\_漢字割当エクスポート_学習者版_20260723.tsv')

RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>'); BR = re.compile(r'<br\s*/?>')
SUP = '\u1d2c-\u1d6a\u2070-\u209f\u02b0-\u02ff'      # センチネルに使われる上付き類
STRIP_SUP = re.compile(f'[{SUP}]')
LISTS = ['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)',
         '二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)',
         '全域替换用のリスト(列表)型配列(replacements_final_list)']
ENDINGS = {'o', 'a', 'e', 'i', 'j', 'n', 'oj', 'on', 'ojn', 'aj', 'an', 'ajn',
           'as', 'is', 'os', 'us', 'u', 'ad', 'ant', 'int', 'ont', 'at', 'it', 'ot'}

# ── 1. マスター: 語根 -> {漢字} ────────────────────────────────
root2kanji = collections.defaultdict(collections.Counter)
root2words = collections.defaultdict(lambda: collections.defaultdict(list))
nrow = 0
with io.open(LP(EXPORT), encoding='utf-8', errors='replace') as f:
    for ln in f:
        fs = ln.rstrip('\n').split('\t')
        if len(fs) < 4: continue
        eo, kj, surf = fs[0], fs[1], fs[2]
        pe, pk = eo.split('/'), kj.split('/')
        if len(pe) != len(pk): continue          # 片数が違う行は対象外(fail-closed)
        nrow += 1
        for a, b in zip(pe, pk):
            al = a.lower()
            if not al or al in ENDINGS or len(al) < 2: continue
            if a == b: continue                   # ラテン維持の片は語義を主張していない
            root2kanji[al][b] += 1
            root2words[al][b].append(surf)
print(f'マスター {nrow:,} 行 / 語根 {len(root2kanji):,} 種')

# ── 2. アプリ ルビ: 語根 -> {訳語} ─────────────────────────────
root2gloss = {}
root2keys = {}
for lang in ('JA', 'ZH', 'KO'):
    g = collections.defaultdict(collections.Counter)
    kk = collections.defaultdict(lambda: collections.defaultdict(list))
    d = json.load(open(LP(os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}',
                                       'app_data', '置換リスト_ルビ.json')), encoding='utf-8'))
    for name in LISTS:
        for e in d.get(name, []):
            if not isinstance(e[0], str): continue
            for m in RUBY.finditer(e[1]):
                b = TAG.sub('', m.group(1)).lower()
                if not b or b in ENDINGS or len(b) < 2: continue
                gl = BR.sub('', TAG.sub('', m.group(2)))
                g[b][gl] += 1
                kk[b][gl].append(e[0].strip())
    root2gloss[lang] = g
    root2keys[lang] = kk
    print(f'[{lang}] ルビのベース {len(g):,} 種')

# ── 3. マスターが区別しているのにルビが区別していない語根 ─────────────
findings = []
for r, kc in sorted(root2kanji.items()):
    if len(kc) < 2: continue
    base = {STRIP_SUP.sub('', k) for k in kc}
    langs = {}
    flat = True
    for lang in ('JA', 'ZH', 'KO'):
        gs = root2gloss[lang].get(r, {})
        langs[lang] = dict(gs)
        if len(gs) >= 2: flat = False
    if not flat: continue                          # ルビも区別している = 健全
    if not langs['JA']: continue                   # ルビに出ない語根は対象外
    nwords = sum(sum(v.values()) for v in [kc])
    if nwords < A.min_words: continue
    findings.append({
        'root': r,
        'master_kanji': dict(kc),
        'master_kanji_base': sorted(base),
        'base_distinct': len(base) >= 2,
        'words_by_kanji': {k: sorted(set(v))[:8] for k, v in root2words[r].items()},
        'ruby_gloss': langs,
    })

hard = [f for f in findings if f['base_distinct']]
soft = [f for f in findings if not f['base_distinct']]
print(f'\n★マスターが区別・ルビが単一の語根: {len(findings)} 種')
print(f'   うち漢字の**基底字まで違う**(要精査): {len(hard)} 種')
print(f'   センチネル違いのみ(優先度低)      : {len(soft)} 種')
print('\n--- 基底字まで違うもの ---')
for f in hard[:40]:
    print(f"  [{f['root']}] マスター漢字={dict(f['master_kanji'])}")
    for k, ws in f['words_by_kanji'].items():
        print(f"      {k}: {ws}")
    print(f"      ルビ JA={f['ruby_gloss']['JA']} ZH={f['ruby_gloss']['ZH']} KO={f['ruby_gloss']['KO']}")
if A.report:
    json.dump({'hard': hard, 'soft': soft}, open(LP(A.report), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'\nレポート: {A.report}')
