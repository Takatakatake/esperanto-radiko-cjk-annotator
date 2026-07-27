#!/usr/bin/env python3
"""Promote/audit the closed Phase-600 master-only Ruby repair.

This transaction runs after Phase 599.  It prepends 52 exact rows immediately
after the five Temis phrase rows, stages JA/ZH/KO together, proves the positive
and negative runtime closure, checks the effective Ruby width, and verifies
that no Kanji input changes.  The historical R68 rows remain present and
byte-identical behind the new rows.
"""
from __future__ import annotations

import argparse
import contextlib
import gc
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import sys

from atomic_json import atomic_binary_copy, atomic_json_dump
from gen_replacement import load_app_replacement_helper
import no_worsening_audit as audit
import phase599_temis_context_promotion as phase599_promotion
import phase599_temis_context_runtime_gate as phase599_runtime
import phase600_master_ruby_policy as policy


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LANGUAGES = policy.LANGUAGES
RUBY_RE = re.compile(
    r'<ruby>(?P<rb>.*?)<rt class="(?P<class>[A-Z_]+)">'
    r'(?P<rt>.*?)</rt></ruby>',
    re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>")
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def payload_path(language: str) -> Path:
    return phase599_runtime.deployed_payload_path(language)


def _managed_phase599_rows(rows: list) -> list:
    return [row for row in rows if policy.is_phase599_row(row)]


def normalize_and_build_payload(
    payload: dict,
    language: str,
    phase599_rows: list[list[str]],
) -> tuple[dict, dict, dict]:
    """Normalize only Phase 600, then insert its exact rows after Phase 599."""
    local_key, global_key, two_char_key = policy.rule_keys(payload)
    expected = policy.build_expected_rows(payload, language)
    managed = policy.validate_optional_layer(payload, language)
    normalized = dict(payload)
    normalized[global_key] = [
        row for row in payload[global_key] if not policy.is_managed_row(row)
    ]
    if (
        len(normalized[global_key]) != policy.NORMALIZED_GLOBAL_ROWS
        or normalized[global_key][:policy.PHASE599_ROWS] != phase599_rows
        or _managed_phase599_rows(normalized[global_key]) != phase599_rows
        or normalized[local_key] is not payload[local_key]
        or normalized[two_char_key] is not payload[two_char_key]
    ):
        raise ValueError(
            f"Phase 600 {language} normalized Phase-599 parent drift"
        )
    candidate = dict(normalized)
    candidate[global_key] = [
        *phase599_rows,
        *expected,
        *normalized[global_key][policy.PHASE599_ROWS:],
    ]
    if (
        len(candidate[global_key]) != policy.PROMOTED_GLOBAL_ROWS
        or candidate[local_key] is not normalized[local_key]
        or candidate[two_char_key] is not normalized[two_char_key]
    ):
        raise ValueError(f"Phase 600 {language} candidate delta escaped scope")
    policy.validate_optional_layer(
        candidate, language, require_present=True,
    )
    canonical = candidate == payload
    state = {
        "existing_managed_rows": len(managed),
        "normalized_global_rows": len(normalized[global_key]),
        "managed_rows_added": len(expected),
        "promoted_global_rows": len(candidate[global_key]),
        "state": "promoted_canonical" if canonical else "unpromoted",
        "needs_write": not canonical,
    }
    return normalized, candidate, state


def _expected_signature(surface: str):
    if surface in ("glu-glu-glu", "nor"):
        return audit.signature_from_typed_parts([(surface, True)])
    prefix, tail = surface.split("-", 1)
    lower_tail = tail.lower()
    stem = next(
        stem.split("-", 1)[1]
        for stem in policy.STEMS
        if lower_tail.startswith(stem.split("-", 1)[1])
    )
    body = tail[:len(stem)]
    ending = tail[len(stem):]
    return audit.signature_from_typed_parts([
        (prefix, True),
        ("-", False),
        (body, True),
        (ending, False),
    ])


def _render(
    language: str, payload: dict, surfaces: list[str], *, batch_size: int,
) -> dict:
    app = phase599_runtime.app_dir(language)
    runtime = audit.runtime_module(app, f"phase600_runtime_{language}")
    overlay = audit.overlay_module(app, f"phase600_overlay_{language}")
    corrections = json.loads(
        (app / "app_data" / "user_corrections.json").read_text(
            encoding="utf-8"
        )
    )
    # The automatic second pass is text-dependent.  Isolate the five forms
    # whose literal lowercase ``nor`` can teach a correction to another line;
    # all other closed forms are safe to render in one bulk call.
    sensitive = {"nor", "nor-", "kuku-nor", "lob-nor", "nor-X"}
    bulk = [surface for surface in surfaces if surface not in sensitive]
    groups = ([bulk] if bulk else []) + [
        [surface] for surface in surfaces if surface in sensitive
    ]
    results = {}
    with contextlib.redirect_stdout(io.StringIO()):
        for group in groups:
            rendered = audit.render_signatures(
                runtime,
                app,
                payload,
                group,
                max(1, min(batch_size, len(group))),
                overlay=overlay,
                corrections=corrections,
                include_annotations=True,
            )
            overlap = set(results) & set(rendered)
            if overlap:
                raise ValueError(
                    f"Phase 600 duplicate runtime group: {overlap!r}"
                )
            results.update(rendered)
    if set(results) != set(surfaces):
        raise ValueError("Phase 600 runtime surface closure drift")
    return results


def _validate_language_runtime(
    language: str, before: dict, after: dict,
) -> dict:
    positives = list(policy.positive_surfaces())
    negatives = list(policy.negative_surfaces())
    for surface in positives:
        expected = _expected_signature(surface)
        if after[surface]["signature"] != expected:
            raise ValueError(
                f"Phase 600 {language} positive boundary drift: {surface!r}"
            )
        if before[surface]["signature"] == after[surface]["signature"]:
            raise ValueError(
                f"Phase 600 {language} positive was already unchanged: "
                f"{surface!r}"
            )
        annotations = after[surface]["annotations"]
        if not annotations:
            raise ValueError(
                f"Phase 600 {language} positive lost annotations: {surface!r}"
            )
        if surface == "glu-glu-glu":
            if annotations != [{
                "rb": surface,
                "rt": policy.GLU_GLOSS[language],
            }]:
                raise ValueError(
                    f"Phase 600 {language} glu gloss drift"
                )
        else:
            if annotations[0] != {
                "rb": surface.split("-", 1)[0],
                "rt": policy.NOR_GLOSS[language],
            }:
                raise ValueError(
                    f"Phase 600 {language} nor gloss drift: {surface!r}"
                )
    for surface in negatives:
        if after[surface] != before[surface]:
            raise ValueError(
                f"Phase 600 {language} negative changed: {surface!r}"
            )
    return {
        "positive_surfaces": len(positives),
        "negative_surfaces": len(negatives),
        "positive_signatures_sha256": policy.compact_sha256([
            audit.signature_payload(after[surface]["signature"])
            for surface in positives
        ]),
        "positive_rb_sequences_sha256": policy.compact_sha256([
            [row["rb"] for row in after[surface]["annotations"]]
            for surface in positives
        ]),
        "negative_results_sha256": policy.compact_sha256([
            [surface, after[surface]] for surface in negatives
        ]),
        "gate": True,
    }


def _text_width(value: str, widths: dict) -> float:
    visible = html.unescape(TAG_RE.sub("", value))
    missing = [character for character in visible if character not in widths]
    if missing:
        raise ValueError(
            f"Phase 600 width table lacks characters: {missing!r}"
        )
    return sum(float(widths[character]) for character in visible)


def _validate_widths(
    language: str, rows: list[list[str]],
) -> dict:
    app = phase599_runtime.app_dir(language)
    widths = json.loads(
        (app / "app_data" / "char_widths.json").read_text(encoding="utf-8")
    )
    scales = phase599_runtime._css_scales(language)
    maximum = 0.0
    annotations = 0
    automatic_breaks = 0
    for row in rows:
        for match in RUBY_RE.finditer(row[1]):
            rb = html.unescape(TAG_RE.sub("", match.group("rb")))
            rt_markup = match.group("rt")
            if BR_RE.search(rt_markup):
                automatic_breaks += 1
            class_name = match.group("class").upper()
            if class_name not in scales:
                raise ValueError(
                    f"Phase 600 {language} unknown CSS class {class_name!r}"
                )
            rb_width = _text_width(rb, widths)
            if rb_width <= 0:
                raise ValueError("Phase 600 zero-width rb")
            ratio = (
                _text_width(rt_markup, widths)
                * scales[class_name]
                / rb_width
            )
            if ratio >= 2.0:
                raise ValueError(
                    f"Phase 600 {language} Ruby width >=2: "
                    f"{rb!r}/{ratio}"
                )
            maximum = max(maximum, ratio)
            annotations += 1
    if annotations < policy.MANAGED_ROWS:
        raise ValueError(f"Phase 600 {language} annotation closure drift")
    return {
        "managed_rows": len(rows),
        "annotations": annotations,
        "automatic_br_count": automatic_breaks,
        "max_effective_width_ratio": maximum,
        "effective_ruby_width_strictly_below_2x": True,
        "gate": True,
    }


def _validate_trilingual_runtime(
    results: dict[str, dict],
    language_reports: dict[str, dict],
) -> dict:
    positives = list(policy.positive_surfaces())
    signatures = {}
    rb_sequences = {}
    for language in LANGUAGES:
        signatures[language] = [
            audit.signature_payload(results[language][surface]["signature"])
            for surface in positives
        ]
        rb_sequences[language] = [
            [row["rb"] for row in results[language][surface]["annotations"]]
            for surface in positives
        ]
    if (
        len({policy.compact_sha256(value) for value in signatures.values()})
        != 1
        or len({
            policy.compact_sha256(value) for value in rb_sequences.values()
        }) != 1
        or any(not row["gate"] for row in language_reports.values())
    ):
        raise ValueError("Phase 600 JA/ZH/KO boundary/rb mismatch")
    return {
        "languages": list(LANGUAGES),
        "positive_surfaces": len(positives),
        "signature_sha256": policy.compact_sha256(signatures["JA"]),
        "rb_sequence_sha256": policy.compact_sha256(rb_sequences["JA"]),
        "boundary_mismatches": 0,
        "rb_sequence_mismatches": 0,
        "gate": True,
    }


def _stage_path(language: str) -> Path:
    destination = payload_path(language)
    return destination.with_name(destination.name + ".phase600_stage")


def _rollback_path(language: str) -> Path:
    destination = payload_path(language)
    return destination.with_name(destination.name + ".phase600_rollback")


def _cleanup(paths) -> None:
    for path in map(Path, paths):
        for candidate in (
            path,
            path.with_name(path.name + ".tmp_atomic_write"),
            path.with_name(path.name + ".tmp_atomic_copy"),
        ):
            try:
                candidate.unlink()
            except FileNotFoundError:
                pass


def prepare_repair(
    *, batch_size: int = 20, write_stages: bool = False,
) -> dict:
    if not isinstance(batch_size, int) or not 1 <= batch_size <= 200:
        raise ValueError("Phase 600 batch size must be in 1..200")
    phase599_closure = phase599_promotion.validate_trilingual_row_manifests()
    phase599_rows = phase599_closure["rows"]
    sources = {
        tuple(row[0] for row in policy.build_expected_rows(
            json.loads(payload_path(language).read_text(encoding="utf-8")),
            language,
        ))
        for language in LANGUAGES
    }
    if len(sources) != 1:
        raise ValueError("Phase 600 managed source order differs by language")
    payload_hashes_before = {
        language: file_sha256(payload_path(language))
        for language in LANGUAGES
    }
    runtime_before = {
        language: phase599_runtime.runtime_input_fingerprint(language)
        for language in LANGUAGES
    }
    kanji_before = phase599_runtime.kanji_track_fingerprint()
    stage_paths = {language: _stage_path(language) for language in LANGUAGES}
    if write_stages:
        stale = [
            str(path)
            for language, path in stage_paths.items()
            if path.exists() or _rollback_path(language).exists()
        ]
        if stale:
            raise ValueError(f"Phase 600 stale transaction files: {stale!r}")
    states = {}
    before_results = {}
    after_results = {}
    language_reports = {}
    width_reports = {}
    row_identities = {}
    stage_hashes = {}
    all_surfaces = [
        *policy.positive_surfaces(),
        *policy.negative_surfaces(),
    ]
    try:
        for language in LANGUAGES:
            payload = json.loads(
                payload_path(language).read_text(encoding="utf-8")
            )
            normalized, candidate, state = normalize_and_build_payload(
                payload, language, phase599_rows[language],
            )
            states[language] = state
            before_results[language] = _render(
                language, normalized, all_surfaces, batch_size=batch_size,
            )
            after_results[language] = _render(
                language, candidate, all_surfaces, batch_size=batch_size,
            )
            language_reports[language] = _validate_language_runtime(
                language, before_results[language], after_results[language],
            )
            managed = policy.validate_optional_layer(
                candidate, language, require_present=True,
            )
            width_reports[language] = _validate_widths(language, managed)
            row_identities[language] = policy.layer_identity(
                candidate, language,
            )
            if write_stages:
                atomic_json_dump(stage_paths[language], candidate)
                staged = json.loads(
                    stage_paths[language].read_text(encoding="utf-8")
                )
                _normalized, rebuilt, staged_state = (
                    normalize_and_build_payload(
                        staged, language, phase599_rows[language],
                    )
                )
                if (
                    staged_state["state"] != "promoted_canonical"
                    or rebuilt != staged
                ):
                    raise ValueError(
                        f"Phase 600 {language} staged payload drift"
                    )
                stage_hashes[language] = file_sha256(stage_paths[language])
            del payload, normalized, candidate
            gc.collect()
        trilingual = _validate_trilingual_runtime(
            after_results, language_reports,
        )
        payload_hashes_after = {
            language: file_sha256(payload_path(language))
            for language in LANGUAGES
        }
        runtime_after = {
            language: phase599_runtime.runtime_input_fingerprint(language)
            for language in LANGUAGES
        }
        kanji_after = phase599_runtime.kanji_track_fingerprint()
        if (
            payload_hashes_after != payload_hashes_before
            or runtime_after != runtime_before
            or kanji_after != kanji_before
        ):
            raise ValueError("Phase 600 inputs changed during preparation")
        all_canonical = all(
            state["state"] == "promoted_canonical"
            for state in states.values()
        )
        report = {
            "phase": policy.PHASE,
            "mode": "promotion_prepare",
            "managed_rows_per_language": policy.MANAGED_ROWS,
            "semantic_repairs": 50,
            "non_worsening_guards": 2,
            "states": states,
            "already_promoted": all_canonical,
            "writes_required": 0 if all_canonical else len(LANGUAGES),
            "normalized_phase599_global_rows": policy.NORMALIZED_GLOBAL_ROWS,
            "post_phase600_global_rows": policy.PROMOTED_GLOBAL_ROWS,
            "row_identities": row_identities,
            "runtime": language_reports,
            "trilingual": trilingual,
            "width": {
                "languages": width_reports,
                "max_effective_width_ratio": {
                    language: width_reports[language][
                        "max_effective_width_ratio"
                    ]
                    for language in LANGUAGES
                },
                "gate": True,
            },
            "deployed_payload_sha256_before": payload_hashes_before,
            "stage_payload_sha256": stage_hashes,
            "kanji_track_files_fingerprinted": len(kanji_before),
            "kanji_track_files_changed": 0,
            "kanji_nonintervention": True,
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
            _cleanup(stage_paths.values())
        raise


def plan_repair(*, batch_size: int = 20) -> dict:
    return prepare_repair(batch_size=batch_size)["report"]


def audit_deployed_repair(*, batch_size: int = 20) -> dict:
    report = prepare_repair(batch_size=batch_size)["report"]
    if (
        not report["already_promoted"]
        or report["writes_required"] != 0
        or any(
            state["state"] != "promoted_canonical"
            for state in report["states"].values()
        )
    ):
        raise ValueError("Phase 600 deployed repair is incomplete")
    return {
        **report,
        "mode": "deployed_repair_audit",
        "deployed_repair_gate": True,
    }


def _postcondition(batch_size: int) -> dict:
    return audit_deployed_repair(batch_size=batch_size)


def apply_repair(*, batch_size: int = 20) -> dict:
    prepared = prepare_repair(
        batch_size=batch_size, write_stages=True,
    )
    report = prepared["report"]
    if report["already_promoted"]:
        _cleanup(prepared["stage_paths"].values())
        return {
            **report,
            "mode": "promotion_noop",
            "transaction_writes": 0,
            "gate": True,
        }
    rollbacks = {
        language: _rollback_path(language) for language in LANGUAGES
    }
    replaced = []
    try:
        for language in LANGUAGES:
            atomic_binary_copy(payload_path(language), rollbacks[language])
        for language in LANGUAGES:
            os.replace(
                prepared["stage_paths"][language], payload_path(language)
            )
            replaced.append(language)
        post = _postcondition(batch_size)
    except Exception as original:
        errors = []
        for language in reversed(LANGUAGES):
            try:
                if language in replaced and rollbacks[language].exists():
                    os.replace(rollbacks[language], payload_path(language))
            except Exception as error:
                errors.append((language, repr(error)))
        _cleanup(prepared["stage_paths"].values())
        if errors:
            raise RuntimeError(
                f"Phase 600 rollback incomplete: {errors!r}"
            ) from original
        _cleanup(rollbacks.values())
        raise
    _cleanup(prepared["stage_paths"].values())
    _cleanup(rollbacks.values())
    return {
        **post,
        "mode": "promotion_applied",
        "transaction_writes": len(LANGUAGES),
        "gate": True,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "audit", "apply"):
        item = sub.add_parser(name)
        item.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args(argv)
    if args.command == "plan":
        report = plan_repair(batch_size=args.batch_size)
    elif args.command == "audit":
        report = audit_deployed_repair(batch_size=args.batch_size)
    else:
        report = apply_repair(batch_size=args.batch_size)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
