# -*- coding: utf-8 -*-
"""★マスター62,313見出しに日中韓ルビが適切に振れているかを全数で測る(第90R新設)。

ユーザーの常設質問「62000語以上あるマスターに、きちんと日中韓語のルビを適切に
振ることができているのか」に直接答えるための測定器。既存の
`audit_master_3lang_fast.py`(3字以上55,383語・分節一致のみ)と
`audit_master_3lang_full_snapshot.py`(正式ゲート・多数のSHAピンが必要)では
測っていない**カバレッジ・空グロス・言語間の非対称**まで見る。

測る軸
  1. 3言語で分節(ルビのベース列)が完全一致するか   ← ユーザーの絶対要件
  2. 注釈カバレッジ(1つ以上ルビが付いた表層の割合)
  3. 空の <rt>(訳語が空)が無いか
  4. ★JAだけ振れて ZH/KO が無注釈 / その逆 が無いか(言語間の非対称)

  usage: audit_ruby_master_62k_coverage.py [--gold <学習者版gold>] [--report out.json]
         gold は既定で ESP_GOLD_PATH、無ければ作者環境のパスを使う。

第90R(gen-q)実測: 表層62,046 / 分節不一致0 / カバレッジ99.832%(3言語同一) /
空rt 0 / 非対称0。無注釈104件は全て「ハイフン付き接辞見出し58・1-2文字の語尾や
文字名29・ドット付き略語12・感嘆符付き間投詞3・SATano(衝突語)・nor(第79Rで意図的除外)」
であり、単独で文中に現れる実在語のカバレッジは実質100%である。
"""
import argparse, io, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92) * 2 + chr(63) + chr(92)
def LP(p): return p if p.startswith(PFX) else PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_GOLD = (r'D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学'
                r'\エスペラントの漢字化プロジェクト総結集20260630'
                r'\エスペラント辞書徹底語根分解_20260630'
                r'\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt')
X = {'c^': 'ĉ', 'g^': 'ĝ', 'h^': 'ĥ', 'j^': 'ĵ', 's^': 'ŝ', 'u^': 'ŭ',
     'C^': 'Ĉ', 'G^': 'Ĝ', 'H^': 'Ĥ', 'J^': 'Ĵ', 'S^': 'Ŝ', 'U^': 'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
BRt = re.compile(r'<br\s*/?>')
FMT = 'HTML格式_Ruby文字_大小调整'

ap = argparse.ArgumentParser()
ap.add_argument('--gold', default=os.environ.get('ESP_GOLD_PATH') or DEFAULT_GOLD)
ap.add_argument('--report', default='')
ap.add_argument('--batch-size', type=int, default=500)
A = ap.parse_args()

heads = []
with io.open(LP(A.gold), encoding='utf-8', errors='replace') as f:
    for ln in f:
        h = ln.split(':', 1)[0]
        if h: heads.append(circ(h))
print(f'gold 見出し {len(heads)}  ({os.path.basename(A.gold)})')
surf = sorted({h.replace('/', '') for h in heads if h.replace('/', '').strip()})
print(f'重複除去した表層 {len(surf)}')

res = {}
for lang in ('JA', 'ZH', 'KO'):
    app_dir = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    for name in list(sys.modules):
        if name == 'esp_text_replacement_module': del sys.modules[name]
    sys.path.insert(0, app_dir)
    import esp_text_replacement_module as M
    d = json.load(open(LP(os.path.join(app_dir, 'app_data', '置換リスト_ルビ.json')),
                       encoding='utf-8'))
    GL = d['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
    G2 = d['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
    GG = d['全域替换用のリスト(列表)型配列(replacements_final_list)']
    ps = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_skip.txt'))
    pl = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_localcapture.txt'))
    out = {}; SEP = '◆'; B = A.batch_size
    for i in range(0, len(surf), B):
        ch = surf[i:i + B]
        o = M.orchestrate_comprehensive_esperanto_text_replacement(
            ' ' + (' ' + SEP + ' ').join(ch) + ' ', ps, GL, pl, GG, G2, FMT)
        parts = o.split(SEP)
        if len(parts) != len(ch):
            parts = [M.orchestrate_comprehensive_esperanto_text_replacement(
                ' ' + w + ' ', ps, GL, pl, GG, G2, FMT) for w in ch]
        for w, s in zip(ch, parts):
            ms = list(RUBY.finditer(s))
            out[w] = ('/'.join(TAG.sub('', m.group(1)) for m in ms), len(ms),
                      sum(1 for m in ms
                          if not BRt.sub('', TAG.sub('', m.group(2))).strip()))
        if i % 10000 == 0: print(f'  [{lang}] {i}/{len(surf)}', flush=True)
    res[lang] = out
    sys.path.remove(app_dir)

mism = [w for w in surf if len({res[l][w][0] for l in ('JA', 'ZH', 'KO')}) != 1]
anno = {l: sum(1 for w in surf if res[l][w][1] > 0) for l in ('JA', 'ZH', 'KO')}
bare = {l: [w for w in surf if res[l][w][1] == 0] for l in ('JA', 'ZH', 'KO')}
empty = {l: sum(res[l][w][2] for w in surf) for l in ('JA', 'ZH', 'KO')}
only_ja = [w for w in surf
           if res['JA'][w][1] > 0 and (res['ZH'][w][1] == 0 or res['KO'][w][1] == 0)]
only_zhko = [w for w in surf
             if res['JA'][w][1] == 0 and (res['ZH'][w][1] > 0 or res['KO'][w][1] > 0)]
print('\n' + '=' * 64)
print(f'★3言語で分節が一致しない表層 : {len(mism)}  ({len(mism) / len(surf) * 100:.4f}%)')
for l in ('JA', 'ZH', 'KO'):
    print(f'   [{l}] 注釈あり {anno[l]:6d} / {len(surf)} '
          f'({anno[l] / len(surf) * 100:.3f}%)   無注釈 {len(bare[l]):5d}   空rt {empty[l]}')
print(f'★JAだけ振れて ZH/KO が無注釈 : {len(only_ja)}')
print(f'★ZH/KOだけ振れて JA が無注釈 : {len(only_zhko)}')
if mism:
    print('\n★分節不一致:')
    for w in mism[:20]:
        print(f'   {w:<24} ' + ' | '.join(f'{l}={res[l][w][0]}' for l in ('JA', 'ZH', 'KO')))
gate = not mism and not only_ja and not only_zhko and not any(empty.values())
print(f'\n判定: {"PASS" if gate else "★FAIL"}')
if A.report:
    json.dump({'surfaces': len(surf), 'seg_mismatch': mism,
               'coverage': {l: anno[l] for l in anno},
               'bare': {l: bare[l] for l in bare},
               'empty_rt': empty, 'only_ja': only_ja, 'only_zhko': only_zhko,
               'gate': gate},
              open(LP(A.report), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'report: {A.report}')
sys.exit(0 if gate else 1)
