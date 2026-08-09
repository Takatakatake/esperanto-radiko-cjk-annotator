# -*- coding: utf-8 -*-
"""第124R: 第123R照会リストのB類=「マスター既存部品で合成可能なマスター外エスペラント実語」
   12語の漢字描画を部品合成で是正する。DRY既定 / --apply。

■ 対象と構成(部品は全てマスター実在行: 第124R世代確認時に実測)
  kafeja=kaf所a(kaf/ej/o→kaf所o実在) kafeto=kaf小o(dom/et/o→屋小o) kafpulvoro=kaf粉ᴾo
  kaftrinki=kaf饮i psikanalizisto=心ᴾˢ析家o(psik/a→心ᴾˢa+analiz/ist/o→析家o)
  rasistaj=种ᴿ家aj(ras/ist/o→种ᴿ家o実在) ruslanda=rus国a(rus/land/an/o→rus国员o)
  ruslingva=rus语a ĉinlingvaj/an=ĉin语aj/an(ĉin=ラテン維持) judaraj=jud群aj judisman=jud主义an
  ★taŭismo/romiajn は語根(taŭ/romi)がマスター外のため据置(照会リスト残置)
■ 作法
  値 = LIT(素のラテン) + アプリ実描画からの採取(REN=表層を描画し末尾ラテンn字を語尾に差替 /
  DH=先頭ruby要素をn個落とす)の連結。発明ゼロ。
  fail-closed: 採取元の描画がマスターflatと一致 / 合成値の「rt連結+ラテン」=対象表層(完全性) /
  現に壊れている語だけ挿入 / 3言語同一 / 適用後全対象再描画。冪等($R124C)。
  ルビ側は12語とも既に正しく分節・注釈されるため無変更(プレップで検証)。
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
TAGID = '$R124C'
RT = re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>'); TAG = re.compile(r'<[^>]+>')
RTC = re.compile(r'<rt[^>]*>((?:[^<]|<br\s*/?>)*?)</rt>')
RUBYEL = re.compile(r'<ruby>.*?</rt>\s*</ruby>', re.S)
def disp(seg): return TAG.sub('', RT.sub('', seg)).strip()
def surface_of(html):
    """rt連結+地のラテンで元表層を復元(完全性検査用)。"""
    out = []
    pos = 0
    for m in re.finditer(r'<ruby>(.*?)<rt[^>]*>((?:[^<]|<br\s*/?>)*?)</rt>\s*</ruby>', html, re.S):
        out.append(TAG.sub('', html[pos:m.start()]))
        out.append(re.sub(r'<br\s*/?>', '', m.group(2)))
        pos = m.end()
    out.append(TAG.sub('', html[pos:]))
    return ''.join(out).strip()

X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
flat_of = {}
for ln in open(LP(os.path.join(A.frozen, A.export_name)), encoding='utf-8'):
    if ln.startswith('#'): continue
    ps = ln.rstrip('\n').split('\t')
    if len(ps) >= 4: flat_of.setdefault(circ(ps[2].strip()), set()).add(circ(ps[3].strip()))

def LIT(t): return ('LIT', t)
def REN(surf, strip=0, app=''): return ('REN', surf, strip, app)
def DH(surf, drop=1, strip=0, app=''): return ('DH', surf, drop, strip, app)
PLAN = {
    'kafeja': [REN('kafejo', 1, 'a')],
    'kafeto': [LIT('kaf'), DH('dometo', 1)],
    'kafpulvoro': [LIT('kaf'), REN('pulvoro')],
    'kaftrinki': [LIT('kaf'), REN('trinki')],
    'psikanalizisto': [REN('psika', 1), REN('analizisto')],
    'rasistaj': [REN('rasisto', 1, 'aj')],
    'ruslanda': [LIT('rus'), REN('lando', 1, 'a')],
    'ruslingva': [LIT('rus'), REN('lingvo', 1, 'a')],
    'ĉinlingvaj': [LIT('ĉin'), REN('lingvo', 1, 'aj')],
    'ĉinlingvan': [LIT('ĉin'), REN('lingvo', 1, 'an')],
    'judaraj': [LIT('jud'), REN('aro', 1, 'aj')],
    'judisman': [LIT('jud'), REN('ismo', 1, 'an')],
}

sys.path.insert(0, os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA'))
import esp_text_replacement_module as M
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

ps_ = pl_ = None
outs = {}
plan_words = None
for lang in ('JA', 'ZH', 'KO'):
    app = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    path = os.path.join(app, 'app_data', '置換リスト_漢字.json')
    dd = json.load(open(LP(path), encoding='utf-8'))
    gg = [e for e in dd[KEY]
          if not (len(e) > 2 and isinstance(e[2], str) and TAGID in e[2])]
    GL = dd['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
    G2 = dd['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
    if ps_ is None:
        ps_ = M.import_placeholders(os.path.join(app, 'app_data', 'placeholders_skip.txt'))
        pl_ = M.import_placeholders(os.path.join(app, 'app_data', 'placeholders_localcapture.txt'))
    def render(t, g=gg):
        return M.orchestrate_comprehensive_esperanto_text_replacement(
            ' ' + t + ' ', ps_, GL, pl_, g, G2, '汉字替换_大小调整').strip()
    def harvest(op):
        if op[0] == 'LIT': return op[1]
        if op[0] == 'REN':
            _, surf, strip, appn = op
            h = render(surf)
            if disp(h) not in flat_of.get(surf, set()):
                raise SystemExit(f'fail-closed: 採取元 {surf} が不健全: {disp(h)!r}')
            if strip:
                if not h.endswith(surf[-strip:]):
                    raise SystemExit(f'fail-closed: {surf} 末尾が {surf[-strip:]!r} でない')
                h = h[:-strip]
            return h + appn
        if op[0] == 'DH':
            _, surf, drop, strip, appn = op
            h = render(surf)
            if disp(h) not in flat_of.get(surf, set()):
                raise SystemExit(f'fail-closed: 採取元 {surf} が不健全: {disp(h)!r}')
            for _i in range(drop):
                m = re.match(r'\s*<ruby>.*?</rt>\s*</ruby>', h, re.S)
                if not m: raise SystemExit(f'fail-closed: {surf} 先頭ruby要素が無い')
                h = h[m.end():]
            if strip: h = h[:-strip]
            return h + appn
        raise SystemExit('unknown op')
    rows_plan = []
    for w, ops in sorted(PLAN.items()):
        val = ''.join(harvest(op) for op in ops)
        if surface_of(val) != w:
            raise SystemExit(f'fail-closed: {w} 完全性NG: {surface_of(val)!r}')
        cur = disp(render(w))
        if cur == disp(' ' + val + ' '):
            continue
        rows_plan.append((w, val, cur))
    words = [w for w, _v, _c in rows_plan]
    if plan_words is None:
        plan_words = words
        print(f'[JA] 合成対象(現に壊れている): {len(rows_plan)}')
        for w, v, c in rows_plan: print(f'   {w}: {c} -> {disp(" " + v + " ")}')
    elif words != plan_words:
        raise SystemExit(f'{lang}: 対象集合がJAと不一致')
    used = {e[2] for e in gg if len(e) > 2}
    rows = []
    for n_, (w, v, _c) in enumerate(rows_plan):
        ph = f' {TAGID}{n_:02d}{"" if lang == "JA" else lang}$ '
        if ph in used: raise SystemExit(f'placeholder collision: {ph}')
        rows.append([' ' + w + ' ', ' ' + v + ' ', ph])
    gg2 = splice(gg, rows)
    for w, v, _c in rows_plan:
        got = disp(M.orchestrate_comprehensive_esperanto_text_replacement(
            ' ' + w + ' ', ps_, GL, pl_, gg2, G2, '汉字替换_大小调整'))
        if got != disp(' ' + v + ' '):
            raise SystemExit(f'fail-closed: {lang} {w} 未治癒: {got!r}')
    print(f'  [{lang}] 検証OK')
    outs[lang] = (path, dd, gg2, len(rows))

if DRY:
    print('(DRY-RUN: --apply で書込)'); sys.exit(0)
for lang, (path, dd, gg2, n_) in outs.items():
    dd[KEY] = gg2
    atomic_file_copy(LP(path), LP(path + '.bak_preR124'))
    atomic_json_dump(LP(path), dd)
    print(f'  [{lang}] 書込 挿入{n_} (全域 {len(gg2)})')
print('適用完了。漢字3ゲートを回すこと(ルビ無変更)。')
