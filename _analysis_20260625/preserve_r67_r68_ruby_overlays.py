#!/usr/bin/env python3
"""Carry the reviewed R67/R68 Ruby protection layers across regeneration.

``apply_confirmed_now.py --write`` rebuilds the three large Ruby payloads from
the pinned master inputs.  The R67/R68 protections were historically added as
post-generation sidecars, so a plain rebuild drops them.  Re-running the old
R68 discovery script is not an acceptable recovery mechanism: it scans a
moving absolute master and can widen its scope.

This module instead seals the already-deployed, reviewed rows before a rebuild
and restores exactly that closed set afterwards.  The row identities, order,
and localized renderings are pinned to the R72 parent.  Any collision or drift
fails before the three deployed payloads are replaced.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from atomic_json import atomic_file_copy, atomic_json_dump


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("JA", "ZH", "KO")
RUBY_PAYLOAD_NAME = (
    "\u7f6e\u63db\u30ea\u30b9\u30c8_\u30eb\u30d3.json"
)
GLOBAL_BUCKET_TOKEN = "replacements_final_list"
OVERLAY_PREFIXES = ("R67H", "R68W")
SCHEMA_VERSION = 1

PINNED_PARENT_COMMIT = "4682D32496F166802B4A2CF28626F376E12AAE3E"
PINNED_PARENT_TREE = "2C494DB69EBAC28EF63A192BEFA017A22710CCD7"
PINNED_PARENT_GLOBAL_ROWS = 572_356
EXPECTED_POST_R73_GLOBAL_ROWS = 572_501

EXPECTED_OVERLAYS = {
    "JA": {
        "R67H": {
            "count": 336,
            "rows_sha256": (
                "EFF64DE3C95FEC66209CA72E1EFE5A8E0EB0C438A89AEA4C200A6C41130F340A"
            ),
            "sources_sha256": (
                "0408F60AA78FB00B2A43FAE3A6FDA93E68C1786C660DA6094A0A6E27FCFB919B"
            ),
        },
        "R68W": {
            "count": 1_013,
            "rows_sha256": (
                "BE04F81592359C8DB5B51D45721440D2025BCC61D5C163821EEECC90A70CFF2D"
            ),
            "sources_sha256": (
                "9DD2837E37A927105E626897ACD99E23A40FE22826015B6A0E05CF6DC2833B3B"
            ),
        },
    },
    "ZH": {
        "R67H": {
            "count": 336,
            "rows_sha256": (
                "2BE0D3D80BFCFF668D771DB4891A9F8A0E52BBBB4C5F10A7B364A3DA6625D609"
            ),
            "sources_sha256": (
                "0408F60AA78FB00B2A43FAE3A6FDA93E68C1786C660DA6094A0A6E27FCFB919B"
            ),
        },
        "R68W": {
            "count": 1_013,
            "rows_sha256": (
                "74A9D3F5A4F6BCC879E57C67044F42A6A09FAAACDFD90580878B7752910649FD"
            ),
            "sources_sha256": (
                "9DD2837E37A927105E626897ACD99E23A40FE22826015B6A0E05CF6DC2833B3B"
            ),
        },
    },
    "KO": {
        "R67H": {
            "count": 336,
            "rows_sha256": (
                "3341E8260981925082A3E4D156B64FA2C21A7B7FB6FED8FB97973B941C73B056"
            ),
            "sources_sha256": (
                "0408F60AA78FB00B2A43FAE3A6FDA93E68C1786C660DA6094A0A6E27FCFB919B"
            ),
        },
        "R68W": {
            "count": 1_013,
            "rows_sha256": (
                "663C2D073A563C5B17527E8FFC13829FBEE0125C211C194BACC9C2136AC817BE"
            ),
            "sources_sha256": (
                "9DD2837E37A927105E626897ACD99E23A40FE22826015B6A0E05CF6DC2833B3B"
            ),
        },
    },
}

EXACT_OVERRIDE_SOURCE = " Auster "
EXACT_OVERRIDE_RENDERED = {
    "JA": " Auster ",
    "ZH": " Auster ",
    "KO": " Auster ",
}


def compact_sha256(value) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def payload_path(language: str) -> Path:
    return (
        ROOT
        / f"Esperanto-Kanji-Ruby-{language}"
        / "app_data"
        / RUBY_PAYLOAD_NAME
    )


def load_payload(language: str, git_ref: str | None = None) -> dict:
    path = payload_path(language)
    if git_ref is None:
        return json.loads(path.read_text(encoding="utf-8"))
    relative = path.relative_to(ROOT).as_posix()
    raw = subprocess.check_output(
        ["git", "show", f"{git_ref}:{relative}"],
        cwd=ROOT,
    )
    return json.loads(raw.decode("utf-8"))


def global_bucket(payload: dict) -> tuple[str, list]:
    matches = [
        key
        for key, rows in payload.items()
        if GLOBAL_BUCKET_TOKEN in key and isinstance(rows, list)
    ]
    if len(matches) != 1:
        raise ValueError(f"global Ruby bucket drift: {matches!r}")
    return matches[0], payload[matches[0]]


def overlay_rows(rows: list, prefix: str) -> list:
    return [
        row
        for row in rows
        if (
            isinstance(row, list)
            and len(row) >= 3
            and isinstance(row[2], str)
            and f"${prefix}" in row[2]
        )
    ]


def validate_rows(language: str, prefix: str, rows: list) -> dict:
    expected = EXPECTED_OVERLAYS[language][prefix]
    if any(
        not isinstance(row, list)
        or len(row) != 3
        or not all(isinstance(value, str) for value in row)
        for row in rows
    ):
        raise ValueError(f"{language}/{prefix}: malformed overlay row")
    sources = [row[0] for row in rows]
    placeholders = [row[2] for row in rows]
    actual = {
        "count": len(rows),
        "rows_sha256": compact_sha256(rows),
        "sources_sha256": compact_sha256(sources),
    }
    if actual != expected:
        raise ValueError(
            f"{language}/{prefix}: reviewed overlay drift: "
            f"{actual!r} != {expected!r}"
        )
    if len(sources) != len(set(sources)):
        raise ValueError(f"{language}/{prefix}: duplicate source key")
    if len(placeholders) != len(set(placeholders)):
        raise ValueError(f"{language}/{prefix}: duplicate placeholder")
    return actual


def validate_overlay_matrix(matrix: dict) -> dict:
    if set(matrix) != set(LANGUAGES):
        raise ValueError("overlay snapshot must contain exactly JA/ZH/KO")
    report = {}
    for language in LANGUAGES:
        if set(matrix[language]) != set(OVERLAY_PREFIXES):
            raise ValueError(
                f"{language}: overlay prefixes are not closed"
            )
        report[language] = {}
        for prefix in OVERLAY_PREFIXES:
            report[language][prefix] = validate_rows(
                language,
                prefix,
                matrix[language][prefix],
            )
    for prefix in OVERLAY_PREFIXES:
        source_lists = {
            tuple(row[0] for row in matrix[language][prefix])
            for language in LANGUAGES
        }
        if len(source_lists) != 1:
            raise ValueError(
                f"{prefix}: JA/ZH/KO source order mismatch"
            )
    for language in LANGUAGES:
        left = {
            row[0] for row in matrix[language]["R67H"]
        }
        right = {
            row[0] for row in matrix[language]["R68W"]
        }
        overlap = left & right
        if overlap:
            raise ValueError(
                f"{language}: R67/R68 source collision: "
                f"{sorted(overlap)[:5]!r}"
            )
    return report


def resolve_git_identity(git_ref: str) -> dict:
    commit = subprocess.check_output(
        ["git", "rev-parse", f"{git_ref}^{{commit}}"],
        cwd=ROOT,
        text=True,
    ).strip().upper()
    tree = subprocess.check_output(
        ["git", "rev-parse", f"{git_ref}^{{tree}}"],
        cwd=ROOT,
        text=True,
    ).strip().upper()
    return {"commit": commit, "tree": tree}


def capture_snapshot(output: Path, git_ref: str | None = None) -> dict:
    if git_ref is not None:
        identity = resolve_git_identity(git_ref)
        expected = {
            "commit": PINNED_PARENT_COMMIT,
            "tree": PINNED_PARENT_TREE,
        }
        if identity != expected:
            raise ValueError(
                f"recovery parent identity drift: {identity!r} != {expected!r}"
            )
    else:
        identity = {
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                text=True,
            ).strip().upper(),
            "tree": subprocess.check_output(
                ["git", "rev-parse", "HEAD^{tree}"],
                cwd=ROOT,
                text=True,
            ).strip().upper(),
        }

    matrix = {}
    exact_overrides = {}
    deployed_counts = {}
    for language in LANGUAGES:
        payload = load_payload(language, git_ref)
        _key, rows = global_bucket(payload)
        matrix[language] = {
            prefix: overlay_rows(rows, prefix)
            for prefix in OVERLAY_PREFIXES
        }
        exact_rows = [
            row for row in rows
            if (
                isinstance(row, list)
                and len(row) >= 2
                and row[0] == EXACT_OVERRIDE_SOURCE
            )
        ]
        if len(exact_rows) != 1:
            raise ValueError(
                f"{language}: exact override source multiplicity drift"
            )
        if exact_rows[0][1] != EXACT_OVERRIDE_RENDERED[language]:
            raise ValueError(
                f"{language}: exact override rendering drift: "
                f"{exact_rows[0][1]!r}"
            )
        exact_overrides[language] = {
            "source": EXACT_OVERRIDE_SOURCE,
            "rendered": exact_rows[0][1],
        }
        deployed_counts[language] = len(rows)

    overlay_report = validate_overlay_matrix(matrix)
    if git_ref is not None and any(
        count != PINNED_PARENT_GLOBAL_ROWS
        for count in deployed_counts.values()
    ):
        raise ValueError(
            f"pinned parent global row count drift: {deployed_counts!r}"
        )

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "authority": "reviewed-r67-r68-deployed-carry-forward",
        "source_identity": identity,
        "source_git_ref": git_ref,
        "global_rows_at_capture": deployed_counts,
        "overlay_report": overlay_report,
        "overlays": matrix,
        "exact_overrides": exact_overrides,
    }
    snapshot["snapshot_sha256"] = compact_sha256(snapshot)
    atomic_json_dump(output, snapshot, indent=2)
    return snapshot


def load_snapshot(path: Path) -> dict:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported historical overlay snapshot schema")
    if (
        snapshot.get("authority")
        != "reviewed-r67-r68-deployed-carry-forward"
    ):
        raise ValueError("historical overlay authority drift")
    recorded = snapshot.get("snapshot_sha256")
    unsigned = dict(snapshot)
    unsigned.pop("snapshot_sha256", None)
    actual = compact_sha256(unsigned)
    if recorded != actual:
        raise ValueError(
            f"historical overlay snapshot digest drift: "
            f"{actual} != {recorded}"
        )
    overlay_report = validate_overlay_matrix(snapshot.get("overlays"))
    if snapshot.get("overlay_report") != overlay_report:
        raise ValueError("historical overlay report drift")
    captured_counts = snapshot.get("global_rows_at_capture")
    if (
        set(captured_counts or {}) != set(LANGUAGES)
        or len(set(captured_counts.values())) != 1
        or not set(captured_counts.values())
        <= {PINNED_PARENT_GLOBAL_ROWS, EXPECTED_POST_R73_GLOBAL_ROWS}
    ):
        raise ValueError("historical overlay capture-count drift")
    if snapshot.get("source_git_ref") is not None:
        if snapshot.get("source_identity") != {
            "commit": PINNED_PARENT_COMMIT,
            "tree": PINNED_PARENT_TREE,
        }:
            raise ValueError("recovery snapshot parent identity drift")
    exact_overrides = snapshot.get("exact_overrides")
    if set(exact_overrides or {}) != set(LANGUAGES):
        raise ValueError("exact override language closure drift")
    for language in LANGUAGES:
        if exact_overrides[language] != {
            "source": EXACT_OVERRIDE_SOURCE,
            "rendered": EXACT_OVERRIDE_RENDERED[language],
        }:
            raise ValueError(
                f"{language}: exact override snapshot drift"
            )
    return snapshot


# This is the reviewed R68 insertion algorithm.  It reproduces the parent
# ordering exactly when R67 is prepended first (verified for all three
# 572,356-row parent payloads).
_BOL = chr(1)
_HAT12 = "".join(
    chr(code)
    for code in (264, 265, 284, 285, 292, 293, 308, 309, 348, 349, 364, 365)
)
_LATEXT = (
    chr(192) + "-" + chr(214)
    + chr(216) + "-" + chr(246)
    + chr(248) + "-" + chr(591)
)
_APOS = chr(39) + chr(8217)
_KEEP = (
    "A-Za-z0-9"
    + _HAT12
    + _LATEXT
    + chr(37)
    + chr(64)
    + _APOS
    + " "
    + chr(10)
    + chr(13)
    + chr(1)
)
_PAD = re.compile("([^" + _KEEP + "])")
_LTR = "A-Za-z" + _HAT12 + _LATEXT
_APOS_R = re.compile("[" + _APOS + "](?=[" + _LTR + "])")


def padkey(source: str) -> str:
    padded = _PAD.sub(
        lambda match: " " + _BOL + match.group(1) + _BOL + " ",
        source,
    )
    return _APOS_R.sub(
        lambda match: match.group(0) + _BOL + " ",
        padded,
    )


def splice_r68(base_rows: list, r68_rows: list) -> list:
    candidates = [
        (index, padkey(row[0]))
        for index, row in enumerate(base_rows)
        if (
            isinstance(row, list)
            and row
            and isinstance(row[0], str)
            and (
                " " in row[0].strip()
                or _PAD.search(row[0])
            )
        )
    ]
    groups = {}
    for row in r68_rows:
        key = padkey(row[0])
        position = 0
        for index, candidate in candidates:
            if len(candidate) > len(key) and key in candidate:
                position = max(position, index + 1)
        groups.setdefault(position, []).append(row)
    result = list(base_rows)
    for position in sorted(groups, reverse=True):
        result[position:position] = groups[position]
    return result


def restore_bucket(language: str, rows: list, snapshot: dict) -> list:
    clean = [
        row
        for row in rows
        if not (
            isinstance(row, list)
            and len(row) >= 3
            and isinstance(row[2], str)
            and any(
                f"${prefix}" in row[2]
                for prefix in OVERLAY_PREFIXES
            )
        )
    ]
    base_sources = Counter(
        row[0]
        for row in clean
        if isinstance(row, list) and row and isinstance(row[0], str)
    )
    if any(count != 1 for count in base_sources.values()):
        duplicates = sorted(
            source
            for source, count in base_sources.items()
            if count != 1
        )
        raise ValueError(
            f"{language}: duplicate base source keys: {duplicates[:5]!r}"
        )

    r67 = snapshot["overlays"][language]["R67H"]
    r68 = snapshot["overlays"][language]["R68W"]
    overlay_sources = {row[0] for row in r67 + r68}
    collisions = overlay_sources & set(base_sources)
    if collisions:
        raise ValueError(
            f"{language}: reviewed overlay/base collision: "
            f"{sorted(collisions)[:5]!r}"
        )

    exact_indexes = [
        index
        for index, row in enumerate(clean)
        if (
            isinstance(row, list)
            and len(row) >= 2
            and row[0] == EXACT_OVERRIDE_SOURCE
        )
    ]
    if len(exact_indexes) != 1:
        raise ValueError(
            f"{language}: exact override target multiplicity drift"
        )
    exact_index = exact_indexes[0]
    exact_row = list(clean[exact_index])
    exact_row[1] = EXACT_OVERRIDE_RENDERED[language]
    clean[exact_index] = exact_row

    restored = splice_r68(r67 + clean, r68)
    restored_sources = [
        row[0]
        for row in restored
        if isinstance(row, list) and row and isinstance(row[0], str)
    ]
    duplicates = [
        source
        for source, count in Counter(restored_sources).items()
        if count != 1
    ]
    if duplicates:
        raise ValueError(
            f"{language}: duplicate restored source keys: "
            f"{sorted(duplicates)[:5]!r}"
        )
    return restored


def audit_payloads(payloads: dict, expected_global_rows: int | None) -> dict:
    matrix = {}
    counts = {}
    exact_values = {}
    for language in LANGUAGES:
        _key, rows = global_bucket(payloads[language])
        matrix[language] = {
            prefix: overlay_rows(rows, prefix)
            for prefix in OVERLAY_PREFIXES
        }
        counts[language] = len(rows)
        exact_rows = [
            row
            for row in rows
            if (
                isinstance(row, list)
                and len(row) >= 2
                and row[0] == EXACT_OVERRIDE_SOURCE
            )
        ]
        if len(exact_rows) != 1:
            raise ValueError(
                f"{language}: deployed exact override multiplicity drift"
            )
        exact_values[language] = exact_rows[0][1]
        if exact_rows[0][1] != EXACT_OVERRIDE_RENDERED[language]:
            raise ValueError(
                f"{language}: deployed exact override rendering drift"
            )
    overlay_report = validate_overlay_matrix(matrix)
    if expected_global_rows is not None and any(
        count != expected_global_rows for count in counts.values()
    ):
        raise ValueError(
            f"global Ruby row count drift: {counts!r} != "
            f"{expected_global_rows}"
        )
    return {
        "gate": True,
        "languages": list(LANGUAGES),
        "global_rows": counts,
        "expected_global_rows": expected_global_rows,
        "overlay_report": overlay_report,
        "exact_override_rendered": exact_values,
    }


def apply_snapshot(path: Path, expected_global_rows: int | None) -> dict:
    snapshot = load_snapshot(path)
    payloads = {
        language: load_payload(language)
        for language in LANGUAGES
    }
    candidates = {}
    for language in LANGUAGES:
        payload = payloads[language]
        bucket_key, rows = global_bucket(payload)
        candidate = dict(payload)
        candidate[bucket_key] = restore_bucket(
            language,
            rows,
            snapshot,
        )
        candidates[language] = candidate
    report = audit_payloads(candidates, expected_global_rows)

    stages = {}
    rollbacks = {}
    replaced = []
    try:
        for language in LANGUAGES:
            destination = payload_path(language)
            stage = destination.with_name(
                destination.name + ".stage_r67_r68_overlay"
            )
            rollback = destination.with_name(
                destination.name + ".bak_preR67R68CarryForward"
            )
            atomic_json_dump(stage, candidates[language])
            stages[language] = stage
            rollbacks[language] = rollback
        for language in LANGUAGES:
            destination = payload_path(language)
            atomic_file_copy(destination, rollbacks[language])
        for language in LANGUAGES:
            os.replace(stages[language], payload_path(language))
            replaced.append(language)
        deployed = {
            language: load_payload(language)
            for language in LANGUAGES
        }
        deployed_report = audit_payloads(
            deployed,
            expected_global_rows,
        )
        if deployed_report != report:
            raise ValueError(
                "deployed overlay audit differs from staged audit"
            )
    except Exception:
        for language in reversed(replaced):
            rollback = rollbacks[language]
            if rollback.exists():
                os.replace(rollback, payload_path(language))
        raise
    finally:
        for stage in stages.values():
            if stage.exists():
                stage.unlink()
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Seal, restore, or audit the reviewed R67/R68 Ruby overlays."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture")
    capture.add_argument("--output", required=True, type=Path)
    capture.add_argument(
        "--git-ref",
        help=(
            "Recovery-only source; must resolve to the pinned R72 parent."
        ),
    )

    apply = subparsers.add_parser("apply")
    apply.add_argument("--input", required=True, type=Path)
    apply.add_argument(
        "--expected-global-rows",
        type=int,
        default=EXPECTED_POST_R73_GLOBAL_ROWS,
    )

    audit = subparsers.add_parser("audit")
    audit.add_argument(
        "--expected-global-rows",
        type=int,
        default=EXPECTED_POST_R73_GLOBAL_ROWS,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "capture":
        snapshot = capture_snapshot(args.output, args.git_ref)
        report = {
            "gate": True,
            "snapshot": str(args.output),
            "snapshot_sha256": snapshot["snapshot_sha256"],
            "source_identity": snapshot["source_identity"],
            "global_rows_at_capture": snapshot["global_rows_at_capture"],
        }
    elif args.command == "apply":
        report = apply_snapshot(
            args.input,
            args.expected_global_rows,
        )
    else:
        payloads = {
            language: load_payload(language)
            for language in LANGUAGES
        }
        report = audit_payloads(
            payloads,
            args.expected_global_rows,
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            f"historical Ruby overlay gate failed: {error}",
            file=sys.stderr,
        )
        raise
