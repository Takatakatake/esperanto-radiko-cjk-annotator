# -*- coding: utf-8 -*-
"""Fail-closed policy for eight reviewed technical ``on`` Ruby repairs.

The learner master deliberately keeps the deeper/fake decompositions used by
the Kanji track.  This sidecar changes only annotation Ruby: seven reviewed
technical stems become one coarse Ruby root, and one compound receives an
exact three-root Ruby boundary.  Generic ``on`` (fraction), the moving master,
and every Kanji setting remain outside this closed set.
"""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

import phase532_ruby_policy as phase532


HERE = Path(__file__).resolve().parent
REVIEW_PATH = HERE / "_phase598_technical_on_review.json"

PHASE = 598
EXPECTED_REVIEW_SHA256 = (
    "C151FD6F486D034504BFF38726E058508736096B2C7E36F79FEEBE61C441EB13"
)
EXPECTED_ENTRIES_SHA256 = (
    "EA66E4EF6BEB585A15114F86C4A4A8A14E30F47B0C7FA099958D3B20ED97ACAE"
)
EXPECTED_POLICY = (
    "Repair only eight reviewed technical lexical roots whose internal on "
    "was confused with the fraction root. Keep Kyoto-HTML-level coarse Ruby "
    "identical in JA/ZH/KO, preserve the learner fake/deep split for Kanji, "
    "and never generalize the generic on annotation."
)
EXPECTED_SOURCES = {
    "base_app_parent": {
        "commit": (
            "4682D32496F166802B4A2CF28626F376E12AAE3E"
        ),
        "tree": "2C494DB69EBAC28EF63A192BEFA017A22710CCD7",
        "required_r71_ancestor": (
            "2E05403756DB6A4D1081BDD0EF95ADD77C3BFA87"
        ),
    },
    "phase597_learner": {
        "bytes": 4373830,
        "lines": 62313,
        "sha256": (
            "9A610D086E60A1863E1D59D61FE0F844B3EACF4DCEBDBF6AE6354E0D16D99700"
        ),
    },
    "phase597_academic": {
        "bytes": 4277601,
        "lines": 62313,
        "sha256": (
            "63DAB5BAF932605A2D94843AD249FBE32CB1E8A40B8D244714A17744C0384261"
        ),
    },
    "phase597_pejvo_original": {
        "bytes": 2211329,
        "lines": 44621,
        "sha256": (
            "B551510513C1924E65E64CF87EA4CE39128E80717E3A3F53847753F8A0557CBF"
        ),
    },
    "phase597_fake_coarse_manifest": {
        "bytes": 1013538,
        "entries": 3321,
        "sha256": (
            "E699B6BF5CE737CF1DAFBF61C9B256DF0339A48B3AA7F24E215F2136B6D00541"
        ),
        "entries_sha256": (
            "63BF80872496A0644BE75ADC8554E130F49F30990870D3B47956727387FA97A6"
        ),
    },
}
EXPECTED_COUNTS = {
    "entries": 8,
    "productive_ruby_morph": 7,
    "exact_typed_ruby_only": 1,
    "positive_surfaces_per_language": 211,
    "genuine_fraction_guards": 120,
    "bare_homograph_guards": 21,
    "adjacent_technical_guards": 14,
    "exact_leakage_guards": 4,
    "negative_surfaces_per_language": 159,
    "combined_runtime_surfaces_per_language": 370,
}
EXPECTED_ROWS = {
    "fonono": {
        "line": 11579,
        "learner": "fon/on/o",
        "academic": "fonon/o",
        "pejvo": [11723],
        "kind": "productive_ruby_morph",
        "context_key": "@phase598-ruby:technical-on:fonon",
        "piece": "fonon",
        "glosses": {"ja": "フォノン", "zh": "声子", "ko": "포논"},
    },
    "fotono": {
        "line": 11925,
        "learner": "fot/on/o",
        "academic": "foton/o",
        "pejvo": [12070],
        "kind": "productive_ruby_morph",
        "context_key": "@phase598-ruby:technical-on:foton",
        "piece": "foton",
        "glosses": {"ja": "光子", "zh": "光子", "ko": "광자"},
    },
    "gangliono": {
        "line": 12551,
        "learner": "gangli/on/o",
        "academic": "ganglion/o",
        "pejvo": [12709],
        "kind": "productive_ruby_morph",
        "context_key": "@phase598-ruby:technical-on:ganglion",
        "piece": "ganglion",
        "glosses": {"ja": "リンパ節", "zh": "淋巴结", "ko": "림프절"},
    },
    "gigaelektronvolto": {
        "line": 12887,
        "learner": "giga/elektr/on/volt/o",
        "academic": "giga/elektron/volt/o",
        "pejvo": [13049],
        "kind": "exact_typed_ruby_only",
        "typed_roles": "RRRL",
        "annotations": [
            {
                "index": 0,
                "piece": "giga",
                "glosses": {"ja": "ギガ", "zh": "吉", "ko": "기가"},
            },
            {
                "index": 1,
                "piece": "elektron",
                "glosses": {"ja": "電子", "zh": "电子", "ko": "전자"},
            },
            {
                "index": 2,
                "piece": "volt",
                "glosses": {"ja": "ボルト", "zh": "伏特", "ko": "볼트"},
            },
        ],
    },
    "magnetono": {
        "line": 22882,
        "learner": "magnet/on/o",
        "academic": "magneton/o",
        "pejvo": [23154],
        "kind": "productive_ruby_morph",
        "context_key": "@phase598-ruby:technical-on:magneton",
        "piece": "magneton",
        "glosses": {"ja": "磁子", "zh": "磁子", "ko": "마그네톤"},
    },
    "mezono": {
        "line": 25285,
        "learner": "mez/on/o",
        "academic": "mezon/o",
        "pejvo": [25585],
        "kind": "productive_ruby_morph",
        "context_key": "@phase598-ruby:technical-on:mezon",
        "piece": "mezon",
        "glosses": {"ja": "中間子", "zh": "介子", "ko": "중간자"},
    },
    "nukleono": {
        "line": 27949,
        "learner": "nukle/on/o",
        "academic": "nukleon/o",
        "pejvo": [28288],
        "kind": "productive_ruby_morph",
        "context_key": "@phase598-ruby:technical-on:nukleon",
        "piece": "nukleon",
        "glosses": {"ja": "核子", "zh": "核子", "ko": "핵자"},
    },
    "termoelektrono": {
        "line": 40412,
        "learner": "term/o/elektr/on/o",
        "academic": "termoelektron/o",
        "pejvo": [40890],
        "kind": "productive_ruby_morph",
        "context_key": "@phase598-ruby:technical-on:termoelektron",
        "piece": "termoelektron",
        "glosses": {"ja": "熱電子", "zh": "热电子", "ko": "열전자"},
    },
}


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def _head(line: str) -> str:
    return line.split(":", 1)[0]


def _validate_common(entry: dict, expected: dict) -> None:
    surface = entry["surface"]
    if (
        entry["learner_line"] != expected["line"]
        or entry["learner_decomposition"] != expected["learner"]
        or entry["academic_decomposition"] != expected["academic"]
        or entry["selected_ruby_target"] != expected["academic"]
        or _head(entry["learner_line_text"]) != expected["learner"]
        or _head(entry["academic_line_text"]) != expected["academic"]
        or entry["authority"] != "pejvo_original"
        or entry["authority_lines"] != expected["pejvo"]
        or entry["kind"] != expected["kind"]
        or phase532.surface_from_decomposition(entry["selected_ruby_target"])
        != phase532.canonical(surface)
    ):
        raise ValueError(f"Phase 598 technical-on row identity drift: {surface!r}")


def _validate_entry(entry: dict, expected: dict) -> None:
    common_keys = {
        "surface", "learner_line", "learner_line_text",
        "academic_line_text", "learner_decomposition",
        "academic_decomposition", "selected_ruby_target", "authority",
        "authority_lines", "kind",
    }
    _validate_common(entry, expected)
    if expected["kind"] == "productive_ruby_morph":
        if (
            set(entry) != common_keys | {"context_key", "piece", "glosses"}
            or entry["context_key"] != expected["context_key"]
            or entry["piece"] != expected["piece"]
            or entry["glosses"] != expected["glosses"]
            or entry["selected_ruby_target"] != f'{entry["piece"]}/o'
        ):
            raise ValueError(
                f"Phase 598 productive Ruby scope drift: {entry['surface']!r}"
            )
        return
    pieces = [
        piece for piece in entry["selected_ruby_target"].split("/") if piece
    ]
    if (
        set(entry) != common_keys | {"typed_roles", "exact_annotations"}
        or entry["typed_roles"] != expected["typed_roles"]
        or entry["exact_annotations"] != expected["annotations"]
        or len(pieces) != len(entry["typed_roles"])
        or any(
            row["index"] >= len(pieces)
            or pieces[row["index"]] != row["piece"]
            or entry["typed_roles"][row["index"]] != "R"
            for row in entry["exact_annotations"]
        )
    ):
        raise ValueError(
            f"Phase 598 exact typed Ruby scope drift: {entry['surface']!r}"
        )


def validate_review_payload(payload: dict) -> dict:
    expected_keys = {
        "schema_version", "phase", "candidate_only", "policy", "sources",
        "expected_counts", "entries_sha256", "entries",
    }
    entries = payload.get("entries")
    if (
        set(payload) != expected_keys
        or payload.get("schema_version") != 1
        or payload.get("phase") != PHASE
        or payload.get("candidate_only") is not False
        or payload.get("policy") != EXPECTED_POLICY
        or payload.get("sources") != EXPECTED_SOURCES
        or payload.get("expected_counts") != EXPECTED_COUNTS
        or payload.get("entries_sha256") != EXPECTED_ENTRIES_SHA256
        or not isinstance(entries, list)
        or len(entries) != EXPECTED_COUNTS["entries"]
        or compact_sha256(entries) != EXPECTED_ENTRIES_SHA256
    ):
        raise ValueError("Phase 598 technical-on review identity drift")
    surfaces = [entry.get("surface") for entry in entries]
    lines = [entry.get("learner_line") for entry in entries]
    if (
        set(surfaces) != set(EXPECTED_ROWS)
        or len(surfaces) != len(set(surfaces))
        or len(lines) != len(set(lines))
    ):
        raise ValueError("Phase 598 technical-on closed-set scope drift")
    kinds = collections.Counter(entry.get("kind") for entry in entries)
    if kinds != {
        "productive_ruby_morph": 7,
        "exact_typed_ruby_only": 1,
    }:
        raise ValueError("Phase 598 technical-on setting partition drift")
    for entry in entries:
        _validate_entry(entry, EXPECTED_ROWS[entry["surface"]])
    return payload


def load_review() -> dict:
    raw = REVIEW_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != EXPECTED_REVIEW_SHA256:
        raise ValueError("Phase 598 technical-on raw review identity drift")
    return validate_review_payload(json.loads(raw.decode("utf-8")))


def managed_morph_targets() -> dict[str, dict]:
    result = {}
    for entry in load_review()["entries"]:
        if entry["kind"] != "productive_ruby_morph":
            continue
        result[entry["surface"]] = {
            "target": entry["selected_ruby_target"],
            "ruby_track_only": True,
            "ruby_context_annotation": entry["context_key"],
        }
    return result


def typed_exact_targets() -> dict[str, dict]:
    result = {}
    for entry in load_review()["entries"]:
        if entry["kind"] != "exact_typed_ruby_only":
            continue
        result[entry["surface"]] = {
            "target": entry["selected_ruby_target"],
            "typed_roles": entry["typed_roles"],
            "case_sensitive": True,
            "ruby_only": True,
        }
    return result


def morph_context_annotations() -> dict[str, dict]:
    return {
        entry["context_key"]: {
            "piece": entry["piece"],
            "glosses": dict(entry["glosses"]),
        }
        for entry in load_review()["entries"]
        if entry["kind"] == "productive_ruby_morph"
    }


def typed_context_glosses() -> dict[tuple[str, int, str], dict]:
    result = {}
    for entry in load_review()["entries"]:
        for annotation in entry.get("exact_annotations", []):
            key = (entry["surface"], annotation["index"], annotation["piece"])
            if key in result:
                raise ValueError(
                    f"duplicate Phase 598 typed annotation: {key!r}"
                )
            result[key] = dict(annotation["glosses"])
    return result


def selected_ruby_targets() -> dict[str, str]:
    return {
        entry["surface"]: entry["selected_ruby_target"]
        for entry in load_review()["entries"]
    }


def review_identity() -> dict:
    review = load_review()
    return {
        "phase": PHASE,
        "review_sha256": EXPECTED_REVIEW_SHA256,
        "entries_sha256": EXPECTED_ENTRIES_SHA256,
        "entries": len(review["entries"]),
        "productive_ruby_morph": EXPECTED_COUNTS["productive_ruby_morph"],
        "exact_typed_ruby_only": EXPECTED_COUNTS["exact_typed_ruby_only"],
        "positive_surfaces_per_language": (
            EXPECTED_COUNTS["positive_surfaces_per_language"]
        ),
        "negative_surfaces_per_language": (
            EXPECTED_COUNTS["negative_surfaces_per_language"]
        ),
        "phase597_learner_sha256": (
            EXPECTED_SOURCES["phase597_learner"]["sha256"]
        ),
        "phase597_academic_sha256": (
            EXPECTED_SOURCES["phase597_academic"]["sha256"]
        ),
        "base_app_parent_commit": (
            EXPECTED_SOURCES["base_app_parent"]["commit"]
        ),
        "base_app_parent_tree": EXPECTED_SOURCES["base_app_parent"]["tree"],
    }
