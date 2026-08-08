# -*- coding: utf-8 -*-
"""第114R新設: 「ルビの分節はマスターの分節の**併合**でなければならない」ゲート。測定のみ。

■ 何を守るのか(ユーザー原則の機械化)
  注釈ルビは漢字化より粗くてよい(マスターの隣接片を1つにまとめてよい)。
  しかし**マスターが認めない位置で切ってはいけない**。
      OK : deoksiribozo  master de/oksi/rib/oz/o  ruby deoksi|riboz|o     (併合=粗い)
      NG : alteon        master alte/o            ruby alt|«eon»          (語幹を切断)
      NG : ocelon        master ocel/o            ruby «o»cel|«on»        (語頭が裸)

■ 既存3ゲートの死角
  62kゲートは「ルビが1つでもあれば注釈あり」と数えるため、語中・語頭に裸の断片が
  残っても検出できない。本ゲートはその死角を埋める。

■ 判定
  マスターexportが持つ表層 W(片列と表層が一致する行)について、
  ルビ値の分節境界が**マスターの境界の部分集合**であることを検査する。
  先頭(0)と語末は自明なので除外する。

■ 既知の許容差(第114R裁定・違反として数えるが是正対象外)
  - ハイフン複合の固有名詞(135件): マスターが Nov-Kaledoni を1片とするのに対し
    ルビはハイフンで割る。意味は壊れておらず第85R軸として別管理。
  - 感嘆詞の `!`(約60件): 句読点をルビ外に置くのは正常。
  - Temis(第74Rでコーパス実証6/6により裸化を撤回済み)・sendota(京大の実文
    「letero sendota」がsend/ot/aを支持)など、コーパスがアプリ側を支持する同綴り衝突。

第114R実測(app d58faaa時点): 照合 27,429 / 適合 27,212 / 違反 217 = 99.209%。
是正後も同値(是正した alte/ocel はマスターexportに変化形表層が無く母集団外)。
"""
import io, json, os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return p if p.startswith(PFX) else PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
X = {'c^': 'ĉ', 'g^': 'ĝ', 'h^': 'ĥ', 'j^': 'ĵ', 's^': 'ŝ', 'u^': 'ŭ',
     'C^': 'Ĉ', 'G^': 'Ĝ', 'H^': 'Ĥ', 'J^': 'Ĵ', 'S^': 'Ŝ', 'U^': 'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
EXPORT = os.environ.get('ESP_KANJI_EXPORT') or (
    r'D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学'
    r'\エスペラントの漢字化プロジェクト総結集20260630'
    r'\エスペラント語根＿漢字割り当て＿20260630\_漢字割当エクスポート_学習者版_20260723.tsv')
if not os.path.exists(LP(EXPORT)):
    raise SystemExit(f'★マスターexportが見つからない: {EXPORT}')

master = {}
with io.open(LP(EXPORT), encoding='utf-8', errors='replace') as f:
    for ln in f:
        fs = ln.rstrip('\n').split('\t')
        if len(fs) < 4: continue
        surf = circ(fs[2].strip())
        pcs = [p for p in circ(fs[0].strip()).split('/') if p]
        if surf and pcs and ''.join(pcs) == surf:
            master.setdefault(surf, pcs)
print(f'マスター表層(片列==表層) {len(master):,}')

def segs_of(v):
    out, pos = [], 0
    for m in RUBY.finditer(v):
        if m.start() > pos:
            t = TAG.sub('', v[pos:m.start()])
            if t: out.append(('lit', t))
        out.append(('ruby', TAG.sub('', m.group(1))))
        pos = m.end()
    if pos < len(v):
        t = TAG.sub('', v[pos:])
        if t: out.append(('lit', t))
    return out

d = json.load(open(LP(os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA', 'app_data',
                                   '置換リスト_ルビ.json')), encoding='utf-8'))
checked = ok = 0
viol = []
for e in d[KEY]:
    if not (isinstance(e, list) and isinstance(e[0], str) and isinstance(e[1], str)): continue
    k = e[0].strip()
    P = master.get(k)
    if P is None: continue
    S = segs_of(e[1])
    if not S: continue
    flat = ''.join(t for _, t in S)
    if flat.strip() != k: continue
    checked += 1
    bnd, acc = set(), 0
    for p in P:
        acc += len(p); bnd.add(acc)
    lead = len(flat) - len(flat.lstrip())
    total = len(k)
    acc2 = 0; bad = []
    for kind, t in S:
        acc2 += len(t)
        pos = acc2 - lead
        if 0 < pos < total and pos not in bnd:
            bad.append(pos)
    if not bad:
        ok += 1; continue
    viol.append({'key': k, 'master': '/'.join(P),
                 'ruby': ''.join(('«' + t + '»' if kd == 'lit' else t + '|') for kd, t in S)})
del d
rate = ok / max(1, checked) * 100
print(f'照合 {checked:,} / 適合 {ok:,} / 違反 {len(viol):,} = {rate:.3f}%')
hy = sum(1 for v in viol if '-' in v['key'] or '-' in v['master'])
ex = sum(1 for v in viol if v['key'].endswith('!'))
print(f'  内訳: ハイフン複合 {hy} / 感嘆詞`!` {ex} / その他 {len(viol) - hy - ex}')
for v in viol[:12]:
    print(f"    {v['key']:<20} master={v['master']:<24} ruby={v['ruby'][:44]}")
BASE = 217
if len(viol) > BASE:
    print(f'★違反が基線 {BASE} 件を超えた: 新たな分節破れの疑い')
    raise SystemExit(1)
print(f'マスター分節への併合適合(ルビ軌道): PASS (基線 {BASE} 件以内)')
