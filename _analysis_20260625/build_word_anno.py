# -*- coding: utf-8 -*-
"""
日中韓注釈版から「E_stem語形 → [(語根片, 文脈依存訳), ...]」マップを言語別に構築。
語の意味は文脈依存(per-word)なので、語ごとに注釈を保持する。
出力: out/word_anno_{ja,zh,ko}.json   key=E_stem語形(語尾片を除いた /区切り), value=[[piece,trans],...]
"""
import re, sys, json, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp, hat_to_circumflex, replace_esperanto_chars

ANNO = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416_日中韓注釈版_ドラフト.txt"
OUT = BASE + r"\_analysis_20260625\out"
LINE_RE = re.compile(r'^(.*?)【日=(.*?)｜中=(.*?)｜韓=(.*?)】')

def norm(p):
    return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

def align(head, trans):
    """head(原文字) と trans(同一言語) を片ごとに整合(語尾アンカー)。失敗時None。"""
    hpw = [hw.split('/') for hw in head.split(' ')]
    flat = trans.split('/')
    out_words = []   # 各語ごとの [(piece_raw, trans), ...]
    fi = 0; carry = None
    for wi, hp in enumerate(hpw):
        np = len(hp); tp = []
        for k in range(np):
            if carry is not None:
                tp.append(carry); carry = None; continue
            if fi >= len(flat): return None
            piece = flat[fi]; fi += 1
            if k == np - 1 and wi < len(hpw) - 1 and ' ' in piece:
                e, rest = piece.split(' ', 1); tp.append(e); carry = rest
            else:
                tp.append(piece)
        if len(tp) != np: return None
        out_words.append(list(zip(hp, tp)))
    if fi != len(flat) or carry is not None: return None
    return out_words

maps = {'ja': {}, 'zh': {}, 'ko': {}}
n=0; okc=collections.Counter()
with open(lp(ANNO), encoding="utf-8") as f:
    for line in f:
        line = line.rstrip('\n')
        if not line or line.startswith('##') or '【日=' not in line: continue
        m = LINE_RE.match(line)
        if not m: continue
        head, s = m.group(1).strip(), {'ja': m.group(2), 'zh': m.group(3), 'ko': m.group(4)}
        if '#' in head: continue
        n += 1
        for L in ('ja','zh','ko'):
            aligned = align(head, s[L])
            if aligned is None: continue
            okc[L]+=1
            for word_pairs in aligned:
                if len(word_pairs) < 2:   # 語尾だけ等はスキップ
                    continue
                # E_stem語形 = 末尾(語尾)片を除いた /区切り(正規化)
                pieces_norm = [norm(p) for p, _ in word_pairs]
                key = '/'.join(pieces_norm[:-1])
                if not key or '#' in key: continue
                # 値 = 末尾片を除いた (正規化片, 訳)
                val = []
                for (p, t) in word_pairs[:-1]:
                    val.append([norm(p), t.strip()])
                # 既存と異なる場合は最初を優先(同一見出しは基本一意)
                if key not in maps[L]:
                    maps[L][key] = val

for L in ('ja','zh','ko'):
    with open(lp(OUT + f"\\word_anno_{L}.json"), "w", encoding="utf-8") as g:
        json.dump(maps[L], g, ensure_ascii=False)
    print(f"[{L}] 整合 {okc[L]}/{n}  語形エントリ {len(maps[L])}")
print("保存: out/word_anno_(ja|zh|ko).json")

# 文脈依存(同一語根片が語により異なる訳)を確認
ja_root_trans = collections.defaultdict(set)
for key, val in maps['ja'].items():
    for p, t in val:
        if len(p) >= 2: ja_root_trans[p].add(t)
poly = {r: ts for r, ts in ja_root_trans.items() if len(ts) >= 3}
print(f"\n日訳が3種以上に分かれる語根(文脈依存の証拠) {len(poly)}例:")
for r in list(poly)[:8]:
    print(f"  {r}: {sorted(poly[r])[:6]}")
