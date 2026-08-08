# -*- coding: utf-8 -*-
"""第93R: **漢字軌道が既に区別している語義を、ルビ軌道に写す**。DRY既定 / --apply。

■ 何を直すか
  `audit_ruby_vs_kanji_sense_split.py` が検出した「マスターが同綴り語根を別漢字で区別している
  のに、ルビが単一の訳語しか持たない」語根のうち、**訳語の出所が配信内に実在する**ものだけ。

      uri     マスター 尿(8語: albuminurio/anurio/glukozurio…) vs 鸟ᵁᴿ(1語: urio)
              ルビ現状 全部 ウミガラス属/海鸠属/바다오리속  ← ★医学語8つが「海鳥」
      oks     氧(anoksemio/oksonio) vs 牛ᴼ(okso)   ルビ現状 全部 去勢牛/阉牛/거세소
      himen   膜(himenopteroj/himenomicetoj) vs 处女膜(himeno)  ルビ現状 全部 処女膜
      epi     表ᴱ(22語) vs 后ᴱ(epilogo/epipaleolitiko)  ルビ現状 全部 上
      halo    晕(haloo) vs 盐ᴴ(halofito)          ルビ現状 全部 ホール/大厅/홀
      panikl  圆锥(paniklo) vs 脂ᴾ(paniklito)      ルビ現状 全部 皮下脂肪
      afrodit 性ᴬᶠ(hermafrodit…5語) vs 虫ᴬᴰ(afrodito)  ルビ現状 全部 アフロディテ
      goni    源ᴳᴼ(kosmogonio/teogonio…5語) vs 角ᴳ(goniometr…5語)  ルビ現状 全部 角

■ ★語義の出所は「アプリ自身の配信」(発明ゼロ)
  同じキーが 置換リスト_漢字 と 置換リスト_ルビ の両方にあり、エス語根の列が一致するキーは
  387,005 件ある。そこから〔漢字 -> 訳語三つ組〕の対応表(8,894漢字)が配信実績だけで作れる。
  下の GLOSS はその表から**実測で採った**もので、支持数を併記する。

■ ★どのキーがどちらの語義かは「漢字リストを引く」だけで決まる(発明ゼロ)
  漢字軌道は既に正しいので、同じキーの漢字片を見れば語義が確定する。
  推測は一切しない。漢字リストに無いキー・分節が違うキーは**触らない**(fail-closed)。
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
ap.add_argument('--report', default='')
ap.add_argument('--only', default='', help='この語根だけに限定(カンマ区切り)')
A = ap.parse_args()
DRY = not A.apply
FMT = 'HTML格式_Ruby文字_大小调整'
LISTS = ['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)',
         '二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)',
         '全域替换用のリスト(列表)型配列(replacements_final_list)']
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>'); BR = re.compile(r'<br\s*/?>')
SUP = re.compile('[ᴬ-ᵪ⁰-₟ʰ-˿]')          # センチネル(上付き)

# 語根 -> {センチネルを剥がした漢字: (JA, ZH, KO)}
# 値は配信実績から実測。コメントの ×N は対応表での支持数。
GLOSS = {
    'uri':     {'尿':  ('尿', '尿', '소변')},          # ×28 UROLOG/UROGRAFI/URGENER 族(=uro と同じ)
    'oks':     {'氧':  ('酸素', '氧', '산소')},        # ×57 ANOKSI 族
    'himen':   {'膜':  ('膜', '膜', '막')},            # ×27 MEMBRAN 族
    'epi':     {'后':  ('後で', '之后', '후에')},       # ×355 POST 族
    'halo':    {'盐':  ('塩', '盐', '소금')},          # ×349 SAL 族
    'panikl':  {'脂':  ('脂肪', '脂肪', '지방')},       # ×351 ADIP 族
    'afrodit': {'性':  ('性', '性', '성')},            # ×237 SEKS 族
    # ★goni の 源 は候補が2つある(発生×93 GENEZ族 / 起源×63 ORIGIN族)。
    #   漢字が 源 なので字面が直結する 起源 を採る。どちらでも現状の「角」(偽の友)より良い。
    'goni':    {'源':  ('起源', '起源', '기원')},       # ×63 ORIGIN 族
}
if A.only:
    keep = {x.strip() for x in A.only.split(',')}
    GLOSS = {k: v for k, v in GLOSS.items() if k in keep}
LANGS = ('JA', 'ZH', 'KO')
LI = {l: i for i, l in enumerate(LANGS)}

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

# ── 漢字リストを読み、キー -> (エス語根列, 漢字列) を作る ────────────
kanji_of = {}
for lang in LANGS:
    d = json.load(open(LP(os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}',
                                       'app_data', '置換リスト_漢字.json')), encoding='utf-8'))
    per = {}
    for name in LISTS:
        for e in d.get(name, []):
            if not isinstance(e[0], str): continue
            ms = list(RUBY.finditer(e[1]))
            if not ms: continue
            per[e[0].strip()] = ([BR.sub('', TAG.sub('', m.group(2))) for m in ms],
                                 [TAG.sub('', m.group(1)) for m in ms])
    kanji_of[lang] = per
print('漢字キー ' + ' / '.join(f'{l}={len(kanji_of[l]):,}' for l in LANGS))

# ── 計画づくり ────────────────────────────────────────────
plan = {}; segof = {}; stat = collections.Counter(); skipped = collections.Counter()
samples = collections.defaultdict(list)
for lang in LANGS:
    app_dir = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    d = json.load(open(LP(os.path.join(app_dir, 'app_data', '置換リスト_ルビ.json')),
                       encoding='utf-8'))
    helper = load_app_replacement_helper(app_dir)
    cw = json.load(open(LP(os.path.join(app_dir, 'app_data', 'char_widths.json')),
                        encoding='utf-8'))
    per = {}
    for li, name in enumerate(LISTS):
        for idx, e in enumerate(d[name]):
            if not isinstance(e[0], str): continue
            key = e[0].strip()
            cur = parse(e[1])
            bases = [p[0] for p in cur if not isinstance(p, str)]
            if not bases: continue
            lb = [b.lower() for b in bases]
            hits = [i for i, b in enumerate(lb) if b in GLOSS]
            if not hits: continue
            if surface(cur).strip() != key:
                skipped['現行値の表層がキーと違う'] += 1; continue
            kj = kanji_of[lang].get(key)
            if kj is None:
                skipped['漢字リストに同じキーが無い'] += 1; continue
            if [x.lower() for x in kj[0]] != lb:
                skipped['漢字リストと分節が違う'] += 1; continue
            gl = [p[1] for p in cur if not isinstance(p, str)]
            newg = list(gl); changed = False
            for i in hits:
                bare = SUP.sub('', kj[1][i])
                tbl = GLOSS[lb[i]]
                if bare not in tbl:
                    skipped[f'{lb[i]}: 漢字 {bare} は対象外(現状維持)'] += 1; continue
                want = tbl[bare][LI[lang]]
                if newg[i] != want:
                    newg[i] = want; changed = True
            if not changed:
                stat[f'{lang}:既に正しい'] += 1
                segof.setdefault(key, {})[lang] = '/'.join(bases)
                continue
            # 値を組み直す(リテラル片はそのまま・ルビ片だけ差し替える)
            buf = []; gi = 0
            for p in cur:
                if isinstance(p, str): buf.append(p); continue
                buf.append(helper.output_format(p[0], newg[gi], FMT, cw)); gi += 1
            val = ''.join(buf)
            new = parse(val)
            if surface(new) != surface(cur):
                skipped['組み直した表層が不一致'] += 1; continue
            if [p[0] for p in new if not isinstance(p, str)] != bases:
                skipped['ベースが変わった'] += 1; continue
            if [p[1] for p in new if not isinstance(p, str)] != newg:
                skipped['訳語が意図と違う'] += 1; continue
            pad_l = e[1][:len(e[1]) - len(e[1].lstrip())]
            pad_r = e[1][len(e[1].rstrip()):]
            per[(li, idx)] = (e[0], pad_l + val + pad_r)
            segof.setdefault(key, {})[lang] = '/'.join(bases)
            stat[f'{lang}:★是正'] += 1
            root = lb[hits[0]]
            if len(samples[(lang, root)]) < 3:
                def sh(x): return ''.join('«' + p + '»' if isinstance(p, str)
                                          else f'{p[0]}[{p[1]}]' for p in parse(x))
                samples[(lang, root)].append((key, sh(e[1]), sh(pad_l + val + pad_r)))
    plan[lang] = per
    print(f'[{lang}] 是正対象キー {len(per):,}')

# ── 3言語で分節が完全一致することの検証(ユーザーの絶対要件) ────────────
keys = [set(v[0] for v in plan[l].values()) for l in LANGS]
if not (keys[0] == keys[1] == keys[2]):
    only = keys[0] ^ keys[1] | keys[1] ^ keys[2]
    raise SystemExit(f'★3言語で対象キー集合が違う({len(only)}件): 中止 例={sorted(only)[:5]}')
bad = [k for k, m in segof.items() if len(set(m.values())) != 1]
if bad:
    for k in bad[:5]: print('  ', k, segof[k])
    raise SystemExit(f'★分節が3言語で食い違う {len(bad)} 件: 中止')
print(f'3言語の分節一致: ○ ({len(segof):,} キー)')

print('内訳: ' + ' / '.join(f'{k}={v}' for k, v in sorted(stat.items())))
print('\nskip の内訳:')
for k, v in skipped.most_common(12): print(f'   {v:7,}  {k}')
print('\n=== 例 (JA) ===')
for (lang, root), ss in sorted(samples.items()):
    if lang != 'JA': continue
    print(f'\n[{root}]')
    for k, o, n in ss:
        print(f'   {k}\n     現在 {o}\n     以後 {n}')
if A.report:
    json.dump({'stat': dict(stat), 'skipped': dict(skipped),
               'samples': {f'{l}:{r}': v for (l, r), v in samples.items()}},
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
    atomic_file_copy(LP(path), LP(path + '.bak_preR93S'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 値の差替 {n:,} 件(キー数・重複キーは不変)')
print('適用完了')
