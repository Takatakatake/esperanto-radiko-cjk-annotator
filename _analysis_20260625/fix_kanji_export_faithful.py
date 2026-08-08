# -*- coding: utf-8 -*-
"""第69R: マスターexportに忠実な漢字割り当てを、普通のエスペラント語について語スコープで与える。
   DRY既定 / --apply。

■ 何を直すか(ユーザー方針 2026-07-26)
  「固有名詞の対応もさることながら、既存のエスペラント単語がしっかり正しく注釈ルビを
    振れたり、学習者版のマスターに忠実な(偽分解に忠実な)漢字変換ができたりすることの
    方が、もっと重要」
  よって漢字残差1,101件のうち **固有名詞928件は保留**し、**普通の語173件**を潰す。

    debato    app=从打o(de+bat)  -> master=辩ᴰo    ★偽分解を尊重した割り当て
    demokratio app=民ᴰo          -> master=民ᴰᴱio
    filantropio app=儿人ᴬio(fil=儿) -> master=爱ᶠ人ᴬio
    aina      app=a女a(a+in)     -> master=aina    ★ラテン維持
    balta     app=b高a(b+alt)    -> master=balta   ★語頭食い込み

■ 権威と構築方法(発明ゼロ)
  マスターの `_漢字割当エクスポート_学習者版` は4列:
      f0=エス語根分解 / f1=漢字分解 / f2=表層 / f3=漢字表層
  例) debato : debat/o | 辩ᴰ/o | debato | 辩ᴰo
  f0とf1は**同じ片数**なので、片ごとに
      漢字片 == エス片  -> 素のラテン(=マスターがラテン維持を宣言)
      それ以外          -> アプリと同じ output_format で <ruby>漢字<rt>エス語根</rt></ruby>
  として連結するだけでマスターの意図がそのまま再現できる。
  ルビサイズ(rtのCSSクラス)はアプリ本体の output_format を呼んで計算するので、
  既存エントリと同じ体裁になる。

■ 安全設計
  1. 構築後、**ルビを剥いだ漢字表層が f3 と一致**し、**rt+素片が f2 と一致**することを
     検証する。一致しなければその語は捨てる(fail-closed)。
  2. 追加キーは空白パディングの完全一致キー。その語形にしか発火しない。
  3. 挿入位置は「自分を部分文字列として含む既存キーの直後、無ければ先頭」。
     包含判定は**約物パディング後の形**で行う(第68Rで3回やり直して確定した作法)。
  4. 大小変種は**実際に欠陥が出る変種にだけ**与える。
  5. 再実行できるように、前回の投入分($R69E)を外して測り、入れ直す。
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
ap.add_argument('--frozen', required=True, help='凍結マスターのディレクトリ')
ap.add_argument('--export-name', default='_漢字割当エクスポート_学習者版_20260723.tsv')
ap.add_argument('--include-proper', action='store_true',
                help='固有名詞クラスも対象にする(既定は普通の語のみ)')
ap.add_argument('--report', default='')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
FMT = 'HTML格式_Ruby文字_大小调整_汉字替换'
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
# ★監査(audit_kanji_vs_master_export.py)と完全に同じ正規化・絞り込みにする。
#   実測で踏んだ罠: f1/f3 にも circ() を掛けないと h-system が漏れ、
#   aĉeŭleo の是正値が 'ac^eu^leo' になる。また監査は「文字のみの単語」に絞っており、
#   -aĉ- や 'adori Dion' のような接辞見出し・句は対象外(これらを含めると偽の対象が2,000件出る)。
L_ = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
def ok_surface(s): return bool(re.fullmatch('[' + L_ + ']{1,40}', s))
EXP = collections.defaultdict(list)     # 表層 -> [(f0,f1,f2,f3), ...] 複数描画あり
for ln in raw.decode('utf-8', 'replace').splitlines():
    if ln.startswith('#'): continue
    f = ln.rstrip('\n').split('\t')
    if len(f) < 4: continue
    surf = circ(f[2].strip())
    if not ok_surface(surf): continue
    EXP[surf].append((circ(f[0].strip()), circ(f[1].strip()), surf, circ(f[3].strip())))
print(f'export 実在語(監査と同じ絞り込み): {len(EXP)}')

def is_proper(w, f0):
    if w[:1].isupper(): return True
    return any(p[:1].isupper() for p in f0.split('/') if p)

# ── 触ってはいけない語根族(実測で退行を出した/裁定済み) ──────────────────
#   語幹で判定する。大小変種も同時に除外される。
EXCLUDE_STEMS = {
    # ユーザー裁定: esperanto は望在o のまま据え置く(esper/ant と分解する意図的設定であり
    # プロジェクトの名称でもある)。マスターexportはラテン維持だが、裁定が優先する。
    'esperant': 'ユーザー裁定により 望在o を据置(マスターとの既知の差分)',
    # マスターには5文字語根 polo=马球(ポロ競技)が別に存在し、表層 polo が
    # pol/o(ポーランド人)と衝突する。ラテン固定すると实使用語彙で马球が消える。
    'pol': '表層衝突(pol/o ラテン維持 vs 語根 polo=马球)。マスター照会中',
    # ★マスター内部で不一致: export は et -> 乙、注入版は et -> 小。
    #   export に従うと注入版軸に退行が出る。どちらが正かはマスターの管轄。
    'et': 'export(乙)と注入版(小)が不一致。マスター照会に回す',
}
def excluded(w):
    lw = w.lower()
    for st in EXCLUDE_STEMS:
        if lw == st or lw.startswith(st) and len(lw) - len(st) <= 4:
            return st
    return None

# ── 手当て(表層衝突の解消。マスターの語根データからのみ組む) ────────────────
#   (語形, 語根, 漢字, 語尾) — 漢字は必ずマスターに実在する割り当てを使う
MANUAL_OVERRIDE = [
    # 表層 et は2つの形態素が衝突する: et/(化学の接頭辞 et-=エチル)=乙 と -et-(指小辞)=小。
    # export は 乙、注入版は 小 を返し、export に従うと注入版軸に退行が出る。
    # 実文で単独の et はほぼ現れず、配信実績のある 小 を維持してマスターに照会する。
    ('et', 'et', '小', ''),
    # 表層 polo も衝突: pol/o(ポーランド人; export はラテン維持) と
    # 5文字語根 polo=马球(ポロ競技, polo/c^emiz/o=ポロシャツ)。
    # gen-g で pol=插ᴾ(数学の補間)が入り、現状 polo -> 插ᴾo という**どの読みでも誤り**の
    # 出力になっている。マスターに実在する 马球 に戻す(gen-g以前の配信挙動)。
    ('polo', 'polo', '马球', ''), ('Polo', 'Polo', '马球', ''),
    ('poloj', 'polo', '马球', 'j'), ('polon', 'polo', '马球', 'n'),
    ('polojn', 'polo', '马球', 'jn'),
    ('Poloj', 'Polo', '马球', 'j'), ('Polon', 'Polo', '马球', 'n'),
    ('Polojn', 'Polo', '马球', 'jn'),
]

# ── アプリの現行出力 ────────────────────────────────────────────
app_dir = os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA')
sys.path.insert(0, app_dir)
import esp_text_replacement_module as M
helper = load_app_replacement_helper(app_dir)
with open(LP(os.path.join(app_dir, 'app_data', 'char_widths.json')), encoding='utf-8') as fp:
    CW = json.load(fp)
dJA = json.load(open(LP(os.path.join(app_dir, 'app_data', '置換リスト_漢字.json')), encoding='utf-8'))
GL = dJA['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = dJA['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
# 前回の投入分($R69E)を外した状態で測る(再実行できるように)
GGm = [e for e in dJA[KEY] if not (len(e) > 2 and isinstance(e[2], str) and '$R69E' in e[2])]
ps = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_skip.txt'))
pl = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_localcapture.txt'))
def conv(t):
    return M.orchestrate_comprehensive_esperanto_text_replacement(
        t, ps, GL, pl, GGm, G2, FMT)
def kanji_surface(html):
    """出力からマスターの f3 に相当する漢字表層を取り出す。"""
    s = re.sub(r'<rt[^>]*>.*?</rt>', '', html, flags=re.S)
    return TAG.sub('', s).strip()

def build(f0, f1):
    """マスターの片対応から、アプリと同じ体裁のエントリ値を作る。"""
    e_ps = f0.split('/'); k_ps = f1.split('/')
    if len(e_ps) != len(k_ps): return None
    buf = []
    for e, k in zip(e_ps, k_ps):
        if not e:
            if k: return None
            continue
        if k == e: buf.append(e)                      # ラテン維持
        else: buf.append(helper.output_format(e, k, FMT, CW))
    return ''.join(buf)

def verify(val, f2, f3):
    """漢字表層とエス表層の両方が master と一致するか。"""
    if kanji_surface(val) != f3: return False
    esp = []
    pos = 0
    for m in RUBY.finditer(val):
        if m.start() > pos: esp.append(TAG.sub('', val[pos:m.start()]))
        esp.append(BR.sub('', TAG.sub('', m.group(2))))
        pos = m.end()
    if pos < len(val): esp.append(TAG.sub('', val[pos:]))
    return ''.join(esp) == f2

# ── 対象の選定 ──────────────────────────────────────────────────
targets = sorted(EXP)
SEP = '◆'; B = 600
cur = {}
for i in range(0, len(targets), B):
    ch = targets[i:i+B]
    o = conv(' ' + (' ' + SEP + ' ').join(ch) + ' ')
    parts = o.split(SEP)
    if len(parts) != len(ch): parts = [conv(' ' + w + ' ') for w in ch]
    for w, s in zip(ch, parts): cur[w] = s.strip()
    if i % 15000 == 0: print(f'  現行出力の走査 {i}/{len(targets)}', flush=True)

entries, skipped = [], []
stat = collections.Counter()
_added = set(); _val_of = {}
for w in targets:
    senses = EXP[w]
    ad = kanji_surface(cur[w])
    if ad in {s[3] for s in senses}:
        stat['既に一致'] += 1; continue      # 複数描画のいずれかに一致すれば可(監査と同基準)
    f0, f1, f2, f3 = senses[0]               # 一次描画をマスターの意図とする
    ex = excluded(w)
    if ex:
        stat['除外(裁定/衝突)'] += 1; skipped.append((w, 'EXCLUDE:' + EXCLUDE_STEMS[ex])); continue
    if not A.include_proper and is_proper(w, f0):
        stat['固有名詞(保留)'] += 1; continue
    val = build(f0, f1)
    if val is None or not verify(val, f2, f3):
        stat['構築不可'] += 1; skipped.append((w, f'構築/検証に失敗 f0={f0} f1={f1}')); continue
    entries.append([' ' + w + ' ', ' ' + val + ' ', None])
    _added.add(w); _val_of[w] = (f0, f1, f2, f3)
    stat['★是正対象'] += 1

print()
print('選定: ' + ' / '.join(f'{k}={v}' for k, v in stat.most_common()))

# ── 大小変種の補完(実際に欠陥が出る変種にだけ) ─────────────────────
var_cand = []
for w in list(_added):
    for v in (w[0].upper() + w[1:], w.upper()):
        if v == w or v in _added: continue
        var_cand.append((v, w))
seen = set()
var_cand = [(v, w) for v, w in var_cand if not (v in seen or seen.add(v))]
if var_cand:
    vs = [v for v, _ in var_cand]
    for i in range(0, len(vs), B):
        ch = vs[i:i+B]
        o = conv(' ' + (' ' + SEP + ' ').join(ch) + ' ')
        parts = o.split(SEP)
        if len(parts) != len(ch): parts = [conv(' ' + x + ' ') for x in ch]
        for x, s in zip(ch, parts): cur[x] = s.strip()
    nv = 0
    for v, w in var_cand:
        # 2026-08-05 第110R: 変種自身がマスターexportの表層なら各自の管轄(大小で裁定が
        # 割れるペア357件)。小文字値の機械的な大文字化を与えると Rodo(ロードス島=ラテン)に
        # rodo(泊o)の値を付ける退行になる。
        if v in EXP: continue
        f0, f1, f2, f3 = _val_of[w]
        up = (v == w.upper())
        cf0 = f0.upper() if up else (f0[0].upper() + f0[1:])
        cf1 = f1.upper() if up else f1
        cf2 = f2.upper() if up else (f2[0].upper() + f2[1:])
        cf3 = f3.upper() if up else f3
        if not up:
            # 漢字側は大小の概念が無いので f1/f3 はそのまま。先頭片がラテンなら大文字化される
            k0 = f1.split('/')[0]; e0 = f0.split('/')[0]
            if k0 == e0:
                cf1 = '/'.join([k0[0].upper() + k0[1:]] + f1.split('/')[1:])
                cf3 = cf3[0].upper() + cf3[1:] if cf3 and cf3[0].isascii() else cf3
        if kanji_surface(cur[v]) == cf3: continue        # その変種は既に正しい
        val = build(cf0, cf1)
        if val is None or not verify(val, cf2, cf3): continue
        entries.append([' ' + v + ' ', ' ' + val + ' ', None]); _added.add(v); nv += 1
    print(f'大小変種の補完: {nv} 件(候補 {len(var_cand)})')

# ── 手当ての適用(表層衝突) ────────────────────────────────────────
mo_n = 0
for w, root, kan, end in MANUAL_OVERRIDE:
    if w in _added: continue
    val = helper.output_format(root, kan, FMT, CW) + end
    if kanji_surface(val) != kan + end:
        skipped.append((w, '手当ての検証に失敗')); continue
    entries.append([' ' + w + ' ', ' ' + val + ' ', None]); _added.add(w); mo_n += 1
if mo_n: print(f'表層衝突の手当て: {mo_n} 件')

print(f'\n追加キー: {len(entries)} 件')
for k, v, _ in entries[:30]:
    w = k.strip()
    print(f"   {w:<22} 現在={kanji_surface(cur.get(w, ''))[:22]:<22} -> {kanji_surface(v)[:22]}")
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
          if not (len(e) > 2 and isinstance(e[2], str) and '$R69E' in e[2])]
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
        ph = f' $R69E{n:05d}{"" if lang == "JA" else lang}$ '
        if ph in used: raise SystemExit(f'placeholder collision: {ph}')
        rows.append([k, v, ph])
    d[KEY] = splice(gg, rows)
    atomic_file_copy(LP(path), LP(path + '.bak_preR69E'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 挿入 {len(rows)} / 既存値の差替 {replaced} '
          f'(旧投入 {removed} 件を除去 / 全域 {len(gg)} -> {len(d[KEY])})')
print('適用完了')
