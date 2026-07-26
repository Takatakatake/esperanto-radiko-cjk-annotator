#!/usr/bin/env python3
"""Fail closed unless R73 changes only its reviewed 211 Ruby surfaces.

The Phase 598 runtime gate proves the positive and negative examples, but that
closed corpus cannot by itself detect removal of older post-generation
sidecars.  This gate compares every deployed replacement row with the pinned
R72 parent and permits only the reviewed technical-``on`` delta.

Placeholders are intentionally ignored in the global semantic comparison:
numeric placeholder IDs are regenerated mechanically.  Source order and
``(source, rendered)`` order outside the 211 reviewed surfaces must still be
byte-for-byte identical, and the two non-global buckets must be fully equal.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gc
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import phase598_technical_on_policy as policy
import phase598_technical_on_runtime_gate as runtime_gate
from preserve_r67_r68_ruby_overlays import (
    GLOBAL_BUCKET_TOKEN,
    LANGUAGES,
    PINNED_PARENT_COMMIT,
    PINNED_PARENT_GLOBAL_ROWS,
    PINNED_PARENT_TREE,
    EXPECTED_POST_R73_GLOBAL_ROWS,
    compact_sha256,
    global_bucket,
    load_payload,
)


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COUNTS = {
    "source_removed": 66,
    "source_added": 211,
    "semantic_removed": 66,
    "semantic_added": 211,
}
EXPECTED_MANIFESTS = {
    "source_removed_sha256": (
        "CB42BBF454ADE32DCBC7EFEB8D0F03EA96E374FBE3F39E4CBBF505CCF1E8FBCE"
    ),
    "source_added_sha256": (
        "8D7254290ED07835EE8740AAA5222C14C87D1FA9E5EB83ED288FC5FCBD8A3BBB"
    ),
    "semantic_removed_sha256": {
        "JA": (
            "6BE357D9219216998BF2A1FA72642A802B4D489509FE5BC5431469C26FB7A7C3"
        ),
        "ZH": (
            "E068C6BC9BBB1C429E361352F833764C5F5CE21C1ACD281BF64C38BE3CAF7068"
        ),
        "KO": (
            "8100A99CF639B7214FBE449B8F7075A3CCB1C80F293C502F98C99E85999F97F3"
        ),
    },
    "semantic_added_sha256": {
        "JA": (
            "F8B62277A19FC001F2A0134BD741D18CFA98B49F577F5BD478C06B033B9D0900"
        ),
        "ZH": (
            "38C66A27102639FB3927D3E988423EF03B18968EC63817747DF875A04F32E6E0"
        ),
        "KO": (
            "CDB95A4A64FA58F9C8C1C97FB11F0212BDD6D935437A848611BB2E7E351704BB"
        ),
    },
    "offscope_ordered_sha256": {
        "JA": (
            "0AE2D25F9DFBBC99C1C2E4A3149EEC12B5F92D8861C45FE7C63DA9D97E2A7C68"
        ),
        "ZH": (
            "33167ED7466CDDDC32EDD2EC9FE7E1B3116073ED8C77F9467F42A3CAA02B474A"
        ),
        "KO": (
            "66CCC27169AAFA379A1CC2DE61A70E4392875A0F77B48C692B2D0836AFF06AED"
        ),
    },
}


def _parent_identity() -> dict:
    commit = subprocess.check_output(
        ["git", "rev-parse", f"{PINNED_PARENT_COMMIT}^{{commit}}"],
        cwd=ROOT,
        text=True,
    ).strip().upper()
    tree = subprocess.check_output(
        ["git", "rev-parse", f"{PINNED_PARENT_COMMIT}^{{tree}}"],
        cwd=ROOT,
        text=True,
    ).strip().upper()
    identity = {"commit": commit, "tree": tree}
    expected = {
        "commit": PINNED_PARENT_COMMIT,
        "tree": PINNED_PARENT_TREE,
    }
    if identity != expected:
        raise ValueError(
            f"Phase 598 parent identity drift: {identity!r} != {expected!r}"
        )
    review_identity = policy.review_identity()
    if (
        review_identity["base_app_parent_commit"] != PINNED_PARENT_COMMIT
        or review_identity["base_app_parent_tree"] != PINNED_PARENT_TREE
    ):
        raise ValueError("Phase 598 review/parent identity mismatch")
    return identity


def _validate_global_row_shape(language: str, label: str, rows: list) -> None:
    malformed = [
        index
        for index, row in enumerate(rows)
        if (
            not isinstance(row, list)
            or len(row) < 3
            or not all(isinstance(value, str) for value in row[:3])
        )
    ]
    if malformed:
        raise ValueError(
            f"{language}/{label}: malformed global rows: {malformed[:5]!r}"
        )
    duplicate_sources = [
        source
        for source, count in Counter(row[0] for row in rows).items()
        if count != 1
    ]
    if duplicate_sources:
        raise ValueError(
            f"{language}/{label}: duplicate global sources: "
            f"{sorted(duplicate_sources)[:5]!r}"
        )


def _sorted_counter_elements(counter: Counter, pair: bool) -> list:
    elements = list(counter.elements())
    elements.sort()
    if pair:
        return [list(element) for element in elements]
    return elements


def validate_language_delta(
    language: str,
    parent_payload: dict,
    candidate_payload: dict,
    positive_surfaces: set[str],
) -> dict:
    if set(parent_payload) != set(candidate_payload):
        raise ValueError(f"{language}: payload bucket names changed")
    parent_key, parent_rows = global_bucket(parent_payload)
    candidate_key, candidate_rows = global_bucket(candidate_payload)
    if parent_key != candidate_key:
        raise ValueError(f"{language}: global bucket key changed")
    if len(parent_rows) != PINNED_PARENT_GLOBAL_ROWS:
        raise ValueError(
            f"{language}: parent global count drift: {len(parent_rows)}"
        )
    if len(candidate_rows) != EXPECTED_POST_R73_GLOBAL_ROWS:
        raise ValueError(
            f"{language}: candidate global count drift: {len(candidate_rows)}"
        )
    _validate_global_row_shape(language, "parent", parent_rows)
    _validate_global_row_shape(language, "candidate", candidate_rows)

    for key in parent_payload:
        if GLOBAL_BUCKET_TOKEN in key:
            continue
        if parent_payload[key] != candidate_payload[key]:
            raise ValueError(
                f"{language}: non-global Ruby bucket changed: {key!r}"
            )

    parent_sources = Counter(row[0] for row in parent_rows)
    candidate_sources = Counter(row[0] for row in candidate_rows)
    source_removed = parent_sources - candidate_sources
    source_added = candidate_sources - parent_sources

    parent_semantics = Counter(
        (row[0], row[1]) for row in parent_rows
    )
    candidate_semantics = Counter(
        (row[0], row[1]) for row in candidate_rows
    )
    semantic_removed = parent_semantics - candidate_semantics
    semantic_added = candidate_semantics - parent_semantics

    actual_counts = {
        "source_removed": sum(source_removed.values()),
        "source_added": sum(source_added.values()),
        "semantic_removed": sum(semantic_removed.values()),
        "semantic_added": sum(semantic_added.values()),
    }
    if actual_counts != EXPECTED_COUNTS:
        raise ValueError(
            f"{language}: parent delta count drift: "
            f"{actual_counts!r} != {EXPECTED_COUNTS!r}"
        )

    outside = {
        "source_removed": sorted({
            source.strip()
            for source in source_removed
            if source.strip() not in positive_surfaces
        }),
        "source_added": sorted({
            source.strip()
            for source in source_added
            if source.strip() not in positive_surfaces
        }),
        "semantic_removed": sorted({
            source.strip()
            for source, _rendered in semantic_removed
            if source.strip() not in positive_surfaces
        }),
        "semantic_added": sorted({
            source.strip()
            for source, _rendered in semantic_added
            if source.strip() not in positive_surfaces
        }),
    }
    if any(outside.values()):
        raise ValueError(
            f"{language}: off-scope Phase 598 delta: {outside!r}"
        )
    normalized_added = Counter(
        source.strip() for source in source_added.elements()
    )
    if normalized_added != Counter(positive_surfaces):
        raise ValueError(
            f"{language}: positive payload source closure drift"
        )

    source_removed_sha = compact_sha256(
        _sorted_counter_elements(source_removed, pair=False)
    )
    source_added_sha = compact_sha256(
        _sorted_counter_elements(source_added, pair=False)
    )
    semantic_removed_sha = compact_sha256(
        _sorted_counter_elements(semantic_removed, pair=True)
    )
    semantic_added_sha = compact_sha256(
        _sorted_counter_elements(semantic_added, pair=True)
    )
    if source_removed_sha != EXPECTED_MANIFESTS["source_removed_sha256"]:
        raise ValueError(
            f"{language}: removed source manifest drift"
        )
    if source_added_sha != EXPECTED_MANIFESTS["source_added_sha256"]:
        raise ValueError(
            f"{language}: added source manifest drift"
        )
    if (
        semantic_removed_sha
        != EXPECTED_MANIFESTS["semantic_removed_sha256"][language]
    ):
        raise ValueError(
            f"{language}: removed semantic manifest drift"
        )
    if (
        semantic_added_sha
        != EXPECTED_MANIFESTS["semantic_added_sha256"][language]
    ):
        raise ValueError(
            f"{language}: added semantic manifest drift"
        )

    parent_offscope = [
        [row[0], row[1]]
        for row in parent_rows
        if row[0].strip() not in positive_surfaces
    ]
    candidate_offscope = [
        [row[0], row[1]]
        for row in candidate_rows
        if row[0].strip() not in positive_surfaces
    ]
    if parent_offscope != candidate_offscope:
        raise ValueError(
            f"{language}: off-scope source/render ordering changed"
        )
    offscope_sha = compact_sha256(candidate_offscope)
    if (
        offscope_sha
        != EXPECTED_MANIFESTS["offscope_ordered_sha256"][language]
    ):
        raise ValueError(
            f"{language}: off-scope ordered manifest drift"
        )

    return {
        "parent_global_rows": len(parent_rows),
        "candidate_global_rows": len(candidate_rows),
        **actual_counts,
        "source_removed_sha256": source_removed_sha,
        "source_added_sha256": source_added_sha,
        "semantic_removed_sha256": semantic_removed_sha,
        "semantic_added_sha256": semantic_added_sha,
        "offscope_ordered_rows": len(candidate_offscope),
        "offscope_ordered_sha256": offscope_sha,
        "non_global_buckets_unchanged": True,
        "gate": True,
    }


def validate_deployed_delta() -> dict:
    parent_identity = _parent_identity()
    positive_list = runtime_gate.positive_surface_list()
    positive_surfaces = set(positive_list)
    if len(positive_list) != len(positive_surfaces):
        raise ValueError("Phase 598 positive list contains duplicates")

    languages = {}
    source_removed_manifests = set()
    source_added_manifests = set()
    for language in LANGUAGES:
        parent_payload = load_payload(
            language,
            git_ref=PINNED_PARENT_COMMIT,
        )
        candidate_payload = load_payload(language)
        report = validate_language_delta(
            language,
            parent_payload,
            candidate_payload,
            positive_surfaces,
        )
        languages[language] = report
        source_removed_manifests.add(
            report["source_removed_sha256"]
        )
        source_added_manifests.add(
            report["source_added_sha256"]
        )
        del parent_payload
        del candidate_payload
        gc.collect()
    if len(source_removed_manifests) != 1:
        raise ValueError("JA/ZH/KO removed source delta mismatch")
    if len(source_added_manifests) != 1:
        raise ValueError("JA/ZH/KO added source delta mismatch")

    return {
        "phase": 598,
        "authority": "pinned-parent-full-payload-delta",
        "parent_identity": parent_identity,
        "positive_surfaces": len(positive_surfaces),
        "expected_counts": EXPECTED_COUNTS,
        "languages": languages,
        "trilingual_source_delta_identical": True,
        "gate": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the full deployed R73 Ruby payload delta against R72."
        )
    )
    parser.add_argument("--deployed", action="store_true", required=True)
    return parser.parse_args()


def main() -> None:
    parse_args()
    report = validate_deployed_delta()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            f"Phase 598 parent payload delta gate failed: {error}",
            file=sys.stderr,
        )
        raise
