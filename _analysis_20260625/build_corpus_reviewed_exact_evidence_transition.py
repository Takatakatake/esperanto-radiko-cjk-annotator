# -*- coding: utf-8 -*-
"""Apply/check the explicit d1642c2 -> ccb9398 evidence-only transition.

The selected 625 residual surfaces remain unchanged.  The newer clean corpus
adds one document and two reviewed ``Gugyeol`` ruby instances, so occurrence
counts, paths and annotation-variant evidence legitimately change.  This
builder proves that every runtime-bearing typed rule and selected JA/ZH/KO
gloss remains byte-for-byte equivalent before it re-pins the evidence.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess

from atomic_json import atomic_json_dump
import build_corpus_reviewed_exact_manifest as reviewed
import no_worsening_audit as audit


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LEDGER_PATH = HERE / "_corpus_reviewed_exact_evidence_transition_ccb9398.json"
OUTPUT = HERE / "_corpus_reviewed_exact_app_manifest.json"
MANIFEST_PATH = "_analysis_20260625/_corpus_reviewed_exact_app_manifest.json"
ROW_SEMANTIC_FIELDS = (
    "surface", "target", "typed_roles", "signature", "typed",
    "available_expected_options", "annotation_keys",
)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def canonical_hash(value) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(raw)


def git_blob(commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode:
        raise ValueError(
            "cannot read pinned parent manifest: "
            + completed.stderr.decode("utf-8", errors="replace")
        )
    return completed.stdout


def git_tree(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=repo,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode:
        raise ValueError(
            "cannot read candidate corpus tree: "
            + completed.stderr.decode("utf-8", errors="replace")
        )
    return completed.stdout.decode("ascii").strip()


def row_semantics(rows: list[dict]) -> list[dict]:
    return [{key: row[key] for key in ROW_SEMANTIC_FIELDS} for row in rows]


def annotation_semantics(annotations: dict) -> dict:
    return {
        key: {"piece": row["piece"], "glosses": row["glosses"]}
        for key, row in annotations.items()
    }


def path_counter(row: dict) -> collections.Counter:
    return collections.Counter({item["path"]: item["count"] for item in row["paths"]})


def evidence_deltas(parent: dict, candidate: dict) -> list[dict]:
    old_rows = {row["surface"]: row for row in parent["exact_surfaces"]}
    new_rows = {row["surface"]: row for row in candidate["exact_surfaces"]}
    if set(old_rows) != set(new_rows):
        raise ValueError("reviewed exact surface set changed")
    result = []
    for surface in sorted(old_rows):
        old = old_rows[surface]
        new = new_rows[surface]
        if old == new:
            continue
        old_semantic = {key: old[key] for key in ROW_SEMANTIC_FIELDS}
        new_semantic = {key: new[key] for key in ROW_SEMANTIC_FIELDS}
        if old_semantic != new_semantic:
            raise ValueError(f"runtime-bearing reviewed rule changed: {surface!r}")
        delta = path_counter(new) - path_counter(old)
        removed = path_counter(old) - path_counter(new)
        if removed:
            raise ValueError(f"reviewed evidence path was removed: {surface!r}")
        result.append({
            "surface": surface,
            "old_count": old["count"],
            "new_count": new["count"],
            "path_deltas": dict(sorted(delta.items())),
        })
    return result


def validate_ledger(ledger: dict) -> None:
    if ledger.get("schema_version") != 1:
        raise ValueError("unsupported reviewed-exact evidence transition schema")
    if ledger.get("parent", {}).get("manifest_path") != MANIFEST_PATH:
        raise ValueError("reviewed-exact parent path changed")
    if ledger.get("parent", {}).get("counts") != {
        "exact_surfaces": 625,
        "exact_instances": 2740,
        "ruby_context_annotations": 924,
    }:
        raise ValueError("reviewed-exact parent count closure changed")
    if ledger.get("candidate", {}).get("counts") != {
        "exact_surfaces": 625,
        "exact_instances": 2745,
        "ruby_context_annotations": 924,
    }:
        raise ValueError("reviewed-exact candidate count closure changed")
    expected = {
        "Chiba": (7, 8, "new_202608_document"),
        "Gugyeol": (2, 4, "reviewed_missing_ruby_repairs"),
        "Sophia-Universitato": (7, 8, "new_202608_document"),
        "Tokio": (64, 65, "new_202608_document"),
    }
    actual = {
        row.get("surface"): (
            row.get("old_count"), row.get("new_count"), row.get("cause"),
        )
        for row in ledger.get("evidence_deltas", [])
    }
    if actual != expected:
        raise ValueError(f"reviewed-exact evidence delta closure changed: {actual!r}")
    if ledger.get("policy") != {
        "old_residual_report_reuse": False,
        "source_only_refresh": False,
        "explicit_evidence_transition": True,
        "selected_surface_set_unchanged": True,
        "typed_boundaries_unchanged": True,
        "selected_glosses_unchanged": True,
        "runtime_rules_changed": False,
    }:
        raise ValueError("reviewed-exact evidence transition policy changed")


def load_parent(ledger: dict) -> dict:
    parent = ledger["parent"]
    raw = git_blob(parent["app_commit"], parent["manifest_path"])
    if sha256_bytes(raw) != parent["manifest_sha256"]:
        raise ValueError("pinned parent reviewed-exact manifest hash changed")
    payload = json.loads(raw.decode("utf-8"))
    source = payload.get("source", {})
    for key, expected in parent["source"].items():
        if source.get(key) != expected:
            raise ValueError(f"historical reviewed-exact source changed: {key}")
    if source.get("report", {}).get("sha256") != parent["report_sha256"]:
        raise ValueError("historical reviewed-exact report identity changed")
    if payload.get("counts") != parent["counts"]:
        raise ValueError("historical reviewed-exact counts changed")
    return payload


def build(corpus_root: Path) -> dict:
    ledger_raw = LEDGER_PATH.read_bytes()
    ledger = json.loads(ledger_raw.decode("utf-8"))
    validate_ledger(ledger)
    parent = load_parent(ledger)
    selected = {
        row["surface"]: set(row["available_expected_options"])
        for row in parent["exact_surfaces"]
    }
    if len(selected) != 625:
        raise ValueError(f"reviewed exact selection changed: {len(selected)}")
    report_meta = {
        "kind": "explicit_evidence_transition",
        "filename": LEDGER_PATH.name,
        "sha256": sha256_bytes(ledger_raw),
        "schema_version": ledger["schema_version"],
        "parent_report_sha256": ledger["parent"]["report_sha256"],
        "changed_surfaces": sorted(
            row["surface"] for row in ledger["evidence_deltas"]
        ),
    }
    payload = reviewed.build(corpus_root, selected, report_meta)

    candidate = ledger["candidate"]
    source = payload["source"]
    expected_source = {
        key: candidate[key]
        for key in (
            "head_oid", "content_sha256", "content_files", "raw_ruby",
            "parsed_ruby", "parsed_units",
        )
    }
    actual_source = {key: source[key] for key in expected_source}
    if actual_source != expected_source or git_tree(corpus_root) != candidate["tree_oid"]:
        raise ValueError(f"reviewed-exact candidate source changed: {actual_source!r}")
    if payload["counts"] != candidate["counts"]:
        raise ValueError("reviewed-exact candidate counts changed")

    semantic_hashes = {
        "parent_exact_rules_sha256": canonical_hash(
            row_semantics(parent["exact_surfaces"])
        ),
        "candidate_exact_rules_sha256": canonical_hash(
            row_semantics(payload["exact_surfaces"])
        ),
        "parent_annotation_glosses_sha256": canonical_hash(
            annotation_semantics(parent["annotations"])
        ),
        "candidate_annotation_glosses_sha256": canonical_hash(
            annotation_semantics(payload["annotations"])
        ),
    }
    expected_semantic = {
        key: value for key, value in ledger["semantic_hashes"].items()
        if key.endswith("_sha256")
    }
    if semantic_hashes != expected_semantic:
        raise ValueError(f"reviewed-exact semantic identity changed: {semantic_hashes!r}")
    if (
        semantic_hashes["parent_exact_rules_sha256"]
        != semantic_hashes["candidate_exact_rules_sha256"]
        or semantic_hashes["parent_annotation_glosses_sha256"]
        != semantic_hashes["candidate_annotation_glosses_sha256"]
    ):
        raise ValueError("reviewed-exact runtime semantics changed")

    computed_deltas = evidence_deltas(parent, payload)
    ledger_deltas = [
        {key: row[key] for key in ("surface", "old_count", "new_count", "path_deltas")}
        for row in ledger["evidence_deltas"]
    ]
    if computed_deltas != ledger_deltas:
        raise ValueError(f"reviewed-exact evidence deltas changed: {computed_deltas!r}")

    candidate_hashes = {
        "exact_surfaces_sha256": canonical_hash(payload["exact_surfaces"]),
        "annotations_sha256": canonical_hash(payload["annotations"]),
        "payload_sha256": canonical_hash({
            key: value for key, value in payload.items()
            if key not in {"source", "description"}
        }),
    }
    if candidate_hashes != ledger["candidate_hashes"]:
        raise ValueError(f"reviewed-exact candidate payload changed: {candidate_hashes!r}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    corpus_value = os.environ.get("ESP_CORPUS_PATH", "").strip()
    if not corpus_value:
        raise SystemExit("ESP_CORPUS_PATH is required")
    payload = build(Path(corpus_value).resolve())
    if args.write:
        atomic_json_dump(OUTPUT, payload, indent=1)
    else:
        current = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if reviewed.semantic_manifest(current) != reviewed.semantic_manifest(payload):
            raise SystemExit("active reviewed-exact manifest is stale")
    print(json.dumps({
        "mode": "write" if args.write else "check",
        "output": str(OUTPUT),
        "corpus_head": payload["source"]["head_oid"],
        "content_sha256": payload["source"]["content_sha256"],
        **payload["counts"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
