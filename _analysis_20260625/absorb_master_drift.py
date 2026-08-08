# -*- coding: utf-8 -*-
"""マスター更新の吸収(第13R):
 A(マスター一体化342語)+C(組替え5語)のうち、JCKドラフトが新形+3言語グロスで
 収録している語を word_anno(3言語) へ吸収。B(細分化340語)はルビ粗方針により不変
 (漢字側の将来課題として記録)。--write で書込。"""
import json, sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
WRITE = '--write' in sys.argv
ROOT = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630"
BASE = ROOT + r"\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630"
OUT = os.path.join(BASE, '_analysis_20260625', 'out')
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)
X = {'c^': 'ĉ', 'g^': 'ĝ', 'h^': 'ĥ', 'j^': 'ĵ', 's^': 'ŝ', 'u^': 'ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s

cls = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'master_diff_classified.json'), encoding='utf-8'))
# コーパス(ルビの裁定者)が分割形を使う語は、gold/ドラフトが一体化しても吸収しない
CORPUS_SPLIT_KEEP = {'dekkvin', 'dekses', 'novzeland', 'ĉifoj', 'dekdu', 'dektri', 'dekkvar', 'deksep', 'dekok', 'deknaŭ'}
targets = [t for t in (cls['A'] + cls['C']) if t[0] not in CORPUS_SPLIT_KEEP]

draft = ROOT + r"\エスペラント辞書徹底語根分解_20260630\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416_日中韓注釈版_ドラフト.txt"
dm = {}
for ln in open(LP(draft), encoding='utf-8'):
    m = re.match(r'^([^【]+)【日=([^｜]*)｜中=([^｜]*)｜韓=([^】]*)】', ln)
    if m:
        dec = circ(m.group(1).strip()).replace('-', '')
        dm.setdefault(dec.replace('/', '').lower(), (dec.lower(), m.group(2), m.group(3), m.group(4)))

ENDS = {'o', 'a', 'i', 'e', 'u', 'n', 'j', 'oj', 'on', 'aj', 'an', 'en', 'as', 'is', 'os'}
def stemize(dec_pieces, gl_pieces):
    """末尾の文法語尾片を分解・グロス双方から除去。"""
    d = list(dec_pieces); g = list(gl_pieces)
    while d and d[-1].lower() in ENDS:
        d.pop()
        if g: g.pop()
    return d, g

absorbed = {}  # nosl -> (dec_pieces, ja_pieces, zh_pieces, ko_pieces)
skipped = []
for n, e, mnew in targets:
    hit = None
    for suf in ('o', 'a', 'i', 'e', '', 'oj'):
        if (n + suf) in dm: hit = dm[n + suf]; break
    if not hit:
        skipped.append((n, mnew, '未収録')); continue
    ddec, ja, zh, ko = hit
    dp = [p for p in ddec.split('/') if p]
    jp = [p.replace('-', '') for p in ja.split('/')]
    zp = [p.replace('-', '') for p in zh.split('/')]
    kp = [p.replace('-', '') for p in ko.split('/')]
    dp2, _ = stemize(dp, [])
    ds = '/'.join(dp2)
    if ds != mnew:
        skipped.append((n, mnew, f'ドラフト形={ds}')); continue
    if not (len(jp) >= len(dp) and len(zp) >= len(dp) and len(kp) >= len(dp)):
        skipped.append((n, mnew, 'グロス片数不足')); continue
    # 語尾込みでゾロ目対応: 分解片数に合わせ先頭からlen(dp2)片を採用
    absorbed[n] = (dp2, jp[:len(dp2)], zp[:len(dp2)], kp[:len(dp2)])

print(f"吸収対象: {len(absorbed)} / スキップ: {len(skipped)}")
for n, m, why in skipped[:12]: print(f"  skip {n:20s} {m:24s} ({why})")

if WRITE:
    LM = {'JA': ('word_anno_ja.json', 1), 'ZH': ('word_anno_zh.json', 2), 'KO': ('word_anno_ko.json', 3)}
    for L, (fn, gi) in LM.items():
        for tgt in (os.path.join(BASE, f'Esperanto-Kanji-Ruby-{L}', 'app_data', 'word_anno.json'),
                    os.path.join(OUT, fn)):
            if not os.path.exists(LP(tgt)): continue
            wa = json.load(open(LP(tgt), encoding='utf-8'))
            nosl = {k.replace('/', ''): k for k in wa}
            for n, (dp, jp, zp, kp) in absorbed.items():
                gl = (jp, zp, kp)[gi - 1]
                key = '/'.join(dp)
                oldk = nosl.get(n)
                if oldk and oldk in wa and oldk != key: del wa[oldk]
                wa[key] = [[p, g] for p, g in zip(dp, gl)]
            json.dump(wa, open(LP(tgt), 'w', encoding='utf-8'), ensure_ascii=False)
        print(f"[{L}] word_anno へ {len(absorbed)}語 吸収")
    print("書込完了")
else:
    print("(dry-run: --write で書込)")
    for n, (dp, jp, zp, kp) in list(absorbed.items())[:6]:
        print(f"  {'/'.join(dp):26s} JA={'/'.join(jp)[:24]} KO={'/'.join(kp)[:20]}")
