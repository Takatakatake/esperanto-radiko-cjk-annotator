# -*- coding: utf-8 -*-
"""ガイド§3.4(同一語根の注釈統一)照合: 統一13ケースの残存揺れ + 全内容語根の実質的揺れ検出。"""
import os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
CORP = r"D:\GoogleDrive202510\マイドライブ\20_エスペラント・語学\エスペラントの漢字化プロジェクト総結集20260630\語根分解、注釈ルビ振り、漢字化アプリ徹底ブラッシュアップ20260630\_project_root_misc\京大エス研html文書＿Github"
PFX = chr(92) + chr(92) + chr(63) + chr(92)
def LP(p): return PFX + os.path.abspath(p)

# §3.4 統一すべき13ケース: root -> (統一先, 許容集合)
UNIFY = {
    'eg': ('強大', set()), 'eĉ': ('(~)さえ', set()), 'apart': ('別々の', set()),
    'san': ('健康な', set()), 'ĝeneral': ('全般の', set()), 'urĝ': ('さし迫る', set()),
    'aprior': ('先天的な', {'先験的な'}), 'aposterior': ('後天的', {'後験的な'}),
    'do': ('それゆえ', set()), 'mekanism': ('機構', set()), 'am': ('愛する', set()),
    'demokrat': ('民主', set()), 'anim': ('魂', set()),
}
# §3.4 正当な多義(統一しない) + §7既検査の機能語は除外
LEGIT_POLY = {'en','kun','ĉar','radio','sek','kultur','kod','ĉiel','kamp','orden','kript',
              'objekt','organ','model','art','versi','zorg','sign','konvenci','lanĉ','vic'}

dist = collections.defaultdict(collections.Counter)
samp = {}
for r, _, fs in os.walk(CORP):
    if os.sep + '.git' in r: continue
    for f in fs:
        if not f.endswith('.html') or f.endswith(('_ZH.html', '_KO.html')): continue
        h = open(LP(os.path.join(r, f)), encoding='utf-8', errors='ignore').read()
        for m in re.finditer(r'<ruby>([A-Za-zĉĝĥĵŝŭĈĜĤĴŜŬ]{2,})<rt[^>]*>((?:[^<]|<br\s*/?>)*?)</rt></ruby>', h):
            root = m.group(1).lower()
            g = re.sub(r'<br\s*/?>|\s', '', m.group(2))
            dist[root][g] += 1
            samp.setdefault((root, g), f[:26])

print("=== §3.4 統一13ケースの残存揺れ ===")
n_viol = 0
for root, (target, allowed) in UNIFY.items():
    for g, c in dist.get(root, {}).items():
        if g == target or g in allowed or g.startswith('['): continue
        n_viol += 1
        print(f"  {root:12s} 統一先='{target}' 残存='{g}' ×{c} [{samp[(root,g)]}]")
if n_viol == 0: print("  なし(13ケース全て統一済み)")

print("\n=== 全内容語根の実質的揺れ(頻度20+・2変種以上・多義/固有名除外) ===")
def norm(g):
    return re.sub(r'[;；,、。()（）~〜・\-]', '', g)
found = 0
for root, gc in sorted(dist.items(), key=lambda x: -sum(x[1].values())):
    if root in LEGIT_POLY or root in UNIFY: continue
    total = sum(gc.values())
    if total < 20: continue
    variants = [(g, c) for g, c in gc.items() if not g.startswith('[')]
    # 正規化して実質異なる変種
    normed = collections.Counter()
    rep = {}
    for g, c in variants:
        k = norm(g)
        normed[k] += c
        if k not in rep or c > gc[rep[k]]: rep[k] = g
    real = [(rep[k], c) for k, c in normed.items() if c >= 2]
    if len(real) >= 2:
        # 最頻が90%以上なら少数派のみ表示対象
        real.sort(key=lambda x: -x[1])
        if real[1][1] / total >= 0.02 or real[1][1] >= 3:
            found += 1
            vs = ' | '.join(f"'{g}'×{c}" for g, c in real[:4])
            print(f"  {root:14s} ({total:4d}回): {vs}"[:120])
            if found >= 30: break
print(f"\n表示: {found}(上限30)")
