# -*- coding: utf-8 -*-
"""Recheck the frozen Phase 513 -> Phase 532 authority carry-forward.

The committed ledger is a reviewed decision and this command is deliberately
check-only.  It binds the separately retained Phase 513 raw evidence plus the
Phase 532 candidate manifest, finds all four
master files by their exact hashes, derives the five reviewed line scopes from
their original decision ledgers, and proves that every selected manifest entry
and learner/academic row is exactly unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import unicodedata

import phase532_authority_carry_forward as carry


HERE = Path(__file__).resolve().parent
PHASE513_MANIFEST_PATH = (
    HERE / "_phase513_fake_coarse_reference_manifest.json"
)
HAT_TO_CIRCUMFLEX = {
    "c^": "ĉ", "g^": "ĝ", "h^": "ĥ", "j^": "ĵ", "s^": "ŝ",
    "u^": "ŭ", "C^": "Ĉ", "G^": "Ĝ", "H^": "Ĥ", "J^": "Ĵ",
    "S^": "Ŝ", "U^": "Ŭ",
}


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def find_by_sha(directory: Path, expected_sha256: str) -> Path:
    directory = directory.resolve()
    if not directory.is_dir():
        raise ValueError(f"frozen source directory does not exist: {directory}")
    matches = [
        path.resolve() for path in directory.iterdir()
        if path.is_file() and sha256_file(path) == expected_sha256
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one {expected_sha256} file in {directory}, "
            f"found {matches!r}"
        )
    return matches[0]


def read_bound_json(path: Path, expected_sha256: str) -> tuple[bytes, dict]:
    raw = path.resolve().read_bytes()
    if sha256_bytes(raw) != expected_sha256:
        raise ValueError(f"JSON source identity changed: {path}")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON source is not an object: {path}")
    return raw, payload


def read_bound_master(path: Path, expected_sha256: str) -> list[str]:
    raw = path.resolve().read_bytes()
    if sha256_bytes(raw) != expected_sha256:
        raise ValueError(f"master source identity changed: {path}")
    lines = raw.decode("utf-8", errors="strict").splitlines()
    if len(lines) != carry.EXPECTED_MASTER_LINES:
        raise ValueError(f"master line count changed: {path}")
    return lines


def _decomposition(line: str) -> str:
    if ":" not in line:
        raise ValueError(f"master row has no definition separator: {line!r}")
    raw = line.lstrip("\ufeff").split(":", 1)[0].strip()
    for source, replacement in HAT_TO_CIRCUMFLEX.items():
        raw = raw.replace(source, replacement)
    raw = unicodedata.normalize("NFC", raw).replace("’", "'")
    # The source master permits a trailing slash for bare affix rows; the
    # fake/coarse manifest canonicalizes decomposition by dropping empty
    # pieces.  Reproduce only that structural normalization here.
    return "/".join(piece for piece in raw.split("/") if piece)


def _load_manifest(
    path: Path, *, expected_raw_sha256: str, expected_entries_sha256: str,
    expected_entries: int, learner_sha256: str, academic_sha256: str,
) -> tuple[dict, dict[int, dict]]:
    _raw, payload = read_bound_json(path, expected_raw_sha256)
    entries = payload.get("entries")
    if (
        payload.get("schema_version") != 1
        or not isinstance(entries, list)
        or len(entries) != expected_entries
        or payload.get("entries_sha256") != expected_entries_sha256
        or carry.compact_sha256(entries) != expected_entries_sha256
        or payload.get("sources", {}).get("learner", {}).get("sha256")
        != learner_sha256
        or payload.get("sources", {}).get("academic", {}).get("sha256")
        != academic_sha256
        or payload.get("sources", {}).get("pejvo_original", {}).get("sha256")
        != carry.PEJVO_SHA256
    ):
        raise ValueError(f"fake/coarse manifest semantic identity drift: {path}")
    by_line = {entry.get("learner_line"): entry for entry in entries}
    if (
        len(by_line) != len(entries)
        or None in by_line
        or any(not isinstance(line, int) or line < 1 for line in by_line)
    ):
        raise ValueError(f"fake/coarse manifest line identity drift: {path}")
    return payload, by_line


def _decision_lines(name: str, payload: dict) -> list[int]:
    if name == "app_review":
        entries = payload.get("entries", [])
        lines = [
            line for entry in entries for line in entry.get("learner_lines", [])
        ]
    elif name == "atomic_families":
        families = payload.get("families", [])
        lines = [
            authority["learner_line"]
            for family in families
            for authority in family.get("authority", [])
        ]
    else:
        entries = payload.get("entries", [])
        lines = [entry.get("learner_line") for entry in entries]
    if (
        any(not isinstance(line, int) or line < 1 for line in lines)
        or len(lines) != len(set(lines))
    ):
        raise ValueError(f"invalid or duplicate decision lines: {name}")
    return sorted(lines)


def load_decision_line_scopes() -> dict[str, list[int]]:
    """Re-derive the five exact scopes from their original reviewed files."""
    scopes = {}
    for name, spec in carry.DECISION_SOURCE_SPECS.items():
        path = HERE / spec["path"]
        _raw, payload = read_bound_json(path, spec["sha256"])
        semantic = payload.get(spec["semantic_key"])
        semantic_field = f"{spec['semantic_key']}_sha256"
        if (
            not isinstance(semantic, list)
            or len(semantic) != spec["decision_records"]
            or payload.get(semantic_field) != spec["semantic_sha256"]
            or carry.compact_sha256(semantic) != spec["semantic_sha256"]
        ):
            raise ValueError(f"decision source semantic drift: {name}")
        lines = _decision_lines(name, payload)
        if (
            len(lines) != spec["learner_lines"]
            or lines
            != carry.EXPECTED_AUTHORITY_GROUPS[name]["learner_lines"]
        ):
            raise ValueError(f"decision source line scope drift: {name}")
        scopes[name] = lines
    if set(scopes) != set(carry.EXPECTED_AUTHORITY_GROUPS):
        raise ValueError("decision source group closure drift")
    return scopes


def verify_carry_forward_groups(
    *, scopes: dict[str, list[int]], phase513_by_line: dict[int, dict],
    phase532_by_line: dict[int, dict], masters: dict[str, list[str]],
) -> dict[str, dict]:
    """Prove and fingerprint exact old-to-new equality for all five scopes."""
    line_sets = [set(lines) for lines in scopes.values()]
    if any(
        left & right
        for index, left in enumerate(line_sets)
        for right in line_sets[index + 1:]
    ):
        raise ValueError("derived carry-forward scopes overlap")
    union = sorted(set().union(*line_sets))
    if (
        len(union) != carry.EXPECTED_COUNTS["reviewed_learner_lines"]
        or carry.compact_sha256(union) != carry.REVIEWED_LINE_UNION_SHA256
    ):
        raise ValueError("derived carry-forward union drift")

    computed = {}
    for name, lines in scopes.items():
        try:
            old_entries = [phase513_by_line[line] for line in lines]
            new_entries = [phase532_by_line[line] for line in lines]
            old_learner = [masters["phase513_learner"][line - 1] for line in lines]
            new_learner = [masters["phase532_learner"][line - 1] for line in lines]
            old_academic = [
                masters["phase513_academic"][line - 1] for line in lines
            ]
            new_academic = [
                masters["phase532_academic"][line - 1] for line in lines
            ]
        except (KeyError, IndexError) as error:
            raise ValueError(f"carry-forward source row missing: {name}") from error
        if old_entries != new_entries:
            raise ValueError(f"fake/coarse authority changed: {name}")
        if old_learner != new_learner:
            raise ValueError(f"learner authority rows changed: {name}")
        if old_academic != new_academic:
            raise ValueError(f"academic authority rows changed: {name}")

        for line, entry, learner_row, academic_row in zip(
            lines, new_entries, new_learner, new_academic,
        ):
            if (
                entry.get("learner_line") != line
                or entry.get("learner_decomposition")
                != _decomposition(learner_row)
                or entry.get("academic_decomposition")
                != _decomposition(academic_row)
                or "##偽分解" not in learner_row
                or "##偽分解" in academic_row
            ):
                raise ValueError(
                    f"manifest/master authority correspondence drift: "
                    f"{name} line {line}"
                )

        computed[name] = {
            "learner_lines": lines,
            "learner_lines_sha256": carry.compact_sha256(lines),
            "phase513_fake_entries_sha256": carry.compact_sha256(old_entries),
            "phase532_fake_entries_sha256": carry.compact_sha256(new_entries),
            "phase513_learner_lines_sha256": carry.compact_sha256(old_learner),
            "phase532_learner_lines_sha256": carry.compact_sha256(new_learner),
            "phase513_academic_lines_sha256": carry.compact_sha256(old_academic),
            "phase532_academic_lines_sha256": carry.compact_sha256(new_academic),
        }
    if computed != carry.EXPECTED_AUTHORITY_GROUPS:
        raise ValueError("carry-forward aggregate fingerprints drifted")
    return computed


def validate_frozen_closure(
    baseline_dir: Path, candidate_dir: Path, candidate_manifest_path: Path,
) -> dict:
    """Validate all frozen inputs and return the carry-forward gate report."""
    baseline_dir = Path(baseline_dir)
    candidate_dir = Path(candidate_dir)
    candidate_manifest_path = Path(candidate_manifest_path)
    baseline_dir = baseline_dir.resolve()
    candidate_dir = candidate_dir.resolve()
    candidate_manifest_path = candidate_manifest_path.resolve()
    master_paths = {
        "phase513_learner": find_by_sha(
            baseline_dir, carry.PHASE513_LEARNER_SHA256,
        ),
        "phase513_academic": find_by_sha(
            baseline_dir, carry.PHASE513_ACADEMIC_SHA256,
        ),
        "phase532_learner": find_by_sha(
            candidate_dir, carry.PHASE532_LEARNER_SHA256,
        ),
        "phase532_academic": find_by_sha(
            candidate_dir, carry.PHASE532_ACADEMIC_SHA256,
        ),
    }
    input_paths = [
        PHASE513_MANIFEST_PATH.resolve(), candidate_manifest_path,
        carry.LEDGER_PATH.resolve(), Path(carry.__file__).resolve(),
        Path(__file__).resolve(), *master_paths.values(),
        *(HERE / spec["path"] for spec in carry.DECISION_SOURCE_SPECS.values()),
    ]
    if len(input_paths) != len(set(input_paths)):
        raise ValueError("carry-forward input path alias detected")
    start_hashes = {path: sha256_file(path) for path in input_paths}

    ledger = carry.load_phase532_authority_carry_forward()
    _old_payload, old_by_line = _load_manifest(
        PHASE513_MANIFEST_PATH,
        expected_raw_sha256=carry.PHASE513_FAKE_MANIFEST_SHA256,
        expected_entries_sha256=carry.PHASE513_FAKE_ENTRIES_SHA256,
        expected_entries=3213,
        learner_sha256=carry.PHASE513_LEARNER_SHA256,
        academic_sha256=carry.PHASE513_ACADEMIC_SHA256,
    )
    _new_payload, new_by_line = _load_manifest(
        candidate_manifest_path,
        expected_raw_sha256=carry.PHASE532_FAKE_MANIFEST_SHA256,
        expected_entries_sha256=carry.PHASE532_FAKE_ENTRIES_SHA256,
        expected_entries=3238,
        learner_sha256=carry.PHASE532_LEARNER_SHA256,
        academic_sha256=carry.PHASE532_ACADEMIC_SHA256,
    )
    masters = {
        name: read_bound_master(path, carry.EXPECTED_SOURCES[name]["sha256"])
        for name, path in master_paths.items()
    }
    scopes = load_decision_line_scopes()
    computed = verify_carry_forward_groups(
        scopes=scopes, phase513_by_line=old_by_line,
        phase532_by_line=new_by_line, masters=masters,
    )
    if computed != ledger["authorities"]:
        raise ValueError("reviewed carry-forward ledger does not match closure")

    end_hashes = {path: sha256_file(path) for path in input_paths}
    if start_hashes != end_hashes:
        raise ValueError("carry-forward audit input changed during validation")
    return {
        "phase_from": carry.PHASE_FROM,
        "phase_to": carry.PHASE_TO,
        "authority_groups": len(computed),
        "reviewed_learner_lines": len(set().union(*(
            set(group["learner_lines"]) for group in computed.values()
        ))),
        "group_line_counts": {
            name: len(group["learner_lines"])
            for name, group in computed.items()
        },
        "phase511_entries_carried": 21,
        "ff33_entries_carried": 1,
        "5e_entries_carried": 1,
        "app_review_entries_carried": 85,
        "app_review_lines_carried": 86,
        "atomic_families_carried": 2,
        "atomic_authority_lines_carried": 4,
        "phase513_to_phase532_manifest_entries_identical": True,
        "phase513_to_phase532_learner_rows_identical": True,
        "phase513_to_phase532_academic_rows_identical": True,
        "review_identity": carry.review_identity(),
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
