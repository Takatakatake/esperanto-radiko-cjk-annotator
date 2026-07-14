# -*- coding: utf-8 -*-
"""MONITOR-ONLY高速版（正式gateではない）。

固定snapshot・全行accounting・安定入力検証を持たないため、正式証明には必ず
``audit_master_3lang_full_snapshot.py`` を使う。このスクリプトは明示的な
``--monitor-only`` 指定時だけ動かす。
"""
import os, re, sys, json
sys.stdout.reconfigure(encoding='utf-8')
if '--monitor-only' not in sys.argv:
    raise SystemExit(
        'monitor-only audit: pass --monitor-only explicitly; '
        'use audit_master_3lang_full_snapshot.py for the formal gate'
    )
ROOT = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630"
BASE = ROOT + r"\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630"
GOLD = ROOT + r"\エスペラント辞書徹底語根分解_20260630\世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)
RTP = re.compile(r'<ruby>([^<]+)<rt[^>]*>(?:(?:[^<]|<br\s*/?>)*?)</rt></ruby>')
L = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ','C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s

words = []
for ln in open(LP(GOLD), encoding='utf-8'):
    w = ln.split(':', 1)[0].strip()
    if not w or w.startswith('#'): continue
    cw = circ(w).replace('/', '').replace('-', '')
    if ' ' in cw or '!' in cw or '.' in cw: continue
    if re.fullmatch('[' + L + ']{3,30}', cw):
        words.append(cw)
words = sorted(set(words))
print(f"マスター実在語(3字以上): {len(words)}", flush=True)

SEP = '◆'
def load_app(Lg):
    APP = BASE + '\\' + f'Esperanto-Kanji-Ruby-{Lg}'; DATA = APP + r"\app_data"
    sys.path.insert(0, APP)
    import importlib, esp_text_replacement_module as M; importlib.reload(M)
    dd = json.load(open(LP(DATA + r"\置換リスト_ルビ.json"), encoding="utf-8"))
    GL = dd["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]
    G2 = dd["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
    GG = dd["全域替换用のリスト(列表)型配列(replacements_final_list)"]
    ps = M.import_placeholders(DATA + r"\placeholders_skip.txt"); pl = M.import_placeholders(DATA + r"\placeholders_localcapture.txt")
    def convert(text):
        return M.orchestrate_comprehensive_esperanto_text_replacement(text, ps, GL, pl, GG, G2, "HTML格式_Ruby文字_大小调整")
    return convert

def seg_to_decomp(seg):
    toks = []; pos = 0
    for m in RTP.finditer(seg):
        for ch in re.findall('[' + L + "']+", re.sub(r'<[^>]+>', '', seg[pos:m.start()])): toks.append(ch)
        toks.append(m.group(1)); pos = m.end()
    for ch in re.findall('[' + L + "']+", re.sub(r'<[^>]+>', '', seg[pos:])): toks.append(ch)
    return '/'.join(t.lower() for t in toks)

convs = {Lg: load_app(Lg) for Lg in ('JA', 'ZH', 'KO')}
B = 500
mism = []
for i in range(0, len(words), B):
    chunk = words[i:i + B]
    text = (' ' + SEP + ' ').join(chunk)
    text = ' ' + text + ' '
    decs = {}
    ok = True
    for Lg, cv in convs.items():
        out = cv(text)
        parts = out.split(SEP)
        if len(parts) != len(chunk):
            ok = False; break
        decs[Lg] = [seg_to_decomp(p) for p in parts]
    if not ok:
        # フォールバック: このチャンクだけ単語ごと
        decs = {Lg: [seg_to_decomp(cv(' ' + w + ' ')) for w in chunk] for Lg, cv in convs.items()}
    for j, w in enumerate(chunk):
        a, b, c = decs['JA'][j], decs['ZH'][j], decs['KO'][j]
        if not (a == b == c):
            mism.append({'w': w, 'JA': a, 'ZH': b, 'KO': c})
    if (i // B) % 20 == 19:
        print(f"  ...{min(i+B,len(words))}/{len(words)} 不一致累計 {len(mism)}", flush=True)
print(f"\n=== 最終: マスター全語 {len(words)} の3言語分解不一致: {len(mism)} ({100*len(mism)/max(len(words),1):.3f}%) ===")
for x in mism[:40]:
    print(f"  {x['w']:20s} JA={x['JA']:22s} ZH={x['ZH']:22s} KO={x['KO']}")
json.dump(mism, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'master_3lang_mismatch.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if mism:
    raise SystemExit(1)
