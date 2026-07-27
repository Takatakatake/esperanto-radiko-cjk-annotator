# -*- coding: utf-8 -*-
"""Read-only deployed precondition and in-memory candidate gate for Phase 599.

Nothing in this module writes a payload or hooks the generator.  The optional
candidate path prepends five exact long-phrase rows to a shallow in-memory
copy of each deployed Ruby payload, renders both sides through the current app
runtime, and then discards the copy.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import html
import json
from pathlib import Path
import re

from gen_replacement import load_app_replacement_helper
import no_worsening_audit as audit
import phase599_temis_context_policy as policy


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = policy.LANGUAGES
RUBY_FILENAME = "置換リスト_ルビ.json"
KANJI_FILENAMES = {
    "JA": (
        "分解設定.json",
        "置換リスト_漢字.json",
        "置換リスト_漢字_純粋置換.json",
    ),
    "ZH": ("分解設定.json", "置換リスト_漢字.json"),
    "KO": ("分解設定.json", "置換リスト_漢字.json"),
}
RUNTIME_INPUT_FILES = (
    "main.py",
    "esp_text_replacement_module.py",
    "esp_overlay_module.py",
    "esp_replacement_json_make_module.py",
    "app_data/placeholders_skip.txt",
    "app_data/placeholders_localcapture.txt",
    "app_data/char_widths.json",
    "app_data/user_corrections.json",
    f"app_data/{RUBY_FILENAME}",
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
PLACEHOLDER_PREFIX = "$599599599"
LANGUAGE_PLACEHOLDER_DIGIT = {"JA": "1", "ZH": "2", "KO": "3"}
RT_RE = re.compile(
    r"<rt\b[^>]*\bclass=['\"](?P<class>[A-Z_]+)['\"][^>]*>"
    r"(?P<rt>.*?)</rt>",
    re.IGNORECASE | re.DOTALL,
)
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def app_dir(language: str) -> Path:
    if language not in LANGUAGES:
        raise ValueError(f"Phase 599 unsupported language: {language!r}")
    return ROOT / f"Esperanto-Kanji-Ruby-{language}"


def deployed_payload_path(language: str) -> Path:
    return app_dir(language) / "app_data" / RUBY_FILENAME


def runtime_input_fingerprint(language: str) -> dict[str, str]:
    base = app_dir(language)
    result = {}
    for relative in RUNTIME_INPUT_FILES:
        path = base / Path(relative)
        if not path.is_file():
            raise ValueError(
                f"Phase 599 missing runtime input: "
                f"{path.relative_to(ROOT).as_posix()}"
            )
        result[path.relative_to(ROOT).as_posix()] = file_sha256(path)
    return result


def kanji_track_fingerprint() -> dict[str, str]:
    result = {}
    for language in LANGUAGES:
        for filename in KANJI_FILENAMES[language]:
            path = app_dir(language) / "app_data" / filename
            if not path.is_file():
                raise ValueError(
                    f"Phase 599 missing Kanji-track input: "
                    f"{path.relative_to(ROOT).as_posix()}"
                )
            result[path.relative_to(ROOT).as_posix()] = file_sha256(path)
    return result


def _rule_keys(payload: dict) -> tuple[str, str, str]:
    if not isinstance(payload, dict) or len(payload) != 3:
        raise ValueError("Phase 599 Ruby payload schema drift")

    def unique(fragment: str) -> str:
        keys = [key for key in payload if fragment in key]
        if len(keys) != 1 or not isinstance(payload[keys[0]], list):
            raise ValueError(
                f"Phase 599 Ruby rule-list key drift: {fragment!r}"
            )
        return keys[0]

    local_key = unique("localized_string")
    global_key = unique("replacements_final_list")
    two_char_key = unique("replacements_list_for_2char")
    if len({local_key, global_key, two_char_key}) != 3:
        raise ValueError("Phase 599 Ruby rule-list keys overlap")
    return local_key, global_key, two_char_key


def _validate_rule_row(row, *, context: str) -> None:
    if (
        not isinstance(row, (list, tuple))
        or len(row) < 3
        or not all(isinstance(value, str) for value in row[:3])
        or not row[0]
        or not row[2]
    ):
        raise ValueError(f"Phase 599 invalid replacement row: {context}")


def validate_deployed_candidate_absent(payload: dict) -> dict:
    """Require all five rows and Phase-599 placeholders to be undeployed."""
    target_sources = {f" {phrase} " for phrase in policy.positive_phrases()}
    found_sources = []
    found_placeholders = []
    scanned = 0
    for key in _rule_keys(payload):
        for index, row in enumerate(payload[key]):
            _validate_rule_row(row, context=f"{key}[{index}]")
            scanned += 1
            if row[0] in target_sources:
                found_sources.append(row[0])
            if PLACEHOLDER_PREFIX in row[2]:
                found_placeholders.append(row[2])
    if found_sources or found_placeholders:
        raise ValueError(
            "Phase 599 candidate is already present in deployed payload: "
            f"sources={found_sources!r}, placeholders={found_placeholders!r}"
        )
    return {
        "deployed_candidate_rows": 0,
        "deployed_candidate_placeholders": 0,
        "deployed_rules_scanned": scanned,
        "candidate_activation_not_redundant": True,
    }


def _render_target_phrase(
    entry: dict, language: str, output_format, char_widths: dict,
) -> str:
    annotations = policy.expected_candidate_annotations()[language][
        entry["phrase"]
    ]
    annotation_index = 0
    rendered = []
    for part in entry["target_typed_parts"]:
        text = part["text"]
        if not part["ruby"]:
            rendered.append(text)
            continue
        if annotation_index >= len(annotations):
            raise ValueError(
                f"Phase 599 annotation underflow: {entry['phrase']!r}"
            )
        annotation = annotations[annotation_index]
        if annotation["rb"] != text:
            raise ValueError(
                f"Phase 599 annotation/rb mismatch: {entry['phrase']!r}"
            )
        rendered.append(output_format(
            text, annotation["rt"], audit.FORMAT, char_widths,
        ))
        annotation_index += 1
    if annotation_index != len(annotations):
        raise ValueError(
            f"Phase 599 annotation overflow: {entry['phrase']!r}"
        )
    return "".join(rendered)


def build_candidate_rows(
    language: str, output_format, char_widths: dict,
) -> list[list[str]]:
    """Build exactly five phrase rows without touching an app payload."""
    if language not in LANGUAGES:
        raise ValueError(f"Phase 599 unsupported language: {language!r}")
    if not callable(output_format) or not isinstance(char_widths, dict):
        raise ValueError("Phase 599 formatter/width input drift")
    rows = []
    for index, entry in enumerate(policy.load_review()["entries"]):
        phrase = entry["phrase"]
        rendered = _render_target_phrase(
            entry, language, output_format, char_widths,
        )
        rows.append([
            f" {phrase} ",
            f" {rendered} ",
            (
                f" {PLACEHOLDER_PREFIX}"
                f"{LANGUAGE_PLACEHOLDER_DIGIT[language]}{index:02d}$ "
            ),
        ])
    if (
        len(rows) != policy.EXPECTED_COUNTS["candidate_rows_per_language"]
        or len({row[0] for row in rows}) != len(rows)
        or len({row[2] for row in rows}) != len(rows)
    ):
        raise ValueError("Phase 599 candidate row closure drift")
    return rows


def build_candidate_payload(
    deployed_payload: dict, language: str, output_format, char_widths: dict,
) -> tuple[dict, list[list[str]]]:
    """Return a shallow, Ruby-only candidate copy; never mutate the input."""
    validate_deployed_candidate_absent(deployed_payload)
    local_key, global_key, two_char_key = _rule_keys(deployed_payload)
    rows = build_candidate_rows(language, output_format, char_widths)
    candidate = dict(deployed_payload)
    candidate[global_key] = [*rows, *deployed_payload[global_key]]
    if (
        candidate is deployed_payload
        or candidate[global_key] is deployed_payload[global_key]
        or candidate[local_key] is not deployed_payload[local_key]
        or candidate[two_char_key] is not deployed_payload[two_char_key]
    ):
        raise ValueError("Phase 599 in-memory copy isolation drift")
    return candidate, rows


def validate_candidate_payload_delta(
    deployed_payload: dict, candidate_payload: dict,
    rows: list[list[str]], language: str,
) -> dict:
    base_keys = _rule_keys(deployed_payload)
    candidate_keys = _rule_keys(candidate_payload)
    if base_keys != candidate_keys or set(deployed_payload) != set(candidate_payload):
        raise ValueError("Phase 599 candidate payload key drift")
    local_key, global_key, two_char_key = base_keys
    if (
        len(rows) != policy.EXPECTED_COUNTS["candidate_rows_per_language"]
        or candidate_payload[global_key][:len(rows)] != rows
        or candidate_payload[global_key][len(rows):]
        != deployed_payload[global_key]
        or candidate_payload[local_key] != deployed_payload[local_key]
        or candidate_payload[two_char_key] != deployed_payload[two_char_key]
        or candidate_payload[local_key] is not deployed_payload[local_key]
        or candidate_payload[two_char_key] is not deployed_payload[two_char_key]
    ):
        raise ValueError("Phase 599 candidate payload delta escaped scope")
    expected_sources = [
        f" {phrase} " for phrase in policy.EXPECTED_POSITIVE_PHRASES
    ]
    if (
        [row[0] for row in rows] != expected_sources
        or any(
            row[2] != (
                f" {PLACEHOLDER_PREFIX}"
                f"{LANGUAGE_PLACEHOLDER_DIGIT[language]}{index:02d}$ "
            )
            for index, row in enumerate(rows)
        )
    ):
        raise ValueError("Phase 599 exact phrase row drift")
    return {
        "candidate_rows": len(rows),
        "global_rows_added": len(rows),
        "local_rows_changed": 0,
        "two_char_rows_changed": 0,
        "payload_keys_added": 0,
        "payload_keys_removed": 0,
        "ruby_payload_only": True,
        "in_memory_only": True,
    }


def _validate_results_shape(results_by_language: dict, *, stage: str) -> None:
    surfaces = set(policy.combined_surfaces())
    if set(results_by_language) != set(LANGUAGES):
        raise ValueError(f"Phase 599 {stage} language set drift")
    for language in LANGUAGES:
        results = results_by_language[language]
        if not isinstance(results, dict) or set(results) != surfaces:
            raise ValueError(
                f"Phase 599 {stage} {language} surface set drift"
            )
        for surface in surfaces:
            result = results[surface]
            if (
                not isinstance(result, dict)
                or "signature" not in result
                or "annotations" not in result
                or not isinstance(result["annotations"], list)
            ):
                raise ValueError(
                    f"Phase 599 {stage} result shape drift: "
                    f"{language}/{surface!r}"
                )


def _validate_exact_results(
    results_by_language: dict, expected_signatures: dict,
    expected_annotations: dict, *, stage: str,
) -> dict:
    _validate_results_shape(results_by_language, stage=stage)
    surfaces = policy.combined_surfaces()
    for language in LANGUAGES:
        for surface in surfaces:
            actual = results_by_language[language][surface]
            if actual["signature"] != expected_signatures[surface]:
                raise ValueError(
                    f"Phase 599 {stage} boundary drift: "
                    f"{language}/{surface!r}"
                )
            if actual["annotations"] != expected_annotations[language][surface]:
                raise ValueError(
                    f"Phase 599 {stage} annotation drift: "
                    f"{language}/{surface!r}"
                )
    for surface in surfaces:
        signatures = [
            results_by_language[language][surface]["signature"]
            for language in LANGUAGES
        ]
        rb_sequences = [
            [
                annotation["rb"]
                for annotation in
                results_by_language[language][surface]["annotations"]
            ]
            for language in LANGUAGES
        ]
        if (
            any(signature != signatures[0] for signature in signatures[1:])
            or any(sequence != rb_sequences[0] for sequence in rb_sequences[1:])
        ):
            raise ValueError(
                f"Phase 599 {stage} trilingual boundary/rb drift: {surface!r}"
            )
    return {
        "languages": list(LANGUAGES),
        "surfaces_per_language": len(surfaces),
        "trilingual_boundaries_identical": True,
        "trilingual_rb_sequences_identical": True,
    }


def validate_precondition_rendered_results(
    results_by_language: dict,
) -> dict:
    """Require the deployed runtime to retain the reviewed current baseline."""
    report = _validate_exact_results(
        results_by_language,
        policy.expected_precondition_signatures(),
        policy.expected_precondition_annotations(),
        stage="deployed precondition",
    )
    positives = policy.positive_phrases()
    for language in LANGUAGES:
        for phrase in positives:
            spans = results_by_language[language][phrase]["signature"][1]
            if not spans or spans[0] != ("Temis ", False):
                raise ValueError(
                    f"Phase 599 deployed target is no longer unresolved: "
                    f"{language}/{phrase!r}"
                )
    report.update({
        "positive_phrases": len(positives),
        "corpus_instances": policy.EXPECTED_COUNTS["corpus_instances"],
        "unresolved_positive_language_cases": (
            len(positives) * len(LANGUAGES)
        ),
        "negative_cases": len(policy.negative_surfaces()),
        "uppercase_guard_preserves_deployed_TEM_IS": True,
        "candidate_activation_not_redundant": True,
        "deployed_current_runtime_precondition": True,
        "precondition_gate": True,
    })
    return report


def validate_candidate_rendered_results(
    candidate_results: dict, precondition_results: dict,
) -> dict:
    """Require exact positives and byte-semantic nonintervention on guards."""
    report = _validate_exact_results(
        candidate_results,
        {
            **policy.expected_candidate_signatures(),
            **{
                surface: policy.expected_precondition_signatures()[surface]
                for surface in policy.negative_surfaces()
            },
        },
        policy.expected_candidate_annotations(),
        stage="in-memory candidate",
    )
    _validate_results_shape(
        precondition_results, stage="candidate comparison precondition",
    )
    unchanged_negative_cases = 0
    preserved_positive_tails = 0
    for language in LANGUAGES:
        for surface in policy.negative_surfaces():
            before = precondition_results[language][surface]
            after = candidate_results[language][surface]
            if (
                after["signature"] != before["signature"]
                or after["annotations"] != before["annotations"]
            ):
                raise ValueError(
                    f"Phase 599 negative leakage: {language}/{surface!r}"
                )
            unchanged_negative_cases += 1
        for phrase in policy.positive_phrases():
            before = precondition_results[language][phrase]
            after = candidate_results[language][phrase]
            collapsed = audit.signature_from_typed_parts([
                ("Temis", False), *list(after["signature"][1][2:]),
            ])
            if (
                collapsed != before["signature"]
                or after["annotations"][2:] != before["annotations"]
            ):
                raise ValueError(
                    f"Phase 599 positive tail changed: {language}/{phrase!r}"
                )
            preserved_positive_tails += 1
    report.update({
        "positive_phrases_repaired_per_language": (
            policy.EXPECTED_COUNTS["positive_phrases"]
        ),
        "positive_language_cases_repaired": preserved_positive_tails,
        "positive_tail_boundary_annotation_cases_preserved": (
            preserved_positive_tails
        ),
        "negative_language_cases_unchanged": unchanged_negative_cases,
        "negative_nonintervention": True,
        "candidate_runtime_gate": True,
    })
    return report


def _width(text: str, widths: dict) -> float:
    missing = sorted({character for character in text if character not in widths})
    if missing:
        raise ValueError(
            f"Phase 599 width table lacks characters: {missing!r}"
        )
    return sum(float(widths[character]) for character in text)


def _css_scales(language: str) -> dict[str, float]:
    css_text = (
        app_dir(language) / "esp_text_replacement_module.py"
    ).read_text(encoding="utf-8")
    observed = {
        name: float(scale)
        for name, scale in re.findall(
            r"rt\.([A-Z_]+)\s*\{[^}]*?--ruby-font-size\s*:\s*"
            r"([0-9.]+)em",
            css_text,
            re.DOTALL,
        )
    }
    if observed != CSS_CLASS_SCALE:
        raise ValueError(f"Phase 599 {language} CSS scale mapping drift")
    return observed


def validate_added_annotation_widths(
    language: str, output_format, char_widths: dict,
) -> dict:
    """Gate every Phase-599-added Tem/is annotation at strict width < 2."""
    scales = _css_scales(language)
    annotations = policy.load_review()["added_annotations"][language]
    maximum = 0.0
    rendered_count = 0
    for _phrase in policy.positive_phrases():
        for annotation in annotations:
            rb, rt = annotation["rb"], annotation["rt"]
            rendered = output_format(rb, rt, audit.FORMAT, char_widths)
            match = RT_RE.search(rendered)
            if match is None:
                raise ValueError(
                    f"Phase 599 {language} formatter omitted rt class"
                )
            class_name = match.group("class").upper()
            if class_name not in scales:
                raise ValueError(
                    f"Phase 599 {language} unknown rt class: {class_name!r}"
                )
            if BR_RE.search(match.group("rt")):
                raise ValueError(
                    f"Phase 599 {language} added annotation auto-broke"
                )
            visible_rt = html.unescape(TAG_RE.sub("", match.group("rt")))
            rb_width = _width(rb, char_widths)
            if rb_width <= 0:
                raise ValueError(f"Phase 599 zero rb width: {rb!r}")
            ratio = (
                _width(visible_rt, char_widths)
                * scales[class_name]
                / rb_width
            )
            if ratio >= 2.0:
                raise ValueError(
                    f"Phase 599 effective Ruby width is not <2: "
                    f"{language}/{rb!r}/{ratio}"
                )
            maximum = max(maximum, ratio)
            rendered_count += 1
    return {
        "added_annotations_rendered": rendered_count,
        "automatic_br_count": 0,
        "max_effective_width_ratio": maximum,
        "effective_ruby_width_strictly_below_2x": True,
        "width_gate": True,
    }


def _load_runtime_inputs(language: str):
    base = app_dir(language)
    payload_path = deployed_payload_path(language)
    raw = payload_path.read_bytes()
    raw_sha = hashlib.sha256(raw).hexdigest().upper()
    if (
        len(raw) != policy.EXPECTED_PAYLOAD_BYTES[language]
        or raw_sha != policy.EXPECTED_PAYLOAD_SHA256[language]
    ):
        raise ValueError(
            f"Phase 599 {language} deployed Ruby payload identity drift"
        )
    payload = json.loads(raw.decode("utf-8"))
    helper = load_app_replacement_helper(base)
    widths = json.loads(
        (base / "app_data" / "char_widths.json").read_text(encoding="utf-8")
    )
    runtime = audit.runtime_module(base, f"phase599_temis_runtime_{language}")
    overlay = audit.overlay_module(base, f"phase599_temis_overlay_{language}")
    corrections = json.loads(
        (base / "app_data" / "user_corrections.json").read_text(
            encoding="utf-8"
        )
    )
    return payload, helper, widths, runtime, overlay, corrections, raw_sha


def _render(
    language: str, payload: dict, runtime, overlay, corrections,
    *, batch_size: int,
) -> dict:
    return audit.render_signatures(
        runtime,
        app_dir(language),
        payload,
        list(policy.combined_surfaces()),
        batch_size,
        overlay=overlay,
        corrections=corrections,
        include_annotations=True,
    )


def _validate_batch_size(batch_size: int) -> None:
    if not isinstance(batch_size, int) or not 1 <= batch_size <= 50:
        raise ValueError("Phase 599 runtime batch size must be in 1..50")


def _deployed_run(*, include_candidate: bool, batch_size: int) -> dict:
    _validate_batch_size(batch_size)
    review_before = policy.review_identity()
    runtime_before = {
        language: runtime_input_fingerprint(language)
        for language in LANGUAGES
    }
    kanji_before = kanji_track_fingerprint()
    precondition_results = {}
    candidate_results = {}
    payload_hashes = {}
    absence_reports = {}
    delta_reports = {}
    width_reports = {}
    for language in LANGUAGES:
        (
            payload, helper, widths, runtime, overlay, corrections, raw_sha,
        ) = _load_runtime_inputs(language)
        payload_hashes[language] = raw_sha
        absence_reports[language] = validate_deployed_candidate_absent(payload)
        precondition_results[language] = _render(
            language, payload, runtime, overlay, corrections,
            batch_size=batch_size,
        )
        if include_candidate:
            candidate, rows = build_candidate_payload(
                payload, language, helper.output_format, widths,
            )
            delta_reports[language] = validate_candidate_payload_delta(
                payload, candidate, rows, language,
            )
            width_reports[language] = validate_added_annotation_widths(
                language, helper.output_format, widths,
            )
            candidate_results[language] = _render(
                language, candidate, runtime, overlay, corrections,
                batch_size=batch_size,
            )
            del candidate, rows
        del payload, helper, widths, runtime, overlay, corrections
        gc.collect()
    precondition_report = validate_precondition_rendered_results(
        precondition_results
    )
    candidate_report = None
    if include_candidate:
        candidate_report = validate_candidate_rendered_results(
            candidate_results, precondition_results,
        )
    runtime_after = {
        language: runtime_input_fingerprint(language)
        for language in LANGUAGES
    }
    kanji_after = kanji_track_fingerprint()
    payload_hashes_after = {
        language: file_sha256(deployed_payload_path(language))
        for language in LANGUAGES
    }
    if (
        runtime_after != runtime_before
        or kanji_after != kanji_before
        or payload_hashes_after != payload_hashes
        or policy.review_identity() != review_before
    ):
        raise ValueError("Phase 599 input changed during runtime gate")
    report = {
        "phase": policy.PHASE,
        "mode": (
            "deployed_precondition_and_in_memory_candidate"
            if include_candidate else "deployed_precondition"
        ),
        "candidate_only": True,
        "generator_integration": False,
        "filesystem_payload_writes": 0,
        "deployed_payload_sha256": payload_hashes,
        "deployed_candidate_absence": absence_reports,
        "precondition": precondition_report,
        "runtime_inputs_stable": True,
        "review_input_stable": True,
        "kanji_track_files_fingerprinted": len(kanji_before),
        "kanji_track_files_changed": 0,
        "kanji_nonintervention": True,
        "kanji_nonintervention_gate": True,
        "review": review_before,
    }
    if candidate_report is not None:
        maxima = {
            language: width_reports[language]["max_effective_width_ratio"]
            for language in LANGUAGES
        }
        if any(value >= 2.0 for value in maxima.values()):
            raise ValueError(
                f"Phase 599 aggregate width gate failed: {maxima!r}"
            )
        report.update({
            "candidate_payload_delta": delta_reports,
            "candidate_runtime": candidate_report,
            "width": {
                "languages": width_reports,
                "max_effective_width_ratio": maxima,
                "effective_ruby_width_strictly_below_2x": True,
                "width_gate": True,
            },
            "candidate_payloads_materialized_on_disk": 0,
            "candidate_discarded_after_validation": True,
        })
    return report


def validate_deployed_precondition(*, batch_size: int = 20) -> dict:
    return _deployed_run(include_candidate=False, batch_size=batch_size)


def validate_deployed_in_memory_candidate(
    *, batch_size: int = 20,
) -> dict:
    return _deployed_run(include_candidate=True, batch_size=batch_size)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--deployed-precondition",
        action="store_true",
        help="verify that all 11 reviewed surfaces still equal deployed runtime",
    )
    mode.add_argument(
        "--in-memory-candidate",
        action="store_true",
        help=(
            "verify the deployed precondition, then inject and discard five "
            "Ruby-only rows in memory"
        ),
    )
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args(argv)
    if args.deployed_precondition:
        report = validate_deployed_precondition(batch_size=args.batch_size)
    else:
        report = validate_deployed_in_memory_candidate(
            batch_size=args.batch_size
        )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
