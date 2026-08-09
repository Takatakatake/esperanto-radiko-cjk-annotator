# -*- coding: utf-8 -*-
"""三表記入力(ĉ/cx/c^)等価性ゲート(第128R新設)。
理論: orchestrate は最初に convert_to_circumflex するため、
  N(down_x(T)) == N(T) かつ N(down_hat(T)) == N(T)
が成り立てば出力等価が全機能経路(%/@込み)で保証される(N=正規化)。
検査: ①変換辞書6本+convert_to_circumflexの3言語同一(挙動比較) ②コーパス全HTML本文
③コーパス実使用語彙。将来モジュールの前処理順序を変えた場合の破壊を検出する。
不一致で非0終了。digraph偽変換(Linux型: 真形にcx/ux等を含む外来語)の census も表示
(既知2件=Chaux-de-Fonds/Gembloŭ は据置裁定・第128R)。
"""
import json, os, re, sys, glob, html as htmllib, importlib.util
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92)+chr(92)+chr(63)+chr(92)
def LP(p): return PFX + os.path.abspath(p)
AN = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AN)
CORPUS = r'D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\Esperanto_HTML文書\京大エス研html文書＿Github'

fail = False
mods = {}
for L in ('JA', 'ZH', 'KO'):
    p = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{L}', 'esp_text_replacement_module.py')
    spec = importlib.util.spec_from_file_location(f'etr_{L}', p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    mods[L] = m
M = mods['JA']
DICTS = ['x_to_circumflex', 'circumflex_to_x', 'hat_to_circumflex',
         'circumflex_to_hat', 'hat_to_x', 'x_to_hat']
ok = all(getattr(mods['JA'], n) == getattr(mods['ZH'], n) == getattr(mods['KO'], n) for n in DICTS)
stress = ('cx gx hx jx sx ux Cx Gx Hx Jx Sx Ux c^ g^ h^ j^ s^ u^ C^ G^ H^ J^ S^ U^ '
          'ĉĝĥĵŝŭ ĈĜĤĴŜŬ sxatas s^atas ŝatas CXU Linux aux 3cx x^ ^c xc')
ok &= (mods['JA'].convert_to_circumflex(stress) == mods['ZH'].convert_to_circumflex(stress)
       == mods['KO'].convert_to_circumflex(stress))
print(f'①変換辞書+挙動の3言語同一: {"PASS" if ok else "FAIL"}')
fail |= not ok

N = M.convert_to_circumflex
def down_x(t): return M.replace_esperanto_chars(t, M.circumflex_to_x)
def down_hat(t): return M.replace_esperanto_chars(t, M.circumflex_to_hat)

STYLE = re.compile(r'<(style|script)[^>]*>.*?</\1>', re.S | re.I)
RT = re.compile(r'<rt[^>]*>.*?</rt>', re.S)
TAG = re.compile(r'<[^>]+>')
WORD = re.compile(r"[A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬÀ-ÖØ-öø-ɏ'’-]+")
files = glob.glob(os.path.join(CORPUS, '**', '*.html'), recursive=True)
if not files:
    print(f'FAIL: コーパスが空({CORPUS})'); sys.exit(1)
bad = 0
census = {}
for fp in files:
    raw = open(LP(fp), encoding='utf-8', errors='replace').read()
    txt = htmllib.unescape(TAG.sub(' ', RT.sub('', STYLE.sub(' ', raw))))
    nt = N(txt)
    if N(down_x(txt)) != nt or N(down_hat(txt)) != nt:
        bad += 1
        print('  NG:', os.path.basename(fp))
    for w in WORD.findall(txt):
        if N(w) != w and w not in census:
            census[w] = os.path.basename(fp)
print(f'②コーパス全文({len(files)}本): 表記間不一致 {bad}本 -> {"PASS" if not bad else "FAIL"}')
fail |= bad > 0

wp = os.path.join(AN, 'out', '_r109_corpus_words.json')
words = json.load(open(LP(wp), encoding='utf-8'))
wl = words['words'] if isinstance(words, dict) else words
badw = [w for w in wl if N(down_x(w)) != N(w) or N(down_hat(w)) != N(w)]
print(f'③語彙({len(wl)}語): 表記間不一致 {len(badw)}語 -> {"PASS" if not badw else "FAIL"}')
for w in badw[:10]: print('   ', w)
fail |= bool(badw)

print(f'(参考) digraph偽変換 census: {len(census)}語 '
      f'(index.htmlのxスラッグ等は正当変換・外来固有名の実害は据置2件)')
sys.exit(1 if fail else 0)
