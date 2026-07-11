# -*- coding: utf-8 -*-
"""
注釈版から語根→日中韓訳を抽出(改良版)。
語尾アンカー方式: 各語の最終片(文法語尾=ラテン文字)を手がかりに、
訳中の空白(複合句境界 vs 訳語内空白)を区別して語境界を復元する。
"""
import re, sys, csv, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp, hat_to_circumflex, replace_esperanto_chars

ANNO = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416_日中韓注釈版_ドラフト.txt"
APP = BASE + r"\Esperanto-Kanji-Ruby-JA"
DATA = APP + r"\app_data"
NEW_ROOTS = BASE + r"\_analysis_20260625\out\new_rootlist.txt"
OUTDIR = BASE + r"\_analysis_20260625\out"
LINE_RE = re.compile(r'^(.*?)【日=(.*?)｜中=(.*?)｜韓=(.*?)】')
ENDINGS = {'o','a','e','i','u','oj','aj','on','an','ojn','ajn','as','is','os','us','n','j','en','u!','o!','a!','e!'}
ENDING_TOKEN = re.compile(r'^[a-zĉĝĥĵŝŭ!]+$')   # ラテンのみ=語尾候補

def norm_root(p):
    return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

def align(head, trans):
    """head と trans(同一言語) を語根片→訳片に整合。失敗時 None。"""
    hpw = [hw.split('/') for hw in head.split(' ')]
    flat = trans.split('/')
    pairs = []
    fi = 0
    carry = None
    for wi, hp in enumerate(hpw):
        np = len(hp)
        tpieces = []
        for k in range(np):
            if carry is not None:
                tpieces.append(carry); carry = None; continue
            if fi >= len(flat):
                return None
            piece = flat[fi]; fi += 1
            # 非最終語の最終片は "語尾 次語先頭" の形(空白境界)
            if k == np - 1 and wi < len(hpw) - 1 and ' ' in piece:
                end_part, rest = piece.split(' ', 1)
                tpieces.append(end_part); carry = rest
            else:
                tpieces.append(piece)
        if len(tpieces) != np:
            return None
        for k in range(np):
            pairs.append((hp[k], tpieces[k]))
    if fi != len(flat) or carry is not None:
        return None
    return pairs

ja = collections.defaultdict(collections.Counter)
zh = collections.defaultdict(collections.Counter)
ko = collections.defaultdict(collections.Counter)
maps = {'ja': ja, 'zh': zh, 'ko': ko}
n_lines = 0; n_ok = {'ja':0,'zh':0,'ko':0}; n_fail = {'ja':0,'zh':0,'ko':0}

with open(lp(ANNO), encoding="utf-8") as f:
    for line in f:
        line = line.rstrip('\n')
        if not line or line.startswith('##'):
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        head, s = m.group(1).strip(), {'ja': m.group(2), 'zh': m.group(3), 'ko': m.group(4)}
        if '#' in head:
            continue
        n_lines += 1
        for L in ('ja','zh','ko'):
            pairs = align(head, s[L])
            if pairs is None:
                n_fail[L] += 1
                continue
            n_ok[L] += 1
            for hp, tp in pairs:
                r = norm_root(hp); tp = tp.strip()
                if len(r) < 2 or r in ENDINGS or '#' in r or any(c.isdigit() for c in r):
                    continue
                if not tp or tp == hp or tp == r or ENDING_TOKEN.match(tp):
                    continue   # 未訳(ローマ字)はskip
                maps[L][r][tp] += 1

def finalize(store):
    return {r: c.most_common(1)[0][0] for r, c in store.items()}
fin = {L: finalize(maps[L]) for L in ('ja','zh','ko')}

with open(lp(NEW_ROOTS), encoding="utf-8") as f:
    deployed = set(l.strip() for l in f if l.strip())

def csv_roots(path):
    s = set()
    with open(lp(path), encoding="utf-8") as f:
        for row in csv.reader(f):
            if row and row[0] and '#' not in row[0] and len(row) >= 2 and row[1].strip():
                r = norm_root(row[0])
                if len(r) >= 2:
                    s.add(r)
    return s
cur = {'ja': csv_roots(DATA + r"\エスペラント語根-日本語訳ルビ対応リスト.csv"),
       'zh': csv_roots(DATA + r"\世界语词根-中文注释对应列表.csv"),
       'ko': csv_roots(DATA + r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv")}

print("="*72)
print("【改良版 抽出 & カバレッジ】 注釈行 %d" % n_lines)
for L in ('ja','zh','ko'):
    print(f"  [{L}] 整合成功 {n_ok[L]} / 失敗 {n_fail[L]}  抽出語根訳 {len(fin[L])}")
print(f"デプロイ語根 {len(deployed)}")
for L in ('ja','zh','ko'):
    a = set(fin[L]); c = cur[L]
    union = len(deployed & (a | c))
    gap = deployed - c
    fill = gap & a
    print(f"  [{L}] カバレッジ 現行 {len(deployed & c)/len(deployed)*100:.1f}% → 注釈版併用 {union/len(deployed)*100:.1f}%  (残ギャップ {len(gap-a)})")

# 残ギャップ(注釈版でも埋まらない)を保存して確認用
for L in ('ja','zh','ko'):
    a = set(fin[L]); gap = (deployed - cur[L]) - a
    with open(lp(OUTDIR + f"\\uncovered_{L}.txt"), "w", encoding="utf-8") as g:
        for r in sorted(gap):
            g.write(r + "\n")
    with open(lp(OUTDIR + f"\\anno_root_{L}.csv"), "w", encoding="utf-8", newline="") as g:
        w = csv.writer(g)
        for r, t in sorted(fin[L].items()):
            w.writerow([r, t])
print("保存: out\\anno_root_(ja|zh|ko).csv, out\\uncovered_(ja|zh|ko).txt")
