# -*- coding: utf-8 -*-
"""第95R: **より短い別語根の訳語が流れ込んだ語根**の訳語を、証拠のある値へ差し替える。
   DRY既定 / --apply。分節(語根の切り方)は1文字も触らない。訳語だけを置き換える。

■ 何が壊れているか
  配信の全域リスト(GG)は word_anno.json 由来。word_anno は辞書セッションの
  「日中韓注釈版ドラフト」から build_word_anno.py が抽出したもので、
  **より短い別語根の訳語が長い語根へ流れ込んでいる**ケースがある。

      likvid  正=[商](を)清算する  → 誤=液体      (likv=[理]液体 から混入)
      legi    正=[史]軍団        → 誤=読む      (leg=(を)読む から混入)
      revizor 正=[法]検察官       → 誤=監査      (reviz=監査 から混入)

  ★ただし「短い語根と長い語根で綴りが重なる」だけでは欠陥にならない。
    legi という**単語**は leg+i(読む)で正しく、誤りなのは legi/o(軍団)の側だけ。
    どの語形がその語根キーを使うかを実描画で確かめてから対象にする。

■ 安全設計(第94Rの mukoz で「直すと退行する」ことを学んだ)
  1. TARGETS は敵対的検証を通過した語根だけを手で書く。機械的な一括変換はしない。
  2. **キーもベース(語根の切り方)も変えない。<rt> の中身だけを差し替える。**
     → 分節は定義上不変。3言語の分節一致は自動的に保たれる。
  3. 現在値が期待どおり(TARGETS の `now`)でなければその言語・その行を捨てる(fail-closed)。
  4. パディング(前後の空白)は元の値のものをそのまま使う。付け足さない。
     (第86Rでパディング二重付加、第94Rでパディング付与による隣接語の注釈消失を経験)
  5. ルビのサイズクラスは helper.output_format で再計算する(訳語の幅が変わるため)。
  6. 既存キーの**値だけ**を差し替える。新規キー・重複キー・行数は不変(冪等)。
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
ap.add_argument('--targets', default='', help='裁定結果JSON(confirmed配列)。未指定なら埋め込みTARGETSを使う')
A = ap.parse_args()
DRY = not A.apply
FMT = 'HTML格式_Ruby文字_大小调整'
LISTS = ['局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)',
         '二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)',
         '全域替换用のリスト(列表)型配列(replacements_final_list)']
RUBY = re.compile(r'<ruby>(.*?)<rt[^>]*>(.*?)</rt></ruby>', re.S)
TAG = re.compile(r'<[^>]+>')
BR = re.compile(r'<br\s*/?>')
LANGS = ('JA', 'ZH', 'KO')

# 語根 -> {'now': {lang: 現在値}, 'new': {lang: 新しい値}, 'src': 出所}
# ★敵対的検証を通過したものだけをここに書く。--targets で外から与えることもできる。
TARGETS = {}

if A.targets:
    conf = json.load(open(LP(A.targets), encoding='utf-8'))
    for c in conf:
        TARGETS[c['root']] = {
            'now': {'JA': c.get('now', '')},
            # ★言語ごとに独立。null/未指定ならその言語は触らない(既に正しい/裁定で却下)
            'new': {l: c.get('new_' + l.lower()) for l in ('JA', 'ZH', 'KO')},
            'src': c.get('source', ''),
            # ★キー限定モード: 指定があればそのキーだけを対象にする。
            #   ルビのベースが語根と一致しない場合に使う(例 romanet 族はベースが roman)。
            'keys': set(c['keys']) if c.get('keys') else None,
            # ★現在値ガード: 指定があれば、その言語の現在値が一致する行だけ触る(fail-closed)
            'guard': c.get('guard') or None,
        }
if not TARGETS:
    raise SystemExit('★TARGETS が空。--targets で裁定結果JSONを渡すこと(機械的一括変換はしない設計)')

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
            hits = [i for i, b in enumerate(lb) if b in TARGETS]
            if not hits: continue
            if surface(cur).strip() != e[0].strip():
                skipped['現行値の表層がキーと違う'] += 1; continue
            gl = [p[1] for p in cur if not isinstance(p, str)]
            newg = list(gl); changed = False
            for i in hits:
                t = TARGETS[lb[i]]
                want = t['new'].get(lang)
                if not want:
                    skipped[f'{lb[i]}: {lang} は対象外(裁定で据置)'] += 1; continue
                # ★キー限定モード: 指定キー以外は触らない
                if t['keys'] is not None and e[0].strip() not in t['keys']:
                    skipped[f'{lb[i]}: キー限定の対象外'] += 1; continue
                # ★現在値ガード: 想定した現在値でなければ触らない(fail-closed)
                g = t['guard']
                if g and g.get(lang) is not None and newg[i] != g[lang]:
                    skipped[f'{lb[i]}: {lang} の現在値がガードと違う'] += 1; continue
                if newg[i] == want: continue
                newg[i] = want; changed = True
            if not changed:
                stat[f'{lang}:既に正しい'] += 1; continue
            buf = []; gi = 0
            for p in cur:
                if isinstance(p, str): buf.append(p); continue
                buf.append(helper.output_format(p[0], newg[gi], FMT, cw)); gi += 1
            val = ''.join(buf)
            new = parse(val)
            # ★分節(ベース列)が1文字も変わっていないことを検証
            if [p[0] for p in new if not isinstance(p, str)] != bases:
                skipped['ベースが変わった'] += 1; continue
            if surface(new) != surface(cur):
                skipped['表層が変わった'] += 1; continue
            if [p[1] for p in new if not isinstance(p, str)] != newg:
                skipped['訳語が意図と違う'] += 1; continue
            # ★parse() は前後の空白パディングも literal 片として拾うので、val には
            #   既にパディングが含まれている。ここで pad_l/pad_r を足すと**二重になる**。
            #   (第86Rで踏み、第95Rでも DRY-RUN の目視 « » → «  » で再発を検出した)
            #   ここでは val をそのまま使い、外側の空白が元と同じであることを検証する。
            if (len(val) - len(val.lstrip())) != (len(e[1]) - len(e[1].lstrip())) or \
               (len(val) - len(val.rstrip())) != (len(e[1]) - len(e[1].rstrip())):
                skipped['★パディングが変わった'] += 1; continue
            per[(li, idx)] = (e[0], val)
            segof.setdefault(e[0], {})[lang] = '/'.join(bases)
            stat[f'{lang}:★是正'] += 1
            r0 = lb[hits[0]]
            if len(samples[(lang, r0)]) < 3:
                def sh(x): return ''.join('«' + p + '»' if isinstance(p, str)
                                          else f'{p[0]}[{p[1]}]' for p in parse(x))
                samples[(lang, r0)].append((e[0].strip(), sh(e[1]), sh(val)))
    plan[lang] = per
    print(f'[{lang}] 是正対象キー {len(per):,}')

# ── 3言語の検証 ───────────────────────────────────────────
# ★キー集合は3言語で一致しなくてよい。ある言語だけ既に正しい訳語を持っていれば
#   その言語は変更不要になるため(例: orient の ZH は既に「东」)。
#   **絶対要件は「分節(語根の切り方)が3言語で完全一致すること」**であり、
#   本スクリプトは <rt> の中身しか触らないので分節は定義上不変。
#   それを実測でも確かめる: 触った全キーについて、3言語の**現在の**分節が一致するか。
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
bad = [k for k in union
       if len({cur[l].get(k) for l in LANGS}) != 1 or cur['JA'].get(k) is None]
if bad:
    for k in sorted(bad)[:5]:
        print('   ', repr(k), {l: cur[l].get(k) for l in LANGS})
    raise SystemExit(f'★分節が3言語で食い違うキーがある {len(bad)} 件: 中止')
print(f'3言語の分節一致(触ったキー全数): ○ ({len(union):,} キー)')
# 差替後も分節が変わっていないこと(各言語内)
bad2 = [k for k, m in segof.items() if len(set(m.values())) != 1]
if bad2:
    raise SystemExit(f'★同一キーの分節が言語間で食い違う {len(bad2)} 件: 中止')
print('内訳: ' + ' / '.join(f'{k}={v}' for k, v in sorted(stat.items())))
if skipped:
    print('skip: ' + ' / '.join(f'{k}={v}' for k, v in skipped.most_common(8)))
print('\n=== 例 (JA) ===')
for (lang, r0), ss in sorted(samples.items()):
    if lang != 'JA': continue
    print(f'\n[{r0}]  出所: {TARGETS[r0]["src"][:80]}')
    for k, o, n in ss:
        print(f'   {k}\n     現在 {o}\n     以後 {n}')
if A.report:
    # ★TARGETS の 'keys' は set なのでそのままでは JSON 化できない(第96Rで実際に落ちた)。
    #   幸い report 出力は適用ループより前にあるので部分書き込みは起きなかったが、
    #   「レポートで落ちて適用が走らない」のは事故なので必ず直列化可能な形にする。
    def ser(t):
        return {'now': t['now'], 'new': t['new'], 'src': t['src'],
                'keys': sorted(t['keys']) if t['keys'] else None, 'guard': t['guard']}
    json.dump({'stat': dict(stat), 'skipped': dict(skipped),
               'targets': {k: ser(v) for k, v in TARGETS.items()},
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
    atomic_file_copy(LP(path), LP(path + '.bak_preR95G'))
    atomic_json_dump(LP(path), d)
    print(f'[{lang}] 値の差替 {n:,} 件(キー数・重複キー・分節は不変)')
print('適用完了')
