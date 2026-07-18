# -*- coding: utf-8 -*-
"""Verify the frozen Phase513 -> Phase532 58-surface Ruby policy closure.

This command is deliberately check-only.  The ledgers are human decisions;
they are never regenerated from a moving master or silently rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import phase532_ruby_policy as policy


HERE = Path(__file__).resolve().parent
HISTORICAL_TRANSITION_PATH = HERE / "_fake_coarse_transition_review.json"
HISTORICAL_TRANSITION_SHA256 = (
    "D20633B41904776B5A6954F6EAC8F72335DCE3FEE51213AA9245A360E3027E34"
)
HISTORICAL_TRANSITION_ENTRIES_SHA256 = (
    "B8B1036BF0164960429B2FD079EBF62A71FA02425FC0A4D8EB7B84F127BCCF01"
)
EXPECTED_MASTER_LINES = 62313
EXPECTED_CANDIDATE_MANIFEST_COUNTS = {
    "entries": 3238,
    "marker_excluded_rows": 279,
    "marker_exclusions_by_reason": {
        "contains_space": 264,
        "non_evaluable_surface": 15,
    },
    "source_rows": {
        "pejvo_original": 1402,
        "pejvo_reviewed_override": 9,
        "paired_academic": 1825,
        "project_reviewed_override": 2,
    },
    "academic_rows_with_nonmatching_pejvo_homographs": 13,
    "exact_surfaces": 3222,
    "duplicate_exact_surface_rows": 16,
    "casefold_surfaces": 3211,
    "duplicate_casefold_surface_rows": 27,
}


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def find_by_sha(directory: Path, expected_sha256: str) -> Path:
    matches = [
        path.resolve() for path in directory.resolve().iterdir()
        if path.is_file() and sha256_file(path) == expected_sha256
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one {expected_sha256} file in {directory}, "
            f"found {matches!r}"
        )
    return matches[0]


def decomposition(line: str) -> str:
    return policy.canonical(line.lstrip("\ufeff").split(":", 1)[0].strip())


def surface(line: str) -> str:
    return policy.surface_from_decomposition(decomposition(line))


def metadata_free_rhs(line: str) -> str:
    if ":" not in line:
        return line.strip()
    return re.split(r"\s*##", line.split(":", 1)[1], maxsplit=1)[0].strip()


def read_bound_lines(path: Path, expected_sha256: str) -> tuple[bytes, list[str]]:
    raw = path.read_bytes()
    if sha256_bytes(raw) != expected_sha256:
        raise ValueError(f"frozen source identity changed: {path}")
    text = raw.decode("utf-8", errors="strict")
    lines = text.splitlines()
    if len(lines) != EXPECTED_MASTER_LINES:
        raise ValueError(f"frozen source line count changed: {path}")
    return raw, lines


def changed_lines(old_lines: list[str], new_lines: list[str]) -> set[int]:
    if len(old_lines) != len(new_lines):
        raise ValueError("master line count changed")
    return {
        line for line, (old, new) in enumerate(zip(old_lines, new_lines), 1)
        if old != new
    }


def validate_candidate_manifest(raw: bytes) -> tuple[dict, dict[int, dict]]:
    if sha256_bytes(raw) != policy.CANDIDATE_MANIFEST_SHA256:
        raise ValueError("Phase 532 candidate-manifest raw identity drift")
    payload = json.loads(raw.decode("utf-8"))
    entries = payload.get("entries")
    if (
        payload.get("schema_version") != 1
        or payload.get("counts") != EXPECTED_CANDIDATE_MANIFEST_COUNTS
        or payload.get("paired_invariant") != {
            "unmarked_rows": 58796,
            "unmarked_identical_decomposition": 58796,
            "academic_rows_without_fake_marker": 62313,
            "marked_rows": 3517,
            "marked_different_decomposition": 3517,
            "marked_gloss_context_matches_academic": 3517,
        }
        or policy.compact_sha256(entries)
        != policy.CANDIDATE_MANIFEST_ENTRIES_SHA256
        or payload.get("entries_sha256")
        != policy.CANDIDATE_MANIFEST_ENTRIES_SHA256
    ):
        raise ValueError("Phase 532 candidate-manifest semantic identity drift")
    expected_sources = {
        "learner": policy.CANDIDATE_LEARNER_SHA256,
        "academic": policy.CANDIDATE_ACADEMIC_SHA256,
        "pejvo_original": (
            "B551510513C1924E65E64CF87EA4CE39128E80717E3A3F53847753F8A0557CBF"
        ),
    }
    if any(
        payload.get("sources", {}).get(label, {}).get("sha256") != digest
        for label, digest in expected_sources.items()
    ):
        raise ValueError("Phase 532 candidate-manifest source drift")
    by_line = {entry.get("learner_line"): entry for entry in entries}
    if len(by_line) != len(entries) or None in by_line:
        raise ValueError("Phase 532 candidate-manifest line identity drift")
    return payload, by_line


def validate_historical_retirement(fake_review: dict) -> None:
    raw = HISTORICAL_TRANSITION_PATH.read_bytes()
    historical = json.loads(raw.decode("utf-8"))
    entries = historical.get("entries", [])
    if (
        sha256_bytes(raw) != HISTORICAL_TRANSITION_SHA256
        or historical.get("entries_sha256")
        != HISTORICAL_TRANSITION_ENTRIES_SHA256
        or policy.compact_sha256(entries)
        != HISTORICAL_TRANSITION_ENTRIES_SHA256
    ):
        raise ValueError("historical transition raw manifest changed")
    by_line = {entry["learner_line"]: entry for entry in entries}
    retired = fake_review["retired_historical_entries"][0]
    historical_entry = by_line.get(retired["learner_line"])
    if historical_entry != {
        "learner_line": 2704,
        "surface": "atletiko",
        "coarse_decomposition": "atletik/o",
        "category": "reviewed_c679_to_b090_fake_transition",
    }:
        raise ValueError("atletiko historical retirement provenance drift")


def validate_frozen_closure(
    baseline_dir: Path, candidate_dir: Path, candidate_manifest_path: Path,
) -> dict:
    baseline_dir = Path(baseline_dir)
    candidate_dir = Path(candidate_dir)
    candidate_manifest_path = Path(candidate_manifest_path)
    loaded = policy.load_phase532_policy()
    unmarked = loaded["unmarked"]
    fake = loaded["fake"]

    source_paths = {
        "baseline_learner": find_by_sha(
            baseline_dir, policy.BASELINE_LEARNER_SHA256,
        ),
        "baseline_academic": find_by_sha(
            baseline_dir, policy.BASELINE_ACADEMIC_SHA256,
        ),
        "candidate_learner": find_by_sha(
            candidate_dir, policy.CANDIDATE_LEARNER_SHA256,
        ),
        "candidate_academic": find_by_sha(
            candidate_dir, policy.CANDIDATE_ACADEMIC_SHA256,
        ),
    }
    inputs = [
        *source_paths.values(), candidate_manifest_path.resolve(),
        policy.UNMARKED_REVIEW_PATH, policy.FAKE_TRANSITION_PATH,
        HISTORICAL_TRANSITION_PATH, Path(__file__).resolve(),
        Path(policy.__file__).resolve(),
    ]
    start_hashes = {path: sha256_file(path) for path in inputs}
    parsed = {}
    for label, path in source_paths.items():
        expected = {
            "baseline_learner": policy.BASELINE_LEARNER_SHA256,
            "baseline_academic": policy.BASELINE_ACADEMIC_SHA256,
            "candidate_learner": policy.CANDIDATE_LEARNER_SHA256,
            "candidate_academic": policy.CANDIDATE_ACADEMIC_SHA256,
        }[label]
        _raw, parsed[label] = read_bound_lines(path, expected)
    manifest_raw = candidate_manifest_path.resolve().read_bytes()
    _manifest, candidate_by_line = validate_candidate_manifest(manifest_raw)
    validate_historical_retirement(fake)

    raw_changed = changed_lines(
        parsed["baseline_learner"], parsed["candidate_learner"],
    ) | changed_lines(
        parsed["baseline_academic"], parsed["candidate_academic"],
    )
    reviewed_entries = [*unmarked["entries"], *fake["entries"]]
    reviewed_lines = {entry["learner_line"] for entry in reviewed_entries}
    if raw_changed != reviewed_lines or len(reviewed_lines) != 58:
        raise ValueError(
            "Phase 532 raw delta escaped its 58-row closed set: "
            f"missing={sorted(raw_changed - reviewed_lines)!r}, "
            f"extra={sorted(reviewed_lines - raw_changed)!r}"
        )

    for entry in reviewed_entries:
        line_number = entry["learner_line"]
        rows = {
            label: lines[line_number - 1] for label, lines in parsed.items()
        }
        surfaces = {surface(line) for line in rows.values()}
        if surfaces != {policy.canonical(entry["surface"])}:
            raise ValueError(f"Phase 532 surface drift at line {line_number}")
        if (
            metadata_free_rhs(rows["baseline_learner"])
            != metadata_free_rhs(rows["candidate_learner"])
            or metadata_free_rhs(rows["baseline_academic"])
            != metadata_free_rhs(rows["candidate_academic"])
            or metadata_free_rhs(rows["candidate_learner"])
            != metadata_free_rhs(rows["candidate_academic"])
        ):
            raise ValueError(f"Phase 532 gloss drift at line {line_number}")
        is_fake = entry in fake["entries"]
        candidate_learner_line = rows["candidate_learner"]
        candidate_academic_line = rows["candidate_academic"]
        if is_fake:
            authority = candidate_by_line.get(line_number)
            disposition = entry["disposition"]
            if disposition == "keep_academic_coarse_for_ruby":
                selected_target_matches = (
                    authority is not None
                    and decomposition(rows["baseline_learner"])
                    == entry["target"]
                    and decomposition(rows["baseline_academic"])
                    == entry["target"]
                    and authority.get("coarse_decomposition") == entry["target"]
                    and authority.get("academic_decomposition") == entry["target"]
                )
            elif disposition == "adopt_productive_ruby_repair":
                selected_target_matches = (
                    authority is not None
                    and authority.get("coarse_decomposition") == entry["target"]
                    and authority.get("academic_decomposition") == entry["target"]
                )
            elif disposition in {
                "retain_current_outer_ik_pending",
                "retain_current_missing_parent_translation",
            }:
                selected_target_matches = (
                    authority is not None
                    and decomposition(rows["baseline_learner"])
                    == entry["target"]
                    and decomposition(candidate_learner_line) == entry["target"]
                )
            else:
                selected_target_matches = False
            if (
                "##偽分解" not in candidate_learner_line
                or "##偽分解" in candidate_academic_line
                or authority is None
                or authority.get("surface") != entry["surface"]
                or authority.get("learner_decomposition")
                != decomposition(candidate_learner_line)
                or authority.get("academic_decomposition")
                != decomposition(candidate_academic_line)
                or not selected_target_matches
            ):
                raise ValueError(
                    f"Phase 532 fake/coarse authority drift at line {line_number}"
                )
        elif (
            "##偽分解" in candidate_learner_line
            or line_number in candidate_by_line
        ):
            raise ValueError(
                f"Phase 532 unmarked disposition became fake at line {line_number}"
            )
        else:
            selected = entry["selected_ruby_decomposition"]
            disposition = entry["disposition"]
            if disposition == "adopt_shared_ruby_repair":
                selected_target_matches = (
                    decomposition(candidate_learner_line) == selected
                    and decomposition(candidate_academic_line) == selected
                )
            elif disposition == "already_aligned":
                selected_target_matches = (
                    decomposition(rows["baseline_academic"]) == selected
                    and decomposition(candidate_learner_line) == selected
                    and decomposition(candidate_academic_line) == selected
                )
            elif disposition == "retain_current_granularity_pending":
                selected_target_matches = (
                    decomposition(rows["baseline_academic"]) == selected
                )
            else:
                selected_target_matches = False
            if not selected_target_matches:
                raise ValueError(
                    "Phase 532 unmarked selected-boundary provenance drift "
                    f"at line {line_number}"
                )

    retired_line = fake["retired_historical_entries"][0]["learner_line"]
    if (
        retired_line not in {e["learner_line"] for e in unmarked["entries"]}
        or retired_line in candidate_by_line
        or "##偽分解" in parsed["candidate_learner"][retired_line - 1]
    ):
        raise ValueError("Phase 532 atletiko retirement is not fail-closed")

    end_hashes = {path: sha256_file(path) for path in inputs}
    if start_hashes != end_hashes:
        raise ValueError("Phase 532 audit input changed during validation")
    return {
        "phase": policy.PHASE,
        "baseline_learner_sha256": policy.BASELINE_LEARNER_SHA256,
        "candidate_learner_sha256": policy.CANDIDATE_LEARNER_SHA256,
        "changed_surface_union": len(reviewed_lines),
        "unmarked_dispositions": len(unmarked["entries"]),
        "fake_transitions": len(fake["entries"]),
        "retired_historical_transitions": len(
            fake["retired_historical_entries"]
        ),
        "safe_managed_targets": len(loaded["safe_targets"]),
        "retained_phase513_ruby_targets": (
            len(reviewed_lines) - len(loaded["safe_targets"])
        ),
        "adopted_reviewed_ruby_repairs": len(loaded["safe_targets"]),
        "adopted_shared_repairs": sum(
            reviewed["track"] == "shared"
            for reviewed in loaded["safe_targets"].values()
        ),
        "adopted_ruby_track_only_repairs": sum(
            reviewed["track"] == "ruby"
            for reviewed in loaded["safe_targets"].values()
        ),
        "review_identity": policy.review_identity(),
        "all_inputs_stable": True,
        "gate": True,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--check", action="store_true", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    report = validate_frozen_closure(
        args.baseline_dir, args.candidate_dir, args.candidate_manifest,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
