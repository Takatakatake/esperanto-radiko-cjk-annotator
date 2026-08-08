# -*- coding: utf-8 -*-
"""
学術版(マーカー無し・PEJVO尊重)から E_stem を抽出し、
旧E_stem との分解差分を測る。学習者版と比較して「訳劣化リスクの低い改善量」を把握。
"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
sys.path.insert(0, BASE + r"\_analysis_20260625")
from extract_lib import normalize_lines, extract_estem, lp

ACAD = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学術版_utf8_20260416.txt"
LEARN = r"\\wsl.localhost\Ubuntu\home\y\エスペラント辞書徹底語根分解_20260619\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
APP = BASE + r"\Esperanto-Kanji-Ruby-JA"
DATA = APP + r"\app_data"
OLD_ESTEM = DATA + r"\E_stem.json"

def estem_map(path):
    lines = normalize_lines(path, skip_marker_lines=True)
    est = extract_estem(lines)
    m = {}
    for x in est:
        if len(x)==2:
            m.setdefault(x[0].replace('/',''), set()).add(x[0])
    return m, len(est)

acad, n_acad = estem_map(ACAD)
learn, n_learn = estem_map(LEARN)
with open(lp(OLD_ESTEM), encoding='utf-8') as f:
    oe = json.load(f)
old = {}
for x in oe:
    if len(x)==2:
        old.setdefault(x[0].replace('/',''), set()).add(x[0])

def diff(name, new):
    both = set(old)&set(new)
    changed = [k for k in both if not (new[k] & old[k])]
    only_new = set(new)-set(old)
    print(f"[{name}] entry数={'?'}  nosl語数={len(new)}  both={len(both)}  分解変化={len(changed)}  新規語={len(only_new)}")
    return changed

print("="*72)
print("【学術版 vs 学習者版: 旧E_stemからの分解変化量】")
ca = diff("学術版", acad)
cl = diff("学習者版", learn)

# 特定の誤誘導語が各版でどうなるか
probe = ['agronom','telegrafret','monomani','germanium','majoran','aerobi','reorganiz','aŭtomobil','telefon','zoologi']
print("\n---- 注目語の分解 (旧 / 学術版 / 学習者版) ----")
for p in probe:
    o = sorted(old.get(p,[]))
    a = sorted(acad.get(p,[]))
    l = sorted(learn.get(p,[]))
    print(f"  {p:14s} 旧={o}  学術={a}  学習={l}")
