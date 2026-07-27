# -*- coding: utf-8 -*-
"""Runtime boundary, gloss, width, and non-leakage gate for Phase 598."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re

from gen_replacement import load_app_replacement_helper
import no_worsening_audit as audit
import phase598_technical_on_policy as policy
from phase598_technical_on_activation import activation_report


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("JA", "ZH", "KO")
PRODUCTIVE_VARIANT_ENDINGS = (
    "a", "aj", "ajn", "an", "e", "en", "o", "oj", "ojn", "on",
)
PRODUCTIVE_VARIANT_CASES = ("lower", "initial", "upper")
FRACTION_NUMERALS = ("du", "tri", "kvar", "ok")
BARE_HOMOGRAPH_STEMS = (
    "fonon", "foton", "ganglion", "magneton", "mezon", "nukleon",
    "termoelektron",
)
ADJACENT_TECHNICAL_GUARDS = (
    "antiprotono",
    "elektrona",
    "elektronkanono",
    "elektrono",
    "elektrontubo",
    "elektronvolto",
    "megaelektronvolto",
    "mezonteorio",
    "neŭtrono",
    "protono",
    "valentelektrono",
    "elektronmikroskopo",
    "fotonmikroskopo",
    "antineŭtrono",
)
EXACT_LEAKAGE_GUARDS = (
    "Gigaelektronvolto",
    "GIGAELEKTRONVOLTO",
    "gigaelektronvolton",
    "gigaelektronvoltoj",
)
POSITIVE_SURFACE_LIST_SHA256 = (
    "289C0895DBAEED670129A00B3C2439F53B763E68B95A3325D0B5BE4436631B8E"
)
NEGATIVE_SURFACE_LIST_SHA256 = (
    "365DBAD50E924D33CC284934EC5D3A4384EF49462A992AF9FCE52E59B8B731F3"
)
COMBINED_SURFACE_LIST_SHA256 = (
    "3D18DAA34939713729E689C92548FDF3A5DB0AE60351535AC198E502C39369BB"
)
POSITIVE_SIGNATURE_MANIFEST_SHA256 = (
    "2A8859471A3D0EB5DDCFA7A9B34D6337126DE963944FBF60E74025DD3BE365A7"
)
POSITIVE_GLOSS_MANIFEST_SHA256 = (
    "1CC87B852F236EFBE56AC8876B7EE6300EC67672CE9ED53B5EDD3D4516A4018F"
)
NEGATIVE_SIGNATURE_MANIFEST_SHA256 = (
    "A50E1C8C2DEF6D6EEC2DAD4AC6763F1C66934B53F19D37241BAF3E1A3BCF9D9C"
)
NEGATIVE_LOCALIZED_MANIFEST_SHA256 = {
    "JA": "27A81E2B61402972DCFC864A355BF1CFBB2859467B936F46FA66D72D22DC97C5",
    "ZH": "3C1E57263B6227742A9EF76E8E0B19BF90C06E3BDAD0814EEBC3FF9F639B19AF",
    "KO": "7686C694D87DE875B34A14519E68CAE0FCA93CFF00834A3D61482C089EBA323E",
}
CHAR_WIDTHS_SHA256 = (
    "AC009C26AF1D7FAE05E8969D86042B5BAFF5F482B226C575E1CEF8D27AEA2C7B"
)
CSS_CLASS_SCALE = {
    "XXXS_S": 0.3,
    "XXS_S": 0.3,
    "XS_S": 0.3,
    "S_S": 0.4,
    "M_M": 0.5,
    "L_L": 0.6,
    "XL_L": 0.7,
    "XXL_L": 0.8,
}
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


def _signature(target: str, typed_roles: str):
    pieces = [piece for piece in target.split("/") if piece]
    if (
        len(pieces) != len(typed_roles)
        or any(role not in "RL" for role in typed_roles)
    ):
        raise ValueError(f"invalid Phase 598 typed target: {target!r}")
    return audit.signature_from_typed_parts([
        (piece, role == "R")
        for piece, role in zip(pieces, typed_roles)
    ])


def _case_variant(
    stem: str, ending: str, case: str,
) -> tuple[str, str, str]:
    if case == "lower":
        rendered_stem, rendered_ending = stem, ending
    elif case == "initial":
        rendered_stem = stem[:1].upper() + stem[1:]
        rendered_ending = ending
    elif case == "upper":
        rendered_stem, rendered_ending = stem.upper(), ending.upper()
    else:
        raise ValueError(f"invalid Phase 598 case variant: {case!r}")
    return (
        rendered_stem + rendered_ending,
        f"{rendered_stem}/{rendered_ending}",
        rendered_stem,
    )


def positive_surface_list() -> list[str]:
    result = []
    for spec in policy.managed_morph_targets().values():
        stem = spec["target"].rsplit("/", 1)[0]
        for ending in PRODUCTIVE_VARIANT_ENDINGS:
            for case in PRODUCTIVE_VARIANT_CASES:
                result.append(_case_variant(stem, ending, case)[0])
    result.extend(policy.typed_exact_targets())
    if (
        len(result) != len(set(result))
        or len(result)
        != policy.EXPECTED_COUNTS["positive_surfaces_per_language"]
        or compact_sha256(result) != POSITIVE_SURFACE_LIST_SHA256
    ):
        raise ValueError("Phase 598 positive surface closure drift")
    return result


def negative_surface_groups() -> dict[str, list[str]]:
    fraction = [
        _case_variant(numeral + "on", ending, case)[0]
        for numeral in FRACTION_NUMERALS
        for ending in PRODUCTIVE_VARIANT_ENDINGS
        for case in PRODUCTIVE_VARIANT_CASES
    ]
    bare = [
        _case_variant(stem, "", case)[0]
        for stem in BARE_HOMOGRAPH_STEMS
        for case in PRODUCTIVE_VARIANT_CASES
    ]
    groups = {
        "genuine_fraction_guards": fraction,
        "bare_homograph_guards": bare,
        "adjacent_technical_guards": list(ADJACENT_TECHNICAL_GUARDS),
        "exact_leakage_guards": list(EXACT_LEAKAGE_GUARDS),
    }
    expected = policy.EXPECTED_COUNTS
    for name, surfaces in groups.items():
        if len(surfaces) != expected[name]:
            raise ValueError(f"Phase 598 {name} count drift")
    return groups


def negative_surface_list() -> list[str]:
    groups = negative_surface_groups()
    result = [
        surface
        for group in groups.values()
        for surface in group
    ]
    if (
        len(result) != len(set(result))
        or len(result) != policy.EXPECTED_COUNTS[
            "negative_surfaces_per_language"
        ]
        or compact_sha256(result) != NEGATIVE_SURFACE_LIST_SHA256
    ):
        raise ValueError("Phase 598 negative surface closure drift")
    return result


def combined_surface_list() -> list[str]:
    positive = positive_surface_list()
    negative = negative_surface_list()
    if set(positive) & set(negative):
        raise ValueError("Phase 598 positive/negative surface overlap")
    result = positive + negative
    if (
        len(result) != policy.EXPECTED_COUNTS[
            "combined_runtime_surfaces_per_language"
        ]
        or compact_sha256(result) != COMBINED_SURFACE_LIST_SHA256
    ):
        raise ValueError("Phase 598 combined runtime surface drift")
    return result


def positive_expected_signatures() -> tuple[dict, str]:
    result = {}
    for spec in policy.managed_morph_targets().values():
        stem = spec["target"].rsplit("/", 1)[0]
        for ending in PRODUCTIVE_VARIANT_ENDINGS:
            for case in PRODUCTIVE_VARIANT_CASES:
                surface, target, _rb = _case_variant(stem, ending, case)
                result[surface] = _signature(target, "RL")
    for surface, spec in policy.typed_exact_targets().items():
        result[surface] = _signature(spec["target"], spec["typed_roles"])
    if set(result) != set(positive_surface_list()):
        raise ValueError("Phase 598 positive signature surface drift")
    manifest = [{
        "surface": surface,
        "signature": audit.signature_payload(result[surface]),
    } for surface in sorted(result)]
    digest = compact_sha256(manifest)
    if digest != POSITIVE_SIGNATURE_MANIFEST_SHA256:
        raise ValueError("Phase 598 positive signature manifest drift")
    return result, digest


def positive_expected_annotations() -> tuple[dict, str]:
    expected = {language: {} for language in LANGUAGES}
    annotations = policy.morph_context_annotations()
    for spec in policy.managed_morph_targets().values():
        stem = spec["target"].rsplit("/", 1)[0]
        authority = annotations[spec["ruby_context_annotation"]]
        for ending in PRODUCTIVE_VARIANT_ENDINGS:
            for case in PRODUCTIVE_VARIANT_CASES:
                surface, _target, rb = _case_variant(stem, ending, case)
                for language in LANGUAGES:
                    expected[language][surface] = [{
                        "rb": rb,
                        "rt": authority["glosses"][language.lower()],
                    }]
    typed_glosses = policy.typed_context_glosses()
    used_typed = set()
    for surface, spec in policy.typed_exact_targets().items():
        pieces = [piece for piece in spec["target"].split("/") if piece]
        for language in LANGUAGES:
            expected[language][surface] = []
        for index, (piece, role) in enumerate(
            zip(pieces, spec["typed_roles"])
        ):
            if role != "R":
                continue
            key = (surface, index, piece)
            glosses = typed_glosses.get(key)
            if glosses is None:
                raise ValueError(
                    f"Phase 598 missing typed gloss authority: {key!r}"
                )
            used_typed.add(key)
            for language in LANGUAGES:
                expected[language][surface].append({
                    "rb": piece,
                    "rt": glosses[language.lower()],
                })
    if used_typed != set(typed_glosses):
        raise ValueError("Phase 598 unused typed gloss authority")
    positive = set(positive_surface_list())
    if any(set(expected[language]) != positive for language in LANGUAGES):
        raise ValueError("Phase 598 positive gloss surface drift")
    manifest = [{
        "language": language,
        "surface": surface,
        "annotations": expected[language][surface],
    } for language in LANGUAGES for surface in sorted(positive)]
    digest = compact_sha256(manifest)
    if digest != POSITIVE_GLOSS_MANIFEST_SHA256:
        raise ValueError("Phase 598 positive gloss manifest drift")
    return expected, digest


def _normalize_signature(signature):
    if not isinstance(signature, (tuple, list)) or len(signature) != 2:
        raise ValueError(f"invalid Phase 598 signature: {signature!r}")
    reconstruction, spans = signature
    if (
        not isinstance(reconstruction, str)
        or not isinstance(spans, (tuple, list))
        or any(
            not isinstance(row, (tuple, list))
            or len(row) != 2
            or not isinstance(row[0], str)
            or not isinstance(row[1], bool)
            for row in spans
        )
    ):
        raise ValueError(f"invalid Phase 598 signature span: {signature!r}")
    return (
        policy.phase532.canonical(reconstruction),
        tuple(
            (policy.phase532.canonical(text), is_ruby)
            for text, is_ruby in spans
        ),
    )


def _normalize_annotations(value) -> list[dict[str, str]]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"invalid Phase 598 annotations: {value!r}")
    result = []
    for row in value:
        if (
            not isinstance(row, dict)
            or set(row) != {"rb", "rt"}
            or not isinstance(row["rb"], str)
            or not isinstance(row["rt"], str)
        ):
            raise ValueError(f"invalid Phase 598 annotation: {row!r}")
        result.append({
            "rb": policy.phase532.canonical(row["rb"]),
            "rt": row["rt"],
        })
    return result


def validate_rendered_results(results_by_language: dict) -> dict:
    if set(results_by_language) != set(LANGUAGES):
        raise ValueError("Phase 598 runtime languages must be exactly JA/ZH/KO")
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
                f"Phase 598 {language} runtime surface scope drift"
            )
        for surface, row in rows.items():
            if not isinstance(row, dict):
                raise ValueError(
                    f"Phase 598 {language} runtime row drift: {surface!r}"
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
            "Phase 598 positive runtime gate failed: "
            f"mismatches={positive_mismatches!r}, "
            f"trilingual={positive_trilingual!r}"
        )

    negative_signature_manifests = {}
    negative_localized_manifests = {}
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
    if (
        set(negative_signature_manifests.values())
        != {NEGATIVE_SIGNATURE_MANIFEST_SHA256}
        or negative_localized_manifests
        != NEGATIVE_LOCALIZED_MANIFEST_SHA256
        or negative_trilingual
    ):
        raise ValueError(
            "Phase 598 negative/non-leakage gate failed: "
            f"signature={negative_signature_manifests!r}, "
            f"localized={negative_localized_manifests!r}, "
            f"trilingual={negative_trilingual!r}"
        )

    annotation_counts = {
        language: sum(
            len(normalized[language][surface]["annotations"])
            for surface in positive
        )
        for language in LANGUAGES
    }
    if set(annotation_counts.values()) != {213}:
        raise ValueError(
            f"Phase 598 positive annotation count drift: {annotation_counts!r}"
        )
    return {
        "phase": policy.PHASE,
        "languages": list(LANGUAGES),
        "positive_surfaces": len(positive),
        "positive_annotations_per_language": annotation_counts,
        "negative_surfaces": len(negatives),
        "combined_surfaces": len(expected_surfaces),
        "positive_signature_manifest_sha256": (
            positive_signature_sha256
        ),
        "positive_gloss_manifest_sha256": positive_gloss_sha256,
        "negative_signature_manifest_sha256": (
            NEGATIVE_SIGNATURE_MANIFEST_SHA256
        ),
        "negative_localized_manifest_sha256": (
            negative_localized_manifests
        ),
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
                    f"Phase 598 {language} candidate rule-list drift"
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
            f"Phase 598 positive payload closure failed: {mismatches!r}"
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
            f"Phase 598 width table lacks characters: {sorted(set(missing))!r}"
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
            raise ValueError(f"Phase 598 {language} char-width identity drift")
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
            raise ValueError(f"Phase 598 {language} CSS scale mapping drift")
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
                        f"Phase 598 formatter omitted rt class: {rendered!r}"
                    )
                class_name = match.group("class").upper()
                if class_name not in observed_scale:
                    raise ValueError(
                        f"Phase 598 unknown rt class: {class_name!r}"
                    )
                if BR_RE.search(match.group("rt")):
                    raise ValueError(
                        f"Phase 598 unexpected automatic rt break: {surface!r}"
                    )
                visible_rt = html.unescape(
                    TAG_RE.sub("", match.group("rt"))
                )
                rb_width = _width(rb, widths)
                if rb_width <= 0:
                    raise ValueError(f"Phase 598 zero rb width: {rb!r}")
                ratio = (
                    _width(visible_rt, widths)
                    * observed_scale[class_name]
                    / rb_width
                )
                maximum = max(maximum, ratio)
                rendered_count += 1
        maxima[language] = maximum
    if any(value > 2.0 for value in maxima.values()):
        raise ValueError(f"Phase 598 effective Ruby width exceeds 2x: {maxima!r}")
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
        raise ValueError(f"Phase 598 {language} candidate payload schema drift")
    if any(not isinstance(rows, list) for rows in audit.extract_lists(payload)):
        raise ValueError(f"Phase 598 {language} candidate rule-list drift")


def validate_generated_payloads(
    payloads_by_language: dict, *, batch_size: int = 20,
) -> dict:
    if set(payloads_by_language) != set(LANGUAGES):
        raise ValueError("Phase 598 payloads must be exactly JA/ZH/KO")
    if not isinstance(batch_size, int) or not 1 <= batch_size <= 50:
        raise ValueError("Phase 598 runtime batch size must be in 1..50")
    activation = activation_report()
    if not activation.get("phase598_technical_on_active"):
        raise ValueError("Phase 598 runtime gate lacks formal activation")
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
            app_dir, f"phase598_technical_on_{language}",
        )
        overlay = audit.overlay_module(
            app_dir, f"phase598_technical_on_overlay_{language}",
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
        raise ValueError("Phase 598 runtime gate input changed during rendering")
    report.update({
        "candidate_payload_sha256": payload_hashes_before,
        "app_input_fingerprints": fingerprints_before,
        "phase598_review": review_before,
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
            "Phase 598 deployed payload changed across load/render/reload"
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
