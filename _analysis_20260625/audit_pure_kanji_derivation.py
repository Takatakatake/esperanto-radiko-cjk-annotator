# -*- coding: utf-8 -*-
"""純粋置換JSON派生ゲート(第125R新設)。derive_pure_kanji.py 実行後の検査3点:
 A. 派生同一性: 3リスト全行で キー/占位符が漢字JSONと同一 かつ 値==strip(漢字値)
 B. マーカー同期: ラウンドマーカー($RnnnX)集計が漢字JSONと完全一致
 C. 端到端: コーパス実使用語彙全量で 純粋置換出力 == 漢字(ルビ付き)出力のタグ剥がし
不一致があれば非0終了。第116〜124Rで再導出漏れ(第110R世代のまま配信)をやった反省で新設。
"""
import json, os, re, sys, argparse
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92)+chr(92)+chr(63)+chr(92)
def LP(p): return PFX + os.path.abspath(p)
AN = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AN)
APP = os.path.join(ROOT, 'Esperanto-Kanji-Ruby-JA')
AD = os.path.join(APP, 'app_data')
KEY = '全域替换用のリスト(列表)型配列(replacements_final_list)'
KGL = '局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)'
KG2 = '二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)'

ap = argparse.ArgumentParser()
ap.add_argument('--words', default=os.path.join(AN, 'out', '_r109_corpus_words.json'),
                help='コーパス実使用語彙JSON({"words":[...]}またはリスト)')
A = ap.parse_args()

dk = json.load(open(LP(os.path.join(AD, '置換リスト_漢字.json')), encoding='utf-8'))
dp = json.load(open(LP(os.path.join(AD, '置換リスト_漢字_純粋置換.json')), encoding='utf-8'))

def strip(v):
    v = re.sub(r'<rt[^>]*>.*?</rt>', '', v)
    return v.replace('<ruby>', '').replace('</ruby>', '')

fail = False
bad = 0
for k in (KEY, KGL, KG2):
    a, b = dk[k], dp[k]
    if len(a) != len(b):
        print(f'NG: {k} 行数 {len(a)} vs {len(b)}'); bad += 1; continue
    for i, (ea, eb) in enumerate(zip(a, b)):
        if ea[0] != eb[0] or strip(ea[1]) != eb[1] or list(ea[2:]) != list(eb[2:]):
            bad += 1
            if bad <= 5: print(f'NG: {k}[{i}] {ea[0]!r}')
print(f'A. 派生同一性: {"PASS" if bad == 0 else f"FAIL {bad}"} '
      f'(GG {len(dk[KEY])}行/GL {len(dk[KGL])}/G2 {len(dk[KG2])})')
fail |= bad > 0

def marks(d):
    c = Counter()
    for e in d[KEY]:
        if len(e) > 2 and isinstance(e[2], str):
            m = re.match(r'\s*\$R(\d+)[A-Z]', e[2])
            if m: c['R'+m.group(1)] += 1
    return dict(sorted(c.items(), key=lambda x: int(x[0][1:])))
mk, mp = marks(dk), marks(dp)
ok = mk == mp
print(f'B. マーカー同期: {"PASS" if ok else "FAIL"} {mp}')
fail |= not ok

sys.path.insert(0, APP)
import esp_text_replacement_module as M
ps = M.import_placeholders(os.path.join(AD, 'placeholders_skip.txt'))
pl = M.import_placeholders(os.path.join(AD, 'placeholders_localcapture.txt'))
TAG = re.compile(r'<[^>]+>')
def flat(html): return TAG.sub('', re.sub(r'<rt[^>]*>.*?</rt>', '', html))

words = json.load(open(LP(A.words), encoding='utf-8'))
wl = words['words'] if isinstance(words, dict) else words
text = '\n'.join(wl)
outk = M.orchestrate_comprehensive_esperanto_text_replacement(
    text, ps, dk[KGL], pl, dk[KEY], dk[KG2], '汉字替换_大小调整')
outp = M.orchestrate_comprehensive_esperanto_text_replacement(
    text, ps, dp[KGL], pl, dp[KEY], dp[KG2], '替换后文字列のみ(仅)保留(简单替换)')
lk = [x.strip() for x in flat(outk).split('\n')]
lp = [x.strip() for x in outp.split('\n')]
if not (len(lk) == len(lp) == len(wl)):
    print(f'C. 行数不一致 {len(lk)}/{len(lp)}/{len(wl)}'); fail = True
else:
    diff = [(w, a, b) for w, a, b in zip(wl, lk, lp) if a != b]
    print(f'C. コーパス語彙 {len(wl)}語: 不一致 {len(diff)} -> {"PASS" if not diff else "FAIL"}')
    for w, a, b in diff[:10]: print(f'   {w}: 漢字={a!r} 純粋={b!r}')
    fail |= bool(diff)

sys.exit(1 if fail else 0)
