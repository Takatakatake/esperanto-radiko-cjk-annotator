# -*- coding: utf-8 -*-
"""第18R: 漢字割り当てマスター正本(エスペラント語根＿漢字割り当て＿20260630)との全面再同期。
   正本(読取専用): _kanji_map_master.tsv + _identifier_sidecar.tsv(識別子込み表示形)
                  + 漢字注入_学習者版(語単位の漢字形 ⟦…⟧)
   再構築対象: app_data 漢字対応CSV(3アプリ) / out/kanji_root.csv / out/word_kanji.json
   --write で書込。"""
import csv, sys, os, re, json, hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
WRITE = '--write' in sys.argv
BASE = str(Path(__file__).resolve().parents[1])
ROOT = str(Path(BASE).parent)
KM = os.environ.get(
    'ESP_KANJI_MASTER_PATH',
    str(Path(ROOT) / "エスペラント語根＿漢字割り当て＿20260630"),
)
OUT = os.path.join(BASE, '_analysis_20260625', 'out')
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ','C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s

expected_manifest_path = os.environ.get('ESP_EXPECTED_KANJI_MASTER_MANIFEST')
expected_files = None
if expected_manifest_path:
    with open(LP(expected_manifest_path), encoding='utf-8') as fp:
        expected_manifest = json.load(fp)
    if expected_manifest.get('schema_version') != 1:
        raise RuntimeError('unsupported Kanji master manifest schema')
    expected_files = {row['name']: row for row in expected_manifest['files']}

def pinned_text(name):
    path = os.path.join(KM, name)
    raw = open(LP(path), 'rb').read()
    if expected_files is not None:
        expected = expected_files.get(name)
        if expected is None:
            raise RuntimeError(f'Kanji master file is not pinned: {name}')
        actual_sha = hashlib.sha256(raw).hexdigest().upper()
        if len(raw) != expected['bytes'] or actual_sha != expected['sha256']:
            raise RuntimeError(
                f'Kanji master drift: {name}: expected '
                f"{expected['bytes']} bytes/{expected['sha256']}, got "
                f'{len(raw)} bytes/{actual_sha}'
            )
    return raw.decode('utf-8')

# --- 1) 正本の語根→表示形(識別子込み) ---
master = {}
for ln in pinned_text('_kanji_map_master.tsv').splitlines():
    ps = ln.rstrip('\n').split('\t')
    if len(ps) >= 3 and ps[1] and ps[2]:
        master[circ(ps[1].strip())] = ps[2].strip()
disp = {}
for ln in pinned_text('_identifier_sidecar.tsv').splitlines():
    ps = [p.strip().strip('"') for p in ln.rstrip('\n').split('\t')]
    if len(ps) >= 5 and ps[0] and ps[4]:
        disp[circ(ps[0])] = ps[4]
authority = {r: disp.get(r, k) for r, k in master.items()}
print(f"正本語根: {len(authority)} (識別子込み表示形 {len(disp)})")

# --- 2) 語単位: 漢字注入_学習者版 ⟦…⟧ → word_kanji ---
GRAM = {'o','a','i','e','u','n','j','oj','on','aj','an','en','as','is','os','us'}
wk_new = {}
bad = 0
for ln in pinned_text('漢字注入_学習者版_20260620.txt').splitlines():
    m = re.match(r'^([^:⟦{]+)⟦([^⟧]+)⟧', ln.strip().lstrip('﻿'))
    if not m: continue
    dec = circ(m.group(1).strip()).replace('-', '')
    kj = circ(m.group(2).strip())
    dp = [p for p in dec.split('/') if p]
    kp = [p for p in kj.split('/') if p]
    if len(dp) != len(kp) or not dp: bad += 1; continue
    # 語幹化(末尾文法語尾を両列から除去)
    while dp and dp[-1].lower() in GRAM and kp[-1].lower() == dp[-1].lower():
        dp.pop(); kp.pop()
    if not dp: continue
    # CJK文字を含まない語形は登録不要(ラテン素通しが正しい挙動)
    if not any(re.search(r'[⺀-鿿豈-﫿]', k) for k in kp):
        continue
    key = '/'.join(p.lower() for p in dp)
    if key in wk_new: continue  # 先勝ち(同語幹の重複派生)
    wk_new[key] = [[p.lower(), k] for p, k in zip(dp, kp)]
print(f"語単位(注入版→word_kanji): {len(wk_new)} (形不一致スキップ {bad})")
print("  例:", {k: ''.join(g for _, g in v) for k, v in list(wk_new.items())[:5]})
amp = [k for k in wk_new if k.startswith('amplifik')]
print("  amplifik系:", {k: ''.join(g for _, g in wk_new[k]) for k in amp[:3]})

if WRITE:
    # 3) app_data CSV(3アプリ) + out/kanji_root.csv
    hdr = None
    src = LP(os.path.join(BASE, 'Esperanto-Kanji-Ruby-JA', 'app_data', '世界语词根-汉字对应列表_参照2新割当_7791.csv'))
    rows_old = list(csv.reader(open(src, encoding='utf-8')))
    hdr = rows_old[0] if rows_old and '#' in ''.join(rows_old[0]) or (rows_old and not rows_old[0][0].islower()) else None
    newrows = sorted(authority.items())
    for L in ('JA', 'ZH', 'KO'):
        tgt = LP(os.path.join(BASE, f'Esperanto-Kanji-Ruby-{L}', 'app_data', '世界语词根-汉字对应列表_参照2新割当_7791.csv'))
        with open(tgt, 'w', encoding='utf-8', newline='') as fp:
            w = csv.writer(fp, lineterminator='\n')
            for r, k in newrows: w.writerow([r, k])
    with open(LP(os.path.join(OUT, 'kanji_root.csv')), 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, lineterminator='\n')
        for r, k in newrows: w.writerow([r, k])
    print(f"CSV再構築: {len(newrows)}語根 ×(3アプリ+out)")
    # 4) word_kanji.json 全面再構築(正本注入版ベース)
    json.dump(wk_new, open(LP(os.path.join(OUT, 'word_kanji.json')), 'w', encoding='utf-8'), ensure_ascii=False)
    print(f"word_kanji.json 再構築: {len(wk_new)}語形")
else:
    print("(dry-run: --write で書込)")
