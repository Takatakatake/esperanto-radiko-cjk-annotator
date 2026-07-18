# -*- coding: utf-8 -*-
"""Fail-closed Phase 532 runtime gate for the frozen 58-row Ruby delta.

This gate has two deliberately different modes:

* ``pre-regen`` proves that the deployed runtime still exposes the reviewed
  Phase 513 signature for exactly the safe-seven rows and the selected Phase
  532 signature for the other 51 rows.  It is the permission gate to start a
  Ruby-only regeneration; seven selected-target mismatches are required.
* ``post-regen`` proves that an in-memory generated payload exposes all 58
  selected Phase 532 signatures in JA/ZH/KO before any generated JSON is
  written.

The ordinary no-worsening union represents 57 single words.  The one phrase,
``ritma gimnastiko``, is intentionally proved here as a bounded two-token
runtime expression; flattening ``ritm/a gimnastik/o`` through a single-word
slash parser would invent the ruby span ``a gimnastik``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from gen_replacement import load_app_replacement_helper
import no_worsening_audit as audit
import phase532_ruby_policy as policy


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("JA", "ZH", "KO")
MODES = ("pre-regen", "post-regen")
PRE_REGEN_SAFE7_DECOMPOSITIONS = {
    "lulu": "lulu",
    "suprenglisi": "supr/en/glis/i",
    "pasivaĵo": "pas/iv/aĵ/o",
    "pasivigi": "pas/iv/ig/i",
    "neologismemo": "neo/log/ism/em/o",
    "neologismemulo": "neo/log/ism/em/ul/o",
    "stenografistino": "sten/o/graf/ist/in/o",
}
PRE_REGEN_SAFE7_DECOMPOSITIONS_SHA256 = (
    "522D7DD6B4C079619A6AE9F42C8E11D5C01F608312FA2CBEA3D149A02A1A8459"
)

# These fingerprints bind every visible R/L span, including the literal space
# in the dedicated multiword expression.  They are filled from the frozen
# policy by the tests below and must change only with an explicit review.
PRE_REGEN_SIGNATURE_MANIFEST_SHA256 = (
    "245226991D8004CBA2B39237580375D54CCE6F10A6AF4E946A9FD74004E9644A"
)
POST_REGEN_SIGNATURE_MANIFEST_SHA256 = (
    "6B5234B6904961388E5F322B4E8E372AC97AF5D058603D73D79213CF2A6741BC"
)


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def _expression_signature(expression: dict, decomposition_override=None):
    kind = expression.get("kind")
    if kind == "word":
        decomposition = (
            decomposition_override
            if decomposition_override is not None
            else expression["decomposition"]
        )
        if policy.surface_from_decomposition(decomposition) != policy.canonical(
            expression["surface"]
        ):
            raise ValueError(
                f"Phase 532 word signature reconstruction drift: {expression!r}"
            )
        return audit.expected_signature(decomposition)
    if kind != "bounded_multiword" or decomposition_override is not None:
        raise ValueError(f"unsupported Phase 532 runtime expression: {expression!r}")
    if set(expression) != {"kind", "surface", "separator", "tokens"}:
        raise ValueError("Phase 532 multiword runtime schema drift")
    separator = expression["separator"]
    tokens = expression["tokens"]
    if separator != " " or len(tokens) != 2:
        raise ValueError("Phase 532 multiword runtime boundary drift")
    parts = []
    for index, token in enumerate(tokens):
        if set(token) != {"surface", "decomposition"}:
            raise ValueError("Phase 532 multiword token schema drift")
        if index:
            parts.append((separator, False))
        parts.extend(audit.expected_typed_parts(token["decomposition"]))
    signature = audit.signature_from_typed_parts(parts)
    if signature[0] != policy.canonical(expression["surface"]):
        raise ValueError("Phase 532 multiword signature reconstruction drift")
    return signature


def expected_signatures(mode: str):
    if mode not in MODES:
        raise ValueError(f"unsupported Phase 532 runtime gate mode: {mode!r}")
    expressions = policy.selected_ruby_expressions()
    if set(PRE_REGEN_SAFE7_DECOMPOSITIONS) != set(
        policy.EXPECTED_SAFE_TARGETS
    ) or compact_sha256(PRE_REGEN_SAFE7_DECOMPOSITIONS) != (
        PRE_REGEN_SAFE7_DECOMPOSITIONS_SHA256
    ):
        raise ValueError("Phase 532 pre-regen safe-seven scope drift")
    signatures = {}
    for surface, expression in expressions.items():
        override = (
            PRE_REGEN_SAFE7_DECOMPOSITIONS.get(surface)
            if mode == "pre-regen" else None
        )
        signatures[surface] = _expression_signature(expression, override)
    if len(signatures) != 58:
        raise ValueError("Phase 532 runtime signature scope is not 58")
    manifest = [
        {
            "surface": surface,
            "signature": audit.signature_payload(signatures[surface]),
        }
        for surface in sorted(signatures)
    ]
    actual_sha256 = compact_sha256(manifest)
    expected_sha256 = {
        "pre-regen": PRE_REGEN_SIGNATURE_MANIFEST_SHA256,
        "post-regen": POST_REGEN_SIGNATURE_MANIFEST_SHA256,
    }[mode]
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"Phase 532 {mode} expected-signature manifest drift: "
            f"{actual_sha256} != {expected_sha256}"
        )
    return signatures, actual_sha256


def _normalize_signature(signature):
    if not isinstance(signature, (tuple, list)) or len(signature) != 2:
        raise ValueError(f"invalid runtime signature: {signature!r}")
    reconstruction, spans = signature
    normalized_spans = []
    if not isinstance(reconstruction, str) or not isinstance(spans, (tuple, list)):
        raise ValueError(f"invalid runtime signature: {signature!r}")
    for span in spans:
        if (
            not isinstance(span, (tuple, list))
            or len(span) != 2
            or not isinstance(span[0], str)
            or not isinstance(span[1], bool)
        ):
            raise ValueError(f"invalid runtime signature span: {span!r}")
        normalized_spans.append((policy.canonical(span[0]), span[1]))
    return policy.canonical(reconstruction), tuple(normalized_spans)


def validate_rendered_results(results_by_language: dict, mode: str) -> dict:
    """Validate already-rendered results; useful for focused tamper tests."""
    if set(results_by_language) != set(LANGUAGES):
        raise ValueError("Phase 532 runtime languages must be exactly JA/ZH/KO")
    expected, expected_manifest_sha256 = expected_signatures(mode)
    post_expected, _post_manifest_sha256 = expected_signatures("post-regen")
    surfaces = set(expected)
    normalized = {}
    mismatches = {}
    selected_mismatches = {}
    for language in LANGUAGES:
        language_results = results_by_language[language]
        if not isinstance(language_results, dict) or set(language_results) != surfaces:
            raise ValueError(
                f"Phase 532 {language} runtime surface scope drift"
            )
        normalized[language] = {}
        mismatches[language] = []
        selected_mismatches[language] = []
        for surface in sorted(surfaces):
            row = language_results[surface]
            signature = row.get("signature") if isinstance(row, dict) else row
            signature = _normalize_signature(signature)
            normalized[language][surface] = signature
            if signature != expected[surface]:
                mismatches[language].append(surface)
            if signature != post_expected[surface]:
                selected_mismatches[language].append(surface)

    trilingual_mismatches = [
        surface for surface in sorted(surfaces)
        if len({normalized[language][surface] for language in LANGUAGES}) != 1
    ]
    expected_selected_mismatches = (
        sorted(PRE_REGEN_SAFE7_DECOMPOSITIONS)
        if mode == "pre-regen" else []
    )
    if (
        any(mismatches.values())
        or trilingual_mismatches
        or any(
            selected_mismatches[language] != expected_selected_mismatches
            for language in LANGUAGES
        )
    ):
        raise ValueError(
            "Phase 532 runtime signature gate failed: "
            f"mode={mode!r}, mismatches={mismatches!r}, "
            f"selected_mismatches={selected_mismatches!r}, "
            f"trilingual={trilingual_mismatches!r}"
        )

    actual_manifests = {}
    for language in LANGUAGES:
        manifest = [
            {
                "surface": surface,
                "signature": audit.signature_payload(
                    normalized[language][surface]
                ),
            }
            for surface in sorted(surfaces)
        ]
        actual_manifests[language] = compact_sha256(manifest)
    if set(actual_manifests.values()) != {expected_manifest_sha256}:
        raise ValueError(
            f"Phase 532 runtime signature manifest drift: {actual_manifests!r}"
        )
    multiword = policy.MULTIWORD_EXPRESSION["surface"]
    return {
        "phase": policy.PHASE,
        "mode": mode,
        "languages": list(LANGUAGES),
        "surfaces": len(surfaces),
        "ordinary_words": 57,
        "bounded_multiword_expressions": 1,
        "multiword_surface": multiword,
        "multiword_signature": audit.signature_payload(
            normalized["JA"][multiword]
        ),
        "selected_target_mismatches": len(expected_selected_mismatches),
        "selected_target_mismatch_surfaces": expected_selected_mismatches,
        "trilingual_mismatches": 0,
        "signature_manifest_sha256": expected_manifest_sha256,
        "gate": True,
    }


def _validate_payload_shape(payload, language):
    if not isinstance(payload, dict) or len(payload) != 3:
        raise ValueError(f"Phase 532 {language} candidate payload schema drift")
    local_rules, global_rules, two_char_rules = audit.extract_lists(payload)
    if any(not isinstance(rules, list) for rules in (
        local_rules, global_rules, two_char_rules,
    )):
        raise ValueError(f"Phase 532 {language} candidate rule-list drift")


def validate_generated_payloads(
    payloads_by_language: dict, mode: str, *, batch_size: int = 58,
) -> dict:
    """Render three in-memory payloads through the deployed app runtime."""
    if set(payloads_by_language) != set(LANGUAGES):
        raise ValueError("Phase 532 candidate payloads must be exactly JA/ZH/KO")
    if not isinstance(batch_size, int) or not 1 <= batch_size <= 58:
        raise ValueError("Phase 532 runtime batch size must be in 1..58")
    expressions = policy.selected_ruby_expressions()
    surfaces = list(expressions)
    policy_identity_before = policy.review_identity()
    policy_file_hashes_before = {
        str(path): policy.file_sha256(path)
        for path in (policy.UNMARKED_REVIEW_PATH, policy.FAKE_TRANSITION_PATH)
    }
    payload_hashes_before = {}
    app_fingerprints_before = {}
    for language in LANGUAGES:
        _validate_payload_shape(payloads_by_language[language], language)
        payload_hashes_before[language] = compact_sha256(
            payloads_by_language[language]
        )
        app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
        app_fingerprints_before[language] = audit.current_app_fingerprint(
            app_dir
        )

    rendered = {}
    for language in LANGUAGES:
        app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
        load_app_replacement_helper(app_dir)
        runtime = audit.runtime_module(app_dir, f"phase532_{mode}_{language}")
        overlay = audit.overlay_module(
            app_dir, f"phase532_{mode}_overlay_{language}",
        )
        corrections = json.loads(
            (app_dir / "app_data" / "user_corrections.json").read_text(
                encoding="utf-8"
            )
        )
        rendered[language] = audit.render_signatures(
            runtime, app_dir, payloads_by_language[language], surfaces,
            batch_size, overlay=overlay, corrections=corrections,
        )
    report = validate_rendered_results(rendered, mode)

    payload_hashes_after = {
        language: compact_sha256(payloads_by_language[language])
        for language in LANGUAGES
    }
    app_fingerprints_after = {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in LANGUAGES
    }
    policy_file_hashes_after = {
        str(path): policy.file_sha256(path)
        for path in (policy.UNMARKED_REVIEW_PATH, policy.FAKE_TRANSITION_PATH)
    }
    if (
        payload_hashes_after != payload_hashes_before
        or app_fingerprints_after != app_fingerprints_before
        or policy_file_hashes_after != policy_file_hashes_before
        or policy.review_identity() != policy_identity_before
    ):
        raise ValueError("Phase 532 runtime gate input changed during rendering")
    report.update({
        "candidate_payload_sha256": payload_hashes_before,
        "app_input_fingerprints": app_fingerprints_before,
        "policy_identity": policy_identity_before,
        "all_inputs_stable": True,
    })
    return report


def load_deployed_payloads() -> dict:
    return {
        language: json.loads(
            (
                ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
                / "置換リスト_ルビ.json"
            ).read_text(encoding="utf-8")
        )
        for language in LANGUAGES
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--deployed", action="store_true", required=True)
    parser.add_argument("--batch-size", type=int, default=58)
    args = parser.parse_args(argv)
    report = validate_generated_payloads(
        load_deployed_payloads(), args.mode, batch_size=args.batch_size,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
