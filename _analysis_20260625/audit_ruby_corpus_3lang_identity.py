# -*- coding: utf-8 -*-
"""★実使用語彙(=語尾変化形を含む)で3言語の分節が完全一致するかを測る(第90R新設)。

これまでの3言語一致監査はいずれも**マスター見出しの表層**が母集団で、
京大コーパスに実在する語尾変化形(duonon・klasanoj・hungardevena 等)は入っていなかった。
ユーザーの絶対要件「日中韓語で、分解は完全一致していないといけません」は
実文に現れる形にも掛かるので、その隙間を埋める。

  usage: audit_ruby_corpus_3lang_identity.py --words <corpus_words.json> [--report out.json]
         words は {"words": [...]} 形式(京大HTMLから抽出した実使用語彙)。
         省略時は ESP_CORPUS_WORDS を見る。

第90R(gen-q)実測: 22,133語 / ★3言語分節不一致 0 (0.0000%) /
  注釈カバレッジ 96.422%(21,341語・3言語で完全に同一) / 空rt 0 /
  ★JAだけ振れて ZH/KO が無注釈 = 0。
  無注釈792語は裸の接辞の引用と外国固有名詞(音写は発明になるため保留)。
"""
import argparse, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92) * 2 + chr(63) + chr(92)
def LP(p): return p if p.startswith(PFX) else PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
BRt = re.compile(r'<br\s*/?>')
FMT = 'HTML格式_Ruby文字_大小调整'

ap = argparse.ArgumentParser()
ap.add_argument('--words', default=os.environ.get('ESP_CORPUS_WORDS', ''))
ap.add_argument('--report', default='')
ap.add_argument('--batch-size', type=int, default=600)
A = ap.parse_args()
if not A.words:
    raise SystemExit('--words <corpus_words.json> が必要 (または ESP_CORPUS_WORDS)')
words = json.load(open(LP(A.words), encoding='utf-8'))['words']
print(f'実使用語彙 {len(words)}')

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
    for i in range(0, len(words), B):
        ch = words[i:i + B]
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
        if i % 6000 == 0: print(f'  [{lang}] {i}/{len(words)}', flush=True)
    res[lang] = out
    sys.path.remove(app_dir)

mism = [w for w in words if len({res[l][w][0] for l in ('JA', 'ZH', 'KO')}) != 1]
anno = {l: sum(1 for w in words if res[l][w][1] > 0) for l in ('JA', 'ZH', 'KO')}
empty = {l: sum(res[l][w][2] for w in words) for l in ('JA', 'ZH', 'KO')}
only_ja = [w for w in words
           if res['JA'][w][1] > 0 and (res['ZH'][w][1] == 0 or res['KO'][w][1] == 0)]
print('\n' + '=' * 60)
print(f'★3言語で分節が一致しない語: {len(mism)}  ({len(mism) / len(words) * 100:.4f}%)')
for l in ('JA', 'ZH', 'KO'):
    print(f'   [{l}] 注釈あり {anno[l]:6d} / {len(words)} '
          f'({anno[l] / len(words) * 100:.3f}%)   空rt {empty[l]}')
print(f'★JAだけ振れて ZH/KO が無注釈: {len(only_ja)}')
if mism:
    print('\n★不一致:')
    for w in mism[:20]:
        print(f'   {w:<22} ' + ' | '.join(f'{l}={res[l][w][0]}' for l in ('JA', 'ZH', 'KO')))
gate = not mism and not only_ja and not any(empty.values())
print(f'\n判定: {"PASS" if gate else "★FAIL"}')
if A.report:
    json.dump({'words': len(words), 'seg_mismatch': mism,
               'coverage': anno, 'empty_rt': empty, 'only_ja': only_ja, 'gate': gate},
              open(LP(A.report), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'report: {A.report}')
sys.exit(0 if gate else 1)
