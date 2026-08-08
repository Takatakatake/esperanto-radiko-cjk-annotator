# -*- coding: utf-8 -*-
"""漢字忠実度【旧指標】: 配信appの漢字描画 vs 漢字注入版の ⟦…⟧(全数照合)。

過去ラウンド(411→266→253 …)と直接比較できる従来指標。地の文は注入版(学習者版)の
`見出し⟦漢字⟧` 行の実在語(同一表層は先勝ち)。

※ 本指標は「マスターが漢字を与える語」しか地の文に載らない。マスターが意図的にラテンで
   残す語をappもラテンで残せているかは測れないため、必ず audit_kanji_vs_master_export.py と
   併用すること(第65Rの教訓)。

使い方:
  python audit_kanji_vs_master_injection.py --frozen <凍結マスターdir> --tag r150 [--app <repo>] [--baseline <前回json>]
"""
import json, re, sys, os, argparse
sys.stdout.reconfigure(encoding='utf-8')
PFX = chr(92)*2 + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)

ap = argparse.ArgumentParser()
ap.add_argument('--frozen', required=True)
ap.add_argument('--app', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument('--tag', required=True)
ap.add_argument('--baseline', default='')
ap.add_argument('--out-dir', default='.')
ap.add_argument('--injection-name', default='漢字注入_学習者版_20260620.txt')
A = ap.parse_args()

X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
L = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
seen = {}
for ln in open(LP(os.path.join(A.frozen, A.injection_name)), encoding='utf-8'):
    head = ln.split(':', 1)[0]
    if '⟦' not in head: continue
    latin, kj = head.split('⟦', 1); kj = kj.split('⟧', 1)[0]
    surf = circ(latin).replace('/', '').replace('-', '')
    if ' ' in surf or '!' in surf or '.' in surf: continue
    if not re.fullmatch('[' + L + ']{1,40}', surf): continue
    if surf not in seen: seen[surf] = circ(kj).replace('/', '').replace('-', '')
surfaces = sorted(seen)
print(f'注入版⟦⟧実在語: {len(surfaces)}', flush=True)

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
mism = []
for i in range(0, len(surfaces), B):
    ch = surfaces[i:i+B]
    out = convert(' ' + (' ' + SEP + ' ').join(ch) + ' ')
    parts = out.split(SEP)
    if len(parts) != len(ch):
        parts = [convert(' ' + w + ' ') for w in ch]
    for w, seg in zip(ch, parts):
        ad = disp(seg)
        if ad != seen[w]: mism.append({'w': w, 'app': ad, 'master': seen[w]})
hy = un = other = 0
for m in mism:
    if m['app'].replace('-', '') == m['master'].replace('-', ''): hy += 1
    elif not re.search(r'[^' + L + r'\-]', m['app']): un += 1
    else: other += 1
n = len(surfaces)
print(f'不一致 {len(mism)} / {n} ({100*len(mism)/max(n,1):.3f}%)  忠実度 {100*(n-len(mism))/n:.3f}%')
print(f'  内訳: ハイフンのみ={hy} 未割当(ラテン素通し)={un} 値差={other}')
if A.baseline and os.path.exists(LP(A.baseline)):
    prev = {m['w']: m for m in json.load(open(LP(A.baseline), encoding='utf-8'))}
    cur = {m['w']: m for m in mism}
    new = [w for w in cur if w not in prev]
    healed = [w for w in prev if w not in cur]
    print(f'--- baseline比較 --- ★退行(新規不一致) {len(new)} / 解消 {len(healed)}')
    for w in new[:40]: print(f'    NEW {w}: app={cur[w]["app"]} master={cur[w]["master"]}')
    for w in healed[:40]: print(f'    HEAL {w}: 旧app={prev[w]["app"]} → master({prev[w]["master"]})一致')
out_p = os.path.join(A.out_dir, f'{A.tag}_injection_mismatch.json')
json.dump(mism, open(LP(out_p), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('saved:', out_p)
