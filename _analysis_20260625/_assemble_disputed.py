# -*- coding: utf-8 -*-
"""監査で出た全係争語(コーパスvsappが食い違う語)を1つのデータセットに集約し、
   workflow敵対裁定用の compact JSON を吐く。各 bucket のラベルも付与。"""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
OUT = BASE + r"\_analysis_20260625\out"
def L(n): return json.load(open(os.path.join(OUT, n), encoding="utf-8"))
src = [
    ("CORPUS_ERR_GOLD", "_audit_corpus_errors.json"),     # gold が app を支持
    ("APP_ERR_GOLD",    "_audit_app_errors.json"),          # gold が corpus を支持
    ("NOTINGOLD_APPCOARSE", "_audit_notingold_appcoarse.json"),  # app丸ごと, corpus分解
    ("NOTINGOLD_APPFINE",   "_audit_notingold_appfine.json"),    # app分解, corpus丸ごと
    ("CEILING", "_audit_ceiling.json"),                     # 国名-i/o 等
]
ds = []
seen = set()
for label, fn in src:
    for e in L(fn):
        k = (e["word"], e["corpus"], e["app"])
        if k in seen: continue
        seen.add(k)
        ds.append({"w": e["word"], "c": e["corpus"], "a": e["app"],
                   "g": e.get("gold"), "n": e["count"], "b": label})
ds.sort(key=lambda x: -x["n"])
json.dump(ds, open(os.path.join(OUT, "_disputed_all.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(f"係争語 {len(ds)} 件 -> out/_disputed_all.json")
from collections import Counter
c = Counter(x["b"] for x in ds)
for k, v in c.most_common(): print(f"  {v:4d}  {k}")
print(f"総インスタンス {sum(x['n'] for x in ds)}")
