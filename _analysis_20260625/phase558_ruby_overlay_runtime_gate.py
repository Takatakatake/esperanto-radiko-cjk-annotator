# -*- coding: utf-8 -*-
"""Pre/post runtime boundary and gloss gate for Phase 558 Ruby repairs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from gen_replacement import load_app_replacement_helper
import no_worsening_audit as audit
import phase558_ruby_overlay as policy
from phase558_ruby_overlay_activation import activation_report


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("JA", "ZH", "KO")
MODES = ("pre-regen", "post-regen")
PRE_REGEN_TARGETS = {
    "kateĥismo": {"target": "kateĥ/ism/o", "typed_roles": "RRL"},
    "kateĥisto": {"target": "kateĥ/ist/o", "typed_roles": "RRL"},
    "magnetito": {"target": "magnet/it/o", "typed_roles": "RRL"},
    "Izraelio": {"target": "Izraeli/o", "typed_roles": "RL"},
    "tia-tia": {"target": "ti/a-/ti/a", "typed_roles": "RLRL"},
}
PRE_REGEN_TARGETS_SHA256 = (
    "449E05CE110F5A8A3D39D7B537AEF7E39F0ED226E73D2AE5C6E016D6DF49B4BE"
)
EXPECTED_SIGNATURE_MANIFEST_SHA256 = {
    "pre-regen": "97168743392D1ADED54A89F39D680961F59C39CFC348DA3D163083A0E3B59EF8",
    "post-regen": "F2C589D6F2C0A4F57A1374CD68C727D618F9AC17D6C01A6B18177658974714CA",
}
SCOPE_GUARD_TARGETS = {
    # Productive grammatical forms that the two bounded morph rules are
    # intentionally allowed to coarsen.
    "kateĥismoj": {"target": "kateĥism/oj", "typed_roles": "RL"},
    "kateĥismon": {"target": "kateĥism/on", "typed_roles": "RL"},
    "kateĥisma": {"target": "kateĥism/a", "typed_roles": "RL"},
    "kateĥisme": {"target": "kateĥism/e", "typed_roles": "RL"},
    "Kateĥismo": {"target": "Kateĥism/o", "typed_roles": "RL"},
    "KATEĤISMO": {"target": "KATEĤISM/O", "typed_roles": "RL"},
    "kateĥistoj": {"target": "kateĥist/oj", "typed_roles": "RL"},
    "kateĥiston": {"target": "kateĥist/on", "typed_roles": "RL"},
    "Kateĥisto": {"target": "Kateĥist/o", "typed_roles": "RL"},
    "KATEĤISTO": {"target": "KATEĤIST/O", "typed_roles": "RL"},
    # Longer productive families and exact/case/suffix neighbours must remain
    # byte-for-boundary compatible with the deployed Phase 532 runtime.
    "kateĥistino": {"target": "kateĥ/ist/in/o", "typed_roles": "RRRL"},
    "kateĥistinoj": {"target": "kateĥ/ist/in/oj", "typed_roles": "RRRL"},
    "magnetita": {"target": "magnet/it/a", "typed_roles": "RRL"},
    "magnetitoj": {"target": "magnet/it/oj", "typed_roles": "RRL"},
    "Tia-tia": {"target": "Tia/-/tia", "typed_roles": "RLR"},
    "TIA-TIA": {"target": "TIA/-/TIA", "typed_roles": "RLR"},
    "izraelio": {"target": "izraeli/o", "typed_roles": "RL"},
    "IZRAELIO": {"target": "IZRAELI/O", "typed_roles": "RL"},
    "Izraelion": {"target": "Izraeli/on", "typed_roles": "RL"},
    "Japanio": {"target": "Japan/io", "typed_roles": "RL"},
    "Izraelo": {"target": "Izrael/o", "typed_roles": "RL"},
    "Izraelidoj": {"target": "Izrael/id/oj", "typed_roles": "RRL"},
    "tien": {"target": "tie/n", "typed_roles": "RL"},
    "ĉiuj": {"target": "ĉiu/j", "typed_roles": "RL"},
    "tiamanere": {"target": "tiam/an/er/e", "typed_roles": "RLRL"},
    "tiaspeca": {"target": "ti/a/spec/a", "typed_roles": "RLRL"},
    "monarĥio": {"target": "monarĥi/o", "typed_roles": "RL"},
    "oligarĥio": {"target": "oligarĥi/o", "typed_roles": "RL"},
}
SCOPE_GUARD_TARGETS_SHA256 = (
    "EDE56F7207E5FB6102C7FE7493B24EB0765E5A492139A844673C77559BDC1A08"
)
SCOPE_GUARD_SIGNATURE_MANIFEST_SHA256 = (
    "E9F63E8AF863F99434F446CE1A3E251DFCB6CA20794502D24285CB3D5101BAD4"
)
PRODUCTIVE_VARIANT_ENDINGS = (
    "a", "aj", "ajn", "an", "e", "en", "o", "oj", "ojn", "on",
)
PRODUCTIVE_VARIANT_CASES = ("lower", "initial", "upper")
PAYLOAD_VARIANT_COUNTS = {
    "adjudicated_source_rows": 5,
    "productive_rules": 2,
    "productive_endings": 10,
    "productive_cases": 3,
    "productive_payload_variants": 60,
    "exact_payload_variants": 3,
    "expanded_payload_variants": 63,
}
PAYLOAD_VARIANT_MANIFEST_SHA256 = (
    "5971B203E379C8F7D3AD07C13E9A34480C071E9EA113B2DF36B2C32327DB5A35"
)
PAYLOAD_GLOSS_MANIFEST_SHA256 = (
    "77F2FD0EB8F87B59DFBDD041ADCFBF2B9BFD6D3DB34BEBCCB27FFA99CCB546F0"
)


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def _signature(target: str, typed_roles: str | None = None):
    pieces = [piece for piece in target.split("/") if piece]
    if typed_roles is None:
        return audit.expected_signature(target)
    if (
        len(pieces) != len(typed_roles)
        or any(role not in "RL" for role in typed_roles)
    ):
        raise ValueError(f"invalid Phase 558 typed target: {target!r}")
    return audit.signature_from_typed_parts([
        (piece, role == "R") for piece, role in zip(pieces, typed_roles)
    ])


def _case_variant(stem: str, ending: str, case: str) -> tuple[str, str]:
    if case == "lower":
        return stem + ending, f"{stem}/{ending}"
    if case == "initial":
        initial_stem = stem[:1].upper() + stem[1:]
        return initial_stem + ending, f"{initial_stem}/{ending}"
    if case == "upper":
        return stem.upper() + ending.upper(), f"{stem.upper()}/{ending.upper()}"
    raise ValueError(f"invalid productive variant case: {case!r}")


def payload_variant_signatures():
    """Seal 5 adjudicated source rows separately from 63 payload forms."""
    signatures = {}
    productive = policy.managed_morph_targets()
    if len(productive) != PAYLOAD_VARIANT_COUNTS["productive_rules"]:
        raise ValueError("Phase 558 productive payload rule count drift")
    for spec in productive.values():
        stem = spec["target"].rsplit("/", 1)[0]
        for ending in PRODUCTIVE_VARIANT_ENDINGS:
            for case in PRODUCTIVE_VARIANT_CASES:
                surface, target = _case_variant(stem, ending, case)
                if surface in signatures:
                    raise ValueError(
                        f"duplicate Phase 558 payload variant: {surface!r}"
                    )
                signatures[surface] = _signature(target, "RL")
    exact = policy.typed_exact_targets()
    if len(exact) != PAYLOAD_VARIANT_COUNTS["exact_payload_variants"]:
        raise ValueError("Phase 558 exact payload rule count drift")
    for surface, spec in exact.items():
        if surface in signatures:
            raise ValueError(f"duplicate Phase 558 exact variant: {surface!r}")
        signatures[surface] = _signature(
            spec["target"], spec["typed_roles"],
        )
    if (
        len(signatures)
        != PAYLOAD_VARIANT_COUNTS["expanded_payload_variants"]
        or len(signatures) - len(exact)
        != PAYLOAD_VARIANT_COUNTS["productive_payload_variants"]
        or len(policy.selected_ruby_targets())
        != PAYLOAD_VARIANT_COUNTS["adjudicated_source_rows"]
    ):
        raise ValueError("Phase 558 payload variant expansion drift")
    manifest = [{
        "surface": surface,
        "signature": audit.signature_payload(signatures[surface]),
    } for surface in sorted(signatures)]
    digest = compact_sha256(manifest)
    if PAYLOAD_VARIANT_MANIFEST_SHA256.startswith("TO_BE_SEALED"):
        raise ValueError(f"unsealed Phase 558 payload variants: {digest}")
    if digest != PAYLOAD_VARIANT_MANIFEST_SHA256:
        raise ValueError("Phase 558 payload variant manifest drift")
    return signatures, digest


def payload_variant_glosses():
    """Seal expected JA/ZH/KO ``rb``/``rt`` pairs for all 63 forms.

    The productive forms inherit their language-specific annotation through
    ``morph_context_annotations``; the three exact forms use the indexed
    ``typed_context_glosses`` authority.  This keeps the gloss authority bound
    to the reviewed Phase 558 policy rather than duplicating it in this gate.
    """
    signatures, _signature_digest = payload_variant_signatures()
    expected = {language: {} for language in LANGUAGES}
    morph_annotations = policy.morph_context_annotations()
    productive = policy.managed_morph_targets()
    expected_context_keys = {
        spec["ruby_context_annotation"] for spec in productive.values()
    }
    if set(morph_annotations) != expected_context_keys:
        raise ValueError("Phase 558 productive gloss context scope drift")
    for spec in productive.values():
        stem = spec["target"].rsplit("/", 1)[0]
        context_key = spec["ruby_context_annotation"]
        annotation = morph_annotations[context_key]
        if (
            set(annotation) != {"piece", "glosses"}
            or policy.phase532.canonical(annotation["piece"])
            != policy.phase532.canonical(stem)
            or set(annotation["glosses"]) != {"ja", "zh", "ko"}
        ):
            raise ValueError(
                f"Phase 558 productive gloss authority drift: {context_key!r}"
            )
        for ending in PRODUCTIVE_VARIANT_ENDINGS:
            for case in PRODUCTIVE_VARIANT_CASES:
                surface, target = _case_variant(stem, ending, case)
                rb = target.rsplit("/", 1)[0]
                for language in LANGUAGES:
                    expected[language][surface] = [{
                        "rb": rb,
                        "rt": annotation["glosses"][language.lower()],
                    }]

    typed_glosses = policy.typed_context_glosses()
    used_typed_keys = set()
    for surface, spec in policy.typed_exact_targets().items():
        pieces = [piece for piece in spec["target"].split("/") if piece]
        roles = spec["typed_roles"]
        if len(pieces) != len(roles):
            raise ValueError(f"Phase 558 typed gloss target drift: {surface!r}")
        for language in LANGUAGES:
            expected[language][surface] = []
        for index, (piece, role) in enumerate(zip(pieces, roles)):
            if role != "R":
                continue
            key = (surface, index, piece)
            glosses = typed_glosses.get(key)
            if glosses is None or set(glosses) != {"ja", "zh", "ko"}:
                raise ValueError(
                    f"Phase 558 typed gloss authority drift: {key!r}"
                )
            used_typed_keys.add(key)
            for language in LANGUAGES:
                expected[language][surface].append({
                    "rb": piece, "rt": glosses[language.lower()],
                })
    if used_typed_keys != set(typed_glosses):
        raise ValueError("Phase 558 typed gloss authority scope drift")
    if any(set(expected[language]) != set(signatures) for language in LANGUAGES):
        raise ValueError("Phase 558 payload gloss surface scope drift")

    manifest = [{
        "language": language,
        "surface": surface,
        "annotations": expected[language][surface],
    } for language in LANGUAGES for surface in sorted(signatures)]
    digest = compact_sha256(manifest)
    if PAYLOAD_GLOSS_MANIFEST_SHA256 == "TO_BE_SEALED":
        raise ValueError(f"unsealed Phase 558 payload glosses: {digest}")
    if digest != PAYLOAD_GLOSS_MANIFEST_SHA256:
        raise ValueError("Phase 558 payload gloss manifest drift")
    return expected, digest


def _normalize_annotations(annotations):
    if not isinstance(annotations, (list, tuple)):
        raise ValueError(f"invalid Phase 558 runtime annotations: {annotations!r}")
    normalized = []
    for annotation in annotations:
        if (
            not isinstance(annotation, dict)
            or set(annotation) != {"rb", "rt"}
            or not isinstance(annotation["rb"], str)
            or not isinstance(annotation["rt"], str)
        ):
            raise ValueError(
                f"invalid Phase 558 runtime annotation: {annotation!r}"
            )
        normalized.append({
            "rb": audit.canonical(annotation["rb"]),
            "rt": annotation["rt"],
        })
    return normalized


def validate_payload_gloss_results(results_by_language: dict) -> dict:
    """Reject any rendered boundary or gloss drift across all 63 forms."""
    if set(results_by_language) != set(LANGUAGES):
        raise ValueError("Phase 558 payload glosses require exactly JA/ZH/KO")
    expected_signatures_by_surface, _digest = payload_variant_signatures()
    expected_glosses, manifest_sha256 = payload_variant_glosses()
    actual_glosses = {language: {} for language in LANGUAGES}
    mismatches = {language: [] for language in LANGUAGES}
    rb_by_language = {language: {} for language in LANGUAGES}
    for language in LANGUAGES:
        rows = results_by_language[language]
        if not isinstance(rows, dict) or set(rows) != set(expected_glosses[language]):
            raise ValueError(f"Phase 558 {language} payload gloss surface drift")
        for surface in sorted(expected_glosses[language]):
            row = rows[surface]
            if not isinstance(row, dict) or "signature" not in row:
                raise ValueError(
                    f"Phase 558 {language} payload gloss row drift: {surface!r}"
                )
            signature = _normalize_signature(row["signature"])
            annotations = _normalize_annotations(row.get("annotations"))
            actual_glosses[language][surface] = annotations
            rb_by_language[language][surface] = tuple(
                annotation["rb"] for annotation in annotations
            )
            if (
                signature != expected_signatures_by_surface[surface]
                or annotations != expected_glosses[language][surface]
            ):
                mismatches[language].append(surface)
    trilingual_rb_mismatches = [
        surface for surface in sorted(expected_signatures_by_surface)
        if len({rb_by_language[language][surface] for language in LANGUAGES}) != 1
    ]
    if any(mismatches.values()) or trilingual_rb_mismatches:
        raise ValueError(
            "Phase 558 payload gloss gate failed: "
            f"mismatches={mismatches!r}, "
            f"trilingual_rb={trilingual_rb_mismatches!r}"
        )
    actual_manifest = [{
        "language": language,
        "surface": surface,
        "annotations": actual_glosses[language][surface],
    } for language in LANGUAGES
      for surface in sorted(expected_signatures_by_surface)]
    actual_digest = compact_sha256(actual_manifest)
    if actual_digest != manifest_sha256:
        raise ValueError("Phase 558 rendered payload gloss manifest drift")
    annotation_counts = {
        language: sum(
            len(annotations)
            for annotations in actual_glosses[language].values()
        ) for language in LANGUAGES
    }
    if set(annotation_counts.values()) != {64}:
        raise ValueError(
            f"Phase 558 payload gloss annotation count drift: "
            f"{annotation_counts!r}"
        )
    return {
        "payload_gloss_surfaces": len(expected_signatures_by_surface),
        "payload_gloss_annotations_per_language": annotation_counts,
        "payload_gloss_manifest_sha256": manifest_sha256,
        "payload_gloss_mismatches": 0,
        "payload_gloss_rb_trilingual_mismatches": 0,
        "payload_gloss_gate": True,
    }


def validate_payload_variant_closure(payloads_by_language: dict) -> dict:
    """Require exactly one bounded rule for every one of the 63 forms."""
    if set(payloads_by_language) != set(LANGUAGES):
        raise ValueError("Phase 558 payload variants require exactly JA/ZH/KO")
    expected, manifest_sha256 = payload_variant_signatures()
    normalized = {}
    mismatches = {}
    for language in LANGUAGES:
        payload = payloads_by_language[language]
        _validate_payload_shape(payload, language)
        rows_by_surface = {surface: [] for surface in expected}
        for rows in audit.extract_lists(payload):
            for row in rows:
                if not isinstance(row, (list, tuple)) or len(row) < 2:
                    continue
                source = row[0]
                if not isinstance(source, str):
                    continue
                surface = source.strip()
                if surface in rows_by_surface:
                    rows_by_surface[surface].append(row)
        normalized[language] = {}
        mismatches[language] = []
        for surface in sorted(expected):
            matches = rows_by_surface[surface]
            if (
                len(matches) != 1
                or matches[0][0] != f" {surface} "
                or not isinstance(matches[0][1], str)
            ):
                raise ValueError(
                    f"Phase 558 {language} payload variant row drift: "
                    f"{surface!r}/{len(matches)}"
                )
            signature = audit.signature_from_typed_parts(
                audit.rendered_typed_parts(matches[0][1])
            )
            signature = _normalize_signature(signature)
            normalized[language][surface] = signature
            if signature != expected[surface]:
                mismatches[language].append(surface)
    trilingual = [
        surface for surface in sorted(expected)
        if len({normalized[language][surface] for language in LANGUAGES}) != 1
    ]
    if any(mismatches.values()) or trilingual:
        raise ValueError(
            "Phase 558 payload variant closure failed: "
            f"mismatches={mismatches!r}, trilingual={trilingual!r}"
        )
    return {
        **PAYLOAD_VARIANT_COUNTS,
        "payload_variant_manifest_sha256": manifest_sha256,
        "payload_variant_trilingual_mismatches": 0,
        "payload_variant_gate": True,
    }


def expected_signatures(mode: str):
    if mode not in MODES:
        raise ValueError(f"unsupported Phase 558 runtime mode: {mode!r}")
    if compact_sha256(PRE_REGEN_TARGETS) != PRE_REGEN_TARGETS_SHA256:
        raise ValueError("Phase 558 pre-regen target identity drift")
    review = policy.load_review()
    if mode == "pre-regen":
        specs = PRE_REGEN_TARGETS
    else:
        specs = {
            entry["surface"]: {
                "target": entry["selected_ruby_target"],
                "typed_roles": (
                    entry["setting"].get("typed_roles")
                    if entry["setting"]["kind"] == "exact_typed_ruby_only"
                    else None
                ),
            }
            for entry in review["entries"]
        }
    signatures = {
        surface: _signature(spec["target"], spec.get("typed_roles"))
        for surface, spec in specs.items()
    }
    if set(signatures) != set(policy.EXPECTED_ROWS) or len(signatures) != 5:
        raise ValueError("Phase 558 runtime surface scope drift")
    manifest = [{
        "surface": surface,
        "signature": audit.signature_payload(signatures[surface]),
    } for surface in sorted(signatures)]
    digest = compact_sha256(manifest)
    expected = EXPECTED_SIGNATURE_MANIFEST_SHA256[mode]
    if expected.startswith("TO_BE_FILLED"):
        raise ValueError(f"unsealed Phase 558 {mode} signature manifest: {digest}")
    if digest != expected:
        raise ValueError(
            f"Phase 558 {mode} signature manifest drift: {digest} != {expected}"
        )
    return signatures, digest


def scope_guard_signatures():
    target_digest = compact_sha256(SCOPE_GUARD_TARGETS)
    if SCOPE_GUARD_TARGETS_SHA256.startswith("TO_BE_FILLED"):
        raise ValueError(f"unsealed Phase 558 scope targets: {target_digest}")
    if target_digest != SCOPE_GUARD_TARGETS_SHA256:
        raise ValueError("Phase 558 scope target identity drift")
    if set(SCOPE_GUARD_TARGETS) & set(policy.selected_ruby_targets()):
        raise ValueError("Phase 558 scope guard overlaps the five-row review")
    signatures = {
        surface: _signature(spec["target"], spec["typed_roles"])
        for surface, spec in SCOPE_GUARD_TARGETS.items()
    }
    manifest = [{
        "surface": surface,
        "signature": audit.signature_payload(signatures[surface]),
    } for surface in sorted(signatures)]
    digest = compact_sha256(manifest)
    if SCOPE_GUARD_SIGNATURE_MANIFEST_SHA256.startswith("TO_BE_FILLED"):
        raise ValueError(f"unsealed Phase 558 scope signatures: {digest}")
    if digest != SCOPE_GUARD_SIGNATURE_MANIFEST_SHA256:
        raise ValueError("Phase 558 scope signature identity drift")
    return signatures, digest


def _normalize_signature(signature):
    if not isinstance(signature, (tuple, list)) or len(signature) != 2:
        raise ValueError(f"invalid Phase 558 runtime signature: {signature!r}")
    reconstruction, spans = signature
    if any(
        not isinstance(text, str) or not isinstance(is_ruby, bool)
        for text, is_ruby in spans
    ):
        raise ValueError(f"invalid Phase 558 runtime span: {spans!r}")
    normalized = tuple((policy.phase532.canonical(text), is_ruby)
                       for text, is_ruby in spans)
    return policy.phase532.canonical(reconstruction), normalized


def validate_scope_guard_results(results_by_language: dict) -> dict:
    if set(results_by_language) != set(LANGUAGES):
        raise ValueError("Phase 558 scope languages must be exactly JA/ZH/KO")
    expected, manifest_sha256 = scope_guard_signatures()
    normalized = {}
    mismatches = {}
    for language in LANGUAGES:
        rows = results_by_language[language]
        if not isinstance(rows, dict) or set(rows) != set(expected):
            raise ValueError(f"Phase 558 {language} scope surface drift")
        normalized[language] = {}
        mismatches[language] = []
        for surface in sorted(expected):
            row = rows[surface]
            signature = row.get("signature") if isinstance(row, dict) else row
            signature = _normalize_signature(signature)
            normalized[language][surface] = signature
            if signature != expected[surface]:
                mismatches[language].append(surface)
    trilingual = [
        surface for surface in sorted(expected)
        if len({normalized[language][surface] for language in LANGUAGES}) != 1
    ]
    if any(mismatches.values()) or trilingual:
        raise ValueError(
            "Phase 558 runtime scope guard failed: "
            f"mismatches={mismatches!r}, trilingual={trilingual!r}"
        )
    return {
        "scope_guard_surfaces": len(expected),
        "scope_guard_trilingual_mismatches": 0,
        "scope_guard_signature_manifest_sha256": manifest_sha256,
        "scope_guard_gate": True,
    }


def validate_rendered_results(results_by_language: dict, mode: str) -> dict:
    if set(results_by_language) != set(LANGUAGES):
        raise ValueError("Phase 558 runtime languages must be exactly JA/ZH/KO")
    expected, manifest_sha256 = expected_signatures(mode)
    normalized = {}
    mismatches = {}
    for language in LANGUAGES:
        rows = results_by_language[language]
        if not isinstance(rows, dict) or set(rows) != set(expected):
            raise ValueError(f"Phase 558 {language} runtime surface scope drift")
        normalized[language] = {}
        mismatches[language] = []
        for surface in sorted(expected):
            row = rows[surface]
            signature = row.get("signature") if isinstance(row, dict) else row
            signature = _normalize_signature(signature)
            normalized[language][surface] = signature
            if signature != expected[surface]:
                mismatches[language].append(surface)
    trilingual = [
        surface for surface in sorted(expected)
        if len({normalized[language][surface] for language in LANGUAGES}) != 1
    ]
    if any(mismatches.values()) or trilingual:
        raise ValueError(
            "Phase 558 runtime signature gate failed: "
            f"mode={mode!r}, mismatches={mismatches!r}, "
            f"trilingual={trilingual!r}"
        )
    actual = {
        language: compact_sha256([{
            "surface": surface,
            "signature": audit.signature_payload(
                normalized[language][surface]
            ),
        } for surface in sorted(expected)])
        for language in LANGUAGES
    }
    if set(actual.values()) != {manifest_sha256}:
        raise ValueError(f"Phase 558 runtime manifest drift: {actual!r}")
    return {
        "phase": policy.PHASE_TO,
        "mode": mode,
        "languages": list(LANGUAGES),
        "surfaces": len(expected),
        "trilingual_mismatches": 0,
        "signature_manifest_sha256": manifest_sha256,
        "gate": True,
    }


def _validate_payload_shape(payload, language):
    if not isinstance(payload, dict) or len(payload) != 3:
        raise ValueError(f"Phase 558 {language} candidate payload schema drift")
    local_rules, global_rules, two_char_rules = audit.extract_lists(payload)
    if any(not isinstance(rows, list) for rows in (
        local_rules, global_rules, two_char_rules,
    )):
        raise ValueError(f"Phase 558 {language} candidate rule-list drift")


def validate_generated_payloads(
    payloads_by_language: dict, mode: str, *, batch_size: int = 5,
) -> dict:
    if set(payloads_by_language) != set(LANGUAGES):
        raise ValueError("Phase 558 candidate payloads must be exactly JA/ZH/KO")
    if not isinstance(batch_size, int) or not 1 <= batch_size <= 33:
        raise ValueError("Phase 558 runtime batch size must be in 1..33")
    activation = activation_report()
    if not activation.get("phase558_ruby_overlay_active"):
        raise ValueError("Phase 558 runtime gate lacks formal activation")
    selected_surfaces = list(policy.selected_ruby_targets())
    scope_surfaces = list(scope_guard_signatures()[0])
    payload_variant_surfaces = (
        list(payload_variant_signatures()[0])
        if mode == "post-regen" else []
    )
    surfaces = list(dict.fromkeys(
        selected_surfaces + scope_surfaces + payload_variant_surfaces
    ))
    review_before = policy.review_identity()
    payload_hashes_before = {}
    app_fingerprints_before = {}
    for language in LANGUAGES:
        _validate_payload_shape(payloads_by_language[language], language)
        payload_hashes_before[language] = compact_sha256(
            payloads_by_language[language]
        )
        app_fingerprints_before[language] = audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
    payload_variant_report = (
        validate_payload_variant_closure(payloads_by_language)
        if mode == "post-regen" else None
    )
    rendered = {}
    for language in LANGUAGES:
        app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
        load_app_replacement_helper(app_dir)
        runtime = audit.runtime_module(
            app_dir, f"phase558_{mode}_{language}",
        )
        runtime_overlay = audit.overlay_module(
            app_dir, f"phase558_{mode}_overlay_{language}",
        )
        corrections = json.loads(
            (app_dir / "app_data" / "user_corrections.json").read_text(
                encoding="utf-8"
            )
        )
        rendered[language] = audit.render_signatures(
            runtime, app_dir, payloads_by_language[language], surfaces,
            batch_size, overlay=runtime_overlay, corrections=corrections,
            include_annotations=(mode == "post-regen"),
        )
    report = validate_rendered_results({
        language: {
            surface: rendered[language][surface]
            for surface in selected_surfaces
        } for language in LANGUAGES
    }, mode)
    report.update(validate_scope_guard_results({
        language: {
            surface: rendered[language][surface]
            for surface in scope_surfaces
        } for language in LANGUAGES
    }))
    if payload_variant_report is not None:
        report.update(payload_variant_report)
        report.update(validate_payload_gloss_results({
            language: {
                surface: rendered[language][surface]
                for surface in payload_variant_surfaces
            } for language in LANGUAGES
        }))
    payload_hashes_after = {
        language: compact_sha256(payloads_by_language[language])
        for language in LANGUAGES
    }
    app_fingerprints_after = {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        ) for language in LANGUAGES
    }
    if (
        payload_hashes_after != payload_hashes_before
        or app_fingerprints_after != app_fingerprints_before
        or policy.review_identity() != review_before
    ):
        raise ValueError("Phase 558 runtime gate input changed during rendering")
    report.update({
        "candidate_payload_sha256": payload_hashes_before,
        "app_input_fingerprints": app_fingerprints_before,
        "overlay_review": review_before,
        "all_inputs_stable": True,
    })
    return report


def deployed_payload_path(language: str) -> Path:
    return (
        ROOT / f"Esperanto-Kanji-Ruby-{language}" / "app_data"
        / "置換リスト_ルビ.json"
    )


def load_deployed_payloads() -> dict:
    return {
        language: json.loads(
            deployed_payload_path(language).read_text(encoding="utf-8")
        )
        for language in LANGUAGES
    }


def deployed_payload_compact_hashes() -> dict:
    """Re-read deployed JSON sequentially to avoid a second 3-file snapshot."""
    hashes = {}
    for language in LANGUAGES:
        payload = json.loads(
            deployed_payload_path(language).read_text(encoding="utf-8")
        )
        hashes[language] = compact_sha256(payload)
    return hashes


def deployed_app_fingerprints() -> dict:
    return {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in LANGUAGES
    }


def validate_deployed_payloads(
    mode: str, *, batch_size: int = 5, payload_loader=None,
    payload_hash_reader=None, fingerprint_reader=None,
) -> dict:
    """Bind rendered in-memory payloads back to the deployed files.

    ``validate_generated_payloads`` also licenses pre-write in-memory
    candidates, so it intentionally cannot assume that its payload object is
    the deployed JSON.  This wrapper is the deployed-only path used by the CLI
    and no-worsening sidecar: it reloads all three files after rendering and
    requires both semantic payload hashes and raw app fingerprints to match.
    """
    if payload_loader is None:
        payload_loader = load_deployed_payloads
    if payload_hash_reader is None:
        payload_hash_reader = deployed_payload_compact_hashes
    if fingerprint_reader is None:
        fingerprint_reader = deployed_app_fingerprints
    loaded = payload_loader()
    report = validate_generated_payloads(
        loaded, mode, batch_size=batch_size,
    )
    reloaded_hashes = payload_hash_reader()
    if set(reloaded_hashes) != set(LANGUAGES):
        raise ValueError("Phase 558 deployed payload reload scope drift")
    final_fingerprints = fingerprint_reader()
    if (
        reloaded_hashes != report["candidate_payload_sha256"]
        or final_fingerprints != report["app_input_fingerprints"]
    ):
        raise ValueError(
            "Phase 558 deployed payload changed across load/render/reload"
        )
    report["deployed_snapshot_revalidated"] = True
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--deployed", action="store_true", required=True)
    parser.add_argument("--batch-size", type=int, default=5)
    args = parser.parse_args(argv)
    report = validate_deployed_payloads(
        args.mode, batch_size=args.batch_size,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
