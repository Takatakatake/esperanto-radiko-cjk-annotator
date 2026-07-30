# -*- coding: utf-8 -*-
"""第92R: 語義分裂が見つかった語根について、**訳語の出所(DONOR)を機械的に探す**。
   読み取り専用。提案を出すだけで、何も書き換えない。

■ 考え方(発明ゼロ)
  マスターは「語ごとの片 -> 漢字」を与える。アプリのルビは「語ごとの片 -> 訳語」を与える。
  両者が**既に一致している語**を使えば、〔漢字 -> (JA,ZH,KO)訳語〕の対応表が**配信実績から**作れる。

      uro/log/o ⟦尿ᵁᴼ/学家/o⟧ + ルビ uro[尿]/log[学者]  ->  尿ᵁᴼ = 尿 / 尿 / 소변

  欠陥語根はマスターが与える漢字が分かっているので、この表を引けば
  **発明せずに正しい訳語の三つ組**が得られる。引けなければ「出所なし＝要ユーザー裁定」と報告する。

■ 一致の判定
  ある語について、マスターの片列(f0)とアプリのルビのベース列が**完全に一致**するときだけ採用する
  (分節が違う語は片と訳語の対応が取れないので捨てる = fail-closed)。
"""
import argparse, collections, io, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument('--export', default='')
ap.add_argument('--findings', required=True, help='audit_ruby_vs_kanji_sense_split.py の --report')
ap.add_argument('--report', default='')
A = ap.parse_args()
EXPORT = A.export or (
    r'D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学'
    r'\エスペラントの漢字化プロジェクト総結集20260630\エスペラント語根＿漢字割り当て＿20260630'
    r'\_漢字割当エクスポート_学習者版_20260723.tsv')

RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>'); BR = re.compile(r'<br\s*/?>')
SUP = 'ᴬ-ᵪ⁰-₟ʰ-˿'
STRIP_SUP = re.compile(f'[{SUP}]')
LISTS = ['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)',
         '二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)',
         '全域替换用のリスト(列表)型配列(replacements_final_list)']

# ── 1. マスター: 表層 -> (片列, 漢字列) ────────────────────────
m_pieces = {}
with io.open(LP(EXPORT), encoding='utf-8', errors='replace') as f:
    for ln in f:
        fs = ln.rstrip('\n').split('\t')
        if len(fs) < 4: continue
        pe, pk = fs[0].split('/'), fs[1].split('/')
        if len(pe) != len(pk): continue
        m_pieces[fs[2]] = (pe, pk)
print(f'マスター表層 {len(m_pieces):,}')

# ── 2. アプリのルビ: キー -> (ベース列, 訳語列) を3言語ぶん ─────────
app_r = {}
for lang in ('JA', 'ZH', 'KO'):
    d = json.load(open(LP(os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}',
                                       'app_data', '置換リスト_ルビ.json')), encoding='utf-8'))
    per = {}
    for name in LISTS:
        for e in d.get(name, []):
            if not isinstance(e[0], str): continue
            ms = list(RUBY.finditer(e[1]))
            if not ms: continue
            per[e[0].strip()] = ([TAG.sub('', m.group(1)) for m in ms],
                                 [BR.sub('', TAG.sub('', m.group(2))) for m in ms])
    app_r[lang] = per
print('ルビキー ' + ' / '.join(f'{l}={len(app_r[l]):,}' for l in ('JA', 'ZH', 'KO')))

# ── 3. 〔漢字 -> 訳語三つ組〕を**アプリ自身の2つのリスト**から作る ──────
#   同じキーについて 置換リスト_漢字 は <ruby>漢字<rt>エス語根</rt></ruby>、
#   置換リスト_ルビ は <ruby>エス語根<rt>訳語</rt></ruby> を持つ。
#   両者のエス語根の列が完全一致するキーだけを使えば、漢字 i ↔ 訳語 i が確定する。
app_k = {}
for lang in ('JA', 'ZH', 'KO'):
    d = json.load(open(LP(os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}',
                                       'app_data', '置換リスト_漢字.json')), encoding='utf-8'))
    per = {}
    for name in LISTS:
        for e in d.get(name, []):
            if not isinstance(e[0], str): continue
            ms = list(RUBY.finditer(e[1]))
            if not ms: continue
            per[e[0].strip()] = ([BR.sub('', TAG.sub('', m.group(2))) for m in ms],   # エス語根
                                 [TAG.sub('', m.group(1)) for m in ms])               # 漢字
    app_k[lang] = per
print('漢字キー ' + ' / '.join(f'{l}={len(app_k[l]):,}' for l in ('JA', 'ZH', 'KO')))

k2g = collections.defaultdict(collections.Counter)
k2src = collections.defaultdict(lambda: collections.defaultdict(list))
nkey = 0
for key, (rb, rg) in app_r['JA'].items():
    kj = app_k['JA'].get(key)
    if kj is None: continue
    if [x.lower() for x in kj[0]] != [x.lower() for x in rb]: continue   # 分節不一致は捨てる
    tri = {}
    ok = True
    for lang in ('JA', 'ZH', 'KO'):
        er, ek = app_r[lang].get(key), app_k[lang].get(key)
        if er is None or ek is None or len(er[1]) != len(rb) or len(ek[1]) != len(rb):
            ok = False; break
        tri[lang] = (er[1], ek[1])
    if not ok: continue
    nkey += 1
    for i in range(len(rb)):
        k = tri['JA'][1][i]
        if k.lower() == rb[i].lower(): continue        # ラテン維持の片
        g = tuple(tri[l][0][i] for l in ('JA', 'ZH', 'KO'))
        k2g[k][g] += 1
        k2src[k][g].append(key)
print(f'漢字→訳語 対応表: {len(k2g):,} 漢字 / 突き合わせたキー {nkey:,}\n')

# ── 4. 欠陥候補ごとに DONOR を引く ────────────────────────────
F = json.load(open(LP(A.findings), encoding='utf-8'))
out = []
for f in F['hard']:
    r = f['root']
    entry = {'root': r, 'ruby_now': {l: list(f['ruby_gloss'][l]) for l in ('JA', 'ZH', 'KO')},
             'senses': []}
    for k, n in sorted(f['master_kanji'].items(), key=lambda x: -x[1]):
        # ①そのままの漢字で引く ②引けなければセンチネル(上付き)を剥がして引く
        cand, via = k2g.get(k), k
        if not cand:
            bare = STRIP_SUP.sub('', k)
            if bare != k and k2g.get(bare): cand, via = k2g[bare], bare
        best = cand.most_common(1)[0] if cand else None
        entry['senses'].append({
            'kanji': k, 'via': via, 'words': n,
            'sample_words': sorted(set(f['words_by_kanji'].get(k, [])))[:6],
            'donor_gloss': list(best[0]) if best else None,
            'donor_support': best[1] if best else 0,
            'donor_words': sorted(set(k2src[via][best[0]]))[:5] if best else [],
        })
    out.append(entry)

print(f"{'語根':<9} {'漢字':<7}{'語数':>4}  {'DONORの訳語(JA/ZH/KO)':<34} 出所")
print('-' * 108)
for e in out:
    print(f"[{e['root']}] 現ルビ JA={e['ruby_now']['JA']} ZH={e['ruby_now']['ZH']} KO={e['ruby_now']['KO']}")
    for s in e['senses']:
        dg = ' / '.join(s['donor_gloss']) if s['donor_gloss'] else '★出所なし'
        print(f"   {'':<7}{s['kanji']:<7}{s['words']:>4}  {dg:<34} "
              f"{'×' + str(s['donor_support']) + ' ' + str(s['donor_words'][:3]) if s['donor_gloss'] else ''}")
        print(f"   {'':<7}   語: {s['sample_words']}")
if A.report:
    json.dump(out, open(LP(A.report), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\nレポート: {A.report}')
