# -*- coding: utf-8 -*-
"""第122R: 分詞/ad派生スイープ(旧・導出不能1,050語)で見つかった真欠陥の是正。
   DRY既定 / --apply。

■ 診断(2026-08-08, scratchpad r122_participle_sweep.py + コーパス実文確認)
  - Jamada(山田耕筰)→ Jama份 / Okada(岡田さん)→ O木ᴷᴰa : 人名が語根キーに食われる(漢字軌道。
    ルビ軌道は京大由来の [人名]山田/岡田 注釈が既に正しく出る)→ 恒等ラテン化(Kanae前例)
  - metinte → 甲过e : 第118R met族是正(as/is/os/us/u)の分詞形の取り残し → 置过e
  - telefoninta/telefoninto → 远声ᶠᴼinta(int素通し) → 远声ᶠᴼ过a/o
  - tempopasigadon → ★専用GG行の保存値が生成時から a+don 誤読(ルビ=…adon[与える] /
    漢字=…a给)。大文字変種行も同罪 → 値置換で ad[継続]on / 行on に(順序・ID不変)
  - 据置: diskantis=dis+kant+isの詩的表現でアプリ正 / prante=実文0件 / Kosadi=ラテン素通しで正
■ 作法: 値はアプリ自身の健全描画とGG接尾辞行(inte/inta/into=过, adoj=ad[継続])から採取
  (発明ゼロ)。挿入はパディング完全一致キー+splice。冪等($R122P)。ルビのrt語義は言語毎に
  その言語のGG行から採取(3言語で分節同一・語義は各言語版)。
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
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
TAGID = '$R122P'
RT = re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>'); TAG = re.compile(r'<[^>]+>')
def disp(seg): return TAG.sub('', RT.sub('', seg)).strip()

sys.path.insert(0, os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA'))
import esp_text_replacement_module as M
ps_ = pl_ = None

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

# ★接尾辞はマスター合議でグリフ確認済みの ant=在 / int=过 系のみ(第122R実測: 'ota'行は
#   耳ᴼᵀ=語彙衝突行で、at/it/ot/ont はマスター行から確認できない → 生成禁止=発明ゼロ)
MET_SUFS = ('inte', 'inta', 'into', 'anta', 'ante', 'anto')
DON_TAIL = re.compile(r'a<ruby>(?:don|给|don)<rt[^>]*>[^<]*</rt></ruby>\s*$')

def process(track):
    """track: 'ルビ' or '漢字'。言語毎に (挿入行, 値置換) を計画・検証・適用。"""
    global ps_, pl_
    results = {}
    plan_shape = None
    for lang in ('JA', 'ZH', 'KO'):
        app = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
        path = os.path.join(app, 'app_data', f'置換リスト_{track}.json')
        dd = json.load(open(LP(path), encoding='utf-8'))
        gg = [e for e in dd[KEY]
              if not (len(e) > 2 and isinstance(e[2], str) and TAGID in e[2])]
        GL = dd['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
        G2 = dd['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
        if ps_ is None:
            ps_ = M.import_placeholders(os.path.join(app, 'app_data', 'placeholders_skip.txt'))
            pl_ = M.import_placeholders(os.path.join(app, 'app_data', 'placeholders_localcapture.txt'))
        fmt = 'HTML格式_Ruby文字_大小调整' if track == 'ルビ' else '汉字替换_大小调整'
        def render(t, g=gg):
            return M.orchestrate_comprehensive_esperanto_text_replacement(
                ' ' + t + ' ', ps_, GL, pl_, g, G2, fmt)
        bykey = {}
        for i, e in enumerate(gg):
            if isinstance(e[0], str): bykey.setdefault(e[0].strip(), []).append(i)
        def sufrow(sfx):
            for i in bykey.get(sfx, []):
                v = gg[i][1]
                if disp(v).endswith(sfx[-1]) and v != sfx: return v
            return None
        inserts, valfix = [], []
        if track == '漢字':
            # 1) 人名の恒等ラテン化
            for w in ('Jamada', 'Okada'):
                if disp(render(w)) != w:
                    inserts.append((w, w))
            # 2) met族分詞(壊れている形だけ)。値 = 置(metiの実描画から) + 接尾辞行値
            met_html = render('meti').strip()
            if not met_html.endswith('i'):
                raise SystemExit('fail-closed: meti描画が i で終わらない')
            met_head = met_html[:-1]
            if disp(met_head + 'i') != disp(met_html):
                raise SystemExit('fail-closed: met頭部の切り出し不整合')
            for sfx in MET_SUFS:
                w = 'met' + sfx
                srow = sufrow(sfx)
                if srow is None: continue
                exp = met_head + srow
                if disp(render(w)) != disp(exp):
                    inserts.append((w, exp))
            # 3) telefon族(int素通し)。頭 = telefoniの実描画から
            tel_html = render('telefoni').strip()
            if not tel_html.endswith('i'):
                raise SystemExit('fail-closed: telefoni描画が i で終わらない')
            tel_head = tel_html[:-1]
            for sfx in ('inta', 'into', 'inte'):
                w = 'telefon' + sfx
                srow = sufrow(sfx)
                if srow is None: continue
                exp = tel_head + srow
                if disp(render(w)) != disp(exp):
                    inserts.append((w, exp))
            # 4) tempopasigadon: 既存行があれば値置換(尾部 a+给 → 行on)、無ければ採取合成で挿入
            adonv = sufrow('adon')
            if adonv is None: raise SystemExit('fail-closed: 漢字 adon 行が見つからない')
            found_tpa = False
            for kf in ('tempopasigadon', 'Tempopasigadon'):
                for i in bykey.get(kf, []):
                    old = gg[i][1]
                    new = DON_TAIL.sub(adonv, old)
                    if new == old:
                        raise SystemExit(f'fail-closed: {kf} 尾部パターン不一致: …{old[-60:]!r}')
                    valfix.append((i, old, new)); found_tpa = True
            if not found_tpa:
                t_head = render('tempo').strip()
                p_html = render('pasigi').strip()
                if not (t_head.endswith('o') and p_html.endswith('i')):
                    raise SystemExit('fail-closed: tempo/pasigi の採取形が想定外')
                exp = t_head + p_html[:-1] + adonv
                if disp(render('tempopasigadon')) != disp(exp):
                    inserts.append(('tempopasigadon', exp))
        else:  # ルビ
            adojv = sufrow('adoj')
            if adojv is None or not adojv.endswith('oj'):
                raise SystemExit('fail-closed: ルビ adoj 行が見つからない')
            adonv = adojv[:-2] + 'on'
            for kf in ('tempopasigadon', 'Tempopasigadon'):
                for i in bykey.get(kf, []):
                    old = gg[i][1]
                    new = DON_TAIL.sub(adonv, old)
                    if new == old:
                        raise SystemExit(f'fail-closed: {kf} 尾部パターン不一致: …{old[-70:]!r}')
                    valfix.append((i, old, new))
        # ── 形状の3言語一致検証(挿入表層と値置換の対象キー) ──
        shape = (tuple(w for w, _ in inserts), tuple(gg[i][0] for i, _o, _n in valfix))
        if plan_shape is None:
            plan_shape = shape
            print(f'[{track}] 挿入 {len(inserts)} / 値置換 {len(valfix)}')
            for w, v in inserts: print(f'   + {w} -> {disp(" " + v + " ") if v != w else "(恒等)"}')
            for i, _o, n in valfix: print(f'   ~ {gg[i][0]!r} 尾部 -> {disp(n)[-14:]}')
        elif shape != plan_shape:
            raise SystemExit(f'{lang} {track}: 計画形状がJAと不一致(3言語同一性が壊れる)')
        # ── 検証: 適用後描画 ──
        gg2 = [list(e) for e in gg]
        for i, _o, n in valfix: gg2[i][1] = n
        used = {e[2] for e in gg2 if len(e) > 2}
        rows = []
        for n_, (w, v) in enumerate(inserts):
            ph = f' {TAGID}{n_:02d}{"" if lang == "JA" else lang}$ '
            if ph in used: raise SystemExit(f'placeholder collision: {ph}')
            rows.append([' ' + w + ' ', ' ' + v + ' ', ph])
        gg2 = splice(gg2, rows)
        for w, v in inserts:
            got = disp(M.orchestrate_comprehensive_esperanto_text_replacement(
                ' ' + w + ' ', ps_, GL, pl_, gg2, G2, fmt))
            if got != disp(' ' + v + ' '):
                raise SystemExit(f'fail-closed: {lang} {track} {w}: {got!r}')
        if track == 'ルビ':
            got = M.orchestrate_comprehensive_esperanto_text_replacement(
                ' tempopasigadon ', ps_, GL, pl_, gg2, G2, fmt)
            base_chain = TAG.sub('', RT.sub('', got)).strip()
            if base_chain != 'tempopasigadon':
                raise SystemExit(f'fail-closed: {lang} ルビ tempopasigadon 表層破壊: {base_chain!r}')
            if lang == 'JA' and '与える' in got:
                raise SystemExit('fail-closed: JA tempopasigadon に与えるが残存')
        results[lang] = (path, dd, gg2)
        print(f'  [{lang}] 検証OK')
    if DRY:
        return 0
    n_ops = 0
    for lang, (path, dd, gg2) in results.items():
        dd[KEY] = gg2
        atomic_file_copy(LP(path), LP(path + '.bak_preR122'))
        atomic_json_dump(LP(path), dd)
        n_ops += 1
        print(f'  [{lang}] {track} 書込 (全域 {len(gg2)})')
    return n_ops

process('漢字')
process('ルビ')
if DRY:
    print('(DRY-RUN: --apply で書込)')
else:
    print('適用完了。両軌道ゲートを回すこと。')
