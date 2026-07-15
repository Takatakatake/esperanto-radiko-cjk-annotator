# -*- coding: utf-8 -*-
"""Build/check the fixed coarse-Ruby authority for learner fake rows.

The learner and academic masters are a line-paired snapshot: every learner
``##偽分解`` row has a different, reconstructing academic decomposition, while
every unmarked row has the same decomposition.  The original PEJVO is the
higher corroborating authority only where its signature matches the paired
academic row.  A surface-only PEJVO disagreement is recorded but never used
as an automatic override because it may be a different homograph.  Entries
remain line-specific so duplicate/casefold surfaces are fully accounted rather
than collapsed through runtime output.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from atomic_json import atomic_json_dump
import no_worsening_audit as audit


DEFAULT_MANIFEST = HERE / "_fake_coarse_reference_manifest.json"
DEFAULT_REVIEW = HERE / "_fake_coarse_pejvo_disagreement_review.json"
DEFAULT_PROJECT_REVIEW = HERE / "_fake_coarse_project_boundary_review.json"


def identity(path, raw, lines):
    return {
        "name": path.name,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "lines": len(lines),
    }


def parsed_row(line, line_number):
    if ":" not in line:
        return None, "missing_colon"
    decomposition = line.lstrip("\ufeff").split(":", 1)[0].strip()
    if not decomposition:
        return None, "empty_decomposition"
    if " " in decomposition:
        return None, "contains_space"
    if decomposition.startswith("-") or decomposition.endswith("-"):
        return None, "edge_affix"
    pieces = [
        audit.canonical(piece)
        for piece in decomposition.split("/")
        if audit.canonical(piece)
    ]
    surface = audit.canonical("".join(pieces))
    if not audit.evaluable(surface):
        return None, "non_evaluable_surface"
    return {
        "line": line_number,
        "surface": surface,
        "decomposition": "/".join(pieces),
        "signature": audit.expected_signature("/".join(pieces)),
    }, None


def load_lines(path):
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    return raw, text.splitlines()


def load_disagreement_review(
    path, allowed_decisions=frozenset({"pejvo_coarse", "paired_academic"}),
):
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported PEJVO disagreement-review schema")
    entries = payload.get("entries", [])
    if len(entries) != payload.get("expected_entries"):
        raise ValueError("PEJVO disagreement-review entry count changed")
    by_line = {}
    for entry in entries:
        line = entry.get("learner_line")
        if (
            not isinstance(line, int) or line in by_line
            or entry.get("decision") not in allowed_decisions
            or not entry.get("reason")
        ):
            raise ValueError(f"invalid PEJVO disagreement review: {entry!r}")
        by_line[line] = entry
    return by_line, {
        "path": path.name,
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "entries": len(entries),
    }


def build(
    learner_path, academic_path, original_path, review_path=DEFAULT_REVIEW,
    project_review_path=DEFAULT_PROJECT_REVIEW,
):
    learner_raw, learner_lines = load_lines(learner_path)
    academic_raw, academic_lines = load_lines(academic_path)
    original_raw, original_lines = load_lines(original_path)
    disagreement_review, review_identity = load_disagreement_review(review_path)
    project_review, project_review_identity = load_disagreement_review(
        project_review_path, frozenset({
            "project_piv_long_root",
            "project_conservative_ruby_display_override",
        }),
    )
    used_reviews = set()
    used_project_reviews = set()
    if len(learner_lines) != len(academic_lines):
        raise ValueError("learner/academic line counts differ")

    original_by_surface = collections.defaultdict(list)
    for line_number, line in enumerate(original_lines, 1):
        row, _reason = parsed_row(line, line_number)
        if row is not None:
            original_by_surface[row["surface"]].append(row)

    entries = []
    marker_exclusions = collections.Counter()
    invariant = collections.Counter()
    source_counts = collections.Counter()
    marked_exact_surfaces = []
    marked_casefold_surfaces = []
    for line_number, (learner_line, academic_line) in enumerate(
        zip(learner_lines, academic_lines), 1
    ):
        learner_decomposition = learner_line.lstrip("\ufeff").split(":", 1)[0].strip()
        academic_decomposition = academic_line.lstrip("\ufeff").split(":", 1)[0].strip()
        marked = bool(audit.FAKE_MARKER_RE.search(learner_line))
        if audit.FAKE_MARKER_RE.search(academic_line):
            raise ValueError(f"academic row contains fake marker at line {line_number}")
        if marked:
            invariant["marked_rows"] += 1
            if learner_decomposition == academic_decomposition:
                raise ValueError(
                    f"marked learner row did not differ from academic line {line_number}"
                )
            invariant["marked_different_decomposition"] += 1
            learner_without_marker_suffix = audit.FAKE_MARKER_RE.split(
                learner_line, maxsplit=1,
            )[0]
            if ":" not in learner_without_marker_suffix or ":" not in academic_line:
                raise ValueError(
                    f"marked learner/academic gloss is unavailable at line {line_number}"
                )
            learner_gloss = learner_without_marker_suffix.split(":", 1)[1]
            academic_gloss = academic_line.split(":", 1)[1]
            if learner_gloss != academic_gloss:
                raise ValueError(
                    f"marked learner/academic sense context drift at line {line_number}"
                )
            invariant["marked_gloss_context_matches_academic"] += 1
        else:
            invariant["unmarked_rows"] += 1
            if learner_decomposition != academic_decomposition:
                raise ValueError(
                    f"unmarked learner/academic decomposition drift at line {line_number}"
                )
            invariant["unmarked_identical_decomposition"] += 1
        invariant["academic_rows_without_fake_marker"] += 1

        learner_row, learner_reason = parsed_row(learner_line, line_number)
        academic_row, academic_reason = parsed_row(academic_line, line_number)
        if not marked:
            continue
        if learner_row is None or academic_row is None:
            if learner_reason != academic_reason:
                raise ValueError(
                    f"paired marker eligibility differs at line {line_number}: "
                    f"learner={learner_reason}, academic={academic_reason}"
                )
            marker_exclusions[learner_reason] += 1
            continue
        if learner_row["surface"].casefold() != academic_row["surface"].casefold():
            raise ValueError(f"paired marker surface differs at line {line_number}")

        academic_signature = academic_row["signature"]
        original_rows = original_by_surface.get(academic_row["surface"], [])
        original_by_signature = collections.defaultdict(list)
        for row in original_rows:
            original_by_signature[row["signature"]].append(row)
        if academic_signature in original_by_signature:
            if line_number in disagreement_review:
                raise ValueError(
                    f"stale PEJVO disagreement review at learner line {line_number}"
                )
            selected = original_by_signature[academic_signature][0]
            authority = "pejvo_original"
            authority_lines = [
                row["line"] for row in original_by_signature[academic_signature]
            ]
        elif original_by_signature:
            # A surface-only PEJVO hit is not a sense-aligned authority.  A
            # sole mismatching signature can be a different homograph just as
            # readily as several signatures can (e.g. heroino, kateto and
            # Bonaero).  The paired academic row shares this exact learner
            # line's gloss/context, so retain it and record every nonmatching
            # PEJVO candidate for review instead of auto-overriding it.
            review = disagreement_review.get(line_number)
            if review is None:
                raise ValueError(
                    "unreviewed PEJVO/academic disagreement at learner line "
                    f"{line_number}: {academic_row['surface']!r}"
                )
            available_decompositions = sorted(
                rows[0]["decomposition"] for rows in original_by_signature.values()
            )
            if (
                review.get("surface") != academic_row["surface"]
                or review.get("academic_decomposition")
                != academic_row["decomposition"]
                or review.get("pejvo_decompositions") != available_decompositions
            ):
                raise ValueError(
                    f"PEJVO disagreement-review context drift at line {line_number}"
                )
            selected_decomposition = review.get("selected_decomposition")
            if review["decision"] == "paired_academic":
                if selected_decomposition != academic_row["decomposition"]:
                    raise ValueError(
                        f"academic review selected another boundary at line {line_number}"
                    )
                selected = academic_row
                authority = "paired_academic"
                authority_lines = [line_number]
            else:
                selected_rows = [
                    row for rows in original_by_signature.values() for row in rows
                    if row["decomposition"] == selected_decomposition
                ]
                if not selected_rows:
                    raise ValueError(
                        f"review selected absent PEJVO boundary at line {line_number}"
                    )
                selected = selected_rows[0]
                authority = "pejvo_reviewed_override"
                authority_lines = [row["line"] for row in selected_rows]
            used_reviews.add(line_number)
        else:
            if line_number in disagreement_review:
                raise ValueError(
                    f"stale PEJVO disagreement review at learner line {line_number}"
                )
            selected = academic_row
            authority = "paired_academic"
            authority_lines = [line_number]

        project_entry = project_review.get(line_number)
        if project_entry is not None:
            if (
                project_entry.get("surface") != academic_row["surface"]
                or project_entry.get("academic_decomposition")
                != academic_row["decomposition"]
                or project_entry.get("decision") not in {
                    "project_piv_long_root",
                    "project_conservative_ruby_display_override",
                }
                or not project_entry.get("evidence")
            ):
                raise ValueError(
                    f"project boundary-review context drift at line {line_number}"
                )
            selected_decomposition = project_entry.get("selected_decomposition", "")
            selected_surface = audit.expected_signature(selected_decomposition)[0]
            if selected_surface != academic_row["surface"]:
                raise ValueError(
                    f"project boundary review does not reconstruct line {line_number}"
                )
            selected = {
                "surface": selected_surface,
                "decomposition": selected_decomposition,
                "line": line_number,
            }
            authority = "project_reviewed_override"
            authority_lines = [line_number]
            used_project_reviews.add(line_number)

        if selected["surface"].casefold() != learner_row["surface"].casefold():
            raise ValueError(f"selected authority reconstruction drift at line {line_number}")
        source_counts[authority] += 1
        # The fake learner decomposition may itself destroy a semantically
        # meaningful initial capital (the paired velaro/Velaro senses are the
        # concrete example).  Runtime matching is case-sensitive, so retain
        # the exact surface reconstructed by the non-fake authority and keep
        # the learner reconstruction only as line-level provenance.
        marked_exact_surfaces.append(selected["surface"])
        marked_casefold_surfaces.append(selected["surface"].casefold())
        entry = {
            "learner_line": line_number,
            "surface": selected["surface"],
            "learner_surface": learner_row["surface"],
            "learner_decomposition": learner_row["decomposition"],
            "coarse_decomposition": selected["decomposition"],
            "academic_decomposition": academic_row["decomposition"],
            "authority": authority,
            "authority_lines": authority_lines,
        }
        if original_by_signature and academic_signature not in original_by_signature:
            entry["nonmatching_pejvo_candidates"] = [
                {
                    "decomposition": rows[0]["decomposition"],
                    "lines": [row["line"] for row in rows],
                }
                for _signature, rows in sorted(
                    original_by_signature.items(),
                    key=lambda item: item[1][0]["decomposition"],
                )
            ]
            entry["disagreement_review_decision"] = review["decision"]
        if project_entry is not None:
            entry["project_boundary_review_decision"] = project_entry["decision"]
        entries.append(entry)

    entry_lines = [row["learner_line"] for row in entries]
    if len(entry_lines) != len(set(entry_lines)):
        raise ValueError("coarse authority reused a learner line")
    if used_reviews != set(disagreement_review):
        raise ValueError(
            "unused PEJVO disagreement reviews: "
            f"{sorted(set(disagreement_review) - used_reviews)!r}"
        )
    if used_project_reviews != set(project_review):
        raise ValueError(
            "unused project boundary reviews: "
            f"{sorted(set(project_review) - used_project_reviews)!r}"
        )
    entry_raw = json.dumps(
        entries, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    exact_counts = collections.Counter(marked_exact_surfaces)
    casefold_counts = collections.Counter(marked_casefold_surfaces)
    return {
        "schema_version": 1,
        "sources": {
            "learner": identity(learner_path, learner_raw, learner_lines),
            "academic": identity(academic_path, academic_raw, academic_lines),
            "pejvo_original": identity(original_path, original_raw, original_lines),
        },
        "pejvo_disagreement_review": review_identity,
        "project_boundary_review": project_review_identity,
        "paired_invariant": dict(invariant),
        "counts": {
            "entries": len(entries),
            "marker_excluded_rows": sum(marker_exclusions.values()),
            "marker_exclusions_by_reason": dict(marker_exclusions),
            "source_rows": dict(source_counts),
            "academic_rows_with_nonmatching_pejvo_homographs": sum(
                "nonmatching_pejvo_candidates" in entry for entry in entries
            ),
            "exact_surfaces": len(exact_counts),
            "duplicate_exact_surface_rows": sum(
                count - 1 for count in exact_counts.values() if count > 1
            ),
            "casefold_surfaces": len(casefold_counts),
            "duplicate_casefold_surface_rows": sum(
                count - 1 for count in casefold_counts.values() if count > 1
            ),
        },
        "entries_sha256": hashlib.sha256(entry_raw).hexdigest().upper(),
        "entries": entries,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--learner", type=Path, required=True)
    parser.add_argument("--academic", type=Path, required=True)
    parser.add_argument("--pejvo-original", type=Path, required=True)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument(
        "--project-review", type=Path, default=DEFAULT_PROJECT_REVIEW,
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    payload = build(
        args.learner.resolve(), args.academic.resolve(),
        args.pejvo_original.resolve(), args.review.resolve(),
        args.project_review.resolve(),
    )
    if args.write:
        atomic_json_dump(args.manifest, payload, indent=1)
    else:
        expected = json.loads(args.manifest.read_text(encoding="utf-8"))
        if payload != expected:
            raise SystemExit("fake coarse reference manifest drift")
    print(json.dumps({
        "manifest": str(args.manifest.resolve()),
        "sources": payload["sources"],
        "paired_invariant": payload["paired_invariant"],
        "counts": payload["counts"],
        "entries_sha256": payload["entries_sha256"],
        "mode": "write" if args.write else "check",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
