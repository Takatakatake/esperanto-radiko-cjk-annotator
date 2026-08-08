# -*- coding: utf-8 -*-
"""第116R: 第65R台帳 closable_survived(328) の「マスターはラテン維持 / appが漢字化」を閉じる。
   DRY既定 / --apply / --frozen 必須。

■ 背景
  _latin_maintained_adjudication_20260725.json(第65R, 10エージェント分類+敵対的反証)で
  「完全一致の表層キーなら安全に閉じられる」と裁定された328語が未実装のまま残っていた
  (第68Rのfix_kanji_export_latin_lock.pyに「ユーザー裁定により保留中」と明記)。
  第116R時点の再測定で: 48語は第100-110Rの副産物で治癒 / 1語(majorano)はマスターが漢字化に
  転じたため対象外 / 残り279語が現に壊れている(例: Usono→U声o, Sara→S群a, Filipinoj→Filip女oj)。

■ 壊れ方の2型(第116R実測)
  A型(110語): 全語キー('Akadujo')が既に存在し最初に発火するが、値がマスターに反して
      漢字合成('Akad器o')。生成器がマスターの語スコープのラテン維持行を消費していない。
      → 是正 = 既存キーの**値だけ**を恒等ラテンに置換。語幹キー('Akaduj')も漢字値なら同様。
        発火位置は一切変わらないので巻き添えゼロ。語尾変化形は既存キーが包含するため自動治癒。
  B型(8語+新規154語): 恒等キーが無い/後方にあり、手前の語根キーが先に食う
      ('sono'が'Usono'を、'ara'が'Sara'を)。
      → 是正 = 空白パディングの完全一致キー(' Usono '→' Usono ')を「自分を含む既存キーの
        直後(無ければ先頭)」に挿入(第68R確定の作法)。語尾変化形は**現に壊れている形だけ**
        ガード付きで同時に挿入(R76-77「見出しだけ直して語尾変化形を落とす」の再発防止)。

■ 裁定ルール(発明ゼロ)
  1. 値は常に「表層そのもの」(マスターexportの行の値=表層と一致することを事前検証, fail-closed)。
  2. EXCLUDE: esperant*(ユーザー裁定=望在o据置)。pol/et は**完全一致の衝突表層のみ**除外
     (pol{a,o,...}=马球衝突 / et,eta,eto=乙/小不一致)。Polinezio や Etiopujo のような
     「たまたま同じ2字で始まる別語」は完全一致キーなので衝突し得ず、除外しない。
  3. LEAVE: 小文字形がマスターexportに漢字描画で実在する語形は触らない(Blanka則/第69R)。
  4. 生成する語尾変化形は基本形の正規延長のみ(-o→on,oj,ojn / -a→an,aj,ajn / -e→en /
     語尾がoj→ojn)。exportに漢字描画で実在する同綴りはスキップ(裸の同綴りは触らない)。
  5. 対象は測定で実際に壊れている語形だけ(適用後に全対象を再描画してfail-closed検証)。

■ 安全設計
  1. 冪等: 挿入分は $R116L マーカーで外して測り直せる。値置換は目標値=恒等なので自然に冪等。
  2. 値置換の原状は out/r116_valuefix_ledger.json に保存(可逆)。適用前に .bak_preR116。
  3. 3言語に同一操作(対象キーの位置・キー・値がJA/ZH/KOで同一であることを事前検証, fail-closed)。
  4. 適用後の検証は呼び出し側のゲート(export監査で治癒数=計画数・新規不一致0 /
     injection監査不変 / 3言語構造一致 / ハイフンゲート不変)。
"""
import json, os, re, sys, argparse
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AN = os.path.join(ROOT, '_analysis_20260625')
sys.path.insert(0, AN)
from atomic_json import atomic_file_copy, atomic_json_dump

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--frozen', required=True, help='凍結マスターのディレクトリ')
ap.add_argument('--export-name', default='_漢字割当エクスポート_学習者版_20260723.tsv')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
TAGID = '$R116L'

X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
L = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
FULL_LATIN = re.compile('^[' + L + r"\-'’ ]+$")
CJK = re.compile(r'[⺀-鿿가-힯぀-ヿᄀ-ᇿ㄰-㆏'
                 r'ꥠ-꥿ힰ-퟿＀-￯]')
RT = re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>'); TAG = re.compile(r'<[^>]+>')
def disp(seg): return TAG.sub('', RT.sub('', seg)).strip()

# ── EXCLUDE(過去のユーザー裁定・照会中。完全一致表層で判定) ─────────────────
# 第117R裁定: 国名 -ujo 型107語は器(_ujo_country_adjudication_20260808.json)。
# 本スクリプトを再実行しても裁定を巻き戻さないための EXCLUDE。
_UJO_ADJ = set()
_ujo_p = os.path.join(AN, '_ujo_country_adjudication_20260808.json')
if os.path.exists(_ujo_p):
    _UJO_ADJ = set(json.load(open(_ujo_p, encoding='utf-8'))['words'])

def excluded(w):
    lw = w.lower()
    if w in _UJO_ADJ or (w[:-1] in _UJO_ADJ) or (w[:-2] in _UJO_ADJ):
        return 'ユーザー裁定(第117R): 国名-ujoは器(Afgan器o)。ラテン化しない'
    if lw.startswith('esperant'):
        return 'ユーザー裁定: esperanto=望在o 据置'
    if re.fullmatch(r'pol[oa]j?n?', lw):
        return 'pol/o vs polo=马球 表層衝突(マスター照会中)'
    if lw in ('et', 'eta', 'eto', 'etaj', 'eton', 'etan'):
        return 'et: export(乙)と注入版(小)の不一致(マスター照会中)'
    return ''

# ── マスターexport ───────────────────────────────────────────────────────
exp = {}
for ln in open(LP(os.path.join(A.frozen, A.export_name)), encoding='utf-8'):
    if ln.startswith('#'): continue
    ps = ln.rstrip('\n').split('\t')
    if len(ps) < 4: continue
    exp.setdefault(circ(ps[2].strip()), []).append(circ(ps[3].strip()))
print(f'マスターexport 表層: {len(exp)}')

led = json.load(open(os.path.join(AN, '_latin_maintained_adjudication_20260725.json'),
                     encoding='utf-8'))
surv = [e['w'] for e in led['closable_survived']]

# ── アプリ3言語の読込と同一性検証 ──────────────────────────────────────────
sys.path.insert(0, os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA'))
import esp_text_replacement_module as M
DATA = {}
for lang in ('JA', 'ZH', 'KO'):
    p = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_漢字.json')
    DATA[lang] = (p, json.load(open(LP(p), encoding='utf-8')))
GGj = DATA['JA'][1][KEY]

# 冪等: 前回投入分($R116L)を外した素の状態で「本来どう出るか」を測る
def strip_mine(gg):
    return [e for e in gg if not (len(e) > 2 and isinstance(e[2], str) and TAGID in e[2])]
GGm = strip_mine(GGj)
appj = os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA')
d0 = DATA['JA'][1]
GL = d0['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = d0['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
ps_ = M.import_placeholders(os.path.join(appj, 'app_data', 'placeholders_skip.txt'))
pl_ = M.import_placeholders(os.path.join(appj, 'app_data', 'placeholders_localcapture.txt'))
def render_many(words, gg):
    out = {}
    B = 400; SEP = '◆'
    for i in range(0, len(words), B):
        ch = words[i:i+B]
        o = M.orchestrate_comprehensive_esperanto_text_replacement(
            ' ' + (' ' + SEP + ' ').join(ch) + ' ', ps_, GL, pl_, gg, G2, '汉字替换_大小调整')
        parts = o.split(SEP)
        if len(parts) != len(ch):
            for w in ch:
                o1 = M.orchestrate_comprehensive_esperanto_text_replacement(
                    ' ' + w + ' ', ps_, GL, pl_, gg, G2, '汉字替换_大小调整')
                out[w] = disp(o1)
        else:
            for w, seg in zip(ch, parts): out[w] = disp(seg)
    return out

# ── 対象の確定 ───────────────────────────────────────────────────────────
cand, skipped = [], []
for w in surv:
    r = excluded(w)
    if r: skipped.append((w, r)); continue
    ms = exp.get(w, [])
    if not any(FULL_LATIN.fullmatch(m or '') for m in ms):
        skipped.append((w, f'マスターが全ラテンでない: {ms[:2]}')); continue
    lw = w.lower()
    if lw != w and lw in exp and any(not FULL_LATIN.fullmatch(m or '') for m in exp[lw]):
        skipped.append((w, f'LEAVE(Blanka則): 小文字形が漢字描画 {exp[lw][:1]}')); continue
    cand.append(w)
cur = render_many(cand, GGm)
targets = [w for w in cand if cur[w] != w]
print(f'台帳328 → 除外/据置 {len(skipped)} / 既に正しい {len(cand)-len(targets)} / 是正対象 {len(targets)}')
for w, r in skipped:
    if 'ラテンでない' not in r: print(f'  据置 {w}: {r}')

# ── 語尾変化形の生成(正規延長のみ) ───────────────────────────────────────
def gen_forms(w):
    fs = []
    if w.endswith(('oj', 'aj')): fs = [w + 'n']
    elif w.endswith('o') or w.endswith('a'): fs = [w + 'n', w + 'j', w + 'jn']
    elif w.endswith('e'): fs = [w + 'n']
    out = []
    for f in fs:
        if f in exp and any(not FULL_LATIN.fullmatch(m or '') for m in exp[f]):
            continue  # exportに漢字描画の同綴りが実在 → 裸の同綴りは触らない
        fl = f.lower()
        if fl != f and fl in exp and any(not FULL_LATIN.fullmatch(m or '') for m in exp[fl]):
            continue  # Blanka則
        out.append(f)
    return out

# ── A型/B型の振り分け ────────────────────────────────────────────────────
bykey = {}
for i, e in enumerate(GGm):
    if isinstance(e[0], str): bykey.setdefault(e[0].strip(), []).append(i)

# 値置換は「stripped==w の全語キー」のみ。語幹キー(' Amon' 等の前方開放キー)は
# 無関係語(Amoniako型)を巻き添えにし得るので触らない(壊れて残る変化形は挿入側が拾う)。
# さらに: w を部分文字列に含む**別語**が export に漢字描画で実在するなら値置換もしない
# (全語キーは w を含む長い語の内部でも発火するため)。
def contained_in_kanji_word(w):
    for s, ms in exp.items():
        if w in s and s != w:
            if any(not FULL_LATIN.fullmatch(m or '') for m in ms):
                return s
    return ''

valuefix = []   # (GGm内のindex, キー, 旧値)
inserts = []    # 挿入する表層(基本形+壊れている変化形)
for w in targets:
    idxs = [i for i in bykey.get(w, []) if CJK.search(GGm[i][1])]
    host = contained_in_kanji_word(w) if idxs else ''
    if idxs and not host:
        for i in sorted(set(idxs)):
            valuefix.append((i, GGm[i][0], GGm[i][1]))
    else:
        if host:
            print(f'  値置換回避(内包語が漢字描画: {host}) → 挿入で対応: {w}')
        inserts.append(w)

# 変化形: 全対象語について「現に壊れている形」だけ挿入対象に足す
#   (A型は値置換で自動治癒するはずなので、置換後にまだ壊れる形だけを拾うため
#    まず値置換をGGmのコピーに先行適用してから測る)
GGsim = [list(e) for e in GGm]
for i, k, _old in valuefix:
    GGsim[i][1] = k
forms_all = []
form_of = {}
for w in targets:
    for f in gen_forms(w):
        forms_all.append(f); form_of[f] = w
base_ins = set(inserts)
sim1 = render_many(sorted(set(list(base_ins) + forms_all)), GGsim)
still = [f for f in forms_all if sim1[f] != f]
ins_base_broken = [w for w in inserts if sim1[w] != w]
# A型なのに値置換だけでは治らない基本形(手前に食うキーがある)も挿入へ
typA_words = {w for w in targets if w not in base_ins}
extraA = [w for w in typA_words if w in sim1 and sim1[w] != w]
all_inserts = sorted(set(ins_base_broken + still + extraA))
print(f'値置換: {len(valuefix)}キー(A型 {len(typA_words)}語) / '
      f'挿入: 基本形{len(ins_base_broken)} + 変化形{len(still)} + A型残り{len(extraA)} '
      f'= {len(all_inserts)}表層')

# ── 挿入位置(第68R確定のsplice) ─────────────────────────────────────────
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

def splice(gg, new_rows):
    cand_ = [(i, padkey(e[0])) for i, e in enumerate(gg)
             if isinstance(e[0], str) and (' ' in e[0].strip() or _PAD.search(e[0]))]
    groups = {}
    for r in new_rows:
        k = padkey(r[0]); p = 0
        for i, mk in cand_:
            if len(mk) > len(k) and k in mk: p = max(p, i + 1)
        groups.setdefault(p, []).append(r)
    out = list(gg)
    for p in sorted(groups, reverse=True):
        out[p:p] = groups[p]
    return out

# ── 事前検証: 3言語で対象キーの(キー,値)が同一(第111R同一性の再確認) ─────────
GGz = strip_mine(DATA['ZH'][1][KEY]); GGk = strip_mine(DATA['KO'][1][KEY])
if not (len(GGm) == len(GGz) == len(GGk)):
    raise SystemExit(f'3言語のGG行数が不一致: JA={len(GGm)} ZH={len(GGz)} KO={len(GGk)}')
for i, _k, _old in valuefix:
    for gg, nm in ((GGz, 'ZH'), (GGk, 'KO')):
        if gg[i][0] != GGm[i][0] or gg[i][1] != GGm[i][1]:
            raise SystemExit(f'{nm} GG[{i}] がJAと不一致: {gg[i][:2]!r} vs {GGm[i][:2]!r}')
print('3言語同一性(対象キーの位置・キー・値): OK')

# ── 最終シミュレーション(JA)で全対象が治ることを検証 ─────────────────────
rows_sim = [[' ' + w + ' ', ' ' + w + ' ', f' $SIM{n:05d}$ ']
            for n, w in enumerate(all_inserts)]
GGfin = splice(GGsim, rows_sim)
allw = sorted(set(targets + forms_all))
fin = render_many(allw, GGfin)
bad = [(w, fin[w]) for w in targets if fin[w] != w]
badf = [(f, fin[f]) for f in forms_all if fin[f] != f and f in [r[0].strip() for r in rows_sim]]
if bad or badf:
    for w, v in (bad + badf)[:20]: print(f'  ★未治癒: {w} → {v}')
    raise SystemExit(f'fail-closed: シミュレーションで未治癒 {len(bad)}+{len(badf)}')
print(f'シミュレーション: 対象{len(targets)}語 + 変化形挿入{len(still)}形 すべて恒等ラテン化を確認')

if DRY:
    print('(DRY-RUN: --apply で書込)'); sys.exit(0)

# ── 適用(3言語) ──────────────────────────────────────────────────────────
ledger = {'valuefix': [], 'inserts': all_inserts}
for lang in ('JA', 'ZH', 'KO'):
    path, dd = DATA[lang]
    gg = strip_mine(dd[KEY])
    removed = len(dd[KEY]) - len(gg)
    for i, k, old in valuefix:
        if gg[i][0] != k:
            raise SystemExit(f'{lang} GG[{i}] キー不一致(適用中断): {gg[i][0]!r} != {k!r}')
        if lang == 'JA':
            ledger['valuefix'].append({'i': i, 'key': k, 'old': old, 'new': k})
        gg[i] = [gg[i][0], gg[i][0], gg[i][2] if len(gg[i]) > 2 else '']
    used = {e[2] for e in gg if len(e) > 2}
    rows = []
    for n, w in enumerate(all_inserts):
        ph = f' {TAGID}{n:04d}{"" if lang == "JA" else lang}$ '
        if ph in used: raise SystemExit(f'placeholder collision: {ph}')
        rows.append([' ' + w + ' ', ' ' + w + ' ', ph])
    dd[KEY] = splice(gg, rows)
    atomic_file_copy(LP(path), LP(path + '.bak_preR116'))
    atomic_json_dump(LP(path), dd)
    print(f'[{lang}] 値置換 {len(valuefix)} / 挿入 {len(rows)} (旧$R116L {removed} 件を除去 / '
          f'全域 {len(gg)} -> {len(dd[KEY])})')
json.dump(ledger, open(LP(os.path.join(AN, 'out', 'r116_valuefix_ledger.json')), 'w',
                       encoding='utf-8'), ensure_ascii=False, indent=1)
print('適用完了。ゲート(export/injection/3言語同一性/ハイフン)を必ず回すこと。')
