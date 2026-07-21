# -*- coding: utf-8 -*-
"""Revalidate the frozen Phase 532 -> 558 source closure for the Ruby sidecar."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import phase558_ruby_overlay as policy
from phase532_ruby_policy import canonical, surface_from_decomposition

sys.stdout.reconfigure(encoding="utf-8")


EXPECTED_LEARNER_CHANGED_ROWS = 87
EXPECTED_ACADEMIC_CHANGED_ROWS = 4
EXPECTED_CHANGED_SURFACES = 85
EXPECTED_CHANGED_SURFACES_SHA256 = (
    "66E83AAD3C47C212A83D623E2627A0A359B71383E63D3E34E204482961FA6DD5"
)
PHASE558_DELTA_GROUPS = (
    "G_phase533_558_kanji_only_decomposition_keep_ruby_coarse",
    "H_phase533_558_marker_metadata_only_boundary_unchanged",
    "I_phase533_558_fake_marker_retired_adopt_coarse_fusion_ruby",
    "J_phase533_558_shared_ordinary_boundary_keep_deployed_coarse_ruby",
    "K_phase533_558_shared_ordinary_boundary_adopt_reviewed_ruby_repair",
)
SELECTED_LEDGER_GROUPS = (
    "I_phase533_558_fake_marker_retired_adopt_coarse_fusion_ruby",
    "K_phase533_558_shared_ordinary_boundary_adopt_reviewed_ruby_repair",
)
KEEP_COARSE_LEDGER_GROUP = (
    "J_phase533_558_shared_ordinary_boundary_keep_deployed_coarse_ruby"
)


def compact_sha256(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def find_bound_file(directory: Path, expected: dict) -> Path:
    directory = directory.resolve()
    matches = [
        path.resolve() for path in directory.iterdir()
        if path.is_file()
        and path.stat().st_size == expected["bytes"]
        and file_sha256(path) == expected["sha256"]
    ]
    if len(matches) != 1 or matches[0].parent != directory:
        raise ValueError(
            f"expected one frozen {expected['sha256']} file in {directory}, "
            f"found {matches!r}"
        )
    return matches[0]


def read_lines(path: Path, expected: dict) -> list[str]:
    raw = path.read_bytes()
    if (
        len(raw) != expected["bytes"]
        or hashlib.sha256(raw).hexdigest().upper() != expected["sha256"]
    ):
        raise ValueError(f"frozen source identity changed: {path}")
    lines = raw.decode("utf-8", errors="strict").splitlines()
    if len(lines) != expected["lines"]:
        raise ValueError(f"frozen source line count changed: {path}")
    return lines


def decomposition(line: str) -> str:
    return canonical(line.lstrip("\ufeff").split(":", 1)[0].strip())


def surface(line: str) -> str:
    return surface_from_decomposition(decomposition(line))


def metadata_free_rhs(line: str) -> str:
    if ":" not in line:
        return line.strip()
    return re.split(r"\s*##", line.split(":", 1)[1], maxsplit=1)[0].strip()


def changed_rows(old: list[str], new: list[str]) -> list[dict]:
    if len(old) != len(new):
        raise ValueError("master line count changed")
    rows = []
    for line_number, (before, after) in enumerate(zip(old, new), 1):
        if before == after:
            continue
        before_surface = surface(before)
        after_surface = surface(after)
        if before_surface != after_surface:
            raise ValueError(
                f"Phase 558 changed visible surface at line {line_number}: "
                f"{before_surface!r} -> {after_surface!r}"
            )
        rows.append({
            "line": line_number,
            "surface": before_surface,
            "before": decomposition(before),
            "after": decomposition(after),
            "gloss_unchanged_before_metadata": (
                metadata_free_rhs(before) == metadata_free_rhs(after)
            ),
        })
    return rows


def validate_frozen_closure(
    phase532_dir: Path, phase558_dir: Path, disposition_ledger: Path,
    japanese_guide: Path, chinese_guide: Path,
) -> dict:
    review = policy.load_review()
    sources = policy.EXPECTED_SOURCES
    external_paths = {
        "ruby_track_disposition_ledger": Path(disposition_ledger).resolve(),
        "japanese_guide": Path(japanese_guide).resolve(),
        "chinese_guide": Path(chinese_guide).resolve(),
    }
    external_hashes_before = {}
    for key, path in external_paths.items():
        if not path.is_file():
            raise ValueError(f"Phase 558 external authority is missing: {path}")
        expected = sources[key]
        raw = path.read_bytes()
        if (
            len(raw) != expected.get("bytes", len(raw))
            or hashlib.sha256(raw).hexdigest().upper() != expected["sha256"]
        ):
            raise ValueError(f"Phase 558 external authority drift: {key}")
        external_hashes_before[key] = file_sha256(path)

    ledger = json.loads(
        external_paths["ruby_track_disposition_ledger"].read_text(
            encoding="utf-8"
        )
    )
    groups = ledger.get("groups")
    expected_counts = ledger.get("expected_counts")
    if (
        ledger.get("schema_version") != 1
        or ledger.get("candidate_only") is not True
        or ledger.get("source_phase") != policy.PHASE_TO
        or ledger.get("sources", {}).get("candidate_learner_sha256")
        != sources["phase558_learner"]["sha256"]
        or ledger.get("sources", {}).get("candidate_academic_sha256")
        != sources["phase558_academic"]["sha256"]
        or not isinstance(groups, dict)
        or not isinstance(expected_counts, dict)
        or expected_counts.get("union")
        != sources["ruby_track_disposition_ledger"]["changed_surfaces"]
        or not isinstance(ledger.get("promotion_gate"), bool)
        or not isinstance(ledger.get("promotion_blockers"), list)
        or any(
            not isinstance(blocker, str) or not blocker.strip()
            for blocker in ledger.get("promotion_blockers", [])
        )
    ):
        raise ValueError("Phase 558 disposition ledger header drift")
    ledger_surfaces = []
    for name, expected_count in expected_counts.items():
        if name == "union":
            continue
        rows = groups.get(name)
        if not isinstance(rows, list) or len(rows) != expected_count:
            raise ValueError(f"Phase 558 disposition group drift: {name}")
        ledger_surfaces.extend(rows)
    if (
        len(ledger_surfaces) != expected_counts["union"]
        or len(set(ledger_surfaces)) != expected_counts["union"]
    ):
        raise ValueError("Phase 558 disposition union is not a partition")
    paths = {}
    lines = {}
    source_hashes_before = {}
    for phase, directory in (
        ("phase532", phase532_dir), ("phase558", phase558_dir),
    ):
        for track in ("learner", "academic"):
            key = f"{phase}_{track}"
            expected = sources[key]
            path = find_bound_file(Path(directory), expected)
            paths[key] = path
            # Record the first accepted identity before parsing.  The former
            # end-of-function ``before``/``after`` pair was sampled twice in
            # immediate succession and therefore could not detect a source
            # that changed after ``read_lines`` had consumed it.
            source_hashes_before[key] = file_sha256(path)
            if source_hashes_before[key] != expected["sha256"]:
                raise ValueError(f"Phase 558 frozen source drift: {key}")
            lines[key] = read_lines(path, expected)

    learner_delta = changed_rows(
        lines["phase532_learner"], lines["phase558_learner"],
    )
    academic_delta = changed_rows(
        lines["phase532_academic"], lines["phase558_academic"],
    )
    changed_surfaces = sorted({
        row["surface"] for row in learner_delta + academic_delta
    })
    if (
        len(learner_delta) != EXPECTED_LEARNER_CHANGED_ROWS
        or len(academic_delta) != EXPECTED_ACADEMIC_CHANGED_ROWS
        or len(changed_surfaces) != EXPECTED_CHANGED_SURFACES
        or compact_sha256(changed_surfaces)
        != EXPECTED_CHANGED_SURFACES_SHA256
    ):
        raise ValueError("Phase 532 -> 558 exact source delta drift")
    phase558_delta_authority = {
        surface
        for group in PHASE558_DELTA_GROUPS
        for surface in groups[group]
    }
    selected_authority = {
        surface
        for group in SELECTED_LEDGER_GROUPS
        for surface in groups[group]
    }
    if (
        phase558_delta_authority != set(changed_surfaces)
        or selected_authority != set(policy.selected_ruby_targets())
        or set(groups[KEEP_COARSE_LEDGER_GROUP])
        != {"monarĥio", "oligarĥio"}
    ):
        raise ValueError("Phase 558 disposition-to-source closure drift")

    by_surface = {
        row["surface"]: row for row in learner_delta + academic_delta
    }
    selected = []
    for entry in review["entries"]:
        line_number = entry["learner_line"]
        exact_lines = {
            "phase532_learner_line": lines["phase532_learner"][line_number - 1],
            "phase532_academic_line": lines["phase532_academic"][line_number - 1],
            "phase558_learner_line": lines["phase558_learner"][line_number - 1],
            "phase558_academic_line": lines["phase558_academic"][line_number - 1],
        }
        if any(entry[key] != value for key, value in exact_lines.items()):
            raise ValueError(
                f"Phase 558 reviewed source row changed: {entry['surface']!r}"
            )
        if (
            entry["surface"] not in by_surface
            or any(surface(value) != entry["surface"] for value in exact_lines.values())
            or metadata_free_rhs(exact_lines["phase532_learner_line"])
            != metadata_free_rhs(exact_lines["phase558_learner_line"])
            or metadata_free_rhs(exact_lines["phase532_academic_line"])
            != metadata_free_rhs(exact_lines["phase558_academic_line"])
        ):
            raise ValueError(
                f"Phase 558 reviewed row provenance drift: {entry['surface']!r}"
            )
        selected.append({
            "line": line_number,
            "surface": entry["surface"],
            "selected_ruby_target": entry["selected_ruby_target"],
        })

    after_hashes = {key: file_sha256(path) for key, path in paths.items()}
    expected_hashes = {
        key: sources[key]["sha256"] for key in paths
    }
    external_hashes_after = {
        key: file_sha256(path) for key, path in external_paths.items()
    }
    if (
        source_hashes_before != expected_hashes
        or after_hashes != expected_hashes
        or source_hashes_before != after_hashes
        or external_hashes_before != external_hashes_after
    ):
        raise ValueError("Phase 558 overlay source changed during validation")
    return {
        "phase_from": policy.PHASE_FROM,
        "phase_to": policy.PHASE_TO,
        "review_identity": policy.review_identity(),
        "source_paths": {key: str(path) for key, path in paths.items()},
        "source_sha256": source_hashes_before,
        "external_authority_paths": {
            key: str(path) for key, path in external_paths.items()
        },
        "external_authority_sha256": external_hashes_before,
        "disposition_surfaces": len(ledger_surfaces),
        "phase558_delta_authority_surfaces": len(phase558_delta_authority),
        "selected_authority_surfaces": len(selected_authority),
        "keep_coarse_authority_surfaces": len(
            groups[KEEP_COARSE_LEDGER_GROUP]
        ),
        "learner_changed_rows": len(learner_delta),
        "academic_changed_rows": len(academic_delta),
        "changed_surfaces": len(changed_surfaces),
        "changed_surfaces_sha256": compact_sha256(changed_surfaces),
        "selected_entries": selected,
        "selected_entries_sha256": compact_sha256(selected),
        # The five-surface Ruby sidecar is independently adoptable, while the
        # broader moving-master candidate remains governed by its own ledger.
        "master_candidate_promotion_gate": ledger["promotion_gate"],
        "master_candidate_promotion_blockers": list(
            ledger["promotion_blockers"]
        ),
        "inputs_stable": True,
        "gate": True,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase532-dir", type=Path, required=True)
    parser.add_argument("--phase558-dir", type=Path, required=True)
    parser.add_argument("--disposition-ledger", type=Path, required=True)
    parser.add_argument("--japanese-guide", type=Path, required=True)
    parser.add_argument("--chinese-guide", type=Path, required=True)
    parser.add_argument("--check", action="store_true", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(
        validate_frozen_closure(
            args.phase532_dir, args.phase558_dir,
            args.disposition_ledger, args.japanese_guide,
            args.chinese_guide,
        ),
        ensure_ascii=False, indent=2,
    ))


if __name__ == "__main__":
    main()
