# -*- coding: utf-8 -*-
"""Adopt the pinned Phase 513 Ruby reference delta without bulk promotion.

Phase 513 adds nine fake-marker rows and deepens two existing fake rows.  This
adopter leaves all eleven on the Kanji/review queue, retains the twenty-one
explicit Phase 511 Ruby decisions (including the closed sugar/deoksi semantic
review), and adds only the ordinary paired decomposition ``nen -> ne/n`` from
the Phase 513 delta.  It never promotes the remaining fake rows in bulk.

The migration is intentionally reproducible directly from the tracked app
main state; no unpublished Phase 511/513 intermediate manifest is required.
"""
import argparse
import hashlib
import json
from pathlib import Path

from atomic_json import atomic_json_dump
from adopt_no_worsening_reference_candidate import (
    atomic_compact_entries_dump,
    preserve_tracked_entry_order,
    typed_signature,
)
import build_fake_coarse_phase511_transition_review as phase_builder
from gold_snapshot import consistent_snapshot
import no_worsening_audit as audit


HERE = Path(__file__).resolve().parent
SCOPE_PATH = HERE / "_no_worsening_scope_manifest.json"
CONFLICT_PATH = HERE / "_no_worsening_reference_conflicts.json"
STRICT_PATH = HERE / "_strict_gold_reference_fixes.json"
PHASE_PATH = HERE / "_fake_coarse_phase511_transition_review.json"

OLD_REFERENCE_SHA256 = (
    "F7C4755D70215A4DB78976A1AAFFA801B0374AE8B3248D1BADB480911F741B29"
)
OLD_GOLD_SHA256 = (
    "5E972C8AC9D8A8CA00097720C455871A871EE4D8F25A9F4B11A28FA30A01A1A0"
)
OLD_CONFLICTS_SHA256 = (
    "78600D1BE475F5BC7124069174BBAC66DB8EA6B6A8A943E1D032DC453AD17986"
)
OLD_ARENO_CONFLICT_SHA256 = (
    "03EC8E7113F58498CD5DDD7B8C9532725B57A248F4655C673BC6C29E4BE5F183"
)
OLD_STRICT_ENTRIES_SHA256 = (
    "CB85DE9D401F1476D5DFC7A2D7BE5E0816D34CA3E00C37ADF82EB9652CB52EE7"
)
OLD_PROJECTION_SHA256 = (
    "2055924C6E8FC7D65F65C20E60BF594A8A20D3905020A1FC6E4DD800CCD07969"
)
INTERMEDIATE_REFERENCE_SHA256 = (
    "A2E7D90A1528293ADE5DAFDE81342EF3793811338D6D85F67D5955D730556F6A"
)
INTERMEDIATE_PROJECTION_SHA256 = (
    "FD6D8E007904BA26786D802C4DF8FF18E483CBF66AD9B75FDCC64082617CA600"
)
OLD_CONFLICT_ENTRIES_SHA256 = (
    "F0DED91E5D83410AC3F181B03315DD20D7B22175403687B064FA33B1A6C0495D"
)
EXPECTED_CONFLICT_ENTRIES_SHA256 = (
    "C836888CA14AE8006209A441EAB0EEFF3DD394E3317CC06A4FBA379E5D03E7BE"
)
EXPECTED_GOLD_SHA256 = (
    "1435F5B1CD1B0BB8224521A8262E3CA740B07B7523E805545A4E3CA7447A286C"
)
EXPECTED_REFERENCE_SHA256 = (
    "EB81086916F181D657D683EC5E983C5E0D3FE287E71AA9D059ABA98D1A33E357"
)
EXPECTED_PROJECTION_SHA256 = (
    "361505F0B7CE0966085089346F8619F13A09D1DC9D3536408CECB12BBEB35444"
)
EXPECTED_CONFLICTS_SHA256 = (
    "16FD7BFCF7C1FC1840400FC4D09B83BCA96B987971C12C5BDE1A5D6A5D42404E"
)
EXPECTED_STRICT_ENTRIES_SHA256 = (
    "61B497E12602D03DF51FA82ACC49653070476E81216FCB9733FC40CAB7A75AAA"
)
INTERMEDIATE_STRICT_ENTRIES_SHA256 = (
    "BE3050609AABADFA47119B0E1D5A4AA88121E4A5F2AD075824F2DAC1C55E705D"
)


def compact_sha256(value):
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def validate_candidate(candidate, expected_gold):
    projection = candidate.get("projection", {})
    scope_candidate = candidate.get("scope_manifest_candidate", {})
    conflicts = candidate.get("conflicts", [])
    if (
        expected_gold.upper() != EXPECTED_GOLD_SHA256
        or projection.get("schema_version") != audit.REFERENCE_SCHEMA_VERSION
        or projection.get("gold", {}).get("sha256") != EXPECTED_GOLD_SHA256
        or projection.get("reference_sha256") != EXPECTED_REFERENCE_SHA256
        or projection.get("case_count") != 68516
        or projection.get("surface_count") != 68427
        or projection.get("reference_conflict_count") != 89
        or projection.get("reference_conflicts_sha256")
        != EXPECTED_CONFLICTS_SHA256
        or set(scope_candidate) != {
            "manifest_schema_version", "projection_sha256", "expected",
        }
        or scope_candidate.get("manifest_schema_version") != 1
        or scope_candidate.get("expected") != projection
        or scope_candidate.get("projection_sha256")
        != EXPECTED_PROJECTION_SHA256
        or audit.stable_json_sha256(projection)
        != EXPECTED_PROJECTION_SHA256
        or audit.stable_json_sha256(conflicts) != EXPECTED_CONFLICTS_SHA256
    ):
        raise ValueError("Phase 513 references-only candidate identity changed")
    return projection, scope_candidate, conflicts


def rebuild_conflict_manifest(conflicts):
    current = json.loads(CONFLICT_PATH.read_text(encoding="utf-8"))
    current_by_surface = {
        entry["surface"]: entry for entry in current.get("entries", [])
    }
    candidate_by_surface = {
        entry["surface"]: entry for entry in conflicts
    }
    removed = set(current_by_surface) - set(candidate_by_surface)
    added = set(candidate_by_surface) - set(current_by_surface)
    current_conflicts_sha256 = current.get("raw_conflicts_sha256")
    current_entries_sha256 = compact_sha256(current.get("entries", []))
    if (
        current.get("manifest_schema_version") != 1
        or current.get("reference_schema_version")
        != audit.REFERENCE_SCHEMA_VERSION
    ):
        raise ValueError("pre-adoption conflict manifest schema drift")
    if current_conflicts_sha256 == OLD_CONFLICTS_SHA256:
        old_areno = current_by_surface.get("areno")
        if (
            removed != {"areno"}
            or added
            or old_areno is None
            or compact_sha256(old_areno) != OLD_ARENO_CONFLICT_SHA256
            or current_entries_sha256 != OLD_CONFLICT_ENTRIES_SHA256
        ):
            raise ValueError(
                "tracked-main conflict transition drift: "
                f"removed={sorted(removed)!r}, added={sorted(added)!r}"
            )
    elif current_conflicts_sha256 == EXPECTED_CONFLICTS_SHA256:
        if (
            removed
            or added
            or current_entries_sha256
            != EXPECTED_CONFLICT_ENTRIES_SHA256
        ):
            raise ValueError(
                "already-adopted conflict membership drift: "
                f"removed={sorted(removed)!r}, added={sorted(added)!r}"
            )
    else:
        raise ValueError(
            "unexpected pre-adoption conflict identity: "
            f"{current_conflicts_sha256!r}"
        )
    reviewed_entries = []
    for conflict in conflicts:
        old = current_by_surface.get(conflict["surface"])
        if old is None or old.get("options") != conflict.get("options"):
            raise ValueError(
                f"existing conflict drift: {conflict['surface']!r}"
            )
        reviewed = dict(old)
        reviewed["options"] = conflict["options"]
        reviewed_entries.append(reviewed)
    if [entry["surface"] for entry in reviewed_entries] != sorted(
        entry["surface"] for entry in reviewed_entries
    ):
        raise ValueError("reviewed conflicts are no longer surface-sorted")
    return {
        "manifest_schema_version": 1,
        "reference_schema_version": audit.REFERENCE_SCHEMA_VERSION,
        "raw_conflicts_sha256": EXPECTED_CONFLICTS_SHA256,
        "entries": reviewed_entries,
    }


def validate_strict_input(strict):
    entries = strict.get("entries", [])
    identity = {
        "schema_version": strict.get("schema_version"),
        "reference_schema_version": strict.get("reference_schema_version"),
        "gold_sha256": strict.get("gold_sha256"),
        "reference_sha256": strict.get("reference_sha256"),
        "declared_entries": strict.get("expected_entries"),
        "declared_entries_sha256": strict.get("entries_sha256"),
        "entries": len(entries),
        "entries_sha256": compact_sha256(entries),
    }
    tracked_main = {
        "schema_version": 1,
        "reference_schema_version": audit.REFERENCE_SCHEMA_VERSION,
        "gold_sha256": OLD_GOLD_SHA256,
        "reference_sha256": OLD_REFERENCE_SHA256,
        "declared_entries": 914,
        "declared_entries_sha256": OLD_STRICT_ENTRIES_SHA256,
        "entries": 914,
        "entries_sha256": OLD_STRICT_ENTRIES_SHA256,
    }
    intermediate = {
        "schema_version": 1,
        "reference_schema_version": audit.REFERENCE_SCHEMA_VERSION,
        "gold_sha256": EXPECTED_GOLD_SHA256,
        "reference_sha256": INTERMEDIATE_REFERENCE_SHA256,
        "declared_entries": 918,
        "declared_entries_sha256": INTERMEDIATE_STRICT_ENTRIES_SHA256,
        "entries": 918,
        "entries_sha256": INTERMEDIATE_STRICT_ENTRIES_SHA256,
    }
    adopted = {
        "schema_version": 1,
        "reference_schema_version": audit.REFERENCE_SCHEMA_VERSION,
        "gold_sha256": EXPECTED_GOLD_SHA256,
        "reference_sha256": EXPECTED_REFERENCE_SHA256,
        "declared_entries": 933,
        "declared_entries_sha256": EXPECTED_STRICT_ENTRIES_SHA256,
        "entries": 933,
        "entries_sha256": EXPECTED_STRICT_ENTRIES_SHA256,
    }
    if identity not in (tracked_main, intermediate, adopted):
        raise ValueError(f"unexpected pre-adoption strict identity: {identity!r}")


def rebind_strict_ledger(strict, phase, available):
    phase_by_surface = {
        entry["surface"]: entry for entry in phase["entries"]
    }
    if set(phase_by_surface) != {
        "arabinozo", "bifenilo", "celulozo", "laktozo",
        "deoksiozo", "deoksiribozo",
        "maltozo", "sakarozo", "amelozo", "deoksi", "fruktozo",
        "kalozo", "ksilozo", "rafinozo", "ribozo", "stakiozo",
        "grenmaltozaĵo", "aldozo", "furanozo", "ketozo", "piranozo",
    }:
        raise ValueError("Phase 511 carried Ruby surface scope changed")
    strict_by_surface = {entry["w"]: entry for entry in strict["entries"]}
    for surface, reviewed in phase_by_surface.items():
        current = strict_by_surface.get(surface)
        old_hash = reviewed.get("supersedes_strict_entry_sha256")
        is_addition = reviewed.get("adds_strict_entry") is True
        desired = {
            "w": surface,
            "target": reviewed["target"],
            "typed_roles": reviewed["typed_roles"],
            "exact_only": True,
            "boundary_only": True,
            "case_sensitive": True,
            "ruby_track_only": True,
        }
        if is_addition:
            if old_hash is not None:
                raise ValueError(
                    f"new semantic entry unexpectedly supersedes strict: {surface!r}"
                )
            if current is None:
                current = {"w": surface}
                strict["entries"].append(current)
                strict_by_surface[surface] = current
            elif current != desired:
                raise ValueError(
                    f"prior semantic strict addition drift: {surface!r}"
                )
        elif surface == "arabinozo":
            if current is not None and not current.get("ruby_track_only"):
                raise ValueError("arabinozo pre-exists outside Phase 511 scope")
            if current is None:
                current = {"w": surface}
                strict["entries"].append(current)
                strict_by_surface[surface] = current
        elif (
            compact_sha256(current) != old_hash
            and not (
                current.get("target") == reviewed["target"]
                and current.get("typed_roles") == reviewed["typed_roles"]
                and current.get("ruby_track_only") is True
            )
        ):
            raise ValueError(f"prior strict entry drift: {surface!r}")
        current.update(desired)
    nen = strict_by_surface.get("nen")
    expected_nen = {
        "w": "nen",
        "target": "ne/n",
        "typed_roles": "RL",
        "exact_only": True,
        "boundary_only": True,
        "case_sensitive": True,
    }
    if nen is None:
        nen = dict(expected_nen)
        strict["entries"].append(nen)
        strict_by_surface["nen"] = nen
    elif nen != expected_nen:
        raise ValueError("prior Phase 513 nen entry drift")

    # Reconstruct the newly added tail in one fixed reviewed order.  Without
    # this normalization, direct tracked-main adoption and idempotent adoption
    # of an earlier intermediate produce different byte identities merely
    # because ``nen`` was appended at a different moment.
    addition_order = [
        entry["surface"] for entry in phase["entries"]
        if entry.get("adds_strict_entry") is True
        or entry["surface"] == "arabinozo"
    ] + ["nen"]
    if len(addition_order) != len(set(addition_order)):
        raise ValueError("Phase 513 strict addition order contains duplicates")
    addition_set = set(addition_order)
    stable_entries = [
        entry for entry in strict["entries"] if entry["w"] not in addition_set
    ]
    if set(strict_by_surface) & addition_set != addition_set:
        raise ValueError("Phase 513 strict addition is missing after rebind")
    stable_entries.extend(strict_by_surface[surface] for surface in addition_order)
    strict["entries"] = preserve_tracked_entry_order(stable_entries)
    if len(strict["entries"]) != 933:
        raise ValueError("Phase 513 strict ledger must contain 933 entries")
    for entry in strict["entries"]:
        signature = typed_signature(entry)
        if signature[0] != entry["w"] or (entry["w"], signature) not in available:
            raise ValueError(
                f"strict exact fix is absent from Phase 513 union: {entry!r}"
            )
    entries_sha256 = compact_sha256(strict["entries"])
    if (
        EXPECTED_STRICT_ENTRIES_SHA256 != "TO_BE_PINNED"
        and entries_sha256 != EXPECTED_STRICT_ENTRIES_SHA256
    ):
        raise ValueError(
            f"Phase 513 strict ledger fingerprint changed: {entries_sha256}"
        )
    strict.update({
        "reference_schema_version": audit.REFERENCE_SCHEMA_VERSION,
        "gold_sha256": EXPECTED_GOLD_SHA256,
        "reference_sha256": EXPECTED_REFERENCE_SHA256,
        "expected_entries": len(strict["entries"]),
        "entries_sha256": entries_sha256,
    })
    return strict


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--expected-gold-sha256", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    projection, scope_candidate, conflicts = validate_candidate(
        candidate, args.expected_gold_sha256,
    )
    phase = json.loads(PHASE_PATH.read_text(encoding="utf-8"))
    phase_builder.validate(phase)

    current_scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    current_reference = current_scope.get("expected", {}).get(
        "reference_sha256"
    )
    if current_reference not in {
        OLD_REFERENCE_SHA256, INTERMEDIATE_REFERENCE_SHA256,
        EXPECTED_REFERENCE_SHA256,
    }:
        raise ValueError("unexpected pre-adoption reference identity")
    if current_reference == OLD_REFERENCE_SHA256:
        current_expected = current_scope.get("expected", {})
        if (
            set(current_scope) != {
                "manifest_schema_version", "projection_sha256", "expected",
            }
            or current_scope.get("manifest_schema_version") != 1
            or current_scope.get("projection_sha256")
            != OLD_PROJECTION_SHA256
            or audit.stable_json_sha256(current_expected)
            != OLD_PROJECTION_SHA256
            or current_expected.get("gold", {}).get("sha256")
            != OLD_GOLD_SHA256
            or current_expected.get("reference_conflict_count") != 90
            or current_expected.get("reference_conflicts_sha256")
            != OLD_CONFLICTS_SHA256
        ):
            raise ValueError("tracked-main scope manifest identity drift")
    if current_reference == INTERMEDIATE_REFERENCE_SHA256:
        current_expected = current_scope.get("expected", {})
        if (
            set(current_scope) != {
                "manifest_schema_version", "projection_sha256", "expected",
            }
            or current_scope.get("manifest_schema_version") != 1
            or current_scope.get("projection_sha256")
            != INTERMEDIATE_PROJECTION_SHA256
            or audit.stable_json_sha256(current_expected)
            != INTERMEDIATE_PROJECTION_SHA256
            or current_expected.get("gold", {}).get("sha256")
            != EXPECTED_GOLD_SHA256
            or current_expected.get("reference_conflict_count") != 89
            or current_expected.get("reference_conflicts_sha256")
            != EXPECTED_CONFLICTS_SHA256
        ):
            raise ValueError("intermediate scope manifest identity drift")
    if (
        current_reference == EXPECTED_REFERENCE_SHA256
        and current_scope != scope_candidate
    ):
        raise ValueError("already-adopted scope manifest differs from candidate")
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
        ),
    }
    surfaces = sorted({case["surface"] for case in cases.values()})
    rebuilt_conflicts = audit.reference_conflicts(cases)
    rebuilt_projection = audit.scope_projection(
        scope, cases, surfaces, rebuilt_conflicts,
    )
    if rebuilt_projection != projection or rebuilt_conflicts != conflicts:
        raise ValueError("candidate does not match rebuilt Phase 513 references")

    available = {
        (case["surface"], case["signature"]) for case in cases.values()
    }
    strict = json.loads(STRICT_PATH.read_text(encoding="utf-8"))
    validate_strict_input(strict)
    strict = rebind_strict_ledger(strict, phase, available)
    if args.write:
        atomic_json_dump(SCOPE_PATH, scope_candidate, indent=1)
        atomic_json_dump(CONFLICT_PATH, conflict_manifest, indent=1)
        atomic_compact_entries_dump(STRICT_PATH, strict)
    print(json.dumps({
        "mode": "write" if args.write else "check",
        "projection_sha256": EXPECTED_PROJECTION_SHA256,
        "gold_sha256": EXPECTED_GOLD_SHA256,
        "case_count": projection["case_count"],
        "surface_count": projection["surface_count"],
        "conflicts": len(conflicts),
        "strict_entries": strict["expected_entries"],
        "strict_entries_sha256": strict["entries_sha256"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
