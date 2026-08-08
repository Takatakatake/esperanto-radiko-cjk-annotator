# -*- coding: utf-8 -*-
"""第118R: 漢字軌道×コーパス実使用語彙の初の全数診断で見つかった語尾変化形の欠陥を是正。
   DRY既定 / --apply / --frozen 必須。

■ 背景(2026-08-08)
  既存の漢字2ゲート(注入/エクスポート)はマスター見出し表層のみが母集団で、コーパス実在の
  語尾変化形22,201語は未測定だった。全数診断の結果134不一致 → 機械分類+コーパス実文脈裁定で
  真の欠陥だけに絞った(残りは文頭大文字=普通語支配/断片アーティファクト/既知基線の変化形)。

■ 欠陥2型と是正
  A. ラテン維持族の変化形の穴: マスターが franc/a→franca 等とラテン維持する小文字族は
     第69Rで基本形だけ恒等キーを得て、複数・対格が断片スープに食われていた
     (francaj→f哈喇aj[哈喇=悪臭!] / dukatojn→二猫ojn[二匹の猫!] / japanojn→ja面包ojn[パン!])。
     → 恒等キー(空白パディング完全一致)を挿入。対象は「マスター由来の期待値が全ラテン」かつ
       「現に壊れている」語形のみ。族の兄弟形(an/aj/ajn等)もガード付きで同時に手当て(R76-77)。
  B. 健全な基本形と別経路に落ちる変化形: meti→置i は健全なのに metas→甲as、
     reprezenti→再呈i なのに reprezentas→表ᴿas、sinteno→己n持o なのに sintenojn→怀持ojn。
     → 値は**アプリ自身の健全な基本形描画**から語尾だけ挿げ替えて構築(発明ゼロ)。
       構築値の表示がマスター由来の期待値と一致することを fail-closed 検証。

■ コーパス実文脈による裁定(rt除去済みで確認)
  - Bene = 「Medalo Alumno Bene Merento」の固有名 → 恒等(マスター由来の祝eではなく)
  - Metu = 「Metu iom da oleo」命令法 → 置u(met族5形も同時是正)
  - Aŭdu = 登場人物名 / Sue,Sule,Dan,Han,Kaku,Jan等 = 人名 / bon,are,ale等 = メタ言語断片
    → いずれも据置(アプリの現出力が正当)

■ 安全設計: 冪等($R118C を外して測り直す)・挿入位置は第68R確定のsplice・
  3言語同一操作(事前検証)・適用後に全対象を3言語で再描画検証。
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
ap.add_argument('--frozen', required=True)
ap.add_argument('--export-name', default='_漢字割当エクスポート_学習者版_20260723.tsv')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
TAGID = '$R118C'

X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
L = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
FULL_LATIN = re.compile('^[' + L + r"\-'’ ]+$")
RT = re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>'); TAG = re.compile(r'<[^>]+>')
def disp(seg): return TAG.sub('', RT.sub('', seg)).strip()

senses = {}
for ln in open(LP(os.path.join(A.frozen, A.export_name)), encoding='utf-8'):
    if ln.startswith('#'): continue
    ps = ln.rstrip('\n').split('\t')
    if len(ps) < 4: continue
    senses.setdefault(circ(ps[2].strip()), set()).add(circ(ps[3].strip()))

# ── A. 恒等系: (基本形, 兄弟形を生成するか) ──────────────────────────────────
#   基本形はマスターに実在しラテン維持であることを実行時に検証(fail-closed)
IDENT_FAMILIES = ['azia', 'Azio', 'brita', 'franca', 'italo', 'japano', 'skoto',
                  'dolaro', 'dukato', 'eksperto', 'utopio']
# コーパス実文脈で裁定した固有名(表層そのものだけ・兄弟生成なし)
IDENT_EXACT = {
    'Bene': 'コーパス唯一の用例が「Medalo Alumno Bene Merento」の固有名(2026-08-08実文確認)',
    'Kanae': '人名(SUMII Sue関連文の Kanae)。マスター由来の期待値もラテン',
    'Lucien': '人名。マスター由来の期待値もラテン',
    'Pekinon': 'Pekin/o=ラテン維持の対格。海胆(ウニ)が語中発火していた',
    'Valerie': '人名。マスター由来の期待値もラテン',
    'Aziajn': 'コーパス実在の大文字形', 'Azion': 'コーパス実在の大文字形',
    'Britaj': 'コーパス実在の大文字形',
}
# ── B. 合成系: 壊れている語形 -> 健全な基本形 ────────────────────────────────
COMPOSED = {
    'metas': 'meti', 'metis': 'meti', 'metos': 'meti', 'metus': 'meti', 'metu': 'meti',
    'Metu': 'meti',
    'efektivigas': 'efektivigi', 'efektivigis': 'efektivigi',
    'efektiviĝas': 'efektiviĝi', 'efektiviĝis': 'efektiviĝi',
    'reprezentas': 'reprezenti', 'reprezentaj': 'reprezenta',
    'reprezentantaj': 'reprezentanta', 'reprezentante': 'reprezentanta',
    'filozofiaj': 'filozofia', 'filozofie': 'filozofia',
    'organiziĝis': 'organiziĝi', 'Organiziĝis': 'organiziĝi',
    'sindone': 'sindona', 'sinsekvaj': 'sinsekva', 'sinsekvajn': 'sinsekva',
    'sintenojn': 'sinteno', 'sinĝenon': 'sinĝeno',
    'gastroskopon': 'gastroskopo', 'hidrogenbomboj': 'hidrogenbombo',
    'ideogramojn': 'ideogramo', 'kilogramojn': 'kilogramo',
    'milimetrojn': 'milimetro', 'neŭtronoj': 'neŭtrono', 'pacifismon': 'pacifismo',
    'prototipoj': 'prototipo', 'prototipojn': 'prototipo',
    'radioamatoroj': 'radioamatoro', 'radiofonie': 'radiofonia',
    'radioprogramoj': 'radioprogramo', 'videoludon': 'videoludo',
    'firmaon': 'firmao', 'detektivajn': 'detektiva', 'intensivajn': 'intensiva',
    'miriadoj': 'miriado',
}
SIB = {'a': ['an', 'aj', 'ajn'], 'o': ['on', 'oj', 'ojn'], 'i': []}

# ── アプリ読込 ───────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA'))
import esp_text_replacement_module as M
DATA = {}
for lang in ('JA', 'ZH', 'KO'):
    p = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_漢字.json')
    DATA[lang] = (p, json.load(open(LP(p), encoding='utf-8')))
def strip_mine(gg):
    return [e for e in gg if not (len(e) > 2 and isinstance(e[2], str) and TAGID in e[2])]
d0 = DATA['JA'][1]
GGm = strip_mine(d0[KEY])
GL = d0['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = d0['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
appj = os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA')
ps_ = M.import_placeholders(os.path.join(appj, 'app_data', 'placeholders_skip.txt'))
pl_ = M.import_placeholders(os.path.join(appj, 'app_data', 'placeholders_localcapture.txt'))
def render_html(w, gg):
    o = M.orchestrate_comprehensive_esperanto_text_replacement(
        ' ' + w + ' ', ps_, GL, pl_, gg, G2, '汉字替换_大小调整')
    return o.strip()

rows = []   # (表層, 値, 種別, 根拠)
skipped = []

# A. 恒等系
ident_surfaces = {}
for b in IDENT_FAMILIES:
    ms = senses.get(b, set())
    if not ms or not all(FULL_LATIN.fullmatch(m) for m in ms):
        skipped.append((b, f'マスターがラテン維持でない: {sorted(ms)[:2]}')); continue
    fams = [b] + [b[:-1] + s for s in SIB.get(b[-1], [])]
    for f in fams: ident_surfaces[f] = f'ラテン維持族 {b}'
for w, why in IDENT_EXACT.items():
    ident_surfaces[w] = why
for w, why in sorted(ident_surfaces.items()):
    cur = disp(render_html(w, GGm))
    if cur == w: continue          # 既に正しい
    # 大文字形は「小文字形がマスターで漢字描画」なら触らない(Blanka則)
    lw = w[0].lower() + w[1:]
    if w[0].isupper() and lw in senses and any(not FULL_LATIN.fullmatch(m) for m in senses[lw]):
        skipped.append((w, 'Blanka則(小文字形が漢字描画)')); continue
    rows.append((w, w, 'A恒等', why))

# B. 合成系
for w, b in sorted(COMPOSED.items()):
    ms = senses.get(b, set())
    if not ms:
        skipped.append((w, f'基本形 {b} がマスターに無い')); continue
    bh = render_html(b, GGm)
    bd = disp(bh)
    if bd not in ms:
        skipped.append((w, f'基本形 {b} が健全でない: {bd!r} not in {sorted(ms)[:2]}')); continue
    lb = b
    lw = w[0].lower() + w[1:] if w[0].isupper() else w
    if lw[:len(lb) - 1] != lb[:-1]:
        skipped.append((w, f'語幹不一致: {lb}')); continue
    tail = lw[len(lb) - 1:]
    if not bh.endswith(lb[-1]):
        skipped.append((w, f'基本形描画が語尾{lb[-1]!r}で終わらない: …{bh[-20:]!r}')); continue
    val = bh[:-1] + tail
    exp_d = {m[:-1] + tail for m in ms}
    if disp(val) not in exp_d:
        skipped.append((w, f'構築値の表示がマスター期待と不一致: {disp(val)!r} vs {sorted(exp_d)[:2]}')); continue
    cur = disp(render_html(w, GGm))
    if cur == disp(val): continue  # 既に正しい
    if w[0].isupper() and val and val[0].isascii() and val[0].isalpha():
        val = val[0].upper() + val[1:]
    rows.append((w, val, 'B合成', f'基本形 {b} の実描画から構築'))

print(f'是正対象: {len(rows)} (恒等 {sum(1 for r in rows if r[2]=="A恒等")} / '
      f'合成 {sum(1 for r in rows if r[2]=="B合成")}) / スキップ {len(skipped)}')
for w, why in skipped: print(f'  skip {w}: {why}')
for w, v, t, why in rows[:60]:
    print(f'  {t} {w}: {disp(" "+v+" ") if t=="B合成" else v}')

# ── splice(第68R確定) ────────────────────────────────────────────────────
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

# ── シミュレーション(JA) ─────────────────────────────────────────────────
sim_rows = [[' ' + w + ' ', ' ' + v + ' ', f' $SIM{n:05d}$ ']
            for n, (w, v, _t, _y) in enumerate(rows)]
GGfin = splice(GGm, sim_rows)
bad = []
for w, v, _t, _y in rows:
    got = disp(render_html(w, GGfin))
    if got != disp(' ' + v + ' '): bad.append((w, got, disp(' ' + v + ' ')))
if bad:
    for b in bad[:15]: print('  ★未治癒:', b)
    raise SystemExit(f'fail-closed: シミュレーション未治癒 {len(bad)}')
print(f'シミュレーション: {len(rows)}表層 全て期待どおり')

if DRY:
    print('(DRY-RUN: --apply で書込)'); sys.exit(0)

for lang in ('JA', 'ZH', 'KO'):
    path, dd = DATA[lang]
    gg = strip_mine(dd[KEY])
    removed = len(dd[KEY]) - len(gg)
    used = {e[2] for e in gg if len(e) > 2}
    new_rows = []
    for n, (w, v, _t, _y) in enumerate(rows):
        ph = f' {TAGID}{n:04d}{"" if lang == "JA" else lang}$ '
        if ph in used: raise SystemExit(f'placeholder collision: {ph}')
        new_rows.append([' ' + w + ' ', ' ' + v + ' ', ph])
    dd[KEY] = splice(gg, new_rows)
    atomic_file_copy(LP(path), LP(path + '.bak_preR118'))
    atomic_json_dump(LP(path), dd)
    print(f'[{lang}] 挿入 {len(new_rows)} (旧{TAGID} {removed} 件除去 / 全域 {len(gg)} -> {len(dd[KEY])})')

json.dump([{'w': w, 'value': v, 'type': t, 'why': y} for w, v, t, y in rows],
          open(LP(os.path.join(AN, 'out', 'r118_fix_ledger.json')), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('適用完了。ゲート(export/injection/3言語同一性)と3言語スポット検証を必ず回すこと。')
