# -*- coding: utf-8 -*-
"""R59 新機械軸#13: 語尾ルビ片の非語末出現検出。
形態論的不変量: 定動詞語尾 as/is/os/us(+単独u,i) と対格n・複数j(n以外が続く)は語末限定。
語再構成でルビ片列を取り、文法グロス付き語尾片の後に文字が続く語を全数検出。
   末尾アポストロフィのみは閉じ引用符(語末扱い)として除外。"""
import os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)
BASE = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630"
CORP = os.path.join(BASE, '_project_root_misc', '京大エス研html文書＿Github')

RUBY = re.compile(r'<ruby>([^<]+)<rt[^>]*>((?:[^<]|<br\s*/?>|<[bi]>|</[bi]>)*?)</rt></ruby>')
LETTER = r"A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ'"
# 語尾片(rb完全一致) → その片が語末でなければ違反となる文法グロスの手掛かり
FINITE = {'as', 'is', 'os', 'us'}
GRAM_HINT = re.compile(r'現在|過去|未来|仮定|時制|형|현재|과거|미래|对格|對格|対格|대격|复数|複数|복수')

def words_with_pieces(h):
    out = []
    i = 0; n = len(h); cur = []; start = None
    def flush():
        nonlocal cur
        if cur and any(g is not None for _, g in cur):
            w = ''.join(p for p, _ in cur)
            if re.fullmatch(f"[{LETTER}-]+", w):
                out.append((w, list(cur)))
        cur = []
    while i < n:
        m = RUBY.match(h, i)
        if m:
            cur.append((m.group(1), re.sub(r'<br\s*/?>', '', m.group(2))))
            i = m.end(); continue
        ch = h[i]
        if ch == '<':
            j = h.find('>', i); i = (j + 1) if j >= 0 else n
            flush() if h[i-2:i] != '->' and False else None
            continue
        if re.match(f"[{LETTER}\\-]", ch):
            cur.append((ch, None)); i += 1; continue
        flush(); i += 1
    flush()
    return out

hits = collections.defaultdict(list)
nf = 0
for r, ds, fs in os.walk(LP(CORP)):
    if os.sep + '.git' in r: continue
    for f in fs:
        if not f.endswith('.html') or 'index' in f.lower(): continue
        nf += 1
        h = open(os.path.join(r, f), encoding='utf-8', errors='ignore').read()
        for w, pieces in words_with_pieces(h):
            # 各片の語内位置を計算
            pos = 0
            for k, (p, g) in enumerate(pieces):
                pos += len(p)
                if g is None: continue
                at_end = (pos == len(w))
                rest = w[pos:]
                pl = p.lower()
                # (1) 定動詞語尾が語中
                if pl in FINITE and not at_end and not rest.startswith('-') and rest != chr(39):
                    hits[(w.lower(), 'A:定動詞語尾が語中')].append((f, p, g))
                # (2) 対格n/複数j: 文法グロス付きで直後に文字
                elif pl == 'n' and GRAM_HINT.search(g) and not at_end and not rest.startswith('-'):
                    hits[(w.lower(), 'B:対格nが語中')].append((f, p, g))
                elif pl in ('oj', 'aj', 'j') and GRAM_HINT.search(g) and not at_end and rest[:1] != 'n' and not rest.startswith('-'):
                    hits[(w.lower(), 'C:複数jの後にn以外')].append((f, p, g))
print(f"走査 {nf} ファイル / 違反候補 {len(hits)} 語")
for (w, kind), occ in sorted(hits.items()):
    fs2 = collections.Counter(o[0][:28] for o in occ)
    print(f"  [{kind}] {w:22s} ×{len(occ):3d}  gloss例={occ[0][2][:16]!r}  {dict(list(fs2.items())[:2])}")
