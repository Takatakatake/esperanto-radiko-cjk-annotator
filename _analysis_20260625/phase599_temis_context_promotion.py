# -*- coding: utf-8 -*-
"""Explicit, idempotent JA/ZH/KO promotion transaction for Phase 599.

The Phase 599 review and deployed-precondition gate intentionally remain
candidate-only.  This separate module consumes an explicit promotion ledger.
It removes only an already exact copy of the five managed rows in memory,
revalidates the normalized R73 payload, rebuilds the five rows from the sealed
candidate authority, stages all languages, and performs rollback-protected
replacement.  No Kanji path is ever a write destination.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

from atomic_json import atomic_binary_copy, atomic_json_dump
from gen_replacement import load_app_replacement_helper
import no_worsening_audit as audit
import phase598_parent_payload_delta_gate as phase598_parent
import phase598_technical_on_runtime_gate as phase598_runtime
import phase599_temis_context_policy as candidate_policy
import phase599_temis_context_runtime_gate as candidate_gate
import phase600_master_ruby_policy as later_policy
import preserve_r67_r68_ruby_overlays as historical_overlay


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LEDGER_PATH = HERE / "_phase599_temis_context_promotion.json"
LANGUAGES = candidate_policy.LANGUAGES
MANAGED_PLACEHOLDER_PREFIX = candidate_gate.PLACEHOLDER_PREFIX
NORMALIZED_GLOBAL_ROWS = 572_501
PROMOTED_GLOBAL_ROWS = 572_506
POST_PHASE600_GLOBAL_ROWS = later_policy.PROMOTED_GLOBAL_ROWS
EXPECTED_LEDGER_SHA256 = (
    "0A24AECF19564B49452E355A14E43ECE1183B2A7023B7F22E4C65DDE7DFB5E74"
)
EXPECTED_SECTION_SHA256 = {
    "authorization": (
        "CE0DBD630489087D69118ADA2A16703A5F60947BABB4DA9B1BCC8CB86181FA0E"
    ),
    "candidate_authority": (
        "13C8C04135420FCBB1607FD2A19F418A8927F660D14275E473A304E3D12B1CE1"
    ),
    "required_preconditions": (
        "5590D6B2F3CA18BBAF1D1174E32BDE0F1968DED0A732FDBCE5FA6CB7A0FF5174"
    ),
    "transaction": (
        "450634590269DC63878BA52A109AFD2E1B7175BA78A36BF30B8FEE97F3F1FE0C"
    ),
    "row_manifests": (
        "85BB06768253721C0553A2BBC2D0C541FC671A21C7674D7B1FFE7B6C2F4F19A6"
    ),
    "expected_counts": (
        "2AD127655EFDC878E83B505F064E963F18CC04A864E9540B635657152C4FDA81"
    ),
}
EXPECTED_POLICY = (
    "Promote only the five sealed Phase 599 long-phrase Ruby rows. Normalize "
    "any already-promoted exact rows away, revalidate the R67/R68 and R73 "
    "parent layers plus the candidate-only Temis precondition in memory, "
    "stage JA/ZH/KO together, and publish only after candidate runtime, guard, "
    "width, and Kanji-nonintervention gates pass."
)
EXPECTED_COUNTS = {
    "unique_phrases": 5,
    "corpus_instances": 6,
    "languages": 3,
    "managed_rows_total": 15,
    "negative_cases": 6,
    "kanji_files_written": 0,
}
CORPUS_CONTEXTS = (
    (
        "Temis tamen pri aparatoj",
        "Temis tamen pri aparatoj grandaj, malkomfortaj.",
        1,
    ),
    (
        "Temis pri tre noveca",
        "Temis pri tre noveca leĝo, ĝi rolis kiel specifa konstitucio "
        "reguliganta ĉiujn sferojn de la socia, politika kaj ekonomia vivo.",
        1,
    ),
    (
        "Temis pri la volo",
        "Temis pri la volo de Frederiko Chopin mem.",
        1,
    ),
    (
        "Temis pri la distrikto",
        "Temis pri la distrikto Sūzin, kie iam amase loĝis homoj de la "
        "diskriminaciata sociklaso Burakumin, pri kiu grava dokumento estas "
        "prezentata sur la paĝoj 12-14 de tiu ĉi numero.",
        1,
    ),
    (
        "Temis pri malnovaj",
        "Temis pri malnovaj vestaĵoj, kiujn Milovano kaj lia familio jam ne "
        "povis uzi, sed por malriĉaj familianoj eble ankoraŭ taŭgas.",
        2,
    ),
)
EXPECTED_CORPUS_CONTEXTS_SHA256 = (
    "43FCD26C408BADF9C26D91BB54E4E9F9092C1BD277C989B4C4A370E0B61CB4A0"
)


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def validate_corpus_context_inventory() -> dict:
    phrases = [phrase for phrase, _surface, _count in CORPUS_CONTEXTS]
    instance_counts = {
        phrase: count for phrase, _surface, count in CORPUS_CONTEXTS
    }
    if (
        compact_sha256(CORPUS_CONTEXTS)
        != EXPECTED_CORPUS_CONTEXTS_SHA256
        or phrases != list(candidate_policy.positive_phrases())
        or instance_counts != candidate_policy.EXPECTED_POSITIVE_INSTANCES
        or len({surface for _phrase, surface, _count in CORPUS_CONTEXTS})
        != len(CORPUS_CONTEXTS)
        or any(
            not surface.startswith(phrase + " ")
            for phrase, surface, _count in CORPUS_CONTEXTS
        )
        or sum(instance_counts.values()) != EXPECTED_COUNTS["corpus_instances"]
    ):
        raise ValueError("Phase 599 sealed corpus-context inventory drift")
    return {
        "contexts_sha256": EXPECTED_CORPUS_CONTEXTS_SHA256,
        "unique_contexts": len(CORPUS_CONTEXTS),
        "corpus_instances": sum(instance_counts.values()),
        "gate": True,
    }


def validate_ledger_payload(payload: dict) -> dict:
    expected_keys = {
        "schema_version", "phase", "status", "policy", "authorization",
        "candidate_authority", "required_preconditions", "transaction",
        "row_manifests", "expected_counts",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != expected_keys
        or payload.get("schema_version") != 1
        or payload.get("phase") != candidate_policy.PHASE
        or payload.get("status") != "promotion_authorized"
        or payload.get("policy") != EXPECTED_POLICY
        or payload.get("expected_counts") != EXPECTED_COUNTS
        or any(
            compact_sha256(payload.get(section)) != expected_sha
            for section, expected_sha in EXPECTED_SECTION_SHA256.items()
        )
    ):
        raise ValueError("Phase 599 promotion ledger identity drift")
    authority = payload["authorization"]
    if authority != {
        "kind": "explicit_user_instruction",
        "date": "2026-07-26",
        "from_status": "candidate_only",
        "to_status": "deployed_ruby_overlay",
        "scope": "five_exact_temis_context_rows_in_JA_ZH_KO",
    }:
        raise ValueError("Phase 599 explicit promotion authority drift")
    candidate = payload["candidate_authority"]
    review_identity = candidate_policy.review_identity()
    if (
        candidate["path"]
        != "_analysis_20260625/_phase599_temis_context_review.json"
        or candidate["review_sha256"]
        != candidate_policy.EXPECTED_REVIEW_SHA256
        or candidate["decisions_sha256"]
        != candidate_policy.EXPECTED_DECISIONS_SHA256
        or candidate["base_app_commit"] != review_identity["base_app_commit"]
        or candidate["kyoto_corpus_commit"]
        != review_identity["kyoto_corpus_commit"]
    ):
        raise ValueError("Phase 599 candidate-to-promotion binding drift")
    required = payload["required_preconditions"]
    if required != {
        "normalized_global_rows_per_language": NORMALIZED_GLOBAL_ROWS,
        "r67_r68_overlay_audit": True,
        "r73_parent_payload_delta_gate": True,
        "candidate_temis_precondition_gate": True,
        "candidate_runtime_gate": True,
        "strict_added_ruby_width_below_2x": True,
        "negative_nonintervention": True,
        "trilingual_boundary_rb_identity": True,
    }:
        raise ValueError("Phase 599 promotion precondition drift")
    transaction = payload["transaction"]
    if transaction != {
        "languages": list(LANGUAGES),
        "track": "Ruby",
        "managed_bucket": "replacements_final_list",
        "remove_existing_managed_rows_before_add": True,
        "rows_added_per_language": 5,
        "post_promotion_global_rows_per_language": PROMOTED_GLOBAL_ROWS,
        "stage_all_before_replace": True,
        "rollback_on_replace_or_postcondition_failure": True,
        "idempotent_noop_when_exactly_promoted": True,
        "kanji_paths_written": [],
        "generator_hook": (
            "after_r67_r68_audit_and_r73_parent_delta_gate"
        ),
    }:
        raise ValueError("Phase 599 promotion transaction drift")
    manifests = payload["row_manifests"]
    if (
        not isinstance(manifests, dict)
        or set(manifests) != set(LANGUAGES)
        or any(
            not isinstance(manifests[language], dict)
            or set(manifests[language]) != {
                "rows", "rows_sha256", "sources_sha256",
                "rendered_sha256", "placeholders_sha256",
            }
            or manifests[language]["rows"] != 5
            for language in LANGUAGES
        )
    ):
        raise ValueError("Phase 599 promotion row-manifest shape drift")
    return payload


def load_promotion_ledger(path: Path = LEDGER_PATH) -> dict:
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != EXPECTED_LEDGER_SHA256:
        raise ValueError("Phase 599 promotion ledger raw identity drift")
    return validate_ledger_payload(json.loads(raw.decode("utf-8")))


def promotion_identity() -> dict:
    ledger = load_promotion_ledger()
    return {
        "phase": candidate_policy.PHASE,
        "status": ledger["status"],
        "ledger_sha256": EXPECTED_LEDGER_SHA256,
        "candidate_review_sha256": (
            ledger["candidate_authority"]["review_sha256"]
        ),
        "authorization": dict(ledger["authorization"]),
        "managed_rows_total": EXPECTED_COUNTS["managed_rows_total"],
        "normalized_global_rows_per_language": NORMALIZED_GLOBAL_ROWS,
        "post_promotion_global_rows_per_language": PROMOTED_GLOBAL_ROWS,
        "kanji_paths_written": [],
    }


def row_manifest(rows: list) -> dict:
    return {
        "rows": len(rows),
        "rows_sha256": compact_sha256(rows),
        "sources_sha256": compact_sha256([row[0] for row in rows]),
        "rendered_sha256": compact_sha256([row[1] for row in rows]),
        "placeholders_sha256": compact_sha256([row[2] for row in rows]),
    }


def expected_rows(language: str) -> list[list[str]]:
    ledger = load_promotion_ledger()
    app = candidate_gate.app_dir(language)
    helper = load_app_replacement_helper(app)
    widths = json.loads(
        (app / "app_data" / "char_widths.json").read_text(encoding="utf-8")
    )
    rows = candidate_gate.build_candidate_rows(
        language, helper.output_format, widths,
    )
    actual = row_manifest(rows)
    expected = ledger["row_manifests"][language]
    if actual != expected:
        raise ValueError(
            f"Phase 599 {language} promoted row manifest drift: "
            f"{actual!r} != {expected!r}"
        )
    return rows


def validate_trilingual_row_manifests() -> dict:
    rows_by_language = {
        language: expected_rows(language) for language in LANGUAGES
    }
    source_sequences = {
        tuple(row[0] for row in rows_by_language[language])
        for language in LANGUAGES
    }
    if len(source_sequences) != 1:
        raise ValueError("Phase 599 promoted source order differs by language")
    placeholders = [
        row[2]
        for language in LANGUAGES
        for row in rows_by_language[language]
    ]
    if len(placeholders) != len(set(placeholders)):
        raise ValueError("Phase 599 promoted placeholders are not trilingual")
    return {
        "rows": rows_by_language,
        "row_manifests": {
            language: row_manifest(rows_by_language[language])
            for language in LANGUAGES
        },
        "trilingual_source_order_identical": True,
        "trilingual_placeholders_unique": True,
        "gate": True,
    }


def _rule_keys(payload: dict) -> tuple[str, str, str]:
    return candidate_gate._rule_keys(payload)


def _managed_row(row, target_sources: set[str]) -> bool:
    return (
        isinstance(row, (list, tuple))
        and len(row) >= 3
        and (
            row[0] in target_sources
            or (
                isinstance(row[2], str)
                and MANAGED_PLACEHOLDER_PREFIX in row[2]
            )
        )
    )


def normalize_and_build_payload(
    payload: dict, language: str, rows: list[list[str]], *,
    expected_normalized_rows: int = NORMALIZED_GLOBAL_ROWS,
) -> tuple[dict, dict, dict]:
    """Normalize Phase 599 while preserving an exact optional later layer."""
    local_key, global_key, two_char_key = _rule_keys(payload)
    later_rows = later_policy.validate_optional_layer(payload, language)
    without_later = dict(payload)
    without_later[global_key] = [
        row for row in payload[global_key]
        if not later_policy.is_managed_row(row)
    ]
    target_sources = {row[0] for row in rows}
    if len(target_sources) != len(rows):
        raise ValueError(f"Phase 599 {language} duplicate managed sources")
    for key in (local_key, two_char_key):
        leaked = [
            row
            for row in without_later[key]
            if _managed_row(row, target_sources)
        ]
        if leaked:
            raise ValueError(
                f"Phase 599 {language} managed row leaked into {key!r}"
            )
    global_rows = without_later[global_key]
    managed = [
        row for row in global_rows if _managed_row(row, target_sources)
    ]
    expected_counter = Counter(
        json.dumps(row, ensure_ascii=False, separators=(",", ":"))
        for row in rows
    )
    managed_counter = Counter(
        json.dumps(list(row), ensure_ascii=False, separators=(",", ":"))
        for row in managed
    )
    if managed and managed_counter != expected_counter:
        raise ValueError(
            f"Phase 599 {language} existing managed rows are not exact"
        )
    normalized_rows = [
        row for row in global_rows if not _managed_row(row, target_sources)
    ]
    if len(normalized_rows) != expected_normalized_rows:
        raise ValueError(
            f"Phase 599 {language} normalized global row count drift: "
            f"{len(normalized_rows)} != {expected_normalized_rows}"
        )
    normalized = dict(without_later)
    normalized[global_key] = normalized_rows
    candidate_gate.validate_deployed_candidate_absent(normalized)
    phase599_candidate = dict(normalized)
    phase599_candidate[global_key] = [*rows, *normalized_rows]
    delta = candidate_gate.validate_candidate_payload_delta(
        normalized, phase599_candidate, rows, language,
    )
    expected_phase599_rows = expected_normalized_rows + len(rows)
    if len(phase599_candidate[global_key]) != expected_phase599_rows:
        raise ValueError(
            f"Phase 599 {language} promoted global row count drift"
        )
    candidate = dict(phase599_candidate)
    candidate[global_key] = [*rows, *later_rows, *normalized_rows]
    expected_deployed_rows = expected_phase599_rows + len(later_rows)
    if len(candidate[global_key]) != expected_deployed_rows:
        raise ValueError(
            f"Phase 599 {language} deployed global row count drift"
        )
    if later_rows:
        later_policy.validate_optional_layer(
            candidate, language, require_present=True,
        )
    canonical = (
        len(managed) == len(rows)
        and payload[global_key] == candidate[global_key]
    )
    state = {
        "existing_managed_rows": len(managed),
        "later_phase600_rows_preserved": len(later_rows),
        "rows_removed_during_normalization": len(managed),
        "rows_added_to_candidate": len(rows),
        "normalized_global_rows": len(normalized_rows),
        "phase599_global_rows": len(phase599_candidate[global_key]),
        "deployed_global_rows": len(candidate[global_key]),
        "state": (
            "promoted_canonical"
            if canonical
            else (
                "unpromoted"
                if not managed
                else "promoted_exact_noncanonical"
            )
        ),
        "needs_write": not canonical,
    }
    return normalized, candidate, {**state, **delta}


def _r67_r68_language_summary(language: str, payload: dict) -> dict:
    _key, rows = historical_overlay.global_bucket(payload)
    if len(rows) != NORMALIZED_GLOBAL_ROWS:
        raise ValueError(
            f"Phase 599 {language} R67/R68 normalized count drift"
        )
    overlays = {
        prefix: historical_overlay.overlay_rows(rows, prefix)
        for prefix in historical_overlay.OVERLAY_PREFIXES
    }
    exact = [
        row for row in rows
        if (
            isinstance(row, list)
            and len(row) >= 2
            and row[0] == historical_overlay.EXACT_OVERRIDE_SOURCE
        )
    ]
    if (
        len(exact) != 1
        or exact[0][1] != historical_overlay.EXACT_OVERRIDE_RENDERED[language]
    ):
        raise ValueError(
            f"Phase 599 {language} R67/R68 exact override drift"
        )
    return {
        "overlays": overlays,
        "global_rows": len(rows),
        "exact_override": exact[0][1],
    }


def _render_pair(
    language: str, normalized: dict, candidate: dict, *, batch_size: int,
) -> tuple[dict, dict, dict, dict, dict]:
    app = candidate_gate.app_dir(language)
    runtime = audit.runtime_module(
        app, f"phase599_promotion_runtime_{language}",
    )
    overlay = audit.overlay_module(
        app, f"phase599_promotion_overlay_{language}",
    )
    corrections = json.loads(
        (app / "app_data" / "user_corrections.json").read_text(
            encoding="utf-8"
        )
    )
    reviewed_surfaces = list(candidate_policy.combined_surfaces())
    context_surfaces = [surface for _phrase, surface, _count in CORPUS_CONTEXTS]
    surfaces = [*reviewed_surfaces, *context_surfaces]
    all_precondition = audit.render_signatures(
        runtime, app, normalized, surfaces, batch_size,
        overlay=overlay, corrections=corrections,
        include_annotations=True,
    )
    all_promoted = audit.render_signatures(
        runtime, app, candidate, surfaces, batch_size,
        overlay=overlay, corrections=corrections,
        include_annotations=True,
    )
    helper = load_app_replacement_helper(app)
    widths = json.loads(
        (app / "app_data" / "char_widths.json").read_text(encoding="utf-8")
    )
    width = candidate_gate.validate_added_annotation_widths(
        language, helper.output_format, widths,
    )
    return (
        {
            surface: all_precondition[surface]
            for surface in reviewed_surfaces
        },
        {
            surface: all_promoted[surface]
            for surface in reviewed_surfaces
        },
        {
            surface: all_precondition[surface]
            for surface in context_surfaces
        },
        {
            surface: all_promoted[surface]
            for surface in context_surfaces
        },
        width,
    )


def validate_corpus_context_rendered_results(
    promoted_results: dict, precondition_results: dict,
) -> dict:
    """Prove the five reviewed rows inside all six corpus-instance contexts."""
    inventory = validate_corpus_context_inventory()
    expected_surfaces = {
        surface for _phrase, surface, _count in CORPUS_CONTEXTS
    }
    if (
        set(promoted_results) != set(LANGUAGES)
        or set(precondition_results) != set(LANGUAGES)
    ):
        raise ValueError("Phase 599 corpus-context language set drift")
    preserved_cases = 0
    for language in LANGUAGES:
        if (
            set(promoted_results[language]) != expected_surfaces
            or set(precondition_results[language]) != expected_surfaces
        ):
            raise ValueError(
                f"Phase 599 {language} corpus-context surface set drift"
            )
        for phrase, surface, _count in CORPUS_CONTEXTS:
            if not surface.startswith(phrase + " "):
                raise ValueError(
                    f"Phase 599 corpus context no longer extends {phrase!r}"
                )
            before = precondition_results[language][surface]
            after = promoted_results[language][surface]
            before_signature = before["signature"]
            after_signature = after["signature"]
            if (
                before_signature[0] != surface
                or after_signature[0] != surface
                or after_signature[1][:2]
                != (("Tem", True), ("is", True))
                or [item["rb"] for item in after["annotations"][:2]]
                != ["Tem", "is"]
            ):
                raise ValueError(
                    f"Phase 599 {language} corpus-context activation drift: "
                    f"{surface!r}"
                )
            collapsed = audit.signature_from_typed_parts([
                ("Temis", False), *list(after_signature[1][2:]),
            ])
            if (
                collapsed != before_signature
                or after["annotations"][2:] != before["annotations"]
            ):
                raise ValueError(
                    f"Phase 599 {language} corpus-context suffix drift: "
                    f"{surface!r}"
                )
            preserved_cases += 1
    for surface in expected_surfaces:
        signatures = [
            promoted_results[language][surface]["signature"]
            for language in LANGUAGES
        ]
        rb_sequences = [
            [
                annotation["rb"]
                for annotation in
                promoted_results[language][surface]["annotations"]
            ]
            for language in LANGUAGES
        ]
        if (
            any(signature != signatures[0] for signature in signatures[1:])
            or any(sequence != rb_sequences[0] for sequence in rb_sequences[1:])
        ):
            raise ValueError(
                f"Phase 599 corpus-context trilingual drift: {surface!r}"
            )
    return {
        **inventory,
        "language_cases_activated": preserved_cases,
        "suffix_boundary_annotation_cases_preserved": preserved_cases,
        "trilingual_boundaries_identical": True,
        "trilingual_rb_sequences_identical": True,
    }


def _validate_parent_delta(language: str, normalized: dict) -> dict:
    parent_payload = historical_overlay.load_payload(
        language, git_ref=historical_overlay.PINNED_PARENT_COMMIT,
    )
    try:
        report = phase598_parent.validate_language_delta(
            language,
            parent_payload,
            normalized,
            set(phase598_runtime.positive_surface_list()),
        )
    finally:
        del parent_payload
        gc.collect()
    return report


def _stage_path(language: str) -> Path:
    destination = candidate_gate.deployed_payload_path(language)
    return destination.with_name(destination.name + ".phase599_stage")


def _rollback_path(destination: Path) -> Path:
    return destination.with_name(destination.name + ".phase599_rollback")


def _cleanup_paths(paths) -> None:
    for path in paths:
        path = Path(path)
        for suffix in (".tmp_atomic_write", ".tmp_atomic_copy"):
            temporary = path.with_name(path.name + suffix)
            if temporary.exists():
                temporary.unlink()
        if path.exists():
            path.unlink()


def prepare_promotion(
    *, batch_size: int = 20, write_stages: bool = False,
) -> dict:
    """Build and fully validate the normalized/candidate pair for all apps."""
    candidate_gate._validate_batch_size(batch_size)
    identity_before = promotion_identity()
    candidate_review_before = candidate_policy.review_identity()
    row_closure = validate_trilingual_row_manifests()
    rows_by_language = row_closure["rows"]
    payload_hashes_before = {
        language: candidate_gate.file_sha256(
            candidate_gate.deployed_payload_path(language)
        )
        for language in LANGUAGES
    }
    runtime_before = {
        language: candidate_gate.runtime_input_fingerprint(language)
        for language in LANGUAGES
    }
    kanji_before = candidate_gate.kanji_track_fingerprint()
    stage_paths = {language: _stage_path(language) for language in LANGUAGES}
    if write_stages:
        stale = [
            str(path)
            for language, path in stage_paths.items()
            if (
                path.exists()
                or path.with_name(path.name + ".tmp_atomic_write").exists()
                or _rollback_path(
                    candidate_gate.deployed_payload_path(language)
                ).exists()
            )
        ]
        if stale:
            raise ValueError(
                f"Phase 599 stale promotion transaction files: {stale!r}"
            )
    precondition_results = {}
    promoted_results = {}
    context_precondition_results = {}
    context_promoted_results = {}
    states = {}
    widths = {}
    parent_deltas = {}
    overlay_matrix = {}
    overlay_rows = {}
    staged_sha256 = {}
    try:
        phase598_parent._parent_identity()
        for language in LANGUAGES:
            payload = json.loads(
                candidate_gate.deployed_payload_path(language).read_text(
                    encoding="utf-8"
                )
            )
            normalized, candidate, state = normalize_and_build_payload(
                payload, language, rows_by_language[language],
            )
            states[language] = state
            overlay_summary = _r67_r68_language_summary(
                language, normalized,
            )
            overlay_matrix[language] = overlay_summary["overlays"]
            overlay_rows[language] = overlay_summary["global_rows"]
            parent_deltas[language] = _validate_parent_delta(
                language, normalized,
            )
            (
                precondition_results[language],
                promoted_results[language],
                context_precondition_results[language],
                context_promoted_results[language],
                widths[language],
            ) = _render_pair(
                language, normalized, candidate, batch_size=batch_size,
            )
            if write_stages:
                atomic_json_dump(stage_paths[language], candidate)
                staged = json.loads(
                    stage_paths[language].read_text(encoding="utf-8")
                )
                (
                    _staged_normalized, staged_candidate, staged_state,
                ) = normalize_and_build_payload(
                    staged, language, rows_by_language[language],
                )
                if (
                    staged_state["state"] != "promoted_canonical"
                    or staged_candidate != staged
                ):
                    raise ValueError(
                        f"Phase 599 {language} staged payload drift"
                    )
                staged_sha256[language] = candidate_gate.file_sha256(
                    stage_paths[language]
                )
                del staged, _staged_normalized, staged_candidate
            del payload, normalized, candidate
            gc.collect()
        later_counts = {
            language: states[language]["later_phase600_rows_preserved"]
            for language in LANGUAGES
        }
        if (
            len(set(later_counts.values())) != 1
            or next(iter(later_counts.values()))
            not in (0, later_policy.MANAGED_ROWS)
        ):
            raise ValueError(
                f"Phase 599 mixed Phase-600 deployment state: "
                f"{later_counts!r}"
            )
        overlay_report = historical_overlay.validate_overlay_matrix(
            overlay_matrix
        )
        precondition_report = (
            candidate_gate.validate_precondition_rendered_results(
                precondition_results
            )
        )
        promoted_report = candidate_gate.validate_candidate_rendered_results(
            promoted_results, precondition_results,
        )
        context_report = validate_corpus_context_rendered_results(
            context_promoted_results, context_precondition_results,
        )
        source_removed = {
            report["source_removed_sha256"]
            for report in parent_deltas.values()
        }
        source_added = {
            report["source_added_sha256"]
            for report in parent_deltas.values()
        }
        if (
            len(source_removed) != 1
            or len(source_added) != 1
            or any(not report["gate"] for report in parent_deltas.values())
        ):
            raise ValueError(
                "Phase 599 normalized trilingual R73 parent delta drift"
            )
        maxima = {
            language: widths[language]["max_effective_width_ratio"]
            for language in LANGUAGES
        }
        if any(value >= 2.0 for value in maxima.values()):
            raise ValueError(
                f"Phase 599 promotion width drift: {maxima!r}"
            )
        payload_hashes_after = {
            language: candidate_gate.file_sha256(
                candidate_gate.deployed_payload_path(language)
            )
            for language in LANGUAGES
        }
        runtime_after = {
            language: candidate_gate.runtime_input_fingerprint(language)
            for language in LANGUAGES
        }
        kanji_after = candidate_gate.kanji_track_fingerprint()
        if (
            payload_hashes_after != payload_hashes_before
            or runtime_after != runtime_before
            or kanji_after != kanji_before
            or promotion_identity() != identity_before
            or candidate_policy.review_identity() != candidate_review_before
        ):
            raise ValueError(
                "Phase 599 promotion input changed during preparation"
            )
        state_names = {
            language: states[language]["state"] for language in LANGUAGES
        }
        all_canonical = all(
            state == "promoted_canonical"
            for state in state_names.values()
        )
        report = {
            "phase": candidate_policy.PHASE,
            "mode": "promotion_prepare",
            "promotion": identity_before,
            "states": states,
            "ready_to_promote": True,
            "already_promoted": all_canonical,
            "writes_required": 0 if all_canonical else len(LANGUAGES),
            "candidate_review_remains_candidate_only": (
                candidate_review_before["status"] == "candidate_only"
            ),
            "later_phase600": {
                "rows_preserved_per_language": later_counts,
                "deployed_global_rows_per_language": {
                    language: states[language]["deployed_global_rows"]
                    for language in LANGUAGES
                },
                "trilingual_presence_identical": True,
                "gate": True,
            },
            "normalized_r67_r68": {
                "global_rows": overlay_rows,
                "overlay_report": overlay_report,
                "gate": True,
            },
            "normalized_r73_parent_delta": {
                "languages": parent_deltas,
                "trilingual_source_delta_identical": True,
                "gate": True,
            },
            "normalized_candidate_precondition": precondition_report,
            "promoted_candidate_runtime": promoted_report,
            "promoted_corpus_context_runtime": context_report,
            "width": {
                "languages": widths,
                "max_effective_width_ratio": maxima,
                "effective_ruby_width_strictly_below_2x": True,
                "gate": True,
            },
            "row_manifests": row_closure["row_manifests"],
            "deployed_payload_sha256_before": payload_hashes_before,
            "stage_payload_sha256": staged_sha256,
            "runtime_inputs_stable": True,
            "kanji_track_files_fingerprinted": len(kanji_before),
            "kanji_track_files_changed": 0,
            "kanji_nonintervention": True,
            "generator_hook": (
                "after_r67_r68_audit_and_r73_parent_delta_gate"
            ),
            "gate": True,
        }
        return {
            "report": report,
            "stage_paths": stage_paths,
            "payload_hashes_before": payload_hashes_before,
            "kanji_before": kanji_before,
        }
    except Exception:
        if write_stages:
            _cleanup_paths(stage_paths.values())
        raise


def plan_promotion(*, batch_size: int = 20) -> dict:
    return prepare_promotion(
        batch_size=batch_size, write_stages=False,
    )["report"]


def audit_deployed_promotion(*, batch_size: int = 20) -> dict:
    prepared = prepare_promotion(
        batch_size=batch_size, write_stages=False,
    )
    report = prepared["report"]
    if (
        not report["already_promoted"]
        or report["writes_required"] != 0
        or any(
            state["state"] != "promoted_canonical"
            for state in report["states"].values()
        )
    ):
        raise ValueError("Phase 599 deployed promotion is incomplete")
    return {
        **report,
        "mode": "deployed_promotion_audit",
        "managed_rows_per_language": {
            language: report["states"][language]["existing_managed_rows"]
            for language in LANGUAGES
        },
        "post_promotion_global_rows_per_language": PROMOTED_GLOBAL_ROWS,
        "deployed_global_rows_per_language": {
            language: report["states"][language]["deployed_global_rows"]
            for language in LANGUAGES
        },
        "phase600_rows_preserved_per_language": {
            language: report["states"][language][
                "later_phase600_rows_preserved"
            ]
            for language in LANGUAGES
        },
        "promotion_audit_gate": True,
    }


def transactional_replace(
    staged: dict[str, Path],
    destinations: dict[str, Path],
    postcondition,
    *,
    replace=os.replace,
) -> dict:
    """Replace all three staged files with rollback on any later failure."""
    if set(staged) != set(LANGUAGES) or set(destinations) != set(LANGUAGES):
        raise ValueError("Phase 599 transaction language closure drift")
    rollbacks = {
        language: _rollback_path(destinations[language])
        for language in LANGUAGES
    }
    stale = [
        str(path)
        for path in rollbacks.values()
        if path.exists()
    ]
    if stale:
        raise ValueError(
            f"Phase 599 stale rollback files: {stale!r}"
        )
    for language in LANGUAGES:
        if not staged[language].is_file():
            raise ValueError(
                f"Phase 599 missing staged payload: {staged[language]}"
            )
        if not destinations[language].is_file():
            raise ValueError(
                f"Phase 599 missing deployed payload: "
                f"{destinations[language]}"
            )
    replaced = []
    try:
        for language in LANGUAGES:
            atomic_binary_copy(
                destinations[language], rollbacks[language],
            )
        for language in LANGUAGES:
            replace(staged[language], destinations[language])
            replaced.append(language)
        post_report = postcondition()
    except Exception as original:
        rollback_errors = []
        for language in reversed(LANGUAGES):
            rollback = rollbacks[language]
            destination = destinations[language]
            try:
                if language in replaced and rollback.exists():
                    os.replace(rollback, destination)
                elif rollback.exists():
                    rollback.unlink()
            except Exception as error:
                rollback_errors.append(
                    (language, str(destination), repr(error))
                )
        _cleanup_paths(staged.values())
        if rollback_errors:
            recovery_copies = {
                language: str(path)
                for language, path in rollbacks.items()
                if path.exists()
            }
            raise RuntimeError(
                "Phase 599 transaction failed and rollback was incomplete: "
                f"{rollback_errors!r}; recovery copies preserved: "
                f"{recovery_copies!r}"
            ) from original
        _cleanup_paths(rollbacks.values())
        raise
    _cleanup_paths(staged.values())
    _cleanup_paths(rollbacks.values())
    return {
        "languages_replaced": list(LANGUAGES),
        "rollback_files_remaining": 0,
        "postcondition": post_report,
        "transaction_gate": True,
    }


def _lock_path() -> Path:
    token = hashlib.sha256(str(ROOT).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"phase599_promotion_{token}.lock"


class PromotionLock:
    def __init__(self, path: Path | None = None):
        self.path = Path(path or _lock_path())
        self.descriptor = None

    def __enter__(self):
        try:
            self.descriptor = os.open(
                self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError as error:
            raise ValueError(
                f"Phase 599 promotion lock already exists: {self.path}"
            ) from error
        os.write(
            self.descriptor,
            f"pid={os.getpid()}\nroot={ROOT}\n".encode("utf-8"),
        )
        os.fsync(self.descriptor)
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self.descriptor is not None:
            os.close(self.descriptor)
            self.descriptor = None
        if self.path.exists():
            self.path.unlink()
        return False


def apply_promotion(
    *, explicit_promotion: bool, batch_size: int = 20,
    replace=os.replace,
) -> dict:
    if explicit_promotion is not True:
        raise ValueError(
            "Phase 599 apply requires explicit promotion authorization"
        )
    with PromotionLock():
        prepared = prepare_promotion(
            batch_size=batch_size, write_stages=True,
        )
        report = prepared["report"]
        stages = prepared["stage_paths"]
        if report["already_promoted"]:
            _cleanup_paths(stages.values())
            if (
                candidate_gate.kanji_track_fingerprint()
                != prepared["kanji_before"]
            ):
                raise ValueError(
                    "Phase 599 Kanji input changed during idempotent audit"
                )
            return {
                **report,
                "mode": "promotion_apply",
                "managed_rows_per_language": {
                    language: report["states"][language][
                        "existing_managed_rows"
                    ]
                    for language in LANGUAGES
                },
                "post_promotion_global_rows_per_language": (
                    PROMOTED_GLOBAL_ROWS
                ),
                "promotion_audit_gate": True,
                "payload_files_written": 0,
                "idempotent_noop": True,
                "transaction_gate": True,
            }
        destinations = {
            language: candidate_gate.deployed_payload_path(language)
            for language in LANGUAGES
        }

        def postcondition():
            audit_report = audit_deployed_promotion(batch_size=batch_size)
            if (
                candidate_gate.kanji_track_fingerprint()
                != prepared["kanji_before"]
            ):
                raise ValueError(
                    "Phase 599 promotion changed a Kanji-track file"
                )
            return audit_report

        transaction = transactional_replace(
            stages, destinations, postcondition, replace=replace,
        )
        deployed_after = {
            language: candidate_gate.file_sha256(destinations[language])
            for language in LANGUAGES
        }
        if deployed_after == prepared["payload_hashes_before"]:
            raise ValueError("Phase 599 promotion made no payload delta")
        return {
            **transaction["postcondition"],
            "mode": "promotion_apply",
            "payload_files_written": len(LANGUAGES),
            "idempotent_noop": False,
            "deployed_payload_sha256_before": (
                prepared["payload_hashes_before"]
            ),
            "deployed_payload_sha256_after": deployed_after,
            "languages_replaced": transaction["languages_replaced"],
            "rollback_files_remaining": (
                transaction["rollback_files_remaining"]
            ),
            "transaction_gate": True,
        }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser(
        "plan", help="validate and report without staging or writing",
    )
    plan_parser.add_argument("--batch-size", type=int, default=20)
    apply_parser = subparsers.add_parser(
        "apply", help="explicitly promote all three Ruby payloads",
    )
    apply_parser.add_argument(
        "--promote", action="store_true", required=True,
    )
    apply_parser.add_argument("--batch-size", type=int, default=20)
    audit_parser = subparsers.add_parser(
        "audit", help="require the exact promoted deployed state",
    )
    audit_parser.add_argument(
        "--deployed", action="store_true", required=True,
    )
    audit_parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args(argv)
    if args.command == "plan":
        report = plan_promotion(batch_size=args.batch_size)
    elif args.command == "apply":
        report = apply_promotion(
            explicit_promotion=args.promote, batch_size=args.batch_size,
        )
    else:
        report = audit_deployed_promotion(batch_size=args.batch_size)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Phase 599 promotion failed: {error}", file=sys.stderr)
        raise
