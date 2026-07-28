# -*- coding: utf-8 -*-
"""Fail-closed policy for seven reviewed Phase 619 ordinary-word Ruby repairs.

The sidecar is intentionally narrow:

* annotation Ruby follows the frozen academic/coarse decomposition;
* Kanji continues to follow the learner master, including fake/deep splits;
* all productive forms are whole-word bounded by ``make_correction``;
* every localized annotation is present for JA, ZH, and KO.
"""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

import phase532_ruby_policy as phase532


HERE = Path(__file__).resolve().parent
REVIEW_PATH = HERE / "_phase619_ordinary_ruby_review.json"

PHASE_FROM = 597
PHASE_TO = 619
EXPECTED_REVIEW_SHA256 = (
    "5BA83778181568ED90D989A4AFE866059F759DA2F46B7F6D8746FAFCEAAD4C4F"
)
EXPECTED_ENTRIES_SHA256 = (
    "D96EED41AE3E8716052E2138E0E9D8E7286974A1EF522E399DFB9175E4CB8CC1"
)
EXPECTED_POLICY = (
    "Adopt only seven reviewed ordinary-word Ruby repairs from the frozen "
    "Phase 619 master. Ruby follows the academic Kyoto-HTML-level coarse "
    "boundary; Kanji continues to follow the learner fake/deep decomposition. "
    "Every productive repair is whole-word bounded, JA/ZH/KO use identical "
    "R/L boundaries, and no root is split for width."
)
EXPECTED_COUNTS = {
    "entries": 7,
    "productive_atomic_ruby_morph": 6,
    "productive_split_ruby_morph": 1,
    "ordinary_priority": 7,
    "proper_name_changes": 0,
    "productive_endings": 10,
    "productive_case_variants": 3,
    "runtime_positive_surfaces_per_language": 210,
}
EXPECTED_SOURCES = {
    "phase597_learner": {
        "bytes": 4_373_830,
        "lines": 62_313,
        "sha256": (
            "9A610D086E60A1863E1D59D61FE0F844B3EACF4DCEBDBF6AE6354E0D16D99700"
        ),
    },
    "phase597_academic": {
        "bytes": 4_277_601,
        "lines": 62_313,
        "sha256": (
            "63DAB5BAF932605A2D94843AD249FBE32CB1E8A40B8D244714A17744C0384261"
        ),
    },
    "phase597_fake_coarse_manifest": {
        "bytes": 1_013_538,
        "lines": 40_060,
        "sha256": (
            "E699B6BF5CE737CF1DAFBF61C9B256DF0339A48B3AA7F24E215F2136B6D00541"
        ),
    },
    "phase619_learner": {
        "bytes": 4_374_847,
        "lines": 62_313,
        "sha256": (
            "4D89CD96F27D635DDC0EBC08F37DC7B211481F844C1AAE6922EB65749ACBB0D2"
        ),
    },
    "phase619_academic": {
        "bytes": 4_277_594,
        "lines": 62_313,
        "sha256": (
            "8E5D317521F2399168BA37DD4AA6A9944B98E1E1D717BE6B0989AE753E6CC7F5"
        ),
    },
    "phase619_pejvo_original": {
        "bytes": 2_841_948,
        "lines": 44_104,
        "sha256": (
            "EFE44C8E85F76CAA8C2C55F3FE1F64CCD2001B381E520D6386670D29D57DBB34"
        ),
    },
    "phase619_fake_coarse_manifest": {
        "bytes": 1_028_015,
        "lines": 40_650,
        "sha256": (
            "003FAE11D93499AD3D737EE6D31A759F4D0A9BF9EDBCC916B64B22BCBB6AF420"
        ),
    },
    "phase619_transition_dispositions": {
        "bytes": 1_100,
        "lines": 24,
        "sha256": (
            "42D30B155CCEF9832189C382EE2049B89350DA0BFAD5C774E4268D86D90164F6"
        ),
    },
    "japanese_guide": {
        "bytes": 131_181,
        "lines": 1_835,
        "sha256": (
            "B8F21605E019A394560A6E4ED5238FE4BEDE7B2A949A0CBC6927189ADADFB965"
        ),
    },
    "chinese_guide": {
        "bytes": 118_657,
        "lines": 1_907,
        "sha256": (
            "A3AF2F18004A63A2C6ECB438B9ABBABF62A9B40D15494FC6B6FC0CADA7ECEA46"
        ),
    },
    "app_parent": {
        "commit": "8AF4C19F50EA34D8C84767173C716E9B3F45EC5C",
    },
    "kyoto_corpus": {
        "commit": "D1642C276857C1FE400A6D597214FF7A923E7BD2",
    },
}
EXPECTED_ROWS = {
    "imperialisto": {
        "line": 15_017,
        "target": "imperialist/o",
        "kind": "productive_atomic_ruby_morph",
        "context_key": "@phase619-ruby:imperialist",
    },
    "provincialismo": {
        "line": 32_464,
        "target": "provincialism/o",
        "kind": "productive_atomic_ruby_morph",
        "context_key": "@phase619-ruby:provincialism",
    },
    "endoskopio": {
        "line": 47_244,
        "target": "endoskopi/o",
        "kind": "productive_atomic_ruby_morph",
        "context_key": "@phase619-ruby:endoskopi",
    },
    "mikroskopio": {
        "line": 52_038,
        "target": "mikroskopi/o",
        "kind": "productive_atomic_ruby_morph",
        "context_key": "@phase619-ruby:mikroskopi",
    },
    "mukozaĵo": {
        "line": 52_263,
        "target": "mukoz/aĵ/o",
        "kind": "productive_split_ruby_morph",
        "split_context_key": "mukoz/aĵ",
        "pieces": ("mukoz", "aĵ"),
    },
    "ditionato": {
        "line": 61_484,
        "target": "ditionat/o",
        "kind": "productive_atomic_ruby_morph",
        "context_key": "@phase619-ruby:ditionat",
    },
    "tetrationato": {
        "line": 61_485,
        "target": "tetrationat/o",
        "kind": "productive_atomic_ruby_morph",
        "context_key": "@phase619-ruby:tetrationat",
    },
}


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def _head(line: str) -> str:
    return line.split(":", 1)[0]


def _validate_entry(entry: dict, expected: dict) -> None:
    common_keys = {
        "learner_line", "surface",
        "phase597_learner_line", "phase597_academic_line",
        "phase619_learner_line", "phase619_academic_line",
        "selected_ruby_target", "setting", "reason",
    }
    kind = expected["kind"]
    expected_keys = set(common_keys)
    if kind == "productive_atomic_ruby_morph":
        expected_keys.add("context_annotation")
    else:
        expected_keys.add("split_context_annotations")
    if set(entry) != expected_keys:
        raise ValueError(
            f"Phase 619 ordinary review entry schema drift: {entry!r}"
        )
    if (
        entry["learner_line"] != expected["line"]
        or entry["selected_ruby_target"] != expected["target"]
        or phase532.surface_from_decomposition(entry["selected_ruby_target"])
        != phase532.canonical(entry["surface"])
        or not entry["reason"]
    ):
        raise ValueError(
            f"Phase 619 ordinary review identity drift: {entry['surface']!r}"
        )
    for field in (
        "phase597_learner_line", "phase597_academic_line",
        "phase619_learner_line", "phase619_academic_line",
    ):
        if not isinstance(entry[field], str) or not entry[field]:
            raise ValueError(
                f"Phase 619 source row is empty: {entry['surface']!r}/{field}"
            )
    if (
        _head(entry["phase619_academic_line"])
        != entry["selected_ruby_target"].replace(
            "ĉ", "c^",
        ).replace(
            "ĝ", "g^",
        ).replace(
            "ĥ", "h^",
        ).replace(
            "ĵ", "j^",
        ).replace(
            "ŝ", "s^",
        ).replace(
            "ŭ", "u^",
        )
    ):
        raise ValueError(
            f"Phase 619 academic authority drift: {entry['surface']!r}"
        )
    setting = entry["setting"]
    if kind == "productive_atomic_ruby_morph":
        context_key = expected["context_key"]
        if setting != {
            "kind": kind,
            "ruby_track_only": True,
            "ruby_context_annotation": context_key,
        }:
            raise ValueError(
                f"Phase 619 atomic setting drift: {entry['surface']!r}"
            )
        annotation = entry["context_annotation"]
        stem = entry["selected_ruby_target"].rsplit("/", 1)[0]
        if (
            set(annotation) != {"piece", "glosses"}
            or annotation["piece"] != stem
            or set(annotation["glosses"]) != {"ja", "zh", "ko"}
            or any(
                not isinstance(value, str) or not value
                for value in annotation["glosses"].values()
            )
        ):
            raise ValueError(
                f"Phase 619 atomic annotation drift: {entry['surface']!r}"
            )
        return
    if setting != {
        "kind": kind,
        "ruby_track_only": True,
        "split_context_key": expected["split_context_key"],
    }:
        raise ValueError(
            f"Phase 619 split setting drift: {entry['surface']!r}"
        )
    annotations = entry["split_context_annotations"]
    if (
        not isinstance(annotations, list)
        or tuple(row.get("piece") for row in annotations)
        != expected["pieces"]
        or setting["split_context_key"] != "/".join(expected["pieces"])
        or any(
            set(row) != {"piece", "glosses"}
            or set(row["glosses"]) != {"ja", "zh", "ko"}
            or any(
                not isinstance(value, str) or not value
                for value in row["glosses"].values()
            )
            for row in annotations
        )
    ):
        raise ValueError(
            f"Phase 619 split annotation drift: {entry['surface']!r}"
        )


def validate_review_payload(payload: dict) -> dict:
    expected_keys = {
        "schema_version", "phase_from", "phase_to", "candidate_only",
        "policy", "sources", "expected_counts", "entries_sha256", "entries",
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
        or not isinstance(entries, list)
        or len(entries) != EXPECTED_COUNTS["entries"]
        or payload.get("entries_sha256") != EXPECTED_ENTRIES_SHA256
        or compact_sha256(entries) != EXPECTED_ENTRIES_SHA256
    ):
        raise ValueError("Phase 619 ordinary Ruby review identity drift")
    surfaces = [entry.get("surface") for entry in entries]
    lines = [entry.get("learner_line") for entry in entries]
    if (
        set(surfaces) != set(EXPECTED_ROWS)
        or len(surfaces) != len(set(surfaces))
        or len(lines) != len(set(lines))
    ):
        raise ValueError("Phase 619 ordinary Ruby closed-set scope drift")
    kinds = collections.Counter(
        entry.get("setting", {}).get("kind") for entry in entries
    )
    if kinds != {
        "productive_atomic_ruby_morph": 6,
        "productive_split_ruby_morph": 1,
    }:
        raise ValueError("Phase 619 ordinary Ruby setting partition drift")
    for entry in entries:
        _validate_entry(entry, EXPECTED_ROWS[entry["surface"]])
    return payload


def load_review() -> dict:
    raw = REVIEW_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != EXPECTED_REVIEW_SHA256:
        raise ValueError("Phase 619 ordinary Ruby raw review identity drift")
    return validate_review_payload(json.loads(raw.decode("utf-8")))


def managed_morph_targets() -> dict[str, dict]:
    result = {}
    for entry in load_review()["entries"]:
        setting = entry["setting"]
        spec = {
            "target": entry["selected_ruby_target"],
            "ruby_track_only": True,
        }
        if setting["kind"] == "productive_atomic_ruby_morph":
            spec["ruby_context_annotation"] = (
                setting["ruby_context_annotation"]
            )
        result[entry["surface"]] = spec
    return result


def morph_context_annotations() -> dict[str, dict]:
    result = {}
    for entry in load_review()["entries"]:
        setting = entry["setting"]
        if setting["kind"] != "productive_atomic_ruby_morph":
            continue
        result[setting["ruby_context_annotation"]] = dict(
            entry["context_annotation"]
        )
    return result


def split_context_annotations() -> dict[str, list[dict]]:
    result = {}
    for entry in load_review()["entries"]:
        setting = entry["setting"]
        if setting["kind"] != "productive_split_ruby_morph":
            continue
        result[setting["split_context_key"]] = [
            {
                "piece": row["piece"],
                "glosses": dict(row["glosses"]),
            }
            for row in entry["split_context_annotations"]
        ]
    return result


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
        "productive_atomic_ruby_morph": (
            EXPECTED_COUNTS["productive_atomic_ruby_morph"]
        ),
        "productive_split_ruby_morph": (
            EXPECTED_COUNTS["productive_split_ruby_morph"]
        ),
        "phase619_learner_sha256": EXPECTED_SOURCES[
            "phase619_learner"
        ]["sha256"],
        "phase619_academic_sha256": EXPECTED_SOURCES[
            "phase619_academic"
        ]["sha256"],
        "phase619_transition_dispositions_sha256": EXPECTED_SOURCES[
            "phase619_transition_dispositions"
        ]["sha256"],
        "kyoto_corpus_commit": EXPECTED_SOURCES[
            "kyoto_corpus"
        ]["commit"],
    }
