# -*- coding: utf-8 -*-
"""Fail-closed successor gate for the complete Phase 597 master audit.

The raw full-master auditor intentionally keeps a generic moving-master
candidate non-promotable.  This sidecar can certify only the deployed Ruby
runtime chain and one explicitly reviewed two-track residual (``atletiko``).
It never promotes the Phase 597 master or closes the broader fake/coarse
semantic queue.

Runtime-dependent values are deliberately absent from the initial review.
Until a fresh raw report is run and those values are explicitly sealed, this
module fails before invoking any expensive deployed predecessor gate.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess

import no_worsening_audit as audit


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REVIEW_PATH = HERE / "_phase597_full_master_successor_review.json"
RAW_AUDITOR = HERE / "audit_master_3lang_full_snapshot.py"
EXPECTED_REVIEW_SHA256 = (
    "8344182631231E6407AE51BD20067EE258A416B6F009C7B4427F68D92523BE22"
)
LANGUAGES = ("JA", "ZH", "KO")

REVIEW_TOP_KEYS = {
    "schema_version",
    "phase",
    "review_kind",
    "policy",
    "sources",
    "atletiko_two_track_adjudication",
    "raw_audit_contract",
    "deployed_predecessor_requirements",
    "runtime_measurement",
}
SOURCE_NAMES = {
    "learner",
    "academic",
    "pejvo_original",
    "candidate_fake_coarse_manifest",
    "candidate_pejvo_disagreement_review",
    "candidate_transition_dispositions",
}
RAW_TOP_KEYS = {
    "schema_version",
    "algorithm",
    "script_path",
    "script_sha256",
    "app",
    "gold",
    "coarse_authority",
    "accounting",
    "three_language_boundary",
    "languages",
    "inputs_stable",
    "candidate_audit",
    "complete",
    "gate",
    "interpretation",
}
RAW_LANGUAGE_KEYS = {
    "language",
    "render_seconds",
    "runtime_sha256",
    "overlay_sha256",
    "payload_sha256",
    "char_widths_sha256",
    "css_class_scale",
    "global_rules",
    "localized_rules",
    "two_char_rules",
    "correction_entries",
    "rendered_unique_surfaces",
    "rendered_full_exact_surfaces",
    "rendered_legacy_fast_surfaces",
    "issues",
    "issue_counts",
    "naked_fragment_audit",
    "ruby_length_audit",
}
RAW_COARSE_KEYS = {
    "academic",
    "fake_coarse_manifest",
    "transition_manifests",
    "candidate_transition_dispositions",
    "paired_invariant",
    "coverage_categories",
    "academic_sha256_at_end",
    "authority_rows",
    "all_rows_assessed_in_all_languages",
    "staged_transition_gate",
    "staged_transition_expected_rows",
    "all_fake_coarse_gate",
    "all_fake_coarse_enforced",
    "effective_ruby_width_within_2x",
    "languages",
    "staging_note",
}
RAW_COARSE_LANGUAGE_KEYS = {
    "language",
    "counts",
    "coverage_categories",
    "authority_sources",
    "transition_scopes",
    "mismatches",
}
RUNTIME_MEASUREMENT_KEYS = {
    "sealed",
    "seal_source",
    "raw_audit_script_sha256",
    "raw_semantic_projection_sha256",
    "comment_line_numbers_sha256",
    "fake_mismatch_count_per_language",
    "fake_mismatch_projection_sha256",
    "current_app_fingerprints",
    "language_semantic_projection_sha256",
}
SHA256_RE = re.compile(r"^[0-9A-F]{64}$")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def stable_json_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest().upper()


def _is_sha256(value) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _read_regular_json(path: Path, label: str) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} is not a regular file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is unreadable: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain one JSON object")
    return payload


def load_review(review_path: Path = REVIEW_PATH) -> dict:
    """Load the byte-pinned review while permitting no implicit sealing."""
    review_path = Path(review_path)
    if review_path.is_symlink() or not review_path.is_file():
        raise ValueError(
            f"Phase 597 successor review is not a regular file: {review_path}"
        )
    raw = review_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest().upper()
    if digest != EXPECTED_REVIEW_SHA256:
        raise ValueError(
            "Phase 597 successor review identity drift: "
            f"{digest} != {EXPECTED_REVIEW_SHA256}"
        )
    try:
        review = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(
            f"Phase 597 successor review is unreadable: {error}"
        ) from error
    if not isinstance(review, dict) or set(review) != REVIEW_TOP_KEYS:
        raise ValueError("Phase 597 successor review schema drift")
    if (
        review["schema_version"] != 1
        or review["phase"] != 597
        or review["review_kind"]
        != "full_master_successor_runtime_integrity_sidecar"
        or set(review["sources"]) != SOURCE_NAMES
        or set(review["runtime_measurement"]) != RUNTIME_MEASUREMENT_KEYS
    ):
        raise ValueError("Phase 597 successor review identity drift")
    if (
        review["raw_audit_contract"].get("master_promotion_gate") is not False
        or review["raw_audit_contract"].get(
            "full_fake_coarse_semantic_gate"
        ) is not False
        or review["atletiko_two_track_adjudication"].get(
            "master_candidate_promotion_authorized"
        ) is not False
        or review["atletiko_two_track_adjudication"].get(
            "full_fake_coarse_semantic_gate"
        ) is not False
    ):
        raise ValueError("Phase 597 successor promotion policy drift")
    return review


def require_sealed_runtime_measurement(review: dict) -> dict:
    """Reject the review until every fresh-report-dependent pin is present."""
    measurement = review.get("runtime_measurement")
    if (
        not isinstance(measurement, dict)
        or set(measurement) != RUNTIME_MEASUREMENT_KEYS
        or measurement.get("sealed") is not True
    ):
        raise ValueError(
            "unsealed Phase 597 successor measurement; run one fresh raw "
            "audit, independently review it, then explicitly seal every "
            "runtime-dependent pin"
        )
    for key in (
        "raw_audit_script_sha256",
        "raw_semantic_projection_sha256",
        "comment_line_numbers_sha256",
        "fake_mismatch_projection_sha256",
    ):
        if not _is_sha256(measurement.get(key)):
            raise ValueError(
                f"unsealed Phase 597 successor measurement field: {key}"
            )
    mismatch_count = measurement.get("fake_mismatch_count_per_language")
    if not isinstance(mismatch_count, int) or mismatch_count < 0:
        raise ValueError(
            "unsealed Phase 597 successor fake-mismatch count"
        )
    fingerprints = measurement.get("current_app_fingerprints")
    if (
        not isinstance(fingerprints, dict)
        or tuple(fingerprints) != LANGUAGES
    ):
        raise ValueError(
            "unsealed Phase 597 successor current app fingerprints"
        )
    for language in LANGUAGES:
        fingerprint = fingerprints[language]
        if (
            not isinstance(fingerprint, dict)
            or not fingerprint
            or any(
                not isinstance(path, str) or not _is_sha256(digest)
                for path, digest in fingerprint.items()
            )
        ):
            raise ValueError(
                f"unsealed Phase 597 successor {language} app fingerprint"
            )
    projections = measurement.get("language_semantic_projection_sha256")
    if (
        not isinstance(projections, dict)
        or tuple(projections) != LANGUAGES
        or any(not _is_sha256(projections[language]) for language in LANGUAGES)
    ):
        raise ValueError(
            "unsealed Phase 597 successor language semantic projections"
        )
    return measurement


def _source_identity(path: Path) -> dict:
    raw = path.read_bytes()
    return {
        "bytes": len(raw),
        "lines": len(raw.decode("utf-8").splitlines()),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def _expected_transition_entry(review: dict) -> dict:
    adjudication = review["atletiko_two_track_adjudication"]
    master = adjudication["kanji_master_track"]
    return {
        "learner_line": adjudication["learner_line"],
        "surface": adjudication["surface"],
        "previous_transition_scope": adjudication[
            "previous_transition_scope"
        ],
        "previous_coarse_decomposition": adjudication["ruby_track"][
            "decomposition"
        ],
        "current_learner_decomposition": master[
            "learner_decomposition"
        ],
        "current_academic_decomposition": master[
            "academic_decomposition"
        ],
        "status": adjudication["raw_candidate_status"],
        "decision": adjudication["raw_candidate_decision"],
        "reason": adjudication["raw_candidate_reason"],
    }


def validate_phase597_source_directory(
    phase597_dir: Path, review: dict | None = None,
) -> dict:
    """Require exactly the six byte-pinned Phase 597 source artifacts."""
    if review is None:
        review = load_review()
    phase597_dir = Path(phase597_dir)
    if phase597_dir.is_symlink() or not phase597_dir.is_dir():
        raise ValueError(
            f"Phase 597 source is not a regular directory: {phase597_dir}"
        )
    expected_filenames = {
        spec["path"] for spec in review["sources"].values()
    }
    actual_paths = list(phase597_dir.iterdir())
    if (
        {path.name for path in actual_paths} != expected_filenames
        or any(path.is_symlink() or not path.is_file() for path in actual_paths)
    ):
        raise ValueError(
            "Phase 597 source directory must contain exactly the six "
            "reviewed regular files"
        )
    identities = {}
    for name, spec in review["sources"].items():
        path = phase597_dir / spec["path"]
        observed = _source_identity(path)
        expected = {
            "bytes": spec["bytes"],
            "lines": spec["lines"],
            "sha256": spec["sha256"],
        }
        if observed != expected:
            raise ValueError(
                f"Phase 597 fixed source drift: {name}: "
                f"{observed!r} != {expected!r}"
            )
        identities[name] = observed

    manifest = _read_regular_json(
        phase597_dir
        / review["sources"]["candidate_fake_coarse_manifest"]["path"],
        "Phase 597 fake/coarse manifest",
    )
    manifest_spec = review["sources"]["candidate_fake_coarse_manifest"]
    if (
        manifest.get("schema_version") != 1
        or not isinstance(manifest.get("entries"), list)
        or len(manifest["entries"]) != manifest_spec["entries"]
        or compact_sha256(manifest["entries"])
        != manifest_spec["entries_sha256"]
        or manifest.get("entries_sha256")
        != manifest_spec["entries_sha256"]
    ):
        raise ValueError("Phase 597 fake/coarse manifest semantic drift")

    pejvo_review = _read_regular_json(
        phase597_dir
        / review["sources"]["candidate_pejvo_disagreement_review"]["path"],
        "Phase 597 PEJVO disagreement review",
    )
    if (
        pejvo_review.get("schema_version") != 1
        or pejvo_review.get("expected_entries")
        != review["sources"]["candidate_pejvo_disagreement_review"][
            "entries"
        ]
        or not isinstance(pejvo_review.get("entries"), list)
        or len(pejvo_review["entries"])
        != review["sources"]["candidate_pejvo_disagreement_review"][
            "entries"
        ]
    ):
        raise ValueError("Phase 597 PEJVO disagreement review drift")

    dispositions = _read_regular_json(
        phase597_dir
        / review["sources"]["candidate_transition_dispositions"]["path"],
        "Phase 597 transition dispositions",
    )
    manifest_identity = review["sources"]["candidate_fake_coarse_manifest"]
    expected_disposition = _expected_transition_entry(review)
    if (
        set(dispositions)
        != {
            "schema_version",
            "candidate_only",
            "source_phase",
            "sources",
            "entries",
        }
        or dispositions["schema_version"] != 1
        or dispositions["candidate_only"] is not True
        or dispositions["source_phase"] != 597
        or dispositions["sources"]
        != {
            "learner_sha256": review["sources"]["learner"]["sha256"],
            "academic_sha256": review["sources"]["academic"]["sha256"],
            "candidate_manifest_sha256": manifest_identity["sha256"],
            "candidate_manifest_entries_sha256": manifest_identity[
                "entries_sha256"
            ],
        }
        or dispositions["entries"] != [expected_disposition]
    ):
        raise ValueError("Phase 597 transition disposition semantic drift")

    adjudication = review["atletiko_two_track_adjudication"]
    line_index = adjudication["learner_line"] - 1
    learner_lines = (
        phase597_dir / review["sources"]["learner"]["path"]
    ).read_text(encoding="utf-8").splitlines()
    academic_lines = (
        phase597_dir / review["sources"]["academic"]["path"]
    ).read_text(encoding="utf-8").splitlines()
    master = adjudication["kanji_master_track"]
    if (
        learner_lines[line_index] != master["learner_line_text"]
        or academic_lines[line_index] != master["academic_line_text"]
        or master["learner_decomposition"] != "atlet/ik/o"
        or master["academic_decomposition"] != "atlet/ik/o"
        or master["fake_decomposition_preserved_for_kanji"] is not True
        or adjudication["ruby_track"]["decomposition"] != "atletik/o"
        or adjudication["ruby_track"]["typed_signature"]
        != "R:atletik|L:o"
    ):
        raise ValueError("Phase 597 atletiko two-track source drift")
    return {
        "directory": str(phase597_dir.resolve()),
        "files": identities,
        "atletiko_two_track_source_gate": True,
        "gate": True,
    }


def _strip_paths(value):
    """Remove host paths and timing noise while retaining semantic fields."""
    if isinstance(value, list):
        return [_strip_paths(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _strip_paths(item)
            for key, item in value.items()
            if key not in {
                "path",
                "provenance_manifest_path",
                "render_seconds",
            }
        }
    return value


def language_semantic_projection(language_report: dict) -> dict:
    projection = copy.deepcopy(language_report)
    projection.pop("render_seconds", None)
    return projection


def raw_report_semantic_projection(report: dict) -> dict:
    """Project all stable audit meaning, excluding only host/Git diagnostics."""
    return _strip_paths({
        key: copy.deepcopy(value)
        for key, value in report.items()
        if key not in {"script_path", "app"}
    })


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise ValueError(
            completed.stderr.decode("utf-8", errors="replace")
        )
    return completed.stdout.decode("ascii").strip()


def _validate_raw_source_identity(
    observed: dict, source_spec: dict, expected_path: Path, label: str,
    *, at_end_key: str | None = None,
) -> None:
    required = {
        "path",
        "bytes",
        "sha256",
        "lines",
        *({at_end_key} if at_end_key else set()),
    }
    if (
        not isinstance(observed, dict)
        or set(observed) != required
        or Path(observed["path"]).resolve() != expected_path.resolve()
        or observed["bytes"] != source_spec["bytes"]
        or observed["lines"] != source_spec["lines"]
        or observed["sha256"] != source_spec["sha256"]
        or (
            at_end_key is not None
            and observed[at_end_key] != source_spec["sha256"]
        )
    ):
        raise ValueError(f"Phase 597 raw {label} identity drift")


def _fingerprint_value(fingerprint: dict, suffix: str) -> str:
    suffix = suffix.replace("\\", "/")
    matches = [
        digest
        for path, digest in fingerprint.items()
        if path.replace("\\", "/").endswith(suffix)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Phase 597 app fingerprint lacks unique {suffix!r}"
        )
    return matches[0]


def _validate_raw_language(
    row: dict, contract: dict, measurement: dict,
) -> dict:
    language = row.get("language") if isinstance(row, dict) else None
    if language not in LANGUAGES or set(row) != RAW_LANGUAGE_KEYS:
        raise ValueError("Phase 597 raw language schema/order drift")
    if (
        not isinstance(row["render_seconds"], (int, float))
        or row["render_seconds"] < 0
        or row["rendered_unique_surfaces"]
        != contract["rendered_unique_surfaces"]
        or row["rendered_full_exact_surfaces"]
        != contract["rendered_full_exact_surfaces"]
        or row["rendered_legacy_fast_surfaces"]
        != contract["rendered_legacy_fast_surfaces"]
    ):
        raise ValueError(f"Phase 597 {language} render accounting drift")
    issue_buckets = contract["issue_buckets"]
    if (
        not isinstance(row["issues"], dict)
        or tuple(row["issues"]) != tuple(issue_buckets)
        or any(row["issues"][bucket] != [] for bucket in issue_buckets)
        or not isinstance(row["issue_counts"], dict)
        or tuple(row["issue_counts"]) != tuple(issue_buckets)
        or any(row["issue_counts"][bucket] != 0 for bucket in issue_buckets)
    ):
        raise ValueError(f"Phase 597 {language} runtime issue gate failed")
    width = row["ruby_length_audit"]
    zero_width_fields = (
        "empty_rt_unique",
        "empty_rt_line_weighted",
        "empty_rb_unique",
        "empty_rb_line_weighted",
    )
    if (
        not isinstance(width, dict)
        or any(width.get(key) != 0 for key in zero_width_fields)
        or width.get("missing_width_characters") != {}
        or width.get("unknown_rt_classes") != {}
        or not isinstance(width.get("max_effective_width_ratio"), (int, float))
        or width["max_effective_width_ratio"] > 2
    ):
        raise ValueError(f"Phase 597 {language} effective-width gate failed")
    for bin_key in (
        "effective_width_ratio_bins_unique",
        "effective_width_ratio_bins_line_weighted",
    ):
        bins = width.get(bin_key)
        if (
            not isinstance(bins, dict)
            or bins.get("gt_2") != 0
            or bins.get("gt_2_5") != 0
            or bins.get("gt_3") != 0
            or bins.get("unmeasurable") != 0
        ):
            raise ValueError(
                f"Phase 597 {language} effective-width bins failed"
            )

    fingerprint = measurement["current_app_fingerprints"][language]
    raw_hashes = {
        "runtime_sha256": _fingerprint_value(
            fingerprint,
            f"Esperanto-Kanji-Ruby-{language}/esp_text_replacement_module.py",
        ),
        "overlay_sha256": _fingerprint_value(
            fingerprint,
            f"Esperanto-Kanji-Ruby-{language}/esp_overlay_module.py",
        ),
        "payload_sha256": _fingerprint_value(
            fingerprint,
            f"Esperanto-Kanji-Ruby-{language}/app_data/置換リスト_ルビ.json",
        ),
        "char_widths_sha256": _fingerprint_value(
            fingerprint,
            f"Esperanto-Kanji-Ruby-{language}/app_data/char_widths.json",
        ),
    }
    if any(row[key] != digest for key, digest in raw_hashes.items()):
        raise ValueError(
            f"Phase 597 {language} raw/current app fingerprint drift"
        )
    projection_sha256 = stable_json_sha256(
        language_semantic_projection(row)
    )
    if (
        projection_sha256
        != measurement["language_semantic_projection_sha256"][language]
    ):
        raise ValueError(
            f"Phase 597 {language} semantic projection drift"
        )
    return {
        "language": language,
        "max_effective_width_ratio": width["max_effective_width_ratio"],
        "runtime_issues": 0,
        "language_semantic_projection_sha256": projection_sha256,
        "gate": True,
    }


def validate_raw_report(
    report: dict,
    phase597_dir: Path,
    *,
    review: dict | None = None,
    expected_head: str | None = None,
) -> dict:
    """Validate a fresh generic Phase 597 report against sealed measurements."""
    if review is None:
        review = load_review()
    measurement = require_sealed_runtime_measurement(review)
    validate_phase597_source_directory(phase597_dir, review)
    phase597_dir = Path(phase597_dir)
    if not isinstance(report, dict) or set(report) != RAW_TOP_KEYS:
        raise ValueError("Phase 597 raw report schema drift")
    contract = review["raw_audit_contract"]
    if (
        report["schema_version"] != contract["schema_version"]
        or not isinstance(report["algorithm"], dict)
        or report["algorithm"].get("id") != contract["algorithm_id"]
        or report["algorithm"].get("batch_size") != contract["batch_size"]
        or report["script_sha256"]
        != measurement["raw_audit_script_sha256"]
        or Path(report["script_path"]).resolve() != RAW_AUDITOR.resolve()
        or file_sha256(RAW_AUDITOR) != report["script_sha256"]
        or report["complete"] is not True
        or report["gate"] is not False
    ):
        raise ValueError("Phase 597 raw audit identity/gate drift")

    if expected_head is None:
        expected_head = _git_head()
    app = report["app"]
    if (
        not isinstance(app, dict)
        or set(app)
        != {
            "root",
            "head_oid",
            "tracked_status_at_start",
            "tracked_status_at_end",
        }
        or Path(app["root"]).resolve() != ROOT.resolve()
        or app["head_oid"] != expected_head
        or not re.fullmatch(r"[0-9a-f]{40}", expected_head)
        or app["tracked_status_at_start"] != app["tracked_status_at_end"]
    ):
        raise ValueError("Phase 597 raw app snapshot drift")

    _validate_raw_source_identity(
        report["gold"],
        review["sources"]["learner"],
        phase597_dir / review["sources"]["learner"]["path"],
        "learner",
        at_end_key="sha256_at_end",
    )
    coarse = report["coarse_authority"]
    if not isinstance(coarse, dict) or set(coarse) != RAW_COARSE_KEYS:
        raise ValueError("Phase 597 raw coarse-authority schema drift")
    _validate_raw_source_identity(
        coarse["academic"],
        review["sources"]["academic"],
        phase597_dir / review["sources"]["academic"]["path"],
        "academic",
    )
    if (
        coarse["academic_sha256_at_end"]
        != review["sources"]["academic"]["sha256"]
        or coarse["authority_rows"] != contract["authority_rows"]
        or coarse["all_rows_assessed_in_all_languages"] is not True
        or coarse["staged_transition_gate"] is not True
        or coarse["staged_transition_expected_rows"]
        != contract["staged_transition_expected_rows"]
        or coarse["all_fake_coarse_gate"] is not False
        or coarse["all_fake_coarse_enforced"] is not False
        or coarse["effective_ruby_width_within_2x"] is not True
    ):
        raise ValueError("Phase 597 raw coarse-authority gate drift")
    fake_spec = review["sources"]["candidate_fake_coarse_manifest"]
    fake_identity = coarse["fake_coarse_manifest"]
    if (
        not isinstance(fake_identity, dict)
        or Path(fake_identity.get("path", "")).resolve()
        != (phase597_dir / fake_spec["path"]).resolve()
        or fake_identity.get("sha256") != fake_spec["sha256"]
        or fake_identity.get("entries_sha256")
        != fake_spec["entries_sha256"]
        or fake_identity.get("entries") != fake_spec["entries"]
        or fake_identity.get("candidate_only") is not True
    ):
        raise ValueError("Phase 597 raw fake/coarse identity drift")
    disposition_spec = review["sources"]["candidate_transition_dispositions"]
    disposition_identity = coarse["candidate_transition_dispositions"]
    if (
        not isinstance(disposition_identity, dict)
        or Path(disposition_identity.get("path", "")).resolve()
        != (phase597_dir / disposition_spec["path"]).resolve()
        or disposition_identity.get("sha256") != disposition_spec["sha256"]
        or disposition_identity.get("source_phase") != 597
        or disposition_identity.get("entries") != 1
        or disposition_identity.get("statuses")
        != {"retired_fake_marker_transition_pending_review": 1}
    ):
        raise ValueError("Phase 597 raw transition disposition drift")

    accounting = report["accounting"]
    expected_accounting = contract["accounting"]
    if (
        not isinstance(accounting, dict)
        or any(
            accounting.get(key) != value
            for key, value in expected_accounting.items()
        )
        or accounting.get("runtime_candidate_lines")
        + accounting.get("excluded_lines")
        != accounting.get("input_lines")
        or set(accounting.get("exclusion_line_numbers", {})) != {"comment"}
    ):
        raise ValueError("Phase 597 raw line accounting drift")
    comment_lines = accounting["exclusion_line_numbers"]["comment"]
    if (
        not isinstance(comment_lines, list)
        or len(comment_lines) != accounting["excluded_lines"]
        or any(
            not isinstance(line, int) or not 1 <= line <= 62313
            for line in comment_lines
        )
        or comment_lines != sorted(set(comment_lines))
        or stable_json_sha256(comment_lines)
        != measurement["comment_line_numbers_sha256"]
    ):
        raise ValueError("Phase 597 raw comment exclusion projection drift")

    boundary = report["three_language_boundary"]
    if (
        not isinstance(boundary, dict)
        or any(boundary.get(key) != 0 for key in contract["boundary_zero_fields"])
        or boundary.get("all_mismatches") != []
        or boundary.get("all_token_mismatches") != []
    ):
        raise ValueError("Phase 597 JA/ZH/KO boundary mismatch")
    stability = report["inputs_stable"]
    if (
        not isinstance(stability, dict)
        or tuple(stability) != tuple(contract["required_input_stability"])
        or any(stability[key] is not True for key in stability)
    ):
        raise ValueError("Phase 597 raw inputs were not stable")
    if report["candidate_audit"] != contract["candidate_audit"]:
        raise ValueError("Phase 597 raw candidate-only contract drift")

    coarse_rows = coarse["languages"]
    if (
        not isinstance(coarse_rows, list)
        or [row.get("language") for row in coarse_rows] != list(LANGUAGES)
    ):
        raise ValueError("Phase 597 coarse-authority language order drift")
    canonical_mismatches = None
    mismatch_count = measurement["fake_mismatch_count_per_language"]
    mismatch_sha256 = measurement["fake_mismatch_projection_sha256"]
    for row in coarse_rows:
        language = row["language"]
        if set(row) != RAW_COARSE_LANGUAGE_KEYS:
            raise ValueError(
                f"Phase 597 {language} coarse-language schema drift"
            )
        counts = row["counts"]
        if (
            not isinstance(counts, dict)
            or counts.get("rows") != contract["authority_rows"]
            or counts.get("mismatched") != mismatch_count
            or counts.get("matched") + counts.get("mismatched")
            != contract["authority_rows"]
            or counts.get("transition_rows")
            != contract["staged_transition_expected_rows"]["combined"]
            or counts.get("transition_matched")
            != contract["staged_transition_expected_rows"]["combined"]
            or counts.get("transition_mismatched", 0) != 0
            or len(row["mismatches"]) != mismatch_count
            or stable_json_sha256(row["mismatches"]) != mismatch_sha256
        ):
            raise ValueError(
                f"Phase 597 {language} fake/coarse projection drift"
            )
        expected_scopes = {
            scope: {"matched": count}
            for scope, count in contract[
                "staged_transition_expected_rows"
            ].items()
            if scope
            not in {"combined", "historical_total_before_candidate_dispositions"}
        }
        if row["transition_scopes"] != expected_scopes:
            raise ValueError(
                f"Phase 597 {language} transition-scope drift"
            )
        if canonical_mismatches is None:
            canonical_mismatches = row["mismatches"]
        elif row["mismatches"] != canonical_mismatches:
            raise ValueError(
                "Phase 597 fake/coarse mismatch queue differs across JA/ZH/KO"
            )

    language_rows = report["languages"]
    if (
        not isinstance(language_rows, list)
        or [row.get("language") for row in language_rows] != list(LANGUAGES)
    ):
        raise ValueError("Phase 597 raw language scope/order drift")
    language_reports = [
        _validate_raw_language(row, contract, measurement)
        for row in language_rows
    ]
    semantic_sha256 = stable_json_sha256(
        raw_report_semantic_projection(report)
    )
    if semantic_sha256 != measurement["raw_semantic_projection_sha256"]:
        raise ValueError("Phase 597 raw semantic projection drift")
    return {
        "phase": 597,
        "languages": list(LANGUAGES),
        "input_lines": accounting["input_lines"],
        "runtime_candidate_lines": accounting["runtime_candidate_lines"],
        "runtime_unique_surfaces": accounting["runtime_unique_surfaces"],
        "render_union_unique_surfaces": accounting[
            "render_union_unique_surfaces"
        ],
        "boundary_mismatches": 0,
        "runtime_issues": 0,
        "effective_width_over_2": 0,
        "fake_mismatch_count_per_language": mismatch_count,
        "fake_mismatch_projection_sha256": mismatch_sha256,
        "fake_mismatch_queue_semantic_approval": False,
        "admitted_residuals": 1,
        "atletiko_only_sidecar_admission": True,
        "master_promotion_gate": False,
        "full_fake_coarse_semantic_gate": False,
        "raw_semantic_projection_sha256": semantic_sha256,
        "language_reports": language_reports,
        "gate": True,
    }


def _payload_compact_hashes(payloads: dict, compact_hasher) -> dict:
    return {
        language: compact_hasher(payloads[language])
        for language in LANGUAGES
    }


def run_deployed_predecessor_gates(*, batch_size: int = 20) -> dict:
    """Run Phase 532/558/598 plus final Phase 599/600 deployed closures."""
    import phase532_activation
    import phase532_runtime_signature_gate as phase532_runtime
    import phase558_ruby_overlay_activation
    import phase558_ruby_overlay_runtime_gate as phase558_runtime
    import phase598_technical_on_activation
    import phase598_technical_on_runtime_gate as phase598_runtime
    import phase599_temis_context_promotion
    import phase600_master_ruby_repair

    phase532_activation_report = phase532_activation.activation_report()
    phase532_payloads = phase532_runtime.load_deployed_payloads()
    phase532_report = phase532_runtime.validate_generated_payloads(
        phase532_payloads,
        "post-regen",
        batch_size=min(max(batch_size, 1), 58),
    )
    phase532_reloaded = phase532_runtime.load_deployed_payloads()
    phase532_final_fingerprints = {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in LANGUAGES
    }
    if (
        _payload_compact_hashes(
            phase532_reloaded, phase532_runtime.compact_sha256,
        )
        != phase532_report["candidate_payload_sha256"]
        or phase532_final_fingerprints
        != phase532_report["app_input_fingerprints"]
    ):
        raise ValueError(
            "Phase 532 deployed payload changed across load/render/reload"
        )
    phase532_report["deployed_snapshot_revalidated"] = True

    phase558_activation_report = (
        phase558_ruby_overlay_activation.activation_report()
    )
    phase558_report = phase558_runtime.validate_deployed_payloads(
        "post-regen",
        batch_size=min(max(batch_size, 1), 33),
    )
    phase598_activation_report = (
        phase598_technical_on_activation.activation_report()
    )
    phase598_report = phase598_runtime.validate_deployed_payloads(
        batch_size=min(max(batch_size, 1), 50),
    )
    phase599_report = (
        phase599_temis_context_promotion.audit_deployed_promotion(
            batch_size=min(max(batch_size, 1), 20),
        )
    )
    phase600_report = phase600_master_ruby_repair.audit_deployed_repair(
        batch_size=min(max(batch_size, 1), 20),
    )
    final_fingerprints = {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in LANGUAGES
    }
    if final_fingerprints != phase598_report["app_input_fingerprints"]:
        raise ValueError(
            "deployed app snapshot changed across predecessor gates"
        )
    return {
        "phase532": {
            "activation": phase532_activation_report,
            "runtime": phase532_report,
        },
        "phase558": {
            "activation": phase558_activation_report,
            "runtime": phase558_report,
        },
        "phase598": {
            "activation": phase598_activation_report,
            "runtime": phase598_report,
        },
        "phase599": phase599_report,
        "phase600": phase600_report,
        "final_app_fingerprints": final_fingerprints,
    }


def validate_deployed_predecessor_reports(
    reports: dict, review: dict,
) -> dict:
    requirements = review["deployed_predecessor_requirements"]
    measurement = require_sealed_runtime_measurement(review)
    expected_top = {
        "phase532",
        "phase558",
        "phase598",
        "phase599",
        "phase600",
        "final_app_fingerprints",
    }
    if not isinstance(reports, dict) or set(reports) != expected_top:
        raise ValueError("Phase 597 predecessor report schema drift")

    phase532 = reports["phase532"]
    phase558 = reports["phase558"]
    phase598 = reports["phase598"]
    if (
        phase532["activation"].get("phase532_active") is not True
        or phase532["activation"].get("gate") is not True
        or phase558["activation"].get("phase558_ruby_overlay_active")
        is not True
        or phase558["activation"].get("gate") is not True
        or phase598["activation"].get("phase598_technical_on_active")
        is not True
        or phase598["activation"].get("gate") is not True
    ):
        raise ValueError("Phase 597 predecessor activation chain failed")
    p532 = phase532["runtime"]
    p558 = phase558["runtime"]
    p598 = phase598["runtime"]
    if (
        p532.get("mode") != requirements["phase532"]["runtime_mode"]
        or p532.get("surfaces") != requirements["phase532"]["surfaces"]
        or p532.get("selected_target_mismatches")
        != requirements["phase532"]["selected_target_mismatches"]
        or p532.get("trilingual_mismatches")
        != requirements["phase532"]["trilingual_mismatches"]
        or p532.get("all_inputs_stable") is not True
        or p532.get("deployed_snapshot_revalidated") is not True
        or p532.get("gate") is not True
    ):
        raise ValueError("Phase 532 deployed predecessor gate failed")
    if (
        p558.get("mode") != requirements["phase558"]["runtime_mode"]
        or p558.get("surfaces") != requirements["phase558"]["surfaces"]
        or p558.get("trilingual_mismatches")
        != requirements["phase558"]["trilingual_mismatches"]
        or p558.get("scope_guard_gate") is not True
        or p558.get("payload_variant_gate") is not True
        or p558.get("payload_gloss_gate") is not True
        or p558.get("all_inputs_stable") is not True
        or p558.get("deployed_snapshot_revalidated") is not True
        or p558.get("gate") is not True
    ):
        raise ValueError("Phase 558 deployed predecessor gate failed")
    if (
        p598.get("positive_surfaces")
        != requirements["phase598"]["positive_surfaces"]
        or p598.get("negative_surfaces")
        != requirements["phase598"]["negative_surfaces"]
        or p598.get("combined_surfaces")
        != requirements["phase598"]["combined_surfaces"]
        or p598.get("positive_payload_gate") is not True
        or p598.get("width_gate") is not True
        or p598.get("trilingual_boundary_mismatches")
        != requirements["phase598"]["trilingual_boundary_mismatches"]
        or p598.get("trilingual_rb_mismatches")
        != requirements["phase598"]["trilingual_rb_mismatches"]
        or p598.get("all_inputs_stable") is not True
        or p598.get("deployed_snapshot_revalidated") is not True
        or p598.get("gate") is not True
    ):
        raise ValueError("Phase 598 deployed predecessor gate failed")

    fingerprints = measurement["current_app_fingerprints"]
    if (
        p532.get("app_input_fingerprints") != fingerprints
        or p558.get("app_input_fingerprints") != fingerprints
        or p598.get("app_input_fingerprints") != fingerprints
        or reports["final_app_fingerprints"] != fingerprints
        or p532.get("candidate_payload_sha256")
        != p558.get("candidate_payload_sha256")
    ):
        raise ValueError(
            "Phase 597 predecessor gates do not share one deployed snapshot"
        )
    # Phase 532/558 preserve JSON key order in their compact semantic hash,
    # while Phase 598 deliberately uses ``sort_keys=True``.  Their digest
    # strings are therefore not cross-algorithm identities.  The complete
    # raw app fingerprints above (including each deployed payload file SHA)
    # are the common snapshot authority; every individual runtime gate also
    # reloaded and rebound its own semantic hash before returning.

    p599 = reports["phase599"]
    expected_rows = {
        language: requirements["phase599"][
            "final_global_rows_per_language"
        ]
        for language in LANGUAGES
    }
    expected_preserved = {
        language: requirements["phase599"][
            "phase600_rows_preserved_per_language"
        ]
        for language in LANGUAGES
    }
    if (
        p599.get("promotion_audit_gate") is not True
        or p599.get("gate") is not True
        or p599.get("already_promoted") is not True
        or p599.get("writes_required") != 0
        or p599.get("deployed_global_rows_per_language") != expected_rows
        or p599.get("phase600_rows_preserved_per_language")
        != expected_preserved
        or p599.get("later_phase600", {}).get("gate") is not True
        or p599.get("later_phase600", {}).get(
            "deployed_global_rows_per_language"
        )
        != expected_rows
        or p599.get("kanji_nonintervention") is not True
    ):
        raise ValueError("Phase 599 final deployed preservation gate failed")
    p600 = reports["phase600"]
    if (
        p600.get("deployed_repair_gate") is not True
        or p600.get("gate") is not True
        or p600.get("already_promoted") is not True
        or p600.get("writes_required") != 0
        or p600.get("managed_rows_per_language")
        != requirements["phase600"]["managed_rows_per_language"]
        or p600.get("post_phase600_global_rows")
        != requirements["phase600"]["final_global_rows_per_language"]
        or p600.get("trilingual", {}).get("gate") is not True
        or p600.get("width", {}).get("gate") is not True
        or p600.get("kanji_nonintervention") is not True
    ):
        raise ValueError("Phase 600 final deployed repair gate failed")
    for language in LANGUAGES:
        raw_payload_sha = _fingerprint_value(
            fingerprints[language],
            f"Esperanto-Kanji-Ruby-{language}/app_data/置換リスト_ルビ.json",
        )
        if (
            p599.get("deployed_payload_sha256_before", {}).get(language)
            != raw_payload_sha
            or p600.get("deployed_payload_sha256_before", {}).get(language)
            != raw_payload_sha
        ):
            raise ValueError(
                f"Phase 599/600 {language} payload snapshot drift"
            )
        if (
            p599.get("states", {}).get(language, {}).get(
                "deployed_global_rows"
            )
            != expected_rows[language]
            or p600.get("states", {}).get(language, {}).get("state")
            != "promoted_canonical"
            or p600.get("states", {}).get(language, {}).get(
                "promoted_global_rows"
            )
            != expected_rows[language]
        ):
            raise ValueError(
                f"Phase 599/600 {language} canonical state drift"
            )
    return {
        "phases": [532, 558, 598, 599, 600],
        "deployed_snapshot_identical": True,
        "final_global_rows_per_language": expected_rows,
        "phase600_rows_preserved_per_language": expected_preserved,
        "kanji_nonintervention": True,
        "gate": True,
    }


def render_deployed_atletiko(*, review: dict | None = None) -> dict:
    """Render only ``atletiko`` and retain exact rb/rt annotations."""
    from gen_replacement import load_app_replacement_helper

    if review is None:
        review = load_review()
    require_sealed_runtime_measurement(review)
    expected = review["atletiko_two_track_adjudication"]["ruby_track"]
    fingerprint_before = {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in LANGUAGES
    }
    rendered = {}
    for language in LANGUAGES:
        app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
        load_app_replacement_helper(app_dir)
        payload = json.loads(
            (app_dir / "app_data" / "置換リスト_ルビ.json").read_text(
                encoding="utf-8"
            )
        )
        runtime = audit.runtime_module(
            app_dir, f"phase597_successor_atletiko_{language}",
        )
        overlay = audit.overlay_module(
            app_dir, f"phase597_successor_atletiko_overlay_{language}",
        )
        corrections = json.loads(
            (app_dir / "app_data" / "user_corrections.json").read_text(
                encoding="utf-8"
            )
        )
        rendered[language] = audit.render_signatures(
            runtime,
            app_dir,
            payload,
            ["atletiko"],
            1,
            overlay=overlay,
            corrections=corrections,
            include_annotations=True,
        )["atletiko"]
    fingerprint_after = {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in LANGUAGES
    }
    if (
        fingerprint_after != fingerprint_before
        or fingerprint_after
        != review["runtime_measurement"]["current_app_fingerprints"]
    ):
        raise ValueError("atletiko deployed app inputs changed during rendering")
    return {
        "surface": "atletiko",
        "languages": rendered,
        "app_input_fingerprints": fingerprint_after,
    }


def _typed_signature(signature) -> str:
    _reconstruction, spans = signature
    return "|".join(
        f"{'R' if is_ruby else 'L'}:{text}"
        for text, is_ruby in spans
    )


def validate_atletiko_runtime(
    focused_report: dict, review: dict,
) -> dict:
    expected = review["atletiko_two_track_adjudication"]["ruby_track"]
    if (
        not isinstance(focused_report, dict)
        or focused_report.get("surface") != "atletiko"
        or set(focused_report.get("languages", {})) != set(LANGUAGES)
        or focused_report.get("app_input_fingerprints")
        != review["runtime_measurement"]["current_app_fingerprints"]
    ):
        raise ValueError("Phase 597 atletiko focused runtime schema drift")
    normalized = {}
    for language in LANGUAGES:
        row = focused_report["languages"][language]
        if not isinstance(row, dict):
            raise ValueError(f"Phase 597 {language} atletiko row drift")
        signature = row.get("signature")
        try:
            typed = _typed_signature(signature)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Phase 597 {language} atletiko signature is invalid"
            ) from error
        expected_annotation = expected["languages"][language]
        if (
            typed != expected["typed_signature"]
            or row.get("decomposition") != expected["decomposition"]
            or row.get("typed_decomposition") != expected["typed_signature"]
            or row.get("annotations") != [expected_annotation]
        ):
            raise ValueError(
                f"Phase 597 {language} atletiko two-track runtime drift"
            )
        normalized[language] = {
            "typed_signature": typed,
            "annotations": row["annotations"],
        }
    if len({row["typed_signature"] for row in normalized.values()}) != 1:
        raise ValueError("Phase 597 atletiko trilingual boundary mismatch")
    return {
        "surface": "atletiko",
        "ruby_decomposition": expected["decomposition"],
        "kanji_master_decomposition": "atlet/ik/o",
        "languages": normalized,
        "trilingual_boundary_mismatches": 0,
        "admitted_two_track_residuals": 1,
        "atletiko_only_sidecar_admission": True,
        "master_promotion_gate": False,
        "gate": True,
    }


def validate_successor_gate(
    raw_report: dict,
    phase597_dir: Path,
    *,
    review: dict | None = None,
    expected_head: str | None = None,
    predecessor_runner=None,
    focused_renderer=None,
    batch_size: int = 20,
) -> dict:
    """Run the formal successor gate, failing before work when unsealed."""
    if review is None:
        review = load_review()
    # This ordering is intentional: an unsealed review must never launch the
    # expensive Phase 532/558/598/599/600 or focused runtime passes.
    require_sealed_runtime_measurement(review)
    raw_summary = validate_raw_report(
        raw_report,
        phase597_dir,
        review=review,
        expected_head=expected_head,
    )
    if predecessor_runner is None:
        predecessor_runner = run_deployed_predecessor_gates
    predecessor_reports = predecessor_runner(batch_size=batch_size)
    predecessor_summary = validate_deployed_predecessor_reports(
        predecessor_reports, review,
    )
    if focused_renderer is None:
        focused_renderer = render_deployed_atletiko
    focused_report = focused_renderer(review=review)
    atletiko_summary = validate_atletiko_runtime(focused_report, review)
    return {
        "schema_version": 1,
        "phase": 597,
        "audit_kind": "full_master_successor_runtime_integrity",
        "languages": list(LANGUAGES),
        "raw_audit": raw_summary,
        "deployed_predecessors": predecessor_summary,
        "atletiko_two_track": atletiko_summary,
        "trilingual_boundary_mismatches": 0,
        "effective_width_over_2": 0,
        "runtime_issues": 0,
        "admitted_residuals": 1,
        "atletiko_only_sidecar_admission": True,
        "fake_mismatch_queue_semantic_approval": False,
        "runtime_integrity_gate": True,
        "master_promotion_gate": False,
        "full_fake_coarse_semantic_gate": False,
        "gate": True,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--phase597-dir", type=Path, required=True)
    parser.add_argument("--deployed", action="store_true", required=True)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args(argv)
    if not 1 <= args.batch_size <= 20:
        raise ValueError("Phase 597 successor batch size must be in 1..20")
    review = load_review()
    report = _read_regular_json(args.audit, "Phase 597 raw audit report")
    result = validate_successor_gate(
        report,
        args.phase597_dir,
        review=review,
        expected_head=_git_head(),
        batch_size=args.batch_size,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
