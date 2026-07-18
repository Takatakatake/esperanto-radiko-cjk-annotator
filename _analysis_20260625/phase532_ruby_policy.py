# -*- coding: utf-8 -*-
"""Load and fail-closed validate the frozen Phase 532 Ruby dispositions.

The two committed ledgers partition the complete Phase513 -> Phase532 source
delta.  Unmarked rows select either the reviewed new Ruby boundary or the
already deployed boundary.  Fake/deep rows retain the learner decomposition
for Kanji; Ruby normally selects the paired-academic boundary, while four
explicitly pending rows retain their already deployed learner boundary.
"""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
import unicodedata

from extract_lib import hat_to_circumflex, replace_esperanto_chars


HERE = Path(__file__).resolve().parent
UNMARKED_REVIEW_PATH = HERE / "_phase532_unmarked_ruby_disposition_review.json"
FAKE_TRANSITION_PATH = HERE / "_fake_coarse_phase532_transition_review.json"

PHASE = 532
BASELINE_LEARNER_SHA256 = (
    "1435F5B1CD1B0BB8224521A8262E3CA740B07B7523E805545A4E3CA7447A286C"
)
BASELINE_ACADEMIC_SHA256 = (
    "4C813C48B3C4919601FA51E25B6AA3628A0A6793A39C49F1DDFB22A9112E1A0A"
)
CANDIDATE_LEARNER_SHA256 = (
    "6B403AA30BBCBBA4C9E41A2CF48D1AD2FC1D5A5DB1154CAF1260A361566E3226"
)
CANDIDATE_ACADEMIC_SHA256 = (
    "FE632820E7752A555787C926C0A843CD82B2F79D4177A6D8D1E9622CA96393A5"
)
CANDIDATE_MANIFEST_SHA256 = (
    "5F743A916742BE022EFDEC30D24B5ACA0EB2A9156A2086FBB01740DDC356A060"
)
CANDIDATE_MANIFEST_ENTRIES_SHA256 = (
    "8F823A44A62AFB38321662FB843F52D9E97FB5953962CD5B75406B2F1EBC4368"
)
UNMARKED_REVIEW_ENTRIES_SHA256 = (
    "BDE281D9016972B2896EFF812C706E1355A5C531580FCA23B7F875A70FD238ED"
)
FAKE_TRANSITION_ENTRIES_SHA256 = (
    "B441D2242638A6BD09B6933EC92E078AA0C6EF51104E6559AD5DBD32F1C730F1"
)
RETIRED_HISTORICAL_ENTRIES_SHA256 = (
    "0079404290137D0CB0A91D865AF38D5CBFA1AD5195541DF073BFA1B93BCF4E99"
)

UNMARKED_POLICY = (
    "For the frozen Phase 532 source delta, adopt only the four reviewed "
    "ordinary Ruby repairs and otherwise retain the deployed Kyoto-level "
    "Ruby boundary until a separate review changes it."
)
FAKE_TRANSITION_POLICY = (
    "Keep the learner fake/deep decomposition available to the Kanji track. "
    "Annotation Ruby uses the paired academic coarse boundary except for "
    "four explicitly pending rows that retain their deployed learner "
    "boundary; only three reviewed ordinary-affix families add productive "
    "Ruby rules."
)
MULTIWORD_EXPRESSION = {
    "kind": "bounded_multiword",
    "surface": "ritma gimnastiko",
    "separator": " ",
    "tokens": [
        {"surface": "ritma", "decomposition": "ritm/a"},
        {"surface": "gimnastiko", "decomposition": "gimnastik/o"},
    ],
}

EXPECTED_UNMARKED_COUNTS = {
    "entries": 23,
    "already_aligned": 2,
    "adopt_shared_ruby_repair": 4,
    "retain_current_granularity_pending": 17,
}
EXPECTED_FAKE_COUNTS = {
    "entries": 35,
    "keep_academic_coarse_for_ruby": 28,
    "adopt_productive_ruby_repair": 3,
    "retain_current_outer_ik_pending": 3,
    "retain_current_missing_parent_translation": 1,
    "retired_historical_entries": 1,
}
EXPECTED_SAFE_TARGETS = {
    "lulu": {"target": "lul/u", "track": "shared", "productive": False},
    "suprenglisi": {
        "target": "supr/e/n/glis/i", "track": "shared", "productive": True,
    },
    "pasivaĵo": {
        "target": "pasiv/aĵ/o", "track": "shared", "productive": True,
    },
    "pasivigi": {
        "target": "pasiv/ig/i", "track": "shared", "productive": True,
    },
    "neologismemo": {
        "target": "neologism/em/o", "track": "ruby", "productive": True,
    },
    "neologismemulo": {
        "target": "neologism/em/ul/o", "track": "ruby", "productive": True,
    },
    "stenografistino": {
        "target": "stenograf/ist/in/o", "track": "ruby", "productive": True,
    },
}
EXPECTED_STRICT_SUPERSESSIONS = {
    "lulu": {
        "w": "lulu",
        "target": "lulu",
        "typed_roles": "R",
        "exact_only": True,
        "boundary_only": True,
        "case_sensitive": True,
    },
}


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def canonical(value: str) -> str:
    return unicodedata.normalize(
        "NFC", replace_esperanto_chars(value, hat_to_circumflex),
    ).replace("’", "'")


def surface_from_decomposition(value: str) -> str:
    return canonical("".join(piece for piece in value.split("/") if piece))


def _validate_header(
    payload: dict, *, expected_counts: dict, expected_keys: set[str],
    expected_policy: str, expected_source_keys: set[str],
) -> None:
    if set(payload) != expected_keys:
        raise ValueError("unsupported Phase 532 Ruby review keys")
    if (
        payload.get("schema_version") != 1
        or payload.get("phase") != PHASE
        or payload.get("candidate_only") is not False
        or payload.get("policy") != expected_policy
        or payload.get("expected_counts") != expected_counts
    ):
        raise ValueError("Phase 532 Ruby review header drift")
    sources = payload.get("sources", {})
    expected_sources = {
        "baseline_learner_sha256": BASELINE_LEARNER_SHA256,
        "baseline_academic_sha256": BASELINE_ACADEMIC_SHA256,
        "candidate_learner_sha256": CANDIDATE_LEARNER_SHA256,
        "candidate_academic_sha256": CANDIDATE_ACADEMIC_SHA256,
    }
    if (
        not isinstance(sources, dict)
        or set(sources) != expected_source_keys
        or any(
            sources.get(key) != value
            for key, value in expected_sources.items()
        )
    ):
        raise ValueError("Phase 532 source identity drift")


def _validate_entries(
    payload: dict, *, expected_counts: dict, expected_sha256: str,
) -> None:
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != expected_counts["entries"]:
        raise ValueError("Phase 532 review entry count drift")
    if (
        payload.get("entries_sha256") != expected_sha256
        or compact_sha256(entries) != expected_sha256
    ):
        raise ValueError("Phase 532 review entry fingerprint drift")
    lines = [entry.get("learner_line") for entry in entries]
    surfaces = [entry.get("surface") for entry in entries]
    if (
        any(not isinstance(line, int) or line < 1 for line in lines)
        or len(lines) != len(set(lines))
        or any(not isinstance(surface, str) or not surface for surface in surfaces)
        or len(surfaces) != len(set(surfaces))
    ):
        raise ValueError("Phase 532 review line/surface identity drift")
    dispositions = collections.Counter(
        entry.get("disposition") for entry in entries
    )
    for disposition, count in expected_counts.items():
        if disposition in {"entries", "retired_historical_entries"}:
            continue
        if dispositions[disposition] != count:
            raise ValueError(
                f"Phase 532 disposition count drift: {disposition!r}"
            )


def validate_policy_payloads(unmarked: dict, fake: dict) -> dict:
    unmarked_keys = {
        "schema_version", "phase", "candidate_only", "policy", "sources",
        "expected_counts", "entries_sha256", "entries",
    }
    _validate_header(
        unmarked, expected_counts=EXPECTED_UNMARKED_COUNTS,
        expected_keys=unmarked_keys,
        expected_policy=UNMARKED_POLICY,
        expected_source_keys={
            "baseline_learner_sha256", "baseline_academic_sha256",
            "candidate_learner_sha256", "candidate_academic_sha256",
        },
    )
    _validate_entries(
        unmarked, expected_counts=EXPECTED_UNMARKED_COUNTS,
        expected_sha256=UNMARKED_REVIEW_ENTRIES_SHA256,
    )
    expected_fake_keys = {
        "schema_version", "phase", "candidate_only", "policy", "sources",
        "expected_counts", "retired_historical_entries_sha256",
        "retired_historical_entries", "entries_sha256", "entries",
    }
    if set(fake) != expected_fake_keys:
        raise ValueError("unsupported Phase 532 fake-transition keys")
    _validate_header(
        fake, expected_counts=EXPECTED_FAKE_COUNTS,
        expected_keys=expected_fake_keys,
        expected_policy=FAKE_TRANSITION_POLICY,
        expected_source_keys={
            "baseline_learner_sha256", "baseline_academic_sha256",
            "candidate_learner_sha256", "candidate_academic_sha256",
            "candidate_manifest_sha256",
            "candidate_manifest_entries_sha256",
        },
    )
    _validate_entries(
        fake, expected_counts=EXPECTED_FAKE_COUNTS,
        expected_sha256=FAKE_TRANSITION_ENTRIES_SHA256,
    )
    sources = fake["sources"]
    if (
        sources.get("candidate_manifest_sha256")
        != CANDIDATE_MANIFEST_SHA256
        or sources.get("candidate_manifest_entries_sha256")
        != CANDIDATE_MANIFEST_ENTRIES_SHA256
    ):
        raise ValueError("Phase 532 candidate manifest identity drift")
    retired = fake.get("retired_historical_entries")
    if (
        not isinstance(retired, list)
        or len(retired) != 1
        or fake.get("retired_historical_entries_sha256")
        != RETIRED_HISTORICAL_ENTRIES_SHA256
        or compact_sha256(retired) != RETIRED_HISTORICAL_ENTRIES_SHA256
        or retired[0] != {
            "learner_line": 2704,
            "surface": "atletiko",
            "historical_coarse_decomposition": "atletik/o",
            "candidate_learner_decomposition": "atlet/ik/o",
            "candidate_academic_decomposition": "atlet/ik/o",
            "disposition": "retire_fake_marker_keep_unmarked_ruby_review",
        }
    ):
        raise ValueError("Phase 532 historical retirement drift")

    safe_targets = {}
    for ledger, entry in (
        *(("unmarked", entry) for entry in unmarked["entries"]),
        *(("fake", entry) for entry in fake["entries"]),
    ):
        if ledger == "unmarked":
            expected_entry_keys = {
                "learner_line", "surface", "selected_ruby_decomposition",
                "disposition", "reason_code",
            }
            if entry.get("disposition") == "adopt_shared_ruby_repair":
                expected_entry_keys.add("setting")
        else:
            expected_entry_keys = {
                "learner_line", "surface", "target", "disposition",
            }
            if entry.get("disposition") == "adopt_productive_ruby_repair":
                expected_entry_keys.add("setting")
        if set(entry) != expected_entry_keys:
            raise ValueError(
                f"Phase 532 {ledger} entry schema drift: {entry!r}"
            )
        selected = entry.get("selected_ruby_decomposition", entry.get("target"))
        if surface_from_decomposition(selected or "") != canonical(entry["surface"]):
            raise ValueError(
                f"Phase 532 target reconstruction drift: {entry!r}"
            )
        setting = entry.get("setting")
        if setting is None:
            continue
        if (
            set(setting) - {
                "target", "track", "productive", "supersedes_strict_target",
            }
            or setting.get("target") != selected
            or setting.get("track") not in {"shared", "ruby"}
            or not isinstance(setting.get("productive"), bool)
        ):
            raise ValueError(f"invalid Phase 532 managed setting: {entry!r}")
        safe_targets[entry["surface"]] = {
            "target": setting["target"],
            "track": setting["track"],
            "productive": setting["productive"],
        }
    if safe_targets != EXPECTED_SAFE_TARGETS:
        raise ValueError("Phase 532 safe-target scope drift")

    unmarked_lines = {entry["learner_line"] for entry in unmarked["entries"]}
    fake_lines = {entry["learner_line"] for entry in fake["entries"]}
    if (
        unmarked_lines & fake_lines
        or len(unmarked_lines | fake_lines) != 58
        or retired[0]["learner_line"] not in unmarked_lines
    ):
        raise ValueError("Phase 532 58-row closed-set partition drift")
    return {
        "unmarked": unmarked,
        "fake": fake,
        "safe_targets": safe_targets,
        "strict_supersessions": dict(EXPECTED_STRICT_SUPERSESSIONS),
    }


def selected_ruby_expressions() -> dict[str, dict]:
    """Return the closed 57-word + one-multiword Ruby expression scope.

    A slash string is sufficient for a single word.  It is not sufficient for
    ``ritma gimnastiko``: treating its internal space as part of one slash
    piece would incorrectly turn ``a gimnastik`` into one ruby span.  Preserve
    that row as a bounded two-token expression so the full-runtime gate can
    prove both word structures and the literal separator independently.
    """
    loaded = load_phase532_policy()
    selected = {}
    for entry in loaded["unmarked"]["entries"]:
        target = entry["selected_ruby_decomposition"]
        selected[entry["surface"]] = target
    for entry in loaded["fake"]["entries"]:
        if entry["surface"] in selected:
            raise ValueError("Phase 532 selected Ruby surface overlapped")
        selected[entry["surface"]] = entry["target"]
    if len(selected) != 58:
        raise ValueError("Phase 532 selected Ruby expression scope is not 58")

    expressions = {}
    for surface, decomposition in selected.items():
        if surface == MULTIWORD_EXPRESSION["surface"]:
            expression = json.loads(json.dumps(
                MULTIWORD_EXPRESSION, ensure_ascii=False,
            ))
            token_surface = expression["separator"].join(
                token["surface"] for token in expression["tokens"]
            )
            token_decomposition = expression["separator"].join(
                token["decomposition"] for token in expression["tokens"]
            )
            if (
                token_surface != surface
                or token_decomposition != decomposition
                or any(
                    surface_from_decomposition(token["decomposition"])
                    != canonical(token["surface"])
                    for token in expression["tokens"]
                )
            ):
                raise ValueError("Phase 532 multiword expression drift")
        else:
            if any(character.isspace() for character in surface + decomposition):
                raise ValueError(
                    f"unreviewed Phase 532 multiword expression: {surface!r}"
                )
            expression = {
                "kind": "word",
                "surface": surface,
                "decomposition": decomposition,
            }
        expressions[surface] = expression
    if collections.Counter(
        expression["kind"] for expression in expressions.values()
    ) != {"word": 57, "bounded_multiword": 1}:
        raise ValueError("Phase 532 word/multiword expression partition drift")
    return expressions


def ordinary_reference_targets() -> dict[str, str]:
    """Return only the 57 targets representable as ordinary union cases.

    The bounded multiword is proved by ``phase532_runtime_signature_gate``;
    forcing it through the single-word no-worsening case representation would
    collapse its token boundary and manufacture a false signature.
    """
    return {
        surface: expression["decomposition"]
        for surface, expression in selected_ruby_expressions().items()
        if expression["kind"] == "word"
    }


def load_phase532_policy() -> dict:
    unmarked = json.loads(UNMARKED_REVIEW_PATH.read_text(encoding="utf-8"))
    fake = json.loads(FAKE_TRANSITION_PATH.read_text(encoding="utf-8"))
    return validate_policy_payloads(unmarked, fake)


def managed_morph_targets() -> dict:
    policy = load_phase532_policy()
    targets = {}
    for surface, reviewed in policy["safe_targets"].items():
        spec = {"target": reviewed["target"]}
        if reviewed["track"] == "ruby":
            spec["ruby_track_only"] = True
        targets[surface] = spec
    return targets


def strict_supersessions() -> dict:
    """Return exact legacy strict rows displaced by reviewed shared rules."""
    policy = load_phase532_policy()
    return {
        surface: dict(entry)
        for surface, entry in policy["strict_supersessions"].items()
    }


def review_identity() -> dict:
    policy = load_phase532_policy()
    expressions = selected_ruby_expressions()
    return {
        "phase": PHASE,
        "candidate_learner_sha256": CANDIDATE_LEARNER_SHA256,
        "candidate_academic_sha256": CANDIDATE_ACADEMIC_SHA256,
        "unmarked_review_sha256": file_sha256(UNMARKED_REVIEW_PATH),
        "unmarked_entries_sha256": policy["unmarked"]["entries_sha256"],
        "unmarked_entries": len(policy["unmarked"]["entries"]),
        "fake_transition_sha256": file_sha256(FAKE_TRANSITION_PATH),
        "fake_transition_entries_sha256": policy["fake"]["entries_sha256"],
        "fake_transition_entries": len(policy["fake"]["entries"]),
        "retired_historical_entries_sha256": policy["fake"][
            "retired_historical_entries_sha256"
        ],
        "retired_historical_entries": len(
            policy["fake"]["retired_historical_entries"]
        ),
        "selected_expression_sha256": compact_sha256(expressions),
        "selected_expressions": len(expressions),
        "ordinary_reference_expressions": sum(
            expression["kind"] == "word"
            for expression in expressions.values()
        ),
        "bounded_multiword_expressions": sum(
            expression["kind"] == "bounded_multiword"
            for expression in expressions.values()
        ),
    }
