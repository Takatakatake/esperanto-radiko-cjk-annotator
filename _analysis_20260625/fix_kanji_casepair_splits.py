# -*- coding: utf-8 -*-
"""第110R: 大小文字ペア(マスターが大小で描画を割る357表層)のパラダイム内分裂5件を是正。
   DRY既定 / --apply / --frozen 必須。

■ 背景(2026-08-05)
  マスターexportは同綴りを大小文字で裁定し分ける(Rod/o→Rodo=ロードス島ラテン vs
  rod/o→泊o=停泊地)。全357ペアを掃引した結果、大文字側の基本形と語尾変化形で
  扱いが割れている(=パラダイム内分裂)のは5語族だけだった:
    Ido:  基本形Ido=ラテン✓ / Idon→子on ✗   (京大コーパスの Idon は全て「イド語」対格)
    Rodo: 基本形→泊o ✗ / Rodon等=ラテン✓(第76F是正済)
    Marta/Mateo/Kana: 基本形=ラテン✓ / 対格→三月an・茶ᴹon・苇an ✗

■ 裁定(発明ゼロ・牛を殺さない)
  FIX = 恒等ラテン5キーのみ: Idon / Rodo / Martan / Mateon / Kanan
    いずれもマスターの大文字行(Id/o→Ido等)が明示のラテン裁定。
    対格単数は「文頭に対格形容詞が来る倒置」がほぼ存在しないため逆読みリスク消失的。
  LEAVE(意図的に触らない):
    Idoj/Idojn      … 文頭の「Idoj de la reĝo」(子孫たち)が実在読み。子oj を保持
    Martaj/Martajn, Kanaj/Kanajn … 文頭の形容詞複数(三月の/葦の)が実在読み
    Mateoj/Mateojn  … 両読みとも稀。churn最小化で据置
    全大文字(RODO等) … アプリの全大文字バケットは小文字由来で自己整合。マスター裁定なし
    非分裂の344ペア  … Blanka(白a)/Bordo(岸o)等は文頭大文字=普通語の正読が支配的。
                      第69R「固有名詞928件は保留」裁定を維持
  小文字側(ido/idon=子・rodo=泊・marta=三月・mateo=茶ᴹ・kana=苇)は一切触らない。

■ 安全設計(第69R/108Rの作法)
  1. 各キーについて、凍結マスターexportに「大文字表層→ラテン維持(f3==表層)」の行が
     実在することを実行時に検証(fail-closed)。
  2. 空白パディング完全一致キー・恒等値。挿入位置は包含キーの直後(無ければ先頭)。
  3. $R110A タグで冪等(再実行時は旧投入分を外してから入れ直す)。
  4. 対象はマスター見出し表層のためエクスポート監査に映る:
     期待 = 'Rodo' の1件が解消(932→931)し、新規不一致0。
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
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
TAGID = '$R110A'
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s

# (キー語形, マスター根拠となる大文字見出し表層)
TARGETS = [('Idon', 'Ido'), ('Rodo', 'Rodo'), ('Martan', 'Marta'),
           ('Mateon', 'Mateo'), ('Kanan', 'Kana')]

# ── fail-closed: マスターexportの大文字ラテン行を検証 ─────────────────
latin_caps = set()
exp = os.path.join(A.frozen, '_漢字割当エクスポート_学習者版_20260723.tsv')
for ln in open(LP(exp), encoding='utf-8'):
    if ln.startswith('#'): continue
    ps = ln.rstrip('\n').split('\t')
    if len(ps) < 4: continue
    surf = circ(ps[2].strip())
    if surf[:1].isupper() and circ(ps[3].strip()) == surf:
        latin_caps.add(surf)
for w, base in TARGETS:
    if base not in latin_caps:
        raise SystemExit(f'マスターexportに大文字ラテン行が見つからない: {base} (対象 {w})')
print(f'マスター検証OK: ' + ' / '.join(f'{w}(根拠 {b}→ラテン)' for w, b in TARGETS))

# ── 約物パディングと挿入位置(既存作法) ─────────────────────────────
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

entries = [[' ' + w + ' ', ' ' + w + ' ', None] for w, _ in TARGETS]
if DRY:
    for k, v, _ in entries: print(f'  追加(恒等): {k!r}')
    print('(DRY-RUN: --apply で書込)'); sys.exit(0)

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
    atomic_file_copy(LP(path), LP(path + '.bak_preR110A'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 挿入 {len(rows)} / 既存値の差替 {replaced} '
          f'(旧投入 {removed} 件を除去 / 全域 {len(gg)} -> {len(d[KEY])})')
print('適用完了')
