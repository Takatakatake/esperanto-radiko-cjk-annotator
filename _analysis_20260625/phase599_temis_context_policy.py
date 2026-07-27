# -*- coding: utf-8 -*-
"""Fail-closed, candidate-only policy for contextual ordinary-verb ``Temis``.

The global bare-form guard is intentional because ``Temis`` is also the name
of the goddess Themis.  Phase 599 therefore licenses ``Tem/is`` only inside
five exact, case-sensitive long phrases attested six times in the reviewed
Kyoto corpus.  This module describes policy and expectations; it does not
integrate anything into the generator or write an application payload.
"""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

import no_worsening_audit as audit


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REVIEW_PATH = HERE / "_phase599_temis_context_review.json"

PHASE = 599
LANGUAGES = ("JA", "ZH", "KO")
EXPECTED_REVIEW_SHA256 = (
    "36632BC256E435103A3CA2BCC5B41E11D184C68BBEC544D16457441EBFB00F32"
)
EXPECTED_SCOPE_SHA256 = (
    "ABCD0362210F3C91D6A9B84ACA9B60BFD82AAA6F44980E2A39A334C2A7116864"
)
EXPECTED_SOURCES_SHA256 = (
    "AC48E3975F0D0DB5FA921E01F28DC72D2B72B6DCEFD9DAD1EBF8CBBC6B99E413"
)
EXPECTED_COUNTS_SHA256 = (
    "17569E82649F045CC1CAE72EA2065C11C5E86FF12C37953753D0A51E4BAD5F30"
)
EXPECTED_ADDED_ANNOTATIONS_SHA256 = (
    "82C4613C82C7A9A9F46936BAF27F7168A7A8E8F3FDC8EF609CEE7679A2597781"
)
EXPECTED_ENTRIES_SHA256 = (
    "7BF166810B0BC0A807C5C19A815AD0F10D710FB70D53744382D9445AC80C5F30"
)
EXPECTED_NEGATIVE_CASES_SHA256 = (
    "E6005CDD1B948BB02FEDFECC927F92987519E1CE0BBDFDCD4EBC01B1BB26D34A"
)
EXPECTED_DECISIONS_SHA256 = (
    "96AB0FC5C4D8C8E269B694E43E0BF8C464752C5F87445C59A3A99CF1689467CB"
)

EXPECTED_POLICY = (
    "Split the ordinary past-tense verb Temis as Tem/is only when one of the "
    "five reviewed Kyoto-corpus long phrases matches exactly. Preserve every "
    "following Ruby boundary and annotation in JA/ZH/KO, leave every guard "
    "and the Kanji track unchanged, and keep this candidate out of the "
    "deployed generator."
)
EXPECTED_SCOPE = {
    "track": "Ruby",
    "activation": "in_memory_candidate_only",
    "match_mode": "exact_case_sensitive_long_phrase",
    "generator_integration": False,
    "filesystem_writes": False,
    "kanji_paths": [],
    "allowed_languages": list(LANGUAGES),
}
EXPECTED_COUNTS = {
    "positive_phrases": 5,
    "corpus_instances": 6,
    "duplicate_corpus_instances": 1,
    "negative_cases": 6,
    "languages": 3,
    "added_annotations_per_positive": 2,
    "candidate_rows_per_language": 5,
    "candidate_rows_total": 15,
    "generator_files_changed": 0,
    "kanji_files_changed": 0,
}
EXPECTED_POSITIVE_PHRASES = (
    "Temis tamen pri aparatoj",
    "Temis pri tre noveca",
    "Temis pri la volo",
    "Temis pri la distrikto",
    "Temis pri malnovaj",
)
EXPECTED_POSITIVE_INSTANCES = {
    "Temis tamen pri aparatoj": 1,
    "Temis pri tre noveca": 1,
    "Temis pri la volo": 1,
    "Temis pri la distrikto": 1,
    "Temis pri malnovaj": 2,
}
EXPECTED_NEGATIVE_SURFACES = (
    "Temis",
    "Temiso",
    "TEMIS",
    "La diino Temis pri justeco",
    "Temis tamen bela",
    "Temis, pri justeco",
)
EXPECTED_NEGATIVE_KINDS = (
    "bare_ambiguous_surface",
    "goddess_name_derivative",
    "case_guard_preserve_deployed_behavior",
    "goddess_name_context",
    "unreviewed_predicate_context",
    "punctuation_guard",
)
EXPECTED_PAYLOAD_SHA256 = {
    "JA": "3D9EDF76DC2857350742D9473388AF97C49823DCAF523CD56EE6491C478C6873",
    "ZH": "0557CBD1DB91F30CF824E27E894E8008F61E2789B24AEEF6922089F1256FE37A",
    "KO": "CFF51B7F9AA9D251311D78DA5349891350E9379618C8365F00C4BFE6E9CD50E0",
}
EXPECTED_PAYLOAD_BYTES = {
    "JA": 72404214,
    "ZH": 70132667,
    "KO": 71704722,
}
EXPECTED_PAYLOAD_PATHS = {
    language: (
        f"Esperanto-Kanji-Ruby-{language}/app_data/置換リスト_ルビ.json"
    )
    for language in LANGUAGES
}


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def _typed_parts(value, *, context: str) -> list[tuple[str, bool]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"Phase 599 missing typed parts: {context}")
    parts: list[tuple[str, bool]] = []
    for index, row in enumerate(value):
        if (
            not isinstance(row, dict)
            or set(row) != {"text", "ruby"}
            or not isinstance(row["text"], str)
            or not row["text"]
            or not isinstance(row["ruby"], bool)
        ):
            raise ValueError(
                f"Phase 599 invalid typed part: {context}[{index}]"
            )
        parts.append((row["text"], row["ruby"]))
    return parts


def _annotations(value, *, context: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError(f"Phase 599 missing annotation list: {context}")
    result = []
    for index, row in enumerate(value):
        if (
            not isinstance(row, dict)
            or set(row) != {"rb", "rt"}
            or not isinstance(row["rb"], str)
            or not row["rb"]
            or not isinstance(row["rt"], str)
            or not row["rt"]
        ):
            raise ValueError(
                f"Phase 599 invalid annotation: {context}[{index}]"
            )
        result.append({"rb": row["rb"], "rt": row["rt"]})
    return result


def _signature(value, *, context: str):
    return audit.signature_from_typed_parts(
        _typed_parts(value, context=context)
    )


def _positive_precondition_signature(entry: dict):
    target = _typed_parts(
        entry["target_typed_parts"],
        context=f"{entry.get('phrase')!r}.target_typed_parts",
    )
    if target[:2] != [("Tem", True), ("is", True)]:
        raise ValueError(
            f"Phase 599 positive target lost Tem/is: {entry.get('phrase')!r}"
        )
    return audit.signature_from_typed_parts(
        [("Temis", False), *target[2:]]
    )


def _validate_source_identity(payload: dict) -> None:
    sources = payload["sources"]
    if (
        sources.get("base_app") != {
            "commit": "3F338920F59EFD80333616AF6192E0F099C3D07C"
        }
        or sources.get("kyoto_corpus", {}).get("commit")
        != "7C04F97C51A7CECF88918D2ABC2E6BF2F34601A6"
        or sources["kyoto_corpus"].get("content_fingerprint")
        != "4F04FD2F3DBE0FC79909CBBEA61ED2848FC093AE2DFE3F0ADEB79882AEB04F52"
        or sources["kyoto_corpus"].get("temis_instances") != 6
    ):
        raise ValueError("Phase 599 source revision drift")
    deployed = sources.get("deployed_ruby_payloads")
    if not isinstance(deployed, dict) or set(deployed) != set(LANGUAGES):
        raise ValueError("Phase 599 deployed-payload source drift")
    for language in LANGUAGES:
        if deployed[language] != {
            "path": EXPECTED_PAYLOAD_PATHS[language],
            "bytes": EXPECTED_PAYLOAD_BYTES[language],
            "sha256": EXPECTED_PAYLOAD_SHA256[language],
        }:
            raise ValueError(
                f"Phase 599 {language} deployed-payload identity drift"
            )
    collision = sources.get("semantic_collision", {})
    if (
        collision.get("force_bare", {}).get("line") != 157
        or collision.get("reference_conflicts", {}).get("category")
        != "contextual_homograph"
        or collision.get("two_track_decision", {}).get("lines") != [159, 160]
    ):
        raise ValueError("Phase 599 semantic-collision authority drift")


def _validate_positive_entry(
    entry: dict, expected_phrase: str, added_annotations: dict,
) -> None:
    if (
        not isinstance(entry, dict)
        or set(entry) != {
            "phrase", "corpus_instances", "corpus_locations",
            "target_typed_parts", "preserved_annotations",
        }
        or entry.get("phrase") != expected_phrase
        or entry.get("corpus_instances")
        != EXPECTED_POSITIVE_INSTANCES[expected_phrase]
    ):
        raise ValueError(
            f"Phase 599 positive entry identity drift: {expected_phrase!r}"
        )
    locations = entry["corpus_locations"]
    if (
        not isinstance(locations, list)
        or not locations
        or any(
            not isinstance(location, dict)
            or set(location) != {"path", "instances"}
            or not isinstance(location["path"], str)
            or not location["path"].endswith(".html")
            or not isinstance(location["instances"], int)
            or location["instances"] < 1
            for location in locations
        )
        or sum(location["instances"] for location in locations)
        != entry["corpus_instances"]
    ):
        raise ValueError(
            f"Phase 599 corpus location drift: {expected_phrase!r}"
        )
    target_signature = _signature(
        entry["target_typed_parts"],
        context=f"{expected_phrase!r}.target_typed_parts",
    )
    if target_signature[0] != expected_phrase:
        raise ValueError(
            f"Phase 599 positive reconstruction drift: {expected_phrase!r}"
        )
    if list(target_signature[1][:2]) != [("Tem", True), ("is", True)]:
        raise ValueError(
            f"Phase 599 positive Tem/is boundary drift: {expected_phrase!r}"
        )
    precondition = _positive_precondition_signature(entry)
    if (
        precondition[0] != expected_phrase
        or precondition[1][0] != ("Temis ", False)
    ):
        raise ValueError(
            f"Phase 599 positive precondition drift: {expected_phrase!r}"
        )
    preserved = entry["preserved_annotations"]
    if not isinstance(preserved, dict) or set(preserved) != set(LANGUAGES):
        raise ValueError(
            f"Phase 599 positive annotation-language drift: {expected_phrase!r}"
        )
    expected_ruby_bases = [
        text for text, is_ruby in target_signature[1] if is_ruby
    ]
    rb_sequences = []
    for language in LANGUAGES:
        added = _annotations(
            added_annotations[language],
            context=f"added_annotations.{language}",
        )
        tail = _annotations(
            preserved[language],
            context=f"{expected_phrase!r}.preserved_annotations.{language}",
        )
        full = [*added, *tail]
        rb_sequence = [annotation["rb"] for annotation in full]
        if rb_sequence != expected_ruby_bases:
            raise ValueError(
                f"Phase 599 {language} positive rb drift: "
                f"{expected_phrase!r}"
            )
        rb_sequences.append(rb_sequence)
    if any(sequence != rb_sequences[0] for sequence in rb_sequences[1:]):
        raise ValueError(
            f"Phase 599 trilingual positive rb drift: {expected_phrase!r}"
        )


def _validate_negative_case(entry: dict, surface: str, kind: str) -> None:
    if (
        not isinstance(entry, dict)
        or set(entry) != {
            "surface", "kind", "current_typed_parts", "current_annotations",
        }
        or entry.get("surface") != surface
        or entry.get("kind") != kind
    ):
        raise ValueError(f"Phase 599 negative identity drift: {surface!r}")
    signature = _signature(
        entry["current_typed_parts"],
        context=f"{surface!r}.current_typed_parts",
    )
    if signature[0] != surface:
        raise ValueError(
            f"Phase 599 negative reconstruction drift: {surface!r}"
        )
    localized = entry["current_annotations"]
    if not isinstance(localized, dict) or set(localized) != set(LANGUAGES):
        raise ValueError(
            f"Phase 599 negative annotation-language drift: {surface!r}"
        )
    expected_ruby_bases = [
        text for text, is_ruby in signature[1] if is_ruby
    ]
    rb_sequences = []
    for language in LANGUAGES:
        annotations = _annotations(
            localized[language],
            context=f"{surface!r}.current_annotations.{language}",
        )
        rb_sequence = [annotation["rb"] for annotation in annotations]
        if rb_sequence != expected_ruby_bases:
            raise ValueError(
                f"Phase 599 {language} negative rb drift: {surface!r}"
            )
        rb_sequences.append(rb_sequence)
    if any(sequence != rb_sequences[0] for sequence in rb_sequences[1:]):
        raise ValueError(
            f"Phase 599 trilingual negative rb drift: {surface!r}"
        )


def validate_review_payload(payload: dict) -> dict:
    expected_keys = {
        "schema_version", "phase", "status", "policy", "scope", "sources",
        "expected_counts", "added_annotations", "entries", "negative_cases",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != expected_keys
        or payload.get("schema_version") != 1
        or payload.get("phase") != PHASE
        or payload.get("status") != "candidate_only"
        or payload.get("policy") != EXPECTED_POLICY
        or payload.get("scope") != EXPECTED_SCOPE
        or payload.get("expected_counts") != EXPECTED_COUNTS
        or compact_sha256(payload.get("scope")) != EXPECTED_SCOPE_SHA256
        or compact_sha256(payload.get("sources")) != EXPECTED_SOURCES_SHA256
        or compact_sha256(payload.get("expected_counts"))
        != EXPECTED_COUNTS_SHA256
        or compact_sha256(payload.get("added_annotations"))
        != EXPECTED_ADDED_ANNOTATIONS_SHA256
        or compact_sha256(payload.get("entries")) != EXPECTED_ENTRIES_SHA256
        or compact_sha256(payload.get("negative_cases"))
        != EXPECTED_NEGATIVE_CASES_SHA256
        or compact_sha256({
            "added_annotations": payload.get("added_annotations"),
            "entries": payload.get("entries"),
            "negative_cases": payload.get("negative_cases"),
        }) != EXPECTED_DECISIONS_SHA256
    ):
        raise ValueError("Phase 599 contextual review identity drift")
    _validate_source_identity(payload)
    added = payload["added_annotations"]
    if not isinstance(added, dict) or set(added) != set(LANGUAGES):
        raise ValueError("Phase 599 added-annotation language drift")
    added_rb_sequences = []
    for language in LANGUAGES:
        annotations = _annotations(
            added[language], context=f"added_annotations.{language}",
        )
        if len(annotations) != 2:
            raise ValueError(
                f"Phase 599 {language} added-annotation count drift"
            )
        added_rb_sequences.append(
            [annotation["rb"] for annotation in annotations]
        )
    if any(sequence != ["Tem", "is"] for sequence in added_rb_sequences):
        raise ValueError("Phase 599 added Tem/is rb drift")
    entries = payload["entries"]
    negatives = payload["negative_cases"]
    if (
        not isinstance(entries, list)
        or [entry.get("phrase") for entry in entries]
        != list(EXPECTED_POSITIVE_PHRASES)
        or len({entry["phrase"] for entry in entries}) != len(entries)
        or not isinstance(negatives, list)
        or [entry.get("surface") for entry in negatives]
        != list(EXPECTED_NEGATIVE_SURFACES)
        or len({entry["surface"] for entry in negatives}) != len(negatives)
        or set(EXPECTED_POSITIVE_PHRASES) & set(EXPECTED_NEGATIVE_SURFACES)
    ):
        raise ValueError("Phase 599 closed phrase/guard set drift")
    for entry, phrase in zip(entries, EXPECTED_POSITIVE_PHRASES):
        _validate_positive_entry(entry, phrase, added)
    for entry, surface, kind in zip(
        negatives, EXPECTED_NEGATIVE_SURFACES, EXPECTED_NEGATIVE_KINDS,
    ):
        _validate_negative_case(entry, surface, kind)
    instance_counts = collections.Counter({
        entry["phrase"]: entry["corpus_instances"] for entry in entries
    })
    if (
        dict(instance_counts) != EXPECTED_POSITIVE_INSTANCES
        or sum(instance_counts.values()) != EXPECTED_COUNTS["corpus_instances"]
        or sum(value - 1 for value in instance_counts.values())
        != EXPECTED_COUNTS["duplicate_corpus_instances"]
    ):
        raise ValueError("Phase 599 corpus instance count drift")
    return payload


def load_review(path: Path = REVIEW_PATH) -> dict:
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != EXPECTED_REVIEW_SHA256:
        raise ValueError("Phase 599 contextual review raw identity drift")
    return validate_review_payload(json.loads(raw.decode("utf-8")))


def positive_phrases() -> tuple[str, ...]:
    review = load_review()
    return tuple(entry["phrase"] for entry in review["entries"])


def negative_surfaces() -> tuple[str, ...]:
    review = load_review()
    return tuple(entry["surface"] for entry in review["negative_cases"])


def combined_surfaces() -> tuple[str, ...]:
    return (*positive_phrases(), *negative_surfaces())


def expected_candidate_signatures() -> dict:
    return {
        entry["phrase"]: _signature(
            entry["target_typed_parts"],
            context=f"{entry['phrase']!r}.target_typed_parts",
        )
        for entry in load_review()["entries"]
    }


def expected_precondition_signatures() -> dict:
    review = load_review()
    result = {
        entry["phrase"]: _positive_precondition_signature(entry)
        for entry in review["entries"]
    }
    result.update({
        entry["surface"]: _signature(
            entry["current_typed_parts"],
            context=f"{entry['surface']!r}.current_typed_parts",
        )
        for entry in review["negative_cases"]
    })
    return result


def expected_candidate_annotations() -> dict:
    review = load_review()
    result = {language: {} for language in LANGUAGES}
    for entry in review["entries"]:
        for language in LANGUAGES:
            result[language][entry["phrase"]] = [
                *review["added_annotations"][language],
                *entry["preserved_annotations"][language],
            ]
    for entry in review["negative_cases"]:
        for language in LANGUAGES:
            result[language][entry["surface"]] = (
                entry["current_annotations"][language]
            )
    return result


def expected_precondition_annotations() -> dict:
    review = load_review()
    result = {language: {} for language in LANGUAGES}
    for entry in review["entries"]:
        for language in LANGUAGES:
            result[language][entry["phrase"]] = (
                entry["preserved_annotations"][language]
            )
    for entry in review["negative_cases"]:
        for language in LANGUAGES:
            result[language][entry["surface"]] = (
                entry["current_annotations"][language]
            )
    return result


def review_identity() -> dict:
    review = load_review()
    return {
        "phase": PHASE,
        "status": review["status"],
        "review_sha256": EXPECTED_REVIEW_SHA256,
        "entries_sha256": EXPECTED_ENTRIES_SHA256,
        "negative_cases_sha256": EXPECTED_NEGATIVE_CASES_SHA256,
        "positive_phrases": EXPECTED_COUNTS["positive_phrases"],
        "corpus_instances": EXPECTED_COUNTS["corpus_instances"],
        "negative_cases": EXPECTED_COUNTS["negative_cases"],
        "generator_integration": review["scope"]["generator_integration"],
        "filesystem_writes": review["scope"]["filesystem_writes"],
        "kanji_paths": list(review["scope"]["kanji_paths"]),
        "base_app_commit": review["sources"]["base_app"]["commit"],
        "kyoto_corpus_commit": review["sources"]["kyoto_corpus"]["commit"],
    }
