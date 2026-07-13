# -*- coding: utf-8 -*-
"""
検証済み確定リスト out/confirmed_tier{N}.json (各 {w, target}) を元に、
3アプリの語根分解法設定JSONを補正(競合nosl棚卸し＋target分解を高優先度で強制)し、
再生成→検証。 target はgold分解(または検証で修正された分解)。
  python apply_confirmed.py <tier> [--write]
"""
import os
import hashlib, json, sys, re
sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repoルート自動検出
sys.path.insert(0, BASE + r"\_analysis_20260625")
from gen_replacement import (
    correction_removal_identity,
    confirmed_priority_for_stem,
    filter_settings_for_correction_removals,
    generate,
    lp,
    normalize_esperanto_surface_notation,
)
from extract_lib import hat_to_circumflex, replace_esperanto_chars
from atomic_json import atomic_file_copy, atomic_json_dump
from gold_snapshot import consistent_snapshot
OUT = BASE + r"\_analysis_20260625\out"
BASE_SETTINGS_PATH = os.path.join(
    BASE, "_analysis_20260625", "_base_stemming_settings.json",
)
BASE_SETTINGS_MANIFEST_PATH = os.path.join(
    BASE, "_analysis_20260625", "_base_stemming_settings_manifest.json",
)


def load_pinned_base_settings():
    with open(lp(BASE_SETTINGS_MANIFEST_PATH), encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("schema_version") != 1:
        raise SystemExit("unsupported base stemming settings manifest schema")
    with open(lp(BASE_SETTINGS_PATH), "rb") as handle:
        disk_raw = handle.read()
    if manifest.get("line_endings") != "canonical_lf":
        raise SystemExit("unsupported base settings line-ending policy")
    raw = disk_raw.replace(b"\r\n", b"\n")
    if b"\r" in raw:
        raise SystemExit("base settings contain unsupported lone CR bytes")
    if len(raw) != manifest["bytes"]:
        raise SystemExit("base stemming settings byte count mismatch")
    if hashlib.sha256(raw).hexdigest().upper() != manifest["sha256"]:
        raise SystemExit("base stemming settings SHA-256 mismatch")
    payload = json.loads(raw.decode("utf-8"))
    if len(payload) != manifest["rows"]:
        raise SystemExit("base stemming settings row count mismatch")
    semantic = json.dumps(
        payload[manifest["header_rows"]:],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if hashlib.sha256(semantic).hexdigest().upper() != manifest["semantic_sha256"]:
        raise SystemExit("base stemming settings semantic SHA-256 mismatch")
    return payload, manifest


PINNED_BASE_SETTINGS, BASE_SETTINGS_MANIFEST = load_pinned_base_settings()
print(
    "[base settings] "
    f"rows={BASE_SETTINGS_MANIFEST['rows']} "
    f"sha256={BASE_SETTINGS_MANIFEST['sha256']}"
)
GOLD = os.environ.get(
    'ESP_GOLD_PATH',
    os.path.join(
        os.path.dirname(BASE),
        "エスペラント辞書徹底語根分解_20260630",
        "世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt",
    ),
)  # 外部マスター。他環境では環境変数 ESP_GOLD_PATH で指定
if not os.path.exists(lp(GOLD)):
    # WSL不通時はDownloadsバックアップのgoldを使用
    import glob
    _bks=sorted(glob.glob(os.path.join(os.environ['USERPROFILE'],'Downloads','エスペラント_backup_*')))
    for _b in reversed(_bks):
        _g=os.path.join(_b,'語根分解辞書_WSL','世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt')
        if os.path.exists(lp(_g)): GOLD=_g; break
    print(f"[gold] WSL不通→backup使用: {GOLD[:60]}...")
TIER=int(sys.argv[1]); WRITE='--write' in sys.argv
SETTINGS_AUDIT='--settings-audit' in sys.argv
def _norm(p): return replace_esperanto_chars(p, hat_to_circumflex).lower().strip()

# gold辞書マップ: word_nosl -> 分解pieces(正規化)。屈折生成のgold照合に使用。
gold_map={}
gold_raw, gold_identity = consistent_snapshot(lp(GOLD))
print(
    f"[gold] bytes={gold_identity['bytes']} sha256={gold_identity['sha256']}",
    flush=True,
)
expected_gold_sha = os.environ.get('ESP_EXPECTED_GOLD_SHA256', '').strip().upper()
if expected_gold_sha and gold_identity['sha256'] != expected_gold_sha:
    raise RuntimeError(
        f"gold SHA mismatch: expected {expected_gold_sha}, got {gold_identity['sha256']}"
    )
for line in gold_raw.decode('utf-8').splitlines():
    if not line or line.startswith('##') or ':' not in line: continue
    for w in line.split(':')[0].split(' '):
        wc=_norm(w)
        if '#' in wc or not wc: continue
        ps=[p for p in wc.split('/') if p]
        if not ps: continue
        gold_map.setdefault(''.join(ps), ps)
# gold語根集合(全分解片)。stem+語尾がそれ自体gold語根なら分割しない(spontane等の保全)。
gold_roots=set()
for ps in gold_map.values():
    for p in ps: gold_roots.add(p)

with open(lp(OUT+f"\\confirmed_tier{TIER}.json"),encoding='utf-8') as f:
    confirmed=json.load(f)
guard_path=os.path.join(os.path.dirname(__file__), 'no_worsening_guards.json')
with open(lp(guard_path), encoding='utf-8') as f:
    no_worsening_guards=json.load(f)
confirmed.extend(no_worsening_guards)
strict_fix_path=os.path.join(
    os.path.dirname(__file__), '_strict_gold_reference_fixes.json',
)
with open(lp(strict_fix_path), 'rb') as f:
    strict_fix_raw=f.read()
strict_fix_manifest=json.loads(strict_fix_raw.decode('utf-8'))
if (
    strict_fix_manifest.get('schema_version') != 1
    or strict_fix_manifest.get('reference_schema_version') != 4
):
    raise ValueError('unsupported strict gold-reference fix manifest schema')
strict_gold_fixes=strict_fix_manifest.get('entries', [])
strict_fix_compact=json.dumps(
    strict_gold_fixes, ensure_ascii=False, separators=(',', ':'),
).encode('utf-8')
if (
    len(strict_gold_fixes) != strict_fix_manifest.get('expected_entries')
    or hashlib.sha256(strict_fix_compact).hexdigest().upper()
    != strict_fix_manifest.get('entries_sha256')
):
    raise ValueError('strict gold-reference fix manifest identity mismatch')
scope_path=os.path.join(
    os.path.dirname(__file__), '_no_worsening_scope_manifest.json',
)
with open(lp(scope_path), encoding='utf-8') as f:
    strict_scope=json.load(f)
strict_expected=strict_scope.get('expected', {})
if (
    strict_fix_manifest.get('gold_sha256') != gold_identity['sha256']
    or strict_fix_manifest.get('gold_sha256')
    != strict_expected.get('gold', {}).get('sha256')
    or strict_fix_manifest.get('reference_sha256')
    != strict_expected.get('reference_sha256')
):
    raise ValueError('strict gold-reference fixes do not match pinned authority')
strict_words=set()
for entry in strict_gold_fixes:
    word=entry.get('w')
    target=entry.get('target')
    pieces=[piece for piece in str(target).split('/') if piece]
    roles=entry.get('typed_roles')
    if (
        not word or word in strict_words
        or not entry.get('exact_only') or not entry.get('boundary_only')
        or len(roles or '') != len(pieces)
        or any(role not in 'RL' for role in roles or '')
        or normalize_esperanto_surface_notation(word)
        != normalize_esperanto_surface_notation(''.join(pieces))
        or entry.get('case_sensitive') is not True
    ):
        raise ValueError(f'invalid strict gold-reference fix: {entry!r}')
    strict_words.add(word)
confirmed.extend(strict_gold_fixes)
print(
    f"[strict gold] entries={len(strict_gold_fixes)} "
    f"sha256={strict_fix_manifest['entries_sha256']}",
    flush=True,
)
for entry in confirmed:
    normalized_word = normalize_esperanto_surface_notation(entry['w'])
    normalized_target = normalize_esperanto_surface_notation(entry['target'].replace('/', ''))
    if normalized_word != normalized_target:
        raise ValueError(
            f"confirmed surface/target mismatch: {entry['w']!r} -> {entry['target']!r}"
        )

_NOMINAL=["o","oj","on","ojn","a","aj","an","ajn","e","en"]
def make_correction(decomp, boundary_only=False, boundary_with_noop_guard=False,
                    exact_only=False, case_sensitive=False,
                    allow_substring=False, typed_roles=None,
                    context_annotation=None):
    """target分解→設定エントリ。屈折語尾はgold照合で生成:
      候補(名詞/形容詞/副詞語尾)のうち、stem+語尾がgoldに「別分解で」存在する形だけ除外。
      → 多品詞語根(esperant=名詞esperanto/形容詞esperanta/副詞esperante)の兄弟形を1項目から自動カバーしつつ、
        衝突(名詞tramet+i=gold tra/met/i、spontan+e=gold語根spontane)は回避。
      動詞形(verbo)は gold語尾がiか stem+iがgold整合の場合のみ付与。
    """
    pieces=[p for p in decomp.split('/') if p]
    if not pieces: return None
    if typed_roles is not None:
        if not exact_only:
            raise ValueError("typed_roles requires exact_only")
        if len(typed_roles) != len(pieces) or any(role not in "RL" for role in typed_roles):
            raise ValueError(f"invalid typed_roles {typed_roles!r} for {decomp!r}")
    if context_annotation is not None and not isinstance(context_annotation, str):
        raise ValueError("context_annotation must be a reserved word_anno key")
    nosl=''.join(pieces)
    last=pieces[-1]
    if exact_only:
        stem=decomp; stem_nosl=nosl
        suffixes=["ne"]
        if len(pieces) == 1:
            suffixes.append("atomic_no_split")
        if boundary_only or boundary_with_noop_guard:
            suffixes.append("word_boundary")
        if boundary_with_noop_guard:
            suffixes.append("boundary_noop_guard")
    elif boundary_only or boundary_with_noop_guard:
        stem=decomp; stem_nosl=nosl
        suffixes=["ne", "word_boundary"]                  # 固定語形だが語内部は捕捉しない
        if boundary_with_noop_guard:
            suffixes.append("boundary_noop_guard")
    elif len(pieces) >= 2 and last in ("as", "is", "os", "us"):
        # Esperanto permits productive verbalization beyond dictionary rows
        # explicitly tagged as verbs (agrabl/as, leg/ebl/as, apud/as).  One
        # reviewed finite form licenses the full bounded verb paradigm; the
        # generator renders as/is/os/us from localized CSV entries as rubies.
        stem='/'.join(pieces[:-1]); stem_nosl=''.join(pieces[:-1])
        suffixes=["verbo_s1", "verbo_s2"]
    elif len(pieces)>=2 and last in ('o','a','e','i') and len(last)==1:
        stem='/'.join(pieces[:-1]); stem_nosl=''.join(pieces[:-1]); stem_pieces=pieces[:-1]
        suffixes=[]
        for end in _NOMINAL:
            form=stem_nosl+end
            if form==nosl:
                suffixes.append(end); continue              # 確定語自身は常に採用(私の意図分解が正本)
            if form in gold_roots and [form]!=stem_pieces+[end]:
                continue                                    # 兄弟形がそれ自体gold語根(spontane等)→分割しない
            gd=gold_map.get(form)
            if gd is not None and gd!=stem_pieces+[end]:
                continue                                    # 兄弟形がgoldで別分解→侵食しない(trameti等)
            suffixes.append(end)
        addverb=(last=='i')
        if not addverb:
            gi=gold_map.get(stem_nosl+'i')
            if gi is not None and gi==stem_pieces+['i']: addverb=True
        if addverb:
            suffixes=["verbo_s1","verbo_s2"]+suffixes
    else:
        stem=decomp; stem_nosl=nosl
        suffixes=["ne"]                                     # 固定形(全体強制)
    # Confirmed entries are corpus/dictionary adjudications for complete word
    # forms.  Their productive sibling endings remain useful, but every sibling
    # must also be whole-word bounded: an unbounded high-priority ``fer/i``
    # sibling otherwise consumes the tail of unrelated ``ofer/i``.  A future
    # deliberately productive-in-compounds entry must opt in explicitly.
    if not allow_substring and "word_boundary" not in suffixes:
        suffixes.append("word_boundary")
    if case_sensitive:
        suffixes.append("case_sensitive")
    if typed_roles is not None:
        suffixes.append(f"typed_roles:{typed_roles}")
    if context_annotation is not None:
        suffixes.append(f"context_annotation:{context_annotation}")
    # Confirmed human adjudications must beat same-surface generated rules
    # (+5000 in gen_replacement) without crossing the next length tier.
    prio=confirmed_priority_for_stem(stem_nosl)
    return {
        'stem': stem,
        'stem_nosl': stem_nosl,
        'prio': prio,
        'suffixes': suffixes,
        'word_nosl': nosl,
        'case_sensitive': case_sensitive,
        'exact_only': exact_only,
    }

# 同一語幹は語尾を和集合マージ(例 sugesti/o + sugesti/a + sugesti/i → 名詞+形容詞+動詞)
corrs={}
remove_nosl_casefold=set(); remove_nosl_exact_case=set()
exact_only_remove_nosl_casefold=set()
exact_only_remove_nosl_exact_case=set()
for e in confirmed:
    c=make_correction(
        e['target'],
        bool(e.get('boundary_only')),
        bool(e.get('boundary_with_noop_guard')),
        bool(e.get('exact_only')),
        bool(e.get('case_sensitive')),
        bool(e.get('allow_substring')),
        e.get('typed_roles'),
        e.get('context_annotation'),
    )
    if not c: continue
    sn=c['stem_nosl']
    if sn in corrs and corrs[sn]['stem']==c['stem']:
        ex=corrs[sn]
        for s in c['suffixes']:
            if s not in ex['suffixes']: ex['suffixes'].append(s)
        ex['prio']=max(ex['prio'], c['prio'])
    else:
        corrs[sn]=c
    # A case-sensitive proper name replaces only an old row with the same
    # written case.  Deleting its casefold sibling would erase legitimate
    # homographs (Sin must coexist with grammatical si/n; Kacumi with kacumi).
    if c['exact_only']:
        removal_set = (
            exact_only_remove_nosl_exact_case
            if c['case_sensitive'] else exact_only_remove_nosl_casefold
        )
    else:
        removal_set = (
            remove_nosl_exact_case
            if c['case_sensitive'] else remove_nosl_casefold
        )
    removal_set.add(correction_removal_identity(sn, c['case_sensitive']))
    removal_set.add(correction_removal_identity(
        c['word_nosl'], c['case_sensitive'],
    ))

# These four reviewed stems resolve equal-length prefix/suffix competitions
# that used to choose different decompositions by annotation language.  Keep
# their full productive paradigms explicit: future gold drift must not silently
# prune one sibling and reintroduce a language-specific fallback.
_required_productive_corrections = {
    "akordig": (
        "akord/ig", {"verbo_s1", "verbo_s2", "word_boundary"},
    ),
    "difinit": (
        "difin/it",
        {"o", "oj", "on", "ojn", "a", "aj", "an", "ajn", "e", "en",
         "word_boundary"},
    ),
    "memorigant": (
        "memor/ig/ant",
        {"o", "oj", "on", "ojn", "a", "aj", "an", "ajn", "e", "en",
         "word_boundary"},
    ),
    "rehonorigant": (
        "re/honor/ig/ant",
        {"o", "oj", "on", "ojn", "a", "aj", "an", "ajn", "e", "en",
         "word_boundary"},
    ),
}
for _identity, (_stem, _actions) in _required_productive_corrections.items():
    _actual = corrs.get(_identity)
    if (
        _actual is None
        or _actual["stem"] != _stem
        or set(_actual["suffixes"]) != _actions
    ):
        raise ValueError(
            "required productive correction drifted: "
            f"{_identity!r}: expected stem/actions={(_stem, sorted(_actions))!r}, "
            f"got {_actual!r}"
        )
print(f"Tier{TIER} 確定 {len(confirmed)} → 補正エントリ {len(corrs)}")

APPS={'JP':(r"\Esperanto-Kanji-Ruby-JA",r"\エスペラント語根-日本語訳ルビ対応リスト.csv",'ja'),
      'ZH':(r"\Esperanto-Kanji-Ruby-ZH",r"\世界语词根-中文注释对应列表.csv",'zh'),
      'KO':(r"\Esperanto-Kanji-Ruby-KO",r"\에스페란토 어근-한국어 번역 루비 대응 목록.csv",'ko')}
ESTEM=r"\E_stem.json"
ROOTS=r"\root_list.txt"; FINAL=r"\置換リスト_ルビ.json"
STEM=r"\分解設定.json"; USER=r"\替换后文字列(汉字)の使用者自定义设置(基本上完全不推荐).json"; FMT='HTML格式_Ruby文字_大小调整'


def prepare_settings(settings_path):
    with open(lp(settings_path),encoding='utf-8') as f:
        current_settings=json.load(f)
    settings=json.loads(json.dumps(PINNED_BASE_SETTINGS, ensure_ascii=False))
    if (
        current_settings
        and isinstance(current_settings[0], list)
        and len(current_settings[0]) != 3
    ):
        settings[0]=current_settings[0]
    settings, removed = filter_settings_for_correction_removals(
        settings, remove_nosl_exact_case, remove_nosl_casefold,
        exact_only_remove_nosl_exact_case,
        exact_only_remove_nosl_casefold,
    )
    for sn,c in corrs.items():
        settings.append([c['stem'], c['prio'], list(c['suffixes'])])
    return settings, removed

def process(key, write):
    d,csvn,lang=APPS[key]; APPDIR=BASE+d; DATA=APPDIR+r"\app_data"
    sp=DATA+STEM
    # The morphology settings are language-independent.  Always rebuild from
    # one pinned base instead of reading a per-app rollback backup: an older ZH
    # backup had already absorbed generated word_boundary rows and produced a
    # different global key set.  Keep only the localized explanatory header.
    settings, removed = prepare_settings(sp)
    tmp=DATA+r"\_settings_confirmed_tmp.json"
    with open(lp(tmp),'w',encoding='utf-8') as g: json.dump(settings,g,ensure_ascii=False,indent=1)
    with open(lp(OUT+f"\\word_anno_{lang}.json"),encoding='utf-8') as f: word_anno=json.load(f)
    combined=generate(APPDIR,DATA,DATA+csvn,tmp,DATA+USER,DATA+ESTEM,DATA+ROOTS,FMT,word_anno=word_anno)
    if write:
        atomic_file_copy(lp(sp), lp(sp+".bak_preTier"+str(TIER)+"confirmed"))
        atomic_json_dump(sp, settings, indent=1)
        # 大JSONはリポジトリの正規形(改行なし)で保存。
        # pretty-print は数百万行の無意味な diff と中間失敗時の肥大化を生む。
        atomic_json_dump(DATA+FINAL, combined)
        os.remove(lp(tmp))
        print(f"  [{key}] 除去{removed} 追加{len(corrs)} → 書込完了")
    else:
        os.remove(lp(tmp)); print(f"  [{key}] 除去{removed} 追加{len(corrs)} (未書込)")
    return combined


if SETTINGS_AUDIT:
    semantic_hashes={}
    for key,(directory,_csv_name,_lang) in APPS.items():
        settings_path=BASE+directory+r"\app_data"+STEM
        settings, removed = prepare_settings(settings_path)
        semantic=json.dumps(
            settings[1:], ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")
        digest=hashlib.sha256(semantic).hexdigest().upper()
        semantic_hashes[key]=digest
        print(
            f"  [{key}] rows={len(settings)} removed={removed} "
            f"semantic_sha256={digest}"
        )
    if len(set(semantic_hashes.values())) != 1:
        raise SystemExit(
            "3-language morphology settings differ after pinned-base overlay: "
            + repr(semantic_hashes)
        )
    print("[settings audit] PASS: 3-language semantic settings are identical")
    raise SystemExit(0)

# JP検証 (SKIP_VERIFY=1 で省略=反復高速化)
if not os.environ.get('SKIP_VERIFY'):
    combined=process('JP', False)
    sys.path.insert(0, BASE+APPS['JP'][0])
    from esp_text_replacement_module import orchestrate_comprehensive_esperanto_text_replacement as orch, import_placeholders as imp
    DATA=BASE+APPS['JP'][0]+r"\app_data"
    ps=imp(lp(DATA+r"\placeholders_skip.txt")); pl=imp(lp(DATA+r"\placeholders_localcapture.txt"))
    g_=combined["全域替换用のリスト(列表)型配列(replacements_final_list)"]; l_=combined["局部文字替换用のリスト(列表)型配列(replacements_list_for_localized_string)"]; c_=combined["二文字词根替换用のリスト(列表)型配列(replacements_list_for_2char)"]
    def segplain(w): return re.sub(r'<[^>]+>','',orch(w,ps,l_,pl,g_,c_,FMT))
    print("\n  検証(確定語の再分解):")
    for e in confirmed[:40]:
        full=''.join(p for p in e['target'].split('/') if p)
        print(f"    {full:20s} -> {segplain(full)}")
if WRITE:
    process('ZH', True); process('KO', True); process('JP', True)
    print("\n3アプリ書込完了")
