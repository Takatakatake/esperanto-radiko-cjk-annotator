# -*- coding: utf-8 -*-
"""Pin and structurally audit the external learner gold reference.

This script is read-only.  It also reports the scale of the delta against an
older available copy without treating that older copy as authoritative.
"""
from __future__ import annotations

import argparse
import collections
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from extract_lib import hat_to_circumflex, replace_esperanto_chars
from gold_snapshot import consistent_snapshot


ESP_LETTERS = "a-zĉĝĥĵŝŭ"
WORD_RE = re.compile(rf"(?=.*[{ESP_LETTERS}])[{ESP_LETTERS}'-]+", re.IGNORECASE)
FAKE_MARKER_RE = re.compile(r"##偽分解(?:\([^)]*\))?")


def norm(value):
    return (
        replace_esperanto_chars(value, hat_to_circumflex)
        .lower().replace("’", "'").strip()
    )


def selected_record(line, line_number):
    if ":" not in line:
        return None
    decomposition, gloss = line.split(":", 1)
    decomposition = decomposition.strip()
    if (
        not decomposition or " " in decomposition
        or decomposition.startswith("-") or decomposition.endswith("-")
    ):
        return None
    surface = norm("".join(piece for piece in decomposition.split("/") if piece))
    if not WORD_RE.fullmatch(surface):
        return None
    return surface, {
        "decomposition": "/".join(
            norm(piece) for piece in decomposition.split("/") if norm(piece)
        ),
        "marker": FAKE_MARKER_RE.search(gloss).group(0)
        if FAKE_MARKER_RE.search(gloss) else None,
        "line": line_number,
        "line_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest().upper(),
    }


def inspect(path, snapshot=None):
    path = Path(path)
    if snapshot is None:
        raw, snapshot_identity = consistent_snapshot(path)
    else:
        raw, snapshot_identity = snapshot
    text = raw.decode("utf-8", errors="strict")
    lines = text.splitlines()
    raw_heads = collections.Counter()
    selected = {}
    selected_duplicate_rows = 0
    marker_rows = 0
    marker_in_head = 0
    blank_decomposition_pieces = 0
    for line_number, line in enumerate(lines, 1):
        if ":" in line:
            head, gloss = line.split(":", 1)
            raw_heads[head.strip()] += 1
            marker_rows += "##偽分解" in gloss
            marker_in_head += "##偽分解" in head
            blank_decomposition_pieces += "//" in head
        record = selected_record(line, line_number)
        if record is None:
            continue
        surface, value = record
        if surface in selected:
            selected_duplicate_rows += 1
        else:
            selected[surface] = value
    metadata = {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "bytes": len(raw),
        "mtime": datetime.fromtimestamp(
            snapshot_identity["mtime_ns"] / 1_000_000_000
        ).astimezone().isoformat(),
        "mtime_ns": snapshot_identity["mtime_ns"],
        "lines": len(lines),
        "terminal_lf": raw.endswith(b"\n"),
        "cr_bytes": raw.count(b"\r"),
        "nul_bytes": raw.count(b"\x00"),
        "replacement_chars": text.count("\ufffd"),
        "empty_lines": sum(not line for line in lines),
        "colon_rows": sum(":" in line for line in lines),
        "fake_marker_rows": marker_rows,
        "fake_marker_in_head_rows": marker_in_head,
        "blank_decomposition_piece_rows": blank_decomposition_pieces,
        "unique_raw_heads": len(raw_heads),
        "duplicate_raw_heads": sum(count > 1 for count in raw_heads.values()),
        "duplicate_raw_head_rows": sum(count - 1 for count in raw_heads.values()),
        "selected_surfaces": len(selected),
        "selected_duplicate_rows": selected_duplicate_rows,
        "max_line_chars": max(map(len, lines), default=0),
    }
    metadata["structural_gate"] = all((
        metadata["terminal_lf"],
        metadata["cr_bytes"] == 0,
        metadata["nul_bytes"] == 0,
        metadata["replacement_chars"] == 0,
        metadata["empty_lines"] == 0,
        metadata["colon_rows"] == metadata["lines"],
        metadata["fake_marker_in_head_rows"] == 0,
        metadata["blank_decomposition_piece_rows"] == 0,
    ))
    return raw, lines, selected, metadata


def line_fingerprint(line):
    return {
        "head": line.split(":", 1)[0],
        "sha256": hashlib.sha256(line.encode("utf-8")).hexdigest().upper(),
    }


def compare(current_lines, current_selected, baseline_lines, baseline_selected):
    current_counter = collections.Counter(current_lines)
    baseline_counter = collections.Counter(baseline_lines)
    added_lines = list((current_counter - baseline_counter).elements())
    removed_lines = list((baseline_counter - current_counter).elements())
    current_surfaces = set(current_selected)
    baseline_surfaces = set(baseline_selected)
    common = current_surfaces & baseline_surfaces
    decomposition_changes = []
    marker_changes = []
    gloss_or_metadata_changes = 0
    for surface in sorted(common):
        current = current_selected[surface]
        baseline = baseline_selected[surface]
        if current["decomposition"] != baseline["decomposition"]:
            decomposition_changes.append({
                "surface": surface,
                "baseline": baseline["decomposition"],
                "current": current["decomposition"],
            })
        if current["marker"] != baseline["marker"]:
            marker_changes.append({
                "surface": surface,
                "baseline": baseline["marker"],
                "current": current["marker"],
            })
        if current["line_sha256"] != baseline["line_sha256"]:
            gloss_or_metadata_changes += 1
    return {
        "added_line_instances": len(added_lines),
        "removed_line_instances": len(removed_lines),
        "added_line_samples": [line_fingerprint(line) for line in added_lines[:30]],
        "removed_line_samples": [line_fingerprint(line) for line in removed_lines[:30]],
        "added_selected_surfaces": len(current_surfaces - baseline_surfaces),
        "removed_selected_surfaces": len(baseline_surfaces - current_surfaces),
        "common_selected_surfaces": len(common),
        "selected_line_changes": gloss_or_metadata_changes,
        "selected_decomposition_changes": decomposition_changes,
        "selected_marker_changes": marker_changes,
    }


def default_current():
    return (
        ROOT.parent / "エスペラント辞書徹底語根分解_20260630"
        / "世界语全部单词_大约44100个(原pejvo.txt)_学習者版_utf8_20260416.txt"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path, default=default_current())
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-bytes", type=int, required=True)
    parser.add_argument("--expected-lines", type=int, required=True)
    parser.add_argument("--expected-fake-marker-rows", type=int, required=True)
    args = parser.parse_args()

    _raw, current_lines, current_selected, current = inspect(args.current)
    _old_raw, baseline_lines, baseline_selected, baseline = inspect(args.baseline)
    expected = {
        "sha256": args.expected_sha256.upper(),
        "bytes": args.expected_bytes,
        "lines": args.expected_lines,
        "fake_marker_rows": args.expected_fake_marker_rows,
    }
    pinned_gate = all(current[key] == value for key, value in expected.items())
    result = {
        "scope": "read_only_external_gold_health_and_nearest_copy_delta",
        "expected_current": expected,
        "current": current,
        "baseline": baseline,
        "comparison": compare(
            current_lines, current_selected, baseline_lines, baseline_selected
        ),
        "gate": pinned_gate and current["structural_gate"] and baseline["structural_gate"],
    }
    output = HERE / "out" / "_audit_gold_health.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({
        "current": current,
        "baseline": baseline,
        "comparison_counts": {
            key: value for key, value in result["comparison"].items()
            if not isinstance(value, list)
        },
        "decomposition_changes": len(
            result["comparison"]["selected_decomposition_changes"]
        ),
        "marker_changes": len(result["comparison"]["selected_marker_changes"]),
        "gate": result["gate"],
    }, ensure_ascii=False, indent=1))
    if not result["gate"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
