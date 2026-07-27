# -*- coding: utf-8 -*-
"""Fail-closed bare-word coverage gate for Kyoto corpus revision 7c04f97.

The schema-2 review remains an immutable b769038 parent.  This module verifies
the schema-3 successor without weakening the scanner in ``bare_word_audit.py``:

* every current scanner candidate is covered by one of 204 active entries;
* all 204 entries are used and their untruncated visible-line anchors match;
* 49 line reanchors are explicit (ten reviewed long-line splits);
* five tokens which moved to ``translation_or_note`` remain visibly present;
* both the corpus Git HEAD and the content fingerprint are pinned.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import warnings
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LEDGER_PATH = HERE / "_bare_word_reviewed_7c04f97.json"
PARENT_LEDGER_PATH = HERE / "_bare_word_reviewed.json"
LEGACY_SCANNER_PATH = HERE / "bare_word_audit.py"

LEDGER_SHA256 = (
    "A0FCC7442FC276D840180375F8861A4208DAEB0A35397D1C4696928DE1F7FADB"
)
PARENT_LEDGER_SHA256 = (
    "F97D5FBEE9B93AFA4A2A4C0ADB686CF8BFAA90C46F56AF67C0F261B46A290768"
)
EMPTY_SHA256 = (
    "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
)
PARENT_SOURCE_PIN = {
    "head_oid": "b769038ef15346a536ce93721d6f0f46849db0ea",
    "status_entries": 0,
    "status_sha256": EMPTY_SHA256,
    "content_files": 169,
    "content_sha256": (
        "264E4217BE484ABC2DC5EF7A22D83C56076C255BFB389F8218A0C215DD2420B6"
    ),
}
SOURCE_PIN = {
    "head_oid": "7c04f97c51a7cecf88918d2abc2e6bf2f34601a6",
    "status_entries": 0,
    "status_sha256": EMPTY_SHA256,
    "content_files": 169,
    "content_sha256": (
        "4F04FD2F3DBE0FC79909CBBEA61ED2848FC093AE2DFE3F0ADEB79882AEB04F52"
    ),
}
SUCCESSOR_SOURCE_PIN = {
    "head_oid": "d1642c276857c1fe400a6d597214ff7a923e7bd2",
    "status_entries": 0,
    "status_sha256": EMPTY_SHA256,
    "content_files": 169,
    "content_sha256": (
        "C8CAA1940F7F4685CE317B4107E9AA36AF28CBC47A06630CD24092D3C045BE1B"
    ),
}
# Filled from the untruncated candidate + five-scope-transition projection
# emitted by ``reviewed_bare_projection``.  It is shared by 7c04 and d164.
BARE_PROJECTION_SHA256 = (
    "04741F86E4E38DD29473D82EB95D2A0056C52AD8BC65EBBD9662BE94E9494DD1"
)
EXPECTED_COUNTS = {
    "parent_entries": 209,
    "parent_occurrences": 241,
    "active_entries": 204,
    "candidate_occurrences": 236,
    "reviewed_occurrences": 236,
    "unchanged_entries": 155,
    "reanchor_entries": 49,
    "reanchor_same_context": 39,
    "reanchor_split_context_reviewed": 10,
    "scope_transitions": 5,
    "scope_transition_anchor_occurrences": 5,
}
CONTEXT_HASH_POLICY = {
    "algorithm": "SHA-256",
    "encoding": "UTF-8",
    "serialization": (
        "JSON sort_keys=True, separators=(',', ':'), ensure_ascii=False"
    ),
    "fields": ["context", "kind", "line_class"],
    "context_projection": (
        "Full normalized visible line after the legacy scanner's protected-block, "
        "ruby, tag and URL masking; NUL runs become [R], whitespace is collapsed, "
        "and no length truncation is applied."
    ),
    "truncated": False,
}

JA_ROUNDO = (
    "rondolegado/2026-03/"
    "rondolegada_materialoj_202603_enhavoj_JA.html"
)
KO_ROUNDO = (
    "rondolegado/2026-03/"
    "rondolegada_materialoj_202603_enhavoj_KO.html"
)
REVUO_202504 = (
    "revuoj/revuo-orienta/2025/"
    "202504_Revuo_eltiritaj_Esperantaj_pagxoj.html"
)
INICIATORO_CHANGE_PATH = (
    "revuoj/revuo-orienta/2025/"
    "202506_Revuo_eltiritaj_Esperantaj_pagxoj_kun_japanaj_tradukoj.html"
)
EXPECTED_SPLIT_CONTEXT_KEYS = {
    (JA_ROUNDO, token) for token in ("ale", "guan", "luka", "mute", "sike")
} | {
    (KO_ROUNDO, token) for token in ("ale", "guan", "luka", "mute", "sike")
}
EXPECTED_SCOPE_TRANSITIONS = {
    (REVUO_202504, "Fūsui"): {"current_lines": [260], "file_visible_count": 1},
    (REVUO_202504, "Ki"): {"current_lines": [260], "file_visible_count": 1},
    (REVUO_202504, "Qi"): {"current_lines": [260], "file_visible_count": 1},
    (JA_ROUNDO, "dol"): {"current_lines": [1105], "file_visible_count": 2},
    (KO_ROUNDO, "dol"): {"current_lines": [1108], "file_visible_count": 2},
}


class AuditError(ValueError):
    """A pinned input, ledger invariant, or coverage invariant failed."""


_LEGACY = None


def legacy_scanner():
    """Load the existing scanner without changing it."""
    global _LEGACY
    if _LEGACY is None:
        spec = importlib.util.spec_from_file_location(
            "bare_word_audit_legacy_for_7c04f97",
            LEGACY_SCANNER_PATH,
        )
        if spec is None or spec.loader is None:
            raise AuditError(f"cannot load legacy scanner: {LEGACY_SCANNER_PATH}")
        module = importlib.util.module_from_spec(spec)
        # The immutable legacy module uses ``json.load(open(...))`` for its
        # stem inventory.  Keep its unrelated ResourceWarning out of this
        # successor gate without changing that module.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            spec.loader.exec_module(module)
        _LEGACY = module
    return _LEGACY


def stable_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def stable_json_sha256(value: Any) -> str:
    return hashlib.sha256(stable_json_bytes(value)).hexdigest().upper()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def normalized_visible_context(visible: str) -> str:
    """Return the legacy context before its historical ``[:500]`` truncation."""
    return re.sub(r"\s+", " ", re.sub(r"\x00+", "[R]", visible)).strip()


def context_sha256(context: str, kind: str, line_class: str) -> str:
    return stable_json_sha256({
        "context": context,
        "kind": kind,
        "line_class": line_class,
    })


def corpus_content_fingerprint(corpus_root: Path) -> dict[str, Any]:
    scanner = legacy_scanner()
    rows = []
    for dirname in scanner.CONTENT_DIRS:
        root = corpus_root / dirname
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".html", ".htm"}:
                rows.append([
                    path.relative_to(corpus_root).as_posix(),
                    file_sha256(path),
                ])
    return {"files": len(rows), "sha256": stable_json_sha256(rows)}


def git_repo_state(repo: Path) -> dict[str, Any]:
    def run(*args: str, binary: bool = False):
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode:
            raise AuditError(
                completed.stderr.decode("utf-8", errors="replace").strip()
            )
        if binary:
            return completed.stdout
        return completed.stdout.decode("utf-8", errors="strict").strip()

    status = run(
        "status",
        "--porcelain=v2",
        "-z",
        "--untracked-files=all",
        binary=True,
    )
    return {
        "head_oid": run("rev-parse", "HEAD"),
        "status_entries": status.count(b"\x00"),
        "status_sha256": hashlib.sha256(status).hexdigest().upper(),
    }


def source_observation(corpus_root: Path) -> dict[str, Any]:
    state = git_repo_state(corpus_root)
    fingerprint = corpus_content_fingerprint(corpus_root)
    return {
        **state,
        "content_files": fingerprint["files"],
        "content_sha256": fingerprint["sha256"],
    }


def git_parent_oid(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD^"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise AuditError(
            completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return completed.stdout.decode("ascii").strip()


def content_file_hashes(corpus_root: Path) -> dict[str, str]:
    scanner = legacy_scanner()
    rows = {}
    for dirname in scanner.CONTENT_DIRS:
        root = corpus_root / dirname
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".html", ".htm"}:
                rows[path.relative_to(corpus_root).as_posix()] = file_sha256(path)
    return rows


def source_pin_errors(
    expected: dict[str, Any],
    observed: dict[str, Any],
) -> list[dict[str, Any]]:
    errors = []
    for field, expected_value in expected.items():
        actual_value = observed.get(field)
        if actual_value != expected_value:
            errors.append({
                "field": field,
                "expected": expected_value,
                "actual": actual_value,
            })
    return errors


def require_source_pin(
    corpus_root: Path,
    expected: dict[str, Any],
) -> dict[str, Any]:
    observed = source_observation(corpus_root)
    errors = source_pin_errors(expected, observed)
    if errors:
        raise AuditError(f"corpus source pin mismatch: {errors}")
    return observed


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"JSON root must be an object: {path}")
    return value


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _validate_lines(lines: Any, label: str) -> list[int]:
    if (
        not isinstance(lines, list)
        or not lines
        or any(not _positive_int(line) for line in lines)
        or lines != sorted(set(lines))
    ):
        raise AuditError(f"{label}: sorted unique positive lines required")
    return lines


def _validate_anchor(anchor: Any, label: str) -> None:
    expected_fields = {
        "line",
        "expected_count",
        "kind",
        "line_class",
        "context_length",
        "context_sha256",
    }
    if not isinstance(anchor, dict) or set(anchor) != expected_fields:
        raise AuditError(f"{label}: exact anchor fields required")
    if not _positive_int(anchor["line"]):
        raise AuditError(f"{label}: positive line required")
    if not _positive_int(anchor["expected_count"]):
        raise AuditError(f"{label}: positive expected_count required")
    if not isinstance(anchor["kind"], str) or not anchor["kind"]:
        raise AuditError(f"{label}: kind required")
    if not isinstance(anchor["line_class"], str) or not anchor["line_class"]:
        raise AuditError(f"{label}: line_class required")
    if (
        not isinstance(anchor["context_length"], int)
        or isinstance(anchor["context_length"], bool)
        or anchor["context_length"] < 0
    ):
        raise AuditError(f"{label}: non-negative context_length required")
    if not re.fullmatch(r"[0-9A-F]{64}", anchor["context_sha256"] or ""):
        raise AuditError(f"{label}: uppercase SHA-256 required")


def _validate_anchor_list(
    anchors: Any,
    lines: list[int],
    expected_count: int,
    label: str,
) -> None:
    if not isinstance(anchors, list) or len(anchors) != len(lines):
        raise AuditError(f"{label}: one anchor per line required")
    for index, anchor in enumerate(anchors):
        _validate_anchor(anchor, f"{label}[{index}]")
    if [anchor["line"] for anchor in anchors] != lines:
        raise AuditError(f"{label}: anchor lines do not match")
    if sum(anchor["expected_count"] for anchor in anchors) != expected_count:
        raise AuditError(f"{label}: anchor occurrence count does not match")


def _anchor_without_line(anchor: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in anchor.items() if key != "line"}


def _anchor_multiset(anchors: Iterable[dict[str, Any]]) -> list[str]:
    return sorted(
        json.dumps(_anchor_without_line(anchor), sort_keys=True)
        for anchor in anchors
    )


def _parent_entry_index(parent_data: dict[str, Any]) -> dict[tuple[str, str], dict]:
    if parent_data.get("schema_version") != 2:
        raise AuditError("parent bare-word ledger must remain schema_version 2")
    entries = parent_data.get("entries")
    if not isinstance(entries, list):
        raise AuditError("parent bare-word entries must be a list")
    index = {}
    for row_id, row in enumerate(entries):
        if not isinstance(row, dict):
            raise AuditError(f"parent entry {row_id}: object required")
        key = (row.get("path"), row.get("token"))
        if (
            not all(isinstance(value, str) and value for value in key)
            or key in index
        ):
            raise AuditError(f"parent entry {row_id}: unique path/token required")
        _validate_lines(row.get("lines"), f"parent entry {row_id} lines")
        if not _positive_int(row.get("expected_count")):
            raise AuditError(
                f"parent entry {row_id}: positive expected_count required"
            )
        index[key] = row
    return index


def validate_ledger_structure(
    ledger: dict[str, Any],
    parent_data: dict[str, Any] | None = None,
) -> None:
    """Validate the complete b769038 -> 7c04f97 review partition."""
    if ledger.get("schema_version") != 3:
        raise AuditError("7c04f97 ledger requires schema_version 3")
    if ledger.get("context_hash") != CONTEXT_HASH_POLICY:
        raise AuditError("context hash policy changed or is incomplete")
    if ledger.get("counts") != EXPECTED_COUNTS:
        raise AuditError("schema-3 transition counts changed")
    if ledger.get("source") != SOURCE_PIN:
        raise AuditError("schema-3 source pin changed")

    parent = ledger.get("parent")
    if not isinstance(parent, dict) or set(parent) != {"ledger", "source"}:
        raise AuditError("exact parent ledger/source objects required")
    expected_parent_ledger = {
        "path": "_bare_word_reviewed.json",
        "sha256": PARENT_LEDGER_SHA256,
        "schema_version": 2,
    }
    if parent["ledger"] != expected_parent_ledger:
        raise AuditError("parent ledger identity changed")
    if parent["source"] != PARENT_SOURCE_PIN:
        raise AuditError("parent corpus identity changed")

    if parent_data is None:
        parent_data = load_json(PARENT_LEDGER_PATH)
    parent_index = _parent_entry_index(parent_data)
    if len(parent_index) != EXPECTED_COUNTS["parent_entries"]:
        raise AuditError("parent entry count changed")
    if (
        sum(row["expected_count"] for row in parent_index.values())
        != EXPECTED_COUNTS["parent_occurrences"]
    ):
        raise AuditError("parent occurrence count changed")

    entries = ledger.get("entries")
    transitions = ledger.get("scope_transitions")
    if not isinstance(entries, list) or len(entries) != 204:
        raise AuditError("exactly 204 active entries required")
    if not isinstance(transitions, list) or len(transitions) != 5:
        raise AuditError("exactly five scope transitions required")

    assigned = set()
    active_keys = set()
    dispositions = collections.Counter()
    split_keys = set()
    for row_id, row in enumerate(entries):
        expected_fields = {
            "path",
            "token",
            "lines",
            "expected_count",
            "category",
            "reason",
            "anchors",
            "transition",
        }
        if not isinstance(row, dict) or set(row) != expected_fields:
            raise AuditError(f"active entry {row_id}: exact fields required")
        key = (row["path"], row["token"])
        if key in active_keys or key not in parent_index:
            raise AuditError(f"active entry {row_id}: invalid path/token {key}")
        active_keys.add(key)
        assigned.add(key)
        parent_row = parent_index[key]
        for field in ("category", "reason"):
            if row[field] != parent_row[field]:
                raise AuditError(f"active entry {row_id}: {field} drifted")
        lines = _validate_lines(row["lines"], f"active entry {row_id} lines")
        if not _positive_int(row["expected_count"]):
            raise AuditError(f"active entry {row_id}: expected_count required")
        _validate_anchor_list(
            row["anchors"],
            lines,
            row["expected_count"],
            f"active entry {row_id} anchors",
        )

        transition = row["transition"]
        if not isinstance(transition, dict):
            raise AuditError(f"active entry {row_id}: transition required")
        required_transition_fields = {
            "kind",
            "disposition",
            "parent_lines",
            "parent_anchors",
        }
        optional_note = {"review_note"} if "review_note" in transition else set()
        if set(transition) != required_transition_fields | optional_note:
            raise AuditError(f"active entry {row_id}: transition fields changed")
        parent_lines = _validate_lines(
            transition["parent_lines"],
            f"active entry {row_id} parent_lines",
        )
        if parent_lines != parent_row["lines"]:
            raise AuditError(f"active entry {row_id}: parent lines drifted")
        _validate_anchor_list(
            transition["parent_anchors"],
            parent_lines,
            parent_row["expected_count"],
            f"active entry {row_id} parent anchors",
        )

        kind = transition["kind"]
        disposition = transition["disposition"]
        dispositions[disposition] += 1
        if kind == "unchanged":
            if optional_note:
                raise AuditError(f"active entry {row_id}: unexpected review note")
            if disposition != "unchanged_exact_line":
                raise AuditError(f"active entry {row_id}: bad unchanged disposition")
            if lines != parent_lines or row["anchors"] != transition["parent_anchors"]:
                raise AuditError(f"active entry {row_id}: unchanged anchor drifted")
        elif kind == "reanchor":
            if lines == parent_lines:
                raise AuditError(f"active entry {row_id}: reanchor did not move")
            if disposition == "reanchor_same_context":
                if optional_note:
                    raise AuditError(
                        f"active entry {row_id}: unexpected same-context note"
                    )
                if (
                    _anchor_multiset(row["anchors"])
                    != _anchor_multiset(transition["parent_anchors"])
                ):
                    raise AuditError(
                        f"active entry {row_id}: same-context anchor mutated"
                    )
            elif disposition == "reanchor_split_context_reviewed":
                if key not in EXPECTED_SPLIT_CONTEXT_KEYS:
                    raise AuditError(
                        f"active entry {row_id}: unexpected split-context key"
                    )
                split_keys.add(key)
                if transition.get("review_note") != (
                    "The 2026-03 JA/KO long line was split. The source token, "
                    "candidate kind and annotated_body class were manually "
                    "reconfirmed; shortening is not a review exemption."
                ):
                    raise AuditError(
                        f"active entry {row_id}: split review note changed"
                    )
                old = transition["parent_anchors"]
                new = row["anchors"]
                if len(old) != 1 or len(new) != 1:
                    raise AuditError(
                        f"active entry {row_id}: split anchor cardinality changed"
                    )
                invariant_fields = (
                    "expected_count",
                    "kind",
                    "line_class",
                )
                if any(old[0][field] != new[0][field] for field in invariant_fields):
                    raise AuditError(
                        f"active entry {row_id}: split anchor semantics changed"
                    )
                if new[0]["context_length"] >= old[0]["context_length"]:
                    raise AuditError(
                        f"active entry {row_id}: reviewed context is not shorter"
                    )
                if new[0]["context_sha256"] == old[0]["context_sha256"]:
                    raise AuditError(
                        f"active entry {row_id}: split context hash did not change"
                    )
            else:
                raise AuditError(f"active entry {row_id}: unknown reanchor type")
        else:
            raise AuditError(f"active entry {row_id}: unknown transition kind")

    if split_keys != EXPECTED_SPLIT_CONTEXT_KEYS:
        raise AuditError("the explicit set of ten shortened contexts changed")

    scope_keys = set()
    for row_id, row in enumerate(transitions):
        expected_fields = {
            "path",
            "token",
            "parent_lines",
            "current_lines",
            "expected_count",
            "file_visible_count",
            "category",
            "reason",
            "required_raw_presence",
            "disposition",
            "review_note",
            "parent_anchors",
            "current_anchors",
        }
        if not isinstance(row, dict) or set(row) != expected_fields:
            raise AuditError(
                f"scope transition {row_id}: exact fields required"
            )
        key = (row["path"], row["token"])
        if key in scope_keys or key not in parent_index:
            raise AuditError(f"scope transition {row_id}: invalid key {key}")
        scope_keys.add(key)
        assigned.add(key)
        parent_row = parent_index[key]
        expected_transition = EXPECTED_SCOPE_TRANSITIONS.get(key)
        if expected_transition is None:
            raise AuditError(f"scope transition {row_id}: unexpected key")
        if row["current_lines"] != expected_transition["current_lines"]:
            raise AuditError(f"scope transition {row_id}: current line changed")
        if row["file_visible_count"] != expected_transition["file_visible_count"]:
            raise AuditError(
                f"scope transition {row_id}: visible token count changed"
            )
        if row["expected_count"] != 1:
            raise AuditError(f"scope transition {row_id}: one anchor required")
        if row["parent_lines"] != parent_row["lines"]:
            raise AuditError(f"scope transition {row_id}: parent lines drifted")
        for field in ("category", "reason"):
            if row[field] != parent_row[field]:
                raise AuditError(f"scope transition {row_id}: {field} drifted")
        if row["required_raw_presence"] is not True:
            raise AuditError(f"scope transition {row_id}: raw presence required")
        if row["disposition"] != "still_present_reviewed_source_term":
            raise AuditError(f"scope transition {row_id}: bad disposition")
        if row["review_note"] != (
            "The token remains in visible source-language material, but the "
            "paragraph/translation layout now classifies its line as "
            "translation_or_note. It must never be silently retired."
        ):
            raise AuditError(f"scope transition {row_id}: review note changed")
        _validate_anchor_list(
            row["parent_anchors"],
            row["parent_lines"],
            parent_row["expected_count"],
            f"scope transition {row_id} parent anchors",
        )
        _validate_anchor_list(
            row["current_anchors"],
            row["current_lines"],
            row["expected_count"],
            f"scope transition {row_id} current anchors",
        )
        if any(
            anchor["line_class"] != "annotated_body"
            for anchor in row["parent_anchors"]
        ):
            raise AuditError(
                f"scope transition {row_id}: parent class must be annotated_body"
            )
        if any(
            anchor["line_class"] != "translation_or_note"
            for anchor in row["current_anchors"]
        ):
            raise AuditError(
                f"scope transition {row_id}: current class must be translation_or_note"
            )
        old_kinds = {anchor["kind"] for anchor in row["parent_anchors"]}
        new_kinds = {anchor["kind"] for anchor in row["current_anchors"]}
        if old_kinds != new_kinds or len(old_kinds) != 1:
            raise AuditError(f"scope transition {row_id}: token kind changed")

    if scope_keys != set(EXPECTED_SCOPE_TRANSITIONS):
        raise AuditError("the explicit set of five scope transitions changed")
    if assigned != set(parent_index):
        missing = sorted(set(parent_index) - assigned)
        extra = sorted(assigned - set(parent_index))
        raise AuditError(
            f"parent partition is incomplete: missing={missing} extra={extra}"
        )
    if active_keys & scope_keys:
        raise AuditError("active and scope-transition partitions overlap")

    if dispositions != {
        "unchanged_exact_line": 155,
        "reanchor_same_context": 39,
        "reanchor_split_context_reviewed": 10,
    }:
        raise AuditError(f"active transition partition changed: {dispositions}")


def scan_candidates(corpus_root: Path) -> list[dict[str, Any]]:
    """Run the unchanged schema-2 scanner over the selected corpus."""
    scanner = legacy_scanner()
    scanner.CORP = corpus_root
    occurrences = []
    for path in sorted(scanner.iter_html()):
        raw = path.read_text(encoding="utf-8", errors="ignore")
        if scanner.RUBY_RE.search(raw):
            rows, _stats = scanner.scan_document(path)
            occurrences.extend(rows)
    return occurrences


def occurrence_groups(
    occurrences: Iterable[dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    groups = collections.defaultdict(list)
    for row in occurrences:
        groups[(row["path"], row["token"])].append(row)
    return dict(groups)


def requested_line_records(
    corpus_root: Path,
    requested_lines: dict[str, set[int]],
    counted_tokens: dict[str, set[str]] | None = None,
) -> tuple[dict[tuple[str, int], dict[str, Any]], collections.Counter]:
    """Inspect exact lines with the same visibility projection as the scanner.

    ``counted_tokens`` additionally counts visible bare occurrences throughout
    selected files.  Ruby base text is masked, so those counts cannot be
    satisfied by an annotation elsewhere in the document.
    """
    scanner = legacy_scanner()
    scanner.CORP = corpus_root
    counted_tokens = counted_tokens or {}
    records = {}
    token_totals = collections.Counter()
    paths = sorted(set(requested_lines) | set(counted_tokens))
    for relative in paths:
        path = corpus_root / relative
        if not path.is_file():
            raise AuditError(f"reviewed corpus path disappeared: {relative}")
        raw = path.read_text(encoding="utf-8", errors="ignore")
        ruby_matches = list(scanner.RUBY_RE.finditer(raw))
        masked = scanner.mask_same_length(raw, scanner.HEAD_SCRIPT_STYLE_RE)
        masked = scanner.mask_same_length(masked, scanner.RUBY_RE)
        raw_lines = raw.splitlines(keepends=True)
        ruby_index = 0
        wanted = requested_lines.get(relative, set())
        count_these = counted_tokens.get(relative, set())
        for (line_no, offset, line), raw_line in zip(
            scanner.line_offsets(masked),
            raw_lines,
        ):
            raw_line_start = offset
            raw_line_end = offset + len(raw_line)
            while (
                ruby_index < len(ruby_matches)
                and ruby_matches[ruby_index].end() <= raw_line_start
            ):
                ruby_index += 1
            has_ruby = (
                ruby_index < len(ruby_matches)
                and ruby_matches[ruby_index].start() < raw_line_end
                and ruby_matches[ruby_index].end() > raw_line_start
            )
            if line_no not in wanted and not count_these:
                continue
            visible = scanner.visible_line(line)
            visible, _url_count = scanner.mask_urls(visible)
            line_class = scanner.classify_line(visible, has_ruby)
            tokens = [
                match.group()
                for match in scanner.WORD_RE.finditer(visible)
            ]
            if count_these:
                counts = collections.Counter(tokens)
                for token in count_these:
                    token_totals[(relative, token)] += counts[token]
            if line_no in wanted:
                records[(relative, line_no)] = {
                    "line": line_no,
                    "line_class": line_class,
                    "context": normalized_visible_context(visible),
                    "token_counts": dict(collections.Counter(tokens)),
                }
        missing_lines = [
            line for line in sorted(wanted) if (relative, line) not in records
        ]
        if missing_lines:
            raise AuditError(
                f"reviewed lines disappeared: {relative}:{missing_lines}"
            )
    return records, token_totals


def anchor_from_record(
    record: dict[str, Any],
    token: str,
    kind: str,
    expected_count: int,
) -> dict[str, Any]:
    context = record["context"]
    return {
        "line": record["line"],
        "expected_count": expected_count,
        "kind": kind,
        "line_class": record["line_class"],
        "context_length": len(context),
        "context_sha256": context_sha256(
            context,
            kind,
            record["line_class"],
        ),
    }


def candidate_anchors(
    path: str,
    token: str,
    rows: list[dict[str, Any]],
    records: dict[tuple[str, int], dict[str, Any]],
) -> list[dict[str, Any]]:
    by_line = collections.defaultdict(list)
    for row in rows:
        by_line[row["line"]].append(row)
    anchors = []
    for line, line_rows in sorted(by_line.items()):
        kinds = {row["kind"] for row in line_rows}
        classes = {row["line_class"] for row in line_rows}
        if len(kinds) != 1 or len(classes) != 1:
            raise AuditError(f"mixed candidate semantics: {path}:{line}:{token}")
        record = records.get((path, line))
        if record is None:
            raise AuditError(f"missing full-line record: {path}:{line}:{token}")
        if record["line_class"] != next(iter(classes)):
            raise AuditError(f"line classifier drift: {path}:{line}:{token}")
        anchors.append(anchor_from_record(
            record,
            token,
            next(iter(kinds)),
            len(line_rows),
        ))
    return anchors


def evaluate_coverage(
    ledger: dict[str, Any],
    candidates: list[dict[str, Any]],
    records: dict[tuple[str, int], dict[str, Any]],
    scope_token_totals: collections.Counter,
) -> dict[str, Any]:
    """Evaluate current candidates/anchors; usable independently in tests."""
    groups = occurrence_groups(candidates)
    entries = {(row["path"], row["token"]): row for row in ledger["entries"]}
    new_candidates = []
    for key in sorted(set(groups) - set(entries)):
        new_candidates.extend(groups[key])
    unused_entries = [
        {"path": path, "token": token}
        for path, token in sorted(set(entries) - set(groups))
    ]
    count_mismatches = []
    anchor_mismatches = []
    reviewed_occurrences = 0

    for key in sorted(set(entries) & set(groups)):
        entry = entries[key]
        rows = groups[key]
        reviewed_occurrences += len(rows)
        actual_lines = sorted({row["line"] for row in rows})
        if (
            len(rows) != entry["expected_count"]
            or actual_lines != entry["lines"]
        ):
            count_mismatches.append({
                "path": key[0],
                "token": key[1],
                "expected_count": entry["expected_count"],
                "actual_count": len(rows),
                "expected_lines": entry["lines"],
                "actual_lines": actual_lines,
            })
        try:
            actual_anchors = candidate_anchors(
                key[0],
                key[1],
                rows,
                records,
            )
        except AuditError as exc:
            anchor_mismatches.append({
                "path": key[0],
                "token": key[1],
                "error": str(exc),
            })
        else:
            if actual_anchors != entry["anchors"]:
                anchor_mismatches.append({
                    "path": key[0],
                    "token": key[1],
                    "expected": entry["anchors"],
                    "actual": actual_anchors,
                })

    scope_mismatches = []
    for row in ledger["scope_transitions"]:
        key = (row["path"], row["token"])
        actual_anchors = []
        for expected_anchor in row["current_anchors"]:
            line = expected_anchor["line"]
            record = records.get((row["path"], line))
            if record is None:
                scope_mismatches.append({
                    "path": row["path"],
                    "token": row["token"],
                    "error": f"scope anchor line disappeared: {line}",
                })
                continue
            raw_count = record["token_counts"].get(row["token"], 0)
            actual_anchors.append(anchor_from_record(
                record,
                row["token"],
                expected_anchor["kind"],
                raw_count,
            ) if raw_count else {
                "line": line,
                "actual_visible_count": 0,
            })
        if actual_anchors != row["current_anchors"]:
            scope_mismatches.append({
                "path": row["path"],
                "token": row["token"],
                "expected": row["current_anchors"],
                "actual": actual_anchors,
            })
        actual_file_count = scope_token_totals[key]
        if actual_file_count != row["file_visible_count"]:
            scope_mismatches.append({
                "path": row["path"],
                "token": row["token"],
                "expected_file_visible_count": row["file_visible_count"],
                "actual_file_visible_count": actual_file_count,
            })

    expected_candidate_count = ledger["counts"]["candidate_occurrences"]
    expected_reviewed_count = ledger["counts"]["reviewed_occurrences"]
    count_gate = (
        len(candidates) == expected_candidate_count
        and reviewed_occurrences == expected_reviewed_count
    )
    coverage_gate = not any((
        new_candidates,
        unused_entries,
        count_mismatches,
        anchor_mismatches,
        scope_mismatches,
    )) and count_gate
    return {
        "candidate_occurrences": len(candidates),
        "reviewed_occurrences": reviewed_occurrences,
        "active_entries": len(entries),
        "scope_transitions": len(ledger["scope_transitions"]),
        "new_candidates": new_candidates,
        "unused_entries": unused_entries,
        "count_mismatches": count_mismatches,
        "mutated_anchors": anchor_mismatches,
        "scope_transition_mismatches": scope_mismatches,
        "count_gate": count_gate,
        "coverage_gate": coverage_gate,
    }


def reviewed_bare_projection(
    corpus_root: Path,
    ledger: dict[str, Any],
) -> dict[str, Any]:
    """Project every bare candidate and preserved scope-transition anchor.

    Unlike the legacy report's 500-character display context, every anchor in
    this projection hashes the full normalized visible line.
    """
    candidates = scan_candidates(corpus_root)
    groups = occurrence_groups(candidates)
    requested = collections.defaultdict(set)
    counted = collections.defaultdict(set)
    for row in ledger["entries"]:
        requested[row["path"]].update(row["lines"])
    for (path, _token), rows in groups.items():
        requested[path].update(candidate["line"] for candidate in rows)
    for row in ledger["scope_transitions"]:
        requested[row["path"]].update(row["current_lines"])
        counted[row["path"]].add(row["token"])
    records, scope_totals = requested_line_records(
        corpus_root,
        dict(requested),
        dict(counted),
    )
    coverage = evaluate_coverage(
        ledger,
        candidates,
        records,
        scope_totals,
    )

    candidate_projection = []
    for key in sorted(groups):
        rows = groups[key]
        candidate_projection.append({
            "path": key[0],
            "token": key[1],
            "count": len(rows),
            "anchors": candidate_anchors(
                key[0],
                key[1],
                rows,
                records,
            ),
        })
    scope_projection = []
    for row in ledger["scope_transitions"]:
        anchors = []
        for expected_anchor in row["current_anchors"]:
            record = records[(row["path"], expected_anchor["line"])]
            visible_count = record["token_counts"].get(row["token"], 0)
            if visible_count < 1:
                raise AuditError(
                    "scope-transition token disappeared while projecting: "
                    f"{row['path']}:{expected_anchor['line']}:{row['token']}"
                )
            anchors.append(anchor_from_record(
                record,
                row["token"],
                expected_anchor["kind"],
                visible_count,
            ))
        scope_projection.append({
            "path": row["path"],
            "token": row["token"],
            "file_visible_count": scope_totals[(row["path"], row["token"])],
            "anchors": anchors,
        })
    payload = {
        "schema_version": 1,
        "candidate_occurrences": len(candidates),
        "active_entries": len(ledger["entries"]),
        "scope_transitions": len(ledger["scope_transitions"]),
        "candidates": candidate_projection,
        "scope_transition_anchors": scope_projection,
    }
    return {
        "payload": payload,
        "sha256": stable_json_sha256(payload),
        "coverage": coverage,
    }


def iniciatoro_annotation_transition(
    parent_corpus: Path,
    successor_corpus: Path,
) -> dict[str, Any]:
    """Prove that d164 changes only one annotated ``iniciatoro`` surface."""
    parent_hashes = content_file_hashes(parent_corpus)
    successor_hashes = content_file_hashes(successor_corpus)
    changed_files = sorted(
        path
        for path in set(parent_hashes) | set(successor_hashes)
        if parent_hashes.get(path) != successor_hashes.get(path)
    )
    parent_path = parent_corpus / INICIATORO_CHANGE_PATH
    successor_path = successor_corpus / INICIATORO_CHANGE_PATH
    parent_text = parent_path.read_text(encoding="utf-8", errors="strict")
    successor_text = successor_path.read_text(encoding="utf-8", errors="strict")
    parent_lines = parent_text.splitlines()
    successor_lines = successor_text.splitlines()
    changed_lines = []
    if len(parent_lines) == len(successor_lines):
        changed_lines = [
            index
            for index, (old, new) in enumerate(
                zip(parent_lines, successor_lines),
                1,
            )
            if old != new
        ]

    scanner = legacy_scanner()
    parent_visible = scanner.RUBY_RE.sub(
        lambda match: match.group("rb"),
        parent_text,
    )
    successor_visible = scanner.RUBY_RE.sub(
        lambda match: match.group("rb"),
        successor_text,
    )
    old_line = parent_lines[changed_lines[0] - 1] if len(changed_lines) == 1 else ""
    new_line = (
        successor_lines[changed_lines[0] - 1] if len(changed_lines) == 1 else ""
    )
    old_line_visible = scanner.RUBY_RE.sub(
        lambda match: match.group("rb"),
        old_line,
    )
    new_line_visible = scanner.RUBY_RE.sub(
        lambda match: match.group("rb"),
        new_line,
    )
    old_roots = [
        match.group("rb").strip()
        for match in scanner.RUBY_RE.finditer(old_line)
    ]
    new_roots = [
        match.group("rb").strip()
        for match in scanner.RUBY_RE.finditer(new_line)
    ]
    root_replacement_positions = [
        index
        for index in range(len(old_roots) - 1)
        if old_roots[index:index + 2] == ["iniciat", "or"]
        and new_roots == (
            old_roots[:index] + ["iniciator"] + old_roots[index + 2:]
        )
    ]
    parent_ruby_elements = len(scanner.RUBY_RE.findall(parent_text))
    successor_ruby_elements = len(scanner.RUBY_RE.findall(successor_text))
    parent_oid = git_parent_oid(successor_corpus)
    gate = (
        set(parent_hashes) == set(successor_hashes)
        and changed_files == [INICIATORO_CHANGE_PATH]
        and changed_lines == [117]
        and parent_oid == SOURCE_PIN["head_oid"]
        and parent_visible == successor_visible
        and old_line_visible == new_line_visible
        and old_line_visible.count("iniciatoro") == 1
        and len(root_replacement_positions) == 1
        and successor_ruby_elements == parent_ruby_elements - 1
    )
    return {
        "path": INICIATORO_CHANGE_PATH,
        "changed_content_files": changed_files,
        "changed_lines": changed_lines,
        "successor_parent_oid": parent_oid,
        "annotated_surface": "iniciatoro",
        "annotated_surface_occurrences": old_line_visible.count("iniciatoro"),
        "parent_roots": ["iniciat", "or"],
        "successor_roots": ["iniciator"],
        "parent_ruby_elements_in_file": parent_ruby_elements,
        "successor_ruby_elements_in_file": successor_ruby_elements,
        "ruby_element_delta": successor_ruby_elements - parent_ruby_elements,
        "visible_base_text_identical": parent_visible == successor_visible,
        "gate": gate,
    }


def audit_successor_bare_projection(
    parent_corpus: Path,
    successor_corpus: Path,
    ledger_path: Path = LEDGER_PATH,
    parent_ledger_path: Path = PARENT_LEDGER_PATH,
) -> dict[str, Any]:
    """Prove d164's annotated edit leaves the pinned 7c04 bare scope intact."""
    if file_sha256(ledger_path) != LEDGER_SHA256:
        raise AuditError("7c04 schema-3 authority hash mismatch")
    if file_sha256(parent_ledger_path) != PARENT_LEDGER_SHA256:
        raise AuditError("immutable schema-2 parent ledger hash mismatch")
    ledger = load_json(ledger_path)
    parent_data = load_json(parent_ledger_path)
    validate_ledger_structure(ledger, parent_data)

    parent_source = source_observation(parent_corpus)
    successor_source = source_observation(successor_corpus)
    parent_source_errors = source_pin_errors(SOURCE_PIN, parent_source)
    successor_source_errors = source_pin_errors(
        SUCCESSOR_SOURCE_PIN,
        successor_source,
    )
    parent_projection = reviewed_bare_projection(parent_corpus, ledger)
    successor_projection = reviewed_bare_projection(successor_corpus, ledger)
    annotation_transition = iniciatoro_annotation_transition(
        parent_corpus,
        successor_corpus,
    )
    projection_identical = (
        parent_projection["sha256"] == successor_projection["sha256"]
    )
    sealed_projection = (
        parent_projection["sha256"] == BARE_PROJECTION_SHA256
        and successor_projection["sha256"] == BARE_PROJECTION_SHA256
    )
    gate = (
        not parent_source_errors
        and not successor_source_errors
        and parent_projection["coverage"]["coverage_gate"]
        and successor_projection["coverage"]["coverage_gate"]
        and projection_identical
        and sealed_projection
        and annotation_transition["gate"]
    )
    return {
        "schema_version": 1,
        "scope": "7c04f97_to_d1642c2_bare_projection",
        "authority": {
            "ledger_path": ledger_path.name,
            "ledger_sha256": file_sha256(ledger_path),
            "expected_ledger_sha256": LEDGER_SHA256,
        },
        "parent_source": parent_source,
        "parent_source_pin_errors": parent_source_errors,
        "successor_source": successor_source,
        "successor_source_pin_errors": successor_source_errors,
        "annotation_transition": annotation_transition,
        "parent_bare_projection": {
            "sha256": parent_projection["sha256"],
            **{
                key: parent_projection["payload"][key]
                for key in (
                    "candidate_occurrences",
                    "active_entries",
                    "scope_transitions",
                )
            },
            "coverage_gate": parent_projection["coverage"]["coverage_gate"],
        },
        "successor_bare_projection": {
            "sha256": successor_projection["sha256"],
            **{
                key: successor_projection["payload"][key]
                for key in (
                    "candidate_occurrences",
                    "active_entries",
                    "scope_transitions",
                )
            },
            "coverage_gate": successor_projection["coverage"]["coverage_gate"],
        },
        "projection_identical": projection_identical,
        "sealed_projection": sealed_projection,
        "gate": gate,
    }


def audit_corpus(
    corpus_root: Path,
    ledger_path: Path = LEDGER_PATH,
    parent_ledger_path: Path = PARENT_LEDGER_PATH,
) -> dict[str, Any]:
    ledger = load_json(ledger_path)
    if file_sha256(ledger_path) != LEDGER_SHA256:
        raise AuditError("7c04 schema-3 authority hash mismatch")
    if file_sha256(parent_ledger_path) != PARENT_LEDGER_SHA256:
        raise AuditError("immutable schema-2 parent ledger hash mismatch")
    parent_data = load_json(parent_ledger_path)
    validate_ledger_structure(ledger, parent_data)

    observed_source = source_observation(corpus_root)
    source_errors = source_pin_errors(SOURCE_PIN, observed_source)
    projection = reviewed_bare_projection(corpus_root, ledger)
    coverage = projection["coverage"]
    gate = not source_errors and coverage["coverage_gate"]
    return {
        "schema_version": 1,
        "scope": "bare_word_review_7c04f97",
        "ledger": {
            "path": ledger_path.name,
            "sha256": file_sha256(ledger_path),
            "parent_path": parent_ledger_path.name,
            "parent_sha256": file_sha256(parent_ledger_path),
        },
        "bare_projection_sha256": projection["sha256"],
        "bare_projection_sealed": (
            projection["sha256"] == BARE_PROJECTION_SHA256
        ),
        "source": observed_source,
        "source_pin_errors": source_errors,
        **coverage,
        "gate": gate and projection["sha256"] == BARE_PROJECTION_SHA256,
    }


def corpus_from_args(value: str | None) -> Path:
    raw = value or os.environ.get("ESP_CORPUS_PATH")
    if not raw:
        raise AuditError(
            "latest corpus is required via --corpus or ESP_CORPUS_PATH"
        )
    return Path(raw).resolve()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus",
        help="clean 7c04f97 corpus checkout; otherwise ESP_CORPUS_PATH",
    )
    parser.add_argument(
        "--successor-corpus",
        help=(
            "optional clean d1642c2 checkout; otherwise "
            "ESP_BARE_WORD_D164_CORPUS_PATH"
        ),
    )
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    parser.add_argument("--parent-ledger", type=Path, default=PARENT_LEDGER_PATH)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    parent_corpus = corpus_from_args(args.corpus)
    successor_raw = (
        args.successor_corpus
        or os.environ.get("ESP_BARE_WORD_D164_CORPUS_PATH")
    )
    if successor_raw:
        report = audit_successor_bare_projection(
            parent_corpus,
            Path(successor_raw).resolve(),
            args.ledger.resolve(),
            args.parent_ledger.resolve(),
        )
    else:
        report = audit_corpus(
            parent_corpus,
            args.ledger.resolve(),
            args.parent_ledger.resolve(),
        )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif successor_raw:
        parent_projection = report["parent_bare_projection"]
        successor_projection = report["successor_bare_projection"]
        print(
            "bare-word 7c04f97 -> d1642c2: "
            f"parent={parent_projection['candidate_occurrences']} "
            f"successor={successor_projection['candidate_occurrences']} "
            f"projection={'IDENTICAL' if report['projection_identical'] else 'DIFF'} "
            f"iniciatoro={'PASS' if report['annotation_transition']['gate'] else 'FAIL'} "
            f"gate={'PASS' if report['gate'] else 'FAIL'}"
        )
    else:
        print(
            "bare-word 7c04f97: "
            f"active={report['active_entries']} "
            f"candidates={report['candidate_occurrences']} "
            f"reviewed={report['reviewed_occurrences']} "
            f"scope-transitions={report['scope_transitions']} "
            f"gate={'PASS' if report['gate'] else 'FAIL'}"
        )
        if not report["gate"]:
            print(json.dumps({
                "source_pin_errors": report["source_pin_errors"],
                "new_candidates": report["new_candidates"],
                "unused_entries": report["unused_entries"],
                "count_mismatches": report["count_mismatches"],
                "mutated_anchors": report["mutated_anchors"],
                "scope_transition_mismatches": (
                    report["scope_transition_mismatches"]
                ),
            }, ensure_ascii=False, indent=2))
    if successor_raw and not report["gate"] and not args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["gate"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
