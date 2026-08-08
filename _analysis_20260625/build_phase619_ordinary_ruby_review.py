# -*- coding: utf-8 -*-
"""Revalidate the frozen Phase 597 -> 619 evidence for seven Ruby repairs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import phase619_ordinary_ruby_policy as policy


SOURCE_DIRECTORY = {
    "phase597_learner": "phase597",
    "phase597_academic": "phase597",
    "phase597_fake_coarse_manifest": "phase597",
    "phase619_learner": "phase619",
    "phase619_academic": "phase619",
    "phase619_pejvo_original": "phase619",
    "phase619_fake_coarse_manifest": "phase619",
    "phase619_transition_dispositions": "phase619",
}
LINE_SOURCES = {
    "phase597_learner": "phase597_learner_line",
    "phase597_academic": "phase597_academic_line",
    "phase619_learner": "phase619_learner_line",
    "phase619_academic": "phase619_academic_line",
}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def find_bound_file(directory: Path, expected: dict) -> Path:
    directory = directory.resolve()
    matches = [
        path.resolve()
        for path in directory.iterdir()
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


def read_bound_lines(path: Path, expected: dict) -> list[str]:
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


def validate_frozen_closure(
    phase597_dir: Path,
    phase619_dir: Path,
    japanese_guide: Path,
    chinese_guide: Path,
) -> dict:
    review = policy.load_review()
    directories = {
        "phase597": Path(phase597_dir).resolve(),
        "phase619": Path(phase619_dir).resolve(),
    }
    paths = {}
    for source_name, directory_name in SOURCE_DIRECTORY.items():
        paths[source_name] = find_bound_file(
            directories[directory_name],
            policy.EXPECTED_SOURCES[source_name],
        )
    paths.update({
        "japanese_guide": Path(japanese_guide).resolve(),
        "chinese_guide": Path(chinese_guide).resolve(),
    })

    hashes_before = {}
    line_tables = {}
    for source_name, path in paths.items():
        expected = policy.EXPECTED_SOURCES[source_name]
        raw = path.read_bytes()
        identity = {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest().upper(),
        }
        if "lines" in expected:
            lines = raw.decode("utf-8", errors="strict").splitlines()
            identity["lines"] = len(lines)
            line_tables[source_name] = lines
        if identity != expected:
            raise ValueError(
                f"Phase 619 bound source identity drift: "
                f"{source_name}: {identity!r}"
            )
        hashes_before[source_name] = identity["sha256"]

    selected = []
    for entry in review["entries"]:
        index = entry["learner_line"] - 1
        evidence = {}
        for source_name, field_name in LINE_SOURCES.items():
            lines = line_tables[source_name]
            if not 0 <= index < len(lines):
                raise ValueError(
                    f"Phase 619 line is outside source: "
                    f"{entry['surface']!r}/{source_name}"
                )
            evidence[field_name] = lines[index]
        if any(
            entry[field_name] != value
            for field_name, value in evidence.items()
        ):
            raise ValueError(
                f"Phase 619 reviewed source row changed: "
                f"{entry['surface']!r}"
            )
        if any(
            policy.phase532.surface_from_decomposition(
                line.split(":", 1)[0]
            ) != policy.phase532.canonical(entry["surface"])
            for line in evidence.values()
        ):
            raise ValueError(
                f"Phase 619 reviewed source surface drift: "
                f"{entry['surface']!r}"
            )
        selected.append({
            "line": entry["learner_line"],
            "surface": entry["surface"],
            "selected_ruby_target": entry["selected_ruby_target"],
            "kind": entry["setting"]["kind"],
        })

    hashes_after = {
        source_name: file_sha256(path)
        for source_name, path in paths.items()
    }
    if hashes_after != hashes_before:
        raise ValueError("Phase 619 evidence changed during validation")
    return {
        "phase_from": policy.PHASE_FROM,
        "phase_to": policy.PHASE_TO,
        "review_identity": policy.review_identity(),
        "source_paths": {
            source_name: str(path)
            for source_name, path in paths.items()
        },
        "source_sha256": hashes_before,
        "selected_entries": selected,
        "selected_entries_sha256": policy.compact_sha256(selected),
        "ordinary_entries": len(selected),
        "proper_name_changes": 0,
        "inputs_stable": True,
        "gate": True,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase597-dir", type=Path, required=True)
    parser.add_argument("--phase619-dir", type=Path, required=True)
    parser.add_argument("--japanese-guide", type=Path, required=True)
    parser.add_argument("--chinese-guide", type=Path, required=True)
    parser.add_argument("--check", action="store_true", required=True)
    args = parser.parse_args(argv)
    report = validate_frozen_closure(
        args.phase597_dir,
        args.phase619_dir,
        args.japanese_guide,
        args.chinese_guide,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
