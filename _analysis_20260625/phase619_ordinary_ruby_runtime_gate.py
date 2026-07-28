# -*- coding: utf-8 -*-
"""Runtime boundary, gloss, width, and non-leakage gate for Phase 619."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re

from gen_replacement import load_app_replacement_helper
import no_worsening_audit as audit
import phase598_technical_on_runtime_gate as parent_runtime
import phase619_ordinary_ruby_policy as policy
from phase619_ordinary_ruby_activation import activation_report


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("JA", "ZH", "KO")
PRODUCTIVE_VARIANT_ENDINGS = (
    "a", "aj", "ajn", "an", "e", "en", "o", "oj", "ojn", "on",
)
PRODUCTIVE_VARIANT_CASES = ("lower", "initial", "upper")
ADJACENT_ORDINARY_GUARDS = (
    "imperialismo",
    "imperiala",
    "imperiisto",
    "provincismo",
    "provincialo",
    "provinciala",
    "endoskopo",
    "endoskopa",
    "videoendoskopio",
    "mikroskopo",
    "mikroskopa",
    "lummikroskopo",
    "elektronmikroskopo",
    "fotonmikroskopo",
    "ultramikroskopo",
    "mukozo",
    "mukozito",
    "ditionito",
    "politionato",
    "tritionato",
    "tetrationito",
    "tetrafluorido",
)
DERIVATIONAL_LEAKAGE_GUARDS = (
    "imperialistino",
    "provincialismulo",
    "endoskopiisto",
    "mikroskopiisto",
    "mukozaĵeto",
    "ditionataĵo",
    "tetrationataĵo",
)
POSITIVE_SURFACE_LIST_SHA256 = (
    "B946BF90DCB39EFEBAE05C8A6BAD07D8D76E755081646AD2135D684DD2153909"
)
NEGATIVE_SURFACE_LIST_SHA256 = (
    "DF28A20D56BAE71F1FBB905F5EC1DB5DF57C49C76E375F644940243B3B86820E"
)
COMBINED_SURFACE_LIST_SHA256 = (
    "52E85BE429ED3A2AA7B739BCAC05FECBDAD1861766BC9D17D5FAC65D493D6DFE"
)
POSITIVE_SIGNATURE_MANIFEST_SHA256 = (
    "AFFD05A9B401A77B1C06BF3696E9312F48B1E83F6F8414F87E8B1A6C3FB106F7"
)
POSITIVE_GLOSS_MANIFEST_SHA256 = (
    "6D94A8C7E0C881DDBF8F8F382FD40DB2EFD86C53BB292CB652C27BA747BC9778"
)
CHAR_WIDTHS_SHA256 = (
    "AC009C26AF1D7FAE05E8969D86042B5BAFF5F482B226C575E1CEF8D27AEA2C7B"
)
CSS_CLASS_SCALE = parent_runtime.CSS_CLASS_SCALE
RT_RE = re.compile(
    r"<rt\b[^>]*\bclass=['\"](?P<class>[A-Z_]+)['\"][^>]*>"
    r"(?P<rt>.*?)</rt>",
    re.IGNORECASE | re.DOTALL,
)
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def _case_variant(
    pieces: tuple[str, ...], ending: str, case: str,
) -> tuple[str, tuple[str, ...], str]:
    if case == "lower":
        rendered_pieces = pieces
        rendered_ending = ending
    elif case == "initial":
        rendered_pieces = (
            pieces[0][:1].upper() + pieces[0][1:],
            *pieces[1:],
        )
        rendered_ending = ending
    elif case == "upper":
        rendered_pieces = tuple(piece.upper() for piece in pieces)
        rendered_ending = ending.upper()
    else:
        raise ValueError(f"invalid Phase 619 case variant: {case!r}")
    return (
        "".join(rendered_pieces) + rendered_ending,
        tuple(rendered_pieces),
        rendered_ending,
    )


def _target_pieces(spec: dict) -> tuple[str, ...]:
    target = spec["target"]
    pieces = tuple(piece for piece in target.rsplit("/", 1)[0].split("/")
                   if piece)
    if not pieces:
        raise ValueError(f"invalid Phase 619 target: {target!r}")
    return pieces


def _positive_surface_list_unchecked() -> list[str]:
    result = []
    for spec in policy.managed_morph_targets().values():
        pieces = _target_pieces(spec)
        for ending in PRODUCTIVE_VARIANT_ENDINGS:
            for case in PRODUCTIVE_VARIANT_CASES:
                result.append(_case_variant(pieces, ending, case)[0])
    return result


def positive_surface_list() -> list[str]:
    result = _positive_surface_list_unchecked()
    if (
        len(result) != len(set(result))
        or len(result)
        != policy.EXPECTED_COUNTS["runtime_positive_surfaces_per_language"]
        or compact_sha256(result) != POSITIVE_SURFACE_LIST_SHA256
    ):
        raise ValueError("Phase 619 positive surface closure drift")
    return result


def negative_surface_groups() -> dict[str, list[str]]:
    lemmas = list(policy.managed_morph_targets())
    bare_stems = [
        _case_variant(_target_pieces(spec), "", case)[0]
        for spec in policy.managed_morph_targets().values()
        for case in PRODUCTIVE_VARIANT_CASES
    ]
    groups = {
        "bare_stem_guards": bare_stems,
        "left_boundary_guards": [f"x{lemma}" for lemma in lemmas],
        "right_boundary_guards": [f"{lemma}x" for lemma in lemmas],
        "derivational_leakage_guards": list(
            DERIVATIONAL_LEAKAGE_GUARDS
        ),
        "adjacent_ordinary_guards": list(ADJACENT_ORDINARY_GUARDS),
    }
    if {name: len(rows) for name, rows in groups.items()} != {
        "bare_stem_guards": 21,
        "left_boundary_guards": 7,
        "right_boundary_guards": 7,
        "derivational_leakage_guards": 7,
        "adjacent_ordinary_guards": 22,
    }:
        raise ValueError("Phase 619 negative group count drift")
    return groups


def _negative_surface_list_unchecked() -> list[str]:
    return [
        surface
        for group in negative_surface_groups().values()
        for surface in group
    ]


def negative_surface_list() -> list[str]:
    result = _negative_surface_list_unchecked()
    if (
        len(result) != len(set(result))
        or len(result) != 64
        or compact_sha256(result) != NEGATIVE_SURFACE_LIST_SHA256
    ):
        raise ValueError("Phase 619 negative surface closure drift")
    return result


def combined_surface_list() -> list[str]:
    positive = positive_surface_list()
    negative = negative_surface_list()
    if set(positive) & set(negative):
        raise ValueError("Phase 619 positive/negative surface overlap")
    result = positive + negative
    if (
        len(result) != 274
        or compact_sha256(result) != COMBINED_SURFACE_LIST_SHA256
    ):
        raise ValueError("Phase 619 combined runtime surface drift")
    return result


def _positive_expected_signatures_unchecked() -> dict:
    result = {}
    for spec in policy.managed_morph_targets().values():
        pieces = _target_pieces(spec)
        for ending in PRODUCTIVE_VARIANT_ENDINGS:
            for case in PRODUCTIVE_VARIANT_CASES:
                surface, rendered_pieces, rendered_ending = _case_variant(
                    pieces, ending, case,
                )
                result[surface] = audit.signature_from_typed_parts([
                    *((piece, True) for piece in rendered_pieces),
                    (rendered_ending, False),
                ])
    return result


def positive_expected_signatures() -> tuple[dict, str]:
    result = _positive_expected_signatures_unchecked()
    if set(result) != set(positive_surface_list()):
        raise ValueError("Phase 619 positive signature surface drift")
    manifest = [{
        "surface": surface,
        "signature": audit.signature_payload(result[surface]),
    } for surface in sorted(result)]
    digest = compact_sha256(manifest)
    if digest != POSITIVE_SIGNATURE_MANIFEST_SHA256:
        raise ValueError("Phase 619 positive signature manifest drift")
    return result, digest


def _positive_expected_annotations_unchecked() -> dict:
    expected = {language: {} for language in LANGUAGES}
    atomic = policy.morph_context_annotations()
    split = policy.split_context_annotations()
    for spec in policy.managed_morph_targets().values():
        pieces = _target_pieces(spec)
        if "ruby_context_annotation" in spec:
            authorities = [atomic[spec["ruby_context_annotation"]]]
        else:
            authorities = split["/".join(pieces)]
        if tuple(row["piece"] for row in authorities) != pieces:
            raise ValueError("Phase 619 annotation piece closure drift")
        for ending in PRODUCTIVE_VARIANT_ENDINGS:
            for case in PRODUCTIVE_VARIANT_CASES:
                surface, rendered_pieces, _rendered_ending = _case_variant(
                    pieces, ending, case,
                )
                for language in LANGUAGES:
                    expected[language][surface] = [
                        {
                            "rb": rendered_piece,
                            "rt": authority["glosses"][language.lower()],
                        }
                        for rendered_piece, authority in zip(
                            rendered_pieces, authorities,
                        )
                    ]
    return expected


def positive_expected_annotations() -> tuple[dict, str]:
    expected = _positive_expected_annotations_unchecked()
    positive = set(positive_surface_list())
    if any(set(expected[language]) != positive for language in LANGUAGES):
        raise ValueError("Phase 619 positive gloss surface drift")
    manifest = [{
        "language": language,
        "surface": surface,
        "annotations": expected[language][surface],
    } for language in LANGUAGES for surface in sorted(positive)]
    digest = compact_sha256(manifest)
    if digest != POSITIVE_GLOSS_MANIFEST_SHA256:
        raise ValueError("Phase 619 positive gloss manifest drift")
    return expected, digest


def forbidden_negative_annotation_sequences(language: str) -> list[tuple]:
    """Return only this sidecar's annotation signatures.

    Negative words are deliberately *not* frozen to their current parse or
    gloss.  Some adjacent technical words still merit future correction.
    This gate rejects leakage of the Phase 619 sidecar while allowing those
    unrelated words to improve independently.
    """
    if language not in LANGUAGES:
        raise ValueError(f"invalid Phase 619 language: {language!r}")
    result = []
    atomic = policy.morph_context_annotations()
    split = policy.split_context_annotations()
    for spec in policy.managed_morph_targets().values():
        pieces = _target_pieces(spec)
        if "ruby_context_annotation" in spec:
            authorities = [atomic[spec["ruby_context_annotation"]]]
        else:
            authorities = split["/".join(pieces)]
        result.append(tuple(
            (
                policy.phase532.canonical(piece).lower(),
                authority["glosses"][language.lower()],
            )
            for piece, authority in zip(pieces, authorities)
        ))
    if len(result) != 7 or len(result) != len(set(result)):
        raise ValueError("Phase 619 forbidden annotation closure drift")
    return result


def _normalize_signature(signature):
    return parent_runtime._normalize_signature(signature)


def _normalize_annotations(value):
    return parent_runtime._normalize_annotations(value)


def validate_rendered_results(results_by_language: dict) -> dict:
    if set(results_by_language) != set(LANGUAGES):
        raise ValueError("Phase 619 runtime languages must be exactly JA/ZH/KO")
    positive, positive_signature_sha256 = positive_expected_signatures()
    expected_annotations, positive_gloss_sha256 = (
        positive_expected_annotations()
    )
    negatives = negative_surface_list()
    expected_surfaces = set(positive) | set(negatives)
    normalized = {language: {} for language in LANGUAGES}
    for language in LANGUAGES:
        rows = results_by_language[language]
        if not isinstance(rows, dict) or set(rows) != expected_surfaces:
            raise ValueError(
                f"Phase 619 {language} runtime surface scope drift"
            )
        for surface, row in rows.items():
            if not isinstance(row, dict):
                raise ValueError(
                    f"Phase 619 {language} runtime row drift: {surface!r}"
                )
            normalized[language][surface] = {
                "signature": _normalize_signature(row.get("signature")),
                "annotations": _normalize_annotations(
                    row.get("annotations")
                ),
            }

    positive_mismatches = {language: [] for language in LANGUAGES}
    for language in LANGUAGES:
        for surface in positive:
            row = normalized[language][surface]
            if (
                row["signature"] != positive[surface]
                or row["annotations"]
                != expected_annotations[language][surface]
            ):
                positive_mismatches[language].append(surface)
    positive_trilingual = [
        surface for surface in sorted(positive)
        if len({
            normalized[language][surface]["signature"]
            for language in LANGUAGES
        }) != 1
        or len({
            tuple(
                annotation["rb"]
                for annotation in normalized[language][surface]["annotations"]
            )
            for language in LANGUAGES
        }) != 1
    ]
    if any(positive_mismatches.values()) or positive_trilingual:
        raise ValueError(
            "Phase 619 positive runtime gate failed: "
            f"mismatches={positive_mismatches!r}, "
            f"trilingual={positive_trilingual!r}"
        )

    negative_signature_manifests = {}
    negative_localized_manifests = {}
    negative_leakage = {language: [] for language in LANGUAGES}
    for language in LANGUAGES:
        signature_manifest = [{
            "surface": surface,
            "signature": audit.signature_payload(
                normalized[language][surface]["signature"]
            ),
        } for surface in sorted(negatives)]
        localized_manifest = [{
            "surface": surface,
            "signature": audit.signature_payload(
                normalized[language][surface]["signature"]
            ),
            "annotations": normalized[language][surface]["annotations"],
        } for surface in sorted(negatives)]
        negative_signature_manifests[language] = compact_sha256(
            signature_manifest
        )
        negative_localized_manifests[language] = compact_sha256(
            localized_manifest
        )
        forbidden = forbidden_negative_annotation_sequences(language)
        for surface in negatives:
            annotations = tuple(
                (
                    policy.phase532.canonical(row["rb"]).lower(),
                    row["rt"],
                )
                for row in normalized[language][surface]["annotations"]
            )
            if any(
                annotations[index:index + len(sequence)] == sequence
                for sequence in forbidden
                for index in range(len(annotations) - len(sequence) + 1)
            ):
                negative_leakage[language].append(surface)
    negative_trilingual = [
        surface for surface in sorted(negatives)
        if len({
            normalized[language][surface]["signature"]
            for language in LANGUAGES
        }) != 1
        or len({
            tuple(
                annotation["rb"]
                for annotation in normalized[language][surface]["annotations"]
            )
            for language in LANGUAGES
        }) != 1
    ]
    if negative_trilingual or any(negative_leakage.values()):
        raise ValueError(
            "Phase 619 negative/non-leakage gate failed: "
            f"leakage={negative_leakage!r}, "
            f"trilingual={negative_trilingual!r}, "
            f"diagnostic_signature={negative_signature_manifests!r}, "
            f"diagnostic_localized={negative_localized_manifests!r}"
        )

    annotation_counts = {
        language: sum(
            len(normalized[language][surface]["annotations"])
            for surface in positive
        )
        for language in LANGUAGES
    }
    if set(annotation_counts.values()) != {240}:
        raise ValueError(
            f"Phase 619 positive annotation count drift: "
            f"{annotation_counts!r}"
        )
    return {
        "phase": policy.PHASE_TO,
        "languages": list(LANGUAGES),
        "positive_surfaces": len(positive),
        "positive_annotations_per_language": annotation_counts,
        "negative_surfaces": len(negatives),
        "combined_surfaces": len(expected_surfaces),
        "positive_signature_manifest_sha256": (
            positive_signature_sha256
        ),
        "positive_gloss_manifest_sha256": positive_gloss_sha256,
        "negative_signature_manifest_sha256": negative_signature_manifests,
        "negative_localized_manifest_sha256": negative_localized_manifests,
        "negative_sidecar_leakage": negative_leakage,
        "negative_parse_or_gloss_frozen": False,
        "trilingual_boundary_mismatches": 0,
        "trilingual_rb_mismatches": 0,
        "gate": True,
    }


def validate_positive_payload_closure(payloads_by_language: dict) -> dict:
    expected, _digest = positive_expected_signatures()
    mismatches = {}
    for language in LANGUAGES:
        payload = payloads_by_language[language]
        rows_by_surface = {surface: [] for surface in expected}
        for rules in audit.extract_lists(payload):
            if not isinstance(rules, list):
                raise ValueError(
                    f"Phase 619 {language} candidate rule-list drift"
                )
            for row in rules:
                if (
                    isinstance(row, (list, tuple))
                    and len(row) >= 2
                    and isinstance(row[0], str)
                    and row[0].strip() in rows_by_surface
                ):
                    rows_by_surface[row[0].strip()].append(row)
        mismatches[language] = []
        for surface, matches in rows_by_surface.items():
            if (
                len(matches) != 1
                or matches[0][0] != f" {surface} "
                or not isinstance(matches[0][1], str)
                or _normalize_signature(audit.signature_from_typed_parts(
                    audit.rendered_typed_parts(matches[0][1])
                )) != expected[surface]
            ):
                mismatches[language].append(surface)
    if any(mismatches.values()):
        raise ValueError(
            f"Phase 619 positive payload closure failed: {mismatches!r}"
        )
    return {
        "positive_payload_rows_per_language": {
            language: len(expected) for language in LANGUAGES
        },
        "positive_payload_duplicates": 0,
        "positive_payload_gate": True,
    }


def _width(text: str, widths: dict) -> float:
    missing = [character for character in text if character not in widths]
    if missing:
        raise ValueError(
            f"Phase 619 width table lacks characters: "
            f"{sorted(set(missing))!r}"
        )
    return sum(float(widths[character]) for character in text)


def validate_expected_widths() -> dict:
    expected, _digest = positive_expected_annotations()
    maxima = {}
    rendered_count = 0
    for language in LANGUAGES:
        app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
        helper = load_app_replacement_helper(app_dir)
        width_path = app_dir / "app_data" / "char_widths.json"
        if hashlib.sha256(width_path.read_bytes()).hexdigest().upper() != (
            CHAR_WIDTHS_SHA256
        ):
            raise ValueError(f"Phase 619 {language} char-width identity drift")
        widths = json.loads(width_path.read_text(encoding="utf-8"))
        css_text = (app_dir / "esp_text_replacement_module.py").read_text(
            encoding="utf-8"
        )
        observed_scale = {
            name: float(scale)
            for name, scale in re.findall(
                r"rt\.([A-Z_]+)\s*\{[^}]*?--ruby-font-size\s*:\s*"
                r"([0-9.]+)em",
                css_text, re.DOTALL,
            )
        }
        if observed_scale != CSS_CLASS_SCALE:
            raise ValueError(f"Phase 619 {language} CSS scale mapping drift")
        maximum = 0.0
        for surface in sorted(expected[language]):
            for annotation in expected[language][surface]:
                rb, rt = annotation["rb"], annotation["rt"]
                rendered = helper.output_format(
                    rb, rt, audit.FORMAT, widths,
                )
                match = RT_RE.search(rendered)
                if match is None:
                    raise ValueError(
                        f"Phase 619 formatter omitted rt class: {rendered!r}"
                    )
                class_name = match.group("class").upper()
                if class_name not in observed_scale:
                    raise ValueError(
                        f"Phase 619 unknown rt class: {class_name!r}"
                    )
                if BR_RE.search(match.group("rt")):
                    raise ValueError(
                        f"Phase 619 unexpected automatic rt break: "
                        f"{surface!r}"
                    )
                visible_rt = html.unescape(TAG_RE.sub("", match.group("rt")))
                rb_width = _width(rb, widths)
                if rb_width <= 0:
                    raise ValueError(f"Phase 619 zero rb width: {rb!r}")
                ratio = (
                    _width(visible_rt, widths)
                    * observed_scale[class_name]
                    / rb_width
                )
                maximum = max(maximum, ratio)
                rendered_count += 1
        maxima[language] = maximum
    if any(value > 2.0 for value in maxima.values()):
        raise ValueError(
            f"Phase 619 effective Ruby width exceeds 2x: {maxima!r}"
        )
    return {
        "char_widths_sha256": CHAR_WIDTHS_SHA256,
        "expected_ruby_annotations_rendered": rendered_count,
        "unknown_width_characters": 0,
        "automatic_br_count": 0,
        "max_effective_width_ratio": maxima,
        "effective_ruby_width_within_2x": True,
        "width_gate": True,
    }


def _validate_payload_shape(payload, language: str) -> None:
    if not isinstance(payload, dict) or len(payload) != 3:
        raise ValueError(f"Phase 619 {language} candidate payload schema drift")
    if any(not isinstance(rows, list) for rows in audit.extract_lists(payload)):
        raise ValueError(f"Phase 619 {language} candidate rule-list drift")


def validate_generated_payloads(
    payloads_by_language: dict, *, batch_size: int = 20,
) -> dict:
    if set(payloads_by_language) != set(LANGUAGES):
        raise ValueError("Phase 619 payloads must be exactly JA/ZH/KO")
    if not isinstance(batch_size, int) or not 1 <= batch_size <= 50:
        raise ValueError("Phase 619 runtime batch size must be in 1..50")
    activation = activation_report()
    if not activation.get("phase619_ordinary_ruby_active"):
        raise ValueError("Phase 619 runtime gate lacks formal activation")
    surfaces = combined_surface_list()
    review_before = policy.review_identity()
    payload_hashes_before = {}
    fingerprints_before = {}
    rendered = {}
    for language in LANGUAGES:
        payload = payloads_by_language[language]
        _validate_payload_shape(payload, language)
        payload_hashes_before[language] = compact_sha256(payload)
        app_dir = ROOT / f"Esperanto-Kanji-Ruby-{language}"
        fingerprints_before[language] = audit.current_app_fingerprint(app_dir)
        load_app_replacement_helper(app_dir)
        runtime = audit.runtime_module(
            app_dir, f"phase619_ordinary_ruby_{language}",
        )
        overlay = audit.overlay_module(
            app_dir, f"phase619_ordinary_ruby_overlay_{language}",
        )
        corrections = json.loads(
            (app_dir / "app_data" / "user_corrections.json").read_text(
                encoding="utf-8"
            )
        )
        rendered[language] = audit.render_signatures(
            runtime, app_dir, payload, surfaces, batch_size,
            overlay=overlay, corrections=corrections,
            include_annotations=True,
        )
    report = validate_rendered_results(rendered)
    report.update(validate_positive_payload_closure(payloads_by_language))
    report.update(validate_expected_widths())
    payload_hashes_after = {
        language: compact_sha256(payloads_by_language[language])
        for language in LANGUAGES
    }
    fingerprints_after = {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in LANGUAGES
    }
    if (
        payload_hashes_after != payload_hashes_before
        or fingerprints_after != fingerprints_before
        or policy.review_identity() != review_before
    ):
        raise ValueError("Phase 619 runtime gate input changed during rendering")
    report.update({
        "candidate_payload_sha256": payload_hashes_before,
        "app_input_fingerprints": fingerprints_before,
        "phase619_review": review_before,
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


def deployed_payload_hashes() -> dict:
    return {
        language: compact_sha256(json.loads(
            deployed_payload_path(language).read_text(encoding="utf-8")
        ))
        for language in LANGUAGES
    }


def deployed_app_fingerprints() -> dict:
    return {
        language: audit.current_app_fingerprint(
            ROOT / f"Esperanto-Kanji-Ruby-{language}"
        )
        for language in LANGUAGES
    }


def validate_deployed_payloads(
    *, batch_size: int = 20, payload_loader=None,
    payload_hash_reader=None, fingerprint_reader=None,
) -> dict:
    payload_loader = payload_loader or load_deployed_payloads
    payload_hash_reader = payload_hash_reader or deployed_payload_hashes
    fingerprint_reader = fingerprint_reader or deployed_app_fingerprints
    loaded = payload_loader()
    report = validate_generated_payloads(loaded, batch_size=batch_size)
    if (
        payload_hash_reader() != report["candidate_payload_sha256"]
        or fingerprint_reader() != report["app_input_fingerprints"]
    ):
        raise ValueError(
            "Phase 619 deployed payload changed across load/render/reload"
        )
    report["deployed_snapshot_revalidated"] = True
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployed", action="store_true", required=True)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args(argv)
    report = validate_deployed_payloads(batch_size=args.batch_size)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
