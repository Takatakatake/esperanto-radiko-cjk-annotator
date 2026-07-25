# -*- coding: utf-8 -*-
"""漢字忠実度【新指標】: 配信appの漢字描画 vs 漢字マスターの注入エクスポート(全数照合)。

第65Rで新設。従来指標(audit_kanji_vs_master_injection.py)は注入版の ⟦…⟧ を地の文にしていたが、
注入版は**漢字が付く語にしか ⟦⟧ 行を持たない**。よって「マスターが意図的にラテンのまま残す語を、
アプリもラテンで残せているか」という軸を一度も測れていなかった。
注入エクスポート(4列・inline rule適用済・原本行順)を地の文にすると、この第二の軸が可視化される。

注意点(実測で踏んだ罠):
 - エクスポートは辞書本体と同じ h-system(c^=ĉ 等)のキャレット表記を含む。字上符へ正規化してから
   照合しないと該当見出し(c^in/a 等)を丸ごと取りこぼす。
 - 1見出しに複数描画がある語(語釈ゲートで解決)が存在する。appは原理的に弁別できないため、
   いずれかの sense に一致すれば可として別集計する。

使い方:
  python audit_kanji_vs_master_export.py --frozen <凍結マスターdir> --tag r150 [--app <repo>] [--baseline <前回json>]
"""
import json, re, sys, os, argparse
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92)*2 + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)

ap = argparse.ArgumentParser()
ap.add_argument('--frozen', required=True, help='凍結マスターのディレクトリ(SHA固定スナップショット)')
ap.add_argument('--app', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument('--tag', required=True)
ap.add_argument('--baseline', default='', help='比較する前回の *_mismatch.json')
ap.add_argument('--out-dir', default='.')
ap.add_argument('--export-name', default='_漢字割当エクスポート_学習者版_20260723.tsv')
A = ap.parse_args()

L = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
def ok_surface(s):
    return bool(re.fullmatch('[' + L + ']{1,40}', s))

senses = {}   # 表層 -> [(原本行, 描画flat), ...]
for i, ln in enumerate(open(LP(os.path.join(A.frozen, A.export_name)), encoding='utf-8'), 1):
    if ln.startswith('#'): continue
    ps = ln.rstrip('\n').split('\t')
    if len(ps) < 4: continue
    surf, flat = circ(ps[2].strip()), circ(ps[3].strip())
    if not ok_surface(surf): continue
    senses.setdefault(surf, []).append((i, flat))
surfaces = sorted(senses)
multi = {s for s, v in senses.items() if len({f for _, f in v}) > 1}
print(f'エクスポート実在語: {len(surfaces)} (複数描画 {len(multi)})', flush=True)

APP = os.path.join(A.app, 'Esperanto-Kanji-Ruby-JA'); sys.path.insert(0, APP)
import esp_text_replacement_module as M
dd = json.load(open(os.path.join(APP, 'app_data', '置換リスト_漢字.json'), encoding='utf-8'))
GL = dd['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = dd['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
GG = dd['全域替换用のリスト(列表)型配列(replacements_final_list)']
ps_ = M.import_placeholders(os.path.join(APP, 'app_data', 'placeholders_skip.txt'))
pl_ = M.import_placeholders(os.path.join(APP, 'app_data', 'placeholders_localcapture.txt'))
def convert(t):
    return M.orchestrate_comprehensive_esperanto_text_replacement(
        t, ps_, GL, pl_, GG, G2, '汉字替换_大小调整')
RT = re.compile(r'<rt[^>]*>(?:[^<]|<br\s*/?>)*?</rt>'); TAG = re.compile(r'<[^>]+>')
def disp(seg): return TAG.sub('', RT.sub('', seg)).strip()

SEP = '◆'; B = 800
mism, amb_ok = [], 0
for i in range(0, len(surfaces), B):
    ch = surfaces[i:i+B]
    out = convert(' ' + (' ' + SEP + ' ').join(ch) + ' ')
    parts = out.split(SEP)
    if len(parts) != len(ch):
        parts = [convert(' ' + w + ' ') for w in ch]
    for w, seg in zip(ch, parts):
        ad = disp(seg)
        cands = {f for _, f in senses[w]}
        if ad in cands:
            if w in multi: amb_ok += 1
            continue
        prim = senses[w][0][1]
        mism.append({'w': w, 'app': ad, 'master': prim,
                     'alts': sorted(cands - {prim}) if w in multi else []})

hy = un = other = 0
for m in mism:
    if m['app'].replace('-', '') == m['master'].replace('-', ''): hy += 1
    elif not re.search(r'[^' + L + r'\-]', m['app']): un += 1
    else: other += 1
n = len(surfaces)
print(f'不一致 {len(mism)} / {n} ({100*len(mism)/max(n,1):.3f}%)  忠実度 {100*(n-len(mism))/n:.3f}%')
print(f'  内訳: ハイフンのみ={hy} 未割当(ラテン素通し)={un} 値差={other}')
print(f'  複数描画語のうちいずれかに一致(容認)={amb_ok}')

if A.baseline and os.path.exists(LP(A.baseline)):
    prev = {m['w']: m for m in json.load(open(LP(A.baseline), encoding='utf-8'))}
    cur = {m['w']: m for m in mism}
    new = [w for w in cur if w not in prev]
    healed = [w for w in prev if w not in cur]
    chg = [w for w in cur if w in prev and cur[w]['app'] != prev[w]['app']]
    print(f'--- baseline({os.path.basename(A.baseline)})比較 ---')
    print(f'  ★退行(新規不一致) {len(new)} / 解消 {len(healed)} / app値変化 {len(chg)}')
    for w in new[:40]: print(f'    NEW {w}: app={cur[w]["app"]} master={cur[w]["master"]}')
    for w in healed[:40]: print(f'    HEAL {w}: (旧app={prev[w]["app"]} → master一致)')

out_p = os.path.join(A.out_dir, f'{A.tag}_export_mismatch.json')
json.dump(mism, open(LP(out_p), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved:', out_p)
