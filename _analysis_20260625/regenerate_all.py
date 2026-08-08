# -*- coding: utf-8 -*-
"""道B: 大JSON一括再生成 (正式ルート)

使い方:
  python regenerate_all.py --ruby-only
  python regenerate_all.py --all-tracks
  1. 偽分解・corpus・Phase532/558/619の固定authorityを検証
  2. Phase532/558/598/619 pre-gate後にRuby 3言語を一括再生成
  3. R67/R68復元と4つの事後層を経て572,771行をpost-gate
  4. canonical 21,438表層・apostrophe・構造・回帰を検査
  5. Phase619 learnerとword_kanjiのdirect-key coverageを限定監査
  6. 固定62,313行を3言語で正式全量監査
  7. --all-tracksだけ漢字正本再同期・漢字生成・pure導出・.bak掃除

track modeは必須である。--ruby-onlyは漢字書込工程を実行せず、
配備済み漢字成果物9本が各工程の前後で不変であることをSHA-256で監視する。
--all-tracksだけが固定漢字マスターから漢字成果物を再構築する。

外部マスターが必要な工程は環境変数で場所を指定できる(既定は作者環境):
  ESP_GOLD_PATH          … 学習者版マスター辞書(62k行)
  ESP_ACADEMIC_GOLD_PATH … 同じ行に対応する学術版マスター辞書
  ESP_PEJVO_ORIGINAL_PATH … 固定した原典PEJVO snapshot
  ESP_KANJI_MASTER_PATH  … 漢字割り当てマスター
  ESP_CORPUS_PATH        … 固定exact manifestの元になったcleanな京大HTML repo
  ESP_PHASE619_CANDIDATE_DIR … 固定Phase619入力一式
  ESP_PHASE619_RUBY_HTML_GUIDE_JA/ZH … 現行京大HTML修正ガイド
"""
import argparse, hashlib, json, subprocess, sys, os, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from gold_snapshot import consistent_snapshot
import build_phase532_authority_carry_forward as phase532_carry_builder
import build_phase532_ruby_policy_review as phase532_policy_builder
import build_phase558_ruby_overlay_review as phase558_overlay_builder
import phase532_activation
import phase532_authority_carry_forward as phase532_carry
import phase532_ruby_policy as phase532_policy
import phase558_ruby_overlay as phase558_overlay
import phase558_ruby_overlay_activation as phase558_activation
import phase598_technical_on_policy as phase598_policy
import phase598_technical_on_activation as phase598_activation
import build_phase619_ordinary_ruby_review as phase619_review_builder
import phase619_ordinary_ruby_policy as phase619_policy
import phase619_ordinary_ruby_activation as phase619_activation


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--ruby-only",
        action="store_true",
        help="regenerate and verify Ruby assets without writing Kanji assets",
    )
    mode.add_argument(
        "--all-tracks",
        action="store_true",
        help="explicitly regenerate both Ruby and Kanji assets",
    )
    return parser.parse_args(argv)


ARGS = parse_args()

KANJI_CANDIDATE_ACK = "ESP_ALLOW_UNREVIEWED_KANJI_CANDIDATE"
if ARGS.all_tracks and os.environ.get(KANJI_CANDIDATE_ACK) != "1":
    raise SystemExit(
        "all-tracks is candidate-only until the reviewed Phase511 21-row "
        "Kanji authority gate exists; run only in an isolated worktree and "
        f"set {KANJI_CANDIDATE_ACK}=1 explicitly"
    )

KANJI_PROTECTED_PATHS = (
    "Esperanto-Kanji-Ruby-JA/app_data/世界语词根-汉字对应列表_参照2新割当_7791.csv",
    "Esperanto-Kanji-Ruby-ZH/app_data/世界语词根-汉字对应列表_参照2新割当_7791.csv",
    "Esperanto-Kanji-Ruby-KO/app_data/世界语词根-汉字对应列表_参照2新割当_7791.csv",
    "Esperanto-Kanji-Ruby-JA/app_data/置換リスト_漢字.json",
    "Esperanto-Kanji-Ruby-ZH/app_data/置換リスト_漢字.json",
    "Esperanto-Kanji-Ruby-KO/app_data/置換リスト_漢字.json",
    "Esperanto-Kanji-Ruby-JA/app_data/置換リスト_漢字_純粋置換.json",
    "_analysis_20260625/out/kanji_root.csv",
    "_analysis_20260625/out/word_kanji.json",
)


def _kanji_artifact_fingerprints():
    fingerprints = {}
    for relative in KANJI_PROTECTED_PATHS:
        path = os.path.join(REPO_ROOT, *relative.split("/"))
        try:
            with open(path, "rb") as handle:
                raw = handle.read()
        except OSError as error:
            raise SystemExit(
                f"Ruby-only Kanji guard cannot read {relative}: {error}"
            ) from error
        fingerprints[relative] = {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest().upper(),
        }
    return fingerprints


def _capture_ruby_only_kanji_guard():
    clean = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *KANJI_PROTECTED_PATHS],
        cwd=REPO_ROOT,
        check=False,
    )
    if clean.returncode != 0:
        raise SystemExit(
            "Ruby-only regeneration requires all 9 protected Kanji artifacts "
            "to match HEAD before the first write"
        )
    return _kanji_artifact_fingerprints()


def _assert_ruby_only_kanji_guard(expected, completed_step):
    actual = _kanji_artifact_fingerprints()
    changed = [
        relative for relative in KANJI_PROTECTED_PATHS
        if actual[relative] != expected[relative]
    ]
    if changed:
        raise SystemExit(
            "Ruby-only regeneration changed protected Kanji artifacts after "
            f"{completed_step}: {changed}"
        )

# No write starts until all external moving inputs are explicitly pinned.
# The reviewed scope manifest is the authority for the accepted gold identity;
# an asynchronously synchronized newer master must be audited separately before
# it can replace this snapshot.
required_inputs = [
    "ESP_GOLD_PATH", "ESP_ACADEMIC_GOLD_PATH", "ESP_PEJVO_ORIGINAL_PATH",
    "ESP_CORPUS_PATH", "ESP_PHASE558_CURRENT_CORPUS_PATH",
    "ESP_PHASE597_CANDIDATE_DIR", "ESP_PHASE619_CANDIDATE_DIR",
    "ESP_PHASE619_RUBY_HTML_GUIDE_JA",
    "ESP_PHASE619_RUBY_HTML_GUIDE_ZH",
]
if ARGS.all_tracks:
    required_inputs.append("ESP_KANJI_MASTER_PATH")
for required in required_inputs:
    if not os.environ.get(required):
        raise SystemExit(f"formal regeneration requires explicit {required}")
with open(os.path.join(HERE, "_no_worsening_scope_manifest.json"), encoding="utf-8") as handle:
    scope_manifest = json.load(handle)
expected_gold = scope_manifest["expected"]["gold"]
phase532_scope_identity = scope_manifest["expected"].get(
    "phase532_ruby_policy"
)
phase532_carry_identity = scope_manifest["expected"].get(
    "phase532_authority_carry_forward"
)
phase532_formal = phase532_scope_identity is not None
if phase532_formal:
    for required in (
        "ESP_PHASE532_BASELINE_DIR", "ESP_PHASE532_CANDIDATE_DIR",
    ):
        if not os.environ.get(required):
            raise SystemExit(
                f"formal Phase 532 regeneration requires explicit {required}"
            )
    phase532_manifest_path = os.path.join(
        HERE, "_fake_coarse_reference_manifest.json",
    )
    phase532_policy_report = phase532_policy_builder.validate_frozen_closure(
        os.environ["ESP_PHASE532_BASELINE_DIR"],
        os.environ["ESP_PHASE532_CANDIDATE_DIR"],
        phase532_manifest_path,
    )
    phase532_carry_report = phase532_carry_builder.validate_frozen_closure(
        os.environ["ESP_PHASE532_BASELINE_DIR"],
        os.environ["ESP_PHASE532_CANDIDATE_DIR"],
        phase532_manifest_path,
    )
    if (
        phase532_scope_identity != phase532_policy.review_identity()
        or phase532_scope_identity
        != phase532_policy_report["review_identity"]
        or phase532_carry_identity != phase532_carry.review_identity()
        or phase532_carry_identity
        != phase532_carry_report["review_identity"]
    ):
        raise SystemExit("formal Phase 532 policy/carry identity mismatch")
elif phase532_carry_identity is not None:
    raise SystemExit("Phase 532 carry identity exists without its Ruby policy")
phase532_deployed_mode = None
if phase532_formal:
    phase532_activation_report = phase532_activation.activation_report()
    if phase532_activation_report.get("phase532_active") is not True:
        raise SystemExit("formal Phase 532 regeneration lacks active parent state")
    # This pipeline is the repeatable post-adoption route.  The one-time
    # pre-regen proof belongs to the reviewed promotion procedure, not every
    # subsequent regeneration.
    phase532_deployed_mode = "post-regen"

phase558_activation_report = phase558_activation.activation_report()
phase558_formal = phase558_activation_report.get(
    "phase558_ruby_overlay_active"
) is True
if not phase558_formal:
    raise SystemExit("formal regeneration requires the Phase 558 Ruby sidecar")
for required in (
    "ESP_PHASE558_CANDIDATE_DIR",
    "ESP_PHASE558_RUBY_DISPOSITION_LEDGER",
    "ESP_RUBY_HTML_GUIDE_JA",
    "ESP_RUBY_HTML_GUIDE_ZH",
    "ESP_PHASE558_FAKE_COARSE_MANIFEST",
    "ESP_PHASE558_TRANSITION_DISPOSITIONS",
):
    if not os.environ.get(required):
        raise SystemExit(
            f"formal Phase 558 regeneration requires explicit {required}"
        )
phase558_source_review = phase558_overlay_builder.validate_frozen_closure(
    os.environ["ESP_PHASE532_CANDIDATE_DIR"],
    os.environ["ESP_PHASE558_CANDIDATE_DIR"],
    os.environ["ESP_PHASE558_RUBY_DISPOSITION_LEDGER"],
    os.environ["ESP_RUBY_HTML_GUIDE_JA"],
    os.environ["ESP_RUBY_HTML_GUIDE_ZH"],
)
if (
    phase558_source_review["review_identity"]
    != phase558_overlay.review_identity()
    or phase558_activation_report["overlay_review"]
    != phase558_overlay.review_identity()
):
    raise SystemExit("formal Phase 558 source/activation identity mismatch")

phase598_activation_report = phase598_activation.activation_report()
if phase598_activation_report.get("phase598_technical_on_active") is not True:
    raise SystemExit(
        "formal regeneration requires the Phase 598 technical-on sidecar"
    )
phase597_candidate_dir = os.environ["ESP_PHASE597_CANDIDATE_DIR"]
phase598_bound_sources = {}
for source_name in (
    "phase597_learner",
    "phase597_academic",
    "phase597_pejvo_original",
    "phase597_fake_coarse_manifest",
):
    expected = phase598_policy.EXPECTED_SOURCES[source_name]
    matches = []
    for name in os.listdir(phase597_candidate_dir):
        path = os.path.join(phase597_candidate_dir, name)
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as handle:
            raw = handle.read()
        if (
            len(raw) == expected["bytes"]
            and hashlib.sha256(raw).hexdigest().upper()
            == expected["sha256"]
        ):
            matches.append(path)
    if len(matches) != 1:
        raise SystemExit(
            f"formal Phase 598 source binding failed for {source_name}: "
            f"{matches!r}"
        )
    phase598_bound_sources[source_name] = matches[0]
if (
    phase598_activation_report["phase598_review"]
    != phase598_policy.review_identity()
):
    raise SystemExit("formal Phase 598 source/activation identity mismatch")

phase619_activation_report = phase619_activation.activation_report()
if phase619_activation_report.get("phase619_ordinary_ruby_active") is not True:
    raise SystemExit(
        "formal regeneration requires the Phase 619 ordinary Ruby sidecar"
    )
phase619_source_review = phase619_review_builder.validate_frozen_closure(
    os.environ["ESP_PHASE597_CANDIDATE_DIR"],
    os.environ["ESP_PHASE619_CANDIDATE_DIR"],
    os.environ["ESP_PHASE619_RUBY_HTML_GUIDE_JA"],
    os.environ["ESP_PHASE619_RUBY_HTML_GUIDE_ZH"],
)
if (
    phase619_source_review["review_identity"]
    != phase619_policy.review_identity()
    or phase619_activation_report["phase619_review"]
    != phase619_policy.review_identity()
):
    raise SystemExit("formal Phase 619 source/activation identity mismatch")
_gold_raw, gold_identity = consistent_snapshot(os.environ["ESP_GOLD_PATH"])
if (
    gold_identity["sha256"] != expected_gold["sha256"]
    or gold_identity["bytes"] != expected_gold["bytes"]
):
    raise SystemExit(
        "pinned gold mismatch before regeneration: "
        f"expected {expected_gold['bytes']} bytes/{expected_gold['sha256']}, "
        f"got {gold_identity['bytes']} bytes/{gold_identity['sha256']}"
    )
COMMON_ENV = {
    "ESP_EXPECTED_GOLD_SHA256": expected_gold["sha256"],
    # Windows' legacy cp932 console cannot represent all Chinese/Korean paths
    # emitted by the formal reports.  Make every child deterministic UTF-8.
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
}
with open(
    os.path.join(HERE, "_fake_coarse_reference_manifest.json"),
    encoding="utf-8",
) as handle:
    fake_coarse_manifest = json.load(handle)
for label, environment_name in (
    ("academic", "ESP_ACADEMIC_GOLD_PATH"),
    ("pejvo_original", "ESP_PEJVO_ORIGINAL_PATH"),
):
    _paired_raw, paired_identity = consistent_snapshot(
        os.environ[environment_name]
    )
    expected = fake_coarse_manifest["sources"][label]
    if (
        paired_identity["sha256"] != expected["sha256"]
        or paired_identity["bytes"] != expected["bytes"]
        or paired_identity["lines"] != expected["lines"]
    ):
        raise SystemExit(
            f"pinned {label} mismatch before regeneration: expected "
            f"{expected['bytes']} bytes/{expected['lines']} lines/"
            f"{expected['sha256']}, got {paired_identity['bytes']} bytes/"
            f"{paired_identity['lines']} lines/{paired_identity['sha256']}"
        )
COMMON_ENV["ESP_EXPECTED_ACADEMIC_SHA256"] = (
    fake_coarse_manifest["sources"]["academic"]["sha256"]
)
FORMAL_HEAD = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=os.path.dirname(HERE), text=True,
).strip()
R67_R68_OVERLAY_SNAPSHOT = os.path.join(
    tempfile.gettempdir(),
    f"esperanto_r67_r68_overlay_{os.getpid()}.json",
)
if ARGS.all_tracks:
    kanji_manifest_path = os.path.join(
        HERE, "_kanji_master_scope_manifest.json",
    )
    with open(kanji_manifest_path, encoding="utf-8") as handle:
        kanji_manifest = json.load(handle)
    if kanji_manifest.get("schema_version") != 1:
        raise SystemExit("unsupported Kanji master manifest schema")
    for expected in kanji_manifest["files"]:
        path = os.path.join(
            os.environ["ESP_KANJI_MASTER_PATH"], expected["name"],
        )
        raw = open(path, "rb").read()
        actual_sha = hashlib.sha256(raw).hexdigest().upper()
        if len(raw) != expected["bytes"] or actual_sha != expected["sha256"]:
            raise SystemExit(
                f"pinned Kanji master mismatch: {expected['name']}: expected "
                f"{expected['bytes']} bytes/{expected['sha256']}, got "
                f"{len(raw)} bytes/{actual_sha}"
            )
    COMMON_ENV["ESP_EXPECTED_KANJI_MASTER_MANIFEST"] = kanji_manifest_path
    _kanji_injection = next(
        row for row in kanji_manifest["files"]
        if row["name"] == "漢字注入_学習者版_20260620.txt"
    )
    if sum(
        row.get("name") == _kanji_injection["name"]
        for row in kanji_manifest["files"]
    ) != 1:
        raise SystemExit(
            "Kanji master manifest must pin exactly one injection file"
        )
    COMMON_ENV["ESP_EXPECTED_KANJI_MASTER_SHA256"] = (
        _kanji_injection["sha256"]
    )
STEPS = [
    ([
        sys.executable,
        os.path.join(HERE, 'build_fake_coarse_reference_manifest.py'),
        '--learner', os.environ['ESP_GOLD_PATH'],
        '--academic', os.environ['ESP_ACADEMIC_GOLD_PATH'],
        '--pejvo-original', os.environ['ESP_PEJVO_ORIGINAL_PATH'],
        '--check',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'build_fake_coarse_transition_review.py'),
        '--check',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'build_fake_coarse_ff33_transition_review.py'),
        '--check',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'build_fake_coarse_5e_transition_review.py'),
        '--check',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'build_fake_coarse_phase511_transition_review.py'),
        '--check',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'build_fake_coarse_transition_app_review.py'),
        '--check',
    ], {}),
    ([sys.executable, os.path.join(HERE, 'build_corpus_exact_manifest.py'), '--check'], {}),
    ([sys.executable, os.path.join(HERE, 'build_corpus_reviewed_exact_manifest.py'), '--check'], {}),
    ([sys.executable, os.path.join(HERE, 'bare_word_audit.py'), '--require-zero'], {}),
    *([
        ([
            sys.executable,
            os.path.join(HERE, 'build_phase532_ruby_policy_review.py'),
            '--baseline-dir', os.environ['ESP_PHASE532_BASELINE_DIR'],
            '--candidate-dir', os.environ['ESP_PHASE532_CANDIDATE_DIR'],
            '--candidate-manifest', phase532_manifest_path,
            '--check',
        ], {}),
        ([
            sys.executable,
            os.path.join(HERE, 'build_phase532_authority_carry_forward.py'),
            '--baseline-dir', os.environ['ESP_PHASE532_BASELINE_DIR'],
            '--candidate-dir', os.environ['ESP_PHASE532_CANDIDATE_DIR'],
            '--candidate-manifest', phase532_manifest_path,
            '--check',
        ], {}),
    ] if phase532_formal else []),
    ([
        sys.executable,
        os.path.join(HERE, 'build_phase558_ruby_overlay_review.py'),
        '--phase532-dir', os.environ['ESP_PHASE532_CANDIDATE_DIR'],
        '--phase558-dir', os.environ['ESP_PHASE558_CANDIDATE_DIR'],
        '--disposition-ledger',
        os.environ['ESP_PHASE558_RUBY_DISPOSITION_LEDGER'],
        '--japanese-guide', os.environ['ESP_RUBY_HTML_GUIDE_JA'],
        '--chinese-guide', os.environ['ESP_RUBY_HTML_GUIDE_ZH'],
        '--check',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'build_phase619_ordinary_ruby_review.py'),
        '--phase597-dir', os.environ['ESP_PHASE597_CANDIDATE_DIR'],
        '--phase619-dir', os.environ['ESP_PHASE619_CANDIDATE_DIR'],
        '--japanese-guide',
        os.environ['ESP_PHASE619_RUBY_HTML_GUIDE_JA'],
        '--chinese-guide',
        os.environ['ESP_PHASE619_RUBY_HTML_GUIDE_ZH'],
        '--check',
    ], {}),
    # Permission to begin any repeat regeneration comes from the already
    # adopted Phase 532/558 state, with identical JA/ZH/KO boundaries.  The
    # one-time legacy/pre-regen proof remains in the promotion audit log.
    *([([
        sys.executable,
        os.path.join(HERE, 'phase532_runtime_signature_gate.py'),
        '--mode', phase532_deployed_mode, '--deployed',
    ], {})] if phase532_formal else []),
    ([
        sys.executable,
        os.path.join(HERE, 'phase558_ruby_overlay_runtime_gate.py'),
        '--mode', 'post-regen', '--deployed', '--batch-size', '33',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'phase598_technical_on_runtime_gate.py'),
        '--deployed', '--batch-size', '20',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'phase619_ordinary_ruby_runtime_gate.py'),
        '--deployed', '--batch-size', '32',
    ], {}),
    # R67/R68 are reviewed post-generation layers.  Seal their exact deployed
    # rows before apply_confirmed rebuilds the large Ruby payloads; re-running
    # the historical discovery script would consult a moving absolute master.
    ([
        sys.executable,
        os.path.join(HERE, 'preserve_r67_r68_ruby_overlays.py'),
        'capture', '--output', R67_R68_OVERLAY_SNAPSHOT,
    ], {}),
    ([sys.executable, os.path.join(HERE, 'apply_corpus_word_anno.py'), '--write'], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'build_word_anno_boundary_manifest.py'),
        '--check',
    ], {}),
    # 3言語とも同一の固定正本 + 確定補正になることを、生成前にfail-closedで検査する。
    ([sys.executable, os.path.join(HERE, 'apply_confirmed_now.py'), '30', '--settings-audit'], {'SKIP_VERIFY': '1'}),
    # apply_confirmed builds all three payloads in memory and runs every active
    # Phase 532/558/598/619 runtime gate before its first persistent write.
    ([sys.executable, os.path.join(HERE, 'apply_confirmed_now.py'), '30', '--write'], {'SKIP_VERIFY': '1'}),
    # Carry forward only the pinned R67H 336 + R68W 1,012 rows per language
    # (plus the reviewed Auster exact override), transactionally across JA/ZH/KO.
    ([
        sys.executable,
        os.path.join(HERE, 'preserve_r67_r68_ruby_overlays.py'),
        'apply', '--input', R67_R68_OVERLAY_SNAPSHOT,
        '--expected-global-rows', '572713',
    ], {}),
    ([sys.executable, os.path.join(HERE, 'fix_ruby_postregen.py')], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'fix_ruby_kyodai_meaning_break.py'),
        '--apply',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'fix_ruby_hyphen_joiner.py'),
        '--apply',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'fix_ruby_zhko_diminutive_gloss.py'),
        '--apply',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'preserve_r67_r68_ruby_overlays.py'),
        'audit', '--expected-global-rows', '572729',
    ], {}),
    # Re-render the persisted payloads after post-processing as well: the
    # in-memory gate above cannot license a later fixer to alter any of the 58.
    *([([
        sys.executable,
        os.path.join(HERE, 'phase532_runtime_signature_gate.py'),
        '--mode', 'post-regen', '--deployed',
    ], {})] if phase532_formal else []),
    ([
        sys.executable,
        os.path.join(HERE, 'phase558_ruby_overlay_runtime_gate.py'),
        '--mode', 'post-regen', '--deployed', '--batch-size', '33',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'phase598_technical_on_runtime_gate.py'),
        '--deployed', '--batch-size', '20',
    ], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'phase619_ordinary_ruby_runtime_gate.py'),
        '--deployed', '--batch-size', '32',
    ], {}),
    # 全21438 canonical表記を配置済み3言語runtimeで描画し、残差0を漢字工程前に強制する。
    ([sys.executable, os.path.join(HERE, 'test_canonical_corpus_surfaces.py')], {}),
    ([sys.executable, os.path.join(HERE, 'check_canonical_corpus_surfaces.py')], {}),
    # 漢字は正本(エスペラント語根＿漢字割り当て＿20260630)から全面再同期してから統合する(第18R以降の正道)
    ([sys.executable, os.path.join(HERE, 'resync_kanji_master.py'), '--write'], {}),
    ([sys.executable, os.path.join(HERE, 'apply_kanji_now.py'), '--write'], {}),
    ([sys.executable, os.path.join(HERE, 'fix_kanji_2890.py'), '--apply'], {}),  # 旧安全網(resync後は実質no-op)
    # This is intentionally coverage-only: it proves direct learner-master
    # key/piece alignment without claiming all-path deployed render fidelity.
    ([
        sys.executable,
        os.path.join(
            HERE, 'audit_phase619_learner_word_kanji_key_coverage.py',
        ),
        '--phase619-dir', os.environ['ESP_PHASE619_CANDIDATE_DIR'],
        '--check',
    ], {}),
    # 偽分解/深分解のpiece列と漢字割当を、固定word_kanji authorityに対し3言語全件照合。
    ([sys.executable, os.path.join(HERE, 'check_kanji_fake_decomposition.py')], {}),
    # 純粋置換版(タグなし)はHTML漢字JSONから毎回再導出する(忘れると陳腐化する成果物)
    ([sys.executable, os.path.join(HERE, 'derive_pure_kanji.py')], {}),
    ([sys.executable, os.path.join(HERE, 'anomaly_scan.py')], {}),
    # 生成規則の単体テスト + 3言語デプロイJSONの実機回帰テスト。
    ([sys.executable, os.path.join(HERE, 'test_generation_regressions.py')], {}),
    ([sys.executable, os.path.join(HERE, 'test_phase558_ruby_overlay.py')], {}),
    ([sys.executable, os.path.join(
        HERE, 'test_phase598_technical_on.py',
    )], {}),
    ([sys.executable, os.path.join(
        HERE, 'test_phase619_ordinary_ruby.py',
    )], {}),
    ([sys.executable, os.path.join(
        HERE, 'test_phase619_learner_word_kanji_key_coverage.py',
    )], {}),
    ([sys.executable, os.path.join(
        HERE, 'test_r67_r68_overlay_carry_forward.py',
    )], {}),
    ([
        sys.executable,
        os.path.join(HERE, 'test_phase558_no_worsening_sidecar_gate.py'),
    ], {}),
    ([sys.executable, os.path.join(HERE, 'test_reviewed_exact_manifest.py')], {}),
    ([sys.executable, os.path.join(
        HERE, 'test_corpus_reviewed_exact_transition.py',
    )], {}),
    ([sys.executable, os.path.join(
        HERE, 'test_word_anno_boundary_transition.py',
    )], {}),
    ([sys.executable, os.path.join(
        HERE, 'test_fake_coarse_review_drift.py',
    )], {}),
    ([sys.executable, os.path.join(HERE, 'check_multilingual_structure.py')], {}),
    ([sys.executable, os.path.join(HERE, 'check_raw_apostrophe_structure.py')], {}),
    # Run both isolated Phase 558 authorities.  Each raw audit is expected to
    # fail on exactly the closed five-row/two-row reviewed delta; only its
    # matching fail-closed sidecar may admit that report.
    ([
        sys.executable,
        os.path.join(HERE, 'run_phase558_no_worsening.py'),
    ], {}),
    # 固定gold snapshot全行（空白・約物・hyphenを含む）を3言語runtimeで監査。
    # fast版はmoving absolute pathのmonitor-onlyであり、正式工程では使用しない。
    ([
        sys.executable,
        os.path.join(HERE, 'audit_master_3lang_full_snapshot.py'),
        '--gold', phase619_source_review['source_paths']['phase619_learner'],
        '--expected-gold-sha256',
        phase619_policy.EXPECTED_SOURCES['phase619_learner']['sha256'],
        '--academic',
        phase619_source_review['source_paths']['phase619_academic'],
        '--expected-academic-sha256',
        phase619_policy.EXPECTED_SOURCES['phase619_academic']['sha256'],
        '--expected-head', FORMAL_HEAD,
        '--candidate-fake-coarse-manifest',
        phase619_source_review[
            'source_paths'
        ]['phase619_fake_coarse_manifest'],
        '--candidate-transition-dispositions',
        phase619_source_review[
            'source_paths'
        ]['phase619_transition_dispositions'],
        '--phase597-candidate-dir',
        os.environ['ESP_PHASE597_CANDIDATE_DIR'],
        '--phase619-candidate-dir',
        os.environ['ESP_PHASE619_CANDIDATE_DIR'],
        '--phase619-japanese-guide',
        os.environ['ESP_PHASE619_RUBY_HTML_GUIDE_JA'],
        '--phase619-chinese-guide',
        os.environ['ESP_PHASE619_RUBY_HTML_GUIDE_ZH'],
        '--allow-stable-tracked-changes',
        '--report', os.path.join(
            tempfile.gettempdir(), 'esperanto_master_3lang_formal_report.json',
        ),
    ], {}),
    # 全工程合格後に .bak_* を掃除(放置すると3GB超に膨張。現行成果物はgit+SSDで三重保全済み)
    ([sys.executable, os.path.join(HERE, 'prune_baks.py')], {}),
]

KANJI_WRITE_SCRIPTS = frozenset({
    "resync_kanji_master.py",
    "apply_kanji_now.py",
    "fix_kanji_2890.py",
    "derive_pure_kanji.py",
})
RUBY_ONLY_EXCLUDED_SCRIPTS = KANJI_WRITE_SCRIPTS | {"prune_baks.py"}
if ARGS.ruby_only:
    STEPS = [
        step for step in STEPS
        if os.path.basename(step[0][1]) not in RUBY_ONLY_EXCLUDED_SCRIPTS
    ]
    planned_scripts = {os.path.basename(step[0][1]) for step in STEPS}
    if planned_scripts & RUBY_ONLY_EXCLUDED_SCRIPTS:
        raise SystemExit("Ruby-only plan unexpectedly contains a writer")
    if "check_kanji_fake_decomposition.py" not in planned_scripts:
        raise SystemExit("Ruby-only plan lost the read-only Kanji integrity gate")
    if (
        "audit_phase619_learner_word_kanji_key_coverage.py"
        not in planned_scripts
    ):
        raise SystemExit(
            "Ruby-only plan lost the Phase 619 Kanji coverage-only audit"
        )
    ruby_only_kanji_guard = _capture_ruby_only_kanji_guard()
else:
    ruby_only_kanji_guard = None

for cmd, env_add in STEPS:
    env = dict(os.environ); env.update(COMMON_ENV); env.update(env_add)
    step_name = os.path.basename(cmd[1])
    print('>>>', ' '.join(os.path.basename(c) for c in cmd[1:2] + cmd[2:]))
    try:
        r = subprocess.run(cmd, env=env)
    finally:
        if ruby_only_kanji_guard is not None:
            _assert_ruby_only_kanji_guard(
                ruby_only_kanji_guard,
                step_name,
            )
    if r.returncode != 0:
        print(f'!! 失敗: {cmd[1]}'); sys.exit(1)
print(
    '=== 道B 一括再生成 完了 '
    f"({'Ruby-only' if ARGS.ruby_only else 'all-tracks candidate'}) ==="
)
