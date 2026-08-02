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
  1. 固定コミット間で実際に変わった言語/list/key/片番号だけを台帳化する。
     語根名を一括規則にせず、同綴り・別語義の行へは広げない。
  2. **キーもベース(語根の切り方)も変えない。<rt> の中身だけを差し替える。**
     → 分節は定義上不変。3言語の分節一致は自動的に保たれる。
  3. 現在値が台帳の before/after のどちらでもなければ、1行も書かず停止する。
  4. パディング(前後の空白)は元の値のものをそのまま使う。付け足さない。
     (第86Rでパディング二重付加、第94Rでパディング付与による隣接語の注釈消失を経験)
  5. ルビのサイズクラスは helper.output_format で再計算する(訳語の幅が変わるため)。
  6. 既存キーの**値だけ**を差し替える。新規キー・重複キー・行数は不変(冪等)。
"""
import json, os, re, sys, argparse, collections, hashlib
sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92); PFX = BS * 2 + chr(63) + BS
def LP(p): return PFX + os.path.abspath(p)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, '_analysis_20260625'))
from build_r98_root_gloss_transition_ledger import (
    EXPECTED_LEDGER_SHA256, PREDECESSOR_COMMIT, TARGET_COMMIT,
)
from gen_replacement import load_app_replacement_helper
from r98_payload_transaction import (
    ConcurrentModificationError,
    PayloadTransactionError,
    apply_payload_transaction,
    validate_report_path,
)

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--no-backup', action='store_true')
ap.add_argument('--report', default='')
ap.add_argument(
    '--targets', required=True,
    help='build_r98_root_gloss_transition_ledger.py が封印した exact 台帳',
)
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
PAYLOAD_PATHS = {
    lang: os.path.join(
        ROOT, f'Esperanto-Kanji-Ruby-{lang}',
        'app_data', '置換リスト_ルビ.json',
    )
    for lang in LANGS
}
CHAR_WIDTH_PATHS = {
    lang: os.path.join(
        ROOT, f'Esperanto-Kanji-Ruby-{lang}',
        'app_data', 'char_widths.json',
    )
    for lang in LANGS
}
OUT_DIR = os.path.join(ROOT, '_analysis_20260625', 'out')
JOURNAL_PATH = os.path.join(OUT_DIR, '.r98_root_gloss_transaction.active.json')
LOCK_PATH = os.path.join(OUT_DIR, '.r98_root_gloss_transaction.lock')

if A.report and DRY:
    raise SystemExit('★--report はtransaction完了後の証拠なので --apply と併用すること')
if A.report:
    validate_report_path(
        A.report,
        report_directory=OUT_DIR,
        protected_paths={
            'ledger': A.targets,
            'journal': JOURNAL_PATH,
            'lock': LOCK_PATH,
            **{f'payload:{lang}': path for lang, path in PAYLOAD_PATHS.items()},
            **{f'char_width:{lang}': path for lang, path in CHAR_WIDTH_PATHS.items()},
        },
    )

with open(LP(A.targets), 'rb') as stream:
    ledger_raw = stream.read()
if hashlib.sha256(ledger_raw).hexdigest().upper() != EXPECTED_LEDGER_SHA256:
    raise SystemExit('★exact 訳語遷移台帳のSHA-256が封印値と違う')
ledger = json.loads(ledger_raw.decode('utf-8'))
if not isinstance(ledger, dict) or ledger.get('schema_version') != 1:
    raise SystemExit('★exact 訳語遷移台帳の schema_version が不正')
if ledger.get('ledger_id') != 'r95-r96-r98-root-gloss-exact-transition-v1':
    raise SystemExit('★exact 訳語遷移台帳の ledger_id が不正')
authority = ledger.get('authority') or {}
if authority.get('predecessor_commit') != PREDECESSOR_COMMIT \
   or authority.get('target_commit') != TARGET_COMMIT:
    raise SystemExit('★exact 訳語遷移台帳の固定commit鎖が不正')
policy = ledger.get('policy') or {}
required_policy = {
    'ruby_only': True,
    'gloss_and_size_class_only': True,
    'source_key_must_remain_exact': True,
    'list_bucket_must_remain_exact': True,
    'ruby_segment_index_must_remain_exact': True,
    'wildcard_or_substring_authorization': False,
    'boundary_change_authorized': False,
    'placeholder_change_authorized': False,
    'kanji_change_authorized': False,
}
for key, expected_value in required_policy.items():
    if policy.get(key) is not expected_value:
        raise SystemExit(f'★exact 訳語遷移台帳の policy が不正: {key}')

# AUTH[lang][(list code, exact raw source key)][Ruby segment index]
#     = (root, before gloss, after gloss, before rendered rt, after rendered rt)
# 語根名を一括規則にせず、固定コミット間で実際に変わった座標だけを許可する。
AUTH = {lang: {} for lang in LANGS}
ROOT_META = {}
expected = set()
for item in ledger.get('confirmed') or []:
    root = item['root']
    if root in ROOT_META:
        raise SystemExit(f'★exact 訳語遷移台帳の語根が重複: {root}')
    ROOT_META[root] = item
    for lang in LANGS:
        for row in item['transitions'].get(lang, []):
            code = row['list']
            if code not in ('GL', 'G2', 'GG'):
                raise SystemExit(f'★未知のリストコード: {code}')
            token = (code, row['key'])
            spec = AUTH[lang].setdefault(token, {})
            for segment in row['segments']:
                index = segment['index']
                if index in spec:
                    raise SystemExit(
                        f'★exact 訳語遷移座標が重複: '
                        f'{lang}/{code}/{row["key"]!r}/{index}'
                    )
                before = segment['before']
                after = segment['after']
                before_rendered = segment['before_rendered']
                after_rendered = segment['after_rendered']
                if before == after:
                    raise SystemExit('★before と after が同一の遷移は許可しない')
                if before_rendered == after_rendered:
                    raise SystemExit('★before/after rendered が同一の遷移は許可しない')
                spec[index] = (
                    root, before, after, before_rendered, after_rendered,
                )
                expected.add((
                    lang, code, row['key'], index, root, before, after,
                    before_rendered, after_rendered,
                ))
if not expected:
    raise SystemExit('★exact 訳語遷移台帳が空')

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

def render_selected(value, replacements, helper, char_widths):
    """Re-render only authorized Ruby segments; preserve every other byte."""
    out = []
    pos = 0
    for index, match in enumerate(RUBY.finditer(value)):
        out.append(value[pos:match.start()])
        if index in replacements:
            base = TAG.sub('', match.group(1))
            out.append(helper.output_format(
                base, replacements[index], FMT, char_widths,
            ))
        else:
            out.append(match.group(0))
        pos = match.end()
    out.append(value[pos:])
    return ''.join(out)


plan = {}; stat = collections.Counter(); seen = set()
payload_raw = {}; payload_docs = {}
samples = collections.defaultdict(list)
for lang in LANGS:
    app_dir = os.path.join(ROOT, f'Esperanto-Kanji-Ruby-{lang}')
    with open(LP(PAYLOAD_PATHS[lang]), 'rb') as stream:
        payload_raw[lang] = stream.read()
    d = json.loads(payload_raw[lang].decode('utf-8'))
    payload_docs[lang] = d
    helper = load_app_replacement_helper(app_dir)
    with open(LP(CHAR_WIDTH_PATHS[lang]), encoding='utf-8') as stream:
        cw = json.load(stream)
    per = {}
    for li, name in enumerate(LISTS):
        code = ('GL', 'G2', 'GG')[li]
        for idx, e in enumerate(d[name]):
            if not (isinstance(e, list) and len(e) >= 2 and isinstance(e[0], str)):
                continue
            authorized = AUTH[lang].get((code, e[0]))
            if authorized is None:
                continue
            cur = parse(e[1])
            bases = [p[0] for p in cur if not isinstance(p, str)]
            if not bases:
                raise SystemExit(f'★許可行にRubyが無い: {lang}/{code}/{e[0]!r}')
            if surface(cur).strip() != e[0].strip():
                raise SystemExit(f'★許可行の表層がキーと違う: {lang}/{code}/{e[0]!r}')
            gl = [p[1] for p in cur if not isinstance(p, str)]
            rendered_segments = [match.group(0) for match in RUBY.finditer(e[1])]
            replacements = {}
            expected_after_rendered = {}
            roots = []
            for i, values in sorted(authorized.items()):
                root, before, after, before_rendered, after_rendered = values
                identity = (
                    lang, code, e[0], i, root, before, after,
                    before_rendered, after_rendered,
                )
                seen.add(identity)
                if i >= len(bases):
                    raise SystemExit(f'★許可したRuby片番号が範囲外: {identity!r}')
                if bases[i].lower() != root:
                    raise SystemExit(
                        f'★許可した語根座標が別語根を指す: '
                        f'{identity!r} -> {bases[i]!r}'
                    )
                current_rendered = rendered_segments[i]
                if gl[i] == after and current_rendered == after_rendered:
                    stat[f'{lang}:既に正しい片'] += 1
                elif gl[i] == before and current_rendered == before_rendered:
                    replacements[i] = after
                    expected_after_rendered[i] = after_rendered
                    stat[f'{lang}:★是正片'] += 1
                else:
                    raise SystemExit(
                        f'★許可行の訳語またはrt class/markupが固定before/afterと違う: '
                        f'{lang}/{code}/{e[0]!r}/{i} current={current_rendered!r}'
                    )
                roots.append(root)
            if not replacements:
                stat[f'{lang}:既に正しい行'] += 1
                continue
            newg = list(gl)
            for i, value in replacements.items():
                newg[i] = value
            val = render_selected(e[1], replacements, helper, cw)
            new = parse(val)
            # ★分節(ベース列)が1文字も変わっていないことを検証
            if [p[0] for p in new if not isinstance(p, str)] != bases:
                raise SystemExit(f'★ベースが変わった: {lang}/{code}/{e[0]!r}')
            if surface(new) != surface(cur):
                raise SystemExit(f'★表層が変わった: {lang}/{code}/{e[0]!r}')
            if [p[1] for p in new if not isinstance(p, str)] != newg:
                raise SystemExit(f'★訳語が意図と違う: {lang}/{code}/{e[0]!r}')
            new_rendered = [match.group(0) for match in RUBY.finditer(val)]
            for i, rendered in expected_after_rendered.items():
                if new_rendered[i] != rendered:
                    raise SystemExit(
                        f'★再計算したrt class/markupが固定target commitと違う: '
                        f'{lang}/{code}/{e[0]!r}/{i}'
                    )
            # ★parse() は前後の空白パディングも literal 片として拾うので、val には
            #   既にパディングが含まれている。ここで pad_l/pad_r を足すと**二重になる**。
            #   (第86Rで踏み、第95Rでも DRY-RUN の目視 « » → «  » で再発を検出した)
            #   ここでは val をそのまま使い、外側の空白が元と同じであることを検証する。
            if (len(val) - len(val.lstrip())) != (len(e[1]) - len(e[1].lstrip())) or \
               (len(val) - len(val.rstrip())) != (len(e[1]) - len(e[1].rstrip())):
                raise SystemExit(f'★パディングが変わった: {lang}/{code}/{e[0]!r}')
            per[(li, idx)] = (e[0], val)
            stat[f'{lang}:★是正行'] += 1
            for r0 in sorted(set(roots)):
                if len(samples[(lang, r0)]) < 3:
                    def sh(x): return ''.join(
                        '«' + p + '»' if isinstance(p, str)
                        else f'{p[0]}[{p[1]}]' for p in parse(x)
                    )
                    samples[(lang, r0)].append(
                        (e[0].strip(), sh(e[1]), sh(val))
                    )
    plan[lang] = per
    print(f'[{lang}] 是正対象キー {len(per):,}')

missing = expected - seen
extra = seen - expected
if missing or extra:
    raise SystemExit(
        f'★exact 訳語遷移座標の過不足: missing={len(missing)} extra={len(extra)}'
    )

# ── 3言語の検証 ───────────────────────────────────────────
# ★キー集合は3言語で一致しなくてよい。ある言語だけ既に正しい訳語を持っていれば
#   その言語は変更不要になるため(例: orient の ZH は既に「东」)。
#   **絶対要件は「分節(語根の切り方)が3言語で完全一致すること」**であり、
#   本スクリプトは <rt> の中身しか触らないので分節は定義上不変。
#   それを実測でも確かめる: 触った全キーについて、3言語の**現在の**分節が一致するか。
pairs = set().union(*(set(AUTH[lang]) for lang in LANGS))
print(f'許可したリスト/キー対(和集合) {len(pairs):,}')
cur = {}
for lang in LANGS:
    d = payload_docs[lang]
    m = {}
    for li, name in enumerate(LISTS):
        code = ('GL', 'G2', 'GG')[li]
        wanted = {key for pair_code, key in pairs if pair_code == code}
        for e in d[name]:
            if isinstance(e[0], str) and e[0] in wanted:
                token = (code, e[0])
                if token in m:
                    raise SystemExit(
                        f'★許可キーが同一リスト内で重複: {lang}/{token!r}'
                    )
                m[token] = '/'.join(
                    p[0] for p in parse(e[1]) if not isinstance(p, str)
                )
    cur[lang] = m
bad = [pair for pair in pairs
       if len({cur[l].get(pair) for l in LANGS}) != 1
       or cur['JA'].get(pair) is None]
if bad:
    for pair in sorted(bad)[:5]:
        print('   ', repr(pair), {l: cur[l].get(pair) for l in LANGS})
    raise SystemExit(f'★分節が3言語で食い違うキーがある {len(bad)} 件: 中止')
print(f'3言語の分節一致(許可した対全数): ○ ({len(pairs):,} 対)')
print('内訳: ' + ' / '.join(f'{k}={v}' for k, v in sorted(stat.items())))
print('\n=== 例 (JA) ===')
for (lang, r0), ss in sorted(samples.items()):
    if lang != 'JA': continue
    print(f'\n[{r0}]  出所: {ROOT_META[r0]["source"][:80]}')
    for k, o, n in ss:
        print(f'   {k}\n     現在 {o}\n     以後 {n}')


def build_candidates(snapshots):
    """Build all three candidates from the transaction's one snapshot."""
    result = {}
    for lang in LANGS:
        if snapshots[lang] != payload_raw[lang]:
            raise ConcurrentModificationError(
                f'{lang} payload changed between exact planning and transaction snapshot'
            )
        if not plan[lang]:
            result[lang] = snapshots[lang]
            continue
        d = json.loads(snapshots[lang].decode('utf-8'))
        for (li, idx), (key, value) in plan[lang].items():
            row = d[LISTS[li]][idx]
            if row[0] != key:
                raise PayloadTransactionError(
                    f'★添字がずれている {lang} {idx} {row[0]!r} != {key!r}'
                )
            row[1] = value
        result[lang] = json.dumps(d, ensure_ascii=False).encode('utf-8')
    return result


def value_skeleton(value):
    """Remove only rt attributes/text so every other source byte is compared."""
    return RUBY.sub(
        lambda match: f'<ruby>{match.group(1)}<rt></rt></ruby>', value,
    )


def validate_candidates(before_bytes, after_bytes):
    """Prove exact scope, pinned target markup and trilingual boundaries."""
    boundary = {lang: {} for lang in LANGS}
    for lang in LANGS:
        before = json.loads(before_bytes[lang].decode('utf-8'))
        after = json.loads(after_bytes[lang].decode('utf-8'))
        if set(before) != set(after):
            raise PayloadTransactionError(f'{lang}: payload top-level schema changed')
        for key in before:
            if key not in LISTS and before[key] != after[key]:
                raise PayloadTransactionError(
                    f'{lang}: non-replacement field changed: {key!r}'
                )
        authorized_seen = set()
        for li, name in enumerate(LISTS):
            code = ('GL', 'G2', 'GG')[li]
            old_rows = before[name]
            new_rows = after[name]
            if len(old_rows) != len(new_rows):
                raise PayloadTransactionError(
                    f'{lang}/{code}: row count changed '
                    f'{len(old_rows)} -> {len(new_rows)}'
                )
            for old_row, new_row in zip(old_rows, new_rows):
                if not (
                    isinstance(old_row, list) and len(old_row) >= 2
                    and isinstance(new_row, list) and len(new_row) == len(old_row)
                    and isinstance(old_row[0], str) and isinstance(old_row[1], str)
                    and isinstance(new_row[0], str) and isinstance(new_row[1], str)
                ):
                    if old_row != new_row:
                        raise PayloadTransactionError(
                            f'{lang}/{code}: nonstandard row changed'
                        )
                    continue
                token = (code, old_row[0])
                if token in pairs:
                    if token in boundary[lang]:
                        raise PayloadTransactionError(
                            f'{lang}/{code}: reviewed source key duplicated: {old_row[0]!r}'
                        )
                    candidate_parts = parse(new_row[1])
                    boundary[lang][token] = tuple(
                        part[0] for part in candidate_parts
                        if not isinstance(part, str)
                    )
                    if surface(candidate_parts).strip() != old_row[0].strip():
                        raise PayloadTransactionError(
                            f'{lang}/{code}: candidate surface/key mismatch: {old_row[0]!r}'
                        )
                authorized = AUTH[lang].get(token)
                if authorized is None:
                    if old_row != new_row:
                        raise PayloadTransactionError(
                            f'{lang}/{code}: unauthorized row changed: {old_row[0]!r}'
                        )
                    continue
                authorized_seen.add(token)
                if old_row[0] != new_row[0] or old_row[2:] != new_row[2:]:
                    raise PayloadTransactionError(
                        f'{lang}/{code}: key/placeholder/tail changed: {old_row[0]!r}'
                    )
                if value_skeleton(old_row[1]) != value_skeleton(new_row[1]):
                    raise PayloadTransactionError(
                        f'{lang}/{code}: non-rt structure changed: {old_row[0]!r}'
                    )
                old_parts = [match.group(0) for match in RUBY.finditer(old_row[1])]
                new_parts = [match.group(0) for match in RUBY.finditer(new_row[1])]
                old_parsed = [
                    part for part in parse(old_row[1]) if not isinstance(part, str)
                ]
                new_parsed = [
                    part for part in parse(new_row[1]) if not isinstance(part, str)
                ]
                if len(old_parts) != len(new_parts) or len(old_parts) != len(old_parsed):
                    raise PayloadTransactionError(
                        f'{lang}/{code}: Ruby count changed: {old_row[0]!r}'
                    )
                if [part[0] for part in old_parsed] != [part[0] for part in new_parsed]:
                    raise PayloadTransactionError(
                        f'{lang}/{code}: Ruby boundary changed: {old_row[0]!r}'
                    )
                for index in range(len(old_parts)):
                    spec = authorized.get(index)
                    if spec is None:
                        if old_parts[index] != new_parts[index]:
                            raise PayloadTransactionError(
                                f'{lang}/{code}: unauthorized Ruby piece changed: '
                                f'{old_row[0]!r}/{index}'
                            )
                        continue
                    root, before_gloss, after_gloss, before_rt, after_rt = spec
                    if old_parsed[index][0].lower() != root:
                        raise PayloadTransactionError(
                            f'{lang}/{code}: authorized root moved: {old_row[0]!r}/{index}'
                        )
                    old_identity = (old_parsed[index][1], old_parts[index])
                    if old_identity not in {
                        (before_gloss, before_rt), (after_gloss, after_rt),
                    }:
                        raise PayloadTransactionError(
                            f'{lang}/{code}: source rt is outside pinned before/after: '
                            f'{old_row[0]!r}/{index}'
                        )
                    if (new_parsed[index][1], new_parts[index]) != (
                        after_gloss, after_rt,
                    ):
                        raise PayloadTransactionError(
                            f'{lang}/{code}: candidate rt differs from target commit: '
                            f'{old_row[0]!r}/{index}'
                        )
        if authorized_seen != set(AUTH[lang]):
            raise PayloadTransactionError(
                f'{lang}: authorized row closure drift: '
                f'missing={len(set(AUTH[lang]) - authorized_seen)} '
                f'extra={len(authorized_seen - set(AUTH[lang]))}'
            )

    for token in pairs:
        signatures = {boundary[lang].get(token) for lang in LANGS}
        if None in signatures or len(signatures) != 1:
            raise PayloadTransactionError(
                f'★candidateの三言語分節が不一致: {token!r} '
                + repr({lang: boundary[lang].get(token) for lang in LANGS})
            )


candidates_for_dry_run = build_candidates(dict(payload_raw))
validate_candidates(dict(payload_raw), candidates_for_dry_run)
if DRY:
    print('\n(DRY-RUN: exact 3言語candidate検証済み。--apply でtransaction書込)')
    sys.exit(0)

report_value = {
    'ledger_id': ledger['ledger_id'],
    'ledger_sha256': EXPECTED_LEDGER_SHA256,
    'stat': dict(stat),
    'authorized_segments': len(expected),
    'authorized_list_key_pairs': len(pairs),
    'samples': {f'{lang}:{root}': value for (lang, root), value in samples.items()},
}
result = apply_payload_transaction(
    PAYLOAD_PATHS,
    build_candidates,
    journal_path=JOURNAL_PATH,
    lock_path=LOCK_PATH,
    report_directory=OUT_DIR,
    report_path=A.report or None,
    report_value=report_value if A.report else None,
    protected_paths={
        'ledger': A.targets,
        **{f'char_width:{lang}': path for lang, path in CHAR_WIDTH_PATHS.items()},
    },
    keep_permanent_backups=not A.no_backup,
    candidate_validator=validate_candidates,
)
for lang in LANGS:
    print(
        f'[{lang}] 値の差替 {len(plan[lang]):,} 件 '
        f'(transaction SHA {result.before_sha256[lang][:12]}→'
        f'{result.after_sha256[lang][:12]})'
    )
print('transaction適用完了: ' + ','.join(result.changed_languages or ('変更なし',)))
