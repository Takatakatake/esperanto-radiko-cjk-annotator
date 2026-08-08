# -*- coding: utf-8 -*-
"""第108R: ラテン固定語根の語尾変化形・接尾辞形に空いた穴を語スコープで是正する。
   DRY既定 / --apply / --frozen 必須。

■ 何を直すか(2026-08-04)
  マスターは大小文字で同綴り衝突を弁別する(export は大小保存):
      Petr/o  -> Petr/o (聖ペトロ; ラテン維持)   petr/o -> 岩ᴾ/o (岩)
      Krist/o -> Krist/o                        krist/an/o -> krist/员/o (語根はラテン)
      Oceani/o-> Oceani/o                       eŭropi/o -> 金ᴱᵁ̆/o (元素ユウロピウム)
  アプリは基本形(Petro/Petra/Oceanio/ĉina…)に恒等キーを持つが語尾変化形が漏れており、
  前方一致の断片スープが語根セグメントを壊す:
      Petroj -> 岩ᴾoj / Krista -> Kr家a / Kristujo -> 叫s侧柏o / eŭropismo -> 金ᴱᵁ̆smo
      ĉine -> ĉ女e / kafajn -> ka精ᶠ (語頭食い: fajn=精ᶠ) / Petrajn -> Pe车ᵀ (trajn=车ᵀ)
  これは R76-77「見出しだけ直して語尾変化形を落とす」の残存クラス。

■ 裁定ルール(発明ゼロ)
  1. 対象は測定で実際に壊れている語形だけ(大小変種も個別に測る)。
  2. ★LEAVE: 大文字語形でも、小文字形がマスター見出しに実在するものは触らない。
       Petrigi -> 岩ᴾ使i は文頭の petr/ig/i⟦岩ᴾ/使/i⟧(石化する)の正読であり得るため保持。
  3. 値 = 語根そのまま(ラテン) + 尾部。尾部は
       文法語尾(o/on/oj/ojn/a/an/aj/ajn/e) と umi(um はラテン固定) -> 素のラテン
       生産的接尾辞 -> islam 族(全形が現行アプリで正しく描画される兄弟)の実描画から
                      マークアップごと抽出した断片を使う。期待表層を表で照合し fail-closed。
       接尾辞漢字は全てマスター実在: kaf/uj/o⟦kaf/器/o⟧ islam/ist/o⟦islam/家/o⟧
       islam/an/o⟦islam/员/o⟧ islam/ism/o⟦islam/主义/o⟧ islam/ig/i⟦islam/使/i⟧
       petr/iĝ/i⟦岩ᴾ/成/i⟧ reĝ/in/o⟦王/女/o⟧ latin/ec/o⟦latin/性/o⟧
  4. 小文字 oceani*/petr* は正当な既存割当(ocean=洋 の派生・petr=岩ᴾ)と衝突し得るため
     対象にしない。大文字のみ(oceani は大文字 Oceani だけ、petr も大文字 Petr だけ)。
  5. esperant* は KANJI_DECOMPOSE 政策(望在)なので対象外。

■ 安全設計(fix_kanji_export_faithful.py 第69R の作法を踏襲)
  1. 追加キーは空白パディングの完全一致キー。その語形にしか発火しない。
  2. 挿入位置は「自分を部分文字列として含む既存キーの直後、無ければ先頭」
     (包含判定は約物パディング後の形。第68R確定の作法)。
  3. 再実行できるように、前回の投入分($R108A)を外して測り、入れ直す(冪等)。
  4. 適用後の検証は呼び出し側のゲート(両基準監査の不一致数不変・3言語構造一致・退行0)。
     ★対象語形は両監査の母集団(マスター見出し表層)に含まれないため、
       監査の不一致数が1件でも動いたら巻き添え退行である。
"""
import json, os, re, sys, argparse, collections
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--frozen', required=True, help='凍結マスターのディレクトリ')
ap.add_argument('--report', default='')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
TAGID = '$R108A'
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
RT = re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>'); TAG = re.compile(r'<[^>]+>')
def disp(seg): return TAG.sub('', RT.sub('', seg)).strip()

# ── 約物パディング(エンジンの照合形。fix_kanji_export_faithful.py と同一) ──────
_BOL = chr(1)
_HAT12 = ''.join(chr(c) for c in (264, 265, 284, 285, 292, 293, 308, 309, 348, 349, 364, 365))
_LATEXT = chr(192) + '-' + chr(214) + chr(216) + '-' + chr(246) + chr(248) + '-' + chr(591)
_APOS = chr(39) + chr(8217)
_KEEP = ('A-Za-z0-9' + _HAT12 + _LATEXT + chr(37) + chr(64) + _APOS
         + ' ' + chr(10) + chr(13) + chr(1))
_PAD = re.compile('([^' + _KEEP + '])')
_LTR = 'A-Za-z' + _HAT12 + _LATEXT
_APOS_R = re.compile('[' + _APOS + '](?=[' + _LTR + '])')
def padkey(s):
    s = _PAD.sub(lambda m: ' ' + _BOL + m.group(1) + _BOL + ' ', s)
    return _APOS_R.sub(lambda m: m.group(0) + _BOL + ' ', s)

def splice(GG, new_rows):
    cand = [(i, padkey(e[0])) for i, e in enumerate(GG)
            if isinstance(e[0], str) and (' ' in e[0].strip() or _PAD.search(e[0]))]
    groups = collections.defaultdict(list)
    for r in new_rows:
        k = padkey(r[0]); p = 0
        for i, mk in cand:
            if len(mk) > len(k) and k in mk: p = max(p, i + 1)
        groups[p].append(r)
    out = list(GG)
    for p in sorted(groups, reverse=True):
        out[p:p] = groups[p]
    return out

# ── 凍結マスター: 小文字見出し(LEAVE 判定)────────────────────────────
inj_lower = {}
RE_INJ = re.compile(r'^([^⟦:]+)⟦([^⟧]+)⟧')
with open(LP(os.path.join(A.frozen, '漢字注入_学習者版_20260620.txt')), encoding='utf-8') as fp:
    for ln in fp:
        m = RE_INJ.match(ln)
        if not m: continue
        w = circ(m.group(1).strip())
        if ' ' in w: continue
        surf = w.replace('/', '').replace('-', '')
        inj_lower.setdefault(surf.lower(), w + '⟦' + circ(m.group(2).strip()) + '⟧')

# ── アプリのエンジン(JA。値は3言語共通) ─────────────────────────────
app_dir = os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA')
sys.path.insert(0, app_dir)
import esp_text_replacement_module as M
dJA = json.load(open(LP(os.path.join(app_dir, 'app_data', '置換リスト_漢字.json')), encoding='utf-8'))
GL = dJA['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = dJA['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
GGm = [e for e in dJA[KEY] if not (len(e) > 2 and isinstance(e[2], str) and TAGID in e[2])]
ps = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_skip.txt'))
pl = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_localcapture.txt'))
def conv(t):
    return M.orchestrate_comprehensive_esperanto_text_replacement(
        t, ps, GL, pl, GGm, G2, '汉字替换_大小调整')

# ── 接尾辞断片を islam 族の実描画から抽出(fail-closed) ─────────────────
SUF_EXPECT = {'ujo': '器o', 'isto': '家o', 'ano': '员o', 'ismo': '主义o',
              'igi': '使i', 'iĝi': '成i', 'ino': '女o', 'eco': '性o'}
SUF_HTML = {}
for t, exp_surface in SUF_EXPECT.items():
    raw = conv(' islam' + t + ' ').strip()
    if not raw.startswith('islam'):
        raise SystemExit(f'接尾辞抽出失敗(語幹が壊れた): islam{t} -> {raw!r}')
    frag = raw[len('islam'):]
    ks = TAG.sub('', RT.sub('', frag)).strip()
    if ks != exp_surface:
        raise SystemExit(f'接尾辞抽出失敗(表層不一致): {t} -> {ks!r} 期待 {exp_surface!r}')
    # rt を剥いだエス表層が t 自身に戻ることも確認
    esp = []
    pos = 0
    for m in re.finditer(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', frag, re.S):
        if m.start() > pos: esp.append(TAG.sub('', frag[pos:m.start()]))
        esp.append(re.sub(r'<br\s*/?>', '', TAG.sub('', m.group(2))))
        pos = m.end()
    if pos < len(frag): esp.append(TAG.sub('', frag[pos:]))
    if ''.join(esp) != t:
        raise SystemExit(f'接尾辞抽出失敗(rt復元不一致): {t} -> {"".join(esp)!r}')
    SUF_HTML[t] = frag
BARE = {'o', 'on', 'oj', 'ojn', 'a', 'an', 'aj', 'ajn', 'e', 'umi'}

# ── 候補の生成と測定 ────────────────────────────────────────────
FAMS = [('ĉin', ['ĉin', 'Ĉin']),
        ('eŭrop', ['eŭrop', 'Eŭrop']),
        ('krist', ['krist', 'Krist']),
        ('oceani', ['Oceani']),
        ('petr', ['Petr']),
        ('kaf', ['kaf', 'Kaf'])]
TAILS = ['o', 'on', 'oj', 'ojn', 'a', 'an', 'aj', 'ajn', 'e', 'umi',
         'ujo', 'isto', 'ano', 'ismo', 'igi', 'iĝi', 'ino', 'eco']
cands = [(fam, st, t, st + t) for fam, stems in FAMS for st in stems for t in TAILS]
SEP = '◆'
out = conv(' ' + (' ' + SEP + ' ').join(w for _, _, _, w in cands) + ' ')
parts = out.split(SEP)
if len(parts) != len(cands):
    parts = [conv(' ' + w + ' ') for _, _, _, w in cands]

entries, report = [], []
stat = collections.Counter()
for (fam, st, t, w), seg in zip(cands, parts):
    ad = disp(seg)
    if ad[:len(st)] == st:
        stat['OK(語根素通し)'] += 1; continue
    if w[:1].isupper() and w.lower() in inj_lower:
        stat['LEAVE(小文字master見出し)'] += 1
        report.append({'w': w, 'app': ad, 'action': 'LEAVE', 'why': inj_lower[w.lower()]})
        continue
    val = w if t in BARE else st + SUF_HTML[t]
    ks = TAG.sub('', RT.sub('', val)).strip()
    expected_surface = w if t in BARE else st + SUF_EXPECT[t]
    if ks != expected_surface:
        raise SystemExit(f'値構築の検証失敗: {w} -> {ks!r} 期待 {expected_surface!r}')
    entries.append([' ' + w + ' ', ' ' + val + ' ', None])
    stat['★是正'] += 1
    report.append({'w': w, 'app': ad, 'action': 'FIX', 'new': expected_surface})

print('選定: ' + ' / '.join(f'{k}={v}' for k, v in stat.most_common()))
for r in report:
    if r['action'] == 'FIX':
        print(f"   {r['w']:<12} {r['app']:<14} -> {r['new']}")
    else:
        print(f"   {r['w']:<12} {r['app']:<14} 保持({r['why']})")
if A.report:
    json.dump(report, open(LP(A.report), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'report: {A.report}')
if DRY:
    print('\n(DRY-RUN: --apply で書込)'); sys.exit(0)

for lang in ('JA', 'ZH', 'KO'):
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_漢字.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    gg = [e for e in d[KEY]
          if not (len(e) > 2 and isinstance(e[2], str) and TAGID in e[2])]
    removed = len(d[KEY]) - len(gg)
    used = {e[2] for e in gg if len(e) > 2}
    where = {}
    for i, e in enumerate(gg):
        if isinstance(e[0], str) and e[0] not in where: where[e[0]] = i
    rows, replaced = [], 0
    for n, (k, v, _) in enumerate(entries):
        j = where.get(k)
        if j is not None:
            gg[j] = [k, v, gg[j][2]]; replaced += 1; continue
        ph = f' {TAGID}{n:05d}{"" if lang == "JA" else lang}$ '
        if ph in used: raise SystemExit(f'placeholder collision: {ph}')
        rows.append([k, v, ph])
    d[KEY] = splice(gg, rows)
    atomic_file_copy(LP(path), LP(path + '.bak_preR108A'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 挿入 {len(rows)} / 既存値の差替 {replaced} '
          f'(旧投入 {removed} 件を除去 / 全域 {len(gg)} -> {len(d[KEY])})')
print('適用完了')
