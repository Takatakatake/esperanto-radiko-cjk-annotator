# -*- coding: utf-8 -*-
"""Successor no-worsening gate for the post-R93 deployed Ruby snapshot.

This gate is deliberately separate from the immutable Phase558 evidence.  A
fresh current-only audit over the frozen Phase532 reference union is written to
``out/_audit_no_worsening_post_r93.json``.  After that expensive audit has
finished, :mod:`build_post_r93_no_worsening_manifest` may create a small sealed
manifest.  This module then checks the raw report byte identity, the exact
reviewed residual contract, zero old-correct regressions/changed-wrong rows,
trilingual identity, and the deployed app input fingerprints.

``EXPECTED_MANIFEST_SHA256`` is the reviewed byte seal of that successor
manifest.  The default deployed gate fails closed if either the report, the
manifest, or any fingerprinted app input changes.
"""
from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import no_worsening_audit as audit
import phase558_no_worsening_sidecar_gate as phase558_schema


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPORT_RELATIVE_PATH = Path(
    "_analysis_20260625/out/_audit_no_worsening_post_r93.json"
)
MANIFEST_RELATIVE_PATH = Path(
    "_analysis_20260625/_post_r93_no_worsening_residual_manifest.json"
)
REPORT_PATH = ROOT / REPORT_RELATIVE_PATH
MANIFEST_PATH = ROOT / MANIFEST_RELATIVE_PATH
EXPECTED_MANIFEST_SHA256 = (
    "D426327CE438C74B78DDE5FC5938158F8BB85AF889A8C5B10E8027DDE139EFEA"
)

SCHEMA_VERSION = 1
GATE_ID = "post_r93_current_only_no_worsening"
LANGUAGES = ("JA", "ZH", "KO")

TOP_KEYS = set(phase558_schema.CURRENT_ONLY_TOP_KEYS)
LANGUAGE_KEYS = set(phase558_schema.CURRENT_ONLY_LANGUAGE_KEYS)
FINDING_KEYS = set(phase558_schema.FINDING_KEYS)
STAT_KEYS = set(phase558_schema.STAT_KEYS)
COMPARISON_KEYS = {
    "comparison", "sources", "combined", *FINDING_KEYS,
    "weighted_worsening_sources", "gate",
}

FIXED_REFERENCE = {
    "raw_cases": 68650,
    "resolved_cases": 68609,
    "surfaces": 68559,
    "raw_reference_sha256": (
        "C26EF076E4FC073868E99233567C3C3CE2A3D0C96E40701A83BD5520C7DA161B"
    ),
    "resolved_reference_sha256": (
        "7CE4C1DCCE293D98A0AB55B6832D13B55D5CCA5FFE90E0B9C050FB11F52577EF"
    ),
    "surface_sha256": (
        "E18AC7EAB4B89744A732C1DE3E3A6150D0FF7CA61D84073D662ED58AE384C489"
    ),
    "gold_sha256": (
        "6B403AA30BBCBBA4C9E41A2CF48D1AD2FC1D5A5DB1154CAF1260A361566E3226"
    ),
    "scope_manifest_sha256": (
        "13C989F4B4652CB2984AE96E5DAC3AECDAB6C40F37C7A6632BF5573B045599F0"
    ),
    "conflict_manifest_sha256": (
        "F6ABEC16CC73B2FE74F3F4ECC2803582CB0AD09288B620CCFC2226E0C6B40522"
    ),
    "corpus_content_sha256": (
        "33ED6EA94E45A5434B3AAE035F8C44D97278ACABA9A83714A0167EC0754C70B8"
    ),
    "corpus_head_oid": "dd55318c33b36128e64561d4ae7fca587ad974fa",
    "corpus_status_sha256": (
        "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
    ),
    "total_weight": 324757,
    "total_cases": 74444,
}

EXPECTED_SOURCE_NAMES = {
    "gold_fake_coarse_paired_academic",
    "gold_fake_coarse_pejvo_original",
    "gold_fake_coarse_project_reviewed_override",
    "gold_official_override",
    "gold_phase532_selected_ruby_policy",
    "gold_project_ruby_boundary_override",
    "gold_unmarked",
    "html_corpus",
    "html_place_manifest",
}

# These are reviewed semantic facts, not values inferred from a provisional
# report.  The builder will refuse to seal a report that changes the exact set
# or any of these post-R93 typed signatures.
EXPECTED_RESIDUALS = (
    {
        "surface": "Gaŭlo-Romiano",
        "current_typed": "R:Gaŭl|L:o-|R:Romi|R:an|L:o",
        "provenance": "r85_hyphen_joiner",
    },
    {
        "surface": "Izraelio",
        "current_typed": "R:Izrael|L:io",
        "provenance": "phase558_reviewed_predecessor",
    },
    {
        "surface": "endoskopio",
        "current_typed": "R:endoskopi|L:o",
        "provenance": "phase619_reviewed_coarse_ruby",
    },
    {
        "surface": "glu-glu-glu",
        "current_typed": "R:glu-glu-glu",
        "provenance": "r79_reviewed_atomic_onomatopoeia",
    },
    {
        "surface": "imperialisto",
        "current_typed": "R:imperialist|L:o",
        "provenance": "phase619_reviewed_coarse_ruby",
    },
    {
        "surface": "mikroskopio",
        "current_typed": "R:mikroskopi|L:o",
        "provenance": "phase619_reviewed_coarse_ruby",
    },
    {
        "surface": "mukozaĵo",
        "current_typed": "R:mukoz|R:aĵ|L:o",
        "provenance": "phase619_reviewed_coarse_ruby",
    },
    {
        "surface": "nor",
        "current_typed": "L:nor",
        "provenance": "r79_guarded_nonactivation",
    },
    {
        "surface": "reprezenti",
        "current_typed": "R:reprezent|L:i",
        "provenance": "r94_kyoto_coarse_reprezent_family",
    },
    {
        "surface": "tia-tia",
        "current_typed": "R:tia|L:-|R:tia",
        "provenance": "phase558_reviewed_predecessor",
    },
)
EXPECTED_RESIDUAL_BY_SURFACE = {
    row["surface"]: row for row in EXPECTED_RESIDUALS
}
EXPECTED_RESIDUAL_SURFACES = tuple(EXPECTED_RESIDUAL_BY_SURFACE)
EXPECTED_PROVENANCE_COUNTS = dict(sorted(Counter(
    row["provenance"] for row in EXPECTED_RESIDUALS
).items()))
EXPECTED_OFFICIAL_WRONG_SURFACES = ("glu-glu-glu",)
EXPECTED_EXACT_WRONG_SURFACES = ("glu-glu-glu",)

INPUT_STABILITY_KEYS = {
    "gold", "head", "corpus", "place_manifest", "audit_code",
    "review_manifests", "app_inputs",
}

COMMON_FINGERPRINT_SUFFIXES = {
    "main.py",
    "esp_text_replacement_module.py",
    "esp_overlay_module.py",
    "esp_replacement_json_make_module.py",
    "app_data/置換リスト_ルビ.json",
    "app_data/placeholders_skip.txt",
    "app_data/placeholders_localcapture.txt",
    "app_data/char_widths.json",
    "app_data/世界语词根-汉字对应列表_参照2新割当_7791.csv",
    "app_data/user_corrections.json",
}
LANGUAGE_RUBY_CSV = {
    "JA": "app_data/エスペラント語根-日本語訳ルビ対応リスト.csv",
    "ZH": "app_data/世界语词根-中文注释对应列表.csv",
    "KO": "app_data/에스페란토 어근-한국어 번역 루비 대응 목록.csv",
}

MANIFEST_TOP_KEYS = {
    "schema_version", "gate_id", "report", "reference_projection",
    "languages", "expected_counts", "residual_contract",
    "provenance_counts", "sealed",
}
REPORT_IDENTITY_KEYS = {"path", "bytes", "sha256"}
EXPECTED_COUNT_KEYS = {
    "raw_cases", "resolved_cases", "surfaces",
    "residual_surfaces_per_language",
    "official_wrong_cases_per_language",
    "exact_wrong_cases_per_language",
    "regression_cases", "changed_wrong_surfaces",
    "trilingual_residual_mismatches",
}
SEALED_KEYS = {
    "residual_entries_sha256", "official_wrong_entries_sha256",
    "exact_wrong_entries_sha256", "source_statistics_sha256",
    "combined_statistics", "app_input_fingerprints",
    "app_input_fingerprints_sha256", "checkpoint_context_sha256",
    "scope_sha256", "reviewed_reference_sha256",
    "inputs_stable_sha256",
}


def stable_sha256(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest().upper()


def raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.upper()
        and all(character in "0123456789ABCDEF" for character in value)
    )


def expected_fingerprint_paths(language: str) -> set[str]:
    prefix = f"Esperanto-Kanji-Ruby-{language}/"
    suffixes = set(COMMON_FINGERPRINT_SUFFIXES)
    suffixes.add(LANGUAGE_RUBY_CSV[language])
    return {prefix + suffix for suffix in suffixes}


def _validate_fingerprints(fingerprints: Any) -> None:
    if not isinstance(fingerprints, dict) or set(fingerprints) != set(LANGUAGES):
        raise ValueError("post-R93 app fingerprints must be exactly JA/ZH/KO")
    for language in LANGUAGES:
        row = fingerprints[language]
        if (
            not isinstance(row, dict)
            or set(row) != expected_fingerprint_paths(language)
            or any(not is_sha256(value) for value in row.values())
        ):
            raise ValueError(
                f"post-R93 {language} app input fingerprint schema drift"
            )


def _typed_from_signature(payload: Any, *, surface: str) -> str:
    if (
        not isinstance(payload, dict)
        or set(payload) != {"reconstruction", "spans"}
        or payload.get("reconstruction") != surface
        or not isinstance(payload.get("spans"), list)
        or not payload["spans"]
    ):
        raise ValueError(f"invalid signature payload for {surface!r}")
    parts = []
    reconstruction = ""
    for span in payload["spans"]:
        if (
            not isinstance(span, dict)
            or set(span) != {"text", "ruby"}
            or not isinstance(span["text"], str)
            or not span["text"]
            or not isinstance(span["ruby"], bool)
        ):
            raise ValueError(f"invalid signature span for {surface!r}")
        reconstruction += span["text"]
        parts.append(f"{'R' if span['ruby'] else 'L'}:{span['text']}")
    if reconstruction != surface:
        raise ValueError(f"signature reconstruction drift for {surface!r}")
    return "|".join(parts)


def _surface_sequence(rows: Any, *, bucket: str) -> tuple[str, ...]:
    if not isinstance(rows, list):
        raise ValueError(f"post-R93 {bucket} must be a list")
    surfaces = []
    for row in rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("surface"), str)
            or not row["surface"]
        ):
            raise ValueError(f"post-R93 invalid finding in {bucket}")
        surfaces.append(row["surface"])
    if len(surfaces) != len(set(surfaces)):
        raise ValueError(f"post-R93 duplicate surface in {bucket}")
    return tuple(surfaces)


def _validate_residual_entries(rows: Any) -> None:
    surfaces = _surface_sequence(
        rows, bucket="current_unreferenced_wrong_surfaces",
    )
    if surfaces != EXPECTED_RESIDUAL_SURFACES:
        raise ValueError(
            "post-R93 residual set drift (the reviewed set is exact): "
            f"{surfaces!r}"
        )
    expected_keys = {
        "surface", "expected_options", "expected_signatures", "sources",
        "baseline", "baseline_typed", "current", "current_typed",
        "current_signature",
    }
    for row in rows:
        surface = row["surface"]
        if set(row) != expected_keys:
            raise ValueError(f"post-R93 residual schema drift: {surface}")
        if (
            not isinstance(row["expected_options"], list)
            or not row["expected_options"]
            or any(not isinstance(value, str) for value in row["expected_options"])
            or not isinstance(row["expected_signatures"], list)
            or not row["expected_signatures"]
            or not isinstance(row["sources"], list)
            or not row["sources"]
            or any(not isinstance(value, str) for value in row["sources"])
            or row["baseline"] != row["current"]
            or row["baseline_typed"] != row["current_typed"]
        ):
            raise ValueError(f"post-R93 current-only residual drift: {surface}")
        current_typed = _typed_from_signature(
            row["current_signature"], surface=surface,
        )
        if (
            current_typed != row["current_typed"]
            or current_typed
            != EXPECTED_RESIDUAL_BY_SURFACE[surface]["current_typed"]
        ):
            raise ValueError(f"post-R93 typed residual drift: {surface}")
        expected_typed = {
            _typed_from_signature(payload, surface=surface)
            for payload in row["expected_signatures"]
        }
        if current_typed in expected_typed:
            raise ValueError(f"post-R93 non-residual was listed as wrong: {surface}")


def _validate_stats(stats: Any, *, label: str) -> None:
    if not isinstance(stats, dict) or set(stats) != STAT_KEYS:
        raise ValueError(f"post-R93 statistics schema drift: {label}")
    if any(not isinstance(stats[key], int) or stats[key] < 0 for key in STAT_KEYS):
        raise ValueError(f"post-R93 invalid statistics value: {label}")
    if (
        stats["baseline_correct_weight"] != stats["current_correct_weight"]
        or stats["baseline_correct_cases"] != stats["current_correct_cases"]
        or stats["regression_weight"] != 0
        or stats["regression_cases"] != 0
        or stats["improvement_weight"] != 0
        or stats["improvement_cases"] != 0
    ):
        raise ValueError(f"post-R93 old-correct regression/stat drift: {label}")


def _validate_comparison(comparison: Any, *, language: str) -> dict:
    if not isinstance(comparison, dict) or set(comparison) != COMPARISON_KEYS:
        raise ValueError(f"post-R93 {language} comparison schema drift")
    if comparison["comparison"] != "current_only" or comparison["gate"] is not False:
        raise ValueError(f"post-R93 {language} comparison identity drift")
    if set(comparison["sources"]) != EXPECTED_SOURCE_NAMES:
        raise ValueError(f"post-R93 {language} source set drift")
    for source, stats in comparison["sources"].items():
        _validate_stats(stats, label=f"{language}/{source}")
    _validate_stats(comparison["combined"], label=f"{language}/combined")
    recomputed = {
        key: sum(stats[key] for stats in comparison["sources"].values())
        for key in STAT_KEYS
    }
    if recomputed != comparison["combined"]:
        raise ValueError(f"post-R93 {language} combined statistics drift")
    if (
        comparison["combined"]["total_weight"]
        != FIXED_REFERENCE["total_weight"]
        or comparison["combined"]["total_cases"]
        != FIXED_REFERENCE["total_cases"]
    ):
        raise ValueError(f"post-R93 {language} fixed statistics scope drift")

    for bucket in (
        "regression_cases",
        "changed_to_unreferenced_wrong_surfaces",
        "current_place_manifest_wrong_cases",
        "current_project_ruby_boundary_override_wrong_cases",
        "weighted_worsening_sources",
    ):
        if comparison[bucket] != []:
            raise ValueError(f"post-R93 forbidden nonempty finding: {bucket}")
    _validate_residual_entries(
        comparison["current_unreferenced_wrong_surfaces"]
    )
    official = _surface_sequence(
        comparison["current_official_override_wrong_cases"],
        bucket="current_official_override_wrong_cases",
    )
    exact = _surface_sequence(
        comparison["current_exact_required_wrong_cases"],
        bucket="current_exact_required_wrong_cases",
    )
    if official != EXPECTED_OFFICIAL_WRONG_SURFACES:
        raise ValueError(f"post-R93 official-override residual drift: {official!r}")
    if exact != EXPECTED_EXACT_WRONG_SURFACES:
        raise ValueError(f"post-R93 exact-required residual drift: {exact!r}")
    return {
        "residual_entries": comparison["current_unreferenced_wrong_surfaces"],
        "official_entries": comparison["current_official_override_wrong_cases"],
        "exact_entries": comparison["current_exact_required_wrong_cases"],
        "statistics": {
            "sources": comparison["sources"],
            "combined": comparison["combined"],
        },
    }


def _validate_reference_identity(report: dict) -> None:
    projection = report.get("reference_projection")
    resolved = report.get("resolved_reference")
    reviewed = report.get("reviewed_reference")
    checkpoint = report.get("checkpoint_context")
    scope = report.get("scope")
    if not all(isinstance(value, dict) for value in (
        projection, resolved, reviewed, checkpoint, scope,
    )):
        raise ValueError("post-R93 reference identity is incomplete")
    if (
        report["raw_case_count"] != FIXED_REFERENCE["raw_cases"]
        or report["case_count"] != FIXED_REFERENCE["resolved_cases"]
        or report["surface_count"] != FIXED_REFERENCE["surfaces"]
        or projection.get("case_count") != FIXED_REFERENCE["raw_cases"]
        or projection.get("surface_count") != FIXED_REFERENCE["surfaces"]
        or projection.get("reference_sha256")
        != FIXED_REFERENCE["raw_reference_sha256"]
        or resolved.get("case_count") != FIXED_REFERENCE["resolved_cases"]
        or resolved.get("surface_count") != FIXED_REFERENCE["surfaces"]
        or resolved.get("reference_sha256")
        != FIXED_REFERENCE["resolved_reference_sha256"]
    ):
        raise ValueError("post-R93 fixed Phase532 reference projection drift")
    selected_checkpoint = {
        "raw_reference_sha256": FIXED_REFERENCE["raw_reference_sha256"],
        "reference_sha256": FIXED_REFERENCE["resolved_reference_sha256"],
        "surface_sha256": FIXED_REFERENCE["surface_sha256"],
        "corpus_sha256": FIXED_REFERENCE["corpus_content_sha256"],
        "corpus_head_oid": FIXED_REFERENCE["corpus_head_oid"],
        "corpus_status_sha256": FIXED_REFERENCE["corpus_status_sha256"],
        "gold_sha256": FIXED_REFERENCE["gold_sha256"],
        "scope_manifest_sha256": FIXED_REFERENCE["scope_manifest_sha256"],
        "conflict_manifest_sha256": FIXED_REFERENCE[
            "conflict_manifest_sha256"
        ],
    }
    if any(checkpoint.get(key) != value for key, value in selected_checkpoint.items()):
        raise ValueError("post-R93 checkpoint reference identity drift")
    if (
        reviewed.get("scope_manifest_sha256")
        != FIXED_REFERENCE["scope_manifest_sha256"]
        or reviewed.get("conflict_manifest_sha256")
        != FIXED_REFERENCE["conflict_manifest_sha256"]
        or scope.get("gold", {}).get("sha256")
        != FIXED_REFERENCE["gold_sha256"]
        or scope.get("corpus", {}).get("content_sha256")
        != FIXED_REFERENCE["corpus_content_sha256"]
        or scope.get("corpus_repository", {}).get("head_oid")
        != FIXED_REFERENCE["corpus_head_oid"]
        or scope.get("corpus_repository", {}).get("status_sha256")
        != FIXED_REFERENCE["corpus_status_sha256"]
    ):
        raise ValueError("post-R93 audited source identity drift")


def validate_manifest(
    manifest: Any, *, gate_id: str = GATE_ID,
    report_relative_path: Path = REPORT_RELATIVE_PATH,
) -> dict:
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_TOP_KEYS:
        raise ValueError("post-R93 manifest schema drift")
    if manifest["schema_version"] != SCHEMA_VERSION or manifest["gate_id"] != gate_id:
        raise ValueError("post-R93 manifest identity drift")
    report_identity = manifest["report"]
    if (
        not isinstance(report_identity, dict)
        or set(report_identity) != REPORT_IDENTITY_KEYS
        or report_identity["path"] != report_relative_path.as_posix()
        or not isinstance(report_identity["bytes"], int)
        or report_identity["bytes"] <= 0
        or not is_sha256(report_identity["sha256"])
    ):
        raise ValueError("post-R93 raw report identity drift")
    if manifest["reference_projection"] != FIXED_REFERENCE:
        raise ValueError("post-R93 manifest reference projection drift")
    if manifest["languages"] != list(LANGUAGES):
        raise ValueError("post-R93 manifest language drift")
    expected_counts = {
        "raw_cases": FIXED_REFERENCE["raw_cases"],
        "resolved_cases": FIXED_REFERENCE["resolved_cases"],
        "surfaces": FIXED_REFERENCE["surfaces"],
        "residual_surfaces_per_language": len(EXPECTED_RESIDUALS),
        "official_wrong_cases_per_language": 1,
        "exact_wrong_cases_per_language": 1,
        "regression_cases": 0,
        "changed_wrong_surfaces": 0,
        "trilingual_residual_mismatches": 0,
    }
    if (
        not isinstance(manifest["expected_counts"], dict)
        or set(manifest["expected_counts"]) != EXPECTED_COUNT_KEYS
        or manifest["expected_counts"] != expected_counts
    ):
        raise ValueError("post-R93 manifest count contract drift")
    if manifest["residual_contract"] != list(EXPECTED_RESIDUALS):
        raise ValueError("post-R93 manifest residual contract drift")
    if manifest["provenance_counts"] != EXPECTED_PROVENANCE_COUNTS:
        raise ValueError("post-R93 manifest provenance contract drift")
    sealed = manifest["sealed"]
    if not isinstance(sealed, dict) or set(sealed) != SEALED_KEYS:
        raise ValueError("post-R93 manifest sealed schema drift")
    for key in SEALED_KEYS - {"combined_statistics", "app_input_fingerprints"}:
        if not is_sha256(sealed[key]):
            raise ValueError(f"post-R93 manifest invalid sealed digest: {key}")
    _validate_fingerprints(sealed["app_input_fingerprints"])
    if stable_sha256(sealed["app_input_fingerprints"]) != sealed[
        "app_input_fingerprints_sha256"
    ]:
        raise ValueError("post-R93 manifest app fingerprint digest drift")
    _validate_stats(sealed["combined_statistics"], label="manifest/combined")
    return manifest


def deployed_app_fingerprints() -> dict:
    return {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in LANGUAGES
    }


def validate_report(
    report: Any, *, manifest: dict | None = None,
    current_fingerprints: dict | None = None,
    gate_id: str = GATE_ID,
    report_relative_path: Path = REPORT_RELATIVE_PATH,
) -> dict:
    if not isinstance(report, dict) or set(report) != TOP_KEYS:
        raise ValueError("post-R93 current-only report schema drift")
    if report.get("complete") is not True or report.get("gate") is not False:
        raise ValueError("post-R93 report must be complete with reviewed residuals")
    _validate_reference_identity(report)
    stability = report.get("inputs_stable")
    if (
        not isinstance(stability, dict)
        or set(stability) != INPUT_STABILITY_KEYS
        or any(value is not True for value in stability.values())
    ):
        raise ValueError("post-R93 report input stability drift")
    rows = report.get("languages")
    if (
        not isinstance(rows, list)
        or [row.get("language") for row in rows if isinstance(row, dict)]
        != list(LANGUAGES)
    ):
        raise ValueError("post-R93 report language order/set drift")

    report_fingerprints = {}
    comparison_evidence = []
    for row, language in zip(rows, LANGUAGES):
        if not isinstance(row, dict) or set(row) != LANGUAGE_KEYS:
            raise ValueError(f"post-R93 {language} language schema drift")
        if (
            row["language"] != language
            or row["input_stable"] is not True
            or row["gate"] is not False
        ):
            raise ValueError(f"post-R93 {language} language identity drift")
        report_fingerprints[language] = row["input_fingerprint"]
        comparison_evidence.append(
            _validate_comparison(row["comparison"], language=language)
        )
    _validate_fingerprints(report_fingerprints)

    first = comparison_evidence[0]
    for evidence in comparison_evidence[1:]:
        if evidence != first:
            raise ValueError("post-R93 JA/ZH/KO residual boundary/report mismatch")

    if current_fingerprints is not None:
        _validate_fingerprints(current_fingerprints)
        if current_fingerprints != report_fingerprints:
            raise ValueError("post-R93 deployed app input fingerprint changed")

    extracted = {
        "residual_entries_sha256": stable_sha256(first["residual_entries"]),
        "official_wrong_entries_sha256": stable_sha256(first["official_entries"]),
        "exact_wrong_entries_sha256": stable_sha256(first["exact_entries"]),
        "source_statistics_sha256": stable_sha256(first["statistics"]),
        "combined_statistics": first["statistics"]["combined"],
        "app_input_fingerprints": report_fingerprints,
        "app_input_fingerprints_sha256": stable_sha256(report_fingerprints),
        "checkpoint_context_sha256": stable_sha256(
            report["checkpoint_context"]
        ),
        "scope_sha256": stable_sha256(report["scope"]),
        "reviewed_reference_sha256": stable_sha256(
            report["reviewed_reference"]
        ),
        "inputs_stable_sha256": stable_sha256(report["inputs_stable"]),
    }
    if manifest is not None:
        validate_manifest(
            manifest, gate_id=gate_id,
            report_relative_path=report_relative_path,
        )
        if extracted != manifest["sealed"]:
            raise ValueError("post-R93 report no longer matches sealed evidence")
    return {
        "gate_id": gate_id,
        "languages": list(LANGUAGES),
        "raw_cases": report["raw_case_count"],
        "resolved_cases": report["case_count"],
        "surfaces": report["surface_count"],
        "residual_surfaces_per_language": len(EXPECTED_RESIDUALS),
        "regression_cases": 0,
        "changed_wrong_surfaces": 0,
        "trilingual_residual_mismatches": 0,
        "sealed": extracted,
        "gate": True,
    }


def build_manifest_from_report(
    report: dict, report_raw: bytes, *, current_fingerprints: dict,
    gate_id: str = GATE_ID,
    report_relative_path: Path = REPORT_RELATIVE_PATH,
) -> dict:
    # Validate semantics and live input identity before deriving any seal.
    result = validate_report(
        report, current_fingerprints=current_fingerprints,
        gate_id=gate_id, report_relative_path=report_relative_path,
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "gate_id": gate_id,
        "report": {
            "path": report_relative_path.as_posix(),
            "bytes": len(report_raw),
            "sha256": raw_sha256(report_raw),
        },
        "reference_projection": dict(FIXED_REFERENCE),
        "languages": list(LANGUAGES),
        "expected_counts": {
            "raw_cases": FIXED_REFERENCE["raw_cases"],
            "resolved_cases": FIXED_REFERENCE["resolved_cases"],
            "surfaces": FIXED_REFERENCE["surfaces"],
            "residual_surfaces_per_language": len(EXPECTED_RESIDUALS),
            "official_wrong_cases_per_language": 1,
            "exact_wrong_cases_per_language": 1,
            "regression_cases": 0,
            "changed_wrong_surfaces": 0,
            "trilingual_residual_mismatches": 0,
        },
        "residual_contract": [dict(row) for row in EXPECTED_RESIDUALS],
        "provenance_counts": dict(EXPECTED_PROVENANCE_COUNTS),
        "sealed": result["sealed"],
    }
    validate_manifest(
        manifest, gate_id=gate_id,
        report_relative_path=report_relative_path,
    )
    return manifest


def manifest_bytes(
    manifest: dict, *, gate_id: str = GATE_ID,
    report_relative_path: Path = REPORT_RELATIVE_PATH,
) -> bytes:
    validate_manifest(
        manifest, gate_id=gate_id,
        report_relative_path=report_relative_path,
    )
    return json.dumps(
        manifest, ensure_ascii=False, indent=2,
    ).encode("utf-8")


def load_manifest(
    path: Path = MANIFEST_PATH, *,
    expected_sha256: str = EXPECTED_MANIFEST_SHA256,
    gate_id: str = GATE_ID,
    report_relative_path: Path = REPORT_RELATIVE_PATH,
) -> tuple[dict, bytes]:
    raw = Path(path).read_bytes()
    observed = raw_sha256(raw)
    if not is_sha256(expected_sha256):
        raise ValueError(
            "post-R93 manifest is not sealed in gate code: "
            f"observed={observed}"
        )
    if observed != expected_sha256:
        raise ValueError(
            f"post-R93 manifest byte drift: {observed} != {expected_sha256}"
        )
    manifest = json.loads(raw.decode("utf-8"))
    validate_manifest(
        manifest, gate_id=gate_id,
        report_relative_path=report_relative_path,
    )
    return manifest, raw


def validate_report_bytes(
    report_raw: bytes, *, manifest: dict,
    current_fingerprints: dict,
    gate_id: str = GATE_ID,
    report_relative_path: Path = REPORT_RELATIVE_PATH,
) -> dict:
    validate_manifest(
        manifest, gate_id=gate_id,
        report_relative_path=report_relative_path,
    )
    identity = manifest["report"]
    if (
        len(report_raw) != identity["bytes"]
        or raw_sha256(report_raw) != identity["sha256"]
    ):
        raise ValueError("post-R93 raw report byte identity drift")
    report = json.loads(report_raw.decode("utf-8"))
    return validate_report(
        report, manifest=manifest,
        current_fingerprints=current_fingerprints,
        gate_id=gate_id, report_relative_path=report_relative_path,
    )


def validate_deployed(
    *, report_path: Path = REPORT_PATH, manifest_path: Path = MANIFEST_PATH,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
    gate_id: str = GATE_ID,
    report_relative_path: Path = REPORT_RELATIVE_PATH,
) -> dict:
    manifest, manifest_raw = load_manifest(
        manifest_path, expected_sha256=expected_manifest_sha256,
        gate_id=gate_id, report_relative_path=report_relative_path,
    )
    report_raw = Path(report_path).read_bytes()
    fingerprints_before = deployed_app_fingerprints()
    result = validate_report_bytes(
        report_raw,
        manifest=manifest,
        current_fingerprints=fingerprints_before,
        gate_id=gate_id, report_relative_path=report_relative_path,
    )
    if (
        Path(report_path).read_bytes() != report_raw
        or Path(manifest_path).read_bytes() != manifest_raw
        or deployed_app_fingerprints() != fingerprints_before
    ):
        raise ValueError("post-R93 evidence/input changed during gate validation")
    result.update({
        "report_sha256": manifest["report"]["sha256"],
        "manifest_sha256": raw_sha256(manifest_raw),
        "deployed_inputs_revalidated": True,
    })
    return result


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument(
        "--expected-manifest-sha256", default=EXPECTED_MANIFEST_SHA256,
    )
    args = parser.parse_args(argv)
    result = validate_deployed(
        report_path=args.report,
        manifest_path=args.manifest,
        expected_manifest_sha256=args.expected_manifest_sha256,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
