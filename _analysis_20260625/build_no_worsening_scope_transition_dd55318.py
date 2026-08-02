# -*- coding: utf-8 -*-
"""Build/check the reviewed no-worsening reference scope for corpus dd55318.

The Phase532/b769 manifests remain immutable historical evidence.  This
successor pair is selected explicitly with ``--scope-manifest`` and
``--conflict-manifest``.  Only newly introduced corpus conflicts are
adjudicated here, and all three choose the coarse Kyoto Ruby boundary; none
changes the learner/Kanji fake-decomposition authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from atomic_json import atomic_json_dump
import build_corpus_source_transition_dd55318 as corpus_transition
import no_worsening_audit as audit


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CANDIDATE_PATH = HERE / "out" / "_audit_no_worsening_references_dd55318.json"
PARENT_SCOPE_PATH = HERE / "_no_worsening_scope_manifest.json"
PARENT_CONFLICT_PATH = HERE / "_no_worsening_reference_conflicts.json"
SOURCE_TRANSITION_PATH = HERE / "_corpus_source_transition_dd55318.json"
OUTPUT_SCOPE_PATH = HERE / "_no_worsening_scope_manifest_dd55318.json"
OUTPUT_CONFLICT_PATH = HERE / "_no_worsening_reference_conflicts_dd55318.json"

CANDIDATE_FILE_SHA256 = (
    "70D5BEC163DABF7560E96FCC6632036BC68FBF09AE7331E9335D555DE0456190"
)
PARENT_SCOPE_FILE_SHA256 = (
    "3A56C4C87BBB739A8D12D3E9EB19310F648CB4E735AD705054CD19A579060215"
)
PARENT_CONFLICT_FILE_SHA256 = (
    "2EDE9CDCB492D1B99C990818EF2E82809C49BDB9943EAB163E04B93C4FA58D94"
)
SOURCE_TRANSITION_FILE_SHA256 = (
    "C3BD6DE90C3BDC3BC1B8008308F1AB94D9FFDE15940757522FC202BEB48BC42A"
)
EXPECTED_SCOPE_FILE_SHA256 = (
    "13C989F4B4652CB2984AE96E5DAC3AECDAB6C40F37C7A6632BF5573B045599F0"
)
EXPECTED_CONFLICT_FILE_SHA256 = (
    "F6ABEC16CC73B2FE74F3F4ECC2803582CB0AD09288B620CCFC2226E0C6B40522"
)
EXPECTED_PROJECTION = {
    "case_count": 68650,
    "surface_count": 68559,
    "reference_sha256": (
        "C26EF076E4FC073868E99233567C3C3CE2A3D0C96E40701A83BD5520C7DA161B"
    ),
    "reference_conflict_count": 91,
    "reference_conflicts_sha256": (
        "5FEAD5FA9E21065B204FCC0C790B7460AADC9A0B35A9DD9D03836812DC65A61B"
    ),
    "projection_sha256": (
        "A61C15066C3C0AD9A70A8381713EAE1AE7CCF97F5352BDB9E05BE03EC3A9EC96"
    ),
    "corpus_head_oid": "dd55318c33b36128e64561d4ae7fca587ad974fa",
    "corpus_content_sha256": (
        "33ED6EA94E45A5434B3AAE035F8C44D97278ACABA9A83714A0167EC0754C70B8"
    ),
    "gold_sha256": (
        "6B403AA30BBCBBA4C9E41A2CF48D1AD2FC1D5A5DB1154CAF1260A361566E3226"
    ),
}
ADDED_CONFLICTS = {"miksdevena", "radioelsendo", "radioprogramo"}
REMOVED_CONFLICTS = {"iniciatoro"}
CHANGED_EXISTING_OPTIONS = {"Tokio", "radio"}
COARSE_EXPECTED = {
    "miksdevena": "miks/deven/a",
    "radioelsendo": "radio/el/send/o",
    "radioprogramo": "radio/program/o",
}


def raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def read_sealed(path: Path, expected_sha256: str) -> dict:
    raw = path.read_bytes()
    if raw_sha256(raw) != expected_sha256:
        raise ValueError(f"sealed input changed: {path.name}")
    return json.loads(raw.decode("utf-8"))


def validate_candidate(candidate: dict, source_transition: dict) -> None:
    projection = candidate.get("projection")
    scope = candidate.get("scope_manifest_candidate")
    conflicts = candidate.get("conflicts")
    if not isinstance(projection, dict) or not isinstance(scope, dict):
        raise ValueError("references-only candidate schema changed")
    if scope != {
        "manifest_schema_version": 1,
        "projection_sha256": audit.stable_json_sha256(projection),
        "expected": projection,
    }:
        raise ValueError("candidate scope manifest is not self-consistent")
    for key in (
        "case_count", "surface_count", "reference_sha256",
        "reference_conflict_count", "reference_conflicts_sha256",
    ):
        if projection.get(key) != EXPECTED_PROJECTION[key]:
            raise ValueError(f"dd55318 reference projection changed: {key}")
    if scope["projection_sha256"] != EXPECTED_PROJECTION["projection_sha256"]:
        raise ValueError("dd55318 projection hash changed")
    if (
        projection.get("schema_version") != audit.REFERENCE_SCHEMA_VERSION
        or projection.get("corpus_repository", {}).get("head_oid")
        != EXPECTED_PROJECTION["corpus_head_oid"]
        or projection.get("corpus", {}).get("content_sha256")
        != EXPECTED_PROJECTION["corpus_content_sha256"]
        or projection.get("corpus", {}).get("files") != 170
        or projection.get("gold", {}).get("sha256")
        != EXPECTED_PROJECTION["gold_sha256"]
        or not isinstance(conflicts, list)
        or len(conflicts) != EXPECTED_PROJECTION["reference_conflict_count"]
        or audit.stable_json_sha256(conflicts)
        != EXPECTED_PROJECTION["reference_conflicts_sha256"]
    ):
        raise ValueError("dd55318 source/reference identity changed")
    source_candidate = source_transition.get("corpus", {}).get("candidate", {})
    policy = source_transition.get("policy", {})
    if (
        source_candidate.get("head_oid")
        != EXPECTED_PROJECTION["corpus_head_oid"]
        or source_candidate.get("content_sha256")
        != EXPECTED_PROJECTION["corpus_content_sha256"]
        or not policy.get("source_only_transition")
        or policy.get("kanji_track_changed_by_transition")
        or policy.get("learner_fake_decomposition_changed_by_transition")
    ):
        raise ValueError("corpus successor authority/policy changed")


def select_signature(conflict: dict, expected: str) -> dict:
    matches = [
        option["signature"] for option in conflict["options"]
        if option.get("expected") == expected
    ]
    if len(matches) != 1:
        raise ValueError(
            f"coarse conflict choice is not unique: {conflict['surface']!r}"
        )
    return matches[0]


def build_conflict_manifest(parent: dict, conflicts: list[dict]) -> dict:
    old_by_surface = {row["surface"]: row for row in parent["entries"]}
    new_by_surface = {row["surface"]: row for row in conflicts}
    if len(old_by_surface) != len(parent["entries"]):
        raise ValueError("duplicate parent conflict surface")
    if len(new_by_surface) != len(conflicts):
        raise ValueError("duplicate candidate conflict surface")
    if set(new_by_surface) - set(old_by_surface) != ADDED_CONFLICTS:
        raise ValueError("new conflict set changed")
    if set(old_by_surface) - set(new_by_surface) != REMOVED_CONFLICTS:
        raise ValueError("retired conflict set changed")
    changed = {
        surface for surface in set(old_by_surface) & set(new_by_surface)
        if old_by_surface[surface]["options"] != new_by_surface[surface]["options"]
    }
    if changed != CHANGED_EXISTING_OPTIONS:
        raise ValueError(f"existing conflict evidence drifted: {sorted(changed)!r}")

    entries = []
    for conflict in conflicts:
        surface = conflict["surface"]
        if surface in ADDED_CONFLICTS:
            expected = COARSE_EXPECTED[surface]
            reason = {
                "miksdevena": (
                    "The learner/Kanji track retains miks/de/ven/a, while "
                    "the Kyoto annotation-Ruby convention intentionally uses "
                    "the coarser lexical unit miks/deven/a."
                ),
                "radioelsendo": (
                    "This corpus occurrence means a radio broadcast, so the "
                    "media root radio is required; radi/o is the competing "
                    "radiation/electromagnetic analysis from the frozen gold."
                ),
                "radioprogramo": (
                    "This corpus occurrence means a radio program, so the "
                    "media root radio is required; it must not be split as "
                    "the physical radi/o analysis merely to shorten Ruby."
                ),
            }[surface]
            entries.append({
                "surface": surface,
                "options": conflict["options"],
                "allowed_signatures": [select_signature(conflict, expected)],
                "category": "ruby_track_coarse_two_track_partition",
                "reason": reason,
            })
            continue
        old = old_by_surface[surface]
        entry = dict(old)
        entry["options"] = conflict["options"]
        if surface == "radio":
            entry["reason"] = (
                "The spelling radio is context-sensitive: radi/o is the "
                "radiation/electromagnetic noun, while atomic radio is the "
                "media/broadcast lexical unit. Both are attested; document "
                "context determines the Ruby boundary."
            )
        available = {
            json.dumps(
                option["signature"], ensure_ascii=True, sort_keys=True,
                separators=(",", ":"),
            )
            for option in conflict["options"]
        }
        allowed = {
            json.dumps(
                signature, ensure_ascii=True, sort_keys=True,
                separators=(",", ":"),
            )
            for signature in entry["allowed_signatures"]
        }
        if not allowed or not allowed <= available:
            raise ValueError(f"carried conflict choice became invalid: {surface!r}")
        entries.append(entry)
    entries.sort(key=lambda row: row["surface"])
    return {
        "manifest_schema_version": 1,
        "reference_schema_version": audit.REFERENCE_SCHEMA_VERSION,
        "raw_conflicts_sha256": audit.stable_json_sha256(conflicts),
        "entries": entries,
    }


def build() -> tuple[dict, dict]:
    candidate = read_sealed(CANDIDATE_PATH, CANDIDATE_FILE_SHA256)
    parent_scope = read_sealed(PARENT_SCOPE_PATH, PARENT_SCOPE_FILE_SHA256)
    parent_conflict = read_sealed(
        PARENT_CONFLICT_PATH, PARENT_CONFLICT_FILE_SHA256,
    )
    source_transition = read_sealed(
        SOURCE_TRANSITION_PATH, SOURCE_TRANSITION_FILE_SHA256,
    )
    corpus_transition.validate_ledger(source_transition)
    validate_candidate(candidate, source_transition)
    if (
        parent_scope.get("expected", {}).get("corpus_repository", {}).get(
            "head_oid"
        ) != "b769038ef15346a536ce93721d6f0f46849db0ea"
        or parent_conflict.get("raw_conflicts_sha256")
        != parent_scope.get("expected", {}).get("reference_conflicts_sha256")
    ):
        raise ValueError("historical Phase532/b769 reference evidence changed")
    successor_scope = candidate["scope_manifest_candidate"]
    successor_conflict = build_conflict_manifest(
        parent_conflict, candidate["conflicts"],
    )
    return successor_scope, successor_conflict


def verify_output(path: Path, payload: dict, expected_sha256: str) -> None:
    current_raw = path.read_bytes()
    if json.loads(current_raw.decode("utf-8")) != payload:
        raise ValueError(f"successor manifest is stale: {path.name}")
    if expected_sha256 == "TO_BE_SEALED":
        raise ValueError(f"successor manifest hash is not sealed: {path.name}")
    if raw_sha256(current_raw) != expected_sha256:
        raise ValueError(f"successor manifest byte identity changed: {path.name}")


def serialized_payload(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    scope, conflict = build()
    if args.write:
        if OUTPUT_SCOPE_PATH.exists() or OUTPUT_CONFLICT_PATH.exists():
            raise FileExistsError(
                "refusing to overwrite immutable dd55318 successor manifests"
            )
        if (
            raw_sha256(serialized_payload(scope)) != EXPECTED_SCOPE_FILE_SHA256
            or raw_sha256(serialized_payload(conflict))
            != EXPECTED_CONFLICT_FILE_SHA256
        ):
            raise ValueError("successor serialization does not match sealed hashes")
        atomic_json_dump(OUTPUT_SCOPE_PATH, scope, indent=1)
        atomic_json_dump(OUTPUT_CONFLICT_PATH, conflict, indent=1)
        verify_output(
            OUTPUT_SCOPE_PATH, scope, EXPECTED_SCOPE_FILE_SHA256,
        )
        verify_output(
            OUTPUT_CONFLICT_PATH, conflict, EXPECTED_CONFLICT_FILE_SHA256,
        )
        result = {
            "mode": "write",
            "scope_file_sha256": raw_sha256(OUTPUT_SCOPE_PATH.read_bytes()),
            "conflict_file_sha256": raw_sha256(OUTPUT_CONFLICT_PATH.read_bytes()),
        }
    else:
        verify_output(
            OUTPUT_SCOPE_PATH, scope, EXPECTED_SCOPE_FILE_SHA256,
        )
        verify_output(
            OUTPUT_CONFLICT_PATH, conflict, EXPECTED_CONFLICT_FILE_SHA256,
        )
        result = {"mode": "check", "gate": True}
    result.update({
        "case_count": EXPECTED_PROJECTION["case_count"],
        "surface_count": EXPECTED_PROJECTION["surface_count"],
        "conflicts": EXPECTED_PROJECTION["reference_conflict_count"],
        "added_conflicts": sorted(ADDED_CONFLICTS),
        "removed_conflicts": sorted(REMOVED_CONFLICTS),
        "kanji_track_changed": False,
    })
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
