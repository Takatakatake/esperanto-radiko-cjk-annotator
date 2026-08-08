# -*- coding: utf-8 -*-
"""敵対裁定の結果から「京大コーパス自身が直すべき分解箇所」を確信度・型別に整理して出力。
   APP_RIGHT(=コーパス分解が誤り) と NEITHER(=両者誤り, コーパスも誤り) を対象。
   各語が何文書に何回出るかは監査の per-doc から補完しない(語単位のn=総出現)。"""
import json, os, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"d:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\語根分解アプリ徹底ブラッシュアップ20260624"
TASK = r"C:\Users\yt\AppData\Local\Temp\claude\d--GoogleDrive202510--------20----------------------------20260624\46f52639-acfa-48a8-8c2f-e95e8e59b22d\tasks\wkkb1m50g.output"
wf = json.load(open(TASK, encoding="utf-8"))["result"]
corpusErr = wf["corpusErrors"]   # コーパス分解が誤り(app/専門家が正)
neither = wf["neither"]          # 両者誤り(コーパスも誤り・正解は第三案)

def categorize(e):
    w, c, a = e["w"], e["corpus"], e["app"]
    correct = e.get("correct", a)
    cp = [p for p in c.split("/") if p]; ap = [p for p in a.split("/") if p]
    # 先頭1字孤立(コーパスが語頭1字を孤立させた)
    if len(cp) >= 2 and len(cp[0]) == 1 and cp[0] not in "aeiou":
        return "A_語頭1字の偽孤立"
    if len(cp) >= 2 and len(cp[0]) == 1 and cp[0] in "aeiou":
        return "A_語頭母音の偽孤立"
    # -log/-logi の綴り割れ (log/io のように形態素 logi を割っている)
    if "log/i" in c or "/log/" in ("/"+c+"/") and "logi" in (a):
        return "B_-logi-の綴り割れ/不統一"
    # 実在接辞の未分割: app片数 > corpus片数 (コーパスが一体化)
    if len(ap) > len(cp):
        return "C_実在接辞/語根の未分割(コーパスが一体)"
    # コーパスが過分解(片数 corpus > app) = 実在しない境界で割った
    if len(cp) > len(ap):
        return "D_コーパスが過分解(偽境界)"
    return "E_その他境界ずれ"

rows = []
for e in corpusErr + neither:
    rows.append({**e, "cat": categorize(e), "src": ("両者誤り" if e in neither else "コーパス誤り")})

bycat = collections.defaultdict(list)
for r in rows: bycat[r["cat"]].append(r)

print(f"コーパスが直すべき語: {len(rows)} 語 (コーパス誤り{len(corpusErr)} + 両者誤り{len(neither)})")
print(f"総出現インスタンス: {sum(r['n'] for r in rows)}\n")
order = ["A_語頭1字の偽孤立","A_語頭母音の偽孤立","D_コーパスが過分解(偽境界)",
         "B_-logi-の綴り割れ/不統一","C_実在接辞/語根の未分割(コーパスが一体)","E_その他境界ずれ"]
for cat in order:
    if cat not in bycat: continue
    items = sorted(bycat[cat], key=lambda x: -x["n"])
    tot = sum(i["n"] for i in items)
    print(f"### {cat}  ({len(items)}語 / {tot}inst)")
    for e in items:
        g = f" gold={e['gold']}" if e.get("gold") else ""
        print(f"   {e['n']:>3}x  {e['w']:16s} コーパス={e['corpus']:20s} → 正={e.get('correct',''):18s}{g}  [{e['reason']}]")
    print()

OUT = BASE + r"\_analysis_20260625\out"
json.dump(rows, open(os.path.join(OUT, "_corpus_fixlist.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"保存: out/_corpus_fixlist.json")
