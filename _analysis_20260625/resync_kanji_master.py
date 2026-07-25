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
sys.path.insert(0, os.path.join(BASE, '_analysis_20260625'))
from build_fake_coarse_5e_transition_review import (
    validate as validate_fake_coarse_5e_transition_review,
)
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
# 2026-07-25 第65R: 語根マップの「未対応」は漢字値ではなくカテゴリ名。
# マスター方針書 漢字化方針_v2 §2 用語定義:
#   「未対応 | 意味訳不能でラテン語形のまま残す語根。」
# 漢字と同じCJK文字列であるため既存の「CJKを含むか」判定を素通りし、第64Rまで
# authority に漢字値として取り込まれていた。結果、配信3アプリが literal「未対応」を
# 出力していた(angl/german/rus/ĉin/eŭrop/kaf/islam/latin/Krist/Petr/Oceani/
# esperant/um の13語根、置換リスト内949箇所。例: "la angla"→"la 未対応a")。
# 正本の描画層(注入版・注入エクスポート・_p_work.csv・_homonym*.tsv)には
# この文字列が一切現れない=ラテン維持が正しい描画である、が根拠。
#
# 正しい扱いは「語根ごと落とす」ではなく「ラテン固定(恒等値)で登録する」。
# 落とすと語根の綴りが保護されなくなり、内側の短い語根が発火して別の偽分解になる
# (実測: ĉin→ĉ/in で ĉina→ĉ女a、latin→l/at/in で latina→l被女a など52派生形)。
# 恒等値で登録すると置換表に長さ順で載るため内側の2字語根より先に一致し、
# 綴りをそのまま保ったまま保護できる。gen_replacement は CSV の
# `E_root == hanzi_or_meaning` 行をルビ無しの素のラテンとして扱う既存機構
# (gen_replacement.py の局部置換構築部)を持つので、描画も追加処理なしで正しい。
MASTER_LATIN_SENTINEL = '未対応'
master = {}
latin_sentinel_roots = []
for ln in pinned_text('_kanji_map_master.tsv').splitlines():
    ps = ln.rstrip('\n').split('\t')
    if len(ps) >= 3 and ps[1] and ps[2]:
        root, val = circ(ps[1].strip()), ps[2].strip()
        if val == MASTER_LATIN_SENTINEL:
            latin_sentinel_roots.append(root)
            master[root] = root      # ラテン固定(恒等値)
            continue
        master[root] = val
disp = {}
for ln in pinned_text('_identifier_sidecar.tsv').splitlines():
    ps = [p.strip().strip('"') for p in ln.rstrip('\n').split('\t')]
    if len(ps) >= 5 and ps[0] and ps[4]:
        if ps[4].strip() == MASTER_LATIN_SENTINEL:
            continue
        disp[circ(ps[0])] = ps[4]
_sentinel_set = set(latin_sentinel_roots)
authority = {r: (r if r in _sentinel_set else disp.get(r, k))
             for r, k in master.items()}
if MASTER_LATIN_SENTINEL in set(authority.values()):
    raise SystemExit(
        f'Kanji master sentinel leaked into authority: {MASTER_LATIN_SENTINEL!r}'
    )
for _r in _sentinel_set:
    if authority.get(_r) != _r:
        raise SystemExit(f'latin-lock root lost its identity value: {_r!r}')
print(f"正本語根: {len(authority)} (識別子込み表示形 {len(disp)})")
print(f"ラテン固定(未対応=恒等値)の語根: {len(latin_sentinel_roots)} "
      f"{sorted(latin_sentinel_roots)}")

# --- 2) 語単位: 漢字注入_学習者版 ⟦…⟧ → word_kanji ---
# 2026-07-24 met同形異義修正(マスター裁定②案A): an/enをGRAMから除外。
# met/an/o(メタン)のanはアルカン接尾-aneで文法語尾でない→剥がすと裸met=甲に誤爆し
# met/i(置く)と衝突する。an/en非除去でmet/an=甲/an語幹を保持し裸metはmet/i/met/o由来=置。
# (成員-anも城/员ᴬ等でkanji化されるのが現行マスター描画=注入版に忠実)。
GRAM = {'o','a','i','e','u','n','j','oj','on','aj','as','is','os','us'}
wk_new = {}
bad = 0
valid_stem_nosl = set()
for ln in pinned_text('漢字注入_学習者版_20260620.txt').splitlines():
    m = re.match(r'^([^:⟦{]+)⟦([^⟧]+)⟧', ln.strip().lstrip('﻿'))
    if not m: continue
    dec = circ(m.group(1).strip()).replace('-', '')
    kj = circ(m.group(2).strip())
    dp = [p for p in dec.split('/') if p]
    kp = [p for p in kj.split('/') if p]
    # 見出しの「全部品」「末尾1部品を除く語幹」を正当キー集合に収集(第61R裁定,
    # 複数語句見出しも含む=61R実測手順と同一)
    if dp:
        valid_stem_nosl.add(''.join(p.lower() for p in dp))
        if len(dp) > 1:
            valid_stem_nosl.add(''.join(p.lower() for p in dp[:-1]))
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
# 2026-07-24 第61R裁定の恒久化: 中間語幹の過収穫防止フィルタ。
# 例: but/an/on/o から末尾GRAM連続剥ぎで but/an が生まれると butano(語根but+ano)
# を丁an化する誤爆になる。キーのnosl(スラッシュ除去)が正当集合(=いずれかの見出しの
# 「全部品」or「末尾1部品を除いた語幹」)に一致するもののみ残す。
wk_new = {k: v for k, v in wk_new.items()
          if k.replace('/', '') in valid_stem_nosl}
print(f"語単位(注入版→word_kanji): {len(wk_new)} (形不一致スキップ {bad})")
print("  例:", {k: ''.join(g for _, g in v) for k, v in list(wk_new.items())[:5]})
amp = [k for k in wk_new if k.startswith('amplifik')]
print("  amplifik系:", {k: ''.join(g for _, g in wk_new[k]) for k in amp[:3]})
if bad:
    raise SystemExit(
        f"Kanji master resync aborted: {bad} injected forms have mismatched "
        "Esperanto/Kanji piece counts"
    )

# 2026-07-24 master adjudication ③: promil's pro is Latin pro(=per), kept latin
# like its pro/cent family; 因ᴾ(causal) was wrong.  When the injection master
# provides pro/mil (it does), the master render wins; the locally derived 因ᴾ
# pairs remain only as a fallback for older masters predating the 5E delta.
_final_5e_path = os.path.join(
    BASE, '_analysis_20260625', '_fake_coarse_5e_transition_review.json',
)
with open(LP(_final_5e_path), encoding='utf-8') as _fp:
    _final_5e = json.load(_fp)
validate_fake_coarse_5e_transition_review(_final_5e)
_promil_entry = _final_5e['entries'][0]
_promil_stem = '/'.join(
    piece for piece in _promil_entry['learner_decomposition'].split('/')
    if piece and piece not in GRAM
)
if _promil_entry.get('learner_line') != 53890 or _promil_stem != 'pro/mil':
    raise SystemExit(
        f'5E promil transition drift: stem={_promil_stem!r} '
        f'entry={_promil_entry!r}'
    )
if _promil_stem in wk_new:
    print(
        f"5E pro/mil: injection master provides {wk_new[_promil_stem]} "
        "(master authority; derived fallback unused)"
    )
else:
    _promil_pairs = [
        ['pro', authority.get('pro')],
        ['mil', authority.get('mil')],
    ]
    if _promil_pairs != [['pro', '因ᴾ'], ['mil', '千']]:
        raise SystemExit(
            f'5E promil Kanji fallback authority drift: pairs={_promil_pairs!r}'
        )
    wk_new[_promil_stem] = _promil_pairs
    print(f"5E reviewed word_kanji fallback: {_promil_stem} -> {_promil_pairs}")

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
