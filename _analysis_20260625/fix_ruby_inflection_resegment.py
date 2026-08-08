# -*- coding: utf-8 -*-
"""第114R: 語尾変化形だけが**語幹を切られて**別語根に化けているキーを、
   アプリ自身の基本形キーの分節・訳語に揃え直す。DRY既定 / --apply。

■ 何が壊れているか(第114Rの新レンズで発見)
  基本形キーは語幹を一体で正しく描いているのに、語尾変化形だけが短い別語根に食われる。

      alteo   -> alte[タチアオイ]o   ✓        alteon  -> alt[高い]«eon»      ✗
      ocelo   -> ocel[単眼]o        ✓        ocelon  -> «o»cel[目的]«on»    ✗

  ★マスターも漢字軌道も alte/o→立葵/o, ocel/o→单眼/o と一体で扱っており、
    ルビ軌道の語尾変化形だけが取り残されている(第76R/77Rで漢字軌道に見つけた型の
    ルビ版)。既存3ゲートの死角: 62kゲートは「ルビが1つでもあれば注釈あり」と数えるため、
    語頭が裸になっても検出されない。

■ 安全設計
  1. 対象は --plan で外から与えた語族だけ。機械的一括変換はしない。
  2. **訳語は各言語のアプリ自身の基本形キーから取る**(発明ゼロ)。
     3言語のどれかで基本形キーが見つからなければその言語は触らない(fail-closed)。
  3. 現在値ガード: 期待した「壊れている先頭ベース」でなければ触らない。
  4. 表層(=見える文字列)は1文字も変えない。前後のパディングは元のまま。
  5. 生成後に検証: 表層一致 / 分節が[語幹]の1片 / 訳語が意図どおり / パディング不変。
  6. 触った全キーで3言語の分節が一致することを最後に実測する。
  7. 同じキーがGGに複数エントリある(パディング有無の2系統)ため、**全エントリ**を直す。
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
ap.add_argument('--plan', required=True)
ap.add_argument('--report', default='')
A = ap.parse_args()
DRY = not A.apply
FMT = 'HTML格式_Ruby文字_大小调整'
LISTS = ['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)',
         '二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)',
         '全域替换用のリスト(列表)型配列(replacements_final_list)']
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>'); BR = re.compile(r'<br\s*/?>')
LANGS = ('JA', 'ZH', 'KO')

PLAN = json.load(open(LP(A.plan), encoding='utf-8'))
if not PLAN:
    raise SystemExit('★plan が空')
print('語族 ' + ', '.join(f"{g['stem']}({len(g['forms'])}形)" for g in PLAN))

def parse(v):
    out, pos = [], 0
    for m in RUBY.finditer(v):
        if m.start() > pos:
            t = TAG.sub('', v[pos:m.start()])
            if t: out.append(('lit', t))
        out.append(('ruby', TAG.sub('', m.group(1)), BR.sub('', TAG.sub('', m.group(2)))))
        pos = m.end()
    if pos < len(v):
        t = TAG.sub('', v[pos:])
        if t: out.append(('lit', t))
    return out
def surface(ps):
    return ''.join(p[1] for p in ps)

def case_of(word, stem):
    """キーの大小に合わせて語幹を整える(ALTEON->ALTE / Alteon->Alte / alteon->alte)"""
    return word[:len(stem)]

plan_out = {}; stat = collections.Counter(); skipped = collections.Counter()
samples = collections.defaultdict(list); segof = {}
for lang in LANGS:
    app_dir = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    d = json.load(open(LP(os.path.join(app_dir, 'app_data', '置換リスト_ルビ.json')), encoding='utf-8'))
    helper = load_app_replacement_helper(app_dir)
    cw = json.load(open(LP(os.path.join(app_dir, 'app_data', 'char_widths.json')), encoding='utf-8'))
    # 1) 各語族の訳語を、その言語の基本形キーから取得(発明ゼロ)
    gloss = {}
    for g in PLAN:
        want = g['gloss_from'].lower()
        for name in LISTS:
            for e in d[name]:
                if not isinstance(e[0], str) or e[0].strip().lower() != want: continue
                ps = parse(e[1])
                rb = [p for p in ps if p[0] == 'ruby']
                if len(rb) == 1 and rb[0][1].lower() == g['stem'].lower():
                    gloss[g['stem']] = rb[0][2]; break
            if g['stem'] in gloss: break
        if g['stem'] not in gloss:
            print(f"  ★{lang}: {g['stem']} の基本形キー {g['gloss_from']!r} から訳語を取得できない -> この言語は対象外")
    # 2) 対象キーを直す
    per = {}
    targets = {}
    for g in PLAN:
        if g['stem'] not in gloss: continue
        for f in g['forms']:
            for var in (f.lower(), f.capitalize(), f.upper()):
                targets[var] = (g, gloss[g['stem']])
    for li, name in enumerate(LISTS):
        for idx, e in enumerate(d[name]):
            if not isinstance(e[0], str): continue
            k = e[0].strip()
            tg = targets.get(k)
            if tg is None: continue
            g, gl = tg
            ps = parse(e[1])
            if surface(ps).strip() != k:
                skipped['現行値の表層がキーと違う'] += 1; continue
            rb = [p for p in ps if p[0] == 'ruby']
            if not rb: skipped['ルビ無し'] += 1; continue
            if rb[0][1].lower() not in {b.lower() for b in g['broken_bases']}:
                skipped[f"{g['stem']}: 先頭ベースがガードと違う({rb[0][1]})"] += 1; continue
            stem_c = case_of(k, g['stem'])
            tail = k[len(stem_c):]
            raw = e[1]
            pad_l = raw[:len(raw) - len(raw.lstrip())]
            pad_r = raw[len(raw.rstrip()):]
            val = pad_l + helper.output_format(stem_c, gl, FMT, cw) + tail + pad_r
            new = parse(val)
            if surface(new) != surface(ps):
                skipped['★表層が変わった'] += 1; continue
            nrb = [p for p in new if p[0] == 'ruby']
            if len(nrb) != 1 or nrb[0][1] != stem_c or nrb[0][2] != gl:
                skipped['★生成結果が意図と違う'] += 1; continue
            if (len(val) - len(val.lstrip())) != len(pad_l) or \
               (len(val) - len(val.rstrip())) != len(pad_r):
                skipped['★パディングが変わった'] += 1; continue
            per[(li, idx)] = (e[0], val)
            segof.setdefault(e[0], {})[lang] = stem_c
            stat[f'{lang}:★是正'] += 1
            if len(samples[(lang, g['stem'])]) < 3:
                def sh(x): return ''.join(
                    ('«' + p[1] + '»') if p[0] == 'lit' else f'{p[1]}[{p[2]}]' for p in parse(x))
                samples[(lang, g['stem'])].append((k, sh(e[1]), sh(val)))
    plan_out[lang] = per
    print(f'[{lang}] 是正対象エントリ {len(per):,}')
    del d

keys = [set(v[0].strip() for v in plan_out[l].values()) for l in LANGS]
union = keys[0] | keys[1] | keys[2]
print(f'触ったキー(和集合) {len(union):,} / ' + ' '.join(f'{l}={len(keys[i]):,}' for i, l in enumerate(LANGS)))
if not (keys[0] == keys[1] == keys[2]):
    raise SystemExit('★3言語で対象キー集合が一致しない: 中止')
print('内訳: ' + ' / '.join(f'{k}={v}' for k, v in sorted(stat.items())))
if skipped:
    print('skip: ' + ' / '.join(f'{k}={v}' for k, v in skipped.most_common(8)))
print('\n=== 例 ===')
for (lang, st), ss in sorted(samples.items()):
    print(f'\n[{st}] {lang}')
    for k, o, n in ss:
        print(f'   {k}\n     現在 {o}\n     以後 {n}')
if A.report:
    json.dump({'stat': dict(stat), 'skipped': dict(skipped), 'plan': PLAN,
               'samples': {f'{l}:{s}': v for (l, s), v in samples.items()}},
              open(LP(A.report), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
if DRY:
    print('\n(DRY-RUN: --apply で書込)'); sys.exit(0)
for lang in LANGS:
    path = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}', 'app_data', '置換リスト_ルビ.json')
    d = json.load(open(LP(path), encoding='utf-8'))
    n = 0
    for (li, idx), (k, v) in plan_out[lang].items():
        e = d[LISTS[li]][idx]
        if e[0] != k: raise SystemExit(f'★添字がずれている {lang} {idx} {e[0]!r} != {k!r}')
        if e[1] == v: continue
        d[LISTS[li]][idx] = [e[0], v] + list(e[2:])
        n += 1
    atomic_file_copy(LP(path), LP(path + '.bak_preR114'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 値の差替 {n:,} 件(キー数・重複キーは不変)')
print('適用完了')
