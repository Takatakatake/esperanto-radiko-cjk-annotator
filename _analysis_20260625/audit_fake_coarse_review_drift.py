# -*- coding: utf-8 -*-
"""List review-ledger drift for a frozen learner/academic master pair.

``build_fake_coarse_reference_manifest.py`` is intentionally fail-fast: the
first new PEJVO/academic disagreement stops a formal build.  That is correct
for promotion, but it hides the size of the review queue.  This read-only
companion enumerates the complete missing/stale queue without choosing a
boundary or editing any authority file.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from atomic_json import atomic_json_dump
import build_fake_coarse_reference_manifest as builder
import no_worsening_audit as audit


def source_identity(path: Path, raw: bytes, lines: list[str]) -> dict:
    return {
        "path": str(path),
        "bytes": len(raw),
        "lines": len(lines),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def load(path: Path) -> tuple[bytes, list[str]]:
    raw = path.read_bytes()
    return raw, raw.decode("utf-8", errors="strict").splitlines()


def build_report(
    learner_path: Path,
    academic_path: Path,
    original_path: Path,
    review_path: Path,
) -> dict:
    learner_raw, learner_lines = load(learner_path)
    academic_raw, academic_lines = load(academic_path)
    original_raw, original_lines = load(original_path)
    if len(learner_lines) != len(academic_lines):
        raise ValueError("learner/academic line counts differ")

    reviews, review_identity = builder.load_disagreement_review(review_path)
    original_by_surface = collections.defaultdict(list)
    for line_number, line in enumerate(original_lines, 1):
        row, _reason = builder.parsed_row(line, line_number)
        if row is not None:
            original_by_surface[row["surface"]].append(row)

    missing = []
    encountered_review_lines = set()
    matched_review_lines = set()
    marked_rows = 0
    evaluable_marked_rows = 0
    disagreement_rows = 0
    for line_number, (learner_line, academic_line) in enumerate(
        zip(learner_lines, academic_lines), 1
    ):
        if not audit.FAKE_MARKER_RE.search(learner_line):
            continue
        marked_rows += 1
        if audit.FAKE_MARKER_RE.search(academic_line):
            raise ValueError(
                f"academic row contains fake marker at line {line_number}"
            )
        learner_row, learner_reason = builder.parsed_row(
            learner_line, line_number,
        )
        academic_row, academic_reason = builder.parsed_row(
            academic_line, line_number,
        )
        if learner_row is None or academic_row is None:
            if learner_reason != academic_reason:
                raise ValueError(
                    "paired marker eligibility differs at line "
                    f"{line_number}: learner={learner_reason}, "
                    f"academic={academic_reason}"
                )
            continue
        evaluable_marked_rows += 1
        if learner_row["surface"].casefold() != (
            academic_row["surface"].casefold()
        ):
            raise ValueError(
                f"paired marker surface differs at line {line_number}"
            )

        original_rows = original_by_surface.get(academic_row["surface"], [])
        by_signature = collections.defaultdict(list)
        for row in original_rows:
            by_signature[row["signature"]].append(row)
        if (
            not by_signature
            or academic_row["signature"] in by_signature
        ):
            continue
        disagreement_rows += 1
        available = sorted(
            rows[0]["decomposition"] for rows in by_signature.values()
        )
        review = reviews.get(line_number)
        context = {
            "learner_line": line_number,
            "surface": academic_row["surface"],
            "learner_decomposition": learner_row["decomposition"],
            "academic_decomposition": academic_row["decomposition"],
            "pejvo_decompositions": available,
            "pejvo_candidates": [
                {
                    "decomposition": rows[0]["decomposition"],
                    "lines": [row["line"] for row in rows],
                }
                for _signature, rows in sorted(
                    by_signature.items(),
                    key=lambda item: item[1][0]["decomposition"],
                )
            ],
        }
        if review is None:
            missing.append(context)
            continue
        encountered_review_lines.add(line_number)
        expected_context = {
            "surface": academic_row["surface"],
            "academic_decomposition": academic_row["decomposition"],
            "pejvo_decompositions": available,
        }
        actual_context = {
            key: review.get(key) for key in expected_context
        }
        if actual_context != expected_context:
            missing.append({
                **context,
                "kind": "existing_review_context_drift",
                "existing_review": review,
            })
            continue
        selected_decomposition = review.get("selected_decomposition")
        if review["decision"] == "paired_academic":
            selection_is_valid = (
                selected_decomposition == academic_row["decomposition"]
            )
            selection_rule = (
                "paired_academic must select academic_decomposition"
            )
        else:
            selection_is_valid = selected_decomposition in available
            selection_rule = (
                "pejvo_coarse must select one available "
                "pejvo_decomposition"
            )
        if not selection_is_valid:
            missing.append({
                **context,
                "kind": "existing_review_decision_drift",
                "selection_rule": selection_rule,
                "existing_review": review,
            })
            continue
        matched_review_lines.add(line_number)

    # A review whose source context or selected decision drifted is active but
    # invalid, not stale.  Reserve "stale" for a ledger row which no longer
    # corresponds to any PEJVO/academic disagreement.
    stale_review_lines = sorted(set(reviews) - encountered_review_lines)
    stale_reviews = [
        {"learner_line": line, "existing_review": reviews[line]}
        for line in stale_review_lines
    ]
    return {
        "schema_version": 1,
        "algorithm": "fake-coarse-review-ledger-drift-v1",
        "sources": {
            "learner": source_identity(
                learner_path, learner_raw, learner_lines,
            ),
            "academic": source_identity(
                academic_path, academic_raw, academic_lines,
            ),
            "pejvo_original": source_identity(
                original_path, original_raw, original_lines,
            ),
            "review": {
                **review_identity,
                "path": str(review_path),
            },
        },
        "counts": {
            "marked_rows": marked_rows,
            "evaluable_marked_rows": evaluable_marked_rows,
            "pejvo_academic_disagreement_rows": disagreement_rows,
            "encountered_existing_reviews": len(
                encountered_review_lines
            ),
            "matched_existing_reviews": len(matched_review_lines),
            "missing_or_drifted_reviews": len(missing),
            "stale_reviews": len(stale_reviews),
        },
        "missing_or_drifted_reviews": missing,
        "stale_reviews": stale_reviews,
        "review_ledger_closed": not missing and not stale_reviews,
        "formal_manifest_review_prerequisite_satisfied": (
            not missing and not stale_reviews
        ),
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--learner", type=Path, required=True)
    parser.add_argument("--academic", type=Path, required=True)
    parser.add_argument("--pejvo-original", type=Path, required=True)
    parser.add_argument(
        "--review",
        type=Path,
        default=builder.DEFAULT_REVIEW,
    )
    parser.add_argument("--report", type=Path)
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    report = build_report(
        args.learner.resolve(),
        args.academic.resolve(),
        args.pejvo_original.resolve(),
        args.review.resolve(),
    )
    if args.report is not None:
        atomic_json_dump(args.report, report, indent=1)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
