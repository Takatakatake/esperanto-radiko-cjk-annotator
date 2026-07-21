# -*- coding: utf-8 -*-
"""Fail-closed loader for the five reviewed Phase 558 Ruby repairs.

This is deliberately a sidecar over the formally adopted Phase 532 state.
It does not repin the moving master, broaden the fake/deep Kanji authority, or
silently change any Phase 532 decision.  Consumers may activate these settings
only after the parent Phase 532 activation gate and this complete five-row
identity have both passed.
"""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

import phase532_ruby_policy as phase532


HERE = Path(__file__).resolve().parent
REVIEW_PATH = HERE / "_phase558_ruby_overlay_review.json"

PHASE_FROM = 532
PHASE_TO = 558
EXPECTED_REVIEW_SHA256 = (
    "90A8070F4BE8CEB97F4B08A6119F68C69BE6D281C2E358F0529E2D353CAEFD26"
)
EXPECTED_ENTRIES_SHA256 = (
    "614C9FBF7435583A64FB8CD673D461FD5E9065589063978B7CEAAEB992EFE67C"
)
EXPECTED_POLICY = (
    "Keep Kyoto-HTML-level coarse annotation Ruby separate from Kanji "
    "fake/deep decomposition. Adopt only five reviewed Phase 558 Ruby "
    "repairs, with identical JA/ZH/KO R/L boundaries and no width-driven "
    "morphological splitting."
)
EXPECTED_SOURCES = {
    "phase532_learner": {
        "bytes": 4372552,
        "lines": 62313,
        "sha256": phase532.CANDIDATE_LEARNER_SHA256,
    },
    "phase532_academic": {
        "bytes": 4277591,
        "lines": 62313,
        "sha256": phase532.CANDIDATE_ACADEMIC_SHA256,
    },
    "phase558_learner": {
        "bytes": 4373188,
        "lines": 62313,
        "sha256": (
            "21D8B88C79D8D1E45A23CF9987006688EB0308084652AE50FFA2ED337215E4D4"
        ),
    },
    "phase558_academic": {
        "bytes": 4277592,
        "lines": 62313,
        "sha256": (
            "6BAF43D0A2981B0ED48A576178991B48A33AF9AFCA9795D8ED213B2FD460FCFB"
        ),
    },
    "ruby_track_disposition_ledger": {
        "sha256": (
            "F1810CDA6B801DADC445380A48D6C35A30D29982960A0707166763D0DCC85708"
        ),
        "changed_surfaces": 143,
    },
    "japanese_guide": {
        "bytes": 121693,
        "sha256": (
            "2B678BFCA362A359BD4367C8C869E1ECAEFF497812937AFD15F4D6A14DD80284"
        ),
    },
    "chinese_guide": {
        "bytes": 111909,
        "sha256": (
            "992FE8E84244BA5AD4BF9B98706E52F74D32398FF6D0B5D2D226FA448028F953"
        ),
    },
}
EXPECTED_COUNTS = {
    "entries": 5,
    "productive_ruby_morph": 2,
    "exact_typed_ruby_only": 3,
    "strict_supersessions": 1,
}
EXPECTED_STRICT_SUPERSESSIONS = [{
    "w": "tia-tia",
    "target": "ti/a-/ti/a",
    "typed_roles": "RLRL",
    "exact_only": True,
    "boundary_only": True,
    "case_sensitive": True,
}]

EXPECTED_ROWS = {
    "kateĥismo": {
        "learner_line": 17542,
        "selected_ruby_target": "kateĥism/o",
        "kind": "productive_ruby_morph",
        "phase532_learner_head": "kateh^/ism/o",
        "phase532_academic_head": "kateh^ism/o",
        "phase558_learner_head": "kateh^ism/o",
        "phase558_academic_head": "kateh^ism/o",
        "context_key": "@phase558-ruby:kateĥism",
        "piece": "kateĥism",
        "glosses": {
            "ja": "教理問答", "zh": "教理问答", "ko": "교리문답",
        },
    },
    "kateĥisto": {
        "learner_line": 17543,
        "selected_ruby_target": "kateĥist/o",
        "kind": "productive_ruby_morph",
        "phase532_learner_head": "kateh^/ist/o",
        "phase532_academic_head": "kateh^ist/o",
        "phase558_learner_head": "kateh^ist/o",
        "phase558_academic_head": "kateh^ist/o",
        "context_key": "@phase558-ruby:kateĥist",
        "piece": "kateĥist",
        "glosses": {
            "ja": "教理教師", "zh": "教理教师", "ko": "교리교사",
        },
    },
    "magnetito": {
        "learner_line": 22871,
        "selected_ruby_target": "magnetit/o",
        "kind": "exact_typed_ruby_only",
        "typed_roles": "RL",
        "phase532_learner_head": "magnet/it/o",
        "phase532_academic_head": "magnetit/o",
        "phase558_learner_head": "magnetit/o",
        "phase558_academic_head": "magnetit/o",
        "piece": "magnetit",
        "glosses": {
            "ja": "磁鉄鉱", "zh": "磁铁矿", "ko": "자철석",
        },
    },
    "Izraelio": {
        "learner_line": 49611,
        "selected_ruby_target": "Izrael/io",
        "kind": "exact_typed_ruby_only",
        "typed_roles": "RL",
        "phase532_learner_head": "Izraeli/o",
        "phase532_academic_head": "Izraeli/o",
        "phase558_learner_head": "Izrael/i/o",
        "phase558_academic_head": "Izrael/i/o",
        "piece": "Izrael",
        "glosses": {
            "ja": "イスラエル", "zh": "以色列", "ko": "이스라엘",
        },
    },
    "tia-tia": {
        "learner_line": 56151,
        "selected_ruby_target": "tia/-/tia",
        "kind": "exact_typed_ruby_only",
        "typed_roles": "RLR",
        "phase532_learner_head": "ti/a-ti/a",
        "phase532_academic_head": "ti/a-ti/a",
        "phase558_learner_head": "tia-tia",
        "phase558_academic_head": "tia-tia",
        "piece": "tia",
        "glosses": {
            "ja": "そんな", "zh": "那样的", "ko": "그런",
        },
    },
}


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _head(line: str) -> str:
    return line.split(":", 1)[0]


def _validate_entry(entry: dict, expected: dict) -> None:
    common_keys = {
        "learner_line", "surface", "phase532_learner_line",
        "phase532_academic_line", "phase558_learner_line",
        "phase558_academic_line", "selected_ruby_target", "setting",
        "reason",
    }
    kind = expected["kind"]
    expected_keys = set(common_keys)
    if kind == "productive_ruby_morph":
        expected_keys.add("context_annotation")
    else:
        expected_keys.add("exact_annotations")
        if entry.get("negative_scope") is not None:
            expected_keys.add("negative_scope")
    if set(entry) != expected_keys:
        raise ValueError(f"Phase 558 overlay entry schema drift: {entry!r}")
    surface = entry["surface"]
    if (
        entry["learner_line"] != expected["learner_line"]
        or entry["selected_ruby_target"] != expected["selected_ruby_target"]
        or phase532.surface_from_decomposition(entry["selected_ruby_target"])
        != phase532.canonical(surface)
        or not entry["reason"]
    ):
        raise ValueError(f"Phase 558 overlay identity drift: {surface!r}")
    for field in (
        "phase532_learner_line", "phase532_academic_line",
        "phase558_learner_line", "phase558_academic_line",
    ):
        if _head(entry[field]) != expected[field.replace("_line", "_head")]:
            raise ValueError(
                f"Phase 558 source-row head drift: {surface!r}/{field}"
            )
    setting = entry["setting"]
    if setting.get("kind") != kind:
        raise ValueError(f"Phase 558 setting kind drift: {surface!r}")
    if kind == "productive_ruby_morph":
        if setting != {
            "kind": kind,
            "ruby_track_only": True,
            "ruby_context_annotation": expected["context_key"],
        } or entry["context_annotation"] != {
            "piece": expected["piece"],
            "glosses": expected["glosses"],
        }:
            raise ValueError(
                f"Phase 558 productive/context scope drift: {surface!r}"
            )
        return
    if setting != {
        "kind": kind,
        "typed_roles": expected["typed_roles"],
        "case_sensitive": True,
        "ruby_only": True,
    }:
        raise ValueError(f"Phase 558 exact setting drift: {surface!r}")
    pieces = [piece for piece in entry["selected_ruby_target"].split("/") if piece]
    roles = setting["typed_roles"]
    annotations = entry["exact_annotations"]
    expected_indexes = [0, 2] if surface == "tia-tia" else [0]
    if (
        len(pieces) != len(roles)
        or [row.get("index") for row in annotations] != expected_indexes
        or any(
            row.get("piece") != expected["piece"]
            or row.get("glosses") != expected["glosses"]
            or roles[row["index"]] != "R"
            or pieces[row["index"]] != row["piece"]
            for row in annotations
        )
    ):
        raise ValueError(f"Phase 558 exact annotation drift: {surface!r}")


def validate_review_payload(payload: dict) -> dict:
    expected_keys = {
        "schema_version", "phase_from", "phase_to", "candidate_only",
        "policy", "sources", "expected_counts", "strict_supersessions",
        "entries_sha256", "entries",
    }
    entries = payload.get("entries")
    if (
        set(payload) != expected_keys
        or payload.get("schema_version") != 1
        or payload.get("phase_from") != PHASE_FROM
        or payload.get("phase_to") != PHASE_TO
        or payload.get("candidate_only") is not False
        or payload.get("policy") != EXPECTED_POLICY
        or payload.get("sources") != EXPECTED_SOURCES
        or payload.get("expected_counts") != EXPECTED_COUNTS
        or payload.get("strict_supersessions")
        != EXPECTED_STRICT_SUPERSESSIONS
        or not isinstance(entries, list)
        or len(entries) != EXPECTED_COUNTS["entries"]
        or payload.get("entries_sha256") != EXPECTED_ENTRIES_SHA256
        or compact_sha256(entries) != EXPECTED_ENTRIES_SHA256
    ):
        raise ValueError("Phase 558 Ruby overlay review identity drift")
    surfaces = [entry.get("surface") for entry in entries]
    lines = [entry.get("learner_line") for entry in entries]
    if (
        set(surfaces) != set(EXPECTED_ROWS)
        or len(surfaces) != len(set(surfaces))
        or len(lines) != len(set(lines))
    ):
        raise ValueError("Phase 558 overlay closed-set scope drift")
    kinds = collections.Counter(entry.get("setting", {}).get("kind") for entry in entries)
    if kinds != {
        "productive_ruby_morph": 2,
        "exact_typed_ruby_only": 3,
    }:
        raise ValueError("Phase 558 overlay setting partition drift")
    for entry in entries:
        _validate_entry(entry, EXPECTED_ROWS[entry["surface"]])
    return payload


def load_review() -> dict:
    raw = REVIEW_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != EXPECTED_REVIEW_SHA256:
        raise ValueError("Phase 558 overlay raw review identity drift")
    return validate_review_payload(json.loads(raw.decode("utf-8")))


def managed_morph_targets() -> dict[str, dict]:
    result = {}
    for entry in load_review()["entries"]:
        setting = entry["setting"]
        if setting["kind"] != "productive_ruby_morph":
            continue
        result[entry["surface"]] = {
            "target": entry["selected_ruby_target"],
            "ruby_track_only": True,
            "ruby_context_annotation": setting["ruby_context_annotation"],
        }
    return result


def typed_exact_targets() -> dict[str, dict]:
    result = {}
    for entry in load_review()["entries"]:
        setting = entry["setting"]
        if setting["kind"] != "exact_typed_ruby_only":
            continue
        result[entry["surface"]] = {
            "target": entry["selected_ruby_target"],
            "typed_roles": setting["typed_roles"],
            "case_sensitive": True,
            "ruby_only": True,
        }
    return result


def morph_context_annotations() -> dict[str, dict]:
    result = {}
    for entry in load_review()["entries"]:
        setting = entry["setting"]
        if setting["kind"] != "productive_ruby_morph":
            continue
        result[setting["ruby_context_annotation"]] = dict(
            entry["context_annotation"]
        )
    return result


def typed_context_glosses() -> dict[tuple[str, int, str], dict]:
    result = {}
    for entry in load_review()["entries"]:
        for annotation in entry.get("exact_annotations", []):
            key = (entry["surface"], annotation["index"], annotation["piece"])
            if key in result:
                raise ValueError(f"duplicate Phase 558 typed annotation: {key!r}")
            result[key] = dict(annotation["glosses"])
    return result


def strict_supersessions() -> dict[str, dict]:
    return {
        entry["w"]: dict(entry)
        for entry in load_review()["strict_supersessions"]
    }


def selected_ruby_targets() -> dict[str, str]:
    return {
        entry["surface"]: entry["selected_ruby_target"]
        for entry in load_review()["entries"]
    }


def review_identity() -> dict:
    review = load_review()
    return {
        "phase_from": PHASE_FROM,
        "phase_to": PHASE_TO,
        "review_sha256": EXPECTED_REVIEW_SHA256,
        "entries_sha256": EXPECTED_ENTRIES_SHA256,
        "entries": len(review["entries"]),
        "productive_ruby_morph": EXPECTED_COUNTS["productive_ruby_morph"],
        "exact_typed_ruby_only": EXPECTED_COUNTS["exact_typed_ruby_only"],
        "strict_supersessions": EXPECTED_COUNTS["strict_supersessions"],
        "phase558_learner_sha256": EXPECTED_SOURCES["phase558_learner"]["sha256"],
        "phase558_academic_sha256": EXPECTED_SOURCES["phase558_academic"]["sha256"],
    }
