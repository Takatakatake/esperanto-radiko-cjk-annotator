# -*- coding: utf-8 -*-
"""第112R: **訳語の語義が日中韓で割れている**キー群の訳語を、出典のある値へ差し替える。
   DRY既定 / --apply。分節(語根の切り方)は1文字も触らない。<rt>の中身だけを置き換える。

■ 第95R(fix_ruby_root_gloss_mixup.py)との違い
  第95Rは「語根1つ = 裁定1つ」だった。第112Rでは**同じ語根の中でキー群ごとに語義が違う**
  ケースを扱う必要がある(実例: sin)。

      sino/sinon/sinoj/sinojn        = sin/o(懐)      … KO 품 が正・JA/ZH が誤
      sinteno/singarda/sindona/...   = si+n(自分+対格) … JA/ZH が正・KO 품 が誤
      sinkron*/sinonim*              = syn-(共)       … 3言語とも正

  そこで**キー群(group)を単位**にし、1語根に複数の独立した群を許す。群同士のキーが
  重ならないことを実行時に検証する(重なれば適用順で結果が変わるため fail-closed)。

■ 安全設計(第95R/96R/98Rで実際に踏んだ罠の再発防止をそのまま継承)
  1. 群は敵対的検証を通ったものだけを --plan で外から渡す。機械的一括変換はしない。
  2. キーもベース(分節)も変えない。<rt> の中身だけを差し替える → 分節は定義上不変。
     それでも実測で「ベース列が変わっていないこと」「表層が変わっていないこと」を検証する。
  3. 現在値ガード(now): 期待した現在値でなければその行は触らない(fail-closed)。
  4. パディング(前後の空白)は元の値のものをそのまま使う。付け足さない(第86R/95Rの二重付加)。
  5. ルビのサイズクラスは helper.output_format で再計算する(訳語の幅が変わるため)。
  6. キー限定(keys)・リスト限定(lists)は第96R/98Rと同じ意味。
     GL(局部)がCSVを忠実に写している場合は lists=["GG"] で GL/CSV を保全する。
  7. keys に書いたキーが1つでもデータに存在しなければ中止(綴り誤りの検出)。
  8. 触った全キーについて、3言語の**現在の**分節が一致することを最後に実測する。
"""
import json, os, re, sys, argparse, collections
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from atomic_json import atomic_file_copy, atomic_json_dump
from gen_replacement import load_app_replacement_helper

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--plan', required=True, help='群の配列JSON(敵対的検証を通過したものだけ)')
ap.add_argument('--report', default='')
A = ap.parse_args()
DRY = not A.apply
FMT = 'HTML格式_Ruby文字_大小调整'
LISTS = ['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)',
         '二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)',
         '全域替换用のリスト(列表)型配列(replacements_final_list)']
LTAG = ('GL', 'G2', 'GG')
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
BR = re.compile(r'<br\s*/?>')
LANGS = ('JA', 'ZH', 'KO')

GROUPS = json.load(open(LP(A.plan), encoding='utf-8'))
if not GROUPS:
    raise SystemExit('★plan が空')
for g in GROUPS:
    g['root'] = g['root'].lower()
    g['keys'] = set(g['keys']) if g.get('keys') else None
    g['lists'] = set(g['lists']) if g.get('lists') else None
# 同一語根の群同士でキーが重ならないこと(全キー指定の群は1語根1つまで)
by_root = collections.defaultdict(list)
for g in GROUPS: by_root[g['root']].append(g)
for r, gs in by_root.items():
    wide = [g for g in gs if g['keys'] is None]
    if len(gs) > 1 and wide:
        raise SystemExit(f'★{r}: 複数群があるのに keys 未指定の群がある(全キー群は排他)')
    seen = set()
    for g in gs:
        if g['keys'] is None: continue
        dup = seen & g['keys']
        if dup:
            raise SystemExit(f'★{r}: 群のキーが重複 {sorted(dup)[:5]}')
        seen |= g['keys']
print(f'群 {len(GROUPS)} / 語根 {len(by_root)}')

def parse(v):
    out, pos = [], 0
    for m in RUBY.finditer(v):
        if m.start() > pos:
            t = TAG.sub('', v[pos:m.start()])
            if t: out.append(t)
        out.append((TAG.sub('', m.group(1)), BR.sub('', TAG.sub('', m.group(2))))); pos = m.end()
    if pos < len(v):
        t = TAG.sub('', v[pos:])
        if t: out.append(t)
    return out
def surface(ps): return ''.join(p if isinstance(p, str) else p[0] for p in ps)

plan = {}; segof = {}; stat = collections.Counter(); skipped = collections.Counter()
samples = collections.defaultdict(list)
seen_keys = collections.defaultdict(set)   # group id -> 実在を確認できたキー
for lang in LANGS:
    app_dir = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    d = json.load(open(LP(os.path.join(app_dir, 'app_data', '置換リスト_ルビ.json')), encoding='utf-8'))
    helper = load_app_replacement_helper(app_dir)
    cw = json.load(open(LP(os.path.join(app_dir, 'app_data', 'char_widths.json')), encoding='utf-8'))
    per = {}
    for li, name in enumerate(LISTS):
        for idx, e in enumerate(d[name]):
            if not isinstance(e[0], str): continue
            cur = parse(e[1])
            bases = [p[0] for p in cur if not isinstance(p, str)]
            if not bases: continue
            lb = [b.lower() for b in bases]
            k = e[0].strip()
            # この行に効きうる群を集める
            acts = []
            for i, b in enumerate(lb):
                for g in by_root.get(b, ()):
                    if g['keys'] is not None and k not in g['keys']: continue
                    acts.append((i, g))
            if not acts: continue
            for _, g in acts: seen_keys[g['id']].add(k)
            if surface(cur).strip() != k:
                skipped['現行値の表層がキーと違う'] += 1; continue
            gl = [p[1] for p in cur if not isinstance(p, str)]
            newg = list(gl); changed = False
            for i, g in acts:
                spec = g.get(lang) or {}
                want = spec.get('next')
                if not want:
                    skipped[f"{g['id']}: {lang} は対象外(裁定で据置)"] += 1; continue
                if g['lists'] is not None and LTAG[li] not in g['lists']:
                    skipped[f"{g['id']}: リスト限定の対象外({LTAG[li]})"] += 1; continue
                now = spec.get('now')
                if now is not None:
                    allowed = now if isinstance(now, list) else [now]
                    if newg[i] not in allowed:
                        skipped[f"{g['id']}: {lang} の現在値がガードと違う"] += 1; continue
                if newg[i] == want: continue
                newg[i] = want; changed = True
            if not changed:
                stat[f'{lang}:既に正しい/対象外'] += 1; continue
            buf = []; gi = 0
            for p in cur:
                if isinstance(p, str): buf.append(p); continue
                buf.append(helper.output_format(p[0], newg[gi], FMT, cw)); gi += 1
            val = ''.join(buf)
            new = parse(val)
            if [p[0] for p in new if not isinstance(p, str)] != bases:
                skipped['★ベースが変わった'] += 1; continue
            if surface(new) != surface(cur):
                skipped['★表層が変わった'] += 1; continue
            if [p[1] for p in new if not isinstance(p, str)] != newg:
                skipped['★訳語が意図と違う'] += 1; continue
            if (len(val) - len(val.lstrip())) != (len(e[1]) - len(e[1].lstrip())) or \
               (len(val) - len(val.rstrip())) != (len(e[1]) - len(e[1].rstrip())):
                skipped['★パディングが変わった'] += 1; continue
            per[(li, idx)] = (e[0], val)
            segof.setdefault(e[0], {})[lang] = '/'.join(bases)
            stat[f'{lang}:★是正'] += 1
            gid = acts[0][1]['id']
            if len(samples[(lang, gid)]) < 3:
                def sh(x): return ''.join('«' + p + '»' if isinstance(p, str)
                                          else f'{p[0]}[{p[1]}]' for p in parse(x))
                samples[(lang, gid)].append((k, sh(e[1]), sh(val)))
    plan[lang] = per
    print(f'[{lang}] 是正対象キー {len(per):,}')
    del d

# ── 指定キーの実在検証(fail-closed) ──────────────────────────
missing = {}
for g in GROUPS:
    if g['keys'] is None: continue
    lost = g['keys'] - seen_keys[g['id']]
    if lost: missing[g['id']] = sorted(lost)
if missing:
    for gid, ks in list(missing.items())[:5]:
        print(f'  ★{gid}: データに存在しないキー {len(ks)} 件 例{ks[:6]}')
    raise SystemExit('★keys に実在しないキーがある: 中止')

# ── 3言語の分節一致(触ったキー全数) ────────────────────────
keys = [set(v[0] for v in plan[l].values()) for l in LANGS]
union = keys[0] | keys[1] | keys[2]
print(f'触ったキー(和集合) {len(union):,} / ' + ' '.join(f'{l}={len(keys[i]):,}' for i, l in enumerate(LANGS)))
cur = {}
for lang in LANGS:
    d = json.load(open(LP(os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}',
                                       'app_data', '置換リスト_ルビ.json')), encoding='utf-8'))
    m = {}
    for name in LISTS:
        for e in d[name]:
            if isinstance(e[0], str) and e[0] in union:
                m.setdefault(e[0], '/'.join(p[0] for p in parse(e[1]) if not isinstance(p, str)))
    cur[lang] = m
    del d
bad = [k for k in union if len({cur[l].get(k) for l in LANGS}) != 1 or cur['JA'].get(k) is None]
if bad:
    for k in sorted(bad)[:5]:
        print('   ', repr(k), {l: cur[l].get(k) for l in LANGS})
    raise SystemExit(f'★分節が3言語で食い違うキーがある {len(bad)} 件: 中止')
print(f'3言語の分節一致(触ったキー全数): ○ ({len(union):,} キー)')
bad2 = [k for k, m in segof.items() if len(set(m.values())) != 1]
if bad2:
    raise SystemExit(f'★同一キーの分節が言語間で食い違う {len(bad2)} 件: 中止')
print('内訳: ' + ' / '.join(f'{k}={v}' for k, v in sorted(stat.items())))
if skipped:
    print('skip: ' + ' / '.join(f'{k}={v}' for k, v in skipped.most_common(10)))
print('\n=== 例 ===')
for (lang, gid), ss in sorted(samples.items()):
    print(f'\n[{gid}] {lang}')
    for k, o, n in ss:
        print(f'   {k}\n     現在 {o}\n     以後 {n}')
if A.report:
    def ser(g):
        return {k: (sorted(v) if isinstance(v, set) else v) for k, v in g.items()}
    json.dump({'stat': dict(stat), 'skipped': dict(skipped),
               'groups': [ser(g) for g in GROUPS],
               'samples': {f'{l}:{g}': v for (l, g), v in samples.items()}},
              open(LP(A.report), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if DRY:
    print('\n(DRY-RUN: --apply で書込)'); sys.exit(0)
for lang in LANGS:
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_ルビ.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    n = 0
    for (li, idx), (k, v) in plan[lang].items():
        e = d[LISTS[li]][idx]
        if e[0] != k: raise SystemExit(f'★添字がずれている {lang} {idx} {e[0]!r} != {k!r}')
        if e[1] == v: continue
        d[LISTS[li]][idx] = [e[0], v] + list(e[2:])
        n += 1
    atomic_file_copy(LP(path), LP(path + '.bak_preR112'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 値の差替 {n:,} 件(キー数・重複キー・分節は不変)')
print('適用完了')
