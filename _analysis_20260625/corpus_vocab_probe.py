# -*- coding: utf-8 -*-
"""実使用語彙ゲート(2/2): 抽出語彙を漢字エンジンに通し、実文中の退行を実測する。

第66Rで新設。corpus_vocab_extract.py の出力(実使用語彙)を漢字モードで変換して記録し、
前回スナップショットと比較して「漢字を失った語」を検出する。辞書見出しの全数照合を
補完するゲートで、語スコープのラテン固定など**表層に触る変更**では必ず併用すること。

比較時、旧描画に「未対応」(漢字マスターのラテン維持センチネル)が含まれる語は、
漢字が消えたのではなく**是正**なので真の退行から除外して集計する。

使い方:
  python corpus_vocab_probe.py --words corpus_words.json --tag r150 [--app <repo>] [--baseline <前回json>]
"""
import json, re, sys, os, argparse
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92)*2 + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)

ap = argparse.ArgumentParser()
ap.add_argument('--words', default='corpus_words.json')
ap.add_argument('--app', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument('--tag', required=True)
ap.add_argument('--baseline', default='')
ap.add_argument('--out-dir', default='.')
A = ap.parse_args()

words = json.load(open(LP(A.words), encoding='utf-8'))['words']
print(f'コーパス実使用語: {len(words)}', flush=True)

APP = os.path.join(A.app, 'Esperanto-Kanji-Ruby-JA'); sys.path.insert(0, APP)
import esp_text_replacement_module as M
dd = json.load(open(os.path.join(APP, 'app_data', '置換リスト_漢字.json'), encoding='utf-8'))
GL = dd['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = dd['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
GG = dd['全域替换用のリスト(列表)型配列(replacements_final_list)']
ps_ = M.import_placeholders(os.path.join(APP, 'app_data', 'placeholders_skip.txt'))
pl_ = M.import_placeholders(os.path.join(APP, 'app_data', 'placeholders_localcapture.txt'))
def convert(t):
    return M.orchestrate_comprehensive_esperanto_text_replacement(
        t, ps_, GL, pl_, GG, G2, '汉字替换_大小调整')
RT = re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>'); TAG = re.compile(r'<[^>]+>')
def disp(seg): return TAG.sub('', RT.sub('', seg)).strip()

SEP = '◆'; B = 800
out = {}
for i in range(0, len(words), B):
    ch = words[i:i+B]
    o = convert(' ' + (' ' + SEP + ' ').join(ch) + ' ')
    parts = o.split(SEP)
    if len(parts) != len(ch):
        parts = [convert(' ' + w + ' ') for w in ch]
    for w, seg in zip(ch, parts):
        out[w] = disp(seg)
CJK = re.compile(r'[一-鿿]')
SENTINEL = '未対応'
n_k = sum(1 for v in out.values() if CJK.search(v) and SENTINEL not in v)
print(f'真に漢字化された語: {n_k} / {len(out)} ({100*n_k/len(out):.2f}%)')
print(f'「{SENTINEL}」を含む語: {sum(1 for v in out.values() if SENTINEL in v)}')

if A.baseline and os.path.exists(LP(A.baseline)):
    prev = json.load(open(LP(A.baseline), encoding='utf-8'))
    lost_true, lost_sentinel, gained, changed = [], [], [], []
    for w, v in out.items():
        p = prev.get(w)
        if p is None or p == v: continue
        pk, vk = bool(CJK.search(p)), bool(CJK.search(v))
        if pk and not vk:
            (lost_sentinel if SENTINEL in p else lost_true).append((w, p, v))
        elif vk and not pk: gained.append((w, p, v))
        else: changed.append((w, p, v))
    print(f'--- baseline({os.path.basename(A.baseline)}) 比較 ---')
    print(f'  ★真に漢字を失った語: {len(lost_true)}   ← これが 0 でなければ変更を撤回する')
    for w, p, v in lost_true[:60]: print(f'      {w}: {p!r} -> {v!r}')
    print(f'  センチネル是正による見かけの消失: {len(lost_sentinel)}')
    print(f'  漢字を得た語: {len(gained)}')
    for w, p, v in gained[:40]: print(f'      {w}: {p!r} -> {v!r}')
    print(f'  その他の描画変化: {len(changed)}')
    for w, p, v in [x for x in changed if SENTINEL not in x[1]][:40]:
        print(f'      {w}: {p!r} -> {v!r}')

out_p = os.path.join(A.out_dir, f'{A.tag}_corpus.json')
json.dump(out, open(LP(out_p), 'w', encoding='utf-8'), ensure_ascii=False)
print('saved:', out_p)
