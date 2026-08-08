# -*- coding: utf-8 -*-
"""★アプリのルビの「粗さ」を京大エス研HTML本体と全数照合する(第90R新設)。

ユーザーの基準は「注釈ルビ振りの分解の粗さについては、京大エス研のHTMLファイル群
ぐらいがいいな」。したがって**粗さの裁定者は学術版goldではなく京大コーパス本体**である。
この測定器はコーパスのHTMLから実ルビを復元し、アプリの分節と全数で突き合わせる。

★これが要る理由(第89R実測):
  「アプリが学術版goldより細かい語」を洗うと2,236語出るが、京大コーパス本体は
  **アプリと同じ語根単位**で振っていた(ルビ個数一致 23/24)。
      geologio   アプリ geo|logi   京大 geo[地] logi[学]
      klorido    アプリ klor|id    京大 klor[[化]塩素] id[化物]
  学術版に合わせて粗くすると逆にユーザー基準から外れる。**一括粗化は禁止**。

  usage: audit_ruby_vs_kyodai_coarseness.py [--corpus <京大HTMLのdir>] [--report out.json]
         corpus は既定で ESP_CORPUS_PATH。

第90R(gen-q)実測: ルビ付き21,321表層 / 分節一致 99.625% / 不一致80。
  不一致の内訳(単語57・句23=改行を挟む複数語句の測定アーティファクト):
    無注釈42(裸の接辞の引用 `re`/`um`/`aĉ` と外国固有名詞。音写は発明になるので保留)
    位置違い13(revu/Bombaj/korona/video/animea 等いずれも既裁定)
    アプリが粗い2(mine=コーパス側のタイポ候補 / deven*=複合語では京大自身が一語根)
    ★アプリが細かい 0
"""
import argparse, io, json, os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92) * 2 + chr(63) + chr(92)
def LP(p): return p if p.startswith(PFX) else PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CORPUS = (r'D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学'
                  r'\Esperanto_HTML文書'
                  r'\京大エス研html文書＿Github＿実際にHTMLを作成する場所_クラウド用意外と使わないかも')
L_ = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
RUBY_C = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt>\s*</ruby>', re.S)
RUBY_A = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
SEQ = re.compile(r'(?:<ruby>.*?</ruby>|[' + L_ + r'])+', re.S)
WORD = re.compile('[' + L_ + ']{1,40}')
FMT = 'HTML格式_Ruby文字_大小调整'

ap = argparse.ArgumentParser()
ap.add_argument('--corpus', default=os.environ.get('ESP_CORPUS_PATH') or DEFAULT_CORPUS)
ap.add_argument('--report', default='')
A = ap.parse_args()

# ── 京大HTMLから「連続するruby群 = 1語」を復元 ─────────────────────
corp = collections.defaultdict(collections.Counter)
files = 0
for r, _, fs in os.walk(LP(A.corpus)):
    if '.git' in r: continue
    for f in fs:
        if not f.lower().endswith(('.html', '.htm')): continue
        files += 1
        t = io.open(os.path.join(r, f), encoding='utf-8', errors='replace').read()
        for m in SEQ.finditer(t):
            chunk = m.group(0)
            if '<ruby>' not in chunk: continue
            surf = ''; bases = []; pos = 0
            for rm in RUBY_C.finditer(chunk):
                if rm.start() > pos: surf += TAG.sub('', chunk[pos:rm.start()])
                b = TAG.sub('', rm.group(1)); surf += b; bases.append(b); pos = rm.end()
            if pos < len(chunk): surf += TAG.sub('', chunk[pos:])
            if surf and bases: corp[surf]['/'.join(bases)] += 1
print(f'走査 {files} HTML / ルビの付いた表層 {len(corp)}')

words = sorted(corp)
app_dir = os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA')
sys.path.insert(0, app_dir)
import esp_text_replacement_module as M
d = json.load(open(LP(os.path.join(app_dir, 'app_data', '置換リスト_ルビ.json')),
                   encoding='utf-8'))
GL = d['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = d['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
GG = d['全域替换用のリスト(列表)型配列(replacements_final_list)']
ps = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_skip.txt'))
pl = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_localcapture.txt'))
app = {}; SEP = '◆'; B = 500
for i in range(0, len(words), B):
    ch = words[i:i + B]
    o = M.orchestrate_comprehensive_esperanto_text_replacement(
        ' ' + (' ' + SEP + ' ').join(ch) + ' ', ps, GL, pl, GG, G2, FMT)
    parts = o.split(SEP)
    if len(parts) != len(ch):
        parts = [M.orchestrate_comprehensive_esperanto_text_replacement(
            ' ' + w + ' ', ps, GL, pl, GG, G2, FMT) for w in ch]
    for w, s in zip(ch, parts):
        app[w] = '/'.join(TAG.sub('', m.group(1)) for m in RUBY_A.finditer(s))
    if i % 5000 == 0: print(f'  描画 {i}/{len(words)}', flush=True)

exact = 0; diff = []
for w in words:
    a = app.get(w, '')
    if a in set(corp[w]): exact += 1; continue
    top = corp[w].most_common(1)[0][0]
    diff.append({'w': w, 'n': sum(corp[w].values()), 'app': a, 'kyodai': top,
                 'kyodai_all': list(corp[w]), 'is_word': bool(WORD.fullmatch(w))})
print(f'\n★分節一致 {exact} / {len(words)} ({exact / len(words) * 100:.3f}%)   不一致 {len(diff)}')
單 = [r for r in diff if r['is_word']]
print(f'   単語 {len(單)} / 句・改行入り(測定アーティファクト) {len(diff) - len(單)}')
kind = collections.Counter()
for r in 單:
    if not r['app']: kind['アプリが無注釈'] += 1
    elif r['app'].count('/') > r['kyodai'].count('/'): kind['★アプリが細かい'] += 1
    elif r['app'].count('/') < r['kyodai'].count('/'): kind['アプリが粗い'] += 1
    else: kind['同数だが位置違い'] += 1
print('   単語の内訳: ' + ' / '.join(f'{k}={v}' for k, v in kind.most_common()))
print('\n出現数の多い単語不一致 上位25:')
for r in sorted(單, key=lambda x: -x['n'])[:25]:
    tag = ('無注釈' if not r['app'] else
           '細かい' if r['app'].count('/') > r['kyodai'].count('/') else
           '粗い' if r['app'].count('/') < r['kyodai'].count('/') else '位置')
    print(f"  {r['n']:4d} [{tag}] {r['w']:<20} app={r['app'] or '(なし)':<26} 京大={r['kyodai']}")
if A.report:
    json.dump({'surfaces': len(words), 'exact': exact, 'diff': diff,
               'word_kinds': dict(kind)},
              open(LP(A.report), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\nreport: {A.report}')
