# -*- coding: utf-8 -*-
"""注釈監査ワークフロー結果を読み、136問題を型・原因別に分類してレポート化。"""
import json, sys, os, collections
sys.stdout.reconfigure(encoding="utf-8")
TASK = r"C:\Users\yt\AppData\Local\Temp\claude\d--GoogleDrive202510--------20----------------------------20260624\46f52639-acfa-48a8-8c2f-e95e8e59b22d\tasks\woz0ib96n.output"
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
res = json.load(open(TASK, encoding="utf-8"))["result"]
issues = res["issueList"]
print(f"監査 {res['total']}件 / 問題 {res['issues']}件 / 一致 {res['agreement']}")
print(f"型別: " + ", ".join(f"{k}={v['issue']}/{v['total']}" for k, v in res["byType"].items()))

# 言語別 問題数
lang_cnt = collections.Counter()
for it in issues:
    for p in it.get("problems", []):
        lang_cnt[p["lang"]] += 1
print(f"\n問題のある言語別(延べ): " + ", ".join(f"{k}={v}" for k, v in lang_cnt.most_common()))

# DIVERGE を原因分類
def classify(it):
    if it["t"] == "GAP": return "GAP_言語欠落"
    if it["t"] == "GLOSS": return "GLOSS_誤訳/非並行"
    langs = [p["lang"] for p in it.get("problems", [])]
    note = it.get("note", "")
    if set(langs) == {"ja"}: return "DIVERGE_JAのみ非分割(ZH/KO正)"
    if "ko" in langs and "ja" not in langs and "zh" not in langs: return "DIVERGE_KOで-an脱落等"
    if {"zh", "ko"} <= set(langs): return "DIVERGE_ZH/KO偽友分割(JA正)"
    return "DIVERGE_その他"

cat = collections.defaultdict(list)
for it in issues:
    cat[classify(it)].append(it)
print("\n=== 問題の原因分類 ===")
for k, v in sorted(cat.items(), key=lambda x: -len(x[1])):
    print(f"  {len(v):4d}  {k}")

def show(it):
    probs = "; ".join(f"{p['lang']}:{p['current']}→{p['correct']}({p['why']})" for p in it.get("problems", []))
    cd = f" 正分解={it['correct_decomp']}" if it.get("correct_decomp") else ""
    return f"  {it['key']:18s}{cd}  [{probs}]"

for k in ["DIVERGE_ZH/KO偽友分割(JA正)", "GLOSS_誤訳/非並行", "DIVERGE_JAのみ非分割(ZH/KO正)",
          "DIVERGE_KOで-an脱落等", "GAP_言語欠落", "DIVERGE_その他"]:
    if k not in cat: continue
    print(f"\n=== [{k}] {len(cat[k])}件 ===")
    for it in cat[k][:40]:
        print(show(it))

OUT = BASE + r"\_analysis_20260625\out"
json.dump({k: v for k, v in cat.items()}, open(os.path.join(OUT, "_anno_issues_by_cause.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n保存: out/_anno_issues_by_cause.json")
