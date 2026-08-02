# -*- coding: utf-8 -*-
"""実使用語彙ゲート(1/2): 公開コーパスHTMLから素のエスペラント語彙を抽出する。

第66Rで新設。辞書見出し集合(注入エクスポート55,064語)だけの照合では
 (a) 辞書に無い**生産的派生形**、(b) **文頭大文字の普通名詞**
が測れず、実文中の退行が不可視になる。ルビ版コーパスは
`<ruby>エス語根<rt>訳</rt></ruby>` 形式なので、rt を除去すれば原文が復元できる。

★実装上の罠(実測): ruby系タグは**空文字**で除去しないと、1語が語根単位に割れる
   (タグを空白に置換すると頻度上位語が o/la/a/is という語尾断片になり即座に判る)。
   段落等の他のタグは語の連結を防ぐため空白に置換する。

使い方:
  python corpus_vocab_extract.py --corpus <コーパスrepo> --out corpus_words.json
"""
import os, re, sys, json, glob, collections, argparse
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92)*2 + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)

ap = argparse.ArgumentParser()
ap.add_argument('--corpus', default=r'C:\Users\yt\.esp_repos\wt_corpus')
ap.add_argument('--out', default='corpus_words.json')
ap.add_argument('--scope', choices=('all', 'content'), default='all',
                help=('all: repo内の全HTML（従来動作） / content: '
                      'lernolibroj,legajxoj,revuoj,rondolegado の本文HTMLのみ'))
A = ap.parse_args()

CONTENT_DIRS = ('lernolibroj', 'legajxoj', 'revuoj', 'rondolegado')

RT = re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>')
RUBYTAG = re.compile(r'</?ruby[^>]*>')          # ← 空文字で除去(語を割らない)
TAG = re.compile(r'<[^>]+>')                    # ← 空白で置換(語を連結しない)
SCRIPT = re.compile(r'<(script|style)[^>]*>.*?</\1>', re.S | re.I)
L = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
WORD = re.compile('[' + L + ']{1,40}')

if A.scope == 'content':
    missing = [name for name in CONTENT_DIRS
               if not os.path.isdir(os.path.join(A.corpus, name))]
    if missing:
        ap.error('content scope requires all content directories; missing: '
                 + ', '.join(missing))
    html_paths = []
    for name in CONTENT_DIRS:
        directory_paths = glob.glob(
            os.path.join(A.corpus, name, '**', '*.html'), recursive=True)
        if not directory_paths:
            ap.error('content scope requires at least one HTML file in each '
                     f'content directory; empty: {name}')
        html_paths.extend(directory_paths)
else:
    html_paths = glob.glob(os.path.join(A.corpus, '**', '*.html'), recursive=True)

freq = collections.Counter(); files = 0
for p in html_paths:
    try:
        raw = open(LP(p), encoding='utf-8', errors='replace').read()
    except Exception as error:
        if A.scope == 'content':
            ap.error(f'content HTML could not be read: {p}: {error}')
        continue
    files += 1
    raw = SCRIPT.sub(' ', raw)
    txt = TAG.sub(' ', RUBYTAG.sub('', RT.sub('', raw)))
    for w in WORD.findall(txt):
        freq[w] += 1

words = sorted(freq)
cap = [w for w in words if w[:1].isupper()]
print(f'コーパスHTML {files} ファイル / ユニーク語 {len(words)} (うち語頭大文字 {len(cap)})')
print('  頻度上位20:', [w for w, _ in freq.most_common(20)])
if words and freq.most_common(1)[0][0] in ('o', 'a', 'is', 'as'):
    print('  ★警告: 頻度上位が語尾断片です。ruby除去の実装を確認してください。')
json.dump({'files': files, 'words': words, 'capitalized': cap,
           'freq_top': freq.most_common(500)},
          open(LP(A.out), 'w', encoding='utf-8'), ensure_ascii=False)
print('saved:', A.out)
