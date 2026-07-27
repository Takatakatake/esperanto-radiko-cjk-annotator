# -*- coding: utf-8 -*-
"""Build the schema-3 bare-word ledger for corpus revision 7c04f97.

This transition builder needs two clean, pinned checkouts:

* ``--parent-corpus`` / ``ESP_BARE_WORD_PARENT_CORPUS_PATH``: b769038
* ``--corpus`` / ``ESP_CORPUS_PATH``: 7c04f97

It never rewrites the immutable schema-2 parent ledger.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
from pathlib import Path

import bare_word_audit_7c04f97 as audit


OUTPUT = audit.LEDGER_PATH
SPLIT_REVIEW_NOTE = (
    "The 2026-03 JA/KO long line was split. The source token, "
    "candidate kind and annotated_body class were manually "
    "reconfirmed; shortening is not a review exemption."
)
SCOPE_REVIEW_NOTE = (
    "The token remains in visible source-language material, but the "
    "paragraph/translation layout now classifies its line as "
    "translation_or_note. It must never be silently retired."
)


def _path_from_cli_env(
    cli_value: str | None,
    env_name: str,
    label: str,
) -> Path:
    raw = cli_value or os.environ.get(env_name)
    if not raw:
        raise audit.AuditError(
            f"{label} is required via its CLI option or {env_name}"
        )
    return Path(raw).resolve()


def _line_requests(
    groups: dict[tuple[str, str], list[dict]],
) -> dict[str, set[int]]:
    requested = collections.defaultdict(set)
    for (path, _token), rows in groups.items():
        requested[path].update(row["line"] for row in rows)
    return dict(requested)


def _anchor_multiset(anchors: list[dict]) -> list[str]:
    return sorted(
        json.dumps(
            {key: value for key, value in anchor.items() if key != "line"},
            sort_keys=True,
        )
        for anchor in anchors
    )


def _verify_parent_candidate_inventory(
    parent_entries: dict[tuple[str, str], dict],
    parent_groups: dict[tuple[str, str], list[dict]],
) -> None:
    if set(parent_entries) != set(parent_groups):
        raise audit.AuditError(
            "schema-2 parent does not exactly cover b769038 candidates: "
            f"ledger_only={sorted(set(parent_entries) - set(parent_groups))} "
            f"candidate_only={sorted(set(parent_groups) - set(parent_entries))}"
        )
    for key, entry in parent_entries.items():
        rows = parent_groups[key]
        actual_lines = sorted({row["line"] for row in rows})
        if (
            len(rows) != entry["expected_count"]
            or actual_lines != entry["lines"]
        ):
            raise audit.AuditError(
                f"schema-2 parent occurrence drift for {key}: "
                f"count={len(rows)} lines={actual_lines}"
            )


def _candidate_anchors_for_all(
    groups: dict[tuple[str, str], list[dict]],
    records: dict[tuple[str, int], dict],
) -> dict[tuple[str, str], list[dict]]:
    return {
        key: audit.candidate_anchors(
            key[0],
            key[1],
            rows,
            records,
        )
        for key, rows in groups.items()
    }


def build(
    parent_corpus: Path,
    current_corpus: Path,
    parent_ledger_path: Path = audit.PARENT_LEDGER_PATH,
) -> dict:
    if audit.file_sha256(parent_ledger_path) != audit.PARENT_LEDGER_SHA256:
        raise audit.AuditError("immutable schema-2 parent ledger hash mismatch")
    parent_data = audit.load_json(parent_ledger_path)
    parent_entries = audit._parent_entry_index(parent_data)
    parent_source = audit.require_source_pin(
        parent_corpus,
        audit.PARENT_SOURCE_PIN,
    )
    current_source = audit.require_source_pin(
        current_corpus,
        audit.SOURCE_PIN,
    )

    parent_candidates = audit.scan_candidates(parent_corpus)
    current_candidates = audit.scan_candidates(current_corpus)
    parent_groups = audit.occurrence_groups(parent_candidates)
    current_groups = audit.occurrence_groups(current_candidates)
    _verify_parent_candidate_inventory(parent_entries, parent_groups)

    if len(parent_candidates) != 241 or len(current_candidates) != 236:
        raise audit.AuditError(
            "candidate occurrence totals changed: "
            f"parent={len(parent_candidates)} current={len(current_candidates)}"
        )
    if set(current_groups) - set(parent_entries):
        raise audit.AuditError(
            "new path/token candidates are not eligible for automatic review: "
            f"{sorted(set(current_groups) - set(parent_entries))}"
        )
    missing_keys = set(parent_entries) - set(current_groups)
    if missing_keys != set(audit.EXPECTED_SCOPE_TRANSITIONS):
        raise audit.AuditError(
            "the five candidate-to-scope transitions changed: "
            f"{sorted(missing_keys)}"
        )

    parent_records, _unused_parent_counts = audit.requested_line_records(
        parent_corpus,
        _line_requests(parent_groups),
    )
    parent_anchors = _candidate_anchors_for_all(
        parent_groups,
        parent_records,
    )

    current_requests = _line_requests(current_groups)
    counted_tokens = collections.defaultdict(set)
    for key, transition in audit.EXPECTED_SCOPE_TRANSITIONS.items():
        current_requests.setdefault(key[0], set()).update(
            transition["current_lines"]
        )
        counted_tokens[key[0]].add(key[1])
    current_records, visible_counts = audit.requested_line_records(
        current_corpus,
        current_requests,
        dict(counted_tokens),
    )
    current_anchors = _candidate_anchors_for_all(
        current_groups,
        current_records,
    )

    active_entries = []
    disposition_counts = collections.Counter()
    for parent_row in parent_data["entries"]:
        key = (parent_row["path"], parent_row["token"])
        if key in missing_keys:
            continue
        rows = current_groups[key]
        lines = sorted({row["line"] for row in rows})
        anchors = current_anchors[key]
        old_anchors = parent_anchors[key]
        if lines == parent_row["lines"]:
            if anchors != old_anchors:
                raise audit.AuditError(
                    f"same-line context mutated without review: {key}"
                )
            transition = {
                "kind": "unchanged",
                "disposition": "unchanged_exact_line",
                "parent_lines": parent_row["lines"],
                "parent_anchors": old_anchors,
            }
        elif _anchor_multiset(anchors) == _anchor_multiset(old_anchors):
            transition = {
                "kind": "reanchor",
                "disposition": "reanchor_same_context",
                "parent_lines": parent_row["lines"],
                "parent_anchors": old_anchors,
            }
        elif key in audit.EXPECTED_SPLIT_CONTEXT_KEYS:
            if len(old_anchors) != 1 or len(anchors) != 1:
                raise audit.AuditError(
                    f"reviewed split must remain one old/new line: {key}"
                )
            invariant_fields = ("expected_count", "kind", "line_class")
            if any(
                old_anchors[0][field] != anchors[0][field]
                for field in invariant_fields
            ):
                raise audit.AuditError(
                    f"reviewed split changed candidate semantics: {key}"
                )
            if (
                anchors[0]["context_length"]
                >= old_anchors[0]["context_length"]
            ):
                raise audit.AuditError(
                    f"reviewed split context is not shorter: {key}"
                )
            transition = {
                "kind": "reanchor",
                "disposition": "reanchor_split_context_reviewed",
                "parent_lines": parent_row["lines"],
                "parent_anchors": old_anchors,
                "review_note": SPLIT_REVIEW_NOTE,
            }
        else:
            raise audit.AuditError(
                f"unreviewed full-context mutation during reanchor: {key}"
            )
        disposition_counts[transition["disposition"]] += 1
        active_entries.append({
            "path": parent_row["path"],
            "token": parent_row["token"],
            "lines": lines,
            "expected_count": len(rows),
            "category": parent_row["category"],
            "reason": parent_row["reason"],
            "anchors": anchors,
            "transition": transition,
        })

    scope_transitions = []
    for parent_row in parent_data["entries"]:
        key = (parent_row["path"], parent_row["token"])
        if key not in missing_keys:
            continue
        expected = audit.EXPECTED_SCOPE_TRANSITIONS[key]
        old_anchors = parent_anchors[key]
        kinds = {anchor["kind"] for anchor in old_anchors}
        if len(kinds) != 1:
            raise audit.AuditError(f"scope transition kind is ambiguous: {key}")
        kind = next(iter(kinds))
        new_anchors = []
        for line in expected["current_lines"]:
            record = current_records[(key[0], line)]
            raw_count = record["token_counts"].get(key[1], 0)
            if raw_count < 1:
                raise audit.AuditError(
                    f"scope-transition source token disappeared: {key}:{line}"
                )
            new_anchors.append(audit.anchor_from_record(
                record,
                key[1],
                kind,
                raw_count,
            ))
        expected_count = sum(
            anchor["expected_count"] for anchor in new_anchors
        )
        file_visible_count = visible_counts[key]
        if file_visible_count != expected["file_visible_count"]:
            raise audit.AuditError(
                f"scope-transition visible count changed: {key} "
                f"{file_visible_count} != {expected['file_visible_count']}"
            )
        scope_transitions.append({
            "path": parent_row["path"],
            "token": parent_row["token"],
            "parent_lines": parent_row["lines"],
            "current_lines": expected["current_lines"],
            "expected_count": expected_count,
            "file_visible_count": file_visible_count,
            "category": parent_row["category"],
            "reason": parent_row["reason"],
            "required_raw_presence": True,
            "disposition": "still_present_reviewed_source_term",
            "review_note": SCOPE_REVIEW_NOTE,
            "parent_anchors": old_anchors,
            "current_anchors": new_anchors,
        })

    counts = {
        "parent_entries": len(parent_entries),
        "parent_occurrences": len(parent_candidates),
        "active_entries": len(active_entries),
        "candidate_occurrences": len(current_candidates),
        "reviewed_occurrences": sum(
            row["expected_count"] for row in active_entries
        ),
        "unchanged_entries": disposition_counts["unchanged_exact_line"],
        "reanchor_entries": (
            disposition_counts["reanchor_same_context"]
            + disposition_counts["reanchor_split_context_reviewed"]
        ),
        "reanchor_same_context": disposition_counts["reanchor_same_context"],
        "reanchor_split_context_reviewed": disposition_counts[
            "reanchor_split_context_reviewed"
        ],
        "scope_transitions": len(scope_transitions),
        "scope_transition_anchor_occurrences": sum(
            row["expected_count"] for row in scope_transitions
        ),
    }
    if counts != audit.EXPECTED_COUNTS:
        raise audit.AuditError(f"transition counts changed: {counts}")
    if parent_source != audit.PARENT_SOURCE_PIN:
        raise audit.AuditError("parent source observation changed")
    if current_source != audit.SOURCE_PIN:
        raise audit.AuditError("current source observation changed")

    payload = {
        "schema_version": 3,
        "scope": (
            "Exact reviewed non-annotation occurrences at Kyoto corpus "
            "7c04f97, transitioned from immutable b769038 schema-2 review"
        ),
        "parent": {
            "ledger": {
                "path": parent_ledger_path.name,
                "sha256": audit.PARENT_LEDGER_SHA256,
                "schema_version": 2,
            },
            "source": audit.PARENT_SOURCE_PIN,
        },
        "source": audit.SOURCE_PIN,
        "context_hash": audit.CONTEXT_HASH_POLICY,
        "counts": counts,
        "entries": active_entries,
        "scope_transitions": scope_transitions,
    }
    audit.validate_ledger_structure(payload, parent_data)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--parent-corpus",
        help=(
            "clean b769038 checkout; otherwise "
            "ESP_BARE_WORD_PARENT_CORPUS_PATH"
        ),
    )
    parser.add_argument(
        "--corpus",
        help="clean 7c04f97 checkout; otherwise ESP_CORPUS_PATH",
    )
    parser.add_argument(
        "--parent-ledger",
        type=Path,
        default=audit.PARENT_LEDGER_PATH,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    payload = build(
        _path_from_cli_env(
            args.parent_corpus,
            "ESP_BARE_WORD_PARENT_CORPUS_PATH",
            "parent corpus",
        ),
        _path_from_cli_env(
            args.corpus,
            "ESP_CORPUS_PATH",
            "current corpus",
        ),
        args.parent_ledger.resolve(),
    )
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        OUTPUT.write_text(rendered, encoding="utf-8", newline="\n")
    elif args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit("7c04f97 bare-word ledger is stale")
    print(json.dumps({
        "mode": "write" if args.write else ("check" if args.check else "dry-run"),
        "output": str(OUTPUT),
        "source_head": payload["source"]["head_oid"],
        **payload["counts"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
