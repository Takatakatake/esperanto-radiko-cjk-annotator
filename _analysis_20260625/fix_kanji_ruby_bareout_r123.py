# -*- coding: utf-8 -*-
"""第123R: マスター外残余5,139語のガーブル署名スイープの是正。DRY既定 / --apply。

■ 診断(scratchpad r123_residue_sweep.py / r123_ctx_all.py, 2026-08-08)
  漢字頭食い署名408 + ルビ語頭裸署名6。全て「マスター外の語が語中の語根キーに食われる」型
  (Cambridge→C龙香子双 / Adam→A妃 / Chiune→Ch某u不 / ルビ Witold→Witol[糖アルコール]d)。

■ 裁定規則
  裸化する(恒等キー挿入):
   1. 大文字始まり(外国固有名詞。残余=導出不能なので文頭普通語の可能性は構造的に無い)
   2. 小文字でも非エスペラント文字(wxyq)含み or 明白な外国語/音写(実文脈で確認済)
   3. ラテン固定語根族の派生(マスター実測: Tajvan/o・Vien/a・Kansaj/o・maori/oj 全てラテン)
  据置:
   - 実文0件(語彙抽出アーティファクト) / コーパス側タイポ(lauta/rakonis/niiaj/atinis等)
   - ★B類=合成が本筋のエスペラント実語(kafeja→kaf所a型)。マスター既存部品で組めるため
     裸化せず第124R軸+照会リスト(out/_r123_compose_referral.tsv)に回す
  ルビ側は署名6語のみ裸化(Jamada[人名]山田 のような京大由来の正当な全語注釈は殺さない)。
■ 冪等($R123B)・パディング完全一致キー・splice・3言語同一・全対象sim検証。
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
ap.add_argument('--flags', default='')
ap.add_argument('--ctx', default='')
A = ap.parse_args()
DRY = not A.apply
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
TAGID = '$R123B'
L = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
RT = re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>'); TAG = re.compile(r'<[^>]+>')
def disp(seg): return TAG.sub('', RT.sub('', seg)).strip()

flags = json.load(open(LP(A.flags), encoding='utf-8'))
ctx = json.load(open(LP(A.ctx), encoding='utf-8'))

# B類: 合成が本筋のエスペラント実語(据置+照会)
COMPOSE_REFERRAL = {
    'kafeja': 'kaf/ej/o→kaf所o 実在。kaf所a が本筋', 'kafeto': 'kaf小o(et=小)',
    'kafpulvoro': 'kaf+粉ᴾ?合成要検討', 'kaftrinki': 'kaf+飲i合成要検討',
    'judaraj': 'jud=ラテン+ar=群 → jud群aj', 'judisman': 'jud主义an',
    'psikanalizisto': 'psik=心ᴾˢ+析+家 → 心ᴾˢ析家o', 'rasistaj': 'ras=种ᴿ → 种ᴿ家aj',
    'ruslanda': 'rus/land/an/o→rus国员o 実在 → rus国a', 'ruslingva': 'rus语a',
    'ĉinlingvaj': 'ĉin=ラテン+语 → ĉin语aj', 'ĉinlingvan': 'ĉin语an',
    'taŭismo': 'taŭ がマスター外。道主义o 候補はマスター照会', 'romiajn': 'romi 語根がマスター外。照会',
}
# コーパス側タイポ(直すべきはコーパスであってアプリではない)
TYPOS = {'lauta', 'rakonis', 'niiaj', 'atinis', 'marapide', 'lomete', 'aubas',
         'bjetrime', 'broj', 'fŭsmova', 'vuouve', 'legaC'}
# ラテン固定語根族の派生(マスター実測でラテン確認済み)
LATIN_FAMILY = {'tajvana', 'tajvanajn', 'maoria', 'vienaj', 'kansaja', 'kansajaj',
                'vroclava', 'vroclavanoj'}

kanji_words, ruby_words, leaves = [], [], []
for f in flags['kanji']:
    w = f['w']
    n = ctx.get(w, {}).get('n', 0)
    if n == 0:
        leaves.append((w, '実文0件')); continue
    if w in TYPOS:
        leaves.append((w, 'コーパス側タイポ')); continue
    if w in COMPOSE_REFERRAL:
        leaves.append((w, 'B類=合成が本筋(照会)')); continue
    if w[0].isupper() or re.search(r'[wxyqWXYQ]', w) or w in LATIN_FAMILY:
        kanji_words.append(w); continue
    # 残り: 小文字Eo正書法だが上記いずれでもない → 外国語/音写(実文脈確認済クラス)
    kanji_words.append(w)
for f in flags['ruby']:
    w = f['w']
    if ctx.get(w, {}).get('n', 0) > 0:
        ruby_words.append(w)
kanji_words = sorted(set(kanji_words)); ruby_words = sorted(set(ruby_words))
print(f'漢字裸化: {len(kanji_words)} / ルビ裸化: {len(ruby_words)} / 据置: {len(leaves)}')
for w, why in leaves:
    if '0件' not in why: print(f'  据置 {w}: {why}')

# マスター表層(両ケースが表層でないことの最終ガード)
EXPORT = (r'D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学'
          r'\エスペラントの漢字化プロジェクト総結集20260630'
          r'\エスペラント語根＿漢字割り当て＿20260630\_漢字割当エクスポート_学習者版_20260723.tsv')
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
surfs = set()
for ln in open(LP(EXPORT), encoding='utf-8'):
    if ln.startswith('#'): continue
    ps = ln.rstrip('\n').split('\t')
    if len(ps) >= 4: surfs.add(circ(ps[2].strip()))
for w in kanji_words + ruby_words:
    lw = w[0].lower() + w[1:]
    if w in surfs or lw in surfs:
        raise SystemExit(f'fail-closed: {w} はマスター表層(裸化対象外のはず)')

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
def process(track, words):
    global ps_, pl_
    fmt = 'HTML格式_Ruby文字_大小调整' if track == 'ルビ' else '汉字替换_大小调整'
    outs = {}
    targets_ref = None
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
        def render(t, g):
            return M.orchestrate_comprehensive_esperanto_text_replacement(
                ' ' + t + ' ', ps_, GL, pl_, g, G2, fmt)
        # 現に壊れている語だけ(言語毎に判定はJA基準と同一のはずだが個別ガード)
        targets = []
        B = 300; SEP = '◆'
        for i in range(0, len(words), B):
            ch = words[i:i+B]
            o = render((' ' + SEP + ' ').join(ch), gg)
            parts = o.split(SEP)
            if len(parts) != len(ch):
                parts = [render(w, gg) for w in ch]
            for w, seg in zip(ch, parts):
                broken = ('<ruby>' in seg) if track == 'ルビ' else (disp(seg) != w)
                if broken: targets.append(w)
        if targets_ref is None:
            targets_ref = targets
            print(f'[{track}] 裸化対象(現に壊れている): {len(targets)}')
        elif targets != targets_ref:
            raise SystemExit(f'{lang} {track}: 対象集合がJAと不一致')
        used = {e[2] for e in gg if len(e) > 2}
        rows = []
        for n_, w in enumerate(targets):
            ph = f' {TAGID}{n_:04d}{"" if lang == "JA" else lang}$ '
            if ph in used: raise SystemExit(f'placeholder collision: {ph}')
            rows.append([' ' + w + ' ', ' ' + w + ' ', ph])
        gg2 = splice(gg, rows)
        bad = []
        for i in range(0, len(targets), B):
            ch = targets[i:i+B]
            o = render((' ' + SEP + ' ').join(ch), gg2)
            parts = o.split(SEP)
            if len(parts) != len(ch):
                parts = [render(w, gg2) for w in ch]
            for w, seg in zip(ch, parts):
                ok = ('<ruby>' not in seg and disp(seg) == w)
                if not ok: bad.append((w, disp(seg)))
        if bad:
            for b in bad[:10]: print('  ★未治癒:', b)
            raise SystemExit(f'fail-closed: {lang} {track} 未治癒 {len(bad)}')
        outs[lang] = (path, dd, gg2, len(rows))
    if DRY:
        print(f'[{track}] シミュレーションOK({targets_ref and len(targets_ref)}語×3言語)')
        return
    for lang, (path, dd, gg2, n_) in outs.items():
        dd[KEY] = gg2
        atomic_file_copy(LP(path), LP(path + '.bak_preR123'))
        atomic_json_dump(LP(path), dd)
        print(f'  [{lang}] {track} 挿入 {n_} (全域 {len(gg2)})')

process('漢字', kanji_words)
process('ルビ', ruby_words)

refp = os.path.join(AN, 'out', '_r123_compose_referral.tsv')
if not DRY:
    with open(LP(refp), 'w', encoding='utf-8') as f:
        f.write('# 第123R B類: マスター既存部品で合成可能なマスター外エスペラント実語(第124R軸+照会)\n')
        for w, why in sorted(COMPOSE_REFERRAL.items()):
            f.write(f'{w}\t{why}\n')
    print('照会リスト:', refp)
print('(DRY-RUN: --apply で書込)' if DRY else '適用完了。両軌道ゲートを回すこと。')
