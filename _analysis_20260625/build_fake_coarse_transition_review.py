# -*- coding: utf-8 -*-
"""Build/check the staged fake-to-coarse transition review scope.

The source candidate was independently assembled from the C679->B090 marker
transition and the three B090 marker-only deltas.  The committed result keeps
only line keys, exact surfaces and approved coarse decompositions; the full
paired-master audit revalidates each of them against the fixed authority.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

from atomic_json import atomic_json_dump


HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "_fake_coarse_transition_review.json"
FULL_AUTHORITY_MANIFEST = (
    HERE / "_phase513_fake_coarse_reference_manifest.json"
)
SOURCE_CANDIDATE_SHA256 = (
    "0D62EA71A07499800AA49DAAEB8C9B9BA0D6870F3AF9D7158C249115D8BE34B3"
)
EXPECTED_COUNTS = {
    "entries": 136,
    "unique_surfaces": 135,
    "duplicate_surface_rows": 1,
    "categories": {
        "reviewed_c679_to_b090_fake_transition": 133,
        "reviewed_b090_marker_only_delta": 3,
    },
    "authority_adjustments": 2,
}
EXPECTED_ENTRIES_SHA256 = (
    "B8B1036BF0164960429B2FD079EBF62A71FA02425FC0A4D8EB7B84F127BCCF01"
)


def entries_sha256(entries):
    raw = json.dumps(
        entries, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def build(candidate_path):
    raw = candidate_path.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != SOURCE_CANDIDATE_SHA256:
        raise ValueError("transition authority candidate SHA256 changed")
    candidate = json.loads(raw.decode("utf-8"))
    full_authority = json.loads(
        FULL_AUTHORITY_MANIFEST.read_text(encoding="utf-8")
    )
    full_by_line = {
        row["learner_line"]: row for row in full_authority["entries"]
    }
    entries = []
    for row in candidate["rows"]:
        if row.get("status") != "candidate_ready":
            raise ValueError(f"unapproved transition row: {row.get('surface')!r}")
        candidate_coarse = row["proposed_coarse_decomposition"]
        paired = row.get("paired_academic_exact_surface") or []
        if not paired:
            raise ValueError(f"transition row lacks paired academic line: {row!r}")
        for paired_row in paired:
            if paired_row["decomposition"] != candidate_coarse:
                raise ValueError(
                    f"transition candidate has ambiguous coarse authority: {row['surface']!r}"
                )
            authority_row = full_by_line.get(paired_row["line"])
            coarse = (
                authority_row["coarse_decomposition"]
                if authority_row else candidate_coarse
            )
            entry = {
                "learner_line": paired_row["line"],
                "surface": row["surface"],
                "coarse_decomposition": coarse,
                "category": "reviewed_c679_to_b090_fake_transition",
            }
            if coarse != candidate_coarse:
                entry["candidate_coarse_decomposition"] = candidate_coarse
                entry["authority_adjustment"] = authority_row["authority"]
            entries.append(entry)
    for row in candidate["latest_b090_marker_only_delta"]:
        if row.get("status") != "candidate_ready":
            raise ValueError(f"unapproved B090 marker-only delta: {row!r}")
        entries.append({
            "learner_line": row["b090_fake"]["line"],
            "surface": row["surface"],
            "coarse_decomposition": row["proposed_coarse_decomposition"],
            "category": "reviewed_b090_marker_only_delta",
        })
    entries.sort(key=lambda row: row["learner_line"])
    lines = [row["learner_line"] for row in entries]
    if len(lines) != len(set(lines)):
        raise ValueError("transition manifest reused a learner line")
    surfaces = collections.Counter(row["surface"] for row in entries)
    categories = collections.Counter(row["category"] for row in entries)
    return {
        "schema_version": 1,
        "source_candidate_sha256": SOURCE_CANDIDATE_SHA256,
        "review_basis": (
            "Independent C679/B090 transition audit plus same-line paired-academic "
            "coarse authority; staged before the remaining full fake-row queue."
        ),
        "counts": {
            "entries": len(entries),
            "unique_surfaces": len(surfaces),
            "duplicate_surface_rows": sum(
                count - 1 for count in surfaces.values() if count > 1
            ),
            "categories": dict(categories),
            "authority_adjustments": sum(
                "authority_adjustment" in row for row in entries
            ),
        },
        "entries_sha256": entries_sha256(entries),
        "entries": entries,
    }


def validate(payload):
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported transition review schema")
    if payload.get("source_candidate_sha256") != SOURCE_CANDIDATE_SHA256:
        raise ValueError("transition review provenance changed")
    entries = payload.get("entries", [])
    if (
        payload.get("entries_sha256") != entries_sha256(entries)
        or payload.get("entries_sha256") != EXPECTED_ENTRIES_SHA256
    ):
        raise ValueError("transition review entry fingerprint mismatch")
    lines = [row.get("learner_line") for row in entries]
    if any(not isinstance(line, int) or line < 1 for line in lines):
        raise ValueError("transition review has invalid learner line")
    if len(lines) != len(set(lines)):
        raise ValueError("transition review reused a learner line")
    for row in entries:
        if (
            not row.get("surface") or not row.get("coarse_decomposition")
            or row.get("category") not in {
                "reviewed_c679_to_b090_fake_transition",
                "reviewed_b090_marker_only_delta",
            }
        ):
            raise ValueError(f"invalid transition row: {row!r}")
    surfaces = collections.Counter(row["surface"] for row in entries)
    categories = collections.Counter(row["category"] for row in entries)
    actual_counts = {
        "entries": len(entries),
        "unique_surfaces": len(surfaces),
        "duplicate_surface_rows": sum(
            count - 1 for count in surfaces.values() if count > 1
        ),
        "categories": dict(categories),
        "authority_adjustments": sum(
            "authority_adjustment" in row for row in entries
        ),
    }
    if actual_counts != EXPECTED_COUNTS:
        raise ValueError(
            f"transition review cardinality drift: {actual_counts!r} "
            f"!= {EXPECTED_COUNTS!r}"
        )
    if payload.get("counts") != actual_counts:
        raise ValueError("transition review counts changed")
    return actual_counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write-from-candidate", type=Path)
    modes.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.write_from_candidate:
        payload = build(args.write_from_candidate.resolve())
        validate(payload)
        atomic_json_dump(args.manifest, payload, indent=1)
        mode = "write"
    else:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        validate(payload)
        mode = "check"
    print(json.dumps({
        "manifest": str(args.manifest.resolve()),
        "mode": mode,
        "counts": payload["counts"],
        "entries_sha256": payload["entries_sha256"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
