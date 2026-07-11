# -*- coding: utf-8 -*-
"""62,283語マスターへの3言語ルビ網羅性・構造監査。
A. マスター鮮度: 本日更新のマスター語彙 vs アプリE_stem/word_annoの差分
B. 3言語構造同一性: 分解設定diff / 語根CSV語根集合diff (word_annoは0確認済)
C. 語根グロスのカバレッジ: JAにありZH/KOに無い語根(→ZH/KOで裸片になる)
"""
import os, re, sys, csv, json
sys.stdout.reconfigure(encoding='utf-8')
ROOT = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630"
BASE = ROOT + r"\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630"
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)

X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ','C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a,b in X.items(): s = s.replace(a,b)
    return s

# ===== A. マスター鮮度 =====
GOLD = ROOT + r"\エスペラント辞書徹底語根分解_20260630\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
master = {}
for ln in open(LP(GOLD), encoding='utf-8'):
    w = ln.split(':', 1)[0].strip()
    if w: master[circ(w).replace('/','').replace('-','').lower().replace(' ','')] = circ(w)
print(f"A. マスター語彙: {len(master)}")
import datetime
print(f"   マスター更新時刻: {datetime.datetime.fromtimestamp(os.path.getmtime(LP(GOLD)))}")
for L in ('JA',):
    es = json.load(open(LP(rf"{BASE}\Esperanto-Kanji-Ruby-{L}\app_data\E_stem.json"), encoding='utf-8'))
    p_es = rf"{BASE}\Esperanto-Kanji-Ruby-{L}\app_data\E_stem.json"
    print(f"   E_stem({L}): {len(es)}エントリ 更新: {datetime.datetime.fromtimestamp(os.path.getmtime(LP(p_es)))}")
    es_set = set()
    for e in es:
        if isinstance(e, list) and e: es_set.add(str(e[0]).replace('/','').lower())
        elif isinstance(e, str): es_set.add(e.replace('/','').lower())
    wa = json.load(open(LP(rf"{BASE}\Esperanto-Kanji-Ruby-{L}\app_data\word_anno.json"), encoding='utf-8'))
    wa_set = {k.replace('/','').lower() for k in wa}
    # マスター語(語尾を除いたステム化はせず単語形で) がE_stem/wa経由でカバーされるか(概算):
    # E_stemはステム形なので、マスター単語形から語尾を落として照合
    ENDS = ('ojn','ajn','oj','aj','on','an','as','is','os','us','o','a','i','e','u','n','j')
    def stems(w):
        cands = {w}
        for e in ENDS:
            if w.endswith(e) and len(w) - len(e) >= 2: cands.add(w[:len(w)-len(e)])
        return cands
    uncovered = []
    for n, orig in master.items():
        if not (stems(n) & (es_set | wa_set)):
            uncovered.append(orig)
    print(f"   E_stem∪word_annoに語幹が見つからないマスター語: {len(uncovered)}")
    for w in uncovered[:15]: print(f"      {w}")
    json.dump(uncovered, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'master_uncovered.json'), 'w', encoding='utf-8'), ensure_ascii=False)

# ===== B. 3言語構造同一性 =====
print("\nB. 3言語構造同一性")
import hashlib
s_hash = {}
for L in ('JA','ZH','KO'):
    s = json.load(open(LP(rf"{BASE}\Esperanto-Kanji-Ruby-{L}\app_data\分解設定.json"), encoding='utf-8'))
    s_hash[L] = hashlib.md5(json.dumps(s, ensure_ascii=False, sort_keys=False).encode()).hexdigest()
print(f"   分解設定md5: JA={s_hash['JA'][:10]} ZH={s_hash['ZH'][:10]} KO={s_hash['KO'][:10]}  一致={len(set(s_hash.values()))==1}")
CSVN = {'JA':'エスペラント語根-日本語訳ルビ対応リスト.csv','ZH':'世界语词根-中文注释对应列表.csv','KO':'에스페란토 어근-한국어 번역 루비 대응 목록.csv'}
roots = {}
for L in ('JA','ZH','KO'):
    m = {}
    for row in csv.reader(open(LP(rf"{BASE}\Esperanto-Kanji-Ruby-{L}\app_data\{CSVN[L]}"), encoding='utf-8')):
        if len(row) >= 2 and row[0] and '#' not in row[0]:
            r = circ(row[0].strip())
            if r and row[1].strip(): m[r] = row[1].strip()
    roots[L] = m
    print(f"   語根CSV({L}): {len(m)}語根(グロス有)")
ja, zh, ko = set(roots['JA']), set(roots['ZH']), set(roots['KO'])
print(f"   語根集合: JA∖ZH={len(ja-zh)} JA∖KO={len(ja-ko)} ZH∖JA={len(zh-ja)} KO∖JA={len(ko-ja)} ZH∖KO={len(zh-ko)} KO∖ZH={len(ko-zh)}")

# ===== C. カバレッジ差の実例 =====
print("\nC. 語根グロスのカバレッジ差(分解に影響し得る差)")
for label, diff in [('JAのみ(ZH欠落)', sorted(ja-zh)), ('JAのみ(KO欠落)', sorted(ja-ko)),
                    ('ZHのみ(JA欠落)', sorted(zh-ja)), ('KOのみ(JA欠落)', sorted(ko-ja))]:
    print(f"   {label}: {len(diff)}  例: {diff[:12]}")
json.dump({'ja_not_zh': sorted(ja-zh), 'ja_not_ko': sorted(ja-ko), 'zh_not_ja': sorted(zh-ja), 'ko_not_ja': sorted(ko-ja)},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'root_coverage_diff.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
