# -*- coding: utf-8 -*-
"""第77R: export忠実化した語の**文法語尾変化形**を同じ無発明機構で埋める。DRY既定 / --apply。

■ なぜ要るか(第76Rで実測)
  fix_kanji_export_faithful.py はマスターexportの**見出し表層そのもの**にしかキーを置かない。
  そのため基本形だけが直り、語尾変化形は旧来の語根置換に落ちて食い違う:

      neu^tonmetro  -> neu^ton米o   (是正済)
      neu^tonmetroj -> neu^ton计ᴹoj (★旧値のまま)

  実測 319候補中 316件が食い違い。単に未是正なだけでなく、語尾まで巻き込んで
  壊れる例がある:
      alkanalojn : 向渠ojn   (alkanal が alkan+al に食われた上に語尾も別解釈)
      arg^entanon: 银员分     (語尾 -on が 分 に化けている)
  実文はほぼ必ず語尾変化するので、こちらの方が読者への影響は大きい。

■ 構築方法(発明ゼロ・第76Rと同一)
  export の4列 f0=エス語根分解 / f1=漢字分解 / f2=表層 / f3=漢字表層 について、
  **末尾の片が文法語尾そのもの**(f0/f1 とも同じ1〜2字のラテン)である見出しに限り、
  その末尾片だけを差し替えた (f0',f1',f2',f3') を作り、f1' から同じ output_format で組む。

      abĵur/i | abĵur/i | abĵuri | abĵuri     -- 末尾片 i がラテン一致
        -> abĵur/as | abĵur/as | abĵuras | abĵuras
      akinezi/o | 无ᴬ动ᴷᶻ/o | akinezio | 无ᴬ动ᴷᶻo
        -> akinezi/oj | 无ᴬ动ᴷᶻ/oj | akinezioj | 无ᴬ动ᴷᶻoj

  漢字片は一切触らないので、マスターに無い割り当てが生まれる余地が無い。

■ 安全設計
  1. 末尾片が f0/f1 で同一のラテン語尾でなければ対象外(漢字が語尾に掛かる語を触らない)。
  2. 生成した語形が**別のマスター見出し**なら対象外(その語自身の管轄。跨ぎ捕獲の防止)。
  3. 組んだ後、漢字表層 == f3' かつ エス表層 == f2' を検証。外れたら捨てる(fail-closed)。
  4. 既に正しく描画できている語形には何も入れない。
  5. 再実行できるように、前回の投入分($R76F)を外して測り、入れ直す。
  6. 挿入位置は第68Rで確定した作法(自分を部分文字列として含む既存キーの直後、無ければ先頭。
     包含判定は約物パディング後の形で行う)。
"""
import json, os, re, sys, argparse, collections, hashlib
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump
from gen_replacement import load_app_replacement_helper

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--frozen', required=True)
ap.add_argument('--export-name', default='_漢字割当エクスポート_学習者版_20260723.tsv')
ap.add_argument('--report', default='')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
FMT = 'HTML格式_Ruby文字_大小调整_汉字替换'
MARK = '$R76F'
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
BR = re.compile(r'<br\s*/?>')

# ── 約物パディング(エンジンの照合形を再現) ──────────────────────────
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

# ── マスター export ────────────────────────────────────────────
exp_path = os.path.join(A.frozen, A.export_name)
raw = open(LP(exp_path), 'rb').read()
print(f'export: {os.path.basename(exp_path)} sha256={hashlib.sha256(raw).hexdigest()[:16]}')
L_ = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
def ok_surface(s): return bool(re.fullmatch('[' + L_ + ']{1,40}', s))
EXP = collections.defaultdict(list)
for ln in raw.decode('utf-8', 'replace').splitlines():
    if ln.startswith('#'): continue
    f = ln.rstrip('\n').split('\t')
    if len(f) < 4: continue
    surf = circ(f[2].strip())
    if not ok_surface(surf): continue
    EXP[surf].append((circ(f[0].strip()), circ(f[1].strip()), surf, circ(f[3].strip())))
print(f'export 実在語: {len(EXP)}')
ALL_SURF = set(EXP)

# ── アプリ ────────────────────────────────────────────────────
app_dir = os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA')
sys.path.insert(0, app_dir)
import esp_text_replacement_module as M
helper = load_app_replacement_helper(app_dir)
with open(LP(os.path.join(app_dir, 'app_data', 'char_widths.json')), encoding='utf-8') as fp:
    CW = json.load(fp)
dJA = json.load(open(LP(os.path.join(app_dir, 'app_data', '置換リスト_漢字.json')), encoding='utf-8'))
GL = dJA['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = dJA['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
GGm = [e for e in dJA[KEY] if not (len(e) > 2 and isinstance(e[2], str) and MARK in e[2])]
ps = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_skip.txt'))
pl = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_localcapture.txt'))
def conv(t):
    return M.orchestrate_comprehensive_esperanto_text_replacement(
        t, ps, GL, pl, GGm, G2, FMT)
def kanji_surface(html):
    s = re.sub(r'<rt[^>]*>.*?</rt>', '', html, flags=re.S)
    return TAG.sub('', s).strip()

def build(f0, f1):
    e_ps = f0.split('/'); k_ps = f1.split('/')
    if len(e_ps) != len(k_ps): return None
    buf = []
    for e, k in zip(e_ps, k_ps):
        if not e:
            if k: return None
            continue
        if k == e: buf.append(e)
        else: buf.append(helper.output_format(e, k, FMT, CW))
    return ''.join(buf)

def verify(val, f2, f3):
    if kanji_surface(val) != f3: return False
    esp = []; pos = 0
    for m in RUBY.finditer(val):
        if m.start() > pos: esp.append(TAG.sub('', val[pos:m.start()]))
        esp.append(BR.sub('', TAG.sub('', m.group(2))))
        pos = m.end()
    if pos < len(val): esp.append(TAG.sub('', val[pos:]))
    return ''.join(esp) == f2

# ── 対象: 前回 $R69E で入れた語(=マスターexportに合わせて是正した語) ──────
BASE = sorted({e[0].strip() for e in dJA[KEY]
               if len(e) > 2 and isinstance(e[2], str) and '$R69E' in e[2] and e[0].strip()})
print(f'$R69E 基本形 {len(BASE)}')

# 語尾のパラダイム(末尾片がその語尾そのものである見出しにのみ適用)
PARADIGM = {'o': ['oj', 'on', 'ojn'],
            'a': ['aj', 'an', 'ajn'],
            'e': ['en'],
            'i': ['as', 'is', 'os', 'us', 'u']}

def senses_for(w):
    """大小変種も含めて export の見出しを引く。"""
    if w in EXP: return EXP[w], False
    lw = w.lower()
    if lw in EXP: return EXP[lw], True
    return None, False

cands = []   # (新語形, f0', f1', f2', f3')
seen = set()
for w in BASE:
    sen, was_cased = senses_for(w)
    if not sen: continue
    f0, f1, f2, f3 = sen[0]
    p0 = f0.split('/'); p1 = f1.split('/')
    if len(p0) != len(p1) or not p0: continue
    end = p0[-1]
    if end not in PARADIGM: continue
    if p1[-1] != end: continue                    # 語尾に漢字が掛かる語は触らない
    # 表層は片の連結そのものでなければならない(ハイフン等が挟まる見出しは対象外)。
    # これが成り立つので、変化形の表層も片から機械的に導ける(f2/f3を切らない)。
    if f0.replace('/', '') != f2 or f1.replace('/', '') != f3: continue
    upper_all = (w == w.upper() and w != w.lower())
    title = (w[:1].isupper() and not upper_all)
    for suf in PARADIGM[end]:
        q0 = p0[:-1] + [suf]                      # エス片(export と同じ小文字系)
        q1 = p1[:-1] + [suf]                      # 漢字片(ラテン維持片は q0 と同一)
        lat = [a == b for a, b in zip(q0, q1)]    # 片ごとの「ラテン維持」フラグ
        if upper_all:
            q0 = [x.upper() for x in q0]
            q1 = [x.upper() if lat[i] else x for i, x in enumerate(q1)]
        elif title:
            q0 = [q0[0][:1].upper() + q0[0][1:]] + q0[1:]
            if lat[0]:                            # 先頭片がラテン維持なら漢字側も大文字化
                q1 = [q1[0][:1].upper() + q1[0][1:]] + q1[1:]
        n0 = '/'.join(q0); n1 = '/'.join(q1)
        n2 = ''.join(q0); n3 = ''.join(q1)
        if n2 in ALL_SURF: continue               # 別見出し -> その語の管轄
        if n2 in seen: continue
        seen.add(n2)
        cands.append((n2, n0, n1, n2, n3))
print(f'語尾変化候補 {len(cands)}')

# ── 現行描画を測る ─────────────────────────────────────────────
SEP = '◆'; B = 600
words = [c[0] for c in cands]
cur = {}
for i in range(0, len(words), B):
    ch = words[i:i+B]
    o = conv(' ' + (' ' + SEP + ' ').join(ch) + ' ')
    parts = o.split(SEP)
    if len(parts) != len(ch): parts = [conv(' ' + x + ' ') for x in ch]
    for x, s in zip(ch, parts): cur[x] = s.strip()
    if i % 3000 == 0: print(f'  走査 {i}/{len(words)}', flush=True)

# ★既に配信リストに完全一致キーがある語形には触らない。
#   実測(第77R): polo 族の手当て(poloj/polon/polojn とその大文字変種=马球)を
#   export のラテン維持で上書きし、実使用語彙で马球が消える退行を出した。
#   完全一致キーは「誰かが意図して置いたもの」なので、その管轄を尊重する。
EXISTING = {e[0] for e in GGm if isinstance(e[0], str)}

entries, skipped = [], []
stat = collections.Counter()
for w, n0, n1, n2, n3 in cands:
    if ' ' + w + ' ' in EXISTING:
        stat['既存キー(手当て等)を尊重'] += 1
        skipped.append((w, '既存の完全一致キーあり')); continue
    if kanji_surface(cur[w]) == n3:
        stat['既に一致'] += 1; continue
    val = build(n0, n1)
    if val is None or not verify(val, n2, n3):
        stat['構築不可'] += 1; skipped.append((w, f'f0={n0} f1={n1}')); continue
    entries.append([' ' + w + ' ', ' ' + val + ' ', None])
    stat['★是正対象'] += 1

print()
print('選定: ' + ' / '.join(f'{k}={v}' for k, v in stat.most_common()))
print(f'追加キー: {len(entries)} 件')
for k, v, _ in entries[:30]:
    w = k.strip()
    print(f"   {w:<24} 現在={kanji_surface(cur.get(w, ''))[:24]:<24} -> {kanji_surface(v)[:24]}")
if A.report:
    json.dump({'stat': dict(stat),
               'entries': [{'w': k.strip(), 'cur': kanji_surface(cur.get(k.strip(), '')),
                            'new': kanji_surface(v)} for k, v, _ in entries],
               'skipped': skipped},
              open(LP(A.report), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'report: {A.report}')

if DRY:
    print('\n(DRY-RUN: --apply で書込)'); sys.exit(0)

for lang in ('JA', 'ZH', 'KO'):
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_漢字.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    gg = [e for e in d[KEY]
          if not (len(e) > 2 and isinstance(e[2], str) and MARK in e[2])]
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
        ph = f' {MARK}{n:05d}{"" if lang == "JA" else lang}$ '
        if ph in used: raise SystemExit(f'placeholder collision: {ph}')
        rows.append([k, v, ph])
    d[KEY] = splice(gg, rows)
    atomic_file_copy(LP(path), LP(path + '.bak_preR76F'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 挿入 {len(rows)} / 既存値の差替 {replaced} '
          f'(旧投入 {removed} 件を除去 / 全域 {len(gg)} -> {len(d[KEY])})')
print('適用完了')
