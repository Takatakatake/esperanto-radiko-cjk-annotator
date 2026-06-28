# -*- coding: utf-8 -*-
"""
日中韓注釈版から「語根→日/中/韓 訳」マップを抽出し、
デプロイ済み語根リストに対する訳カバレッジ改善を定量化。ドラフトCSVも保存。
"""
import re, json, sys, collections, csv
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import lp, hat_to_circumflex, replace_esperanto_chars

ANNO = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416_日中韓注釈版_ドラフト.txt"
APP = BASE + r"\Esperanto-Kanji-Ruby-JA"
DATA = APP + r"\Appの运行に使用する各类文件"
NEW_ROOTS = BASE + r"\_analysis_20260625\out\new_rootlist.txt"
OUTDIR = BASE + r"\_analysis_20260625\out"

ENDINGS = {'o','a','e','i','u','oj','aj','on','an','ojn','ajn','as','is','os','us','n','j','en'}
LINE_RE = re.compile(r'^(.*?)【日=(.*?)｜中=(.*?)｜韓=(.*?)】')

def norm_root(p):
    p = replace_esperanto_chars(p, hat_to_circumflex).lower().strip()
    return p

ja = collections.defaultdict(collections.Counter)
zh = collections.defaultdict(collections.Counter)
ko = collections.defaultdict(collections.Counter)
maps = {'ja': ja, 'zh': zh, 'ko': ko}

n_lines = 0; n_parsed = 0; n_mismatch = 0
with open(lp(ANNO), encoding="utf-8") as f:
    for line in f:
        line = line.rstrip('\n')
        if not line or line.startswith('##'):
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        n_lines += 1
        head, sja, szh, sko = m.group(1).strip(), m.group(2), m.group(3), m.group(4)
        if '#' in head:
            continue
        hwords = head.split(' ')
        lang_words = {'ja': sja.split(' '), 'zh': szh.split(' '), 'ko': sko.split(' ')}
        ok = True
        for li, lw in lang_words.items():
            if len(lw) != len(hwords):
                ok = False
        if not ok:
            n_mismatch += 1
            continue
        for wi, hw in enumerate(hwords):
            hpieces = [p for p in hw.split('/') if p != '']
            for li, store in maps.items():
                tpieces = [p for p in lang_words[li][wi].split('/') if p != '']
                if len(tpieces) != len(hpieces):
                    continue
                for hp, tp in zip(hpieces, tpieces):
                    r = norm_root(hp)
                    tp = tp.strip()
                    if len(r) < 2:                # 1文字語尾(o,a,e,i等)は語根でない
                        continue
                    if r in ENDINGS:
                        continue
                    if not tp or tp == hp or tp == r:   # 未訳(ローマ字のまま)はスキップ
                        continue
                    if '#' in r or any(c.isdigit() for c in r):
                        continue
                    store[r][tp] += 1
        n_parsed += 1

# 各語根の最頻訳を採用
def finalize(store):
    return {r: c.most_common(1)[0][0] for r, c in store.items()}
ja_f, zh_f, ko_f = finalize(ja), finalize(zh), finalize(ko)

# デプロイ済み語根リスト
with open(lp(NEW_ROOTS), encoding="utf-8") as f:
    deployed_roots = set(l.strip() for l in f if l.strip())

# 現行CSVカバレッジ
def csv_roots(path):
    s = set()
    try:
        with open(lp(path), encoding="utf-8") as f:
            for row in csv.reader(f):
                if row and row[0] and '#' not in row[0]:
                    r = norm_root(row[0])
                    if len(r) >= 2 and len(row) >= 2 and row[1].strip():
                        s.add(r)
    except Exception as e:
        print("csv err", e)
    return s

cur = {
 'ja': csv_roots(DATA + r"\エスペラント語根-日本語訳ルビ対応リスト.csv"),
 'zh': csv_roots(DATA + r"\世界语词根-中文注释对应列表.csv"),
 'ko': csv_roots(DATA + r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv"),
}
anno_f = {'ja': ja_f, 'zh': zh_f, 'ko': ko_f}

print("="*72)
print("【注釈版 抽出 & 訳カバレッジ定量化】")
print(f"注釈行 解析 {n_parsed}/{n_lines}  (片数不一致でskip {n_mismatch})")
print(f"デプロイ済み語根数: {len(deployed_roots)}")
for L in ('ja','zh','ko'):
    a = set(anno_f[L]); c = cur[L]
    cov_cur = len(deployed_roots & c)
    cov_anno = len(deployed_roots & a)
    cov_union = len(deployed_roots & (a | c))
    gap_now = deployed_roots - c                       # 現行で訳が無い語根
    gap_filled = gap_now & a                            # 注釈版が埋められる
    still_gap = gap_now - a
    print(f"\n[{L}] 注釈版から抽出した語根訳数: {len(a)}")
    print(f"   デプロイ語根の訳カバレッジ: 現行CSV {cov_cur} ({cov_cur/len(deployed_roots)*100:.1f}%) "
          f"→ 注釈版併用 {cov_union} ({cov_union/len(deployed_roots)*100:.1f}%)")
    print(f"   現行の訳ギャップ {len(gap_now)} のうち 注釈版が補完可 {len(gap_filled)} / 残り {len(still_gap)}")
    print(f"   注釈版で新たに埋まる語根例: {sorted(list(gap_filled))[:15]}")

# ドラフト保存(語根, 訳) CSV — 後でworkflowの方針を反映して確定
for L in ('ja','zh','ko'):
    with open(lp(OUTDIR + f"\\anno_root_{L}.csv"), "w", encoding="utf-8", newline="") as g:
        w = csv.writer(g)
        for r, t in sorted(anno_f[L].items()):
            w.writerow([r, t])
print(f"\nドラフト保存: out\\anno_root_(ja|zh|ko).csv")
