# -*- coding: utf-8 -*-
"""第85R: **ハイフン入り見出し**の漢字をマスターexportに忠実化する。DRY既定 / --apply。

■ なぜ抜けていたか
  fix_kanji_export_faithful.py / …_endings.py は監査と同じ絞り込み
      ok_surface(s) = [A-Za-zĉĝĥĵŝŭ]{1,40} に完全一致
  を使うため、**ハイフンを含む表層を構造的に対象外**にしていた。
  実測: マスターexportのハイフン入り見出しは 353 語。
      一致 190 / 不一致 163 (固有名詞 143 / 普通の語 20)

■ この回で直す 15 語(いずれも普通の語。**注入版と export が一致**することを確認済み)
      oto-rino-laringologo  待o-rino-laringo诱ᴸo   -> 耳ᴼᵀo-鼻ᴿo-喉ᴸo学家o
      mal-vorto             m向-词o                -> 反-词o
      glu-glu-glu           g租-g租-胶             -> 胶-胶-胶
      2-butenalo            2-buten向o             -> 2-丁enalo
      2-propanolo           2-propan比o            -> 2-丙anolo
      2-propenilo           2-propen具o            -> 2-丙en基o
      1,2-etandiolo         1,2-etan神比o          -> 1,2-乙an二olo
      1,2-propandiolo       1,2-丙an二ᴰᴵolo        -> 1,2-丙an二olo
      1,2,3-propantriolo    1,2,3-propantriolo     -> 1,2,3-propan三olo
      ter-butanolo          地-丁anolo             -> ter-丁anolo   ★偽の「地」が消える
      f-ino                 f-ino                  -> f-女o
      gik-gak               gik-gak                -> gik-鸣ᴳ
      kala-azaro            草ᴷᴬ-草ᴬᶻᴬo            -> kala-azaro    ★マスターはラテン維持
      nor-adrenalino        n金-adrenalino         -> nor-adrenalino ★同上(偽の「金」が消える)
      nor-epinefrino        n金-epinefrino         -> nor-epinefrino ★同上

■ ★保留する5語(マスター照会に回す。現行のラテン素通しの方が害が小さい)
      d-ro / s-ro / n-ro   マスターは `ro`(=文字Rの名称ロー)に木を当てるため d-木ᴿ になる。
                           既に `NRO`->`N-木ᴿ` を「どの読みでも誤り」としてユーザー裁定待ちに
                           載せている同型。略語の分解自体が偽分解であり、適用すると
                           現在の無害なラテン素通しが誤読に変わる。
      k-do                 同上(`do`=文字Dの名称/接続詞「だから」に 故)。kamarado の略。
      riĉ-raĉ              `riĉ`=富。布が裂ける擬音語に「富」が付く。現行はラテン素通し。

■ 固有名詞143語は保留(ユーザー裁定待ちの固有名詞クラスと同じ扱い)

■ 構築方法(発明ゼロ・第69R/第77Rと同一)
  export の f0=エス語根分解 / f1=漢字分解 は同じ片数なので、片ごとに
      漢字片 == エス片 -> 素のラテン / それ以外 -> output_format で <ruby>漢字<rt>エス</rt></ruby>
  大小変種と語尾変化形も、**片の綴りを切り出して同じ大小を移す**だけで作る
  (ハイフン区切りごとの大文字化 Oto-Rino-… にも対応する)。
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
MARK = '$R85K'
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
BR = re.compile(r'<br\s*/?>')

HOLD = {
    'd-ro': 'ro=文字Rの名称に木。NRO->N-木ᴿ と同型でユーザー裁定待ち',
    's-ro': 'ro=文字Rの名称に木。同上',
    'n-ro': 'ro=文字Rの名称に木。同上',
    'k-do': 'do=文字Dの名称/接続詞に故。kamaradoの略。同上',
    'riĉ-raĉ': 'riĉ=富。布が裂ける擬音に富。現行ラテンの方が害が小さい',
}

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
HYPH = re.compile('[' + L_ + r'0-9,\.]+(?:-[' + L_ + r'0-9,\.]+)+')
EXP = collections.defaultdict(list)
ALL_SURF = set()
for ln in raw.decode('utf-8', 'replace').splitlines():
    if ln.startswith('#'): continue
    f = ln.rstrip('\n').split('\t')
    if len(f) < 4: continue
    surf = circ(f[2].strip())
    ALL_SURF.add(surf)
    if not HYPH.fullmatch(surf): continue
    EXP[surf].append((circ(f[0].strip()), circ(f[1].strip()), surf, circ(f[3].strip())))
print(f'ハイフン入り見出し {len(EXP)} / export 全見出し {len(ALL_SURF)}')

def is_proper(w, f0):
    if w[:1].isupper(): return True
    return any(p[:1].isupper() for p in f0.split('/') if p)

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
EXISTING = {e[0] for e in GGm if isinstance(e[0], str)}
EXIST_MARK = {}
for e in GGm:
    if isinstance(e[0], str) and e[0] not in EXIST_MARK:
        EXIST_MARK[e[0]] = e[2] if len(e) > 2 else None
# 生成系(gen_replacement)が置いた行のマーカー。手当て($R69E 等)や無印とは区別する。
GEN_MARK = re.compile(r'^\s*\$\d+(up|cap|pc)?\$\s*$')
ps = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_skip.txt'))
pl = M.import_placeholders(os.path.join(app_dir, 'app_data', 'placeholders_localcapture.txt'))
def conv(t):
    return M.orchestrate_comprehensive_esperanto_text_replacement(t, ps, GL, pl, GGm, G2, FMT)
def ksurf(h):
    return TAG.sub('', re.sub(r'<rt[^>]*>.*?</rt>', '', h, flags=re.S)).strip()

def build(f0, f1):
    e_ps = f0.split('/'); k_ps = f1.split('/')
    if len(e_ps) != len(k_ps): return None
    buf = []
    for e, k in zip(e_ps, k_ps):
        if not e:
            if k: return None
            continue
        buf.append(e if k == e else helper.output_format(e, k, FMT, CW))
    return ''.join(buf)

def verify(val, f2, f3):
    if ksurf(val) != f3: return False
    esp = []; pos = 0
    for m in RUBY.finditer(val):
        if m.start() > pos: esp.append(TAG.sub('', val[pos:m.start()]))
        esp.append(BR.sub('', TAG.sub('', m.group(2))))
        pos = m.end()
    if pos < len(val): esp.append(TAG.sub('', val[pos:]))
    return ''.join(esp) == f2

def recase_piece(e, k, seg):
    """片1つを seg の大小に合わせ直す。

    ★実測した罠(第85R): 漢字片には `a-词` `ter-丁` `o-鼻ᴿ` のように**ラテンが混じる**ものがある。
      k をそのまま使うと A-vorto が a-词o に、Oto-… が oto-… に落ちる(大小の退行)。
      そこで e と k の**共通接頭辞・共通接尾辞**(=ラテンのまま残っている部分)にだけ
      seg の大小を移し、中央に別のラテンが残る場合は不明として捨てる(fail-closed)。
    """
    if k == e: return seg
    i = 0
    while i < min(len(e), len(k)) and e[i] == k[i]: i += 1
    j = 0
    while j < min(len(e), len(k)) - i and e[len(e) - 1 - j] == k[len(k) - 1 - j]: j += 1
    mid = k[i:len(k) - j]
    if any(ch.isascii() and ch.isalpha() for ch in mid): return None
    return seg[:i] + mid + (seg[len(e) - j:] if j else '')

def recase(p0, p1, cased_surface):
    """片列を cased_surface の大小に合わせ直す。"""
    q0 = []; q1 = []; pos = 0
    for e, k in zip(p0, p1):
        seg = cased_surface[pos:pos + len(e)]; pos += len(e)
        if seg.lower() != e.lower(): return None
        ck = recase_piece(e, k, seg)
        if ck is None: return None
        q0.append(seg); q1.append(ck)
    if pos != len(cased_surface): return None
    return q0, q1

def variants(w):
    """小文字形 w から、綴りが同じで大小だけ違う変種を作る。"""
    out = [w, w[:1].upper() + w[1:], w.upper(),
           '-'.join(p[:1].upper() + p[1:] for p in w.split('-'))]
    seen = set(); res = []
    for v in out:
        if v in seen: continue
        seen.add(v); res.append(v)
    return res

PARADIGM = {'o': ['oj', 'on', 'ojn'],
            'a': ['aj', 'an', 'ajn'],
            'e': ['en'],
            'i': ['as', 'is', 'os', 'us', 'u']}

# ── 候補づくり ────────────────────────────────────────────────
cands = []   # (表層, p0, p1)
held = []
for w in sorted(EXP):
    f0, f1, f2, f3 = EXP[w][0]
    if w in HOLD: held.append((w, HOLD[w])); continue
    if is_proper(w, f0): continue
    if f0.replace('/', '') != f2 or f1.replace('/', '') != f3: continue
    p0 = f0.split('/'); p1 = f1.split('/')
    if len(p0) != len(p1): continue
    base_forms = [(w, p0, p1)]
    end = p0[-1]
    if end in PARADIGM and p1[-1] == end:
        for suf in PARADIGM[end]:
            n2 = ''.join(p0[:-1]) + suf
            if n2 in ALL_SURF: continue          # 別見出し -> その語の管轄
            base_forms.append((n2, p0[:-1] + [suf], p1[:-1] + [suf]))
    for surf, q0, q1 in base_forms:
        for v in variants(surf):
            r = recase(q0, q1, v)
            if r is None: continue
            cands.append((v, r[0], r[1], len(EXP[w])))
seen = set(); cands = [c for c in cands if not (c[0] in seen or seen.add(c[0]))]
print(f'候補語形 {len(cands)} / 保留 {len(held)}')
for w, why in held: print(f'   保留 {w:<10} {why}')

# ── 現行描画 ─────────────────────────────────────────────────
SEP = '◆'; B = 300
ws = [c[0] for c in cands]
cur = {}
for i in range(0, len(ws), B):
    ch = ws[i:i+B]
    o = conv(' ' + (' ' + SEP + ' ').join(ch) + ' ')
    parts = o.split(SEP)
    if len(parts) != len(ch): parts = [conv(' ' + x + ' ') for x in ch]
    for x, s in zip(ch, parts): cur[x] = s.strip()

entries, skipped = [], []
stat = collections.Counter()
for w, q0, q1, nsense in cands:
    n2 = ''.join(q0); n3 = ''.join(q1)
    if ksurf(cur[w]) == n3:
        stat['既に一致'] += 1; continue
    if ' ' + w + ' ' in EXISTING:
        # ★第77Rの教訓「既存の完全一致キーは誰かが意図して置いたもの」を、出所で切り分ける。
        #   polo=马球 を潰した事故は**手当ての行**を上書きしたことが原因だった。
        #   ここで上書きするのは**生成系が置いた行**に限り、しかも
        #   マスターが単一の描画しか持たない語に限る(複数描画は別の読みを潰す危険)。
        #   放置すると同じ語の単数形と複数形で描画が食い違う(f-ino/f-女oj など)。
        mk = EXIST_MARK.get(' ' + w + ' ')
        if not (isinstance(mk, str) and GEN_MARK.match(mk)) or nsense != 1:
            stat['既存キー(手当て等)を尊重'] += 1
            skipped.append((w, f'既存キーを尊重 marker={mk!r} 描画数={nsense}')); continue
        stat['既存の生成行を上書き'] += 1
    val = build('/'.join(q0), '/'.join(q1))
    if val is None or not verify(val, n2, n3):
        stat['構築不可'] += 1; skipped.append((w, f'f0={"/".join(q0)} f1={"/".join(q1)}')); continue
    entries.append([' ' + w + ' ', ' ' + val + ' ', None])
    stat['★是正対象'] += 1

print('\n選定: ' + ' / '.join(f'{k}={v}' for k, v in stat.most_common()))
print(f'追加キー: {len(entries)}')
for k, v, _ in entries:
    w = k.strip()
    print(f"   {w:<28} 現在={ksurf(cur.get(w, '')):<26} -> {ksurf(v)}")
if skipped:
    print(f'\nskip {len(skipped)}')
    for s in skipped[:10]: print('   ', s)
if A.report:
    json.dump({'stat': dict(stat), 'held': held, 'skipped': skipped,
               'entries': [{'w': k.strip(), 'cur': ksurf(cur.get(k.strip(), '')),
                            'new': ksurf(v)} for k, v, _ in entries]},
              open(LP(A.report), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

if DRY:
    print('\n(DRY-RUN: --apply で書込)'); sys.exit(0)

for lang in ('JA', 'ZH', 'KO'):
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_漢字.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    gg = [e for e in d[KEY] if not (len(e) > 2 and isinstance(e[2], str) and MARK in e[2])]
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
    atomic_file_copy(LP(path), LP(path + '.bak_preR85K'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 挿入 {len(rows)} / 既存値の差替 {replaced} '
          f'(旧投入 {removed} 件を除去 / 全域 {len(gg)} -> {len(d[KEY])})')
print('適用完了')
