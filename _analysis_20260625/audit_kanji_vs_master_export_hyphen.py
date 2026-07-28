# -*- coding: utf-8 -*-
"""第85R新設: **ハイフン入り見出し**の漢字忠実度を測る(既存の2軸の死角)。

■ なぜ要るか
  既存の忠実度ゲートは2本とも、ハイフン入り表層を**構造的に見ていない**。
    audit_kanji_vs_master_export.py    : ok_surface=[A-Za-zĉĝĥĵŝŭ]{1,40} に完全一致
    audit_kanji_vs_master_injection.py : 同様(その「ハイフンのみ」分類は
                                          H-弹o vs H弹o のような**挿入**の話で別物)
  そのため `oto-rino-laringologo` が `待o-rino-laringo诱ᴸo`(待=受動将然の-ot-、
  诱=誘惑するlog/i)と描画されていても、どちらのゲートも赤くならなかった。

■ 測り方
  export(学習者版)の4列から、表層がハイフンを含むものだけを取り、
  アプリの漢字表層と f3 を突き合わせる。複数描画のいずれかに一致すれば可。
  固有名詞クラスは別集計(ユーザー裁定待ちのため是正対象外)。

  usage: audit_kanji_vs_master_export_hyphen.py --frozen <凍結ディレクトリ>
                                                [--tag T] [--baseline J] [--out-dir D]
"""
import json, os, re, sys, argparse, collections, hashlib
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument('--frozen', required=True)
ap.add_argument('--app', default='Esperanto-Kanji-Ruby-JA')
ap.add_argument('--tag', default='')
ap.add_argument('--baseline', default='')
ap.add_argument('--out-dir', default='')
ap.add_argument('--export-name', default='_漢字割当エクスポート_学習者版_20260723.tsv')
A = ap.parse_args()
X = {'c^':'ĉ','g^':'ĝ','h^':'ĥ','j^':'ĵ','s^':'ŝ','u^':'ŭ',
     'C^':'Ĉ','G^':'Ĝ','H^':'Ĥ','J^':'Ĵ','S^':'Ŝ','U^':'Ŭ'}
def circ(s):
    for a, b in X.items(): s = s.replace(a, b)
    return s
TAG = re.compile(r'<[^>]+>')
L_ = "A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ"
HYPH = re.compile('[' + L_ + r'0-9,\.]+(?:-[' + L_ + r'0-9,\.]+)+')

exp_path = os.path.join(A.frozen, A.export_name)
raw = open(LP(exp_path), 'rb').read()
print(f'export: {os.path.basename(exp_path)} sha256={hashlib.sha256(raw).hexdigest()[:16]}')
EXP = collections.defaultdict(list)
for ln in raw.decode('utf-8', 'replace').splitlines():
    if ln.startswith('#'): continue
    f = ln.rstrip('\n').split('\t')
    if len(f) < 4: continue
    surf = circ(f[2].strip())
    if not HYPH.fullmatch(surf): continue
    EXP[surf].append((circ(f[0].strip()), circ(f[1].strip()), surf, circ(f[3].strip())))
print(f'ハイフン入り見出し {len(EXP)}')

APP = os.path.join(ROOT, A.app)
sys.path.insert(0, APP)
import esp_text_replacement_module as M
d = json.load(open(LP(os.path.join(APP, 'app_data', '置換リスト_漢字.json')), encoding='utf-8'))
GL = d['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)']
G2 = d['二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)']
GG = d['全域替换用のリスト(列表)型配列(replacements_final_list)']
ps = M.import_placeholders(os.path.join(APP, 'app_data', 'placeholders_skip.txt'))
pl = M.import_placeholders(os.path.join(APP, 'app_data', 'placeholders_localcapture.txt'))
FMT = 'HTML格式_Ruby文字_大小调整_汉字替换'
def conv(t):
    return M.orchestrate_comprehensive_esperanto_text_replacement(t, ps, GL, pl, GG, G2, FMT)
def ksurf(h):
    return TAG.sub('', re.sub(r'<rt[^>]*>.*?</rt>', '', h, flags=re.S)).strip()

ws = sorted(EXP); SEP = '◆'; B = 400
cur = {}
for i in range(0, len(ws), B):
    ch = ws[i:i+B]
    o = conv(' ' + (' ' + SEP + ' ').join(ch) + ' ')
    parts = o.split(SEP)
    if len(parts) != len(ch): parts = [conv(' ' + w + ' ') for w in ch]
    for w, s in zip(ch, parts): cur[w] = ksurf(s)

def is_proper(w, f0):
    if w[:1].isupper(): return True
    return any(p[:1].isupper() for p in f0.split('/') if p)

ok = 0; rows = []
for w in ws:
    if cur[w] in {s[3] for s in EXP[w]}: ok += 1; continue
    f0, f1, f2, f3 = EXP[w][0]
    rows.append({'w': w, 'app': cur[w], 'master': f3, 'f0': f0, 'f1': f1,
                 'cls': '固有' if is_proper(w, f0) else '普通'})
n_p = sum(1 for r in rows if r['cls'] == '固有')
n_n = len(rows) - n_p
print(f'一致 {ok} / {len(ws)} ({ok / len(ws) * 100:.3f}%)   '
      f'不一致 {len(rows)} (固有名詞 {n_p} / ★普通の語 {n_n})')
print('\n=== 普通の語 ===')
for r in rows:
    if r['cls'] != '普通': continue
    lat = '  ※マスターは全ラテン' if r['f0'] == r['f1'] else ''
    print(f"  {r['w']:<26} app={r['app']:<24} master={r['master']}{lat}")

if A.baseline and os.path.exists(LP(A.baseline)):
    base = {r['w']: r for r in json.load(open(LP(A.baseline), encoding='utf-8'))}
    now = {r['w']: r for r in rows}
    new = sorted(set(now) - set(base)); fixed = sorted(set(base) - set(now))
    chg = [w for w in set(now) & set(base) if now[w]['app'] != base[w]['app']]
    print(f'\n--- baseline({os.path.basename(A.baseline)})比較 ---')
    print(f'  ★退行(新規不一致) {len(new)} / 解消 {len(fixed)} / app値変化 {len(chg)}')
    for w in new[:20]: print(f'    退行 {w}: {base.get(w, {}).get("app", "(一致だった)")} -> {now[w]["app"]}')
    for w in fixed[:20]: print(f'    解消 {w}: {base[w]["app"]} -> {now.get(w, {}).get("app", cur.get(w))}')

if A.tag and A.out_dir:
    out = os.path.join(A.out_dir, f'{A.tag}_export_hyphen_mismatch.json')
    json.dump(rows, open(LP(out), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'saved: {out}')
