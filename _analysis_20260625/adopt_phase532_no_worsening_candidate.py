# -*- coding: utf-8 -*-
"""Adopt a frozen Phase 532 no-worsening candidate, without bulk promotion.

The adopter is intentionally unusable until the references-only candidate
contains the exact Phase 532 policy identity.  It independently rebuilds the
corpus/gold union, checks the 57 single-word target signatures, preserves the
unchanged conflict review, and removes only the superseded atomic ``lulu``
strict pin.  The bounded ``ritma gimnastiko`` expression is intentionally not
flattened into a single-word union case: the full-runtime Phase 532 signature
gate proves its two tokens and literal separator.  The seven ordinary repairs
are owned by the managed morphology settings, not copied into the strict-exact
ledger.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from atomic_json import atomic_file_copy, atomic_json_dump
from adopt_no_worsening_reference_candidate import (
    atomic_compact_entries_dump,
    preserve_tracked_entry_order,
    typed_signature,
)
import build_phase532_ruby_policy_review as phase532_builder
import build_phase532_authority_carry_forward as phase532_carry_builder
from gold_snapshot import consistent_snapshot
import no_worsening_audit as audit
import phase532_authority_carry_forward as phase532_carry
import phase532_ruby_policy as phase532_policy


HERE = Path(__file__).resolve().parent
SCOPE_PATH = HERE / "_no_worsening_scope_manifest.json"
CONFLICT_PATH = HERE / "_no_worsening_reference_conflicts.json"
STRICT_PATH = HERE / "_strict_gold_reference_fixes.json"
FAKE_REFERENCE_PATH = HERE / "_fake_coarse_reference_manifest.json"

PHASE513_GOLD_SHA256 = phase532_policy.BASELINE_LEARNER_SHA256
PHASE513_REFERENCE_SHA256 = (
    "EB81086916F181D657D683EC5E983C5E0D3FE287E71AA9D059ABA98D1A33E357"
)
PHASE513_PROJECTION_SHA256 = (
    "361505F0B7CE0966085089346F8619F13A09D1DC9D3536408CECB12BBEB35444"
)
UNCHANGED_CONFLICTS_SHA256 = (
    "16FD7BFCF7C1FC1840400FC4D09B83BCA96B987971C12C5BDE1A5D6A5D42404E"
)
UNCHANGED_CONFLICT_ENTRIES_SHA256 = (
    "C836888CA14AE8006209A441EAB0EEFF3DD394E3317CC06A4FBA379E5D03E7BE"
)
PHASE513_STRICT_ENTRIES_SHA256 = (
    "61B497E12602D03DF51FA82ACC49653070476E81216FCB9733FC40CAB7A75AAA"
)
PHASE532_STRICT_ENTRIES_SHA256 = (
    "CA736E47CEAC5F128FFB491A976C930C0B37895D498ECF7656A9AC17F2C3B017"
)
PHASE532_REFERENCE_SOURCE = "gold_phase532_selected_ruby_policy"
PHASE532_CASE_COUNT = 68524
PHASE532_SURFACE_COUNT = 68435
PHASE532_REFERENCE_SHA256 = (
    "308121D186957A792073F1620C5A4E5EA80D3B7EAA87DFE39573E05A2FE822A9"
)
PHASE532_PROJECTION_SHA256 = (
    "75AC6732AACD145F91EE7866738E57D073A998F1634AADA9D28CCFE3FBCAD3D6"
)
PHASE532_CANDIDATE_FILE_SHA256 = (
    "7DE0A31F6BD455EDB5E8730284E6B8EB04A5557BACE4BD5B719313DE67182C92"
)


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def validate_candidate(candidate: dict, expected_gold_sha256: str):
    projection = candidate.get("projection", {})
    scope_candidate = candidate.get("scope_manifest_candidate", {})
    conflicts = candidate.get("conflicts", [])
    gold = projection.get("gold", {})
    fake_reference = gold.get("fake_coarse_reference", {})
    expected_policy = phase532_policy.review_identity()
    reference_sha256 = projection.get("reference_sha256", "")
    if (
        expected_gold_sha256.upper()
        != phase532_policy.CANDIDATE_LEARNER_SHA256
        or projection.get("schema_version")
        != audit.REFERENCE_SCHEMA_VERSION
        or projection.get("phase532_ruby_policy") != expected_policy
        or projection.get("phase532_authority_carry_forward")
        != phase532_carry.review_identity()
        or gold.get("sha256") != phase532_policy.CANDIDATE_LEARNER_SHA256
        or gold.get("lines") != phase532_builder.EXPECTED_MASTER_LINES
        or fake_reference.get("sha256")
        != phase532_policy.CANDIDATE_MANIFEST_SHA256
        or fake_reference.get("entries_sha256")
        != phase532_policy.CANDIDATE_MANIFEST_ENTRIES_SHA256
        or fake_reference.get("academic_sha256")
        != phase532_policy.CANDIDATE_ACADEMIC_SHA256
        or projection.get("case_count") != PHASE532_CASE_COUNT
        or projection.get("surface_count") != PHASE532_SURFACE_COUNT
        or reference_sha256 != PHASE532_REFERENCE_SHA256
        or set(scope_candidate) != {
            "manifest_schema_version", "projection_sha256", "expected",
        }
        or scope_candidate.get("manifest_schema_version") != 1
        or scope_candidate.get("expected") != projection
        or scope_candidate.get("projection_sha256")
        != PHASE532_PROJECTION_SHA256
        or audit.stable_json_sha256(projection)
        != PHASE532_PROJECTION_SHA256
        or not isinstance(conflicts, list)
        or len(conflicts) != 89
        or projection.get("reference_conflict_count") != 89
        or projection.get("reference_conflicts_sha256")
        != UNCHANGED_CONFLICTS_SHA256
        or audit.stable_json_sha256(conflicts)
        != UNCHANGED_CONFLICTS_SHA256
    ):
        raise ValueError("Phase 532 references-only candidate identity changed")
    return projection, scope_candidate, conflicts


def validate_current_scope(current: dict, scope_candidate: dict) -> str:
    """Accept only tracked Phase 513 or an exactly idempotent adoption."""
    if current == scope_candidate:
        return "already_adopted"
    expected = current.get("expected", {})
    if (
        set(current) != {
            "manifest_schema_version", "projection_sha256", "expected",
        }
        or current.get("manifest_schema_version") != 1
        or current.get("projection_sha256") != PHASE513_PROJECTION_SHA256
        or audit.stable_json_sha256(expected) != PHASE513_PROJECTION_SHA256
        or expected.get("gold", {}).get("sha256") != PHASE513_GOLD_SHA256
        or expected.get("reference_sha256") != PHASE513_REFERENCE_SHA256
        or expected.get("reference_conflict_count") != 89
        or expected.get("reference_conflicts_sha256")
        != UNCHANGED_CONFLICTS_SHA256
    ):
        raise ValueError("unexpected pre-Phase532 scope identity")
    candidate_expected = scope_candidate["expected"]
    for unchanged_key in ("corpus", "corpus_repository", "place_manifest"):
        if candidate_expected.get(unchanged_key) != expected.get(unchanged_key):
            raise ValueError(
                f"Phase 532 candidate changed {unchanged_key!r}"
            )
    return "phase513"


def rebuild_conflict_manifest(conflicts: list[dict]) -> dict:
    """Require the already reviewed conflict set and options to stay exact."""
    current = json.loads(CONFLICT_PATH.read_text(encoding="utf-8"))
    entries = current.get("entries", [])
    if (
        current.get("manifest_schema_version") != 1
        or current.get("reference_schema_version")
        != audit.REFERENCE_SCHEMA_VERSION
        or current.get("raw_conflicts_sha256")
        != UNCHANGED_CONFLICTS_SHA256
        or compact_sha256(entries) != UNCHANGED_CONFLICT_ENTRIES_SHA256
        or len(entries) != 89
        or audit.stable_json_sha256(conflicts)
        != UNCHANGED_CONFLICTS_SHA256
    ):
        raise ValueError("Phase 532 conflict identity requires separate review")
    reviewed_by_surface = {entry["surface"]: entry for entry in entries}
    candidate_by_surface = {entry["surface"]: entry for entry in conflicts}
    if (
        len(reviewed_by_surface) != len(entries)
        or len(candidate_by_surface) != len(conflicts)
        or set(candidate_by_surface) != set(reviewed_by_surface)
    ):
        raise ValueError("Phase 532 conflict membership changed")
    for surface, conflict in candidate_by_surface.items():
        if reviewed_by_surface[surface].get("options") != conflict.get("options"):
            raise ValueError(
                f"Phase 532 conflict options changed: {surface!r}"
            )
    return current


def ordinary_selected_policy_targets() -> dict[str, str]:
    """Return the 57 targets representable by ordinary union cases."""
    selected = phase532_policy.ordinary_reference_targets()
    expressions = phase532_policy.selected_ruby_expressions()
    multiword = [
        expression for expression in expressions.values()
        if expression["kind"] == "bounded_multiword"
    ]
    if len(selected) != 57 or multiword != [phase532_policy.MULTIWORD_EXPRESSION]:
        raise ValueError("Phase 532 ordinary/multiword proof scope drift")
    return selected


def validate_phase532_reference_cases(cases: dict) -> None:
    """Prove all 57 ordinary targets in the rebuilt single-word authority.

    ``ritma gimnastiko`` is not an ordinary case: its exact R/L signature is
    proved pre- and post-regeneration by ``phase532_runtime_signature_gate``.
    """
    atomic_hyphens, _identity = audit.load_atomic_hyphen_review()
    by_surface = {}
    for case in cases.values():
        by_surface.setdefault(case["surface"], []).append(case)
    for surface, target in ordinary_selected_policy_targets().items():
        normalized_surface = audit.canonical(surface)
        atomic_pieces = audit.reviewed_atomic_hyphen_pieces(
            normalized_surface, target, atomic_hyphens,
        )
        wanted_signature = audit.expected_signature(target, atomic_pieces)
        matching = [
            case for case in by_surface.get(normalized_surface, [])
            if case["signature"] == wanted_signature
            and case.get("sources", {}).get(PHASE532_REFERENCE_SOURCE) == 1
        ]
        if len(matching) != 1:
            raise ValueError(
                "Phase 532 selected Ruby reference is absent/ambiguous: "
                f"{surface!r} -> {target!r}"
            )


def rebind_strict_ledger(
    strict: dict, projection: dict, available: set,
) -> dict:
    entries = strict.get("entries", [])
    if (
        strict.get("schema_version") != 1
        or strict.get("reference_schema_version")
        != audit.REFERENCE_SCHEMA_VERSION
        or len(entries) != strict.get("expected_entries")
        or compact_sha256(entries) != strict.get("entries_sha256")
    ):
        raise ValueError("strict gold-reference fix manifest identity mismatch")
    pre_phase532 = (
        strict.get("gold_sha256") == PHASE513_GOLD_SHA256
        and strict.get("reference_sha256") == PHASE513_REFERENCE_SHA256
        and len(entries) == 933
        and strict.get("entries_sha256")
        == PHASE513_STRICT_ENTRIES_SHA256
    )
    already_adopted = (
        strict.get("gold_sha256") == projection["gold"]["sha256"]
        and strict.get("reference_sha256") == projection["reference_sha256"]
        and len(entries) == 932
    )
    if not (pre_phase532 or already_adopted):
        raise ValueError("unexpected pre-Phase532 strict identity")

    superseded = phase532_policy.strict_supersessions()
    by_word = {}
    for entry in entries:
        by_word.setdefault(entry["w"], []).append(entry)
    for word, expected_entry in superseded.items():
        matches = by_word.get(word, [])
        if len(matches) > 1 or (matches and matches[0] != expected_entry):
            raise ValueError(f"Phase 532 strict supersession drift: {word!r}")
        if pre_phase532 and len(matches) != 1:
            raise ValueError(f"Phase 532 strict supersession missing: {word!r}")
        if already_adopted and matches:
            raise ValueError(f"adopted strict supersession returned: {word!r}")
    entries = [entry for entry in entries if entry["w"] not in superseded]
    entries = preserve_tracked_entry_order(entries)
    if len(entries) != 932 or len({entry["w"] for entry in entries}) != 932:
        raise ValueError("Phase 532 strict ledger must contain 932 unique rows")
    for entry in entries:
        signature = typed_signature(entry)
        if signature[0] != entry["w"] or (entry["w"], signature) not in available:
            raise ValueError(
                f"strict exact fix is absent from Phase 532 union: {entry!r}"
            )
    entries_sha256 = compact_sha256(entries)
    if entries_sha256 != PHASE532_STRICT_ENTRIES_SHA256:
        raise ValueError(
            "Phase 532 strict removal changed more than lulu: "
            f"{entries_sha256}"
        )
    strict["entries"] = entries
    strict.update({
        "reference_schema_version": audit.REFERENCE_SCHEMA_VERSION,
        "gold_sha256": projection["gold"]["sha256"],
        "reference_sha256": projection["reference_sha256"],
        "expected_entries": len(entries),
        "entries_sha256": entries_sha256,
    })
    return strict


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--expected-gold-sha256", required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    candidate_raw = args.candidate.read_bytes()
    candidate_sha256 = hashlib.sha256(candidate_raw).hexdigest().upper()
    if candidate_sha256 != PHASE532_CANDIDATE_FILE_SHA256:
        raise ValueError("Phase 532 candidate file identity changed")
    tracked_paths = (
        SCOPE_PATH, CONFLICT_PATH, STRICT_PATH, FAKE_REFERENCE_PATH,
    )
    tracked_hashes_at_start = {
        path: hashlib.sha256(path.read_bytes()).hexdigest().upper()
        for path in tracked_paths
    }
    candidate = json.loads(candidate_raw.decode("utf-8"))
    projection, scope_candidate, conflicts = validate_candidate(
        candidate, args.expected_gold_sha256,
    )
    source_review = phase532_builder.validate_frozen_closure(
        args.baseline_dir, args.candidate_dir, args.candidate_manifest,
    )
    carry_review = phase532_carry_builder.validate_frozen_closure(
        args.baseline_dir, args.candidate_dir, args.candidate_manifest,
    )
    reference_review = audit.load_phase532_reference_review(
        args.candidate_manifest,
    )
    if (
        source_review["review_identity"]
        != projection["phase532_ruby_policy"]
        or reference_review["identity"]
        != projection["phase532_ruby_policy"]
    ):
        raise ValueError("candidate/source Phase 532 policy identities differ")

    current_scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    prior_state = validate_current_scope(current_scope, scope_candidate)
    if (
        tracked_hashes_at_start[FAKE_REFERENCE_PATH]
        not in {
            audit.PHASE513_FAKE_COARSE_MANIFEST_SHA256,
            phase532_policy.CANDIDATE_MANIFEST_SHA256,
        }
    ):
        raise ValueError(
            "tracked fake/coarse manifest does not match adoption state"
        )
    conflict_manifest = rebuild_conflict_manifest(conflicts)

    gold_raw, gold_identity = consistent_snapshot(args.gold.resolve())
    cases = {}
    scope = {
        "corpus": audit.corpus_cases(cases, args.corpus.resolve()),
        "corpus_repository": audit.git_repo_state(args.corpus.resolve()),
        "place_manifest": audit.place_cases(cases),
        "gold": audit.gold_cases(
            cases, args.gold.resolve(), gold_raw, gold_identity,
            args.expected_gold_sha256,
            fake_coarse_manifest_path=args.candidate_manifest,
            phase532_reference_review=reference_review,
        ),
    }
    validate_phase532_reference_cases(cases)
    surfaces = sorted({case["surface"] for case in cases.values()})
    rebuilt_conflicts = audit.reference_conflicts(cases)
    rebuilt_projection = audit.scope_projection(
        scope, cases, surfaces, rebuilt_conflicts,
        phase532_policy_identity=reference_review["identity"],
        phase532_carry_forward_identity=carry_review["review_identity"],
    )
    if rebuilt_projection != projection or rebuilt_conflicts != conflicts:
        raise ValueError("candidate does not match rebuilt Phase 532 references")

    available = {
        (case["surface"], case["signature"]) for case in cases.values()
    }
    strict_before = json.loads(STRICT_PATH.read_text(encoding="utf-8"))
    strict_was_phase513 = (
        strict_before.get("gold_sha256") == PHASE513_GOLD_SHA256
        and strict_before.get("reference_sha256")
        == PHASE513_REFERENCE_SHA256
        and strict_before.get("expected_entries") == 933
        and strict_before.get("entries_sha256")
        == PHASE513_STRICT_ENTRIES_SHA256
    )
    strict_was_phase532 = (
        strict_before.get("gold_sha256")
        == projection["gold"]["sha256"]
        and strict_before.get("reference_sha256")
        == projection["reference_sha256"]
        and strict_before.get("expected_entries") == 932
        and strict_before.get("entries_sha256")
        == PHASE532_STRICT_ENTRIES_SHA256
    )
    strict = rebind_strict_ledger(strict_before, projection, available)
    tracked_fake_is_phase513 = (
        tracked_hashes_at_start[FAKE_REFERENCE_PATH]
        == audit.PHASE513_FAKE_COARSE_MANIFEST_SHA256
    )
    tracked_fake_is_phase532 = (
        tracked_hashes_at_start[FAKE_REFERENCE_PATH]
        == phase532_policy.CANDIDATE_MANIFEST_SHA256
    )
    if prior_state == "already_adopted":
        if not (tracked_fake_is_phase532 and strict_was_phase532):
            raise ValueError("adopted Phase 532 tracked state is incomplete")
    elif not (
        (tracked_fake_is_phase513 or tracked_fake_is_phase532)
        and (strict_was_phase513 or strict_was_phase532)
    ):
        raise ValueError("invalid recoverable Phase 532 adoption state")
    elif tracked_fake_is_phase532 or strict_was_phase532:
        # A process interruption may occur between the three atomic replaces.
        # Exact candidate identities are safe to resume; foreign/half-edited
        # content was rejected above.
        prior_state = "phase513_partial_exact"
    corpus_at_end = audit.corpus_content_fingerprint(args.corpus.resolve())
    corpus_repo_at_end = audit.git_repo_state(args.corpus.resolve())
    if (
        corpus_at_end.get("files") != projection["corpus"]["files"]
        or corpus_at_end.get("sha256")
        != projection["corpus"]["content_sha256"]
        or corpus_repo_at_end != projection["corpus_repository"]
    ):
        raise ValueError("Phase 532 corpus changed during adoption")
    if (
        hashlib.sha256(args.gold.read_bytes()).hexdigest().upper()
        != phase532_policy.CANDIDATE_LEARNER_SHA256
    ):
        raise ValueError("Phase 532 gold changed during adoption")
    end_source_review = phase532_builder.validate_frozen_closure(
        args.baseline_dir, args.candidate_dir, args.candidate_manifest,
    )
    if end_source_review != source_review:
        raise ValueError("Phase 532 frozen source review changed during adoption")
    if phase532_carry_builder.validate_frozen_closure(
        args.baseline_dir, args.candidate_dir, args.candidate_manifest,
    ) != carry_review:
        raise ValueError("Phase 532 carry-forward review changed during adoption")
    if audit.load_phase532_reference_review(
        args.candidate_manifest,
    )["identity"] != reference_review["identity"]:
        raise ValueError("Phase 532 reference review changed during adoption")
    if hashlib.sha256(args.candidate.read_bytes()).hexdigest().upper() != candidate_sha256:
        raise ValueError("Phase 532 candidate changed during adoption")
    if args.write:
        tracked_hashes_before_write = {
            path: hashlib.sha256(path.read_bytes()).hexdigest().upper()
            for path in tracked_paths
        }
        if tracked_hashes_before_write != tracked_hashes_at_start:
            raise ValueError(
                "tracked adoption files changed before the first write"
            )
        # The scope is the commit marker, so install the exact referenced
        # authority and strict ledger first, then expose the new scope last.
        # The unchanged conflict ledger is deliberately not rewritten.
        staged_fake_path = FAKE_REFERENCE_PATH.with_name(
            FAKE_REFERENCE_PATH.name + ".phase532_staged"
        )
        atomic_file_copy(args.candidate_manifest, staged_fake_path)
        if (
            hashlib.sha256(staged_fake_path.read_bytes()).hexdigest().upper()
            != phase532_policy.CANDIDATE_MANIFEST_SHA256
        ):
            staged_fake_path.unlink(missing_ok=True)
            raise ValueError("Phase 532 staged fake manifest identity changed")
        os.replace(staged_fake_path, FAKE_REFERENCE_PATH)
        if (
            hashlib.sha256(FAKE_REFERENCE_PATH.read_bytes()).hexdigest().upper()
            != phase532_policy.CANDIDATE_MANIFEST_SHA256
        ):
            raise ValueError("Phase 532 fake manifest install failed")
        atomic_compact_entries_dump(STRICT_PATH, strict)
        if json.loads(STRICT_PATH.read_text(encoding="utf-8")) != strict:
            raise ValueError("Phase 532 strict ledger install failed")
        atomic_json_dump(SCOPE_PATH, scope_candidate, indent=1)
        if (
            hashlib.sha256(FAKE_REFERENCE_PATH.read_bytes()).hexdigest().upper()
            != phase532_policy.CANDIDATE_MANIFEST_SHA256
            or json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
            != scope_candidate
            or json.loads(STRICT_PATH.read_text(encoding="utf-8"))
            != strict
            or hashlib.sha256(CONFLICT_PATH.read_bytes()).hexdigest().upper()
            != tracked_hashes_at_start[CONFLICT_PATH]
        ):
            raise ValueError("Phase 532 atomic adoption postcondition failed")
    print(json.dumps({
        "mode": "write" if args.write else "check",
        "prior_state": prior_state,
        "candidate_sha256": candidate_sha256,
        "projection_sha256": scope_candidate["projection_sha256"],
        "gold_sha256": projection["gold"]["sha256"],
        "case_count": projection["case_count"],
        "surface_count": projection["surface_count"],
        "conflicts": len(conflicts),
        "strict_entries": strict["expected_entries"],
        "strict_entries_sha256": strict["entries_sha256"],
        "phase532_review_identity": source_review["review_identity"],
        "phase532_carry_forward_identity": carry_review["review_identity"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
