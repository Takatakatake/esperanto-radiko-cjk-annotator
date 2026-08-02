# -*- coding: utf-8 -*-
"""
検証済み確定リスト out/confirmed_tier{N}.json (各 {w, target}) を元に、
3アプリの語根分解法設定JSONを補正(競合nosl棚卸し＋target分解を高優先度で強制)し、
再生成→検証。 target はgold分解(または検証で修正された分解)。
  python apply_confirmed.py <tier> [--write]
"""
import os
import gc, hashlib, json, sys, re
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
    validate_multilingual_word_anno_boundaries,
)
from extract_lib import hat_to_circumflex, replace_esperanto_chars
from atomic_json import atomic_binary_copy, atomic_file_copy, atomic_json_dump
from gold_snapshot import consistent_snapshot
from phase532_ruby_policy import (
    CANDIDATE_ACADEMIC_SHA256 as PHASE532_ACADEMIC_SHA256,
    CANDIDATE_LEARNER_SHA256 as PHASE532_LEARNER_SHA256,
    load_phase532_policy,
    managed_morph_targets as phase532_managed_morph_targets,
    strict_supersessions as phase532_strict_supersessions,
)
from phase532_runtime_signature_gate import validate_generated_payloads
from phase532_activation import activation_report
from phase558_ruby_overlay import (
    managed_morph_targets as phase558_managed_morph_targets,
    strict_supersessions as phase558_strict_supersessions,
    typed_exact_targets as phase558_typed_exact_targets,
)
from phase558_ruby_overlay_activation import (
    activation_report as phase558_activation_report,
)
from phase558_ruby_overlay_runtime_gate import (
    validate_generated_payloads as validate_phase558_generated_payloads,
)
from phase598_technical_on_policy import (
    managed_morph_targets as phase598_managed_morph_targets,
    typed_exact_targets as phase598_typed_exact_targets,
)
from phase598_technical_on_activation import (
    activation_report as phase598_activation_report,
)
from phase598_technical_on_runtime_gate import (
    validate_generated_payloads as validate_phase598_generated_payloads,
)
from phase619_ordinary_ruby_policy import (
    managed_morph_targets as phase619_managed_morph_targets,
)
from phase619_ordinary_ruby_activation import (
    activation_report as phase619_activation_report,
)
from phase619_ordinary_ruby_runtime_gate import (
    validate_generated_payloads as validate_phase619_generated_payloads,
)
PHASE532_ACTIVATION = activation_report()
PHASE532_FORMAL = PHASE532_ACTIVATION['phase532_active']
PHASE558_ACTIVATION = phase558_activation_report()
PHASE558_FORMAL = PHASE558_ACTIVATION['phase558_ruby_overlay_active']
PHASE598_ACTIVATION = phase598_activation_report()
PHASE598_FORMAL = PHASE598_ACTIVATION['phase598_technical_on_active']
PHASE619_ACTIVATION = phase619_activation_report()
PHASE619_FORMAL = PHASE619_ACTIVATION['phase619_ordinary_ruby_active']
R94_RESIDUAL_LEDGER_PATH = os.path.join(
    BASE, "_analysis_20260625", "_corpus_r94_ccb9398_residual_closure.json",
)
with open(lp(R94_RESIDUAL_LEDGER_PATH), encoding="utf-8") as _handle:
    R94_RESIDUAL_LEDGER = json.load(_handle)
if (
    R94_RESIDUAL_LEDGER.get("schema_version") != 1
    or R94_RESIDUAL_LEDGER.get("ledger_id")
    != "corpus-r94-ccb9398-ruby-residual-closure-v1"
):
    raise ValueError("invalid ccb9398 residual-closure ledger")
R94_RESIDUAL_POLICY = R94_RESIDUAL_LEDGER.get("policy", {})
if {
    "ruby_track_only": R94_RESIDUAL_POLICY.get("ruby_track_only"),
    "kanji_planned_changes": R94_RESIDUAL_POLICY.get("kanji_planned_changes"),
    "kanji_artifacts_must_remain_byte_identical": R94_RESIDUAL_POLICY.get(
        "kanji_artifacts_must_remain_byte_identical"
    ),
    "trilingual_boundary_identity_required": R94_RESIDUAL_POLICY.get(
        "trilingual_boundary_identity_required"
    ),
} != {
    "ruby_track_only": True,
    "kanji_planned_changes": 0,
    "kanji_artifacts_must_remain_byte_identical": True,
    "trilingual_boundary_identity_required": True,
}:
    raise ValueError("ccb9398 residual-closure track policy drift")
R94_STRICT_TRACK_PARTITIONS = R94_RESIDUAL_POLICY.get(
    "strict_track_partitions", {}
)


def curly_apostrophe_variant(value):
    """Return the exact U+2019 spelling of an ASCII-apostrophe value."""
    return value.replace("'", "’") if "'" in value else None


OUT = BASE + r"\_analysis_20260625\out"
BASE_SETTINGS_PATH = os.path.join(
    BASE, "_analysis_20260625", "_base_stemming_settings.json",
)
BASE_SETTINGS_MANIFEST_PATH = os.path.join(
    BASE, "_analysis_20260625", "_base_stemming_settings_manifest.json",
)
ATOMIC_ROOT_FAMILY_PATH = os.path.join(
    BASE, "_analysis_20260625", "localized_atomic_root_families.json",
)
with open(lp(ATOMIC_ROOT_FAMILY_PATH), encoding="utf-8") as _handle:
    ATOMIC_ROOT_FAMILY_REVIEW = json.load(_handle)
if ATOMIC_ROOT_FAMILY_REVIEW.get("schema_version") != 1:
    raise ValueError("unsupported localized atomic-root family schema")
_atomic_families = ATOMIC_ROOT_FAMILY_REVIEW.get("families", [])
_atomic_families_compact = json.dumps(
    _atomic_families, ensure_ascii=False, separators=(",", ":"),
).encode("utf-8")
if (
    ATOMIC_ROOT_FAMILY_REVIEW.get("learner_sha256")
    != "1435F5B1CD1B0BB8224521A8262E3CA740B07B7523E805545A4E3CA7447A286C"
    or ATOMIC_ROOT_FAMILY_REVIEW.get("academic_sha256")
    != "4C813C48B3C4919601FA51E25B6AA3628A0A6793A39C49F1DDFB22A9112E1A0A"
    or ATOMIC_ROOT_FAMILY_REVIEW.get("case_policy")
    != ["lower", "initial", "upper"]
    or len(_atomic_families)
    != ATOMIC_ROOT_FAMILY_REVIEW.get("expected_families")
    or sum(len(row.get("morph_targets", [])) for row in _atomic_families)
    != ATOMIC_ROOT_FAMILY_REVIEW.get("expected_morph_targets")
    or sum(len(row.get("authority", [])) for row in _atomic_families)
    != ATOMIC_ROOT_FAMILY_REVIEW.get("expected_authority_rows")
    or hashlib.sha256(_atomic_families_compact).hexdigest().upper()
    != ATOMIC_ROOT_FAMILY_REVIEW.get("families_sha256")
    or ATOMIC_ROOT_FAMILY_REVIEW.get("families_sha256")
    != "B047D6177321BC1E3B0C73D57B57A8B20EA79679E309AC8E3BCFBAABCF57BB61"
):
    raise ValueError("localized atomic-root family identity/count drift")
ATOMIC_ROOT_LEGACY_PREFIXES = []
for _family in _atomic_families:
    _legacy = tuple(_family.get("legacy_pieces", []))
    if not _legacy or "".join(_legacy) != _family.get("root"):
        raise ValueError(f"invalid localized atomic-root family: {_family!r}")
    if "lower" in _family.get("productive_left_cases", []):
        ATOMIC_ROOT_LEGACY_PREFIXES.append(_legacy)


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
# Ruby morphology must never learn productive boundaries from learner rows
# marked as fake/deep decomposition.  The line-paired academic snapshot is
# identical for ordinary rows and supplies the reviewed coarse decomposition
# for those fake rows, so it is the correct collision authority for this Ruby
# generator.  Kanji consumes the learner/deep track in its separate pipeline.
fake_reference_path=os.path.join(
    os.path.dirname(__file__), '_fake_coarse_reference_manifest.json',
)
with open(lp(fake_reference_path), encoding='utf-8') as _handle:
    fake_reference_manifest=json.load(_handle)
expected_academic=fake_reference_manifest.get('sources', {}).get('academic', {})
ACADEMIC_GOLD=os.environ.get('ESP_ACADEMIC_GOLD_PATH', '').strip()
if not ACADEMIC_GOLD:
    _learner_path=os.path.abspath(lp(GOLD))
    _academic_name=os.path.basename(_learner_path).replace(
        '学習者版', '学術版',
    )
    _academic_candidate=os.path.join(
        os.path.dirname(_learner_path), _academic_name,
    )
    if _academic_name == os.path.basename(_learner_path) or not os.path.exists(
        lp(_academic_candidate)
    ):
        raise SystemExit(
            'ESP_ACADEMIC_GOLD_PATH is required for coarse Ruby morphology'
        )
    ACADEMIC_GOLD=_academic_candidate
academic_raw, academic_identity=consistent_snapshot(lp(ACADEMIC_GOLD))
expected_academic_env=os.environ.get(
    'ESP_EXPECTED_ACADEMIC_SHA256', '',
).strip().upper()
if (
    not expected_academic
    or academic_identity['sha256'] != expected_academic.get('sha256')
    or academic_identity['bytes'] != expected_academic.get('bytes')
    or academic_identity['lines'] != expected_academic.get('lines')
    or academic_identity['lines'] != gold_identity['lines']
    or (
        expected_academic_env
        and academic_identity['sha256'] != expected_academic_env
    )
):
    raise RuntimeError(
        'academic Ruby authority mismatch: '
        f"got {academic_identity}, expected {expected_academic}"
    )
print(
    f"[academic Ruby authority] bytes={academic_identity['bytes']} "
    f"sha256={academic_identity['sha256']}",
    flush=True,
)
if PHASE532_FORMAL and (
    gold_identity['sha256'] != PHASE532_LEARNER_SHA256
    or academic_identity['sha256'] != PHASE532_ACADEMIC_SHA256
):
    raise ValueError(
        'Phase 532 managed Ruby policy requires its frozen learner/academic '
        'snapshot identities'
    )
for line in academic_raw.decode('utf-8').splitlines():
    if not line or line.startswith('##') or ':' not in line: continue
    for w in line.split(':')[0].split(' '):
        wc=_norm(w)
        if '#' in wc or not wc: continue
        ps=[p for p in wc.split('/') if p]
        if not ps: continue
        gold_map.setdefault(''.join(ps), ps)
# Coarse Ruby-authority root set.  A fake/deep learner row must not remove a
# lexical coarse root (etan, metan, ...), otherwise a short productive setting
# can silently invade it merely because the moving learner master was refined.
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
    or strict_fix_manifest.get('reference_schema_version') != 5
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
_phase532_superseded_strict = phase532_strict_supersessions()
_strict_by_word = {}
_phase532_present_supersessions = set()
for _entry in strict_gold_fixes:
    _strict_by_word.setdefault(_entry.get('w'), []).append(_entry)
for _word, _expected_entry in _phase532_superseded_strict.items():
    _matches = _strict_by_word.get(_word, [])
    if len(_matches) > 1:
        raise ValueError(
            f'duplicate Phase 532 superseded strict entry: {_word!r}'
        )
    if _matches and _matches[0] != _expected_entry:
        raise ValueError(
            f'Phase 532 superseded strict entry drift: {_matches[0]!r}'
        )
    if _matches:
        _phase532_present_supersessions.add(_word)
# The old atomic ``lulu`` pin remains active throughout Phase 513.  It is
# removed only after the activation gate proves one coherent adopted Phase
# 532 scope/strict/fake-manifest state.
if PHASE532_FORMAL:
    strict_gold_fixes = [
        entry for entry in strict_gold_fixes
        if entry.get('w') not in _phase532_superseded_strict
    ]
_phase558_superseded_strict = phase558_strict_supersessions()
_phase558_present_supersessions = set()
_strict_after_phase532_by_word = {}
for _entry in strict_gold_fixes:
    _strict_after_phase532_by_word.setdefault(_entry.get('w'), []).append(
        _entry
    )
for _word, _expected_entry in _phase558_superseded_strict.items():
    _matches = _strict_after_phase532_by_word.get(_word, [])
    if len(_matches) != 1 or _matches[0] != _expected_entry:
        raise ValueError(
            f'Phase 558 superseded strict entry missing/drifted: {_word!r}'
        )
    _phase558_present_supersessions.add(_word)
if PHASE558_FORMAL:
    strict_gold_fixes = [
        entry for entry in strict_gold_fixes
        if entry.get('w') not in _phase558_superseded_strict
    ]
if _phase558_present_supersessions != set(_phase558_superseded_strict):
    raise ValueError('Phase 558 strict supersession scope drift')
_r94_partitioned_strict = set()
_r94_effective_strict = []
for _entry in strict_gold_fixes:
    _word = _entry.get("w")
    _partition = R94_STRICT_TRACK_PARTITIONS.get(_word)
    if _partition is None:
        _r94_effective_strict.append(_entry)
        continue
    if _word in _r94_partitioned_strict:
        raise ValueError(f'duplicate R94 strict track partition: {_word!r}')
    if (
        set(_partition)
        != {
            "operation", "source_entry", "effective_entry", "ruby_target",
            "kanji_output_change",
        }
        or _partition.get("operation")
        != "retag_existing_strict_as_kanji_track_only"
        or _partition.get("kanji_output_change") is not False
        or _entry != _partition.get("source_entry")
        or _partition.get("effective_entry")
        != {**_entry, "kanji_track_only": True}
        or R94_RESIDUAL_POLICY.get("managed_morph_targets", {}).get(
            _word, {}
        ).get("target") != _partition.get("ruby_target")
        or normalize_esperanto_surface_notation(_word)
        != normalize_esperanto_surface_notation(
            str(_partition["ruby_target"]).replace("/", "")
        )
    ):
        raise ValueError(
            f'R94 strict track partition drift: {_word!r}: {_partition!r}'
        )
    _r94_effective_strict.append(_partition["effective_entry"])
    _r94_partitioned_strict.add(_word)
if _r94_partitioned_strict != set(R94_STRICT_TRACK_PARTITIONS):
    raise ValueError("R94 strict track partition source missing")
strict_gold_fixes = _r94_effective_strict
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
_strict_is_phase532 = (
    strict_fix_manifest.get('gold_sha256') == PHASE532_LEARNER_SHA256
)
if (
    _strict_is_phase532 != PHASE532_FORMAL
    or
    _strict_is_phase532
    and _phase532_present_supersessions
) or (
    not _strict_is_phase532
    and _phase532_present_supersessions != set(_phase532_superseded_strict)
):
    raise ValueError(
        'Phase 532 strict supersession state does not match pinned authority'
    )
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
    f"[strict gold] manifest_entries={strict_fix_manifest['expected_entries']} "
    f"effective_entries={len(strict_gold_fixes)} "
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
                    ruby_left_boundary=False, exact_only=False,
                    case_sensitive=False,
                    allow_substring=False, typed_roles=None,
                    context_annotation=None, ruby_context_annotation=None,
                    ruby_track_only=False, kanji_track_only=False,
                    ruby_only=False):
    """target分解→設定エントリ。屈折語尾はgold照合で生成:
      候補(名詞/形容詞/副詞語尾)のうち、stem+語尾がgoldに「別分解で」存在する形だけ除外。
      → 多品詞語根(esperant=名詞esperanto/形容詞esperanta/副詞esperante)の兄弟形を1項目から自動カバーしつつ、
        衝突(名詞tramet+i=gold tra/met/i、spontan+e=gold語根spontane)は回避。
      動詞形(verbo)は gold語尾がiか stem+iがgold整合の場合のみ付与。
    """
    pieces=[p for p in decomp.split('/') if p]
    if not pieces: return None
    if ruby_left_boundary and (boundary_only or boundary_with_noop_guard):
        raise ValueError("ruby_left_boundary conflicts with whole-word boundary")
    if ruby_left_boundary and not exact_only:
        raise ValueError("ruby_left_boundary requires an exact reviewed prefix")
    if typed_roles is not None:
        if not exact_only:
            raise ValueError("typed_roles requires exact_only")
        if len(typed_roles) != len(pieces) or any(role not in "RL" for role in typed_roles):
            raise ValueError(f"invalid typed_roles {typed_roles!r} for {decomp!r}")
    if context_annotation is not None and not isinstance(context_annotation, str):
        raise ValueError("context_annotation must be a reserved word_anno key")
    if (
        ruby_context_annotation is not None
        and not isinstance(ruby_context_annotation, str)
    ):
        raise ValueError(
            "ruby_context_annotation must be a reserved word_anno key"
        )
    if context_annotation is not None and ruby_context_annotation is not None:
        raise ValueError("context annotations are mutually exclusive")
    if ruby_track_only and kanji_track_only:
        raise ValueError(
            "ruby_track_only and kanji_track_only are mutually exclusive"
        )
    if ruby_only and (ruby_track_only or kanji_track_only):
        raise ValueError(
            "legacy ruby_only cannot be combined with track-only metadata"
        )
    if kanji_track_only and (
        ruby_left_boundary or ruby_context_annotation is not None
    ):
        raise ValueError(
            "kanji_track_only cannot carry Ruby-only boundary/context metadata"
        )
    if ruby_only and (not exact_only or typed_roles is None):
        raise ValueError("ruby_only requires an exact typed rule")
    nosl=''.join(pieces)
    last=pieces[-1]
    if exact_only:
        stem=decomp; stem_nosl=nosl
        suffixes=["ne"]
        if len(pieces) == 1:
            suffixes.append("atomic_no_split")
        if ruby_left_boundary:
            suffixes.append("ruby_left_boundary")
        elif boundary_only or boundary_with_noop_guard:
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
    if (
        not allow_substring
        and "word_boundary" not in suffixes
        and "ruby_left_boundary" not in suffixes
    ):
        suffixes.append("word_boundary")
    if case_sensitive:
        suffixes.append("case_sensitive")
    if typed_roles is not None:
        suffixes.append(f"typed_roles:{typed_roles}")
    if context_annotation is not None:
        suffixes.append(f"context_annotation:{context_annotation}")
    if ruby_context_annotation is not None:
        suffixes.append(
            f"ruby_context_annotation:{ruby_context_annotation}"
        )
    if ruby_track_only:
        suffixes.append("ruby_track_only")
    if kanji_track_only:
        suffixes.append("kanji_track_only")
    if ruby_only:
        suffixes.append("ruby_only")
    # Confirmed human adjudications must beat same-surface generated rules
    # (+5000 in gen_replacement) without crossing the next length tier.
    prio=confirmed_priority_for_stem(stem_nosl)
    if ruby_left_boundary:
        # A token-left proper-root rule must precede a same-stem reusable
        # compositional fallback (Bonaer vs bon/aer). One point stays inside
        # the same length tier while making the intended precedence explicit.
        prio += 1
    return {
        'stem': stem,
        'stem_nosl': stem_nosl,
        'prio': prio,
        'suffixes': suffixes,
        'word_nosl': nosl,
        'case_sensitive': case_sensitive,
        'exact_only': exact_only,
        'ruby_track_only': ruby_track_only,
        'kanji_track_only': kanji_track_only,
    }

# 同一語幹は語尾を和集合マージ(例 sugesti/o + sugesti/a + sugesti/i → 名詞+形容詞+動詞)
corrs={}
casefold_productive_stems={}
remove_nosl_casefold=set(); remove_nosl_exact_case=set()
exact_only_remove_nosl_casefold=set()
exact_only_remove_nosl_exact_case=set()
for e in confirmed:
    c=make_correction(
        e['target'],
        bool(e.get('boundary_only')),
        bool(e.get('boundary_with_noop_guard')),
        bool(e.get('ruby_left_boundary')),
        bool(e.get('exact_only')),
        bool(e.get('case_sensitive')),
        bool(e.get('allow_substring')),
        e.get('typed_roles'),
        e.get('context_annotation'),
        e.get('ruby_context_annotation'),
        bool(e.get('ruby_track_only')),
        bool(e.get('kanji_track_only')),
        bool(e.get('ruby_only')),
    )
    if not c: continue
    sn=c['stem_nosl']
    track_scope = (
        "ruby_track_only" if c["ruby_track_only"] else
        "kanji_track_only" if c["kanji_track_only"] else None
    )
    if not c['case_sensitive'] and not c['exact_only']:
        folded=sn.casefold()
        decomposition=tuple(
            piece.casefold() for piece in c['stem'].split('/') if piece
        )
        managed=bool(e.get('corpus_managed'))
        previous=casefold_productive_stems.setdefault(
            (track_scope or "shared", folded), {}
        )
        if previous and decomposition not in previous and (
            managed or any(previous.values())
        ):
            raise ValueError(
                "managed case-insensitive productive decomposition conflicts "
                f"for {folded!r}: {tuple(previous)!r} vs {decomposition!r}"
            )
        previous[decomposition]=previous.get(decomposition, False) or managed
    # A Ruby-left atomic root and its bounded known morphology intentionally
    # share slashless spelling but are separate rules. Merging their actions
    # would create an impossible left+whole-boundary hybrid.
    corr_key = (
        ("ruby_left_boundary", sn)
        if "ruby_left_boundary" in c["suffixes"] else sn
    )
    if e.get("localized_compositional"):
        corr_key = ("localized_compositional", sn)
    if track_scope is not None:
        corr_key = (track_scope, corr_key)
    if corr_key in corrs and corrs[corr_key]['stem']==c['stem']:
        ex=corrs[corr_key]
        for s in c['suffixes']:
            if s not in ex['suffixes']: ex['suffixes'].append(s)
        ex['prio']=max(ex['prio'], c['prio'])
    elif corr_key in corrs and track_scope is not None:
        raise ValueError(
            f"track-specific correction key collision: {corr_key!r}: "
            f"{corrs[corr_key]['stem']!r} vs {c['stem']!r}"
        )
    else:
        corrs[corr_key]=c
    # A case-sensitive proper name replaces only an old row with the same
    # written case.  Deleting its casefold sibling would erase legitimate
    # homographs (Sin must coexist with grammatical si/n; Kacumi with kacumi).
    if track_scope is not None:
        # Track-scoped rows must not delete shared pinned settings: the
        # opposite generator skips this row and still needs the common base.
        continue
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

_phase532_expected_corrections = {}
_phase532_safe_target_policy = (
    load_phase532_policy()['safe_targets'] if PHASE532_FORMAL else {}
)
_phase532_managed_items = (
    phase532_managed_morph_targets().items() if PHASE532_FORMAL else ()
)
for _surface, _spec in _phase532_managed_items:
    _ruby_track_only = bool(_spec.get('ruby_track_only'))
    _expected = make_correction(
        _spec['target'], ruby_track_only=_ruby_track_only,
    )
    if _expected is None:
        raise ValueError(
            f'Phase 532 managed correction is empty: {_surface!r}'
        )
    _reviewed_target = _phase532_safe_target_policy[_surface]
    if _reviewed_target['productive'] is False:
        if (
            _surface != 'lulu'
            or _expected['stem'] != 'lul/u'
            or set(_expected['suffixes']) != {'ne', 'word_boundary'}
        ):
            raise ValueError(
                f'Phase 532 fixed-form setting became productive: {_expected!r}'
            )
    elif (
        'ne' in _expected['suffixes']
        or 'word_boundary' not in _expected['suffixes']
        or not any(
            action in _expected['suffixes']
            for action in (*_NOMINAL, 'verbo_s1', 'verbo_s2')
        )
    ):
        raise ValueError(
            f'Phase 532 productive setting became fixed: {_expected!r}'
        )
    _expected_key = (
        ('ruby_track_only', _expected['stem_nosl'])
        if _ruby_track_only else _expected['stem_nosl']
    )
    if _expected['stem'] in _phase532_expected_corrections:
        raise ValueError(
            f'Phase 532 managed stem duplicated: {_expected["stem"]!r}'
        )
    _phase532_expected_corrections[_expected['stem']] = _expected
    _actual = corrs.get(_expected_key)
    if _actual != _expected:
        raise ValueError(
            'Phase 532 managed correction missing or merged: '
            f'{_surface!r}: expected={_expected!r}, got={_actual!r}'
        )

_phase558_expected_corrections = {}
_phase558_managed_items = (
    phase558_managed_morph_targets().items() if PHASE558_FORMAL else ()
)
for _surface, _spec in _phase558_managed_items:
    _context_key = _spec.get('ruby_context_annotation')
    _expected = make_correction(
        _spec['target'], ruby_track_only=True,
        ruby_context_annotation=_context_key,
    )
    if (
        _expected is None
        or 'ne' in _expected['suffixes']
        or 'word_boundary' not in _expected['suffixes']
        or 'ruby_track_only' not in _expected['suffixes']
        or f'ruby_context_annotation:{_context_key}'
        not in _expected['suffixes']
        or not set(_NOMINAL) & set(_expected['suffixes'])
    ):
        raise ValueError(
            f'Phase 558 managed correction lost its bounded Ruby scope: '
            f'{_surface!r}: {_expected!r}'
        )
    _expected_key = ('ruby_track_only', _expected['stem_nosl'])
    if (
        _expected['stem'] in _phase558_expected_corrections
        or _expected['stem'] in _phase532_expected_corrections
    ):
        raise ValueError(
            f'Phase 558 managed stem duplicated: {_expected["stem"]!r}'
        )
    _phase558_expected_corrections[_expected['stem']] = _expected
    _actual = corrs.get(_expected_key)
    if _actual != _expected:
        raise ValueError(
            'Phase 558 managed correction missing or merged: '
            f'{_surface!r}: expected={_expected!r}, got={_actual!r}'
        )

_phase598_expected_corrections = {}
_phase598_managed_items = (
    phase598_managed_morph_targets().items() if PHASE598_FORMAL else ()
)
for _surface, _spec in _phase598_managed_items:
    _context_key = _spec.get('ruby_context_annotation')
    _expected = make_correction(
        _spec['target'], ruby_track_only=True,
        ruby_context_annotation=_context_key,
    )
    if (
        _expected is None
        or 'ne' in _expected['suffixes']
        or 'word_boundary' not in _expected['suffixes']
        or 'ruby_track_only' not in _expected['suffixes']
        or f'ruby_context_annotation:{_context_key}'
        not in _expected['suffixes']
        or set(_NOMINAL) - set(_expected['suffixes'])
    ):
        raise ValueError(
            f'Phase 598 managed correction lost its complete bounded Ruby '
            f'scope: {_surface!r}: {_expected!r}'
        )
    _expected_key = ('ruby_track_only', _expected['stem_nosl'])
    if (
        _expected['stem'] in _phase598_expected_corrections
        or _expected['stem'] in _phase558_expected_corrections
        or _expected['stem'] in _phase532_expected_corrections
    ):
        raise ValueError(
            f'Phase 598 managed stem duplicated: {_expected["stem"]!r}'
        )
    _phase598_expected_corrections[_expected['stem']] = _expected
    _actual = corrs.get(_expected_key)
    if _actual != _expected:
        raise ValueError(
            'Phase 598 managed correction missing or merged: '
            f'{_surface!r}: expected={_expected!r}, got={_actual!r}'
        )

_phase619_expected_corrections = {}
_phase619_managed_items = (
    phase619_managed_morph_targets().items() if PHASE619_FORMAL else ()
)
for _surface, _spec in _phase619_managed_items:
    _context_key = _spec.get('ruby_context_annotation')
    _expected = make_correction(
        _spec['target'], ruby_track_only=True,
        ruby_context_annotation=_context_key,
    )
    _required_actions = set(_NOMINAL) | {
        'word_boundary', 'ruby_track_only',
    }
    if _context_key is not None:
        _required_actions.add(
            f'ruby_context_annotation:{_context_key}'
        )
    if (
        _expected is None
        or set(_expected['suffixes']) != _required_actions
    ):
        raise ValueError(
            f'Phase 619 ordinary correction lost its complete bounded '
            f'Ruby scope: {_surface!r}: {_expected!r}'
        )
    _expected_key = ('ruby_track_only', _expected['stem_nosl'])
    if (
        _expected['stem'] in _phase619_expected_corrections
        or _expected['stem'] in _phase598_expected_corrections
        or _expected['stem'] in _phase558_expected_corrections
        or _expected['stem'] in _phase532_expected_corrections
    ):
        raise ValueError(
            f'Phase 619 managed stem duplicated: {_expected["stem"]!r}'
        )
    _phase619_expected_corrections[_expected['stem']] = _expected
    _actual = corrs.get(_expected_key)
    if _actual != _expected:
        raise ValueError(
            'Phase 619 managed correction missing or merged: '
            f'{_surface!r}: expected={_expected!r}, got={_actual!r}'
        )

_r94_expected_corrections = {}
_r94_managed_items = R94_RESIDUAL_POLICY.get("managed_morph_targets", {}).items()
for _surface, _spec in _r94_managed_items:
    if set(_spec) != {"target", "ruby_track_only"} or _spec.get(
        "ruby_track_only"
    ) is not True:
        raise ValueError(
            f'R94 managed morphology lost its Ruby-only policy: '
            f'{_surface!r}: {_spec!r}'
        )
    _expected = make_correction(_spec["target"], ruby_track_only=True)
    if (
        _expected is None
        or not _expected["ruby_track_only"]
        or _expected["kanji_track_only"]
        or "word_boundary" not in _expected["suffixes"]
        or "ruby_track_only" not in _expected["suffixes"]
        or "kanji_track_only" in _expected["suffixes"]
        or "ruby_only" in _expected["suffixes"]
    ):
        raise ValueError(
            f'R94 managed correction lost its bounded Ruby scope: '
            f'{_surface!r}: {_expected!r}'
        )
    _expected_key = ("ruby_track_only", _expected["stem_nosl"])
    if (
        _expected["stem"] in _r94_expected_corrections
        or _expected["stem"] in _phase619_expected_corrections
        or _expected["stem"] in _phase598_expected_corrections
        or _expected["stem"] in _phase558_expected_corrections
        or _expected["stem"] in _phase532_expected_corrections
    ):
        raise ValueError(
            f'R94 managed stem duplicated: {_expected["stem"]!r}'
        )
    _r94_expected_corrections[_expected["stem"]] = _expected
    _actual = corrs.get(_expected_key)
    if _actual != _expected:
        raise ValueError(
            'R94 managed correction missing or merged: '
            f'{_surface!r}: expected={_expected!r}, got={_actual!r}'
        )

_r94_expected_kanji_corrections = {}
for _surface, _partition in R94_STRICT_TRACK_PARTITIONS.items():
    _entry = _partition["effective_entry"]
    _expected = make_correction(
        _entry["target"],
        boundary_only=bool(_entry.get("boundary_only")),
        exact_only=bool(_entry.get("exact_only")),
        case_sensitive=bool(_entry.get("case_sensitive")),
        typed_roles=_entry.get("typed_roles"),
        kanji_track_only=bool(_entry.get("kanji_track_only")),
    )
    if (
        _expected is None
        or _expected["ruby_track_only"]
        or not _expected["kanji_track_only"]
        or set(_expected["suffixes"])
        != {
            "ne", "word_boundary", "case_sensitive",
            f'typed_roles:{_entry["typed_roles"]}', "kanji_track_only",
        }
    ):
        raise ValueError(
            f'R94 Kanji preservation correction lost exact deep scope: '
            f'{_surface!r}: {_expected!r}'
        )
    _expected_key = ("kanji_track_only", _expected["stem_nosl"])
    if _expected["stem"] in _r94_expected_kanji_corrections:
        raise ValueError(
            f'R94 Kanji preservation stem duplicated: {_expected["stem"]!r}'
        )
    _r94_expected_kanji_corrections[_expected["stem"]] = _expected
    _actual = corrs.get(_expected_key)
    if _actual != _expected:
        raise ValueError(
            'R94 Kanji preservation correction missing or merged: '
            f'{_surface!r}: expected={_expected!r}, got={_actual!r}'
        )

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

WORD_ANNO_BOUNDARY_MANIFEST_PATH = os.path.join(
    BASE, "_analysis_20260625", "_word_anno_boundary_scope_manifest.json",
)
with open(lp(WORD_ANNO_BOUNDARY_MANIFEST_PATH), encoding="utf-8") as handle:
    WORD_ANNO_BOUNDARY_MANIFEST = json.load(handle)
WORD_ANNO_BY_LANGUAGE = {}
for _language in WORD_ANNO_BOUNDARY_MANIFEST.get("languages", []):
    with open(lp(OUT + f"\\word_anno_{_language}.json"), encoding="utf-8") as handle:
        WORD_ANNO_BY_LANGUAGE[_language] = json.load(handle)
WORD_ANNO_BOUNDARY_AUTHORITY = validate_multilingual_word_anno_boundaries(
    WORD_ANNO_BY_LANGUAGE,
    WORD_ANNO_BOUNDARY_MANIFEST,
)
print(
    "[word_anno boundary] "
    f"authority_keys={len(WORD_ANNO_BOUNDARY_AUTHORITY)} "
    f"sha256={WORD_ANNO_BOUNDARY_MANIFEST['authority_sha256']}",
    flush=True,
)


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
    # Remove stale settings whose leading pieces spell a root reviewed as
    # atomic in lowercase (nov/jork...). Bonaer is intentionally excluded:
    # its learner-authoritative bon/aer composition must remain reusable in
    # lowercase and token-internal forms.
    filtered=[]
    for row in settings:
        if not isinstance(row, list) or len(row) != 3:
            filtered.append(row)
            continue
        pieces=tuple(piece for piece in str(row[0]).split('/') if piece)
        if any(
            pieces[:len(prefix)] == prefix
            for prefix in ATOMIC_ROOT_LEGACY_PREFIXES
        ):
            removed += 1
            continue
        filtered.append(row)
    settings=filtered
    for sn,c in corrs.items():
        settings.append([c['stem'], c['prio'], list(c['suffixes'])])
    _ruby_left_rows = [
        row for row in settings
        if isinstance(row, list) and len(row) == 3
        and 'ruby_left_boundary' in row[2]
    ]
    _ruby_left_actions = {row[0]: set(row[2]) for row in _ruby_left_rows}
    if _ruby_left_actions != {
        'Bonaer': {
            'ne', 'atomic_no_split', 'ruby_left_boundary', 'case_sensitive',
            'ruby_context_annotation:@atomic-family:Bonaer',
        },
        'BONAER': {
            'ne', 'atomic_no_split', 'ruby_left_boundary', 'case_sensitive',
            'ruby_context_annotation:@atomic-family:BONAER',
        },
        'novjork': {'ne', 'atomic_no_split', 'ruby_left_boundary'},
    }:
        raise ValueError(f'Ruby-left family settings drift: {_ruby_left_rows!r}')
    _novjork_rows = [
        row for row in settings
        if isinstance(row, list) and len(row) == 3
        and str(row[0]).casefold() in {'novjork', 'novjork/an'}
    ]
    _novjork_left = [
        row for row in _novjork_rows
        if 'ruby_left_boundary' in row[2]
    ]
    _novjork_morph = [
        row for row in _novjork_rows
        if row[0] == 'novjork/an'
        and 'word_boundary' in row[2]
        and 'ruby_track_only' in row[2]
        and any(action in row[2] for action in _NOMINAL)
    ]
    _novjork_shared_morph = [
        row for row in _novjork_rows
        if row[0] == 'novjork'
        if 'word_boundary' in row[2]
        and 'ruby_track_only' not in row[2]
        and 'kanji_track_only' not in row[2]
        and any(action in row[2] for action in _NOMINAL)
    ]
    if (
        len(_novjork_left) != 1
        or set(_novjork_left[0][2])
        != {'ne', 'atomic_no_split', 'ruby_left_boundary'}
        or len(_novjork_morph) != 1
        or len(_novjork_shared_morph) != 1
        or any(
            'ruby_left_boundary' in row[2] and 'word_boundary' in row[2]
            for row in _novjork_rows
        )
    ):
        raise ValueError(
            f'Novjork Ruby-left/morph settings collapsed: {_novjork_rows!r}'
        )
    _bonaer_rows = [
        row for row in settings
        if isinstance(row, list) and len(row) == 3
        and str(row[0]).replace('/', '').casefold() == 'bonaer'
    ]
    _bonaer_compositional = [
        row for row in _bonaer_rows
        if row[0] == 'bon/aer' and set(row[2]) == {'ne'}
    ]
    _bonaer_morph = [
        row for row in _bonaer_rows
        if row[0] == 'bonaer'
        and 'word_boundary' in row[2]
        and 'ruby_context_annotation:@atomic-family:bonaer' in row[2]
        and any(action in row[2] for action in _NOMINAL)
    ]
    _bonaer_left = [
        row for row in _bonaer_rows if 'ruby_left_boundary' in row[2]
    ]
    if (
        len(_bonaer_compositional) != 1
        or len(_bonaer_morph) != 1
        or 'ruby_track_only' in _bonaer_morph[0][2]
        or 'kanji_track_only' in _bonaer_morph[0][2]
        or len(_bonaer_left) != 2
        or min(row[1] for row in _bonaer_left)
        <= _bonaer_compositional[0][1]
    ):
        raise ValueError(
            f'Bonaer compositional/atomic ordering drift: {_bonaer_rows!r}'
        )
    _ruby_track_rows = [
        row for row in settings
        if isinstance(row, list) and len(row) == 3
        and 'ruby_track_only' in row[2]
    ]
    _strict_ruby_track_entries = {
        entry['target']: entry
        for entry in strict_gold_fixes
        if entry.get('ruby_track_only')
    }
    _expected_ruby_track_stems = {
        'novjork/an', *_strict_ruby_track_entries,
        *(
            stem for stem, expected in _phase532_expected_corrections.items()
            if expected['ruby_track_only']
        ),
        *_phase558_expected_corrections,
        *_phase598_expected_corrections,
        *_phase619_expected_corrections,
        *_r94_expected_corrections,
    }
    if (
        {row[0] for row in _ruby_track_rows}
        != _expected_ruby_track_stems
        or len(_ruby_track_rows) != len(_expected_ruby_track_stems)
    ):
        raise ValueError(
            f'localized Ruby-track morphology drift: {_ruby_track_rows!r}'
        )
    for _row in _ruby_track_rows:
        if _row[0] == 'novjork/an':
            _expected_actions = set(_NOMINAL) | {
                'word_boundary', 'ruby_track_only',
            }
        elif _row[0] in _phase532_expected_corrections:
            _expected_actions = set(
                _phase532_expected_corrections[_row[0]]['suffixes']
            )
        elif _row[0] in _phase558_expected_corrections:
            _expected_actions = set(
                _phase558_expected_corrections[_row[0]]['suffixes']
            )
        elif _row[0] in _phase598_expected_corrections:
            _expected_actions = set(
                _phase598_expected_corrections[_row[0]]['suffixes']
            )
        elif _row[0] in _phase619_expected_corrections:
            _expected_actions = set(
                _phase619_expected_corrections[_row[0]]['suffixes']
            )
        elif _row[0] in _r94_expected_corrections:
            _expected_actions = set(
                _r94_expected_corrections[_row[0]]["suffixes"]
            )
        else:
            _entry = _strict_ruby_track_entries[_row[0]]
            _expected_actions = {
                'ne', 'word_boundary', 'case_sensitive',
                f"typed_roles:{_entry['typed_roles']}", 'ruby_track_only',
            }
            if len([part for part in _row[0].split('/') if part]) == 1:
                # A one-piece exact Ruby target is represented by the same
                # fail-closed atomic marker used by other no-split settings.
                # Derive this from the reviewed target instead of naming an
                # individual surface such as deoksi.
                _expected_actions.add('atomic_no_split')
        if set(_row[2]) != _expected_actions:
            raise ValueError(
                f'localized Ruby-track action drift: {_row!r}'
            )
    _kanji_track_rows = [
        row for row in settings
        if isinstance(row, list) and len(row) == 3
        and 'kanji_track_only' in row[2]
    ]
    _expected_kanji_track_rows = {
        'pro/mil': set(_NOMINAL) | {
            'word_boundary', 'kanji_track_only',
        },
        **{
            stem: set(expected["suffixes"])
            for stem, expected in _r94_expected_kanji_corrections.items()
        },
    }
    _actual_kanji_track_rows = {
        row[0]: set(row[2]) for row in _kanji_track_rows
    }
    if (
        len(_actual_kanji_track_rows) != len(_kanji_track_rows)
        or _actual_kanji_track_rows != _expected_kanji_track_rows
    ):
        raise ValueError(
            f'Kanji-track morphology drift: {_kanji_track_rows!r}'
        )
    _ruby_only_rows = [
        row for row in settings
        if isinstance(row, list) and len(row) == 3 and 'ruby_only' in row[2]
    ]
    _expected_ruby_only_rows = {
        'promil/o': {
            'ne', 'word_boundary', 'case_sensitive',
            'typed_roles:RL', 'ruby_only',
        },
    }
    if PHASE558_FORMAL:
        for _surface, _spec in phase558_typed_exact_targets().items():
            _expected_ruby_only_rows[_spec['target']] = {
                'ne', 'word_boundary', 'case_sensitive',
                f"typed_roles:{_spec['typed_roles']}", 'ruby_only',
            }
    if PHASE598_FORMAL:
        for _surface, _spec in phase598_typed_exact_targets().items():
            _expected_ruby_only_rows[_spec['target']] = {
                'ne', 'word_boundary', 'case_sensitive',
                f"typed_roles:{_spec['typed_roles']}", 'ruby_only',
            }
    for _surface, _spec in R94_RESIDUAL_POLICY.get(
        "managed_typed_exact_targets", {}
    ).items():
        if (
            set(_spec)
            != {"target", "typed_roles", "case_sensitive", "ruby_only"}
            or _spec.get("case_sensitive") is not True
            or _spec.get("ruby_only") is not True
            or normalize_esperanto_surface_notation(_surface)
            != normalize_esperanto_surface_notation(
                str(_spec.get("target", "")).replace("/", "")
            )
        ):
            raise ValueError(
                f'R94 typed-exact policy drift: {_surface!r}: {_spec!r}'
            )
        _variants = [(_surface, _spec["target"])]
        _curly_surface = curly_apostrophe_variant(_surface)
        if _curly_surface is not None:
            _variants.append((
                _curly_surface,
                curly_apostrophe_variant(_spec["target"])
                or _spec["target"],
            ))
        for _variant_surface, _target in _variants:
            if normalize_esperanto_surface_notation(_variant_surface) != (
                normalize_esperanto_surface_notation(
                    _target.replace("/", "")
                )
            ):
                raise ValueError(
                    "R94 apostrophe variant reconstruction drift: "
                    f"{_variant_surface!r} -> {_target!r}"
                )
            if _target in _expected_ruby_only_rows:
                raise ValueError(
                    f'R94 typed-exact target duplicated: {_target!r}'
                )
            _actions = {
                "ne", "word_boundary", "case_sensitive",
                f'typed_roles:{_spec["typed_roles"]}', "ruby_only",
            }
            if len([part for part in _target.split("/") if part]) == 1:
                _actions.add("atomic_no_split")
            _expected_ruby_only_rows[_target] = _actions
    _actual_ruby_only_rows = {
        row[0]: set(row[2]) for row in _ruby_only_rows
    }
    if (
        len(_actual_ruby_only_rows) != len(_ruby_only_rows)
        or _actual_ruby_only_rows != _expected_ruby_only_rows
        or any(
            'ruby_only' in row[2]
            and (
                'ruby_track_only' in row[2]
                or 'kanji_track_only' in row[2]
            )
            for row in settings
            if isinstance(row, list) and len(row) == 3
        )
        or any(
            'ruby_track_only' in row[2] and 'kanji_track_only' in row[2]
            for row in settings
            if isinstance(row, list) and len(row) == 3
        )
    ):
        raise ValueError(
            f'Ruby-only exact setting drift: {_ruby_only_rows!r}'
        )
    return settings, removed

def prepare_candidate(key):
    d,csvn,lang=APPS[key]; APPDIR=BASE+d; DATA=APPDIR+r"\app_data"
    sp=DATA+STEM
    # The morphology settings are language-independent.  Always rebuild from
    # one pinned base instead of reading a per-app rollback backup: an older ZH
    # backup had already absorbed generated word_boundary rows and produced a
    # different global key set.  Keep only the localized explanatory header.
    settings, removed = prepare_settings(sp)
    tmp=DATA+r"\_settings_confirmed_tmp.json"
    try:
        with open(lp(tmp),'w',encoding='utf-8') as g:
            json.dump(settings,g,ensure_ascii=False,indent=1)
        word_anno=WORD_ANNO_BY_LANGUAGE[lang]
        combined=generate(
            APPDIR,DATA,DATA+csvn,tmp,DATA+USER,DATA+ESTEM,DATA+ROOTS,
            FMT,word_anno=word_anno,
        )
    finally:
        if os.path.exists(lp(tmp)):
            os.remove(lp(tmp))
    return {
        'key': key, 'settings_path': sp, 'data_dir': DATA,
        'settings': settings, 'combined': combined, 'removed': removed,
    }


def write_prepared_candidate(prepared):
    key=prepared['key']; sp=prepared['settings_path']
    DATA=prepared['data_dir']; settings=prepared['settings']
    combined=prepared['combined']; removed=prepared['removed']
    atomic_file_copy(lp(sp), lp(sp+".bak_preTier"+str(TIER)+"confirmed"))
    atomic_json_dump(sp, settings, indent=1)
    # 大JSONはリポジトリの正規形(改行なし)で保存。
    # pretty-print は数百万行の無意味な diff と中間失敗時の肥大化を生む。
    atomic_json_dump(DATA+FINAL, combined)
    print(f"  [{key}] 除去{removed} 追加{len(corrs)} → 書込完了")


def write_all_prepared_candidates(prepared_by_key, *, replace=os.replace):
    """Stage all six files, then replace them with rollback-on-error.

    A filesystem cannot atomically rename files across the three app
    directories.  Staging every settings/payload file before the first
    replace and retaining same-directory rollback copies nevertheless avoids
    the ordinary partial-write failure mode.  Persisted three-language gates
    still run after the separate post-regeneration fixer.
    """
    if set(prepared_by_key) != {'ZH', 'KO', 'JP'}:
        raise ValueError('three-language prepared candidate scope drift')
    staged = []
    rollbacks = []
    replaced = []
    try:
        for key in ('ZH', 'KO', 'JP'):
            prepared = prepared_by_key[key]
            settings_path = lp(prepared['settings_path'])
            payload_path = lp(prepared['data_dir'] + FINAL)
            rows = (
                (settings_path, prepared['settings'], 1, 'settings'),
                (payload_path, prepared['combined'], None, 'payload'),
            )
            for destination, value, indent, label in rows:
                stage = destination + '.phase558_staged'
                rollback = destination + '.phase558_rollback'
                if os.path.exists(stage) or os.path.exists(rollback):
                    raise ValueError(
                        f'stale Phase 558 transaction file: {destination}'
                    )
                # Register the path before writing so even a failed/partial
                # stage dump is removed by the transaction cleanup below.
                staged.append((stage, destination, key, label))
                atomic_json_dump(stage, value, indent=indent)
                with open(stage, encoding='utf-8') as staged_stream:
                    staged_value = json.load(staged_stream)
                    # ``generate`` may retain tuples in memory whereas JSON
                    # necessarily restores them as arrays/lists.  Compare the
                    # canonical JSON meaning, not Python container types.
                    encoder = json.JSONEncoder(
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(',', ':'),
                    )
                    expected_hash = hashlib.sha256()
                    staged_hash = hashlib.sha256()
                    for chunk in encoder.iterencode(value):
                        expected_hash.update(chunk.encode('utf-8'))
                    for chunk in encoder.iterencode(staged_value):
                        staged_hash.update(chunk.encode('utf-8'))
                    if staged_hash.digest() != expected_hash.digest():
                        raise ValueError(
                            f'Phase 558 staged JSON drift: {destination}'
                        )
                    del staged_value
                rollbacks.append((rollback, destination))
                # Register the rollback path before the copy.  The durable
                # copy replaces its target before performing the final size
                # check, so a post-replace validation error must still leave
                # the artifact inside this transaction's cleanup scope.
                atomic_binary_copy(destination, rollback)
            atomic_file_copy(
                settings_path,
                settings_path + '.bak_preTier' + str(TIER) + 'confirmed',
            )
        for stage, destination, _key, _label in staged:
            replace(stage, destination)
            replaced.append(destination)
    except Exception:
        rollback_errors = []
        for rollback, destination in rollbacks:
            try:
                if destination in replaced and os.path.exists(rollback):
                    replace(rollback, destination)
                elif os.path.exists(rollback):
                    os.remove(rollback)
            except Exception as error:
                rollback_errors.append((destination, repr(error)))
        for stage, _destination, _key, _label in staged:
            if os.path.exists(stage):
                os.remove(stage)
        if rollback_errors:
            raise RuntimeError(
                f'Phase 558 three-language rollback failed: {rollback_errors!r}'
            )
        raise
    else:
        for rollback, _destination in rollbacks:
            if os.path.exists(rollback):
                os.remove(rollback)
        for key in ('ZH', 'KO', 'JP'):
            prepared = prepared_by_key[key]
            print(
                f"  [{key}] 除去{prepared['removed']} 追加{len(corrs)} "
                "→ 三言語transaction書込完了"
            )


def process(key, write):
    prepared=prepare_candidate(key)
    if write:
        write_prepared_candidate(prepared)
    else:
        print(
            f"  [{key}] 除去{prepared['removed']} 追加{len(corrs)} (未書込)"
        )
    return prepared['combined']


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
    # ``combined`` is a full multi-million-rule payload.  A WRITE invocation
    # subsequently holds three candidates until their cross-language gate has
    # passed, so release this optional JP preview and its list aliases first.
    del segplain, g_, l_, c_, combined
    gc.collect()
if WRITE:
    # Build all three payloads in memory first.  No settings or generated Ruby
    # JSON is written until the frozen 58-row Phase 532 post-regen gate proves
    # exact JA/ZH/KO signatures, including the dedicated multiword expression.
    _prepared_candidates = {
        key: prepare_candidate(key) for key in ('ZH', 'KO', 'JP')
    }
    if PHASE532_FORMAL:
        _phase532_runtime_report = validate_generated_payloads({
            'JA': _prepared_candidates['JP']['combined'],
            'ZH': _prepared_candidates['ZH']['combined'],
            'KO': _prepared_candidates['KO']['combined'],
        }, 'post-regen')
        print(
            "[Phase 532 runtime gate] PASS: "
            f"surfaces={_phase532_runtime_report['surfaces']} "
            f"3lang_mismatch="
            f"{_phase532_runtime_report['trilingual_mismatches']} "
            f"signature_sha256="
            f"{_phase532_runtime_report['signature_manifest_sha256']}",
            flush=True,
        )
    if PHASE558_FORMAL:
        _phase558_runtime_report = validate_phase558_generated_payloads({
            'JA': _prepared_candidates['JP']['combined'],
            'ZH': _prepared_candidates['ZH']['combined'],
            'KO': _prepared_candidates['KO']['combined'],
        }, 'post-regen')
        print(
            "[Phase 558 Ruby overlay runtime gate] PASS: "
            f"surfaces={_phase558_runtime_report['surfaces']} "
            f"3lang_mismatch="
            f"{_phase558_runtime_report['trilingual_mismatches']} "
            f"signature_sha256="
            f"{_phase558_runtime_report['signature_manifest_sha256']}",
            flush=True,
        )
    if PHASE598_FORMAL:
        _phase598_runtime_report = validate_phase598_generated_payloads({
            'JA': _prepared_candidates['JP']['combined'],
            'ZH': _prepared_candidates['ZH']['combined'],
            'KO': _prepared_candidates['KO']['combined'],
        })
        print(
            "[Phase 598 technical-on runtime gate] PASS: "
            f"positive={_phase598_runtime_report['positive_surfaces']} "
            f"negative={_phase598_runtime_report['negative_surfaces']} "
            f"combined={_phase598_runtime_report['combined_surfaces']} "
            f"3lang_mismatch="
            f"{_phase598_runtime_report['trilingual_boundary_mismatches']} "
            f"width_max="
            f"{max(_phase598_runtime_report['max_effective_width_ratio'].values()):.6f}",
            flush=True,
        )
    if PHASE619_FORMAL:
        _phase619_runtime_report = validate_phase619_generated_payloads({
            'JA': _prepared_candidates['JP']['combined'],
            'ZH': _prepared_candidates['ZH']['combined'],
            'KO': _prepared_candidates['KO']['combined'],
        })
        print(
            "[Phase 619 ordinary Ruby runtime gate] PASS: "
            f"positive={_phase619_runtime_report['positive_surfaces']} "
            f"negative={_phase619_runtime_report['negative_surfaces']} "
            f"combined={_phase619_runtime_report['combined_surfaces']} "
            f"3lang_mismatch="
            f"{_phase619_runtime_report['trilingual_boundary_mismatches']} "
            f"width_max="
            f"{max(_phase619_runtime_report['max_effective_width_ratio'].values()):.6f}",
            flush=True,
        )
    write_all_prepared_candidates(_prepared_candidates)
    print("\n3アプリ書込完了")
